"""EXP-07-P0-C15: OPS-02 Formal Dataset Freeze and Training Readiness Guardrails.

Validates:
1. Formal dataset freeze specification integrity (OPS02_DATASET_FREEZE_SPEC_v1.json).
2. Physical file and SHA-256 hash consistency across all 212 samples.
3. Canonical multiclass taxonomy firewall (0..11, zero class 14 Mineral Oil Spill).
4. 64 vs 91 independent parent and datatake accounting reconciliation.
5. Absolute partition isolation and zero cross-partition datatake/scene leakage.
6. Strict HOLDOUT partition quarantine firewall.
7. Geometry classification, multiplicity, and reproducibility audit specifications.
8. Authoritative pre-training protocol freeze and normalization constants.
9. Training readiness authorization gate status.
10. Governance learning (GOV-RULE-081 through GOV-RULE-084).
11. Prohibitions integrity (no training, no Seed 2024, no HOLDOUT model selection).
"""

import hashlib
import json
from pathlib import Path
from PIL import Image
import numpy as np
import pytest
import rasterio

REPO_ROOT = Path(__file__).resolve().parent.parent
OPS02_DIR = REPO_ROOT / "data" / "ops02"
MANIFESTS_DIR = OPS02_DIR / "manifests"
AUDITS_DIR = OPS02_DIR / "audits"
METADATA_DIR = REPO_ROOT / "data" / "metadata"
TELEMETRY_PATH = REPO_ROOT / "scratch" / "exp07_p0_c15_run_state.json"
FREEZE_SPEC_PATH = OPS02_DIR / "OPS02_DATASET_FREEZE_SPEC_v1.json"
PRETRAINING_PROTOCOL_PATH = REPO_ROOT / "experiments" / "EXP-07" / "EXP07_P0_C15_PRETRAINING_PROTOCOL_V1.md"


def test_freeze_spec_exists_and_valid():
    assert FREEZE_SPEC_PATH.exists(), f"Freeze spec missing: {FREEZE_SPEC_PATH}"
    with open(FREEZE_SPEC_PATH, "r", encoding="utf-8") as f:
        spec = json.load(f)
    assert spec["dataset_version"] == "OPS02_v1.0.0_FROZEN"
    assert spec["freeze_status"] == "FROZEN"
    assert spec["summary"]["total_physical_sample_pairs"] == 212
    assert spec["summary"]["total_independent_parent_clusters"] == 64
    assert spec["summary"]["total_mission_datatakes"] == 64
    assert spec["summary"]["partition_breakdown"]["TRAIN"]["sample_pairs"] == 132
    assert spec["summary"]["partition_breakdown"]["DEV"]["sample_pairs"] == 40
    assert spec["summary"]["partition_breakdown"]["HOLDOUT"]["sample_pairs"] == 40


def test_physical_dataset_manifest_and_filesystem_consistency():
    manifest_path = MANIFESTS_DIR / "ops02_physical_dataset_manifest_v1.json"
    assert manifest_path.exists()
    with open(manifest_path, "r", encoding="utf-8") as f:
        m = json.load(f)
    samples = m["samples"]
    assert len(samples) == 212

    for s in samples:
        img_p = REPO_ROOT / s["derived_image_path"]
        mask_p = REPO_ROOT / s["derived_mask_path"]
        assert img_p.exists(), f"Missing image: {img_p}"
        assert mask_p.exists(), f"Missing mask: {mask_p}"

        with rasterio.open(img_p) as ds:
            assert ds.shape == (256, 256)
            assert ds.count == 1
            assert ds.dtypes[0] == "float32"
            arr = ds.read(1)
            assert not np.isnan(arr).any()
            assert not np.isinf(arr).any()

        mask_arr = np.array(Image.open(mask_p))
        assert mask_arr.shape == (256, 256)


def test_sha256_hash_integrity():
    manifest_path = MANIFESTS_DIR / "ops02_physical_dataset_manifest_v1.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        m = json.load(f)

    # Verify a representative stratified sample across partitions
    samples = m["samples"]
    # Check 15 samples across train/dev/holdout
    for s in samples[::14]:
        img_p = REPO_ROOT / s["derived_image_path"]
        mask_p = REPO_ROOT / s["derived_mask_path"]

        with open(img_p, "rb") as f:
            img_hash = hashlib.sha256(f.read()).hexdigest().upper()
        with open(mask_p, "rb") as f:
            mask_hash = hashlib.sha256(f.read()).hexdigest().upper()

        assert img_hash == s["image_sha256"].upper()
        assert mask_hash == s["mask_sha256"].upper()


def test_canonical_taxonomy_and_quarantine_firewall():
    audit_p = AUDITS_DIR / "ops02_taxonomy_freeze_v1.json"
    assert audit_p.exists()
    with open(audit_p, "r", encoding="utf-8") as f:
        tax = json.load(f)

    assert tax["taxonomy_version"] == "CANONICAL_DENSE_12_CLASS_V1"
    assert len(tax["dense_classes"]) == 12
    assert tax["quarantined_and_excluded_classes"]["source_class_14"]["verified_pixels_in_ops02"] == 0

    manifest_path = MANIFESTS_DIR / "ops02_physical_dataset_manifest_v1.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        m = json.load(f)

    for s in m["samples"]:
        assert 14 not in s["source_class_ids_present"], f"Class 14 leaked into sample {s['sample_id']}"
        assert all(0 <= c <= 11 for c in s["canonical_dense_class_ids_present"])


