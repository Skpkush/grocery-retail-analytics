"""Integration tests on the real warehouse (skipped until the pipeline has run)."""

from __future__ import annotations

import json

import pytest
from conftest import requires_warehouse

from retail import analytics
from retail.config import QUALITY_REPORT_PATH, skipped_tables
from retail.metrics import select_metrics
from retail.sql_guard import execute_readonly_query
from retail.stats import wilson

pytestmark = requires_warehouse


def test_quality_gate_passed():
    report = json.loads(QUALITY_REPORT_PATH.read_text(encoding="utf-8"))
    assert report["blocking_failures"] == []
    assert report["total"] >= 20


def test_metric_layer_matches_sql_library():
    """Governed metric definitions and the hand-written library must agree."""
    governed = execute_readonly_query(
        "SELECT d.quarter_name, " + select_metrics("net_sales", "baskets", "avg_basket_value",
                                                   "discount_rate_pct", "private_label_share_pct")
        + " FROM fct_sales s JOIN dim_product p USING (product_id)"
          " JOIN dim_date d ON d.date_key = s.business_date WHERE s.is_merch GROUP BY 1 ORDER BY 1")
    library = analytics.run_analysis("kpi_by_quarter")
    for row, lib in zip(governed.rows, library.to_dict("records"), strict=True):
        assert row["quarter_name"] == lib["quarter"]
        for key in ("net_sales", "baskets", "avg_basket_value", "discount_rate_pct",
                    "private_label_share_pct"):
            assert row[key] == pytest.approx(lib[key], abs=0.01), key


def test_every_analysis_runs_and_returns_rows():
    for analysis in analytics.list_analyses():
        if analysis.key == "promotion_lift" and "promotions" in skipped_tables():
            continue
        assert not analytics.run_analysis(analysis.key).empty, analysis.key


@pytest.mark.parametrize("key,column", [
    ("department_performance", None), ("customer_concentration", "sales_share_pct"),
    ("rfm_segments", "sales_share_pct"), ("discount_dependency", "sales_share_pct"),
])
def test_shares_sum_to_100(key, column):
    if column:
        assert analytics.run_analysis(key)[column].sum() == pytest.approx(100, abs=0.5)


def test_quarters_sum_to_full_year():
    year = execute_readonly_query("SELECT SUM(sales_value) AS s FROM fct_sales WHERE is_merch").rows[0]["s"]
    assert analytics.run_analysis("kpi_by_quarter").net_sales.sum() == pytest.approx(year, abs=1)


def test_headline_findings_are_generated_with_numbers():
    findings = analytics.headline_findings()
    assert len(findings) >= 9
    assert all(any(ch.isdigit() for ch in f) for f in findings)


def test_wilson_interval_known_value():
    assert wilson(50, 100) == [40.4, 59.6]
