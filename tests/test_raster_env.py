"""Raster stack validation test.

Verifies that the installed rasterio/GDAL environment can perform
basic raster I/O operations required for Phase 1B.

This uses ONLY synthetic test data.
No real satellite imagery is used or simulated.
"""

import tempfile
import os

import numpy as np
import pytest
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_bounds


class TestRasterEnvironment:
    """Validates that rasterio can create, write, and read rasters."""

    @pytest.fixture
    def synthetic_raster_path(self, tmp_path):
        """Create a small synthetic 2-band FLOAT32 GeoTIFF (VV/VH placeholder).

        This is purely a library validation artifact — NOT satellite data.
        The pixel values are arbitrary test data.
        """
        filepath = tmp_path / "test_synthetic_raster.tif"

        height, width = 10, 10
        bands = 2  # Matching eventual VV + VH layout

        # Arbitrary test pixel data — NOT real backscatter values
        band1 = np.random.default_rng(42).random((height, width)).astype(np.float32)
        band2 = np.random.default_rng(99).random((height, width)).astype(np.float32)

        # Arbitrary Mediterranean-area bounds for the test AOI
        west, south, east, north = 16.0, 39.0, 17.0, 40.0
        transform = from_bounds(west, south, east, north, width, height)

        with rasterio.open(
            filepath,
            "w",
            driver="GTiff",
            height=height,
            width=width,
            count=bands,
            dtype=rasterio.float32,
            crs=CRS.from_epsg(4326),
            transform=transform,
        ) as dst:
            dst.write(band1, 1)
            dst.write(band2, 2)

        return filepath, band1, band2, (west, south, east, north)

    def test_rasterio_import(self):
        """rasterio must import and report a version."""
        assert hasattr(rasterio, "__version__")
        assert rasterio.__version__  # not empty

    def test_gdal_available(self):
        """GDAL must be accessible through rasterio."""
        gdal_version = rasterio.gdal_version()
        assert gdal_version  # not empty
        parts = gdal_version.split(".")
        assert len(parts) >= 2  # e.g. "3.10.3"

    def test_create_and_read_dimensions(self, synthetic_raster_path):
        """Created raster must have correct dimensions."""
        filepath, _, _, _ = synthetic_raster_path
        with rasterio.open(filepath) as src:
            assert src.height == 10
            assert src.width == 10
            assert src.count == 2  # 2 bands (VV + VH layout)

    def test_read_pixel_data(self, synthetic_raster_path):
        """Pixel data must be readable and match what was written."""
        filepath, expected_band1, expected_band2, _ = synthetic_raster_path
        with rasterio.open(filepath) as src:
            band1 = src.read(1)
            band2 = src.read(2)
            assert band1.dtype == np.float32
            assert band2.dtype == np.float32
            np.testing.assert_array_almost_equal(band1, expected_band1)
            np.testing.assert_array_almost_equal(band2, expected_band2)

    def test_crs(self, synthetic_raster_path):
        """CRS must be preserved (EPSG:4326)."""
        filepath, _, _, _ = synthetic_raster_path
        with rasterio.open(filepath) as src:
            assert src.crs is not None
            assert src.crs.to_epsg() == 4326

    def test_transform_and_bounds(self, synthetic_raster_path):
        """Transform and bounds must match what was specified."""
        filepath, _, _, (west, south, east, north) = synthetic_raster_path
        with rasterio.open(filepath) as src:
            assert src.transform is not None
            bounds = src.bounds
            assert bounds.left == pytest.approx(west)
            assert bounds.bottom == pytest.approx(south)
            assert bounds.right == pytest.approx(east)
            assert bounds.top == pytest.approx(north)

    def test_dtype_float32(self, synthetic_raster_path):
        """All bands must report FLOAT32 dtype."""
        filepath, _, _, _ = synthetic_raster_path
        with rasterio.open(filepath) as src:
            for i in range(1, src.count + 1):
                assert src.dtypes[i - 1] == "float32"
