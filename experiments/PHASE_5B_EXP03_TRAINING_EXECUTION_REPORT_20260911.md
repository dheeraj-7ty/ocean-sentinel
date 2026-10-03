# Ocean Sentinel: Phase 5B EXP-03 Training Execution & Forensic Audit Report
**Date**: 2026-09-11  
**Project**: Ocean Sentinel  
**Experiment**: EXP-03 Hard-Negative Baseline Training  
**Author**: Antigravity IDE Implementation, Recovery, and Execution Agent  
**Governance**: Chief Architect Officer (CAO) Strict Governance  

---

## 1. Executive Summary

Phase 5B (EXP-03 Hard-Negative Baseline) training was authorized by the CAO to evaluate whether exposing the ResNet-34 U-Net model to hard-negative development tiles (12.5% two-stream exposure; 14 standard tiles + 2 mined tiles per batch) reduces clean-water false alarms without compromising core segmentation capability.

The execution traversed an initial implementation failure during Epoch 1 validation metric extraction (Attempt 001), followed by evidence preservation, code repair, regression testing, transaction-safe preflighting, and a full clean rerun (Attempt 002) for 10 epochs. Independent post-training validation on the canonical Trujillo Part I validation split (2,880 tiles) confirmed:
1. **False Alarm Reduction**: Clean-water false alarm rate plummeted from **20.09%** (baseline) to **0.33%** (EXP-03 Best, Epoch 9). Significant false alarm rate dropped from **10.56%** to **0.33%**. Total validation false positive pixels dropped from **2,327,942** to **79,742** (a 96.6% continuous reduction in false alarm burden).
2. **Segmentation Capability & Non-Inferiority Gates**: Validation global IoU reached **0.70435** (against pre-registered non-inferiority gate of $\ge 0.71731$, shortfall of 0.01296 IoU points). Validation recall reached **0.77287** (against pre-registered non-inferiority gate of $\ge 0.80000$, shortfall of 0.02713; baseline teacher was 0.78488).
3. **Acceptance Status**: While the primary false alarm reduction criteria were massively exceeded, the strict binary non-inferiority threshold was not crossed. Therefore, under pre-registered criteria, `EXP03_ACCEPTANCE_STATUS = FAIL`.

---

## 2. Parameter Count Authority & Architectural Reconciliation

Historical records in prior audits contained an apparent contradiction:
- Earlier canonical record: 24,346,305 parameters
- Later audit reference: 24,365,359 elements

### Empirical Reconciliation (Observed Facts)
Direct inspection of `ResNet34UNet(in_channels=2, num_classes=1, adaptation_method='slice_variance_scaled')` and the canonical checkpoint `experiments/exp01_baseline/best_model.pt` established:
- `sum(p.numel() for p in model.parameters())` = **24,346,305** (100% learnable, trainable weights).
- `sum(b.numel() for b in model.buffers())` = **19,054** (persistent BatchNorm running mean and variance buffers).
- `sum(v.numel() for v in model.state_dict().values())` = **24,365,359** ($24,346,305 + 19,054$).

**Authoritative Conclusion**:
- Authoritative learnable model parameters: **24,346,305**.
- Total state dict elements (parameters + persistent buffers): **24,365,359**.
- The discrepancy was a documentation convention issue where state dict elements were cited as "model parameters".

---

## 3. Attempt 001 Failure Audit & Evidence Preservation

### Execution Timeline & Failure Mode
- **Launch**: 2026-09-11T15:36:22Z under task `task-4292`.
- **Training Progression**: Completed all 960 batches of Epoch 1 without error (duration: 488s, loss ended at 0.2994).
- **Validation Progression**: Completed all 180 validation inference batches (2,880 tiles).
- **Failure Root Cause**: Line 426 of `scripts/train_exp03.py` executed:
  ```python
  summary = meter.summary()
  ```
  `SegmentationMeter` in `src/ocean_sentinel/ml/metrics.py` exposes `meter.compute()`, not `meter.summary()`. Python raised `AttributeError: 'SegmentationMeter' object has no attribute 'summary'`.
- **Checkpoint Status**: `NO_VALID_CHECKPOINT_EXISTED`. Checkpoint serialization was strictly gated behind metric extraction. Attempt 001 produced zero `.pt` files.
- **Classification**: Correctly classified as non-resumable.

