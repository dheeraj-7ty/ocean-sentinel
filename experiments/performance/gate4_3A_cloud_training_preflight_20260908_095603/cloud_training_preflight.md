# Gate 4.3A — Cloud Training Preflight & Execution Plan

**Gate Reference**: `GATE_4.3A_REPOSITORY_HYGIENE_AND_CLOUD_PREFLIGHT`  
**Author**: Implementation Engineer under Ocean Sentinel CAO Governance  
**Timestamp**: `2026-09-08T10:04:30+05:30`  
**Execution Target**: Kaggle Cloud GPU Container (1x NVIDIA Tesla T4 16GB)  
**Scientific Contract**: EXP01 Rev B Baseline (`B=8`, `accum=1`, `CosineAnnealingLR`, `AdamW`, `Spatial Split`)  

---

## 1. Executive Summary

This document formalizes the cloud training execution plan for the Ocean Sentinel EXP01 baseline model on Kaggle Cloud GPU infrastructure. It verifies that the repository can produce a fully deterministic, self-contained, secret-free execution bundle capable of executing under CAO governance without any architectural or scientific drift.

---

## 2. Deterministic Bundle Specification

The cloud training bundle has been assembled and verified at:  
`experiments/performance/gate4_3A_cloud_training_preflight_20260908_095603/bundle/`

### 2.1 Bundle Component Inventory

| Component | Relative Path | Purpose | Hash / Size |
| :--- | :--- | :--- | :--- |
| **Kernel Metadata** | `kernel-metadata.json` | Kaggle API submission descriptor | 358 bytes |
| **Runner Script** | `train_runner.py` | Autonomous mount detection, staging, telemetry, invocation | 8,938 bytes |
| **Training Engine** | `scripts/train_exp01.py` | Production training runner with 9-point preflight gate | 68,625 bytes (`20440B0C...`) |
| **Source Library** | `src/ocean_sentinel/` | Complete ML, ingestion, processing, and error taxonomy | 26 Python modules |
| **Secret Audit** | Across all 29 files | Automated regex scan for keys, tokens, credentials | **PASS: 0 VIOLATIONS** |

The cryptographic inventory of all 29 bundle files is formally codified in `cloud_bundle_manifest.json`.

---

## 3. Dataset Mount Contract Verification

The Kaggle container mounts datasets under `/kaggle/input/`. The bundle design and runner have been verified against the exact production dataset mount structure created during Gate 4.2P:

### 3.1 Mount Path Contract
- **Primary Mount Point**:  
  `/kaggle/input/datasets/dheeraj12237/ocean-sentinel-trujillo-corpus`
- **Secondary (Direct Dataset Name) Mount Point**:  
  `/kaggle/input/ocean-sentinel-trujillo-corpus`
- **Manifest Location**:  
  `/kaggle/input/datasets/dheeraj12237/ocean-sentinel-trujillo-corpus/manifest/spatial_split_manifest.json`
- **Image Directory**:  
  `/kaggle/input/datasets/dheeraj12237/ocean-sentinel-trujillo-corpus/images/Oil/` (1,200 GeoTIFFs, `00001.tif` to `01200.tif`)
- **Mask Directory**:  
  `/kaggle/input/datasets/dheeraj12237/ocean-sentinel-trujillo-corpus/masks/Mask_oil/` (1,200 GeoTIFFs, `00001.tif` to `01200.tif`)

### 3.2 Dynamic Path Resolution
`train_runner.py` executes the following resolution sequence:
1. Checks if `/kaggle/input/datasets/dheeraj12237/ocean-sentinel-trujillo-corpus/images/Oil` exists.
2. Checks if `/kaggle/input/ocean-sentinel-trujillo-corpus/images/Oil` exists.
3. Performs a dynamic tree search under `/kaggle/input` for directory pairs containing both `images/Oil` and `masks/Mask_oil`.
4. Rebases all 19,200 tile paths dynamically via `TrujilloTileDataset(..., data_root=corpus_root)`.

This ensures seamless execution regardless of whether the dataset is mounted via standard UI or CLI submission.

---

## 4. Single-GPU Policy (Tesla T4)

Kaggle GPU instances typically allocate dual Tesla T4 GPUs (`cuda:0` and `cuda:1`). In accordance with strict CAO governance:

### 4.1 Strict Single-GPU Enforcement
- **Target Device**: `cuda:0` (Single NVIDIA Tesla T4 16GB).
- **No Distributed Data Parallel (DDP)**: DDP is explicitly prohibited. Multi-GPU gradient averaging would alter the gradient variance and optimizer dynamics.
- **Batch Size Invariance**: Physical batch size is locked to **8** (`B=8`, `accum=1`). This strictly preserves the exact BatchNorm activation statistics and running mean/variance estimates certified in EXP01 Rev B.

