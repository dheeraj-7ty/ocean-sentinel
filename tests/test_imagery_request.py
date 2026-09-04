"""Tests for Phase 1B.3.1 — Process API request construction.

Covers:
- ImageryRequest model validation
- OutputConfig model validation
- ProcessRequestBuilder payload structure
- Evalscript generation (per-band)
- Datetime serialisation
- Bbox serialisation
- Band/polarization availability validation
- Security: no credentials in payload or errors
- Regression: existing test suite unaffected

All tests are pure Python — no real network calls.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from ocean_sentinel.errors import InvalidRequestError
from ocean_sentinel.models import (
    AcquisitionMetadata,
    BoundingBox,
    ImageryRequest,
    OutputConfig,
    OutputFormat,
    Polarization,
    ProductType,
    TimeRange,
)
from ocean_sentinel.satellite.imagery import (
    SH_DATA_TYPE_S1_GRD,
    SH_S1_DEFAULT_PROCESSING,
    ProcessRequestBuilder,
    _fmt_sh_datetime,
)

# ---------------------------------------------------------------------------
# Shared helpers / fixtures
# ---------------------------------------------------------------------------

_GEOM = {
    "type": "Polygon",
    "coordinates": [[
        [15.0, 39.5], [16.0, 39.5], [16.0, 40.5],
        [15.0, 40.5], [15.0, 39.5],
    ]],
}

_BBOX = BoundingBox(west=15.0, south=39.5, east=16.0, north=40.5)
_TIME = TimeRange(
    start=datetime(2026, 9, 1, tzinfo=timezone.utc),
    end=datetime(2026, 9, 2, tzinfo=timezone.utc),
)


def _make_obs(
    polarizations: list[Polarization] | None = None,
    obs_id: str = "S1D_TEST_OBS",
) -> AcquisitionMetadata:
    """Create a minimal valid AcquisitionMetadata for testing."""
    if polarizations is None:
        polarizations = [Polarization.VV, Polarization.VH]
    return AcquisitionMetadata(
        id=obs_id,
        mission="sentinel-1",
        product_type=ProductType.GRD,
        acquisition_time=datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc),
        geometry=_GEOM,
        polarizations=polarizations,
    )


def _make_request(
    bands: list[Polarization] | None = None,
    obs: AcquisitionMetadata | None = None,
    output: OutputConfig | None = None,
) -> ImageryRequest:
    """Create a valid ImageryRequest for use in builder tests."""
    if bands is None:
        bands = [Polarization.VV, Polarization.VH]
    if obs is None:
        obs = _make_obs()
    if output is None:
        output = OutputConfig(width=512, height=512)
    return ImageryRequest(
        observation=obs,
        bbox=_BBOX,
        time_range=_TIME,
        requested_bands=bands,
        output=output,
    )


# ---------------------------------------------------------------------------
# OutputConfig — model validation
# ---------------------------------------------------------------------------


class TestOutputConfig:
    """Tests for OutputConfig Pydantic model."""

    def test_pixel_dimensions_valid(self):
        cfg = OutputConfig(width=512, height=512)
        assert cfg.width == 512
        assert cfg.height == 512
        assert cfg.resolution_meters is None

    def test_resolution_valid(self):
        cfg = OutputConfig(resolution_meters=10.0)
        assert cfg.resolution_meters == 10.0
        assert cfg.width is None
        assert cfg.height is None

    def test_default_format_is_tiff(self):
        cfg = OutputConfig(width=64, height=64)
        assert cfg.format == OutputFormat.TIFF
        assert cfg.format.value == "image/tiff"

    def test_invalid_output_format_raises(self):
        with pytest.raises(ValidationError):
            OutputConfig(format="image/png", width=512, height=512)

    def test_default_crs_is_wgs84(self):
        cfg = OutputConfig(width=64, height=64)
        assert cfg.crs_epsg == 4326

    def test_invalid_crs_epsg_raises(self):
        with pytest.raises(ValidationError):
            OutputConfig(width=512, height=512, crs_epsg=0)

    def test_custom_crs(self):
        cfg = OutputConfig(width=64, height=64, crs_epsg=32632)
        assert "32632" in cfg.to_crs_url()

    def test_crs_url_format(self):
        cfg = OutputConfig(width=64, height=64)
        assert cfg.to_crs_url() == "http://www.opengis.net/def/crs/EPSG/0/4326"

    def test_neither_dimensions_nor_resolution_raises(self):
        with pytest.raises(ValidationError, match="At least one"):
            OutputConfig()

    def test_both_dimensions_and_resolution_raises(self):
        with pytest.raises(ValidationError, match="not both"):
            OutputConfig(width=512, height=512, resolution_meters=10.0)

    def test_width_without_height_raises(self):
        with pytest.raises(ValidationError, match="both be specified"):
            OutputConfig(width=512)

    def test_height_without_width_raises(self):
        with pytest.raises(ValidationError, match="both be specified"):
            OutputConfig(height=512)

    def test_zero_resolution_raises(self):
        with pytest.raises(ValidationError):
            OutputConfig(resolution_meters=0.0)

    def test_negative_resolution_raises(self):
        with pytest.raises(ValidationError):
            OutputConfig(resolution_meters=-5.0)

    def test_zero_width_raises(self):
        with pytest.raises(ValidationError):
            OutputConfig(width=0, height=512)

    def test_oversized_dimensions_raise(self):
        with pytest.raises(ValidationError):
            OutputConfig(width=2501, height=512)

    def test_to_sh_output_with_pixel_dims(self):
        cfg = OutputConfig(width=256, height=128)
        out = cfg.to_sh_output()
        assert out["width"] == 256
        assert out["height"] == 128
        assert "resx" not in out
        assert out["responses"][0]["identifier"] == "default"
        assert out["responses"][0]["format"]["type"] == "image/tiff"

    def test_to_sh_output_with_resolution(self):
        cfg = OutputConfig(resolution_meters=20.0)
        out = cfg.to_sh_output()
        assert out["resx"] == 20.0
        assert out["resy"] == 20.0
        assert "width" not in out
        assert "height" not in out


# ---------------------------------------------------------------------------
# ImageryRequest — model validation
# ---------------------------------------------------------------------------


class TestImageryRequest:
    """Tests for ImageryRequest Pydantic model."""

    def test_valid_vv_request(self):
        """Single VV band request should succeed."""
        req = _make_request(bands=[Polarization.VV])
        assert req.requested_bands == [Polarization.VV]

    def test_valid_vh_request(self):
        """Single VH band request should succeed."""
        req = _make_request(bands=[Polarization.VH])
        assert req.requested_bands == [Polarization.VH]

    def test_valid_vv_vh_request(self):
        """Dual-band VV+VH request should succeed."""
        req = _make_request(bands=[Polarization.VV, Polarization.VH])
        assert len(req.requested_bands) == 2

    def test_observation_required(self):
        with pytest.raises(ValidationError):
            ImageryRequest(
                bbox=_BBOX,
                time_range=_TIME,
                requested_bands=[Polarization.VV],
            )

    def test_bbox_required(self):
        with pytest.raises(ValidationError):
            ImageryRequest(
                observation=_make_obs(),
                time_range=_TIME,
                requested_bands=[Polarization.VV],
            )

    def test_time_range_required(self):
        with pytest.raises(ValidationError):
            ImageryRequest(
                observation=_make_obs(),
                bbox=_BBOX,
                requested_bands=[Polarization.VV],
            )

    def test_empty_bands_rejected(self):
        """Empty band list must be rejected at model level."""
        with pytest.raises(ValidationError, match="at least 1"):
            ImageryRequest(
                observation=_make_obs(),
                bbox=_BBOX,
                time_range=_TIME,
                requested_bands=[],
            )

    def test_unsupported_polarization_rejected(self):
        """Requesting HH when observation has only VV/VH must fail."""
        obs = _make_obs(polarizations=[Polarization.VV, Polarization.VH])
        with pytest.raises(ValidationError, match="HH"):
            ImageryRequest(
                observation=obs,
                bbox=_BBOX,
                time_range=_TIME,
                requested_bands=[Polarization.HH],
            )

    def test_partial_unsupported_polarization_rejected(self):
        """VV+HH when observation only has VV+VH must fail."""
        obs = _make_obs(polarizations=[Polarization.VV, Polarization.VH])
        with pytest.raises(ValidationError, match="HH"):
            ImageryRequest(
                observation=obs,
                bbox=_BBOX,
                time_range=_TIME,
                requested_bands=[Polarization.VV, Polarization.HH],
            )

    def test_hh_hv_obs_accepts_hh(self):
        """HH band should be accepted when observation has HH."""
        obs = _make_obs(polarizations=[Polarization.HH, Polarization.HV])
        req = ImageryRequest(
            observation=obs,
            bbox=_BBOX,
            time_range=_TIME,
            requested_bands=[Polarization.HH],
        )
        assert req.requested_bands == [Polarization.HH]

    def test_no_polarization_metadata_allows_any_band(self):
        """Observation with None polarizations skips band validation."""
        obs = _make_obs(polarizations=None)
        # Should not raise — polarization check is skipped
        req = ImageryRequest(
            observation=obs,
            bbox=_BBOX,
            time_range=_TIME,
            requested_bands=[Polarization.VV],
        )
        assert req.requested_bands == [Polarization.VV]

    def test_reversed_bbox_rejected(self):
        """Reversed east/west or north/south must fail bbox validation."""
        with pytest.raises(ValidationError):
            ImageryRequest(
                observation=_make_obs(),
                bbox=BoundingBox(west=16.0, south=39.5, east=15.0, north=40.5),
                time_range=_TIME,
                requested_bands=[Polarization.VV],
            )

    def test_reversed_time_range_rejected(self):
        """end <= start must be rejected."""
        with pytest.raises(ValidationError):
            ImageryRequest(
                observation=_make_obs(),
                bbox=_BBOX,
                time_range=TimeRange(
                    start=datetime(2026, 9, 2, tzinfo=timezone.utc),
                    end=datetime(2026, 9, 1, tzinfo=timezone.utc),
                ),
                requested_bands=[Polarization.VV],
            )

    def test_timezone_aware_datetimes_accepted(self):
        """Timezone-aware datetimes must be accepted."""
        req = _make_request()
        assert req.time_range.start.tzinfo is not None
        assert req.time_range.end.tzinfo is not None

    def test_default_output_is_512x512_tiff(self):
        """Default output should be 512×512 GeoTIFF."""
        req = _make_request()
        assert req.output.width == 512
        assert req.output.height == 512
        assert req.output.format == OutputFormat.TIFF


# ---------------------------------------------------------------------------
# ProcessRequestBuilder — payload structure
# ---------------------------------------------------------------------------


class TestProcessRequestBuilder:
    """Tests for ProcessRequestBuilder.build() payload structure."""

    def test_build_returns_dict(self):
        payload = ProcessRequestBuilder.build(_make_request())
        assert isinstance(payload, dict)

    def test_payload_has_required_top_level_keys(self):
        payload = ProcessRequestBuilder.build(_make_request())
        assert "input" in payload
        assert "output" in payload
        assert "evalscript" in payload

    def test_input_has_bounds_and_data(self):
        payload = ProcessRequestBuilder.build(_make_request())
        assert "bounds" in payload["input"]
        assert "data" in payload["input"]

    def test_bounds_bbox_matches_request(self):
        req = _make_request()
        payload = ProcessRequestBuilder.build(req)
        assert payload["input"]["bounds"]["bbox"] == [15.0, 39.5, 16.0, 40.5]

    def test_bounds_crs_is_wgs84_by_default(self):
        payload = ProcessRequestBuilder.build(_make_request())
        crs = payload["input"]["bounds"]["properties"]["crs"]
        assert "4326" in crs

    def test_data_collection_is_sentinel1_grd(self):
        payload = ProcessRequestBuilder.build(_make_request())
        data = payload["input"]["data"]
        assert len(data) == 1
        assert data[0]["type"] == SH_DATA_TYPE_S1_GRD

    def test_data_filter_time_range_from(self):
        payload = ProcessRequestBuilder.build(_make_request())
        tf = payload["input"]["data"][0]["dataFilter"]["timeRange"]
        assert tf["from"] == "2026-09-01T00:00:00Z"

    def test_data_filter_time_range_to(self):
        payload = ProcessRequestBuilder.build(_make_request())
        tf = payload["input"]["data"][0]["dataFilter"]["timeRange"]
        assert tf["to"] == "2026-09-02T00:00:00Z"

    def test_processing_orthorectify_present(self):
        payload = ProcessRequestBuilder.build(_make_request())
        proc = payload["input"]["data"][0]["processing"]
        assert proc.get("orthorectify") == "true"
        assert proc == SH_S1_DEFAULT_PROCESSING

    def test_processing_back_coeff_present(self):
        payload = ProcessRequestBuilder.build(_make_request())
        proc = payload["input"]["data"][0]["processing"]
        assert proc.get("backCoeff") == "SIGMA0_ELLIPSOID"

    def test_empty_deduplicated_bands_raises_invalid_request_error(self):
        req = _make_request()
        object.__setattr__(req, "requested_bands", [])
        with pytest.raises(InvalidRequestError, match="No valid bands remain"):
            ProcessRequestBuilder.build(req)

    def test_output_width_height_present(self):
        req = _make_request(output=OutputConfig(width=256, height=128))
        payload = ProcessRequestBuilder.build(req)
        assert payload["output"]["width"] == 256
        assert payload["output"]["height"] == 128

    def test_output_responses_format_tiff(self):
        payload = ProcessRequestBuilder.build(_make_request())
        responses = payload["output"]["responses"]
        assert responses[0]["format"]["type"] == "image/tiff"

    def test_evalscript_contains_version3(self):
        payload = ProcessRequestBuilder.build(_make_request())
        assert "//VERSION=3" in payload["evalscript"]

    def test_evalscript_vv_single_band(self):
        req = _make_request(bands=[Polarization.VV])
        payload = ProcessRequestBuilder.build(req)
        es = payload["evalscript"]
        assert '"VV"' in es
        assert '"VH"' not in es
        assert "samples.VV" in es
        assert "bands: 1" in es

    def test_evalscript_vh_single_band(self):
        req = _make_request(bands=[Polarization.VH])
        payload = ProcessRequestBuilder.build(req)
        es = payload["evalscript"]
        assert '"VH"' in es
        assert '"VV"' not in es
        assert "samples.VH" in es

    def test_evalscript_vv_vh_dual_band(self):
        req = _make_request(bands=[Polarization.VV, Polarization.VH])
        payload = ProcessRequestBuilder.build(req)
        es = payload["evalscript"]
        assert '"VV"' in es
        assert '"VH"' in es
        assert "samples.VV" in es
        assert "samples.VH" in es
        assert "bands: 2" in es

    def test_evalscript_hh_hv_dual_band(self):
        obs = _make_obs(polarizations=[Polarization.HH, Polarization.HV])
        req = _make_request(
            obs=obs,
            bands=[Polarization.HH, Polarization.HV],
        )
        payload = ProcessRequestBuilder.build(req)
        es = payload["evalscript"]
        assert '"HH"' in es
        assert '"HV"' in es
        assert "bands: 2" in es

    def test_duplicate_bands_deduplicated(self):
        """Duplicate requested bands should be silently deduplicated."""
        req = ImageryRequest(
            observation=_make_obs(),
            bbox=_BBOX,
            time_range=_TIME,
            requested_bands=[Polarization.VV, Polarization.VV],
        )
        payload = ProcessRequestBuilder.build(req)
        es = payload["evalscript"]
        # Only one VV entry in output list, not two
        assert "bands: 1" in es
        assert es.count('"VV"') == 1  # appears once in input list

    def test_output_with_resolution(self):
        """Resolution-based output should use resx/resy instead of width/height."""
        req = _make_request(output=OutputConfig(resolution_meters=10.0))
        payload = ProcessRequestBuilder.build(req)
        assert payload["output"]["resx"] == 10.0
        assert payload["output"]["resy"] == 10.0
        assert "width" not in payload["output"]
        assert "height" not in payload["output"]


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    """Payload must be deterministic across identical invocations."""

    def test_identical_inputs_produce_identical_payload(self):
        req1 = _make_request()
        req2 = _make_request()
        p1 = json.dumps(ProcessRequestBuilder.build(req1), sort_keys=True)
        p2 = json.dumps(ProcessRequestBuilder.build(req2), sort_keys=True)
        assert p1 == p2

    def test_evalscript_is_deterministic(self):
        req = _make_request(bands=[Polarization.VV, Polarization.VH])
        p1 = ProcessRequestBuilder.build(req)
        p2 = ProcessRequestBuilder.build(req)
        assert p1["evalscript"] == p2["evalscript"]


# ---------------------------------------------------------------------------
# Datetime serialisation
# ---------------------------------------------------------------------------


class TestDatetimeSerialization:
    """Process API datetime format: YYYY-MM-DDTHH:MM:SSZ (no microseconds)."""

    def test_utc_datetime_formatted_correctly(self):
        dt = datetime(2026, 9, 1, 16, 30, 45, tzinfo=timezone.utc)
        assert _fmt_sh_datetime(dt) == "2026-09-01T16:30:45Z"

    def test_microseconds_are_dropped(self):
        dt = datetime(2026, 9, 1, 16, 30, 45, 123456, tzinfo=timezone.utc)
        result = _fmt_sh_datetime(dt)
        assert result == "2026-09-01T16:30:45Z"
        assert "." not in result

    def test_naive_datetime_formatted_without_offset(self):
        dt = datetime(2026, 9, 1, 0, 0, 0)
        result = _fmt_sh_datetime(dt)
        assert result == "2026-09-01T00:00:00Z"

    def test_time_range_in_payload_is_utc(self):
        req = _make_request()
        payload = ProcessRequestBuilder.build(req)
        tf = payload["input"]["data"][0]["dataFilter"]["timeRange"]
        assert tf["from"].endswith("Z")
        assert tf["to"].endswith("Z")
        assert "+" not in tf["from"]
        assert "+" not in tf["to"]


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------


class TestSecurity:
    """No credentials or tokens must appear in the payload or error messages."""

    def test_payload_has_no_authorization_key(self):
        payload = ProcessRequestBuilder.build(_make_request())
        payload_str = json.dumps(payload)
        assert "Authorization" not in payload_str
        assert "Bearer" not in payload_str
        assert "access_token" not in payload_str

    def test_payload_has_no_client_secret_key(self):
        payload = ProcessRequestBuilder.build(_make_request())
        payload_str = json.dumps(payload)
        assert "client_secret" not in payload_str
        assert "client_id" not in payload_str

    def test_error_message_contains_no_fake_credentials(self):
        """Error messages must not contain credential-like strings."""
        obs = _make_obs(polarizations=[Polarization.VV, Polarization.VH])
        with pytest.raises(ValidationError) as exc_info:
            ImageryRequest(
                observation=obs,
                bbox=_BBOX,
                time_range=_TIME,
                requested_bands=[Polarization.HH],
            )
        err_str = str(exc_info.value)
        assert "secret" not in err_str.lower()
        assert "token" not in err_str.lower()
        assert "password" not in err_str.lower()

    def test_no_env_contents_in_errors(self, monkeypatch):
        """Errors must not leak environment variable values."""
        secret_val = "very-confidential-secret-98765"
        monkeypatch.setenv("COPERNICUS_CLIENT_SECRET", secret_val)
        obs = _make_obs(polarizations=[Polarization.VV])
        with pytest.raises(ValidationError) as exc_info:
            ImageryRequest(
                observation=obs,
                bbox=_BBOX,
                time_range=_TIME,
                requested_bands=[Polarization.HH],
            )
        assert secret_val not in str(exc_info.value)

    def test_no_secrets_in_logs(self, caplog):
        """Building request must not log secrets or tokens."""
        import logging
        with caplog.at_level(logging.DEBUG):
            req = _make_request()
            ProcessRequestBuilder.build(req)
        assert "secret" not in caplog.text.lower()
        assert "token" not in caplog.text.lower()


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Boundary and edge cases for the builder."""

    def test_minimum_pixel_dimensions(self):
        req = _make_request(output=OutputConfig(width=1, height=1))
        payload = ProcessRequestBuilder.build(req)
        assert payload["output"]["width"] == 1
        assert payload["output"]["height"] == 1

    def test_maximum_pixel_dimensions(self):
        req = _make_request(output=OutputConfig(width=2500, height=2500))
        payload = ProcessRequestBuilder.build(req)
        assert payload["output"]["width"] == 2500

    def test_custom_crs_in_bounds(self):
        req = _make_request(output=OutputConfig(width=64, height=64, crs_epsg=32632))
        payload = ProcessRequestBuilder.build(req)
        assert "32632" in payload["input"]["bounds"]["properties"]["crs"]

    def test_builder_does_not_mutate_request(self):
        """Builder must not modify the input request object."""
        req = _make_request()
        original_bands = list(req.requested_bands)
        ProcessRequestBuilder.build(req)
        assert req.requested_bands == original_bands

    def test_very_small_bbox(self):
        """Very small (but non-degenerate) bbox should produce valid payload."""
        bbox = BoundingBox(west=15.0, south=40.0, east=15.001, north=40.001)
        req = ImageryRequest(
            observation=_make_obs(),
            bbox=bbox,
            time_range=_TIME,
            requested_bands=[Polarization.VV],
        )
        payload = ProcessRequestBuilder.build(req)
        assert payload["input"]["bounds"]["bbox"] == [15.0, 40.0, 15.001, 40.001]
