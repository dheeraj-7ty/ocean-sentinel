# Phase 7A.3 Historical Audit Correction Addendum

**Document Identifier:** `PHASE_7A3_CORRECTION_ADDENDUM_20260913`  
**Parent Document:** `PHASE_7A3_SEMANTIC_ADJUDICATION_REPORT_20260913`  
**Author / Auditor:** Senior CAO Scientific Data / Protocol Auditor & Implementation Engineer  
**Effective Date:** September 13, 2026  
**Status:** AUTHORITATIVE COMPANION AUDIT ARTIFACT  

---

## 1. Purpose & Protocol History Mandate

Under Protocol Rule 41 (Preservation of Audit History), historical evaluation artifacts must be preserved without silent modification. Whenever taxonomic inconsistencies or unsupported generalizations are identified, they must be formally documented in an addendum and codified in a corrected versioned companion artifact.

This addendum documents three critical corrections to `experiments/PHASE_7A3_SEMANTIC_ADJUDICATION_REPORT_20260913.md`, `data/metadata/proxy_semantic_evidence_matrix.json`, and `data/metadata/proxy_semantic_dataset_manifest.json`.

---

## 2. Itemized Corrections

### Correction 1: Taxonomy of the 30 Physical Acquisition Failures
- **Original Classification:**  
  `REJECTED_SEMANTIC` (30 candidates).
- **Corrected Classification:**  
  `REJECTED_ACQUISITION` (30 candidates).
- **Reason for Correction:**  
  The 30 candidates failed physical acquisition due to intersecting the swath boundary edge, resulting in nodata NaN pixels along the tile perimeter. Calling them `REJECTED_SEMANTIC` conflated physical acquisition failure with semantic disqualification. Unless an independent semantic investigation establishes a semantic reason, they must remain `REJECTED_ACQUISITION`.
- **Affected Artifacts:**  
  - `data/metadata/proxy_semantic_evidence_matrix.json`
  - `data/metadata/proxy_semantic_dataset_manifest.json`
  - `experiments/PHASE_7A3_SEMANTIC_ADJUDICATION_REPORT_20260913.md`
- **Scientific Consequence:**  
  Maintains rigorous separation between physical data pipeline failures and semantic evidence adjudication.
- **Regression Guardrail:**  
  `tests/test_phase_7a_protocol_guardrails.py::test_guardrail_03_acquisition_rejection_cannot_become_semantic_rejection_without_evidence`

---

### Correction 2: Correction of Parent-Product Alarm Distribution Language
- **Original Statement (Sections 4.4, 7.3):**  
  *"Alarms are distributed across almost the entire parent-product ensemble rather than concentrated in a few anomalous acquisitions"* / *"alarms are uniformly distributed"*.
- **Corrected Statement:**  
  *"Alarm-producing patches occur across a large majority of parent products in the evaluated proxy population (290 / 325, 89.23%) rather than being concentrated in a few isolated anomalous acquisitions."*
- **Reason for Correction:**  
  The word "uniformly" implies a specific spatial or statistical distribution that was not proven. The empirical fact is simply that alarm-producing patches occur across a large majority of parent products in the evaluated proxy population.
- **Affected Artifacts:**  
  - `experiments/PHASE_7A3_SEMANTIC_ADJUDICATION_REPORT_20260913.md`
- **Scientific Consequence:**  
  Restricts empirical claims to direct observational evidence without introducing unwarranted distributional assumptions.
- **Regression Guardrail:**  
  `tests/test_phase_7a_protocol_guardrails.py::test_guardrail_parent_product_alarm_distribution_language`

---

### Correction 3: Correction of Domain Generalization Language
- **Original Statement (Section 7.3):**  
  *"It is a generalized model response across Sentinel-1 acquisitions"* / *"systemic across the SAR acquisition domain"*.
- **Corrected Statement:**  
  *"The predicted-positive response is observed across a large majority of parent products in this evaluated proxy population."*
- **Reason for Correction:**  
  Extrapolating model behavior observed across 325 parent products in the Eastern Mediterranean to "the entire SAR acquisition domain" is an overgeneralized claim not supported by the sample.
- **Affected Artifacts:**  
  - `experiments/PHASE_7A3_SEMANTIC_ADJUDICATION_REPORT_20260913.md`
- **Scientific Consequence:**  
  Enforces strict epistemic bounds, confining conclusions to the evaluated population.
- **Regression Guardrail:**  
  `tests/test_phase_7a_protocol_guardrails.py::test_guardrail_no_unsupported_sar_domain_generalization`

---

## 3. Preservation & Companion Artifact Registry

1. **Original Historical Report (Preserved):**  
   [PHASE_7A3_SEMANTIC_ADJUDICATION_REPORT_20260913.md](file:///d:/Projects/ocean-sentinel/experiments/PHASE_7A3_SEMANTIC_ADJUDICATION_REPORT_20260913.md)
2. **Corrected Companion Report:**  
   [PHASE_7A3_SEMANTIC_ADJUDICATION_REPORT_20260913_CORRECTED.md](file:///d:/Projects/ocean-sentinel/experiments/PHASE_7A3_SEMANTIC_ADJUDICATION_REPORT_20260913_CORRECTED.md)
3. **Historical Addendum:**  
   [PHASE_7A3_CORRECTION_ADDENDUM_20260913.md](file:///d:/Projects/ocean-sentinel/experiments/PHASE_7A3_CORRECTION_ADDENDUM_20260913.md)
4. **Updated Semantic Evidence Matrix:**  
   [proxy_semantic_evidence_matrix.json](file:///d:/Projects/ocean-sentinel/data/metadata/proxy_semantic_evidence_matrix.json)
5. **Updated Semantic Manifest:**  
   [proxy_semantic_dataset_manifest.json](file:///d:/Projects/ocean-sentinel/data/metadata/proxy_semantic_dataset_manifest.json)
