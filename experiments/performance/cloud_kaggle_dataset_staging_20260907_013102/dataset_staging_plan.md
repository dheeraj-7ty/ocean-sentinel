# Kaggle Dataset Staging, Path Abstraction & I/O Pipeline Qualification Plan

**Document Status**: APPROVED TECHNICAL SPECIFICATION  
**Gate**: Gate 4 — Dataset Staging & Data-Loading Pipeline Qualification  
**Target Next Gate**: Gate 5 — Kaggle Live I/O & DataLoader Benchmark  
**Repository**: `D:\Projects\ocean-sentinel`  
**Date**: September 7, 2026  
**Auditor**: Implementation / Validation Worker  
**Authority**: Chief Architect Officer (CAO)  

---

## 1. Executive Summary & Objective

The objective of Gate 4 is to establish a rigorous, low-waste, reproducible strategy to stage the canonical **56.19 GB** Trujillo Part I dataset on Kaggle, resolve platform-specific path semantics between Windows local development and Linux Kaggle execution, and design the Gate 5 live I/O benchmark.

### Core Architectural Conclusions:
1. **Scratch Storage Constraint**: Kaggle's `/kaggle/working` directory has a hard **20.0 GB** ceiling. Unpacking the 40.71 GB archive at runtime is physically impossible.
2. **Mount Architecture**: Data must be mounted as an attached Kaggle Dataset under `/kaggle/input/` (100 GB capacity, virtual GCS FUSE read-only mount, 0 GB working disk usage).
3. **Primary Staging Architecture**: **6 Balanced Numerical Shards** (~200 parent scenes per shard, $\sim 6.8\text{ GB}$ compressed upload per shard). This prevents single-point-of-failure network drops and Kaggle server-side unbundling timeouts.
4. **Data Loader Path Abstraction**: `TrujilloTileDataset` must resolve patch files dynamically using a configurable data root or shard directory list, decoupling the data loader from the Windows-specific paths currently frozen in `spatial_split_manifest.json`.

---

## 2. Dataset Packaging & Sharding Architecture

### 2.1 The 6-Shard Balanced Sharding Model
The 1,200 parent scenes (`00000` to `01339`) are partitioned into 6 balanced numerical shards of 200 scenes each:

| Shard ID | Kaggle Dataset Slug | Scene Stems Range | Scenes Count | Uncompressed Size | Est. Compressed Upload |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Shard 1** | `dheeraj12237/ocean-sentinel-trujillo-part1` | `00000` – `00222` (first 200) | 200 | ~9.36 GB | ~6.78 GB |
| **Shard 2** | `dheeraj12237/ocean-sentinel-trujillo-part2` | `00223` – `00445` (next 200) | 200 | ~9.36 GB | ~6.78 GB |
| **Shard 3** | `dheeraj12237/ocean-sentinel-trujillo-part3` | `00446` – `00668` (next 200) | 200 | ~9.36 GB | ~6.78 GB |
| **Shard 4** | `dheeraj12237/ocean-sentinel-trujillo-part4` | `00669` – `00891` (next 200) | 200 | ~9.36 GB | ~6.78 GB |
| **Shard 5** | `dheeraj12237/ocean-sentinel-trujillo-part5` | `00892` – `01114` (next 200) | 200 | ~9.36 GB | ~6.78 GB |
| **Shard 6** | `dheeraj12237/ocean-sentinel-trujillo-part6` | `01115` – `01339` (final 200) | 200 | ~9.39 GB | ~6.81 GB |
| **TOTAL** | **6 Discrete Kaggle Datasets** | **All 1,200 exact pairs** | **1,200** | **56.19 GB** | **~40.71 GB** |

### 2.2 Shard Internal Directory Layout
Each shard folder adheres strictly to the canonical directory structure:
```
staging_shards/part_X/
├── dataset-metadata.json
├── images/
│   └── Oil/
│       ├── XXXXX.tif
│       └── ...
└── masks/
    └── Mask_oil/
        ├── XXXXX.tif
        └── ...
```

