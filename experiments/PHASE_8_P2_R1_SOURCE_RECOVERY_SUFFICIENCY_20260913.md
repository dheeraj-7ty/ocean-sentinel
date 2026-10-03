# PHASE 8-P2-R1: OPS-01 SOURCE IMAGERY RECOVERY, MATERIALIZATION SUFFICIENCY & DATASET SCOPE AUDIT
**Authoritative Forensic Source Recovery & Dataset Sufficiency Audit Report**  
**Date:** 2026-09-13  
**Status:** COMPLETE & AUDITED  
**Repository Branch:** `master`  
**Evaluation Target:** Candidate OPS-01 Source Recoverability, Scope Definition, and Pre-Training Sufficiency Gate

---

## 1. Executive Verdict

**FINAL DECISION:**
### **C. OPS-01 SOURCE DATA INSUFFICIENT — FURTHER RECOVERY REQUIRED**

While the Phase 8-P2 dataset-construction mechanics and grouping firewalls were functionally verified, this forensic audit demonstrates that the physical dataset materialized to date (9 image/mask pairs from 2 parent acquisitions) is **scientifically insufficient** to justify authorizing Phase 8-P3 (Final Pre-Training Audit & Compute Budget Specification).

### Core Forensic Audit Findings
1. **DEV and HOLDOUT Partitions are Physically Empty:**
   Although the parent-scene grouping firewall correctly partitions the 2,162 cataloged parent groups (70% / 15% / 15%), **100% of the 9 physically materialized samples belong to Controls 1 and 2, which are assigned exclusively to TRAIN**. Both DEV and HOLDOUT contain **0 physically materialized samples**. A pre-training audit cannot evaluate generalization or model behavior against empty partitions.
2. **Six Out of Ten Operational Phenomena Classes are Completely Absent:**
   Atmospheric Front (AF), Biological Slicks (BS), Low Wind Area (LWA), Oceanic Front (OF), Oceanic Eddy (Eddy), and Artificial / Anthropogenic Objects (HM) have **0 samples and 0 pixels** in the materialized dataset.
3. **Anthropogenic Clutter (HM) Coverage Gap:**
   HM is **completely absent** (0 samples, 0 pixels). OPS-01 cannot claim vessel/platform false-alarm discrimination capability without physical recovery of HM-bearing scenes (which exist in 202 scenes across the full IW catalog).
4. **Source Recoverability is Confirmed on AWS S3 Open Data:**
   All 12 control products (47 slices) have been confirmed online and accessible via public HTTP GET on AWS Open Data (`sentinel-s1-l1c.s3.amazonaws.com`). Remote windowed reading via GDAL `/vsicurl/` makes recovering hundreds of additional slices technically feasible without full multi-gigabyte downloads.
5. **Wave Mode (WV) Must Remain Outside Current Scope:**
   The 2,383 WV vignettes (from 1,678 orbit passes) represent Wave Mode SLC data with fundamentally different acquisition geometry, resolution, and preprocessing. WV is formally designated **`OUTSIDE_CURRENT_SCOPE`** to prevent artificial catalog inflation.

### Epistemic & Scientific Boundary
```
CATALOGED_LABEL              ≠ PHYSICALLY_AVAILABLE_IMAGE
PHYSICALLY_AVAILABLE_IMAGE   ≠ ALIGNMENT_VERIFIED
ALIGNMENT_SUPPORTED          ≠ HISTORICAL_GENERATION_PROVEN
CONSTRUCTED_SAMPLE           ≠ TRAINING-ELIGIBLE_SAMPLE
TRAIN/DEV/HOLDOUT PLAN       ≠ ACTUAL USABLE PHYSICAL DATASET
PASSING TESTS                ≠ SCIENTIFIC SUFFICIENCY
```
- **Permanent Formulation:** *"OPS-01 uses an empirically supported correspondence hypothesis under a conditional geographic alignment model."*
- **Empirical Hypothesis:** *"10× block mean is an empirically supported correspondence hypothesis."* (Never: *"proven historical fact."*)
- **Residual Limitation:** 15.79 m is a conditional residual under Model-B assumptions, strictly prohibited from being labeled an independent physical accuracy metric.

