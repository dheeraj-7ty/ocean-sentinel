# Phase 4B-3R: Scientific Qualification Reconciliation Audit — Trujillo Part III

**Document Identifier:** `TRUJILLO_PART_III_QUALIFICATION_RECONCILIATION_20260911`  
**Execution Phase:** Phase 4B-3R (Scientific Qualification Reconciliation + Finalization)  
**Dataset Under Audit:** Trujillo Part III (`10.5281/zenodo.13761290`, `02_Test_images_and_ground_truth.7z`)  
**Authority:** Chief Architect Officer (CAO) Mandate  
**Execution Date:** 2026-09-11  
**Baseline Git HEAD:** `542bab19f6f08c9bba8b8762e6480386c8b6026b`  
**Active Git Branch:** `master`  
**ML Forward Passes:** Exactly 0  
**Overall Scientific Qualification Status:** **`SCIENTIFIC_QUALIFICATION_CONDITIONAL`**  

---

## 1. Executive Summary & Purpose

Phase 4B-3R was commissioned by the CAO to reconcile, challenge, and calibrate the scientific qualification records of the Trujillo Part III dataset. Rather than executing a blind rerun, Phase 4B-3R evaluated the empirical measurements, resolved discrepancies between initial narrative text and machine-readable artifacts, eliminated uncalibrated epistemic overclaims, and verified the complete physical and cryptographic state of the dataset.

The ten reconciliation gates were audited against the physical rasters, machine-readable artifacts, repository code, and applicable provenance evidence. This reconciliation establishes an evidence-calibrated record where every scientific statement strictly reflects its physical evidence scope.

---

## 2. Root Cause Discrepancy Audits & Resolutions

### Discrepancy 1: Part I Audited Raster Counts (2,397 vs. 2,400)
- **Initial Observation:** The initial Gate 4B-3G report stated that `2,397` rasters were audited from Part I (`1,198` images and `1,199` masks), whereas the canonical Part I dataset physically contains `1,200` images and `1,200` masks (`2,400` files total).
- **Physical Investigation:**
  - Filesystem scan of `data/raw/trujillo_2024/images/Oil` confirmed exactly `1,200` TIFF files.
  - Filesystem scan of `data/raw/trujillo_2024/masks/Mask_oil` confirmed exactly `1,200` TIFF files.
  - Inspection of the initial qualification script revealed that files were indexed in a Python dictionary using their computed SHA-256 hash as the dictionary key: `p1_img_hashes[hash] = filename`.
  - When two distinct files possess identical byte content, the second file overwrites the first in the dictionary, causing `len(p1_img_hashes)` to report unique hash count rather than physical file count.
- **Root Cause Established:**
  - **Part I Images:** Part I contains two pairs of exact duplicate images:
    1. `00007.tif` and `01339.tif` share identical file size (`41,857,591` bytes) and identical SHA-256 hash (`927B382EBFFC2F84...`).
    2. `00356.tif` and `00357.tif` share identical file size (`42,988,308` bytes) and identical SHA-256 hash (`87148351174FB8CB...`).
    - Calculation: $1200 \text{ physical image files} - 2 \text{ duplicate entries} = 1198 \text{ unique image hashes}$.
  - **Part I Masks:** Part I contains one pair of exact duplicate masks:
    1. `00356.tif` and `00357.tif` share identical file size (`4,211,084` bytes) and identical SHA-256 hash (`6DA04149726A3EC5...`).
    - Note: While `00007.tif` and `01339.tif` share image content, their mask files differ (`4D2638E21B...` vs `F3819A2E...`).
    - Calculation: $1200 \text{ physical mask files} - 1 \text{ duplicate entry} = 1199 \text{ unique mask hashes}$.
- **Resolution:** All `2,400` physical files in Part I were read and audited. The updated leakage audit artifact (`scratch/trujillo_part_iii_leakage_audit.json`) explicitly separates total physical files examined (`2,400`) from unique cryptographic content hashes (`1,198` images, `1,199` masks). Cross-dataset comparison confirms `0` exact SHA-256 matches between Part III and Part I across all `450` images and `450` masks. No exact SHA-256 content matches were detected under the completed comparison. This does not establish acquisition-level independence.

