{{ config(meta={'dq_check': 'Derived retail week matches the source week',
                'description': 'The store-local trading date reproduces the retailer week numbers.'}) }}

-- Transaction lines whose derived retail week differs from the week in the source.

select t.basket_id, t.business_date, t.source_week, d.retail_week
from {{ ref('stg_completejourney__transactions') }} as t
inner join {{ ref('dim_date') }} as d
    on d.date_key = t.business_date
where d.retail_week <> t.source_week
