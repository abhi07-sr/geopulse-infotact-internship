-- Fails if any row has more unique visitors than pings.
select * from {{ ref('hourly_footfall') }}
where unique_visitors > ping_count
