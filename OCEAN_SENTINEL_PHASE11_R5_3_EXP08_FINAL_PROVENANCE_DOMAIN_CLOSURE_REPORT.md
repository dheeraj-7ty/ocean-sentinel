# OCEAN SENTINEL — PHASE 11-R5.3
# FINAL EXP-08 PROVENANCE + EVALUATION-DOMAIN CLOSURE REPORT

**Document ID:** `OCEAN_SENTINEL_PHASE11_R5_3_EXP08_FINAL_PROVENANCE_DOMAIN_CLOSURE_REPORT`  
**Task ID:** `OCEAN-SENTINEL-PHASE11-R5.3-EXP08-FINAL-PROVENANCE-DOMAIN-CLOSURE`  
**Model:** Gemini 3.8 Flash High  
**Tool:** Antigravity IDE 2.0  
**Authority:** ChatGPT = CAO / Architecture Authority | Human = Final Approval Authority  
**Role:** Controlled repository forensic implementation / verification worker  
**Date:** 2026-09-27  

---

## Absolute Firewall Attestation

```yaml
EXECUTION_AUTHORIZED: FALSE
SCIENTIFIC_EXECUTION: NO
INFERENCE: NO
TRAINING: NO
HOLDOUT: NOT_ACCESSED
PART_III: NOT_ACCESSED
GPU: NO
```

Throughout this phase, zero model inference was conducted, zero weights were loaded, no EXP-08 metrics or alarm rates were evaluated, the decision threshold 0.22 remained untouched, no holdout data was accessed, and no training occurred.

---

## Executive Summary

Phase 11-R5.3 represents the **final prerequisite-integrity closure pass** on the EXP-08 protocol prior to CAO and Human authorization. Following the resolution of angular-grid vs. physical-metre wording, tile-window coverage, and channel operational contracts in R5.2, R5.3 resolves the final material forensic risks:

1. **Exact Sentinel-1 Product Provenance Pinned**: Reconciled the DARTIS `.SAFE` product IDs with official CDSE `_COG` representations. Established that over the patch bounding box during the exact 25-second acquisition window, exactly ONE Sentinel-1 product exists in the archive (`exact_match = True`, `mosaicking_ambiguity = False`).
2. **Frozen EXP-06 Normalization Contract Audited**: Confirmed the single canonical source of truth in `src/ocean_sentinel/inference.py`: `DEFAULT_NORM_MEAN = [-33.2323, -19.9405]`, `DEFAULT_NORM_STD = [6.4912, 4.5308]`. Purged historical typo values (`[-19.86, -11.96]`) from all active reports and established a deterministic guardrail test.
3. **Explicit Process API Parameters Pinned**: Explicitly specified `upsampling: "NEAREST"`, `downsampling: "NEAREST"`, `speckleFilter: "NONE"`, `backCoeff: "SIGMA0_ELLIPSOID"`, `orthorectify: "false"`. Documented that nearest-neighbor interpolation prevents artificial backscatter synthesis across sharp slick/ocean boundaries and preserves discrete dataMask borders.
4. **Evaluation Domain Geometry Formally Resolved**: Distinguished `RETRIEVAL_DOMAIN = DARTIS_AABB` (required for continuous $512 \times 512$ tile extraction) from `PRIMARY_EVALUATION_DOMAIN = DARTIS_QUADRILATERAL_FOOTPRINT` (where `primary_eval_mask = (dataMask == 1) & (dartis_polygon_mask == 1)`). Pixels in the extra $\sim 26\%$ AABB margin are prevented from triggering false alarms or distorting pixel burden.
5. **Overclaim and Chronology Hygiene**: Cleansed unsupported "reconstructed as original Sentinel-1 float32 GeoTIFFs" (replaced with "CDSE-processed Sentinel-1 GRD data represented on the frozen Trujillo angular storage grid"), refined spatial overlap semantics (zero footprint intersection $\ne$ statistical independence), and classified Trujillo chronology as unestablished.
6. **Provenance Hashing**: Recorded canonical request payload SHA-256 hashes for all physical pilots (P1, P2, P3).
7. **Deterministic Verification**: Added 15 new guardrails (`tests/test_exp08_r5_3_provenance_domain_closure.py`); 133/133 tests passed across all 8 EXP-08 test suites. Protected model checkpoint SHA-256 (`B5FFCCA3...`) verified with zero drift.

---

## Detailed Prerequisite Classification Matrix

