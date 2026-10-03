# Ocean Sentinel — Phase 7C-R1 Methodological Validity Audit
**Date:** 2026-09-13  
**Auditor:** Senior CAO Scientific Auditor, Sentinel-1 SAR Geolocation Specialist, Raster Geometry / Coordinate-Convention Auditor, Scientific Reproducibility Auditor  
**Repository Root:** `D:\Projects\ocean-sentinel`  
**Branch:** `master`  
**Audit Target:** Phase 7C Controlled Spatial-Alignment Pilot & 15.8 m Residual Claim  
**Reconciled Final Status:** `B. PHASE 7C METHOD CONDITIONALLY SUPPORTED — LIMITATIONS`

---

## 1. Executive Verdict

Phase 7C reported an alignment residual of at most 15.8 m using a corrected bilinear model across 12 control products and 47 Li slices, concluding that a candidate 50 m boundary tolerance was empirically supported.

A rigorous post-pilot methodological audit was conducted to resolve two critical concerns:
1. **Arithmetic / Dimension Mismatch:** The source window was reported as $2,550 \times 2,550$ native Level-1 cells with an "exact factor-of-10 downsample" to a $256 \times 256$ slice raster, whereas $256 \times 10 = 2,560$.
2. **Epistemic Circularity / Independence Deficit:** The 15.8 m residual test reconstructed the crop window by inverting the Li corner coordinates through the Level-1 geolocation grid, and then mapped interior Level-1 tiepoints to Li slice pixel coordinates using a linear normalization based on that *same* inverted window.

### Authoritative Findings:
- **Arithmetic Discrepancy Resolved:** The discrepancy between 2,550 and 2,560 is resolved by distinguishing **discrete raster cell counts** from **continuous index spans between pixel centers**. A $2,560 \times 2,560$ native cell window downsampled by $10 \times 10$ block aggregation produces a $256 \times 256$ cell target raster. The distance between the center of block 0 (native line 5,174.5) and the center of block 255 (native line 7,724.5) is exactly $255 \times 10 = \mathbf{2,550.0}$ native lines.
- **Convention Conflation Identified (Incident INC-7C-01):** The Phase 7C implementation normalized coordinates using $(pos - min) / 2550.0 \times 256.0$, dividing a center-to-center span by cell count and yielding an erroneous effective pixel scale of $9.961\text{ m}$ instead of $10.000\text{ m}$. This has been corrected to $(pos - min) / 2550.0 \times 255.0$ (Center convention) or $(pos - min_{edge}) / 2560.0 \times 2560.0$ (Edge convention).
- **Source Crop Evidence is `INFERRED`, not `DIRECTLY_VERIFIED`:** No native extraction offsets, generation scripts, or sample provenance were published with the Li dataset. The Level-1 bounding box is derived purely by numerically inverting Tag 33922 corner GCPs through the Sentinel-1 range-Doppler grid.
- **Circularity of the 15.8 m Residual Test:** The 15.8 m residual evaluates whether a single bilinear patch can approximate the Sentinel-1 Level-1 range-Doppler geolocation grid over a $25.6\text{ km} \times 25.6\text{ km}$ area. It proves that the geometric distortion of the Level-1 grid itself is bounded by 15.8 m over this aperture. However, because the mapping from Level-1 tiepoints to Li slice pixels was constructed from the inferred corner bounds, the residual is **conditional on the assumed crop correspondence** and does not constitute independent physical proof of slice placement.
- **Model C Terminology Corrected:** Language describing Model C as an "authoritative physical ground control model" or "ground truth reproduction" has been corrected to **`SOURCE_PRODUCT_GEOLOCATION_GRID_INTERPOLATION`**. The Level-1 grid is an internal satellite orbit model reference, not surveyed geodetic ground truth.
- **50 m Tolerance Downgraded:** The candidate 50 m boundary tolerance is downgraded from unconditionally validated to **`SUPPORTED ONLY CONDITIONAL ON THE CROP/PIXEL CONVENTION ASSUMPTION`**.
- **Final Reconciled Phase 7C Gate:** **`B. PHASE 7C METHOD CONDITIONALLY SUPPORTED — LIMITATIONS`**.

---

## 2. 2550 / 2560 Arithmetic Reconciliation

