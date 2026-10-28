"""Export the star schema to Parquet for the Power BI report.

Power BI reads Parquet natively (Parquet.Document), so the report uses exactly
the rows the warehouse holds. Re-run after the pipeline:

    python -m retail.export_powerbi
"""

from __future__ import annotations

from retail.config import POWERBI_DATA_DIR
from retail.transform import connect

# table -> SELECT. Measures in the model are defined on these columns.
EXPORTS = {
    "fct_sales": "SELECT business_date, household_id, store_id, basket_id, product_id, units, "
                 "sales_value, retail_disc, coupon_disc, coupon_match_disc, gross_sales "
                 "FROM fct_sales WHERE is_merch",
    "dim_product": "SELECT product_id, department, product_category, product_type, brand "
                   "FROM dim_product",
    "dim_household": "SELECT household_id, has_demographics, age, age_order, income_band, "
                     "household_comp, household_size, campaigns_received FROM dim_household",
    "dim_date": "SELECT date_key, retail_week, week_start, month_number, month_name, "
                "quarter_number, quarter_name, day_of_week, day_name, holiday_name FROM dim_date",
    "fct_coupon_redemptions": "SELECT household_id, coupon_upc, campaign_id, campaign_type, "
                              "redemption_date FROM fct_coupon_redemptions",
    "fct_campaign_targets": "SELECT campaign_id, campaign_type, household_id FROM fct_campaign_targets",
}


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
    return written


def main() -> None:
    print("Exported:", ", ".join(export()), "->", POWERBI_DATA_DIR)


if __name__ == "__main__":
    main()
