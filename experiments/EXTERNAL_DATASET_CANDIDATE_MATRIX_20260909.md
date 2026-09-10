# External Dataset Candidate Matrix: Marine SAR Oil Spill Benchmarks (Corrected & Reverified)
**Date of Audit:** 2026-09-09T23:06:30+05:30  
**Authority:** CAO Directive — Phase 3.2C-R / Phase 3.2D Re-verification  
**Evaluation Standard:** EVIDENCE > ASSUMPTION > CONVENIENCE  
**Acquisition Status:** **NO DATASET AUTHORIZED FOR ACQUISITION IN THIS PHASE (METADATA AUDIT ONLY)**  

---

### 1. Reverified Candidate Evaluation Matrix

| Candidate ID | Candidate Name | Primary DOI / URI | Authority & Source | Sensor & Platform | SAR Mode & Product | Polarizations | Annotation Geometry | Mask Semantics | Reported Images / Samples | Geography & Era | Spatial Indep. | Temporal Indep. | Acquisition Indep. | Pipeline Indep. | Provenance Indep. | Model Input Compatibility | Annotation Compatibility | Domain Difference | Access Type & License | Current Archive Size | Checksum Status | Primary Scientific Role | Candidate Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **CAND-01** | Trujillo Part III (Test Set) | `10.5281/zenodo.13761290` | R. Trujillo-Acatitla et al. (Zenodo) | Sentinel-1 (C-band) | IW GRD | 2-channel (calibrated $\sigma^0$ dB) | Pixel-level raster | $\{0, 1\}$ (Oil vs Non-oil) | 450 test images (150 oil, 150 look-alike, 150 clean) | Gulf of Mexico / Caribbean (2020–2023) | **NO** | **PARTIAL** | **NOT DETERMINABLE** | **NO** | **NO** | **HIGH (Native 2-ch $2048 \times 2048$ dB TIFF)** | **HIGH (Native binary $\{0, 1\}$)** | **LOW** | Open Access (CC-BY-4.0) | **9.9 GB** (`02_Test_images...7z`) | Verified (`5dce64cd7ff9...`) | **SAME-FAMILY HOLDOUT** | **ACQUISITION HALTED (ZENODO IP RATE-LIMIT HTTP 403)** |
| **CAND-02** | DARTIS / East Med SAR | `10.1594/PANGAEA.980773` | Y.-J. Yang, S. Singha et al. (ESSD 2025, PANGAEA) | Sentinel-1 (C-band) | IW GRD | 1-channel (VV normalized 0–255) | **Pascal VOC XML Bounding Boxes** | Oil slicks (3,225 objects) + Look-alikes | 1,365 oil patches + 2,290 look-alike patches | Eastern Mediterranean Sea (2019) | **YES** | **YES** | **NOT DETERMINABLE** | **YES** | **YES** | **RED (8-bit JPG, not quantitative dB)** | **RED (Bounding boxes, no pixel masks)** | **HIGH** | Open Access (CC-BY-4.0) | ~4.5 GB (PANGAEA dataset) | Exposed on PANGAEA | **DETECTION-ONLY / BOX-ANNOTATED** | **NOT READY FOR SEGMENTATION** |
| **CAND-03** | CleanSeaNet / M4D Dataset | `https://m4d.iti.gr/oil-spill-detection-dataset/` | M. Krestenitis et al. (ITI-CERTH / EMSA) | Sentinel-1 (C-band) | SAR GRD | Unspecified (saved as 8-bit JPG) | Pixel-level semantic | 5 classes: Sea (0), Oil (1), Look-alike (2), Ship (3), Land (4) | 1,000 train + 110 test patches | European / Mediterranean waters | **YES** | **YES** | **NOT DETERMINABLE** | **YES** | **YES** | **LOW / BLOCKED (8-bit lossy JPG)** | **YELLOW (5-class mapping required)** | **HIGH** | Restricted (Application required) | ~1.2 GB | None | **EXTERNAL DOMAIN GENERALIZATION** | **YELLOW (RESTRICTED / LOSSY JPG)** |
| **CAND-04** | Refined Deep-SAR SOS | `10.5281/zenodo.15298010` | D. Zuenko & I. Khaidarova (Zenodo 2025, refining Zhu et al. 2021) | Mixed: ALOS PALSAR + Sentinel-1A | Mixed modes | Single-channel (PALSAR HH, S1 VV) | Pixel-level binary | Binary $\{0, 1\}$ (manually refined) | 4,193 Sentinel-1 patches from **only 7 parent scenes** | Kuwait / Persian Gulf (Aug 11, 2017) | **YES** | **YES** | **NOT DETERMINABLE** | **YES** | **YES** | **LOW / BLOCKED (8-bit image slices)** | **YELLOW (Severe patch replication)** | **MEDIUM-HIGH** | Open Access (CC-BY-4.0) | 1.13 GB (`images.zip` + `masks.zip`) | Verified (`e527287...`) | **SAME-EVENT LOCALIZED BENCHMARK** | **YELLOW (SCENE-CLUSTERING RISK)** |
| **CAND-05** | CSIRO Sentinel-1 Oil Spill | `https://data.csiro.au/collection/csiro:57430` | CSIRO Data Portal (Australia) | Sentinel-1 (C-band) | IW GRD | Single-band grayscale ($400 \times 400$) | **Image-level label (NO PIXEL MASK)** | Binary $\{0, 1\}$ (Chip-level label) | 5,630 image chips ($400 \times 400$) | Australian waters / Global | **YES** | **YES** | **NOT DETERMINABLE** | **YES** | **YES** | **LOW (Grayscale chips)** | **RED (FATAL: Classification only)** | **HIGH** | Open Access (CSIRO Open) | ~1.8 GB | Verified | **FALSE-ALARM / SCREENING ONLY** | **REJECTED (FOR SEGMENTATION)** |
| **CAND-06** | MORP-Synth Peruvian S1 | Unpublished (arXiv:2512.02290v1) | A. Juarez, L. Salsavilca et al. (UNALM CIMA) | Sentinel-1 (C-band) | IW GRD | 1-channel (VV, calibrated $\sigma^0$ 10m) | Pixel-level semantic | 5 classes harmonized with CleanSeaNet | 2,112 patches ($512 \times 512$) from 40 scenes | Peruvian Coast (Humboldt Current, 2014–2024) | **YES** | **YES** | **NOT DETERMINABLE** | **YES** | **YES** | **MEDIUM (Adapter required for 1-ch VV)** | **HIGH (CleanSeaNet semantics)** | **HIGH** | **UNPUBLISHED (Awaiting release)** | Unknown (~3.2 GB estimated) | None | **TARGET EXTERNAL GENERALIZATION** | **NOT-YET-AVAILABLE (UNRESOLVED)** |
| **CAND-07** | QPOSD | `10.5281/zenodo.19258036` | S. Jamal & Y. Li (Beijing Univ. of Tech.) | **Airborne NASA UAVSAR** | PolSAR MLC | **9-channel Quad-Pol coherency ($T$)** | Pixel-level 4-class | 4 classes: Sea, Oil, Look-alike, Land | 41 airborne flight lines | U.S. Gulf of Mexico (2010–2022) | Unrelated | Unrelated | Unrelated | Unrelated | Unrelated | **RED (FATAL: 9-ch airborne L-band)** | **RED (Incompatible class boundaries)** | Irrelevant | Open Access (CC-BY-4.0) | 3.87 GB | Verified (`876771b...`) | Polarimetric SAR research only | **REJECTED (PROVENANCE MISMATCH)** |
| **CAND-08** | Kaggle Sentinel-1 Oil Spill | `kaggle.com/datasets/harikrishnacs` | harikrishnacs (Kaggle user) | Sentinel-1 (claimed) | Grayscale patches | Grayscale (1-channel) | Image-level binary | Oil vs No-oil | Unverified patches | Unverified | Unverified | Unverified | Unverified | Unverified | Unverified | **LOW (Grayscale patches)** | **RED (FATAL: Classification only)** | Unknown | Kaggle download | ~250 MB | None | Scratch testing only | **REJECTED (UNVERIFIED MIRROR)** |
| **CAND-09** | MADOS | `10.5281/zenodo.8286950` | K. Kikaki et al. (Zenodo 2023) | **Sentinel-2 MSI (Optical)** | Level-1C / 2A | Multispectral optical bands | Pixel-level semantic | Debris, oil, sea, clouds | Multi-scene optical patches | Global coastal waters | Irrelevant | Irrelevant | Irrelevant | Irrelevant | Irrelevant | **RED (FATAL: Optical multispectral)** | Optical segmentation | Irrelevant | Open Access (CC-BY-4.0) | ~6.5 GB | Verified | Optical marine debris research | **REJECTED (SENSOR MISMATCH)** |
| **CAND-10** | Trujillo Part II (Look-alikes) | `10.5281/zenodo.8253899` | R. Trujillo-Acatitla et al. (Zenodo) | Sentinel-1 (C-band) | IW GRD | 2-channel (calibrated $\sigma^0$ dB) | Pixel-level binary | 685 look-alikes + 685 clean scenes | 1,370 images ($2048 \times 2048$) | Gulf of Mexico / Caribbean (2020–2023) | **NO** | **PARTIAL** | **PARTIAL / UNKNOWN** | **NO** | **NO** | **HIGH (Native 2-ch $2048 \times 2048$ dB TIFF)** | **HIGH (All-zero / negative masks)** | **LOW** | Open Access (CC-BY-4.0) | **45.9 GB** (4 archives total) | Verified | **SAME-FAMILY NEGATIVE HOLDOUT** | **READY FOR FUTURE AUTHORIZATION** |

