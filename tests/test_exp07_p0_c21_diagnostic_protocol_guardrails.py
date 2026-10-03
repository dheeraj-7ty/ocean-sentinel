"""Tests for EXP-07-P0-C21 Single-Variable Diagnostic Protocol & Invariant Guardrails.

Verifies:
- 19 locked experimental dimensions and single independent variable
- Canonical Sqrt-Median loss weights and uniform treatment loss weights
- Source label vs dense index terminology precision
- Full model initialization state cloning and RNG snapshot contracts
- Sample schedule, DataLoader batch ID, and input/target parity contracts
- Complete optimizer, scheduler, and BatchNorm parity contracts
- Rejection of arbitrary thresholds and causal overclaims
- Telemetry integrity and absolute no-training boundaries
"""

import json
from pathlib import Path
import re
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = REPO_ROOT / "data" / "ops02" / "audits" / "ops02_c21_single_variable_diagnostic_protocol_v1.json"
RUN_STATE_PATH = REPO_ROOT / "scratch" / "exp07_p0_c21_run_state.json"
POST_AUDIT_PATH = REPO_ROOT / "data" / "ops02" / "audits" / "ops02_c21_c20_post_audit_v1.json"


def load_protocol() -> dict:
    assert PROTOCOL_PATH.exists(), f"Protocol file missing: {PROTOCOL_PATH}"
    return json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))


def test_canonical_taxonomy_ordering():
    """INV-07: Verify 12 dense classes with exact names and indices."""
    proto = load_protocol()
    expected_classes = [
        "BG", "AF", "BS", "LWA", "MCC", "OF",
        "POW", "RF", "WS", "Eddy", "IWs", "HM"
    ]
    # Check dense index 3 is LWA and dense index 9 is Eddy
    assert expected_classes[3] == "LWA"
    assert expected_classes[9] == "Eddy"

    inv7 = next(i for i in proto["locked_experimental_dimensions"]["invariants"] if i["id"] == "INV-07")
    assert "Dense 3=LWA" in inv7["value"]
    assert "Dense 9=Eddy" in inv7["value"]


def test_source_labels_vs_dense_indices_terminology():
    """INV-08: Rejects conflating source labels with dense indices."""
    proto = load_protocol()
    inv8 = next(i for i in proto["locked_experimental_dimensions"]["invariants"] if i["id"] == "INV-08")
    assert "SOURCE LABELS" in inv8["value"]
    assert "3 (Iceberg)" in inv8["value"]
    assert "9 (Sea Ice)" in inv8["value"]
    assert "14 (Mineral Oil Spill)" in inv8["value"]

    # Ensure no raw 'classes 3, 9, 14' without SOURCE LABELS in protocol JSON
    text = PROTOCOL_PATH.read_text(encoding="utf-8")
    matches = re.findall(r'(?<!SOURCE LABELS )classes 3, 9, 14', text, re.IGNORECASE)
    assert len(matches) == 0, f"Unqualified 'classes 3, 9, 14' found: {matches}"


def test_exact_canonical_weight_vector():
    """DIFF-01 Control: Canonical Sqrt-Median-Frequency Class Weights."""
    proto = load_protocol()
    ctrl = proto["single_independent_variable"]["control_condition"]
    assert ctrl["name"] == "Canonical C16 Sqrt-Median-Frequency Class Weights"

    expected_control = [
        0.403935, 2.450546, 0.876692, 0.945945, 0.648189, 4.211476,
        0.719641, 2.956203, 1.064525, 1.882870, 0.387652, 18.243211
    ]
    assert len(ctrl["weight_vector_float32"]) == 12
    for actual, expected in zip(ctrl["weight_vector_float32"], expected_control):
        assert abs(actual - expected) < 1e-6


def test_exact_uniform_treatment_vector():
    """DIFF-01 Treatment: Uniform Unweighted Class Weights (all 12 classes = 1.0)."""
    proto = load_protocol()
    treat = proto["single_independent_variable"]["treatment_condition"]
    assert treat["name"] == "Uniform Unweighted Class Weights"

    expected_treatment = [1.0] * 12
    assert len(treat["weight_vector_float32"]) == 12
    for val in treat["weight_vector_float32"]:
        assert val == 1.0


