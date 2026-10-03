# OCEAN SENTINEL — AUTHORITATIVE PROJECT GOVERNANCE RULES

**Artifact Version:** 2.0.0  
**Phase Established:** PHASE 8-P3-C3  
**Status:** AUTHORITATIVE & BINDING ACROSS ALL AG AGENTS  
**Total Rules:** 41  

---

## Permanent Epistemic Disclosures

The following 4 disclosures are permanent, mandatory, and must be cited in all top-level metadata and reports:
1. `HOLDOUT_PARTIALLY_USED_FOR_SELECTION`: Holdout scenes were inspected during dataset qualification; holdout is not purely blind.
2. `CONDITIONAL_ENGINEERING_RECONSTRUCTION`: Spatial alignment and partition assignments were reconstructed under engineering constraints.
3. `EMPIRICALLY_SUPPORTED_PILOT_HYPOTHESIS`: Scientific conclusions represent empirical hypotheses supported by pilot benchmarks, not definitive proofs.
4. `DATASET_GENERATION_METHOD = NOT_DIRECTLY_VERIFIED`: Upstream generation of raw SAR slices from Sentinel-1 granules was not independently executed or verified in this environment.

---

## Canonical Class Taxonomy

All semantic references must adhere strictly to `data/metadata/ops01_taxonomy_v1.json` verbatim:
- Class 0: `Background / Water` (Clean Sea)
- Class 1: `Atmospheric Front`
- Class 2: `Low Wind Area` (LWA)
- Class 3: `Internal Waves`
- Class 4: `Vegetable / Organic Slick`
- Class 5: `Artificial / Anthropogenic Objects` (**HM** — strictly verbatim; never shortened)
- Class 6: `Ocean Front` (**OF** — distinct from Vegetable/Organic Slick)
- Class 7: `Biological Slick` (**BS** — lookalike class)
- Class 14: `Mineral Oil Spill` (**OS** — strictly excluded from OPS-01; 0 admitted pixels)

---

## Governance Sections & Principles

### Section A — Core Scientific Doctrine
Scientific validity takes absolute precedence over speed, convenience, or UI cleanliness. Never promote hypothesis into fact without cryptographic or empirical proof.

### Section B — Evidence-Status Hierarchy
Every scientific claim must be classified strictly as PROVEN, STRONGLY_SUPPORTED, INFERRED, or UNKNOWN based on direct baseline evidence.

### Section C — Provenance Doctrine
Every dataset slice and parent scene must trace unbroken lineage to verified raw acquisition metadata.

### Section D — Dataset Integrity Doctrine
Physical files on disk outrank stale implementation assumptions. Zero corruption, zero invalid pixels, and zero dimension mismatches.

### Section E — Split and Leakage Doctrine
Zero parent scene or product ID leakage across TRAIN, DEV, and HOLDOUT partitions. Partition boundaries are inviolable.

### Section F — Alignment Doctrine
Spatial and geometric alignment reconstruction must be documented under conditional engineering disclosures.

### Section G — Reproducibility Doctrine
Reproducibility Level B applies strictly to deterministic verification of stored artifacts, never to unverified pipeline regeneration.

### Section H — Taxonomy Doctrine
Canonical terminology from ops01_taxonomy_v1.json is binding. HM is strictly 'Artificial / Anthropogenic Objects'.

### Section I — Geographic and Temporal Claim Doctrine
Geographic clusters and temporal ranges must not be generalized beyond verified scene metadata.

### Section J — Artifact-Versioning Doctrine
Never mutate an authoritative artifact in place. Create explicit successor versions (e.g. manifest_v4, sufficiency_v5).

### Section K — Experiment Authorization Doctrine
No experiment may execute without a frozen scientific protocol, frozen dataset manifest, and explicit operator authorization.

### Section L — Git Safety Doctrine
0 staged != clean. Complete porcelain accounting is mandatory. git clean, reset, and destructive commands are strictly prohibited.

### Section M — Telemetry Doctrine
Every autonomous phase must maintain durable run-state telemetry with active heartbeat tracking and complete command logs.

### Section N — Incident-Learning Doctrine
Every unexpected failure, broken assumption, or discrepancy must be formalized in the incident register with root cause and regression tests.

### Section O — Training Authorization Doctrine
Model training, GPU computation, and EXP-07 execution remain strictly prohibited until explicit pre-training gate approval.

---

## Authoritative Rules Catalog (Rules 001 — 040)

### GOV-RULE-001: Never evaluate a criterion by class presence; evaluate literal contractual conditions (parent diversity >= required threshold).
- **Category:** `DATASET_INTEGRITY`
- **Triggering Incident:** LWA marked sufficient with only 1 parent scene
- **Root Cause:** Evaluating class presence rather than independent parent acquisition diversity
- **Failed Assumption:** Class present in dataset implies dataset sufficiency for that class
- **Missed Guardrail:** Contractual parent diversity check per class
- **New Guardrail:** assert class_parents >= required_parents (>= 2 for all core lookalikes)
- **Regression Test:** `test_phase_8_p3_pretraining_audit_guardrails.py::TestDiversityCoverageAudit::test_lwa_minimum_parents`
- **Phase Introduced:** `PHASE_8_P2_R2_C1` | **Status:** `ACTIVE`

### GOV-RULE-002: Distinguish index span from cell count and coordinate convention in all spatial calculations.
- **Category:** `ALIGNMENT_GEOMETRY`
- **Triggering Incident:** Conflation of 2,550 vs 2,560 coordinate span
- **Root Cause:** Ambiguity between 0-indexed endpoint span (2550) vs cell count / coordinate bounds (2560)
- **Failed Assumption:** Array index span equals cell-centered spatial extent
- **Missed Guardrail:** Explicit distinction between index coordinate span and cell count
- **New Guardrail:** Explicitly assert cell count vs coordinate span conventions in geometry audits
- **Regression Test:** `test_phase_7c_alignment_guardrails.py::test_coordinate_convention_bounds`
- **Phase Introduced:** `PHASE_7C` | **Status:** `ACTIVE`

### GOV-RULE-003: Design or evaluation parameter != physical uncertainty. Physical uncertainty requires empirical ground-truth validation.
- **Category:** `ALIGNMENT_GEOMETRY`
- **Triggering Incident:** 50m design evaluation buffer described as physical registration uncertainty
- **Root Cause:** Confusing an algorithmic tolerance parameter with empirical physical measurement uncertainty
- **Failed Assumption:** Design tolerance parameter equals physical uncertainty
- **Missed Guardrail:** Epistemic separation of design parameters from measured empirical uncertainty
- **New Guardrail:** Disallow labeling algorithmic window/buffer parameters as physical registration uncertainty
- **Regression Test:** `test_phase_7c_r2_alignment_evidence_guardrails.py::test_design_parameter_not_uncertainty`
- **Phase Introduced:** `PHASE_7C_R2` | **Status:** `ACTIVE`

