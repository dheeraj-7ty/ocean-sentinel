# Ocean Sentinel — Phase 7C-R2 Alignment Evidence Boundary & Pre-Phase-8 Gate Audit
**Date:** 2026-09-13  
**Auditor:** Senior CAO Scientific Auditor, Sentinel-1 SAR Geolocation Specialist, Raster Geometry / Coordinate-Convention Auditor, Scientific Reproducibility Auditor  
**Repository Root:** `D:\Projects\ocean-sentinel`  
**Branch:** `master`  
**Audit Purpose:** Pre-Phase-8 Scientific Evidence Boundary & Methodological Gate Audit  
**Authoritative Final Verdict:** `B. PHASE 8 CAN PROCEED WITH EXPLICIT CONDITIONAL ASSUMPTIONS`

---

## 1. Executive Verdict

Following the completion of Phase 7C-R1, this forensic gate audit establishes the definitive scientific evidence boundary governing all spatial alignment claims between the Li et al. dataset (100 m SAR imagery and annotations) and the Sentinel-1 Level-1 GRD source products before any Phase 8 dataset construction begins.

### Primary Audit Findings:
1. **Separation of Distinct Scientific Questions:**
   - *Can Sentinel-1 Level-1 coordinates reproduce the source geolocation grid?* **SUPPORTED.** Piecewise bivariate bilinear interpolation across the native XML tiepoints reproduces the Level-1 orbit model with $0.00\text{ m}$ numerical residual.
   - *Can the Li GeoTIFF corner metadata be interpreted consistently?* **CONDITIONALLY SUPPORTED.** Inverting corner coordinates yields a $2,550.0$ index span in Level-1 coordinates, mathematically compatible with $10\times$ block downsampling of a $2,560$-cell window under the Center Convention.
   - *Has the exact Li pixel-to-Level-1 crop transformation been independently established?* **NOT SUPPORTED.** No published extraction offsets, source generation code, or physical SAR backscatter cross-correlations exist in project evidence. The correspondence used to test alignment was inferred from the same corner coordinates being evaluated.
2. **The 15.79 m Residual is Conditional, Not Independent:**
   Because the mapping from Level-1 tiepoints to Li slice pixels $(row, col)$ was constructed from the inferred bounding box, the 15.79 m residual demonstrates internal geometric smoothness of the Level-1 range-Doppler grid over a $25.6\text{ km}$ patch. It does **not** constitute independent physical validation of slice georegistration.
3. **Sample Scope Discovery (Incident INC-7C-02):**
   While 12 source Level-1 control products were identified and 47 slice label masks are present in the repository, only **9 GeoTIFF imagery slices across 2 control products** were quantitatively evaluated in the alignment pilot. The remaining 10 controls (38 slices) were not evaluated for geometric residual or orientation. Orientation across all 12 controls is therefore classified as `ORIENTATION_UNCERTAIN`.
4. **Candidate 50 m Tolerance Reclassified:**
   The 50 m quantity is an a priori downstream evaluation **`DESIGN_PARAMETER`**, not an empirically established physical error bound.
5. **Phase 8 Authorization:**
   Phase 8 may open under **`B. PHASE 8 CAN PROCEED WITH EXPLICIT CONDITIONAL ASSUMPTIONS`**. Alignment must be treated as a conditional engineering reconstruction, not an independently validated geodetic contract.

---

## 2. Claim Classification Table