---

### Discrepancy 2: Numerical Value Summary Alignment
- **Initial Observation:** The summary table in the initial qualification report contained template decibel values (Band 1: `-31.45 dB`, Band 2: `-21.74 dB`) that did not match the computed values in `scratch/trujillo_part_iii_value_statistics.json`.
- **Physical Investigation:** Direct inspection of `scratch/trujillo_part_iii_value_statistics.json` established the exact empirical means computed across all 450 scenes:
  - **Oil Class:** Band 1 mean = `-29.08`, Band 2 mean = `-20.96`
  - **No oil Class:** Band 1 mean = `-22.41`, Band 2 mean = `-13.82`
  - **Lookalike Class:** Band 1 mean = `-26.57`, Band 2 mean = `-21.36`
  - **Overall Mean:** Band 1 mean = **`-26.02`**, Band 2 mean = **`-18.71`**
- **Resolution:** Reconciled report tables and narrative to reflect the exact deterministic calculations recorded in `scratch/trujillo_part_iii_value_statistics.json`.

---

### Discrepancy 3: Epistemic Overclaim Calibration
- **Initial Observation:** The initial report asserted that pixel values are "calibrated SAR backscatter in decibels", that image/mask pairs are "geospatially aligned", and that certain pipeline properties are "native compatible" despite missing metadata.
- **Epistemic Calibration:**
  - **Readability vs. Corruption:** Replaced "0 corruptions" with "0 unreadable containers / 0 physical-read failures observed".
  - **Extracted File Verification:** All 900 extracted TIFFs were SHA-256 verified against the hashes recorded in the extraction inventory; 900/900 matched. Complete hashes are recorded in `scratch/trujillo_part_iii_extracted_sha256.json`. This confirms container preservation against the recorded inventory; it does not independently establish semantic correctness of the published raster contents.
  - **Radiometric Properties:** Raster pixel storage is `float32` with negative numerical distributions. However, GeoTIFF tags lack explicit units (`dB`, `linear`, `DN`) and calibration metadata. Physical calibration and decibel units are classified as **INFERENCES** / **UNVERIFIED**, not observed facts.
  - **Polarization:** Container tags contain no channel descriptions or polarization identifiers. Channel mapping remains **UNVERIFIED**.
  - **Geospatial Reference:** Image rasters possess `EPSG:4326` geographic transforms; mask rasters possess unreferenced identity transforms. Image and mask arrays share identical dimensions. Their world-coordinate registration is not established because image georeferencing is present while mask CRS/geotransform metadata are absent/default.
  - **Semantic Target Labels:** Binary-valued mask encoding {0, 1} was observed. For No oil and Lookalike, all 300 masks are all-zero target masks. Semantic interpretation remains conditional/unverified unless supported by source documentation.
  - **Dataset Independence:** A result of zero exact SHA-256 matches confirms zero identical content under the performed hash test. It does not establish acquisition-level or sensor-level independence. Shared upstream provenance (Zenodo `13761290`) is explicitly documented.

---

### Discrepancy 4: Pipeline Compatibility Contract Matrix
- **Initial Observation:** The initial compatibility matrix manually cited "3 native compatible / 6 adapter required".
- **Independent Re-Evaluation:** Re-evaluating the Trujillo Part III observations against the native Ocean Sentinel ingestion contract (`src/ocean_sentinel/ingestion/models.py` and `trujillo.py`) across 15 distinct evaluated properties:
  - **Native Compatible (4):** 2-band array structure, Numeric storage dtype (`float32`), Nodata behavior (`None`), Mask value encoding ($\{0, 1\}$).
  - **Adapter Required (8):** Dimensions ($2048 \times 2048$), Normalization (z-score standardization), Mask storage dtype (`uint8` $\rightarrow$ `float32`), Mask filename convention (`_segmentation.tif` $\rightarrow$ `.tif`), Negative / all-zero mask handling (300 all-zero target masks), Metadata preservation, Batching / collation, Geospatial coordinate alignment.
  - **Unknown (3):** Radiometric units (unverified tags), Calibration / scaling (unverified calibration), Polarization / channel mapping (unverified channel order).
  - **Incompatible (0).**