### Evidence Preservation (Observed Facts)
- State preserved: `experiments/performance/exp03_baseline_hard_neg/run_state.failed_attempt_001.json` (685 bytes).
- Log preserved: `experiments/performance/exp03_baseline_hard_neg/failure.failed_attempt_001.log` (4,251 bytes).
- Manifest written: `experiments/performance/exp03_baseline_hard_neg/attempt_001_preservation_metadata.json`.
- Preservation status: `EXP03_ATTEMPT_001_EVIDENCE_PRESERVED = PASS`.

---

## 4. Code Repair, Regression Guard & Transaction Preflight

1. **Method Call Correction**:
   - `summary = meter.compute()` applied to `scripts/train_exp03.py:426`.
   - Grep verification confirmed zero occurrences of `meter.summary` remain across the entire repository.
2. **Regression Guard Added**:
   - Added `test_exp03_validation_metric_extraction_regression` to `tests/test_phase_5b_prelaunch_adversarial.py`.
   - Verified that `SegmentationMeter` update, compute, metric formatting, and checkpoint selection proceed without `AttributeError`.
3. **Mandatory Epoch Transaction Preflight Added**:
   - Added `test_exp03_epoch_transaction_preflight` to `tests/test_phase_5b_prelaunch_adversarial.py`.
   - Proved complete transaction traversal: Training step $\to$ Validation $\to$ Metric computation $\to$ Metric persistence $\to$ Atomic checkpoint serialization with load verification $\to$ Reload check.
   - Result: `EXP03_EPOCH_TRANSACTION_PREFLIGHT = PASS` (all 7 adversarial prelaunch tests passed).
4. **Transaction-Safe State Tracking**:
   - Updated `scripts/train_exp03.py` so that `completed_epochs` is only incremented after checkpoint serialization and independent load verification succeed.

---

## 5. Independent Verification Incident & Diagnostic

During post-training verification following Attempt 002 completion, a standalone evaluation script `scratch/independent_verify_exp03.py` was deployed.

### Incident Sequence & Root Cause (Observed Facts)
1. **Initial Stall**:
   - Process launched under task `task-4488`.
   - System observed PID 13996 (wrapper `venv Python`, CPU 0.015s, WorkingSet 4.45 MB) and PID 25360 (child `Python310`, CPU 6.50s, WorkingSet 1,028 MB).
   - Both processes stalled with zero CPU progress and zero GPU activity.
2. **Diagnostic Evidence**:
   - Preserved diagnostic: `experiments/performance/exp03_baseline_hard_neg/independent_verification_stall_diagnostic_001.json`.
   - Root Cause Analysis: The script instantiated `DataLoader(..., num_workers=4)` without an `if __name__ == '__main__':` guard. On Windows, PyTorch multi-worker DataLoader uses `multiprocessing.spawn`, which re-imports the module at top level, creating a recursive spawning deadlock and raising `RuntimeError: An attempt has been made to start a new process before the current process has finished its bootstrapping phase`.
3. **Termination**:
   - PID 25360 and PID 13996 were verified to point exclusively to `scratch/independent_verify_exp03.py` and were safely terminated with `Stop-Process -Force`.
   - No training processes, Antigravity IDE processes, or unrelated system processes were affected.
4. **Repair & Re-execution**:
   - Repaired `scratch/independent_verify_exp03.py` with `num_workers=0` (strictly single-process, no spawning), explicit `if __name__ == '__main__':` guard, and progress telemetry every 20 batches.
   - Executed under task `task-4507`. Completed in 1m 52s with exit code 0.
   - Full 2,880 validation tiles evaluated on GPU.
   - Recomputed metrics matched saved checkpoint metrics exactly to the last decimal place.
   - `EXP03_INDEPENDENT_METRIC_VERIFICATION = PASS`.

---

## 6. Attempt 002 Clean Rerun Execution & Progression

Attempt 002 was initialized fresh starting from Epoch 1, Batch 1 under task `task-4436`.

