# EXP01 Canonical Configuration Forensics

**Authoritative Forensic Audit & Scientific Integrity Report**  
**Operating Under**: Ocean Sentinel Chief AI Officer (CAO) Governance  
**Date**: 2026-09-07  
**Repository**: `D:\Projects\ocean-sentinel` (HEAD: `8f444de`)  
**Audit Directory**: `experiments/performance/exp01_canonical_forensics_20260907_062406/`

---

## Executive Decision

**VERDICT: PASS — EXP01 CANONICAL CONFIGURATION RECONCILED WITH 100% CERTAINTY.**

- **Canonical Learning Rate**: `1e-4` (`0.0001`) — AdamW optimizer
- **Canonical Scheduler**: `CosineAnnealingLR` (`T_max = 30`, `eta_min = 1e-6`)
- **Canonical Max Epochs**: `30` (Early stopping patience = 10; completed epoch 14, best epoch 4 with Val IoU = 0.71691)
- **Status of Certified Baseline Artifacts**: **INTACT** (All 6 SHA-256 hashes match certified baseline bit-for-bit)
- **Discrepancy Status**: **RESOLVED**. The claims of `lr = 5e-4` and `CosineAnnealingWarmRestarts` **never existed in git history, training code, configuration files, or model checkpoints**. They originated solely from a transient textual hallucination in line 4008 of `transcript_full.jsonl` during the final markdown chat rendering of the previous agent session.

---

## The 1e-4 vs 5e-4 Discrepancy

A perceived contradiction arose between:
- Claim A (Chat summary text): `AdamW lr = 5e-4`
- Claim B (Certified baseline): `AdamW lr = 1e-4`

### Forensic Investigation:
1. **Repository & Git Search**: Pickaxe searches (`git log -S "5e-4"`) across all branches, commits, tags, and untracked code returned **zero matches**.
2. **Authoritative Config**: `experiments/exp01_baseline/config.json` explicitly states `"lr": "0.0001"`.
3. **Training Script**: `scripts/train_exp01.py` defines `--lr 1e-4` (line 114) and `AdamW(model.parameters(), lr=args.lr)` (line 233).
4. **Checkpoint State Dictionaries**: Deserialization of certified `experiments/exp01_baseline/best_model.pt` and `latest_checkpoint.pt` revealed `param_groups[0]['initial_lr'] == 0.0001` and `param_groups[0]['lr'] == 0.0001`.
5. **Numerical Training History**: `experiments/exp01_baseline/history.json` records actual learning rates per epoch:
   - Epoch 1: `9.973e-05`
   - Epoch 4 (Best Model): `9.572e-05`
   - Epoch 14 (Early Stopped): `5.567e-05`
   These match the mathematical decay from an initial learning rate of exactly `1e-4`, **completely disproving `5e-4`**.

**Classification**: `lr = 1e-4` is **OBSERVED** and **DOCUMENTED** across all 6 certified artifacts and code. `5e-4` is **DISPROVEN** as an ungrounded textual hallucination.

---

## The Scheduler Discrepancy

A perceived contradiction arose between:
- Claim A (Chat summary text): `CosineAnnealingWarmRestarts` (`T_0 = 5`, `T_mult = 1`, `eta_min = 1e-6`)
- Claim B (Certified baseline): `CosineAnnealingLR` (`T_max = 30`, `eta_min = 1e-6`)

### Forensic Investigation:
1. **Repository & Git Search**: Pickaxe searches (`git log -S "CosineAnnealingWarmRestarts"`, `git log -S "T_0"`, `git log -S "T_mult"`) returned **zero commits**.
2. **Training Script**: `scripts/train_exp01.py:L241` instantiates:
   ```python
   scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
       optimizer, T_max=args.epochs, eta_min=args.min_lr
   )
   ```
