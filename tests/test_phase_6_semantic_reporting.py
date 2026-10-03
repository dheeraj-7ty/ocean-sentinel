"""Unit and regression tests guarding semantic precision, metric scopes, and arithmetic firewalls for Phase 6 reporting."""

import json
import re
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
METRICS_DIR = REPO_ROOT / "experiments/performance/phase_6_part_iii_external_evaluation/attempt_001/metrics"
REPORT_PATH = REPO_ROOT / "experiments/PHASE_6_PART_III_EXTERNAL_EVALUATION_REPORT_20260912.md"
LESSONS_PATH = REPO_ROOT / "experiments/EXPERIMENTAL_LESSONS_LEARNED_20260911.md"


def test_metric_json_stratum_scoping():
    """Verify that official metrics files scope IoU strictly to oil_stratum and FAR to scene_far."""
    summary_path = METRICS_DIR / "comparison_summary.json"
    mapping_a_path = METRICS_DIR / "metrics_mapping_a.json"
    mapping_b_path = METRICS_DIR / "metrics_mapping_b.json"

    assert summary_path.is_file(), f"Missing {summary_path}"
    assert mapping_a_path.is_file(), f"Missing {mapping_a_path}"
    assert mapping_b_path.is_file(), f"Missing {mapping_b_path}"

    with open(summary_path, "r") as f:
        summary = json.load(f)

    # IoU must be scoped under oil_stratum_comparison, not top-level
    assert "oil_stratum_comparison" in summary
    assert "macro_mean_iou" in summary["oil_stratum_comparison"]
    assert "overall_iou" not in summary
    assert "benchmark_iou" not in summary

    # FAR must be explicitly labeled scene_far_primary, not specificity
    assert "no_oil_stratum_comparison" in summary
    assert "scene_far_primary" in summary["no_oil_stratum_comparison"]
    assert "specificity" not in summary["no_oil_stratum_comparison"]

    with open(mapping_a_path, "r") as f:
        meta_a = json.load(f)
    assert "oil_stratum" in meta_a
    assert "no_oil_stratum" in meta_a
    assert "lookalike_stratum" in meta_a
    assert meta_a["no_oil_stratum"]["scene_far_primary"]["rule"] == "I(FP > 0)"
    assert "specificity" not in meta_a["no_oil_stratum"]


def test_mathematical_firewall_scene_far_vs_specificity():
    """Verify that Scene FAR, Clean Scene Rejection Rate, and Pixel Specificity are mathematically distinct."""
    total_clean_pixels = 150 * 2048 * 2048  # 629,145,600
    clean_water_fp_a = 95157
    clean_water_tn_a = total_clean_pixels - clean_water_fp_a

    pixel_specificity_clean_a = clean_water_tn_a / total_clean_pixels
    scene_far_a = 7 / 150  # 4.67%
    clean_scene_rejection_a = 143 / 150  # 95.33%

    # Specificity is > 99.98%, whereas clean scene rejection rate is ~95.33%
    assert abs(pixel_specificity_clean_a - 0.9998487375895182) < 1e-6
    assert abs(scene_far_a - 0.04666666666666667) < 1e-6
    assert abs(clean_scene_rejection_a - 0.9533333333333334) < 1e-6

    # Mathematical firewall: Scene-level rates must NEVER be numerically equal to pixel specificity
    assert abs(scene_far_a - pixel_specificity_clean_a) > 0.90
    assert abs(clean_scene_rejection_a - pixel_specificity_clean_a) > 0.04

    # Whole-benchmark pixel specificity
    whole_tn_a = 1687207376
    whole_fp_a = 137727437
    whole_specificity_a = whole_tn_a / (whole_tn_a + whole_fp_a)
    assert abs(whole_specificity_a - 0.9245302294158498) < 1e-5


def test_confusion_matrix_conservation_and_global_iou():
    """Verify arithmetic conservation identities and contrast Oil-stratum IoU with Whole-Benchmark Pixel IoU."""
    total_pixels = 1887436800
    n_fg = 62501987
    n_bg = 1824934813

    # Mapping A
    tp_a, fp_a, fn_a, tn_a = 50477786, 137727437, 12024201, 1687207376
    assert tp_a + fn_a == n_fg
    assert fp_a + tn_a == n_bg
    assert tp_a + fp_a + fn_a + tn_a == total_pixels

    # Mapping B
    tp_b, fp_b, fn_b, tn_b = 56333470, 1399686042, 6168517, 425248771
    assert tp_b + fn_b == n_fg
    assert fp_b + tn_b == n_bg
    assert tp_b + fp_b + fn_b + tn_b == total_pixels

    # Global pixel IoU for Mapping A
    global_pixel_iou_a = tp_a / (tp_a + fp_a + fn_a)
    assert abs(global_pixel_iou_a - 0.25209974261771175) < 1e-6

    # Oil-stratum macro mean IoU is ~74.49%, while global pixel IoU is ~25.21%
    oil_stratum_macro_iou_a = 0.7448561327020893
    assert abs(oil_stratum_macro_iou_a - global_pixel_iou_a) > 0.45


