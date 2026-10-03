"""Automated Adversarial Replay Test Suite for Lesson Architecture v2.

Replays all 12 concrete failure modes discovered during DIAG-05 to verify that
Lesson Architecture v2 actively detects, blocks, or warns against each failure mode,
while permitting valid, compliant scientific workflows without false blocks.
"""

import pytest
from ocean_sentinel.governance.interface import evaluate_task_preflight
from ocean_sentinel.governance.models import ActionType, SeverityLevel, TaskContext
from ocean_sentinel.governance.provenance import MethodProvenanceValidator


# ==============================================================================
# CASE 1: Raw source support >= threshold but post-validity support = 0
# ==============================================================================
def test_adversarial_case_01_raw_mask_census_failure():
    """Case 1: Evaluating class presence on raw disk mask before validity masking must be blocked."""
    ctx = TaskContext(
        task_id="ADV-CASE-01",
        task_type="diagnostic",
        diagnostic="DIAG-05",
        operation=["sample_eligibility_census"],
        proposed_plan="Evaluate rare class pixel count directly from raw disk mask files."
    )
    res = evaluate_task_preflight(ctx)
    assert not res.passed, "Case 1 failed: Unsafe raw mask census was not blocked!"
    blocker_codes = [b.code for b in res.blockers]
    assert "GOV-RULE-129-POPULATION_CONSTRUCTION" in blocker_codes
    assert any("validity masking" in b.remediation.lower() for b in res.blockers)


def test_adversarial_case_01_compliant_counterexample():
    """Compliant Case 1: Post-validity support census must pass."""
    ctx = TaskContext(
        task_id="ADV-CASE-01-COMPLIANT",
        task_type="diagnostic",
        diagnostic="DIAG-05",
        operation=["sample_eligibility_census"],
        proposed_plan="Evaluate class support strictly after applying canonical SAR validity mask (compute_validity_mask)."
    )
    res = evaluate_task_preflight(ctx)
    assert res.passed, f"Compliant Case 1 was falsely blocked: {[b.message for b in res.blockers]}"


# ==============================================================================
# CASE 2: scipy.stats.wilcoxon called without explicit method
# ==============================================================================
def test_adversarial_case_02_unbound_wilcoxon_method():
    """Case 2: Calling scipy.stats.wilcoxon without explicit method parameter must be blocked."""
    ctx = TaskContext(
        task_id="ADV-CASE-02",
        task_type="diagnostic",
        diagnostic="DIAG-05",
        operation=["wilcoxon"],
        proposed_plan="Execute scipy.stats.wilcoxon(diffs) for paired inference."
    )
    res = evaluate_task_preflight(ctx)
    assert not res.passed, "Case 2 failed: Unbound wilcoxon method was not blocked!"
    blocker_codes = [b.code for b in res.blockers]
    assert "GOV-RULE-130-UNBOUND_METHOD" in blocker_codes

    # Also test via MethodProvenanceValidator
    issues = MethodProvenanceValidator.validate_statistical_payload({
        "test_name": "wilcoxon",
        "p_value": 0.1514,
        "n_paired": 15
    })
    assert any(i.code == "PROV-001-UNBOUND_METHOD" for i in issues)


def test_adversarial_case_02_compliant_counterexample():
    """Compliant Case 2: Wilcoxon with explicit method='asymptotic' must pass."""
    ctx = TaskContext(
        task_id="ADV-CASE-02-COMPLIANT",
        task_type="diagnostic",
        diagnostic="DIAG-05",
        operation=["wilcoxon"],
        statistical_test="wilcoxon_asymptotic",
        proposed_plan="Execute scipy.stats.wilcoxon(diffs, method='asymptotic') with explicit distribution binding."
    )
    res = evaluate_task_preflight(ctx)
    assert res.passed, f"Compliant Case 2 was falsely blocked: {[b.message for b in res.blockers]}"


