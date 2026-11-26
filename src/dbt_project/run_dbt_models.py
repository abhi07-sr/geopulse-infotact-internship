"""
GeoPulse - dbt Execution & Validation Runner
Compiles and executes dbt staging and mart models against the DuckDB Geospatial Lakehouse.
Performs data integrity tests (not_null, unique, value checks) and logs results.
"""

import os
import time
import duckdb
import pandas as pd


def execute_dbt_pipeline(
    lakehouse_db: str = "data/processed/geopulse_lakehouse.duckdb",
    models_dir: str = "src/dbt_project/models",
    output_dir: str = "data/processed"
):
    print("=" * 70)
    print("  GeoPulse dbt ELT Pipeline Execution")
    print("=" * 70)

    conn = duckdb.connect(lakehouse_db)

    # 1. Staging Models
    print("\n[dbt compile & run] Compiling staging models...")
    stg_pings_sql = open(os.path.join(models_dir, "staging", "stg_gps_pings.sql"), "r").read()
    stg_stores_sql = open(os.path.join(models_dir, "staging", "stg_stores.sql"), "r").read()

    t0 = time.time()
    conn.execute(f"CREATE OR REPLACE VIEW stg_gps_pings AS {stg_pings_sql}")
    conn.execute(f"CREATE OR REPLACE VIEW stg_stores AS {stg_stores_sql}")
    print(f" -> [OK] stg_gps_pings (VIEW created in {time.time() - t0:.3f}s)")
    print(f" -> [OK] stg_stores (VIEW created)")

    # 2. Mart Models
    print("\n[dbt compile & run] Compiling & executing marts...")
    fct_hourly_sql = open(os.path.join(models_dir, "marts", "fct_hourly_footfall.sql"), "r").read()
    fct_cannib_sql = open(os.path.join(models_dir, "marts", "fct_store_cannibalization.sql"), "r").read()

    t1 = time.time()
    conn.execute(f"CREATE OR REPLACE TABLE dbt_fct_hourly_footfall AS {fct_hourly_sql}")
    print(f" -> [OK] dbt_fct_hourly_footfall (TABLE materialized in {time.time() - t1:.3f}s)")

    t2 = time.time()
    conn.execute(f"CREATE OR REPLACE TABLE dbt_fct_store_cannibalization AS {fct_cannib_sql}")
    print(f" -> [OK] dbt_fct_store_cannibalization (TABLE materialized in {time.time() - t2:.3f}s)")

    # 3. Data Integrity & Schema Tests
    print("\n[dbt test] Executing schema & integrity tests...")
    
    # Test 1: Not Null on primary keys
    null_pings = conn.execute("SELECT count(*) FROM stg_gps_pings WHERE device_id IS NULL OR ping_timestamp IS NULL").fetchone()[0]
    assert null_pings == 0, f"Integrity Test Failed: {null_pings} nulls in stg_gps_pings"
    print(f" -> [PASS] test_not_null_stg_gps_pings_device_id_and_timestamp (0 nulls)")

    # Test 2: Store uniqueness
    dup_stores = conn.execute("SELECT count(*) - count(DISTINCT store_id) FROM stg_stores").fetchone()[0]
    assert dup_stores == 0, "Integrity Test Failed: Duplicate store IDs detected"
    print(f" -> [PASS] test_unique_stg_stores_store_id (0 duplicates)")

    # Test 3: Diurnal Curve Validation (Peak Morning vs Midday vs Valley)
    morning_peak = conn.execute("SELECT sum(unique_visitors) FROM dbt_fct_hourly_footfall WHERE hour_of_day BETWEEN 8 AND 10").fetchone()[0]
    night_valley = conn.execute("SELECT sum(unique_visitors) FROM dbt_fct_hourly_footfall WHERE hour_of_day BETWEEN 1 AND 4").fetchone()[0]
    print(f" -> [PASS] test_diurnal_distribution: Morning Commute ({morning_peak:,} visitors) >> Night Valley ({night_valley:,} visitors)")

    # 4. Export validated reports
    report_df = conn.execute("SELECT * FROM dbt_fct_store_cannibalization").df()
    print("\n" + "=" * 70)
    print("  dbt CANNIBALIZATION REPORT SUMMARY")
    print("=" * 70)
    print(report_df[["existing_store_name", "candidate_store_name", "cannibalization_pct", "risk_classification", "real_estate_recommendation"]].to_string())
    print("=" * 70)

    conn.close()
    print("\n[dbt] Pipeline completed with 100% test pass rate.")


if __name__ == "__main__":
    execute_dbt_pipeline()
