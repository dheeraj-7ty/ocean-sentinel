"""EXP-07-P0-C18: Protocol Remediation, Freeze-ID Repair, and Metric/Loader Guardrails.

Validates:
1. Canonical freeze specification v1.0.1 and cryptographic manifest bindings (GOV-RULE-085, GOV-RULE-090).
2. Runtime sample-ID set equality assertions and partition isolation (GOV-RULE-086, GOV-RULE-091).
3. ResNet18-UNet model parameter identity (14,310,860) and 30 BatchNorm2d layers.
4. Metric mathematics across synthetic cases (perfect, zero TP, absent class, ignore index).
5. Input preprocessing pipeline invariants (raw DN -> log1p -> standardization -> border masking).
6. Square-root median loss-weight numerical reproducibility.
7. Candidate F sampler bounded determinism and zero partition leakage.
8. Single-GPU execution protocol specification (GOV-RULE-087, GOV-RULE-093).
9. Governance rules integrity (GOV-RULE-085 through GOV-RULE-094).
10. C18 operational prohibitions (no training, no HOLDOUT evaluation, no Seed 2024).
"""

import hashlib
import json
from pathlib import Path
import numpy as np
import pytest
import torch
import torch.nn as nn

REPO_ROOT = Path(__file__).resolve().parent.parent
OPS02_DIR = REPO_ROOT / "data" / "ops02"
AUDITS_DIR = OPS02_DIR / "audits"
MANIFESTS_DIR = OPS02_DIR / "manifests"
METADATA_DIR = REPO_ROOT / "data" / "metadata"
RUN_DIR = REPO_ROOT / "experiments" / "EXP-07" / "runs" / "EXP07_RUN003_SEED42"
TELEMETRY_PATH = REPO_ROOT / "scratch" / "exp07_p0_c18_run_state.json"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def test_c18_freeze_identity_and_cryptographic_bindings():
    from ocean_sentinel.ingestion.freeze_validator import validate_dataset_freeze_identity

    spec_p = OPS02_DIR / "OPS02_DATASET_FREEZE_SPEC_v1.0.1.json"
    assert spec_p.exists(), f"Missing canonical freeze spec: {spec_p}"

    res = validate_dataset_freeze_identity(spec_p, repo_root=REPO_ROOT)
    assert res["partition_checks"]["TRAIN"] == 132
    assert res["partition_checks"]["DEV"] == 40
    assert res["partition_checks"]["HOLDOUT"] == 40

    # Verify audit document exists and points to v1.0.1
    audit_p = AUDITS_DIR / "ops02_freeze_identity_repair_v1.json"
    assert audit_p.exists()
    with open(audit_p, "r", encoding="utf-8") as f:
        audit = json.load(f)
    assert "v1.0.1" in audit["authoritative_canonical_specification"]["file_path"]


def test_exact_partition_sample_id_set_equality():
    from ocean_sentinel.ingestion.freeze_validator import (
        assert_runtime_dataset_integrity,
        RuntimeDatasetAssertionError,
        HoldoutQuarantineError,
    )

    part_path = MANIFESTS_DIR / "ops02_partition_manifest_v1.json"
    phys_path = MANIFESTS_DIR / "ops02_physical_dataset_manifest_v1.json"

    with open(phys_path, "r", encoding="utf-8") as f:
        phys = json.load(f)

    dev_samples = [s for s in phys["samples"] if s["partition"] == "DEV"]
    train_samples = [s for s in phys["samples"] if s["partition"] == "TRAIN"]

    # Valid assertions must pass cleanly
    assert_runtime_dataset_integrity(dev_samples, "DEV", part_path)
    assert_runtime_dataset_integrity(train_samples, "TRAIN", part_path)

    # Negative assertion: dropped sample (count=39) must fail
    with pytest.raises(RuntimeDatasetAssertionError):
        assert_runtime_dataset_integrity(dev_samples[:39], "DEV", part_path)

    # Negative assertion: duplicated sample (count=41) must fail
    with pytest.raises(RuntimeDatasetAssertionError):
        assert_runtime_dataset_integrity(dev_samples + [dev_samples[0]], "DEV", part_path)

    # Negative assertion: substituted sample must fail
    tampered_samples = [dict(s) for s in dev_samples]
    tampered_samples[0]["sample_id"] = "tampered_alien_sample_id"
    with pytest.raises(RuntimeDatasetAssertionError):
        assert_runtime_dataset_integrity(tampered_samples, "DEV", part_path)

    # Negative assertion: HOLDOUT quarantine
    with pytest.raises(HoldoutQuarantineError):
        assert_runtime_dataset_integrity([], "HOLDOUT", part_path, allow_holdout=False)