# ==============================================================================
# CASE 3: Metadata says asymptotic while value corresponds to exact calculation
# ==============================================================================
def test_adversarial_case_03_metadata_result_mismatch():
    """Case 3: Discrepancy between stated asymptotic inference and exact permutation calculation."""
    ctx = TaskContext(
        task_id="ADV-CASE-03",
        task_type="diagnostic",
        diagnostic="DIAG-05",
        operation=["paired_inference"],
        proposed_plan="Report asymptotic p-value while exact permutation method was executed (metadata mismatch)."
    )
    res = evaluate_task_preflight(ctx)
    warning_codes = [w.code for w in res.warnings]
    assert "GOV-RULE-130-METADATA_MISMATCH" in warning_codes


def test_adversarial_case_03_compliant_counterexample():
    """Compliant Case 3: Consistent metadata and method declaration must pass."""
    ctx = TaskContext(
        task_id="ADV-CASE-03-COMPLIANT",
        task_type="diagnostic",
        diagnostic="DIAG-05",
        operation=["paired_inference"],
        proposed_plan="Report exact permutation p-value where exact method was executed (metadata matches method)."
    )
    res = evaluate_task_preflight(ctx)
    assert res.passed, f"Compliant Case 3 was falsely blocked: {[b.message for b in res.blockers]}"


# ==============================================================================
# CASE 4: p > 0.05 described as "no effect"
# ==============================================================================
def test_adversarial_case_04_p_value_overclaim_no_effect():
    """Case 4: Interpreting p > 0.05 as proof of zero effect or stability must be blocked."""
    ctx = TaskContext(
        task_id="ADV-CASE-04",
        task_type="documentation",
        diagnostic="DIAG-05",
        operation=["report_generation"],
        proposed_plan="The non-significant p-value proves no effect and guarantees stability of optimization."
    )
    res = evaluate_task_preflight(ctx)
    assert not res.passed, "Case 4 failed: 'proves no effect' overclaim was not blocked!"
    blocker_codes = [b.code for b in res.blockers]
    assert "GOV-RULE-131-OVERCLAIM_NO_EFFECT" in blocker_codes


def test_adversarial_case_04_compliant_counterexample():
    """Compliant Case 4: Bounded negative reporting must pass."""
    ctx = TaskContext(
        task_id="ADV-CASE-04-COMPLIANT",
        task_type="documentation",
        diagnostic="DIAG-05",
        operation=["report_generation"],
        proposed_plan="The Wilcoxon test did not detect a statistically distinguishable paired difference under the registered design."
    )
    res = evaluate_task_preflight(ctx)
    assert res.passed, f"Compliant Case 4 was falsely blocked: {[b.message for b in res.blockers]}"


# ==============================================================================
# CASE 5: Step-0 directional alignment described as "intrinsic"
# ==============================================================================
def test_adversarial_case_05_intrinsic_orientation_claim():
    """Case 5: Asserting that gradient alignment is an intrinsic structural characteristic must be blocked."""
    ctx = TaskContext(
        task_id="ADV-CASE-05",
        task_type="documentation",
        diagnostic="DIAG-05",
        operation=["report_generation"],
        proposed_plan="Opposing directional gradient alignment is an intrinsic structural characteristic of the architecture."
    )
    res = evaluate_task_preflight(ctx)
    assert not res.passed, "Case 5 failed: 'intrinsic structural characteristic' was not blocked!"
    blocker_codes = [b.code for b in res.blockers]
    assert "GOV-RULE-131-OVERCLAIM_INTRINSIC" in blocker_codes


def test_adversarial_case_05_compliant_counterexample():
    """Compliant Case 5: Bounded empirical observation must pass."""
    ctx = TaskContext(
        task_id="ADV-CASE-05-COMPLIANT",
        task_type="documentation",
        diagnostic="DIAG-05",
        operation=["report_generation"],
        proposed_plan="Negative rare-vs-common directional cosine was observed under both weighting regimes in this Step-0 OPS-02 evaluation."
    )
    res = evaluate_task_preflight(ctx)
    assert res.passed, f"Compliant Case 5 was falsely blocked: {[b.message for b in res.blockers]}"