| Audit Item | Classification | Forensic Basis & Status |
|---|---|---|
| **1. Normalization Constants Source of Truth** | `CLOSED` | `src/ocean_sentinel/inference.py` L49–50 defines `DEFAULT_NORM_MEAN = [-33.2323, -19.9405]`, `DEFAULT_NORM_STD = [6.4912, 4.5308]`. Typo `[-19.86, -11.96]` in R5.2 report corrected. Guardrail test enforces single source of truth. |
| **2. Exact Sentinel-1 Product Provenance** | `CLOSED` | DARTIS SAFE products matched to CDSE COG products with 100% prefix identity. P1: `..._02D7E5_F282_COG`, P2: `..._02CD9D_4F9F_COG`, P3: `..._02CDDA_7F3C_COG`. 25s acquisition window guarantees uniqueness; `mosaicking_ambiguity = False`. |
| **3. Process API Request Specification** | `CLOSED` | Request pinned: `backCoeff: "SIGMA0_ELLIPSOID"`, `orthorectify: "false"`, `speckleFilter: "NONE"`, `upsampling: "NEAREST"`, `downsampling: "NEAREST"`, `resx: 8.9831528e-5`, `resy: 8.9831528e-5`, `CRS: EPSG:4326`, format: `image/tiff` (float32). |
| **4. Spatial Grid & Resampling Taxonomy** | `CLOSED` | Explicitly distinguished: `TRUJILLO_STORAGE_GRID_MATCH = VERIFIED` (angular resolution $\Delta = 8.98315e-5^\circ$), `LOCAL_RESAMPLING = NONE` (zero client-side interpolation), `SERVICE_SIDE_GRID_GENERATION = YES`, `SERVICE_SIDE_INTERPOLATION = NEAREST`. |
| **5. Evaluation Domain Contract (AABB vs Polygon)** | `CLOSED` | Contract established: `RETRIEVAL_DOMAIN = DARTIS_AABB`, `PRIMARY_EVALUATION_DOMAIN = DARTIS_QUADRILATERAL_FOOTPRINT`. Evaluated strictly where `primary_eval_mask = (dataMask == 1) & (dartis_polygon_mask == 1)`. AABB context reported separately. |
| **6. Spatial Overlap Semantics** | `CLOSED` | Wording strictly audited: "demonstrating zero geometric intersection with the inspected Trujillo training raster footprints under the defined bounding box geometry (absence of footprint intersection does NOT imply proven statistical or geographical independence)." |
| **7. Channel Stacking & Mapping** | `CLOSED_WITH_LIMITATION` | `DATASET_SOURCE_TRUTH = UNKNOWN` (Trujillo §Data Preparation inaccessible). `EXP06_OPERATIONAL_CONTRACT = Ch0: VH, Ch1: VV` verified by `inference.py` L48 and normalization coupling. |
| **8. Radiometric Framing & Equivalence** | `CLOSED_WITH_LIMITATION` / `NOT_PROVEN` | `CDSE_RADIOMETRIC_DOMAIN = VERIFIED` (linear sigma0 converted to dB via $10 \cdot \log_{10}$). `TRUJILLO_NUMERICAL_EQUIVALENCE = NOT_PROVEN` (exact bitwise author preprocessing cannot be demonstrated without empirical pixel comparison during authorized execution). |
| **9. Input Construction Contract** | `CLOSED` | Complete 10-step inference pipeline verified: CDSE VH/VV $\to$ Ch0=VH/Ch1=VV $\to 10\cdot\log_{10}$ float32 dB $\to$ exact frozen normalization $\to$ no threshold changes $\to$ no client-side resizing $\to$ explicit nodata imputation to 0.0. |
| **10. Provenance Hashing** | `CLOSED` | Canonical request payload SHA-256 computed: P1 = `9e036058...`, P2 = `be0b7632...`, P3 = `64524e5d...`. Results documented in `scratch/cdse_physical_pilot_results_r5_3.json`. |
| **11. CDSE Catalog Scope** | `INFORMATIONAL` | 40/1,063 scenes verified sample is informational. The remaining 1,023 scenes are NOT claimed to be catalog-wide resolved. |
| **12. Temporal Chronology Language** | `CLOSED` | DARTIS 2019 verified. Trujillo acquisition chronology is unestablished from accessible artifacts; unsupported "2020–2023" purged from live protocol. |
| **13. Repository-Wide Claim Hygiene** | `CLOSED` | Stale terms (2468, 3047, 5515, 64x64, 232m, native resolution, valid ocean, 3x2, 6 tiles) classified and purged or marked SUPERSEDED. |
| **14. Protocol Version & Footer Alignment** | `CLOSED` | Protocol frozen as Version 3.3. Pilot document synchronized as Version 3.2. TASK_ID uniform across all Phase 11-R5.3 artifacts. |
| **15. Deterministic Guardrail Tests** | `CLOSED` | 15 new tests in `tests/test_exp08_r5_3_provenance_domain_closure.py`. Entire suite of 133 EXP-08 tests PASSED with 0 failures. |
| **16. Protected Artifact Verification** | `CLOSED` | `best_model.pt` SHA-256 verified `B5FFCCA3...`. Governance V2 files and `temporal.py` untouched. Pre-existing modifications preserved. |

