# Data quality

_Generated from `data/quality_report.json`, which `retail.quality` builds from the dbt test results after every `dbt build`._

**24 of 24 checks pass.** Each check is one or more dbt tests (column tests in the model YAML files, SQL tests in `tests/dbt/`). `error` checks fail `dbt build`; `warn` checks record a known source limitation and its size, and warn only above a ceiling.

| Check | Severity | Rows affected | Result | How it is handled | dbt tests |
| --- | --- | ---: | --- | --- | --- |
| Basket belongs to one household and store | error | 0 | pass | A basket is one trip by one household in one store. | `assert_basket_has_one_household_and_store` |
| Campaign end on or after start | error | 0 | pass | Campaign windows are valid. | `dbt_utils_expression_is_true_dim_campaign_end_date_start_date` |
| Derived retail week matches the source week | error | 0 | pass | Fails `dbt build`: proves the UTC to US Eastern rule. | `assert_derived_week_matches_source_week` |
| Every shopping household has one segment row | error | 0 | pass | RFM and deal segments cover each merchandise household exactly once. | `assert_every_merch_household_has_one_segment` |
| Income band mapped for every surveyed household | error | 0 | pass | Every source income/age label maps to a sort order. | `not_null_stg_completejourney__households_age_order`<br>`not_null_stg_completejourney__households_income_order` |
| Landing rows reconcile to fact + quarantine | error | 0 | pass | Fails `dbt build` if any source line is lost. | `assert_transaction_rows_reconcile` |
| No negative sales or discounts | error | 0 | pass | The source stores discounts as positive amounts. | `dbt_utils_accepted_range_fct_sales_sales_value__0`<br>`dbt_utils_accepted_range_fct_sales_retail_disc__0`<br>`dbt_utils_accepted_range_fct_sales_coupon_disc__0`<br>`dbt_utils_accepted_range_fct_sales_coupon_match_disc__0` |
| Redeemed coupons exist in the coupon master | error | 0 | pass | Every redemption maps to a coupon. | `assert_redeemed_coupons_exist` |
| Redemptions come from targeted households | error | 0 | pass | A household can only redeem a coupon from a campaign it received. | `assert_redemptions_from_targeted_households` |
| Sales dates fall inside the calendar | error | 0 | pass | Every business_date exists in dim_date (2017). | `relationships_fct_sales_business_date__date_key__ref_dim_date_` |
| Sales reference a known household | error | 0 | pass | Every fact row joins to the household dimension. | `relationships_fct_sales_household_id__household_id__ref_dim_household_` |
| Sales reference a known product | error | 0 | pass | Every fact row joins to the product dimension. | `relationships_fct_sales_product_id__product_id__ref_dim_product_` |
| Sales value reconciles to the cent | error | 0 | pass | Fails `dbt build` if source and warehouse sales differ. | `assert_sales_value_reconciles_to_the_cent` |
| Unique basket_id | error | 0 | pass | Basket fact has one row per basket. | `unique_fct_baskets_basket_id` |
| Unique household_id | error | 0 | pass | Household dimension has one row per household. | `unique_dim_household_household_id` |
| Unique product_id | error | 0 | pass | Product dimension has one row per product. | `unique_dim_product_product_id` |
| Unique promotion key | error | 0 | pass | One promotion row per product x store x week after merging. | `dbt_utils_unique_combination_of_columns_fct_promotions_product_id__store_id__week` |
| Duplicate promotion listings (merged) | warn | 12,785 | pass | Merged to one row per key; promoted if any listing says so. | `assert_duplicate_promotion_listings_within_limit` |
| Exact duplicate transaction lines | warn | 0 | pass | Kept: the same item scanned twice is a legitimate sale. | `assert_no_exact_duplicate_lines` |
| Households without demographics | warn | 1,668 | pass | Kept; demographic views filter to surveyed households. | `assert_households_without_demographics_within_limit` |
| Orphan transaction lines (quarantined) | warn | 4,836 | pass | Moved to quarantine_transactions with a reason; kept for audit. | `assert_orphan_lines_within_limit` |
| Products without a category | warn | 540 | pass | Labelled UNCATEGORIZED in category views. | `assert_uncategorized_products_within_limit` |
| Zero-quantity merchandise lines | warn | 4,062 | pass | Kept in sales totals; units reported as recorded. | `assert_zero_quantity_lines_within_limit` |
| Zero-value merchandise lines | warn | 6,248 | pass | Kept: fully discounted or free items. | `assert_zero_value_lines_within_limit` |

## Rules applied in the dbt models

- **Time zone.** Source timestamps are UTC; business dates are US Eastern dates. A fixed 05:00 cut-off put 785 rows in the wrong week during daylight saving time, and the week check caught it.
- **Fuel.** Gasoline lines record gallons or odometer readings as quantity (up to 89,638), so `units` is NULL for fuel and fuel is excluded from merchandise metrics.
- **Gift cards and coupons.** Gift card activations are liabilities, and coupon and postal lines are not merchandise, so `is_merch` excludes them.
- **Orphans.** Lines whose product is missing from the master go to `quarantine_transactions`.
- **Duplicates.** The coupon master (1,623 duplicate rows) is de-duplicated, and promotions are merged to one row per product x store x week.
- **Determinism.** RFM quintiles break ties on household_id, so segments are identical on every run.

dbt unit tests (the `unit_tests:` blocks in the model YAML files) run these models on small hand-built inputs that contain each problem, and check the expected handling.
