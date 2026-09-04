# Copernicus Integration Guide

## Overview

Ocean Sentinel uses two Copernicus Data Space Ecosystem (CDSE) APIs:

1. **STAC API** — for discovering Sentinel-1 GRD acquisitions
2. **Sentinel Hub Process API** — for retrieving AOI-specific processed imagery

## Authentication

### OAuth2 Client Credentials Flow

| Parameter | Value |
|-----------|-------|
| **Grant type** | `client_credentials` |
| **Token endpoint** | `https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token` |
| **Token lifetime** | ~600 seconds (10 minutes) |
| **Rate limit** | Avoid requesting new tokens for every API call |

### How to Obtain Credentials

1. Create a free account at [Copernicus Data Space](https://dataspace.copernicus.eu/)
2. Navigate to [Sentinel Hub Dashboard](https://shapps.dataspace.copernicus.eu/dashboard/)
3. Go to **User Settings** → **OAuth clients** → **Create**
4. Save the **Client ID** and **Client Secret** securely
5. Copy `.env.example` to `.env` and fill in credentials

### Token Request Example

```http
POST /auth/realms/CDSE/protocol/openid-connect/token HTTP/1.1
Host: identity.dataspace.copernicus.eu
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials&client_id=YOUR_ID&client_secret=YOUR_SECRET
```

### Response

```json
{
  "access_token": "eyJhbGci...",
  "token_type": "Bearer",
  "expires_in": 600
}
```

### Implementation

Authentication is implemented in [`satellite/auth.py`](file:///d:/Projects/ocean-sentinel/src/ocean_sentinel/satellite/auth.py):

- **`TokenManager`** — Manages the full OAuth2 lifecycle: token acquisition, caching, expiry-aware reuse, and invalidation.
- **`TokenInfo`** — Immutable dataclass representing a token with metadata (token_type, expires_in, scope). The access_token is excluded from `repr()` to prevent logging leakage.

Usage by future satellite clients:

```python
from ocean_sentinel.config import CopernicusSettings
from ocean_sentinel.satellite.auth import TokenManager

settings = CopernicusSettings()  # Reads from .env / environment
tm = TokenManager(settings)

# For Authorization headers
token = await tm.get_token()  # Returns str

# For full metadata
info = await tm.get_token_info()  # Returns TokenInfo
```

### Authentication Verification

To verify real authentication works with your local credentials:

```bash
# Ensure .env is configured
python scripts/verify_auth.py
```

This will safely report whether authentication succeeded without printing the actual token.

---

## STAC API

### Endpoints

| Endpoint | URL |
|----------|-----|
| **Base URL** | `https://stac.dataspace.copernicus.eu/v1` |
| **Search** | `POST https://stac.dataspace.copernicus.eu/v1/search` |
| **Collections** | `GET https://stac.dataspace.copernicus.eu/v1/collections` |
| **S1 GRD Collection** | `GET https://stac.dataspace.copernicus.eu/v1/collections/sentinel-1-grd` |

> **Note:** The legacy STAC endpoint (`https://catalogue.dataspace.copernicus.eu/stac`)
> was deprecated on November 17, 2025.

### STAC Version

The CDSE STAC API follows **STAC specification v1.1.0**.

### Collection Identifier

Sentinel-1 GRD products are in the collection: **`sentinel-1-grd`**

### Authentication

The STAC API is **publicly accessible** for search operations.
No authentication is required for catalog browsing.
Authentication may be required for certain advanced features.

### Search Request (POST)

```json
{
  "collections": ["sentinel-1-grd"],
  "bbox": [12.0, 40.0, 15.0, 42.0],
  "datetime": "2024-01-01T00:00:00Z/2024-01-31T23:59:59Z",
  "limit": 10
}
```

### Spatial Filtering

- **`bbox`**: `[west, south, east, north]` in WGS84
- **`intersects`**: GeoJSON geometry (alternative to bbox)

### Temporal Filtering

- **`datetime`**: ISO 8601 interval string `start/end`

### Pagination

- Uses `limit` parameter (default varies)
- Response includes `links` with `rel: "next"` for pagination
- Follow `next links for additional pages

### Relevant Metadata Fields

STAC items for Sentinel-1 GRD include:

| Field | Location | Description |
|-------|----------|-------------|
| `id` | item root | Product identifier |
| `datetime` | `properties` | Acquisition datetime |
| `geometry` | item root | Footprint GeoJSON |
| `bbox` | item root | Bounding box |
| `sar:instrument_mode` | `properties` | Mode (IW, EW, etc.) |
| `sar:polarizations` | `properties` | Available polarizations |
| `sat:orbit_state` | `properties` | ASCENDING/DESCENDING |
| `sat:relative_orbit` | `properties` | Relative orbit number |

---

## Sentinel Hub Process API

### Endpoint

| Endpoint | URL |
|----------|-----|
| **Process API** | `https://sh.dataspace.copernicus.eu/api/v1/process` |

### Authentication

All Process API requests require a valid Bearer token:

```http
Authorization: Bearer <access_token>
```

### Data Collection

Sentinel-1 GRD is referenced as: **`sentinel-1-grd`**

### Request Structure

The Process API uses a JSON body with three main sections:

1. **`input`** — data source, AOI, and time range
2. **`output`** — format and resolution
3. **`evalscript`** — JavaScript processing logic

### Example Request

```json
{
  "input": {
    "bounds": {
      "bbox": [12.0, 40.0, 15.0, 42.0],
      "properties": {
        "crs": "http://www.opengis.net/def/crs/EPSG/0/4326"
      }
    },
    "data": [{
      "type": "sentinel-1-grd",
      "dataFilter": {
        "timeRange": {
          "from": "2024-01-01T00:00:00Z",
          "to": "2024-01-31T23:59:59Z"
        }
      },
      "processing": {
        "orthorectify": "true"
      }
    }]
  },
  "output": {
    "width": 512,
    "height": 512,
    "responses": [{
      "identifier": "default",
      "format": {
        "type": "image/tiff"
      }
    }]
  },
  "evalscript": "//VERSION=3\nfunction setup() {\n  return {\n    input: ['VV', 'VH'],\n    output: { id: 'default', bands: 2, sampleType: 'FLOAT32' }\n  };\n}\nfunction evaluatePixel(samples) {\n  return [samples.VV, samples.VH];\n}"
}
```

### VV + VH Evalscript

```javascript
//VERSION=3
function setup() {
    return {
        input: ["VV", "VH"],
        output: {
            id: "default",
            bands: 2,
            sampleType: "FLOAT32"
        }
    };
}

function evaluatePixel(samples) {
    return [samples.VV, samples.VH];
}
```

### Supported Output Formats

- `image/tiff` — GeoTIFF (canonical for scientific analysis)
- `image/png` — PNG (visualization only)
- `image/jpeg` — JPEG (visualization only)

### Processing Options

- `orthorectify`: `"true"` — terrain correction
- `backCoeff`: `"SIGMA0_ELLIPSOID"` — calibration coefficient

---

## Official Documentation URLs

| Resource | URL |
|----------|-----|
| CDSE Documentation Portal | https://documentation.dataspace.copernicus.eu/ |
| STAC API Documentation | https://documentation.dataspace.copernicus.eu/APIs/STAC.html |
| Sentinel Hub Overview | https://documentation.dataspace.copernicus.eu/APIs/SentinelHub.html |
| Sentinel Hub Authentication | https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Overview/Authentication.html |
| Process API | https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Process.html |
| STAC Browser | https://browser.stac.dataspace.copernicus.eu |
| Sentinel Hub Dashboard | https://shapps.dataspace.copernicus.eu/dashboard/ |
| Copernicus Data Space | https://dataspace.copernicus.eu/ |

---

## Temporal Coverage

Sentinel-1 GRD data is available from **October 4, 2014** to present.

## Current Limitations

- STAC search is public; advanced features may require authentication
- Process API has rate limits (HTTP 429 if exceeded)
- Token lifetime is ~10 minutes; must be refreshed proactively
- AOI size is limited by Sentinel Hub processing constraints
- Legacy STAC endpoint is deprecated as of November 2025
