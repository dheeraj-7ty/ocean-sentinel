# EXP-08 Corrected Experimental Protocol — Version 3.5 (Final Corrective Closure V2)

**Document ID:** `EXP08_CORRECTED_PROTOCOL_V3_5`
**Supersedes:** `EXP08_CORRECTED_PROTOCOL_V3_4` (Phase 11-R5.4), `EXP08_CORRECTED_PROTOCOL_V3_3` (Phase 11-R5.3), and earlier versions
**Task ID:** OCEAN-SENTINEL-FINAL-EXP08-CORRECTIVE-CLOSURE-V2
**Date:** 2026-09-27
**Status:** FROZEN — DESIGN ONLY — NOT AUTHORIZED FOR SCIENTIFIC EXECUTION
**Protocol Gate:** READY_FOR_EXPLICIT_CAO_HUMAN_AUTHORIZATION (see §17)
**Authority:** ChatGPT (CAO) / Human (Final Approval)
**Worker:** AG (Antigravity IDE 2.0)

---

> [!IMPORTANT]
> **EXECUTION_AUTHORIZED = FALSE**
> This document defines the fully reconciled scientific protocol for EXP-08. It does NOT authorize execution. Scientific execution requires separate explicit CAO + Human authorization, contingent on ALL prerequisites in §17 being resolved.

---

## 1. Scientific Question

> "How often does the frozen EXP-06 binary oil proposal system activate on documented DARTIS Eastern Mediterranean lookalike patches (CDSE-processed Sentinel-1 GRD data represented on the frozen Trujillo angular storage grid), and what oil-patch activation rate does the frozen system exhibit on genuine oil patches from the same external dataset — under the frozen inference contract, without threshold adjustment?"

This is a **hard-negative / external-generalization diagnostic evaluation**.

**This is explicitly NOT:**
- A segmentation benchmark (DARTIS has no pixel masks)
- A supervised lookalike detection experiment (model was not trained for lookalike classification)
- A threshold calibration exercise (τ = 0.22 is frozen)
- A training population audit

---

## 2. Primary Acquisition Route

**ROUTE B (CDSE reconstruction) is the ONLY scientifically valid route for EXP-08.**

Route A (PANGAEA JPEG patches) is incompatible with EXP-06's input contract on two independent grounds:
1. **Encoding**: 8-bit normalized JPEG (lossy, 0–255, VV channel only) ≠ float32 calibrated σ⁰ dB (two channels)
2. **Radiometry**: Unknown normalization pipeline applied during PANGAEA packaging; inverse cannot be reliably estimated

Route A documentation (Phase 11-R2 §6) is retained as a historical note only. It does not constitute an alternative evaluation path for EXP-08.

---

## 3. DARTIS Entity Ontology (Forensically Established)

**Source:** Direct inspection of `data/metadata/yang_singha_2025/data_matrix.tab` (Phase 11-R3).

### 3.1 Schema

`data_matrix.tab` is a 31-column TSV with a PANGAEA header block (lines 1–49) followed by 5,515 data rows (lines 50–5564).

| Column | Name | Description |
|---|---|---|
| Col 0 | subset | `oc`, `ow`, `nc`, `nw` |
| Col 1 | jpg_file | JPEG patch filename (PATCH identifier for oil; RECORD identifier for no-oil) |
| Col 2 | xml_file | XML annotation file (populated for oil patches; empty string for no-oil) |
| Col 3 | tag | Unique annotation record ID (`{subset}-{patch_num:04d}-{obj_num:02d}-{seq:06d}`) |
| Col 4 | patch_name | Tracing key: `S1_{datetime}_{polarization}_{tile_index}` |
| Col 5–6 | start_time / end_time | Acquisition UTC timestamps |
| Col 7 | Sentinel_ID | Full Sentinel-1 SAFE product ID (may contain semicolons for boundary slices) |
| Col 8–9 | patch_width / patch_height | Patch dimensions in pixels |
| Col 10–17 | patch_*_lon/lat | Four geographic corners of the patch (WGS84 degrees) |
| Col 18–25 | obj_*_lon/lat | Four geographic corners of the annotated oil object (oil subsets only) |
| Col 26–29 | obj_patchloc_* | Pixel coordinates of object bounding box within the patch |
| Col 30 | label_size | Annotated object size in pixels |

### 3.2 Entity Definitions and Verified Counts

| Entity | Definition | Verified Count |
|---|---|---|
| **ANNOTATION_RECORD** | One row in data_matrix.tab; uniquely identified by `tag`. | **5,515** (total rows) |
| **PATCH** | One unique image file (`jpg_file`). For oil: may contain ≥1 oil objects. For no-oil: one patch per record. | **3,655** unique (1,365 oil + 2,290 no-oil) |
| **OBJECT** | One annotated slick or lookalike entity; for oil subsets corresponds to one row; for no-oil: N/A (no object-level annotations). | **3,225** oil objects (oc+ow record total); no individual no-oil object annotations |
| **SCENE** | One unique Sentinel-1 SAFE product (Sentinel_ID after semicolon-splitting). | **1,063** unique scenes |

### 3.3 Subset Breakdown (Verified)

| Subset | Description | Annotation Records | Unique Patches (jpg) | Unique Scenes |
|---|---|---|---|---|
| `ow` | Oil spill, open water | 2,284 | 990 | 451 |
| `oc` | Oil spill, coastal | 941 | 375 | 288 |
| `nw` | No-oil/lookalike, open water | 1,939 | 1,939 | 684 |
| `nc` | No-oil/lookalike, coastal | 351 | 351 | 293 |
| **Total oil** | — | **3,225** | **1,365** | — |
| **Total no-oil** | — | **2,290** | **2,290** | — |
| **TOTAL** | — | **5,515** | **3,655** | **1,063** |

**Cross-checks:**
- 941 + 2,284 = 3,225 ✓ (oil annotation records = oil object count)
- 351 + 1,939 = 2,290 ✓ (no-oil annotation records = no-oil patch count)
- 3,225 + 2,290 = 5,515 ✓ (total records)
- Oil patches (1,365) < oil records (3,225): 724 oil patches contain >1 annotated object

### 3.4 Critical Entity-Semantic Clarification

The 5,515 record total mixes two incompatible entity types:
- Oil-side rows = **oil objects** (multiple rows per oil patch possible)
- No-oil-side rows = **no-oil patches** (exactly one row per patch)

**5,515 is the annotation record count. It is NOT a patch count, object count, or valid scientific denominator for any EXP-08 metric.**

---

## 4. DARTIS Temporal Coverage (Verified)

| Year | Records | Notes |
|---|---|---|
| **2019** | **5,515** | All records |

**The "2018 records" claim in Phase 11-R2 is SUPERSEDED.** Direct inspection of all start_time fields in data_matrix.tab shows all 5,515 records have timestamps in 2019. No 2018 records exist. This reconciles with the dataset description: "observed from Sentinel-1 SAR in 2019."

---

## 5. DARTIS Geographic Coverage (Verified)

