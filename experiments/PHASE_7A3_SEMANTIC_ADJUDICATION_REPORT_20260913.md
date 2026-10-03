# Ocean Sentinel — Phase 7A.3 Semantic / Geophysical Adjudication and Proxy Evaluation-Readiness Report

**Document Identifier:** `PHASE_7A3_SEMANTIC_ADJUDICATION_REPORT_20260913`  
**Protocol Version:** `PHASE_7A.3_20260913`  
**Author / Auditor:** Senior CAO Scientific Data / Protocol Auditor & Implementation Engineer  
**Date:** September 13, 2026  
**Status:** COMPLETED, AUDITED & CERTIFIED  

---

## 1. Executive Summary & Authoritative State

Phase 7A.3 resolves the scientific, semantic, and geophysical uncertainties surrounding the 517 physically validated DARTIS proxy candidates (`SET_G`) under a strict **Blind Semantic Adjudication Firewall**.

```
+----------------------------------------------------------------------------------------------------+
|                                    PHASE 7A.3 AUTHORITATIVE STATE                                  |
+-----------------------------------------+----------------------------------------------------------+
| Governance Constraint                   | Certified State                                          |
+-----------------------------------------+----------------------------------------------------------+
| EXP-07 or Any Model Training            | STRICTLY FORBIDDEN / NOT AUTHORIZED                      |
| Trujillo Part III Benchmark             | PERMANENTLY QUARANTINED (Rule 38)                       |
| Part-I Internal Development Split       | BITWISE FROZEN (SHA-256: 17F1FF35146C7CE62E90D6FCE...)   |
| EXP-06 Checkpoint                       | FROZEN (SHA-256: B5FFCCA3D95A96A73ABAA895216BC42FA5F...) |
| Canonical Decision Threshold (tau)      | 0.22 (FROZEN)                                            |
| Total Candidates in SET_G               | 547 candidates across 343 parent products                |
| Physical Outcome                        | 517 PHYSICALLY_VALIDATED_PROXY / 30 REJECTED_ACQUISITION |
| Semantic Adjudication Outcome           | 0 SEMANTICALLY_VALIDATED_NEGATIVE_PROXY                  |
|                                         | 517 SEMANTIC_STATUS_UNRESOLVED                           |
|                                         | 30 REJECTED_SEMANTIC                                     |
| Official Negative Evaluation Denominator| 0 (No candidate qualifies for official negative benchmark)
| Blind Firewall Enforcement              | Stage A completed strictly prior to Stage B unblinding   |
| Preprocessing / Normalization Audit     | Discrepancy resolved: canonical source stats verified    |
| Geometry Contract (640x640 -> 512x512)  | Center offset: 0.0 px; Area evaluated: 64.00%           |
| Provisional Patch Alarm Rate            | 89.75% (464 / 517 patches)                               |
| Predicted Positive Pixel Fraction       | 71.61% (97,054,851 / 135,528,448 pixels)                 |
| Parent-Product Alarm Rate               | 89.23% (290 / 325 parent products with >= 1 alarm)       |
| Regression Guardrails Suite             | 50 / 50 PASSED (tests/test_phase_7a_protocol_guardrails) |
+-----------------------------------------+----------------------------------------------------------+
```

---

## 2. SOURCE FACT

1. **DARTIS Primary Catalog (`data_matrix.tab`, Yang & Singha, 2025):**  
   The primary catalog defines candidate bounding boxes for subsets `nw` (wide-swath open water) and `nc` (coastal water). Across all entries in `nw` and `nc`, the columns `xml_file`, `obj_type`, `obj_xmin`, `obj_ymin`, `obj_xmax`, and `obj_ymax` are empty or null. The catalog methodology indicates regional absence of reported oil spills in the 2019 survey, but does not provide per-pixel annotations, bounding boxes, or taxonomic classifications of dark ocean features.
2. **Sentinel-1 SAR Ground Range Detected (GRD) Products:**  
   Primary observations were acquired in Interferometric Wide (IW) swath mode with dual polarization (`1SDV`: VV + VH) and 10-meter nominal pixel spacing under the `EPSG:4326` geographic coordinate system.
3. **Canonical Normalization Source (`data/metadata/trujillo_2024/spatial_split_manifest.json`):**  
   The canonical normalization parameters used to train EXP-01 through EXP-06 were computed strictly across all 840 Part-I training patches ($3,523,215,360$ valid pixels):  
   - Channel 0 (VH dB): $\mu_0 = -33.233136989478695, \sigma_0 = 6.489985665955077$  
   - Channel 1 (VV dB): $\mu_1 = -19.941215852796695, \sigma_1 = 4.531345684833188$
4. **Part-I and Part-III Manifest Checksums:**  
   - `internal_development_split_manifest.json`: `17F1FF35146C7CE62E90D6FCE7F197B711B55E3C3CB599610578443208669072`  
   - `exp06_positive_bce_weight/best_model.pt`: `B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF`

---

## 3. OBSERVED DATA

