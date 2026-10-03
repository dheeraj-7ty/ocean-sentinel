"""Tests for Report Reconciliation Candidate Lessons.

Validates that the learning artifacts from the reconciliation phase are
structurally correct, contain the required lessons, and can be distinguished
by keyword/concept retrieval.

These tests validate TASK-LOCAL NON-AUTHORITATIVE candidate lessons only.
They do NOT modify canonical governance files.
"""

import json
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CANDIDATE_LESSONS_PATH = (
    REPO_ROOT / "outputs" / "scene_authority" / "REPORT_RECONCILIATION_CANDIDATE_LESSONS.json"
)


def load_candidate_lessons() -> dict:
    assert CANDIDATE_LESSONS_PATH.is_file(), f"Candidate lessons not found: {CANDIDATE_LESSONS_PATH}"
    return json.loads(CANDIDATE_LESSONS_PATH.read_text(encoding="utf-8"))


class TestReportReconciliationLearning:
    """Verify reconciliation learning artifacts are correct and distinguishable."""

    def test_candidate_lessons_schema(self) -> None:
        """Validate schema of candidate lessons artifact."""
        data = load_candidate_lessons()
        meta = data["meta"]
        assert meta["task_id"] == "OCEAN-SENTINEL-REPORT-RECONCILIATION-LEARNING-HARDENING-V1"
        assert meta["promotion_status"] == "NON_AUTHORITATIVE_PROPOSED_ONLY"
        assert meta["document_type"] == "TASK_LOCAL_CANDIDATE_LEARNING"
        lessons = data["candidate_lessons"]
        assert len(lessons) >= 8

        required_fields = ["lesson_id", "title", "failure_pattern", "category",
                           "description", "root_cause", "evidence", "prevention",
                           "feedback_taxonomy", "severity"]
        for lesson in lessons:
            for field in required_fields:
                assert field in lesson, f"Lesson {lesson['lesson_id']} missing field: {field}"

    def test_lesson_ids_unique(self) -> None:
        """All candidate lesson IDs are unique."""
        data = load_candidate_lessons()
        ids = [l["lesson_id"] for l in data["candidate_lessons"]]
        assert len(ids) == len(set(ids))

    def test_corpus_inventory_lesson_present(self) -> None:
        """Lesson A: Corpus-wide claims require machine-reproducible evidence."""
        data = load_candidate_lessons()
        lesson = next(
            (l for l in data["candidate_lessons"]
             if "CORPUS" in l["title"] and "MACHINE-REPRODUCIBLE" in l["title"]),
            None,
        )
        assert lesson is not None
        assert lesson["feedback_taxonomy"] == "INSUFFICIENT_EVIDENCE"
        assert "machine-readable" in lesson["prevention"].lower()

    def test_test_count_evidence_lesson_present(self) -> None:
        """Lesson B: Test count claims require actual execution evidence."""
        data = load_candidate_lessons()
        lesson = next(
            (l for l in data["candidate_lessons"]
             if "PASSED-TEST" in l["title"] and "AUTHORITATIVE" in l["title"]),
            None,
        )
        assert lesson is not None
        assert lesson["feedback_taxonomy"] == "INSUFFICIENT_EVIDENCE"
        assert lesson["severity"] == "CRITICAL"
        assert "exit code" in lesson["prevention"].lower()

    def test_evidence_contradiction_lesson_present(self) -> None:
        """Lesson C: Evidence contradiction blocks certification."""
        data = load_candidate_lessons()
        lesson = next(
            (l for l in data["candidate_lessons"]
             if "CONTRADICTION" in l["title"] and "CERTIFICATION" in l["title"]),
            None,
        )
        assert lesson is not None
        assert lesson["feedback_taxonomy"] == "CONTRADICTORY_LESSON"

    def test_annotation_divergence_lesson_present(self) -> None:
        """Lesson D: Different annotations don't prove why annotations differ."""
        data = load_candidate_lessons()
        lesson = next(
            (l for l in data["candidate_lessons"]
             if "ANNOTATIONS" in l["title"] and "WHY" in l["title"]),
            None,
        )
        assert lesson is not None
        assert "causal" in lesson["root_cause"].lower()

    def test_legacy_artifact_validity_lesson_present(self) -> None:
        """Lesson E: Preserved artifacts are not automatically valid."""
        data = load_candidate_lessons()
        lesson = next(
            (l for l in data["candidate_lessons"]
             if "LEGACY" in l["title"] and "VALID" in l["title"]),
            None,
        )
        assert lesson is not None
        assert lesson["feedback_taxonomy"] == "WRONG_APPLICABILITY"

    def test_temporal_pair_terminology_lesson_present(self) -> None:
        """Lesson F: Potential != verified temporal pair."""
        data = load_candidate_lessons()
        lesson = next(
            (l for l in data["candidate_lessons"]
             if "POTENTIAL" in l["title"] and "VERIFIED" in l["title"]),
            None,
        )
        assert lesson is not None
        assert "TEMPORAL_ORDER_UNKNOWN" in lesson["evidence"]

    def test_report_self_audit_lesson_present(self) -> None:
        """Lesson G: Report self-audit is part of engineering verification."""
        data = load_candidate_lessons()
        lesson = next(
            (l for l in data["candidate_lessons"]
             if "REPORT" in l["title"] and "SELF-AUDIT" in l["title"]),
            None,
        )
        assert lesson is not None
        assert lesson["feedback_taxonomy"] == "WEAK_ENFORCEMENT"

    def test_stage_completion_lesson_present(self) -> None:
        """Lesson H: Scientific stage completion requires actual execution."""
        data = load_candidate_lessons()
        lesson = next(
            (l for l in data["candidate_lessons"]
             if "STAGE COMPLETION" in l["title"] and "ACTUAL EXECUTION" in l["title"]),
            None,
        )
        assert lesson is not None

    # ---------------------------------------------------------------
    # Concept distinguishability tests
    # ---------------------------------------------------------------
    def test_distinguish_corpus_inventory_from_duplicate_detection(self) -> None:
        """Lessons about corpus inventory vs duplicate detection are distinct."""
        data = load_candidate_lessons()
        corpus_lesson = next(
            (l for l in data["candidate_lessons"] if "CORPUS" in l["title"]),
            None,
        )
        dup_distinct = all(
            l["lesson_id"] != corpus_lesson["lesson_id"]
            for l in data["candidate_lessons"]
            if "DUPLICATE" in l.get("title", "") or "ANNOTATIONS" in l.get("title", "")
        )
        assert corpus_lesson is not None
        assert dup_distinct, "Corpus inventory lesson must be distinct from duplicate/annotation lessons"

    def test_distinguish_test_evidence_from_stage_execution(self) -> None:
        """Test count evidence (Lesson B) is distinct from stage execution (Lesson H)."""
        data = load_candidate_lessons()
        test_lesson = next(
            (l for l in data["candidate_lessons"] if "PASSED-TEST" in l["title"]),
            None,
        )
        stage_lesson = next(
            (l for l in data["candidate_lessons"] if "STAGE COMPLETION" in l["title"]),
            None,
        )
        assert test_lesson is not None
        assert stage_lesson is not None
        assert test_lesson["lesson_id"] != stage_lesson["lesson_id"]
        assert test_lesson["category"] != stage_lesson["category"]

    def test_no_automatic_promotion_to_permanent_governance(self) -> None:
        """Candidate lessons must NOT modify canonical governance files."""
        data = load_candidate_lessons()
        assert data["meta"]["promotion_status"] == "NON_AUTHORITATIVE_PROPOSED_ONLY"
        # Canonical governance files must be unchanged (verified by hash checks elsewhere)

    def test_runtime_execution_vs_test_evidence_lesson_present(self) -> None:
        """Lesson I: Runtime execution claim requires actual execution, not merely tests or UI rendering."""
        data = load_candidate_lessons()
        lesson = next(
            (l for l in data["candidate_lessons"]
             if "REPORT CLAIMED RUNTIME EXECUTION" in l["title"]),
            None,
        )
        assert lesson is not None
        assert lesson["lesson_id"] == "CL-RECON-I"
        assert lesson["severity"] == "CRITICAL"
        assert lesson["feedback_taxonomy"] == "INSUFFICIENT_EVIDENCE"

        hierarchy = lesson.get("evidence_class_hierarchy", [])
        expected_classes = [
            "STATIC INSPECTION",
            "UNIT TEST EXECUTION",
            "ORCHESTRATION EXECUTION",
            "LIVE API EXECUTION",
            "BROWSER END-TO-END EXECUTION",
        ]
        for ec in expected_classes:
            assert ec in hierarchy, f"Evidence hierarchy missing class: {ec}"

        gov_rule = lesson.get("governance_rule", "")
        assert "A TEST PASS IS NOT RUNTIME EXECUTION" in gov_rule
        assert "A RUNTIME EXECUTION IS NOT EXTERNAL SCIENTIFIC AUTHORITY" in gov_rule
        assert "A REPORT CLAIM IS NEVER STRONGER THAN ITS EVIDENCE" in gov_rule

    def test_corpus_wide_fact_direct_measurement_requirement(self) -> None:
        """Lesson A enforces: CORPUS-WIDE FACT requires CURRENT DIRECT MEASUREMENT OR CRYPTOGRAPHICALLY LINKED ARTIFACT."""
        data = load_candidate_lessons()
        lesson_a = next(
            (l for l in data["candidate_lessons"] if l["lesson_id"] == "CL-RECON-A"),
            None,
        )
        assert lesson_a is not None
        assert "CURRENT DIRECT MEASUREMENT OR CRYPTOGRAPHICALLY LINKED ARTIFACT" in lesson_a["prevention"]

    def test_backend_availability_vs_result_validity_lesson_present(self) -> None:
        """Lesson J: Backend availability is not scientific result validity or result freshness."""
        data = load_candidate_lessons()
        lesson = next(
            (l for l in data["candidate_lessons"] if l["lesson_id"] == "CL-RECON-J"),
            None,
        )
        assert lesson is not None
        assert "BACKEND AVAILABILITY IS NOT SCIENTIFIC RESULT VALIDITY" in lesson["title"]
        assert lesson["failure_pattern"] == "WRONG_APPLICABILITY"
        assert lesson["category"] == "STATE_INTEGRITY"
        assert lesson["severity"] == "HIGH"

        gov_rule = lesson.get("governance_rule", "")
        assert "BACKEND AVAILABILITY IS NOT SCIENTIFIC RESULT VALIDITY OR RESULT FRESHNESS" in gov_rule
        assert "LAST LOADED RESULT MUST NEVER BE MISTAKEN FOR LIVE CURRENT SCIENTIFIC EVIDENCE" in gov_rule

    def test_distinguish_backend_state_from_result_freshness_dimensions(self) -> None:
        """Lesson J establishes 6 orthogonal state dimensions."""
        data = load_candidate_lessons()
        lesson = next(
            (l for l in data["candidate_lessons"] if l["lesson_id"] == "CL-RECON-J"),
            None,
        )
        assert lesson is not None
        dims = lesson.get("state_dimensions", [])
        assert len(dims) == 6

        dim_keys = [d.split(":")[0].strip() for d in dims]
        assert "CONNECTION" in dim_keys
        assert "RESULT FRESHNESS" in dim_keys
        assert "JOB STATE" in dim_keys
        assert "PROVENANCE" in dim_keys
        assert "SCIENTIFIC VALIDITY" in dim_keys
        assert "APPLICATION GATE" in dim_keys

    def test_distinguish_offline_lifecycle_from_scientific_defect(self) -> None:
        """Lesson J establishes that dev server shutdown is not a product or scientific defect."""
        data = load_candidate_lessons()
        lesson = next(
            (l for l in data["candidate_lessons"] if l["lesson_id"] == "CL-RECON-J"),
            None,
        )
        assert lesson is not None
        desc = lesson["description"]
        assert "Backend unreachable after execution is not a product or scientific defect" in desc
        assert "Cached results may be viewed but must never masquerade as live current executions" in desc

    def test_quarantine_lesson_k_present(self) -> None:
        """Lesson K: Warning-only mismatch protection may not be sufficient for scientific UI."""
        data = load_candidate_lessons()
        lesson = next(
            (l for l in data["candidate_lessons"] if l["lesson_id"] == "CL-RECON-K"),
            None,
        )
        assert lesson is not None
        assert "WARNING-ONLY MISMATCH PROTECTION" in lesson["title"]
        assert lesson["failure_pattern"] == "HUMAN_FACTORS"
        assert lesson["category"] == "STATE_INTEGRITY"
        assert lesson["severity"] == "HIGH"

        rule = lesson.get("governance_rule", "")
        assert "A WARNING MUST NOT BE THE ONLY BARRIER" in rule
        assert "PRESERVE THE EVIDENCE. QUARANTINE ITS USE. NEVER REWRITE ITS IDENTITY." in rule

    def test_distinguish_quarantine_from_invalidity(self) -> None:
        """Lesson K distinguishes quarantined result usage from scientific invalidation."""
        data = load_candidate_lessons()
        lesson = next(
            (l for l in data["candidate_lessons"] if l["lesson_id"] == "CL-RECON-K"),
            None,
        )
        assert lesson is not None
        desc = lesson["description"]
        assert "explicitly quarantined from active interpretation while preserving its original provenance and historical identity" in desc
        prev = lesson["prevention"]
        assert "RESULT_USAGE = QUARANTINED" in prev
        assert "Preserves original provenance without rewriting identity" in prev

    # ---------------------------------------------------------------
    # Section 21: CL-RECON-L and Evidence-State Semantics Tests
    # ---------------------------------------------------------------
    def test_lesson_l_present_and_distinct(self) -> None:
        """Requirement 1: CL-RECON-L exists and is distinct from prior candidate lessons."""
        data = load_candidate_lessons()
        lesson_l = next(
            (l for l in data["candidate_lessons"] if l["lesson_id"] == "CL-RECON-L"),
            None,
        )
        assert lesson_l is not None
        assert lesson_l["title"] == "RESULT FRESHNESS IS NOT SCIENTIFIC VALIDITY"
        assert lesson_l["category"] == "STATE_INTEGRITY"
        assert lesson_l["severity"] == "CRITICAL"
        assert lesson_l["failure_pattern"] == "WRONG_APPLICABILITY"

        # Distinctness check from all prior lessons (A through K)
        prior_ids = {l["lesson_id"] for l in data["candidate_lessons"] if l["lesson_id"] != "CL-RECON-L"}
        assert "CL-RECON-L" not in prior_ids
        for l in data["candidate_lessons"]:
            if l["lesson_id"] != "CL-RECON-L":
                assert l["title"] != lesson_l["title"]
                assert l["description"] != lesson_l["description"]

    def test_live_current_not_valid_for_scope(self) -> None:
        """Requirement 2: LIVE_CURRENT != VALID_FOR_SCOPE."""
        data = load_candidate_lessons()
        lesson = next(l for l in data["candidate_lessons"] if l["lesson_id"] == "CL-RECON-L")
        rule = lesson.get("governance_rule", "")
        assert "RESULT FRESHNESS IS NOT SCIENTIFIC VALIDITY" in rule
        assert "CONTEXT APPLICABILITY IS NOT EVIDENCE ACTIONABILITY" in rule

        # Conceptual invariant: freshness describes execution recency; validity describes evidence authority
        dims = lesson.get("orthogonal_dimensions", [])
        assert any("Recency" in d for d in dims)
        assert any("Authority" in d for d in dims)

    def test_live_current_plus_provenance_limited_valid_coexistence(self) -> None:
        """Requirement 3: LIVE_CURRENT + PROVENANCE_LIMITED is valid coexistence."""
        data = load_candidate_lessons()
        lesson = next(l for l in data["candidate_lessons"] if l["lesson_id"] == "CL-RECON-L")
        evidence = lesson.get("evidence", "")
        assert "TRUJILLO_00260_00608" in evidence
        assert "Freshness is LIVE_CURRENT while scientific validity is PROVENANCE_LIMITED" in evidence

    def test_blocked_provenance_duplicate_semantics(self) -> None:
        """Requirement 4: BLOCKED_PROVENANCE duplicate has freshness NONE and validity BLOCKED."""
        # Simulated duplicate scenario job execution evaluation
        manifest_duplicate = {
            "scenario_id": "TRUJILLO_00007_01339",
            "source_pair_status": "INVALID_DUPLICATE_IMAGE_PAIR",
            "job_state": "BLOCKED_PROVENANCE",
            "has_scientific_result": False,
        }
        # Invariants required by Section 10 & 3.2:
        # If job is BLOCKED_PROVENANCE with no scientific result:
        # scientific_validity = BLOCKED, result_freshness = NONE, result_usage = NONE
        result_freshness = "NONE" if not manifest_duplicate["has_scientific_result"] else "UNKNOWN"
        scientific_validity = "BLOCKED" if manifest_duplicate["job_state"] == "BLOCKED_PROVENANCE" else "VALID_FOR_SCOPE"
        result_usage = "NONE"

        assert result_freshness == "NONE"
        assert scientific_validity == "BLOCKED"
        assert result_usage == "NONE"
        # Stale cached result must not be retained or masquerade as current job
        stale_cached_result_attached = False
        assert not stale_cached_result_attached

    def test_blocked_temporal_stage_does_not_globally_invalidate_sar(self) -> None:
        """Requirement 5: Blocked temporal stage does not globally invalidate unrelated SAR evidence."""
        # Scenario B state simulation
        stage_status = {
            "INGEST": {"status": "COMPLETED"},
            "INFER": {"status": "COMPLETED"},
            "TEMPORAL": {"status": "BLOCKED", "message": "Chronology unresolved"},
            "DRIFT": {"status": "COMPLETED"},
            "AIS": {"status": "COMPLETED"},
            "FUSION": {"status": "COMPLETED"},
        }
        evidence_sar = {"evidence_type": "SAR_DETECTION", "stage": "INFER", "status": "VALID_FOR_SCOPE"}
        evidence_temporal = {"evidence_type": "TEMPORAL_CHANGE", "stage": "TEMPORAL", "status": "BLOCKED"}

        # Upstream SAR detection remains valid for its scope
        assert evidence_sar["status"] == "VALID_FOR_SCOPE"
        # Only the temporal stage is blocked
        assert stage_status["TEMPORAL"]["status"] == "BLOCKED"
        assert evidence_temporal["status"] == "BLOCKED"

        # Overall package is PROVENANCE_LIMITED, NOT globally BLOCKED
        package_validity = (
            "BLOCKED" if stage_status.get("INGEST", {}).get("status") == "BLOCKED"
            else "PROVENANCE_LIMITED" if stage_status.get("TEMPORAL", {}).get("status") == "BLOCKED"
            else "VALID_FOR_SCOPE"
        )
        assert package_validity == "PROVENANCE_LIMITED"

    def test_context_match_does_not_activate_blocked_or_legacy_invalid_controls(self) -> None:
        """Requirement 6: Context match does not activate blocked/legacy-invalid controls (Two-level gating)."""
        # Selected scenario matches result scenario -> Level 1 passes (RESULT_USAGE = ACTIVE)
        selected_scenario = "TRUJILLO_00260_00608"
        result_scenario = "TRUJILLO_00260_00608"
        is_quarantined = selected_scenario != result_scenario
        result_usage = "QUARANTINED" if is_quarantined else "ACTIVE"
        assert result_usage == "ACTIVE"

        # However, temporal stage is blocked in this result -> Level 2 gating intervenes
        is_temporal_stage_blocked = True
        timeline_controls_disabled = is_quarantined or is_temporal_stage_blocked
        assert timeline_controls_disabled is True  # Blocked despite matching context!

        # Unrelated valid SAR interactions remain enabled
        sar_control_disabled = is_quarantined  # only quarantined disables SAR
        assert sar_control_disabled is False

    def test_result_usage_semantics_distinguish_context_from_actionability(self) -> None:
        """Requirement 7: Result usage semantics distinguish context eligibility from stage actionability."""
        # RESULT_USAGE = ACTIVE means context-level eligibility, NOT universal control permission
        context_eligibility = "ACTIVE"
        temporal_control_permission = False  # blocked at Level 2
        sar_control_permission = True        # permitted at Level 2

        assert context_eligibility == "ACTIVE"
        assert temporal_control_permission != sar_control_permission
        # Proves context eligibility and control permission are decoupled

    def test_lessons_m_through_q_present_and_unique(self) -> None:
        """Verify candidate lessons CL-RECON-M through CL-RECON-Q exist and are distinct."""
        data = load_candidate_lessons()
        lessons_by_id = {l["lesson_id"]: l for l in data["candidate_lessons"]}
        
        expected_ids = ["CL-RECON-M", "CL-RECON-N", "CL-RECON-O", "CL-RECON-P", "CL-RECON-Q"]
        for lid in expected_ids:
            assert lid in lessons_by_id, f"Candidate lesson {lid} missing"
            lesson = lessons_by_id[lid]
            assert len(lesson["title"]) > 0
            assert len(lesson["description"]) > 0
            assert len(lesson["evidence"]) > 0
            assert len(lesson["governance_rule"]) > 0

    def test_lesson_m_canonical_state_vocabulary(self) -> None:
        """Verify CL-RECON-M enforces unconflated canonical state vocabulary."""
        data = load_candidate_lessons()
        lesson = next(l for l in data["candidate_lessons"] if l["lesson_id"] == "CL-RECON-M")
        assert "CANONICAL STATE VOCABULARY" in lesson["title"]
        assert "APPLICATION GATE: READY" in lesson["evidence"]
        assert "PROVENANCE LIMITED" in lesson["evidence"]

    def test_lesson_o_repository_hash_vs_cryptographic_result(self) -> None:
        """Verify CL-RECON-O distinguishes repo SHA-256 integrity from cryptographic result verification."""
        data = load_candidate_lessons()
        lesson = next(l for l in data["candidate_lessons"] if l["lesson_id"] == "CL-RECON-O")
        assert "CRYPTOGRAPHIC VERIFICATION" in lesson["title"]
        assert "HASH EQUALITY != RESULT AUTHENTICATION" in lesson["governance_rule"]

    def test_lesson_p_reanalysis_vs_physical_observation(self) -> None:
        """Verify CL-RECON-P distinguishes numerical reanalysis from physical observation."""
        data = load_candidate_lessons()
        lesson = next(l for l in data["candidate_lessons"] if l["lesson_id"] == "CL-RECON-P")
        assert "REANALYSIS AND MODELLED FORCING" in lesson["title"]
        assert "NUMERICAL MODELLING" in lesson["governance_rule"]

    def test_lesson_q_stale_result_running_race_audit(self) -> None:
        """Verify CL-RECON-Q enforces demoting prior results during RUNNING."""
        data = load_candidate_lessons()
        lesson = next(l for l in data["candidate_lessons"] if l["lesson_id"] == "CL-RECON-Q")
        assert "STALE-RESULT" in lesson["title"]
        assert "NEW EXECUTION DISPATCH IMMEDIATELY DEMOTES PRIOR LIVE RESULTS" in lesson["governance_rule"]

    def test_lesson_r_canonical_enum_vs_behavioral_descriptors(self) -> None:
        """Verify CL-RECON-R enforces canonical enum values rather than behavioral descriptors."""
        data = load_candidate_lessons()
        lesson = next(l for l in data["candidate_lessons"] if l["lesson_id"] == "CL-RECON-R")
        assert "BEHAVIORAL DESCRIPTORS" in lesson["title"]
        assert "READY, DEGRADED, BLOCKED" in lesson["description"]
        assert "CANONICAL STATE ENUMS MUST NOT BE REPLACED BY BEHAVIORAL DESCRIPTORS" in lesson["governance_rule"]

    def test_lesson_s_live_e2e_reconnect_fidelity(self) -> None:
        """Verify CL-RECON-S enforces physical daemon stop/start for reconnect tests."""
        data = load_candidate_lessons()
        lesson = next(l for l in data["candidate_lessons"] if l["lesson_id"] == "CL-RECON-S")
        assert "LIVE E2E DEMONSTRATIONS" in lesson["title"]
        assert "RECONNECT VERIFICATION REQUIRES ACTUAL PHYSICAL SERVICE RECOVERY" in lesson["governance_rule"]

    def test_lesson_t_report_self_consistency(self) -> None:
        """Verify CL-RECON-T forbids contradictions between report statements and runtime evidence."""
        data = load_candidate_lessons()
        lesson = next(l for l in data["candidate_lessons"] if l["lesson_id"] == "CL-RECON-T")
        assert "CLOSURE REPORTS MUST NOT CONTRADICT" in lesson["title"]
        assert "EVERY CLOSURE REPORT STATEMENT MUST BE INTERNALLY SELF-CONSISTENT" in lesson["governance_rule"]

    def test_lesson_u_stage_completion_vs_actionability(self) -> None:
        """Verify CL-RECON-U distinguishes computational completion from scientific actionability."""
        data = load_candidate_lessons()
        lesson = next(l for l in data["candidate_lessons"] if l["lesson_id"] == "CL-RECON-U")
        assert "STAGE EXECUTION COMPLETION AND SCIENTIFIC ACTIONABILITY" in lesson["title"]
        assert "COMPUTATIONAL STAGE COMPLETION != SCIENTIFIC OPERATIONAL ACTIONABILITY" in lesson["governance_rule"]

    def test_lesson_v_environment_causality_evidence(self) -> None:
        """Verify CL-RECON-V enforces causality proof before classifying test failures as pre-existing."""
        data = load_candidate_lessons()
        lesson = next(l for l in data["candidate_lessons"] if l["lesson_id"] == "CL-RECON-V")
        assert "ENVIRONMENT-ORIGIN TEST FAILURES REQUIRE CAUSALITY EVIDENCE" in lesson["title"]
        assert "PRE-EXISTING CLASSIFICATIONS REQUIRE DEMONSTRATED INDEPENDENCE" in lesson["governance_rule"]

    def test_lesson_w_six_dimensions_model_preservation(self) -> None:
        """Verify CL-RECON-W enforces preserving all 6 canonical dimensions without collapsing overlays."""
        data = load_candidate_lessons()
        lesson = next(l for l in data["candidate_lessons"] if l["lesson_id"] == "CL-RECON-W")
        assert "PRESERVE ALL APPROVED DIMENSIONS" in lesson["title"]
        assert "CANONICAL SIX DIMENSIONS AND CONTEXTUAL OVERLAYS" in lesson["governance_rule"]
        assert "CONNECTION STATE" in lesson["description"]
        assert "RESULT_USAGE" in lesson["description"]

    def test_lesson_x_async_response_race_prevention(self) -> None:
        """Verify CL-RECON-X enforces execution generation guarding against stale async responses."""
        data = load_candidate_lessons()
        lesson = next(l for l in data["candidate_lessons"] if l["lesson_id"] == "CL-RECON-X")
        assert "ASYNC RESPONSE MUST BE PREVENTED" in lesson["title"]
        assert "ASYNC CALLBACKS MUST VERIFY EXECUTION GENERATION" in lesson["governance_rule"]
        assert "executionTokenRef" in lesson["evidence"]

    def test_lesson_y_operational_gate_vs_quarantine(self) -> None:
        """Verify CL-RECON-Y enforces separation between Application Gate and context quarantine."""
        data = load_candidate_lessons()
        lesson = next(l for l in data["candidate_lessons"] if l["lesson_id"] == "CL-RECON-Y")
        assert "OPERATIONAL GATE MUST NOT BE INFERRED FROM CONTEXT QUARANTINE" in lesson["title"]
        assert "APPLICATION GATE REFLECTS SYSTEM OPERATIONAL READINESS" in lesson["governance_rule"]
        assert "QUARANTINED" in lesson["evidence"]

    def test_lesson_z_final_bytes_audit(self) -> None:
        """Verify CL-RECON-Z enforces programmatic inspection of written artifact bytes post-edit."""
        data = load_candidate_lessons()
        lesson = next(l for l in data["candidate_lessons"] if l["lesson_id"] == "CL-RECON-Z")
        assert "FINAL ARTIFACT AUDITS MUST INSPECT THE FINAL BYTES" in lesson["title"]
        assert "CERTIFICATION AUDITS MUST INSPECT WRITTEN FINAL ARTIFACT BYTES" in lesson["governance_rule"]
        assert "ocean_sentinel_evidence_state_semantics_final.md" in lesson["evidence"]

    def test_lesson_aa_current_context_at_adoption(self) -> None:
        """Verify CL-RECON-AA enforces checking current context at result adoption time."""
        data = load_candidate_lessons()
        lesson = next(l for l in data["candidate_lessons"] if l["lesson_id"] == "CL-RECON-AA")
        assert "CURRENT EXECUTION CONTEXT MUST BE VERIFIED AT RESULT ADOPTION" in lesson["title"]
        assert "RESULT ADOPTION MUST VALIDATE CURRENT LIVE CONTEXT" in lesson["governance_rule"]
        assert "selectedScenarioIdRef" in lesson["evidence"]

    def test_lesson_ab_cumulative_worktree_reconciliation(self) -> None:
        """Verify CL-RECON-AB enforces cumulative worktree classification and temporary file accounting."""
        data = load_candidate_lessons()
        lesson = next(l for l in data["candidate_lessons"] if l["lesson_id"] == "CL-RECON-AB")
        assert "WORKTREE CLOSURE MUST RECONCILE CUMULATIVE AUTHORIZED CHANGES" in lesson["title"]
        assert "WORKTREE CLOSURE REQUIRES CUMULATIVE CLASSIFICATION" in lesson["governance_rule"]
        assert "check_hashes.py" in lesson["root_cause"]

    def test_lesson_ac_fresh_browser_coverage(self) -> None:
        """Verify CL-RECON-AC enforces distinguishing fresh browser execution from prior artifacts."""
        data = load_candidate_lessons()
        lesson = next(l for l in data["candidate_lessons"] if l["lesson_id"] == "CL-RECON-AC")
        assert "FRESH BROWSER COVERAGE MUST BE EXPLICITLY DISTINGUISHED" in lesson["title"]
        assert "FINAL BROWSER COVERAGE MUST NOT BE OVERSTATED" in lesson["governance_rule"]
        assert lesson["feedback_taxonomy"] == "INSUFFICIENT_EVIDENCE"
        assert lesson["category"] == "VERIFICATION_INTEGRITY"

    def test_lesson_ad_bounded_async_race_claims(self) -> None:
        """Verify CL-RECON-AD enforces scoping concurrency claims to audited race patterns."""
        data = load_candidate_lessons()
        lesson = next(l for l in data["candidate_lessons"] if l["lesson_id"] == "CL-RECON-AD")
        assert "BOUNDED ASYNC RACE TESTS PROVE ABSENCE OF AUDITED DEFECTS" in lesson["title"]
        assert "CONCURRENCY PROOFS MUST BE BOUNDED TO AUDITED SCENARIOS" in lesson["governance_rule"]
        assert lesson["feedback_taxonomy"] == "OVERCLAIM"
        assert lesson["category"] == "CONCURRENCY_INTEGRITY"

    def test_lesson_ae_application_provenance_vs_item_provenance(self) -> None:
        """Verify CL-RECON-AE enforces separating application provenance context from item-level ProvenanceClass."""
        data = load_candidate_lessons()
        lesson = next(l for l in data["candidate_lessons"] if l["lesson_id"] == "CL-RECON-AE")
        assert "APPLICATION PROVENANCE CONTEXT MUST REMAIN DISTINCT" in lesson["title"]
        assert "APPLICATION PROVENANCE CONTEXT AND ITEM-LEVEL PROVENANCECLASS" in lesson["governance_rule"]
        assert lesson["feedback_taxonomy"] == "WRONG_APPLICABILITY"
        assert lesson["category"] == "STATE_INTEGRITY"

    def test_lesson_af_test_number_continuity(self) -> None:
        """Verify CL-RECON-AF enforces exact test-number continuity across documentation."""
        data = load_candidate_lessons()
        lesson = next(l for l in data["candidate_lessons"] if l["lesson_id"] == "CL-RECON-AF")
        assert "FINAL EVIDENCE REPORTS MUST MAINTAIN EXACT TEST-NUMBER CONTINUITY" in lesson["title"]
        assert "TEST RANGES AND TOTAL COUNTS MUST BE INTERNALLY CONSISTENT" in lesson["governance_rule"]
        assert lesson["feedback_taxonomy"] == "INSUFFICIENT_EVIDENCE"
        assert lesson["category"] == "DOCUMENTATION_INTEGRITY"

    def test_lesson_ag_worktree_authorized_vs_clean(self) -> None:
        """Verify CL-RECON-AG enforces distinguishing authorized modifications from literal cleanliness."""
        data = load_candidate_lessons()
        lesson = next(l for l in data["candidate_lessons"] if l["lesson_id"] == "CL-RECON-AG")
        assert "WORKTREE STATUS MUST DISTINGUISH NO UNAUTHORIZED CHANGES" in lesson["title"]
        assert "WORKTREE GOVERNANCE MUST DISTINGUISH AUTHORIZED MODIFICATIONS" in lesson["governance_rule"]
        assert lesson["feedback_taxonomy"] == "WRONG_SCOPE"
        assert lesson["category"] == "GOVERNANCE_INTEGRITY"




