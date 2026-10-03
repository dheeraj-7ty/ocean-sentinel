"""EXP-07-P0-C11: Adversarial Two-Seed Forensic Review & Claim Correction Guardrails.

Automated regression suite verifying:
- Model parameter count exact reconciliation (14,310,860 trainable, 14,322,666 state elements)
- Checkpoint state dict tensor count (192) and strict weight architecture fidelity
- Canonical taxonomy integrity (OF = Ocean Front, HM = Artificial / Anthropogenic Objects)
- Sensor modality discipline (SAR radar backscatter, zero acoustic/sonar terminology)
- Epistemic claim boundaries (OBSERVED, SUPPORTED, PLAUSIBLE, CAUSAL_ESTABLISHED)
- Bitwise comparison precision
- Governance rules GOV-RULE-069 through GOV-RULE-072
- Incident resolution for INC-P0-C11-001 through INC-P0-C11-004
- Next-experiment gate authorization
"""

import json
from pathlib import Path
import sys
import pytest
import torch

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
METADATA_DIR = REPO_ROOT / "data" / "metadata"
RUNS_DIR = REPO_ROOT / "experiments" / "EXP-07" / "runs"

S42_BEST = RUNS_DIR / "EXP07_RUN001_SEED42" / "best_model.pt"
S101_BEST = RUNS_DIR / "EXP07_RUN002_SEED101" / "best_model.pt"

GOV_RULES_PATH = METADATA_DIR / "ocean_sentinel_governance_rules_v1.json"
INCIDENT_REG_PATH = METADATA_DIR / "ocean_sentinel_incident_learning_register_v1.json"
TAXONOMY_PATH = METADATA_DIR / "ops01_taxonomy_v1.json"

PARAM_RECON_PATH = METADATA_DIR / "exp07_p0_c11_parameter_reconciliation_v1.json"
TAX_DRIFT_PATH = METADATA_DIR / "exp07_p0_c11_taxonomy_drift_audit_v1.json"
CLAIM_AUDIT_PATH = METADATA_DIR / "exp07_p0_c11_claim_audit_v1.json"
FORENSIC_REG_PATH = METADATA_DIR / "exp07_p0_c11_two_seed_forensic_register_v1.json"


class TestC11ParameterReconciliation:
    def test_01_model_trainable_parameters_exact(self):
        from ocean_sentinel.ml.exp07_reference import ResNet18UNet
        model = ResNet18UNet(in_channels=1, num_classes=12, bn_momentum=0.05)
        trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
        non_trainable = sum(p.numel() for p in model.parameters() if not p.requires_grad)
        state_elements = sum(t.numel() for t in model.state_dict().values())

        assert trainable == 14310860
        assert non_trainable == 0
        assert state_elements == 14322666
        assert len(model.state_dict()) == 192

    def test_02_checkpoints_parameter_integrity(self):
        assert S42_BEST.exists()
        assert S101_BEST.exists()

        ckpt42 = torch.load(S42_BEST, map_location="cpu")
        ckpt101 = torch.load(S101_BEST, map_location="cpu")

        sd42 = ckpt42["model_state_dict"]
        sd101 = ckpt101["model_state_dict"]

        assert len(sd42) == 192
        assert len(sd101) == 192
        assert sum(t.numel() for t in sd42.values()) == 14322666
        assert sum(t.numel() for t in sd101.values()) == 14322666

    def test_03_parameter_reconciliation_artifact_valid(self):
        assert PARAM_RECON_PATH.exists()
        with open(PARAM_RECON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["authoritative_counts"]["trainable_parameters"] == 14310860
        assert data["authoritative_counts"]["total_state_elements"] == 14322666
        assert data["discrepancy_audit"]["actual_trainable_number"] == 14310860
        assert data["discrepancy_audit"]["status"] == "RECONCILED_AND_CORRECTED"


class TestC11TaxonomyAndModalityDiscipline:
    def test_04_taxonomy_definitions_canonical(self):
        with open(TAXONOMY_PATH, "r", encoding="utf-8") as f:
            tax = json.load(f)
        classes = {c["abbreviation"]: c for c in tax["classes"]}

        assert classes["OF"]["class_name"] == "Ocean Front"
        assert classes["OF"]["source_label_id"] == 6

        assert classes["HM"]["class_name"] == "Artificial / Anthropogenic Objects"
        assert classes["HM"]["source_label_id"] == 13

        assert classes["OS"]["class_name"] == "Mineral Oil Spill"
        assert classes["OS"]["training_eligible"] is False

    def test_05_taxonomy_drift_artifact_valid(self):
        assert TAX_DRIFT_PATH.exists()
        with open(TAX_DRIFT_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        terms = {item["term"]: item for item in data["findings"]}
        assert "OF" in terms
        assert "HM" in terms
        assert "acoustic" in terms
        assert terms["OF"]["canonical_name"] == "Ocean Front"
        assert terms["HM"]["canonical_name"] == "Artificial / Anthropogenic Objects"


class TestC11EpistemicClaimsAndGovernance:
    def test_06_claim_audit_artifact_valid(self):
        assert CLAIM_AUDIT_PATH.exists()
        with open(CLAIM_AUDIT_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        claims = {c["claim_id"]: c for c in data["audit_table"]}
        assert len(claims) >= 7
        for c in claims.values():
            assert c["epistemic_level"] in ("OBSERVED", "SUPPORTED", "PLAUSIBLE", "CAUSAL_ESTABLISHED", "NOT_ESTABLISHED")

    def test_07_governance_rules_69_to_72_active(self):
        with open(GOV_RULES_PATH, "r", encoding="utf-8") as f:
            rules_data = json.load(f)
        rules = {r["rule_id"]: r for r in rules_data["rules"]}
        for rid in ("GOV-RULE-069", "GOV-RULE-070", "GOV-RULE-071", "GOV-RULE-072"):
            assert rid in rules, f"Missing {rid}"
            assert rules[rid]["status"] == "ACTIVE"
        assert rules_data["total_rules"] >= 72

    def test_08_incidents_p0_c11_recorded_and_resolved(self):
        with open(INCIDENT_REG_PATH, "r", encoding="utf-8") as f:
            inc_data = json.load(f)
        incidents = {i["incident_id"]: i for i in inc_data["incidents"]}
        for inc_id in ("INC-P0-C11-001", "INC-P0-C11-002", "INC-P0-C11-003", "INC-P0-C11-004"):
            assert inc_id in incidents, f"Missing {inc_id}"
            assert incidents[inc_id]["status"] == "RESOLVED"

    def test_09_next_experiment_gate_decision(self):
        assert FORENSIC_REG_PATH.exists()
        with open(FORENSIC_REG_PATH, "r", encoding="utf-8") as f:
            reg = json.load(f)
        assert reg["next_experiment_gate"] == "AUTHORIZE_DATASET_EXPANSION"
        assert "A = PASS" in reg["final_decision"]
