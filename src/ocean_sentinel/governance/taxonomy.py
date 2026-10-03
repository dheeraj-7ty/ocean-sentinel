"""Controlled taxonomies for Ocean Sentinel Failure Classes, Principles, and Scope."""

from typing import Dict, List
from ocean_sentinel.governance.models import FailureClass, Principle, ScopeLevel, SeverityLevel


def get_default_failure_classes() -> Dict[str, FailureClass]:
    """Returns the controlled taxonomy of 28 Ocean Sentinel failure classes."""
    classes = [
        FailureClass(
            class_id="DATA-INTEGRITY",
            name="Data Integrity Failure",
            description="Corrupted, truncated, misaligned, or missing rasters, masks, manifests, or labels.",
            typical_severity=SeverityLevel.CRITICAL,
            prevention_guideline="Verify cryptographic SHA256 hashes and physical manifest invariants before reading data."
        ),
        FailureClass(
            class_id="POPULATION-CONSTRUCTION",
            name="Population Construction Defect",
            description="Evaluating sample eligibility prior to validity masking, cropping, or nodata filtering.",
            typical_severity=SeverityLevel.CRITICAL,
            prevention_guideline="GOV-RULE-129: All sample eligibility criteria must be evaluated after all validity transformations."
        ),
        FailureClass(
            class_id="OBSERVATION-UNIT-MISMATCH",
            name="Observation Unit Mismatch",
            description="Conflating tiles, patches, minibatches, or pixels with physical experimental units.",
            typical_severity=SeverityLevel.HIGH,
            prevention_guideline="Explicitly define observation unit (e.g. tile vs scene) in the registered plan and verify in data loader."
        ),
        FailureClass(
            class_id="INFERENCE-UNIT-MISMATCH",
            name="Inference Unit Mismatch",
            description="Treating non-independent sub-units (e.g. tiles from the same scene) as independent units of inference.",
            typical_severity=SeverityLevel.CRITICAL,
            prevention_guideline="Aggregate sub-unit observations to parent acquisition cluster medians before inferential testing."
        ),
        FailureClass(
            class_id="INDEPENDENCE-ASSUMPTION",
            name="False Independence Assumption",
            description="Assuming independent observations across samples sharing parent scene, geographic cluster, or acquisition pass.",
            typical_severity=SeverityLevel.CRITICAL,
            prevention_guideline="Verify clustering structure and require cluster block bootstrap or paired cluster tests."
        ),
        FailureClass(
            class_id="TAXONOMY-DRIFT",
            name="Taxonomy Drift",
            description="Modifying or confusing dense class IDs, source labels, or semantic meanings across phases.",
            typical_severity=SeverityLevel.CRITICAL,
            prevention_guideline="Enforce immutable 12-class dense taxonomy dictionary; distinguish source labels from dense indices."
        ),
        FailureClass(
            class_id="MATHEMATICAL-DEFINITION",
            name="Mathematical Definition Drift",
            description="Altering loss functions, similarity metrics, or statistical estimators from registered specification.",
            typical_severity=SeverityLevel.HIGH,
            prevention_guideline="Derive formulas directly from registered protocol and verify with unit tests against reference tensors."
        ),
        FailureClass(
            class_id="DENOMINATOR-DRIFT",
            name="Gradient or Loss Denominator Drift",
            description="Substituting subset-normalized denominators for full-batch denominators in masked gradient computations.",
            typical_severity=SeverityLevel.CRITICAL,
            prevention_guideline="Assert denominator semantics explicitly: masked loss must normalize by total valid pixels or registered weight sum."
        ),
        FailureClass(
            class_id="IMPLEMENTATION-MISMATCH",
            name="Implementation Contract Mismatch",
            description="Discrepancy between mathematical/scientific specification and actual runtime code execution.",
            typical_severity=SeverityLevel.HIGH,
            prevention_guideline="Pre-execution contract testing: verify code behavior directly against mathematical test vectors."
        ),
        FailureClass(
            class_id="MODEL-STATE-MISMATCH",
            name="Model State Mismatch",
            description="Running diagnostics in model.train() mode, causing BatchNorm buffer mutation or dropout randomness.",
            typical_severity=SeverityLevel.CRITICAL,
            prevention_guideline="Explicitly enforce model.eval() and assert running mean/var buffers remain identical before and after diagnostic."
        ),
        FailureClass(
            class_id="AUTOGRAD-SEMANTICS",
            name="Autograd Semantics Error",
            description="Graph retention, in-place tensor mutations, or incorrect backward pass accumulation.",
            typical_severity=SeverityLevel.HIGH,
            prevention_guideline="Verify autograd graph lifecycle and assert gradient zeroing between distinct observational backward passes."
        ),
        FailureClass(
            class_id="OPTIMIZATION-SEMANTICS",
            name="Optimization Semantics Error",
            description="Optimizer step, learning rate schedule, or weight decay invocation during diagnostic profiling.",
            typical_severity=SeverityLevel.CRITICAL,
            prevention_guideline="BLOCK-006: Diagnostic governance counters assert optimizer_steps == 0, parameter_updates == 0."
        ),
        FailureClass(
            class_id="STATISTICAL-PROVENANCE",
            name="Statistical Provenance Mismatch",
            description="Discrepancy between executed statistical routine and documented distribution or metadata.",
            typical_severity=SeverityLevel.CRITICAL,
            prevention_guideline="GOV-RULE-130: Explicitly bind method arguments in code and derive artifact metadata directly from the call."
        ),
        FailureClass(
            class_id="STATISTICAL-INFERENCE",
            name="Statistical Inference Defect",
            description="Applying inappropriate parametric tests, unadjusted multiple testing, or invalid null distributions.",
            typical_severity=SeverityLevel.HIGH,
            prevention_guideline="Require non-parametric rank tests (Wilcoxon) or cluster bootstrap with verified exchangeability."
        ),
        FailureClass(
            class_id="P-VALUE-OVERINTERPRETATION",
            name="P-Value Overinterpretation",
            description="Interpreting p > 0.05 as proof of zero effect or absence of difference.",
            typical_severity=SeverityLevel.HIGH,
            prevention_guideline="GOV-RULE-131: Non-significant tests report 'did not detect a statistically distinguishable difference under registered design'."
        ),
        FailureClass(
            class_id="CAUSAL-OVERCLAIM",
            name="Causal Overclaim from Observational Evidence",
            description="Using causal verbs (drives, causes, explains, bottleneck) on purely observational or descriptive data.",
            typical_severity=SeverityLevel.CRITICAL,
            prevention_guideline="BLOCK-004 / FP-016: Calibrate language to 'observed', 'associated with', or 'HYPOTHESIZED'."
        ),
        FailureClass(
            class_id="STATIC-VS-DYNAMIC-CONFLATION",
            name="Static-vs-Dynamic Conflation",
            description="Extrapolating multi-step training dynamics or optimization stability from static Step-0 evaluations.",
            typical_severity=SeverityLevel.HIGH,
            prevention_guideline="Explicitly state that Step-0 profiling characterizes initialization geometry only, not dynamic trajectory."
        ),
        FailureClass(
            class_id="ARTIFACT-INTEGRITY",
            name="Artifact Integrity & Immutability Violation",
            description="Mutating historical closed execution artifacts in place or corrupting machine JSON hashes.",
            typical_severity=SeverityLevel.CRITICAL,
            prevention_guideline="Historical machine JSON artifacts are strictly immutable; corrections must produce new versioned artifacts."
        ),
        FailureClass(
            class_id="ARTIFACT-REPORT-MISMATCH",
            name="Artifact-to-Report Inconsistency",
            description="Discrepancy between quantitative values in machine JSON and numbers cited in markdown narrative.",
            typical_severity=SeverityLevel.CRITICAL,
            prevention_guideline="GOV-RULE-100: All quantitative assertions in reports must be machine-derived directly from verified JSON."
        ),
        FailureClass(
            class_id="EXECUTION-SAFETY",
            name="Operational Execution Safety Breach",
            description="Attempting destructive git operations, GPU allocations, or unconstrained execution loops.",
            typical_severity=SeverityLevel.CRITICAL,
            prevention_guideline="Enforce fail-closed preflight checks and assert working-tree preservation."
        ),
        FailureClass(
            class_id="AUTHORIZATION",
            name="Task Authorization Scope Breach",
            description="Executing tasks, training phases, or experiments exceeding explicit user-authorized scope.",
            typical_severity=SeverityLevel.CRITICAL,
            prevention_guideline="Fail-closed task gating: Tier-2/H3 remains blocked until explicit separate authorization."
        ),
        FailureClass(
            class_id="TELEMETRY",
            name="Telemetry Inconsistency or Drift",
            description="Leaving execution_authorized=true in analysis tasks or reporting incomplete tests at task close.",
            typical_severity=SeverityLevel.CRITICAL,
            prevention_guideline="BLOCK-012: Preflight verifies telemetry run state matches task constraints before permitting completion."
        ),
        FailureClass(
            class_id="PSEUDOREPLICATION",
            name="Pixel or Sub-Tile Pseudo-Replication",
            description="Treating spatially autocorrelated pixel counts (N > 10^6) as independent degrees of freedom.",
            typical_severity=SeverityLevel.CRITICAL,
            prevention_guideline="BLOCK-009 / FP-010: Require parent acquisition cluster blocking for all inferential uncertainty estimation."
        ),
        FailureClass(
            class_id="POST-HOC-ANALYSIS",
            name="Post-Hoc Subgrouping Conflated with Registration",
            description="Presenting post-hoc subgroup discoveries as if they were preregistered confirmatory hypotheses.",
            typical_severity=SeverityLevel.HIGH,
            prevention_guideline="Explicitly label exploratory post-hoc subgroupings and require separate preregistered validation."
        ),
        FailureClass(
            class_id="REPRODUCIBILITY",
            name="Non-Deterministic or Unseeded Execution",
            description="Unseeded random generators, non-deterministic CUDA algorithms, or unversioned dependency drift.",
            typical_severity=SeverityLevel.HIGH,
            prevention_guideline="Fix random seeds, freeze environments, and assert determinism on test subsets."
        ),
        FailureClass(
            class_id="TERMINOLOGY-DRIFT",
            name="Deprecated or Inaccurate Terminology",
            description="Using forbidden synonyms (calling OF an 'oil spill', or HM a 'vessel' or 'Heavy Metal').",
            typical_severity=SeverityLevel.HIGH,
            prevention_guideline="BLOCK-008: Automated regex scan verifies nomenclature matches canonical dictionary."
        ),
        FailureClass(
            class_id="DOCUMENTATION-INTEGRITY",
            name="Documentation and Reporting Integrity",
            description="Inaccurate narrative claims, markdown transcription discrepancies, or outdated documentation.",
            typical_severity=SeverityLevel.HIGH,
            prevention_guideline="GOV-RULE-100: All quantitative assertions in reports must be machine-derived directly from verified JSON."
        ),
        FailureClass(
            class_id="GOVERNANCE",
            name="Governance Framework Defect",
            description="Preflight bypass, unverified PROVEN_STABLE claims, or weakening rules to force test passing.",
            typical_severity=SeverityLevel.CRITICAL,
            prevention_guideline="BLOCK-010 / BLOCK-011: Enforce preflight receipts and evidence-based promotion."
        ),
    ]
    return {c.class_id: c for c in classes}