| claim_id | claim | evidence_source | evidence_type | independence_status | current_R1_wording | scientifically_defensible_wording | status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **A** | Li TIFF dimensions = 256×256 | GeoTIFF headers in `scratch/li_sample/Image_Geo/` | `OBSERVED` | `INDEPENDENT` | "256x256 Li raster" | Observed raster dimensions of evaluated Li GeoTIFF slices are 256×256 pixels. | `DIRECTLY_ESTABLISHED` |
| **B** | Li Tag 33922 contains corner coordinates 0/256 | Raw TIFF Tag 33922 inspection | `OBSERVED` | `INDEPENDENT` | "Tiepoints recorded as (0.0, 0.0), (0.0, 256.0), (256.0, 0.0), (256.0, 256.0)" | Observed GeoTIFF Tag 33922 ModelTiepointTag metadata specifies pixel coordinates 0.0 and 256.0. | `DIRECTLY_ESTABLISHED` |
| **C** | Inverted L1 coordinates corresponding to Li corner GCPs | Inversion through Level-1 XML grid | `DERIVED` | `DERIVED_FROM_PRIOR_STEP` | "Invert each corner into Level-1 scene with sub-meter precision" | Continuous Level-1 line/pixel coordinates numerically reproduce Tag 33922 lat/lon under the Level-1 orbit model. | `REPRODUCED_CONDITIONAL` |
| **D** | 2550 center-to-center native coordinate span | Max minus min of inverted coordinates | `DERIVED` | `DERIVED_FROM_PRIOR_STEP` | "Distance between first and last block centers is exactly 2,550.0 native lines/pixels" | Inverted Level-1 corner coordinates span exactly 2,550.0 native line and pixel index units. | `REPRODUCED_CONDITIONAL` |
| **E** | 2560 native cell-count hypothesis | Mathematical downsampling arithmetic | `DERIVED` | `ASSUMED` | "A 2,560x2,560 native cell window downsampled produces a 256x256 raster" | Plausible generation hypothesis mathematically compatible with 2,550 center span, but lacking direct generation evidence. | `INFERRED` |
| **F** | Exact 10× source-to-target sampling relationship | Dimension ratio ($2550/255 = 10.0$) | `DERIVED` | `ASSUMED` | "Exact factor-10 reduction" | Mathematically consistent with 10× downsampling, but specific aggregation algorithm is unverified from source code. | `INFERRED` |
| **G** | Exact Li crop bounding box in native Level-1 coordinates | Inverted corner GCPs | `DERIVED` | `DERIVED_FROM_PRIOR_STEP` | "Each Li slice corresponds to native window [min_line, max_line]" | Inferred Level-1 bounding box reconstructed from corner GCP inversion; unconfirmed by published crop offsets or intensity matching. | `INFERRED` |
| **H** | Bilinear corrected Model B residual <= 15.8 m | Geodetic distance calculations on interior tiepoints | `DERIVED` | `CONDITIONAL` | "Maximum residual across all evaluated interior Level-1 controls is 15.79 m" | Over 9 evaluated slices from 2 controls, a bilinear model fitted to inverted corners matches interior tiepoints within 15.79 m, conditional on assumed crop mapping. | `REPRODUCED_CONDITIONAL` |
| **I** | Independent validation of that residual | Circularity analysis | `NONE` | `UNSUPPORTED` | "Residual is conditional on assumed crop correspondence; not independent physical validation" | The residual test is not an independent geodetic validation of slice georegistration. | `UNSUPPORTED` |
| **J** | Model C zero residual | Grid interpolation at grid tiepoints | `DERIVED` | `INTERNAL_CONSISTENCY` | "Exact reproduction (0.00 m residual) of Sentinel-1 Level-1 orbit model tiepoints" | Trivially reproduces the source geolocation grid under its own interpolation rule; verifies numerical implementation, not physical ground truth. | `REPRODUCED_CONDITIONAL` |
| **K** | 50 m tolerance | Downstream evaluation protocol parameter | `DESIGN_PARAMETER` | `ASSUMED` | "Supported only conditional on the crop/pixel convention assumption" | Candidate design boundary tolerance for downstream task evaluation; not an empirically validated physical error bound. | `REPRODUCED_CONDITIONAL` |
| **L** | 47 slices linked to 12 controls | Manifest and filesystem audit | `MIXED` | `PARTIALLY_VERIFIED` | "12 control products, 47 corresponding Li slices evaluated" | 47 slice label masks are linked by filename to 12 control scenes; only 9 GeoTIFF slices across 2 control scenes were quantitatively evaluated for geometric residual. | `REPRODUCED_CONDITIONAL` |
| **M** | Row/column interpretation | Coordinate inversion across slices | `MIXED` | `PARTIALLY_OBSERVED` | "Row corresponds to range (pixel), col corresponds to azimuth (line)" | Verified for the 9 available GeoTIFF slices from Controls 1 and 2; unverified for the remaining 10 controls due to absence of GeoTIFF metadata. | `INFERRED` |
| **N** | Raw GCP ordering problem (Model A shear) | Tag 33922 perimeter coordinate ordering | `OBSERVED` | `INDEPENDENT` | "Raw perimeter-ordered GCP row/col assignment in Li GeoTIFF metadata" | A metadata ordering interpretation issue occurs when perimeter-ordered tiepoints are ingested into a Cartesian bilinear basis without sorting. | `DIRECTLY_ESTABLISHED` |
| **O** | Model D suitability | Comparison against curved orbit grid | `DERIVED` | `INDEPENDENT` | "Scientifically invalid for radar geometry" | Not suitable as the general physical geolocation model for this SAR geometry under the tested spatial extent; may remain a local approximation. | `DIRECTLY_ESTABLISHED` |
| **P** | Dataset-wide applicability | Pilot scope vs dataset volume | `NONE` | `UNSUPPORTED` | "Dataset-wide validation status: NOT_VALIDATED_REMAINS_RESTRICTED_TO_PILOT" | Strictly unvalidated dataset-wide; findings apply only to evaluated pilot controls. | `UNSUPPORTED` |

