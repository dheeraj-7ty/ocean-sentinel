# Ocean Sentinel — Traceable Evidence Matrix

**Authoritative Claim-to-Proof Verification Matrix**
**Version**: `1.1.0`
**Classification**: CANONICAL EVIDENCE MATRIX

---

## 1. Traceability Standard & Evidence Classification Taxonomy

Every capability, safety boundary, and governance invariant within Ocean Sentinel is mapped to its implementing module, verification tests, empirical evidence, and explicit evidence classification scope.

```
CLAIM ──► IMPLEMENTING MODULE ──► AUTOMATED TESTS ──► EMPIRICAL ARTIFACT ──► EVIDENCE SCOPE
```

### Evidence Scope Definitions
- **`CURRENT PHASE 6C LIVE / OPERATIONAL PROOF`**: Capabilities verified by direct, authenticated execution against external live services (Copernicus CDSE / live REST API smoke tests).
- **`CURRENT DETERMINISTIC UNIT-TEST PROOF`**: Capabilities verified by deterministic, offline automated unit and contract test suites.
- **`STANDING GOVERNANCE INVARIANT`**: Enforced repository, safety, and source-control properties verified dynamically against canonical oracles.
- **`GATED`**: Capabilities architecturally defined but strictly forbidden from execution under current governing safety rules.
- **`EXISTING BUT NOT CURRENTLY EXERCISED IN LIVE PHASE-6C FLOW`**: Subsystems fully implemented and unit-tested in the repository that are not part of the minimal raw acquisition smoke path.
- **`HISTORICAL SCIENTIFIC EVIDENCE`**: Model weights, benchmark evaluations, and training datasets from prior scientific phases, frozen under the Canonical Artifact Registry.

---

## 2. Current Operational Acquisition Chain (Phase 6A – 6C)

| Core Claim | Implementing Code | Automated Test Suites | Live Empirical Proof / Behavior | Evidence Scope |
| :--- | :--- | :--- | :--- | :--- |
| **Copernicus OAuth2 Token Acquisition** | [`src/ocean_sentinel/satellite/auth.py`](src/ocean_sentinel/satellite/auth.py) | `tests/test_auth.py` | Direct token exchange with CDSE identity endpoint | **CURRENT PHASE 6C LIVE / OPERATIONAL PROOF** |
| **Sentinel-1 STAC Catalog Discovery** | [`src/ocean_sentinel/satellite/discovery.py`](src/ocean_sentinel/satellite/discovery.py) | `tests/test_discovery.py` (37 tests) | CDSE STAC search returning real observation `S1A_IW_GRDH_..._D2F2_COG` | **CURRENT PHASE 6C LIVE / OPERATIONAL PROOF** |
| **Sentinel Hub Process API Raster Retrieval** | [`src/ocean_sentinel/satellite/imagery.py`](src/ocean_sentinel/satellite/imagery.py) | `tests/test_imagery_service.py` (32 tests) | 2-band float32 GeoTIFF retrieved via Process API | **CURRENT PHASE 6C LIVE / OPERATIONAL PROOF** |
| **Atomic Raster & Metadata Persistence** | [`src/ocean_sentinel/satellite/persistence.py`](src/ocean_sentinel/satellite/persistence.py) | `tests/test_acquisition_persistence.py` (11 tests) | Materialized GeoTIFF and JSON metadata sidecar in `data/raw/acquisitions/` | **CURRENT PHASE 6C LIVE / OPERATIONAL PROOF** |
| **SHA-256 Integrity Binding** | [`src/ocean_sentinel/satellite/persistence.py`](src/ocean_sentinel/satellite/persistence.py) | `tests/test_acquisition_persistence.py` | Verified SHA-256 digest `c41fbf7bed0102f9fd29cee4df752c4496b6c281632852b41f124ac7d3c9d8ee` | **CURRENT PHASE 6C LIVE / OPERATIONAL PROOF** |
| **Live REST API & Path Sanitization** | [`src/ocean_sentinel/api/routes.py`](src/ocean_sentinel/api/routes.py) | `tests/test_backend_api.py` (20 tests), `tests/test_acquisition_job.py` | Live HTTP smoke test `POST /api/v1/acquisitions` -> `201 Created` with relative paths | **CURRENT PHASE 6C LIVE / OPERATIONAL PROOF** |
| **SAR Channel Order Invariance (Mapping A)** | [`src/ocean_sentinel/operational_pipeline.py`](src/ocean_sentinel/operational_pipeline.py) | `tests/test_operational_pipeline.py` (25 tests) | Invariant verified: `Ch0 = VH`, `Ch1 = VV` regardless of input order `[VV, VH]` | **CURRENT DETERMINISTIC UNIT-TEST PROOF** |
| **Job Lifecycle State Machine** | [`src/ocean_sentinel/orchestration/acquisition_job.py`](src/ocean_sentinel/orchestration/acquisition_job.py) | `tests/test_acquisition_job.py` (22 tests) | Terminal state `READY_FOR_DETECTION` reached from `REQUESTED`; manifest in `outputs/jobs/` | **CURRENT DETERMINISTIC UNIT-TEST PROOF** |

