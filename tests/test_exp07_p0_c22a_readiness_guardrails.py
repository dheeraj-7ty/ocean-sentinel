"""Tests for EXP-07-P0-C22-A Numerical Reconciliation, Weight Provenance, and Training-Readiness Guardrails.

Verifies:
- Valid-pixel physical decomposition: 8,595,330 - 194,270 == 8,401,060
- Per-class pixel counts sum to 8,401,060 and match physical mask audit
- Exact weight recomputation from first principles: w_c = sqrt(median(f_valid) / f_c)
- Historical C16 executed literal match and float32 tensor equality
- Precision consistency (formula float64 matches 6-decimal literals after rounding; residual <= 5e-7)
- Dataset-version lineage: OPS02_v1.0.0_FROZEN and v1.0.1_FROZEN physical sample byte identity
- Single independent variable constraint (19 locked dimensions)
- Loss semantics and normalization
- Model collapse policy: zero foreground predictions is recorded behavior, NOT automatic invalidation
- Full initial model state cloning contract
- Complete multi-engine RNG snapshot contract
- Precomputed sample schedule and DataLoader batch parity contracts
- Telemetry schema and absolute no-training, no-Kaggle, no-HOLDOUT, no-Part-III boundaries
- Training readiness verdict is READY_FOR_USER_AUTHORIZATION (never TRAINING_AUTHORIZED)
"""

import json
import math
from pathlib import Path
import pytest
import torch

REPO_ROOT = Path(__file__).resolve().parent.parent
RECONCILIATION_PATH = REPO_ROOT / "data" / "ops02" / "audits" / "ops02_c22a_loss_weight_reconciliation_v1.json"
READINESS_PATH = REPO_ROOT / "data" / "ops02" / "audits" / "ops02_c22a_training_readiness_v1.json"
RUN_STATE_PATH = REPO_ROOT / "scratch" / "exp07_p0_c22a_run_state.json"
PROTOCOL_PATH = REPO_ROOT / "data" / "ops02" / "audits" / "ops02_c21_single_variable_diagnostic_protocol_v1.json"
INCIDENT_PATH = REPO_ROOT / "data" / "metadata" / "exp07_p0_c22a_incident_register_v1.json"


def load_json(path: Path) -> dict:
    assert path.exists(), f"File missing: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def test_valid_pixel_count_decomposition():
    """Verify exact first-principles decomposition of radiometric valid vs training class pixels."""
    rec = load_json(RECONCILIATION_PATH)
    decomp = rec["physical_pixel_decomposition"]
    
    total_raw = decomp["total_raw_raster_pixels"]
    nodata_border = decomp["border_padding_nodata_pixels"]
    radiometric_valid = decomp["total_radiometric_valid_pixels"]
    excluded_source = decomp["excluded_source_label_valid_pixels"]["total_excluded_pixels"]
    dense_training = decomp["total_canonical_dense_training_pixels"]

    assert total_raw == 8650752  # 132 * 256 * 256
    assert nodata_border == 55422
    assert radiometric_valid == 8595330
    assert total_raw == nodata_border + radiometric_valid
    assert excluded_source == 194270  # Source label 9 Sea Ice in valid DN
    assert dense_training == 8401060
    assert radiometric_valid - excluded_source == dense_training


def test_per_class_pixel_counts_and_sum():
    """Verify per-class counts for all 12 canonical dense classes sum to 8,401,060."""
    rec = load_json(RECONCILIATION_PATH)
    classes = rec["per_class_pixel_frequencies_and_weight_derivation"]["classes"]
    assert len(classes) == 12

    expected_counts = {
        0: 2449755,   # BG
        1: 66561,     # AF
        2: 520058,    # BS
        3: 446698,    # LWA
        4: 951354,    # MCC
        5: 22536,     # OF
        6: 771817,    # POW
        7: 45738,     # RF
        8: 352723,    # WS
        9: 112747,    # Eddy
        10: 2659872,  # IWs
        11: 1201      # HM
    }

    total_sum = 0
    for cls in classes:
        dense_id = cls["dense_id"]
        freq = cls["valid_pixel_frequency"]
        assert freq == expected_counts[dense_id]
        total_sum += freq

    assert total_sum == 8401060


def test_first_principles_weight_recomputation():
    """Verify w_c = sqrt(median(f_valid) / f_c) across float64, float32, and 6-decimal rounding."""
    rec = load_json(RECONCILIATION_PATH)
    classes = rec["per_class_pixel_frequencies_and_weight_derivation"]["classes"]
    
    freqs = [cls["valid_pixel_frequency"] for cls in classes]
    sorted_freqs = sorted(freqs)
    # 12 classes: median is average of index 5 and 6
    median_val = (sorted_freqs[5] + sorted_freqs[6]) / 2.0
    assert median_val == 399710.5  # (352,723 + 446,698) / 2.0

    for cls in classes:
        f_c = cls["valid_pixel_frequency"]
        w_f64 = math.sqrt(median_val / f_c)
        assert abs(w_f64 - cls["formula_result_float64"]) < 1e-9

        # Verify rounded 6 decimals matches C16 executed literal
        w_round6 = round(w_f64, 6)
        assert w_round6 == cls["rounded_6_decimals"]
        assert w_round6 == cls["c16_executed_literal"]
        assert cls["status"] == "EXACT_MATCH"