---

## 3. 2550 vs 2560 Reconciliation

### Mathematical Consistency vs Generation Verification:
- **`MATHEMATICALLY_CONSISTENT`**: **`TRUE`**.
  In a $10\times$ block downsample of a $2,560 \times 2,560$ cell native window, the center of block 0 is at index $4.5$, and the center of block 255 is at index $2554.5$. The center-to-center span is $2554.5 - 4.5 = \mathbf{2,550.0}$ index units. Concurrently, the discrete target raster has $256$ cells with center indices $0$ to $255$, spanning $\mathbf{255.0}$ index intervals. The ratio $2550.0 / 255.0 = 10.0\text{ m/index}$ exactly reconciles the geometry.
- **`DATASET_GENERATION_VERIFIED`**: **`FALSE`**.
  No source generation scripts, preprocessing documentation, or code repositories were released by Li et al. While the observed numbers are mathematically compatible with this hypothesis, we have zero empirical proof that the authors actually performed this exact operation.

---

## 4. Pixel Convention Audit

- **Tag 33922 Tiepoint Coordinates:** $(0.0, 0.0)$, $(0.0, 256.0)$, $(256.0, 0.0)$, $(256.0, 256.0)$ represent pixel edges / raster boundaries.
- **Inverted Physical Coordinates:** Map to $(5174.5, 2614.5)$ and $(7724.5, 5164.5)$, which represent pixel centers of $10\times10$ native blocks.
- **Convention Ambiguity Impact:** A center-vs-edge convention shift ($0.5$ target pixels) equals $5.0$ native pixels, which is exactly **$50.0\text{ meters}$** on the ground.

---

## 5. The 15.79 m Residual Dependency Chain

Tracing every dependency of the 15.79 m Model B result:
$$\text{Li TIFF GCP } [OBSERVED]$$
$$\downarrow$$
$$\text{Corner Inversion through L1 Grid } [DERIVED]$$
$$\downarrow$$
$$\text{Inferred L1 Window } [DERIVED]$$
$$\downarrow$$
$$\text{Assumed Slice-Coordinate Mapping } [ASSUMED]$$
$$\downarrow$$
$$\text{Interpolated L1 Coordinates } [DERIVED]$$
$$\downarrow$$
$$\text{Model B Fit } [DERIVED]$$
$$\downarrow$$
$$\mathbf{\text{Residual: 15.79 m } [CONDITIONAL]}$$

