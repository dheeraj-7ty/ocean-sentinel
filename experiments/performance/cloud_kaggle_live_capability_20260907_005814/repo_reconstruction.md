# Gate 3 — Repository State Reconstruction & Canonical Source of Truth

**Timestamp**: 2026-09-06T19:29:14Z  
**Directory**: `experiments/performance/cloud_kaggle_live_capability_20260907_005814/`  
**Authority**: Ocean Sentinel Chief Architect Officer (CAO)  
**Worker**: Implementation / Validation Worker  

---

## 1. Version Control & Working Tree

- **Repository Root**: `D:\Projects\ocean-sentinel`
- **Current Branch**: `master`
- **HEAD Commit**: `8f444de1d0fb35d09912a9e6bf27cebde8125f0d`
- **Commit Message**: "Phase 1C.2: Oil-spill dataset reconnaissance & selection strategy"
- **Working Tree Status**:
  - Uncommitted staged/tracked files preserved:
    - `data/metadata/yang_singha_2025/data_matrix.tab`
    - `docs/sar-preprocessing.md`
    - `scripts/download_datasets.py`
    - `src/ocean_sentinel/errors.py`
    - `src/ocean_sentinel/processing/models.py`
    - `src/ocean_sentinel/processing/sar.py`
    - `tests/test_preprocessing.py`
  - Untracked project assets preserved:
    - `experiments/` (all performance audits and EXP-01 baseline)
    - `src/ocean_sentinel/ml/` (production model, loss, and metrics modules)
    - `scripts/train_exp01.py` (canonical training runner)
    - `docs/` and `tests/`
- **Rule Compliance**: Zero files reset, cleaned, committed, or deleted.

---

## 2. Canonical EXP-01 Architecture & Parameters (Repository-Confirmed)

Directly confirmed from disk (`src/ocean_sentinel/ml/unet_resnet.py`, `src/ocean_sentinel/ml/losses.py`, `scripts/train_exp01.py`, `experiments/exp01_baseline/config.json`):

| Property | Canonical Specification | Confirmation Source |
| :--- | :--- | :--- |
| **Model Architecture** | `ResNet34UNet` | `src/ocean_sentinel/ml/unet_resnet.py:154` |
| **Parameter Count** | Exactly 24,346,305 parameters (all trainable) | Empirically verified via `sum(p.numel() for p in model.parameters())` |
| **Input Contract** | 2-channel SAR (VV, VH) in dB, `[B, 2, 512, 512]`, float32 | `unet_resnet.py:259` |
| **First-Layer Adaptation** | `slice_variance_scaled` ($W' = W[:, 0:2] \times \sqrt{3/2}$) | `unet_resnet.py:105` |
| **Output Contract** | Single raw logit channel, `[B, 1, 512, 512]`, float32 | `unet_resnet.py:253` |
| **Loss Function** | `CombinedBCEAndDiceLoss` ($0.5 \times \text{BCE} + 0.5 \times \text{SoftDice}$, smooth=1.0) | `src/ocean_sentinel/ml/losses.py:112` |
| **Optimizer** | AdamW (`lr=1e-4`, `weight_decay=1e-2`, `eps=1e-8`) | `scripts/train_exp01.py:1225` |
| **Learning Rate Scheduler** | Canonical pure `CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-6)` without warmup | `scripts/train_exp01.py:1232` |
| **Mixed Precision** | CUDA AMP FP16 (`torch.amp.autocast(device_type='cuda', dtype=torch.float16)`) | `scripts/train_exp01.py` |
| **Canonical Max Epochs** | 30 epochs (early stopping patience = 10) | `experiments/exp01_baseline/config.json` |
| **Spatial Split** | 840 train scenes / 180 val scenes / 180 test scenes | `data/metadata/trujillo_2024/spatial_split_manifest.json` |
| **Tile Count** | 13,440 train tiles / 2,880 val tiles / 2,880 test tiles | `data/metadata/trujillo_2024/spatial_split_manifest.json` |
| **Batch Configuration** | Physical batch size = 8, accumulation steps = 1 | `experiments/exp01_baseline/config.json` |

---

## 3. Local Machine & Baseline Reference

- **Host**: Dell G15 5530 (Intel Core i7-13650HX, 14 cores / 20 threads, 16 GB RAM)
- **Local GPU**: NVIDIA GeForce RTX 3050 6GB Laptop GPU (GA107, CC 8.6, 6144 MB VRAM, 95W TGP)
- **Local Python**: Python 3.10.9 (venv)
- **Local PyTorch**: `2.14.0+cu126`, CUDA `12.6`, cuDNN `91002`
- **Audited Step 2B Local Throughput**: `32.15 samples/sec` (sustained training throughput)
- **Role of Local Throughput**: Reference metric for future comparisons only; NOT to be benchmarked against in Gate 3.

---

## 4. Gate 2 Qualification Summary

- **Audit Directory**: `experiments/performance/cloud_kaggle_environment_qualification_20260907_004849/`
- **Decision**: CONDITIONAL PASS
- **Core Findings**:
  - Ephemeral scratch disk (`/kaggle/working`) capped at 20.0 GB; cannot unpack the 47.62 GB Trujillo `.7z` corpus.
  - Attached datasets (`/kaggle/input`) support up to 100 GB via FUSE network mount.
  - Weekly GPU quota: 30.0 hours.
  - Interactive/headless session limits: 12.0 hours.
  - Capability probe created and verified locally (`capability_probe.py`).
  - Condition for Gate 3: Live execution of the non-destructive capability probe on a remote Kaggle GPU runtime.
