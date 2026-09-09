# SAR Preprocessing & Scientific Data Pipeline (Phase 1C.1 & Phase 1C.3)

## 1. Overview & Purpose

The SAR preprocessing subsystem (`ocean_sentinel.processing`) transforms Sentinel-1 radar rasters returned by the satellite retrieval layer (`ImageryResult`) or loaded from offline training datasets into standardized, deterministic, and analysis-ready numerical representations (`PreprocessingResult`).

This layer forms the scientific foundation for:
1. Baseline oil-spill candidate detection (Phase 1C.2)
2. Radiometrically generalized offline training ingestion (Phase 1C.3 & Phase 1C.4)
3. Multi-temporal SAR change detection
4. Geospatial intelligence visualization
5. Rigorous radiometric evaluation

---

## 2. Radiometric Unit Architecture (Phase 1C.3 Generalization)

SAR observations originate from multiple sources with fundamentally different radiometric scales:

```
[Live CDSE Process API]                  [Offline Trujillo Part I]
Linear Radar Cross-Section (σ0)          Reported Backscatter in Decibels (dB)
     (typical: 0.001 to 0.2)                  (typical: -30 dB to -5 dB)
             │                                        │
             ▼                                        ▼
   input_unit = LINEAR                      input_unit = DECIBEL
             │                                        │
             ├───────────────────┬────────────────────┤
             ▼                                        ▼
   [LINEAR Validity Mask]                   [DECIBEL Validity Mask]
   valid = finite & (raw > 0)               valid = finite (negative, 0, positive)
             │                                        │
             ▼                                        ▼
   [Physical Conversion]                    [Direct dB Preservation]
   σ0_dB = 10 * log10(max(x, ε))            σ0_dB = raw (NO logarithm applied)
             │                                        │
             ├───────────────────┬────────────────────┤
             ▼                                        ▼
    [db_data Converged]                      [db_data Converged]
    Physical Decibels (float32)              Physical Decibels (float32)
             │                                        │
             ▼                                        ▼
   [Independent Per-Band Normalization]     [Independent Per-Band Normalization]
   Percentile / MinMax / ZScore             Percentile / MinMax / ZScore
             │                                        │
             └───────────────────┬────────────────────┘
                                 ▼
                     PreprocessingResult / ML Tensor
```

### Supported Radiometric Units

| Unit Enum | String Aliases | Physical Meaning | Typical Marine Range |
|---|---|---|---|
| `BackscatterUnit.LINEAR` | `"linear"`, `"lin"` | Radar cross section per unit area $\sigma^0$ (power intensity ratio) | $0.001$ to $0.15$ |
| `BackscatterUnit.DECIBEL` | `"dB"`, `"db"`, `"decibel"` | Logarithmic backscatter scale $10 \log_{10}(\sigma^0)$ | $-30\text{ dB}$ to $-5\text{ dB}$ |

> [!CAUTION]
> **CRITICAL SCIENTIFIC SAFETY: THE DOUBLE-CONVERSION HAZARD**
> - The pipeline **NEVER** infers radiometric units heuristically from numeric signs, value ranges, filenames, or dataset names.
> - If decibel imagery is passed with `input_unit = LINEAR`:
>   1. All normal ocean pixels (negative dB, e.g. $-20\text{ dB}$) will fail `raw > 0.0` and be marked invalid, causing `PreprocessingError: zero valid pixels`.
>   2. If not rejected, computing $10 \log_{10}(\text{negative dB})$ produces mathematical `NaN`, irreversibly corrupting training data and downstream model weights.
> - The caller or configuration must **explicitly state** `input_unit = BackscatterUnit.DECIBEL` for pre-calibrated dB imagery.

---

## 3. Scientific Radiometric Foundations & Equations

### Linear Backscatter ($\sigma^0_{\text{linear}}$)
In Copernicus Sentinel Hub Process API requests specifying `backCoeff: "SIGMA0_ELLIPSOID"` and `sampleType: "FLOAT32"`, pixel values represent linear backscatter power $\sigma^0$:
- Calm sea surface: $0.001 \le \sigma^0_{\text{linear}} \le 0.05$
- Rough sea / ambient ocean: $0.05 \le \sigma^0_{\text{linear}} \le 0.2$
- Hard targets (ships, platforms, land): $\sigma^0_{\text{linear}} > 1.0$

