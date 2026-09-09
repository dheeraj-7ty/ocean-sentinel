# Gate 4.1 Data Loader Path Audit & Kaggle Path Resolution Architecture

**Generated UTC**: 2026-09-07T02:32:00Z  
**Target Repository**: `D:\Projects\ocean-sentinel`  
**Worker Role**: Implementation & Validation Worker under Ocean Sentinel CAO  
**Gate**: Gate 4.1 — Monolithic Kaggle Dataset Packaging & Upload Preflight  

---

## 1. Executive Summary & Problem Statement

This audit analyzes the path resolution mechanisms inside the Ocean Sentinel data loading pipeline, specifically:
1. `data/metadata/trujillo_2024/spatial_split_manifest.json` (canonical manifest serialization)
2. `src/ocean_sentinel/ingestion/split.py` (`DatasetManifest.load()`)
3. `src/ocean_sentinel/ingestion/dataset.py` (`TrujilloTileDataset.__getitem__()`)
4. `scripts/train_exp01.py` (CLI arguments and dataset invocation)

### Core Pathology Identified (OBSERVED FACT)
The canonical `spatial_split_manifest.json` was generated on Windows and contains **hardcoded absolute Windows paths**:
```json
{
  "patch_stem": "00000",
  "image_path": "D:\\Projects\\ocean-sentinel\\data\\raw\\trujillo_2024\\images\\Oil\\00000.tif",
  "mask_path": "D:\\Projects\\ocean-sentinel\\data\\raw\\trujillo_2024\\masks\\Mask_oil\\00000.tif",
  "group_key": "00000",
  ...
}
```
When transferred to the Kaggle Linux environment (where the dataset is mounted at `/kaggle/input/ocean-sentinel-trujillo-corpus/`), any attempt to open `p.image_path` directly in `rasterio.open()` will fail immediately with:
```
RasterioIOError: 'D:\Projects\ocean-sentinel\data\raw\trujillo_2024\images\Oil\00000.tif' does not exist in the file system.
```

---

## 2. Detailed Component Audit

### 2.1 Manifest Generation & Schema (`split.py`)
In `src/ocean_sentinel/ingestion/split.py`:
- `PatchManifestEntry` defines:
  ```python
  @dataclass(frozen=True)
  class PatchManifestEntry:
      patch_stem: str
      image_path: str
      mask_path: str
      group_key: str
      height: int
      width: int
      channels: int
      dtype: str
      crs: Optional[str]
      radiometric_unit: str
      split: SplitName
  ```
- `DatasetManifest.load(path)` parses the JSON directly and constructs `PatchManifestEntry` instances taking `p["image_path"]` and `p["mask_path"]` verbatim as strings.
- **Path Expectation**: Absolute string path. No path rebasing or root relocation is currently implemented in `split.py`.

### 2.2 Data Loader Runtime (`dataset.py`)
In `src/ocean_sentinel/ingestion/dataset.py`:
- During construction:
  ```python
  self._patch_paths: dict[str, tuple[str, str]] = {
      p.patch_stem: (p.image_path, p.mask_path)
      for p in manifest.patches
  }
  ```
- During `__getitem__(idx)`:
  ```python
  entry = self._tiles[idx]
  img_path, mask_path = self._patch_paths[entry.parent_stem]
  
  with rasterio.open(img_path) as src:
      img = src.read(window=window).astype(np.float32)
  with rasterio.open(mask_path) as src:
      mask = src.read(1, window=window).astype(np.float32)
  ```
- **Path Expectation**: Verbatim `img_path` and `mask_path` passed directly to `rasterio.open()`.
- The class does NOT accept a `dataset_root` or `data_dir` parameter.

### 2.3 Training Runner (`train_exp01.py`)
In `scripts/train_exp01.py`:
- CLI arguments:
  ```python
  parser.add_argument(
      "--manifest",
      type=Path,
      default=DEFAULT_MANIFEST,
      help=f"Path to dataset manifest JSON. Default: {DEFAULT_MANIFEST}",
  )
  ```
- The runner loads `manifest = DatasetManifest.load(manifest_path)` and passes it to `TrujilloTileDataset(manifest, SplitName.TRAIN, ...)`.
- There is currently no CLI flag for `--data-dir` or `--dataset-root`.

