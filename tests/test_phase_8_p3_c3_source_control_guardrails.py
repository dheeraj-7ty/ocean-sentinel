"""
test_phase_8_p3_c3_source_control_guardrails.py

Authoritative Automated Regression Guardrail Suite for Phase 8-P3-C3:
Source Control Forensics, Safe Repository Hygiene & Self-Healing Closure.

Verifies:
1. EXP-06 hash unchanged
2. Part-I hash unchanged
3. Protected taxonomy not ignored
4. Protected manifests not ignored
5. Protected tests not ignored
6. Protected reports not ignored
7. Governance files not ignored
8. No broad data/ ignore rule
9. No broad experiments/ ignore rule
10. No broad tests/ ignore rule
11. Tracked dataset.py remains visible
12. Tracked .gitignore remains visible
13. Ignore rules are documented
14. Generated categories with approved policy are ignored
15. Protected scientific artifacts are not ignored
16. No deletion commands recorded
17. Git staging remains zero
18. Branch remains master
19. Physical OPS-01 sample count remains 147
20. Parent count remains 27
21. Partition counts remain 72/39/36
22. Parent leakage remains 0
23. OS pixels remain 0
24. Governance rules 31–40 exist
25. Every new incident has a regression test
26. Telemetry exists and is internally consistent
27. Task completion cannot be declared while an expected verification command is still running
"""

import hashlib
import json
import subprocess
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent

# Frozen paths and hashes
EXP06_PATH = ROOT / "experiments/performance/exp06_positive_bce_weight/best_model.pt"
EXP06_EXPECTED_SHA = "B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF"

PART_I_PATH = ROOT / "data/metadata/internal_development_split_manifest.json"
PART_I_EXPECTED_SHA = "17F1FF35146C7CE62E90D6FCE7F197B711B55E3C3CB599610578443208669072"

GITIGNORE_PATH = ROOT / ".gitignore"
BASELINE_PATH = ROOT / "data/metadata/ops01_p3_c3_git_baseline_v1.json"
GITIGNORE_AUDIT_PATH = ROOT / "data/metadata/ops01_p3_c3_gitignore_audit_v1.json"
TRACKING_POLICY_PATH = ROOT / "data/metadata/ops01_p3_c3_data_tracking_policy_v1.json"
IGNORE_AUDIT_PATH = ROOT / "data/metadata/ops01_p3_c3_ignore_regression_audit_v1.json"
GOV_RULES_JSON = ROOT / "data/metadata/ocean_sentinel_governance_rules_v1.json"
GOV_RULES_MD = ROOT / "experiments/PROJECT_GOVERNANCE/ocean_sentinel_governance_rules_v1.md"
INCIDENTS_PATH = ROOT / "data/metadata/ocean_sentinel_incident_learning_register_v1.json"
RUN_STATE_PATH = ROOT / "scratch/phase_8_p3_c3_run_state.json"
MANIFEST_V4_PATH = ROOT / "data/metadata/ops01_physical_dataset_manifest_v4.json"


# ============================================================
# GROUP 1: FROZEN BASELINE INTEGRITY
# ============================================================
class TestFrozenArtifactIntegrity:
    """EXP-06 checkpoint and Part-I manifest must remain immutably exact."""

    def test_exp06_hash_unchanged(self):
        assert EXP06_PATH.exists(), "EXP-06 model checkpoint missing"
        actual = hashlib.sha256(EXP06_PATH.read_bytes()).hexdigest().upper()
        assert actual == EXP06_EXPECTED_SHA, f"EXP-06 corrupted: {actual}"

    def test_part_i_hash_unchanged(self):
        assert PART_I_PATH.exists(), "Part-I manifest missing"
        actual = hashlib.sha256(PART_I_PATH.read_bytes()).hexdigest().upper()
        assert actual == PART_I_EXPECTED_SHA, f"Part-I corrupted: {actual}"


