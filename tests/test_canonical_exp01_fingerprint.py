"""Regression tests locking canonical EXP-01 configuration against drift.

Mandatory verification for Gate 4 / Code Freeze:
Guarantees that canonical EXP-01 hyperparameters (AdamW lr=1e-4, wd=1e-2,
CosineAnnealingLR T_max=30, eta_min=1e-6) cannot silently drift or be overridden
by hallucinated configurations (e.g. lr=5e-4, CosineAnnealingWarmRestarts).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import torch

from ocean_sentinel.ml.canonical_exp01 import (
    CANONICAL_EARLY_STOPPING_PATIENCE,
    CANONICAL_MAX_EPOCHS,
    CANONICAL_MODEL_ARCHITECTURE,
    CANONICAL_OPTIMIZER_LR,
    CANONICAL_OPTIMIZER_WEIGHT_DECAY,
    CANONICAL_PHYSICAL_BATCH_SIZE,
    CANONICAL_SCHEDULER_CLASS,
    CANONICAL_SCHEDULER_ETA_MIN,
    CANONICAL_SCHEDULER_T_MAX,
    CANONICAL_TOTAL_PARAMETERS,
    CERTIFIED_BASELINE_HASHES,
    build_canonical_fingerprint_dict,
    verify_canonical_exp01_config,
)
from scripts.train_exp01 import build_arg_parser, file_sha256, safe_load_checkpoint

REPO_ROOT = Path(__file__).resolve().parent.parent
EXP01_BASELINE_DIR = REPO_ROOT / "experiments" / "exp01_baseline"


# ===========================================================================
# 1. Canonical Constants and Argument Parser Default Locks
# ===========================================================================

class TestCanonicalConstantsLock:
    """Verify that canonical constants are immutable and locked."""

    def test_canonical_hyperparameter_values(self) -> None:
        """Verify baseline values match certified experimental record."""
        assert CANONICAL_OPTIMIZER_LR == 1e-4, "Canonical EXP-01 LR must be 1e-4"
        assert CANONICAL_OPTIMIZER_WEIGHT_DECAY == 1e-2, "Canonical EXP-01 weight decay must be 1e-2"
        assert CANONICAL_SCHEDULER_CLASS == "CosineAnnealingLR", "Canonical scheduler must be CosineAnnealingLR"
        assert CANONICAL_SCHEDULER_T_MAX == 30, "Canonical T_max must be 30"
        assert CANONICAL_SCHEDULER_ETA_MIN == 1e-6, "Canonical eta_min must be 1e-6"
        assert CANONICAL_MAX_EPOCHS == 30, "Canonical max epochs must be 30"
        assert CANONICAL_EARLY_STOPPING_PATIENCE == 10, "Canonical early stopping patience must be 10"
        assert CANONICAL_PHYSICAL_BATCH_SIZE == 8, "Canonical physical batch size must be 8"
        assert CANONICAL_TOTAL_PARAMETERS == 24_346_305, "Canonical parameter count must be 24,346,305"

    def test_train_exp01_cli_defaults_match_canonical(self) -> None:
        """Verify that CLI defaults in scripts/train_exp01.py match canonical EXP-01."""
        parser = build_arg_parser()
        args = parser.parse_args([])

        assert args.lr == CANONICAL_OPTIMIZER_LR, (
            f"train_exp01.py default --lr drifted: found {args.lr}, expected {CANONICAL_OPTIMIZER_LR}"
        )
        assert args.weight_decay == CANONICAL_OPTIMIZER_WEIGHT_DECAY, (
            f"train_exp01.py default --weight-decay drifted: found {args.weight_decay}, expected {CANONICAL_OPTIMIZER_WEIGHT_DECAY}"
        )
        assert args.epochs == CANONICAL_MAX_EPOCHS, (
            f"train_exp01.py default --epochs drifted: found {args.epochs}, expected {CANONICAL_MAX_EPOCHS}"
        )
        assert args.eta_min == CANONICAL_SCHEDULER_ETA_MIN, (
            f"train_exp01.py default --eta-min drifted: found {args.eta_min}, expected {CANONICAL_SCHEDULER_ETA_MIN}"
        )
        assert args.patience == CANONICAL_EARLY_STOPPING_PATIENCE, (
            f"train_exp01.py default --patience drifted: found {args.patience}, expected {CANONICAL_EARLY_STOPPING_PATIENCE}"
        )
        assert args.batch_size == CANONICAL_PHYSICAL_BATCH_SIZE, (
            f"train_exp01.py default --batch-size drifted: found {args.batch_size}, expected {CANONICAL_PHYSICAL_BATCH_SIZE}"
        )


# ===========================================================================
# 2. Rejection of Hallucinated Configurations (Negative Tests)
# ===========================================================================

class TestDiscrepancyRejection:
    """Explicit negative testing: verify that hallucinated configurations are rejected."""

    def test_rejects_hallucinated_lr_5e_4(self) -> None:
        """verify_canonical_exp01_config must fail when presented with lr = 5e-4."""
        with pytest.raises(AssertionError) as exc_info:
            verify_canonical_exp01_config({"lr": 5e-4})
        err_msg = str(exc_info.value)
        assert "EXP-01 LR mismatch" in err_msg
        assert "0.0001" in err_msg or "1e-4" in err_msg

    def test_rejects_hallucinated_warm_restarts_scheduler(self) -> None:
        """verify_canonical_exp01_config must fail when presented with CosineAnnealingWarmRestarts."""
        with pytest.raises(AssertionError) as exc_info:
            verify_canonical_exp01_config({"scheduler": "CosineAnnealingWarmRestarts"})
        err_msg = str(exc_info.value)
        assert "EXP-01 scheduler mismatch" in err_msg
        assert "CosineAnnealingLR" in err_msg

    def test_rejects_hallucinated_max_epochs(self) -> None:
        """verify_canonical_exp01_config must fail on max_epochs != 30."""
        with pytest.raises(AssertionError) as exc_info:
            verify_canonical_exp01_config({"epochs": 50})
        assert "EXP-01 epochs mismatch" in str(exc_info.value)

    def test_rejects_hallucinated_architecture(self) -> None:
        """verify_canonical_exp01_config must fail on incorrect model architecture."""
        with pytest.raises(AssertionError) as exc_info:
            verify_canonical_exp01_config({"model": "DeepLabV3Plus"})
        assert "EXP-01 architecture mismatch" in str(exc_info.value)

    def test_accepts_valid_canonical_configuration(self) -> None:
        """verify_canonical_exp01_config must pass cleanly for true canonical configuration."""
        canonical_dict = {
            "lr": 1e-4,
            "weight_decay": 1e-2,
            "scheduler": "CosineAnnealingLR",
            "epochs": 30,
            "patience": 10,
            "eta_min": 1e-6,
            "batch_size": 8,
            "accum_steps": 1,
            "model": "ResNet34UNet",
            "seed": 42,
        }
        # Must not raise
        verify_canonical_exp01_config(canonical_dict)


# ===========================================================================
# 3. Certified Baseline Checkpoint & History Forensics
# ===========================================================================

@pytest.mark.real_data
class TestCertifiedBaselineArtifacts:
    """Forensic verification against the certified EXP-01 baseline artifacts."""

    def test_best_model_pt_internal_optimizer_and_scheduler_state(self) -> None:
        """Verify best_model.pt records initial_lr=1e-4 and CosineAnnealingLR state."""
        best_path = EXP01_BASELINE_DIR / "best_model.pt"
        if not best_path.exists():
            pytest.skip("best_model.pt not present")

        chkpt = safe_load_checkpoint(
            best_path, map_location="cpu", expected_sha256=CERTIFIED_BASELINE_HASHES["best_model.pt"]
        )
        assert chkpt["epoch"] == 4
        assert abs(chkpt["val_iou"] - 0.71691) < 1e-4

        # Optimizer forensics
        opt = chkpt["optimizer_state_dict"]
        assert len(opt["param_groups"]) == 1
        pg = opt["param_groups"][0]
        assert pg["initial_lr"] == 0.0001, f"Expected initial_lr=0.0001, got {pg['initial_lr']}"
        assert pg["weight_decay"] == 0.01, f"Expected weight_decay=0.01, got {pg['weight_decay']}"

        # Scheduler forensics
        sched = chkpt["scheduler_state_dict"]
        assert "T_max" in sched, "Missing T_max in scheduler state (proves CosineAnnealingLR)"
        assert sched["T_max"] == 30
        assert sched["eta_min"] == 1e-06
        assert sched["base_lrs"] == [0.0001]
        assert sched["last_epoch"] == 4
        # Proves CosineAnnealingWarmRestarts was NOT used
        assert "T_0" not in sched, "T_0 found in scheduler (would indicate WarmRestarts)"
        assert "T_mult" not in sched, "T_mult found in scheduler (would indicate WarmRestarts)"

    def test_latest_checkpoint_pt_internal_optimizer_and_scheduler_state(self) -> None:
        """Verify latest_checkpoint.pt records initial_lr=1e-4 and CosineAnnealingLR state."""
        latest_path = EXP01_BASELINE_DIR / "latest_checkpoint.pt"
        if not latest_path.exists():
            pytest.skip("latest_checkpoint.pt not present")

        chkpt = safe_load_checkpoint(
            latest_path, map_location="cpu", expected_sha256=CERTIFIED_BASELINE_HASHES["latest_checkpoint.pt"]
        )
        assert chkpt["epoch"] == 14

        opt = chkpt["optimizer_state_dict"]
        pg = opt["param_groups"][0]
        assert pg["initial_lr"] == 0.0001
        assert pg["weight_decay"] == 0.01

        sched = chkpt["scheduler_state_dict"]
        assert sched["T_max"] == 30
        assert sched["eta_min"] == 1e-06
        assert sched["base_lrs"] == [0.0001]
        assert sched["last_epoch"] == 14
        assert "T_0" not in sched
        assert "T_mult" not in sched

    def test_history_json_proves_smooth_cosine_decay_without_restarts(self) -> None:
        """Verify history.json decays smoothly from 1e-4 with zero warm restarts."""
        hist_path = EXP01_BASELINE_DIR / "history.json"
        if not hist_path.exists():
            pytest.skip("history.json not present")

        history = json.loads(hist_path.read_text(encoding="utf-8"))
        assert len(history) == 14

        # Epoch 1: ~9.973e-05
        assert abs(history[0]["learning_rate"] - 9.973e-05) < 1e-7
        # Epoch 4: ~9.572e-05
        assert abs(history[3]["learning_rate"] - 9.572e-05) < 1e-7

        # Monotonically non-increasing across all 14 epochs (proves no restarts occurred)
        lrs = [record["learning_rate"] for record in history]
        for i in range(len(lrs) - 1):
            assert lrs[i] >= lrs[i + 1], (
                f"Learning rate increased from epoch {i+1} to {i+2} ({lrs[i]} -> {lrs[i+1]}). "
                "Violates monotonic CosineAnnealingLR decay!"
            )


# ===========================================================================
# 4. Fingerprint Generator Verification
# ===========================================================================

class TestFingerprintGenerator:
    """Verify programmatic fingerprint generation matches baseline requirements."""

    def test_build_canonical_fingerprint_dict(self) -> None:
        """Verify generated fingerprint contains all certified fields."""
        fp = build_canonical_fingerprint_dict(REPO_ROOT)
        assert fp["experiment_name"] == "EXP-01"
        assert fp["experiment_revision"] == "Rev B"
        assert fp["optimizer"]["lr"] == 1e-4
        assert fp["optimizer"]["weight_decay"] == 1e-2
        assert fp["scheduler"]["class"] == "CosineAnnealingLR"
        assert fp["scheduler"]["T_max"] == 30
        assert fp["training"]["max_epochs"] == 30
        assert fp["training"]["physical_batch_size"] == 8
        assert fp["model"]["architecture"] == "ResNet34UNet"
        assert fp["model"]["total_parameters"] == 24_346_305