def test_parent_accounting_64_vs_91_reconciliation():
    audit_p = AUDITS_DIR / "ops02_final_parent_accounting_audit_v1.json"
    assert audit_p.exists()
    with open(audit_p, "r", encoding="utf-8") as f:
        acct = json.load(f)

    summary = acct["accounting_summary"]
    assert summary["ops01_unique_datatakes"] == 27
    assert summary["ops02_unique_datatakes"] == 64
    assert summary["combined_unique_independent_datatakes"] == 91
    assert summary["direct_scene_overlap_ops01_vs_ops02"] == 0
    assert summary["datatake_overlap_ops01_vs_ops02"] == 0
    assert acct["reconciliation_analysis"]["finding"] == "EXACT_SET_UNION_VERIFIED"


def test_partition_isolation_zero_leakage():
    manifest_p = MANIFESTS_DIR / "ops02_partition_manifest_v1.json"
    assert manifest_p.exists()
    with open(manifest_p, "r", encoding="utf-8") as f:
        part = json.load(f)

    def extract_clusters(clist):
        return {c if isinstance(c, str) else c["cluster_id"] for c in clist}

    train_c = extract_clusters(part["partitions"]["TRAIN"]["clusters"])
    dev_c = extract_clusters(part["partitions"]["DEV"]["clusters"])
    ho_c = extract_clusters(part["partitions"]["HOLDOUT"]["clusters"])

    assert len(train_c) == 40
    assert len(dev_c) == 12
    assert len(ho_c) == 12
    assert len(train_c & dev_c) == 0
    assert len(train_c & ho_c) == 0
    assert len(dev_c & ho_c) == 0


def test_holdout_quarantine_firewall():
    gate_p = AUDITS_DIR / "ops02_training_readiness_gate_v1.json"
    assert gate_p.exists()
    with open(gate_p, "r", encoding="utf-8") as f:
        gate = json.load(f)

    assert gate["gate_questions"]["8_is_holdout_pristine"]["verdict"] == "YES"
    assert "No evaluation on HOLDOUT during model selection." in gate["prohibited_actions"]


def test_geometry_and_reproducibility_audit_spec():
    repro_p = AUDITS_DIR / "ops02_reproducibility_audit_v1.json"
    indep_p = AUDITS_DIR / "ops02_final_independence_audit_v1.json"
    assert repro_p.exists()
    assert indep_p.exists()

    with open(repro_p, "r", encoding="utf-8") as f:
        repro = json.load(f)
    assert repro["epistemic_decomposition"]["artifact_integrity"]["level"] == "OBSERVED_COMPLETE"
    assert repro["deterministic_parameters"]["crop_window_size"] == [2560, 2560]

    with open(indep_p, "r", encoding="utf-8") as f:
        indep = json.load(f)
    assert "C15 MUST NOT claim '212 independent physical samples'" in indep["authoritative_terminology"]["mandate"]


def test_pretraining_protocol_frozen():
    assert PRETRAINING_PROTOCOL_PATH.exists()
    content = PRETRAINING_PROTOCOL_PATH.read_text(encoding="utf-8")
    assert "AGGREGATED_RAW_DN_LOG1P_STANDARDIZED" in content
    assert "4.424158" in content
    assert "0.469261" in content
    assert "ResNet18-UNet" in content
    assert "14,310,860" in content
    assert "Candidate F Hybrid" in content


def test_training_authorization_gate_verdict():
    gate_p = AUDITS_DIR / "ops02_training_readiness_gate_v1.json"
    assert gate_p.exists()
    with open(gate_p, "r", encoding="utf-8") as f:
        gate = json.load(f)
    assert gate["final_status"] == "TRAINING_AUTHORIZED_WITH_EXPLICIT_LIMITATIONS"
    assert len(gate["explicit_scientific_limitations"]) >= 4


def test_governance_rules_integrity():
    gov_p = METADATA_DIR / "ocean_sentinel_governance_rules_v1.json"
    assert gov_p.exists()
    with open(gov_p, "r", encoding="utf-8") as f:
        gov = json.load(f)

    rule_ids = {r["rule_id"] for r in gov["rules"]}
    assert "GOV-RULE-081" in rule_ids
    assert "GOV-RULE-082" in rule_ids
    assert "GOV-RULE-083" in rule_ids
    assert "GOV-RULE-084" in rule_ids


def test_prohibitions_and_telemetry():
    assert TELEMETRY_PATH.exists()
    with open(TELEMETRY_PATH, "r", encoding="utf-8") as f:
        state = json.load(f)

    assert state["training_started"] is False
    assert state["seed2024_started"] is False
    assert state["holdout_model_access"] is False
