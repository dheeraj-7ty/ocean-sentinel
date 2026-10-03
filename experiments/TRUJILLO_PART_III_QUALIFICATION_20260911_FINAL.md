# Ocean Sentinel — Authoritative Scientific Dataset Qualification Record: Trujillo Part III

**Document Identifier:** `TRUJILLO_PART_III_QUALIFICATION_20260911_FINAL`  
**Execution Phase:** Phase 4B-3R (Scientific Qualification Reconciliation + Finalization)  
**Dataset Under Audit:** Trujillo Part III (`10.5281/zenodo.13761290`, `02_Test_images_and_ground_truth.7z`)  
**Authority:** Chief Architect Officer (CAO) Mandate  
**Execution Date:** 2026-09-11  
**Baseline Git HEAD:** `542bab19f6f08c9bba8b8762e6480386c8b6026b`  
**Active Git Branch:** `master`  
**ML Forward Passes:** Exactly 0  
**Final Scientific Qualification Status:** **`SCIENTIFIC_QUALIFICATION_CONDITIONAL`**  

---

## 1. Executive Decision

The Trujillo Part III dataset has undergone comprehensive scientific qualification across physical inventory, file pairing, mask encoding, image numerical distributions, geospatial referencing, pipeline compatibility, contamination auditing, and recovery resilience. 

The dataset is qualified as **`SCIENTIFIC_QUALIFICATION_CONDITIONAL`**.

The dataset is physically complete, readable in standard raster containers, and exhibits clean 1-to-1 filename correspondence. However, it cannot be ingested directly into the Ocean Sentinel native inference pipeline without a certified external benchmark adapter due to:
1. Spatial resolution mismatch ($2048 \times 2048$ scene rasters vs. native $512 \times 512$ model patches).
2. Unverified polarization channel mapping and radiometric physical unit metadata in GeoTIFF container headers.
3. Asymmetric georeferencing metadata between image rasters (geographic coordinates) and mask rasters (unreferenced pixel grids).
4. Structural class partitioning into distinct scene directories (`Oil`, `No oil`, `Lookalike`) with 300 all-zero target masks.

---

## 2. Scope and Boundary

This qualification phase was conducted under an absolute scientific firewall:
- **Zero ML Forward Passes:** No machine learning model was trained, evaluated, loaded for inference, or scored.
- **Zero In-Place Transformations:** No source raster was rewritten, reprojected, resampled, normalized, or renamed.
- **Durable Quarantine:** All intermediate calculations and audit records were written exclusively to approved `scratch/` and `experiments/` locations.
- **Separation of Concerns:** Adapter design and evaluation benchmarking are explicitly out of scope for this qualification phase.

---

## 3. Repository State

- **Current Working Directory:** `D:\Projects\ocean-sentinel`
- **Active Branch:** `master`
- **Current Commit Hash (HEAD):** `542bab19f6f08c9bba8b8762e6480386c8b6026b`
- **Staged Changes:** Exactly 0 files
- **Tracked File Modifications:** Exactly 0 files
- **Working Tree State:** Tracked working tree clean; untracked files strictly confined to experimental markdown reports, frozen checkpoints, and uv lockfile.

---

## 4. Physical Dataset State

### 4.1 Canonical Archive Integrity
- **Archive Path:** `data/raw/external_validation/trujillo_part_iii/02_Test_images_and_ground_truth.7z`
- **Archive Byte Size:** `9,859,650,011` bytes (exact byte match to Zenodo upstream specification)
- **Archive Signature:** `37 7A BC AF` (verified valid 7-Zip container header)
- **Full Canonical Digest:** `5dce64cd7ff9d80189d13504bd3bcbf5` (exact MD5 match to acquisition-stage verified archive identity in `scratch/trujillo_part_iii_acquisition_summary.json`)

### 4.2 Canonical Extracted Dataset
- **Extraction Directory:** `data/raw/external_validation/trujillo_part_iii/extracted/`
- **Total Physical Files:** Exactly 900 files (450 images, 450 masks)
- **Total Uncompressed Volume:** `17,000,181,900` bytes
- **Manifest & Cryptographic Reconciliation:** All 900 extracted TIFF contents match the recorded SHA-256 extraction inventory. All 900 extracted TIFF contents match the recorded SHA-256 inventory, and no qualification operation was authorized to rewrite canonical TIFF content. Complete hashes are recorded in `scratch/trujillo_part_iii_extracted_sha256.json`.

