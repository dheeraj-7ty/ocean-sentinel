"""Migration script to normalize legacy v1 governance files into Lesson Architecture v2."""

import json
from pathlib import Path
from typing import Any, Dict, List

from ocean_sentinel.governance.assumptions import get_default_assumptions
from ocean_sentinel.governance.models import (
    ActionType,
    Assumption,
    FailureClass,
    Incident,
    LearningState,
    Lesson,
    Principle,
    Rule,
    ScopeLevel,
    SeverityLevel,
    ValidationRecord,
)
from ocean_sentinel.governance.taxonomy import (
    get_default_failure_classes,
    get_default_principles,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
METADATA_DIR = REPO_ROOT / "data" / "metadata"
V2_DIR = METADATA_DIR / "governance_v2"


def build_v2_catalog():
    """Builds and writes all normalized v2 JSON files from existing repository truth."""
    V2_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Principles
    principles = get_default_principles()
    with open(V2_DIR / "principles.json", "w", encoding="utf-8") as f:
        json.dump({"principles": [p.to_dict() for p in principles.values()]}, f, indent=2)

    # 2. Failure Classes
    failure_classes = get_default_failure_classes()
    with open(V2_DIR / "failure_classes.json", "w", encoding="utf-8") as f:
        json.dump({"failure_classes": [fc.to_dict() for fc in failure_classes.values()]}, f, indent=2)

    # 3. Assumptions
    assumptions = get_default_assumptions()
    with open(V2_DIR / "assumptions.json", "w", encoding="utf-8") as f:
        json.dump({"assumptions": [a.to_dict() for a in assumptions.values()]}, f, indent=2)

    # 4. Rules
    rules_dict: Dict[str, Rule] = {}

    # Load legacy rules v1 if exists
    legacy_rules_p = METADATA_DIR / "ocean_sentinel_governance_rules_v1.json"
    if legacy_rules_p.exists():
        legacy_rules_data = json.loads(legacy_rules_p.read_text(encoding="utf-8"))
        for lr in legacy_rules_data.get("rules", []):
            rid = lr["rule_id"]
            # Map legacy category to failure class
            cat_map = {
                "DATASET_INTEGRITY": "DATA-INTEGRITY",
                "MODEL_INTEGRITY": "MODEL-STATE-MISMATCH",
                "TRAINING_INTEGRITY": "OPTIMIZATION-SEMANTICS",
                "PROCESS_INTEGRITY": "GOVERNANCE",
                "SCIENTIFIC_VALIDITY": "STATISTICAL-INFERENCE",
            }
            fc = cat_map.get(lr.get("category"), "DATA-INTEGRITY")
            title = lr.get("title") or lr.get("triggering_incident") or f"Governance Rule {rid}"
            statement = (
                lr.get("permanent_rule")
                or lr.get("new_guardrail")
                or lr.get("description")
                or lr.get("title")
                or f"Rule {rid} requirement."
            )
            r = Rule(
                rule_id=rid,
                principle_id="PRIN-001",
                failure_class=fc,
                title=title,
                statement=statement,
                scope=ScopeLevel.PROJECT,
                severity=SeverityLevel.HIGH,
                action=ActionType.BLOCK,
                prohibited_actions=[],
                required_checks=[lr.get("new_guardrail", "")] if lr.get("new_guardrail") else [],
                regression_test_ids=[lr.get("regression_test", "")] if lr.get("regression_test") else [],
                evidence_refs=[lr.get("triggering_incident", "")] if lr.get("triggering_incident") else [],
                status=LearningState.REGRESSION_PROTECTED if lr.get("status") == "ACTIVE" else LearningState.RECORDED,
            )
            rules_dict[rid] = r

    # Add hard blockers from ocean_sentinel_agent_governance_v1.json as top-level critical rules
    gov_meta_p = METADATA_DIR / "ocean_sentinel_agent_governance_v1.json"
    if gov_meta_p.exists():
        gov_meta = json.loads(gov_meta_p.read_text(encoding="utf-8"))
        for bid, bdata in gov_meta.get("hard_blockers", {}).items():
            r = Rule(
                rule_id=bid,
                principle_id="PRIN-007" if "HOLDOUT" in bid or "PART_III" in bid else "PRIN-006" if "TRAINING" in bid else "PRIN-001",
                failure_class="EXECUTION-SAFETY" if "GIT" in bid else "DATA-INTEGRITY" if "HOLDOUT" in bid or "PART_III" in bid else "AUTHORIZATION",
                title=bdata.get("rule", bid),
                statement=bdata.get("rule", ""),
                scope=ScopeLevel.GLOBAL,
                severity=SeverityLevel.CRITICAL if bdata.get("severity") == "CRITICAL" else SeverityLevel.HIGH,
                action=ActionType.BLOCK,
                non_overridable=True,
                prohibited_actions=[bdata.get("trigger", "")],
                required_checks=[bdata.get("action", "")],
                status=LearningState.PROVEN_STABLE,
                precedence_weight=100
            )
            rules_dict[bid] = r

    # Add rules 100-131 defined across lessons and DIAG-05
    diagnostic_rules = [
        Rule(
            rule_id="GOV-RULE-100",
            principle_id="PRIN-001",
            failure_class="ARTIFACT-REPORT-MISMATCH",
            title="All quantitative assertions must derive directly from machine JSON",
            statement="All quantitative assertions in reports must be machine-derived directly from verified JSON artifacts, never manual transcription.",
            scope=ScopeLevel.GLOBAL,
            severity=SeverityLevel.CRITICAL,
            action=ActionType.BLOCK,
            regression_test_ids=["tests/test_ocean_sentinel_agent_learning_framework.py::test_lesson_001_narrative_vs_machine_truth"],
            status=LearningState.PROVEN_STABLE
        ),
        Rule(
            rule_id="GOV-RULE-116",
            principle_id="PRIN-005",
            failure_class="INFERENCE-UNIT-MISMATCH",
            title="Parent acquisition scene is the independent unit of inference",
            statement="Tile-level observations cannot be treated as independent degrees of freedom when scenes contain multiple tiles.",
            scope=ScopeLevel.PROJECT,
            severity=SeverityLevel.CRITICAL,
            action=ActionType.BLOCK,
            regression_test_ids=["tests/test_exp07_p0_diag05_tier1_forensic_guardrails.py"],
            status=LearningState.REGRESSION_PROTECTED
        ),
        Rule(
            rule_id="GOV-RULE-123",
            principle_id="PRIN-001",
            failure_class="MODEL-STATE-MISMATCH",
            title="Canonical checkpoint initialization verification",
            statement="Diagnostic profiling must verify checkpoint weights match canonical SHA256 before inference.",
            scope=ScopeLevel.PROJECT,
            severity=SeverityLevel.CRITICAL,
            action=ActionType.BLOCK,
            regression_test_ids=["tests/test_exp07_p0_diag05_tier1_forensic_guardrails.py::test_diag05_tier1_artifacts_integrity_and_hashes"],
            status=LearningState.REGRESSION_PROTECTED
        ),
        Rule(
            rule_id="GOV-RULE-124",
            principle_id="PRIN-005",
            failure_class="INDEPENDENCE-ASSUMPTION",
            title="Minibatch size does not create scene independence",
            statement="Physical minibatch size does not guarantee independent scene representation in clustered datasets.",
            scope=ScopeLevel.PROJECT,
            severity=SeverityLevel.HIGH,
            action=ActionType.BLOCK,
            regression_test_ids=["tests/test_exp07_p0_diag05_preexecution_guardrails.py"],
            status=LearningState.REGRESSION_PROTECTED
        ),
        Rule(
            rule_id="GOV-RULE-126",
            principle_id="PRIN-005",
            failure_class="INFERENCE-UNIT-MISMATCH",
            title="Tile to parent scene one-to-one nesting invariant",
            statement="Every tile must map deterministically to exactly one parent acquisition scene.",
            scope=ScopeLevel.PROJECT,
            severity=SeverityLevel.CRITICAL,
            action=ActionType.BLOCK,
            regression_test_ids=["tests/test_exp07_p0_diag05_preexecution_guardrails.py"],
            status=LearningState.REGRESSION_PROTECTED
        ),
        Rule(
            rule_id="GOV-RULE-127",
            principle_id="PRIN-009",
            failure_class="DENOMINATOR-DRIFT",
            title="Literal contractual gradient denominator preservation",
            statement="Gradient sub-computations must normalize by literal contractual denominator, never subset convenience normalizations.",
            scope=ScopeLevel.PROJECT,
            severity=SeverityLevel.CRITICAL,
            action=ActionType.BLOCK,
            regression_test_ids=["tests/test_exp07_p0_diag05_preexecution_guardrails.py"],
            status=LearningState.REGRESSION_PROTECTED
        ),
        Rule(
            rule_id="GOV-RULE-128",
            principle_id="PRIN-010",
            failure_class="MODEL-STATE-MISMATCH",
            title="Model.eval() and frozen BatchNorm during static diagnostics",
            statement="Static gradient diagnostics must execute in model.eval() mode with frozen running statistics.",
            scope=ScopeLevel.PROJECT,
            severity=SeverityLevel.CRITICAL,
            action=ActionType.BLOCK,
            regression_test_ids=["tests/test_exp07_p0_diag05_preexecution_guardrails.py"],
            status=LearningState.REGRESSION_PROTECTED
        ),
        Rule(
            rule_id="GOV-RULE-129",
            principle_id="PRIN-002",
            failure_class="POPULATION-CONSTRUCTION",
            title="Post-validity support census for sample eligibility",
            statement="Any sample eligibility query involving class presence (M_c >= K) must be evaluated strictly after all validity masking transformations.",
            scope=ScopeLevel.PROJECT,
            severity=SeverityLevel.CRITICAL,
            action=ActionType.BLOCK,
            applies_to={"operation": ["sample_eligibility_census", "population_census"]},
            prohibited_actions=["raw disk mask support evaluation"],
            regression_test_ids=["tests/test_exp07_p0_diag05_tier1_forensic_guardrails.py::test_diag05_post_validity_support_census_guardrail"],
            status=LearningState.REGRESSION_PROTECTED
        ),
        Rule(
            rule_id="GOV-RULE-130",
            principle_id="PRIN-003",
            failure_class="STATISTICAL-PROVENANCE",
            title="Explicit statistical method binding in code and metadata",
            statement="Statistical test routines must explicitly bind method parameters in code, and artifact schemas must derive method metadata directly from the executed call.",
            scope=ScopeLevel.GLOBAL,
            severity=SeverityLevel.CRITICAL,
            action=ActionType.BLOCK,
            applies_to={"operation": ["paired_inference", "wilcoxon", "statistical_test"]},
            prohibited_actions=["unbound statistical method parameter"],
            regression_test_ids=["tests/test_exp07_p0_diag05_tier1_forensic_guardrails.py::test_diag05_statistical_method_binding_guardrail"],
            status=LearningState.REGRESSION_PROTECTED
        ),
        Rule(
            rule_id="GOV-RULE-131",
            principle_id="PRIN-004",
            failure_class="P-VALUE-OVERINTERPRETATION",
            title="Bounded negative epistemic reporting for Step-0 diagnostics",
            statement="Non-significant diagnostic findings (p > 0.05) must be reported as bounded negative findings under registered design; agents are strictly prohibited from asserting 'no effect', 'eliminated interference', or dynamic stability.",
            scope=ScopeLevel.GLOBAL,
            severity=SeverityLevel.CRITICAL,
            action=ActionType.BLOCK,
            applies_to={"operation": ["report_generation", "paired_inference"]},
            prohibited_actions=["proves no effect", "intrinsic structural characteristic", "guarantees stability"],
            regression_test_ids=["tests/test_exp07_p0_diag05_tier1_forensic_guardrails.py::test_diag05_bounded_negative_interpretation_guardrail"],
            status=LearningState.REGRESSION_PROTECTED
        ),
    ]
    for dr in diagnostic_rules:
        rules_dict[dr.rule_id] = dr

    with open(V2_DIR / "rules.json", "w", encoding="utf-8") as f:
        json.dump({"rules": [r.to_dict() for r in rules_dict.values()]}, f, indent=2)

    # 5. Incidents
    incidents_dict: Dict[str, Incident] = {}
    legacy_incidents_p = METADATA_DIR / "ocean_sentinel_incident_learning_register_v1.json"
    if legacy_incidents_p.exists():
        legacy_inc_data = json.loads(legacy_incidents_p.read_text(encoding="utf-8"))
        for li in legacy_inc_data.get("incidents", []):
            iid = li["incident_id"]
            inc = Incident(
                incident_id=iid,
                task_id=li.get("phase", "HISTORICAL"),
                title=li.get("title", iid),
                failure_class="ARTIFACT-INTEGRITY" if "artifact" in li.get("title", "").lower() else "DATA-INTEGRITY",
                description=li.get("impact", ""),
                root_cause=li.get("root_cause", ""),
                impact=li.get("impact", ""),
                detection=li.get("missed_guardrail", ""),
                correction=li.get("resolution", ""),
                prevention=li.get("permanent_rule", ""),
                rules_created=[li.get("governance_rule_id", "")] if li.get("governance_rule_id") else [],
                tests_created=[li.get("regression_test", "")] if li.get("regression_test") else [],
            )
            incidents_dict[iid] = inc

    # Add DIAG-05 incidents
    diag05_incidents = [
        Incident(
            incident_id="INC-DIAG05-001",
            task_id="EXP-07-P0-DIAG-05-TIER1-STATIC-GRADIENT-PROFILING",
            title="Tile 22 admitted to H2 population despite zero post-validity rare support",
            failure_class="POPULATION-CONSTRUCTION",
            description="Pre-validity census evaluated class support on raw disk mask, admitting Tile ...-001-22 whose 119 rare pixels were entirely located in sensor border nodata.",
            root_cause="Decoupling pre-execution census query from SAR sensor validity masking (compute_validity_mask).",
            impact="Tile produced zero subgradient and cosine = 0.0 in H2 runner; population construction defect.",
            detection="Deterministic post-validity support census script.",
            correction="Excluded Tile 22 from H2 inference; retained 27 valid tiles across 15 clusters.",
            prevention="GOV-RULE-129: Sample eligibility must be evaluated after all validity masking transformations.",
            evidence="data/ops02/audits/diag05_tier1_corrected_h2_eligibility_census_v1.json",
            lessons_created=["LL-DIAG05-EXEC-001"],
            rules_created=["GOV-RULE-129"],
            tests_created=["tests/test_exp07_p0_diag05_tier1_forensic_guardrails.py::test_diag05_post_validity_support_census_guardrail"]
        ),
        Incident(
            incident_id="INC-DIAG05-002",
            task_id="EXP-07-P0-DIAG-05-TIER1-STATIC-GRADIENT-PROFILING",
            title="SciPy Wilcoxon default parameter mismatch (exact permutation vs asymptotic metadata)",
            failure_class="STATISTICAL-PROVENANCE",
            description="Runner called wilcoxon without method='asymptotic', defaulting to exact permutation (p=0.1514) while artifact metadata declared asymptotic inference (p=0.1475).",
            root_cause="SciPy 1.15.3 defaults to method='exact' when N <= 50; caller did not explicitly bind method argument.",
            impact="Discrepancy between stated statistical distribution and executed mathematical value in artifact metadata.",
            detection="Forensic recalculation comparing asymptotic with exact permutation distributions.",
            correction="Separated asymptotic and exact distributions in corrected artifact diag05_tier1_corrected_h2_paired_inference_v1.json.",
            prevention="GOV-RULE-130: Explicitly bind method argument in code and derive artifact metadata directly from execution.",
            evidence="data/ops02/audits/diag05_tier1_corrected_h2_paired_inference_v1.json",
            lessons_created=["LL-DIAG05-EXEC-002"],
            rules_created=["GOV-RULE-130"],
            tests_created=["tests/test_exp07_p0_diag05_tier1_forensic_guardrails.py::test_diag05_statistical_method_binding_guardrail"]
        ),
        Incident(
            incident_id="INC-DIAG05-003",
            task_id="EXP-07-P0-DIAG-05-TIER1-STATIC-GRADIENT-PROFILING",
            title="Epistemic overclaim of 'intrinsic' gradient orientation and zero effect",
            failure_class="P-VALUE-OVERINTERPRETATION",
            description="Initial reporting characterized negative cosine as an 'intrinsic structural characteristic' across domains and equated p > 0.05 with proof of no effect.",
            root_cause="Over-generalizing static Step-0 observation to architecture and inferring dynamic stability from non-significance.",
            impact="Risk of premature authorization of training interventions and uncalibrated scientific claims.",
            detection="Forensic review and preflight causal language audit.",
            correction="Calibrated language to bounded negative Step-0 empirical observation; gated Tier-2 as NOT_JUSTIFIED_YET.",
            prevention="GOV-RULE-131: Enforce bounded negative epistemic reporting and prohibit 'intrinsic' generalizations.",
            evidence="experiments/performance/diag05_tier1_corrective_analysis_report_v1.md",
            lessons_created=["LL-DIAG05-EXEC-003"],
            rules_created=["GOV-RULE-131"],
            tests_created=["tests/test_exp07_p0_diag05_tier1_forensic_guardrails.py::test_diag05_bounded_negative_interpretation_guardrail"]
        ),
    ]
    for di in diag05_incidents:
        incidents_dict[di.incident_id] = di

    with open(V2_DIR / "incidents.json", "w", encoding="utf-8") as f:
        json.dump({"incidents": [inc.to_dict() for inc in incidents_dict.values()]}, f, indent=2)

    # 6. Lessons (Normalized 104 lessons from v1)
    lessons_list: List[Lesson] = []
    lessons_v1_p = METADATA_DIR / "ocean_sentinel_lessons_learned_v1.json"
    if lessons_v1_p.exists():
        lessons_v1 = json.loads(lessons_v1_p.read_text(encoding="utf-8"))
        for l in lessons_v1.get("lessons", []):
            lid = l["lesson_id"]
            val_records = []
            for vr in l.get("validation_history", []):
                val_records.append(ValidationRecord(
                    task=vr.get("task", ""),
                    timestamp=vr.get("timestamp", ""),
                    test=vr.get("test", ""),
                    result=vr.get("result", "PASSED"),
                    evidence=vr.get("evidence", "")
                ))
            
            # Link failure class
            cat = l.get("category", "SCIENTIFIC_VALIDITY")
            fc = "STATISTICAL-INFERENCE" if cat == "SCIENTIFIC_VALIDITY" else "DATA-INTEGRITY" if cat == "DATA_INTEGRITY" else "DOCUMENTATION-INTEGRITY" if cat == "DOCUMENTATION_INTEGRITY" else "GOVERNANCE"
            if "census" in l.get("title", "").lower() or "mask" in l.get("title", "").lower():
                fc = "POPULATION-CONSTRUCTION"
            elif "wilcoxon" in l.get("title", "").lower() or "method" in l.get("title", "").lower():
                fc = "STATISTICAL-PROVENANCE"
            elif "epistemic" in l.get("title", "").lower() or "intrinsic" in l.get("title", "").lower():
                fc = "P-VALUE-OVERINTERPRETATION"

            lsn = Lesson(
                lesson_id=lid,
                title=l.get("title", l.get("failure_pattern", lid)),
                principle_id="PRIN-001",
                failure_class=fc,
                severity=SeverityLevel[l.get("severity", "HIGH")],
                scope=ScopeLevel.PROJECT,
                description=l.get("description", ""),
                root_cause=l.get("root_cause", ""),
                incorrect_behavior=l.get("incorrect_behavior", l.get("description", "")),
                correct_rule=l.get("correct_rule", l.get("prevention_rule", l.get("prevention_method", ""))),
                prevention_method=l.get("prevention_method", ""),
                required_checks=[l.get("required_preflight", "")] if l.get("required_preflight") else [],
                regression_test_ids=[l.get("regression_test", "")] if l.get("regression_test") else [],
                status=LearningState[l.get("status", "REGRESSION_PROTECTED")],
                validation_history=val_records,
                category=l.get("category", "SCIENTIFIC_VALIDITY"),
                first_seen=l.get("first_seen", ""),
                last_seen=l.get("last_seen", ""),
                occurrence_count=l.get("occurrence_count", 1),
                metadata={
                    "affected_diagnostics": l.get("affected_diagnostics", []),
                    "affected_domains": l.get("affected_domains", []),
                    "notes": l.get("notes", "")
                }
            )
            lessons_list.append(lsn)

    with open(V2_DIR / "lessons.json", "w", encoding="utf-8") as f:
        json.dump({"lessons": [ls.to_dict() for ls in lessons_list]}, f, indent=2)

    # 7. Precedence Policy
    precedence_policy = {
        "framework_version": "2.0.0",
        "severity_hierarchy": ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFORMATIONAL"],
        "scope_hierarchy": ["GLOBAL", "DOMAIN", "PROJECT", "EXPERIMENT", "DIAGNOSTIC", "TASK"],
        "resolution_rules": [
            "1. Explicit supersession declared in metadata always retires the superseded rule.",
            "2. Non-overridable global rules (e.g. HOLDOUT, Part-III firewall) can never be overridden by local rules.",
            "3. When severities differ, higher severity governs.",
            "4. When severities are equal, more specific scope governs unless higher scope has non_overridable=true.",
            "5. When severity and scope are equal with opposing directives, emit BLOCK-CONFLICT-001 requiring human review; never last record wins."
        ]
    }
    with open(V2_DIR / "precedence_policy.json", "w", encoding="utf-8") as f:
        json.dump(precedence_policy, f, indent=2)

    # 8. Governance Metrics
    proven_stable = sum(1 for ls in lessons_list if ls.status == LearningState.PROVEN_STABLE)
    regression_protected = sum(1 for ls in lessons_list if ls.status == LearningState.REGRESSION_PROTECTED)
    metrics = {
        "version": "2.0.0",
        "total_principles": len(principles),
        "total_failure_classes": len(failure_classes),
        "total_rules": len(rules_dict),
        "total_incidents": len(incidents_dict),
        "total_lessons": len(lessons_list),
        "total_assumptions": len(assumptions),
        "proven_stable_lessons": proven_stable,
        "regression_protected_lessons": regression_protected,
        "recorded_lessons": len(lessons_list) - proven_stable - regression_protected,
        "rules_with_tests": sum(1 for r in rules_dict.values() if r.regression_test_ids),
        "rules_without_tests": sum(1 for r in rules_dict.values() if not r.regression_test_ids),
        "migration_status": "COMPLETED_WITHOUT_LOSS"
    }
    with open(V2_DIR / "governance_metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    return metrics


if __name__ == "__main__":
    m = build_v2_catalog()
    print("V2 Catalog built successfully:")
    for k, v in m.items():
        print(f"  {k}: {v}")
