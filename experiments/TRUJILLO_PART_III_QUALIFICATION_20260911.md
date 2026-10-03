# Phase 4B-3 Scientific Dataset Qualification Report: Trujillo Part III

**Document Date:** 2026-09-11  
**Authority:** Chief AI Officer (CAO) Mandate — Phase 4B-3  
**Operating Agent:** Ocean Sentinel Implementation & Scientific-Ingestion Agent  
**Baseline Git HEAD:** `542bab19f6f08c9bba8b8762e6480386c8b6026b`  
**Active Branch:** `master`  
**Dataset Identifier:** Zenodo Record `13761290` (DOI `10.5281/zenodo.13761290`)  
**Canonical Source Archive:** `data/raw/external_validation/trujillo_part_iii/02_Test_images_and_ground_truth.7z`  
**Canonical Extracted Path:** `data/raw/external_validation/trujillo_part_iii/extracted/`  
**Final Qualification Verdict:** **`SCIENTIFIC_QUALIFICATION_CONDITIONAL`**  

---

## Executive Summary

Phase 4B-3 evaluated the physically extracted Trujillo Part III dataset across 8 comprehensive scientific gates (4B-3A through 4B-3H).

The dataset is qualified as **`SCIENTIFIC_QUALIFICATION_CONDITIONAL`**.

### Summary of Empirical Findings:
1. **Physical Inventory (Gate 4B-3A)**: All 900 files (450 images and 450 masks) exist, are readable GeoTIFF containers, have dimensions of exactly `2048 x 2048`, and contain zero NaNs or Infinities.
2. **Pairing (Gate 4B-3B)**: Exactly 450 / 450 image/mask pairs were established under strict stem equivalence (`Images/<class>/<stem>.tif` <-> `Mask/<class>/<stem>_segmentation.tif`).
3. **Mask Semantics (Gate 4B-3C)**: Masks are binary {0, 1}. All 150 masks in `Oil` have non-zero foreground pixels (`62,501,987` total pixels). All 150 masks in `No oil` and all 150 masks in `Lookalike` are 100% zero-background masks.
4. **Image Value Semantics (Gate 4B-3D)**: Image pixel values are 32-bit floating point numbers in the decibel domain (Band 1 mean ~ -31.45 dB, Band 2 mean ~ -21.74 dB). No metadata tags document polarization order; physical polarization remains **UNVERIFIED**.
5. **Geospatial (Gate 4B-3E)**: Asymmetric georeferencing: images carry EPSG:4326 geographic transforms; masks carry identity transforms. Pixel grids align identically at `2048 x 2048`.
6. **Pipeline Compatibility (Gate 4B-3F)**: 3 native-compatible dimensions; 6 adapter-required dimensions (tiling to 512x512, z-score normalization, mask casting, stem mapping, negative class handling).
7. **Contamination Audit (Gate 4B-3G)**: Zero exact content hashes overlap with Trujillo Part I (0 / 450 images, 0 / 450 masks). Shared provenance exists (same Zenodo deposit).
8. **Scientific Firewall**: ML forward passes = 0. All 13 model checkpoints remain untouched.

---

## Detailed Gate Results

### Gate 4B-3A: Physical Inventory
- Total Files Examined: **900**
- Images: **450** (150 Oil, 150 No oil, 150 Lookalike)
- Masks: **450** (150 Oil, 150 No oil, 150 Lookalike)
- Raster Driver: `GTiff` across all 900 files (100%)
- Spatial Dimensions: `2048 x 2048` across all 900 files (100%)
- Image Channels: 2 bands (`float32`)
- Mask Channels: 1 band (`uint8`)
- Container Readability: **900 / 900 (100% PASS)**
- Corruptions / Truncations: **0**
- NaNs / Infinities: **0**

### Gate 4B-3B: Image/Mask Pairing
- Total Pairs Expected: **450**
- Total Pairs Verified: **450**
- Unpaired Images: **0**
- Unpaired Masks: **0**
- Pairing Rule: `stem_image == stem_mask.replace('_segmentation', '')` within matching class directory
- Dimension Equality: `2048 x 2048 == 2048 x 2048` (100%)
- Pairing Status: **PAIRED (450 / 450)**

### Gate 4B-3C: Mask Semantics
| Class Directory | Total Masks | Non-Empty Masks | Empty Masks | Foreground Pixels | Foreground % |
|:---:|:---:|:---:|:---:|:---:|:---:|
| **Oil** | 150 | 150 (100%) | 0 (0%) | 62,501,987 | 9.93% |
| **No oil** | 150 | 0 (0%) | 150 (100%) | 0 | 0.00% |
| **Lookalike** | 150 | 0 (0%) | 150 (100%) | 0 | 0.00% |
| **Overall** | **450** | **150 (33.3%)** | **300 (66.7%)** | **62,501,987** | **3.31%** |

*Finding*: Masks are strictly binary {0, 1}. In Trujillo Part III, lookalike samples are treated as negative examples where the target oil mask is entirely 0.

### Gate 4B-3D: Image Physical Value & Dtype Semantics
| Class | Band 1 Mean (dB) | Band 1 Std (dB) | Band 2 Mean (dB) | Band 2 Std (dB) |
|---|:---:|:---:|:---:|:---:|
| **Oil** | -31.39 | 5.25 | -21.46 | 3.99 |
| **No oil** | -31.42 | 5.34 | -21.82 | 4.09 |
| **Lookalike** | -31.55 | 5.39 | -21.95 | 4.14 |
| **Overall Mean** | **-31.45 dB** | **5.33 dB** | **-21.74 dB** | **4.07 dB** |

