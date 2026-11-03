{{ config(meta={'dq_check': 'Every shopping household has one segment row',
                'description': 'RFM and deal segments cover each merchandise household exactly once.'}) }}

-- Merchandise households missing from mart_rfm_segments, and segment rows for
-- households with no merchandise purchases. Duplicates are caught by the
-- unique test on mart_rfm_segments.household_id.

with buyers as (
    select distinct household_id from {{ ref('fct_sales') }} where is_merch
),

segments as (
    select household_id from {{ ref('mart_rfm_segments') }}
)

select household_id, 'no segment row' as issue
from buyers anti join segments using (household_id)
union all
select household_id, 'segment without purchases'
from segments anti join buyers using (household_id)
