# Ocean Sentinel — Repository Reconstruction & Canonical Baseline Audit

**Audit Date**: September 7, 2026 (00:51 UTC+5:30 / 19:21 UTC)  
**Audit Directory**: `experiments/performance/cloud_kaggle_environment_qualification_20260907_004849/`  
**Engineer**: Implementation / Research Worker  
**Authority**: Chief Architect Officer (CAO)  
**Classification**: GATE 2 AUDIT ARTIFACT  

---

## 1. Version Control State

### Git Metadata
- **Repository Root**: `D:\Projects\ocean-sentinel`
- **Current Branch**: `master`
- **Canonical Git Commit HEAD**: `8f444de`
- **Commit Message**: `"Phase 1C.2: Oil-spill dataset reconnaissance & selection strategy"`
- **Prior Commits**:
  - `8352da4`: Phase 1C.1: SAR preprocessing pipeline
  - `f05e1f1`: Phase 1B.3.2: Sentinel-1 imagery retrieval implementation
  - `5a8d87e`: Phase 1B.3.1: Sentinel-1 Process API request construction
  - `70d0da6`: Phase 1B.2: Sentinel-1 STAC discovery implementation

### Working Tree State (Dirty / Uncommitted)
The working tree contains cumulative, verified development artifacts from Phase 1C through Phase 2.4 and Step 2B performance auditing. In strict compliance with CAO constraints, zero modifications have been reset, cleaned, stashed, or overwritten.

- **Staged for commit**:
  - `data/metadata/yang_singha_2025/data_matrix.tab`
  - `scripts/download_datasets.py`
- **Unstaged modifications**:
  - `docs/sar-preprocessing.md`
  - `scripts/download_datasets.py`
  - `src/ocean_sentinel/errors.py`
  - `src/ocean_sentinel/processing/models.py`
  - `src/ocean_sentinel/processing/sar.py`
  - `tests/test_preprocessing.py`
- **Untracked canonical directories & files**:
  - `data/metadata/trujillo_2024/` (spatial split manifest, split audit, archive listing, dataset audit)
  - `docs/adr/` (ADR 002, 003, 004)
  - `docs/trujillo-dataset-contract.md`
  - `experiments/` (EXP-01 baseline artifacts, performance benchmarks)
  - `scripts/train_exp01.py`, `scripts/audit_spatial_leakage.py`, `scripts/benchmark_*.py`
  - `src/ocean_sentinel/ingestion/`
  - `src/ocean_sentinel/ml/`
  - `tests/test_exp01_eval.py`, `tests/test_spatial_split.py`, `tests/test_ml_components.py`

---

## 2. Canonical Experiment Files (EXP-01 Baseline)

The canonical source of truth for model architecture, training configuration, weights, and evaluation metrics is strictly preserved in `experiments/exp01_baseline/`:

1. **`experiments/exp01_baseline/config.json`**:
   - `manifest`: `data\metadata\trujillo_2024\spatial_split_manifest.json`
   - `epochs`: 30
   - `batch_size`: 8
   - `accum_steps`: 1
   - `lr`: 0.0001 (1e-4)
   - `weight_decay`: 0.01 (1e-2)
   - `eta_min`: 1e-06
   - `num_workers`: 4
   - `patience`: 10
   - `no_amp`: False (AMP CUDA FP16 active)
   - `execution_note`: "Rev B: physical_batch=8, accum=1, workers=4. BatchNorm runs on B=8 per step."

2. **`experiments/exp01_baseline/experiment_fingerprint.json`**:
   - Created: `2026-09-06T08:42:01Z`
   - Platform: `Windows-10-10.0.26200-SP0`
   - Hostname: `Grimdawn`
   - GPU: `NVIDIA GeForce RTX 3050 6GB Laptop GPU`
   - Python: `3.10.9`
   - PyTorch: `2.14.0+cu126`, CUDA `12.6`, cuDNN `91002`
   - Manifest SHA256: `C052720A954C2E7A3E9A87AA64557450BF0DEABEC71D54C2A813849DB60812E0`
   - Spatial Audit SHA256: `9F4AD5B3CD1771CD168F7172D2E4F9475271D10224016930694697AD591A6AAE`

3. **`experiments/exp01_baseline/exp01_results.json`**:
   - Status: `COMPLETED`
   - Checkpoint SHA256 (`best_model.pt`): `9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699`
   - Best Epoch: 4
   - Best Validation IoU: `0.71691`
   - Optimal Threshold: `0.22` (selected via validation grid search, step 0.02)
   - Validation IoU at 0.22: `0.72231`
   - Mean Training Throughput: `28.3 samples/sec` (training phase), `32.15 samples/sec` (benchmarked sustained forward/backward)

4. **Model Checkpoints**:
   - `experiments/exp01_baseline/best_model.pt` (292,465,299 bytes, SHA256: `9B8BD867DC...`)
   - `experiments/exp01_baseline/final_model.pt` (292,467,835 bytes)
   - `experiments/exp01_baseline/latest_checkpoint.pt` (292,472,299 bytes)

---

## 3. Training & Evaluation Entry Points

