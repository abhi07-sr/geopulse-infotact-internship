"""
GeoPulse - Apache Sedona / PySpark Distributed Spatial Join Engine
Enterprise-scale implementation for distributed computing clusters (AWS EMR / Databricks / Snowflake Snowpark).
Executes ST_Buffer (500m catchment) and ST_Intersects joins over tens of millions of GPS pings.
"""

import sys
import os

try:
    from pyspark.sql import SparkSession
    from pyspark.sql.functions import col, expr, to_timestamp, hour, date_trunc
    from sedona.register import SedonaRegistrator
    from sedona.utils import SedonaKryoRegistrator, KryoSerializer
except ImportError:
    # PySpark/Sedona may be optional for local single-node development
    pass


def create_sedona_spark_session(app_name: str = "GeoPulse_Sedona_Spatial_Join"):
    """
    Initializes a distributed SparkSession configured with Apache Sedona spatial extensions,
    Kryo serializer, and GeoSpark spatial partitioning.
    """
    spark = SparkSession.builder \
        .appName(app_name) \
        .config("spark.serializer", KryoSerializer.getName) \
        .config("spark.kryo.registrator", SedonaKryoRegistrator.getName) \
        .config("spark.sql.extensions", "org.apache.sedona.sql.SedonaSqlExtensions") \
        .config("spark.executor.memory", "8g") \
        .config("spark.driver.memory", "4g") \
        .getOrCreate()

    SedonaRegistrator.registerAll(spark)
    return spark


def run_distributed_spatial_pipeline(
    pings_parquet_path: str = "data/raw/pings.parquet",
    stores_json_path: str = "data/metadata/stores_metadata.json",
    output_path: str = "data/processed/sedona_spatial_matches.parquet"
):
    """
    Executes distributed spatial point-in-polygon join using Sedona:
    1. Ingests raw GPS pings into a Spark DataFrame.
    2. Projects coordinates to Geometry Point: ST_Point(longitude, latitude).
    3. Transforms EPSG:4326 (WGS84 lat/lon) to EPSG:3857 (Spherical Mercator meters) for accurate 500m buffering.
    4. Performs ST_Intersects between store 500m buffers and pings.
    """
    print(f"[GeoPulse Sedona] Initializing distributed spatial pipeline...")
    try:
        spark = create_sedona_spark_session()
    except Exception as e:
        print(f"[GeoPulse Sedona Warning] Native PySpark/Sedona cluster not detected in current environment ({e}).")
        print("[GeoPulse Sedona] Please use 'src/spatial_engine/local_spatial_runner.py' for local zero-dependency execution.")
        return False

    print(f"[GeoPulse Sedona] Reading telemetry pings from: {pings_parquet_path}")
    pings_df = spark.read.parquet(pings_parquet_path)
    stores_df = spark.read.json(stores_json_path)

    # Register temporary views for SQL execution
    pings_df.createOrReplaceTempView("raw_pings")
    stores_df.createOrReplaceTempView("stores_meta")

    # Construct spatial points and buffers
    spatial_join_query = """
    WITH pings_geom AS (
        SELECT 
            device_id,
            timestamp,
            latitude,
            longitude,
            ST_Point(CAST(longitude AS Decimal(24,20)), CAST(latitude AS Decimal(24,20))) AS ping_geom
        FROM raw_pings
    ),
    stores_geom AS (
        SELECT
            store_id,
            store_name,
            status,
            category,
            ST_Buffer(
                ST_Transform(
                    ST_Point(CAST(longitude AS Decimal(24,20)), CAST(latitude AS Decimal(24,20))), 
                    'EPSG:4326', 
                    'EPSG:3857'
                ), 
                500.0
            ) AS catchment_geom_3857
        FROM stores_meta
    )
    SELECT 
        p.device_id,
        p.timestamp,
        p.latitude,
        p.longitude,
        s.store_id,
        s.store_name,
        s.status
    FROM pings_geom p
    JOIN stores_geom s
    ON ST_Intersects(ST_Transform(p.ping_geom, 'EPSG:4326', 'EPSG:3857'), s.catchment_geom_3857)
    """

    print("[GeoPulse Sedona] Executing distributed ST_Intersects spatial join...")
    joined_df = spark.sql(spatial_join_query)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    joined_df.write.mode("overwrite").parquet(output_path)
    print(f"[GeoPulse Sedona] Distributed join completed. Result written to {output_path}")

    return True


if __name__ == "__main__":
    run_distributed_spatial_pipeline()
