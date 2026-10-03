"""Governance Knowledge Store: In-memory cached loader and indexer for Lesson Architecture v2."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ocean_sentinel.governance.models import (
    ActionType,
    Assumption,
    AssumptionState,
    FailureClass,
    Incident,
    LearningState,
    Lesson,
    Principle,
    Rule,
    ScopeLevel,
    SeverityLevel,
    ValidationRecord,
    EvidenceStrength,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
V2_DIR = REPO_ROOT / "data" / "metadata" / "governance_v2"


class GovernanceStore:
    """Thread-safe, high-performance in-memory store for normalized governance v2 entities."""

    _instance: Optional["GovernanceStore"] = None

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or V2_DIR
        self.principles: Dict[str, Principle] = {}
        self.failure_classes: Dict[str, FailureClass] = {}
        self.rules: Dict[str, Rule] = {}
        self.incidents: Dict[str, Incident] = {}
        self.lessons: Dict[str, Lesson] = {}
        self.assumptions: Dict[str, Assumption] = {}
        self.metrics: Dict[str, Any] = {}
        self.load()

    @classmethod
    def get_instance(cls, force_reload: bool = False) -> "GovernanceStore":
        if cls._instance is None or force_reload:
            cls._instance = cls()
        return cls._instance

    def load(self):
        """Loads all entities from disk into indexed in-memory dictionaries."""
        if not self.data_dir.exists():
            # Build automatically if directory doesn't exist yet
            from ocean_sentinel.governance.migration import build_v2_catalog
            build_v2_catalog()

        # 1. Principles
        p_path = self.data_dir / "principles.json"
        if p_path.exists():
            data = json.loads(p_path.read_text(encoding="utf-8"))
            self.principles = {
                p["principle_id"]: Principle(
                    principle_id=p["principle_id"],
                    title=p["title"],
                    statement=p["statement"],
                    rationale=p["rationale"],
                    scope=ScopeLevel[p.get("scope", "GLOBAL")],
                    domain=p.get("domain", "general"),
                    metadata=p.get("metadata", {})
                )
                for p in data.get("principles", [])
            }

        # 2. Failure Classes
        fc_path = self.data_dir / "failure_classes.json"
        if fc_path.exists():
            data = json.loads(fc_path.read_text(encoding="utf-8"))
            self.failure_classes = {
                fc["class_id"]: FailureClass(
                    class_id=fc["class_id"],
                    name=fc["name"],
                    description=fc["description"],
                    parent_class=fc.get("parent_class"),
                    aliases=fc.get("aliases", []),
                    typical_severity=SeverityLevel[fc.get("typical_severity", "HIGH")],
                    prevention_guideline=fc.get("prevention_guideline", "")
                )
                for fc in data.get("failure_classes", [])
            }

        # 3. Assumptions
        asmp_path = self.data_dir / "assumptions.json"
        if asmp_path.exists():
            data = json.loads(asmp_path.read_text(encoding="utf-8"))
            self.assumptions = {
                a["assumption_id"]: Assumption(
                    assumption_id=a["assumption_id"],
                    statement=a["statement"],
                    status=AssumptionState[a.get("status", "UNVERIFIED")],
                    scope=ScopeLevel[a.get("scope", "PROJECT")],
                    verification_method=a.get("verification_method", ""),
                    associated_rules=a.get("associated_rules", []),
                    verified_in_task=a.get("verified_in_task"),
                    notes=a.get("notes", "")
                )
                for a in data.get("assumptions", [])
            }

        # 4. Rules
        r_path = self.data_dir / "rules.json"
        if r_path.exists():
            data = json.loads(r_path.read_text(encoding="utf-8"))
            self.rules = {
                r["rule_id"]: Rule(
                    rule_id=r["rule_id"],
                    principle_id=r["principle_id"],
                    failure_class=r["failure_class"],
                    title=r["title"],
                    statement=r["statement"],
                    scope=ScopeLevel[r.get("scope", "PROJECT")],
                    severity=SeverityLevel[r.get("severity", "HIGH")],
                    action=ActionType[r.get("action", "BLOCK")],
                    applies_to=r.get("applies_to", {}),
                    prohibited_actions=r.get("prohibited_actions", []),
                    required_checks=r.get("required_checks", []),
                    regression_test_ids=r.get("regression_test_ids", []),
                    evidence_refs=r.get("evidence_refs", []),
                    incident_refs=r.get("incident_refs", []),
                    supersedes=r.get("supersedes", []),
                    superseded_by=r.get("superseded_by"),
                    status=LearningState[r.get("status", "REGRESSION_PROTECTED")],
                    non_overridable=r.get("non_overridable", False),
                    precedence_weight=r.get("precedence_weight", 0),
                    evidence_lineage=r.get("evidence_lineage", {}),
                    evidence_strength=EvidenceStrength[r.get("evidence_strength", "DIRECT_MEASUREMENT")],
                )
                for r in data.get("rules", [])
            }

        # 5. Incidents
        inc_path = self.data_dir / "incidents.json"
        if inc_path.exists():
            data = json.loads(inc_path.read_text(encoding="utf-8"))
            self.incidents = {
                inc["incident_id"]: Incident(
                    incident_id=inc["incident_id"],
                    task_id=inc["task_id"],
                    title=inc["title"],
                    failure_class=inc["failure_class"],
                    description=inc["description"],
                    root_cause=inc["root_cause"],
                    impact=inc["impact"],
                    detection=inc["detection"],
                    correction=inc["correction"],
                    prevention=inc["prevention"],
                    evidence=inc.get("evidence", ""),
                    lessons_created=inc.get("lessons_created", []),
                    rules_created=inc.get("rules_created", []),
                    tests_created=inc.get("tests_created", []),
                    timestamp=inc.get("timestamp", "")
                )
                for inc in data.get("incidents", [])
            }

        # 6. Lessons
        ls_path = self.data_dir / "lessons.json"
        if ls_path.exists():
            data = json.loads(ls_path.read_text(encoding="utf-8"))
            self.lessons = {}
            for l in data.get("lessons", []):
                val_records = [
                    ValidationRecord(
                        task=v.get("task", ""),
                        timestamp=v.get("timestamp", ""),
                        test=v.get("test", ""),
                        result=v.get("result", "PASSED"),
                        environment=v.get("environment", "python-3.10"),
                        scope=v.get("scope", "regression"),
                        evidence=v.get("evidence", ""),
                        fingerprint=v.get("fingerprint", ""),
                    )
                    for v in l.get("validation_history", [])
                ]
                self.lessons[l["lesson_id"]] = Lesson(
                    lesson_id=l["lesson_id"],
                    title=l["title"],
                    principle_id=l.get("principle_id", "PRIN-001"),
                    failure_class=l.get("failure_class", "GENERAL"),
                    severity=SeverityLevel[l.get("severity", "HIGH")],
                    scope=ScopeLevel[l.get("scope", "PROJECT")],
                    description=l.get("description", ""),
                    root_cause=l.get("root_cause", ""),
                    incorrect_behavior=l.get("incorrect_behavior", ""),
                    correct_rule=l.get("correct_rule", ""),
                    prevention_method=l.get("prevention_method", ""),
                    rules=l.get("rules", []),
                    incidents=l.get("incidents", []),
                    required_checks=l.get("required_checks", []),
                    regression_test_ids=l.get("regression_test_ids", []),
                    status=LearningState[l.get("status", "REGRESSION_PROTECTED")],
                    validation_history=val_records,
                    aliases=l.get("aliases", []),
                    category=l.get("category", "SCIENTIFIC_VALIDITY"),
                    first_seen=l.get("first_seen", ""),
                    last_seen=l.get("last_seen", ""),
                    occurrence_count=l.get("occurrence_count", 1),
                    metadata=l.get("metadata", {})
                )

        # 7. Metrics
        m_path = self.data_dir / "governance_metrics.json"
        if m_path.exists():
            self.metrics = json.loads(m_path.read_text(encoding="utf-8"))

    def get_rule(self, rule_id: str) -> Optional[Rule]:
        return self.rules.get(rule_id)

    def get_lesson(self, lesson_id: str) -> Optional[Lesson]:
        return self.lessons.get(lesson_id)

    def get_failure_class(self, class_id: str) -> Optional[FailureClass]:
        return self.failure_classes.get(class_id)

    def get_principle(self, principle_id: str) -> Optional[Principle]:
        return self.principles.get(principle_id)

    def get_assumption(self, assumption_id: str) -> Optional[Assumption]:
        return self.assumptions.get(assumption_id)

    def list_rules(self) -> List[Rule]:
        return list(self.rules.values())

    def list_lessons(self) -> List[Lesson]:
        return list(self.lessons.values())

    def list_failure_classes(self) -> List[FailureClass]:
        return list(self.failure_classes.values())

    def list_assumptions(self) -> List[Assumption]:
        return list(self.assumptions.values())

    def get_incident(self, incident_id: str) -> Optional[Incident]:
        return self.incidents.get(incident_id)

    def list_incidents(self) -> List[Incident]:
        return list(self.incidents.values())

    def list_principles(self) -> List[Principle]:
        return list(self.principles.values())

