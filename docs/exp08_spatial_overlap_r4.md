# EXP-08 Spatial Footprint Overlap — Phase 11-R4
# docs/exp08_spatial_overlap_r4.md

**Document Version**: 1.0  
**Task**: OCEAN-SENTINEL-PHASE11-R4-EXP08-PREREQUISITE-CLOSURE  
**Stage**: STAGE_4 — Spatial Footprint Overlap Recomputation  
**Date**: 2026-09-27  
**Supersedes**: Prior "2,468 / 3,047" result (invalid denominator: 5,515 annotation records)

---

## 1. Objective

Recompute the spatial relationship between DARTIS patch footprints and Trujillo Part I raster footprints using **correct, consistent entity denominators** and **actual polygon intersection** (not geographic basin labels).

---

## 2. Methodology

### 2.1 Population Definitions

| Population | Count | Entity | Source |
|---|---|---|---|
| DARTIS no-oil patches | **2,290** | Unique jpg_file per patch (nc + nw subsets) | `data_matrix.tab` |
| DARTIS oil patches | **1,365** | Unique jpg_file per patch (oc + ow subsets) | `data_matrix.tab` |
| Trujillo Oil footprints | **1,200** | Individual GeoTIFF raster extents | `data/raw/trujillo_2024/images/Oil/` |

> [!IMPORTANT]
> The prior result used 5,515 annotation records as denominator. This was **incorrect**: 5,515 counts oil annotation objects (multiple per patch); it does not count unique patches. The corrected denominators are 2,290 (no-oil) and 1,365 (oil).

### 2.2 Geometry Construction

- **DARTIS patch polygons**: Constructed from 4 explicit corner coordinates per row: `patch_ul`, `patch_ur`, `patch_br`, `patch_bl` (longitude, latitude pairs, WGS84)
- **Trujillo footprint polygons**: Constructed from rasterio `bounds` (left, bottom, right, top) as axis-aligned boxes
- **CRS**: Both datasets in EPSG:4326 (WGS84 geographic coordinates)
- **Intersection library**: Shapely 2.x with STRtree spatial index for efficiency

### 2.3 Validation Checks Applied

- Oil patches deduplicated by jpg_file (multiple annotation rows per patch → one polygon per patch)
- No-oil patches: one row per patch → no deduplication needed
- Shapely `buffer(0)` applied to fix any invalid polygon topologies

---

## 3. Results

### 3.1 No-Oil Patches vs Trujillo Oil Footprints

| Metric | Value |
|---|---|
| Total no-oil DARTIS patches | 2,290 |
| Patches with ANY Trujillo footprint intersection | **789 (34.5%)** |
| Patches with NO Trujillo footprint intersection | **1,501 (65.5%)** |

### 3.2 Oil Patches vs Trujillo Oil Footprints

| Metric | Value |
|---|---|
| Total oil DARTIS patches | 1,365 |
| Patches with ANY Trujillo footprint intersection | **712 (52.2%)** |
| Patches with NO Trujillo footprint intersection | **653 (47.8%)** |

### 3.3 Comparison with Prior Result

| Result | Denominator | Oil intersects | Source |
|---|---|---|---|
| Prior (EXTERNAL_VALIDATION_READINESS.md) | 5,515 (INVALID — annotation rows) | 2,468 / 3,047 | Superseded |
| **R4 No-oil** | **2,290 (CORRECT — unique patches)** | **789 (34.5%)** | **This document** |
| **R4 Oil** | **1,365 (CORRECT — unique patches)** | **712 (52.2%)** | **This document** |

**The prior result is entirely superseded.** The prior "3,047 zero-overlap" count mixed oil objects as denominator.

---

## 4. Scientific Interpretation

> [!WARNING]
> **Polygon intersection ≠ statistical dependence.**  
> **Geographic co-location ≠ acquisition-level overlap.**  
> **Raster footprint overlap ≠ shared training examples.**

### 4.1 What Intersection Means

34.5% of DARTIS no-oil patches (789 of 2,290) and 52.2% of DARTIS oil patches (712 of 1,365) have their geographic footprint intersecting with at least one Trujillo Part I Oil raster footprint.

This means these DARTIS patches are drawn from geographic regions where Trujillo also collected source imagery.

### 4.2 What Intersection Does NOT Mean

1. **Not acquisition overlap**: DARTIS covers 2019 only; Trujillo Part I acquisition chronology is not fully established from current accessible artifacts (acquisition timestamps are absent from raster metadata). Acquisition-level identity cannot be established from current Trujillo artifacts.

2. **Not pixel-level identity**: Spatial footprint overlap means the geographic regions overlap, not that individual pixels are identical.

3. **Not statistical contamination**: Whether geographic region overlap introduces statistical dependence (contamination) depends on whether the same ocean state, environmental conditions, or labeling patterns are shared — this requires scene-level analysis not achievable from footprints alone.

4. **Absence of Footprint Intersection ≠ Proven Statistical Independence**: The 65.5% of no-oil patches with no Trujillo overlap (1,501 patches) represent samples with zero Trujillo footprint intersection under the defined rotated quadrilateral vs raster extent geometry. These form a spatially non-overlapping stratum. While these samples avoid direct geographic co-location with Trujillo Part I source rasters, this represents an absence of geographic footprint intersection rather than proven statistical independence.

### 4.3 Implications for EXP-08

- **789 no-oil DARTIS patches (34.5%)** have rotated quadrilateral footprints that geometrically intersect Trujillo Part I source raster extents (441 intersect actual EXP-06 training footprints). These patches may have correlated labeling conditions (same ocean region), introducing potential geographic bias.
- **1,501 no-oil patches (65.5%)** have zero geometric intersection with inspected Trujillo Part I source raster footprints under the defined rotated quadrilateral vs raster extent geometry (1,849 have zero intersection with actual EXP-06 training footprints). These form a spatially non-overlapping stratum and are evaluated as a separate stratum, but absence of footprint intersection does NOT imply proven statistical independence.
- **Oil patch overlap**: 712 of 1,365 oil patches (52.2%) geometrically intersect Trujillo Part I source footprints (399 intersect training footprints), while 653 patches (47.8%) have zero footprint intersection under the stated geometry (966 zero intersection with training footprints).
- **No statistical independence claim can be made or rejected from these numbers alone.** The geographic overlap is a risk factor to document, not a proven source of contamination.

---

## 5. Machine-Readable Output

Results saved to: `data/metadata/exp08_spatial_overlap_r4.json`

```json
{
  "nooil_result": {
    "total_patches": 2290,
    "overlap_with_trujillo": 789,
    "no_overlap_with_trujillo": 1501,
    "overlap_pct": 34.5
  },
  "oil_result": {
    "total_patches": 1365,
    "overlap_with_trujillo": 712,
    "no_overlap_with_trujillo": 653,
    "overlap_pct": 52.2
  }
}
```

---

*End of Spatial Footprint Overlap Report*
