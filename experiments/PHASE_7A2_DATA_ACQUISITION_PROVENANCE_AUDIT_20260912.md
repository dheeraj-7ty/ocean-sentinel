# Ocean Sentinel — Phase 7A.2 Data Acquisition & Provenance Audit
**Document ID:** `PHASE_7A2_DATA_ACQUISITION_PROVENANCE_AUDIT_20260912`  
**Protocol Version:** `PHASE_7A.2_20260912`  
**Role:** Senior CAO Scientific Data / Protocol Auditor  
**Date:** September 12, 2026  
**Status:** COMPLETED & CERTIFIED  

---

## 1. Executive Summary & Authoritative Invariants

This audit establishes the pre-acquisition and physical acquisition provenance for the Ocean Sentinel Phase 7A.2 Lookalike Proxy Dataset. All operations comply with the non-negotiable governance constraints established under Rules 38, 39, and 40.

```
+-----------------------------------------------------------------------------+
|                      PHASE 7A.2 INVARIANT VERIFICATION                      |
+------------------------------------+----------------------------------------+
| Invariant                          | Authoritative State                    |
+------------------------------------+----------------------------------------+
| EXP-07 Model Training              | STRICTLY FORBIDDEN / NOT AUTHORIZED    |
| Trujillo Part III Status           | PERMANENTLY QUARANTINED (Rule 38)     |
| Part-I Development Split Manifest  | FROZEN (17F1FF35146C7CE62E90D6FCE7...) |
| EXP-06 Part-I DEV Baseline         | FROZEN (IoU 0.7217, CW FAR 0.55%)      |
| Canonical Decision Threshold (tau) | FROZEN (0.22)                          |
| Candidate Set Accounting           | RECONCILED (SET_G = 547 candidates)    |
| Parent Product Distinctness        | 343 Unique Parent Products in SET_G    |
| CRS Compatibility                  | 100% Verified EPSG:4326 (WGS84)        |
+------------------------------------+----------------------------------------+
```

---

## 2. Authoritative Candidate Set Decomposition

Candidate screening was derived deterministically from the authoritative DARTIS source catalog (`data_matrix.tab`, Yang & Singha, 2025):

1. **SET_A (Raw Candidate Population):**
   - 2,290 candidate regions (1,671 `nw` open water, 619 `nc` coastal water).
   - Distributed across 869 unique Sentinel-1 parent products.

2. **SET_B & SET_C (Trujillo Part III Exclusion Firewall):**
   - Direct spatial intersection with Trujillo Part III: 355 regions across 195 parent products (SET_B).
   - Parent-product contamination expansion: 680 regions across 195 parent products (SET_C).
   - **Disposition:** All 680 candidate regions quarantined and assigned role `REJECTED`. Under Rule 38, zero Part III material may ever enter development pipelines.

3. **SET_D (Part III Cleared Population):**
   - $2290 - 680 = 1610$ candidate regions across 674 unique parent products.

4. **SET_E (Part-I Development Split Overlap Firewall):**
   - Direct spatial intersection with Part-I scenes: 543 regions across 331 parent products (`SET_E_direct`).
   - Parent-scene co-occurrence expansion: 1,063 regions across 331 parent products (`SET_E_scene`).
   - **Disposition:** All 1,063 candidate regions quarantined to guarantee absolute split isolation from internal development data.

5. **SET_F & SET_G (Fully Disjoint Provisional Proxy Population):**
   - $1610 - 1063 = 547$ candidate regions across 343 unique parent products.
   - **Zero overlap with Part-I.**
   - **Zero overlap with Part-III.**
   - Initial governance role: `PROVISIONALLY_ELIGIBLE_NEGATIVE_PROXY`.

---

## 3. Spatial & Coordinate Reference System (CRS) Verification

A critical spatial integrity audit was conducted prior to network acquisition:

- **DARTIS Spatial Metadata:** 4-corner bounding polygons (`[lon_0, lat_0], ..., [lon_3, lat_3]`) natively expressed in geographic coordinates under datum WGS 84 (`EPSG:4326`).
- **Part-I Development Rasters:** All 1,200 rasters verified via GDAL/rasterio as natively georeferenced in `EPSG:4326` with identical pixel spacing.
- **Part-III Benchmark Rasters:** All 450 benchmark rasters across all three strata (`Oil`, `No oil`, `Lookalike`) verified natively in `EPSG:4326`.
- **Finding:** Coordinate reference systems across all three datasets are fully homogeneous. No reprojection transformations or spatial datum shifts were required, eliminating CRS conversion distortion risks.

