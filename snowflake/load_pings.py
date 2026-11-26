"""Load synthetic pings into Snowflake and build the GEOGRAPHY column.

Credentials are read from environment variables, never from code:
    SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD
Optional: SNOWFLAKE_WAREHOUSE (default COMPUTE_WH)

Usage:
    python snowflake/load_pings.py --input data/raw/pings.csv
    python snowflake/load_pings.py --input data/raw/pings.csv --dry-run   # no connection
"""
import argparse
import os
import sys
import pandas as pd

REQUIRED_COLUMNS = ["device_id", "lat", "lon", "ts"]
REQUIRED_ENV = ["SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD"]


def read_pings(path):
    df = pd.read_csv(path, parse_dates=["ts"])
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        sys.exit(f"Input file is missing columns: {missing}")
    if df[REQUIRED_COLUMNS].isnull().any().any():
        sys.exit("Input file has missing values; fix the data before loading.")
    return df[REQUIRED_COLUMNS]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="data/raw/pings.csv")
    ap.add_argument("--dry-run", action="store_true", help="validate only, no connection")
    args = ap.parse_args()

    df = read_pings(args.input)
    print(f"Validated {len(df):,} pings from {df['device_id'].nunique():,} devices.")
    if args.dry_run:
        print("Dry run: nothing was loaded.")
        return

    absent = [v for v in REQUIRED_ENV if not os.environ.get(v)]
    if absent:
        sys.exit(f"Set these environment variables first: {absent}")

    import snowflake.connector
    from snowflake.connector.pandas_tools import write_pandas

    conn = snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        database="GEOPULSE",
        schema="RAW",
    )
    try:
        cur = conn.cursor()
        cur.execute("TRUNCATE TABLE PINGS_STAGING")
        cur.execute("TRUNCATE TABLE PINGS")
        df.columns = [c.upper() for c in df.columns]      # match Snowflake column names
        ok, _, nrows, _ = write_pandas(conn, df, "PINGS_STAGING")
        print(f"Loaded {nrows:,} rows into PINGS_STAGING (success={ok}).")
        cur.execute(
            "INSERT INTO PINGS (device_id, ts, lat, lon, geog) "
            "SELECT device_id, ts, lat, lon, ST_MAKEPOINT(lon, lat) FROM PINGS_STAGING"
        )
        cur.execute("SELECT COUNT(*) FROM PINGS")
        print(f"PINGS now has {cur.fetchone()[0]:,} rows with GEOGRAPHY points.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
