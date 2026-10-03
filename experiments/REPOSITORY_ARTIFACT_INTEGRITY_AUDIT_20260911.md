# Ocean Sentinel — Repository Artifact Integrity & Scientific Provenance Audit

**Date:** 2026-09-11  
**Authority:** Chief Architect Officer (CAO)  
**Document Identity:** `experiments/REPOSITORY_ARTIFACT_INTEGRITY_AUDIT_20260911.md`  
**Execution Class:** Non-Destructive Repository & Artifact Integrity Repair  
**Status:** COMPLETED — REPOSITORY INTEGRITY PASS  

---

## 1. Executive Summary

Operating under the direction of the Chief Architect Officer (CAO), a comprehensive repository-integrity and scientific-artifact management audit was executed.

### Core Objectives Achieved:
1. **Composition of 1,859 Initial Git Status Entries Identified:** The visible Git status explosion was definitively traced to 1 tracked modified source file (`src/ocean_sentinel/ingestion/dataset.py`) and 1,858 untracked files (1,806 Part III evaluation files, 13 binary checkpoint files, 12 smoke-test files, 7 diagnostic images, 15 markdown reports, 3 source/test files, 1 failure analysis JSON report, and 1 dependency lockfile `uv.lock`).
2. **Scientific Assets Verified on Disk:** Fresh filesystem inventory confirms 4,788 files under `experiments/` and 9 files under `data/metadata/` (4,797 on-disk experiment and metadata artifacts), plus 27 test verification suites under `tests/*.py`, reconciling the prior 4,824 figure ($4,788 + 9 + 27 = 4,824$). Zero files were deleted.
3. **Surgical, Non-Destructive Gitignore Repair:** Narrow path-specific ignore rules were implemented for large generated prediction arrays (1,800 files), registered checkpoints (13 files), smoke payloads (12 files), and diagnostic images (7 files), totaling **1,832 ignored on-disk artifacts**. This reduced visible Git entries from 1,859 to 31 (2 tracked modified files: `.gitignore`, `src/ocean_sentinel/ingestion/dataset.py`; 29 untracked canonical reports, metrics, manifests, tests, and source code).
4. **Canonical Checkpoint & Part III Preservation:** Canonical EXP-01 baseline checkpoint bytes were verified against its expected SHA-256 digest (`9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699`), supporting unchanged checkpoint bytes. For Trujillo Part III, all 1,806 evaluation files were structurally verified (450 JSON/NPZ pairs in `mapping_a/`, 450 JSON/NPZ pairs in `mapping_b/`, 4 metrics JSON, 2 manifests JSON). Inventory and file-presence preservation were verified; complete byte-for-byte immutability was not independently re-established during this repair.
5. **Phase 5B Training Boundary Preserved:** Phase 5B training remains **NOT GRANTED**.

---

## 2. Initial Git State Reconstruction

At audit initialization, running `git status --porcelain=v1 --untracked-files=all` produced **1,859 entries**:

```
 M src/ocean_sentinel/ingestion/dataset.py  (1 tracked modified file)
?? [1,858 untracked files]
```

### Exact Categorical Composition of the 1,859 Entries:

| Category | File Count | Primary Location | Scientific Description |
| :--- | :--- | :--- | :--- |
| **Part III Prediction Arrays** | 900 | `experiments/performance/trujillo_part_iii_eval_20260911_exp01/mapping_*/` | 450 float16 NPZ arrays in mapping_a + 450 float16 NPZ arrays in mapping_b |
| **Part III Per-Scene JSONs** | 900 | `experiments/performance/trujillo_part_iii_eval_20260911_exp01/mapping_*/` | 450 JSON outputs in mapping_a + 450 JSON outputs in mapping_b |
| **Part III Summary Metrics** | 4 | `experiments/performance/trujillo_part_iii_eval_20260911_exp01/metrics/` | `metrics_mapping_a.json`, `metrics_mapping_b.json`, comparison & audit |
| **Part III Manifests** | 2 | `experiments/performance/trujillo_part_iii_eval_20260911_exp01/manifests/` | `freeze_hashes.json`, `trujillo_part_iii_pairing.json` |
| **Markdown Scientific Reports** | 15 | `experiments/` | Phase 4C/4D evaluation reports, Phase 5A report, Phase 5B contract |
| **Checkpoint Binary Weights** | 13 | `experiments/**/*.pt` | Heavyweight PyTorch model state dicts (~278 MB each) |
| **Smoke Test Payload** | 12 | `experiments/performance/trujillo_part_iii_smoke_20260911_baseline_exp01/` | 6 NPZ prediction arrays + 6 JSON per-scene smoke outputs |
| **Diagnostic Images** | 7 | `experiments/performance/phase_5a_diagnostics/` | 6-panel composite failure visualization PNGs ($1536 \times 1024$) |
| **Source & Test Code** | 3 | `src/ocean_sentinel/ingestion/`, `tests/` | Firewall module (`firewall.py`), firewall tests, Phase 5 guardrails |
| **Modified Tracked Source** | 1 | `src/ocean_sentinel/ingestion/dataset.py` | Scientific firewall verification hook on dataset construction |
| **Failure Analysis Report** | 1 | `experiments/performance/phase_5a_failure_analysis/` | Quantitative machine report (`failure_analysis_report.json`) |
| **Dependency Lockfile** | 1 | `uv.lock` | Standard `uv` dependency lockfile |
| **TOTAL INITIAL ENTRIES** | **1,859** | Repository Root | **100% Accounted For (1 Tracked Modified + 1,858 Untracked)** |

