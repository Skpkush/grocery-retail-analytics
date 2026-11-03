{{ config(
    severity='warn',
    warn_if='>2000',
    meta={'dq_check': 'Households without demographics',
          'description': 'Demographic analysis covers surveyed households only.'}
) }}

-- Known source limitation, tracked with a ceiling: warns if it grows past 2,000.

select * from {{ ref('dim_household') }}
where not has_demographics