---

## Stage 1: Normalization Source-of-Truth Audit

### 1.1 Code Inspection of `src/ocean_sentinel/inference.py`
Inspection of `src/ocean_sentinel/inference.py` lines 48–50 establishes:
```python
# Mapping A Normalization Constants (Cross-Pol VH, Co-Pol VV in dB)
DEFAULT_NORM_MEAN = [-33.2323, -19.9405]
DEFAULT_NORM_STD = [6.4912, 4.5308]
```
These values are strictly coupled to:
- Channel 0: VH (${\mu} = -33.2323\text{ dB}$, ${\sigma} = 6.4912\text{ dB}$)
- Channel 1: VV (${\mu} = -19.9405\text{ dB}$, ${\sigma} = 4.5308\text{ dB}$)

### 1.2 Repository-Wide Search & Purge
A comprehensive scan identified an isolated occurrence of `[-19.86, -11.96]` in `OCEAN_SENTINEL_PHASE11_R5_2_EXP08_FINAL_SCIENTIFIC_CONTRACT_CLOSURE_REPORT.md` (line 94).
- **Classification**: `HISTORICAL_TYPO`. The actual code and frozen protocol V3.2 already used `[-33.2323, -19.9405]`.
- **Action**: Corrected the typo in the R5.2 report and confirmed exact values in `docs/exp08_corrected_protocol.md` and `docs/exp08_cdse_physical_compatibility_pilot.md`.
- **Guardrail**: Added `test_no_conflicting_frozen_normalization_constants_in_live_documents` to prevent alternative constants from appearing in live protocol documents.

---

## Stage 2: Exact Sentinel-1 Product Provenance

### 2.1 SAFE to CDSE Product Mapping
In the Copernicus Data Space Ecosystem (CDSE), Sentinel-1 Level-1 GRDH products are cataloged as Cloud-Optimized GeoTIFFs with the suffix `_COG` and an updated metadata hash:

| Pilot | DARTIS SAFE Product Identifier | CDSE COG Product Identifier | Platform | Orbit / Track | 25s Acquisition Window | Match |
|---|---|---|---|---|---|---|
| **P1 (`nc`)** | `S1A_IW_GRDH_1SDV_20190124T035117_20190124T035142_025614_02D7E5_2D5A.SAFE` | `S1A_IW_GRDH_1SDV_20190124T035117_20190124T035142_025614_02D7E5_F282_COG` | Sentinel-1A | DESCENDING 167 | 2019-01-24T03:51:17 to 03:51:42 | `EXACT_MATCH` |
| **P2 (`nw`)** | `S1A_IW_GRDH_1SDV_20190104T155728_20190104T155753_025330_02CD9D_B67E.SAFE` | `S1A_IW_GRDH_1SDV_20190104T155728_20190104T155753_025330_02CD9D_4F9F_COG` | Sentinel-1A | ASCENDING 58 | 2019-01-04T15:57:28 to 15:57:53 | `EXACT_MATCH` |
| **P3 (`oc`)** | `S1A_IW_GRDH_1SDV_20190105T040043_20190105T040108_025337_02CDDA_FAEC.SAFE` | `S1A_IW_GRDH_1SDV_20190105T040043_20190105T040108_025337_02CDDA_7F3C_COG` | Sentinel-1A | DESCENDING 65 | 2019-01-05T04:00:43 to 04:01:08 | `EXACT_MATCH` |

### 2.2 Provenance Uniqueness Proof
- The acquisition time range requested from the Process API is restricted to the exact 25-second duration of the SAFE product take.
- Over the spatial extent of each patch during that 25-second interval, **exactly ONE Sentinel-1 observation exists** in the Copernicus archive.
- Therefore, `mosaicking_ambiguity = False`. Broad $\pm 1$-hour windows are strictly prohibited.

---

