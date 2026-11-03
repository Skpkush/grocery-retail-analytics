-- One row per transaction line, as in the source. Types are cast explicitly so the
-- Parquet files and the CI sample CSVs produce identical columns.

with source as (
    select * from {{ source('completejourney', 'transactions') }}
),

renamed as (
    select
        cast(household_id as varchar)            as household_id,
        cast(store_id as varchar)                as store_id,
        cast(basket_id as varchar)               as basket_id,
        cast(product_id as varchar)              as product_id,
        cast(quantity as double)                 as quantity,
        cast(sales_value as double)              as sales_value,
        cast(retail_disc as double)              as retail_disc,
        cast(coupon_disc as double)              as coupon_disc,
        cast(coupon_match_disc as double)        as coupon_match_disc,
        cast(week as integer)                    as source_week,
        cast(transaction_timestamp as timestamp) as transaction_timestamp_utc
    from source
)

select
    *,
    -- Stores trade on US Eastern time and the retailer's weeks start at local
    -- midnight, so the trading date comes from Eastern local time. A sale at
    -- 04:01 UTC on 1 Jan 2018 happened at 23:01 on 31 Dec 2017 in the store.
    timezone('America/New_York', timezone('UTC', transaction_timestamp_utc)) as transaction_timestamp_local,
    cast(timezone('America/New_York', timezone('UTC', transaction_timestamp_utc)) as date) as business_date
from renamed