### 4.3 Quarantine Smoke Test Directory
- **Quarantine Path:** `data/raw/external_validation/trujillo_part_iii/smoke_test/`
- **Quarantine Status:** 4 isolated files; completely separate from canonical extracted storage.

---

## 5. Reconciliation R1 — Physical Inventory

Every file in the extracted dataset was physically inspected and cataloged:

| Property | Measured Specification | Conformance |
|---|---|:---:|
| **Total Files** | 900 (450 images, 450 masks) | Exact match |
| **Class Directory Breakdown** | 150 Oil, 150 No oil, 150 Lookalike | Exact match |
| **Raster Container Driver** | 100% `GTiff` (900 / 900) | Exact match |
| **Spatial Dimensions** | $2048 \times 2048$ pixels across all 900 rasters | Exact match |
| **Image Channels & Dtype** | 2 bands per image, stored as `float32` | Exact match |
| **Mask Channels & Dtype** | 1 band per mask, stored as `uint8` | Exact match |
| **Container Readability** | 900 / 900 readable via `rasterio` | 100.0% PASS |
| **Read Failures** | 0 unreadable containers / 0 physical-read failures observed | Exact match |
| **Non-Finite Values** | 0 NaNs, 0 $+ \infty$, 0 $- \infty$ across all pixels | Exact match |

- **Gate Status:** **`R1_PASS`**

---

## 6. Reconciliation R2 — Image/Mask Pairing

The pairing relationship between image rasters and mask rasters was empirically validated across all 450 candidate pairs:

- **Pairing Rule Established:**
  $$\text{Mask Path} = \text{Mask}/[\text{Class}]/[\text{Stem}]\_segmentation.tif$$
  $$\text{Image Path} = \text{Images}/[\text{Class}]/[\text{Stem}].tif$$
- **Bijective Correspondence:** Exactly 450 pairs established with zero duplicate pairings, zero one-to-many pairings, zero many-to-one pairings, and zero cross-class pairing errors.
- **Dimensional Concordance:** Width and height match across all 450 pairs ($2048 \times 2048 \equiv 2048 \times 2048$).
- **Distinction of Correspondence:** Successful filename pairing establishes filename association within directory structures; it does not by itself prove ground-truth semantic correspondence.
- **Gate Status:** **`R2_PASS`**

---

## 7. Reconciliation R3 — Mask Encoding vs. Mask Semantics

Mask rasters were examined to decouple physical storage values from semantic interpretation:

### 7.1 Physical Value Encoding
- **Observed Unique Values:** Strictly $\{0, 1\}$ across all 450 masks.
- **Oil Directory (150 masks):** 150 / 150 masks contain non-zero pixels; total foreground pixels = `62,501,987` (mean foreground area = 9.93% per scene).
- **No oil Directory (150 masks):** 150 / 150 masks contain strictly zero pixels (100.0% all-zero target masks).
- **Lookalike Directory (150 masks):** 150 / 150 masks contain strictly zero pixels (100.0% all-zero target masks).

### 7.2 Semantic Classification
- **ENCODING OBSERVED:** Binary-valued mask encoding {0,1} observed.
- **ALL-ZERO MASKS:** 300 target masks are all-zero arrays.
- **SEMANTICS UNVERIFIED:** Semantic interpretation as objective "true negatives" or confirmed absence of oil remains unverified unless authoritative source evidence establishes that semantic claim. Attributing specific semantic labels ("1 = oil", "0 = background") is an inference from directory structure and file naming; authoritative semantic tags are absent from raster container metadata.
- **Gate Status:** **`R3_CONDITIONAL`**

---

## 8. Reconciliation R4 — Image Storage and Radiometric Semantics

All 450 image rasters were evaluated to determine physical storage and distribution properties:

### 8.1 Measured Statistical Distributions
Across all 3,774,873,600 evaluated image pixels:
- **Finite Pixel Ratio:** 100.0% (zero NaNs, zero Infinities across all evaluated pixels).
- **Class-Level Empirical Means:**
  - **Oil (150 scenes):** Band 1 mean = `-29.08` (mean std = `1.74`); Band 2 mean = `-20.96` (mean std = `2.75`).
  - **No oil (150 scenes):** Band 1 mean = `-22.41` (mean std = `4.07`); Band 2 mean = `-13.82` (mean std = `3.23`).
  - **Lookalike (150 scenes):** Band 1 mean = `-26.57` (mean std = `3.98`); Band 2 mean = `-21.36` (mean std = `4.53`).
  - **Overall Mean (450 scenes):** Band 1 mean = **`-26.02`**; Band 2 mean = **`-18.71`**.

### 8.2 Epistemic Property Disaggregation
1. **STORAGE DTYPE:** `float32` (OBSERVED FACT).
2. **NUMERIC RANGE:** Negative-valued distributions with values predominantly between $-40$ and $+10$ (OBSERVED FACT).
3. **FINITE STATISTICS:** 100.0% finite pixels; zero NaNs, zero $+ \infty$, zero $- \infty$ across all 3,774,873,600 evaluated pixels (OBSERVED FACT).
4. **RADIOMETRIC UNITS:** UNKNOWN. Container tags lack unit descriptors (`dB`, `linear`, or `DN`). Negative values do not establish that data are in decibels (dB), and data must not be termed calibrated $\sigma^0$ without authoritative metadata.
5. **CALIBRATION SEMANTICS:** UNKNOWN. Metadata tags do not state whether values represent $\sigma^0$, $\gamma^0$, or $\beta^0$; physical calibration cannot be confirmed from container metadata alone.
6. **POLARIZATION ORDER:** UNKNOWN. Band descriptions in raster headers are `(None, None)`. Polarization order is not established by the currently available evidence.
- **Gate Status:** **`R4_CONDITIONAL`**

---

## 9. Reconciliation R5 — Geospatial Metadata vs. Pixel-Grid Compatibility

Geospatial metadata was audited across all 450 image/mask pairs and recorded separately across all dimensions:

- **Image Dimensions:** $2048 \times 2048$ pixels across all 450 images.
- **Mask Dimensions:** $2048 \times 2048$ pixels across all 450 masks.
- **Array Shape:** Image arrays are $(2, 2048, 2048)$ 3D; mask arrays are $(2048, 2048)$ 2D.
- **Pixel-Index Relationship:** Bijective 1-to-1 correspondence is inferred from directory structure and file stem pairing.
- **Image CRS:** `EPSG:4326` (WGS 84 geographic coordinates) present on all 450 images.
- **Mask CRS:** CRS is `None` (unreferenced / unprojected) on all 450 masks.
- **Image Transform:** Affine geotransform present (e.g. `(0.00010086..., 0.0, ..., -0.00010086...)`) on all 450 images.
- **Mask Transform:** Default identity affine matrix `[1.0, 0.0, 0.0, 0.0, 1.0, 0.0]` on all 450 masks.
- **World-Coordinate Registration:** NOT ESTABLISHED. Image and mask arrays share identical dimensions. World-coordinate registration is not established because image georeferencing is present while mask CRS/geotransform metadata are absent/default.
- **Gate Status:** **`R5_CONDITIONAL`**

---

## 10. Reconciliation R6 — Ocean Sentinel Pipeline Compatibility

The physical properties of Trujillo Part III were evaluated against the Ocean Sentinel native dataset contract:

| Evaluation Dimension | Trujillo Part III Property | Ocean Sentinel Native Contract | Classification | Evidence Dependency |
|---|---|---|:---:|---|
| **Dimensions** | $2048 \times 2048$ pixels | $512 \times 512$ patches | **ADAPTER_REQUIRED** | Rasterio image/mask headers ($2048 \times 2048$) vs model patch resolution ($512 \times 512$). |
| **2-band array structure** | 2 bands per scene | 2 input channels | **NATIVE_COMPATIBLE** | Rasterio band count (count=2) across all 450 images vs U-Net `in_channels=2`. |
| **Storage Numeric Dtype** | `float32` | `torch.float32` | **NATIVE_COMPATIBLE** | Rasterio dtype (`float32`) vs PyTorch tensor dtype (`torch.float32`). |
| **Radiometric Units** | Negative values in $[-36.4, 18.0]$; unit tags absent | `BackscatterUnit.DECIBEL` ($\sigma^0$ dB) | **UNKNOWN** | Rasterio tag inspection demonstrating absence of unit metadata; physical calibration and dB scale are unverified in GeoTIFF container. |
| **Calibration / Scaling** | Unverified calibration state | Calibrated $\sigma^0$ backscatter | **UNKNOWN** | Rasterio tag inspection demonstrating absence of radiometric calibration metadata. |
| **Polarization / Channel Mapping** | Band descriptions are `(None, None)` | Channel 0 = VV, Channel 1 = VH | **UNKNOWN** | Rasterio description inspection (`None`); authoritative polarization order is unverified in container metadata. |
| **Normalization** | Un-normalized raw values | Training-derived z-score normalization | **ADAPTER_REQUIRED** | Raw pixel distributions vs frozen EXP-01/02 z-score standardization contract. |
| **Mask Value Encoding** | Binary $\{0, 1\}$ | Binary $\{0, 1\}$ | **NATIVE_COMPATIBLE** | Direct pixel inspection confirming values strictly in $\{0, 1\}$. |
| **Mask Storage Dtype** | `uint8` | `torch.float32` | **ADAPTER_REQUIRED** | Rasterio mask dtype (`uint8`) vs loss function target dtype (`torch.float32`). |
| **Mask Filename Convention** | `_segmentation.tif` suffix | `.tif` exact stem match | **ADAPTER_REQUIRED** | Filesystem mask filenames vs `discover_mask_stems` in `trujillo.py`. |
| **Negative / All-Zero Mask Handling** | 300 all-zero target masks | Single split partition manifest | **ADAPTER_REQUIRED** | Class directories (300 all-zero target masks) vs single split manifest contract. |
| **Metadata Preservation** | Asymmetric (Images EPSG:4326; Masks unprojected) | Structured patch metadata | **ADAPTER_REQUIRED** | Rasterio metadata inspection across image/mask pairs. |
| **Batching / Collation** | $2048 \times 2048$ full-scene rasters | Batched patches of shape $(B, 2, 512, 512)$ | **ADAPTER_REQUIRED** | Scene dimensions and PyTorch DataLoader collation contract. |
| **Geospatial Coordinate Alignment** | Asymmetric (Images EPSG:4326; Masks identity) | Aligned spatial metadata | **ADAPTER_REQUIRED** | Rasterio CRS/transform audit (Images: EPSG:4326; Masks: unprojected identity). |
| **Nodata Behavior** | `nodata = None` | `nodata = None` | **NATIVE_COMPATIBLE** | Rasterio nodata tag (`None`) vs `DatasetPatchMetadata(nodata=None)`. |

- **Summary Totals:** Exactly 4 Native Compatible, 8 Adapter Required, 3 Unknown, 0 Incompatible (generated programmatically in `scratch/trujillo_part_iii_compatibility_audit.json`).
- **Overall Compatibility Status:** **`R6_CONDITIONAL`**

---

## 11. Reconciliation R7 — Contamination, Duplication, and Independence Audit

### 11.1 Complete Raster Accounting
- **Part I Physical Images Audited:** Exactly 1,200 physical files read and hashed.
  - Unique image hashes: **1,198**
  - Duplicate image pairs in Part I: 2 pairs (`00007.tif` == `01339.tif` and `00356.tif` == `00357.tif`).
- **Part I Physical Masks Audited:** Exactly 1,200 physical files read and hashed.
  - Unique mask hashes: **1,199**
  - Duplicate mask pairs in Part I: 1 pair (`00356.tif` == `00357.tif`).
- **Total Part I Physical Files Audited:** **2,400** files.
- **Part III Physical Images Audited:** Exactly 450 physical files read and hashed.
  - Unique image hashes: **450** (zero internal image duplicates).
- **Part III Physical Masks Audited:** Exactly 450 physical files read and hashed.
  - Unique mask hashes: **151** (150 unique positive masks in Oil + 1 shared all-zero mask hash representing the 300 empty masks in No oil and Lookalike).
- **Total Part III Physical Files Audited:** **900** files.

