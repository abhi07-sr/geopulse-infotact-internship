-- Unique devices and pings within the catchment radius of each store, per hour.
select
    s.store_id,
    s.store_name,
    p.hour_ts,
    count(distinct p.device_id) as unique_visitors,
    count(*)                    as ping_count
from {{ ref('stg_pings') }} p
join {{ ref('stg_stores') }} s
  on st_dwithin(p.geog, s.geog, {{ var('catchment_m') }})
group by 1, 2, 3