### Operational & Hyperparameter Configuration
- **Experiment ID**: `EXP-03_HARD_NEGATIVE_BASELINE` (Attempt: `EXP03_ATTEMPT_002`)
- **Start Time**: 2026-09-11T15:50:33Z
- **Completion Time**: 2026-09-11T17:17:48Z
- **Total Duration**: 5,232.5s (87m 12s)
- **Dataset**: Trujillo Part I TRAIN (13,440 tiles; 840 scenes $\times$ 16 tiles)
- **Mined Pool**: 400 frozen hard negatives from TRAIN split
- **Batch Architecture**: 16 tiles total (14 standard TRAIN tiles + 2 mined tiles; 12.5% hard negative exposure)
- **Epochs**: 10 (960 batches per epoch; 9,600 total batches)
- **Optimizer**: AdamW (Initial LR: `1e-4`, Weight Decay: `1e-2`)
- **Scheduler**: CosineAnnealingLR ($T_{\max}=10$, $\eta_{\min}=1\times 10^{-6}$)
- **Loss Function**: CombinedBCEAndDiceLoss (BCE: 0.5, Soft Dice: 0.5, smooth: 1.0)
- **Validation Dataset**: Trujillo Part I VAL (2,880 tiles; 180 scenes $\times$ 16 tiles; 180 batches of 16)
- **Evaluation Threshold**: 0.22 (canonical frozen threshold)
- **Hardware**: NVIDIA GeForce RTX 3050 6GB Laptop GPU (`Grimdawn`), CUDA 12.6, cuDNN 91002, AMP FP16 enabled.

### Full 10-Epoch Trajectory (Observed Facts)

| Epoch | Train Loss | LR | Val Loss | Val IoU | Val Dice | Val Precision | Val Recall | Clean-Water FAR (%) | Significant FAR (%) | Total FP Pixels | Duration (s) | Best Model? |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | 0.37701 | 9.76e-5 | 0.26427 | 0.68557 | 0.81346 | 0.87905 | 0.75698 | 6.02% | 2.74% | 124,463 | 542.8 | Yes |
| 2 | 0.25356 | 9.05e-5 | 0.13599 | 0.66044 | 0.79550 | 0.79570 | 0.79530 | 4.76% | 3.94% | 420,855 | 519.8 | No |
| 3 | 0.16892 | 7.96e-5 | 0.14729 | 0.60942 | 0.75731 | 0.88677 | 0.66084 | 1.64% | 0.88% | 124,101 | 523.3 | No |
| 4 | 0.14392 | 6.58e-5 | 0.09981 | 0.69868 | 0.82261 | 0.86425 | 0.78481 | 0.49% | 0.49% | 167,930 | 523.9 | Yes |
| 5 | 0.12420 | 5.05e-5 | 0.10377 | 0.68430 | 0.81256 | 0.87400 | 0.75920 | 0.49% | 0.49% | 147,844 | 518.5 | No |
| 6 | 0.11962 | 3.52e-5 | 0.10212 | 0.68430 | 0.81256 | 0.88401 | 0.75180 | 0.99% | 0.99% | 93,518 | 518.3 | No |
| 7 | 0.10810 | 2.14e-5 | 0.10159 | 0.67111 | 0.80319 | 0.86334 | 0.75088 | 0.55% | 0.55% | 165,461 | 517.9 | No |
| 8 | 0.10534 | 1.05e-5 | 0.11304 | 0.66168 | 0.79640 | 0.88226 | 0.72577 | 0.22% | 0.22% | 72,660 | 522.3 | No |
| **9** | **0.10077** | **3.42e-6** | **0.09007** | **0.70435** | **0.82653** | **0.88820** | **0.77287** | **0.33%** | **0.33%** | **79,742** | **519.1** | **YES (BEST)** |
| 10 | 0.09811 | 1.00e-6 | 0.09503 | 0.70190 | 0.82484 | 0.88483 | 0.77247 | 0.33% | 0.33% | 83,383 | 518.5 | No |

*Note on Loss Trajectory*: Training loss fluctuated across batches and ended lower than the initial observed batch loss (`B1: 0.4191` $\to$ `B960: 0.0233`). It did NOT progress strictly monotonically.

---

## 7. Comparative Performance & Pre-Registered Acceptance Gates

Comparison between EXP-01 Baseline (Teacher) and EXP-03 Hard-Negative Baseline (Best Checkpoint: Epoch 9):

