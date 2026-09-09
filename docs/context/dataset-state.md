# Ocean Sentinel — Dataset State & Acquisition Audit

**Document Version**: 2.0.0  
**Status**: ACTIVE / CANONICAL DATASET REGISTRY  
**Date**: September 2026  
**Repository**: `D:\Projects\ocean-sentinel`  
**Primary Sources**: `docs/dataset-reconnaissance.md`, `docs/dataset-selection.md`, `docs/dataset-ingestion-readiness.md`, `docs/trujillo-dataset-contract.md`, local filesystem  

---

## 1. Inventory of Acquired Assets `[VERIFIED]`

| Asset Name | Local File Path | Size on Disk | Integrity Checksum | Verified Properties |
| :--- | :--- | :---: | :---: | :--- |
| **DARTIS Metadata Catalog** | `data/metadata/yang_singha_2025/data_matrix.tab` | 2,411,266 Bytes | MD5: `7a1b9cf16587935cb9269c2360ccdc36` | 5,515 patch records; 1,181 unique primary `Sentinel_ID` values; WGS84 patch and object bounding coordinates; subsets: `ow` (2,284), `oc` (941), `nw` (1,939), `nc` (351). |
| **Trujillo Part I Mask Archive** | `data/raw/trujillo_2024/01_Train_Val_Oil_Spill_mask.7z` | 6,236,761 Bytes | MD5: `9bc53c38db2ab82d15bf6914352403ef` | Compressed 7z archive of ground-truth oil spill masks. |
| **Trujillo Part I Extracted Masks** | `data/raw/trujillo_2024/masks/Mask_oil/` | ~5.8 MB uncompressed | Verified across 1,200 files | Exactly 1,200 single-band GeoTIFF masks (`00000.tif` to `01339.tif`); $2048 \times 2048$ dimensions; `uint8`; strictly binary values {0, 1}; `CRS: None`; identity affine transform. |
| **Trujillo Part I Image Archive** | `data/raw/trujillo_2024/01_Train_Val_Oil_Spill_images.7z` | 40,712,942,245 Bytes | MD5: `e2a6a5b473ca587474d8daee9cd54e10` | Full Phase 2.0 image archive downloaded from Zenodo record 8346860; contains 1,200 GeoTIFF images in root directory `Oil/`. |
| **Trujillo Part I Extracted Images** | `data/raw/trujillo_2024/images/Oil/` | ~45 GB uncompressed | Verified across 1,200 files | Exactly 1,200 2-band `float32` GeoTIFF images (`00000.tif` to `01339.tif`); $2048 \times 2048$; LZW compression; `CRS: EPSG:4326`; valid geographic affine transforms; dB radiometry; 1:1 exact pairing with masks. |
| **CDSE Cross-Validation Audit Report** | `data/metadata/yang_singha_2025/cdse_validation_report.json` | 57,397 Bytes | Machine-generated | Full audit records of 40-scene deterministic stratified CDSE STAC search; 100% resolution. |

---

## 2. Dataset Evaluations & Status Matrix

### 2.1 Trujillo-Acatitla et al. (July 2024) `[VERIFIED]`
* **Citation**: Marine Pollution Bulletin, Vol. 204, 116549. DOI: `10.1016/j.marpolbul.2024.116549`.
* **Zenodo DOI**: Part I (`10.5281/zenodo.8346860`), Part II (`10.5281/zenodo.8253899`), Part III (`10.5281/zenodo.13761290`).
* **License**: Creative Commons Attribution 4.0 International (CC-BY 4.0).
* **Part I Image Archive (`01_Train_Val_Oil_Spill_images.7z`)**:
  - Size: 40,712,942,245 bytes compressed (~45 GB uncompressed). MD5: `e2a6a5b473ca587474d8daee9cd54e10`.
  - Contents: Exactly 1,200 paired 2-band GeoTIFF rasters, $2048 \times 2048$, `float32`, LZW compressed.
  - Radiometry: Pre-calibrated backscatter $\sigma^0$ in decibels (dB). Band 1 mean ~$-35\text{ dB}$, Band 2 mean ~$-21\text{ dB}$.
  - Georeferencing: **VERIFIED** `CRS: EPSG:4326` with valid geographic affine transforms in the North Sea.
  - Polarization Mapping: **UNKNOWN** (no tags or documentation explicitly specify which band is VV or VH; heuristic guessing forbidden).
  - Pairing: 1,200 / 1,200 (100.0%) exact stem pairing against `data/raw/trujillo_2024/masks/Mask_oil/`. Zero orphans.
  - **Authorization Status**: **PHASE 2.0 ACQUISITION AND EXTRACTION COMPLETED**.
* **Part II (Look-Alikes / Hard Negatives)**: Deferred to Phase 2.1.
* **Part III (Independent Test Set)**: Potential held-out evaluation benchmark; deferred.

### 2.2 Yang & Singha / DARTIS Project (2025) `[VERIFIED]`
* **Citation**: Earth System Science Data (ESSD), 17(12), 6807–6837. DOI: `10.5194/essd-17-6807-2025`.
* **PANGAEA DOI**: `10.1594/PANGAEA.980773`. Zenodo Code: `10.5281/zenodo.17789853`.
* **License**: Creative Commons Attribution 4.0 International (CC-BY 4.0).
* **Role**: Lineage & CDSE STAC Discovery Benchmark.
* **Public JPEG Archive (~14.1 GB)**: **REJECTED FOR TRAINING**. Lossy 8-bit quantization is scientifically unsuitable for SAR backscatter modeling.
* **Metadata Table (`data_matrix.tab`)**: **ACQUIRED AND VERIFIED**. Unlocks direct programmatic retrieval of full-precision, calibrated float32 GeoTIFFs directly from CDSE.

### 2.3 Other Candidate Datasets `[SUPERSEDED / AUDITED]`
* **Zenodo 19258036**: Corrected during audit. This record is **QPOSD**, NOT Peruvian MORP-Synth. Peruvian MORP-Synth is not part of current acquisition.
* **Krestenitis et al. (2019)**: Academic restricted, third-party mirrors severely degraded, random patch split introduces spatial leakage. Rejected as primary training data.
* **SkyTruth Cerulean**: Operational vessel-matching pipeline. Valuable reference for AIS track correlation and bilge dump attribution; not training imagery.
* **NOAA NESDIS SAB MPSR**: Operational analyst GIS shapefiles in US EEZ. Reference for case-study validation.
* **CleanSeaNet (EMSA)**: Restricted to EU maritime authorities; unavailable.

---

## 3. Storage Allocation Profile `[VERIFIED]`

* **Host Drive**: `D:\`
* **Total Drive Capacity**: ~930 GB
* **Current Free Space**: **~435.85 GB** (with 40.71 GB archive + ~45 GB extracted imagery present)
* **Safe Headroom Threshold**: 100 GB (Reserved for OS, IDE, runtime cache, Docker)
* **Usable Ingestion Budget**: **~335 GB** remaining headroom

Even after downloading and extracting the 40.71 GB Trujillo Part I imagery archive (~85 GB total footprint), drive `D:` will retain approximately 395 GB of free space (>80% available headroom).\n