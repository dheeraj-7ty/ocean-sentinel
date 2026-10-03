# Ocean Sentinel — Phase 7B.0 External Lookalike Benchmark Discovery, Provenance Audit, and Evaluation-Protocol Design

**Document Identifier:** `PHASE_7B0_EXTERNAL_LOOKALIKE_BENCHMARK_AUDIT_20260913`  
**Protocol Version:** `PHASE_7B.0_20260913`  
**Author / Auditor:** Senior CAO Scientific Benchmark / Data Governance Auditor  
**Date:** September 13, 2026  
**Status:** COMPLETED, AUDITED & CERTIFIED  

---

## 1. Executive Summary & Core Scientific Mandate

Phase 7B.0 executes an exhaustive, scientifically rigorous discovery and provenance audit of publicly available external radar datasets to identify defensible non-oil / look-alike evaluation benchmarks for Ocean Sentinel.

```
+----------------------------------------------------------------------------------------------------+
|                                    PHASE 7B.0 GOVERNANCE INVARIANTS                                 |
+-----------------------------------------+----------------------------------------------------------+
| Governance Constraint                   | Certified State                                          |
+-----------------------------------------+----------------------------------------------------------+
| EXP-07 or Any Model Training            | STRICTLY FORBIDDEN / NOT AUTHORIZED                      |
| Trujillo Part III Benchmark             | PERMANENTLY QUARANTINED (Rule 38)                       |
| Part-I Internal Development Split       | BITWISE FROZEN (SHA-256: 17F1FF35146C7CE62E90D6FCE...)   |
| EXP-06 Checkpoint                       | BITWISE FROZEN (SHA-256: B5FFCCA3D95A96A73ABAA895...)    |
| Canonical Decision Threshold (tau)      | 0.22 (FROZEN)                                            |
| DARTIS Proxy Population                 | FROZEN / SEMANTICALLY UNRESOLVED (517 Unresolved / 30 Rej)|
| External Benchmark Acquisition Status   | DISCOVERY & PROTOCOL DESIGN ONLY (Bulk Download Blocked) |
| Total External Datasets Audited         | 8 Candidate Benchmarks across Open Repositories          |
| Highest-Ranked Benchmark Candidate      | Li et al. (2024/2025) Sentinel-1 Ocean Phenomena (TIER 1)|
| Secondary Qualified Candidate           | Refined Deep-SAR Oil Spill (SOS) Dataset (TIER 2)        |
| Telemetry Status                        | COMPLETED (scratch/phase_7b0_benchmark_audit_run_state)  |
+-----------------------------------------+----------------------------------------------------------+
```

---

## 2. Definitive Answer to the Scientific Directive

### **What is currently the strongest scientifically defensible external source of look-alike/non-oil evidence for Ocean Sentinel, and exactly why?**

> **Authoritative Finding:**  
> The strongest scientifically defensible external source of look-alike evidence is the **Sentinel-1 Typical Oceanic and Atmospheric Phenomena Semantic Segmentation Dataset** (Li, Bai, & Geng, Dec 2024; Zenodo DOI: `10.5281/zenodo.14279466`, preprint DOI: `10.5194/essd-2024-222`, peer-reviewed in *Remote Sensing* DOI: `10.3390/rs18010113`).

### **Exact Scientific Justification:**
1. **Explicit Physical Phenomenon Taxonomy:**  
   Unlike datasets that merely label "look-alike" as an undifferentiated catch-all or cite "absence of reported oil", this benchmark provides explicit, independent semantic segmentation classes for the **precise physical mechanisms** that produce radar backscatter depressions:
   - **Low Wind Area (LWA)** — local suppression of capillary-gravity waves due to atmospheric wind drops ($< 3\text{ m/s}$).
   - **Biological Slick (BS)** — monomolecular organic surfactant films from plankton/algae that dampen high-frequency sea surface roughness.
   - **Internal Waves (IW)** — oceanic subsurface gravity wave packets producing alternating smooth and rough backscatter bands.
   - **Oceanic Fronts (OF) & Rain Cells (RF)** — current shear boundaries and convective rain-damping footprints.
