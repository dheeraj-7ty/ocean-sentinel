# Phase 3.2R Authoritative Remediation Report: Provenance Gate Architecture, Adversarial Verification, and Scientific Audit Correction

**Document Identifier:** `experiments/MORP_SYNTH_PROVENANCE_GATE_REMEDIATION_20260909.md`  
**Execution Authority:** CAO Directive — Phase 3.2R  
**Execution Timestamp:** 2026-09-09T22:21:00+05:30  
**Terminal State:** **`BLOCKED_DATASET_PROVENANCE`**  
**Data Access Status:** **`MORP_SYNTH_DATA_ACCESS = UNRESOLVED`**  
**Repository Branch:** `master`  
**Committed HEAD:** `97567f712684a011a6849c6bc0af7b6c561bef1e`  

---

## 1. Executive Decision

Phase 3.2R has successfully converted the historical Phase 3.2 dataset provenance failure into an executable, hardened, and verified architectural barrier. 

The invalid QPOSD acquisition initiated under DOI `10.5281/zenodo.19258036` was halted during Phase 3.2 execution, its partial artifacts were forensically cataloged with SHA-256 hashes and completely removed, and the ingestion subsystem has now been architecturally hardened with a cryptographic `VerifiedProvenanceToken` gate, a strict `DatasetQualificationStateMachine`, and an enforced `DatasetTransferManager`.

Through 15 deterministic unit and adversarial test suites (100% PASS), we have independently proven that:
1. The historical QPOSD acquisition scenario is permanently encoded as an executable regression test.
2. An invalid provenance check causes **exactly 0 archive requests** and **0 bytes transferred**.
3. Stale state, forged tokens, or metadata drift cannot authorize archive download or resume.
4. Lower-level download machinery cannot be invoked without a valid, fresh `VerifiedProvenanceToken`.
5. The erroneous EXP-02C test benchmark values previously stated ($0.8126 / 0.6844$) have been expunged and corrected to the canonical official test metrics ($\text{IoU} = 0.79808$, $\text{Dice} = 0.88770$, $\text{Precision} = 0.84864$, $\text{Recall} = 0.93054$, Threshold $= 0.22$).
6. All six frozen scientific artifact hashes match with 100% precision.
7. External dataset acquisition remains strictly blocked (`MORP_SYNTH_DATA_ACCESS = UNRESOLVED`, terminal state `BLOCKED_DATASET_PROVENANCE`).

---

## 2. Incident Summary

During Phase 3.2 execution, candidate DOI `10.5281/zenodo.19258036` (recorded in preliminary Phase 3.1 protocol notes as Peruvian MORP-Synth) was resolved via the Zenodo REST API. The resolved metadata identified the deposit as **QPOSD (Quad-Polarization Dataset for Marine Oil Spill and Look-Alike Segmentation)** by Sohail Jamal & Yu Li (Beijing University of Technology, Jan 15, 2026, IEEE JSTARS), comprising airborne UAVSAR L-band polarimetric SAR over the U.S. Gulf of Mexico. 

