# Ocean Sentinel — Canonical Project Phase & Evolution History

**Authoritative Project History & Phase Reconciliation Document**
**Version**: `1.0.0`
**Classification**: CANONICAL PROJECT HISTORY

---

## 1. Executive Taxonomy Reconciliation

Project Ocean Sentinel's development history is structured across four historical / current engineering tracks plus one planned next engineering track. Because these tracks originated in separate historical project workstreams that have now been unified into a single coherent repository, phase numbers can recur across distinct tracks (for example, historical scientific Phase 6 external evaluation vs. operational Phase 6A–6C pipeline; historical scientific Phase 7 lookalikes vs. planned operational Phase 7 3D globe interface).

```
TRACK 1: HISTORICAL PROTOTYPE & DATA ACCESS (Phases 1A – 1C) [HISTORICAL]
   │
   ▼
TRACK 2: HISTORICAL SCIENTIFIC RESEARCH & ML (Phases 2 – 8, EXP-01 – EXP-08) [HISTORICAL RESEARCH BASELINE]
   │
   ▼
TRACK 3: GOVERNANCE V2 & REPOSITORY INTEGRATION (10-Commit Group Boundary) [GOVERNED / ACTIVE]
   │
   ▼
TRACK 4: CURRENT OPERATIONAL PIPELINE (Phases 6A – 6C) [CURRENT COMPLETED MILESTONE]
   │
   ▼
TRACK 5: PLANNED OPERATIONAL VISUALIZATION & GLOBE (Phase 7) [PLANNED NEXT ENGINEERING TRACK]
```

---

## 2. Track 1: Foundation & Satellite Access Prototype (Phases 1A – 1C)

*Status*: **HISTORICAL / SUPERSEDED BY PRODUCTION STACK**

| Milestone | Objective | Implementation Scope | Verification / Proof | Disposition |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 1A** | Foundation & Core Models | Basic package structure, Pydantic configuration, AOI models, error taxonomy. | Unit tests in `tests/test_config.py`, `tests/test_models.py` | Complete |
| **Phase 1B.1** | Copernicus OAuth2 | CDSE token exchange, token caching, credential security. | `src/ocean_sentinel/satellite/auth.py`, `tests/test_auth.py` | Active in Prod |
| **Phase 1B.2** | STAC Product Discovery | Spatio-temporal STAC queries for Sentinel-1 GRD imagery. | `src/ocean_sentinel/satellite/discovery.py`, `tests/test_discovery.py` | Active in Prod |
| **Phase 1B.3** | Process API Imagery Retrieval | Sentinel Hub evalscript generation and raw raster retrieval. | `src/ocean_sentinel/satellite/imagery.py`, `tests/test_imagery_service.py` | Active in Prod |
| **Phase 1C.1** | SAR Preprocessing | Backscatter conversion, invalid masking, dB normalization. | `src/ocean_sentinel/processing/sar.py`, `tests/test_preprocessing.py` | Historical |
| **Phase 1C.2** | Dataset Reconnaissance | Analysis of Trujillo et al. (2024) Peruvian dataset vs CDSE. | `docs/dataset-reconnaissance.md`, `docs/dataset-selection.md` | Complete |

---

## 3. Track 2: Scientific Research, ML Training & External Validation (Phases 2 – 8)

*Status*: **HISTORICAL RESEARCH BASELINE / FROZEN UNDER CANONICAL REGISTRY**

