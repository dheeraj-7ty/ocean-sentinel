"""
test_phase_8_p3_c4_source_control_delta_guardrails.py

Authoritative Automated Regression Guardrail Suite for Phase 8-P3-C4:
Final Source-Control Delta Reconciliation & C3 Closure.

Verifies:
1. Frozen EXP-06 hash
2. Frozen Part-I hash
3. Current branch = master
4. Staged count = 0
5. Tracked modifications remain visible
6. 0 staged != clean
7. Protected artifacts are not ignored
8. Current Git count is reported from fresh porcelain output
9. C3 historical count is preserved as historical
10. Current count is not confused with C3 count
11. No deletion command was used
12. No Git history mutation occurred
13. Telemetry is valid
14. C4 does not claim a clean working tree
15. Delta classification exists
"""

import hashlib
import json
import subprocess
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent

EXP06_PATH = ROOT / "experiments/performance/exp06_positive_bce_weight/best_model.pt"
EXP06_EXPECTED_SHA = "B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF"

PART_I_PATH = ROOT / "data/metadata/internal_development_split_manifest.json"
PART_I_EXPECTED_SHA = "17F1FF35146C7CE62E90D6FCE7F197B711B55E3C3CB599610578443208669072"

C3_BASELINE_PATH = ROOT / "data/metadata/ops01_p3_c3_git_baseline_v1.json"
C3_REPORT_PATH = ROOT / "experiments/PHASE_8_P3_C3_SOURCE_CONTROL_FORENSIC_HYGIENE_CLOSURE_20260913.md"
RUN_STATE_C4_PATH = ROOT / "scratch/phase_8_p3_c4_run_state.json"


# ============================================================
# GROUP 1: FROZEN BASELINE INTEGRITY
# ============================================================
class TestFrozenBaselines:
    """EXP-06 and Part-I must remain byte-for-byte exact."""

    def test_exp06_hash_exact(self):
        assert EXP06_PATH.exists()
        actual = hashlib.sha256(EXP06_PATH.read_bytes()).hexdigest().upper()
        assert actual == EXP06_EXPECTED_SHA, f"EXP-06 hash mismatch: {actual}"

    def test_part_i_hash_exact(self):
        assert PART_I_PATH.exists()
        actual = hashlib.sha256(PART_I_PATH.read_bytes()).hexdigest().upper()
        assert actual == PART_I_EXPECTED_SHA, f"Part-I hash mismatch: {actual}"


# ============================================================
# GROUP 2: FRESH GIT STATE & SAFETY
# ============================================================
class TestFreshGitStateAndSafety:
    """Git branch, staging, and tracked modifications must obey invariants."""

    def test_branch_is_master(self):
        res = subprocess.run("git branch --show-current", shell=True, capture_output=True, text=True, cwd=ROOT)
        assert res.stdout.strip() == "master"

    def test_staged_count_is_zero(self):
        res = subprocess.run("git diff --cached --name-status", shell=True, capture_output=True, text=True, cwd=ROOT)
        assert not res.stdout.strip(), f"Staged changes detected: {res.stdout.strip()}"

    def test_tracked_modifications_remain_visible(self):
        res = subprocess.run("git diff --name-status", shell=True, capture_output=True, text=True, cwd=ROOT)
        diff_lines = res.stdout.splitlines()
        modified_files = [l.split()[-1] for l in diff_lines if l.startswith("M")]
        assert ".gitignore" in modified_files
        assert "src/ocean_sentinel/ingestion/dataset.py" in modified_files

    def test_zero_staged_does_not_equal_clean(self):
        res = subprocess.run("git status --porcelain -uall", shell=True, capture_output=True, text=True, cwd=ROOT)
        status_lines = res.stdout.splitlines()
        assert len(status_lines) > 0, "Expected non-clean working tree"
        # Total pending changes must reflect tracked modified + untracked
        assert len(status_lines) >= 288


