# Ocean Sentinel — Phase 8-P1-R1 Empirical Correspondence Validity & Threshold Audit Report

**Date:** 2026-09-13  
**Auditor:** Senior CAO Scientific Auditor, Sentinel-1 SAR Geolocation Specialist, Dataset Provenance Auditor, ML Protocol Auditor  
**Repository Root:** `D:\Projects\ocean-sentinel`  
**Branch:** `master`  
**Audit Target:** Phase 8-P1 Empirical Correspondence Results, Epistemic Scope, and Threshold Claims  
**Historical Generation Status:** `DATASET_GENERATION_METHOD = NOT_DIRECTLY_VERIFIED`  
**Generalization Level:** `LEVEL 2: MULTIPLE INDEPENDENT PARENT ACQUISITIONS` (Controls 1 & 2 only)  
**Threshold Status:** `DESIGN_THRESHOLD_ONLY`  
**P2 Readiness Decision:** `B. P2 READY ONLY WITH RESTRICTED CONDITIONAL ALIGNMENT`  
**Training Authorization Status:** `UNAUTHORIZED_AUDIT_AND_PROTOCOL_GOVERNANCE_ONLY`  

---

## 1. Executive Verdict

Phase 8-P1 provided strong empirical proof that Sentinel-1 Level-1 GRD measurement imagery correlates directly with Li GeoTIFF slices under an exact regular 2,560-cell crop, identity orientation, zero spatial offset, and $10 \times 10$ block averaging (median NCC $\approx 0.94$, positive-negative separation margin $+0.3595$).

This Phase 8-P1-R1 audit was conducted to reconcile the exact scientific scope of those results, preventing epistemic overreach:

1. **Empirically Supported Hypothesis vs. Historical Ground Truth:**
   The $10 \times 10$ block mean aggregation pipeline is **`EMPIRICALLY SUPPORTED AS A CORRESPONDENCE HYPOTHESIS`**, but the historical preprocessing pipeline used by the Li dataset authors remains **`NOT_DIRECTLY_VERIFIED`**. No original generation scripts, preprocessing code, or mathematical specifications were released. Wording claiming "confirmed historical preprocessing method" is permanently prohibited.
2. **Reconstructed Pipeline Transparency:**
   Every stage of the correspondence pipeline is explicitly categorized as `OBSERVED`, `DERIVED`, `ASSUMED`, or `OPTIMIZED`. The identity orientation and zero shift parameters were selected on the Discovery subset (Control 1) and evaluated blindly on the Confirmation subset (Control 2).
3. **Deterministic Zero/NoData Handling:**
   Audit of Slice 7 of Control 1 confirmed that its 5,579 zero pixels (8.5% of the raster) are border-padding artifacts introduced where Li authors clipped data outside the radar swath. Masking $Li > 0$ is deterministic, leakage-safe, and restores NCC from $0.4349$ to $0.8536$. Across the 6 slices without zero padding, raw NCC and masked NCC are identical. Both metrics are permanently recorded side by side.
4. **Shift Response Surface Confirms Sharp Unimodal Peak:**
   Fine-grained local response search demonstrates that the maximizing shift is strictly $(0.0, 0.0)$ Li pixels. A half-pixel shift ($50\text{ m}$) drops correlation by $0.076$ NCC units, and a 1-pixel shift ($100\text{ m}$) drops correlation by $0.173$ NCC units, proving a sharp, isolated peak rather than a broad plateau.
5. **Null Control Distribution Scoped to Pilot:**
   The 45 negative controls establish a clear separation on the pilot imagery ($+0.3595$ margin), but are classified as **`NULL_CONTROL_STRENGTH = LIMITED_PILOT`**, not a universal null distribution.
6. **Thresholds Reclassified as Design Thresholds:**
   Candidate thresholds ($0.70$ conservative, $0.85$ high-confidence) are reclassified as **`DESIGN_THRESHOLD_ONLY`**. While consistent with the observed pilot distribution, a 2-scene pilot sample size cannot statistically calibrate dataset-wide thresholds for 484 scenes.
7. **Strict Generalization Boundary:**
   The empirical evidence is strictly bounded at **`LEVEL 2: MULTIPLE INDEPENDENT PARENT ACQUISITIONS`** (Controls 1 and 2). Generalization to Controls 3–12 (which lack local Li GeoTIFFs) or the 472 untested IW scenes is prohibited.
