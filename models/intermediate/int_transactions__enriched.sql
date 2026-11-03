-- One row per transaction line, with the product flags attached. Lines whose
-- product is missing from the product master are flagged, not dropped, so the
-- marts can route them to quarantine and the totals still reconcile.

with transactions as (
    select * from {{ ref('stg_completejourney__transactions') }}
),

products as (
    select product_id, is_fuel, is_non_merch
    from {{ ref('stg_completejourney__products') }}
)

select
    t.*,
    p.product_id is null              as is_orphan_product,
    coalesce(p.is_fuel, false)        as is_fuel,
    coalesce(p.is_non_merch, false)   as is_non_merch
from transactions as t
left join products as p
    on p.product_id = t.product_id
