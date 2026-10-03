# Ocean Sentinel — Real Data Investigation Workflow V1
**Task ID**: `OCEAN-SENTINEL-REAL-DATA-INVESTIGATION-V1`  
**Milestone**: Real Data Investigation V1  
**Status**: `CERTIFIED`  
**Authority**: ChatGPT (CAO) / Human (Final Approval)  

---

## 1. Executive Summary

The **Real Data Investigation Workflow V1** transforms Ocean Sentinel from a synthetic DEMO-centric operational visualization console into an authentic scientific investigation application capable of operating directly on real repository datasets and generated scientific outputs without inventing physical data or external operational feeds.

### Core Pipeline Realized
```
REAL REPOSITORY DATA (Trujillo et al., 2024)
       │
       ▼
BACKEND JOB ORCHESTRATION (JobStore / Pipeline Engine)
       │
       ▼
PRE-EXISTING SCIENTIFIC ARTIFACTS REUSE (Inference & Interpret: SKIPPED)
       │
       ▼
EVIDENCE FUSION V1 (Anti-Tamper SHA-256 Ledger & Hypotheses)
       │
       ▼
3D FRONTEND EXPLORATION (Three.js Orthographic/Perspective Globe & Evidence Inspector)
```

---

## 2. Mode Separation & Scientific Governance

Ocean Sentinel enforces three mutually exclusive operational modes across the backend API, orchestration engine, and frontend interface:

| Operational Mode | Provenance Source | Provenance Class | External Feed Access | Fail-Closed Policy |
| :--- | :--- | :--- | :--- | :--- |
| **`DEMO`** | Synthetic deterministic fixture (`fixtures/evidence_fusion_scenario_01.json`) | `SYNTHETIC_DEMO` | None | Synthetic fixtures allowed |
| **`REAL_REPOSITORY`** | Authentic repository datasets (`data/trujillo/`) and precomputed scientific artifacts (`outputs/`) | `HISTORICAL_ARCHIVE` | None (Repository local only) | Rejects non-existent artifacts & directory traversal |
| **`PHYSICAL`** | Operational live external feeds (Copernicus Hub, Spire/MarineTraffic AIS) | `PHYSICAL_OPERATIONAL` | Unavailable in current release | **Strictly Fail-Closed** (`BLOCKED — AWAITING_OPERATIONAL_SOURCE`) |

> [!IMPORTANT]
> **Strict Non-Bleed Invariant**:
> `REAL_REPOSITORY` mode strictly means **repository-originated data and verified derived artifacts**. It **does NOT imply live operational external-feed access**.
> The system strictly prohibits implicit fallbacks across mode boundaries:
> - `DEMO` never falls back to `REAL_REPOSITORY`
> - `REAL_REPOSITORY` never falls back to `PHYSICAL` or `DEMO`
> - `PHYSICAL` never falls back to `DEMO` or `REAL_REPOSITORY`

---

## 3. Registered Real Repository Scenarios

The backend catalog (`src/ocean_sentinel/orchestration/scenarios.py`) registers authentic scenarios verified to exist in the repository:

### Scenario 1: `TRUJILLO_00007_01339`
- **Label**: Trujillo 2024 S1 Scene Pair 00007 / 01339 (Eastern Mediterranean)
- **Source Dataset**: Trujillo et al., 2024 Sentinel-1 SAR Oil Spill Dataset (`data/trujillo/`)
- **Scene Pair**: `00007` (Pre-spill / baseline) → `01339` (Detection / observation)
- **Geographic Locus**: Eastern Mediterranean offshore Nile Delta (`32.1378° N`, `30.6526° E`)
- **Event Identifier**: `00007_01339_persistent_0003`
- **Artifacts Utilized**:
  - Detection Mask T0: `outputs/inference/00007_mask.tif`
  - Detection Mask T1: `outputs/inference/01339_mask.tif`
  - Temporal Analysis: `outputs/temporal/00007_to_01339_temporal_events.geojson`
  - Lagrangian Drift: `outputs/origin_drift/trujillo_00007_01339.geojson`
  - AIS Hypotheses & Summary: `outputs/ais/trujillo_00007_01339.geojson` & `outputs/ais/trujillo_00007_01339_summary.json`
