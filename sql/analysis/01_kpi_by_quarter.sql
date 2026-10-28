-- Headline KPIs by quarter, 2017.
-- Business question: "How is the business trending through the year?"
SELECT
  d.quarter_name AS quarter,
  ROUND(SUM(s.sales_value), 2) AS net_sales,
  COUNT(DISTINCT s.basket_id) AS baskets,
  COUNT(DISTINCT s.household_id) AS households,
  ROUND(SUM(s.sales_value) / NULLIF(COUNT(DISTINCT s.basket_id), 0), 2) AS avg_basket_value,
  ROUND(SUM(s.units) / NULLIF(COUNT(DISTINCT s.basket_id), 0), 2) AS units_per_basket,
  ROUND(100.0 * SUM(s.retail_disc + s.coupon_match_disc) / NULLIF(SUM(s.gross_sales), 0), 1)
    AS discount_rate_pct,
  ROUND(100.0 * SUM(CASE WHEN p.brand = 'Private' THEN s.sales_value END)
        / NULLIF(SUM(s.sales_value), 0), 1) AS private_label_share_pct
FROM fct_sales s
JOIN dim_date d ON d.date_key = s.business_date
JOIN dim_product p ON p.product_id = s.product_id
WHERE s.is_merch
GROUP BY d.quarter_number, d.quarter_name
ORDER BY d.quarter_number;
