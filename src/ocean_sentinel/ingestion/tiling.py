"""Pure deterministic sliding-window tiling engine for radar patches.

Decoupled from loader and file I/O. Operates directly on geometry and in-memory
DatasetSample representations, guaranteeing:
- Generic arbitrary-dimension sliding window support.
- Deterministic row-major tile ordering.
- Zero-leakage grouping key preservation (group_key = parent_stem).
- Strict binary mask semantics preservation (no interpolation).
- Deterministic foreground statistic computation.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from ocean_sentinel.errors import DatasetTilingError
from ocean_sentinel.ingestion.models import (
    DatasetSample,
    TileDefinition,
    TileProvenance,
    TileSample,
    TilingConfig,
)


def compute_tile_definitions(
    parent_height: int,
    parent_width: int,
    parent_stem: str,
    config: Optional[TilingConfig] = None,
    group_key: Optional[str] = None,
) -> list[TileDefinition]:
    """Compute geometric tile definitions for a given raster dimension.

    Generic calculation decoupled from in-memory raster data. Works for arbitrary
    dimensions, strides, and tile sizes.

    Args:
        parent_height: Height of parent raster in pixels.
        parent_width: Width of parent raster in pixels.
        parent_stem: Canonical stem of parent patch (e.g. '00000').
        config: Tiling configuration. Defaults to 512x512 with stride 512, drop edges.
        group_key: Partition grouping key for data leakage prevention. Defaults to parent_stem.

    Returns:
        List of TileDefinition objects ordered deterministically in row-major order.

    Raises:
        DatasetTilingError: If parameters are invalid or zero tiles can be generated.
    """
    cfg = config or TilingConfig()
    effective_group_key = group_key or parent_stem

    if parent_height <= 0 or parent_width <= 0:
        raise DatasetTilingError(
            f"Parent dimensions must be positive, got ({parent_height}, {parent_width})",
            details={"parent_height": parent_height, "parent_width": parent_width},
        )
    if cfg.tile_height <= 0 or cfg.tile_width <= 0:
        raise DatasetTilingError(
            f"Tile dimensions must be positive, got ({cfg.tile_height}, {cfg.tile_width})",
            details={"tile_height": cfg.tile_height, "tile_width": cfg.tile_width},
        )
    if cfg.stride_y <= 0 or cfg.stride_x <= 0:
        raise DatasetTilingError(
            f"Strides must be positive, got ({cfg.stride_y}, {cfg.stride_x})",
            details={"stride_y": cfg.stride_y, "stride_x": cfg.stride_x},
        )

    edge_mode = cfg.edge_handling.lower()
    if edge_mode not in ("drop", "pad", "crop"):
        raise DatasetTilingError(
            f"Unsupported edge_handling: {cfg.edge_handling!r}. Must be 'drop', 'pad', or 'crop'",
            details={"edge_handling": cfg.edge_handling},
        )

    # Compute row and column starting coordinates
    if edge_mode == "drop":
        if parent_height < cfg.tile_height or parent_width < cfg.tile_width:
            raise DatasetTilingError(
                f"Parent dimensions ({parent_height}, {parent_width}) smaller than "
                f"tile dimensions ({cfg.tile_height}, {cfg.tile_width}) with edge_handling='drop'",
                details={
                    "parent_height": parent_height,
                    "parent_width": parent_width,
                    "tile_height": cfg.tile_height,
                    "tile_width": cfg.tile_width,
                },
            )
        y_offsets = list(range(0, parent_height - cfg.tile_height + 1, cfg.stride_y))
        x_offsets = list(range(0, parent_width - cfg.tile_width + 1, cfg.stride_x))
    else:  # 'pad' or 'crop'
        y_offsets = list(range(0, parent_height, cfg.stride_y))
        x_offsets = list(range(0, parent_width, cfg.stride_x))

    if not y_offsets or not x_offsets:
        raise DatasetTilingError(
            "Tiling configuration produced zero valid tile offsets",
            details={
                "parent_height": parent_height,
                "parent_width": parent_width,
                "config": cfg.model_dump(),
            },
        )

    definitions: list[TileDefinition] = []
    for row_idx, r_off in enumerate(y_offsets):
        for col_idx, c_off in enumerate(x_offsets):
            tile_id = f"{parent_stem}_r{row_idx:02d}_c{col_idx:02d}"

            if edge_mode == "crop":
                h = min(cfg.tile_height, parent_height - r_off)
                w = min(cfg.tile_width, parent_width - c_off)
            else:
                h = cfg.tile_height
                w = cfg.tile_width

            definition = TileDefinition(
                tile_id=tile_id,
                parent_stem=parent_stem,
                group_key=effective_group_key,
                row_idx=row_idx,
                col_idx=col_idx,
                row_offset=r_off,
                col_offset=c_off,
                height=h,
                width=w,
            )
            definitions.append(definition)

    return definitions


def tile_sample(
    sample: DatasetSample,
    config: Optional[TilingConfig] = None,
) -> list[TileSample]:
    """Deterministically tile a DatasetSample into chips.

    Preserves binary {0, 1} mask semantics exactly via integer array slicing
    (no continuous interpolation or resampling). Inherits immutable parent patch
    provenance and computes exact foreground statistics for each tile.

    Args:
        sample: Validated in-memory DatasetSample.
        config: Optional tiling configuration. Defaults to 512x512 non-overlapping grid.

    Returns:
        List of TileSample objects ordered deterministically in row-major order.

    Raises:
        DatasetTilingError: If slicing fails or sample dimensions are inconsistent.
    """
    cfg = config or TilingConfig()
    num_channels, parent_h, parent_w = sample.image_data.shape

    # Generate geometric tile definitions
    definitions = compute_tile_definitions(
        parent_height=parent_h,
        parent_width=parent_w,
        parent_stem=sample.metadata.provenance.patch_stem,
        config=cfg,
        group_key=sample.metadata.group_key,
    )

    parent_prov = sample.metadata.provenance
    tile_samples: list[TileSample] = []

    for defn in definitions:
        r0 = defn.row_offset
        r1 = r0 + defn.height
        c0 = defn.col_offset
        c1 = c0 + defn.width

        # Check boundary behavior
        if r1 > parent_h or c1 > parent_w:
            if cfg.edge_handling == "pad":
                # Create padded arrays
                tile_img = np.zeros((num_channels, defn.height, defn.width), dtype=np.float32)
                tile_mask = np.zeros((defn.height, defn.width), dtype=np.uint8)
                tile_valid = np.zeros((defn.height, defn.width), dtype=bool)
                tile_valid_pc = np.zeros(
                    (num_channels, defn.height, defn.width), dtype=bool
                )

                actual_r1 = min(r1, parent_h)
                actual_c1 = min(c1, parent_w)
                h_actual = actual_r1 - r0
                w_actual = actual_c1 - c0

                tile_img[:, :h_actual, :w_actual] = sample.image_data[:, r0:actual_r1, c0:actual_c1]
                tile_mask[:h_actual, :w_actual] = sample.mask_data[r0:actual_r1, c0:actual_c1]
                tile_valid[:h_actual, :w_actual] = sample.valid_mask[r0:actual_r1, c0:actual_c1]
                tile_valid_pc[:, :h_actual, :w_actual] = sample.valid_mask_per_channel[
                    :, r0:actual_r1, c0:actual_c1
                ]
            else:
                # Should not occur for 'drop' or 'crop'
                raise DatasetTilingError(
                    f"Tile bounds ({r0}:{r1}, {c0}:{c1}) exceed parent ({parent_h}, {parent_w})",
                    details={"tile_id": defn.tile_id},
                )
        else:
            # Direct integer slicing (exact zero-interpolation preservation of binary values)
            tile_img = sample.image_data[:, r0:r1, c0:c1].copy()
            tile_mask = sample.mask_data[r0:r1, c0:c1].copy()
            tile_valid = sample.valid_mask[r0:r1, c0:c1].copy()
            tile_valid_pc = sample.valid_mask_per_channel[:, r0:r1, c0:c1].copy()

        # Compute exact deterministic foreground statistics
        fg_count = int(np.count_nonzero(tile_mask == 1))
        tile_pixel_count = defn.height * defn.width
        fg_ratio = float(fg_count / tile_pixel_count) if tile_pixel_count > 0 else 0.0
        has_oil = fg_count > 0

        # Construct updated definition with statistics
        populated_defn = TileDefinition(
            tile_id=defn.tile_id,
            parent_stem=defn.parent_stem,
            group_key=defn.group_key,
            row_idx=defn.row_idx,
            col_idx=defn.col_idx,
            row_offset=defn.row_offset,
            col_offset=defn.col_offset,
            height=defn.height,
            width=defn.width,
            foreground_pixels=fg_count,
            foreground_ratio=fg_ratio,
            has_oil=has_oil,
        )

        # Compositional Tile Provenance (references immutable parent patch provenance)
        tile_prov = TileProvenance(
            parent=parent_prov,
            tile_id=defn.tile_id,
            parent_stem=defn.parent_stem,
            group_key=defn.group_key,
            row_idx=defn.row_idx,
            col_idx=defn.col_idx,
            row_offset=defn.row_offset,
            col_offset=defn.col_offset,
            height=defn.height,
            width=defn.width,
        )

        tile_sample_obj = TileSample(
            definition=populated_defn,
            provenance=tile_prov,
            image_data=tile_img,
            mask_data=tile_mask,
            valid_mask=tile_valid,
            valid_mask_per_channel=tile_valid_pc,
        )
        tile_samples.append(tile_sample_obj)

    return tile_samples
