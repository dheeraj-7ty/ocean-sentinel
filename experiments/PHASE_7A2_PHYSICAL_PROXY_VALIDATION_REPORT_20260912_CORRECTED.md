# Ocean Sentinel — Phase 7A.2 Physical Proxy Validation, Semantic Status Gate, and Zero-Shot Diagnostic Report (CORRECTED)

**Document Identifier:** `PHASE_7A2_PHYSICAL_PROXY_VALIDATION_REPORT_20260912_CORRECTED`  
**Parent Document:** `PHASE_7A2_PHYSICAL_PROXY_VALIDATION_REPORT_20260912`  
**Correction Addendum:** `PHASE_7A2_CORRECTION_ADDENDUM_20260913`  
**Protocol Version:** `PHASE_7A.2_20260912_CORRECTED`  
**Author / Auditor:** Senior CAO Scientific Data / Protocol Auditor & Implementation Engineer  
**Original Date:** September 12, 2026  
**Correction Date:** September 13, 2026  
**Status:** AUDITED, AMENDED & COMPLETED  

---

## 1. Executive Summary & Authoritative Invariants

All requirements of Phase 7A.2 have been executed under strict serial process control and verified across all audit invariants. This corrected version replaces provisional terminology ("false positives", "lookalike FAR", "native candidate resolution") with protocol-compliant terms (`PREDICTED_POSITIVE_PIXEL_FRACTION`, `PROVISIONAL_PROXY_ALARM_RATE`, `PARENT_PRODUCT_ALARM_RATE`) and includes parent-product clustered metrics.

```
+----------------------------------------------------------------------------------------------------+
|                               PHASE 7A.2 AUTHORITATIVE STATE (CORRECTED)                           |
+-----------------------------------------+----------------------------------------------------------+
| Governance Constraint                   | Certified State                                          |
+-----------------------------------------+----------------------------------------------------------+
| EXP-07 or Any Model Training            | STRICTLY FORBIDDEN / NOT AUTHORIZED                      |
| Trujillo Part III Benchmark             | PERMANENTLY QUARANTINED (Rule 38)                       |
| Part-I Internal Development Split       | FROZEN (SHA-256: 17F1FF35146C7CE62E90D6FCE7F197B7...)    |
| EXP-06 Development Baseline             | FROZEN (Val IoU 0.7217, CW FAR 0.55%, tau=0.22)          |
| Canonical Decision Threshold (tau)      | 0.22 (FROZEN)                                            |
| Candidate Set Reconciliation            | SET_G = 547 candidates across 343 parent products        |
| Physical Acquisition Route              | CDSE Live Process API (Dual-Pol VV/VH, Float32, 640x640) |
| Physical Validation Result              | 517 VALIDATED / 30 REJECTED_ACQUISITION (100% Accounted)   |
| Semantic Status Gate                    | 517 SEMANTIC_STATUS_UNRESOLVED (0 Forced Negative Labels)|
| Evaluation Role                         | PROVISIONAL_PROXY_DIAGNOSTIC_ONLY (No Model Selection)   |
| Zero-Shot Provisional Alarm Rate        | 89.75% Patch Alarm Rate / 71.60% Predicted Positive Frac |
| Parent-Product Alarm Rate               | 89.23% (290 / 325 parent products with >= 1 alarm)       |
| Regression Guardrail Suite              | PASSED (tests/test_phase_7a_protocol_guardrails)         |
+-----------------------------------------+----------------------------------------------------------+
```

---

## 2. Epistemological Categorization (Scientific Rigor)

In strict accordance with Ocean Sentinel governance standards, all statements, results, and findings in this audit are partitioned into the following epistemological categories:

### 2.1 SOURCE FACT (Authoritative Data from Primary Literature & Satellites)
- The DARTIS catalog (`data_matrix.tab`, Yang & Singha, 2025) provides 2,290 candidate bounding boxes across `nw` (open water) and `nc` (coastal water) subsets.
- Primary Sentinel-1 observations are recorded as Level-1 Ground Range Detected (GRD) products in Interferometric Wide (IW) swath mode with dual polarization (`1SDV`: VV + VH).
- The corner coordinates in `data_matrix.tab` are recorded in geographic coordinates under the WGS 84 datum (`EPSG:4326`).
- Part-I development rasters (1,200 rasters) and Part-III benchmark rasters (450 rasters) are natively georeferenced in `EPSG:4326`.

