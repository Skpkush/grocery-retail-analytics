"""Export the star schema and analysis results to Parquet for the Power BI report.

Power BI reads Parquet natively (Parquet.Document), so the report uses exactly
the rows the warehouse holds. Statistical results (promotion lift, campaign
tests) are exported from reports/stats_results.json so the report shows the
same numbers, with their confidence intervals, as the Python analysis.

    python -m retail.export_powerbi
"""

from __future__ import annotations

import json

import pandas as pd

from retail.config import POWERBI_DATA_DIR, REPORTS_DIR
from retail.transform import connect

# table -> SELECT. Measures in the model are defined on these columns.
EXPORTS = {
    "fct_sales": "SELECT business_date, household_id, store_id, basket_id, product_id, units, "
                 "sales_value, retail_disc, coupon_disc, coupon_match_disc, gross_sales "
                 "FROM fct_sales WHERE is_merch",
    "dim_product": "SELECT product_id, department, product_category, product_type, brand "
                   "FROM dim_product",
    "dim_household": "SELECT h.household_id, h.has_demographics, h.age, h.age_order, h.income_band, "
                     "h.household_comp, h.household_size, h.campaigns_received, "
                     "COALESCE(s.rfm_segment, 'No merchandise purchases') AS rfm_segment, "
                     "COALESCE(s.deal_segment, 'No merchandise purchases') AS deal_segment, "
                     "s.recency_days, s.r_score, s.f_score, s.m_score "
                     "FROM dim_household h LEFT JOIN mart_household_segments s USING (household_id)",
    "dim_date": "SELECT date_key, retail_week, week_start, month_number, month_name, "
                "quarter_number, quarter_name, day_of_week, day_name, holiday_name FROM dim_date",
    "fct_coupon_redemptions": "SELECT redemption_id, household_id, coupon_upc, campaign_id, campaign_type, "
                              "redemption_date, is_scored, is_habitual FROM mart_coupon_redemptions",
    "fct_campaign_targets": "SELECT campaign_id, campaign_type, household_id FROM fct_campaign_targets",
    "basket_affinity": "SELECT category_a, category_b, baskets_together, support_pct, "
                       "confidence_a_to_b_pct, lift FROM mart_basket_affinity",
}


def _stats_tables() -> dict[str, pd.DataFrame]:
    path = REPORTS_DIR / "stats_results.json"
    if not path.exists():
        return {}
    stats = json.loads(path.read_text(encoding="utf-8"))
    lift = pd.DataFrame([
        {"promotion": k, "lift_pct": v["lift_pct"], "ci_low_pct": v["ci95_pct"][0],
         "ci_high_pct": v["ci95_pct"][1], "product_store_pairs": v["pairs"]}
        for k, v in stats.get("promotion_lift", {}).items()
    ], columns=["promotion", "lift_pct", "ci_low_pct", "ci_high_pct", "product_store_pairs"])
    tests = pd.DataFrame([
        {"campaign_type": ctype, "test": "Launch effect" if t == "did" else "Placebo (pre-launch)",
         "effect_per_household_week": r[t]["effect_per_household_week"],
         "ci_low": r[t]["ci95"][0], "ci_high": r[t]["ci95"][1], "p_value": r[t]["p_value"],
         "significant": r[t]["p_value"] < 0.05}
        for ctype, r in stats.get("campaign_did", {}).items() for t in ("did", "placebo")
    ])
    coupons = pd.DataFrame([
        {"campaign_type": k, "redemptions_scored": v["redemptions"], "habitual_pct": v["habitual_pct"],
         "ci_low_pct": v["ci95_pct"][0], "ci_high_pct": v["ci95_pct"][1]}
        for k, v in stats.get("coupon_habitual", {}).items()
    ])
    return {"promotion_lift": lift, "campaign_tests": tests, "coupon_habitual": coupons}


def export() -> list[str]:
    POWERBI_DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = connect(read_only=True)
    written = []
    try:
        for name, sql in EXPORTS.items():
            path = (POWERBI_DATA_DIR / f"{name}.parquet").as_posix()
            con.execute(f"COPY ({sql}) TO '{path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
            written.append(name)
    finally:
        con.close()
    for name, frame in _stats_tables().items():
        frame.to_parquet(POWERBI_DATA_DIR / f"{name}.parquet", index=False)
        written.append(name)
    return written


def main() -> None:
    print("Exported:", ", ".join(export()), "->", POWERBI_DATA_DIR)


if __name__ == "__main__":
    main()
