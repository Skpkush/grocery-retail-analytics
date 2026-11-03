{{
    config(
        materialized='incremental',
        incremental_strategy='delete+insert',
        unique_key='business_date',
        on_schema_change='fail'
    )
}}

-- One row per transaction line with a known product. Grain: transaction line.
--
-- Incremental strategy: the source has no line-level ID (identical lines are
-- legitimate), so rows cannot be upserted one at a time. Each run reloads whole
-- trading days instead: it selects every line dated on or after
-- (latest date already loaded - lookback days), deletes those dates from the
-- table and inserts them again. Late-arriving lines inside the lookback window
-- are picked up without creating duplicates. `dbt build --full-refresh`
-- rebuilds the table from scratch.

with lines as (
    select * from {{ ref('int_transactions__enriched') }}
    where not is_orphan_product
    {% if is_incremental() %}
      and business_date >= (
          select max(business_date) - interval {{ var('incremental_lookback_days') }} day
          from {{ this }}
      )
    {% endif %}
)

select
    business_date,
    household_id,
    store_id,
    basket_id,
    product_id,
    -- Fuel quantity is gallons or an odometer reading; NULL keeps it out of unit metrics.
    case when is_fuel then null else quantity end         as units,
    sales_value,
    retail_disc,
    coupon_disc,
    coupon_match_disc,
    -- Shelf price before the loyalty and retailer coupon-match discounts.
    -- Manufacturer coupons (coupon_disc) are funded by the manufacturer.
    sales_value + retail_disc + coupon_match_disc         as gross_sales,
    is_fuel,
    is_non_merch,
    not is_fuel and not is_non_merch                      as is_merch
from lines
