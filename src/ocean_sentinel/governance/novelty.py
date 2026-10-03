"""Novelty Detection Engine for identifying unmodeled risks and uncovered operational surfaces."""

from typing import Dict, List
from ocean_sentinel.governance.models import (
    Assumption,
    AssumptionState,
    FailureClass,
    LearningState,
    NoveltyFlag,
    Rule,
    TaskContext,
)


class NoveltyDetector:
    """Detects when an incoming task context contains novel operations, unverified assumptions, or unprotected rules."""

    def __init__(
        self,
        failure_classes: Dict[str, FailureClass],
        rules: Dict[str, Rule],
        assumptions: Dict[str, Assumption],
    ):
        self.failure_classes = failure_classes
        self.rules = rules
        self.assumptions = assumptions

    def evaluate_task_novelty(
        self, context: TaskContext, applicable_rules: List[Rule]
    ) -> List[Dict[str, str]]:
        """Evaluates novelty of the task and its declared assumptions and operations."""
        findings = []

        # 1. Check for unrecognized operations
        known_operations = set()
        for r in self.rules.values():
            for op in r.applies_to.get("operation", []):
                known_operations.add(op.lower())
            for pact in r.prohibited_actions:
                known_operations.add(pact.lower())

        for op in context.operation:
            if op.lower() not in known_operations and not any(op.lower() in kop for kop in known_operations):
                findings.append({
                    "flag": NoveltyFlag.NOVEL.value,
                    "target": f"operation:{op}",
                    "description": f"Operation '{op}' has no matching governance rule or explicit prohibited action.",
                    "guideline": "Document operational invariants and establish a new governance check if this operation introduces risk."
                })

        # 2. Check for active unverified assumptions
        for asmp_id in context.active_assumptions:
            if asmp_id in self.assumptions:
                asmp = self.assumptions[asmp_id]
                if asmp.status == AssumptionState.CONTRADICTED:
                    findings.append({
                        "flag": "BLOCK_CONTRADICTED_ASSUMPTION",
                        "target": f"assumption:{asmp_id}",
                        "description": f"Assumption {asmp_id} ('{asmp.statement}') has been empirically CONTRADICTED.",
                        "guideline": "Relying on a contradicted assumption is strictly prohibited. Correct workflow to reflect empirical truth."
                    })
                elif asmp.status == AssumptionState.UNVERIFIED:
                    findings.append({
                        "flag": NoveltyFlag.POTENTIALLY_NOVEL.value,
                        "target": f"assumption:{asmp_id}",
                        "description": f"Assumption {asmp_id} ('{asmp.statement}') is UNVERIFIED in the governance registry.",
                        "guideline": "Preflight requires verifying this assumption before executing substantive operations."
                    })
            else:
                findings.append({
                    "flag": NoveltyFlag.NOVEL.value,
                    "target": f"assumption:{asmp_id}",
                    "description": f"Declared assumption '{asmp_id}' is not registered in the institutional assumption registry.",
                    "guideline": "Register new assumption in governance registry before relying upon it in execution."
                })

        # 3. Check for applicable rules that lack automated tests (KNOWN_BUT_UNPROTECTED)
        for r in applicable_rules:
            if r.status == LearningState.RECORDED and not r.regression_test_ids:
                findings.append({
                    "flag": NoveltyFlag.KNOWN_BUT_UNPROTECTED.value,
                    "target": f"rule:{r.rule_id}",
                    "description": f"Rule {r.rule_id} ('{r.title}') is in RECORDED state and lacks an automated regression test.",
                    "guideline": "Implement an automated guardrail test to promote this rule to REGRESSION_PROTECTED."
                })

        # 4. If no novel or unprotected items found, flag as KNOWN
        if not findings and applicable_rules:
            findings.append({
                "flag": NoveltyFlag.KNOWN.value,
                "target": f"task:{context.task_id or 'current'}",
                "description": "All identified operational risks and failure classes are covered by regression-protected governance rules.",
                "guideline": "Proceed under verified governance envelope."
            })

        return findings