def test_exactly_one_differing_dimension():
    """Verify strictly ONE independent variable is varied."""
    proto = load_protocol()
    assert proto["single_independent_variable"]["variable_identifier"] == "CLASS_LOSS_WEIGHT_VECTOR"
    assert proto["locked_experimental_dimensions"]["dimension_count"] == 19


def test_nineteen_locked_dimensions_parity():
    """Verify all 19 locked experimental dimensions exist and have authoritative sources."""
    proto = load_protocol()
    invariants = proto["locked_experimental_dimensions"]["invariants"]
    assert len(invariants) == 19
    expected_ids = [f"INV-{i:02d}" for i in range(1, 20)]
    actual_ids = [inv["id"] for inv in invariants]
    assert actual_ids == expected_ids
    for inv in invariants:
        assert inv["authority"], f"Missing authority in {inv['id']}"
        assert inv["value"], f"Missing value in {inv['id']}"


def test_loss_semantics_equality():
    """Verify PyTorch CrossEntropyLoss reduction and ignore_index semantics."""
    proto = load_protocol()
    loss_sem = proto["loss_implementation_semantics"]
    assert loss_sem["pytorch_call"] == "nn.CrossEntropyLoss(weight=weight_tensor, ignore_index=-100, reduction='mean')"
    props = loss_sem["parity_properties"]
    assert props["same_logits"] is True
    assert props["same_targets"] is True
    assert props["same_ignore_index"] is True
    assert props["same_reduction"] is True
    assert props["same_valid_pixel_handling"] is True
    assert props["only_differing_element"] == "weight_tensor"


def test_initial_model_state_cloning_contract():
    """Verify separation of backbone enum and full initial model state hash lock."""
    proto = load_protocol()
    init_contract = proto["reproducibility_and_parity_contracts"]["model_initialization_contract"]
    assert init_contract["pretrained_backbone_identity"] == "torchvision.models.ResNet18_Weights.IMAGENET1K_V1"
    assert init_contract["full_initial_model_state_identity"] == "initial_model_state.pt"
    assert "SHA256(control_initial_state) == SHA256(treatment_initial_state)" in init_contract["pre_epoch_0_parity_assertion"]


def test_pretrained_backbone_identifier():
    """Verify suffix f37072fd is documented as filename identifier, not a SHA-256 digest."""
    text = PROTOCOL_PATH.read_text(encoding="utf-8")
    assert "f37072fd SHA-256" not in text
    assert "f37072fd is filename identifier" in text or "f37072fd is filename suffix" in text


def test_rng_snapshot_contract():
    """Verify comprehensive RNG snapshot captures all 6 engines."""
    proto = load_protocol()
    rng_contract = proto["reproducibility_and_parity_contracts"]["rng_parity_contract"]
    expected_engines = [
        "python_random_state",
        "numpy_rng_state",
        "pytorch_cpu_rng_state",
        "pytorch_cuda_rng_state_all",
        "dataloader_worker_seed_config",
        "sampler_generator_state"
    ]
    assert rng_contract["components_captured"] == expected_engines
    assert "initial_rng_state.pt" in rng_contract["persistence"]


def test_sampler_seed_contract():
    """INV-17: Verify canonical seed 42 and epoch formula."""
    proto = load_protocol()
    inv17 = next(i for i in proto["locked_experimental_dimensions"]["invariants"] if i["id"] == "INV-17")
    assert "Base seed 42" in inv17["value"]
    assert "42 + epoch * 1000" in inv17["value"]


def test_sample_schedule_reuse_contract():
    """Verify precomputed canonical schedule reuse across conditions."""
    proto = load_protocol()
    schedule_contract = proto["reproducibility_and_parity_contracts"]["sample_schedule_reuse_contract"]
    assert schedule_contract["policy"] == "PRECOMPUTED_CANONICAL_SCHEDULE"
    assert "control_batch_ids[step] == treatment_batch_ids[step]" in schedule_contract["batch_id_assertion"]


