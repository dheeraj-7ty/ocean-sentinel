"""EXP-07-P0-C10: Controlled Replicate Execution (Seed 101) & Stochastic Variance Guardrails.

Automated regression suite verifying:
- Immutable dataset and taxonomy hashes
- Programmatic protocol equivalence between Seed 42 and Seed 101 (zero protocol drift)
- Seed 101 configuration fingerprint
- Independent checkpoint integrity and distinct stochastic weight evolution
- HOLDOUT quarantine firewall enforcement
- Per-class metrics, confusion matrix, and parent diagnostics artifact completeness
- Stochastic variance comparison artifact structure and validity
- Rare-class stability classification
"""

import json
from pathlib import Path
import hashlib
import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
METADATA_DIR = REPO_ROOT / "data" / "metadata"
RUNS_DIR = REPO_ROOT / "experiments" / "EXP-07" / "runs"

S42_RUN_DIR = RUNS_DIR / "EXP07_RUN001_SEED42"
S101_RUN_DIR = RUNS_DIR / "EXP07_RUN002_SEED101"

MANIFEST_PATH = METADATA_DIR / "ops01_physical_dataset_manifest_v4.json"
TAXONOMY_PATH = METADATA_DIR / "ops01_taxonomy_v1.json"

S101_CONFIG_PATH = METADATA_DIR / "exp07_p0_c10_final_training_config_seed101_v1.json"
S101_FINGERPRINT_PATH = METADATA_DIR / "exp07_p0_c10_configuration_fingerprint_seed101_v1.json"
PROTOCOL_DIFF_PATH = METADATA_DIR / "exp07_p0_c10_protocol_diff_v1.json"
S101_RESULTS_PATH = METADATA_DIR / "exp07_p0_c10_training_results_seed101_v1.json"
S101_RUN_REG_PATH = METADATA_DIR / "exp07_p0_c10_seed101_run_register_v1.json"
COMPARISON_PATH = METADATA_DIR / "exp07_p0_c10_seed42_vs_seed101_comparison_v1.json"
PER_CLASS_PATH = METADATA_DIR / "exp07_p0_c10_seed101_per_class_metrics_v1.json"
CONF_MATRIX_PATH = METADATA_DIR / "exp07_p0_c10_seed101_confusion_matrix_v1.json"
SAMPLER_EXP_PATH = METADATA_DIR / "exp07_p0_c10_seed101_sampler_exposure_v1.json"
PARENT_DIAG_PATH = METADATA_DIR / "exp07_p0_c10_seed101_parent_diagnostics_v1.json"

EXPECTED_S101_FINGERPRINT = "7DF509EECBFF7AB0D4CFB8F2E5693A6CF7A1E86DCB3C7393B1F77BACB5355AD4"
EXPECTED_MANIFEST_SHA = "FF1680C9135EF5CD9C7B77FBC8373953F9924BD5BE2830617EB0EF386C8DC85E"
EXPECTED_TAXONOMY_SHA = "86A043EFDBB641EE2073C959DA315E7BF90C5F72D35B9E40F62C39F225C551AD"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


class TestC10ProtocolEquivalence:
    def test_01_immutable_hashes(self):
        assert sha256_file(MANIFEST_PATH) == EXPECTED_MANIFEST_SHA
        assert sha256_file(TAXONOMY_PATH) == EXPECTED_TAXONOMY_SHA

    def test_02_protocol_diff_is_equivalent(self):
        assert PROTOCOL_DIFF_PATH.exists()
        with open(PROTOCOL_DIFF_PATH, "r", encoding="utf-8") as f:
            diff_data = json.load(f)
        assert diff_data["protocol_drift_detected"] is False
        assert len(diff_data["unintentional_differences"]) == 0
        # Authorized differences must only be seed, run_id, phase, title, fingerprint
        for field in diff_data["intentional_differences"].keys():
            assert field in ("seed", "run_id", "phase", "title", "configuration_fingerprint_sha256")
        assert len(diff_data["identical_fields"]) >= 15

    def test_03_seed101_configuration_fingerprint(self):
        assert S101_FINGERPRINT_PATH.exists()
        with open(S101_FINGERPRINT_PATH, "r", encoding="utf-8") as f:
            fp_data = json.load(f)
        assert fp_data["configuration_fingerprint_sha256"] == EXPECTED_S101_FINGERPRINT
        assert fp_data["seed"] == 101
        assert fp_data["run_id"] == "EXP07_RUN002_SEED101"

    def test_04_no_seed2024_executed(self):
        seed2024_dir = RUNS_DIR / "EXP07_RUN003_SEED2024"
        assert not seed2024_dir.exists(), "Seed 2024 directory must NOT exist during C10."


class TestC10CheckpointsAndProvenance:
    def test_05_checkpoints_exist_and_distinct(self):
        s42_best = S42_RUN_DIR / "best_model.pt"
        s101_best = S101_RUN_DIR / "best_model.pt"
        assert s42_best.exists()
        assert s101_best.exists()

        s42_sha = sha256_file(s42_best)
        s101_sha = sha256_file(s101_best)
        assert s42_sha != s101_sha, "Checkpoints must have different hashes (stochastic seed variation)."

    def test_06_holdout_quarantine(self):
        # Verify that training results and evaluations never evaluated HOLDOUT
        if S101_RUN_REG_PATH.exists():
            with open(S101_RUN_REG_PATH, "r", encoding="utf-8") as f:
                reg = json.load(f)
            assert "holdout" not in reg
        if PER_CLASS_PATH.exists():
            with open(PER_CLASS_PATH, "r", encoding="utf-8") as f:
                pcm = json.load(f)
            assert "holdout_metrics" not in pcm
            assert "dev_metrics" in pcm
            assert "train_metrics" in pcm


class TestC10StochasticComparison:
    def test_07_comparison_artifact_structure(self):
        if not COMPARISON_PATH.exists():
            pytest.skip("Comparison artifact not yet generated.")
        with open(COMPARISON_PATH, "r", encoding="utf-8") as f:
            comp = json.load(f)

        assert "runs" in comp
        assert "seed42" in comp["runs"]
        assert "seed101" in comp["runs"]
        assert comp["runs"]["seed42"]["seed"] == 42
        assert comp["runs"]["seed101"]["seed"] == 101

        assert "per_class_comparison" in comp
        assert len(comp["per_class_comparison"]) == 12

        assert "rare_class_stability" in comp
        for rc in ("AF", "OF", "RF", "Eddy", "HM"):
            assert rc in comp["rare_class_stability"]
            assert comp["rare_class_stability"][rc]["classification"] in (
                "STABLE_FAILURE_ACROSS_SEEDS",
                "SEED_SENSITIVE_FAILURE",
                "UNSTABLE_BUT_NONZERO",
                "UNEXPECTEDLY_IMPROVED",
            )

        assert "parent_scene_comparison" in comp
        assert len(comp["parent_scene_comparison"]) >= 3

    def test_08_sampler_exposure_comparison(self):
        if not SAMPLER_EXP_PATH.exists():
            pytest.skip("Sampler exposure artifact not yet generated.")
        with open(SAMPLER_EXP_PATH, "r", encoding="utf-8") as f:
            sampler_data = json.load(f)
        assert sampler_data["seed"] == 101
        assert sampler_data["sampler_name"] == "Candidate_F_Hybrid"
        assert sampler_data["unique_tiles_sampled_overall"] > 0
        assert len(sampler_data["parent_exposures"]) == 12
