from __future__ import annotations

import os

from conftest import requires_warehouse

os.environ["RETAIL_OFFLINE"] = "1"

from retail.copilot import route  # noqa: E402


def test_routing_rules():
    assert route("Top 10 products in Q4") == "sql"
    assert route("How is gross sales defined?") == "docs"
    assert route("Are coupons incremental?") == "both"
    assert route("Which campaign types work?") == "both"
    assert route("hello") == "none"


@requires_warehouse
def test_golden_set_passes_fully():
    from retail.evaluate import evaluate

    results, scores = evaluate()
    assert {r["id"]: r["failures"] for r in results if not r["passed"]} == {}
    assert scores["route_accuracy"] == 1.0
