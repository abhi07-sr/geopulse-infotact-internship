-- One row per device, store and hour: which devices were inside which store catchment.
select
    p.device_id,
    s.store_id,
    p.hour_ts,
    count(*) as ping_count
from {{ ref('stg_pings') }} p
join {{ ref('stg_stores') }} s
  on st_dwithin(p.geog, s.geog, {{ var('catchment_m') }})
group by 1, 2, 3
