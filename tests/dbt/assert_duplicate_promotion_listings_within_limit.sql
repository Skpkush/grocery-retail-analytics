{{ config(
    severity='warn',
    warn_if='>20000',
    fail_calc='coalesce(sum(source_rows - 1), 0)',
    meta={'dq_check': 'Duplicate promotion listings (merged)',
          'description': 'Product x store x week keys listed more than once in the source; merged to one row.'}
) }}

-- Known source limitation, tracked with a ceiling: warns if it grows past 20,000.

select * from {{ ref('fct_promotions') }}
where source_rows > 1
