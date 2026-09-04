# SAR Preprocessing & Scientific Data Pipeline (Phase 1C.1)

## 1. Overview & Purpose

The SAR preprocessing subsystem (`ocean_sentinel.processing`) transforms validated Sentinel-1 GeoTIFF rasters returned by the satellite retrieval layer (`ImageryResult`) into standardized, deterministic, and analysis-ready numerical arrays (`PreprocessingResult`).

This layer forms the scientific foundation for:
1. Baseline oil-spill candidate detection (Phase 1C.2)
2. Future ML model training and inference
3. Multi-temporal SAR change detection
4. Geospatial intelligence visualization
5. Rigorous radiometric evaluation

---

## 2. Pipeline Architecture

```
Copernicus Sentinel Hub Process API
       ↓
ImageryResult (validated GeoTIFF bytes + spatial metadata)
       ↓
SARPreprocessor.process(imagery, config)
       ↓
Raster Decoding (rasterio.io.MemoryFile)
       ↓
Band Identification & Polarization Mapping
  - Band 1 = VV
  - Band 2 = VH
       ↓
Invalid Pixel Detection & Masking
  - Non-positive (x <= 0)
  - NaN / +Inf / -Inf
       ↓
Physical Radiometric Conversion (Linear → Decibels)
  σ0_dB = 10 * log10(max(x, threshold))
  Invalid pixels clamped to db_floor (default: -50 dB)
       ↓
Independent Per-Band Normalization
  - Percentile / MinMax / Z-Score
  - Preserves physical arrays separately from normalized arrays
       ↓
Quality & Scientific Statistical Metrics
       ↓
PreprocessingResult (PreprocessedSAR)
  - Full geospatial metadata preserved (CRS, bounds, transform, dimensions)
  - to_multichannel_array() for ML/detector ingestion
```

---

## 3. Scientific Radiometric Foundations

### Linear Radar Backscatter ($\sigma^0_{\text{linear}}$)
In Copernicus Sentinel Hub Process API, requests specifying `backCoeff: "SIGMA0_ELLIPSOID"` and `sampleType: "FLOAT32"` produce **linear backscatter intensity (power)** $\sigma^0$.
These values represent unitless radar cross-section per unit surface area:
- For calm ocean surfaces, typical linear values range between $0.001$ and $0.1$.
- For land or bright maritime targets (ships, platforms), linear values frequently exceed $1.0$.

### Decibel (dB) Conversion
Because radar backscatter spans several orders of magnitude, analysis is performed in logarithmic decibels:
$$\sigma^0_{\text{dB}} = 10 \cdot \log_{10}(\sigma^0_{\text{linear}})$$

The decibel transformation converts multiplicative speckle noise into additive noise, compresses dynamic range, and enhances the contrast between dark formations (oil slicks, which dampen surface capillary waves: $\sim -25\text{ dB}$ to $-18\text{ dB}$) and surrounding ambient sea ($\sim -15\text{ dB}$ to $-10\text{ dB}$).

---

## 4. Invalid Pixel Policy

Raw satellite rasters often contain zero or non-positive values along image edges, no-data boundaries, or masked sensor areas. In linear power, values $\le 0$ are scientifically non-physical.

1. **Identification**:
   A pixel is marked invalid if:
   - $x \le 0$
   - $x$ is `NaN`
   - $x$ is $+\infty$ or $-\infty$
2. **Validity Mask**:
   A 2D boolean array `valid_mask` (`bool`, same shape `(H, W)`) is generated where `True` marks genuine physical observations.
3. **Clamping Floor**:
   To ensure that numerical arrays passed downstream remain strictly finite (no $-\infty$, $+\infty$, or NaN), invalid pixels in the dB representation are substituted with a configurable floor:
   $$\text{default } \text{db\_floor} = -50.0\text{ dB}$$
   Downstream models can safely compute convolutions or statistics while using `valid_mask` to exclude substituted floor values.
4. **All-Invalid Protection**:
   If a raster band contains zero valid pixels, `SARPreprocessor` raises a `PreprocessingError` rather than emitting meaningless synthetic results.

---

## 5. Independent Per-Band Normalization

Normalization is performed **strictly for ML and visualization** and is stored separately from physical physical dB and linear arrays.

### Polarization Independence
VV and VH channels have fundamentally different physical scattering mechanisms and magnitudes:
- **VV**: Directly sensitive to sea surface roughness and capillary waves; typically $\sim -12\text{ dB}$ on open water.
- **VH**: Cross-polarized signal sensitive to volumetric/depolarizing scattering; typically $8\text{ to }12\text{ dB}$ weaker than VV, closer to instrument noise.

Normalizing VV and VH jointly would crush the VH channel into near-zero values. Therefore, normalization is calculated **independently per band**.

