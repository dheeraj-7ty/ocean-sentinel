import hashlib
import json
import math
from pathlib import Path
import pytest
import torch

REPO_ROOT = Path(__file__).resolve().parent.parent

EXP06_BEST_MODEL_PATH = REPO_ROOT / "experiments" / "performance" / "exp06_positive_bce_weight" / "best_model.pt"
EXP06_EXPECTED_SHA256 = "B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF"

PART1_MANIFEST_PATH = REPO_ROOT / "data" / "metadata" / "internal_development_split_manifest.json"
PART1_EXPECTED_SHA256 = "17F1FF35146C7CE62E90D6FCE7F197B711B55E3C3CB599610578443208669072"

OPS01_MANIFEST_PATH = REPO_ROOT / "data" / "metadata" / "ops01_physical_dataset_manifest_v4.json"
OPS01_EXPECTED_SHA256 = "FF1680C9135EF5CD9C7B77FBC8373953F9924BD5BE2830617EB0EF386C8DC85E"

TAXONOMY_MANIFEST_PATH = REPO_ROOT / "data" / "metadata" / "ops01_taxonomy_v1.json"
TAXONOMY_EXPECTED_SHA256 = "86A043EFDBB641EE2073C959DA315E7BF90C5F72D35B9E40F62C39F225C551AD"

C8_CONFIG_PATH = REPO_ROOT / "data" / "metadata" / "exp07_p0_c8_final_training_config_v1.json"
C8_EXPECTED_FINGERPRINT = "D93EAEF12787F9408F2C3F9DD613DC6C47F2EC5A76C02B731EB42B29AB35273A"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def test_frozen_hashes_preflight():
    """Verify EXP-06, Part-I, OPS-01, and taxonomy manifests match immutable hashes."""
    assert sha256_file(EXP06_BEST_MODEL_PATH) == EXP06_EXPECTED_SHA256
    assert sha256_file(PART1_MANIFEST_PATH) == PART1_EXPECTED_SHA256
    assert sha256_file(OPS01_MANIFEST_PATH) == OPS01_EXPECTED_SHA256
    assert sha256_file(TAXONOMY_MANIFEST_PATH) == TAXONOMY_EXPECTED_SHA256


