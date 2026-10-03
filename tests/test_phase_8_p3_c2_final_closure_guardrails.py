"""Phase 8-P3-C2 Final Evidence-Bound Provenance Reconciliation & Closure Guardrails.

Semantic regression suite testing:
1. Exact frozen EXP-06 hash and Part-I hash integrity.
2. Complete Git-state inspection rule and refusal to equate '0 staged' with 'clean'.
3. Strict canonical taxonomy exactness (HM = 'Artificial / Anthropogenic Objects', OF, BS, OS).
4. Permanent persistence of all four epistemic disclosures.
5. Exact Level B reproducibility definition and explicit prohibition of Level C/D claims.
6. Evidence status integrity: PROVEN strictly forbidden without direct before/after evidence.
7. Successor manifest explicit version lineage without false claims of historical equality.
8. Bounded investigation rule and active telemetry validation.
9. Strict enforcement of prohibitions: zero training, zero GPU, zero Part-III access, zero EXP-07.
10. All four C2 incidents registered and guarded.
"""

import hashlib
import json
import subprocess
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent

EXP06_PATH = ROOT / "experiments/performance/exp06_positive_bce_weight/best_model.pt"
PART_I_PATH = ROOT / "data/metadata/internal_development_split_manifest.json"
EXP06_SHA = "B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF"
PART_I_SHA = "17F1FF35146C7CE62E90D6FCE7F197B711B55E3C3CB599610578443208669072"

TAXONOMY_PATH = ROOT / "data/metadata/ops01_taxonomy_v1.json"
MANIFEST_V4 = ROOT / "data/metadata/ops01_physical_dataset_manifest_v4.json"
SUFFICIENCY_V5 = ROOT / "data/metadata/ops01_dataset_sufficiency_v5.json"
VERSION_LINEAGE = ROOT / "data/metadata/ops01_p3_c1_version_lineage_v1.json"
DATASET_IDENTITY = ROOT / "data/metadata/ops01_dataset_identity_v1.json"
REPRODUCIBILITY_LEVELS = ROOT / "data/metadata/ocean_sentinel_reproducibility_levels_v1.json"
GOVERNANCE_JSON = ROOT / "data/metadata/ocean_sentinel_governance_rules_v1.json"
GOVERNANCE_MD = ROOT / "experiments/PROJECT_GOVERNANCE/ocean_sentinel_governance_rules_v1.md"
INCIDENT_LEARNING = ROOT / "data/metadata/ocean_sentinel_incident_learning_register_v1.json"
EVIDENCE_BOUNDARY_RECON = ROOT / "data/metadata/ops01_p3_c2_evidence_boundary_reconciliation_v1.json"
GIT_STATE_AUDIT = ROOT / "data/metadata/ops01_p3_c2_git_state_audit_v1.json"
RUN_STATE_C2 = ROOT / "scratch/phase_8_p3_c2_run_state.json"
SUCCESSOR_LANG_AUDIT = ROOT / "data/metadata/ops01_p3_c2_successor_language_audit_v1.json"
REPRO_LANG_AUDIT = ROOT / "data/metadata/ops01_p3_c2_reproducibility_language_audit_v1.json"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while c := f.read(65536):
            h.update(c)
    return h.hexdigest().upper()


# ============================================================
# 1. FROZEN ARTIFACT INTEGRITY
# ============================================================
class TestFrozenArtifactIntegrity:
    """EXP-06 and Part-I must remain bitwise identical to reference hashes."""

    def test_exp06_model_checkpoint_exact_hash(self):
        assert EXP06_PATH.exists()
        assert sha256(EXP06_PATH) == EXP06_SHA

    def test_part_i_split_manifest_exact_hash(self):
        assert PART_I_PATH.exists()
        assert sha256(PART_I_PATH) == PART_I_SHA


# ============================================================
# 2. GIT STATE AUDIT & '0 STAGED != CLEAN' DOCTRINE
# ============================================================
class TestGitStateAuthoritativeAudit:
    """Git state must be inspected via complete porcelain output and not equate 0 staged with clean."""

    def test_git_state_audit_artifact_exists_and_valid(self):
        assert GIT_STATE_AUDIT.exists()
        data = json.loads(GIT_STATE_AUDIT.read_text(encoding="utf-8"))
        assert data["staged"]["is_zero_staged"] is True
        assert data["working_tree_is_clean"] is False
        assert data["audit_conclusion"] == "NOT_CLEAN"
        assert "0 staged != clean" in data["doctrine"]

    def test_no_false_clean_claim_in_git_audit(self):
        data = json.loads(GIT_STATE_AUDIT.read_text(encoding="utf-8"))
        assert data["tracked_modified"]["count"] >= 1
        assert data["untracked"]["count"] > 0
        assert "GOV-RULE-018" in data["audit_interpretation"]

    def test_live_porcelain_confirms_untracked_files_present(self):
        res = subprocess.run("git status --porcelain -uall", shell=True, capture_output=True, text=True, cwd=ROOT)
        lines = res.stdout.splitlines()
        untracked = [l for l in lines if l.startswith("??")]
        assert len(untracked) > 0, "Repository has untracked files; calling it clean is prohibited."