---

## 2. P2 Previous-State Reconciliation

Phase 8-P2 successfully verified:
- Ingestion mechanics from Sentinel-1 Level-1 GRD measurement COGs via `/vsicurl/`.
- Spatial block mean downsampling ($2,560 \times 2,560 \to 256 \times 256$).
- Bitwise reproducible manifests and 100% test pass rates across 17 dataset guardrails.

However, forensic review reveals that P2 materialized only the 9 slices corresponding to local Li GeoTIFFs in `scratch/li_sample/Image_Geo/`. The remaining 5,002 cataloged slices were marked `EXCLUDED_MISSING_PHYSICAL_IMAGERY`. Because Controls 1 and 2 both fell into the TRAIN split under deterministic hashing, the physical dataset contains:
- TRAIN: 9 samples (100% of physical data)
- DEV: 0 samples
- HOLDOUT: 0 samples

**Reconciliation Verdict:** The pipeline functions correctly, but the physical data volume is insufficient for scientific pre-training.

---

## 3. Catalog vs. Physical Inventory

The complete candidate population was reconciled from authoritative manifests (`li_iw_source_scene_manifest.json` and `li_wv_source_lineage_manifest.json`):

| Cohort | Parent Groups | Total Slices | Physical Labels Available | Local GeoTIFFs Available | Materialized Derived Images |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **IW Mode Slices** | 484 scenes | 2,628 | 2,628 (100.0%) | 9 (0.34%) | 9 (0.34%) |
| - *12 Control Scenes* | 12 scenes | 47 | 47 (100.0%) | 9 (19.15%) | 9 (19.15%) |
| - *472 Untested Scenes* | 472 scenes | 2,581 | 2,581 (100.0%) | 0 (0.00%) | 0 (0.00%) |
| **WV Mode Vignettes** | 1,678 orbit passes | 2,383 | 2,383 (100.0%) | 0 (0.00%) | 0 (0.00%) |
| **Total Candidate Population** | **2,162 groups** | **5,011** | **5,011 (100.0%)** | **9 (0.18%)** | **9 (0.18%)** |

> [!CAUTION]
> **Label Presence ≠ Image Availability:** All 5,011 candidate slices possess label masks in `scratch/all_labels/label/*.png`. However, exactly 9 possessed local Li GeoTIFFs. Reporting 5,011 samples as "the dataset" when only 9 images are physically present is a severe provenance conflation.

---

## 4. Source Availability State Definitions

Every candidate sample in `data/metadata/ops01_candidate_population_ledger_v1.json` is classified into one of 14 mutually exclusive states:

| Source Availability State | Count | % of Population | Description |
| :--- | :--- | :--- | :--- |
| **`CONSTRUCTED`** | 9 | 0.18% | Materialized into derived $256 \times 256$ GeoTIFF and verified against label mask. |
| **`PHYSICAL_IMAGE_PRESENT_REMOTE_CONFIRMED`** | 37 | 0.74% | Parent Level-1 product confirmed online on AWS S3 Open Data; unmaterialized. |
| **`METADATA_ONLY`** | 2,578 | 51.45% | Untested IW scenes cataloged by SAFE syntax; archive presence not yet queried. |
| **`EXCLUDED_DEFICIENT_DATA_OS`** | 4 | 0.08% | Mineral Oil Spill class slices permanently excluded from OPS-01 training. |
| **`OUTSIDE_CURRENT_SCOPE`** | 2,383 | 47.56% | Wave Mode SLC vignettes held for separate future specialization. |
| **Total** | **5,011** | **100.00%** | **Exhaustive and mutually exclusive.** |

---

## 5. IW Source Recovery

- **Target Population:** 484 unique IW parent scenes (2,628 candidate slices).
- **Control Cohort (12 Scenes, 47 Slices):**
  - **100% of the 12 control scenes** were probed on AWS Open Data S3 (`sentinel-s1-l1c.s3.amazonaws.com/GRD/...`).
  - **12 / 12 returned HTTP 200 OK** with valid `measurement/iw-vv.tiff` streams (file sizes 300.4 MB to 712.0 MB).
  - All 12 products have verified ESA SAFE granule identities, NASA ASF DAAC MD5 checksums, and CDSE catalog records.