| Phase / Milestone | Research Objective | Key Artifacts & Deliverables | Verification State |
| :--- | :--- | :--- | :--- |
| **Phase 2 (EXP-01, EXP-02a)** | Baseline U-Net Model & Qualitative Audit | `experiments/exp01_baseline/`, qualitative error galleries | Evaluated on Kaggle GPU |
| **Phase 3 & 4 (Trujillo Part III)** | External Dataset Qualification & Ingestion | `docs/trujillo-dataset-contract.md`, Part III pairing manifest | Physical Qualification Passed |
| **Phase 5 (EXP-03 – EXP-06)** | Hard Negative Training & Loss Re-weighting | Canonical checkpoint `experiments/performance/exp06_positive_bce_weight/best_model.pt` | Converged; Frozen Baseline |
| **Phase 6 (Historical Sept 12)** | External Evaluation on Part III Holdout | `experiments/PHASE_6_PART_III_EXTERNAL_EVALUATION_REPORT_20260912.md` | Evaluation Complete |
| **Phase 7 (Historical Sept 12-13)** | Lookalike Benchmarks & Physical Proxy | `experiments/PHASE_7A_DATA_PROTOCOL_FOUNDATION_REPORT_20260912.md` | Methodological Audit Passed |
| **Phase 8 (Historical Sept 13)** | OPS-01 / OPS-02 Dataset Construction | `data/ops02/` manifests, training freeze audits | Ingestion Complete & Frozen |
| **EXP-07 & EXP-08** | Replication Pilots & Calibration Analysis | `docs/exp08_corrected_protocol.md` (Protected baseline file #8) | Governed Protocol Registered |

> [!IMPORTANT]
> **Distinction Between Phase 6 Scientific vs Phase 6 Operational**:
> - **Historical Phase 6 (Sept 12, 2026)**: Evaluated model weight performance against external Peruvian SAR holdouts.
> - **Operational Phase 6 (Oct 2026)**: Engineered the operational, real-data Earth-observation ingestion, persistence, and REST API pipeline.

---

## 4. Track 3: Governance V2 & Repository Integration

*Status*: **GOVERNED / ACTIVE**

| Milestone | Objective | Key Deliverables | Governance Impact |
| :--- | :--- | :--- | :--- |
| **Governance V2 Architecture** | Machine-verifiable rules, lessons, and incidents catalogs. | `data/metadata/governance_v2/` (`rules.json`, `lessons.json`, `incidents.json`), `runner.py` | 8 Protected Baseline Files Established |
| **Evidence Semantics (V1–V5)** | Orthogonal six-dimension state taxonomy & quarantine. | `ocean_sentinel_evidence_state_semantics_final.md` | Fail-closed provenance enforcement |
| **10-Group Git Integration** | Clean integration of 819 canonical tracked files. | `docs/OCEAN_SENTINEL_SOURCE_CONTROL_INTEGRATION_V2_REPORT.md` (Commits `6237e06`..`63af216`) | Zero untracked files; clean Git working tree |
| **Artifact Registry Policy** | Accounting of 36 preserved checkpoints and 264 external assets. | `experiments/ARTIFACT_REGISTRY.md` | Surgical `.gitignore` boundaries |
| **Cross-AI Evidence Audit** | Formal reconciliation of 17 declared AI evidence sources. | 13 accessible/evaluated, 4 unavailable/unverified, AI-SRC-008 superseded | Integrity ledger synchronized |

---

## 5. Track 4: Operational Pipeline (Phases 6A – 6C)

*Status*: **CURRENT VERIFIED MILESTONE (COMPLETE)**

| Sub-Phase | Focus Area | Technical Scope | Empirical Proof / Tests |
| :--- | :--- | :--- | :--- |
| **Phase 6A** | Pipeline Foundation | Fail-closed pipeline boundary, spatial/temporal validation, polarization handling (`Ch0=VH`, `Ch1=VV`). | `src/ocean_sentinel/operational_pipeline.py`, `tests/test_operational_pipeline.py` (25 tests) |
| **Phase 6B** | Live Acquisition & Persistence | Authenticated retrieval of real Copernicus Sentinel-1 observation (`S1A_IW_GRDH_..._D2F2_COG`), atomic GeoTIFF persistence, SHA-256 sidecars. | Direct CDSE live smoke test passed; `tests/test_acquisition_persistence.py` (11 tests) |
| **Phase 6C** | Acquisition Job & API Surface | Full state machine (`REQUESTED` → `READY_FOR_DETECTION`), FastAPI REST API (`/api/v1/acquisitions`), evidence result endpoint. | Direct live HTTP API smoke test passed; `tests/test_acquisition_job.py` (22 tests), `tests/test_backend_api.py` (20 tests) |
| **Phase 6C Hardening** | Contract Hardening & Reconciliation | Test cardinality reconciled (201 in-scope tests), dynamic canonical checkpoint hash derivation from ARTIFACT_REGISTRY, API path sanitization, proven polarization order invariance under inverted input `[VV, VH]`. | PR #11 (`3c5ca81`), all 201 in-scope tests passing |

---

## 6. Track 5: Next Engineering Milestone (Phase 7)

*Status*: **PLANNED / NEXT ACTIVE ENGINEERING MILESTONE**

- **Milestone Name**: **Phase 7 — 3D Operational Globe & Geospatial Investigation Interface**
- **Objective**: Connect the existing React/Three.js frontend dashboard (`frontend/`) directly to the Phase 6C REST API surface (`/api/v1/acquisitions`).
- **Target Capabilities**:
  - Interactive 3D globe visualization of user AOI polygons and Sentinel-1 observation footprints.
  - Real-time job lifecycle tracking via HTTP polling against `/api/v1/acquisitions/{job_id}`.
  - Inspection of persisted GeoTIFF metadata, SAR preflight attributes, and evidence objects in terminal state `READY_FOR_DETECTION`.
  - Strict preservation of the scientific safety boundary (`EXECUTION_AUTHORIZED = False`).
