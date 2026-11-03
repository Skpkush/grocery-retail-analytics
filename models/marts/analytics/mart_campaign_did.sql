-- Difference-in-differences by campaign type, as plain 2x2 means.
-- Grain: one row per campaign type x test.
--
--   launch  : change from the pre window to the campaign window
--   placebo : change from the placebo window to the pre window, before any
--             campaign started. A real "effect" here means treated and control
--             households were already on different trends, so the launch
--             estimate cannot be trusted as a campaign effect.
--
-- did_weekly_spend = (treated after - treated before) - (control after - control before).
-- The regression version with campaign fixed effects and household-clustered
-- confidence intervals is in src/retail/stats.py, which reads
-- fct_campaign_spend_panel.

with tests as (
    select 'launch' as test, 'pre' as before_period, 'post' as after_period
    union all
    select 'placebo', 'placebo_pre', 'pre'
),

cell_means as (
    select
        p.campaign_type,
        t.test,
        p.treated,
        avg(case when p.period = t.before_period then p.weekly_spend end) as before_spend,
        avg(case when p.period = t.after_period then p.weekly_spend end)  as after_spend,
        count(distinct p.household_id)                                    as households,
        count(distinct p.campaign_id)                                     as campaigns
    from {{ ref('fct_campaign_spend_panel') }} as p
    inner join tests as t
        on p.period in (t.before_period, t.after_period)
    group by p.campaign_type, t.test, p.treated
)

select
    tr.campaign_type,
    tr.test,
    tr.campaigns,
    tr.households                                         as treated_households,
    co.households                                         as control_households,
    round(tr.before_spend, 2)                             as treated_before_weekly_spend,
    round(tr.after_spend, 2)                              as treated_after_weekly_spend,
    round(co.before_spend, 2)                             as control_before_weekly_spend,
    round(co.after_spend, 2)                              as control_after_weekly_spend,
    round((tr.after_spend - tr.before_spend) - (co.after_spend - co.before_spend), 2)
                                                          as did_weekly_spend
from cell_means as tr
inner join cell_means as co
    on co.campaign_type = tr.campaign_type
   and co.test = tr.test
   and co.treated = 0
where tr.treated = 1