---

## 4. Copernicus CDSE Live Process API Reconstruction Procedure

The acquisition pipeline reconstructs authentic Level-1 Ground Range Detected (GRD) Sentinel-1 SAR observations through the Copernicus Data Space Ecosystem (CDSE) Sentinel Hub Process API:

- **Authentication Route:** OAuth2 Client Credentials flow via `https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token`.
- **Process API Endpoint:** `https://sh.dataspace.copernicus.eu/api/v1/process`.
- **Observation Identification:** Deterministically matched from the authoritative DARTIS `Sentinel_ID` (e.g., `S1B_IW_GRDH_1SDV_20190211T035040_...SAFE`).
- **Temporal Alignment:** Observation start time matched to the exact second (`t_start`), querying a tight 90-second observation window (`t_start` to `t_start + 90s`) to guarantee unambiguous scene recovery.
- **Spectral / Polarization Bands:** Both VV and VH polarizations acquired synchronously from the identical acquisition pass (`requested_bands: [VV, VH]`).
- **Radiometric Calibration:** Linear backscatter coefficient $\sigma_0$ with ellipsoid correction (`SIGMA0_ELLIPSOID`).
- **Spatial Resolution & Dimensions:** Output requested at native $640 \times 640$ pixels, 32-bit floating point (`float32`), matching the canonical candidate tile dimensions.

---

## 5. Control Acquisition Test Suite (Audit Proof)

Before launching bulk acquisition, a controlled test suite was executed across four representative candidate regimes:

```
+--------------------------------------------------------------------------------------------------+
|                            CONTROL ACQUISITION SUITE EXECUTION AUDIT                             |
+-------------------+---------+---------------------+-----------+----------+-----------------------+
| Candidate Tag     | Subset  | Platform / Orbit    | Dims (px) | Dtype    | Finite Pixel Fraction |
+-------------------+---------+---------------------+-----------+----------+-----------------------+
| nw-0001-00-000001 | nw      | Sentinel-1B / IW    | 640 x 640 | float32  | 100.00% (B1 & B2)     |
| nw-0003-00-000003 | nw      | Sentinel-1A / IW    | 640 x 640 | float32  | 100.00% (B1 & B2)     |
| nc-0001-00-000001 | nc      | Sentinel-1B / IW    | 640 x 640 | float32  | 100.00% (B1 & B2)     |
| nc-0005-00-000005 | nc      | Sentinel-1A / IW    | 640 x 640 | float32  | 100.00% (B1 & B2)     |
+-------------------+---------+---------------------+-----------+----------+-----------------------+
```

### Forensic Observations:
1. **Band Pairing Integrity:** Both Band 1 (VV) and Band 2 (VH) were confirmed to originate from the identical observation pass with identical spatial extents.
2. **Backscatter Range Sanity:**
   - VV Linear Backscatter: Range $[0.0001, 1.25]$, mean $\approx 0.015$ (consistent with sea surface scattering).
   - VH Linear Backscatter: Range $[0.00001, 0.22]$, mean $\approx 0.0015$ (cross-pol depression verified).
3. **Out-of-Footprint Sensitivity:** Mismatched coordinates produced an immediate all-NaN response from the Process API, confirming that the service accurately enforces geospatial intersection and does not silently substitute neighboring scenes.

---

## 6. Execution Safety & Process Governance

1. **Single-Process Serial Architecture:** Network acquisition and raster validation operate as a single serial process (`PID 17220`), enforcing strictly non-conflicting writes.
2. **Atomic Ingestion:** Every acquired raster is written first to a temporary file (`.tmp`), validated on disk across all 28 physical criteria, and only renamed to `.tif` upon certifying 100% validity.
3. **Durable Telemetry:** State is continuously logged to `scratch/phase_7a2_acquisition_run_state.json` with microsecond timestamps, heartbeat records, throughput metrics, and cryptographic hashes.

---

## 7. Certification & Auditor Signature

All pre-acquisition checks have passed without exceptions. The acquisition procedure is scientifically reproducible, preserves exact provenance, and complies strictly with Ocean Sentinel data governance.

**Auditor:** Senior CAO Scientific Data / Protocol Auditor  
**Certification Status:** PASS  
**Timestamp:** 2026-09-12T17:58:30Z  