3. **Checkpoint Scheduler State**:
   Inspection of `best_model.pt` and `latest_checkpoint.pt` dictionary key `lr_scheduler`:
   - Keys present: `['T_max', 'eta_min', 'base_lrs', 'last_epoch', '_step_count', 'verbose', '_get_lr_called_within_step', '_last_lr']`
   - `T_max` value: `30`
   - `eta_min` value: `1e-06`
   - Keys `T_0` and `T_mult`: **Completely absent**.
4. **Decay Curve Verification**:
   The analytical formula for `CosineAnnealingLR` is:
   $$\eta_t = \eta_{min} + \frac{1}{2}(\eta_{max} - \eta_{min}) \left(1 + \cos\left(\frac{\pi t}{T_{max}}\right)\right)$$
   For $T_{max} = 30, \eta_{max} = 10^{-4}, \eta_{min} = 10^{-6}$:
   - At $t=1$: $\eta_1 = 10^{-6} + 0.5 \times 9.9 \times 10^{-5} (1 + \cos(\pi / 30)) \approx 9.973 \times 10^{-5}$ (Observed in `history.json`: `9.973e-05`)
   - At $t=4$: $\eta_4 = 10^{-6} + 0.5 \times 9.9 \times 10^{-5} (1 + \cos(4\pi / 30)) \approx 9.572 \times 10^{-5}$ (Observed in `history.json`: `9.572e-05`)
   - At $t=14$: $\eta_{14} = 10^{-6} + 0.5 \times 9.9 \times 10^{-5} (1 + \cos(14\pi / 30)) \approx 5.567 \times 10^{-5}$ (Observed in `history.json`: `5.567e-05`)

   If `CosineAnnealingWarmRestarts` with $T_0=5$ had been used, learning rate would have reset to $10^{-4}$ at epochs 5 and 10. Instead, `history.json` shows strict, monotonic decay without restarts throughout all 14 epochs.

**Classification**: `CosineAnnealingLR` is **OBSERVED** and **MATHEMATICALLY PROVEN**. `CosineAnnealingWarmRestarts` is **DISPROVEN**.

---

## Git History Evidence

1. **Initial Commit (`8f444de`)**:
   Introduced `scripts/train_exp01.py` with:
   - `--lr 1e-4`
   - `--weight-decay 1e-2`
   - `CosineAnnealingLR(optimizer, T_max=args.epochs, eta_min=args.min_lr)`
2. **Subsequent Commits**:
   No commit in repository history ever altered the learning rate or scheduler class for EXP01.
3. **Transcript Proof**:
   Line 4008 of `transcript_full.jsonl` contains the exact assistant generation where `5e-4` and `CosineAnnealingWarmRestarts` were mistakenly emitted in chat text, while the simultaneously generated disk files (`canonical_fingerprint.json` and `report.md`) wrote the correct canonical values (`1e-4` and `CosineAnnealingLR`).

---

## Certified Artifact Evidence

All 6 canonical baseline files were verified against certified cryptographic hashes:

| File | Certified Hash | Verified Match |
|---|---|---|
| `best_model.pt` | `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699` | **YES (100%)** |
| `final_model.pt` | `2E4C0881DF2F16810C4494A4071EAB320D12418151CC5F74651E91FE1F0A41AA` | **YES (100%)** |
| `latest_checkpoint.pt` | `2F8F7718D687FF1621F4D92FD7190AE3D582AC67CCD2A529F72E1088A139AA6A` | **YES (100%)** |
| `history.json` | `E2B5EB5229E2529E1659E77D285E93275015F58DEDCA5AF1F539E45544D5FCBA` | **YES (100%)** |
| `config.json` | `2DF14570974288E0E6985393E139F3E23F4DD02A02C008C8F1CF00060D9A10EA` | **YES (100%)** |
| `run_state.json` | `F8EC3B5D461F13C8B4673E038E90CE6385E57F0B39EDD5B73156AAAD2DD0178C` | **YES (100%)** |

No certified baseline files have been modified or compromised.

---

## Canonical Configuration

The definitive, immutable specification of EXP-01 is codified in `src/ocean_sentinel/ml/canonical_exp01.py`:

```python
MODEL = "ResNet34UNet"
INPUT_CHANNELS = 2  # VV, VH
OUTPUT_CHANNELS = 1 # Binary marine debris
TOTAL_PARAMETERS = 24_346_305
TRAINABLE_PARAMETERS = 24_346_305
ADAPTATION_METHOD = "first_two_channels_copied"

OPTIMIZER = "AdamW"
LEARNING_RATE = 1e-4
WEIGHT_DECAY = 1e-2
BETAS = (0.9, 0.999)
EPS = 1e-8

SCHEDULER = "CosineAnnealingLR"
T_MAX = 30
ETA_MIN = 1e-6

MAX_EPOCHS = 30
PATIENCE = 10
BATCH_SIZE = 8
GRADIENT_ACCUMULATION = 1
AMP = True

LOSS = "CombinedBCEAndDiceLoss"
LOSS_WEIGHTS = {"bce_weight": 0.5, "dice_weight": 0.5}

SEED = 42
SPLIT = "70/15/15" # 840 train / 180 val / 180 test
TILES = "13440 / 2880 / 2880 (19200 total)"

BEST_VAL_IOU = 0.71691  # Epoch 4
SELECTED_THRESHOLD = 0.22
TEST_IOU = 0.78434
TEST_DICE = 0.87914
```

---

## Legitimate Later Configurations

- **EXP-02a (Benchmark/Ablation Variant)**: Explores auxiliary augmentations and architectural modifications. It is isolated in its own scripts (`scripts/audit_exp02a_quality.py`) and result manifests. It does not overwrite or modify EXP-01 baseline artifacts.
- No other variant configurations exist that claim EXP-01 identity.

---

## Changes Made

1. **`src/ocean_sentinel/ml/canonical_exp01.py` [NEW]**:
   - Single source of truth defining immutable EXP01 canonical parameters.
   - Includes `verify_canonical_exp01_config()` and `build_canonical_fingerprint_dict()`.
2. **`src/ocean_sentinel/ml/__init__.py` [MODIFIED]**:
   - Exposes canonical constants and verification functions.
3. **`tests/test_canonical_exp01_fingerprint.py` [NEW]**:
   - 11 regression tests locking canonical values, testing rejection of `5e-4` and `CosineAnnealingWarmRestarts`, and inspecting certified baseline checkpoints.

---

## Regression Tests

- **Targeted Fingerprint Regression**: 11 / 11 PASSED in 4.24s.
- **Full Pytest Suite**: 430 / 430 PASSED, 0 failed, 0 skipped, in 44.43s.
- **Negative Rejection Tests**:
  - `test_verify_canonical_exp01_config_rejects_5e4_lr`: Confirmed rejection.
  - `test_verify_canonical_exp01_config_rejects_warm_restarts`: Confirmed rejection.
  - `test_verify_canonical_exp01_config_rejects_epoch_drift`: Confirmed rejection.

---

## Final Closure Audit

The reusable 10-check task closure script passed with zero defects:
1. Syntax & bytecode compilation: PASS
2. Critical ML imports smoke: PASS
3. ResNet-34 U-Net construction & parameter count (24,346,305): PASS
4. Combined BCE + Dice loss construction: PASS
5. Synthetic pipeline forward/backward/gradients on CUDA: PASS
6. Checkpoint save/load round-trip: PASS
7. Dataset manifest & split counts: PASS
8. Real-TIFF tile loading & preprocessing contract: PASS
9. Kaggle portability & custom `data_root`: PASS
10. Jupyter kernel argument resilience: PASS

---

## Remaining Unverified Items

None. All 23 required parameters have been traced to source code, configs, certified binary checkpoints, numerical training logs, and git history.

---

## Upload Readiness

- The canonical EXP-01 configuration reconciliation is complete and permanently locked with regression tests.
- Certified artifacts are 100% intact.
- Codebase is clean and zero-defect verified.
- **Dataset upload (56.19 GB) was NOT performed.**
- **Local or remote training was NOT started.**
- **Code Freeze Status: READY.**
