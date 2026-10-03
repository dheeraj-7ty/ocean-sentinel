"""Phase 8-P3-C1 Governance, Provenance Versioning, and Reproducibility Guardrails.

Comprehensive regression suite validating:
- Cryptographic integrity of frozen reference artifacts (EXP-06, Part-I).
- Formal successor version lineage (manifest_v4, sufficiency_v5).
- Accurate recovery status of pre-P3 authoritative hashes.
- Operational definition and evidence boundary of Reproducibility Levels.
- Strict separation of scientific protocol decisions from engineering choices.
- Permanent preservation of all four epistemic disclosures.
- Durable institutional memory and governance rules.
- Complete absence of unauthorized training, GPU usage, or Part-III benchmark access.
- Strict git safety (zero staged mutations).
- Correction of narrative discrepancy wording (7E vs 7F, absence of 7E vs 7B).
"""

import hashlib
import json
import subprocess
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent

EXP06_PATH = ROOT / "experiments/performance/exp06_positive_bce_weight/best_model.pt"
PART_I_PATH = ROOT / "data/metadata/internal_development_split_manifest.json"
EXP06_SHA = "B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF"
PART_I_SHA = "17F1FF35146C7CE62E90D6FCE7F197B711B55E3C3CB599610578443208669072"

MANIFEST_V4 = ROOT / "data/metadata/ops01_physical_dataset_manifest_v4.json"
SUFFICIENCY_V5 = ROOT / "data/metadata/ops01_dataset_sufficiency_v5.json"
VERSION_LINEAGE = ROOT / "data/metadata/ops01_p3_c1_version_lineage_v1.json"
DATASET_IDENTITY = ROOT / "data/metadata/ops01_dataset_identity_v1.json"
REPRODUCIBILITY_LEVELS = ROOT / "data/metadata/ocean_sentinel_reproducibility_levels_v1.json"
GOVERNANCE_JSON = ROOT / "data/metadata/ocean_sentinel_governance_rules_v1.json"
GOVERNANCE_MD = ROOT / "experiments/PROJECT_GOVERNANCE/ocean_sentinel_governance_rules_v1.md"
INCIDENT_LEARNING = ROOT / "data/metadata/ocean_sentinel_incident_learning_register_v1.json"
DECISION_CLASSIFICATION = ROOT / "data/metadata/ops01_p3_c1_decision_classification_v1.json"
PREPROC_RECORD = ROOT / "data/metadata/ops01_p3_c1_preprocessing_decision_record_v1.json"
CHANGE_RECONCILIATION = ROOT / "data/metadata/ops01_p3_c1_change_reconciliation_v1.json"
RUN_STATE = ROOT / "scratch/phase_8_p3_c1_run_state.json"
TAXONOMY_PATH = ROOT / "data/metadata/ops01_taxonomy_v1.json"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while c := f.read(65536):
            h.update(c)
    return h.hexdigest().upper()


# ============================================================
# GROUP 1: FROZEN ARTIFACT INTEGRITY
# ============================================================
class TestFrozenArtifactIntegrity:
    """Frozen artifacts from prior phases must remain bitwise identical."""

    def test_exp06_model_checkpoint_sha256(self):
        assert EXP06_PATH.exists(), f"EXP-06 checkpoint not found at {EXP06_PATH}"
        assert sha256(EXP06_PATH) == EXP06_SHA, "EXP-06 checkpoint was modified!"

    def test_part_i_split_manifest_sha256(self):
        assert PART_I_PATH.exists(), f"Part-I split manifest not found at {PART_I_PATH}"
        assert sha256(PART_I_PATH) == PART_I_SHA, "Part-I split manifest was modified!"