## Stage 3 & 4: Process API Processing Contract & Resampling

### 3.1 Pinned Process API Configuration
```json
{
  "input": {
    "bounds": {
      "bbox": [min_lon, min_lat, max_lon, max_lat],
      "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"}
    },
    "data": [
      {
        "type": "sentinel-1-grd",
        "dataFilter": {
          "timeRange": {"from": "exact_start_z", "to": "exact_stop_z"},
          "acquisitionMode": "IW",
          "polarization": "DV",
          "resolution": "HIGH"
        },
        "processing": {
          "backCoeff": "SIGMA0_ELLIPSOID",
          "orthorectify": false,
          "speckleFilter": "NONE",
          "upsampling": "NEAREST",
          "downsampling": "NEAREST"
        }
      }
    ]
  },
  "output": {
    "resx": 8.983152841195215e-05,
    "resy": 8.983152841195215e-05,
    "responses": [{"format": {"type": "image/tiff"}}]
  }
}
```

### 3.2 Scientific Justification for `upsampling: "NEAREST"`
1. **Preservation of Radiometric Boundaries**: Bilinear or bicubic interpolation synthesizes artificial intermediate backscatter values across sharp edges (such as oil slick boundaries and land/water interfaces), creating radiometric gradients not present in the source IPF product.
2. **Preservation of Binary Mask Semantics**: `dataMask` contains discrete values (0 = nodata, 1 = valid). Nearest-neighbor interpolation preserves discrete values without floating-point edge filtering.
3. **Spatial Grid Taxonomy**:
   - `TRUJILLO_STORAGE_GRID_MATCH = VERIFIED`: Output grid matches $\Delta = 8.9831528e-5^\circ$ (within 0.03%).
   - `LOCAL_RESAMPLING = NONE`: Zero client-side interpolation or reprojection.
   - `SERVICE_SIDE_GRID_GENERATION = YES`: Process API resamples Level-1 GRD swath to the requested EPSG:4326 grid.
   - `SERVICE_SIDE_INTERPOLATION = NEAREST`: Formally declared and pinned.

---

## Stage 5: Evaluation Domain Geometry (AABB vs Polygon)

### 5.1 Rotated Footprint vs Axis-Aligned Bounding Box
- Sentinel-1's near-polar orbit (inclination $\sim 98.2^\circ$) produces track-aligned rectangular patches tilted $\sim 8.2^\circ\text{--}8.5^\circ$ relative to lines of latitude/longitude.
- DARTIS annotations are defined strictly within this rotated quadrilateral (UL, UR, BR, BL).
- Enclosing the 4 corners in an axis-aligned bounding box (AABB) yields an area ratio of:
  - P1: $74.14\%$ polygon / $25.86\%$ external AABB margin
  - P2: $74.02\%$ polygon / $25.98\%$ external AABB margin
  - P3: $74.18\%$ polygon / $25.82\%$ external AABB margin

### 5.2 Contractual Domain Separation
1. **`RETRIEVAL_DOMAIN = DARTIS_AABB`**:
   - The CDSE Process API retrieves the complete AABB.
   - This rectangular canvas enables continuous, unpadded $512 \times 512$ tile extraction and full convolutional receptive field support along patch boundaries.
2. **`PRIMARY_EVALUATION_DOMAIN = DARTIS_QUADRILATERAL_FOOTPRINT`**:
   - Primary lookalike alarm rate (METRIC-L1) and pixel false-positive burden (METRIC-L2) are strictly evaluated where:
     $$\text{primary\_eval\_mask} = (\text{dataMask} == 1) \land (\text{dartis\_polygon\_mask} == 1)$$
   - Binary proposal map inside evaluation domain:
     $$\text{predicted\_mask\_poly} = (\text{probability\_map} \ge 0.22) \land \text{primary\_eval\_mask}$$
   - Any model activation occurring in the external $\sim 26\%$ AABB margin does **NOT** trigger a patch-level false alarm or contribute to primary false-positive pixel burden.
3. **`SECONDARY_REPORTING = FULL_AABB_CONTEXT`**:
   - Unmasked AABB statistics (METRIC-L1-AABB, METRIC-L2-AABB) are reported separately as an informational diagnostic of surrounding ocean behavior.

---

## Stage 10: Pilot Artifact Provenance Hashing

Canonical SHA-256 hashes of the exact Process API request payloads:
- **Pilot 1 (P1 `nc`) Payload SHA-256**:
  `9e036058277a9f77a4ccc40e8c3c32b718a82bff20dad2be9680e6329765e10e`
