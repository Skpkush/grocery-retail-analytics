-- One row per coupon x product x campaign.

select * from {{ ref('stg_completejourney__coupons') }}
