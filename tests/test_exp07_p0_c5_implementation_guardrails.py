"""Regression guardrails for EXP-07-P0-C5 Implementation Contract and Reference Pipeline.

Locks all C5 decisions, corrections, mathematical contracts, and golden sample baselines.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pytest

from ocean_sentinel.ml.exp07_reference import (
    CLASS_WEIGHTS_SQRT_MEDIAN,
    DENSE_CLASSES,
    IGNORE_INDEX,
    OPS01Dataset,
    SOURCE_LABEL_TO_DENSE,
    TRAIN_LOG1P_MEAN,
    TRAIN_LOG1P_STD,
    compute_candidate_f_hybrid_weights,
    compute_confusion_matrix_12x12,
    compute_metrics_from_confusion_matrix,
    compute_validity_mask,
    preprocess_sar_image,
    remap_source_mask_to_dense,
)

try:
    import torch
    from ocean_sentinel.ml.exp07_reference import ResNet18UNet, create_exp07_loss
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


REPO_ROOT = Path(__file__).resolve().parent.parent

EXP06_BEST_PT = REPO_ROOT / "experiments" / "performance" / "exp06_positive_bce_weight" / "best_model.pt"
PART_I_MANIFEST = REPO_ROOT / "data" / "metadata" / "internal_development_split_manifest.json"
OPS01_MANIFEST_V4 = REPO_ROOT / "data" / "metadata" / "ops01_physical_dataset_manifest_v4.json"
OPS01_TAXONOMY = REPO_ROOT / "data" / "metadata" / "ops01_taxonomy_v1.json"

C5_REPORT = REPO_ROOT / "experiments" / "EXP-07" / "EXP07_P0_C5_IMPLEMENTATION_AUDIT_AND_CPU_REFERENCE_REPORT_20260913.md"
C5_CONTRACT_JSON = REPO_ROOT / "data" / "metadata" / "exp07_p0_c5_implementation_contract_v1.json"
C5_REPRO_JSON = REPO_ROOT / "data" / "metadata" / "exp07_p0_c5_reproducibility_contract_v1.json"
GOV_RULES_JSON = REPO_ROOT / "data" / "metadata" / "ocean_sentinel_governance_rules_v1.json"
INCIDENTS_JSON = REPO_ROOT / "data" / "metadata" / "ocean_sentinel_incident_learning_register_v1.json"
TELEMETRY = REPO_ROOT / "scratch" / "exp07_p0_c5_run_state.json"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


# ==============================================================================
# 1. Frozen Hashes
# ==============================================================================

class TestC5FrozenHashes:
    def test_01_frozen_exp06_hash(self):
        assert EXP06_BEST_PT.exists()
        assert sha256_file(EXP06_BEST_PT) == "B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF"

    def test_02_frozen_part_i_hash(self):
        assert PART_I_MANIFEST.exists()
        assert sha256_file(PART_I_MANIFEST) == "17F1FF35146C7CE62E90D6FCE7F197B711B55E3C3CB599610578443208669072"

    def test_03_frozen_ops01_v4_manifest_hash(self):
        assert OPS01_MANIFEST_V4.exists()
        assert sha256_file(OPS01_MANIFEST_V4) == "FF1680C9135EF5CD9C7B77FBC8373953F9924BD5BE2830617EB0EF386C8DC85E"


# ==============================================================================
# 2. C5 Artifacts and Governance
# ==============================================================================

class TestC5ArtifactsAndGovernance:
    def test_04_c5_artifacts_exist(self):
        assert C5_REPORT.exists()
        assert C5_CONTRACT_JSON.exists()
        assert C5_REPRO_JSON.exists()

    def test_05_gov_rule_059_enacted(self):
        with open(GOV_RULES_JSON, "r", encoding="utf-8") as f:
            gov = json.load(f)
        rules = {r["rule_id"]: r for r in gov["rules"]}
        assert "GOV-RULE-059" in rules
        r59 = rules["GOV-RULE-059"]
        assert "BatchNorm" in r59["title"]
        assert "optimization batch" in r59["title"]

    def test_06_incident_inc_p0_c5_001_registered(self):
        with open(INCIDENTS_JSON, "r", encoding="utf-8") as f:
            inc = json.load(f)
        incidents = {i["incident_id"]: i for i in inc["incidents"]}
        assert "INC-P0-C5-001" in incidents
        i51 = incidents["INC-P0-C5-001"]
        assert "BatchNorm" in i51["title"]
        assert i51["status"] == "RESOLVED"

    def test_07_batchnorm_vs_gradient_accumulation_separated(self):
        with open(C5_CONTRACT_JSON, "r", encoding="utf-8") as f:
            contract = json.load(f)
        corrections = {c["issue_id"]: c for c in contract["corrections_to_c4"]}
        assert "CORR-C5-001" in corrections
        assert "INC-P0-C5-001" in corrections["CORR-C5-001"]["incident_id"]


# ==============================================================================
# 3. Taxonomy and Excluded Class Remapping
# ==============================================================================

class TestC5TaxonomyAndRemapping:
    def test_08_canonical_dense_class_count(self):
        assert len(DENSE_CLASSES) == 12
        assert DENSE_CLASSES[0] == "BG"
        assert DENSE_CLASSES[11] == "HM"

    def test_09_hm_and_os_identities(self):
        with open(OPS01_TAXONOMY, "r", encoding="utf-8") as f:
            tax = json.load(f)
        by_abbr = {c["abbreviation"]: c for c in tax["classes"]}
        assert by_abbr["HM"]["class_name"] == "Artificial / Anthropogenic Objects"
        assert by_abbr["OS"]["training_eligible"] is False
        assert by_abbr["SI"]["training_eligible"] is False
        assert by_abbr["IB"]["training_eligible"] is False

    def test_10_excluded_classes_mapped_to_ignore_index(self):
        # Excluded source labels: 3 (IB), 9 (SI), 14 (OS)
        synthetic_mask = np.array([0, 1, 2, 3, 4, 9, 10, 13, 14], dtype=np.uint8)
        dense = remap_source_mask_to_dense(synthetic_mask)
        assert dense[0] == 0   # BG
        assert dense[1] == 1   # AF
        assert dense[2] == 2   # BS
        assert dense[3] == -100 # IB -> ignore
        assert dense[4] == 3   # LWA
        assert dense[5] == -100 # SI -> ignore
        assert dense[6] == 8   # WS
        assert dense[7] == 11  # HM
        assert dense[8] == -100 # OS -> ignore


# ==============================================================================
# 4. Radiometric Preprocessing and Normalization
# ==============================================================================

class TestC5RadiometricAndNormalization:
    def test_11_normalization_constants(self):
        assert TRAIN_LOG1P_MEAN == 4.2756
        assert TRAIN_LOG1P_STD == 0.3866

    def test_12_validity_mask_identifies_zeros(self):
        img = np.array([[0.0, 50.0], [100.0, 0.0]], dtype=np.float32)
        v = compute_validity_mask(img)
        assert bool(v[0, 0]) is False
        assert bool(v[0, 1]) is True
        assert bool(v[1, 0]) is True
        assert bool(v[1, 1]) is False

    def test_13_preprocessing_pipeline_zeros_padding(self):
        raw = np.array([[[0.0, 71.0], [150.0, 0.0]]], dtype=np.float32)
        norm, v = preprocess_sar_image(raw)
        assert norm[0, 0, 0] == 0.0
        assert norm[0, 1, 1] == 0.0
        # Valid pixel 71.0: log1p(71) = 4.276666 -> (4.276666 - 4.2756)/0.3866 ≈ 0.00276
        assert abs(norm[0, 0, 1] - 0.00276) < 1e-3


# ==============================================================================
# 5. Sampler and Loss Math
# ==============================================================================

class TestC5SamplerAndLossMath:
    def test_14_hybrid_sampler_weights_sum_to_one(self):
        weights, samples, diag = compute_candidate_f_hybrid_weights()
        assert len(weights) == 72
        assert abs(float(np.sum(weights)) - 1.0) < 1e-10
        assert diag["max_parent_multiplier"] < 1.45
        assert diag["max_parent_multiplier"] > 1.30
        assert diag["rare_class_exposures"]["HM"] >= 3.10
        assert diag["rare_class_exposures"]["LWA"] >= 3.10
        assert diag["rare_class_exposures"]["Eddy"] >= 3.10

    def test_15_loss_weights_exact_values(self):
        # Verify BG and HM weights (compatible with C5 baseline and C6/C8 source-recalculated values)
        assert abs(CLASS_WEIGHTS_SQRT_MEDIAN[0] - 0.273233) < 1e-3 or abs(CLASS_WEIGHTS_SQRT_MEDIAN[0] - 0.272584) < 1e-4
        assert abs(CLASS_WEIGHTS_SQRT_MEDIAN[11] - 12.159536) < 1e-2 or abs(CLASS_WEIGHTS_SQRT_MEDIAN[11] - 12.151197) < 1e-4
        ratio = CLASS_WEIGHTS_SQRT_MEDIAN[11] / CLASS_WEIGHTS_SQRT_MEDIAN[0]
        assert abs(ratio - 44.5) < 0.2


# ==============================================================================
# 6. Architecture Contract
# ==============================================================================

@pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not installed")
class TestC5ArchitectureContract:
    def test_16_resnet18_unet_parameter_counts(self):
        model = ResNet18UNet()
        trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
        total = sum(p.numel() for p in model.parameters()) + sum(b.numel() for b in model.buffers())
        bn_count = sum(1 for m in model.modules() if isinstance(m, torch.nn.BatchNorm2d))
        
        assert trainable == 14310860
        # 14,310,860 trainable + 11,776 fp buffers = 14,322,636 (+ 30 int64 buffers = 14,322,666)
        assert total in (14322636, 14322666)
        assert bn_count == 30

    def test_17_resnet18_unet_forward_shape(self):
        model = ResNet18UNet()
        x = torch.randn(2, 1, 256, 256)
        logits = model(x)
        assert logits.shape == (2, 12, 256, 256)
        assert logits.dtype == torch.float32


# ==============================================================================
# 7. Dataset Reader and Golden Samples
# ==============================================================================

class TestC5DatasetAndGoldenSamples:
    def test_18_dataset_partitions_load(self):
        ds_train = OPS01Dataset(partition="TRAIN", as_torch=False)
        ds_dev = OPS01Dataset(partition="DEV", as_torch=False)
        ds_holdout = OPS01Dataset(partition="HOLDOUT", as_torch=False)
        
        assert len(ds_train) == 72
        assert len(ds_dev) == 39
        assert len(ds_holdout) == 36

    def test_19_golden_sample_train_hashes_and_stats(self):
        ds = OPS01Dataset(partition="TRAIN", as_torch=False)
        item0 = ds[0]
        img_path = REPO_ROOT / ds.samples[0]["derived_image_path"]
        msk_path = REPO_ROOT / ds.samples[0]["derived_mask_path"]
        
        assert sha256_file(img_path) == "AD477CB836F2A5DF1018390EA264A96FD89BF8EA00A5D05B3E6CAC8C4FC5B328"
        assert sha256_file(msk_path) == "E040D38339D91BAB9AE4CE05E956BD3B48C73B3DDF55DFF75E6944D0761807EE"
        assert item0["validity_mask"].sum() == 65536
        assert abs(float(item0["raw_image"].mean()) - 131.1164) < 0.1

    def test_20_golden_sample_dev_hashes_and_stats(self):
        ds = OPS01Dataset(partition="DEV", as_torch=False)
        img_path = REPO_ROOT / ds.samples[0]["derived_image_path"]
        msk_path = REPO_ROOT / ds.samples[0]["derived_mask_path"]
        
        assert sha256_file(img_path) == "EB5F258965E169990B5033A3F87D3A3FD8926CA7161C1D6DDA752A70E684B11E"
        assert sha256_file(msk_path) == "14960734A5D4B76B188759408A04BFFC91A1AB9211601E4222AB849505B9162D"

    def test_21_golden_sample_holdout_sea_ice_remapped(self):
        ds = OPS01Dataset(partition="HOLDOUT", as_torch=False)
        item0 = ds[0]
        img_path = REPO_ROOT / ds.samples[0]["derived_image_path"]
        msk_path = REPO_ROOT / ds.samples[0]["derived_mask_path"]
        
        assert sha256_file(img_path) == "D1D293BA927798C147DEE34686078CFBCB1BBFBBE9EB935F786BBAAC963E5859"
        assert sha256_file(msk_path) == "B8047AA937A6536DE34DADB054364BBF7FCC67D4147FF3F259DFEBF75F5CDA5A"
        # Source mask contains 9 (Sea Ice), which must be remapped to -100
        assert -100 in item0["target"]
        assert 0 in item0["target"]


# ==============================================================================
# 8. Evaluation Metrics and Absent Class Handling
# ==============================================================================

class TestC5MetricsAndAbsentClasses:
    def test_22_confusion_matrix_and_absent_classes(self):
        # 2 valid pixels: class 0 and class 1
        targets = np.array([0, 1, -100], dtype=np.int64)
        preds = np.array([0, 1, 5], dtype=np.int64)
        cm = compute_confusion_matrix_12x12(preds, targets)
        
        assert cm[0, 0] == 1
        assert cm[1, 1] == 1
        assert cm.sum() == 2  # The pixel with target -100 is excluded
        
        metrics = compute_metrics_from_confusion_matrix(cm)
        assert metrics["iou_per_class"]["BG"] == 1.0
        assert metrics["iou_per_class"]["AF"] == 1.0
        assert metrics["iou_per_class"]["BS"] is None # Absent class
        assert metrics["mIoU_all"] == 1.0
        assert metrics["mIoU_phenomena"] == 1.0
        assert metrics["num_classes_present_all"] == 2
        assert metrics["num_classes_present_phenomena"] == 1

    def test_23_binary_threshold_prohibition(self):
        with open(C5_CONTRACT_JSON, "r", encoding="utf-8") as f:
            c = json.load(f)
        audit = {item["decision_item"]: item for item in c["adversarial_contract_audit_table"]}
        assert "Z. Multiclass Prediction Rule" in audit
        z = audit["Z. Multiclass Prediction Rule"]
        assert "argmax" in z["correction"]
        assert "prohibit binary" in z["correction"]

    def test_24_holdout_selection_disclosure(self):
        with open(C5_CONTRACT_JSON, "r", encoding="utf-8") as f:
            c = json.load(f)
        audit = {item["decision_item"]: item for item in c["adversarial_contract_audit_table"]}
        ad = audit["AD. Holdout Reporting"]
        assert "HOLDOUT_PARTIALLY_USED_FOR_SELECTION" in ad["current_c4_statement"]
        assert "pristine" in ad["ambiguity_risk"]


# ==============================================================================
# 9. Telemetry Consistency
# ==============================================================================

class TestC5TelemetryConsistency:
    def test_25_telemetry_valid(self):
        with open(TELEMETRY, "r", encoding="utf-8") as f:
            tel = json.load(f)
        assert tel["phase"] == "EXP-07-P0-C5"
        assert tel["git_state"]["staged"] == 0
        assert tel["git_state"]["branch"] == "master"
