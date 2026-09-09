# Trujillo Part I Dataset Contract & Ingestion Specification

**Document Version**: 2.0.0  
**Status**: VERIFIED / CANONICAL SPECIFICATION (PHASE 2.0 COMPLETED)  
**Target Phase**: Phase 2.0  
**Repository**: `D:\Projects\ocean-sentinel`  
**Author**: Implementation Engineer  
**Supervisor**: Chief Architect Officer (CAO)  
**Date**: September 2026  

---

## 1. Executive Summary & Objective

This document defines the formal offline dataset contract, validation engine, provenance schema, and deterministic tiling architecture required to safely ingest the **Trujillo-Acatitla et al. (July 2024) Part I** dataset (`01_Train_Val_Oil_Spill_images.7z` / `01_Train_Val_Oil_Spill_mask.7z`, Zenodo DOI `10.5281/zenodo.8346860`).

The pipeline architecture enforces:
$$\text{Trujillo Image} \longrightarrow \text{Validated Patch} \longrightarrow \text{Explicit DECIBEL} \longrightarrow \text{Strict Pairing} \longrightarrow \text{Provenance} \longrightarrow \text{Deterministic Tiling} \longrightarrow \text{Zero-Leakage Grouping} \longrightarrow \text{Model-Ready Tile}$$

> [!NOTE]
> **Phase 2.0 Acquisition & Verification Completed**:
> The 40.71 GB image archive (`01_Train_Val_Oil_Spill_images.7z`, 40,712,942,245 bytes) was acquired and verified via MD5 checksum (`e2a6a5b473ca587474d8daee9cd54e10`, Zenodo record 8346860). All 1,200 GeoTIFF images have been verified against the 1,200 ground-truth masks.

---

## 2. Source-Truth Audit & Verification Taxonomy

Every attribute in this contract is explicitly categorized under one of four standards:

| Status | Definition | Verified State in Trujillo Part I |
| :---: | :--- | :--- |
| **`VERIFIED`** | Directly proven via inspected code, local disk checksums, raster inspections, or executed unit tests. | • Archive: 40,712,942,245 bytes, MD5 `e2a6a5b473ca587474d8daee9cd54e10`.<br>• 1,200 masks in `data/raw/trujillo_2024/masks/Mask_oil/`: shape $(2048, 2048)$; `uint8`; binary $\{0, 1\}$; `CRS: None`; transform identity.<br>• 1,200 images in `data/raw/trujillo_2024/images/Oil/`: shape $(2048, 2048)$; 2 bands; `float32`; LZW compression; `CRS: EPSG:4326`; valid geographic affine transform.<br>• Pairing: exactly 1,200 exact 1:1 pairs (`00000` to `01339`), 0 orphaned images, 0 orphaned masks.<br>• Radiometry: strictly decibels ($\text{dB } \sigma^0$), Band 1 mean ~$-35\text{ dB}$ (100% negative), Band 2 mean ~$-21\text{ dB}$ (>99.99% negative). |
| **`REPORTED`** | Documented in peer-reviewed literature or author metadata, but not yet verified via raw Sentinel-1 telemetry. | Sensor: Sentinel-1 C-band SAR IW mode; geographical region: North Sea; polarizations: dual-pol ($\text{VV} + \text{VH}$). |
| **`ASSUMED`** | Working engineering or scientific assumption, explicitly labeled. | Nominal GSD of $10.0\text{ m}$ (Sentinel-1 IW GRDH nominal grid spacing); policy default minimum valid ratio = 0.5. |
| **`UNKNOWN`** | Completely absent from source headers, unverified, or not yet determined. | • Channel polarization mapping: which band is VV and which is VH (neither TIFF tags nor Zenodo defines this; guessing is forbidden).<br>• Parent Sentinel-1 scene ID, orbit direction, relative orbit, acquisition timestamps. |

---

## 3. Error Taxonomy Architecture

Offline dataset failures (local file corruption, unreadable GeoTIFFs, dimension mismatches, tiling bounds violations) are conceptually distinct from remote satellite-service failures (OAuth2 token expiry, STAC provider rate limiting, Process API timeouts).

To preserve clean architectural boundaries, `DatasetError` is established as an independent root exception inheriting directly from `Exception`, completely decoupled from `SatelliteError`:

```
Exception
   │
   ├── SatelliteError (Remote Satellite / STAC / Process API domain)
   │     ├── AuthenticationError
   │     ├── ProviderUnavailableError
   │     └── ...
   │
   └── DatasetError (Offline Ingestion & Tiling domain)
         ├── DatasetPairingError       (Mismatched stems, orphaned files)
         ├── DatasetValidationError   (Dimension mismatch, non-binary mask, non-finite pixels)
         ├── DatasetTilingError        (Invalid strides, impossible tile geometry)
         └── DatasetProvenanceError    (Corrupted provenance, metadata inconsistencies)
```

Every `DatasetError` carries:
- `code: DatasetErrorCode` (e.g. `PAIRING_FAILURE`, `VALIDATION_FAILURE`, `TILING_FAILURE`).
- `message: str` (actionable human-readable description).
- `details: dict[str, Any]` (structured debugging context, sanitized of secrets via `to_dict()`).
- `cause: Optional[Exception]` (underlying exception chain).

---

## 4. Domain Models & Provenance Contract

All domain models reside in `src/ocean_sentinel/ingestion/models.py`.

### 4.1 Immutable Dataset Patch Provenance (`DatasetPatchProvenance`)
Frozen at the model level (`ConfigDict(frozen=True)`) to eliminate accidental mutation:
```python
class DatasetPatchProvenance(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    dataset_name: str                               # 'trujillo_2024_part_i'
    dataset_version: Optional[str] = None          # '1.0.0'
    source_archive: Optional[str] = None           # '01_Train_Val_Oil_Spill_images.7z'
    patch_stem: str                                # e.g. '00000'
    image_path: Optional[Path] = None
    mask_path: Optional[Path] = None
    radiometric_unit: BackscatterUnit              # BackscatterUnit.DECIBEL

    # Polarizations (marked UNKNOWN or REPORTED, never hardcoded as verified fact)
    polarizations: Optional[list[Polarization]] = None
    polarization_status: VerificationStatus = VerificationStatus.UNKNOWN

    # Spatial geometry
    native_shape: tuple[int, int] = (2048, 2048)
    native_shape_status: VerificationStatus = VerificationStatus.REPORTED
    dtype: str = "float32"
    dtype_status: VerificationStatus = VerificationStatus.REPORTED
    nominal_gsd_meters: Optional[float] = 10.0
    nominal_gsd_status: VerificationStatus = VerificationStatus.ASSUMED

    # Geospatial reference (None for unreferenced rasters)
    crs: Optional[str] = None
    crs_status: VerificationStatus = VerificationStatus.UNKNOWN
    transform: Optional[list[float]] = None
    transform_status: VerificationStatus = VerificationStatus.UNKNOWN

    # Satellite telemetry (None for Trujillo Part I)
    parent_scene_id: Optional[str] = None
    parent_scene_status: VerificationStatus = VerificationStatus.UNKNOWN
    acquisition_time: Optional[datetime] = None
    acquisition_time_status: VerificationStatus = VerificationStatus.UNKNOWN
```

### 4.2 Compositional Tile Provenance (`TileProvenance`)
Rather than duplicating mutable parent fields, `TileProvenance` embeds an immutable reference to `DatasetPatchProvenance` and adds only tile-specific coordinates:
```python
class TileProvenance(BaseModel):
    model_config = ConfigDict(frozen=True)

    parent: DatasetPatchProvenance
    tile_id: str          # e.g. '00000_r01_c02'
    parent_stem: str      # '00000'
    group_key: str        # '00000' (enforces zero-leakage partitioning)
    row_idx: int          # 0..3
    col_idx: int          # 0..3
    row_offset: int       # 0, 512, 1024, 1536
    col_offset: int       # 0, 512, 1024, 1536
    height: int           # 512
    width: int            # 512
```

### 4.3 Dual-Polarization Validity Mask Semantics
`DatasetSample` carries both per-channel validity and a reduced 2D validity mask:
- `valid_mask_per_channel`: Shape `(num_channels, height, width)`, boolean. Element `[c, y, x]` is `True` if and only if `image_data[c, y, x]` is finite (not NaN, +inf, -inf).
- `valid_mask`: Shape `(height, width)`, boolean. **Reduction Rule**:
  $$\text{valid\_mask}[y, x] = \bigwedge_{c=0}^{C-1} \text{valid\_mask\_per\_channel}[c, y, x]$$
  Implemented via: `np.all(valid_mask_per_channel, axis=0)`.
  This guarantees that any pixel marked valid in the 2D mask contains valid scientific data in all polarizations.

