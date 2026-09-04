# ADR-001: Copernicus STAC + Sentinel Hub Process API

**Status:** Accepted  
**Date:** 2026-09-04  
**Decider:** CAO

## Decision

Use the **Copernicus Data Space STAC API** for satellite product discovery
and the **Sentinel Hub Process API** for AOI-specific imagery access.

## Context

Ocean Sentinel needs access to real Sentinel-1 GRD satellite observations
for oil-spill detection and investigation. The system must be practical
for a solo developer while using real satellite data.

Key requirements:
- Discover Sentinel-1 GRD products by area and time
- Retrieve processed imagery for a specific AOI
- Avoid downloading complete native products when only a subset is needed
- Use official, well-documented, maintained APIs

## Alternatives Considered

### 1. STAC API Only

**Approach:** Use STAC for discovery and follow asset links to download native products.

**Pros:**
- Single API to learn
- Direct access to native product files

**Cons:**
- Must download entire native products (hundreds of MB to GB)
- Requires local processing infrastructure (SNAP, GDAL) for AOI extraction
- Significant storage and compute requirements
- Complex for a solo developer

### 2. OData API

**Approach:** Use the CDSE OData API for search and download.

**Pros:**
- Mature API with comprehensive metadata
- Supports product download

**Cons:**
- Still requires downloading complete native products
- OData query syntax is less standard than STAC
- Same local processing burden as option 1

### 3. Native Product Download (S3/OData)

**Approach:** Download complete Sentinel-1 native products via S3 or OData.

**Pros:**
- Full product fidelity
- No dependency on processing service

**Cons:**
- Very large downloads
- Complex local SAR processing pipeline
- Impractical for prototype development

### 4. Sentinel Hub Process API Only

**Approach:** Use Sentinel Hub for both discovery (Catalog API) and imagery.

**Pros:**
- Single authentication system
- Built-in processing

**Cons:**
- Sentinel Hub Catalog API has different capabilities vs CDSE STAC
- Less standard than STAC
- Couples both discovery and imagery to one provider

### 5. STAC + Sentinel Hub Process API (Selected)

**Approach:** Use CDSE STAC for discovery, Sentinel Hub Process API for imagery.

**Pros:**
- STAC is an open standard — portable, well-tooled
- STAC search is public — no auth needed for discovery
- Process API eliminates need to download full products
- Process API handles AOI subsetting, orthorectification, calibration
- Output directly as GeoTIFF/FLOAT32 — ready for analysis
- Well-documented official APIs
- Reasonable for a solo developer

**Cons:**
- Two APIs to integrate (but separate concerns)
- Process API has rate limits and processing constraints
- Dependency on Sentinel Hub service availability

## Decision Rationale

**STAC + Sentinel Hub** provides the best balance of:
- **Practicality**: No large downloads or local SAR processing
- **Standards compliance**: STAC is an open, portable standard
- **Separation of concerns**: Discovery and imagery are independent
- **Developer experience**: Well-documented, reasonable complexity
- **Future flexibility**: Can add native product access later if needed

## Consequences

### Advantages
- Rapid iteration on AOI-specific imagery without GB downloads
- Clean separation between discovery and imagery access
- Standard STAC metadata enables future provider portability
- FLOAT32 GeoTIFF output is directly suitable for ML pipelines

### Limitations
- Cannot access raw native product internals via Process API
- Rate limits may constrain high-volume batch processing
- Limited to processing capabilities offered by Sentinel Hub
- Requires internet connectivity (no offline mode)

### Future Implications
- OData/S3 native product access can be added in a future phase
  for cases requiring full product fidelity
- The internal `AcquisitionMetadata` schema is provider-agnostic,
  enabling future multi-provider support
- The error taxonomy supports both API patterns

### Phase 1B Requirements
- Implement STAC search with pagination
- Implement Sentinel Hub Process API request/response
- Implement OAuth2 token management with caching
- Validate with real Copernicus credentials
