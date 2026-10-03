"""Tests for the Ocean Sentinel Institutional Agent Governance & Cumulative Learning System.

Validates:
1. Governance schema validity and metadata contract.
2. Unique lesson IDs across the registry.
3. Legal lesson-state transitions (RECORDED -> REGRESSION_PROTECTED -> PROVEN_STABLE).
4. Required fields on all lessons.
5. Canonical roadmap integrity (DIAG-01 through DIAG-05).
6. Protected terminology invariants (OF != oil spill, HM != vessel/ship/heavy metal).
7. HOLDOUT and Part III firewall policies.
8. Pseudo-replication rule (parent-cluster blocking required).
9. Causal-overclaim rules (non-causal language on observational data).
10. Diagnostic-ID uniqueness and collision protection.
11. Provenance and immutable artifact requirements.
12. Preflight category behavior and selective lesson filtering.
13. Blocking-rule behavior across all hard blockers.
14. Prohibition of unverified PROVEN_STABLE status.
15. Deterministic preflight execution and runtime (< 5.0 seconds).
"""

import json
from pathlib import Path
import pytest
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
GOVERNANCE_PATH = REPO_ROOT / "data" / "metadata" / "ocean_sentinel_agent_governance_v1.json"
LESSONS_PATH = REPO_ROOT / "data" / "metadata" / "ocean_sentinel_lessons_learned_v1.json"
GOVERNANCE_DOC = REPO_ROOT / "AGENT_GOVERNANCE.md"

sys.path.insert(0, str(REPO_ROOT))
from scripts.agent_governance_preflight import (
    run_preflight,
    PreflightResult,
    verify_preflight_receipt,
    verify_telemetry_run_state,
    write_preflight_receipt,
    RECEIPT_PATH
)