### 11.2 Overlap Analysis
- **Exact Image SHA-256 Matches:** **0 / 450** (zero identical content detected under the completed cross-dataset comparison).
- **Exact Mask SHA-256 Matches:** **0 / 450** (zero identical content detected under the completed cross-dataset comparison).
- **Filename Overlap:** Stems `00000` through `00149` exist in both datasets, but their SHA-256 hashes demonstrate completely distinct scene content.
- **Cross-Dataset Comparison:** No exact SHA-256 content matches were detected under the completed cross-dataset comparison.
- **Acquisition Independence:** Acquisition-level independence is UNVERIFIED. Zero exact SHA-256 content matches under the completed comparison does not establish sensor-level or scene-level independence. Without raw Sentinel-1 SAFE product IDs or acquisition timestamps in metadata, scene-level independence cannot be proven.
- **Provenance Relationship:** CONFIRMED SHARED UPSTREAM PROVENANCE. Both datasets originate from Zenodo Record `13761290` (Trujillo-Acatitla et al., 2024).
- **Gate Status:** **`R7_CONDITIONAL`**

---

## 12. Reconciliation R8 — Recovery and Resumability Evidence

The qualification execution model was audited for operational resilience and classified by evidence tier:

| Recovery Feature | Evidence Classification | Execution Evidence / Verification Basis |
|---|:---:|---|
| **Process Lock Contention Rejection** | **UNIT-TESTED** | Verified in quarantine via `scratch/test_qualification_recovery.py`. |
| **Simulated Crash Interruption Recovery** | **UNIT-TESTED** | Verified in quarantine via `scratch/test_qualification_recovery.py`. |
| **Atomic State Updates (`tmp` + `fsync` + `replace`)** | **IMPLEMENTED & OBSERVED-IN-RUN** | Used for all durable JSON artifact writes with fsync flushing. |
| **Stale Lock Detection and Reclamation** | **OBSERVED-IN-RUN** | A stale lock associated with deceased PID 24652 was observed and reclaimed during execution: `[LOCK] Removing stale lockfile from deceased PID 24652`. |
| **Filesystem State Reconciliation on Resume** | **OBSERVED-IN-RUN** | `reconcile_from_filesystem()` verified on-disk artifacts and resumed without duplicate execution. |
| **Clean Lock Release Upon Exit** | **OBSERVED-IN-RUN** | Verified upon termination of PID 15032. |
| **Kernel Panic / Power-Loss Durability** | **NOT-TESTED** | Not tested under simulated power interruption. |

- **Gate Status:** **`R8_PASS`**

---

## 13. Reconciliation R9 — Artifact Consistency

All numerical values, tables, and claims in this final report were checked against the persisted machine-readable artifacts:
- Image inventory records in `scratch/trujillo_part_iii_image_inventory.json` reconcile to 450 entries.
- Mask inventory records in `scratch/trujillo_part_iii_mask_inventory.json` reconcile to 450 entries.
- Pairing records in `scratch/trujillo_part_iii_pairing.json` reconcile to 450 paired entries.
- Mask statistics in `scratch/trujillo_part_iii_mask_statistics.json` reconcile to $62,501,987$ foreground pixels in Oil and 300 empty target masks.
- Numerical statistics in `scratch/trujillo_part_iii_value_statistics.json` reconcile to Band 1 mean $-26.02$ and Band 2 mean $-18.71$.
- Complete extracted SHA-256 records in `scratch/trujillo_part_iii_extracted_sha256.json` reconcile to all 900 physical files on disk.
- Leakage records in `scratch/trujillo_part_iii_leakage_audit.json` reconcile to 2,400 Part I files and 900 Part III files audited with 0 exact matches.
- Gate Status: **`R9_PASS`**

---

## 14. Reconciliation R10 — Terminology and Epistemic Audit

A systematic terminology audit was conducted to eliminate unsupported claims:
- Replaced uncalibrated assertions of "calibrated SAR backscatter in decibels" with "observed float32 rasters with negative-valued distributions; radiometric units remain unverified".
- Replaced "geospatially aligned" with "Array dimensions match at 2048 x 2048 for image/mask pairs; world-coordinate alignment is not established in mask metadata".
- Replaced "true negatives" with "all-zero target masks".
- Replaced "independent dataset" with "No exact SHA-256 content matches were detected under the completed comparison. This does not establish acquisition-level independence; both datasets share upstream provenance".
- Replaced "0 corruptions" with "0 unreadable containers / 0 physical-read failures observed".
- Replaced generic "all gates passed" with calibrated gate classifications (`R1_PASS`, `R2_PASS`, `R3_CONDITIONAL`, `R4_CONDITIONAL`, `R5_CONDITIONAL`, `R6_CONDITIONAL`, `R7_CONDITIONAL`, `R8_PASS`, `R9_PASS`, `R10_PASS`).
- Gate Status: **`R10_PASS`**

