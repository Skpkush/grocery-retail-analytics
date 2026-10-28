-- Spend by income band and household composition (surveyed households only).
-- 801 of 2,469 households have demographics; segment sizes are shown so small
-- cells are not over-read.
WITH hh AS (
  SELECT
    s.household_id,
    SUM(s.sales_value) AS net_sales,
    COUNT(DISTINCT s.basket_id) AS baskets,
    SUM(CASE WHEN p.brand = 'Private' THEN s.sales_value END) AS private_sales
  FROM fct_sales s
  JOIN dim_product p ON p.product_id = s.product_id
  WHERE s.is_merch
  GROUP BY s.household_id
)
SELECT
  h.income_band,
  h.household_comp,
  COUNT(*) AS households,
  ROUND(AVG(hh.net_sales), 2) AS avg_annual_sales,
  ROUND(SUM(hh.net_sales) / SUM(hh.baskets), 2) AS avg_basket_value,
  ROUND(AVG(hh.baskets), 1) AS avg_baskets,
  ROUND(100.0 * SUM(hh.private_sales) / SUM(hh.net_sales), 1) AS private_label_share_pct
FROM hh
JOIN dim_household h USING (household_id)
WHERE h.has_demographics
GROUP BY h.income_band, h.household_comp
ORDER BY MIN(h.income_order), h.household_comp;
