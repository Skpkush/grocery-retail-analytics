# KPI definitions

_Generated from `src/retail/metrics.py` (SQL metric layer) and the Power BI TMDL files. The two sides are reconciled value-by-value in `reports/reconciliation.md`._

All KPIs use **merchandise only** (`is_merch`: fuel, gift cards and non-merchandise excluded) and the panel households' purchases, not total store sales.

## Core KPIs: SQL and DAX

### Net Sales

Merchandise sales the retailer received.

SQL (metric layer, `s` = fct_sales, `p` = dim_product):

```sql
ROUND(SUM(s.sales_value), 2)
```

DAX (Power BI):

```dax
SUM ( Sales[sales_value] )
```

### Gross Sales

Shelf-price sales before retailer-funded discounts.

SQL (metric layer, `s` = fct_sales, `p` = dim_product):

```sql
ROUND(SUM(s.gross_sales), 2)
```

DAX (Power BI):

```dax
SUM ( Sales[gross_sales] )
```

### Retailer Discount

Loyalty discounts plus coupon matches, funded by the retailer.

SQL (metric layer, `s` = fct_sales, `p` = dim_product):

```sql
ROUND(SUM(s.retail_disc + s.coupon_match_disc), 2)
```

DAX (Power BI):

```dax
SUM ( Sales[retail_disc] ) + SUM ( Sales[coupon_match_disc] )
```

### Manufacturer Coupons

Manufacturer-funded coupon value.

SQL (metric layer, `s` = fct_sales, `p` = dim_product):

```sql
ROUND(SUM(s.coupon_disc), 2)
```

DAX (Power BI):

```dax
SUM ( Sales[coupon_disc] )
```

### Discount Rate %

Retailer-funded discount as a percent of gross sales.

SQL (metric layer, `s` = fct_sales, `p` = dim_product):

```sql
ROUND(100.0 * SUM(s.retail_disc + s.coupon_match_disc) / NULLIF(SUM(s.gross_sales), 0), 1)
```

DAX (Power BI):

```dax
DIVIDE ( [Retailer Discount], [Gross Sales] )
```

### Baskets

Shopping trips.

SQL (metric layer, `s` = fct_sales, `p` = dim_product):

```sql
COUNT(DISTINCT s.basket_id)
```

DAX (Power BI):

```dax
DISTINCTCOUNT ( Sales[basket_id] )
```

### Households

Households that shopped.

SQL (metric layer, `s` = fct_sales, `p` = dim_product):

```sql
COUNT(DISTINCT s.household_id)
```

DAX (Power BI):

```dax
DISTINCTCOUNT ( Sales[household_id] )
```

### Units Sold

Units sold (fuel excluded).

SQL (metric layer, `s` = fct_sales, `p` = dim_product):

```sql
SUM(s.units)
```

DAX (Power BI):

```dax
SUM ( Sales[units] )
```

### Avg Basket Value

Net sales per basket.

SQL (metric layer, `s` = fct_sales, `p` = dim_product):

```sql
ROUND(SUM(s.sales_value) / NULLIF(COUNT(DISTINCT s.basket_id), 0), 2)
```

DAX (Power BI):

```dax
DIVIDE ( [Net Sales], [Baskets] )
```

### Units per Basket

Units per basket.

SQL (metric layer, `s` = fct_sales, `p` = dim_product):

```sql
ROUND(SUM(s.units) / NULLIF(COUNT(DISTINCT s.basket_id), 0), 2)
```

DAX (Power BI):

```dax
DIVIDE ( [Units Sold], [Baskets] )
```

### Sales per Household

Net sales per shopping household.

SQL (metric layer, `s` = fct_sales, `p` = dim_product):

```sql
ROUND(SUM(s.sales_value) / NULLIF(COUNT(DISTINCT s.household_id), 0), 2)
```

DAX (Power BI):

```dax
DIVIDE ( [Net Sales], [Households] )
```

### Private Label Share %

Share of net sales from the retailer's own brand.

SQL (metric layer, `s` = fct_sales, `p` = dim_product):

```sql
ROUND(100.0 * SUM(CASE WHEN p.brand = 'Private' THEN s.sales_value END) / NULLIF(SUM(s.sales_value), 0), 1)
```

DAX (Power BI):

```dax
DIVIDE ( CALCULATE ( [Net Sales], Product[brand] = "Private" ), [Net Sales] )
```

### Promo Sales Share %

Share of net sales sold with a loyalty discount.

SQL (metric layer, `s` = fct_sales, `p` = dim_product):

```sql
ROUND(100.0 * SUM(CASE WHEN s.retail_disc > 0 THEN s.sales_value END) / NULLIF(SUM(s.sales_value), 0), 1)
```

DAX (Power BI):

```dax
DIVIDE ( CALCULATE ( [Net Sales], Sales[retail_disc] > 0 ), [Net Sales] )
```

## Other Power BI measures