### GOV-RULE-004: Conditional residual under an assumed correspondence != independently validated physical registration.
- **Category:** `ALIGNMENT_GEOMETRY`
- **Triggering Incident:** 15.79m residual described as independent physical alignment error
- **Root Cause:** Confusing conditional mathematical residual under an assumed correspondence model with independent physical registration error
- **Failed Assumption:** Optimization residual under a correspondence model equals independent physical error
- **Missed Guardrail:** Conditional engineering reconstruction boundary disclosure
- **New Guardrail:** Mandatory CONDITIONAL_ENGINEERING_RECONSTRUCTION epistemic disclosure
- **Regression Test:** `test_phase_8_p1_r1_correspondence_guardrails.py::test_residual_not_independent_error`
- **Phase Introduced:** `PHASE_8_P1_R1` | **Status:** `ACTIVE`

### GOV-RULE-005: Interpolation fitting control points by construction is not independent validation.
- **Category:** `ALIGNMENT_GEOMETRY`
- **Triggering Incident:** Four-corner interpolation zero residual claimed as alignment proof
- **Root Cause:** Mathematical identity of fitting control points by construction confused with independent empirical validation
- **Failed Assumption:** Zero residual on fitted control points validates spatial accuracy across the scene
- **Missed Guardrail:** Guardrail rejecting circular verification where test points are fitting points
- **New Guardrail:** Prohibit treating control-point interpolation residual as independent spatial accuracy
- **Regression Test:** `test_phase_7c_r1_methodology_guardrails.py::test_interpolation_residual_semantics`
- **Phase Introduced:** `PHASE_7C_R1` | **Status:** `ACTIVE`

### GOV-RULE-006: Catalog declaration != physical imagery. Only materialized, hash-verified files constitute physical data.
- **Category:** `PROVENANCE_AND_EVIDENCE`
- **Triggering Incident:** 47 declared catalog labels treated as 47 physically evaluated images
- **Root Cause:** Conflating catalog metadata declarations with materialized physical imagery on disk
- **Failed Assumption:** Metadata catalog entry implies physical image availability and validation
- **Missed Guardrail:** Physical file existence and hash verification before reporting dataset size
- **New Guardrail:** Physical filesystem verification of all candidate tiles (sample_count on disk)
- **Regression Test:** `test_phase_8_p2_dataset_guardrails.py::test_materialized_sample_count`
- **Phase Introduced:** `PHASE_8_P2` | **Status:** `ACTIVE`

### GOV-RULE-007: Catalog partition != physically populated dataset.
- **Category:** `SPLIT_AND_LEAKAGE`
- **Triggering Incident:** Catalog splits treated as physical train/dev/holdout datasets
- **Root Cause:** Confusing catalog-level partition definitions with populated physical splits
- **Failed Assumption:** A split defined on paper exists in the physical domain
- **Missed Guardrail:** Physical partition membership reconciliation
- **New Guardrail:** Reconcile physical sample paths against partition assignments in split manifest
- **Regression Test:** `test_phase_8_p2_r2_c2_guardrails.py::test_physical_partition_reconciliation`
- **Phase Introduced:** `PHASE_8_P2_R2` | **Status:** `ACTIVE`

### GOV-RULE-008: Class presence != causal model failure. Co-occurrence is not proof of causality.
- **Category:** `SCIENTIFIC_METHODOLOGY`
- **Triggering Incident:** Class presence in false positives treated as causal model explanation
- **Root Cause:** Inferring causal failure mechanism from observational correlation of class presence
- **Failed Assumption:** Co-occurrence of a lookalike feature implies it caused the false positive
- **Missed Guardrail:** Separation of empirical correlation from causal attribution
- **New Guardrail:** Disallow asserting causal failure mechanisms without controlled counterfactual ablation
- **Regression Test:** `test_phase_6_semantic_reporting.py::test_no_unsupported_causal_claims`
- **Phase Introduced:** `PHASE_6` | **Status:** `ACTIVE`

### GOV-RULE-009: Protective mechanism != empirically demonstrated overlap absence. Trust requires empirical verification.
- **Category:** `PROVENANCE_AND_EVIDENCE`
- **Triggering Incident:** Firewall architecture language conflated with empirical demonstration of zero overlap
- **Root Cause:** Confusing a protective containment mechanism with an empirical measurement of overlap absence
- **Failed Assumption:** A firewall rule guarantees empirical dataset separation without hash verification
- **Missed Guardrail:** Empirical hash-level cross-dataset duplication check
- **New Guardrail:** Explicit cryptographic cross-check of image/mask hashes between datasets
- **Regression Test:** `test_part_iii_firewall.py::test_zero_byte_cross_leakage`
- **Phase Introduced:** `PHASE_5B` | **Status:** `ACTIVE`

### GOV-RULE-010: Canonical taxonomy file (ops01_taxonomy_v1.json) is the absolute semantic authority. No informal synonyms.
- **Category:** `TAXONOMY`
- **Triggering Incident:** Taxonomy terminology drift in C1 reports and tables
- **Root Cause:** Informal human-readable labels used in report tables diverging from canonical class definitions
- **Failed Assumption:** Informal names are harmless descriptive synonyms
- **Missed Guardrail:** Strict taxonomy validator comparing all report terms to ops01_taxonomy_v1.json
- **New Guardrail:** Prohibit drift terms (e.g. Organic Film, Oil Front, Marine Organisms, Rain Cell)
- **Regression Test:** `test_phase_8_p2_r2_c2_guardrails.py::test_canonical_taxonomy_no_drift`
- **Phase Introduced:** `PHASE_8_P2_R2_C2` | **Status:** `ACTIVE`

### GOV-RULE-011: OF = Ocean Front (label_id=6). BS = Biological Slicks. OS = Mineral Oil Spill and remains strictly excluded.
- **Category:** `TAXONOMY`
- **Triggering Incident:** OF incorrectly described as Class 8 / Oil Slick lookalike
- **Root Cause:** Transcribing lookalike codes without checking canonical label register
- **Failed Assumption:** OF stands for Oil Film or Class 8 lookalike
- **Missed Guardrail:** Validation of class abbreviations against canonical source_label_id and semantic role
- **New Guardrail:** Enforce OF = Ocean Front (label_id=6); BS = Biological Slicks; OS = Mineral Oil Spill (excluded)
- **Regression Test:** `test_phase_8_p3_pretraining_audit_guardrails.py::TestTaxonomyIntegrity::test_of_class_identity`
- **Phase Introduced:** `PHASE_8_P2_R2_C2` | **Status:** `ACTIVE`

### GOV-RULE-012: Exact evidence-backed geographic wording only. Never turn a set of labels into globally representative.
- **Category:** `GEOGRAPHIC_AND_TEMPORAL`
- **Triggering Incident:** Geographic labels mixed and described as globally representative
- **Root Cause:** Generalizing a multi-basin dataset to global representativeness without geographic coverage proof
- **Failed Assumption:** Samples from multiple oceans constitute a globally representative dataset
- **Missed Guardrail:** Audit of geographic basin claims against specific coordinates and marine regions
- **New Guardrail:** Enforce specific basin reporting (e.g. 5 ocean basins); prohibit global representativeness claims
- **Regression Test:** `test_phase_8_p2_r2_c2_guardrails.py::test_geographic_basin_labels`
- **Phase Introduced:** `PHASE_8_P2_R2_C2` | **Status:** `ACTIVE`