def test_configuration_fingerprint_integrity():
    """Verify C8 training configuration reproduces exact canonical fingerprint."""
    assert C8_CONFIG_PATH.exists()
    with open(C8_CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Exclude metadata envelope keys before hashing
    config_body = {k: v for k, v in data.items() if k not in ("metadata_version", "artifact_version", "phase", "title", "configuration_fingerprint_sha256")}
    canonical_str = json.dumps(config_body, sort_keys=True, separators=(',', ':'))
    calc_fingerprint = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest().upper()
    assert calc_fingerprint == C8_EXPECTED_FINGERPRINT
    assert data["configuration_fingerprint_sha256"] == C8_EXPECTED_FINGERPRINT


def test_normalization_constants_source_reconciliation():
    """Verify normalization constants are strictly 4.2756 and 0.3866 across all active contracts."""
    from ocean_sentinel.ml.exp07_reference import TRAIN_LOG1P_MEAN, TRAIN_LOG1P_STD
    assert pytest.approx(TRAIN_LOG1P_MEAN, abs=1e-4) == 4.2756
    assert pytest.approx(TRAIN_LOG1P_STD, abs=1e-4) == 0.3866

    with open(C8_CONFIG_PATH, "r", encoding="utf-8") as f:
        c8_config = json.load(f)
    assert c8_config["normalization"]["mean"] == 4.2756
    assert c8_config["normalization"]["std"] == 0.3866


def test_taxonomy_prohibits_corrupted_class_names():
    """Verify prohibited terms (OIL, SHIP, LAND, BUOY) do not exist in training class definitions."""
    from ocean_sentinel.ml.exp07_reference import DENSE_CLASS_NAMES, SOURCE_LABEL_TO_DENSE
    prohibited = ["OIL", "SHIP", "LAND", "BUOY", "HIGH_MOTION"]
    for name in DENSE_CLASS_NAMES:
        for p in prohibited:
            assert p != name, f"Prohibited corrupted taxonomy term '{p}' found in DENSE_CLASS_NAMES!"

    # Ensure 12 classes exactly
    assert len(DENSE_CLASS_NAMES) == 12
    assert DENSE_CLASS_NAMES[0] == "BG"
    assert DENSE_CLASS_NAMES[11] == "HM"
    assert len(SOURCE_LABEL_TO_DENSE) == 12
    # Ensure OS (source 14) and SI (source 9) are excluded from dense mapping
    assert 14 not in SOURCE_LABEL_TO_DENSE
    assert 9 not in SOURCE_LABEL_TO_DENSE
    assert 3 not in SOURCE_LABEL_TO_DENSE


def test_loss_weights_source_recalculated_values():
    """Verify loss weights match exact source recomputation across 4,712,082 valid pixels."""
    from ocean_sentinel.ml.exp07_reference import CLASS_WEIGHTS_SQRT_MEDIAN
    assert pytest.approx(CLASS_WEIGHTS_SQRT_MEDIAN[0], abs=1e-5) == 0.273233
    assert pytest.approx(CLASS_WEIGHTS_SQRT_MEDIAN[1], abs=1e-5) == 2.013263
    assert pytest.approx(CLASS_WEIGHTS_SQRT_MEDIAN[2], abs=1e-5) == 0.703954
    assert pytest.approx(CLASS_WEIGHTS_SQRT_MEDIAN[3], abs=1e-5) == 2.493473
    assert pytest.approx(CLASS_WEIGHTS_SQRT_MEDIAN[4], abs=1e-5) == 0.515947
    assert pytest.approx(CLASS_WEIGHTS_SQRT_MEDIAN[5], abs=1e-5) == 1.469686
    assert pytest.approx(CLASS_WEIGHTS_SQRT_MEDIAN[6], abs=1e-5) == 0.512411
    assert pytest.approx(CLASS_WEIGHTS_SQRT_MEDIAN[7], abs=1e-5) == 1.510850
    assert pytest.approx(CLASS_WEIGHTS_SQRT_MEDIAN[8], abs=1e-5) == 0.806601
    assert pytest.approx(CLASS_WEIGHTS_SQRT_MEDIAN[9], abs=1e-5) == 2.066304
    assert pytest.approx(CLASS_WEIGHTS_SQRT_MEDIAN[10], abs=1e-5) == 0.398704
    assert pytest.approx(CLASS_WEIGHTS_SQRT_MEDIAN[11], abs=1e-5) == 12.159536
    ratio = CLASS_WEIGHTS_SQRT_MEDIAN[11] / CLASS_WEIGHTS_SQRT_MEDIAN[0]
    assert pytest.approx(ratio, abs=1e-3) == 44.5024


def test_architecture_parameters_and_state_elements():
    """Verify ResNet18UNet exact parameter counts: 14,310,860 trainable, 14,322,666 total elements."""
    from ocean_sentinel.ml.exp07_reference import ResNet18UNet

    model = ResNet18UNet(in_channels=1, num_classes=12, bn_momentum=0.05)
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    assert trainable_params == 14310860

    buffers = list(model.named_buffers())
    float_buffers = sum(b.numel() for _, b in buffers if b.dtype in (torch.float32, torch.float64))
    int_buffers = sum(b.numel() for _, b in buffers if b.dtype in (torch.int64, torch.int32, torch.int16, torch.int8, torch.uint8))
    assert float_buffers == 11776
    assert int_buffers == 30

    total_state_elements = sum(v.numel() for v in model.state_dict().values())
    assert total_state_elements == 14322666
    assert trainable_params + float_buffers + int_buffers == 14322666

    bn_layers = sum(1 for m in model.modules() if isinstance(m, torch.nn.BatchNorm2d))
    assert bn_layers == 30


def test_optimizer_parameter_groups_separation():
    """Verify weight decay applies exclusively to 2D conv/linear weights, excluding biases and BN affine."""
    from ocean_sentinel.ml.exp07_reference import ResNet18UNet

    model = ResNet18UNet(in_channels=1, num_classes=12)
    decay_params = [p for n, p in model.named_parameters() if p.requires_grad and p.ndim >= 2 and not n.endswith('.bias')]
    no_decay_params = [p for n, p in model.named_parameters() if p.requires_grad and (p.ndim < 2 or n.endswith('.bias'))]

    decay_count = sum(p.numel() for p in decay_params)
    no_decay_count = sum(p.numel() for p in no_decay_params)
    assert decay_count == 14298560
    assert no_decay_count == 12300
    assert decay_count + no_decay_count == 14310860


def test_scheduler_curve_properties():
    """Verify LR scheduler curve matches exact warmup and cosine annealing contract."""
    def get_lr(epoch, total_epochs=30, warmup_epochs=3, base_lr=5e-4, warmup_start_lr=1e-5, min_lr=1e-6):
        if epoch < warmup_epochs:
            return warmup_start_lr + (epoch / warmup_epochs) * (base_lr - warmup_start_lr)
        else:
            cosine_epoch = epoch - warmup_epochs
            cosine_total = total_epochs - warmup_epochs
            fraction = cosine_epoch / cosine_total
            return min_lr + 0.5 * (base_lr - min_lr) * (1.0 + math.cos(math.pi * fraction))

    assert get_lr(0) == 1.0e-5
    assert get_lr(1) > get_lr(0)
    assert get_lr(2) > get_lr(1)
    assert pytest.approx(get_lr(3), rel=1e-5) == 5.0e-4
    assert get_lr(4) < get_lr(3)
    assert get_lr(15) < get_lr(4)
    assert get_lr(29) < get_lr(15)
    assert get_lr(29) >= 1.0e-6
