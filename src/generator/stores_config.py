"""
GeoPulse - Store & Catchment Area Definitions
Defines existing store locations, candidate expansion sites, and 500-meter radial catchment zones.
Also defines key urban mobility anchors (Residential, Transit hubs, Tech parks).
"""

import json
import math
from typing import Dict, List, Any

# Urban Center: Bengaluru Commercial & Retail Corridor (Indiranagar / MG Road / Koramangala)
# Coordinates centered around a bustling metropolitan retail sector:
BASE_LAT = 12.9716
BASE_LON = 77.5946

STORES_METADATA = [
    {
        "store_id": "STORE_A_EXISTING",
        "store_name": "Store A - 5th Ave Commercial Flagship (Existing)",
        "status": "EXISTING",
        "category": "Flagship Coffee & Retail",
        "latitude": 12.9750,
        "longitude": 77.6050,
        "daily_target_revenue": 125000,
        "description": "High-performing established flagship on the primary commuter corridor."
    },
    {
        "store_id": "STORE_B_CANDIDATE",
        "store_name": "Store B - 5th Ave North Proposed (Candidate)",
        "status": "PROPOSED_CANDIDATE",
        "category": "Express Coffee",
        "latitude": 12.9785,
        "longitude": 77.6075,
        "daily_target_revenue": 85000,
        "description": "Proposed new site ~450m north of Store A. Highly prone to cannibalizing Store A commuters."
    },
    {
        "store_id": "STORE_C_ALTERNATIVE",
        "store_name": "Store C - Tech Hub Outer Ring (Alternative)",
        "status": "ALTERNATIVE_CANDIDATE",
        "category": "Drive-Thru & Cafe",
        "latitude": 12.9352,
        "longitude": 77.6245,
        "daily_target_revenue": 95000,
        "description": "Alternative candidate site in an underserved tech park hub with independent foot traffic."
    },
    {
        "store_id": "STORE_D_RESIDENTIAL",
        "store_name": "Store D - Garden Suburb Plaza (Existing)",
        "status": "EXISTING",
        "category": "Neighborhood Cafe",
        "latitude": 12.9610,
        "longitude": 77.5850,
        "daily_target_revenue": 70000,
        "description": "Neighborhood residential cafe with steady weekend and evening traffic."
    }
]

# Urban transit anchors that drive morning & evening commuter flows
MOBILITY_ANCHORS = {
    "transit_hub_central": {"lat": 12.9780, "lon": 77.6020, "type": "Metro Interchange"},
    "tech_park_hub": {"lat": 12.9360, "lon": 77.6250, "type": "IT SEZ Campus"},
    "residential_zone_west": {"lat": 12.9600, "lon": 77.5800, "type": "High Density Apartments"},
    "residential_zone_east": {"lat": 12.9800, "lon": 77.6400, "type": "Suburban Living"},
    "university_quarter": {"lat": 12.9550, "lon": 77.6050, "type": "Student Campus"}
}


def create_circle_polygon(center_lat: float, center_lon: float, radius_meters: float = 500, num_points: int = 32) -> List[List[float]]:
    """
    Computes coordinates for a circular catchment polygon of specified radius in meters.
    Returns GeoJSON format coordinates: [[lon, lat], [lon, lat], ...]
    """
    coords = []
    earth_radius = 6378137.0  # WGS84 major axis in meters
    lat_rad = math.radians(center_lat)

    for i in range(num_points + 1):
        angle = (2 * math.pi / num_points) * i
        # Offsets in meters
        dx = radius_meters * math.cos(angle)
        dy = radius_meters * math.sin(angle)

        # Coordinate offsets in degrees
        d_lat = (dy / earth_radius) * (180 / math.pi)
        d_lon = (dx / (earth_radius * math.cos(lat_rad))) * (180 / math.pi)

        coords.append([round(center_lon + d_lon, 6), round(center_lat + d_lat, 6)])

    return coords


def get_catchments_geojson(radius_meters: float = 500) -> Dict[str, Any]:
    """Generates a FeatureCollection GeoJSON representing the 500m catchment polygons."""
    features = []
    for store in STORES_METADATA:
        polygon_coords = create_circle_polygon(store["latitude"], store["longitude"], radius_meters)
        feature = {
            "type": "Feature",
            "properties": {
                "store_id": store["store_id"],
                "store_name": store["store_name"],
                "status": store["status"],
                "category": store["category"],
                "radius_meters": radius_meters,
                "center_lat": store["latitude"],
                "center_lon": store["longitude"]
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [polygon_coords]
            }
        }
        features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features
    }


def export_metadata_files(output_dir: str = "data/metadata"):
    """Exports store list and catchment GeoJSON to metadata directory."""
    import os
    os.makedirs(output_dir, exist_ok=True)

    # 1. Export stores JSON
    stores_path = os.path.join(output_dir, "stores_metadata.json")
    with open(stores_path, "w", encoding="utf-8") as f:
        json.dump(STORES_METADATA, f, indent=2)

    # 2. Export 500m catchments GeoJSON
    catchments_path = os.path.join(output_dir, "catchments_500m.geojson")
    catchments = get_catchments_geojson(radius_meters=500)
    with open(catchments_path, "w", encoding="utf-8") as f:
        json.dump(catchments, f, indent=2)

    print(f"[GeoPulse] Metadata exported successfully to {output_dir}")
    print(f" - Stores metadata: {stores_path}")
    print(f" - 500m Catchments: {catchments_path}")


if __name__ == "__main__":
    export_metadata_files()
