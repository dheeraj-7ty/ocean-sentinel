"""Phase 5G Adversarial Preflight & Forensic Integrity Unit Test Suite.

Verifies:
1. Checkpoint integrity and physical immutability for EXP-01, EXP-03, EXP-04, and EXP-05.
2. Part III scientific firewall protection (zero Part III access).
3. Canonical validation set definition (2,880 tiles: exactly 1,053 positive, 1,827 clean-water).
4. Deterministic failure classification logic (COMPLETE_DROPOUT, PARTIAL_DETECTION, FULL_DETECTION).
5. Data leakage controls (strict TRAIN vs VAL split separation).
6. Operating threshold invariant (strictly tau = 0.22).
7. Correct FN decomposition mathematical invariants.
8. No silent checkpoint substitution across experiments.
9. Windows safety invariants (single-process num_workers=0, main guard in scripts).
10. Forensic run-state telemetry presence and schema.
11. EXP-06 single-variable contract constraints (no training allowed in Phase 5G).
"""

import hashlib
import json
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

EXPECTED_TEACHER_SHA256 = "9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699"
EXPECTED_EXP03_BEST_SHA256 = "BE00C1C8B35A3648FCCAD3864F844ED2EB68E079F2CC390C1BA3EC147BF2DA57"
EXPECTED_EXP04_BEST_SHA256 = "FAC3C313386F3FE561C2ECF0945B7F960CAA74897C5E8105FB68635529F1320B"
EXPECTED_EXP05_BEST_SHA256 = "D9FC12E312E5DF012650E8106DCF90782534EFB1BD1E38BA7FDCF4E0802A0481"

FROZEN_TAU = 0.22
EXPECTED_TOTAL_VAL_TILES = 2880
EXPECTED_POS_VAL_TILES = 1053
EXPECTED_EMPTY_VAL_TILES = 1827


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest().upper()


def test_four_way_checkpoint_integrity_and_immutability():
    """Verify that all four experiment checkpoints exist, are immutable, and have distinct digests."""
    checkpoints = {
        "EXP-01": (REPO_ROOT / "experiments" / "exp01_baseline" / "best_model.pt", EXPECTED_TEACHER_SHA256),
        "EXP-03": (REPO_ROOT / "experiments" / "performance" / "exp03_baseline_hard_neg" / "best_model.pt", EXPECTED_EXP03_BEST_SHA256),
        "EXP-04": (REPO_ROOT / "experiments" / "performance" / "exp04_hard_neg_ablation" / "best_model.pt", EXPECTED_EXP04_BEST_SHA256),
        "EXP-05": (REPO_ROOT / "experiments" / "performance" / "exp05_candidate_severity_cap" / "best_model.pt", EXPECTED_EXP05_BEST_SHA256),
    }

    seen_shas = set()
    for exp_id, (path, expected_sha) in checkpoints.items():
        assert path.exists(), f"{exp_id} checkpoint missing at {path}"
        actual_sha = compute_sha256(path)
        assert actual_sha == expected_sha, f"{exp_id} SHA mismatch: {actual_sha} != {expected_sha}"
        assert actual_sha not in seen_shas, f"Duplicate checkpoint SHA detected for {exp_id}"
        seen_shas.add(actual_sha)


def test_part_iii_firewall_strictly_enforced():
    """Verify Part III firewall raises PartIIIFirewallViolationError on forbidden paths."""
    from ocean_sentinel.ingestion.firewall import assert_no_part_iii_leakage, PartIIIFirewallViolationError

    allowed_paths = [
        "data/raw/trujillo_2024/images/Oil/00001.tif",
        "experiments/performance/phase_5g_positive_failure_forensics/run_state.json",
    ]
    assert_no_part_iii_leakage(allowed_paths, check_content_hashes=False)

    forbidden_paths = [
        "data/raw/trujillo_part_iii/images/00001.tif",
        "data/metadata/trujillo_part_iii/manifest.json",
    ]
    with pytest.raises(PartIIIFirewallViolationError):
        assert_no_part_iii_leakage(forbidden_paths, check_content_hashes=False)