- **Untested Cohort (472 Scenes, 2,581 Slices):**
  - All 472 scenes have unambiguous acquisition timestamps, orbit numbers, and data-take IDs.
  - S3 paths can be resolved deterministically using standard Sentinel-1 UTC timestamp and orbit metadata.

---

## 6. WV Source Recovery & Scope Decision

- **Vignettes Cataloged:** 2,383 vignettes across 1,678 orbit passes.
- **Sensor Mode:** Wave Mode (WV) Single Look Complex (SLC).
- **Physical Characteristics:** Small $20 \times 20\text{ km}$ imagettes acquired at 100 km intervals in open oceans; complex I/Q representation; nominal resolution $\sim 5\text{ m} \times 5\text{ m}$.
- **Methodological Conflict:**
  - IW uses Level-1 Ground Range Detected (GRD) with nominal 10 m pixel spacing and bilinear cartesian crop indexing.
  - WV requires SLC processing, multilooking, and vignette boundary handling that differ substantially from IW GRD.
  - Class composition is heavily skewed: 53.1% Pure Oceanic Waves (POW) and 16.7% Icebergs (IB).
- **Formal Scope Decision:**
  > **`WV_MODE = OUTSIDE_CURRENT_SCOPE`**
  >
  > Wave Mode vignettes must **not** be blended into the current OPS-01 candidate dataset. WV is reserved for a future dedicated deep-ocean wave/sea-ice benchmark.

---

## 7. Source Product Deduplication

In SAR dataset construction, slices from the same parent acquisition share identical atmospheric, sea-state, and sensor calibration properties:
- **IW Mode Slices per Scene:** Ranges from 1 to 51 slices per scene (mean 5.43 slices/scene).
- **Controls Cohort:** 12 parent products generate 47 slices (mean 3.92 slices/scene).
- **Deduplication Mandate:** Downloading or accessing the same 500 MB parent product multiple times is wasteful and error-prone. The materialization pipeline must ingest each parent scene once and extract all designated windowed slices concurrently.

---

## 8. Slice-to-Source Lineage

The geometric relationship between the Li slice index and native Level-1 raster coordinates was decoded:
- **Native Crop Size:** $2,560 \times 2,560$ native Level-1 cells.
- **Grid Layout:** Regular Cartesian grid starting at `(row=50, col=50)` with stride $\Delta\text{row} = 2,560$ and $\Delta\text{col} = 2,560$.
- **Slice Numbering Convention:** Column-major layout where slice indices increment along range lines before stepping to the next azimuth column:
  - Column 0 (`col=50`): Slices $1, \dots, N_{\text{rows}}$
  - Column 1 (`col=2610`): Slices $N_{\text{rows}}+1, \dots, 2N_{\text{rows}}$
- **Lineage Contract:** Every candidate slice maps to exactly one parent acquisition, one native crop window, and one label mask.

---

## 9. Physical Materialization Analysis

| Cohort | Slices | Parent Scenes | Materialization Status | Storage Req. |
| :--- | :--- | :--- | :--- | :--- |
| **P2 Constructed Subset** | 9 | 2 | Materialized (`data/derived/ops01/`) | 2.37 MB |
| **Remaining Control Slices** | 38 | 10 | Recoverable via AWS S3 Open Data | 10.0 MB |
| **Full IW Catalog** | 2,628 | 484 | Recoverable via AWS S3 / CDSE | 693.8 MB |
| **WV Catalog** | 2,383 | 1,678 | Outside Current Scope | N/A |

---

## 10. Alignment Construction Boundary

- **Inferred Crop Bounds:** Deterministic $2,560 \times 2,560$ native Level-1 window.
- **Aggregation:** $10 \times 10$ spatial block mean amplitude DN.
- **Orientation:** Identity (unflipped).
- **Shift:** 0 native cells offset.
- **Epistemic Classification:**
  - `geometric_alignment_status`: **`CONDITIONAL_ENGINEERING_RECONSTRUCTION`**
  - `intensity_correspondence_status`: **`EMPIRICALLY_SUPPORTED_PILOT_HYPOTHESIS`**
  - Prohibitions: No claim of physically validated georegistration. 15.79 m is not an accuracy tolerance.