### 2.2 OBSERVED RESULT (Direct Measurements from Verification Pipelines)
- Pre-acquisition spatial overlap tests demonstrated that 680 candidate regions share parent-product identity with Trujillo Part III benchmark scenes and were quarantined under Rule 38.
- Pre-acquisition spatial overlap tests demonstrated that 1,063 candidate regions share parent-product identity with Part-I development scenes and were quarantined to prevent internal development leakage.
- Exactly 547 candidate regions across 343 parent products are fully disjoint from both Part-I and Part-III (`SET_G`).
- The Copernicus Sentinel Hub Process API reconstructed dual-polarization SAR rasters with dimensions $640 \times 640$, float32 data type, native `EPSG:4326` projection, and valid backscatter ranges.
- Exactly 517 rasters passed all 28 physical raster integrity checks on disk (100% finite data, valid dual polarization, correct dimensions, non-degenerate backscatter).
- Exactly 30 candidate rasters were rejected during physical validation due to swath boundary intersection causing peripheral nodata/NaN pixels.

### 2.3 CALCULATED RESULT (Deterministic Computations & Metrics)
- SHA-256 cryptographic checksum of frozen proxy manifest: `347A0CD9409377197783BBAE42A89EC77A1BE63FD84E777BCE0009804C39F6AE`.
- SHA-256 cryptographic checksum of frozen EXP-06 checkpoint: `B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF`.
- SHA-256 cryptographic checksum of Part-I split manifest: `17F1FF35146C7CE62E90D6FCE7F197B711B55E3C3CB599610578443208669072` (strictly identical).
- Evaluated proxy pixel denominator: $135,528,448\text{ pixels}$ ($517 \times 512 \times 512$).
- Total predicted positive pixels: $97,044,583\text{ pixels}$ (executed norm) / $97,054,851\text{ pixels}$ (canonical norm).
- Predicted Positive Pixel Fraction: $71.6046\%$ (executed norm) / $71.6122\%$ (canonical norm).
- Provisional Patch Alarm Rate ($\ge 1\text{ px}$): $464 / 517$ ($89.7485\%$).
- Significant Patch Alarm Rate ($\ge 100\text{ px}$): $464 / 517$ ($89.7485\%$).
- Parent-Product Alarm Rate ($\ge 1\text{ alarm}$): $290 / 325$ unique parent products ($89.23\%$).

### 2.4 INFERENCE (Logical Deductions from Empirical Evidence)
- The high provisional patch alarm rate ($89.75\%$) and parent-product alarm rate ($89.23\%$) demonstrate that the model produces predicted-positive responses across the physically validated but semantically unresolved proxy population. The specific physical cause of these backscatter depressions (whether biogenic films, wind slicks, low-wind areas, or unrecorded anthropogenic discharges) remains unverified.
- The model's low clean water false alarm rate on Part-I DEV ($0.55\%$) contrasted with $89.75\%$ provisional alarm rate on DARTIS open-water patches proves that clean water validation in Part-I does not establish model behavior across broader maritime domains.

### 2.5 HYPOTHESIS (Testable Proposals for Future Governed Phases)
- If semantically verified hard negative proxies are eventually established under a governed protocol, targeted negative-class regularization may reduce predicted-positive responses on natural sea-surface roughness depressions without degrading positive oil slick recall.

### 2.6 UNKNOWN / UNRESOLVED (Explicitly Unproven Claims & Scientific Limits)
- Whether the dark features observed in the DARTIS candidate rasters represent biogenic slicks, internal waves, low-wind areas, or lookalikes: **SEMANTIC STATUS UNRESOLVED**.
- DARTIS catalog metadata establishes only the absence of reported oil spills in 2019; it does NOT provide validated per-pixel segmentation ground truth.
- Therefore, **zero candidate rasters are labeled as CONFIRMED_NEGATIVE or SEMANTICALLY_VALIDATED_NEGATIVE_PROXY**.

---

## 3. Physical Raster Acquisition & Validation Accounting

```
+----------------------------------------------------------------------------------------------------+
|                                PHYSICAL ACQUISITION & VALIDATION AUDIT                             |
+---------------------------------------+-------------------+----------------------------------------+
| Metric Category                       | Count             | Scientific Disposition                 |
+---------------------------------------+-------------------+----------------------------------------+
| Total Candidates Targeted             | 547               | All records in SET_G                   |
| Physically Validated on Disk          | 517               | Pass all 28 physical raster checks     |
| Rejected Acquisition                  | 30                | Documented swath boundary edge NaNs   |
| Incomplete / Unaccounted Candidates   | 0                 | 100% Complete Accounting               |
| Total Physical Bytes Stored           | 1,215,095,631 B   | Multi-band Float32 GeoTIFFs            |
| Primary Image Dimensions              | 640 x 640         | Reconstructed candidate raster         |
| Evaluation Tile Crop                  | 512 x 512         | Central window (Architecture native)   |
| Bands Acquired                        | Band 1: VV        | Band 2: VH (Paired identical pass)     |
| Projection / Datum                    | EPSG:4326         | Homogeneous with Part I and Part III   |
+---------------------------------------+-------------------+----------------------------------------+
```

