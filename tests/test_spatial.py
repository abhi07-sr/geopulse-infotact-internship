import sys
import numpy as np
import pandas as pd
sys.path.insert(0, "spatial")
from reference_join import hourly_unique_visitors, haversine_m

STORES = pd.DataFrame({"store_id": ["S1", "S2"], "store_name": ["A", "B"],
                       "status": ["existing", "candidate"],
                       "lat": [40.740, 40.750], "lon": [-73.980, -73.965]})


def make_pings(n=4000, seed=3):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "device_id": [f"D{i % 300:04d}" for i in range(n)],
        "lat": rng.uniform(40.73, 40.76, n),
        "lon": rng.uniform(-73.99, -73.955, n),
        "ts": pd.Timestamp("2025-03-03") + pd.to_timedelta(rng.uniform(0, 48, n), unit="h"),
    })


def test_distance_known_value():
    # 0.01 degrees of latitude is about 1,112 m
    assert abs(haversine_m(40.0, -74.0, 40.01, -74.0) - 1111.9) < 2


def test_point_on_store_is_inside_catchment():
    p = pd.DataFrame({"device_id": ["D1"], "lat": [40.740], "lon": [-73.980],
                      "ts": [pd.Timestamp("2025-03-03 08:10")]})
    _, out = hourly_unique_visitors(p, STORES)
    assert out.loc[0, "store_id"] == "S1" and out.loc[0, "unique_visitors"] == 1


def test_far_point_is_outside():
    p = pd.DataFrame({"device_id": ["D1"], "lat": [40.80], "lon": [-73.90],
                      "ts": [pd.Timestamp("2025-03-03 08:10")]})
    joined, _ = hourly_unique_visitors(p, STORES)
    assert len(joined) == 0


def test_matches_geopandas_projected_buffer():
    import geopandas as gpd
    pings = make_pings()
    joined, out = hourly_unique_visitors(pings, STORES)
    g = gpd.GeoDataFrame(pings, geometry=gpd.points_from_xy(pings.lon, pings.lat), crs=4326).to_crs(32618)
    s = gpd.GeoDataFrame(STORES, geometry=gpd.points_from_xy(STORES.lon, STORES.lat), crs=4326).to_crs(32618)
    s["geometry"] = s.buffer(500)
    ref = gpd.sjoin(g, s[["store_id", "geometry"]], predicate="within")
    # projected buffer and haversine differ by a few metres at the edge: allow tiny gap
    assert abs(len(ref) - len(joined)) <= 0.01 * max(len(ref), 1)


def test_unique_visitors_not_more_than_pings():
    pings = make_pings()
    joined, out = hourly_unique_visitors(pings, STORES)
    assert out["unique_visitors"].sum() <= len(joined)
