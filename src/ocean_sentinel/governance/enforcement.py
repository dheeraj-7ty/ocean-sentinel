"""Governance Enforcement Engine: Evaluates proposed task actions, plan texts, code, and telemetry."""

import re
from typing import Any, Dict, List, Optional, Tuple
from ocean_sentinel.governance.models import (
    ActionType,
    LearningState,
    PreflightIssueV2,
    Rule,
    SeverityLevel,
    TaskContext,
)


class EnforcementEngine:
    """Evaluates task context and proposed actions against active governance rules."""

    def evaluate_task(
        self, context: TaskContext, active_rules: List[Rule]
    ) -> Tuple[List[PreflightIssueV2], List[PreflightIssueV2], List[PreflightIssueV2]]:
        """Evaluates context against active rules.
        
        Returns:
          blockers: Issues that halt task execution.
          warnings: Advisory issues requiring awareness.
          recommendations: Helpful suggestions for compliance.
        """
        blockers: List[PreflightIssueV2] = []
        warnings: List[PreflightIssueV2] = []
        recommendations: List[PreflightIssueV2] = []

        text_to_scan = []
        if context.proposed_plan:
            text_to_scan.append(context.proposed_plan)
        if context.proposed_command:
            text_to_scan.append(context.proposed_command)
        if context.operation:
            text_to_scan.extend(context.operation)
        if getattr(context, "target_path", None):
            text_to_scan.append(context.target_path)
        if getattr(context, "dataset", None):
            text_to_scan.append(context.dataset)
        if context.partition:
            text_to_scan.append(context.partition)
        joined_text = " ".join(text_to_scan)
        lower_text = joined_text.lower()

        # 1. Evaluate Rule-specific prohibitions and checks
        for rule in active_rules:
            # Check prohibited actions
            for pact in rule.prohibited_actions:
                pact_lower = pact.lower()
                if pact_lower in lower_text or any(pact_lower in op.lower() for op in context.operation):
                    issue = PreflightIssueV2(
                        severity=rule.severity,
                        code=f"ENF-{rule.rule_id}",
                        rule_id=rule.rule_id,
                        message=f"Action '{pact}' violates Rule {rule.rule_id}: {rule.statement}",
                        remediation=rule.statement,
                        test_ids=rule.regression_test_ids
                    )
                    
                    # Rule Quarantine & Evidence Strength Governance
                    is_quarantined = rule.status in (LearningState.PROPOSED, LearningState.REVIEW_REQUIRED)
                    lacks_evidence = not getattr(rule.evidence_strength, "allows_hard_block", True)

                    if rule.action == ActionType.BLOCK:
                        if is_quarantined:
                            issue.code = f"WARN-QUARANTINED-{rule.rule_id}"
                            issue.message = f"Rule {rule.rule_id} is quarantined ({rule.status.value}) and cannot emit hard BLOCK: {issue.message}"
                            warnings.append(issue)
                        elif lacks_evidence:
                            issue.code = f"WARN-WEAK-EVIDENCE-{rule.rule_id}"
                            issue.message = f"Rule {rule.rule_id} has weak evidence ({rule.evidence_strength.value}) and cannot emit hard BLOCK: {issue.message}"
                            warnings.append(issue)
                        else:
                            blockers.append(issue)
                    elif rule.action == ActionType.WARN:
                        warnings.append(issue)
                    else:
                        recommendations.append(issue)

        # 2. Specific Hardened Guardrail Checks (Adversarial Corpus & Invariants)

        # A. HOLDOUT Access Check (BLOCK-001)
        if "holdout" in lower_text or (context.partition and "holdout" in context.partition.lower()):
            blockers.append(PreflightIssueV2(
                severity=SeverityLevel.CRITICAL,
                code="BLOCK-001-HOLDOUT",
                rule_id="BLOCK-001-HOLDOUT",
                message="HOLDOUT partition access is strictly forbidden.",
                remediation="Remove all HOLDOUT references; evaluation is strictly firewalled."
            ))

        # B. Part III Access Check (BLOCK-002)
        if "part_iii" in lower_text or "part iii" in lower_text or (context.partition and "part_iii" in context.partition.lower()):
            blockers.append(PreflightIssueV2(
                severity=SeverityLevel.CRITICAL,
                code="BLOCK-002-PART_III",
                rule_id="BLOCK-002-PART_III",
                message="Part III evaluation data and prediction payloads are strictly firewalled.",
                remediation="Remove all Part III references; external benchmark is quarantined."
            ))

        # C. Destructive Git Check (BLOCK-007)
        destructive_patterns = [
            "git reset --hard", "git clean", "git checkout -f", "git push --force", "git push -f"
        ]
        for dp in destructive_patterns:
            if dp in lower_text:
                blockers.append(PreflightIssueV2(
                    severity=SeverityLevel.CRITICAL,
                    code="BLOCK-007-DESTRUCTIVE_GIT",
                    rule_id="BLOCK-007-DESTRUCTIVE_GIT",
                    message=f"Command contains destructive git operation '{dp}'.",
                    remediation="Zero destructive git operations permitted. Working-tree changes must be preserved."
                ))

        # D. Diagnostic Unauthorized Training Check (BLOCK-006 / Case 9)
        if context.task_type == "diagnostic":
            training_keywords = ["train(", "model.train()", "--epochs", "optimizer.step", "scheduler.step"]
            for kw in training_keywords:
                if kw in lower_text:
                    blockers.append(PreflightIssueV2(
                        severity=SeverityLevel.CRITICAL,
                        code="BLOCK-006-UNAUTHORIZED_TRAINING",
                        rule_id="GOV-RULE-128",
                        message=f"Diagnostic plan/command invokes training mechanism '{kw}'.",
                        remediation="Diagnostics permit zero training steps and must execute in explicit model.eval() mode."
                    ))

        # E. Post-Validity Support Census Check (Case 1 / GOV-RULE-129)
        if "sample_eligibility_census" in context.operation or "population_census" in context.operation:
            if ("raw mask" in lower_text or "raw disk mask" in lower_text) and "validity mask" not in lower_text:
                blockers.append(PreflightIssueV2(
                    severity=SeverityLevel.CRITICAL,
                    code="GOV-RULE-129-POPULATION_CONSTRUCTION",
                    rule_id="GOV-RULE-129",
                    message="Evaluating sample eligibility from raw disk mask without post-validity masking is prohibited.",
                    remediation="Evaluate class support strictly after applying sensor validity masking (compute_validity_mask)."
                ))

        # F. Statistical Method Binding Check (Case 2 / GOV-RULE-130)
        if "scipy.stats.wilcoxon" in lower_text or "wilcoxon" in [t.lower() for t in context.operation]:
            if "method=" not in lower_text and not context.statistical_test:
                blockers.append(PreflightIssueV2(
                    severity=SeverityLevel.CRITICAL,
                    code="GOV-RULE-130-UNBOUND_METHOD",
                    rule_id="GOV-RULE-130",
                    message="Calling scipy.stats.wilcoxon without explicit method parameter is prohibited.",
                    remediation="Explicitly pass method='asymptotic' or method='exact' in code."
                ))

        # G. Metadata vs Result Mismatch Check (Case 3 / GOV-RULE-130)
        if "asymptotic" in lower_text and "exact permutation" in lower_text and "mismatch" in lower_text:
            warnings.append(PreflightIssueV2(
                severity=SeverityLevel.HIGH,
                code="GOV-RULE-130-METADATA_MISMATCH",
                rule_id="GOV-RULE-130",
                message="Detected potential discrepancy between stated asymptotic inference and exact calculation.",
                remediation="Ensure artifact metadata declares the exact distribution used in computation."
            ))

        # H. Bounded Negative Interpretation Check (Case 4 / GOV-RULE-131)
        zero_effect_patterns = [
            r"\bproves?\s+(no|zero)\s+effect\b",
            r"\bthere\s+is\s+no\s+effect\b",
            r"\bno\s+conflict\b",
            r"\beliminated\s+interference\b",
            r"\bguarantees?\s+(stability|convergence)\b"
        ]
        for pat in zero_effect_patterns:
            if re.search(pat, lower_text):
                blockers.append(PreflightIssueV2(
                    severity=SeverityLevel.CRITICAL,
                    code="GOV-RULE-131-OVERCLAIM_NO_EFFECT",
                    rule_id="GOV-RULE-131",
                    message=f"Text contains unsupported claim of zero effect or guaranteed stability: '{pat}'.",
                    remediation="Report non-significant findings as 'did not detect a statistically distinguishable difference'."
                ))

        # I. Intrinsic Alignment Claims (Case 5 / GOV-RULE-131)
        intrinsic_patterns = [
            r"\bintrinsic\s+structural\s+characteristic\b",
            r"\barchitectural\s+invariant\s+across\s+domains\b"
        ]
        for pat in intrinsic_patterns:
            if re.search(pat, lower_text):
                blockers.append(PreflightIssueV2(
                    severity=SeverityLevel.CRITICAL,
                    code="GOV-RULE-131-OVERCLAIM_INTRINSIC",
                    rule_id="GOV-RULE-131",
                    message=f"Text claims orientation is an intrinsic structural property: '{pat}'.",
                    remediation="State finding as conditional Step-0 empirical observation; avoid generalizing to architecture."
                ))

        # J. Observation Unit vs Inference Unit Mismatch (Case 6 / GOV-RULE-116)
        if ("tile-level n" in lower_text or "n_tiles as degrees of freedom" in lower_text) and "cluster" in lower_text:
            blockers.append(PreflightIssueV2(
                severity=SeverityLevel.CRITICAL,
                code="GOV-RULE-116-INFERENCE_UNIT_MISMATCH",
                rule_id="GOV-RULE-116",
                message="Treating physical tile count as inferential N when parent clusters are clustered is prohibited.",
                remediation="Aggregate tile observations to parent acquisition cluster medians before inference."
            ))

        # K. Minibatch Independence Misattribution (Case 7 / GOV-RULE-124)
        if "b=8 provides parent-cluster independence" in lower_text or "minibatch provides independent scenes" in lower_text:
            warnings.append(PreflightIssueV2(
                severity=SeverityLevel.HIGH,
                code="GOV-RULE-124-MINIBATCH_INDEPENDENCE",
                rule_id="GOV-RULE-124",
                message="Minibatch size does not guarantee independent scene representation in clustered OPS-02.",
                remediation="Acknowledge parent cluster multi-tile nesting within minibatches."
            ))

        # L. Denominator Estimand Drift (Case 8 / GOV-RULE-127)
        if "subset-normalized gradient" in lower_text and "full-batch denominator" in lower_text:
            blockers.append(PreflightIssueV2(
                severity=SeverityLevel.CRITICAL,
                code="GOV-RULE-127-DENOMINATOR_DRIFT",
                rule_id="GOV-RULE-127",
                message="Substituting subset-normalized gradient for registered full-batch denominator is prohibited.",
                remediation="Preserve literal contractual gradient denominator."
            ))

        # M. Destructive Interference Language (Case 10 / GOV-RULE-131)
        if "destructive interference" in lower_text and "registered threshold" not in lower_text:
            warnings.append(PreflightIssueV2(
                severity=SeverityLevel.HIGH,
                code="GOV-RULE-131-UNREGISTERED_INTERFERENCE",
                rule_id="GOV-RULE-131",
                message="Using phrase 'destructive interference' without a registered quantitative threshold.",
                remediation="Describe geometric angle as 'negative directional cosine' rather than functional interference."
            ))

        # N. Telemetry Authorization Inconsistency (Case 11 / BLOCK-012)
        if context.telemetry_state:
            tel = context.telemetry_state
            if tel.get("analysis_authorized") is True and tel.get("execution_authorized") is True:
                if context.task_type in ("diagnostic", "documentation", "artifact_repair"):
                    blockers.append(PreflightIssueV2(
                        severity=SeverityLevel.CRITICAL,
                        code="BLOCK-012-TELEMETRY_AUTHORIZATION_AMBIGUITY",
                        rule_id="BLOCK-012-UNVERIFIED_TELEMETRY",
                        message="Analysis-only task cannot have execution_authorized=true in telemetry.",
                        remediation="Set execution_authorized=false and scientific_execution=false."
                    ))

        # O. Ambiguous 'VALID' Status on Defective Population (Case 12 / GOV-RULE-100)
        if "status: valid" in lower_text and ("defective population" in lower_text or "zero valid rare" in lower_text):
            blockers.append(PreflightIssueV2(
                severity=SeverityLevel.CRITICAL,
                code="GOV-RULE-100-AMBIGUOUS_VALID_STATUS",
                rule_id="GOV-RULE-100",
                message="Declaring overall status 'VALID' while population construction is defective is prohibited.",
                remediation="Separate execution artifact integrity from scientific population validity."
            ))

        # P. Causal Overclaims & Paraphrases (BLOCK-004 / FP-016)
        causal_terms = [
            "radiometric bottleneck", "information bottleneck", "root cause",
            "proves model failure", "cannot learn", "causes low miou", "explains low miou"
        ]
        for term in causal_terms:
            if term in lower_text:
                blockers.append(PreflightIssueV2(
                    severity=SeverityLevel.CRITICAL,
                    code="BLOCK-004-CAUSAL_OVERCLAIM",
                    rule_id="BLOCK-004-CAUSAL_OVERCLAIM",
                    message=f"Plan contains forbidden causal claim: '{term}'.",
                    remediation="Diagnostics are observational. Use 'observed', 'associated with', or 'HYPOTHESIZED'."
                ))

        # Q. Statistical Method Conflation (Case 13 / GOV-RULE-132)
        if ("wilcoxon" in lower_text and "exact permutation" in lower_text) or "conflating exact signed-rank" in lower_text:
            warnings.append(PreflightIssueV2(
                severity=SeverityLevel.HIGH,
                code="GOV-RULE-132-STATISTICAL_CONFLATION",
                rule_id="GOV-RULE-132",
                message="Informal statistical method conflation: SciPy wilcoxon method='exact' computes the exact discrete null distribution of the signed-rank statistic, not a generic permutation/randomization test.",
                remediation="Accurately distinguish exact signed-rank distribution from permutation testing or asymptotic approximation."
            ))

        return blockers, warnings, recommendations
