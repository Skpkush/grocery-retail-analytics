{{
    config(
        materialized='incremental',
        incremental_strategy='delete+insert',
        unique_key='week',
        on_schema_change='fail'
    )
}}

-- One row per product x store x week with its display and mailer placement.
-- The largest table in the warehouse (built from about 20.9M source rows).
-- Incremental by week: each run reloads the latest loaded week onwards, since
-- the most recent week can still receive listings.

select * from {{ ref('int_promotions__deduped') }}
{% if is_incremental() %}
where week >= (select max(week) from {{ this }})
{% endif %}
