{{ config(
    severity='warn',
    warn_if='>5000',
    meta={'dq_check': 'Zero-quantity merchandise lines',
          'description': 'Kept for sales totals; excluded from unit price calculations.'}
) }}

-- Known source limitation, tracked with a ceiling: warns if it grows past 5,000.

select * from {{ ref('fct_sales') }}
where is_merch and units = 0
