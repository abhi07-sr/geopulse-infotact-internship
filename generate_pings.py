"""Generate synthetic, anonymized GPS pings that mimic city movement.

Each device has a home and a work location. On weekdays it commutes in the morning
(about 07:00-09:30) and back in the evening (about 16:30-19:00), with a few random
daytime pings. All data is synthetic: no real people or devices.

Usage:
    python data_generation/generate_pings.py --devices 5000 --days 3 --seed 42
"""
import argparse
import numpy as np
import pandas as pd

# Bounding box of an imaginary city (roughly 10 km x 10 km)
LAT_MIN, LAT_MAX = 40.70, 40.79
LON_MIN, LON_MAX = -74.02, -73.93


def commute_points(home, work, n, rng):
    """n points along the straight line home -> work, with small GPS noise."""
    t = rng.random(n)
    lat = home[0] + t * (work[0] - home[0]) + rng.normal(0, 0.0003, n)
    lon = home[1] + t * (work[1] - home[1]) + rng.normal(0, 0.0003, n)
    return lat, lon, t


def generate(devices, days, seed, start="2025-03-03"):
    rng = np.random.default_rng(seed)
    start_day = pd.Timestamp(start)
    frames = []
    for d in range(devices):
        home = (rng.uniform(LAT_MIN, LAT_MAX), rng.uniform(LON_MIN, LON_MAX))
        work = (rng.uniform(LAT_MIN, LAT_MAX), rng.uniform(LON_MIN, LON_MAX))
        for day in range(days):
            date = start_day + pd.Timedelta(days=day)
            weekend = date.dayofweek >= 5
            if weekend:
                n = rng.integers(2, 6)
                lat = rng.uniform(LAT_MIN, LAT_MAX, n)
                lon = rng.uniform(LON_MIN, LON_MAX, n)
                hours = rng.uniform(10, 20, n)
            else:
                n_m, n_e, n_x = rng.integers(3, 7), rng.integers(3, 7), rng.integers(1, 4)
                la1, lo1, t1 = commute_points(home, work, n_m, rng)
                la2, lo2, t2 = commute_points(work, home, n_e, rng)
                la3 = work[0] + rng.normal(0, 0.002, n_x)
                lo3 = work[1] + rng.normal(0, 0.002, n_x)
                lat = np.concatenate([la1, la2, la3])
                lon = np.concatenate([lo1, lo2, lo3])
                hours = np.concatenate([7 + 2.5 * t1,        # morning 07:00-09:30
                                        16.5 + 2.5 * t2,     # evening 16:30-19:00
                                        rng.uniform(11, 15, n_x)])
            ts = date + pd.to_timedelta(hours, unit="h")
            frames.append(pd.DataFrame({
                "device_id": f"D{d:06d}",
                "lat": np.clip(lat, LAT_MIN, LAT_MAX).round(6),
                "lon": np.clip(lon, LON_MIN, LON_MAX).round(6),
                "ts": ts.floor("s"),
            }))
    return pd.concat(frames, ignore_index=True).sort_values(["ts", "device_id"]).reset_index(drop=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--devices", type=int, default=5000)
    p.add_argument("--days", type=int, default=3)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--output", default="data/raw/pings.csv")
    a = p.parse_args()
    df = generate(a.devices, a.days, a.seed)
    import os
    os.makedirs(os.path.dirname(a.output), exist_ok=True)
    df.to_csv(a.output, index=False)
    print(f"{len(df):,} pings, {df.device_id.nunique():,} devices -> {a.output}")
