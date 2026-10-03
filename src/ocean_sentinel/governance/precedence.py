"""Precedence and Conflict Resolution Engine for Ocean Sentinel Governance Rules."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple
from ocean_sentinel.governance.models import ActionType, PreflightIssueV2, Rule, ScopeLevel, SeverityLevel


@dataclass
class ConflictReport:
    """A detected conflict between two or more governance rules."""
    conflict_id: str
    rule_ids: List[str]
    description: str
    resolution_status: str  # "RESOLVED_BY_SEVERITY", "RESOLVED_BY_SUPERSESSION", "UNRESOLVED_CONFLICT"
    winning_rule_id: Optional[str] = None
    reason: str = ""


class PrecedenceEngine:
    """Evaluates rule precedence, handles supersession, and detects conflicting directives."""

    @staticmethod
    def calculate_effective_priority(rule: Rule) -> int:
        """Computes deterministic priority score. Higher score = higher enforcement priority.
        
        Formula:
          Base = severity.rank * 100
          If non_overridable: +10000
          Specificity bonus = (60 - scope.rank)  [More specific gets bonus, UNLESS non_overridable]
          Custom weight = rule.precedence_weight
        """
        base = rule.severity.rank * 100
        if rule.non_overridable:
            base += 100000
        else:
            # Specificity preference only within same severity tier
            specificity_bonus = 60 - rule.scope.rank
            base += specificity_bonus
        return base + rule.precedence_weight

    def resolve_rules(self, rules: List[Rule]) -> Tuple[List[Rule], List[ConflictReport], List[PreflightIssueV2]]:
        """Resolves a collection of candidate applicable rules.
        
        Returns:
          active_rules: Rules sorted by descending priority, with superseded rules removed.
          conflicts: Audit trail of detected conflicts and their resolutions.
          blocking_issues: Any unresolvable conflicts that trigger critical system blocks.
        """
        conflicts: List[ConflictReport] = []
        blocking_issues: List[PreflightIssueV2] = []

        # 1. Process explicit supersession
        superseded_ids: Set[str] = set()
        for r in rules:
            if r.superseded_by:
                superseded_ids.add(r.rule_id)
            for s_id in r.supersedes:
                superseded_ids.add(s_id)

        active_candidates = [r for r in rules if r.rule_id not in superseded_ids]

        for r in rules:
            for s_id in r.supersedes:
                conflicts.append(ConflictReport(
                    conflict_id=f"CONF-SUPERSEDE-{r.rule_id}-{s_id}",
                    rule_ids=[r.rule_id, s_id],
                    description=f"Rule {r.rule_id} explicitly supersedes {s_id}.",
                    resolution_status="RESOLVED_BY_SUPERSESSION",
                    winning_rule_id=r.rule_id,
                    reason=f"Explicit supersession declared in {r.rule_id} metadata."
                ))

        # 2. Check for semantic / directive conflicts among active rules
        # Group rules by target operation or prohibited actions
        action_map: Dict[str, List[Rule]] = {}
        for r in active_candidates:
            for act in r.prohibited_actions:
                action_map.setdefault(act, []).append(r)

        # Look for identical action with conflicting directives or unresolvable ties
        for act, mapped_rules in action_map.items():
            if len(mapped_rules) > 1:
                # Compare pairs
                for i in range(len(mapped_rules)):
                    for j in range(i + 1, len(mapped_rules)):
                        r1, r2 = mapped_rules[i], mapped_rules[j]
                        if r1.action != r2.action:
                            # Direct conflict: one blocks while another warns or informs
                            p1 = self.calculate_effective_priority(r1)
                            p2 = self.calculate_effective_priority(r2)
                            if p1 > p2:
                                conflicts.append(ConflictReport(
                                    conflict_id=f"CONF-{r1.rule_id}-{r2.rule_id}",
                                    rule_ids=[r1.rule_id, r2.rule_id],
                                    description=f"Direct action conflict on '{act}': {r1.rule_id} ({r1.action}) vs {r2.rule_id} ({r2.action})",
                                    resolution_status="RESOLVED_BY_SEVERITY",
                                    winning_rule_id=r1.rule_id,
                                    reason=f"{r1.rule_id} has higher effective priority ({p1} vs {p2})."
                                ))
                            elif p2 > p1:
                                conflicts.append(ConflictReport(
                                    conflict_id=f"CONF-{r1.rule_id}-{r2.rule_id}",
                                    rule_ids=[r1.rule_id, r2.rule_id],
                                    description=f"Direct action conflict on '{act}': {r1.rule_id} ({r1.action}) vs {r2.rule_id} ({r2.action})",
                                    resolution_status="RESOLVED_BY_SEVERITY",
                                    winning_rule_id=r2.rule_id,
                                    reason=f"{r2.rule_id} has higher effective priority ({p2} vs {p1})."
                                ))
                            else:
                                # Equal priority and opposing actions: UNRESOLVED CONFLICT -> BLOCK
                                conf = ConflictReport(
                                    conflict_id=f"CONF-UNRESOLVED-{r1.rule_id}-{r2.rule_id}",
                                    rule_ids=[r1.rule_id, r2.rule_id],
                                    description=f"Unresolvable directive conflict on '{act}': {r1.rule_id} vs {r2.rule_id}",
                                    resolution_status="UNRESOLVED_CONFLICT",
                                    winning_rule_id=None,
                                    reason="Rules have identical effective priority but opposing enforcement actions."
                                )
                                conflicts.append(conf)
                                blocking_issues.append(PreflightIssueV2(
                                    severity=SeverityLevel.CRITICAL,
                                    code="BLOCK-CONFLICT-001",
                                    rule_id=f"{r1.rule_id}/{r2.rule_id}",
                                    message=f"Governance Conflict: {r1.rule_id} and {r2.rule_id} have conflicting actions on '{act}'.",
                                    remediation="Human or agent review required to explicitly declare supersession or adjust precedence."
                                ))

        # 3. Sort active rules by priority descending, with deterministic rule_id tiebreaker
        active_candidates.sort(key=lambda r: (self.calculate_effective_priority(r), r.rule_id), reverse=True)
        return active_candidates, conflicts, blocking_issues
