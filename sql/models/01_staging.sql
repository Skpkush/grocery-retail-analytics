-- Staging: type, rename and flag the landed source data. No rows are dropped
-- here; every exclusion decision is a flag, so it can be audited and counted.

CREATE OR REPLACE TABLE stg_products AS
SELECT
  product_id,
  manufacturer_id,
  TRIM(department) AS department,
  brand,
  COALESCE(NULLIF(TRIM(product_category), ''), 'UNCATEGORIZED') AS product_category,
  COALESCE(NULLIF(TRIM(product_type), ''), 'UNCATEGORIZED') AS product_type,
  NULLIF(TRIM(package_size), '') AS package_size,
  -- Fuel lines record gallons/odometer readings in quantity, so unit metrics exclude them.
  product_type LIKE 'GASOLINE%' AS is_fuel,
  -- Gift card activations are a liability, not revenue; coupon/postal lines are not merchandise.
  (product_type LIKE '%GIFT CARD%'
   OR department IN ('COUPON', 'POSTAL CENTER', 'CHARITABLE CONT')) AS is_non_merch
FROM landing_products;

CREATE OR REPLACE TABLE stg_transactions AS
SELECT
  t.household_id,
  t.store_id,
  t.basket_id,
  t.product_id,
  t.quantity,
  t.sales_value,
  t.retail_disc,
  t.coupon_disc,
  t.coupon_match_disc,
  t.week AS source_week,
  t.transaction_timestamp,  -- UTC
  -- Source timestamps are UTC. The retailer's weeks start at local midnight US
  -- Eastern (05:00 UTC in winter, 04:00 UTC under daylight saving), so trading
  -- dates and shopping hours use Eastern local time. A sale at 04:01 UTC on
  -- 1 Jan 2018 is 23:01 on 31 Dec 2017 in the store. The quality gate checks this
  -- reproduces the retailer's own week number on every row.
  timezone('America/New_York', timezone('UTC', t.transaction_timestamp)) AS local_timestamp,
  CAST(timezone('America/New_York', timezone('UTC', t.transaction_timestamp)) AS DATE)
    AS business_date,
  p.product_id IS NULL AS is_orphan_product,
  COALESCE(p.is_fuel, FALSE) AS is_fuel,
  COALESCE(p.is_non_merch, FALSE) AS is_non_merch
FROM landing_transactions t
LEFT JOIN stg_products p ON p.product_id = t.product_id;

CREATE OR REPLACE TABLE stg_households AS
SELECT
  household_id,
  age,
  CASE age WHEN '19-24' THEN 1 WHEN '25-34' THEN 2 WHEN '35-44' THEN 3
           WHEN '45-54' THEN 4 WHEN '55-64' THEN 5 WHEN '65+' THEN 6 END AS age_order,
  income,
  CASE income
    WHEN 'Under 15K' THEN 1 WHEN '15-24K' THEN 2 WHEN '25-34K' THEN 3 WHEN '35-49K' THEN 4
    WHEN '50-74K' THEN 5 WHEN '75-99K' THEN 6 WHEN '100-124K' THEN 7 WHEN '125-149K' THEN 8
    WHEN '150-174K' THEN 9 WHEN '175-199K' THEN 10 WHEN '200-249K' THEN 11 WHEN '250K+' THEN 12
  END AS income_order,
  -- Coarser bands keep segment sizes large enough to compare.
  CASE
    WHEN income IN ('Under 15K', '15-24K', '25-34K') THEN 'Under 35K'
    WHEN income IN ('35-49K', '50-74K') THEN '35-74K'
    WHEN income IN ('75-99K', '100-124K') THEN '75-124K'
    ELSE '125K+'
  END AS income_band,
  COALESCE(home_ownership, 'Unknown') AS home_ownership,
  COALESCE(marital_status, 'Unknown') AS marital_status,
  household_size,
  household_comp,
  kids_count
FROM landing_demographics;

CREATE OR REPLACE TABLE stg_campaigns AS
SELECT
  d.campaign_id,
  d.campaign_type,
  d.start_date,
  d.end_date,
  DATEDIFF('day', d.start_date, d.end_date) + 1 AS duration_days
FROM landing_campaign_descriptions d;

CREATE OR REPLACE TABLE stg_campaign_targets AS
SELECT DISTINCT campaign_id, household_id FROM landing_campaigns;

-- The source lists 1,623 coupon/product/campaign rows more than once.
CREATE OR REPLACE TABLE stg_coupons AS
SELECT DISTINCT coupon_upc, product_id, campaign_id FROM landing_coupons;

CREATE OR REPLACE TABLE stg_coupon_redemptions AS
SELECT household_id, coupon_upc, campaign_id, redemption_date FROM landing_coupon_redemptions;

-- The source lists only promoted product x store x weeks (no "not promoted"
-- rows), and 12,785 keys appear more than once with different placements. One
-- row per key: promoted if any listing says so; the first placement code is kept.
CREATE OR REPLACE TABLE stg_promotions AS
SELECT
  product_id,
  store_id,
  week,
  MIN(display_location) FILTER (WHERE display_location <> '0') AS display_location,
  MIN(mailer_location) FILTER (WHERE mailer_location <> '0') AS mailer_location,
  BOOL_OR(display_location <> '0') AS on_display,
  BOOL_OR(mailer_location <> '0') AS in_mailer,
  COUNT(*) AS source_rows
FROM landing_promotions
GROUP BY product_id, store_id, week;
