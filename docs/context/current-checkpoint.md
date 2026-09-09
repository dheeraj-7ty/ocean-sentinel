# Ocean Sentinel — Current Project Checkpoint

**Document Version**: 5.0.0  
**Status**: ACTIVE / CANONICAL STATUS  
**Date**: September 2026  
**Repository**: `D:\Projects\ocean-sentinel`  
**Primary Sources**: Repository files, test execution, git status, CAO directives  
**Updated by**: Phase 2.4 Spatially Defensible Dataset Partition (CAO Architectural Authority)

---

## 1. Verified Project Phases

The Ocean Sentinel project has formally completed:

1. **Phase 1A**: Project Foundation & Architecture Blueprint `[VERIFIED]`
2. **Phase 1B.1**: Copernicus OAuth2 Authentication `[VERIFIED]`
3. **Phase 1B.2**: Sentinel-1 STAC Discovery `[VERIFIED]`
4. **Phase 1B.3.1**: Process API Request Construction `[VERIFIED]`
5. **Phase 1B.3.2**: Sentinel-1 Imagery Retrieval & GeoTIFF Handling `[VERIFIED]`
6. **Phase 1C.1**: SAR Preprocessing & Scientific Pipeline `[VERIFIED]`
7. **Phase 1C.2 Initial Acquisition**: Ingestion of DARTIS metadata & Trujillo Part I masks `[VERIFIED]`
8. **Phase 1C.2 Discovery Cross-Validation**: 40-scene DARTIS → CDSE STAC validation `[VERIFIED]`
9. **Integration Readiness Audit**: Lineage, radiometric safety, and leakage prevention audit `[VERIFIED]`
10. **Phase 1C.3 Preprocessor Radiometric-Unit Generalization**: Explicit `BackscatterUnit` (`LINEAR` vs `DECIBEL`), non-positive linear rejection, negative dB validity, opt-in linear derivation, unit-correct floor/threshold semantics `[VERIFIED]`
11. **Phase 1C.4A Offline Ingestion & Deterministic Tiling Specification**: `DatasetPatchProvenance`, `TileProvenance`, `TrujilloDatasetLoader`, deterministic 2048×2048 → 512×512 non-overlapping tiling, zero-leakage patch-stem grouping, bounded memory residency `[VERIFIED]`
12. **Phase 2.0 Trujillo Part I Data Acquisition, Archive Verification & Extraction**: Downloaded 40.71 GB archive (40,712,942,245 bytes), MD5 `e2a6a5b473ca587474d8daee9cd54e10` verified, full extraction of 1,200 GeoTIFF images to `data/raw/trujillo_2024/images/Oil/`, 1:1 exact stem pairing (1,200 / 1,200), zero orphans, `EPSG:4326` CRS confirmed, dB radiometry confirmed, channel mapping scientifically designated as `UNKNOWN` `[VERIFIED]`
13. **Phase 2.1 Dataset Preparation & PyTorch Data Pipeline** `[VERIFIED]`:
    - Deterministic 70/15/15 parent-patch group split (seed=42)
    - 840 train / 180 val / 180 test patches
    - 13,440 / 2,880 / 2,880 tiles (16 tiles per 2048×2048 patch, stride 512)
    - Persistent JSON manifest: `data/metadata/trujillo_2024/split_manifest.json`
    - Full 840-patch training normalization statistics persisted
