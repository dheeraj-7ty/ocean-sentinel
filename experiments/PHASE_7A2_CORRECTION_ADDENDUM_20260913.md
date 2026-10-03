# Phase 7A.2 Historical Audit Correction Addendum

**Document Identifier:** `PHASE_7A2_CORRECTION_ADDENDUM_20260913`  
**Parent Document:** `PHASE_7A2_PHYSICAL_PROXY_VALIDATION_REPORT_20260912`  
**Author / Auditor:** Senior CAO Scientific Data / Protocol Auditor & Implementation Engineer  
**Effective Date:** September 13, 2026  
**Status:** AUTHORITATIVE COMPANION AUDIT ARTIFACT  

---

## 1. Purpose & Historical Integrity Mandate

In strict accordance with Ocean Sentinel Scientific Protocol Rule 41 (Preservation of Audit History), historical evaluation and audit reports must NEVER be silently edited or overwritten. When inconsistencies, unsupported inferences, or terminology non-compliances are identified during higher-tier protocol audits, they must be formally preserved in their original state and amended via explicit, versioned correction addenda and corrected companion artifacts.

This addendum documents five specific corrections to `experiments/PHASE_7A2_PHYSICAL_PROXY_VALIDATION_REPORT_20260912.md` and its companion diagnostic artifact `experiments/performance/exp06_positive_bce_weight/exp06_proxy_zero_shot_diagnostic.json`.

---

## 2. Itemized Corrections

### Correction 1: Terminology of Evaluated Pixels and Alarm Metrics
- **Original Statement (Sections 1, 2.3, 6.2):**  
  `Pixel False-Positive Rate: 71.6046%`, `71.60% Pixel FPR`, `Pixel false alarms`.
- **Correction:**  
  Replace all occurrences with `PREDICTED_POSITIVE_PIXEL_FRACTION` (`71.6046%`) and `PREDICTED_POSITIVE_PIXELS` (`97,044,583 px`).
- **Reason for Correction:**  
  Under Protocol Rule 40 and Phase 7A.3 Section 16, model responses on candidates with unresolved semantic status cannot be termed "false positives" or "false alarms". The term "false positive" presumes ground-truth negative status, which has not been established for any of the 517 candidates.
- **Affected Artifacts:**  
  - `experiments/PHASE_7A2_PHYSICAL_PROXY_VALIDATION_REPORT_20260912.md`
  - `experiments/performance/exp06_positive_bce_weight/exp06_proxy_zero_shot_diagnostic.json`
- **Scientific Consequence:**  
  Prevents epistemological circularity and unwarranted claims that the model produces "71.6% false positives on maritime lookalikes", when the true nature of the imaged phenomena is scientifically unconfirmed.
- **Regression Guardrail:**  
  `tests/test_phase_7a_protocol_guardrails.py::test_provisional_terminology_enforced_no_false_positive_claims`

---

### Correction 2: Causal Attribution of Model Responses
- **Original Statement (Section 2.4 Inference):**  
  *"The high provisional patch alarm rate (89.75%) on uncalibrated open-water rasters demonstrates that the model responds strongly to maritime backscatter depressions (wind slicks, low-wind zones, biogenic films) that were unrepresented in the Part-I development training distribution."*
- **Correction:**  
  *"The high provisional patch alarm rate (89.75%) on uncalibrated open-water rasters demonstrates that the model produces predicted-positive responses on the physically validated but semantically unresolved proxy population. The specific physical cause of these depressions (whether wind slicks, low-wind zones, biogenic films, or unrecorded anthropogenic discharges) remains unproven."*
- **Reason for Correction:**  
  Violates epistemological separation between observed model response and speculative physical causation. DARTIS catalog metadata does not identify which specific physical phenomenon is present in each candidate patch.
- **Affected Artifacts:**  
  - `experiments/PHASE_7A2_PHYSICAL_PROXY_VALIDATION_REPORT_20260912.md`
- **Scientific Consequence:**  
  Restricts scientific claims to strictly what the empirical evidence supports, eliminating unverified causal explanations from official findings.
- **Regression Guardrail:**  
  `tests/test_phase_7a_protocol_guardrails.py::test_no_unsupported_causal_lookalike_claims`

---

### Correction 3: Description of Acquired Raster Dimensions
- **Original Statement (Section 3 Table):**  
  `Primary Image Dimensions: 640 x 640 | Native candidate bounding box`
- **Correction:**  
  `Primary Image Dimensions: 640 x 640 | Reconstructed candidate raster matching target patch dimensions`