### Forensic Analysis of 30 Rejected Acquisitions:
All 30 rejections exhibited finite pixel fractions between $89.6\%$ and $99.9995\%$. In each case, the rectangular bounding box intersected the diagonal perimeter of the Sentinel-1 SAR swath, resulting in nodata pixels along the tile boundary. Rather than imputing or masking unobserved data without source authorization, the pipeline strictly classified these candidates as `REJECTED_ACQUISITION`, preserving absolute data integrity.

---

## 4. Semantic Status Adjudication Gate

A hard firewall was enforced between physical validity and semantic truth:

```
PROVISIONAL CANDIDATE (SET_G, N=547)
        │
        ├──► PHYSICAL VALIDATION ───[FAIL, N=30]───► REJECTED_ACQUISITION
        │
        └──► [PASS, N=517]
             PHYSICALLY_VALIDATED_PROXY
                     │
                     ▼
             SEMANTIC STATUS GATE
                     │
                     ├──► [Authoritative Per-Pixel Ground Truth Available?]
                     │          ├──► NO  ──► SEMANTIC_STATUS_UNRESOLVED (N=517)
                     │          └──► YES ──► SEMANTICALLY_VALIDATED_NEGATIVE_PROXY (N=0)
                     │
                     ▼
             OFFICIAL CLASSIFICATION:
             - PHYSICALLY_VALIDATED_PROXY = 517
             - SEMANTIC_STATUS_UNRESOLVED = 517
             - CONFIRMED_NEGATIVE = 0 (PROHIBITED)
             - SEMANTICALLY_VALIDATED_NEGATIVE_PROXY = 0
```

**CRITICAL SCIENTIFIC GOVERNANCE RULING:**  
Because DARTIS metadata establishes only the regional absence of reported oil spills in 2019 and lacks per-pixel ground truth, promoting physically valid rasters to `CONFIRMED_NEGATIVE` or `SEMANTICALLY_VALIDATED_NEGATIVE_PROXY` is scientifically unsupportable. All 517 physically valid candidates are preserved honestly as `SEMANTIC_STATUS_UNRESOLVED`.

---

## 5. EXP-06 Zero-Shot Diagnostic Evaluation (Corrected)

### 5.1 Diagnostic Metrics
```
+----------------------------------------------------------------------------------------------------+
|                         ZERO-SHOT EXP-06 PROVISIONAL PROXY DIAGNOSTIC (CORRECTED)                  |
+---------------------------------------+-------------------+----------------------------------------+
| Metric Parameter                      | Value             | Evaluation Scope & Caveat              |
+---------------------------------------+-------------------+----------------------------------------+
| Metric Name                           | PROVISIONAL_PROXY_ALARM_RATE | Explicitly provisional      |
| Population Evaluated                  | Physically Valid Proxies     | Semantic Status Unresolved  |
| Evaluated Patches (Denominator)       | 517               | Exactly the physically validated count |
| Total Pixels Evaluated                | 135,528,448 px    | 517 patches x 512 x 512 pixels         |
| Total Predicted Positive Pixels       | 97,044,583 px     | Executed normalization                 |
| Predicted Positive Pixel Fraction     | 71.6046%          | 97,044,583 / 135,528,448               |
| Provisional Patch Alarm Rate (>= 1px) | 464 / 517 (89.75%)| Patches triggering >= 1 alarm pixel    |
| Significant Alarm Rate (>= 100px)     | 464 / 517 (89.75%)| Patches triggering >= 100 alarm pixels |
| Unique Parent Products Evaluated      | 325 products      | Clustering accounted for               |
| Parent Products with >= 1 Alarm       | 290 / 325 (89.23%)| Observed across large majority of parent products |
| Prohibited Terminology Check          | 'lookalike FAR'   | ENFORCED AS PROHIBITED                 |
+---------------------------------------+-------------------+----------------------------------------+
```

---

## 6. Document Provenance & Certification

- **Original Report:** `experiments/PHASE_7A2_PHYSICAL_PROXY_VALIDATION_REPORT_20260912.md`
- **Correction Addendum:** `experiments/PHASE_7A2_CORRECTION_ADDENDUM_20260913.md`
- **Reproduction Payload:** `experiments/performance/exp06_positive_bce_weight/exp06_proxy_zero_shot_diagnostic_reproduction.json`
- **Certified By:** Senior CAO Scientific Data / Protocol Auditor & Implementation Engineer
