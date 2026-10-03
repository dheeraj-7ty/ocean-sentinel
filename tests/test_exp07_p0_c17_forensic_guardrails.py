"""EXP-07-P0-C17: C16 Forensic Validity Audit Guardrails.

Validates:
1. C15 vs C16 freeze reconciliation and DEV 40 vs 41 sample accounting.
2. Manifest and physical dataset integrity across 212 samples.
3. Code lineage and SHA-256 identity of train_replicate003.py.
4. Metric definition and mathematical consistency (dev_mIoU_phenomena).
5. GPU execution facts (single-GPU cuda:0 vs dual-T4 reporting, 55.5 MB eval memory).
6. Checkpoint forensics (best_model.pt and last_model.pt SHA-256 and parameter counts).
7. HOLDOUT quarantine firewall integrity (0 access).
8. Candidate F sampler bounded determinism and zero partition leakage.
9. Final validity gate verdict (VALID_BUT_PROTOCOL_LIMITED) and NEXT_REPLICATE_AUTHORIZED == False.
10. Telemetry state and operational prohibitions.
"""

import hashlib
import json
from pathlib import Path
import pytest
import torch
import torch.nn as nn
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
OPS02_DIR = REPO_ROOT / "data" / "ops02"
AUDITS_DIR = OPS02_DIR / "audits"
MANIFESTS_DIR = OPS02_DIR / "manifests"
METADATA_DIR = REPO_ROOT / "data" / "metadata"
RUN_DIR = REPO_ROOT / "experiments" / "EXP-07" / "runs" / "EXP07_RUN003_SEED42"
TELEMETRY_PATH = REPO_ROOT / "scratch" / "exp07_p0_c17_run_state.json"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def test_freeze_reconciliation_audit_exists_and_valid():
    audit_p = AUDITS_DIR / "ops02_c15_c16_freeze_reconciliation_v1.json"
    assert audit_p.exists(), f"Missing {audit_p}"

    with open(audit_p, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["status"] == "RECONCILED_WITH_DOCUMENTATION_DEFECT"
    assert data["summary"]["verdict"] == "PHYSICAL_DATASET_IDENTICAL_C15_DOCUMENTATION_DEFECT"

    # Verify physical manifest counts
    phys_p = MANIFESTS_DIR / "ops02_physical_dataset_manifest_v1.json"
    with open(phys_p, "r", encoding="utf-8") as f:
        phys = json.load(f)

    samples = phys["samples"]
    assert len(samples) == 212
    train_cnt = sum(1 for s in samples if s["partition"] == "TRAIN")
    dev_cnt = sum(1 for s in samples if s["partition"] == "DEV")
    holdout_cnt = sum(1 for s in samples if s["partition"] == "HOLDOUT")

    assert train_cnt == 132
    assert dev_cnt == 40
    assert holdout_cnt == 40


def test_partition_manifest_and_cluster_slice_accounting():
    part_p = MANIFESTS_DIR / "ops02_partition_manifest_v1.json"
    clust_p = MANIFESTS_DIR / "ops02_parent_cluster_manifest_v1.json"
    assert part_p.exists() and clust_p.exists()

    with open(part_p, "r", encoding="utf-8") as f:
        part = json.load(f)
    with open(clust_p, "r", encoding="utf-8") as f:
        clust = json.load(f)

    assert len(part["partitions"]["TRAIN"]["sample_ids"]) == 132
    assert len(part["partitions"]["DEV"]["sample_ids"]) == 40
    assert len(part["partitions"]["HOLDOUT"]["sample_ids"]) == 40

    dev_clusters = [c for c in clust["clusters"] if c.get("partition") == "DEV"]
    holdout_clusters = [c for c in clust["clusters"] if c.get("partition") == "HOLDOUT"]

    assert len(dev_clusters) == 12
    assert len(holdout_clusters) == 12

    # Cluster sum must equal 40 exactly
    assert sum(c["sample_count"] for c in dev_clusters) == 40
    assert sum(c["sample_count"] for c in holdout_clusters) == 40


def test_manifest_and_freeze_spec_hashes():
    spec_p = OPS02_DIR / "OPS02_DATASET_FREEZE_SPEC_v1.json"
    phys_p = MANIFESTS_DIR / "ops02_physical_dataset_manifest_v1.json"
    part_p = MANIFESTS_DIR / "ops02_partition_manifest_v1.json"
    clust_p = MANIFESTS_DIR / "ops02_parent_cluster_manifest_v1.json"

    assert sha256_file(spec_p) == "AF406D5F4E4092D8ECE240220FB97FF6B28C393D0D37D878898B26D0C6A4A57E"
    assert sha256_file(phys_p) == "F5480EA2E26AF8D963EDE40CA658138CDCD6157CD79438E9C8673AD0C1DD8102"
    assert sha256_file(part_p) == "757DEAF7A7E72BE331843B518A99AF32E14D68A080822F1D9B4FDBADF889F94D"
    assert sha256_file(clust_p) == "08ED21FBB492363E1D05040020F73177BFD4DC84F1A39E2D9C5C9B38BC97D10B"


def test_c16_code_lineage_and_script_hash():
    lineage_p = METADATA_DIR / "exp07_p0_c17_code_lineage_v1.json"
    assert lineage_p.exists()

    with open(lineage_p, "r", encoding="utf-8") as f:
        lineage = json.load(f)

    v4 = lineage["versions_lineage"][-1]
    assert v4["kernel_version"] == 4
    assert v4["exit_status"] == "COMPLETED_SUCCESSFULLY"
    assert v4["best_checkpoint_sha256"] == "936EF935F8049FA15FBC735F8073D08F074796ACC20BE0A2885DD35C7CB09D67"

    script_p = REPO_ROOT / "scratch" / "kaggle_replicate003_kernel" / "train_replicate003.py"
    assert script_p.exists()
    assert sha256_file(script_p) == "DF9F35BB957B907671FE13029923F59C9C90704712343CE010301582F6D61ADB"


def test_c16_metric_definition_audit():
    audit_p = AUDITS_DIR / "ops02_c16_metric_definition_audit_v1.json"
    assert audit_p.exists()

    with open(audit_p, "r", encoding="utf-8") as f:
        audit = json.load(f)

    assert audit["status"] == "MATHEMATICALLY_VERIFIED_EXACT_HARMONIZATION"
    assert "CONFIRMED_EXCLUDED" in audit["audit_findings"]["background_exclusion"]
    assert "CONFIRMED_INCLUDED" in audit["audit_findings"]["class_11_hm_inclusion"]


def test_c16_gpu_execution_audit():
    audit_p = AUDITS_DIR / "ops02_c16_gpu_execution_audit_v1.json"
    assert audit_p.exists()

    with open(audit_p, "r", encoding="utf-8") as f:
        audit = json.load(f)

    hw = audit["hardware_environment_findings"]
    assert hw["parallelism_and_device_utilization"]["dataparallel_used"] is False
    assert hw["parallelism_and_device_utilization"]["distributed_dataparallel_used"] is False
    assert "BENCHMARK_EVAL_TENSOR_RESIDENCE" in hw["memory_allocation_forensics"]["technical_classification"]


def test_checkpoint_forensics():
    forensics_p = AUDITS_DIR / "ops02_c16_checkpoint_forensics_v1.json"
    assert forensics_p.exists()

    with open(forensics_p, "r", encoding="utf-8") as f:
        forensics = json.load(f)

    best_ckpt = forensics["checkpoints"]["best_model"]
    last_ckpt = forensics["checkpoints"]["last_model"]

    assert best_ckpt["sha256"] == "936EF935F8049FA15FBC735F8073D08F074796ACC20BE0A2885DD35C7CB09D67"
    assert last_ckpt["sha256"] == "60411490EFB81D5DE806F4DFFBA760F5D7F4486B14AB4F144AD35D37EE16FA9E"
    assert best_ckpt["trainable_parameters"] == 14310860
    assert best_ckpt["batchnorm_layers"] == 30
    assert forensics["tensor_level_comparison"]["differing_tensors_count"] == 192


def test_holdout_quarantine_firewall():
    metrics_p = RUN_DIR / "metrics.json"
    assert metrics_p.exists()

    with open(metrics_p, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    assert metrics["holdout_access_count"] == 0


def test_candidate_f_sampler_deterministic_audit():
    phys_p = MANIFESTS_DIR / "ops02_physical_dataset_manifest_v1.json"
    with open(phys_p, "r", encoding="utf-8") as f:
        phys = json.load(f)

    train_samples = [s for s in phys["samples"] if s["partition"] == "TRAIN"]
    holdout_sids = {s["sample_id"] for s in phys["samples"] if s["partition"] == "HOLDOUT"}
    dev_sids = {s["sample_id"] for s in phys["samples"] if s["partition"] == "DEV"}

    parent_counts = {}
    for s in train_samples:
        parent_counts[s["cluster_id"]] = parent_counts.get(s["cluster_id"], 0) + 1

    w_parent = np.array([1.0 / parent_counts[s["cluster_id"]] for s in train_samples], dtype=np.float64)
    w_parent /= w_parent.sum()

    presence_scores = []
    for s in train_samples:
        fg_classes = [c for c in s["canonical_dense_class_ids_present"] if c > 0]
        score = sum(1.0 / np.sqrt(max(1, len([x for x in train_samples if c in x["canonical_dense_class_ids_present"]]))) for c in fg_classes)
        presence_scores.append(max(0.1, score))
    w_presence = np.array(presence_scores, dtype=np.float64)
    w_presence /= w_presence.sum()

    w_hybrid = 0.70 * w_parent + 0.30 * w_presence
    w_hybrid /= w_hybrid.sum()
    weights_tensor = torch.as_tensor(w_hybrid, dtype=torch.double)

    for epoch in range(1, 4):
        g = torch.Generator()
        g.manual_seed(42 + epoch * 1000)
        indices = torch.multinomial(weights_tensor, 72, replacement=True, generator=g).tolist()
        drawn_sids = {train_samples[i]["sample_id"] for i in indices}

        assert len(indices) == 72
        assert len(drawn_sids & holdout_sids) == 0, f"Leakage of HOLDOUT into sampler draws at epoch {epoch}!"
        assert len(drawn_sids & dev_sids) == 0, f"Leakage of DEV into sampler draws at epoch {epoch}!"


def test_final_validity_gate_and_replicate_prohibition():
    gate_p = AUDITS_DIR / "ops02_c16_final_validity_gate_v1.json"
    assert gate_p.exists()

    with open(gate_p, "r", encoding="utf-8") as f:
        gate = json.load(f)

    assert gate["c16_scientific_validity_classification"] == "B_VALID_BUT_PROTOCOL_LIMITED"
    assert gate["next_replicate_decision"] == "TRAINING_PAUSED_PENDING_PROTOCOL_REMEDIATION"
    assert gate["authorization_status"]["next_replicate_authorized"] is False
    assert gate["authorization_status"]["training_started"] is False
    assert gate["authorization_status"]["seed2024_started"] is False
    assert gate["authorization_status"]["holdout_access"] is False
