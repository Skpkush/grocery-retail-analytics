-- One row per household with merchandise purchases: recency, frequency and
-- monetary value, each scored into quintiles (5 = best).

with base as (
    select
        household_id,
        datediff('day', max(business_date),
                 cast('{{ var("data_end_date") }}' as date) + interval 1 day) as recency_days,
        count(distinct basket_id)                                            as frequency,
        sum(sales_value)                                                     as monetary,
        sum(case when retail_disc > 0 then sales_value else 0 end)
            / nullif(sum(sales_value), 0)                                    as promo_share
    from {{ ref('int_transactions__enriched') }}
    where not is_orphan_product
      and not is_fuel
      and not is_non_merch
    group by household_id
)

select
    *,
    -- household_id breaks ties so every run gives the same scores; without it
    -- NTILE puts tied households into quintiles arbitrarily.
    ntile(5) over (order by recency_days desc, household_id) as r_score,
    ntile(5) over (order by frequency, household_id)         as f_score,
    ntile(5) over (order by monetary, household_id)          as m_score
from base
