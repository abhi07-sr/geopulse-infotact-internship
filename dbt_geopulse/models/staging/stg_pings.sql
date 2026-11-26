select
    device_id,
    ts,
    date_trunc('hour', ts) as hour_ts,
    lat,
    lon,
    geog
from {{ source('raw', 'pings') }}
where device_id is not null
  and lat between -90 and 90
  and lon between -180 and 180
