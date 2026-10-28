-- RFM segmentation (Recency, Frequency, Monetary) with NTILE quintiles.
-- Snapshot is the day after the data ends (2018-01-01).
WITH base AS (
  SELECT
    s.household_id,
    DATEDIFF('day', MAX(s.business_date), DATE '2018-01-01') AS recency_days,
    COUNT(DISTINCT s.basket_id) AS frequency,
    SUM(s.sales_value) AS monetary
  FROM fct_sales s
  WHERE s.is_merch
  GROUP BY s.household_id
),
scored AS (
  SELECT
    *,
    NTILE(5) OVER (ORDER BY recency_days DESC) AS r,  -- most recent = 5
    NTILE(5) OVER (ORDER BY frequency) AS f,
    NTILE(5) OVER (ORDER BY monetary) AS m
  FROM base
),
segmented AS (
  SELECT
    *,
    CASE
      WHEN r >= 4 AND f >= 4 AND m >= 4 THEN '1. Champions'
      WHEN r >= 3 AND f >= 3 THEN '2. Loyal'
      WHEN r <= 2 AND f >= 3 THEN '3. At risk'
      WHEN r >= 4 AND f <= 2 THEN '4. New / occasional'
      WHEN r <= 2 AND f <= 2 THEN '5. Lapsed'
      ELSE '6. Needs attention'
    END AS segment
  FROM scored
)
SELECT
  segment,
  COUNT(*) AS households,
  ROUND(AVG(recency_days), 0) AS avg_recency_days,
  ROUND(AVG(frequency), 1) AS avg_baskets,
  ROUND(AVG(monetary), 2) AS avg_annual_sales,
  ROUND(SUM(monetary), 2) AS net_sales,
  ROUND(100.0 * SUM(monetary) / SUM(SUM(monetary)) OVER (), 1) AS sales_share_pct
FROM segmented
GROUP BY segment
ORDER BY segment;
