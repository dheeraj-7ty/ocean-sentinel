# ADR 004: Spatially Defensible Dataset Partition for Model Evaluation

**Status**: ACCEPTED  
**Date**: September 2026  
**Author**: Implementation Engineer (under CAO Architectural Authority)  
**Deciders**: Chief Architect Officer (CAO), Implementation Engineer  
**Context**: Phase 2.4 Spatially Defensible Dataset Partition  

---

## 1. Context and Problem Statement

During Phase 2.3, an extensive spatial and scene-level audit (`scripts/audit_spatial_leakage.py`, `data/metadata/trujillo_2024/spatial_leakage_report.json`) was executed across all 1,200 parent patches of the Trujillo Part I dataset against the Phase 2.1 group-based partition (`split_manifest.json`).

While Phase 2.1 successfully guaranteed that no single parent patch stem had its 16 constituent tiles split across train, val, and test, the spatial audit revealed severe cross-split geographic leakage:
- **4,496 cross-split overlapping parent patch pairs** with positive-area footprint intersection ($A_{\text{inter}} > 0$).
- **3,548 cross-split pairs with $\ge 10\%$ area overlap** of the smaller patch.
- **1,234 cross-split pairs with $\ge 50\%$ area overlap** of the smaller patch.
- **2 duplicate geotransform pairs crossing split boundaries** (identical physical bounding boxes assigned to different splits).
- **Severe geographic proximity leakage**: validation patches were as close as $73.6\text{ m}$ to training patches (66 validation patches $< 5\text{ km}$ from training data); test patches had $0.0\text{ km}$ minimum separation (63 test patches $< 5\text{ km}$ from training data).

In Earth observation SAR segmentation, training on imagery that spatially overlaps or directly neighbors evaluation imagery introduces extreme spatial autocorrelation leakage. Under these conditions, validation metrics measure memorization of local surface roughness and sea-clutter artifacts rather than generalized oil slick detection. 

While the Phase 2.1 split was acceptable for engineering verification and hardware benchmarking (EXP-00), it is scientifically invalid as the primary evaluation split for EXP-01 model training.

---

## 2. Decision Drivers

1. **Zero Spatial Overlap**: All positive-area intersections ($A_{\text{inter}} > 0$) between patch footprints across different splits must be eliminated.
2. **Indivisible Connected Components**: Any two patches that share overlapping footprints belong to the same connected component. Connected components must be assigned as monolithic, indivisible units to a single split.
3. **Parent Exclusivity & Tile Inheritance**: All 16 tiles of each parent patch must belong exclusively to that patch's assigned partition.
4. **Target Ratio Preservation**: The target partition should approximate $70\%$ train, $15\%$ val, and $15\%$ test as closely as feasible without violating component indivisibility.
5. **Deterministic Reproducibility**: The partitioning algorithm must be fully deterministic and produce bitwise-identical results across operating systems and runs given a fixed random seed (`seed=42`).
6. **Provenance & Legacy Preservation**: The existing `data/metadata/trujillo_2024/split_manifest.json` must remain completely untouched to preserve historical reproducibility of Phase 2.1 and EXP-00.
7. **Independent Audit Requirement**: Partition certification cannot rely solely on the generator script; an independent post-generation verification directly against raw GeoTIFF metadata on disk must certify zero leakage.

---

## 3. Considered Options

### Option A: Grid-Based Spatial Block Partitioning (e.g., $1^\circ \times 1^\circ$ geographic tiles)
- **Concept**: Divide the globe into regular latitude/longitude blocks and assign blocks to splits.
- **Flaws**: Patches lying on block boundaries would have partial footprint intersections across splits unless complex buffer margins were introduced, dropping significant data.

### Option B: K-Means Spatial Clustering on Patch Centroids
- **Concept**: Cluster centroids and assign clusters to splits.
- **Flaws**: Centroid distance does not account for rectangular footprint geometry. Two patches can have distant centroids while their bounding boxes overlap.

### Option C: Graph Connected Component Partitioning on Exact Raster Footprints (Chosen)
- **Concept**: 
  1. Extract exact bounding boxes $[W, S, E, N]$ in EPSG:4326 for all 1,200 rasters.
  2. Construct an undirected overlap graph $G = (V, E)$ where $V$ is the set of 1,200 patch stems, and an edge $(u, v) \in E$ exists if and only if the intersection area of their bounding polygons is strictly positive ($A_{\text{inter}} > 0$).
  3. Compute connected components of $G$. Each connected component is an indivisible equivalence class of spatial overlap.
  4. Balance connected components across splits using a deterministic capacity-aware bin-packing algorithm.

---

## 4. Geometric Proof and Connected Component Structure

All 1,200 Trujillo Part I rasters have geotransforms with zero rotation/shear ($b = 0, d = 0$ in the GDAL 6-parameter affine transform) and positive pixel resolutions ($\Delta x \approx 0.0001078^\circ, \Delta y \approx -0.0001078^\circ$). Therefore, every raster footprint is a north-up axis-aligned rectangle in EPSG:4326 coordinates. The bounding box $[left, bottom, right, top]$ represents the exact raster polygon.

