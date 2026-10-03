"""Tests for repository artifact policy and gitignore rules."""

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def is_ignored(path_str: str) -> bool:
    """Check if a path is ignored according to git."""
    res = subprocess.run(
        ["git", "check-ignore", "-q", path_str],
        cwd=str(REPO_ROOT),
    )
    return res.returncode == 0


def test_registered_checkpoint_binaries_are_ignored():
    # Verify explicitly registered checkpoint binaries are ignored
    registered_checkpoints = [
        "experiments/exp01_baseline/best_model.pt",
        "experiments/exp01_baseline/final_model.pt",
        "experiments/exp01_baseline/latest_checkpoint.pt",
        "experiments/archive/exp01_interrupted_20260906_135852/best_model.pt",
        "experiments/performance/exp02b_1_hard_negative_training_20260909_094500/kernel_output/exp02b_1_hard_negative_training/best_model.pt",
        "experiments/performance/exp02c_annealed_hard_negative_20260909_144000/best_model.pt",
        "experiments/performance/exp02c_annealed_hard_negative_20260909_144000/remote_training_output/best_model.pt",
    ]
    for c in registered_checkpoints:
        assert is_ignored(c), f"Expected {c} to be ignored"


def test_future_checkpoints_are_not_globally_suppressed():
    # A future checkpoint path that has NOT been explicitly registered must NOT be ignored
    future_checkpoint = "experiments/exp03_future_experiment/best_model.pt"
    assert not is_ignored(future_checkpoint), (
        f"Future checkpoint {future_checkpoint} was unexpectedly ignored! "
        "Artifact policy prohibits global *.pt or experiments/**/*.pt wildcard rules."
    )


def test_part_iii_prediction_payloads_are_ignored():
    assert is_ignored("experiments/performance/trujillo_part_iii_eval_20260911_exp01/mapping_a/Oil_00000.npz")
    assert is_ignored("experiments/performance/trujillo_part_iii_eval_20260911_exp01/mapping_a/Oil_00000.json")
    assert is_ignored("experiments/performance/trujillo_part_iii_eval_20260911_exp01/mapping_b/Oil_00000.npz")
    assert is_ignored("experiments/performance/trujillo_part_iii_eval_20260911_exp01/mapping_b/Oil_00000.json")
    assert is_ignored("experiments/performance/trujillo_part_iii_smoke_20260911_baseline_exp01/smoke_pass_01.npz")
    assert is_ignored("experiments/performance/phase_5a_diagnostics/forensic_panel.png")


def test_canonical_manifests_remain_visible():
    assert not is_ignored("data/metadata/trujillo_2024/spatial_split_manifest.json")
    assert not is_ignored("experiments/DATASET_MANIFEST_TRUJILLO_PART_III.json")
    assert not is_ignored("experiments/performance/trujillo_part_iii_eval_20260911_exp01/manifests/freeze_hashes.json")
    assert not is_ignored("experiments/performance/trujillo_part_iii_eval_20260911_exp01/manifests/trujillo_part_iii_pairing.json")
    assert not is_ignored("data/metadata/trujillo_2024/exp03_hard_negative_manifest.json")


def test_canonical_reports_and_metrics_remain_visible():
    assert not is_ignored("experiments/PHASE_5A_DEVELOPMENT_FAILURE_ANALYSIS_20260911.md")
    assert not is_ignored("experiments/PHASE_5B_HARD_NEGATIVE_TRAINING_CONTRACT_20260911.md")
    assert not is_ignored("experiments/ARTIFACT_REGISTRY.md")
    assert not is_ignored("experiments/REPOSITORY_ARTIFACT_INTEGRITY_AUDIT_20260911.md")
    assert not is_ignored("experiments/TRUJILLO_PART_III_PHASE_4D_FULL_EVALUATION_20260911.md")
    assert not is_ignored("experiments/performance/trujillo_part_iii_eval_20260911_exp01/metrics/metrics_mapping_a.json")
    assert not is_ignored("experiments/performance/trujillo_part_iii_eval_20260911_exp01/metrics/comparison_summary.json")
    assert not is_ignored("experiments/performance/phase_5a_failure_analysis/failure_analysis_report.json")


def test_source_code_and_lockfile_remain_visible():
    assert not is_ignored("src/ocean_sentinel/ingestion/firewall.py")
    assert not is_ignored("tests/test_part_iii_firewall.py")
    assert not is_ignored("tests/test_phase_5_guardrails.py")
    assert not is_ignored("uv.lock")


def test_canonical_protected_checkpoint_path_and_no_abbreviated_aliases():
    """Verify exact canonical checkpoint path exists and abbreviated aliases are prohibited."""
    canonical_ckpt = REPO_ROOT / "experiments" / "performance" / "exp06_positive_bce_weight" / "best_model.pt"
    assert canonical_ckpt.is_file(), f"Canonical checkpoint missing: {canonical_ckpt}"

    stale_alias_dir = REPO_ROOT / "experiments" / "performance" / "exp06"
    assert not stale_alias_dir.exists(), f"Stale alias directory must not exist: {stale_alias_dir}"

    # Verify no active documentation in root, docs/, experiments/, or scratch/ uses the abbreviated alias
    search_dirs = [REPO_ROOT, REPO_ROOT / "docs", REPO_ROOT / "experiments", REPO_ROOT / "scratch"]
    for search_dir in search_dirs:
        for md_file in search_dir.glob("*.md"):
            content = md_file.read_text(encoding="utf-8", errors="replace")
            for line in content.splitlines():
                if "exp06/best_model.pt" in line:
                    lower = line.lower()
                    # Skip lines in audit/telemetry records that explicitly document the prohibition, finding, repair, or historical drift
                    if any(term in lower for term in ["alias", "prohibit", "finding", "repair", "reconcil", "unauthorized", "verification", "drift", "re-introduce", "reintroduce"]):
                        continue
                    assert False, (
                        f"Prohibited abbreviated checkpoint alias 'exp06/best_model.pt' found in {md_file.name}: {line.strip()}. "
                        "Must use canonical path 'experiments/performance/exp06_positive_bce_weight/best_model.pt'."
                    )



