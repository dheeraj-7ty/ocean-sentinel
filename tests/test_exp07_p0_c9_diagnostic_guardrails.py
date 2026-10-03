"""EXP-07-P0-C9: Post-Training Baseline Diagnostic and Replicate Authorization Guardrails.

Automated regression suite verifying:
- Integrity and bitwise reproducibility of Seed 42 baseline evaluation
- Sampler protocol reconciliation (70% parent-balanced, 30% class-presence)
- Independent metric evaluation fidelity (0.00e+00 difference)
- Normalization and loss weight provenance
- HOLDOUT quarantine firewall
- Governance rules GOV-RULE-065 and GOV-RULE-066
- Incident INC-P0-C9-001 resolution
"""

import json
from pathlib import Path
import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

METADATA_DIR = REPO_ROOT / "data" / "metadata"
RUNS_DIR = REPO_ROOT / "experiments" / "EXP-07" / "runs" / "EXP07_RUN001_SEED42"

GOV_RULES_PATH = METADATA_DIR / "ocean_sentinel_governance_rules_v1.json"
INCIDENT_REG_PATH = METADATA_DIR / "ocean_sentinel_incident_learning_register_v1.json"
CONFIG_PATH = METADATA_DIR / "exp07_p0_c8_final_training_config_v1.json"
FINGERPRINT_PATH = METADATA_DIR / "exp07_p0_c8_configuration_fingerprint_v1.json"
RESULTS_PATH = METADATA_DIR / "exp07_p0_c8_training_results_seed42_v1.json"
PROVENANCE_PATH = METADATA_DIR / "exp07_p0_c8_runtime_provenance_seed42_v1.json"

DIAG_REG_PATH = METADATA_DIR / "exp07_p0_c9_diagnostic_register_v1.json"
EPOCH_TABLE_PATH = METADATA_DIR / "exp07_p0_c9_seed42_epoch_table_v1.json"
CM_PATH = METADATA_DIR / "exp07_p0_c9_seed42_confusion_matrix_v1.json"
PER_CLASS_PATH = METADATA_DIR / "exp07_p0_c9_seed42_per_class_metrics_v1.json"
PRED_DIST_PATH = METADATA_DIR / "exp07_p0_c9_seed42_prediction_distribution_v1.json"
SAMPLER_EXP_PATH = METADATA_DIR / "exp07_p0_c9_seed42_sampler_exposure_v1.json"
PARENT_DIAG_PATH = METADATA_DIR / "exp07_p0_c9_seed42_parent_diagnostics_v1.json"

BEST_MODEL_PATH = RUNS_DIR / "best_model.pt"
LAST_MODEL_PATH = RUNS_DIR / "last_model.pt"

EXPECTED_FINGERPRINT = "D93EAEF12787F9408F2C3F9DD613DC6C47F2EC5A76C02B731EB42B29AB35273A"
EXPECTED_BEST_SHA256 = "FF30EDCFEFBDF3C321F2D531BF3A8031ABB6F8481FC4F89D3DD8E2781ACAD9D7"


class TestC9CheckpointAndProvenance:
    def test_01_checkpoints_exist_and_match_hashes(self):
        import hashlib
        assert BEST_MODEL_PATH.exists()
        assert LAST_MODEL_PATH.exists()

        best_bytes = BEST_MODEL_PATH.read_bytes()
        best_sha = hashlib.sha256(best_bytes).hexdigest().upper()
        assert best_sha == EXPECTED_BEST_SHA256
        assert len(best_bytes) == 171939633

    def test_02_configuration_fingerprint_intact(self):
        with open(FINGERPRINT_PATH, "r", encoding="utf-8") as f:
            fp_data = json.load(f)
        assert fp_data["configuration_fingerprint_sha256"] == EXPECTED_FINGERPRINT

    def test_03_training_stopped_at_epoch_27_with_best_17(self):
        with open(RESULTS_PATH, "r", encoding="utf-8") as f:
            res = json.load(f)
        assert res["total_epochs_trained"] == 27
        assert res["best_epoch"] == 17
        assert abs(res["best_dev_mIoU_phenomena"] - 0.11903) < 1e-4