### GOV-RULE-013: Endpoint span != continuous temporal representation. Disclose actual temporal sparsity.
- **Category:** `GEOGRAPHIC_AND_TEMPORAL`
- **Triggering Incident:** Temporal span (2015-2024) treated as continuous yearly coverage
- **Root Cause:** Confusing temporal endpoint span with uniform or continuous temporal sampling
- **Failed Assumption:** A dataset with samples from 2015 and 2024 covers the intermediate decade uniformly
- **Missed Guardrail:** Year-by-year temporal distribution histogram check
- **New Guardrail:** Disclose exact acquisition date distribution; prohibit claiming continuous coverage
- **Regression Test:** `test_phase_8_p3_pretraining_audit_guardrails.py::TestDiversityCoverageAudit::test_temporal_span_disclosure`
- **Phase Introduced:** `PHASE_8_P3` | **Status:** `ACTIVE`

### GOV-RULE-014: Compare image content and lineage before calling contamination. Duplicate mask != duplicate image.
- **Category:** `DATASET_INTEGRITY`
- **Triggering Incident:** Duplicate masks interpreted as duplicate imagery / contamination
- **Root Cause:** Observing identical mask hashes across different tiles without checking image hashes or spatial lineage
- **Failed Assumption:** Identical mask implies duplicate data sample
- **Missed Guardrail:** Joint image and mask SHA256 uniqueness analysis
- **New Guardrail:** Distinguish all-zero background masks or recurring lookalike patterns from image duplication
- **Regression Test:** `test_phase_8_p3_pretraining_audit_guardrails.py::TestLeakageAndDuplicates::test_zero_image_duplicates`
- **Phase Introduced:** `PHASE_8_P2_R2_C1` | **Status:** `ACTIVE`

### GOV-RULE-015: Repository component existence != dataset compatibility. Verify contracts before assuming reuse.
- **Category:** `DATALOADER_AND_INTERFACE`
- **Triggering Incident:** Existing TrujilloTileDataset assumed to be directly usable for OPS-01
- **Root Cause:** Assuming repository codebase components generalize across different dataset contracts without inspection
- **Failed Assumption:** An existing PyTorch Dataset in the repository works for a new dataset format
- **Missed Guardrail:** Contractual inspection of input shape, bands, dtype, and read mechanics
- **New Guardrail:** Formal DataLoader contract audit before declaring dataset training-ready
- **Regression Test:** `test_phase_8_p3_pretraining_audit_guardrails.py::TestDataLoaderContract::test_ops01_loader_not_implemented`
- **Phase Introduced:** `PHASE_8_P3` | **Status:** `ACTIVE`

### GOV-RULE-016: Actual physical data characteristics outrank stale implementation assumptions.
- **Category:** `PREPROCESSING_AND_DATA`
- **Triggering Incident:** OPS-01 discovered to be 1-band 256x256 VV raw intensity, conflicting with 2-band 512x512 assumption
- **Root Cause:** Stale implementation assumptions from prior phases not updated with physical data discovery
- **Failed Assumption:** All project imagery is 2-band 512x512 normalized float
- **Missed Guardrail:** Direct physical tensor profiling of materialized GeoTIFF/raster files
- **New Guardrail:** Inspect physical array shape, bands, and value domain directly from raster files
- **Regression Test:** `test_phase_8_p3_pretraining_audit_guardrails.py::TestPreprocessingAudit::test_raw_amplitude_dn_documented`
- **Phase Introduced:** `PHASE_8_P3` | **Status:** `ACTIVE`

### GOV-RULE-017: Historical test result != freshly executed result. Always run fresh verification.
- **Category:** `VERIFICATION_AND_TESTING`
- **Triggering Incident:** Historical test suite counts confused with fresh execution counts
- **Root Cause:** Transcribing previous session logs without re-executing test suites
- **Failed Assumption:** A test passed yesterday means it passes now without running it
- **Missed Guardrail:** Fresh execution timestamp and exit code capture
- **New Guardrail:** Capture live execution start/end time, exit code, and exact pass/fail counts
- **Regression Test:** `test_phase_8_p3_pretraining_audit_guardrails.py::TestReconciliationAudit`
- **Phase Introduced:** `PHASE_8_P2_R2_C2` | **Status:** `ACTIVE`

### GOV-RULE-018: 0 staged != clean. Staging, working tree, and untracked files are distinct states.
- **Category:** `GIT_SAFETY`
- **Triggering Incident:** Empty git diff --cached described as clean repository
- **Root Cause:** Checking only staged index while ignoring untracked and unstaged working-tree modifications
- **Failed Assumption:** Zero staged changes implies a clean git working tree
- **Missed Guardrail:** Full three-way git state inspection (status porcelain, diff cached, diff)
- **New Guardrail:** Always inspect git status --porcelain -uall, git diff --cached, and git diff
- **Regression Test:** `test_phase_8_p3_pretraining_audit_guardrails.py::TestGitStateSafety::test_zero_staged_changes`
- **Phase Introduced:** `PHASE_8_P2_R2_C2` | **Status:** `ACTIVE`

### GOV-RULE-019: Never modify a closed authoritative artifact in place without an explicit version transition.
- **Category:** `ARTIFACT_VERSIONING`
- **Triggering Incident:** P2-C2 authoritative artifacts mutated in place by P3
- **Root Cause:** Directly editing closed authoritative artifacts (manifest_v3, sufficiency_v4) to add disclosure fields
- **Failed Assumption:** Adding disclosure metadata in place is harmless because data samples were unchanged
- **Missed Guardrail:** Cryptographic immutability enforcement on closed authoritative artifacts
- **New Guardrail:** Successor versioning rule: closed artifacts are immutable; create v(N+1) with parent references
- **Regression Test:** `tests/test_phase_8_p3_c1_governance_guardrails.py::TestArtifactVersioningLineage`
- **Phase Introduced:** `PHASE_8_P3_C1` | **Status:** `ACTIVE`

### GOV-RULE-020: Every reproducibility level must have a precise operational definition and evidence requirement.
- **Category:** `REPRODUCIBILITY`
- **Triggering Incident:** LEVEL_B_ESTABLISHED used without formal operational definitions
- **Root Cause:** Assigning a qualitative reproducibility grade without contractual operational evidence criteria
- **Failed Assumption:** Reproducibility levels are self-explanatory intuitive grades
- **Missed Guardrail:** Formal reproducibility hierarchy specification (Levels 0, A, B, C, D)
- **New Guardrail:** Require formal operational criteria and evidence mapping for every reproducibility claim
- **Regression Test:** `tests/test_phase_8_p3_c1_governance_guardrails.py::TestReproducibilityHierarchy`
- **Phase Introduced:** `PHASE_8_P3_C1` | **Status:** `ACTIVE`

### GOV-RULE-021: Bounded investigation is mandatory. Never launch unbounded recursive searches across the repository.
- **Category:** `INVESTIGATION_BOUNDS`
- **Triggering Incident:** Unbounded recursive repository scan became stuck searching for historical hashes
- **Root Cause:** Executing unconstrained recursive filesystem crawl across thousands of files and binaries
- **Failed Assumption:** An unbounded search will quickly find historical hashes across the entire disk tree
- **Missed Guardrail:** Strict time and scope budget on forensic investigations
- **New Guardrail:** Bounded investigation rule: search only targeted authoritative locations within bounded time
- **Regression Test:** `tests/test_phase_8_p3_c1_governance_guardrails.py::TestInvestigationBounds`
- **Phase Introduced:** `PHASE_8_P3_C1` | **Status:** `ACTIVE`