---

### 2. Disentangled Model-Compatibility Matrix for Frozen EXP02C

Frozen Production Model EXP02C Contract:
- **Input Channels:** 2 channels (dual-polarization)
- **Input Representation:** Calibrated radar backscatter $\sigma^0$ in decibels (dB)
- **Normalization:** Frozen training statistics (Channel Means: `[-33.2331369895, -19.9412158528]`, Channel Stds: `[6.4899856660, 4.5313456848]`; physical channel order mapping UNKNOWN)
- **Spatial Resolution:** $10\text{ m}$ pixel spacing
- **Decision Threshold:** `0.22` (strictly locked)

| Candidate ID | Provenance Compatibility | Input Representation Compatibility | Architectural Compatibility | Annotation Compatibility | Scientific Evaluation Compatibility |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **CAND-01** (Trujillo Part III) | **PASS** | **PASS (Native float dB TIFF)** | **PASS (Native 2-channel)** | **PASS (Native binary mask)** | **PASS (As same-family holdout test set)** |
| **CAND-02** (DARTIS / East Med) | **PASS** | **FAIL / RED (8-bit normalized JPG)** | **FAIL / RED (1-channel VV)** | **FAIL / RED (Pascal VOC Bounding Boxes)** | **FAIL (Cannot evaluate pixel IoU/Dice without raster masks)** |
| **CAND-03** (CleanSeaNet / M4D) | **PASS** | **FAIL / RED (8-bit lossy JPG)** | **UNKNOWN / YELLOW (3-ch JPG representation)** | **YELLOW (Requires 5-to-2 class mapping)** | **CONDITIONAL (Subject to lossy quantization impact)** |
| **CAND-04** (Refined SOS) | **PASS** | **FAIL / RED (8-bit PNG/JPG)** | **FAIL / RED (1-channel)** | **YELLOW (Severe scene-replication bias)** | **LOW (7 parent scenes on 1 date)** |
| **CAND-05** (CSIRO) | **PASS** | **FAIL / RED (8-bit grayscale)** | **FAIL / RED (1-channel)** | **FAIL / RED (Zero pixel segmentation masks)** | **FAIL (Classification only)** |
| **CAND-06** (MORP-Synth) | **UNRESOLVED** | **LIKELY PASS (Calibrated $\sigma^0$ 10m)** | **FAIL / YELLOW (1-channel VV requires adapter)** | **PASS (5-class CleanSeaNet semantics)** | **HIGH (Target external domain once released)** |
| **CAND-10** (Trujillo Part II) | **PASS** | **PASS (Native float dB TIFF)** | **PASS (Native 2-channel)** | **PASS (All-zero / negative masks)** | **PASS (Specifically for false-alarm pixel quantification)** |

