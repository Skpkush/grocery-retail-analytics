-- One row per household with merchandise purchases: RFM segment and how much of
-- its spending happens on a loyalty discount (deal segment).

select
    household_id,
    recency_days,
    frequency                       as baskets,
    round(monetary, 2)              as annual_sales,
    round(promo_share, 4)           as promo_share,
    r_score,
    f_score,
    m_score,
    case
        when r_score >= 4 and f_score >= 4 and m_score >= 4 then '1. Champions'
        when r_score >= 3 and f_score >= 3 then '2. Loyal'
        when r_score <= 2 and f_score >= 3 then '3. At risk'
        when r_score >= 4 and f_score <= 2 then '4. New / occasional'
        when r_score <= 2 and f_score <= 2 then '5. Lapsed'
        else '6. Needs attention'
    end                             as rfm_segment,
    case
        when monetary <= 0 or promo_share is null then null
        when promo_share < 0.25 then '1. Full-price (<25% on deal)'
        when promo_share < 0.40 then '2. Balanced (25-40%)'
        when promo_share < 0.55 then '3. Deal-leaning (40-55%)'
        else '4. Deal-dependent (55%+)'
    end                             as deal_segment
from {{ ref('int_households__rfm_scores') }}
