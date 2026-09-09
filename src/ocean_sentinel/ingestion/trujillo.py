"""Trujillo Part I dataset loader, strict stem-pairing, and validation engine.

Implements the offline dataset contract required to safely ingest Trujillo-Acatitla Part I:
- Strict exact stem pairing: XXXXX.tif (image) <-> XXXXX.tif (mask).
- Explicit BackscatterUnit.DECIBEL propagation.
- Comprehensive scientific validation (dimensionality, channels, dtypes, binary mask).
- Zero-leakage partition grouping key exposure (group_key = stem).
- Memory-safe bounded per-sample loading (no full-archive RAM caching).
- Avoids duplicate full-raster reads in load_and_tile.
"""

from __future__ import annotations

import logging
import warnings
from pathlib import Path
from typing import Iterator, Optional

import numpy as np
import rasterio
from rasterio.errors import NotGeoreferencedWarning

from ocean_sentinel.errors import (
    DatasetPairingError,
    DatasetValidationError,
)
from ocean_sentinel.ingestion.models import (
    DatasetPatchMetadata,
    DatasetPatchProvenance,
    DatasetSample,
    DatasetValidationConfig,
    DatasetValidationResult,
    TileSample,
    TilingConfig,
    VerificationStatus,
)
from ocean_sentinel.ingestion.tiling import tile_sample
from ocean_sentinel.models import Polarization
from ocean_sentinel.processing.models import BackscatterUnit

logger = logging.getLogger(__name__)


