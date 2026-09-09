# Gate 4.1 — Monolithic Kaggle Dataset Package Preflight

**Experiment ID**: `cloud_kaggle_dataset_package_preflight_20260907_022953`  
**Execution Timestamp**: 2026-09-07T02:30:00Z to 2026-09-07T02:36:00Z  
**Worker Role**: Implementation & Validation Worker under Ocean Sentinel CAO  
**Target Environment**: Local Validation & Staging Workspace (`D:\Projects\ocean-sentinel`)  

---

## 1. Decision

### **PASS**

All preflight packaging, integrity hashing, rasterio validation, pairing checks, split alignment, loader path audits, and Kaggle metadata preparations have been completed successfully. The canonical package is fully staged in `experiments/performance/cloud_kaggle_dataset_package_preflight_20260907_022953/staging/` using zero-overhead NTFS directory junctions.

**Zero bytes were transmitted over the network. Zero GPU minutes were consumed. Model training was not started. Human approval is strictly required before any data transfer in Gate 4.2.**

---

## 2. Exact Final Package Size

Every number below reflects direct filesystem measurements of the staged upload payload:

| Metric | Raw Bytes | Binary Units (GiB, $1024^3$) | Decimal Units (GB, $10^9$) |
| :--- | :---: | :---: | :---: |
| **Image GeoTIFFs (`images/Oil/*.tif`)** | `51,133,994,714` | `47.622244 GiB` | `51.133995 GB` |
| **Mask GeoTIFFs (`masks/Mask_oil/*.tif`)** | `5,053,246,936` | `4.706203 GiB` | `5.053247 GB` |
| **Manifests (`manifest/*.json`)** | `6,257,163` | `0.005828 GiB` | `0.006257 GB` |
| **Root Metadata (`dataset-metadata.json`)** | `750` | `0.000001 GiB` | `0.000001 GB` |
| **TOTAL FINAL PACKAGE** | **`56,193,499,563`** | **`52.334293 GiB`** | **`56.193500 GB`** |

### Numerical Reconciliation of Historical Figures:
- **40.71 GB** (`40,712,942,245 bytes` = `37.917 GiB` = `40.713 GB`): The raw compressed Zenodo `.7z` image archive `01_Train_Val_Oil_Spill_images.7z`.
- **47.62 GB** (often cited in earlier reports): Represents `47.622 GiB` (binary) of extracted 1,200 image GeoTIFFs.
- **51.13 GB** (`51,133,994,714 bytes`): The exact decimal gigabyte size of the 1,200 extracted image GeoTIFFs.
- **5.05 GB** (`5,053,246,936 bytes` = `4.706 GiB`): The exact decimal gigabyte size of the 1,200 uncompressed mask GeoTIFFs.
- **56.19 GB** (`56,193,499,563 bytes` = `52.334 GiB`): The complete, exact size of the final monolithic upload package.

---

## 3. Included Files

A total of **2,403 files** are included in the upload package:

| Category | Path in Package | File Count | Total Bytes | Technical Description |
| :--- | :--- | :---: | :---: | :--- |
| **SAR Images** | `images/Oil/*.tif` | 1,200 | `51,133,994,714` | 2-channel `float32`, LZW compressed GeoTIFF, EPSG:4326, native decibels ($\text{dB } \sigma^0$), $2048 \times 2048$. |
| **Masks** | `masks/Mask_oil/*.tif` | 1,200 | `5,053,246,936` | 1-channel `uint8`, uncompressed GeoTIFF, binary $\{0, 1\}$, $2048 \times 2048$. |
| **Split Manifest** | `manifest/spatial_split_manifest.json` | 1 | `5,748,446` | Canonical spatial split manifest (840 train, 180 val, 180 test; 19,200 tiles) with training-derived z-score normalization parameters. |
| **Integrity Manifest** | `manifest/integrity_manifest.json` | 1 | `508,717` | Full SHA-256 integrity manifest for all 2,401 payload files. |
| **Kaggle Metadata** | `dataset-metadata.json` | 1 | `750` | Kaggle CLI metadata specifying private visibility and package metadata. |
| **TOTAL** | | **2,403** | **`56,193,499,563`** | **Complete upload payload** |

---

## 4. Excluded Files

All auxiliary, redundant, and compressed archive files were strictly excluded from the upload package:

| Excluded Resource | Disk Bytes | Category | Reason for Exclusion |
| :--- | :---: | :--- | :--- |
| `01_Train_Val_Oil_Spill_images.7z` | `40,712,942,245` | Compressed 7z Archive | Redundant. The extracted GeoTIFF images are uploaded directly to eliminate runtime decompression on Kaggle. |
| `01_Train_Val_Oil_Spill_mask.7z` | `6,236,761` | Compressed 7z Archive | Redundant. The extracted GeoTIFF masks are uploaded directly. |
| `sample_images/` | `124,060,970` (3 files) | Duplicate Directory | Redundant. Contains exact bitwise duplicates of `images/Oil/00000.tif`, `00002.tif`, and `00003.tif`. |
| **TOTAL EXCLUDED** | **`40,843,239,976`** | **(~40.84 GB)** | **Eliminates 40.84 GB of wasteful redundant transfer.** |

