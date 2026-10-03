"""Test suite for EXP-07-P0-C22-A.4: Canonical ImageNet Backbone Provisioning and Reconstruction.

Validates official pretrained weights, cryptographic verification, canonical state
reconstruction determinism, conv1 adaptation correctness, architectural invariant counts,
preservation of the non-canonical state, and readiness logic.
"""

import hashlib
import json
import os
from pathlib import Path
import pytest
import torch
import torch.nn as nn
from torchvision.models import resnet18, ResNet18_Weights

REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE_FILE = Path(os.path.expanduser("~/.cache/torch/hub/checkpoints/resnet18-f37072fd.pth"))
CANONICAL_STATE_FILE = REPO_ROOT / "data" / "ops02" / "initial_model_state_canonical.pt"
RANDOM_STATE_FILE = REPO_ROOT / "data" / "ops02" / "initial_model_state.pt"
MANIFEST_FILE = REPO_ROOT / "data" / "ops02" / "manifests" / "exp07_diag01_initialization_lineage_v1.json"
AUDIT_FILE = REPO_ROOT / "data" / "ops02" / "audits" / "ops02_c22a4_initialization_provisioning_v1.json"
INCIDENT_FILE = REPO_ROOT / "data" / "metadata" / "exp07_p0_c22a4_incident_register_v1.json"
TELEMETRY_FILE = REPO_ROOT / "scratch" / "exp07_p0_c22a4_run_state.json"

from ocean_sentinel.ml.exp07_reference import ResNet18UNet
from ocean_sentinel.ml.exp07_fingerprint import fingerprint_model_state_dict

EXPECTED_PRETRAINED_SHA256 = "F37072FD47E89C5E827621C5BAFFA7500819F7896BBACEC160B1A16C560E07EC"
EXPECTED_CANONICAL_SHA256 = "67181C4ECD420DEABA4129AB67AA34D617C1C581ACB3A1A7A9DE8BEAF2F1544D"
EXPECTED_CANONICAL_TENSOR_FP = "B472DBA86C0AA9CB1821B6C6CB172D8DCD93CE556AA256BDE931558D965F749C"
EXPECTED_RANDOM_SHA256 = "4BB233DB629E44DE12E41F11809024B7A5BDA4DBCFB19D13752295973117E45C"
EXPECTED_RANDOM_TENSOR_FP = "E9343B5DE995D2DD0985C62FC57FC9B154974732F48BF6CCA81F62CAA8C1FA7D"


def load_json(p: Path):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def test_official_weights_enum_and_filename_identity():
    """Verify official weight enum identity and expected filename."""
    weights_enum = ResNet18_Weights.IMAGENET1K_V1
    assert "IMAGENET1K_V1" in str(weights_enum)
    assert weights_enum.url == "https://download.pytorch.org/models/resnet18-f37072fd.pth"
    assert weights_enum.url.endswith("resnet18-f37072fd.pth")


def test_pretrained_artifact_existence_and_complete_sha256():
    """Verify official pretrained weights file exists locally with exact complete SHA256."""
    assert CACHE_FILE.exists(), f"Pretrained weights missing at {CACHE_FILE}"
    file_bytes = CACHE_FILE.read_bytes()
    assert len(file_bytes) == 46830571
    computed_sha256 = hashlib.sha256(file_bytes).hexdigest().upper()
    assert computed_sha256 == EXPECTED_PRETRAINED_SHA256
    # Verify the first 8 characters match the TorchVision filename hash identifier
    assert computed_sha256.lower().startswith("f37072fd")


def test_canonical_manifest_and_audit_exist_and_match():
    """Verify initialization lineage manifest and provisioning audit exist."""
    assert MANIFEST_FILE.exists()
    assert AUDIT_FILE.exists()
    assert INCIDENT_FILE.exists()

    manifest = load_json(MANIFEST_FILE)
    audit = load_json(AUDIT_FILE)

    assert manifest["pretrained_dependency"]["complete_pretrained_sha256"] == EXPECTED_PRETRAINED_SHA256
    assert audit["official_pretrained_dependency"]["complete_sha256"] == EXPECTED_PRETRAINED_SHA256
    assert audit["canonical_initial_state_artifact"]["artifact_sha256"] == EXPECTED_CANONICAL_SHA256


def test_canonical_state_artifact_and_strict_loading():
    """Verify canonical initial state file exists, matches SHA256, and strictly loads into ResNet18UNet."""
    assert CANONICAL_STATE_FILE.exists()
    can_bytes = CANONICAL_STATE_FILE.read_bytes()
    assert len(can_bytes) == 57356426
    assert hashlib.sha256(can_bytes).hexdigest().upper() == EXPECTED_CANONICAL_SHA256

    sd = torch.load(CANONICAL_STATE_FILE, map_location="cpu")
    assert len(sd) == 192

    # Instantiate model and strict load
    model = ResNet18UNet(in_channels=1, num_classes=12, pretrained=False, bn_momentum=0.05)
    model.load_state_dict(sd, strict=True)


