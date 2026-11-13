-- GeoPulse: Snowflake setup for synthetic GPS pings
CREATE DATABASE IF NOT EXISTS GEOPULSE;
CREATE SCHEMA IF NOT EXISTS GEOPULSE.RAW;
USE SCHEMA GEOPULSE.RAW;

-- 1. Staging table: exactly what the CSV contains
CREATE OR REPLACE TABLE PINGS_STAGING (
    device_id STRING,
    lat       FLOAT,
    lon       FLOAT,
    ts        TIMESTAMP_NTZ
);

-- 2. Main table: adds a native GEOGRAPHY point
--    Note: ST_MAKEPOINT takes longitude first, then latitude.
CREATE OR REPLACE TABLE PINGS (
    device_id STRING        NOT NULL,
    ts        TIMESTAMP_NTZ NOT NULL,
    lat       FLOAT         NOT NULL,
    lon       FLOAT         NOT NULL,
    geog      GEOGRAPHY     NOT NULL
);

-- 3. Store locations (existing and candidate stores)
CREATE OR REPLACE TABLE STORES (
    store_id   STRING    NOT NULL,
    store_name STRING,
    status     STRING,           -- 'existing' or 'candidate'
    geog       GEOGRAPHY NOT NULL
);

-- Example stores inside the synthetic city (edit as you like)
INSERT INTO STORES
SELECT 'S1', 'Store A', 'existing',  ST_MAKEPOINT(-73.980, 40.740) UNION ALL
SELECT 'S2', 'Store B', 'candidate', ST_MAKEPOINT(-73.965, 40.750);

-- 4. Fill PINGS from staging after loading the CSV (run after the load step)
-- INSERT INTO PINGS
-- SELECT device_id, ts, lat, lon, ST_MAKEPOINT(lon, lat) FROM PINGS_STAGING;

-- 5. Quick checks
-- SELECT COUNT(*) FROM PINGS;
-- SELECT COUNT(*) FROM PINGS p JOIN STORES s
--   ON ST_DWITHIN(p.geog, s.geog, 500);   -- pings within 500 m of a store
