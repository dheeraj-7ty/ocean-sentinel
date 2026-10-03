import json
import inspect
from pathlib import Path
import pytest
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent

def test_lesson_c22g_001_rarity_vs_absence():
    """LL-C22G-001: All 11 phenomenon classes must have positive GT support on OPS-02 DEV."""
    audit_path = REPO_ROOT / "data/ops02/audits/ops02_c22g_class_support_metric_sensitivity_v1.json"
    assert audit_path.exists(), f"Audit file missing: {audit_path}"
    with open(audit_path, "r", encoding="utf-8") as f:
        audit = json.load(f)

    dev_classes = audit["physical_support_census"]["DEV"]["classes"]
    phenom_classes = ['AF', 'BS', 'LWA', 'MCC', 'OF', 'POW', 'RF', 'WS', 'Eddy', 'IWs', 'HM']

    zero_support_classes = []
    for c in phenom_classes:
        assert c in dev_classes, f"Class {c} missing from DEV support census"
        px = dev_classes[c]["pixel_count"]
        if px == 0:
            zero_support_classes.append(c)
        assert px > 0, f"Class {c} has zero pixels on DEV!"
        assert not dev_classes[c]["is_support_zero"], f"Class {c} marked as zero support!"

    assert len(zero_support_classes) == 0, f"Unexpected zero-support classes found: {zero_support_classes}"

    # Verify ultra-sparse classes are present but rare (< 10,000 px)
    assert 0 < dev_classes["RF"]["pixel_count"] < 10000
    assert 0 < dev_classes["OF"]["pixel_count"] < 10000
    assert 0 < dev_classes["HM"]["pixel_count"] < 10000


def test_lesson_c22g_002_single_scene_vulnerability():
    """LL-C22G-002: Verify single-parent classes and leave-one-parent-out denominator vulnerability."""
    audit_path = REPO_ROOT / "data/ops02/audits/ops02_c22g_class_support_metric_sensitivity_v1.json"
    with open(audit_path, "r", encoding="utf-8") as f:
        audit = json.load(f)

    dev_classes = audit["physical_support_census"]["DEV"]["classes"]

    # OF and RF must have exactly 1 parent in DEV
    assert dev_classes["OF"]["parent_count"] == 1
    assert dev_classes["RF"]["parent_count"] == 1
    of_parent = dev_classes["OF"]["parent_ids"][0]
    rf_parent = dev_classes["RF"]["parent_ids"][0]
    assert of_parent == "00E063"
    assert rf_parent == "00BDE6"

    # Verify parent sensitivity analysis results
    parent_loo = audit["parent_level_sensitivity_analysis"]
    assert "Seed 42 Ctrl" in parent_loo
    s42_c = parent_loo["Seed 42 Ctrl"]
    assert s42_c["influence_range"] > 0.02, "Influence range must exceed 0.02 on Seed 42 Ctrl"

    # Verify that removing 00E063 drops OF and increases mIoU
    loo_e063 = s42_c["parent_loo_details"]["00E063"]
    assert "OF" in loo_e063["dropped_classes"]
    assert loo_e063["delta_influence"] > 0.005, "Removing OF parent must cause positive delta"


def test_lesson_c22g_003_support_stratification():
    """LL-C22G-003: Verify support stratification and score decomposition."""
    audit_path = REPO_ROOT / "data/ops02/audits/ops02_c22g_class_support_metric_sensitivity_v1.json"
    with open(audit_path, "r", encoding="utf-8") as f:
        audit = json.load(f)

    decomp = audit["score_decomposition"]
    assert 0.045 < decomp["observed_frozen_primary_mean"] < 0.055
    assert decomp["dominant_phenomena_mean_mIoU"] > 0.10, "Dominant phenomena mIoU must exceed 0.10"
    assert decomp["support_weighted_mean_IoU"] > 0.14, "Support-weighted IoU must exceed 0.14"
    assert decomp["percentage_of_score_from_dominant_stratum"] > 80.0, "Dominant stratum must contribute >80% to score"

    # Verify mathematical decomposition identity
    num_dom = decomp["numerator_contribution_by_stratum"]["dominant_stratum_contribution"]
    num_int = decomp["numerator_contribution_by_stratum"]["intermediate_stratum_contribution"]
    num_sparse = decomp["numerator_contribution_by_stratum"]["ultra_sparse_stratum_contribution"]
    total_reconstructed = num_dom + num_int + num_sparse
    assert abs(total_reconstructed - decomp["observed_frozen_primary_mean"]) < 1e-4


def test_lesson_c22g_004_benchmark_preservation():
    """LL-C22G-004: Verify that the frozen primary benchmark implementation remains untouched."""
    from ocean_sentinel.ml.exp07_reference import compute_metrics_from_confusion_matrix, DENSE_CLASSES
    import inspect

    src = inspect.getsource(compute_metrics_from_confusion_matrix)
    assert "mIoU_phenomena" in src
    assert "if gt[c] > 0:" in src
    assert "if c > 0:" in src

    # Verify mathematical behavior on synthetic test matrix:
    # 12x12 confusion matrix where class 1 has TP=10, GT=10 (IoU=1.0)
    # class 2 has GT=0 (absent) -> IoU=None
    # classes 3..11 have TP=0, GT=10 (IoU=0.0)
    cm_test = np.zeros((12, 12), dtype=np.int64)
    cm_test[1, 1] = 10  # Class 1: TP=10, Union=10 -> 1.0
    for c in range(3, 12):
        cm_test[c, 0] = 10  # Classes 3..11: FN=10, TP=0 -> 0.0

    res = compute_metrics_from_confusion_matrix(cm_test)
    assert res["iou_per_class"]["AF"] == 1.0
    assert res["iou_per_class"]["BS"] is None
    # 10 present phenomenon classes (1, 3..11), sum = 1.0, denom = 10 -> mIoU = 0.10
    assert abs(res["mIoU_phenomena"] - 0.10) < 1e-6
    assert res["num_classes_present_phenomena"] == 10


def test_c22g_zero_training_governance():
    """Enforce zero-training and quarantine governance constraints for diagnostic task."""
    audit_path = REPO_ROOT / "data/ops02/audits/ops02_c22g_class_support_metric_sensitivity_v1.json"
    with open(audit_path, "r", encoding="utf-8") as f:
        audit = json.load(f)

    gov = audit["governance_guarantees"]
    assert gov["training_steps"] == 0
    assert gov["backward_passes"] == 0
    assert gov["optimizer_steps"] == 0
    assert gov["scheduler_steps"] == 0
    assert gov["gpu_training_compute_seconds"] == 0.0
    assert gov["holdout_payload_access_count"] == 0
    assert gov["part_iii_benchmark_access_count"] == 0
    assert gov["analytical_compute_mode"] == "CPU_ONLY"


def test_c22g_audit_artifacts_exist():
    """Verify that all required C22-G deliverables exist and have non-zero size."""
    files = [
        REPO_ROOT / "data/ops02/audits/ops02_c22g_metric_semantics_v1.json",
        REPO_ROOT / "data/ops02/audits/ops02_c22g_class_support_metric_sensitivity_v1.json",
        REPO_ROOT / "experiments/EXP-07/EXP07_P0_C22G_CLASS_SUPPORT_METRIC_SENSITIVITY_20260914.md",
    ]
    for p in files:
        assert p.exists(), f"File missing: {p}"
        assert p.stat().st_size > 500, f"File too small: {p}"
