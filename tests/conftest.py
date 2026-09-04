"""Shared test fixtures for Ocean Sentinel."""

import os

import pytest


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Ensure no real credentials leak into tests."""
    # Remove any real credentials from the environment
    for key in [
        "COPERNICUS_CLIENT_ID",
        "COPERNICUS_CLIENT_SECRET",
        "COPERNICUS_STAC_URL",
        "COPERNICUS_TOKEN_URL",
        "COPERNICUS_PROCESS_API_URL",
    ]:
        monkeypatch.delenv(key, raising=False)
