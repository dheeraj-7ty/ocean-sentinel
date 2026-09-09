# Repository Reconstruction & Authoritative State Context

**Document Status**: AUTHORITATIVE / AUDITED  
**Gate**: Gate 4 — Dataset Staging & Data-Loading Pipeline Qualification  
**Repository**: `D:\Projects\ocean-sentinel`  
**Date**: September 7, 2026  
**Auditor**: Implementation / Validation Worker  
**Authority**: Chief Architect Officer (CAO)  

---

## 1. Version Control & Working Tree State

- **Branch**: `master`
- **Git Commit HEAD**: `8f444de` (*"Phase 1C.2: Oil-spill dataset reconnaissance & selection strategy"*)
- **Working Tree Integrity**:
  - Cumulative project development artifacts (`experiments/`, `src/ocean_sentinel/ml/`, `src/ocean_sentinel/ingestion/`, `scripts/train_exp01.py`, `docs/adr/`, `data/metadata/trujillo_2024/`) remain intact.
  - Zero files were committed, reset, cleaned, or deleted.
  - Non-destructive execution policy strictly maintained.

---

## 2. Canonical Hardware & Performance Baselines

### 2.1 Local Authoritative Baseline (Dell G15 / RTX 3050 Laptop)
- **Baseline Metric**: **32.15 samples/sec** (audited in Step 2B under G-Mode enabled, batch size 8, accumulation 1, 4 DataLoader workers, pin_memory=True, AMP FP16).
- **GPU Specifications**:
  - NVIDIA GeForce RTX 3050 6GB Laptop GPU (GA107, Compute Capability 8.6).
  - VRAM: 6,144 MB total (allocation ceiling ~5.1 GB at B=8).
  - TGP: 95W.
- **CPU & Host RAM**:
  - 13th Gen Intel Core i7-13650HX (14 cores / 20 logical threads).
  - 15.69 GB RAM visible physical memory.
- **Local Tooling**:
  - Python: 3.10.9 (MSC v.1934 64 bit).
  - PyTorch: `2.14.0+cu126`, CUDA 12.6, cuDNN 91002.
  - Project venv: `D:\Projects\ocean-sentinel\venv`.

### 2.2 Kaggle Cloud Hardware Target (Dual Tesla T4)
- **Qualified Hardware (Gate 3.1)**:
  - 2x NVIDIA Tesla T4 (Turing TU104, Compute Capability 7.5).
  - VRAM: 14,911.69 MB (14.56 GiB) per GPU; 29.12 GiB total VRAM.
  - Host RAM: 31.35 GB total (29.63 GB free).
  - CPU: 4 vCPU cores (Intel Xeon / AMD EPYC virtualized).
- **Kaggle Software Environment**:
  - OS: Linux 6.12.90+ (Ubuntu 22.04 base).
  - Python: 3.12.13.
  - PyTorch: `2.10.0+cu128`, CUDA 12.8, cuDNN 91002.
  - Smoke checks: Allocation, FP16 Matmul, Conv2D, ResNet-34 U-Net instantiation (24,346,305 parameters) all PASSED.
- **Gate 3.1 Verdict**: **PASS** (dual T4 qualified for architecture sm_75).

---

## 3. Canonical Trujillo Part I Dataset Contract

- **Source Zenodo Archive**: DOI `10.5281/zenodo.8346860` (Trujillo-Acatitla et al., July 2024).
- **Archive Verification**:
  - `01_Train_Val_Oil_Spill_images.7z`: 40,712,942,245 bytes (MD5 `e2a6a5b473ca587474d8daee9cd54e10`).
  - `01_Train_Val_Oil_Spill_mask.7z`: 6,236,761 bytes.
- **Corpus Characteristics**:
  - Total parent scenes: 1,200 exact pairs (`00000` to `01339`).
  - Image geometry: 2048x2048 pixels, 2 bands, float32, LZW compressed.
  - Georeferencing: EPSG:4326, valid affine geotransform on all images.
  - Mask geometry: 2048x2048 pixels, 1 band, uint8, binary {0, 1}, uncompressed.
  - Radiometry: Native decibel ($\text{dB } \sigma^0$) pre-calibrated backscatter.
  - Polarization mapping: `UNKNOWN` (scientific policy prohibits guessing VV/VH assignment).
- **Spatial Partition Contract** (`spatial_split_manifest.json`):
  - Split strategy: Spatial connected component partition (seed 42, zero cross-split component leakage).
  - Composition:
    - Train: 840 parent scenes (70.0%) $\rightarrow$ 13,440 tiles of 512x512.
    - Validation: 180 parent scenes (15.0%) $\rightarrow$ 2,880 tiles of 512x512.
    - Test: 180 parent scenes (15.0%) $\rightarrow$ 2,880 tiles of 512x512.
    - Total: 1,200 parent scenes $\rightarrow$ 19,200 tiles of 512x512.
  - Normalization: Frozen `NormalizationStats` derived strictly from the training partition:
    - Channel 0: mean = -35.1245 dB, std = 6.2312 dB.
    - Channel 1: mean = -21.4589 dB, std = 5.8924 dB.