The apparent arithmetic contradiction between native window span ($2,550$), target raster dimension ($256$), and downsampling factor ($10$) is resolved mathematically:

| Parameter | Value | Definition & Derivation | Evidence Status |
| :--- | :--- | :--- | :--- |
| `SOURCE_CELL_COUNT` | **2,560** | Total discrete native Level-1 GRD range/azimuth cells spanned by the crop window (e.g., lines $[5170, 7730)$, pixels $[2610, 5170)$). | `DERIVED` |
| `SOURCE_INDEX_SPAN` | **2,550.0** | Distance in native index units between the center of the first $10 \times 10$ block ($5174.5$) and the center of the last $10 \times 10$ block ($7724.5$): $7724.5 - 5174.5 = 255 \times 10 = 2,550.0$. | `DERIVED` |
| `TARGET_CELL_COUNT` | **256** | Total discrete cells in the output Li slice GeoTIFF ($256 \times 256$). | `DIRECT` |
| `TARGET_INDEX_SPAN` | **255.0** | Distance in target index units between the center of pixel 0 and the center of pixel 255 ($255 - 0 = 255.0$). | `DIRECT` |
| `DOWNSAMPLE_FACTOR` | **10** | Ratio of native cells to target cells ($2560 / 256 = 10.0$) and center span to index span ($2550.0 / 255.0 = 10.0$). | `DIRECT` |

### Mathematical Proof of Consistency:
Let the native Level-1 crop window span lines $[\text{start}, \text{start} + 2560)$.
Under non-overlapping $10 \times 10$ block aggregation, output pixel $k \in \{0, 1, \dots, 255\}$ aggregates native cells $[\text{start} + 10k, \text{start} + 10(k+1))$.
The physical sampling center of block $k$ in native continuous coordinates is:
$$C_{\text{native}}(k) = \text{start} + 10k + 4.5$$
For block $k = 0$: $C_{\text{native}}(0) = \text{start} + 4.5$.
For block $k = 255$: $C_{\text{native}}(255) = \text{start} + 2550 + 4.5 = \text{start} + 2554.5$.
The center-to-center span is:
$$\Delta C_{\text{native}} = C_{\text{native}}(255) - C_{\text{native}}(0) = 2550.0 \text{ native lines}$$
The outer cell boundary span is:
$$\Delta B_{\text{native}} = (\text{start} + 2560.0) - \text{start} = 2560.0 \text{ native lines}$$

Thus:
- $256 \text{ target cells} \times 10 = 2,560 \text{ native cells}$ (outer cell count).
- $255 \text{ target index intervals} \times 10 = 2,550 \text{ native index intervals}$ (center-to-center span).

---

## 3. Pixel-Center / Pixel-Edge Convention Audit

An inspection of GeoTIFF Tag 33922 (`ModelTiepointTag`) in the Li slices reveals a metadata convention conflation:
1. **Recorded Metadata Indices:** Tag 33922 records tiepoint pixel coordinates as $(0.0, 0.0)$, $(0.0, 256.0)$, $(256.0, 0.0)$, and $(256.0, 256.0)$. In TIFF/GeoTIFF raster specifications, indices $0.0$ and $256.0$ define the **outer raster boundaries** (edges) of a $256 \times 256$ image.
2. **Inverted Physical Coordinates:** When the geographic coordinates $(lat, lon)$ associated with these tiepoints are numerically inverted through the Sentinel-1 Level-1 range-Doppler geolocation grid, they map to:
   $$\text{line} \in \{5174.5, 7724.5\}, \quad \text{pixel} \in \{2614.5, 5164.5\}$$
   These coordinates end in $.5$ and have an exact span of $2,550.0$ native lines/pixels.
3. **Conflation Analysis:** The physical geographic coordinates in the Li dataset were sampled at the **pixel centers** of the corner $10 \times 10$ blocks, but were erroneously cataloged in Tag 33922 with the **pixel edge** bounding box indices $0.0$ and $256.0$.
4. **Geodetic Impact of Convention Ambiguity:**
   In a 100 m SAR raster, a half-pixel shift ($\Delta = 0.5$ target pixels) equals $5.0$ native Level-1 pixels, which corresponds to exactly **$50.0\text{ meters}$** on the ground.
   Because $50.0\text{ m}$ is identical to the candidate evaluation tolerance, any silent confusion between center and edge conventions shifts the geocoded footprint by the entire tolerance margin.

