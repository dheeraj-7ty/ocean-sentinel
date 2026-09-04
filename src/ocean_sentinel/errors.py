"""Error model for the Ocean Sentinel satellite subsystem.

Provides clear, actionable error types for the satellite data pipeline.
Each error carries a machine-readable code and a human-readable message.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional


class SatelliteErrorCode(str, Enum):
    """Machine-readable error codes for the satellite subsystem."""

    # Request validation
    INVALID_AOI = "INVALID_AOI"
    INVALID_TIME_RANGE = "INVALID_TIME_RANGE"
    INVALID_REQUEST = "INVALID_REQUEST"

    # Authentication / Authorization
    AUTH_FAILURE = "AUTH_FAILURE"
    AUTH_EXPIRED = "AUTH_EXPIRED"
    AUTHORIZATION_DENIED = "AUTHORIZATION_DENIED"

    # Discovery
    NO_OBSERVATIONS = "NO_OBSERVATIONS"
    UNSUPPORTED_PRODUCT = "UNSUPPORTED_PRODUCT"

    # Provider
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
    PROVIDER_INVALID_RESPONSE = "PROVIDER_INVALID_RESPONSE"
    PROVIDER_RATE_LIMITED = "PROVIDER_RATE_LIMITED"

    # Processing
    PROCESSING_FAILURE = "PROCESSING_FAILURE"
    RASTER_VALIDATION_FAILURE = "RASTER_VALIDATION_FAILURE"

    # Configuration
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"


class SatelliteError(Exception):
    """Base exception for the satellite subsystem.

    All satellite-related errors should inherit from this class
    to enable consistent error handling at the API layer.
    """

    def __init__(
        self,
        code: SatelliteErrorCode,
        message: str,
        *,
        details: Optional[dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        self.cause = cause
        super().__init__(f"[{code.value}] {message}")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dict safe for API responses.

        Never includes internal exception details or credentials.
        """
        result: dict[str, Any] = {
            "error": self.code.value,
            "message": self.message,
        }
        # Only include details that are explicitly safe
        safe_details = {
            k: v for k, v in self.details.items()
            if k not in ("token", "secret", "password", "credentials")
        }
        if safe_details:
            result["details"] = safe_details
        return result


# ---------------------------------------------------------------------------
# Convenience subclasses
# ---------------------------------------------------------------------------


class InvalidAOIError(SatelliteError):
    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(SatelliteErrorCode.INVALID_AOI, message, **kwargs)


class InvalidRequestError(SatelliteError):
    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(SatelliteErrorCode.INVALID_REQUEST, message, **kwargs)


class UnsupportedBandError(SatelliteError):
    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(SatelliteErrorCode.UNSUPPORTED_PRODUCT, message, **kwargs)


class InvalidTimeRangeError(SatelliteError):
    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(SatelliteErrorCode.INVALID_TIME_RANGE, message, **kwargs)


class AuthenticationError(SatelliteError):
    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(SatelliteErrorCode.AUTH_FAILURE, message, **kwargs)


class AuthorizationError(SatelliteError):
    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(SatelliteErrorCode.AUTHORIZATION_DENIED, message, **kwargs)


class NoObservationsError(SatelliteError):
    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(SatelliteErrorCode.NO_OBSERVATIONS, message, **kwargs)


class ProviderUnavailableError(SatelliteError):
    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(SatelliteErrorCode.PROVIDER_UNAVAILABLE, message, **kwargs)


class ProviderTimeoutError(SatelliteError):
    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(SatelliteErrorCode.PROVIDER_TIMEOUT, message, **kwargs)


class ProviderInvalidResponseError(SatelliteError):
    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(SatelliteErrorCode.PROVIDER_INVALID_RESPONSE, message, **kwargs)


class ProviderRateLimitedError(SatelliteError):
    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(SatelliteErrorCode.PROVIDER_RATE_LIMITED, message, **kwargs)


class ProcessingError(SatelliteError):
    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(SatelliteErrorCode.PROCESSING_FAILURE, message, **kwargs)


class RasterValidationError(SatelliteError):
    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(SatelliteErrorCode.RASTER_VALIDATION_FAILURE, message, **kwargs)


class ConfigurationError(SatelliteError):
    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(SatelliteErrorCode.CONFIGURATION_ERROR, message, **kwargs)