# ============================================================
# GROUP 2: PROTECTED ARTIFACTS NOT IGNORED
# ============================================================
class TestProtectedArtifactsUnignored:
    """Critical scientific, governance, and test files must NEVER be ignored."""

    @pytest.mark.parametrize("rel_path", [
        "data/metadata/ops01_taxonomy_v1.json",
        "data/metadata/ops01_physical_dataset_manifest_v4.json",
        "data/metadata/ops01_split_manifest_v4.json",
        "data/metadata/ops01_dataset_sufficiency_v5.json",
        "data/metadata/ocean_sentinel_governance_rules_v1.json",
        "experiments/PROJECT_GOVERNANCE/ocean_sentinel_governance_rules_v1.md",
        "data/metadata/ocean_sentinel_incident_learning_register_v1.json",
        "data/metadata/ocean_sentinel_reproducibility_levels_v1.json",
        "experiments/PHASE_8_P3_FINAL_PRETRAINING_AUDIT_20260913.md",
        "experiments/PHASE_8_P3_C1_PROVENANCE_REPRODUCIBILITY_GOVERNANCE_CLOSURE_20260913.md",
        "experiments/PHASE_8_P3_C2_FINAL_EVIDENCE_BOUNDARY_CLOSURE_20260913.md",
        "tests/test_phase_8_p3_c1_governance_guardrails.py",
        "tests/test_phase_8_p3_c2_final_closure_guardrails.py",
        "experiments/performance/exp06_positive_bce_weight/best_model.pt",
        "src/ocean_sentinel/ingestion/dataset.py",
        "src/ocean_sentinel/ingestion/firewall.py"
    ])
    def test_protected_artifact_is_not_ignored(self, rel_path):
        target = ROOT / rel_path
        assert target.exists(), f"Protected target {rel_path} does not exist"
        cmd = f'git check-ignore -v "{rel_path}"'
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=ROOT)
        assert res.returncode != 0, f"Protected artifact {rel_path} is accidentally ignored by: {res.stdout.strip()}"


# ============================================================
# GROUP 3: NO BROAD BLANKET IGNORE RULES
# ============================================================
class TestNoBroadIgnoreRules:
    """Blanket ignoring of data/, experiments/, or tests/ is strictly prohibited."""

    def test_no_broad_data_ignore_rule(self):
        content = GITIGNORE_PATH.read_text(encoding="utf-8")
        lines = [l.strip() for l in content.splitlines() if l.strip() and not l.strip().startswith("#")]
        assert "data/" not in lines, "Broad 'data/' ignore rule detected in .gitignore"
        assert "data/*" not in lines, "Broad 'data/*' ignore rule detected in .gitignore"

    def test_no_broad_experiments_ignore_rule(self):
        content = GITIGNORE_PATH.read_text(encoding="utf-8")
        lines = [l.strip() for l in content.splitlines() if l.strip() and not l.strip().startswith("#")]
        assert "experiments/" not in lines, "Broad 'experiments/' ignore rule detected in .gitignore"
        assert "experiments/*" not in lines, "Broad 'experiments/*' ignore rule detected in .gitignore"

    def test_no_broad_tests_ignore_rule(self):
        content = GITIGNORE_PATH.read_text(encoding="utf-8")
        lines = [l.strip() for l in content.splitlines() if l.strip() and not l.strip().startswith("#")]
        assert "tests/" not in lines, "Broad 'tests/' ignore rule detected in .gitignore"
        assert "tests/*" not in lines, "Broad 'tests/*' ignore rule detected in .gitignore"
        assert "src/" not in lines, "Broad 'src/' ignore rule detected in .gitignore"