- **Pilot 2 (P2 `nw`) Payload SHA-256**:
  `be0b763218a0860d10cc11bb5b6d9558558a22bb5dab3b704e781aca26e5b288`
- **Pilot 3 (P3 `oc`) Payload SHA-256**:
  `64524e5df9604deae1892fd8657a8c292a3c5621361b7b4b0d607d7dae59315b`

Complete machine-readable provenance metadata is recorded in:
[`scratch/cdse_physical_pilot_results_r5_3.json`](file:///d:/Projects/ocean-sentinel/scratch/cdse_physical_pilot_results_r5_3.json)

---

## Stage 15: Test Suite Verification

### Execution Summary
```
Command: .venv\Scripts\python -m pytest tests/test_exp08_*.py -v
Result: 133 PASSED, 0 FAILED in 0.65s
```

### Breakdown by Suite
1. `tests/test_exp08_calibration.py`: **5 PASSED**
2. `tests/test_exp08_protocol_semantics.py`: **12 PASSED**
3. `tests/test_exp08_r3_protocol_semantics.py`: **21 PASSED**
4. `tests/test_exp08_r4_prerequisite_closure.py`: **23 PASSED**
5. `tests/test_exp08_r5_prerequisite_closure.py`: **19 PASSED**
6. `tests/test_exp08_r5_1_prerequisite_closure.py`: **19 PASSED**
7. `tests/test_exp08_r5_2_scientific_contract_closure.py`: **19 PASSED**
8. `tests/test_exp08_r5_3_provenance_domain_closure.py`: **15 PASSED**

All 15 Stage 15 invariants are deterministically verified.

---

## Stage 16: Protected Artifact Verification

1. **EXP-06 Checkpoint SHA-256**:
   - File: `experiments/performance/exp06_positive_bce_weight/best_model.pt`
   - Expected: `B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF`
   - Measured: `B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF`
   - Status: **VERIFIED — 100% BITWISE MATCH**
2. **Governance V2 Files**:
   - `data/metadata/governance_v2/rules.json`: Untouched (diff empty)
   - `data/metadata/governance_v2/lessons.json`: Untouched (diff empty)
   - `data/metadata/governance_v2/incidents.json`: Untouched (diff empty)
3. **Protected Source Files**:
   - `src/ocean_sentinel/temporal.py`: Untouched (diff empty)
4. **Pre-existing Tracked Modifications**:
   - `.gitignore`, `experiments/EXTERNAL_VALIDATION_READINESS.md`, `pyproject.toml`, `src/ocean_sentinel/ingestion/dataset.py` strictly preserved without resets, cleans, commits, or pushes.

---

## Stage 17: Final Prerequisite Gate Evaluation

### Protocol Gate Status: `READY_FOR_EXPLICIT_CAO_HUMAN_AUTHORIZATION`

Every prerequisite required for a scientifically sound, reproducible, and contractually valid future EXP-08 execution has been implemented, validated, and frozen.

### Remaining Known Scientific Limitations
1. **CDSE Calibration Equivalence with Trujillo Pipeline**: Classified as `NOT_PROVEN`. Cannot be proven bitwise because Trujillo Part I Data Preparation is paywalled; physical compatibility is confirmed via standard Level-1 IPF `SIGMA0_ELLIPSOID` linear power $\to$ dB conversion.
2. **Channel Mapping Source-Truth**: Classified as `VERIFIED_WITH_LIMITATIONS`. Operational contract ($Ch0 = \text{VH}, Ch1 = \text{VV}$) is verified by code and normalization binding; source dataset labeling remains `UNKNOWN`.
3. **Trujillo Acquisition Chronology**: Classified as unestablished from accessible artifacts; live protocol avoids unsupported date ranges.
4. **Level-1 GRD dataMask Scope**: Defines sensor swath data validity, not water/land classification.
5. **DARTIS Spatial Unit**: Patches are clustered within scenes; scene is the primary statistical reporting unit.

---

## Absolute Firewall Confirmation

```yaml
EXECUTION_AUTHORIZED: FALSE
SCIENTIFIC_EXECUTION: NO
INFERENCE: NO
TRAINING: NO
HOLDOUT: NOT_ACCESSED
PART_III: NOT_ACCESSED
GPU: NO
```

**THIS DOCUMENT DOES NOT AUTHORIZE MODEL INFERENCE OR SCIENTIFIC EXECUTION.**  
Execution requires separate, explicit authorization from CAO (ChatGPT) and Human Authority.
