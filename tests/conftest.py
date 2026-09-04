"""Shared test fixtures for Ocean Sentinel."""

import os

import pytest


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, tmp_path):
    """Ensure no real credentials leak into tests.

    Strips Copernicus env vars AND prevents pydantic-settings from
    loading the real .env file by changing the working directory to
    a temporary path that has no .env file.
    """
    # Remove any real credentials from the environment
    for key in [
        "COPERNICUS_CLIENT_ID",
        "COPERNICUS_CLIENT_SECRET",
        "COPERNICUS_STAC_URL",
        "COPERNICUS_TOKEN_URL",
        "COPERNICUS_PROCESS_API_URL",
    ]:
        monkeypatch.delenv(key, raising=False)

    # Change working directory so pydantic-settings won't find .env
    monkeypatch.chdir(tmp_path)
