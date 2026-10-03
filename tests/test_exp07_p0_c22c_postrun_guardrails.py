"""Tests for EXP-07-P0-C22-C Post-Run Forensic Audit, Scientific Repair, and Guardrails.

Validates:
1. Exact numerical reconciliation against raw C22-B artifacts.
2. Single-variable pair integrity (only loss vector differs).
3. Absence of unsupported mechanistic or background loss claims.
4. Canonical taxonomy terminology compliance (no illegal aliases for HM, OF, BS).
5. Quarantine of HOLDOUT and Part III payloads.
6. Integration of LL-C22B-001 through LL-C22B-006 in agent learning database.
"""

import json
import re
from pathlib import Path
import pytest
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
RUN_DIR = REPO_ROOT / "experiments" / "EXP-07" / "runs" / "EXP07_DIAG01"
REPORT_PATH = REPO_ROOT / "experiments" / "EXP-07" / "EXP07_P0_C22B_FINAL_PAIRED_TRAINING_REPORT_20260914.md"
VALIDATION_JSON_PATH = REPO_ROOT / "data" / "ops02" / "audits" / "ops02_c22c_postrun_validation_v1.json"
LESSONS_PATH = REPO_ROOT / "data" / "metadata" / "ocean_sentinel_lessons_learned_v1.json"


def test_numerical_reconciliation_exactness():
    """Verify raw C22-B artifacts support the exact numerical values."""
    ctrl_hist = json.loads((RUN_DIR / "control_history.json").read_text(encoding="utf-8"))
    treat_hist = json.loads((RUN_DIR / "treatment_history.json").read_text(encoding="utf-8"))

    assert len(ctrl_hist) == 20
    assert len(treat_hist) == 15

    ctrl_best = max(ctrl_hist, key=lambda x: x["dev_mIoU_phenomena"])
    treat_best = max(treat_hist, key=lambda x: x["dev_mIoU_phenomena"])

    assert ctrl_best["epoch"] == 10
    assert abs(ctrl_best["dev_mIoU_phenomena"] - 0.04147) < 1e-6

    assert treat_best["epoch"] == 5
    assert abs(treat_best["dev_mIoU_phenomena"] - 0.05318) < 1e-6

    abs_delta = treat_best["dev_mIoU_phenomena"] - ctrl_best["dev_mIoU_phenomena"]
    rel_pct = (abs_delta / ctrl_best["dev_mIoU_phenomena"]) * 100.0

    assert abs(abs_delta - 0.01171) < 1e-5
    assert abs(rel_pct - 28.24) < 0.05


def test_paired_experiment_single_variable_isolation():
    """Verify Control and Treatment differ solely in the loss weight vector."""
    paired = json.loads((RUN_DIR / "exp07_diag01_paired_comparison.json").read_text(encoding="utf-8"))

    # Initial state bitwise equality
    assert paired["initialization"]["initial_state_bitwise_equal"] is True
    assert paired["initialization"]["control_initial_state_fingerprint"] == paired["initialization"]["treatment_initial_state_fingerprint"]
    assert paired["initialization"]["canonical_initial_state_sha256"] == "67181C4ECD420DEABA4129AB67AA34D617C1C581ACB3A1A7A9DE8BEAF2F1544D"

    # Sampler schedule equality
    assert paired["sampling"]["schedule_sha256"] == "2B1562E33FF32F73A8BF373D24951AF220E423FF74F12F7B589CEDA426A6834B"

    # Loss vectors
    ctrl_weights = paired["results"]["control"]["loss_weights"]
    treat_weights = paired["results"]["treatment"]["loss_weights"]
    assert len(ctrl_weights) == 12
    assert len(treat_weights) == 12
    assert ctrl_weights != treat_weights
    assert treat_weights == [1.0] * 12


def test_c22b_report_absence_of_unsupported_claims():
    """Verify C22-B report does NOT contain unsupported causal/background claims."""
    assert REPORT_PATH.exists(), f"Report not found at {REPORT_PATH}"
    report_text = REPORT_PATH.read_text(encoding="utf-8")

    forbidden_patterns = [
        r"degrading boundary resolution",
        r"Treatment experienced higher penalty on background",
        r"vastly boosting boundary definition"
    ]
    for pattern in forbidden_patterns:
        matches = re.findall(pattern, report_text, flags=re.IGNORECASE)
        assert len(matches) == 0, f"Found unsupported claim in report: '{matches[0]}'"


def test_canonical_taxonomy_no_illegal_aliases():
    """Verify Class 11 (HM) is named Artificial/Anthropogenic Objects, NOT Heavy Metal or Vessel."""
    assert REPORT_PATH.exists()
    report_text = REPORT_PATH.read_text(encoding="utf-8")

    # HM must not be described as Heavy Metal, Ship, or Marine Vessel in canonical taxonomy tables
    forbidden_hm_aliases = [
        r"Heavy Metal",
        r"Marine Vessel",
        r"Ship class",
        r"Vessel class"
    ]
    for alias in forbidden_hm_aliases:
        matches = re.findall(alias, report_text, flags=re.IGNORECASE)
        assert len(matches) == 0, f"Found illegal taxonomy alias in C22-B report: '{matches[0]}'"

    # Check OF is not referred to as Oil Spill
    matches_of = re.findall(r"OF.*Oil Spill", report_text, flags=re.IGNORECASE)
    assert len(matches_of) == 0, f"Found illegal OF alias in C22-B report: '{matches_of[0]}'"


def test_quarantine_integrity_zero_access():
    """Verify HOLDOUT and Part III access counts remain strictly zero."""
    paired = json.loads((RUN_DIR / "exp07_diag01_paired_comparison.json").read_text(encoding="utf-8"))
    assert paired["dataset"]["holdout_access_count"] == 0

    if VALIDATION_JSON_PATH.exists():
        val = json.loads(VALIDATION_JSON_PATH.read_text(encoding="utf-8"))
        assert val["governance_and_quarantine"]["holdout_access_count"] == 0
        assert val["governance_and_quarantine"]["part_iii_access_count"] == 0


def test_agent_learning_c22b_lessons():
    """Verify LL-C22B-001 through LL-C22B-006 exist and are regression protected."""
    db = json.loads(LESSONS_PATH.read_text(encoding="utf-8"))
    lesson_map = {l["lesson_id"]: l for l in db["lessons"]}

    expected_lessons = [
        "LL-C22B-001", "LL-C22B-002", "LL-C22B-003",
        "LL-C22B-004", "LL-C22B-005", "LL-C22B-006"
    ]
    for lid in expected_lessons:
        assert lid in lesson_map, f"Missing required lesson: {lid}"
        lsn = lesson_map[lid]
        assert lsn["status"] == "REGRESSION_PROTECTED"
        assert "tests/test_exp07_p0_c22c_postrun_guardrails.py" in lsn["regression_test"]
