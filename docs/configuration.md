# Configuration Guide

## Overview

Ocean Sentinel uses environment variables loaded from a `.env` file
for all configuration. Secrets are never hardcoded or committed.

## Required Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `COPERNICUS_CLIENT_ID` | **Yes** | Sentinel Hub OAuth2 client ID |
| `COPERNICUS_CLIENT_SECRET` | **Yes** | Sentinel Hub OAuth2 client secret |

## Optional Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `COPERNICUS_STAC_URL` | `https://stac.dataspace.copernicus.eu/v1` | STAC API base URL |
| `COPERNICUS_TOKEN_URL` | `https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token` | OAuth2 token endpoint |
| `COPERNICUS_PROCESS_API_URL` | `https://sh.dataspace.copernicus.eu/api/v1/process` | Process API endpoint |

## Setup Instructions

### 1. Obtain Credentials

1. Register at [Copernicus Data Space](https://dataspace.copernicus.eu/)
2. Go to [Sentinel Hub Dashboard](https://shapps.dataspace.copernicus.eu/dashboard/)
3. Navigate to **User Settings** → **OAuth clients** → **Create**
4. Name your client (e.g., "ocean-sentinel-dev")
5. Save the Client ID and Client Secret

### 2. Configure Locally

```bash
# Copy the template
copy .env.example .env

# Edit .env with your credentials
# COPERNICUS_CLIENT_ID=your-client-id-here
# COPERNICUS_CLIENT_SECRET=your-client-secret-here
```

### 3. Verify Configuration

```python
from ocean_sentinel.config import get_settings

# This will raise ValidationError if credentials are missing
settings = get_settings()
print(settings)  # Secrets are masked in output
```

## Security Rules

- **NEVER** commit `.env` to version control
- **NEVER** hardcode credentials in source code
- **NEVER** log or print credential values
- **NEVER** include credentials in error messages
- `.env` is excluded by `.gitignore`
- Secrets are wrapped in `pydantic.SecretStr`
- `repr()` and `str()` never expose secret values
- JSON serialization masks secret values

## Configuration Validation

Configuration is validated at application startup:

- Missing required fields → `ValidationError`
- Non-HTTPS URLs → `ValidationError`
- Invalid values → `ValidationError`

The application will fail fast with a clear error message
if configuration is invalid.
