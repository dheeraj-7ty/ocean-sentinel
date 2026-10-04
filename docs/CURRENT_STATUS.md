# Ocean Sentinel — Current Operational & Governance Status

**Authoritative Current State Document**
**Last Verified Snapshot**: 2026-10-05T01:45:00+05:30 (LAST_VERIFIED_SNAPSHOT_AT)
**Current Branch**: `master`
**Synchronization**: `IN_SYNC` (`HEAD == origin/master`, clean working tree)
**Authoritative Commit Identity**: Derived dynamically from live Git via `git rev-parse HEAD`

---

## 1. Executive Status Summary

Ocean Sentinel is an Earth-observation maritime investigation platform combining real Copernicus Sentinel-1 Synthetic Aperture Radar (SAR) imagery, deterministic preprocessing, and fail-closed operational orchestration.

| Status Dimension | Current State | Verification Authority |
| :--- | :--- | :--- |
| **Current Verified Milestone** | **Phase 7C: 3D Operational Globe & Geospatial Investigation Interface** | Interactive Three.js 3D Globe, Real S1 Evidence Inspector, SSE Stream Telemetry Proof |
| **Operational Pipeline Status** | **Operational Synchronous Workflow, 3D Geospatial Console & Observable Event Stream Verified** | End-to-End Live CDSE, API, Recovery, SSE & 3D Globe Smoke Tests |
| **Scientific Safety Status** | **STRICTLY GATED (`EXECUTION_AUTHORIZED = False`)** | `OperationalDetectionBoundary` & Scientific Gate Firewall |
| **Protected Baseline Integrity** | **8/8 Canonical Hashes Intact (100% Match)** | `test_all_eight_protected_baseline_hashes_match` |
| **Automated Test Battery** | **235/235 Backend In-Scope + 79/79 Frontend Tests Passing (100%)** | 11 Governed Operational, Spine, Event & Policy Suites + 2 Frontend Suites |
| **Next Engineering Milestone** | **Separately Authorized Scientific Inference Activation Gate** | Controlled Model Forward Passes under Strict Authorization |

---

## 2. Dynamic Repository & Git State

```yaml
REPOSITORY: dheeraj-7ty/ocean-sentinel
CANONICAL_TARGET: refs/heads/master
GIT_BRANCH: master
AUTHORITATIVE_COMMIT_DERIVATION: "git rev-parse HEAD"
SYNCHRONIZATION: IN_SYNC (HEAD == origin/master)
WORKING_TREE_STATE: CLEAN (0 staged, 0 modified, 0 untracked)
GITHUB_RULESET: master-canonical-protection (ID: 24407361)
```

> [!NOTE]
> Exact repository commit identity is intentionally derived from live Git (`git rev-parse HEAD`) rather than duplicated statically here, because editing this version-controlled document modifies the repository commit whenever changes are committed. Static reports are historical execution records; repository HEAD is authoritative from live Git.

### 2.1 PR #12 Merge Governance Analysis & Forward Merge Policy
- **Investigation of PR #12 Merge**: PR #12 was merged using CLI invocation `gh pr merge 12 --squash --delete-branch --admin`. Inspection of the active repository ruleset #24407361 (`master-canonical-protection`) reveals:
  - Conditions: Enforces rules on `refs/heads/master`.
  - Rules: Requires deletion protection, non-fast-forward protection, linear history, and pull request.
  - Review / Status Parameters: `required_approving_review_count: 0`, `required_reviewers: []`, 0 required status checks, all review threads resolved, squash merges allowed.
  - Bypass Permissions: `bypass_actors: []`, `current_user_can_bypass: "never"`.
  - **Factual Determination**: PR #12 met all requirements of the active ruleset. While `--admin` was provided on the CLI, no unmet protection requirement was bypassed.
- **Forward-Looking Governance Rule**:
  ```
  ADMIN_MERGE_BYPASS = PROHIBITED BY DEFAULT
  EXCEPTION = only with explicit human authorization and explicit documentation of the unmet requirement
  ```
  Standard governed PR merges (`gh pr merge --squash --delete-branch`) are strictly required for all future changes.

---

## 3. Operational Pipeline Architecture (Phase 6A → 6B → 6C)

The Phase 6 operational chain executes a deterministic, fail-closed workflow from user API request to validated Earth-observation evidence:

```
[ POST /api/v1/acquisitions ]
            │
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

### 3.1 Verified Operational Contracts
1. **Synchronous Execution Semantics**: The current acquisition endpoint (`POST /api/v1/acquisitions`) executes synchronously, running discovery, materialization, persistence, and validation within the HTTP lifecycle and returning after reaching a terminal state (`READY_FOR_DETECTION` or failure).
2. **Collision-Resistant Job Identifiers**: Job IDs are generated as `acq_{timestamp}_{token_hex(4)}`—unique, collision-resistant operational tokens.
3. **Canonical Storage Namespace**: Acquired Sentinel-1 rasters and sidecars persist exclusively under governed path `data/raw/acquisitions/{product_id}/`.
4. **API Path Safety & Sanitization**: The API response model sanitizes all host filesystem references into safe relative paths (`data/raw/acquisitions/...`), preventing server host drive letter leakage.
5. **Polarization Channel Order Contract**: The SAR pipeline contract strictly enforces Mapping A channel ordering (`Ch0 = VH`, `Ch1 = VV`). Polarization order is invariant under inverted provider response orders (`[VV, VH]`).
6. **Empirical Raster Format**: Downloaded Copernicus observation rasters are verified as multi-band, strip-organized GeoTIFFs (`driver: GTiff`, `dtype: float32`, `tiled: False`), stored alongside SHA-256 integrity digests.

---

## 4. Scientific Safety Firewall

Under governing repository safety rules, scientific model execution remains decoupled from operational pipeline readiness:

```yaml
SCIENTIFIC_SAFETY_STATE:
  EXECUTION_AUTHORIZED: false
  MODEL_INFERENCE: 0 (No forward passes executed)
  MODEL_TRAINING: 0 (No parameter weight updates)
  HOLDOUT_EVALUATION: 0 (No holdout dataset access)
  TRUJILLO_PART_III_ACCESS: 0 (Quarantined)
  THRESHOLD_TUNING: 0 (No post-hoc threshold adjustment)
  SCIENTIFIC_DETECTION_CLAIMS: 0 (No candidate slicks claimed)
  VESSEL_ATTRIBUTION: 0 (No legal or causal culpability inferred)
```

The canonical trained model checkpoint [`experiments/performance/exp06_positive_bce_weight/best_model.pt`](experiments/performance/exp06_positive_bce_weight/best_model.pt) is verified against the canonical SHA-256 digest (`B5FFCCA3...E8DF`) derived dynamically from [`experiments/ARTIFACT_REGISTRY.md`](experiments/ARTIFACT_REGISTRY.md) Section 7.1.

---

## 5. Protected Baseline Status (8/8 Match)

The 8 canonical baseline authorities remain strictly frozen and bitwise verified:

| Canonical Protected Path | Role | Baseline Hash Match |
| :--- | :--- | :---: |
| [`data/metadata/governance_v2/rules.json`](data/metadata/governance_v2/rules.json) | Governance V2 Rule Engine Definitions | **100% MATCH** |
| [`data/metadata/governance_v2/lessons.json`](data/metadata/governance_v2/lessons.json) | Approved Governance Lessons Ledger | **100% MATCH** |
| [`data/metadata/governance_v2/incidents.json`](data/metadata/governance_v2/incidents.json) | Governance Incident Log | **100% MATCH** |
| [`src/ocean_sentinel/governance/runner.py`](src/ocean_sentinel/governance/runner.py) | Governed Preflight & Rule Validation Runner | **100% MATCH** |
| [`src/ocean_sentinel/ingestion/dataset.py`](src/ocean_sentinel/ingestion/dataset.py) | Ingestion Dataset Schema & Normalization | **100% MATCH** |
| [`src/ocean_sentinel/temporal.py`](src/ocean_sentinel/temporal.py) | Temporal Analysis & Timeline Geometry | **100% MATCH** |
| [`experiments/performance/exp06_positive_bce_weight/best_model.pt`](experiments/performance/exp06_positive_bce_weight/best_model.pt) | Canonical EXP-06 Best Model Weights | **100% MATCH** |
| [`docs/exp08_corrected_protocol.md`](docs/exp08_corrected_protocol.md) | Corrected CDSE Replication Protocol | **100% MATCH** |

---

## 6. Automated Test Battery (235 In-Scope Tests)

Deterministic collection and execution across the 11 governed operational, spine, event, and guardrail suites:

```
Domain & Investigation Spine Suites (9 files, 193 tests):
  tests/test_acquisition_job.py                             22 passed
  tests/test_backend_api.py                                20 passed
  tests/test_acquisition_persistence.py                     10 passed
  tests/test_operational_pipeline.py                        26 passed
  tests/test_imagery_service.py                             32 passed
  tests/test_discovery.py                                   37 passed
  tests/test_pipeline_orchestration.py                      12 passed
  tests/test_investigation_spine.py                         15 passed
  tests/test_event_spine.py                                 19 passed

Policy & Guardrail Suites (2 files, 42 tests):
  tests/test_source_control_policy_and_reporting_guardrails.py  35 passed
  tests/test_artifact_policy.py                              7 passed

Total In-Scope Suite:                                      235 passed (100%)
Total Failures:                                              0
Total Errors:                                                0
```

---

## 7. Deferred Items & Future Roadmap

1. **Distributed Asynchronous Worker Queue**: Support for Celery / Redis / arq background task processing for multi-tile batch acquisition.
2. **Scientific Inference Activation Gate**: Controlled model forward pass execution under strict operator authorization (`EXECUTION_AUTHORIZED = True`).
3. **Multi-Sensor Data Fusion (Phase 8)**: Integration of optical and multispectral imagery with Synthetic Aperture Radar baseline evidence.
