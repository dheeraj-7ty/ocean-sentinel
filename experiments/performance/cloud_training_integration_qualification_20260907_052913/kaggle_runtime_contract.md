# Ocean Sentinel — Kaggle Runtime Contract

**Runtime Target**: Kaggle GPU T4 x2 Compute Environment  
**Qualification Reference**: Gate 3.1 Live Capability Probe (`cloud_kaggle_t4x2_retrial_20260907_011421`)  
**Authority**: Ocean Sentinel Chief AI Officer (CAO)  

---

## 1. Cloud Infrastructure Baseline

| Hardware / Environment Layer | Qualified Specification | Live Measured State |
| :--- | :--- | :--- |
| **Operating System** | Linux 6.12.90+ (x86_64 glibc 2.35) | `Linux-6.12.90+-x86_64-with-glibc2.35` |
| **Python Environment** | Python 3.12.13 | `/usr/bin/python3` (Pre-installed in container) |
| **PyTorch Version** | 2.10.0+cu128 | CUDA 12.8, cuDNN 91002 |
| **Torchvision Version** | 0.25.0+cu128 | Pre-installed |
| **Rasterio / GDAL** | Rasterio 1.4.x / GDAL 3.x | Verified importable in standard Kaggle image |
| **Host CPU** | Intel Xeon / AMD EPYC | 4 logical vCPU cores |
| **Host System RAM** | 31.35 GB total | 29.63 GB free at session start |
| **Primary GPU (cuda:0)** | NVIDIA Tesla T4 | 14,911.69 MB total VRAM (14,804.81 MB free) |
| **Secondary GPU (cuda:1)**| NVIDIA Tesla T4 | 14,911.69 MB total VRAM (14,804.81 MB free) |
| **Compute Capability** | 7.5 (Turing Architecture) | Native FP16 Tensor Cores supported |

---

## 2. Storage & Filesystem Partitioning

### A. Input Dataset (`/kaggle/input/`)
- **Mount Point**: `/kaggle/input/ocean-sentinel-trujillo-corpus`
- **Filesystem Type**: Virtual FUSE Mount (Read-Only)
- **Total Corpus Size**: 56,193,499,563 bytes (52.33 GiB / 56.19 GB)
- **Local Disk Impact**: **0 GB consumed**. The virtual FUSE filesystem streams data directly from Google Cloud Storage backend without occupying the 20 GB scratch disk limit.
- **Directory Structure**:
  ```text
  /kaggle/input/ocean-sentinel-trujillo-corpus/
  ├── images/
  │   └── Oil/
  │       └── 00001.tif ... 01200.tif
  ├── masks/
  │   └── Mask_oil/
  │       └── 00001.tif ... 01200.tif
  └── metadata/
      ├── spatial_split_manifest.json
      └── trujillo_part1_audit_report.json
  ```

### B. Output & Working Scratch (`/kaggle/working/`)
- **Capacity**: 20 GB local scratch disk.
- **Usage Strategy**: Reserved strictly for training artifacts:
  - Checkpoints: `best_model.pt` (~93 MB), `latest_checkpoint.pt` (~93 MB)
  - Logs: `progress.log`, `history.json`, `run_state.json` (<5 MB)
  - Qualitative visual diagnostics (<10 MB)
  - Total scratch consumption per training run: **<250 MB** (well within 20 GB budget).

---

## 3. Session Lifecycle & Quota Budgeting

- **Weekly Allocation**: 30.0 hours GPU quota per rolling week.
- **Session Duration Limit**: 12.0 hours max execution time per interactive or batch notebook run.
- **Preflight Quota Impact**: 9-point preflight gate executes in ~7.2 seconds (0.002 GPU hours).
- **Target EXP01 Rev B Run**:
  - 30 epochs at measured 32+ samples/sec throughput: ~3.0 to 3.5 hours per full training run.
  - Leaves >26 hours of weekly GPU quota for ablations and qualification.

---

## 4. Kernel Configuration & Metadata Contract

The notebook push configuration must adhere to:

```json
{
  "id": "dheeraj12237/ocean-sentinel-exp01-training",
  "title": "ocean-sentinel-exp01-training",
  "code_file": "ocean-sentinel-exp01-training.ipynb",
  "language": "python",
  "kernel_type": "notebook",
  "is_private": true,
  "enable_gpu": true,
  "enable_tpu": false,
  "enable_internet": false,
  "dataset_sources": [
    "dheeraj12237/ocean-sentinel-trujillo-corpus"
  ]
}
```

- **Internet Access**: Set to `false` during training to ensure complete air-gapped reproducibility and guarantee zero external data leakage.
- **Privacy**: `is_private = true` (strict proprietary research isolation).

---

## 5. Failure & Preemption Handling

1. **Preemptible Instance Interruptions**:
   Kaggle GPU containers may be interrupted or recycled. The atomic writing of `latest_checkpoint.pt` ensures training can be resumed from the exact last completed epoch via `--resume /kaggle/working/experiments/exp01_baseline/latest_checkpoint.pt`.
2. **Heartbeat Monitoring**:
   Every completed epoch flushes `run_state.json` with an updated timestamp and metrics, allowing remote state recovery.
3. **Out-of-Memory (OOM) Protection**:
   Batch size 8 consumes ~2.2 GB VRAM on the Tesla T4, leaving >12 GB headroom. OOM risk is near zero under canonical settings.
