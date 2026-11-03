"""Transform: build and test the DuckDB warehouse with dbt.

The models, tests and analyses live in the dbt project at the repository root
(models/, tests/dbt/, analyses/). This module runs ``dbt build`` so the pipeline
and the Streamlit app can rebuild the warehouse in one call.

    dbt build                 # same thing from the command line
"""

from __future__ import annotations

import logging
import subprocess
import sys

import duckdb

from retail.config import PROJECT_ROOT, WAREHOUSE_PATH

logger = logging.getLogger("retail")


def connect(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(WAREHOUSE_PATH), read_only=read_only)


def _dbt(*args: str) -> int:
    # A separate process, so dbt's DuckDB connection is closed when it finishes
    # (DuckDB refuses a second connection with different settings in one process).
    command = [sys.executable, "-c", "from dbt.cli.main import cli; cli()", *args]
    # dbt resolves the project, profile and source paths from the project root.
    return subprocess.run(command, cwd=PROJECT_ROOT, check=False).returncode


def build(target: str | None = None) -> bool:
    """Run `dbt deps` and `dbt build`. Returns True when no model or error-level test failed."""
    if not (PROJECT_ROOT / "dbt_packages").exists() and _dbt("deps", "--quiet") != 0:
        raise RuntimeError("dbt deps failed.")
    return _dbt("build", *(["--target", target] if target else [])) == 0


def table_counts() -> dict[str, int]:
    con = connect(read_only=True)
    try:
        tables = con.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_type = 'BASE TABLE' ORDER BY table_name"
        ).fetchall()
        return {t: con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for (t,) in tables}
    finally:
        con.close()
