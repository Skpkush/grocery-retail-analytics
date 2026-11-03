-- One row per product. Blank categories become UNCATEGORIZED so they still group.

with source as (
    select * from {{ source('completejourney', 'products') }}
)

select
    cast(product_id as varchar)                                          as product_id,
    cast(manufacturer_id as varchar)                                     as manufacturer_id,
    trim(department)                                                     as department,
    brand,
    coalesce(nullif(trim(product_category), ''), 'UNCATEGORIZED')        as product_category,
    coalesce(nullif(trim(product_type), ''), 'UNCATEGORIZED')            as product_type,
    nullif(trim(package_size), '')                                       as package_size,
    -- Fuel lines record gallons or odometer readings in quantity.
    coalesce(product_type like 'GASOLINE%', false)                       as is_fuel,
    -- Gift card activations are a liability, not revenue; coupon, postal and
    -- charity lines are not merchandise either.
    coalesce(
        product_type like '%GIFT CARD%'
        or department in ('COUPON', 'POSTAL CENTER', 'CHARITABLE CONT'),
        false
    )                                                                    as is_non_merch
from source
