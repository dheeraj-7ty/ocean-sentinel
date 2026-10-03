"""EXP-07-P0-C22-J Guardrail Test Suite
DIAG-02 Forensic Correction, Association Bounding & Roadmap Realignment

Validates:
1. Zero training, zero backward passes, zero optimizer steps, zero GPU compute, zero holdout access, zero DIAG-05 execution.
2. Level 5 audit artifact schema, numeric consistency, and 5-seed correlation statistics.
3. Audit artifact provenance and explicit forensic history embedding.
4. Canonical rare-class nomenclature and physical vs sampled cluster accounting.
5. Complete elimination of unsupported gradient and mechanistic claims.
6. Calibrated starvation conclusion and tripartite concept separation.
7. Preservation of authoritative roadmap (DIAG-03, DIAG-04 unchanged; DIAG-05 DESIGN ONLY).
8. Durable lessons learned registration (LL-C22I-001..004, LL-C22J-001..005).
"""

import json
from pathlib import Path
import pytest
import numpy as np
import scipy.stats as stats


REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIT_C22J_JSON = REPO_ROOT / "data" / "ops02" / "audits" / "ops02_c22j_diag02_forensic_correction_v1.json"
AUDIT_C22I_JSON = REPO_ROOT / "data" / "ops02" / "audits" / "ops02_c22i_sampler_exposure_audit_v1.json"
REPORT_C22J_MD = REPO_ROOT / "experiments" / "EXP-07" / "EXP07_P0_C22J_DIAG02_FORENSIC_CORRECTION_20260914.md"
REPORT_C22I_MD = REPO_ROOT / "experiments" / "EXP-07" / "EXP07_P0_C22I_SAMPLER_EXPOSURE_AUDIT_20260914.md"
LESSONS_JSON = REPO_ROOT / "data" / "metadata" / "ocean_sentinel_lessons_learned_v1.json"


