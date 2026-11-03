-- One row per campaign.

select * from {{ ref('stg_completejourney__campaigns') }}
