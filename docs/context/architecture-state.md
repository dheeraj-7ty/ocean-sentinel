# Ocean Sentinel — Architecture State

**Document Version**: 1.0.0  
**Status**: ACTIVE / CANONICAL ARCHITECTURE  
**Date**: September 2026  
**Repository**: `D:\Projects\ocean-sentinel`  
**Primary Sources**: `docs/architecture.md`, `docs/adr/001-copernicus-stac-sentinelhub.md`, `docs/copernicus-integration.md`, `src/ocean_sentinel/`  

---

## 1. Architectural Overview & Boundaries

```
[ Client / Investigation Layer ]
              │
              ▼
┌────────────────────────────────────────────────────────┐
│ 1. Configuration Boundary (config.py)                  │
│    - CopernicusSettings, SecretStr, .env validation    │
└────────────────────────────────────────────────────────┘
              │
              ▼
┌────────────────────────────────────────────────────────┐
│ 2. Request Validation Boundary (models.py)             │
│    - BoundingBox (WGS84), TimeRange, SearchRequest     │
└────────────────────────────────────────────────────────┘
              │
              ▼
┌────────────────────────────────────────────────────────┐
│ 3. Authentication Boundary (satellite/auth.py)         │
│    - TokenManager, OAuth2 Client Credentials, Locking  │
└────────────────────────────────────────────────────────┘
              │
              ├─────────────────────────────┐
              ▼                             ▼
┌───────────────────────────┐ ┌───────────────────────────┐
│ 4. Discovery Service      │ │ 5. Imagery Service        │
│    (satellite/discovery)  │ │    (satellite/imagery)    │
│    - CDSE STAC v1.1.0 API │ │    - Sentinel Hub Process │
│    - Collection: S1 GRD   │ │    - Evalscript (VV + VH) │
│    - -> AcquisitionMetadata│ │    - In-Memory GeoTIFF    │
└───────────────────────────┘ └───────────────────────────┘
              │                             │
              └──────────────┬──────────────┘
                             ▼
┌────────────────────────────────────────────────────────┐
│ 6. SAR Preprocessing Pipeline (processing/sar.py)      │
│    - In-memory decoding (MemoryFile)                   │
│    - Valid pixel masking (isfinite & bounds)           │
│    - Linear σ⁰ -> dB conversion (10*log10)             │
│    - Per-band normalization (Percentile/MinMax/ZScore) │
│    - QualityMetrics & PreprocessedBandStats            │
│    - -> PreprocessingResult                            │
└────────────────────────────────────────────────────────┘
```

---

## 2. Component Specifications & Contracts

### 2.1 Configuration Boundary (`src/ocean_sentinel/config.py`) `[VERIFIED]`
* **Class**: `CopernicusSettings(BaseSettings)`
* **Parameters**:
  - `client_id: str`: CDSE OAuth2 client ID.
  - `client_secret: SecretStr`: Wrapped in Pydantic `SecretStr` to prevent plaintext leakage in logs or stack traces.
  - `token_url: HttpUrl`: Defaults to `https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token`.
  - `stac_url: HttpUrl`: Defaults to `https://stac.dataspace.copernicus.eu/v1`.
  - `process_url: HttpUrl`: Defaults to `https://sh.dataspace.copernicus.eu/api/v1/process`.
* **Behavior**: Reads from `.env` or system environment variables. Caches instance via `get_settings()`.

### 2.2 Domain Data Contracts (`src/ocean_sentinel/models.py`) `[VERIFIED]`
* **`BoundingBox`**: Validates $[\text{west}, \text{south}, \text{east}, \text{north}]$ in EPSG:4326. Enforces $-180 \le \text{west} < \text{east} \le 180$ and $-90 \le \text{south} < \text{north} \le 90$.
* **`TimeRange`**: Validates start/end UTC datetimes. Enforces $\text{start} < \text{end}$. Serializes to STAC ISO 8601 interval string.
* **`AcquisitionMetadata`**: The canonical normalized satellite scene representation:
  - `id: str`: Unique product identifier.
  - `mission: str`: e.g. `"sentinel-1"`.
  - `product_type: ProductType`: e.g. `GRD`.
  - `acquisition_time: datetime`: UTC acquisition timestamp.
  - `geometry: dict`: GeoJSON Polygon representing swath footprint.
  - `polarizations: list[Polarization]`: Available channels (e.g. `[VV, VH]`).
  - `platform: str`: e.g. `"sentinel-1a"`, `"sentinel-1b"`.
  - `orbit_direction: OrbitDirection`: `ASCENDING` or `DESCENDING`.
  - `relative_orbit: int`: Track number.
