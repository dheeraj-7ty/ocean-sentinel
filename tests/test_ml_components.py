"""Comprehensive tests for Ocean Sentinel ML subsystem.

Covers:
1. ResNet34UNet & VanillaUNet (contracts, parameter count, forward, backward, channel adaptation).
2. CombinedBCEAndDiceLoss, SoftDiceLoss, FocalTverskyLoss (edge cases, finite loss & gradients).
3. Segmentation metrics & SegmentationMeter (empty mask semantics, precision/recall/iou/dice).
4. Validation threshold optimization.
5. SAR geometric augmentations (discrete consistency, determinism, binary mask preservation).
6. Real Trujillo dataset & model integration.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest
import torch
import torch.nn as nn

from ocean_sentinel.ingestion.dataset import TrujilloTileDataset
from ocean_sentinel.ingestion.split import DatasetManifest, SplitName
from ocean_sentinel.ml import (
    CombinedBCEAndDiceLoss,
    FocalTverskyLoss,
    IdentityTransform,
    ResNet34UNet,
    SARGeometricAugmentation,
    SegmentationMeter,
    SoftDiceLoss,
    VanillaUNet,
    adapt_resnet_conv1_weights,
    compute_batch_metrics,
    compute_metrics_from_counts,
    count_parameters,
    generate_default_threshold_grid,
    optimize_threshold_on_validation,
)
from scripts.audit_spatial_leakage import compute_box_overlap, haversine_distance_km

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "data" / "metadata" / "trujillo_2024" / "spatial_split_manifest.json"


# ===========================================================================
# 1. Model Architecture Tests
# ===========================================================================


class TestResNet34UNet:
    """Test ResNet34UNet architecture, contracts, and weight adaptations."""

    def test_construction_and_parameter_count(self) -> None:
        model = ResNet34UNet(in_channels=2, num_classes=1, pretrained=False)
        counts = count_parameters(model)
        assert counts["total"] > 20_000_000
        assert counts["trainable"] == counts["total"]
        assert counts["non_trainable"] == 0
        assert model.in_channels == 2
        assert model.num_classes == 1

    def test_output_shape_and_contract(self) -> None:
        model = ResNet34UNet(in_channels=2, num_classes=1, pretrained=False)
        model.eval()
        x = torch.randn(2, 2, 512, 512)
        with torch.no_grad():
            logits = model(x)
        assert logits.shape == (2, 1, 512, 512)
        assert logits.dtype == torch.float32

    def test_invalid_input_channels_raises(self) -> None:
        model = ResNet34UNet(in_channels=2, num_classes=1, pretrained=False)
        # 3 channels instead of 2
        x_3ch = torch.randn(1, 3, 512, 512)
        with pytest.raises(ValueError, match="Expected 2 input channels"):
            model(x_3ch)

        # 1 channel instead of 2
        x_1ch = torch.randn(1, 1, 512, 512)
        with pytest.raises(ValueError, match="Expected 2 input channels"):
            model(x_1ch)

    def test_invalid_input_dimensions_raises(self) -> None:
        model = ResNet34UNet(in_channels=2, num_classes=1, pretrained=False)
        # 3D tensor
        x_3d = torch.randn(2, 512, 512)
        with pytest.raises(ValueError, match="Expected 4D input"):
            model(x_3d)

        # Non-divisible spatial size
        x_odd = torch.randn(1, 2, 500, 500)
        with pytest.raises(ValueError, match="must be divisible by 32"):
            model(x_odd)

    def test_gradient_flow_and_finite_gradients(self) -> None:
        model = ResNet34UNet(in_channels=2, num_classes=1, pretrained=False)
        model.train()
        x = torch.randn(2, 2, 128, 128)
        logits = model(x)
        loss = logits.sum()
        loss.backward()

        for name, param in model.named_parameters():
            if param.requires_grad:
                assert param.grad is not None, f"Missing gradient for {name}"
                assert torch.isfinite(param.grad).all(), f"Non-finite gradient in {name}"

    @pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
    def test_cuda_forward_and_backward(self) -> None:
        model = ResNet34UNet(in_channels=2, num_classes=1, pretrained=False).cuda()
        model.train()
        x = torch.randn(2, 2, 256, 256, device="cuda")
        logits = model(x)
        assert logits.is_cuda
        assert logits.shape == (2, 1, 256, 256)
        loss = logits.mean()
        loss.backward()
        assert model.conv1.weight.grad is not None
        assert torch.isfinite(model.conv1.weight.grad).all()

    @pytest.mark.parametrize(
        "method",
        ["slice_variance_scaled", "average_distributed", "slice", "rgb_luminance"],
    )
    def test_channel_adaptation_methods(self, method: str) -> None:
        w_rgb = torch.randn(64, 3, 7, 7)
        adapted = adapt_resnet_conv1_weights(w_rgb, method=method)
        assert adapted.shape == (64, 2, 7, 7)
        assert torch.isfinite(adapted).all()

        if method == "slice_variance_scaled":
            expected = w_rgb[:, 0:2] * math.sqrt(3.0 / 2.0)
            assert torch.allclose(adapted, expected)
        elif method == "slice":
            assert torch.allclose(adapted, w_rgb[:, 0:2])
        elif method == "average_distributed":
            expected_0 = w_rgb[:, 0] + 0.5 * w_rgb[:, 2]
            assert torch.allclose(adapted[:, 0], expected_0)


class TestVanillaUNet:
    """Test secondary VanillaUNet baseline architecture."""

    def test_vanilla_unet_construction_and_forward(self) -> None:
        model = VanillaUNet(in_channels=2, num_classes=1, base_channels=32)
        counts = count_parameters(model)
        assert counts["total"] > 7_000_000
        x = torch.randn(2, 2, 128, 128)
        logits = model(x)
        assert logits.shape == (2, 1, 128, 128)
        assert logits.dtype == torch.float32


# ===========================================================================
# 2. Loss Function Tests
# ===========================================================================


class TestLosses:
    """Test SoftDiceLoss, CombinedBCEAndDiceLoss, and FocalTverskyLoss."""

    def test_combined_loss_finite_and_gradients(self) -> None:
        criterion = CombinedBCEAndDiceLoss()
        logits = torch.randn(2, 1, 64, 64, requires_grad=True)
        targets = torch.randint(0, 2, (2, 1, 64, 64)).float()

        loss = criterion(logits, targets)
        assert torch.isfinite(loss)
        assert loss.item() > 0

        loss.backward()
        assert logits.grad is not None
        assert torch.isfinite(logits.grad).all()

    def test_soft_dice_perfect_prediction(self) -> None:
        criterion = SoftDiceLoss(smooth=1e-6)
        # Perfectly confident predictions matching target
        targets = torch.ones(2, 1, 32, 32)
        logits = torch.ones(2, 1, 32, 32) * 20.0  # sigmoid(20) ≈ 1.0

        loss = criterion(logits, targets)
        assert loss.item() < 1e-4  # Near 0.0

    def test_soft_dice_empty_masks_agreement(self) -> None:
        criterion = SoftDiceLoss(smooth=1.0)
        # Clean water in both ground truth and prediction
        targets = torch.zeros(2, 1, 32, 32)
        logits = torch.ones(2, 1, 32, 32) * -20.0  # sigmoid(-20) ≈ 0.0

        loss = criterion(logits, targets)
        assert loss.item() < 1e-4

    def test_soft_dice_worst_prediction_false_positive(self) -> None:
        criterion = SoftDiceLoss(smooth=1e-6)
        targets = torch.zeros(2, 1, 32, 32)
        logits = torch.ones(2, 1, 32, 32) * 20.0  # False alarm everywhere

        loss = criterion(logits, targets)
        assert loss.item() > 0.99

    def test_focal_tversky_loss_finite_and_gradients(self) -> None:
        criterion = FocalTverskyLoss(alpha=0.3, beta=0.7, gamma=4.0 / 3.0)
        logits = torch.randn(2, 1, 32, 32, requires_grad=True)
        targets = torch.randint(0, 2, (2, 1, 32, 32)).float()

        loss = criterion(logits, targets)
        assert torch.isfinite(loss)
        loss.backward()
        assert logits.grad is not None
        assert torch.isfinite(logits.grad).all()


# ===========================================================================
# 3. Segmentation Metrics Tests
# ===========================================================================


class TestMetrics:
    """Test IoU, Dice, Precision, Recall, and SegmentationMeter accumulator."""

    def test_empty_mask_conventions(self) -> None:
        # Case 1: Both empty -> 1.0
        m1 = compute_metrics_from_counts(tp=0, fp=0, fn=0, tn=1000)
        assert m1["iou"] == 1.0
        assert m1["dice"] == 1.0
        assert m1["precision"] == 1.0
        assert m1["recall"] == 1.0

        # Case 2: Clean water with false alarm (FP > 0) -> 0.0
        m2 = compute_metrics_from_counts(tp=0, fp=50, fn=0, tn=950)
        assert m2["iou"] == 0.0
        assert m2["dice"] == 0.0
        assert m2["precision"] == 0.0
        assert m2["recall"] == 0.0

        # Case 3: Positive spill completely missed (FN > 0, TP = 0) -> 0.0
        m3 = compute_metrics_from_counts(tp=0, fp=0, fn=50, tn=950)
        assert m3["iou"] == 0.0
        assert m3["dice"] == 0.0
        assert m3["precision"] == 0.0
        assert m3["recall"] == 0.0

    def test_standard_metrics_calculation(self) -> None:
        # TP=80, FP=20, FN=10, TN=890
        # IoU = 80 / (80 + 20 + 10) = 80 / 110 ≈ 0.72727
        # Dice = 160 / (160 + 20 + 10) = 160 / 190 ≈ 0.8421
        # Precision = 80 / (80 + 20) = 0.80
        # Recall = 80 / (80 + 10) = 80 / 90 ≈ 0.88889
        m = compute_metrics_from_counts(tp=80, fp=20, fn=10, tn=890)
        assert math.isclose(m["iou"], 80.0 / 110.0, rel_tol=1e-4)
        assert math.isclose(m["dice"], 160.0 / 190.0, rel_tol=1e-4)
        assert math.isclose(m["precision"], 0.80, rel_tol=1e-4)
        assert math.isclose(m["recall"], 80.0 / 90.0, rel_tol=1e-4)

    def test_segmentation_meter_streaming(self) -> None:
        meter = SegmentationMeter(threshold=0.50)
        logits1 = torch.tensor([[[[10.0, -10.0], [-10.0, -10.0]]]])  # Pred: [1, 0, 0, 0]
        targets1 = torch.tensor([[[[1.0, 0.0], [0.0, 0.0]]]])         # Target: [1, 0, 0, 0]
        # Batch 1: TP=1, FP=0, FN=0, TN=3
        meter.update(logits1, targets1)

        logits2 = torch.tensor([[[[10.0, 10.0], [-10.0, -10.0]]]])   # Pred: [1, 1, 0, 0]
        targets2 = torch.tensor([[[[1.0, 0.0], [1.0, 0.0]]]])         # Target: [1, 0, 1, 0]
        # Batch 2: TP=1, FP=1, FN=1, TN=1
        meter.update(logits2, targets2)

        res = meter.compute()
        # Cumulative: TP=2, FP=1, FN=1, TN=4
        assert res["tp"] == 2
        assert res["fp"] == 1
        assert res["fn"] == 1
        assert res["tn"] == 4
        assert math.isclose(res["iou"], 2.0 / (2.0 + 1.0 + 1.0), rel_tol=1e-4)
        assert res["n_samples"] == 2


# ===========================================================================
# 4. Validation Threshold Optimization Tests
# ===========================================================================


class TestThresholdOptimization:
    """Test validation-only threshold grid search."""

    def test_grid_generation(self) -> None:
        grid = generate_default_threshold_grid(0.10, 0.90, 0.02)
        assert len(grid) == 41
        assert grid[0] == 0.10
        assert grid[-1] == 0.90

    def test_threshold_selection_on_dummy_validation(self) -> None:
        # Create a mock model and validation loader
        class DummyModel(nn.Module):
            def forward(self, x: torch.Tensor) -> torch.Tensor:
                # Return fixed logits corresponding to prob ≈ 0.65
                # logit = log(0.65 / 0.35) ≈ 0.619
                return torch.full((x.shape[0], 1, x.shape[2], x.shape[3]), 0.619)

        # Ground truth targets have 1s where prob 0.65 is positive
        class MockDataset(torch.utils.data.Dataset):
            def __len__(self) -> int:
                return 4

            def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
                return torch.zeros(2, 32, 32), torch.ones(1, 32, 32)

        loader = torch.utils.data.DataLoader(MockDataset(), batch_size=2)
        result = optimize_threshold_on_validation(
            model=DummyModel(),
            val_loader=loader,
            device="cpu",
            thresholds=[0.30, 0.50, 0.60, 0.70, 0.80],
            target_metric="iou",
        )

        # For threshold <= 0.60, pred is 1 and target is 1 -> IoU = 1.0
        # For threshold >= 0.70, pred is 0 and target is 1 -> IoU = 0.0
        assert result.best_score == 1.0
        assert result.best_threshold in [0.30, 0.50, 0.60]
        assert result.target_metric == "iou"
        assert result.n_validation_samples == 4


# ===========================================================================
# 5. SAR Augmentation Tests
# ===========================================================================


class TestSARAugmentation:
    """Test discrete geometric SAR augmentations."""

    def test_spatial_consistency_between_image_and_mask(self) -> None:
        aug = SARGeometricAugmentation(p_hflip=1.0, p_vflip=0.0, p_rot90=0.0)
        img = torch.tensor([[[1.0, 2.0], [3.0, 4.0]], [[5.0, 6.0], [7.0, 8.0]]])  # [2, 2, 2]
        mask = torch.tensor([[[1.0, 0.0], [0.0, 0.0]]])                             # [1, 2, 2]

        out_img, out_mask = aug(img, mask)
        # Horizontal flip reverses last dimension
        assert out_img[0, 0, 0].item() == 2.0
        assert out_img[0, 0, 1].item() == 1.0
        assert out_mask[0, 0, 0].item() == 0.0
        assert out_mask[0, 0, 1].item() == 1.0

    def test_binary_mask_preservation_no_interpolation(self) -> None:
        aug = SARGeometricAugmentation(p_hflip=0.5, p_vflip=0.5, p_rot90=0.5, seed=42)
        img = torch.randn(2, 64, 64)
        mask = torch.randint(0, 2, (1, 64, 64)).float()

        for _ in range(20):
            _, out_mask = aug(img, mask)
            # Mask must be strictly {0.0, 1.0}
            vals = set(out_mask.unique().tolist())
            assert vals.issubset({0.0, 1.0})

    def test_determinism_with_seed(self) -> None:
        img = torch.randn(2, 32, 32)
        mask = torch.randint(0, 2, (1, 32, 32)).float()

        aug1 = SARGeometricAugmentation(seed=1234)
        out_img1, out_mask1 = aug1(img, mask)

        aug2 = SARGeometricAugmentation(seed=1234)
        out_img2, out_mask2 = aug2(img, mask)

        assert torch.equal(out_img1, out_img2)
        assert torch.equal(out_mask1, out_mask2)

    def test_identity_transform(self) -> None:
        transform = IdentityTransform()
        img = torch.randn(2, 32, 32)
        mask = torch.randn(1, 32, 32)
        out_img, out_mask = transform(img, mask)
        assert torch.equal(img, out_img)
        assert torch.equal(mask, out_mask)


# ===========================================================================
# 6. Real Dataset & Model Pipeline Integration
# ===========================================================================


@pytest.fixture(scope="module")
def manifest() -> DatasetManifest:
    if not MANIFEST_PATH.exists():
        pytest.skip(f"Manifest not found: {MANIFEST_PATH}")
    return DatasetManifest.load(MANIFEST_PATH)


@pytest.mark.real_data
class TestRealDataPipelineIntegration:
    """Test real TrujilloTileDataset sample loading through model and loss."""

    def test_real_dataset_sample_dimensions_and_types(
        self, manifest: DatasetManifest
    ) -> None:
        dataset = TrujilloTileDataset(
            manifest=manifest,
            split=SplitName.TRAIN,
            normalize=True,
        )
        assert len(dataset) == 13440
        image, mask = dataset[0]

        # Invariant contract checks
        assert isinstance(image, torch.Tensor)
        assert isinstance(mask, torch.Tensor)
        assert image.shape == (2, 512, 512)
        assert mask.shape == (1, 512, 512)
        assert image.dtype == torch.float32
        assert mask.dtype == torch.float32
        assert set(mask.unique().tolist()).issubset({0.0, 1.0})

    def test_real_batch_through_model_and_loss(
        self, manifest: DatasetManifest
    ) -> None:
        dataset = TrujilloTileDataset(
            manifest=manifest,
            split=SplitName.TRAIN,
            normalize=True,
        )
        loader = dataset.make_dataloader(batch_size=2, shuffle=False)
        images, masks = next(iter(loader))

        assert images.shape == (2, 2, 512, 512)
        assert masks.shape == (2, 1, 512, 512)

        model = ResNet34UNet(pretrained=False)
        model.eval()

        with torch.no_grad():
            logits = model(images)

        assert logits.shape == (2, 1, 512, 512)

        criterion = CombinedBCEAndDiceLoss()
        loss = criterion(logits, masks)
        assert torch.isfinite(loss)
        assert loss.item() > 0

        metrics = compute_batch_metrics(logits, masks, threshold=0.50)
        assert "iou" in metrics
        assert "dice" in metrics
        assert 0.0 <= metrics["iou"] <= 1.0


# ===========================================================================
# 7. Spatial Leakage Audit Unit Tests
# ===========================================================================


class TestSpatialLeakageAudit:
    """Test spatial bounding box overlap and proximity audit primitives."""

    def test_identical_bounding_boxes_100_percent_overlap(self) -> None:
        box_a = [10.0, 20.0, 11.0, 21.0]
        box_b = [10.0, 20.0, 11.0, 21.0]

        res = compute_box_overlap(box_a, box_b)
        assert res["is_overlapping"] is True
        assert math.isclose(res["overlap_pct_of_smaller"], 100.0, abs_tol=1e-5)
        assert math.isclose(res["intersection_area"], 1.0, abs_tol=1e-5)

    def test_disjoint_bounding_boxes_zero_overlap(self) -> None:
        box_a = [0.0, 0.0, 1.0, 1.0]
        box_b = [2.0, 2.0, 3.0, 3.0]

        res = compute_box_overlap(box_a, box_b)
        assert res["is_overlapping"] is False
        assert res["overlap_pct_of_smaller"] == 0.0
        assert res["intersection_area"] == 0.0

    def test_known_partial_overlap_50_percent(self) -> None:
        box_a = [0.0, 0.0, 2.0, 1.0]  # area = 2.0
        box_b = [1.0, 0.0, 3.0, 1.0]  # area = 2.0
        # intersection is [1.0, 0.0, 2.0, 1.0], area = 1.0 -> 50%

        res = compute_box_overlap(box_a, box_b)
        assert res["is_overlapping"] is True
        assert math.isclose(res["intersection_area"], 1.0, abs_tol=1e-5)
        assert math.isclose(res["overlap_pct_of_smaller"], 50.0, abs_tol=1e-5)

    def test_haversine_distance_known_equator_degree(self) -> None:
        # 1 degree of longitude at equator is ~111.195 km (2 * pi * 6371 / 360)
        dist = haversine_distance_km(0.0, 0.0, 1.0, 0.0)
        expected = (2.0 * math.pi * 6371.0) / 360.0
        assert math.isclose(dist, expected, rel_tol=1e-4)

    def test_deterministic_spatial_audit_results(self) -> None:
        b1 = [0.0, 0.0, 1.0, 1.0]
        b2 = [0.5, 0.5, 1.5, 1.5]
        res1 = compute_box_overlap(b1, b2)
        res2 = compute_box_overlap(b1, b2)
        assert res1 == res2