From data_matrix.tab column patch_ul_lon/patch_ul_lat:
- **Longitude range:** 27.1461°E to 36.0836°E
- **Latitude range:** 29.2992°N to 36.3484°N

This is entirely within the **Eastern Mediterranean Sea** (approximately between the coasts of Israel, Cyprus, Greece, and Egypt). There is no ambiguity about this geographic domain.

---

## 6. Trujillo Training Data Geographic Reality (Verified — CORRECTS PRIOR REPORTS)

> [!WARNING]
> Prior reports (Phase 11-R2 and earlier) described EXP-06 training geography as "Gulf of Mexico and Caribbean." This is **PARTIALLY INCORRECT.** Direct rasterio inspection of the 1,200 Trujillo Oil GeoTIFFs reveals a multi-ocean-basin dataset.

**Full census — all 1,200 Trujillo Oil GeoTIFFs (Phase 11-R3, rasterio centroid classification):**

| Ocean Basin | Patches | Share |
|---|---|---|
| Gulf of Mexico / Caribbean | 397 | 33.1% |
| **Eastern Mediterranean** | **254** | **21.2%** |
| W. Mediterranean / Iberian | 141 | 11.8% |
| North Sea / NW Europe | 77 | 6.4% |
| Indian Ocean / SE Asia | ~138 | ~11.5% |
| Red Sea / Arabian Sea | ~61 | ~5.1% |
| East Africa / Indonesia | ~69 | ~5.7% |
| East Asia (Japan/Korea) | ~5 | ~0.4% |
| Other / unclassified | ~58 | ~4.8% |
| **TOTAL** | **1,200** | **100%** |

*Overall lon range: −95.16°E to +130.21°E; lat range: −8.07°N to +61.36°N*

Key individual patches:
- `00000.tif` → lon 3.97–4.15, lat 55.15–55.33 → **North Sea (Netherlands coastal)**
- `00582.tif` → lon 98.24–98.42, lat 4.50–4.68 → **Strait of Malacca / SE Asia**
- `01335.tif` → lon −89.15 to −88.97, lat 28.79–28.97 → **Gulf of Mexico**
- `01339.tif` → lon 30.63–30.81, lat 32.09–32.27 → **Eastern Mediterranean**

**Corrected Trujillo geographic description (authoritative source: `docs/dataset-reconnaissance.md` §2):**
> "Gulf of Mexico, Caribbean, Global" — the Trujillo dataset spans multiple ocean basins globally.

**Implication for spatial independence:**
**254 of 1,200 Trujillo Oil source patches (21.2%) are in the Eastern Mediterranean geographic domain** — the same region as all DARTIS patches. Crucially, the 1,200 Trujillo Part I rasters are split across three partitions:
- **EXP-06 Train:** 840 source patches (13,440 tiles)
- **Validation:** 180 source patches (2,880 tiles)
- **Test:** 180 source patches (2,880 tiles)

Geographic separation between Trujillo and DARTIS is NOT universal. The "2,468 overlap / 3,047 zero-overlap" result (EXTERNAL_VALIDATION_READINESS.md §3.1) is therefore **plausibly correct geographically** — but uses a MIXED-ENTITY denominator (5,515 records = oil objects + no-oil patches) and has been superseded by forensic recomputation.

---

## 7. Spatial Geometry & Footprint Audit (Verified)

### 7.1 Geometry Semantics (R4 Implementation Authority)

The spatial overlap calculation between DARTIS and Trujillo raster footprints adheres to the following exact geometric definitions:
- **DARTIS Patch Geometry:** Rotated quadrilateral footprint (`shapely.geometry.Polygon` formed from the 4 reported corner coordinates: `[UpperLeft, UpperRight, BottomRight, BottomLeft]`, tilted $\sim 8.5^\circ$ according to Sentinel-1 orbit inclination $\sim 98.2^\circ$).
- **Trujillo Raster Extent Geometry:** Axis-aligned bounding extent (`shapely.geometry.box` constructed from `rasterio.bounds` of each GeoTIFF).
- **Intersection Metric:** Exact planar polygon-polygon geometric intersection (`dartis_poly.intersects(trujillo_extent_box)`).

> [!NOTE]
> Geometric intersection does NOT imply statistical dependence, and geometric non-intersection does NOT prove statistical independence.

### 7.2 Source Footprint vs Training Footprint Disambiguation

To avoid conflating geographic co-location with training contamination, EXP-08 explicitly separates two footprint reference domains:

| Footprint Concept | Description | No-Oil Overlap (of 2,290) | Oil Overlap (of 1,365) |
|---|---|---|---|
| **A. `TRUJILLO_PART_I_SOURCE_FOOTPRINTS`** | All 1,200 Part I source GeoTIFF footprints (Train + Val + Test) | **789 (34.45%)** intersect<br>**1,501 (65.55%)** zero intersection | **712 (52.16%)** intersect<br>**653 (47.84%)** zero intersection |
| **B. `EXP06_TRAINING_SOURCE_FOOTPRINTS`** | Only 840 source patches assigned to the EXP-06 TRAIN split | **441 (19.26%)** intersect<br>**1,849 (80.74%)** zero intersection | **399 (29.23%)** intersect<br>**966 (70.77%)** zero intersection |

All live documents and analyses must distinguish `SOURCE_FOOTPRINT_OVERLAP` (against all 1,200 rasters) from `TRAINING_SOURCE_FOOTPRINT_OVERLAP` (against the 840 actual training rasters).

| Audit Dimension | Finding | Status |
|---|---|---|
| CRS — DARTIS | WGS84 EPSG:4326 (degrees); confirmed from column values: lon 27–36°E, lat 29–37°N | VERIFIED |
| CRS — Trujillo rasters | EPSG:4326 (from rasterio: `crs=EPSG:4326`); spatial_split_manifest.json field `crs: "EPSG:4326"` | VERIFIED |
| CRS compatibility | Both datasets use EPSG:4326; geometric intersection in degree units is valid | VERIFIED |
| Axis order | data_matrix.tab explicitly labels columns as `Longitude` and `Latitude` in order; corner coordinates confirmed against abstract (lon ~33°E, lat ~33°N = Eastern Med) | VERIFIED |
| Geographic reality | **Trujillo is multi-basin global (all 1,200 patches):** 397 Gulf of Mexico/Caribbean (33.1%), **254 Eastern Mediterranean (21.2%)**, 141 W. Mediterranean (11.8%), 77 North Sea (6.4%), ~138 Indian Ocean/SE Asia (11.5%), rest scattered. DARTIS is exclusively Eastern Mediterranean. | VERIFIED (full census) |
| Prior 2468/3047 denominator validity | **INVALID** — denominator of 5,515 mixes oil-object records and no-oil-patch records | MARKED INVALID |
| Prior 3047 "zero-overlap" subset | **SUPERSEDED / UNTRUSTED** — must be recomputed against correct 2,290 no-oil patch footprints | SUPERSEDED |

---

## 8. CDSE Resolution & Acquisition Provenance Contract (Corrected)