| Measure | DAX |
| --- | --- |
| Affinity Lift | `MAX ( 'Basket Affinity'[lift] )` |
| Avg Basket QoQ % | `VAR Prior = CALCULATE ( [Avg Basket Value], DATEADD ( 'Date'[date_key], -1, QUARTER ) ) RETURN DIVIDE ( [Avg Basket Value] - Prior, Prior )` |
| Baskets QoQ % | `VAR Prior = CALCULATE ( [Baskets], DATEADD ( 'Date'[date_key], -1, QUARTER ) ) RETURN DIVIDE ( [Baskets] - Prior, Prior )` |
| Baskets per Household | `DIVIDE ( [Baskets], [Households] )` |
| Category Sales Share % | `DIVIDE ( [Net Sales], CALCULATE ( [Net Sales], REMOVEFILTERS ( Product ) ) )` |
| Color Basket Value QoQ | `IF ( [Avg Basket QoQ %] >= 0, "#15803D", "#B91C1C" )` |
| Color Baskets QoQ | `IF ( [Baskets QoQ %] >= 0, "#15803D", "#B91C1C" )` |
| Color Discount Change | `IF ( [Discount Rate Change pts] <= 0, "#15803D", "#B91C1C" )` |
| Color Effect | `IF ( SELECTEDVALUE ( 'Campaign Tests'[effect_per_household_week] ) < 0, "#B91C1C", "#15803D" )` |
| Color Placebo Highlight | `IF ( SELECTEDVALUE ( 'Campaign Tests'[test] ) = "Placebo (pre-launch)" && SELECTEDVALUE ( 'Campaign Tests'[significant] ) = TRUE (), "#FEF3C7", "#FFFFFF" )` |
| Color RFM Segment | `SWITCH ( SELECTEDVALUE ( Household[rfm_segment] ), "1. Champions", "#0F766E", "3. At risk", "#D97706", "#94A3B8" )` |
| Color Sales QoQ | `IF ( [Net Sales QoQ %] >= 0, "#15803D", "#B91C1C" )` |
| Discount Rate Change pts | `VAR Prior = CALCULATE ( [Discount Rate %], DATEADD ( 'Date'[date_key], -1, QUARTER ) ) RETURN IF ( NOT ISBLANK ( Prior ), ( [Discount Rate %] - Prior ) * 100 )` |
| Habitual Redemption % | `DIVIDE ( [Habitual Redemptions], [Scored Redemptions] )` |
| Habitual Redemptions | `CALCULATE ( COUNTROWS ( 'Coupon Redemptions' ), 'Coupon Redemptions'[is_scored] = TRUE (), 'Coupon Redemptions'[is_habitual] = TRUE () )` |
| Household Redemption Rate % | `VAR Redeemers = SUMX ( VALUES ( 'Campaign Targets'[campaign_id] ), VAR c = 'Campaign Targets'[campaign_id] RETURN CALCULATE ( DISTINCTCOUNT ( 'Coupon Redemptions'[household_id] ), 'Coupon Redemptions'[campaign_id] = c ) ) RETURN DIVIDE ( Redeemers, [Targeted Households] )` |
| Lift CI High % | `DIVIDE ( MAX ( 'Promotion Lift'[ci_high_pct] ), 100 )` |
| Lift CI Low % | `DIVIDE ( MAX ( 'Promotion Lift'[ci_low_pct] ), 100 )` |
| Loyalty Discount Sales | `CALCULATE ( [Net Sales], Sales[retail_disc] > 0 )` |
| Net Sales PQ | `CALCULATE ( [Net Sales], DATEADD ( 'Date'[date_key], -1, QUARTER ) )` |
| Net Sales QoQ % | `DIVIDE ( [Net Sales] - [Net Sales PQ], [Net Sales PQ] )` |
| Product Penetration % | `DIVIDE ( [Households], COUNTROWS ( ALL ( Household ) ) )` |
| Promotion Lift % | `DIVIDE ( MAX ( 'Promotion Lift'[lift_pct] ), 100 )` |
| Redemptions | `COUNTROWS ( 'Coupon Redemptions' )` |
| Repeat Household Rate % | `VAR HH = ADDCOLUMNS ( VALUES ( Sales[household_id] ), "@trips", CALCULATE ( DISTINCTCOUNT ( Sales[basket_id] ) ) ) RETURN DIVIDE ( COUNTROWS ( FILTER ( HH, [@trips] >= 2 ) ), COUNTROWS ( HH ) )` |
| Rolling 4-Week Sales | `VAR Wk = MAX ( 'Date'[retail_week] ) VAR Weeks = CALCULATETABLE ( VALUES ( 'Date'[retail_week] ), REMOVEFILTERS ( 'Date' ), 'Date'[retail_week] > Wk - 4, 'Date'[retail_week] <= Wk ) RETURN AVERAGEX ( Weeks, VAR w = 'Date'[retail_week] RETURN CALCULATE ( [Net Sales], REMOVEFILTERS ( 'Date' ), 'Date'[retail_week] = w ) )` |
| Scored Redemptions | `CALCULATE ( COUNTROWS ( 'Coupon Redemptions' ), 'Coupon Redemptions'[is_scored] = TRUE () )` |
| Segment Sales Share % | `DIVIDE ( [Net Sales], CALCULATE ( [Net Sales], REMOVEFILTERS ( Household ) ) )` |
| Targeted Households | `COUNTROWS ( 'Campaign Targets' )` |
| Top 10% Household Share | `VAR HH = FILTER ( ADDCOLUMNS ( VALUES ( Sales[household_id] ), "@s", [Net Sales] ), NOT ISBLANK ( [@s] ) ) VAR N = INT ( 0.1 * COUNTROWS ( HH ) ) VAR TopHH = TOPN ( N, HH, [@s], DESC ) RETURN DIVIDE ( SUMX ( TopHH, [@s] ), SUMX ( HH, [@s] ) )` |
| WoW Growth % | `VAR Wk = MAX ( 'Date'[retail_week] ) VAR Prior = CALCULATE ( [Net Sales], REMOVEFILTERS ( 'Date' ), 'Date'[retail_week] = Wk - 1 ) RETURN IF ( HASONEVALUE ( 'Date'[retail_week] ), DIVIDE ( [Net Sales] - Prior, Prior ) )` |

The model has **44 measures** in total.
