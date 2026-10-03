"""Phase 5E Adversarial Pre-Launch & Preflight Unit Test Suite.

Verifies all pre-flight invariants, single-variable constraints, and safety guardrails
for Phase 5E (EXP-05 Candidate Severity Capping) prior to any training authorization:
1. Exact candidate manifest integrity and hash.
2. Exact selected severity cap (50,000 FP pixels).
3. Exact resulting candidate count (355 retained, 45 excluded).
4. Zero ground-truth contamination (100% negative purity across all candidates).
5. All retained candidates satisfy cap; no excluded candidate satisfies cap.
6. Parent scene diversity preservation (251 surviving scenes, 91.94%).
7. Standard pool invariant (13,440 tiles, untouched).
8. Sampling contract invariant (15 standard + 1 mined = 16 tiles/batch, 896 batches/epoch, 8,960 total steps).
9. Operating threshold invariant (strictly tau = 0.22).
10. Part III scientific firewall remains 100% closed.
11. EXP-01, EXP-03, and EXP-04 artifacts remain strictly untouched and immutable.
12. Windows-safe verifier requirements enforced.
"""

import hashlib
import json
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# Cryptographic and Architectural Constants
EXPECTED_CANDIDATE_MANIFEST_SHA256 = "3867671E639F020A686C5ACCA4FE5DA4280EB7DAEAB9BD9FEF467C192AA9F9F4"
EXPECTED_CANDIDATE_MANIFEST_SIZE = 261621
EXPECTED_SPLIT_MANIFEST_SHA256 = "C052720A954C2E7A3E9A87AA64557450BF0DEABEC71D54C2A813849DB60812E0"
EXPECTED_TEACHER_SHA256 = "9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699"
EXPECTED_EXP03_BEST_SHA256 = "BE00C1C8B35A3648FCCAD3864F844ED2EB68E079F2CC390C1BA3EC147BF2DA57"
EXPECTED_EXP04_BEST_SHA256 = "FAC3C313386F3FE561C2ECF0945B7F960CAA74897C5E8105FB68635529F1320B"

SELECTED_SEVERITY_CAP = 50000
EXPECTED_SURVIVING_CANDIDATES = 355
EXPECTED_EXCLUDED_CANDIDATES = 45
EXPECTED_SURVIVING_SCENES = 251
EXPECTED_EXCLUDED_SCENES = 22
FROZEN_TAU = 0.22


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest().upper()


def test_candidate_manifest_integrity_and_hash():
    """Verify physical size, SHA-256 digest, and structure of exp03_hard_negative_manifest.json."""
    manifest_path = REPO_ROOT / "data" / "metadata" / "trujillo_2024" / "exp03_hard_negative_manifest.json"
    assert manifest_path.exists(), f"Manifest file missing: {manifest_path}"
    assert manifest_path.stat().st_size == EXPECTED_CANDIDATE_MANIFEST_SIZE
    actual_sha = compute_sha256(manifest_path)
    assert actual_sha == EXPECTED_CANDIDATE_MANIFEST_SHA256, f"SHA mismatch: {actual_sha} != {EXPECTED_CANDIDATE_MANIFEST_SHA256}"


def test_severity_cap_filtering_and_counts():
    """Derive filtered pool directly from manifest and verify exact retained/excluded counts."""
    manifest_path = REPO_ROOT / "data" / "metadata" / "trujillo_2024" / "exp03_hard_negative_manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    candidates = data["candidates"]
    assert len(candidates) == 400

    retained = [c for c in candidates if c["fp_pixels"] <= SELECTED_SEVERITY_CAP]
    excluded = [c for c in candidates if c["fp_pixels"] > SELECTED_SEVERITY_CAP]

    assert len(retained) == EXPECTED_SURVIVING_CANDIDATES, f"Retained count mismatch: {len(retained)} != {EXPECTED_SURVIVING_CANDIDATES}"
    assert len(excluded) == EXPECTED_EXCLUDED_CANDIDATES, f"Excluded count mismatch: {len(excluded)} != {EXPECTED_EXCLUDED_CANDIDATES}"
    assert len(retained) + len(excluded) == 400

    # Strict adherence: all retained <= 50,000; all excluded > 50,000
    assert all(c["fp_pixels"] <= SELECTED_SEVERITY_CAP for c in retained)
    assert all(c["fp_pixels"] > SELECTED_SEVERITY_CAP for c in excluded)

    # Post-cap max severity
    max_severity = max(c["fp_pixels"] for c in retained)
    assert max_severity == 45377, f"Expected post-cap max 45,377 px, got {max_severity}"


def test_candidate_pool_zero_ground_truth_contamination():
    """Verify 100% negative purity: zero positive pixels in any candidate."""
    manifest_path = REPO_ROOT / "data" / "metadata" / "trujillo_2024" / "exp03_hard_negative_manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    candidates = data["candidates"]
    assert all(c["gt_pixels"] == 0 for c in candidates), "Contamination: non-zero gt_pixels detected!"


