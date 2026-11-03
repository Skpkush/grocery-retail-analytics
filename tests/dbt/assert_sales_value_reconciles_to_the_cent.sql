{{ config(
    fail_calc='coalesce(sum(cents_difference), 0)',
    meta={'dq_check': 'Sales value reconciles to the cent',
          'description': 'Total sales across fact and quarantine equals the source total.'}
) }}

-- Returns the difference in cents between the source total and fact + quarantine, if any.

with totals as (
    select
        (select sum(sales_value) from {{ source('completejourney', 'transactions') }})    as source_sales,
        (select sum(sales_value) from {{ ref('fct_sales') }})                            as fact_sales,
        (select coalesce(sum(sales_value), 0) from {{ ref('quarantine_transactions') }}) as quarantine_sales
),

difference as (
    select cast(round(100 * abs(source_sales - fact_sales - quarantine_sales)) as bigint) as cents_difference
    from totals
)

select cents_difference
from difference
where cents_difference <> 0