---

## 4. Source Crop Evidence Status

| Evidence Type | Investigation Source | Finding | Classification |
| :--- | :--- | :--- | :--- |
| Stored Native Offsets | Li GeoTIFF headers & Zenodo archive | None present. Tag 33922 contains only geographic coordinates and raster indices. | `NOT_ESTABLISHED` |
| Source Generation Scripts | Paper repository & public releases | No preprocessing, cropping, or downsampling scripts released. | `NOT_ESTABLISHED` |
| Native Image Dimensions | S1 Level-1 SAFE annotation XML | Full scene dimensions verified ($numberOfLines \sim 13,500 - 16,500$, $numberOfSamples \sim 21,500 - 26,000$). | `DIRECT` |
| Inverted Corner Bounds | Numerical inversion through L1 XML grid | Sub-millimeter numerical convergence to native lines/pixels (e.g. $[5174.5, 7724.5]$). | `DERIVED` |
| Crop Rectangularity | Inverted corners collinearity check | All 4 inverted corners form an exact axis-aligned rectangle in Level-1 range/azimuth space. | `DERIVED` |
| Physical Pixel Alignment | SAR intensity cross-correlation | Not performed in Phase 7C; no intensity correlation against Level-1 raster. | `NOT_ESTABLISHED` |
| **Overall Crop Evidence** | **Synthesized Provenance Assessment** | **The crop window is mathematically consistent with an inferred 2,560-cell extraction, but lacks direct operational provenance.** | **`INFERRED`** |

---

## 5. Exact Dependency Graph for the 15.8 m Residual

```mermaid
graph TD
    subgraph Raw Source Inputs
        GCP[Li GeoTIFF Tag 33922 Corner GCPs<br/><i>RAW EVIDENCE 1</i>]
        L1XML[Sentinel-1 Level-1 XML Geolocation Grid<br/><i>RAW EVIDENCE 2</i>]
    end

    subgraph Pipeline Derivations
        GCP -->|Invert through L1 Grid<br/><b>DERIVED_FROM_PRIOR_STEP</b>| INVBOUNDS[Inferred L1 Bounding Box<br/>min_line, max_line, min_pix, max_pix<br/><b>INFERRED / DERIVED</b>]
        INVBOUNDS -->|Interpolate 4 corners of box<br/><b>DERIVED_FROM_PRIOR_STEP</b>| CORNERS[Corrected Cartesian Corner Lat/Lon<br/><b>DERIVED</b>]
        CORNERS -->|Solve 4x4 Bilinear Basis<br/><b>DERIVED_FROM_PRIOR_STEP</b>| MODELB[Model B Bilinear Transformation<br/><b>DERIVED</b>]
        
        L1XML -->|Extract Interior Points in Box<br/><b>DERIVED_FROM_PRIOR_STEP</b>| TIEPOINTS[Interior L1 Geolocation Tiepoints<br/>line_k, pixel_k, lat_k, lon_k<br/><b>RAW EVIDENCE 2 (RESTRICTED)</b>]
        
        INVBOUNDS -.->|Impose Assumed Linear Mapping<br/><b>ASSUMED CORRESPONDENCE</b>| MAPCOORD[Normalized Coordinates<br/>scol = pl - min_l / delta_l * 255<br/>srow = pp - min_p / delta_p * 255<br/><b>DERIVED_FROM_PRIOR_STEP</b>]
        TIEPOINTS --> MAPCOORD
    end

    subgraph Residual Calculation
        MAPCOORD -->|Evaluate Model B at scol, srow<br/><b>DERIVED</b>| PREDS[Predicted Lat/Lon<br/><b>DERIVED</b>]
        TIEPOINTS -->|Compare with true lat_k, lon_k<br/><b>DERIVED</b>| RESIDUAL[Point Geodetic Residuals<br/>Max: 15.79 m<br/><b>CONDITIONAL RESIDUAL</b>]
        PREDS --> RESIDUAL
    end

    style GCP fill:#e1f5fe,stroke:#0288d1,stroke-width:2px;
    style L1XML fill:#e1f5fe,stroke:#0288d1,stroke-width:2px;
    style INVBOUNDS fill:#fff3e0,stroke:#f57c00,stroke-width:2px;
    style MAPCOORD fill:#ffebee,stroke:#d32f2f,stroke-width:2px;
    style RESIDUAL fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px;
```

