"""Comprehensive test suite for Phase 1C.4A: Trujillo Dataset Contract & Ingestion Design.

Verifies:
1. Error taxonomy independence (DatasetError not subclass of SatelliteError).
2. Model immutability (DatasetPatchProvenance frozen at model level).
3. Strict exact stem pairing (XXXXX <-> XXXXX, no fuzzy/fallback).
4. Missing image / missing mask explicit failures.
5. Scientific validation: dimension mismatch, non-binary mask, channel counts, dtypes.
6. Explicit dual-pol valid_mask reduction semantics (np.all across channels).
7. Explicit BackscatterUnit.DECIBEL propagation (no heuristic guessing or linear conversion).
8. Generic tiling engine & canonical 2048x2048 -> 512x512 (16 tiles, row-major).
9. Exact binary mask preservation across tile slices without interpolation.
10. Foreground sum invariant: sum(tile_foreground) == parent_foreground.
11. Zero-leakage grouping key preservation across all tiles (group_key == parent_stem).
12. Memory-safe bounded per-sample lazy loading (weakref verification of no iterator retention).
13. Real Trujillo mask integration (testing against local verified masks).
14. End-to-end integration with SARPreprocessor using BackscatterUnit.DECIBEL.
"""

from __future__ import annotations

import gc
import weakref
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import Affine

from ocean_sentinel.errors import (
    DatasetError,
    DatasetErrorCode,
    DatasetPairingError,
    DatasetTilingError,
    DatasetValidationError,
    SatelliteError,
)
from ocean_sentinel.ingestion.models import (
    DatasetPatchProvenance,
    DatasetValidationConfig,
    TilingConfig,
    VerificationStatus,
)
from ocean_sentinel.ingestion.tiling import compute_tile_definitions
from ocean_sentinel.ingestion.trujillo import TrujilloDatasetLoader
from ocean_sentinel.models import Polarization
from ocean_sentinel.processing.models import BackscatterUnit, PreprocessingConfig
from ocean_sentinel.processing.sar import SARPreprocessor

REPO_ROOT = Path(__file__).resolve().parent.parent
REAL_MASKS_DIR = REPO_ROOT / "data" / "raw" / "trujillo_2024" / "masks" / "Mask_oil"
REAL_IMAGES_DIR = REPO_ROOT / "data" / "raw" / "trujillo_2024" / "images" / "Oil"