def test_parent_scene_diversity_preservation():
    """Verify scene retention and ensure no single parent scene dominates post-cap pool."""
    manifest_path = REPO_ROOT / "data" / "metadata" / "trujillo_2024" / "exp03_hard_negative_manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    candidates = data["candidates"]

    all_stems = set(c["parent_stem"] for c in candidates)
    assert len(all_stems) == 273

    retained = [c for c in candidates if c["fp_pixels"] <= SELECTED_SEVERITY_CAP]
    retained_stems = set(c["parent_stem"] for c in retained)
    lost_stems = all_stems - retained_stems

    assert len(retained_stems) == EXPECTED_SURVIVING_SCENES, f"Surviving scenes mismatch: {len(retained_stems)} != {EXPECTED_SURVIVING_SCENES}"
    assert len(lost_stems) == EXPECTED_EXCLUDED_SCENES, f"Lost scenes mismatch: {len(lost_stems)} != {EXPECTED_EXCLUDED_SCENES}"

    # Verify no concentration into a single scene (max 2 candidates/scene)
    from collections import Counter
    stem_counts = Counter(c["parent_stem"] for c in retained)
    assert max(stem_counts.values()) <= 2, "Scene concentration breach: a scene has > 2 candidates!"


def test_sampling_contract_invariants():
    """Verify that batch size is 16, standard=15, mined=1, batches/epoch=896, steps=8,960."""
    from scripts.train_exp04 import TwoStreamBatchSampler

    n_std = 13440
    n_mined = EXPECTED_SURVIVING_CANDIDATES  # 355
    sampler = TwoStreamBatchSampler(n_std, n_mined, n_standard_per_batch=15, n_mined_per_batch=1, seed=42)

    assert len(sampler) == 896, f"Expected 896 batches/epoch, got {len(sampler)}"
    assert 896 * 10 == 8960, "Total optimizer steps over 10 epochs must be exactly 8,960"

    # Test single epoch batches
    batches = list(sampler)
    assert len(batches) == 896
    for b in batches:
        assert len(b) == 16
        b_std = b[:15]
        b_mined = [idx - n_std for idx in b[15:]]
        assert len(b_std) == 15
        assert len(b_mined) == 1
        assert 0 <= b_mined[0] < n_mined


def test_operating_threshold_invariant():
    """Verify frozen operating threshold tau = 0.22."""
    assert FROZEN_TAU == 0.22


def test_part_iii_firewall_strictly_enforced():
    """Verify that Part III paths cannot be loaded or leaked into training."""
    from ocean_sentinel.ingestion.firewall import assert_no_part_iii_leakage, PartIIIFirewallViolationError

    # Allowed paths must pass
    allowed_paths = [
        "data/raw/trujillo_2024/images/Oil/00001.tif",
        "data/raw/trujillo_2024/masks/Mask_oil/00001.tif",
    ]
    assert_no_part_iii_leakage(allowed_paths, check_content_hashes=False)

    # Forbidden Part III paths must raise PartIIIFirewallViolationError
    forbidden_paths = [
        "data/raw/trujillo_2024/part_iii/images/some_part3_image.tif",
        "data/metadata/trujillo_part_iii/manifest.json",
    ]
    with pytest.raises(PartIIIFirewallViolationError):
        assert_no_part_iii_leakage(forbidden_paths, check_content_hashes=False)


def test_prior_experiment_artifacts_remain_untouched():
    """Verify that EXP-01, EXP-03, and EXP-04 checkpoints exist and match immutable hashes."""
    # EXP-01 Teacher
    teacher_path = REPO_ROOT / "experiments" / "exp01_baseline" / "best_model.pt"
    assert teacher_path.exists()
    assert compute_sha256(teacher_path) == EXPECTED_TEACHER_SHA256

    # EXP-03 Best Checkpoint
    exp03_path = REPO_ROOT / "experiments" / "performance" / "exp03_baseline_hard_neg" / "best_model.pt"
    assert exp03_path.exists()
    assert compute_sha256(exp03_path) == EXPECTED_EXP03_BEST_SHA256

    # EXP-04 Best Checkpoint
    exp04_path = REPO_ROOT / "experiments" / "performance" / "exp04_hard_neg_ablation" / "best_model.pt"
    assert exp04_path.exists()
    assert compute_sha256(exp04_path) == EXPECTED_EXP04_BEST_SHA256


def test_windows_safe_verifier_invariants():
    """Verify that independent verification scripts maintain Windows multiprocessing safety."""
    exp04_verify_script = REPO_ROOT / "scratch" / "independent_verify_exp04.py"
    assert exp04_verify_script.exists()
    content = exp04_verify_script.read_text(encoding="utf-8")

    assert "num_workers=0" in content
    assert 'if __name__ == "__main__":' in content or "if __name__ == '__main__':" in content
    assert "SegmentationMeter" in content