- **Resolution:** Replaced the legacy count with the regenerated 15-property contract matrix generated programmatically in `scratch/trujillo_part_iii_compatibility_audit.json`.

---

### Discrepancy 5: Recovery and Resumability Evidence
- **Initial Observation:** Recovery guarantees were asserted broadly without distinguishing between unit-tested mock logic and production-observed behavior.
- **Evidence Classification:**
  - **Unit-Tested in Scratch Quarantine:** Process lock contention rejection and simulated interruption recovery were verified via `scratch/test_qualification_recovery.py`.
  - **Actually Observed in Production Execution:**
    1. *Stale Lock Reclamation:* A stale lock associated with deceased PID 24652 was observed and reclaimed during execution: `[LOCK] Removing stale lockfile from deceased PID 24652`.
    2. *Filesystem Reconciliation:* The qualification engine verified completed gate artifacts on disk via `reconcile_from_filesystem()`, safely bypassed previously completed gates, and resumed directly at Gate 4B-3H.
    3. *Clean Lock Release:* Clean lock release was observed upon process termination (`PID 15032`).

---

## 3. Reconciliation Gate Statuses (R1 through R10)

| Gate | Gate Identifier | Reconciliation Status | Evidence Basis |
|---|---|:---:|---|
| **R1** | Physical Inventory | **`R1_PASS`** | 900 files verified physically on disk; byte sizes, dimensions ($2048 \times 2048$), and dtypes match 100%. 0 unreadable containers / 0 physical-read failures observed. |
| **R2** | Image/Mask Pairing | **`R2_PASS`** | Exactly 450 bijective pairs established via stem mapping; zero orphans, zero duplicates, zero cross-class errors. |
| **R3** | Mask Encoding & Semantics | **`R3_CONDITIONAL`** | Encoding verified as binary $\{0, 1\}$; semantic interpretation of all-zero target masks remains inferential. |
| **R4** | Image Radiometric Semantics | **`R4_CONDITIONAL`** | Storage verified as `float32`; negative distributions observed; units, calibration, and polarization remain unverified. |
| **R5** | Geospatial Grid Qualification | **`R5_CONDITIONAL`** | Array dimensions match at 2048 x 2048 for image/mask pairs; world-coordinate alignment is not established in mask metadata. |
| **R6** | Pipeline Compatibility | **`R6_CONDITIONAL`** | 4 Native Compatible, 8 Adapter Required, 3 Unknown, 0 Incompatible (generated programmatically); certified adapter required prior to inference. |
| **R7** | Contamination & Independence | **`R7_CONDITIONAL`** | Zero exact SHA-256 overlap with Part I; acquisition-level independence unverified; shared provenance confirmed. |
| **R8** | Recovery & Resumability | **`R8_PASS`** | Recovery logic unit-tested in quarantine; stale lock reclamation and artifact reconciliation observed in production. |
| **R9** | Artifact Consistency | **`R9_PASS`** | All machine-readable JSON artifacts and markdown report tables strictly match physical measurements. |
| **R10** | Epistemic & Terminology Audit | **`R10_PASS`** | All forbidden overclaim terms excised; every claim strictly calibrated to its underlying physical evidence. |

---

## 4. Reconciliation Conclusion & Final Status

Following comprehensive physical re-verification, complete extracted SHA-256 identity verification (`scratch/trujillo_part_iii_extracted_sha256.json`), discrepancy resolution, and epistemic calibration, the Trujillo Part III dataset is officially designated:

### **`FINALIZATION_READY`** $\rightarrow$ **`SCIENTIFIC_QUALIFICATION_CONDITIONAL`**

The authoritative final qualification report has been compiled and saved to:  
`experiments/TRUJILLO_PART_III_QUALIFICATION_20260911_FINAL.md`.
