-- Segments and derived facts: defined once here, used by the SQL library,
-- the Streamlit app and Power BI, so a segment means the same thing everywhere.

-- One row per household with merchandise purchases: RFM and deal-dependence segments.
CREATE OR REPLACE TABLE mart_household_segments AS
WITH base AS (
  SELECT
    s.household_id,
    DATEDIFF('day', MAX(s.business_date), DATE '2018-01-01') AS recency_days,
    COUNT(DISTINCT s.basket_id) AS frequency,
    SUM(s.sales_value) AS monetary,
    SUM(CASE WHEN s.retail_disc > 0 THEN s.sales_value ELSE 0 END) / NULLIF(SUM(s.sales_value), 0)
      AS promo_share
  FROM fct_sales s
  WHERE s.is_merch
  GROUP BY s.household_id
),
scored AS (
  SELECT
    *,
    -- household_id breaks ties so scores are identical on every run; without it,
    -- NTILE assigns tied households to quintiles arbitrarily.
    NTILE(5) OVER (ORDER BY recency_days DESC, household_id) AS r_score,  -- most recent = 5
    NTILE(5) OVER (ORDER BY frequency, household_id) AS f_score,
    NTILE(5) OVER (ORDER BY monetary, household_id) AS m_score
  FROM base
)
SELECT
  household_id,
  recency_days,
  frequency AS baskets,
  ROUND(monetary, 2) AS annual_sales,
  ROUND(promo_share, 4) AS promo_share,
  r_score, f_score, m_score,
  CASE
    WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN '1. Champions'
    WHEN r_score >= 3 AND f_score >= 3 THEN '2. Loyal'
    WHEN r_score <= 2 AND f_score >= 3 THEN '3. At risk'
    WHEN r_score >= 4 AND f_score <= 2 THEN '4. New / occasional'
    WHEN r_score <= 2 AND f_score <= 2 THEN '5. Lapsed'
    ELSE '6. Needs attention'
  END AS rfm_segment,
  CASE
    WHEN monetary <= 0 OR promo_share IS NULL THEN NULL
    WHEN promo_share < 0.25 THEN '1. Full-price (<25% on deal)'
    WHEN promo_share < 0.40 THEN '2. Balanced (25-40%)'
    WHEN promo_share < 0.55 THEN '3. Deal-leaning (40-55%)'
    ELSE '4. Deal-dependent (55%+)'
  END AS deal_segment
FROM scored;

-- One row per coupon redemption, flagged "habitual" when the household bought any
-- product covered by that coupon in the 56 days before redeeming. Redemptions
-- before 26 Feb 2017 lack a full look-back and are not scored (is_scored = FALSE).
CREATE OR REPLACE TABLE mart_coupon_redemptions AS
WITH redemptions AS (
  SELECT ROW_NUMBER() OVER (ORDER BY redemption_date, household_id, coupon_upc, campaign_id)
           AS redemption_id, r.*
  FROM fct_coupon_redemptions r
),
prior AS (
  SELECT DISTINCT r.redemption_id
  FROM redemptions r
  JOIN dim_coupon k ON k.coupon_upc = r.coupon_upc AND k.campaign_id = r.campaign_id
  JOIN fct_sales s
    ON s.household_id = r.household_id
   AND s.product_id = k.product_id
   AND s.business_date BETWEEN r.redemption_date - INTERVAL 56 DAY AND r.redemption_date - INTERVAL 1 DAY
)
SELECT
  r.redemption_id,
  r.household_id,
  r.coupon_upc,
  r.campaign_id,
  r.campaign_type,
  r.redemption_date,
  r.redemption_date >= DATE '2017-02-26' AS is_scored,
  p.redemption_id IS NOT NULL AS is_habitual
FROM redemptions r
LEFT JOIN prior p USING (redemption_id);

-- Category pairs bought in the same basket (top 40 categories by basket count).
-- support = share of all baskets; lift > 1 = bought together more than chance.
CREATE OR REPLACE TABLE mart_basket_affinity AS
WITH basket_cat AS (
  SELECT DISTINCT s.basket_id, p.product_category
  FROM fct_sales s
  JOIN dim_product p ON p.product_id = s.product_id
  WHERE s.is_merch AND p.product_category <> 'UNCATEGORIZED'
),
top_cat AS (
  SELECT product_category, COUNT(*) AS baskets
  FROM basket_cat GROUP BY 1 ORDER BY baskets DESC, product_category LIMIT 40
),
filtered AS (SELECT bc.* FROM basket_cat bc JOIN top_cat USING (product_category)),
total AS (SELECT COUNT(DISTINCT basket_id) AS n FROM fct_baskets),
pairs AS (
  SELECT a.product_category AS category_a, b.product_category AS category_b, COUNT(*) AS together
  FROM filtered a
  JOIN filtered b ON a.basket_id = b.basket_id AND a.product_category < b.product_category
  GROUP BY ALL
)
SELECT
  pairs.category_a,
  pairs.category_b,
  pairs.together AS baskets_together,
  ROUND(100.0 * pairs.together / total.n, 2) AS support_pct,
  ROUND(100.0 * pairs.together / ta.baskets, 1) AS confidence_a_to_b_pct,
  ROUND(pairs.together * total.n / (ta.baskets * tb.baskets)::DOUBLE, 2) AS lift
FROM pairs
CROSS JOIN total
JOIN top_cat ta ON ta.product_category = pairs.category_a
JOIN top_cat tb ON tb.product_category = pairs.category_b
WHERE pairs.together >= 500;
