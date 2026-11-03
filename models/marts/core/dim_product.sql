-- One row per product.

select * from {{ ref('stg_completejourney__products') }}
