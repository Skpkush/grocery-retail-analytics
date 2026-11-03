-- One row per coupon x product x campaign. The source lists 1,623 of these
-- combinations more than once; exact duplicates carry no information.

with source as (
    select * from {{ source('completejourney', 'coupons') }}
)

select distinct
    cast(coupon_upc as varchar)  as coupon_upc,
    cast(product_id as varchar)  as product_id,
    cast(campaign_id as varchar) as campaign_id
from source
