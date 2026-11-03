-- One row per campaign x targeted household.

select
    t.campaign_id,
    t.household_id,
    c.campaign_type,
    c.start_date,
    c.end_date
from {{ ref('stg_completejourney__campaign_targets') }} as t
inner join {{ ref('dim_campaign') }} as c
    using (campaign_id)
