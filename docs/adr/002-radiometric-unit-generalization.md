# ADR-002: Explicit Radiometric-Unit Aware SAR Preprocessing

**Status:** Accepted  
**Date:** 2026-09-05  
**Decider:** CAO

## Decision

Make the SAR preprocessing pipeline (`SARPreprocessor` and `PreprocessingConfig`) explicitly radiometric-unit aware via the `BackscatterUnit` enumeration (`LINEAR` vs `DECIBEL`). The caller must authoritatively declare the input unit; the preprocessor will **never** infer radiometric units heuristically from numeric signs, dynamic ranges, filenames, or dataset names.

## Context

Ocean Sentinel ingests SAR imagery from two fundamentally different sources:
1. **Live Copernicus Data Space Ecosystem (CDSE) Sentinel Hub Process API**:
   Returns calibrated **linear backscatter intensity (power)** $\sigma^0_{\text{linear}}$ in `FLOAT32` GeoTIFFs (typical ocean water values: $0.001$ to $0.15$). Analysis requires logarithmic conversion:
   $$\sigma^0_{\text{dB}} = 10 \cdot \log_{10}(\sigma^0_{\text{linear}})$$
2. **Offline Training Datasets (e.g. Trujillo-Acatitla et al., 2024)**:
   Returns rasters whose pixel values are **already calibrated in decibels (dB)** (typical ocean water values: $-30\text{ dB}$ to $-5\text{ dB}$).

### The Critical Hazard
In the initial Phase 1C.1 pipeline, the validity mask was defined as:
```python
valid_mask = np.isfinite(raw_arr) & (raw_arr > 0.0)
```
For linear power, non-positive values are non-physical. However, in decibels, normal ocean backscatter is strictly negative (e.g. $-20\text{ dB}$). If pre-calibrated dB imagery were passed to the initial pipeline:
1. All valid ocean observations would evaluate `raw > 0` as `False`, marking 100% of pixels invalid and triggering `PreprocessingError: zero valid pixels`.
2. Even worse, if bypassed, applying $10 \log_{10}(\text{negative dB})$ would produce mathematical `NaN`, corrupting training data and downstream model weights.

## Alternatives Considered

### 1. Heuristic Auto-Detection (e.g. `raw < 0` $\implies$ dB)
- **Rejected**: Scientifically dangerous. Linear backscatter can occasionally be corrupted or masked with negative no-data sentinels, while decibel imagery over high-reflectance targets (ships, corner reflectors, urban coastal areas) frequently has positive dB values ($> 0\text{ dB}$). Heuristic unit inference introduces silent catastrophic failure modes.

### 2. File-based or Path-based Detection
- **Rejected**: Brittle and tightly coupled to directory structure. Rasters loaded in-memory from buffers, object stores, or synthetic test generators lack filenames.

### 3. Separate Pipeline Classes (e.g. `LinearSARPreprocessor` vs `DecibelSARPreprocessor`)
- **Rejected**: Violates DRY and complicates pipeline composition. Both sources require identical band mapping (VV/VH), identical quality metrics, identical spatial provenance preservation, and converge on the exact same physical dB domain before entering per-band normalization (Percentile/MinMax/ZScore).

### 4. Authoritative Configuration Flag via `BackscatterUnit` (Selected)
- **Adopted**: Add `input_unit: BackscatterUnit` (`LINEAR` default, `DECIBEL` opt-in) to `PreprocessingConfig`.

## Decision Rationale

An explicit configuration contract ensures:
- **100% Determinism**: Zero ambiguity regarding data semantics.
- **Scientific Safety**: Prevents the catastrophic double log-conversion hazard ($10 \log_{10}(\text{dB})$).
- **Backward Compatibility**: `input_unit` defaults to `BackscatterUnit.LINEAR`, preserving existing live CDSE Process API behavior without breaking any existing callers.
- **Unified Downstream Contract**: Both linear and decibel inputs converge onto physical `db_data` before independent per-band normalization, producing identical model-ready $[0, 1]$ tensors.

## Consequences

### Positive
- Safely processes live CDSE imagery and offline Trujillo training datasets in the same unified pipeline.
- Negative dB ocean water pixels are recognized as valid observations.
- Optional dB $\to$ linear reconstruction is supported via explicit, opt-in `derive_linear=True` ($\sigma^0_{\text{linear}} = 10^{\sigma^0_{\text{dB}} / 10}$).
- Invalid pixels (NaN, $\pm\infty$) in both domains are deterministically masked and substituted with `db_floor`.

### Constraints
- Callers ingesting pre-calibrated dB data must explicitly set `input_unit=BackscatterUnit.DECIBEL` (or `"dB"`, `"decibel"`).
- Attempting to derive linear from dB without enabling `derive_linear=True` leaves `linear_data=None`, and calling `get_linear()` raises an explicit `ValueError`.
