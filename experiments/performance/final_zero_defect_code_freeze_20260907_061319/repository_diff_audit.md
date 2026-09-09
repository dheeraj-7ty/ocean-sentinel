# Ocean Sentinel — Repository Diff & Git Safety Audit

**Audit Target**: Working Tree Integrity & Untracked / Modified File Classification  
**Authority**: Ocean Sentinel Chief AI Officer (CAO)  
**Baseline HEAD**: `8f444de` (*"Phase 1C.2: Oil-spill dataset reconnaissance & selection strategy"*)  

---

## 1. Classification of Modified & Untracked Files

| File / Path | Git Status | Classification | Assessment & Rationale |
| :--- | :---: | :---: | :--- |
| `data/metadata/yang_singha_2025/data_matrix.tab` | `A` | **PRE-EXISTING** | Added in Phase 1C. Preserved intact. |
| `docs/sar-preprocessing.md` | `M` | **PRE-EXISTING** | Phase 1C preprocessing documentation. Preserved intact. |
| `scripts/download_datasets.py` | `AM` | **PRE-EXISTING** | Phase 1C dataset download utility. Preserved intact. |
| `src/ocean_sentinel/errors.py` | `M` | **PRE-EXISTING** | Error taxonomy additions from Phase 1C. Preserved intact. |
| `src/ocean_sentinel/processing/models.py` | `M` | **PRE-EXISTING** | Preprocessing data models from Phase 1C. Preserved intact. |
| `src/ocean_sentinel/processing/sar.py` | `M` | **PRE-EXISTING** | SAR preprocessing logic from Phase 1C. Preserved intact. |
| `tests/test_preprocessing.py` | `M` | **PRE-EXISTING** | Preprocessing unit tests from Phase 1C. Preserved intact. |
| `data/metadata/trujillo_2024/` | `??` | **PRE-EXISTING** | Canonical spatial split manifest & audit report. Preserved intact. |
| `data/metadata/yang_singha_2025/cdse_validation_report.json` | `??` | **PRE-EXISTING** | Phase 1C CDSE validation report. Preserved intact. |
| `docs/adr/002-004` | `??` | **PRE-EXISTING** | Architecture Decision Records for Phase 2. Preserved intact. |
| `docs/context/` | `??` | **PRE-EXISTING** | Architecture context documents. Preserved intact. |
| `docs/dartis-cdse-cross-validation.md` | `??` | **PRE-EXISTING** | Validation doc. Preserved intact. |
| `docs/dataset-ingestion-readiness.md` | `??` | **PRE-EXISTING** | Readiness assessment. Preserved intact. |
| `docs/trujillo-dataset-contract.md` | `??` | **PRE-EXISTING** | Trujillo dataset contract. Preserved intact. |
| `experiments/` | `??` | **PRE-EXISTING / GENERATED** | Baseline EXP-01 artifacts & historical qualification directories. Preserved intact. |
| `scripts/audit_*.py`, `scripts/benchmark_*.py`, `scripts/generate_*.py` | `??` | **PRE-EXISTING** | Phase 2 utility and benchmark scripts. Preserved intact. |
| `scripts/train_exp01.py` | `??` | **PRE-EXISTING** | EXP-01 Rev B training runner (Hardened with `--data-dir` and `build_arg_parser`). |
| `src/ocean_sentinel/ingestion/` | `??` | **PRE-EXISTING** | Ingestion & split modules (`dataset.py`, `split.py`, `provenance.py`). |
| `src/ocean_sentinel/ml/` | `??` | **PRE-EXISTING** | ML modules (`unet_resnet.py`, `losses.py`, `metrics.py`, `threshold.py`, `augmentation.py`). |
| `tests/test_dartis_cross_validation.py` | `??` | **PRE-EXISTING** | Phase 1C cross validation tests. Preserved intact. |
| `tests/test_dataset_pipeline.py` | `??` | **PRE-EXISTING** | Phase 2.1 dataset pipeline unit tests. Preserved intact. |
| `tests/test_exp01_eval.py` | `??` | **PRE-EXISTING** | Phase 2.3 EXP01 evaluation tests (Hardened with `*args, **kwargs`). |
| `tests/test_ml_components.py` | `??` | **PRE-EXISTING** | Phase 2.3 ML model and loss unit tests. Preserved intact. |
| `tests/test_spatial_split.py` | `??` | **PRE-EXISTING** | Phase 2.4 spatial split unit tests. Preserved intact. |
| `tests/test_trujillo_ingestion.py` | `??` | **PRE-EXISTING** | Phase 2.0 raw ingestion unit tests. Preserved intact. |
| `experiments/performance/final_zero_defect_code_freeze_20260907_061319/` | `??` | **GENERATED-AUDIT** | Current Gate 4.4 code freeze audit artifacts. |

---

## 2. Git Invariants Verified

- **Zero Git Destructive Actions**: No `git reset`, `git clean`, `git checkout`, or `git stash` was executed.
- **Zero Uncommitted Work Discarded**: All cumulative Phase 1 and Phase 2 uncommitted work remains 100% intact.
- **Zero Accidental Binary Files**: No large binary weights or data dumps created in source or tracked folders.
- **Zero Secret Exposure**: No credentials or private tokens introduced into tracked files.
- **Zero Modification to Canonical Checkpoints**: Reference checkpoints in `experiments/exp01_baseline/` match canonical SHA-256 hashes.
