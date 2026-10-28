-- Revenue concentration: what share of sales comes from the best households?
-- Techniques: ROW_NUMBER, rank-based deciles, running cumulative share.
WITH ranked AS (
  SELECT
    household_id,
    SUM(sales_value) AS net_sales,
    ROW_NUMBER() OVER (ORDER BY SUM(sales_value) DESC) AS sales_rank,
    COUNT(*) OVER () AS total_households
  FROM fct_sales
  WHERE is_merch
  GROUP BY household_id
),
deciles AS (
  SELECT
    CAST(CEIL(10.0 * sales_rank / total_households) AS INTEGER) AS decile,
    COUNT(*) AS households,
    SUM(net_sales) AS net_sales
  FROM ranked
  GROUP BY decile
)
SELECT
  decile,
  households,
  ROUND(net_sales, 2) AS net_sales,
  ROUND(100.0 * net_sales / SUM(net_sales) OVER (), 1) AS sales_share_pct,
  ROUND(100.0 * SUM(net_sales) OVER (ORDER BY decile) / SUM(net_sales) OVER (), 1)
    AS cumulative_share_pct
FROM deciles
ORDER BY decile;
