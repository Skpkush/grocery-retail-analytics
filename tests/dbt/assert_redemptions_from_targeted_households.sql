{{ config(meta={'dq_check': 'Redemptions come from targeted households',
                'description': 'A household can only redeem a coupon from a campaign it received.'}) }}

-- Redemptions by a household the campaign did not target.

select r.*
from {{ ref('fct_coupon_redemptions') }} as r
anti join {{ ref('fct_campaign_targets') }} as t
    using (campaign_id, household_id)
