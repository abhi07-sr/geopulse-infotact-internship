-- Staging model: stg_gps_pings
-- Cleanses raw mobile GPS ping telemetry, casts timestamps, and extracts temporal features.

WITH source AS (
    SELECT * FROM read_parquet('data/raw/pings.parquet')
)
SELECT
    device_id,
    CAST(timestamp AS TIMESTAMP) AS ping_timestamp,
    EXTRACT(hour FROM CAST(timestamp AS TIMESTAMP)) AS ping_hour,
    EXTRACT(minute FROM CAST(timestamp AS TIMESTAMP)) AS ping_minute,
    latitude,
    longitude,
    accuracy_meters,
    activity_type,
    profile
FROM source
WHERE latitude IS NOT NULL 
  AND longitude IS NOT NULL
  AND accuracy_meters <= 25.0
