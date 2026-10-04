# Ocean Sentinel — Phase 7C: 3D Operational Globe & Geospatial Investigation Interface Specification

**Document Version**: 1.0.0  
**Status**: VERIFIED & COMPLETE  
**Milestone**: Phase 7C (3D Operational Globe & Geospatial Investigation Interface)  
**Parent Architecture**: [Phase 7B Event Spine & Stream Telemetry](PHASE_7B_EVENT_SPINE_AND_TELEMETRY.md)  

---

## 1. Overview & Architectural Intent

Phase 7C delivers the interactive 3D operational visualization and geospatial investigation interface for Ocean Sentinel. It connects the React / Three.js frontend console directly to the verified Phase 7A investigation kernel and Phase 7B durable event spine.

The interface enables operators to:
1. Select and inspect Areas of Interest (AOIs) and investigate geospatial coordinates.
2. Monitor end-to-end investigation run lifecycles in real time.
3. Inspect real Copernicus Sentinel-1 Synthetic Aperture Radar (SAR) acquisition and evidence metadata.
4. Visualize 3D Earth geometry with precise observation footprints and operator AOIs.
5. Trace persisted evidence, sidecars, and cryptographic provenance relationships.
6. Stream real-time operational lifecycle updates via Server-Sent Events (SSE).
7. Strictly distinguish operator inputs from real repository evidence and derived states.
8. Visibly display scientifically gated stages as `BLOCKED` rather than simulating execution.

```
       Operator Interaction
                │
                ▼
     React / Three.js Console
  (GlobeView, RightInspector,
   BottomTimeline, LeftControlPanel)
         │               ▲
         │ (HTTP REST)   │ (SSE Stream)
         ▼               │
    FastAPI Router (/api/v1/investigations)
         │               │
         ▼               ▼
InvestigationStore  EventBus / DurableEventLog
  (outputs/.../        (outputs/.../
   manifest.json)       events.jsonl)
```

---

## 2. Core Architectural Invariants

1. **Non-Negotiable Scientific Gate Boundary (`EXECUTION_AUTHORIZED = False`)**:
   - `MODEL_INFERENCE`, `MODEL_TRAINING`, `HOLDOUT` evaluation, and vessel attribution remain strictly disabled.
   - Gated stages (`INFER`, `INTERPRET`) are visibly rendered as:
     ```
     BLOCKED
     Scientific execution gated
     EXECUTION_AUTHORIZED = False
     ```
   - No mock or fake detection masks are rendered over map geometries.
2. **Semantic Distinction of Evidence Classes**:
   - `USER_INPUT`: Operator-selected latitude/longitude, bounding boxes, AOI polygons, requested polarizations. Invariant: `USER_SELECTED_LOCATION != SCIENTIFIC_EVIDENCE`.
   - `REAL_REPOSITORY_EVIDENCE`: Real Copernicus Sentinel-1 products, observation footprints, GeoTIFF raster metadata (CRS, dimensions, polarizations), and SHA-256 integrity digests.
   - `DERIVED_OPERATIONAL_STATE`: Job lifecycle, DAG stage execution states, event sequences, provenance links.
   - `DEMO / MOCK`: Explicitly tagged scenarios with synthetic forcing; prohibited from mimicking real satellite evidence.
   - `GATED_SCIENTIFIC_OUTPUT`: Fail-closed blocked stages.
3. **No Fabricated Completion Percentages**:
   - The UI displays exact discrete DAG lifecycle states (`REQUESTED`, `DISCOVERING`, `ACQUIRING`, `PERSISTING`, `VALIDATING`, `READY_FOR_DETECTION`, `BLOCKED`) rather than synthetic progress percentages.
4. **Local-First & Path Safety**:
   - All persisted file paths exposed to the UI are repository-relative (`data/raw/acquisitions/...`), preventing host filesystem or credential leakage.

---

## 3. UI Component Architecture