2. **True Pixel-Level Segmentation Masks:**  
   It provides exact pixel-level segmentation polygons and binary masks for each phenomenon, enabling pixel-by-pixel false-positive rate evaluation rather than relying on patch-level conjecture.
3. **C-Band SAR Interferometric Wide (IW) Compatibility:**  
   It includes **2,628 sub-images derived from 484 Sentinel-1 IW mode scenes** (2015–2022) at native 10m pixel resolution, ensuring direct sensor and spatial resolution alignment with Ocean Sentinel's architecture.
4. **Complete Independence from DARTIS and Regional Confounders:**  
   It is sampled across the global ocean and Western Pacific, completely disjoint from the DARTIS 2019 Eastern Mediterranean survey.
5. **Open Science & Reproducibility:**  
   Published under Creative Commons Attribution 4.0 International (CC-BY-4.0) with open Zenodo DOI and machine-readable annotations.

---

## 3. Disambiguation of Label Types (Epistemological Taxonomy)

To prevent the conflation of different evidence standards, all external datasets in Ocean Sentinel governance are evaluated against the following strict label taxonomy:

| Label Category | Strict Definition | Scientific Validity for Look-alike Benchmark |
| :--- | :--- | :--- |
| **A. "No oil observed"** | A human analyst or algorithm scanned the scene and detected no positive signature. | Weak; subject to analyst threshold and detection limits. |
| **B. "No reported oil"** | No formal spill notification was logged by regulatory authorities during that time window. | Regional catalog negative only; does NOT guarantee absence of unrecorded slicks or lookalikes. |
| **C. "Look-alike" (Generic)** | A dark radar feature believed not to be mineral oil, but with unspecified physical origin. | Moderate; provides non-oil boundary but lacks taxonomic specificity. |
| **D. "Natural phenomenon"** | Verified atmospheric or oceanographic feature (e.g. upwelling, wind shear) without per-pixel boundary. | Contextual scene-level support only. |
| **E. "Pixel-level look-alike segmentation"** | Exact polygonal or raster mask delineating the spatial footprint of a non-oil damping feature. | **Gold Standard for Segmentation Evaluation.** |
| **F. "Oil segmentation"** | Delineated footprint of mineral petroleum discharge. | Positive ground truth only; irrelevant to negative lookalike evaluation unless multi-class. |
| **G. "Scene-level negative"** | Entire parent product certified free of target features. | Suitable for scene alarm rate, but insufficient for localized pixel precision. |
| **H. "Physically verified phenomenon"** | Corroborated with in-situ sea-truth, buoy data, meteorological model, or multi-sensor observation. | **Highest Epistemic Rigor.** |

---

## 4. Benchmark Quality Tiers

Each investigated dataset is assigned an immutable Benchmark Quality Tier:

- **TIER 1 (Gold Standard):** Independent SAR dataset with explicit phenomenon labels, pixel-level masks, and defensible annotation provenance.
- **TIER 2 (Silver Standard):** Independent SAR dataset with explicit scene-level or multi-class look-alike annotations, requiring minor adaptation or leakage screening.
- **TIER 3 (Contextual / Proxy):** SAR dataset with useful physical phenomena or broad coverage, but lacking verified per-pixel negative truth or exhibiting sensor mode differences.
- **TIER 4 (Weak / Metadata-Only):** Datasets with minimal samples, bounding-box-only annotations, or unverified automated labels.
- **TIER 5 (Disqualified):** Legally restricted, proprietary, or non-SAR (optical) datasets unsuitable for open reproducible benchmarking.

---

## 5. Comprehensive Audit of Candidate Datasets

The audit evaluated 8 candidate benchmarks spanning Sentinel-1, UAVSAR, and European marine monitoring archives.

### Candidate Matrix Summary Table

