-- When do households shop? Baskets and basket value by day of week and daypart.
-- Business question: "When should we staff up and when should promotions land?"
SELECT
  d.day_of_week,
  d.day_name,
  CASE
    WHEN EXTRACT(hour FROM t.first_ts) < 12 THEN '1. Morning (before 12)'
    WHEN EXTRACT(hour FROM t.first_ts) < 17 THEN '2. Afternoon (12-17)'
    ELSE '3. Evening (17+)'
  END AS daypart,
  COUNT(*) AS baskets,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS basket_share_pct,
  ROUND(AVG(b.sales_value), 2) AS avg_basket_value
FROM fct_baskets b
JOIN (
  -- Store-local (US Eastern) time; source timestamps are UTC.
  SELECT basket_id, MIN(local_timestamp) AS first_ts
  FROM stg_transactions GROUP BY basket_id
) t USING (basket_id)
JOIN dim_date d ON d.date_key = b.business_date
GROUP BY ALL
ORDER BY d.day_of_week, daypart;
