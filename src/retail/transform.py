"""Transform: build the DuckDB warehouse from landed Parquet with the SQL models.

Models in ``sql/models`` run in filename order (staging, then marts), the same
layering a dbt project uses, without the extra dependency.
"""

from __future__ import annotations

import logging
import time

import duckdb

from retail.config import (
    EMPTY_SCHEMAS,
    LANDING_DIR,
    MODELS_DIR,
    SOURCE_FILES,
    WAREHOUSE_PATH,
    skipped_tables,
)

logger = logging.getLogger("retail")


def connect(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(WAREHOUSE_PATH), read_only=read_only)


def build(names: tuple[str, ...] | None = None) -> dict[str, int]:
    WAREHOUSE_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = connect()
    try:
        for name in names or tuple(SOURCE_FILES):
            if name in skipped_tables():
                con.execute(f"CREATE OR REPLACE VIEW landing_{name} AS "
                            f"SELECT {EMPTY_SCHEMAS[name]} WHERE FALSE")
                continue
            path = (LANDING_DIR / f"{name}.parquet").as_posix()
            con.execute(f"CREATE OR REPLACE VIEW landing_{name} AS SELECT * FROM read_parquet('{path}')")
        for model in sorted(MODELS_DIR.glob("*.sql")):
            started = time.perf_counter()
            con.execute(model.read_text(encoding="utf-8"))
            logger.info("model %-16s %.1fs", model.name, time.perf_counter() - started)
        tables = con.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_type = 'BASE TABLE' ORDER BY table_name"
        ).fetchall()
        return {t: con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for (t,) in tables}
    finally:
        con.close()