### GOV-RULE-022: The correct documented discrepancy is 7E vs 7F (never 7E vs 7F (erroneous 7B character transcription prohibited)). Verify hashes directly from filesystem.
- **Category:** `PROVENANCE_AND_EVIDENCE`
- **Triggering Incident:** Part-I SHA discrepancy wording error (7E vs 7F (erroneous 7B character transcription prohibited))
- **Root Cause:** Transcribing typo from prompt/report without verifying exact hash characters
- **Failed Assumption:** Prompt narrative typo correctly described the character mismatch
- **Missed Guardrail:** Automated string assertion rejecting erroneous 7E vs 7F (erroneous 7B character transcription prohibited) wording
- **New Guardrail:** Assert absence of 7E vs 7F (erroneous 7B character transcription prohibited); assert presence of correct 7E vs 7F wording where noted
- **Regression Test:** `tests/test_phase_8_p3_c1_governance_guardrails.py::TestPartIDiscrepancyWording`
- **Phase Introduced:** `PHASE_8_P3_C1` | **Status:** `ACTIVE`

### GOV-RULE-023: Scientific protocol decisions must be frozen before implementation. Engineering decisions must not silently dictate scientific protocol.
- **Category:** `SCIENTIFIC_METHODOLOGY`
- **Triggering Incident:** Conflation of scientific protocol decisions with engineering implementation choices
- **Root Cause:** Allowing engineering implementation ease to decide scientific experimental protocol values
- **Failed Assumption:** Choosing a convenient implementation choice does not compromise scientific validity
- **Missed Guardrail:** Explicit taxonomy of decisions: SCIENTIFIC vs ENGINEERING vs BOTH
- **New Guardrail:** Separate scientific training protocol decisions from engineering choices; freeze protocol before implementation
- **Regression Test:** `tests/test_phase_8_p3_c1_governance_guardrails.py::TestDecisionSeparation`
- **Phase Introduced:** `PHASE_8_P3_C1` | **Status:** `ACTIVE`

### GOV-RULE-024: The OPS-01 DataLoader gap remains open until EXP-07 protocol is frozen. The loader must not invent protocol.
- **Category:** `DATALOADER_AND_INTERFACE`
- **Triggering Incident:** OPS-01 DataLoader contract left open and at risk of premature implementation
- **Root Cause:** Desire to quickly implement a DataLoader before scientific protocol is approved
- **Failed Assumption:** Implementing a loader early accelerates project progress
- **Missed Guardrail:** Explicit OPEN-LOADER-001 and OPEN-LOADER-CONTRACT-001 locks
- **New Guardrail:** Enforce that OPS-01 DataLoader is NOT implemented until EXP-07 protocol is formally frozen
- **Regression Test:** `tests/test_phase_8_p3_c1_governance_guardrails.py::TestDataLoaderGapStatus`
- **Phase Introduced:** `PHASE_8_P3_C1` | **Status:** `ACTIVE`

### GOV-RULE-025: Value domain (raw DN / dB / sigma0) is an open scientific decision (OPEN-PREPROC-001). Do not choose prematurely.
- **Category:** `PREPROCESSING_AND_DATA`
- **Triggering Incident:** Raw DN vs dB vs sigma0 representation at risk of premature selection
- **Root Cause:** Selecting input value domain for convenience without experimental evidence
- **Failed Assumption:** Defaulting to raw DN or dB is a trivial implementation detail
- **Missed Guardrail:** OPEN-PREPROC-001 formal open issue record
- **New Guardrail:** Document raw DN vs dB vs sigma0 trade-offs; forbid selection during pre-training audit
- **Regression Test:** `tests/test_phase_8_p3_c1_governance_guardrails.py::TestPreprocessingDecisionStatus`
- **Phase Introduced:** `PHASE_8_P3_C1` | **Status:** `ACTIVE`

### GOV-RULE-026: Training requires separate explicit authorization. Part-III remains protected. EXP-06 remains frozen.
- **Category:** `AUTHORIZATION_AND_FIREWALL`
- **Triggering Incident:** Risk of unauthorized model training or Part-III benchmark leakage
- **Root Cause:** Pressure to evaluate downstream performance before data readiness audit is closed
- **Failed Assumption:** Running quick exploratory training is harmless to governance
- **Missed Guardrail:** Zero EXP-07 artifacts, zero GPU usage, zero Part-III access enforcement
- **New Guardrail:** Assert absence of EXP-07 training runs, check GPU execution prohibition, and verify Part-III isolation
- **Regression Test:** `tests/test_phase_8_p3_c1_governance_guardrails.py::TestTrainingAndFirewallProhibitions`
- **Phase Introduced:** `PHASE_8_P3_C1` | **Status:** `ACTIVE`

### GOV-RULE-027: Never promote current-state consistency into historical-state equality. Use PROVEN only when direct before/after evidence exists.
- **Category:** `EVIDENCE_BOUNDARY`
- **Triggering Incident:** INC-P3-C2-001: Overstated pre-P3 unchanged claims without direct before/after evidence
- **Root Cause:** Conflating current filesystem hash matching with historical equality proof
- **Failed Assumption:** Current file integrity proves historical artifact identicalness
- **Missed Guardrail:** Evidence boundary validator distinguishing current verification from historical equivalence
- **New Guardrail:** Disallow PROVEN claim unless direct pre-P3 byte comparison is demonstrated
- **Regression Test:** `test_phase_8_p3_c2_final_closure_guardrails.py::TestEvidenceBoundaryAndProvenClaims::test_proven_requires_evidence`
- **Phase Introduced:** `PHASE_8_P3_C2` | **Status:** `ACTIVE`

### GOV-RULE-028: 0 staged != clean. The full working tree state must always be reported from git status --porcelain -uall.
- **Category:** `GIT_SAFETY`
- **Triggering Incident:** INC-P3-C2-002: Git state interpretation risked calling 0 staged clean
- **Root Cause:** Evaluating only git diff --cached while ignoring untracked and modified files
- **Failed Assumption:** 0 staged changes means the working tree is clean
- **Missed Guardrail:** Complete porcelain audit parsing all four state components
- **New Guardrail:** Full 4-command git state inspection in ops01_p3_c2_git_state_audit_v1.json
- **Regression Test:** `test_phase_8_p3_c2_final_closure_guardrails.py::TestGitStateAuthoritativeAudit::test_no_false_clean_claim`
- **Phase Introduced:** `PHASE_8_P3_C2` | **Status:** `ACTIVE`

### GOV-RULE-029: Canonical class names must strictly match ops01_taxonomy_v1.json. Shortened or informal synonyms are strictly prohibited.
- **Category:** `TAXONOMY`
- **Triggering Incident:** INC-P3-C2-003: Shortened taxonomy name for HM used in governance
- **Root Cause:** Informally shortening 'Artificial / Anthropogenic Objects' to 'Anthropogenic Objects'
- **Failed Assumption:** Informal shortened names are acceptable in high-level narrative summaries
- **Missed Guardrail:** Exact string equality check against ops01_taxonomy_v1.json class_name
- **New Guardrail:** Assert HM exact class_name == 'Artificial / Anthropogenic Objects' across all governance text
- **Regression Test:** `test_phase_8_p3_c2_final_closure_guardrails.py::TestCanonicalTaxonomyExactness::test_hm_exact_canonical_name`
- **Phase Introduced:** `PHASE_8_P3_C2` | **Status:** `ACTIVE`

