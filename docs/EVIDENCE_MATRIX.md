# Ocean Sentinel — Traceable Evidence Matrix

**Authoritative Claim-to-Proof Verification Matrix**
**Version**: `1.0.0`
**Classification**: CANONICAL EVIDENCE MATRIX

---

## 1. Traceability Standard

Every core project claim within Ocean Sentinel is mapped to its underlying implementation module, automated test suite, live empirical artifact, and current operational status.

```
CLAIM ──► IMPLEMENTATION ──► AUTOMATED TESTS ──► EMPIRICAL PROOF ──► STATUS
```

---

## 2. Operational Pipeline Claims (Phase 6A – 6C)

| Core Claim | Implementing Code | Automated Test Suites | Live Empirical Proof | Current Status |
| :--- | :--- | :--- | :--- | :--- |
| **Copernicus OAuth2 Token Acquisition** | [`src/ocean_sentinel/satellite/auth.py`](file:///d:/Projects/ocean-sentinel/src/ocean_sentinel/satellite/auth.py) | `tests/test_auth.py` | Direct token exchange with `https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token` | **VERIFIED (Active)** |
| **Sentinel-1 STAC Catalog Discovery** | [`src/ocean_sentinel/satellite/discovery.py`](file:///d:/Projects/ocean-sentinel/src/ocean_sentinel/satellite/discovery.py) | `tests/test_discovery.py` (37 tests) | CDSE STAC search returning observation `S1A_IW_GRDH_..._D2F2_COG` | **VERIFIED (Active)** |
| **Sentinel Hub Process API Raster Retrieval** | [`src/ocean_sentinel/satellite/imagery.py`](file:///d:/Projects/ocean-sentinel/src/ocean_sentinel/satellite/imagery.py) | `tests/test_imagery_service.py` (32 tests) | 2-band float32 GeoTIFF retrieved via Process API | **VERIFIED (Active)** |
| **Atomic Raster & Metadata Persistence** | [`src/ocean_sentinel/satellite/persistence.py`](file:///d:/Projects/ocean-sentinel/src/ocean_sentinel/satellite/persistence.py) | `tests/test_acquisition_persistence.py` (11 tests) | Materialized GeoTIFF and JSON metadata in `data/raw/acquisitions/` | **VERIFIED (Active)** |
| **Cryptographic SHA-256 Integrity Binding** | [`src/ocean_sentinel/satellite/persistence.py`](file:///d:/Projects/ocean-sentinel/src/ocean_sentinel/satellite/persistence.py) | `tests/test_acquisition_persistence.py` | Verified digest `c41fbf7bed0102f9fd29cee4df752c4496b6c281632852b41f124ac7d3c9d8ee` | **VERIFIED (Active)** |
| **SAR Channel Order Invariance (Mapping A)** | [`src/ocean_sentinel/operational_pipeline.py`](file:///d:/Projects/ocean-sentinel/src/ocean_sentinel/operational_pipeline.py) | `tests/test_operational_pipeline.py` (25 tests) | Proven invariant: `Ch0 = VH`, `Ch1 = VV` regardless of input order `[VV, VH]` | **VERIFIED (Active)** |
| **Job Lifecycle State Machine** | [`src/ocean_sentinel/orchestration/acquisition_job.py`](file:///d:/Projects/ocean-sentinel/src/ocean_sentinel/orchestration/acquisition_job.py) | `tests/test_acquisition_job.py` (22 tests) | Terminal state `READY_FOR_DETECTION` reached; manifest saved to `outputs/jobs/` | **VERIFIED (Active)** |
| **REST API & Path Sanitization** | [`src/ocean_sentinel/api/routes.py`](file:///d:/Projects/ocean-sentinel/src/ocean_sentinel/api/routes.py) | `tests/test_backend_api.py` (20 tests), `tests/test_acquisition_job.py` | Live HTTP smoke test `POST /api/v1/acquisitions` -> `201 Created` with relative paths | **VERIFIED (Active)** |

---

## 3. Scientific Safety & Model Gating Claims

| Core Claim | Implementing Code | Automated Test Suites | Live Empirical Proof | Current Status |
| :--- | :--- | :--- | :--- | :--- |
| **Scientific Execution Authorization Firewall** | [`src/ocean_sentinel/operational_pipeline.py`](file:///d:/Projects/ocean-sentinel/src/ocean_sentinel/operational_pipeline.py) | `tests/test_operational_pipeline.py` | Zero model forward passes; zero mask generation | **STRICTLY ENFORCED (`EXECUTION_AUTHORIZED = False`)** |
| **Canonical Checkpoint Hash Verification** | [`src/ocean_sentinel/operational_pipeline.py`](file:///d:/Projects/ocean-sentinel/src/ocean_sentinel/operational_pipeline.py) | `tests/test_operational_pipeline.py` | Dynamically derived from `experiments/ARTIFACT_REGISTRY.md` Section 7.1 (`B5FFCCA3...E8DF`) | **VERIFIED (Active)** |
| **Quarantined Trujillo Part III Holdout** | [`src/ocean_sentinel/operational_pipeline.py`](file:///d:/Projects/ocean-sentinel/src/ocean_sentinel/operational_pipeline.py) | `tests/test_part_iii_firewall.py` | No holdout evaluation executed during operational runs | **PROTECTED / QUARANTINED** |
| **Heuristic-Only Spatio-Temporal Alignment** | [`src/ocean_sentinel/fusion.py`](file:///d:/Projects/ocean-sentinel/src/ocean_sentinel/fusion.py), [`src/ocean_sentinel/drift.py`](file:///d:/Projects/ocean-sentinel/src/ocean_sentinel/drift.py) | `tests/test_evidence_fusion.py`, `tests/test_drift.py` | `AIS_ABSENCE_IS_NOT_VESSEL_ABSENCE` invariant enforced; no causal blame assigned | **VERIFIED (Active)** |

---

## 4. Governance & Repository Truth Claims

| Core Claim | Implementing Code | Automated Test Suites | Live Empirical Proof | Current Status |
| :--- | :--- | :--- | :--- | :--- |
| **8 Protected Baseline Files Intact** | [`tests/test_source_control_policy_and_reporting_guardrails.py`](file:///d:/Projects/ocean-sentinel/tests/test_source_control_policy_and_reporting_guardrails.py) | `test_all_eight_protected_baseline_hashes_match` | Bitwise SHA-256 verification against canonical governance oracle (8/8 match) | **VERIFIED (100% Intact)** |
| **Clean Git Working Tree Invariant** | Git porcelain verification | `test_zero_staged_does_not_imply_clean_repository` | `git status` reports 0 staged, 0 modified, 0 untracked | **VERIFIED (Clean)** |
| **Surgical Artifact Tracking Boundary** | [`.gitignore`](file:///d:/Projects/ocean-sentinel/.gitignore), [`experiments/ARTIFACT_REGISTRY.md`](file:///d:/Projects/ocean-sentinel/experiments/ARTIFACT_REGISTRY.md) | `tests/test_artifact_policy.py` (7 tests) | 36 `.pt` checkpoints & 225 PNG masks preserved on disk but excluded from Git; 0 wildcard ignore violations | **VERIFIED (Active)** |
| **Cross-AI Evidence Taxonomy Reconciled** | [`docs/OCEAN_SENTINEL_SOURCE_CONTROL_INTEGRATION_V2_REPORT.md`](file:///d:/Projects/ocean-sentinel/docs/OCEAN_SENTINEL_SOURCE_CONTROL_INTEGRATION_V2_REPORT.md) | `test_ai_evidence_inventory_status_consistency` | 17 declared: 13 accessible/evaluated, 4 unavailable/unverified, AI-SRC-008 superseded | **VERIFIED (Active)** |
| **Reconciled Test Cardinality** | `pytest --collect-only` | `test_authoritative_report_summary_matches_freshly_measured_state` | 201 tests collected across 9 governed suites; 201 passing | **VERIFIED (201 Passed)** |
