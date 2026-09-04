"""Tests for data models and validation.

Verifies:
- Valid AOI is accepted
- Invalid coordinates are rejected
- Time range validation works
- Acquisition metadata handles required/optional fields
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from ocean_sentinel.models import (
    AcquisitionMetadata,
    BoundingBox,
    OrbitDirection,
    Polarization,
    ProductType,
    SearchRequest,
    TimeRange,
)


class TestBoundingBox:
    """Tests for BoundingBox validation."""

    def test_valid_bbox(self):
        """Normal Mediterranean AOI should be accepted."""
        bbox = BoundingBox(west=12.0, south=40.0, east=15.0, north=42.0)
        assert bbox.west == 12.0
        assert bbox.to_list() == [12.0, 40.0, 15.0, 42.0]

    def test_invalid_latitude_too_high(self):
        """Latitude > 90 must be rejected."""
        with pytest.raises(ValidationError, match="less than or equal to 90"):
            BoundingBox(west=0.0, south=0.0, east=1.0, north=91.0)

    def test_invalid_latitude_too_low(self):
        """Latitude < -90 must be rejected."""
        with pytest.raises(ValidationError, match="greater than or equal to -90"):
            BoundingBox(west=0.0, south=-91.0, east=1.0, north=1.0)

    def test_invalid_longitude_too_high(self):
        """Longitude > 180 must be rejected."""
        with pytest.raises(ValidationError, match="less than or equal to 180"):
            BoundingBox(west=0.0, south=0.0, east=181.0, north=1.0)

    def test_invalid_longitude_too_low(self):
        """Longitude < -180 must be rejected."""
        with pytest.raises(ValidationError, match="greater than or equal to -180"):
            BoundingBox(west=-181.0, south=0.0, east=1.0, north=1.0)

    def test_reversed_latitude(self):
        """north <= south must be rejected."""
        with pytest.raises(ValidationError, match="north.*must be greater than south"):
            BoundingBox(west=0.0, south=42.0, east=1.0, north=40.0)

    def test_reversed_longitude(self):
        """east <= west must be rejected."""
        with pytest.raises(ValidationError, match="east.*must be greater than west"):
            BoundingBox(west=15.0, south=40.0, east=12.0, north=42.0)

    def test_zero_area_latitude(self):
        """north == south (zero-height box) must be rejected."""
        with pytest.raises(ValidationError, match="north.*must be greater than south"):
            BoundingBox(west=0.0, south=40.0, east=1.0, north=40.0)

    def test_zero_area_longitude(self):
        """east == west (zero-width box) must be rejected."""
        with pytest.raises(ValidationError, match="east.*must be greater than west"):
            BoundingBox(west=12.0, south=40.0, east=12.0, north=42.0)

    def test_to_geojson_polygon(self):
        """GeoJSON output should be a valid Polygon."""
        bbox = BoundingBox(west=12.0, south=40.0, east=15.0, north=42.0)
        geojson = bbox.to_geojson_polygon()
        assert geojson["type"] == "Polygon"
        assert len(geojson["coordinates"][0]) == 5  # Closed ring
        assert geojson["coordinates"][0][0] == geojson["coordinates"][0][-1]  # Ring is closed

    def test_area_degrees_squared(self):
        """Area calculation should return positive value."""
        bbox = BoundingBox(west=12.0, south=40.0, east=15.0, north=42.0)
        assert bbox.area_degrees_squared == pytest.approx(6.0)


class TestTimeRange:
    """Tests for TimeRange validation."""

    def test_valid_time_range(self):
        """Normal time range should be accepted."""
        tr = TimeRange(
            start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end=datetime(2024, 1, 31, tzinfo=timezone.utc),
        )
        assert tr.start < tr.end

    def test_reversed_time_range(self):
        """end before start must be rejected."""
        with pytest.raises(ValidationError, match="end.*must be after start"):
            TimeRange(
                start=datetime(2024, 1, 31, tzinfo=timezone.utc),
                end=datetime(2024, 1, 1, tzinfo=timezone.utc),
            )

    def test_equal_start_end(self):
        """start == end must be rejected."""
        with pytest.raises(ValidationError, match="end.*must be after start"):
            TimeRange(
                start=datetime(2024, 1, 1, tzinfo=timezone.utc),
                end=datetime(2024, 1, 1, tzinfo=timezone.utc),
            )

    def test_stac_datetime_format(self):
        """STAC datetime string format should be correct."""
        tr = TimeRange(
            start=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            end=datetime(2024, 1, 31, 23, 59, 59, tzinfo=timezone.utc),
        )
        stac_str = tr.to_stac_datetime()
        assert "/" in stac_str
        assert stac_str.count("Z") == 2


class TestSearchRequest:
    """Tests for SearchRequest validation."""

    def test_valid_search_request(self):
        """Complete valid search request should be accepted."""
        req = SearchRequest(
            bbox=BoundingBox(west=12.0, south=40.0, east=15.0, north=42.0),
            time_range=TimeRange(
                start=datetime(2024, 1, 1, tzinfo=timezone.utc),
                end=datetime(2024, 1, 31, tzinfo=timezone.utc),
            ),
        )
        assert req.product_type == ProductType.GRD
        assert Polarization.VV in req.polarizations
        assert Polarization.VH in req.polarizations

    def test_max_results_bounds(self):
        """max_results must be between 1 and 100."""
        with pytest.raises(ValidationError):
            SearchRequest(
                bbox=BoundingBox(west=12.0, south=40.0, east=15.0, north=42.0),
                time_range=TimeRange(
                    start=datetime(2024, 1, 1, tzinfo=timezone.utc),
                    end=datetime(2024, 1, 31, tzinfo=timezone.utc),
                ),
                max_results=0,
            )


class TestAcquisitionMetadata:
    """Tests for the internal acquisition representation."""

    def _valid_geometry(self) -> dict:
        return {
            "type": "Polygon",
            "coordinates": [[
                [12.0, 40.0],
                [15.0, 40.0],
                [15.0, 42.0],
                [12.0, 42.0],
                [12.0, 40.0],
            ]],
        }

    def test_valid_acquisition(self):
        """Complete valid acquisition should be accepted."""
        acq = AcquisitionMetadata(
            id="S1A_IW_GRDH_1SDV_20240101T054500",
            mission="sentinel-1",
            product_type=ProductType.GRD,
            acquisition_time=datetime(2024, 1, 1, 5, 45, 0, tzinfo=timezone.utc),
            geometry=self._valid_geometry(),
            polarizations=[Polarization.VV, Polarization.VH],
            orbit_direction=OrbitDirection.ASCENDING,
            acquisition_mode="IW",
        )
        assert acq.id == "S1A_IW_GRDH_1SDV_20240101T054500"
        assert acq.provider == "copernicus_cdse"

    def test_minimal_acquisition(self):
        """Acquisition with only required fields should be accepted."""
        acq = AcquisitionMetadata(
            id="test-id",
            mission="sentinel-1",
            product_type=ProductType.GRD,
            acquisition_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
            geometry=self._valid_geometry(),
        )
        assert acq.polarizations is None
        assert acq.orbit_direction is None
        assert acq.provider_properties is None

    def test_missing_required_id(self):
        """Missing 'id' must be rejected."""
        with pytest.raises(ValidationError, match="id"):
            AcquisitionMetadata(
                mission="sentinel-1",
                product_type=ProductType.GRD,
                acquisition_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
                geometry=self._valid_geometry(),
            )

    def test_missing_required_geometry(self):
        """Missing 'geometry' must be rejected."""
        with pytest.raises(ValidationError, match="geometry"):
            AcquisitionMetadata(
                id="test-id",
                mission="sentinel-1",
                product_type=ProductType.GRD,
                acquisition_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
            )

    def test_invalid_geometry(self):
        """Non-GeoJSON geometry must be rejected."""
        with pytest.raises(ValidationError, match="geometry"):
            AcquisitionMetadata(
                id="test-id",
                mission="sentinel-1",
                product_type=ProductType.GRD,
                acquisition_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
                geometry={"type": "InvalidType", "coordinates": []},
            )

    def test_optional_provider_properties(self):
        """Provider properties should store arbitrary metadata."""
        acq = AcquisitionMetadata(
            id="test-id",
            mission="sentinel-1",
            product_type=ProductType.GRD,
            acquisition_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
            geometry=self._valid_geometry(),
            provider_properties={"stac_version": "1.1.0", "raw_id": "abc123"},
        )
        assert acq.provider_properties["stac_version"] == "1.1.0"
