# Ocean Sentinel Architecture

## System Overview

Ocean Sentinel is a satellite-based oil-spill investigation system.
The architecture is designed for progressive elaboration by a single developer.

## Data Flow

```
AOI + Time Range
       │
       ▼
┌─────────────────────┐
│  Request Validation  │  Validates coordinates, time ranges,
│  (models.py)         │  product type, polarization
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  Sentinel Discovery  │  STAC API search for Sentinel-1 GRD
│  (satellite/         │  products matching AOI + time range
│   discovery.py)      │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  Acquisition         │  Normalized internal representation
│  Metadata            │  of satellite observations
│  (models.py)         │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  Sentinel Imagery    │  Sentinel Hub Process API request
│  (satellite/         │  for AOI-specific GeoTIFF
│   imagery.py)        │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  Processed Raster    │  GeoTIFF / FLOAT32 with VV + VH
│  (future: raster     │  bands for analysis
│   processing)        │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  Future ML Pipeline  │  Oil-spill detection,
│                      │  vessel attribution, etc.
└─────────────────────┘
```

## Architectural Boundaries

### 1. Configuration Boundary (`config.py`)

- Loads credentials and settings from environment / `.env`
- Validates all configuration at startup
- Wraps secrets in `SecretStr` to prevent exposure
- Provides a cached singleton via `get_settings()`

### 2. Request Validation (`models.py`)

- `BoundingBox`: WGS84 coordinate validation
- `TimeRange`: Temporal search window validation
- `SearchRequest`: Combined search parameters
- Prevents invalid coordinates from reaching external APIs

### 3. Satellite Discovery (`satellite/discovery.py`)

- Translates `SearchRequest` → STAC API calls
- Searches the CDSE STAC catalog
- Converts raw STAC items → `AcquisitionMetadata`
- Handles pagination, retries, errors

### 4. Satellite Imagery (`satellite/imagery.py`)

- Translates acquisition + AOI → Process API request
- Manages evalscript for VV + VH extraction
- Returns GeoTIFF / FLOAT32 raster data
- Handles authentication via `TokenManager`

### 5. Authentication (`satellite/auth.py`)

- OAuth2 Client Credentials flow
- Token caching with automatic refresh
- Never logs or serializes tokens

### 6. Error Model (`errors.py`)

- Typed error hierarchy with machine-readable codes
- Safe serialization (filters sensitive details)
- Enables consistent error handling at the API layer

### 7. Internal Data Contract (`models.py: AcquisitionMetadata`)

- Normalized representation of satellite observations
- Decouples downstream consumers from STAC response format
- Distinguishes required vs optional fields
- Preserves raw provider data for debugging

## Key Design Decisions

See [ADR-001](adr/001-copernicus-stac-sentinelhub.md) for the satellite access architecture.

## Future Boundaries (not yet implemented)

- Raster Processing: validation, normalization, tiling
- ML Pipeline: oil-spill detection models
- AIS Integration: vessel trajectory correlation
- Investigation Engine: source attribution