8. **P2 Readiness:**
   **`B. P2 READY ONLY WITH RESTRICTED CONDITIONAL ALIGNMENT`**, subject to 11 mandatory operational restrictions.

---

## 2. Task 1: Source-Generation Claim Audit

A forensic review of all available literature, code repositories, and metadata artifacts was conducted:
- *ESSD Paper & Preprint:* Extracted text (`scratch/essd_paper_extracted_text.txt`) describes cropping Sentinel-1 images to $256 \times 256$ pixels, but omits code, mathematical downsampling equations, or intermediate calibration steps.
- *Zenodo Repository & Metadata:* No preprocessing scripts, cropping routines, or machine-readable provenance logs were deposited.
- *GeoTIFF Headers:* Tag 33922 records only corner GCPs and bounding box pixel coordinates.

### Binding Classification:
$$\mathbf{DATASET\_GENERATION\_METHOD = NOT\_DIRECTLY\_VERIFIED}$$

- **Prohibited Phrasing:** "confirmed historical preprocessing method", "dataset authors definitively used 10x block averaging", "historically verified downsampling".
- **Approved Phrasing:** "empirically supported correspondence hypothesis", "empirically preferred aggregation method", "candidate operational ingestion pipeline".

---

## 3. Task 2: Reconstruct Full P1 Correlation Pipeline

The exact epistemic dependency graph for the correspondence evaluation is reconstructed below:

| Stage | Operation / Quantity | Source / Rule | Epistemic Status | Circularity / Leakage Risk |
| :--- | :--- | :--- | :--- | :--- |
| **1. Target Raster** | Li GeoTIFF Slice ($256 \times 256$) | `scratch/li_sample/Image_Geo/*.tiff` | `OBSERVED` | None (independent external input) |
| **2. Invalid/Zero Mask** | Target data validity mask | $valid = (Li > 0)$ | `DERIVED` | None (intrinsic to target raster) |
| **3. Source Window** | Bounding box $[row, col, h, w]$ | Inverted Tag 33922 GCPs $\to$ Grid: offset 50, step 2560 | `DERIVED_HYPOTHESIS` | Conditional on regular grid hypothesis |
| **4. Source Raster** | Native Level-1 SAR GeoTIFF | AWS S3 Open Data COG `measurement/iw-vv.tiff` | `OBSERVED` | None (independent ESA/Copernicus data) |
| **5. Native Window** | Level-1 window crop ($2560 \times 2560$) | Windowed read from COG at $[col\_off, row\_off]$ | `DERIVED` | None (exact sub-array extract) |
| **6. Aggregation** | $10 \times 10$ block averaging | `reshape(256, 10, 256, 10).mean(axis=(1, 3))` | `DERIVED_HYPOTHESIS` | Evaluated against H2–H5 |
| **7. Normalization** | Zero-mean, unit-variance | $(X - \mu_X) / \sigma_X$ | `DERIVED` | Mathematical standardization |
| **8. Orientation** | Identity rotation / flips | Parameter search on Discovery subset (Control 1) | `OPTIMIZED_ON_DISCOVERY` | Confirmed blindly on Control 2 |
| **9. Shift Offset** | $(0.0, 0.0)$ Li pixels | Parameter search on Discovery subset (Control 1) | `OPTIMIZED_ON_DISCOVERY` | Confirmed blindly on Control 2 |
| **10. Cross-Correlation** | Scalar NCC value | $\frac{1}{N} \sum X_{norm} Y_{norm}$ | `DERIVED` | Statistical similarity metric |
| **11. Gate Assessment** | Conditional alignment decision | Protocol threshold comparison and evidence bounds | `GOVERNED_ASSESSMENT` | Bounded by audit policy |

---

## 4. Task 3: Zero / NoData Audit

A systematic audit of exact zero-valued pixels across all 9 physical Li GeoTIFF slices was executed:

| Slice Identifier | Parent Scene | Li Zero Pixels | Zero Fraction | Level-1 Zeros | Raw NCC | Masked NCC | Difference ($\Delta$) | Audit Diagnosis |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `005d33-001-10.tiff` | Control 1 | 0 | 0.00% | 0 | 0.9764 | **0.9764** | $+0.0000$ | Zero-free interior ocean crop |
| `005d33-001-7.tiff` | Control 1 | 5,579 | 8.51% | 0 | 0.4349 | **0.8536** | $+0.4187$ | Swath-edge padding artifact (Incident INC-8P1-01) |
| `005d33-001-8.tiff` | Control 1 | 0 | 0.00% | 10 | 0.9478 | **0.9478** | $+0.0000$ | Zero-free interior ocean crop |
| `005d33-001-9.tiff` | Control 1 | 589 | 0.90% | 0 | 0.7915 | **0.9704** | $+0.1789$ | Minor coastal/boundary zero padding |
| `00db41-001-1.tiff` | Control 2 | 0 | 0.00% | 0 | 0.9404 | **0.9404** | $+0.0000$ | Zero-free interior ocean crop |
| `00db41-001-2.tiff` | Control 2 | 0 | 0.00% | 0 | 0.9294 | **0.9294** | $+0.0000$ | Zero-free interior ocean crop |
| `00db41-001-4.tiff` | Control 2 | 26 | 0.04% | 0 | 0.9029 | **0.9051** | $+0.0022$ | Negligible edge zero pixels |
| `00db41-001-7.tiff` | Control 2 | 0 | 0.00% | 0 | 0.9387 | **0.9387** | $+0.0000$ | Zero-free interior ocean crop |
| `00db41-001-8.tiff` | Control 2 | 0 | 0.00% | 0 | 0.9598 | **0.9598** | $+0.0000$ | Zero-free interior ocean crop |

### Key Audit Findings:
1. **Nature of Zero Pixels:** In Sentinel-1 SAR imagery, valid ocean backscatter produces positive digital numbers ($DN \approx 40 - 500$). Exact zeros in Li GeoTIFFs occur strictly at the edges of the radar swath (e.g. Slice 7 line offset 15,410 near the swath end), where Li authors clipped or padded invalid radar data.
2. **Impact of Masking:** For 6 out of 9 slices, zero-count is exactly 0, so Raw NCC equals Masked NCC identically. Masking materially affects only Slices 7 and 9, where zero padding would otherwise correlate against valid radar noise in the raw Level-1 file.
3. **Information Leakage Prevention:** The masking rule $valid = (Li > 0)$ is derived solely from the target raster itself before any Level-1 comparison, ensuring **zero leakage from candidate correspondence**.
4. **Policy Enforcement:** Raw and masked metrics are permanently recorded side by side. Masked metrics may never silently replace raw metrics.

---

## 5. Task 4: Downsampling Robustness

The performance of the five downsampling hypotheses across all 9 physical pairs:

| Downsampling Candidate | Median Masked NCC | Median Pearson $r$ | Median NRMSE | Relative Rank | Epistemic Assessment |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **H3: $10 \times 10$ Block Intensity Mean ($DN^2$)** | **0.9412** | **0.9412** | **0.0315** | **1** | **Plausibly Equivalent to H1** |
| **H1: $10 \times 10$ Block Amplitude Mean ($DN$)** | **0.9404** | **0.9404** | **0.0328** | **2** | **Plausibly Equivalent to H3** |
| **H2: $10 \times 10$ Block Median ($DN$)** | 0.9285 | 0.9285 | 0.0381 | 3 | Viable, but slightly suppresses texture |
| **H4: Center Point Sampling (Stride 10, off 4)** | 0.5420 | 0.5420 | 0.1840 | 4 | Inadequate (speckle noise dominates) |
| **H5: Edge Point Sampling (Stride 10, off 0)** | 0.5182 | 0.5182 | 0.1995 | 5 | Inadequate (speckle noise dominates) |

### Conclusion on Aggregation Hypothesis:
- $10 \times 10$ spatial block aggregation is **`CLEARLY PREFERRED`** over point decimation ($NCC \approx 0.94$ vs $0.52$).
- Amplitude mean (H1) and intensity mean (H3) are **`PLAUSIBLY EQUIVALENT`** ($|\Delta NCC| < 0.001$). H1 is selected as the canonical operational pipeline because Sentinel-1 GRDH data are distributed in amplitude digital numbers.

---

## 6. Task 5: Orientation Robustness

Orientation search was verified across all transform group candidates on every physical pair:

| Orientation Candidate | Transformation Matrix | Median NCC | IQR | Status |
| :--- | :---: | :---: | :---: | :--- |
| **Identity** | $\begin{bmatrix} 1 & 0 \\ 0 & 1 \end{bmatrix}$ | **+0.9404** | **0.0304** | **CONFIRMED FOR CONTROLS 1 & 2** |
| **Transpose (Row/Col Swap)** | $\begin{bmatrix} 0 & 1 \\ 1 & 0 \end{bmatrix}$ | $-0.0210$ | 0.0980 | Rejected ($\Delta = -0.961$) |
| **Horizontal Flip** | $\begin{bmatrix} 1 & 0 \\ 0 & -1 \end{bmatrix}$ | $+0.0415$ | 0.0620 | Rejected ($\Delta = -0.899$) |
| **Vertical Flip** | $\begin{bmatrix} -1 & 0 \\ 0 & 1 \end{bmatrix}$ | $+0.0820$ | 0.0950 | Rejected ($\Delta = -0.858$) |
| **180-Degree Rotation** | $\begin{bmatrix} -1 & 0 \\ 0 & -1 \end{bmatrix}$ | $-0.0141$ | 0.0580 | Rejected ($\Delta = -0.954$) |
| **Transpose + Horiz. Flip** | $\begin{bmatrix} 0 & -1 \\ 1 & 0 \end{bmatrix}$ | $+0.0784$ | 0.0450 | Rejected ($\Delta = -0.862$) |
| **Transpose + Vert. Flip** | $\begin{bmatrix} 0 & 1 \\ -1 & 0 \end{bmatrix}$ | $+0.0070$ | 0.0380 | Rejected ($\Delta = -0.933$) |

### Finding:
Identity orientation is stable across all 9 slices in Controls 1 and 2. However, Controls 3–12 lack physical imagery and **must not inherit identity orientation by assumption**.

---

## 7. Task 6: Shift Robustness & Peak Characterization

The continuous local response surface around the nominal grid placement was reconstructed:

| Native Offset (Cells) | Li Pixel Offset (px) | Ground Distance (m) | Slice 10 NCC | Drop vs Peak ($\Delta$) | Characterization |
| :---: | :---: | :---: | :---: | :---: | :--- |
| $-20$ | $-2.0$ | $-200\text{ m}$ | 0.7655 | $-0.2109$ | Distant decorrelation |
| $-10$ | $-1.0$ | $-100\text{ m}$ | 0.8025 | $-0.1738$ | Significant decorrelation |
| $-5$ | $-0.5$ | $-50\text{ m}$ | 0.8998 | $-0.0766$ | Margin-scale drop |
| $-2$ | $-0.2$ | $-20\text{ m}$ | 0.9561 | $-0.0202$ | Near-peak slope |
| **0** | **0.0** | **0 m** | **0.9764** | **PEAK** | **MAXIMUM CORRESPONDENCE** |
| $+2$ | $+0.2$ | $+20\text{ m}$ | 0.9564 | $-0.0199$ | Near-peak slope |
| $+5$ | $+0.5$ | $+50\text{ m}$ | 0.9005 | $-0.0758$ | Margin-scale drop |
| $+10$ | $+1.0$ | $+100\text{ m}$ | 0.8030 | $-0.1734$ | Significant decorrelation |
| $+20$ | $+2.0$ | $+200\text{ m}$ | 0.7659 | $-0.2104$ | Distant decorrelation |

### Findings:
1. **Best Shift:** Exactly $(0.0, 0.0)$ Li pixels.
2. **Second-Best Shift:** $\pm 0.2$ Li pixels ($\pm 20\text{ m}$), dropping correlation by $\approx 0.020$.
3. **Peak Prominence:** $+0.076$ NCC units above a half-pixel shift ($50\text{ m}$ tolerance margin).
4. **Peak Character:** Highly symmetric, sharp unimodal peak. This confirms physical pixel registration rather than broad textural coincidence.

---

## 8. Task 7: Negative-Control Strength

45 systematic negative controls across 5 categories were evaluated to assess the null distribution:

| Negative Control Category | Sample Size | Min NCC | Median NCC | Max NCC | Separation Margin vs Min Positive (0.8536) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Nearby Spatial Shifts ($+500$ lines / $5\text{ km}$)** | 9 | $+0.1240$ | $+0.3850$ | $+0.4941$ | **+0.3595** |
| **Far Spatial Shifts ($+2,000$ lines / $20\text{ km}$)** | 9 | $-0.0520$ | $+0.0480$ | $+0.1820$ | **+0.6716** |
| **Far Column Shifts ($+3,000$ cols / $30\text{ km}$)** | 9 | $-0.1875$ | $-0.0650$ | $+0.0320$ | **+0.8216** |
| **Cross-Scene Unrelated Controls** | 9 | $-0.0980$ | $+0.0020$ | $+0.0710$ | **+0.7826** |
| **Random Permutations** | 9 | $-0.0120$ | $+0.0010$ | $+0.0150$ | **+0.8386** |
| **All Negative Controls Combined** | **45** | **-0.1875** | **+0.0013** | **+0.4941** | **+0.3595** |

### Classification:
$$\mathbf{NULL\_CONTROL\_STRENGTH = LIMITED\_PILOT}$$
- The negative controls are adequate to prove strong separation on this 2-scene pilot.
- However, they do not constitute a statistically universal null distribution covering global marine clutter variations.

---

## 9. Task 8: NCC Threshold Audit

The Phase 8-P0 candidate thresholds ($0.70$ and $0.85$) were audited against the empirical distributions:

1. **Empirical Separation:** True positive matches cluster at $[0.8536, 0.9764]$. The highest negative accidental correlation reached $0.4941$. Separation is complete and unequivocal on this pilot ($+0.3595$ margin).
2. **0.70 Threshold Assessment:** $0.70$ is comfortably above the worst accidental negative correlation ($0.4941$) and safely below all valid positive matches ($0.8536$).
3. **0.85 Threshold Rejection Risk:** Slice 7 (swath edge) yielded masked NCC = $0.8536$. A rigid $0.85$ threshold risks rejecting valid boundary crops that suffer minor edge artifacts.
4. **Generalization Restriction:** A pilot sample of 9 slices across 2 scenes is insufficient to declare thresholds universally calibrated across all 484 IW scenes.

### Binding Classification:
$$\mathbf{THRESHOLD\_STATUS = DESIGN\_THRESHOLD\_ONLY}$$
- The label `EMPIRICALLY_VALIDATED_DATASET_WIDE` is prohibited.
- $0.70$ and $0.85$ are retained as protocol design guideposts, not infallible ground-truth classifiers.

---

## 10. Task 9: Discovery / Confirmation Independence

The segregation between parameter selection and validation was audited:

- **Discovery Subset (Control 1, 4 slices):** Used to evaluate candidate hypotheses and select optimal transformation parameters (identity orientation, $10 \times 10$ block mean, zero spatial shift).
- **Confirmation Subset (Control 2, 5 slices):** Evaluated strictly under the fixed parameters selected from Control 1.
- **Leakage Check:** Did Control 2 imagery or metrics influence crop placement, downsampling method, orientation, shift, or threshold choices? **NO.**

### Formal Finding:
$$\mathbf{CONFIRMATION\_WAS\_BLIND\_TO\_CONTROL\_2\_RESULTS}$$
Parameters selected on Control 1 generalized to Control 2 without degradation (median NCC $0.9387$, range $0.9051$ to $0.9598$).

---

## 11. Task 10: Generalization Boundary

The highest scientifically defensible claim supported by Phase 8-P1 evidence:

| Level | Description | P1 Support Status | Epistemic Assessment |
| :--- | :--- | :---: | :--- |
| **LEVEL 0** | Single-slice consistency | SUPPORTED | Trivial baseline |
| **LEVEL 1** | Multiple slices within one parent acquisition | SUPPORTED | Demonstrated on Control 1 (4 slices) |
| **LEVEL 2** | **Multiple independent parent acquisitions** | **SUPPORTED** | **HIGHEST DEFENSIBLE CLAIM (Controls 1 & 2)** |
| **LEVEL 3** | Dataset-wide empirical validation | **PROHIBITED** | 38 slices in Controls 3–12 and 472 IW scenes unverified |

P1 evidence proves consistency across two independent Sentinel-1 scenes, but **does NOT prove dataset-wide validity**.

---

## 12. Task 11 & 12: P2 Readiness Decision & Required Restrictions

### Formal Decision:
$$\mathbf{B.\ P2\ READY\ ONLY\ WITH\ RESTRICTED\ CONDITIONAL\ ALIGNMENT}$$

Controlled dataset construction for OPS-01 is authorized under the empirically supported correspondence hypothesis, subject to 11 mandatory restrictions:

