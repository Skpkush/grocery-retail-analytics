-- One row per coupon redemption, as in the source.

with source as (
    select * from {{ source('completejourney', 'coupon_redemptions') }}
)

select
    cast(household_id as varchar)  as household_id,
    cast(coupon_upc as varchar)    as coupon_upc,
    cast(campaign_id as varchar)   as campaign_id,
    cast(redemption_date as date)  as redemption_date
from source
