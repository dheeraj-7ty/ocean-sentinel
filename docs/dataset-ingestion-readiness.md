# Dataset Ingestion & Training Readiness Audit

**Document Version**: 1.0.0  
**Status**: ACTIVE / ARCHITECTURAL AUDIT  
**Date**: September 2026  
**Repository**: `D:\Projects\ocean-sentinel`  
**Author**: Implementation Engineer  
**Supervisor**: Chief Architect Officer (CAO)  

---

## 1. Executive Summary & Audit Context

This document establishes the technical, scientific, and architectural readiness for transitioning Ocean Sentinel from Phase 1C (SAR Preprocessing & Dataset Discovery Validation) to Phase 2.0 (Dataset Ingestion, Pre-processing Pipeline Integration, and Leakage-Safe Model Training).

The primary focus of this audit is verifying the end-to-end lineage:
$$\text{DARTIS Metadata} \longrightarrow \text{CDSE STAC Discovery} \longrightarrow \text{Process API} \longrightarrow \text{SAR Preprocessing} \longrightarrow \text{Trujillo Training Dataset} \longrightarrow \text{Leakage-Safe Splits}$$

### Evidence Standard Classification
Throughout this document, all assertions are strictly qualified using the following taxonomy:
* `[VERIFIED]`: Directly proven via inspected code, executed deterministic scripts, local filesystem checksums, or live API responses.
* `[REPORTED]`: Documented in peer-reviewed scientific literature or author-provided repository notes, but not yet locally executed or reproduced.
* `[PLANNED]`: Architectural design intended for implementation in the subsequent phase.
* `[OPEN QUESTION]`: Unresolved technical ambiguity requiring CAO decision or empirical resolution.
* `[SUPERSEDED]`: Prior assumptions or hypotheses that have been formally refuted by audit findings.

---

## 2. DARTIS -> CDSE STAC Lineage & Resolution Analysis

### 2.1 The Naming Discrepancy: `MATCH_WITH_METADATA_DIFFERENCE`
In the Phase 1C.2 cross-validation of 40 deterministically stratified scenes from Yang & Singha (2025) / PANGAEA 980773, 100% of queries returned `MATCH_WITH_METADATA_DIFFERENCE`. Zero scenes returned `EXACT_MATCH`. `[VERIFIED]`

The mechanical reason is the difference in product encapsulation between raw ESA `.SAFE` archives and Copernicus CDSE STAC Cloud-Optimized GeoTIFFs (`_COG`):

* **DARTIS Catalog Identifier (ESA SAFE convention)**:
  `S1B_IW_GRDH_1SDV_20190101T034300_20190101T034325_014295_01A97E_39B8.SAFE`
  Prefix: `S1B_IW_GRDH_1SDV_20190101T034300_20190101T034325_014295_01A97E`
  Suffix: `39B8.SAFE` (IPF build checksum)

* **CDSE STAC Item Identifier (Copernicus COG convention)**:
  `S1B_IW_GRDH_1SDV_20190101T034300_20190101T034325_014295_01A97E_2DFF_COG`
  Prefix: `S1B_IW_GRDH_1SDV_20190101T034300_20190101T034325_014295_01A97E`
  Suffix: `2DFF_COG` (COG packaging checksum)

### 2.2 Canonical Lineage Matching Rule
Two records denote the identical physical satellite radar observation if and only if the 8-component telemetry prefix matches: `[VERIFIED]`
$$P(\text{ID}) = \text{Mission} \times \text{Mode} \times \text{Type} \times \text{Pol} \times \text{Start} \times \text{Stop} \times \text{Orbit} \times \text{DataTake}$$

$$\text{Prefix}(\text{DARTIS\_ID}) \equiv \text{Prefix}(\text{CDSE\_STAC\_ID})$$

* Mission: `S1A` / `S1B`
* Beam Mode: `IW` (Interferometric Wide)
* Product Type: `GRDH` (Ground Range Detected High-Resolution)
* Processing Level & Polarization: `1SDV` (Level-1 Dual-Pol VV+VH)
* Start / Stop Timestamps: UTC down to second precision (`YYYYMMDDTHHMMSS`)
* Absolute Orbit: 6-digit zero-padded integer (e.g. `014295`)
* Data-Take ID: 6-character hexadecimal identifier (e.g. `01A97E`)

The trailing 4-character hex hash is an ephemeral packaging checksum (IPF build hash in SAFE vs COG generator hash in CDSE).

