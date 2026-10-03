# CDSE Physical Compatibility Pilot — EXP-08 Phase 11-R5.4
# docs/exp08_cdse_physical_compatibility_pilot.md

**Document Version**: 3.4 (Phase 11-R5.5 Final Integrity Micro-Closure)  
**Task ID**: `OCEAN-SENTINEL-PHASE11-R5.5-EXP08-LAST-INTEGRITY-MICROCLOSURE`  
**Stage**: Real Physical Compatibility Pilot at Trujillo Angular Storage Grid  
**Date**: 2026-09-27  
**Pilot Scope**: PHYSICAL BYTE-LEVEL, SPATIAL-GRID, AND PROVENANCE COMPATIBILITY PILOT (3/3 Scenes)  
**Model Inference**: STRICTLY FORBIDDEN & NOT PERFORMED (`EXECUTION_AUTHORIZED = FALSE`)  
**Data Access Route**: Authenticated CDSE Process API (`https://sh.dataspace.copernicus.eu/api/v1/process`)  
**Machine-Readable Results**: [`scratch/cdse_physical_pilot_results_r5_1.json`](file:///d:/Projects/ocean-sentinel/scratch/cdse_physical_pilot_results_r5_1.json) | [`scratch/cdse_physical_pilot_results_r5_3.json`](file:///d:/Projects/ocean-sentinel/scratch/cdse_physical_pilot_results_r5_3.json) | [`data/metadata/exp08_r5_4_footprints_and_clusters.json`](file:///d:/Projects/ocean-sentinel/data/metadata/exp08_r5_4_footprints_and_clusters.json)  
**Protocol Consistency**: This pilot (V3.4) is consistent with Protocol V3.5 (`EXP08_CORRECTED_PROTOCOL_V3_5`). V3.5 normative changes (§9.3 -70 dB reframing, §13.3 O1 rename, §14.1 bootstrap seed) do not alter any pilot procedure, finding, or interpretation. No pilot re-execution is required.

> [!NOTE]
> **Pilot Scope Boundaries**:
> - **VERIFIED**: Actual byte-level retrieval, float32 dtype, EPSG:4326 grid fidelity ($\Delta = 8.9831528e-5^\circ$), raster dimensions, nodata/dataMask behavior, operative processing contract (upsampling NEAREST, backCoeff SIGMA0_ELLIPSOID), exact acquisition identity (1:1 Catalog match), evaluation domain geometry, and absence of local resampling (`LOCAL_RESAMPLING = NONE`).
> - **NOT PROVEN**: Exact Trujillo preprocessing equivalence, bitwise radiometric equivalence, and primary dataset band-label provenance beyond the established operational EXP-06 contract (`Ch0 = VH, Ch1 = VV`).
> - **BYTE-LEVEL SCOPE CLARIFICATION**: "Byte-level" in this document refers to format/storage retrieval verification (dtype, shape, grid, nodata consistency). It does NOT imply radiometric or numerical equivalence with the original Trujillo preprocessing pipeline. The limitation `Trujillo preprocessing equivalence = NOT_PROVEN_WITH_CURRENT_ARTIFACTS` is not upgraded by this verification.

---

## 1. Executive Summary & Resolution of R5 Spatial Finding

In Phase 11-R4, the CDSE pilot was restricted to STAC metadata inspection. In Phase 11-R5, an initial byte-level retrieval confirmed API connectivity, but requested coarse 64×64 rasters (~232m pixel spacing), which matched the CNN tensor shape but failed to achieve spatial-resolution equivalence with the training grid.

In **Phase 11-R5.1 through R5.4**, all prerequisite contracts were forensically resolved:
1. **Audit of Frozen Spatial Grid**: Inspection of all 1,200 Trujillo Part I Oil GeoTIFFs confirmed the canonical spatial grid is `EPSG:4326` with fixed angular cell size $\Delta \text{deg} = 8.983152841195215 \times 10^{-5}$ degrees in both axes.
   - *Physical Ground Spacing Interpretation*: Under the WGS84 ellipsoid, this angular cell size corresponds to approximately 9.96 metres north-south across all latitudes, while east-west physical ground spacing varies with $\cos(\text{latitude})$. At the pilot latitudes ($31^\circ\text{--}35^\circ\text{N}$), east-west spacing is approximately $8.23\text{--}8.55\text{ metres}$ (aspect ratio 1.16–1.21). It is not described as globally isotropic 10m×10m pixels; the scientific invariant is reproduction of the frozen **Trujillo TIFF angular storage grid** in EPSG:4326.
2. **CDSE Requested Angular Grid Execution**: Authenticated raster retrievals were executed across all three representative DARTIS pilot scenes requesting this exact angular cell size (`resx = 8.983152841195215e-05°`, `resy = 8.983152841195215e-05°`, `backCoeff: "SIGMA0_ELLIPSOID"`, `orthorectify: "false"`, `upsampling: "NEAREST"`, bounds CRS: `EPSG:4326`):
   - **Pilot 1 (P1 `nc` — Coastal Lookalike)**: 1,779 × 1,509 pixels, 16.35 MB GeoTIFF (9.97m lat, 8.23m lon spacing), 100% dataMask-valid pixels, $\text{VV} - \text{VH} = +26.46\text{ dB}$ (diagnostic observation).
   - **Pilot 2 (P2 `nw` — Open Water Lookalike)**: 1,771 × 1,511 pixels, 13.54 MB GeoTIFF (9.96m lat, 8.29m lon spacing), 100% dataMask-valid pixels, $\text{VV} - \text{VH} = +20.00\text{ dB}$ (diagnostic observation).
   - **Pilot 3 (P3 `oc` — Coastal Oil Spill)**: 1,745 × 1,514 pixels, 16.87 MB GeoTIFF (9.96m lat, 8.55m lon spacing), 100% dataMask-valid pixels, $\text{VV} - \text{VH} = +20.34\text{ dB}$ (diagnostic observation).
3. **Server-Side Gridding vs Local Resampling**:
   - `LOCAL_RESAMPLING = NONE`: No interpolation, reprojection, or spatial resizing is performed locally by the client between retrieval and tiling.
   - `SERVICE_SIDE_GRID_GENERATION = YES`: The CDSE Process API generates the requested EPSG:4326 grid server-side from Sentinel-1 Level-1 GRDH source data via its internal sampling chain.
   - `SERVICE_SIDE_INTERPOLATION = NEAREST`: Nearest-neighbor upsampling avoids artificial intermediate backscatter generation and preserves discrete mask boundaries without bilinear smoothing.
4. **Tileability and Pixel Coverage**:
   - All three full-resolution rasters exceed $512 \times 512$ pixels.
   - Execution of `inference.py`'s `compute_tile_windows(height, width, tile_size=512, overlap=0)` produces **12 tiles** per scene ($3 \text{ row spans} \times 4 \text{ col spans}$) via boundary clamping on non-divisible dimensions.
   - Every pixel of the retrieved raster is covered ($min\_coverage \ge 1$, $uncovered = 0$). Overlapping boundary strips are normalized during spatial reconstruction via weighted accumulation (`accum_prob / accum_weight`). Zero silent truncation; zero omitted edge strips.

---

## 2. Pilot Scene Configuration, Provenance & Geometry

| Pilot | Subset | Category | Sentinel-1 Acquisition Time | DARTIS Sentinel ID | CDSE Resolved ID | Exact Match | Platform | Orbit Direction (Rel Orbit) | Canonical Payload SHA-256 |
|---|---|---|---|---|---|---|---|---|---|
| **P1** | `nc` | Coastal Lookalike | 2019-01-24T03:51:17Z | `S1A_IW_GRDH_1SDV_20190124T035117_20190124T035142_025614_02D7E5_2D5A.SAFE` | `..._02D7E5_F282_COG` | `TRUE` | `sentinel-1a` | `DESCENDING` (167) | `9e036058277a9f77...` |
| **P2** | `nw` | Open Water Lookalike | 2019-01-04T15:57:28Z | `S1A_IW_GRDH_1SDV_20190104T155728_20190104T155753_025330_02CD9D_B67E.SAFE` | `..._02CD9D_4F9F_COG` | `TRUE` | `sentinel-1a` | `ASCENDING` (58) | `be0b763218a0860d...` |
| **P3** | `oc` | Coastal Oil Spill | 2019-01-05T04:00:43Z | `S1A_IW_GRDH_1SDV_20190105T040043_20190105T040108_025337_02CDDA_FAEC.SAFE` | `..._02CDDA_7F3C_COG` | `TRUE` | `sentinel-1a` | `DESCENDING` (65) | `64524e5df9604dea...` |

### 2.1 Provenance Uniqueness & Zero Mosaicking Ambiguity
- **Catalog Uniqueness Rule**: Exact product provenance is established via the official CDSE Catalog / STAC API (`https://stac.dataspace.copernicus.eu/v1/search`), where spatial intersection and the exact 25-second acquisition window resolve to **exactly ONE Sentinel-1 physical scene** (`multiple_possible_matches = 0`).
- **Process API Datasource Identifier Semantics**: The Process API `input.data[].id` field is a user-assigned datasource alias (e.g. `"s1grd"`), NOT a physical Sentinel-1 product ID. Process API queries retrieve the scene by temporal filtering (`timeRange: {"from": exact_start, "to": exact_stop}`) and spatial bounding box. Because Catalog uniqueness proves that only one acquisition exists in that 25-second interval over that bounding box, mosaicking ambiguity is `FALSE`.

### 2.2 Processing Contract Semantics & Parameter Pinning
- **Active Parameters**:
  - `backCoeff: "SIGMA0_ELLIPSOID"`: Calibrates Level-1 GRD DN to linear backscatter intensity relative to the WGS84 ellipsoid.
  - `orthorectify: false`: Terrain correction omitted to preserve the Level-1 GRD slant/ground range geometry consistent with marine SAR standards.
  - `upsampling: "NEAREST"`: Controls interpolation from sensor geometry to the requested EPSG:4326 grid. Nearest-neighbor preserves discrete radiometric boundaries and avoids artificial backscatter averaging across slick edges.
- **Inactive / Omitted Parameters**:
  - `downsampling`: Inactive and ignored by the CDSE Process API for Sentinel-1 GRD products. It is omitted from the canonical request.
  - `speckleFilter`: Omission is semantically identical to `{"type": "NONE"}`. Omitted to keep the canonical request strictly limited to operative parameters.
- **Canonical Processing Hash**:
  `PROCESSING_PARAMS_SHA256 = 1fe63856cdfcf07950fba9465dc5e4c1d9ca9102a75c1f21fe61d8e53ed50353`

### 2.3 Bounding Box (AABB) vs Evaluation Domain Contract
- **Rotated Track Geometry**: Sentinel-1's near-polar orbit (inclination $\sim 98.2^\circ$) causes track-aligned rectangular patches to be rotated $\sim 8.2^\circ\text{--}8.5^\circ$ relative to lines of latitude/longitude.
- **Contractual Separation**:
  1. `RETRIEVAL_DOMAIN = DARTIS_AABB`:
     The Process API request defines an **axis-aligned bounding box (AABB)** enclosing the 4 corner coordinates (UL, UR, BR, BL). Ratio of polygon area to AABB area is $74.14\%$ (P1), $74.02\%$ (P2), and $74.18\%$ (P3). The AABB provides the rectangular context necessary for unpadded, continuous $512 \times 512$ tile extraction.
  2. `PRIMARY_EVALUATION_DOMAIN = DARTIS_QUADRILATERAL_FOOTPRINT`:
     Primary lookalike alarm rate (METRIC-L1) and false-positive pixel burden (METRIC-L2) are evaluated strictly inside the DARTIS quadrilateral mask:
     $$\text{primary\_eval\_mask} = (\text{dataMask} == 1) \land (\text{dartis\_polygon\_mask} == 1)$$
     Extra AABB pixels outside the polygon do NOT trigger patch-level false alarms or dilute pixel burden.
  3. `SECONDARY_REPORTING = FULL_AABB_CONTEXT`:
     Unmasked AABB metrics are reported separately as an informational diagnostic of surrounding ocean behavior.

### 2.4 Tile-Window Clamping Forensics vs Smart Expanded AABB
- **Clamped 12-Window Method (Current Code)**:
  - Produces 12 windows ($3 \times 4$ spans) for P1, P2, P3.
  - Unique pixels (1 tile): $81.44\%\text{--}83.36\%$.
  - 2-tile overlap strip: $16.37\%\text{--}18.31\%$.
  - 4-tile corner overlap: $0.25\%\text{--}0.27\%$ (~6,600 to 7,200 pixels).
  - Overlap is normalized via weighted accumulation (`accum_prob / accum_weight`).
- **Smart Expanded AABB Option (Alternative Deterministic Route)**:
  - Requesting an AABB expanded outward to $1536 \times 2048$ (the nearest exact multiples of 512) at the **exact same angular resolution** ($\Delta = 8.9831528e-5^\circ$) produces **exactly 12 non-overlapping tiles** (0% duplicate evaluations, zero boundary blending artifacts).
  - Both routes require exactly 12 model forward passes.
  - **Non-Equivalence Caveat**: The current clamped 12-window route is the established, frozen deterministic inference route. Expanding the retrieval AABB alters spatial context around tile boundaries and shifts tile alignments relative to the clamped scheme. Because CNN receptive fields span hundreds of pixels, the expanded route and the clamped route are **NOT mathematically equivalent**, and the expanded route cannot be assumed to have "zero effect" on primary metrics. One route must be frozen prior to scientific execution and cannot be chosen post-hoc based on model outputs.

---

## 2.5 Raw CDSE COG Architecture vs Process API

> [!IMPORTANT]
> **Raw COG Architecture Distinction:**
> In the raw Copernicus archive on `s3://eodata/`, CDSE serves Sentinel-1 Level-1 GRDH imagery as separate single-band COG files (e.g. `s1a-iw-grd-vh-...-cog.tiff` and `s1a-iw-grd-vv-...-cog.tiff`).
> - **Raw Representation**: The raw COG files contain uncalibrated digital number (DN) amplitude stored as uint16, NOT calibrated sigma0, and NOT sigma0 in dB.
> - **Required Calibration Pipeline**: Using raw COGs directly requires executing the multi-step ESA calibration chain:
>   `raw uint16 DN → Apply ESA LUT (sigma0_linear = DN² / A_sigma²) → 10 * log10 conversion → sigma0 dB (float32) → Stack separate single-band VH/VV rasters`.
> - **Executed Process API Route**: In this physical pilot, the official CDSE Process API was executed with `backCoeff: "SIGMA0_ELLIPSOID"`, `upsampling: "NEAREST"`, performing the ESA sigma0 calibration server-side, followed by local client-side `10 * log10` dB conversion and `[VH, VV]` stacking (enforcing Ch0 = VH as the first channel and Ch1 = VV as the second channel).

---

## 3. Measured Physical Raster Observations (Audit Dimensions A–O)

All values below are **directly measured from returned raster bytes** retrieved from the Copernicus Data Space Ecosystem Process API.

| Audit Dimension | Measured Value — Pilot 1 (P1 `nc`) | Measured Value — Pilot 2 (P2 `nw`) | Measured Value — Pilot 3 (P3 `oc`) | Status |
|---|---|---|---|---|
| **A. Actual Bytes Retrieved** | 16,350,371 bytes (~16.35 MB) | 13,544,550 bytes (~13.54 MB) | 16,874,218 bytes (~16.87 MB) | `BYTE_ACCESS_CONFIRMED` |
| **B. Actual Dtype** | `float32` (IEEE 754 32-bit float) | `float32` | `float32` | `RADIOMETRIC_DOMAIN_CONFIRMED` |
| **C. Dimensions** | Width: 1,779, Height: 1,509, Bands: 3 | Width: 1,771, Height: 1,511, Bands: 3 | Width: 1,745, Height: 1,514, Bands: 3 | `SPATIAL_GRID_COMPATIBLE` |
| **D. Transform (Affine)** | `[8.9808e-5, 0.0, 33.3551, 0.0, -8.9805e-5, 34.7704]` | `[8.9854e-5, 0.0, 31.2896, 0.0, -8.9813e-5, 34.1860]` | `[8.9837e-5, 0.0, 30.0204, 0.0, -8.9839e-5, 31.3631]` | `SPATIAL_GRID_COMPATIBLE` |
| **E. CRS** | `EPSG:4326` (WGS84 geographic 2D) | `EPSG:4326` | `EPSG:4326` | `SPATIAL_GRID_COMPATIBLE` |
| **F. Pixel Spacing (Lat / Lon)** | 9.97 m (lat) / 8.23 m (lon at 34.7°N) | 9.96 m (lat) / 8.29 m (lon at 34.1°N) | 9.96 m (lat) / 8.55 m (lon at 31.3°N) | `SPATIAL_GRID_COMPATIBLE` |
| **G. Angular Resolution Deviation** | 0.0291% vs Trujillo reference | 0.0247% vs Trujillo reference | 0.0082% vs Trujillo reference | `SPATIAL_GRID_COMPATIBLE` |
| **H. dataMask Behavior** | 2,684,511 / 2,684,511 dataMask-valid (100.0%) | 2,675,981 / 2,675,981 dataMask-valid (100.0%) | 2,641,930 / 2,641,930 dataMask-valid (100.0%) | `NODATA_COMPATIBLE` |
| **I. Finite Value Behavior** | All linear pixels finite; floored at −70 dB | All linear pixels finite; floored at −70 dB | All linear pixels finite; floored at −70 dB | `RADIOMETRIC_DOMAIN_CONFIRMED` |
| **J. Actual VH Asset** | Band 1: linear $\sigma^0$ intensity | Band 1: linear $\sigma^0$ intensity | Band 1: linear $\sigma^0$ intensity | `CHANNEL_ORDER_OPERATIONALLY_COMPATIBLE` |
| **K. Actual VV Asset** | Band 2: linear $\sigma^0$ intensity | Band 2: linear $\sigma^0$ intensity | Band 2: linear $\sigma^0$ intensity | `CHANNEL_ORDER_OPERATIONALLY_COMPATIBLE` |
| **L. VH/VV Stacking** | Shape: `(2, 1509, 1779)`, float32 | Shape: `(2, 1511, 1771)`, float32 | Shape: `(2, 1514, 1745)`, float32 | `CHANNEL_ORDER_OPERATIONALLY_COMPATIBLE` |
| **M. $\sigma^0$ Representation** | CDSE returns linear $\sigma^0$ power | CDSE returns linear $\sigma^0$ power | CDSE returns linear $\sigma^0$ power | `RADIOMETRIC_DOMAIN_CONFIRMED` |
| **N. Local dB Conversion** | Applied $10 \cdot \log_{10}(\max(\sigma^0, 10^{-7}))$ | Applied $10 \cdot \log_{10}(\max(\sigma^0, 10^{-7}))$ | Applied $10 \cdot \log_{10}(\max(\sigma^0, 10^{-7}))$ | `RADIOMETRIC_DOMAIN_CONFIRMED` |
| **O. Tileability (512×512)** | 12 clamped windows ($3 \times 4$ spans); 100% pixel coverage | 12 clamped windows ($3 \times 4$ spans); 100% pixel coverage | 12 clamped windows ($3 \times 4$ spans); 100% pixel coverage | `SPATIAL_GRID_COMPATIBLE` |

> [!NOTE]
> **dataMask Semantic Notice (Audit Dimension H):**
> `dataMask == 1` indicates that the pixel lies within the valid Level-1 SAR acquisition swath (0 = nodata, 1 = data). It does **NOT** denote an ocean/water classification. DARTIS patches may contain terrestrial coastal land within valid dataMask regions unless an independent land/sea mask is applied.

---

## 4. Radiometric Distribution Analysis & Low-Value / -70 dB Audit

### 4.1 Measured Backscatter Statistics (Decibels)

| Pilot Scene | Band 1 (Ch0 = VH) Mean ± Std | Band 1 (VH) Min / Max | Band 2 (Ch1 = VV) Mean ± Std | Band 2 (VV) Min / Max | Polarization Delta $\Delta(\text{VV} - \text{VH})$ |
|---|---|---|---|---|---|
| **P1 (`nc`)** | **−40.86 ± 20.61 dB** | −70.00 / +3.73 dB | **−14.40 ± 3.59 dB** | −70.00 / +13.76 dB | **+26.46 dB** (diagnostic) |
| **P2 (`nw`)** | **−55.04 ± 17.52 dB** | −70.00 / −20.30 dB | **−35.04 ± 14.70 dB** | −70.00 / +6.02 dB | **+20.00 dB** (diagnostic) |
| **P3 (`oc`)** | **−35.26 ± 22.23 dB** | −70.00 / +9.18 dB | **−14.92 ± 6.07 dB** | −70.00 / +14.65 dB | **+20.34 dB** (diagnostic) |

### 4.2 Low-Value / -70 dB Epsilon Floor Evidence
1. **Mathematical Definition**: Conversion from linear backscatter intensity to decibels applies:
   $$\sigma^0_{\text{dB}} = 10 \cdot \log_{10}(\max(\sigma^0_{\text{linear}}, 10^{-7}))$$
   where $\epsilon = 10^{-7}$ sets a $-70\text{ dB}$ lower clamp floor.
2. **Trujillo Part I Baseline Evidence**: Audit of all 10,066,329,600 pixels across the 1,200 Trujillo Part I source GeoTIFFs reveals minimum backscatter values reaching **-112.28 dB** (Band 1) and **-114.67 dB** (Band 2), with 98.1% of pixels negative.
3. **Physical SAR Instrument Context**: Sentinel-1 C-band SAR Noise Equivalent Sigma Zero (NESZ) is approximately $-22\text{ dB}$ to $-28\text{ dB}$. A backscatter value of $-70\text{ dB}$ is more than $40\text{ dB}$ below the sensor noise floor.
4. **Normalized Space Mapping & Deterministic Guard**:
   Under frozen EXP-06 normalization:
   - Ch0 (VH): $(-70 - (-33.2323)) / 6.4912 = -5.66\sigma$
   - Ch1 (VV): $(-70 - (-19.9405)) / 4.5308 = -11.05\sigma$
   The $-70\text{ dB}$ floor is a deterministic numerical guard in `linear_to_db()` preventing $\log_{10}(0) = -\infty$. Classification safety from this floor is not independently established; it is a numerical boundary rather than a proven guarantee against false activation.
5. **dataMask Interaction**: Pixels outside the sensor swath (`dataMask == 0`) are explicitly masked to NaN in probability maps and 0 in binary prediction masks.

### 4.3 Scientific Assessment

1. **Observed Polarization Separation (DIAGNOSTIC OBSERVATION ONLY)**: All three pilot scenes display positive $\text{VV} - \text{VH}$ separation ($\Delta \ge 20.0\text{ dB}$), consistent with typical co-pol vs cross-pol marine scattering. This observation serves as diagnostic corroboration for the operational mapping (Ch0=VH, Ch1=VV) but is **not independent proof** of dataset provenance.
2. **Noise Floor Representation**: In open calm water (Pilot 2 `nw`), cross-polarization backscatter approaches the sensor noise floor; mapping non-positive backscatter to the $-70\text{ dB}$ epsilon floor provides numerical stability while preserving valid float32 values for convolution.
3. **Equivalence Disclaimer**:
   > [!IMPORTANT]
   > While the physical backscatter values are in correct decibel units and conform to standard Sentinel-1 Level-1 IPF `SIGMA0_ELLIPSOID` calibration, **exact bitwise or preprocessing equivalence with Trujillo Part I cannot be proven** because the original paper's Data Preparation section is inaccessible (Elsevier paywall) and Trujillo GeoTIFFs lack parent SAFE provenance. Calibration equivalence remains classified as `NOT_PROVEN_WITH_CURRENT_ARTIFACTS` (permanent declarative limitation).

---

## 5. Explicit Physical Compatibility Statuses

- **Byte Access**: `BYTE_ACCESS_CONFIRMED`
- **Radiometric Domain**: `RADIOMETRIC_DOMAIN_CONFIRMED`
- **Spatial Grid**: `SPATIAL_GRID_COMPATIBLE`
- **Nodata Behavior**: `NODATA_COMPATIBLE`
- **Channel Stacking Order**: `CHANNEL_ORDER_OPERATIONALLY_COMPATIBLE`
- **Calibration Equivalence**: `CALIBRATION_EQUIVALENCE_NOT_PROVEN` / `NOT_PROVEN_WITH_CURRENT_ARTIFACTS`
- **Acquisition Provenance**: `EXACT_ACQUISITION_MATCH_CONFIRMED`
- **Evaluation Domain**: `EVALUATION_DOMAIN_CONTRACT_SPECIFIED`

---

## 6. Document Control

- **Version**: 3.4 (Phase 11-R5.5 Final Integrity Micro-Closure)
- **Date**: 2026-09-27
- **Task ID**: `OCEAN-SENTINEL-PHASE11-R5.5-EXP08-LAST-INTEGRITY-MICROCLOSURE`
- **Supersedes**: Version 3.3 (Phase 11-R5.4), Version 3.2 (Phase 11-R5.3), Version 3.1 (Phase 11-R5.2), and Version 3.0 (Phase 11-R5.1)
- **EXECUTION_AUTHORIZED = FALSE**
