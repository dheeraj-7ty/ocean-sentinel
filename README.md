# Ocean Sentinel

Satellite-based oil-spill investigation and vessel-attribution system.

## Overview

Ocean Sentinel processes real satellite observations to detect potential oil spills,
analyze their temporal evolution, correlate incidents with vessel trajectories,
estimate probable sources, and provide explainable investigation results.

## Architecture

```
AOI + Time Range
       ↓
Request Validation
       ↓
Sentinel Discovery Service
       ↓
Copernicus STAC API
       ↓
Sentinel-1 GRD Acquisition Metadata
       ↓
Sentinel Imagery Service
       ↓
Copernicus Sentinel Hub Process API
       ↓
Processed Sentinel-1 Raster (GeoTIFF / FLOAT32)
       ↓
Raster / Geospatial Validation
       ↓
Future ML Pipeline
```

## Current Phase: 1C — Scientific Data Pipeline & Dataset Construction

- Phase 1A ✅: Project foundation, configuration, models, errors
- Phase 1B.1 ✅: Copernicus OAuth2 authentication
- Phase 1B.2 ✅: Sentinel-1 STAC discovery
- Phase 1B.3.1 ✅: Sentinel-1 Process API request construction
- Phase 1B.3.2 ✅: Sentinel-1 Imagery retrieval (Process API download & raster validation)
- Phase 1C.1 ✅: SAR Preprocessing & Scientific Data Pipeline (dB conversion, invalid masking, per-band normalization)
- Phase 1C.2 ⏳: Dataset Construction

### Running Tests

```bash
# Run all unit tests
pytest -v

# Verify real Copernicus authentication (requires .env credentials)
python scripts/verify_auth.py

# Verify real STAC discovery (requires .env credentials)
python scripts/verify_stac.py

# Verify real Process API imagery retrieval (requires .env credentials)
python scripts/verify_imagery.py

# Verify real SAR preprocessing pipeline (requires .env credentials)
python scripts/verify_preprocessing.py
```

### Prerequisites

- CPython >= 3.10 (from [python.org](https://www.python.org/downloads/))
  - MSYS2 Python is **not** supported (lacks pre-built wheel compatibility)
- A Copernicus Data Space Ecosystem account
- Sentinel Hub OAuth2 client credentials

### Setup

```bash
# Clone repository
git clone <repo-url> ocean-sentinel
cd ocean-sentinel

# Create virtual environment (use python.org CPython, not MSYS2)
# Windows example with explicit path:
"C:\Users\<you>\AppData\Local\Programs\Python\Python310\python.exe" -m venv venv
venv\Scripts\activate

# Linux/macOS:
# python3 -m venv venv
# source venv/bin/activate

# Install dependencies (includes rasterio with GDAL)
pip install -e ".[dev]"

# Configure credentials
copy .env.example .env
# Edit .env with your Copernicus credentials
```

### Running Tests

```bash
pytest -v
```

## Project Structure

```
ocean-sentinel/
├── src/
│   └── ocean_sentinel/
│       ├── __init__.py          # Package metadata
│       ├── config.py            # Configuration management
│       ├── models.py            # Data models (AOI, acquisitions)
│       ├── errors.py            # Error taxonomy
│       ├── satellite/           # Satellite data access subsystem
│       │   ├── __init__.py      # Satellite subsystem boundary
│       │   ├── auth.py          # OAuth2 token management
│       │   ├── discovery.py     # STAC-based product discovery
│       │   └── imagery.py       # Sentinel Hub Process API
│       └── processing/          # SAR & raster processing subsystem
│           ├── __init__.py      # Processing subsystem exports
│           ├── models.py        # Preprocessing configuration and data structures
│           └── sar.py           # SAR backscatter, dB conversion & normalization
├── tests/
│   ├── conftest.py              # Shared fixtures
│   ├── test_auth.py             # Authentication tests
│   ├── test_discovery.py        # STAC discovery tests
│   ├── test_config.py           # Configuration tests
│   ├── test_models.py           # Data model tests
│   ├── test_imagery_request.py  # Process API request construction tests
│   ├── test_imagery_service.py  # Process API imagery retrieval tests
│   ├── test_preprocessing.py    # SAR preprocessing & scientific tests
│   ├── test_errors.py           # Error model tests
│   └── test_raster_env.py       # Raster environment validation
├── scripts/
│   ├── verify_auth.py           # Real Copernicus auth verification
│   ├── verify_stac.py           # Real STAC discovery verification
│   ├── verify_imagery.py        # Real Process API imagery retrieval verification
│   └── verify_preprocessing.py  # Real SAR preprocessing pipeline verification
├── docs/
│   ├── architecture.md          # Architecture documentation
│   ├── copernicus-integration.md # Copernicus API details
│   ├── sar-preprocessing.md     # SAR preprocessing & radiometric documentation
│   ├── configuration.md         # Configuration guide
│   └── adr/
│       └── 001-copernicus-stac-sentinelhub.md  # ADR
├── .env.example                 # Configuration template
├── .gitignore                   # Git exclusions
├── pyproject.toml               # Project metadata & dependencies
└── README.md                    # This file
```

## Security

- Credentials are loaded from environment variables / `.env` file
- `.env` is excluded from Git via `.gitignore`
- Secrets are wrapped in `SecretStr` to prevent accidental logging
- No credentials are ever committed, logged, or serialized

## License

MIT
