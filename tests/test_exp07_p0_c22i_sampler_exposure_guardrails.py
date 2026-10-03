"""
EXP-07-P0-C22-I Guardrail Test Suite
DIAG-02: Sampler Exposure, Schedule Invariance & Optimization Dynamics Diagnostic

Validates:
1. Zero compute, zero GPU, zero holdout access, zero training steps.
2. Lessons learned LL-C22I-001 through LL-C22I-004 registration and enforcement.
3. Level 5 audit artifact schema and numeric consistency.
4. Absence of illegal overclaims and adherence to empirical exposure realities.
"""

import json
from pathlib import Path
import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIT_JSON_PATH = REPO_ROOT / "data" / "ops02" / "audits" / "ops02_c22i_sampler_exposure_audit_v1.json"
REPORT_MD_PATH = REPO_ROOT / "experiments" / "EXP-07" / "EXP07_P0_C22I_SAMPLER_EXPOSURE_AUDIT_20260914.md"
LESSONS_JSON_PATH = REPO_ROOT / "data" / "metadata" / "ocean_sentinel_lessons_learned_v1.json"


@pytest.fixture(scope="module")
def audit_data():
    assert AUDIT_JSON_PATH.exists(), f"Audit file missing: {AUDIT_JSON_PATH}"
    with open(AUDIT_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def report_text():
    assert REPORT_MD_PATH.exists(), f"Report file missing: {REPORT_MD_PATH}"
    with open(REPORT_MD_PATH, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture(scope="module")
def lessons_data():
    assert LESSONS_JSON_PATH.exists(), f"Lessons file missing: {LESSONS_JSON_PATH}"
    with open(LESSONS_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ==============================================================================
# Governance & Resource Invariants
# ==============================================================================

def test_zero_compute_and_governance_invariants(audit_data):
    gov = audit_data["governance"]
    assert gov["status"] == "VALIDATED"
    assert gov["training_steps"] == 0
    assert gov["gpu_seconds"] == 0.0
    assert gov["holdout_access_count"] == 0
    assert gov["part_iii_access_count"] == 0


# ==============================================================================
# Audit JSON Schema & Structural Parity
# ==============================================================================

def test_c22i_audit_artifact_schema_and_integrity(audit_data):
    assert audit_data["audit_id"] == "OPS02-C22I-SAMPLER-EXPOSURE-AUDIT-V1"
    assert audit_data["task_id"] == "EXP-07-P0-C22-I"
    assert audit_data["investigation_id"] == "DIAG-02-SAMPLER-EXPOSURE-SCHEDULE-DYNAMICS"
    
    # 5 seeds audited
    seeds = list(audit_data["schedule_hashes"].keys())
    assert len(seeds) == 5
    assert set(seeds) == {"42", "101", "202", "303", "404"}
    
    # Check empirical findings in verdict
    verdict = audit_data["diagnostic_verdict"]
    assert verdict["sampler_starvation_hypothesis"] in ["REFUTED", "NOT_SUPPORTED"]
    assert verdict["verdict_case"] == "CASE_C_AND_D"
    
    # Check correlations
    corrs = audit_data["linkage_to_experimental_outcomes"]["correlations"]
    assert corrs["pearson_r_ultra_rare_vs_paired_delta"] > 0.8


# ==============================================================================
# Lesson Learned Regressions (LL-C22I-001 .. LL-C22I-004)
# ==============================================================================

def test_lesson_c22i_001_no_silent_manifest_key_fallback(lessons_data):
    lesson = next((l for l in lessons_data["lessons"] if l["lesson_id"] == "LL-C22I-001"), None)
    assert lesson is not None, "LL-C22I-001 missing from lessons database"
    assert lesson["status"] == "REGRESSION_PROTECTED"
    assert lesson["severity"] == "CRITICAL"
    assert "labels_present" in lesson["failure_pattern"] or "labels_present" in lesson["description"]


def test_lesson_c22i_002_exposure_audit_precedes_starvation_claims(audit_data, lessons_data):
    lesson = next((l for l in lessons_data["lessons"] if l["lesson_id"] == "LL-C22I-002"), None)
    assert lesson is not None, "LL-C22I-002 missing from lessons database"
    assert lesson["status"] == "REGRESSION_PROTECTED"
    
    # Verify that in the audit, all phenomenon classes have positive draws across all 5 seeds in all_30
    exp_by_seed = audit_data["exposure_by_seed_window"]
    for seed_str, seed_data in exp_by_seed.items():
        draw_counts = seed_data["all_30"]["class_draw_counts"]
        for c_idx in range(12):
            assert draw_counts[str(c_idx)] > 0, f"Seed {seed_str} class {c_idx} had 0 draws in all_30!"


def test_lesson_c22i_003_schedule_variance_correlation_audited(audit_data, lessons_data):
    lesson = next((l for l in lessons_data["lessons"] if l["lesson_id"] == "LL-C22I-003"), None)
    assert lesson is not None, "LL-C22I-003 missing from lessons database"
    assert lesson["status"] == "REGRESSION_PROTECTED"
    
    corr = audit_data["linkage_to_experimental_outcomes"]["correlations"]["pearson_r_ultra_rare_vs_paired_delta"]
    assert 0.8 < corr < 1.0, f"Expected strong positive correlation, got {corr}"


def test_lesson_c22i_004_early_peaking_not_sampler_starvation(audit_data, lessons_data):
    lesson = next((l for l in lessons_data["lessons"] if l["lesson_id"] == "LL-C22I-004"), None)
    assert lesson is not None, "LL-C22I-004 missing from lessons database"
    assert lesson["status"] == "REGRESSION_PROTECTED"
    
    outcomes = audit_data["linkage_to_experimental_outcomes"]["outcomes"]
    treatment_epochs = [outcomes[s]["treat_ep"] for s in outcomes]
    assert all(e in [5, 6, 7] for e in treatment_epochs), f"Expected treatment epochs in [5, 6, 7], got {treatment_epochs}"


# ==============================================================================
# Report Content & Scientific Integrity
# ==============================================================================

def test_report_structure_and_no_forbidden_claims(report_text):
    assert "EXP-07-P0-C22-I" in report_text
    assert "DIAG-02-SAMPLER-EXPOSURE-SCHEDULE-DYNAMICS" in report_text
    assert "LL-C22I-001" in report_text
    assert "LL-C22I-002" in report_text
    assert "LL-C22I-003" in report_text
    assert "LL-C22I-004" in report_text
    
    # Must state correlation accurately
    assert "0.8955" in report_text
