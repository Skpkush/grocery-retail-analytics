{{ config(
    severity='warn',
    fail_calc='coalesce(sum(extra_copies), 0)',
    meta={'dq_check': 'Exact duplicate transaction lines',
          'description': 'Identical lines are legitimate (same item scanned twice) but are tracked.'}
) }}

-- Groups of identical transaction lines; extra_copies = copies beyond the first.

select
    household_id, store_id, basket_id, product_id, units,
    sales_value, retail_disc, coupon_disc,
    count(*) - 1 as extra_copies
from {{ ref('fct_sales') }}
group by all
having count(*) > 1
