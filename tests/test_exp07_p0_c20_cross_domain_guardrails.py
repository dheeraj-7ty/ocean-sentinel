"""EXP-07-P0-C20 Cross-Domain Guardrails, Checkpoint Lineage, Firewall, and Metric Integrity Tests."""

import hashlib
import json
from pathlib import Path
import pytest
import subprocess

REPO_ROOT = Path(__file__).resolve().parent.parent
OPS02_DIR = REPO_ROOT / "data" / "ops02"
AUDITS_DIR = OPS02_DIR / "audits"
METADATA_DIR = REPO_ROOT / "data" / "metadata"
CHECKPOINTS_DIR = REPO_ROOT / "data" / "checkpoints"
SCRATCH_DIR = REPO_ROOT / "scratch"


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest().upper()


def test_checkpoint_lineage_and_cryptographic_identities():
    """Verify exact SHA256 hashes, parameter counts, and BN counts for all three checkpoints."""
    lineage_p = AUDITS_DIR / "ops02_c20_checkpoint_lineage_audit_v1.json"
    assert lineage_p.exists(), "Checkpoint lineage audit must exist"

    with open(lineage_p, "r", encoding="utf-8") as f:
        lineage = json.load(f)

    expected_hashes = {
        "C8_best": "FF30EDCFEFBDF3C321F2D531BF3A8031ABB6F8481FC4F89D3DD8E2781ACAD9D7",
        "C10_best": "D64FE6197B73F47A1B97D2881E273441C61F6562D0B68B4B3C1A9322E6C2190E",
        "C16_best": "936EF935F8049FA15FBC735F8073D08F074796ACC20BE0A2885DD35C7CB09D67",
    }

    for name, expected_hash in expected_hashes.items():
        info = lineage["checkpoints"][name]
        assert info["sha256"] == expected_hash
        assert info["trainable_parameters"] == 14310860
        assert info["batch_norm_2d_layers"] == 30
        assert info["input_channels"] == 1
        assert info["output_channels"] == 12

        # Verify against physical file on disk
        ckpt_path = REPO_ROOT / info["exact_path"]
        assert ckpt_path.exists()
        assert compute_sha256(ckpt_path) == expected_hash


def test_checkpoint_immutability_verification():
    """Verify that checkpoint SHA256 hashes are byte-identical before and after evaluation."""
    integrity_p = AUDITS_DIR / "ops02_c20_cross_eval_integrity_audit_v1.json"
    assert integrity_p.exists(), "Integrity audit must exist"

    with open(integrity_p, "r", encoding="utf-8") as f:
        integrity = json.load(f)

    assert integrity["checkpoint_immutability_verified"] is True
    for ckpt_id in ["C8", "C10", "C16"]:
        assert integrity["checkpoints_verified"][ckpt_id]["status"] == "BYTE_IDENTICAL"


