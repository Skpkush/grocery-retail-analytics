-- Market basket affinity between product categories (top 40 categories by baskets).
-- support = share of baskets with both; lift > 1 means bought together more than chance.
-- Pairs are computed once in mart_basket_affinity.
SELECT category_a, category_b, baskets_together, support_pct, confidence_a_to_b_pct, lift
FROM mart_basket_affinity
ORDER BY lift DESC, baskets_together DESC
LIMIT 20;
