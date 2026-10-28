-- Weekly sales trend with week-over-week growth and a 4-week rolling average.
-- Techniques: LAG and a framed AVG window; holiday weeks flagged for context.
WITH weekly AS (
  SELECT
    d.retail_week,
    MIN(d.week_start) AS week_start,
    STRING_AGG(DISTINCT d.holiday_name, ', ') AS holidays,
    SUM(s.sales_value) AS net_sales,
    COUNT(DISTINCT s.basket_id) AS baskets
  FROM fct_sales s
  JOIN dim_date d ON d.date_key = s.business_date
  WHERE s.is_merch
  GROUP BY d.retail_week
)
SELECT
  retail_week,
  week_start,
  holidays,
  ROUND(net_sales, 2) AS net_sales,
  baskets,
  ROUND(100.0 * (net_sales - LAG(net_sales) OVER w) / NULLIF(LAG(net_sales) OVER w, 0), 1)
    AS wow_growth_pct,
  ROUND(AVG(net_sales) OVER (w ROWS BETWEEN 3 PRECEDING AND CURRENT ROW), 2) AS rolling_4w_sales
FROM weekly
WINDOW w AS (ORDER BY retail_week)
ORDER BY retail_week;