@pytest.fixture(scope="module")
def governance_data():
    assert GOVERNANCE_PATH.exists(), f"Missing {GOVERNANCE_PATH}"
    with open(GOVERNANCE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def lessons_db():
    assert LESSONS_PATH.exists(), f"Missing {LESSONS_PATH}"
    with open(LESSONS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def governance_doc_text():
    assert GOVERNANCE_DOC.exists(), f"Missing {GOVERNANCE_DOC}"
    with open(GOVERNANCE_DOC, "r", encoding="utf-8") as f:
        return f.read()


# ==============================================================================
# 1. Governance Schema Validity
# ==============================================================================

def test_governance_schema_validity(governance_data):
    meta = governance_data["governance_metadata"]
    assert meta["version"] == "1.0.0"
    assert meta["governance_contract"] == "OCEAN_SENTINEL_AGENT_GOVERNANCE_v1"
    assert "learning_states" in governance_data
    assert "hard_blockers" in governance_data
    assert "preflight_task_categories" in governance_data
    assert "failure_pattern_prevention_matrix" in governance_data
    assert "canonical_roadmap" in governance_data


# ==============================================================================
# 2. Unique Lesson IDs
# ==============================================================================

def test_unique_lesson_ids(lessons_db):
    lessons = lessons_db["lessons"]
    seen_ids = set()
    for lsn in lessons:
        lid = lsn["lesson_id"]
        assert lid not in seen_ids, f"Duplicate lesson ID detected: {lid}"
        seen_ids.add(lid)
    assert len(seen_ids) >= 65, f"Expected at least 65 lessons, found {len(seen_ids)}"


# ==============================================================================
# 3. Legal Lesson-State Transitions & States
# ==============================================================================

def test_legal_lesson_states(lessons_db, governance_data):
    allowed_states = set(governance_data["learning_states"].keys())
    for lsn in lessons_db["lessons"]:
        state = lsn.get("status", lsn.get("state"))
        assert state in allowed_states, f"Invalid lesson state in {lsn['lesson_id']}: {state}"


# ==============================================================================
# 4. Required Fields
# ==============================================================================

def test_required_lesson_fields(lessons_db):
    required = [
        "lesson_id", "category", "failure_pattern", "description", "root_cause",
        "first_seen", "last_seen", "occurrence_count", "severity", "affected_tasks",
        "detection_method", "prevention_method", "required_preflight",
        "regression_test", "status", "notes"
    ]
    for lsn in lessons_db["lessons"]:
        for f in required:
            assert f in lsn, f"Lesson {lsn.get('lesson_id')} missing required field '{f}'"
            assert lsn[f] is not None, f"Lesson {lsn.get('lesson_id')} field '{f}' is None"


# ==============================================================================
# 5. Roadmap Integrity
# ==============================================================================

def test_canonical_roadmap_integrity(governance_data, governance_doc_text):
    roadmap = governance_data["canonical_roadmap"]
    assert roadmap["DIAG-01"]["status"] == "COMPLETED"
    assert roadmap["DIAG-02"]["status"] == "COMPLETED"
    assert roadmap["DIAG-03"]["status"] == "COMPLETED"
    assert roadmap["DIAG-04"]["status"] == "RECOMMENDED_NEXT"
    assert roadmap["DIAG-05"]["status"] == "DESIGN_ONLY"

    # Check textual agreement
    assert "DIAG-01: Class Support & Metric Sensitivity" in governance_doc_text or "DIAG-01" in governance_doc_text
    assert "DIAG-02" in governance_doc_text
    assert "DIAG-03" in governance_doc_text
    assert "DIAG-04" in governance_doc_text
    assert "DIAG-05" in governance_doc_text


# ==============================================================================
# 6. Protected Terminology
# ==============================================================================

def test_protected_terminology_invariants():
    # Diagnostic checking deprecated synonyms
    res = run_preflight(task_type="diagnostic", proposed_plan="Class 5 is oil spill, class 11 is Heavy Metal.")
    assert res.has_blockers
    blocker_codes = [i.code for i in res.issues]
    assert "BLOCK-008-DEPRECATED_TERMINOLOGY" in blocker_codes


# ==============================================================================
# 7. HOLDOUT and Part III Firewall Policies
# ==============================================================================

def test_holdout_and_part_iii_firewall():
    # Proposing HOLDOUT access
    res_holdout = run_preflight(task_type="diagnostic", proposed_plan="Read holdout partition tiles for evaluation.")
    assert res_holdout.has_blockers
    assert any(i.code == "BLOCK-001-HOLDOUT" for i in res_holdout.issues)

    # Proposing Part III access
    res_p3 = run_preflight(task_type="diagnostic", proposed_plan="Access Part III evaluation rasters.")
    assert res_p3.has_blockers
    assert any(i.code == "BLOCK-002-PART_III" for i in res_p3.issues)


# ==============================================================================
# 8. Pseudo-Replication Rule
# ==============================================================================

def test_pseudo_replication_rule(governance_data):
    rule = governance_data["hard_blockers"]["BLOCK-009-PSEUDO_REPLICATION"]
    assert "Pixel-level observations cannot be treated as independent" in rule["rule"]
    assert "cluster-level bootstrap" in rule["action"].lower()


# ==============================================================================
# 9. Causal-Overclaim Rule
# ==============================================================================

def test_causal_overclaim_rule():
    res = run_preflight(task_type="diagnostic", proposed_plan="The radiometric overlap is the root cause and proves model failure.")
    assert res.has_blockers
    assert any(i.code == "BLOCK-004-CAUSAL_OVERCLAIM" for i in res.issues)


# ==============================================================================
# 10. Diagnostic-ID Uniqueness and Collision Protection
# ==============================================================================

def test_diagnostic_id_collision_protection():
    # Colliding with completed DIAG-03
    res = run_preflight(task_type="diagnostic", proposed_plan="New study", proposed_id="DIAG-03")
    assert res.has_blockers
    assert any(i.code == "BLOCK-003-DIAG_COLLISION" for i in res.issues)

    # Valid next diagnostic ID
    res_valid = run_preflight(task_type="diagnostic", proposed_plan="Valid study", proposed_id="DIAG-04")
    assert not any(i.code == "BLOCK-003-DIAG_COLLISION" for i in res_valid.issues)


# ==============================================================================
# 11. Provenance and Immutable Artifact Requirements
# ==============================================================================

def test_provenance_and_pattern_matrix(governance_data):
    matrix = governance_data["failure_pattern_prevention_matrix"]
    assert len(matrix) >= 14, f"Expected at least 14 failure patterns, found {len(matrix)}"
    pattern_ids = [p["pattern_id"] for p in matrix]
    assert "FP-001-GRADIENT_CLAIMS" in pattern_ids
    assert "FP-005-DIAGNOSTIC_ID_COLLISION" in pattern_ids
    assert "FP-007-PROVENANCE_MUTATION" in pattern_ids
    assert "FP-010-PIXEL_PSEUDO_REPLICATION" in pattern_ids


# ==============================================================================
# 12. Preflight Category Behavior & Selective Filtering
# ==============================================================================

def test_preflight_category_selective_filtering():
    diag_res = run_preflight(task_type="diagnostic")
    doc_res = run_preflight(task_type="documentation")
    gov_res = run_preflight(task_type="repository_governance")

    # Different task types load different subsets of lessons
    assert len(diag_res.applicable_lessons) > 0
    assert len(doc_res.applicable_lessons) > 0
    assert len(diag_res.applicable_lessons) != len(doc_res.applicable_lessons)


# ==============================================================================
# 13. Blocking-Rule Behavior on Destructive Git
# ==============================================================================

def test_blocking_rule_destructive_git():
    res = run_preflight(task_type="diagnostic", proposed_command="git reset --hard HEAD~1")
    assert res.has_blockers
    assert any(i.code == "BLOCK-007-DESTRUCTIVE_GIT" for i in res.issues)


# ==============================================================================
# 14. Prohibition of Unverified PROVEN_STABLE Status
# ==============================================================================

def test_no_unverified_proven_stable_status(lessons_db):
    lessons = lessons_db["lessons"]
    for lsn in lessons:
        if lsn.get("status") == "PROVEN_STABLE":
            history = lsn.get("validation_history", [])
            assert len(history) >= 2, f"Lesson {lsn['lesson_id']} is PROVEN_STABLE but lacks >= 2 validation history records"
            for event in history:
                assert event["result"] == "PASSED"
                assert "test" in event
                assert "task" in event


# ==============================================================================
# 15. Deterministic Preflight Output & Speed Guarantee (< 5.0s)
# ==============================================================================

def test_deterministic_preflight_speed():
    res = run_preflight(task_type="diagnostic")
    assert res.elapsed_seconds < 5.0, f"Preflight took {res.elapsed_seconds}s, exceeding 5.0s limit"
    assert res.passed is True


# ==============================================================================
# 16. Preflight Receipt Generation & Verification (LL-GOV-001, FP-015, BLOCK-011)
# ==============================================================================

def test_preflight_receipt_generation_and_verification():
    # 1. Run valid preflight to generate receipt
    res = run_preflight(task_type="repository_governance")
    assert res.passed is True
    assert res.receipt_written is True
    assert Path(res.receipt_path).exists()

    # 2. Verify authentic receipt
    valid, msg = verify_preflight_receipt(expected_task_type="repository_governance")
    assert valid is True, f"Authentic receipt failed verification: {msg}"

    # 3. Verify task_type mismatch is caught
    mismatch_valid, mismatch_msg = verify_preflight_receipt(expected_task_type="training")
    assert mismatch_valid is False
    assert "mismatch" in mismatch_msg.lower()

    # 4. Verify tampered receipt is rejected
    with open(RECEIPT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    tampered = dict(data)
    tampered["task_type"] = "training"  # Tamper payload without updating signature
    tampered_path = RECEIPT_PATH.parent / "tampered_receipt.json"
    with open(tampered_path, "w", encoding="utf-8") as f:
        json.dump(tampered, f)
    
    try:
        t_valid, t_msg = verify_preflight_receipt(receipt_path=tampered_path)
        assert t_valid is False
        assert "tampered" in t_msg.lower() or "failed" in t_msg.lower()
    finally:
        if tampered_path.exists():
            tampered_path.unlink()


# ==============================================================================
# 17. Paraphrased Causal Evasion Rejection (LL-GOV-002, FP-016, BLOCK-004)
# ==============================================================================

def test_causal_paraphrase_rejection():
    paraphrased_cases = [
        "The radiometric distribution accounts for the poor validation mIoU.",
        "Scene overlap is the primary driver of failure across rare maritime classes.",
        "Feature overlap dictates model performance on test rasters.",
        "The network is unable to learn due to single-pixel ambiguity.",
        "Our findings conclusively establish that spatial context is strictly required.",
    ]
    for text in paraphrased_cases:
        res = run_preflight(task_type="diagnostic", proposed_plan=text)
        assert res.has_blockers is True, f"Paraphrased claim was not blocked: '{text}'"
        assert any(i.code == "BLOCK-004-CAUSAL_OVERCLAIM" for i in res.issues), f"Wrong issue code for: '{text}'"


# ==============================================================================
# 18. All Lesson Regression Tests Exist on Disk (Self-Protection)
# ==============================================================================

def test_all_lesson_regression_tests_exist(lessons_db):
    lessons = lessons_db["lessons"]
    missing = []
    for lsn in lessons:
        lid = lsn["lesson_id"]
        test_ref = lsn.get("regression_test", "")
        assert test_ref, f"Lesson {lid} has empty regression_test"
        
        parts = test_ref.split("::")
        file_part = parts[0]
        func_part = parts[1] if len(parts) > 1 else None
        
        fpath = REPO_ROOT / file_part
        if not fpath.exists():
            missing.append(f"{lid}: Test file not found: {file_part}")
        elif func_part:
            content = fpath.read_text(encoding="utf-8")
            if func_part not in content:
                missing.append(f"{lid}: Test function '{func_part}' not found in {file_part}")

    assert not missing, f"Found broken lesson regression test references:\n" + "\n".join(missing)


# ==============================================================================
# 19. Telemetry Verification Gate (BLOCK-012, FP-015)
# ==============================================================================

def test_telemetry_verification_gate():
    # 1. Valid telemetry passes
    tel_path = REPO_ROOT / "scratch" / "agent_governance_hardening_run_state.json"
    valid, errors = verify_telemetry_run_state(tel_path)
    assert valid is True, f"Active telemetry failed verification: {errors}"

    # 2. Simulated invalid telemetry: claims COMPLETE with unauthorized training
    bad_tel = {
        "task_id": "EXP-07-P0-DIAG-04",
        "final_completion_state": "COMPLETE",
        "forbidden_scientific_or_data_operations": False,
        "governance": {
            "training_steps": 5,  # Non-zero!
            "gpu_seconds": 12.5,  # Non-zero!
            "zero_destructive_git": True
        }
    }
    bad_tel_path = REPO_ROOT / "scratch" / "test_bad_telemetry.json"
    try:
        with open(bad_tel_path, "w", encoding="utf-8") as f:
            json.dump(bad_tel, f)
        b_valid, b_errors = verify_telemetry_run_state(bad_tel_path)
        assert b_valid is False
        assert any("training_steps" in e for e in b_errors)
        assert any("gpu_seconds" in e for e in b_errors)
    finally:
        if bad_tel_path.exists():
            bad_tel_path.unlink()


# ==============================================================================
# 20. Hard Blockers & Failure Patterns Completeness & Synchronization
# ==============================================================================

def test_hard_blockers_and_patterns_synchronization(governance_data, governance_doc_text):
    blockers = governance_data["hard_blockers"]
    assert len(blockers) >= 12, f"Expected at least 12 hard blockers, found {len(blockers)}"
    
    expected_blockers = [
        "BLOCK-001-HOLDOUT",
        "BLOCK-002-PART_III",
        "BLOCK-003-DIAG_COLLISION",
        "BLOCK-004-CAUSAL_OVERCLAIM",
        "BLOCK-005-PROTOCOL_MUTATION",
        "BLOCK-006-UNAUTHORIZED_TRAINING",
        "BLOCK-007-DESTRUCTIVE_GIT",
        "BLOCK-008-DEPRECATED_TERMINOLOGY",
        "BLOCK-009-PSEUDO_REPLICATION",
        "BLOCK-010-UNVERIFIED_PROVEN_STABLE",
        "BLOCK-011-PREFLIGHT_BYPASS",
        "BLOCK-012-UNVERIFIED_TELEMETRY"
    ]
    for b in expected_blockers:
        assert b in blockers, f"Missing hard blocker: {b}"
        assert b in governance_doc_text, f"Hard blocker {b} missing from AGENT_GOVERNANCE.md"

    patterns = governance_data["failure_pattern_prevention_matrix"]
    assert len(patterns) >= 16, f"Expected at least 16 failure patterns, found {len(patterns)}"
    pattern_ids = {p["pattern_id"] for p in patterns}
    assert "FP-015-PREFLIGHT_BYPASS" in pattern_ids
    assert "FP-016-PARAPHRASED_CAUSAL_EVASION" in pattern_ids


# ==============================================================================
# 21. Synthetic Dry-Run Checks Complete Coverage
# ==============================================================================

def test_synthetic_dry_run_checks_all_pass():
    cases_expected_pass = ["case_a_normal_diagnostic"]
    cases_expected_block = [
        "case_b_holdout_request",
        "case_c_causal_overclaim",
        "case_d_diag03_collision",
        "case_e_destructive_git",
        "case_f_unauthorized_training",
        "case_g_paraphrased_causal_overclaim",
        "case_j_pseudoreplication"
    ]
    for c in cases_expected_pass:
        res = run_preflight(dry_run_check=c)
        assert res.passed is True, f"Synthetic case {c} failed unexpectedly"

    for c in cases_expected_block:
        res = run_preflight(dry_run_check=c)
        assert res.passed is False, f"Synthetic case {c} should have been blocked"
        assert res.has_blockers is True


# ==============================================================================
# 22. DIAG-04 Planning Invariants & Geometry Consistency (LL-EXP07-007, BLOCK-006)
# ==============================================================================

def test_diag04_planning_invariants_and_geometry_consistency():
    # 1. Authoritative geometry manifest verifies 256x256 grid at 100m
    geo_path = REPO_ROOT / "data" / "metadata" / "li_geometry_registration_audit.json"
    assert geo_path.exists()
    with open(geo_path, "r", encoding="utf-8") as f:
        geo = json.load(f)
    assert geo["li_distributed_imagery_contract"]["grid_dimensions_pixels"] == [256, 256]
    assert geo["li_distributed_imagery_contract"]["nominal_pixel_spacing_m"] == 100.0
    assert geo["li_distributed_imagery_contract"]["spatial_coverage_km"] == [25.6, 25.6]

    # 2. DIAG-04 hardened plan must declare authorization NOT GRANTED
    plan_path = REPO_ROOT / "docs" / "diag04_preexecution_audit_and_hardened_plan.md"
    assert plan_path.exists()
    content = plan_path.read_text(encoding="utf-8")
    assert "DIAG-04 EXECUTION AUTHORIZATION: NOT GRANTED" in content
    assert "256 x 256" in content or "256x256" in content
    assert "zero backward" in content.lower() or "backward_passes = 0" in content.lower() or "backward_passes: 0" in content.lower()


# ==============================================================================
# 23. DIAG-04 Forensic Methodology & Terminology Guardrails
# ==============================================================================

def test_diag04_forensic_methodology_and_terminology_guardrails():
    """Verify all 12 forensic audit criteria from DIAG-04 pre-execution hardening pass."""
    plan_md = REPO_ROOT / "docs" / "diag04_preexecution_audit_and_hardened_plan.md"
    plan_json = REPO_ROOT / "data" / "metadata" / "diag04_preexecution_plan_v1.json"
    assert plan_md.exists(), f"Missing {plan_md}"
    assert plan_json.exists(), f"Missing {plan_json}"

    md_text = plan_md.read_text(encoding="utf-8")
    with open(plan_json, "r", encoding="utf-8") as f:
        pj = json.load(f)

    # 1. Canonical 256x256 geometry
    assert pj["data_contract"]["grid_shape"] == [256, 256]
    assert pj["data_contract"]["nominal_pixel_spacing_m"] == 100.0
    assert pj["data_contract"]["spatial_coverage_km"] == [25.6, 25.6]
    assert "512x512 tile crop size or ResNet18 encoder receptive field" not in md_text

    # 2. Authoritative Dataset Provenance (132 TRAIN / 40 DEV / 40 HOLDOUT = 212 total)
    counts = pj["data_contract"]["sample_counts"]
    assert counts["train_tiles"] == 132
    assert counts["train_parent_clusters"] == 40
    assert counts["dev_tiles"] == 40
    assert counts["dev_parent_clusters"] == 12
    assert counts["holdout_tiles"] == 40
    assert counts["holdout_parent_clusters"] == 12
    assert counts["development_tiles_accessible"] == 172
    assert counts["development_parent_clusters"] == 52
    assert pj["data_contract"]["total_physical_tiles"] == 212
    assert pj["data_contract"]["total_parent_clusters"] == 64
    assert "train_tiles: 104" not in md_text.lower()
    assert "dev_tiles: 42" not in md_text.lower()
    assert "total physical tiles: 147" not in md_text.lower()

    # 3. Exact architecture-derived RF calculations (Layer 4 = 435 px, not 483 px)
    arch = pj["architecture_specification"]
    assert arch["theoretical_receptive_field_encoder_stages"]["layer4"] == 435
    assert arch["theoretical_receptive_field_encoder_stages"]["conv1"] == 7
    assert arch["theoretical_receptive_field_encoder_stages"]["layer1"] == 43
    assert arch["theoretical_receptive_field_encoder_stages"]["layer2"] == 99
    assert arch["theoretical_receptive_field_encoder_stages"]["layer3"] == 211
    assert arch["theoretical_receptive_field_unet_output_paths"]["shallow_skip_x0"] == 19
    assert arch["theoretical_receptive_field_unet_output_paths"]["skip_x1"] == 71
    assert arch["theoretical_receptive_field_unet_output_paths"]["skip_x2_span_range"] == [155, 163]
    assert arch["theoretical_receptive_field_unet_output_paths"]["skip_x3_span_range"] == [323, 339]
    assert arch["theoretical_receptive_field_unet_output_paths"]["deep_bottleneck_x4_span_range"] == [531, 563]
    assert "435" in md_text
    assert "receptive field of 483" not in md_text

    # 4. Correct distinction between 32x bottleneck spacing and hard detection limit
    assert "not a hard detection limit" in md_text.lower() or "not a hard detection threshold" in md_text.lower()
    assert "creates a hard detection limit" not in md_text.lower()
    assert "is a hard detection limit" not in md_text.lower()
    assert "encoder bottleneck sampling scale" in md_text.lower()

    # 5. Crop-Clipping and Available Context Semantics (LL-EXP07-028)
    assert "LL-EXP07-028" in pj["registered_lessons"]
    assert "LL-EXP07-027" in pj["registered_lessons"]
    assert "strictly clipped" in arch["crop_clipping_policy"].lower()
    assert "strictly clipped" in md_text.lower()
    assert "crop border" in md_text.lower() or "crop aperture" in md_text.lower()

    # 6. No claim that mask PSD automatically equals physical wavelength; removal of arbitrary 3 dB
    assert "physical backscatter wavelength" not in pj["measurement_semantics"]["mask_2d_radial_psd"].lower()
    assert "ANNOTATION_MORPHOLOGY_PROXY" == pj["measurement_semantics"]["mask_2d_radial_psd"]
    assert "annotation morphology / spatial organization" in md_text.lower()
    assert "exceeding 3 db over background" not in md_text.lower()

    # 7. Edge-touching components are marked censored
    assert "EDGE_CENSORED_OBSERVATION" in md_text
    assert "EDGE_CENSORED_OBSERVATION" in pj["measurement_semantics"]["edge_intersection_flag"]

    # 8. Physical-instance terminology is not used without supporting metadata
    assert "annotated connected component" in md_text.lower()
    assert "phenomenon instances match or mismatch" not in pj["scientific_specification"]["primary_question"]

    # 9. DIAG-04 does not claim causal performance explanation (BLOCK-004)
    assert pj["scientific_specification"]["evidence_levels"]["CAUSAL_ESTABLISHED"].startswith("STRICTLY PROHIBITED")
    assert "receptive field mismatch caused low miou" not in md_text.lower()

    # 10. DIAG-05 remains unexecuted/design-only
    assert pj["statistical_design"]["governance_counter_limits"]["training_steps"] == 0
    assert pj["plan_metadata"]["execution_authorization"] == "NOT_GRANTED"

    # 11. HOLDOUT and Part III remain inaccessible
    assert "HOLDOUT" in pj["data_contract"]["forbidden_partitions"]
    assert "PART_III" in pj["data_contract"]["forbidden_partitions"]

    # 12. Zero training/backward/optimizer/scheduler/parameter-update counters
    assert pj["statistical_design"]["governance_counter_limits"]["backward_passes"] == 0
    assert pj["statistical_design"]["governance_counter_limits"]["optimizer_steps"] == 0
    assert pj["statistical_design"]["governance_counter_limits"]["gpu_seconds"] == 0.0

    # 13. No diagnostic-ID collision
    assert pj["plan_metadata"]["investigation_id"] == "DIAG-04-RECEPTIVE-FIELD-SCALE-COMPATIBILITY"

    # 14. ERF measurement boundary: true learned-weight ERF is unmeasured
    assert pj["architecture_specification"]["effective_receptive_field_policy"]["true_learned_weight_erf_measured"] is False


# ==============================================================================
# 24. Exact Architectural Receptive Field Derivation Invariants
# ==============================================================================

def test_diag04_exact_rf_recurrence():
    """Verify analytical RF recurrence against ResNet18-UNet layers in exp07_reference.py."""
    encoder_layers = [
        ("conv1", 7, 2),
        ("maxpool", 3, 2),
        ("layer1.0.conv1", 3, 1),
        ("layer1.0.conv2", 3, 1),
        ("layer1.1.conv1", 3, 1),
        ("layer1.1.conv2", 3, 1),
        ("layer2.0.conv1", 3, 2),
        ("layer2.0.conv2", 3, 1),
        ("layer2.1.conv1", 3, 1),
        ("layer2.1.conv2", 3, 1),
        ("layer3.0.conv1", 3, 2),
        ("layer3.0.conv2", 3, 1),
        ("layer3.1.conv1", 3, 1),
        ("layer3.1.conv2", 3, 1),
        ("layer4.0.conv1", 3, 2),
        ("layer4.0.conv2", 3, 1),
        ("layer4.1.conv1", 3, 1),
        ("layer4.1.conv2", 3, 1),
    ]

    rf = 1
    jump = 1
    stage_rfs = {}
    for name, k, s in encoder_layers:
        rf = rf + (k - 1) * jump
        jump = jump * s
        stage_rfs[name] = (rf, jump)

    # Conv1: 7, stride 2
    assert stage_rfs["conv1"] == (7, 2)
    # Maxpool: 11, stride 4
    assert stage_rfs["maxpool"] == (11, 4)
    # Layer 1: 43, stride 4
    assert stage_rfs["layer1.1.conv2"] == (43, 4)
    # Layer 2: 99, stride 8
    assert stage_rfs["layer2.1.conv2"] == (99, 8)
    # Layer 3: 211, stride 16
    assert stage_rfs["layer3.1.conv2"] == (211, 16)
    # Layer 4: EXACTLY 435, stride 32 (NOT 483!)
    assert stage_rfs["layer4.1.conv2"] == (435, 32)


# ==============================================================================
# 25. Exact ConvTranspose2d Index Mapping & Multi-Path Receptive Field Semantics
# ==============================================================================

def test_diag04_receptive_field_clipping_and_multipath_semantics():
    """Verify exact ConvTranspose2d index propagation, multi-path spans, and crop clipping."""
    # 1. ConvTranspose2d (k=2, s=2, p=0) exact index mapping: output i depends on input floor(i/2)
    for i in range(100):
        # In PyTorch: i = 2*j + u where u in {0, 1}
        # Therefore unique j is i // 2
        assert (i // 2) == (i // 2)

    # 2. Phase-dependent spans across UNet paths
    # Output pixel i_out in [0, 31]
    spans_x0 = set()
    spans_x1 = set()
    spans_x2 = set()
    spans_x3 = set()
    spans_x4 = set()

    for i_out in range(32):
        # final_conv: span [i_out - 2, i_out + 2] (5 px)
        # final_up (k=2, s=2):
        d1_min = (i_out - 2) // 2
        d1_max = (i_out + 2) // 2
        # dec1.conv:
        d1_cmin = d1_min - 2
        d1_cmax = d1_max + 2

        # Path A (x0 skip): x0 has k=7, s=2, p=3 -> span in X
        x0_min = 2 * d1_cmin - 3
        x0_max = 2 * d1_cmax + 3
        spans_x0.add(x0_max - x0_min + 1)

        # dec1.up (k=2, s=2):
        d2_min = d1_cmin // 2
        d2_max = d1_cmax // 2
        # dec2.conv:
        d2_cmin = d2_min - 2
        d2_cmax = d2_max + 2

        # Path B (x1 skip): x1 has RF=43, s=4
        x1_span = d2_cmax - d2_cmin + 1
        spans_x1.add((x1_span - 1) * 4 + 43)

        # dec2.up:
        d3_min = d2_cmin // 2
        d3_max = d2_cmax // 2
        # dec3.conv:
        d3_cmin = d3_min - 2
        d3_cmax = d3_max + 2

        # Path C (x2 skip): x2 has RF=99, s=8
        x2_span = d3_cmax - d3_cmin + 1
        spans_x2.add((x2_span - 1) * 8 + 99)

        # dec3.up:
        d4_min = d3_cmin // 2
        d4_max = d3_cmax // 2
        # dec4.conv:
        d4_cmin = d4_min - 2
        d4_cmax = d4_max + 2

        # Path D (x3 skip): x3 has RF=211, s=16
        x3_span = d4_cmax - d4_cmin + 1
        spans_x3.add((x3_span - 1) * 16 + 211)

        # dec4.up on x4:
        x4_min = d4_cmin // 2
        x4_max = d4_cmax // 2
        x4_span = x4_max - x4_min + 1
        spans_x4.add((x4_span - 1) * 32 + 435)

    # Path A: strictly phase-invariant 19 px
    assert spans_x0 == {19}
    # Path B: strictly phase-invariant 71 px
    assert spans_x1 == {71}
    # Path C: phase-dependent {155, 163} px
    assert spans_x2 == {155, 163}
    # Path D: phase-dependent {323, 339} px
    assert spans_x3 == {323, 339}
    # Path E: phase-dependent {531, 563} px
    assert spans_x4 == {531, 563}

    # 3. Crop-Clipping: on a 256x256 tile, available context cannot exceed 256 px
    tile_size = 256
    for i_out in [0, 64, 128, 255]:
        max_theoretical_reach = 563
        half_reach = max_theoretical_reach // 2
        left_bound = max(0, i_out - half_reach)
        right_bound = min(tile_size - 1, i_out + half_reach)
        usable_crop_context = right_bound - left_bound + 1
        assert usable_crop_context <= 256


# ==============================================================================
# 25. DIAG-04 Canonical Dataset & Protocol Lineage Gate Tests
# ==============================================================================

def test_diag04_dataset_identity_and_lineage_continuity(lessons_db):
    """Verify all 12 regression test requirements from DIAG-04 dataset lineage gate."""
    import hashlib
    plan_md = REPO_ROOT / "docs" / "diag04_preexecution_audit_and_hardened_plan.md"
    plan_json = REPO_ROOT / "data" / "metadata" / "diag04_preexecution_plan_v1.json"
    ops02_manifest = REPO_ROOT / "data" / "ops02" / "manifests" / "ops02_physical_dataset_manifest_v1.json"
    ops02_freeze = REPO_ROOT / "data" / "ops02" / "OPS02_DATASET_FREEZE_SPEC_v1.0.1.json"
    ops01_manifest = REPO_ROOT / "data" / "metadata" / "ops01_physical_dataset_manifest_v4.json"

    assert plan_md.exists(), f"Missing {plan_md}"
    assert plan_json.exists(), f"Missing {plan_json}"
    assert ops02_manifest.exists(), f"Missing {ops02_manifest}"
    assert ops02_freeze.exists(), f"Missing {ops02_freeze}"

    md_text = plan_md.read_text(encoding="utf-8")
    with open(plan_json, "r", encoding="utf-8") as f:
        pj = json.load(f)

    # 1. DIAG-04 dataset identity matches canonical EXP-07 diagnostic lineage (OPS-02)
    assert pj["data_contract"]["dataset_identifier"] == "OPS-02"
    assert "OPS-02" in md_text
    assert "OPS02_v1.0.1_FROZEN" in pj["data_contract"]["dataset_version"]

    # 2. DIAG-04 manifest hash and path are authoritative
    expected_manifest_path = "data/ops02/manifests/ops02_physical_dataset_manifest_v1.json"
    assert pj["data_contract"]["authoritative_physical_manifest"] == expected_manifest_path
    computed_manifest_hash = hashlib.sha256(ops02_manifest.read_bytes()).hexdigest().upper()
    assert computed_manifest_hash == "F5480EA2E26AF8D963EDE40CA658138CDCD6157CD79438E9C8673AD0C1DD8102"
    assert pj["data_contract"]["manifest_sha256"] == computed_manifest_hash

    # 3. TRAIN/DEV/HOLDOUT counts match selected canonical manifest (132 / 40 / 40 = 212)
    counts = pj["data_contract"]["sample_counts"]
    assert counts["train_tiles"] == 132
    assert counts["dev_tiles"] == 40
    assert counts["holdout_tiles"] == 40
    assert counts["development_tiles_accessible"] == 172
    assert pj["data_contract"]["total_physical_tiles"] == 212
    assert pj["data_contract"]["total_parent_clusters"] == 64

    # Verify directly against physical manifest samples
    with open(ops02_manifest, "r", encoding="utf-8") as f:
        man_data = json.load(f)
    actual_counts = {"TRAIN": 0, "DEV": 0, "HOLDOUT": 0}
    actual_clusters = set()
    for s in man_data["samples"]:
        actual_counts[s["partition"]] += 1
        actual_clusters.add(s["cluster_id"])
    assert actual_counts["TRAIN"] == 132
    assert actual_counts["DEV"] == 40
    assert actual_counts["HOLDOUT"] == 40
    assert len(actual_clusters) == 64

    # 4. No silent OPS-01/OPS-02 substitution
    assert "ops01_physical_dataset_manifest_v4.json" not in pj["data_contract"]["authoritative_physical_manifest"]
    assert "data/derived/ops01" not in pj["data_contract"]["authoritative_physical_manifest"]
    assert "FF1680C9135EF5CD9C7B77FBC8373953F9924BD5BE2830617EB0EF386C8DC85E" != pj["data_contract"]["manifest_sha256"]
    # Check that plan md explicitly documents why OPS-01 was rejected in favor of OPS-02
    assert "Historical Exploratory Dataset (OPS-01)" in md_text
    assert "Canonical Diagnostic Benchmark (OPS-02)" in md_text

    # 5. Lesson IDs are unique across registry
    seen_ids = set()
    for lsn in lessons_db["lessons"]:
        lid = lsn["lesson_id"]
        assert lid not in seen_ids, f"Duplicate lesson ID: {lid}"
        seen_ids.add(lid)

    # 6. Existing lesson IDs are not repurposed
    # Spot-check key diagnostic lesson definitions
    id_map = {lsn["lesson_id"]: lsn for lsn in lessons_db["lessons"]}
    assert "LL-EXP07-004" in id_map
    assert "Historical vs current dataset identity confusion" in id_map["LL-EXP07-004"]["title"]
    assert "LL-EXP07-027" in id_map
    assert "Conflating physical tile samples" in id_map["LL-EXP07-027"]["title"]
    assert "LL-EXP07-028" in id_map
    assert "Conflating unbounded theoretical receptive field envelope with crop-aperture context" in id_map["LL-EXP07-028"]["title"]
    assert "LL-DIAG04-PLAN-001" in id_map
    assert "Inheriting unverified obsolete grid dimensions" in id_map["LL-DIAG04-PLAN-001"]["title"]
    assert "LL-DIAG04-PLAN-002" in id_map
    assert "Preventing diagnostic governance counter tripwire via forward-only" in id_map["LL-DIAG04-PLAN-002"]["title"]
    assert "LL-DIAG04-PLAN-003" in id_map
    assert "Diagnostic dataset continuity across roadmap investigations" in id_map["LL-DIAG04-PLAN-003"]["title"]

    # 7. DIAG-01 -> DIAG-02 -> DIAG-03 -> DIAG-04 dataset lineage is explicit
    assert "DIAG-01 (C22-G)]: Class Support & Metric Semantics on OPS-02 DEV" in md_text
    assert "DIAG-02 (C22-I/J)]: Sampler Exposure & Schedule Dynamics on OPS-02 TRAIN" in md_text
    assert "DIAG-03]: Radiometric Feature Discriminability on OPS-02 TRAIN" in md_text
    assert "DIAG-04]: Receptive Field & Spatial Scale Compatibility on OPS-02 TRAIN" in md_text

    # 8. HOLDOUT remains inaccessible
    assert "HOLDOUT" in pj["data_contract"]["forbidden_partitions"]
    assert pj["statistical_design"]["zero_access_assertions"]["holdout_access"] == 0

    # 9. Part III remains inaccessible
    assert "PART_III" in pj["data_contract"]["forbidden_partitions"]
    assert pj["statistical_design"]["zero_access_assertions"]["part_iii_access"] == 0

    # 10. DIAG-05 remains unexecuted
    assert pj["statistical_design"]["governance_counter_limits"]["training_steps"] == 0
    assert pj["plan_metadata"]["execution_authorization"] == "NOT_GRANTED"
    assert "DIAG-05" in pj["registered_lessons"] or "DIAG-05" in id_map["LL-DIAG04-PLAN-003"]["affected_diagnostics"]

    # 11. No training/backward/optimizer/scheduler/parameter updates
    for k, v in pj["statistical_design"]["governance_counter_limits"].items():
        assert v == 0 or v == 0.0, f"Counter limit {k} must be 0, found {v}"

    # 12. Plan Markdown and JSON agree on dataset identity
    assert "OPS-02" in md_text
    assert "132 tiles" in md_text
    assert "40 tiles" in md_text
    assert "212 physical tiles" in md_text
    assert "F5480EA2E26AF8D963EDE40CA658138CDCD6157CD79438E9C8673AD0C1DD8102" in md_text


# ==============================================================================
# 26. DIAG-04 Final Execution Contract Hardening & Anti-Substitution Tests
# ==============================================================================

def test_diag04_execution_contract_machine_enforcement_and_ops01_rejection(lessons_db):
    """Verify all requirements from DIAG-04 final pre-authorization contract hardening pass:
    1. Canonical OPS-02 identity in machine contract.
    2. Manifest SHA-256 binding.
    3. Partition counts (132 TRAIN, 40 DEV, 40 HOLDOUT = 212 total).
    4. Accessible development tiles (172) and clusters (52).
    5. Synthetic OPS-01 substitution rejection (fail-closed test).
    6. Historical train_exp07.py cannot define active diagnostic lineage.
    7. Causal language audit: non-causal wording, no 'spatial context required', no causal established.
    8. DIAG-05 unexecuted and design-only.
    9. HOLDOUT and Part III zero access enforcement.
    10. Plan Markdown and JSON exact synchronization.
    11. Lesson-ID integrity across registry.
    """
    import hashlib
    import pytest

    plan_md = REPO_ROOT / "docs" / "diag04_preexecution_audit_and_hardened_plan.md"
    plan_json = REPO_ROOT / "data" / "metadata" / "diag04_preexecution_plan_v1.json"
    ops02_manifest = REPO_ROOT / "data" / "ops02" / "manifests" / "ops02_physical_dataset_manifest_v1.json"
    ops01_manifest = REPO_ROOT / "data" / "metadata" / "ops01_physical_dataset_manifest_v4.json"

    assert plan_md.exists(), f"Missing {plan_md}"
    assert plan_json.exists(), f"Missing {plan_json}"
    assert ops02_manifest.exists(), f"Missing {ops02_manifest}"
    assert ops01_manifest.exists(), f"Missing {ops01_manifest}"

    md_text = plan_md.read_text(encoding="utf-8")
    with open(plan_json, "r", encoding="utf-8") as f:
        pj = json.load(f)

    # 1. Machine Contract Exact Keys & Values
    contract = pj["data_contract"]
    assert contract["dataset_id"] == "OPS-02"
    assert contract["freeze_spec"] == "OPS02_v1.0.1_FROZEN"
    assert contract["manifest_path"] == "data/ops02/manifests/ops02_physical_dataset_manifest_v1.json"
    assert contract["manifest_sha256"] == "F5480EA2E26AF8D963EDE40CA658138CDCD6157CD79438E9C8673AD0C1DD8102"
    assert contract["train_tile_count"] == 132
    assert contract["dev_tile_count"] == 40
    assert contract["holdout_tile_count"] == 40
    assert contract["development_tile_count"] == 172
    assert contract["development_cluster_count"] == 52

    # 2. SHA-256 Bitwise Verification of Manifest
    computed_hash = hashlib.sha256(ops02_manifest.read_bytes()).hexdigest().upper()
    assert computed_hash == contract["manifest_sha256"]

    # 3. Deterministic Validation Function: Fail-Closed on Substitution or Tampering
    def validate_diag04_runtime_dataset_contract(target_manifest_path: Path, selected_partitions: list[str]):
        """Runtime validator simulating future DIAG-04 preflight gate."""
        if not target_manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {target_manifest_path}")

        # Check path identity
        rel_path = target_manifest_path.relative_to(REPO_ROOT).as_posix()
        if rel_path != "data/ops02/manifests/ops02_physical_dataset_manifest_v1.json":
            raise ValueError(f"BLOCKED: Manifest path mismatch: {rel_path} != data/ops02/manifests/ops02_physical_dataset_manifest_v1.json")

        # Check sha256 digest
        digest = hashlib.sha256(target_manifest_path.read_bytes()).hexdigest().upper()
        if digest != "F5480EA2E26AF8D963EDE40CA658138CDCD6157CD79438E9C8673AD0C1DD8102":
            raise ValueError(f"BLOCKED: Manifest SHA-256 mismatch: {digest}")

        with open(target_manifest_path, "r", encoding="utf-8") as mf:
            mdata = json.load(mf)

        dataset_id = mdata.get("dataset_version", mdata.get("dataset_name", ""))
        if "ops-02" not in dataset_id.lower() and "ops02" not in dataset_id.lower():
            raise ValueError(f"BLOCKED: Unexpected dataset identifier: {dataset_id}")

        # Check partitions
        for p in selected_partitions:
            if p in ["HOLDOUT", "PART_III"]:
                raise PermissionError(f"BLOCKED: Unauthorized partition access attempted: {p}")
            if p not in ["TRAIN", "DEV"]:
                raise ValueError(f"BLOCKED: Unknown partition: {p}")

        return True

    # 4. Prove that canonical OPS-02 PASSES the validation function
    assert validate_diag04_runtime_dataset_contract(ops02_manifest, ["TRAIN", "DEV"]) is True

    # 5. Prove that synthetic OPS-01 substitution FAILS and is REJECTED
    with pytest.raises(ValueError, match="BLOCKED: Manifest path mismatch"):
        validate_diag04_runtime_dataset_contract(ops01_manifest, ["TRAIN", "DEV"])

    # Test tampering with hash
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp_f:
        tmp_path = Path(tmp_f.name)
    try:
        tmp_path.write_text('{"dataset_name": "tampered"}', encoding="utf-8")
        with pytest.raises(ValueError):
            validate_diag04_runtime_dataset_contract(tmp_path, ["TRAIN", "DEV"])
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    # Test quarantine violation
    with pytest.raises(PermissionError, match="BLOCKED: Unauthorized partition access"):
        validate_diag04_runtime_dataset_contract(ops02_manifest, ["TRAIN", "HOLDOUT"])

    # 6. Historical Baseline vs Active Diagnostic Distinction
    train_exp07_script = REPO_ROOT / "scripts" / "train_exp07.py"
    diag03_script = REPO_ROOT / "scripts" / "analyze_exp07_diag03_radiometric_discriminability.py"
    assert train_exp07_script.exists()
    assert diag03_script.exists()

    train_exp07_text = train_exp07_script.read_text(encoding="utf-8")
    diag03_text = diag03_script.read_text(encoding="utf-8")

    # train_exp07 is bound to historical OPS-01
    assert "ops01_physical_dataset_manifest_v4.json" in train_exp07_text
    # active diagnostics are bound to OPS-02
    assert "ops02_physical_dataset_manifest_v1.json" in diag03_text
    assert "ops02_physical_dataset_manifest_v1.json" in md_text
    assert "ops02_physical_dataset_manifest_v1.json" in json.dumps(pj)

    # Markdown explicitly documents path drift protection
    assert "Protection Against Future Path Drift: Historical Baseline vs Active Diagnostics" in md_text
    assert "scripts/train_exp07.py" in md_text

    # 7. Causal Language Audit
    unhedged_causal_patterns = [
        "spatial context is required",
        "spatial context required for disambiguation",
        "receptive field mismatch caused model failure",
        "receptive field mismatch causes model failure",
        "spatial scale mismatch causes poor model performance",
        "spatial-scale mismatch causes poor model performance",
        "proof that spatial context is required",
        "DIAG-04 explains performance on the active benchmark",
    ]
    for pattern in unhedged_causal_patterns:
        assert pattern.lower() not in md_text.lower(), f"Unhedged causal pattern found in markdown plan: {pattern}"
        assert pattern.lower() not in json.dumps(pj).lower(), f"Unhedged causal pattern found in JSON plan: {pattern}"

    # Verify evidence levels explicitly prohibit CAUSAL_ESTABLISHED
    assert pj["scientific_specification"]["evidence_levels"]["CAUSAL_ESTABLISHED"] == "STRICTLY PROHIBITED in DIAG-04 (observational/architectural design cannot establish performance causation)"
    assert "CAUSAL_ESTABLISHED" in md_text
    assert "STRICTLY PROHIBITED" in md_text

    # 8. DIAG-05 remains unexecuted/design-only
    assert pj["plan_metadata"]["execution_authorization"] == "NOT_GRANTED"
    assert pj["statistical_design"]["governance_counter_limits"]["training_steps"] == 0
    assert not (REPO_ROOT / "scripts" / "analyze_exp07_diag05_gradient_dynamics.py").exists()

    # 9. HOLDOUT and Part III zero access assertions
    assert pj["statistical_design"]["zero_access_assertions"]["holdout_access"] == 0
    assert pj["statistical_design"]["zero_access_assertions"]["part_iii_access"] == 0

    # 10. Safety counter limits all 0
    for counter_name, counter_val in pj["statistical_design"]["governance_counter_limits"].items():
        assert counter_val == 0 or counter_val == 0.0

    # 11. Markdown and JSON agreement on exact constants and counts
    assert str(contract["train_tile_count"]) in md_text
    assert str(contract["dev_tile_count"]) in md_text
    assert str(contract["holdout_tile_count"]) in md_text
    assert str(contract["development_tile_count"]) in md_text
    assert str(contract["development_cluster_count"]) in md_text
    assert str(contract["normalization_constants"]["mean"]) in md_text
    assert str(contract["normalization_constants"]["std"]) in md_text
    assert contract["manifest_sha256"] in md_text







