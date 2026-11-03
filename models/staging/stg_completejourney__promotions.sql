-- One row per source promotion listing. Placement code '0' means "not placed".
-- Duplicate keys are merged later, in int_promotions_deduped.

with source as (
    select * from {{ source('completejourney', 'promotions') }}
)

select
    cast(product_id as varchar)        as product_id,
    cast(store_id as varchar)          as store_id,
    cast(week as integer)              as week,
    cast(display_location as varchar)  as display_location,
    cast(mailer_location as varchar)   as mailer_location
from source
