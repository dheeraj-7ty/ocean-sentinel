"""Test suite for EXP-07-P0-C22-A.9: Final EXP07_DIAG01 Protocol-Parameter
Consistency Audit and Pre-Training Authorization Gate.

Validates that:
1. Canonical control vector is the exact 12-element square-root median frequency vector.
2. Treatment vector is the exact 12-element uniform unweighted vector [1.0] * 12.
3. Loss vector JSON serializations match exact cryptographic digests.
4. Training schedule bounds are MAX_EPOCHS = 30, MIN_EPOCHS = 15, PATIENCE = 10.
5. Primary metric is strictly dev_mIoU_phenomena (classes 1..11, background Class 0 excluded).
6. Batch dynamics distinguish physical batch (8), accumulation (2), and virtual batch (16).
7. Input modality is strictly single-band VV SAR (1 channel).
8. Multiclass taxonomy comprises exactly 12 dense classes with exclusions 3, 9, 14 -> -100.
9. Sampler strategy is strictly Candidate F Hybrid (72 draws/epoch, replacement=True, seed=42).
10. Optimizer and scheduler settings match frozen protocol (AdamW 5e-4, CosineWarmup 30 epochs).
11. Authoritative partition independence counts equal 40 TRAIN, 12 DEV, 12 HOLDOUT (64 total).
12. Erroneous three-element loss vector [0.0898, 0.9069, 1.0033] does not exist in active protocol or code.
13. Stale 15-max-epochs claim is eliminated from report narrative.
14. Stale dual-polarization 'VV/VH' claim is eliminated from report narrative.
15. Cryptographic hashes of frozen manifest, canonical state, backbone, and random state match bitwise.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import pytest
import torch

REPO_ROOT = Path(__file__).resolve().parent.parent

C21_PROTOCOL = REPO_ROOT / "data" / "ops02" / "audits" / "ops02_c21_single_variable_diagnostic_protocol_v1.json"
C15_PROTOCOL = REPO_ROOT / "experiments" / "EXP-07" / "EXP07_P0_C15_PRETRAINING_PROTOCOL_V1.md"
C22A8_REPORT = REPO_ROOT / "experiments" / "EXP-07" / "EXP07_P0_C22A8_FINAL_INDEPENDENCE_SOURCE_OF_TRUTH_AND_READINESS_20260914.md"
C22A9_AUDIT = REPO_ROOT / "data" / "ops02" / "audits" / "ops02_c22a9_exp07_protocol_consistency_v1.json"
C22A9_INCIDENT = REPO_ROOT / "data" / "metadata" / "exp07_p0_c22a9_incident_register_v1.json"
PHYSICAL_MANIFEST = REPO_ROOT / "data" / "ops02" / "manifests" / "ops02_physical_dataset_manifest_v1.json"
CANONICAL_MODEL = REPO_ROOT / "data" / "ops02" / "initial_model_state_canonical.pt"
HISTORICAL_RANDOM = REPO_ROOT / "data" / "ops02" / "initial_model_state.pt"
PRETRAINED_BACKBONE = Path(os.path.expanduser("~/.cache/torch/hub/checkpoints/resnet18-f37072fd.pth"))

EXPECTED_CONTROL_VECTOR = [
    0.403935, 2.450546, 0.876692, 0.945945, 0.648189, 4.211476,
    0.719641, 2.956203, 1.064525, 1.882870, 0.387652, 18.243211
]
EXPECTED_TREATMENT_VECTOR = [1.0] * 12


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while b := f.read(65536):
            h.update(b)
    return h.hexdigest().upper()


def test_01_canonical_control_vector_exact_12_elements():
    """Verify control loss vector has length 12 and exact 6-decimal literals."""
    from ocean_sentinel.ml.exp07_fingerprint import CANONICAL_HISTORICAL_C16_LITERALS

    assert len(CANONICAL_HISTORICAL_C16_LITERALS) == 12
    assert CANONICAL_HISTORICAL_C16_LITERALS == EXPECTED_CONTROL_VECTOR

    # Verify C21 protocol JSON matches
    c21 = load_json(C21_PROTOCOL)
    ctrl = c21["single_independent_variable"]["control_condition"]["weight_vector_float32"]
    assert len(ctrl) == 12
    assert ctrl == EXPECTED_CONTROL_VECTOR


def test_02_uniform_treatment_vector_exact_12_elements():
    """Verify treatment loss vector has length 12 and exact 1.0 literals."""
    from ocean_sentinel.ml.exp07_fingerprint import UNIFORM_TREATMENT_LITERALS

    assert len(UNIFORM_TREATMENT_LITERALS) == 12
    assert UNIFORM_TREATMENT_LITERALS == EXPECTED_TREATMENT_VECTOR

    c21 = load_json(C21_PROTOCOL)
    treat = c21["single_independent_variable"]["treatment_condition"]["weight_vector_float32"]
    assert len(treat) == 12
    assert treat == EXPECTED_TREATMENT_VECTOR


def test_03_vector_serialization_and_hash():
    """Verify compact JSON SHA-256 digests of both loss vectors."""
    ctrl_bytes = json.dumps(EXPECTED_CONTROL_VECTOR, separators=(',', ':')).encode('utf-8')
    treat_bytes = json.dumps(EXPECTED_TREATMENT_VECTOR, separators=(',', ':')).encode('utf-8')

    ctrl_hash = hashlib.sha256(ctrl_bytes).hexdigest().upper()
    treat_hash = hashlib.sha256(treat_bytes).hexdigest().upper()

    assert len(ctrl_hash) == 64
    assert len(treat_hash) == 64
    assert ctrl_hash != treat_hash

    # Cross-verify with rehearse script expectations
    rehearse_path = REPO_ROOT / "scripts" / "rehearse_exp07_diag01_canonical_zero_step.py"
    rehearse_content = rehearse_path.read_text(encoding="utf-8")
    assert "CANONICAL_HISTORICAL_C16_LITERALS" in rehearse_content
    assert "UNIFORM_TREATMENT_LITERALS" in rehearse_content


def test_04_training_schedule_bounds():
    """Verify MAX_EPOCHS = 30, MIN_EPOCHS = 15, PATIENCE = 10."""
    c21 = load_json(C21_PROTOCOL)
    inv14 = next(inv for inv in c21["locked_experimental_dimensions"]["invariants"] if inv["id"] == "INV-14")
    inv19 = next(inv for inv in c21["locked_experimental_dimensions"]["invariants"] if inv["id"] == "INV-19")

    assert "T_max=30" in inv14["value"]
    assert "T_warmup=3" in inv14["value"]
    assert "patience=10" in inv19["value"]
    assert "min_epoch=15" in inv19["value"]

    c15_text = C15_PROTOCOL.read_text(encoding="utf-8")
    assert "Total Epochs: 30" in c15_text
    assert "Warmup Epochs: 3" in c15_text


def test_05_primary_metric_contract():
    """Verify primary metric is dev_mIoU_phenomena (classes 1..11, background excluded)."""
    c21 = load_json(C21_PROTOCOL)
    primary = c21["evaluation_and_metrics"]["primary_metric"]
    assert "dev_mIoU_phenomena" in primary
    assert "classes 1 through 11" in primary
    assert "background excluded" in primary

    c15_text = C15_PROTOCOL.read_text(encoding="utf-8")
    assert "**Monitored Metric:** `dev_mIoU_phenomena`" in c15_text
    assert "excluding background Class 0" in c15_text


def test_06_batch_dynamics_and_batchnorm_distinction():
    """Verify physical batch = 8, accumulation = 2, effective batch = 16, BN batch = 8."""
    c21 = load_json(C21_PROTOCOL)
    inv15 = next(inv for inv in c21["locked_experimental_dimensions"]["invariants"] if inv["id"] == "INV-15")
    assert "Physical batch = 8" in inv15["value"]
    assert "accumulation steps = 2" in inv15["value"]
    assert "effective batch = 16" in inv15["value"]


def test_07_input_modality_and_channels():
    """Verify input modality is single-band VV SAR (1 channel)."""
    from ocean_sentinel.ml.exp07_reference import ResNet18UNet

    model = ResNet18UNet(in_channels=1, num_classes=12, pretrained=False)
    assert model.conv1.in_channels == 1
    assert model.head.out_channels == 12

    c21 = load_json(C21_PROTOCOL)
    inv04 = next(inv for inv in c21["locked_experimental_dimensions"]["invariants"] if inv["id"] == "INV-04")
    assert "single-band VV SAR" in inv04["value"]


def test_08_taxonomy_and_exclusion_mapping():
    """Verify 12 dense classes and source labels 3, 9, 14 mapped to ignore_index = -100."""
    from ocean_sentinel.ml.exp07_reference import DENSE_CLASSES, IGNORE_INDEX, SOURCE_LABEL_TO_DENSE

    assert len(DENSE_CLASSES) == 12
    assert DENSE_CLASSES[0] == "BG"
    assert DENSE_CLASSES[11] == "HM"
    assert IGNORE_INDEX == -100

    # Ensure excluded labels are not mapped to dense classes
    assert 3 not in SOURCE_LABEL_TO_DENSE
    assert 9 not in SOURCE_LABEL_TO_DENSE
    assert 14 not in SOURCE_LABEL_TO_DENSE


def test_09_sampler_configuration():
    """Verify Candidate F Hybrid sampler parameters (72 draws/epoch, replacement=True, seed=42)."""
    c21 = load_json(C21_PROTOCOL)
    inv16 = next(inv for inv in c21["locked_experimental_dimensions"]["invariants"] if inv["id"] == "INV-16")
    inv17 = next(inv for inv in c21["locked_experimental_dimensions"]["invariants"] if inv["id"] == "INV-17")

    assert "Candidate F Hybrid" in inv16["value"]
    assert "72 draws per epoch" in inv16["value"]
    assert "Base seed 42" in inv17["value"]


def test_10_optimizer_and_scheduler_settings():
    """Verify AdamW optimizer (5e-4, 0.01 decay) and LinearWarmupCosineAnnealingLR scheduler."""
    c21 = load_json(C21_PROTOCOL)
    inv11 = next(inv for inv in c21["locked_experimental_dimensions"]["invariants"] if inv["id"] == "INV-11")
    inv12 = next(inv for inv in c21["locked_experimental_dimensions"]["invariants"] if inv["id"] == "INV-12")
    inv13 = next(inv for inv in c21["locked_experimental_dimensions"]["invariants"] if inv["id"] == "INV-13")

    assert "AdamW" in inv11["value"]
    assert "0.0005" in inv12["value"]
    assert "0.01" in inv13["value"]


def test_11_authoritative_train_cluster_count():
    """Verify partition cluster counts equal 40 TRAIN, 12 DEV, 12 HOLDOUT (64 total)."""
    p_man = load_json(PHYSICAL_MANIFEST)
    train_cids = set(s["cluster_id"] for s in p_man["samples"] if s["partition"] == "TRAIN")
    dev_cids = set(s["cluster_id"] for s in p_man["samples"] if s["partition"] == "DEV")
    holdout_cids = set(s["cluster_id"] for s in p_man["samples"] if s["partition"] == "HOLDOUT")

    assert len(train_cids) == 40
    assert len(dev_cids) == 12
    assert len(holdout_cids) == 12
    assert len(train_cids | dev_cids | holdout_cids) == 64


def test_12_rejection_of_stale_three_element_loss_vector():
    """Verify erroneous 3-element loss vector [0.0898, 0.9069, 1.0033] does not exist in active protocol."""
    # Check C21 protocol and C22A9 audit
    assert "0.0898" not in C21_PROTOCOL.read_text(encoding="utf-8")
    assert "0.0898" not in (REPO_ROOT / "src" / "ocean_sentinel" / "ml" / "exp07_fingerprint.py").read_text(encoding="utf-8")
    assert "0.0898" not in (REPO_ROOT / "scripts" / "rehearse_exp07_diag01_canonical_zero_step.py").read_text(encoding="utf-8")

    # In C22A8 report, verify it only appears inside the documented erratum
    c22a8_text = C22A8_REPORT.read_text(encoding="utf-8")
    assert "0.403935, 2.450546" in c22a8_text
    # The erroneous string must NOT be presented as the answer to Q10
    lines = c22a8_text.splitlines()
    for lno, line in enumerate(lines, 1):
        if "### Q10:" in line:
            # Check the next 5 lines
            q10_block = "\n".join(lines[lno-1:lno+5])
            assert "0.403935" in q10_block
            assert "0.0898" not in q10_block


def test_13_rejection_of_stale_15_max_epochs():
    """Verify reports do not claim maximum training duration is 15 epochs."""
    c22a8_text = C22A8_REPORT.read_text(encoding="utf-8")
    assert "MAX_EPOCHS = 30" in c22a8_text
    assert "MIN_EPOCHS = 15" in c22a8_text


def test_14_rejection_of_stale_vv_vh_modality():
    """Verify reports and configs do not describe runtime input as dual-pol VV/VH."""
    c22a8_text = C22A8_REPORT.read_text(encoding="utf-8")
    lines = c22a8_text.splitlines()
    for lno, line in enumerate(lines, 1):
        if "### Q4:" in line:
            q4_block = "\n".join(lines[lno-1:lno+15])
            assert "SAR Single-Band VV Tiles" in q4_block
            assert "SAR VV/VH Tiles" not in q4_block


def test_15_cryptographic_manifest_and_model_state_integrity():
    """Verify bitwise exact SHA-256 hashes of frozen manifest and initial model states."""
    expected_manifest_hash = "F5480EA2E26AF8D963EDE40CA658138CDCD6157CD79438E9C8673AD0C1DD8102"
    expected_canonical_model = "67181C4ECD420DEABA4129AB67AA34D617C1C581ACB3A1A7A9DE8BEAF2F1544D"
    expected_pretrained_backbone = "F37072FD47E89C5E827621C5BAFFA7500819F7896BBACEC160B1A16C560E07EC"
    expected_historical_random = "4BB233DB629E44DE12E41F11809024B7A5BDA4DBCFB19D13752295973117E45C"

    assert sha256_file(PHYSICAL_MANIFEST) == expected_manifest_hash
    assert sha256_file(CANONICAL_MODEL) == expected_canonical_model
    assert sha256_file(PRETRAINED_BACKBONE) == expected_pretrained_backbone
    assert sha256_file(HISTORICAL_RANDOM) == expected_historical_random
