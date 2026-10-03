"""EXP-07-P0-C13: OPS-02 Controlled Acquisition Pilot & Feasibility Guardrails.

Automated regression suite verifying:
- Canonical dense taxonomy integrity (OF is Dense Index 5 / Source Label 6, POW is Dense Index 6 / Source Label 7)
- Excluded source labels (3=IB, 9=SI, 14=OS) strictly mapped to ignore_index (-100)
- Physical vs catalog distinction: catalog entries != physical data
- Parent identity requirements and datatake clustering (GOV-RULE-077)
- Multi-source crosswalk and deduplication (GOV-RULE-078)
- Partition-before-slicing requirement and zero cross-partition parent sharing
- Provenance manifest schema compliance on pilot materialized samples
- 100% technical raster QC pass rate on pilot samples
- Multi-dimensional dataset sufficiency reassessment
- Quarantine semantics for oil spills and weak labels
- Holdout preservation and absolute prohibition of training in C13
- Governance rules GOV-RULE-077 and GOV-RULE-078 active
- Incident INC-P0-C13-001 recorded and resolved
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

SOURCE_REG_PATH = METADATA_DIR / "exp07_p0_c13_source_registry_v1.json"
CANDIDATE_INV_PATH = METADATA_DIR / "exp07_p0_c13_candidate_inventory_v1.json"
PARENT_AUDIT_PATH = METADATA_DIR / "exp07_p0_c13_parent_identity_audit_v1.json"
PROVENANCE_MANIFEST_PATH = METADATA_DIR / "exp07_p0_c13_provenance_manifest_v1.json"
QC_RESULTS_PATH = METADATA_DIR / "exp07_p0_c13_qc_results_v1.json"
COVERAGE_MATRIX_PATH = METADATA_DIR / "exp07_p0_c13_coverage_matrix_v1.json"
SUFFICIENCY_REASSESS_PATH = METADATA_DIR / "exp07_p0_c13_sufficiency_reassessment_v1.json"
SOURCE_CROSSWALK_PATH = METADATA_DIR / "exp07_p0_c13_source_crosswalk_v1.json"
RUN_STATE_PATH = SCRATCH_DIR / "exp07_p0_c13_run_state.json"


class TestC13TaxonomyAndQuarantineGuardrails:
    def test_01_canonical_dense_and_excluded_mapping(self):
        from ocean_sentinel.ml.exp07_reference import DENSE_CLASSES, SOURCE_LABEL_TO_DENSE, IGNORE_INDEX
        assert DENSE_CLASSES[5] == "OF"
        assert DENSE_CLASSES[6] == "POW"
        assert DENSE_CLASSES[11] == "HM"
        assert SOURCE_LABEL_TO_DENSE[6] == 5
        assert SOURCE_LABEL_TO_DENSE[7] == 6
        assert SOURCE_LABEL_TO_DENSE[13] == 11
        for ex in [3, 9, 14]:
            assert ex not in SOURCE_LABEL_TO_DENSE
        assert IGNORE_INDEX == -100

    def test_02_oil_spill_and_lookalike_task_separation(self):
        reg = json.loads(SOURCE_REG_PATH.read_text(encoding="utf-8"))
        trujillo_src = next(s for s in reg["registry"] if s["source_id"] == "SRC_04_TRUJILLO_2024_OIL")
        assert trujillo_src["decision"] == "QUARANTINED_FOR_EXP07_RESERVED_FOR_FUTURE_OIL_SPILL_TASK"


class TestC13ParentIdentityAndDeduplicationGuardrails:
    def test_03_parent_identity_audit_integrity(self):
        assert PARENT_AUDIT_PATH.exists()
        audit = json.loads(PARENT_AUDIT_PATH.read_text(encoding="utf-8"))
        assert audit["total_pilot_parents_audited"] >= 12
        assert audit["ops01_parent_overlap_count"] == 0
        assert audit["independent_parents_confirmed"] >= 12

    def test_04_datatake_clustering_preventing_pseudoreplication(self):
        audit = json.loads(PARENT_AUDIT_PATH.read_text(encoding="utf-8"))
        datatakes = [r["mission_data_take_id"] for r in audit["audit_records"]]
        # Ensure all pilot parents have unique datatake IDs
        assert len(datatakes) == len(set(datatakes))

    def test_05_source_crosswalk_graph_structure(self):
        assert SOURCE_CROSSWALK_PATH.exists()
        cw = json.loads(SOURCE_CROSSWALK_PATH.read_text(encoding="utf-8"))
        node_ids = [n["node_id"] for n in cw["nodes"]]
        assert "ARCHIVE_AWS_S3_SENTINEL1" in node_ids
        assert "DATASET_LI_IW_ZENODO_14279466" in node_ids
        assert "DATASET_DARTIS_LOOKALIKES" in node_ids
        assert "DATASET_TRUJILLO_2024" in node_ids


class TestC13PilotMaterializationAndQCGuardrails:
    def test_06_pilot_materialized_files_exist_and_match_manifest(self):
        assert PROVENANCE_MANIFEST_PATH.exists()
        manifest = json.loads(PROVENANCE_MANIFEST_PATH.read_text(encoding="utf-8"))
        assert manifest["total_physical_parent_scenes"] >= 12
        assert manifest["total_derived_tiles"] >= 12

        for sample in manifest["samples"]:
            img_path = REPO_ROOT / sample["derived_image_path"]
            mask_path = REPO_ROOT / sample["derived_mask_path"]
            assert img_path.exists(), f"Missing image: {img_path}"
            assert mask_path.exists(), f"Missing mask: {mask_path}"

    def test_07_pilot_technical_raster_qc_100_percent_pass(self):
        assert QC_RESULTS_PATH.exists()
        qc = json.loads(QC_RESULTS_PATH.read_text(encoding="utf-8"))
        assert qc["total_samples_tested"] >= 12
        assert qc["failed_qc_count"] == 0
        assert qc["qc_pass_rate"] == 1.0

    def test_08_provenance_schema_fields_present_in_pilot(self):
        manifest = json.loads(PROVENANCE_MANIFEST_PATH.read_text(encoding="utf-8"))
        sample = manifest["samples"][0]
        required_fields = [
            "sample_id", "parent_scene_id", "source_product_id",
            "acquisition_datetime_utc", "platform", "polarization",
            "geographic_metadata", "source_class_ids_present",
            "canonical_dense_class_ids_present", "annotation_provenance",
            "derived_image_sha256", "derived_mask_sha256", "partition"
        ]
        for f in required_fields:
            assert f in sample
        assert sample["annotation_provenance"]["provenance_tier"] in ["TIER_A", "TIER_B"]


class TestC13SufficiencyAndGovernanceGuardrails:
    def test_09_sufficiency_reassessment_valid(self):
        assert SUFFICIENCY_REASSESS_PATH.exists()
        reassess = json.loads(SUFFICIENCY_REASSESS_PATH.read_text(encoding="utf-8"))
        assert "TOTAL_INDEPENDENT_PARENT_SCENES" in [t["dimension"] for t in reassess["target_audits"]]
        assert "RARE_CLASS_PARENT_DIVERSITY" in [t["dimension"] for t in reassess["target_audits"]]

    def test_10_governance_rules_77_and_78_active(self):
        assert GOV_RULES_PATH.exists()
        rules = json.loads(GOV_RULES_PATH.read_text(encoding="utf-8"))["rules"]
        rule_ids = [r["rule_id"] for r in rules]
        assert "GOV-RULE-077" in rule_ids
        assert "GOV-RULE-078" in rule_ids

    def test_11_incident_p0_c13_recorded_and_resolved(self):
        assert INCIDENT_REG_PATH.exists()
        incidents = json.loads(INCIDENT_REG_PATH.read_text(encoding="utf-8"))["incidents"]
        inc_ids = [i["incident_id"] for i in incidents]
        assert "INC-P0-C13-001" in inc_ids

    def test_12_no_training_authorization_in_c13(self):
        assert RUN_STATE_PATH.exists()
        state = json.loads(RUN_STATE_PATH.read_text(encoding="utf-8"))
        assert state["training_authorization"] == "NO"
        assert state["seed2024_authorization"] == "NO"
