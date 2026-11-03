-- One row per coupon redemption.

select
    r.household_id,
    r.coupon_upc,
    r.campaign_id,
    r.redemption_date,
    c.campaign_type
from {{ ref('stg_completejourney__coupon_redemptions') }} as r
inner join {{ ref('dim_campaign') }} as c
    using (campaign_id)
