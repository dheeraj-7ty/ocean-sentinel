"""Satellite data access subsystem.

This package provides the boundary between Ocean Sentinel and
external satellite data providers (currently Copernicus CDSE).

Architectural boundaries:
    - discovery: STAC-based product search and metadata retrieval
    - imagery: Sentinel Hub Process API for AOI-specific raster access
    - auth: OAuth2 token management for Copernicus services
"""