---

## 5. Strict Stem-Pairing Engine

The pairing contract between image rasters and mask rasters is strictly deterministic:
$$\text{Stem}(\text{image}) \equiv \text{Stem}(\text{mask}) \quad (\text{e.g. } 00000.\text{tif} \longleftrightarrow 00000.\text{tif})$$

Rules:
1. **Zero Fuzzy Matching**: Never match `00000_a.tif` to `00000.tif` or search for nearest string distance.
2. **Zero Silent Fallback**: If an image lacks an exact corresponding mask (or vice versa), raising `DatasetPairingError` is mandatory upon access.
3. **Explicit Orphan Discovery**: `loader.get_orphaned_stems()` returns explicit lists `(orphaned_images, orphaned_masks)` for pre-flight data auditing.

---

## 6. Scientific Validation Engine

`TrujilloDatasetLoader.validate_sample(stem)` evaluates candidate pairs against configurable policy rules (`DatasetValidationConfig`):

| Check Name | Rule Evaluated | Failure Consequence |
| :--- | :--- | :--- |
| `image_exists` | Image file exists and is a regular file. | `DatasetValidationError` |
| `mask_exists` | Mask file exists and is a regular file. | `DatasetValidationError` |
| `rasters_readable` | File can be decoded by GDAL/rasterio without corruption. | `DatasetValidationError` |
| `dimension_equality` | $\text{Height}_{\text{img}} == \text{Height}_{\text{mask}} \land \text{Width}_{\text{img}} == \text{Width}_{\text{mask}}$. | `DatasetValidationError` |
| `expected_shape` | Shape matches policy (default: $(2048, 2048)$). | Configurable policy check |
| `expected_channels` | Channels match policy (default: $2$). | Configurable policy check |
| `expected_image_dtype` | Image dtype matches policy (default: `float32`). | Configurable policy check |
| `expected_mask_dtype` | Mask dtype matches policy (default: `uint8`). | Configurable policy check |
| `mask_binary_semantics` | $\text{Unique}(\text{mask}) \subseteq \{0, 1\}$. | Critical validation failure |
| `valid_pixel_ratio_policy` | $\text{ValidPixels} / \text{TotalPixels} \ge \text{min\_valid\_ratio}$ (default: $0.5$). | Configurable policy check |

---

## 7. Radiometric Unit Safety & Preprocessor Integration

Trujillo Part I radar backscatter data is calibrated in **decibels ($\sigma^0\text{ dB}$)**:
- Typical marine values: $-30.0\text{ dB}$ to $-5.0\text{ dB}$.
- Negative values are physical ocean radar observations.

### Integration Contract
1. **Unconditional Declaration**: `DatasetPatchProvenance.radiometric_unit` is set to `BackscatterUnit.DECIBEL`.
2. **No Heuristic Guessing**: Unit is never inferred from array signs, numerical ranges, or filenames.
3. **No Linear Conversion**: Linear-to-dB logarithm conversion ($10 \log_{10}(\sigma^0)$) is **NEVER** applied to Trujillo data.
4. **Direct Preprocessor Ingestion**: When passed to `SARPreprocessor.process_arrays`, `PreprocessingConfig(input_unit=BackscatterUnit.DECIBEL)` is enforced. Valid pixels are defined by `np.isfinite(raw_arr)`, and normalization (Percentile/MinMax/Z-Score) operates directly on the native dB backscatter distribution.

---

## 8. Deterministic Sliding-Window Tiling Engine

The tiling engine (`src/ocean_sentinel/ingestion/tiling.py`) is decoupled from file loading and operates on pure geometry and in-memory arrays.

### 8.1 Generic Tile Coordinate Calculation
`compute_tile_definitions(parent_height, parent_width, parent_stem, config)`:
- Accepts arbitrary $(H, W)$, $(T_h, T_w)$, and strides $(S_y, S_x)$.
- Canonical Trujillo Part I setup:
  - Parent: $2048 \times 2048$ pixels
  - Tile: $512 \times 512$ pixels
  - Stride: $512 \times 512$ pixels (non-overlapping)
  - Edge handling: `"drop"`
  - Grid: $4 \text{ rows} \times 4 \text{ cols} = 16 \text{ tiles}$ exactly.
