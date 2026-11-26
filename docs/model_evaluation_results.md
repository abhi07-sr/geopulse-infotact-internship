# GeoPulse Model & Spatial Pipeline Evaluation Results

**Document Type:** Formal Evaluation Report (Deliverable 5)  
**Author:** Abhinandan Naik, Data Associate L1. Intern  
**Project:** "GeoPulse": Hyper-Local Retail Mobility Analytics  
**Organization:** Infotact Solutions  

---

## 1. Executive Summary

This evaluation document benchmarks the performance, throughput, memory safety, and data integrity of the **GeoPulse** spatial mobility pipeline against the technical requirements specified in the project document.

Key milestones verified:
- **Spatial Join Benchmark**: Zero memory exhaustion (no OOM), executing spatial point-in-polygon joins over 240,000 pings in **0.82 seconds**.
- **Query Optimization**: Complex multi-hop cannibalization and spatial aggregation queries executed in **< 100 ms**.
- **Data Integrity**: dbt models compiled with 100% test pass rate, validating realistic morning (08:00–10:00 AM) and evening (17:00–19:00 PM) commuter traffic spikes.

---

## 2. Quantitative Performance & Spatial Join Benchmarks

| Metric | Target Specification | Achieved Result | Evaluation Status |
| :--- | :--- | :--- | :--- |
| **Ingested Telemetry Volume** | > 100,000 pings | **240,000 pings** (6,000 devices) | **EXCEEDED** |
| **Spatial Join Execution Time** | < 10.0 seconds | **0.820 seconds** | **EXCEEDED** (12x faster) |
| **Join Throughput** | > 20,000 pings/sec | **292,682 pings/sec** | **EXCEEDED** |
| **Memory Footprint** | Stable (No OOM) | Peak RSS **< 180 MB** | **PASSED (Safe)** |
| **Catchment Intersections** | Validated (500m radius) | **107,423 pings** (44.7% capture) | **PASSED** |
| **dbt Mart Materialization** | < 2.0 seconds | **0.214 seconds** | **EXCEEDED** |
| **dbt Test Pass Rate** | 100% | **100% (3/3 test suites passed)** | **PASSED** |

---

## 3. Data Integrity & Diurnal Distribution Verification

The pipeline was subjected to temporal distribution audits to verify that synthetic mobility faithfully mirrors human commuter behavior:

```
Hour Range       Phase Classification       Observed Unique Visitors    Traffic Spike Ratio
00:00 - 05:00    Night Dormancy Valley      1,968 visitors              1.0x (Baseline)
08:00 - 10:00    Morning Commute Peak       9,649 visitors              4.9x Spike (Expected)
12:00 - 14:00    Midday Lunch Break         5,920 visitors              3.0x Surge
17:00 - 19:00    Evening Transit Peak       8,812 visitors              4.5x Spike (Expected)
```

**Conclusion:** The traffic distribution accurately reflects urban commuting dynamics, fulfilling the Week 2 mid-project audit requirements.

---

## 4. Cannibalization Audit & Business Impact Validation

### Cross-Store Matrix Findings:

| Existing Store | Candidate Store | Existing Visitors | Overlapping Devices | Overlap % | Real Estate Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Store A (Flagship)** | **Store B (5th Ave North)** | 2,778 | 2,509 | **90.32%** | **REJECT LOCATION** |
| **Store B (Candidate)** | **Store A (Flagship)** | 2,557 | 2,509 | **98.12%** | **REJECT LOCATION** |
| **Store A (Flagship)** | **Store C (Tech Hub)** | 2,778 | 1 | **0.04%** | **PROCEED / EXPAND** |
| **Store D (Residential)**| **Store A (Flagship)** | 1,787 | 14 | **0.78%** | **HEALTHY / INDEPENDENT** |

### Strategic Business Conclusion
- **Store B**: Candidate location on 5th Ave North is placed directly on the same pedestrian transit funnel. Proceeding with Store B would split existing sales rather than capturing new market share.
- **Store C**: Located along the Outer Ring Road Tech Hub corridor, capturing an independent pool of 1,623 unique daily visitors with virtually zero overlap ($<0.1\%$). This represents an optimal ROI expansion target.
