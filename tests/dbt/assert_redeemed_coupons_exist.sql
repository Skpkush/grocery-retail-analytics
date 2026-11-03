{{ config(meta={'dq_check': 'Redeemed coupons exist in the coupon master',
                'description': 'Every redemption maps to a coupon.'}) }}

-- Redemptions whose coupon and campaign are not in dim_coupon.

select r.*
from {{ ref('fct_coupon_redemptions') }} as r
anti join {{ ref('dim_coupon') }} as c
    using (coupon_upc, campaign_id)
