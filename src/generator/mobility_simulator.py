"""
GeoPulse - Synthetic Mobile Telemetry Simulator
Generates high-fidelity anonymized GPS pings mimicking urban diurnal mobility.
Models realistic morning/evening commutes, midday commercial rushes, and commuter
interceptions along commercial corridors to simulate store cannibalization.
"""

import os
import argparse
import random
import datetime
import math
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Tuple

from stores_config import STORES_METADATA, MOBILITY_ANCHORS


class MobilitySimulator:
    def __init__(self, seed: int = 42):
        random.seed(seed)
        np.random.seed(seed)
        self.stores = {s["store_id"]: s for s in STORES_METADATA}
        self.anchors = MOBILITY_ANCHORS

    def _generate_devices(self, num_devices: int) -> List[Dict[str, Any]]:
        """
        Assigns behavioral profiles and home/work locations to devices.
        Profiles:
        - COMMUTER_5TH_AVE: Travels past Store B and Store A (commuter corridor) -> creates cannibalization!
        - TECH_COMMUTER: Lives in West/East, commutes to Tech Park (Store C catchment).
        - RESIDENTIAL_LOCAL: Stays near suburban hub (Store D catchment).
        - DOWNTOWN_WORKER: Already based downtown near Store A.
        - CASUAL_EXPLORER: Random mobility throughout the city.
        """
        profiles = [
            ("COMMUTER_5TH_AVE", 0.35),  # 35% corridor commuters (prone to Store B interception)
            ("TECH_COMMUTER", 0.30),     # 30% tech corridor commuters (Store C)
            ("RESIDENTIAL_LOCAL", 0.15), # 15% suburban locals (Store D)
            ("DOWNTOWN_WORKER", 0.12),   # 12% downtown office workers
            ("CASUAL_EXPLORER", 0.08)    # 8% casual wanderers
        ]
        profile_names = [p[0] for p in profiles]
        weights = [p[1] for p in profiles]

        devices = []
        for i in range(num_devices):
            dev_id = f"DEV_{i+1:06d}"
            profile = random.choices(profile_names, weights=weights)[0]

            if profile == "COMMUTER_5TH_AVE":
                # Origin near Transit Hub or East/North residential, destination past 5th Ave
                origin = (12.9850 + np.random.normal(0, 0.004), 77.6100 + np.random.normal(0, 0.004))
                destination = (12.9650 + np.random.normal(0, 0.003), 77.6000 + np.random.normal(0, 0.003))
            elif profile == "TECH_COMMUTER":
                origin = (12.9600 + np.random.normal(0, 0.005), 77.5850 + np.random.normal(0, 0.005))
                destination = (12.9352 + np.random.normal(0, 0.003), 77.6245 + np.random.normal(0, 0.003))
            elif profile == "RESIDENTIAL_LOCAL":
                origin = (12.9610 + np.random.normal(0, 0.003), 77.5850 + np.random.normal(0, 0.003))
                destination = (12.9620 + np.random.normal(0, 0.004), 77.5870 + np.random.normal(0, 0.004))
            elif profile == "DOWNTOWN_WORKER":
                origin = (12.9750 + np.random.normal(0, 0.002), 77.6050 + np.random.normal(0, 0.002))
                destination = (12.9740 + np.random.normal(0, 0.003), 77.6060 + np.random.normal(0, 0.003))
            else:
                origin = (12.9700 + np.random.normal(0, 0.02), 77.6000 + np.random.normal(0, 0.02))
                destination = (12.9700 + np.random.normal(0, 0.02), 77.6000 + np.random.normal(0, 0.02))

            devices.append({
                "device_id": dev_id,
                "profile": profile,
                "origin": origin,
                "destination": destination
            })

        return devices

    def generate_day_pings(
        self,
        date_str: str = "2026-11-10",
        num_devices: int = 5000,
        pings_per_device: int = 40
    ) -> pd.DataFrame:
        """
        Generates diurnal GPS pings across 24 hours for the given devices.
        Returns a DataFrame of anonymized GPS pings.
        """
        devices = self._generate_devices(num_devices)
        base_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")

        records = []

        for dev in devices:
            profile = dev["profile"]
            orig_lat, orig_lon = dev["origin"]
            dest_lat, dest_lon = dev["destination"]

            # Diurnal schedule:
            # 00:00 - 07:00: Sleep at origin
            # 07:30 - 09:30: Morning commute (origin -> destination)
            # 09:30 - 12:00: At work/destination
            # 12:00 - 13:30: Lunch walk around destination
            # 13:30 - 17:30: At work
            # 17:30 - 20:00: Evening commute (destination -> origin)
            # 20:00 - 23:59: At origin / local

            # Sample time offsets throughout the day
            hours = np.random.choice(24, size=pings_per_device, p=self._diurnal_hourly_probabilities())
            hours.sort()

            for h in hours:
                minute = random.randint(0, 59)
                second = random.randint(0, 59)
                timestamp = base_date.replace(hour=h, minute=minute, second=second)

                # Determine spatial position based on time of day
                if 7 <= h <= 9:
                    # Morning commute phase: progress from origin towards destination
                    t_ratio = (h - 7 + minute / 60.0) / 3.0  # 0 to 1
                    t_ratio = min(max(t_ratio, 0.0), 1.0)
                    lat = orig_lat + (dest_lat - orig_lat) * t_ratio + np.random.normal(0, 0.0006)
                    lon = orig_lon + (dest_lon - orig_lon) * t_ratio + np.random.normal(0, 0.0006)
                    activity = "IN_TRANSIT" if random.random() > 0.3 else "WALKING"
                elif 12 <= h <= 13:
                    # Midday lunch/coffee break around destination
                    lat = dest_lat + np.random.normal(0, 0.0010)
                    lon = dest_lon + np.random.normal(0, 0.0010)
                    activity = "WALKING"
                elif 17 <= h <= 19:
                    # Evening return commute (destination -> origin)
                    t_ratio = (h - 17 + minute / 60.0) / 3.0
                    t_ratio = min(max(t_ratio, 0.0), 1.0)
                    lat = dest_lat + (orig_lat - dest_lat) * t_ratio + np.random.normal(0, 0.0006)
                    lon = dest_lon + (orig_lon - dest_lon) * t_ratio + np.random.normal(0, 0.0006)
                    activity = "IN_TRANSIT" if random.random() > 0.3 else "WALKING"
                elif 10 <= h <= 16:
                    # At destination
                    lat = dest_lat + np.random.normal(0, 0.0003)
                    lon = dest_lon + np.random.normal(0, 0.0003)
                    activity = "STATIONARY"
                else:
                    # Night/Early morning at origin
                    lat = orig_lat + np.random.normal(0, 0.0002)
                    lon = orig_lon + np.random.normal(0, 0.0002)
                    activity = "STATIONARY"

                accuracy = round(random.uniform(3.0, 14.5), 1)

                records.append({
                    "device_id": dev["device_id"],
                    "latitude": round(lat, 6),
                    "longitude": round(lon, 6),
                    "timestamp": timestamp.isoformat() + "Z",
                    "accuracy_meters": accuracy,
                    "activity_type": activity,
                    "profile": profile
                })

        df = pd.DataFrame(records)
        df.sort_values(by="timestamp", inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    def _diurnal_hourly_probabilities(self) -> List[float]:
        """Returns realistic 24-hour mobility activity probability distribution."""
        probs = [
            0.01, 0.005, 0.005, 0.005, 0.01, 0.02,   # 00 - 05: Night sleep
            0.04, 0.09,  0.11,  0.08,  0.05, 0.05,   # 06 - 11: Morning rise & Commute peak
            0.07, 0.07,  0.05,  0.05,  0.05, 0.09,   # 12 - 17: Lunch & afternoon peak
            0.10, 0.07,  0.05,  0.04,  0.03, 0.02    # 18 - 23: Evening peak & return
        ]
        total = sum(probs)
        return [p / total for p in probs]


def run_synthesis(
    output_path: str = "data/raw/pings.parquet",
    num_devices: int = 6000,
    pings_per_device: int = 40,
    export_csv: bool = True
):
    print(f"[GeoPulse] Starting Data Synthesis...")
    print(f" - Simulating {num_devices:,} devices x ~{pings_per_device} pings = ~{num_devices * pings_per_device:,} total GPS pings")
    
    sim = MobilitySimulator(seed=2026)
    df = sim.generate_day_pings(date_str="2026-11-10", num_devices=num_devices, pings_per_device=pings_per_device)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # 1. Export Parquet (primary production storage)
    df.to_parquet(output_path, index=False, engine="pyarrow", compression="snappy")
    print(f" -> Exported Parquet to: {output_path} ({len(df):,} rows)")

    # 2. Export sample CSV if requested
    if export_csv:
        csv_path = output_path.replace(".parquet", "_sample.csv")
        df.head(10000).to_csv(csv_path, index=False)
        print(f" -> Exported Sample CSV to: {csv_path} (10,000 sample rows)")

    # Display volume & temporal statistics
    df["hour"] = pd.to_datetime(df["timestamp"]).dt.hour
    hourly_counts = df.groupby("hour").size()
    print("\n--- Hourly Ping Distribution (Diurnal Curve Preview) ---")
    print(f"Peak Morning Hour (8 AM) : {hourly_counts.get(8, 0):,} pings")
    print(f"Midday Lunch (1 PM)      : {hourly_counts.get(13, 0):,} pings")
    print(f"Peak Evening Hour (6 PM) : {hourly_counts.get(18, 0):,} pings")
    print(f"Night Valley (3 AM)      : {hourly_counts.get(3, 0):,} pings")
    print("------------------------------------------------------\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GeoPulse Mobile GPS Ping Simulator")
    parser.add_argument("--output", type=str, default="data/raw/pings.parquet", help="Output file path")
    parser.add_argument("--devices", type=int, default=6000, help="Number of simulated devices")
    parser.add_argument("--pings-per-device", type=int, default=40, help="Average pings per device")
    args = parser.parse_args()

    run_synthesis(
        output_path=args.output,
        num_devices=args.devices,
        pings_per_device=args.pings_per_device
    )