1. **Physical Rasters on Disk:**  
   Exactly 517 `.tif` files exist in `data/raw/lookalike_candidates/dartis/rasters/`. All 517 files are $640 \times 640$ pixels, 2 bands (Band 1: VV, Band 2: VH), float32, `EPSG:4326`, and contain 100% finite backscatter values ($262,144 / 262,144$ valid pixels per band). Every file matches its recorded SHA-256 checksum in `proxy_dataset_manifest.json`.
2. **Acquisition Rejections:**  
   Exactly 30 candidates failed physical acquisition due to intersecting the swath boundary edge, resulting in nodata NaN pixels along the tile perimeter. These 30 candidates have `physical_raster_path = null` on disk.
3. **Geometry Contract (640x640 -> 512x512):**  
   The central $512 \times 512$ window (`col_off=64, row_off=64, width=512, height=512`) shares the exact pixel center $(320.0, 320.0)$ and geographic coordinate center ($\Delta\text{lon} = 0.0^{\circ}, \Delta\text{lat} = 0.0^{\circ}$) with the $640 \times 640$ raster. The model crop evaluates $262,144 / 409,600$ pixels ($64.00\%$ of the surface area), leaving a 64-pixel perimeter margin ($36.00\%$ of the area) un-evaluated.
4. **Parent-Product Clustering:**  
   The 517 physically validated patches originate from 325 unique parent Sentinel-1 products. The entire `SET_G` population (547 candidates) spans 343 unique parent products.

---

## 4. OBSERVED MODEL RESPONSE

*(Unblinded in Stage B strictly after freezing the Semantic Evidence Matrix)*

Under the canonical frozen EXP-06 model ($\tau = 0.22$, ResNet34UNet, Mapping A):
1. **Patch-Level Alarm Rate:**  
   $464$ out of $517$ evaluated patches contain $\ge 1$ predicted-positive pixel ($89.7485\%$).  
   $464$ out of $517$ evaluated patches contain $\ge 100$ predicted-positive pixels ($89.7485\%$).
2. **Pixel-Level Response Fraction:**  
   Out of $135,528,448$ evaluated pixels ($517 \times 512 \times 512$), $97,054,851$ pixels are predicted positive ($71.6122\%$) under canonical normalization, and $97,044,583$ pixels ($71.6046\%$) under executed normalization.
3. **Parent-Product Response Rate:**  
   Out of 325 unique parent Sentinel-1 products, $290$ products trigger $\ge 1$ alarm in their evaluated patches ($89.2308\%$).
4. **Alarm Distribution across Parent Products:**  
   - Mean patches per parent product: $1.59$ (range: 1 to 10)  
   - Mean alarms per parent product: $1.43$ (range: 0 to 10)  
   - Alarms are distributed across almost the entire parent-product ensemble rather than concentrated in a few anomalous acquisitions.

---

## 5. CALCULATED METRICS

```
+----------------------------------------------------------------------------------------------------+
|                                    STAGE B CALCULATED METRICS TABLE                                |
+------------------------------------+--------------------------+------------------------------------+
| Metric                             | Value                    | Definition / Scope                 |
+------------------------------------+--------------------------+------------------------------------+
| Evaluated Candidate Patches        | 517 patches              | Physically validated proxy patches |
| Unique Parent Sentinel-1 Products  | 325 products             | Parent scenes in validated pool    |
| Total Pixels Evaluated             | 135,528,448 pixels       | 517 patches x 512 x 512 pixels     |
| Predicted Positive Pixels (Canon)  | 97,054,851 pixels        | Canonical normalization            |
| Predicted Positive Pixels (Exec)   | 97,044,583 pixels        | Phase 7A.2 executed normalization  |
| Normalization Pixel Delta          | 10,268 pixels (0.0076%)  | Net difference across 135M pixels  |
| Patch Alarm Invariance             | 100.0% invariant         | 464 / 517 under both norms         |
| PROVISIONAL_PROXY_ALARM_RATE       | 89.7485% (464 / 517)     | Patches with >= 1 positive pixel   |
| SIGNIFICANT_PROXY_ALARM_RATE       | 89.7485% (464 / 517)     | Patches with >= 100 positive pixels|
| PREDICTED_POSITIVE_PIXEL_FRACTION  | 71.6122%                 | 97,054,851 / 135,528,448 pixels    |
| PARENT_PRODUCT_ALARM_RATE          | 89.2308% (290 / 325)     | Parent products with >= 1 alarm    |
+------------------------------------+--------------------------+------------------------------------+
```

---

## 6. SEMANTIC EVIDENCE

In Stage A (Blind Adjudication), every candidate was systematically audited against source catalog records, ancillary data feasibility, and epistemological standards:

1. **Evidence Tier Allocation:**  
   - **Tier A (Direct Authoritative Ground Truth):** 0 candidates.  
   - **Tier B (Strong Multi-Source Corroborated Evidence):** 0 candidates.  
   - **Tier C (Weak Contextual Evidence):** 0 candidates.  
   - **Tier D (Contextual Regional Survey Absence Only):** 517 candidates.  
   - **Rejected Physical Acquisition:** 30 candidates.