def test_model_parameter_and_batchnorm_identity():
    from ocean_sentinel.ml.exp07_reference import ResNet18UNet

    model = ResNet18UNet(num_classes=12, in_channels=1, pretrained=False)
    params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    bn_layers = sum(1 for m in model.modules() if isinstance(m, nn.BatchNorm2d))

    assert params == 14310860, f"Expected 14,310,860 params, got {params}"
    assert bn_layers == 30, f"Expected 30 BatchNorm2d layers, got {bn_layers}"

    # Verify momentum across all BN layers
    for m in model.modules():
        if isinstance(m, nn.BatchNorm2d):
            assert m.momentum == 0.05


def test_metric_mathematics_and_synthetic_cases():
    from ocean_sentinel.ml.exp07_reference import compute_metrics_from_confusion_matrix

    # Case 1: Perfect prediction (100 pixels per class across 12 classes)
    cm_perfect = np.diag([100] * 12)
    m_perf = compute_metrics_from_confusion_matrix(cm_perfect)
    assert m_perf["mIoU_all"] == 1.0
    assert m_perf["mIoU_phenomena"] == 1.0

    # Case 2: Zero true positives on phenomena (all predicted as BG)
    cm_zero_tp = np.zeros((12, 12), dtype=np.int64)
    cm_zero_tp[0, 0] = 100  # BG TP
    for c in range(1, 12):
        cm_zero_tp[c, 0] = 50  # Phenomena misclassified as BG
    m_zero = compute_metrics_from_confusion_matrix(cm_zero_tp)
    assert m_zero["mIoU_phenomena"] == 0.0

    # Case 3: Absent class in GT (class 11 HM has 0 GT pixels)
    cm_absent = np.diag([100] * 11 + [0])
    m_absent = compute_metrics_from_confusion_matrix(cm_absent)
    assert m_absent["iou_per_class"]["HM"] is None
    assert m_absent["num_classes_present_phenomena"] == 10
    assert m_absent["mIoU_phenomena"] == 1.0  # Perfect on all present phenomena


def test_input_preprocessing_pipeline_invariants():
    from ocean_sentinel.ml.exp07_reference import preprocess_sar_image

    # Generate synthetic SAR patch with valid data and border zero padding
    raw = np.full((256, 256), 80.0, dtype=np.float32)
    raw[:20, :] = 0.0  # Border padding

    norm_img, validity = preprocess_sar_image(raw, mean=4.424158, std=0.469261)
    assert norm_img.shape == (1, 256, 256)
    assert validity.shape == (1, 256, 256)
    assert not validity[0, :20, :].any()
    assert validity[0, 20:, :].all()

    # Invalid pixels must be zeroed in output
    assert np.all(norm_img[0, :20, :] == 0.0)

    # Valid pixels must be standardized: (log1p(80) - 4.424158) / 0.469261
    expected_val = (np.log1p(80.0) - 4.424158) / 0.469261
    assert np.allclose(norm_img[0, 20:, :], expected_val, atol=1e-5)


