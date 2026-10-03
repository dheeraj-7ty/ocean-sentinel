"""Hybrid Retrieval Engine combining exact entity lookup, structured scope filters, trigger patterns, and lexical search."""

import json
import re
from typing import Any, Dict, List, Optional, Set
from ocean_sentinel.governance.models import (
    LearningState,
    Lesson,
    RetrievalResult,
    Rule,
    ScopeLevel,
    SeverityLevel,
    TaskContext,
)


class HybridRetrievalEngine:
    """Retrieves relevant lessons and rules with human-readable relevance explainability."""

    def __init__(self, lessons: List[Lesson], rules: List[Rule]):
        self.lessons = lessons
        self.rules = rules
        self._build_indices()

    def _build_indices(self):
        self.lessons_by_id: Dict[str, Lesson] = {}
        for l in self.lessons:
            self.lessons_by_id[l.lesson_id] = l
            for alias in l.aliases:
                self.lessons_by_id[alias] = l

        self.rules_by_id: Dict[str, Rule] = {}
        for r in self.rules:
            self.rules_by_id[r.rule_id] = r

    def retrieve_for_context(self, context: TaskContext, max_results: int = 10) -> List[RetrievalResult]:
        """Performs hybrid retrieval given a rich TaskContext."""
        results: List[RetrievalResult] = []
        seen_ids: Set[str] = set()

        text_to_scan = []
        if context.proposed_plan:
            text_to_scan.append(context.proposed_plan)
        if context.proposed_command:
            text_to_scan.append(context.proposed_command)
        joined_text = " ".join(text_to_scan).lower()

        # Tokenize query tokens from context
        query_tokens = set()
        for field_val in (context.domain + context.operation + context.risk_class):
            for tok in re.findall(r"\w+", field_val.lower()):
                if len(tok) >= 3:
                    query_tokens.add(tok)
        if context.diagnostic:
            query_tokens.add(context.diagnostic.lower())
        if context.experiment:
            query_tokens.add(context.experiment.lower())

        # 1. Check rules
        for rule in self.rules:
            score = 0.0
            reasons = []
            scope_match = False
            fc_match = False

            # Trigger pattern match (very high relevance)
            for pat in rule.applies_to.get("trigger_patterns", []):
                if re.search(pat, joined_text, re.IGNORECASE):
                    score = max(score, 0.95)
                    reasons.append(f"Trigger pattern matched: '{pat}'")

            for act in rule.prohibited_actions:
                if act.lower() in joined_text or any(act.lower() in op.lower() for op in context.operation):
                    score = max(score, 0.98)
                    reasons.append(f"Prohibited action matched: '{act}'")

            # Structured scope match
            if rule.scope == ScopeLevel.GLOBAL:
                scope_match = True
            elif rule.scope == ScopeLevel.DIAGNOSTIC and context.diagnostic:
                if rule.applies_to.get("diagnostic", "").lower() == context.diagnostic.lower():
                    scope_match = True
                    score = max(score, 0.85)
                    reasons.append(f"Diagnostic scope matched: '{context.diagnostic}'")

            # Domain / operation match
            rule_domains = rule.applies_to.get("domain", [])
            if isinstance(rule_domains, str):
                rule_domains = [rule_domains]
            if any(d.lower() in [cd.lower() for cd in context.domain] for d in rule_domains):
                score = max(score, 0.80)
                reasons.append(f"Domain matched: {rule_domains}")

            rule_ops = rule.applies_to.get("operation", [])
            if isinstance(rule_ops, str):
                rule_ops = [rule_ops]
            if any(o.lower() in [co.lower() for co in context.operation] for o in rule_ops):
                score = max(score, 0.85)
                reasons.append(f"Target operation matched: {rule_ops}")

            # Failure class match
            if rule.failure_class in context.risk_class or any(r.lower() in rule.failure_class.lower() for r in context.risk_class):
                fc_match = True
                score = max(score, 0.75)
                reasons.append(f"Failure class matched: '{rule.failure_class}'")

            if score > 0.0 and rule.rule_id not in seen_ids:
                seen_ids.add(rule.rule_id)
                results.append(RetrievalResult(
                    item_id=rule.rule_id,
                    item_type="rule",
                    score=score,
                    relevance_reason="; ".join(reasons),
                    scope_match=scope_match,
                    failure_class_match=fc_match,
                    severity=rule.severity,
                    status=rule.status,
                    item=rule.to_dict()
                ))

        # 2. Check lessons
        for lesson in self.lessons:
            score = 0.0
            reasons = []
            scope_match = False
            fc_match = False

            # Check exact ID or aliases
            if context.task_id and context.task_id.lower() in lesson.title.lower():
                score = max(score, 0.90)
                reasons.append("Task ID present in lesson title")

            # Check diagnostic
            if context.diagnostic and any(context.diagnostic.lower() in d.lower() for d in lesson.metadata.get("affected_diagnostics", [])):
                score = max(score, 0.85)
                reasons.append(f"Lesson explicitly affects diagnostic '{context.diagnostic}'")

            # Check failure class
            if lesson.failure_class in context.risk_class or any(r.lower() in lesson.failure_class.lower() for r in context.risk_class):
                fc_match = True
                score = max(score, 0.75)
                reasons.append(f"Failure class matched: '{lesson.failure_class}'")

            # Lexical keyword match on title, description, and root cause
            lesson_text = f"{lesson.title} {lesson.description} {lesson.root_cause} {lesson.prevention_method}".lower()
            matched_tokens = [tok for tok in query_tokens if tok in lesson_text]
            if matched_tokens:
                token_score = min(0.70, 0.30 + 0.08 * len(matched_tokens))
                if token_score > score:
                    score = token_score
                    reasons.append(f"Keyword match on: {matched_tokens[:4]}")

            if score > 0.0 and lesson.lesson_id not in seen_ids:
                seen_ids.add(lesson.lesson_id)
                results.append(RetrievalResult(
                    item_id=lesson.lesson_id,
                    item_type="lesson",
                    score=score,
                    relevance_reason="; ".join(reasons),
                    scope_match=scope_match,
                    failure_class_match=fc_match,
                    severity=lesson.severity,
                    status=lesson.status,
                    item=lesson.to_dict()
                ))

        results.sort(key=lambda x: (x.score, x.severity.rank), reverse=True)
        return results[:max_results]

    def retrieve_by_query(self, query: str, filters: Optional[Dict[str, Any]] = None, max_results: int = 10) -> List[RetrievalResult]:
        """Free-form query search with structured filters."""
        query_tokens = [tok.lower() for tok in re.findall(r"\w+", query) if len(tok) >= 3]
        results: List[RetrievalResult] = []
        seen_ids: Set[str] = set()

        # Check exact ID lookup first
        q_upper = query.strip().upper()
        if q_upper in self.rules_by_id:
            r = self.rules_by_id[q_upper]
            return [RetrievalResult(
                item_id=r.rule_id,
                item_type="rule",
                score=1.0,
                relevance_reason=f"Exact Rule ID match: '{r.rule_id}'",
                scope_match=True,
                failure_class_match=True,
                severity=r.severity,
                status=r.status,
                item=r.to_dict()
            )]
        if q_upper in self.lessons_by_id:
            l = self.lessons_by_id[q_upper]
            return [RetrievalResult(
                item_id=l.lesson_id,
                item_type="lesson",
                score=1.0,
                relevance_reason=f"Exact Lesson ID match: '{l.lesson_id}'",
                scope_match=True,
                failure_class_match=True,
                severity=l.severity,
                status=l.status,
                item=l.to_dict()
            )]

        # Search across rules
        for r in self.rules:
            pact_str = " ".join(r.prohibited_actions)
            chk_str = " ".join(r.required_checks)
            app_str = json.dumps(r.applies_to)
            text = f"{r.rule_id} {r.title} {r.statement} {r.failure_class} {pact_str} {chk_str} {app_str}".lower()
            matches = [t for t in query_tokens if t in text]
            if matches:
                score = min(0.95, 0.40 + 0.15 * len(matches))
                seen_ids.add(r.rule_id)
                results.append(RetrievalResult(
                    item_id=r.rule_id,
                    item_type="rule",
                    score=score,
                    relevance_reason=f"Lexical match on {matches}",
                    scope_match=True,
                    failure_class_match=False,
                    severity=r.severity,
                    status=r.status,
                    item=r.to_dict()
                ))

        # Search across lessons
        for l in self.lessons:
            if l.lesson_id in seen_ids:
                continue
            chk_str = " ".join(l.required_checks)
            alias_str = " ".join(l.aliases)
            text = f"{l.lesson_id} {l.title} {l.description} {l.root_cause} {l.prevention_method} {chk_str} {alias_str}".lower()
            matches = [t for t in query_tokens if t in text]
            if matches:
                score = min(0.90, 0.35 + 0.12 * len(matches))
                seen_ids.add(l.lesson_id)
                results.append(RetrievalResult(
                    item_id=l.lesson_id,
                    item_type="lesson",
                    score=score,
                    relevance_reason=f"Lexical match on {matches}",
                    scope_match=True,
                    failure_class_match=False,
                    severity=l.severity,
                    status=l.status,
                    item=l.to_dict()
                ))

        results.sort(key=lambda x: (x.score, x.severity.rank), reverse=True)
        return results[:max_results]
