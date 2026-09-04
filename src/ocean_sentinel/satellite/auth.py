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
"""

from __future__ import annotations

import logging
import time
from typing import Optional

import httpx

from ocean_sentinel.config import CopernicusSettings
from ocean_sentinel.errors import AuthenticationError

logger = logging.getLogger(__name__)


class TokenManager:
    """Manages OAuth2 access tokens for Sentinel Hub.

    Caches the token and only refreshes when the token is about to expire.
    Thread-safety note: current implementation is single-threaded.
    """

    def __init__(self, settings: CopernicusSettings) -> None:
        self._settings = settings
        self._access_token: Optional[str] = None
        self._expires_at: float = 0.0

    @property
    def is_token_valid(self) -> bool:
        """Check if current token is still valid (with margin)."""
        if self._access_token is None:
            return False
        margin = self._settings.token_refresh_margin_seconds
        return time.time() < (self._expires_at - margin)

    async def get_token(self) -> str:
        """Return a valid access token, refreshing if necessary.

        Raises:
            AuthenticationError: If token acquisition fails.
        """
        if self.is_token_valid:
            return self._access_token  # type: ignore[return-value]

        logger.info("Requesting new Sentinel Hub access token")
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
                token_data = response.json()

        except httpx.TimeoutException as e:
            raise AuthenticationError(
                "Token request timed out",
                cause=e,
            ) from e
        except httpx.HTTPStatusError as e:
            # Never include the response body in errors (may contain token info)
            raise AuthenticationError(
                f"Token request failed with status {e.response.status_code}",
                details={"status_code": e.response.status_code},
                cause=e,
            ) from e
        except httpx.HTTPError as e:
            raise AuthenticationError(
                "Token request failed due to network error",
                cause=e,
            ) from e

        if "access_token" not in token_data:
            raise AuthenticationError(
                "Token response missing access_token field",
            )

        self._access_token = token_data["access_token"]
        expires_in = token_data.get("expires_in", 600)
        self._expires_at = time.time() + expires_in

        logger.info("Access token acquired, expires in %d seconds", expires_in)
        return self._access_token

    def invalidate(self) -> None:
        """Force token refresh on next request."""
        self._access_token = None
        self._expires_at = 0.0