---

## 6. Independence and Circularity Assessment

### Critical Epistemic Analysis:
1. **What Quantities Were Used to Fit / Define the Model?**
   - The 4 corner coordinates $(min\_l, max\_l, min\_p, max\_p)$ obtained by inverting the Li corner GCPs through the Level-1 grid.
   - The Level-1 interpolated geographic coordinates $(lat, lon)$ at those 4 corner points.
2. **What Quantities Were Used to Validate the Model?**
   - The geographic coordinates $(lat_k, lon_k)$ of the interior Level-1 geolocation grid tiepoints.
3. **Where Does Circularity Enter?**
   - To compute the residual at an interior Level-1 tiepoint $(line_k, pixel_k)$, that point must be mapped to a location $(row, col)$ in the Li slice raster.
   - The pipeline mapped $(line_k, pixel_k)$ into $(row, col)$ using the *exact same bounding box* $[min\_l, max\_l] \times [min\_p, max\_p]$ derived from the 4 corner GCPs.
   - It assumed that the spatial relationship between native pixels and slice pixels is a strictly linear, affine, uniform 10x block downsampling.
4. **Authoritative Independence Finding:**
   > **Independent source-product geolocation coordinates are available, but independent Li-pixel-to-Level-1-pixel correspondence is not directly established; the 15.8 m residual is conditional on the assumed crop-coordinate correspondence.**

The residual proves that the Sentinel-1 Level-1 range-Doppler geolocation grid is smooth and that a single bilinear patch approximates the grid within 15.8 m over a $25.6\text{ km}$ tile. It does **not** prove that the physical pixel contents of the Li slice correspond to that ground footprint.

---

## 7. Corrected Model A / B / C / D Interpretations

| Model | Formulation | Historical Phase 7C Verdict | Reconciled Phase 7C-R1 Status | Reconciled Scientific Interpretation |
| :--- | :--- | :--- | :--- | :--- |
| **Model A** | Raw GeoTIFF Bilinear (Tag 33922 GCPs) | `FAILED_FOR_INTERIOR_ALIGNMENT_WHEN_UNCORRECTED` | `FAILED_FOR_INTERIOR_ALIGNMENT_WHEN_UNCORRECTED` | Fails due to raw perimeter-ordered diagonal cross-tagging in Tag 33922 metadata, producing artificial multi-kilometer shear distortion ($3.6 - 22.2\text{ km}$). |
| **Model B** | Corrected Bilinear (Cartesian Corners) | `VALIDATED_WITHIN_50M_TOLERANCE_FOR_PILOT` | `CONDITIONALLY_SUPPORTED_FOR_12_CONTROLS` | Maximum residual is 15.79 m across all 47 slices. Satisfies candidate 50 m tolerance conditionally under the assumed crop correspondence. |
| **Model C** | Direct Level-1 Geolocation Grid | `AUTHORITATIVE_PHYSICAL_GROUND_CONTROL_MODEL` | `SOURCE_PRODUCT_GEOLOCATION_GRID_INTERPOLATION` | Exact reproduction ($0.00\text{ m}$) of Level-1 range-Doppler orbit tiepoints under its piecewise bilinear interpolation rule. Not geodetic ground truth. |
| **Model D** | Standard 2D Affine (6-DOF) | `SCIENTIFICALLY_INVALID_FOR_RADAR_GEOMETRY` | `SCIENTIFICALLY_INVALID_FOR_RADAR_GEOMETRY` | Imposes a rigid parallelogram constraint that violates SAR orbital swath geometry; mathematically invalid for wide swaths. |

---

## 8. Corrected 50 m Tolerance Status

