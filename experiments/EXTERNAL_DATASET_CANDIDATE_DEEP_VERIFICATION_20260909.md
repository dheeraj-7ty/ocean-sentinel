# External Dataset Candidate Deep Verification (Phase 3.2D)
**Date of Audit:** 2026-09-09T23:06:00+05:30  
**Authority:** CAO Directive — Phase 3.2C-R / Phase 3.2D  
**Evaluation Standard:** EVIDENCE > ASSUMPTION > CONVENIENCE  
**Network Activity:** Metadata-only research (0 dataset content bytes transferred)  

---

## 1. DARTIS / Eastern Mediterranean SAR (PANGAEA DOI: 10.1594/PANGAEA.980773)

### 1.1 Dataset Identity & Provenance
- **Dataset Title:** Dataset of oil slicks, look-alikes and remarkable SAR signatures obtained from Sentinel-1 data in the Eastern Mediterranean Sea
- **Authors:** Yi-Jie Yang, Suman Singha (DLR - German Aerospace Center), Ron Goldman, Florian Schütte (GEOMAR Helmholtz Centre for Ocean Research Kiel)
- **Host Repository:** PANGAEA Data Publisher for Earth & Environmental Science
- **Primary DOI:** `10.1594/PANGAEA.980773`
- **Peer-Reviewed Reference:** *Earth System Science Data* (ESSD), 17, 6807–6826, 2025 (DOI: `10.5194/essd-17-6807-2025`)
- **Companion Code Repository:** `https://github.com/yi-jie-yang/dataset_DARTIS_2019` (Zenodo Code DOI: `10.5281/zenodo.17789853`)
- **License:** Creative Commons Attribution 4.0 International (CC-BY-4.0)
- **Access Model:** Public open-access

### 1.2 Annotation Geometry Audit (CRITICAL FINDING)
- **Observed Fact:** The dataset annotations are distributed in **Pascal VOC XML format** (`<annotation><object><name>oil</name><bndbox><xmin>...<ymin>...<xmax>...<ymax>...</bndbox></object></annotation>`).
- **Observed Fact:** The accompanying evaluation scripts in `calculate_perform.py` evaluate detections against YOLO object detectors using bounding box IoU calculated via `shapely.geometry.Polygon` box coordinates.
- **Observed Fact:** Exactly **0 native pixel-level segmentation raster masks** are distributed with the dataset.
- **Classification:** **`BOX-ANNOTATED DETECTION DATASET`**
- **Mask Suitability Gate:** **`RED`** for semantic segmentation benchmark. It cannot be used for IoU/Dice pixel segmentation evaluation without a separately developed, validated, and justified annotation rasterization or contour-generation process.

### 1.3 Physical Image Representation Gate (CRITICAL FINDING)
- **Observed Fact:** The distributed image patches are **8-bit normalized (0–255) JPG files**, not calibrated floating-point GeoTIFFs.
- **Observed Fact:** In the ESSD paper, the authors explicitly state that users requiring the original quantitative calibrated SAR products must download the parent Sentinel-1 scenes from the Copernicus Data Space Ecosystem using the scene ID lookup table provided in the repository.
- **Classification:** **`RED`** for direct frozen EXP02C inference.
- **Physical Rationale:** Frozen EXP02C operates strictly on calibrated $\sigma^0$ radar backscatter in decibels (dB), normalized by frozen training statistics. Feeding 8-bit normalized visual JPG pixels into EXP02C violates the physical contract of the neural network and would produce scientifically invalid inference outputs.

### 1.4 Independence Audit
- **Spatial Independence:** **`YES`** (Eastern Mediterranean Sea vs. Mexican Gulf / Caribbean coastal waters).
- **Temporal Independence:** **`YES`** (Acquired throughout 2019; disjoint from canonical Trujillo Part I dates).
- **Acquisition Independence:** **`NOT DETERMINABLE`** at parent product level from published metadata without cross-matching all Copernicus product IDs against Trujillo scene footprints.
- **Pipeline Independence:** **`YES`** (Independent DLR / GEOMAR preprocessing pipeline using SNAP, border noise removal, thermal noise removal).
- **Provenance Independence:** **`YES`** (German/Israeli DARTIS project consortium; fully independent of IPICYT Mexico).