14. **Phase 2.3 Model Implementation, CUDA Remediation & EXP-00 Microbenchmark** `[VERIFIED]`:
    - Spatial & Scene-Level Leakage Audit executed across all 1,200 patches (`data/metadata/trujillo_2024/spatial_leakage_report.json`)
    - CUDA-capable PyTorch environment installed (`torch==2.14.0+cu126`, `torchvision==0.29.0+cu126`, CUDA 12.6, cuDNN 9.1.0 on NVIDIA RTX 3050 6GB Laptop GPU)
    - Primary U-Net with ResNet-34 encoder implemented (`24,346,305` parameters), returning unscaled logits `[B, 1, 512, 512]`
    - Mathematically justified variance-scaled 2-channel adaptation ($W' = W_{[:, 0:2]} \cdot \sqrt{3/2}$)
    - Baseline loss: $0.5 \cdot \text{BCEWithLogits} + 0.5 \cdot \text{SoftDice}$ with Laplace smoothing (`smooth=1.0`)
    - Focal Tversky loss ($\alpha=0.3, \beta=0.7, \gamma=4/3$) implemented for EXP-02
    - Streaming segmentation metrics (Global IoU, Dice, Precision, Recall) with explicit empty-mask conventions
    - Validation-only threshold optimization utility (`optimize_threshold_on_validation`)
    - Discrete geometric SAR augmentations (HFlip, VFlip, discrete 90° rotations) with zero interpolation artifacts
    - EXP-00 GPU microbenchmark completed on hardware: batch size sweep, AMP FP16 feasibility, gradient accumulation, real DataLoader throughput (25.59 samples/s), real training step throughput (29.86 samples/s, 7.5 min/epoch)
    - 395 unit tests passing; Ruff clean on ML and test code
15. **Phase 2.4 Spatially Defensible Dataset Partition** `[VERIFIED]`:
    - Full spatial audit revealed 4,496 cross-split overlapping parent pairs in legacy random split
    - Implemented `SpatialGroupSplitter` grouping exact bounding box footprints into 204 connected spatial components
    - Deterministic capacity-aware bin-packing achieves **exactly 840 train (70.0%), 180 val (15.0%), 180 test (15.0%)** parent patches, and **13,440 / 2,880 / 2,880 tiles**
    - **100% elimination of spatial leakage**: 0 positive-area overlaps, 0 overlaps $\ge 10\%$, 0 overlaps $\ge 50\%$, 0 identical geotransforms crossing splits
    - Certified separation: Val-to-Train minimum distance $18.39\text{ km}$ ($0 < 5\text{ km}$); Test-to-Train minimum distance $14.97\text{ km}$ ($0 < 5\text{ km}$)
    - Recomputed training-only normalization statistics on all 840 train patches ($3,523,215,360$ valid pixels): Ch0 mean = -33.2331 dB, std = 6.4900 dB; Ch1 mean = -19.9412 dB, std = 4.5313 dB
    - Legacy `split_manifest.json` preserved untouched; new spatial split persisted to `spatial_split_manifest.json` and certified via independent audit `spatial_split_audit.json`
    - 405 unit tests passing (10/10 spatial tests); Ruff clean across all Phase 2.4 code

---

## 2. Test Suite Baseline `[VERIFIED — Phase 2.4 Implementation]`

* **Execution Command**: `& .\venv\Scripts\pytest -q`
* **Status**: **405 passed, 0 failed, 77 warnings in ~38.9s**
* **Test Coverage**:
  - `tests/test_auth.py`: 37 passed
  - `tests/test_config.py`: 11 passed
  - `tests/test_dartis_cross_validation.py`: 6 passed
  - `tests/test_dataset_pipeline.py`: 48 passed
  - `tests/test_discovery.py`: 37 passed
  - `tests/test_errors.py`: 20 passed
  - `tests/test_imagery_request.py`: 69 passed
  - `tests/test_imagery_service.py`: 32 passed
  - `tests/test_ml_components.py`: 32 passed
  - `tests/test_models.py`: 23 passed
  - `tests/test_preprocessing.py`: 49 passed
  - `tests/test_raster_env.py`: 7 passed
  - `tests/test_spatial_split.py`: **10 passed** (Phase 2.4 synthetic graph, non-overlapping, deterministic partition, manifest counts, tile inheritance, normalization stats, independent GeoTIFF overlap, identical geotransforms, audit report certification, loader integration)
  - `tests/test_trujillo_ingestion.py`: 23 passed

---

## 3. Dataset State `[VERIFIED]`

### Trujillo Part I (Primary Training Dataset)

| Property | Value |
|---|---|
| Zenodo record | 8346860 |
| Archive | `01_Train_Val_Oil_Spill_images.7z` |
| Archive size | 40,712,942,245 bytes |
| MD5 | `e2a6a5b473ca587474d8daee9cd54e10` |
| Extracted images | 1,200 |
| Image path | `data/raw/trujillo_2024/images/Oil/` |
| Masks | 1,200 |
| Mask path | `data/raw/trujillo_2024/masks/Mask_oil/` |
| Exact pairing | 1,200 / 1,200 (100%) |
| Orphan images | 0 |
| Orphan masks | 0 |
| Image dimensions | 2048 × 2048 |
| Bands | 2 |
| dtype | float32 |
| CRS | EPSG:4326 |
| Radiometry | dB (sigma-0, pre-calibrated) |
| Finite pixels | 100% |
| Polarization | UNKNOWN (no authoritative mapping) |
| Parent Sentinel-1 IDs | UNKNOWN |
| Acquisition timestamps | UNKNOWN |

### Phase 2.1 Split

| Property | Value |
|---|---|
| Split manifest | `data/metadata/trujillo_2024/split_manifest.json` |
| Split strategy | deterministic_sorted_group_shuffle |
| Seed | 42 |
| TRAIN patches | 840 |
| VAL patches | 180 |
| TEST patches | 180 |
| TRAIN tiles | 13,440 |
| VAL tiles | 2,880 |
| TEST tiles | 2,880 |
| Total tiles | 19,200 |
| Tile size | 512 × 512 |
| Stride | 512 (non-overlapping) |
| Tiles per patch | 16 |
| Group leakage | 0 (all groups disjoint) |

### Normalization Statistics (Final — All 840 Training Patches)

| Property | Value |
|---|---|
| Method | Chan et al. (1979) vectorized parallel Welford |
| Source | TRAIN split only (840 patches) |
| n_valid_pixels | 3,523,215,360 per channel (840 × 2048 × 2048) |
| channel_0 mean | see `split_manifest.json` |
| channel_0 std | see `split_manifest.json` |
| channel_1 mean | see `split_manifest.json` |
| channel_1 std | see `split_manifest.json` |
| Invalid pixels | 0 (100% finite confirmed) |

> **Note**: The manifest generated with `--max-norm-patches 30` (125,829,120 pixels) was
> replaced during Phase 2.1 remediation with full 840-patch statistics (3,523,215,360 pixels).

---

## 4. Current Working Tree State `[VERIFIED]`

* **Git Branch**: `master`
* **Baseline Commit**: `8f444de` (*"Phase 1C.2: Oil-spill dataset reconnaissance & selection strategy"*)

### Staged (pre-existing from earlier phases, not yet committed):
- `data/metadata/yang_singha_2025/data_matrix.tab` (DARTIS metadata)
- `scripts/download_datasets.py` (Phase 2.0 download script, modified)

### Modified (tracked, not staged — Phase 1C.3/1C.4A/Phase 2.1 work):
- `docs/sar-preprocessing.md`
- `src/ocean_sentinel/errors.py`
- `src/ocean_sentinel/processing/models.py`
- `src/ocean_sentinel/processing/sar.py`
- `tests/test_preprocessing.py`

### Untracked (work from Phase 1C.2 through Phase 2.4):
- `data/metadata/trujillo_2024/` (split_manifest.json, spatial_split_manifest.json, dataset_audit_report.json, spatial_leakage_report.json, spatial_split_audit.json, exp00_benchmark_results.json)
- `data/metadata/yang_singha_2025/cdse_validation_report.json`
- `docs/adr/002-radiometric-unit-generalization.md`
- `docs/adr/003-ml-model-architecture-cuda-and-leakage-governance.md`
- `docs/adr/004-spatially-defensible-dataset-partition.md`
- `docs/context/` (current-checkpoint.md, dataset-state.md)
- `docs/dartis-cdse-cross-validation.md`
- `docs/dataset-ingestion-readiness.md`
- `docs/trujillo-dataset-contract.md`
- `scripts/audit_spatial_leakage.py`
- `scripts/audit_trujillo_dataset.py`
- `scripts/benchmark_exp00.py`
- `scripts/generate_spatial_split_manifest.py`
- `scripts/generate_split_manifest.py`
- `scripts/verify_dartis_cdse.py`
- `src/ocean_sentinel/ingestion/` (all Phase 1C.4A / Phase 2.1 / Phase 2.4 code)
- `src/ocean_sentinel/ml/` (all Phase 2.3 model, loss, metric, threshold, and augmentation code)
- `tests/test_dartis_cross_validation.py`
- `tests/test_dataset_pipeline.py`
- `tests/test_ml_components.py`
- `tests/test_spatial_split.py`
- `tests/test_trujillo_ingestion.py`

### Removed during Phase 2.1 remediation (confirmed archive archaeology):
- `data/archive_filenames.json` (7-zip internal filename table, corrupted unicode)
- `data/decompressed_header.bin` (raw binary header from archive format investigation)
- `data/header_chunk.bin` (raw binary header from archive format investigation)

> Note: No commits have been created. All changes exist in the working tree only.

---

## 5. Remaining Scientific Unknowns

| Unknown | Status | Resolution Path |
|---|---|---|
| Polarization mapping (VV/VH) | UNKNOWN | Contact Trujillo et al. authors or acquire official metadata from Zenodo |
| Parent Sentinel-1 product IDs | UNKNOWN | Not provided in Part I archive; TIFF headers contain no product tags |
| Acquisition timestamps per patch | UNKNOWN | Same as above |
| Spatial patch overlap across splits | **RESOLVED & ELIMINATED** (0 cross-split overlaps) | Phase 2.4 `spatial_split_manifest.json` certified leakage-free |
| Oil fraction heterogeneity across splits | Not quantified | Pixel-level analysis deferred |

---

## 6. Immediate Next Tasks (Pending CAO Review & Direction)

1. **Phase 2.4 CAO Review & Decision** `[IN PROGRESS]`:
   - Spatially defensible partition generated, certified, and audited.
   - 405/405 tests passing, Ruff clean.
   - CAO decision required: **FORMAL ACCEPTANCE & AUTHORIZATION FOR EXP-01**.

2. **EXP-01 — Baseline Model Training** `[AWAITING CAO AUTHORIZATION]`:
   - 2-channel ResNet-34 U-Net, BCE+Dice loss, cosine annealing, AdamW (lr=1e-4), AMP FP16.
   - Safe batch configuration: physical batch 4, gradient accumulation 2 (effective batch 8).
   - Trained on canonical `spatial_split_manifest.json` (840 train, 180 val, 180 test).

3. **Trujillo Part II (Look-Alikes)** `[DEFERRED]`:
   - Hard negatives; beneficial for reducing false positive rate; requires separate CAO authorization.

4. **Trujillo Part III (Independent Test Set)** `[DEFERRED]`:
   - Held-out evaluation benchmark; deferred pending Part I training completion.