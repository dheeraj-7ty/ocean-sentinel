# Ocean Sentinel

> **Earth-Observation Maritime Investigation & SAR Anomaly Platform**
> Operational real-data Sentinel-1 acquisition, SHA-256 integrity binding and provenance metadata, fail-closed SAR validation, and REST API evidence orchestration.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Governance: V2](https://img.shields.io/badge/Governance-V2%20Active-brightgreen.svg)](docs/governance/)
[![Tests: 235 Passing](https://img.shields.io/badge/Tests-235%20In--Scope%20Pass-success.svg)](tests/)
[![Scientific Execution: Gated](https://img.shields.io/badge/Scientific%20Execution-Gated-orange.svg)](docs/CURRENT_STATUS.md)

---

## 1. Mission

Ocean Sentinel is an Earth-observation maritime investigation platform engineered to process real synthetic aperture radar (SAR) observations from the European Space Agency's Copernicus constellation.

The system provides an end-to-end, fail-closed operational bridge from user-defined spatio-temporal requests to validated, SHA-256 integrity-bound satellite evidence:
- **Discovers** Sentinel-1 GRD observations matching user Areas of Interest (AOI).
- **Retrieves** real dual-polarization (`[VV, VH]`) radar rasters from the Copernicus Data Space Ecosystem (CDSE).
- **Persists** acquired imagery atomically with SHA-256 integrity digests and structured metadata sidecars.
- **Validates** radiometric properties, geospatial coordinate reference systems, and polarization channel contracts (`Ch0 = VH`, `Ch1 = VV`).
- **Orchestrates** investigation runs via a 10-stage `ScientificDAG` through a deterministic lifecycle into a structured operational evidence state (`READY_FOR_DETECTION`).
- **Recovers** deterministically after process interruption without duplicate stage re-execution.
- **Streams** real-time Server-Sent Events (SSE) and durable operational telemetry with `Last-Event-ID` replay.

For current operational state and metrics, see [**`docs/CURRENT_STATUS.md`**](docs/CURRENT_STATUS.md), [**`docs/PHASE_7A_INVESTIGATION_RUN_KERNEL.md`**](docs/PHASE_7A_INVESTIGATION_RUN_KERNEL.md), and [**`docs/PHASE_7B_EVENT_SPINE_AND_TELEMETRY.md`**](docs/PHASE_7B_EVENT_SPINE_AND_TELEMETRY.md).

---

## 2. Current Verified State

| Status Dimension | Verified Reality | Evidence Authority |
| :--- | :--- | :--- |
| **Current Milestone** | **Phase 7B: Event Spine & Stream Telemetry** | `InvestigationEvent`, `DurableEventLog`, `EventBus`, SSE & Telemetry Proof |
| **Operational Pipeline** | **Operational synchronous acquisition workflow, durable spine & observable event stream verified** | Proven via live CDSE, live REST API, crash-recovery, and SSE smoke tests |
| **Scientific Safety** | **Strictly Gated (`EXECUTION_AUTHORIZED = False`)** | `OperationalDetectionBoundary` fail-closed firewall |
| **Protected Baseline** | **8/8 Canonical baseline files bitwise intact (100%)** | `test_all_eight_protected_baseline_hashes_match` |
| **Automated Tests** | **235/235 In-scope tests passing (100%)** | 11 governed operational, spine, event, and guardrail suites |
| **Git Working Tree** | **Clean (0 staged, 0 modified, 0 untracked)** | Synchronized with `origin/master` |
| **Next Milestone** | **Phase 7C: 3D Geospatial Investigation Globe** | Interactive 3D Visualization & Investigation Console |

---

## 3. Operational Pipeline Architecture

The Phase 6 operational chain transforms raw satellite data into validated, audit-ready operational evidence:

```
[ Operator / API Request ]
            │  (AOI Polygon + Datetime Window + Polarization [VV, VH])
            ▼
    [ REQUESTED ] ─────────── (Job Manifest Initialized in outputs/jobs/)
            │
            ▼
   [ DISCOVERING ] ────────── (Copernicus CDSE STAC Search: sentinel-1-grd)
            │
            ▼
    [ ACQUIRING ] ─────────── (Copernicus Sentinel Hub Process API: Multi-Band Float32 GeoTIFF)
            │
            ▼
   [ PERSISTING ] ─────────── (Atomic Storage to data/raw/acquisitions/ + Metadata Sidecar)
            │
            ▼
    [ VALIDATING ] ────────── (SHA-256 Hash Binding + SAR Preflight + Mapping A Channel Order)
            │
            ▼
[ READY_FOR_DETECTION ] ───── (Structured Operational Evidence State: execution_authorized=False, has_prediction=False)
```

### Core Operational Invariants
1. **Synchronous REST Lifecycle**: `POST /api/v1/acquisitions` executes synchronously, running discovery, materialization, persistence, and preflight validation, returning only after reaching a terminal state.
2. **Collision-Resistant Job Identifiers**: Job IDs are generated as `acq_{timestamp}_{token_hex(4)}`—unique, collision-resistant operational tokens.
3. **Canonical Persistence Namespace**: Materialized rasters and sidecars persist under `data/raw/acquisitions/{product_id}/`.
4. **Host Path Sanitization**: API responses sanitize host filesystem paths into relative references, preventing local machine environment leakage.
5. **Channel Order Determinism**: Dual-polarization rasters are validated and stacked so that Channel 0 is always VH and Channel 1 is always VV (Mapping A contract), invariant to provider band response order.
6. **Empirical Raster Format**: Observations are materialized as multi-band, strip-organized GeoTIFFs (`driver: GTiff`, `dtype: float32`, `tiled: False`), bound by SHA-256 digests.

---

## 4. Scientific Safety & Gating

Ocean Sentinel enforces a strict architectural firewall between operational data acquisition and scientific inference:

```yaml
SCIENTIFIC_SAFETY_STATE:
  EXECUTION_AUTHORIZED: false
  MODEL_INFERENCE: 0 (Zero forward passes executed)
  MODEL_TRAINING: 0 (Zero parameter weight updates)
  HOLDOUT_EVALUATION: 0 (Zero holdout dataset access)
  TRUJILLO_PART_III_ACCESS: 0 (Quarantined)
  THRESHOLD_TUNING: 0 (Zero threshold adjustment)
  SCIENTIFIC_DETECTION_CLAIMS: 0 (Zero candidate slicks claimed)
  VESSEL_ATTRIBUTION: 0 (Zero causal blame assigned)
```

The canonical trained model checkpoint [`experiments/performance/exp06_positive_bce_weight/best_model.pt`](experiments/performance/exp06_positive_bce_weight/best_model.pt) is verified against the canonical SHA-256 digest (`B5FFCCA3...E8DF`) derived dynamically from [`experiments/ARTIFACT_REGISTRY.md`](experiments/ARTIFACT_REGISTRY.md) Section 7.1.

---

## 5. Verified Capabilities vs. Gated Boundaries

| Capability Category | Verified Operational Capabilities | Gated / Future Capabilities |
| :--- | :--- | :--- |
| **Satellite Access** | Real Copernicus CDSE OAuth2 token management, STAC catalog search, and Sentinel Hub Process API multi-band retrieval. | Automatic multi-scene batch scheduling across distributed clusters. |
| **Persistence & Provenance** | Atomic GeoTIFF file writes, SHA-256 hash verification, JSON metadata sidecars, and manifest logging. | Cloud object store (S3/GCS) direct streaming adapters. |
| **SAR Validation** | Dimensions, float32 dtype, EPSG:4326 CRS, non-empty raster checks, and Mapping A channel ordering (`Ch0=VH, Ch1=VV`). | On-the-fly Doppler centroid correction or terrain correction. |
| **API Surface** | FastAPI endpoints (`/api/v1/acquisitions`, `/api/v1/acquisitions/{job_id}`, `/api/v1/acquisitions/{job_id}/result`, `/api/v1/health`). | Asynchronous background task workers (Celery/Redis/arq). |
| **Scientific Inference** | Operational SAR preflight checks and dynamic canonical checkpoint hash derivation. | **GATED**: Model forward passes, segmentation masks, and slick candidate extraction. |
| **Vessel Attribution** | Spatio-temporal heuristic alignment demonstration (`AIS_ABSENCE_IS_NOT_VESSEL_ABSENCE`). | **GATED**: Legal or causal blame attribution. |

---

## 6. Project History & Reconciled Taxonomy

The repository history comprises four historical / current engineering tracks plus one planned next engineering track:

1. **Track 1: Foundation & Data Access Prototype (Phases 1A – 1C)**: Initial package layout, Copernicus OAuth2 authentication, STAC discovery, and exploratory preprocessing. *(Historical / Superseded)*
2. **Track 2: Scientific Research & ML Training (Phases 2 – 8, EXP-01 – EXP-08)**: Baseline model exploration, hard negative training (EXP-03–EXP-06), Part III external evaluation, and OPS-01/OPS-02 dataset split freezes. *(Historical Research Baseline)*
3. **Track 3: Governance V2 & Repository Integration**: 8 protected baseline files, machine-verifiable rule/lesson/incident catalogs, 10-commit-group integration, and surgical artifact accounting. *(Governed / Active)*
4. **Track 4: Operational Pipeline (Phases 6A – 6C)**: Fail-closed operational SAR pipeline, live CDSE acquisition proof, persistent GeoTIFF storage, and FastAPI REST endpoints. *(Operational Baseline / Complete)*
5. **Track 5: Investigation Spine & Presentation Layer (Phase 7)**: Investigation run kernel and durable execution spine (Phase 7A: Complete), event spine & telemetry (Phase 7B: Next / Planned), and 3D operational globe interface (Phase 7C: Future / Planned). *(Current / Active Engineering Track)*

For the complete evidence-backed timeline, see [**`docs/PROJECT_PHASE_HISTORY.md`**](docs/PROJECT_PHASE_HISTORY.md).
For the complete claim-to-proof mapping, see [**`docs/EVIDENCE_MATRIX.md`**](docs/EVIDENCE_MATRIX.md).

---

## 7. Evidence & Governance Integrity

### 7.1 Protected Baseline (8/8 Match)
Under strict CAO repository policy, the following 8 canonical files are frozen:
1. `data/metadata/governance_v2/rules.json`
2. `data/metadata/governance_v2/lessons.json`
3. `data/metadata/governance_v2/incidents.json`
4. `src/ocean_sentinel/governance/runner.py`
5. `src/ocean_sentinel/ingestion/dataset.py`
6. `src/ocean_sentinel/temporal.py`
7. `experiments/performance/exp06_positive_bce_weight/best_model.pt`
8. `docs/exp08_corrected_protocol.md`

### 7.2 Cross-AI Evidence Inventory
- **Total Declared Sources**: 17
- **Accessible & Evaluated**: 13 (AI-SRC-001 through AI-SRC-013; AI-SRC-008 is formally superseded)
- **Unavailable / Unverified**: 4 (AI-SRC-014 Claude, AI-SRC-015 Perplexity, AI-SRC-016 ChatGPT/Codex, AI-SRC-017 OpenCode)

---

## 8. Repository Structure

```
ocean-sentinel/
├── src/ocean_sentinel/          # Core Python package
│   ├── api/                     # FastAPI backend application, routes, and Pydantic schemas
│   ├── satellite/               # Copernicus CDSE OAuth2, STAC discovery, imagery, persistence
│   ├── orchestration/           # Acquisition job orchestrator, state machine, job store
│   ├── processing/              # SAR backscatter, dB conversion, and normalization
│   ├── ingestion/               # Dataset ingestion schemas and spatial contracts
│   ├── governance/              # Governed preflight runner and integrity checkers
│   ├── operational_pipeline.py  # Phase 6 operational SAR pipeline & detection boundary
│   ├── temporal.py              # Temporal change analysis & timeline geometry
│   ├── drift.py                 # Particle drift simulation & windage models
│   ├── ais.py                   # Vessel AIS trajectory ingestion & correlation
│   └── fusion.py                # Multi-source evidence fusion & scoring
├── tests/                       # Automated test battery (142 files; 216 in-scope tests)
├── scripts/                     # Operational runners (run_backend.py, verify_auth.py, etc.)
├── docs/                        # Architecture, reports, status, and governance contracts
│   ├── CURRENT_STATUS.md        # Single authoritative current-state document
│   ├── PROJECT_PHASE_HISTORY.md # Complete chronological phase evolution
│   └── EVIDENCE_MATRIX.md       # Traceable claim-to-proof verification matrix
├── experiments/                 # ML research artifacts, experiment logs, ARTIFACT_REGISTRY.md
├── frontend/                    # Vite + React 19 + TypeScript + Three.js web UI console
├── data/                        # Governed metadata catalogs & raw acquisition storage
└── outputs/                     # Investigation evidence payloads and job execution logs
```

---

## 9. Development & Testing Quickstart

### Prerequisites
- **Python**: CPython >= 3.10 (managed with `uv` or `venv`)
- **Node.js**: >= 18.x (for frontend web console)
- **Copernicus CDSE Account**: (Optional for unit tests; required for live Earth-observation acquisitions)

### Installation

```bash
# Clone the repository
git clone https://github.com/dheeraj-7ty/ocean-sentinel.git
cd ocean-sentinel

# Create and activate virtual environment (using uv)
uv venv .venv
source .venv/bin/activate       # Linux/macOS
# .venv\Scripts\activate        # Windows

# Install package with development dependencies
uv pip install -e ".[dev]"
```

### Running In-Scope Automated Tests

The authoritative in-scope test suite comprises 235 tests across 11 operational, investigation spine, event, and policy suites:

```bash
# Run the 235 in-scope operational, spine, event & guardrail tests
pytest \
  tests/test_acquisition_job.py \
  tests/test_backend_api.py \
  tests/test_acquisition_persistence.py \
  tests/test_operational_pipeline.py \
  tests/test_imagery_service.py \
  tests/test_discovery.py \
  tests/test_pipeline_orchestration.py \
  tests/test_source_control_policy_and_reporting_guardrails.py \
  tests/test_artifact_policy.py \
  tests/test_investigation_spine.py \
  tests/test_event_spine.py
```

### Running the Backend API Server

```bash
# Launch the FastAPI operational backend (port 8000)
python scripts/run_backend.py --host 127.0.0.1 --port 8000 --reload
```
- API Base: `http://127.0.0.1:8000`
- Interactive OpenAPI Docs: `http://127.0.0.1:8000/docs`
- Health Check: `http://127.0.0.1:8000/api/v1/health`

### Running the Frontend Console

```bash
cd frontend
npm install
npm run dev
```
- Web Console: `http://localhost:5173` (proxies `/api` to `http://127.0.0.1:8000`)

---

## 10. Roadmap & Engineering Tracks

- **Phase 7A: Investigation Run Kernel & Durable Scientific Execution Spine** (`COMPLETE`):
  - Durable `InvestigationRun` lifecycle kernel, `InvestigationContext`, and 10-stage `ScientificDAG`.
  - Content-integrity verification via `ArtifactRef` SHA-256 bindings.
  - Granular `StageAttempt` audit ledgers and protocol-derived idempotency fingerprinting.
  - Process-restart crash recovery with fail-closed remediation for corrupted artifacts.
  - Strict preservation of the scientific safety boundary (`EXECUTION_AUTHORIZED = False`).

- **Phase 7B: Event Spine & Stream Telemetry** (`COMPLETE`):
  - Typed `InvestigationEvent` domain model and canonical event taxonomy.
  - Append-only durable event log (`events.jsonl`) with sequence monotonicity and crash recovery.
  - In-process non-blocking `EventBus` subscriber hub with run-level isolation.
  - Server-Sent Events (SSE) streaming (`/api/v1/investigations/{run_id}/events`) with `Last-Event-ID` cursor replay.
  - Live operational telemetry without fabricating uncomputed scientific metrics.

- **Phase 7C: 3D Operational Globe & Geospatial Investigation Interface** (`NEXT / PLANNED`):
  - Connect the Three.js interactive 3D globe console directly to the investigation REST API.
  - Visualize Sentinel-1 observation footprints, AOI bounding polygons, and validated GeoTIFF evidence.
  - Maintain the scientific safety firewall (`EXECUTION_AUTHORIZED = False`).

---

## 11. Security

- Credentials are loaded exclusively via environment variables or a local `.env` file (excluded from Git).
- Secrets are wrapped in Pydantic `SecretStr` to prevent accidental serialization, logging, or API exposure.
- All API responses sanitize server host filesystem paths to safe relative references.
- No secrets or credentials are ever committed to version control.

---

## 12. License

MIT
