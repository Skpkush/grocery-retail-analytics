-- Coupon incrementality proxy: was the redeeming household already buying the product?
-- A redemption is "habitual" if the household bought any product covered by that
-- coupon in the 56 days before redeeming. Habitual redemptions are likely
-- subsidised purchases that would have happened anyway.
WITH redemptions AS (
  SELECT ROW_NUMBER() OVER () AS redemption_id, r.*
  FROM fct_coupon_redemptions r
  WHERE r.redemption_date >= DATE '2017-02-26'  -- needs a full 56-day look-back in the data
),
prior AS (
  SELECT DISTINCT r.redemption_id
  FROM redemptions r
  JOIN dim_coupon k ON k.coupon_upc = r.coupon_upc AND k.campaign_id = r.campaign_id
  JOIN fct_sales s
    ON s.household_id = r.household_id
   AND s.product_id = k.product_id
   AND s.business_date BETWEEN r.redemption_date - INTERVAL 56 DAY AND r.redemption_date - INTERVAL 1 DAY
)
SELECT
  r.campaign_type,
  COUNT(*) AS redemptions,
  COUNT(p.redemption_id) AS habitual_redemptions,
  ROUND(100.0 * COUNT(p.redemption_id) / COUNT(*), 1) AS habitual_pct
FROM redemptions r
LEFT JOIN prior p USING (redemption_id)
GROUP BY ROLLUP (r.campaign_type)
ORDER BY r.campaign_type NULLS LAST;
