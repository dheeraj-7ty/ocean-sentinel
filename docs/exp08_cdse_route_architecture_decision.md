# CDSE Access & Radiometric Route Architecture Decision — EXP-08

**Document ID:** `EXP08_CDSE_ROUTE_ARCHITECTURE_DECISION`  
**Task ID:** `OCEAN-SENTINEL-PHASE11-R5-EXP08-FINAL-PREREQUISITE-CLOSURE`  
**Date:** 2026-09-27  
**Status:** ARCHITECTURAL DECISION — PREREQUISITE CLOSURE ONLY  
**Authority:** ChatGPT (CAO) / Human (Final Approval)  

---

## 1. Context and Objective

EXP-08 requires reconstructing external DARTIS lookalike patches from original Sentinel-1 data. Two potential CDSE access and radiometric processing routes exist:
1. **Route B (Raw Level-1 GRD COG + Client-Side Calibration LUT)**
2. **Official CDSE Process API Route (AOI Request + Server-Side SIGMA0_ELLIPSOID + Client-Side dB Conversion)**

This document provides the formal scientific and technical comparison of both routes, records repository credential availability, and establishes the implementation path for prerequisite closure.

---

## 2. Credential and Infrastructure Inventory

A rigorous environment inspection was performed without logging or serializing secrets:

| Infrastructure Component | Configured Endpoint / Target | Credential Status in Repository | Operational Viability |
|---|---|---|---|
| **CDSE OAuth2 Token Service** | `https://identity.dataspace.copernicus.eu/.../token` | **Configured & Validated** (`copernicus_client_id`, `copernicus_client_secret`) | **ACTIVE** (OAuth2 token acquisition verified: 1800s validity) |
| **CDSE Process API** | `https://sh.dataspace.copernicus.eu/api/v1/process` | **Configured & Validated** via `SentinelImageryService` | **ACTIVE** (Direct AOI retrieval supported) |
| **CDSE STAC Discovery** | `https://stac.dataspace.copernicus.eu/v1` | Public discovery (unauthenticated GET / authenticated search) | **ACTIVE** (40/40 sample resolved in Phase 11-R3) |
| **CDSE Object Storage S3** | `s3://eodata` (`eodata.dataspace.copernicus.eu`) | **NOT CONFIGURED** (No S3/AWS access keys present in `.env` or environment) | **BLOCKED** for direct S3 bucket streaming |

**Key Finding:** Direct `s3://eodata` access is blocked in this environment due to absence of CDSE S3 access keys. In contrast, the CDSE Process API is fully provisioned, authenticated, and active.

---

## 3. Scientific Comparison of Routes

### Route B: Raw COG + Local Calibration LUT Chain

- **Workflow:**
  1. Retrieve raw Level-1 GRDH measurement GeoTIFFs (`measurement/s1a-iw-grd-vh-...-cog.tiff` and `vv`).
  2. Parse calibration annotation XML (`annotation/calibration/calibration-s1a-iw-grd-*.xml`).
  3. Interpolate calibration vector grid ($A_\sigma$) bilinearly over pixel coordinates $(x, y)$.
  4. Compute $\sigma^0_{\text{linear}} = \frac{DN^2}{A_\sigma(x, y)^2}$.
  5. Convert to decibels: $\sigma^0_{\text{dB}} = 10 \cdot \log_{10}(\sigma^0_{\text{linear}} + \epsilon)$.
  6. Stack into 2-channel float32 array: $[VH, VV]$.
- **What is gained:**
  - Absolute local control over raw integer-to-float transformation.
  - Independent verification of ESA LUT interpolation math.
- **What is lost:**
  - Blocked by lack of S3 credentials for direct `s3://eodata` reads.
  - Bandwidth inefficiency: downloading/streaming full-scene COGs (~1 GB per scene per polarization) when only a 512×512 patch (~2 MB) is required.
  - Sub-pixel registration complexity if native radar geometry is preserved.

### Alternative Route: Official CDSE Process API

- **Workflow:**
  1. Post structured JSON payload to `https://sh.dataspace.copernicus.eu/api/v1/process`.
  2. Specify AOI bounding box matching DARTIS patch corners in EPSG:4326.
  3. Request collection `"sentinel-1-grd"` with:
     - `backCoeff: "SIGMA0_ELLIPSOID"`
     - `orthorectify: "true"`
  4. Evalscript explicitly maps channels:
     ```javascript
     //VERSION=3
     function setup() {
       return {
         input: ["VH", "VV", "dataMask"],
         output: { id: "default", bands: 3, sampleType: "FLOAT32" }
       };
     }
     function evaluatePixel(samples) {
       return [samples.VH, samples.VV, samples.dataMask];
     }
     ```
  5. Response is a float32 GeoTIFF containing linear $\sigma^0$ values for VH (Band 1 = Ch0) and VV (Band 2 = Ch1) plus `dataMask` (Band 3).
  6. Client-side conversion: apply $10 \cdot \log_{10}(\sigma^0 + \epsilon)$ to Bands 1 and 2 to yield calibrated dB.
- **What is gained:**
  - Official, ESA-maintained, operational calibration pipeline executed server-side.
  - Zero channel ordering ambiguity: the evalscript explicitly sets Band 1 = VH and Band 2 = VV, enforcing `EXP06_OPERATIONAL_MAPPING`.
  - Minimal bandwidth: only the exact bounding box raster is returned (~2 MB instead of ~2 GB).
  - Native `dataMask` returns exact ocean/validity boundaries.
- **What is lost:**
  - Resampling interpolation during orthorectification is governed by Sentinel Hub backend.

---

## 4. Architectural Synthesis & Path Forward

1. **Protocol Continuity:** Protocol V3 retains the definition of Route B as the primary ingestion framework while acknowledging that the CDSE Process API is the concrete HTTP implementation mechanism providing the calibrated data.
2. **Radiometric Engine Implementation (Stage 3):** To ensure zero scientific ambiguity, the repository implements an isolated, self-contained radiometric processing and calibration module (`src/ocean_sentinel/satellite/calibration.py`) supporting:
   - Full ESA LUT calibration formulas ($\sigma^0 = \frac{DN^2}{A_\sigma^2}$)
   - Linear to decibel conversion ($10 \cdot \log_{10}(\sigma^0 + \epsilon)$)
   - Finite/non-finite and non-positive value masking
   - Channel stacking order enforcement ($[VH, VV]$ → $(2, H, W)$)
   - Nodata / dataMask propagation
3. **Physical Pilot (Stage 4 & 5):** The physical compatibility pilot utilizes the authenticated CDSE Process API to inspect actual retrieved raster bytes, spatial transform, pixel dimensions, nodata behavior, and dB numerical distributions on the three designated pilot scenes.
