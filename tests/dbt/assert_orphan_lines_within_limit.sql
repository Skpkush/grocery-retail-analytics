{{ config(
    severity='warn',
    warn_if='>10000',
    meta={'dq_check': 'Orphan transaction lines (quarantined)',
          'description': 'Lines whose product_id is missing from the product master.'}
) }}

-- Known source limitation, tracked with a ceiling: warns if it grows past 10,000.

select * from {{ ref('quarantine_transactions') }}