def test_canonical_architecture_counts():
    """Verify exact architecture counts of the canonical initial state."""
    model = ResNet18UNet(in_channels=1, num_classes=12, pretrained=False, bn_momentum=0.05)
    sd = torch.load(CANONICAL_STATE_FILE, map_location="cpu")
    model.load_state_dict(sd, strict=True)

    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    buffers = list(model.named_buffers())
    float_buffers = sum(b.numel() for _, b in buffers if b.dtype in (torch.float32, torch.float64))
    int_buffers = sum(b.numel() for _, b in buffers if b.dtype in (torch.int64, torch.int32))
    total_elements = sum(v.numel() for v in sd.values())
    bn_count = sum(1 for m in model.modules() if isinstance(m, nn.BatchNorm2d))

    assert trainable_params == 14310860
    assert float_buffers == 11776
    assert int_buffers == 30
    assert (float_buffers + int_buffers) == 11806
    assert total_elements == 14322666
    assert bn_count == 30


def test_conv1_shape_and_adaptation_correctness():
    """Verify conv1 shape [64, 1, 7, 7] and exact channel-mean adaptation from pretrained weights."""
    sd = torch.load(CANONICAL_STATE_FILE, map_location="cpu")
    assert sd["conv1.weight"].shape == (64, 1, 7, 7)
    assert sd["conv1.weight"].dtype == torch.float32

    # Verify against raw pretrained checkpoint
    ckpt_sd = torch.load(CACHE_FILE, map_location="cpu")
    expected_conv1 = ckpt_sd["conv1.weight"].mean(dim=1, keepdim=True)
    assert torch.equal(sd["conv1.weight"], expected_conv1)


def test_unmodified_pretrained_layers_match_checkpoint():
    """Verify that unmodified backbone layers match the ImageNet checkpoint bitwise."""
    sd = torch.load(CANONICAL_STATE_FILE, map_location="cpu")
    ckpt_sd = torch.load(CACHE_FILE, map_location="cpu")

    # Check key layers across all 4 ResNet stages
    assert torch.equal(sd["layer1.0.conv1.weight"], ckpt_sd["layer1.0.conv1.weight"])
    assert torch.equal(sd["layer2.1.conv2.weight"], ckpt_sd["layer2.1.conv2.weight"])
    assert torch.equal(sd["layer3.0.conv1.weight"], ckpt_sd["layer3.0.conv1.weight"])
    assert torch.equal(sd["layer4.1.conv2.weight"], ckpt_sd["layer4.1.conv2.weight"])


def test_canonical_state_differs_from_old_random_state():
    """Verify canonical state differs completely from the old random state."""
    assert RANDOM_STATE_FILE.exists()
    sd_rand = torch.load(RANDOM_STATE_FILE, map_location="cpu")
    sd_canon = torch.load(CANONICAL_STATE_FILE, map_location="cpu")

    fp_rand = fingerprint_model_state_dict(sd_rand)
    fp_canon = fingerprint_model_state_dict(sd_canon)

    assert fp_rand == EXPECTED_RANDOM_TENSOR_FP
    assert fp_canon == EXPECTED_CANONICAL_TENSOR_FP
    assert fp_rand != fp_canon

    # Check that conv1 and layer1 are completely different
    assert not torch.equal(sd_rand["conv1.weight"], sd_canon["conv1.weight"])
    assert not torch.equal(sd_rand["layer1.0.conv1.weight"], sd_canon["layer1.0.conv1.weight"])


def test_deterministic_reconstruction_reproducibility():
    """Verify that independent reconstructions under seed 42 produce bitwise identical state dicts."""
    torch.manual_seed(42)
    m1 = ResNet18UNet(in_channels=1, num_classes=12, pretrained=True, bn_momentum=0.05)

    torch.manual_seed(42)
    m2 = ResNet18UNet(in_channels=1, num_classes=12, pretrained=True, bn_momentum=0.05)

    sd1 = m1.state_dict()
    sd2 = m2.state_dict()

    assert len(sd1) == len(sd2) == 192
    for k in sd1.keys():
        assert torch.equal(sd1[k], sd2[k]), f"Nondeterminism detected in tensor {k}"


def test_historical_random_artifact_remains_classified_non_canonical():
    """Verify that data/ops02/initial_model_state.pt is preserved and classified NON_CANONICAL."""
    rand_bytes = RANDOM_STATE_FILE.read_bytes()
    assert hashlib.sha256(rand_bytes).hexdigest().upper() == EXPECTED_RANDOM_SHA256

    manifest = load_json(MANIFEST_FILE)
    prev = manifest["initial_state_hashes"]
    assert prev["previous_non_canonical_state_file_sha256"] == EXPECTED_RANDOM_SHA256


def test_readiness_logic_advances_to_ready_for_next_preflight():
    """Verify that readiness verdict is READY_FOR_NEXT_PREFLIGHT (not READY_FOR_USER_AUTHORIZATION)."""
    audit = load_json(AUDIT_FILE)
    verdict = audit["readiness_decision"]["verdict"]
    assert verdict == "READY_FOR_NEXT_PREFLIGHT"
    assert verdict != "READY_FOR_USER_AUTHORIZATION"


def test_no_training_occurred_in_c22a4():
    """Verify zero training occurred, zero backward passes, and zero holdout access."""
    telemetry = load_json(TELEMETRY_FILE)
    assert telemetry["training_started"] is False
    assert telemetry["backward_executed"] is False
    assert telemetry["optimizer_step_executed"] is False
    assert telemetry["scheduler_step_executed"] is False
    assert telemetry["kaggle_started"] is False
    assert telemetry["holdout_access"] is False
    assert telemetry["part_iii_access"] is False
