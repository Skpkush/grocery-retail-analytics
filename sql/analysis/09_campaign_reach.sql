-- Campaign reach and coupon redemption by campaign type.
-- Business question: "Which campaign formats get customers to act?"
WITH per_campaign AS (
  SELECT
    c.campaign_id,
    c.campaign_type,
    c.duration_days,
    (SELECT COUNT(*) FROM fct_campaign_targets t WHERE t.campaign_id = c.campaign_id) AS households_targeted,
    (SELECT COUNT(DISTINCT r.household_id) FROM fct_coupon_redemptions r
      WHERE r.campaign_id = c.campaign_id) AS households_redeeming,
    (SELECT COUNT(*) FROM fct_coupon_redemptions r WHERE r.campaign_id = c.campaign_id) AS redemptions,
    (SELECT COUNT(DISTINCT coupon_upc) FROM dim_coupon k WHERE k.campaign_id = c.campaign_id) AS coupons_offered
  FROM dim_campaign c
)
SELECT
  campaign_type,
  COUNT(*) AS campaigns,
  ROUND(AVG(duration_days), 0) AS avg_duration_days,
  SUM(households_targeted) AS households_targeted,
  ROUND(AVG(households_targeted), 0) AS avg_households_per_campaign,
  SUM(redemptions) AS redemptions,
  ROUND(100.0 * SUM(households_redeeming) / NULLIF(SUM(households_targeted), 0), 1)
    AS household_redemption_rate_pct,
  ROUND(AVG(coupons_offered), 0) AS avg_coupons_offered
FROM per_campaign
GROUP BY campaign_type
ORDER BY campaign_type;