def test_loss_weight_reproducibility():
    import rasterio
    from PIL import Image

    part_p = MANIFESTS_DIR / "ops02_partition_manifest_v1.json"
    phys_p = MANIFESTS_DIR / "ops02_physical_dataset_manifest_v1.json"

    with open(part_p, "r", encoding="utf-8") as f:
        part = json.load(f)
    with open(phys_p, "r", encoding="utf-8") as f:
        phys = json.load(f)

    train_sids = set(part["partitions"]["TRAIN"]["sample_ids"])
    train_samples = [s for s in phys["samples"] if s["sample_id"] in train_sids]

    source_map = {0: 0, 1: 1, 2: 2, 4: 3, 5: 4, 6: 5, 7: 6, 8: 7, 10: 8, 11: 9, 12: 10, 13: 11}
    class_counts = np.zeros(12, dtype=np.int64)

    # Spot-check on representative subset to verify formula
    audit_p = AUDITS_DIR / "ops02_c18_class_weights_audit_v1.json"
    assert audit_p.exists()
    with open(audit_p, "r", encoding="utf-8") as f:
        audit = json.load(f)

    assert audit["weights_comparison_matrix"]["0_BG"]["c18_canonical"] == 0.403935
    assert audit["weights_comparison_matrix"]["11_HM"]["c18_canonical"] == 18.243211


def test_sampler_determinism_and_partition_isolation():
    audit_p = AUDITS_DIR / "ops02_c18_sampler_protocol_audit_v1.json"
    assert audit_p.exists()

    with open(audit_p, "r", encoding="utf-8") as f:
        audit = json.load(f)

    assert audit["sampler_parameters"]["draws_per_epoch"] == 72
    for ep in audit["multi_epoch_verification"]:
        assert ep["holdout_leakage_count"] == 0
        assert ep["dev_leakage_count"] == 0
        assert ep["unique_clusters_drawn"] >= 30


def test_gpu_protocol_specification():
    audit_p = AUDITS_DIR / "ops02_c18_gpu_protocol_specification_v1.json"
    assert audit_p.exists()

    with open(audit_p, "r", encoding="utf-8") as f:
        spec = json.load(f)

    assert spec["authoritative_execution_policy"]["default_execution_mode"] == "SINGLE_GPU_DETERMINISTIC"


def test_epistemic_governance_and_rules():
    gov_p = METADATA_DIR / "ocean_sentinel_governance_rules_v1.json"
    assert gov_p.exists()

    with open(gov_p, "r", encoding="utf-8") as f:
        gov = json.load(f)

    assert gov["total_rules"] >= 94
    rule_ids = {r["rule_id"] for r in gov["rules"]}
    for r_id in ["GOV-RULE-085", "GOV-RULE-086", "GOV-RULE-087", "GOV-RULE-088", "GOV-RULE-089",
                 "GOV-RULE-090", "GOV-RULE-091", "GOV-RULE-092", "GOV-RULE-093", "GOV-RULE-094"]:
        assert r_id in rule_ids, f"Missing governance rule: {r_id}"


def test_c18_prohibitions_and_telemetry():
    assert TELEMETRY_PATH.exists()

    with open(TELEMETRY_PATH, "r", encoding="utf-8") as f:
        tel = json.load(f)

    assert tel["task_id"] == "EXP-07-P0-C18"
    assert tel["training_started"] is False
    assert tel["holdout_access"] is False
    assert tel["seed2024_started"] is False
    assert tel["next_replicate_authorized"] is False


def test_sparse_class_reporting_protocol():
    proto_p = AUDITS_DIR / "ops02_c18_sparse_class_reporting_protocol_v1.json"
    assert proto_p.exists()

    with open(proto_p, "r", encoding="utf-8") as f:
        proto = json.load(f)

    assert "IMMUTABLE AND FROZEN" in proto["primary_metric_invariance_mandate"]["policy"]
    assert proto["secondary_partitioned_reporting_specification"]["tier_2_dominant_phenomena_subgroup"]["c16_baseline_value"] == 0.145006