### GOV-RULE-030: Level B applies strictly to deterministic audit verification of stored files, never to pipeline or source reconstruction.
- **Category:** `REPRODUCIBILITY`
- **Triggering Incident:** INC-P3-C2-004: Reproducibility Level B required narrower operational semantic wording
- **Root Cause:** Broad phrasing at risk of being casually interpreted as 'OPS-01 dataset is fully reproducible'
- **Failed Assumption:** Level B label alone prevents misinterpretation by future sessions
- **Missed Guardrail:** Explicit operational statement bounding Level B to stored verification artifacts
- **New Guardrail:** Require operational statement: 'OPS-01 verification artifacts satisfy Level B deterministic verification reproducibility'
- **Regression Test:** `test_phase_8_p3_c2_final_closure_guardrails.py::TestReproducibilityLanguageExactness::test_level_b_narrow_scope`
- **Phase Introduced:** `PHASE_8_P3_C2` | **Status:** `ACTIVE`

### GOV-RULE-031: Repository hygiene must not be achieved through deletion of evidence.
- **Category:** `REPOSITORY_HYGIENE`
- **Triggering Incident:** INC-P3-C3-002: Risk of solving Source Control cleanliness through destructive deletion
- **Root Cause:** Urge to make Source Control panel clean by deleting untracked files
- **Failed Assumption:** Repository cleanliness justifies removing untracked scientific data or artifacts
- **Missed Guardrail:** Explicit prohibition of git clean or destructive file deletion during hygiene operations
- **New Guardrail:** Prohibit git clean, git reset, and file deletion; resolve hygiene purely through classification and narrow ignore rules
- **Regression Test:** `test_phase_8_p3_c3_source_control_guardrails.py::TestSafetyAndNoDeletion`
- **Phase Introduced:** `PHASE_8_P3_C3` | **Status:** `ACTIVE`

### GOV-RULE-032: Untracked != disposable.
- **Category:** `REPOSITORY_HYGIENE`
- **Triggering Incident:** INC-P3-C3-002: Risk of solving Source Control cleanliness through destructive deletion
- **Root Cause:** Conflating untracked status with disposable status
- **Failed Assumption:** Files not currently staged or committed have no scientific authority
- **Missed Guardrail:** Doctrine explicitly stating untracked files may be authoritative local artifacts
- **New Guardrail:** Treat untracked scientific data, models, and reports as protected until provenance is established
- **Regression Test:** `test_phase_8_p3_c3_source_control_guardrails.py::TestSafetyAndNoDeletion`
- **Phase Introduced:** `PHASE_8_P3_C3` | **Status:** `ACTIVE`

### GOV-RULE-033: Scientific artifact retention must be decided by provenance and authority, not file size.
- **Category:** `PROVENANCE_AND_STORAGE`
- **Triggering Incident:** INC-P3-C3-001: Source Control noise caused by large untracked generated/scientific artifact population
- **Root Cause:** Deciding file tracking solely by byte size rather than authority and provenance
- **Failed Assumption:** Large files should automatically be deleted or ignored without checking if they are frozen baselines
- **Missed Guardrail:** Explicit evaluation of artifact authority before applying retention policy
- **New Guardrail:** Evaluate whether artifact is frozen, authoritative, derived, or ephemeral before deciding tracking status
- **Regression Test:** `test_phase_8_p3_c3_source_control_guardrails.py::TestDataTrackingPolicyAdherence`
- **Phase Introduced:** `PHASE_8_P3_C3` | **Status:** `ACTIVE`

### GOV-RULE-034: .gitignore must never hide authoritative scientific artifacts.
- **Category:** `SOURCE_CONTROL`
- **Triggering Incident:** INC-P3-C3-003: Risk of .gitignore hiding authoritative scientific artifacts
- **Root Cause:** Broad wildcard patterns in .gitignore accidentally excluding critical files
- **Failed Assumption:** Broad ignore rules are harmless if applied to top-level directories
- **Missed Guardrail:** Mandatory protected artifact allowlist audit after every .gitignore modification
- **New Guardrail:** Run git check-ignore against all protected artifacts whenever .gitignore changes
- **Regression Test:** `test_phase_8_p3_c3_source_control_guardrails.py::TestProtectedArtifactsUnignored`
- **Phase Introduced:** `PHASE_8_P3_C3` | **Status:** `ACTIVE`

### GOV-RULE-035: Tracked modifications must never be concealed by ignore rules.
- **Category:** `SOURCE_CONTROL`
- **Triggering Incident:** INC-P3-C2-002: Git state interpretation risked repeating '0 staged = clean' error
- **Root Cause:** Attempting to use .gitignore to conceal existing tracked modifications
- **Failed Assumption:** Git ignore rules can or should suppress modifications to tracked files
- **Missed Guardrail:** Explicit confirmation that tracked modifications remain visible and documented
- **New Guardrail:** Require git diff --name-status verification that tracked modifications are not obscured
- **Regression Test:** `test_phase_8_p3_c3_source_control_guardrails.py::TestTrackedModificationsRemainVisible`
- **Phase Introduced:** `PHASE_8_P3_C3` | **Status:** `ACTIVE`

### GOV-RULE-036: Source Control panel cleanliness != repository scientific correctness.
- **Category:** `OPERATIONAL_DOCTRINE`
- **Triggering Incident:** INC-P3-C3-001: Source Control noise caused by large untracked generated/scientific artifact population
- **Root Cause:** Prioritizing aesthetic UI cleanliness ('0 changes') over truthful repository state
- **Failed Assumption:** A clean Git status panel indicates scientific correctness
- **Missed Guardrail:** Rule establishing that scientific truthfulness outranks UI aesthetics
- **New Guardrail:** Explicitly report remaining legitimate untracked files and forbid artificial clean claims
- **Regression Test:** `test_phase_8_p3_c3_source_control_guardrails.py::TestNoFalseCleanClaims`
- **Phase Introduced:** `PHASE_8_P3_C3` | **Status:** `ACTIVE`

### GOV-RULE-037: Every state-mutating task must audit and repair its own side effects before declaring COMPLETE.
- **Category:** `OPERATIONAL_DOCTRINE`
- **Triggering Incident:** INC-P3-C3-004: Need for every AG task to self-audit and self-repair its own side effects
- **Root Cause:** Completing tasks without auditing newly introduced inconsistencies or broken assertions
- **Failed Assumption:** Passing initial tests means the overall state has zero unintended side effects
- **Missed Guardrail:** Mandatory self-audit and self-healing lifecycle before declaring COMPLETE
- **New Guardrail:** Inspect changes, detect introduced inconsistencies, repair them automatically, and re-verify
- **Regression Test:** `test_phase_8_p3_c3_source_control_guardrails.py::TestSelfHealingGovernance`
- **Phase Introduced:** `PHASE_8_P3_C3` | **Status:** `ACTIVE`

