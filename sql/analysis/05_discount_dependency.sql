-- Deal dependency: how much of each household's spend is bought on discount?
-- Segments (defined in mart_household_segments) compared on value and share of sales.
SELECT
  deal_segment,
  COUNT(*) AS households,
  ROUND(AVG(annual_sales), 2) AS avg_annual_sales,
  ROUND(AVG(baskets), 1) AS avg_baskets,
  ROUND(SUM(annual_sales) / SUM(baskets), 2) AS avg_basket_value,
  ROUND(100.0 * SUM(annual_sales) / SUM(SUM(annual_sales)) OVER (), 1) AS sales_share_pct
FROM mart_household_segments
WHERE deal_segment IS NOT NULL
GROUP BY deal_segment
ORDER BY deal_segment;