1. **Complete Provenance Retention:** Every constructed sample must record source SAFE granule ID, native window coordinates, downsampling parameters, and verification hash.
2. **Empirical Correspondence Hypothesis:** Ingestion must use $10 \times 10$ block mean amplitude averaging, identity orientation, and zero spatial offset.
3. **Alignment Uncertainty Metadata:** Samples must carry metadata reflecting conditional alignment status.
4. **Zero/NoData Handling Metadata:** Border zero-padding and nodata fractions must be cataloged per raster.
5. **Exact Transformation Specification:** The deterministic bilinear coordinate mapping must be recorded per sample.
6. **Mandatory Scene-Level Grouping:** All slices from the same parent acquisition must be assigned to the same partition.
7. **Zero Cross-Partition Leakage:** Strict partition firewall ($\text{Train} \cap \text{Dev} = \emptyset$, $\text{Train} \cap \text{Holdout} = \emptyset$, $\text{Dev} \cap \text{Holdout} = \emptyset$).
8. **No Independent Georegistration Overclaim:** No claim of independent sub-pixel geodetic ground-truth registration may be made.
9. **No Historical Preprocessing Overclaim:** The dataset documentation must state that the historical generation method is `NOT_DIRECTLY_VERIFIED`.
10. **Holdout Partition Isolation:** The final OPS-01 holdout must remain untouched during development and tuning.
11. **Protected Part-III Firewall:** Part-III benchmark files remain completely untouched and firewalled.

---

## 13. Task 13: Incident Governance

| Incident ID | Severity | Status | Title & Description | Root Cause | Correction & Guardrail |
| :--- | :---: | :---: | :--- | :--- | :--- |
| **INC-8P1R1-01** | MEDIUM | RESOLVED | Risk of overclaiming historical preprocessing method as proven fact | High NCC ($0.94-0.98$) can be misinterpreted as historical provenance proof | Permanently classify `DATASET_GENERATION_METHOD = NOT_DIRECTLY_VERIFIED`; enforce guardrail `test_r1_01` |
| **INC-8P1R1-02** | LOW | RESOLVED | Premature claim of dataset-wide threshold validation | Conflating pilot separability with global threshold calibration | Reclassify thresholds as `DESIGN_THRESHOLD_ONLY`; enforce guardrail `test_r1_08` |

---

## 14. Regression Guardrails & Verification

- **New Test Suite:** `tests/test_phase_8_p1_r1_correspondence_guardrails.py` (13/13 passed)
- **Cumulative Protocol & Alignment Suites:** 107/107 passed:
  - `tests/test_phase_7c_alignment_guardrails.py` (30 passed)
  - `tests/test_phase_7c_r1_methodology_guardrails.py` (20 passed)
  - `tests/test_phase_7c_r2_alignment_evidence_guardrails.py` (15 passed)
  - `tests/test_phase_8_p0_ops01_protocol_guardrails.py` (17 passed)
  - `tests/test_phase_8_p1_alignment_guardrails.py` (12 passed)
  - `tests/test_phase_8_p1_r1_correspondence_guardrails.py` (13 passed)
- **Repository-Wide Test Suite:** 909 passed, 2 skipped, 0 failed.

---

## 15. Git Integrity & Execution Invariants

- **Branch:** `master`
- **Staged Git Changes:** 0 (`git diff --cached` is strictly empty)
- **Frozen Artifacts Verified:**
  - EXP-06 Checkpoint SHA256: `B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF`
  - Part-I Manifest SHA256: `17F1FF35146C7CE62E90D6FCE7F197B711B55E3C3CB599610578443208669072`
  - Decision Threshold $\tau = 0.22$
- **Execution Safeguards:**
  - `training_invoked = false`
  - `gpu_invoked = false`
  - Part-III benchmark untouched.

---

## 16. Final Recommendation

Phase 8-P1-R1 successfully reconciles the empirical findings of Phase 8-P1 with strict scientific rigor:
- The candidate correspondence ($10\times$ block mean, identity orientation, zero spatial offset) is established as an **empirically supported hypothesis across two independent parent scenes** ($NCC \ge 0.85$, separation margin $+0.3595$).
- Historical preprocessing provenance is cataloged as **`NOT_DIRECTLY_VERIFIED`**.
- Generalization is bounded at **Level 2**.
- Phase 8-P2 may proceed under **Restricted Conditional Alignment**.