### GOV-RULE-038: No task may introduce a new inconsistency and then terminate without either resolving it or explicitly marking the phase BLOCKED/CONDITIONAL.
- **Category:** `OPERATIONAL_DOCTRINE`
- **Triggering Incident:** INC-P3-C3-004: Need for every AG task to self-audit and self-repair its own side effects
- **Root Cause:** Terminating with unresolved contradictions instead of blocking or repairing
- **Failed Assumption:** Leaving minor known issues for future prompts is acceptable
- **Missed Guardrail:** Hard requirement that unresolvable issues must force CONDITIONAL or BLOCKED status
- **New Guardrail:** Forbid Decision A if any known task-introduced defect remains unresolved
- **Regression Test:** `test_phase_8_p3_c3_source_control_guardrails.py::TestDecisionIntegrityAndBlocking`
- **Phase Introduced:** `PHASE_8_P3_C3` | **Status:** `ACTIVE`

### GOV-RULE-039: Repository investigations must be bounded; never perform unbounded recursive scans.
- **Category:** `INVESTIGATION_BOUNDS`
- **Triggering Incident:** INC-P3-C1-002: Historical hash recovery executed as unbounded repository scan
- **Root Cause:** Executing recursive file searches across large trees without depth or path bounds
- **Failed Assumption:** Repository-wide rglob(*) will terminate in acceptable time
- **Missed Guardrail:** Mandatory bounded scope and timeout on all directory enumerations
- **New Guardrail:** Require explicit path lists and depth limits for all forensic scans
- **Regression Test:** `test_phase_8_p3_c3_source_control_guardrails.py::TestBoundedInvestigationPolicy`
- **Phase Introduced:** `PHASE_8_P3_C3` | **Status:** `ACTIVE`

### GOV-RULE-040: Generated artifacts must have an explicit retention policy: tracked, ignored-retained, externally reproducible, or temporary.
- **Category:** `PROVENANCE_AND_STORAGE`
- **Triggering Incident:** INC-P3-C3-001: Source Control noise caused by large untracked generated/scientific artifact population
- **Root Cause:** Absence of formalized retention policy for generated experimental outputs
- **Failed Assumption:** Generated outputs can exist without an explicit category classification
- **Missed Guardrail:** Classification into Category A, B, C, or D in ops01_p3_c3_data_tracking_policy_v1.json
- **New Guardrail:** Require every generated artifact class to be registered in the project data tracking policy
- **Regression Test:** `test_phase_8_p3_c3_source_control_guardrails.py::TestDataTrackingPolicyAdherence`
- **Phase Introduced:** `PHASE_8_P3_C3` | **Status:** `ACTIVE`

### GOV-RULE-041: Every final repository-state claim must be measured AFTER all artifacts for that phase are created: INTERMEDIATE GIT STATE != FINAL GIT STATE.
- **Category:** `OPERATIONAL_DOCTRINE`
- **Triggering Incident:** INC-P3-C5-001: Conflation of historical UI snapshot with final post-phase Git state
- **Root Cause:** Phase-created artifacts alter the Git count after the phase's intermediate baseline
- **Failed Assumption:** Intermediate baseline count equals final repository state after report generation
- **Missed Guardrail:** Mandatory final Git measurement executed strictly after the final artifact creation
- **New Guardrail:** Require final Git inspection to be measured after all artifacts are created, distinguishing intermediate states from final state
- **Regression Test:** `test_phase_8_p3_c5_final_source_control_self_consistency.py::TestTimelineAndGitIntegrity`
- **Phase Introduced:** `PHASE_8_P3_C5` | **Status:** `ACTIVE`

### GOV-RULE-042: A phase's final Git state must be measured only after all phase artifacts are created.
- **Category:** `OPERATIONAL_DOCTRINE`
- **Triggering Incident:** INC-P3-C6-001: C5 timeline omitted phase-created telemetry artifact from final count reconciliation
- **Root Cause:** Measuring Git state before the final closure report, tests, or telemetry are written, leading to stale counts
- **Failed Assumption:** Git counts can be measured once and remain unchanged even as closure artifacts are created
- **Missed Guardrail:** Mandatory post-artifact final Git inspection order
- **New Guardrail:** Require final Git state measurement to occur strictly after all phase artifacts have been written to disk
- **Regression Test:** `test_phase_8_p3_c6_final_artifact_count_guardrails.py::TestOperationalDoctrine::test_final_git_state_after_all_artifacts`
- **Phase Introduced:** `PHASE_8_P3_C6` | **Status:** `ACTIVE`

### GOV-RULE-043: A phase-created telemetry file is itself part of the repository-state timeline if Git-visible, and must be explicitly classified if ignored.
- **Category:** `SOURCE_CONTROL`
- **Triggering Incident:** INC-P3-C6-001: C5 timeline omitted phase-created telemetry artifact from final count reconciliation
- **Root Cause:** Ambiguity over whether phase-created telemetry files under scratch/ increment Git porcelain counts
- **Failed Assumption:** Telemetry files can be created without documenting their ignore/tracking status
- **Missed Guardrail:** Explicit tracking/ignore classification of every phase-created telemetry file
- **New Guardrail:** Account for every phase-created telemetry file: if Git-visible, increment timeline; if matched by .gitignore, document as IGNORED_ARTIFACT with +0 porcelain impact
- **Regression Test:** `test_phase_8_p3_c6_final_artifact_count_guardrails.py::TestOperationalDoctrine::test_telemetry_git_visibility_accounted`
- **Phase Introduced:** `PHASE_8_P3_C6` | **Status:** `ACTIVE`

### GOV-RULE-044: A final report must never use an intermediate filesystem count as its final count.
- **Category:** `REPORTING_ACCURACY`
- **Triggering Incident:** INC-P3-C5-001 & INC-P3-C6-001: Intermediate snapshot conflated with final filesystem state
- **Root Cause:** Authoring executive summary counts using intermediate filesystem measurements rather than final porcelain output
- **Failed Assumption:** Intermediate snapshot counts represent the concluding state of a phase
- **Missed Guardrail:** Rule prohibiting executive summaries from using intermediate counts as final counts
- **New Guardrail:** Disallow intermediate counts in executive closure summaries; mandate fresh post-artifact Git verification
- **Regression Test:** `test_phase_8_p3_c6_final_artifact_count_guardrails.py::TestOperationalDoctrine::test_no_intermediate_count_used_as_final`
- **Phase Introduced:** `PHASE_8_P3_C6` | **Status:** `ACTIVE`

### GOV-RULE-045: Every state-mutating task must perform a post-artifact self-consistency check before declaring COMPLETE.
- **Category:** `OPERATIONAL_DOCTRINE`
- **Triggering Incident:** INC-P3-C5-001 & INC-P3-C6-001: Agent tasks terminating with post-artifact discrepancies
- **Root Cause:** Failing to perform a self-consistency check after creating all phase artifacts
- **Failed Assumption:** Pre-artifact verification ensures post-artifact consistency
- **Missed Guardrail:** Mandatory post-artifact self-consistency check prior to declaring COMPLETE
- **New Guardrail:** Execute a full self-consistency verification of Git porcelain, report, telemetry, and regression tests after all phase artifacts are authored
- **Regression Test:** `test_phase_8_p3_c6_final_artifact_count_guardrails.py::TestOperationalDoctrine::test_post_artifact_self_consistency`
- **Phase Introduced:** `PHASE_8_P3_C6` | **Status:** `ACTIVE`

