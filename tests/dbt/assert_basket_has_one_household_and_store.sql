{{ config(meta={'dq_check': 'Basket belongs to one household and store',
                'description': 'A basket is one trip by one household in one store.'}) }}

-- Baskets that appear under more than one household or store.

select basket_id
from {{ ref('fct_sales') }}
group by basket_id
having count(distinct household_id) > 1
    or count(distinct store_id) > 1
