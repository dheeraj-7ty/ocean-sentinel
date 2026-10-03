# Channel Mapping Audit — EXP-08 Phase 11-R4
# docs/exp08_channel_mapping_audit.md

**Document Version**: 1.0  
**Task**: OCEAN-SENTINEL-PHASE11-R4-EXP08-PREREQUISITE-CLOSURE  
**Stage**: STAGE_1 — Authoritative Channel-Mapping Forensics  
**Date**: 2026-09-27  
**Status**: **VERIFIED_WITH_LIMITATIONS**

---

## 1. Audit Objective

Determine whether EXP-06 Band 1 (Ch0) and Band 2 (Ch1) can be authoritatively mapped to VH and VV.

---

## 2. Evidence Hierarchy Applied

| Priority | Source | Status |
|---|---|---|
| A | Trujillo 2024 Marine Pollution Bulletin paper (§Data Preparation) | INACCESSIBLE — Elsevier paywall (HTTP 403) |
| B | Official Zenodo Part I page and accompanying documentation | ACCESSED — Key findings |
| C | Actual local repository code and TIFF metadata | ACCESSED — Key findings |
| D | CDSE COG asset structure | ACCESSED — Supporting context |
| E | Third-party implementations | NOT USED |

---

## 3. Evidence Inventory

### 3.1 Zenodo Official Record (DOI: 10.5281/zenodo.8346860)

**Source URL**: https://zenodo.org/records/8346860  
**Accessed**: 2026-09-27

**Zenodo Description** (verbatim):
> "The dataset comprises Sentinel-1 SAR images in Sigma0, in decibels (db), along with their ground truth. The images are **2048x2048x2**..."

**Zenodo Notes** (verbatim, emphasis added):
> "Note that only the Sentinel-1 Sigma0 images in decibels (db) with **two polarizations (VV, VH)** and dimensions of 2048x2048x2 are georeferenced."

**Interpretation**:  
The Zenodo Notes state "two polarizations (VV, VH)". This enumerates the polarizations present in the dataset but does **NOT** specify which TIFF band corresponds to which polarization. The string "(VV, VH)" is an English description of the dual-pol content, not a band-index specification.

**Classification**: REPORTED (ambiguous as to band order)

---

### 3.2 Local Source Code — `src/ocean_sentinel/inference.py`

