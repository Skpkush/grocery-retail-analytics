-- One row per surveyed household (801 of 2,469). Ordered codes make the
-- age and income labels sort correctly in charts.

with source as (
    select * from {{ source('completejourney', 'demographics') }}
)

select
    cast(household_id as varchar) as household_id,
    age,
    case age
        when '19-24' then 1 when '25-34' then 2 when '35-44' then 3
        when '45-54' then 4 when '55-64' then 5 when '65+' then 6
    end as age_order,
    income,
    case income
        when 'Under 15K' then 1 when '15-24K' then 2 when '25-34K' then 3 when '35-49K' then 4
        when '50-74K' then 5 when '75-99K' then 6 when '100-124K' then 7 when '125-149K' then 8
        when '150-174K' then 9 when '175-199K' then 10 when '200-249K' then 11 when '250K+' then 12
    end as income_order,
    -- Coarser bands keep each group large enough to compare.
    case
        when income in ('Under 15K', '15-24K', '25-34K') then 'Under 35K'
        when income in ('35-49K', '50-74K') then '35-74K'
        when income in ('75-99K', '100-124K') then '75-124K'
        else '125K+'
    end as income_band,
    coalesce(home_ownership, 'Unknown') as home_ownership,
    coalesce(marital_status, 'Unknown') as marital_status,
    cast(household_size as varchar)     as household_size,
    household_comp,
    cast(kids_count as varchar)         as kids_count
from source