---

## 11. Zero / Nodata Handling

- **Border Padding:** Deterministically cataloged in `radiometric_statistics`.
- **Zero Rule:** Valid Level-1 ocean cells have non-zero amplitude DN. True SAR zeros occur only at orbit edges or land masks.
- **Preservation:** Both raw and valid-pixel statistics ($\text{DN} > 0$) are preserved in sample metadata. Edge padding fraction across the 9 materialized samples is $0.0\%$.

---

## 12. Pixel-Space Label Audit

- Shape agreement verified: $\text{image.shape} == \text{mask.shape} == (256, 256)$.
- Pixel grid 1-to-1 match confirmed on all 9 materialized pairs.
- Unexpected class IDs: 0. Invalid label fraction: $0.0\%$.

---

## 13. Class Coverage Sufficiency Audit

A rigorous cross-cohort comparison of semantic class representation reveals critical capability gaps:

| Class ID | Abbreviation | Class Name | 9 Materialized Slices | 47 Control Slices | All 2,628 IW Slices | All 2,383 WV Vignettes | Current Physical Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **0** | **BG** | Background / Clean Sea | 9 slices (336k px) | 36 slices (905k px) | 1,267 slices (26.7M px) | 502 slices (5.5M px) | **Represented** (2 parents) |
| **1** | **AF** | Atmospheric Front | **0 slices (0 px)** | 3 slices (12k px) | 311 slices (1.6M px) | 333 slices (2.1M px) | **COMPLETELY ABSENT** |
| **2** | **BS** | Biological Slicks | **0 slices (0 px)** | 2 slices (122k px) | 596 slices (27.9M px) | 438 slices (16.3M px) | **COMPLETELY ABSENT** |
| **3** | **IB** | Iceberg | **0 slices (0 px)** | 0 slices (0 px) | 0 slices (0 px) | 398 slices (261k px) | **WV Only / Outside Scope** |
| **4** | **LWA** | Low Wind Area | **0 slices (0 px)** | 4 slices (68k px) | 369 slices (14.6M px) | 232 slices (8.3M px) | **COMPLETELY ABSENT** |
| **5** | **MCC** | Microscale Cellular Convection | 1 slice (3.7k px) | 11 slices (544k px) | 488 slices (25.2M px) | 342 slices (18.7M px) | **Single-Parent Only** (1 parent) |
| **6** | **OF** | Oceanic Front | **0 slices (0 px)** | 0 slices (0 px) | 222 slices (681k px) | 215 slices (786k px) | **COMPLETELY ABSENT** |
| **7** | **POW** | Pure Oceanic Waves | 1 slice (38.3k px) | 8 slices (284k px) | 480 slices (23.7M px) | 1,266 slices (67.7M px) | **Single-Parent Only** (1 parent) |
| **8** | **RF** | Rain Cells | 1 slice (8.0k px) | 4 slices (43.5k px) | 282 slices (6.1M px) | 202 slices (2.3M px) | **Single-Parent Only** (1 parent) |
| **9** | **SI** | Sea Ice | **0 slices (0 px)** | 7 slices (457k px) | 244 slices (15.7M px) | 210 slices (13.4M px) | **Cryospheric Hazard** (Excluded) |
| **10** | **WS** | Wind Streak | 1 slice (43.8k px) | 1 slice (43.8k px) | 276 slices (16.2M px) | 309 slices (19.2M px) | **Single-Parent Only** (1 parent) |
| **11** | **Eddy** | Oceanic Eddy | **0 slices (0 px)** | 2 slices (9.5k px) | 394 slices (3.6M px) | 107 slices (1.5M px) | **COMPLETELY ABSENT** |
| **12** | **IWs** | Internal Waves | 9 slices (159.8k px) | 37 slices (591k px) | 416 slices (10.1M px) | 1 slice (5.1k px) | **Represented** (2 parents) |
| **13** | **HM** | Artificial / Anthropogenic | **0 slices (0 px)** | 1 slice (68 px) | 202 slices (30.3k px) | 5 slices (352 px) | **COMPLETELY ABSENT** |
| **14** | **OS** | Mineral Oil Spill | **0 slices (0 px)** | 1 slice (700 px) | 4 slices (1.7k px) | 0 slices (0 px) | **PERMANENTLY EXCLUDED** |