### 4.2 Hyperparameter & Scientific Invariance Lock
The following parameters are frozen and immutable:
- **Model**: `ResNet34UNet(in_channels=2, num_classes=1, adaptation_method='slice_variance_scaled')`
- **Input Representation**: **2-channel Sentinel-1 dual-polarization SAR input in dB (polarization ordering UNKNOWN)**
- **Loss Formulation**: `0.5 * BCEWithLogitsLoss + 0.5 * SoftDiceLoss(smooth=1.0)`
- **Optimizer**: `AdamW(lr=1e-4, weight_decay=1e-2, betas=(0.9, 0.999))`
- **Learning Rate Scheduler**: `CosineAnnealingLR(T_max=30, eta_min=1e-6)` without restarts
- **Augmentation**: Spatial-only (Random Horizontal Flip, Vertical Flip, 90-degree Rotation with $p=0.5$ on train split only; zero photometric alteration)
- **Evaluation Threshold**: Validation grid search over $[0.10, 0.90]$ with step $0.02$; single test evaluation on held-out test split at optimal validation threshold
- **Data Partition**: Spatial connected-component split (`spatial_split_manifest.json`: 13,440 train / 2,880 val / 2,880 test tiles)

---

## 5. Observability & Telemetry Architecture

Headless cloud jobs require clear, unbuffered observability. The bundle implements a multi-tiered telemetry contract:

### 5.1 Real-Time Telemetry Logs (`progress.log` and stdout)
- **ASCII-Safe Formatting**: Standard 7-bit ASCII text with ISO 8601 UTC timestamps: `YYYY-MM-DDTHH:MM:SSZ`.
- **Phase Markers**: Every major operational stage emits explicit markers:
  - `[PHASE_START: ENVIRONMENT_INSPECTION]` / `[PHASE_COMPLETE: ENVIRONMENT_INSPECTION]`
  - `[PHASE_START: DATASET_MOUNT_DETECTION]` / `[PHASE_COMPLETE: DATASET_MOUNT_DETECTION]`
  - `[PHASE_START: PRETRAINED_WEIGHT_STAGING]` / `[PHASE_COMPLETE: PRETRAINED_WEIGHT_STAGING]`
  - `[PHASE_START: PREFLIGHT_GATE]` / `[PHASE_COMPLETE: PREFLIGHT_GATE]`
  - `[PHASE_START: TRAINING_EPOCH_XX]` / `[PHASE_COMPLETE: TRAINING_EPOCH_XX]`
  - `[PHASE_START: VALIDATION_EPOCH_XX]` / `[PHASE_COMPLETE: VALIDATION_EPOCH_XX]`
  - `[PHASE_START: TEST_EVALUATION]` / `[PHASE_COMPLETE: TEST_EVALUATION]`
- **Throughput & ETA**: Every logging interval computes samples/second throughput and dynamic ETA based on rolling epoch duration.

### 5.2 Structured Telemetry (`run_state.json`)
The execution state is persisted atomically via temporary file replacement after every epoch and phase change:
```json
{
  "run_id": "a259f5be",
  "status": "RUNNING",
  "pid": 12345,
  "start_time_utc": "2026-09-08T04:33:35Z",
  "last_heartbeat_utc": "2026-09-08T05:12:10Z",
  "current_epoch": 12,
  "best_epoch": 9,
  "best_val_iou": 0.71691,
  "last_epoch_duration_sec": 384.2,
  "throughput_samp_per_sec": 34.9,
  "eta_remaining_min": 115.3,
  "peak_vram_allocated_mb": 2184.5,
  "disk_free_gb": 18.7
}
```

### 5.3 Resumability & Preemption Defense
- **Atomic Checkpointing**: Checkpoints are written to `.tmp.pt` and renamed to `latest_checkpoint.pt` and `best_model.pt` via `os.replace`, guaranteeing that interrupted writes never corrupt prior checkpoints.
- **Fingerprint Verification**: Upon resume (`--resume /kaggle/working/experiments/exp01_baseline/latest_checkpoint.pt`), the runner verifies that `manifest_sha256` and code fingerprints match the original run.
- **Run Lock**: `run.lock` records process ID and hostname, preventing concurrent duplicate jobs while enabling safe stale-lock recovery.

---

## 6. End-to-End Bundle Preflight Verification

The complete bundle was executed with `--preflight-only` on local GPU hardware:
1. Environment inspection: CUDA detected, RTX 3050 initialized.
2. Dataset mount detection: Successfully resolved local corpus and `spatial_split_manifest.json`.
3. Pretrained weights: Pre-cached weights recognized at `~/.cache/torch/hub/checkpoints/resnet34-b627a593.pth`.
4. 9-point preflight gate:
   - Check 1: Real batch loads: shape `[8, 2, 512, 512]` — **PASS**
   - Check 2: Forward pass: logits `[8, 1, 512, 512]` — **PASS**
   - Check 3: Loss computes and is finite (0.8702) — **PASS**
   - Check 4: Backward pass completes without errors — **PASS**
   - Check 5: AMP scaler functional (scale=65536.0) — **PASS**
   - Check 6: Gradients strictly finite (zero NaN/Inf) — **PASS**
   - Check 7: Optimizer step completes — **PASS**
   - Check 8: Validation pass: loss=0.8634, IoU=0.0398 — **PASS**
   - Check 9: Checkpoint atomic write + reload verified — **PASS**
5. Execution exited cleanly with code 0 in 4.0 seconds without launching full training.

The bundle is certified **READY FOR CLOUD STAGING**.
