# EXP01 Repository Conflict Map

**Audit Date**: 2026-09-07  
**Scope**: All tracked and untracked repository files (`scripts/`, `src/`, `experiments/`, `tests/`, `docs/`)  
**Objective**: Detect and categorize any experiment drift, stale code, conflicting configs, or scheduler/learning rate ambiguities.

---

## 1. Conflict Term Search Results

| Search Term | Repository Matches | Affected Files / Locations | Interpretation |
|---|---|---|---|
| `5e-4` | 0 in codebase / 0 in git | Only user prompt & explicit negative test in `tests/test_canonical_exp01_fingerprint.py` | **Non-existent in repo**. Traceable strictly to LLM hallucination in prior chat markdown turn. |
| `1e-4` (or `0.0001`) | 39 matches | `scripts/train_exp01.py`, `experiments/exp01_baseline/config.json`, `run_state.json`, `exp01_results.json`, `experiment_fingerprint.json`, benchmarks | **Unanimous Canonical Baseline**. Consistent across all code, configs, and artifacts. |
| `CosineAnnealingWarmRestarts` | 0 in codebase / 0 in git | Only user prompt & negative test in `tests/test_canonical_exp01_fingerprint.py` | **Non-existent in repo**. Traceable strictly to LLM hallucination in prior chat markdown turn. |
| `CosineAnnealingLR` | 10 matches | `scripts/train_exp01.py:L24, L321, L960, L1287`, `experiments/exp01_baseline/experiment_fingerprint.json:L32`, `src/ocean_sentinel/ml/canonical_exp01.py` | **Unanimous Canonical Scheduler**. Used in all baseline scripts and checkpoints. |
| `warmup` | 85 matches | Exclusively in benchmarking harness (`scripts/benchmark_awcc_ultra_performance.py`, `scripts/benchmark_baseline_recovery.py`) referring to GPU/DataLoader warmup batches (e.g. 20 warmup batches before timing). | **Zero impact on EXP01 training**. No learning rate warmup was used in EXP01. |
| `T_0` / `T_mult` | 0 in code/configs | Checkpoint state dicts verify neither key exists in `lr_scheduler`. | **Non-existent in repo**. |
| `max_epochs` / `epochs` | 36 matches | `scripts/train_exp01.py:L110, L322`, `experiments/exp01_baseline/config.json:L7` (value `30`), `run_state.json` (value `30`) | **Unanimous Canonical Setting**: `max_epochs = 30`. |
| `30` | Ubiquitous in manifests & configs | Matches `epochs: 30`, `T_max: 30`, `patience: 10`, etc. | Verified canonical budget. |
| `50` | Metadata and augmentations | Not used as training epoch count anywhere in EXP01. | No conflict with EXP01. |

---

## 2. Structural Conflict Analysis

### A. Multiple Experiment Variants
- **Finding**: No conflicting variant branches exist for EXP01.
- **Evidence**: `scripts/train_exp01.py` is the single training entrypoint for the baseline experiment. Later experiments (such as EXP02a) are isolated in separate evaluation and benchmark scripts and do not masquerade as EXP01.

### B. Stale Code
- **Finding**: No stale code setting `lr = 5e-4` or `CosineAnnealingWarmRestarts` was found.
- **Evidence**: `scripts/train_exp01.py` defaults have always been `--lr 1e-4`, `--weight-decay 1e-2`, and `CosineAnnealingLR(T_max=30, eta_min=1e-6)`.

### C. Stale Documentation
- **Finding**: The only discrepancy was in the prior assistant's chat turn markdown output (line 4008 of `transcript_full.jsonl`).
- **Resolution**: All actual serialized reports in the filesystem (`pre_upload_zero_defect_hardening_20260907_042853/report.md`, `canonical_fingerprint.json`) recorded the true canonical values (`1e-4`, `CosineAnnealingLR`). This audit creates the definitive erratum and forensic audit.

### D. Fingerprint Generator
- **Finding**: Previously, fingerprints were either generated via ad-hoc dictionary construction in `train_exp01.py` or manually validated.
- **Resolution**: Created `src/ocean_sentinel/ml/canonical_exp01.py`, which provides a centralized, immutable canonical specification and fingerprint builder (`build_canonical_fingerprint_dict()`), backed by 11 pytest regression tests in `tests/test_canonical_exp01_fingerprint.py`.

### E. Training Script Drift
- **Finding**: Zero drift detected. The training script matches certified baseline artifacts 100%.

### F. Configuration Duplication
- **Finding**: `experiments/exp01_baseline/config.json` is the authoritative static configuration for EXP01. All fields align with `run_state.json` and checkpoint state dicts.

---

## 3. Conflict Status: RESOLVED
All potential discrepancies between `1e-4` vs `5e-4` and `CosineAnnealingLR` vs `CosineAnnealingWarmRestarts` have been proven to be external to the codebase and artifacts, originating solely from an LLM hallucination in chat text. The canonical repository configuration is 100% harmonious.