| Claim / Dimension | Correct Wording / Finding | Status |
|---|---|---|
| "100% of DARTIS Sentinel_IDs resolvable" | **SUPERSEDED** — this overstates scope | SUPERSEDED |
| Correct resolution statement | "40/40 stratified DARTIS→CDSE sampled scenes resolved; 0 failures, 0 not-found, 0 API errors (cdse_validation_report.json, 2026-09-05)" | VERIFIED |
| Exact classification | 40/40 as `MATCH_WITH_METADATA_DIFFERENCE` — same physical observation, CDSE STAC uses `_COG` suffix | VERIFIED |
| Polarizations confirmed | VV and VH both present in matched CDSE products | VERIFIED |
| Patch enclosed in footprint | `patch_enclosed_in_footprint: true` for all 40 sampled records | VERIFIED |
| Catalog coverage | 40 of 1,063 unique scenes tested (3.8%); full catalog resolution unverified | VERIFIED_WITH_LIMITATIONS |
| **API Semantic Rule** | Process API `input.data[].id` is a **datasource identifier / alias** (e.g. `"s1grd"`), NOT an individual Sentinel-1 product selector. | VERIFIED |
| **Exact Physical Scene Identity** | Established via the official **CDSE Catalog API** using spatio-temporal restriction (exact 25-second SAFE acquisition window + patch bbox + IW mode + DV polarization + orbit direction). In Phase 11-R5.4 audit, exactly **1 physical acquisition** exists for each pilot scene (`multiple_possible_matches = 0`). | VERIFIED |

---

## 9. CDSE Radiometric & Preprocessing Contract (Forensically Verified)

> [!WARNING]
> The Phase 11-R2 claim "Original Sentinel-1 format = calibrated float32 σ⁰ dB" is **INCORRECT AND SUPERSEDED.**

### 9.1 Processing Parameter Semantics (R5.4 Audit)

The CDSE Process API payload for Sentinel-1 GRD adheres to the following exact semantic rules:
- **`upsampling: "NEAREST"`**: Active operative parameter controlling interpolation onto the requested $\Delta \text{deg} = 8.983152841195215 \times 10^{-5}$ degree grid.
- **`downsampling`**: Ignored / inactive in CDSE Sentinel-1 GRD processing; omitted from canonical payload.
- **`speckleFilter`**: Omitted from canonical payload, which is semantically equivalent to `{"type": "NONE"}`.
- **Active Operative Parameters:**
  ```json
  {
    "backCoeff": "SIGMA0_ELLIPSOID",
    "orthorectify": false,
    "upsampling": "NEAREST"
  }
  ```
- **Canonical Processing Hash:** `PROCESSING_PARAMS_SHA256 = 1fe63856cdfcf07950fba9465dc5e4c1d9ca9102a75c1f21fe61d8e53ed50353`.

### 9.2 Radiometric Processing Chain

```
DARTIS Sentinel_ID
  → CDSE Catalog API spatio-temporal lookup (exact 25-s window, uniqueness verified: 1:1)
  → CDSE Process API (type: "sentinel-1-grd", SIGMA0_ELLIPSOID, upsampling: NEAREST)
  → Linear power intensity float32 GeoTIFF (EPSG:4326, 8.98315e-5° cell size)
  → Local explicit dB conversion: 10 * log10(max(sigma0_linear, 1e-7)) = σ⁰_dB
  → Stacking: Ch0 = VH, Ch1 = VV (calibrated dB; see §10)
  → Z-score normalization with Mapping A constants
      (Ch0: μ=−33.2323 dB, σ=6.4912 dB)
      (Ch1: μ=−19.9405 dB, σ=4.5308 dB)
  → Frozen EXP-06 inference forward pass (ResNet34UNet, τ=0.22)
```

### 9.3 Low-Value / -70 dB Linear Sigma0 Handling Evidence

The local conversion $10 \cdot \log_{10}(\max(\sigma^0, 10^{-7}))$ imposes a $-70\text{ dB}$ floor. This floor is a **deterministic numerical guard only** — it prevents $\log_{10}(0) = -\infty$ when CDSE linear backscatter values are zero or non-positive inside `dataMask == 1`.

> [!CAUTION]
> **DO NOT interpret the -70 dB floor as a physical classification guarantee.** The statements that -70 dB "represents total signal extinction" or corresponds to "shadow or extreme specular reflection" are physical interpretations of specific ocean targets that are NOT established from current EXP-08 artifacts and must NOT be asserted.

Forensic evidence on numerical compatibility with the frozen EXP-06 input contract:
1. **Trujillo Pixel Range (Numerical Only):** Dataset audit of 10.06 billion pixels across 1,200 Trujillo Part I rasters confirmed 100% finite dB values with minimums of $-112.28\text{ dB}$ (Band 1) and $-114.67\text{ dB}$ (Band 2). This establishes that Trujillo training data included deeply negative dB values, but NOT that -70 dB CDSE pixels are harmless.
2. **NESZ Context (Descriptive, Not Safety Proof):** Noise Equivalent Sigma Zero (NESZ) for Sentinel-1 IW mode is approximately $-22$ to $-28\text{ dB}$. A floored value of $-70\text{ dB}$ is $>40\text{ dB}$ below this floor. This is a descriptive fact about the instrument noise context; it does NOT constitute proof that floored pixels cannot cause false activation in the frozen model.
3. **Numerical Guard Semantics & Training Trace:** Neither the Trujillo training loader (`TrujilloTileDataset`) nor the frozen inference preprocessor (`preprocess_sar`) applies a $-70\text{ dB}$ clamp on input rasters; Trujillo source GeoTIFFs were distributed already in decibels. The $-70\text{ dB}$ floor ($\epsilon = 10^{-7}$) exists strictly as a deterministic numerical guard in `linear_to_db()` to prevent $\log_{10}(0) = -\infty$. While $-70\text{ dB}$ maps to deeply negative normalized Z-scores ($-5.66\sigma$ for VH, $-11.05\sigma$ for VV), **classification safety from this floor is not independently established** and must not be claimed.
4. **DataMask Distinction:** Pixels with valid sensor signal have `dataMask == 1`. Non-positive linear power values inside `dataMask == 1` are clamped to $-70\text{ dB}$. Pixels with `dataMask == 0` (outside the Level-1 swath) are explicitly masked as invalid and excluded from evaluation. These are independent pixel categories.

**Compatibility prerequisites:**
1. **Trujillo Numerical Equivalence:** `NOT_PROVEN_WITH_CURRENT_ARTIFACTS` (permanent declarative limitation; Trujillo rasters stripped parent SAFE names and timestamps).
2. **Channel ordering:** EXP-06 operational contract specifies Ch0 = VH, Ch1 = VV (see §10).
3. **Nodata convention:** CDSE nodata semantics verified compatible with `load_and_validate_sar_raster()`.
4. **Resolution and projection:** EPSG:4326, $\Delta \text{deg} = 8.983152841195215 \times 10^{-5}$ degrees.

---

## 10. EXP-06 Channel Mapping Status (MATERIAL PREREQUISITE)

### 10.1 Ontological Separation: Source Truth vs Operational Contract

A critical distinction must be maintained between the original dataset's source provenance and the model's operational inference contract:

| Dimension | Scope | Current Evidence | Status |
|---|---|---|---|
| **A. Dataset Source-Truth** | Original Trujillo GeoTIFF files and published record | • Embedded TIFF metadata has no band labels (`descriptions = (None, None)`).<br>• Zenodo note lists `(VV, VH)` as English enumeration of dual-pol presence, not band indices.<br>• Trujillo 2024 paper §Data Preparation is inaccessible under publisher paywall.<br>• Canonical dataset metadata records `polarization_mapping: UNKNOWN`. | **UNKNOWN / UNVERIFIED AT SOURCE**<br>*(Do NOT claim Trujillo dataset officially proves Band 1=VH, Band 2=VV)* |
| **B. EXP-06 Operational Contract** | Model code and normalization binding | • `src/ocean_sentinel/inference.py` line 48 explicitly documents: `Mapping A Normalization Constants (Cross-Pol VH, Co-Pol VV in dB)`.<br>• Ch0 mean/std (−33.2323 dB / 6.4912 dB) is tied to the 1st normalization channel.<br>• Ch1 mean/std (−19.9405 dB / 4.5308 dB) is tied to the 2nd normalization channel.<br>• Full 1,200-patch census corroborates this (B1 mean −33.158 dB, B2 mean −19.884 dB; B1 < B2 in 100% of patches). | **VERIFIED_WITH_LIMITATIONS**<br>*(Operational contract establishes Ch0 = VH, Ch1 = VV for model input)* |

### 10.2 Synthesis and Blocking Status

1. **Operational Input Contract**: EXP-06 expects Ch0 = VH (Cross-Pol) and Ch1 = VV (Co-Pol) in calibrated dB. When ingesting separate CDSE GRD assets (`vh` and `vv`), they must be stacked in this explicit order: `[vh, vv]` → `(2, H, W)`.
2. **Declared Limitation**: Because the original Trujillo paper's Data Preparation section cannot be inspected directly due to the publisher paywall, the source dataset provenance cannot be independently verified from the primary publication. This is a known, pre-declared limitation (`VERIFIED_WITH_LIMITATIONS`), not unreserved source truth.
3. **Prerequisite Resolution**: The operational input contract is sufficiently established to construct the CDSE ingestion pipeline deterministically without ambiguity. However, scientific execution remains blocked (`EXECUTION_AUTHORIZED = FALSE`) until all physical prerequisites and CAO/Human authorizations are satisfied.

---

## 11. EXP-06 Inference Contract (Forensically Verified)

**Source:** Direct inspection of `src/ocean_sentinel/inference.py` (Phase 11-R3).

| Contract Element | Specification | Evidence |
|---|---|---|
| Input | 2-band float32 GeoTIFF, EPSG:4326 | `load_and_validate_sar_raster()` L209: `if count != 2: raise InputValidationError` |
| Normalization | Z-score: Ch0 (μ=−33.2323, σ=6.4912), Ch1 (μ=−19.9405, σ=4.5308); invalid pixels imputed to 0.0 | `preprocess_sar()` L308–315 |
| Tile size | 512×512 pixels (configurable; default used in EXP-06) | `DEFAULT_TILE_SIZE = 512` L52 |
| Overlap (default) | 0 pixels | `predict_sar_image()` L681 `overlap=overlap` default |
| Blending (no-overlap) | Uniform weight (ones); no Bartlett taper when overlap=0 | `create_blend_weight_window()` L384: `if not blend: return np.ones(...)` |
| Reconstruction | Weighted accumulation + normalization by cumulative weight | `reconstruct_prediction()` L484–489 |
| Sigmoid | Applied during forward pass: `probs = torch.sigmoid(logits)` | `predict_tiles()` L437 |
| Thresholding | `valid_oil = (prob_map >= threshold) & validity_mask` | `reconstruct_prediction()` L496 |
| Threshold value (frozen) | τ = 0.22 | `DEFAULT_THRESHOLD = 0.22` L53 |
| Output | `probability_map` (float32 H×W, NaN for invalid), `prediction_mask` (uint8 H×W, {0,1}) | `InferenceResult` L88–91 |
| Nodata handling | Invalid pixels: NaN in probability map; 0 in prediction mask | L492: `prob_map[~validity_mask] = np.nan`; L497: only `valid_oil` pixels get mask=1 |

### 11.1 Patch Activation — Formal Definition

For EXP-08, **patch activation** is defined as:

> "EXP-06 produces at least one pixel in the reconstructed probability map satisfying `prob_map[row, col] >= 0.22 AND validity_mask[row, col] == True`, for any (row, col) within the patch footprint."

Equivalently: `any(prediction_mask == 1)` over valid pixels.

This definition follows directly from `reconstruct_prediction()` L496 and is the only definition consistent with the frozen inference contract.

---

## 12. EXP-08 Population Definition (Revised)

### 12.1 Primary Evaluation Population

**LOOKALIKE HARD-NEGATIVE POPULATION:**

| Property | Value |
|---|---|
| Entity type | DARTIS no-oil patches (unique `jpg_file` in `nc` and `nw` subsets) |
| Count | **2,290 unique patches** |
| Subset breakdown | `nw`: 1,939 patches; `nc`: 351 patches |
| Geographic domain | Eastern Mediterranean: lon 27.1–36.1°E, lat 29.3–36.4°N |
| Temporal range | 2019 acquisitions only |
| Annotation type | No pixel-level annotations; no bounding boxes for no-oil patches (XML field empty) |
| Parent scenes | 869 unique Sentinel_IDs (joint `nc`+`nw`, from provenance manifest) |

> [!CAUTION]
> The previously claimed "3,047 zero-overlap patches" used an invalid mixed-entity denominator (5,515). **This figure is SUPERSEDED** by the definitive Phase 11-R4 recomputation on consistent entities (`data/metadata/exp08_spatial_overlap_r4.json`): **1,501 of 2,290 no-oil patches (65.5%)** have zero Trujillo footprint overlap.

**OIL PATCH ACTIVATION POPULATION:**

| Property | Value |
|---|---|
| Entity type | DARTIS oil patches (unique `jpg_file` in `oc` and `ow` subsets) |
| Count | **1,365 unique patches** |
| Subset breakdown | `ow`: 990 patches; `oc`: 375 patches |
| Annotated oil objects | 3,225 individual objects (across 1,365 patches; 724 patches have >1 object) |

### 12.2 Pre-Registered Analysis Populations & Stratification Plan

To address the forensically established spatial footprint overlap (Phase 11-R4: 789/2,290 no-oil patches = 34.5%; 712/1,365 oil patches = 52.2%) without conflating geometric intersection with statistical dependence, EXP-08 pre-registers the following analytical handling rules:

1. **Stratum 1 (Primary Generalization Benchmark — Spatially Disjoint)**:
   - **Population:** **1,501 unique no-oil patches (65.5%)** whose rotated quadrilateral footprint has ZERO geometric intersection with any Trujillo Part I Oil raster extent geometry (1,849 patches have zero intersection with actual EXP-06 training footprints).
   - **Role:** Primary evaluation benchmark for hard-negative lookalike activation, demonstrating zero geometric intersection with the inspected Trujillo source raster footprints under the defined rotated quadrilateral vs raster extent geometry (absence of footprint intersection does NOT imply proven statistical independence).
   - **Parent Scenes:** 719 unique Sentinel-1 parent scenes.
   - **Statistical Unit:** Scene-clustered alarm rate across the corresponding unique parent scenes.

2. **Stratum 2 (Geographic Hotspot Sensitivity Cohort — Spatially Co-located)**:
   - **Population:** **789 unique no-oil patches (34.5%)** whose rotated quadrilateral footprint geometrically intersects ≥1 Trujillo Part I Oil raster extent geometry (441 intersect actual EXP-06 training footprints).
   - **Role:** Sensitivity cohort to evaluate whether geographic co-location in the Eastern Mediterranean basin alters model behavior relative to the disjoint stratum.
   - **Parent Scenes:** 447 unique Sentinel-1 parent scenes.
   - **Reporting:** Reported separately as a diagnostic sensitivity check; not pooled without reporting the decomposed strata.

3. **Cross-Stratum Scene Clustering Interaction (R5.4 Finding)**:
   - **Shared Parent Scenes:** Exactly **297 parent Sentinel-1 scenes (34.2% of the 869 unique no-oil scenes)** contribute patches to BOTH Stratum 1 (disjoint) and Stratum 2 (co-located).
   - **Statistical Constraint:** Stratum 1 and Stratum 2 CANNOT be treated as independent scene populations. Any statistical comparison between strata must utilize paired cluster-aware modeling (e.g. generalized estimating equations with exchangeable working correlation or paired cluster bootstrap) rather than two-sample independent tests.

4. **Oil Patch Activation Cohorts (Dual Stratification)**:
   - **Disjoint Oil Cohort:** **653 oil patches (47.8%)** with zero Trujillo source footprint overlap (966 patches zero overlap with training footprints); spans 457 parent scenes.
   - **Co-located Oil Cohort:** **712 oil patches (52.2%)** with Trujillo source footprint overlap (399 patches overlap with training footprints); spans 422 parent scenes.
   - **Shared Parent Scenes:** 140 parent scenes contribute to both oil strata.
   - **Combined Oil Cohort:** All **1,365 unique oil patches** (3,225 annotated objects across 739 scenes).

All reporting preserves:
- Patch-level descriptive metrics (METRIC-L1, METRIC-O1)
- Scene as primary statistical unit (METRIC-L3)
- Scene-clustered summaries
- Strict prohibition of unclustered confidence intervals

### 12.3 Excluded Population

| Excluded | Reason |
|---|---|
| PANGAEA JPEG patches (Route A) | Radiometric domain mismatch; VV-only; 8-bit lossy encoding |
| Patches requiring non-existing physical imagery | Only patches resolvable via CDSE Route B can be evaluated |
| Part III holdout data | Absolute firewall; NEVER accessed |

---

## 13. EXP-08 Metrics (Corrected and Final)

### 13.1 Prohibitions

| Prohibited Metric | Reason |
|---|---|
| Segmentation IoU | No pixel masks in DARTIS |
| Segmentation Dice | No pixel masks in DARTIS |
| Filled-bounding-box IoU labeled as "segmentation IoU" | Fabricates ground truth |
| Threshold tuning on DARTIS | τ = 0.22 is frozen |
| "Lookalike IoU" as success metric | High oil overlap with lookalike = false activation (inverted) |
| 50% or 30% threshold as scientific truth | No published basis |
| 5,515 as population denominator | Mixed entity types |
| "Pipeline independence" as statistical independence | Institutional separation ≠ statistical independence |

### 13.1b Evaluation Domain Contract (DARTIS Quadrilateral vs AABB)

- **RETRIEVAL_DOMAIN:** `DARTIS AABB` (Axis-Aligned Bounding Box)
  - The CDSE Process API request defines an **axis-aligned bounding box (AABB)** enclosing the 4 DARTIS patch corner coordinates (UL, UR, BR, BL).
  - The AABB provides the complete rectangular context required for unpadded, continuous $512 \times 512$ tile extraction and full receptive-field support along patch edges.
- **PRIMARY_EVALUATION_DOMAIN:** `DARTIS QUADRILATERAL FOOTPRINT`
  - DARTIS ground-truth annotations are defined strictly within the rotated quadrilateral footprint (tilted $\sim 8.5^\circ$ due to Sentinel-1 orbit inclination $\sim 98.2^\circ$; polygon-to-AABB area ratio $\sim 74.0\%$).
  - For all primary patch-level metrics (METRIC-L1, METRIC-L2, METRIC-O1, METRIC-O2, METRIC-O3), evaluation is restricted strictly to pixels satisfying:
    $$\text{primary\_eval\_mask} = (\text{dataMask} == 1) \land (\text{dartis\_polygon\_mask} == 1)$$
  - **Executable Implementation:** Implemented in `src/ocean_sentinel/geometry.py`:
    - `create_dartis_polygon_mask(height, width, transform, corners, all_touched=False)`
    - `create_primary_evaluation_mask(height, width, transform, corners, data_mask, all_touched=False)`
    - Rasterization adheres strictly to EPSG:4326, pixel-center rule (`all_touched=False`), closed 5-point ring, and logical AND with `dataMask == 1`.
  - Binary prediction inside evaluation domain:
    $$\text{predicted\_mask\_poly} = (\text{probability\_map} \ge 0.22) \land \text{primary\_eval\_mask}$$
  - Any model activation occurring in the surrounding AABB margin outside the DARTIS polygon does **NOT** trigger a patch-level false alarm or contribute to primary false-positive pixel burden.
- **SECONDARY_REPORTING:** `FULL AABB CONTEXT`
  - Unmasked AABB statistics (METRIC-L1-AABB, METRIC-L2-AABB) are reported separately as an informational diagnostic of surrounding ocean behavior.

### 13.2 Lookalike Hard-Negative Metrics

**METRIC-L1 (Primary): Patch Hard-Negative Activation Rate**
```
Denominator: N_nooil_patches = 2,290 unique no-oil jpg_files
Value: count(patches where any predicted_mask pixel == 1) / 2,290
```

**METRIC-L2: Predicted Oil Area Fraction**
```
Mean oil_pixels / valid_pixels per patch, averaged across 2,290 no-oil patches
```

**METRIC-L3: Scene-Clustered Alarm Rate (Primary clustering unit)**
```
N_scenes_with_any_activation / N_unique_scenes_in_nooil_population
(Corrects for within-scene patch correlation; N_unique_scenes = 869 for full nooil set)
```

**METRIC-L4: Subgroup Stratification**
- METRIC-L1 separately for `nc` (351 patches) and `nw` (1,939 patches)

### 13.3 Oil Patch Activation Metrics

> [!IMPORTANT]
> **METRIC-O1 is NOT conventional recall.** DARTIS does not provide pixel-level oil masks for oil patches. Activation of the model in any predicted-positive pixel within an oil patch does not constitute recovery of a known ground-truth pixel. The preferred name is **Oil-Patch Activation Rate**.