**File**: [`src/ocean_sentinel/inference.py`](file:///d:/Projects/ocean-sentinel/src/ocean_sentinel/inference.py)  
**Line 48** (exact verbatim):

```python
# Mapping A Normalization Constants (Cross-Pol VH, Co-Pol VV in dB)
DEFAULT_NORM_MEAN = [-33.2323, -19.9405]
DEFAULT_NORM_STD = [6.4912, 4.5308]
```

**Interpretation**:  
The comment is the original EXP-06 implementation label.  
- Index 0 (Ch0) → "Cross-Pol VH"  
- Index 1 (Ch1) → "Co-Pol VV"

This means the model was trained with Ch0 = VH, Ch1 = VV.

**Classification**: VERIFIED (primary local artifact — the authoritative contract for this model)

**Caveat**: This comment was authored by the EXP-06 implementer and reflects their belief about the mapping. It is not independently verifiable from the Trujillo paper itself, because that paper is behind a paywall. However, it is the **controlling contract** for how EXP-06 actually processes data.

---

### 3.3 Local TIFF Band Statistics — All 1,200 Trujillo Part I Patches

**Inspection method**: rasterio full-population census of all 1,200 GeoTIFFs.  
**TIFF band descriptions**: `(None, None)` — **No embedded polarization labels**.

| Statistic | Band 1 (Ch0) | Band 2 (Ch1) |
|---|---|---|
| Global mean (dB) | **−33.158** | **−19.884** |
| Global std (dB) | 3.856 | 3.178 |
| EXP-06 norm mean | −33.232 | −19.941 |
| Difference | +0.074 dB | +0.057 dB |
| Patches with B1 < B2 | **1,200 / 1,200 (100%)** | — |

**SAR physics reference**:
- VH (cross-pol) typical ocean/oil: −35 to −20 dB (lower backscatter)
- VV (co-pol) typical ocean/oil: −25 to −12 dB (higher backscatter)

**Interpretation**:  
Band 1 mean (−33.158 dB) is statistically consistent with VH cross-polarization.  
Band 2 mean (−19.884 dB) is statistically consistent with VV co-polarization.  
The difference between Band 1 and Band 2 is approximately 13.3 dB, which is within the expected range for IW-mode GRDH VH/VV separation over ocean.  
The EXP-06 normalization constants match the measured band statistics with < 0.1 dB difference, confirming the normalization was computed from Band 1 = VH, Band 2 = VV.

**Classification**: CORROBORATING (statistically consistent; not independently authoritative as band labels)

---

### 3.4 Trujillo Dataset Contract — `docs/trujillo-dataset-contract.md`

**File**: [`docs/trujillo-dataset-contract.md`](file:///d:/Projects/ocean-sentinel/docs/trujillo-dataset-contract.md)  
**Section 2 (Source-Truth Audit)** explicitly categorizes:

> "Channel polarization mapping: which band is VV and which is VH (neither TIFF tags nor Zenodo defines this; guessing is forbidden)."  
> Status: **`UNKNOWN`**

This pre-existing contract statement was written before this audit. However, after finding the explicit comment in `inference.py`, it must be reconciled.

**Resolution**: The trujillo-dataset-contract correctly reflects that the TIFFs themselves have NO band labels (`descriptions: (None, None)`). The mapping is established through the EXP-06 normalization comment in `inference.py`, not from the TIFF files directly.

---

### 3.5 Trujillo Paper (Marine Pollution Bulletin 2024, DOI: 10.1016/j.marpolbul.2024.116549)

**Access result**: HTTP 403 — Elsevier paywall. Content not retrievable.  
**Status**: NOT ACCESSIBLE

The paper's §"Data Preparation" section cannot be directly verified. Therefore, the paper cannot serve as primary authority in this audit.

---

### 3.6 CDSE COG Asset Structure

From STAC metadata for pilot scenes, CDSE COG assets are:
- `vh`: `s3://eodata/...measurement/s1a-iw-grd-vh-...-cog.tiff` (single-band, VH)
- `vv`: `s3://eodata/...measurement/s1a-iw-grd-vv-...-cog.tiff` (single-band, VV)

This means: **CDSE distributes VH and VV as separate single-band COG files.** They are NOT pre-merged into a 2-band TIFF. The EXP-08 pipeline must explicitly fetch and stack `vh` (as Ch0) and `vv` (as Ch1) in the correct order to be compatible with EXP-06.

---

## 4. Synthesis

| Source | Evidence | Maps to |
|---|---|---|
| `inference.py` L48 comment | `[-33.23, -19.94]` labeled "(Cross-Pol VH, Co-Pol VV)" | **Ch0=VH, Ch1=VV** |
| TIFF Band 1 mean (−33.158 dB) | Statistically consistent with VH | Ch0=VH corroborated |
| TIFF Band 2 mean (−19.884 dB) | Statistically consistent with VV | Ch1=VV corroborated |
| EXP-06 norm constants (0.074 dB error) | Near-exact match to Band 1 as Ch0 | Ch0=VH corroborated |
| Zenodo Notes "(VV, VH)" | Enumerates polarizations present; not band-indexed | Not determinative of order |
| Trujillo TIFF descriptions | `(None, None)` — no band labels | Not determinative |
| Trujillo paper | INACCESSIBLE | Not available |

---

## 5. Determination

**FINAL VERDICT: VERIFIED_WITH_LIMITATIONS**

```
CHANNEL_MAPPING:
  Ch0 (Band 1): VH (Cross-Polarization)
  Ch1 (Band 2): VV (Co-Polarization)

EVIDENCE_BASIS: src/ocean_sentinel/inference.py line 48 comment
                (original EXP-06 implementation label)
                + full 1,200-patch band statistics census (100% consistent)
                + EXP-06 normalization mean alignment (< 0.1 dB error)

LIMITATION_1: Trujillo paper §"Data Preparation" NOT verified (paywall).
              This is the ideal primary authority and it remains inaccessible.
LIMITATION_2: TIFF files contain zero embedded polarization metadata.
LIMITATION_3: The Zenodo Notes say "(VV, VH)" which could suggest VV-first ordering,
              but this is an English description of dual-pol content, not a band-index
              specification. The normalization constants and implementation label 
              consistently indicate Ch0=VH, Ch1=VV.

HARD_BLOCK: REDUCED (see below)
CONFIDENCE: HIGH (multiple converging lines of evidence; no contradictions)
```

**Hard Block Status Update**:  
The Phase 11-R3 hard block (`CHANNEL_MAPPING = UNVERIFIED`) is now reduced to a soft warning. The channel mapping is established from the EXP-06 source code with strong statistical corroboration. The Trujillo paper §"Data Preparation" remains unverified but is no longer a blocking prerequisite, as the implementation's own contract is authoritative for how EXP-06 operates.

**EXP-08 Pipeline Contract**:  
When constructing the 2-band input from CDSE COG files, the pipeline MUST stack:
- Channel 0 (Band 1): CDSE asset `vh` 
- Channel 1 (Band 2): CDSE asset `vv`

---

## 6. CDSE Stack Construction Requirement

The EXP-08 pipeline must explicitly implement:

```python
# REQUIRED stacking order for EXP-06 compatibility
vh_band = load_cdse_cog(scene, asset='vh')   # → Ch0
vv_band = load_cdse_cog(scene, asset='vv')   # → Ch1
input_tensor = stack([vh_band, vv_band])     # shape: (2, H, W)
```

Any swap of VH/VV order would invert the model's polarization assumptions and is **FORBIDDEN**.

---

*End of Channel Mapping Audit*
