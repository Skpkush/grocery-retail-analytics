# Data quality

_Generated from `data/quality_report.json`, written by the quality gate in every pipeline run._

**24 of 24 checks pass.** `error` checks block the pipeline; `warn` checks record a known source limitation and its size, so it is visible rather than silent.

| Check | Severity | Rows affected | Result | How it is handled |
| --- | --- | ---: | --- | --- |
| Landing rows reconcile to fact + quarantine | error | 0 | pass | Blocks the build if any source line is lost. |
| Sales value reconciles to the cent | error | 0 | pass | Blocks the build if source and warehouse sales differ. |
| Unique product_id | error | 0 | pass | Product dimension has one row per product. |
| Unique household_id | error | 0 | pass | Household dimension has one row per household. |
| Unique basket_id | error | 0 | pass | Basket fact has one row per basket. |
| Basket belongs to one household and store | error | 0 | pass | A basket is one trip by one household in one store. |
| Exact duplicate transaction lines | warn | 0 | pass | Kept: the same item scanned twice is a legitimate sale. |
| Sales reference a known product | error | 0 | pass | Every fact row joins to the product dimension. |
| Sales reference a known household | error | 0 | pass | Every fact row joins to the household dimension. |
| Sales dates fall inside the calendar | error | 0 | pass | Every business_date exists in dim_date (2017). |
| Redemptions come from targeted households | error | 0 | pass | A household can only redeem a coupon from a campaign it received. |
| Redeemed coupons exist in the coupon master | error | 0 | pass | Every redemption maps to a coupon. |
| Derived retail week matches the source week | error | 0 | pass | Blocks the build: proves the UTC to US Eastern rule. |
| No negative sales or discounts | error | 0 | pass | Source stores discounts as positive amounts. |
| Campaign end on or after start | error | 0 | pass | Campaign windows are valid. |
| Income band mapped for every surveyed household | error | 0 | pass | Every source income/age label maps to a sort order. |
| Orphan transaction lines (quarantined) | warn | 4,836 | pass | Moved to quarantine_transactions with a reason; kept for audit. |
| Zero-quantity merchandise lines | warn | 4,062 | pass | Kept in sales totals; units reported as recorded. |
| Zero-value merchandise lines | warn | 6,248 | pass | Kept: fully discounted or free items. |
| Households without demographics | warn | 1,668 | pass | Kept; demographic views filter to surveyed households. |
| Duplicate promotion listings (merged) | warn | 12,785 | pass | Merged to one row per key; promoted if any listing says so. |
| Unique promotion key | error | 0 | pass | One promotion row per product x store x week after merging. |
| Every shopping household has one segment row | error | 0 | pass | RFM and deal segments cover each merchandise household exactly once. |
| Products without a category | warn | 540 | pass | Labelled UNCATEGORIZED in category views. |

## Rules applied in the SQL models

- **Time zone.** Source timestamps are UTC; business dates are US Eastern dates. A fixed 05:00 cut-off put 785 rows in the wrong week during daylight saving time, and the week check caught it.
- **Fuel.** Gasoline lines record gallons or odometer readings as quantity (up to 89,638), so `units` is NULL for fuel and fuel is excluded from merchandise metrics.
- **Gift cards and coupons.** Gift card activations are liabilities, and coupon and postal lines are not merchandise, so `is_merch` excludes them.
- **Orphans.** Lines whose product is missing from the master go to `quarantine_transactions`.
- **Duplicates.** The coupon master (1,623 duplicate rows) is de-duplicated, and promotions are merged to one row per product x store x week.
- **Determinism.** RFM quintiles break ties on household_id, so segments are identical on every run.

Unit tests (`tests/test_models.py`) run these exact SQL models on a hand-built fixture that contains each problem, and assert the expected handling.