2. **Semantic Status Assignment:**  
   - `SEMANTICALLY_VALIDATED_NEGATIVE_PROXY`: 0 candidates.  
   - `PROBABLE_NEGATIVE_PROXY`: 0 candidates.  
   - `SEMANTIC_STATUS_UNRESOLVED`: 517 candidates.  
   - `REJECTED_SEMANTIC`: 30 candidates.
3. **Ancillary Evidence Audit Findings:**  
   - *In-situ marine records:* No vessel logs, buoys, or aerial surveillance records exist for these specific open-water patches during the 2019 survey.  
   - *Optical satellite imagery (Sentinel-2):* Sentinel-1 acquisitions occurred at dawn (~03:50 UTC). Contemporaneous daylight optical imagery within $\pm 1$ hour is physically non-existent; temporal offsets exceed 6 hours, precluding dynamic ocean feature alignment.  
   - *Atmospheric wind fields (ERA5):* Available at $0.25^{\circ}$ (~28 km) resolution. While confirming regional low-to-moderate wind conditions, synoptic grid cells cannot resolve sub-kilometer slick boundaries.
4. **Governed Decision:**  
   Because neither pixel-level masks nor contemporaneous high-resolution corroboration exist, **zero candidates can be promoted to validated negative ground truth**. The official negative evaluation denominator is strictly **0**.

---

## 7. INFERENCE

1. **Widespread Model Sensitivity to Maritime Backscatter Depressions:**  
   The $89.75\%$ patch alarm rate and $89.23\%$ parent-product alarm rate demonstrate that EXP-06 systematically generates positive segmentation predictions over uncalibrated open-water SAR imagery.
2. **Inference vs Causation Distinction:**  
   The data proves that the model responds to the backscatter patterns present in these candidate patches. However, without per-pixel ground truth, we cannot definitively infer whether the model is triggering on natural low-wind areas, biogenic surfactants, shear zones, or undocumented anthropogenic sheens.
3. **Clustering Proof:**  
   Because $89.23\%$ of unique parent products trigger alarms, the response is not driven by a small number of anomalous scenes (e.g. a single stormy or corrupted pass). It is a generalized model response across Sentinel-1 acquisitions.

---

## 8. HYPOTHESIS

1. **Hypothesis H-1 (Domain Bias):**  
   EXP-06 was trained on Part-I patches where the negative class consisted of clean open water with standard sea-surface roughness. Dark backscatter depressions of any origin may lie completely outside the model's learned negative distribution, causing the segmentation head to classify low-backscatter pixels as oil slicks.
2. **Hypothesis H-2 (Threshold Sensitivity):**  
   At $\tau = 0.22$, the model decision threshold was calibrated to maximize recall on Part-I DEV without exposure to diverse maritime lookalike regimes.
3. **Hypothesis H-3 (Polarization Response):**  
   Mapping A combines VH and VV channels in dB. Depressions in co-polarized VV backscatter without corresponding cross-polarized VH responses may be misclassified if the model relies primarily on VV attenuation.

---

## 9. UNKNOWN

1. The exact physical phenomenon present at the pixel level in each of the 517 candidate rasters remains **UNKNOWN**.
2. Whether the high predicted-positive fraction ($71.61\%$) represents pure false alarms or unrecorded surface films remains **UNKNOWN**.
3. The true external false alarm rate of EXP-06 against confirmed maritime lookalikes remains **UNKNOWN** because an authoritative, verified negative benchmark does not yet exist.

---

## 10. LIMITATIONS

1. **No External Evaluation Denominator:**  
   Because all 517 physically valid candidates are semantically unresolved, Phase 7A.3 cannot report an official "lookalike False Alarm Rate".
2. **Perimeter Margin Exclusion:**  
   The central $512 \times 512$ crop evaluates $64.00\%$ of the candidate area, omitting the outer 64-pixel perimeter ($36.00\%$). If a specific lookalike feature was localized in the outer perimeter, it was not evaluated by the model.
3. **Coarse Ancillary Resolution:**  
   Available reanalysis meteorological products (ERA5) lack the sub-kilometer resolution necessary to adjudicate individual slick boundaries.

---

## 11. NEXT AUTHORIZED STAGE

```
+----------------------------------------------------------------------------------------------------+
|                                    NEXT SCIENTIFIC INTERVENTION MANDATE                            |
+----------------------------------------------------------------------------------------------------+
| FINAL HARD RULE:                                                                                   |
| NO EXP-07 MODEL TRAINING.                                                                          |
| NO MODEL RETRAINING.                                                                               |
| NO THRESHOLD SEARCH OR CALIBRATION.                                                                |
+----------------------------------------------------------------------------------------------------+
```

Before any future training (EXP-07) or model selection may be authorized, the Ocean Sentinel governance committee must:
1. Formally review the Phase 7A.3 Semantic Evidence Matrix and Preprocessing Audit.
2. Determine whether an external, independently annotated lookalike benchmark with verifiable per-pixel ground truth can be acquired or curated.
3. If proxy candidates are ever proposed for training regularization, enforce a multi-level split partitioning candidates by parent product, geographic cluster, and source provenance, while strictly reserving an untouched evaluation holdout.

**No development feedback loop into Part-I or Part-III is authorized.**
