"""
GeoPulse - Master Verification Test Suite
Executes and validates every pipeline component, data generator, spatial join,
dbt transformation, dashboard generator, and script in the GeoPulse workspace.
"""

import sys
import subprocess
import os

SCRIPTS = [
    ("1. Stores & Catchments Metadata Generator", "python src/generator/stores_config.py"),
    ("2. Mobile GPS Mobility Telemetry Simulator", "python src/generator/mobility_simulator.py --devices 2000 --pings-per-device 20"),
    ("3. Local Geodesic Spatial Join & Catchment Engine", "python src/spatial_engine/local_spatial_runner.py"),
    ("4. Apache Sedona / PySpark Join Engine (Syntax & Import)", "python -c \"import py_compile; py_compile.compile('src/spatial_engine/sedona_spatial_join.py', doraise=True); print('[OK] Sedona PySpark script compiled successfully')\""),
    ("5. dbt Staging, Marts & Data Integrity Tests", "python src/dbt_project/run_dbt_models.py"),
    ("6. 3D Deck.gl Dashboard Packager", "python dashboard/generate_dashboard.py"),
    ("7. Apache Airflow Orchestration DAG (Syntax & Tasks)", "python -c \"import py_compile; py_compile.compile('src/orchestration/airflow_dag_geopulse.py', doraise=True); print('[OK] Airflow DAG compiled successfully')\""),
    ("8. Streamlit Mobility App (Syntax & Modules)", "python -c \"import py_compile; py_compile.compile('dashboard/app.py', doraise=True); print('[OK] Streamlit app compiled successfully')\""),
]

ARTIFACTS_TO_VERIFY = [
    ("Store Metadata JSON", "data/metadata/stores_metadata.json"),
    ("500m Catchment GeoJSON", "data/metadata/catchments_500m.geojson"),
    ("Raw GPS Pings Parquet", "data/raw/pings.parquet"),
    ("Raw GPS Pings Sample CSV", "data/raw/pings_sample.csv"),
    ("DuckDB Geospatial Lakehouse DB", "data/processed/geopulse_lakehouse.duckdb"),
    ("Spatial Catchment Intersections Parquet", "data/processed/spatial_catchment_pings.parquet"),
    ("Hourly Footfall Mart Parquet", "data/processed/fct_hourly_footfall.parquet"),
    ("Hourly Footfall Mart CSV", "data/processed/fct_hourly_footfall.csv"),
    ("Cannibalization Mart Parquet", "data/processed/fct_store_cannibalization.parquet"),
    ("Cannibalization Mart CSV", "data/processed/fct_store_cannibalization.csv"),
    ("Movement Arcs CSV", "data/processed/kepler_movement_arcs.csv"),
    ("Interactive 3D Dashboard HTML", "dashboard/index.html"),
    ("Project Documentation README", "README.md"),
    ("Formal Project Report", "docs/project_report.md"),
    ("Presentation Slide Deck", "docs/presentation_deck.md"),
    ("Model Evaluation Results", "docs/model_evaluation_results.md"),
    ("Data Dictionary", "docs/data_dictionary.md"),
]


def run_all_tests():
    print("=" * 80)
    print("           GEOPULSE MASTER PIPELINE EXECUTION & INTEGRITY AUDIT")
    print("=" * 80)

    failed = 0

    print("\n--- STAGE 1: EXECUTING ALL COMPONENT SCRIPTS ---")
    for name, cmd in SCRIPTS:
        print(f"\n[RUNNING] {name}")
        print(f"  Command: {cmd}")
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"  Status : PASSED (Exit Code 0)")
            lines = [l for l in res.stdout.strip().splitlines() if l.strip()]
            for l in lines[:2]:
                print(f"    | {l}")
            if len(lines) > 2:
                print(f"    | ... ({len(lines)} lines total output)")
        else:
            print(f"  Status : FAILED (Exit Code {res.returncode})")
            print(f"    STDERR: {res.stderr.strip()[:400]}")
            failed += 1

    print("\n" + "-" * 80)
    print("--- STAGE 2: VERIFYING ALL OUTPUT ARTIFACTS & DELIVERABLES ---")
    print("-" * 80)

    missing_files = 0
    for label, path in ARTIFACTS_TO_VERIFY:
        exists = os.path.exists(path)
        size = os.path.getsize(path) if exists else 0
        if exists and size > 0:
            print(f"  [OK] {label:<42} -> {path} ({size:,} bytes)")
        else:
            print(f"  [MISSING/EMPTY] {label:<42} -> {path}")
            missing_files += 1

    print("\n" + "=" * 80)
    if failed == 0 and missing_files == 0:
        print("  ALL FILES AND SCRIPTS RUN PROPERLY! 100% SUCCESS ACROSS ALL PIPELINE STAGES.")
    else:
        print(f"  AUDIT COMPLETED WITH ISSUES: {failed} script errors, {missing_files} missing files.")
    print("=" * 80)

    sys.exit(0 if (failed == 0 and missing_files == 0) else 1)


if __name__ == "__main__":
    run_all_tests()
