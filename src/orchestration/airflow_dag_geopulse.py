"""
GeoPulse - Apache Airflow Production DAG
Orchestrates the daily end-to-end geospatial data engineering pipeline:
1. Ingest Raw Mobile GPS Pings (Lakehouse)
2. Distributed Spatial Joins (Apache Sedona / Spatial Engine)
3. dbt Model Materializations & Schema Tests
4. Automated Cannibalization Risk Calculation & Alerting
5. Dashboard Cache Refresh
"""

from datetime import datetime, timedelta

try:
    from airflow import DAG
    from airflow.operators.bash import BashOperator
    from airflow.operators.python import PythonOperator
    from airflow.utils.dates import days_ago
except ImportError:
    # Airflow placeholder classes for environments without Airflow daemon
    class DAG:
        def __init__(self, *args, **kwargs): pass
    class BashOperator:
        def __init__(self, *args, **kwargs): pass
    class PythonOperator:
        def __init__(self, *args, **kwargs): pass


default_args = {
    "owner": "Abhinandan Naik (Infotact Solutions)",
    "depends_on_past": False,
    "email": ["naikabhinandan3@gmail.com"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "start_date": datetime(2026, 11, 10),
}


def audit_cannibalization_alerts(**kwargs):
    """
    Python callable checking if any candidate store breaches the 30% cannibalization threshold.
    Logs warning and triggers executive notifications if high risk is detected.
    """
    import duckdb
    conn = duckdb.connect("data/processed/geopulse_lakehouse.duckdb", read_only=True)
    res = conn.execute("""
        SELECT existing_store_name, candidate_store_name, cannibalization_pct
        FROM dbt_fct_store_cannibalization
        WHERE cannibalization_pct >= 30.0
    """).fetchall()
    conn.close()

    if res:
        print(f"[ALERT] {len(res)} store pairings breached high cannibalization threshold:")
        for r in res:
            print(f" -> {r[1]} intercepts {r[2]:.2f}% of {r[0]} traffic!")
    else:
        print("[INFO] All candidate stores exhibit healthy independent capture.")


with DAG(
    dag_id="geopulse_daily_mobility_pipeline",
    default_args=default_args,
    description="Daily automated ingestion, spatial catchment join, and cannibalization modeling",
    schedule_interval="0 2 * * *",  # Runs daily at 2:00 AM UTC
    catchup=False,
    tags=["retail", "geospatial", "mobility", "dbt", "sedona", "infotact"],
) as dag:

    # Task 1: Generate & Ingest Telemetry
    task_ingest_pings = BashOperator(
        task_id="ingest_mobile_pings",
        bash_command="python src/generator/mobility_simulator.py --output data/raw/pings.parquet",
    )

    # Task 2: Execute Spatial Catchment Joins
    task_spatial_join = BashOperator(
        task_id="execute_spatial_catchment_joins",
        bash_command="python src/spatial_engine/local_spatial_runner.py",
    )

    # Task 3: Run dbt ELT Models & Validation Tests
    task_dbt_run = BashOperator(
        task_id="run_dbt_models_and_tests",
        bash_command="python src/dbt_project/run_dbt_models.py",
    )

    # Task 4: Automated Cannibalization Alerts
    task_cannibalization_check = PythonOperator(
        task_id="check_cannibalization_thresholds",
        python_callable=audit_cannibalization_alerts,
        provide_context=True,
    )

    # Task 5: Refresh Interactive 3D Dashboard Data
    task_refresh_dashboard = BashOperator(
        task_id="refresh_dashboard_assets",
        bash_command="python dashboard/generate_dashboard.py",
    )

    # Define Workflow Dependencies
    task_ingest_pings >> task_spatial_join >> task_dbt_run >> task_cannibalization_check >> task_refresh_dashboard