---

## 15. Observed Facts

1. All 900 files in `data/raw/external_validation/trujillo_part_iii/extracted/` exist, are non-zero in size, and are readable GeoTIFF containers.
2. Every image raster contains exactly 2 channels stored as `float32`.
3. Every mask raster contains exactly 1 channel stored as `uint8`.
4. Spatial dimensions are exactly $2048 \times 2048$ pixels across all 900 files.
5. All 150 masks in `Mask/Oil/` contain non-zero pixels ($62,501,987$ foreground pixels total; values strictly $\{0, 1\}$).
6. All 150 masks in `Mask/No oil/` and all 150 masks in `Mask/Lookalike/` contain strictly zero pixels.
7. GeoTIFF tags on images contain `{'AREA_OR_POINT': 'Area'}` and descriptions `(None, None)`; authoritative polarization tags are absent.
8. Images contain `EPSG:4326` geographic transforms; masks contain unprojected identity transforms.
9. Zero exact SHA-256 content matches exist between Part III and Part I across all audited rasters.
10. Part I contains 2 duplicate image pairs (`00007.tif` == `01339.tif` and `00356.tif` == `00357.tif`) and 1 duplicate mask pair (`00356.tif` == `00357.tif`).
11. The source archive `02_Test_images_and_ground_truth.7z` remains intact (`9,859,650,011` bytes, signature `37 7A BC AF`).
12. All 13 model checkpoints remain unmodified with identical cryptographic hashes.
13. Exactly 0 ML forward passes were executed during this qualification.

---

## 16. Derived Measurements

1. Oil scene foreground pixel coverage: $62,501,987 / (150 \times 2048 \times 2048) = 9.9348\%$.
2. Overall dataset foreground pixel coverage: $62,501,987 / (450 \times 2048 \times 2048) = 3.3116\%$.
3. Overall empirical mean of image Band 1: $-26.0192$.
4. Overall empirical mean of image Band 2: $-18.7127$.
5. Part I unique image hashes: $1200 - 2 = 1198$.
6. Part I unique mask hashes: $1200 - 1 = 1199$.
7. Part III unique mask hashes: $150 \text{ (Oil)} + 1 \text{ (shared empty)} = 151$.

---

## 17. Inferences

1. While negative values in SAR often correlate with decibel distributions, the observed numerical ranges remain unverified floating-point numbers; they cannot be assumed to represent decibels (dB) or calibrated $\sigma^0$ without authoritative metadata tags.
2. While lower numerical values in Band 1 relative to Band 2 are consistent with general cross-polarization behavior, this does not establish polarization order, which remains unverified in container metadata.
3. The presence of all-zero target masks in `No oil` and `Lookalike` suggests an evaluation partition structured around negative scenes, but semantic confirmation of verified absence of oil requires upstream documentation.

---

## 18. Unverified Properties

1. **Physical Polarization Mapping:** Unverified due to lack of channel description tags in raster headers.
2. **Radiometric Units and Calibration Standard:** Unverified due to lack of calibration metadata in GeoTIFF tags.
3. **Acquisition-Level Independence:** Unverified due to lack of raw Sentinel-1 product IDs and acquisition timestamps.
4. **World-Coordinate Mask Alignment:** Unverified due to unprojected identity transforms in mask headers.

---

## 19. Blocking Issues

- **None for Qualification.** Qualification is complete.
- **For Direct Model Inference:** Lack of a certified adapter currently blocks unadapted native inference.

---

## 20. Conditional Restrictions

To utilize Trujillo Part III in future Ocean Sentinel benchmark evaluations, the following conditions must be satisfied:
1. **Certified Evaluation Adapter:** A dedicated adapter must be implemented to tile $2048 \times 2048$ scenes into $512 \times 512$ patches, map `_segmentation.tif` suffixes, and cast `uint8` masks to `torch.float32`.
2. **Explicit Channel Mapping Policy:** In the absence of container polarization tags, the evaluation protocol must document whether channels are mapped empirically based on decibel mean parity.
3. **Class-Stratified Metric Reporting:** Metrics must be reported separately for Oil scenes (IoU, Precision, Recall), No oil scenes (False Positive Area), and Lookalike scenes (Lookalike False Alarm Rate).
4. **Documentation of Shared Upstream Provenance:** Scientific reports must acknowledge shared repository provenance with Trujillo Part I.

