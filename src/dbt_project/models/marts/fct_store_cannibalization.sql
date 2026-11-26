-- Mart Model: fct_store_cannibalization
-- Quantifies cross-store device interception and computes the Cannibalization Index.

WITH store_devices AS (
    SELECT DISTINCT
        store_id,
        device_id
    FROM read_parquet('data/processed/spatial_catchment_pings.parquet')
),
store_totals AS (
    SELECT
        store_id,
        COUNT(DISTINCT device_id) AS total_unique_devices
    FROM store_devices
    GROUP BY store_id
),
cross_intersections AS (
    SELECT
        a.store_id AS existing_store_id,
        b.store_id AS candidate_store_id,
        COUNT(DISTINCT a.device_id) AS overlapping_devices
    FROM store_devices a
    JOIN store_devices b ON a.device_id = b.device_id
    WHERE a.store_id != b.store_id
    GROUP BY a.store_id, b.store_id
)
SELECT
    x.existing_store_id,
    s1.store_name AS existing_store_name,
    x.candidate_store_id,
    s2.store_name AS candidate_store_name,
    s2.status AS candidate_store_status,
    tot.total_unique_devices AS existing_store_total_devices,
    x.overlapping_devices,
    ROUND((CAST(x.overlapping_devices AS DOUBLE) / tot.total_unique_devices) * 100.0, 2) AS cannibalization_pct,
    CASE
        WHEN (CAST(x.overlapping_devices AS DOUBLE) / tot.total_unique_devices) * 100.0 >= 30.0 
            THEN 'SEVERE_CANNIBALIZATION_RISK'
        WHEN (CAST(x.overlapping_devices AS DOUBLE) / tot.total_unique_devices) * 100.0 >= 15.0 
            THEN 'MODERATE_OVERLAP'
        ELSE 'LOW_OVERLAP_INDEPENDENT_CAPTURE'
    END AS risk_classification,
    CASE
        WHEN (CAST(x.overlapping_devices AS DOUBLE) / tot.total_unique_devices) * 100.0 >= 30.0 
            THEN 'REJECT_LOCATION'
        ELSE 'PROCEED_WITH_FURTHER_ANALYSIS'
    END AS real_estate_recommendation
FROM cross_intersections x
JOIN store_totals tot ON x.existing_store_id = tot.store_id
JOIN read_json_auto('data/metadata/stores_metadata.json') s1 ON x.existing_store_id = s1.store_id
JOIN read_json_auto('data/metadata/stores_metadata.json') s2 ON x.candidate_store_id = s2.store_id
ORDER BY cannibalization_pct DESC