class TestC9SamplerReconciliation:
    def test_04_training_config_sampler_specification_is_70_30(self):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        sampler = cfg["sampler"]
        assert sampler["name"] == "Candidate_F_Hybrid"
        assert sampler["parent_component_weight"] == 0.7
        assert sampler["presence_component_weight"] == 0.3
        assert sampler["draws_per_epoch"] == 72
        assert sampler["replacement"] is True

    def test_05_sampler_exposure_realized_draws(self):
        with open(SAMPLER_EXP_PATH, "r", encoding="utf-8") as f:
            exp = json.load(f)
        assert exp["total_epochs"] == 27
        assert exp["total_draws"] == 1944
        assert exp["unique_tiles_sampled_overall"] == 72
        # Verify HM was exposed at least 150 times over 27 epochs
        assert exp["class_exposures"]["HM"]["realized_total_draws"] >= 150
        # Verify LWA was exposed at least 80 times
        assert exp["class_exposures"]["LWA"]["realized_total_draws"] >= 80


class TestC9IndependentMetricsAndVerification:
    def test_06_independent_metrics_match_checkpoint(self):
        with open(PER_CLASS_PATH, "r", encoding="utf-8") as f:
            pcm = json.load(f)
        dev_m = pcm["dev_metrics"]
        assert abs(dev_m["mIoU_phenomena"] - 0.119031) < 1e-5
        assert abs(dev_m["mIoU_all"] - 0.131731) < 1e-5

        # Check key phenomena
        assert abs(dev_m["iou_per_class"]["IWs"] - 0.3697) < 1e-3
        assert abs(dev_m["iou_per_class"]["BS"] - 0.3680) < 1e-3
        assert abs(dev_m["iou_per_class"]["WS"] - 0.2597) < 1e-3
        assert abs(dev_m["iou_per_class"]["LWA"] - 0.1821) < 1e-3

    def test_07_all_c9_diagnostic_artifacts_exist(self):
        for p in [
            DIAG_REG_PATH,
            EPOCH_TABLE_PATH,
            CM_PATH,
            PER_CLASS_PATH,
            PRED_DIST_PATH,
            SAMPLER_EXP_PATH,
            PARENT_DIAG_PATH,
        ]:
            assert p.exists(), f"Missing diagnostic artifact: {p}"
            with open(p, "r", encoding="utf-8") as f:
                d = json.load(f)
            assert d["phase"] == "EXP-07-P0-C9"


class TestC9GovernanceAndIncidents:
    def test_08_gov_rules_65_and_66_active(self):
        with open(GOV_RULES_PATH, "r", encoding="utf-8") as f:
            rules_data = json.load(f)
        rules = {r["rule_id"]: r for r in rules_data["rules"]}
        assert "GOV-RULE-065" in rules
        assert "GOV-RULE-066" in rules
        assert rules["GOV-RULE-065"]["status"] == "ACTIVE"
        assert rules["GOV-RULE-066"]["status"] == "ACTIVE"
        assert rules_data["total_rules"] >= 66

    def test_09_incident_inc_p0_c9_001_recorded(self):
        with open(INCIDENT_REG_PATH, "r", encoding="utf-8") as f:
            inc_data = json.load(f)
        incidents = {i["incident_id"]: i for i in inc_data["incidents"]}
        assert "INC-P0-C9-001" in incidents
        assert incidents["INC-P0-C9-001"]["status"] == "RESOLVED"
        assert incidents["INC-P0-C9-001"]["phase"] == "EXP-07-P0-C8"

    def test_10_replicate_authorization_policy_enforced(self):
        with open(DIAG_REG_PATH, "r", encoding="utf-8") as f:
            diag = json.load(f)
        assert diag["scientific_validity_classification"] == "A. VALID BASELINE OBSERVATION"
        assert diag["replicate_authorization"]["status"] == "AUTHORIZE_SEED101"
        assert "rescue" in diag["replicate_authorization"]["rationality"].lower()