### 2.3 Cross-Validation Evidence Summary `[VERIFIED]`
* **Sample Size**: 40 unique scenes across 8 strata (`ow`, `oc`, `nw`, `nc` x `S1A`, `S1B`) covering all 12 calendar months of 2019.
* **CDSE STAC Match Rate**: 40 / 40 (100.0%).
* **Spatial Containment**: 40 / 40 (100.0%) patches lie fully inside the resolved CDSE footprint.
* **Dual-Polarization**: 40 / 40 (100.0%) scenes confirm `['VV', 'VH']` availability.
* **Imagery Downloaded**: 0 Bytes transferred (zero storage impact).
* **Machine-Readable Report**: `data/metadata/yang_singha_2025/cdse_validation_report.json`.

---

## 3. Radiometric Unit Safety: Linear $\sigma^0$ vs. Decibel (dB)

### 3.1 The Critical Conflict
A major scientific risk exists at the interface between live satellite ingestion and offline training datasets: `[VERIFIED]`

1. **Copernicus Sentinel Hub Process API (Live Pipeline)**:
   Returns calibrated **linear radar backscatter** $\sigma^0$ in float32.
   To convert to decibels:
   $$\sigma^0_{\text{dB}} = 10 \cdot \log_{10}(\sigma^0_{\text{linear}})$$
   Typical marine backscatter in linear scale: $0.001$ to $0.2$.

2. **Trujillo-Acatitla Part I (Offline Training Candidate)**:
   The imagery is **already calibrated in decibels (dB)**. `[REPORTED]`
   Typical marine backscatter in dB scale: $-30\text{ dB}$ to $-5\text{ dB}$.

### 3.2 Hazard Analysis in Existing Code `[VERIFIED]`
In `SARPreprocessor._process_single_band` (`src/ocean_sentinel/processing/sar.py:198`):
```python
valid_mask = np.isfinite(raw_arr) & (raw_arr > 0.0)
```
and lines 244-245:
```python
clamped_linear = np.maximum(valid_linear, config.linear_min_threshold)
computed_db = 10.0 * np.log10(clamped_linear)
```

If Trujillo dB imagery is passed to `SARPreprocessor` under the current implementation:
1. `raw_arr > 0.0` will evaluate to `False` for all typical ocean pixels (e.g. $-18\text{ dB} \ngtr 0$).
2. `valid_count` will equal $0$, raising `PreprocessingError: contains zero valid pixels`.
3. If `valid_mask` were bypassed, $10 \cdot \log_{10}(\text{negative dB})$ would produce `NaN` or clamp to `linear_min_threshold`, completely corrupting the training data.

### 3.3 Required Architecture Solution `[PLANNED]`
Add `input_unit: BackscatterUnit` to `PreprocessingConfig`:
* `BackscatterUnit.LINEAR` (Default for Process API GeoTIFFs):
  - Valid mask: `np.isfinite(arr) & (arr > 0.0)`
  - dB conversion: $10 \cdot \log_{10}(\max(arr, \epsilon))$
* `BackscatterUnit.DECIBEL` (For Trujillo Part I / pre-calibrated sources):
  - Valid mask: `np.isfinite(arr) & (arr >= db_valid_min) & (arr <= db_valid_max)` (e.g. $[-50.0, +15.0]\text{ dB}$)
  - Bypass dB conversion (`db_data = raw_arr.copy()`)
  - Optional linear reconstruction: $\sigma^0_{\text{linear}} = 10^{\sigma^0_{\text{dB}} / 10}$
* **Normalized Representation**:
  Both paths converge on the physical `db_data` array before entering per-band normalization (Percentile/MinMax/Z-Score) to produce the model-ready $[0, 1]$ tensor.

---

## 4. Trujillo-Acatitla Part I Ingestion Contract

### 4.1 Asset Verification `[VERIFIED]`
* **Mask Archive**: `data/raw/trujillo_2024/01_Train_Val_Oil_Spill_mask.7z` (6,236,761 bytes, MD5 `9bc53c38db2ab82d15bf6914352403ef`).
* **Extracted Masks**: `data/raw/trujillo_2024/masks/Mask_oil/` containing exactly 1,200 single-band TIFF masks.
* **Verified Dimensions**: $2048 \times 2048$ pixels, `uint8`, strictly binary {0, 1}.
* **Missing Geospatial Metadata**:
  - `CRS`: `None`
  - `transform`: Identity `Affine(1.0, 0.0, 0.0, 0.0, 1.0, 0.0)`
  - No parent Sentinel-1 acquisition ID in headers or filenames.

### 4.2 Image Archive Properties `[REPORTED]`
* **Archive**: `01_Train_Val_Oil_Spill_images.7z` (40.71 GB compressed, $\approx 45\text{ GB}$ uncompressed).
* **Expected Content**: 1,200 paired dual-polarization ($\text{VV} + \text{VH}$) rasters, $2048 \times 2048$, `float32`, units in dB $\sigma^0$.

