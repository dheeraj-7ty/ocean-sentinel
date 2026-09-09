"""
Verification script for EXP02B-1 Preflight Deployment (Items 1 - 8).
Audits git status, validates all cryptographic hashes against authorized CAO specifications,
and checks EXP02B-0 artifact integrity.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EXP02B_0_DIR = REPO_ROOT / "experiments" / "performance" / "exp02b_0_hard_negative_design_20260909_021500"

# CAO Authorized Hashes (Frozen Science Lock)
EXPECTED_HASHES = {
    "teacher_model": {
        "path": REPO_ROOT / "experiments" / "exp01_baseline" / "best_model.pt",
        "sha256": "9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699",
        "description": "Certified EXP01 Teacher Model Checkpoint",
    },
    "pretrained_imagenet_resnet34": {
        "path": Path(os.path.expanduser("~/.cache/torch/hub/checkpoints/resnet34-b627a593.pth")),
        "sha256": "B627A593BCBE140C234610266FE4F8AE95EA42FC881D091C9B6052E6B1D0590F",
        "description": "Torchvision Pretrained ResNet-34 ImageNet Weights",
    },
    "canonical_split_manifest": {
        "path": REPO_ROOT / "data" / "metadata" / "trujillo_2024" / "spatial_split_manifest.json",
        "sha256": "C052720A954C2E7A3E9A87AA64557450BF0DEABEC71D54C2A813849DB60812E0",
        "description": "Canonical Trujillo Spatial Split Manifest (13,440 train, 2,880 val, 2,880 test)",
    },
    "candidate_manifest": {
        "path": EXP02B_0_DIR / "candidate_manifest.json",
        "sha256": "5876A4E65FA636F6C0CD39377E56EEC6D9E848E8E48254927BE71ED4668B97E7",
        "description": "Approved EXP02B-0 13,440-tile Candidate Manifest",
    },
    "proposed_sampling_policy": {
        "path": EXP02B_0_DIR / "proposed_sampling_policy.md",
        "sha256": "F4F40D921238EC34EE5F33A413D22CFB5138015F133E57BD74532B4ADAF42FC9",
        "description": "Approved Proposed Sampling Policy Document",
    },
    "proposed_success_criteria": {
        "path": EXP02B_0_DIR / "proposed_success_criteria.md",
        "sha256": "DD777D1D51C2751A5F7C6E960B941A83A4783435D0B4E9BA9FF0AE9053961D29",
        "description": "Approved Pre-registered Success Criteria & Decision Hierarchy",
    },
    "experiment_identity": {
        "path": EXP02B_0_DIR / "experiment_identity.json",
        "sha256": "D78497BC951348D6E5CA078648D34F040F43B7FBABB4C756B2CC1D256A7EC44C",
        "description": "EXP02B-0 Authoritative Experiment Identity Metadata",
    },
    "gate_exp02b_0_report": {
        "path": EXP02B_0_DIR / "GATE_EXP02B_0_REPORT.md",
        "sha256": "BB787BE720BCCBF3BBDD27DD3E204C64BFFC4D11070C4E8A901197D82B36C502",
        "description": "EXP02B-0 Formal Gate Closure Report",
    },
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest().upper()


def audit_git() -> dict:
    status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=REPO_ROOT)
    diff = subprocess.run(["git", "diff", "--stat"], capture_output=True, text=True, cwd=REPO_ROOT)
    branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, cwd=REPO_ROOT)
    head_commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=REPO_ROOT)

    return {
        "branch": branch.stdout.strip(),
        "head_commit": head_commit.stdout.strip(),
        "porcelain_status": status.stdout.strip().splitlines(),
        "diff_summary": diff.stdout.strip(),
    }


def main():
    print("=" * 80)
    print("EXP02B-1 DEPLOYMENT PREFLIGHT AUDIT (ITEMS 1-8)")
    print("=" * 80)

    # 1. Git status audit
    git_info = audit_git()
    print(f"\n[ITEM 1] Git Audit:")
    print(f"  Branch:      {git_info['branch']}")
    print(f"  HEAD Commit: {git_info['head_commit']}")
    print(f"  Dirty Files: {len(git_info['porcelain_status'])}")

    # 2 - 8. Cryptographic Hash Audit
    print(f"\n[ITEMS 2-8] Cryptographic Hash Verification:")
    all_passed = True
    audit_results = {}

    for key, spec in EXPECTED_HASHES.items():
        path = spec["path"]
        expected_sha = spec["sha256"]
        desc = spec["description"]

        if not path.exists():
            print(f"  [FAIL] {key}: File NOT FOUND -> {path}")
            all_passed = False
            audit_results[key] = {"status": "NOT_FOUND", "path": str(path)}
            continue

        actual_sha = sha256_file(path)
        file_size = path.stat().st_size
        matches = actual_sha == expected_sha

        if matches:
            status_tag = "[PASS]"
        else:
            status_tag = "[FAIL]"
            all_passed = False

        print(f"  {status_tag} {key}:")
        print(f"         Path:   {path.relative_to(REPO_ROOT) if path.is_relative_to(REPO_ROOT) else path}")
        print(f"         Size:   {file_size:,} bytes")
        print(f"         Actual: {actual_sha}")
        print(f"         Expect: {expected_sha}")

        audit_results[key] = {
            "status": "PASS" if matches else "FAIL",
            "size": file_size,
            "actual_sha256": actual_sha,
            "expected_sha256": expected_sha,
        }

    # 9. Verify candidate manifest contents
    print("\n[VERIFICATION] Candidate Manifest Internal Consistency:")
    cand_path = EXPECTED_HASHES["candidate_manifest"]["path"]
    with open(cand_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    n_pos = sum(1 for r in records if r["final_classification"] == "positive_spill_tile")
    n_hard = sum(1 for r in records if r["final_classification"] == "candidate_hard_negative")
    n_ord = sum(1 for r in records if r["final_classification"] == "ordinary_gt_negative")
    total = len(records)

    print(f"  Total records:           {total} (expected: 13440) -> {'PASS' if total == 13440 else 'FAIL'}")
    print(f"  Positive spill tiles:    {n_pos} (expected: 5083)  -> {'PASS' if n_pos == 5083 else 'FAIL'}")
    print(f"  Candidate hard negatives: {n_hard} (expected: 1605)  -> {'PASS' if n_hard == 1605 else 'FAIL'}")
    print(f"  Ordinary GT negatives:   {n_ord} (expected: 6752)  -> {'PASS' if n_ord == 6752 else 'FAIL'}")

    # Verify weights
    w_pos = {r["sampling_weight"] for r in records if r["final_classification"] == "positive_spill_tile"}
    w_hard = {r["sampling_weight"] for r in records if r["final_classification"] == "candidate_hard_negative"}
    w_ord = {r["sampling_weight"] for r in records if r["final_classification"] == "ordinary_gt_negative"}

    print(f"  Positive weight:         {w_pos} (expected: {{1.0}})  -> {'PASS' if w_pos == {1.0} else 'FAIL'}")
    print(f"  Hard negative weight:    {w_hard} (expected: {{2.25}}) -> {'PASS' if w_hard == {2.25} else 'FAIL'}")
    print(f"  Ordinary negative weight:{w_ord} (expected: {{0.75}}) -> {'PASS' if w_ord == {0.75} else 'FAIL'}")

    counts_pass = (total == 13440 and n_pos == 5083 and n_hard == 1605 and n_ord == 6752)
    weights_pass = (w_pos == {1.0} and w_hard == {2.25} and w_ord == {0.75})

    overall_pass = all_passed and counts_pass and weights_pass
    print("\n" + "=" * 80)
    print(f"PREFLIGHT AUDIT RESULT (ITEMS 1-8): {'PASS' if overall_pass else 'FAIL'}")
    print("=" * 80)

    # Write audit report
    out_json = REPO_ROOT / "experiments" / "performance" / "exp02b_1_preflight_audit.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "audit_timestamp_utc": subprocess.check_output(
            ["python", "-c", "import time; print(time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))"],
            text=True
        ).strip(),
        "git_audit": git_info,
        "hash_audit": audit_results,
        "candidate_counts": {
            "total": total,
            "positive_spill_tiles": n_pos,
            "candidate_hard_negatives": n_hard,
            "ordinary_gt_negatives": n_ord,
        },
        "sampling_weights": {
            "w_pos": list(w_pos),
            "w_hard_neg": list(w_hard),
            "w_ord_neg": list(w_ord),
        },
        "preflight_status": "PASS" if overall_pass else "FAIL",
    }
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Preflight audit report written to: {out_json}")

    if not overall_pass:
        sys.exit(1)


if __name__ == "__main__":
    main()
