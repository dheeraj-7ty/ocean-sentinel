# OCEAN SENTINEL — PHASE 7B.0 CORRECTION ADDENDUM
**Document Identifier:** `PHASE_7B0_CORRECTION_ADDENDUM_20260913`  
**Governing Role:** Senior CAO Scientific Benchmark / Data Governance Auditor  
**Date:** September 13, 2026  
**Status:** **AUTHORITATIVE CORRECTION ADDENDUM TO PHASE 7B.0 REPORT**  
**Associated Historical Report:** [PHASE_7B0_EXTERNAL_LOOKALIKE_BENCHMARK_AUDIT_20260913.md](file:///d:/Projects/ocean-sentinel/experiments/PHASE_7B0_EXTERNAL_LOOKALIKE_BENCHMARK_AUDIT_20260913.md)

---

### 1. GOVERNANCE PURPOSE & AUDIT SCOPE

This addendum preserves the historical text of `experiments/PHASE_7B0_EXTERNAL_LOOKALIKE_BENCHMARK_AUDIT_20260913.md` bitwise without silent modification, while formally auditing and correcting preliminary technical claims regarding the leading external benchmark candidate (**Li et al. 2024/2025**, Zenodo DOI: `10.5281/zenodo.14279466`).

In Phase 7B.1, authoritative external sources (Zenodo record API, the archive byte-level headers, and the peer-reviewed methodology in *Earth System Science Data* [ESSD] preprint `10.5194/essd-2024-222` and *Remote Sensing* `10.3390/rs18010113`) were directly machine-read and inspected. This forensic audit revealed material discrepancies between the preliminary Phase 7B.0 description and the physical reality of the distributed dataset.

---

### 2. MATERIAL AUDIT CORRECTIONS TABLE

| Specification Area | Phase 7B.0 Preliminary Claim | Phase 7B.1 Authoritative Forensic Truth | Scientific Governance Significance |
| :--- | :--- | :--- | :--- |
| **Total Sample Count** | "2,628 sub-images" | **5,011 image slices** ($2,628\ \text{IW} + 2,383\ \text{WV}$) | Phase 7B.0 omitted the 2,383 Wave Mode (WV) vignettes. |
| **Imaging Modes** | "Sentinel-1 IW mode" | **Dual-Mode: IW (52.4%) + WV (47.6%)** | 47.6% of the dataset originates from open-ocean Wave Mode (WV1 & WV2), which has radically different incidence angles ($23^\circ, 36^\circ$) and spatial footprints ($20\text{ km} \times 20\text{ km}$) than IW mode. |
| **Spatial Dimensions** | "$512 \times 512$ pixels" | **$256 \times 256$ pixels** | Image slices are exactly $256 \times 256$, half the width and height of Ocean Sentinel's $512 \times 512$ tiles. |
| **Spatial Resolution** | "$10\text{ m}$ spatial resolution" | **$100\text{ m}$ spatial resolution** | Slices are downsampled by a factor of $10\times$ from native Sentinel-1 GRD ($10\text{ m}$). Missing high-frequency spatial detail cannot be recovered by upsampling. |
| **Physical Swath Footprint** | "$5.12\text{ km} \times 5.12\text{ km}$" | **$25.6\text{ km} \times 25.6\text{ km}$** | Each slice covers a geographic area $25\times$ larger than an Ocean Sentinel tile ($25.6\text{ km}$ vs $5.12\text{ km}$). |
| **Polarization** | "VV/VH dual-pol" | **Single-Polarization VV Only (100%)** | Zero VH channels exist in the distributed files. 5,011 / 5,011 slices are single-channel VV (`s1a-...-vv-...`). |
| **Radiometric Data Type** | "float32 calibrated $\sigma^0$ dB" | **16-bit Unsigned Integer (`uint16`)** | Imagery is distributed as scaled, normalized 16-bit integers ($[0, 65535]$), not physical float32 backscatter in dB. |
| **GeoTIFF Georeferencing** | "Level-1 GRD native georeferencing" | **Corner Ground Control Points (`ModelTiepointTag`)** | `CRS` is `None` in the raster header; georeferencing is stored as 4 corner tiepoints in Tag 33922 (approximate affine bounds). |
| **Upstream Lineage** | "Independent oceanographic annotation" | **Reused TenGeoP-SARwv (2,383 WV) & Tao et al. (156 IW scenes)** | The dataset explicitly incorporates external imagery from Wang et al. 2019 (TenGeoP-SARwv) and Tao et al. 2022 (IWs Dataset). It is a derived synthesis, not de novo imagery. |
| **Parent-Product Identity** | "484 unique parent products" | **484 IW source scenes + 2,383 WV vignettes** | The 484 IW scenes yielded 2,628 slices (1 to 51 slices per scene, mean 5.43). Patches from the same parent scene are correlated. |
| **Internal Data Splitting** | "Holdout evaluation benchmark" | **Random patch-level split (8:1:1)** | Li et al. split slices randomly, causing parent-scene leakage between their internal training, validation, and test sets. |
| **EXP-06 Direct Compatibility** | "Directly compatible with normalization" | **Methodologically useful but NOT directly suitable for zero-shot EXP-06** | Due to resolution ($100\text{ m}$ vs $10\text{ m}$), polarization (VV only vs VH/VV dual-pol), and radiometric format (`uint16` vs float32 dB), direct zero-shot evaluation of EXP-06 is physically invalid. |

---

### 3. CORRECTED CITATION & PROVENANCE RECORD

- **Authoritative Dataset Title:** *A dataset for semantic segmentation of typical oceanic and atmospheric phenomena from Sentinel-1 images*
- **Creators:** Quankun Li, Xue Bai, Lizhen Hu, Liangsheng Li, Yaohui Bao, Xupu Geng, Xiao-Hai Yan
- **Zenodo Record ID:** `14279466` (Version 2, updated December 7, 2024; replaces Version 1 `11410662`)
- **Persistent DOI:** [`10.5281/zenodo.14279466`](https://doi.org/10.5281/zenodo.14279466)
- **Primary Methodological Publications:**
  1. *Earth System Science Data* (ESSD Preprint): `10.5194/essd-2024-222` (Published July 1, 2024)
  2. *Remote Sensing* (Peer-Reviewed Article): `10.3390/rs18010113` (Published December 28, 2025)
- **Licensing:** Creative Commons Attribution 4.0 International (CC-BY 4.0)
- **File Asset:** `Sentinel-1 oceanic and atmospheric Phenomena dataset_V2.rar` ($818,667,409\text{ bytes}$, MD5: `5bf6e338dd2a686de5ecd5fee3e139cd`)

---

### 4. GOVERNANCE DISPOSITION

The preliminary qualification of Li et al. as a "Tier-1 Benchmark" is hereby clarified:
1. It is a **Tier-1 Phenomenon & Look-alike Segmentation Dataset** for developing and evaluating **phenomena-specialist models**.
2. It is **NOT** a direct drop-in test set for **Ocean Sentinel EXP-06**, because EXP-06 is hard-wired to $10\text{ m}$ dual-pol (VH/VV) decibel backscatter.
3. Any future evaluation of EXP-06 against these phenomena must retrieve the **native Level-1 GRD source products** ($10\text{ m}$, dual-pol) using the 484 parent product IDs rather than evaluating on the downsampled $100\text{ m}$ uint16 slices.