### GOV-RULE-046: Missing local metadata does not equal impossible metadata.
- **Category:** `METADATA_RECOVERY`
- **Triggering Incident:** INC-P0-C2-001: P0-C1 declared calibration infeasible without searching remote archives
- **Root Cause:** Failure to distinguish between local artifact absence and general metadata availability
- **Failed Assumption:** If metadata is not in local folder, it cannot be recovered
- **Missed Guardrail:** Exhaustive check of remote repositories, public S3 buckets, and archive endpoints
- **New Guardrail:** Before declaring metadata permanently missing, search external archives and verify HTTP range/S3 access
- **Phase Introduced:** `EXP-07-P0-C2` | **Status:** `ACTIVE`

### GOV-RULE-047: Calibration of aggregated nonlinear measurements requires explicit error decomposition.
- **Category:** `RADIOMETRIC_CALIBRATION`
- **Triggering Incident:** INC-P0-C2-002: Conflating LUT smoothness with aggregation invariance
- **Root Cause:** Incomplete error decomposition (ignoring Jensen inequality DN^2 vs mean(DN)^2)
- **Failed Assumption:** Smooth LUT implies calibrate(mean(DN)) == mean(calibrate(DN))
- **Missed Guardrail:** Decomposition into E1 (LUT variation) and E2 (amplitude Jensen nonlinearity)
- **New Guardrail:** Separate and independently bound E1 and E2; quantify empirical error across stratified scenes
- **Phase Introduced:** `EXP-07-P0-C2` | **Status:** `ACTIVE`

### GOV-RULE-048: Supervised task performance does not automatically constitute representation learning.
- **Category:** `SCIENTIFIC_METHODOLOGY`
- **Triggering Incident:** INC-P0-C2-003: Overclaiming representation learning from supervised cross-entropy training
- **Root Cause:** Conflation of task-specific optimization with general representation extraction
- **Failed Assumption:** Supervised segmentation models inherently yield representations suitable for separate downstream tasks
- **Missed Guardrail:** Representation quality evaluation protocol (linear probing, feature extraction)
- **New Guardrail:** Do not claim representation learning without explicit evaluation; treat as testable hypothesis
- **Phase Introduced:** `EXP-07-P0-C2` | **Status:** `ACTIVE`

### GOV-RULE-049: A protocol correction must itself receive adversarial review.
- **Category:** `SECOND_ORDER_REVIEW`
- **Triggering Incident:** INC-P0-C2-001 & INC-P0-C2-002: P0-C1 red-team corrections introduced new invalid assumptions
- **Root Cause:** Accepting red-team corrections without independent second-order audit
- **Failed Assumption:** Red-team critiques are inherently free of defects
- **Missed Guardrail:** Second-order adversarial verification before plan freeze
- **New Guardrail:** All red-team corrections must undergo rigorous second-order scientific review
- **Phase Introduced:** `EXP-07-P0-C2` | **Status:** `ACTIVE`

### GOV-RULE-050: Nonlinear calibration after aggregation requires empirical validation.
- **Category:** `RADIOMETRIC_CALIBRATION`
- **Triggering Incident:** INC-P0-C3-001: Calibration nonlinearity derived theoretically required empirical validation
- **Root Cause:** Theoretical speckle formulas (CV=0.25) cannot guarantee accuracy across complex empirical scenes
- **Failed Assumption:** Theoretical derivations substitute for physical pixel measurements
- **Missed Guardrail:** Empirical comparison of calibrate-after vs calibrate-before aggregation
- **New Guardrail:** Empirically quantify approximation error against recovered raw parent pixels before plan freeze
- **Phase Introduced:** `EXP-07-P0-C3` | **Status:** `ACTIVE`

### GOV-RULE-051: LUT smoothness alone cannot establish aggregation equivalence.
- **Category:** `RADIOMETRIC_CALIBRATION`
- **Triggering Incident:** INC-P0-C3-001: P0-C1 cited LUT variation <0.01% as proof of calibration equivalence
- **Root Cause:** Overlooking that LUT smoothness governs E1, while amplitude variance governs E2
- **Failed Assumption:** Small parameter variation implies linear aggregation invariance
- **Missed Guardrail:** Mandatory evaluation of Jensen inequality ratio across blocks
- **New Guardrail:** Prohibit citing LUT spatial smoothness as justification for post-aggregation calibration equivalence
- **Phase Introduced:** `EXP-07-P0-C3` | **Status:** `ACTIVE`

### GOV-RULE-052: Theoretical speckle CV does not substitute for measured dataset CV.
- **Category:** `STATISTICAL_RIGOR`
- **Triggering Incident:** INC-P0-C3-001: Assuming CV=0.25 everywhere without empirical verification
- **Root Cause:** Applying homogeneous speckle models to heterogeneous ocean surface and anthropogenic features
- **Failed Assumption:** Natural scenes match theoretical fully developed speckle
- **Missed Guardrail:** Direct measurement of within-block CV across diverse scene strata
- **New Guardrail:** Measure and report actual within-block CV distributions (mean, median, p95, max) across strata
- **Phase Introduced:** `EXP-07-P0-C3` | **Status:** `ACTIVE`

### GOV-RULE-053: Instrument radiometric accuracy is distinct from processing approximation error.
- **Category:** `METROLOGICAL_DISCIPLINE`
- **Triggering Incident:** Conflating Sentinel-1 0.34 dB absolute calibration accuracy with 0.24 dB Jensen bias
- **Root Cause:** Using sensor error budget to excuse algorithmic processing errors
- **Failed Assumption:** An approximation error is acceptable if it is smaller than sensor uncertainty
- **Missed Guardrail:** Strict conceptual separation of sensor physics and algorithmic approximations
- **New Guardrail:** Prohibit justifying processing approximation error by appealing to sensor absolute accuracy
- **Phase Introduced:** `EXP-07-P0-C3` | **Status:** `ACTIVE`

### GOV-RULE-054: Reachable metadata does not equal verified metadata content.
- **Category:** `DATA_VERIFICATION`
- **Triggering Incident:** P0-C2 verified 27/27 XML HTTP 200 reachability but had inspected content of only 1
- **Root Cause:** Conflating network endpoint reachability with validated data integrity
- **Failed Assumption:** HTTP 200 guarantees XML schema conformity and vector validity
- **Missed Guardrail:** Content-level inspection of metadata vectors across parent scenes
- **New Guardrail:** Distinguish reachable metadata from content-verified metadata in all claims
- **Phase Introduced:** `EXP-07-P0-C3` | **Status:** `ACTIVE`

### GOV-RULE-055: Source mask is distinct from validity mask.
- **Category:** `DATA_GOVERNANCE`
- **Triggering Incident:** INC-P0-C3-002: Conflating source mask annotations with valid sensor pixels
- **Root Cause:** Conflating semantic ground-truth annotation with data acquisition valid/invalid state
- **Failed Assumption:** Source mask labels should be overwritten to represent zero padding
- **Missed Guardrail:** Decoupling semantic annotations from acquisition validity masks
- **New Guardrail:** Preserve source masks unmodified; implement decoupled validity masks for loss masking
- **Phase Introduced:** `EXP-07-P0-C3` | **Status:** `ACTIVE`

