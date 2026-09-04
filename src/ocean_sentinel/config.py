"""Configuration management for Ocean Sentinel.

Loads settings from environment variables / .env file.
Never logs, prints, or serializes secrets.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Optional

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class CopernicusSettings(BaseSettings):
    """Copernicus API configuration.

    Credentials are wrapped in SecretStr to prevent accidental exposure
    in logs, exceptions, or serialized representations.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Credentials (required) ---
    copernicus_client_id: SecretStr = Field(
        ...,
        description="Sentinel Hub OAuth2 client ID",
    )
    copernicus_client_secret: SecretStr = Field(
        ...,
        description="Sentinel Hub OAuth2 client secret",
    )

    # --- Endpoints (with defaults) ---
    copernicus_stac_url: str = Field(
        default="https://stac.dataspace.copernicus.eu/v1",
        description="CDSE STAC API base URL",
    )
    copernicus_token_url: str = Field(
        default="https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
        description="Sentinel Hub OAuth2 token endpoint",
    )
    copernicus_process_api_url: str = Field(
        default="https://sh.dataspace.copernicus.eu/api/v1/process",
        description="Sentinel Hub Process API endpoint",
    )

    # --- Operational settings ---
    token_refresh_margin_seconds: int = Field(
        default=60,
        description="Seconds before token expiry to trigger a refresh",
    )
    http_timeout_seconds: int = Field(
        default=30,
        description="Default HTTP request timeout",
    )
    max_retries: int = Field(
        default=3,
        description="Maximum HTTP retry attempts",
    )

    @field_validator("copernicus_stac_url", "copernicus_token_url", "copernicus_process_api_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith("https://"):
            raise ValueError(f"URL must start with https://, got: {v}")
        return v.rstrip("/")

    def __repr__(self) -> str:
        """Safe repr that never exposes secrets."""
        return (
            f"CopernicusSettings("
            f"stac_url={self.copernicus_stac_url!r}, "
            f"token_url={self.copernicus_token_url!r}, "
            f"process_api_url={self.copernicus_process_api_url!r}, "
            f"client_id=****)"
        )


@lru_cache(maxsize=1)
def get_settings() -> CopernicusSettings:
    """Return cached application settings.

    Raises ValidationError if required credentials are missing.
    """
    return CopernicusSettings()  # type: ignore[call-arg]
