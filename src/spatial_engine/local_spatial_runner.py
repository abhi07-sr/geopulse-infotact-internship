"""
GeoPulse - High-Performance Local Spatial Engine (DuckDB Geodesic Engine)
Executes spatial catchment joins (500m buffers) and ELT aggregations.
Runs point-in-polygon / distance checks across hundreds of thousands of pings in seconds.
Produces production tables for dbt modeling and Kepler.gl visualization.
"""

import os
import time
import duckdb
import pandas as pd


def run_spatial_engine(
    pings_path: str = "data/raw/pings.parquet",
    stores_path: str = "data/metadata/stores_metadata.json",
    output_dir: str = "data/processed",
    buffer_radius_meters: float = 500.0
):
    print("=" * 70)
    print("  GeoPulse Spatial Engine - Catchment Joins & Cannibalization Pipeline")
    print("=" * 70)

    start_total = time.time()
    os.makedirs(output_dir, exist_ok=True)
    db_file = os.path.join(output_dir, "geopulse_lakehouse.duckdb")

    conn = duckdb.connect(db_file)

    # 1. Register Geodesic Haversine Macro
    conn.execute("""
    CREATE OR REPLACE MACRO haversine_distance_m(lat1, lon1, lat2, lon2) AS (
        6371000 * 2 * asin(
            sqrt(
                power(sin(radians(lat2 - lat1) / 2), 2) +
                cos(radians(lat1)) * cos(radians(lat2)) *
                power(sin(radians(lon2 - lon1) / 2), 2)
            )
        )
    );
    """)

    # 2. Ingest Metadata & Raw Telemetry
    print(f"[1/5] Ingesting stores metadata & raw GPS telemetry...")
    conn.execute(f"CREATE OR REPLACE TABLE raw_stores AS SELECT * FROM read_json_auto('{stores_path}')")
    conn.execute(f"CREATE OR REPLACE TABLE raw_pings AS SELECT * FROM read_parquet('{pings_path}')")

    total_pings = conn.execute("SELECT count(*) FROM raw_pings").fetchone()[0]
    total_stores = conn.execute("SELECT count(*) FROM raw_stores").fetchone()[0]
    print(f"      -> Ingested {total_pings:,} raw GPS pings across {total_stores} store profiles.")

    # 3. Spatial Catchment Join with Bounding-Box Indexing Pre-Filter
    # Approx 500m in degrees: d_lat ≈ 0.0045, d_lon ≈ 0.0046
    print(f"[2/5] Executing spatial join (500-meter catchment buffers)...")
    t0 = time.time()
    
    conn.execute(f"""
    CREATE OR REPLACE TABLE spatial_catchment_pings AS
    SELECT 
        p.device_id,
        p.timestamp,
        CAST(p.timestamp AS TIMESTAMP) AS ping_timestamp,
        EXTRACT(hour FROM CAST(p.timestamp AS TIMESTAMP)) AS ping_hour,
        p.latitude,
        p.longitude,
        p.accuracy_meters,
        p.activity_type,
        p.profile,
        s.store_id,
        s.store_name,
        s.status AS store_status,
        s.category AS store_category,
        s.latitude AS store_lat,
        s.longitude AS store_lon,
        round(haversine_distance_m(p.latitude, p.longitude, s.latitude, s.longitude), 2) AS distance_to_store_m
    FROM raw_pings p
    CROSS JOIN raw_stores s
    WHERE abs(p.latitude - s.latitude) <= 0.0055
      AND abs(p.longitude - s.longitude) <= 0.0055
      AND haversine_distance_m(p.latitude, p.longitude, s.latitude, s.longitude) <= {buffer_radius_meters}
    """)

    join_time = time.time() - t0
    catchment_pings_count = conn.execute("SELECT count(*) FROM spatial_catchment_pings").fetchone()[0]
    unique_visitors_count = conn.execute("SELECT count(DISTINCT device_id) FROM spatial_catchment_pings").fetchone()[0]
    print(f"      -> Spatial Join completed in {join_time:.3f} seconds.")
    print(f"      -> Catchment Intersections: {catchment_pings_count:,} pings | {unique_visitors_count:,} unique visitors.")

    # Export Catchment Parquet
    catchment_parquet = os.path.join(output_dir, "spatial_catchment_pings.parquet")
    conn.execute(f"COPY spatial_catchment_pings TO '{catchment_parquet}' (FORMAT PARQUET)")

    # 4. Hourly Footfall Aggregation (dbt staging & mart simulation)
    print(f"[3/5] Aggregating Hourly Footfall Traffic per store...")
    conn.execute("""
    CREATE OR REPLACE TABLE fct_hourly_footfall AS
    SELECT
        store_id,
        store_name,
        store_status,
        ping_hour AS hour_of_day,
        count(DISTINCT device_id) AS unique_hourly_visitors,
        count(*) AS total_catchment_pings,
        round(avg(distance_to_store_m), 1) AS avg_distance_from_center_m
    FROM spatial_catchment_pings
    GROUP BY store_id, store_name, store_status, ping_hour
    ORDER BY store_id, ping_hour;
    """)

    hourly_parquet = os.path.join(output_dir, "fct_hourly_footfall.parquet")
    hourly_csv = os.path.join(output_dir, "fct_hourly_footfall.csv")
    conn.execute(f"COPY fct_hourly_footfall TO '{hourly_parquet}' (FORMAT PARQUET)")
    conn.execute(f"COPY fct_hourly_footfall TO '{hourly_csv}' (FORMAT CSV, HEADER)")

    # 5. Cannibalization Analytics Matrix
    print(f"[4/5] Computing Store Cannibalization & Overlap Matrix...")
    conn.execute("""
    CREATE OR REPLACE TABLE dim_store_visitors AS
    SELECT 
        store_id,
        device_id
    FROM spatial_catchment_pings
    GROUP BY store_id, device_id;
    """)

    conn.execute("""
    CREATE OR REPLACE TABLE fct_store_cannibalization AS
    WITH base_counts AS (
        SELECT store_id, count(DISTINCT device_id) AS total_unique_devices
        FROM dim_store_visitors
        GROUP BY store_id
    ),
    overlap AS (
        SELECT 
            a.store_id AS existing_store_id,
            b.store_id AS candidate_store_id,
            count(DISTINCT a.device_id) AS overlapping_device_count
        FROM dim_store_visitors a
        JOIN dim_store_visitors b ON a.device_id = b.device_id
        WHERE a.store_id != b.store_id
        GROUP BY a.store_id, b.store_id
    )
    SELECT
        o.existing_store_id,
        s_exist.store_name AS existing_store_name,
        o.candidate_store_id,
        s_cand.store_name AS candidate_store_name,
        s_cand.status AS candidate_status,
        b.total_unique_devices AS existing_store_total_devices,
        o.overlapping_device_count,
        round((CAST(o.overlapping_device_count AS DOUBLE) / b.total_unique_devices) * 100.0, 2) AS cannibalization_pct,
        CASE 
            WHEN (CAST(o.overlapping_device_count AS DOUBLE) / b.total_unique_devices) * 100.0 >= 25.0 
                THEN 'HIGH_CANNIBALIZATION_RISK'
            WHEN (CAST(o.overlapping_device_count AS DOUBLE) / b.total_unique_devices) * 100.0 >= 10.0 
                THEN 'MODERATE_OVERLAP'
            ELSE 'HEALTHY_INDEPENDENT_CAPTURE'
        END AS cannibalization_risk_tier
    FROM overlap o
    JOIN base_counts b ON o.existing_store_id = b.store_id
    JOIN raw_stores s_exist ON o.existing_store_id = s_exist.store_id
    JOIN raw_stores s_cand ON o.candidate_store_id = s_cand.store_id
    ORDER BY cannibalization_pct DESC;
    """)

    cannib_parquet = os.path.join(output_dir, "fct_store_cannibalization.parquet")
    cannib_csv = os.path.join(output_dir, "fct_store_cannibalization.csv")
    conn.execute(f"COPY fct_store_cannibalization TO '{cannib_parquet}' (FORMAT PARQUET)")
    conn.execute(f"COPY fct_store_cannibalization TO '{cannib_csv}' (FORMAT CSV, HEADER)")

    # Print Cannibalization Results Table
    results_df = conn.execute("SELECT existing_store_id, candidate_store_id, existing_store_total_devices, overlapping_device_count, cannibalization_pct, cannibalization_risk_tier FROM fct_store_cannibalization").df()
    print("\n" + "=" * 70)
    print("  EXECUTIVE CANNIBALIZATION AUDIT RESULTS")
    print("=" * 70)
    print(results_df.to_string(index=False))
    print("=" * 70)

    # 6. Export Trip Arcs / Corridors for Kepler.gl Visualization
    print(f"\n[5/5] Generating Movement Vectors & Origin-Destination Arcs for Kepler.gl...")
    conn.execute("""
    CREATE OR REPLACE TABLE kepler_movement_arcs AS
    WITH ranked_pings AS (
        SELECT 
            device_id,
            timestamp,
            latitude,
            longitude,
            ping_hour,
            activity_type,
            ROW_NUMBER() OVER (PARTITION BY device_id ORDER BY timestamp) AS ping_seq
        FROM spatial_catchment_pings
    ),
    trips AS (
        SELECT
            r1.device_id,
            r1.ping_hour,
            r1.latitude AS origin_lat,
            r1.longitude AS origin_lon,
            r2.latitude AS dest_lat,
            r2.longitude AS dest_lon,
            r1.timestamp AS departure_time,
            r2.timestamp AS arrival_time
        FROM ranked_pings r1
        JOIN ranked_pings r2 
          ON r1.device_id = r2.device_id 
         AND r1.ping_seq + 1 = r2.ping_seq
    )
    SELECT * FROM trips LIMIT 5000;
    """)
    arcs_csv = os.path.join(output_dir, "kepler_movement_arcs.csv")
    conn.execute(f"COPY kepler_movement_arcs TO '{arcs_csv}' (FORMAT CSV, HEADER)")
    print(f"      -> Exported Movement Arcs to: {arcs_csv}")

    total_time = time.time() - start_total
    print(f"\n[GeoPulse Pipeline] Full spatial engine completed successfully in {total_time:.2f} seconds.")
    print(f"Artifacts stored in: {output_dir}\n")

    conn.close()


if __name__ == "__main__":
    run_spatial_engine()
