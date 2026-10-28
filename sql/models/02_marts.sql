-- Marts: the star schema every dashboard, analysis and the copilot query.
-- Grain is stated on each table.

-- One row per trading day in 2017.
CREATE OR REPLACE TABLE dim_date AS
WITH days AS (
  SELECT CAST(d AS DATE) AS date_key
  FROM generate_series(DATE '2017-01-01', DATE '2017-12-31', INTERVAL 1 DAY) AS g(d)
)
SELECT
  date_key,
  -- Retail week: week 1 is the partial week ending Sunday 1 Jan; weeks start Monday.
  CAST(FLOOR(DATEDIFF('day', DATE '2016-12-26', date_key) / 7) + 1 AS INTEGER) AS retail_week,
  DATE_TRUNC('week', date_key)::DATE AS week_start,
  EXTRACT(month FROM date_key)::INTEGER AS month_number,
  STRFTIME(date_key, '%b %Y') AS month_name,
  EXTRACT(quarter FROM date_key)::INTEGER AS quarter_number,
  'Q' || EXTRACT(quarter FROM date_key) || ' 2017' AS quarter_name,
  ISODOW(date_key) AS day_of_week,
  STRFTIME(date_key, '%a') AS day_name,
  CASE date_key
    WHEN DATE '2017-02-05' THEN 'Super Bowl'
    WHEN DATE '2017-04-16' THEN 'Easter'
    WHEN DATE '2017-05-29' THEN 'Memorial Day'
    WHEN DATE '2017-07-04' THEN 'Independence Day'
    WHEN DATE '2017-09-04' THEN 'Labor Day'
    WHEN DATE '2017-11-23' THEN 'Thanksgiving'
    WHEN DATE '2017-12-25' THEN 'Christmas'
  END AS holiday_name
FROM days;

-- One row per product.
CREATE OR REPLACE TABLE dim_product AS
SELECT * FROM stg_products;

-- One row per shopping household (all 2,469); demographics exist for 801.
CREATE OR REPLACE TABLE dim_household AS
WITH shoppers AS (
  SELECT household_id,
         MIN(business_date) AS first_purchase_date,
         MAX(business_date) AS last_purchase_date
  FROM stg_transactions
  WHERE NOT is_orphan_product
  GROUP BY household_id
),
targeted AS (
  SELECT household_id, COUNT(*) AS campaigns_received
  FROM stg_campaign_targets GROUP BY household_id
)
SELECT
  s.household_id,
  s.first_purchase_date,
  s.last_purchase_date,
  h.household_id IS NOT NULL AS has_demographics,
  COALESCE(h.age, 'Unknown') AS age,
  COALESCE(h.age_order, 99) AS age_order,
  COALESCE(h.income, 'Unknown') AS income,
  COALESCE(h.income_order, 99) AS income_order,
  COALESCE(h.income_band, 'Unknown') AS income_band,
  COALESCE(h.home_ownership, 'Unknown') AS home_ownership,
  COALESCE(h.marital_status, 'Unknown') AS marital_status,
  COALESCE(h.household_size, 'Unknown') AS household_size,
  COALESCE(h.household_comp, 'Unknown') AS household_comp,
  COALESCE(h.kids_count, 'Unknown') AS kids_count,
  COALESCE(t.campaigns_received, 0) AS campaigns_received
FROM shoppers s
LEFT JOIN stg_households h USING (household_id)
LEFT JOIN targeted t USING (household_id);

-- One row per transaction line with a known product. Orphan lines are quarantined.
CREATE OR REPLACE TABLE fct_sales AS
SELECT
  business_date,
  household_id,
  store_id,
  basket_id,
  product_id,
  -- Fuel quantity is not a unit count; NULL keeps it out of unit metrics.
  CASE WHEN is_fuel THEN NULL ELSE quantity END AS units,
  sales_value,
  retail_disc,
  coupon_disc,
  coupon_match_disc,
  -- Shelf price before loyalty and retailer coupon-match discounts.
  sales_value + retail_disc + coupon_match_disc AS gross_sales,
  is_fuel,
  is_non_merch,
  NOT is_fuel AND NOT is_non_merch AS is_merch
FROM stg_transactions
WHERE NOT is_orphan_product;

CREATE OR REPLACE TABLE quarantine_transactions AS
SELECT *, 'product_id not in product master' AS reason
FROM stg_transactions
WHERE is_orphan_product;

-- One row per basket (shopping trip), merchandise only.
CREATE OR REPLACE TABLE fct_baskets AS
SELECT
  basket_id,
  ANY_VALUE(household_id) AS household_id,
  ANY_VALUE(store_id) AS store_id,
  MIN(business_date) AS business_date,
  COUNT(*) AS lines,
  SUM(units) AS units,
  SUM(sales_value) AS sales_value,
  SUM(gross_sales) AS gross_sales,
  SUM(retail_disc + coupon_disc + coupon_match_disc) AS total_discount
FROM fct_sales
WHERE is_merch
GROUP BY basket_id;

-- One row per campaign x targeted household.
CREATE OR REPLACE TABLE fct_campaign_targets AS
SELECT t.campaign_id, t.household_id, c.campaign_type, c.start_date, c.end_date
FROM stg_campaign_targets t
JOIN stg_campaigns c USING (campaign_id);

-- One row per coupon redemption.
CREATE OR REPLACE TABLE fct_coupon_redemptions AS
SELECT r.*, c.campaign_type
FROM stg_coupon_redemptions r
JOIN stg_campaigns c USING (campaign_id);

-- One row per product x store x week with promotion placement.
CREATE OR REPLACE TABLE fct_promotions AS
SELECT * FROM stg_promotions;

CREATE OR REPLACE TABLE dim_campaign AS
SELECT * FROM stg_campaigns;

CREATE OR REPLACE TABLE dim_coupon AS
SELECT * FROM stg_coupons;
