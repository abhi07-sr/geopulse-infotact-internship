# Project Report: GeoPulse – Hyper-Local Retail Mobility Analytics

**Internship Organization:** Infotact Solutions (Bengaluru, Karnataka)  
**Author:** Abhinandan Naik  
**Designation:** Data Associate L1. Intern – Data Analytics Domain  
**Document Ref. No.:** ITS/DA/1797  
**Project Duration:** 10 November 2026 – 10 December 2026  

---

## 1. Introduction & Background

In the hyper-competitive retail and quick-service restaurant (QSR) industries, location decisions are among the largest drivers of long-term profitability. However, real estate teams have traditionally relied upon static demographic charts and annual municipal census data. 

While static data outlines where individuals reside, it is fundamentally blind to dynamic human mobility: where people travel, which transit corridors they walk down at 8:30 AM for coffee, and how foot traffic distributes across commercial sectors throughout the day.

This analytical blind spot frequently produces catastrophic real estate investments known as **store cannibalization**: opening a new branch that merely captures footfall already visiting an existing location, doubling operating costs and rent while producing near-zero incremental revenue.

The **GeoPulse** project was engineered to replace static assumptions with dynamic, high-velocity geospatial mobility intelligence.

---

## 2. Problem Statement & Business Objective

### Problem Statement
A retail chain seeks to expand its footprint in a high-density urban corridor. Market planners identified a candidate location on **5th Avenue North ("Store B")**, located approximately 450 meters from their top-performing existing branch, **Store A ("5th Ave Flagship")**. Static census data indicated high commercial viability. However, management lacked visibility into whether Store B would capture net-new foot traffic or merely cannibalize Store A.

### Core Objectives
1. **High-Velocity Data Ingestion**: Synthesize and ingest high-frequency, anonymized mobile GPS telemetry (DeviceID, Lat, Long, Timestamp) mimicking authentic diurnal urban movement.
2. **Distributed Spatial Catchments**: Construct 500-meter radial catchment buffer polygons around existing and candidate stores and execute distributed point-in-polygon spatial joins.
3. **ELT Data Modeling**: Build modular **dbt** models to aggregate hourly footfall and calculate the mathematical **Cannibalization Index** over time.
4. **Interactive 3D Visual BI**: Deliver an interactive **Kepler.gl / Deck.gl** mobility dashboard with 3D H3 hexagonal density layers, trip vectors, and a 24-hour interactive time scrubber.
5. **Workflow Automation**: Orchestrate the complete pipeline with an Apache Airflow DAG for reproducible daily updates.

---

## 3. System Architecture & Modern Data Stack

GeoPulse implements an enterprise Modern Data Stack (MDS) tailored for high-volume coordinate geometry:

```
[Raw GPS Ping Telemetry] (240k+ points)
            │
            ▼
[Geospatial Lakehouse] (Snowflake / DuckDB GEOGRAPHY)
            │
            ▼
[Distributed Spatial Joins] (Apache Sedona / Geodesic Macro)
            │
            ▼
[dbt ELT Transformation Models]
  ├── Staging: stg_gps_pings, stg_stores
  └── Marts: fct_hourly_footfall, fct_store_cannibalization
            │
            ▼
[Interactive BI & Decision Layer]
  ├── 3D H3 Hexagonal Density (Deck.gl / Kepler.gl)
  ├── 24-Hour Timeline Scrubber (00:00 - 23:00)
  └── Executive Cannibalization Alerts
```

---

## 4. Methodology & Mathematical Formulations

### 4.1 Geodesic Spatial Catchment Join
For every GPS ping $P_i = (\phi_p, \lambda_p)$ and store centroid $S_j = (\phi_s, \lambda_s)$, the exact distance $d(P_i, S_j)$ on the WGS84 sphere is calculated via the Haversine formula:
$$d = 2 R \arcsin\left(\sqrt{\sin^2\left(\frac{\Delta \phi}{2}\right) + \cos(\phi_p)\cos(\phi_s)\sin^2\left(\frac{\Delta \lambda}{2}\right)}\right)$$
where $R = 6,371,000\text{ meters}$. A ping is joined to store $S_j$ if and only if $d(P_i, S_j) \le 500.0\text{ meters}$.

To optimize execution across hundreds of thousands of records, a bounding-box pre-filter eliminates $>90\%$ of non-qualifying candidate pairs prior to trigonometric computation:
$$|\phi_p - \phi_s| \le 0.0055^\circ \quad \text{and} \quad |\lambda_p - \lambda_s| \le 0.0055^\circ$$

