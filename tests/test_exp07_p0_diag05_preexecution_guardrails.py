"""Tests for EXP-07-P0-DIAG-05: Loss Landscape & Gradient Dynamics Pre-Execution Plan Guardrails.

Validates:
1. DIAG-05 planning deliverables exist and are machine-verifiable.
2. Canonical OPS-02 dataset contract (manifest path and SHA-256 binding).
3. Exact partition counts: 132 TRAIN / 40 DEV / 40 HOLDOUT (172 dev tiles across 52 clusters).
4. HOLDOUT and Part III strictly quarantined and firewalled (0 access).
5. Governance tier partitioning: Tier 1 Static Profiling vs Tier 2 Controlled Training.
6. BLOCK-006 reconciliation and PLAN_READY_WITH_PREREQUISITES verdict.
7. Primary question and pre-registered hypotheses.
8. Four-tier evidence hierarchy with explicit causal scope boundaries.
9. Within-batch counterfactual masking design (same batch, exact class sets, dual-support policy).
10. Norm ratio and denominator policy (Log-Norm Ratio Lambda_l, tau_floor, ad-hoc epsilon prohibited).
11. Continuous cosine distribution and descriptive threshold calibration (no arbitrary proof cutoffs).
12. Separation of computational observations from statistical independence units (parent cluster K, seeds).
13. Bounded remaining uncertainty language (no claims of guaranteed explanation or exhausted bottlenecks).
14. Calibrated contingency matrix (numerical events vs universal mechanism claims).
15. Tier 2 Short-Horizon Intervention Protocol specifications (held constant vs altered components).
16. ResNet18-UNet architecture specifications and frozen AdamW optimizer parameters.
17. Primary performance metric lock (dev_mIoU_phenomena).
18. Comprehensive 23-threat failure mode analysis (A through W).
19. Compute budget hard caps (Tier 1 <= 180s, Tier 2 <= 60 min GPU).
20. Lesson registry integrity (LL-DIAG05-PLAN-001 and LL-DIAG05-PLAN-002 registered and regression-protected).
21. Execution run state telemetry validation.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PLAN_MD_PATH = REPO_ROOT / "docs" / "diag05_preexecution_audit_and_hardened_plan.md"
PLAN_JSON_PATH = REPO_ROOT / "data" / "metadata" / "diag05_preexecution_plan_v1.json"
MANIFEST_PATH = REPO_ROOT / "data" / "ops02" / "manifests" / "ops02_physical_dataset_manifest_v1.json"
LESSONS_JSON_PATH = REPO_ROOT / "data" / "metadata" / "ocean_sentinel_lessons_learned_v1.json"
RUN_STATE_PATH = REPO_ROOT / "scratch" / "diag05_preexecution_audit_run_state.json"


@pytest.fixture(scope="module")
def diag05_plan():
    assert PLAN_JSON_PATH.exists(), f"Missing plan JSON: {PLAN_JSON_PATH}"
    with open(PLAN_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def diag05_plan_md():
    assert PLAN_MD_PATH.exists(), f"Missing markdown plan: {PLAN_MD_PATH}"
    return PLAN_MD_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def lessons_db():
    assert LESSONS_JSON_PATH.exists(), f"Missing lessons DB: {LESSONS_JSON_PATH}"
    with open(LESSONS_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_diag05_plan_files_exist():
    """1. Verify required planning deliverables exist on disk."""
    assert PLAN_MD_PATH.exists(), f"Markdown plan missing: {PLAN_MD_PATH}"
    assert PLAN_JSON_PATH.exists(), f"Plan JSON missing: {PLAN_JSON_PATH}"
    assert RUN_STATE_PATH.exists(), f"Run state telemetry missing: {RUN_STATE_PATH}"


def test_diag05_canonical_ops02_contract(diag05_plan):
    """2. Verify canonical OPS-02 dataset identity and manifest binding."""
    dc = diag05_plan["data_contract"]
    assert dc["dataset_id"] == "OPS-02"
    assert dc["freeze_spec"] == "OPS02_v1.0.1_FROZEN"
    assert dc["manifest_path"] == "data/ops02/manifests/ops02_physical_dataset_manifest_v1.json"
    
    expected_sha = "F5480EA2E26AF8D963EDE40CA658138CDCD6157CD79438E9C8673AD0C1DD8102"
    assert dc["manifest_sha256"] == expected_sha

    manifest_bytes = MANIFEST_PATH.read_bytes()
    computed_sha = hashlib.sha256(manifest_bytes).hexdigest().upper()
    assert computed_sha == expected_sha


def test_diag05_exact_partition_counts(diag05_plan):
    """3. Verify 132 TRAIN / 40 DEV / 40 HOLDOUT counts and 52 dev clusters."""
    dc = diag05_plan["data_contract"]
    assert dc["train_tile_count"] == 132
    assert dc["dev_tile_count"] == 40
    assert dc["holdout_tile_count"] == 40
    assert dc["development_tile_count"] == 172
    assert dc["development_cluster_count"] == 52

    sc = dc["sample_counts"]
    assert sc["train_tiles"] == 132
    assert sc["train_parent_clusters"] == 40
    assert sc["dev_tiles"] == 40
    assert sc["dev_parent_clusters"] == 12
    assert sc["holdout_tiles"] == 40
    assert sc["holdout_parent_clusters"] == 12
    assert sc["development_tiles_accessible"] == 172
    assert sc["development_parent_clusters"] == 52


def test_diag05_holdout_and_part_iii_firewall(diag05_plan):
    """4. Verify HOLDOUT and Part III are quarantined with 0 access."""
    dc = diag05_plan["data_contract"]
    assert "HOLDOUT" in dc["forbidden_partitions"]
    assert "PART_III" in dc["forbidden_partitions"]
    assert "TRAIN" in dc["authorized_partitions"]
    assert "DEV" in dc["authorized_partitions"]

    sd = diag05_plan["statistical_design"]
    assert sd["zero_access_assertions"]["holdout_access"] == 0
    assert sd["zero_access_assertions"]["part_iii_access"] == 0
    assert sd["current_governance_counters"]["holdout_access"] == 0
    assert sd["current_governance_counters"]["part_iii_access"] == 0


def test_diag05_governance_tier_partitioning(diag05_plan):
    """5. Verify two-tier governance architecture and protocol amendment prerequisite."""
    gov = diag05_plan["governance_and_protocol_reconciliation"]
    assert gov["governance_conflict"]["conflicting_rule"] == "BLOCK-006-UNAUTHORIZED_TRAINING"
    
    tiers = gov["two_tier_design"]
    assert "tier_1_static_profiling" in tiers
    assert "tier_2_controlled_training" in tiers
    
    t1 = tiers["tier_1_static_profiling"]
    assert t1["max_backward_passes"] == 120
    assert t1["max_optimizer_steps"] == 0
    assert t1["max_parameter_updates"] == 0
    assert "eval" in t1["model_mode"]
    
    t2 = tiers["tier_2_controlled_training"]
    assert t2["number_of_arms"] == 2
    assert t2["epochs_per_run"] == 5
    assert t2["max_gpu_minutes"] <= 60.0
    assert t2["protocol_name"] == "SHORT_HORIZON_INTERVENTION_PROTOCOL"


def test_diag05_readiness_verdict_and_non_execution(diag05_plan):
    """6. Verify verdict is PLAN_READY_WITH_PREREQUISITES and zero scientific execution occurred."""
    pm = diag05_plan["plan_metadata"]
    assert pm["readiness_verdict"] == "PLAN_READY_WITH_PREREQUISITES"
    assert pm["execution_authorization"] == "NOT_GRANTED"
    assert pm["investigation_id"] == "DIAG-05-LOSS-LANDSCAPE-GRADIENT-DYNAMICS"

    counters = diag05_plan["statistical_design"]["current_governance_counters"]
    assert counters["training_steps"] == 0
    assert counters["backward_passes"] == 0
    assert counters["optimizer_steps"] == 0
    assert counters["scheduler_steps"] == 0
    assert counters["parameter_updates"] == 0
    assert counters["gpu_seconds"] == 0.0
    assert counters["diag05_execution"] == 0


def test_diag05_primary_question_and_hypotheses(diag05_plan):
    """7. Verify primary scientific question and within-batch hypotheses."""
    spec = diag05_plan["scientific_specification"]
    assert "within-batch cross-class gradient direction interference" in spec["primary_question"]
    assert "canonical inverse-frequency" in spec["primary_question"]
    assert "uniform" in spec["primary_question"]

    hyps = spec["investigation_hypotheses"]
    assert len(hyps) == 3
    hyp_ids = [h["hypothesis_id"] for h in hyps]
    assert "HYP-01-GRADIENT_NORM_VOLATILITY" in hyp_ids
    assert "HYP-02-WITHIN_BATCH_GRADIENT_INTERFERENCE" in hyp_ids
    assert "HYP-03-UNIFORM_WEIGHT_GRADIENT_ATTENUATION" in hyp_ids


def test_diag05_causal_scope_boundaries(diag05_plan, diag05_plan_md):
    """8. Verify three-tier causal scope boundaries and full-recovery prohibition."""
    ev = diag05_plan["scientific_specification"]["evidence_levels"]
    assert "OBSERVED" in ev
    assert "SUPPORTED" in ev
    assert "PLAUSIBLE" in ev
    assert "CAUSAL_SHORT_HORIZON_INTERVENTION" in ev
    assert "FULL_CANONICAL_TRAINING_RECOVERY" in ev
    assert "PROHIBITED" in ev["FULL_CANONICAL_TRAINING_RECOVERY"]

    assert "CAUSAL_SHORT_HORIZON" in diag05_plan_md
    assert "STRICTLY PROHIBITED TO CLAIM FROM DIAG-05" in diag05_plan_md


def test_diag05_within_batch_counterfactual_masking(diag05_plan):
    """9. Verify within-batch counterfactual masking specifications and canonical class sets."""
    wb = diag05_plan["within_batch_counterfactual_masking"]
    assert "exact same physical input tensor" in wb["methodological_principle"]
    
    rare = wb["rare_class_sets"]
    assert "primary_core" in rare
    assert any("OF (5" in c for c in rare["primary_core"])
    assert any("RF (7" in c for c in rare["primary_core"])
    assert any("HM (11" in c for c in rare["primary_core"])
    assert "extended" in rare
    assert any("BS (2" in c for c in rare["extended"])

    dom = wb["dominant_class_sets"]
    assert "common_with_background" in dom
    assert any("BG (0" in c for c in dom["common_with_background"])
    assert any("MCC (4" in c for c in dom["common_with_background"])
    assert any("IWs (10" in c for c in dom["common_with_background"])
    assert "common_phenomena_only" in dom

    assert wb["minimum_pixel_support"]["rare_mask_min_pixels"] == 16
    assert wb["minimum_pixel_support"]["common_mask_min_pixels"] == 64
    assert wb["dual_support_policy"]["insufficient_support_flag"] == "INSUFFICIENT_DUAL_SUPPORT"

    invariants = wb["model_state_and_bn_invariants"]
    assert invariants["model_mode"] == "eval"
    assert "30 BatchNorm2d" in invariants["batchnorm_behavior"]
    assert "identical model weights" in invariants["parameter_equality"]


def test_diag05_norm_ratio_and_denominator_policy(diag05_plan):
    """10. Verify norm ratio, log-ratio primary metric, and machine-precision floor policy."""
    nr = diag05_plan["norm_ratio_and_denominator_policy"]
    assert "Log-Norm Ratio" in nr["primary_summary_metric"]
    assert nr["denominator_floor_threshold"] == 1e-07
    assert "IEEE 754 float32 machine epsilon" in nr["floor_theoretical_justification"]
    assert nr["exact_zero_policy"]["flag"] == "DENOMINATOR_EXACT_ZERO_VANISHED"
    assert nr["near_zero_policy"]["flag"] == "DENOMINATOR_NEAR_ZERO_ILL_CONDITIONED"
    assert "prohibited" in nr["arbitrary_epsilon_prohibition"].lower()


def test_diag05_cosine_threshold_calibration(diag05_plan):
    """11. Verify continuous cosine distribution as primary evidence and descriptive bins."""
    ct = diag05_plan["cosine_threshold_calibration"]
    assert "Continuous empirical distribution" in ct["primary_evidence"]
    assert "descriptive only" in ct["interpretation_boundary"].lower()
    assert "does NOT prove harmful training dynamics" in ct["interpretation_boundary"]

    cats = ct["descriptive_categories"]
    assert "strong_negative_alignment" in cats
    assert "moderate_negative_alignment" in cats
    assert "orthogonal_unaligned" in cats


def test_diag05_sample_independence_distinction(diag05_plan):
    """12. Verify separation of computational observations from statistical independence units."""
    sd = diag05_plan["statistical_design"]
    assert "Parent acquisition" in sd["unit_of_independence"]
    assert "computational observations" in sd["computational_observations_distinction"].lower()
    assert sd["replication_seeds"] == [42, 101, 202]


def test_diag05_remaining_uncertainty_bounded_language(diag05_plan_md):
    """13. Verify bounded language on remaining uncertainty (Item 6)."""
    assert "narrowed and tested several structural hypotheses" in diag05_plan_md
    assert "did not exhaust all possible explanations of low validation performance" in diag05_plan_md
    assert "guaranteed to explain the performance deficit" in diag05_plan_md


def test_diag05_calibrated_contingency_matrix(diag05_plan):
    """14. Verify calibrated interpretations in contingency matrix (Item 7)."""
    cm = diag05_plan["contingency_matrix_summary"]
    rules = cm["calibrated_interpretation_rules"]
    assert "Observed numerical event" in rules["gradient_explosion"]
    assert "does NOT prove universal instability mechanism" in rules["gradient_explosion"]
    assert "does NOT prove destructive cancellation without interventional ablation" in rules["negative_alignment"]


def test_diag05_tier2_short_horizon_protocol(diag05_plan):
    """15. Verify Tier 2 short-horizon intervention protocol parameters and canonical batch geometry."""
    t2 = diag05_plan["governance_and_protocol_reconciliation"]["two_tier_design"]["tier_2_controlled_training"]
    assert t2["protocol_name"] == "SHORT_HORIZON_INTERVENTION_PROTOCOL"
    assert t2["batch_geometry"]["physical_batch_size"] == 8
    assert t2["batch_geometry"]["gradient_accumulation_steps"] == 2
    assert t2["batch_geometry"]["effective_optimizer_batch_size"] == 16
    assert t2["batch_geometry"]["batchnorm_statistical_batch_size"] == 8
    
    step_math = t2["step_arithmetic"]
    assert step_math["batches_per_epoch"] == 17
    assert step_math["optimizer_steps_per_epoch"] == 9
    assert step_math["optimizer_steps_per_run"] == 45
    assert step_math["total_optimizer_steps_6_runs"] == 270
    assert step_math["total_physical_batches_6_runs"] == 510

    assert any("AdamW" in c for c in t2["deliberately_held_constant"])
    assert any("Candidate F" in c for c in t2["deliberately_held_constant"])
    assert any("Scheduler disabled" in c for c in t2["intentionally_altered_for_isolation"])
    assert any("5 epochs" in c for c in t2["intentionally_altered_for_isolation"])
    assert "CAUSAL_SHORT_HORIZON_INTERVENTION" in t2["causal_scope"]


def test_diag05_architecture_and_layer_targets(diag05_plan):
    """16. Verify ResNet18-UNet parameters and pre-registered canonical layer targets."""
    arch = diag05_plan["architecture_contract"]
    assert arch["model_name"] == "ResNet18-UNet"
    assert arch["total_trainable_parameters"] == 14310860
    assert arch["input_contract"] == "[B, 1, 256, 256] float32"
    assert arch["output_contract"] == "[B, 12, 256, 256] float32 logits"

    targets = arch["pre_registered_layer_targets"]
    assert len(targets) == 10
    assert "conv1" in targets
    assert "layer1.0.conv1" in targets
    assert "layer4.0.conv1" in targets
    assert "dec4.conv.conv.0" in targets
    assert "dec1.conv.conv.0" in targets
    assert "head" in targets
    # Ensure no fictitious 'up4..up1' modules remain
    assert not any("up" in t for t in targets)


def test_diag05_canonical_optimizer_contract(diag05_plan):
    """17. Verify canonical AdamW training parameters are specified and contrasted."""
    opt = diag05_plan["architecture_contract"]["canonical_training_optimizer"]
    assert opt["type"] == "AdamW"
    assert opt["base_lr"] == 0.0005
    assert opt["betas"] == [0.9, 0.999]
    assert opt["weight_decay"] == 0.01
    assert opt["gradient_clipping"] == 1.0


def test_diag05_performance_metric_contract(diag05_plan):
    """18. Verify dev_mIoU_phenomena is locked as primary evaluation metric."""
    sd = diag05_plan["statistical_design"]
    assert sd["primary_metric"] == "dev_mIoU_phenomena"


def test_diag05_failure_mode_coverage(diag05_plan):
    """19. Verify all 23 failure mode threats (A through W) are documented."""
    fm = diag05_plan["failure_mode_threat_model"]
    assert fm["audited_threat_count"] == 23
    assert len(fm["threat_identifiers"]) == 23
    assert "A_DATASET_LEAKAGE" in fm["threat_identifiers"]
    assert "D_HOLDOUT_CONTAMINATION" in fm["threat_identifiers"]
    assert "F_PARENT_PSEUDOREPLICATION" in fm["threat_identifiers"]
    assert "T_CAUSAL_OVERCLAIMING" in fm["threat_identifiers"]
    assert "W_RUNAWAY_COMPUTE" in fm["threat_identifiers"]


def test_diag05_lesson_registry_integrity(lessons_db):
    """20. Verify LL-DIAG05-PLAN-001 through LL-DIAG05-PLAN-016 are registered and regression-protected."""
    lessons = lessons_db["lessons"]
    l_map = {lsn["lesson_id"]: lsn for lsn in lessons}
    
    expected_lessons = [
        "LL-DIAG05-PLAN-001",
        "LL-DIAG05-PLAN-002",
        "LL-DIAG05-PLAN-003",
        "LL-DIAG05-PLAN-004",
        "LL-DIAG05-PLAN-005",
        "LL-DIAG05-PLAN-006",
        "LL-DIAG05-PLAN-007",
        "LL-DIAG05-PLAN-008",
        "LL-DIAG05-PLAN-009",
        "LL-DIAG05-PLAN-010",
        "LL-DIAG05-PLAN-011",
        "LL-DIAG05-PLAN-012",
        "LL-DIAG05-PLAN-013",
        "LL-DIAG05-PLAN-014",
        "LL-DIAG05-PLAN-015",
        "LL-DIAG05-PLAN-016",
        "LL-DIAG05-PLAN-017",
        "LL-DIAG05-PLAN-018",
        "LL-DIAG05-PLAN-019",
        "LL-DIAG05-PLAN-020",
        "LL-DIAG05-PLAN-021",
        "LL-DIAG05-PLAN-022",
        "LL-DIAG05-PLAN-023",
        "LL-DIAG05-PLAN-024",
        "LL-DIAG05-PLAN-025",
    ]
    for l_id in expected_lessons:
        assert l_id in l_map, f"{l_id} not found in lessons DB"
        l = l_map[l_id]
        assert l["status"] == "REGRESSION_PROTECTED"
        assert "DIAG-05" in l["affected_diagnostics"]


def test_diag05_taxonomy_integrity_and_forbidden_stale_aliases(diag05_plan, diag05_plan_md):
    """21. Verify canonical 12-class taxonomy and absence of corrupted/stale class aliases."""
    raw_json = json.dumps(diag05_plan)

    forbidden_stale_tokens = [
        "OF (1)",
        "RF (8)",
        "HM (10)",
        "SI (3)",
        "WB (4)",
        "OW (5)",
        "Oil Film",
    ]
    for token in forbidden_stale_tokens:
        assert token not in raw_json, f"Forbidden stale token found in plan JSON: {token}"
        assert token not in diag05_plan_md, f"Forbidden stale token found in plan markdown: {token}"

    mask_spec = diag05_plan["within_batch_counterfactual_masking"]
    primary_rare = mask_spec["rare_class_sets"]["primary_core"]
    assert "OF (5, Oceanic Front)" in primary_rare
    assert "RF (7, Rain Footprint)" in primary_rare
    assert "HM (11, Human-Made Objects)" in primary_rare

    common_phenomena = mask_spec["dominant_class_sets"]["common_phenomena_only"]
    assert "MCC (4, Mesoscale Cellular Convection)" in common_phenomena
    assert "IWs (10, Internal Waves)" in common_phenomena

    # Authoritative primary 3-way partition
    if "primary_authoritative_grouping" in mask_spec:
        pag = mask_spec["primary_authoritative_grouping"]
        assert pag["rare_set"] == [5, 7, 11]
        assert pag["common_set"] == [1, 2, 4, 6, 8, 9, 10]
        assert pag["other_set"] == [0, 3]
        assert pag["status"] == "AUTHORITATIVE_PRIMARY_ESTIMAND"
    assert "ONE and ONLY PRIMARY CONFIRMATORY ESTIMAND" in diag05_plan_md


def test_diag05_dual_population_reporting(diag05_plan, diag05_plan_md):
    """22. Verify dual-population reporting requirement to prevent ascertainment bias (LL-DIAG05-PLAN-003)."""
    dual_pop = diag05_plan["within_batch_counterfactual_masking"]["dual_population_reporting"]
    assert "population_1_co_occurrence" in dual_pop
    assert "population_2_unconditional_profile" in dual_pop

    p1 = dual_pop["population_1_co_occurrence"]
    assert p1["ascertainment_bias_acknowledged"] is True
    for req in ["total_batches_evaluated", "eligible_dual_support_batches", "excluded_batches_count", "exclusion_reasons_breakdown"]:
        assert req in p1["reporting_requirements"]

    assert "Dual-Population Reporting" in diag05_plan_md
    assert "Population 1" in diag05_plan_md
    assert "Population 2" in diag05_plan_md


def test_diag05_curvature_claim_disclaimer(diag05_plan, diag05_plan_md):
    """23. Verify explicit disclaimer that curvature/Hessians are not measured (LL-DIAG05-PLAN-004)."""
    spec = diag05_plan["scientific_specification"]
    assert "first-order gradient dynamics" in spec["curvature_scope_disclaimer"].lower()
    assert "not measure second-order" in spec["curvature_scope_disclaimer"].lower()

    assert "loss landscape & curvature scope limitation" in diag05_plan_md.lower()
    assert "hessian matrix" in diag05_plan_md.lower()


def test_diag05_forward_recomputation_invariant(diag05_plan, diag05_plan_md):
    """24. Verify deterministic forward recomputation invariant, model.eval(), and frozen BatchNorm."""
    fwd = diag05_plan["within_batch_counterfactual_masking"]["forward_recomputation_invariant"]
    assert fwd["method"] == "DETERMINISTIC_RECOMPUTATION_ON_IDENTICAL_INPUTS"
    assert "retain_graph=True is prohibited" in fwd["description"]

    assert "Deterministic Forward Recomputation Invariant" in diag05_plan_md
    assert "retain_graph=True" in diag05_plan_md
    assert "model.eval()" in diag05_plan_md
    assert "frozen running statistics" in diag05_plan_md.lower()
    assert "30 batchnorm2d layers" in diag05_plan_md.lower()


def test_diag05_canonical_loss_weight_vector_integrity(diag05_plan, diag05_plan_md):
    """25. Verify exact canonical class weight vector and prohibition of ungrounded literals (LL-DIAG05-PLAN-005)."""
    from ocean_sentinel.ml.exp07_fingerprint import CANONICAL_HISTORICAL_C16_LITERALS

    w_plan = diag05_plan["within_batch_counterfactual_masking"]["masked_loss_mathematical_definition"]["class_weights_w_canonical"]
    assert len(w_plan) == 12
    assert w_plan == CANONICAL_HISTORICAL_C16_LITERALS
    assert w_plan == [
        0.403935, 2.450546, 0.876692, 0.945945, 0.648189, 4.211476,
        0.719641, 2.956203, 1.064525, 1.882870, 0.387652, 18.243211
    ]

    # Prohibit the bogus vector [0.0894, 0.4497, ...] from appearing in plan or markdown
    raw_json = json.dumps(diag05_plan)
    assert "0.0894" not in raw_json
    assert "0.0894" not in diag05_plan_md
    assert "0.4497" not in raw_json
    assert "0.4497" not in diag05_plan_md

    assert "0.403935" in diag05_plan_md
    assert "18.243211" in diag05_plan_md


def test_diag05_float32_precision_justification(diag05_plan, diag05_plan_md):
    """26. Verify float32 machine epsilon is accurately described as unit roundoff (LL-DIAG05-PLAN-006)."""
    policy = diag05_plan["norm_ratio_and_denominator_policy"]["float32_precision_specification"]
    assert abs(policy["machine_epsilon"] - 1.1920929e-07) < 1e-12
    assert abs(policy["smallest_normal_float32"] - 1.1754944e-38) < 1e-42
    assert "relative unit roundoff" in policy["precision_interpretation"].lower()
    assert "not an absolute lower bound" in policy["precision_interpretation"].lower()
    assert "arbitrary numerical regularizer" in policy["regularizer_purpose"].lower()

    assert "relative unit roundoff" in diag05_plan_md.lower()
    assert "1.1754944" in diag05_plan_md or "1.18" in diag05_plan_md


def test_diag05_zero_mask_ineligibility_policy(diag05_plan, diag05_plan_md):
    """27. Verify absent mask support is treated as ineligibility rather than zero loss / zero gradient (LL-DIAG05-PLAN-007)."""
    policy = diag05_plan["within_batch_counterfactual_masking"]["zero_mask_policy"]
    assert policy["status"] == "INELIGIBLE_ABSENT_MASK"
    assert "strictly do NOT record" in policy["action"]

    assert "INELIGIBLE_ABSENT_MASK" in diag05_plan_md


def test_diag05_global_aggregation_distinction(diag05_plan, diag05_plan_md):
    """28. Verify target submodules are distinct from global gradient aggregation (LL-DIAG05-PLAN-008)."""
    arch = diag05_plan["architecture_and_target_modules"]
    submodules = arch["target_submodules"]
    assert len(submodules) == 10
    assert not any(sm["module_name"] == "global" for sm in submodules)

    global_agg = arch["global_gradient_aggregation"]
    assert global_agg["is_module"] is False
    assert global_agg["total_parameters"] == 14310860

    assert "RMS(g_l)" in arch["cross_layer_comparison_metric"]
    assert "Root Mean Square (RMS) gradient magnitude" in diag05_plan_md


def test_diag05_step_arithmetic_reconciliation(diag05_plan, diag05_plan_md):
    """29. Verify step arithmetic distinguishes Candidate F sampler draws from full dataset traversal (LL-DIAG05-PLAN-009)."""
    opts = diag05_plan["governance_and_protocol_reconciliation"]["two_tier_design"]["tier_2_controlled_training"]["step_arithmetic_options"]
    
    primary = opts["primary_candidate_f_sampler_schedule"]
    assert primary["draws_per_epoch"] == 72
    assert primary["batches_per_epoch"] == 9
    assert primary["partial_batches_per_epoch"] == 0
    assert primary["optimizer_steps_per_epoch"] == 5
    assert primary["optimizer_steps_per_run_5_epochs"] == 25
    assert primary["total_optimizer_steps_6_runs"] == 150
    assert primary["total_physical_batches_6_runs"] == 270

    alt = opts["alternative_full_132_tile_traversal"]
    assert alt["tiles_per_epoch"] == 132
    assert alt["batches_per_epoch"] == 17
    assert alt["partial_batches_per_epoch"] == 1
    assert alt["partial_batch_size"] == 4
    assert alt["optimizer_steps_per_epoch"] == 9
    assert alt["optimizer_steps_per_run_5_epochs"] == 45
    assert alt["total_optimizer_steps_6_runs"] == 270
    assert alt["total_physical_batches_6_runs"] == 510

    assert "candidate_f_sampler_parity_primary" in diag05_plan_md or "Candidate F Sampler Parity" in diag05_plan_md or "72 draws" in diag05_plan_md


def test_diag05_canonical_checkpoint_provenance(diag05_plan, diag05_plan_md):
    """30. Verify Tier 1 static checkpoint provenance is locked to initial_model_state_canonical.pt."""
    cps = diag05_plan["governance_and_protocol_reconciliation"]["two_tier_design"]["tier_1_static_profiling"]["checkpoints"]
    assert len(cps) == 1
    cp = cps[0]
    assert cp["checkpoint_id"] == "STEP_0_CANONICAL_INIT"
    assert cp["artifact_path"] == "data/ops02/initial_model_state_canonical.pt"
    assert cp["sha256"] == "67181C4ECD420DEABA4129AB67AA34D617C1C581ACB3A1A7A9DE8BEAF2F1544D"

    assert "initial_model_state_canonical.pt" in diag05_plan_md
    assert "67181C4ECD420DEABA4129AB67AA34D617C1C581ACB3A1A7A9DE8BEAF2F1544D" in diag05_plan_md


def test_diag05_run_state_telemetry():
    """31. Verify run state telemetry exists and confirms zero execution."""
    assert RUN_STATE_PATH.exists()
    with open(RUN_STATE_PATH, "r", encoding="utf-8") as f:
        rs = json.load(f)
    assert rs["investigation_id"] == "DIAG-05-LOSS-LANDSCAPE-GRADIENT-DYNAMICS"
    assert rs["scientific_execution"] is False
    assert rs["backward_passes"] == 0
    assert rs["optimizer_steps"] == 0
    assert rs["parameter_updates"] == 0
    assert rs["scheduler_steps"] == 0
    assert rs["training_steps"] == 0
    assert rs["gpu_seconds"] == 0.0
    assert rs["holdout_access_count"] == 0
    assert rs["part_iii_access_count"] == 0


def test_diag05_subgradient_decomposition_and_cancellation_proof(diag05_plan, diag05_plan_md):
    """32. Verify subgradient decomposition proof, partition conditions, and single-class cancellation (LL-DIAG05-PLAN-010)."""
    mld = diag05_plan["within_batch_counterfactual_masking"]["masked_loss_mathematical_definition"]
    assert "mutually exclusive and exhaustive partition" in mld["partition_condition"]
    assert "D_batch" in mld["mathematical_proof_of_subgradient_decomposition"]
    assert "g_rare + g_common + g_other = g_total" in mld["mathematical_proof_of_subgradient_decomposition"]
    
    # Estimand distinction
    ed = mld["estimand_distinction"]
    assert "masked gradient contribution under the full-batch reduction denominator" in ed["estimand_A_contribution"].lower()
    assert "isolated loss" in ed["estimand_B_isolated"].lower()
    assert "mandatory_qualification" in ed
    assert "masked gradient contribution under the full-batch reduction denominator" in ed["mandatory_qualification"].lower()
    
    # Single-class cancellation proof
    assert "cancels identically in numerator and denominator" in mld["single_class_cancellation_proof"]
    
    # Weight intervention identifiability
    wi = mld["weight_intervention_identifiability"]
    assert "w_c / bar{w}_batch" in wi["ratio_decomposition"]
    
    # Markdown plan reflection
    assert "LL-DIAG05-PLAN-010" in diag05_plan_md
    assert "masked gradient contribution under the full-batch reduction denominator" in diag05_plan_md.lower()
    assert "w_c / \\bar{w}_{\\text{batch}}" in diag05_plan_md or "w_c / bar{w}" in diag05_plan_md or "\\bar{w}" in diag05_plan_md


def test_diag05_class_grouping_and_resultant_vector_caution(diag05_plan, diag05_plan_md):
    """33. Verify rare/common/other class groupings, LWA/BG exclusion rationales, and resultant vector caveat."""
    mld = diag05_plan["within_batch_counterfactual_masking"]["masked_loss_mathematical_definition"]
    cgr = mld["class_grouping_rationale"]
    
    # Rare set: OF, RF, HM
    assert any("OF (5" in c for c in cgr["rare_set"])
    assert any("RF (7" in c for c in cgr["rare_set"])
    assert any("HM (11" in c for c in cgr["rare_set"])
    assert len(cgr["rare_set"]) == 3
    
    # Common set: AF, BS, MCC, POW, WS, Eddy, IWs
    assert len(cgr["common_set"]) == 7
    for code in ["AF", "BS", "MCC", "POW", "WS", "Eddy", "IWs"]:
        assert any(code in c for c in cgr["common_set"])
        
    # Other set: BG, LWA
    assert len(cgr["other_set"]) == 2
    assert any("BG (0" in c for c in cgr["other_set"])
    assert any("LWA (3" in c for c in cgr["other_set"])
    
    # Resultant vector warning
    assert "resultant vector" in mld["resultant_vector_warning"].lower()
    assert "internal vector cancellation" in mld["resultant_vector_warning"].lower()
    
    assert "resultant vector" in diag05_plan_md.lower()
    assert "Low Wind Area" in diag05_plan_md


def test_diag05_stage_representative_modules_and_rms_roles(diag05_plan, diag05_plan_md):
    """34. Verify target modules are stage representatives and distinguish raw L2 vs RMS roles."""
    arch = diag05_plan["architecture_and_target_modules"]
    
    # Stage representative classification
    tmr = arch["target_module_representativeness"]
    assert tmr["classification"] == "STAGE_REPRESENTATIVE_TARGETS"
    assert "depth transitions" in tmr["scope"].lower()
    
    # Raw L2 vs RMS roles
    roles = arch["raw_l2_vs_rms_roles"]
    assert "primary physical metric" in roles["raw_l2_role"].lower()
    assert "secondary normalized metric" in roles["rms_role"].lower()
    assert "cross-layer depth comparisons" in roles["rms_role"].lower()
    
    assert "Stage-Representative" in diag05_plan_md or "stage-representative" in diag05_plan_md.lower()
    assert "RMS(g_l)" in diag05_plan_md


def test_diag05_positive_low_support_and_numerical_precision_policy(diag05_plan, diag05_plan_md):
    """35. Verify positive low-support retention & flagging, exact positive logs, and zero censoring."""
    zmp = diag05_plan["within_batch_counterfactual_masking"]["zero_mask_policy"]
    assert "INELIGIBLE_ABSENT_MASK" in zmp["zero_support"]
    assert "LOW_SUPPORT_ESTIMATE" in zmp["positive_low_support"]
    assert "RETAINED" in zmp["positive_low_support"]
    
    # Exact positive logs policy
    nrd = diag05_plan["norm_ratio_and_denominator_policy"]
    assert "exact_positive_logs_policy" in nrd
    assert "directly without adding any artificial regularizer" in nrd["exact_positive_logs_policy"].lower()
    assert "CENSORED_ZERO_GRADIENT" in nrd["exact_positive_logs_policy"]
    
    assert "LOW_SUPPORT_ESTIMATE" in diag05_plan_md
    assert "CENSORED_ZERO_GRADIENT" in diag05_plan_md


def test_diag05_step0_checkpoint_scope_limitation(diag05_plan, diag05_plan_md):
    """36. Verify Step 0 initialization-only scope limitation and Candidate F step arithmetic."""
    t1 = diag05_plan["governance_and_protocol_reconciliation"]["two_tier_design"]["tier_1_static_profiling"]
    assert "checkpoint_scope_limitation" in t1
    assert "initialization (Step 0)" in t1["checkpoint_scope_limitation"]
    assert "CANNOT answer whether gradient geometry changes after adaptation" in t1["checkpoint_scope_limitation"]
    
    # Multiple comparison policy
    sd = diag05_plan["statistical_design"]
    assert "multiple_comparison_policy" in sd
    assert "descriptive empirical estimation" in sd["multiple_comparison_policy"].lower()
    
    assert "Scope Limitation" in diag05_plan_md
    assert "initialization (step 0)" in diag05_plan_md.lower()


def test_diag05_three_way_partition_programmatic_invariants(diag05_plan):
    """37. Verify programmatic invariants of the three-way partition (rare, common, other)."""
    contract = diag05_plan["within_batch_counterfactual_masking"]["three_way_partition_contract"]
    rare_set = set(contract["rare_set"])
    common_set = set(contract["common_set"])
    other_set = set(contract["other_set"])
    all_classes = set(contract["taxonomy_classes"])

    # 1. Exact mathematical taxonomy
    assert all_classes == set(range(12)), "Taxonomy must be exactly classes 0..11"
    assert contract["excluded_source_classes"] == [3, 9, 14]

    # 2. Pairwise disjointness
    assert rare_set & common_set == set(), "Rare and Common must be disjoint"
    assert rare_set & other_set == set(), "Rare and Other must be disjoint"
    assert common_set & other_set == set(), "Common and Other must be disjoint"

    # 3. Exhaustiveness
    assert rare_set | common_set | other_set == all_classes, "Union must exhaust classes 0..11"

    # 4. Programmatic batch simulation with ignored pixels (-100, 255)
    import torch
    targets = torch.tensor([
        [0, 1, 2, 3],
        [4, 5, 6, 7],
        [8, 9, 10, 11],
        [-100, 255, 0, 5]
    ])
    valid_mask = (targets >= 0) & (targets < 12)
    valid_pixels = targets[valid_mask]

    m_rare = torch.isin(targets, torch.tensor(list(rare_set))) & valid_mask
    m_common = torch.isin(targets, torch.tensor(list(common_set))) & valid_mask
    m_other = torch.isin(targets, torch.tensor(list(other_set))) & valid_mask

    # Assert mutual exclusivity for every pixel
    assert not (m_rare & m_common).any()
    assert not (m_rare & m_other).any()
    assert not (m_common & m_other).any()

    # Assert exhaustiveness for valid pixels
    assert (m_rare | m_common | m_other).equal(valid_mask)

    # Assert ignored pixels are never included
    ignored_mask = ~valid_mask
    assert not (m_rare & ignored_mask).any()
    assert not (m_common & ignored_mask).any()
    assert not (m_other & ignored_mask).any()


def test_diag05_adamw_gradient_vs_displacement_distinction(diag05_plan, diag05_plan_md):
    """38. Verify distinction between raw gradient L2 norm and AdamW parameter displacement (LL-DIAG05-PLAN-011)."""
    arch = diag05_plan["architecture_and_target_modules"]
    assert "adamw_update_distinction" in arch
    ad = arch["adamw_update_distinction"]

    assert "max_norm" in ad["raw_gradient_l2_norm"]
    assert "hat{m}_t" in ad["adamw_preconditioned_update"]
    assert "observed parameter displacement" in ad["observed_parameter_displacement"].lower()
    assert "GOV-RULE-114" in ad["governance_rule"]

    # Assert raw_l2_role does not claim raw L2 directly governs AdamW update magnitude
    role = arch["raw_l2_vs_rms_roles"]["raw_l2_role"]
    assert "does not directly govern" in role.lower()
    assert "second-moment preconditioning" in role.lower()

    # In markdown plan: ensure no unscaled SGD claim (\Delta \theta = -\eta g) is made for AdamW
    assert "does **not** directly govern adamw parameter update magnitude" in diag05_plan_md.lower()
    assert "actual observed parameter displacement" in diag05_plan_md.lower()


def test_diag05_cosine_interpretation_discipline(diag05_plan, diag05_plan_md):
    """39. Verify cosine similarity is strictly interpreted as opposing gradient direction (LL-DIAG05-PLAN-012)."""
    h2 = diag05_plan["scientific_specification"]["hypothesis_estimand_mapping"]["H2"]
    assert "opposing gradient direction" in h2["allowable_conclusion"].lower()
    assert "destructive interference" in h2["allowable_conclusion"].lower()
    assert "cannot conclude" in h2["allowable_conclusion"].lower()

    # Verify no ungrounded antagonism claims in plan description
    for h in diag05_plan["scientific_specification"]["investigation_hypotheses"]:
        if h["hypothesis_id"] == "HYP-02-WITHIN_BATCH_GRADIENT_INTERFERENCE":
            assert "opposing directions" in h["description"].lower()
            assert "antagonistic directions" not in h["description"].lower()

    assert "LL-DIAG05-PLAN-012" in diag05_plan_md
    assert "opposing gradient direction" in diag05_plan_md.lower()


def test_diag05_population_b_census_definition_and_tier1_batch_size(diag05_plan, diag05_plan_md):
    """40. Verify Population B census definition and Tier 1 B=4 batch size (LL-DIAG05-PLAN-013)."""
    dual_pop = diag05_plan["within_batch_counterfactual_masking"]["dual_population_reporting"]
    pop_b = dual_pop["population_2_unconditional_profile"]
    assert "full-dataset physical census" in pop_b["definition"].lower()
    assert "not a sample from the candidate f" in pop_b["definition"].lower()

    # Batch geometry specifications
    bg = diag05_plan["governance_and_protocol_reconciliation"]["batch_geometry_specifications"]
    pop_a_batch = bg["population_a_physical_batch_size"]
    assert pop_a_batch["batch_size"] in (1, 8)
    assert pop_a_batch["accumulation_steps"] == 1
    assert pop_a_batch["effective_batch_size"] in (1, 8)
    assert "does not reproduce the optimizer accumulation boundary" in dual_pop["population_1_co_occurrence"]["definition"].lower()

    t1_batch = bg["tier_1_physical_batch_size"]
    assert t1_batch["batch_size"] == 4
    assert t1_batch["total_physical_batches"] == 33
    assert t1_batch["partial_batches"] == 0

    t2_batch = bg["tier_2_batch_and_accumulation_semantics"]
    assert t2_batch["physical_batch_size"] == 8
    assert t2_batch["accumulation_steps"] == 2
    assert t2_batch["physical_batches_per_epoch"] == 9
    assert t2_batch["optimizer_steps_per_epoch"] == 5
    assert "step_5" in t2_batch["step_breakdown"]
    assert "8 tiles" in t2_batch["step_breakdown"]["step_5"]

    assert "Full-Dataset Physical Census" in diag05_plan_md
    assert "B_{\\text{phys}}=4" in diag05_plan_md or "B_{phys}=4" in diag05_plan_md or "B_{\\text{phys}} = 4" in diag05_plan_md


def test_diag05_h1_h2_h3_hypothesis_mapping(diag05_plan):
    """41. Verify H1/H2/H3 hypothesis estimand mapping completeness and volatility metric locks."""
    mapping = diag05_plan["scientific_specification"]["hypothesis_estimand_mapping"]
    assert set(mapping.keys()) == {"H1", "H2", "H3"}

    for h_key, h_data in mapping.items():
        assert "scientific_question" in h_data
        assert "exact_estimand" in h_data
        assert "exact_measurement" in h_data
        assert "allowable_conclusion" in h_data

    # Volatility metrics check: IQR is primary, max/median is secondary, CV is eliminated
    h1 = mapping["H1"]
    assert "IQR" in h1["exact_estimand"]
    assert "max-to-median" in h1["exact_estimand"]

    h1_hyp = [h for h in diag05_plan["scientific_specification"]["investigation_hypotheses"] if h["hypothesis_id"] == "HYP-01-GRADIENT_NORM_VOLATILITY"][0]
    dm = h1_hyp["dispersion_metrics"]
    assert "IQR" in dm["primary_robust"]
    assert "max-to-median" in dm["secondary_tail"]
    assert "CV = sigma / mu eliminated" in dm["prohibited_metric"]


def test_diag05_bitwise_vs_mathematical_identity_distinction(diag05_plan, diag05_plan_md):
    """42. Verify separation of mathematical equivalence, single-environment determinism, and bitwise identity (LL-DIAG05-PLAN-015)."""
    rc = diag05_plan["governance_and_protocol_reconciliation"]["reproducibility_contract"]
    assert "mathematical_equivalence" in rc
    assert "deterministic_repeated_evaluation" in rc
    assert "cross_platform_bitwise_identity" in rc
    assert "supported_guarantee" in rc

    assert "not guaranteed" in rc["cross_platform_bitwise_identity"].lower()
    assert "single-environment deterministic reproducibility" in rc["supported_guarantee"].lower()

    assert "LL-DIAG05-PLAN-015" in diag05_plan_md
    assert "Deterministic Single-Environment Reproducibility" in diag05_plan_md


def test_diag05_clipping_boundary_and_accumulation_semantics(diag05_plan, diag05_plan_md):
    """43. Verify gradient clipping is evaluated at optimizer accumulation boundaries, not per physical batch (LL-DIAG05-PLAN-017)."""
    cbs = diag05_plan["governance_and_protocol_reconciliation"]["clipping_boundary_semantics"]
    assert cbs["clipping_boundary"] == "OPTIMIZER_STEP_ACCUMULATION_BOUNDARY"
    assert "clip_grad_norm_" in cbs["unclipped_accumulated_norm_capture"]
    assert "strictly prohibited" in cbs["prohibition"].lower()
    assert "unaccumulated" in cbs["prohibition"].lower()

    # Markdown reflection
    assert "LL-DIAG05-PLAN-017" in diag05_plan_md
    assert "optimizer accumulation boundary" in diag05_plan_md.lower()
    assert "never on single physical minibatches" in diag05_plan_md.replace("*", "").lower()


def test_diag05_h3_small_sample_inference_discipline(diag05_plan, diag05_plan_md):
    """44. Verify H3 small-sample (n=3) inferential boundaries and prohibition of false null claims (LL-DIAG05-PLAN-018)."""
    h3 = diag05_plan["scientific_specification"]["hypothesis_estimand_mapping"]["H3"]
    conclusion = h3["allowable_conclusion"].lower()

    assert "no detectable difference was observed under the 3-seed short-horizon protocol" in conclusion
    assert "cannot rule out moderate or longer-horizon effects" in conclusion
    assert "prohibit claiming absence of effect or rejecting weighting" in conclusion

    # Paired seed structure: 3 paired seeds x 2 arms, NOT 6 independent runs
    assert "3 paired seed replications" in h3["paired_seed_structure"].lower()
    assert "prohibits claiming 6 independent runs" in h3["paired_seed_structure"].lower()

    assert "LL-DIAG05-PLAN-018" in diag05_plan_md
    assert "Small-Sample" in diag05_plan_md and "Inferential Discipline" in diag05_plan_md


def test_diag05_iqr_denominator_zero_categorical_policy(diag05_plan, diag05_plan_md):
    """45. Verify pre-registered categorical handling for zero IQR denominators without artificial epsilons (LL-DIAG05-PLAN-019)."""
    h1 = diag05_plan["scientific_specification"]["hypothesis_estimand_mapping"]["H1"]
    zdp = h1["zero_denominator_policy"]

    assert "FINITE_RATIO" in zdp
    assert "UNDEFINED_ZERO_DENOMINATOR" in zdp
    assert "BOTH_IQR_ZERO" in zdp
    assert "NONFINITE" in zdp
    assert "zero artificial epsilon regularizers" in zdp["prohibition"].lower()

    assert "LL-DIAG05-PLAN-019" in diag05_plan_md
    assert "UNDEFINED_ZERO_DENOMINATOR" in diag05_plan_md
    assert "BOTH_IQR_ZERO" in diag05_plan_md


def test_diag05_step0_cross_batch_heterogeneity_scope(diag05_plan, diag05_plan_md):
    """46. Verify H1 is defined strictly as spatial cross-batch heterogeneity at Step 0, not temporal volatility (LL-DIAG05-PLAN-020)."""
    h1 = diag05_plan["scientific_specification"]["hypothesis_estimand_mapping"]["H1"]
    assert "spatial cross-batch heterogeneity" in h1["exact_estimand"].lower()
    assert "prohibits claiming temporal training volatility" in h1["scope_boundary"].lower()

    assert "LL-DIAG05-PLAN-020" in diag05_plan_md
    assert "spatial cross-batch heterogeneity" in diag05_plan_md.lower()


def test_diag05_cosine_denominator_cancellation_and_numerator_shift(diag05_plan, diag05_plan_md):
    """47. Verify proof of denominator cancellation in cosine similarity and numerator vector reweighting (LL-DIAG05-PLAN-021)."""
    import torch
    proof = diag05_plan["within_batch_counterfactual_masking"]["masked_loss_mathematical_definition"]["cosine_denominator_cancellation_proof"]
    assert "cancels identically" in proof["mathematical_proof"].lower()
    assert "numerator composition" in proof["numerator_vector_reweighting_effect"].lower()

    # Numerical proof of invariance under positive scalar scaling
    u = torch.tensor([1.5, -2.0, 3.2], dtype=torch.float32)
    v = torch.tensor([-0.8, 1.2, -1.9], dtype=torch.float32)
    D = 42.75  # shared reduction denominator

    cos_uv = torch.dot(u, v) / (torch.norm(u) * torch.norm(v))
    cos_scaled = torch.dot(u / D, v / D) / (torch.norm(u / D) * torch.norm(v / D))
    assert abs(float(cos_uv) - float(cos_scaled)) < 1e-6, "Scalar denominator must cancel identically in cosine"

    assert "LL-DIAG05-PLAN-021" in diag05_plan_md
    assert "cancels identically in cosine" in diag05_plan_md.lower() or "cancels identically from cosine" in diag05_plan_md.lower() or "cancels identically" in diag05_plan_md.lower()


def test_diag05_paired_seed_replications_and_cluster_balanced_reporting(diag05_plan, diag05_plan_md):
    """48. Verify parent cluster-balanced reporting and 4 distinct Tier-2 endpoints."""
    sd = diag05_plan["statistical_design"]
    cbr = sd["cluster_balanced_reporting"]
    assert "Parent mission datatake acquisition cluster" in cbr["primary_independence_unit"]
    assert "cluster medians" in cbr["reporting_requirement"].lower()

    # Four distinct endpoints
    t2 = diag05_plan["governance_and_protocol_reconciliation"]["two_tier_design"]["tier_2_controlled_training"]
    fe = t2["four_endpoints"]
    assert "endpoint_1_clipping_frequency" in fe
    assert "endpoint_2_parameter_displacement" in fe
    assert "endpoint_3_training_loss_trajectory" in fe
    assert "endpoint_4_validation_miou" in fe
    assert "non_redundancy_justification" in fe

    assert "Four Distinct Tier-2 Endpoints" in diag05_plan_md


def test_diag05_accumulated_terminology_and_h3_causal_bound(diag05_plan, diag05_plan_md):
    """49. Verify accumulated terminology discipline, Population A batch geometry, and bounded H3 causal claims (LL-DIAG05-PLAN-022)."""
    mapping = diag05_plan["scientific_specification"]["hypothesis_estimand_mapping"]
    
    # H1 within-batch unclipped gradient norm (not accumulated)
    h1 = mapping["H1"]
    assert "within-batch unclipped gradient norm" in h1["exact_estimand"].lower()
    assert "accumulated" not in h1["exact_estimand"].lower()
    assert "accumulated" in h1["exact_measurement"].lower() and "reserved exclusively for tier 2" in h1["exact_measurement"].lower()

    # H2 within-physical-batch diagnostic without optimizer accumulation
    h2 = mapping["H2"]
    assert "within-batch masked gradient contributions" in h2["exact_estimand"].lower()
    assert "does not reproduce the optimizer accumulation boundary" in h2["exact_estimand"].lower()
    assert "b_phys=1" in h2["exact_estimand"].lower() or "b_phys=8" in h2["exact_estimand"].lower()

    # Population A geometry
    bg = diag05_plan["governance_and_protocol_reconciliation"]["batch_geometry_specifications"]
    pop_a = bg["population_a_physical_batch_size"]
    assert pop_a["batch_size"] in (1, 8)
    assert pop_a["accumulation_steps"] == 1
    assert pop_a["effective_batch_size"] in (1, 8)

    # H3 causal language bounded: "supports a causal effect", prohibited "causal driver of instability"
    h3 = mapping["H3"]
    h3_conclusion = h3["allowable_conclusion"].lower()
    assert "supports a causal effect of the loss-weighting intervention on short-horizon optimization behavior under this protocol" in h3_conclusion
    assert "causal driver of short-horizon optimization instability" not in h3_conclusion
    assert "endpoint-specific results must remain separately interpretable" in h3_conclusion
    assert "inferring an unmeasured mechanism merely because multiple endpoints move together is prohibited" in h3_conclusion

    # Markdown verification
    assert "LL-DIAG05-PLAN-022" in diag05_plan_md
    assert "supports a causal effect of the loss-weighting intervention" in diag05_plan_md.lower()
    assert "causal driver of short-horizon optimization instability" not in diag05_plan_md.lower()
    assert "within-batch unclipped gradient norm" in diag05_plan_md.lower()


def test_diag05_h2_cluster_independence_and_inferential_unit(diag05_plan, diag05_plan_md):
    """50. Verify cluster-level paired inference, 3-tier unit hierarchy, and multiplicity controls (LL-DIAG05-PLAN-023)."""
    sd = diag05_plan["statistical_design"]
    cbr = sd["cluster_balanced_reporting"]
    
    # Three-tier unit structure
    assert "Cluster-pure dual-supported physical tile observation" in cbr["raw_descriptive_unit"]
    assert "Parent mission datatake acquisition cluster" in cbr["primary_independence_unit"]
    assert "Paired parent-cluster median summary" in cbr["inferential_unit"]
    
    # Paired inference and unmatched cluster handling
    assert "UNMATCHED_CLUSTER_EXCLUDED" in cbr["unmatched_cluster_handling"]
    assert "paired inferential contrast" in cbr["unmatched_cluster_handling"].lower()
    
    # Multiplicity structure: global is primary confirmatory, 10 stage targets are secondary descriptive
    assert "primary confirmatory inference is restricted to the global full-network paired cluster contrast" in cbr["multiplicity_structure"].lower()
    assert "secondary descriptive diagnostics" in cbr["multiplicity_structure"].lower()
    assert "without multiplicity inflation" in cbr["multiplicity_structure"].lower()
    
    # H1 is descriptive physical census, no formal NHST
    assert "descriptive physical-census profiling" in cbr["h1_census_status"].lower()
    assert "zero formal nhst tests" in cbr["h1_census_status"].lower()
    
    # Pairing parity guarantee
    assert "identical physical inputs" in cbr["pairing_parity_guarantee"].lower()
    assert "identical initial weights theta_0" in cbr["pairing_parity_guarantee"].lower()
    
    # H2 hypothesis estimand mapping assertions
    h2 = diag05_plan["scientific_specification"]["hypothesis_estimand_mapping"]["H2"]
    h2_measurement = h2["exact_measurement"].lower()
    assert "raw descriptive unit is the cluster-pure physical observation" in h2_measurement
    assert "primary independence unit is the parent acquisition mission datatake cluster" in h2_measurement
    assert "inferential unit is the paired parent-cluster median summary" in h2_measurement
    assert "wilcoxon signed-rank test on matched cluster-level paired median differences" in h2_measurement
    assert "unmatched_cluster_excluded" in h2_measurement
    assert "secondary descriptive diagnostics without multiplicity inflation" in h2_measurement
    
    # Prohibit treating multiple batches from same cluster as independent (pseudo-replication)
    assert "pseudo-replication" in h2["allowable_conclusion"].lower()
    assert "independent parent clusters" in h2["allowable_conclusion"].lower()
    
    # Markdown verification
    assert "LL-DIAG05-PLAN-023" in diag05_plan_md
    assert "LL-DIAG05-PLAN-024" in diag05_plan_md
    assert "Three-Tier Statistical Unit Structure for H2" in diag05_plan_md
    assert "UNMATCHED_CLUSTER_EXCLUDED" in diag05_plan_md
    assert "cluster-level paired inference" in diag05_plan_md.lower()


def test_diag05_exact_inference_zero_tie_handling_and_h1_arms(diag05_plan, diag05_plan_md):
    """51. Verify H1 evaluates both arms without stale IQR/median, and H2 specifies exact zero/tie handling."""
    # 1. H1 evaluates both arms, raw IQR within each arm, and no stale IQR/median single-arm ratio
    h1 = diag05_plan["scientific_specification"]["hypothesis_estimand_mapping"]["H1"]
    h1_estimand = h1["exact_estimand"].lower()
    assert "within each arm" in h1_estimand
    assert "iqr_canonical / iqr_uniform" in h1_estimand
    
    raw_json_str = json.dumps(diag05_plan).lower()
    assert "iqr_l / median_l" not in raw_json_str
    assert "iqr_l / median_l" not in diag05_plan_md.lower()
    
    # 2. H2 zero-difference handling
    cbr = diag05_plan["statistical_design"]["cluster_balanced_reporting"]
    assert "zero_method='wilcox'" in cbr["zero_difference_policy"]
    assert "n_effective = n_paired - n_zero" in cbr["zero_difference_policy"]
    assert "never be silently dropped" in cbr["zero_difference_policy"].lower()
    
    # 3. H2 tie handling
    assert "average ranks" in cbr["tie_handling_policy"].lower()
    assert "continuity-corrected tie-adjusted" in cbr["tie_handling_policy"].lower()
    
    # 4. Small-n discipline
    assert "prohibit interpreting non-significance under small n as proof of no effect" in cbr["small_n_discipline"].lower()
    
    # 5. Markdown verification
    assert 'zero_method="wilcox"' in diag05_plan_md
    assert "NEVER silently dropped" in diag05_plan_md
    assert "continuity-corrected, tie-adjusted" in diag05_plan_md


def test_diag05_batch_cluster_identifiability_and_pure_observation_unit(diag05_plan, diag05_plan_md):
    """52. Verify batch-to-cluster identifiability and cluster-pure observation requirements (LL-DIAG05-PLAN-024)."""
    # 1. Registered lesson in plan
    assert "LL-DIAG05-PLAN-024" in diag05_plan["registered_lessons"]
    assert "LL-DIAG05-PLAN-024" in diag05_plan_md
    
    # 2. Raw descriptive unit is cluster-pure observation
    cbr = diag05_plan["statistical_design"]["cluster_balanced_reporting"]
    assert "Cluster-pure dual-supported physical tile observation" in cbr["raw_descriptive_unit"]
    assert "B_phys=1" in cbr["raw_descriptive_unit"]
    assert "LL-DIAG05-PLAN-024" in cbr["raw_descriptive_unit"]
    
    # 3. Population A definition
    h2 = diag05_plan["scientific_specification"]["hypothesis_estimand_mapping"]["H2"]
    assert "cluster-pure" in h2["exact_estimand"].lower()
    assert "LL-DIAG05-PLAN-024" in h2["exact_estimand"]
    assert "prevents multi-cluster batch mixing" in h2["exact_estimand"]
    
    # 4. Multi-cluster batch mixing prohibition
    assert "multi-cluster batch mixing is prohibited" in h2["exact_measurement"].lower()
    assert "LL-DIAG05-PLAN-024" in h2["exact_measurement"]
    
    # 5. Exact statistical test implementation parameters
    assert "zero_method='wilcox'" in cbr["zero_difference_policy"]
    assert "ZERO_DIFFERENCE_ALL_PAIRS" in cbr["zero_difference_policy"]
    assert "asymptotic" in cbr["tie_handling_policy"].lower()
    assert "DESCRIPTIVE_ONLY_LOW_POWER" in cbr["small_n_discipline"]
    
    # 6. Markdown guarantees
    assert "LL-DIAG05-PLAN-024" in diag05_plan_md
    assert "Cluster-pure physical Population-A tile observation" in diag05_plan_md
    assert "scipy.stats.wilcoxon" in diag05_plan_md
    assert "ZERO_DIFFERENCE_ALL_PAIRS" in diag05_plan_md
    assert "DESCRIPTIVE_ONLY_LOW_POWER" in diag05_plan_md


def test_diag05_tier1_compute_envelope_reconciliation_and_h2_population(diag05_plan, diag05_plan_md, lessons_db):
    """53. Verify deterministic Tier-1 compute envelope, 28-tile Population A, and absence of fake df (LL-DIAG05-PLAN-025)."""
    # 1. Lesson registration and protection
    l_map = {lsn["lesson_id"]: lsn for lsn in lessons_db["lessons"]}
    assert "LL-DIAG05-PLAN-025" in l_map
    assert l_map["LL-DIAG05-PLAN-025"]["status"] == "REGRESSION_PROTECTED"
    assert "LL-DIAG05-PLAN-025" in diag05_plan["registered_lessons"]
    assert "LL-DIAG05-PLAN-025" in diag05_plan_md

    # 2. Population A exact census and backward pass arithmetic
    mask_spec = diag05_plan["within_batch_counterfactual_masking"]
    assert "population_a_exact_census" in mask_spec
    census = mask_spec["population_a_exact_census"]
    assert census["eligible_tiles_count"] == 28
    assert census["parent_clusters_count"] == 15
    assert census["raw_observation_unit"] == "cluster_pure_physical_tile (B_phys=1)"
    assert census["backward_passes_per_tile"] == 4
    assert census["total_h2_backward_passes"] == 112
    assert census["total_h1_backward_passes"] == 66
    assert census["total_deterministic_backward_passes"] == 178
    assert census["hard_authorization_ceiling"] >= 178

    # 3. Markdown alignment
    assert "28 physical tiles" in diag05_plan_md
    assert "15 parent acquisition clusters" in diag05_plan_md
    assert "Conditional Co-Occurrence Gradient-Geometry Estimand" in diag05_plan_md
    assert "178 passes" in diag05_plan_md or "178 deterministic backward passes" in diag05_plan_md
    assert "max 200 backward passes" in diag05_plan_md

    # 4. H2 paired inference schema: prohibits misleading df / degrees_of_freedom
    assert "h2_paired_inference_schema" in mask_spec
    inf_schema = mask_spec["h2_paired_inference_schema"]
    for req_field in ["statistic", "p_value", "n_paired", "n_zero", "n_effective", "method", "zero_method"]:
        assert req_field in inf_schema["required_fields"]
    for prohibited in ["df", "degrees_of_freedom"]:
        assert prohibited in inf_schema["strictly_prohibited_fields"]

    # 5. Exact backward pass implementation rationale (safe execution without graph reuse)
    expected_rationale = (
        "Four backward passes are the registered execution implementation because "
        "the required masked gradient vectors are obtained through independent "
        "forward/backward evaluations without retained computation graphs; this "
        "avoids the memory and graph-lifetime risks of graph reuse."
    )
    assert census["backward_pass_implementation_rationale"] == expected_rationale
    assert expected_rationale in diag05_plan_md


def test_diag05_tier1_execution_contract_and_h2_denominator_semantics(diag05_plan, diag05_plan_md):
    """54. Verify Tier-1 execution contract: H1 eval mode, H2 full-observation D_batch, and exact decomposition."""
    from scripts import execute_exp07_diag05_tier1 as runner
    import torch

    # 1. Pre-execution authorization gate must fail closed
    assert runner.EXECUTION_AUTHORIZED is False
    with pytest.raises(RuntimeError, match="DIAG-05 Tier-1 execution is strictly NOT authorized"):
        runner.assert_execution_authorized()

    # 2. Compute constants alignment
    assert runner.H1_EXPECTED_BACKWARD_PASSES == 66
    assert runner.H2_EXPECTED_BACKWARD_PASSES == 112
    assert runner.TOTAL_DETERMINISTIC_PASSES == 178
    assert runner.HARD_AUTHORIZATION_CEILING == 200
    assert runner.WALLCLOCK_LIMIT_SECONDS == 180
    assert runner.POPULATION_A_TILES_COUNT == 28
    assert runner.POPULATION_A_CLUSTERS_COUNT == 15

    # 3. H1 terminology: spatial cross-batch gradient-norm heterogeneity (prohibits temporal volatility)
    pq_json = diag05_plan["scientific_specification"]["primary_question"]
    assert "Step-0 spatial cross-batch gradient-norm heterogeneity" in pq_json
    assert "gradient norm volatility" not in pq_json.lower()
    assert "Step-0 spatial cross-batch gradient-norm heterogeneity" in diag05_plan_md

    # 4. H2 mathematical decomposition and full-observation D_batch denominator invariant
    torch.manual_seed(42)
    B, C, H, W = 1, 12, 16, 16
    dummy_logits = torch.randn(B, C, H, W, requires_grad=False)
    dummy_targets = torch.randint(0, 12, (B, H, W))
    dummy_targets[:, 0, :4] = -100  # inject border ignore_index

    # Construct mutually exclusive and exhaustive class masks
    rare_mask = torch.zeros((B, H, W), dtype=torch.bool)
    for c in runner.RARE_CORE_CLASSES:
        rare_mask |= (dummy_targets == c)

    common_mask = torch.zeros((B, H, W), dtype=torch.bool)
    for c in runner.COMMON_7_CLASSES:
        common_mask |= (dummy_targets == c)

    other_mask = torch.zeros((B, H, W), dtype=torch.bool)
    for c in runner.OTHER_CLASSES:
        other_mask |= (dummy_targets == c)

    canonical_weights = torch.tensor(
        [0.403935, 2.450546, 0.876692, 0.945945, 0.648189, 4.211476,
         0.719641, 2.956203, 1.064525, 1.882870, 0.387652, 18.243211],
        dtype=torch.float32,
    )

    # Verify linear decomposition under full-observation denominator D_batch
    decomp = runner.verify_h2_loss_decomposition(
        logits=dummy_logits,
        targets=dummy_targets,
        rare_mask=rare_mask,
        common_mask=common_mask,
        other_mask=other_mask,
        class_weights=canonical_weights,
    )
    assert decomp["is_exact_decomposition"] is True
    assert decomp["absolute_difference"] < 1e-6
    assert decomp["d_batch"] > 0

    # Explicitly assert that single-mask loss divides by full D_batch, NOT by subset weight sum
    loss_rare, d_batch_rare = runner.compute_h2_masked_loss(
        dummy_logits, dummy_targets, rare_mask, canonical_weights
    )
    valid_mask = (dummy_targets != -100)
    expected_full_d_batch = canonical_weights[dummy_targets[valid_mask]].sum().item()
    subset_weight_sum = canonical_weights[dummy_targets[rare_mask & valid_mask]].sum().item()

    assert abs(d_batch_rare.item() - expected_full_d_batch) < 1e-4
    assert abs(expected_full_d_batch - subset_weight_sum) > 1.0, (
        "Full D_batch must be distinct from subset-only weight sum to verify correct denominator"
    )

    # 5. Runner integrity gates and population locks
    chk = runner.verify_checkpoint_integrity()
    assert chk["is_valid"] is True
    assert chk["sha256"] == runner.CHECKPOINT_CANONICAL_SHA256

    man = runner.verify_dataset_manifest_integrity()
    assert man["is_valid"] is True
    assert man["train_tiles_count"] == 132
    assert man["train_clusters_count"] == 40

    cen = runner.verify_h2_population_census()
    assert cen["is_census_locked"] is True
    assert cen["eligible_tiles_count"] == 28
    assert cen["eligible_clusters_count"] == 15

    env = runner.verify_compute_envelope_limits()
    assert env["is_valid"] is True
    assert env["total_deterministic_passes"] == 178
    assert env["hard_ceiling"] == 200





