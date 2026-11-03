-- Category pairs bought in the same basket, among the 40 categories that appear
-- in the most baskets. One row per category pair seen together in 500+ baskets.
-- support = share of all baskets; lift > 1 = bought together more than chance.

with basket_categories as (
    select distinct s.basket_id, p.product_category
    from {{ ref('fct_sales') }} as s
    inner join {{ ref('dim_product') }} as p
        on p.product_id = s.product_id
    where s.is_merch
      and p.product_category <> 'UNCATEGORIZED'
),

top_categories as (
    select product_category, count(*) as baskets
    from basket_categories
    group by product_category
    order by baskets desc, product_category
    limit 40
),

filtered as (
    select bc.*
    from basket_categories as bc
    inner join top_categories using (product_category)
),

total as (
    select count(distinct basket_id) as n from {{ ref('fct_baskets') }}
),

pairs as (
    select
        a.product_category as category_a,
        b.product_category as category_b,
        count(*)           as together
    from filtered as a
    inner join filtered as b
        on a.basket_id = b.basket_id
       and a.product_category < b.product_category
    group by all
)

select
    pairs.category_a,
    pairs.category_b,
    pairs.together                                                        as baskets_together,
    round(100.0 * pairs.together / total.n, 2)                            as support_pct,
    round(100.0 * pairs.together / ta.baskets, 1)                         as confidence_a_to_b_pct,
    round(pairs.together * total.n / cast(ta.baskets * tb.baskets as double), 2) as lift
from pairs
cross join total
inner join top_categories as ta on ta.product_category = pairs.category_a
inner join top_categories as tb on tb.product_category = pairs.category_b
where pairs.together >= 500