**METRIC-O1 (Primary): Oil-Patch Activation Rate**
```
Estimand: Rate at which the frozen EXP-06 model produces at least one valid
          predicted-positive pixel inside the DARTIS quadrilateral of an oil patch.
Denominator: N_oil_patches = 1,365 unique oil jpg_files
Numerator:   count(oil patches where any predicted_mask pixel == 1 inside primary_eval_mask)
Value: numerator / 1,365
NOT called: "Patch Recall Rate", "Recall", or "Detection Rate" — those terms imply
            pixel-level or object-level ground truth semantics that DARTIS does not provide.
```

**METRIC-O2: Predicted Oil Area Fraction (within oil patches)**
```
Mean of (valid_positive_pixels / valid_eval_mask_pixels) per oil patch,
aggregated across the 1,365 oil patches.
```

**METRIC-O3: Oil-Object Bounding-Box Hit Rate**
```
Estimand: Rate at which any valid predicted-positive pixel intersects an annotated
          oil object's documented axis-aligned bounding box.
Numerator:   count(annotated oil objects where any predicted_mask pixel intersects
             object bounding box AND pixel is inside primary_eval_mask)
Denominator: N_oil_objects = 3,225 annotated objects (across 1,365 oil patches)
Must be labeled: "oil-object bounding-box hit rate" or
                 "prediction-bounding-box overlap rate"
NOT labeled: "segmentation IoU", "segmentation recall", "localization IoU",
             "object detection precision"
```

**METRIC-O4: Subgroup Stratification**
- METRIC-O1 separately for `oc` (375 patches) and `ow` (990 patches)
- Descriptive reporting view only; not an independent inferential estimand unless explicitly justified

### 13.4 Reference Baseline (Descriptive Only — NOT a Hypothesis Test)

| Baseline | Value | Use |
|---|---|---|
| EXP-06 internal clean-water FAR | 0.55% (1,827 empty Trujillo Part I validation tiles at τ=0.22) | Descriptive contextual reference; no equivalence margin defined |
| EXP-06 internal validation IoU | 0.72168 (2,880 Trujillo Part I tiles) | Reference for internal domain performance; NOT comparable to DARTIS metrics |

---

## 14. Statistical Unit, Clustering, and Bootstrap Specification

**Primary statistical unit:** SCENE (parent Sentinel-1 SAFE product).

**Required reporting:**
1. Raw patch-level estimates (METRIC-L1 through L4, METRIC-O1 through O4)
2. Scene-clustered summary (METRIC-L3): one binary alarm indicator per scene
3. Paired cluster-aware modeling for cross-stratum comparisons (due to 297 shared parent scenes between Stratum 1 and Stratum 2)
4. Strict prohibition of unclustered confidence intervals or treating patches as independent observations

**Must NOT claim:** "2,290 independent lookalike observations" — patches from the same parent scene are correlated.

### 14.1 Frozen Cluster Bootstrap Specification (Pre-Declared)

The following cluster bootstrap specification is **frozen prior to scientific execution**. No parameter may be chosen at execution time based on model results.

| Parameter | Value | Rationale |
|---|---|---|
| **Bootstrap method** | Non-parametric cluster bootstrap | Resamples parent scenes (the primary statistical unit) |
| **Resampling unit** | Parent Sentinel-1 SAFE scene | Maintains within-scene patch correlation |
| **Replicate count** | **10,000** | Pre-declared; must not be adjusted after seeing results |
| **Confidence level** | 95% (two-sided percentile CI) | Standard; no Bonferroni correction unless pre-declared |
| **Pre-declared RNG seed** | **`20260927`** | Fixed deterministic seed; must be set before any bootstrap resampling |
| **RNG implementation** | `numpy.random.default_rng(20260927)` | Reproducible across NumPy versions ≥ 1.17 |
| **Seed declaration** | This Protocol V3.5, §14.1 | Seed pre-declared here; NOT generated at execution time |

> [!CAUTION]
> The seed `20260927` was chosen before any model results were seen (date of corrective closure V2). It must NOT be changed after any model forward pass has occurred. If the bootstrap must be re-run for any administrative reason, the same seed must be used.

**For patch-level metrics:** Resample parent scenes; include all eligible/evaluated patches belonging to each resampled scene.

**For cross-stratum comparisons (Stratum 1 vs Stratum 2):** The 297 shared parent scenes must remain jointly represented in both strata's bootstrap replicate. Resample from the 869 unique no-oil parent scenes; each resampled scene contributes its patches to whichever stratum(a) they belong.

**For oil subgroup comparisons (Disjoint vs Co-located oil):** The 140 shared oil parent scenes must likewise remain jointly represented. Resample from the 739 unique oil parent scenes.

**Do NOT use:** IID confidence intervals, GEE (unless pre-declared), any method chosen after results are seen.

---

## 15. Leakage and Independence Status

| Dimension | Status | Basis |
|---|---|---|
| Geographic separation (full) | **NOT UNIVERSAL** | Trujillo has Eastern Mediterranean patches; DARTIS is Eastern Mediterranean |
| Geographic separation (subset) | **VERIFIED for some patches** | 01339.tif (Trujillo) and most DARTIS patches are in different sub-regions |
| Spatial footprint overlap (all 1,200 source rasters) | **RECOMPUTED — R4/R5.4** | 789/2,290 (34.45%) intersect; 1,501/2,290 (65.55%) zero intersection. Intersection ≠ statistical dependence. |
| Spatial footprint overlap (840 training rasters) | **COMPUTED — R5.4** | 441/2,290 (19.26%) intersect; 1,849/2,290 (80.74%) zero intersection. |
| Acquisition-level independence | **NOT DETERMINABLE** | Acquisition-level identity cannot be established from current Trujillo artifacts (stripped SAFE IDs) |
| Temporal independence | **PARTIALLY ESTABLISHED** | DARTIS 2019 verified; Trujillo acquisition chronology is not fully established from current accessible artifacts |
| DARTIS within-scene patch independence | **NO** | Multiple patches from same parent scene are correlated |
| Training contamination from DARTIS | **NONE** | EXP-06 training dataset verified directly from manifest: strictly composed of 13,440 standard tiles + 355 mined negatives from Trujillo Part I. Zero DARTIS data present. Absence is directly evidence-backed. |
| Pipeline/institutional independence | **INSTITUTIONAL ONLY** | Institutional separation does not establish statistical independence without spatial/acquisition analysis |

---

## 16. CDSE Physical Compatibility Pilot & Tiling Forensics (Completed — R5.1–R5.4)

