"""Tests for the error model.

Verifies:
- Error codes are properly set
- Error serialization doesn't expose secrets
- Error hierarchy works correctly
"""

from ocean_sentinel.errors import (
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
    InvalidAOIError,
    InvalidRequestError,
    InvalidTimeRangeError,
    NoObservationsError,
    PreprocessingError,
    ProcessingError,
    ProviderInvalidResponseError,
    ProviderRateLimitedError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    RasterValidationError,
    SatelliteError,
    SatelliteErrorCode,
    UnsupportedBandError,
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

    def test_invalid_request_error(self):
        err = InvalidRequestError("Invalid request params")
        assert err.code == SatelliteErrorCode.INVALID_REQUEST
        assert isinstance(err, SatelliteError)

    def test_unsupported_band_error(self):
        err = UnsupportedBandError("Requested band HH not in observation")
        assert err.code == SatelliteErrorCode.UNSUPPORTED_PRODUCT
        assert isinstance(err, SatelliteError)

    def test_invalid_time_range_error(self):
        err = InvalidTimeRangeError("End before start")
        assert err.code == SatelliteErrorCode.INVALID_TIME_RANGE

    def test_authentication_error(self):
        err = AuthenticationError("Token expired")
        assert err.code == SatelliteErrorCode.AUTH_FAILURE

    def test_authorization_error(self):
        err = AuthorizationError("Access denied")
        assert err.code == SatelliteErrorCode.AUTHORIZATION_DENIED

    def test_no_observations_error(self):
        err = NoObservationsError("No data for AOI")
        assert err.code == SatelliteErrorCode.NO_OBSERVATIONS

    def test_provider_unavailable_error(self):
        err = ProviderUnavailableError("Service down")
        assert err.code == SatelliteErrorCode.PROVIDER_UNAVAILABLE

    def test_provider_timeout_error(self):
        err = ProviderTimeoutError("Request timed out")
        assert err.code == SatelliteErrorCode.PROVIDER_TIMEOUT

    def test_provider_invalid_response_error(self):
        err = ProviderInvalidResponseError("Bad JSON")
        assert err.code == SatelliteErrorCode.PROVIDER_INVALID_RESPONSE

    def test_provider_rate_limited_error(self):
        err = ProviderRateLimitedError("Rate limit exceeded")
        assert err.code == SatelliteErrorCode.PROVIDER_RATE_LIMITED

    def test_processing_error(self):
        err = ProcessingError("Raster corrupt")
        assert err.code == SatelliteErrorCode.PROCESSING_FAILURE

    def test_preprocessing_error(self):
        err = PreprocessingError("Preprocessing failure")
        assert err.code == SatelliteErrorCode.PROCESSING_FAILURE
        assert isinstance(err, SatelliteError)

    def test_raster_validation_error(self):
        err = RasterValidationError("Corrupt GeoTIFF")
        assert err.code == SatelliteErrorCode.RASTER_VALIDATION_FAILURE
        assert isinstance(err, SatelliteError)

    def test_configuration_error(self):
        err = ConfigurationError("Missing client_id")
        assert err.code == SatelliteErrorCode.CONFIGURATION_ERROR

    def test_all_errors_are_satellite_errors(self):
        """All subclasses must be catchable as SatelliteError."""
        errors = [
            InvalidAOIError("test"),
            InvalidRequestError("test"),
            UnsupportedBandError("test"),
            InvalidTimeRangeError("test"),
            AuthenticationError("test"),
            AuthorizationError("test"),
            NoObservationsError("test"),
            ProviderUnavailableError("test"),
            ProviderTimeoutError("test"),
            ProviderInvalidResponseError("test"),
            ProviderRateLimitedError("test"),
            ProcessingError("test"),
            PreprocessingError("test"),
            RasterValidationError("test"),
            ConfigurationError("test"),
        ]
        for err in errors:
            assert isinstance(err, SatelliteError)
            assert isinstance(err, Exception)