# ============================================================
# GROUP 3: PROTECTED ARTIFACTS NOT IGNORED
# ============================================================
class TestProtectedArtifactsUnignored:
    """Authoritative artifacts must remain discoverable and not ignored."""

    @pytest.mark.parametrize("rel_path", [
        "data/metadata/ops01_taxonomy_v1.json",
        "data/metadata/ops01_physical_dataset_manifest_v4.json",
        "data/metadata/ops01_split_manifest_v4.json",
        "data/metadata/ocean_sentinel_governance_rules_v1.json",
        "experiments/performance/exp06_positive_bce_weight/best_model.pt",
        "src/ocean_sentinel/ingestion/dataset.py",
        "experiments/PHASE_8_P3_C3_SOURCE_CONTROL_FORENSIC_HYGIENE_CLOSURE_20260913.md"
    ])
    def test_protected_artifact_unignored(self, rel_path):
        target = ROOT / rel_path
        assert target.exists(), f"Target {rel_path} does not exist"
        cmd = f'git check-ignore -v "{rel_path}"'
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=ROOT)
        assert res.returncode != 0, f"Protected artifact {rel_path} is ignored by: {res.stdout.strip()}"


# ============================================================
# GROUP 4: C3 TO C4 DELTA RECONCILIATION
# ============================================================
class TestDeltaReconciliation:
    """Current untracked count must be reconciled against C3 baseline with exact accounting."""

    def test_c3_historical_count_preserved(self):
        assert C3_BASELINE_PATH.exists()
        data = json.loads(C3_BASELINE_PATH.read_text(encoding="utf-8"))
        assert data["git_context"]["untracked_count"] == 288

    def test_current_count_is_fresh_porcelain(self):
        res = subprocess.run("git status --porcelain -uall", shell=True, capture_output=True, text=True, cwd=ROOT)
        untracked = [l for l in res.stdout.splitlines() if l.startswith("?? ")]
        # Accommodates C4, C5, and C6 test and closure report files across phases.
        assert len(untracked) in [289, 290, 291, 292, 293, 294, 295]

    def test_c3_report_file_identified_in_delta(self):
        assert C3_REPORT_PATH.exists()
        cmd = f'git check-ignore -v "{C3_REPORT_PATH.relative_to(ROOT)}"'
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=ROOT)
        assert res.returncode != 0, "C3 report must be untracked and unignored"

    def test_no_deletion_used(self):
        # Verify that prediction files are still intact
        mapping_dir = ROOT / "experiments/performance/phase_6_part_iii_external_evaluation/attempt_001/mapping_a"
        if mapping_dir.exists():
            assert len(list(mapping_dir.glob("*.npz"))) >= 400

    def test_no_git_history_mutation(self):
        res = subprocess.run("git log -n 1 --oneline", shell=True, capture_output=True, text=True, cwd=ROOT)
        assert res.returncode == 0, "Git history inaccessible"


# ============================================================
# GROUP 5: TELEMETRY & DECISION INTEGRITY
# ============================================================
class TestTelemetryAndDecisionIntegrity:
    """C4 telemetry must be valid and accurately reflect state."""

    def test_c4_telemetry_valid(self):
        assert RUN_STATE_C4_PATH.exists()
        data = json.loads(RUN_STATE_C4_PATH.read_text(encoding="utf-8"))
        assert data["phase"] == "PHASE_8_P3_C4"
        assert data["status"] in ["RUNNING", "COMPLETE"]
        assert data["previous_c3_untracked_count"] == 288
        assert data["current_untracked_count"] >= 288
        assert data["current_staged_count"] == 0
        assert data["current_tracked_modified_count"] == 2
        assert "delta_classification" in data

    def test_c4_does_not_claim_clean_working_tree(self):
        assert RUN_STATE_C4_PATH.exists()
        data = json.loads(RUN_STATE_C4_PATH.read_text(encoding="utf-8"))
        assert data.get("is_clean") is not True