A physical raster compatibility pilot across 3 representative DARTIS parent scenes from CDSE was executed and validated in Phase 11-R5.1 and finalized in R5.2/R5.3/R5.4 (NOT scientific execution; `EXECUTION_AUTHORIZED = FALSE`).
- Verified CDSE Process API GeoTIFF float32 output format
- Verified VV + VH band presence and ordering
- Confirmed linear power units converted locally via $10 \cdot \log_{10}(\max(\sigma^0, 10^{-7}))$ to dB
- Confirmed channel stacking order: Ch0 = VH (Cross-Pol), Ch1 = VV (Co-Pol)
- **Verified spatial grid fidelity**: Output angular cell size requested and verified at $\Delta \text{deg} = 8.983152841195215 \times 10^{-5}$ degrees in EPSG:4326, reproducing the frozen Trujillo TIFF angular storage grid within 0.03% (corresponding to ~9.96m N-S and 8.23–8.55m E-W physical ground spacing at pilot latitudes $31^\circ\text{--}35^\circ\text{N}$, rather than globally isotropic 10m pixels)
- **Clarified resampling semantics**: `LOCAL_RESAMPLING = NONE` (zero client-side interpolation, reprojection, or spatial resizing); `SERVICE_SIDE_GRID_GENERATION = YES` (CDSE Process API generates the requested EPSG:4326 angular grid server-side from Level-1 GRDH source data using `backCoeff: "SIGMA0_ELLIPSOID"`, `orthorectify: "false"`)
- **Pinned service-side upsampling**: Explicitly pinned `upsampling: "NEAREST"`. `downsampling` is omitted from the canonical payload as inactive in CDSE Sentinel-1 GRD processing; `speckleFilter` is omitted as semantically equivalent to `{"type": "NONE"}`. Canonical processing hash: `PROCESSING_PARAMS_SHA256 = 1fe63856...`.
- **Verified exact product provenance**: Confirmed 100% exact observation match between DARTIS SAFE products and CDSE COG products across all 3 pilots (P1: `..._02D7E5_F282_COG`, P2: `..._02CD9D_4F9F_COG`, P3: `..._02CDDA_7F3C_COG`) via CDSE Catalog API spatio-temporal lookup (25-second acquisition windows, platform `sentinel-1a`, orbit direction, and relative orbit). Uniqueness confirmed (`multiple_possible_matches = 0`). Mosaicking ambiguity is `FALSE`.
- **Recorded canonical request hashes**: P1 payload SHA-256 = `9e036058...`, P2 = `be0b7632...`, P3 = `64524e5d...`
- **Verified dataMask semantics**: Evaluated pixels have `dataMask == 1` (valid Level-1 SAR swath footprint); explicitly distinguished from ocean classification (dataMask contains no land/water discrimination).
- **Established evaluation domain contract**: Bounding box (AABB) retrieval enables continuous $512 \times 512$ tile extraction; primary lookalike alarm evaluation is strictly masked to the DARTIS quadrilateral footprint ($\text{primary\_eval\_mask} = (\text{dataMask} == 1) \land (\text{dartis\_polygon\_mask} == 1)$) implemented in `src/ocean_sentinel/geometry.py`.
- **Tile Window Forensics & Options**:
  - *Current Clamped 12-Window Method:* Evaluated `compute_tile_windows(height, width, tile_size=512, overlap=0)` on actual pilot dimensions; edge boundary clamping produces **12 tiles** per scene ($3 \text{ row spans} \times 4 \text{ col spans}$) with 100% pixel coverage across the entire raster, normalized during reconstruction via weighted accumulation (`accum_prob / accum_weight`). Quantitative forensic analysis indicates 81.4%–83.4% unique pixels, 16.4%–18.3% overlap strip pixels (evaluated 2×), and ~0.26% corner pixels (evaluated 4×), giving ~17%–19% duplicated area evaluations.
  - *Smart Expanded AABB Option (Alternative Deterministic Route):* Requesting an expanded retrieval AABB ($1536 \times 2048$, exact multiples of 512 at identical angular grid) requires the exact same 12 model forward passes while eliminating edge clamping duplicates (0% duplicated evaluations). However, the current clamped 12-window route is the established, frozen inference route. Expanding the retrieval AABB alters spatial context and tile boundaries; because CNN receptive fields span hundreds of pixels, the two routes are NOT mathematically equivalent and the expanded route cannot be assumed to have zero effect on primary metrics. One route must be frozen prior to scientific execution.
- **Observed polarization separation**: Observed 20–26 dB VV-VH delta labeled strictly as `DIAGNOSTIC OBSERVATION ONLY`, not proof of channel provenance or calibration equivalence.

