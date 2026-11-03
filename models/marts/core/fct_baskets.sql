-- One row per basket (shopping trip), merchandise lines only.

with merch_lines as (
    select * from {{ ref('fct_sales') }}
    where is_merch
),

basket_start as (
    -- Earliest store-local timestamp of any line in the basket.
    select basket_id, min(transaction_timestamp_local) as basket_started_at_local
    from {{ ref('int_transactions__enriched') }}
    group by basket_id
)

select
    l.basket_id,
    any_value(l.household_id)                                    as household_id,
    any_value(l.store_id)                                        as store_id,
    min(l.business_date)                                         as business_date,
    any_value(b.basket_started_at_local)                         as basket_started_at_local,
    count(*)                                                     as lines,
    sum(l.units)                                                 as units,
    sum(l.sales_value)                                           as sales_value,
    sum(l.gross_sales)                                           as gross_sales,
    sum(l.retail_disc + l.coupon_disc + l.coupon_match_disc)     as total_discount
from merch_lines as l
left join basket_start as b
    using (basket_id)
group by l.basket_id
