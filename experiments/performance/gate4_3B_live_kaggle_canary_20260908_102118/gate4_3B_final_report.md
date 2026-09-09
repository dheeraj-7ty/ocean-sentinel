# Gate 4.3B — Live Kaggle Canary — Final Evidence Report

**Gate:** 4.3B  
**Purpose:** Live Kaggle cloud infrastructure qualification canary  
**Verdict:** ✅ **PASS WITH WARNINGS**  
**Software/Model/Data Contract:** ✅ **PASS**  
**GPU Training Qualification:** ❌ **NOT QUALIFIED**  
**Regression Test Status:** ✅ **PASS**  
**Source Dataset Deployment:** ✅ **VERIFIED**  
**Full Local Test Suite:** ⚠️ **INCOMPLETE** (466 tests passed; stalled at heavy disk-I/O integration tests)  
**Report Frozen:** 2026-09-08T15:30 IST (2026-09-08T10:00 UTC)  

---

## 1. Executive Status

Gate 4.3B is **PASS WITH WARNINGS**.

- **Software / Model / Data Contract:** **PASS**  
  All 9 required canary contracts passed on live Kaggle infrastructure (`KernelWorkerStatus.COMPLETE`, kernel version 5).
  The runtime booted, mounted the 1,200 image + 1,200 mask production corpus, verified all 19,200 virtual tiles and canonical normalization stats, instantiated `TrujilloTileDataset`, loaded real GeoTIFF batches, loaded pretrained `ResNet34UNet` with exact canonical parameter count (24,346,305), verified `slice_variance_scaled` adaptation, executed forward pass smoke, and verified observability and credential safety.
- **GPU Training Qualification:** **NOT QUALIFIED**  
  Kaggle allocated a Tesla P100-PCIE-16GB (sm_60) GPU. The installed PyTorch CUDA build (`2.10.0+cu128`) requires sm_70+.
  Because CUDA was incompatible on sm_60, the canary model contract was verified on **CPU fallback**.
  **CPU fallback is acceptable for canary software contract verification, but strictly prohibited for production training.**
  Therefore, GPU training qualification remains **NOT QUALIFIED** until Gate 4.3C verifies a supported GPU (such as Tesla T4 / sm_75).
- **Training Guard:** No training step was executed (`training_step_executed=False`, `optimizer_steps=0`).

---

## 2. Kernel Identity & Cloud Metadata

| Field | Value |
|---|---|
| Kaggle Kernel Slug | `dheeraj12237/ocean-sentinel-gate-4-3b-live-canary` |
| Successful Version | **v5** |
| Kernel Status | `KernelWorkerStatus.COMPLETE` |
| Attached Dataset 1 | `dheeraj12237/ocean-sentinel-trujillo-corpus` (56 GB production corpus) |
| Attached Dataset 2 | `dheeraj12237/ocean-sentinel-src` (source code package) |
| Source Dataset Status | `ready` (Version 3, containing `PureWindowsPath` fix) |

---

## 3. Execution Timestamps (v5)

| Event | UTC Timestamp |
|---|---|
| Kernel v5 Push | 2026-09-08T09:16:51Z |
| Kernel v5 Boot | 2026-09-08T09:17:03Z |
| Kernel v5 Dataloader Pass | 2026-09-08T09:17:20Z |
| Kernel v5 Pretrained Download & Verification | 2026-09-08T09:17:30Z |
| Kernel v5 Model Forward Pass | 2026-09-08T09:17:31Z |
| Kernel v5 Completion | 2026-09-08T09:17:31Z |
| Worker Complete Status Polled | 2026-09-08T09:19:15Z |

---

## 4. Runtime Environment (Observed Facts)

| Field | Value |
|---|---|
| Hostname | `537e86bbbb27` |
| Platform | `Linux-6.12.90+-x86_64-with-glibc2.35` |
| Python Version | `3.12.13 (main, Mar 4 2026, 09:23:07) [GCC 11.4.0]` |
| PyTorch Version | `2.10.0+cu128` |
| Torchvision Version | `0.25.0+cu128` |
| CUDA Version | `12.8` |
| cuDNN Version | `91002` |
| GPU Count | 1 |
| GPU Model | `Tesla P100-PCIE-16GB` (17,059.5 MB) |
| GPU Compute Capability | sm_60 |
| Active Device | `cpu` (capability fallback triggered) |
| Is Kaggle | True |