def _write_synthetic_geotiff(
    file_path: Path,
    data: np.ndarray,
    dtype: str,
    crs: str | None = None,
    transform: Affine | None = None,
) -> Path:
    """Helper to write synthetic 2D or 3D NumPy array as a GeoTIFF."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    if data.ndim == 2:
        count = 1
        height, width = data.shape
    elif data.ndim == 3:
        count, height, width = data.shape
    else:
        raise ValueError(f"Unsupported array ndim: {data.ndim}")

    with rasterio.open(
        file_path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=count,
        dtype=dtype,
        crs=crs,
        transform=transform or Affine.identity(),
    ) as dst:
        if data.ndim == 2:
            dst.write(data.astype(dtype), 1)
        else:
            for b_idx in range(count):
                dst.write(data[b_idx].astype(dtype), b_idx + 1)
    return file_path


# ===========================================================================
# 1. Error Taxonomy Architecture Tests
# ===========================================================================


class TestErrorTaxonomy:
    """Verify independent error hierarchy for dataset ingestion."""

    def test_dataset_error_is_independent_of_satellite_error(self):
        """DatasetError must NOT inherit from SatelliteError."""
        assert issubclass(DatasetError, Exception)
        assert not issubclass(DatasetError, SatelliteError)

    def test_dataset_error_subclasses_inherit_cleanly(self):
        """All dataset error subclasses inherit from DatasetError."""
        subclasses = [
            DatasetPairingError,
            DatasetValidationError,
            DatasetTilingError,
        ]
        for sc in subclasses:
            assert issubclass(sc, DatasetError)
            assert not issubclass(sc, SatelliteError)

    def test_dataset_error_serialization(self):
        """DatasetError serializes cleanly to dict without leaking credentials."""
        err = DatasetPairingError(
            "Missing paired mask",
            details={"stem": "00042", "token": "secret_token_123"},
        )
        d = err.to_dict()
        assert d["error"] == DatasetErrorCode.PAIRING_FAILURE.value
        assert "Missing paired mask" in d["message"]
        assert d["details"]["stem"] == "00042"
        assert "token" not in d["details"]


# ===========================================================================
# 2. Provenance & Model Immutability Tests
# ===========================================================================


class TestModelImmutabilityAndProvenance:
    """Verify genuine immutability and provenance tracking."""

    def test_provenance_is_genuinely_frozen(self):
        """DatasetPatchProvenance must reject attribute mutation at model level."""
        prov = DatasetPatchProvenance(
            dataset_name="trujillo_2024_part_i",
            patch_stem="00000",
            radiometric_unit=BackscatterUnit.DECIBEL,
        )
        with pytest.raises(Exception):  # ValidationError or FrozenInstanceError
            prov.patch_stem = "00001"  # type: ignore[misc]

        with pytest.raises(Exception):
            prov.radiometric_unit = BackscatterUnit.LINEAR  # type: ignore[misc]

    def test_provenance_explicit_source_truth_statuses(self):
        """Provenance preserves distinction between verified, reported, and assumed."""
        prov = DatasetPatchProvenance(
            dataset_name="trujillo_2024_part_i",
            patch_stem="00000",
            radiometric_unit=BackscatterUnit.DECIBEL,
            nominal_gsd_status=VerificationStatus.ASSUMED,
            parent_scene_status=VerificationStatus.UNKNOWN,
            dtype_status=VerificationStatus.REPORTED,
        )
        assert prov.nominal_gsd_status == VerificationStatus.ASSUMED
        assert prov.parent_scene_status == VerificationStatus.UNKNOWN
        assert prov.dtype_status == VerificationStatus.REPORTED
        assert prov.crs is None


# ===========================================================================
# 3. Strict Stem-Pairing Tests
# ===========================================================================


class TestStrictPairing:
    """Verify strict stem pairing: XXXXX <-> XXXXX (no fuzzy or fallback)."""

    def test_exact_pairing_success(self, tmp_path):
        """Identical stems paired successfully."""
        img_dir = tmp_path / "images"
        mask_dir = tmp_path / "masks"
        img_dir.mkdir()
        mask_dir.mkdir()

        (img_dir / "00001.tif").write_bytes(b"dummy")
        (mask_dir / "00001.tif").write_bytes(b"dummy")
        (img_dir / "00002.tif").write_bytes(b"dummy")
        (mask_dir / "00002.tif").write_bytes(b"dummy")

        loader = TrujilloDatasetLoader(images_dir=img_dir, masks_dir=mask_dir)
        paired = loader.get_paired_stems()
        assert paired == ["00001", "00002"]

    def test_missing_image_raises_pairing_error(self, tmp_path):
        """Mask present but image missing raises explicit DatasetPairingError."""
        img_dir = tmp_path / "images"
        mask_dir = tmp_path / "masks"
        img_dir.mkdir()
        mask_dir.mkdir()

        (mask_dir / "00001.tif").write_bytes(b"dummy")

        loader = TrujilloDatasetLoader(images_dir=img_dir, masks_dir=mask_dir)
        with pytest.raises(DatasetPairingError) as exc_info:
            loader.load_sample("00001")
        assert "Image file missing" in str(exc_info.value)
        assert exc_info.value.code == DatasetErrorCode.PAIRING_FAILURE

    def test_missing_mask_raises_pairing_error(self, tmp_path):
        """Image present but mask missing raises explicit DatasetPairingError."""
        img_dir = tmp_path / "images"
        mask_dir = tmp_path / "masks"
        img_dir.mkdir()
        mask_dir.mkdir()

        (img_dir / "00001.tif").write_bytes(b"dummy")

        loader = TrujilloDatasetLoader(images_dir=img_dir, masks_dir=mask_dir)
        with pytest.raises(DatasetPairingError) as exc_info:
            loader.load_sample("00001")
        assert "Mask file missing" in str(exc_info.value)
        assert exc_info.value.code == DatasetErrorCode.PAIRING_FAILURE

    def test_orphaned_stems_detection(self, tmp_path):
        """Unpaired stems are reported explicitly without silent fallback."""
        img_dir = tmp_path / "images"
        mask_dir = tmp_path / "masks"
        img_dir.mkdir()
        mask_dir.mkdir()

        (img_dir / "00001.tif").write_bytes(b"dummy")
        (mask_dir / "00001.tif").write_bytes(b"dummy")
        (img_dir / "00002.tif").write_bytes(b"dummy")  # Orphan image
        (mask_dir / "00003.tif").write_bytes(b"dummy")  # Orphan mask

        loader = TrujilloDatasetLoader(images_dir=img_dir, masks_dir=mask_dir)
        orphaned_img, orphaned_mask = loader.get_orphaned_stems()
        assert orphaned_img == ["00002"]
        assert orphaned_mask == ["00003"]
        assert loader.get_paired_stems() == ["00001"]


# ===========================================================================
# 4. Validation Engine & Scientific Integrity Tests
# ===========================================================================


class TestValidationEngine:
    """Verify validation checks on dimensions, channels, dtypes, and mask values."""

    @pytest.fixture
    def synthetic_pair(self, tmp_path):
        """Fixture producing a valid synthetic 2048x2048 dual-channel image and binary mask."""
        img_dir = tmp_path / "images"
        mask_dir = tmp_path / "masks"
        img_path = img_dir / "00100.tif"
        mask_path = mask_dir / "00100.tif"

        # Realistic dB range [-30, -5] float32
        img_data = np.random.uniform(-30.0, -5.0, size=(2, 2048, 2048)).astype(np.float32)
        # Binary mask uint8
        mask_data = np.zeros((2048, 2048), dtype=np.uint8)
        mask_data[100:150, 100:200] = 1  # 50 * 100 = 5000 oil pixels

        _write_synthetic_geotiff(img_path, img_data, dtype="float32")
        _write_synthetic_geotiff(mask_path, mask_data, dtype="uint8")

        return img_dir, mask_dir, "00100", 5000

    def test_valid_synthetic_pair_passes_validation(self, synthetic_pair):
        """Valid synthetic pair passes all checks."""
        img_dir, mask_dir, stem, expected_fg = synthetic_pair
        loader = TrujilloDatasetLoader(images_dir=img_dir, masks_dir=mask_dir)

        res = loader.validate_sample(stem)
        assert res.is_valid is True
        assert len(res.checks_failed) == 0
        assert res.metadata is not None
        assert res.metadata.foreground_pixels == expected_fg
        assert res.metadata.total_pixels == 2048 * 2048
        assert res.metadata.has_oil is True
        assert res.metadata.group_key == stem

    def test_dimension_mismatch_fails_validation(self, tmp_path):
        """Image and mask with different shapes fail validation."""
        img_dir = tmp_path / "images"
        mask_dir = tmp_path / "masks"
        img_path = img_dir / "00101.tif"
        mask_path = mask_dir / "00101.tif"

        img_data = np.full((2, 2048, 2048), -15.0, dtype=np.float32)
        mask_data = np.zeros((1024, 1024), dtype=np.uint8)  # Mismatch!

        _write_synthetic_geotiff(img_path, img_data, dtype="float32")
        _write_synthetic_geotiff(mask_path, mask_data, dtype="uint8")

        loader = TrujilloDatasetLoader(images_dir=img_dir, masks_dir=mask_dir)
        res = loader.validate_sample("00101")
        assert res.is_valid is False
        assert "dimension_equality" in res.checks_failed

        with pytest.raises(DatasetValidationError) as exc_info:
            loader.load_sample("00101")
        assert "Validation failed" in str(exc_info.value)

    def test_non_binary_mask_fails_validation(self, tmp_path):
        """Mask containing values other than {0, 1} fails validation."""
        img_dir = tmp_path / "images"
        mask_dir = tmp_path / "masks"
        img_path = img_dir / "00102.tif"
        mask_path = mask_dir / "00102.tif"

        img_data = np.full((2, 2048, 2048), -15.0, dtype=np.float32)
        mask_data = np.zeros((2048, 2048), dtype=np.uint8)
        mask_data[10, 10] = 2  # Non-binary!

        _write_synthetic_geotiff(img_path, img_data, dtype="float32")
        _write_synthetic_geotiff(mask_path, mask_data, dtype="uint8")

        loader = TrujilloDatasetLoader(images_dir=img_dir, masks_dir=mask_dir)
        res = loader.validate_sample("00102")
        assert res.is_valid is False
        assert "mask_binary_semantics" in res.checks_failed

    def test_unexpected_channel_count_fails_validation(self, tmp_path):
        """Image with 1 band when 2 are expected fails validation."""
        img_dir = tmp_path / "images"
        mask_dir = tmp_path / "masks"
        img_path = img_dir / "00103.tif"
        mask_path = mask_dir / "00103.tif"

        img_data = np.full((1, 2048, 2048), -15.0, dtype=np.float32)  # 1 channel
        mask_data = np.zeros((2048, 2048), dtype=np.uint8)

        _write_synthetic_geotiff(img_path, img_data, dtype="float32")
        _write_synthetic_geotiff(mask_path, mask_data, dtype="uint8")

        loader = TrujilloDatasetLoader(
            images_dir=img_dir,
            masks_dir=mask_dir,
            validation_config=DatasetValidationConfig(expected_channels=2),
        )
        res = loader.validate_sample("00103")
        assert res.is_valid is False
        assert "expected_channels" in res.checks_failed

    def test_valid_mask_reduction_semantics(self, tmp_path):
        """Verify dual-pol valid_mask reduction: True iff valid in ALL channels."""
        img_dir = tmp_path / "images"
        mask_dir = tmp_path / "masks"
        img_path = img_dir / "00104.tif"
        mask_path = mask_dir / "00104.tif"

        img_data = np.full((2, 2048, 2048), -15.0, dtype=np.float32)
        # Introduce NaN in band 0 at (10, 10)
        img_data[0, 10, 10] = np.nan
        # Introduce +inf in band 1 at (20, 20)
        img_data[1, 20, 20] = np.inf

        mask_data = np.zeros((2048, 2048), dtype=np.uint8)

        _write_synthetic_geotiff(img_path, img_data, dtype="float32")
        _write_synthetic_geotiff(mask_path, mask_data, dtype="uint8")

        loader = TrujilloDatasetLoader(images_dir=img_dir, masks_dir=mask_dir)
        sample = loader.load_sample("00104")

        # In 2D reduced mask, both (10, 10) and (20, 20) must be False
        assert sample.valid_mask[10, 10] is np.False_
        assert sample.valid_mask[20, 20] is np.False_
        # A normal pixel must be True
        assert sample.valid_mask[0, 0] is np.True_

        # Per-channel masks verify exact channel location
        assert sample.valid_mask_per_channel[0, 10, 10] is np.False_
        assert sample.valid_mask_per_channel[1, 10, 10] is np.True_
        assert sample.valid_mask_per_channel[0, 20, 20] is np.True_
        assert sample.valid_mask_per_channel[1, 20, 20] is np.False_

    def test_configurable_min_valid_ratio_policy(self, tmp_path):
        """Verify min_valid_ratio is treated as a configurable policy."""
        img_dir = tmp_path / "images"
        mask_dir = tmp_path / "masks"
        img_path = img_dir / "00105.tif"
        mask_path = mask_dir / "00105.tif"

        # 60% invalid pixels
        img_data = np.full((2, 2048, 2048), -15.0, dtype=np.float32)
        img_data[:, :1228, :] = np.nan  # 1228 / 2048 = 60% NaN
        mask_data = np.zeros((2048, 2048), dtype=np.uint8)

        _write_synthetic_geotiff(img_path, img_data, dtype="float32")
        _write_synthetic_geotiff(mask_path, mask_data, dtype="uint8")

        # Under default policy 0.5 (50%), 40% valid fails
        loader_strict = TrujilloDatasetLoader(
            images_dir=img_dir,
            masks_dir=mask_dir,
            validation_config=DatasetValidationConfig(min_valid_ratio_policy=0.5),
        )
        assert loader_strict.validate_sample("00105").is_valid is False

        # Under permissive policy 0.3 (30%), 40% valid passes
        loader_permissive = TrujilloDatasetLoader(
            images_dir=img_dir,
            masks_dir=mask_dir,
            validation_config=DatasetValidationConfig(min_valid_ratio_policy=0.3),
        )
        assert loader_permissive.validate_sample("00105").is_valid is True


# ===========================================================================
# 5. Deterministic Tiling & Leakage Prevention Tests
# ===========================================================================


class TestDeterministicTiling:
    """Verify generic and canonical tiling, mask preservation, and leakage grouping."""

    def test_canonical_2048_to_512_tile_count(self):
        """Canonical 2048x2048 -> 512x512 with stride 512 produces exactly 16 tiles."""
        defs = compute_tile_definitions(
            parent_height=2048,
            parent_width=2048,
            parent_stem="00000",
            config=TilingConfig(tile_height=512, tile_width=512, stride_y=512, stride_x=512),
        )
        assert len(defs) == 16
        # Check first and last tile coordinates
        assert defs[0].tile_id == "00000_r00_c00"
        assert defs[0].row_offset == 0
        assert defs[0].col_offset == 0

        assert defs[-1].tile_id == "00000_r03_c03"
        assert defs[-1].row_offset == 1536
        assert defs[-1].col_offset == 1536

    def test_generic_tiling_arbitrary_dimensions(self):
        """Tiling engine handles arbitrary non-power-of-two dimensions."""
        defs = compute_tile_definitions(
            parent_height=1000,
            parent_width=800,
            parent_stem="custom",
            config=TilingConfig(
                tile_height=300,
                tile_width=250,
                stride_y=300,
                stride_x=250,
                edge_handling="drop",
            ),
        )
        # 1000 // 300 = 3 rows (0, 300, 600; 900+300 > 1000 dropped)
        # 800 // 250 = 3 cols (0, 250, 500; 750+250 > 800 dropped)
        assert len(defs) == 3 * 3

    def test_tile_sample_preserves_binary_mask_and_foreground_sum(self, tmp_path):
        """Tile cropping preserves binary mask semantics and foreground pixel count sum."""
        img_dir = tmp_path / "images"
        mask_dir = tmp_path / "masks"
        img_path = img_dir / "00200.tif"
        mask_path = mask_dir / "00200.tif"

        img_data = np.full((2, 2048, 2048), -18.0, dtype=np.float32)
        mask_data = np.zeros((2048, 2048), dtype=np.uint8)
        # Dispersed oil slicks across multiple tile regions
        mask_data[10:50, 10:50] = 1        # in tile r00_c00 (40 * 40 = 1600)
        mask_data[600:700, 100:150] = 1    # in tile r01_c00 (100 * 50 = 5000)
        mask_data[1800:1820, 1800:1820] = 1 # in tile r03_c03 (20 * 20 = 400)
        total_parent_fg = 1600 + 5000 + 400

        _write_synthetic_geotiff(img_path, img_data, dtype="float32")
        _write_synthetic_geotiff(mask_path, mask_data, dtype="uint8")

        loader = TrujilloDatasetLoader(images_dir=img_dir, masks_dir=mask_dir)
        tiles = loader.load_and_tile("00200")

        assert len(tiles) == 16
        tile_fg_sum = 0
        for tile in tiles:
            # 1. Mask unique values strictly in {0, 1}
            unique_vals = set(np.unique(tile.mask_data).tolist())
            assert unique_vals.issubset({0, 1})

            # 2. Dimensions exact
            assert tile.image_data.shape == (2, 512, 512)
            assert tile.mask_data.shape == (512, 512)

            # 3. Group key matches parent stem
            assert tile.definition.group_key == "00200"
            assert tile.provenance.group_key == "00200"
            assert tile.provenance.parent.patch_stem == "00200"

            # 4. Foreground stats
            assert tile.definition.foreground_pixels == np.count_nonzero(tile.mask_data == 1)
            tile_fg_sum += tile.definition.foreground_pixels

        # Invariant: non-overlapping tiling partition conserves exact foreground pixels
        assert tile_fg_sum == total_parent_fg


# ===========================================================================
# 6. Lazy Loading & Memory Residency Tests
# ===========================================================================


class TestLazyLoading:
    """Verify bounded per-sample loading and that iterator retains no sample references."""

    def test_iter_samples_retains_no_strong_references(self, tmp_path):
        """Weakref test: previous sample is freed when caller drops reference."""
        img_dir = tmp_path / "images"
        mask_dir = tmp_path / "masks"

        # Create 3 synthetic pairs
        for s in ["00010", "00011", "00012"]:
            img_p = img_dir / f"{s}.tif"
            mask_p = mask_dir / f"{s}.tif"
            dummy_img = np.full((2, 2048, 2048), -15.0, dtype=np.float32)
            _write_synthetic_geotiff(img_p, dummy_img, "float32")
            _write_synthetic_geotiff(mask_p, np.zeros((2048, 2048), dtype=np.uint8), "uint8")

        loader = TrujilloDatasetLoader(images_dir=img_dir, masks_dir=mask_dir)
        iterator = loader.iter_samples()

        # Fetch first sample
        sample1 = next(iterator)
        ref1 = weakref.ref(sample1)
        assert ref1() is not None

        # Caller drops reference to sample1 and advances iterator to sample2
        del sample1
        sample2 = next(iterator)
        gc.collect()

        # Generator local frame must have released sample1 (no retention/caching)
        assert ref1() is None

        # Fetch third sample and check sample2 release
        ref2 = weakref.ref(sample2)
        del sample2
        _ = next(iterator)
        gc.collect()
        assert ref2() is None


# ===========================================================================
# 7. Radiometric Integration & Downstream Preprocessor Tests
# ===========================================================================


class TestRadiometricIntegration:
    """Verify explicit BackscatterUnit.DECIBEL propagation and SARPreprocessor integration."""

    def test_explicit_decibel_propagation(self, tmp_path):
        """TrujilloDatasetLoader unconditionally sets BackscatterUnit.DECIBEL."""
        img_dir = tmp_path / "images"
        mask_dir = tmp_path / "masks"
        img_p = img_dir / "00300.tif"
        mask_p = mask_dir / "00300.tif"

        dummy_arr = np.full((2, 2048, 2048), -22.5, dtype=np.float32)
        _write_synthetic_geotiff(img_p, dummy_arr, "float32")
        _write_synthetic_geotiff(mask_p, np.zeros((2048, 2048), dtype=np.uint8), "uint8")

        loader = TrujilloDatasetLoader(
            images_dir=img_dir,
            masks_dir=mask_dir,
            expected_polarizations=[Polarization.VV, Polarization.VH],
        )
        sample = loader.load_sample("00300")

        prov = sample.metadata.provenance
        assert prov.radiometric_unit == BackscatterUnit.DECIBEL
        assert prov.polarizations == [Polarization.VV, Polarization.VH]
        assert prov.polarization_status == VerificationStatus.REPORTED

    def test_end_to_end_preprocessor_integration_with_decibel(self, tmp_path):
        """Sample arrays feed directly into SARPreprocessor with BackscatterUnit.DECIBEL."""
        img_dir = tmp_path / "images"
        mask_dir = tmp_path / "masks"
        img_p = img_dir / "00301.tif"
        mask_p = mask_dir / "00301.tif"

        # Realistic negative dB SAR values (e.g. -24 dB to -8 dB)
        raw_vv = np.random.uniform(-25.0, -10.0, size=(2048, 2048)).astype(np.float32)
        raw_vh = np.random.uniform(-30.0, -15.0, size=(2048, 2048)).astype(np.float32)
        combined = np.stack([raw_vv, raw_vh], axis=0)

        _write_synthetic_geotiff(img_p, combined, "float32")
        _write_synthetic_geotiff(mask_p, np.zeros((2048, 2048), dtype=np.uint8), "uint8")

        loader = TrujilloDatasetLoader(
            images_dir=img_dir,
            masks_dir=mask_dir,
            expected_polarizations=[Polarization.VV, Polarization.VH],
        )
        sample = loader.load_sample("00301")

        # Pass to SARPreprocessor with explicit DECIBEL config
        preprocessor = SARPreprocessor()
        prep_cfg = PreprocessingConfig(input_unit=BackscatterUnit.DECIBEL)

        arrays = {
            Polarization.VV: sample.image_data[0],
            Polarization.VH: sample.image_data[1],
        }
        res = preprocessor.process_arrays(
            arrays=arrays,
            polarizations=[Polarization.VV, Polarization.VH],
            observation_id=sample.metadata.provenance.patch_stem,
            width=2048,
            height=2048,
            crs="None",
            bounds=[0.0, 0.0, 2048.0, 2048.0],
            transform=[1.0, 0.0, 0.0, 0.0, 1.0, 0.0],
            config=prep_cfg,
        )

        assert res.band_count == 2
        vv_band = res.get_band(Polarization.VV)
        # All finite negative dB values must remain valid (not clipped by raw > 0)
        assert vv_band.quality.valid_pixels == 2048 * 2048
        assert vv_band.input_unit == BackscatterUnit.DECIBEL
        # Values in db_data are exactly equal to raw values (no log applied)
        np.testing.assert_allclose(vv_band.db_data, raw_vv, rtol=1e-5)


# ===========================================================================
# 8. Real Extracted Trujillo Mask Integration Tests
# ===========================================================================


@pytest.mark.real_data
class TestRealTrujilloMasks:
    """Verify contract against actual extracted Trujillo masks in data/raw/trujillo_2024."""

    @pytest.mark.skipif(not REAL_MASKS_DIR.exists(), reason="Real masks directory not present")
    def test_real_mask_files_exist_and_match_contract(self):
        """Verify real masks 00000.tif and 00001.tif match contract."""
        mask_files = sorted(list(REAL_MASKS_DIR.glob("*.tif")))
        assert len(mask_files) == 1200, f"Expected 1,200 masks, found {len(mask_files)}"

        # Inspect first mask
        first_mask = REAL_MASKS_DIR / "00000.tif"
        with rasterio.open(first_mask) as src:
            assert src.width == 2048
            assert src.height == 2048
            assert src.count == 1
            assert src.dtypes[0] == "uint8"
            assert src.crs is None

            data = src.read(1)
            unique_vals = set(np.unique(data).tolist())
            assert unique_vals.issubset({0, 1})
            fg_count = int(np.count_nonzero(data == 1))
            assert fg_count == 14539  # Verified ground-truth foreground count for 00000.tif

    @pytest.mark.skipif(not REAL_MASKS_DIR.exists(), reason="Real masks directory not present")
    def test_paired_loader_with_synthetic_image_and_real_mask(self, tmp_path):
        """Simulate future archive ingestion: pair synthetic image with real 00000.tif mask."""
        img_dir = tmp_path / "images"
        mask_dir = tmp_path / "masks"
        mask_dir.mkdir()

        # Copy real mask to test dir
        real_mask_src = REAL_MASKS_DIR / "00000.tif"
        real_mask_dst = mask_dir / "00000.tif"
        real_mask_dst.write_bytes(real_mask_src.read_bytes())

        # Generate synthetic image for 00000
        img_p = img_dir / "00000.tif"
        _write_synthetic_geotiff(
            img_p,
            np.random.uniform(-25.0, -10.0, size=(2, 2048, 2048)).astype(np.float32),
            "float32",
        )

        loader = TrujilloDatasetLoader(
            images_dir=img_dir,
            masks_dir=mask_dir,
            expected_polarizations=[Polarization.VV, Polarization.VH],
        )

        # 1. Validation passes
        val_res = loader.validate_sample("00000")
        assert val_res.is_valid is True
        assert val_res.metadata is not None
        assert val_res.metadata.foreground_pixels == 14539

        # 2. Loading succeeds
        sample = loader.load_sample("00000")
        assert sample.mask_data.shape == (2048, 2048)
        assert sample.metadata.provenance.radiometric_unit == BackscatterUnit.DECIBEL

        # 3. Tiling generates exactly 16 chips with conserved foreground sum
        tiles = loader.load_and_tile("00000")
        assert len(tiles) == 16
        assert sum(t.definition.foreground_pixels for t in tiles) == 14539

    @pytest.mark.skipif(
        not (REAL_IMAGES_DIR / "00000.tif").exists() or not REAL_MASKS_DIR.exists(),
        reason="Real extracted images not present",
    )
    def test_real_trujillo_image_and_mask_end_to_end(self):
        """End-to-end integration test with real extracted 00000 image and mask."""
        loader = TrujilloDatasetLoader(
            images_dir=REAL_IMAGES_DIR,
            masks_dir=REAL_MASKS_DIR,
        )

        # 1. Validation
        val_res = loader.validate_sample("00000")
        assert val_res.is_valid is True
        assert val_res.metadata is not None
        assert val_res.metadata.foreground_pixels == 14539
        assert val_res.metadata.provenance.native_shape == (2048, 2048)
        assert val_res.metadata.group_key == "00000"

        # 2. Loading
        sample = loader.load_sample("00000")
        assert sample.image_data.shape == (2, 2048, 2048)
        assert sample.mask_data.shape == (2048, 2048)
        assert sample.metadata.provenance.radiometric_unit == BackscatterUnit.DECIBEL
        assert sample.metadata.provenance.crs == "EPSG:4326"

        # 3. Deterministic Tiling
        tiles = loader.load_and_tile("00000")
        assert len(tiles) == 16
        assert sum(t.definition.foreground_pixels for t in tiles) == 14539

        # 4. SARPreprocessor integration
        preprocessor = SARPreprocessor()
        proc_res = preprocessor.process_arrays(
            arrays={
                Polarization.VV: sample.image_data[0],
                Polarization.VH: sample.image_data[1],
            },
            polarizations=[Polarization.VV, Polarization.VH],
            observation_id=sample.metadata.provenance.patch_stem,
            width=2048,
            height=2048,
            crs=sample.metadata.provenance.crs or "None",
            bounds=[0.0, 0.0, 2048.0, 2048.0],
            transform=sample.metadata.provenance.transform or [1.0, 0.0, 0.0, 0.0, 1.0, 0.0],
            config=PreprocessingConfig(input_unit=BackscatterUnit.DECIBEL),
        )
        assert proc_res.band_count == 2
        vv_band = proc_res.get_band(Polarization.VV)
        assert vv_band.input_unit == BackscatterUnit.DECIBEL
        assert vv_band.quality.valid_pixels == 2048 * 2048


