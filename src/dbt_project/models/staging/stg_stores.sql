-- Staging model: stg_stores
-- Standardizes store master metadata and catchment definitions.

WITH source AS (
    SELECT * FROM read_json_auto('data/metadata/stores_metadata.json')
)
SELECT
    store_id,
    store_name,
    status AS store_status,
    category AS store_category,
    latitude AS store_latitude,
    longitude AS store_longitude,
    daily_target_revenue,
    description
FROM source
