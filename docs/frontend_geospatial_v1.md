# Ocean Sentinel — Frontend 3D Geospatial Visualization & Interactive Evidence Explorer V1

**Document ID**: `DOC-FRONTEND-GEOSPATIAL-V1`  
**Milestone**: `OCEAN-SENTINEL-FRONTEND-GEOSPATIAL-V1`  
**Status**: `CERTIFIED` (Local Integration & Forensic Alignment)  
**Date**: `2026-09-21`  
**Git Baseline**: `master` (`542bab19f6f08c9bba8b8762e6480386c8b6026b`)  

---

## 1. Core Scientific & Legal Disclaimer

> [!IMPORTANT]
> **Non-Attribution Principle**: This frontend is an operational visualization interface over the existing scientific and backend pipeline. It evaluates spatio-temporal evidence compatibility only; it does **not** establish physical truth, causality, legal responsibility, or vessel culpability.
>
> 1. **No Causal Certainty**: Compatibility scores measure geometric and temporal alignment relative to modeled slick trajectories, never probability of guilt.
> 2. **No Single Winner**: Multiple plausible candidate vessels (`MT_HORIZON_STAR`, `GULF_SUPPLIER_VII`) are preserved and displayed simultaneously.
> 3. **Negative-Proof Guard (`AIS_ABSENCE_IS_NOT_VESSEL_ABSENCE`)**: Gaps in AIS telemetry are explicitly labeled as `DATA_UNAVAILABLE` / `INSUFFICIENT_EVIDENCE`, never as proof of vessel absence.
> 4. **Fail-Closed Physical Mode**: Without operational satellite/AIS credentials, physical pipeline runs fail closed (`BLOCKED_PROVENANCE`). No synthetic demo data is ever silently presented as physical evidence.

---

## 2. Frontend Architecture & Technology Stack

The frontend was built as a lightweight, high-performance operational console:

```
frontend/
├── index.html                  # HTML entrypoint with Inter/Outfit/JetBrains Mono fonts
├── package.json                # Dependencies: React 19, TypeScript, Vite, Three.js, Lucide
├── tsconfig.json               # Modular TypeScript configurations
├── vite.config.ts              # Vite config with API proxy (/api -> http://127.0.0.1:8000)
└── src/
    ├── index.css               # Vanilla CSS operational console design system (tokens, glassmorphism)
    ├── main.tsx                # React DOM root mounting
    ├── App.tsx                 # Master state orchestration and operational dashboard
    ├── types/
    │   └── api.ts              # Canonical TypeScript definitions matching FastAPI backend schemas
    ├── services/
    │   └── api.ts              # Typed HTTP client service for /api/v1/*
    ├── components/
    │   ├── TopBar.tsx          # System identity, health indicator, mode badge, active job
    │   ├── LeftControlPanel.tsx# Pipeline dispatch (DEMO/ARTIFACT/PHYSICAL), 7 layer toggles, job history
    │   ├── GlobeView.tsx       # 3D interactive Three.js globe, HUD coordinates, camera flyTo, raycasting
    │   ├── RightInspector.tsx  # Candidate vessel cards, multi-source evidence chain, limitations
    │   ├── BottomTimeline.tsx  # Temporal scrubber (T0, T_release, T_ais, T1, Fusion)
    │   └── Legend.tsx          # Symbology guide for polygons, tracks, and candidate statuses
    └── test/
        ├── setup.ts            # JSDOM & WebGL mock harness
        └── App.test.tsx        # 18-point comprehensive test suite (all passing)
```

### Chosen Renderer: Three.js WebGL 3D Globe
- **True 3D Geospatial Engine**: Hardware-accelerated WebGL sphere of radius $R = 100$ with WGS84 geodesic conversions ($(\text{lat}, \text{lon}) \longleftrightarrow (x, y, z)$).
- **Navigation Controls**: `OrbitControls` with smooth rotational damping, zoom clamping, and reset/home orientation.
- **Geographic Context**: Deep-space ocean sphere, atmospheric glow shader, 15-degree lat/lon graticule lines, and vector continental coastlines (Mediterranean basin, Europe, Africa, Americas).
- **Camera Fly-To**: Smooth sine-eased camera interpolation to any selected evidence item or candidate vessel.
- **Raycasting HUD**: Real-time pointer intersection calculation displaying precise geographic coordinates (`LAT`, `LON`, `ALT`) and hover tooltips.
- **Honest Vector Basemap**: Transparently labeled as *"Vector Basemap (Fail-Closed: No Fabricated Satellite Imagery)"*.

---

## 3. Component Architecture