def test_surface_percentage_denominators():
    """Verify that stratum surface area percentages use exact stratum denominator 629,145,600."""
    stratum_pixels = 150 * 2048 * 2048  # 629,145,600
    total_benchmark_pixels = 450 * 2048 * 2048  # 1,887,436,800

    clean_fp_a = 95157
    clean_prop_stratum = clean_fp_a / stratum_pixels
    clean_prop_global = clean_fp_a / total_benchmark_pixels
    assert abs(clean_prop_stratum - 0.000151248) < 1e-6  # ~0.015%
    assert abs(clean_prop_global - 0.000050416) < 1e-6   # ~0.005%

    lookalike_fp_a = 130502095
    lookalike_prop_stratum = lookalike_fp_a / stratum_pixels
    lookalike_prop_global = lookalike_fp_a / total_benchmark_pixels
    assert abs(lookalike_prop_stratum - 0.2074275) < 1e-6  # ~20.74%
    assert abs(lookalike_prop_global - 0.0691425) < 1e-6   # ~6.91%


def test_report_semantic_guards():
    """Verify that Phase 6 technical report complies with evidence-bounded terminology rules."""
    assert REPORT_PATH.is_file(), f"Missing {REPORT_PATH}"
    content = REPORT_PATH.read_text(encoding="utf-8")

    # Prohibited uncalibrated phrases
    prohibited_phrases = [
        "false-alarm collapse",
        "overall external benchmark IoU",
        "global Part III IoU",
        "The model requires Channel 0 to correspond to the lower backscatter mean",
        "cannot reliably discriminate",
        "Authoritative Whole-Benchmark Headline",
        "Polarization Sensitivity Gap",
    ]
    for phrase in prohibited_phrases:
        assert phrase not in content, f"Prohibited phrase '{phrase}' found in report."

    # Required calibrated phrases and headings
    assert "Key External-Benchmark Findings" in content
    assert "Signed Delta (A − B)" in content
    assert "Oil-stratum" in content
    assert "catastrophic performance degradation under inverted channel ordering" in content
    assert "vulnerability of the" in content and "to the benchmark Lookalike class" in content
    assert "Primary Scene FAR" in content
    assert "Metric Scope Is Part of Scientific Correctness" in content
    assert "136 of 150 Lookalike scenes contained at least one false-positive pixel, corresponding to a Primary Scene FAR of 90.67%" in content

    # Verify that 'Gap' does not appear as a column header in markdown tables
    for line in content.splitlines():
        if line.startswith("|") and ("---" not in line):
            assert " Gap " not in line and "| Gap" not in line and "Gap |" not in line, f"Ambiguous 'Gap' found in table header: {line}"


def test_conclusion_evidence_boundaries():
    """Verify that the conclusion explicitly states limitations on generalization and readiness."""
    assert REPORT_PATH.is_file()
    content = REPORT_PATH.read_text(encoding="utf-8")

    conclusion_idx = content.find("## 8. Final Scientific Conclusion")
    assert conclusion_idx != -1, "Missing Section 8 in report"
    conclusion_text = content[conclusion_idx:]

    assert "universal generalization" in conclusion_text
    assert "operational readiness" in conclusion_text
    assert "deployment readiness" in conclusion_text
    assert "causal superiority of the channel ordering" in conclusion_text
    assert "untested future interventions" in conclusion_text


def test_lessons_learned_doctrine_entry():
    """Verify that the permanent governance doctrine documents Section 4.10 on metric scope and signed delta."""
    assert LESSONS_PATH.is_file(), f"Missing {LESSONS_PATH}"
    content = LESSONS_PATH.read_text(encoding="utf-8")
    assert "4.10 Scientific & Governance Lesson: Metric Scope Is Part of Scientific Correctness" in content
    assert "A valid numerical metric can still be scientifically misleading if its evaluation population and scope are not explicitly declared." in content
    assert "Signed Delta vs. Absolute Gap" in content


def test_signed_deltas_final_table():
    """Verify that all directional comparisons use 'Signed Delta (A − B)' with explicit signs."""
    assert REPORT_PATH.is_file()
    content = REPORT_PATH.read_text(encoding="utf-8")

    expected_signed_deltas = [
        ("Oil Macro IoU", "+0.65315"),
        ("Oil Micro IoU", "+0.63269"),
        ("Oil Dice", "+0.69095"),
        ("Oil Precision", "+0.74501"),
        ("Oil Recall", "-0.07088"),
        ("No-Oil Primary Scene FAR", "-0.87333"),
        ("No-Oil Clean Scene Rejection Rate", "+0.87333"),
        ("No-Oil Significant Scene FAR", "-0.85333"),
        ("No-Oil Total FP Pixel Burden", "-373,036,477"),
        ("No-Oil Pixel Specificity", "+0.59293"),
        ("Lookalike Primary Scene FAR", "-0.07333"),
        ("Lookalike Significant Scene FAR", "-0.08000"),
        ("Lookalike Total FP Pixel Burden", "-347,783,505"),
        ("Lookalike Pixel Specificity", "+0.55278"),
        ("Whole-Benchmark Pixel Specificity", "+0.69151"),
        ("Whole-Benchmark Global Pixel IoU", "+0.21356"),
    ]

    for metric_name, signed_val in expected_signed_deltas:
        assert signed_val in content, f"Expected signed delta '{signed_val}' for '{metric_name}' not found in report"
        assert signed_val.startswith("+") or signed_val.startswith("-")


