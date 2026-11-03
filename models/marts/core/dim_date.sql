-- One row per calendar day of 2017.

with days as (
    select cast(d as date) as date_day
    from generate_series(
        cast('{{ var("data_start_date") }}' as date),
        cast('{{ var("data_end_date") }}' as date),
        interval 1 day
    ) as g(d)
)

select
    cast(date_day as date)                                                  as date_key,
    -- Retail week 1 is the partial week ending Sunday 1 Jan; weeks start Monday.
    cast(floor(datediff('day', date '2016-12-26', cast(date_day as date)) / 7) + 1 as integer)
                                                                            as retail_week,
    cast(date_trunc('week', date_day) as date)                              as week_start,
    cast(extract(month from date_day) as integer)                           as month_number,
    strftime(date_day, '%b %Y')                                             as month_name,
    cast(extract(quarter from date_day) as integer)                         as quarter_number,
    'Q' || extract(quarter from date_day) || ' ' || extract(year from date_day) as quarter_name,
    isodow(date_day)                                                        as day_of_week,
    strftime(date_day, '%a')                                                as day_name,
    case cast(date_day as date)
        when date '2017-02-05' then 'Super Bowl'
        when date '2017-04-16' then 'Easter'
        when date '2017-05-29' then 'Memorial Day'
        when date '2017-07-04' then 'Independence Day'
        when date '2017-09-04' then 'Labor Day'
        when date '2017-11-23' then 'Thanksgiving'
        when date '2017-12-25' then 'Christmas'
    end                                                                     as holiday_name
from days