---

### 3. Disentangled Independence Matrix

| Candidate ID | Spatial Independence | Temporal Independence | Acquisition Independence | Pipeline Independence | Provenance Independence | Basis of Determination |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **CAND-01** (Trujillo Part III) | **NO** | **PARTIAL** | **NOT DETERMINABLE** | **NO** | **NO** | Same Gulf of Mexico / Caribbean basin; disjoint test dates in same era (2020–2023); parent product IDs not enumerated; identical SNAP dB pipeline and IPICYT author team. |
| **CAND-02** (DARTIS / East Med) | **YES** | **YES** | **NOT DETERMINABLE** | **YES** | **YES** | Eastern Mediterranean basin; acquired in 2019 (prior to Trujillo dataset); parent Sentinel-1 footprints not cross-matched; independent DLR/GEOMAR pipeline and German/Israeli consortium. |
| **CAND-03** (CleanSeaNet / M4D) | **YES** | **YES** | **NOT DETERMINABLE** | **YES** | **YES** | European / Mediterranean coastal waters; 2015–2019 acquisitions; EMSA operational alert pipeline; ITI-CERTH institutional origin. |
| **CAND-04** (Refined SOS) | **YES** | **YES** | **NOT DETERMINABLE** | **YES** | **YES** | Persian Gulf (Kuwait coast); single event on Aug 11, 2017; CUG Wuhan / Zuenko pipeline. |
| **CAND-05** (CSIRO) | **YES** | **YES** | **NOT DETERMINABLE** | **YES** | **YES** | Australasian coastal waters; 2016–2022 era; CSIRO institutional origin. |
| **CAND-06** (MORP-Synth) | **YES** | **YES** | **NOT DETERMINABLE** | **YES** | **YES** | Peruvian Pacific (Humboldt Current upwelling); 2014–2024 era; UNALM CIMA institutional origin. |
| **CAND-10** (Trujillo Part II) | **NO** | **PARTIAL** | **NOT DETERMINABLE** | **NO** | **NO** | Same Gulf of Mexico / Caribbean basin; disjoint dates; identical SNAP dB pipeline and IPICYT author team. |