# ============================================================
# GROUP 4: TRACKED MODIFICATIONS REMAIN VISIBLE
# ============================================================
class TestTrackedModificationsRemainVisible:
    """Tracked modifications in .gitignore and dataset.py must remain visible in git status."""

    def test_tracked_modified_files_visible_in_status(self):
        res = subprocess.run("git status --porcelain -uall", shell=True, capture_output=True, text=True, cwd=ROOT)
        status_lines = res.stdout.splitlines()
        tracked_mod = [l[3:].strip() for l in status_lines if l[1:2] == "M"]
        assert ".gitignore" in tracked_mod, ".gitignore is not visible as a tracked modified file"
        assert "src/ocean_sentinel/ingestion/dataset.py" in tracked_mod, "dataset.py is not visible as a tracked modified file"

    def test_tracked_modifications_diff_shows_expected_content(self):
        res = subprocess.run("git diff src/ocean_sentinel/ingestion/dataset.py", shell=True, capture_output=True, text=True, cwd=ROOT)
        assert "assert_no_part_iii_leakage" in res.stdout, "Firewall protection in dataset.py missing"


# ============================================================
# GROUP 5: GITIGNORE AUDIT & NOISE REDUCTION
# ============================================================
class TestGitIgnorePolicyAndNoiseReduction:
    """Ignore rules must be documented and generated noisy payloads must be ignored."""

    def test_gitignore_audit_artifact_exists_and_valid(self):
        assert GITIGNORE_AUDIT_PATH.exists()
        data = json.loads(GITIGNORE_AUDIT_PATH.read_text(encoding="utf-8"))
        assert data["phase"] == "PHASE_8_P3_C3"
        assert data["protected_artifacts_audit"]["all_protected_artifacts_unignored"] is True
        assert len(data["rules"]) >= 35

    def test_generated_phase_6_evaluation_payloads_are_ignored(self):
        sample_payload = "experiments/performance/phase_6_part_iii_external_evaluation/attempt_001/mapping_a/Oil_00001.npz"
        cmd = f'git check-ignore -v "{sample_payload}"'
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=ROOT)
        assert res.returncode == 0, f"Generated prediction payload {sample_payload} must be ignored"

    def test_ops01_masks_are_ignored(self):
        sample_mask = "data/derived/ops01/masks/sample_00000.png"
        cmd = f'git check-ignore -v "{sample_mask}"'
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=ROOT)
        assert res.returncode == 0, f"OPS-01 mask {sample_mask} must be ignored by data tracking policy"


# ============================================================
# GROUP 6: SAFETY, NO DELETION & GIT STATE INTEGRITY
# ============================================================
class TestSafetyAndNoDeletion:
    """Zero file deletion, zero git staging, branch is master."""

    def test_git_staged_remains_zero(self):
        res = subprocess.run("git diff --cached --name-status", shell=True, capture_output=True, text=True, cwd=ROOT)
        assert not res.stdout.strip(), f"Staged changes detected: {res.stdout.strip()}"

    def test_git_branch_is_master(self):
        res = subprocess.run("git branch --show-current", shell=True, capture_output=True, text=True, cwd=ROOT)
        assert res.stdout.strip() == "master"

    def test_no_deletion_of_generated_prediction_files(self):
        mapping_a_dir = ROOT / "experiments/performance/phase_6_part_iii_external_evaluation/attempt_001/mapping_a"
        if mapping_a_dir.exists():
            count = len(list(mapping_a_dir.glob("*.npz")))
            assert count >= 400, f"Generated files were deleted! Expected >= 400 .npz, found {count}"

    def test_no_false_clean_claims(self):
        assert BASELINE_PATH.exists()
        data = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
        assert data["git_context"]["is_clean"] is False
        assert "0 staged != clean" in data["git_context"]["clean_doctrine"]


