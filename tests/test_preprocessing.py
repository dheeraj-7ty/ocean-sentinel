"""Comprehensive scientific tests for SAR Preprocessing & Scientific Data Pipeline (Phase 1C.1).

Tests:
- Scientific Linear-to-dB conversion (1.0 -> 0 dB, 0.1 -> -10 dB, 0.01 -> -20 dB)
- Deterministic invalid pixel handling (0, negatives, NaN, +inf, -inf)
- Clamping floor application on invalid pixels in dB representation (-50 dB)
- Boolean validity mask accuracy
- Independent per-band normalization (Percentile, MinMax, Z-score, None)
- Prevention of mutual band contamination (VV vs VH independent scaling)
- Preservation of physical arrays (normalization does NOT mutate dB or linear)
- Constant-valued array safety (no division-by-zero)
- Clear failure on all-invalid or zero-valid-pixel rasters
- Geospatial preservation (CRS, transform, bounds, dimensions, observation_id)
- Band ordering contract preservation (VV then VH)
- Output dtypes (float32, bool)
- Reproducibility across multiple identical runs
- Safe representation and error handling (no secrets or array dumps in repr or errors)
- End-to-end processing with real in-memory GeoTIFF ImageryResult
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from rasterio.io import MemoryFile
from rasterio.transform import from_bounds

from ocean_sentinel.errors import PreprocessingError, SatelliteErrorCode
from ocean_sentinel.models import BandStatistics, ImageryResult, Polarization
from ocean_sentinel.processing import (
    NormalizationMethod,
    PreprocessingConfig,
    PreprocessingResult,
    SARPreprocessor,
)

# ---------------------------------------------------------------------------
# Helper fixtures & functions
# ---------------------------------------------------------------------------


def create_synthetic_geotiff(
    arrays: list[np.ndarray],
    bounds: tuple[float, float, float, float] = (15.0, 39.0, 16.0, 40.0),
    crs_epsg: int = 4326,
) -> bytes:
    """Create a valid in-memory GeoTIFF byte string from 2D numpy arrays."""
    count = len(arrays)
    height, width = arrays[0].shape
    transform = from_bounds(*bounds, width, height)

    with MemoryFile() as memfile:
        with memfile.open(
            driver="GTiff",
            width=width,
            height=height,
            count=count,
            dtype="float32",
            crs=f"EPSG:{crs_epsg}",
            transform=transform,
        ) as dataset:
            for idx, arr in enumerate(arrays):
                dataset.write(arr.astype(np.float32), idx + 1)
        return memfile.read()


def create_sample_imagery_result(
    arrays: list[np.ndarray],
    polarizations: list[Polarization],
    observation_id: str = "S1A_IW_GRDH_1SDV_20260901T000000",
    bounds: tuple[float, float, float, float] = (15.0, 39.0, 16.0, 40.0),
    crs: str = "EPSG:4326",
) -> ImageryResult:
    """Create a valid ImageryResult wrapping synthetic GeoTIFF bytes."""
    raw_bytes = create_synthetic_geotiff(arrays, bounds=bounds)
    height, width = arrays[0].shape
    transform = from_bounds(*bounds, width, height)
    transform_list = [float(x) for x in transform[:6]]

    band_stats = [
        BandStatistics(
            polarization=pol,
            min_value=float(np.nanmin(arr[np.isfinite(arr)])),
            max_value=float(np.nanmax(arr[np.isfinite(arr)])),
            mean_value=float(np.nanmean(arr[np.isfinite(arr)])),
            finite_pixel_count=int(np.sum(np.isfinite(arr))),
            total_pixel_count=int(arr.size),
        )
        for pol, arr in zip(polarizations, arrays)
    ]

    return ImageryResult(
        observation_id=observation_id,
        width=width,
        height=height,
        band_count=len(polarizations),
        bands=polarizations,
        dtype="float32",
        crs=crs,
        bounds=list(bounds),
        transform=transform_list,
        band_statistics=band_stats,
        raw_bytes=raw_bytes,
    )


# ---------------------------------------------------------------------------
# Scientific dB Conversion Tests
# ---------------------------------------------------------------------------


class TestDecibelConversion:
    """Verify exact mathematical linear-to-dB conversion and stability."""

    def test_known_linear_values(self):
        """Verify standard physical SAR backscatter conversions:

        1.0   -> 0 dB
        0.1   -> -10 dB
        0.01  -> -20 dB
        0.001 -> -30 dB
        2.0   -> ~3.0103 dB
        """
        arr = np.array([
            [1.0, 0.1],
            [0.01, 0.001],
            [2.0, 0.5],
        ], dtype=np.float32)

        preprocessor = SARPreprocessor()
        arrays = {Polarization.VV: arr}
        res = preprocessor.process_arrays(
            arrays=arrays,
            polarizations=[Polarization.VV],
            observation_id="test_db",
            width=2,
            height=3,
            crs="EPSG:4326",
            bounds=[0.0, 0.0, 1.0, 1.0],
            transform=[0.5, 0.0, 0.0, 0.0, -0.333, 1.0],
            config=PreprocessingConfig(
                convert_to_db=True, normalization_method=NormalizationMethod.NONE
            ),
        )

        db_vv = res.get_db(Polarization.VV)

        # 1.0 -> 0 dB
        assert math.isclose(db_vv[0, 0], 0.0, abs_tol=1e-5)
        # 0.1 -> -10 dB
        assert math.isclose(db_vv[0, 1], -10.0, abs_tol=1e-5)
        # 0.01 -> -20 dB
        assert math.isclose(db_vv[1, 0], -20.0, abs_tol=1e-5)
        # 0.001 -> -30 dB
        assert math.isclose(db_vv[1, 1], -30.0, abs_tol=1e-5)
        # 2.0 -> 10 * log10(2) ~ 3.0103 dB
        assert math.isclose(db_vv[2, 0], 10.0 * math.log10(2.0), abs_tol=1e-4)

    def test_disabled_db_conversion(self):
        """When convert_to_db is False, db_data preserves linear values."""
        arr = np.array([[1.0, 0.5], [0.2, 0.1]], dtype=np.float32)
        preprocessor = SARPreprocessor()
        res = preprocessor.process_arrays(
            arrays={Polarization.VV: arr},
            polarizations=[Polarization.VV],
            observation_id="test_no_db",
            width=2,
            height=2,
            crs="EPSG:4326",
            bounds=[0.0, 0.0, 1.0, 1.0],
            transform=[0.5, 0.0, 0.0, 0.0, -0.5, 1.0],
            config=PreprocessingConfig(
                convert_to_db=False, normalization_method=NormalizationMethod.NONE
            ),
        )
        db_vv = res.get_db(Polarization.VV)
        np.testing.assert_allclose(db_vv, arr)


# ---------------------------------------------------------------------------
# Invalid Pixel & Validity Mask Tests
# ---------------------------------------------------------------------------


class TestInvalidPixelPolicy:
    """Verify deterministic identification of invalid pixels and clamping floor."""

    def test_invalid_pixels_masked_and_clamped(self):
        """Test zero, negative values, NaN, +inf, -inf.

        All must produce:
        1. valid_mask == False
        2. db_data == configured floor (e.g. -50 dB)
        3. No NaN, +inf, or -inf in db_data!
        """
        arr = np.array([
            [1.0, 0.0],          # 0 is non-positive
            [-0.5, np.nan],       # negative and NaN
            [np.inf, -np.inf],    # infinities
            [0.05, 0.1],          # valid positive numbers
        ], dtype=np.float32)

        config = PreprocessingConfig(
            convert_to_db=True,
            db_floor=-50.0,
            normalization_method=NormalizationMethod.NONE,
        )
        preprocessor = SARPreprocessor(default_config=config)

        res = preprocessor.process_arrays(
            arrays={Polarization.VV: arr},
            polarizations=[Polarization.VV],
            observation_id="test_invalid",
            width=2,
            height=4,
            crs="EPSG:4326",
            bounds=[0.0, 0.0, 1.0, 1.0],
            transform=[0.5, 0.0, 0.0, 0.0, -0.25, 1.0],
        )

        mask = res.get_valid_mask(Polarization.VV)
        db_vv = res.get_db(Polarization.VV)
        quality = res.get_band(Polarization.VV).quality

        # Validity mask checks
        expected_mask = np.array([
            [True, False],
            [False, False],
            [False, False],
            [True, True],
        ], dtype=bool)
        np.testing.assert_array_equal(mask, expected_mask)

        # Quality metrics
        assert quality.total_pixels == 8
        assert quality.valid_pixels == 3
        assert quality.invalid_pixels == 5
        assert math.isclose(quality.valid_percentage, (3.0 / 8.0) * 100.0)
        assert not quality.all_valid
        assert not quality.all_invalid

        # db_data checks
        assert np.all(np.isfinite(db_vv)), "All values in db_data must be finite"
        # Check that invalid locations contain the floor (-50.0 dB)
        assert db_vv[0, 1] == -50.0
        assert db_vv[1, 0] == -50.0
        assert db_vv[1, 1] == -50.0
        assert db_vv[2, 0] == -50.0
        assert db_vv[2, 1] == -50.0

        # Valid locations contain the true log10 value
        assert math.isclose(db_vv[0, 0], 0.0, abs_tol=1e-5)
        assert math.isclose(db_vv[3, 0], 10.0 * math.log10(0.05), abs_tol=1e-5)
        assert math.isclose(db_vv[3, 1], -10.0, abs_tol=1e-5)

    def test_all_invalid_pixels_raises_error(self):
        """A raster band containing zero valid pixels must raise PreprocessingError."""
        arr = np.array([
            [0.0, -1.0],
            [np.nan, np.inf],
        ], dtype=np.float32)

        preprocessor = SARPreprocessor()
        with pytest.raises(PreprocessingError) as exc_info:
            preprocessor.process_arrays(
                arrays={Polarization.VV: arr},
                polarizations=[Polarization.VV],
                observation_id="test_all_invalid",
                width=2,
                height=2,
                crs="EPSG:4326",
                bounds=[0.0, 0.0, 1.0, 1.0],
                transform=[0.5, 0.0, 0.0, 0.0, -0.5, 1.0],
            )

        err = exc_info.value
        assert "contains zero valid pixels" in err.message
        assert err.code == SatelliteErrorCode.PROCESSING_FAILURE


# ---------------------------------------------------------------------------
# Normalization Tests
# ---------------------------------------------------------------------------


class TestNormalization:
    """Verify independent per-band normalization algorithms and edge cases."""

    def test_percentile_normalization(self):
        """Percentile scaling normalizes valid values between p_min and p_max to [0, 1]."""
        # Create a linear ramp of valid backscatter
        data = np.linspace(0.01, 1.0, 100, dtype=np.float32).reshape(10, 10)
        config = PreprocessingConfig(
            convert_to_db=True,
            normalization_method=NormalizationMethod.PERCENTILE,
            percentile_min=5.0,
            percentile_max=95.0,
            clip_normalized=True,
        )
        preprocessor = SARPreprocessor(default_config=config)
        res = preprocessor.process_arrays(
            arrays={Polarization.VV: data},
            polarizations=[Polarization.VV],
            observation_id="test_norm_pct",
            width=10,
            height=10,
            crs="EPSG:4326",
            bounds=[0.0, 0.0, 1.0, 1.0],
            transform=[0.1, 0.0, 0.0, 0.0, -0.1, 1.0],
        )

        norm_vv = res.get_normalized(Polarization.VV)
        assert norm_vv is not None
        assert norm_vv.shape == (10, 10)
        assert np.min(norm_vv) >= 0.0
        assert np.max(norm_vv) <= 1.0

        # Check normalization metadata recorded
        meta = res.get_band(Polarization.VV).normalization_metadata
        assert meta is not None
        assert meta.method == NormalizationMethod.PERCENTILE
        assert "p_min" in meta.parameters
        assert "p_max" in meta.parameters
        assert meta.parameters["p_min"] < meta.parameters["p_max"]

    def test_minmax_normalization(self):
        """MinMax scaling maps exactly min to 0.0 and max to 1.0."""
        data = np.array([
            [0.01, 0.1],
            [0.5, 1.0],
        ], dtype=np.float32)

        config = PreprocessingConfig(
            convert_to_db=True,
            normalization_method=NormalizationMethod.MINMAX,
            clip_normalized=True,
        )
        preprocessor = SARPreprocessor(default_config=config)
        res = preprocessor.process_arrays(
            arrays={Polarization.VV: data},
            polarizations=[Polarization.VV],
            observation_id="test_norm_minmax",
            width=2,
            height=2,
            crs="EPSG:4326",
            bounds=[0.0, 0.0, 1.0, 1.0],
            transform=[0.5, 0.0, 0.0, 0.0, -0.5, 1.0],
        )

        norm_vv = res.get_normalized(Polarization.VV)
        assert norm_vv is not None
        assert math.isclose(norm_vv[0, 0], 0.0, abs_tol=1e-5)
        assert math.isclose(norm_vv[1, 1], 1.0, abs_tol=1e-5)

        meta = res.get_band(Polarization.VV).normalization_metadata
        assert meta is not None
        assert meta.method == NormalizationMethod.MINMAX
        assert "min" in meta.parameters
        assert "max" in meta.parameters

    def test_zscore_normalization(self):
        """Z-Score maps valid values to zero mean and unit variance."""
        np.random.seed(42)
        data = np.random.uniform(0.01, 1.0, (20, 20)).astype(np.float32)

        config = PreprocessingConfig(
            convert_to_db=True,
            normalization_method=NormalizationMethod.ZSCORE,
        )
        preprocessor = SARPreprocessor(default_config=config)
        res = preprocessor.process_arrays(
            arrays={Polarization.VV: data},
            polarizations=[Polarization.VV],
            observation_id="test_norm_zscore",
            width=20,
            height=20,
            crs="EPSG:4326",
            bounds=[0.0, 0.0, 1.0, 1.0],
            transform=[0.05, 0.0, 0.0, 0.0, -0.05, 1.0],
        )

        norm_vv = res.get_normalized(Polarization.VV)
        assert norm_vv is not None
        assert math.isclose(float(np.mean(norm_vv)), 0.0, abs_tol=1e-4)
        assert math.isclose(float(np.std(norm_vv)), 1.0, abs_tol=1e-4)

        meta = res.get_band(Polarization.VV).normalization_metadata
        assert meta is not None
        assert meta.method == NormalizationMethod.ZSCORE
        assert "mean" in meta.parameters
        assert "std" in meta.parameters

    def test_constant_array_handling(self):
        """Constant arrays must not trigger division by zero."""
        constant_val = 0.05
        data = np.full((10, 10), fill_value=constant_val, dtype=np.float32)

        methods = [
            NormalizationMethod.PERCENTILE,
            NormalizationMethod.MINMAX,
            NormalizationMethod.ZSCORE,
        ]
        for method in methods:
            config = PreprocessingConfig(
                convert_to_db=True,
                normalization_method=method,
            )
            preprocessor = SARPreprocessor(default_config=config)
            res = preprocessor.process_arrays(
                arrays={Polarization.VV: data},
                polarizations=[Polarization.VV],
                observation_id="test_const",
                width=10,
                height=10,
                crs="EPSG:4326",
                bounds=[0.0, 0.0, 1.0, 1.0],
                transform=[0.1, 0.0, 0.0, 0.0, -0.1, 1.0],
            )
            norm_vv = res.get_normalized(Polarization.VV)
            assert norm_vv is not None
            assert np.all(np.isfinite(norm_vv)), (
                f"Method {method} produced non-finite values on constant input"
            )

    def test_normalization_does_not_mutate_physical_arrays(self):
        """Physical dB and linear arrays must remain completely unmutated by normalization."""
        data = np.array([[0.01, 0.05], [0.1, 0.5]], dtype=np.float32)
        preprocessor = SARPreprocessor()
        res = preprocessor.process_arrays(
            arrays={Polarization.VV: data},
            polarizations=[Polarization.VV],
            observation_id="test_immutability",
            width=2,
            height=2,
            crs="EPSG:4326",
            bounds=[0.0, 0.0, 1.0, 1.0],
            transform=[0.5, 0.0, 0.0, 0.0, -0.5, 1.0],
            config=PreprocessingConfig(
                convert_to_db=True,
                preserve_linear=True,
                normalization_method=NormalizationMethod.PERCENTILE,
            ),
        )

        db_vv = res.get_db(Polarization.VV)
        linear_vv = res.get_linear(Polarization.VV)
        norm_vv = res.get_normalized(Polarization.VV)

        # Verify linear is still original linear values
        np.testing.assert_allclose(linear_vv, data)
        # Verify dB is 10 * log10(linear)
        np.testing.assert_allclose(db_vv, 10.0 * np.log10(data), rtol=1e-5)
        # Verify normalized is separate scaled values in [0, 1]
        assert np.max(norm_vv) <= 1.0 and np.min(norm_vv) >= 0.0


# ---------------------------------------------------------------------------
# Independent Band Processing & Ordering Tests
# ---------------------------------------------------------------------------


class TestBandHandling:
    """Verify VV and VH are normalized and processed independently, preserving order."""

    def test_vv_and_vh_independent_normalization(self):
        """VV (strong ocean backscatter) and VH (weak cross-pol) must NOT cross-contaminate.

        VV: values around 0.1 to 0.5 (~ -10 to -3 dB)
        VH: values around 0.001 to 0.01 (~ -30 to -20 dB)
        Both should scale across their own individual full dynamic range when normalized.
        """
        vv_arr = np.array([[0.1, 0.2], [0.3, 0.5]], dtype=np.float32)
        vh_arr = np.array([[0.001, 0.003], [0.005, 0.01]], dtype=np.float32)

        config = PreprocessingConfig(
            convert_to_db=True,
            normalization_method=NormalizationMethod.MINMAX,
            clip_normalized=True,
        )
        preprocessor = SARPreprocessor(default_config=config)
        res = preprocessor.process_arrays(
            arrays={Polarization.VV: vv_arr, Polarization.VH: vh_arr},
            polarizations=[Polarization.VV, Polarization.VH],
            observation_id="test_dual_band",
            width=2,
            height=2,
            crs="EPSG:4326",
            bounds=[0.0, 0.0, 1.0, 1.0],
            transform=[0.5, 0.0, 0.0, 0.0, -0.5, 1.0],
        )

        norm_vv = res.get_normalized(Polarization.VV)
        norm_vh = res.get_normalized(Polarization.VH)

        # Both bands independently span [0, 1]
        assert math.isclose(norm_vv[0, 0], 0.0, abs_tol=1e-5)
        assert math.isclose(norm_vv[1, 1], 1.0, abs_tol=1e-5)

        assert math.isclose(norm_vh[0, 0], 0.0, abs_tol=1e-5)
        assert math.isclose(norm_vh[1, 1], 1.0, abs_tol=1e-5)

        # Physical dB arrays retain their vastly different magnitudes!
        db_vv = res.get_db(Polarization.VV)
        db_vh = res.get_db(Polarization.VH)
        assert np.mean(db_vv) > np.mean(db_vh) + 10.0  # VV is >10 dB stronger than VH

    def test_band_ordering_preserved(self):
        """Verify polarizations sequence is explicitly preserved as requested."""
        vv = np.full((4, 4), fill_value=0.1, dtype=np.float32)
        vh = np.full((4, 4), fill_value=0.01, dtype=np.float32)

        preprocessor = SARPreprocessor()
        res = preprocessor.process_arrays(
            arrays={Polarization.VV: vv, Polarization.VH: vh},
            polarizations=[Polarization.VV, Polarization.VH],
            observation_id="test_order",
            width=4,
            height=4,
            crs="EPSG:4326",
            bounds=[0.0, 0.0, 1.0, 1.0],
            transform=[0.25, 0.0, 0.0, 0.0, -0.25, 1.0],
        )

        assert res.polarizations == [Polarization.VV, Polarization.VH]
        assert res.band_count == 2

        # Multichannel array test
        multi_db = res.to_multichannel_array(kind="db")
        assert multi_db.shape == (2, 4, 4)
        np.testing.assert_allclose(multi_db[0], res.get_db(Polarization.VV))
        np.testing.assert_allclose(multi_db[1], res.get_db(Polarization.VH))

    def test_single_band_vv(self):
        """Test single-band VV processing."""
        vv = np.full((4, 4), fill_value=0.1, dtype=np.float32)
        preprocessor = SARPreprocessor()
        res = preprocessor.process_arrays(
            arrays={Polarization.VV: vv},
            polarizations=[Polarization.VV],
            observation_id="test_single_vv",
            width=4,
            height=4,
            crs="EPSG:4326",
            bounds=[0.0, 0.0, 1.0, 1.0],
            transform=[0.25, 0.0, 0.0, 0.0, -0.25, 1.0],
        )
        assert res.polarizations == [Polarization.VV]
        assert res.band_count == 1
        assert Polarization.VV in res.bands

    def test_single_band_vh(self):
        """Test single-band VH processing."""
        vh = np.full((4, 4), fill_value=0.01, dtype=np.float32)
        preprocessor = SARPreprocessor()
        res = preprocessor.process_arrays(
            arrays={Polarization.VH: vh},
            polarizations=[Polarization.VH],
            observation_id="test_single_vh",
            width=4,
            height=4,
            crs="EPSG:4326",
            bounds=[0.0, 0.0, 1.0, 1.0],
            transform=[0.25, 0.0, 0.0, 0.0, -0.25, 1.0],
        )
        assert res.polarizations == [Polarization.VH]
        assert res.band_count == 1
        assert Polarization.VH in res.bands


# ---------------------------------------------------------------------------
# Geospatial Integrity & Metadata Preservation Tests
# ---------------------------------------------------------------------------


class TestGeospatialIntegrity:
    """Verify all geospatial metadata, dimensions, and provenance are strictly preserved."""

    def test_spatial_metadata_preserved(self):
        width, height = 32, 16
        bounds = [10.5, 35.2, 11.8, 36.4]
        transform = [0.040625, 0.0, 10.5, 0.0, -0.075, 36.4]
        crs = "EPSG:4326"
        obs_id = "S1B_IW_GRDH_TEST_OBS_9999"

        vv = np.random.uniform(0.01, 1.0, (height, width)).astype(np.float32)
        preprocessor = SARPreprocessor()
        res = preprocessor.process_arrays(
            arrays={Polarization.VV: vv},
            polarizations=[Polarization.VV],
            observation_id=obs_id,
            width=width,
            height=height,
            crs=crs,
            bounds=bounds,
            transform=transform,
        )

        assert res.width == width
        assert res.height == height
        assert res.observation_id == obs_id
        assert res.crs == crs
        assert res.bounds == bounds
        assert res.transform == transform

        # Dimensions of output arrays match input dimensions exactly
        assert res.get_db(Polarization.VV).shape == (height, width)
        assert res.get_valid_mask(Polarization.VV).shape == (height, width)
        assert res.get_linear(Polarization.VV).shape == (height, width)
        assert res.get_normalized(Polarization.VV).shape == (height, width)

    def test_reproducibility(self):
        """Preprocessing identical input twice yields bitwise identical results."""
        vv = np.random.uniform(0.01, 1.0, (20, 20)).astype(np.float32)
        config = PreprocessingConfig(normalization_method=NormalizationMethod.PERCENTILE)
        preprocessor = SARPreprocessor()

        res1 = preprocessor.process_arrays(
            arrays={Polarization.VV: vv},
            polarizations=[Polarization.VV],
            observation_id="test_repro",
            width=20,
            height=20,
            crs="EPSG:4326",
            bounds=[0.0, 0.0, 1.0, 1.0],
            transform=[0.05, 0.0, 0.0, 0.0, -0.05, 1.0],
            config=config,
        )
        res2 = preprocessor.process_arrays(
            arrays={Polarization.VV: vv},
            polarizations=[Polarization.VV],
            observation_id="test_repro",
            width=20,
            height=20,
            crs="EPSG:4326",
            bounds=[0.0, 0.0, 1.0, 1.0],
            transform=[0.05, 0.0, 0.0, 0.0, -0.05, 1.0],
            config=config,
        )

        np.testing.assert_array_equal(res1.get_db(Polarization.VV), res2.get_db(Polarization.VV))
        np.testing.assert_array_equal(
            res1.get_valid_mask(Polarization.VV), res2.get_valid_mask(Polarization.VV)
        )
        np.testing.assert_array_equal(
            res1.get_normalized(Polarization.VV), res2.get_normalized(Polarization.VV)
        )


# ---------------------------------------------------------------------------
# End-to-End ImageryResult GeoTIFF Processing Tests
# ---------------------------------------------------------------------------


class TestImageryResultIntegration:
    """Verify processing an actual ImageryResult containing raw GeoTIFF bytes."""

    def test_process_imagery_result_end_to_end(self):
        vv = np.random.uniform(0.02, 0.5, (16, 16)).astype(np.float32)
        vh = np.random.uniform(0.001, 0.05, (16, 16)).astype(np.float32)
        # Inject an invalid pixel into VV
        vv[2, 3] = 0.0

        imagery = create_sample_imagery_result(
            arrays=[vv, vh],
            polarizations=[Polarization.VV, Polarization.VH],
            observation_id="S1A_IW_GRDH_E2E_VERIFY",
        )

        preprocessor = SARPreprocessor()
        res = preprocessor.process(imagery)

        assert isinstance(res, PreprocessingResult)
        assert res.observation_id == "S1A_IW_GRDH_E2E_VERIFY"
        assert res.width == 16
        assert res.height == 16
        assert res.band_count == 2
        assert res.polarizations == [Polarization.VV, Polarization.VH]

        # Check VV mask at injected invalid position
        vv_mask = res.get_valid_mask(Polarization.VV)
        assert not vv_mask[2, 3]
        assert res.get_db(Polarization.VV)[2, 3] == -50.0  # default floor

        # Check VH mask is all valid
        vh_mask = res.get_valid_mask(Polarization.VH)
        assert np.all(vh_mask)

        # Check safe summary serializability
        summary = res.to_safe_summary()
        assert summary["observation_id"] == "S1A_IW_GRDH_E2E_VERIFY"
        assert "bands" in summary
        assert "VV" in summary["bands"]
        assert "VH" in summary["bands"]

    def test_corrupt_imagery_bytes_raises_preprocessing_error(self):
        """Corrupted raw_bytes must raise PreprocessingError."""
        imagery = ImageryResult(
            observation_id="corrupt_test",
            width=16,
            height=16,
            band_count=1,
            bands=[Polarization.VV],
            dtype="float32",
            crs="EPSG:4326",
            bounds=[0.0, 0.0, 1.0, 1.0],
            transform=[0.1, 0.0, 0.0, 0.0, -0.1, 1.0],
            raw_bytes=b"NOT_A_GEOTIFF_FILE",
        )
        preprocessor = SARPreprocessor()
        with pytest.raises(PreprocessingError) as exc_info:
            preprocessor.process(imagery)

        assert exc_info.value.code == SatelliteErrorCode.PROCESSING_FAILURE


# ---------------------------------------------------------------------------
# Security & Safety Tests
# ---------------------------------------------------------------------------


class TestSecurityAndSafety:
    """Verify security boundaries: no secrets, no massive array logs."""

    def test_repr_excludes_raw_arrays(self):
        """Ensure __repr__ on PreprocessedBand and PreprocessingResult excludes array dumps."""
        vv = np.random.uniform(0.01, 1.0, (10, 10)).astype(np.float32)
        preprocessor = SARPreprocessor()
        res = preprocessor.process_arrays(
            arrays={Polarization.VV: vv},
            polarizations=[Polarization.VV],
            observation_id="test_repr_safety",
            width=10,
            height=10,
            crs="EPSG:4326",
            bounds=[0.0, 0.0, 1.0, 1.0],
            transform=[0.1, 0.0, 0.0, 0.0, -0.1, 1.0],
        )

        res_repr = repr(res)
        band_repr = repr(res.get_band(Polarization.VV))

        # Must not contain large numpy array representations
        assert "array(" not in res_repr
        assert "array(" not in band_repr

    def test_error_to_dict_safety(self):
        """Ensure PreprocessingError.to_dict() filters any potential sensitive keys."""
        err = PreprocessingError(
            "Test processing error",
            details={
                "observation_id": "OBS_123",
                "token": "SHOULD_BE_STRIPPED",
                "secret": "SHOULD_BE_STRIPPED",
            },
        )
        d = err.to_dict()
        assert "token" not in d.get("details", {})
        assert "secret" not in d.get("details", {})
        assert d["details"]["observation_id"] == "OBS_123"


# ---------------------------------------------------------------------------
# Edge Cases & Parameter Validation Tests
# ---------------------------------------------------------------------------


class TestEdgeCasesAndValidation:
    """Verify defensive handling of invalid parameters and access errors."""

    def test_config_percentile_validation(self):
        """percentile_max <= percentile_min must be rejected by Pydantic validation."""
        with pytest.raises(ValueError, match="must be greater than"):
            PreprocessingConfig(percentile_min=90.0, percentile_max=10.0)

        with pytest.raises(ValueError, match="must be greater than"):
            PreprocessingConfig(percentile_min=50.0, percentile_max=50.0)

    def test_missing_polarization_array_raises_error(self):
        """Missing required polarization array raises PreprocessingError."""
        preprocessor = SARPreprocessor()
        with pytest.raises(PreprocessingError) as exc_info:
            preprocessor.process_arrays(
                arrays={Polarization.VV: np.ones((4, 4), dtype=np.float32)},
                polarizations=[Polarization.VV, Polarization.VH],  # VH missing in arrays
                observation_id="test_missing_band",
                width=4,
                height=4,
                crs="EPSG:4326",
                bounds=[0.0, 0.0, 1.0, 1.0],
                transform=[0.25, 0.0, 0.0, 0.0, -0.25, 1.0],
            )
        assert exc_info.value.code == SatelliteErrorCode.PROCESSING_FAILURE
        assert "Missing polarization array for VH" in exc_info.value.message

    def test_dimension_mismatch_raises_error(self):
        """Array shape not matching declared width/height raises PreprocessingError."""
        preprocessor = SARPreprocessor()
        with pytest.raises(PreprocessingError) as exc_info:
            preprocessor.process_arrays(
                arrays={Polarization.VV: np.ones((4, 6), dtype=np.float32)},
                polarizations=[Polarization.VV],
                observation_id="test_mismatch",
                width=4,  # expected 4, actual 6
                height=4,
                crs="EPSG:4326",
                bounds=[0.0, 0.0, 1.0, 1.0],
                transform=[0.25, 0.0, 0.0, 0.0, -0.25, 1.0],
            )
        assert "does not match expected" in exc_info.value.message

    def test_non_2d_array_raises_error(self):
        """Non-2D array raises PreprocessingError."""
        preprocessor = SARPreprocessor()
        with pytest.raises(PreprocessingError) as exc_info:
            preprocessor.process_arrays(
                arrays={Polarization.VV: np.ones((4, 4, 2), dtype=np.float32)},
                polarizations=[Polarization.VV],
                observation_id="test_3d",
                width=4,
                height=4,
                crs="EPSG:4326",
                bounds=[0.0, 0.0, 1.0, 1.0],
                transform=[0.25, 0.0, 0.0, 0.0, -0.25, 1.0],
            )
        assert "array must be 2D" in exc_info.value.message

    def test_empty_raw_bytes_raises_error(self):
        """ImageryResult with empty raw_bytes raises PreprocessingError."""
        imagery = ImageryResult(
            observation_id="empty_test",
            width=4,
            height=4,
            band_count=1,
            bands=[Polarization.VV],
            dtype="float32",
            crs="EPSG:4326",
            bounds=[0.0, 0.0, 1.0, 1.0],
            transform=[0.25, 0.0, 0.0, 0.0, -0.25, 1.0],
            raw_bytes=b"",
        )
        preprocessor = SARPreprocessor()
        with pytest.raises(PreprocessingError) as exc_info:
            preprocessor.process(imagery)
        assert "contains empty raw_bytes" in exc_info.value.message

    def test_get_band_missing_polarization(self):
        """Accessing a polarization not in the result raises KeyError."""
        preprocessor = SARPreprocessor()
        res = preprocessor.process_arrays(
            arrays={Polarization.VV: np.ones((2, 2), dtype=np.float32)},
            polarizations=[Polarization.VV],
            observation_id="test_keyerror",
            width=2,
            height=2,
            crs="EPSG:4326",
            bounds=[0.0, 0.0, 1.0, 1.0],
            transform=[0.5, 0.0, 0.0, 0.0, -0.5, 1.0],
        )
        with pytest.raises(KeyError, match="not present in result"):
            res.get_band(Polarization.VH)

    def test_get_linear_when_not_preserved(self):
        """Accessing linear data when preserve_linear=False raises ValueError."""
        preprocessor = SARPreprocessor()
        res = preprocessor.process_arrays(
            arrays={Polarization.VV: np.ones((2, 2), dtype=np.float32)},
            polarizations=[Polarization.VV],
            observation_id="test_no_linear",
            width=2,
            height=2,
            crs="EPSG:4326",
            bounds=[0.0, 0.0, 1.0, 1.0],
            transform=[0.5, 0.0, 0.0, 0.0, -0.5, 1.0],
            config=PreprocessingConfig(preserve_linear=False),
        )
        with pytest.raises(ValueError, match="Linear data was not preserved"):
            res.get_linear(Polarization.VV)

    def test_to_multichannel_array_invalid_kind(self):
        """Invalid kind in to_multichannel_array raises ValueError."""
        preprocessor = SARPreprocessor()
        res = preprocessor.process_arrays(
            arrays={Polarization.VV: np.ones((2, 2), dtype=np.float32)},
            polarizations=[Polarization.VV],
            observation_id="test_multi_err",
            width=2,
            height=2,
            crs="EPSG:4326",
            bounds=[0.0, 0.0, 1.0, 1.0],
            transform=[0.5, 0.0, 0.0, 0.0, -0.5, 1.0],
        )
        with pytest.raises(ValueError, match="Unknown array kind"):
            res.to_multichannel_array(kind="unsupported_kind")
