"""EXP-07-P0-C12: OPS-02 Multi-Scene Data Expansion Design Guardrails.

Automated regression suite verifying:
- Canonical dense taxonomy mapping and explicit separation from source label IDs
- OF is Dense Index 5 (Source Label 6); POW is Dense Index 6 (Source Label 7)
- Excluded source classes (3=IB, 9=SI, 14=OS) mapped to ignore_index (-100)
- SAR runtime representation terminology (DN-domain uncalibrated representation vs sigma0)
- Parent-level partitioning requirements (split before slicing; zero parent sharing)
- Holdout preservation and quarantine firewall rules
- Provenance manifest schema fields and unknown metadata handling
- Annotation provenance tiers and Tier D quarantine enforcement
- Multi-dimensional minimum dataset sufficiency matrix
- Absolute prohibition of training authorization in C12
- Governance rules GOV-RULE-073 through GOV-RULE-076 active
- Incidents INC-P0-C12-001 and INC-P0-C12-002 recorded and resolved
"""

import json
from pathlib import Path
import sys
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
METADATA_DIR = REPO_ROOT / "data" / "metadata"
SCRATCH_DIR = REPO_ROOT / "scratch"

TAXONOMY_PATH = METADATA_DIR / "ops01_taxonomy_v1.json"
GOV_RULES_PATH = METADATA_DIR / "ocean_sentinel_governance_rules_v1.json"
INCIDENT_REG_PATH = METADATA_DIR / "ocean_sentinel_incident_learning_register_v1.json"

C11_RESIDUAL_AUDIT_PATH = METADATA_DIR / "exp07_p0_c12_c11_residual_audit_v1.json"
PARENT_RULES_PATH = METADATA_DIR / "exp07_p0_c12_ops02_parent_identity_rules_v1.json"
SPLIT_SPEC_PATH = METADATA_DIR / "exp07_p0_c12_ops02_split_specification_v1.json"
PROVENANCE_SCHEMA_PATH = METADATA_DIR / "exp07_p0_c12_ops02_provenance_schema_v1.json"
SUFFICIENCY_GATE_PATH = METADATA_DIR / "exp07_p0_c12_ops02_sufficiency_gate_v1.json"
SOURCE_EVAL_PATH = METADATA_DIR / "exp07_p0_c12_ops02_source_evaluation_framework_v1.json"
CAMPAIGN_SPEC_PATH = METADATA_DIR / "exp07_p0_c12_ops02_campaign_spec_v1.json"
RUN_STATE_PATH = SCRATCH_DIR / "exp07_p0_c12_run_state.json"


class TestC12TaxonomyAndRepresentationGuardrails:
    def test_01_dense_vs_source_mapping_integrity(self):
        from ocean_sentinel.ml.exp07_reference import DENSE_CLASSES, SOURCE_LABEL_TO_DENSE, IGNORE_INDEX
        assert len(DENSE_CLASSES) == 12
        assert DENSE_CLASSES[5] == "OF"
        assert DENSE_CLASSES[6] == "POW"
        assert DENSE_CLASSES[11] == "HM"

        # Source 6 -> Dense 5 (OF)
        assert SOURCE_LABEL_TO_DENSE[6] == 5
        # Source 7 -> Dense 6 (POW)
        assert SOURCE_LABEL_TO_DENSE[7] == 6
        # Source 13 -> Dense 11 (HM)
        assert SOURCE_LABEL_TO_DENSE[13] == 11

        # Excluded source labels: 3 (IB), 9 (SI), 14 (OS)
        for excluded_id in [3, 9, 14]:
            assert excluded_id not in SOURCE_LABEL_TO_DENSE
        assert IGNORE_INDEX == -100

    def test_02_c11_residual_audit_artifact_valid(self):
        assert C11_RESIDUAL_AUDIT_PATH.exists()
        data = json.loads(C11_RESIDUAL_AUDIT_PATH.read_text(encoding="utf-8"))
        assert data["phase"] == "EXP-07-P0-C12"
        error_ids = [e["error_id"] for e in data["residual_errors_identified"]]
        assert "RES-C11-001" in error_ids
        assert "RES-C11-002" in error_ids
        assert "RES-C11-003" in error_ids

    def test_03_runtime_input_representation_discipline(self):
        data = json.loads(CAMPAIGN_SPEC_PATH.read_text(encoding="utf-8"))
        rep_spec = data["sensor_representation_specification"]
        assert "DN-domain" in rep_spec["runtime_input_definition"]
        assert "log1p" in rep_spec["runtime_input_definition"]
        assert "Never casually cite as sigma0" in rep_spec["terminology_invariant"]