| Metric | EXP-01 Baseline | EXP-03 (Epoch 9) | Delta ($\Delta$) | Pre-Registered Gate | Gate Status |
|:---|:---:|:---:|:---:|:---:|:---:|
| **Clean-Water FAR** | 20.09% | **0.33%** | **-19.76%** | $< 20.09\%$ | **PASS** |
| **Significant FAR ($\ge 100$ px)** | 10.56% | **0.33%** | **-10.23%** | $< 10.56\%$ | **PASS** |
| **Total Validation FP Pixels** | 2,327,942 | **79,742** | **-2,248,200** (-96.6%) | $< 2,327,942$ | **PASS** |
| **Validation Global IoU** | 0.71691 | **0.70435** | -0.01256 (-1.75%) | $\ge 0.71731$ | **FAIL** |
| **Validation Recall** | 0.78488 | **0.77287** | -0.01201 (-1.53%) | $\ge 0.80000$ | **FAIL** |
| **Validation Dice / F1** | 0.83512 | **0.82653** | -0.00859 (-1.03%) | N/A | N/A |
| **Validation Precision** | 0.89223 | **0.88820** | -0.00403 (-0.45%) | N/A | N/A |
| **Validation Loss** | 0.38564 | **0.09007** | -0.29557 | N/A | N/A |

### Epistemic Assessment of Results
- **OBSERVED FACT**: The primary objective of hard-negative mining—suppressing false alarms on clean sea water—was overwhelmingly achieved on the development validation set:
  - Clean-water false alarm rate dropped by **98.4% relatively** (from 20.09% to 0.33%).
  - Total false alarm pixel volume dropped by **96.6%** (from 2.33M pixels to under 80K pixels).
- **OBSERVED FACT**: Global IoU dropped slightly from 0.71691 to 0.70435 (-1.75% relative). Because the pre-registered non-inferiority threshold was set at $\ge 0.71731$, the gate was formally missed by 0.01296 IoU points.
- **OBSERVED FACT**: Recall dropped from 0.78488 to 0.77287. Because the pre-registered gate was $\ge 0.80000$, the recall gate was formally missed.
- **INFERENCE**: The slight reduction in IoU and recall is consistent with the model becoming more conservative in ambiguous oil-boundary regions as a direct trade-off for eliminating false alarms across large water expanses.
- **LIMITATION / UNVERIFIED**: These findings apply strictly to the canonical Trujillo Part I spatial validation split. Generalization to Trujillo Part III remains completely unverified and unmeasured, as Trujillo Part III was strictly isolated throughout this entire experiment.

---

## 8. Provenance, Integrity & Artifact Hashes

### Frozen Input Artifact Verification
Independent SHA-256 digests computed before, during, and after execution:
- **EXP-01 Teacher Checkpoint** (`experiments/exp01_baseline/best_model.pt`):  
  `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699` (292,465,299 bytes) — **MATCH / UNCHANGED**
- **Candidate Manifest** (`data/metadata/trujillo_2024/exp03_hard_negative_manifest.json`):  
  `3867671E639F020A686C5ACCA4FE5DA4280EB7DAEAB9BD9FEF467C192AA9F9F4` (261,621 bytes) — **MATCH / UNCHANGED**
- **Spatial Split Manifest** (`data/metadata/trujillo_2024/spatial_split_manifest.json`):  
  `C052720A954C2E7A3E9A87AA64557450BF0DEABEC71D54C2A813849DB60812E0` (5,748,446 bytes) — **MATCH / UNCHANGED**

### Generated EXP-03 Checkpoints
- **Best Model Checkpoint** (`experiments/performance/exp03_baseline_hard_neg/best_model.pt`):
  - Size: 292,463,187 bytes
  - SHA-256: `BE00C1C8B35A3648FCCAD3864F844ED2EB68E079F2CC390C1BA3EC147BF2DA57`
  - Associated Epoch: 9
  - Load Verification: Independently instantiated and strictly verified.
- **Final Model Checkpoint** (`experiments/performance/exp03_baseline_hard_neg/last_model.pt`):
  - Size: 292,463,315 bytes
  - SHA-256: `811B8C2B04696C8C3C7D30305DB64D926AAA6321B56BBE1B7ED07167CDB2B98A`
  - Associated Epoch: 10

---

## 9. Part III Firewall Assessment

- **`EXP03_PART_III_INPUT_REFERENCE_FIREWALL = PASS`**:
  All dataset manifests, mining manifests, scripts, and DataLoader pipelines were audited; zero Part III paths or identifiers were referenced.