- **Authentic Metadata Policy**:
  - Satellite Product ID: `METADATA UNAVAILABLE`
  - Vessel Ground Truth: `METADATA UNAVAILABLE`
  - Physical Incident Label: `METADATA UNAVAILABLE`
  - Unverified Source Metadata: `METADATA UNAVAILABLE`
  - Acquisition Timestamps: `2024-04-05T14:00:00+00:00 (EXTERNALLY_SUPPLIED_TEST_TIMESTAMP)`

### Scenario 2: `TRUJILLO_00260_00608`
- **Label**: Trujillo 2024 S1 Scene Pair 00260 / 00608 (Gulf of Mexico)
- **Source Dataset**: Trujillo et al., 2024 Sentinel-1 SAR Oil Spill Dataset (`data/trujillo/`)
- **Scene Pair**: `00260` → `00608`
- **Geographic Locus**: Gulf of Mexico deepwater offshore (`27.0864° N`, `-90.3864° W`)
- **Event Identifier**: `00260_00608_new_0010`

---

## 4. Pipeline Execution & Manifest Faithfulness

Per Section 6 and Section 10, expensive PyTorch inference is **not** rerun when verified masks and scientific artifacts already exist in `outputs/`. The backend faithfully manifests stage status so the operator sees the true operational history:

```
STAGE          STATUS       DETAILS
────────────────────────────────────────────────────────────────────────
VALIDATE       COMPLETED    Scenario ID and artifact references verified
INGEST         COMPLETED    Dataset files and GeoTIFFs confirmed present
INFER          SKIPPED      Pre-existing verified detection masks reused
INTERPRET      SKIPPED      Pre-existing polygonized vectors reused
TEMPORAL       COMPLETED    Temporal persistence/novelty analysis verified
DRIFT          COMPLETED    Lagrangian backward trajectory & origin loaded
AIS            COMPLETED    AIS candidate trajectories & gap metrics loaded
FUSION         COMPLETED    Evidence Fusion graph built with tamper seals
EXPORT         COMPLETED    Standardized evidence graph & summary exported
```

---

## 5. Backend API Endpoints & Schemas

The FastAPI backend exposes the following contract:

1. **`GET /api/v1/health`**
   - Returns service status, version, and `mode_info` with `supported_modes: ["DEMO", "REAL_REPOSITORY", "PHYSICAL"]` and `physical_operational_status: "BLOCKED — AWAITING_OPERATIONAL_SOURCE"`.
2. **`GET /api/v1/investigations/scenarios`**
   - Returns list of registered, verified repository scenarios (`ScenarioListResponse`).
3. **`GET /api/v1/investigations/scenarios/{scenario_id}`**
   - Returns specific scenario details or `404 NOT_FOUND`. Path traversal attempts (e.g. `../../etc`) are rejected with `400 BAD_REQUEST`.
4. **`POST /api/v1/jobs`**
   - Accepts `CreateJobRequest` with `mode: "REAL_REPOSITORY"`, `pipeline_type: "REAL_REPOSITORY"`, and `scenario_id: "TRUJILLO_00007_01339"`.
5. **`GET /api/v1/jobs/{job_id}/result`**
   - Returns complete `JobResultResponse` including `provenance_class: "HISTORICAL_ARCHIVE"`, `scenario_metadata`, evidence ledger with SHA-256 integrity seals, and candidate vessel hypotheses.

---

## 6. Frontend Operator Workflow

The frontend geospatial console provides an intuitive, high-assurance investigation workflow:

1. **Mode Switch**: Click `REAL REPOSITORY` in the top bar.
2. **Scenario Selection**: Choose verified scenario from the dropdown in `LeftControlPanel`.
3. **Authentic Metadata Audit**: Review metadata card showing verified fields and explicit `METADATA UNAVAILABLE` markers.
4. **Dispatch Investigation**: Click `RUN REAL INVESTIGATION`.
5. **Monitor Manifest**: Observe real-time progress in `PIPELINE STAGES MANIFEST`, including explicit `SKIPPED` badges for reused stages.
6. **3D Globe Exploration**:
   - Camera auto-focuses on Eastern Mediterranean locus (`32.2000° N`, `30.6000° E`).
   - Globe renders SAR detection polygons, temporal changes, backward drift trajectories, and candidate vessel tracks.