---

## 21. Final Scientific Qualification Status

# **`SCIENTIFIC_QUALIFICATION_CONDITIONAL`**

Phase 4B-3 scientific qualification is complete.

The dataset is structurally qualified for downstream evaluation design, but scientific evaluation remains CONDITIONAL pending the documented restrictions and a separately approved evaluation contract.

No model evaluation has been performed.

### Qualification Rationale
The overall qualification verdict is derived strictly from the ten reconciliation gate states:
1. Physical completeness and container readability are established (900/900 readable GeoTIFFs, zero read failures).
2. Exact extracted content identity is established (all 900 extracted TIFF contents match the recorded SHA-256 extraction inventory).
3. Image/mask pairing is established (450 bijective pairs without orphan, duplicate, or cross-class errors).
4. Binary-valued mask encoding is established (mask values strictly $\{0, 1\}$).
5. Radiometric units and calibration standard remain UNKNOWN (GeoTIFF tags omit units and calibration metadata; data must not be termed decibels or calibrated $\sigma^0$).
6. Polarization channel order remains UNKNOWN (band descriptions are absent; authoritative VV/VH mapping unverified).
7. World-coordinate image/mask registration is NOT ESTABLISHED (masks lack CRS and geotransform; identity transform present).
8. Acquisition-level independence is UNKNOWN (zero exact content duplicates detected under completed cross-dataset comparison, but shared Zenodo 13761290 upstream provenance confirmed).
9. Native evaluation compatibility is therefore NOT FULLY ESTABLISHED (adapter strictly required; direct native inference blocked).

---

## 22. Artifacts and Reproducibility

The complete qualification state is persisted in reproducible, machine-readable artifacts:
- `scratch/trujillo_part_iii_qualification_state.json`
- `scratch/trujillo_part_iii_image_inventory.json`
- `scratch/trujillo_part_iii_mask_inventory.json`
- `scratch/trujillo_part_iii_pairing.json`
- `scratch/trujillo_part_iii_value_statistics.json`
- `scratch/trujillo_part_iii_mask_statistics.json`
- `scratch/trujillo_part_iii_geospatial_audit.json`
- `scratch/trujillo_part_iii_compatibility_audit.json`
- `scratch/trujillo_part_iii_leakage_audit.json`
- `scratch/trujillo_part_iii_extracted_sha256.json`
- `experiments/TRUJILLO_PART_III_QUALIFICATION_RECONCILIATION_20260911.md`
- `experiments/TRUJILLO_PART_III_QUALIFICATION_20260911_FINAL.md`

---

## 23. ML Forward Pass Count

# **`ML FORWARD PASSES: EXACTLY 0`**

No model forward passes, predictions, backward passes, training routines, or evaluation inferences were initiated.

---

## 24. Checkpoint Integrity

All 13 model checkpoints remain untouched and cryptographically verified:
- `EXP-02C`: `best_model.pt` (`14073F67...`), `final_model.pt` (`B3FC0DD0...`), `latest_checkpoint.pt` (`B250126F...`)
- `EXP-01`: `best_model.pt` (`9B8BD867...`), `final_model.pt` (`2E4C0881...`), `latest_checkpoint.pt` (`2F8F7718...`)
- `EXP-02B-1`: `best_model.pt` (`54B4B098...`), `final_model.pt` (`35D1C0BA...`), `latest_checkpoint.pt` (`83571183...`)
- `EXP-01 (Interrupted)`: `best_model.pt` (`8B306D97...`)

---

## 25. Network Activity

- **Workflow Network Invocation:** No network access was invoked by the qualification workflow.
- **Firewall Status:** Strict local execution maintained.

---

## 26. Final Git State

- `git status --short`: Clean of tracked modifications (untracked files strictly confined to experimental markdown reports, checkpoints, and uv lockfile).
- `git diff --cached --name-status`: Empty (0 staged changes).
- `git diff --name-status`: Empty (0 unstaged tracked modifications).
- `git branch --show-current`: `master`
- `git rev-parse HEAD`: `542bab19f6f08c9bba8b8762e6480386c8b6026b`

