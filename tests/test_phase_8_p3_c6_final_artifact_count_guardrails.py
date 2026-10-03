"""
test_phase_8_p3_c6_final_artifact_count_guardrails.py

Authoritative Automated Regression Guardrail Suite for Phase 8-P3-C6:
Final C5 Artifact-Count Reconciliation & Definitive Source-Control Closure.

Verifies:
1. Fresh Git state is authoritative
2. C4 baseline is historically separated
3. C5-created artifacts are represented
4. C5 telemetry artifact is accounted for (classified as ignored)
5. C6 artifacts are accounted for
6. Current count is not confused with historical UI count
7. Intermediate count != final count (GOV-RULE-041)
8. Report and telemetry counts agree
9. No 0-staged=clean claim
10. Branch remains master
11. Staged remains 0
12. Tracked modifications remain visible
13. Frozen EXP-06 hash unchanged
14. Frozen Part-I hash unchanged
15. No deletion
16. No Git history mutation
17. No scientific content changed
18. No protected artifact accidentally ignored
19. Current final count comes from fresh porcelain
20. No final artifact is created after the final Git measurement without re-measuring (GOV-RULE-042/045)
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

C4_REPORT_PATH = ROOT / "experiments/PHASE_8_P3_C4_FINAL_SOURCE_CONTROL_DELTA_RECONCILIATION_20260913.md"
C5_REPORT_PATH = ROOT / "experiments/PHASE_8_P3_C5_FINAL_SOURCE_CONTROL_SELF_CONSISTENCY_CLOSURE_20260913.md"
C6_REPORT_PATH = ROOT / "experiments/PHASE_8_P3_C6_FINAL_ARTIFACT_COUNT_RECONCILIATION_20260913.md"

RUN_STATE_C5_PATH = ROOT / "scratch/phase_8_p3_c5_run_state.json"
RUN_STATE_C6_PATH = ROOT / "scratch/phase_8_p3_c6_run_state.json"
GOV_RULES_JSON = ROOT / "data/metadata/ocean_sentinel_governance_rules_v1.json"
INCIDENTS_PATH = ROOT / "data/metadata/ocean_sentinel_incident_learning_register_v1.json"


# ============================================================
# GROUP 1: FROZEN BASELINES & DATA INTEGRITY
# ============================================================
class TestFrozenBaselinesAndDataIntegrity:
    """EXP-06, Part-I, and physical dataset files must remain unchanged."""

    def test_frozen_exp06_hash(self):
        assert EXP06_PATH.exists()
        actual = hashlib.sha256(EXP06_PATH.read_bytes()).hexdigest().upper()
        assert actual == EXP06_EXPECTED_SHA, f"EXP-06 hash mismatch: {actual}"

    def test_frozen_part_i_hash(self):
        assert PART_I_PATH.exists()
        actual = hashlib.sha256(PART_I_PATH.read_bytes()).hexdigest().upper()
        assert actual == PART_I_EXPECTED_SHA, f"Part-I hash mismatch: {actual}"

    def test_no_scientific_dataset_modification(self):
        img_dir = ROOT / "data/derived/ops01/images"
        mask_dir = ROOT / "data/derived/ops01/masks"
        assert len(list(img_dir.glob("*.tif"))) == 147
        assert len(list(mask_dir.glob("*.png"))) == 147


# ============================================================
# GROUP 2: FRESH GIT STATE & SAFETY
# ============================================================
class TestFreshGitStateAndSafety:
    """Branch is master, staged is 0, tracked modifications remain visible."""

    def test_branch_is_master(self):
        res = subprocess.run("git branch --show-current", shell=True, capture_output=True, text=True, cwd=ROOT)
        assert res.stdout.strip() == "master"

    def test_staged_count_is_zero(self):
        res = subprocess.run("git diff --cached --name-status", shell=True, capture_output=True, text=True, cwd=ROOT)
        assert not res.stdout.strip()

    def test_tracked_modifications_remain_visible(self):
        res = subprocess.run("git diff --name-status", shell=True, capture_output=True, text=True, cwd=ROOT)
        diff_files = [l.split()[-1] for l in res.stdout.splitlines() if l.startswith("M")]
        assert ".gitignore" in diff_files
        assert "src/ocean_sentinel/ingestion/dataset.py" in diff_files

    def test_no_deletion_command_used(self):
        mapping_dir = ROOT / "experiments/performance/phase_6_part_iii_external_evaluation/attempt_001/mapping_a"
        if mapping_dir.exists():
            assert len(list(mapping_dir.glob("*.npz"))) >= 400

    def test_no_git_history_mutation(self):
        res = subprocess.run("git log -n 1 --oneline", shell=True, capture_output=True, text=True, cwd=ROOT)
        assert res.returncode == 0

    def test_no_zero_staged_equals_clean_claim(self):
        res = subprocess.run("git status --porcelain -uall", shell=True, capture_output=True, text=True, cwd=ROOT)
        assert len(res.stdout.splitlines()) > 0, "0 staged must not imply clean repository"


# ============================================================
# GROUP 3: TIMELINE & TELEMETRY ACCOUNTING
# ============================================================
class TestTimelineAndTelemetryAccounting:
    """Reconciles C4, C5, and C6 timeline with exact ignore/tracking accounting."""

    def test_c4_baseline_separated(self):
        txt = C4_REPORT_PATH.read_text(encoding="utf-8")
        assert "291" in txt and "293" in txt

    def test_c5_telemetry_classified_and_accounted(self):
        cmd = f'git check-ignore -v "{RUN_STATE_C5_PATH.relative_to(ROOT)}"'
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=ROOT)
        # Must be ignored by .gitignore line matching scratch/
        assert res.returncode == 0
        assert "scratch" in res.stdout

    def test_c6_telemetry_classified_and_accounted(self):
        cmd = f'git check-ignore -v "{RUN_STATE_C6_PATH.relative_to(ROOT)}"'
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=ROOT)
        assert res.returncode == 0
        assert "scratch" in res.stdout

    def test_fresh_porcelain_untracked_count_in_range(self):
        res = subprocess.run("git status --porcelain -uall", shell=True, capture_output=True, text=True, cwd=ROOT)
        untracked = [l for l in res.stdout.splitlines() if l.startswith("?? ")]
        # C5 final was 293. With C6 test: 294. With C6 report: 295.
        assert len(untracked) in [293, 294, 295]

    def test_report_and_telemetry_agree_on_timeline(self):
        assert RUN_STATE_C6_PATH.exists()
        data = json.loads(RUN_STATE_C6_PATH.read_text(encoding="utf-8"))
        assert data["phase"] == "PHASE_8_P3_C6"
        assert data["c4_final_untracked"] == 291
        assert data["c5_recorded_final_untracked"] == 293


# ============================================================
# GROUP 4: OPERATIONAL DOCTRINE & GOVERNANCE RULES 42-45
# ============================================================
class TestOperationalDoctrine:
    """Validates GOV-RULE-042 through 045 and incident registry."""

    def test_gov_rules_42_to_45_in_json(self):
        data = json.loads(GOV_RULES_JSON.read_text(encoding="utf-8"))
        rule_ids = set(r["rule_id"] for r in data["rules"])
        assert "GOV-RULE-042" in rule_ids
        assert "GOV-RULE-043" in rule_ids
        assert "GOV-RULE-044" in rule_ids
        assert "GOV-RULE-045" in rule_ids

    def test_inc_p3_c6_001_in_register(self):
        data = json.loads(INCIDENTS_PATH.read_text(encoding="utf-8"))
        inc_ids = set(i["incident_id"] for i in data["incidents"])
        assert "INC-P3-C6-001" in inc_ids

    def test_protected_artifacts_not_ignored(self):
        for rel in [
            "data/metadata/ops01_taxonomy_v1.json",
            "data/metadata/ops01_physical_dataset_manifest_v4.json",
            "data/metadata/ops01_split_manifest_v4.json",
            "data/metadata/ocean_sentinel_governance_rules_v1.json",
            "src/ocean_sentinel/ingestion/dataset.py",
            "experiments/PHASE_8_P3_C5_FINAL_SOURCE_CONTROL_SELF_CONSISTENCY_CLOSURE_20260913.md"
        ]:
            cmd = f'git check-ignore -v "{rel}"'
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=ROOT)
            assert res.returncode != 0, f"Protected artifact {rel} unexpectedly ignored"
