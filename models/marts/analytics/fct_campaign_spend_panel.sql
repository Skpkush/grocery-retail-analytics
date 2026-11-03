-- Household x campaign x period panel for the difference-in-differences test.
-- Grain: one row per campaign x household x period.
--
-- Treated = households targeted by the campaign. Control = households never
-- targeted by any campaign. Periods (8-week windows by default):
--   placebo_pre  16 to 8 weeks before launch   (used only for the placebo test)
--   pre          8 weeks before launch
--   post         the campaign window, cut at the end of the data
-- Campaigns without 16 weeks of history inside the data are left out.
-- weekly_spend = merchandise sales in the window / weeks in the window, with 0
-- for households that bought nothing.

{% set pre_days = var('did_pre_weeks') * 7 %}

with campaigns as (
    select
        campaign_id,
        campaign_type,
        start_date,
        least(end_date, cast('{{ var("data_end_date") }}' as date)) as end_date
    from {{ ref('dim_campaign') }}
    where start_date - interval {{ 2 * pre_days }} day >= cast('{{ var("data_start_date") }}' as date)
      and start_date <= cast('{{ var("data_end_date") }}' as date)
),

windows as (
    select campaign_id, campaign_type, 'placebo_pre' as period,
           cast(start_date - interval {{ 2 * pre_days }} day as date) as window_start,
           cast(start_date - interval {{ pre_days + 1 }} day as date) as window_end
    from campaigns
    union all
    select campaign_id, campaign_type, 'pre',
           cast(start_date - interval {{ pre_days }} day as date),
           cast(start_date - interval 1 day as date)
    from campaigns
    union all
    select campaign_id, campaign_type, 'post', start_date, end_date
    from campaigns
),

never_targeted as (
    select household_id
    from {{ ref('dim_household') }}
    where campaigns_received = 0
),

panel_households as (
    select c.campaign_id, t.household_id, 1 as treated
    from campaigns as c
    inner join {{ ref('fct_campaign_targets') }} as t using (campaign_id)
    inner join {{ ref('dim_household') }} as h using (household_id)
    union all
    select c.campaign_id, n.household_id, 0 as treated
    from campaigns as c
    cross join never_targeted as n
),

daily_spend as (
    select household_id, business_date, sum(sales_value) as sales
    from {{ ref('fct_sales') }}
    where is_merch
    group by household_id, business_date
),

window_spend as (
    select w.campaign_id, w.period, d.household_id, sum(d.sales) as sales
    from windows as w
    inner join daily_spend as d
        on d.business_date between w.window_start and w.window_end
    group by w.campaign_id, w.period, d.household_id
)

select
    w.campaign_id,
    w.campaign_type,
    p.household_id,
    p.treated,
    w.period,
    w.window_start,
    w.window_end,
    (datediff('day', w.window_start, w.window_end) + 1) / 7.0                     as weeks,
    coalesce(s.sales, 0) / ((datediff('day', w.window_start, w.window_end) + 1) / 7.0)
                                                                                  as weekly_spend
from windows as w
inner join panel_households as p
    on p.campaign_id = w.campaign_id
left join window_spend as s
    on s.campaign_id = w.campaign_id
   and s.period = w.period
   and s.household_id = p.household_id
