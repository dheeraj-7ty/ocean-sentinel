"""Tests for Copernicus Sentinel Hub OAuth2 authentication.

Covers:
- Successful token acquisition
- Invalid credentials (401/403)
- HTTP client errors (4xx)
- HTTP server errors (5xx)
- Network / connection failures
- Timeout failures
- Malformed JSON responses
- Missing access_token in response
- Invalid access_token value
- Token expiry metadata handling
- Token caching / reuse
- Token invalidation
- Request construction verification
- Security: no credential/token leakage in errors or repr

All tests use mocked HTTP — no real Copernicus contact.
No real credentials are used.
"""

from __future__ import annotations

import json
import logging
import time
from unittest.mock import patch

import httpx
import pytest
import respx

from ocean_sentinel.config import CopernicusSettings
from ocean_sentinel.errors import AuthenticationError, SatelliteErrorCode
from ocean_sentinel.satellite.auth import TokenInfo, TokenManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"

MOCK_TOKEN_RESPONSE = {
    "access_token": "mock-access-token-value-for-testing",
    "token_type": "Bearer",
    "expires_in": 600,
    "scope": "",
}


@pytest.fixture
def settings(monkeypatch) -> CopernicusSettings:
    """Provide test settings with fake credentials."""
    monkeypatch.setenv("COPERNICUS_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("COPERNICUS_CLIENT_SECRET", "test-client-secret")
    return CopernicusSettings()


@pytest.fixture
def token_manager(settings) -> TokenManager:
    """Provide a TokenManager using test settings."""
    return TokenManager(settings)


# ---------------------------------------------------------------------------
# TokenInfo unit tests
# ---------------------------------------------------------------------------


class TestTokenInfo:
    """Tests for the TokenInfo dataclass."""

    def test_is_valid_when_fresh(self):
        """A freshly acquired token should be valid."""
        info = TokenInfo(
            access_token="test",
            token_type="Bearer",
            expires_in=600,
            scope="",
            acquired_at=time.time(),
        )
        assert info.is_valid(margin_seconds=60)

    def test_is_invalid_when_expired(self):
        """An expired token should not be valid."""
        info = TokenInfo(
            access_token="test",
            token_type="Bearer",
            expires_in=600,
            scope="",
            acquired_at=time.time() - 700,  # Acquired 700s ago, expires_in=600
        )
        assert not info.is_valid(margin_seconds=60)

    def test_is_invalid_within_margin(self):
        """A token within the margin window should not be valid."""
        info = TokenInfo(
            access_token="test",
            token_type="Bearer",
            expires_in=600,
            scope="",
            acquired_at=time.time() - 550,  # 50s left < 60s margin
        )
        assert not info.is_valid(margin_seconds=60)

    def test_expires_at_property(self):
        """expires_at should be acquired_at + expires_in."""
        now = time.time()
        info = TokenInfo(
            access_token="test",
            token_type="Bearer",
            expires_in=600,
            scope="",
            acquired_at=now,
        )
        assert info.expires_at == pytest.approx(now + 600, abs=1)

    def test_repr_hides_token(self):
        """repr must never expose the access token value."""
        info = TokenInfo(
            access_token="super-secret-token-value",
            token_type="Bearer",
            expires_in=600,
            scope="openid",
            acquired_at=time.time(),
        )
        repr_str = repr(info)
        assert "super-secret-token-value" not in repr_str
        assert "****" in repr_str
        assert "Bearer" in repr_str

    def test_str_hides_token(self):
        """str() must never expose the access token value."""
        info = TokenInfo(
            access_token="super-secret-token-value",
            token_type="Bearer",
            expires_in=600,
            scope="",
            acquired_at=time.time(),
        )
        assert "super-secret-token-value" not in str(info)

    def test_frozen_dataclass(self):
        """TokenInfo should be immutable."""
        info = TokenInfo(
            access_token="test",
            token_type="Bearer",
            expires_in=600,
            scope="",
            acquired_at=time.time(),
        )
        with pytest.raises(AttributeError):
            info.access_token = "modified"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# TokenManager — successful authentication
# ---------------------------------------------------------------------------


class TestTokenManagerSuccess:
    """Tests for successful token acquisition."""

    @respx.mock
    async def test_successful_token_request(self, token_manager):
        """Should return token string on successful auth."""
        respx.post(TOKEN_URL).mock(
            return_value=httpx.Response(200, json=MOCK_TOKEN_RESPONSE)
        )

        token = await token_manager.get_token()

        assert token == "mock-access-token-value-for-testing"

    @respx.mock
    async def test_successful_token_info(self, token_manager):
        """Should return TokenInfo with full metadata."""
        respx.post(TOKEN_URL).mock(
            return_value=httpx.Response(200, json=MOCK_TOKEN_RESPONSE)
        )

        info = await token_manager.get_token_info()

        assert isinstance(info, TokenInfo)
        assert info.access_token == "mock-access-token-value-for-testing"
        assert info.token_type == "Bearer"
        assert info.expires_in == 600
        assert info.scope == ""
        assert info.is_valid(margin_seconds=60)

    @respx.mock
    async def test_correct_request_construction(self, token_manager, settings):
        """Must send correct grant_type, client_id, client_secret."""
        route = respx.post(TOKEN_URL).mock(
            return_value=httpx.Response(200, json=MOCK_TOKEN_RESPONSE)
        )

        await token_manager.get_token()

        assert route.called
        request = route.calls.last.request
        # Decode form body
        body = request.content.decode("utf-8")
        assert "grant_type=client_credentials" in body
        assert "client_id=test-client-id" in body
        assert "client_secret=test-client-secret" in body

    @respx.mock
    async def test_token_with_scope(self, token_manager):
        """Should preserve scope from response."""
        response_data = {**MOCK_TOKEN_RESPONSE, "scope": "openid email"}
        respx.post(TOKEN_URL).mock(
            return_value=httpx.Response(200, json=response_data)
        )

        info = await token_manager.get_token_info()

        assert info.scope == "openid email"

    @respx.mock
    async def test_token_with_custom_expiry(self, token_manager):
        """Should use expires_in from response."""
        response_data = {**MOCK_TOKEN_RESPONSE, "expires_in": 300}
        respx.post(TOKEN_URL).mock(
            return_value=httpx.Response(200, json=response_data)
        )

        info = await token_manager.get_token_info()

        assert info.expires_in == 300


# ---------------------------------------------------------------------------
# TokenManager — caching
# ---------------------------------------------------------------------------


class TestTokenManagerCaching:
    """Tests for token caching behavior."""

    @respx.mock
    async def test_cached_token_reused(self, token_manager):
        """Second call should reuse cached token, not make another request."""
        route = respx.post(TOKEN_URL).mock(
            return_value=httpx.Response(200, json=MOCK_TOKEN_RESPONSE)
        )

        token1 = await token_manager.get_token()
        token2 = await token_manager.get_token()

        assert token1 == token2
        assert route.call_count == 1  # Only one HTTP request

    @respx.mock
    async def test_expired_token_refreshed(self, token_manager):
        """Should request a new token when the cached one is expired."""
        route = respx.post(TOKEN_URL).mock(
            return_value=httpx.Response(200, json=MOCK_TOKEN_RESPONSE)
        )

        # First request
        await token_manager.get_token()
        assert route.call_count == 1

        # Simulate expiry by patching the cached token's acquired_at
        token_manager._token_info = TokenInfo(
            access_token="old-token",
            token_type="Bearer",
            expires_in=600,
            scope="",
            acquired_at=time.time() - 700,  # Expired
        )

        # Second request should refresh
        token = await token_manager.get_token()
        assert route.call_count == 2
        assert token == "mock-access-token-value-for-testing"

    @respx.mock
    async def test_invalidate_forces_refresh(self, token_manager):
        """invalidate() should force a new token request."""
        route = respx.post(TOKEN_URL).mock(
            return_value=httpx.Response(200, json=MOCK_TOKEN_RESPONSE)
        )

        await token_manager.get_token()
        assert route.call_count == 1

        token_manager.invalidate()
        assert not token_manager.has_valid_token

        await token_manager.get_token()
        assert route.call_count == 2

    def test_has_valid_token_initially_false(self, token_manager):
        """Before any request, has_valid_token should be False."""
        assert not token_manager.has_valid_token


# ---------------------------------------------------------------------------
# TokenManager — authentication failures
# ---------------------------------------------------------------------------


class TestTokenManagerAuthFailures:
    """Tests for credential / authorization failures."""

    @respx.mock
    async def test_invalid_credentials_401(self, token_manager):
        """HTTP 401 should raise AuthenticationError with credential message."""
        respx.post(TOKEN_URL).mock(
            return_value=httpx.Response(
                401,
                json={"error": "unauthorized_client"},
            )
        )

        with pytest.raises(AuthenticationError, match="invalid client credentials") as exc_info:
            await token_manager.get_token()

        assert exc_info.value.code == SatelliteErrorCode.AUTH_FAILURE
        assert exc_info.value.details["status_code"] == 401

    @respx.mock
    async def test_forbidden_403(self, token_manager):
        """HTTP 403 should raise AuthenticationError with credential message."""
        respx.post(TOKEN_URL).mock(
            return_value=httpx.Response(403, json={"error": "access_denied"})
        )

        with pytest.raises(AuthenticationError, match="invalid client credentials"):
            await token_manager.get_token()

    @respx.mock
    async def test_bad_request_400(self, token_manager):
        """HTTP 400 should raise with 'rejected' message."""
        respx.post(TOKEN_URL).mock(
            return_value=httpx.Response(400, json={"error": "invalid_request"})
        )

        with pytest.raises(AuthenticationError, match="rejected by server"):
            await token_manager.get_token()


# ---------------------------------------------------------------------------
# TokenManager — HTTP server errors
# ---------------------------------------------------------------------------


class TestTokenManagerServerErrors:
    """Tests for HTTP 5xx server errors."""

    @respx.mock
    async def test_server_error_500(self, token_manager):
        """HTTP 500 should raise AuthenticationError with server error message."""
        respx.post(TOKEN_URL).mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )

        with pytest.raises(AuthenticationError, match="server error") as exc_info:
            await token_manager.get_token()

        assert exc_info.value.details["status_code"] == 500

    @respx.mock
    async def test_service_unavailable_503(self, token_manager):
        """HTTP 503 should raise AuthenticationError."""
        respx.post(TOKEN_URL).mock(
            return_value=httpx.Response(503, text="Service Unavailable")
        )

        with pytest.raises(AuthenticationError, match="server error"):
            await token_manager.get_token()