| Component | Responsibility | Evidence Binding |
| :--- | :--- | :--- |
| `GlobeView.tsx` | 3D interactive Earth globe powered by Three.js / Canvas. Renders operator AOI geometry and Sentinel-1 observation footprints with layer toggle controls. | Distinguishes operator AOI (cyan wireframe, `USER_INPUT`) from Sentinel-1 footprint (emerald polygon, `REAL_REPOSITORY_EVIDENCE`). |
| `LeftControlPanel.tsx` | Investigation dispatch, run selector, and scenario catalog. | Exposes stored investigation runs and allows dispatching AOI investigations. |
| `RightInspector.tsx` | Evidence and provenance inspector panel. | Renders scientific gate banner, Investigation Run identity/status, Real Sentinel-1 Evidence metadata card (product ID, UTC timestamp, CRS, dimensions, polarization, GeoTIFF path, SHA-256), Operator AOI card, and Selected Event details. |
| `BottomTimeline.tsx` | Dual-tab timeline (`EVENT SPINE (PHASE 7B)` vs `TEMPORAL REASONING`). | Renders sequential lifecycle event nodes from the durable event log with live SSE streaming status. |
| `services/api.ts` | Frontend API client with resilient SSE streaming. | Implements `listInvestigations`, `getInvestigation`, `getInvestigationTelemetry`, `getInvestigationEventHistory`, `createInvestigation`, and `subscribeInvestigationEvents` with sequence deduplication and reconnect handling. |

---

## 4. Server-Sent Events (SSE) & Reconnect Semantics

- **Endpoint**: `/api/v1/investigations/{run_id}/events`
- **Reconnection**: Supports `last_event_id` query parameter and standard `Last-Event-ID` header.
- **Sequence Deduplication**: The frontend client maintains a sequence set to prevent duplicate event nodes during reconnect handoffs.
- **Reactive State Updates**: Terminal run events (`RUN_COMPLETED`) and stage transitions (`STAGE_COMPLETED`, `STAGE_BLOCKED`) dynamically reconcile the active `InvestigationRun` without full-page reloads.

---

## 5. Verification & Test Suite

### 5.1 Frontend Verification (79 Tests Passing)
- `frontend/src/test/App.test.tsx` (66 tests): Comprehensive baseline UI, layer management, and temporal controls.
- `frontend/src/test/Phase7C.test.tsx` (13 tests):
  1. Real investigation run identity, lifecycle status, and created date rendering.
  2. Operator AOI parameters labeled as `USER_INPUT` (never scientific evidence).
  3. Sentinel-1 observation metadata and footprint labeled as `REAL_REPOSITORY_EVIDENCE`.
  4. DAG execution status rendering without fabricated percentages.
  5. Live SSE event streaming with sequence progression.
  6. Automatic SSE reconnect handling via `Last-Event-ID`.
  7. Duplicate sequence event suppression.
  8. Fail-closed scientific execution gate banner (`EXECUTION_AUTHORIZED = False`).
  9. Graceful handling of missing observation metadata.
  10. API error handling with operational notices.
  11. Prohibition against presenting user inputs as detected phenomena.
  12. Enforcement of repository-relative persistence paths without local host leaks.
  13. Clean SSE stream unsubscribe on unmount.

### 5.2 Governed Backend Verification (235 Tests Passing)
- 11 governed suites (193 domain & spine tests + 42 policy/guardrail tests) pass cleanly:
  - `test_acquisition_job.py` (22)
  - `test_backend_api.py` (20)
  - `test_acquisition_persistence.py` (10)
  - `test_operational_pipeline.py` (26)
  - `test_imagery_service.py` (32)
  - `test_discovery.py` (37)
  - `test_pipeline_orchestration.py` (12)
  - `test_investigation_spine.py` (15)
  - `test_event_spine.py` (19)
  - `test_source_control_policy_and_reporting_guardrails.py` (35)
  - `test_artifact_policy.py` (7)
- **Live Integration Smoke Test**: `scratch/test_phase7c_integration_smoke.py` verifies the complete live chain: real Phase 6C manifest → `InvestigationRun` → `InvestigationStore` → FastAPI → SSE → evidence inspector.
- **Protected Baselines**: 8/8 canonical protected baseline hashes verified bitwise identical (100% match).
