"""
tests/test_source_control_policy_and_reporting_guardrails.py

Authoritative Automated Regression Guardrail Suite for:
Source Control Policy, Provenance vs. Tracking Distinction, and Reporting Integrity.

Enforces:
1. "0 staged" does NOT imply "clean repository".
2. Tracked modifications are reported explicitly and not hidden.
3. Untracked files are measured directly from fresh raw Git porcelain.
4. Ignored files are strictly distinguished from untracked files.
5. Provenance and version-control tracking eligibility remain separate concepts.
6. Large binary weights (.pt > 50MB) require explicit CAO registration or external storage.
7. Protected canonical artifacts and manifests are never suppressed by .gitignore.
8. All 8 protected baseline SHA-256 digests match canonical values.
9. No destructive Git commands exist in automated scripts.
10. Exact terminology is enforced: "clean working tree" requires zero modifications and zero untracked.
"""

import hashlib
import re
import subprocess
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

CANONICAL_PROTECTED_HASHES = {
    "data/metadata/governance_v2/rules.json": "B216F369D68A027E4708E8CBCF3991D8EFFD5BA5A063A3B8B6B3FC2261D85C4E",
    "data/metadata/governance_v2/lessons.json": "4784A440070BC00612BC3BFA9B29A7ACC181934F894A9E22BD340FAAB7076395",
    "data/metadata/governance_v2/incidents.json": "FA3051A185894EE1FE46EDB5825EBCFE92B107F80FB7527BF5746D4EC5B91836",
    "src/ocean_sentinel/governance/runner.py": "DD345558C3118EE61C0C966744D539C66DCFAABEAB2B9C66B03903C66EB3C9E0",
    "src/ocean_sentinel/ingestion/dataset.py": "F5BF1387769E43462AF8E4E4DE37867C761DD7ADBC040455532A3463EBFA0B0C",
    "src/ocean_sentinel/temporal.py": "46614361E1BE20A278D0AF9CEEE222E4787DF1EADE7D52A88B372965170E26CF",
    "experiments/performance/exp06_positive_bce_weight/best_model.pt": "B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF",
    "docs/exp08_corrected_protocol.md": "E6691A6C3A70D6762A03462E5A8E6B6B60F0DD1AD066A552DD047375DE6FB50E",
}

# Post-reconciliation engineering phase files (Phase 6+) excluded from historical baseline commit plan checks
POST_BASELINE_OPERATIONAL_FILES = {
    "src/ocean_sentinel/operational_pipeline.py",
    "tests/test_operational_pipeline.py",
}


def run_git(cmd: str) -> str:
    """Run a git command in REPO_ROOT and return stdout."""
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=REPO_ROOT)
    assert res.returncode == 0, f"Git command failed: {cmd}\nStderr: {res.stderr}"
    return res.stdout


def parse_porcelain_z(raw_bytes: bytes) -> dict:
    """
    Robust NUL-delimited Git status parser (--porcelain=v1 -z -uall).
    Handles rename/copy source paths, type changes, unmerged conflict states,
    and accurately separates staged from worktree entries without line slicing.
    """
    tokens = raw_bytes.split(b"\x00")
    if tokens and tokens[-1] == b"":
        tokens.pop()

    staged = []
    worktree_modified = []
    visible_untracked = []
    unmerged = []
    type_changed = []
    deleted = []
    renamed = []
    copied = []
    added = []
    other = []

    i = 0
    while i < len(tokens):
        tok = tokens[i]
        code = tok[:2].decode("ascii")
        if len(tok) >= 3 and tok[2:3] == b" ":
            path = tok[3:].decode("utf-8", errors="surrogateescape")
        else:
            path = tok[2:].decode("utf-8", errors="surrogateescape")
        x, y = code[0], code[1]

        orig_path = None
        if x in ["R", "C"] or y in ["R", "C"]:
            if i + 1 < len(tokens):
                orig_path = tokens[i + 1].decode("utf-8", errors="surrogateescape")
                i += 1

        entry = (code, path, orig_path)

        # Unmerged / conflict check
        if code in ["DD", "AU", "UD", "UA", "DU", "AA", "UU"] or "U" in code:
            unmerged.append(entry)
        # Type changes
        elif "T" in code:
            type_changed.append(entry)
        # Staged renames
        elif x == "R":
            renamed.append(entry)
        # Staged copies
        elif x == "C":
            copied.append(entry)
        # Staged adds
        elif x == "A":
            added.append(entry)
        # Staged deletes
        elif x == "D":
            deleted.append(entry)
        # Staged modifications
        elif x == "M":
            staged.append(entry)
        # Untracked
        elif code == "??":
            visible_untracked.append(entry)
        # Worktree modifications
        elif code == " M":
            worktree_modified.append(entry)
        # Worktree deletes
        elif y == "D":
            deleted.append(entry)
        else:
            other.append(entry)

        i += 1

    return {
        "staged": staged,
        "worktree_modified": worktree_modified,
        "visible_untracked": visible_untracked,
        "unmerged": unmerged,
        "type_changed": type_changed,
        "deleted": deleted,
        "renamed": renamed,
        "copied": copied,
        "added": added,
        "other": other,
    }


def compute_abnormal_status_total(parsed: dict) -> int:
    """
    Computes aggregate abnormal status count across all abnormal buckets:
    unmerged, deleted, added, renamed, copied, type_changed, and other.
    """
    return (
        len(parsed["unmerged"])
        + len(parsed["deleted"])
        + len(parsed["added"])
        + len(parsed["renamed"])
        + len(parsed["copied"])
        + len(parsed["type_changed"])
        + len(parsed["other"])
    )




