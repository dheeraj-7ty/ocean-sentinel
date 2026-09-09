# Ocean Sentinel — Project Context & Operating Model

**Document Version**: 1.0.0  
**Status**: ACTIVE / CANONICAL ONBOARDING CONTEXT  
**Date**: September 2026  
**Repository**: `D:\Projects\ocean-sentinel`  
**Primary Sources**: `README.md`, `docs/architecture.md`, `docs/configuration.md`, CAO Project Mandate  

---

## 1. Project Mission & Identity

Ocean Sentinel is a professional geospatial intelligence and maritime surveillance platform designed to detect, verify, investigate, and attribute marine oil pollution using Sentinel-1 Synthetic Aperture Radar (SAR) imagery, automated segmentation models, temporal change detection, and Automatic Identification System (AIS) vessel tracking data.

> [!IMPORTANT]
> Ocean Sentinel is engineered as an enterprise-grade operational intelligence system, **not** a generic dashboard, demo prototype, or toy SaaS application. Scientific validity, radiometric correctness, traceability, and leakage-safe machine learning are mandatory foundational requirements.

---

## 2. End-to-End Target Intelligence Chain

```
[ REAL SATELLITE RADAR DATA ]
Copernicus Data Space Ecosystem (CDSE)
             │
             ▼
[ DISCOVERY & INGESTION ]
Sentinel-1 STAC Search & Sentinel Hub Process API (Dual-Pol VV + VH)
             │
             ▼
[ RADIOMETRIC PREPROCESSING ]
Linear σ⁰ ↔ dB Calibration, Deterministic Validity Masking, Normalization
             │
             ▼
[ DETECTION & SEGMENTATION ]
Deep Learning SAR Oil-Spill Segmentation (Mineral Oil vs Look-Alikes)
             │
             ▼
[ TEMPORAL CHANGE ANALYSIS ]
Historical SAR Baseline Differencing (Pre-Spill vs Post-Spill Verification)
             │
             ▼
[ AIS VESSEL CORRELATION ]
Spatio-Temporal Trajectory Intersect (Bilge Dumps, Ship Wakes, Tanker Tracks)
             │
             ▼
[ SOURCE ATTRIBUTION & EVIDENCE ]
Vessel Identity, MMSI, Course, Confidence Scoring, Spill Volume Estimation
             │
             ▼
[ INVESTIGATION WORKBENCH & ASK EARTH ]
Geospatial Intelligence UI, Multi-Sensor Inspection, Natural Language Analytics
```

---

## 3. Project Operating Model

The project follows a rigorous, engineering-first development loop:
$$\text{Think} \longrightarrow \text{Architect} \longrightarrow \text{Prompt} \longrightarrow \text{Implement} \longrightarrow \text{Report} \longrightarrow \text{Evaluate} \longrightarrow \text{Fix} \longrightarrow \text{Integrate} \longrightarrow \text{Audit}$$

### Role Matrix & Responsibilities
* **Chief Architect Officer (CAO)**:
  - Owns end-to-end architecture, technical strategy, and interface boundaries.
  - Decides when phases are complete and authorizes transitions.
  - Reviews and signs off on architectural changes and dataset acquisition.
* **Antigravity (Implementation Engineer)**:
  - Inspects existing repository state before taking action.
  - Implements approved tasks adhering strictly to established contracts.
  - Validates all code empirically with automated test suites and real API runs.
  - Documents evidence, interfaces, and limitations transparently.
* **Dheeraj (Project Lead)**:
  - Coordinates execution across sessions and accounts.
  - Provides human authorization for cross-cutting decisions, large data pulls, and external credentials.

---

## 4. Core Engineering Non-Negotiables

1. **No Fake AI / Simulated Metrics**: Every metric, score, or classification must derive from a verified mathematical or ML implementation. Random or hardcoded confidence values are strictly prohibited.
2. **No Fake Completion**: Claiming a test passed, an API worked, or a dataset downloaded without empirical execution is treated as a critical defect.
3. **No Uncalibrated Data**: SAR imagery must be tracked with explicit radiometric semantics (linear $\sigma^0$ vs $\text{dB}$). Lossy 8-bit formats (JPEG/PNG) are barred from calibration pipelines.
4. **Leakage-Safe Methodology**: Random splitting of spatial patches or tiles is forbidden. Splitting must respect group identity by parent scene or patch index.
5. **Architectural Discipline**: Never optimize or alter one module in isolation without evaluating its systemic impact on downstream consumers. Significant architectural decisions require an Architecture Decision Record (ADR).
6. **Credential Protection**: Zero tolerance for logging, printing, or versioning OAuth tokens, client secrets, or private keys. `SecretStr` masking and sanitized reprs must be maintained at all times.

---

## 5. UI/UX Vision & Target Experience

* **Theme & Tone**: Dark-mode operational command center (slate, obsidian, subtle radar cyan/amber accents).
* **Investigation Map**: High-performance Leaflet/MapLibre canvas with SAR layer blending, false-color composite toggles (VV/VH ratio), and vector spill polygon overlays.
* **Timeline Scrubber**: Temporal slider comparing historical passes against anomalous acquisitions.
* **Attribution Panel**: Side-by-side dossier displaying candidate vessels, AIS track intercepts, distance to slick centroid, and weather/wind context.
* **Ask Earth Console**: Context-aware natural-language terminal for querying anomalies, vessel fleets, and historical geographic statistics.\n