---

## 2.1. Mathematical Reconciliation Table

The relationship between the initial Git status count (1,859), on-disk ignored artifacts (1,832), audit modifications (+4), and current Git status entries (31) is defined below:

| Lifecycle Stage / Category | Tracked Modified | Untracked Files | Total Status Entries | Ignored on Disk | Reconciliation Notes |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Initial Working Tree State** | **1** | **1,858** | **1,859** | — | Initial state prior to policy repair |
| *— Part III Prediction Arrays & JSONs* | — | 1,800 | 1,800 | — | 900 mapping_a + 900 mapping_b |
| *— Registered Checkpoints (`.pt`)* | — | 13 | 13 | — | 13 binaries across 5 directories |
| *— Smoke Test Payloads* | — | 12 | 12 | — | Smoke evaluation artifacts |
| *— Phase 5A Diagnostic Images* | — | 7 | 7 | — | Composite PNG panels |
| **Subtotal Ignored by Policy** | — | *(1,832)* | *(1,832)* | **1,832** | Excluded via narrow `.gitignore` rules |
| **Remaining from Initial State** | **1** | **26** | **27** | — | $1,859 - 1,832 = 27$ entries |
| *— Part III Metrics & Manifests* | — | 6 | 6 | — | 4 metrics + 2 manifests (Git-visible) |
| *— Pre-existing Markdown Reports* | — | 15 | 15 | — | Reports & contracts in `experiments/` |
| *— Source & Test Files* | — | 3 | 3 | — | `firewall.py`, 2 test files |
| *— Failure Analysis Report* | — | 1 | 1 | — | `failure_analysis_report.json` |
| *— Dependency Lockfile* | — | 1 | 1 | — | `uv.lock` |
| *— Pre-existing Tracked Source* | 1 | — | 1 | — | `src/ocean_sentinel/ingestion/dataset.py` |
| **Audit & Repair Additions** | **+1** | **+3** | **+4** | — | Files modified/created in repair |
| *— Modified Tracked `.gitignore`* | +1 | — | +1 | — | Narrow surgical ignore rules |
| *— New Reports & Registry* | — | +2 | +2 | — | `ARTIFACT_REGISTRY.md`, audit report |
| *— New Policy Test Suite* | — | +1 | +1 | — | `tests/test_artifact_policy.py` |
| **Final Working Tree State** | **2** | **29** | **31** | **1,832** | Exact match with `git status --porcelain -uall` |

### Reconciliation of 1,828 vs. 1,832:
- **Net Git status entries reduction:** $1,859 - 31 = 1,828$ entries.
- **On-disk artifacts ignored by policy:** Exactly **1,832 files** ($1,800 + 13 + 12 + 7 = 1,832$).
- **Exact Arithmetic Formula:**
  $$\text{Initial Entries } (1,859) - \text{Ignored Files } (1,832) + \text{Repair Additions } (4) = \mathbf{31} \text{ Final Git Entries}$$
  The prior occurrence of 1,828 was the net reduction in Git entries, whereas 1,832 is the true count of on-disk scientific files ignored under the artifact policy.

---

## 3. Complete Artifact Classification

The repository contents have been catalogued into standard artifact tiers:

```
[A] Tracked Source:              src/ocean_sentinel/ (config, errors, models, ingestion, ml, processing, satellite)
[B] Tracked Tests:               tests/ (test_dataset_pipeline.py, test_spatial_split.py, etc.)
[C] Untracked Source/Test:       src/.../firewall.py, tests/test_part_iii_firewall.py, tests/test_phase_5_guardrails.py, tests/test_artifact_policy.py
[D] Scientific Reports:          experiments/*.md (15 reports/contracts)
[E] Canonical Manifests:         data/metadata/trujillo_2024/*.json, experiments/DATASET_MANIFEST_TRUJILLO_PART_III.json
[F] Model Checkpoints:           experiments/exp01_baseline/*.pt, experiments/performance/**/*.pt
[G] Evaluation Payloads:         experiments/performance/trujillo_part_iii_eval_20260911_exp01/ (mapping_a, mapping_b)
[H] Diagnostics/Figures:         experiments/performance/phase_5a_diagnostics/*.png
[I] Runtime Outputs:             experiments/performance/*_2026*/kernel_output/
[J] Scratch Scripts:             scratch/*.py (audits, forensic probes, temporary tools)
[K] Transient State:             scratch/*.json (persisted audit telemetry, cached inspection state)
[L] Environment Artifacts:       uv.lock, pyproject.toml
```