### A. TopBar (`src/components/TopBar.tsx`)
- Displays Ocean Sentinel identity, app version (`3D GEOSPATIAL V1`).
- Real-time backend connectivity badge (`BACKEND ONLINE` vs `BACKEND DISCONNECTED`).
- Active execution mode badge (`DEMO MODE` vs `PHYSICAL MODE (FAIL-CLOSED)`).
- Current job indicator with status badge (`SUCCEEDED`, `BLOCKED_PROVENANCE`).
- Non-attribution notice badge (`NON-ATTRIBUTION V1`).

### B. LeftControlPanel (`src/components/LeftControlPanel.tsx`)
- **Pipeline Orchestration Actions**:
  - `RUN DEMO_FUSION`: Synchronous synthetic end-to-end multi-source pipeline execution.
  - `RUN ARTIFACT_FUSION`: Ingestion and fusion of existing verified file artifacts.
  - `RUN PHYSICAL (TEST BLOCK)`: Triggers physical mode execution, verifying fail-closed provenance gate.
- **7 Independent Geospatial Layer Toggles**:
  1. `SAR Detection` (Cyan outline & centroid marker)
  2. `Temporal Change (T0/T1)` (Persistent purple, new magenta polygons)
  3. `Drift Trajectories` (Amber Lagrangian backward drift curves)
  4. `Candidate Origin Region` (Orange dashed convex hull hypothesis)
  5. `AIS Observations / Tracks` (Blue/emerald vessel positions and vectors)
  6. `Fused Evidence Network` (Multi-source corroborated graph linkages)
  7. `Hypothesis Regions` (Origin and corridor bounds)
- **Session Job History**: Interactive list of executed jobs with status badges.
- **Negative-Proof Guard Banner**: Persistent reminder that `AIS_ABSENCE_IS_NOT_VESSEL_ABSENCE`.

### C. GlobeView (`src/components/GlobeView.tsx`)
- Manages Three.js scene, camera, lighting, and independent object groups for all 7 layers.
- Parses backend `evidence_ledger` GeoJSON geometries (Polygon, MultiPolygon, LineString, MultiLineString, Point) and projects them onto the 3D spherical surface.
- Interactive feature selection: Clicking any marker activates the candidate in the Right Inspector and animates the camera.
- Coordinates HUD and operational camera overlay (Zoom In, Zoom Out, Detection Focus, Home Reset).

### D. RightInspector (`src/components/RightInspector.tsx`)
- **Candidate Vessel Hypotheses Explorer**:
  - Renders all candidate vessels simultaneously (`MT_HORIZON_STAR`, `GULF_SUPPLIER_VII`, `GLITCH_RUNNER`, `SEA_PROWLER`).
  - Displays MMSI, closest approach distance ($m$), temporal offset ($h$), origin enclosure status, and exact compatibility score.
  - Preserves independent source cluster counts (`X INDEP. CLUSTERS`) and anti-double-counting status.
- **Multi-Source Evidence Chain (Accordion Tree)**:
  - `Supporting Evidence`: Corroborated spatio-temporal alignment.
  - `Conflicting Evidence`: Preserved spatial/temporal discrepancies (e.g. `GLITCH_RUNNER` 14h offset).
  - `Data Unavailable / Telemetry Gaps`: Preserved AIS coverage gaps (e.g. `SEA_PROWLER` 8h gap).
  - `Scientific Limitations`: Explicit per-candidate caveat checklist.
- **Selected Evidence Item Metadata**:
  - Evidence ID, evidence type, observation timestamp, observation status (`OBSERVED` vs `INFERRED`), provenance class, derivation type.

### E. BottomTimeline (`src/components/BottomTimeline.tsx`)
- 5-Phase Temporal Scrubber:
  - `T0: BASELINE` (`2024-04-08T02:00:00Z` — Pre-spill clean sea surface)
  - `T_RELEASE: DRIFT ORIGIN` (`2024-04-09T14:00:00Z` — Backward Lagrangian release window)
  - `T_AIS: CORRELATION` (`2024-04-09T14:30:00Z` — Candidate vessel approach corridor)
  - `T1: SAR DETECTION` (`2024-04-10T14:00:00Z` — Sentinel-1 slick observation)
  - `EVIDENCE FUSION` (`2024-04-10T16:00:00Z` — Multi-source DAG synthesis)
- Stepping controls (Previous, Play/Pause auto-advance, Next) with status indicators (`OBSERVED`, `INFERRED`, `HYPOTHESIS`).

### F. Legend (`src/components/Legend.tsx`)
- Concise overlay explaining symbology and color coding across all rendered layers.

---

