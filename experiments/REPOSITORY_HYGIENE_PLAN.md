# REPOSITORY HYGIENE & CONTAMINATION AUDIT PLAN

**Date**: 2026-09-09  
**Auditor**: Antigravity IDE Agent (under CAO Master Oversight)  
**Git HEAD**: `8f444de1d0fb35d09912a9e6bf27cebde8125f0d`  
**Active Branch**: `master`  
**Current Audit Status**: `COMPLETE`  
**Cleanup Execution Status**: `NOT YET AUTHORIZED (AWAITING CAO REVIEW)`

---

## 1. EXECUTIVE SUMMARY & REPOSITORY REALITY

An exhaustive audit of the Ocean Sentinel working tree was conducted to resolve the pending Source Control backlog (~891 files). Every tracked modified and untracked file was inventoried, categorized, and assessed for provenance and scientific necessity.

### Aggregate Repository State:
- **Total Pending Changes**: **893 entries** (including active audit scripts in `scratch/`)
- **Tracked Modified / Staged Files**: **8**
  - Staged Added (`A `): 1 (`data/metadata/yang_singha_2025/data_matrix.tab`)
  - Staged & Modified (`AM`): 1 (`scripts/download_datasets.py`)
  - Unstaged Modified (` M`): 6 (`docs/sar-preprocessing.md`, `pyproject.toml`, `src/ocean_sentinel/errors.py`, `src/ocean_sentinel/processing/models.py`, `src/ocean_sentinel/processing/sar.py`, `tests/test_preprocessing.py`)
