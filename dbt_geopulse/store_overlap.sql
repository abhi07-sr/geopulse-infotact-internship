-- Cannibalization: what share of devices that visit store A also visit store B?
-- Computed for the whole day and for the morning commute (06:00-09:59).
with visits_all as (
    select distinct device_id, store_id, 'all_day' as daypart
    from {{ ref('device_store_visits') }}
),
visits_morning as (
    select distinct device_id, store_id, 'morning' as daypart
    from {{ ref('device_store_visits') }}
    where extract(hour from hour_ts) between 6 and 9
),
visits as (
    select * from visits_all
    union all
    select * from visits_morning
),
per_store as (
    select daypart, store_id, count(*) as devices
    from visits
    group by 1, 2
),
pairs as (
    select a.daypart, a.store_id as store_a, b.store_id as store_b, count(*) as shared_devices
    from visits a
    join visits b
      on a.device_id = b.device_id
     and a.daypart = b.daypart
     and a.store_id <> b.store_id
    group by 1, 2, 3
)
select
    p.daypart,
    p.store_a,
    p.store_b,
    s.devices as devices_a,
    p.shared_devices,
    round(100.0 * p.shared_devices / s.devices, 1) as pct_of_a_also_visiting_b
from pairs p
join per_store s
  on s.daypart = p.daypart and s.store_id = p.store_a
