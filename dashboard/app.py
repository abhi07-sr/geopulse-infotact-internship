"""
GeoPulse - Interactive Streamlit & PyDeck Mobility Application
Provides an interactive Python BI layer for geospatial exploratory data analysis,
cannibalization sensitivity analysis, and 3D H3 hexagonal footfall rendering.
"""

import os
import json
import duckdb
import pandas as pd
import streamlit as st
import pydeck as pdk

st.set_page_config(
    page_title="GeoPulse | Hyper-Local Retail Mobility Analytics",
    page_icon="📍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .metric-card {
        background-color: #1e293b;
        border-radius: 10px;
        padding: 15px;
        border: 1px solid #334155;
    }
    .stAlert {
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_data():
    conn = duckdb.connect("data/processed/geopulse_lakehouse.duckdb", read_only=True)
    stores = json.load(open("data/metadata/stores_metadata.json"))
    catchments = json.load(open("data/metadata/catchments_500m.geojson"))
    hourly = conn.execute("SELECT * FROM dbt_fct_hourly_footfall").df()
    cannib = conn.execute("SELECT * FROM dbt_fct_store_cannibalization").df()
    pings = conn.execute("SELECT * FROM spatial_catchment_pings USING SAMPLE 10000").df()
    conn.close()
    return stores, catchments, hourly, cannib, pings


stores, catchments, hourly, cannib, pings = load_data()

# Header
st.title("📍 GeoPulse: Hyper-Local Retail Mobility Analytics")
st.caption("Infotact Solutions • Data Associate L1 Internship Project • Vol. II Advanced Analytics")

# Sidebar Filters
st.sidebar.header("🕹️ Spatial Controls & Timeline")

selected_hour = st.sidebar.slider("Timeline Scrubber (Hour of Day)", 0, 23, 8)
phase_map = {
    8: "Morning Commute Peak (Coffee Surge)",
    13: "Midday Commercial & Lunch Break",
    18: "Evening Commute & Transit Peak",
    3: "Night Valley (Dormant)"
}
current_phase = phase_map.get(selected_hour, "Regular Intra-day Movement")
st.sidebar.info(f"**Selected Time:** {selected_hour:02d}:00 ({current_phase})")

show_3d_hex = st.sidebar.checkbox("Render 3D H3 Hexagon Density", value=True)
show_catchments = st.sidebar.checkbox("Render 500m Store Buffers", value=True)
show_stores = st.sidebar.checkbox("Render Store Pin Anchors", value=True)

# Main Metrics Row
st.subheader("📊 Executive Real Estate Intelligence")
col1, col2, col3, col4 = st.columns(4)

total_visitors = pings["device_id"].nunique()
store_b_cannib = cannib[(cannib["existing_store_id"] == "STORE_A_EXISTING") & (cannib["candidate_store_id"] == "STORE_B_CANDIDATE")]
cannib_pct = store_b_cannib["cannibalization_pct"].values[0] if len(store_b_cannib) > 0 else 0.0

col1.metric("Total Unique Visitors", f"{total_visitors:,}", "Citywide Telemetry")
col2.metric("Catchment Buffer Radius", "500 Meters", "Pedestrian Walkshed")
col3.metric("Store B Cannibalization Rate", f"{cannib_pct:.1f}%", "-90.3% Overlap Alert", delta_color="inverse")
col4.metric("Recommended Expansion Site", "Store C (Tech Hub)", "100% Net-New Footfall")

# Critical Alert Banner
if cannib_pct >= 30.0:
    st.error(
        f"🚨 **HIGH CANNIBALIZATION ALERT:** Candidate Store B (5th Ave North) intercepts **{cannib_pct:.1f}%** of "
        f"commuter footfall already visiting Flagship Store A. Re-allocating capital expenditure to **Store C (Tech Hub)** "
        f"avoids brand cannibalization and maximizes incremental market penetration."
    )

# 3D PyDeck Map Visualization
st.subheader("🗺️ 3D Mobility Footfall & Spatial Catchment Map")

filtered_pings = pings[pings["ping_hour"] == selected_hour]

layers = []

if show_3d_hex:
    hex_layer = pdk.Layer(
        "HexagonLayer",
        data=filtered_pings,
        get_position=["longitude", "latitude"],
        radius=90,
        elevation_scale=15,
        elevation_range=[0, 1000],
        extruded=True,
        pickable=True,
        coverage=0.9
    )
    layers.append(hex_layer)

if show_catchments:
    catchment_layer = pdk.Layer(
        "GeoJsonLayer",
        data=catchments,
        opacity=0.3,
        stroked=True,
        filled=True,
        get_fill_color=[59, 130, 246, 70],
        get_line_color=[34, 197, 94, 255],
        get_line_width=3,
        pickable=True
    )
    layers.append(catchment_layer)

if show_stores:
    stores_df = pd.DataFrame(stores)
    store_layer = pdk.Layer(
        "ScatterplotLayer",
        data=stores_df,
        get_position=["longitude", "latitude"],
        get_radius=60,
        get_fill_color=[239, 68, 68, 255],
        pickable=True
    )
    layers.append(store_layer)

view_state = pdk.ViewState(
    latitude=12.9750,
    longitude=77.6050,
    zoom=12.5,
    pitch=45,
    bearing=-10
)

st.pydeck_chart(
    pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_style="mapbox://styles/mapbox/dark-v10",
        tooltip={"text": "Coordinates: [{longitude}, {latitude}]"}
    )
)

# Footfall Curves & Cannibalization Matrix
col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("📈 Hourly Footfall Volume (dbt Mart)")
    pivot_hourly = hourly.pivot(index="hour_of_day", columns="store_name", values="unique_visitors").fillna(0)
    st.line_chart(pivot_hourly)

with col_right:
    st.subheader("📋 Cross-Store Cannibalization Matrix")
    display_cannib = cannib[[
        "existing_store_name", "candidate_store_name", 
        "cannibalization_pct", "risk_classification", "real_estate_recommendation"
    ]]
    st.dataframe(display_cannib, use_container_width=True)