# ---------------------------------------------------------------------------
# TokenManager — network / connection failures
# ---------------------------------------------------------------------------


class TestTokenManagerNetworkErrors:
    """Tests for network-level failures."""

    @respx.mock
    async def test_connection_error(self, token_manager):
        """Network connection failure should raise AuthenticationError."""
        respx.post(TOKEN_URL).mock(side_effect=httpx.ConnectError("Connection refused"))

        with pytest.raises(AuthenticationError, match="network error"):
            await token_manager.get_token()

    @respx.mock
    async def test_timeout(self, token_manager):
        """Request timeout should raise AuthenticationError."""
        respx.post(TOKEN_URL).mock(side_effect=httpx.ReadTimeout("Read timed out"))

        with pytest.raises(AuthenticationError, match="timed out"):
            await token_manager.get_token()

    @respx.mock
    async def test_dns_failure(self, token_manager):
        """DNS resolution failure should raise AuthenticationError."""
        respx.post(TOKEN_URL).mock(
            side_effect=httpx.ConnectError("Name or service not known")
        )

        with pytest.raises(AuthenticationError, match="network error"):
            await token_manager.get_token()


# ---------------------------------------------------------------------------
# TokenManager — malformed responses
# ---------------------------------------------------------------------------


class TestTokenManagerMalformedResponses:
    """Tests for malformed / unexpected responses."""

    @respx.mock
    async def test_malformed_json(self, token_manager):
        """Non-JSON response should raise AuthenticationError."""
        respx.post(TOKEN_URL).mock(
            return_value=httpx.Response(
                200,
                content=b"<html>Not JSON</html>",
                headers={"Content-Type": "text/html"},
            )
        )

        with pytest.raises(AuthenticationError, match="invalid JSON"):
            await token_manager.get_token()

    @respx.mock
    async def test_missing_access_token_field(self, token_manager):
        """Response without access_token should raise AuthenticationError."""
        respx.post(TOKEN_URL).mock(
            return_value=httpx.Response(
                200,
                json={"token_type": "Bearer", "expires_in": 600},
            )
        )

        with pytest.raises(AuthenticationError, match="missing access_token"):
            await token_manager.get_token()

    @respx.mock
    async def test_empty_access_token(self, token_manager):
        """Empty access_token string should raise AuthenticationError."""
        respx.post(TOKEN_URL).mock(
            return_value=httpx.Response(
                200,
                json={**MOCK_TOKEN_RESPONSE, "access_token": ""},
            )
        )

        with pytest.raises(AuthenticationError, match="invalid access_token"):
            await token_manager.get_token()

    @respx.mock
    async def test_null_access_token(self, token_manager):
        """null access_token should raise AuthenticationError."""
        respx.post(TOKEN_URL).mock(
            return_value=httpx.Response(
                200,
                json={**MOCK_TOKEN_RESPONSE, "access_token": None},
            )
        )

        with pytest.raises(AuthenticationError, match="invalid access_token"):
            await token_manager.get_token()

    @respx.mock
    async def test_response_is_json_array(self, token_manager):
        """JSON array response should raise AuthenticationError."""
        respx.post(TOKEN_URL).mock(
            return_value=httpx.Response(200, json=["unexpected", "array"])
        )

        with pytest.raises(AuthenticationError, match="unexpected response format"):
            await token_manager.get_token()

    @respx.mock
    async def test_missing_expires_in_defaults(self, token_manager):
        """Missing expires_in should default to 600."""
        response_data = {"access_token": "test-token", "token_type": "Bearer"}
        respx.post(TOKEN_URL).mock(
            return_value=httpx.Response(200, json=response_data)
        )

        info = await token_manager.get_token_info()

        assert info.expires_in == 600

    @respx.mock
    async def test_non_numeric_expires_in_defaults(self, token_manager):
        """Non-numeric expires_in should default to 600."""
        response_data = {
            **MOCK_TOKEN_RESPONSE,
            "expires_in": "not-a-number",
        }
        respx.post(TOKEN_URL).mock(
            return_value=httpx.Response(200, json=response_data)
        )

        info = await token_manager.get_token_info()

        assert info.expires_in == 600


