# Data dictionary

Source: 84.51° / dunnhumby "The Complete Journey" (2017 release), via the CC0
`completejourney` package. One year of purchases by 2,469 households that are
frequent shoppers at a US grocery retailer. Sales are those households'
purchases, not total store sales.

## Star schema

| Table | Grain | Rows | Notes |
|---|---|---:|---|
| fct_sales | one transaction line | 1,464,471 | Orphan lines (4,836) are in quarantine_transactions |
| fct_baskets | one shopping trip | 141,180 | Merchandise only |
| fct_campaign_targets | campaign x household | 6,589 | Who received which campaign |
| fct_coupon_redemptions | one redemption | 2,102 | Always by a targeted household |
| fct_promotions | product x store x week | ~20.9M | Only promoted weeks are listed |
| dim_product | product | 92,331 | department, product_category, brand (National/Private) |
| dim_household | household | 2,469 | demographics for 801 (has_demographics) |
| dim_date | trading day | 365 | retail_week, quarter, holiday_name |
| dim_campaign | campaign | 27 | Type A / B / C, start and end dates |
| dim_coupon | coupon x product x campaign | 111,332 | Products a coupon applies to |

## Money columns (fct_sales)

- **sales_value**: amount the retailer receives for the line.
- **retail_disc**: loyalty-card discount, funded by the retailer.
- **coupon_match_disc**: the retailer's match of a manufacturer coupon.
- **coupon_disc**: manufacturer coupon, funded by the manufacturer.
- **gross_sales** = sales_value + retail_disc + coupon_match_disc (shelf price).
- Discounts are stored as positive amounts.

## Flags

- **is_fuel**: gasoline lines. Their quantity is not a unit count (values up to
  89,638), so `units` is NULL for fuel.
- **is_non_merch**: gift card activations, coupons and postal lines, which are not
  merchandise revenue.
- **is_merch** = not fuel and not non-merchandise. All headline metrics use it.

## Time

Source timestamps are UTC. Stores run on US Eastern time, and the retailer's
weeks start at local midnight on Monday (05:00 UTC in winter, 04:00 UTC under
daylight saving). `business_date` is the Eastern local date, and it reproduces
the source week number on every row. Week 1 is the partial week ending Sunday
1 January 2017.

## Campaign types

- **Type A**: large campaigns (about 900 households each, about 200 coupons).
  These have the highest redemption rate.
- **Type B**: the most frequent format (17 campaigns, about 140 households each).
- **Type C**: long-running, small campaigns (about 76 days, about 100 households).

## Promotion codes (fct_promotions)

- **display_location**: in-store display placement; '0' or NULL means not on display.
- **mailer_location**: placement in the weekly mailer; '0' or NULL means not in the mailer.
- The feed lists only promoted product x store x weeks. A product's
  unpromoted weeks in a store are the weeks it does not appear.
