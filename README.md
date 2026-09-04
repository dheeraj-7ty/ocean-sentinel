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

## Current Phase: 1A — Foundation

Phase 1A establishes:
- Project structure and configuration
- Copernicus API documentation and validation
- Data models and error taxonomy
- Testing foundation

## Quick Start

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
│       └── satellite/
│           ├── __init__.py      # Satellite subsystem boundary
│           ├── auth.py          # OAuth2 token management
│           ├── discovery.py     # STAC-based product discovery
│           └── imagery.py       # Sentinel Hub Process API
├── tests/
│   ├── conftest.py              # Shared fixtures
│   ├── test_config.py           # Configuration tests
│   ├── test_models.py           # Data model tests
│   ├── test_errors.py           # Error model tests
│   └── test_raster_env.py       # Raster environment validation
├── docs/
│   ├── architecture.md          # Architecture documentation
│   ├── copernicus-integration.md # Copernicus API details
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