**Circularity Determination:**  
The evaluation coordinates $(srow, scol)$ for interior Level-1 tiepoints were computed using the *same* inverted corner window $[min\_line, max\_line]$ that defined the bilinear transformation.
$$\mathbf{\text{“RESIDUAL IS CONDITIONAL ON ASSUMED CORRESPONDENCE.”}}$$
This test confirms internal mathematical smoothness of the Level-1 grid across a 25.6 km window; it does **not** validate physical alignment of the Li raster.

---

## 6. Independence Audit

A thorough search across all local project evidence (excluding the protected Part-III benchmark) reveals:
- Zero original extraction code.
- Zero published preprocessing scripts.
- Zero native line/pixel crop offsets.
- Zero independent ground control points or surveyed targets.
- Zero SAR intensity cross-correlation measurements against Level-1 imagery.

$$\mathbf{\text{“NO INDEPENDENT LI-PIXEL-TO-L1 CORRESPONDENCE EVIDENCE FOUND.”}}$$

---

## 7. 12-Control / 47-Slice Lineage Audit

Forensic audit of `data/metadata/phase_7c_control_product_manifest.json`, `scratch/all_labels/label/*.png`, and `scratch/li_sample/Image_Geo/*.tiff`:

| Metric | Count | Governance Status |
| :--- | :--- | :--- |
| `control_product_count` | **12** | 12 distinct Level-1 SAFE source granules. |
| `unique_parent_product_count` | **12** | 12 unique parent product stems (zero duplicates). |
| `slice_count_declared_labels` | **47** | 47 PNG label files in `scratch/all_labels/label/`. |
| `unique_slice_filename_count` | **47** | 47 unique filenames (zero collisions). |
| `verified_parent_links` | **47** | All 47 label files match their declared parent stem. |
| `ambiguous_links` | **0** | Zero substring or cross-scene collisions. |
| `unverified_links` | **0** | Zero unverified links among label files. |
| `geotiff_slices_evaluated_count` | **9** | Only 9 GeoTIFF imagery slices exist in `scratch/li_sample/Image_Geo/`. |
| `controls_with_geotiff_data` | **2** | Only Controls 1 and 2 possess GeoTIFF imagery slices locally. |
| `controls_lacking_geotiff_data` | **10** | Controls 3–12 have XML annotations and PNG labels, but no GeoTIFFs. |

---

## 8. Row/Column Orientation Audit

- **Controls 1 & 2 (9 slices evaluated):**
  - Row step ($0 \to 256$): $\Delta line = 0.0, \Delta pixel = 2550.0$. Row corresponds to Level-1 range (pixel).
  - Col step ($0 \to 256$): $\Delta line = 2550.0, \Delta pixel = 0.0$ (after Cartesian re-indexing). Col corresponds to Level-1 azimuth (line).
- **Controls 3 through 12 (38 slices uninspected):**
  No GeoTIFF slices with Tag 33922 metadata exist locally for Controls 3–12. PNG label files lack georeferencing metadata.
- **Authoritative Orientation Status:** **`ORIENTATION_UNCERTAIN`**.
  Orientation is verified for the 2 controls with GeoTIFF data, but remains unverified across the other 10 controls.

---

## 9. GCP Ordering Audit

- **Tag 33922 Inspection:** Tiepoint IDs 1, 2, 3, 4 walk around the polygon perimeter (Top-Left $\to$ Bottom-Left $\to$ Bottom-Right $\to$ Top-Right).
- **Ingestion Shear:** Ingesting perimeter coordinates directly into a Cartesian basis produces multi-kilometer artificial diagonal shear ($3.6 - 22.2\text{ km}$).
- **Classification:** **`METADATA_ORDERING_INTERPRETATION_ISSUE`**.
  Because the dataset release lacks code or documentation, we cannot prove whether perimeter ordering was intentional or an export indexing bug. It must not be labeled a proven dataset corruption.

