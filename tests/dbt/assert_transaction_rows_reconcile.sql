{{ config(
    fail_calc='coalesce(sum(row_difference), 0)',
    meta={'dq_check': 'Landing rows reconcile to fact + quarantine',
          'description': 'No transaction line may be lost between the source and the warehouse.'}
) }}

-- Source lines must equal fct_sales + quarantine_transactions. Returns the difference, if any.

with counts as (
    select
        (select count(*) from {{ source('completejourney', 'transactions') }}) as source_rows,
        (select count(*) from {{ ref('fct_sales') }})                         as fact_rows,
        (select count(*) from {{ ref('quarantine_transactions') }})           as quarantine_rows
)

select abs(source_rows - fact_rows - quarantine_rows) as row_difference
from counts
where source_rows <> fact_rows + quarantine_rows