Due to a deferred validation architecture in the acquisition scripts, an 8-stream parallel download of `QPOSD.zip` was initiated before physical raster inspection, downloading $977,315,023$ bytes across 11 partial files. The invalid acquisition was halted upon CAO directive, all 11 files were forensically fingerprinted in [`scratch/morp_synth_forensic_evidence.json`](file:///d:/Projects/ocean-sentinel/scratch/morp_synth_forensic_evidence.json), and the entire directory `data/raw/external_validation` was deleted.

---

## 3. Observed Facts

1. **Zenodo Record 19258036 Metadata:** The authoritative Zenodo REST API response for record 19258036 establishes title *"Quad-Polarization Dataset for Marine Oil Spill and Look-Alike Segmentation"*, airborne UAVSAR L-band sensor, U.S. Gulf of Mexico domain, and archive `QPOSD.zip`.
2. **Preprint Text (arXiv:2512.02290v1):** The MORP-Synth paper explicitly states under *Data and Code Availability*: *"The Peruvian ground-truth masks and metadata will be uploaded to Zenodo upon manuscript acceptance."*
3. **GitHub Repository (`andrexandrex/MorpSynth`):** Hosts Python synthesis code, but contains zero raw GeoTIFF rasters or ground truth masks.
4. **Current Zenodo Availability:** A search for "MORP-Synth" on Zenodo yields 0 published records.
5. **Disk Cleanliness:** `data/raw/external_validation` does not exist (`Test-Path` returns `False`). Exactly 0 external validation bytes reside on disk.
6. **Canonical Raw Data:** `data/raw/trujillo_2024` contains exclusively 1,200 images in `images/Oil` and 1,200 masks in `masks/Mask_oil`.
7. **Process Verification:** 0 active curl processes and 0 active python download processes exist.
8. **Canonical Test Artifact Metrics:** `experiments/performance/exp02c_annealed_hard_negative_20260909_144000/official_test_evaluation/official_test_results.json` records:
   - `threshold`: `0.22`
   - `iou`: `0.79808`
   - `dice`: `0.8877`
   - `precision`: `0.84864`
   - `recall`: `0.93054`
9. **Six Certified Hashes:** All six frozen scientific artifact hashes match certified expectations.
10. **Test Execution:** 15/15 adversarial provenance tests pass; 382/382 full repository tests pass.

---

## 4. Inferences

1. **DOI Origin:** Candidate DOI `10.5281/zenodo.19258036` was conflated with MORP-Synth during preliminary Phase 3.1 background literature research because it was a newly deposited (Jan 2026) SAR oil spill dataset that appeared in search indices alongside recent 2025/2026 preprint citations.
2. **Incompatibility:** QPOSD could never have been ingested by our production model (`in_channels=2`) without changing model architecture, violating frozen benchmark rules.
3. **Failure Vector:** Deferring dataset validation to post-extraction physical audits created a control-flow vulnerability where byte transfer was allowed before identity assertion.

---

## 5. Unverified

1. **Publication Date of True MORP-Synth Deposit:** When the Peruvian masks and metadata will be uploaded to Zenodo following paper acceptance is unknown and unverified from public records.
2. **Private Mirror Availability:** Whether the authors host the Peruvian GeoTIFFs on private institutional drives is unverified.

---

## 6. Root Cause

1. **Sequential Ordering Flaw:** The initial download workflow assumed a pipeline of "Download $\rightarrow$ Extract $\rightarrow$ Inspect", placing validation in Phase 3/4 rather than as a strict pre-download gate.
2. **Directory String Bias:** Writing to `data/raw/external_validation/morp_synth_zenodo_19258036/` created a false assumption that the underlying payload was MORP-Synth.
3. **Absence of Negative Keyword Guards:** Early scripts checked whether files existed on the remote record, but lacked negative guards (`UAVSAR`, `L-band`, `Gulf of Mexico`, `QPOSD`).

---

## 7. Control-Flow Failure

In the unhardened script:
```
Resolve record 19258036 ──> Extract file URLs ──> Launch 8 curl streams ──> Transfer 977 MB ──> [HALTED]
```
Validation was bypassed because the download function did not require a verified provenance object to execute.

---

## 8. Scientific Audit Correction

The preliminary blocked report (`experiments/MORP_SYNTH_ACQUISITION_BLOCKED_20260909.md`) contained an erroneous statement claiming frozen EXP-02C test metrics were $F_1 = 0.8126$ and $\text{IoU} = 0.6844$. 

This statement has been **corrected** using the canonical official test results artifact (`official_test_results.json`):
- **Canonical IoU:** `0.79808`
- **Canonical Dice:** `0.88770`
- **Canonical Precision:** `0.84864`
- **Canonical Recall:** `0.93054`
- **Canonical Threshold:** `0.22`
- **Derived $F_1$:** `0.88770` (mathematically equivalent to Dice on binary classification)

All overclaiming language (e.g. "permanently prevented") was updated to evidence-bounded statements (e.g. "The invalid QPOSD acquisition was halted during execution and the partial artifacts were removed after forensic capture").

---

## 9. Architecture Changes

The codebase was hardened in [`src/ocean_sentinel/ingestion/provenance_gate.py`](file:///d:/Projects/ocean-sentinel/src/ocean_sentinel/ingestion/provenance_gate.py) to enforce the following trust boundary:

```
DatasetProvenanceSpecification
        ↓
AuthoritativeRecordResolver (ProvenanceGate.fetch_zenodo_record)
        ↓
ProvenanceGate (evaluate_provenance / enforce_gate)
        ↓
VerifiedProvenanceToken (HMAC-signed, fresh, non-forgeable)
        ↓
DatasetTransferManager.download_archive (requires token & fresh state)
        ↓
ArtifactChecksumVerification
        ↓
Extraction
```

### Key Architectural Components:
1. **`DatasetProvenanceSpecification`:** Encapsulates target identity, expected platform, band, polarizations, geographic domain, positive mandatory keywords (`['MORP', 'Peru']`), and negative prohibited guards (`['UAVSAR', 'airborne', 'L-band', 'Gulf of Mexico', 'QPOSD', 'Quad-Polarization']`).
2. **`VerifiedProvenanceToken`:** Cryptographically signed (HMAC-SHA256) data structure issued ONLY upon successful provenance passage. Captures spec fingerprint, metadata fingerprint, authorized archive URL, authorized filename, and timestamp. Includes `verify_integrity()` and `is_stale()` methods.
3. **`DatasetTransferManager`:** Transfer layer that strictly validates that incoming token is a valid, fresh, unexpired `VerifiedProvenanceToken` matching remote metadata. If validation fails or token is missing, **zero network requests are issued and zero bytes are transferred**.
4. **`DatasetQualificationStateMachine`:** Enforces legal state transitions. Forbids transitioning from `BLOCKED_DATASET_PROVENANCE` directly to `DOWNLOADING`, `EXTRACTING`, or `QUALIFIED` without fresh provenance passage.

---

## 10. Adversarial Tests

The test suite in [`tests/test_provenance_gate.py`](file:///d:/Projects/ocean-sentinel/tests/test_provenance_gate.py) was expanded to 15 tests covering all 12 CAO-mandated scenarios:

| Test ID | Scenario | Expected Behavior | Result |
| :--- | :--- | :--- | :--- |
| **4.1** | Historical QPOSD Regression | QPOSD fails provenance; 0 archive requests, 0 bytes; state `BLOCKED_DATASET_PROVENANCE`. | **PASS** |
| **4.2** | DOI Mismatch | Plausible metadata with wrong DOI fails closed. | **PASS** |
| **4.3** | Sensor / Platform Mismatch | UAVSAR platform fails immediately. | **PASS** |
| **4.4** | Geographic Mismatch | Gulf of Mexico domain fails immediately. | **PASS** |
| **4.5** | Record / Filename Mismatch | Filename containing `QPOSD` fails immediately. | **PASS** |
| **4.6** | Stale Resume Attack | Old verified state cannot authorize transfer if remote identity drifts to QPOSD. | **PASS** |
| **4.7** | Direct Downloader Bypass | Calling transfer layer with `None`, fake dict, or forged token raises `ProvenanceBypassAttemptError`. | **PASS** |
| **4.8** | Premature Stream Test | No stream, session, or file handle is opened before provenance PASS. | **PASS** |
| **4.9** | Valid Positive Path | Controlled local fixture passes gate, transfers bytes, verifies checksum, succeeds. | **PASS** |
| **4.10** | Changed Remote Record | Token from Run A fails on Run B due to metadata drift. | **PASS** |
| **4.11** | Missing Required Metadata | Empty title or DOI fails closed. | **PASS** |
| **4.12** | Ambiguous Identity | Conflicting sensor platforms fail closed. | **PASS** |
| **State** | Illegal Transitions | State machine rejects illegal transitions out of `BLOCKED_DATASET_PROVENANCE`. | **PASS** |
| **Preflight**| Contract Generation | Preflight contract correctly documents expected vs observed attributes. | **PASS** |

---

## 11. Zero-Byte Proof

In Test `test_phase_5_independent_zero_byte_proof` and standalone script [`scratch/test_e2e_regression.py`](file:///d:/Projects/ocean-sentinel/scratch/test_e2e_regression.py), wire-tap transport tracking confirmed:
- **Archive GET requests issued:** **`0`**
- **Wire tap requests logged:** **`0`**
- **Bytes transferred:** **`0`**
- **Files created on disk:** **`0`**

The verified provenance token architecture enforces that no archive download can proceed without passing provenance verification.

---

## 12. State-Machine Safety

The `DatasetQualificationStateMachine` enforces:
- `BLOCKED_DATASET_PROVENANCE` cannot transition to `DOWNLOADING`, `EXTRACTING`, or `QUALIFIED`.
- Attempting to transition to active states without a fresh `VerifiedProvenanceToken` raises `ProvenanceBypassAttemptError` or `IllegalStateTransitionError`.
- Stale resume state cannot bypass provenance validation.

---

## 13. Frozen Hash Verification

All six certified frozen scientific artifacts were re-verified via SHA-256 computation:

| Artifact | Path | Expected Hash | Actual Hash | Status |
| :--- | :--- | :--- | :--- | :--- |
| **EXP02C Best Model** | `experiments/performance/.../best_model.pt` | `14073F677F0525D2B32358056BCFAB7ADA4B598B03DB4DEB5D3A9CE162B5071A` | `14073F677F0525D2...` | **PASS** |
| **Official Test Results** | `experiments/performance/.../official_test_results.json` | `ECF2D4AE10AFDE939BA3DDA99912488D1C3632EFD460118A26B17AD393437C6F` | `ECF2D4AE10AFDE93...` | **PASS** |
| **Spatial Split Manifest** | `data/metadata/trujillo_2024/spatial_split_manifest.json` | `C052720A954C2E7A3E9A87AA64557450BF0DEABEC71D54C2A813849DB60812E0` | `C052720A954C2E7A...` | **PASS** |
| **Candidate Manifest** | `experiments/performance/.../candidate_manifest.json` | `5876A4E65FA636F6C0CD39377E56EEC6D9E848E8E48254927BE71ED4668B97E7` | `5876A4E65FA636F6...` | **PASS** |
| **EXP01 Best Model** | `experiments/exp01_baseline/best_model.pt` | `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699` | `9B8BD867DC02C68C...` | **PASS** |
| **EXP02B-1 Best Model** | `experiments/performance/.../best_model.pt` | `54B4B098E1EB64A7422F0401C1CFB8BE81EFCDF4ABACFBC4D3B35B4499765E4B` | `54B4B098E1EB64A7...` | **PASS** |

**Firewall Verdict:** **ALL 6 CERTIFIED HASHES PASS 100%.**

---

## 14. Scientific Contamination Check

- External raster bytes: **0**
- QPOSD data on disk: **0**
- External inference runs: **0**
- Training runs: **0**
- Fine-tuning runs: **0**
- Threshold tuning operations: **0** (threshold strictly frozen at `0.22`)
- Canonical dataset alterations: **0**

---

## 15. Git Audit

- **Staged Changes:** `git diff --cached --name-only` returns **0 files** (zero files staged).
- **Tracked Modifications:** Exactly **0 tracked modified** (`git diff --name-only` is empty; `__init__.py` reverted to pristine tracking).
- **Untracked Checkpoints:** Exactly 13 authorized `.pt` binary checkpoints remain safely outside Git.
- **Untracked Remediation Files:**
  - `experiments/DATASET_PREFLIGHT_MORP_SYNTH.json`
  - `experiments/MORP_SYNTH_PROVENANCE_GATE_REMEDIATION_20260909.md`
  - `src/ocean_sentinel/ingestion/provenance_gate.py`
  - `tests/test_provenance_gate.py`
  - `scratch/verify_all_frozen_hashes_and_metrics.py`
  - `scratch/test_e2e_regression.py`
- **Commits / Pushes:** Exactly **0 commits and 0 pushes**. Repository HEAD remains `97567f712684a011a6849c6bc0af7b6c561bef1e`.

---

## 16. Current MORP-Synth Status

- **Status:** **`MORP_SYNTH_DATA_ACCESS = UNRESOLVED`**.
- **Evidence:** Preprint arXiv:2512.02290 notes masks will be uploaded to Zenodo upon manuscript acceptance. Zenodo search confirms no record has been published yet. Code repository (`andrexandrex/MorpSynth`) does not contain raw rasters or masks.
- **Resolution:** No dataset download may occur until an authoritative DOI is formally published and validated through the provenance gate.

---

## 17. Final State

```json
{
  "status": "BLOCKED",
  "qualification_decision": "BLOCKED_DATASET_PROVENANCE",
  "current_phase": "BLOCKED_DATASET_PROVENANCE",
  "provenance_resolution_status": "MORP_SYNTH_DATA_ACCESS = UNRESOLVED",
  "external_validation_status": "BLOCKED",
  "cleanup_status": "COMPLETED_ALL_PARTIAL_DATA_REMOVED",
  "inference_status": "NOT_RUN",
  "training_status": "NOT_RUN",
  "threshold_tuning_status": "NOT_RUN",
  "physical_qualification_status": "NOT_RUN",
  "model_compatibility_status": "NOT_RUN",
  "resumability_expectations": "BLOCKED_PENDING_AUTHORITATIVE_MORP_SYNTH_PROVENANCE"
}
```

---

## 18. Next Permitted Action

1. Monitor the official MORP-Synth GitHub repository (`andrexandrex/MorpSynth`) or correspond with paper authors regarding the Zenodo upload announcement.
2. If an alternative spaceborne Sentinel-1 C-band dataset is designated by the CAO, construct its `DatasetProvenanceSpecification`, pass the pre-download provenance gate, and only then proceed to download authorization.

---

## 19. Prohibited Actions

1. **DO NOT** download QPOSD or resume record 19258036.
2. **DO NOT** substitute another dataset without CAO authorization and provenance gate passage.
3. **DO NOT** rename any dataset to MORP-Synth.
4. **DO NOT** execute model inference on unverified external rasters.
5. **DO NOT** train, fine-tune, or adjust model weights.
6. **DO NOT** search or tune thresholds.
7. **DO NOT** stage or commit unapproved files.
8. **DO NOT** alter frozen scientific artifacts or Trujillo split manifests.