### 4.2 Cannibalization Percentage Formula
The Cannibalization Percentage represents the proportion of an existing store's unique visitor base intercepted by a candidate site:
$$\text{Cannibalization \%} = \frac{|D_{\text{Candidate}} \cap D_{\text{Existing}}|}{|D_{\text{Existing}}|} \times 100$$
where $D_{\text{Existing}}$ and $D_{\text{Candidate}}$ represent the distinct sets of `device_id`s recorded within the respective 500m catchment areas over the observation period.

---

## 5. Experimental Results & Key Findings

### 5.1 Pipeline Execution Benchmarks
The pipeline was tested and audited using 240,000 telemetry records generated across 6,000 distinct device trajectories:
- **Spatial Join Runtime**: **0.82 seconds** (throughput: >292,000 pings/sec).
- **dbt Model Compilation & Execution**: **0.21 seconds**.
- **Memory Safety**: Zero Out-of-Memory (OOM) errors; peak memory utilization remained under 180 MB.
- **dbt Test Pass Rate**: 100% across all schema uniqueness, nullability, and temporal distribution assertions.

### 5.2 Diurnal Commuter Flow Validation
Aggregated footfall within store catchments demonstrated sharp diurnal characteristics:
- **Morning Surge (08:00–10:00 AM)**: 9,649 unique visitors (predominantly pedestrian coffee and transit commuters).
- **Midday Surge (12:00–14:00 PM)**: 5,920 unique visitors (commercial lunch/break traffic).
- **Evening Surge (17:00–19:00 PM)**: 8,812 unique visitors (reverse commute transit).
- **Night Baseline (01:00–04:00 AM)**: 1,968 unique visitors (dormant local resident activity).

### 5.3 Cannibalization Discovery
The dbt mart `dbt_fct_store_cannibalization` generated the following cross-store matrix:

| Existing Store | Candidate Store | Existing Unique Visitors | Overlapping Devices | Cannibalization % | Risk Classification | Recommendation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Store A (Flagship)** | **Store B (Candidate)** | 2,778 | 2,509 | **90.32%** | **SEVERE_RISK** | **REJECT LOCATION** |
| **Store B (Candidate)** | **Store A (Flagship)** | 2,557 | 2,509 | **98.12%** | **SEVERE_RISK** | **REJECT LOCATION** |
| **Store A (Flagship)** | **Store C (Alternative)** | 2,778 | 1 | **0.04%** | **LOW_OVERLAP** | **APPROVE SITE** |
| **Store D (Residential)**| **Store A (Flagship)** | 1,787 | 14 | **0.78%** | **LOW_OVERLAP** | **PROCEED** |

---

## 6. Business Impact & Strategic Recommendations

1. **Immediate Capital Protection**:
   The candidate site **Store B (5th Ave North)** intercepts **90.32%** of existing Flagship Store A's commuter footfall. Placing a new branch at Store B would dilute flagship revenues without generating significant net-new customer acquisition. The system generated an automated recommendation: **REJECT STORE B**.
   
2. **High-ROI Site Selection**:
   The alternative site **Store C (Outer Ring Road Tech Hub)** recorded an overlap of only **0.04%** with Store A, while capturing **1,623 independent unique visitors** per day. Opening Store C increases total chain customer reach by **+58.4%**, maximizing revenue growth per capital invested.

3. **Operational Readiness**:
   The pipeline is fully automated via an **Apache Airflow DAG** (`src/orchestration/airflow_dag_geopulse.py`), enabling continuous ingestion, automated daily modeling, and automated executive alerts when proposed sites breach the 30% cannibalization threshold.

---

## 7. Deliverables Checklist & Sign-Off

* [x] **Source Code**: Fully modular scripts for simulation, distributed Sedona joins, local DuckDB runner, dbt project, and visualization frontend.
* [x] **Project Documentation**: Master README, architectural blueprints, and data dictionary.
* [x] **Formal Project Report**: This document detailing problem formulation, methodology, benchmarks, and real estate conclusions.
* [x] **Presentation Deck**: Complete 10-slide executive review deck (`docs/presentation_deck.md`).
* [x] **Model Evaluation Results**: Quantitative spatial benchmarks, memory safety audits, and test suites (`docs/model_evaluation_results.md`).
* [x] **Interactive Demonstration**: Standalone 3D interactive dashboard (`dashboard/index.html`) and Streamlit application (`dashboard/app.py`).

---
*Submitted in partial fulfillment of the Data Analytics Internship at Infotact Solutions.*
