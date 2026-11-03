"""Data quality report built from the dbt test results.

The 24 checks are dbt tests (generic tests in the model YAML files, singular
tests in tests/dbt/). Each one carries ``meta.dq_check`` with a readable name.
After ``dbt build``, this module reads target/manifest.json and
target/run_results.json and writes data/quality_report.json for the app and
the generated docs.

``error`` checks fail ``dbt build`` (bad data never reaches a dashboard);
``warn`` checks track a known source limitation and warn only above a ceiling.
dbt records a row count only when a test fails, so the count shown for each
check is recomputed from the test's compiled SQL.
"""

from __future__ import annotations

import json

import duckdb

from retail.config import DBT_TARGET_DIR, QUALITY_REPORT_PATH


def _load(name: str) -> dict:
    return json.loads((DBT_TARGET_DIR / name).read_text(encoding="utf-8"))


def _violations(con: duckdb.DuckDBPyConnection, node: dict) -> int:
    fail_calc = node["config"].get("fail_calc") or "count(*)"
    sql = f"SELECT {fail_calc} FROM ({node['compiled_code']}) AS failing_rows"
    return int(con.execute(sql).fetchone()[0] or 0)


def build_report(con: duckdb.DuckDBPyConnection) -> dict:
    manifest, run_results = _load("manifest.json"), _load("run_results.json")
    status = {r["unique_id"]: r["status"] for r in run_results["results"]}
    checks: dict[str, dict] = {}
    for uid, node in manifest["nodes"].items():
        meta = node["config"].get("meta") or {}
        if node["resource_type"] != "test" or "dq_check" not in meta or uid not in status:
            continue
        violations = _violations(con, node) if node.get("compiled_code") else 0
        check = checks.setdefault(meta["dq_check"], {
            "name": meta["dq_check"],
            "severity": node["config"].get("severity", "ERROR").lower(),
            "description": meta.get("description", ""),
            "max_allowed": _threshold(node["config"].get("warn_if", "!= 0")),
            "dbt_tests": [],
            "violations": 0,
            "passed": True,
        })
        check["dbt_tests"].append(node["name"])
        check["violations"] += violations
        check["passed"] = check["passed"] and status[uid] == "pass"
    results = sorted(checks.values(), key=lambda c: (c["severity"] != "error", c["name"]))
    report = {
        "checks": results,
        "passed": sum(c["passed"] for c in results),
        "total": len(results),
        "blocking_failures": [c["name"] for c in results if c["severity"] == "error" and not c["passed"]],
    }
    QUALITY_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    QUALITY_REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def _threshold(warn_if: str) -> int:
    """'>10000' -> 10000; the default '!= 0' -> 0."""
    digits = "".join(ch for ch in warn_if if ch.isdigit())
    return int(digits) if warn_if.strip().startswith(">") and digits else 0