---

## 10. Model Assessments

- **Model A (Raw GeoTIFF Bilinear):** Fails for interior alignment due to raw perimeter metadata ordering.
- **Model B (Corrected Bilinear):** `CONDITIONALLY_SUPPORTED_FOR_EVALUATED_CONTROLS` (residual $\le 15.79\text{ m}$ across 9 evaluated slices, conditional on assumed crop mapping).
- **Model C (Direct Level-1 Grid):** `SOURCE_PRODUCT_GEOLOCATION_GRID_INTERPOLATION` (interpolates source orbit model tiepoints; not physical ground truth).
- **Model D (2D Affine):** "Not suitable as the general physical geolocation model for this SAR geometry under the tested spatial extent; may remain a local approximation."

---

## 11. 50 m Tolerance Reassessment

- **Classification:** **`DESIGN_PARAMETER`** (`CONDITIONALLY_SUPPORTED` as an evaluation threshold).
- **Four Numerically Equal but Conceptually Distinct Quantities:**
  1. *Candidate Tolerance:* 50.0 m buffer distance chosen a priori for evaluation.
  2. *Half-Pixel Displacement:* 50.0 m distance from pixel center to outer boundary in a 100 m raster.
  3. *Native-Cell Scale:* 50.0 m equals 5 native Level-1 10 m cells.
  4. *Registration Uncertainty:* Physical registration uncertainty on the ground remains unquantified.

---

## 12. Phase 8 Assumption Boundary

```
+-------------------------------------------------------------------------------+
|                           PHASE 8 ASSUMPTION BOUNDARY                         |
+-------------------------------------------------------------------------------+
| SAFE TO USE:                                                                  |
| - Sentinel-1 Level-1 XML grid as source-product geometry model                |
| - Observed Li GeoTIFF raster dimensions (256x256)                             |
| - Observed Tag 33922 tiepoint indices                                         |
| - Verified parent product lineage linking 47 slice labels to 12 controls      |
| - 50 m candidate tolerance strictly as a design evaluation parameter          |
+-------------------------------------------------------------------------------+
| CONDITIONAL TO USE:                                                           |
| - Inferred Level-1 crop bounding boxes derived from corner GCP inversion      |
| - 10x block downsampling reconstruction assumption (Center Convention)        |
| - Model B corrected bilinear transformation                                   |
| - 15.79 m maximum residual (labeled as conditional on assumed correspondence)  |
| - Spatial alignment transformations derived from inferred crop bounds         |
+-------------------------------------------------------------------------------+
| NOT SAFE TO USE:                                                              |
| - Any claim of dataset-wide alignment validation beyond evaluated controls    |
| - Any claim of exact published dataset generation procedure                   |
| - Treating Model C as surveyed physical ground truth                          |
| - Treating conditional residual as independent geodetic validation            |
| - Generalizing orientation from Controls 1 & 2 to Controls 3-12 unverified     |
+-------------------------------------------------------------------------------+
```

---

## 13. Generalization Limits

- Evaluated control scenes: **12** (out of 484 identified IW scenes).
- Untested source scenes remaining: **472**.
- Physically evaluated GeoTIFF slices: **9** (out of 5,011 slices).
- Dataset-wide validation status: **`NOT_VALIDATED_REMAINS_RESTRICTED_TO_PILOT`**.

---

## 14. Incident Register

### INC-7C-01: 2550 vs 2560 Native Line/Pixel Arithmetic Normalization Mismatch
- **Severity:** `MEDIUM` | **Status:** `RESOLVED`
- **Correction:** Normalized by index intervals ($255.0$) rather than cell counts ($256.0$), enforcing exact $10.0\text{ m/index}$ scale.