### Top-Level Directory Inventory under `experiments/performance/`:

| Directory Name | Files | Size (GB) | Primary Extensions | Scientific Role | Canonical? | Safe to Remove? | Action / Policy |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `trujillo_part_iii_eval_20260911_exp01` | 1,806 | 3.841 | .json (906), .npz (900) | Frozen Phase 4D-F benchmark payload | YES | **NO** | Preserved on disk; payloads ignored; metrics tracked |
| `cloud_kaggle_dataset_package_preflight_20260907_022953` | 2,418 | 52.335 | .tif (2400), .json (9), .md (4) | Gate 4 dataset packaging preflight | NO | **NO** | Preserved on disk (tifs ignored globally) |
| `exp02c_annealed_hard_negative_20260909_144000` | 39 | 1.640 | .json (17), .pt (6), .log (4) | Historical annealed hard negative run | NO | **NO** | Preserved on disk; .pt binaries ignored |
| `exp02b_1_diagnostic_20260909_142000` | 39 | 0.010 | .png (24), .csv (4), .json (5) | Historical EXP-02B-1 diagnostics | NO | **NO** | Already Git-tracked |
| `gate4_3B_live_kaggle_canary_20260908_102118` | 31 | 0.003 | .py (14), .log (11), .json (2) | Historical live Kaggle canary trial | NO | **NO** | Preserved on disk |
| `exp02b_1_hard_negative_training_20260909_094500` | 15 | 0.820 | .pt (3), .json (3), .log (3) | Historical EXP-02B-1 training run | NO | **NO** | Preserved on disk; .pt binaries ignored |
| `trujillo_part_iii_smoke_20260911_baseline_exp01` | 12 | 0.010 | .json (6), .npz (6) | Phase 4D-S1 smoke test artifacts | YES | **NO** | Preserved on disk; ignored via .gitignore |
| `phase_5a_diagnostics` | 7 | 0.010 | .png (7) | Phase 5A composite failure panels | YES | **NO** | Preserved on disk; ignored via .gitignore |
| `phase_5a_failure_analysis` | 1 | 0.009 | .json (1) | Quantitative failure report | YES | **NO** | Git-tracked |
| *(Other 35 historical directories)* | ~300 | ~0.100 | .json, .log, .py, .md | Historical qualification & probe runs | NO | **NO** | Preserved on disk |

---

## 4. Critical 3.84 GB Trujillo Part III Payload Audit

An exhaustive file-by-file audit of `experiments/performance/trujillo_part_iii_eval_20260911_exp01/` was conducted:

### Structure & Inventory:
- **Total Files:** Exactly **1,806 files** [OBSERVED FACT].
- **Total Size:** **3.841 GB** (4,124,378,390 bytes) [OBSERVED FACT].
- **Mapping A Directory (`mapping_a/`):**
  - Total Files: 900 files (450 JSON + 450 NPZ).
  - Class Distribution: 150 Oil, 150 No oil, 150 Lookalike.
  - JSON/NPZ 1-to-1 Match: Exactly 450/450 pairs matched identically by stem [OBSERVED FACT].
  - Zero-byte files: 0 [OBSERVED FACT].
- **Mapping B Directory (`mapping_b/`):**
  - Total Files: 900 files (450 JSON + 450 NPZ).
  - Class Distribution: 150 Oil, 150 No oil, 150 Lookalike.
  - JSON/NPZ 1-to-1 Match: Exactly 450/450 pairs matched identically by stem [OBSERVED FACT].
  - Zero-byte files: 0 [OBSERVED FACT].
- **Metrics Directory (`metrics/`):**
  - 4 JSON files: `metrics_mapping_a.json`, `metrics_mapping_b.json`, `comparison_summary.json`, `independent_recomputation_audit.json`.
- **Manifests Directory (`manifests/`):**
  - 2 JSON files: `freeze_hashes.json`, `trujillo_part_iii_pairing.json`.
- **Logs Directory (`logs/`):**
  - Empty directory (0 files).