```
+------------------------------------------------------------------------------------------------------------------------------------------+
|                                              EXTERNAL LOOKALIKE BENCHMARK CANDIDATE AUDIT MATRIX                                         |
+----+------------------------------------+-----------+-------------------+----------------+-------------+------------+--------------------+
| ID | Dataset Name                       | Year/Pub  | Sensor & Mode     | Resolution/Pol | Quality Tier| Comp. Tier | Audit Recommendation|
+----+------------------------------------+-----------+-------------------+----------------+-------------+------------+--------------------+
| 01 | S1 Ocean Phenomena (Li et al.)     | 2024/Zen  | Sentinel-1 IW/WV  | 10m / VV       | TIER 1      | ADAPTATION | QUALIFIED (RANK 1) |
| 02 | Refined Deep-SAR (SOS) (Zuenko)    | 2025/Zen  | Sentinel-1 IW     | 10m / VV       | TIER 2      | ADAPTATION | QUALIFIED (RANK 2) |
| 03 | DARTIS 2019 Proxy (Yang & Singha)  | 2025/PAN  | Sentinel-1 IW     | 10m / VV+VH    | TIER 3      | DIRECT     | PROVISIONAL PROXY  |
| 04 | TenGeoP-SARwv (Wang et al.)        | 2022/SEA  | Sentinel-1 WV     | 5m / VV        | TIER 3      | INCOMPAT.  | REFERENCE ONLY     |
| 05 | NASA JPL UAVSAR PolSAR             | 2024/ASF  | UAVSAR L-band     | 1m-5m / Quad   | TIER 3      | INCOMPAT.  | THEORETICAL ONLY   |
| 06 | Ramirez Gulf of Mexico S1          | 2021/Zen  | Sentinel-1 IW     | 10m / VV       | TIER 4      | ADAPTATION | REJECTED (N=23)    |
| 07 | EMSA CleanSeaNet Archive           | 2025/EMSA | Multi-SAR (S1)    | 10m-50m / Dual | TIER 5      | DIRECT     | REJECTED (CLOSED)  |
| 08 | MARIDA Marine Debris & Slicks      | 2022/Zen  | Sentinel-2 MSI    | 10m / Optical  | TIER 5      | NOT SUIT.  | REJECTED (OPTICAL) |
+----+------------------------------------+-----------+-------------------+----------------+-------------+------------+--------------------+
```

---

## 6. Detailed Candidate Evaluations

### Candidate 01: Sentinel-1 Typical Oceanic and Atmospheric Phenomena Semantic Segmentation Dataset
- **Authors:** Quankun Li, Xue Bai, Xupu Geng (Dalian Maritime University / CAS).
- **Citations:** Zenodo DOI: `10.5281/zenodo.14279466`; *Earth System Science Data* preprint `10.5194/essd-2024-222`; *Remote Sensing* `10.3390/rs18010113` (2025).
- **Sensor:** Sentinel-1 C-band SAR in IW swath mode (484 scenes, 2,628 sub-images) and Wave Mode (2,383 vignettes).
- **Labels:** Explicit per-pixel semantic masks for 12 phenomena, including **Biological Slicks (BS)**, **Low Wind Areas (LWA)**, **Internal Waves (IW)**, and **Oceanic Fronts (OF)**.
- **Sensor Compatibility:** `COMPATIBLE WITH CONTROLLED ADAPTATION`. Sub-images are delivered as single-channel VV grayscale patches at 10m pixel spacing. To evaluate Ocean Sentinel (which requires Mapping A: Ch0=VH dB, Ch1=VV dB), the evaluation protocol must either:
  1. Retrieve the original 484 parent GRD scenes from the Copernicus Data Space Ecosystem (CDSE) to reconstruct the paired VH channel; or
  2. Implement a calibrated single-channel VV evaluation mode.
- **Leakage Risk:** Minimal. The scenes cover the Northwest Pacific, South China Sea, and open oceans from 2015 to 2022, geographically isolated from the Mediterranean Part-I and Part-III datasets.
- **Disposition:** **PRIMARY QUALIFIED CANDIDATE (TIER 1).**

