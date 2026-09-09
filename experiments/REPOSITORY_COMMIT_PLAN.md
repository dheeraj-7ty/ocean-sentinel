# REPOSITORY COMMIT ARCHITECTURE PLAN

**Author**: Antigravity IDE Agent (under CAO Master Oversight)  
**Date**: 2026-09-09  
**Baseline Git HEAD**: `8f444de1d0fb35d09912a9e6bf27cebde8125f0d`  
**Active Branch**: `master`  
**Current Remaining Working Tree Entries**: **541 entries** (plus `.gitignore` modification = 542)  
**Execution Authorization Status**: **PLANNING ONLY (ZERO COMMITS EXECUTED)**  
**Audit Progress Log**: [`scratch/commit_audit_progress.log`](file:///d:/Projects/ocean-sentinel/scratch/commit_audit_progress.log)  
**Machine-Readable Commit Inventory**: [`scratch/commit_inventory.json`](file:///d:/Projects/ocean-sentinel/scratch/commit_inventory.json)

---

## 1. EXECUTIVE SUMMARY & REPOSITORY REALITY

Following the completion of the repository hygiene cleanup (which removed 376 ephemeral staging files and container duplicate outputs), 541 paths remain in the repository working tree. 

Rather than creating a single, unstructured "everything changed" commit, this document defines a disciplined, 10-commit modular commit architecture. Each commit is logically isolated, independently verifiable, strictly ordered by dependency, and designed to preserve scientific evidence and historical provenance.

### Current Working Tree Classification:
| Category | Classification Definition | File Count | Proposed Git Disposition |
|---|---|:---:|---|
| **Category A** | **Canonical Source** | **50** | Commit directly to Git in structured functional groups |
| **Category B** | **Canonical Docs, Contracts, & Tests** | **36** | Commit directly to Git alongside corresponding source modules |
| **Category C** | **Scientific Experiment Artifacts (Text/JSON/MD)** | **389** | Commit directly to Git as scientific evidence |
| **Category D** | **Historical Archive Documentation** | **1** | Commit directly to Git (`interruption_manifest.json`) |
| **Category E** | **Generated / Preserved Telemetry, Logs, & PNGs** | **53** | Commit directly to Git (visual error masks & execution logs) |
| **Category F** | **Large Binaries (`*.pt` Checkpoints)** | **13** | **Git LFS** or External Checkpoint Storage (DO NOT commit to raw Git) |
| **Category G** | **Unknown / Unclassified** | **0** | None |
| **Total** | | **542** | |

---

## 2. LARGE ARTIFACT AUDIT & STORAGE POLICY (Category F)

All files exceeding 10 MB or containing raw model weights were audited. A total of **13 `.pt` checkpoint files** exist across the repository, totaling approximately **3.62 GB**:

| File Path | File Size | Scientific Importance | Appropriate for Raw Git? | Recommendation |
|---|:---:|:---:|:---:|---|
| `experiments/performance/exp02c_.../best_model.pt` | 278.92 MB | **Critical** (Official EXP-02C Checkpoint) | **NO** | **Git LFS / External Artifact Storage** |
| `experiments/performance/exp02c_.../final_model.pt` | 278.92 MB | High (Epoch 30 Checkpoint) | **NO** | **Git LFS / External Artifact Storage** |
| `experiments/performance/exp02c_.../latest_checkpoint.pt` | 278.93 MB | High (Optimizer/Resume State) | **NO** | **Git LFS / External Artifact Storage** |
| `experiments/performance/exp02c_.../remote_training_output/best_model.pt` | 278.92 MB | Duplicate (Identical to root) | **NO** | Keep local / Do not commit |
| `experiments/performance/exp02c_.../remote_training_output/final_model.pt` | 278.92 MB | Duplicate (Identical to root) | **NO** | Keep local / Do not commit |
| `experiments/performance/exp02c_.../remote_training_output/latest_checkpoint.pt` | 278.93 MB | Duplicate (Identical to root) | **NO** | Keep local / Do not commit |
| `experiments/exp01_baseline/best_model.pt` | 278.92 MB | **Critical** (Baseline Reference) | **NO** | **Git LFS / External Artifact Storage** |
| `experiments/exp01_baseline/final_model.pt` | 278.92 MB | High (Baseline Final) | **NO** | **Git LFS / External Artifact Storage** |
| `experiments/exp01_baseline/latest_checkpoint.pt` | 278.92 MB | High (Baseline Latest) | **NO** | **Git LFS / External Artifact Storage** |
| `experiments/.../kernel_output/.../best_model.pt` (EXP02B-1) | 278.91 MB | **Critical** (Candidate Reference) | **NO** | **Git LFS / External Artifact Storage** |
| `experiments/.../kernel_output/.../final_model.pt` (EXP02B-1) | 278.92 MB | High (Candidate Final) | **NO** | **Git LFS / External Artifact Storage** |
| `experiments/.../kernel_output/.../latest_checkpoint.pt` (EXP02B-1) | 278.92 MB | High (Candidate Latest) | **NO** | **Git LFS / External Artifact Storage** |
| `experiments/archive/exp01_interrupted_.../best_model.pt` | 278.91 MB | Moderate (Historical Archive) | **NO** | Cold Storage / Git LFS Archive |

### Policy for Experiment Checkpoints:
1. **Never commit `.pt` files directly into standard Git trees.** Doing so would permanently bloat the Git packfile by ~3.6 GB.
2. Checkpoints should either be tracked via **Git LFS** (with a dedicated `.gitattributes` configuration) or preserved in an authenticated S3 / GCS / Kaggle Model registry with verified SHA-256 links recorded in Git.
3. The duplicate copies under `exp02c/.../remote_training_output/*.pt` should remain local and uncommitted.

---

## 3. PROPOSED 10-STAGE MODULAR COMMIT ARCHITECTURE

### Commit 1: Repository Hygiene & Project Configuration
- **Commit Message**: `build(repo): establish repository hygiene, project configuration, and ignore rules`
- **Purpose**: Establishes git ignore rules preventing future staging contamination and updates core package dependencies.
- **Exact Paths**:
  - `.gitignore`
  - `pyproject.toml`
- **Approx File Count**: 2
- **Category**: Canonical Source / Configuration
- **Dependencies**: None (Root)
- **Validation**: Verify `git status` honors ignore rules cleanly.

---

### Commit 2: SAR Preprocessing & Radiometric Calibration (ADR-002)
- **Commit Message**: `feat(preprocessing): generalize SAR radiometric calibration and noise filtering (ADR-002)`
- **Purpose**: Implements generalized radiometric calibration, decibel conversion, clipping, and nodata handling for Sentinel-1 GRD imagery.
- **Exact Paths**:
  - `src/ocean_sentinel/errors.py`
  - `src/ocean_sentinel/processing/__init__.py`
  - `src/ocean_sentinel/processing/models.py`
  - `src/ocean_sentinel/processing/sar.py`
  - `tests/test_preprocessing.py`
  - `docs/adr/002-radiometric-unit-generalization.md`
  - `docs/sar-preprocessing.md`
- **Approx File Count**: 7
- **Category**: Canonical Source, Tests, Docs
- **Dependencies**: Commit 1
- **Validation**: `pytest tests/test_preprocessing.py` (Must pass 100%).

---

### Commit 3: Dataset Ingestion, Normalization, & Dataset Contracts
- **Commit Message**: `feat(ingestion): establish dataset ingestion, tiling contracts, and CDSE validation`
- **Purpose**: Implements Trujillo 2024 SAR ingestion, automated tiling, and CDSE/DARTIS cross-validation.
- **Exact Paths**:
  - `src/ocean_sentinel/ingestion/__init__.py`
  - `src/ocean_sentinel/ingestion/dataset.py`
  - `src/ocean_sentinel/ingestion/models.py`
  - `src/ocean_sentinel/ingestion/tiling.py`
  - `src/ocean_sentinel/ingestion/trujillo.py`
  - `scripts/download_datasets.py`
  - `scripts/audit_trujillo_dataset.py`
  - `scripts/verify_dartis_cdse.py`
  - `tests/test_trujillo_ingestion.py`
  - `tests/test_dataset_pipeline.py`
  - `tests/test_dartis_cross_validation.py`
  - `docs/trujillo-dataset-contract.md`
  - `docs/dartis-cdse-cross-validation.md`
  - `docs/dataset-ingestion-readiness.md`
  - `data/metadata/yang_singha_2025/data_matrix.tab`
  - `data/metadata/yang_singha_2025/cdse_validation_report.json`
  - `data/metadata/trujillo_2024/archive_listing.json`
  - `data/metadata/trujillo_2024/dataset_audit_report.json`
- **Approx File Count**: 18
- **Category**: Canonical Source, Scripts, Tests, Docs, Metadata
- **Dependencies**: Commit 2
- **Validation**: `pytest tests/test_trujillo_ingestion.py tests/test_dataset_pipeline.py tests/test_dartis_cross_validation.py`.

---

### Commit 4: Spatial Partitioning & Zero-Leakage Governance (ADR-004)
- **Commit Message**: `feat(split): implement spatial split partition and leakage governance (ADR-004)`
- **Purpose**: Establishes parent-patch spatial partitioning and certifies canonical split manifest `C052720A...` (2,880 test tiles).
- **Exact Paths**:
  - `src/ocean_sentinel/ingestion/split.py`
  - `scripts/generate_spatial_split_manifest.py`
  - `scripts/generate_split_manifest.py`
  - `scripts/audit_spatial_leakage.py`
  - `tests/test_spatial_split.py`
  - `docs/adr/004-spatially-defensible-dataset-partition.md`
  - `data/metadata/trujillo_2024/spatial_split_manifest.json`
  - `data/metadata/trujillo_2024/split_manifest.json`
  - `data/metadata/trujillo_2024/spatial_split_audit.json`
  - `data/metadata/trujillo_2024/spatial_leakage_report.json`
- **Approx File Count**: 10
- **Category**: Canonical Source, Scripts, Tests, Docs, Metadata
- **Dependencies**: Commit 3
- **Validation**: `pytest tests/test_spatial_split.py` and manifest hash assertion (`C052720A...`).

---

### Commit 5: ML Model Architecture & CUDA Governance (ADR-003 & ADR-005)
- **Commit Message**: `feat(ml): implement ResNet34-UNet segmentation, loss functions, and CUDA governance (ADR-003)`
- **Purpose**: Implements ResNet34-UNet architecture, slice-variance adapted SAR front-end, BCE+Dice loss, IoU metrics, threshold calibration, and resume qualification.
- **Exact Paths**:
  - `src/ocean_sentinel/ml/__init__.py`
  - `src/ocean_sentinel/ml/unet_resnet.py`
  - `src/ocean_sentinel/ml/losses.py`
  - `src/ocean_sentinel/ml/metrics.py`
  - `src/ocean_sentinel/ml/threshold.py`
  - `src/ocean_sentinel/ml/augmentation.py`
  - `src/ocean_sentinel/ml/canonical_exp01.py`
  - `src/ocean_sentinel/ml/gpu_qualification.py`
  - `tests/test_ml_components.py`
  - `tests/test_canonical_exp01_fingerprint.py`
  - `tests/test_gpu_qualification.py`
  - `tests/test_resume_qualification.py`
  - `docs/adr/003-ml-model-architecture-cuda-and-leakage-governance.md`
  - `docs/adr/005-resumed-training-infrastructure-qualification.md`
- **Approx File Count**: 14
- **Category**: Canonical Source, Tests, Docs
- **Dependencies**: Commit 4
- **Validation**: `pytest tests/test_ml_components.py tests/test_gpu_qualification.py`.

---

### Commit 6: Test Infrastructure & Remote Cloud Training Orchestration
- **Commit Message**: `feat(infra): build test runner, remote cloud upload harness, and packaging tools`
- **Purpose**: Automated test suite runner, cloud dataset upload harness with stall detection, canary packaging tools, and architecture documentation.
- **Exact Paths**:
  - `src/ocean_sentinel/cloud/__init__.py`
  - `src/ocean_sentinel/cloud/upload_harness.py`
  - `scripts/run_test_suite.py`
  - `scripts/gate4_upload_harness.py`
  - `scripts/package_exp02c_canary.py`
  - `scripts/package_exp02c_training.py`
  - `tests/test_upload_harness.py`
  - `tests/test_pilot_runner.py`
  - `docs/test-infrastructure.md`
  - `docs/context/architecture-state.md`
  - `docs/context/current-checkpoint.md`
  - `docs/context/dataset-state.md`
  - `docs/context/decisions-and-constraints.md`
  - `docs/context/implementation-history.md`
  - `docs/context/project-context.md`
- **Approx File Count**: 15
- **Category**: Canonical Source, Scripts, Tests, Docs
- **Dependencies**: Commit 5
- **Validation**: `python scripts/run_test_suite.py --suite default`.

---

### Commit 7: Canonical Training & Test Evaluation Pipelines
- **Commit Message**: `feat(pipeline): establish canonical training and evaluation pipelines for EXP-01, EXP-02B-1, and EXP-02C`
- **Purpose**: Canonical CLI pipelines for reproducible training, official test evaluation, preflight auditing, and diagnostic forensics.
- **Exact Paths**:
  - `scripts/train_exp01.py`
  - `scripts/train_exp02b_1.py`
  - `scripts/train_exp02c.py`
  - `scripts/evaluate_exp02b_1_test.py`
  - `scripts/evaluate_exp02c_test.py`
  - `scripts/verify_exp02b_1_preflight.py`
  - `scripts/diagnose_exp02b_1.py`
  - `scripts/audit_exp02a_quality.py`
  - `scripts/forensic_profiling_step2c_a.py`
  - `tests/test_exp01_eval.py`
- **Approx File Count**: 10
- **Category**: Canonical Scripts, Tests
- **Dependencies**: Commit 6
- **Validation**: `python scripts/evaluate_exp02c_test.py --help` and `pytest tests/test_exp01_eval.py`.

---

### Commit 8: Hardware Qualification, Thermal Profiling, & GPU Benchmark Reports
- **Commit Message**: `docs(benchmarks): document GPU baseline recovery, thermal profiles, and qualification gates`
- **Purpose**: Commits empirical hardware telemetry, AWCC/G-Mode profiles, reboot baselines, and Gate 4 cloud qualification reports.
- **Exact Paths**:
  - `scripts/benchmark_awcc_ultra_performance.py`
  - `scripts/benchmark_baseline_recovery.py`
  - `scripts/benchmark_exp00.py`
  - `scripts/benchmark_exp01_perf.py`
  - `scripts/benchmark_gmode_controlled.py`
  - `scripts/benchmark_gpu_baseline.py`
  - `scripts/benchmark_gpu_optimization.py`
  - `scripts/benchmark_gpu_step2b.py`
  - `scripts/benchmark_reboot_baseline.py`
  - `scripts/benchmark_step2c_b.py`
  - `data/metadata/trujillo_2024/exp00_benchmark_results.json`
  - `experiments/performance/gpu_*`
  - `experiments/performance/gate4_*` (Markdown reports and JSON telemetry only)
  - `experiments/performance/cloud_*` (Reports and probe results)
  - `experiments/performance/test_infrastructure_hardening_*`
- **Approx File Count**: ~180
- **Category**: Scripts, Telemetry JSON, Markdown Reports
- **Dependencies**: Commit 7
- **Validation**: File existence and integrity verification.

---

### Commit 9: Scientific Experiment Evidence & Official Test Evaluations
- **Commit Message**: `docs(experiments): record scientific artifacts, reports, and official test evaluations for EXP-01 through EXP-02C`
- **Purpose**: Commits all scientific experiment identities, training histories, candidate design manifests, official held-out test evaluation reports, confusion matrices, paired McNemar statistics, and hygiene audit reports (excluding `.pt` binary weights).
- **Exact Paths**:
  - `experiments/exp01_baseline/` (`config.json`, `history.json`, `run_state.json`, `exp01_results.json`, `benchmark_report.json`, `checkpoint_integrity.json`, qualitative images)
  - `experiments/exp02a_qualitative_gallery/` (8 visual diagnostic PNG masks)
  - `experiments/performance/exp02b_0_hard_negative_design_20260909_021500/` (`candidate_manifest.json`, `GATE_EXP02B_0_REPORT.md`, mining scripts)
  - `experiments/performance/exp02b_1_hard_negative_training_20260909_094500/` (`GATE_EXP02B_1_REPORT.md`, `bundle_manifest.json`, `kernel_output/exp02b_1_hard_negative_training/history.json`, `run_state.json`, `progress.log`)
  - `experiments/performance/exp02b_1_diagnostic_20260909_142000/` (`EXP02C_PREREGISTRATION_FINAL_DRAFT.md`, diagnostic JSONs)
  - `experiments/performance/exp02c_annealed_hard_negative_20260909_144000/`:
    - `experiment_identity.json`
    - `config.json`
    - `history.json`
    - `run_state.json`
    - `provenance.json`
    - `exp02c_sampling_schedule.csv`
    - `EXP02C_POSTRUN_AUDIT.md`
    - `EXP02C_PRETRAINING_FINAL_GATE.md`
    - `preflight_report.md`
    - `progress.log`
    - `stdout_training.log`
    - `official_test_evaluation/official_test_results.json`
    - `official_test_evaluation/official_test_report.md`
    - `official_test_evaluation/confusion_matrix.json`
    - `official_test_evaluation/pairwise_vs_exp01.json`
    - `official_test_evaluation/pairwise_vs_exp02b_1.json`
    - `official_test_evaluation/test_prediction_summary.json`
    - `official_test_evaluation/progress.log`
    - `official_test_evaluation/run_state.json`
  - `experiments/performance/GATE_*.md`
  - `experiments/REPOSITORY_HYGIENE_PLAN.md`
  - `experiments/REPOSITORY_HYGIENE_FINAL_REPORT.md`
  - `experiments/REPOSITORY_COMMIT_PLAN.md`
- **Approx File Count**: ~250
- **Category**: Scientific Documentation, JSON Results, CSV Schedules, Visual PNGs
- **Dependencies**: Commit 8
- **Validation**: Certified SHA-256 hash assertions match 100%.

---

### Commit 10: Historical Archive (EXP-01 Interrupted Run)
- **Commit Message**: `docs(archive): preserve historical failure telemetry for interrupted EXP-01 run`
- **Purpose**: Preserves historical failure telemetry for the interrupted training run of September 6.
- **Exact Paths**:
  - `experiments/archive/exp01_interrupted_20260906_135852/interruption_manifest.json`
- **Approx File Count**: 1
- **Category**: Historical Archive JSON
- **Dependencies**: Commit 9
- **Validation**: JSON integrity check.

---

## 4. DEPENDENCY & CONSISTENCY AUDIT FINDINGS

1. **`scripts/train_exp02c.py`**:
   - Verified that Line 392 references the canonical candidate manifest path:  
     `REPO_ROOT / "experiments/performance/exp02b_0_hard_negative_design_20260909_021500/candidate_manifest.json"`.
   - Hash matches certified value `5876A4E6...` bit-for-bit.
2. **Zero Staging Dependencies in Core Code**:
   - `src/ocean_sentinel/` and `tests/` contain zero references to `src_dataset_staging`, `kaggle_push_bundle`, or `seed_dataset_staging`.
3. **Follow-Up Item Identified in `scripts/gate4_upload_harness.py`**:
   - Line 198 of `scripts/gate4_upload_harness.py` defines default simulation output path:  
     `REPO_ROOT / "experiments" / "performance" / "synthetic_upload_telemetry_test"`.
   - Because `synthetic_upload_telemetry_test` was removed as an ephemeral mock test directory, running `cmd_simulate` will recreate this directory on-demand.
   - *Recommendation*: As a minor future follow-up, change the default simulation directory to a temporary path under `temp/` or make `--output-dir` required for simulations.

---

## 5. CANONICAL HASH SAFETY VERIFICATION (ALL PASS)

All certified hashes remain identical to their frozen baselines:
- **EXP02C `best_model.pt`**: `14073F677F0525D2B32358056BCFAB7ADA4B598B03DB4DEB5D3A9CE162B5071A` [MATCH]
- **EXP02C `official_test_results.json`**: `ECF2D4AE10AFDE939BA3DDA99912488D1C3632EFD460118A26B17AD393437C6F` [MATCH]
- **Canonical Spatial Manifest**: `C052720A954C2E7A3E9A87AA64557450BF0DEABEC71D54C2A813849DB60812E0` [MATCH]
- **Canonical Candidate Manifest**: `5876A4E65FA636F6C0CD39377E56EEC6D9E848E8E48254927BE71ED4668B97E7` [MATCH]
- **EXP01 Checkpoint `best_model.pt`**: `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699` [MATCH]
- **EXP02B-1 Checkpoint `best_model.pt`**: `54B4B098E1EB64A7422F0401C1CFB8BE81EFCDF4ABACFBC4D3B35B4499765E4B` [MATCH]

---

## 6. FILES THAT MUST NEVER BE COMMITTED TO RAW GIT

1. **`*.pt` (Model Weights)**: 13 files, ~3.62 GB. Must be tracked via Git LFS or external artifact storage.
2. **`scratch/*`**: Ad-hoc debugging, inspection, and temporary script files (safely ignored by `.gitignore`).
3. **`*/remote_training_output/exp02c_...` and duplicate staging folders**: Already removed and blocked by `.gitignore`.