---

## 14. Anthropogenic (HM) Coverage Audit

- **Naming Invariant:** Class 13 is strictly named **`Artificial / Anthropogenic Objects`** (never `Vessel`).
- **Physical Representation:**
  - Current materialized dataset: **0 slices, 0 pixels (0.00%)**.
  - 12 Controls cohort: 1 slice (`...001-41` from Control 10), containing only **68 pixels**.
  - Full IW catalog: 202 slices (30,295 pixels, 7.7% of IW slices).
- **Forensic Assessment:**
  > [!WARNING]
  > **Major Capability Gap:** OPS-01 is intended to detect marine oil slicks while discriminating anthropogenic structures (ships, platforms, wind turbines). In the current 9-sample materialized dataset, **HM is completely absent**. A model trained on this dataset would have zero exposure to man-made targets. Recovery of HM-bearing IW scenes is a mandatory scientific prerequisite for P3.

---

## 15. Oil Spill (OS) Class Exclusion

- Exactly 4 slices across the 5,011 candidate catalog contain Class 14 (OS - Mineral Oil Spill).
- All 4 slices are permanently excluded from OPS-01 training (`EXCLUDED_DEFICIENT_DATA_OS`).
- Total OS pixels in candidate dataset: **0 pixels (0.00%)**.

---

## 16. Parent Diversity & Concentration

- **Materialized Dataset:** Only 2 parent scenes (Control 1: 4 slices, Control 2: 5 slices).
- **Concentration Ratio:** Top 2 scenes account for **100.0% of the physical dataset**.
- **Effective Sample Size:** 9 slices represent only **2 statistically independent meteorological/oceanographic events**. Reporting 9 samples as independent data points is scientifically unsupportable.

---

## 17. Temporal Diversity Audit

- Control 1: February 20, 2015 (`2015-02-20T21:17:00Z`).
- Control 2: January 11, 2016 (`2016-01-11T21:56:27Z`).
- Both acquisitions occurred in mid-winter (boreal winter) over North Atlantic / European coastal waters.
- Seasonal diversity is completely lacking (0 spring, 0 summer, 0 autumn acquisitions).

---

## 18. Geographic Diversity Audit

- Both Control 1 and Control 2 represent North Atlantic maritime passages.
- Tropical, equatorial, Mediterranean, and Asian maritime regimes are completely unrepresented in the physical dataset.
- In contrast, the full 484 IW catalog spans global continental shelves (2015–2023).

---

## 19. Leakage Firewall Recheck

- Evaluated group-level splitting across all 2,162 candidate parent groups:
  - $\text{TRAIN} \cap \text{DEV} = \emptyset$ (0 groups)
  - $\text{TRAIN} \cap \text{HOLDOUT} = \emptyset$ (0 groups)
  - $\text{DEV} \cap \text{HOLDOUT} = \emptyset$ (0 groups)
- **Zero Leakage:** The mathematical firewall is 100% sound.
- **Physical Failure:** Because group hash sorting placed Controls 1 and 2 into TRAIN, DEV and HOLDOUT received 0 physical samples.

---

## 20. Split Sufficiency Verdict

```
TRAIN:   9 physical samples (from 2 parent scenes) -> CONDITIONALLY POPULATED
DEV:     0 physical samples (from 0 parent scenes) -> EMPTY (BLOCKS P3)
HOLDOUT: 0 physical samples (from 0 parent scenes) -> EMPTY (BLOCKS P3)
```
**Verdict:** **`INSUFFICIENT_FOR_P3`**  
A split with empty validation and holdout sets cannot support pre-training qualification.

---

## 21. Materialization Cost & Feasibility