### Decibel Conversion (Linear $\to$ dB)
$$\sigma^0_{\text{dB}} = 10 \cdot \log_{10}(\max(\sigma^0_{\text{linear}}, \epsilon_{\text{min}}))$$
where $\epsilon_{\text{min}}$ is `linear_min_threshold` (default: $10^{-6} \implies -60\text{ dB}$).

### Linear Derivation (dB $\to$ Linear)
When `input_unit == BackscatterUnit.DECIBEL` and the caller explicitly sets `derive_linear = True`:
$$\sigma^0_{\text{linear}} = 10^{\frac{\sigma^0_{\text{dB}}}{10}}$$

Examples:
- $0.0\text{ dB} \implies 10^{0} = 1.0$ (linear)
- $-10.0\text{ dB} \implies 10^{-1} = 0.1$ (linear)
- $-20.0\text{ dB} \implies 10^{-2} = 0.01$ (linear)
- $-30.0\text{ dB} \implies 10^{-3} = 0.001$ (linear)
- $+10.0\text{ dB} \implies 10^{1} = 10.0$ (linear)

---

## 4. Deterministic Validity & Floor Policy

| Check | `BackscatterUnit.LINEAR` | `BackscatterUnit.DECIBEL` |
|---|---|---|
| **Positive finite values ($x > 0$)** | **Valid** | **Valid** |
| **Negative finite values ($x < 0$)** | **Invalid** (physically non-existent power) | **Valid** (standard ocean backscatter, e.g. $-20\text{ dB}$) |
| **Zero ($x = 0.0$)** | **Invalid** (no-data / antenna boundary) | **Valid** ($0\text{ dB} \equiv 1.0$ linear) |
| **`NaN` / $+\infty$ / $-\infty$** | **Invalid** | **Invalid** |
| **`db_floor` substitution** | Substituted for $x \le 0$, `NaN`, $\pm\infty$ | Substituted for `NaN`, $\pm\infty$ only; **never** clips valid dB values |
| **All-invalid protection** | Raises `PreprocessingError` | Raises `PreprocessingError` |

---

## 5. Independent Per-Band Normalization

Normalization is performed **strictly for ML feature extraction and visualization**, operating on the converged physical dB domain (`db_data`) over valid pixels (`valid_mask`):

1. **`PERCENTILE`** (Default):
   Scales between 1st and 99th percentiles of valid pixels to $[0.0, 1.0]$:
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
| `input_unit` | `BackscatterUnit` | `LINEAR` | Authoritative source radiometric unit (`LINEAR` or `DECIBEL`) |
| `convert_to_db` | `bool` | `True` | Convert linear $\sigma^0$ to decibels (LINEAR input only) |
| `db_floor` | `float` | `-50.0` | dB floor applied to invalid/non-finite pixels |
| `linear_min_threshold` | `float` | `1e-6` | Threshold for linear $\sigma^0$ to avoid $\log_{10}(0)$ (LINEAR input only) |
| `preserve_linear` | `bool` | `True` | Retain original linear $\sigma^0$ array in memory (LINEAR input) |
| `derive_linear` | `bool` | `False` | Derive linear backscatter from dB via $10^{\text{dB}/10}$ (DECIBEL input only) |
| `normalization_method` | `NormalizationMethod` | `PERCENTILE` | Normalization algorithm applied per band |
| `percentile_min` | `float` | `1.0` | Lower percentile for percentile normalization |
| `percentile_max` | `float` | `99.0` | Upper percentile for percentile normalization |
| `clip_normalized` | `bool` | `True` | Clip normalized output to $[0.0, 1.0]$ |

