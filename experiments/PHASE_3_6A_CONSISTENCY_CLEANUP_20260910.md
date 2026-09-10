# Phase 3.6A Historical Scientific Consistency & Documentation Cleanup Report

**Document Date:** 2026-09-10  
**Authority:** Chief AI Officer (CAO) Mandate — Phase 3.6A  
**Operating Agent:** Ocean Sentinel Repository Forensic Consistency & Scientific-Documentation Cleanup Agent  
**Target Repository:** `D:\Projects\ocean-sentinel`  
**Committed HEAD:** `97567f712684a011a6849c6bc0af7b6c561bef1e`  

---

## A. Scope

The scope of Phase 3.6A is forensic scientific-consistency reconciliation and documentation cleanup across recent untracked, scratch, and modified artifacts generated during Phases 3.1 through 3.5. Specifically:
1. Reconcile historical claims regarding Trujillo Part III, ensuring consistent designation as a same-family held-out test set (not independent cross-domain) with zero bytes acquired and zero inference forward passes executed.
2. Reconcile candidate descriptions of DARTIS, confirming it as a bounding-box detection suite in 8-bit normalized JPG format without native pixel segmentation masks.
3. Reconcile references to Peruvian Sentinel-1 MORP-Synth, ensuring public data availability is accurately labeled as unresolved without speculative claims of acceptance, embargo, or custody.
4. Correct inaccurate Git status statements (such as declaring working tree "clean" while untracked artifacts exist).
5. Audit state file naming to eliminate semantic ambiguity (specifically resolving Trujillo Part III state stored under a MORP-Synth filename).
6. Verify all frozen scientific artifacts and production constants without mutating any code, checkpoint, metric, or threshold.

---

## B. Repository State Before Cleanup

* **Branch**: `master`
* **HEAD Revision**: `97567f712684a011a6849c6bc0af7b6c561bef1e`
* **Staged Changes**: 0 staged (`git diff --cached` was empty)
* **Tracked Modifications**: 0 tracked modified (`git diff` was empty)
* **Untracked Additions**: 29 untracked files in `experiments/`, `src/`, `tests/`, and root (`uv.lock`)
* **Ignored Files**: 94 ignored entries (.pytest_cache, virtualenv, logs)

---

## C. Known Historical Inconsistencies Reviewed

1. **EXP02C Benchmark Invariants**:
   - Certified Checkpoint SHA-256: `14073F677F0525D2B32358056BCFAB7ADA4B598B03DB4DEB5D3A9CE162B5071A`
   - Certified Threshold: `0.22`
   - Official Metrics: $\text{IoU} = 0.79808$, $\text{Dice} = 0.88770$, $\text{Precision} = 0.84864$, $\text{Recall} = 0.93054$
   - Canonical Normalization: Means `[-33.2331369895, -19.9412158528]`, Stds `[6.4899856660, 4.5313456848]`
   - Channel Polarization Order: `UNKNOWN` (do not declare Band 0=VH / Band 1=VV as physical ground truth)
2. **Trujillo Part III Attributes**:
   - Canonical Role: Same-family held-out test set (NOT independent cross-domain)
   - Canonical Geography: Gulf of Mexico / Caribbean coastal waters
   - Canonical Archive: `02_Test_images_and_ground_truth.7z` ($10,630,044,484$ bytes, MD5 `5dce64cd7ff9d80189d13504bd3bcbf5`)
   - Acquisition Status: NOT ACQUIRED (blocked by Zenodo Cloudflare HTTP 403 rate limit)
   - Physical Qualification: NOT COMPLETED (0 bytes transferred, 0 model forward passes)
   - Exact Physical Raster Properties: UNVERIFIED pending physical raster availability
3. **DARTIS Dataset Reality**:
   - Sensor: Sentinel-1 C-band IW GRD (2019, Eastern Mediterranean Sea)
   - Annotation: Pascal VOC XML bounding boxes (0 native pixel segmentation masks)
   - Image Format: 8-bit normalized JPG (not quantitative calibrated dB float32)
   - Segmentation Status: NOT READY for semantic pixel-segmentation benchmarking
4. **MORP-Synth Dataset Reality**:
   - Preprint: arXiv:2512.02290v1 (Andrex Juarez et al., Dec 2025)
   - Code: `github.com/andrexandrex/MorpSynth` (code present, 0 rasters, 0 masks)
   - Status: `MORP_SYNTH_DATA_ACCESS = UNRESOLVED` (no Zenodo deposit published)
   - Prohibition: Zero guessing, zero substitution with unrelated records
5. **QPOSD Historical Incident**:
   - Conflation: Candidate DOI `10.5281/zenodo.19258036` resolved to airborne UAVSAR QPOSD
   - Abort: Download halted, ~977 MB partial stream wiped after forensic capture
   - Hardening: Provenance gate implemented with zero-byte transfer guarantee