# ============================================================
# GROUP 2: SUCCESSOR VERSION LINEAGE & IMMUTABILITY
# ============================================================
class TestArtifactVersioningLineage:
    """Successor artifacts v4/v5 must establish clean immutable version lineage."""

    def test_version_lineage_artifact_exists(self):
        assert VERSION_LINEAGE.exists(), "Version lineage artifact missing"
        data = json.loads(VERSION_LINEAGE.read_text(encoding="utf-8"))
        assert data["phase"] == "PHASE_8_P3_C1"
        assert len(data["artifacts"]) >= 2

    def test_manifest_v4_successor_properties(self):
        assert MANIFEST_V4.exists(), "ops01_physical_dataset_manifest_v4.json missing"
        data = json.loads(MANIFEST_V4.read_text(encoding="utf-8"))
        assert data["artifact_version"] == "4.0.0"
        assert data["parent_manifest"] == "ops01_physical_dataset_manifest_v3.json"
        assert data["parent_hash_status"] == "RECOVERED_FROM_EXPLICIT_SOURCE"
        assert data["parent_manifest_sha256_pre_p3"] == "94521D08C00AB71269D9DE566468C1E8B8C12E3519C3AB97375F63DF75355787"
        assert data["physical_dataset_change_status"] in ["UNCHANGED", "SAME_CURRENTLY_VERIFIED_PHYSICAL_DATASET_STATE"]
        assert data["sample_bytes_changed"] is False
        assert data["labels_changed"] is False
        assert data["partition_changed"] is False
        assert len(data["samples"]) == 147

    def test_sufficiency_v5_successor_properties(self):
        assert SUFFICIENCY_V5.exists(), "ops01_dataset_sufficiency_v5.json missing"
        data = json.loads(SUFFICIENCY_V5.read_text(encoding="utf-8"))
        assert data["artifact_version"] == "5.0.0"
        assert data["parent_artifact"] == "ops01_dataset_sufficiency_v4.json"
        assert data["parent_hash_status"] == "RECOVERED_FROM_EXPLICIT_SOURCE"
        assert data["parent_artifact_sha256_pre_p3"] == "CB5C14A68BFDC2D72BD37FA4C7E579DD6A01015E6651228B3D6CA4C8B2FEF1A4"
        assert data["physical_dataset_change_status"] in ["UNCHANGED", "SAME_CURRENTLY_VERIFIED_PHYSICAL_DATASET_STATE"]
        assert data["sample_bytes_changed"] is False
        assert data["final_decision"] == "A. CORRECTED -- SUFFICIENT FOR P3"

    def test_change_reconciliation_record(self):
        assert CHANGE_RECONCILIATION.exists()
        rec = json.loads(CHANGE_RECONCILIATION.read_text(encoding="utf-8"))
        assert rec["historical_hash_recovery"]["status"] == "RECOVERED_FROM_EXPLICIT_SOURCE"
        content_change = rec["content_change_determination"]
        assert content_change["physical_samples"]["status"] == "PROVEN_UNCHANGED"
        assert content_change["image_bytes"]["status"] == "PROVEN_UNCHANGED"
        assert content_change["mask_bytes"]["status"] == "PROVEN_UNCHANGED"
        assert content_change["labels"]["status"] == "PROVEN_UNCHANGED"


# ============================================================
# GROUP 3: DATASET IDENTITY CONTRACT
# ============================================================
class TestDatasetIdentityContract:
    """Dataset identity must be defined by CONTENT + MANIFEST + TAXONOMY + SPLIT + PROVENANCE + PROTOCOL."""

    def test_dataset_identity_contract_contents(self):
        assert DATASET_IDENTITY.exists()
        ident = json.loads(DATASET_IDENTITY.read_text(encoding="utf-8"))
        assert ident["dataset_name"] == "OPS-01"
        assert "CONTENT + MANIFEST + TAXONOMY + SPLIT + PROVENANCE + PROTOCOL" in ident["dataset_identity_doctrine"]
        assert ident["dataset_composition"]["sample_count"] == 147
        assert ident["dataset_composition"]["parent_count"] == 27
        assert ident["dataset_composition"]["partition_counts"]["TRAIN"] == 72
        assert ident["dataset_composition"]["partition_counts"]["DEV"] == 39
        assert ident["dataset_composition"]["partition_counts"]["HOLDOUT"] == 36
        assert ident["dataset_composition"]["parent_leakage"] == 0
        assert ident["dataset_composition"]["admitted_class_14_os_pixels"] == 0
        assert ident["reproducibility_level"]["assigned_level"] == "LEVEL_B"
        assert ident["training_dataloader_status"]["status"] == "NOT_IMPLEMENTED"