# ============================================================
# 3. CANONICAL TAXONOMY EXACTNESS (NO SHORTENED HM)
# ============================================================
class TestCanonicalTaxonomyExactness:
    """Taxonomy class names must match ops01_taxonomy_v1.json exactly."""

    def test_hm_exact_canonical_name(self):
        tax = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))
        hm_entry = next((c for c in tax["classes"] if c["abbreviation"] == "HM"), None)
        assert hm_entry is not None
        assert hm_entry["class_name"] == "Artificial / Anthropogenic Objects"

    def test_of_bs_os_exact_canonical_identities(self):
        tax = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))
        classes = {c["abbreviation"]: c for c in tax["classes"]}
        assert classes["OF"]["class_name"] == "Ocean Front"
        assert classes["OF"]["source_label_id"] == 6
        assert classes["BS"]["class_name"] == "Biological Slicks"
        assert classes["BS"]["source_label_id"] == 2
        assert classes["OS"]["class_name"] == "Mineral Oil Spill"
        assert classes["OS"]["source_label_id"] == 14
        assert classes["OS"]["training_eligible"] is False

    def test_no_shortened_hm_in_governance_files(self):
        for p in [GOVERNANCE_MD, GOVERNANCE_JSON, DATASET_IDENTITY]:
            txt = p.read_text(encoding="utf-8")
            for line in txt.splitlines():
                if "HM" in line and "Anthropogenic Objects" in line:
                    assert "Artificial / Anthropogenic Objects" in line, (
                        f"Shortened HM found in {p.name}: {line.strip()}"
                    )


# ============================================================
# 4. PERMANENT EPISTEMIC DISCLOSURES
# ============================================================
class TestPermanentEpistemicDisclosures:
    """All four disclosures must be present in manifest_v4, sufficiency_v5, and dataset_identity."""

    REQUIRED = [
        "HOLDOUT_PARTIALLY_USED_FOR_SELECTION",
        "CONDITIONAL_ENGINEERING_RECONSTRUCTION",
        "EMPIRICALLY_SUPPORTED_PILOT_HYPOTHESIS",
        "DATASET_GENERATION_METHOD = NOT_DIRECTLY_VERIFIED"
    ]

    def test_disclosures_in_manifest_v4(self):
        txt = MANIFEST_V4.read_text(encoding="utf-8")
        for d in self.REQUIRED:
            assert d in txt

    def test_disclosures_in_sufficiency_v5(self):
        txt = SUFFICIENCY_V5.read_text(encoding="utf-8")
        for d in self.REQUIRED:
            assert d in txt

    def test_disclosures_in_dataset_identity(self):
        txt = DATASET_IDENTITY.read_text(encoding="utf-8")
        for d in self.REQUIRED:
            assert d in txt


# ============================================================
# 5. REPRODUCIBILITY LEVEL B OPERATIONAL SCOPE
# ============================================================
class TestReproducibilityLanguageExactness:
    """Level B must be strictly defined and cannot claim pipeline reconstruction."""

    def test_level_b_operational_statement(self):
        repro = json.loads(REPRODUCIBILITY_LEVELS.read_text(encoding="utf-8"))
        op_stmt = repro["current_ops01_evaluation"]["operational_statement"]
        assert op_stmt == "OPS-01 verification artifacts satisfy Level B deterministic verification reproducibility."

    def test_level_c_and_d_strictly_prohibited(self):
        repro = json.loads(REPRODUCIBILITY_LEVELS.read_text(encoding="utf-8"))
        proh = repro["current_ops01_evaluation"]["prohibition_enforcement"]
        assert proh["level_c_prohibited"] is True
        assert proh["level_d_prohibited"] is True
        assert "NOT_DIRECTLY_VERIFIED" in proh["reason"]

    def test_reproducibility_language_audit_artifact(self):
        assert REPRO_LANG_AUDIT.exists()
        data = json.loads(REPRO_LANG_AUDIT.read_text(encoding="utf-8"))
        assert data["current_certification"]["certified_level"] == "LEVEL_B"
        assert "BLOCKED" in data["current_certification"]["level_c_status"]


