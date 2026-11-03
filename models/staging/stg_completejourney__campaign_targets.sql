-- One row per campaign x targeted household.

with source as (
    select * from {{ source('completejourney', 'campaigns') }}
)

select distinct
    cast(campaign_id as varchar)  as campaign_id,
    cast(household_id as varchar) as household_id
from source
