-- Transaction lines whose product_id is not in the product master. Kept here,
-- not deleted, so the source totals still reconcile to the cent.

select
    *,
    'product_id not in product master' as reason
from {{ ref('int_transactions__enriched') }}
where is_orphan_product
