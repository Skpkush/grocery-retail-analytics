-- RFM segmentation (Recency, Frequency, Monetary) with NTILE quintiles.
-- Scores and segment rules live in mart_household_segments; snapshot 2018-01-01.
SELECT
  rfm_segment AS segment,
  COUNT(*) AS households,
  ROUND(AVG(recency_days), 0) AS avg_recency_days,
  ROUND(AVG(baskets), 1) AS avg_baskets,
  ROUND(AVG(annual_sales), 2) AS avg_annual_sales,
  ROUND(SUM(annual_sales), 2) AS net_sales,
  ROUND(100.0 * SUM(annual_sales) / SUM(SUM(annual_sales)) OVER (), 1) AS sales_share_pct
FROM mart_household_segments
GROUP BY rfm_segment
ORDER BY rfm_segment;
