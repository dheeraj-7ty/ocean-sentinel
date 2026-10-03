"""Geometry and Rasterization Helpers for EXP-08 Evaluation Domain.

Provides deterministic construction of DARTIS evaluation masks:
    primary_eval_mask = (dataMask == 1) & (dartis_polygon_mask == 1)

Defines explicit rasterization contract:
- Coordinate Reference System (CRS): EPSG:4326 (WGS84 degrees)
- Affine Transform: [a, b, c, d, e, f] where x' = a*x + b*y + c, y' = d*x + e*y + f
- Pixel Inclusion Rule: pixel-center rule (all_touched=False) ensures area preservation
- Polygon Topology: Explicit 5-point closed ring [(UL), (UR), (BR), (BL), (UL)]
- DataMask Treatment: Pixels where dataMask != 1 are strictly excluded from evaluation
"""

from __future__ import annotations

from typing import Any, Sequence, Union

import affine
import numpy as np
import rasterio.features
from shapely.geometry import Polygon


def create_dartis_polygon_mask(
    height: int,
    width: int,
    transform: Union[affine.Affine, Sequence[float]],
    corners: Union[Sequence[Sequence[float]], dict[str, float]],
    all_touched: bool = False,
) -> np.ndarray:
    """Rasterize the DARTIS rotated quadrilateral polygon onto a target raster grid.

    Args:
        height: Number of rows in target raster grid.
        width: Number of columns in target raster grid.
        transform: Affine transform mapping pixel coordinates to EPSG:4326.
                   Can be an affine.Affine instance or a 6-element sequence
                   [a, b, c, d, e, f] (GDAL order: [dx, 0, x_min, 0, -dy, y_max]).
        corners: Coordinates of the 4 DARTIS patch corners. Either:
                 - A sequence of 4 (lon, lat) pairs: [UL, UR, BR, BL]
                 - A dictionary with keys: 'ul_lon', 'ul_lat', 'ur_lon', 'ur_lat',
                   'br_lon', 'br_lat', 'bl_lon', 'bl_lat'.
        all_touched: If False (default), only pixels whose center is inside the polygon
                     are included (standard pixel-center rule, preserving area).
                     If True, all pixels touched by the polygon are included.

    Returns:
        np.ndarray of shape (height, width) with dtype np.uint8 (1 inside polygon, 0 outside).
    """
    if height <= 0 or width <= 0:
        raise ValueError(f"Raster dimensions must be positive, got height={height}, width={width}")

    # Standardize affine transform
    if isinstance(transform, affine.Affine):
        aff = transform
    elif len(transform) == 6:
        # Check if GDAL-style [dx, 0, left, 0, -dy, top]
        aff = affine.Affine(transform[0], transform[1], transform[2],
                            transform[3], transform[4], transform[5])
    else:
        raise ValueError(f"Transform must be affine.Affine or 6-element sequence, got {transform}")

    # Extract 4 corner points
    if isinstance(corners, dict):
        required_keys = ['ul_lon', 'ul_lat', 'ur_lon', 'ur_lat', 'br_lon', 'br_lat', 'bl_lon', 'bl_lat']
        for k in required_keys:
            if k not in corners:
                raise KeyError(f"Missing required coordinate key '{k}' in corners dict")
        pts = [
            (float(corners['ul_lon']), float(corners['ul_lat'])),
            (float(corners['ur_lon']), float(corners['ur_lat'])),
            (float(corners['br_lon']), float(corners['br_lat'])),
            (float(corners['bl_lon']), float(corners['bl_lat'])),
        ]
    elif len(corners) == 4:
        pts = [(float(c[0]), float(c[1])) for c in corners]
    else:
        raise ValueError(f"Corners must be dict or 4-element sequence of (lon, lat), got {corners}")

    # Construct closed polygon ring
    closed_ring = pts + [pts[0]]
    poly = Polygon(closed_ring)
    if not poly.is_valid:
        poly = poly.buffer(0)

    # Rasterize geometry onto target grid
    mask = rasterio.features.rasterize(
        [(poly, 1)],
        out_shape=(height, width),
        transform=aff,
        all_touched=all_touched,
        default_value=0,
        dtype=np.uint8,
    )
    return mask


def create_primary_evaluation_mask(
    height: int,
    width: int,
    transform: Union[affine.Affine, Sequence[float]],
    corners: Union[Sequence[Sequence[float]], dict[str, float]],
    data_mask: np.ndarray | None = None,
    all_touched: bool = False,
) -> np.ndarray:
    """Construct the executable primary evaluation domain mask for EXP-08.

    Implements the scientific contract:
        primary_eval_mask = (dataMask == 1) & (dartis_polygon_mask == 1)

    Restricts primary patch-level alarm evaluation and pixel-level false alarm
    burden strictly to valid sensor pixels inside the DARTIS ground-truth polygon.
    Extra AABB pixels outside the polygon are masked to 0 and cannot trigger alarms.

    Args:
        height: Number of rows in target raster grid.
        width: Number of columns in target raster grid.
        transform: Affine transform mapping pixel coordinates to EPSG:4326.
        corners: Coordinates of the 4 DARTIS patch corners (UL, UR, BR, BL).
        data_mask: Optional 2D array of sensor data validity (1 = data, 0 = nodata).
                   If None, only the polygon mask is applied.
        all_touched: Pixel inclusion rule (default False: pixel center).

    Returns:
        np.ndarray of shape (height, width) with dtype np.uint8 (1 = evaluate, 0 = mask out).
    """
    poly_mask = create_dartis_polygon_mask(
        height=height,
        width=width,
        transform=transform,
        corners=corners,
        all_touched=all_touched,
    )

    if data_mask is not None:
        if data_mask.shape != (height, width):
            raise ValueError(
                f"data_mask shape {data_mask.shape} does not match raster shape ({height}, {width})"
            )
        eval_mask = ((data_mask == 1) & (poly_mask == 1)).astype(np.uint8)
    else:
        eval_mask = poly_mask

    return eval_mask
