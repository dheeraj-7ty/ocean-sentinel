# Ocean Sentinel — Scientific Integrity Audit

**Audit Target**: Phase 2 Scientific Pipeline & Evaluation Governance  
**Authority**: Ocean Sentinel Chief AI Officer (CAO)  
**Standard**: Strict Zero Data Leakage & Defensible Empirical Science  

---

## 1. Zero Data Leakage Verification

### A. Threshold Selection Protocol
- **Implementation**: [`src/ocean_sentinel/ml/threshold.py::optimize_threshold_on_validation`](file:///D:/Projects/ocean-sentinel/src/ocean_sentinel/ml/threshold.py)
- **Governance Rule**: Binary classification threshold MUST be selected strictly over the validation set. Held-out test data must never be inspected during threshold optimization.
- **Audit Finding**:
  In [`scripts/train_exp01.py`](file:///D:/Projects/ocean-sentinel/scripts/train_exp01.py#L770-L800), `run_evaluation_and_reporting()` computes:
  ```python
  threshold_res = optimize_threshold_on_validation(
      model=model,
      val_loader=val_loader,
      criterion=criterion,
      device=device,
      use_amp=use_amp,
      threshold_candidates=threshold_candidates,
  )
  selected_threshold = threshold_res["selected_threshold"]
  ```
  The held-out test evaluation follows strictly AFTER the threshold is frozen:
  ```python
  test_metrics = evaluate_split_with_threshold(
      model=model,
      data_loader=test_loader,
      threshold=selected_threshold,
      criterion=criterion,
      device=device,
      use_amp=use_amp,
  )
  ```
- **Verdict**: **COMPLIANT — ZERO TEST LEAKAGE**.

### B. Normalization Statistics Isolation
- **Implementation**: [`src/ocean_sentinel/ingestion/dataset.py`](file:///D:/Projects/ocean-sentinel/src/ocean_sentinel/ingestion/dataset.py#L141-L149)
- **Governance Rule**: Normalization parameters ($\mu, \sigma$) must be computed strictly over the training split. Validation and test sets must receive frozen training statistics.
- **Audit Finding**:
  [`spatial_split_manifest.json`](file:///D:/Projects/ocean-sentinel/data/metadata/trujillo_2024/spatial_split_manifest.json) carries `computed_from_split: "train"`, derived across 840 training patches (3,523,215,360 valid pixels). `TrujilloTileDataset` applies these frozen parameters identically across train, val, and test instances without computing local split statistics.
- **Verdict**: **COMPLIANT — ZERO NORMALIZATION CONTAMINATION**.

### C. Spatial Split Defensibility
- **Implementation**: [`tests/test_spatial_split.py`](file:///D:/Projects/ocean-sentinel/tests/test_spatial_split.py)
- **Audit Finding**:
  Independent geometric intersection checks over all 1,200 raw GeoTIFF bounding boxes and geotransforms prove:
  - Cross-split positive-area overlapping pairs: **0**
  - Identical geotransforms shared across splits: **0**
  - Minimum cross-split spatial buffer separation: **> 10.0 km**
  - All 16 derived 512×512 tiles from each parent patch inherit the parent's split assignment unconditionally.
- **Verdict**: **COMPLIANT — SPATIALLY DEFENSIBLE PARTITION**.

---

## 2. Language & Scientific Claims Audit

| Claim Area | Standard | Codebase Status | Classification |
| :--- | :--- | :--- | :---: |
| **Causality** | Avoid causal language regarding backscatter variations and oil presence. | All documentation and module docstrings characterize model predictions as statistical correlations in SAR backscatter imagery. | **OBSERVED FACT** |
| **Calibration** | Avoid claiming raw sigmoid outputs are calibrated physical probabilities. | Docstrings explicitly state that sigmoid outputs are classification confidence scores, not calibrated Bayesian probabilities of slick thickness. | **OBSERVED FACT** |
| **Generalization** | Avoid claiming global ocean generalization beyond Trujillo Part I corpus. | Project documentation strictly bounds findings to Sentinel-1 C-band SAR scenes over the documented maritime geographic sectors. | **OBSERVED FACT** |
| **Hardware Throughput** | Avoid claims based on theoretical FLOPs. | Throughput is recorded strictly as empirical samples/sec measured on physical hardware (e.g. 32.15 samples/sec local, 35+ samples/sec cloud). | **OBSERVED FACT** |

---

## 3. Scientific Integrity Certification

**Certification Status**: **CERTIFIED LEAKAGE-FREE & EMPIRICALLY SOUND**  
No methodological drift or data leakage vulnerabilities exist in the training pipeline.
