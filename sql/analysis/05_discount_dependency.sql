-- Deal dependency: how much of each household's spend is bought on discount?
-- Segments households into deal-dependence bands and compares their value.
WITH hh AS (
  SELECT
    s.household_id,
    SUM(s.sales_value) AS net_sales,
    SUM(CASE WHEN s.retail_disc > 0 THEN s.sales_value ELSE 0 END) / NULLIF(SUM(s.sales_value), 0)
      AS promo_share,
    COUNT(DISTINCT s.basket_id) AS baskets
  FROM fct_sales s
  WHERE s.is_merch
  GROUP BY s.household_id
  HAVING SUM(s.sales_value) > 0
)
SELECT
  CASE
    WHEN promo_share < 0.25 THEN '1. Full-price (<25% on deal)'
    WHEN promo_share < 0.40 THEN '2. Balanced (25-40%)'
    WHEN promo_share < 0.55 THEN '3. Deal-leaning (40-55%)'
    ELSE '4. Deal-dependent (55%+)'
  END AS deal_segment,
  COUNT(*) AS households,
  ROUND(AVG(net_sales), 2) AS avg_annual_sales,
  ROUND(AVG(baskets), 1) AS avg_baskets,
  ROUND(SUM(net_sales) / SUM(baskets), 2) AS avg_basket_value,
  ROUND(100.0 * SUM(net_sales) / SUM(SUM(net_sales)) OVER (), 1) AS sales_share_pct
FROM hh
GROUP BY deal_segment
ORDER BY deal_segment;