- **Previous Phase 7C Status:** `SUPPORTED_FOR_PILOT` (inferred from max residual = 15.79 m).
- **Audit Assessment:** Because the 15.79 m residual is conditional on an assumed crop correspondence, it cannot serve as independent physical validation. Furthermore, a center-vs-edge convention shift introduces an unquantified offset of up to 50.0 m.
- **Reconciled Status:** **`SUPPORTED ONLY CONDITIONAL ON THE CROP/PIXEL CONVENTION ASSUMPTION`**.
- **Operational Requirement:** The 50 m tolerance cannot be declared an empirical property of the data until physical cross-correlation of SAR backscatter against Level-1 imagery is executed or source extraction offsets are directly proven.

---

## 9. Incident Register

### Incident INC-7C-01: 2550 vs 2560 Native Line/Pixel Arithmetic Normalization Mismatch
- **Incident ID:** `INC-7C-01`
- **Severity:** `MEDIUM`
- **Classification:** `IMPLEMENTATION_ARITHMETIC_MISMATCH`
- **Status:** `RESOLVED`
- **Description:** In Phase 7C, `verify_all_slice_crop_windows.py` and `compute_comprehensive_model_benchmarks.py` normalized Level-1 coordinates using:
  $$\text{slice\_col} = \frac{pl - min\_l}{max\_l - min\_l} \times 256.0$$
  Because $max\_l - min\_l = 2550.0$ (the center-to-center span), the code evaluated $\frac{pl - min\_l}{2550.0} \times 256.0 = \frac{pl - min\_l}{9.9609375}$, introducing a $0.39\%$ scaling error ($9.961\text{ m/pixel}$ instead of $10.000\text{ m/pixel}$).
- **Root Cause:** Conflation of discrete raster cell count ($N = 256$) with continuous index span ($N - 1 = 255$) when parameterizing the coordinate normalization from pixel-center GCP coordinates.
- **Guardrail Blindspot:** Phase 7C guardrails checked `b_res["max_m"] <= 50.0`. Because the bilinear model basis matrix $A_{256}$ and the evaluation coordinate $\text{slice\_col}$ both used $256.0$, the scaling factor canceled out algebraically during evaluation, leaving the interior residual numerically unchanged ($15.79\text{ m}$). The guardrails lacked an explicit test verifying $(max - min) / \text{span} == 10.000\text{ m}$.
- **Correction:** Formally established two distinct conventions:
  1. Center Convention: normalization uses $(pl - min\_l) / 2550.0 \times 255.0$ (scale: exactly $10.0\text{ m/index}$).
  2. Edge Convention: normalization uses $(pl - min\_l_{\text{edge}}) / 2560.0 \times 256.0$ (scale: exactly $10.0\text{ m/index}$).
- **Regression Tests:** `tests/test_phase_7c_r1_methodology_guardrails.py::test_01_2550_vs_2560_discrepancy_reconciled`, `test_20_scaling_consistency_check`.
- **Lesson Learned:** Raster cell counts ($N$) and coordinate index spans ($N - 1$) must always be dimensionally reconciled before declaring a downsampling factor exact.

---

## 10. New Governance Rules (Rules 92–102)

The following governance rules are hereby codified and enforced:
- **Rule 92:** Pixel-edge coordinates and pixel-center coordinates must never be silently interchanged.
- **Rule 93:** Raster dimensions must be reconciled with coordinate spans before a crop/downsample factor is declared exact.
- **Rule 94:** 256 output pixels $\times 10$ does not equal a 2,550-cell source span; any discrepancy must be explained by an explicit pixel convention.
- **Rule 95:** A source window inferred from the same control coordinates used to construct the transformation is not independent evidence of that window.
- **Rule 96:** A geolocation model cannot validate the correspondence used to feed that model without an independent correspondence observation.
- **Rule 97:** "Exact factor-of-10 downsample" requires explicit proof of the source sample geometry, not merely approximate dimension arithmetic.
- **Rule 98:** A Level-1 geolocation grid is a source-product geolocation reference, not surveyed physical ground truth.
- **Rule 99:** Zero residual when interpolating source geolocation grid points using the same grid is not physical validation.
- **Rule 100:** A transformation residual is only an independent validation residual if the transformation and coordinate correspondence were established independently of the validation points.
- **Rule 101:** If a scientific conclusion depends on an assumed crop correspondence, the final report must label that assumption explicitly.
- **Rule 102:** If two mathematically plausible pixel-coordinate conventions produce materially different alignment results, the alignment is NOT validated until the convention is established from source evidence.

---

## 11. Regression Guardrail Test Results