- **`EXP03_NO_PART_III_ACCESS_OBSERVED = PASS`**:
  Continuous process monitoring during execution observed zero file reads or accesses targeting Part III directories.

---

## 10. Git Working Tree & Artifact Audit

A fresh post-execution audit was performed via `git status --porcelain -uall` and `git diff`:
- **Staged Files**: `0` (zero files staged; strict compliance with `no git add`).
- **Tracked Modified Files**: `2`
  - `.gitignore`: Narrowed artifact policy preventing large checkpoints from polluting normal status visibility.
  - `src/ocean_sentinel/ingestion/dataset.py`: Canonical ingestion dataset patch from earlier audit.
- **EXP-03 Output Directory Content**: `9 files`
  - `attempt_001_preservation_metadata.json` (Preserved Attempt 001 record)
  - `best_model.pt` (Authoritative EXP-03 best model checkpoint)
  - `failure.failed_attempt_001.log` (Preserved Attempt 001 log)
  - `history.json` (10-epoch per-epoch training & validation history)
  - `independent_validation_verification.json` (Standalone verification record)
  - `independent_verification_stall_diagnostic_001.json` (Diagnostic record for stall incident)
  - `last_model.pt` (Epoch 10 final checkpoint)
  - `metrics.json` (Final execution summary payload)
  - `run_state.failed_attempt_001.json` (Preserved Attempt 001 run state)
  - `run_state.json` (Final durable state: `status = COMPLETED`, `current_epoch = 10`)
- **Other Untracked Files**: Pre-existing canonical reports, manifests, tests, and scripts (`scripts/train_exp03.py`). Zero unexpected files were created.
- **Git State Assessment**: `AUDITED_NO_STAGING_EXPECTED_ARTIFACTS_ONLY`.

---

## 11. Final Declarations

```text
EXP03_ATTEMPT_001_STATUS = FAILED_DURING_EPOCH_1_VALIDATION_METRIC_EXTRACTION
EXP03_ATTEMPT_001_FAILURE_ROOT_CAUSE = AttributeError: 'SegmentationMeter' object has no attribute 'summary'
EXP03_ATTEMPT_001_CHECKPOINT_STATUS = NO_VALID_CHECKPOINT_EXISTED
EXP03_ATTEMPT_001_EVIDENCE_PRESERVED = PASS

EXP03_CODE_REPAIR = PASS
EXP03_VALIDATION_REGRESSION_TEST = PASS
EXP03_EPOCH_TRANSACTION_PREFLIGHT = PASS
EXP03_FRESH_RUN_INITIALIZATION = PASS

EXP03_TRAINING_STATUS = COMPLETED
EXP03_CURRENT_EPOCH = 10/10
EXP03_BEST_CHECKPOINT_STATUS = EPOCH_9_VERIFIED_AND_LOADABLE
EXP03_VALIDATION_STATUS = CANONICAL_PART_I_VALIDATED

EXP03_PARAMETER_COUNT = 24346305_TRAINABLE_19054_BUFFERS_24365359_TOTAL
EXP03_TEACHER_INTEGRITY = 100%_MATCH
EXP03_CANDIDATE_MANIFEST_INTEGRITY = 100%_MATCH
EXP03_SPATIAL_SPLIT_INTEGRITY = 100%_MATCH
EXP03_SAMPLING_INTEGRITY = PASS
EXP03_DATA_LEAKAGE_CONTROLS = PASS
EXP03_PART_III_INPUT_REFERENCE_FIREWALL = PASS
EXP03_NO_PART_III_ACCESS_OBSERVED = PASS
EXP03_ENVIRONMENT_INTEGRITY = PASS
EXP03_RESOURCE_SAFETY = PASS
EXP03_OBSERVABILITY = LIVE_HEARTBEAT_ACTIVE
EXP03_CHECKPOINT_INTEGRITY = PASS
EXP03_INDEPENDENT_VERIFICATION_STATUS = COMPLETED
EXP03_INDEPENDENT_METRIC_VERIFICATION = PASS
EXP03_GIT_AUDIT = AUDITED_NO_STAGING_EXPECTED_ARTIFACTS_ONLY
EXP03_ACCEPTANCE_STATUS = FAIL
EXP03_SCIENTIFIC_CLOSURE = READY_FOR_CAIO_REVIEW
```