* **`ImageryRequest`**: Request domain model validating that requested polarizations are available in the target observation, bounding box overlaps the swath, and output resolution/dimensions are well-formed.
* **`ImageryResult`**: Encapsulates raw GeoTIFF bytes, dimensions, pixel type (`float32`), CRS, affine transform, and per-band basic statistics. Excludes raw binary from `repr()`.

### 2.3 Authentication Service (`src/ocean_sentinel/satellite/auth.py`) `[VERIFIED]`
* **Class**: `TokenManager`
* **Flow**: OAuth2 `client_credentials` grant type.
* **Features**:
  - Thread-safe / asynchronous locking via `asyncio.Lock` to prevent stampeding token requests.
  - Proactive refresh buffer (refreshes if token expires within 60 seconds).
  - Explicit token invalidation via `invalidate()`.
  - `TokenInfo` dataclass hides the access token string in `__repr__`.

### 2.4 Discovery Service (`src/ocean_sentinel/satellite/discovery.py`) `[VERIFIED]`
* **Class**: `SentinelDiscoveryService`
* **Target Catalog**: Copernicus CDSE STAC API v1.1.0 (`https://stac.dataspace.copernicus.eu/v1/search`).
* **Target Collection**: `sentinel-1-grd`.
* **Query Strategy**: POST request filtering by `collections`, `bbox`, `datetime`, and instrument parameters.
* **Output**: `list[AcquisitionMetadata]` with pagination handling and retry logic.

### 2.5 Imagery Retrieval Service (`src/ocean_sentinel/satellite/imagery.py`) `[VERIFIED]`
* **Class**: `SentinelImageryService`
* **Target API**: Sentinel Hub Process API on CDSE (`https://sh.dataspace.copernicus.eu/api/v1/process`).
* **ProcessRequestBuilder**: Constructs valid Sentinel Hub JSON payload with:
  - Input provider: `SENTINEL-1-GRD` with acquisition mode `IW`, polarization `DV` (VV+VH).
  - AOI: Geographic coordinates in EPSG:4326.
  - Output: `image/tiff`, 32-bit floating point.
  - Custom Evalscript: Dynamically requests linear $\sigma^0$ for specified polarizations.
* **Validation**: Reads received bytes in-memory using `rasterio.io.MemoryFile`, validates dimensions, band count, and extracts finite statistics.

### 2.6 SAR Preprocessing Pipeline (`src/ocean_sentinel/processing/sar.py`) `[VERIFIED]`
* **Class**: `SARPreprocessor`
* **Configuration**: `PreprocessingConfig`
  - `convert_to_db: bool = True`: Computes $\sigma^0_{\text{dB}} = 10 \cdot \log_{10}(\max(\sigma^0_{\text{linear}}, 1e-6))$.
  - `db_floor: float = -50.0`: Clamps invalid/non-positive pixels.
  - `preserve_linear: bool = True`: Retains physical linear array alongside dB array.
  - `normalization_method: NormalizationMethod`: Percentile, MinMax, Z-score, or None.
  - `percentile_min: float = 1.0`, `percentile_max: float = 99.0`, `clip_normalized: bool = True`.
* **Output Container**: `PreprocessingResult`
  - Stores `PreprocessedBand` containers keyed by `Polarization`.
  - Provides `get_db(pol)`, `get_linear(pol)`, `get_valid_mask(pol)`, `get_normalized(pol)`.
  - Provides `to_multichannel_array(kind="db"|"normalized"|"linear")` returning a 3D NumPy array shaped `(channels, height, width)`.

### 2.7 Error Taxonomy (`src/ocean_sentinel/errors.py`) `[VERIFIED]`
* Root: `OceanSentinelError`
* Subclasses: `ConfigurationError`, `AuthenticationError`, `DiscoveryError`, `ProcessApiError`, `ImageryError`, `PreprocessingError`, `InvalidRequestError`.
* Features: Standardized `code`, `message`, `details`, and safe string formatting filtering out potential tokens or secrets.\n