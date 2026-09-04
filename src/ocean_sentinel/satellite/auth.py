"""Copernicus Sentinel Hub OAuth2 authentication.

Implements the Client Credentials flow for the Copernicus Data Space
Sentinel Hub services.

Token endpoint:
    https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token

Grant type: client_credentials

Security:
    - Credentials are never logged or serialized
    - Tokens are cached and reused until near expiry
    - Token values are never included in error messages
    - Authorization headers are never logged
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional

import httpx

from ocean_sentinel.config import CopernicusSettings
from ocean_sentinel.errors import AuthenticationError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TokenInfo:
    """Represents an OAuth2 access token with associated metadata.

    The access_token is deliberately excluded from __repr__ to prevent
    accidental exposure in logs, tracebacks, or serialized output.
    """

    access_token: str
    token_type: str
    expires_in: int
    scope: str
    acquired_at: float  # time.time() when token was obtained

    @property
    def expires_at(self) -> float:
        """Absolute expiry time (seconds since epoch)."""
        return self.acquired_at + self.expires_in

    def is_valid(self, margin_seconds: int = 60) -> bool:
        """Check if token is still usable (with safety margin)."""
        return time.time() < (self.expires_at - margin_seconds)

    def __repr__(self) -> str:
        """Safe repr that never exposes the access token."""
        return (
            f"TokenInfo(token_type={self.token_type!r}, "
            f"expires_in={self.expires_in}, "
            f"scope={self.scope!r}, "
            f"access_token=****)"
        )

    def __str__(self) -> str:
        return self.__repr__()


class TokenManager:
    """Manages OAuth2 access tokens for Sentinel Hub.

    Caches the token and only refreshes when the token is about to expire.
    Thread-safety note: current implementation is single-threaded.

    Usage::

        settings = CopernicusSettings()
        tm = TokenManager(settings)

        # Get a raw token string (for Authorization headers)
        token = await tm.get_token()

        # Get full token metadata
        info = await tm.get_token_info()
    """

    def __init__(self, settings: CopernicusSettings) -> None:
        self._settings = settings
        self._token_info: Optional[TokenInfo] = None

    @property
    def has_valid_token(self) -> bool:
        """Check if a cached token is still valid."""
        if self._token_info is None:
            return False
        return self._token_info.is_valid(self._settings.token_refresh_margin_seconds)

    async def get_token(self) -> str:
        """Return a valid access token string, refreshing if necessary.

        This is the primary interface for callers that just need
        the token value for an Authorization header.

        Raises:
            AuthenticationError: If token acquisition fails.
        """
        info = await self.get_token_info()
        return info.access_token

    async def get_token_info(self) -> TokenInfo:
        """Return full token metadata, refreshing if necessary.

        Raises:
            AuthenticationError: If token acquisition fails.
        """
        if self.has_valid_token:
            return self._token_info  # type: ignore[return-value]

        self._token_info = await self._request_token()
        return self._token_info

    async def _request_token(self) -> TokenInfo:
        """Execute the OAuth2 Client Credentials token request.

        Raises:
            AuthenticationError: On any failure — with safe messages
                that never include credentials or tokens.
        """
        logger.info("Requesting new Sentinel Hub access token")

        token_data = await self._execute_token_request()
        return self._parse_token_response(token_data)

    async def _execute_token_request(self) -> dict:
        """Send the HTTP POST to the token endpoint.

        Returns the parsed JSON response body.

        Raises:
            AuthenticationError: On HTTP, network, or parse failures.
        """
        try:
            async with httpx.AsyncClient(
                timeout=self._settings.http_timeout_seconds,
            ) as client:
                response = await client.post(
                    self._settings.copernicus_token_url,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self._settings.copernicus_client_id.get_secret_value(),
                        "client_secret": self._settings.copernicus_client_secret.get_secret_value(),
                    },
                )
                response.raise_for_status()

        except httpx.TimeoutException as e:
            raise AuthenticationError(
                "Token request timed out",
                details={"timeout_seconds": self._settings.http_timeout_seconds},
                cause=e,
            ) from e
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            # Differentiate credential failures from server errors
            if status in (401, 403):
                msg = "Copernicus authentication failed: invalid client credentials"
            elif 400 <= status < 500:
                msg = f"Token request rejected by server (HTTP {status})"
            else:
                msg = f"Token endpoint returned server error (HTTP {status})"
            # Never include response body — may contain token/credential info
            raise AuthenticationError(
                msg,
                details={"status_code": status},
                cause=e,
            ) from e
        except httpx.HTTPError as e:
            raise AuthenticationError(
                "Token request failed due to network error",
                cause=e,
            ) from e

        # Parse JSON — handle malformed responses
        try:
            token_data = response.json()
        except Exception as e:
            raise AuthenticationError(
                "Token endpoint returned invalid JSON",
                cause=e,
            ) from e

        if not isinstance(token_data, dict):
            raise AuthenticationError(
                "Token endpoint returned unexpected response format",
            )

        return token_data

    def _parse_token_response(self, token_data: dict) -> TokenInfo:
        """Extract and validate token fields from the parsed response.

        Raises:
            AuthenticationError: If required fields are missing.
        """
        if "access_token" not in token_data:
            raise AuthenticationError(
                "Token response missing access_token field",
            )

        access_token = token_data["access_token"]
        if not isinstance(access_token, str) or not access_token:
            raise AuthenticationError(
                "Token response contains invalid access_token",
            )

        expires_in = token_data.get("expires_in", 600)
        if not isinstance(expires_in, (int, float)):
            expires_in = 600

        info = TokenInfo(
            access_token=access_token,
            token_type=token_data.get("token_type", "Bearer"),
            expires_in=int(expires_in),
            scope=token_data.get("scope", ""),
            acquired_at=time.time(),
        )

        logger.info(
            "Access token acquired, expires in %d seconds",
            info.expires_in,
        )
        return info

    def invalidate(self) -> None:
        """Force token refresh on next request."""
        self._token_info = None