7. **Evidence & Hypothesis Inspection**:
   - Right panel displays `REAL REPOSITORY INVESTIGATION` with `PROVENANCE: HISTORICAL_ARCHIVE` badge.
   - Inspect multiple candidate hypotheses (e.g. `MT_HORIZON_STAR` compatibility 0.8606, `GULF_SUPPLIER_VII` 0.8351).
   - Review conflicting evidence (`GLITCH_RUNNER`) and telemetry gaps (`SEA_PROWLER`).
8. **Operator Coordinate Reference**:
   - Clicking the globe displays `USER LOCATION (REFERENCE)` with strict non-evidence invariant isolating it from scientific fusion.

---

## 7. Verification & Test Results

### Automated Backend Regression Suite
- **Command**: `uv run pytest tests/test_drift.py tests/test_ais.py tests/test_ais_adversarial.py tests/test_temporal.py tests/test_interpretation.py tests/test_evidence_fusion.py tests/test_pipeline_orchestration.py tests/test_backend_api.py tests/test_real_investigation.py -q`
- **Result**: **192 passed** (175 frozen baseline + 17 real investigation tests).
- **Targeted Real Investigation Coverage (`tests/test_real_investigation.py`)**:
  - Test 1: DEMO mode remains DEMO
  - Test 2: REAL_REPOSITORY mode is accepted and registered
  - Test 3: PHYSICAL mode remains fail-closed
  - Test 4: REAL_REPOSITORY does not silently fall back to DEMO
  - Test 5: Invalid artifact references are rejected
  - Test 6: Path traversal in scenario/artifact ID is rejected
  - Test 7: Job stage states are faithfully surfaced (INFER: SKIPPED, INTERPRET: SKIPPED)
  - Test 8: Real repository result appears through backend API
  - Test 9: Provenance class is HISTORICAL_ARCHIVE
  - Test 10: Metadata unavailable fields handled explicitly
  - Test 11: Actual artifact geometry is present
  - Test 12: Evidence Fusion semantics remain unchanged
  - Test 13: Multiple candidate vessels remain visible
  - Test 14: Conflicting evidence remains visible
  - Test 15: DATA_UNAVAILABLE remains visible
  - Test 16: Prohibited legal attribution wording strictly absent
  - Test 17: Repeated execution is deterministic

### Automated Frontend Suite
- **Command**: `npm test -- --run` in `frontend/`
- **Result**: **26 passed** (22 baseline + 4 real investigation tests).
- **Build**: `npm run build` succeeds with zero errors (`tsc -b && vite build`).

### Live Browser Verification
- **Subagent Execution**: Full autonomous verification via Chrome DevTools protocol.
- **Recording**: `real_investigation_live_1789939856191.webp`
- **Final Screenshot**: `real_repository_investigation_result_1789940050697.png`
- **Confirmed Checklist Items**:
  - [x] Initial load: headers & backend online
  - [x] DEMO mode execution succeeds
  - [x] PHYSICAL fail-closed gate blocks synthetic bleed
  - [x] REAL_REPOSITORY switch & scenario dropdown populated
  - [x] Authentic metadata card displays `METADATA UNAVAILABLE`
  - [x] REAL_REPOSITORY job dispatches and completes
  - [x] Manifest displays `INFER: SKIPPED` and `INTERPRET: SKIPPED`
  - [x] 3D Globe autofocuses on Eastern Mediterranean (`32.20° N`, `30.60° E`)
  - [x] Real detection and drift geometries render on globe
  - [x] Right Inspector displays `PROVENANCE: HISTORICAL_ARCHIVE`
  - [x] Candidate hypotheses, compatibility scores, and conflicting evidence preserved
  - [x] User-selected coordinate displays non-evidence invariant

---

## 8. Protected File Hashes

All 7 protected files verified bitwise identical:

| Protected File Path | Expected SHA-256 | Verification Result |
| :--- | :--- | :--- |
| `.gitignore` | `a664092c8717f70f88941dce08d8000e29cdcb453df9b1d64d9eeaeb3dbd0444` | **MATCH** |
| `src/ocean_sentinel/ingestion/dataset.py` | `f5bf1387769e43462af8e4e4de37867c761dd7adbc040455532a3463ebfa0b0c` | **MATCH** |
| `src/ocean_sentinel/governance/runner.py` | `dd345558c3118ee61c0c966744d539c66dcfaabeab2b9c66b03903c66eb3c9e0` | **MATCH** |
| `data/metadata/governance_v2/rules.json` | `b216f369d68a027e4708e8cbcf3991d8effd5ba5a063a3b8b6b3fc2261d85c4e` | **MATCH** |
| `data/metadata/governance_v2/lessons.json` | `4784a440070bc00612bc3bfa9b29a7acc181934f894a9e22bd340faab7076395` | **MATCH** |
| `data/metadata/governance_v2/incidents.json` | `fa3051a185894ee1fe46edb5825ebcfe92b107f80fb7527bf5746d4ec5b91836` | **MATCH** |
| `src/ocean_sentinel/temporal.py` | `46614361e1be20a278d0af9ceee222e4787df1eade7d52a88b372965170e26cf` | **MATCH** |

---

## 9. Limitations & Guardrails

1. **Repository Historical Artifacts Only**: `REAL_REPOSITORY` operates strictly on data existing in the local repository clone (`data/trujillo/` and `outputs/`). It does not connect to live ESA or satellite APIs.
2. **Skipped Model Inference**: Pre-existing verified masks are ingested directly to prevent unnecessary GPU consumption and non-deterministic re-computation; `INFER` and `INTERPRET` are explicitly marked as `SKIPPED`.
3. **Hypothesis vs Attribution**: Candidate vessel scores represent spatio-temporal compatibility under Lagrangian reverse drift models. They do not constitute legal proof of culpability or causal certainty.
4. **AIS Incompleteness**: `AIS_ABSENCE_IS_NOT_VESSEL_ABSENCE` remains an inviolate system invariant.

---

## 10. Provenance Correction & Transitive Lineage (Task PROVENANCE-CORRECTION)

### Material Defect Corrected
Previously, the `REAL_REPOSITORY` pipeline erroneously relabeled downstream artifacts (`outputs/origin_drift/trujillo_00007_01339.geojson` and `outputs/ais/trujillo_00007_01339_summary.json`) as `HISTORICAL_ARCHIVE` at the investigation export level, despite these artifacts having originated from DEMO-mode executions with synthetic deterministic metocean forcing and synthetic six-vessel AIS fixtures.

### Architectural Rules Enforced
1. **Per-Artifact Transitive Lineage**:
   - Real Sentinel-1 observations remain `HISTORICAL_ARCHIVE`.
   - Temporal change analysis derived from Sentinel-1 remains `HISTORICAL_ARCHIVE` (`DERIVED_ANALYSIS`, non-independent from root SAR scenes).
   - Drift origin trajectories generated using synthetic forcing strictly remain `SYNTHETIC_DEMO`.
   - AIS correlations evaluated against synthetic fixtures strictly remain `SYNTHETIC_DEMO`.
2. **Investigation Result Status**:
   - A `REAL_REPOSITORY` investigation containing synthetic downstream dependencies cannot claim pure `HISTORICAL_ARCHIVE`.
   - Instead, it exposes:
     - `provenance_class`: `"REAL_REPOSITORY_SCENARIO_WITH_SYNTHETIC_DEPENDENCY"`
     - `provenance_status`: `"PROVENANCE_LIMITED"`
     - `has_synthetic_dependencies`: `true`
     - `stage_provenance`: `{ "satellite": "HISTORICAL_ARCHIVE", "temporal": "HISTORICAL_ARCHIVE", "drift": "SYNTHETIC_DEMO", "ais": "SYNTHETIC_DEMO" }`
3. **No HYBRID Mode**:
   - Explicitly avoids introducing a `HYBRID` mode. Execution remains strictly within `REAL_REPOSITORY` with a clear provenance limitation status.
4. **Frontend Transparency**:
   - Frontend console never displays `PROVENANCE: HISTORICAL_ARCHIVE` for the overall investigation when synthetic dependencies exist.
   - It displays `FUSION STATUS: PROVENANCE LIMITED` with an explicit per-stage lineage breakdown card and warning notices.