---

## 3. Governance, Safety & Model Gating Invariants

| Core Claim | Implementing Code | Automated Test Suites | Verification Method / Behavior | Evidence Scope |
| :--- | :--- | :--- | :--- | :--- |
| **Scientific Execution Authorization Firewall** | [`src/ocean_sentinel/operational_pipeline.py`](src/ocean_sentinel/operational_pipeline.py) | `tests/test_operational_pipeline.py` | Zero model forward passes; zero mask generation | **STANDING GOVERNANCE INVARIANT / GATED (`EXECUTION_AUTHORIZED = False`)** |
| **Quarantined Trujillo Part III Holdout** | [`src/ocean_sentinel/operational_pipeline.py`](src/ocean_sentinel/operational_pipeline.py) | `tests/test_part_iii_firewall.py` | Zero holdout evaluation executed during operational runs | **STANDING GOVERNANCE INVARIANT / GATED (`HOLDOUT_ACCESS = 0`)** |
| **Canonical Checkpoint Hash Derivation** | [`src/ocean_sentinel/operational_pipeline.py`](src/ocean_sentinel/operational_pipeline.py) | `tests/test_operational_pipeline.py` | Dynamically derived from `experiments/ARTIFACT_REGISTRY.md` Section 7.1 (`B5FFCCA3...E8DF`) | **CURRENT DETERMINISTIC UNIT-TEST PROOF** |
| **8 Protected Baseline Files Intact** | [`tests/test_source_control_policy_and_reporting_guardrails.py`](tests/test_source_control_policy_and_reporting_guardrails.py) | `test_all_eight_protected_baseline_hashes_match` | Bitwise SHA-256 verification against canonical governance oracle (8/8 match) | **STANDING GOVERNANCE INVARIANT** |
| **Clean Git Working Tree Invariant** | Git porcelain verification | `test_zero_staged_does_not_imply_clean_repository` | `git status` reports 0 staged, 0 modified, 0 untracked | **STANDING GOVERNANCE INVARIANT** |
| **Surgical Artifact Tracking Boundary** | [`.gitignore`](.gitignore), [`experiments/ARTIFACT_REGISTRY.md`](experiments/ARTIFACT_REGISTRY.md) | `tests/test_artifact_policy.py` (7 tests) | 36 `.pt` checkpoints & 225 PNG masks preserved on disk but excluded from Git; 0 wildcard rules | **STANDING GOVERNANCE INVARIANT** |
| **Cross-AI Evidence Taxonomy Reconciled** | [`docs/OCEAN_SENTINEL_SOURCE_CONTROL_INTEGRATION_V2_REPORT.md`](docs/OCEAN_SENTINEL_SOURCE_CONTROL_INTEGRATION_V2_REPORT.md) | `test_ai_evidence_inventory_status_consistency` | 17 declared: 13 accessible/evaluated, 4 unavailable/unverified, AI-SRC-008 superseded | **STANDING GOVERNANCE INVARIANT** |
| **Reconciled Test Cardinality** | `pytest --collect-only` | `test_authoritative_report_summary_matches_freshly_measured_state` | 201 tests collected across 9 governed suites; 201 passing | **CURRENT DETERMINISTIC UNIT-TEST PROOF** |

