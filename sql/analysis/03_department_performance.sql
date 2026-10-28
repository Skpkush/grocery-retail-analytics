-- Department scorecard: size, reach, discount dependence and own-brand share.
-- Business question: "Which departments matter, and how are they sold?"
WITH dept AS (
  SELECT
    p.department,
    SUM(s.sales_value) AS net_sales,
    COUNT(DISTINCT s.household_id) AS buying_households,
    SUM(s.retail_disc + s.coupon_match_disc) AS retailer_discount,
    SUM(s.gross_sales) AS gross_sales,
    SUM(CASE WHEN p.brand = 'Private' THEN s.sales_value END) AS private_sales
  FROM fct_sales s
  JOIN dim_product p ON p.product_id = s.product_id
  WHERE s.is_merch
  GROUP BY p.department
)
SELECT
  department,
  ROUND(net_sales, 2) AS net_sales,
  ROUND(100.0 * net_sales / SUM(net_sales) OVER (), 1) AS sales_share_pct,
  ROUND(100.0 * buying_households / (SELECT COUNT(*) FROM dim_household), 1) AS penetration_pct,
  ROUND(100.0 * retailer_discount / NULLIF(gross_sales, 0), 1) AS discount_rate_pct,
  ROUND(100.0 * COALESCE(private_sales, 0) / NULLIF(net_sales, 0), 1) AS private_label_share_pct
FROM dept
WHERE net_sales > 1000
ORDER BY net_sales DESC;