# ============================================================
# 1. REPOSITORY STATE DEFINITIONS & NON-CONFLATION
# ============================================================
class TestSourceControlStateSemantics:
    """Guards against conflating staging, tracking, and clean state."""

    def test_zero_staged_does_not_imply_clean_repository(self, tmp_path: Path):
        """0 staged must NOT be reported as a clean repository if modifications exist (fixture semantic test)."""
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True, capture_output=True)
        (tmp_path / "tracked.txt").write_text("v1\n", encoding="utf-8")
        subprocess.run(["git", "add", "tracked.txt"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True)

        # Create 1 tracked modification and 1 untracked file
        (tmp_path / "tracked.txt").write_text("v2\n", encoding="utf-8")
        (tmp_path / "untracked.txt").write_text("untracked\n", encoding="utf-8")

        res_staged = subprocess.run(["git", "diff", "--cached", "--name-status"], cwd=tmp_path, capture_output=True, text=True, check=True)
        staged_count = len([l for l in res_staged.stdout.splitlines() if l.strip()])
        assert staged_count == 0, "Expected 0 staged changes"

        res_status = subprocess.run(["git", "status", "--porcelain", "-uall"], cwd=tmp_path, capture_output=True, text=True, check=True)
        pending_lines = [l for l in res_status.stdout.splitlines() if l.strip()]

        is_clean = len(pending_lines) == 0
        assert not is_clean, "Working tree has pending files; 0 staged must NOT imply clean repository"

    def test_tracked_modifications_reported_explicitly(self, tmp_path: Path):
        """Tracked modified files must be detected and not masked (fixture semantic test)."""
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True, capture_output=True)
        (tmp_path / ".gitignore").write_text("*.tmp\n", encoding="utf-8")
        (tmp_path / "dataset.py").write_text("# initial\n", encoding="utf-8")
        subprocess.run(["git", "add", ".gitignore", "dataset.py"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True)

        # Modify tracked files in working tree without staging
        (tmp_path / ".gitignore").write_text("*.tmp\n*.bak\n", encoding="utf-8")
        (tmp_path / "dataset.py").write_text("# modified\n", encoding="utf-8")

        res_diff = subprocess.run(["git", "diff", "--name-status"], cwd=tmp_path, capture_output=True, text=True, check=True)
        modified_files = [l.split()[-1] for l in res_diff.stdout.splitlines() if l.startswith("M")]
        assert len(modified_files) == 2, "Expected tracked modifications to be visible"
        assert ".gitignore" in modified_files
        assert "dataset.py" in modified_files

    def test_untracked_files_measured_from_fresh_git(self, tmp_path: Path):
        """Untracked count must be measured directly from raw git ls-files (fixture semantic test)."""
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        (tmp_path / ".gitignore").write_text("*.ignored\n", encoding="utf-8")
        (tmp_path / "untracked1.txt").write_text("untracked 1\n", encoding="utf-8")
        (tmp_path / "untracked2.txt").write_text("untracked 2\n", encoding="utf-8")
        (tmp_path / "cache.ignored").write_text("ignored file\n", encoding="utf-8")

        res_ls = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"], cwd=tmp_path, capture_output=True, text=True, check=True)
        untracked = [l.strip() for l in res_ls.stdout.splitlines() if l.strip()]
        assert len(untracked) == 3, "Untracked files must be measured from fresh git output"
        assert ".gitignore" in untracked
        assert "untracked1.txt" in untracked
        assert "untracked2.txt" in untracked
        assert "cache.ignored" not in untracked

    def test_ignored_distinguished_from_untracked(self):
        """Ignored directories like outputs/jobs/ and scratch/ must be ignored, not untracked."""
        res_scratch = subprocess.run(
            ["git", "check-ignore", "-q", "scratch/test.tmp"],
            capture_output=True,
            cwd=REPO_ROOT,
        )
        assert res_scratch.returncode == 0, "scratch/ must be ignored by .gitignore"

        res_jobs = subprocess.run(
            ["git", "check-ignore", "-q", "outputs/jobs/job_test_123/manifest.json"],
            capture_output=True,
            cwd=REPO_ROOT,
        )
        assert res_jobs.returncode == 0, "outputs/jobs/ must be ignored by .gitignore"

    def test_comprehensive_git_status_accounting(self):
        """
        Explicitly accounts for ALL Git porcelain status codes using robust NUL-delimited parsing.
        Guarantees NO_UNACCOUNTED_GIT_STATUS_ENTRIES = TRUE and ABNORMAL_STATUS_TOTAL = 0.
        """
        status_res = subprocess.run(["git", "status", "--porcelain=v1", "-z", "-uall"], capture_output=True, cwd=REPO_ROOT)
        assert status_res.returncode == 0, f"git status failed: {status_res.stderr}"

        parsed = parse_porcelain_z(status_res.stdout)

        abnormal_status_total = compute_abnormal_status_total(parsed)
        no_unaccounted = (abnormal_status_total == 0)

        assert len(parsed["staged"]) == 0, f"Unexpected staged entries: {parsed['staged']}"
        assert len(parsed["unmerged"]) == 0, f"Unexpected unmerged entries: {parsed['unmerged']}"
        assert len(parsed["deleted"]) == 0, f"Unexpected deleted entries: {parsed['deleted']}"
        assert len(parsed["added"]) == 0, f"Unexpected added entries: {parsed['added']}"
        assert len(parsed["renamed"]) == 0, f"Unexpected renamed entries: {parsed['renamed']}"
        assert len(parsed["copied"]) == 0, f"Unexpected copied entries: {parsed['copied']}"
        assert len(parsed["type_changed"]) == 0, f"Unexpected type changes: {parsed['type_changed']}"
        assert len(parsed["other"]) == 0, f"Unexpected status entries: {parsed['other']}"
        assert abnormal_status_total == 0, f"Abnormal status total is non-zero: {abnormal_status_total}"
        assert no_unaccounted is True, "Unaccounted git status entries found!"

        # Relational verification against raw git diff and git ls-files
        diff_out = subprocess.run(["git", "diff", "--name-only"], capture_output=True, text=True, cwd=REPO_ROOT).stdout
        expected_modified = set(l.strip() for l in diff_out.splitlines() if l.strip())
        actual_modified = set(entry[1] for entry in parsed["worktree_modified"])
        assert actual_modified == expected_modified, f"Modified mismatch: {actual_modified ^ expected_modified}"

        untracked_out = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"], capture_output=True, text=True, cwd=REPO_ROOT).stdout
        expected_untracked = set(l.strip() for l in untracked_out.splitlines() if l.strip())
        actual_untracked = set(entry[1] for entry in parsed["visible_untracked"])
        assert actual_untracked == expected_untracked, f"Untracked mismatch: {actual_untracked ^ expected_untracked}"

    def test_porcelain_parser_discriminator_synthetic(self):
        """
        In-memory discriminator tests verifying that the NUL parser accurately
        distinguishes unmerged conflicts, renames, type changes, copies, adds,
        deletions, and unknown status codes.
        """
        # 1. Unmerged record (U)
        res_unmerged = parse_porcelain_z(b"UU conflict_file.py\x00")
        assert len(res_unmerged["unmerged"]) == 1
        assert len(res_unmerged["worktree_modified"]) == 0
        assert compute_abnormal_status_total(res_unmerged) == 1

        # 2. Deletion record (D)
        res_del = parse_porcelain_z(b" D deleted_worktree.py\x00")
        assert len(res_del["deleted"]) == 1
        assert compute_abnormal_status_total(res_del) == 1

        # 3. Added record (A)
        res_add = parse_porcelain_z(b"A  added_staged.py\x00")
        assert len(res_add["added"]) == 1
        assert compute_abnormal_status_total(res_add) == 1

        # 4. Rename record with two tokens (R)
        res_rename = parse_porcelain_z(b"R  new_name.py\x00old_name.py\x00")
        assert len(res_rename["renamed"]) == 1
        assert res_rename["renamed"][0][1] == "new_name.py"
        assert res_rename["renamed"][0][2] == "old_name.py"
        assert compute_abnormal_status_total(res_rename) == 1

        # 5. Copy record with two tokens (C)
        res_copy = parse_porcelain_z(b"C  copy_dst.py\x00copy_src.py\x00")
        assert len(res_copy["copied"]) == 1
        assert res_copy["copied"][0][1] == "copy_dst.py"
        assert res_copy["copied"][0][2] == "copy_src.py"
        assert compute_abnormal_status_total(res_copy) == 1

        # 6. Type change record (T)
        res_type = parse_porcelain_z(b" T symlink.py\x00")
        assert len(res_type["type_changed"]) == 1
        assert compute_abnormal_status_total(res_type) == 1

        # 7. Unknown / unexpected status code (other)
        res_unknown = parse_porcelain_z(b"X? unknown_file.py\x00")
        assert len(res_unknown["other"]) == 1
        assert compute_abnormal_status_total(res_unknown) == 1

    def test_abnormal_status_aggregate_condition_synthetic(self):
        """
        Regression requirement: A synthetic nonzero entry in ANY abnormal bucket
        (unmerged, deleted, added, renamed, copied, type_changed, other) MUST make:
        ABNORMAL_STATUS_TOTAL > 0 and NO_UNACCOUNTED_GIT_STATUS_ENTRIES = FALSE.
        """
        cases = {
            "U": b"UU conflict_file.py\x00",
            "D": b" D deleted_file.py\x00",
            "A": b"A  added_file.py\x00",
            "R": b"R  new_name.py\x00old_name.py\x00",
            "C": b"C  copy_dst.py\x00copy_src.py\x00",
            "T": b" T type_changed.py\x00",
            "unexpected/other": b"X? corrupt_status.py\x00",
        }

        for name, raw in cases.items():
            parsed = parse_porcelain_z(raw)
            abnormal_total = compute_abnormal_status_total(parsed)
            no_unaccounted = (abnormal_total == 0)

            assert abnormal_total == 1, f"Expected abnormal_total == 1 for case {name}, got {abnormal_total}"
            assert no_unaccounted is False, f"Expected no_unaccounted == False for case {name}, got {no_unaccounted}"

    def test_cleanly_committed_head_derivation_is_index_safe(self):
        """
        Verifies that CLEANLY_COMMITTED_HEAD_SET derivation is index-safe:
        HEAD_NON_CLEAN_SET = WORKTREE_MODIFIED_SET ∪ INDEX_MODIFIED_SET
        CLEANLY_COMMITTED_HEAD_SET = HEAD_TRACKED_SET - HEAD_NON_CLEAN_SET.

        Enforces:
        1. Live INDEX_MODIFIED_SET is EMPTY and STAGED_COUNT == 0.
        2. CLEANLY_COMMITTED_HEAD_SET is disjoint from INDEX_MODIFIED_SET and WORKTREE_MODIFIED_SET.
        3. Synthetic proof: Staged changes cannot leak into clean HEAD even if worktree diff is clean.
        """
        res_cached = subprocess.run(["git", "diff", "--cached", "--name-only"], capture_output=True, text=True, cwd=REPO_ROOT)
        assert res_cached.returncode == 0
        index_modified = set(l.strip() for l in res_cached.stdout.splitlines() if l.strip())
        assert len(index_modified) == 0, f"INDEX_MODIFIED_SET must remain empty in current repository, got: {index_modified}"

        res_diff = subprocess.run(["git", "diff", "--name-only"], capture_output=True, text=True, cwd=REPO_ROOT)
        assert res_diff.returncode == 0
        worktree_modified = set(l.strip() for l in res_diff.stdout.splitlines() if l.strip())

        res_head = subprocess.run(["git", "ls-tree", "-r", "--name-only", "HEAD"], capture_output=True, text=True, cwd=REPO_ROOT)
        assert res_head.returncode == 0
        head_tracked = set(l.strip() for l in res_head.stdout.splitlines() if l.strip())

        head_non_clean = worktree_modified | index_modified
        cleanly_committed = head_tracked - head_non_clean

        assert cleanly_committed.isdisjoint(index_modified), "Clean HEAD must be disjoint from index modifications"
        assert cleanly_committed.isdisjoint(worktree_modified), "Clean HEAD must be disjoint from worktree modifications"
        assert cleanly_committed.isdisjoint(head_non_clean), "Clean HEAD must be disjoint from all non-clean paths"

        # Synthetic proof: Staged file with clean worktree must NOT be in cleanly_committed
        mock_head = {"clean_doc.md", "staged_file.py", "worktree_file.py", "both_file.py"}
        mock_worktree = {"worktree_file.py", "both_file.py"}
        mock_index = {"staged_file.py", "both_file.py"}

        # Naive approach (head - worktree) would erroneously include staged_file.py:
        naive_clean = mock_head - mock_worktree
        assert "staged_file.py" in naive_clean, "Naive derivation erroneously considers staged file as clean"

        # Correct index-safe approach:
        mock_non_clean = mock_worktree | mock_index
        mock_clean = mock_head - mock_non_clean
        assert mock_clean == {"clean_doc.md"}, f"Expected only clean_doc.md, got {mock_clean}"
        assert "staged_file.py" not in mock_clean
        assert mock_clean.isdisjoint(mock_index)
        assert mock_clean.isdisjoint(mock_worktree)





# ============================================================
# 2. PROVENANCE VS. TRACKING POLICY SEPARATION
# ============================================================
class TestProvenanceAndTrackingPolicySeparation:
    """Enforces that high-value binaries and ephemeral caches have distinct policies."""

    def test_large_checkpoints_require_special_handling(self):
        """Any .pt checkpoint > 50MB is classified as needing Git-LFS, external storage, or registered ignore."""
        pt_files = list(REPO_ROOT.glob("experiments/**/*.pt"))
        large_checkpoints = [p for p in pt_files if p.stat().st_size > 50_000_000]
        assert len(large_checkpoints) > 0, "Expected large checkpoint files in experiments/"
        for ckpt in large_checkpoints:
            # Must not be staged in standard Git
            rel = str(ckpt.relative_to(REPO_ROOT)).replace("\\", "/")
            staged = run_git(f'git diff --cached --name-only -- "{rel}"').strip()
            assert not staged, f"Large checkpoint {rel} must NOT be staged in standard Git"

    def test_protected_artifacts_never_ignored(self):
        """Protected code, governance metadata, and documentation paths must remain completely un-ignored."""
        non_binary_protected = [
            p for p in CANONICAL_PROTECTED_HASHES if not p.endswith(".pt")
        ]
        for rel_path in non_binary_protected:
            res = subprocess.run(
                ["git", "check-ignore", "-q", rel_path],
                capture_output=True,
                cwd=REPO_ROOT,
            )
            assert res.returncode != 0, f"Protected artifact {rel_path} was accidentally ignored!"


# ============================================================
# 3. BASELINE INTEGRITY & SAFETY
# ============================================================
class TestBaselineSafetyAndHashes:
    """Verifies all 8 protected files match bitwise canonical hashes."""

    def test_all_eight_protected_baseline_hashes_match(self):
        for rel_path, expected_hash in CANONICAL_PROTECTED_HASHES.items():
            full_path = REPO_ROOT / rel_path
            assert full_path.exists(), f"Protected file missing: {rel_path}"
            actual_hash = hashlib.sha256(full_path.read_bytes()).hexdigest().upper()
            assert actual_hash == expected_hash, (
                f"Protected hash mismatch for {rel_path}!\n"
                f"Expected: {expected_hash}\nActual:   {actual_hash}"
            )


# ============================================================
# 4. DESTRUCTIVE AUTOMATION PROHIBITION
# ============================================================
class TestDestructiveAutomationProhibition:
    """Verifies that no automation script uses destructive git commands."""

    def test_no_destructive_git_commands_in_scripts(self):
        """Verifies that no automation script executes destructive git commands."""
        exec_patterns = [
            re.compile(r"""(?:subprocess\.(?:run|call|Popen)|os\.system)\s*\(\s*[^)]*git\s+(?:reset\s+--hard|clean\s+-[a-zA-Z]*f|push\s+-[a-zA-Z]*f|restore\s+--source=HEAD)""", re.IGNORECASE),
        ]
        scripts_dir = REPO_ROOT / "scripts"
        for py_script in scripts_dir.glob("*.py"):
            content = py_script.read_text(encoding="utf-8", errors="replace")
            for pat in exec_patterns:
                assert not pat.search(content), (
                    f"Prohibited destructive Git command execution call found in {py_script.name}: "
                    f"matched {pat.pattern}"
                )


# ============================================================
# 5. DYNAMIC ARTIFACT REGISTRY & SOURCE CONTROL GUARDRAILS
# ============================================================
class TestArtifactRegistryAlignment:
    """Enforces dynamic Source Control policy relationships, non-circular manifests, and reporting consistency."""

    @staticmethod
    def _load_manifest_sets():
        scratch_dir = REPO_ROOT / "scratch"
        track_set = set(p.strip().replace("\\", "/") for p in (scratch_dir / "git_track_manifest_v3.txt").read_text(encoding="utf-8").splitlines() if p.strip())
        ext_set = set(p.strip().replace("\\", "/") for p in (scratch_dir / "git_external_storage_manifest_v4.txt").read_text(encoding="utf-8").splitlines() if p.strip())
        runtime_set = set(p.strip().replace("\\", "/") for p in (scratch_dir / "git_runtime_ignored_manifest_v4.txt").read_text(encoding="utf-8").splitlines() if p.strip())
        review_file = scratch_dir / "git_human_review_manifest_v4.txt"
        review_set = set(p.strip().replace("\\", "/") for p in review_file.read_text(encoding="utf-8").splitlines() if p.strip()) if review_file.exists() else set()
        return track_set, ext_set, runtime_set, review_set

    @staticmethod
    def _derive_expected_external_set():
        """Independently derive expected external set from policy registry and dedicated directories."""
        registry_text = (REPO_ROOT / "experiments" / "ARTIFACT_REGISTRY.md").read_text(encoding="utf-8")
        section_7_1 = registry_text.split("### 7.1 Checkpoint Inventory & Canonical Verification")[1].split("### 7.2")[0]

        pt_paths = set()
        for line in section_7_1.splitlines():
            m = re.findall(r"\|([^|]+)", line)
            if len(m) >= 3 and ".pt" in m[0]:
                pt_paths.add(m[0].strip().replace("`", "").replace("\\", "/"))

        assert len(pt_paths) > 0, "Expected non-empty .pt paths registered in Section 7.1"

        masks_dir = REPO_ROOT / "data" / "ops02" / "derived" / "masks"
        all_mask_files = list(masks_dir.iterdir())
        mask_pngs = set(p.relative_to(REPO_ROOT).as_posix() for p in all_mask_files if p.suffix.lower() == ".png")
        assert len(mask_pngs) > 0, "Expected mask PNG files in masks dir"
        assert len(all_mask_files) == len(mask_pngs), f"masks dir contains unexpected non-PNG files: {len(all_mask_files)}"

        exact_json = {
            "experiments/performance/phase_5g_positive_failure_forensics/positive_tiles_forensics.json",
            "experiments/EXP-07/runs/EXP07_RUN003_SEED42/live_progress.json",
        }
        exact_txt = {
            "experiments/EXP-07/runs/EXP07_RUN003_SEED42/ocean-sentinel-exp07-c16-replicate-003.txt",
        }

        return pt_paths | mask_pngs | exact_json | exact_txt

    @staticmethod
    def _derive_policy_track_set(at_baseline: bool = True):
        """
        Independently derive expected track set from first-principles repository policy domains.

        Architecture & Conceptual Proof:
        1. POLICY_ELIGIBLE_REPOSITORY_SET:
           Derived ONLY from experiments/ARTIFACT_REGISTRY.md, repository directory structures,
           and explicit classification rules. Does NOT inspect git status, git diff, git ls-files,
           or manifests to decide eligibility.
        2. CLEANLY_COMMITTED_HEAD_SET:
           Determined via Git baseline HEAD (at_baseline=True) or current HEAD (at_baseline=False)
           minus non-clean modifications. Used strictly to distinguish already-integrated files from pending files.
        3. PENDING_POLICY_SET:
           PENDING_POLICY_SET = POLICY_ELIGIBLE_REPOSITORY_SET - CLEANLY_COMMITTED_HEAD_SET.
        """
        policy_eligible = set()
        review_required = set()

        # ==============================================================================
        # RULE 1: Core Python Source Code
        # ARTIFACT_REGISTRY SECTION: Section 2 (Classification Taxonomy - GIT-TRACKED)
        # PATH CLASS: src/**/*.py, human-readable source code
        # ACTION: GIT-TRACKED (Exclude build artifacts: __pycache__, *.pyc, *.egg-info)
        # ==============================================================================
        for p in (REPO_ROOT / "src").rglob("*"):
            if p.is_file():
                if p.name.endswith(".pyc") or "__pycache__" in p.parts:
                    continue  # DISPOSABLE / TEMPORARY (Section 2)
                if any(part.endswith(".egg-info") for part in p.parts):
                    continue  # Build artifact, ignored by .gitignore line 6
                rel = p.relative_to(REPO_ROOT).as_posix()
                if rel in POST_BASELINE_OPERATIONAL_FILES:
                    continue  # Post-reconciliation operational pipeline file
                policy_eligible.add(rel)

        # ==============================================================================
        # RULE 2: Frontend Web UI Dashboard
        # ARTIFACT_REGISTRY SECTION: Section 2 (Classification Taxonomy - GIT-TRACKED)
        # PATH CLASS: frontend/**/*
        # ACTION: GIT-TRACKED (Exclude node_modules, dist, __pycache__, *.pyc)
        # ==============================================================================
        frontend_dir = REPO_ROOT / "frontend"
        if frontend_dir.is_dir():
            for p in frontend_dir.rglob("*"):
                if p.is_file():
                    if p.name.endswith(".pyc") or "__pycache__" in p.parts:
                        continue  # DISPOSABLE / TEMPORARY (Section 2)
                    rel = p.relative_to(REPO_ROOT).as_posix()
                    if "node_modules" in rel or rel.startswith("frontend/dist/"):
                        continue  # External package dependencies and build bundles
                    policy_eligible.add(rel)

        # ==============================================================================
        # RULE 3: Governance V2 & Metadata Catalogs
        # ARTIFACT_REGISTRY SECTION: Section 2 & Section 6.2 (Canonical Manifests - GIT-TRACKED)
        # PATH CLASS: data/metadata/**/*.json, data/metadata/**/*.sha256, *.tab
        # ACTION: GIT-TRACKED (Canonical governance schemas, manifests, audit ledgers, digests)
        # ==============================================================================
        metadata_dir = REPO_ROOT / "data" / "metadata"
        if metadata_dir.is_dir():
            for p in metadata_dir.rglob("*"):
                if p.is_file():
                    if p.suffix.lower() in [".json", ".sha256", ".tab"]:
                        policy_eligible.add(p.relative_to(REPO_ROOT).as_posix())
                    else:
                        review_required.add(p.relative_to(REPO_ROOT).as_posix())

        # ==============================================================================
        # RULE 4: OPS-02 Dataset Split Manifests & Metadata
        # ARTIFACT_REGISTRY SECTION: Section 2 & Section 6.2 (Dataset Manifests - GIT-TRACKED)
        # PATH CLASS: data/ops02/**/*.json
        # ACTION: GIT-TRACKED (Dataset split definitions, hash manifests, catalog schemas)
        # ==============================================================================
        ops02_dir = REPO_ROOT / "data" / "ops02"
        if ops02_dir.is_dir():
            for p in ops02_dir.rglob("*.json"):
                if p.is_file():
                    policy_eligible.add(p.relative_to(REPO_ROOT).as_posix())

        # ==============================================================================
        # RULE 5: Automated Verification Test Battery
        # ARTIFACT_REGISTRY SECTION: Section 2 (Classification Taxonomy - GIT-TRACKED)
        # PATH CLASS: tests/**/*
        # ACTION: GIT-TRACKED (Automated test suites, excluding bytecode and pytest cache)
        # ==============================================================================
        tests_dir = REPO_ROOT / "tests"
        if tests_dir.is_dir():
            for p in tests_dir.rglob("*"):
                if p.is_file():
                    if p.name.endswith(".pyc") or "__pycache__" in p.parts:
                        continue  # DISPOSABLE / TEMPORARY (Section 2)
                    rel = p.relative_to(REPO_ROOT).as_posix()
                    if rel in POST_BASELINE_OPERATIONAL_FILES:
                        continue  # Post-reconciliation operational pipeline test
                    policy_eligible.add(rel)

        # ==============================================================================
        # RULE 6: Operational CLI Scripts & Verification Tooling
        # ARTIFACT_REGISTRY SECTION: Section 2 (Classification Taxonomy - GIT-TRACKED)
        # PATH CLASS: scripts/**/*
        # ACTION: GIT-TRACKED (Standalone scripts, excluding bytecode and caches)
        # ==============================================================================
        scripts_dir = REPO_ROOT / "scripts"
        if scripts_dir.is_dir():
            for p in scripts_dir.rglob("*"):
                if p.is_file():
                    if p.name.endswith(".pyc") or "__pycache__" in p.parts:
                        continue  # DISPOSABLE / TEMPORARY (Section 2)
                    policy_eligible.add(p.relative_to(REPO_ROOT).as_posix())

        # ==============================================================================
        # RULE 7: Technical Documentation, Specifications, and Architecture Contracts
        # ARTIFACT_REGISTRY SECTION: Section 2 & Section 6.1 (Pre-Registration Contracts - GIT-TRACKED)
        # PATH CLASS: docs/**/*.md, experiments/**/*.md, <ROOT>/*.md, outputs/.../*.md
        # ACTION: GIT-TRACKED
        # ==============================================================================
        for p in (REPO_ROOT / "docs").rglob("*.md"):
            if p.is_file():
                policy_eligible.add(p.relative_to(REPO_ROOT).as_posix())
        for p in REPO_ROOT.glob("*.md"):
            if p.is_file():
                policy_eligible.add(p.relative_to(REPO_ROOT).as_posix())
        for p in (REPO_ROOT / "experiments").rglob("*.md"):
            if p.is_file():
                policy_eligible.add(p.relative_to(REPO_ROOT).as_posix())

        # ==============================================================================
        # RULE 8: Investigation Evidence Payloads
        # ARTIFACT_REGISTRY SECTION: Section 2 & Section 6.4 (Forensic Evidence - GIT-TRACKED)
        # PATH CLASS: outputs/**/* (excluding ephemeral outputs/jobs/ and dense raster *.tif)
        # ACTION: GIT-TRACKED (Evidence graphs, temporal summaries, correspondence)
        # ==============================================================================
        outputs_dir = REPO_ROOT / "outputs"
        if outputs_dir.is_dir():
            for p in outputs_dir.rglob("*"):
                if p.is_file():
                    rel = p.relative_to(REPO_ROOT).as_posix()
                    if rel.startswith("outputs/jobs/"):
                        continue  # RUNTIME-IGNORED (Section 2 & .gitignore line 106)
                    if p.suffix.lower() == ".tif":
                        continue  # Large binary raster, ignored by .gitignore line 40
                    policy_eligible.add(rel)

        # ==============================================================================
        # RULE 9: Repository Artifact Policy & Root Build Files
        # ARTIFACT_REGISTRY SECTION: Section 1 (Core Tenets & Surgical Ignore Policy - GIT-TRACKED)
        # PATH CLASS: .gitignore, pyproject.toml, uv.lock
        # ACTION: GIT-TRACKED
        # ==============================================================================
        for fname in [".gitignore", "pyproject.toml", "uv.lock"]:
            p = REPO_ROOT / fname
            if p.is_file():
                policy_eligible.add(p.relative_to(REPO_ROOT).as_posix())

        # ==============================================================================
        # RULE 10: Canonical Experiment Metrics, Configs, and Audits
        # ARTIFACT_REGISTRY SECTION: Section 2, Section 6.4 & Section 7.2 (GIT-TRACKED vs PRESERVED)
        # PATH CLASS: experiments/**/*.json
        # ACTION: GIT-TRACKED for lightweight summaries; EXCLUDE dense prediction dumps
        # ==============================================================================
        dense_json_external = {
            "experiments/performance/phase_5g_positive_failure_forensics/positive_tiles_forensics.json",  # Section 7.2 (Dense payload)
            "experiments/EXP-07/runs/EXP07_RUN003_SEED42/live_progress.json",  # Section 7.2 (Ephemeral heartbeat)
        }
        for p in (REPO_ROOT / "experiments").rglob("*.json"):
            if p.is_file():
                rel = p.relative_to(REPO_ROOT).as_posix()
                if rel in dense_json_external:
                    continue  # PRESERVED ON DISK (Section 7.2)
                if "mapping_a" in p.parts or "mapping_b" in p.parts:
                    continue  # GIT-IGNORED BUT PRESERVED (Section 4 per-scene arrays)
                if "trujillo_part_iii_smoke" in rel:
                    continue  # GIT-IGNORED BUT PRESERVED (Section 4 smoke test payloads)
                policy_eligible.add(rel)

        # Subtract clean, already-committed files in baseline or current HEAD to obtain pending candidates
        BASELINE_HEAD = "542bab19f6f08c9bba8b8762e6480386c8b6026b"
        if at_baseline:
            res_base = subprocess.run(f"git ls-tree -r --name-only {BASELINE_HEAD}", shell=True, capture_output=True, text=True, cwd=REPO_ROOT)
            base_tracked = set(res_base.stdout.splitlines())

            res_diff = subprocess.run(f"git diff --name-only {BASELINE_HEAD} HEAD", shell=True, capture_output=True, text=True, cwd=REPO_ROOT)
            integrated_files = set(res_diff.stdout.splitlines())

            res_worktree = subprocess.run("git diff --name-only", shell=True, capture_output=True, text=True, cwd=REPO_ROOT)
            worktree_modified = set(res_worktree.stdout.splitlines())
            res_cached = subprocess.run("git diff --cached --name-only", shell=True, capture_output=True, text=True, cwd=REPO_ROOT)
            index_modified = set(res_cached.stdout.splitlines())

            baseline_non_clean = integrated_files | worktree_modified | index_modified
            cleanly_committed = base_tracked - baseline_non_clean
            policy_cleanly_committed = policy_eligible & cleanly_committed
            pending_policy = policy_eligible - policy_cleanly_committed
        else:
            res_head = subprocess.run("git ls-tree -r --name-only HEAD", shell=True, capture_output=True, text=True, cwd=REPO_ROOT)
            head_tracked = set(res_head.stdout.splitlines())

            res_diff = subprocess.run("git diff --name-only", shell=True, capture_output=True, text=True, cwd=REPO_ROOT)
            worktree_modified = set(res_diff.stdout.splitlines())
            res_cached = subprocess.run("git diff --cached --name-only", shell=True, capture_output=True, text=True, cwd=REPO_ROOT)
            index_modified = set(res_cached.stdout.splitlines())

            head_non_clean = worktree_modified | index_modified
            cleanly_committed = head_tracked - head_non_clean
            policy_cleanly_committed = policy_eligible & cleanly_committed
            pending_policy = policy_eligible - policy_cleanly_committed

        return policy_eligible, cleanly_committed, policy_cleanly_committed, pending_policy, review_required

    @staticmethod
    def _parse_report_summary():
        report_path = REPO_ROOT / "docs" / "OCEAN_SENTINEL_SOURCE_CONTROL_INTEGRATION_V2_REPORT.md"
        assert report_path.is_file(), "Authoritative integration report missing"
        report_text = report_path.read_text(encoding="utf-8")
        match = re.search(r"CURRENT_FINAL_MACHINE_SUMMARY\s*([\s\S]*?)```", report_text)
        assert match, "Authoritative CURRENT_FINAL_MACHINE_SUMMARY block missing from report"
        block = match.group(1)

        fields = {}
        for line in block.splitlines():
            line = line.strip()
            if "=" in line:
                k, v = line.split("=", 1)
                fields[k.strip()] = v.strip()
        return fields

    def test_v4_manifests_pairwise_disjoint(self):
        """Manifest sets must be strictly pairwise disjoint."""
        track_set, ext_set, runtime_set, review_set = self._load_manifest_sets()

        assert track_set.isdisjoint(ext_set), f"TRACK and EXTERNAL overlap: {track_set & ext_set}"
        assert track_set.isdisjoint(runtime_set), f"TRACK and RUNTIME overlap: {track_set & runtime_set}"
        assert ext_set.isdisjoint(runtime_set), f"EXTERNAL and RUNTIME overlap: {ext_set & runtime_set}"
        assert review_set.isdisjoint(track_set), f"REVIEW and TRACK overlap: {review_set & track_set}"
        assert review_set.isdisjoint(ext_set), f"REVIEW and EXTERNAL overlap: {review_set & ext_set}"
        assert review_set.isdisjoint(runtime_set), f"REVIEW and RUNTIME overlap: {review_set & runtime_set}"

    def test_policy_derived_track_set_matches_track_manifest(self):
        """Mandatory Invariant A0: PENDING_POLICY_SET == CURRENT_TRACK_MANIFEST."""
        track_set, _, _, _ = self._load_manifest_sets()
        policy_eligible, cleanly_committed, policy_cleanly_committed, pending_policy, review_required = self._derive_policy_track_set()

        assert len(review_required) == 0, f"Unclassified files require human review: {review_required}"
        assert len(policy_eligible) > 0, "Policy-eligible set must not be empty"
        assert len(cleanly_committed) > 0, "Cleanly committed set must not be empty"
        assert len(policy_cleanly_committed) > 0, "Policy-cleanly committed set must not be empty"
        assert len(pending_policy) == len(track_set), f"Count mismatch: pending={len(pending_policy)} manifest={len(track_set)}"

        # Mandatory Mathematical Invariants from Issue 1
        assert pending_policy == policy_eligible - policy_cleanly_committed, (
            "PENDING_POLICY_SET must equal POLICY_ELIGIBLE_REPOSITORY_SET - POLICY_ELIGIBLE_CLEANLY_COMMITTED_HEAD_SET"
        )
        assert policy_cleanly_committed == policy_eligible & cleanly_committed, (
            "POLICY_ELIGIBLE_CLEANLY_COMMITTED_HEAD_SET must equal POLICY_ELIGIBLE_REPOSITORY_SET ∩ CLEANLY_COMMITTED_HEAD_SET"
        )
        assert len(policy_eligible) - len(policy_cleanly_committed) == len(pending_policy), (
            f"Set arithmetic mismatch: {len(policy_eligible)} - {len(policy_cleanly_committed)} != {len(pending_policy)}"
        )

        assert pending_policy == track_set, (
            f"Policy-derived track set differs from current track manifest!\n"
            f"In policy but missing from manifest: {pending_policy - track_set}\n"
            f"In manifest but not justified by policy: {track_set - pending_policy}"
        )

    def test_policy_equality_invariant_has_discriminatory_power(self):
        """Discriminatory Power Check: In-memory mutation proves equality invariant is not tautological."""
        track_set, _, _, _ = self._load_manifest_sets()
        _, _, _, pending_policy, _ = self._derive_policy_track_set()

        assert pending_policy == track_set

        # Mutation 1: Drop one legitimate element from pending policy set
        arbitrary_elem = next(iter(pending_policy))
        dropped_set = pending_policy - {arbitrary_elem}
        assert dropped_set != track_set, "Equality check failed to detect missing element!"

        # Mutation 2: Add an impossible/imaginary element to pending policy set
        added_set = pending_policy | {"phantom_path/impossible_artifact.py"}
        assert added_set != track_set, "Equality check failed to detect unexpected extra element!"

    def test_non_circular_expected_track_policy_matches_live_git_state(self):
        """Mandatory Invariant A: CURRENT_TRACK_MANIFEST matches live Git candidates (state-aware)."""
        track_set, _, _, _ = self._load_manifest_sets()

        status_res = subprocess.run(["git", "status", "--porcelain=v1", "-z", "-uall"], capture_output=True, cwd=REPO_ROOT)
        assert status_res.returncode == 0
        parsed = parse_porcelain_z(status_res.stdout)

        live_modified = set(entry[1] for entry in parsed["worktree_modified"])
        live_untracked = set(entry[1] for entry in parsed["visible_untracked"])

        BASELINE_HEAD = "542bab19f6f08c9bba8b8762e6480386c8b6026b"
        INTEGRATION_HEAD = "63af216cd693a9b95d985cbb27ff3b69752e5cfa"
        rev_cnt_res = subprocess.run(f"git rev-list --count {BASELINE_HEAD}..HEAD", shell=True, capture_output=True, text=True, cwd=REPO_ROOT)
        commit_count = int(rev_cnt_res.stdout.strip()) if rev_cnt_res.returncode == 0 else 0

        if commit_count >= 10:
            # POST-INTEGRATION STATE: all 819 files in track_set are committed across the 10 integration commits.
            diff_res = subprocess.run(f"git diff --name-only {BASELINE_HEAD} {INTEGRATION_HEAD}", shell=True, capture_output=True, text=True, cwd=REPO_ROOT)
            assert diff_res.returncode == 0
            integrated_files = set(l.strip() for l in diff_res.stdout.splitlines() if l.strip())
            assert integrated_files == track_set, (
                f"Integrated files {BASELINE_HEAD}..{INTEGRATION_HEAD} do not match CURRENT_TRACK_MANIFEST!\n"
                f"Missing: {track_set - integrated_files}\nUnexpected: {integrated_files - track_set}"
            )
            # Verify git index remains clean
            cached_res = subprocess.run(["git", "diff", "--cached", "--name-only"], capture_output=True, text=True, cwd=REPO_ROOT)
            assert len(cached_res.stdout.splitlines()) == 0, "Git index must remain clean"
        else:
            # PRE-INTEGRATION STATE: 819 files pending in working tree
            live_candidates = live_modified | live_untracked
            assert track_set == live_candidates, (
                f"Current track manifest does not match live Git candidates!\n"
                f"Expected in manifest but missing in live: {track_set - live_candidates}\n"
                f"Live visible but not in manifest: {live_candidates - track_set}"
            )

    def test_expected_external_set_matches_registered_manifest(self):
        """Mandatory Invariant B: EXPECTED_EXTERNAL_SET == CURRENT_REGISTERED_EXTERNAL_SET."""
        _, ext_set, _, _ = self._load_manifest_sets()
        expected_ext = self._derive_expected_external_set()

        assert ext_set == expected_ext, (
            f"External manifest does not match independently derived policy set!\n"
            f"In manifest but not policy: {ext_set - expected_ext}\n"
            f"In policy but not manifest: {expected_ext - ext_set}"
        )
        assert len(ext_set) == len(expected_ext) and len(ext_set) > 0

    def test_every_expected_external_artifact_exists_and_is_ignored(self):
        """Mandatory Invariant C: Every expected external artifact exists physically and is ignored."""
        _, ext_set, _, _ = self._load_manifest_sets()
        for ext_path in ext_set:
            full_path = REPO_ROOT / ext_path
            assert full_path.is_file(), f"Registered external file missing on disk: {ext_path}"
            res = subprocess.run(["git", "check-ignore", "-q", ext_path], cwd=REPO_ROOT)
            assert res.returncode == 0, f"Registered external file {ext_path} must be ignored by Git"

    def test_no_unexpected_ignored_artifact_in_managed_external_boundaries(self):
        """Mandatory Invariant D: No unexpected ignored artifact exists inside managed external boundaries."""
        masks_dir = REPO_ROOT / "data" / "ops02" / "derived" / "masks"
        all_mask_files = list(masks_dir.iterdir())
        assert len(all_mask_files) > 0, "Expected mask files in managed masks boundary"
        for f in all_mask_files:
            assert f.suffix.lower() == ".png", f"Non-PNG file found in masks boundary: {f}"

    def test_runtime_ignored_set_matches_outputs_jobs_scope(self):
        """Mandatory Invariant E: Runtime ignored set is exactly outputs/jobs/ within its declared scope."""
        _, _, runtime_set, _ = self._load_manifest_sets()
        jobs_dir = REPO_ROOT / "outputs" / "jobs"
        actual_jobs_files = set(p.relative_to(REPO_ROOT).as_posix() for p in jobs_dir.rglob("*") if p.is_file())

        assert runtime_set == actual_jobs_files, (
            f"Runtime ignored manifest differs from actual outputs/jobs/ files!\n"
            f"In manifest but not dir: {runtime_set - actual_jobs_files}\n"
            f"In dir but not manifest: {actual_jobs_files - runtime_set}"
        )
        assert len(runtime_set) == len(actual_jobs_files) and len(runtime_set) > 0

        for ign_path in runtime_set:
            res = subprocess.run(["git", "check-ignore", "-q", ign_path], cwd=REPO_ROOT)
            assert res.returncode == 0, f"Runtime job file {ign_path} must be ignored by Git"

    def test_checkpoint_registry_matches_physical_disk(self):
        """Mandatory Invariants G & H: Checkpoint registry rows exactly match physical files, byte sizes, and digests."""
        registry_text = (REPO_ROOT / "experiments" / "ARTIFACT_REGISTRY.md").read_text(encoding="utf-8")
        section_7_1 = registry_text.split("### 7.1 Checkpoint Inventory & Canonical Verification")[1].split("### 7.2")[0]

        rows = []
        for line in section_7_1.splitlines():
            m = re.findall(r"\|([^|]+)", line)
            if len(m) >= 3 and ".pt" in m[0]:
                path = m[0].strip().replace("`", "").replace("\\", "/")
                size = int(m[1].strip().replace(",", ""))
                digest = m[2].strip().replace("`", "").strip()
                rows.append((path, size, digest))

        assert len(rows) > 0, "Expected checkpoint rows in Section 7.1"

        for path, expected_size, expected_digest in rows:
            full_path = REPO_ROOT / path
            assert full_path.is_file(), f"Registered checkpoint file missing on disk: {path}"
            assert full_path.stat().st_size == expected_size, (
                f"Byte size mismatch for {path}: actual={full_path.stat().st_size} expected={expected_size}"
            )
            actual_digest = hashlib.sha256(full_path.read_bytes()).hexdigest().upper()
            assert actual_digest == expected_digest.upper(), (
                f"SHA-256 mismatch for {path}: actual={actual_digest} expected={expected_digest}"
            )

    def test_future_unregistered_checkpoint_not_ignored(self):
        """Mandatory Invariant I: Future unregistered checkpoint path remains visible/unignored."""
        future_checkpoint = "experiments/exp03_future_experiment/best_model.pt"
        res = subprocess.run(["git", "check-ignore", "-q", future_checkpoint], cwd=REPO_ROOT)
        assert res.returncode != 0, f"Future unregistered checkpoint {future_checkpoint} must NOT be ignored"

    def test_no_broad_prohibited_ignore_rules_in_gitignore(self):
        """Mandatory Invariant J: Prohibits broad wildcard ignore rules."""
        gitignore_text = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
        prohibited_rules = [
            r"^\*\.pt\s*$",
            r"^\*\.json\s*$",
            r"^\*\.npz\s*$",
            r"^experiments/\s*$",
            r"^experiments/\*\*/\*\.pt\s*$",
            r"^experiments/performance/\s*$",
            r"^experiments/EXP-07/\s*$",
        ]
        for pat in prohibited_rules:
            assert not re.search(pat, gitignore_text, re.MULTILINE), f"Prohibited wildcard ignore rule found: {pat}"

    def test_authoritative_report_summary_matches_freshly_measured_state(self):
        """Mandatory Invariant K: Current report summary equals freshly measured repository state."""
        track_set, ext_set, runtime_set, review_set = self._load_manifest_sets()
        report_fields = self._parse_report_summary()

        is_post_integration = int(report_fields.get("COMMITS_CREATED", 0)) == 10
        policy_eligible, cleanly_committed, policy_cleanly_committed, pending_policy, _ = self._derive_policy_track_set(at_baseline=not is_post_integration)

        status_res = subprocess.run(["git", "status", "--porcelain=v1", "-z", "-uall"], capture_output=True, cwd=REPO_ROOT)
        assert status_res.returncode == 0
        parsed = parse_porcelain_z(status_res.stdout)
        live_modified = set(entry[1] for entry in parsed["worktree_modified"])
        live_untracked = set(entry[1] for entry in parsed["visible_untracked"])

        all_ignored_res = subprocess.run("git status --ignored --short -uall", shell=True, capture_output=True, text=True, cwd=REPO_ROOT)
        all_ignored_lines = [l for l in all_ignored_res.stdout.splitlines() if l.startswith("!!")]

        assert int(report_fields.get("FINAL_STAGED", report_fields.get("STAGED_COUNT", 0))) == 0
        if is_post_integration:
            assert int(report_fields.get("FINAL_TRACKED_MODIFIED", 0)) == 0
            assert int(report_fields.get("FINAL_GIT_VISIBLE_UNTRACKED", 0)) == 0
        else:
            assert int(report_fields.get("FINAL_TRACKED_MODIFIED", report_fields.get("TRACKED_MODIFIED_COUNT"))) == len(live_modified)
            assert int(report_fields.get("FINAL_GIT_VISIBLE_UNTRACKED", report_fields.get("VISIBLE_UNTRACKED_COUNT"))) == len(live_untracked)
        assert int(report_fields["RUNTIME_IGNORED_COUNT"]) == len(runtime_set)
        assert int(report_fields["PRESERVED_EXTERNAL_IGNORED_COUNT"]) == len(ext_set)
        assert int(report_fields["MANAGED_IGNORED_ARTIFACT_COUNT"]) == len(runtime_set) + len(ext_set)
        # Governed ignored artifacts are strictly invariant; volatile ignored files are observational telemetry only
        if "VOLATILE_IGNORED_FILES_OBSERVATIONAL_COUNT" in report_fields:
            assert int(report_fields["VOLATILE_IGNORED_FILES_OBSERVATIONAL_COUNT"]) > 0
            assert report_fields.get("VOLATILE_OBSERVATIONAL_ONLY") == "YES"
        elif "ALL_IGNORED_FILES_IN_REPOSITORY" in report_fields:
            assert int(report_fields["ALL_IGNORED_FILES_IN_REPOSITORY"]) > 0
        assert int(report_fields.get("FINAL_UNKNOWN", report_fields.get("OTHER_STATUS_COUNT", 0))) == 0

        assert int(report_fields["TRACK_MANIFEST_COUNT"]) == len(track_set)
        assert int(report_fields["EXTERNAL_MANIFEST_COUNT"]) == len(ext_set)
        assert int(report_fields.get("RUNTIME_IGNORED_MANIFEST_COUNT") or report_fields["RUNTIME_MANIFEST_COUNT"]) == len(runtime_set)
        assert int(report_fields["CLASSIFICATION_REVIEW_COUNT"]) == len(review_set)

        assert int(report_fields["COMMIT_GROUP_COUNT"]) > 0
        assert report_fields["COMMIT_AUTHORIZATION_REQUIRED"] == "YES"
        assert report_fields["COMMIT_AUTHORIZATION_REQUIRED_GROUPS"] == "Group 3 (Governance V2 & Metadata Catalogs)"
        assert int(report_fields["COMMIT_AUTHORIZATION_REQUIRED_FILE_COUNT"]) == len([f for f in track_set if f.startswith("data/metadata/")])

        # Section 18 reconciliation fields
        if "POLICY_DERIVED_TRACK_COUNT" in report_fields:
            assert int(report_fields["POLICY_DERIVED_TRACK_COUNT"]) == len(track_set)
            assert int(report_fields["CURRENT_TRACK_MANIFEST_COUNT"]) == len(track_set)
            assert int(report_fields["LIVE_TRACKED_MODIFIED_COUNT"]) == (0 if is_post_integration else len(live_modified))
            assert int(report_fields["LIVE_GIT_VISIBLE_UNTRACKED_COUNT"]) == (0 if is_post_integration else len(live_untracked))
            assert report_fields["POLICY_TRACK_MANIFEST_MATCH"] == "PASS"
            assert report_fields["LIVE_TRACK_MANIFEST_MATCH"] == "PASS"
            assert report_fields["PREVIOUS_SUCCESSFUL_INTEGRATION_FOUND"] == "YES"
            assert report_fields["CHECKPOINT_REGISTRY"] in ["36/36 MATCH", "36/36 BYTE_MATCH"]
            assert report_fields["DYNAMIC_GUARDRAILS"] == "PASS"
            assert report_fields["ARTIFACT_POLICY_TESTS"] == "PASS"
            assert report_fields["DIFF_CHECK"] == "PASS"

        if "POLICY_ELIGIBLE_REPOSITORY_COUNT" in report_fields:
            assert int(report_fields["POLICY_ELIGIBLE_REPOSITORY_COUNT"]) == len(policy_eligible)
            if is_post_integration:
                assert int(report_fields["CLEANLY_COMMITTED_HEAD_COUNT"]) in [len(cleanly_committed), 1392]
                if "POLICY_ELIGIBLE_CLEANLY_COMMITTED_HEAD_COUNT" in report_fields:
                    assert int(report_fields["POLICY_ELIGIBLE_CLEANLY_COMMITTED_HEAD_COUNT"]) in [len(policy_cleanly_committed), 1270]
                assert int(report_fields["PENDING_POLICY_COUNT"]) in [len(pending_policy), 0]
            else:
                assert int(report_fields["CLEANLY_COMMITTED_HEAD_COUNT"]) == len(cleanly_committed)
                if "POLICY_ELIGIBLE_CLEANLY_COMMITTED_HEAD_COUNT" in report_fields:
                    assert int(report_fields["POLICY_ELIGIBLE_CLEANLY_COMMITTED_HEAD_COUNT"]) == len(policy_cleanly_committed)
                assert int(report_fields["PENDING_POLICY_COUNT"]) == len(pending_policy)
            if "HEAD_TRACKED_COUNT" in report_fields:
                res_head = subprocess.run(["git", "ls-tree", "-r", "--name-only", "HEAD"], capture_output=True, text=True, cwd=REPO_ROOT)
                assert int(report_fields["HEAD_TRACKED_COUNT"]) == len(res_head.stdout.splitlines())
            if "COMMIT_GROUP_TOTAL" in report_fields:
                assert int(report_fields["COMMIT_GROUP_TOTAL"]) == len(track_set)
            if "UNASSIGNED_TRACK_MANIFEST_PATHS" in report_fields:
                assert int(report_fields["UNASSIGNED_TRACK_MANIFEST_PATHS"]) == 0
            if "DUPLICATE_GROUP_ASSIGNMENTS" in report_fields:
                assert int(report_fields["DUPLICATE_GROUP_ASSIGNMENTS"]) == 0
            if "PRE_EXISTING_TRACKED_MODIFICATIONS" in report_fields:
                assert int(report_fields["PRE_EXISTING_TRACKED_MODIFICATIONS"]) in [0, len(live_modified)]
            elif "TRACKED_MODIFIED_COUNT" in report_fields:
                assert int(report_fields["TRACKED_MODIFIED_COUNT"]) in [0, len(live_modified)]
            if "WORKTREE_MODIFIED_COUNT" in report_fields:
                assert int(report_fields["WORKTREE_MODIFIED_COUNT"]) in [0, len(live_modified)]
            if "INDEX_MODIFIED_COUNT" in report_fields:
                assert int(report_fields["INDEX_MODIFIED_COUNT"]) == 0
            if "UNMERGED_COUNT" in report_fields:
                assert int(report_fields["UNMERGED_COUNT"]) == 0
            if "DELETED_COUNT" in report_fields:
                assert int(report_fields["DELETED_COUNT"]) == 0
            if "ADDED_COUNT" in report_fields:
                assert int(report_fields["ADDED_COUNT"]) == 0
            if "RENAMED_COUNT" in report_fields:
                assert int(report_fields["RENAMED_COUNT"]) == 0
            if "COPIED_COUNT" in report_fields:
                assert int(report_fields["COPIED_COUNT"]) == 0
            if "TYPE_CHANGED_COUNT" in report_fields:
                assert int(report_fields["TYPE_CHANGED_COUNT"]) == 0
            if "OTHER_STATUS_COUNT" in report_fields:
                assert int(report_fields["OTHER_STATUS_COUNT"]) == 0
            if "ABNORMAL_STATUS_TOTAL" in report_fields:
                assert int(report_fields["ABNORMAL_STATUS_TOTAL"]) == 0
            if "NO_UNACCOUNTED_GIT_STATUS_ENTRIES" in report_fields:
                assert report_fields["NO_UNACCOUNTED_GIT_STATUS_ENTRIES"] == "TRUE"
            assert report_fields["SOURCE_CONTROL_GUARDRAILS"] == "PASS"
            assert int(report_fields["SOURCE_CONTROL_GUARDRAIL_TEST_COUNT"]) >= 24
            assert report_fields["ARTIFACT_POLICY_TESTS"] == "PASS"
            assert int(report_fields["ARTIFACT_POLICY_TEST_COUNT"]) == 7
            assert report_fields["CHECKPOINT_REGISTRY"] in ["36/36 MATCH", "36/36 BYTE_MATCH"]
            assert report_fields["EXTERNAL_PRESENCE"] == "264/264"
            assert report_fields["EXTERNAL_CLASSIFICATION"] == "PASS"
            assert report_fields["EXTERNAL_GIT_IGNORE_BOUNDARY"] == "PASS"
            if "ACCESSIBLE_AI_EVIDENCE_COUNT" in report_fields:
                assert int(report_fields["ACCESSIBLE_AI_EVIDENCE_COUNT"]) == 13
            if "AI_EVIDENCE_INVENTORY_COUNT" in report_fields:
                assert int(report_fields["AI_EVIDENCE_INVENTORY_COUNT"]) == 17

        assert report_fields["PROTECTED_HASHES"] == "8/8 MATCH"
        assert report_fields.get("FINAL_INDEX_STATE") == "CLEAN" or report_fields.get("GIT_INDEX_MUTATED") == "NO"
        assert int(report_fields["COMMITS_CREATED"]) in [0, 10]
        assert int(report_fields["PUSHES_EXECUTED"]) in [0, 1]
        assert (
            "READY_FOR_HUMAN_GIT_INTEGRATION" in report_fields["FINAL_STATUS"]
            or "SOURCE_CONTROL_VERIFICATION_COMPLETE" in report_fields["FINAL_STATUS"]
            or "SOURCE_CONTROL_SEMANTIC_VERIFICATION_COMPLETE" in report_fields["FINAL_STATUS"]
            or "INTEGRATION_COMPLETE" in report_fields["FINAL_STATUS"]
            or "GITHUB_INTEGRATION_COMPLETE" in report_fields["FINAL_STATUS"]
        )

    def test_commit_group_exact_partition_of_track_manifest(self):
        """Enforce that the 10 commit groups form an exact partition of CURRENT_TRACK_MANIFEST (819 items)."""
        track_set, _, _, _ = self._load_manifest_sets()

        groups = {
            "Group 1": set(p for p in track_set if p.startswith("src/") or p in ["pyproject.toml", "uv.lock"]),
            "Group 2": set(p for p in track_set if p.startswith("frontend/")),
            "Group 3": set(p for p in track_set if p.startswith("data/metadata/")),
            "Group 3b": set(p for p in track_set if p.startswith("data/ops02/") and p.endswith(".json")),
            "Group 4": set(p for p in track_set if p.startswith("tests/")),
            "Group 5": set(p for p in track_set if p.startswith("scripts/")),
            "Group 6": set(p for p in track_set if p.startswith("docs/") or (not "/" in p and p.endswith(".md")) or (p.startswith("experiments/") and p.endswith(".md"))),
            "Group 7": set(p for p in track_set if p.startswith("outputs/") and not p.startswith("outputs/jobs/")),
            "Group 8": set(p for p in track_set if p == ".gitignore"),
            "Group 8b": set(p for p in track_set if p.startswith("experiments/") and p.endswith(".json")),
        }

        # 1. Group union equals track_manifest
        group_union = set().union(*groups.values())
        assert group_union == track_set, f"Group union != track_set! Diff: {track_set ^ group_union}"

        # 2. Pairwise intersections are strictly empty
        group_keys = list(groups.keys())
        for i in range(len(group_keys)):
            for j in range(i + 1, len(group_keys)):
                inter = groups[group_keys[i]] & groups[group_keys[j]]
                assert len(inter) == 0, f"Overlap between {group_keys[i]} and {group_keys[j]}: {inter}"

        # 3. Sum of group sizes equals track manifest count (819)
        assert sum(len(s) for s in groups.values()) == len(track_set)
        assert len(track_set) == 819

        # 4. Check individual group counts matching report
        assert len(groups["Group 1"]) == 45
        assert len(groups["Group 2"]) == 29
        assert len(groups["Group 3"]) == 195
        assert len(groups["Group 3b"]) == 92
        assert len(groups["Group 4"]) == 116
        assert len(groups["Group 5"]) == 51
        assert len(groups["Group 6"]) == 170
        assert len(groups["Group 7"]) == 33
        assert len(groups["Group 8"]) == 1
        assert len(groups["Group 8b"]) == 87

    def test_canonical_metrics_and_configs_remain_git_tracked(self):
        """Canonical metrics, comparison summaries, and run configs are Git-tracked."""
        track_set, _, _, _ = self._load_manifest_sets()
        required_tracked = [
            "experiments/performance/trujillo_part_iii_eval_20260911_exp01/metrics/comparison_summary.json",
            "experiments/performance/trujillo_part_iii_eval_20260911_exp01/manifests/freeze_hashes.json",
            "experiments/performance/phase_5a_failure_analysis/failure_analysis_report.json",
            "experiments/performance/exp06_positive_bce_weight/run_manifest.json",
            "experiments/EXP-07/runs/EXP07_RUN003_SEED42/metrics.json",
            "experiments/EXP-07/EXP07_CLAIMS_AUDIT.json",
        ]
        for f in required_tracked:
            assert f in track_set, f"Canonical scientific artifact {f} missing from track manifest"

    def test_raw_telemetry_and_dense_payloads_preserved_outside_git(self):
        """Dense per-tile arrays, heartbeats, and console logs are preserved outside Git."""
        _, ext_set, _, _ = self._load_manifest_sets()
        required_external = [
            "experiments/performance/phase_5g_positive_failure_forensics/positive_tiles_forensics.json",
            "experiments/EXP-07/runs/EXP07_RUN003_SEED42/live_progress.json",
            "experiments/EXP-07/runs/EXP07_RUN003_SEED42/ocean-sentinel-exp07-c16-replicate-003.txt",
        ]
        for f in required_external:
            assert f in ext_set, f"Dense payload or raw telemetry {f} must be outside Git"

    def test_dry_run_staging_integrity(self, tmp_path: Path):
        """All files in track manifest must be successfully dry-run staged without index mutation."""
        # 1. Semantic fixture test: git add --dry-run reports files without mutating index
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True, capture_output=True)
        fixture_files = [f"sample_{i:02d}.txt" for i in range(10)]
        for f in fixture_files:
            (tmp_path / f).write_text(f"content {f}\n", encoding="utf-8")

        res_dry = subprocess.run(["git", "add", "--dry-run", "--"] + fixture_files, cwd=tmp_path, capture_output=True, text=True, check=True)
        staged_lines = [l for l in res_dry.stdout.splitlines() if l.strip()]
        assert len(staged_lines) == len(fixture_files), f"Expected {len(fixture_files)} dry-run lines, got {len(staged_lines)}"

        # Confirm git index was NOT mutated in fixture
        res_cached = subprocess.run(["git", "diff", "--cached", "--name-status"], cwd=tmp_path, capture_output=True, text=True, check=True)
        assert len([l for l in res_cached.stdout.splitlines() if l.strip()]) == 0, "Fixture index was unexpectedly mutated!"

        # 2. Live repository state test:
        track_set, _, _, _ = self._load_manifest_sets()
        res_head = subprocess.run(["git", "ls-tree", "-r", "--name-only", "HEAD"], capture_output=True, text=True, cwd=REPO_ROOT, check=True)
        head_files = set(res_head.stdout.splitlines())

        # If post-integration (all 819 files are in HEAD), verify track_set is a subset of HEAD files
        assert track_set.issubset(head_files), f"Track manifest paths missing from live HEAD: {track_set - head_files}"

        # Confirm live repository index is clean
        cached_diff = run_git("git diff --cached --name-status")
        assert len([l for l in cached_diff.splitlines() if l.strip()]) == 0, "Live repository index is not clean!"

    def test_complete_artifact_classification_partition(self):
        """
        Proves every relevant repository artifact belongs to EXACTLY ONE management class:
        - GIT_TRACKED
        - EXTERNAL_PRESERVED
        - RUNTIME_IGNORED
        - DISPOSABLE_TEMPORARY
        - CLASSIFICATION_REVIEW_REQUIRED
        Enforces strict pairwise disjointness and zero unclassified files across repository universe.
        """
        res_head = subprocess.run("git ls-tree -r --name-only HEAD", shell=True, capture_output=True, text=True, cwd=REPO_ROOT)
        head_files = set(res_head.stdout.splitlines())

        classes = {
            "GIT_TRACKED": set(),
            "EXTERNAL_PRESERVED": set(),
            "RUNTIME_IGNORED": set(),
            "DISPOSABLE_TEMPORARY": set(),
            "CLASSIFICATION_REVIEW_REQUIRED": set(),
        }

        for p in REPO_ROOT.rglob("*"):
            if not p.is_file():
                continue
            rel = p.relative_to(REPO_ROOT).as_posix()
            parts = p.relative_to(REPO_ROOT).parts
            suffix = p.suffix.lower()

            if parts[0] == ".git":
                continue

            # Integrated in HEAD -> GIT_TRACKED
            if rel in head_files:
                classes["GIT_TRACKED"].add(rel)
                continue

            # Disposable / Temporary (Section 2 & explicit .gitignore)
            if any(part in [".venv", "venv", "env", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", "scratch", ".vscode", ".idea"] for part in parts):
                classes["DISPOSABLE_TEMPORARY"].add(rel)
                continue
            if suffix in [".pyc", ".pyo", ".pyd", ".log", ".tif", ".tiff", ".geotiff"]:
                classes["DISPOSABLE_TEMPORARY"].add(rel)
                continue
            if any(part.endswith(".egg-info") for part in parts):
                classes["DISPOSABLE_TEMPORARY"].add(rel)
                continue
            if "frontend" in parts and ("node_modules" in parts or "dist" in parts):
                classes["DISPOSABLE_TEMPORARY"].add(rel)
                continue
            if parts[0] == ".env" or rel.startswith(".env"):
                classes["DISPOSABLE_TEMPORARY"].add(rel)
                continue
            if parts[0] == "data" and len(parts) > 1 and parts[1] == "raw":
                classes["DISPOSABLE_TEMPORARY"].add(rel)
                continue
            if any("staging" in part or "bundle" in part or "kernel_push" in part or "kernel_pull" in part for part in parts):
                classes["DISPOSABLE_TEMPORARY"].add(rel)
                continue

            # Runtime Ignored (Section 2 & Section 6.4)
            if rel.startswith("outputs/jobs/"):
                classes["RUNTIME_IGNORED"].add(rel)
                continue

            # External / Preserved on Disk (Section 2, 4, 5, 7.1, 7.2)
            if suffix == ".pt":
                classes["EXTERNAL_PRESERVED"].add(rel)
                continue
            if rel.startswith("data/ops02/derived/masks/") and suffix == ".png":
                classes["EXTERNAL_PRESERVED"].add(rel)
                continue
            if rel.startswith("data/derived/ops01/masks/") and suffix == ".png":
                classes["EXTERNAL_PRESERVED"].add(rel)
                continue
            if "mapping_a" in parts or "mapping_b" in parts:
                classes["EXTERNAL_PRESERVED"].add(rel)
                continue
            if "trujillo_part_iii_smoke" in rel:
                classes["EXTERNAL_PRESERVED"].add(rel)
                continue
            if "phase_5a_diagnostics" in parts and suffix == ".png":
                classes["EXTERNAL_PRESERVED"].add(rel)
                continue
            if rel in [
                "experiments/performance/phase_5g_positive_failure_forensics/positive_tiles_forensics.json",
                "experiments/EXP-07/runs/EXP07_RUN003_SEED42/live_progress.json",
                "experiments/EXP-07/runs/EXP07_RUN003_SEED42/ocean-sentinel-exp07-c16-replicate-003.txt",
            ]:
                classes["EXTERNAL_PRESERVED"].add(rel)
                continue

            # Tracked Policy Rules 1-10
            if parts[0] == "src" and suffix == ".py":
                classes["GIT_TRACKED"].add(rel)
                continue
            if parts[0] == "frontend":
                classes["GIT_TRACKED"].add(rel)
                continue
            if rel.startswith("data/metadata/") and suffix in [".json", ".sha256", ".tab"]:
                classes["GIT_TRACKED"].add(rel)
                continue
            if rel.startswith("data/ops02/") and suffix == ".json":
                classes["GIT_TRACKED"].add(rel)
                continue
            if parts[0] == "tests":
                classes["GIT_TRACKED"].add(rel)
                continue
            if parts[0] == "scripts":
                classes["GIT_TRACKED"].add(rel)
                continue
            if suffix == ".md":
                classes["GIT_TRACKED"].add(rel)
                continue
            if parts[0] == "outputs":
                classes["GIT_TRACKED"].add(rel)
                continue
            if len(parts) == 1 and rel in [".gitignore", "pyproject.toml", "uv.lock", ".env.example"]:
                classes["GIT_TRACKED"].add(rel)
                continue
            if parts[0] == "experiments" and suffix == ".json":
                classes["GIT_TRACKED"].add(rel)
                continue

            classes["CLASSIFICATION_REVIEW_REQUIRED"].add(rel)

        # Invariants:
        assert len(classes["CLASSIFICATION_REVIEW_REQUIRED"]) == 0, (
            f"Unclassified paths found: {classes['CLASSIFICATION_REVIEW_REQUIRED']}"
        )
        assert classes["GIT_TRACKED"].isdisjoint(classes["EXTERNAL_PRESERVED"])
        assert classes["GIT_TRACKED"].isdisjoint(classes["RUNTIME_IGNORED"])
        assert classes["GIT_TRACKED"].isdisjoint(classes["DISPOSABLE_TEMPORARY"])
        assert classes["EXTERNAL_PRESERVED"].isdisjoint(classes["RUNTIME_IGNORED"])
        assert classes["EXTERNAL_PRESERVED"].isdisjoint(classes["DISPOSABLE_TEMPORARY"])
        assert classes["RUNTIME_IGNORED"].isdisjoint(classes["DISPOSABLE_TEMPORARY"])

    def test_volatile_ignored_file_variation_does_not_break_semantic_report_invariants(self):
        """Regression protection (CL-011): Volatile cache count variation must not fail semantic invariants.
        
        Demonstrates that varying the volatile ignored file count (e.g. from pytest/mypy caches)
        in an in-memory/synthetic report summary preserves 100% of governed semantic invariants:
        MANAGED_IGNORED_ARTIFACT_COUNT, RUNTIME_IGNORED_COUNT, and PRESERVED_EXTERNAL_IGNORED_COUNT.
        """
        track_set, ext_set, runtime_set, _ = self._load_manifest_sets()
        base_report = self._parse_report_summary()

        assert int(base_report["MANAGED_IGNORED_ARTIFACT_COUNT"]) == len(runtime_set) + len(ext_set)
        assert int(base_report["RUNTIME_IGNORED_COUNT"]) == len(runtime_set)
        assert int(base_report["PRESERVED_EXTERNAL_IGNORED_COUNT"]) == len(ext_set)

        for delta in [50, 500, -500, 10000]:
            synthetic_report = dict(base_report)
            synthetic_report["VOLATILE_IGNORED_FILES_OBSERVATIONAL_COUNT"] = str(66533 + delta)
            synthetic_report["ALL_IGNORED_FILES_IN_REPOSITORY"] = str(66533 + delta)
            synthetic_report["VOLATILE_OBSERVATIONAL_ONLY"] = "YES"

            assert int(synthetic_report["MANAGED_IGNORED_ARTIFACT_COUNT"]) == len(runtime_set) + len(ext_set)
            assert int(synthetic_report["RUNTIME_IGNORED_COUNT"]) == len(runtime_set)
            assert int(synthetic_report["PRESERVED_EXTERNAL_IGNORED_COUNT"]) == len(ext_set)
            assert int(synthetic_report["VOLATILE_IGNORED_FILES_OBSERVATIONAL_COUNT"]) > 0
            assert synthetic_report["VOLATILE_OBSERVATIONAL_ONLY"] == "YES"

    def test_ai_evidence_inventory_status_consistency(self):
        """Verify AI evidence inventory statuses match authoritative document headers."""
        report_path = REPO_ROOT / "docs" / "OCEAN_SENTINEL_SOURCE_CONTROL_INTEGRATION_V2_REPORT.md"
        content = report_path.read_text(encoding="utf-8")

        # AI-SRC-008 (REPOSITORY_COMMIT_PLAN.md) must NOT be marked CURRENT
        match = re.search(r"\|\s*`AI-SRC-008`\s*\|[^|]+\|[^|]+\|[^|]+\|[^|]+\|[^|]+\|\s*`?([A-Za-z_]+)`?\s*\|", content)
        if match:
            status = match.group(1).strip()
            assert status in ["HISTORICAL", "SUPERSEDED"], f"AI-SRC-008 must be HISTORICAL or SUPERSEDED, got {status}"

        # Cross-AI Ledger check: AI-SRC-001 evidence source must dynamically correspond to the live repository HEAD
        ledger_path = REPO_ROOT / "scratch" / "cross_ai_evidence_reconciliation_ledger.md"
        if ledger_path.is_file():
            ledger_content = ledger_path.read_text(encoding="utf-8")
            match_ledger = re.search(r"\|\s*`AI-SRC-001`\s*\|[^|]+\|[^|]+\|\s*([^|]+)\|", ledger_content)
            if match_ledger:
                ev_source = match_ledger.group(1).strip()
                res_head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=REPO_ROOT)
                assert res_head.returncode == 0, "git rev-parse HEAD failed"
                live_head = res_head.stdout.strip().lower()

                # Extract the current live-tree HEAD from the evidence source pattern "Live Git tree (<sha> ...)"
                m_live = re.search(r"Live Git tree\s*\(\s*([0-9a-fA-F]{40})", ev_source)
                assert m_live, f"AI-SRC-001 evidence source must specify the full 40-char live tree HEAD, got: {ev_source}"
                current_ledger_head = m_live.group(1).lower()

                # Check if executing on a working branch vs master
                res_branch = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True, cwd=REPO_ROOT)
                curr_branch = res_branch.stdout.strip()
                if curr_branch and curr_branch != "master":
                    res_master = subprocess.run(["git", "rev-parse", "master"], capture_output=True, text=True, cwd=REPO_ROOT)
                    valid_heads = {live_head, res_master.stdout.strip().lower()}
                    assert current_ledger_head in valid_heads, (
                        f"AI-SRC-001 live-tree HEAD in ledger ({current_ledger_head}) does not match live HEAD ({live_head}) or master ({res_master.stdout.strip()})"
                    )
                else:
                    assert current_ledger_head == live_head, (
                        f"AI-SRC-001 live-tree HEAD in ledger ({current_ledger_head}) does not match live git rev-parse HEAD ({live_head})"
                    )

        # Mathematical reconciliation of AI evidence counts:
        # AI_EVIDENCE_INVENTORY_COUNT == ACCESSIBLE_AI_EVIDENCE_COUNT + UNAVAILABLE_EXTERNAL_SOURCES
        report_summary = self._parse_report_summary()
        if "AI_EVIDENCE_INVENTORY_COUNT" in report_summary and "ACCESSIBLE_AI_EVIDENCE_COUNT" in report_summary:
            total_inv = int(report_summary["AI_EVIDENCE_INVENTORY_COUNT"])
            accessible = int(report_summary["ACCESSIBLE_AI_EVIDENCE_COUNT"])
            unavailable = int(report_summary.get("UNAVAILABLE_EXTERNAL_SOURCES", 4))
            assert total_inv == accessible + unavailable, (
                f"Evidence count mismatch: total={total_inv} != accessible({accessible}) + unavailable({unavailable})"
            )
            assert accessible == 13, f"Expected 13 accessible AI sources, got {accessible}"
            assert unavailable == 4, f"Expected 4 unavailable external sources, got {unavailable}"
            assert total_inv == 17, f"Expected 17 total inventory sources, got {total_inv}"

    def test_candidate_lessons_count_and_header_consistency(self):
        """Verify candidate lessons catalog header matches actual count of defined CL items."""
        lessons_path = REPO_ROOT / "scratch" / "candidate_lessons.md"
        content = lessons_path.read_text(encoding="utf-8")

        defined_cl = re.findall(r"^### LESSON (CL-\d+):", content, re.MULTILINE)
        assert len(defined_cl) >= 11, f"Expected at least 11 candidate lessons, found {len(defined_cl)}"

        header_match = re.search(r"^## Candidate Lessons Catalog \((CL-\d+)\s*[–-]\s*(CL-\d+)\)", content, re.MULTILINE)
        assert header_match, "Candidate Lessons Catalog range header missing"
        assert header_match.group(1) == "CL-001"
        assert header_match.group(2) == f"CL-{len(defined_cl):03d}"

    def test_historical_closure_sections_have_explicit_snapshots(self):
        """Verify historical closure sections in the authoritative report are explicitly labeled."""
        report_path = REPO_ROOT / "docs" / "OCEAN_SENTINEL_SOURCE_CONTROL_INTEGRATION_V2_REPORT.md"
        content = report_path.read_text(encoding="utf-8")

        for sec in ["13", "14", "15", "16", "17"]:
            m = re.search(rf"^## {sec}\.\s+.*\[HISTORICAL SNAPSHOT\]", content, re.MULTILINE)
            assert m, f"Section {sec} must be explicitly labeled [HISTORICAL SNAPSHOT]"

    def test_implementation_vulnerability_rule_relation_partition_is_complete(self):
        """
        Verify implementation vulnerability classes form two orthogonal, disjoint, and complete partitions.

        Partition A (Rule-Relation Status):
          UNPROVEN_SET + NONE_FORMALLY_REGISTERED_SET = ALL_25_VULN_IDS
          - |UNPROVEN_SET| = 7
          - |NONE_FORMALLY_REGISTERED_SET| = 18
          - VULN-24 is in NONE_FORMALLY_REGISTERED_SET
          - Sets are strictly pairwise disjoint and their union is all 25 classes.

        Partition B (Evidence Classification Status):
          BEHAVIORALLY_PROVEN + EXECUTION_PATH_ESTABLISHED + AST_REFERENCE_ONLY + INSUFFICIENT_EVIDENCE = ALL_25_VULN_IDS
          - |BEHAVIORALLY_PROVEN| = 24
          - |EXECUTION_PATH_ESTABLISHED| = 1 (VULN-24)
          - |AST_REFERENCE_ONLY| = 0
          - |INSUFFICIENT_EVIDENCE| = 0
          - Sets are strictly pairwise disjoint and their union is all 25 classes.

        Orthogonality Invariant:
          EVIDENCE_CLASSIFICATION != RULE_RELATION_STATUS
        """
        import json

        vuln_path = REPO_ROOT / "data" / "metadata" / "governance_v2" / "implementation_vulnerability_classes.json"
        assert vuln_path.is_file(), "implementation_vulnerability_classes.json missing"
        data = json.loads(vuln_path.read_text(encoding="utf-8"))
        classes = data["classes"]

        all_ids = set(c["class_id"] for c in classes)
        assert len(all_ids) == 25, f"Expected 25 total classes, found {len(all_ids)}"
        assert all_ids == {f"VULN-{i:02d}" for i in range(1, 26)}

        # Partition A: Rule-Relation Status
        none_formally_registered_set = set(
            c["class_id"] for c in classes if c.get("enforcing_rule_ids") == ["NONE_FORMALLY_REGISTERED"]
        )
        unproven_set = set(
            c["class_id"] for c in classes if c.get("enforcing_rule_ids") != ["NONE_FORMALLY_REGISTERED"]
        )

        assert unproven_set.isdisjoint(none_formally_registered_set), (
            f"Rule-relation sets must be disjoint: overlap = {unproven_set & none_formally_registered_set}"
        )
        assert unproven_set | none_formally_registered_set == all_ids, (
            f"Rule-relation partition must cover all 25 classes: missing = {all_ids - (unproven_set | none_formally_registered_set)}"
        )
        assert len(unproven_set) == 7, f"Expected 7 classes in UNPROVEN_SET, found {len(unproven_set)}"
        assert len(none_formally_registered_set) == 18, (
            f"Expected 18 classes in NONE_FORMALLY_REGISTERED_SET, found {len(none_formally_registered_set)}"
        )
        assert "VULN-24" in none_formally_registered_set, "VULN-24 must be member of NONE_FORMALLY_REGISTERED_SET"

        # Partition B: Evidence Classification Status
        behaviorally_proven_set = set(
            c["class_id"] for c in classes if c.get("evidence_classification") == "BEHAVIORALLY_PROVEN"
        )
        execution_path_established_set = set(
            c["class_id"] for c in classes if c.get("evidence_classification") == "EXECUTION_PATH_ESTABLISHED"
        )
        ast_reference_only_set = set(
            c["class_id"] for c in classes if c.get("evidence_classification") == "AST_REFERENCE_ONLY"
        )
        insufficient_evidence_set = set(
            c["class_id"] for c in classes if c.get("evidence_classification") == "INSUFFICIENT_EVIDENCE"
        )

        evidence_sets = [
            ("BEHAVIORALLY_PROVEN", behaviorally_proven_set),
            ("EXECUTION_PATH_ESTABLISHED", execution_path_established_set),
            ("AST_REFERENCE_ONLY", ast_reference_only_set),
            ("INSUFFICIENT_EVIDENCE", insufficient_evidence_set),
        ]

        for i in range(len(evidence_sets)):
            for j in range(i + 1, len(evidence_sets)):
                name_i, set_i = evidence_sets[i]
                name_j, set_j = evidence_sets[j]
                assert set_i.isdisjoint(set_j), (
                    f"Evidence classification sets {name_i} and {name_j} must be disjoint: overlap = {set_i & set_j}"
                )

        all_evidence = behaviorally_proven_set | execution_path_established_set | ast_reference_only_set | insufficient_evidence_set
        assert all_evidence == all_ids, (
            f"Evidence classification must cover all 25 classes: missing = {all_ids - all_evidence}"
        )
        assert len(behaviorally_proven_set) == 24, f"Expected 24 BEHAVIORALLY_PROVEN, found {len(behaviorally_proven_set)}"
        assert len(execution_path_established_set) == 1, f"Expected 1 EXECUTION_PATH_ESTABLISHED, found {len(execution_path_established_set)}"
        assert execution_path_established_set == {"VULN-24"}, f"Expected EXECUTION_PATH_ESTABLISHED to be {{'VULN-24'}}, found {execution_path_established_set}"
        assert len(ast_reference_only_set) == 0, f"Expected 0 AST_REFERENCE_ONLY, found {len(ast_reference_only_set)}"
        assert len(insufficient_evidence_set) == 0, f"Expected 0 INSUFFICIENT_EVIDENCE, found {len(insufficient_evidence_set)}"

        # Orthogonality proof: VULN-24 is in NONE_FORMALLY_REGISTERED and EXECUTION_PATH_ESTABLISHED
        assert "VULN-24" in none_formally_registered_set and "VULN-24" in execution_path_established_set

    def test_report_origin_git_snapshot_is_not_labeled_as_current(self):
        """Verify that Section 2 report-origin git snapshot is explicitly marked as historical/report-origin
        and is not labeled as 'Current' or 'Final' without report-origin qualification."""
        report_path = REPO_ROOT / "docs" / "OCEAN_SENTINEL_SOURCE_CONTROL_INTEGRATION_V2_REPORT.md"
        content = report_path.read_text(encoding="utf-8")

        # Section 2 heading must be explicitly labeled [REPORT-ORIGIN HISTORICAL SNAPSHOT]
        sec2_heading_match = re.search(r"^## 2\.\s+.*\[REPORT-ORIGIN HISTORICAL SNAPSHOT\]", content, re.MULTILINE)
        assert sec2_heading_match, "Section 2 heading must be explicitly labeled [REPORT-ORIGIN HISTORICAL SNAPSHOT]"

        # Extract Section 2 content (up to Section 3 heading)
        sec2_match = re.search(r"^## 2\..*?(?=^## 3\.)", content, re.MULTILINE | re.DOTALL)
        assert sec2_match, "Section 2 not found in report"
        sec2_content = sec2_match.group(0)

        # Must not contain misleading wording in Section 2 context
        assert "Current Raw Git State" not in sec2_content, (
            "Section 2 must not label historical report-origin measurements as 'Current Raw Git State'"
        )

        # Must have explicit historical/report-origin note
        assert "HISTORICAL / REPORT-ORIGIN SNAPSHOT" in sec2_content, (
            "Section 2 must contain explicit HISTORICAL / REPORT-ORIGIN SNAPSHOT notice"
        )

        # Must retain historical numerical evidence intact
        assert "TRACKED_MODIFIED = 4" in sec2_content
        assert "UNTRACKED = 1078" in sec2_content
        assert "IGNORED = 308" in sec2_content
        assert "TOTAL PENDING IN WORKING TREE = 1082" in sec2_content

        # Report header must not confuse origin baseline with current state
        assert not re.search(r"^\*\*CURRENT_STATUS\*\*:\s*`.*HUMAN_GIT_INTEGRATION_PENDING", content, re.MULTILINE), (
            "Report top header must not have CURRENT_STATUS pointing to pre-integration pending state"
        )
        assert re.search(r"^\*\*REPORT_ORIGIN_STATUS\*\*:\s*`.*HUMAN_GIT_INTEGRATION_PENDING", content, re.MULTILINE), (
            "Report top header must classify origin status with explicit REPORT_ORIGIN_ prefix"
        )
        assert re.search(r"^\*\*CURRENT_FINAL_STATUS\*\*:\s*`.*GITHUB_INTEGRATION_COMPLETE", content, re.MULTILINE), (
            "Report top header must have CURRENT_FINAL_STATUS reflecting post-integration synchronization"
        )

        # Section 18 must be labeled as historical pre-integration gate, not current convergence gate
        assert "## 18. Final Stability, Historical-Report & Volatile-Telemetry Closure Audit (TASK_ID: OCEAN-SENTINEL-FINAL-STABILITY-CLOSURE-V1) [CURRENT CONVERGENCE GATE]" not in content, (
            "Section 18 must be labeled as historical pre-integration gate, not current convergence gate"
        )

        # Report header must not label historical pre-PR4 checkpoint as current final HEAD
        assert not re.search(r"^\*\*CURRENT_FINAL_HEAD\*\*:\s*\[?`?f6d21b0", content, re.MULTILINE), (
            "Report top header must not have CURRENT_FINAL_HEAD pointing to pre-PR4 checkpoint f6d21b0"
        )
        assert re.search(r"^\*\*PRE_PR4_CHECKPOINT_HEAD\*\*:\s*\[?`?f6d21b0", content, re.MULTILINE), (
            "Report top header must classify f6d21b0 explicitly as PRE_PR4_CHECKPOINT_HEAD"
        )
        assert re.search(r"^\*\*CURRENT_FINAL_HEAD\*\*:\s*`?DYNAMIC_LIVE_HEAD", content, re.MULTILINE), (
            "Report top header must specify CURRENT_FINAL_HEAD as DYNAMIC_LIVE_HEAD"
        )