### GOV-RULE-056: Typical/central errors must not be represented as global worst-case bounds.
- **Category:** `STATISTICAL_RIGOR`
- **Triggering Incident:** INC-P0-C3-001: Misrepresenting ~5.5% median error as a global upper bound
- **Root Cause:** Conflating central tendency with distribution support in non-Gaussian, high-dynamic-range imagery
- **Failed Assumption:** Typical speckle error bounds maximum point-target error
- **Missed Guardrail:** Explicit differentiation between central error regimes and peak boundary/target errors
- **New Guardrail:** Never claim a global error bound based on median/mean; explicitly disclose localized worst-case peak errors
- **Phase Introduced:** `EXP-07-P0-C4` | **Status:** `ACTIVE`

### GOV-RULE-057: Multiclass segmentation must not inherit binary threshold semantics.
- **Category:** `EVALUATION_INTEGRITY`
- **Triggering Incident:** Preventative guardrail against reusing EXP-06 binary tau=0.22 threshold
- **Root Cause:** Blindly copying evaluation code across tasks without adjusting for target semantics
- **Failed Assumption:** Decision thresholds from binary detection apply to mutually exclusive multiclass segmentation
- **Missed Guardrail:** Automated prohibition of binary threshold parameters in multiclass evaluation contracts
- **New Guardrail:** Enforce argmax decision rules for multiclass segmentation; strictly prohibit binary threshold parameters
- **Phase Introduced:** `EXP-07-P0-C4` | **Status:** `ACTIVE`

### GOV-RULE-058: Implementation contracts must preserve epistemic status.
- **Category:** `EPISTEMIC_DISCIPLINE`
- **Triggering Incident:** Preventative guardrail against downstream agents dropping holdout and calibration caveats
- **Root Cause:** Loss of provenance context during protocol-to-code translation
- **Failed Assumption:** Implementation code does not need to carry forward epistemic caveats
- **Missed Guardrail:** Machine-checkable verification of epistemic disclosures in implementation contracts
- **New Guardrail:** Downstream implementation contracts must carry forward all upstream epistemic caveats unchanged
- **Phase Introduced:** `EXP-07-P0-C4` | **Status:** `ACTIVE`
### GOV-RULE-059: Effective optimization batch size is distinct from BatchNorm statistical batch size.
- **Category:** `ARCHITECTURE_AND_OPTIMIZATION`
- **Triggering Incident:** INC-P0-C5-001: P0-C4 claimed gradient accumulation (steps=2, virtual batch_size=16) stabilized BatchNorm running statistics
- **Root Cause:** Conflating optimizer gradient accumulation batch with layer-level normalization statistical evaluation windows
- **Failed Assumption:** Accumulating gradients over multiple minibatches increases the sample size seen by BatchNorm during forward passes
- **Missed Guardrail:** Explicit separation of physical minibatch, effective optimization batch, and BatchNorm statistical batch
- **New Guardrail:** Gradient accumulation must never be claimed to increase or stabilize BatchNorm statistical batch size; physical batch size (8) must remain explicitly documented as a known statistical risk
- **Phase Introduced:** `EXP-07-P0-C5` | **Status:** `ACTIVE`

### GOV-RULE-060: Runtime input-domain terminology must distinguish raw uncalibrated DN, physical backscatter, and model-space representation.
- **Category:** `METROLOGICAL_DISCIPLINE`
- **Triggering Incident:** INC-P0-C6-001: Ambiguity in describing uncalibrated aggregated DN as an approximate calibration pathway
- **Root Cause:** Conflating the name of the upstream calibration aggregation validation study with the literal runtime input domain
- **Failed Assumption:** Calling input data approximate calibration does not mislead downstream model interpretation
- **Missed Guardrail:** Explicit requirement that runtime input-domain terminology distinguish uncalibrated DN from physical backscatter (sigma0)
- **New Guardrail:** When models ingest uncalibrated detector counts, documentation and code must explicitly specify the uncalibrated DN domain; describing uncalibrated DN as calibrated backscatter is strictly prohibited
- **Phase Introduced:** `EXP-07-P0-C6` | **Status:** `ACTIVE`

### GOV-RULE-061: Independent recomputation is mandatory for high-impact pipeline validation.
- **Category:** `VERIFICATION_DISCIPLINE`
- **Triggering Incident:** INC-P0-C6-001 / Preventative Guardrail: Need for first-principles mathematical verification
- **Root Cause:** Over-reliance on internal helper self-consistency ('function agrees with itself')
- **Failed Assumption:** Passing internal unit tests proves mathematical fidelity without external first-principles recomputation
- **Missed Guardrail:** Mandatory independent mathematical recomputation of critical pipeline outputs (loss, metrics, normalization, sampling)
- **New Guardrail:** Validation of critical ML pipeline components must include independent mathematical recomputation from first principles without calling production helpers
- **Phase Introduced:** `EXP-07-P0-C6` | **Status:** `ACTIVE`

### GOV-RULE-062: Training protocol must be frozen before execution; hyperparameter sweeps require formal authorization.
- **Category:** `EXPERIMENTAL_DISCIPLINE`
- **Triggering Incident:** Preventative Guardrail: Risk of uncontrolled hyperparameter exploration or post-hoc protocol mutation
- **Root Cause:** Temptation to adjust hyperparameters dynamically during initial baseline execution
- **Failed Assumption:** Dynamic tuning during baseline runs speeds up model convergence without sacrificing scientific validity
- **Missed Guardrail:** Authoritative, machine-checkable training protocol freeze artifact
- **New Guardrail:** A baseline machine learning experiment must have its complete training protocol (optimizer, scheduler, loss weights, batch dynamics, stopping criteria) frozen in an authoritative artifact before launching execution. Uncontrolled hyperparameter fishing or simultaneous multi-variable exploration is strictly prohibited.
- **Phase Introduced:** `EXP-07-P0-C7` | **Status:** `ACTIVE`

### GOV-RULE-063: Single-seed performance must not be represented as robust statistical evidence.
- **Category:** `STATISTICAL_RIGOR`
- **Triggering Incident:** Preventative Guardrail: Small dataset size (12 TRAIN parents) introduces significant seed-to-seed variance
- **Root Cause:** Conflating single-seed convergence with reproducible generalizable performance
- **Failed Assumption:** A single successful seed run provides sufficient evidence of model stability and performance
- **Missed Guardrail:** Mandatory multi-seed replication policy and reporting standards
- **New Guardrail:** A single random seed execution provides preliminary baseline evidence only. Claims of model performance, stability, or superiority must report mean, standard deviation, and min/max ranges across an authorized multi-seed replication set (minimum 3 seeds).
- **Phase Introduced:** `EXP-07-P0-C7` | **Status:** `ACTIVE`

### GOV-RULE-064: Untrained dry-run metrics are pipeline sanity checks, not performance baselines.
- **Category:** `EPISTEMIC_DISCIPLINE`
- **Triggering Incident:** Preventative Guardrail: Confusion between untrained integration checks and scientific baselines
- **Root Cause:** Numeric outputs produced during pipeline dry-runs being cited as performance comparisons
- **Failed Assumption:** Pipeline verification outputs can serve as reference baselines for model accuracy
- **Missed Guardrail:** Explicit epistemic categorization of dry-run evaluation outputs
- **New Guardrail:** Metrics evaluated on untrained or initialized models during pre-flight CPU dry-runs verify pipeline mechanics and numerical safety only. They must never be compared against trained models or cited as baseline performance numbers.
- **Phase Introduced:** `EXP-07-P0-C7` | **Status:** `ACTIVE`