> [!WARNING]
> The Kaggle runtime allocated a **Tesla P100 (sm_60)** instead of the intended Tesla T4 (sm_75).
> PyTorch 2.10+cu128 supports minimum sm_70. CUDA tensor operations on this device trigger `UserWarning: Tesla P100 with CUDA capability sm_60 is not compatible with the current PyTorch installation`.
> The canary safely diagnosed this and fell back to CPU for the diagnostic model contract smoke test.
> **CPU fallback is NOT acceptable for production training.**
> Gate 4.3C MUST preflight a compatible GPU (e.g., T4 sm_75) and abort before any training step if unsupported.

---

## 5. Dataset Mount Verification

| Check | Result | Evidence |
|---|---|---|
| Corpus Root | `/kaggle/input/ocean-sentinel-trujillo-corpus` | Present on filesystem |
| Spatial Split Manifest | `/kaggle/input/.../manifest/spatial_split_manifest.json` | Present, SHA256: `C052720A954C2E7A3E9A87AA64557450BF0DEABEC71D54C2A813849DB60812E0` |
| Images Directory | `/kaggle/input/.../images/Oil` | 1,200 TIFFs confirmed |
| Masks Directory | `/kaggle/input/.../masks/Mask_oil` | 1,200 TIFFs confirmed |
| Spot Checks | `00000.tif`, `00001.tif`, `00002.tif` | All present and readable |
| **CHECK dataset_mount** | **PASS** | Verified in canary v5 |

---

## 6. Source Package Deployment Verification Chain

We verified the complete deployment chain ensuring the fix reached the cloud runtime:

1. **Local Repository Source:**
   - File: `src/ocean_sentinel/ingestion/dataset.py`
   - Size: 12,242 bytes
   - Verification: Contains `from pathlib import Path, PureWindowsPath` and `PureWindowsPath(p.image_path).name`.
2. **Staged Package Directory:**
   - Directory: `experiments/performance/gate4_3B_live_kaggle_canary_20260908_102118/src_dataset_staging_v2`
   - Verification: `filecmp` confirmed 100% identity with `src/ocean_sentinel` (0 diffs).
3. **Kaggle Source Dataset:**
   - Dataset ID: `dheeraj12237/ocean-sentinel-src`
   - Status: `ready` (Version 3)
   - Kaggle File Entry: `ingestion/dataset.py` — Size: 12,242 bytes, Created: `2026-09-08 09:13:30.107000`.
4. **Kernel Attachment:**
   - `kernel-metadata.json` includes `"dheeraj12237/ocean-sentinel-src"` in `dataset_sources`.
5. **Live Runtime Consumption:**
   - Canary v5 detected flat extraction at `/kaggle/input/ocean-sentinel-src/`, established symlink `/kaggle/working/ocean_sentinel` -> `/kaggle/input/ocean-sentinel-src`, inserted `/kaggle/working` into `sys.path`.
   - `from ocean_sentinel.ingestion.dataset import TrujilloTileDataset` succeeded.
   - Initialized `TrujilloTileDataset` over 13,440 training tiles; successfully loaded 3/3 representative TIFFs and batched `[2, 2, 512, 512]` tensors without path errors.

---

## 7. DataLoader Contract Verification

| Field | Value |
|---|---|
| Dataset Class | `TrujilloTileDataset` |
| Split | `SplitName.TRAIN` |
| Data Root | `/kaggle/input/ocean-sentinel-trujillo-corpus` |
| Dataset Size | 13,440 virtual tiles |
| Batch Images Shape | `[2, 2, 512, 512]` (`torch.float32`) |
| Batch Masks Shape | `[2, 1, 512, 512]` (`torch.float32`) |
| Finite Values | `True` (both images and masks) |
| Representative TIFFs | 3/3 OK (`00001.tif`, `00002.tif`, `00003.tif`) |
| **CHECK dataloader_contract** | **PASS** |

---

## 8. Model Reconstruction & Pretrained Checkpoint

| Metric / Attribute | Observed Value | Expected Canonical Value | Status |
|---|---|---|---|
| Architecture | `ResNet34UNet` | `ResNet34UNet` | ✅ PASS |
| Input Channels | 2 | 2 | ✅ PASS |
| Output Channels | 1 (raw logits) | 1 (raw logits) | ✅ PASS |
| Trainable Parameters | 24,346,305 | 24,346,305 | ✅ PASS |
| Total Parameters | 24,346,305 | 24,346,305 | ✅ PASS |
| Adaptation Method | `slice_variance_scaled` | `slice_variance_scaled` | ✅ PASS |
| Pretrained Checkpoint | `resnet34-b627a593.pth` | `resnet34-b627a593.pth` | ✅ PASS |
| Checkpoint Size | 87,319,819 bytes | 87,319,819 bytes | ✅ PASS |
| Checkpoint SHA-256 | `B627A593BCBE140C234610266FE4F8AE95EA42FC881D091C9B6052E6B1D0590F` | `B627A593...` | ✅ PASS |
| Forward Pass Shape | `[1, 1, 512, 512]` | `[1, 1, 512, 512]` | ✅ PASS |
| Output Finite | True | True | ✅ PASS |
| Training Steps Executed | False | False | ✅ PASS |
| Optimizer Steps Executed | 0 | 0 | ✅ PASS |
| **CHECK model_contract** | **PASS** | — | ✅ PASS |
| **CHECK pretrained_weight** | **PASS** | — | ✅ PASS |