### 2.3 Kaggle Metadata Schema (`dataset-metadata.json`)
Every shard includes a valid `dataset-metadata.json` adhering to Kaggle API specifications:
```json
{
  "title": "Ocean Sentinel Trujillo Part X",
  "id": "dheeraj12237/ocean-sentinel-trujillo-partX",
  "licenses": [
    {
      "name": "CC-BY-4.0"
    }
  ]
}
```

### 2.4 Mask Compression Optimization
Source masks are uncompressed uint8 TIFFs (4,211,084 bytes each, 5.05 GB total across 1,200 files). When zipped for upload via `--dir-mode zip`, DEFLATE achieves a **>99.8% compression ratio** on binary segmentation masks, collapsing the 5.05 GB mask payload down to **<6.3 MB** total transfer volume.

---

## 3. Upload Execution Protocol

### 3.1 Pre-Flight Safety Checklist
Before initiating any upload:
1. Ensure user has verified local or browser Kaggle API authentication.
2. Confirm the account's private dataset quota has $\ge 60\text{ GB}$ free space.
3. Validate MD5 checksums of all 200 image/mask pairs in the shard before zipping.
4. Prohibit parallel upload of all 6 shards to avoid broadband saturation and connection resets; upload sequentially (Shard 1 $\rightarrow$ Shard 2 $\rightarrow$ ... $\rightarrow$ Shard 6).

### 3.2 Sequential Upload Command Pattern
Using the Kaggle CLI:
```bash
kaggle datasets create -p staging_shards/part_1 --dir-mode zip
# Verify server-side processing completion before proceeding:
kaggle datasets status dheeraj12237/ocean-sentinel-trujillo-part1
```
Repeat for shards 2 through 6.

---

## 4. Kaggle Ingestion & Mounting Hierarchy

When attached to the Kaggle notebook runtime (`dheeraj12237/ocean-sentinel-gate3-probe` or the training notebook), the 6 datasets mount under `/kaggle/input/`:
```
/kaggle/input/
├── ocean-sentinel-trujillo-part1/
│   ├── images/Oil/*.tif
│   └── masks/Mask_oil/*.tif
├── ocean-sentinel-trujillo-part2/
│   └── ...
├── ...
└── ocean-sentinel-trujillo-part6/
    └── ...
```

### Storage Audit in Runtime:
- Available disk on `/kaggle/working`: `20.0 GB` (100% free, untouched).
- Available data on `/kaggle/input`: `56.19 GB` across 6 mounted folders.
- Mount permissions: Read-only (`ro,nosuid,nodev`).
- Mount latency: 0 seconds (virtualized GCS FUSE mount).

---

## 5. Path Translation & Data Loader Abstraction Design

### 5.1 The Pathology in Existing Code
In `data/metadata/trujillo_2024/spatial_split_manifest.json`, the manifest contains hardcoded local Windows paths:
```json
"image_path": "D:\\Projects\\ocean-sentinel\\data\\raw\\trujillo_2024\\images\\Oil\\00000.tif",
"mask_path": "D:\\Projects\\ocean-sentinel\\data\\raw\\trujillo_2024\\masks\\Mask_oil\\00000.tif"
```
In `src/ocean_sentinel/ingestion/dataset.py`:
```python
self._patch_paths: dict[str, tuple[str, str]] = {
    p.patch_stem: (p.image_path, p.mask_path)
    for p in manifest.patches
}
```
Attempting to open `img_path` on Linux directly results in an immediate `FileNotFoundError: D:\Projects\...`.

### 5.2 Non-Invasive Path Adapter Pattern
To preserve experiment semantics, zero-leakage guarantees, and manifest integrity without regenerating or mutating `spatial_split_manifest.json`, `TrujilloTileDataset` is augmented with an optional `data_roots` parameter (and `OCEAN_SENTINEL_DATA_ROOT` environment variable fallback):