Analysis of the Trujillo Part I geometry reveals:
- Total parent patches: $1,200$.
- Total connected components: $204$.
- Component size distribution:
  - Top 10 largest components: $114, 113, 47, 35, 34, 33, 29, 29, 28, 26$ patches.
  - Intermediate components: 128 components between $2$ and $25$ patches.
  - Isolated singletons: $66$ patches with zero overlap with any other patch in the archive.
- Total unique geotransforms: $1,198$ (only 2 pairs of duplicate geotransforms exist: `['00007', '01339']` and `['00356', '00357']`).

Because the largest component contains only 114 patches ($9.5\%$ of the dataset) and there are 66 singletons, bin-packing components into target capacities of $840$ train ($70.0\%$), $180$ val ($15.0\%$), and $180$ test ($15.0\%$) is mathematically feasible with zero slack.

---

## 5. Algorithmic Implementation (`SpatialGroupSplitter`)

1. **Overlap Graph Construction**:
   Bounding box rejection filter followed by polygon intersection ($A_{\text{inter}} > 0$).
2. **Canonical Sorting**:
   Stems within each component are sorted lexicographically. Components are sorted deterministically: first by descending size ($|C|$), then by the lexicographically smallest stem in the component.
3. **Capacity-Aware Greedy Assignment**:
   A deterministic PRNG (`Random(seed=42)`) assigns components largest-first to eligible target splits whose remaining capacity can accommodate the entire component.
4. **Resulting Partition**:
   - **TRAIN**: 140 components, **840 parent patches (70.0%)**, **13,440 tiles**.
   - **VAL**: 32 components, **180 parent patches (15.0%)**, **2,880 tiles**.
   - **TEST**: 32 components, **180 parent patches (15.0%)**, **2,880 tiles**.
   - **TOTAL**: 204 components, **1,200 parent patches (100.0%)**, **19,200 tiles**.

---

## 6. Verification and Certified Results

An independent post-generation audit script reloaded all 1,200 raw GeoTIFF headers from disk and recomputed all pairwise intersections from scratch. The results confirm:

| Metric | Legacy Split (`split_manifest.json`) | Spatial Split (`spatial_split_manifest.json`) | Status |
| :--- | :--- | :--- | :--- |
| **Cross-split positive-area overlaps** | 4,496 pairs | **0 pairs** | **ELIMINATED** |
| **Cross-split overlaps $\ge 10\%$** | 3,548 pairs | **0 pairs** | **ELIMINATED** |
| **Cross-split overlaps $\ge 50\%$** | 1,234 pairs | **0 pairs** | **ELIMINATED** |
| **Identical geotransforms crossing splits** | 2 pairs | **0 pairs** | **ELIMINATED** |
| **Connected components split across splits** | Unknown / Uncontrolled | **0 of 204 (100% contained)** | **CERTIFIED** |
| **Parents changed split vs legacy** | Baseline | **577 / 1,200 (48.1%)** | **MEASURED** |
| **Val-to-Train Minimum Distance** | $0.07\text{ km}$ ($66 < 5\text{ km}$) | **$18.39\text{ km}$ ($0 < 5\text{ km}$)** | **SAFEGUARDED** |
| **Test-to-Train Minimum Distance** | $0.00\text{ km}$ ($63 < 5\text{ km}$) | **$14.97\text{ km}$ ($0 < 5\text{ km}$)** | **SAFEGUARDED** |
| **Val-to-Train Median Distance** | $13.56\text{ km}$ | **$52.11\text{ km}$** | **MEASURED** |
| **Test-to-Train Median Distance** | $14.12\text{ km}$ | **$67.70\text{ km}$** | **MEASURED** |

Both pairs of identical geotransforms are cleanly contained within single partitions:
- `['00007', '01339']` $\to$ `train`
- `['00356', '00357']` $\to$ `test`

### Recomputed Training-Only Normalization Statistics
Computed across all 840 spatial training patches ($3,523,215,360$ valid pixels per channel) using parallel Welford aggregation:
- **Channel 0**: $\mu = -33.2331369895\text{ dB}$, $\sigma = 6.4899856660\text{ dB}$
- **Channel 1**: $\mu = -19.9412158528\text{ dB}$, $\sigma = 4.5313456848\text{ dB}$

---

## 7. Residual Scientific Limitations

1. **Unresolved Acquisition Timestamps & Scene IDs**:
   Because the author Zenodo archive stripped all Sentinel-1 product IDs and acquisition timestamps from GeoTIFF tags and metadata, temporal proximity cannot be directly computed from headers. While all spatial overlaps have been $100\%$ eliminated, multi-temporal acquisitions over disjoint ocean locations remain a natural feature of SAR surveillance.
2. **Marine Basin Spatial Autocorrelation**:
   While minimum separation is guaranteed ($>14.9\text{ km}$), regional clusters (Mediterranean, Gulf of Mexico, North Sea) are distributed proportionally across train, val, and test to ensure representative maritime coverage.

---

## 8. Consequences

- `data/metadata/trujillo_2024/spatial_split_manifest.json` is established as the canonical evaluation split for EXP-01 and future model benchmarking.
- `data/metadata/trujillo_2024/split_manifest.json` is retained without modification for historical reproducibility.
- `TrujilloTileDataset` seamlessly accepts either manifest via its `manifest_path` parameter.
- EXP-01 model training can proceed on a spatially certified, leakage-free foundation upon CAO authorization.
