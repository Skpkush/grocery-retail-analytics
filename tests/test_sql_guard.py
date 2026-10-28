from __future__ import annotations

import pytest
from conftest import requires_warehouse

from retail.sql_guard import SQLValidationError, execute_readonly_query, readonly_connection, validate_sql


@pytest.mark.parametrize("sql", [
    "SELECT 1", "WITH x AS (SELECT 1 AS n) SELECT n FROM x", "SELECT 'DROP TABLE x' AS note",
    "select department from dim_product -- trailing comment", "SELECT 'a;b' AS s;",
])
def test_allows_read_only_queries(sql):
    assert validate_sql(sql)


@pytest.mark.parametrize("sql", [
    "DELETE FROM fct_sales", "UPDATE dim_product SET brand = 'x'", "DROP TABLE fct_sales",
    "CREATE TABLE t AS SELECT 1", "INSERT INTO t VALUES (1)", "SELECT 1; DROP TABLE fct_sales",
    "SELECT 1; /* hidden */ DELETE FROM fct_sales", "PRAGMA database_list", "SET threads = 1",
    "INSTALL httpfs", "LOAD httpfs", "ATTACH 'x.db' AS x", "COPY fct_sales TO 'out.csv'",
    "SELECT * FROM read_csv('C:/Windows/win.ini')", "SELECT * FROM read_parquet('x.parquet')",
    "SELECT * FROM 'secrets.csv'", "SELECT * FROM glob('*')", "EXPORT DATABASE 'dump'",
])
def test_blocks_writes_files_and_settings(sql):
    with pytest.raises(SQLValidationError):
        validate_sql(sql)


@requires_warehouse
def test_row_cap_is_enforced_by_the_engine():
    result = execute_readonly_query("SELECT * FROM dim_product", max_rows=3)
    assert result.row_count == 3 and result.truncated


@requires_warehouse
def test_connection_cannot_write_or_read_files_even_without_validation():
    con = readonly_connection().cursor()
    with pytest.raises(Exception):
        con.execute("DELETE FROM dim_product")
    with pytest.raises(Exception):
        con.execute("SELECT * FROM read_csv('pyproject.toml')")
