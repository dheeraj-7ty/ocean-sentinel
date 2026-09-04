"""Real Copernicus authentication verification.

This script reads credentials from the local environment
and attempts real authentication against the Copernicus
identity service.

SECURITY:
- Never prints access tokens
- Never prints client secrets
- Never writes credentials to files
- Only reports safe metadata

Usage:
    # Ensure credentials are set in .env or environment variables
    python scripts/verify_auth.py
"""

from __future__ import annotations

import asyncio
import os
import sys

# Add src to path for editable install compatibility
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


async def verify_real_authentication() -> None:
    """Attempt real Copernicus authentication and report results safely."""

    print("=" * 60)
    print("Ocean Sentinel — Real Copernicus Authentication Verification")
    print("=" * 60)
    print()

    # Check if credentials are available
    client_id = os.environ.get("COPERNICUS_CLIENT_ID", "")
    client_secret = os.environ.get("COPERNICUS_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        # Try loading from .env
        try:
            from dotenv import load_dotenv
            load_dotenv()
            client_id = os.environ.get("COPERNICUS_CLIENT_ID", "")
            client_secret = os.environ.get("COPERNICUS_CLIENT_SECRET", "")
        except ImportError:
            pass

    if not client_id or not client_secret:
        print("STATUS: NOT VERIFIED")
        print("REASON: Credentials not found in environment or .env file")
        print()
        print("To configure credentials:")
        print("  1. Copy .env.example to .env")
        print("  2. Fill in COPERNICUS_CLIENT_ID and COPERNICUS_CLIENT_SECRET")
        return

    print("Credentials found: YES")
    print(f"Client ID length: {len(client_id)} characters")
    print("Client Secret: present (not shown)")
    print()

    # Attempt authentication
    try:
        from ocean_sentinel.config import CopernicusSettings
        from ocean_sentinel.satellite.auth import TokenManager

        settings = CopernicusSettings()
        tm = TokenManager(settings)

        print(f"Token endpoint: {settings.copernicus_token_url}")
        print("Requesting token...")
        print()

        info = await tm.get_token_info()

        print("=" * 60)
        print("REAL COPERNICUS AUTHENTICATION")
        print("=" * 60)
        print(f"Status: PASS")
        print(f"Token received: YES")
        print(f"Token type: {info.token_type}")
        print(f"Token length: {len(info.access_token)} characters")
        print(f"Expires in: {info.expires_in} seconds")
        print(f"Scope: {info.scope or '(empty)'}")
        print(f"Token valid: {info.is_valid(margin_seconds=60)}")
        print("=" * 60)

    except Exception as e:
        print("=" * 60)
        print("REAL COPERNICUS AUTHENTICATION")
        print("=" * 60)
        print(f"Status: FAIL")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {e}")
        print("=" * 60)

        # Verify error doesn't contain secrets
        error_str = str(e)
        if client_secret in error_str:
            print("WARNING: Client secret was found in error message!")
        if client_id in error_str:
            print("NOTE: Client ID appeared in error message")


def main() -> None:
    asyncio.run(verify_real_authentication())


if __name__ == "__main__":
    main()
