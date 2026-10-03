"""Applicability Engine for evaluating task contexts against governance rules and lessons."""

import re
from typing import Any, Dict, List, Tuple
from ocean_sentinel.governance.models import Rule, ScopeLevel, SeverityLevel, TaskContext


class ApplicabilityEngine:
    """Determines whether a governance rule or lesson is applicable to a specific task context."""

    def evaluate_rule(self, rule: Rule, context: TaskContext) -> Tuple[bool, List[str]]:
        """Evaluates whether a rule applies to the given TaskContext under the Three-Tier Model.
        
        Tier 1: Universal Safety (Non-overridable, Critical Global invariants).
        Tier 2: Trigger / Prohibited Action match on proposed plan, command, or operations.
        Tier 3: Contextual Relevance (experiment, diagnostic, domain, and selective project scope).
        
        Returns:
          applicable: True if the rule applies to this context.
          match_reasons: Human-readable explanations of why the rule applies.
        """
        match_reasons: List[str] = []

        # ----------------------------------------------------------------------
        # TIER 1: Universal Safety (Invariants, non-overridable, critical globals)
        # ----------------------------------------------------------------------
        is_universal_safety = (
            rule.non_overridable
            or (rule.scope == ScopeLevel.GLOBAL and rule.severity == SeverityLevel.CRITICAL)
        )
        
        # Check if the rule has restricting operational or diagnostic predicates
        has_restricting_predicates = any(
            k in rule.applies_to for k in ("diagnostic", "experiment", "task_id", "operation")
        )

        if is_universal_safety and not has_restricting_predicates:
            match_reasons.append(
                f"Tier 1 Universal Safety: Rule {rule.rule_id} is a non-overridable/critical repository invariant."
            )
            return True, match_reasons

        # ----------------------------------------------------------------------
        # TIER 2: Trigger / Prohibited Action Match
        # ----------------------------------------------------------------------
        text_to_scan = []
        if context.proposed_plan:
            text_to_scan.append(context.proposed_plan)
        if context.proposed_command:
            text_to_scan.append(context.proposed_command)
        joined_text = " ".join(text_to_scan).lower()

        # Check prohibited actions in proposed text or explicit operations
        prohibited_action_matched = False
        for action in rule.prohibited_actions:
            act_lower = action.lower()
            if any(act_lower in op.lower() for op in context.operation):
                match_reasons.append(f"Tier 2 Trigger: Target operation matches prohibited action '{action}'.")
                prohibited_action_matched = True
            elif act_lower in joined_text:
                match_reasons.append(f"Tier 2 Trigger: Proposed text/command references prohibited action '{action}'.")
                prohibited_action_matched = True

        # Check trigger patterns in text
        trigger_matched = False
        for pattern in rule.applies_to.get("trigger_patterns", []):
            if re.search(pattern, joined_text, re.IGNORECASE):
                match_reasons.append(f"Tier 2 Trigger: Text matches trigger pattern '{pattern}'.")
                trigger_matched = True

        # Check exact task_id match
        if rule.applies_to.get("task_id") and context.task_id:
            if str(rule.applies_to["task_id"]).lower() == str(context.task_id).lower():
                match_reasons.append(f"Tier 2 Trigger: Exact task ID match '{context.task_id}'.")
                trigger_matched = True

        if prohibited_action_matched or trigger_matched:
            return True, match_reasons

        # ----------------------------------------------------------------------
        # TIER 3: Contextual Relevance
        # ----------------------------------------------------------------------
        if rule.scope == ScopeLevel.EXPERIMENT:
            exp_target = rule.applies_to.get("experiment")
            if not (exp_target and context.experiment and exp_target.lower() == context.experiment.lower()):
                return False, []
            match_reasons.append(f"Scope matches experiment '{context.experiment}'.")

        elif rule.scope == ScopeLevel.DIAGNOSTIC:
            diag_target = rule.applies_to.get("diagnostic")
            if not (diag_target and context.diagnostic and diag_target.lower() == context.diagnostic.lower()):
                return False, []
            match_reasons.append(f"Scope matches diagnostic '{context.diagnostic}'.")

        elif rule.scope == ScopeLevel.TASK:
            task_target = rule.applies_to.get("task_id")
            if not (task_target and context.task_id and str(task_target).lower() == str(context.task_id).lower()):
                return False, []
            match_reasons.append(f"Scope matches task '{context.task_id}'.")

        elif rule.scope == ScopeLevel.DOMAIN:
            domain_target = rule.applies_to.get("domain", [])
            if isinstance(domain_target, str):
                domain_target = [domain_target]
            if not any(d.lower() in [td.lower() for td in context.domain] for d in domain_target):
                return False, []
            match_reasons.append(f"Scope matches domain {domain_target}.")

        elif rule.scope == ScopeLevel.PROJECT:
            # Check project match
            if context.project and rule.applies_to.get("project", "Ocean Sentinel").lower() != context.project.lower():
                return False, []

            # If rule has no specific predicates, check contextual relevance to prevent project-wide noise
            specific_predicates = {
                k: v for k, v in rule.applies_to.items()
                if k not in ("project", "trigger_patterns", "domain")
            }
            if not specific_predicates:
                # Filter out broad project rules for non-diagnostic/non-scientific refactor/docs tasks
                if context.task_type in ("code_refactor", "documentation", "artifact_repair", "repository_governance"):
                    fc_match = (
                        rule.failure_class in context.risk_class
                        or any(rc.lower() in rule.failure_class.lower() for rc in context.risk_class)
                    )
                    domain_match = any(
                        d.lower() in [cd.lower() for cd in context.domain]
                        for d in rule.applies_to.get("domain", [])
                    )
                    if not (fc_match or domain_match):
                        return False, []
                match_reasons.append(f"Contextual relevance for project '{context.project or 'Ocean Sentinel'}'.")

        # Evaluate structured predicates (AND conditions)
        predicates = {
            k: v for k, v in rule.applies_to.items()
            if k not in ("trigger_patterns", "domain", "project")
        }
        for key, val in predicates.items():
            if not self._evaluate_predicate(key, val, context):
                return False, []
            match_reasons.append(f"Structured predicate matched for '{key}': {val}.")

        # Unknown context handling
        if not context.operation and not context.domain and not context.proposed_plan and not context.diagnostic:
            if rule.severity in (SeverityLevel.CRITICAL, SeverityLevel.HIGH):
                match_reasons.append("Unknown context: safety rule applies conservatively.")
                return True, match_reasons
            else:
                return False, []

        return len(match_reasons) > 0, match_reasons

    def _evaluate_predicate(self, key: str, expected_val: Any, context: TaskContext) -> bool:
        """Evaluates an individual structured predicate against the task context."""
        ctx_val = getattr(context, key, None)
        if ctx_val is None:
            # Check dictionary telemetry_state or custom fields
            ctx_val = context.telemetry_state.get(key)
            if ctx_val is None:
                return True  # If context does not specify field, do not block applicability unless required

        if isinstance(expected_val, list):
            if isinstance(ctx_val, list):
                # Overlap check
                return len(set(x.lower() for x in expected_val) & set(y.lower() for y in ctx_val)) > 0
            return str(ctx_val).lower() in [str(x).lower() for x in expected_val]

        if isinstance(ctx_val, list):
            return str(expected_val).lower() in [str(y).lower() for y in ctx_val]

        return str(expected_val).lower() == str(ctx_val).lower()