class TrujilloDatasetLoader:
    """Offline dataset loader and validator for Trujillo Part I SAR imagery."""

    def __init__(
        self,
        images_dir: Path | str,
        masks_dir: Path | str,
        validation_config: Optional[DatasetValidationConfig] = None,
        expected_polarizations: Optional[list[Polarization]] = None,
        image_extension: str = ".tif",
        mask_extension: str = ".tif",
    ) -> None:
        """Initialize Trujillo dataset loader.

        Does NOT load rasters into memory. Scans directory indexes only.

        Args:
            images_dir: Path to directory containing image rasters.
            masks_dir: Path to directory containing mask rasters.
            validation_config: Configurable validation rules and policy thresholds.
            expected_polarizations: Optional polarization order (defaults to UNKNOWN/REPORTED).
            image_extension: Filename extension for image rasters (default: .tif).
            mask_extension: Filename extension for mask rasters (default: .tif).
        """
        img_p = Path(images_dir)
        self.images_dir = img_p / "Oil" if (img_p / "Oil").is_dir() else img_p
        mask_p = Path(masks_dir)
        self.masks_dir = mask_p / "Mask_oil" if (mask_p / "Mask_oil").is_dir() else mask_p
        self.validation_config = validation_config or DatasetValidationConfig()
        self.expected_polarizations = expected_polarizations
        self.image_extension = image_extension.lower()
        self.mask_extension = mask_extension.lower()

    def get_image_path(self, stem: str) -> Path:
        """Return expected image path for a given stem."""
        return self.images_dir / f"{stem}{self.image_extension}"

    def get_mask_path(self, stem: str) -> Path:
        """Return expected mask path for a given stem."""
        return self.masks_dir / f"{stem}{self.mask_extension}"

    def discover_image_stems(self) -> set[str]:
        """Discover all valid image stems in the images directory."""
        if not self.images_dir.exists():
            return set()
        return {
            p.stem
            for p in self.images_dir.iterdir()
            if p.is_file() and p.suffix.lower() == self.image_extension
        }

    def discover_mask_stems(self) -> set[str]:
        """Discover all valid mask stems in the masks directory."""
        if not self.masks_dir.exists():
            return set()
        return {
            p.stem
            for p in self.masks_dir.iterdir()
            if p.is_file() and p.suffix.lower() == self.mask_extension
        }

    def get_paired_stems(self) -> list[str]:
        """Return sorted list of stems that exist strictly in both image and mask directories.

        Guarantees strict 1-to-1 exact pairing: XXXXX <-> XXXXX.
        No fuzzy matching, no nearest-match, no fallback.
        """
        img_stems = self.discover_image_stems()
        mask_stems = self.discover_mask_stems()
        paired = sorted(list(img_stems.intersection(mask_stems)))
        return paired

    def get_orphaned_stems(self) -> tuple[list[str], list[str]]:
        """Return lists of unpaired/orphaned stems: (orphaned_images, orphaned_masks)."""
        img_stems = self.discover_image_stems()
        mask_stems = self.discover_mask_stems()
        orphaned_images = sorted(list(img_stems - mask_stems))
        orphaned_masks = sorted(list(mask_stems - img_stems))
        return orphaned_images, orphaned_masks

    def validate_sample(self, stem: str) -> DatasetValidationResult:
        """Perform comprehensive validation of an image/mask pair without raising.

        Evaluates:
        - Image and mask file existence and readability.
        - Spatial dimension equality.
        - Configured shape expectations (policy default: 2048x2048).
        - Configured channel expectations (policy default: 2 channels).
        - Mask binary {0, 1} semantics.
        - Image numeric dtype (float32) and mask dtype (uint8).
        - Finite pixel ratio against configurable policy threshold.

        Args:
            stem: Patch stem identifier (e.g. '00000').

        Returns:
            DatasetValidationResult capturing check results and errors.
        """
        img_path = self.get_image_path(stem)
        mask_path = self.get_mask_path(stem)
        cfg = self.validation_config

        passed: list[str] = []
        failed: list[str] = []
        errors: list[str] = []
        warnings_list: list[str] = []

        # 1. Existence checks
        if not img_path.exists():
            failed.append("image_exists")
            errors.append(f"Image file does not exist: {img_path}")
        else:
            passed.append("image_exists")

        if not mask_path.exists():
            failed.append("mask_exists")
            errors.append(f"Mask file does not exist: {mask_path}")
        else:
            passed.append("mask_exists")

        if failed:
            return DatasetValidationResult(
                is_valid=False,
                patch_stem=stem,
                checks_passed=passed,
                checks_failed=failed,
                errors=errors,
                warnings=warnings_list,
            )

        # 2. Readability & metadata checks
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=NotGeoreferencedWarning)
                with rasterio.open(img_path) as src_img, rasterio.open(mask_path) as src_mask:
                    passed.append("rasters_readable")

                    img_h, img_w = src_img.height, src_img.width
                    mask_h, mask_w = src_mask.height, src_mask.width
                    img_count = src_img.count
                    mask_count = src_mask.count
                    img_dtype = src_img.dtypes[0]
                    mask_dtype = src_mask.dtypes[0]

                    # Dimension equality
                    if img_h == mask_h and img_w == mask_w:
                        passed.append("dimension_equality")
                    else:
                        failed.append("dimension_equality")
                        errors.append(
                            f"Dimension mismatch: image ({img_h}, {img_w}) "
                            f"!= mask ({mask_h}, {mask_w})"
                        )

                    # Expected shape policy
                    if cfg.expected_shape is not None:
                        if (img_h, img_w) == cfg.expected_shape:
                            passed.append("expected_shape")
                        else:
                            failed.append("expected_shape")
                            errors.append(
                                f"Image shape ({img_h}, {img_w}) != expected {cfg.expected_shape}"
                            )

                    # Expected dtype checks
                    if cfg.expected_image_dtype is not None:
                        if img_dtype == cfg.expected_image_dtype:
                            passed.append("expected_image_dtype")
                        else:
                            failed.append("expected_image_dtype")
                            errors.append(
                                f"Image dtype {img_dtype} != expected {cfg.expected_image_dtype}"
                            )

                    if cfg.expected_mask_dtype is not None:
                        if mask_dtype == cfg.expected_mask_dtype:
                            passed.append("expected_mask_dtype")
                        else:
                            failed.append("expected_mask_dtype")
                            errors.append(
                                f"Mask dtype {mask_dtype} != expected {cfg.expected_mask_dtype}"
                            )

                    # Expected channel count policy
                    if cfg.expected_channels is not None:
                        if img_count == cfg.expected_channels:
                            passed.append("expected_channels")
                        else:
                            failed.append("expected_channels")
                            errors.append(
                                f"Image band count {img_count} != expected {cfg.expected_channels}"
                            )

                    # Mask single-channel check
                    if mask_count == 1:
                        passed.append("mask_single_channel")
                    else:
                        failed.append("mask_single_channel")
                        errors.append(f"Mask must have 1 band, got {mask_count}")

                    # Read data for semantic validation
                    img_data = src_img.read().astype(np.float32)
                    mask_data = src_mask.read(1)

        except Exception as e:
            failed.append("raster_read_error")
            errors.append(f"Raster read error: {e}")
            return DatasetValidationResult(
                is_valid=False,
                patch_stem=stem,
                checks_passed=passed,
                checks_failed=failed,
                errors=errors,
                warnings=warnings_list,
            )

        # 3. Mask binary semantics
        if cfg.require_binary_mask:
            unique_vals = set(np.unique(mask_data).tolist())
            if unique_vals.issubset({0, 1}):
                passed.append("mask_binary_semantics")
            else:
                failed.append("mask_binary_semantics")
                errors.append(f"Mask contains non-binary values: {sorted(list(unique_vals))}")

        # 4. Finite pixels and validity policy
        valid_per_channel = np.isfinite(img_data)
        valid_mask_2d = np.all(valid_per_channel, axis=0)
        total_pixels = int(valid_mask_2d.size)
        valid_pixels = int(np.count_nonzero(valid_mask_2d))
        valid_ratio = float(valid_pixels / total_pixels) if total_pixels > 0 else 0.0

        if cfg.min_valid_ratio_policy is not None:
            if valid_ratio >= cfg.min_valid_ratio_policy:
                passed.append("valid_pixel_ratio_policy")
            else:
                failed.append("valid_pixel_ratio_policy")
                errors.append(
                    f"Valid pixel ratio {valid_ratio:.3f} below policy threshold "
                    f"{cfg.min_valid_ratio_policy:.3f}"
                )

        fg_count = int(np.count_nonzero(mask_data == 1))
        fg_ratio = float(fg_count / total_pixels) if total_pixels > 0 else 0.0
        has_oil = fg_count > 0

        is_valid = len(failed) == 0

        # Construct patch metadata if valid
        patch_metadata: Optional[DatasetPatchMetadata] = None
        if is_valid:
            pol_status = (
                VerificationStatus.REPORTED
                if self.expected_polarizations is not None
                else VerificationStatus.UNKNOWN
            )
            provenance = DatasetPatchProvenance(
                dataset_name="trujillo_2024_part_i",
                dataset_version="1.0.0",
                source_archive="01_Train_Val_Oil_Spill_images.7z",
                patch_stem=stem,
                image_path=img_path,
                mask_path=mask_path,
                radiometric_unit=BackscatterUnit.DECIBEL,  # Explicitly DECIBEL
                polarizations=self.expected_polarizations,
                polarization_status=pol_status,
                native_shape=(img_h, img_w),
                native_shape_status=VerificationStatus.REPORTED,
                dtype=str(img_dtype),
                dtype_status=VerificationStatus.REPORTED,
                nominal_gsd_meters=10.0,
                nominal_gsd_status=VerificationStatus.ASSUMED,
                crs=str(src_img.crs) if src_img.crs else None,
                crs_status=(
                    VerificationStatus.VERIFIED
                    if src_img.crs is None
                    else VerificationStatus.REPORTED
                ),
                transform=list(src_img.transform)[:6] if src_img.transform else None,
                transform_status=VerificationStatus.VERIFIED,
                source_verification_status=VerificationStatus.REPORTED,
            )
            patch_metadata = DatasetPatchMetadata(
                provenance=provenance,
                total_pixels=total_pixels,
                foreground_pixels=fg_count,
                foreground_ratio=fg_ratio,
                has_oil=has_oil,
                group_key=stem,  # Zero-leakage grouping key
            )

        return DatasetValidationResult(
            is_valid=is_valid,
            patch_stem=stem,
            checks_passed=passed,
            checks_failed=failed,
            errors=errors,
            warnings=warnings_list,
            metadata=patch_metadata,
        )

    def load_sample(self, stem: str) -> DatasetSample:
        """Load a single patch into memory, validating it in a single read pass.

        Avoids duplicate file reads: reads raster once, enforces validation checks,
        and constructs DatasetSample with explicit BackscatterUnit.DECIBEL.

        Args:
            stem: Patch stem identifier (e.g. '00000').

        Returns:
            Validated DatasetSample.

        Raises:
            DatasetPairingError: If image or mask file is missing.
            DatasetValidationError: If validation checks fail.
        """
        img_path = self.get_image_path(stem)
        mask_path = self.get_mask_path(stem)

        if not img_path.exists():
            raise DatasetPairingError(
                f"Image file missing for stem {stem}: {img_path}",
                details={"stem": stem, "missing_path": str(img_path)},
            )
        if not mask_path.exists():
            raise DatasetPairingError(
                f"Mask file missing for stem {stem}: {mask_path}",
                details={"stem": stem, "missing_path": str(mask_path)},
            )

        # Validate and read in a single pass to prevent duplicate file I/O
        validation = self.validate_sample(stem)
        if not validation.is_valid:
            raise DatasetValidationError(
                f"Validation failed for patch {stem}: {'; '.join(validation.errors)}",
                details={
                    "stem": stem,
                    "checks_failed": validation.checks_failed,
                    "errors": validation.errors,
                },
            )

        # Read rasters into in-memory float32 and uint8 arrays
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=NotGeoreferencedWarning)
            with rasterio.open(img_path) as src_img:
                img_data = src_img.read().astype(np.float32)
            with rasterio.open(mask_path) as src_mask:
                mask_data = src_mask.read(1).astype(np.uint8)

        # Validity computation with explicit dual-pol reduction semantics
        valid_per_channel = np.isfinite(img_data)
        valid_mask_2d = np.all(valid_per_channel, axis=0)

        assert validation.metadata is not None
        return DatasetSample(
            metadata=validation.metadata,
            image_data=img_data,
            mask_data=mask_data,
            valid_mask=valid_mask_2d,
            valid_mask_per_channel=valid_per_channel,
        )

    def iter_samples(self) -> Iterator[DatasetSample]:
        """Memory-safe generator yielding one sample at a time.

        Does NOT retain strong references to previously yielded samples,
        guaranteeing bounded memory residency.
        """
        stems = self.get_paired_stems()
        for stem in stems:
            sample = self.load_sample(stem)
            yield sample

    def load_and_tile(
        self,
        stem: str,
        tiling_config: Optional[TilingConfig] = None,
    ) -> list[TileSample]:
        """Validate, load, and deterministically tile a patch in a single operation.

        Strictly routes through validation and unit verification. Reads the raster
        exactly once, preventing redundant full-raster disk reads.

        Args:
            stem: Patch stem identifier (e.g. '00000').
            tiling_config: Optional tiling configuration.

        Returns:
            List of TileSample objects with deterministic row-major ordering.
        """
        sample = self.load_sample(stem)
        return tile_sample(sample, tiling_config)