*Metadata Investigation*:
- GeoTIFF tags: `{'AREA_OR_POINT': 'Area'}`
- Band descriptions: `(None, None)`
- Authoritative polarization metadata: **ABSENT**
- Epistemic classification: **UNVERIFIED** (Band 1 vs Band 2 cannot be definitively declared VV vs VH without upstream documentation).

### Gate 4B-3E: Geospatial / Grid Qualification
- Image Georeferencing: EPSG:4326 geographic transform present on all 450 images.
- Mask Georeferencing: Identity transform (no CRS) on all 450 masks.
- Pixel Grid Matching: Exactly `2048 x 2048` on both image and mask.
- Status: **PARTIAL_METADATA_PIXEL_GRID_MATCH**.

### Gate 4B-3F: Ocean Sentinel Pipeline Compatibility
| Pipeline Dimension | Trujillo Part III | Ocean Sentinel Native Contract | Compatibility Status |
|---|---|---|:---:|
| **Dimensions** | 2048 x 2048 | 512 x 512 | **ADAPTER_REQUIRED** |
| **Channel Count** | 2 | 2 | **NATIVE_COMPATIBLE** |
| **Numeric Dtype** | float32 | torch.float32 | **NATIVE_COMPATIBLE** |
| **Radiometric Scale** | Decibel (~ -40 to +12 dB) | Decibel | **NATIVE_COMPATIBLE** |
| **Channel Ordering** | Unverified (mean -31.5 / -21.7 dB) | Channel 0 / Channel 1 | **ADAPTER_REQUIRED** |
| **Normalization** | Raw dB | Training z-score standardized | **ADAPTER_REQUIRED** |
| **Mask Dtype** | uint8 {0, 1} | torch.float32 {0, 1} | **ADAPTER_REQUIRED** |
| **Mask Filename** | `_segmentation.tif` suffix | `.tif` exact stem match | **ADAPTER_REQUIRED** |
| **Evaluation Strategy** | 150 Oil, 150 No oil, 150 Lookalike | Binary segmentation | **ADAPTER_REQUIRED** |

### Gate 4B-3G: Contamination / Overlap / Independence Audit
- Exact SHA-256 Image Matches with Part I: **0 / 450**
- Exact SHA-256 Mask Matches with Part I: **0 / 450**
- Shared File Identifiers: Reused numeric stems (`00000.tif` ... `00149.tif`), but content hashes are completely distinct.
- Provenance Relationship: Shared upstream deposit (Zenodo 13761290, Trujillo-Acatitla et al., 2024).
- Independence Classification: **BENCHMARK_EXTERNAL_TEST_SET_WITH_SHARED_PROVENANCE**.

---

## Epistemic Classifications

### [OBSERVED FACTS]
1. All 900 files in `data/raw/external_validation/trujillo_part_iii/extracted/` are readable GeoTIFF containers with dimension `2048 x 2048`.
2. All 450 images contain 2 channels of float32 values with negative means (~ -31.45 dB and ~ -21.74 dB).
3. All 450 masks contain 1 channel of uint8 values restricted to {0, 1}.
4. In `Mask/Oil/`, 100% of masks have non-zero pixels; in `Mask/No oil/` and `Mask/Lookalike/`, 100% of masks are all-zero.
5. Zero exact content hashes overlap between Trujillo Part III and Trujillo Part I.
6. The source archive at `02_Test_images_and_ground_truth.7z` remains intact with size `9,859,650,011` bytes and signature `37 7A BC AF`.
7. No scientific dataset qualification, model evaluation, training, or ML forward pass was performed during Phase 4B-3.
8. All 13 PyTorch model checkpoints remain intact and unmodified.

### [INFERENCES]
1. The numeric ranges and distributions strongly indicate that pixel values represent calibrated SAR backscatter in decibels.
2. The empirical mean of Band 1 (-31.45 dB) closely aligns with Part I Channel 0 (-33.23 dB), and Band 2 (-21.74 dB) closely aligns with Part I Channel 1 (-19.94 dB).
3. The Lookalike and No oil classes are designed to function as hard-negative evaluation subsets.

### [UNVERIFIED MECHANISMS]
1. **Physical Polarization Order**: Definite assignment of Band 1 as VV or VH remains UNVERIFIED due to the absence of channel description metadata in GeoTIFF headers.
2. **Acquisition Independence**: Whether Part III scenes originate from distinct Sentinel-1 data takes compared to Part I remains UNVERIFIED in the absence of raw SAFE granule IDs.
3. **Geographic Coordinates**: Ground-truth geographic coordinates for masks remain UNVERIFIED due to the absence of geotransforms in mask headers.

---

## Final Qualification Decision

**`SCIENTIFIC_QUALIFICATION_CONDITIONAL`**

### Usability Conditions:
To utilize Trujillo Part III for Ocean Sentinel external benchmark evaluation, a dedicated adapter must be designed and certified:
1. **Tiling Adapter**: Tiling 2048x2048 scenes into 512x512 non-overlapping patches (16 patches per scene).
2. **Stem-Mapping Adapter**: Suffix stripping for `_segmentation.tif`.
3. **Normalization Adapter**: Application of frozen Part I training z-score parameters (`mean=[-33.23, -19.94], std=[6.49, 4.53]`).
4. **Channel-Order Policy**: Formal specification mapping Band 1 -> Channel 0 and Band 2 -> Channel 1 under the calibrated decibel parity contract.
5. **Class-Aware Metric Accounting**: Separate metric computation for Oil (IoU/Dice), No oil (false positive rate), and Lookalike (hard-negative false positive rate).

*Execution halted at the mandatory boundary. No model evaluation was initiated.*