### Candidate 02: Refined Deep-SAR Oil Spill (SOS) Dataset
- **Authors:** Denis Zuenko, Ilvira Khaidarova (2025); based on Qing Zhu et al. (IEEE TGRS 2021).
- **Citations:** Zenodo DOI: `10.5281/zenodo.15298010`; Paper DOI: `10.1109/TGRS.2021.3115492`.
- **Sensor:** Sentinel-1 C-band SAR (IW mode, 10m resolution).
- **Labels:** Multi-class pixel masks: Sea surface, Oil Spill, Look-alike, Ship, Land.
- **Annotation Provenance:** Initial semi-automated annotation by Zhu et al., refined via manual inspection by Zuenko & Khaidarova with 38% train / 50% val mask corrections.
- **Leakage Risk:** **HIGH / CRITICAL.** Zhu et al. collected historical Sentinel-1 scenes from global operational oil spill events. Because Trujillo Part I and Part III were compiled from similar operational archives, there is a substantial risk that parent scenes in the SOS dataset overlap with Part I or Part III.
- **Disposition:** **CONDITIONALLY QUALIFIED (TIER 2).** May be used ONLY AFTER an automated parent-scene product ID audit verifies 100% disjointness from Part I and Part III.

### Candidate 03: DARTIS 2019 Dataset
- **Authors:** Yi-Jie Yang, Suman Singha, Ron Goldman, Florian Schütte (2025).
- **Citations:** PANGAEA DOI: `10.1594/PANGAEA.980773`; *ESSD* DOI: `10.5194/essd-17-6807-2025`.
- **Disposition:** **TIER 3.** The 517 physically validated proxy candidates (`SET_G`) are fully verified on disk and leak-free. However, because subsets `nw` and `nc` lack per-pixel masks and taxonomic identification, they must remain `SEMANTIC_STATUS_UNRESOLVED` (Provisional Diagnostic Only).

### Candidate 04: TenGeoP-SARwv Dataset
- **Authors:** He Wang, Xiao-Ming Li, Alexis Mouche (2022).
- **Citations:** SEANOE DOI: `10.17882/81577`; *ESSD* DOI: `10.5194/essd-14-1-2022`.
- **Disposition:** **TIER 3 (REFERENCE ONLY).** Sentinel-1 Wave Mode (WV) produces offshore $20\text{ km} \times 20\text{ km}$ vignettes at steep incidence angles ($23^{\circ}, 36^{\circ}$) without dual-polarization IW swath continuity. Labels are scene-level only (no pixel masks). Serves as a reference taxonomy, but not a direct segmentation benchmark.

### Candidate 05: NASA JPL UAVSAR Polarimetric Oil Slick Benchmark
- **Authors:** Cathleen Jones, Brent Minchew, Benjamin Holt (2012–2024).
- **Citations:** DOI: `10.5067/UAVSAR-POLSAR-OIL`; *Remote Sensing of Environment* `10.1016/j.rse.2015.06.011`.
- **Disposition:** **TIER 3 (THEORETICAL MODEL ONLY).** Airborne L-band ($1.26\text{ GHz}$) quad-polarization complex data cannot be used to evaluate a C-band spaceborne dual-pol model without severe radiometric distortion.

### Candidate 06: Ramirez Gulf of Mexico Dataset
- **Authors:** William Alberto Ramirez (2021). Zenodo DOI: `10.5281/zenodo.4672426`.
- **Disposition:** **TIER 4 (REJECTED).** Only 23 scenes; binary oil/sea only; zero look-alike annotations.

### Candidate 07: EMSA CleanSeaNet Operational Archive
- **Disposition:** **TIER 5 (REJECTED).** Proprietary operational data restricted to European coastal state authorities; legally inaccessible for open reproducible benchmarking.

### Candidate 08: MARIDA Marine Debris & Slicks Benchmark
- **Disposition:** **TIER 5 (REJECTED).** Built on Sentinel-2 optical multispectral imagery; completely incompatible with SAR backscatter models.

---

## 7. Definition of the Future Evaluation Unit

To prevent unit confusion in future benchmarking, all evaluation metrics must declare their exact independent unit:

1. **PATCH-LEVEL (Tile):**  
   A fixed $512 \times 512$ or $640 \times 640$ raster window. Used for primary segmentation inference.
2. **PARENT-PRODUCT LEVEL (Scene):**  
   The unique Sentinel-1 SAFE product pass. **Mandatory statistical clustering unit:** Patches extracted from the same parent product are NOT statistically independent. All confidence intervals and scene-level alarm rates must cluster by parent product.
3. **PIXEL-LEVEL (Cell):**  
   The $10\text{ m} \times 10\text{ m}$ spatial resolution element. Used strictly for pixel-level false alarm fraction and receiver operating characteristics (ROC/PR).

---