The test suite was executed via pytest:
```bash
.\venv\Scripts\python -m pytest tests/test_phase_7c_alignment_guardrails.py tests/test_phase_7c_r1_methodology_guardrails.py -v
```

**Results:**
- `tests/test_phase_7c_alignment_guardrails.py`: **30 passed** in 0.46s.
- `tests/test_phase_7c_r1_methodology_guardrails.py`: **20 passed** in 0.26s.
- **Total:** **50 passed, 0 failed, 0 warnings** in 0.72s.

---

## 12. Frozen Artifact Verification

| Artifact | Type | Expected SHA-256 Digest | Verified SHA-256 Digest | Match |
| :--- | :--- | :--- | :--- | :--- |
| `experiments/performance/exp06_positive_bce_weight/best_model.pt` | Model Checkpoint (EXP-06) | `B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF` | `B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF` | **PASS** |
| `data/metadata/internal_development_split_manifest.json` | Part-I Manifest | `17F1FF35146C7CE62E90D6FCE7F197B711B55E3C3CB599610578443208669072` | `17F1FF35146C7CE62E90D6FCE7F197B711B55E3C3CB599610578443208669072` | **PASS** |
| `exp06_frozen_dev_baseline.json` | Operating Threshold $\tau$ | `0.22` | `0.22` | **PASS** |
| `experiments/performance/trujillo_part_iii_eval_20260911_exp01/` | Part-III Benchmark | Quarantined under Rule 38 | Unmodified & quarantined | **PASS** |

---

## 13. Git Working Tree State

Git working tree status was verified before and after audit execution:
- `git branch --show-current`: `master`
- `git diff --cached --name-status`: **Empty (0 files staged)**.
- `git diff --name-status`:
  - `M .gitignore`
  - `M src/ocean_sentinel/ingestion/dataset.py`
- Zero git commands (`git add`, `git commit`, `git push`, `git reset`, `git clean`) were executed.

---

## 14. Phase 7C Corrected Final Status

- Previous Status: `B. ALIGNMENT VALIDATED WITH EXPLICIT LIMITATIONS`
- Corrected Authoritative Status:
  $$\mathbf{B. \text{ PHASE 7C METHOD CONDITIONALLY SUPPORTED — LIMITATIONS}}$$

### Summary of Conditional Scope:
1. Validated exclusively for the **12 control products** (47 Li slices).
2. Strictly prohibited from dataset-wide generalization to the 472 untested scenes or 5,011 slices.
3. Residual of 15.8 m is **conditional on the assumed linear crop mapping**.
4. 50 m tolerance is **supported only conditional on the crop and pixel convention assumption**.
5. Model C is **source-product geolocation grid interpolation**, not physical ground truth.

---

## 15. Phase 8 Recommendation (Do Not Execute)

The pilot spatial-alignment methodology is sufficiently understood and bounded to support controlled progression to dataset design.

### Recommended Next Phase:
**`PHASE 8 — OPS-01 DATASET CONSTRUCTION & LEAKAGE-SAFE TRAIN/DEV/HOLDOUT DESIGN`**

### Mandatory Phase 8 Pre-Conditions (Before Any Training):
1. **Source/Label Alignment Contract:** Enforce the corrected Center Convention ($0..255$, $10.0\text{ m/index}$) and require nearest-neighbor raster resampling.
2. **Physical Cross-Correlation Spot-Check:** Run an intensity-based normalized cross-correlation (NCC) between Li slice SAR backscatter and Level-1 SAR backscatter on a subset of controls to empirically bound the crop offset uncertainty.
3. **Data Representation:** Standardize whether OPS-01 ingests 100 m resampled imagery or native 10 m patches, documenting exact channel normalization.
4. **Class Mapping & Taxonomy:** Formalize the 5-class vs binary oil spill mapping established in Phase 7B.2B.
5. **Leakage Firewall:** Implement scene-level grouping (grouping all slices belonging to the same Sentinel-1 parent acquisition into the same train/dev/holdout split).
6. **Negative / Background Strategy:** Explicitly sample clean ocean background and lookalike phenomena scenes to maintain detector specificity.
7. **Scientific Training Budget:** Present training compute requirements and hyperparameter plan for human operator approval before initiating GPU compute.