# ==============================================================================
# CASE 6: Tile-level n treated as inferential n
# ==============================================================================
def test_adversarial_case_06_tile_n_as_inferential_n():
    """Case 6: Treating tile count as inferential degrees of freedom must be blocked."""
    ctx = TaskContext(
        task_id="ADV-CASE-06",
        task_type="diagnostic",
        diagnostic="DIAG-05",
        operation=["paired_inference"],
        proposed_plan="Treating tile-level n as inferential n when parent clusters are clustered."
    )
    res = evaluate_task_preflight(ctx)
    assert not res.passed, "Case 6 failed: Tile-level inferential n was not blocked!"
    blocker_codes = [b.code for b in res.blockers]
    assert "GOV-RULE-116-INFERENCE_UNIT_MISMATCH" in blocker_codes


def test_adversarial_case_06_compliant_counterexample():
    """Compliant Case 6: Cluster-aggregated inferential n must pass."""
    ctx = TaskContext(
        task_id="ADV-CASE-06-COMPLIANT",
        task_type="diagnostic",
        diagnostic="DIAG-05",
        operation=["paired_inference"],
        proposed_plan="Aggregate tile observations to parent acquisition cluster medians before inferential testing."
    )
    res = evaluate_task_preflight(ctx)
    assert res.passed, f"Compliant Case 6 was falsely blocked: {[b.message for b in res.blockers]}"


# ==============================================================================
# CASE 7: B=8 assumed to provide parent-cluster independence
# ==============================================================================
def test_adversarial_case_07_minibatch_independence_assumption():
    """Case 7: Assuming minibatch size creates parent scene independence must trigger warning/block."""
    ctx = TaskContext(
        task_id="ADV-CASE-07",
        task_type="diagnostic",
        diagnostic="DIAG-05",
        operation=["minibatch_profiling"],
        proposed_plan="Assume B=8 provides parent-cluster independence across tiles."
    )
    res = evaluate_task_preflight(ctx)
    all_codes = [b.code for b in res.blockers] + [w.code for w in res.warnings]
    assert "GOV-RULE-124-MINIBATCH_INDEPENDENCE" in all_codes


def test_adversarial_case_07_compliant_counterexample():
    """Compliant Case 7: Explicit clustered minibatch acknowledgment must pass."""
    ctx = TaskContext(
        task_id="ADV-CASE-07-COMPLIANT",
        task_type="diagnostic",
        diagnostic="DIAG-05",
        operation=["minibatch_profiling"],
        proposed_plan="Evaluate minibatch gradients while acknowledging parent acquisition clustering."
    )
    res = evaluate_task_preflight(ctx)
    assert res.passed, f"Compliant Case 7 was falsely blocked: {[b.message for b in res.blockers]}"


# ==============================================================================
# CASE 8: subset-normalized gradient substituted for full-batch denominator
# ==============================================================================
def test_adversarial_case_08_denominator_estimand_drift():
    """Case 8: Substituting subset-normalized gradient for full-batch denominator must be blocked."""
    ctx = TaskContext(
        task_id="ADV-CASE-08",
        task_type="diagnostic",
        diagnostic="DIAG-05",
        operation=["backward_pass"],
        proposed_plan="Substitute subset-normalized gradient for full-batch denominator."
    )
    res = evaluate_task_preflight(ctx)
    assert not res.passed, "Case 8 failed: Denominator drift was not blocked!"
    blocker_codes = [b.code for b in res.blockers]
    assert "GOV-RULE-127-DENOMINATOR_DRIFT" in blocker_codes


