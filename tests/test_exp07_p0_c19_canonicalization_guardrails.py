"""EXP-07-P0-C19 Canonicalization, Taxonomy Lock, Protocol Authority, and Release Guardrails."""

import json
from pathlib import Path
import pytest
import torch

REPO_ROOT = Path(__file__).resolve().parent.parent
OPS02_DIR = REPO_ROOT / "data" / "ops02"
MANIFESTS_DIR = OPS02_DIR / "manifests"
AUDITS_DIR = OPS02_DIR / "audits"
METADATA_DIR = REPO_ROOT / "data" / "metadata"


def test_canonical_taxonomy_immutability():
    """Verify exact 12-class taxonomy, indices, and prohibition of drifted tokens."""
    tax_p = AUDITS_DIR / "ops02_c19_taxonomy_canonicalization_v1.json"
    assert tax_p.exists(), "Taxonomy canonicalization audit must exist"

    with open(tax_p, "r", encoding="utf-8") as f:
        tax_audit = json.load(f)

    classes = tax_audit["canonical_taxonomy_12_class"]
    assert len(classes) == 12

    expected_mapping = {
        0: "BG",
        1: "AF",
        2: "BS",
        3: "LWA",
        4: "MCC",
        5: "OF",
        6: "POW",
        7: "RF",
        8: "WS",
        9: "Eddy",
        10: "IWs",
        11: "HM",
    }

    for item in classes:
        idx = item["index"]
        code = item["code"]
        assert idx in expected_mapping
        assert expected_mapping[idx] == code

    # Explicitly check required class assignments
    class_dict = {item["index"]: item["code"] for item in classes}
    assert class_dict[5] == "OF"
    assert class_dict[7] == "RF"
    assert class_dict[8] == "WS"
    assert class_dict[10] == "IWs"
    assert class_dict[11] == "HM"

    # Explicitly assert absence of drifted tokens
    all_codes = set(class_dict.values())
    assert "AS" not in all_codes, "'AS' is strictly prohibited from canonical taxonomy"
    assert "Thermal" not in all_codes, "'Thermal' is strictly prohibited from canonical taxonomy"


def test_canonical_freeze_spec_and_manifest_bindings():
    """Verify OPS02_v1.0.1_FROZEN specification and cryptographic manifest bindings."""
    freeze_spec_p = OPS02_DIR / "OPS02_DATASET_FREEZE_SPEC_v1.0.1.json"
    assert freeze_spec_p.exists()

    with open(freeze_spec_p, "r", encoding="utf-8") as f:
        spec = json.load(f)

    assert spec["specification_version"] == "1.0.1"
    assert spec["dataset_version"] == "OPS02_v1.0.1_FROZEN"
    assert spec["summary"]["partition_breakdown"]["TRAIN"]["sample_pairs"] == 132
    assert spec["summary"]["partition_breakdown"]["DEV"]["sample_pairs"] == 40
    assert spec["summary"]["partition_breakdown"]["HOLDOUT"]["sample_pairs"] == 40

    bindings = spec["manifest_cryptographic_bindings"]
    assert "physical_dataset_manifest" in bindings
    assert "partition_manifest" in bindings
    assert "parent_cluster_manifest" in bindings


def test_exact_partition_membership_and_isolation():
    """Verify exact 132 TRAIN, 40 DEV, 40 HOLDOUT samples and zero partition overlap."""
    part_p = MANIFESTS_DIR / "ops02_partition_manifest_v1.json"
    assert part_p.exists()

    with open(part_p, "r", encoding="utf-8") as f:
        part_manifest = json.load(f)

    train_ids = set(part_manifest["partitions"]["TRAIN"]["sample_ids"])
    dev_ids = set(part_manifest["partitions"]["DEV"]["sample_ids"])
    holdout_ids = set(part_manifest["partitions"]["HOLDOUT"]["sample_ids"])

    assert len(train_ids) == 132
    assert len(dev_ids) == 40
    assert len(holdout_ids) == 40

    assert len(train_ids.intersection(dev_ids)) == 0
    assert len(train_ids.intersection(holdout_ids)) == 0
    assert len(dev_ids.intersection(holdout_ids)) == 0


def test_input_dimensions_strictly_256x256():
    """Verify input shape audit confirms 256x256 and rejects 512x512."""
    input_p = AUDITS_DIR / "ops02_c19_input_shape_audit_v1.json"
    assert input_p.exists()

    with open(input_p, "r", encoding="utf-8") as f:
        input_audit = json.load(f)

    assert input_audit["canonical_tensor_contract"]["image_tensor"]["shape"] == "[B, 1, 256, 256]"
    assert input_audit["findings"]["c18_discrepancy_investigation"]["investigation_result"] == "DOCUMENTATION_TYPO"