- **Untracked Files (`??`)**: **885**
- **Machine-Readable Inventory**: [`scratch/repository_change_inventory.json`](file:///d:/Projects/ocean-sentinel/scratch/repository_change_inventory.json)

---

## 2. PENDING CHANGES CLASSIFICATION (A / B / C / D)

Every single path was evaluated against parent directories, file purpose, references in existing code, and reproducibility:

| Category | Definition | Count | Proposed Disposition | Scientific Importance |
|---|---|:---:|---|:---:|
| **Category A** | **Canonical Project Source** | **85** | Stage and commit to git repository | **Critical** |
| **Category B** | **Scientific Experiment Artifacts** | **450** | Preserve permanently (Git LFS / Checkpoint Archive / Git) | **Critical** |
| **Category C** | **Generated / Ephemeral / Reproducible Staging** | **354** | Remove and add to `.gitignore` | **None (Pure Pollution)** |
| **Category D** | **Unknown / Requires Human Review** | **4** | Freeze; resolve explicitly with CAO before cleanup | **Ambiguous / High** |
| **Total** | | **893** | | |

---

## 3. CATEGORY A — CANONICAL PROJECT SOURCE (85 Files)

These files represent genuine production library code, automated test suites, dataset contracts, architectural documentation, and canonical training scripts developed across project milestones. **All 85 files must be preserved and committed to version control.**

### Breakdown by Directory:
1. **`src/` (22 files: 19 untracked + 3 tracked modified)**:
   - `src/ocean_sentinel/errors.py`, `models.py`, `config.py`
   - `src/ocean_sentinel/cloud/__init__.py`, `upload_harness.py`
   - `src/ocean_sentinel/ingestion/__init__.py`, `dataset.py`, `models.py`, `split.py`, `tiling.py`, `trujillo.py`
   - `src/ocean_sentinel/ml/__init__.py`, `augmentation.py`, `canonical_exp01.py`, `gpu_qualification.py`, `losses.py`, `metrics.py`, `threshold.py`, `unet_resnet.py`
   - `src/ocean_sentinel/processing/__init__.py`, `models.py`, `sar.py`
2. **`scripts/` (30 files: 29 untracked + 1 tracked modified)**:
   - Canonical training pipelines: `scripts/train_exp01.py`, `scripts/train_exp02b_1.py`, `scripts/train_exp02c.py`
   - Canonical test evaluators: `scripts/evaluate_exp02b_1_test.py`, `scripts/evaluate_exp02c_test.py`
   - Dataset partitioning & validation: `scripts/generate_spatial_split_manifest.py`, `scripts/generate_split_manifest.py`, `scripts/audit_trujillo_dataset.py`, `scripts/audit_spatial_leakage.py`, `scripts/verify_dartis_cdse.py`, `scripts/download_datasets.py`
   - Benchmark & qualification scripts: `scripts/benchmark_gpu_optimization.py`, `scripts/benchmark_awcc_ultra_performance.py`, `scripts/benchmark_gmode_controlled.py`, etc.
3. **`tests/` (13 files: 12 untracked + 1 tracked modified)**:
   - `tests/test_preprocessing.py`, `tests/test_spatial_split.py`, `tests/test_trujillo_ingestion.py`, `tests/test_dataset_pipeline.py`, `tests/test_ml_components.py`, `tests/test_gpu_qualification.py`, `tests/test_resume_qualification.py`, `tests/test_canonical_exp01_fingerprint.py`, `tests/test_exp01_eval.py`, `tests/test_dartis_cross_validation.py`, `tests/test_upload_harness.py`, `tests/test_pilot_runner.py`
4. **`docs/` (16 files: 15 untracked + 1 tracked modified)**:
   - Architectural Decision Records: `docs/adr/002-radiometric-unit-generalization.md`, `docs/adr/003-ml-model-architecture-cuda-and-leakage-governance.md`, `docs/adr/004-spatially-defensible-dataset-partition.md`, `docs/adr/005-resumed-training-infrastructure-qualification.md`
   - Architectural & Contract Specs: `docs/trujillo-dataset-contract.md`, `docs/dartis-cdse-cross-validation.md`, `docs/sar-preprocessing.md`, `docs/test-infrastructure.md`, `docs/context/*.md`
5. **`data/metadata/` (10 files: 9 untracked + 1 tracked added)**:
   - `data/metadata/trujillo_2024/spatial_split_manifest.json` (canonical split manifest `C052720A...`)
   - `data/metadata/trujillo_2024/split_manifest.json`, `archive_listing.json`, `dataset_audit_report.json`, `spatial_split_audit.json`, `spatial_leakage_report.json`, `exp00_benchmark_results.json`
   - `data/metadata/yang_singha_2025/data_matrix.tab`, `cdse_validation_report.json`
6. **Repository Root (1 file)**:
   - `pyproject.toml` (dependency and package configuration)

---

## 4. CATEGORY B — SCIENTIFIC EXPERIMENT ARTIFACTS (450 Files)

These files represent the immutable empirical record of Ocean Sentinel's completed experiments, hardware qualifications, and preflight gates. **Under no circumstances may any of these files be deleted.**

### Key Preserved Experiments:
- `experiments/exp01_baseline/`: Checkpoints (`best_model.pt`, `final_model.pt`, `latest_checkpoint.pt`), `history.json`, `run_state.json`, `exp01_results.json`, qualitative masks.
- `experiments/performance/exp02b_0_hard_negative_design_20260909_021500/`: Original candidate mining outputs, `candidate_manifest.json`, `GATE_EXP02B_0_REPORT.md`.
- `experiments/performance/exp02b_1_hard_negative_training_20260909_094500/`: Root checkpoints (`best_model.pt`, `final_model.pt`, `latest_checkpoint.pt`), `history.json`, `run_state.json`, `progress.log`, `stdout_training.log`.
- `experiments/performance/exp02b_1_diagnostic_20260909_142000/`: Diagnostic forensics, `EXP02C_PREREGISTRATION_FINAL_DRAFT.md`, analysis reports.
- `experiments/performance/exp02c_annealed_hard_negative_20260909_144000/`: Complete EXP-02C frozen artifacts (see Section 6).
- `experiments/exp02a_qualitative_gallery/`: Qualitative visual error analysis PNGs.
- `experiments/performance/gpu_*`: GPU baseline recovery, AWCC telemetry, G-Mode profiles, and thermal stability proofs.
- `experiments/performance/gate4_*`: Audit reports, environment benchmarks, and preflight verifications.

---

## 5. CATEGORY C — GENERATED / EPHEMERAL CONTAMINATION (354 Files)

This category represents **pure repository pollution**. These files were created during remote execution preparation or fetched recursively by Kaggle CLI tools. They contain redundant copies of canonical source code and intermediate container directories.

### Contamination Taxonomy:
1. **Mirrored Source Trees (`src_dataset_staging`) — 118 files**:
   - When staging Kaggle datasets (`ocean-sentinel-src`), local scripts recursively copied `src/ocean_sentinel/` into experiment subfolders:
     - `experiments/performance/exp02b_1_hard_negative_training_20260909_094500/src_dataset_staging/ocean_sentinel/**` (28 files)
     - `experiments/performance/gate4_3B_live_kaggle_canary_20260908_102118/src_dataset_staging/ocean_sentinel/**` (27 files)
     - `experiments/performance/gate4_3B_live_kaggle_canary_20260908_102118/src_dataset_staging_v2/ocean_sentinel/**` (27 files)
     - `experiments/performance/gate4_3C_A_gpu_qualification_20260908_194000/src_dataset_staging/ocean_sentinel/**` (28 files)
     - `experiments/performance/gate4_3C_C4_resume_epoch2_20260909_002000/seed_dataset_staging/**` (4 files)
     - Staged copies of markdown reports and metadata (e.g. `dataset-metadata.json`, duplicate `GATE_EXP02B_0_REPORT.md` inside staging) (4 files)
2. **Intermediate Canary Kernel Outputs — 101 files**:
   - `experiments/performance/gate4_3B_live_kaggle_canary_20260908_102118/kernel_output*/**`
   - `experiments/performance/gate4_3C_A_gpu_qualification_20260908_194000/kernel_output/**`
   - `experiments/performance/gate4_3C_B_one_epoch_pilot_20260908_220700/kernel_output/**`
   - `experiments/performance/gate4_3C_C2_canonical_seed_20260909_000500/kernel_output/**`
   - `experiments/performance/gate4_3C_C4_resume_epoch2_20260909_002000/kernel_output/**`
3. **Packaging & Push Bundles — 82 files**:
   - Folders assembled exclusively to run `kaggle kernels push`:
     - `experiments/**/kaggle_push_bundle/**`
     - `experiments/**/kaggle_canary_bundle/**`
     - `experiments/**/kaggle_training_bundle/**`
     - `experiments/**/bundle/**`
     - `experiments/**/kernel_push/**`
     - `experiments/**/kernel_pull*/**`
4. **Pulled Nested Container Duplicates — 42 files**:
   - When running `kaggle kernels output`, Kaggle exported the entire container `/kaggle/working/` hierarchy, causing files to be downloaded twice:
     - `experiments/performance/exp02c_annealed_hard_negative_20260909_144000/remote_training_output/exp02c_annealed_hard_negative_training/**` (contains duplicate copies of `best_model.pt`, `final_model.pt`, `latest_checkpoint.pt`, `history.json`, etc. that already exist at the experiment root)
     - `experiments/performance/exp02b_1_hard_negative_training_20260909_094500/kernel_output/exp02b_1_hard_negative_training/**` (contains duplicate checkpoints and logs)
     - `experiments/performance/exp02b_1_hard_negative_training_20260909_094500/kernel_output/scripts/**` (mirrored source copy from container)
5. **Ad-hoc Scratch Scripts (`scratch/`) — 8 files**:
   - Temporary canary gate scripts and debugging harnesses: `scratch/gate7_8_real_data_canary.py`, `scratch/fetch_exp02c_live_logs.py`, `scratch/gate4_code_diff.py`, `scratch/gate5_sampler_lifecycle.py`, `scratch/gate6_generator_audit.py`, etc.
6. **Ephemeral Test / Temp Dirs — 3 files**:
   - Preflight test dummy checkpoints: `experiments/performance/pre_upload_zero_defect_hardening_20260907_042853/**/temp/preflight_test.pt`

---

## 6. EXP-02C SCIENTIFIC ARTIFACT PRESERVATION & INTEGRITY AUDIT

All primary EXP-02C scientific artifacts were independently verified and hashed prior to any cleanup operations. **Zero EXP-02C primary files will be touched.**

| Artifact Path | File Size | Verified SHA-256 Hash | Status |
|---|:---:|:---:|:---:|
| `exp02c.../best_model.pt` | 292,467,955 B | `14073F677F0525D2B32358056BCFAB7ADA4B598B03DB4DEB5D3A9CE162B5071A` | **LOCKED / FROZEN** |
| `exp02c.../final_model.pt` | 292,470,107 B | `B3FC0DD08E8B2BD24025F8F7E22517739977B153AED82822B95B3ACBE0D161C2` | **LOCKED / FROZEN** |
| `exp02c.../latest_checkpoint.pt` | 292,474,571 B | `B250126F59A79BC23EF02A6BAD123D6B1655A76800AB590A0954194090428C60` | **LOCKED / FROZEN** |
| `exp02c.../experiment_identity.json` | 4,017 B | `B1768B5623A061026F35E266A6BD7CE6FE1D5FB1F7A1D3CE6FA7F03F290FDC7C` | **LOCKED / FROZEN** |
| `exp02c.../config.json` | 2,045 B | `B399E98CD7D6111C66FDAC0A0D7845BC9D2FA0C598BDBECC2563CD2FCF46D37B` | **LOCKED / FROZEN** |
| `exp02c.../history.json` | 27,381 B | `E7B607DBF2DBA5E1817F0793216664AF2A6BE89A06B8E63E15ECCB3D0C8DCE3B` | **LOCKED / FROZEN** |
| `exp02c.../run_state.json` | 21,711 B | `3D4AA2290C8AC434EFEE36EE6E03E0A034F356C0D5D2146399720C773631896A` | **LOCKED / FROZEN** |
| `exp02c.../provenance.json` | 1,991 B | `16A57E7F8C37161E4535F31F019C7990944D09687365E4A481B5C2B09EC08442` | **LOCKED / FROZEN** |
| `exp02c.../exp02c_sampling_schedule.csv` | 1,717 B | `BF62634B234E34C9AF7BD3B131AC1709EBE6F756198A41E3ED6D0DFAC148CBA0` | **LOCKED / FROZEN** |
| `exp02c.../EXP02C_POSTRUN_AUDIT.md` | 25,177 B | `6A39FBF9192A3B818DD632C005279FC4C8C4A23956C090DB47D0619768080367` | **LOCKED / FROZEN** |
| `exp02c.../EXP02C_PRETRAINING_FINAL_GATE.md` | 10,160 B | `79AA88E7DF293D34831A9886EC793FED315A85FBCC11451C41DCE9861750060F` | **LOCKED / FROZEN** |
| `exp02c.../preflight_report.md` | 7,998 B | `14FFA3CFD8EFD0BA6BC868ABD584744DF31F1FACC76B4FB97A6AC78DB7CBD398` | **LOCKED / FROZEN** |
| `exp02c.../progress.log` | 76,090 B | `35CFB2427EFBC29E2E2EE29138009F38226AE2F1490E81FFCF7A854328570E52` | **LOCKED / FROZEN** |
| `exp02c.../stdout_training.log` | 76,090 B | `35CFB2427EFBC29E2E2EE29138009F38226AE2F1490E81FFCF7A854328570E52` | **LOCKED / FROZEN** |
| `exp02c.../official_test_results.json` | 38,076 B | `ECF2D4AE10AFDE939BA3DDA99912488D1C3632EFD460118A26B17AD393437C6F` | **LOCKED / FROZEN** |
| `exp02c.../official_test_report.md` | 16,204 B | `C8BBB291D1523068D1A03592527F8CAF3181F5568637A6FBB5B6837A51B8AB76` | **LOCKED / FROZEN** |
| `exp02c.../confusion_matrix.json` | 108 B | `B837C058D1BBCD214C39491D9586A7D09B8A8F7876E6068E768BCEF669ED3A53` | **LOCKED / FROZEN** |
| `exp02c.../pairwise_vs_exp01.json` | 604 B | `3B36438BB1890351D8E84CBC066F7B3B99C6D6E504EDA10810B6A06109CDDAC0` | **LOCKED / FROZEN** |
| `exp02c.../pairwise_vs_exp02b_1.json` | 604 B | `116774BBBFAA4B41C43F65C8DB3A108164FE52108E0FB981E87DDFEBF04AC3B1` | **LOCKED / FROZEN** |
| `exp02c.../test_prediction_summary.json` | 418 B | `1CD87C94589BDB03DEF37231BD8CFB15FAD6E6C8147D785D1F6ADDE815741670` | **LOCKED / FROZEN** |

---

## 7. CATEGORY D — UNKNOWN / AMBIGUOUS ITEMS REQUIRING HUMAN REVIEW (4 Files)

Before executing cleanup, the following 4 files require explicit CAO confirmation:

1. **`experiments/performance/exp02b_1_hard_negative_training_20260909_094500/src_dataset_staging/candidate_manifest.json` (7.6 MB)**:
   - *Provenance Note*: Physically located inside `src_dataset_staging/`, but **directly referenced by**:
     - `scripts/train_exp02c.py` (Line 392 default argument)
     - `experiments/performance/exp02c_annealed_hard_negative_20260909_144000/provenance.json`
     - `experiments/performance/exp02c_annealed_hard_negative_20260909_144000/experiment_identity.json`
   - *Canonical Copy*: An identical copy with SHA-256 `5876A4E65FA636F6C0CD39377E56EEC6D9E848E8E48254927BE71ED4668B97E7` exists at `experiments/performance/exp02b_0_hard_negative_design_20260909_021500/candidate_manifest.json`.
   - *Recommendation*: **DO NOT DELETE**. Retain in place or update script defaults to point to `exp02b_0_hard_negative_design` before removing staging.
2. **`experiments/archive/exp01_interrupted_20260906_135852/best_model.pt` & `interruption_manifest.json` (2 files)**:
   - *Provenance Note*: Checkpoint and failure telemetry from an interrupted run on September 6.
   - *Recommendation*: Retain under `experiments/archive/` or move to cold storage. Do not delete without CAO sign-off.
3. **`experiments/performance/synthetic_upload_telemetry_test/upload_status.json` (1 file)**:
   - *Provenance Note*: Isolated mock output from unit testing the upload telemetry harness.
   - *Recommendation*: Confirm deletion as test stub.

---

## 8. PROPOSED .gitignore AMENDMENTS

To prevent future staging runs, container downloads, or push bundles from polluting git status, add the following targeted rules to `.gitignore`:

```gitignore
# ==============================================================================
# ML Experiment Staging & Container Output Ignored Patterns
# ==============================================================================

# Ephemeral dataset staging directories for remote uploads
experiments/**/src_dataset_staging/
experiments/**/src_dataset_staging_v2/
experiments/**/seed_dataset_staging/

# Exception: Retain approved candidate manifest if kept in staging
!experiments/performance/exp02b_1_hard_negative_training_20260909_094500/src_dataset_staging/candidate_manifest.json

# Ephemeral remote push/pull bundles and packaging
experiments/**/kaggle_push_bundle/
experiments/**/kaggle_canary_bundle/
experiments/**/kaggle_training_bundle/
experiments/**/kernel_push/
experiments/**/kernel_pull/
experiments/**/kernel_pull_v2/
experiments/**/bundle/

# Ephemeral preflight test runs and temp output
experiments/**/temp/
experiments/**/dry_run_preflight/
experiments/**/test_data_dir/
experiments/**/test_jupyter/

# Pulled nested container duplicates from Kaggle
experiments/**/kernel_output/
experiments/**/remote_training_output/exp02c_annealed_hard_negative_training/

# Local scratch analysis and debugging scripts
scratch/
```

---

## 9. SCIENTIFIC RISK ASSESSMENT

- **Risk of Cleaning Category C**: **ZERO**. Every Category C file is a duplicate of canonical source code already in `src/`, an intermediate canary runner, or an ephemeral zip/bundle reconstructed on-the-fly by packaging scripts.
- **Risk of Touching Category B**: **CATASTROPHIC**. Deleting or altering Category B files would destroy training logs, model checkpoints, and frozen test evaluation records. All 450 Category B files are protected.
- **Risk of Unchecked Category D**: **HIGH**. Blind deletion of `candidate_manifest.json` under `exp02b_1/.../src_dataset_staging/` would break default execution of `scripts/train_exp02c.py` and invalidate documented provenance links. Hence, it is protected in Category D.

---

## 10. PROPOSED EXECUTION WORKFLOW (FOR FUTURE AUTHORIZATION)

Once authorized by the CAO, cleanup should execute in three phased, non-destructive steps:
1. **Step 1 (Canonical Source Commit)**: `git add` and commit all 85 Category A files (`src/`, `scripts/`, `tests/`, `docs/`, `data/metadata/`).
2. **Step 2 (Update .gitignore)**: Add the surgical ignore rules above to `.gitignore` and commit.
3. **Step 3 (Category C Decontamination)**: Safely remove the 354 Category C files and directories, preserving Category D until explicitly resolved.