- **Primary Training & Evaluation Script**:
  - `scripts/train_exp01.py`
  - Supports `--manifest`, `--output_dir`, `--epochs`, `--batch_size`, `--accum_steps`, `--lr`, `--weight_decay`, `--num_workers`, `--patience`, `--no_amp`, `--eval_only`, `--checkpoint`.
  - Implements atomic checkpoint saving, atomic JSON writing, safe checkpoint loading (`safe_load_checkpoint`), preflight assertions, and post-training threshold optimization.

---

## 4. Architectural Decisions & Specifications (ADRs & Docs)

1. **`docs/trujillo-dataset-contract.md`**:
   - Verifies 1,200 GeoTIFF scenes (2048x2048, 2 bands float32 dB, EPSG:4326) and 1,200 binary masks (2048x2048, uint8 {0, 1}).
   - Extracted corpus: ~47.62 GB. Compressed archive: 40.71 GB (`01_Train_Val_Oil_Spill_images.7z`, MD5: `e2a6a5b473ca587474d8daee9cd54e10`).
   - Slicing contract: 16 non-overlapping tiles of 512x512 per scene.

2. **`docs/adr/003-ml-model-architecture-cuda-and-leakage-governance.md`**:
   - Architecture: ResNet34-UNet (24.35M parameters).
   - Pretrained weight adaptation: `slice_variance_scaled` ($W' = W[:, 0:2] \times \sqrt{3/2}$).
   - Loss: Combined BCE and SoftDice ($0.5 \times \text{BCE} + 0.5 \times \text{Dice}$).
   - Optimizer: AdamW (`lr=1e-4`, `weight_decay=1e-2`).
   - Precision: AMP CUDA FP16.

3. **`docs/adr/004-spatially-defensible-dataset-partition.md`**:
   - Spatial partition: 840 train scenes (13,440 tiles), 180 val scenes (2,880 tiles), 180 test scenes (2,880 tiles).
   - Split seed: 42. Buffer distance: 20 km between splits to guarantee zero spatial autocorrelation leakage.
   - Audit report: `data/metadata/trujillo_2024/spatial_split_audit.json`.

---

## 5. Environment & Hardware Specifications

### Local Development Environment
- **Python**: 3.10.9 (`D:\Projects\ocean-sentinel\venv\Scripts\python.exe`)
- **PyTorch**: 2.14.0+cu126
- **CUDA**: 12.6, cuDNN 91002
- **Host System**: Windows 11 Home (10.0.26200), Dell G15 5530
- **CPU**: 13th Gen Intel Core i7-13650HX (14 cores, 20 logical threads)
- **RAM**: 15.69 GB physical RAM
- **GPU**: NVIDIA GeForce RTX 3050 6GB Laptop GPU (GA107, 6144 MB VRAM, 95W TGP)
- **Sustained Real Throughput (Step 2B Baseline)**: `32.15 samples/sec` (LOCAL REFERENCE ONLY)

### Kaggle CLI Tooling Discovery
- **Local Virtual Environment**: `kaggle.exe` is installed at `D:\Projects\ocean-sentinel\venv\Scripts\kaggle.exe` (Version: `1.7.4.5`).
- **Global Path**: Not in system `PATH`.
- **Local Credentials**: `C:\Users\Dheeraj\.kaggle\kaggle.json` is absent; environment variables `KAGGLE_USERNAME` / `KAGGLE_KEY` are unset.
- **Local Authentication Status**: `NOT AUTHENTICATED` locally.
- **Platform Account Status (User Evidence)**: Active user account with 30.00h GPU quota remaining and 20.00h TPU quota remaining.

---

## 6. Exact Files Inspected as Evidence

| File Path | Evidence Extracted |
| :--- | :--- |
| `experiments/exp01_baseline/config.json` | Canonical hyperparameters, manifest path, batch size (8), accum (1), lr (1e-4) |
| `experiments/exp01_baseline/experiment_fingerprint.json` | Code SHA256 hashes, manifest SHA256, model spec, seed (42) |
| `experiments/exp01_baseline/exp01_results.json` | Parameter counts (24,346,305), Best Val IoU (0.71691), Best threshold (0.22) |
| `docs/trujillo-dataset-contract.md` | Trujillo Part I dataset size (47.62 GB), tile dimensions, 1,200 scene pairs |
| `docs/adr/003-ml-model-architecture-cuda-and-leakage-governance.md` | Model architecture, slice_variance_scaled derivation, loss formulation |
| `docs/adr/004-spatially-defensible-dataset-partition.md` | Spatial split partition 840/180/180, zero spatial leakage certification |
| `src/ocean_sentinel/ml/unet_resnet.py` | Implementation of ResNet34UNet, slice_variance_scaled weight adaptation |
| `src/ocean_sentinel/ml/losses.py` | Implementation of CombinedBCEAndDiceLoss (0.5 BCE + 0.5 Dice) |
| `scripts/train_exp01.py` | Training loop, optimizer, scheduler (CosineAnnealingLR without warmup), checkpoint loading |
| `experiments/performance/gpu_step2b_results_20260906_131544.json` | Step 2B local baseline throughput reference (32.15 samples/sec) |
