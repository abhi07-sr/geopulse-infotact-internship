# GeoPulse: Hyper-Local Retail Mobility Analytics
## Executive Review Presentation Deck (Deliverable 4)

**Intern:** Abhinandan Naik  
**Role:** Data Associate L1. Intern – Data Analytics Domain  
**Organization:** Infotact Solutions (Bengaluru, Karnataka)  
**Ref. No.:** ITS/DA/1797  

---

### Slide 1: Title & Introduction
* **Header**: GeoPulse: Hyper-Local Retail Mobility Analytics
* **Sub-header**: Uncovering Store Cannibalization & Optimizing Commercial Site Selection
* **Presenter**: Abhinandan Naik, Data Associate L1. Intern
* **Host Organization**: Infotact Solutions, Bengaluru
* **Date**: November 2026

---

### Slide 2: The Core Problem – The Retail Site Selection Fallacy
* **Traditional Approach**: Retailers select sites using static census and annual demographic tables.
* **The Blindspot**: Static boundaries are blind to intra-day foot traffic movement and commuter trajectories.
* **The Costly Consequence**: A new branch often intercepts customers who already patronize an existing store—cannibalizing 30–50% of sales while doubling lease and operating costs.
* **Objective**: Replace guesswork with dynamic, high-frequency spatial mobility intelligence.

---

### Slide 3: Use Case – The Coffee Chain Dilemma
* **Scenario**: Real Estate Director evaluating a new store location on "5th Avenue North" (Candidate Store B), 450 meters from their premier Flagship (Store A).
* **Initial Assumption**: Census shows high commercial foot traffic density—recommendation appears to be "Open Store B".
* **GeoPulse Investigation**: Ingest 240,000 mobile GPS pings, compute 500m catchment polygons, and run cross-store temporal overlap algorithms.

---

### Slide 4: Modern Data Stack Architecture
* **Ingestion Layer**: High-velocity anonymized mobile GPS telemetry (DeviceID, Lat, Long, Timestamp).
* **Lakehouse**: Cloud Geospatial Lakehouse utilizing native `GEOGRAPHY` types and spatial clustering.
* **Spatial Transformation**: Apache Sedona / PySpark distributed point-in-polygon & 500m catchment joins.
* **ELT & Modeling**: dbt (Data Build Tool) staging, hourly footfall aggregation, and cannibalization marts.
* **BI & 3D Visualization**: Kepler.gl + Deck.gl + React, rendering 3D H3 hexagons, origin-destination trip arcs, and a 24-hour time-scrubbing animation.

---

### Slide 5: Mid-Project Audit & Performance Benchmarks
* **Data Scale**: 240,000 raw GPS pings across 6,000 devices.
* **Spatial Join Performance**: Completed in **0.82 seconds** (throughput > 290,000 pings/sec).
* **Memory Safety**: Zero OOM errors, peak memory under 180 MB.
* **Diurnal Peak Validation**: Accurately captured morning commute surge (9,649 visitors at 8–10 AM) and evening transit surge (8,812 visitors at 5–7 PM).
* **dbt Test Status**: 100% pass rate across uniqueness, non-null, and distribution constraints.

---

### Slide 6: Key Analytics Finding – The 90.3% Cannibalization Trap
* **Store A (Existing Flagship)**: 2,778 daily unique catchment visitors.
* **Store B (Candidate Site)**: Intercepts **2,509 of Store A's existing visitors** (**90.32% cannibalization**).
* **The Interception Mechanism**: Morning commuters traveling down 5th Avenue reach Store B first, intercepting Store A's footfall before they reach the flagship.
* **Executive Decision**: **REJECT Store B** to avoid internal revenue cannibalization.

---

### Slide 7: Strategic Pivot – The Store C Discovery
* **Alternative Evaluated**: Store C (Outer Ring Road Tech Hub Corridor), located 2.4 km away.
* **Overlap with Store A**: **0.04%** (only 1 shared device).
* **Independent Capture**: 1,623 net-new unique daily visitors.
* **Outcome**: Opening Store C expands total brand reach by **+58.4% net-new foot traffic**, maximizing return on capital expenditure.

---

### Slide 8: Interactive 3D Demonstration (Kepler.gl / Deck.gl)
* **3D H3 Hexagonal Density**: Highlights real-time pedestrian clusters at street-level resolution.
* **24-Hour Time Slider**: Real-time scrubbing from 00:00 to 23:00 showing morning vs. evening flow transitions.
* **Dynamic Origin-Destination Arcs**: Illustrates transit flows between residential origins and commercial destinations.
* **Executive Action Badges**: Automated Red Alert on Store B, Green Approval on Store C.

---

### Slide 9: Project Value & Industry Impact
* **Capital Protection**: Saved multi-million rupee investment by preventing a redundant, cannibalizing lease.
* **Repeatable Enterprise Pipeline**: Fully orchestrated via Apache Airflow DAG for automated daily execution.
* **Scalable Foundation**: Modular dbt models ready for deployment across any global metropolitan market.

---

### Slide 10: Conclusion & Q&A
* Thank you to Infotact Solutions, Ms. Jyotirmayee Behera, and the Data Analytics team.
* Questions & Live System Demonstration.
