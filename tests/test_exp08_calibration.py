"""Deterministic unit tests for Sentinel-1 radiometric calibration engine.

Covers the 7 required deterministic test cases for Stage 3:
1. synthetic known-value calibration case
2. LUT interpolation test
3. dB conversion test
4. invalid/nonpositive handling test
5. dtype conversion test
6. VH/VV stacking-order test
7. nodata/dataMask propagation test

EXECUTION_AUTHORIZED = FALSE (Unit tests only; no model inference).
"""

from __future__ import annotations

import numpy as np
import pytest

from ocean_sentinel.satellite.calibration import (
    DEFAULT_EPSILON,
    OPERATIONAL_CH0_POLARIZATION,
    OPERATIONAL_CH1_POLARIZATION,
    OPERATIONAL_STACK_ORDER,
    apply_nodata_datamask,
    calibrate_dn_to_sigma0_linear,
    interpolate_calibration_lut_grid,
    linear_to_db,
    stack_dual_pol_channels,
)


class TestRadiometricCalibrationEngine:
    """Stage 3 Unit Tests for Sentinel-1 Calibration Pipeline."""

    # 1. Synthetic known-value calibration case
    def test_synthetic_known_value_calibration(self):
        """Verify sigma0_linear = DN^2 / A_sigma^2 with exact known values."""
        # Case 1: DN = 100, A_sigma = 50 -> sigma0 = 10000 / 2500 = 4.0
        dn = np.array([[100.0, 200.0], [50.0, 150.0]], dtype=np.float32)
        lut_sigma = np.array([[50.0, 100.0], [25.0, 75.0]], dtype=np.float32)

        sigma0 = calibrate_dn_to_sigma0_linear(dn, lut_sigma)
        expected = np.array([[4.0, 4.0], [4.0, 4.0]], dtype=np.float32)

        np.testing.assert_allclose(sigma0, expected, rtol=1e-5)

    # 2. LUT interpolation test
    def test_lut_interpolation_grid(self):
        """Verify bilinear interpolation across sparse calibration vectors."""
        lines = [0, 10]
        pixel_coords = [0, 10]
        # At (0,0)=10, (0,10)=20, (10,0)=30, (10,10)=40
        lut_values = np.array([[10.0, 20.0], [30.0, 40.0]], dtype=np.float64)

        target_shape = (11, 11)
        grid = interpolate_calibration_lut_grid(lines, pixel_coords, lut_values, target_shape)

        assert grid.shape == (11, 11)
        # Check corners
        assert pytest.approx(grid[0, 0], rel=1e-5) == 10.0
        assert pytest.approx(grid[0, 10], rel=1e-5) == 20.0
        assert pytest.approx(grid[10, 0], rel=1e-5) == 30.0
        assert pytest.approx(grid[10, 10], rel=1e-5) == 40.0
        # Check center (5, 5) -> average of 4 corners = 25.0
        assert pytest.approx(grid[5, 5], rel=1e-5) == 25.0
        # Check intermediate points
        assert pytest.approx(grid[0, 5], rel=1e-5) == 15.0
        assert pytest.approx(grid[5, 0], rel=1e-5) == 20.0

    # 3. dB conversion test
    def test_linear_to_db_conversion(self):
        """Verify 10 * log10(linear) for standard radar backscatter values."""
        # linear = 1.0 -> 0.0 dB
        # linear = 0.1 -> -10.0 dB
        # linear = 0.01 -> -20.0 dB
        # linear = 0.001 -> -30.0 dB
        linear = np.array([1.0, 0.1, 0.01, 0.001], dtype=np.float32)
        db = linear_to_db(linear)
        expected = np.array([0.0, -10.0, -20.0, -30.0], dtype=np.float32)

        np.testing.assert_allclose(db, expected, atol=1e-5)

    # 4. Invalid/nonpositive handling test
    def test_invalid_nonpositive_handling(self):
        """Verify handling of zeros, negatives, NaNs, and infinities in dB conversion."""
        linear = np.array([0.0, -5.0, np.nan, np.inf, -np.inf, 0.01], dtype=np.float32)
        db = linear_to_db(linear, fill_invalid=-999.0)

        # 0.0 and -5.0 are non-positive -> fill_invalid
        assert db[0] == -999.0
        assert db[1] == -999.0
        # NaN, inf, -inf are non-finite -> fill_invalid
        assert db[2] == -999.0
        assert db[3] == -999.0
        assert db[4] == -999.0
        # Valid positive value converted correctly: 0.01 -> -20 dB
        assert pytest.approx(db[5], rel=1e-4) == -20.0

    # 5. Dtype conversion test
    def test_dtype_conversion_float32(self):
        """All pipeline stages must produce strictly float32 arrays."""
        # From integer DN
        dn_int = np.array([[100, 200], [300, 400]], dtype=np.uint16)
        sigma0 = calibrate_dn_to_sigma0_linear(dn_int, 50.0)
        assert sigma0.dtype == np.float32

        # To dB
        db = linear_to_db(sigma0)
        assert db.dtype == np.float32

        # Stacking
        stacked = stack_dual_pol_channels(db, db)
        assert stacked.dtype == np.float32

    # 6. VH/VV stacking-order test
    def test_vh_vv_stacking_order_enforcement(self):
        """Verify Ch0 is VH and Ch1 is VV per EXP-06 Operational Contract."""
        vh = np.full((10, 10), -33.0, dtype=np.float32)
        vv = np.full((10, 10), -20.0, dtype=np.float32)

        stacked = stack_dual_pol_channels(vh, vv, order=("VH", "VV"))
        assert stacked.shape == (2, 10, 10)
        # Ch0 must be VH (-33.0)
        assert np.all(stacked[0] == -33.0)
        # Ch1 must be VV (-20.0)
        assert np.all(stacked[1] == -20.0)

        # Inverted or invalid order must raise ValueError
        with pytest.raises(ValueError, match="operational contract strictly requires"):
            stack_dual_pol_channels(vh, vv, order=("VV", "VH"))

    # 7. Nodata/dataMask propagation test
    def test_nodata_datamask_propagation(self):
        """Verify dataMask (0=invalid, 1=valid) sets invalid pixels to nodata_value."""
        # 2D case
        raster_2d = np.ones((4, 4), dtype=np.float32) * 5.0
        mask = np.array([
            [1, 1, 0, 0],
            [1, 1, 1, 0],
            [0, 1, 1, 1],
            [0, 0, 1, 1],
        ], dtype=np.uint8)

        masked_2d = apply_nodata_datamask(raster_2d, mask, nodata_value=np.nan)
        assert not np.isnan(masked_2d[0, 0])
        assert not np.isnan(masked_2d[0, 1])
        assert np.isnan(masked_2d[0, 2])
        assert np.isnan(masked_2d[0, 3])

        # 3D case (dual-channel raster)
        raster_3d = np.ones((2, 4, 4), dtype=np.float32) * 10.0
        masked_3d = apply_nodata_datamask(raster_3d, mask, nodata_value=-999.0)
        assert masked_3d.shape == (2, 4, 4)
        for c in range(2):
            assert masked_3d[c, 0, 0] == 10.0
            assert masked_3d[c, 0, 2] == -999.0
            assert masked_3d[c, 3, 0] == -999.0
            assert masked_3d[c, 3, 3] == 10.0
