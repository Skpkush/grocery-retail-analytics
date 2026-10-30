"""Data quality: declarative checks run after every warehouse build.

Each check is a SQL query that counts violating rows. ``error`` checks stop the
pipeline (bad data never reaches a dashboard); ``warn`` checks document known
source limitations with their size, so they are visible rather than silent.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

import duckdb

from retail.config import QUALITY_REPORT_PATH


@dataclass(frozen=True)
class Check:
    name: str
    sql: str  # returns one integer: violating rows
    severity: str  # "error" | "warn"
    description: str
    max_allowed: int = 0


CHECKS: tuple[Check, ...] = (
    # --- Completeness and reconciliation -----------------------------------
    Check(
        "Landing rows reconcile to fact + quarantine",
        "SELECT ABS((SELECT COUNT(*) FROM landing_transactions)"
        " - (SELECT COUNT(*) FROM fct_sales) - (SELECT COUNT(*) FROM quarantine_transactions))",
        "error",
        "No transaction line may be lost between landing and the warehouse.",
    ),
    Check(
        "Sales value reconciles to the cent",
        "SELECT CAST(ROUND(100 * ABS((SELECT SUM(sales_value) FROM landing_transactions)"
        " - (SELECT SUM(sales_value) FROM fct_sales)"
        " - (SELECT SUM(sales_value) FROM quarantine_transactions))) AS BIGINT)",
        "error",
        "Total sales across fact and quarantine equals the source total.",
    ),
    # --- Keys -----------------------------------------------------------------
    Check("Unique product_id", "SELECT COUNT(*) - COUNT(DISTINCT product_id) FROM dim_product",
          "error", "Product dimension has one row per product."),
    Check("Unique household_id", "SELECT COUNT(*) - COUNT(DISTINCT household_id) FROM dim_household",
          "error", "Household dimension has one row per household."),
    Check("Unique basket_id", "SELECT COUNT(*) - COUNT(DISTINCT basket_id) FROM fct_baskets",
          "error", "Basket fact has one row per basket."),
    Check("Basket belongs to one household and store",
          "SELECT COUNT(*) FROM (SELECT basket_id FROM fct_sales GROUP BY basket_id"
          " HAVING COUNT(DISTINCT household_id) > 1 OR COUNT(DISTINCT store_id) > 1)",
          "error", "A basket is one trip by one household in one store."),
    Check("Exact duplicate transaction lines",
          "SELECT COUNT(*) - COUNT(DISTINCT (household_id, store_id, basket_id, product_id,"
          " units, sales_value, retail_disc, coupon_disc)) FROM fct_sales",
          "warn", "Identical lines are legitimate (same item scanned twice) but are tracked."),
    # --- Referential integrity ---------------------------------------------
    Check("Sales reference a known product",
          "SELECT COUNT(*) FROM fct_sales s ANTI JOIN dim_product p USING (product_id)",
          "error", "Every fact row joins to the product dimension."),
    Check("Sales reference a known household",
          "SELECT COUNT(*) FROM fct_sales s ANTI JOIN dim_household h USING (household_id)",
          "error", "Every fact row joins to the household dimension."),
    Check("Sales dates fall inside the calendar",
          "SELECT COUNT(*) FROM fct_sales s ANTI JOIN dim_date d ON d.date_key = s.business_date",
          "error", "Every business_date exists in dim_date (2017)."),
    Check("Redemptions come from targeted households",
          "SELECT COUNT(*) FROM fct_coupon_redemptions r ANTI JOIN fct_campaign_targets t"
          " USING (campaign_id, household_id)",
          "error", "A household can only redeem a coupon from a campaign it received."),
    Check("Redeemed coupons exist in the coupon master",
          "SELECT COUNT(*) FROM fct_coupon_redemptions r ANTI JOIN dim_coupon c"
          " USING (coupon_upc, campaign_id)", "error", "Every redemption maps to a coupon."),
    # --- Validity ---------------------------------------------------------------
    Check("Derived retail week matches the source week",
          "SELECT COUNT(*) FROM stg_transactions s JOIN dim_date d ON d.date_key = s.business_date"
          " WHERE d.retail_week <> s.source_week",
          "error", "The 05:00 trading-day rule reproduces the retailer's own week numbers."),
    Check("No negative sales or discounts",
          "SELECT COUNT(*) FROM fct_sales WHERE sales_value < 0 OR retail_disc < 0"
          " OR coupon_disc < 0 OR coupon_match_disc < 0", "error",
          "Source stores discounts as positive amounts."),
    Check("Campaign end on or after start",
          "SELECT COUNT(*) FROM dim_campaign WHERE end_date < start_date", "error",
          "Campaign windows are valid."),
    Check("Income band mapped for every surveyed household",
          "SELECT COUNT(*) FROM stg_households WHERE income_order IS NULL OR age_order IS NULL",
          "error", "Every source income/age label maps to a sort order."),
    # --- Known source limitations (warn, documented) -----------------------
    Check("Orphan transaction lines (quarantined)",
          "SELECT COUNT(*) FROM quarantine_transactions", "warn",
          "Lines whose product_id is missing from the product master.", max_allowed=10_000),
    Check("Zero-quantity merchandise lines",
          "SELECT COUNT(*) FROM fct_sales WHERE is_merch AND units = 0", "warn",
          "Kept for sales totals; excluded from unit price calculations.", max_allowed=5_000),
    Check("Zero-value merchandise lines",
          "SELECT COUNT(*) FROM fct_sales WHERE is_merch AND sales_value = 0", "warn",
          "Fully discounted or free items.", max_allowed=20_000),
    Check("Households without demographics",
          "SELECT COUNT(*) FROM dim_household WHERE NOT has_demographics", "warn",
          "Demographic analysis covers surveyed households only.", max_allowed=2_000),
    Check("Duplicate promotion listings (merged)",
          "SELECT COALESCE(SUM(source_rows - 1), 0) FROM fct_promotions", "warn",
          "Product x store x week keys listed more than once in the source; merged to one row.",
          max_allowed=20_000),
    Check("Unique promotion key",
          "SELECT COUNT(*) - COUNT(DISTINCT (product_id, store_id, week)) FROM fct_promotions",
          "error", "One promotion row per product x store x week after merging."),
    Check("Every shopping household has one segment row",
          "SELECT ABS((SELECT COUNT(DISTINCT household_id) FROM fct_sales WHERE is_merch)"
          " - (SELECT COUNT(*) FROM mart_household_segments))"
          " + (SELECT COUNT(*) - COUNT(DISTINCT household_id) FROM mart_household_segments)",
          "error", "RFM and deal segments cover each merchandise household exactly once."),
    Check("Products without a category",
          "SELECT COUNT(*) FROM dim_product WHERE product_category = 'UNCATEGORIZED'", "warn",
          "Shown as UNCATEGORIZED in category views.", max_allowed=1_000),
)


def run_checks(con: duckdb.DuckDBPyConnection) -> dict:
    results = []
    for check in CHECKS:
        violations = int(con.execute(check.sql).fetchone()[0] or 0)
        passed = violations <= check.max_allowed
        results.append({**asdict(check), "violations": violations, "passed": passed})
    errors = [r["name"] for r in results if r["severity"] == "error" and not r["passed"]]
    report = {
        "checks": [{k: v for k, v in r.items() if k != "sql"} for r in results],
        "passed": sum(r["passed"] for r in results),
        "total": len(results),
        "blocking_failures": errors,
    }
    QUALITY_REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
