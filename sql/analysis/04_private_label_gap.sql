-- Own-brand opportunity: large categories where private label is under-penetrated.
-- Compares private vs national average unit price, so the price gap is visible.
WITH cat AS (
  SELECT
    p.department,
    p.product_category,
    SUM(s.sales_value) AS net_sales,
    SUM(CASE WHEN p.brand = 'Private' THEN s.sales_value END) AS private_sales,
    SUM(CASE WHEN p.brand = 'Private' THEN s.sales_value END)
      / NULLIF(SUM(CASE WHEN p.brand = 'Private' THEN s.units END), 0) AS private_unit_price,
    SUM(CASE WHEN p.brand = 'National' THEN s.sales_value END)
      / NULLIF(SUM(CASE WHEN p.brand = 'National' THEN s.units END), 0) AS national_unit_price
  FROM fct_sales s
  JOIN dim_product p ON p.product_id = s.product_id
  WHERE s.is_merch AND s.units > 0 AND p.product_category <> 'UNCATEGORIZED'
  GROUP BY p.department, p.product_category
)
SELECT
  department,
  product_category,
  ROUND(net_sales, 2) AS net_sales,
  ROUND(100.0 * COALESCE(private_sales, 0) / net_sales, 1) AS private_label_share_pct,
  ROUND(private_unit_price, 2) AS private_unit_price,
  ROUND(national_unit_price, 2) AS national_unit_price,
  ROUND(100.0 * (1 - private_unit_price / NULLIF(national_unit_price, 0)), 1) AS private_price_gap_pct
FROM cat
WHERE net_sales >= 20000
ORDER BY net_sales DESC
LIMIT 25;
