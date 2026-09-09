# Ocean Sentinel — Key Decisions & Architectural Constraints

**Document Version**: 1.0.0  
**Status**: ACTIVE / CANONICAL DECISIONS  
**Date**: September 2026  
**Repository**: `D:\Projects\ocean-sentinel`  
**Primary Sources**: `docs/adr/001-copernicus-stac-sentinelhub.md`, `docs/dartis-cdse-cross-validation.md`, `docs/dataset-ingestion-readiness.md`  

---

## 1. Architectural Decisions (ADRs)

### ADR-001: Satellite Access Architecture `[VERIFIED]`
* **Context**: Need to search and retrieve Sentinel-1 GRD imagery over specific AOIs. Full SAFE products are 1–1.5 GB each, which would quickly saturate bandwidth and storage.
* **Decision**: Adopt a hybrid two-tier approach using Copernicus Data Space Ecosystem (CDSE):
  1. **CDSE STAC API v1.1.0** for free, unauthenticated discovery and spatio-temporal catalog queries.
  2. **Sentinel Hub Process API** for targeted, authenticated retrieval of cropped, calibrated float32 GeoTIFF rasters over the exact AOI.
* **Consequences**: Avoids multi-gigabyte SAFE downloads, eliminates local terrain correction/orthorectification overhead, ensures standardized float32 radiometric outputs, and reduces bandwidth by ~99%.

### ADR-002: Explicit Radiometric-Unit Aware SAR Preprocessing `[VERIFIED]`
* **Context**: Need to safely ingest both linear $\sigma^0$ (live CDSE Process API) and pre-calibrated dB $\sigma^0$ (offline Trujillo Part I) without unsafe heuristic guessing.
* **Decision**: Make `SARPreprocessor` explicitly unit-aware via `input_unit: BackscatterUnit` (`LINEAR` default, `DECIBEL` opt-in). Never infer units from numeric signs, ranges, or filenames.
* **Consequences**: Negative dB ocean water pixels remain valid; no double log-conversion occurs; opt-in dB $\to$ linear derivation via $10^{\text{dB}/10}$. Documented in `docs/adr/002-radiometric-unit-generalization.md`.

### ADR-003: In-Memory Raster Decoding `[VERIFIED]`
* **Decision**: All GeoTIFF rasters returned by the Process API or loaded from disk are decoded in-memory using `rasterio.io.MemoryFile`.
* **Rationale**: Eliminates disk I/O bottlenecks, prevents orphaned temporary files, and eliminates file leakage risks.

### ADR-004: Defensive Credential Encapsulation `[VERIFIED]`
* **Decision**: Wrap all client secrets and tokens in Pydantic `SecretStr` or custom classes with sanitized `__repr__`.
* **Rationale**: Prevents accidental leakage in log aggregation systems, terminal outputs, error messages, or documentation.

---

## 2. Scientific & Radiometric Constraints

### Constraint 1: Source-Aware Radiometric Units `[VERIFIED / CRITICAL]`
* **The Conflict**:
  - Live CDSE Process API delivers **linear $\sigma^0$** backscatter ($0.001$ to $0.2$). Converting to decibels requires $10 \log_{10}(\sigma^0)$.
  - Trujillo Part I imagery is **already in decibels (dB)** ($-30\text{ dB}$ to $-5\text{ dB}$).
* **The Danger**:
  - If preprocessor assumes linear input, `raw_arr > 0.0` will evaluate to `False` for all ocean pixels in dB imagery, marking 100% of pixels invalid and crashing with `PreprocessingError`.
  - Furthermore, computing $10 \log_{10}(\text{negative dB})$ produces mathematical NaN.
* **Mandatory Architecture Rule**:
  - Preprocessor must support explicit `input_unit: BackscatterUnit` (`LINEAR` vs `DECIBEL`).
  - Never blindly apply linear $\to$ dB conversion.

### Constraint 2: Missing Geospatial Coordinates in Trujillo Rasters `[VERIFIED]`
* **Observed Reality**:
  - Trujillo masks and images have `CRS: None` and identity affine transform `[0, 1, 0, 0, 0, 1]`.
  - No parent Sentinel-1 product ID or latitude/longitude coordinates exist in the GeoTIFF headers.
* **Systemic Impact**:
  - Detections produced by models trained solely on Trujillo rasters are on an unprojected pixel grid.
  - Cannot compute geographic area ($km^2$) or correlate directly with AIS vessel GPS coordinates without an external spatial index or georeferenced metadata bridge.
* **Mitigation**:
  - Encapsulate offline training patches in `DatasetPatchProvenance` with nominal GSD ($10.0\text{ m}$).
  - Use DARTIS-CDSE reconstructed scenes for georeferenced validation.

### Constraint 3: Data Leakage Prevention in SAR Segmentation `[VERIFIED]`
* **The Danger**:
  - Cropping multiple overlapping $512 \times 512$ chips from the same $2048 \times 2048$ patch and randomly assigning them across train/val/test causes severe spatial data leakage.
* **Mandatory Rules**:
  1. **Group Split by Patch Stem**: All chips cropped from patch `XXXXX` must stay in the same split partition.
  2. **Stratified by Slick Area**: Split partitions must be stratified by quintiles of `oil_pixel_count`.
  3. **Held-Out Benchmarks**: Trujillo Part III and DARTIS-CDSE Mediterranean scenes must serve as completely out-of-distribution evaluation benchmarks.

---

## 3. Canonical Telemetry Lineage Rule `[VERIFIED]`

In Copernicus CDSE, STAC item IDs for `sentinel-1-grd` end in `_COG` with a COG generator packaging hash, whereas ESA `.SAFE` archive names cataloged by DARTIS end in `.SAFE` with an IPF processor hash:
```
DARTIS:    S1B_IW_GRDH_1SDV_20190101T034300_20190101T034325_014295_01A97E_39B8.SAFE
CDSE STAC: S1B_IW_GRDH_1SDV_20190101T034300_20190101T034325_014295_01A97E_2DFF_COG
           └────────────────── 8-TOKEN PREFIX ──────────────────┘
```
**Canonical Lineage Rule**: Two records denote the identical physical satellite radar observation if and only if the 8-component prefix matches:
$$\text{Prefix}(\text{DARTIS\_ID}) \equiv \text{Prefix}(\text{CDSE\_STAC\_ID})$$
and the patch bounding box intersects the scene footprint.