---

## 9. Normalization & Observability Contracts

| Contract | Field | Manifest / Observed | Canonical Reference | Status |
|---|---|---|---|---|
| Normalization | Channel Means | `[-33.233136989478695, -19.941215852796695]` | `[-33.233136989478695, -19.941215852796695]` | ✅ PASS |
| Normalization | Channel Stds | `[6.489985665955077, 4.531345684833188]` | `[6.489985665955077, 4.531345684833188]` | ✅ PASS |
| Observability | `run_state.json` | Valid JSON, atomic write verified | Schema compliant | ✅ PASS |
| Observability | `progress.log` | Valid ASCII log, chronological phases | Schema compliant | ✅ PASS |
| Security | Secret Env Vars | `KAGGLE_DATA_PROXY_TOKEN=SET`, etc. | No token values logged | ✅ PASS |
| Security | Bundle Audit | 0 secret violations | Scanned 33 files, 347,071 bytes | ✅ PASS |

---

## 10. Production Defect Fix & Mandatory Regression Test

### Root Cause
In canary v4, the spatial split manifest stored Windows-style paths:
`D:\Projects\ocean-sentinel\data\raw\trujillo_2024\images\Oil\00000.tif`
On Linux/POSIX runtimes (Kaggle), standard `pathlib.Path(p.image_path).name` treated backslash `\` as an ordinary character (not a separator), returning the entire Windows string.
This resulted in invalid paths:
`/kaggle/input/ocean-sentinel-trujillo-corpus/images/Oil/D:\Projects\...\00000.tif` -> `FileNotFoundError`.

### Production Fix
In `src/ocean_sentinel/ingestion/dataset.py`:
Replaced `Path(p.image_path).name` with `PureWindowsPath(p.image_path).name`.
`PureWindowsPath` guarantees correct Windows-separator parsing regardless of host OS.

### Permanent Automated Regression Test
Added test suite `TestCrossPlatformManifestPathResolution` in `tests/test_dataset_pipeline.py`:
1. `test_pure_windows_path_vs_posix_path_contrast`:
   Demonstrates that `PurePosixPath(win_path).name` fails on POSIX (returns full path), whereas `PureWindowsPath(win_path).name` evaluates to `"00000.tif"`.
2. `test_trujillo_tile_dataset_resolves_under_linux_posix_semantics`:
   Simulates Linux runtime via `monkeypatch.setattr(ds_mod, "Path", PurePosixPath)`. Exercises production `TrujilloTileDataset` with Windows-style paths, asserting that:
   `img_path == "/kaggle/input/ocean-sentinel-trujillo-corpus/images/Oil/00000.tif"`
   `mask_path == "/kaggle/input/ocean-sentinel-trujillo-corpus/masks/Mask_oil/00000.tif"`.
3. `test_production_manifest_paths_resolve_cleanly_if_manifest_present`:
   Loads the actual 1,200-patch manifest and asserts every single resolved path has leaf `<stem>.tif` with zero drive-letter or backslash contamination.

**Regression Test Outcome:** ✅ **3 passed in 2.09s** (`PASS`).

---

## 11. Test Suite Audit & Honest Classification

| Test Suite | Total | Passed | Status | Notes |
|---|---|---|---|---|
| `tests/test_dataset_pipeline.py` | 51 | 51 | ✅ PASS | All manifest, split, tile, loader & regression tests passed |
| `tests/test_canonical_exp01_fingerprint.py` | 11 | 11 | ✅ PASS | Locks hyperparameters, architecture, checkpoints |
| `tests/test_ml_components.py` | 32 | 32 | ✅ PASS | UNet, losses, metrics, threshold, augmentations |
| Core Unit Tests (`config`, `models`, `errors`, `auth`, `discovery`) | 128 | 128 | ✅ PASS | All fast unit tests passed |
| Harness & Preprocessing (`upload_harness`, `preprocessing`, `raster_env`) | 96 | 96 | ✅ PASS | Preflight, telemetry, radiometric, rasterio passed |
| Service & Eval (`imagery_request`, `imagery_service`, `dartis`, `exp01_eval`) | 121 | 121 | ✅ PASS | Imagery pipeline, evaluation lock, baseline artifacts |
| Ingestion Unit Tests (`test_trujillo_ingestion.py`) | 21 | 21 | ✅ PASS | Pairing, validation, tiling, lazy loading |
| Spatial Split Unit Tests (`test_spatial_split.py`) | 6 | 6 | ✅ PASS | Synthetic splitters, manifest counts, normalizations |
| **Total Targeted Tests Executed** | **466** | **466** | ✅ **PASS** | 100% pass rate across all unit & contract tests |
| **Full Local Test Suite** | 470 | — | ⚠️ **INCOMPLETE** | Stalls on heavy full-corpus disk-I/O tests (see audit below) |

### Stall Analysis (F10 / F27 Compliance)
The full suite stalls around `tests/test_spatial_split.py::TestRealSpatialSplitManifest::test_zero_cross_split_identical_geotransforms` and `test_zero_cross_split_spatial_intersection_against_raw_geotiffs`.
**Observed Evidence:**
- These two tests sequentially open all 1,200 large raw GeoTIFFs (54 GB total) using `rasterio.open` and execute 719,400 pairwise polygon intersection tests in Python.
- Process inspection confirmed process ID 32968 with ~580 MB WorkingSet actively reading TIFF tags.
- This is an expensive full-corpus disk-I/O integration test, not a deadlock or functional failure.
- In accordance with CAO rules, the full suite is honestly classified as **INCOMPLETE**, not passed.

---

## 12. Separation of Evidence Types

### OBSERVED FACTS
1. Kaggle kernel `dheeraj12237/ocean-sentinel-gate-4-3b-live-canary` version 5 completed with status `KernelWorkerStatus.COMPLETE`.
2. All 9 canary checks returned `PASS` in `canary_result.json`.
3. Parameter count is exactly 24,346,305; adaptation method is `slice_variance_scaled`.
4. ResNet-34 checkpoint SHA-256 matches certified `B627A593...`.
5. Batch shapes `[2, 2, 512, 512]` and `[2, 1, 512, 512]` were produced from real TIFFs.
6. Kaggle allocated a Tesla P100 (sm_60); PyTorch 2.10+cu128 issued compatibility warning; canary executed model forward pass on CPU.
7. Zero training steps or optimizer steps were executed.
8. Automated regression test `TestCrossPlatformManifestPathResolution` passed (3/3).
9. Source dataset `dheeraj12237/ocean-sentinel-src` version 3 has `ready` status with `dataset.py` matching local 12,242 bytes.

### INFERENCES
1. The P100 allocation was a transient Kaggle cloud scheduler assignment, as GPU type cannot be pinned via standard CLI flags.
2. Production training throughput cannot be estimated from the CPU forward pass and must be measured on a real T4.

### UNVERIFIED MECHANISMS
1. T4 hardware performance on Kaggle (throughput in samples/sec, GPU utilization, epoch wall-clock).
2. Resumability and checkpoint restoration on cloud infrastructure.
3. Multi-GPU / DDP operation (DDP is explicitly deferred and prohibited for Gate 4.3C).

---

## 13. Gate 4.3C Preflight Requirements (Next Step)

Gate 4.3C is **NOT** authorized to begin in this task. When authorized, its mandatory preflight requirements are:

1. **GPU Qualification Preflight:**
   - Detect GPU presence.
   - Verify compute capability >= 7.0 (sm_75 for Tesla T4).
   - Execute CUDA tensor smoke test.
   - Execute CUDA model forward & backward smoke test.
   - **Hard Rule:** If GPU is incompatible (e.g. P100 sm_60), `TRAINING_ALLOWED = False` and the runner must abort immediately. CPU fallback is strictly prohibited for production training.
2. **Execution Order:**
   - **4.3C-A:** Compatible GPU qualification (T4 sm_75).
   - **4.3C-B:** 1-epoch real T4 training pilot.
   - **4.3C-C:** Checkpoint / resume qualification.
   - **4.3C-D:** Measured throughput / performance qualification (samples/sec, wait time).
   - **4.3C-E:** Full canonical EXP01 T4 training.
3. **Single GPU Only:** DDP is prohibited.
4. **Resumability Verification:** Must exercise `--resume` and verify model, optimizer, scheduler, epoch, and dataset fingerprint restoration.

---

## 14. Final Verdict

**Gate 4.3B: PASS WITH WARNINGS**

- Software, data, and model contracts: **PASS**
- GPU training qualification: **NOT QUALIFIED** (P100 sm_60 CPU fallback)
- Regression test: **PASS**
- Source dataset deployment: **VERIFIED**
- Gate 4.3B Evidence: **FROZEN**
- Next Permitted Action: Standby for explicit authorization of Gate 4.3C.