def test_dataloader_and_batch_parity():
    """Verify DataLoader batch ID equality assertion."""
    proto = load_protocol()
    batch_contract = proto["reproducibility_and_parity_contracts"]["sample_schedule_reuse_contract"]
    assert "control_batch_ids[step] == treatment_batch_ids[step]" in batch_contract["batch_id_assertion"]


def test_input_target_parity():
    """Verify per-sample checksum integrity contract."""
    proto = load_protocol()
    integrity = proto["reproducibility_and_parity_contracts"]["input_target_integrity_contract"]
    assert "control_checksum[s] == treatment_checksum[s]" in integrity["assertion"]


def test_optimizer_scheduler_parity():
    """Verify optimizer and scheduler complete state verification before step 1."""
    proto = load_protocol()
    opt_contract = proto["reproducibility_and_parity_contracts"]["optimizer_scheduler_parity_contract"]
    assert len(opt_contract["pre_step_1_verification"]) >= 8


def test_batchnorm_parity():
    """Verify BatchNorm configuration and initial running statistics parity."""
    proto = load_protocol()
    bn_contract = proto["reproducibility_and_parity_contracts"]["batchnorm_parity_contract"]
    assert bn_contract["batchnorm_layers"] == 30
    assert bn_contract["physical_batch_size"] == 8
    assert bn_contract["momentum"] == 0.05
    assert bn_contract["eps"] == 1e-5
    assert "any incidental numerical nondeterminism must be monitored and documented" in bn_contract["nondeterminism_caveat"]


def test_no_arbitrary_thresholds():
    """Verify rejection of arbitrary numerical success cutoffs or invalidation rules."""
    proto = load_protocol()
    invalid_rules = proto["invalidation_criteria"]["invalid_conditions"]
    for rule in invalid_rules:
        assert "gradient norm > 100" not in rule
        assert "gradient norm = 0" not in rule
    assert "Large but finite gradient norms are RECORDED" in proto["invalidation_criteria"]["gradient_norm_policy"]


def test_loss_weight_terminology():
    """Verify absence of 'inverse-frequency' when describing canonical sqrt-median weights."""
    text = PROTOCOL_PATH.read_text(encoding="utf-8")
    assert "inverse-frequency" not in text.lower()


def test_non_causal_interpretation_language():
    """Verify descriptive evidence grades and absence of causal overclaims."""
    proto = load_protocol()
    interp = proto["scientific_interpretation_framework"]
    assert "positive_observed_difference" in interp
    assert "negative_observed_difference" in interp
    assert "near_zero_observed_difference" in interp
    assert "invalid_inconclusive" in interp

    pos = interp["positive_observed_difference"]
    assert "Does NOT prove gradient competition" in pos["bounds"]


def test_historical_control_classification():
    """Verify historical C16 is classified as Historical Reference Control."""
    proto = load_protocol()
    ctrl = proto["single_independent_variable"]["control_condition"]
    assert ctrl["historical_reference_run"] == "C16 (EXP07_RUN003_SEED42)"
    assert "Historical executed vector matches future control vector exactly" in ctrl["precision_audit_verdict"]


def test_telemetry_fields_and_no_training_boundary():
    """Verify run state telemetry schema, zero training, zero Kaggle, zero HOLDOUT."""
    assert RUN_STATE_PATH.exists(), f"Run state file missing: {RUN_STATE_PATH}"
    state = json.loads(RUN_STATE_PATH.read_text(encoding="utf-8"))

    required_fields = [
        "task_id", "phase", "status", "started_at", "last_updated_at",
        "current_step", "training_started", "kaggle_started", "holdout_access",
        "part_iii_access", "active_processes", "artifacts_created",
        "artifacts_modified", "artifacts_verified", "incidents_found",
        "lessons_added", "tests_run", "tests_passed", "tests_failed",
        "protocol_status", "next_action"
    ]
    for field in required_fields:
        assert field in state, f"Run state missing field: {field}"

    assert state["training_started"] is False
    assert state["kaggle_started"] is False
    assert state["holdout_access"] is False
    assert state["part_iii_access"] is False
    assert state["protocol_status"] in ["DRAFTING", "HARDENED_PLAN_APPROVED", "FROZEN_AWAITING_AUTHORIZATION"]