def test_historical_c16_literal_match_and_tensor_equality():
    """Verify historical C16 literals match recomputed values and produce bitwise identical float32 tensors."""
    rec = load_json(RECONCILIATION_PATH)
    verdict = rec["vector_comparison_verdict"]
    
    c16_vec = verdict["historical_c16_vector"]
    control_vec = verdict["future_exp07_diag01_control_vector"]
    assert c16_vec == control_vec

    expected_literals = [
        0.403935, 2.450546, 0.876692, 0.945945, 0.648189, 4.211476,
        0.719641, 2.956203, 1.064525, 1.882870, 0.387652, 18.243211
    ]
    assert c16_vec == expected_literals

    t_c16 = torch.tensor(c16_vec, dtype=torch.float32)
    t_control = torch.tensor(control_vec, dtype=torch.float32)
    assert torch.equal(t_c16, t_control)


def test_precision_consistency_decimal_rounding_residual():
    """Verify formula float64 values agree with 6-decimal literals after rounding; residual <= 5e-7."""
    rec = load_json(RECONCILIATION_PATH)
    classes = rec["per_class_pixel_frequencies_and_weight_derivation"]["classes"]
    
    for cls in classes:
        diff = cls["absolute_difference"]
        # In standard 6-decimal rounding, the decimal residual is bounded by 0.5 * 10^-6 = 5e-7.
        # This is the expected decimal rounding residual, not bounded by float32 machine epsilon.
        assert diff <= 5e-7
        assert round(cls["formula_result_float64"], 6) == cls["c16_executed_literal"]


def test_dataset_version_lineage_and_manifest_hashes():
    """Verify physical manifests and dataset version lineage between v1.0.0 and v1.0.1."""
    audit = load_json(READINESS_PATH)
    d_contract = audit["dataset_contract"]
    
    assert d_contract["dataset_identity"] == "OPS02_v1.0.1_FROZEN"
    assert d_contract["dataset_hash"] == "F5480EA2E26AF8D963EDE40CA658138CDCD6157CD79438E9C8673AD0C1DD8102"
    assert d_contract["partition_manifest_sha256"] == "757DEAF7A7E72BE331843B518A99AF32E14D68A080822F1D9B4FDBADF889F94D"
    assert d_contract["partition_allocation"]["train_tiles"] == 132
    assert d_contract["partition_allocation"]["dev_tiles"] == 40
    assert d_contract["partition_allocation"]["holdout_tiles"] == 40
    assert d_contract["dataset_version_lineage"]["byte_identity"] == "BITWISE_IDENTICAL_PHYSICAL_SAMPLES_AND_MASKS"


def test_single_variable_constraint_and_19_locked_dimensions():
    """Verify exactly one variable differs (CLASS_LOSS_WEIGHT_VECTOR) and 19 dimensions are locked."""
    audit = load_json(READINESS_PATH)
    contrast = audit["single_variable_contrast_contract"]
    
    assert contrast["isolated_variable"] == "CLASS_LOSS_WEIGHT_VECTOR"
    assert len(contrast["control_loss_weight_vector"]) == 12
    assert len(contrast["treatment_loss_weight_vector"]) == 12
    assert contrast["treatment_loss_weight_vector"] == [1.0] * 12
    assert contrast["invariance_dimensions_locked_count"] == 19
    assert len(contrast["invariance_dimensions_locked"]) == 19


def test_loss_contract_semantics():
    """Verify loss function parameters, reduction, ignore_index, and normalization."""
    audit = load_json(READINESS_PATH)
    loss_c = audit["execution_and_parity_contracts"]["loss_contract"]
    
    assert "nn.CrossEntropyLoss" in loss_c["implementation"]
    assert "ignore_index=-100" in loss_c["implementation"]
    assert "reduction='mean'" in loss_c["implementation"]
    assert loss_c["only_difference_allowed"] == "weight_tensor value vector"


def test_no_automatic_background_collapse_invalidation():
    """Verify model background collapse is NOT an automatic run invalidation condition."""
    proto = load_json(PROTOCOL_PATH)
    invalid_rules = proto["invalidation_criteria"]["invalid_conditions"]
    
    for rule in invalid_rules:
        assert "zero foreground" not in rule.lower()
        assert "collapse" not in rule.lower()
    
    collapse_policy = proto["invalidation_criteria"]["model_collapse_policy"]
    assert "do not automatically invalidate" in collapse_policy.lower()
    assert "observed model behavior" in collapse_policy.lower()