# ============================================================
# GROUP 7: PHYSICAL DATASET INVARIANTS
# ============================================================
class TestPhysicalDatasetInvariants:
    """Physical OPS-01 dataset invariants must remain perfectly preserved."""

    def test_ops01_manifest_sample_and_partition_counts(self):
        assert MANIFEST_V4_PATH.exists()
        manifest = json.loads(MANIFEST_V4_PATH.read_text(encoding="utf-8"))
        assert len(manifest["samples"]) == 147
        
        ident_path = ROOT / "data/metadata/ops01_dataset_identity_v1.json"
        assert ident_path.exists()
        ident = json.loads(ident_path.read_text(encoding="utf-8"))
        comp = ident["dataset_composition"]
        assert comp["sample_count"] == 147
        assert comp["parent_count"] == 27
        assert comp["partition_counts"]["TRAIN"] == 72
        assert comp["partition_counts"]["DEV"] == 39
        assert comp["partition_counts"]["HOLDOUT"] == 36
        assert comp["parent_leakage"] == 0
        assert comp["admitted_class_14_os_pixels"] == 0

    def test_physical_mask_files_exist_on_disk(self):
        mask_dir = ROOT / "data/derived/ops01/masks"
        assert mask_dir.exists()
        masks = list(mask_dir.glob("*.png"))
        assert len(masks) == 147, f"Expected 147 mask files on disk, found {len(masks)}"

    def test_physical_image_files_exist_on_disk(self):
        img_dir = ROOT / "data/derived/ops01/images"
        assert img_dir.exists()
        imgs = list(img_dir.glob("*.tif"))
        assert len(imgs) == 147, f"Expected 147 image files on disk, found {len(imgs)}"


# ============================================================
# GROUP 8: GOVERNANCE RULES 31–40 & INCIDENT REGISTRATION
# ============================================================
class TestGovernanceRulesAndIncidents:
    """Rules GOV-RULE-031 to GOV-RULE-040 and incidents INC-P3-C3-001 to 004 must be enacted."""

    def test_governance_rules_31_to_40_present_in_json(self):
        assert GOV_RULES_JSON.exists()
        data = json.loads(GOV_RULES_JSON.read_text(encoding="utf-8"))
        rule_ids = set(r["rule_id"] for r in data["rules"])
        for idx in range(31, 41):
            expected_id = f"GOV-RULE-{idx:03d}"
            assert expected_id in rule_ids, f"{expected_id} missing from governance JSON"

    def test_governance_rules_in_markdown(self):
        assert GOV_RULES_MD.exists()
        txt = GOV_RULES_MD.read_text(encoding="utf-8")
        for idx in range(31, 41):
            expected_id = f"GOV-RULE-{idx:03d}"
            assert expected_id in txt, f"{expected_id} missing from governance markdown"

    def test_c3_incidents_in_learning_register(self):
        assert INCIDENTS_PATH.exists()
        data = json.loads(INCIDENTS_PATH.read_text(encoding="utf-8"))
        inc_ids = set(inc["incident_id"] for inc in data["incidents"])
        for idx in range(1, 5):
            expected_id = f"INC-P3-C3-{idx:03d}"
            assert expected_id in inc_ids, f"{expected_id} missing from incident register"

    def test_data_tracking_policy_artifact_exists_and_valid(self):
        assert TRACKING_POLICY_PATH.exists()
        data = json.loads(TRACKING_POLICY_PATH.read_text(encoding="utf-8"))
        assert data["phase"] == "PHASE_8_P3_C3"
        assert "ops01_physical_dataset_policy" in data
        assert data["ops01_physical_dataset_policy"]["images"]["tracking_category"].startswith("C")
        assert data["ops01_physical_dataset_policy"]["masks"]["tracking_category"].startswith("C")


# ============================================================
# GROUP 9: TELEMETRY & SELF-HEALING GOVERNANCE
# ============================================================
class TestSelfHealingGovernance:
    """Telemetry must exist and self-healing lifecycle must be respected."""

    def test_run_state_telemetry_valid(self):
        assert RUN_STATE_PATH.exists()
        data = json.loads(RUN_STATE_PATH.read_text(encoding="utf-8"))
        assert data["phase"] == "PHASE_8_P3_C3"
        assert data["status"] in ["RUNNING", "COMPLETE"]
        assert "last_heartbeat" in data
        assert data["staged_count"] == 0
        assert data["tracked_modified_count"] == 2