### 4.3 Mask-Image Pairing Contract `[PLANNED]`
1. **Filename Stem Keying**:
   Pairing must occur strictly on the 5-digit stem: `image_{stem}.tif` <-> `mask_{stem}.tif` (or identical stem `00000.tif` <-> `00000.tif`).
2. **Dimension Matching**:
   Strict assertion: `image.shape[:2] == mask.shape == (2048, 2048)`.
3. **Data Integrity Checks**:
   - `mask` unique values must be a subset of {0, 1}.
   - `image` must contain finite values with $< 50\%$ invalid/border pixels.
   - If a pair is mismatched or corrupt, it must be quarantined with an audit log.

### 4.4 Geospatial Provenance Mitigation `[PLANNED]`
Because the raw Trujillo rasters lack embedded CRS/geotransforms:
* Store a synthetic provenance container `DatasetPatchProvenance`:
  - `dataset_id`: `trujillo_2024_part_i`
  - `sample_stem`: e.g. `00000`
  - `crs`: `None` (explicitly documented as unprojected pixel grid)
  - `nominal_gsd_meters`: `10.0`
  - `radiometric_unit`: `BackscatterUnit.DECIBEL`
  - `polarizations`: `[Polarization.VV, Polarization.VH]`
  - `oil_pixel_count`: computed from mask sum
  - `oil_area_fraction`: `oil_pixel_count / (2048 * 2048)`

---

## 5. Leakage Prevention & Dataset Splitting Strategy

### 5.1 Leakage Vectors
In satellite SAR segmentation, data leakage produces catastrophically over-optimistic validation metrics if not prevented: `[VERIFIED]`
1. **Patch-Tile Leakage**: Randomly splitting overlapping $512 \times 512$ chips cropped from the same $2048 \times 2048$ scene into training and test sets.
2. **Parent-Scene Spatial Leakage**: Multiple $2048 \times 2048$ crops originating from the same Sentinel-1 orbit pass placed in both train and validation sets.
3. **Temporal Leakage**: Same geographical slick observed across consecutive orbit cycles (12-day revisit) split across sets.

### 5.2 Split Protocol `[PLANNED]`
1. **Stem-Level Grouping (Strict Zero-Tile Leakage)**:
   All sub-patches or crops generated from a single $2048 \times 2048$ patch `XXXXX` must stay in the same split partition (never split chips across train/val/test).
2. **Internal Trujillo Part I Split (70 / 15 / 15)**:
   - Grouped strictly by patch stem ID (1,200 unique groups).
   - Stratified by slick size distribution (quintiles of `oil_pixel_count` so tiny slicks and massive spills are balanced).
   - Fixed random seed for deterministic reproduction.
3. **Gold-Standard Unseen Test Sets**:
   - **Trujillo Part III**: Held out as an independent evaluation benchmark (never seen during training or validation). `[REPORTED]`
   - **DARTIS-CDSE Mediterranean Reconstructions**: Full-resolution, calibrated scenes reconstructed directly from Copernicus STAC to evaluate cross-geographic generalization. `[PLANNED]`

---

## 6. Architecture Gap Analysis Prior to Large Download

Before initiating the 40.71 GB download of `01_Train_Val_Oil_Spill_images.7z`, the following architectural enhancements should be completed:

| Component | Current State | Required State | Priority |
| :--- | :--- | :--- | :---: |
| **`PreprocessingConfig`** | `convert_to_db: bool` assumes linear input | Add `input_unit: BackscatterUnit` enum | **Critical** |
| **`SARPreprocessor`** | Rejects negative backscatter (`raw > 0`) | Handle pre-computed dB backscatter ($[-50, +15]$) | **Critical** |
| **`DatasetPatchLoader`** | None (only live `ImageryResult`) | Contract for offline paired image/mask rasters | **High** |
| **Patch Tiler** | None ($2048 \times 2048$ full scenes) | Deterministic $512 \times 512$ sliding window tiler | **High** |
| **Storage Resumption** | `scripts/download_datasets.py` exists | Verified range-resumption tested on multi-GB file | **Medium** |

---

## 7. Next-Step Recommendations

1. **Phase 1C.3**: Implement the `BackscatterUnit` enhancements in `src/ocean_sentinel/processing/` and add unit tests covering dB inputs.
2. **Phase 1C.4**: Implement the `TrujilloDatasetLoader` with stem-based group splitting and tiling contracts.
3. **Phase 2.0**: CAO formal authorization to trigger the 40.71 GB download via `scripts/download_datasets.py`.
