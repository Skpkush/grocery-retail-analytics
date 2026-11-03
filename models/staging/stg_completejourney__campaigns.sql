-- One row per campaign with its type and date window.

with source as (
    select * from {{ source('completejourney', 'campaign_descriptions') }}
)

select
    cast(campaign_id as varchar)                                 as campaign_id,
    campaign_type,
    cast(start_date as date)                                     as start_date,
    cast(end_date as date)                                       as end_date,
    datediff('day', cast(start_date as date), cast(end_date as date)) + 1 as duration_days
from source
