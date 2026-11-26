# GeoPulse Data Dictionary

This document details the database schema, table definitions, column types, and descriptions across the GeoPulse lakehouse.

---

## 1. Raw Telemetry: `raw_pings` / `stg_gps_pings`
Source: Synthetic Mobile GPS Telemetry (`data/raw/pings.parquet`)

| Column Name | Data Type | Constraint | Description |
| :--- | :--- | :--- | :--- |
| `device_id` | VARCHAR | NOT NULL | Anonymized unique identifier of the mobile device (e.g. `DEV_000142`). |
| `timestamp` / `ping_timestamp` | TIMESTAMP | NOT NULL | ISO-8601 UTC timestamp of the ping telemetry record. |
| `latitude` | DOUBLE | NOT NULL | WGS84 decimal degrees latitude (-90 to +90). |
| `longitude` | DOUBLE | NOT NULL | WGS84 decimal degrees longitude (-180 to +180). |
| `accuracy_meters` | DOUBLE | NOT NULL | Horizontal GPS accuracy in meters (typically 3.0m - 15.0m). |
| `activity_type` | VARCHAR | NULL | Inferred mobility state (`STATIONARY`, `WALKING`, `IN_TRANSIT`). |
| `profile` | VARCHAR | NULL | Commuter archetype (`COMMUTER_5TH_AVE`, `TECH_COMMUTER`, etc.). |

---

## 2. Store Master Metadata: `raw_stores` / `stg_stores`
Source: Store Registry Metadata (`data/metadata/stores_metadata.json`)

| Column Name | Data Type | Constraint | Description |
| :--- | :--- | :--- | :--- |
| `store_id` | VARCHAR | PRIMARY KEY | Unique store identifier (e.g. `STORE_A_EXISTING`). |
| `store_name` | VARCHAR | NOT NULL | Formal store branch title and commercial corridor. |
| `status` / `store_status` | VARCHAR | NOT NULL | Classification (`EXISTING`, `PROPOSED_CANDIDATE`, `ALTERNATIVE_CANDIDATE`). |
| `category` | VARCHAR | NOT NULL | Retail archetype (`Flagship Coffee & Retail`, `Express Coffee`, etc.). |
| `latitude` | DOUBLE | NOT NULL | Store geographic centroid latitude. |
| `longitude` | DOUBLE | NOT NULL | Store geographic centroid longitude. |
| `daily_target_revenue` | DOUBLE | NULL | Daily target revenue expectation in INR. |
| `description` | VARCHAR | NULL | Strategic retail role and location notes. |

---

## 3. Spatial Intersections: `spatial_catchment_pings`
Source: Spatial Point-in-Catchment Join (500m Buffer)

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `device_id` | VARCHAR | Unique device identifier. |
| `ping_timestamp` | TIMESTAMP | Telemetry timestamp. |
| `ping_hour` | INTEGER | Hour of day (0-23). |
| `store_id` | VARCHAR | Target store whose 500m catchment contains the ping. |
| `distance_to_store_m`| DOUBLE | Geodesic distance from the ping coordinates to store centroid in meters. |

---

## 4. Aggregated Mart: `dbt_fct_hourly_footfall`
Source: Hourly aggregation model (`fct_hourly_footfall.sql`)

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `store_id` | VARCHAR | Target store identifier. |
| `store_name` | VARCHAR | Store location title. |
| `store_status` | VARCHAR | Operational status. |
| `hour_of_day` | INTEGER | Hour of day (0 to 23). |
| `unique_visitors` | BIGINT | Count of distinct `device_id`s observed in the catchment during that hour. |
| `total_catchment_pings` | BIGINT | Total volume of GPS pings recorded in that hour. |
| `avg_distance_to_store_m` | DOUBLE | Mean distance of recorded visitors from the store center. |
| `pings_per_visitor_ratio` | DOUBLE | Dwell/sampling density metric. |

---

## 5. Cannibalization Mart: `dbt_fct_store_cannibalization`
Source: Cross-store device intersection model (`fct_store_cannibalization.sql`)

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `existing_store_id` | VARCHAR | Anchor existing store (e.g. `STORE_A_EXISTING`). |
| `candidate_store_id` | VARCHAR | Proposed candidate store (e.g. `STORE_B_CANDIDATE`). |
| `existing_store_total_devices` | BIGINT | Total unique visitors observed at existing store. |
| `overlapping_devices` | BIGINT | Count of unique devices that visited both store catchments. |
| `cannibalization_pct` | DOUBLE | $\frac{\text{overlapping\_devices}}{\text{existing\_store\_total\_devices}} \times 100$. |
| `risk_classification` | VARCHAR | `SEVERE_CANNIBALIZATION_RISK`, `MODERATE_OVERLAP`, or `LOW_OVERLAP_INDEPENDENT_CAPTURE`. |
| `real_estate_recommendation` | VARCHAR | Strategic corporate action (`REJECT_LOCATION` or `PROCEED_WITH_FURTHER_ANALYSIS`). |
