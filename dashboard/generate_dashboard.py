"""
GeoPulse - Next-Gen 3D Mobility Analytics Dashboard Generator
Constructs a cutting-edge, ultra-reliable 3D Deck.gl + MapLibre visual prototype.
Features:
- Cinematic 3D Camera Controls & Auto-Orbit Drone Mode
- 3D Extruded H3 Hexagonal Density Towers with Ambient Lighting
- Pulsing 500m Catchment Radar Rings
- Dynamic Parabolic 3D Commuter Arcs with Temporal Particle Flow
- Interactive Cannibalization Distance Sensitivity Simulator
- Preset Corridor Viewports (Downtown 5th Ave vs Tech Hub vs Bird's-Eye)
- High-Performance Glassmorphic UI with Glass Blur and Neon Glow Accents
"""

import csv
import datetime
import hashlib
import json
import math
from pathlib import Path

try:
    import duckdb
except ImportError:  # CSV snapshots keep the prototype buildable without the optional database package.
    duckdb = None


def generate_cutting_edge_dashboard(
    lakehouse_db: str = "data/processed/geopulse_lakehouse.duckdb",
    metadata_dir: str = "data/metadata",
    output_html: str = "dashboard/index.html"
):
    print("[GeoPulse] Generating the 3D mobility dashboard...")
    project_root = Path(__file__).resolve().parents[1]

    def resolve_path(value):
        path = Path(value)
        return path if path.is_absolute() else project_root / path

    lakehouse_path = resolve_path(lakehouse_db)
    metadata_path = resolve_path(metadata_dir)
    output_path = resolve_path(output_html)
    use_duckdb = duckdb is not None and lakehouse_path.exists()

    required_paths = [metadata_path / "stores_metadata.json", metadata_path / "catchments_500m.geojson"]
    if not use_duckdb:
        required_paths.extend([
            project_root / "data/processed/fct_hourly_footfall.csv",
            project_root / "data/processed/fct_store_cannibalization.csv",
            project_root / "data/processed/kepler_movement_arcs.csv",
            project_root / "data/raw/pings_sample.csv",
        ])
    missing_paths = [str(path) for path in required_paths if not path.exists()]
    if missing_paths:
        raise FileNotFoundError("Dashboard inputs are missing: " + ", ".join(missing_paths))

    with (metadata_path / "stores_metadata.json").open("r", encoding="utf-8") as source:
        stores_data = json.load(source)
    with (metadata_path / "catchments_500m.geojson").open("r", encoding="utf-8") as source:
        catchment_geojson = json.load(source)

    def normalize_value(value):
        if isinstance(value, (datetime.date, datetime.datetime)):
            return value.isoformat()
        if isinstance(value, float) and not math.isfinite(value):
            return None
        if hasattr(value, "item"):
            value = value.item()
        return value

    def query_records(conn, sql):
        result = conn.execute(sql)
        column_names = [column[0] for column in result.description]
        return [
            {name: normalize_value(value) for name, value in zip(column_names, row)}
            for row in result.fetchall()
        ]

    def read_csv_records(path):
        with path.open("r", encoding="utf-8-sig", newline="") as source:
            rows = list(csv.DictReader(source))
        numeric_fields = {
            "hour_of_day", "unique_hourly_visitors", "total_catchment_pings", "avg_distance_from_center_m",
            "existing_store_total_devices", "overlapping_device_count", "cannibalization_pct",
            "ping_hour", "latitude", "longitude", "origin_lat", "origin_lon", "dest_lat", "dest_lon",
            "accuracy_meters",
        }
        for row in rows:
            for key, value in row.items():
                if key in numeric_fields and value not in (None, ""):
                    number = float(value)
                    row[key] = int(number) if number.is_integer() else number
                elif value == "":
                    row[key] = None
        return rows

    if use_duckdb:
        # Read from one connection scope so it is always closed if a query fails.
        with duckdb.connect(str(lakehouse_path), read_only=True) as conn:
            hourly_data = query_records(conn, "SELECT * FROM dbt_fct_hourly_footfall ORDER BY store_id, hour_of_day")
            cannib_data = query_records(conn, "SELECT * FROM dbt_fct_store_cannibalization")
            pings_sample = query_records(conn, """
                SELECT device_id, latitude, longitude, ping_hour, activity_type,
                       profile, store_id, distance_to_store_m
                FROM spatial_catchment_pings
                ORDER BY hash(device_id || ':' || latitude::VARCHAR || ':' || longitude::VARCHAR || ':' || ping_hour::VARCHAR)
                LIMIT 8000
            """)
            arcs_data = query_records(conn, "SELECT * FROM kepler_movement_arcs LIMIT 1200")
    else:
        # The committed CSV snapshots provide a lightweight fallback for prototype builds.
        hourly_data = read_csv_records(project_root / "data/processed/fct_hourly_footfall.csv")
        for row in hourly_data:
            row["unique_visitors"] = row.pop("unique_hourly_visitors", 0)
        cannib_data = read_csv_records(project_root / "data/processed/fct_store_cannibalization.csv")
        for row in cannib_data:
            row["overlapping_devices"] = row.pop("overlapping_device_count", 0)
            row["risk_classification"] = row.pop("cannibalization_risk_tier", "UNKNOWN")
        pings_sample = read_csv_records(project_root / "data/raw/pings_sample.csv")
        for row in pings_sample:
            timestamp = row.pop("timestamp", None)
            row["ping_hour"] = datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00")).hour if timestamp else 0
            row.setdefault("store_id", None)
            row.setdefault("distance_to_store_m", None)
        pings_sample.sort(key=lambda row: hashlib.sha256(
            f"{row.get('device_id')}:{row.get('latitude')}:{row.get('longitude')}:{row.get('ping_hour')}".encode("utf-8")
        ).digest())
        pings_sample = pings_sample[:8000]
        arcs_data = read_csv_records(project_root / "data/processed/kepler_movement_arcs.csv")[:1200]

    stores_json = json.dumps(stores_data, ensure_ascii=False).replace("<", "\\u003c")
    catchments_json = json.dumps(catchment_geojson, ensure_ascii=False).replace("<", "\\u003c")
    hourly_json = json.dumps(hourly_data, ensure_ascii=False, allow_nan=False).replace("<", "\\u003c")
    cannib_json = json.dumps(cannib_data, ensure_ascii=False, allow_nan=False).replace("<", "\\u003c")
    pings_json = json.dumps(pings_sample, ensure_ascii=False, allow_nan=False).replace("<", "\\u003c")
    arcs_json = json.dumps(arcs_data, ensure_ascii=False, allow_nan=False).replace("<", "\\u003c")

    html_code = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>GeoPulse | Hyper-Local Retail Mobility & 3D Cannibalization Analytics</title>
  
  <!-- MapLibre GL & Deck.gl v8 -->
  <script src="https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.js"></script>
  <link href="https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.css" rel="stylesheet" />
  <script src="https://unpkg.com/deck.gl@8.9.33/dist.min.js"></script>
  
  <!-- Chart.js & Tailwind CSS -->
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
  <script src="https://cdn.tailwindcss.com/3.4.17"></script>

  <!-- Lucide Icons -->
  <script src="https://unpkg.com/lucide@0.468.0"></script>

  <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');
    
    * {{
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }}
    .font-mono {{
      font-family: 'JetBrains Mono', monospace;
    }}

    body, html {{
      margin: 0; padding: 0; width: 100%; height: 100%;
      overflow: hidden; background: #07090e; color: #f1f5f9;
    }}

    #map-container {{
      position: absolute; top: 0; left: 0; width: 100%; height: 100%;
    }}

    /* Ultra-sleek Glassmorphism */
    .glass-panel {{
      background: rgba(13, 18, 30, 0.78);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border: 1px solid rgba(255, 255, 255, 0.08);
      box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.7), inset 0 1px 0 0 rgba(255, 255, 255, 0.06);
    }}

    .glass-card-subtle {{
      background: rgba(22, 30, 49, 0.55);
      border: 1px solid rgba(255, 255, 255, 0.05);
    }}

    .neon-border-cyan {{
      box-shadow: 0 0 15px rgba(6, 182, 212, 0.25);
    }}

    .neon-border-red {{
      box-shadow: 0 0 20px rgba(239, 68, 68, 0.35);
    }}

    /* Custom Scrollbars */
    ::-webkit-scrollbar {{
      width: 5px; height: 5px;
    }}
    ::-webkit-scrollbar-track {{
      background: rgba(10, 15, 26, 0.4);
    }}
    ::-webkit-scrollbar-thumb {{
      background: rgba(71, 85, 105, 0.5);
      border-radius: 4px;
    }}
    ::-webkit-scrollbar-thumb:hover {{
      background: rgba(100, 116, 139, 0.8);
    }}

    /* Pulse animation for radar rings */
    @keyframes pulse-ring {{
      0% {{ transform: scale(0.95); opacity: 0.8; }}
      50% {{ transform: scale(1.05); opacity: 0.3; }}
      100% {{ transform: scale(0.95); opacity: 0.8; }}
    }}

    .pulse-effect {{
      animation: pulse-ring 3s ease-in-out infinite;
    }}

    /* Gradient Text */
    .gradient-text {{
      background: linear-gradient(135deg, #38bdf8 0%, #818cf8 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }}

    /* GeoPulse depth system: an instrument-panel frame over the tilted map. */
    :root {{
      color-scheme: dark;
      --panel-tint: rgba(8, 17, 31, .78);
      --panel-edge: rgba(122, 211, 255, .18);
      --cyan-glow: rgba(34, 211, 238, .16);
    }}
    body {{
      background: radial-gradient(ellipse at 50% 48%, rgba(12, 42, 68, .22), transparent 54%), #050a12;
      isolation: isolate;
    }}
    body::before {{
      content: "";
      position: fixed;
      inset: 0;
      z-index: 1;
      pointer-events: none;
      background-image: linear-gradient(rgba(93, 185, 221, .025) 1px, transparent 1px),
                        linear-gradient(90deg, rgba(93, 185, 221, .025) 1px, transparent 1px);
      background-size: 54px 54px;
      mask-image: radial-gradient(ellipse at center, black 28%, transparent 82%);
    }}
    #map-container {{ filter: saturate(.88) contrast(1.08); transform: scale(1.012); }}
    .glass-panel {{
      position: relative;
      overflow: hidden;
      background: linear-gradient(145deg, rgba(18, 32, 51, .88), var(--panel-tint) 62%, rgba(6, 14, 25, .86));
      border-color: var(--panel-edge);
      box-shadow: 0 22px 55px -26px rgba(0, 0, 0, .95), 0 1px 0 rgba(224, 247, 255, .09) inset,
                  0 0 26px rgba(15, 96, 130, .08);
      transform: perspective(1100px) rotateX(.35deg);
      transition: border-color .22s ease, box-shadow .22s ease, background .22s ease;
    }}
    .glass-panel::after {{
      content: "";
      position: absolute;
      inset: 0 12% auto;
      height: 1px;
      pointer-events: none;
      background: linear-gradient(90deg, transparent, rgba(180, 237, 255, .46), transparent);
    }}
    .glass-panel:hover {{
      border-color: rgba(103, 232, 249, .3);
      box-shadow: 0 26px 64px -26px rgba(0, 0, 0, .98), 0 0 28px var(--cyan-glow), 0 1px 0 rgba(224, 247, 255, .1) inset;
    }}
    .glass-card-subtle {{
      background: linear-gradient(135deg, rgba(37, 55, 78, .58), rgba(13, 25, 42, .58));
      border-color: rgba(148, 190, 214, .1);
      box-shadow: 0 1px 0 rgba(255, 255, 255, .04) inset;
    }}
    aside {{ scrollbar-width: thin; scrollbar-color: rgba(91, 142, 172, .45) transparent; }}
    button, input {{ accent-color: #22d3ee; }}
    button {{ -webkit-tap-highlight-color: transparent; }}
    button:focus-visible, input:focus-visible {{ outline: 2px solid rgba(103, 232, 249, .85); outline-offset: 3px; }}
    #map-status-overlay {{
      position: absolute;
      inset: 50% auto auto 50%;
      z-index: 5;
      transform: translate(-50%, -50%);
      width: min(440px, calc(100vw - 32px));
      display: none;
    }}
    @media (max-width: 1180px) {{
      header {{ flex-wrap: wrap; gap: 10px; }}
      header > :nth-child(2) {{ order: 3; width: 100%; justify-content: center; }}
      header > :nth-child(3) {{ margin-left: auto; }}
      aside:first-of-type {{ width: min(360px, calc(100vw - 32px)); }}
      aside:nth-of-type(2) {{ width: 250px; }}
    }}
    @media (max-width: 760px) {{
      body, html {{ overflow: auto; min-height: 100%; }}
      #map-container {{ position: fixed; transform: none; }}
      header {{ position: fixed !important; top: 10px !important; left: 10px !important; right: 10px !important; }}
      header > :first-child {{ max-width: calc(100% - 110px); padding: 8px 10px; }}
      header > :first-child .text-xs, header > :first-child .text-\\[10px\\] {{ display: none; }}
      header > :nth-child(2) {{ overflow-x: auto; justify-content: flex-start; max-width: 100%; }}
      header > :nth-child(2) button {{ white-space: nowrap; }}
      header > :nth-child(3) {{ padding: 7px 9px; }}
      aside:first-of-type {{
        position: relative !important; top: 150px !important; left: 10px !important;
        width: calc(100vw - 20px) !important; max-height: none !important; margin-bottom: 210px;
      }}
      aside:nth-of-type(2) {{
        position: fixed !important; top: auto !important; right: 10px !important; bottom: 112px !important;
        width: min(220px, calc(100vw - 20px)) !important; max-height: 38vh; overflow-y: auto;
      }}
      body > div:last-of-type {{ position: fixed !important; bottom: 10px !important; width: calc(100vw - 20px) !important; max-width: none !important; }}
      body > div:last-of-type > div {{ padding: 12px !important; }}
      body > div:last-of-type .text-\\[10px\\] {{ display: none; }}
    }}
    @media (prefers-reduced-motion: reduce) {{
      *, *::before, *::after {{ scroll-behavior: auto !important; animation-duration: .01ms !important; transition-duration: .01ms !important; }}
    }}
  </style>
</head>
<body>

  <!-- Fullscreen 3D Map Container -->
  <div id="map-container"></div>
  <div id="map-status-overlay" class="glass-panel rounded-2xl p-5 text-center">
    <div class="text-sm font-bold text-white" id="mapStatusTitle">Loading spatial scene</div>
    <p class="mt-2 text-xs leading-relaxed text-slate-300" id="mapStatusMessage">Connecting to the basemap and preparing the local mobility snapshot.</p>
  </div>

  <!-- Top Navigation Header -->
  <header class="absolute top-4 left-4 right-4 z-20 flex items-center justify-between pointer-events-none">
    <!-- Brand Pill -->
    <div class="glass-panel px-4 py-2.5 rounded-2xl flex items-center gap-3.5 pointer-events-auto shadow-2xl">
      <div class="relative flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 via-blue-600 to-indigo-600 shadow-lg shadow-cyan-500/30">
        <span class="text-white font-black text-lg">G</span>
        <span class="absolute -top-1 -right-1 flex h-3 w-3">
          <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
          <span class="relative inline-flex rounded-full h-3 w-3 bg-cyan-500"></span>
        </span>
      </div>
      <div>
        <div class="flex items-center gap-2">
          <span class="font-extrabold text-base tracking-tight text-white">GeoPulse</span>
          <span class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 uppercase tracking-wider font-mono">
            3D Spatial Analytics v2.0
          </span>
        </div>
        <div class="text-xs text-slate-400 flex items-center gap-1.5">
          <span>Infotact Solutions</span>
          <span class="text-slate-600">•</span>
          <span class="text-slate-300 font-medium">Retail Mobility & Cannibalization Engine</span>
        </div>
      </div>
    </div>

    <!-- Quick Camera Preset Controller (Drone Orbit, Corridor Close-Up, Top-Down) -->
    <div class="glass-panel p-1.5 rounded-2xl flex items-center gap-1 pointer-events-auto">
      <button onclick="setCameraView('drone')" id="btnViewDrone" class="px-3 py-1.5 rounded-xl text-xs font-semibold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 transition flex items-center gap-1.5">
        <i data-lucide="compass" class="w-3.5 h-3.5"></i> 3D Drone View
      </button>
      <button onclick="setCameraView('corridor')" id="btnViewCorridor" class="px-3 py-1.5 rounded-xl text-xs font-semibold hover:bg-slate-800 text-slate-300 transition flex items-center gap-1.5">
        <i data-lucide="crosshair" class="w-3.5 h-3.5"></i> 5th Ave Corridor
      </button>
      <button onclick="setCameraView('techhub')" id="btnViewTechHub" class="px-3 py-1.5 rounded-xl text-xs font-semibold hover:bg-slate-800 text-slate-300 transition flex items-center gap-1.5">
        <i data-lucide="map-pin" class="w-3.5 h-3.5"></i> Store C (Tech Hub)
      </button>
      <button onclick="setCameraView('topdown')" id="btnViewTop" class="px-3 py-1.5 rounded-xl text-xs font-semibold hover:bg-slate-800 text-slate-300 transition flex items-center gap-1.5">
        <i data-lucide="layers" class="w-3.5 h-3.5"></i> 2D Ortho
      </button>
      <div class="h-4 w-[1px] bg-slate-700 mx-1"></div>
      <button onclick="toggleAutoOrbit()" id="btnOrbit" class="px-3 py-1.5 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 transition flex items-center gap-1.5">
        <i data-lucide="rotate-cw" class="w-3.5 h-3.5"></i> <span id="orbitLabel">Auto Orbit</span>
      </button>
    </div>

    <!-- System Status & Data Refresh Pill -->
    <div class="glass-panel px-3.5 py-2 rounded-2xl flex items-center gap-3 pointer-events-auto">
      <div class="flex items-center gap-1.5">
        <span id="systemStatusDot" class="w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span>
        <span id="systemStatusLabel" class="text-xs text-slate-300 font-mono">MAP CONNECTING</span>
      </div>
      <span class="text-xs text-slate-600">|</span>
      <span id="pingCountLabel" class="text-xs font-mono text-cyan-400 font-bold">LOCAL DATA</span>
    </div>
  </header>

  <!-- Left Float: Intelligence Console & Cannibalization Matrix -->
  <aside class="absolute top-24 left-4 z-20 w-[410px] max-h-[calc(100vh-125px)] overflow-y-auto space-y-3.5 pr-1.5">
    
    <!-- Executive Red Alert Banner -->
    <div class="glass-panel p-4 rounded-2xl border-l-4 border-l-red-500 neon-border-red">
      <div class="flex items-center justify-between mb-2">
        <div class="flex items-center gap-2">
          <span class="relative flex h-2.5 w-2.5">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
            <span class="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500"></span>
          </span>
          <span class="text-xs font-bold uppercase tracking-wider text-red-400 font-mono">
            Severe Cannibalization Alert
          </span>
        </div>
        <span id="cannibalAlertPct" class="text-[11px] font-mono px-2 py-0.5 rounded bg-red-500/10 text-red-300 border border-red-500/20">
          Loading overlap…
        </span>
      </div>
      <h3 class="text-sm font-bold text-white tracking-tight">
        Candidate Store B Intercepts Flagship Commuters
      </h3>
      <p class="text-xs text-slate-300 mt-1.5 leading-relaxed">
        The current overlap audit reports <strong id="alertOverlapCount">—</strong> shared devices from a base of <strong id="alertTotalCount">—</strong> for the flagship-to-candidate comparison. Adjust the simulator to explore a modeled distance scenario.
      </p>
      <div class="mt-3 pt-3 border-t border-slate-700/60 flex items-center justify-between text-xs">
        <span class="text-red-400 font-bold flex items-center gap-1">
          <i data-lucide="x-circle" class="w-3.5 h-3.5"></i> Reject Store B
        </span>
        <span class="text-emerald-400 font-bold flex items-center gap-1">
          <i data-lucide="check-circle" class="w-3.5 h-3.5"></i> Assess Store C as Alternative
        </span>
      </div>
    </div>

    <!-- Live Cannibalization Distance Sensitivity Simulator -->
    <div class="glass-panel p-4 rounded-2xl">
      <div class="flex items-center justify-between mb-2">
        <span class="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
          <i data-lucide="sliders-horizontal" class="w-3.5 h-3.5 text-cyan-400"></i> What-If Distance Simulator
        </span>
        <span id="simDistanceLabel" class="text-xs font-mono font-bold text-cyan-400">450m Separator</span>
      </div>
      <p class="text-[11px] text-slate-400 mb-2.5">
        Adjust spacing from Flagship Store A to observe dynamic reduction in commuter interception:
      </p>
      <input type="range" id="distanceSlider" min="200" max="2500" step="50" value="450"
             class="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400" />
      <div class="flex justify-between text-[10px] text-slate-500 font-mono mt-1">
        <span>200m (98% Cannibal)</span>
        <span>1,000m (35%)</span>
        <span>2,500m (0.1% Safe)</span>
      </div>
      
      <div class="mt-3 p-2.5 rounded-xl glass-card-subtle flex items-center justify-between">
        <div>
          <div class="text-[10px] uppercase text-slate-400">Simulated Overlap Rate</div>
          <div id="simOverlapDisplay" class="text-sm font-black text-red-400 font-mono">90.3% (Critical)</div>
        </div>
        <div>
          <div class="text-[10px] uppercase text-slate-400">Est. Flagship Revenue Preserved</div>
          <div id="simRevenuePreserved" class="text-sm font-black text-slate-200 font-mono">9.7% Only</div>
        </div>
      </div>
    </div>

    <!-- Target Stores & Radial Catchments (500m) -->
    <div class="glass-panel p-4 rounded-2xl">
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
          <i data-lucide="store" class="w-3.5 h-3.5 text-cyan-400"></i> Store Catchments (500m Buffer)
        </h3>
        <span id="activeStoreCount" class="text-[11px] font-mono text-slate-400">— Active Sites</span>
      </div>
      <div class="space-y-2" id="store-list-container">
        <!-- Injected via JavaScript -->
      </div>
    </div>

    <!-- Cannibalization Matrix Table (dbt Mart) -->
    <div class="glass-panel p-4 rounded-2xl">
      <h3 class="text-xs font-bold uppercase tracking-wider text-slate-300 mb-2.5 flex items-center gap-1.5">
        <i data-lucide="network" class="w-3.5 h-3.5 text-cyan-400"></i> Cross-Store Overlap Matrix (dbt)
      </h3>
      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs">
          <thead>
            <tr class="text-slate-400 border-b border-slate-700/60 font-mono text-[11px]">
              <th class="pb-1.5">Anchor</th>
              <th class="pb-1.5">Candidate</th>
              <th class="pb-1.5 text-right">Overlap %</th>
              <th class="pb-1.5 text-center">Audit</th>
            </tr>
          </thead>
          <tbody id="cannibal-tbody" class="divide-y divide-slate-800/80">
            <!-- Injected via JavaScript -->
          </tbody>
        </table>
      </div>
    </div>

    <!-- Hourly Diurnal Footfall Distribution Chart -->
    <div class="glass-panel p-4 rounded-2xl">
      <div class="flex items-center justify-between mb-2">
        <h3 class="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
          <i data-lucide="trending-up" class="w-3.5 h-3.5 text-cyan-400"></i> Diurnal Traffic Curve (24h)
        </h3>
        <span class="text-[10px] text-slate-400 font-mono">Visitors/Hr</span>
      </div>
      <div class="h-44 w-full">
        <canvas id="footfallChart"></canvas>
      </div>
    </div>

  </aside>

  <!-- Right Floating Control: Layer Toggles & 3D Parameters -->
  <aside class="absolute top-24 right-4 z-20 w-72 glass-panel p-4 rounded-2xl space-y-3.5 text-xs">
    <div class="flex items-center justify-between border-b border-slate-700/60 pb-2">
      <span class="font-bold text-slate-200 uppercase tracking-wider text-[11px] flex items-center gap-1.5">
        <i data-lucide="layers" class="w-3.5 h-3.5 text-cyan-400"></i> 3D Render Controls
      </span>
      <span class="text-[10px] text-slate-400 font-mono">Deck.gl v8.9</span>
    </div>

    <!-- Layer Toggles -->
    <div class="space-y-2">
      <label class="flex items-center justify-between p-2 rounded-xl glass-card-subtle cursor-pointer hover:bg-slate-800/50 transition">
        <span class="text-slate-300 flex items-center gap-2">
          <span class="w-2.5 h-2.5 rounded bg-cyan-400"></span> 3D H3 Hexagon Towers
        </span>
        <input type="checkbox" id="layerToggleHex" checked class="accent-cyan-400 rounded w-4 h-4 cursor-pointer" />
      </label>

      <label class="flex items-center justify-between p-2 rounded-xl glass-card-subtle cursor-pointer hover:bg-slate-800/50 transition">
        <span class="text-slate-300 flex items-center gap-2">
          <span class="w-2.5 h-2.5 rounded bg-blue-500"></span> 500m Catchment Zones
        </span>
        <input type="checkbox" id="layerToggleCatchments" checked class="accent-cyan-400 rounded w-4 h-4 cursor-pointer" />
      </label>

      <label class="flex items-center justify-between p-2 rounded-xl glass-card-subtle cursor-pointer hover:bg-slate-800/50 transition">
        <span class="text-slate-300 flex items-center gap-2">
          <span class="w-2.5 h-2.5 rounded bg-pink-500"></span> 3D Commuter Trip Arcs
        </span>
        <input type="checkbox" id="layerToggleArcs" checked class="accent-cyan-400 rounded w-4 h-4 cursor-pointer" />
      </label>

      <label class="flex items-center justify-between p-2 rounded-xl glass-card-subtle cursor-pointer hover:bg-slate-800/50 transition">
        <span class="text-slate-300 flex items-center gap-2">
          <span class="w-2.5 h-2.5 rounded bg-emerald-400"></span> Store Anchors & Beacons
        </span>
        <input type="checkbox" id="layerToggleStores" checked class="accent-cyan-400 rounded w-4 h-4 cursor-pointer" />
      </label>
    </div>

    <!-- Hex Elevation Scale Slider -->
    <div class="pt-2 border-t border-slate-700/60">
      <div class="flex items-center justify-between mb-1.5">
        <span class="text-slate-400 text-[11px]">3D Tower Elevation Scale</span>
        <span id="elevationValueLabel" class="font-mono text-cyan-400 text-[11px] font-bold">22x</span>
      </div>
      <input type="range" id="elevationSlider" min="5" max="50" step="1" value="22"
             class="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400" />
    </div>

    <!-- Hex Radius Slider -->
    <div>
      <div class="flex items-center justify-between mb-1.5">
        <span class="text-slate-400 text-[11px]">Hexagon Radius (m)</span>
        <span id="hexRadiusLabel" class="font-mono text-cyan-400 text-[11px] font-bold">95m</span>
      </div>
      <input type="range" id="hexRadiusSlider" min="40" max="180" step="5" value="95"
             class="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400" />
    </div>
  </aside>

  <!-- Bottom Floating Center: 24-Hour Time Scrubber & Transport Timeline -->
  <div class="absolute bottom-6 left-1/2 transform -translate-x-1/2 z-20 w-[720px] max-w-[92vw]">
    <div class="glass-panel px-6 py-4 rounded-3xl shadow-2xl flex flex-col gap-2.5">
      
      <!-- Time Scrubber Header -->
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3">
          <button id="btnPlayPause" class="px-4 py-1.5 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold rounded-xl text-xs transition shadow-lg shadow-cyan-500/25 flex items-center gap-1.5">
            <i data-lucide="play" class="w-3.5 h-3.5 fill-current" id="playIcon"></i>
            <span id="playBtnText">Play (24h)</span>
          </button>
          <div class="flex items-center gap-1 bg-slate-800/80 p-1 rounded-xl text-[11px]">
            <button onclick="setSpeed(1)" id="spd1" class="px-2 py-0.5 rounded-lg font-mono text-cyan-300 font-bold bg-cyan-500/20">1x</button>
            <button onclick="setSpeed(2)" id="spd2" class="px-2 py-0.5 rounded-lg font-mono text-slate-400 hover:text-white">2x</button>
            <button onclick="setSpeed(4)" id="spd4" class="px-2 py-0.5 rounded-lg font-mono text-slate-400 hover:text-white">4x</button>
          </div>
        </div>

        <div class="text-right flex items-center gap-2">
          <span id="activeHourDisplay" class="text-base font-extrabold text-cyan-400 font-mono tracking-tight">08:00 AM</span>
          <span id="activePhaseDisplay" class="text-xs text-slate-300 font-medium px-2.5 py-0.5 rounded-full bg-cyan-500/10 border border-cyan-500/20">
            Morning Commute Surge
          </span>
        </div>
      </div>

      <!-- Scrubber Slider -->
      <input type="range" id="timeScrubber" min="0" max="23" step="1" value="8"
             class="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400" />

      <!-- Timeline Milestone Indicators -->
      <div class="flex justify-between text-[10px] text-slate-500 font-mono px-1">
        <span>00:00 (Sleep)</span>
        <span class="text-slate-400">06:00 (Dawn)</span>
        <span class="text-cyan-400 font-bold">08:00 (Morning Peak)</span>
        <span class="text-amber-400 font-bold">13:00 (Lunch)</span>
        <span class="text-cyan-400 font-bold">18:00 (Evening Return)</span>
        <span>23:00 (Dormant)</span>
      </div>

    </div>
  </div>

  <!-- Embedded Data Payload -->
  <script>
    const STORES_DATA = {stores_json};
    const CATCHMENT_GEOJSON = {catchments_json};
    const HOURLY_DATA = {hourly_json};
    const CANNIBALIZATION_DATA = {cannib_json};
    const PINGS_SAMPLE = {pings_json};
    const ARCS_DATA = {arcs_json};

    // Keep the UI useful when a CDN or remote basemap is unavailable.
    let map = null;
    let mapIsReady = false;
    let deckOverlay = null;
    let currentHour = 8;
    let isPlaying = false;
    let playInterval = null;
    let playbackSpeed = 1000; // ms per frame
    let isAutoOrbiting = false;
    let orbitAnimationId = null;
    let hexElevationScale = 22;
    let hexRadius = 95;

    function setSystemStatus(label, tone = 'emerald') {{
      const labelNode = document.getElementById('systemStatusLabel');
      const dotNode = document.getElementById('systemStatusDot');
      labelNode.textContent = label;
      const toneClass = tone === 'red' ? 'bg-red-400' : tone === 'amber' ? 'bg-amber-400' : 'bg-emerald-400';
      dotNode.className = `w-2 h-2 rounded-full animate-pulse ${{toneClass}}`;
    }}

    function showMapMessage(title, message) {{
      document.getElementById('mapStatusTitle').textContent = title;
      document.getElementById('mapStatusMessage').textContent = message;
      document.getElementById('map-status-overlay').style.display = 'block';
    }}

    if (window.maplibregl) {{
      try {{
        map = new maplibregl.Map({{
          container: 'map-container',
          style: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
          center: [77.6060, 12.9760],
          zoom: 13.6,
          pitch: 58,
          bearing: -22,
          antialias: true,
          maxPitch: 70,
          attributionControl: true
        }});
        map.addControl(new maplibregl.NavigationControl(), 'bottom-right');
        map.on('load', () => {{
          mapIsReady = true;
          document.getElementById('map-status-overlay').style.display = 'none';
          setSystemStatus('MAP ONLINE', 'emerald');
          renderDeckLayers();
        }});
        map.on('error', () => {{
          if (!mapIsReady) {{
            setSystemStatus('MAP UNAVAILABLE', 'amber');
            showMapMessage('Basemap unavailable', 'Check your connection to the map tile service. The dashboard data and controls remain available.');
          }}
        }});
      }} catch (error) {{
        setSystemStatus('MAP UNAVAILABLE', 'amber');
        showMapMessage('Map could not start', 'The local dashboard is still available, but the map engine could not be initialized.');
      }}
    }} else {{
      setSystemStatus('MAP LIBRARY MISSING', 'amber');
      showMapMessage('Map library unavailable', 'The map library did not load. Check your connection and reload to restore the 3D scene.');
    }}

    document.getElementById('pingCountLabel').textContent = `${{PINGS_SAMPLE.length.toLocaleString()}} PINGS · ${{STORES_DATA.length}} SITES`;
    document.getElementById('activeStoreCount').textContent = `${{STORES_DATA.length}} Active Sites`;

    // Phase Descriptions
    const DIURNAL_PHASES = {{
      0: "Night Valley (Dormant)", 1: "Night Valley (Dormant)", 2: "Night Valley (Dormant)",
      3: "Night Valley (Minimum Flow)", 4: "Early Dawn Transition", 5: "Early Dawn Activity",
      6: "Early Commuters Awakening", 7: "Morning Rush Commute",
      8: "Morning Peak Commute (Coffee Surge)", 9: "Office Arrival Phase",
      10: "Core Commercial Business", 11: "Mid-Morning Retail Mobility",
      12: "Lunch Break Mobility", 13: "Midday Peak (Cafe & Dining)",
      14: "Afternoon Work Mobility", 15: "Afternoon Work Mobility",
      16: "Pre-Evening Transit Gathering", 17: "Evening Commute Surge",
      18: "Evening Peak Transit (Store Visits)", 19: "Dinner & Retail Leisure",
      20: "Evening Dining & Shopping", 21: "Late Evening Corridor Flow",
      22: "Night Return Commute", 23: "Night Dormancy Transition"
    }};

    function getStoreColor(status) {{
      if (status === 'EXISTING') return [59, 130, 246];          // Electric Blue
      if (status === 'PROPOSED_CANDIDATE') return [239, 68, 68];    // Crimson Red (Severe Risk)
      if (status === 'ALTERNATIVE_CANDIDATE') return [34, 197, 94]; // Emerald Green (Optimal Safe)
      return [234, 179, 8];
    }}

    // Construct 3D Deck.gl Layers
    function renderDeckLayers() {{
      if (!map || !mapIsReady) return;
      if (!window.deck || !deck.MapboxOverlay) {{
        setSystemStatus('MAP ONLINE · 2D MODE', 'amber');
        return;
      }}
      const showHex = document.getElementById('layerToggleHex').checked;
      const showCatchments = document.getElementById('layerToggleCatchments').checked;
      const showArcs = document.getElementById('layerToggleArcs').checked;
      const showStores = document.getElementById('layerToggleStores').checked;

      // Filter pings by current timeline hour
      const filteredPings = PINGS_SAMPLE.filter(p =>
        Number(p.ping_hour) === currentHour && Number.isFinite(Number(p.latitude)) && Number.isFinite(Number(p.longitude))
      );

      const layers = [];

      // 1. 3D Extruded H3 Hexagonal Density Layer
      if (showHex) {{
        layers.push(new deck.HexagonLayer({{
          id: 'hex-towers-layer',
          data: filteredPings,
          getPosition: d => [d.longitude, d.latitude],
          radius: hexRadius,
          elevationScale: hexElevationScale,
          elevationRange: [0, 1800],
          extruded: true,
          pickable: true,
          autoHighlight: true,
          highlightColor: [255, 255, 255, 80],
          material: {{
            ambient: 0.65,
            diffuse: 0.7,
            shininess: 40,
            specularColor: [60, 64, 70]
          }},
          colorRange: [
            [16, 24, 64, 180],
            [26, 75, 150, 200],
            [6, 182, 212, 220],
            [34, 197, 94, 230],
            [234, 179, 8, 240],
            [239, 68, 68, 255]
          ]
        }}));
      }}

      // 2. 500m Catchment GeoJsonLayer
      if (showCatchments) {{
        layers.push(new deck.GeoJsonLayer({{
          id: 'catchment-zones-layer',
          data: CATCHMENT_GEOJSON,
          filled: true,
          stroked: true,
          getFillColor: f => {{
            const st = f.properties.status;
            if (st === 'EXISTING') return [59, 130, 246, 45];
            if (st === 'PROPOSED_CANDIDATE') return [239, 68, 68, 60];
            return [34, 197, 94, 50];
          }},
          getLineColor: f => {{
            const st = f.properties.status;
            if (st === 'EXISTING') return [59, 130, 246, 230];
            if (st === 'PROPOSED_CANDIDATE') return [239, 68, 68, 255];
            return [34, 197, 94, 230];
          }},
          getLineWidth: 2.5,
          lineWidthUnits: 'pixels',
          pickable: true
        }}));
      }}

      // 3. 3D Parabolic Commuter Arcs Layer
      if (showArcs) {{
        const filteredArcs = ARCS_DATA.filter(a =>
          Number(a.ping_hour) === currentHour &&
          [a.origin_lon, a.origin_lat, a.dest_lon, a.dest_lat].every(value => Number.isFinite(Number(value)))
        );
        layers.push(new deck.ArcLayer({{
          id: 'commuter-arcs-layer',
          data: filteredArcs,
          getSourcePosition: d => [d.origin_lon, d.origin_lat],
          getTargetPosition: d => [d.dest_lon, d.dest_lat],
          getSourceColor: [6, 182, 212, 190],
          getTargetColor: [244, 63, 94, 210],
          getWidth: 2.2,
          getHeight: 0.6,
          greatCircle: false
        }}));
      }}

      // 4. Store Anchors & Glowing Beacon Pins
      if (showStores) {{
        layers.push(new deck.ScatterplotLayer({{
          id: 'stores-outer-glow',
          data: STORES_DATA,
          getPosition: d => [d.longitude, d.latitude],
          getFillColor: d => {{
            const c = getStoreColor(d.status);
            return [c[0], c[1], c[2], 70];
          }},
          getRadius: 160,
          radiusUnits: 'meters',
          pickable: false
        }}));

        layers.push(new deck.ScatterplotLayer({{
          id: 'stores-center-core',
          data: STORES_DATA,
          getPosition: d => [d.longitude, d.latitude],
          getFillColor: d => getStoreColor(d.status),
          getLineColor: [255, 255, 255],
          getLineWidth: 3,
          lineWidthUnits: 'pixels',
          getRadius: 55,
          radiusUnits: 'meters',
          pickable: true
        }}));

        layers.push(new deck.TextLayer({{
          id: 'stores-labels-3d',
          data: STORES_DATA,
          getPosition: d => [d.longitude, d.latitude],
          getText: d => d.store_name.split(' - ')[0],
          getSize: 15,
          getColor: [255, 255, 255, 255],
          getTextAnchor: 'start',
          getAlignmentBaseline: 'center',
          getPixelOffset: [20, -5],
          fontFamily: 'Plus Jakarta Sans',
          fontWeight: 700
        }}));
      }}

      try {{
        if (deckOverlay) {{
          deckOverlay.setProps({{ layers }});
        }} else {{
          deckOverlay = new deck.MapboxOverlay({{ layers }});
          map.addControl(deckOverlay);
        }}
      }} catch (error) {{
        setSystemStatus('MAP OVERLAY ERROR', 'amber');
        console.error('GeoPulse map overlay failed:', error);
      }}
    }}

    // Populate Sidebar UI
    function populateUIElements() {{
      const storeContainer = document.getElementById('store-list-container');
      const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, character => ({{
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
      }})[character]);
      storeContainer.innerHTML = STORES_DATA.map((s, index) => `
        <button type="button" data-store-index="${{index}}"
             class="store-focus-button w-full text-left p-2.5 rounded-xl glass-card-subtle hover:bg-slate-800/80 cursor-pointer transition flex items-center justify-between border-l-2 ${{
               s.status === 'EXISTING' ? 'border-l-blue-500' :
               s.status === 'PROPOSED_CANDIDATE' ? 'border-l-red-500' : 'border-l-emerald-500'
             }}">
          <div>
            <div class="text-xs font-bold text-white flex items-center gap-1.5">
              ${{escapeHTML((s.store_name || 'Store').split(' - ')[0])}}
              <span class="text-[10px] text-slate-400 font-normal">(${{escapeHTML((s.category || 'Site').split(' ')[0])}})</span>
            </div>
            <div class="text-[11px] text-slate-400">${{escapeHTML((s.store_name || '').split(' - ')[1] || (s.description || '').substring(0, 32))}}</div>
          </div>
          <span class="text-[10px] font-mono px-2 py-0.5 rounded ${{
            s.status === 'EXISTING' ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30' :
            s.status === 'PROPOSED_CANDIDATE' ? 'bg-red-500/20 text-red-300 border border-red-500/30 font-bold' :
            'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-bold'
          }}">${{s.status === 'PROPOSED_CANDIDATE' ? 'HIGH RISK' : s.status === 'ALTERNATIVE_CANDIDATE' ? 'OPTIMAL' : 'FLAGSHIP'}}</span>
        </button>
      `).join('');
      storeContainer.querySelectorAll('.store-focus-button').forEach(button => {{
        button.addEventListener('click', () => {{
          const site = STORES_DATA[Number(button.dataset.storeIndex)];
          if (site) focusStore(site.latitude, site.longitude);
        }});
      }});

      const cannibContainer = document.getElementById('cannibal-tbody');
      cannibContainer.innerHTML = CANNIBALIZATION_DATA.slice(0, 5).map(c => `
        <tr class="hover:bg-slate-800/50 transition">
          <td class="py-2 text-slate-200 font-medium">${{escapeHTML((c.existing_store_name || '—').split(' - ')[0])}}</td>
          <td class="py-2 text-slate-300">${{escapeHTML((c.candidate_store_name || '—').split(' - ')[0])}}</td>
          <td class="py-2 text-right font-mono font-bold ${{c.cannibalization_pct >= 25 ? 'text-red-400' : 'text-emerald-400'}}">
            ${{Number(c.cannibalization_pct || 0).toFixed(1)}}%
          </td>
          <td class="py-2 text-center">
            <span class="text-[10px] font-mono px-2 py-0.5 rounded ${{
              (c.risk_classification || '').includes('SEVERE') ? 'bg-red-500/20 text-red-300 border border-red-500/30' :
              'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
            }}">
              ${{(c.risk_classification || '').includes('SEVERE') ? 'REJECT' : 'APPROVE'}}
            </span>
          </td>
        </tr>
      `).join('');
      if (!STORES_DATA.length) storeContainer.textContent = 'No store metadata found.';
      if (!CANNIBALIZATION_DATA.length) cannibContainer.innerHTML = '<tr><td colspan="4" class="py-3 text-slate-400">No overlap audit records available.</td></tr>';
      const flagshipRisk = CANNIBALIZATION_DATA.find(row =>
        row.existing_store_id === 'STORE_A_EXISTING' && row.candidate_store_id === 'STORE_B_CANDIDATE'
      );
      if (flagshipRisk) {{
        document.getElementById('cannibalAlertPct').textContent = `${{Number(flagshipRisk.cannibalization_pct || 0).toFixed(1)}}% Overlap`;
        document.getElementById('alertOverlapCount').textContent = Number(flagshipRisk.overlapping_devices || 0).toLocaleString();
        document.getElementById('alertTotalCount').textContent = Number(flagshipRisk.existing_store_total_devices || 0).toLocaleString();
      }} else {{
        document.getElementById('cannibalAlertPct').textContent = 'No flagship audit';
      }}
    }}

    function focusStore(lat, lon) {{
      if (!map || !mapIsReady || !Number.isFinite(Number(lat)) || !Number.isFinite(Number(lon))) return;
      map.flyTo({{
        center: [lon, lat],
        zoom: 14.8,
        pitch: 62,
        bearing: -30,
        speed: 1.4,
        curve: 1.2
      }});
    }}

    // Diurnal Footfall Chart
    function initDiurnalChart() {{
      const canvas = document.getElementById('footfallChart');
      if (!canvas) return;
      if (!window.Chart) {{
        canvas.replaceWith(Object.assign(document.createElement('div'), {{
          className: 'h-full grid place-items-center text-xs text-slate-400',
          textContent: 'Chart library unavailable. Reload with internet access to show the traffic curve.'
        }}));
        return;
      }}
      const ctx = canvas.getContext('2d');
      const hours = Array.from({{length: 24}}, (_, i) => `${{i}}:00`);
      
      const storeAData = hours.map((_, h) => {{
        const r = HOURLY_DATA.find(d => d.store_id === 'STORE_A_EXISTING' && d.hour_of_day === h);
        return r ? r.unique_visitors : 0;
      }});
      const storeBData = hours.map((_, h) => {{
        const r = HOURLY_DATA.find(d => d.store_id === 'STORE_B_CANDIDATE' && d.hour_of_day === h);
        return r ? r.unique_visitors : 0;
      }});
      const storeCData = hours.map((_, h) => {{
        const r = HOURLY_DATA.find(d => d.store_id === 'STORE_C_ALTERNATIVE' && d.hour_of_day === h);
        return r ? r.unique_visitors : 0;
      }});

      new Chart(ctx, {{
        type: 'line',
        data: {{
          labels: hours,
          datasets: [
            {{ label: 'Store A (Flagship)', data: storeAData, borderColor: '#3b82f6', tension: 0.35, pointRadius: 1, borderWidth: 2 }},
            {{ label: 'Store B (Candidate)', data: storeBData, borderColor: '#ef4444', tension: 0.35, pointRadius: 1, borderWidth: 2, borderDash: [4, 2] }},
            {{ label: 'Store C (Alternative)', data: storeCData, borderColor: '#22c55e', tension: 0.35, pointRadius: 1, borderWidth: 2 }}
          ]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          plugins: {{ legend: {{ labels: {{ color: '#94a3b8', font: {{ size: 9 }} }} }} }},
          scales: {{
            x: {{ ticks: {{ color: '#64748b', font: {{ size: 8 }}, maxTicksLimit: 8 }}, grid: {{ display: false }} }},
            y: {{ ticks: {{ color: '#64748b', font: {{ size: 8 }} }}, grid: {{ color: 'rgba(255,255,255,0.04)' }} }}
          }}
        }}
      }});
    }}

    // Time Scrubber Engine
    const scrubber = document.getElementById('timeScrubber');
    const hourDisplay = document.getElementById('activeHourDisplay');
    const phaseDisplay = document.getElementById('activePhaseDisplay');
    const playBtn = document.getElementById('btnPlayPause');
    const playIcon = document.getElementById('playIcon');
    const playBtnText = document.getElementById('playBtnText');

    function updateTimeScrubber(val) {{
      currentHour = parseInt(val);
      scrubber.value = currentHour;
      const formatted = `${{currentHour.toString().padStart(2, '0')}}:00 ${{currentHour >= 12 ? 'PM' : 'AM'}}`;
      hourDisplay.textContent = formatted;
      phaseDisplay.textContent = DIURNAL_PHASES[currentHour] || "Intra-Day Mobility";
      renderDeckLayers();
    }}

    scrubber.addEventListener('input', (e) => updateTimeScrubber(e.target.value));

    function startPlayback() {{
      if (isPlaying) return;
      isPlaying = true;
      playBtnText.textContent = "Pause";
      playIcon.setAttribute('data-lucide', 'pause');
      if (window.lucide && typeof lucide.createIcons === 'function') lucide.createIcons();
      playInterval = setInterval(() => {{
        let next = (currentHour + 1) % 24;
        updateTimeScrubber(next);
      }}, playbackSpeed);
    }}

    function pausePlayback() {{
      isPlaying = false;
      playBtnText.textContent = "Play (24h)";
      playIcon.setAttribute('data-lucide', 'play');
      if (window.lucide && typeof lucide.createIcons === 'function') lucide.createIcons();
      clearInterval(playInterval);
    }}

    playBtn.addEventListener('click', () => {{
      if (isPlaying) pausePlayback(); else startPlayback();
    }});

    function setSpeed(multiplier) {{
      ['spd1', 'spd2', 'spd4'].forEach(id => {{
        document.getElementById(id).classList.remove('bg-cyan-500/20', 'text-cyan-300', 'font-bold');
        document.getElementById(id).classList.add('text-slate-400');
      }});
      document.getElementById('spd' + multiplier).classList.add('bg-cyan-500/20', 'text-cyan-300', 'font-bold');
      playbackSpeed = 1000 / multiplier;
      if (isPlaying) {{
        pausePlayback();
        startPlayback();
      }}
    }}

    // Preset Camera Viewports
    function setCameraView(preset) {{
      if (!map || !mapIsReady) return;
      ['btnViewDrone', 'btnViewCorridor', 'btnViewTechHub', 'btnViewTop'].forEach(id => {{
        document.getElementById(id).classList.remove('bg-cyan-500/20', 'text-cyan-300', 'border', 'border-cyan-500/40');
        document.getElementById(id).classList.add('hover:bg-slate-800', 'text-slate-300');
      }});

      if (preset === 'drone') {{
        document.getElementById('btnViewDrone').classList.add('bg-cyan-500/20', 'text-cyan-300', 'border', 'border-cyan-500/40');
        map.flyTo({{ center: [77.6060, 12.9760], zoom: 13.6, pitch: 58, bearing: -22, speed: 1.2 }});
      }} else if (preset === 'corridor') {{
        document.getElementById('btnViewCorridor').classList.add('bg-cyan-500/20', 'text-cyan-300', 'border', 'border-cyan-500/40');
        map.flyTo({{ center: [77.6062, 12.9765], zoom: 15.2, pitch: 64, bearing: -35, speed: 1.4 }});
      }} else if (preset === 'techhub') {{
        document.getElementById('btnViewTechHub').classList.add('bg-cyan-500/20', 'text-cyan-300', 'border', 'border-cyan-500/40');
        map.flyTo({{ center: [77.6245, 12.9352], zoom: 14.5, pitch: 50, bearing: 15, speed: 1.4 }});
      }} else if (preset === 'topdown') {{
        document.getElementById('btnViewTop').classList.add('bg-cyan-500/20', 'text-cyan-300', 'border', 'border-cyan-500/40');
        map.flyTo({{ center: [77.6060, 12.9650], zoom: 12.8, pitch: 0, bearing: 0, speed: 1.2 }});
      }}
    }}

    // Auto-Orbit Drone Camera
    function toggleAutoOrbit() {{
      if (!map || !mapIsReady) return;
      isAutoOrbiting = !isAutoOrbiting;
      const btn = document.getElementById('btnOrbit');
      const label = document.getElementById('orbitLabel');
      
      if (isAutoOrbiting) {{
        btn.classList.add('bg-cyan-500/20', 'text-cyan-300', 'border', 'border-cyan-500/40');
        label.textContent = "Stop Orbit";
        function orbitStep() {{
          if (!isAutoOrbiting) return;
          const currentBearing = map.getBearing();
          map.setBearing((currentBearing + 0.15) % 360);
          orbitAnimationId = requestAnimationFrame(orbitStep);
        }}
        orbitStep();
      }} else {{
        btn.classList.remove('bg-cyan-500/20', 'text-cyan-300', 'border', 'border-cyan-500/40');
        label.textContent = "Auto Orbit";
        if (orbitAnimationId !== null) cancelAnimationFrame(orbitAnimationId);
        orbitAnimationId = null;
      }}
    }}

    // Interactive Distance Simulator
    const distSlider = document.getElementById('distanceSlider');
    const simDistanceLabel = document.getElementById('simDistanceLabel');
    const simOverlapDisplay = document.getElementById('simOverlapDisplay');
    const simRevenuePreserved = document.getElementById('simRevenuePreserved');

    function modeledOverlap(distance) {{
      const anchors = [[200, 98], [450, 90.3], [1000, 35], [2500, 0.1]];
      const d = Math.max(200, Math.min(2500, Number(distance) || 450));
      for (let i = 1; i < anchors.length; i++) {{
        if (d <= anchors[i][0]) {{
          const [x0, y0] = anchors[i - 1];
          const [x1, y1] = anchors[i];
          const t = (d - x0) / (x1 - x0);
          return y0 + (y1 - y0) * t;
        }}
      }}
      return anchors[anchors.length - 1][1];
    }}

    function updateDistanceSimulation(distance) {{
      const d = Number(distance) || 450;
      simDistanceLabel.textContent = `${{d}}m Separator`;
      const modeledCannib = modeledOverlap(d);
      
      simOverlapDisplay.textContent = `${{modeledCannib.toFixed(1)}}% (${{modeledCannib >= 30 ? 'Critical' : modeledCannib >= 15 ? 'Moderate' : 'Safe'}})`;
      simOverlapDisplay.className = `text-sm font-black font-mono ${{
        modeledCannib >= 30 ? 'text-red-400' : modeledCannib >= 15 ? 'text-amber-400' : 'text-emerald-400'
      }}`;
      
      const preserved = (100 - modeledCannib).toFixed(1);
      simRevenuePreserved.textContent = `${{preserved}}%`;
    }}

    distSlider.addEventListener('input', (e) => updateDistanceSimulation(e.target.value));
    updateDistanceSimulation(distSlider.value);

    // 3D Sliders & Layer Controls
    ['layerToggleHex', 'layerToggleCatchments', 'layerToggleArcs', 'layerToggleStores'].forEach(id => {{
      document.getElementById(id).addEventListener('change', renderDeckLayers);
    }});

    document.getElementById('elevationSlider').addEventListener('input', (e) => {{
      hexElevationScale = parseInt(e.target.value);
      document.getElementById('elevationValueLabel').textContent = `${{hexElevationScale}}x`;
      renderDeckLayers();
    }});

    document.getElementById('hexRadiusSlider').addEventListener('input', (e) => {{
      hexRadius = parseInt(e.target.value);
      document.getElementById('hexRadiusLabel').textContent = `${{hexRadius}}m`;
      renderDeckLayers();
    }});

    // Keyboard Shortcuts (Spacebar = Play/Pause, Arrow Left/Right = Time Scrubber)
    window.addEventListener('keydown', (e) => {{
      const target = e.target;
      if (target && (['INPUT', 'TEXTAREA', 'SELECT', 'BUTTON'].includes(target.tagName) || target.isContentEditable)) return;
      if (e.code === 'Space') {{
        e.preventDefault();
        if (isPlaying) pausePlayback(); else startPlayback();
      }} else if (e.code === 'ArrowRight') {{
        updateTimeScrubber((currentHour + 1) % 24);
      }} else if (e.code === 'ArrowLeft') {{
        updateTimeScrubber((currentHour - 1 + 24) % 24);
      }}
    }});

    populateUIElements();
    initDiurnalChart();
    updateTimeScrubber(currentHour);
    if (window.lucide && typeof lucide.createIcons === 'function') lucide.createIcons();
    window.addEventListener('beforeunload', () => {{
      if (playInterval) clearInterval(playInterval);
      if (orbitAnimationId !== null) cancelAnimationFrame(orbitAnimationId);
      if (map) map.remove();
    }}, {{ once: true }});
  </script>
</body>
</html>
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_code, encoding="utf-8")

    print(f"[GeoPulse] 3D dashboard successfully built at: {output_path}")


if __name__ == "__main__":
    generate_cutting_edge_dashboard()
