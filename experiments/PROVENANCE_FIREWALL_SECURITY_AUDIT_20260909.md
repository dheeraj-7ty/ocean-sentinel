# Provenance Firewall Security & Commit Readiness Audit

**Document Date**: September 9–10, 2026  
**Document Version**: 1.0.0  
**Audit Scope**: Authoritative Dataset Provenance Firewall (`src/ocean_sentinel/ingestion/provenance_gate.py`), Resumability Safety, and Repository Commit Readiness  
**Target Repository**: `D:\Projects\ocean-sentinel`  
**Canonical Environment**: `D:\Projects\ocean-sentinel\venv\Scripts\python.exe`  
**Expected HEAD Commit**: `97567f712684a011a6849c6bc0af7b6c561bef1e`  

---

## 1. Executive Summary & Audit Context

* **OBSERVED FACT**: Following historical incident analysis where external dataset substitutions (e.g. airborne UAVSAR QPOSD being misidentified as spaceborne Sentinel-1 MORP-Synth) were identified, Phase 3.5 established a strict provenance firewall.
* **OBSERVED FACT**: The architecture introduces `DatasetProvenanceSpecification`, `ResolvedRecordMetadata`, `ProvenanceGate`, `VerifiedProvenanceToken`, `DatasetQualificationStateMachine`, and `DatasetTransferManager` within [`src/ocean_sentinel/ingestion/provenance_gate.py`](file:///d:/Projects/ocean-sentinel/src/ocean_sentinel/ingestion/provenance_gate.py).
* **OBSERVED FACT**: All downloads and state transitions are cryptographically and logically gated before any network transfer or disk writing is initiated.
* **INFERENCE**: The architectural separation between metadata validation, cryptographic token issuance, and byte-level transfer prevents premature network calls or disk pollution.

---

## 2. Security Properties Audit

### Property 1: Provenance Before Transfer
* **Classification**: OBSERVED FACT
* **Implementation**: In [`DatasetTransferManager.download_archive`](file:///d:/Projects/ocean-sentinel/src/ocean_sentinel/ingestion/provenance_gate.py#L656-L746), the method strictly requires a `VerifiedProvenanceToken` argument before constructing any HTTP request or opening any file descriptor.
* **Empirical Verification**: `test_4_1_exact_qposd_incident_regression`, `test_4_8_premature_stream_test`, and `test_phase_5_independent_zero_byte_proof` passed. Zero network wire calls were made, zero bytes were transferred, and zero files were created on disk when provenance validation failed.

### Property 2: Exact DOI / Record Binding
* **Classification**: OBSERVED FACT
* **Implementation**: [`ProvenanceGate.evaluate_provenance`](file:///d:/Projects/ocean-sentinel/src/ocean_sentinel/ingestion/provenance_gate.py#L423-L521) evaluates `spec.expected_doi` and `spec.expected_record_id` against the resolved metadata. Any discrepancy appends a mismatch violation and marks the decision as `BLOCKED_DATASET_PROVENANCE`. The issued token embeds both `resolved_record_id` and `resolved_doi` into its HMAC-SHA256 signature payload.
* **Empirical Verification**: `test_4_2_doi_mismatch` and `test_29_3_wrong_doi_detected` passed.

### Property 3: Exact Filename Binding
* **Classification**: OBSERVED FACT
* **Implementation**: `VerifiedProvenanceToken` binds `authorized_archive_filename`. During download, `DatasetTransferManager` validates the filename against path traversal patterns and ensures destination file resolution stays bounded within `destination_dir`.
* **Empirical Verification**: `test_4_5_record_filename_mismatch`, `test_29_4_wrong_filename_detected`, and `test_path_traversal_filename_blocked` passed.

### Property 4: Checksum Binding
* **Classification**: OBSERVED FACT
* **Implementation**: [`DatasetTransferManager.verify_archive_checksum`](file:///d:/Projects/ocean-sentinel/src/ocean_sentinel/ingestion/provenance_gate.py#L748-L779) computes the cryptographic hash of the downloaded archive and compares it with expected checksums. On mismatch, it transitions the state machine to `BLOCKED_DATASET_PROVENANCE` and raises `ProvenanceBypassAttemptError`.
* **Empirical Verification**: `test_verify_archive_checksum_success_and_failure` and `test_29_2_wrong_checksum_detected` passed.

### Property 5: Token Freshness & Stale-Token Rejection
* **Classification**: OBSERVED FACT
* **Implementation**: `VerifiedProvenanceToken.is_stale(max_age_seconds=600.0)` verifies that the token's ISO timestamp is within an acceptable time window (default 10 minutes) and not future-dated beyond 60s clock skew.
* **Empirical Verification**: `test_29_1_stale_state_detected` passed. Old tokens (>600s) are rejected prior to download execution.

### Property 6: Safe Resume & Partial-Download Rejection
* **Classification**: OBSERVED FACT
* **Implementation**: `DatasetTransferManager.download_archive` compares received bytes with HTTP `Content-Length`. If the stream terminates prematurely, the partial file is unlinked, the state machine transitions to `BLOCKED_DATASET_PROVENANCE`, and `ProvenanceBypassAttemptError` is raised.
* **Empirical Verification**: `test_29_5_incomplete_archive_not_treated_as_complete` passed.

### Property 7: Direct-Download Bypass Prevention
* **Classification**: OBSERVED FACT
* **Implementation**: Invoking `download_archive` with `token=None`, boolean/dict spoofing, or forged HMAC tokens raises `ProvenanceBypassAttemptError`.
* **Empirical Verification**: `test_4_7_direct_downloader_bypass_attack` passed.

### Property 8: State-Machine Fail-Closed Behavior
* **Classification**: OBSERVED FACT
* **Implementation**: [`DatasetQualificationStateMachine`](file:///d:/Projects/ocean-sentinel/src/ocean_sentinel/ingestion/provenance_gate.py#L555-L637) defines explicit `ALLOWED_TRANSITIONS`. The state `BLOCKED_DATASET_PROVENANCE` can ONLY transition to `PROVENANCE_CHECK_IN_PROGRESS`. Direct transitions to `DOWNLOADING`, `EXTRACTING`, or `QUALIFIED` raise `IllegalStateTransitionError`.
* **Empirical Verification**: `test_state_machine_blocks_illegal_transitions` passed.

### Property 9: Path Traversal Rejection
* **Classification**: OBSERVED FACT
* **Implementation**: [`DatasetTransferManager.download_archive`](file:///d:/Projects/ocean-sentinel/src/ocean_sentinel/ingestion/provenance_gate.py#L705-L715) inspects `raw_fname` and rejects filenames containing `".."`, `"/"`, or `"\\"`. It additionally resolves `dest_file` and asserts that it starts with the resolved `destination_dir`.
* **Empirical Verification**: `test_path_traversal_filename_blocked` passed.

### Property 10: Extraction / Qualification Ordering
* **Classification**: OBSERVED FACT
* **Implementation**: The strict topological sequence `UNINITIALIZED -> PROVENANCE_CHECK_IN_PROGRESS -> PROVENANCE_VERIFIED -> DOWNLOADING -> DOWNLOAD_COMPLETED -> CHECKSUM_VERIFIED -> EXTRACTING -> PHYSICAL_QUALIFYING -> QUALIFIED` guarantees that extraction cannot be attempted without prior checksum verification.
* **Empirical Verification**: Verified through state machine transition constraints and `test_4_9_valid_positive_path`.

### Property 11: Remote Metadata-Change Handling
* **Classification**: OBSERVED FACT
* **Implementation**: `DatasetTransferManager.download_archive` accepts optional `expected_metadata: ResolvedRecordMetadata`. If the current metadata fingerprint does not match the token's `resolved_metadata_fingerprint`, it raises `ProvenanceBypassAttemptError("METADATA_DRIFT_DETECTED")`.
* **Empirical Verification**: `test_4_6_stale_resume_attack` and `test_4_10_changed_remote_record_stale_metadata` passed.

---

## 3. Package API & `__init__.py` Export Decision

* **OBSERVED FACT**: Inspection of all codebase imports reveals that every caller (`tests/test_provenance_gate.py` and `tests/test_acquisition_resumability.py`) imports directly from `ocean_sentinel.ingestion.provenance_gate`.
* **OBSERVED FACT**: No application code or existing tests import provenance gate classes from `ocean_sentinel.ingestion`.
* **OBSERVED FACT**: [`src/ocean_sentinel/ingestion/__init__.py`](file:///d:/Projects/ocean-sentinel/src/ocean_sentinel/ingestion/__init__.py) is currently unmodified and clean in Git tracking.
* **INFERENCE**: Re-exporting provenance symbols in `__init__.py` is unnecessary for package consumers and would unnecessarily mutate a tracked file without semantic benefit.
* **DECISION**: Retain `src/ocean_sentinel/ingestion/__init__.py` in its current state without modification.

---

## 4. Empirical Verification Results

### 4.1 Canonical Targeted Security Tests
* **Command**: `D:\Projects\ocean-sentinel\venv\Scripts\python.exe -m pytest tests/test_provenance_gate.py tests/test_acquisition_resumability.py -v`
* **Execution Timestamp**: 2026-09-10T07:29:20Z
* **Result**: **22 passed, 0 failed in 16.54s**
  - `tests/test_provenance_gate.py`: 17 passed
  - `tests/test_acquisition_resumability.py`: 5 passed

### 4.2 Frozen Scientific Verification
* **Command**: `D:\Projects\ocean-sentinel\venv\Scripts\python.exe scratch/verify_all_frozen_hashes.py`
* **Execution Timestamp**: 2026-09-10T07:29:32Z
* **Verification Status**: **ALL_PASS: True**
* **Verified Artifacts**:
  1. `EXP02C_best_model`: `14073F677F0525D2B32358056BCFAB7ADA4B598B03DB4DEB5D3A9CE162B5071A` (PASS)
  2. `EXP02C_test_results`: `ECF2D4AE10AFDE939BA3DDA99912488D1C3632EFD460118A26B17AD393437C6F` (PASS)
  3. `spatial_split_manifest`: `C052720A954C2E7A3E9A87AA64557450BF0DEABEC71D54C2A813849DB60812E0` (PASS)
  4. `candidate_manifest`: `5876A4E65FA636F6C0CD39377E56EEC6D9E848E8E48254927BE71ED4668B97E7` (PASS)
  5. `EXP01_best_model`: `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699` (PASS)
  6. `EXP02B1_best_model`: `54B4B098E1EB64A7422F0401C1CFB8BE81EFCDF4ABACFBC4D3B35B4499765E4B` (PASS)
* **Scientific Constants Confirmation**:
  - Frozen Decision Threshold: `0.22`
  - Frozen Normalization Means: `[-33.2331369895, -19.9412158528]`
  - Frozen Normalization Std Devs: `[6.4899856660, 4.5313456848]`

---

## 5. Threat Model Boundaries & Remaining Limitations

* **OBSERVED FACT**: The provenance gate operates on repository metadata returned by Zenodo or mock providers. If a remote repository host were compromised and published malicious content under the exact authentic author DOI and record ID, metadata matching alone cannot detect physical corruption before download; this is mitigated by downstream mandatory checksum verification (`CHECKSUM_VERIFIED` state).
* **UNVERIFIED**: Multi-process concurrency locks on disk for simultaneous downloads from separate operating system processes have not been evaluated; single-process asynchronous/synchronous transfer is currently assumed.
* **INFERENCE**: Current defenses strictly prevent automated or unintentional acquisition of substituted or unverified datasets.

---

## 6. Git Source Control Audit

* **Branch**: `master`
* **HEAD Revision**: `97567f712684a011a6849c6bc0af7b6c561bef1e`
* **Staged Changes**: 0 staged
* **Tracked Modifications**: 0 tracked modified
* **Untracked Additions**: 28 untracked (including this audit report, security tests, and provenance gate)
* **Ignored Files**: Standard local caches (`.pytest_cache/`, `__pycache__/`, `venv/`)

---

## 7. Audit Determination & Commit Readiness

The provenance firewall code, resumability protections, regression tests, and frozen scientific invariants satisfy all architectural and security constraints established by the CAO.

COMMIT_READINESS:
APPROVED_FOR_CA0_COMMIT
