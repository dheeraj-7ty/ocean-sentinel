"""Tests for EXP-01 post-training recovery, safe checkpoint loading, and lifecycle hardening.

Covers:
1. TorchVersion-safe checkpoint loading (weights_only=True with allowlisted globals).
2. Correct epoch-4 checkpoint loading and state_dict integrity.
3. SHA-256 verification against checkpoint_integrity.json.
4. Windows/Unix process liveness check and safe stale-lock recovery.
5. --eval-only execution flow (no training, no training data loader, no weight mutation).
6. Threshold search uses validation data only and freezes selected threshold.
7. Terminal lifecycle states (COMPLETED, FAILED, INTERRUPTED).
8. Already-completed evaluation cleanly exits without duplicating work.
9. Byte-for-byte immutability of authoritative checkpoint artifacts.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import torch

from ocean_sentinel.ml.unet_resnet import ResNet34UNet, count_parameters
from scripts.train_exp01 import (
    acquire_run_lock,
    file_sha256,
    is_process_alive,
    release_run_lock,
    run_evaluation_and_reporting,
    safe_load_checkpoint,
    write_run_state,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
EXP01_DIR = REPO_ROOT / "experiments" / "exp01_baseline"
BEST_CHKPT = EXP01_DIR / "best_model.pt"
INTEGRITY_JSON = EXP01_DIR / "checkpoint_integrity.json"
HISTORY_JSON = EXP01_DIR / "history.json"


# ===========================================================================
# 1. Safe Checkpoint Loading Tests
# ===========================================================================


class TestSafeCheckpointLoading:
    """Test safe checkpoint loading with allowlisted PyTorch globals."""

    def test_safe_load_torch_version_allowlist(self) -> None:
        """Verify best_model.pt loads under weights_only=True without unpickling error."""
        if not BEST_CHKPT.exists():
            pytest.skip("EXP-01 best_model.pt not found on disk.")

        chkpt = safe_load_checkpoint(BEST_CHKPT, map_location="cpu")
        assert "model_state_dict" in chkpt
        assert "epoch" in chkpt
        assert "val_iou" in chkpt
        assert chkpt["epoch"] == 4
        assert abs(chkpt["val_iou"] - 0.71691) < 1e-4

    def test_epoch_4_checkpoint_model_integrity(self) -> None:
        """Verify epoch 4 checkpoint loads into ResNet34UNet with zero missing keys."""
        if not BEST_CHKPT.exists():
            pytest.skip("EXP-01 best_model.pt not found on disk.")

        chkpt = safe_load_checkpoint(BEST_CHKPT, map_location="cpu")
        model = ResNet34UNet(
            in_channels=2,
            num_classes=1,
            pretrained=False,
            adaptation_method="slice_variance_scaled",
        )
        counts = count_parameters(model)
        assert counts["total"] == 24_346_305
        assert counts["trainable"] == 24_346_305

        load_res = model.load_state_dict(chkpt["model_state_dict"], strict=True)
        assert len(load_res.missing_keys) == 0
        assert len(load_res.unexpected_keys) == 0

    def test_sha256_matches_integrity_record(self) -> None:
        """Verify actual SHA-256 matches checkpoint_integrity.json."""
        if not BEST_CHKPT.exists() or not INTEGRITY_JSON.exists():
            pytest.skip("EXP-01 checkpoint or integrity record missing.")

        actual_sha = file_sha256(BEST_CHKPT)
        integrity = json.loads(INTEGRITY_JSON.read_text(encoding="utf-8"))
        expected_sha = integrity["best_sha256"]
        assert actual_sha.upper() == expected_sha.upper()


# ===========================================================================
# 2. Process Liveness and Lock Safety Tests
# ===========================================================================


class TestProcessLivenessAndLock:
    """Test cross-platform process liveness checking and lock staleness recovery."""

    def test_current_process_is_alive(self) -> None:
        """Current process PID must be reported alive."""
        assert is_process_alive(os.getpid()) is True

    def test_nonexistent_process_is_dead(self) -> None:
        """Non-existent high PID must be reported dead."""
        assert is_process_alive(99999999) is False
        assert is_process_alive(-1) is False
        assert is_process_alive(0) is False

    def test_acquire_and_release_lock(self, tmp_path: Path) -> None:
        """Acquiring lock creates run.lock, releasing unlinks it."""
        lock = acquire_run_lock(tmp_path, "test_run_1")
        assert lock.exists()
        lock_data = json.loads(lock.read_text(encoding="utf-8"))
        assert lock_data["pid"] == os.getpid()

        release_run_lock(lock)
        assert not lock.exists()

    def test_stale_lock_recovery(self, tmp_path: Path) -> None:
        """Stale lock with a terminated PID is safely recovered."""
        lock_path = tmp_path / "run.lock"
        import socket

        fake_stale = {
            "run_id": "stale_run",
            "pid": 99999999,  # non-existent dead PID
            "machine": socket.gethostname(),
            "start_time_utc": "2026-09-01T00:00:00Z",
            "command_line": "python train.py",
        }
        lock_path.write_text(json.dumps(fake_stale), encoding="utf-8")

        new_lock = acquire_run_lock(tmp_path, "new_run_id")
        assert new_lock.exists()
        new_data = json.loads(new_lock.read_text(encoding="utf-8"))
        assert new_data["run_id"] == "new_run_id"
        assert new_data["pid"] == os.getpid()
        release_run_lock(new_lock)

    def test_live_process_lock_conflict_raises(self, tmp_path: Path) -> None:
        """Lock held by a live PID (e.g. current process) refuses duplicate acquisition."""
        lock_path = tmp_path / "run.lock"
        import socket

        existing = {
            "run_id": "live_run",
            "pid": os.getpid(),
            "machine": socket.gethostname(),
            "start_time_utc": "2026-09-01T00:00:00Z",
            "command_line": "python train.py",
        }
        lock_path.write_text(json.dumps(existing), encoding="utf-8")

        with patch("os.getpid", return_value=os.getpid() + 1):
            with pytest.raises(RuntimeError, match="Another EXP-01 process.*is currently alive"):
                acquire_run_lock(tmp_path, "duplicate_run")


# ===========================================================================
# 3. Lifecycle States & Result Artifacts Tests
# ===========================================================================


class TestLifecycleAndResults:
    """Test lifecycle state transitions and result artifact generation."""

    def test_write_run_state_atomic(self, tmp_path: Path) -> None:
        """write_run_state creates run_state.json with heartbeat."""
        state = {"status": "INITIALIZING", "epoch": 0}
        write_run_state(tmp_path, state)

        state_file = tmp_path / "run_state.json"
        assert state_file.exists()
        loaded = json.loads(state_file.read_text(encoding="utf-8"))
        assert loaded["status"] == "INITIALIZING"
        assert "last_heartbeat_utc" in loaded

    def test_run_evaluation_and_reporting_workflow(self, tmp_path: Path) -> None:
        """Test unified evaluation and reporting with small synthetic data."""
        from torch.utils.data import DataLoader, TensorDataset

        # Synthetic validation & test datasets (small tensors: [B, 2, 64, 64])
        val_x = torch.randn(4, 2, 64, 64)
        val_y = (torch.rand(4, 1, 64, 64) > 0.5).float()
        val_loader = DataLoader(TensorDataset(val_x, val_y), batch_size=2)

        test_x = torch.randn(4, 2, 64, 64)
        test_y = (torch.rand(4, 1, 64, 64) > 0.5).float()
        test_loader = DataLoader(TensorDataset(test_x, test_y), batch_size=2)

        # Mock model returning logits
        class DummyModel(torch.nn.Module):
            def forward(self, x: torch.Tensor) -> torch.Tensor:
                return torch.zeros(x.shape[0], 1, x.shape[2], x.shape[3])

        model = DummyModel()
        criterion = torch.nn.BCEWithLogitsLoss()

        lock_path = tmp_path / "run.lock"
        lock_path.write_text("{}", encoding="utf-8")
        run_state: dict = {"status": "EVALUATING", "run_id": "test"}

        mock_manifest = MagicMock()
        mock_manifest.normalization_stats = None

        fake_chkpt = tmp_path / "best_model.pt"
        fake_chkpt.write_bytes(b"fake_checkpoint_bytes")

        results = run_evaluation_and_reporting(
            model=model,
            eval_chkpt_path=fake_chkpt,
            eval_chkpt_sha="MOCK_SHA256",
            manifest=mock_manifest,
            val_loader=val_loader,
            test_loader=test_loader,
            criterion=criterion,
            device=torch.device("cpu"),
            use_amp=False,
            output_dir=tmp_path,
            run_id="test_run",
            config={"test_key": "val"},
            best_epoch=4,
            best_val_iou=0.71691,
            history_data=[{"epoch": 1, "duration_sec": 10.0, "throughput_samp_per_sec": 5.0}],
            run_state=run_state,
            lock_path=lock_path,
            param_counts={"total": 24346305, "trainable": 24346305},
        )

        assert results["evaluation_status"] == "COMPLETED"
        assert "threshold_selection" in results
        assert "test_evaluation" in results
        assert results["threshold_selection"]["selected_threshold"] is not None
        assert "threshold_candidates" in results["threshold_selection"]
        assert "threshold_metric_results" in results["threshold_selection"]

        results_file = tmp_path / "exp01_results.json"
        assert results_file.exists()

        state_file = tmp_path / "run_state.json"
        assert state_file.exists()
        saved_state = json.loads(state_file.read_text(encoding="utf-8"))
        assert saved_state["status"] == "COMPLETED"
        assert saved_state["selected_threshold"] is not None
        assert not lock_path.exists()

    def test_eval_only_exits_cleanly_if_already_completed(self, tmp_path: Path) -> None:
        """When exp01_results.json exists and status=COMPLETED, eval-only exits cleanly."""
        from scripts.train_exp01 import main

        results_file = tmp_path / "exp01_results.json"
        results_file.write_text('{"status": "ok"}', encoding="utf-8")
        state_file = tmp_path / "run_state.json"
        state_file.write_text('{"status": "COMPLETED"}', encoding="utf-8")

        test_args = [
            "train_exp01.py",
            "--output-dir",
            str(tmp_path),
            "--eval-only",
        ]
        with patch("sys.argv", test_args):
            # Should exit cleanly via return (no exception, no sys.exit)
            main()

        # Check lock was never created
        assert not (tmp_path / "run.lock").exists()

    def test_eval_only_does_not_load_training_data(self, tmp_path: Path) -> None:
        """--eval-only initializes VAL and TEST datasets but NEVER TRAIN dataset."""
        from ocean_sentinel.ingestion.split import SplitName

        # Create dummy checkpoint
        fake_chkpt = tmp_path / "best_model.pt"
        torch.save(
            {
                "model_state_dict": ResNet34UNet(
                    in_channels=2, num_classes=1, pretrained=False
                ).state_dict(),
                "epoch": 4,
                "val_iou": 0.71691,
            },
            fake_chkpt,
        )

        # Mock manifest
        mock_manifest = MagicMock()
        mock_manifest.normalization_stats = MagicMock()

        dataset_calls = []

        def mock_dataset_init(manifest, split, normalize=True, transform=None, *args, **kwargs):
            dataset_calls.append(split)
            mock_ds = MagicMock()
            mock_ds.__len__ = MagicMock(return_value=2)
            mock_ds.__getitem__ = MagicMock(
                return_value=(torch.zeros(2, 64, 64), torch.zeros(1, 64, 64))
            )
            return mock_ds

        test_args = [
            "train_exp01.py",
            "--output-dir",
            str(tmp_path),
            "--manifest",
            str(tmp_path / "dummy_manifest.json"),
            "--eval-only",
            "--num-workers",
            "0",
            "--device",
            "cpu",
        ]

        with (
            patch("sys.argv", test_args),
            patch("scripts.train_exp01.DatasetManifest.load", return_value=mock_manifest),
            patch("scripts.train_exp01.TrujilloTileDataset", side_effect=mock_dataset_init),
            patch("scripts.train_exp01.run_evaluation_and_reporting") as mock_eval_rep,
        ):
            from scripts.train_exp01 import main

            main()
            assert mock_eval_rep.called

        # Invariant: TRAIN split must NEVER have been loaded
        assert SplitName.TRAIN not in dataset_calls
        assert SplitName.VAL in dataset_calls
        assert SplitName.TEST in dataset_calls

    def test_evaluation_failure_records_failed_and_releases_lock(self, tmp_path: Path) -> None:
        """Unhandled error in eval-only mode produces status=FAILED and releases lock."""
        fake_chkpt = tmp_path / "best_model.pt"
        torch.save(
            {
                "model_state_dict": ResNet34UNet(
                    in_channels=2, num_classes=1, pretrained=False
                ).state_dict(),
                "epoch": 4,
            },
            fake_chkpt,
        )

        test_args = [
            "train_exp01.py",
            "--output-dir",
            str(tmp_path),
            "--eval-only",
            "--device",
            "cpu",
        ]

        with (
            patch("sys.argv", test_args),
            patch(
                "scripts.train_exp01.DatasetManifest.load",
                side_effect=RuntimeError("Manifest corrupted"),
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            from scripts.train_exp01 import main

            main()

        assert exc_info.value.code == 1
        state_file = tmp_path / "run_state.json"
        assert state_file.exists()
        saved_state = json.loads(state_file.read_text(encoding="utf-8"))
        assert saved_state["status"] == "FAILED"
        assert "Manifest corrupted" in saved_state["error"]
        assert "traceback" in saved_state
        # Lock must be released
        assert not (tmp_path / "run.lock").exists()


# ===========================================================================
# 4. Checkpoint Immutability Pre/Post Test
# ===========================================================================


class TestAuthoritativeArtifactImmutability:
    """Verify that authoritative EXP-01 artifacts are never mutated."""

    def test_authoritative_hashes_intact(self) -> None:
        """Verify best_model.pt and history.json match verified baseline hashes."""
        if not BEST_CHKPT.exists() or not HISTORY_JSON.exists():
            pytest.skip("EXP-01 files not found.")

        best_sha = file_sha256(BEST_CHKPT)
        hist_sha = file_sha256(HISTORY_JSON)

        assert best_sha == "9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699"
        assert hist_sha == "E2B5EB5229E2529E1659E77D285E93275015F58DEDCA5AF1F539E45544D5FCBA"