---

## 3. Path Configuration Taxonomy

| Path Level | Current Local State | Intended Kaggle State | Resolution Strategy Needed |
| :--- | :--- | :--- | :--- |
| **Dataset Root** | `D:\Projects\ocean-sentinel\data\raw\trujillo_2024` | `/kaggle/input/ocean-sentinel-trujillo-corpus` | Configurable via CLI or in-memory adapter |
| **Image Subdirectory** | `images\Oil` | `images/Oil` | Standardized relative subpath `images/Oil/{stem}.tif` |
| **Mask Subdirectory** | `masks\Mask_oil` | `masks/Mask_oil` | Standardized relative subpath `masks/Mask_oil/{stem}.tif` |
| **Manifest Subdirectory** | `data\metadata\trujillo_2024` | `manifest` | `/kaggle/input/ocean-sentinel-trujillo-corpus/manifest/spatial_split_manifest.json` |

---

## 4. Proposed Kaggle Path Resolution Solutions

Per CAO non-negotiables, no production code is modified during Gate 4.1. Three architectural options are qualified for future execution (Gate 5 / EXP-01 Cloud Runner):

### Option A: Configurable `dataset_root` in `TrujilloTileDataset` (Recommended Long-Term)
Update `TrujilloTileDataset.__init__` to accept an optional `dataset_root: Optional[Path | str] = None`.
```python
def __init__(
    self,
    manifest: DatasetManifest,
    split: SplitName,
    normalize: bool = True,
    transform: Optional[object] = None,
    dataset_root: Optional[Path | str] = None,
) -> None:
    ...
    if dataset_root is not None:
        root = Path(dataset_root)
        self._patch_paths = {
            p.patch_stem: (
                str(root / "images" / "Oil" / f"{p.patch_stem}.tif"),
                str(root / "masks" / "Mask_oil" / f"{p.patch_stem}.tif"),
            )
            for p in manifest.patches
        }
    else:
        self._patch_paths = {
            p.patch_stem: (p.image_path, p.mask_path)
            for p in manifest.patches
        }
```
*Benefits*: Clean, non-invasive, backward compatible (defaults to existing behavior if `dataset_root is None`).

### Option B: Zero-Code-Change In-Memory Manifest Rebasing (Recommended for Kaggle Runner)
In the Kaggle runner script / Jupyter notebook, rebase the paths in-memory immediately after loading `DatasetManifest`:
```python
def rebase_manifest_for_kaggle(
    manifest: DatasetManifest,
    kaggle_root: Path = Path("/kaggle/input/ocean-sentinel-trujillo-corpus")
) -> DatasetManifest:
    """Rebase absolute paths to Kaggle mount directory without mutating disk JSON."""
    for p in manifest.patches:
        object.__setattr__(p, "image_path", str(kaggle_root / "images" / "Oil" / f"{p.patch_stem}.tif"))
        object.__setattr__(p, "mask_path", str(kaggle_root / "masks" / "Mask_oil" / f"{p.patch_stem}.tif"))
    return manifest
```
*Benefits*: **Requires ZERO modifications to `src/ocean_sentinel` repository code.** Works cleanly inside any standalone runner or notebook.

### Option C: Canonical Package Includes Kaggle-Ready Manifest
Include both:
1. `manifest/spatial_split_manifest.json` (canonical source manifest with full provenance)
2. `manifest/spatial_split_manifest_relative.json` (where paths are relative strings: `images/Oil/00000.tif` and `masks/Mask_oil/00000.tif`)
When loaded, the runner simply prefixes `dataset_root`.

---

## 5. Decision & Next Steps for Gate 4.2 / Gate 5

1. **Gate 4.1 Packaging**: Package the canonical structure `<dataset-root>/images/Oil/` and `<dataset-root>/masks/Mask_oil/` so that regardless of whether Option A, B, or C is used, the relative path from dataset root is universally:
   - Image: `images/Oil/{stem}.tif`
   - Mask: `masks/Mask_oil/{stem}.tif`
2. **Kaggle Execution**: The Kaggle runner will use Option B (zero-code-change in-memory rebasing) or Option A, ensuring 100% compatibility with `/kaggle/input/ocean-sentinel-trujillo-corpus/`.