### 1.5 DARTIS Summary Assessment
- **Observed Facts:** 3,225 labeled oil objects across 1,365 patches; 2,290 look-alike / remarkable signature patches; Pascal VOC XML bounding box annotations; 8-bit normalized JPG format.
- **Inferences:** DARTIS is a world-class benchmark for **SAR oil spill object detection** and **false-alarm / look-alike screening**, but was never designed or annotated as a semantic pixel-segmentation benchmark.
- **Unverified:** Whether polygon boundary coordinates can be reconstructed from raw Sentinel-1 products without re-annotating the entire dataset.
- **Acquisition Readiness:** **`NOT READY FOR SEGMENTATION BENCHMARKING`** (Requires separate object-detection evaluation track or extensive rasterization engineering).

---

## 2. Trujillo Part III (Zenodo DOI: 10.5281/zenodo.13761290)

### 2.1 Dataset Identity & Provenance
- **Dataset Title:** Sentinel-1 SAR Oil spill image dataset for train, validate, and test deep learning models. Part III
- **Authors:** Rubicel Trujillo-Acatitla, José Tuxpan-Vargas, Cesaré Ovando-Vázquez, Erandi Monterrubio-Martínez (IPICYT, San Luis Potosí, Mexico)
- **Host Repository:** Zenodo
- **Primary DOI:** `10.5281/zenodo.13761290`
- **Publication Date:** September 13, 2024
- **Associated Journal:** *Marine Pollution Bulletin*, 2024 (DOI: `10.1016/j.marpolbul.2024.116549`)
- **License:** Creative Commons Attribution 4.0 International (CC-BY-4.0)
- **Access Model:** Public open-access

### 2.2 Refreshed Authoritative File Metadata
- **Primary Archive File:** `02_Test_images_and_ground_truth.7z`
- **Reported Archive Size:** **`9.9 GB`** ($10,630,044,484$ bytes)  
  *(Correction: Corrected from the preliminary Phase 3.2C estimate of ~2.8 GB)*
- **MD5 Checksum:** **`5dce64cd7ff9d80189d13504bd3bcbf5`**
- **Sample Counts:** Exactly 450 test image samples and 450 ground-truth mask samples:
  - 150 oil spill images + 150 oil spill masks
  - 150 look-alike images + 150 look-alike masks
  - 150 oil-free images + 150 oil-free masks
- **Terminology Correction:** Categorized as **450 released test images/samples**, NOT "450 scenes". The number of distinct parent Sentinel-1 scenes is not documented in the Zenodo metadata.

### 2.3 Input Representation & Annotation Compatibility
- **SAR Mode & Product:** Sentinel-1 C-band IW GRD (reported in metadata).
- **Channel Representation:** **2-channel (reported VV, VH)**, georeferenced GeoTIFF, reported calibrated Sigma0 in dB, nominal dimensions $2048 \times 2048 \times 2$. Exact sample format and dtype are subject to physical raster verification.
- **Annotation Geometry:** Reported **pixel-level binary masks** $\{0, 1\}$, nominal dimensions $2048 \times 2048$, 1-channel TIFF.
- **Input Compatibility Gate:** **`HIGH (Apparent Metadata Compatibility)`**. Metadata indicates high apparent compatibility with our frozen EXP02C pipeline; physical qualification must verify the complete input contract.

### 2.4 Independence Audit
- **Spatial Independence:** **`NO`** (Same Gulf of Mexico / Caribbean coastal region as Part I training data).
- **Temporal Independence:** **`PARTIAL`** (Disjoint test acquisition dates within the 2020–2023 era).
- **Acquisition Independence:** **`NOT DETERMINABLE`** (Parent Sentinel-1 orbit IDs and scene footprints are not enumerated in available metadata).
- **Pipeline Independence:** **`NO`** (Identical SNAP calibration, decibel conversion, and 2-channel stacking pipeline).
- **Provenance Independence:** **`NO`** (Identical IPICYT author team and institutional origin).
- **Scientific Role:** **`SAME-FAMILY HOLDOUT`** (Official test partition of the published Trujillo benchmark).

### 2.5 Trujillo Part III Summary Assessment
- **Observed Facts:** Single 9.9 GB `.7z` archive (MD5: `5dce64cd7ff9d80189d13504bd3bcbf5`); metadata records 450 test image samples and 450 masks.
- **Inferences:** Metadata suggests high apparent architectural compatibility with frozen EXP02C as a same-family holdout test set from the canonical Trujillo distribution, but cannot measure cross-basin external geographic domain shift.
- **Acquisition Readiness:** **`ACQUISITION HALTED (ZENODO HTTP 403 RATE-LIMIT; ZERO CONTENT BYTES TRANSFERRED; QUALIFICATION NOT PERFORMED)`**.