- **Remote Windowed Reading:** Using GDAL `/vsicurl/` over AWS Open Data S3 requires reading only $\sim 25\text{ MB}$ of compressed tiles per $2,560 \times 2,560$ slice, compared to downloading the full $\sim 550\text{ MB}$ Level-1 SAFE zip.
- **Feasibility Benchmark:**
  - Materializing 100 slices from 20 parent scenes requires $\sim 2.5\text{ GB}$ of network transfer and $\sim 26\text{ MB}$ of local disk storage.
  - Estimated runtime: $\sim 3\text{ minutes}$ over high-speed connections.
  - Cost: Free (AWS Open Data public bucket, no requester-pays charges).

---

## 22. Recovery Stop Criteria

To prevent indefinite ingestion while ensuring scientific sufficiency, a controlled recovery campaign must satisfy these strict stopping rules:
1. **Parent Scene Count:** Minimum $\ge 20$ independent IW parent scenes.
2. **Partition Population:**
   - TRAIN: $\ge 14$ parent scenes ($\ge 70$ slices).
   - DEV: $\ge 3$ parent scenes ($\ge 15$ slices).
   - HOLDOUT: $\ge 3$ parent scenes ($\ge 15$ slices).
   - *DEV and HOLDOUT must both be non-empty.*
3. **Class Representation:** Every core lookalike class (AF, BS, LWA, OF, MCC, POW, RF, WS, Eddy, IWs) must appear in $\ge 3$ independent parent scenes.
4. **Anthropogenic Representation:** HM must appear in $\ge 5$ independent parent scenes.
5. **Zero Oil Spill:** Class 14 OS count must strictly equal 0.

---

## 23. Incident Register

| Incident ID | Severity | Status | Description | Root Cause | Guardrail Blindspot | Correction / Prevention |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `INC-P2-R1-01` | HIGH | RESOLVED | Physical sample insufficiency (9 samples, 2 parent scenes) | P2 relied on local Li GeoTIFF sample directory rather than remote Level-1 ingestion | Test suite checked pipeline integrity but not physical population sufficiency | Phase 8-P2-R1 formally audited sufficiency and issued `INSUFFICIENT_FOR_P3` gate |
| `INC-P2-R1-02` | HIGH | RESOLVED | DEV and HOLDOUT partitions physically empty | Deterministic group hashing assigned both verified control scenes (Controls 1 & 2) to TRAIN | Lack of non-emptiness assertion across physical partitions | Implemented guardrail `test_r1_17_holdout_and_dev_non_emptiness_mandate` |
| `INC-P2-R1-03` | MEDIUM | RESOLVED | HM (Artificial Objects) completely absent from physical dataset | Controls 1 and 2 happen not to contain HM annotations | Class coverage was audited at catalog level rather than materialized physical level | Implemented guardrail `test_r1_15_prohibit_declaring_class_covered_from_tiny_sample` |

---

## 24. Regression Tests

Automated regression suite `tests/test_phase_8_p2_r1_source_recovery_guardrails.py` verified 24 mandatory guardrails:
- `test_r1_01_catalog_vs_physical_conflation`: PASSED
- `test_r1_02_missing_vs_unattempted_retrieval`: PASSED
- `test_r1_03_parent_product_deduplication`: PASSED
- `test_r1_04_source_scenes_crossing_partitions`: PASSED
- `test_r1_05_source_product_ids_crossing_partitions`: PASSED
- `test_r1_06_orbit_pass_crossing_wv_partitions`: PASSED
- `test_r1_07_hm_naming_invariant`: PASSED
- `test_r1_08_os_exclusion_invariant`: PASSED
- `test_r1_09_prohibit_15_79m_accuracy`: PASSED
- `test_r1_10_prohibit_50m_uncertainty`: PASSED
- `test_r1_11_ten_x_mean_is_hypothesis`: PASSED
- `test_r1_12_alignment_conditionality_preserved`: PASSED
- `test_r1_13_zero_nodata_statistics_preserved`: PASSED
- `test_r1_14_label_presence_not_image_availability`: PASSED
- `test_r1_15_prohibit_declaring_class_covered_from_tiny_sample`: PASSED
- `test_r1_16_sample_count_not_independent_source_count`: PASSED
- `test_r1_17_holdout_and_dev_non_emptiness_mandate`: PASSED
- `test_r1_18_incomplete_physical_data_prohibits_dataset_ready`: PASSED
- `test_r1_19_source_raw_files_unmutated`: PASSED
- `test_r1_20_part_iii_firewall`: PASSED
- `test_r1_21_exp06_and_part_i_frozen`: PASSED
- `test_r1_22_zero_training_invoked`: PASSED
- `test_r1_23_zero_gpu_invoked`: PASSED
- `test_r1_24_zero_git_staging`: PASSED

