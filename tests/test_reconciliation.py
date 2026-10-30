"""Power BI measure values (captured from the live model) must equal independent SQL."""

from __future__ import annotations

from conftest import requires_warehouse

from retail.config import skipped_tables
from retail.reconcile import reconcile

pytestmark = requires_warehouse


def test_every_power_bi_value_matches_sql():
    rows = reconcile()
    if "promotions" in skipped_tables():  # lift needs the promotions table
        rows = [r for r in rows if not r["check"].startswith("promotion_lift/")]
    mismatches = {r["check"]: (r["dax"], r["sql"]) for r in rows if not r["match"]}
    assert mismatches == {}
    assert len(rows) >= 50
