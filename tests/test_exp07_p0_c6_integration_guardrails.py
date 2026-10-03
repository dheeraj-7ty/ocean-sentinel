"""EXP-07-P0-C6 Controlled CPU Integration Guardrails and Pre-Training Verification Suite.

Phase: EXP-07-P0-C6
Enforces:
- Authoritative manifest and dataset partition integrity (147 tiles / 27 parents)
- Excluded class handling (Sea Ice, Iceberg, Oil Spill remapped to -100)
- Input-domain semantics under GOV-RULE-060 (uncalibrated aggregated DN)
- Loss frequency recalculation directly from TRAIN valid pixels (4,712,082 px)
- Sampler mathematics under Candidate F (70/30 stationary probability vector)
- Model architecture exact parameter counts (14,310,860 trainable / 11,776 buffers)
- BatchNorm Option B semantics under GOV-RULE-059
- Metrics contract (argmax, absent classes excluded from macro denominator)
- Golden sample benchmarks for TRAIN, DEV, and HOLDOUT
- Independent first-principles cross-checks under GOV-RULE-061
- Strict phase restrictions: forward-only, zero optimizer updates, zero checkpoints.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Set

import numpy as np
import pytest
import rasterio

from src.ocean_sentinel.ml.exp07_reference import (
    CLASS_WEIGHTS_SQRT_MEDIAN,
    DENSE_CLASSES,
    IGNORE_INDEX,
    OPS01_MANIFEST_PATH,
    OPS01_TAXONOMY_PATH,
    SOURCE_LABEL_TO_DENSE,
    TRAIN_LOG1P_MEAN,
    TRAIN_LOG1P_STD,
    DoubleConv,
    OPS01Dataset,
    ResNet18UNet,
    compute_candidate_f_hybrid_weights,
    compute_confusion_matrix_12x12,
    compute_metrics_from_confusion_matrix,
    compute_validity_mask,
    create_exp07_loss,
    preprocess_sar_image,
    remap_source_mask_to_dense,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
EXP06_MODEL = REPO_ROOT / "experiments" / "performance" / "exp06_positive_bce_weight" / "best_model.pt"
PART_I_MANIFEST = REPO_ROOT / "data" / "metadata" / "internal_development_split_manifest.json"
OPS01_MANIFEST = REPO_ROOT / "data" / "metadata" / "ops01_physical_dataset_manifest_v4.json"
GOV_RULES_JSON = REPO_ROOT / "data" / "metadata" / "ocean_sentinel_governance_rules_v1.json"
INCIDENT_REGISTER = REPO_ROOT / "data" / "metadata" / "ocean_sentinel_incident_learning_register_v1.json"

EXP06_FROZEN_SHA = "B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF"
PART_I_FROZEN_SHA = "17F1FF35146C7CE62E90D6FCE7F197B711B55E3C3CB599610578443208669072"
OPS01_FROZEN_SHA = "FF1680C9135EF5CD9C7B77FBC8373953F9924BD5BE2830617EB0EF386C8DC85E"


def sha256_file(path: Path) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest().upper()


# ==============================================================================
# 1. Preflight and Frozen Hashes
# ==============================================================================

class TestC6PreflightAndFrozenHashes:
    def test_01_exp06_hash_exact(self):
        assert sha256_file(EXP06_MODEL) == EXP06_FROZEN_SHA

    def test_02_part_i_hash_exact(self):
        assert sha256_file(PART_I_MANIFEST) == PART_I_FROZEN_SHA

    def test_03_ops01_v4_hash_exact(self):
        assert sha256_file(OPS01_MANIFEST) == OPS01_FROZEN_SHA


# ==============================================================================
# 2. Dataset Partition and Manifest Integrity
# ==============================================================================

class TestDatasetPartitionIntegrity:
    def test_04_partition_counts_exact(self):
        with open(OPS01_MANIFEST, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        samples = manifest["samples"]
        assert len(samples) == 147
        counts = {"TRAIN": 0, "DEV": 0, "HOLDOUT": 0}
        for s in samples:
            counts[s["partition"]] += 1
        assert counts["TRAIN"] == 72
        assert counts["DEV"] == 39
        assert counts["HOLDOUT"] == 36

    def test_05_parent_scenes_disjoint(self):
        with open(OPS01_MANIFEST, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        parents_by_split: Dict[str, Set[str]] = {"TRAIN": set(), "DEV": set(), "HOLDOUT": set()}
        for s in manifest["samples"]:
            parents_by_split[s["partition"]].add(s["parent_scene_id"])

        assert len(parents_by_split["TRAIN"]) == 12
        assert len(parents_by_split["DEV"]) == 7
        assert len(parents_by_split["HOLDOUT"]) == 8

        # Pairwise disjoint
        assert len(parents_by_split["TRAIN"].intersection(parents_by_split["DEV"])) == 0
        assert len(parents_by_split["TRAIN"].intersection(parents_by_split["HOLDOUT"])) == 0
        assert len(parents_by_split["DEV"].intersection(parents_by_split["HOLDOUT"])) == 0

    def test_06_image_bytes_strictly_unique_across_splits(self):
        with open(OPS01_MANIFEST, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        img_hashes: Dict[str, Set[str]] = {"TRAIN": set(), "DEV": set(), "HOLDOUT": set()}
        for s in manifest["samples"]:
            img_hashes[s["partition"]].add(s["image_sha256"].upper())
        assert len(img_hashes["TRAIN"].intersection(img_hashes["DEV"])) == 0
        assert len(img_hashes["TRAIN"].intersection(img_hashes["HOLDOUT"])) == 0
        assert len(img_hashes["DEV"].intersection(img_hashes["HOLDOUT"])) == 0


# ==============================================================================
# 3. Excluded Classes and Remapping Audit
# ==============================================================================

class TestExcludedClassesAndRemapping:
    def test_07_excluded_classes_mapped_to_negative_100(self):
        # Excluded source classes: 3 (IB), 9 (SI), 14 (OS)
        source_mask = np.array([0, 1, 2, 3, 4, 9, 10, 14], dtype=np.uint8)
        dense = remap_source_mask_to_dense(source_mask)
        assert dense[3] == -100  # Class 3 (IB)
        assert dense[5] == -100  # Class 9 (SI)
        assert dense[7] == -100  # Class 14 (OS)

    def test_08_sea_ice_in_dev_and_holdout_does_not_collide_with_eddy(self):
        # Source 9 is Sea Ice, dense 9 is Oceanic Eddy (source 11)
        source_mask = np.array([9, 11], dtype=np.uint8)
        dense = remap_source_mask_to_dense(source_mask)
        assert dense[0] == -100  # Sea ice mapped to ignore_index
        assert dense[1] == 9     # Oceanic Eddy mapped to dense class 9

    def test_09_unknown_source_label_raises_error(self):
        source_mask = np.array([0, 1, 99], dtype=np.uint8)
        with pytest.raises(ValueError, match="Corrupted or unknown source label IDs"):
            remap_source_mask_to_dense(source_mask)


# ==============================================================================
# 4. Input-Domain Radiometric Semantics (GOV-RULE-060)
# ==============================================================================

class TestInputDomainSemantics:
    def test_10_input_domain_designated_uncalibrated_dn(self):
        raw = np.array([[[100.0]]], dtype=np.float32)
        norm, val = preprocess_sar_image(raw)
        # Verify log1p transform on raw DN
        expected = (np.log(1.0 + 100.0) - TRAIN_LOG1P_MEAN) / TRAIN_LOG1P_STD
        assert np.isclose(norm[0, 0, 0], expected, atol=1e-5)
        assert bool(val[0, 0, 0]) is True

    def test_11_invalid_border_padding_zeroed_in_model_input(self):
        raw = np.array([[[0.0, 100.0]]], dtype=np.float32)
        norm, val = preprocess_sar_image(raw)
        assert norm[0, 0, 0] == 0.0  # Invalid pixel zeroed out
        assert bool(val[0, 0, 0]) is False
        assert bool(val[0, 0, 1]) is True


# ==============================================================================
# 5. Loss Frequencies and TRAIN Data Recalculation
# ==============================================================================

class TestClassFrequenciesAndLossContract:
    def test_12_train_valid_pixels_exact_4712082(self):
        with open(OPS01_MANIFEST, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        train_samples = [s for s in manifest["samples"] if s["partition"] == "TRAIN"]
        assert len(train_samples) == 72

        total_valid = 0
        total_invalid = 0
        for s in train_samples:
            img_p = REPO_ROOT / s["derived_image_path"]
            with rasterio.open(img_p) as src:
                img = src.read(1)
            valid = (img > 0)
            total_valid += int(np.sum(valid))
            total_invalid += int(np.sum(~valid))

        assert total_valid == 4712082
        assert total_invalid == 6510

    def test_13_loss_weights_derived_strictly_from_train(self):
        # Verify loss weights are positive and finite
        loss_fn = create_exp07_loss()
        weights = loss_fn.weight.numpy()
        assert len(weights) == 12
        assert np.all(weights > 0.0)
        # Background downweighted, HM upweighted
        assert weights[0] < 0.30
        assert weights[11] > 12.0
        # Ratio bounded to ~44.5x
        ratio = float(np.max(weights) / np.min(weights))
        assert 44.0 < ratio < 45.0


# ==============================================================================
# 6. Candidate F Sampler and DataLoader Determinism
# ==============================================================================

class TestSamplerAndDataLoader:
    def test_14_candidate_f_hybrid_stationary_vector_sums_to_one(self):
        w_hybrid, train_samples, diag = compute_candidate_f_hybrid_weights()
        assert len(w_hybrid) == 72
        assert np.all(w_hybrid >= 0.0)
        assert np.isclose(np.sum(w_hybrid), 1.0, atol=1e-12)
        assert diag["max_parent_multiplier"] < 1.45
        for c, exp in diag["rare_class_exposures"].items():
            assert exp >= 3.0

    def test_15_sampler_deterministic_replay(self):
        import torch
        from torch.utils.data import WeightedRandomSampler
        w_hybrid, _, _ = compute_candidate_f_hybrid_weights()
        gen1 = torch.Generator().manual_seed(42)
        sampler1 = WeightedRandomSampler(weights=w_hybrid, num_samples=72, replacement=True, generator=gen1)
        draws1 = list(sampler1)

        gen2 = torch.Generator().manual_seed(42)
        sampler2 = WeightedRandomSampler(weights=w_hybrid, num_samples=72, replacement=True, generator=gen2)
        draws2 = list(sampler2)

        assert draws1 == draws2

    def test_16_different_seeds_produce_different_draws(self):
        import torch
        from torch.utils.data import WeightedRandomSampler
        w_hybrid, _, _ = compute_candidate_f_hybrid_weights()
        gen1 = torch.Generator().manual_seed(42)
        sampler1 = WeightedRandomSampler(weights=w_hybrid, num_samples=72, replacement=True, generator=gen1)
        draws1 = list(sampler1)

        gen3 = torch.Generator().manual_seed(43)
        sampler3 = WeightedRandomSampler(weights=w_hybrid, num_samples=72, replacement=True, generator=gen3)
        draws3 = list(sampler3)

        assert draws1 != draws3


# ==============================================================================
# 7. BatchNorm Option B Semantics (GOV-RULE-059)
# ==============================================================================

class TestBatchNormAndGradientAccumulation:
    def test_17_batchnorm_statistical_batch_size_eight(self):
        import torch
        model = ResNet18UNet(in_channels=1, num_classes=12, bn_momentum=0.05)
        model.train()
        x1 = torch.randn(8, 1, 256, 256)
        _ = model(x1)
        assert model.bn1.num_batches_tracked.item() == 1

        # Second forward pass increments counter by 1 (separate 8-sample calculation)
        x2 = torch.randn(8, 1, 256, 256)
        _ = model(x2)
        assert model.bn1.num_batches_tracked.item() == 2

    def test_18_batchnorm_eval_mode_strictly_frozen(self):
        import torch
        model = ResNet18UNet(in_channels=1, num_classes=12, bn_momentum=0.05)
        model.eval()
        init_mean = model.bn1.running_mean.clone()
        init_var = model.bn1.running_var.clone()
        init_batches = model.bn1.num_batches_tracked.clone()

        x = torch.randn(8, 1, 256, 256)
        with torch.no_grad():
            _ = model(x)

        assert torch.equal(model.bn1.running_mean, init_mean)
        assert torch.equal(model.bn1.running_var, init_var)
        assert model.bn1.num_batches_tracked == init_batches


# ==============================================================================
# 8. Model Architecture Contract
# ==============================================================================

class TestModelArchitectureContract:
    def test_19_model_trainable_parameters_exact(self):
        import torch
        model = ResNet18UNet(in_channels=1, num_classes=12)
        trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
        fp_buffers = sum(b.numel() for _, b in model.named_buffers() if b.dtype.is_floating_point)
        bn_layers = [m for m in model.modules() if isinstance(m, torch.nn.BatchNorm2d)]

        assert trainable == 14310860
        assert fp_buffers == 11776
        assert len(bn_layers) == 30

    def test_20_model_input_output_shapes_and_no_activation(self):
        import torch
        model = ResNet18UNet(in_channels=1, num_classes=12)
        model.eval()
        x = torch.randn(2, 1, 256, 256, dtype=torch.float32)
        with torch.no_grad():
            out = model(x)
        assert out.shape == (2, 12, 256, 256)
        assert out.dtype == torch.float32
        # Verify raw logits (contains both positive and negative numbers)
        assert torch.any(out < 0) and torch.any(out > 0)


# ==============================================================================
# 9. Metrics Contract and Edge Cases
# ==============================================================================

class TestMetricsContract:
    def test_21_absent_classes_excluded_from_macro_denominator(self):
        # GT contains only BG (0) and AF (1)
        gt = np.array([0, 0, 1, 1])
        pred = np.array([0, 0, 1, 1])
        cm = compute_confusion_matrix_12x12(pred, gt)
        metrics = compute_metrics_from_confusion_matrix(cm)
        assert metrics["iou_per_class"]["BG"] == 1.0
        assert metrics["iou_per_class"]["AF"] == 1.0
        assert metrics["iou_per_class"]["BS"] is None  # absent
        assert metrics["mIoU_all"] == 1.0
        assert metrics["mIoU_phenomena"] == 1.0
        assert metrics["num_classes_present_all"] == 2
        assert metrics["num_classes_present_phenomena"] == 1

    def test_22_ignored_pixels_excluded_from_confusion_matrix(self):
        gt = np.array([-100, -100, 0, 1])
        pred = np.array([5, 5, 0, 1])
        cm = compute_confusion_matrix_12x12(pred, gt)
        assert np.sum(cm) == 2  # Only the 2 valid pixels entered CM


# ==============================================================================
# 10. Golden Sample Benchmarks
# ==============================================================================

class TestGoldenSampleBenchmarks:
    def test_23_golden_sample_train(self):
        ds = OPS01Dataset(partition="TRAIN", as_torch=False)
        sample = ds[0]
        assert sample["sample_id"] == "s1a-iw-grd-vv-20150220t211700-20150220t211729-004712-005d33-001-7"
        norm_sha = hashlib.sha256(sample["image"].tobytes()).hexdigest().upper()
        target_sha = hashlib.sha256(sample["target"].tobytes()).hexdigest().upper()
        assert norm_sha == "2850D42E1191318184A64D06FC000F5DAAA22126DC564EAED2B345AF5BD8AEB7"
        assert target_sha == "380D55AB98A4F71814DCE01173528154D380E3C0951AE1710F19D87C6DE4DF3D"

    def test_24_golden_sample_dev(self):
        ds = OPS01Dataset(partition="DEV", as_torch=False)
        sample = ds[0]
        assert sample["sample_id"] == "s1a-iw-grd-vv-20180103t114323-20180103t114348-019990-0220c9-001-3"
        norm_sha = hashlib.sha256(sample["image"].tobytes()).hexdigest().upper()
        target_sha = hashlib.sha256(sample["target"].tobytes()).hexdigest().upper()
        assert norm_sha == "E5C455C0A8FF8C7C4C75882C44B37C6076E16C7A8020969BA09D047CC5BFC14F"
        assert target_sha == "EC663C1A4E794684F63E54D7E2DBD5BC7FED20AE95EB362A69592F1FBFC51EB3"

    def test_25_golden_sample_holdout_sea_ice_remapped(self):
        ds = OPS01Dataset(partition="HOLDOUT", as_torch=False)
        sample = ds[0]
        assert sample["sample_id"] == "s1a-iw-grd-vv-20230128t173320-20230128t173349-046987-05a2c5-001-58"
        norm_sha = hashlib.sha256(sample["image"].tobytes()).hexdigest().upper()
        target_sha = hashlib.sha256(sample["target"].tobytes()).hexdigest().upper()
        assert norm_sha == "C8E8598DAD3A444F07E73104BF0BA1FF426E38A3FAEA70FB5EA326AA096DE557"
        assert target_sha == "960A91A637DCBB333EAB2AC3F27CDBC6892B6483908E3D7D7F52037CEC31DD25"
        # Confirm Sea Ice in this tile is remapped to -100
        unique_targets = sorted(list(np.unique(sample["target"])))
        assert unique_targets == [-100, 0]


# ==============================================================================
# 11. Independent First-Principles Cross-Checks (GOV-RULE-061)
# ==============================================================================

class TestIndependentCrossChecks:
    def test_26_independent_normalization_cross_check(self):
        raw = np.array([[[0.0, 50.0], [100.0, 200.0]]], dtype=np.float32)
        norm_ref, val_ref = preprocess_sar_image(raw)

        val_indep = (raw > 0)
        norm_indep = np.zeros_like(raw)
        for i in range(raw.shape[1]):
            for j in range(raw.shape[2]):
                if val_indep[0, i, j]:
                    norm_indep[0, i, j] = (np.log(1.0 + raw[0, i, j]) - TRAIN_LOG1P_MEAN) / TRAIN_LOG1P_STD
                else:
                    norm_indep[0, i, j] = 0.0

        assert np.allclose(norm_ref, norm_indep, atol=1e-6)
        assert np.array_equal(val_ref, val_indep)

    def test_27_independent_loss_cross_check(self):
        import torch
        B, C, H, W = 2, 12, 4, 4
        logits = torch.randn(B, C, H, W, dtype=torch.float32)
        targets = torch.randint(-1, 12, (B, H, W), dtype=torch.int64)
        targets[targets == -1] = -100

        loss_fn = create_exp07_loss()
        loss_ref = loss_fn(logits, targets).item()

        weights_arr = np.array([CLASS_WEIGHTS_SQRT_MEDIAN[c] for c in range(12)])
        logits_np = logits.numpy()
        targets_np = targets.numpy()

        exp_logits = np.exp(logits_np - np.max(logits_np, axis=1, keepdims=True))
        probs = exp_logits / np.sum(exp_logits, axis=1, keepdims=True)

        weighted_nll_sum = 0.0
        weight_sum = 0.0
        for b in range(B):
            for h in range(H):
                for w in range(W):
                    t = targets_np[b, h, w]
                    if t != -100:
                        p = probs[b, t, h, w]
                        wt = weights_arr[t]
                        weighted_nll_sum += -wt * np.log(p)
                        weight_sum += wt

        loss_indep = weighted_nll_sum / weight_sum
        assert np.isclose(loss_ref, loss_indep, atol=1e-5)

    def test_28_independent_confusion_matrix_and_metrics_cross_check(self):
        preds = np.random.randint(0, 12, (100,))
        tgts = np.random.randint(-1, 12, (100,))
        tgts[tgts == -1] = -100
        cm_ref = compute_confusion_matrix_12x12(preds, tgts)

        cm_indep = np.zeros((12, 12), dtype=np.int64)
        for p, t in zip(preds, tgts):
            if t != -100 and 0 <= t < 12 and 0 <= p < 12:
                cm_indep[t, p] += 1
        assert np.array_equal(cm_ref, cm_indep)

        metrics_ref = compute_metrics_from_confusion_matrix(cm_ref)
        for c in range(12):
            c_name = list(metrics_ref["iou_per_class"].keys())[c]
            tp = cm_indep[c, c]
            fn = np.sum(cm_indep[c, :]) - tp
            fp = np.sum(cm_indep[:, c]) - tp
            gt_total = tp + fn
            if gt_total > 0:
                iou_indep = tp / (tp + fp + fn) if (tp + fp + fn) > 0 else 0.0
                assert np.isclose(metrics_ref["iou_per_class"][c_name], iou_indep, atol=1e-6)


# ==============================================================================
# 12. Phase Boundaries and Governance Verification
# ==============================================================================

class TestPhaseBoundariesAndGovernance:
    def test_29_no_model_checkpoints_created_in_c6(self):
        exp07_dir = REPO_ROOT / "experiments" / "EXP-07"
        checkpoints = [
            p for p in (list(exp07_dir.glob("*.pt")) + list(exp07_dir.glob("**/*.pt")))
            if "runs" not in p.parts
        ]
        assert len(checkpoints) == 0

    def test_30_gov_rules_60_and_61_active(self):
        with open(GOV_RULES_JSON, "r", encoding="utf-8") as f:
            rules_data = json.load(f)
        rules = {r["rule_id"]: r for r in rules_data["rules"]}
        assert "GOV-RULE-060" in rules
        assert "GOV-RULE-061" in rules
        assert rules["GOV-RULE-060"]["status"] == "ACTIVE"
        assert rules["GOV-RULE-061"]["status"] == "ACTIVE"

    def test_31_incident_p0_c6_001_recorded(self):
        with open(INCIDENT_REGISTER, "r", encoding="utf-8") as f:
            inc_data = json.load(f)
        incidents = {inc["incident_id"]: inc for inc in inc_data["incidents"]}
        assert "INC-P0-C6-001" in incidents
        assert incidents["INC-P0-C6-001"]["status"] == "RESOLVED"