---

## D. Errors Actually Found

1. **Part III Role & Size Contradictions in `EXTERNAL_VALIDATION_READINESS.md`**:
   - Line 230 stated `Trujillo Part III | 9.18 GB | Held-Out Scenes` (understating volume and omitting same-family role).
   - Line 254 stated `Candidate 2: Trujillo-Acatitla Part III (Zenodo 13761290): Independent held-out test archive (9.18 GB)` (erroneously labeling Part III as "Independent" and using outdated 9.18 GB estimate).
   - Line 284 referenced `9.18 GB (Test_images, Test_masks)` instead of the authoritative archive `02_Test_images_and_ground_truth.7z` ($9.90\text{ GB}$).
   - Line 288 stated Geographic Region as `North Sea / Global Marine` for Trujillo Part III instead of `Gulf of Mexico / Caribbean coastal waters`.
   - Line 310 referenced `Trujillo Part III (9.18 GB)`.
   - Line 253 associated `Candidate 1: Peruvian S1 / MORP-Synth` with `Zenodo 19258036` (the QPOSD record) without noting that MORP-Synth Zenodo release is unresolved.
2. **Unverified Raster Dtype in `EXTERNAL_DATASET_CANDIDATE_DEEP_VERIFICATION_20260909.md`**:
   - Line 138 claimed Part III is `2-ch 16-bit GeoTIFF (dB)`; physical raster dtype is unverified prior to local file inspection.
   - Line 89 and Line 138 listed Part III as `Ready for Controlled Acquisition` without documenting that the acquisition attempt was halted at the network boundary with HTTP 403.
3. **Unmeasured Extraction Footprint in `EXTERNAL_DATASET_CANDIDATE_MATRIX_20260909.md`**:
   - Line 65 claimed `~18 GB extracted` without explicitly marking it as an unmeasured estimate.
4. **Imprecise Git Terminology in `TRUJILLO_PART_III_FROZEN_EVALUATION_20260909.md`**:
   - Line 123 stated `Working tree clean, 0 files staged` while untracked artifacts existed outside Git.
5. **Stale Git Audit Claim in `MORP_SYNTH_PROVENANCE_GATE_REMEDIATION_20260909.md`**:
   - Line 211 stated `src/ocean_sentinel/ingestion/__init__.py` was modified, whereas `__init__.py` had been reverted and is pristine in git tracking.
6. **Machine-Readable State File Semantic Confusion**:
   - `scratch/morp_synth_qualification_state.json` contained JSON data tracking the Trujillo Part III acquisition attempt rather than MORP-Synth.

---

## E. Corrections Actually Made