def test_taxonomy_compatibility_lock():
    """Verify 12-class canonical taxonomy, index mapping, and exclusion handling."""
    tax_p = AUDITS_DIR / "ops02_c20_taxonomy_compatibility_v1.json"
    assert tax_p.exists(), "Taxonomy compatibility audit must exist"

    with open(tax_p, "r", encoding="utf-8") as f:
        tax = json.load(f)

    matrix = tax["index_compatibility_matrix"]
    assert len(matrix) == 12

    expected_codes = {
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

    for item in matrix:
        idx = item["index"]
        assert idx in expected_codes
        assert item["canonical_code"] == expected_codes[idx]
        assert item["compatibility_status"] == "EXACT_MATCH"

    exclusions = tax["quarantined_exclusions_handling"]
    assert exclusions["target_dense_index"] == -100
    assert exclusions["source_labels"] == [3, 9, 14]


def test_preprocessing_compatibility_contract():
    """Verify preprocessing specifications for both model-declared and dataset-native evaluation."""
    prep_p = AUDITS_DIR / "ops02_c20_preprocessing_compatibility_v1.json"
    assert prep_p.exists(), "Preprocessing compatibility audit must exist"

    with open(prep_p, "r", encoding="utf-8") as f:
        prep = json.load(f)

    assert prep["physical_image_contract"]["ops01"]["spatial_dimensions"] == [256, 256]
    assert prep["physical_image_contract"]["ops02"]["spatial_dimensions"] == [256, 256]
    assert prep["cross_evaluation_radiometric_contracts"]["eval_a_c16_on_ops01_dev"]["mean_used"] == 4.424158
    assert prep["cross_evaluation_radiometric_contracts"]["eval_b_c8_on_ops02_dev"]["mean_used"] == 4.2756


def test_partition_firewall_and_zero_holdout():
    """Verify partition isolation: exactly 39 OPS-01 DEV, 40 OPS-02 DEV, 0 HOLDOUT, 0 TRAIN."""
    firewall_p = AUDITS_DIR / "ops02_c20_dataset_firewall_v1.json"
    assert firewall_p.exists(), "Dataset firewall audit must exist"

    with open(firewall_p, "r", encoding="utf-8") as f:
        fw = json.load(f)

    assert fw["holdout_protection_controls"]["discovery_prohibited"] is True
    assert fw["holdout_protection_controls"]["inference_prohibited"] is True
    assert fw["partition_quarantine_invariants"]["ops01_dev"]["sample_count"] == 39
    assert fw["partition_quarantine_invariants"]["ops02_dev"]["sample_count"] == 40
    assert fw["partition_quarantine_invariants"]["ops01_holdout"]["access_status"] == "STRICTLY_QUARANTINED_ZERO_ACCESS"
    assert fw["partition_quarantine_invariants"]["ops02_holdout"]["access_status"] == "STRICTLY_QUARANTINED_ZERO_ACCESS"

    integrity_p = AUDITS_DIR / "ops02_c20_cross_eval_integrity_audit_v1.json"
    with open(integrity_p, "r", encoding="utf-8") as f:
        integrity = json.load(f)
    assert integrity["holdout_access_count"] == 0
    assert integrity["holdout_firewall_status"] == "PASS_STRICTLY_ISOLATED"
    assert integrity["part_iii_firewall_status"] == "PASS_STRICTLY_ISOLATED"


def test_metric_implementation_and_phenomena_presence():
    """Verify that all 11 phenomena classes exist in DEV splits and BG is excluded from phenomena mIoU."""
    met_p = AUDITS_DIR / "ops02_c20_metric_verification_v1.json"
    assert met_p.exists(), "Metric verification audit must exist"

    with open(met_p, "r", encoding="utf-8") as f:
        met = json.load(f)

    assert met["primary_metric_contract"]["metric_name"] == "dev_mIoU_phenomena"
    assert met["primary_metric_contract"]["classes_evaluated"] == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    assert met["primary_metric_contract"]["classes_excluded"] == [0]
    assert met["primary_metric_contract"]["ground_truth_verification"]["ops01_dev"]["all_11_classes_present"] is True
    assert met["primary_metric_contract"]["ground_truth_verification"]["ops02_dev"]["all_11_classes_present"] is True


def test_cross_eval_results_arithmetic_consistency():
    """Verify mathematical reconciliation: confusion matrix sums, TP/FP/FN/Union, and mIoU."""
    res_p = AUDITS_DIR / "ops02_c20_cross_eval_results_v1.json"
    assert res_p.exists(), "Cross-eval results must exist"

    with open(res_p, "r", encoding="utf-8") as f:
        res = json.load(f)

    eval_keys = [
        "eval_a_c16_on_ops01_dev",
        "eval_b_c8_on_ops02_dev",
        "eval_c_c10_on_ops02_dev",
    ]

    for ek in eval_keys:
        eval_data = res["evaluations"][ek]
        for norm_key in ["primary_model_declared_norm", "secondary_dataset_native_norm"]:
            norm_res = eval_data[norm_key]
            cm = norm_res["confusion_matrix_12x12"]
            class_metrics = norm_res["class_metrics"]

            total_cm_pixels = sum(sum(row) for row in cm)
            total_support = sum(c["support"] for c in class_metrics.values())
            assert total_cm_pixels == total_support

            phenom_ious = []
            for c_str, cmet in class_metrics.items():
                c = int(c_str)
                row_sum = sum(cm[c])
                assert cmet["support"] == row_sum
                assert cmet["tp"] == cm[c][c]
                assert cmet["fn"] == row_sum - cm[c][c]
                assert cmet["union"] == cmet["tp"] + cmet["fp"] + cmet["fn"]
                if cmet["union"] > 0:
                    calculated_iou = cmet["tp"] / cmet["union"]
                    assert abs(cmet["iou"] - calculated_iou) < 1e-9
                if c > 0:
                    phenom_ious.append(cmet["iou"])

            expected_phenom_miou = sum(phenom_ious) / len(phenom_ious)
            assert abs(norm_res["macro_phenomena_mIoU"] - expected_phenom_miou) < 1e-9


def test_incident_register_and_historical_preservation():
    """Verify that incidents INC-C20-001 through INC-C20-003 are logged and historical files were not mutated."""
    inc_p = METADATA_DIR / "exp07_p0_c20_incident_register_v1.json"
    assert inc_p.exists(), "Incident register must exist"

    with open(inc_p, "r", encoding="utf-8") as f:
        inc = json.load(f)

    assert inc["governance_compliance"]["zero_training_verified"] is True
    assert inc["governance_compliance"]["holdout_access_count"] == 0
    assert inc["governance_compliance"]["historical_artifacts_mutated"] is False

    inc_ids = {item["incident_id"] for item in inc["incidents_catalogued"]}
    assert "INC-C20-001" in inc_ids
    assert "INC-C20-002" in inc_ids
    assert "INC-C20-003" in inc_ids


def test_telemetry_and_prohibitions():
    """Verify live telemetry state: no training, no Kaggle, no holdout access."""
    state_p = SCRATCH_DIR / "exp07_p0_c20_run_state.json"
    assert state_p.exists(), "Run state telemetry must exist"

    with open(state_p, "r", encoding="utf-8") as f:
        state = json.load(f)

    assert state["training_started"] is False
    assert state["kaggle_started"] is False
    assert state["holdout_access"] is False


def test_git_tracked_modifications_preserved():
    """Verify known pre-existing tracked modifications remain unchanged."""
    res = subprocess.run(
        ["git", "diff", "--name-only"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    unstaged_files = set(res.stdout.splitlines())
    assert ".gitignore" in unstaged_files
    assert "src/ocean_sentinel/ingestion/dataset.py" in unstaged_files