def test_initialization_state_contract():
    """Verify full initial architecture state cloning contract."""
    audit = load_json(READINESS_PATH)
    init_c = audit["execution_and_parity_contracts"]["full_initial_state_requirement"]
    
    assert init_c["policy"] == "FULL_INITIAL_MODEL_STATE_IDENTITY"
    assert "initial_model_state.pt" in init_c["specification"]
    assert "sha256(control_init_model) == sha256(treatment_init_model)" in init_c["verification"]


def test_rng_and_sampler_contracts():
    """Verify complete multi-engine RNG snapshot and precomputed sample schedule contracts."""
    audit = load_json(READINESS_PATH)
    rng_c = audit["execution_and_parity_contracts"]["rng_contract"]
    sampler_c = audit["execution_and_parity_contracts"]["sampler_contract"]
    batch_c = audit["execution_and_parity_contracts"]["dataloader_contract"]
    
    assert rng_c["policy"] == "COMPLETE_MULTI_ENGINE_RNG_SNAPSHOT"
    assert "initial_rng_state.pt" in rng_c["specification"]
    assert sampler_c["policy"] == "PRECOMPUTED_CANONICAL_SAMPLE_SCHEDULE"
    assert "canonical_sample_schedule.json" in sampler_c["specification"]
    assert batch_c["policy"] == "PRECOMPUTED_CANONICAL_BATCH_SCHEDULE"
    assert "canonical_batch_schedule.json" in batch_c["specification"]


def test_input_target_parity_contract():
    """Verify input/target checksum assertion before step 1."""
    audit = load_json(READINESS_PATH)
    it_c = audit["execution_and_parity_contracts"]["input_target_contract"]
    assert "assert control_input_checksum == treatment_input_checksum" in it_c["verification"]


def test_metric_contract_no_arbitrary_thresholds():
    """Verify primary metric is dev_mIoU_phenomena and threshold policy is descriptive."""
    audit = load_json(READINESS_PATH)
    m_c = audit["execution_and_parity_contracts"]["metric_contract"]
    assert "dev_mIoU_phenomena" in m_c["primary_metric"]
    assert "classes 1..11" in m_c["primary_metric"]
    assert "background excluded" in m_c["primary_metric"]
    assert "NO_ARBITRARY_THRESHOLDS" in m_c["threshold_policy"]


def test_incident_register_completeness():
    """Verify both C22-A incidents are logged with root cause and remediation."""
    inc = load_json(INCIDENT_PATH)
    assert inc["governance_compliance"]["zero_training_verified"] is True
    assert inc["governance_compliance"]["zero_kaggle_verified"] is True
    assert inc["governance_compliance"]["holdout_access_count"] == 0
    assert inc["governance_compliance"]["part_iii_access_verified"] is False
    
    incident_ids = [i["incident_id"] for i in inc["incidents_catalogued"]]
    assert "INC-C22A-001" in incident_ids
    assert "INC-C22A-002" in incident_ids


def test_training_readiness_verdict():
    """Verify readiness verdict is READY_FOR_USER_AUTHORIZATION and NEVER TRAINING_AUTHORIZED."""
    audit = load_json(READINESS_PATH)
    verdict = audit["executive_verdict"]["readiness_verdict"]
    
    assert verdict == "READY_FOR_USER_AUTHORIZATION"
    assert verdict != "TRAINING_AUTHORIZED"
    assert audit["executive_verdict"]["blocking_issues_count"] == 0


def test_telemetry_schema_and_safety_boundaries():
    """Verify run state telemetry schema, zero training, zero Kaggle, zero HOLDOUT, zero Part-III."""
    state = load_json(RUN_STATE_PATH)
    
    required_fields = [
        "task_id", "phase", "status", "started_at", "last_updated_at",
        "current_step", "training_started", "kaggle_started", "holdout_access",
        "part_iii_access", "active_processes", "artifacts_created",
        "artifacts_modified", "artifacts_verified", "critical_issues",
        "resolved_issues", "blocking_issues", "tests_run", "tests_passed",
        "tests_failed", "training_readiness", "next_action"
    ]
    for field in required_fields:
        assert field in state, f"Telemetry missing field: {field}"

    assert state["task_id"] == "EXP-07-P0-C22-A"
    assert state["training_started"] is False
    assert state["kaggle_started"] is False
    assert state["holdout_access"] is False
    assert state["part_iii_access"] is False
    assert state["active_processes"] == 0
    assert state["training_readiness"] in ["PENDING_AUDIT", "READY_FOR_USER_AUTHORIZATION"]