---

## 3. Trujillo Part II (Zenodo DOI: 10.5281/zenodo.8253899)

### 3.1 Dataset Identity & Provenance
- **Dataset Title:** Sentinel-1 SAR Oil spill image dataset for train, validate, and test deep learning models. Part II
- **Authors:** Rubicel Trujillo-Acatitla et al.
- **Host Repository:** Zenodo
- **Primary DOI:** `10.5281/zenodo.8253899`
- **Publication Date:** August 16, 2023
- **License:** Creative Commons Attribution 4.0 International (CC-BY-4.0)
- **Access Model:** Public open-access

### 3.2 Refreshed Authoritative File Metadata
- **Total Archive Size:** **`45.9 GB`** across four `.7z` archive files:
  1. `01_Train_Val_Lookalike_images.7z`: **23.0 GB**
  2. `01_Train_Val_Lookalike_mask.7z`: **426.8 kB**
  3. `01_Train_Val_No_Oil_Images.7z`: **22.9 GB**
  4. `01_Train_Val_No_Oil_mask.7z`: **416.7 kB**  
  *(Correction: Corrected from the preliminary Phase 3.2C estimate of ~8.4 GB; actual size is 45.9 GB)*
- **Sample Counts:** 685 look-alike images + 685 look-alike masks; 685 no-oil images + 685 no-oil masks (1,370 total samples).

### 3.3 Scientific Role & Semantic Compatibility
- **Scientific Role:** **`SAME-FAMILY NEGATIVE / LOOK-ALIKE HOLDOUT`**
- **Annotation Semantics:** All-zero negative masks or sparse look-alike feature masks.
- **Primary Evaluation Metric:** **False-Positive Rate / False-Alarm Pixel Ratio**, NOT positive-class IoU/Dice (which is undefined on all-zero ground truth).
- **Input Compatibility:** Native 2-channel dB GeoTIFFs ($2048 \times 2048 \times 2$).
- **Resource Burden:** High (45.9 GB compressed archive requires substantial download and storage allocation).
- **Acquisition Readiness:** **`READY FOR FUTURE ACQUISITION AUTHORIZATION`** (Specifically for false-alarm screening, subject to CAO mandate).

---

## 4. CleanSeaNet / M4D Dataset Sanity Check
- **Reference:** M. Krestenitis et al., *Remote Sensing* 2019
- **Host:** ITI-CERTH M4D Group (`https://m4d.iti.gr/oil-spill-detection-dataset/`)
- **Image Format:** 8-bit lossy RGB JPG files extracted from Sentinel-1 SAR products.
- **Annotation Geometry:** 5-class semantic masks (Sea, Oil, Look-alike, Ship, Land).
- **Physical Representation Gate:** **`YELLOW / RED`** (Lossy 8-bit JPG imagery prevents quantitative calibrated radar backscatter inference).
- **Access Model:** Restricted research access requiring institutional email application.
- **Status:** **`UNVERIFIED / YELLOW`** (Not acquisition-ready).

---

## 5. Summary Matrix of Reverified Priority Candidates

| Candidate ID | Name | Primary DOI | Stated Role | Geometry | Physical Image Format | 2-Ch EXP02C Compatibility | Total Archive Size | Independence Classification | Acquisition Readiness |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **CAND-01** | Trujillo Part III | `10.5281/zenodo.13761290` | Same-Family Holdout Test Set | Pixel-level binary mask | 2-ch GeoTIFF (reported dB, dtype UNVERIFIED) | **High (Apparent Metadata Match)** | **9.9 GB** | Same-Family Holdout | **Acquisition Halted (HTTP 403; Zero Bytes Transferred)** |
| **CAND-02** | DARTIS / East Med SAR | `10.1594/PANGAEA.980773` | Detection & False-Alarm Suite | Pascal VOC XML Bounding Boxes | 8-bit normalized JPG | **Red (Adapter Required)** | ~4.5 GB | Independent External Domain | **Not Ready (Box Geometry / 8-bit JPG)** |
| **CAND-10** | Trujillo Part II | `10.5281/zenodo.8253899` | False-Alarm & Look-Alike Suite | Pixel-level negative masks | 2-ch 16-bit GeoTIFF (dB) | **High (Native Match)** | **45.9 GB** | Same-Family Negative Holdout | **Ready for Future Authorization** |
