"""Governed, read-only SQL execution against the DuckDB warehouse.

Defence in depth for any SQL a person or a model writes:
1. Validation: exactly one SELECT/WITH statement; DDL, DML, settings and
   file/extension keywords are rejected after comments and literals are masked.
2. Connection: opened ``read_only`` with ``enable_external_access = false``, so
   even a query that slipped past validation cannot write, read local files
   (``read_csv``, ``'file.parquet'``) or load extensions.
3. Row cap: the query is wrapped in an outer LIMIT enforced by the engine.
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass
from typing import Any

import duckdb

from retail.config import MAX_SQL_ROWS, WAREHOUSE_PATH

FORBIDDEN_KEYWORDS = re.compile(
    r"\b("
    r"insert|update|delete|drop|alter|create|truncate|attach|detach|pragma|set|reset|"
    r"vacuum|checkpoint|copy|export|import|install|load|call|begin|commit|rollback|"
    r"grant|revoke|merge|into|replace|"
    r"read_csv\w*|read_parquet|read_json\w*|read_text|read_blob|parquet_scan|glob|"
    r"sniff_csv|query_table|query"
    r")\b",
    re.IGNORECASE,
)


class SQLValidationError(ValueError):
    """Raised when SQL is not a single safe read-only query."""


@dataclass
class SQLResult:
    columns: list[str]
    rows: list[dict[str, Any]]
    sql: str
    row_count: int
    truncated: bool = False

    def to_markdown(self, max_rows: int | None = None) -> str:
        rows = self.rows if max_rows is None else self.rows[:max_rows]
        return rows_to_markdown(self.columns, rows, truncated=self.truncated)


def _strip_fence(sql: str) -> str:
    fenced = re.fullmatch(r"```(?:sql)?\s*(.*?)\s*```", sql.strip(), flags=re.I | re.S)
    return fenced.group(1).strip() if fenced else sql.strip()


def _mask(sql: str) -> str:
    """Blank out comments and quoted text so keyword checks cannot be fooled."""
    out, i, n = [], 0, len(sql)
    while i < n:
        ch = sql[i]
        if sql.startswith("--", i):
            end = sql.find("\n", i)
            end = n if end == -1 else end
            out.append(" " * (end - i))
            i = end
            continue
        if sql.startswith("/*", i):
            end = sql.find("*/", i + 2)
            if end == -1:
                raise SQLValidationError("Unterminated block comment.")
            out.append(" " * (end + 2 - i))
            i = end + 2
            continue
        if ch in "'\"":
            j = i + 1
            while j < n:
                if sql[j] == ch:
                    if j + 1 < n and sql[j + 1] == ch:
                        j += 2
                        continue
                    break
                j += 1
            if j >= n:
                raise SQLValidationError("Unterminated quoted value in SQL.")
            # Keep the quote characters so a file-path scan ('x.parquet') stays visible.
            out.append(ch + " " * (j - i - 1) + ch)
            i = j + 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def validate_sql(sql: str) -> str:
    if not sql or not sql.strip():
        raise SQLValidationError("SQL is empty.")
    cleaned = _strip_fence(sql)
    core = _mask(cleaned).strip().rstrip(";").rstrip()
    if ";" in core:
        raise SQLValidationError("Only one statement is allowed; multiple statements were detected.")
    if not re.match(r"^(select|with)\b", core, re.I):
        raise SQLValidationError("Only read-only SELECT statements are allowed.")
    match = FORBIDDEN_KEYWORDS.search(core)
    if match:
        raise SQLValidationError(f"Blocked SQL keyword: {match.group(0).upper()}.")
    if re.search(r"\b(from|join)\s+'", core, re.I):
        raise SQLValidationError("Reading files directly is not allowed; query warehouse tables.")
    return cleaned.rstrip().rstrip(";").rstrip()


_lock = threading.Lock()
_connection: duckdb.DuckDBPyConnection | None = None


def readonly_connection() -> duckdb.DuckDBPyConnection:
    """One shared read-only connection per process; callers use a cursor."""
    global _connection
    with _lock:
        if _connection is None:
            if not WAREHOUSE_PATH.exists():
                raise FileNotFoundError(
                    f"Warehouse not found at {WAREHOUSE_PATH}. Run: python -m retail.pipeline")
            _connection = duckdb.connect(
                str(WAREHOUSE_PATH), read_only=True,
                config={"enable_external_access": False, "lock_configuration": True},
            )
        return _connection


def reset_connection() -> None:
    global _connection
    with _lock:
        if _connection is not None:
            _connection.close()
        _connection = None


def execute_readonly_query(sql: str, max_rows: int = MAX_SQL_ROWS) -> SQLResult:
    safe_sql = validate_sql(sql)
    wanted = max(1, int(max_rows))
    limited = f"SELECT * FROM (\n{safe_sql}\n) AS _governed LIMIT {wanted + 1}"
    cursor = readonly_connection().cursor()
    try:
        cursor.execute(limited)
        columns = [d[0] for d in cursor.description]
        raw = cursor.fetchall()
    finally:
        cursor.close()
    truncated = len(raw) > wanted
    rows = [dict(zip(columns, values, strict=True)) for values in raw[:wanted]]
    return SQLResult(columns, rows, safe_sql, len(rows), truncated)


def get_schema_description() -> str:
    """Compact schema of the marts for prompts and the UI."""
    cursor = readonly_connection().cursor()
    try:
        cols = cursor.execute(
            "SELECT table_name, column_name, data_type FROM information_schema.columns "
            "WHERE table_name LIKE 'dim_%' OR table_name LIKE 'fct_%' "
            "ORDER BY table_name, ordinal_position").fetchall()
    finally:
        cursor.close()
    tables: dict[str, list[str]] = {}
    for table, column, dtype in cols:
        tables.setdefault(table, []).append(f"{column} {dtype}")
    return "\n".join(f"{t}({', '.join(c)})" for t, c in tables.items())


def format_value(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        if value != value:  # NaN
            return "-"
        return f"{int(value):,}" if value.is_integer() else f"{value:,.2f}"
    return str(value)


def rows_to_markdown(columns: list[str], rows: list[dict[str, Any]], truncated: bool = False) -> str:
    if not columns:
        return "_No columns returned._"
    if not rows:
        return "_No rows matched the query._"

    def cell(v: Any) -> str:
        return format_value(v).replace("|", "\\|").replace("\n", " ")

    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    lines += ["| " + " | ".join(cell(r.get(c)) for c in columns) + " |" for r in rows]
    if truncated:
        lines.append(f"\n_Showing the first {len(rows)} rows (result truncated)._")
    return "\n".join(lines)