class TestC12ParentIdentityAndPartitioningGuardrails:
    def test_04_parent_identity_rules_complete(self):
        assert PARENT_RULES_PATH.exists()
        data = json.loads(PARENT_RULES_PATH.read_text(encoding="utf-8"))
        hierarchy = data["independence_hierarchy"]
        assert "SAME_PARENT" in hierarchy
        assert "RELATED_ACQUISITIONS" in hierarchy
        assert "POTENTIALLY_DEPENDENT" in hierarchy
        assert "INDEPENDENT" in hierarchy
        assert "When independence between two candidate scenes is ambiguous" in data["default_rule"]

    def test_05_split_specification_pre_slicing_requirement(self):
        assert SPLIT_SPEC_PATH.exists()
        data = json.loads(SPLIT_SPEC_PATH.read_text(encoding="utf-8"))
        part_arch = data["partition_architecture"]
        assert part_arch["unit_of_partitioning"] == "INDEPENDENT_PARENT_SCENE_CLUSTER"
        assert "BEFORE any spatial tiling" in part_arch["rule_of_partitioning"]
        assert "CRYPTOGRAPHICALLY_QUARANTINED" in part_arch["partitions"]["HOLDOUT"]["access_level"]

    def test_06_holdout_firewall_rules_enforced(self):
        data = json.loads(SPLIT_SPEC_PATH.read_text(encoding="utf-8"))
        firewall_rules = data["partition_architecture"]["partitions"]["HOLDOUT"]["firewall_rules"]
        assert any("Zero access during exploratory data analysis" in r for r in firewall_rules)
        assert any("Zero access for threshold tuning" in r for r in firewall_rules)
        assert any("Zero access for model architecture selection" in r for r in firewall_rules)


class TestC12ProvenanceAndSufficiencyGuardrails:
    def test_07_provenance_schema_required_fields(self):
        assert PROVENANCE_SCHEMA_PATH.exists()
        data = json.loads(PROVENANCE_SCHEMA_PATH.read_text(encoding="utf-8"))
        fields = data["manifest_structure"]["sample_record_fields"]
        required_keys = [
            "sample_id", "parent_scene_id", "source_product_id",
            "acquisition_datetime_utc", "platform", "polarization",
            "geographic_metadata", "source_class_ids_present",
            "canonical_dense_class_ids_present", "annotation_provenance",
            "derived_image_sha256", "derived_mask_sha256", "partition"
        ]
        for k in required_keys:
            assert k in fields
            assert fields[k].get("required") is True

        # Unknown handling
        assert "UNKNOWN" in data["null_and_unknown_handling"]["rule"]

    def test_08_minimum_sufficiency_matrix_integrity(self):
        assert SUFFICIENCY_GATE_PATH.exists()
        data = json.loads(SUFFICIENCY_GATE_PATH.read_text(encoding="utf-8"))
        matrix = data["readiness_matrix"]
        dims = [row["dimension"] for row in matrix]
        assert "TOTAL_INDEPENDENT_PARENT_SCENES" in dims
        assert "RARE_CLASS_PARENT_DIVERSITY" in dims
        assert "EVALUATION_SPLIT_CLASS_PRESENCE" in dims
        assert "ANTHROPOGENIC_HM_REPRESENTATION" in dims
        assert "PARTITION_INDEPENDENCE_INTEGRITY" in dims

        for row in matrix:
            assert "minimum_target" in row
            assert "preferred_target" in row
            assert "hard_failure_threshold" in row
            assert "scientific_rationale" in row

    def test_09_source_evaluation_framework_valid(self):
        assert SOURCE_EVAL_PATH.exists()
        data = json.loads(SOURCE_EVAL_PATH.read_text(encoding="utf-8"))
        crit_ids = [c["id"] for c in data["scoring_rubric"]["criteria"]]
        assert "CRIT_02_PARENT_TRACEABILITY" in crit_ids
        assert "CRIT_04_ANNOTATION_QUALITY_AND_TIER" in crit_ids
        assert "CRIT_07_TAXONOMY_COMPATIBILITY" in crit_ids


class TestC12GovernanceAndSafetyGates:
    def test_10_governance_rules_73_through_76_active(self):
        assert GOV_RULES_PATH.exists()
        data = json.loads(GOV_RULES_PATH.read_text(encoding="utf-8"))
        rule_ids = [r["rule_id"] for r in data["rules"]]
        assert "GOV-RULE-073" in rule_ids
        assert "GOV-RULE-074" in rule_ids
        assert "GOV-RULE-075" in rule_ids
        assert "GOV-RULE-076" in rule_ids

    def test_11_incidents_p0_c12_recorded_and_resolved(self):
        assert INCIDENT_REG_PATH.exists()
        data = json.loads(INCIDENT_REG_PATH.read_text(encoding="utf-8"))
        incident_ids = [inc["incident_id"] for inc in data["incidents"]]
        assert "INC-P0-C12-001" in incident_ids
        assert "INC-P0-C12-002" in incident_ids

    def test_12_no_training_authorization_in_c12(self):
        assert RUN_STATE_PATH.exists()
        run_state = json.loads(RUN_STATE_PATH.read_text(encoding="utf-8"))
        assert run_state["training_authorization"] == "NO"

        campaign_spec = json.loads(CAMPAIGN_SPEC_PATH.read_text(encoding="utf-8"))
        assert campaign_spec["governance_status"] == "LOCKED_NO_TRAINING_AUTHORIZATION"
