"""Tests for the error model.

Verifies:
- Error codes are properly set
- Error serialization doesn't expose secrets
- Error hierarchy works correctly
"""

import pytest

from ocean_sentinel.errors import (
    AuthenticationError,
    ConfigurationError,
    InvalidAOIError,
    InvalidTimeRangeError,
    NoObservationsError,
    ProcessingError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    SatelliteError,
    SatelliteErrorCode,
)


class TestSatelliteError:
    """Tests for the base SatelliteError."""

    def test_error_code_and_message(self):
        err = SatelliteError(SatelliteErrorCode.INVALID_AOI, "Bad area")
        assert err.code == SatelliteErrorCode.INVALID_AOI
        assert err.message == "Bad area"
        assert "INVALID_AOI" in str(err)

    def test_to_dict(self):
        err = SatelliteError(
            SatelliteErrorCode.AUTH_FAILURE,
            "Auth failed",
            details={"status_code": 401},
        )
        d = err.to_dict()
        assert d["error"] == "AUTH_FAILURE"
        assert d["message"] == "Auth failed"
        assert d["details"]["status_code"] == 401

    def test_to_dict_filters_secrets(self):
        err = SatelliteError(
            SatelliteErrorCode.AUTH_FAILURE,
            "Auth failed",
            details={
                "status_code": 401,
                "token": "SHOULD_NOT_APPEAR",
                "secret": "SHOULD_NOT_APPEAR",
                "credentials": "SHOULD_NOT_APPEAR",
            },
        )
        d = err.to_dict()
        assert "token" not in d.get("details", {})
        assert "secret" not in d.get("details", {})
        assert "credentials" not in d.get("details", {})
        assert d["details"]["status_code"] == 401

    def test_cause_preserved(self):
        original = ValueError("original error")
        err = SatelliteError(
            SatelliteErrorCode.PROCESSING_FAILURE,
            "Processing failed",
            cause=original,
        )
        assert err.cause is original


class TestErrorSubclasses:
    """Tests for convenience error subclasses."""

    def test_invalid_aoi_error(self):
        err = InvalidAOIError("Latitude out of range")
        assert err.code == SatelliteErrorCode.INVALID_AOI
        assert isinstance(err, SatelliteError)

    def test_invalid_time_range_error(self):
        err = InvalidTimeRangeError("End before start")
        assert err.code == SatelliteErrorCode.INVALID_TIME_RANGE

    def test_authentication_error(self):
        err = AuthenticationError("Token expired")
        assert err.code == SatelliteErrorCode.AUTH_FAILURE

    def test_no_observations_error(self):
        err = NoObservationsError("No data for AOI")
        assert err.code == SatelliteErrorCode.NO_OBSERVATIONS

    def test_provider_unavailable_error(self):
        err = ProviderUnavailableError("Service down")
        assert err.code == SatelliteErrorCode.PROVIDER_UNAVAILABLE

    def test_provider_timeout_error(self):
        err = ProviderTimeoutError("Request timed out")
        assert err.code == SatelliteErrorCode.PROVIDER_TIMEOUT

    def test_processing_error(self):
        err = ProcessingError("Raster corrupt")
        assert err.code == SatelliteErrorCode.PROCESSING_FAILURE

    def test_configuration_error(self):
        err = ConfigurationError("Missing client_id")
        assert err.code == SatelliteErrorCode.CONFIGURATION_ERROR

    def test_all_errors_are_satellite_errors(self):
        """All subclasses must be catchable as SatelliteError."""
        errors = [
            InvalidAOIError("test"),
            InvalidTimeRangeError("test"),
            AuthenticationError("test"),
            NoObservationsError("test"),
            ProviderUnavailableError("test"),
            ProviderTimeoutError("test"),
            ProcessingError("test"),
            ConfigurationError("test"),
        ]
        for err in errors:
            assert isinstance(err, SatelliteError)
            assert isinstance(err, Exception)