---

### 4. Authoritative Resource & Archive Burden Refresh

| Candidate ID | Primary Archive Name | Reported Archive Size | Checksum (Algorithm & Hash) | Expected Storage on Disk | Download / Storage Burden Rating |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **CAND-01** | `02_Test_images_and_ground_truth.7z` | **9.9 GB** ($10,630,044,484$ bytes) | MD5: `5dce64cd7ff9d80189d13504bd3bcbf5` | ~18 GB extracted (estimated, unmeasured) | **Moderate** |
| **CAND-02** | PANGAEA dataset archive | **~4.5 GB** | Provided via PANGAEA manifest | ~6 GB extracted | **Low–Moderate** |
| **CAND-03** | M4D archive | **~1.2 GB** | None publicly exposed | ~2 GB extracted | **Low** |
| **CAND-04** | `images.zip` + `masks.zip` | **1.13 GB** ($1,105,739,788$ + $28,321,809$ bytes) | MD5: `e5272875611e8b...` / `09c8a279603c...` | ~2.5 GB extracted | **Low** |
| **CAND-05** | CSIRO Collection 57430 | **~1.8 GB** | Provided via CSIRO portal | ~3 GB extracted | **Low** |
| **CAND-06** | Unpublished | **UNKNOWN** (~3.2 GB estimated) | None | UNKNOWN | **Blocked** |
| **CAND-10** | 4 files (`Lookalike_images.7z` + 3 others) | **45.9 GB** ($23.0\text{ GB} + 22.9\text{ GB} + 0.8\text{ MB}$) | Provided via Zenodo | ~85 GB extracted | **Very High** |