def test_adversarial_case_08_compliant_counterexample():
    """Compliant Case 8: Contractual denominator normalization must pass."""
    ctx = TaskContext(
        task_id="ADV-CASE-08-COMPLIANT",
        task_type="diagnostic",
        diagnostic="DIAG-05",
        operation=["backward_pass"],
        proposed_plan="Normalize masked loss by total valid pixels or registered weight sum per registered contract."
    )
    res = evaluate_task_preflight(ctx)
    assert res.passed, f"Compliant Case 8 was falsely blocked: {[b.message for b in res.blockers]}"


# ==============================================================================
# CASE 9: model.train() used during B=1 static gradient diagnostic
# ==============================================================================
def test_adversarial_case_09_model_train_during_diagnostic():
    """Case 9: Calling model.train() during diagnostic profiling must be blocked."""
    ctx = TaskContext(
        task_id="ADV-CASE-09",
        task_type="diagnostic",
        diagnostic="DIAG-05",
        proposed_command="python scripts/execute_exp07_diag05_tier1.py --model.train()"
    )
    res = evaluate_task_preflight(ctx)
    assert not res.passed, "Case 9 failed: model.train() invocation was not blocked!"
    blocker_codes = [b.code for b in res.blockers]
    assert "BLOCK-006-UNAUTHORIZED_TRAINING" in blocker_codes


def test_adversarial_case_09_compliant_counterexample():
    """Compliant Case 9: Model.eval() static evaluation must pass."""
    ctx = TaskContext(
        task_id="ADV-CASE-09-COMPLIANT",
        task_type="diagnostic",
        diagnostic="DIAG-05",
        proposed_command="python scripts/execute_exp07_diag05_tier1.py --model.eval()"
    )
    res = evaluate_task_preflight(ctx)
    assert res.passed, f"Compliant Case 9 was falsely blocked: {[b.message for b in res.blockers]}"


# ==============================================================================
# CASE 10: negative cosine described as "destructive interference"
# ==============================================================================
def test_adversarial_case_10_unregistered_destructive_interference():
    """Case 10: Using phrase 'destructive interference' without registered criterion must warn."""
    ctx = TaskContext(
        task_id="ADV-CASE-10",
        task_type="documentation",
        diagnostic="DIAG-05",
        operation=["report_generation"],
        proposed_plan="The opposing vectors cause destructive interference during gradient descent."
    )
    res = evaluate_task_preflight(ctx)
    warning_codes = [w.code for w in res.warnings]
    assert "GOV-RULE-131-UNREGISTERED_INTERFERENCE" in warning_codes


def test_adversarial_case_10_compliant_counterexample():
    """Compliant Case 10: Bounded directional cosine reporting without destructive interference must pass."""
    ctx = TaskContext(
        task_id="ADV-CASE-10-COMPLIANT",
        task_type="documentation",
        diagnostic="DIAG-05",
        operation=["report_generation"],
        proposed_plan="Negative rare-vs-common directional cosine was observed under Step-0 OPS-02 evaluation without claiming destructive interference."
    )
    res = evaluate_task_preflight(ctx)
    assert res.passed, f"Compliant Case 10 was falsely blocked: {[b.message for b in res.blockers]}"


# ==============================================================================
# CASE 11: analysis-only task leaves execution_authorized=true
# ==============================================================================
def test_adversarial_case_11_telemetry_authorization_ambiguity():
    """Case 11: Analysis-only task claiming execution_authorized=true in telemetry must be blocked."""
    ctx = TaskContext(
        task_id="ADV-CASE-11",
        task_type="diagnostic",
        diagnostic="DIAG-05",
        telemetry_state={
            "analysis_authorized": True,
            "execution_authorized": True
        }
    )
    res = evaluate_task_preflight(ctx)
    assert not res.passed, "Case 11 failed: Telemetry authorization ambiguity was not blocked!"
    blocker_codes = [b.code for b in res.blockers]
    assert "BLOCK-012-TELEMETRY_AUTHORIZATION_AMBIGUITY" in blocker_codes