## 4. API Integration

The typed client (`src/services/api.ts`) communicates with the FastAPI backend over HTTP:

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/v1/health` | `GET` | Service status, API version, and frozen subsystem check |
| `/api/v1/jobs` | `GET` | List recent pipeline jobs from local job store |
| `/api/v1/jobs` | `POST` | Initialize and execute synchronous pipeline jobs |
| `/api/v1/jobs/{id}` | `GET` | Retrieve complete job manifest and stage execution history |
| `/api/v1/jobs/{id}/artifacts` | `GET` | Discover generated artifact records (Graph, Summary, GeoJSON) |
| `/api/v1/jobs/{id}/result` | `GET` | Retrieve normalized Evidence Fusion result, graph, and ledger |

---

## 5. Local Startup Instructions

### Prerequisites
- Node.js $\ge 18$
- Python 3.10 with `.venv` managed by `uv`

### Step 1: Start Backend API Server
```powershell
# In repository root
uv run python scripts/run_backend.py --host 127.0.0.1 --port 8000
```
- Swagger API Docs: `http://127.0.0.1:8000/docs`
- Health Endpoint: `http://127.0.0.1:8000/api/v1/health`

### Step 2: Start Frontend Development Server
```powershell
cd frontend
npm install
npm run dev
```
- Frontend Operational Console: `http://localhost:5173/`

### Step 3: Run Frontend Tests
```powershell
cd frontend
npm test
```

---

## 6. Verification & Test Results

### A. Frontend Unit Test Suite (Vitest)
All 18 acceptance criteria from Section 18 verified passing:

```
 ✓ src/test/App.test.tsx (18 tests)
   ✓ 1. App renders identity and core layout components
   ✓ 2. Backend health state is displayed correctly
   ✓ 3. DEMO job can be initiated via control button
   ✓ 4. Job status and ID render in top bar and control panel
   ✓ 5. Job list renders recent jobs
   ✓ 6. Evidence result renders candidate vessels and score metrics
   ✓ 7. Layer visibility switches can be toggled
   ✓ 8. Evidence selection activates candidate details and evidence chain
   ✓ 9. Multiple candidate vessels remain simultaneously visible without single winner
   ✓ 10. Conflicting evidence remains explicit in candidate ledger
   ✓ 11. Telemetry gaps are rendered as DATA_UNAVAILABLE / INSUFFICIENT_EVIDENCE
   ✓ 12. PHYSICAL provenance block renders correctly fail-closed
   ✓ 13. No synthetic evidence is labelled physical; DEMO mode badge is visible
   ✓ 14. Temporal controller steps through T0, T_RELEASE, T_AIS, T1, and FUSION
   ✓ 15. Evidence inspector displays provenance and independent source clusters
   ✓ 16. Candidate hypothesis does NOT contain "confirmed responsible vessel" or "guilty"
   ✓ 17. API failure displays controlled error notification without crashing
   ✓ 18. Empty result produces controlled empty state notice

Test Files  1 passed (1)
     Tests  18 passed (18)
  Duration  2.44s
```

### B. Backend Scientific Regression Suite (pytest)
All 175 baseline tests verified 100% passing:

```
======================= 175 passed, 2 warnings in 6.87s =======================
- test_drift.py (23 passed)
- test_ais.py (23 passed)
- test_ais_adversarial.py (13 passed)
- test_temporal.py (14 passed)
- test_interpretation.py (18 passed)
- test_evidence_fusion.py (39 passed)
- test_pipeline_orchestration.py (12 passed)
- test_backend_api.py (20 passed)
Total: 175/175 passing (0 failures, 0 regressions)
```

### C. Protected Files Integrity (Bitwise SHA-256)
All 7 protected files verified bitwise identical against their baseline hashes:

```
.gitignore:                              a664092c8717f70f88941dce08d8000e29cdcb453df9b1d64d9eeaeb3dbd0444 (MATCH)
src/ocean_sentinel/ingestion/dataset.py: f5bf1387769e43462af8e4e4de37867c761dd7adbc040455532a3463ebfa0b0c (MATCH)
src/ocean_sentinel/governance/runner.py: dd345558c3118ee61c0c966744d539c66dcfaabeab2b9c66b03903c66eb3c9e0 (MATCH)
data/metadata/governance_v2/rules.json:  b216f369d68a027e4708e8cbcf3991d8effd5ba5a063a3b8b6b3fc2261d85c4e (MATCH)
data/metadata/governance_v2/lessons.json:4784a440070bc00612bc3bfa9b29a7acc181934f894a9e22bd340faab7076395 (MATCH)
data/metadata/governance_v2/incidents.json:fa3051a185894ee1fe46edb5825ebcfe92b107f80fb7527bf5746d4ec5b91836 (MATCH)
src/ocean_sentinel/temporal.py:          46614361e1be20a278d0af9ceee222e4787df1eade7d52a88b372965170e26cf (MATCH)
ALL PROTECTED HASHES MATCH: True
```