def get_default_principles() -> Dict[str, Principle]:
    """Returns the core institutional principles governing Ocean Sentinel."""
    principles = [
        Principle(
            principle_id="PRIN-001",
            title="Machine Truth Governs",
            statement="Quantitative conclusions and reported values must derive directly from verified machine JSON artifacts, never manual markdown transcription or narrative assumption.",
            rationale="Eliminates narrative inflation, transcription errors, and human confirmation bias across agent generations.",
            scope=ScopeLevel.GLOBAL,
            domain="scientific_integrity"
        ),
        Principle(
            principle_id="PRIN-002",
            title="Post-Transformation Support Invariance",
            statement="Any sample support eligibility criterion involving class presence must be evaluated strictly after all preprocessing transformations that affect validity (validity masking, nodata exclusion, and cropping).",
            rationale="Raw disk masks contain invalid border coordinates that produce empty tensors and zero gradients upon masking.",
            scope=ScopeLevel.PROJECT,
            domain="data_integrity"
        ),
        Principle(
            principle_id="PRIN-003",
            title="Explicit Statistical Method Binding",
            statement="Statistical and numerical calls must explicitly pass method and distribution parameters in code, and artifact schemas must derive method metadata directly from the executed routine.",
            rationale="Prevents default parameter drift (e.g. exact vs asymptotic Wilcoxon) between runtime libraries and written documentation.",
            scope=ScopeLevel.GLOBAL,
            domain="statistics"
        ),
        Principle(
            principle_id="PRIN-004",
            title="Bounded Epistemic Status",
            statement="Observational metrics cannot be asserted as causal mechanisms without controlled intervention, and non-significant test results (p > 0.05) cannot be asserted as proof of zero effect or stability.",
            rationale="Maintains scientific rigor and prevents false confidence in unproven training dynamics or architectural invariance.",
            scope=ScopeLevel.GLOBAL,
            domain="epistemics"
        ),
        Principle(
            principle_id="PRIN-005",
            title="Parent-Cluster Inferential Independence",
            statement="Spatial autocorrelation within Sentinel-1 SAR scenes requires that the parent acquisition cluster be the independent unit of analysis for inferential statistics and uncertainty estimation.",
            rationale="Unclustered pixel evaluations artificially inflate degrees of freedom by factors of 10^6, generating spuriously small p-values.",
            scope=ScopeLevel.PROJECT,
            domain="statistics"
        ),
        Principle(
            principle_id="PRIN-006",
            title="Diagnostic Zero-Training Invariant",
            statement="Scientific diagnostic investigations permit strictly zero model training steps, zero backward passes, zero optimizer steps, and zero GPU allocations unless explicitly authorized for a static gradient protocol.",
            rationale="Protects diagnostic purity and prevents accidental model weights mutation during measurement.",
            scope=ScopeLevel.PROJECT,
            domain="operational_safety"
        ),
        Principle(
            principle_id="PRIN-007",
            title="Protected Evaluation Firewalls",
            statement="HOLDOUT and Part III evaluation partitions are strictly quarantined and firewalled from development, training, and diagnostic access.",
            rationale="Preserves uncontaminated external benchmark validity and prevents test-set leakage.",
            scope=ScopeLevel.GLOBAL,
            domain="data_governance"
        ),
        Principle(
            principle_id="PRIN-008",
            title="Canonical Taxonomy and Terminology Invariance",
            statement="The 12-class dense SAR taxonomy dictionary and official class nomenclatures are immutable across all Ocean Sentinel research tasks.",
            rationale="Prevents domain confusion (e.g. conflating Ocean Front with Oil Spill, or Anthropogenic Objects with Vessels).",
            scope=ScopeLevel.PROJECT,
            domain="taxonomy"
        ),
        Principle(
            principle_id="PRIN-009",
            title="Faithful Denominator Estimands",
            statement="Gradient, loss, and metric calculations must normalize by the literal contractual denominator defined in the registered protocol rather than convenience sub-batch normalizations.",
            rationale="Subgradient norm distortion occurs when masked losses renormalize by subset pixel counts rather than full-batch support.",
            scope=ScopeLevel.PROJECT,
            domain="autograd"
        ),
        Principle(
            principle_id="PRIN-010",
            title="Model State Purity During Diagnostics",
            statement="Static diagnostic evaluations must execute in explicit model.eval() mode with frozen BatchNorm buffers to prevent running statistic contamination.",
            rationale="Batch normalization updates during single-tile passes distort feature representations and alter evaluation metrics.",
            scope=ScopeLevel.PROJECT,
            domain="ml_models"
        ),
        Principle(
            principle_id="PRIN-011",
            title="Fail-Closed Telemetry and State Accounting",
            statement="Telemetry must faithfully record execution authorization and task phase; analysis tasks must never claim execution authorization, and completion requires verified passing gates.",
            rationale="Ensures agent execution state is transparent, deterministic, and verifiable in real time.",
            scope=ScopeLevel.GLOBAL,
            domain="governance"
        ),
        Principle(
            principle_id="PRIN-012",
            title="Evidence-Based Lifecycle Promotion",
            statement="Rules and lessons cannot be promoted to PROVEN_STABLE without verifiable, documented survival across multiple subsequent independent task executions with zero regressions.",
            rationale="Prevents premature declaration of stability and ensures institutional memory is hardened by real operational experience.",
            scope=ScopeLevel.GLOBAL,
            domain="lifecycle"
        ),
    ]
    return {p.principle_id: p for p in principles}