# ---------------------------------------------------------------------------
# TokenManager — missing configuration
# ---------------------------------------------------------------------------


class TestTokenManagerConfiguration:
    """Tests for configuration issues."""

    def test_missing_client_id(self, monkeypatch):
        """Missing client_id should prevent settings construction."""
        monkeypatch.setenv("COPERNICUS_CLIENT_SECRET", "test-secret")
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="copernicus_client_id"):
            CopernicusSettings()

    def test_missing_client_secret(self, monkeypatch):
        """Missing client_secret should prevent settings construction."""
        monkeypatch.setenv("COPERNICUS_CLIENT_ID", "test-id")
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="copernicus_client_secret"):
            CopernicusSettings()


# ---------------------------------------------------------------------------
# Security: credential / token non-leakage
# ---------------------------------------------------------------------------


class TestTokenManagerSecurity:
    """Verify that secrets are never exposed in errors, logs, or repr."""

    @respx.mock
    async def test_credentials_not_in_auth_error_message(self, token_manager):
        """Credential values must not appear in error messages."""
        respx.post(TOKEN_URL).mock(
            return_value=httpx.Response(401, json={"error": "unauthorized"})
        )

        with pytest.raises(AuthenticationError) as exc_info:
            await token_manager.get_token()

        error_str = str(exc_info.value)
        assert "test-client-id" not in error_str
        assert "test-client-secret" not in error_str

    @respx.mock
    async def test_credentials_not_in_error_dict(self, token_manager):
        """Credential values must not appear in to_dict() output."""
        respx.post(TOKEN_URL).mock(
            return_value=httpx.Response(401, json={"error": "unauthorized"})
        )

        with pytest.raises(AuthenticationError) as exc_info:
            await token_manager.get_token()

        error_dict = exc_info.value.to_dict()
        dict_str = json.dumps(error_dict)
        assert "test-client-id" not in dict_str
        assert "test-client-secret" not in dict_str

    @respx.mock
    async def test_token_not_in_log_output(self, token_manager, caplog):
        """Access token must not appear in log messages."""
        respx.post(TOKEN_URL).mock(
            return_value=httpx.Response(200, json=MOCK_TOKEN_RESPONSE)
        )

        with caplog.at_level(logging.DEBUG, logger="ocean_sentinel.satellite.auth"):
            await token_manager.get_token()

        log_text = caplog.text
        assert "mock-access-token-value-for-testing" not in log_text

    @respx.mock
    async def test_token_not_in_error_on_network_failure(self, token_manager):
        """If token was cached and then a network error occurs, cached token
        value must not appear in the error."""
        # First: acquire a token
        respx.post(TOKEN_URL).mock(
            return_value=httpx.Response(200, json=MOCK_TOKEN_RESPONSE)
        )
        await token_manager.get_token()

        # Force invalidation and simulate network error
        token_manager.invalidate()
        respx.post(TOKEN_URL).mock(side_effect=httpx.ConnectError("refused"))

        with pytest.raises(AuthenticationError) as exc_info:
            await token_manager.get_token()

        assert "mock-access-token-value-for-testing" not in str(exc_info.value)