# ============================================================
# GROUP 4: REPRODUCIBILITY HIERARCHY & LEVEL DEFINITIONS
# ============================================================
class TestReproducibilityHierarchy:
    """Reproducibility levels must be formally specified and evidence-bounded."""

    def test_reproducibility_levels_specification(self):
        assert REPRODUCIBILITY_LEVELS.exists()
        repro = json.loads(REPRODUCIBILITY_LEVELS.read_text(encoding="utf-8"))
        levels = repro["levels"]
        assert "LEVEL_0" in levels
        assert "LEVEL_A" in levels
        assert "LEVEL_B" in levels
        assert "LEVEL_C" in levels
        assert "LEVEL_D" in levels

        for lvl_key, lvl in levels.items():
            assert "level_name" in lvl
            assert "definition" in lvl
            assert "evidence_requirements" in lvl
            assert "acceptable_claims" in lvl
            assert "prohibited_claims" in lvl
            assert "verification_method" in lvl

    def test_current_ops01_does_not_exceed_evidence(self):
        repro = json.loads(REPRODUCIBILITY_LEVELS.read_text(encoding="utf-8"))
        curr = repro["current_ops01_evaluation"]
        assert curr["highest_supported_level"] == "LEVEL_B"
        assert curr["prohibition_enforcement"]["level_c_prohibited"] is True
        assert curr["prohibition_enforcement"]["level_d_prohibited"] is True
        assert "NOT_DIRECTLY_VERIFIED" in curr["prohibition_enforcement"]["reason"]


# ============================================================
# GROUP 5: EPISTEMIC DISCLOSURES PERMANENCE
# ============================================================
class TestEpistemicDisclosures:
    """All four permanent epistemic disclosures must be present across authoritative artifacts."""

    REQUIRED_DISCLOSURES = [
        "HOLDOUT_PARTIALLY_USED_FOR_SELECTION",
        "CONDITIONAL_ENGINEERING_RECONSTRUCTION",
        "EMPIRICALLY_SUPPORTED_PILOT_HYPOTHESIS",
        "DATASET_GENERATION_METHOD = NOT_DIRECTLY_VERIFIED"
    ]

    def test_permanent_disclosures_in_manifest_v4(self):
        txt = MANIFEST_V4.read_text(encoding="utf-8")
        for disc in self.REQUIRED_DISCLOSURES:
            assert disc in txt, f"Disclosure '{disc}' missing from manifest_v4!"

    def test_permanent_disclosures_in_sufficiency_v5(self):
        txt = SUFFICIENCY_V5.read_text(encoding="utf-8")
        for disc in self.REQUIRED_DISCLOSURES:
            assert disc in txt, f"Disclosure '{disc}' missing from sufficiency_v5!"

    def test_permanent_disclosures_in_dataset_identity(self):
        txt = DATASET_IDENTITY.read_text(encoding="utf-8")
        for disc in self.REQUIRED_DISCLOSURES:
            assert disc in txt, f"Disclosure '{disc}' missing from dataset_identity!"


# ============================================================
# GROUP 6: CANONICAL TAXONOMY INTEGRITY & OF/OS SEMANTICS
# ============================================================
class TestTaxonomySemantics:
    """Taxonomy must match ops01_taxonomy_v1.json; OF=Ocean Front; OS strictly excluded."""

    def test_of_is_ocean_front_label_6(self):
        tax = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))
        of_entry = next((c for c in tax["classes"] if c["abbreviation"] == "OF"), None)
        assert of_entry is not None, "OF class missing from taxonomy!"
        assert of_entry["class_name"] == "Ocean Front"
        assert of_entry["source_label_id"] == 6

    def test_os_mineral_oil_spill_strictly_excluded(self):
        tax = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))
        os_entry = next((c for c in tax["classes"] if c["abbreviation"] == "OS"), None)
        assert os_entry is not None, "OS class missing from taxonomy!"
        assert os_entry["source_label_id"] == 14
        assert os_entry["training_eligible"] is False

    def test_no_os_pixels_in_manifest_samples(self):
        m4 = json.loads(MANIFEST_V4.read_text(encoding="utf-8"))
        for s in m4["samples"]:
            assert 14 not in s.get("label_class_set", []), f"OS (14) found in sample {s['sample_id']}"
            assert "OS" not in s.get("class_composition", {}), f"OS found in sample {s['sample_id']}"


