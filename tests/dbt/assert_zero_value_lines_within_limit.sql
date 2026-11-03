{{ config(
    severity='warn',
    warn_if='>20000',
    meta={'dq_check': 'Zero-value merchandise lines',
          'description': 'Fully discounted or free items.'}
) }}

-- Known source limitation, tracked with a ceiling: warns if it grows past 20,000.

select * from {{ ref('fct_sales') }}
where is_merch and sales_value = 0
