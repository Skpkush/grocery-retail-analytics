{{ config(
    severity='warn',
    warn_if='>1000',
    meta={'dq_check': 'Products without a category',
          'description': 'Shown as UNCATEGORIZED in category views.'}
) }}

-- Known source limitation, tracked with a ceiling: warns if it grows past 1,000.

select * from {{ ref('dim_product') }}
where product_category = 'UNCATEGORIZED'