No model inference occurred during the pilot. No performance metrics were computed. Complete observations are documented in [`docs/exp08_cdse_physical_compatibility_pilot.md`](file:///d:/Projects/ocean-sentinel/docs/exp08_cdse_physical_compatibility_pilot.md) and [`scratch/cdse_physical_pilot_results_r5_1.json`](file:///d:/Projects/ocean-sentinel/scratch/cdse_physical_pilot_results_r5_1.json).

---

## 17. Prerequisites for Execution Authorization (Protocol Gate)

| Prerequisite | Current Status | Blocker Level |
|---|---|---|
| DARTIS entity ontology established | **VERIFIED** ✓ (§3) | Resolved |
| Valid population denominators defined | **VERIFIED** ✓ (§12) | Resolved |
| Spatial geometry CRS verified | **VERIFIED** ✓ (§7) | Resolved |
| Trujillo geographic reality corrected | **VERIFIED** ✓ (§6) | Resolved |
| CDSE resolution scope corrected | **VERIFIED** ✓ (§8: 40/40 sampled) | Resolved |
| CDSE radiometric contract defined | **VERIFIED** ✓ (§9: calibration chain required) | Resolved |
| Spatial overlap recomputed (all 1,200 source rasters) | **COMPLETED — R4/R5.4** ✓ | Resolved — 789/2,290 no-oil (34.45%); 712/1,365 oil (52.16%) intersect |
| Spatial overlap against 840 training rasters | **COMPLETED — R5.4** ✓ | Resolved — 441/2,290 no-oil (19.26%); 399/1,365 oil (29.23%) intersect |
| R4 overlap geometry semantics | **VERIFIED** ✓ (§7.1) | Resolved — DARTIS rotated polygon vs Trujillo raster extent box |
| Process API `input.data[].id` datasource semantics | **VERIFIED** ✓ (§8) | Resolved — datasource alias, not product selector |
| Exact CDSE acquisition identity | **VERIFIED** ✓ (§8) | Resolved — Catalog API 1:1 match verified across pilot scenes |
| Processing contract semantics | **VERIFIED** ✓ (§9.1) | Resolved — upsampling NEAREST pinned; downsampling & speckleFilter omitted; hash verified |
| **EXP-06 channel mapping (VH/VV) authoritatively verified** | **VERIFIED_WITH_LIMITATIONS** ✓ | Operational contract: Ch0=VH, Ch1=VV (`inference.py` L48 comment + normalization coupling; source truth UNKNOWN at source, see §10 and `docs/exp08_channel_mapping_audit.md`) |
| CDSE radiometric calibration pipeline specified | **VERIFIED** ✓ | CDSE Process API `SIGMA0_ELLIPSOID` → local 10·log10 → dB (see `docs/exp08_cdse_physical_compatibility_pilot.md`) |
| Low-value / -70 dB linear sigma0 handling | **VERIFIED** ✓ (§9.3) | Resolved — deterministic numerical guard in conversion path; classification safety not independently established |
| CDSE calibration equivalence with Trujillo pipeline | **NOT_PROVEN_WITH_CURRENT_ARTIFACTS** | Permanent declarative limitation — stripped source SAFE provenance prevents same-scene validation |
| Physical CDSE compatibility pilot completed | **COMPLETED — R5.1–R5.4** ✓ | Resolved — Trujillo angular grid (8.98315e-5°) pilot across 3 scenes: P1, P2, P3; verified float32, EPSG:4326, 100% dataMask-valid pixels, Ch0=VH/Ch1=VV, 12-tile full coverage with boundary clamping, exact product match confirmed, and zero local resampling (see `docs/exp08_cdse_physical_compatibility_pilot.md`) |
| Executable polygon evaluation mask helper | **VERIFIED** ✓ (§13.1b) | Resolved — implemented and tested in `src/ocean_sentinel/geometry.py` |
| Tile window forensics & options | **VERIFIED** ✓ (§16) | Resolved — clamped 12-window is established frozen route; Smart Expanded AABB formulated as non-equivalent alternative |
| Scene-cluster cross-strata interaction | **VERIFIED** ✓ (§12.2, §14) | Resolved — 297 shared parent scenes quantified; paired cluster requirement established |
| Training contamination from DARTIS | **NONE — EVIDENCE-BACKED** ✓ (§15) | Resolved — EXP-06 training manifest confirms zero DARTIS data |
| EXP-06 checkpoint on-disk SHA-256 verified | **VERIFIED — R4–R5.4** ✓ | B5FFCA... exact match | 

**PROTOCOL GATE: READY_FOR_EXPLICIT_CAO_HUMAN_AUTHORIZATION**

All Phase 11-R3 PENDING/BLOCKING prerequisites and R5/R5.1/R5.2/R5.3/R5.4 spatial/radiometric/provenance/execution-readiness items have been resolved. Remaining pre-declared limitations:
- CDSE calibration bitwise/radiometric equivalence with Trujillo pipeline is `NOT_PROVEN_WITH_CURRENT_ARTIFACTS` (permanent declarative limitation; cannot be proven even during execution without external reference).
- Channel mapping is VERIFIED_WITH_LIMITATIONS (operational contract verified; Trujillo paper §Data Preparation still inaccessible).
- Trujillo acquisition chronology is not fully established from current accessible artifacts.
- Level-1 GRD dataMask defines sensor footprint validity, not land/ocean separation.
- Primary evaluation domain is masked to DARTIS quadrilateral footprint; AABB provides surrounding context (~74% polygon-to-AABB area ratio).
- Cross-stratum comparisons must account for 297 shared parent scenes between Stratum 1 and Stratum 2.

---

## 18. Stopping Rules

1. **Checkpoint hash mismatch:** SHA-256 of `best_model.pt` ≠ `B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF` → STOP immediately.
2. **Channel mapping violation:** Inputs must strictly obey `EXP06_OPERATIONAL_MAPPING` (Ch0 = VH, Ch1 = VV). Feeding unverified, ambiguous, or inverted channels is strictly prohibited → STOP immediately.
3. **CDSE calibration chain not implementable:** STOP; document as a blocking prerequisite.
4. **Patch extraction yields zero valid pixels for >10% of patches:** STOP; report as a format-compatibility failure.

---

## 19. Pre-declared Limitations

1. No pixel-level ground truth in DARTIS: segmentation IoU impossible.
2. DARTIS within-scene patches are NOT statistically independent: confidence intervals require cluster adjustment.
3. Trujillo multi-basin training geography: geographic domain shift vs Eastern Mediterranean cannot be quantified independently of format shift.
4. Calibration equivalence (Trujillo vs CDSE processing): `NOT_PROVEN_WITH_CURRENT_ARTIFACTS` — permanent declarative limitation. Trujillo source GeoTIFFs stripped parent SAFE scene IDs and acquisition timestamps. Numerical equivalence cannot be proven even during authorized execution without an external reference dataset.
5. Channel mapping: VERIFIED_WITH_LIMITATIONS — EXP-06 operational contract establishes Ch0=VH, Ch1=VV (governed by `inference.py` L48 comment and normalization parameter coupling; corroborated by 1,200-patch statistics). Trujillo dataset-source provenance remains UNKNOWN at source because primary paper §Data Preparation is inaccessible (Elsevier paywall).
6. Full CDSE catalog resolution: 40/1,063 scenes explicitly confirmed; the remaining 1,023 are NOT proven to be resolvable — extrapolation from a sample requires caution (see RESEARCH-19 correction).
7. Raw CDSE COG files are NOT calibrated sigma0 dB — they contain raw DN amplitude. A multi-step calibration pipeline (ESA LUT → sigma0_linear → 10·log10) is required before inference.
8. Cross-stratum scene clustering: 297 parent scenes span both Stratum 1 (disjoint) and Stratum 2 (co-located); comparisons must use paired cluster modeling.

---

## 20. Document Control

- **Version:** V3.5 (Final Corrective Closure V2 — OCEAN-SENTINEL-FINAL-EXP08-CORRECTIVE-CLOSURE-V2)
- **Frozen as of:** 2026-10-01
- **Supersedes:** `EXP08_CORRECTED_PROTOCOL_V3_4` (Phase 11-R5.4), `EXP08_CORRECTED_PROTOCOL_V3_3`, `EXP08_CORRECTED_PROTOCOL_V3_2`, `EXP08_CORRECTED_PROTOCOL_V3_1`, and `EXP08_CORRECTED_PROTOCOL_V3`
- **EXECUTION_AUTHORIZED = FALSE**

### 20.1 Version Delta — V3.4 → V3.5

The following normative changes were made. Because they alter the scientific contract, the version was incremented from V3.4 to V3.5.

| Section | Change | Type | Scientific Impact |
|---|---|---|---|
| §9.3 | Removed "total signal extinction" and "shadow or extreme specular reflection" as physical characterizations of -70 dB pixels. Added explicit CAUTION block: -70 dB floor is a numerical guard only; physical-safety claims are not justified. NESZ context reframed as descriptive, not proof. | **Normative** | Eliminates an unjustified physical-safety assertion; does not change the mathematical operation or the frozen inference contract. |
| §13.3 | Renamed METRIC-O1 from "Patch Recall Rate" to **"Oil-Patch Activation Rate"**; added NOTE that DARTIS provides no pixel masks and therefore conventional recall semantics are not applicable. Expanded O3 definition to "Oil-Object Bounding-Box Hit Rate" with explicit NOT-labeled list. | **Normative** | Corrects metric naming to match what is actually measurable given DARTIS ground-truth structure; does not change denominator or computation. |
| §14 | Added **§14.1 Frozen Cluster Bootstrap Specification** with pre-declared seed `20260927` (`numpy.random.default_rng(20260927)`), 10,000 replicates, 95% percentile CI, and explicit resampling rules for shared no-oil and oil parent scenes. | **Normative** | Eliminates all analyst-choice branches from the statistical procedure; seed must not be changed after any model forward pass. |

---

*End of EXP-08 Corrected Protocol V3.5.*