---

## 5. Integrity

### **PASS**

All 2,401 payload files were individually streamed and hashed using SHA-256 across 8 parallel worker processes in 139.55 seconds (throughput: **402.7 MB/s**).

- **Integrity Manifest Path**: [`experiments/performance/cloud_kaggle_dataset_package_preflight_20260907_022953/integrity_manifest.json`](file:///D:/Projects/ocean-sentinel/experiments/performance/cloud_kaggle_dataset_package_preflight_20260907_022953/integrity_manifest.json)
- **Total Payload Files Hashed**: 2,401 files
- **Total Payload Bytes Hashed**: `56,192,990,096 bytes`
- **Corpus Root SHA-256**:
  ```
  e6e342d3c47aeed896283b31d7218d220bd465792d4d1f5d83485cc872b5c453
  ```
- **Hashing Verification**: No read errors, zero truncated streams, 100% bitwise determinism.

---

## 6. Pairing

### **PASS**

- **Image Count**: 1,200 files in `images/Oil/`
- **Mask Count**: 1,200 files in `masks/Mask_oil/`
- **Pairing Ratio**: Exactly 1:1
- **Orphan Images**: **0**
- **Orphan Masks**: **0**
- **Symmetric Set Difference**: `set()` (Empty)
- **Stem Format**: Exactly 5-digit zero-padded strings (`00000` to `01339`).

---

## 7. Split Integrity

### **PASS**

Cross-referenced the 1,200 packaged image stems against `data/metadata/trujillo_2024/spatial_split_manifest.json`:
- **Train Scenes**: Exactly 840 scenes (13,440 tiles)
- **Validation Scenes**: Exactly 180 scenes (2,880 tiles)
- **Test Scenes**: Exactly 180 scenes (2,880 tiles)
- **Total Scenes**: Exactly 1,200 scenes (19,200 tiles)
- **Missing Scenes**: **0**
- **Unmapped Files**: **0**
- **Split Membership Alterations**: **0**

---

## 8. Representative TIFF Validation

### **PASS**

Deterministic representative sampling was conducted across 10 sample archetypes using `rasterio`:
1. `00000.tif` (Early filename / Train scene)
2. `00789.tif` (Median-sized image: 43,214,483 bytes)
3. `01325.tif` (Largest image: 45,627,603 bytes)
4. `00000.tif` (Representative mask / Train scene mask)
5. `00012.tif` (Validation scene image & mask)
6. `00005.tif` (Test scene image & mask)

### Verification Findings:
- **Dimensions**: Strictly $(2048, 2048)$ across all samples.
- **Bands**: Exactly 2 for images, 1 for masks.
- **Data Types**: `float32` for images, `uint8` for masks.
- **CRS & Transform**: Images carry valid `EPSG:4326` geographic coordinates; masks carry identity transform.
- **Compression**: Images are internally `LZW` compressed; masks are uncompressed.
- **Value Integrity**: 100% finite values; 0 NaN, 0 Inf.
- **Mask Semantics**: Strictly binary $\{0, 1\}$. Oil pixel ratios range from $0.347\%$ to $4.009\%$.
- **Radiometry**: Strictly decibels ($\text{dB } \sigma^0$). Band 1 mean ~$-34\text{ to }-39\text{ dB}$ (100% negative); Band 2 mean ~$-20\text{ to }-23\text{ dB}$ (100% negative).

---

## 9. Loader Path Audit Findings

- **Document**: [`experiments/performance/cloud_kaggle_dataset_package_preflight_20260907_022953/loader_path_audit.md`](file:///D:/Projects/ocean-sentinel/experiments/performance/cloud_kaggle_dataset_package_preflight_20260907_022953/loader_path_audit.md)
- **Observed Fact**: The existing `spatial_split_manifest.json` contains hardcoded Windows paths:
  `D:\Projects\ocean-sentinel\data\raw\trujillo_2024\images\Oil\00000.tif`.
- **Kaggle Environment**: Mounted as a virtual read-only FUSE filesystem at:
  `/kaggle/input/ocean-sentinel-trujillo-corpus/images/Oil/00000.tif`.
- **Resolution Architecture**: In the Kaggle runner script / Jupyter notebook, manifest entries will be rebased in memory upon load:
  ```python
  for p in manifest.patches:
      object.__setattr__(p, "image_path", f"/kaggle/input/ocean-sentinel-trujillo-corpus/images/Oil/{p.patch_stem}.tif")
      object.__setattr__(p, "mask_path", f"/kaggle/input/ocean-sentinel-trujillo-corpus/masks/Mask_oil/{p.patch_stem}.tif")
  ```
  This requires **ZERO modifications to existing repository source code** and guarantees 100% path resolution on Linux.

---

## 10. Kaggle Constraints & Documentation Verification

- **Max Dataset Size**: Documented limit is **100 GB** via Web UI and **200 GB** via Kaggle API / CLI. The 56.19 GB package is well within both limits.
- **Private Dataset Quota**: Documented account limit is **200 GB** (or 100 GB for basic tiers). The 56.19 GB package safely fits within the quota.
- **Visibility**: Default visibility for `kaggle datasets create` is **private**. `isPrivate: true` is explicitly configured in `dataset-metadata.json`.
- **File Limit**: Package contains 2,403 files, far below Kaggle's 10,000-file UI advisory threshold.
- **Directory Mode**: CLI upload requires `--dir-mode tar` (`-r tar`) to preserve folder hierarchy without unnecessary local re-compression.

---

## 11. Upload Method

The upload method is fully specified and staged, but **WAS NOT EXECUTED**:

### Method 1: Kaggle CLI (Automated / Headless)
```bash
kaggle datasets create -p "D:\Projects\ocean-sentinel\experiments\performance\cloud_kaggle_dataset_package_preflight_20260907_022953\staging" -r tar
```
*(Requires `kaggle.json` credentials configured on the host).*

### Method 2: Kaggle Web UI (Browser-Based)
1. Navigate to `https://www.kaggle.com/datasets` -> `New Dataset`.
2. Title: `Ocean Sentinel - Trujillo Part I Oil Spill Corpus`
3. Slug: `ocean-sentinel-trujillo-corpus`
4. Set Visibility: **Private**
5. Select Folder: Point browser to the `staging/` directory or upload a pre-bundled archive.

---

## 12. Upload Time Estimates (THEORETICAL ESTIMATES)

> [!NOTE]
> **THEORETICAL ESTIMATES ONLY**: Actual upload speed depends on ISP routing, upstream peering, SSL handshake overhead, and Kaggle ingress capacity.

Calculated for the exact package size of **56,193,499,563 bytes** ($449,547,996,504\text{ bits}$):

| Upstream Bandwidth | Theoretical Transfer Time | Practical Estimate (+15% overhead) |
| :---: | :---: | :---: |
| **25 Mbps** | 4 hours 59 minutes 42 seconds | ~5 hours 45 minutes |
| **50 Mbps** | 2 hours 29 minutes 51 seconds | ~2 hours 52 minutes |
| **100 Mbps** | 1 hour 14 minutes 55 seconds | ~1 hour 26 minutes |
| **200 Mbps** | 37 minutes 28 seconds | ~43 minutes |
| **500 Mbps** | 14 minutes 59 seconds | ~17 minutes |

---

## 13. Disk Requirements

- **Staging Directory Overhead**: **0 bytes** of duplicate imagery.
  - Staging uses NTFS directory junctions (`mklink /J`) for `images/` and `masks/`.
  - Manifests and metadata occupy only `6,257,913 bytes` (~6.26 MB).
- **Current Drive D: Free Space**: **389.09 GiB** free (abundant headroom).
- **Temporary Upload Buffer Warning**: If `kaggle datasets create -r zip` is invoked, Kaggle CLI attempts to create a 56 GB `.zip` in `%TEMP%` (usually on drive C:).
  - *Recommendation*: Use `-r tar` or configure `$env:TEMP = "D:\tmp"` to avoid filling drive C:.

---

## 14. Operational Constraints Maintained

| Constraint | Observed Value | Status |
| :--- | :---: | :---: |
| **Data Transferred to Kaggle** | **0 bytes** | COMPLIANT |
| **GPU Quota Consumed** | **0.0 minutes** | COMPLIANT |
| **Model Training** | **NOT STARTED** | COMPLIANT |
| **Dataset Attached to Notebook** | **NO** | COMPLIANT |
| **Original Dataset Altered** | **NO** | COMPLIANT |
| **Production Venv Altered** | **NO** | COMPLIANT |
| **Credentials Exposed** | **NONE** | COMPLIANT |

---

## 15. Blockers

- **Zero technical blockers** in the repository or staged package.
- **One operational prerequisite**: **Human approval is required** prior to initiating the network transfer of 56.19 GB to Kaggle.

---

## 16. Human Approval Required

### **YES**
Per Gate 4.1 specifications, tens of gigabytes must not be uploaded without explicit human authorization.

---

## 17. Gate 4.2 Recommendation

**ONE precise next action:**  
Obtain human authorization for the dataset upload, followed by a controlled Kaggle dataset upload and read-only mount validation in a live Kaggle T4 session.
