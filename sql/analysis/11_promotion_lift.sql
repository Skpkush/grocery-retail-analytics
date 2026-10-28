-- In-store display and weekly mailer lift.
-- The promotions feed lists only promoted product x store x weeks, so the
-- baseline is the same product in the same store in weeks it was NOT listed.
-- Comparing within each product x store pair controls for product and store.
-- Partial weeks 1 and 53 are excluded; a week with no sale counts as $0.
WITH weekly_sales AS (
  SELECT s.product_id, s.store_id, d.retail_week AS week, SUM(s.sales_value) AS sales
  FROM fct_sales s
  JOIN dim_date d ON d.date_key = s.business_date
  WHERE s.is_merch AND d.retail_week BETWEEN 2 AND 52
  GROUP BY ALL
),
pairs AS (  -- product x store pairs that were promoted at least once and sold at least once
  SELECT DISTINCT product_id, store_id FROM fct_promotions
  INTERSECT
  SELECT DISTINCT product_id, store_id FROM weekly_sales
),
grid AS (
  SELECT pairs.product_id, pairs.store_id, w.week
  FROM pairs CROSS JOIN range(2, 53) AS w(week)
),
panel AS (
  SELECT
    g.product_id,
    g.store_id,
    CASE
      WHEN pr.on_display AND pr.in_mailer THEN 'Display + mailer'
      WHEN pr.on_display THEN 'Display only'
      WHEN pr.in_mailer THEN 'Mailer only'
      ELSE 'Not promoted'
    END AS promo_state,
    COALESCE(ws.sales, 0) AS sales
  FROM grid g
  LEFT JOIN fct_promotions pr USING (product_id, store_id, week)
  LEFT JOIN weekly_sales ws USING (product_id, store_id, week)
),
pair_state AS (
  SELECT product_id, store_id, promo_state, AVG(sales) AS avg_sales, COUNT(*) AS weeks
  FROM panel
  GROUP BY ALL
),
paired AS (
  SELECT p.promo_state, p.avg_sales, b.avg_sales AS baseline_sales, p.weeks
  FROM pair_state p
  JOIN pair_state b
    ON b.product_id = p.product_id AND b.store_id = p.store_id AND b.promo_state = 'Not promoted'
  WHERE p.promo_state <> 'Not promoted'
)
SELECT
  promo_state,
  COUNT(*) AS product_store_pairs,
  SUM(weeks) AS promoted_weeks,
  ROUND(AVG(baseline_sales), 2) AS avg_baseline_weekly_sales,
  ROUND(AVG(avg_sales), 2) AS avg_promoted_weekly_sales,
  ROUND(100.0 * (SUM(avg_sales) / NULLIF(SUM(baseline_sales), 0) - 1), 1) AS sales_lift_pct
FROM paired
GROUP BY promo_state
ORDER BY sales_lift_pct DESC;
