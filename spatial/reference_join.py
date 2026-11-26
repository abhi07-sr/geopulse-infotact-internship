"""Reference (non-Spark) catchment join, used to check the Sedona job.

For every ping, find the stores within RADIUS_M metres (haversine distance), then count
unique devices per store per hour. Fine for small samples; Sedona handles millions.

Usage:
    python spatial/reference_join.py --pings data/raw/pings.csv --stores data/stores.csv
"""
import argparse
import numpy as np
import pandas as pd

RADIUS_M = 500
EARTH_RADIUS_M = 6371008.8


def haversine_m(lat1, lon1, lat2, lon2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = p2 - p1
    dlmb = np.radians(lon2) - np.radians(lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_M * np.arcsin(np.sqrt(a))


def hourly_unique_visitors(pings, stores, radius_m=RADIUS_M):
    frames = []
    for s in stores.itertuples():
        d = haversine_m(pings["lat"].to_numpy(), pings["lon"].to_numpy(), s.lat, s.lon)
        hit = pings[d <= radius_m].copy()
        hit["store_id"] = s.store_id
        frames.append(hit)
    joined = pd.concat(frames, ignore_index=True)
    joined["hour"] = joined["ts"].dt.floor("h")
    out = (joined.groupby(["store_id", "hour"])["device_id"].nunique()
                 .rename("unique_visitors").reset_index())
    return joined, out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pings", default="data/raw/pings.csv")
    ap.add_argument("--stores", default="data/stores.csv")
    a = ap.parse_args()
    pings = pd.read_csv(a.pings, parse_dates=["ts"])
    stores = pd.read_csv(a.stores)
    joined, out = hourly_unique_visitors(pings, stores)
    print(f"{len(joined):,} ping-store matches")
    print(out.sort_values("unique_visitors", ascending=False).head(10).to_string(index=False))