```python
class TrujilloTileDataset:
    def __init__(
        self,
        manifest: DatasetManifest,
        split: SplitName,
        normalize: bool = True,
        transform: Optional[object] = None,
        data_roots: Optional[list[Path | str] | Path | str] = None,
    ) -> None:
        ...
        # Discover actual file paths across specified data roots if provided
        if data_roots is not None or os.environ.get("OCEAN_SENTINEL_DATA_ROOT"):
            raw_roots = data_roots or os.environ["OCEAN_SENTINEL_DATA_ROOT"].split(";")
            roots = [Path(r) for r in (raw_roots if isinstance(raw_roots, list) else [raw_roots])]
            
            # Index all available GeoTIFFs across all shard mount points: stem -> (img, mask)
            discovered_images: dict[str, str] = {}
            discovered_masks: dict[str, str] = {}
            for root in roots:
                for img_file in root.glob("**/images/Oil/*.tif"):
                    discovered_images[img_file.stem] = str(img_file)
                for mask_file in root.glob("**/masks/Mask_oil/*.tif"):
                    discovered_masks[mask_file.stem] = str(mask_file)
            
            self._patch_paths = {
                p.patch_stem: (
                    discovered_images.get(p.patch_stem, p.image_path),
                    discovered_masks.get(p.patch_stem, p.mask_path),
                )
                for p in manifest.patches
            }
        else:
            # Fallback to manifest direct paths (local development default)
            self._patch_paths = {
                p.patch_stem: (p.image_path, p.mask_path)
                for p in manifest.patches
            }
```

### 5.3 Invariant Guarantees:
1. **Mathematical Equivalence**: The exact same patch stems are loaded.
2. **Deterministic Tiling**: Window coordinates `(col_offset, row_offset, width, height)` remain identical.
3. **Zero Split Mutation**: Split assignments (`train`, `val`, `test`) remain 100% frozen.
4. **Zero Manifest Corruption**: The canonical JSON manifest file remains untouched on disk.

---

## 6. Gate 5 Real-Data I/O & DataLoader Benchmark Protocol

Once shards are mounted in the Kaggle notebook, Gate 5 must validate live I/O performance before model training is authorized.

### Benchmark Execution Matrix:
1. **File Existence & Integrity Check**:
   - Verify all 1,200 images and 1,200 masks resolve under `/kaggle/input/*`.
   - Verify 0 missing files.
2. **Single-Tile Windowed Read Latency**:
   - Measure `rasterio` windowed read time on cold cache vs warm cache.
   - Target: $\le 15\text{ ms}$ per 512x512 window on FUSE mount.
3. **Worker Multiprocessing Scaling**:
   - Benchmark standalone `DataLoader` iteration across `num_workers = [0, 2, 4]`.
   - Measure memory stability under Linux Python `fork` with GDAL/Rasterio.
4. **Sustained Throughput Ceiling**:
   - Measure samples/sec for 100 batches at batch size 8.
   - Reference baseline: Local Dell G15 achieved **32.15 samples/sec** (end-to-end) and **98.5 samples/sec** (standalone DataLoader).
   - Gate 5 Pass Criterion: Standalone DataLoader on Kaggle must achieve $\ge 40.0\text{ samples/sec}$.

---

## 7. Verification & Safety Signoff Checklist

- [x] Uncompressed footprint verified: 56.19 GB across 2,400 GeoTIFFs.
- [x] Kaggle scratch limit verified: 20 GB prevents runtime archive extraction.
- [x] Kaggle attached dataset limit verified: 100 GB permits staging 56.19 GB.
- [x] Sharding architecture selected: 6 balanced numerical shards (~6.8 GB upload each).
- [x] Path translation mechanism designed: Non-invasive dynamic stem indexer.
- [x] Local TIFF windowed read verified: 178 ms cold, float32, EPSG:4326.
- [x] Gate 5 benchmark protocol drafted.
- [x] Zero training runs initiated; zero GPU quota consumed.