**Total Test Results:** **24 passed / 24 total (100%)**.  
Combined Phase 7C & 8 Suites: **148 passed / 148 total (100%)**.

---

## 25. Training Authorization Boundary

**MANDATORY GOVERNANCE DIRECTIVE:**
> **PHASE 8-P2-R1 DOES NOT AUTHORIZE MODEL TRAINING.**
>
> Model training, GPU compute, EXP-07 invocation, threshold calibration, and benchmark evaluation remain **STRICTLY UNAUTHORIZED**.
>
> P3 (Final Pre-Training Audit) is **BLOCKED** until:
> 1. A multi-scene source recovery campaign materializes physical imagery across $\ge 20$ parent scenes.
> 2. Both DEV and HOLDOUT contain verified, physically materialized image/mask pairs.
> 3. HM (Artificial / Anthropogenic Objects) has verified multi-parent physical representation.
> 4. Lookalike classes (AF, BS, LWA, OF, Eddy) have verified multi-parent physical representation.

---

## 26. Git Integrity

- Staged changes: `git diff --cached --name-status` returned **0 lines** (strictly clean).
- Git mutation: **Zero `git add`, zero `git commit`, zero `git push`, zero `git reset`, zero `git clean`**.
- Frozen artifacts: EXP-06 checkpoint and Part-I manifest bitwise identical.

---

## 27. Final Answers to Mandated Questions

1. **How many cataloged samples exist?**  
   **5,011 samples** (2,628 IW slices across 484 scenes; 2,383 WV vignettes across 1,678 passes).
2. **How many have physical imagery locally?**  
   **9 samples** (all from Controls 1 and 2).
3. **How many were successfully materialized?**  
   **9 samples** (in `data/derived/ops01/`).
4. **How many independent parent acquisitions are represented?**  
   **2 parent acquisitions** (Control 1 and Control 2).
5. **How many classes have meaningful multi-parent representation?**  
   **Only 2 classes:** Class 0 (Background) and Class 12 (Internal Waves). 4 classes are single-parent only; 6 classes are completely absent.
6. **Is HM actually represented?**  
   **NO.** HM has **0 samples and 0 pixels** in the materialized dataset.
7. **Is OS completely excluded?**  
   **YES.** All 4 OS candidate slices are permanently excluded (0 pixels in dataset).
8. **How much IW source recovery is possible?**  
   **100% of tested control scenes (12/12) are confirmed online on AWS Open Data S3.** Remote windowed access makes recovering hundreds of IW slices technically feasible.
9. **Should WV remain outside current scope?**  
   **YES.** WV represents Wave Mode SLC data with different geometry, resolution, and polar ocean skew. It is designated `OUTSIDE_CURRENT_SCOPE`.
10. **Is train/dev/holdout physically meaningful?**  
    **NO.** TRAIN has 9 samples; DEV has 0 samples; HOLDOUT has 0 samples.
11. **Is the candidate dataset sufficient for P3?**  
    **NO.** The dataset is **`INSUFFICIENT_FOR_P3`**.
12. **What exact data limitation remains?**  
    DEV/HOLDOUT partitions are empty; HM is absent; 6 core lookalike classes are absent; parent diversity is bounded at 2 scenes.
13. **What exact next action is authorized?**  
    **Phase 8-P2-R2: Controlled Multi-Scene Source Ingestion & Partition Population Campaign**, targeting $\ge 20$ parent scenes, non-empty DEV/HOLDOUT, and HM coverage.