---

## 27. Mandatory Hard Stop

Execution is halted at the mandatory qualification boundary. Awaiting CAO review.

---

## 28. Next-Phase Handoff — Design Only (Phase 4C Inputs)

This section documents exclusively the inputs, boundaries, and unresolved questions required for downstream Phase 4C adapter and benchmark design. These items are strictly inputs; none are resolved in Phase 4B-3.

### 28.1 Known Source Representation
- Spatial resolution: $2048 \times 2048$ pixels per raster.
- Container format: Standard GeoTIFF (`GTiff`).
- Channel structure: 2 bands per scene.
- Storage dtype: `float32` for images, `uint8` for masks.
- Mask values: Strictly binary $\{0, 1\}$.
- Directory structure: 3 class folders (`Oil`, `No oil`, `Lookalike`), each containing 150 image/mask pairs.
- Target mask distribution: 150 masks in `Oil` contain foreground annotations ($62,501,987$ non-zero pixels total); 300 masks in `No oil` and `Lookalike` are all-zero target arrays.

### 28.2 Unknown Source Representation
- Radiometric physical units: Unknown (dB, linear intensity, or DN unverified).
- Radiometric calibration standard: Unknown ($\sigma^0$, $\gamma^0$, or uncalibrated).
- Polarization channel assignment: Unknown (authoritative VV/VH order absent).
- World-coordinate image/mask registration: Unknown (masks lack CRS and geotransform).
- Semantic validation of negative masks: Unknown (field validation of absence of oil unverified).

### 28.3 Known Ocean Sentinel Input Contract
- Tensor shape: $(B, 2, 512, 512)$ float32 patches.
- Target mask shape: $(B, 1, 512, 512)$ float32 or long binary tensor.
- Channel convention: Channel 0 = VV, Channel 1 = VH.
- Normalization: Z-score standardization using frozen training parameters (mean=[-33.23, -19.94], std=[6.49, 4.53]).
- Patch extraction: 16 non-overlapping $512 \times 512$ tiles per scene via `tile_sample`.

### 28.4 Unresolved Scientific Decisions
- Radiometric conversion: Whether to treat raw negative values directly as dB or apply an offset/rescaling.
- Polarization mapping policy: Whether to map Band 1 $\rightarrow$ VH and Band 2 $\rightarrow$ VV based on empirical mean heuristic, or evaluate both permutations.
- Mask semantic handling: Whether all-zero masks in `Lookalike` and `No oil` are evaluated as hard negative backgrounds or handled via a separate false-alarm metric.

### 28.5 Candidate Evaluation Units
- Full-scene level ($2048 \times 2048$) aggregated metrics.
- Patch-level ($512 \times 512$) native inference metrics.
- Tile-aggregated whole-scene mosaic metrics.

### 28.6 Candidate Stratification Dimensions
- Strata 1: Oil scenes (150 scenes with positive targets — segmentation IoU, Precision, Recall, F1).
- Strata 2: No oil scenes (150 scenes with zero targets — False Positive Area, False Alarm Rate).
- Strata 3: Lookalike scenes (150 scenes with zero targets — Lookalike Discrimination Rate, False Positive Rate).

### 28.7 Contamination Constraints
- Both Part I and Part III originate from Zenodo deposit `13761290` (Trujillo-Acatitla et al., 2024).
- Exact SHA-256 non-duplication is established (0 identical rasters).
- Acquisition-level independence is UNVERIFIED (potential spatial/temporal overlap of underlying Sentinel-1 scenes cannot be ruled out).
- Benchmark reporting must state that Part III serves as external benchmark validation under shared upstream provenance, not fully independent sensor acquisition.

### 28.8 Adapter Questions
- Should the adapter tile scenes into $512 \times 512$ patches dynamically in memory or pre-generate an evaluation manifest?
- How should border tiles with partial spatial coverage be handled?
- Should polarization permutation evaluation be automated as dual-pass inference?

### 28.9 Decisions Requiring CAO Approval
1. Formal authorization of the Phase 4C Evaluation Adapter Design Specification.
2. Selection of the canonical polarization channel mapping policy.
3. Selection of the radiometric normalization policy.
4. Adoption of the class-stratified metric reporting structure.
5. Authorization of frozen model checkpoint loading for evaluation.