def test_adversarial_case_11_compliant_counterexample():
    """Compliant Case 11: Fail-closed analysis telemetry with execution_authorized=false must pass."""
    ctx = TaskContext(
        task_id="ADV-CASE-11-COMPLIANT",
        task_type="diagnostic",
        diagnostic="DIAG-05",
        telemetry_state={
            "analysis_only": True,
            "execution_authorized": False
        }
    )
    res = evaluate_task_preflight(ctx)
    assert res.passed, f"Compliant Case 11 was falsely blocked: {[b.message for b in res.blockers]}"


# ==============================================================================
# CASE 12: report says "VALID" while population construction is defective
# ==============================================================================
def test_adversarial_case_12_ambiguous_valid_status():
    """Case 12: Declaring status 'VALID' when population construction was defective must be blocked."""
    ctx = TaskContext(
        task_id="ADV-CASE-12",
        task_type="documentation",
        diagnostic="DIAG-05",
        operation=["report_generation"],
        proposed_plan="Overall status: VALID despite defective population and zero valid rare pixels."
    )
    res = evaluate_task_preflight(ctx)
    assert not res.passed, "Case 12 failed: Ambiguous 'VALID' status was not blocked!"
    blocker_codes = [b.code for b in res.blockers]
    assert "GOV-RULE-100-AMBIGUOUS_VALID_STATUS" in blocker_codes


def test_adversarial_case_12_compliant_counterexample():
    """Compliant Case 12: Disambiguated population validity status must pass."""
    ctx = TaskContext(
        task_id="ADV-CASE-12-COMPLIANT",
        task_type="documentation",
        diagnostic="DIAG-05",
        operation=["report_generation"],
        proposed_plan="Execution integrity is COMPLETE; scientific population validity is DEFECTIVE due to zero post-validity rare pixels."
    )
    res = evaluate_task_preflight(ctx)
    assert res.passed, f"Compliant Case 12 was falsely blocked: {[b.message for b in res.blockers]}"


# ==============================================================================
# CASE 13: Statistical method conflation (SciPy exact Wilcoxon vs Permutation)
# ==============================================================================
def test_adversarial_case_13_statistical_method_conflation():
    """Case 13: Conflating SciPy method='exact' with permutation test must trigger registered WARN action."""
    ctx = TaskContext(
        task_id="ADV-CASE-13",
        task_type="documentation",
        diagnostic="DIAG-05",
        operation=["report_generation"],
        proposed_plan="Report scipy wilcoxon exact permutation test results for paired gradient differences."
    )
    res = evaluate_task_preflight(ctx)
    warning_codes = [w.code for w in res.warnings]
    assert "GOV-RULE-132-STATISTICAL_CONFLATION" in warning_codes

    # Also test via MethodProvenanceValidator
    prov_issues = MethodProvenanceValidator.validate_statistical_payload({
        "test_name": "wilcoxon",
        "library": "scipy",
        "version": "1.15.3",
        "method": "exact",
        "executed_algorithm": "permutation test"
    })
    assert any(i.code == "PROV-007-STATISTICAL_CONFLATION" for i in prov_issues)


def test_adversarial_case_13_compliant_counterexample():
    """Compliant Case 13: Accurate discrete signed-rank distribution semantics must pass."""
    ctx = TaskContext(
        task_id="ADV-CASE-13-COMPLIANT",
        task_type="documentation",
        diagnostic="DIAG-05",
        operation=["report_generation"],
        proposed_plan="Report paired Wilcoxon signed-rank test evaluated against exact discrete null distribution (method='exact')."
    )
    res = evaluate_task_preflight(ctx)
    assert res.passed, f"Compliant Case 13 was falsely blocked: {[b.message for b in res.blockers]}"


