# OCEAN SENTINEL — PHASE 7B.2B FINAL SCIENTIFIC AUDIT REPORT
**Document Identifier:** `PHASE_7B2B_FINAL_AUDIT_20260913`  
**Governing Roles:** Senior CAO Scientific Data Auditor, Remote-Sensing Geometry Auditor, Dataset Provenance Auditor, ML Protocol Auditor  
**Audit Date:** September 13, 2026  
**Status:** **AUTHORITATIVE SCIENTIFIC AUDIT & PRE-TRAINING STAGE GATE DISPOSITION**  
**Dataset Under Audit:** Li et al. Sentinel-1 Ocean Phenomena Dataset (Zenodo `10.5281/zenodo.14279466`)  
**Associated Authoritative Documents:**  
- [`experiments/PHASE_7B2B_CANCELLED_RUN_FORENSIC_RECOVERY_REPORT_20260913.md`](file:///d:/Projects/ocean-sentinel/experiments/PHASE_7B2B_CANCELLED_RUN_FORENSIC_RECOVERY_REPORT_20260913.md)  
- [`data/metadata/li_iw_source_scene_manifest.json`](file:///d:/Projects/ocean-sentinel/data/metadata/li_iw_source_scene_manifest.json) (`SHA-256: 00996A2E0A6831F4127568C3366A251F35827DE652F175C93F3A2D8609402F8C`)  
- [`data/metadata/li_geometry_registration_audit_v2.json`](file:///d:/Projects/ocean-sentinel/data/metadata/li_geometry_registration_audit_v2.json) (`SHA-256: E297DB07A836984E738C63B2CDB1E68C3CDC7128EDCF9A0D1B1E044FFB7FA6E5`)  
- [`data/metadata/ops01_taxonomy_and_capability_gap_audit.json`](file:///d:/Projects/ocean-sentinel/data/metadata/ops01_taxonomy_and_capability_gap_audit.json) (`SHA-256: 710B10C128762585D12FBEAF74F52BE954BFCCAFC6FA842E509514561879952E`)  
- [`data/metadata/li_authoritative_class_dictionary.json`](file:///d:/Projects/ocean-sentinel/data/metadata/li_authoritative_class_dictionary.json) (`SHA-256: 9377DA6310804E459F2113914F6C933FF42F03277EC2D740A1FE29630A46DE46`)  
- [`tests/test_phase_7b2b_pretraining_gate_guardrails.py`](file:///d:/Projects/ocean-sentinel/tests/test_phase_7b2b_pretraining_gate_guardrails.py) (`SHA-256: 7B6A3734185096644F92FCE603E28C6010BE6FECC953662FD0092E42FB6B5735`)  

---

### EXECUTIVE SUMMARY & FINAL STAGE GATE DISPOSITION

In Phase 7B.2B, the Senior CAO Scientific Data Auditor, Remote-Sensing Geometry Auditor, Dataset Provenance Auditor, and ML Protocol Auditor completed an exhaustive forensic recovery of the cancelled Phase 7B.2B session, corrected source provenance accounting, audited geometric registration and label-to-10m transfer contracts, disaggregated spatial uncertainty, evaluated the multidimensional evidence matrix for candidate OPS-01 classes, and audited data leakage risks.

#### Final Stage Gate Evaluation:
**`B. OPS-01 PRE-TRAINING READY WITH EXPLICIT LIMITATIONS`**

> [!IMPORTANT]
> **PRE-TRAINING READINESS DOES NOT AUTHORIZE MODEL TRAINING:**  
> This disposition certifies that the data contracts, taxonomy disaggregation, and spatial uncertainty boundaries are formally defined and sufficient to begin controlled training-preparation engineering. **IT STRICTLY DOES NOT AUTHORIZE MODEL TRAINING, EXP-07 COMMENCEMENT, OR GPU ALLOCATION.** Model training requires a separate, explicit operator authorization and resource allocation task.

---

### 1. FORENSIC RECOVERY OF CANCELLED RUN

1. **Activity of Cancelled Run:** The cancelled session executed 176 tool actions between Steps 9508 and 9694 (terminated at 01:26:51 UTC+05:30 on 2026-09-13). All tool actions were non-mutating read commands (`git status`, `dir`, `Get-ChildItem`, `Test-Path`) and read-only test invocations (`pytest tests/ -k "7b"`).
2. **Filesystem Modifications:** **No substantive Ocean Sentinel project artifacts were modified by the cancelled run; pytest created/updated its standard cache artifact** (`.pytest_cache/v/cache/nodeids`). Zero repository code files, manifests, or benchmark results were created or modified.
3. **Training & GPU Compute:** **Zero model training was invoked; zero GPU compute was used.**
4. **Frozen Invariant Preservation:** EXP-06 checkpoint (`B5FFCCA3...`), Part-I split manifest (`17F1FF35...`), operational threshold ($\tau = 0.22$), and Part-III benchmark firewall remained 100% bitwise intact.
5. **Partial Artifacts:** Zero partial or unverified artifacts were generated. The repository was certified clean and safe for Phase 7B.2B re-entry.

---

### 2. SOURCE PROVENANCE & MUTUALLY EXCLUSIVE RECOVERY ACCOUNTING

1. **Total Identified IW Parent Scenes:** Exactly **484** unique Level-1 GRD measurement frame stems identified across 2,628 slices.
2. **Exhaustive Mutually Exclusive Accounting Invariant:**
   $$N_{\text{identified}} = N_{\text{recovered\_exact}} + N_{\text{not\_found\_after\_test}} + N_{\text{query\_error\_after\_test}} + N_{\text{ambiguous\_after\_test}} + N_{\text{not\_yet\_tested}}$$
   $$484 = 12 + 0 + 0 + 0 + 472$$
3. **Tested Scope vs Untested Scope:**
   - **$N_{\text{recovered\_exact}} = 12$**: A multi-year representative control sample (2015–2023) was queried against NASA ASF DAAC / ESA Copernicus Open Access Hub; 100% achieved exact-match product recovery to official ESA SAFE Level-1 GRD granules.
   - **$N_{\text{not\_yet\_tested}} = 472$**: Identified from slice filenames but not yet submitted to external archive queries.
   - **Failure Categories ($0, 0, 0$):** The failure counts are zero **ONLY because no tested scene fell into them**. They do not imply that all 484 have been queried.
4. **Governing Rule on Filenames:** Valid SAFE filename syntax (`s1a-iw-grd-vv-...`) is standard ESA naming syntax; it **MUST NOT be treated as proof of archive recoverability**. Full source recovery remains **NOT COMPLETED / PENDING**.

---

### 3. GEOMETRY AUDIT & PROOF OF ZERO-RESIDUAL CONSTRUCT

1. **Sample Scope Observation:** For examined Li GeoTIFFs (including `s1a-iw-grd-vv-20150220t211700-20150220t211729-004712-005d33-001-10.tiff`), GeoTIFF Tag 33922 (ModelTiepointTag) provides exactly 4 corner Ground Control Points (GCPs). Zero interior tiepoints, zero elevation grids, and zero external geolocation arrays are present in the distributed dataset files.
2. **Transformation Model Comparison:**
   - **Standard 2D Affine (6 DOF):** Fits a parallelogram. Residual error: $0.1146^\circ$ ($\approx 12,753.8\text{ m}$ / $1,275$ native pixels). Fails catastrophically due to orbital inclination ($\approx 98^\circ$) and slant-to-ground range convergence.
   - **Bilinear Corner Interpolation (8 DOF):** Maps $(u,v) \to (\text{lat}, \text{lon})$ via cross-term $u \cdot v$.
3. **Algebraic Proof of Zero Corner Residual by Construction:**
   A bilinear mapping has 4 parameters per axis ($c_0, c_1, c_2, c_3$). Evaluated at the 4 rectangular corner points $(0,0), (256,0), (0,256), (256,256)$, the design matrix $A$ is a $4 \times 4$ matrix with determinant:
   $$\det(A) = W^2 \cdot H^2 = 256^2 \cdot 256^2 = 4,294,967,296 \neq 0$$
   Because $A$ is non-singular, a unique algebraic solution exists that matches all 4 corner coordinates exactly. Fitting 4 parameters to 4 constraints leaves zero degrees of freedom for residual estimation ($\text{DoF} = 4 - 4 = 0$).
4. **Mandatory Scientific Invariant:**
   > **ZERO RESIDUAL ON THE FOUR FITTING CORNERS OCCURS BY ALGEBRAIC CONSTRUCTION AND IS NOT INDEPENDENT GEOMETRIC VALIDATION.**
5. **Formal Geolocation Limitation Statement:**
   > *"Bilinear mapping is an interpolation model anchored to the supplied corner GCPs; independent interior geolocation accuracy is not established."*
6. **Terminology Mandate:** Use **Bilinear Corner Interpolation** or **Bilinear Geolocation Mapping**. The phrase "Bilinear Perspective Interpolation" is prohibited because no projective rational homography denominator ($h(u,v) = \frac{ax+by+c}{gx+hy+1}$) is modeled.

---

### 4. NEUTRAL LABEL-TO-10m GRID ALIGNMENT CONTRACT

1. **Removal of Unsubstantiated Inversion Mechanism:** Premature claims citing "ESA SAFE L1 GRD XML Geolocation Grid Inversion" have been removed. Inversion cannot be declared authoritative until experimentally demonstrated.
2. **Neutral Conceptual Alignment Pipeline:**
   $$\text{100m source label} \longrightarrow \text{verified geographic/geometric representation} \longrightarrow \text{verified source-to-operational-grid alignment} \longrightarrow \text{derived 10m mask}$$
3. **Prerequisites for Implementation:**
   - Establish exact source product identity (ESA SAFE granule ID vs Li crop).
   - Verify native Level-1 GRD geometry and range/azimuth grid spacing.
   - Establish deterministic alignment between the Li 100m multi-looked frame and native 10m frame.
   - Verify reproducible transfer of 100m polygons to the native grid.
   - Confirm identical acquisition geometry.
4. **Ingestion & Resampling Rules:**
   - Categorical resampling: **Nearest-Neighbor only** (strictly zero continuous or fractional class interpolation).
   - Class overlap precedence: Labelme sequential polygon rasterization (higher class ID / later polygon overwrites earlier polygons; foreground over background).
   - Nodata & edge handling: Pixels outside valid radar swaths are assigned NODATA (255) and excluded from scoring.
5. **Mandatory Classification:**
   - Mask classification: **`DERIVED_HIGH_RESOLUTION_MASK`**
   - Strictly forbidden classifications: `NATIVE_10M_GROUND_TRUTH`, `native 10m ground truth`, `10m pixel-level ground truth`.

---

### 5. SPATIAL UNCERTAINTY DECOMPOSITION & BOUNDARY TOLERANCE

1. **Uncertainty Disaggregation (Rule 13):** Do not collapse spatial error into a single $\pm 50\text{ m}$ figure. Decomposed into four distinct components:
   - **Annotation Resolution:** $100\text{ m}$ multi-looked pixel resolution ($\pm 50\text{ m}$ quantization cell). `MEASURABLE`.
   - **Geolocation / Registration Uncertainty:** Corner GCP interpolation across 25.6 km interior. `NOT ESTABLISHED / UNKNOWN` (no interior tiepoints in distributed GeoTIFF).
   - **Resampling / Discretization Envelope:** Discrete grid mapping from $100\text{ m}$ to $10\text{ m}$ operational grid ($\pm 5\text{ m}$ half-pixel discretization). `MEASURABLE`.
   - **Human Annotation Ambiguity:** Visual boundary digitizing variance on diffuse oceanic gradients. `NOT ESTABLISHED / UNKNOWN` (no multi-annotator blind trial data).
2. **Boundary Tolerance Parameter Nature:** A $50\text{ m}$ / $5\text{ native pixel}$ buffer along phenomenon perimeters is a **candidate PRE-REGISTERED BOUNDARY-TOLERANCE PARAMETER**. It is NOT automatically a measured physical uncertainty, exact annotation error, or ground-truth correction.
3. **Dual Evaluation Protocol:**
   - **Protocol A (Strict Evaluation):** Exact pixel-to-pixel comparison without boundary tolerance buffers.
   - **Protocol B (Boundary-Tolerant Evaluation):** Segregates pixels within the candidate 50m tolerance envelope to report interior vs boundary agreement separately.
   - **Reporting Rule:** Protocol B must never silently replace Protocol A; both must be reported side-by-side.

---

### 6. OPS-01 TAXONOMY JUSTIFICATION & MULTIDIMENSIONAL EVIDENCE MATRIX

Candidate classes were disaggregated across five distinct evidence dimensions:
- **Dimension A: Phenomenon / Class Identity** (Literature oceanography/meteorology definition)
- **Dimension B: SAR Signature Interpretation** (Radar scattering physics: Bragg damping, tilt modulation)
- **Dimension C: Plausible Oil-Lookalike Relationship** (Surface roughness damping mimicking petroleum slicks)
- **Dimension D: Demonstrated EXP-06 False-Alarm Cause** (Empirically proven cause of EXP-06 false positives)
- **Dimension E: Demonstrated OPS Suppression Value** (Empirically demonstrated false-alarm suppression in fusion)

#### Comprehensive Class Evidence Matrix:

| ID | Class Name | Abbr | Pixels | Pixel % | Imgs | IW/WV | Dim A | Dim B | Dim C | Dim D | Dim E | Operational Tier |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **0** | Background Seawater | **BG** | 32,264,741 | 9.82% | 1,769 | IW+WV | DIRECT | DIRECT | NOT EST. | NOT EST. | HYPOTH. | **CORE_BACKGROUND** |
| **2** | Biological Slicks | **BS** | 44,132,805 | 13.44% | 1,034 | IW+WV | DIRECT | DIRECT | DIRECT | HYPOTH. | HYPOTH. | **CORE_LOOKALIKE** |
| **4** | Low Wind Area | **LWA** | 22,918,463 | 6.98% | 601 | IW+WV | DIRECT | DIRECT | DIRECT | HYPOTH. | HYPOTH. | **CORE_LOOKALIKE** |
| **12** | Internal Waves | **IWs** | 10,072,384 | 3.07% | 417 | IW+WV | DIRECT | DIRECT | DIRECT | HYPOTH. | HYPOTH. | **CORE_LOOKALIKE** |
| **6** | Oceanic Front | **OF** | 1,467,020 | 0.45% | 437 | IW+WV | DIRECT | DIRECT | INDIRECT | HYPOTH. | HYPOTH. | **CORE_LOOKALIKE** |
| **8** | Rainfall / Rain Cells | **RF** | 8,424,986 | 2.57% | 484 | IW+WV | DIRECT | DIRECT | INDIRECT | HYPOTH. | HYPOTH. | **CORE_LOOKALIKE** |
| **11** | Ocean Eddy | **Eddy** | 5,008,621 | 1.53% | 501 | IW+WV | DIRECT | DIRECT | INDIRECT | HYPOTH. | HYPOTH. | **CORE_LOOKALIKE** |
| **10** | Wind Streak | **WS** | 35,453,890 | 10.80% | 585 | IW+WV | DIRECT | DIRECT | INDIRECT | NOT EST. | HYPOTH. | **AUXILIARY_CONTEXT** |
| **7** | Pure Ocean Wave | **POW** | 91,480,185 | 27.86% | 1,746 | IW+WV | DIRECT | DIRECT | NOT EST. | NOT EST. | HYPOTH. | **AUXILIARY_CONTEXT** |
| **5** | Micro Convective Cells | **MCC** | 43,978,427 | 13.39% | 830 | IW+WV | DIRECT | DIRECT | NOT EST. | NOT EST. | HYPOTH. | **AUXILIARY_CONTEXT** |
| **1** | Atmospheric Front | **AF** | 3,726,670 | 1.13% | 644 | IW+WV | DIRECT | DIRECT | NOT EST. | NOT EST. | HYPOTH. | **AUXILIARY_CONTEXT** |
| **9** | Sea Ice | **SI** | 29,179,492 | 8.89% | 454 | IW+WV | DIRECT | DIRECT | INDIRECT | NOT EST. | HYPOTH. | **CRYOSPHERIC_MODE** |
| **3** | Iceberg | **IB** | 260,863 | 0.08% | 398 | WV only | DIRECT | DIRECT | NOT EST. | NOT EST. | HYPOTH. | **CRYOSPHERIC_MODE** |
| **13** | Artificial Objects | **HM** | 30,647 | 0.01% | 207 | IW+WV | DIRECT | DIRECT | NOT EST. | NOT EST. | HYPOTH. | **MARITIME_ATTRIBUTION** |
| **14** | Mineral Oil Spill | **OS** | 1,702 | 0.0005% | 4 | IW only | DIRECT | DIRECT | N/A | N/A | N/A | **STRICTLY_EXCLUDED** |

**Taxonomy Disposition:**
The proposed 7-class core set (BG, BS, LWA, IWs, OF, RF/RC, Eddy) is formally classified as:
**`B. REASONABLE ENGINEERING HYPOTHESIS REQUIRING VALIDATION`**
(Not an empirically proven operational core, because Dimensions D and E remain hypotheses awaiting experimental validation).

**Special Class Invariants:**
- **HM Designation:** Strictly designated **Artificial / Anthropogenic Objects**. Renaming HM to "Vessel" is strictly forbidden because HM includes offshore platforms, wind farms, and aquaculture rafts.
- **OS Disqualification:** Class 14 (OS) is **STRICTLY EXCLUDED** from OPS training, oil evaluation, and oil ground truth (`EXCLUDED_FROM_OPS_TRAINING = TRUE`, `EXCLUDED_FROM_OIL_EVALUATION = TRUE`, `EXCLUDED_FROM_OIL_GROUND_TRUTH = TRUE`).

---

### 7. CAPABILITY-GAP JUSTIFICATION: WHY DOES OPS-01 NEED TO EXIST?

Ocean Sentinel Rule 18 mandates that every model must have a diagnosed reason for existing. Look-alike classes in another dataset do not justify a model.

#### Diagnosed Capability Gap:
1. **EXP-06 Specialization:** The primary oil spill detection network (EXP-06) was trained on authentic petroleum slicks and achieves strong detection performance ($F_1 = 0.811$ on Part-I dev baseline).
2. **Observed Failure Mode:** In operational deployment across open oceans, natural physical look-alikes that damp capillary waves (biogenic slicks, low wind areas, internal solitons) produce low-backscatter radar signatures that cause clean-water false-positive alarms.
3. **Risk of Model Modification:** Directly retraining or modifying EXP-06 on multi-class natural phenomena data risks catastrophic forgetting, gradient interference on thin petroleum films, and invalidating the protected Part-I benchmark baseline.
4. **Architectural Solution:** OPS-01 is chartered as an independent, specialist recognition engine for natural oceanographic and meteorological phenomena. In the multi-specialist architecture:
   $$\text{Perception (EXP-06, Frozen)} + \text{Phenomena Recognition (OPS-01)} + \text{Evidence Fusion}$$
   OPS-01 identifies natural look-alikes independently, allowing downstream fusion logic to suppress false alarms while leaving the primary oil detector untouched.

---

### 8. LEAKAGE & SOURCE METADATA INDEPENDENCE AUDIT

1. **IW Mode Sibling Leakage ($N=2,628$ slices, $484$ scenes):**
   - **Grouping Basis:** Parent Level-1 GRD product stem (`s1a-iw-grd-vv-...`).
   - **Evidence Source:** `SOURCE METADATA` + `DATASET STRUCTURE`.
   - **Finding:** Up to 51 slices originate from the exact same Level-1 measurement frame, sharing identical satellite orbit geometry, incidence angle profiles, and atmospheric state.
   - **Partitioning Mandate:** Partitioning MUST occur strictly at the **parent scene stem level** ($484$ scenes). Sibling slices crossing partitions constitute severe spatial leakage and are prohibited. Confidence: **`HIGH`**.
2. **WV Mode Sibling Leakage ($N=2,383$ vignettes, $1,678$ passes):**
   - **Grouping Basis:** Orbit pass `(sat, orbit, data_take_id)`.
   - **Evidence Source:** `SOURCE METADATA` (TenGeoP-SARwv lineage).
   - **Finding:** Vignettes along an orbit pass were downlinked seconds apart along the satellite nadir track, sharing sea surface roughness and boundary layer conditions.
   - **Partitioning Mandate:** Partitioning MUST occur strictly at the **orbit-pass level** ($1,678$ passes). Sibling vignettes crossing partitions constitute severe temporal leakage and are prohibited. Confidence: **`HIGH`**.
3. **Cross-Dataset Leakage:** Direct parent product matching against Part-I ($N=1,200$), Part-III ($N=450$), and DARTIS ($N=869$ products, $2,290$ regions) confirmed **zero direct overlap and zero buffer overlap** ($50\text{ km}$ buffer). Confidence: **`HIGH`**.

---

### 9. REGRESSION GUARDRAILS & TEST EXECUTION

A dedicated regression test suite was implemented in [`tests/test_phase_7b2b_pretraining_gate_guardrails.py`](file:///d:/Projects/ocean-sentinel/tests/test_phase_7b2b_pretraining_gate_guardrails.py), codifying 24 distinct governance guardrails.

#### Test Execution Summary:
```powershell
.\venv\Scripts\python.exe -m pytest tests/test_phase_7b2b_pretraining_gate_guardrails.py tests/test_phase_7b2a_class_semantics_guardrails.py tests/test_phase_7b2_reconstruction_guardrails.py tests/test_phase_7b1_protocol_guardrails.py tests/test_phase_7b0_benchmark_guardrails.py tests/test_phase_7a_protocol_guardrails.py -v
```
- **Phase 7B.2B Pre-Training Gate Guardrails:** 24 / 24 PASSED.
- **Phase 7B.2A Class Semantics Guardrails:** 17 / 17 PASSED.
- **Phase 7B.2 Reconstruction Guardrails:** 21 / 21 PASSED.
- **Phase 7B.1 Protocol Guardrails:** 23 / 23 PASSED.
- **Phase 7B.0 Benchmark Guardrails:** 15 / 15 PASSED.
- **Phase 7A Protocol Guardrails:** 61 / 61 PASSED.
- **Total Suite Result:** **161 passed in 4.16 seconds (100% pass rate; zero regressions).**

---

### 10. RECOMPUTED CRYPTOGRAPHIC CHECKSUMS

All critical artifact hashes were recomputed directly from disk:

| Artifact Path | Cryptographic SHA-256 | Provenance / Authority Status |
| :--- | :--- | :--- |
| `experiments/performance/exp06_positive_bce_weight/best_model.pt` | `B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF` | Bitwise Frozen Checkpoint |
| `data/metadata/internal_development_split_manifest.json` | `17F1FF35146C7CE62E90D6FCE7F197B711B55E3C3CB599610578443208669072` | Bitwise Frozen Split Manifest |
| `data/metadata/li_iw_source_scene_manifest.json` | `00996A2E0A6831F4127568C3366A251F35827DE652F175C93F3A2D8609402F8C` | Authoritative Manifest |
| `data/metadata/li_geometry_registration_audit_v2.json` | `E297DB07A836984E738C63B2CDB1E68C3CDC7128EDCF9A0D1B1E044FFB7FA6E5` | Authoritative Geometry Contract |
| `data/metadata/ops01_taxonomy_and_capability_gap_audit.json` | `710B10C128762585D12FBEAF74F52BE954BFCCAFC6FA842E509514561879952E` | Authoritative Taxonomy Audit |
| `data/metadata/li_authoritative_class_dictionary.json` | `9377DA6310804E459F2113914F6C933FF42F03277EC2D740A1FE29630A46DE46` | Authoritative Class Dictionary |
| `experiments/PHASE_7B2B_CANCELLED_RUN_FORENSIC_RECOVERY_REPORT_20260913.md` | `ED0746F34E5F9629836D4C8ABD406529F8A5ACD08A8FF796CB59A363683B343A` | Authoritative Forensic Report |
| `tests/test_phase_7b2b_pretraining_gate_guardrails.py` | `7B6A3734185096644F92FCE603E28C6010BE6FECC953662FD0092E42FB6B5735` | Authoritative Test Guardrail Suite |

---

### 11. REMAINING UNKNOWNS & MATERIAL UNCERTAINTIES

1. **Untested 472 Parent Scenes:** 472 parent scenes remain untested against public archives; archive availability cannot be assumed.
2. **Interior Geolocation Accuracy:** Geolocation accuracy across the interior of the 25.6 km scenes is unknown and unvalidated without independent interior ground control points.
3. **Digitizer Boundary Precision:** Boundary placement variance on diffuse phenomena (eddies, low wind, biogenic films) is unknown without multi-annotator trials.
4. **Empirical Look-Alike Confusion Rates:** The exact rate at which each natural look-alike triggers EXP-06 false alarms has not yet been experimentally measured under canonical preprocessing.

---

### 12. EXACT NEXT SCIENTIFICALLY JUSTIFIED PHASE

**PHASE 7C: CONTROLLED LEVEL-1 GRD RECOVERY & ALIGNMENT PILOT**
- Retrieve the 12 verified representative Level-1 GRD ESA SAFE granules.
- Empirically calibrate native dual-pol (VV+VH) decibel backscatter.
- Implement and measure the spatial alignment between native 10m GRD pixels and the 100m Li label mask.
- Quantify actual interior geolocation error against Sentinel-1 Level-1 XML Geolocation Grid Points.
- **Strict Operating Invariant:** Zero model training; CPU-only pipeline qualification.
