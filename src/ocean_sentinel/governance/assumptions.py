"""Explicit Assumption Registry for Ocean Sentinel Institutional Learning."""

from typing import Dict, List
from ocean_sentinel.governance.models import Assumption, AssumptionState, ScopeLevel


def get_default_assumptions() -> Dict[str, Assumption]:
    """Returns the registered operational and scientific assumptions."""
    assumptions = [
        Assumption(
            assumption_id="ASSUMP-001",
            statement="Each physical tile maps deterministically and uniquely to exactly one parent acquisition scene.",
            status=AssumptionState.VERIFIED,
            scope=ScopeLevel.PROJECT,
            verification_method="Audited against ops02_physical_dataset_manifest_v1.json; 100% verified across all 132 TRAIN tiles.",
            associated_rules=["GOV-RULE-116", "GOV-RULE-126"],
            verified_in_task="DIAG05-TIER1-CORRECTIVE-CLOSURE-AND-GOVERNANCE-HARDENING",
            notes="Tile filename contains scene timestamp and burst identifier."
        ),
        Assumption(
            assumption_id="ASSUMP-002",
            statement="Sample support thresholds (M_c >= K) are evaluated after applying SAR sensor validity masking and border nodata exclusion.",
            status=AssumptionState.VERIFIED,
            scope=ScopeLevel.PROJECT,
            verification_method="Enforced via GOV-RULE-129 and test_diag05_post_validity_support_census_guardrail.",
            associated_rules=["GOV-RULE-129"],
            verified_in_task="DIAG05-TIER1-CORRECTIVE-CLOSURE-AND-GOVERNANCE-HARDENING",
            notes="Previous raw-mask census admitted Tile 22 which had 0 valid rare pixels post-masking."
        ),
        Assumption(
            assumption_id="ASSUMP-003",
            statement="Statistical test functions (e.g. scipy.stats.wilcoxon) have their method parameter explicitly bound in code and artifact metadata.",
            status=AssumptionState.VERIFIED,
            scope=ScopeLevel.GLOBAL,
            verification_method="Enforced via GOV-RULE-130 and test_diag05_statistical_method_binding_guardrail.",
            associated_rules=["GOV-RULE-130"],
            verified_in_task="DIAG05-TIER1-CORRECTIVE-CLOSURE-AND-GOVERNANCE-HARDENING",
            notes="Prevents SciPy exact permutation vs asymptotic distribution defaults mismatch."
        ),
        Assumption(
            assumption_id="ASSUMP-004",
            statement="Model is in explicit model.eval() mode with BatchNorm running statistics frozen during static diagnostic profiling.",
            status=AssumptionState.VERIFIED,
            scope=ScopeLevel.PROJECT,
            verification_method="Enforced via GOV-RULE-128 and pre-execution model state assertion.",
            associated_rules=["GOV-RULE-128"],
            verified_in_task="EXP-07-P0-DIAG-05-FINAL-TIER1-EXECUTION-CONTRACT-CHECK",
            notes="Running mean and variance buffers are asserted bit-for-bit identical before and after passes."
        ),
        Assumption(
            assumption_id="ASSUMP-005",
            statement="The reported p-value and test statistic in audit artifacts are generated directly by the executed routine rather than hardcoded or manually copied.",
            status=AssumptionState.VERIFIED,
            scope=ScopeLevel.GLOBAL,
            verification_method="Enforced via GOV-RULE-100 and test_diag05_corrected_paired_inference_contracts.",
            associated_rules=["GOV-RULE-100", "GOV-RULE-130"],
            verified_in_task="DIAG05-TIER1-CORRECTIVE-CLOSURE-AND-GOVERNANCE-HARDENING",
            notes="Eliminates discrepancy between saved numerical values and descriptive text."
        ),
        Assumption(
            assumption_id="ASSUMP-006",
            statement="Physical minibatch size B_phys = 4 guarantees independent parent scene representations across batches.",
            status=AssumptionState.CONTRADICTED,
            scope=ScopeLevel.PROJECT,
            verification_method="Audited against OPS-02 TRAIN clustering; scenes contain up to 4 tiles that co-occur in the same minibatch.",
            associated_rules=["GOV-RULE-124"],
            verified_in_task="DIAG05-TIER1-FORENSIC-ANALYSIS-AND-GOVERNANCE-LEARNING",
            notes="Minibatch dispersion is an empirical minibatch property, not an independent scene property."
        ),
        Assumption(
            assumption_id="ASSUMP-007",
            statement="Step-0 non-significance (p > 0.05) implies that multi-epoch training will not experience gradient interference or optimization instability.",
            status=AssumptionState.CONTRADICTED,
            scope=ScopeLevel.PROJECT,
            verification_method="Static Step-0 evaluation measures initialization geometry only; multi-epoch dynamics require separate dynamic evidence.",
            associated_rules=["GOV-RULE-131"],
            verified_in_task="DIAG05-TIER1-CORRECTIVE-CLOSURE-AND-GOVERNANCE-HARDENING",
            notes="Never infer dynamic training trajectory from a single static initialization step."
        ),
        Assumption(
            assumption_id="ASSUMP-008",
            statement="Opposing directional gradient alignment between rare and common classes is an intrinsic property of the ResNet18-UNet architecture.",
            status=AssumptionState.CONTRADICTED,
            scope=ScopeLevel.PROJECT,
            verification_method="Empirical negative cosine was observed only for Step-0 OPS-02; generalization across architectures or domains is unproven.",
            associated_rules=["GOV-RULE-131"],
            verified_in_task="DIAG05-TIER1-CORRECTIVE-CLOSURE-AND-GOVERNANCE-HARDENING",
            notes="Over-broad 'intrinsic structural characteristic' wording removed."
        ),
        Assumption(
            assumption_id="ASSUMP-009",
            statement="The HOLDOUT partition (data/ops02/tiles/holdout) is completely inaccessible and quarantined from all active agent workflows.",
            status=AssumptionState.VERIFIED,
            scope=ScopeLevel.GLOBAL,
            verification_method="Enforced via BLOCK-001-HOLDOUT and test_part_iii_firewall.py.",
            associated_rules=["BLOCK-001-HOLDOUT"],
            verified_in_task="DIAG05-TIER1-CORRECTIVE-CLOSURE-AND-GOVERNANCE-HARDENING",
            notes="Zero reads or touches permitted."
        ),
        Assumption(
            assumption_id="ASSUMP-010",
            statement="Part III external benchmark rasters and prediction payloads are strictly firewalled from development and diagnostics.",
            status=AssumptionState.VERIFIED,
            scope=ScopeLevel.GLOBAL,
            verification_method="Enforced via BLOCK-002-PART_III and test_part_iii_firewall.py.",
            associated_rules=["BLOCK-002-PART_III"],
            verified_in_task="DIAG05-TIER1-CORRECTIVE-CLOSURE-AND-GOVERNANCE-HARDENING",
            notes="Firewall assertions pass 100%."
        ),
        Assumption(
            assumption_id="ASSUMP-011",
            statement="The model state loaded at data/ops02/initial_model_state_canonical.pt matches authoritative SHA256 67181C4CD420DEABA4129AB67AA34D617C1C581ACB3A1A7A9DE8BEAF2F1544D.",
            status=AssumptionState.VERIFIED,
            scope=ScopeLevel.PROJECT,
            verification_method="Verified bit-for-bit via test_diag05_tier1_artifacts_integrity_and_hashes.",
            associated_rules=["GOV-RULE-123"],
            verified_in_task="DIAG05-TIER1-CORRECTIVE-CLOSURE-AND-GOVERNANCE-HARDENING",
            notes="Guarantees exact initialization state reproducibility."
        ),
        Assumption(
            assumption_id="ASSUMP-012",
            statement="Analysis-only and forensic tasks permit strictly zero PyTorch backward passes, optimizer steps, or model training.",
            status=AssumptionState.VERIFIED,
            scope=ScopeLevel.GLOBAL,
            verification_method="Enforced via BLOCK-006-UNAUTHORIZED_TRAINING and telemetry authorization checks.",
            associated_rules=["BLOCK-006-UNAUTHORIZED_TRAINING"],
            verified_in_task="DIAG05-TIER1-CORRECTIVE-CLOSURE-AND-GOVERNANCE-HARDENING",
            notes="Counters assert 0 backward passes, 0 optimizer steps, 0 GPU seconds."
        ),
    ]
    return {a.assumption_id: a for a in assumptions}