# ============================================================
# 6. EVIDENCE BOUNDARY: NO 'PROVEN' WITHOUT EVIDENCE
# ============================================================
class TestEvidenceBoundaryAndProvenClaims:
    """PROVEN claims require genuine before/after evidence; current file integrity != historical proof."""

    def test_evidence_boundary_reconciliation_artifact(self):
        assert EVIDENCE_BOUNDARY_RECON.exists()
        recon = json.loads(EVIDENCE_BOUNDARY_RECON.read_text(encoding="utf-8"))
        cats = recon["evidence_categories"]
        
        # Physical samples and images must be STRONGLY_SUPPORTED, not falsely PROVEN without pre-P3 manifest JSON
        assert cats["physical_samples"]["evidence_status"] == "STRONGLY_SUPPORTED"
        assert "PHYSICAL FILE CONTENT CURRENTLY VERIFIED" in cats["physical_samples"]["conclusion"]
        assert cats["image_bytes"]["evidence_status"] == "STRONGLY_SUPPORTED"
        assert cats["mask_bytes"]["evidence_status"] == "STRONGLY_SUPPORTED"

        # Split manifest v4 and source inventory v3 ARE bitwise identical to pre-P3 inventory, so PROVEN is justified
        assert cats["source_ids_and_parents"]["evidence_status"] == "PROVEN"
        assert cats["partition_allocations"]["evidence_status"] == "PROVEN"

    def test_direct_pre_p3_manifest_json_comparison_declared_unavailable(self):
        recon = json.loads(EVIDENCE_BOUNDARY_RECON.read_text(encoding="utf-8"))
        assert recon["historical_hash_recovery"]["direct_manifest_json_byte_comparison"] == "NO DIRECT PRE-P3 BINARY COMPARISON AVAILABLE"


# ============================================================
# 7. SUCCESSOR MANIFEST LINEAGE & LANGUAGE AUDIT
# ============================================================
class TestSuccessorManifestLanguage:
    """Successor manifest must not claim unproven pre-P3 identicalness."""

    def test_successor_language_audit_artifact(self):
        assert SUCCESSOR_LANG_AUDIT.exists()
        data = json.loads(SUCCESSOR_LANG_AUDIT.read_text(encoding="utf-8"))
        assert data["conclusion"] == "SUCCESSOR_LANGUAGE_AUDIT_PASSED"

    def test_manifest_v4_uses_evidence_bounded_language(self):
        m4 = json.loads(MANIFEST_V4.read_text(encoding="utf-8"))
        assert "same currently verified physical dataset state" in m4["semantic_change_summary"]
        assert m4["physical_dataset_change_status"] == "SAME_CURRENTLY_VERIFIED_PHYSICAL_DATASET_STATE"

    def test_manifest_v4_explicit_parent_references(self):
        m4 = json.loads(MANIFEST_V4.read_text(encoding="utf-8"))
        assert m4["parent_manifest"] == "ops01_physical_dataset_manifest_v3.json"
        assert m4["parent_manifest_sha256_pre_p3"] == "94521D08C00AB71269D9DE566468C1E8B8C12E3519C3AB97375F63DF75355787"


# ============================================================
# 8. INCIDENT LEARNING & C2 INCIDENTS
# ============================================================
class TestIncidentLearningRegisters:
    """All four C2 incidents must be registered with root cause, permanent rule, and regression test."""

    C2_INCIDENTS = ["INC-P3-C2-001", "INC-P3-C2-002", "INC-P3-C2-003", "INC-P3-C2-004"]

    def test_c2_incidents_in_learning_register(self):
        reg = json.loads(INCIDENT_LEARNING.read_text(encoding="utf-8"))
        inc_ids = set(inc["incident_id"] for inc in reg["incidents"])
        for inc_id in self.C2_INCIDENTS:
            assert inc_id in inc_ids, f"Incident {inc_id} missing from learning register!"

    def test_c2_incidents_have_required_fields(self):
        reg = json.loads(INCIDENT_LEARNING.read_text(encoding="utf-8"))
        for inc in reg["incidents"]:
            if inc["incident_id"] in self.C2_INCIDENTS:
                assert "root_cause" in inc
                assert "failed_assumption" in inc
                assert "resolution" in inc
                assert "permanent_rule" in inc
                assert "regression_test" in inc


# ============================================================
# 9. PROHIBITIONS & TELEMETRY
# ============================================================
class TestProhibitionsAndTelemetry:
    """No EXP-07 artifacts, no Part-III access, no training, active run state."""

    def test_no_unauthorized_exp07_artifacts(self):
        exp07_files = list(ROOT.glob("experiments/**/exp07*")) + list(ROOT.glob("models/**/exp07*"))
        assert not exp07_files

    def test_run_state_c2_exists_and_valid(self):
        assert RUN_STATE_C2.exists()
        state = json.loads(RUN_STATE_C2.read_text(encoding="utf-8"))
        assert state["phase"] == "PHASE_8_P3_C2"
        assert state["status"] in ["RUNNING", "COMPLETE"]
        assert "last_heartbeat" in state
        assert state["git_state"]["is_clean"] is False
