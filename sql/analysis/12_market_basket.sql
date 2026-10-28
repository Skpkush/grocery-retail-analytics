-- Market basket affinity between product categories (top 40 categories by baskets).
-- support = share of baskets with both; lift > 1 means bought together more than chance.
WITH basket_cat AS (
  SELECT DISTINCT s.basket_id, p.product_category
  FROM fct_sales s
  JOIN dim_product p ON p.product_id = s.product_id
  WHERE s.is_merch AND p.product_category <> 'UNCATEGORIZED'
),
top_cat AS (
  SELECT product_category, COUNT(*) AS baskets
  FROM basket_cat GROUP BY 1 ORDER BY baskets DESC LIMIT 40
),
filtered AS (
  SELECT bc.* FROM basket_cat bc JOIN top_cat USING (product_category)
),
total AS (SELECT COUNT(DISTINCT basket_id) AS n FROM fct_baskets),
pairs AS (
  SELECT a.product_category AS category_a, b.product_category AS category_b, COUNT(*) AS together
  FROM filtered a
  JOIN filtered b ON a.basket_id = b.basket_id AND a.product_category < b.product_category
  GROUP BY ALL
)
SELECT
  pairs.category_a,
  pairs.category_b,
  pairs.together AS baskets_together,
  ROUND(100.0 * pairs.together / total.n, 2) AS support_pct,
  ROUND(100.0 * pairs.together / ta.baskets, 1) AS confidence_a_to_b_pct,
  ROUND(pairs.together * total.n / (ta.baskets * tb.baskets)::DOUBLE, 2) AS lift
FROM pairs
CROSS JOIN total
JOIN top_cat ta ON ta.product_category = pairs.category_a
JOIN top_cat tb ON tb.product_category = pairs.category_b
WHERE pairs.together >= 500
ORDER BY lift DESC
LIMIT 20;