- Ordering: Deterministic row-major raster scan:
  $$\text{Row } 0: (0, 0), (0, 512), (0, 1024), (0, 1536)$$
  $$\text{Row } 1: (512, 0), (512, 512), (512, 1024), (512, 1536)$$
  $$\text{Row } 2: (1024, 0), (1024, 512), (1024, 1024), (1024, 1536)$$
  $$\text{Row } 3: (1536, 0), (1536, 512), (1536, 1024), (1536, 1536)$$

### 8.2 Zero-Interpolation Mask Slicing
- Slicing uses exact integer array indexing: `mask[r0:r1, c0:c1]`.
- No interpolation, nearest-neighbor rounding, or continuous resampling.
- Binary $\{0, 1\}$ integrity is 100% preserved.
- **Conservation Invariant**: For any non-overlapping partition covering the full domain:
  $$\sum_{k=0}^{15} \text{TileForegroundPixels}_k \equiv \text{ParentForegroundPixels}$$

---

## 9. Data Leakage Prevention Strategy

Data leakage across training, validation, and testing partitions causes unrealistically optimistic benchmark scores. In SAR oil spill segmentation, splitting tiles from the same scene across partitions is a critical failure.

### Zero-Leakage Grouping Key
- Every tile carries: `tile.definition.group_key = parent_stem` and `tile.provenance.group_key = parent_stem`.
- When dataset splitting occurs (Phase 2.0+):
  $$\text{Partition}(\text{Tile}_i) = \text{Partition}(\text{Stem}_j) \quad \forall \text{Tile}_i \in \text{Patch}_j$$
- GroupKFold / StratifiedGroupKFold MUST group by `group_key` (stem), guaranteeing that all 16 chips from patch `XXXXX` reside in the identical partition.

---

## 10. Memory Safety & Single-Read Loading

To handle large dataset operations safely:
1. **Bounded Per-Sample Loading**: `TrujilloDatasetLoader` indexes paths and file metadata upon instantiation; zero imagery bytes are loaded until `load_sample()` is invoked.
2. **Generator Memory Independence**: `iter_samples()` yields one sample at a time. It holds zero internal caches or historical lists of yielded samples. Once the caller drops reference to a sample, it is immediately garbage-collected.
3. **Single Read Pass in `load_and_tile`**: `load_and_tile(stem)` calls `load_sample(stem)` which reads the GeoTIFF exactly once and performs validation in-memory before tiling, completely eliminating duplicate full-raster disk I/O.

---

## 11. Archive-Verification Checklist Execution (Phase 2.0 Post-Flight Audit)

During Phase 2.0, the archive was downloaded, inspected, and verified against all pre-flight audit items:

- [x] **Archive Checksum**: Verified archive size of 40,712,942,245 bytes. Authoritative MD5 `e2a6a5b473ca587474d8daee9cd54e10` verified against Zenodo record 8346860. *(Note: SHA256 was NOT AVAILABLE from authoritative Zenodo record).*
- [x] **Archive Structure**: Verified layout consisting of 1 root directory `Oil/` containing 1,200 GeoTIFF images (`Oil/00000.tif` through `Oil/01339.tif`).
- [x] **Total File Count**: Exactly 1,200 GeoTIFF image rasters exist matching the 1,200 verified masks.
- [x] **Filename Stems**: 5-digit stems `00000.tif` to `01339.tif` (100.0% exact pairing with zero orphaned images and zero orphaned masks).
- [x] **Channel Count**: Verified 2 bands across all image rasters.
- [x] **Band Order / Polarization**: `UNKNOWN`. TIFF band descriptions and tags are empty dictionaries; Zenodo record does not declare band order. Heuristic guessing is forbidden.
- [x] **Image Dtype**: `float32` across both bands.
- [x] **Numerical Range**: Verified pre-calibrated decibels (dB $\sigma^0$). Band 1 mean ~$-35\text{ dB}$ (100% negative pixels); Band 2 mean ~$-21\text{ dB}$ (>99.99% negative pixels).
- [x] **TIFF Tags**: LZW compression, GDAL driver `GTiff`, metadata tags empty.
- [x] **Geospatial Reference**: **DISCOVERED FACT** — Image GeoTIFFs contain valid `CRS: EPSG:4326` and non-identity geographic affine transforms with WGS84 bounding coordinates in the North Sea. *(Contradicts earlier reconnaissance assumption that rasters lacked CRS due to unreferenced masks).*
