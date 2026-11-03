-- One row per coupon redemption, with a flag for whether the household bought
-- any product that coupon covers in the look-back window before redeeming.

with redemptions as (
    select
        row_number() over (
            order by redemption_date, household_id, coupon_upc, campaign_id
        ) as redemption_id,
        r.*,
        c.campaign_type
    from {{ ref('stg_completejourney__coupon_redemptions') }} as r
    inner join {{ ref('stg_completejourney__campaigns') }} as c
        using (campaign_id)
),

prior_buys as (
    select distinct r.redemption_id
    from redemptions as r
    inner join {{ ref('stg_completejourney__coupons') }} as c
        on c.coupon_upc = r.coupon_upc
       and c.campaign_id = r.campaign_id
    inner join {{ ref('int_transactions__enriched') }} as s
        on not s.is_orphan_product
       and s.household_id = r.household_id
       and s.product_id = c.product_id
       and s.business_date between r.redemption_date - interval {{ var('habitual_lookback_days') }} day
                               and r.redemption_date - interval 1 day
)

select
    r.*,
    p.redemption_id is not null as has_prior_purchase
from redemptions as r
left join prior_buys as p
    using (redemption_id)
