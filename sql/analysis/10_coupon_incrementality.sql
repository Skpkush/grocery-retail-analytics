-- Coupon incrementality proxy: was the redeeming household already buying the product?
-- A redemption is "habitual" if the household bought any product covered by that
-- coupon in the 56 days before redeeming (flag defined in mart_coupon_redemptions).
-- Habitual redemptions are likely subsidised purchases that would have happened anyway.
SELECT
  CASE WHEN GROUPING(campaign_type) = 1 THEN 'All' ELSE campaign_type END AS campaign_type,
  COUNT(*) AS redemptions,
  COUNT(*) FILTER (WHERE is_habitual) AS habitual_redemptions,
  ROUND(100.0 * COUNT(*) FILTER (WHERE is_habitual) / COUNT(*), 1) AS habitual_pct
FROM mart_coupon_redemptions
WHERE is_scored
GROUP BY ROLLUP (campaign_type)
ORDER BY GROUPING(campaign_type), campaign_type;
