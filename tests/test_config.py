"""Tests for configuration management.

Verifies:
- Missing configuration is properly detected
- Valid configuration loads correctly
- Invalid configuration is rejected
- Secrets are never exposed
"""

import os

import pytest
from pydantic import ValidationError

from ocean_sentinel.config import CopernicusSettings


class TestMissingConfiguration:
    """Tests for missing required configuration."""

    def test_missing_client_id_raises(self, monkeypatch):
        """Must fail if COPERNICUS_CLIENT_ID is not set."""
        monkeypatch.setenv("COPERNICUS_CLIENT_SECRET", "test-secret")
        with pytest.raises(ValidationError, match="copernicus_client_id"):
            CopernicusSettings()

    def test_missing_client_secret_raises(self, monkeypatch):
        """Must fail if COPERNICUS_CLIENT_SECRET is not set."""
        monkeypatch.setenv("COPERNICUS_CLIENT_ID", "test-id")
        with pytest.raises(ValidationError, match="copernicus_client_secret"):
            CopernicusSettings()

    def test_missing_both_credentials_raises(self):
        """Must fail if neither credential is set."""
        with pytest.raises(ValidationError):
            CopernicusSettings()


class TestValidConfiguration:
    """Tests for valid configuration loading."""

    def test_valid_config_loads(self, monkeypatch):
        """Valid credentials should produce a valid settings object."""
        monkeypatch.setenv("COPERNICUS_CLIENT_ID", "test-id")
        monkeypatch.setenv("COPERNICUS_CLIENT_SECRET", "test-secret")

        settings = CopernicusSettings()

        assert settings.copernicus_client_id.get_secret_value() == "test-id"
        assert settings.copernicus_client_secret.get_secret_value() == "test-secret"

    def test_default_endpoints(self, monkeypatch):
        """Default endpoints should be set correctly."""
        monkeypatch.setenv("COPERNICUS_CLIENT_ID", "test-id")
        monkeypatch.setenv("COPERNICUS_CLIENT_SECRET", "test-secret")

        settings = CopernicusSettings()

        assert settings.copernicus_stac_url == "https://stac.dataspace.copernicus.eu/v1"
        assert "identity.dataspace.copernicus.eu" in settings.copernicus_token_url
        assert "sh.dataspace.copernicus.eu" in settings.copernicus_process_api_url

    def test_custom_endpoints(self, monkeypatch):
        """Custom endpoint overrides should work."""
        monkeypatch.setenv("COPERNICUS_CLIENT_ID", "test-id")
        monkeypatch.setenv("COPERNICUS_CLIENT_SECRET", "test-secret")
        monkeypatch.setenv("COPERNICUS_STAC_URL", "https://custom.stac.example.com/v1")

        settings = CopernicusSettings()

        assert settings.copernicus_stac_url == "https://custom.stac.example.com/v1"


class TestInvalidConfiguration:
    """Tests for invalid configuration rejection."""

    def test_http_url_rejected(self, monkeypatch):
        """Non-HTTPS URLs must be rejected."""
        monkeypatch.setenv("COPERNICUS_CLIENT_ID", "test-id")
        monkeypatch.setenv("COPERNICUS_CLIENT_SECRET", "test-secret")
        monkeypatch.setenv("COPERNICUS_STAC_URL", "http://insecure.example.com")

        with pytest.raises(ValidationError, match="https://"):
            CopernicusSettings()


class TestSecretsSafety:
    """Tests verifying secrets are never accidentally exposed."""

    def test_repr_hides_secrets(self, monkeypatch):
        """repr() must not contain actual credential values."""
        monkeypatch.setenv("COPERNICUS_CLIENT_ID", "super-secret-id-12345")
        monkeypatch.setenv("COPERNICUS_CLIENT_SECRET", "super-secret-key-67890")

        settings = CopernicusSettings()
        repr_str = repr(settings)

        assert "super-secret-id-12345" not in repr_str
        assert "super-secret-key-67890" not in repr_str

    def test_str_hides_secrets(self, monkeypatch):
        """str() must not contain actual credential values."""
        monkeypatch.setenv("COPERNICUS_CLIENT_ID", "super-secret-id-12345")
        monkeypatch.setenv("COPERNICUS_CLIENT_SECRET", "super-secret-key-67890")

        settings = CopernicusSettings()
        str_val = str(settings)

        assert "super-secret-id-12345" not in str_val
        assert "super-secret-key-67890" not in str_val

    def test_model_dump_hides_secrets(self, monkeypatch):
        """model_dump() should wrap secrets in SecretStr."""
        monkeypatch.setenv("COPERNICUS_CLIENT_ID", "super-secret-id-12345")
        monkeypatch.setenv("COPERNICUS_CLIENT_SECRET", "super-secret-key-67890")

        settings = CopernicusSettings()
        dumped = str(settings.model_dump())

        assert "super-secret-id-12345" not in dumped
        assert "super-secret-key-67890" not in dumped

    def test_json_serialization_hides_secrets(self, monkeypatch):
        """JSON serialization must not contain actual credential values."""
        monkeypatch.setenv("COPERNICUS_CLIENT_ID", "super-secret-id-12345")
        monkeypatch.setenv("COPERNICUS_CLIENT_SECRET", "super-secret-key-67890")

        settings = CopernicusSettings()
        json_str = settings.model_dump_json()

        assert "super-secret-id-12345" not in json_str
        assert "super-secret-key-67890" not in json_str