---

## 4. Existing Downstream Investigation Subsystems (Outside Live Phase 6C Acquisition Smoke Path)

The following analytical subsystems are fully implemented in the repository with deterministic unit-test coverage, but were not invoked during the minimal Phase 6C single-observation live acquisition smoke test:

| Subsystem Claim | Implementing Code | Automated Test Suites | Operational Role | Evidence Scope |
| :--- | :--- | :--- | :--- | :--- |
| **Lagrangian Particle Drift Modeling** | [`src/ocean_sentinel/drift.py`](src/ocean_sentinel/drift.py) | `tests/test_drift.py` (15 tests) | Backward/forward trajectory modeling under metocean windage forcing | **EXISTING BUT NOT CURRENTLY EXERCISED IN LIVE PHASE-6C FLOW** |
| **Vessel AIS Trajectory Correlator** | [`src/ocean_sentinel/ais.py`](src/ocean_sentinel/ais.py) | `tests/test_ais.py`, `tests/test_ais_adversarial.py` | Historical AIS interpolation, encounter detection, and candidate vessel scoring | **EXISTING BUT NOT CURRENTLY EXERCISED IN LIVE PHASE-6C FLOW** |
| **Multi-Source Evidence Fusion** | [`src/ocean_sentinel/fusion.py`](src/ocean_sentinel/fusion.py) | `tests/test_evidence_fusion.py` | Correlation fusion; enforces `AIS_ABSENCE_IS_NOT_VESSEL_ABSENCE` (no causal blame) | **EXISTING BUT NOT CURRENTLY EXERCISED IN LIVE PHASE-6C FLOW** |
| **Temporal SAR Change Detection** | [`src/ocean_sentinel/temporal.py`](src/ocean_sentinel/temporal.py) | `tests/test_temporal.py` (Protected baseline file #6) | Multi-temporal image pairing, geometry diffing, and persistence tracking | **EXISTING BUT NOT CURRENTLY EXERCISED IN LIVE PHASE-6C FLOW** |

---

## 5. Historical Scientific Research & ML Model Evidence

| Research Milestone | Canonical Artifact References | Historical Verification Baseline | Evidence Scope |
| :--- | :--- | :--- | :--- |
| **Baseline Model Training (EXP-01 – EXP-02)** | `experiments/exp01_baseline/` | Evaluated on Kaggle GPU environment | **HISTORICAL SCIENTIFIC EVIDENCE** |
| **Hard Negative Training (EXP-03 – EXP-06)** | Checkpoint [`experiments/performance/exp06_positive_bce_weight/best_model.pt`](experiments/performance/exp06_positive_bce_weight/best_model.pt) | Converged checkpoint matching registered SHA-256 (`B5FFCCA3...E8DF`) | **HISTORICAL SCIENTIFIC EVIDENCE** |
| **External Holdout Evaluation (Phase 6 Scientific)** | `experiments/PHASE_6_PART_III_EXTERNAL_EVALUATION_REPORT_20260912.md` | Model evaluation against Trujillo et al. (2024) Peruvian holdout corpus | **HISTORICAL SCIENTIFIC EVIDENCE** |
| **OPS-01 / OPS-02 Dataset Construction & Freezes** | `data/ops02/` manifests, [`docs/exp08_corrected_protocol.md`](docs/exp08_corrected_protocol.md) | Ingestion and spatial split manifests frozen under governance rules | **HISTORICAL SCIENTIFIC EVIDENCE** |