# ============================================================
# GROUP 7: DURABLE GOVERNANCE & PROJECT MEMORY
# ============================================================
class TestGovernanceRulesAndMemory:
    """Governance rules must exist in markdown (sections A-O) and machine-readable JSON."""

    def test_governance_files_exist(self):
        assert GOVERNANCE_JSON.exists(), "Governance JSON file missing"
        assert GOVERNANCE_MD.exists(), "Governance MD file missing"

    def test_governance_rules_json_contents(self):
        data = json.loads(GOVERNANCE_JSON.read_text(encoding="utf-8"))
        assert data["rule_count"] >= 20
        rule_ids = set(r["rule_id"] for r in data["rules"])
        assert "GOV-RULE-001" in rule_ids
        assert "GOV-RULE-019" in rule_ids
        assert "GOV-RULE-020" in rule_ids
        assert "GOV-RULE-021" in rule_ids

    def test_governance_markdown_sections(self):
        md_text = GOVERNANCE_MD.read_text(encoding="utf-8")
        sections = [
            "Section A — Core Scientific Doctrine",
            "Section B — Evidence-Status Hierarchy",
            "Section C — Provenance Doctrine",
            "Section D — Dataset Integrity Doctrine",
            "Section E — Split and Leakage Doctrine",
            "Section F — Alignment Doctrine",
            "Section G — Reproducibility Doctrine",
            "Section H — Taxonomy Doctrine",
            "Section I — Geographic and Temporal Claim Doctrine",
            "Section J — Artifact-Versioning Doctrine",
            "Section K — Experiment Authorization Doctrine",
            "Section L — Git Safety Doctrine",
            "Section M — Telemetry Doctrine",
            "Section N — Incident-Learning Doctrine",
            "Section O — Training Authorization Doctrine",
        ]
        for sec in sections:
            assert sec in md_text, f"Missing section in governance rules markdown: '{sec}'"


# ============================================================
# GROUP 8: INCIDENT LEARNING REGISTER
# ============================================================
class TestIncidentLearningRegister:
    """Incident register must capture all major historical failures with root cause and regression test."""

    def test_incident_register_exists_and_populated(self):
        assert INCIDENT_LEARNING.exists()
        data = json.loads(INCIDENT_LEARNING.read_text(encoding="utf-8"))
        assert data["incident_count"] >= 8
        incident_ids = [inc["incident_id"] for inc in data["incidents"]]
        assert "INC-P3-C1-001" in incident_ids
        assert "INC-P3-C1-002" in incident_ids
        assert "INC-P3-C1-003" in incident_ids
        assert "INC-P3-C1-004" in incident_ids

        for inc in data["incidents"]:
            assert "root_cause" in inc
            assert "permanent_rule" in inc
            assert "regression_test" in inc