### D. Visual Verification (Browser Subagent Recording)
- Browser subagent verified complete live UI flows at `http://localhost:5173/`.
- Full session recording: `ocean_sentinel_ui_demo_1789935872044.webp`
- High-resolution visual captures:
  - Initial load with operational layout
  - DEMO_FUSION execution and 3D globe visualization
  - Right inspector candidate vessel selection (`MT_HORIZON_STAR`, `GULF_SUPPLIER_VII`)
  - Layer toggle state update
  - Timeline step controller progression
  - PHYSICAL mode fail-closed provenance gate rejection (`BLOCKED_PROVENANCE`)

## 7. Geospatial V1.1 Live Visual & Integration Correction Pass

### A. Material Defects Addressed
1. **Backend Connectivity Semantics**:
   - Replaced naive job-presence heuristic with explicit, real-time connectivity states: `BACKEND ONLINE`, `BACKEND OFFLINE`, and `BACKEND UNREACHABLE`.
   - Continuous 4-second health heartbeat polling (`oceanSentinelApi.getHealth()`).
   - When the backend service is terminated or unreachable, previous results are preserved but explicitly branded with `[LAST LOADED RESULT]`.
2. **Location Selection Workflow**:
   - Operator can click any point on the 3D globe to select a geographic coordinate (`lat`, `lon`).
   - Distinct 3D pulsing target beacon and vertical reference pin rendered on the sphere.
   - Dedicated "Selected Location" HUD in the central viewport with direct `Focus` and `Clear` actions.
   - Dedicated "USER LOCATION (REFERENCE)" inspector card in `RightInspector` with explicit `NON-EVIDENCE INVARIANT` disclaimers (a user-selected point is never scientific evidence and does not alter drift/fusion models).
3. **Globe Usability & Visual Clarity**:
   - Enriched geographic context: major Mediterranean, African, European, Middle Eastern, and Atlantic coastline segments rendered in high-contrast vector lines.
   - Enhanced graticule with Equator and Prime Meridian highlighted.
   - Incident area default camera framing: initial and result-loaded camera auto-focuses on Eastern Mediterranean incident area (lat: 32.18, lon: 30.65, distance: 135-140 km).
   - Candidate vessels rendered with larger 3D cone markers (0.9r x 2.2h) and dual concentric pulsing halo rings (1.0-2.0 radius), ensuring visibility at normal zoom.
   - Slicks, drift origin envelopes, and drift trajectories rendered with enhanced linewidths and opacity.
4. **Viewport Information Density**:
   - Viewport HUD displays an "INCIDENT AUTO-FOCUS: EASTERN MEDITERRANEAN" banner with immediate "Recenter Event" action and live ledger/candidate counts.
   - Selected items prominently highlighted.
5. **Temporal Controller Reasoning Descriptors**:
   - Enriched timeline stages to communicate both pipeline phase and scientific observation status:
     - `T0: BASELINE` — `[SAR Observed Pre-Spill]` (OBSERVED)
     - `T_RELEASE: DRIFT ORIGIN` — `[Lagrangian Drift Hypothesis]` (HYPOTHESIS)
     - `T_AIS: TRAFFIC` — `[AIS Observed & Coverage Gaps]` (OBSERVED)
     - `T1: SLICK DETECTION` — `[SAR Observed Slick]` (OBSERVED)
     - `FUSION: SYNTHESIS` — `[Multi-Source Lineage Inferred]` (INFERRED)
   - Real timestamps bound dynamically from backend evidence ledger and hypothesis payloads without fabrication.
6. **Evidence vs Location Selection Separation**:
   - Explicit selection-type indicators in inspector header (`USER LOCATION (REFERENCE)`, `CANDIDATE VESSEL HYPOTHESIS`, `CANDIDATE ORIGIN HYPOTHESIS`, `EVIDENCE ITEM (LEDGER)`).
7. **Verification Results**:
   - 22/22 frontend unit tests passing (`frontend/src/test/App.test.tsx`).
   - 175/175 backend scientific baseline tests passing.
   - 7/7 protected files bitwise identical.
   - Live browser verification performed and captured:
     - `backend_unreachable_cached_result_1789938479717.png`
     - `ocean_sentinel_v11_live_operational_state_1789938528107.png`