### INC-7C-02: Conflation of Total Control Slices (47) with Evaluated GeoTIFF Slices (9 across 2 Controls)
- **Severity:** `MEDIUM` | **Status:** `RESOLVED`
- **Description:** Phase 7C and 7C-R1 reported that 47 Li slices were evaluated in the alignment model comparison. Forensic audit revealed that while 47 slice labels exist for the 12 scenes, only 9 GeoTIFF slices (Controls 1 and 2) were physically present and evaluated in `slice_level_evaluations`. Controls 3–12 had no GeoTIFF slices evaluated.
- **Correction:** Formally separated declared label count (47) from evaluated GeoTIFF count (9). Reclassified orientation as `ORIENTATION_UNCERTAIN` for Controls 3–12.

---

## 15. Regression Test Results

Executed via pytest:
```bash
python -m pytest tests/test_phase_7c_alignment_guardrails.py tests/test_phase_7c_r1_methodology_guardrails.py tests/test_phase_7c_r2_alignment_evidence_guardrails.py -v
```
- `test_phase_7c_alignment_guardrails.py`: **30 passed**
- `test_phase_7c_r1_methodology_guardrails.py`: **20 passed**
- `test_phase_7c_r2_alignment_evidence_guardrails.py`: **15 passed**
- **Total:** **65 passed, 0 failed** in 1.11s.

---

## 16. Git Integrity & Frozen Invariants

- **Git Branch:** `master`
- **Staged Changes:** **0 files (empty)** (`git diff --cached --name-status`)
- **Unstaged Tracked Changes:** 2 files (`.gitignore`, `src/ocean_sentinel/ingestion/dataset.py`)
- **Zero Mutating Git Commands:** `git add`, `commit`, `push`, `reset`, `clean` strictly avoided.
- **EXP-06 Checkpoint (`best_model.pt`):** `B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF` (BITWISE VERIFIED)
- **Part-I Manifest (`internal_development_split_manifest.json`):** `17F1FF35146C7CE62E90D6FCE7F197B711B55E3C3CB599610578443208669072` (BITWISE VERIFIED)
- **Operating Threshold $\tau$:** `0.22` (BITWISE VERIFIED)
- **Part-III Benchmark:** Quarantined under Rule 38 (UNTOUCHED)

---

## 17. Final Decision & Phase 8 Authorization

### Explicit Decision Answers:
1. **What is proven?**  
   The Level-1 range-Doppler grid can be numerically reproduced ($0.00\text{ m}$ residual). Tag 33922 GCP coordinates span $2,550.0$ native index units in Level-1 space, which is mathematically consistent with $10\times$ downsampling of a $2,560$-cell window under the Center Convention. The 47 slice labels link unambiguously to the 12 control scenes.
2. **What is only conditionally supported?**  
   The inferred Level-1 crop bounding boxes, the Model B bilinear transformation, and the 15.79 m maximum residual are supported conditional on the assumed linear crop mapping.
3. **What remains unknown?**  
   The physical georegistration uncertainty on the ground, the exact source generation code, and the orientation of slices in Controls 3–12.
4. **What may Phase 8 safely assume?**  
   The Safe-to-Use and Conditional-to-Use items defined in the Phase 8 Assumption Boundary.
5. **What may Phase 8 NOT claim?**  
   Phase 8 must never claim dataset-wide alignment validation, exact published generation procedure, or independent geodetic ground truth.
6. **Whether Phase 8 may begin:**  
   **YES**, under Option B.
7. **Under what exact restrictions:**  
   No model training; no GPU compute; strict scene-level grouping leakage firewall; alignment treated as a conditional engineering reconstruction; and execution of an SAR intensity cross-correlation spot-check before benchmark freeze.

**Authoritative Gate Verdict:**  
$$\mathbf{B. \text{ PHASE 8 CAN PROCEED WITH EXPLICIT CONDITIONAL ASSUMPTIONS}}$$