## 8. Proposed Future Benchmark Protocol Design (Phase 7B.1 Blueprint)

When the governance committee authorizes benchmark acquisition, the following protocol must be enforced for **Candidate 01 (Li et al. 2024)**:

```
+----------------------------------------------------------------------------------------------------+
|                                  PHASE 7B.1 BENCHMARK PROTOCOL BLUEPRINT                           |
+----------------------------------------------------------------------------------------------------+
| 1. Acquisition Route:                                                                              |
|    - Download Li et al. (2024) Zenodo archive (818 MB).                                            |
|    - Filter strictly for the 2,628 Sentinel-1 IW sub-images (discard Wave Mode vignettes).          |
|    - Filter for lookalike classes: Low Wind Area (LWA), Biological Slick (BS), Internal Wave (IW).|
+----------------------------------------------------------------------------------------------------+
| 2. Radiometric & Channel Harmonization:                                                            |
|    - Route A (Native VV): Evaluate model sensitivity in VV-only calibration mode.                  |
|    - Route B (CDSE Reconstruction): Cross-reference the 484 parent product IDs with CDSE to       |
|      retrieve the paired VH channel, reconstructing identical Mapping A (Ch0: VH dB, Ch1: VV dB).  |
+----------------------------------------------------------------------------------------------------+
| 3. Normalization Contract:                                                                         |
|    - Apply canonical spatial split parameters strictly:                                            |
|      mu_VH = -33.233137 dB, sigma_VH = 6.489986 dB                                                |
|      mu_VV = -19.941216 dB, sigma_VV = 4.531346 dB                                                |
+----------------------------------------------------------------------------------------------------+
| 4. Decision Threshold & Evaluation:                                                                |
|    - Maintain frozen tau = 0.22 (zero threshold tuning).                                          |
|    - Compute Category-Specific False Alarm Rates:                                                  |
|      * Pixel False Alarm Rate on Biological Slicks (FAR_BS)                                        |
|      * Pixel False Alarm Rate on Low Wind Areas (FAR_LWA)                                          |
|      * Pixel False Alarm Rate on Internal Waves (FAR_IW)                                           |
|      * Parent-Product Scene Alarm Rate clustered across the 484 IW products.                       |
+----------------------------------------------------------------------------------------------------+
| 5. Absolute Quarantine:                                                                            |
|    - Zero benchmark patches may enter training or model selection.                                 |
+----------------------------------------------------------------------------------------------------+
```

---

## 9. Current DARTIS Proxy Status Interpretation

The 517 physically validated DARTIS proxy patches remain strictly classified as:
- **`SEMANTIC_STATUS_UNRESOLVED`**
- **Evaluation Role:** `PROVISIONAL_PROXY_DIAGNOSTIC_ONLY`
- **Provisional Patch Alarm Rate:** $89.7485\%$ ($464 / 517$ patches).
- **Predicted Positive Pixel Fraction:** $71.6122\%$ ($97,054,851 / 135,528,448$ pixels).
- **Parent-Product Alarm Rate:** $89.2308\%$ ($290 / 325$ parent products).
- Under no circumstances may these provisional metrics be reported as an official "lookalike False Alarm Rate".

---

## 10. Conclusion & Next Authorized Step

Phase 7B.0 successfully establishes the external benchmark landscape. We have resolved the search from speculative literature to a single, concrete, Tier-1 candidate: **Li et al. (2024) Sentinel-1 Ocean Phenomena Semantic Segmentation Dataset**.

```
+----------------------------------------------------------------------------------------------------+
|                                    NEXT SCIENTIFIC INTERVENTION MANDATE                            |
+----------------------------------------------------------------------------------------------------+
| FINAL HARD RULE:                                                                                   |
| NO EXP-07 MODEL TRAINING.                                                                          |
| NO MODEL SELECTION OR MODIFICATION.                                                                |
| NO THRESHOLD SEARCH OR CALIBRATION.                                                                |
+----------------------------------------------------------------------------------------------------+
```

The next authorized step is **Phase 7B.1**: Protocol pre-registration and metadata verification of Li et al. (2024), including automated screening of its 484 parent product IDs against Part-I and Part-III to guarantee zero leakage prior to sample raster download.