1. [`experiments/EXTERNAL_VALIDATION_READINESS.md`](file:///d:/Projects/ocean-sentinel/experiments/EXTERNAL_VALIDATION_READINESS.md):
   - Corrected Part III description to: `Same-family held-out test archive (9.90 GB, 10,630,044,484 bytes; NOT independent cross-domain)`.
   - Corrected Part III geography from `North Sea / Global Marine` to `Gulf of Mexico / Caribbean coastal waters`.
   - Corrected data volume references to `9.90 GB (02_Test_images_and_ground_truth.7z)`.
   - Disassociated MORP-Synth from Zenodo DOI 19258036 in line 253, designating it as `arXiv:2512.02290; Zenodo release unresolved`.
2. [`experiments/EXTERNAL_DATASET_CANDIDATE_DEEP_VERIFICATION_20260909.md`](file:///d:/Projects/ocean-sentinel/experiments/EXTERNAL_DATASET_CANDIDATE_DEEP_VERIFICATION_20260909.md):
   - Corrected line 89 to: `ACQUISITION HALTED (ZENODO HTTP 403 RATE-LIMIT; ZERO CONTENT BYTES TRANSFERRED; QUALIFICATION NOT PERFORMED)`.
   - Corrected line 138 to classify Part III physical format as `2-ch GeoTIFF (reported dB, dtype UNVERIFIED)`.
3. [`experiments/EXTERNAL_DATASET_CANDIDATE_MATRIX_20260909.md`](file:///d:/Projects/ocean-sentinel/experiments/EXTERNAL_DATASET_CANDIDATE_MATRIX_20260909.md):
   - Clarified line 65 to: `~18 GB extracted (estimated, unmeasured)`.
4. [`experiments/TRUJILLO_PART_III_FROZEN_EVALUATION_20260909.md`](file:///d:/Projects/ocean-sentinel/experiments/TRUJILLO_PART_III_FROZEN_EVALUATION_20260909.md):
   - Corrected line 123 to use precise Git terminology: `Tracked working tree clean (0 staged, 0 tracked modified, untracked artifacts present outside Git), HEAD locked at 97567f712684a011a6849c6bc0af7b6c561bef1e`.
5. [`experiments/MORP_SYNTH_PROVENANCE_GATE_REMEDIATION_20260909.md`](file:///d:/Projects/ocean-sentinel/experiments/MORP_SYNTH_PROVENANCE_GATE_REMEDIATION_20260909.md):
   - Corrected line 211 to: `Tracked Modifications: Exactly 0 tracked modified (git diff --name-only is empty; __init__.py reverted to pristine tracking)`.
6. [`scratch/trujillo_part_iii_qualification_state.json`](file:///d:/Projects/ocean-sentinel/scratch/trujillo_part_iii_qualification_state.json) & [`scratch/morp_synth_qualification_state.json`](file:///d:/Projects/ocean-sentinel/scratch/morp_synth_qualification_state.json):
   - Created `scratch/trujillo_part_iii_qualification_state.json` to store the authoritative machine-readable state of the Trujillo Part III attempt (`TRUJILLO_PART_III_ACQUISITION_FAILED`).
   - Restored `scratch/morp_synth_qualification_state.json` to accurately represent the MORP-Synth blocked state (`BLOCKED_DATASET_PROVENANCE`, `MORP_SYNTH_DATA_ACCESS = UNRESOLVED`).

---

## F. Items Intentionally Left Unchanged

1. **Source Code & Unit Tests**:
   - `src/ocean_sentinel/ingestion/provenance_gate.py`: Untouched.
   - `tests/test_provenance_gate.py`: Untouched.
   - `tests/test_acquisition_resumability.py`: Untouched.
   - `src/ocean_sentinel/ingestion/__init__.py`: Untouched (clean in Git tracking).
2. **Historical Incident Evidence**:
   - `experiments/MORP_SYNTH_ACQUISITION_BLOCKED_20260909.md`: Left intact as historical evidence of the QPOSD failure and remediation.
   - `scratch/morp_synth_forensic_evidence.json`: Left intact.
3. **Certified Scientific Artifacts & Checkpoints**:
   - Model weights (`best_model.pt`), split manifests, test results, and candidate manifests: 100% frozen.

---

## G. Frozen Scientific Verification

Executed canonical verification tool:
`D:\Projects\ocean-sentinel\venv\Scripts\python.exe scratch/verify_all_frozen_hashes.py`

* **Execution Status**: `ALL_PASS: True`
* **Artifact Hash Breakdown**:
  - `EXP02C_best_model`: `14073F677F0525D2B32358056BCFAB7ADA4B598B03DB4DEB5D3A9CE162B5071A` (**PASS**)
  - `EXP02C_test_results`: `ECF2D4AE10AFDE939BA3DDA99912488D1C3632EFD460118A26B17AD393437C6F` (**PASS**)
  - `spatial_split_manifest`: `C052720A954C2E7A3E9A87AA64557450BF0DEABEC71D54C2A813849DB60812E0` (**PASS**)
  - `candidate_manifest`: `5876A4E65FA636F6C0CD39377E56EEC6D9E848E8E48254927BE71ED4668B97E7` (**PASS**)
  - `EXP01_best_model`: `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699` (**PASS**)
  - `EXP02B1_best_model`: `54B4B098E1EB64A7422F0401C1CFB8BE81EFCDF4ABACFBC4D3B35B4499765E4B` (**PASS**)

---

## H. Security Regression Verification

Because zero source files in `src/` or `tests/` were modified during Phase 3.6A, security tests were not rerun, preserving testing economy as mandated. The test suite baseline remains at **22/22 passing** (`tests/test_provenance_gate.py` and `tests/test_acquisition_resumability.py`).

---

## I. Remaining UNVERIFIED Items

1. **Zenodo Cloudflare WAF Cooldown**: Duration of the client IP restriction on `zenodo.org` remains unverified.
2. **Part III Physical Raster Properties**: Exact data type, georeferencing tags, and physical channel ordering of Part III rasters cannot be verified until network access is restored and physical files are acquired.
3. **True MORP-Synth Publication Date**: Exact timeline for the deposit of Peruvian Sentinel-1 ground-truth masks by authors of arXiv:2512.02290 remains unverified from public sources.

---

## J. Final Git State

```
Branch: master
HEAD Revision: 97567f712684a011a6849c6bc0af7b6c561bef1e
0 staged
0 tracked modified
31 untracked
94 ignored
```

*(Note: Tracked working tree is clean. 0 files staged. 0 tracked files modified.)*

---

## K. Recommendation for Next Phase

1. **Phase 3.6B — Controlled Commit Packaging**: Under CAO authority, package the hardened provenance firewall, security tests, and audited documentation into disciplined, isolated commits pursuant to `experiments/REPOSITORY_COMMIT_PLAN.md`.
2. **Phase 3.7 — Network Routing Recovery & Stand-Down**: Maintain network quarantine until Cloudflare WAF clears on Zenodo endpoints; do not attempt automatic retries.