### Normalization Methods
1. **`PERCENTILE`** (Default):
   Scales valid pixels between configurable percentiles (default: 1st and 99th) to $[0.0, 1.0]$, clipping extreme outlier spikes (such as ships or land):
   $$x_{\text{norm}} = \text{clip}\left(\frac{x - p_{\text{min}}}{p_{\text{max}} - p_{\text{min}}}, 0.0, 1.0\right)$$
2. **`MINMAX`**:
   Scales between the exact minimum and maximum valid values to $[0.0, 1.0]$.
3. **`ZSCORE`**:
   Standardizes valid pixels to zero mean and unit variance:
   $$x_{\text{norm}} = \frac{x - \mu}{\sigma}$$
4. **`NONE`**:
   Disables normalization; `normalized_data` remains `None`.

---

## 6. Data Contract & Domain Models

### `PreprocessingConfig`
| Field | Type | Default | Description |
|---|---|---|---|
| `convert_to_db` | `bool` | `True` | Whether to convert linear $\sigma^0$ to decibels |
| `db_floor` | `float` | `-50.0` | dB value applied to invalid / non-positive pixels |
| `linear_min_threshold` | `float` | `1e-6` | Minimum linear floor to prevent $\log_{10}(0)$ |
| `preserve_linear` | `bool` | `True` | Retain original linear $\sigma^0$ array in memory |
| `normalization_method` | `NormalizationMethod` | `PERCENTILE` | Normalization algorithm |
| `percentile_min` | `float` | `1.0` | Lower percentile for percentile normalization |
| `percentile_max` | `float` | `99.0` | Upper percentile for percentile normalization |
| `clip_normalized` | `bool` | `True` | Clip normalized output to $[0.0, 1.0]$ |

### `PreprocessedBand`
- `polarization`: `Polarization` (e.g. `VV`, `VH`)
- `valid_mask`: 2D `np.ndarray` of dtype `bool` (`True` = valid)
- `db_data`: 2D `np.ndarray` of dtype `float32` (dB values with floor substitution)
- `linear_data`: 2D `np.ndarray` of dtype `float32` (original linear $\sigma^0$)
- `normalized_data`: Optional 2D `np.ndarray` of dtype `float32`
- `quality`: `QualityMetrics` (`total_pixels`, `valid_pixels`, `invalid_pixels`, `valid_percentage`)
- `db_stats`: `PreprocessedBandStats` (`min`, `max`, `mean`, `median`, `std`)
- `linear_stats`: `PreprocessedBandStats` over valid pixels
- `normalization_metadata`: Parameters used for normalization (e.g. $p_{\text{min}}, p_{\text{max}}$)

### `PreprocessingResult` (alias `PreprocessedSAR`)
Encapsulates all bands and preserves complete geospatial provenance:
- `observation_id`, `width`, `height`, `band_count`, `polarizations`, `crs`, `bounds`, `transform`
- `bands: dict[Polarization, PreprocessedBand]`
- Utility methods:
  - `get_band(pol) -> PreprocessedBand`
  - `get_db(pol) -> np.ndarray`
  - `get_linear(pol) -> np.ndarray`
  - `get_valid_mask(pol) -> np.ndarray`
  - `get_normalized(pol) -> np.ndarray`
  - `to_multichannel_array(kind='db' | 'linear' | 'normalized') -> np.ndarray` (shape: `(C, H, W)`)
  - `to_safe_summary() -> dict`

---

## 7. Example Usage

```python
from ocean_sentinel.processing import (
    SARPreprocessor,
    PreprocessingConfig,
    NormalizationMethod,
)
from ocean_sentinel.models import Polarization

# Configure preprocessor
config = PreprocessingConfig(
    convert_to_db=True,
    db_floor=-50.0,
    normalization_method=NormalizationMethod.PERCENTILE,
    percentile_min=1.0,
    percentile_max=99.0,
)
preprocessor = SARPreprocessor(default_config=config)

# Process validated ImageryResult from retrieval layer
result = preprocessor.process(imagery_result)

# Access physical dB array
vv_db = result.get_db(Polarization.VV)
vv_mask = result.get_valid_mask(Polarization.VV)

# Access normalized array for visualization or ML
vv_norm = result.get_normalized(Polarization.VV)

# Export stacked tensor for downstream detector (Phase 1C.2)
# Shape: (2, height, width) where index 0 is VV and index 1 is VH
tensor_db = result.to_multichannel_array(kind="db")
```

---

## 8. Verification & Test Procedure

### Automated Unit Tests
```bash
pytest tests/test_preprocessing.py -v
```

### Live Real Data Verification
```bash
python scripts/verify_preprocessing.py
```
Outputs complete radiometric, statistical, and geospatial verification against real Sentinel-1 acquisitions.
