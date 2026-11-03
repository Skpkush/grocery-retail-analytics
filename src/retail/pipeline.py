"""End-to-end pipeline: extract -> land -> dbt build -> quality report -> outputs.

    python -m retail.pipeline
"""

from __future__ import annotations

import logging
import time

from retail import (
    analytics,
    docs_gen,
    export_powerbi,
    findings,
    ingest,
    quality,
    sql_guard,
    stats,
    transform,
)

logger = logging.getLogger("retail")


def build_warehouse(target: str | None = None) -> dict:
    """Steps 1-4 only: enough for the app to start. The reports stay as committed."""
    if target != "ci":  # the ci target reads the committed sample instead
        logger.info("1/6 extract")
        ingest.download()
        logger.info("2/6 land")
        ingest.land()
    logger.info("3/6 transform and test (dbt build)")
    built = transform.build(target)
    for table, rows in transform.table_counts().items():
        logger.info("  %-26s %12s rows", table, f"{rows:,}")
    logger.info("4/6 quality report")
    con = transform.connect(read_only=True)
    try:
        report = quality.build_report(con)
    finally:
        con.close()
    for check in report["checks"]:
        status = "PASS" if check["passed"] else ("FAIL" if check["severity"] == "error" else "WARN")
        logger.info("  %-4s %-48s %s", status, check["name"], f"{check['violations']:,}")
    if not built or report["blocking_failures"]:
        failures = ", ".join(report["blocking_failures"]) or "see the dbt output above"
        raise SystemExit(f"dbt build failed: {failures}")
    return report


def run() -> dict:
    started = time.perf_counter()
    report = build_warehouse()
    logger.info("5/6 statistical tests")
    stats.run()
    logger.info("6/6 insights report and Power BI export")
    analytics.write_report()
    findings.write()
    # The export writes files, so it needs a connection with external access; DuckDB
    # allows only one configuration per file per process, so release the governed one.
    docs_gen.write()
    sql_guard.reset_connection()
    export_powerbi.export()
    logger.info("pipeline finished in %.0fs", time.perf_counter() - started)
    return report


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run()


if __name__ == "__main__":
    main()
