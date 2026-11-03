-- One row per basket (shopping trip), merchandise lines only.

select
    basket_id,
    any_value(household_id)                                as household_id,
    any_value(store_id)                                    as store_id,
    min(business_date)                                     as business_date,
    count(*)                                               as lines,
    sum(units)                                             as units,
    sum(sales_value)                                       as sales_value,
    sum(gross_sales)                                       as gross_sales,
    sum(retail_disc + coupon_disc + coupon_match_disc)     as total_discount
from {{ ref('fct_sales') }}
where is_merch
group by basket_id