@pytest.fixture(scope="module")
def audit_c22j_data():
    assert AUDIT_C22J_JSON.exists(), f"Audit file missing: {AUDIT_C22J_JSON}"
    with open(AUDIT_C22J_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def audit_c22i_data():
    assert AUDIT_C22I_JSON.exists(), f"Audit file missing: {AUDIT_C22I_JSON}"
    with open(AUDIT_C22I_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def report_c22j_text():
    assert REPORT_C22J_MD.exists(), f"Report file missing: {REPORT_C22J_MD}"
    with open(REPORT_C22J_MD, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture(scope="module")
def report_c22i_text():
    assert REPORT_C22I_MD.exists(), f"Report file missing: {REPORT_C22I_MD}"
    with open(REPORT_C22I_MD, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture(scope="module")
def lessons_data():
    assert LESSONS_JSON.exists(), f"Lessons file missing: {LESSONS_JSON}"
    with open(LESSONS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


# ==============================================================================
# 1. Absolute Governance & Non-Negotiable Invariants
# ==============================================================================

def test_governance_invariants(audit_c22j_data):
    gov = audit_c22j_data["governance_guarantees"]
    assert gov["training_steps"] == 0
    assert gov["backward_passes"] == 0
    assert gov["optimizer_steps"] == 0
    assert gov["scheduler_steps"] == 0
    assert gov["parameter_updates"] == 0
    assert gov["gpu_training_compute_seconds"] == 0.0
    assert gov["holdout_payload_access_count"] == 0
    assert gov["part_iii_benchmark_access_count"] == 0
    assert gov["diag05_executed"] is False
    assert gov["analytical_compute_mode"] == "CPU_ONLY"


# ==============================================================================
# 2. Level 5 Audit Artifact Schema, Provenance & Numerical Recomputation
# ==============================================================================

def test_c22j_audit_artifact_schema_and_integrity(audit_c22j_data):
    assert audit_c22j_data["task_id"] == "EXP-07-P0-C22-J"
    assert audit_c22j_data["investigation_id"] == "DIAG-02-FORENSIC-CORRECTION-AND-ROADMAP-GATE"
    assert audit_c22j_data["status"] == "COMPLETED_VALID"

    # Verify provenance decision block
    prov = audit_c22j_data["audit_provenance_decision"]
    assert prov["decision"] == "MUTABLE_WITH_EXPLICIT_FORENSIC_HISTORY"
    assert "EXP-07-P0-C22-H" in prov["precedent"]

    reconciliation = audit_c22j_data["forensic_reconciliation"]
    vectors = reconciliation["five_seed_vectors"]
    assert vectors["seeds"] == [42, 101, 202, 303, 404]

    x = np.array(vectors["X_early_rare_class_draws_ep1_7"])
    y1 = np.array(vectors["Y1_control_best_dev_mIoU"])
    y2 = np.array(vectors["Y2_treatment_best_dev_mIoU"])
    y3 = np.array(vectors["Y3_paired_delta_treatment_minus_control"])

    assert len(x) == 5
    assert len(y1) == 5
    assert len(y2) == 5
    assert len(y3) == 5

    # Verify mathematical exactness of correlations
    r1, _ = stats.pearsonr(x, y1)
    rho1, _ = stats.spearmanr(x, y1)
    assert round(r1, 4) == -0.9167
    assert round(rho1, 4) == -0.9000

    r2, _ = stats.pearsonr(x, y2)
    rho2, _ = stats.spearmanr(x, y2)
    assert round(r2, 4) == 0.6302
    assert round(rho2, 4) == 0.4000

    r3, _ = stats.pearsonr(x, y3)
    rho3, _ = stats.spearmanr(x, y3)
    assert round(r3, 4) == 0.8955
    assert round(rho3, 4) == 0.7000

    # Ensure correlations are bounded as descriptive associations only
    corrs = reconciliation["statistical_correlations"]
    assert corrs["sample_size"] == 5
    assert corrs["interpretation_constraint"] == "DESCRIPTIVE_ASSOCIATION_ONLY_NO_CAUSAL_OR_GRADIENT_CLAIMS"
    assert corrs["X_vs_Y1_control"]["classification"] == "DESCRIPTIVE_ASSOCIATION"
    assert corrs["X_vs_Y2_treatment"]["classification"] == "DESCRIPTIVE_ASSOCIATION"
    assert corrs["X_vs_Y3_paired_delta"]["classification"] == "DESCRIPTIVE_ASSOCIATION"


def test_c22i_embedded_provenance_history(audit_c22i_data):
    assert "forensic_correction_history" in audit_c22i_data
    hist = audit_c22i_data["forensic_correction_history"]
    assert hist["corrected_in_task"] == "EXP-07-P0-C22-J"
    assert hist["status"] == "FORENSICALLY_CORRECTED"
    assert "original_mechanistic_interpretation" in hist


# ==============================================================================
# 3. Canonical Rare-Class Nomenclature & Cluster Accounting
# ==============================================================================

def test_canonical_class_nomenclature_and_clusters(audit_c22j_data, report_c22j_text, report_c22i_text):
    classes = audit_c22j_data["forensic_reconciliation"]["target_rare_classes"]
    assert classes["OF"]["canonical_name"] == "Ocean Front"
    assert classes["OF"]["physical_train_samples"] == 9
    assert classes["OF"]["physical_parent_clusters"] == 4

    assert classes["RF"]["canonical_name"] == "Rain / precipitation-related phenomenon"
    assert classes["RF"]["physical_train_samples"] == 13
    assert classes["RF"]["physical_parent_clusters"] == 7

    assert classes["HM"]["canonical_name"] == "Artificial / Anthropogenic Objects"
    assert classes["HM"]["physical_train_samples"] == 12
    assert classes["HM"]["physical_parent_clusters"] == 8

    # Verify cluster accounting in audit
    cluster_acct = audit_c22j_data["forensic_reconciliation"]["physical_vs_sampled_cluster_accounting"]
    assert "4/4" in cluster_acct["OF"]["sampled_clusters_epochs_1_7"]
    assert "7/7" in cluster_acct["RF"]["sampled_clusters_epochs_1_7"]
    assert "7-8/8" in cluster_acct["HM"]["sampled_clusters_epochs_1_7"]

    # Verify forbidden aliases are absent from reports
    for report in [report_c22j_text, report_c22i_text]:
        assert "oil spill" not in report.lower(), "Found forbidden alias 'oil spill'"
        assert "vessel" not in report.lower(), "Found forbidden alias 'vessel'"
        assert "heavy metal" not in report.lower(), "Found forbidden alias 'heavy metal'"


# ==============================================================================
# 4. Absence of Unsupported Optimization & Gradient Claims
# ==============================================================================

def test_no_unsupported_gradient_claims(audit_c22j_data, report_c22j_text, report_c22i_text):
    mech_audit = audit_c22j_data["forensic_reconciliation"]["mechanism_claim_audit"]
    assert mech_audit["sampler_audit_measures_gradients"] is False
    assert mech_audit["unsupported_gradient_claims_removed"] is True

    forbidden_terms = [
        "gradient shock",
        "violent gradient",
        "stable gradient update",
        "unstable gradient",
        "gradient variance",
        "regularization",
        "convergence mechanism"
    ]

    for term in forbidden_terms:
        assert term not in report_c22i_text.lower(), f"Found forbidden term '{term}' in C22-I report"
        assert term not in report_c22j_text.lower(), f"Found forbidden term '{term}' in C22-J report"


# ==============================================================================
# 5. Calibrated Starvation Finding & Concept Separation
# ==============================================================================

def test_calibrated_starvation_and_concept_separation(audit_c22j_data, report_c22j_text, report_c22i_text):
    starvation = audit_c22j_data["forensic_reconciliation"]["starvation_finding"]
    expected_statement = (
        "Complete exposure absence was not observed under Candidate F; whether exposure was quantitatively "
        "sufficient, optimally distributed, or temporally appropriate for learning remains unresolved."
    )
    assert starvation["calibrated_statement"] == expected_statement
    assert starvation["unqualified_starvation_refutation_forbidden"] is True

    for report in [report_c22j_text, report_c22i_text]:
        assert expected_statement in report, "Required calibrated starvation statement missing from report"
        assert "sampler starvation refuted" not in report.lower(), "Found forbidden global 'sampler starvation refuted' claim"

    concept_sep = audit_c22j_data["forensic_reconciliation"]["concept_separation"]
    assert "Physical Class Availability != Sampler Allocation != Demonstrated Learning Effect" in concept_sep["rule"]


# ==============================================================================
# 6. Authoritative Diagnostic Roadmap Preservation & DIAG-05 Design Isolation
# ==============================================================================

def test_authoritative_roadmap_preservation(audit_c22j_data, report_c22j_text, report_c22i_text):
    roadmap = {item["rank"]: item for item in audit_c22j_data["authoritative_diagnostic_roadmap"]}

    assert roadmap[1]["investigation_id"] == "DIAG-01-CLASS-SUPPORT-METRIC-SENSITIVITY"
    assert roadmap[1]["classification"] == "CASE B"

    assert roadmap[2]["investigation_id"] == "DIAG-02-SAMPLER-EXPOSURE-SCHEDULE-AUDIT"
    assert roadmap[2]["status"] == "COMPLETED_FORENSICALLY_REPAIRED"

    assert roadmap[3]["investigation_id"] == "DIAG-03-RADIOMETRIC-FEATURE-DISCRIMINABILITY"
    assert roadmap[3]["title"] == "Radiometric Feature Discriminability Diagnostic"
    assert roadmap[3]["status"] == "UNCHANGED_PENDING_USER_AUTHORIZATION"

    assert roadmap[4]["investigation_id"] == "DIAG-04-RECEPTIVE-FIELD-SCALE-COMPATIBILITY"
    assert roadmap[4]["title"] == "Receptive Field & Spatial Scale Compatibility Diagnostic"
    assert roadmap[4]["status"] == "UNCHANGED_PENDING_USER_AUTHORIZATION"

    assert roadmap[5]["investigation_id"] == "DIAG-05-LOSS-LANDSCAPE-GRADIENT-DYNAMICS"
    assert roadmap[5]["status"] == "DESIGN_ONLY_NOT_EXECUTED"

    diag05_spec = audit_c22j_data["diag05_specification"]
    assert diag05_spec["status"] == "DESIGN_ONLY_NOT_EXECUTED"

    for report in [report_c22j_text, report_c22i_text]:
        assert "DIAG-03: RADIOMETRIC FEATURE DISCRIMINABILITY" in report
        assert "DIAG-04: RECEPTIVE FIELD & SPATIAL SCALE COMPATIBILITY" in report
        assert "DIAG-05" in report
        assert "DESIGN ONLY" in report or "DESIGN ONLY / NOT EXECUTED" in report


# ==============================================================================
# 7. Lessons Learned Registration & Integrity
# ==============================================================================

def test_lesson_c22i_003_strictly_descriptive(lessons_data):
    lesson = next((l for l in lessons_data["lessons"] if l["lesson_id"] == "LL-C22I-003"), None)
    assert lesson is not None
    assert lesson["status"] == "REGRESSION_PROTECTED"
    assert "substantially explains" not in lesson["description"].lower()
    assert "gradient noise" not in lesson["description"].lower()
    assert "drives volatility" not in lesson["description"].lower()
    assert "causes volatility" not in lesson["description"].lower()
    assert "descriptive association" in lesson["description"].lower()


def test_lesson_c22j_001_no_unsupported_gradient_claims(lessons_data):
    lesson = next((l for l in lessons_data["lessons"] if l["lesson_id"] == "LL-C22J-001"), None)
    assert lesson is not None
    assert lesson["status"] == "REGRESSION_PROTECTED"
    assert lesson["category"] == "SCIENTIFIC_VALIDITY"
    assert "DIAG-05" in lesson["notes"] or "DIAG-05" in lesson["prevention_method"]


def test_lesson_c22j_002_descriptive_association_bounding(lessons_data):
    lesson = next((l for l in lessons_data["lessons"] if l["lesson_id"] == "LL-C22J-002"), None)
    assert lesson is not None
    assert lesson["status"] == "REGRESSION_PROTECTED"
    assert lesson["category"] == "SCIENTIFIC_VALIDITY"
    assert "n=5" in lesson["description"]


def test_lesson_c22j_003_bounded_starvation_conclusion(lessons_data):
    lesson = next((l for l in lessons_data["lessons"] if l["lesson_id"] == "LL-C22J-003"), None)
    assert lesson is not None
    assert lesson["status"] == "REGRESSION_PROTECTED"
    assert lesson["category"] == "SCIENTIFIC_VALIDITY"
    assert "Complete exposure absence was not observed" in lesson["detection_method"]


def test_lesson_c22j_004_roadmap_integrity(lessons_data):
    lesson = next((l for l in lessons_data["lessons"] if l["lesson_id"] == "LL-C22J-004"), None)
    assert lesson is not None
    assert lesson["status"] == "REGRESSION_PROTECTED"
    assert lesson["category"] == "DOCUMENTATION_INTEGRITY"
    assert "DIAG-03" in lesson["detection_method"]
    assert "DIAG-04" in lesson["detection_method"]


def test_lesson_c22j_005_tripartite_concept_separation(lessons_data):
    lesson = next((l for l in lessons_data["lessons"] if l["lesson_id"] == "LL-C22J-005"), None)
    assert lesson is not None
    assert lesson["status"] == "REGRESSION_PROTECTED"
    assert lesson["category"] == "SCIENTIFIC_VALIDITY"
    assert "Physical Availability != Sampler Allocation != Demonstrated Learning Effect" in lesson["detection_method"]
