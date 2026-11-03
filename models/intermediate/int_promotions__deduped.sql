-- One row per product x store x week. The source lists 12,785 keys more than
-- once with different placements: a key counts as promoted if any listing says
-- so, and the lowest placement code is kept.

select
    product_id,
    store_id,
    week,
    min(display_location) filter (where display_location <> '0') as display_location,
    min(mailer_location) filter (where mailer_location <> '0')   as mailer_location,
    bool_or(display_location <> '0')                              as on_display,
    bool_or(mailer_location <> '0')                               as in_mailer,
    count(*)                                                      as source_rows
from {{ ref('stg_completejourney__promotions') }}
group by product_id, store_id, week
