-- Mart Model: fct_hourly_footfall
-- Aggregates hourly footfall traffic, distinct visitors, and pedestrian density per store catchment.

WITH spatial_pings AS (
    SELECT * FROM read_parquet('data/processed/spatial_catchment_pings.parquet')
)
SELECT
    store_id,
    store_name,
    store_status,
    ping_hour AS hour_of_day,
    COUNT(DISTINCT device_id) AS unique_visitors,
    COUNT(*) AS total_pings,
    ROUND(AVG(distance_to_store_m), 2) AS avg_distance_to_store_m,
    ROUND(CAST(COUNT(*) AS DOUBLE) / COUNT(DISTINCT device_id), 2) AS pings_per_visitor_ratio
FROM spatial_pings
GROUP BY 
    store_id,
    store_name,
    store_status,
    ping_hour
ORDER BY 
    store_id,
    ping_hour