- **Reason for Correction:**  
  "Native candidate bounding box" could be misinterpreted as implying that Sentinel-1 GRD imagery natively exists at 640x640 resolution, whereas 640x640 is the DARTIS crop dimension reconstructed via the Copernicus Process API at 10m pixel spacing.
- **Affected Artifacts:**  
  - `experiments/PHASE_7A2_PHYSICAL_PROXY_VALIDATION_REPORT_20260912.md`
- **Scientific Consequence:**  
  Clarifies image provenance and processing lineage.
- **Regression Guardrail:**  
  `tests/test_phase_7a_protocol_guardrails.py::test_candidate_raster_dimension_wording`

---

### Correction 4: Preprocessing Normalization Statistics Rounding Discrepancy
- **Original Statement (Section 6.1):**  
  `Normalization: μ_VH = -33.2323, σ_VH = 6.4912; μ_VV = -19.9405, σ_VV = 4.5308`
- **Correction:**  
  Document that these values represent 4-decimal-place rounded approximations from `internal_development_split_manifest.json`. The canonical source values from `trujillo_2024/spatial_split_manifest.json` are:  
  `μ_VH = -33.233136989478695, σ_VH = 6.489985665955077; μ_VV = -19.941215852796695, σ_VV = 4.531345684833188`.  
  The numerical impact on inference was formally evaluated in Phase 7A.3: the patch-level alarm count is completely invariant (464 / 517 patches under both normalizations), with an overall net difference of only 10,268 pixels out of 135,528,448 evaluated pixels (0.0076% net delta; 12,848 total differing pixels = 0.0095%).
- **Reason for Correction:**  
  Full transparency and traceability to canonical training statistics.
- **Affected Artifacts:**  
  - `experiments/PHASE_7A2_PHYSICAL_PROXY_VALIDATION_REPORT_20260912.md`
  - `experiments/performance/exp06_positive_bce_weight/exp06_proxy_zero_shot_diagnostic.json`
- **Scientific Consequence:**  
  Certifies that the rounding discrepancy does not alter the scientific conclusion of Phase 7A.2.
- **Regression Guardrail:**  
  `tests/test_phase_7a_protocol_guardrails.py::test_normalization_source_canonical_pairing`

---

### Correction 5: Addition of Parent-Product Clustered Accounting
- **Original Statement:**  
  Omitted parent-product clustered alarm rates, reporting only patch-level metrics across the 517 candidates.
- **Correction:**  
  Add parent-product clustered metrics:
  - 517 physically validated patches originate from 325 unique parent Sentinel-1 products (out of 343 parent products in `SET_G`).
  - Parent products with $\ge 1$ alarm: 290 / 325 (89.23%).
  - Alarm-producing patches occur across a large majority of parent products in the evaluated proxy population rather than being clustered in a few isolated scenes.
- **Reason for Correction:**  
  Statistical rigor: 517 candidate patches cannot be treated as 517 independent observations due to parent-product spatial and temporal clustering.
- **Affected Artifacts:**  
  - `experiments/PHASE_7A2_PHYSICAL_PROXY_VALIDATION_REPORT_20260912.md`
  - `experiments/performance/exp06_positive_bce_weight/exp06_proxy_zero_shot_diagnostic_reproduction.json`
- **Scientific Consequence:**  
  Establishes that the model's predicted-positive response is observed across a large majority of parent products in this evaluated proxy population.
- **Regression Guardrail:**  
  `tests/test_phase_7a_protocol_guardrails.py::test_parent_product_cluster_reporting`

---

## 3. Preservation & Companion Artifact Registry

1. **Original Unmodified Report (Preserved):**  
   [PHASE_7A2_PHYSICAL_PROXY_VALIDATION_REPORT_20260912.md](file:///d:/Projects/ocean-sentinel/experiments/PHASE_7A2_PHYSICAL_PROXY_VALIDATION_REPORT_20260912.md)
2. **Corrected Companion Report:**  
   [PHASE_7A2_PHYSICAL_PROXY_VALIDATION_REPORT_20260912_CORRECTED.md](file:///d:/Projects/ocean-sentinel/experiments/PHASE_7A2_PHYSICAL_PROXY_VALIDATION_REPORT_20260912_CORRECTED.md)
3. **Historical Addendum:**  
   [PHASE_7A2_CORRECTION_ADDENDUM_20260913.md](file:///d:/Projects/ocean-sentinel/experiments/PHASE_7A2_CORRECTION_ADDENDUM_20260913.md)
4. **Reproduction Diagnostic Payload:**  
   [exp06_proxy_zero_shot_diagnostic_reproduction.json](file:///d:/Projects/ocean-sentinel/experiments/performance/exp06_positive_bce_weight/exp06_proxy_zero_shot_diagnostic_reproduction.json)
