import json
import os
from pathlib import Path
import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent

def test_radiometric_lineage_artifact_exists():
    path = ROOT_DIR / "experiments" / "EXP-07" / "EXP07_RADIOMETRIC_LINEAGE_RECONCILIATION.json"
    assert path.exists(), f"Missing {path}"
    with open(path) as f:
        data = json.load(f)
    assert data["metadata"]["status"] == "VERIFIED_AND_BOUNDED"
    assert data["executive_summary"]["executed_representation_across_all_runs"] == "AGGREGATED_RAW_DN_LOG1P_STANDARDIZED"

def test_claims_audit_artifact_exists():
    path = ROOT_DIR / "experiments" / "EXP-07" / "EXP07_CLAIMS_AUDIT.json"
    assert path.exists(), f"Missing {path}"
    with open(path) as f:
        data = json.load(f)
    assert "claims" in data
    assert len(data["claims"]) >= 10
    for claim in data["claims"]:
        assert "claim_id" in claim
        assert "allowed_wording" in claim
        assert "action" in claim

def test_report_avoids_prohibited_overclaims():
    path = ROOT_DIR / "experiments" / "EXP-07" / "EXP07_FINAL_FORENSIC_TRIAGE_REPORT.md"
    assert path.exists(), f"Missing {path}"
    with open(path, encoding="utf-8") as f:
        content = f.read().lower()

    prohibited = [
        "loss weighting has proven futile",
        "orders of magnitude inadequate",
        "hundreds of thousands of annotations required",
        "proven binary oil detector (exp-06)",
        "a falsified experiment protocol justifies",
        "the implementation is bug-free",
        "variation between random seeds is roughly 300x"
    ]
    for term in prohibited:
        assert term not in content, f"Report contains prohibited overclaim: {term}"

def test_candidate_lessons_tagged_non_authoritative():
    path = ROOT_DIR / "scratch" / "exp07_final_forensic_triage_lessons.md"
    assert path.exists(), f"Missing {path}"
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "NON_AUTHORITATIVE / PROPOSED_ONLY" in content
    assert "GOV-RULE-026" in content

def test_corrective_lessons_exist():
    path = ROOT_DIR / "scratch" / "exp07_final_forensic_corrective_lessons.md"
    assert path.exists(), f"Missing {path}"
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "NON_AUTHORITATIVE / PROPOSED_ONLY" in content