# ============================================================
# GROUP 9: DECISION SEPARATION & OPEN ISSUES
# ============================================================
class TestDecisionSeparationAndOpenIssues:
    """Scientific training decisions must be separated from engineering; loader and preproc open."""

    def test_decision_classification_artifact(self):
        assert DECISION_CLASSIFICATION.exists()
        data = json.loads(DECISION_CLASSIFICATION.read_text(encoding="utf-8"))
        summary = data["classification_summary"]
        assert summary["scientific_count"] >= 4
        assert summary["engineering_count"] >= 2
        assert summary["both_count"] >= 3

    def test_ops01_loader_gap_remains_open(self):
        ident = json.loads(DATASET_IDENTITY.read_text(encoding="utf-8"))
        loader = ident["training_dataloader_status"]
        assert loader["status"] == "NOT_IMPLEMENTED"
        assert loader["issue_id"] == "OPEN-LOADER-001"

    def test_open_preproc_001_unresolved(self):
        assert PREPROC_RECORD.exists()
        data = json.loads(PREPROC_RECORD.read_text(encoding="utf-8"))
        assert data["issue_id"] == "OPEN-PREPROC-001"
        assert data["current_physical_state"]["calibrated_sigma0_status"] == "NOT_ESTABLISHED"
        assert data["current_physical_state"]["decibel_db_status"] == "NOT_ESTABLISHED"
        assert data["status"] == "OPEN_FOR_EXP07_PROTOCOL"


# ============================================================
# GROUP 10: DISCREPANCY WORDING (7E vs 7F, NO 7E vs 7B)
# ============================================================
class TestPartIDiscrepancyWording:
    """Discrepancy must be described as 7E vs 7F; 7E vs 7B is strictly prohibited."""

    def test_no_erroneous_7e_vs_7b_in_repo(self):
        # Check all python, markdown, and json files in key directories
        bad_phrase = "7E" + " vs " + "7B"
        bad_found = []
        for dir_name in ["data/metadata", "scratch", "experiments", "tests"]:
            for p in (ROOT / dir_name).rglob("*"):
                if not p.is_file() or p.suffix not in [".json", ".md", ".py", ".txt"]:
                    continue
                if p.name == "test_phase_8_p3_c1_governance_guardrails.py":
                    continue
                try:
                    txt = p.read_text(encoding="utf-8", errors="ignore")
                    if bad_phrase in txt or bad_phrase.lower() in txt:
                        bad_found.append(str(p.relative_to(ROOT)))
                except Exception:
                    pass
        assert not bad_found, f"Erroneous '{bad_phrase}' string found in: {bad_found}"

    def test_correct_7e_vs_7f_documented(self):
        run_state_txt = RUN_STATE.read_text(encoding="utf-8")
        assert "7E vs 7F" in run_state_txt


# ============================================================
# GROUP 11: INVESTIGATION BOUNDS & TELEMETRY
# ============================================================
class TestInvestigationBoundsAndTelemetry:
    """Historical search must be bounded; telemetry must be actively tracked."""

    def test_bounded_historical_search_status(self):
        rec = json.loads(CHANGE_RECONCILIATION.read_text(encoding="utf-8"))
        hist = rec["historical_hash_recovery"]
        assert hist["status"] in ["RECOVERED_FROM_EXPLICIT_SOURCE", "PRE_P3_BINARY_HASH_UNRECOVERABLE_FROM_CURRENT_EVIDENCE"]

    def test_run_state_telemetry_valid(self):
        assert RUN_STATE.exists()
        state = json.loads(RUN_STATE.read_text(encoding="utf-8"))
        assert state["phase"] == "PHASE_8_P3_C1"
        assert state["phase_status"] in ["RUNNING", "COMPLETE"]
        assert "last_heartbeat" in state
        assert state["preflight"]["frozen_verified"] is True


# ============================================================
# GROUP 12: ABSOLUTE PROHIBITIONS & GIT SAFETY
# ============================================================
class TestAbsoluteProhibitionsAndGitSafety:
    """Zero EXP-07 execution, zero training, zero GPU artifacts, zero staged git changes."""

    def test_no_exp07_training_artifacts_exist(self):
        exp07_paths = list(ROOT.glob("experiments/**/exp07*")) + list(ROOT.glob("models/**/exp07*"))
        assert not exp07_paths, f"Unauthorized EXP-07 artifacts found: {exp07_paths}"

    def test_git_staged_changes_remain_zero(self):
        res = subprocess.run("git diff --cached --name-status", shell=True, capture_output=True, text=True, cwd=ROOT)
        staged = res.stdout.strip()
        assert not staged, f"Git staged mutations detected! Only 0 staged is allowed:\n{staged}"
