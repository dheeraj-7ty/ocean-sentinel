"""Tests for Ocean Sentinel Binary SAR Inference Pipeline (Phase 1).

Covers:
1. Checkpoint loading and architecture verification
2. Input validation (band count, geometry, nodata, file existence)
3. Tile window generation and edge clamping
4. Overlap blending weight creation
5. Spatial reconstruction and accumulation
6. Invalid pixel / nodata masking enforcement
7. Geospatial output metadata preservation (CRS, transform, dtypes)
8. Inference determinism
9. Integration validation against real Trujillo validation sample (scene 00012)
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.crs import CRS
from rasterio.transform import Affine
import torch

from ocean_sentinel.inference import (
    DEFAULT_CHECKPOINT_PATH,
    DEFAULT_THRESHOLD,
    DEFAULT_TILE_SIZE,
    InputValidationError,
    InferenceResult,
    compute_tile_windows,
    create_blend_weight_window,
    load_and_validate_sar_raster,
    load_binary_oil_model,
    predict_sar_image,
    preprocess_sar,
    reconstruct_prediction,
    write_georeferenced_prediction,
)
from ocean_sentinel.ml.unet_resnet import ResNet34UNet

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def dummy_2band_geotiff(tmp_path: Path) -> Path:
    """Create a tiny 512x512 2-band synthetic SAR GeoTIFF with georeferencing."""
    file_path = tmp_path / "synthetic_sar.tif"
    height, width = 512, 512
    crs = CRS.from_epsg(4326)
    transform = Affine(0.0001, 0.0, 10.0, 0.0, -0.0001, 50.0)

    # Synthetic dB values: channel 0 mean ~ -33, channel 1 mean ~ -20
    np.random.seed(42)
    ch0 = np.random.normal(loc=-33.2, scale=5.0, size=(height, width)).astype(np.float32)
    ch1 = np.random.normal(loc=-19.9, scale=4.0, size=(height, width)).astype(np.float32)

    with rasterio.open(
        file_path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=2,
        dtype="float32",
        crs=crs,
        transform=transform,
    ) as dst:
        dst.write(ch0, 1)
        dst.write(ch1, 2)

    return file_path


@pytest.fixture
def dummy_1band_geotiff(tmp_path: Path) -> Path:
    """Create a 1-band GeoTIFF to test band count rejection."""
    file_path = tmp_path / "invalid_1band.tif"
    with rasterio.open(
        file_path,
        "w",
        driver="GTiff",
        height=256,
        width=256,
        count=1,
        dtype="float32",
        crs=CRS.from_epsg(4326),
        transform=Affine.identity(),
    ) as dst:
        dst.write(np.zeros((256, 256), dtype=np.float32), 1)
    return file_path


# ==============================================================================
# 1. Checkpoint Loading Tests
# ==============================================================================

def test_checkpoint_load():
    """Verify EXP-06 checkpoint loads cleanly into ResNet34UNet in eval mode."""
    if not DEFAULT_CHECKPOINT_PATH.is_file():
        pytest.skip("EXP-06 checkpoint not found at default location")

    model, meta = load_binary_oil_model(DEFAULT_CHECKPOINT_PATH, device="cpu")
    assert isinstance(model, ResNet34UNet)
    assert not model.training  # Model must be in eval mode
    assert meta["checkpoint_path"] == str(DEFAULT_CHECKPOINT_PATH)
    assert meta["epoch"] == 9
    assert meta["val_metrics"]["val_iou"] == pytest.approx(0.72168, rel=1e-3)


# ==============================================================================
# 2. Input Validation Tests
# ==============================================================================

def test_input_validation_success(dummy_2band_geotiff: Path):
    """Verify valid 2-band georeferenced GeoTIFF loads without error."""
    raw_data, meta, validity = load_and_validate_sar_raster(dummy_2band_geotiff)
    assert raw_data.shape == (2, 512, 512)
    assert meta.count == 2
    assert meta.width == 512
    assert meta.height == 512
    assert meta.crs == CRS.from_epsg(4326)
    assert np.all(validity)


def test_input_validation_rejects_wrong_band_count(dummy_1band_geotiff: Path):
    """Verify input loader rejects rasters without exactly 2 channels."""
    with pytest.raises(InputValidationError, match="Invalid band count"):
        load_and_validate_sar_raster(dummy_1band_geotiff)


def test_input_validation_missing_file(tmp_path: Path):
    """Verify input loader fails clearly on missing file."""
    non_existent = tmp_path / "ghost.tif"
    with pytest.raises(InputValidationError, match="not found"):
        load_and_validate_sar_raster(non_existent)


def test_input_validation_missing_crs(tmp_path: Path):
    """Verify input loader rejects non-georeferenced raster when required."""
    no_crs_path = tmp_path / "no_crs.tif"
    with rasterio.open(
        no_crs_path,
        "w",
        driver="GTiff",
        height=512,
        width=512,
        count=2,
        dtype="float32",
    ) as dst:
        dst.write(np.zeros((2, 512, 512), dtype=np.float32))

    with pytest.raises(InputValidationError, match="Missing coordinate reference system"):
        load_and_validate_sar_raster(no_crs_path, require_georeferencing=True)


# ==============================================================================
# 3. Tiling and Edge Window Clamping Tests
# ==============================================================================

def test_compute_tile_windows_exact_multiple():
    """Verify 2048x2048 image with 512 tile size yields exactly 16 non-overlapping tiles."""
    windows = compute_tile_windows(2048, 2048, tile_size=512, overlap=0)
    assert len(windows) == 16
    assert windows[0] == (0, 512, 0, 512)
    assert windows[-1] == (1536, 2048, 1536, 2048)


def test_compute_tile_windows_non_multiple_clamped():
    """Verify non-multiple dimensions (e.g. 1200x1300) have edge-clamped windows."""
    windows = compute_tile_windows(1200, 1300, tile_size=512, overlap=0)
    for r0, r1, c0, c1 in windows:
        assert (r1 - r0) == 512
        assert (c1 - c0) == 512
        assert r1 <= 1200
        assert c1 <= 1300

    # Verify boundaries are fully covered
    max_r1 = max(w[1] for w in windows)
    max_c1 = max(w[3] for w in windows)
    assert max_r1 == 1200
    assert max_c1 == 1300


def test_compute_tile_windows_invalid_args():
    """Verify invalid tile size or overlap raises ValueError."""
    with pytest.raises(ValueError, match="smaller than tile size"):
        compute_tile_windows(256, 256, tile_size=512)

    with pytest.raises(ValueError, match="Overlap must be"):
        compute_tile_windows(1024, 1024, tile_size=512, overlap=512)


# ==============================================================================
# 4. Overlap Blending and Reconstruction Tests
# ==============================================================================

def test_blend_weight_window():
    """Verify blend weight creation creates symmetric tapered window."""
    w_flat = create_blend_weight_window(512, blend=False)
    assert w_flat.shape == (512, 512)
    assert np.all(w_flat == 1.0)

    w_blend = create_blend_weight_window(512, blend=True)
    assert w_blend.shape == (512, 512)
    assert w_blend[256, 256] > w_blend[0, 0]
    assert np.min(w_blend) >= 0.01


def test_reconstruction_with_overlap():
    """Verify reconstruction with overlap blends tiles without dimension distortion."""
    height, width = 768, 768
    tile_size = 512
    overlap = 256
    windows = compute_tile_windows(height, width, tile_size=tile_size, overlap=overlap)
    blend_weight = create_blend_weight_window(tile_size, blend=True)
    validity = np.ones((height, width), dtype=bool)

    # Simulated constant tile probability of 0.75
    tile_probs = [np.full((tile_size, tile_size), 0.75, dtype=np.float32) for _ in windows]

    prob_map, mask = reconstruct_prediction(
        tile_probs=tile_probs,
        windows=windows,
        height=height,
        width=width,
        blend_weight=blend_weight,
        validity_mask=validity,
        threshold=0.22,
    )

    assert prob_map.shape == (height, width)
    assert mask.shape == (height, width)
    # Since all tiles are 0.75, blended reconstruction should be 0.75 everywhere
    assert np.allclose(prob_map, 0.75, atol=1e-5)
    assert np.all(mask == 1)


# ==============================================================================
# 5. Invalid Pixel / Nodata Enforcement Tests
# ==============================================================================

def test_invalid_pixel_handling(tmp_path: Path):
    """Verify invalid pixels (NaNs) are strictly excluded from oil predictions."""
    file_path = tmp_path / "nan_sar.tif"
    height, width = 512, 512
    raw = np.full((2, height, width), -25.0, dtype=np.float32)
    # Inject NaNs into a 100x100 block
    raw[:, 100:200, 100:200] = np.nan

    with rasterio.open(
        file_path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=2,
        dtype="float32",
        crs=CRS.from_epsg(4326),
        transform=Affine.identity(),
    ) as dst:
        dst.write(raw)

    raw_data, meta, validity = load_and_validate_sar_raster(file_path, require_georeferencing=False)
    assert np.sum(~validity) == 100 * 100

    norm = preprocess_sar(raw_data, validity)
    # Normalized invalid region should be imputed to 0.0
    assert np.all(norm[:, 100:200, 100:200] == 0.0)

    # Simulated tile probability with high value across entire tile
    tile_prob = np.full((512, 512), 0.95, dtype=np.float32)
    windows = [(0, 512, 0, 512)]
    weights = np.ones((512, 512), dtype=np.float32)

    prob_map, mask = reconstruct_prediction(
        tile_probs=[tile_prob],
        windows=windows,
        height=512,
        width=512,
        blend_weight=weights,
        validity_mask=validity,
        threshold=0.22,
    )

    # Invalid block must be NaN in probability and 0 in mask
    assert np.all(np.isnan(prob_map[100:200, 100:200]))
    assert np.all(mask[100:200, 100:200] == 0)
    # Valid region should be detected as oil
    assert np.all(mask[0:50, 0:50] == 1)


# ==============================================================================
# 6. Geospatial Output Preservation Tests
# ==============================================================================

def test_geospatial_output_preservation(dummy_2band_geotiff: Path, tmp_path: Path):
    """Verify written probability and mask GeoTIFFs match source metadata exactly."""
    _, meta, validity = load_and_validate_sar_raster(dummy_2band_geotiff)
    prob_map = np.full((512, 512), 0.5, dtype=np.float32)
    mask = np.zeros((512, 512), dtype=np.uint8)

    prob_path, mask_path = write_georeferenced_prediction(
        probability_map=prob_map,
        prediction_mask=mask,
        metadata=meta,
        output_dir=tmp_path,
        output_prefix="test_geo",
    )

    with rasterio.open(prob_path) as p_src, rasterio.open(mask_path) as m_src:
        assert p_src.crs == meta.crs
        assert p_src.transform == meta.transform
        assert p_src.dtypes[0] == "float32"
        assert p_src.shape == (512, 512)

        assert m_src.crs == meta.crs
        assert m_src.transform == meta.transform
        assert m_src.dtypes[0] == "uint8"
        assert m_src.shape == (512, 512)


# ==============================================================================
# 7. Deterministic Inference Tests
# ==============================================================================

def test_deterministic_inference(dummy_2band_geotiff: Path):
    """Verify repeated inference on identical input yields identical outputs."""
    if not DEFAULT_CHECKPOINT_PATH.is_file():
        pytest.skip("EXP-06 checkpoint not available")

    model, _ = load_binary_oil_model(DEFAULT_CHECKPOINT_PATH, device="cpu")

    res1 = predict_sar_image(
        input_path=dummy_2band_geotiff,
        model=model,
        overlap=0,
        threshold=0.22,
        output_dir=None,
    )
    res2 = predict_sar_image(
        input_path=dummy_2band_geotiff,
        model=model,
        overlap=0,
        threshold=0.22,
        output_dir=None,
    )

    np.testing.assert_array_equal(res1.probability_map, res2.probability_map)
    np.testing.assert_array_equal(res1.prediction_mask, res2.prediction_mask)


# ==============================================================================
# 8. Real Validation Sample Integration Test (Scene 00012)
# ==============================================================================

def test_real_trujillo_validation_sample():
    """Verify inference pipeline reproduces high accuracy on real Trujillo scene 00012."""
    real_img = REPO_ROOT / "data" / "raw" / "trujillo_2024" / "images" / "Oil" / "00012.tif"
    real_mask = REPO_ROOT / "data" / "raw" / "trujillo_2024" / "masks" / "Mask_oil" / "00012.tif"

    if not real_img.is_file() or not real_mask.is_file():
        pytest.skip("Real Trujillo 00012 data not available")

    if not DEFAULT_CHECKPOINT_PATH.is_file():
        pytest.skip("EXP-06 checkpoint not available")

    with tempfile.TemporaryDirectory() as tmp_dir:
        result = predict_sar_image(
            input_path=real_img,
            checkpoint_path=DEFAULT_CHECKPOINT_PATH,
            output_dir=tmp_dir,
            ground_truth_path=real_mask,
            threshold=0.22,
            overlap=0,
        )

        assert result.evaluation_metrics is not None
        m = result.evaluation_metrics
        # Trujillo 00012 has substantial oil ground truth; exp06 model achieves IoU ~ 0.87
        assert m["iou"] >= 0.72, f"IoU {m['iou']} fell below exp06 baseline 0.72"
        assert m["dice"] >= 0.84, f"Dice {m['dice']} fell below exp06 baseline 0.84"
        assert m["precision"] >= 0.85
        assert m["recall"] >= 0.85

        # Verify output files exist
        assert result.probability_path.is_file()
        assert result.mask_path.is_file()