### `PreprocessedBand`
- `polarization`: `Polarization` (`VV`, `VH`)
- `input_unit`: `BackscatterUnit` (`LINEAR`, `DECIBEL`)
- `valid_mask`: 2D `np.ndarray` of dtype `bool` (`True` = valid pixel)
- `db_data`: 2D `np.ndarray` of dtype `float32` (dB values with floor substitution on invalid pixels)
- `linear_data`: Optional 2D `np.ndarray` of dtype `float32` (`None` unless preserved or derived)
- `normalized_data`: Optional 2D `np.ndarray` of dtype `float32`
- `quality`: `QualityMetrics` (`total_pixels`, `valid_pixels`, `invalid_pixels`, `valid_percentage`)
- `db_stats`: `PreprocessedBandStats` (`min`, `max`, `mean`, `median`, `std`)
- `linear_stats`: `PreprocessedBandStats` over valid pixels (`None` if linear data not preserved/derived)
- `normalization_metadata`: Parameters used for normalization

### `PreprocessingResult` (alias `PreprocessedSAR`)
- `observation_id`, `width`, `height`, `band_count`, `polarizations`, `crs`, `bounds`, `transform`
- `bands: dict[Polarization, PreprocessedBand]`
- Utility methods:
  - `get_band(pol) -> PreprocessedBand`
  - `get_db(pol) -> np.ndarray`
  - `get_linear(pol) -> np.ndarray` (raises informative `ValueError` if not preserved/derived)
  - `get_valid_mask(pol) -> np.ndarray`
  - `get_normalized(pol) -> np.ndarray`
  - `to_multichannel_array(kind='db' | 'linear' | 'normalized') -> np.ndarray` (shape: `(C, H, W)`)
  - `to_safe_summary() -> dict`

---

## 7. Configuration & Usage Examples

### Example 1: Live Copernicus CDSE Process API Imagery (Linear Input)

```python
from ocean_sentinel.processing import (
    BackscatterUnit,
    NormalizationMethod,
    PreprocessingConfig,
    SARPreprocessor,
)
from ocean_sentinel.models import Polarization

# Live imagery returns linear sigma0
config = PreprocessingConfig(
    input_unit=BackscatterUnit.LINEAR,  # Default
    convert_to_db=True,                 # Default
    preserve_linear=True,               # Keep original linear data
    normalization_method=NormalizationMethod.PERCENTILE,
)
preprocessor = SARPreprocessor(default_config=config)

# Process ImageryResult from Copernicus retrieval layer
result = preprocessor.process(imagery_result)

vv_db = result.get_db(Polarization.VV)
vv_lin = result.get_linear(Polarization.VV)
tensor = result.to_multichannel_array(kind="db")  # Shape: (2, H, W)
```

### Example 2: Offline Trujillo Training Imagery (Decibel Input)

```python
from ocean_sentinel.processing import (
    BackscatterUnit,
    NormalizationMethod,
    PreprocessingConfig,
    SARPreprocessor,
)
from ocean_sentinel.models import Polarization

# Trujillo imagery is already in dB
config = PreprocessingConfig(
    input_unit=BackscatterUnit.DECIBEL,  # Explicitly declare dB input
    derive_linear=False,                 # Do NOT compute unnecessary linear data
    normalization_method=NormalizationMethod.PERCENTILE,
    db_floor=-50.0,                      # Applied only to NaN / inf border pixels
)
preprocessor = SARPreprocessor(default_config=config)

# Process numpy arrays decoded from Trujillo GeoTIFFs
result = preprocessor.process_arrays(
    arrays={Polarization.VV: vv_db_arr, Polarization.VH: vh_db_arr},
    polarizations=[Polarization.VV, Polarization.VH],
    observation_id="trujillo_patch_00000",
    width=2048,
    height=2048,
    crs="EPSG:4326",
    bounds=[0.0, 0.0, 1.0, 1.0],
    transform=[1.0, 0.0, 0.0, 0.0, -1.0, 1.0],
    config=config,
)

# Access dB directly (no logarithm was applied)
vv_db = result.get_db(Polarization.VV)
ml_tensor = result.to_multichannel_array(kind="normalized")  # Shape: (2, 2048, 2048)
```

---

## 8. Verification & Test Procedure

### Automated Unit Tests
```bash
venv\Scripts\pytest tests/test_preprocessing.py -v
```

### Complete Test Suite
```bash
venv\Scripts\pytest
```