def test_canonical_training_protocol_values():
    """Verify optimizer, scheduler, batch, and sampler parameters."""
    proto_p = AUDITS_DIR / "ops02_c19_canonical_protocol_v1.json"
    assert proto_p.exists()

    with open(proto_p, "r", encoding="utf-8") as f:
        proto = json.load(f)

    params = proto["canonical_protocol_parameters"]
    assert "AdamW" in params["optimizer"]["canonical_value"]
    assert "0.0005" in params["optimizer"]["canonical_value"] or "5e-4" in params["optimizer"]["canonical_value"]
    assert "0.01" in params["optimizer"]["canonical_value"]

    assert "LinearWarmupCosineAnnealingLR" in params["lr_scheduler"]["canonical_value"]
    assert params["batch_dynamics"]["canonical_value"]["minibatch_size"] == 8
    assert params["batch_dynamics"]["canonical_value"]["gradient_accumulation_steps"] == 2
    assert params["batch_dynamics"]["canonical_value"]["effective_optimizer_batch_size"] == 16

    assert params["sampler_strategy"]["canonical_value"]["draws_per_epoch"] == 72
    assert params["sampler_strategy"]["canonical_value"]["seed_formula"] == "base_seed + epoch * 1000"


def test_metric_lock_specification():
    """Verify primary metric is immutable and dev_mIoU_phenomena evaluates classes 1..11."""
    metric_p = AUDITS_DIR / "ops02_c19_metric_lock_v1.json"
    assert metric_p.exists()

    with open(metric_p, "r", encoding="utf-8") as f:
        metric_lock = json.load(f)

    spec = metric_lock["primary_metric_specification"]
    assert spec["metric_name"] == "dev_mIoU_phenomena"
    assert spec["evaluated_classes"] == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    assert spec["excluded_classes"] == [0]
    assert spec["freeze_status"] == "FROZEN_AND_IMMUTABLE"


def test_c16_execution_reconstruction_machine_truth():
    """Verify C16 machine truth shows best epoch 17, total epochs 27, and single-GPU execution."""
    rec_p = AUDITS_DIR / "ops02_c19_c16_execution_reconstruction_v1.json"
    assert rec_p.exists()

    with open(rec_p, "r", encoding="utf-8") as f:
        rec = json.load(f)

    params = rec["reconstructed_parameters"]
    assert params["best_epoch"] == 17
    assert params["total_epochs_trained"] == 27
    assert pytest.approx(params["best_dev_mIoU_phenomena"], 1e-4) == 0.0494
    assert params["dataset_ingested"]["holdout_access_count"] == 0
    assert params["hardware_execution"]["gpus_allocated_to_trainer"] == 1
    assert params["hardware_execution"]["training_device"] == "cuda:0"


def test_cross_evaluation_epistemic_classification():
    """Verify cross-evaluation is classified as descriptive evidence, not causal proof."""
    cross_p = AUDITS_DIR / "ops02_c19_cross_eval_interpretation_v1.json"
    assert cross_p.exists()

    with open(cross_p, "r", encoding="utf-8") as f:
        cross_eval = json.load(f)

    assert cross_eval["tier_1_epistemic_downgrade"]["evidence_level"] == "OBSERVED / DESCRIPTIVE_ONLY"
    assert "causal" not in cross_eval["tier_1_epistemic_downgrade"]["evidence_level"].lower()


def test_governance_rules_expansion():
    """Verify governance rules 095 through 099 are present and active."""
    gov_p = METADATA_DIR / "ocean_sentinel_governance_rules_v1.json"
    assert gov_p.exists()

    with open(gov_p, "r", encoding="utf-8") as f:
        gov = json.load(f)

    rule_ids = {r["rule_id"] for r in gov["rules"]}
    assert "GOV-RULE-095" in rule_ids
    assert "GOV-RULE-096" in rule_ids
    assert "GOV-RULE-097" in rule_ids
    assert "GOV-RULE-098" in rule_ids
    assert "GOV-RULE-099" in rule_ids
    assert gov["total_rules"] == 99


def test_tier1_release_gate():
    """Verify Tier 1 release gate status and operational prohibitions."""
    gate_p = AUDITS_DIR / "ops02_c19_tier1_release_gate_v1.json"
    assert gate_p.exists()

    with open(gate_p, "r", encoding="utf-8") as f:
        gate = json.load(f)

    assert "TIER1_AUTHORIZED" in gate["verdict"]
    assert gate["flags"]["c19_execution_in_scope"] is False
    assert gate["flags"]["training_required"] is False
    assert gate["flags"]["holdout_access_permitted"] is False


def test_c19_prohibitions_and_telemetry():
    """Verify that no training occurred, holdout is untouched, and telemetry is recorded."""
    telemetry_p = REPO_ROOT / "scratch" / "exp07_p0_c19_run_state.json"
    assert telemetry_p.exists()

    with open(telemetry_p, "r", encoding="utf-8") as f:
        state = json.load(f)

    assert state["task_id"] == "EXP-07-P0-C19"
    assert state["training_started"] is False
    assert state["holdout_access"] is False
    assert state["kaggle_started"] is False
    assert state["next_training_authorized"] is False