### Verification Against Pre-Repair Hash Inventory (`freeze_hashes.json`):
- `checkpoint_sha256`: Expected `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699` -> **EXACT MATCH**
- `contract_sha256`: Expected `70319B82F6795FDEE5B7172BB63D3DD371E56B86F9EEA36D0F8DCCD21BA5A992` -> **EXACT MATCH**
- *Scope Limitation:* Pre-repair `freeze_hashes.json` recorded hashes for the baseline checkpoint, contract, adapter design, adapter implementation, and sample manifest. It did not pre-record individual SHA-256 digests for all 1,800 per-scene prediction files.

**Conclusion & Immutability Scope:** All 450 evaluation scenes are accounted for across both channel mappings with zero missing files and zero unexpected files. Inventory and file-presence preservation were verified; complete byte-for-byte immutability was not independently re-established during this repair.

---

## 5. Checkpoint Audit

All 13 model checkpoint files (`*.pt`) across `experiments/` were audited for file size and SHA-256 digest:

| Checkpoint Path | Size (MB) | SHA-256 Digest | Role & Status |
| :--- | :--- | :--- | :--- |
| `experiments/exp01_baseline/best_model.pt` | 278.92 | `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699` | **CANONICAL EXP-01 (FROZEN)** |
| `experiments/exp01_baseline/final_model.pt` | 278.92 | `2E4C0881DF2F16810C4494A4071EAB320D12418151CC5F74651E91FE1F0A41AA` | EXP-01 final epoch state |
| `experiments/exp01_baseline/latest_checkpoint.pt` | 278.92 | `2F8F7718D687FF1621F4D92FD7190AE3D582AC67CCD2A529F72E1088A139AA6A` | EXP-01 recovery checkpoint |
| `experiments/archive/exp01_interrupted_20260906_135852/best_model.pt` | 278.91 | `8B306D97FA22A8B79E7E0C3F82CD1A60ED85B5DCA903697D4D1771F740AE53B6` | Archive of interrupted trial |
| `experiments/performance/exp02b_1_hard_negative_training_.../best_model.pt` | 278.91 | `54B4B098E1EB64A7422F0401C1CFB8BE81EFCDF4ABACFBC4D3B35B4499765E4B` | EXP-02B-1 best model |
| `experiments/performance/exp02b_1_hard_negative_training_.../final_model.pt` | 278.92 | `35D1C0BA30E7EED7CD44780752E824C512B5566C77D0A1C8613490FB20657B24` | EXP-02B-1 final model |
| `experiments/performance/exp02b_1_hard_negative_training_.../latest_checkpoint.pt` | 278.92 | `8357118346355E295EDB0547096E188709087E7D74C4A9D4991C4D47218D3169` | EXP-02B-1 recovery state |
| `experiments/performance/exp02c_annealed_hard_negative_.../best_model.pt` | 278.92 | `14073F677F0525D2B32358056BCFAB7ADA4B598B03DB4DEB5D3A9CE162B5071A` | EXP-02C candidate |
| `experiments/performance/exp02c_annealed_hard_negative_.../remote_training_output/best_model.pt` | 278.92 | `14073F677F0525D2B32358056BCFAB7ADA4B598B03DB4DEB5D3A9CE162B5071A` | Duplicate of outer candidate |
| `experiments/performance/exp02c_annealed_hard_negative_.../final_model.pt` | 278.92 | `B3FC0DD08E8B2BD24025F8F7E22517739977B153AED82822B95B3ACBE0D161C2` | EXP-02C final |
| `experiments/performance/exp02c_annealed_hard_negative_.../remote_training_output/final_model.pt` | 278.92 | `B3FC0DD08E8B2BD24025F8F7E22517739977B153AED82822B95B3ACBE0D161C2` | Duplicate of outer final |
| `experiments/performance/exp02c_annealed_hard_negative_.../latest_checkpoint.pt` | 278.93 | `B250126F59A79BC23EF02A6BAD123D6B1655A76800AB590A0954194090428C60` | EXP-02C latest |
| `experiments/performance/exp02c_annealed_hard_negative_.../remote_training_output/latest_checkpoint.pt` | 278.93 | `B250126F59A79BC23EF02A6BAD123D6B1655A76800AB590A0954194090428C60` | Duplicate of outer latest |

**Canonical Checkpoint Verification:**
- Path: `experiments/exp01_baseline/best_model.pt`
- Size: Exactly 292,465,299 bytes
- Actual SHA-256: `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699`
- Expected SHA-256: `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699`
- Technical Statement: SHA-256 digest matched before and after execution, supporting unchanged checkpoint bytes.
- Verdict: **CANONICAL_CHECKPOINT_INTEGRITY = PASS [OBSERVED FACT]**.

---

## 5.1. Reconciling the 4,824 "Scientific Assets" Claim

A fresh filesystem scan was conducted across all repository directories to independently verify the composition of the prior "4,824 scientific assets" figure:

### Exact Filesystem Counts:
1. **Files under `experiments/`:** Exactly **4,788 files**
   - `experiments/performance/`: 4,720 files
   - `experiments/exp01_baseline/`: 19 files
   - `experiments/archive/`: 2 files
   - `experiments/exp02a_qualitative_gallery/`: 8 files
   - `experiments/*.md` (root markdown reports): 33 files
   - `experiments/*.json` (root JSON summaries): 6 files
2. **Files under `data/metadata/`:** Exactly **9 files**
   - `data/metadata/trujillo_2024/`: 7 files (manifests, audit reports, spatial split results)
   - `data/metadata/yang_singha_2025/`: 2 files (validation report, data matrix)
3. **Verification Test Suites under `tests/*.py`:** Exactly **27 files**

### Exact Provenance Formula:
$$\mathbf{4,788} \text{ (experiments)} + \mathbf{9} \text{ (data/metadata)} + \mathbf{27} \text{ (tests/*.py)} = \mathbf{4,824} \text{ Total Assets}$$

### Epistemic Inclusion Definition:
The historical 4,824 figure aggregated on-disk experimental outputs (4,788) and metadata manifests (9) with the 27 Python test suites that enforce scientific guardrails and split verification. Strictly distinguishing by role:
- **On-disk Experiment & Metadata Artifacts:** **4,797 files** ($4,788 + 9$).
- **Test Verification Suites:** **27 files** (`tests/*.py`).
- **Grand Aggregate:** **4,824 files** (100% accounted for on disk; zero files deleted).

---

## 6. Report and Provenance Consistency Audit

1. **Terminology Calibration:**
   - In [`scratch/analyze_phase_5a_development_failures.py`](file:///D:/Projects/ocean-sentinel/scratch/analyze_phase_5a_development_failures.py) and [`failure_analysis_report.json`](file:///D:/Projects/ocean-sentinel/experiments/performance/phase_5a_failure_analysis/failure_analysis_report.json), "bitwise verification" and `BIT_EXACT_VERIFIED` were replaced with:
     *“SHA-256 digest matched before and after execution, supporting unchanged checkpoint bytes.”* / `SHA256_DIGEST_MATCHED`.
   - In [`PHASE_5B_HARD_NEGATIVE_TRAINING_CONTRACT_20260911.md`](file:///D:/Projects/ocean-sentinel/experiments/PHASE_5B_HARD_NEGATIVE_TRAINING_CONTRACT_20260911.md#L143), future-tense "committed to the audit record" was corrected to *“recorded in the audit record”*.
   - Automated terminology screening confirmed 0 occurrences of `guaranteed`, `will solve`, `caused by`, `root cause`, `never supervised`, or `zero negative supervision` across Phase 5A and Phase 5B documents.
2. **Optimizer Weight Decay Reconciled:**
   - Phase 5B contract line 34 was corrected from `weight_decay = 1e-4` to `weight_decay = 1e-2` ($0.01$), reconciling it with canonical EXP-01 baseline settings (`experiments/exp01_baseline/config.json`).
3. **Loss Gradient Dynamics Clarified:**
   - Soft Dice contributes zero gradient on empty negative tiles when predictions are all zero, but BCE provides continuous negative-pixel gradients pushing logits downward whenever $\sigma(\text{logits}) > 0$. The intervention is accurately characterized as compositional rebalancing of hard negative sea-states, rather than introducing negative supervision for the first time.

---

## 7. Gitignore Audit & Surgical Repair

### Pre-Existing State:
Previously, `.gitignore` contained rules for Python caches, virtual environments, `.tif` rasters, and specific ephemeral staging directories (`experiments/**/src_dataset_staging/`), but did NOT contain rules for:
- Large generated per-scene prediction arrays (`mapping_a/`, `mapping_b/`)
- Checkpoint binary weights (`experiments/**/*.pt`)
- Smoke-test prediction artifacts
- Diagnostic image renders

### Surgical Rules Added to `.gitignore`:
```gitignore
# Checkpoint binary weights: specifically registered known generated large binary artifacts (hashes registered in ARTIFACT_REGISTRY.md)
experiments/exp01_baseline/*.pt
experiments/archive/exp01_interrupted_20260906_135852/*.pt
experiments/performance/exp02b_1_hard_negative_training_20260909_094500/kernel_output/exp02b_1_hard_negative_training/*.pt
experiments/performance/exp02c_annealed_hard_negative_20260909_144000/*.pt
experiments/performance/exp02c_annealed_hard_negative_20260909_144000/remote_training_output/*.pt

# Generated external evaluation per-scene prediction payloads (preserved on disk, verified in ARTIFACT_REGISTRY.md)
experiments/performance/trujillo_part_iii_eval_20260911_exp01/mapping_a/
experiments/performance/trujillo_part_iii_eval_20260911_exp01/mapping_b/
experiments/performance/trujillo_part_iii_eval_20260911_exp01/logs/

# Generated smoke test prediction artifacts (preserved on disk)
experiments/performance/trujillo_part_iii_smoke_20260911_baseline_exp01/

# Generated qualitative visual diagnostic renders (preserved on disk)
experiments/performance/phase_5a_diagnostics/
```

### Verification via `git check-ignore -v`:
- `experiments/exp01_baseline/best_model.pt` -> **IGNORED** (matches narrow `experiments/exp01_baseline/*.pt`) [EXPECTED]
- `experiments/exp03_future_experiment/best_model.pt` -> **VISIBLE / NOT IGNORED** (matches required surgical policy: future checkpoints are not globally suppressed) [EXPECTED]
- `experiments/performance/trujillo_part_iii_eval_20260911_exp01/mapping_a/Oil_00000.json` -> **IGNORED** [EXPECTED]
- `experiments/performance/trujillo_part_iii_eval_20260911_exp01/mapping_a/Oil_00000.npz` -> **IGNORED** [EXPECTED]
- `scratch/phase_5b_pretraining_gate_audit.json` -> **IGNORED** (matches pre-existing `scratch/`) [EXPECTED]
- `experiments/performance/trujillo_part_iii_eval_20260911_exp01/metrics/metrics_mapping_a.json` -> **VISIBLE** [EXPECTED]
- `experiments/performance/trujillo_part_iii_eval_20260911_exp01/manifests/freeze_hashes.json` -> **VISIBLE** [EXPECTED]
- `experiments/PHASE_5A_DEVELOPMENT_FAILURE_ANALYSIS_20260911.md` -> **VISIBLE** [EXPECTED]
- `experiments/PHASE_5B_HARD_NEGATIVE_TRAINING_CONTRACT_20260911.md` -> **VISIBLE** [EXPECTED]
- `experiments/ARTIFACT_REGISTRY.md` -> **VISIBLE** [EXPECTED]
- `experiments/REPOSITORY_ARTIFACT_INTEGRITY_AUDIT_20260911.md` -> **VISIBLE** [EXPECTED]
- `src/ocean_sentinel/ingestion/firewall.py` -> **VISIBLE** [EXPECTED]
- `tests/test_part_iii_firewall.py` -> **VISIBLE** [EXPECTED]
- `tests/test_phase_5_guardrails.py` -> **VISIBLE** [EXPECTED]
- `tests/test_artifact_policy.py` -> **VISIBLE** [EXPECTED]
- `data/metadata/trujillo_2024/spatial_split_manifest.json` -> **VISIBLE** [EXPECTED]
- `data/metadata/trujillo_2024/exp03_hard_negative_manifest.json` -> **VISIBLE / NOT IGNORED** (Status: NOT PRESENT on disk) [EXPECTED]
- `uv.lock` -> **VISIBLE** [EXPECTED]

---

## 8. Repository Artifact Policy

The formal artifact policy has been authored and registered in [`experiments/ARTIFACT_REGISTRY.md`](file:///D:/Projects/ocean-sentinel/experiments/ARTIFACT_REGISTRY.md).

It codifies:
1. **Four-Tier Storage Taxonomy:** `GIT-TRACKED`, `GIT-IGNORED BUT PRESERVED`, `PRESERVED ON DISK`, and `DISPOSABLE`.
2. **Prohibition of Broad Ignore Patterns:** Ban on blanket wildcard ignores (`*.json`, `*.npz`, `*.pt`, `experiments/`).
3. **Checkpoint Immutability & Registry:** All checkpoints require SHA-256 verification and file size logging; `.pt` files remain on disk but out of Git.
4. **Holdout Protection:** Permanent read-only status for Trujillo Part III.
5. **Future Experiment Registration:** Explicit protocol for pre-registering contracts, candidate manifests, and isolated telemetry paths.

---

## 9. Changes Made

1. **Updated `.gitignore`:** Added narrow, path-specific ignore rules for registered checkpoint binaries and generated evaluation arrays. Broad rules like `experiments/**/*.pt` are strictly prohibited to ensure future canonical experiment checkpoints remain Git-visible until explicitly registered.
2. **Created `experiments/ARTIFACT_REGISTRY.md`:** Comprehensive artifact management contract and checkpoint registry.
3. **Created `tests/test_artifact_policy.py`:** Automated unit tests verifying `.gitignore` behavior, protecting against accidental ignore regressions, and confirming that future checkpoints (e.g. `experiments/exp03_future_experiment/best_model.pt`) are not globally suppressed.
4. **Repaired Terminology:** Corrected docstrings, comments, and JSON status fields in `scratch/analyze_phase_5a_development_failures.py` and `experiments/performance/phase_5a_failure_analysis/failure_analysis_report.json`.
5. **Reconciled Phase 5B Contract:** Added Section 3.5 (HARD-NEGATIVE SAMPLING / REPRODUCIBILITY CONTRACT) and aligned weight decay to `1e-2`.

---

## 10. Test Results

Automated regression and policy tests were executed:
```powershell
.\venv\Scripts\pytest.exe tests/test_part_iii_firewall.py tests/test_phase_5_guardrails.py tests/test_artifact_policy.py tests/test_dataset_pipeline.py
```
**Results:** `70 passed, 40 warnings in 19.40s`
- [`tests/test_part_iii_firewall.py`](file:///D:/Projects/ocean-sentinel/tests/test_part_iii_firewall.py): 6/6 PASS
- [`tests/test_phase_5_guardrails.py`](file:///D:/Projects/ocean-sentinel/tests/test_phase_5_guardrails.py): 7/7 PASS
- [`tests/test_artifact_policy.py`](file:///D:/Projects/ocean-sentinel/tests/test_artifact_policy.py): 6/6 PASS
- [`tests/test_dataset_pipeline.py`](file:///D:/Projects/ocean-sentinel/tests/test_dataset_pipeline.py): 51/51 PASS

---

## 11. Part III Immutability Result

- Total files: Exactly 1,806 files present under `experiments/performance/trujillo_part_iii_eval_20260911_exp01/`.
- Mapping A Composition: 900 files (450 JSON metadata + 450 NPZ float16 prediction arrays; 150 Oil, 150 No oil, 150 Lookalike; 100% paired by stem).
- Mapping B Composition: 900 files (450 JSON metadata + 450 NPZ float16 prediction arrays; 150 Oil, 150 No oil, 150 Lookalike; 100% paired by stem).
- Metrics & Manifests: 4 metrics JSON files + 2 manifests JSON files (`freeze_hashes.json`, `trujillo_part_iii_pairing.json`).
- Run Logs: 0 files.
- Missing or Unexpected Files: Exactly 0 missing files, exactly 0 unexpected files.
- Pre-Repair Hash Verification: Checkpoint and contract hashes in `freeze_hashes.json` matched expected values.
- Epistemic Scope: Inventory and file-presence preservation were verified; complete byte-for-byte immutability was not independently re-established during this repair.
- **Verdict: PART_III_IMMUTABILITY = LIMITED [OBSERVED FACT]**.

---

## 12. Canonical Checkpoint Result

- Target: `experiments/exp01_baseline/best_model.pt`
- File size: 292,465,299 bytes
- SHA-256 Digest: `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699`
- Expected: `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699`
- **Verdict: CANONICAL_CHECKPOINT_INTEGRITY = PASS [OBSERVED FACT]**.

---

## 13. Remaining Working Tree State & Classified Artifacts

Following the surgical `.gitignore` repair, running `git status --porcelain=v1 -uall` shows **31 entries** (2 tracked modified files and 29 untracked files):

```
 M .gitignore
 M src/ocean_sentinel/ingestion/dataset.py
?? experiments/ARTIFACT_REGISTRY.md
?? experiments/PHASE_5A_DEVELOPMENT_FAILURE_ANALYSIS_20260911.md
?? experiments/PHASE_5B_HARD_NEGATIVE_TRAINING_CONTRACT_20260911.md
?? experiments/REPOSITORY_ARTIFACT_INTEGRITY_AUDIT_20260911.md
?? experiments/TRUJILLO_PART_III_ACQUISITION_20260910.md
?? experiments/TRUJILLO_PART_III_ADAPTER_DESIGN_20260911.md
?? experiments/TRUJILLO_PART_III_EVALUATION_CONTRACT_20260911.md
?? experiments/TRUJILLO_PART_III_EXTRACTION_20260910.md
?? experiments/TRUJILLO_PART_III_PHASE_4C_FINAL_CLOSURE_20260911.md
?? experiments/TRUJILLO_PART_III_PHASE_4D_CLOSURE_REPAIR_AUDIT_20260911.md
?? experiments/TRUJILLO_PART_III_PHASE_4D_EXECUTION_GATE_20260911.md
?? experiments/TRUJILLO_PART_III_PHASE_4D_FULL_EVALUATION_20260911.md
?? experiments/TRUJILLO_PART_III_PHASE_4D_PREFLIGHT_20260911.md
?? experiments/TRUJILLO_PART_III_PHASE_4D_S1_SMOKE_20260911.md
?? experiments/TRUJILLO_PART_III_QUALIFICATION_20260911.md
?? experiments/TRUJILLO_PART_III_QUALIFICATION_20260911_FINAL.md
?? experiments/TRUJILLO_PART_III_QUALIFICATION_RECONCILIATION_20260911.md
?? experiments/performance/phase_5a_failure_analysis/failure_analysis_report.json
?? experiments/performance/trujillo_part_iii_eval_20260911_exp01/manifests/freeze_hashes.json
?? experiments/performance/trujillo_part_iii_eval_20260911_exp01/manifests/trujillo_part_iii_pairing.json
?? experiments/performance/trujillo_part_iii_eval_20260911_exp01/metrics/comparison_summary.json
?? experiments/performance/trujillo_part_iii_eval_20260911_exp01/metrics/independent_recomputation_audit.json
?? experiments/performance/trujillo_part_iii_eval_20260911_exp01/metrics/metrics_mapping_a.json
?? experiments/performance/trujillo_part_iii_eval_20260911_exp01/metrics/metrics_mapping_b.json
?? src/ocean_sentinel/ingestion/firewall.py
?? tests/test_artifact_policy.py
?? tests/test_part_iii_firewall.py
?? tests/test_phase_5_guardrails.py
?? uv.lock
```

### Precise Classification:
- **Staged Changes:** 0 (clean index; no changes staged for commit).
- **Tracked Modified Files:** 2 (`.gitignore`, `src/ocean_sentinel/ingestion/dataset.py`).
- **Untracked Canonical Files:** 29 (17 markdown reports, 6 summary JSON metrics/manifests, 1 failure analysis JSON report, 1 source firewall module, 3 test files, 1 uv lockfile).
- **Ignored Scientific Artifacts:** 1,832 files (1,800 Part III prediction arrays/JSONs, 13 checkpoint binaries, 12 smoke test payloads, 7 diagnostic images).
- **Expected vs. Unexpected:** All 31 entries are **EXPECTED**; 0 unexpected files.
- **Candidate Manifest Status:** `data/metadata/trujillo_2024/exp03_hard_negative_manifest.json`: **NOT PRESENT** (not created on disk, adhering strictly to pre-training boundary).

---

## 14. Remaining Risks

1. **Local Working-Copy Accumulation:** If future experiments generate un-ignored prediction arrays outside designated directories, they may appear in Git status. Mitigation: The policy mandates registering all experimental output paths in `ARTIFACT_REGISTRY.md` and adding matching narrow `.gitignore` entries.
2. **Accidental File Deletion:** Because 1,806 evaluation files are excluded from Git tracking, accidental filesystem deletion would require regenerating them via the deterministic evaluation adapter. Mitigation: Write-protection and automated firewall isolation tests prevent unintended overwrites.

---

## 15. Epistemic Classifications

### Observed Facts
1. The 1,859 initial Git status entries consisted of 1 modified file and 1,858 untracked files [OBSERVED FACT].
2. The canonical EXP-01 baseline checkpoint SHA-256 digest is `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699` (matched before and after audit), supporting unchanged checkpoint bytes [OBSERVED FACT].
3. The 1,806 Trujillo Part III evaluation files are present on disk, structured as 450 identical JSON/NPZ stem pairs in `mapping_a/` and 450 pairs in `mapping_b/`, with 4 metrics JSON and 2 manifests JSON [OBSERVED FACT].
4. The on-disk assets total 4,788 files under `experiments/`, 9 files under `data/metadata/`, and 27 test files under `tests/*.py`, exactly accounting for the 4,824 aggregate figure ($4,788 + 9 + 27 = 4,824$) [OBSERVED FACT].

### Inferences
1. Narrow, path-specific ignore rules isolate high-volume generated prediction arrays while maintaining complete visibility over canonical summary metrics and manifests, preventing repository bloat without compromising scientific reproducibility [INFERENCE].

### Limitations & Gaps
1. **Part III Immutability Scope:** Inventory and file-presence preservation were verified; complete byte-for-byte immutability was not independently re-established during this repair [LIMITATION].
2. **Candidate Manifest Generation Pending [BLOCKING GAP]:** `data/metadata/trujillo_2024/exp03_hard_negative_manifest.json` has not yet been generated on disk and hashed.
3. **CAO Execution Authorization Required [BLOCKING GAP]:** Phase 5B model training requires explicit instruction: `CAO AUTHORIZATION: PROCEED WITH PHASE 5B TRAINING`.

---

## 16. Phase 5B Authorization Status

**PHASE_5B_TRAINING_AUTHORIZATION: NOT_GRANTED**

*(Training execution remains strictly prohibited. No model training or checkpoint generation was performed.)*

---

## 17. Final Status Declarations

```
REPOSITORY_ARTIFACT_INTEGRITY_AUDIT = PASS
SCIENTIFIC_ARTIFACT_PRESERVATION = PASS
PART_III_IMMUTABILITY = LIMITED
CANONICAL_CHECKPOINT_INTEGRITY = PASS
GIT_ARTIFACT_POLICY = PASS
PHASE_5B_TRAINING_AUTHORIZATION = NOT_GRANTED
```
