-- One row per shopping household (all 2,469). Demographics exist for 801; the
-- rest show 'Unknown' so they stay in every count.

with shoppers as (
    select
        household_id,
        min(business_date) as first_purchase_date,
        max(business_date) as last_purchase_date
    from {{ ref('int_transactions__enriched') }}
    where not is_orphan_product
    group by household_id
),

demographics as (
    select * from {{ ref('stg_completejourney__households') }}
),

targeted as (
    select household_id, count(*) as campaigns_received
    from {{ ref('stg_completejourney__campaign_targets') }}
    group by household_id
)

select
    s.household_id,
    s.first_purchase_date,
    s.last_purchase_date,
    d.household_id is not null              as has_demographics,
    coalesce(d.age, 'Unknown')              as age,
    coalesce(d.age_order, 99)               as age_order,
    coalesce(d.income, 'Unknown')           as income,
    coalesce(d.income_order, 99)            as income_order,
    coalesce(d.income_band, 'Unknown')      as income_band,
    coalesce(d.home_ownership, 'Unknown')   as home_ownership,
    coalesce(d.marital_status, 'Unknown')   as marital_status,
    coalesce(d.household_size, 'Unknown')   as household_size,
    coalesce(d.household_comp, 'Unknown')   as household_comp,
    coalesce(d.kids_count, 'Unknown')       as kids_count,
    coalesce(t.campaigns_received, 0)       as campaigns_received
from shoppers as s
left join demographics as d using (household_id)
left join targeted as t using (household_id)