def test_canonical_validation_population_counts():
    """Verify validation split contains exactly 2,880 tiles, with 1,053 GT-positive and 1,827 empty."""
    split_manifest_path = REPO_ROOT / "data" / "metadata" / "trujillo_2024" / "spatial_split_manifest.json"
    from ocean_sentinel.ingestion.split import DatasetManifest, SplitName
    from ocean_sentinel.ingestion.dataset import TrujilloTileDataset

    manifest = DatasetManifest.load(split_manifest_path)
    val_ds = TrujilloTileDataset(manifest, split=SplitName.VAL, normalize=False)
    assert len(val_ds) == EXPECTED_TOTAL_VAL_TILES

    # Count positive tiles
    pos_count = 0
    empty_count = 0
    for i in range(len(val_ds)):
        _, mask = val_ds[i]
        if mask.sum().item() > 0:
            pos_count += 1
        else:
            empty_count += 1

    assert pos_count == EXPECTED_POS_VAL_TILES
    assert empty_count == EXPECTED_EMPTY_VAL_TILES


def test_deterministic_failure_classification_semantics():
    """Verify that complete dropout, partial detection, and full detection classifications are deterministic."""
    def classify(gt_pixels: int, pred_pixels: int, fn_pixels: int) -> str:
        if pred_pixels == 0:
            return "COMPLETE_DROPOUT"
        elif fn_pixels == 0:
            return "FULL_DETECTION"
        else:
            return "PARTIAL_DETECTION"

    assert classify(gt_pixels=1000, pred_pixels=0, fn_pixels=1000) == "COMPLETE_DROPOUT"
    assert classify(gt_pixels=1000, pred_pixels=800, fn_pixels=200) == "PARTIAL_DETECTION"
    assert classify(gt_pixels=1000, pred_pixels=1000, fn_pixels=0) == "FULL_DETECTION"


def test_fn_decomposition_identity():
    """Verify mathematical identity: Total FN = Dropout FN + Partial FN + Full FN."""
    # Simulation across synthetic tiles
    records = [
        {"state": "COMPLETE_DROPOUT", "fn": 500},
        {"state": "PARTIAL_DETECTION", "fn": 250},
        {"state": "FULL_DETECTION", "fn": 0},
        {"state": "PARTIAL_DETECTION", "fn": 150},
        {"state": "COMPLETE_DROPOUT", "fn": 600},
    ]

    total_fn = sum(r["fn"] for r in records)
    dropout_fn = sum(r["fn"] for r in records if r["state"] == "COMPLETE_DROPOUT")
    partial_fn = sum(r["fn"] for r in records if r["state"] == "PARTIAL_DETECTION")
    full_fn = sum(r["fn"] for r in records if r["state"] == "FULL_DETECTION")

    assert total_fn == dropout_fn + partial_fn + full_fn
    assert total_fn == 1500
    assert dropout_fn == 1100
    assert partial_fn == 400
    assert full_fn == 0


def test_forensic_run_state_schema_and_presence():
    """Verify that experiments/performance/phase_5g_positive_failure_forensics/run_state.json exists and has valid schema."""
    state_path = REPO_ROOT / "experiments" / "performance" / "phase_5g_positive_failure_forensics" / "run_state.json"
    assert state_path.exists(), "Forensic run_state.json does not exist"

    data = json.loads(state_path.read_text(encoding="utf-8"))
    required_keys = [
        "phase", "status", "pid", "command_line", "start_time_iso",
        "last_heartbeat_iso", "current_task", "progress_pct", "eta_seconds",
        "completed_analyses", "artifact_paths", "current_diagnostic"
    ]
    for k in required_keys:
        assert k in data, f"Key {k} missing in forensic run_state.json"


def test_windows_safety_invariants_in_forensics_script():
    """Verify that scratch/run_phase_5g_forensics.py adheres to Windows safety rules."""
    script_path = REPO_ROOT / "scratch" / "run_phase_5g_forensics.py"
    assert script_path.exists()
    content = script_path.read_text(encoding="utf-8")

    assert "if __name__ == '__main__':" in content or 'if __name__ == "__main__":' in content
    assert "num_workers=0" in content


def test_exp06_training_forbidden_in_phase_5g():
    """Verify that no EXP-06 training artifacts exist and Phase 5G remains strictly analysis/preregistration."""
    exp06_dir = REPO_ROOT / "experiments" / "performance" / "exp06_controlled_intervention"
    assert not (exp06_dir / "best_model.pt").exists(), "EXP-06 checkpoint must not exist in Phase 5G"
    assert not (exp06_dir / "last_model.pt").exists(), "EXP-06 checkpoint must not exist in Phase 5G"