# ==============================================================================
# PERMANENT ADVERSARIAL REGRESSION CORPUS (13 UNSAFE + 13 COMPLIANT CONTROLS)
# ==============================================================================
def test_permanent_governance_adversarial_corpus_integrity():
    """Validates that all 26 cases in GOVERNANCE_REGRESSION_CORPUS produce their exact registered enforcement behavior,
    and asserts cryptographic SHA256 tamper-proofing against unauthorized modification."""
    import hashlib
    import json
    from pathlib import Path
    corpus_path = Path(__file__).resolve().parent / "data" / "governance_adversarial_corpus.json"
    assert corpus_path.exists(), f"Corpus file missing at {corpus_path}"
    
    with open(corpus_path, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    scenarios = corpus.get("scenarios", [])
    assert len(scenarios) == 26, f"Expected exactly 26 corpus scenarios (13 unsafe + 13 compliant), found {len(scenarios)}"

    # Cryptographic SHA256 tamper-proofing of canonical scenario definitions
    serialized = json.dumps(scenarios, sort_keys=True)
    actual_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    CANONICAL_CORPUS_HASH = "c7b0d07883dfa42d187eaf21ee90e28466307512d7d8e0efb75f1652a409fa8b"
    assert actual_hash == CANONICAL_CORPUS_HASH, f"Corpus tampering detected! Expected {CANONICAL_CORPUS_HASH}, got {actual_hash}"

    # Structural invariants: verify exactly 13 unsafe cases and 13 compliant controls
    unsafe_ids = {f"ADV-CASE-{i:02d}" for i in range(1, 14)}
    compliant_ids = {f"ADV-CASE-{i:02d}-COMPLIANT" for i in range(1, 14)}
    present_ids = {s["case_id"] for s in scenarios}
    assert unsafe_ids.issubset(present_ids), f"Missing unsafe cases: {unsafe_ids - present_ids}"
    assert compliant_ids.issubset(present_ids), f"Missing compliant controls: {compliant_ids - present_ids}"

    # Action contract invariants
    for s in scenarios:
        cid = s["case_id"]
        exp_act = s["expected_action"]
        if cid in ("ADV-CASE-03", "ADV-CASE-07", "ADV-CASE-10", "ADV-CASE-13"):
            assert exp_act == "WARN", f"{cid} must have registered action WARN, got {exp_act}"
        elif cid.endswith("-COMPLIANT"):
            assert exp_act == "PASS", f"{cid} must have registered action PASS, got {exp_act}"
        else:
            assert exp_act == "BLOCK", f"{cid} must have registered action BLOCK, got {exp_act}"

    for s in scenarios:
        cid = s["case_id"]
        expected_act = s["expected_action"]
        expected_cd = s["expected_code"]
        ctx_data = s["input_context"]
        
        ctx = TaskContext(
            task_id=ctx_data.get("task_id", cid),
            task_type=ctx_data.get("task_type", "diagnostic"),
            diagnostic=ctx_data.get("diagnostic"),
            operation=ctx_data.get("operation", []),
            proposed_plan=ctx_data.get("proposed_plan"),
            proposed_command=ctx_data.get("proposed_command"),
            telemetry_state=ctx_data.get("telemetry_state", {}),
            statistical_test=ctx_data.get("statistical_test")
        )
        res = evaluate_task_preflight(ctx)
        
        if expected_act == "BLOCK":
            assert not res.passed, f"Corpus scenario {cid} expected BLOCK but passed!"
            blocker_codes = [b.code for b in res.blockers]
            if expected_cd:
                assert expected_cd in blocker_codes, f"Corpus scenario {cid} expected blocker code {expected_cd}, got {blocker_codes}"
        elif expected_act == "WARN":
            warning_codes = [w.code for w in res.warnings]
            if expected_cd:
                assert expected_cd in warning_codes, f"Corpus scenario {cid} expected warning code {expected_cd}, got {warning_codes}"
        elif expected_act == "PASS":
            assert res.passed, f"Corpus compliant scenario {cid} was falsely blocked: {[b.message for b in res.blockers]}"

