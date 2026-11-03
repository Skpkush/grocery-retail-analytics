-- One row per coupon redemption. "Habitual" means the household bought a product
-- covered by that coupon in the look-back window before redeeming, so the coupon
-- most likely discounted a purchase that would have happened anyway.
-- Redemptions before 26 Feb 2017 do not have a full look-back window inside the
-- data and are left unscored (is_scored = false).

select
    redemption_id,
    household_id,
    coupon_upc,
    campaign_id,
    campaign_type,
    redemption_date,
    redemption_date >= cast('{{ var("data_start_date") }}' as date)
                       + interval {{ var('habitual_lookback_days') }} day as is_scored,
    has_prior_purchase                                                    as is_habitual
from {{ ref('int_coupon_redemptions__prior_purchases') }}
