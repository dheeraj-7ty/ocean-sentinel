# PHASE 8-P3-C1 — PROVENANCE VERSIONING, REPRODUCIBILITY SEMANTICS & GOVERNANCE CLOSURE

**Phase:** PHASE 8-P3-C1  
**Date:** 2026-09-13  
**Status:** COMPLETE  
**Final Decision:** **A. FINAL — P3 CLOSED; EXP-07 PROTOCOL DESIGN AUTHORIZED**  
**Repository Branch:** `master` (0 staged changes)  

---

## 1. Executive Summary & Why P3-C1 Existed

Phase 8-P3 (Final Pre-Training Audit) achieved substantial data integrity verification across the 147 physical samples, 27 independent Sentinel-1 IW parent acquisitions, zero parent leakage, zero duplicate images, and zero Class-14 OS pixels. However, P3 terminated with a conditional verdict:

> **B. CONDITIONAL — READY ONLY AFTER SPECIFIED REMEDIATIONS**

This condition was triggered by four specific institutional governance concerns:
1. **In-Place Mutation of Authoritative Artifacts:** During P3 guardrail resolution, two previously authoritative P2-R2-C2 artifacts (`ops01_physical_dataset_manifest_v3.json` and `ops01_dataset_sufficiency_v4.json`) were modified in place to add required epistemic disclosure fields, causing their SHA-256 hashes to diverge from historical records without formal successor versioning.
2. **Unformalized Reproducibility Semantics:** The label `LEVEL_B_ESTABLISHED` was utilized without formal operational criteria, acceptable claim boundaries, or evidence thresholds.
3. **Conflation of Scientific vs. Engineering Decisions:** Fourteen open protocol items for EXP-07 remained open, carrying the risk that engineering implementation convenience could silently dictate scientific experimental design.
4. **Institutional Memory Fragility:** Critical lessons learned across Phase 7C, P2, and P3 required permanent institutionalization so that future sessions could not repeat past errors.

Phase 8-P3-C1 was commissioned as a targeted corrective closure to remediate these governance, provenance, and semantic issues without altering the physical dataset, without training models, and without touching Part-III.

---

## 2. Cancelled Historical Search & Why It Was Bounded

During the initial invocation of P3-C1, an unconstrained recursive scan of the repository was launched in a background task to locate previously recorded hashes for `manifest_v3` and `sufficiency_v4`. This unbounded search crawled deep binary directories and untracked file structures, stalling progress.

The operation was cancelled, and under Step 1 guidance, historical recovery was redefined as a **bounded best-effort search** with a strict time and scope budget limited to targeted authoritative locations:
- Authoritative metadata inventories (`ops01_p3_artifact_inventory_v1.json`)
- Phase reports and ledgers (`experiments/PHASE_8_P2_R2_C2_*.md`, `ops01_corrective_audit_ledger_v2.json`)
- Read-only Git tracked file inspections

This demonstrated a fundamental operational principle: **Never launch unbounded recursive searches across a repository. Scope and time budgets must always govern investigative processes.**

---

## 3. Historical Hash Recovery Outcome

Targeted inspection of `data/metadata/ops01_p3_artifact_inventory_v1.json` (generated at the start of P3 at `2026-09-13T10:44:37.719384+00:00`, before the in-place edits occurred) successfully recovered the exact pre-P3 cryptographic SHA-256 hashes:

| Artifact | Pre-P3 SHA-256 (Recovered) | Post-P3 Mutated SHA-256 | Recovery Status | Evidence Source |
|:---|:---|:---|:---:|:---|
| `ops01_physical_dataset_manifest_v3.json` | `94521D08C00AB71269D9DE566468C1E8B8C12E3519C3AB97375F63DF75355787` | `36C7D5911B420A9B22F61E13604AE86BB933F7F519CB5CC53F8D9692AB361C2D` | `RECOVERED_FROM_EXPLICIT_SOURCE` | `ops01_p3_artifact_inventory_v1.json` (lines 19–27) |
| `ops01_dataset_sufficiency_v4.json` | `CB5C14A68BFDC2D72BD37FA4C7E579DD6A01015E6651228B3D6CA4C8B2FEF1A4` | `D44E05F55167EF46996722BC395FDB7D4293FBF7281E426BEAC3425C9EF45A10` | `RECOVERED_FROM_EXPLICIT_SOURCE` | `ops01_p3_artifact_inventory_v1.json` (lines 74–83) |

Because these hashes were recovered from an authoritative artifact generated within the repository, the outcome was certified as **CASE A: `RECOVERED_FROM_EXPLICIT_SOURCE`**.

---

## 4. Artifact Mutation Incident Analysis (INC-P3-C1-001)

- **Incident ID:** `INC-P3-C1-001`
- **Root Cause:** During Phase 8-P3 pre-training audit, guardrail tests checked for the presence of `EMPIRICALLY_SUPPORTED_PILOT_HYPOTHESIS` in `sufficiency_v4` and `HOLDOUT_PARTIALLY_USED_FOR_SELECTION` in `manifest_v3`. Because P2-R2-C2 had omitted these fields from top-level metadata, the tests failed. The auditing agent directly edited `manifest_v3.json` and `sufficiency_v4.json` in place to inject the fields.
- **Failed Assumption:** The agent assumed that modifying top-level metadata in place was harmless because data samples, image files, mask files, labels, and partition allocations were untouched.
- **Impact:** Divergence of file hashes from previously recorded inventory records, destroying hash-based provenance and version immutability.
- **Remediation:** Formally recorded in `ops01_p3_c1_version_lineage_v1.json` and `ops01_p3_c1_change_reconciliation_v1.json`; created clean successor artifacts `ops01_physical_dataset_manifest_v4.json` and `ops01_dataset_sufficiency_v5.json`.

---

## 5. Version Lineage & Successor Artifacts

To prevent version ambiguity from recurring, clean successor versions have been authored and locked:

### A. Manifest Succession
- **Superseded:** `data/metadata/ops01_physical_dataset_manifest_v3.json`
- **Successor:** `data/metadata/ops01_physical_dataset_manifest_v4.json` (v4.0.0)
- **Parent Reference:** Declares parent artifact and both pre-P3 and mutated SHA-256 hashes.
- **Sample Integrity:** 147 samples identically preserved. Zero additions, zero deletions, zero modifications to image paths, mask paths, radiometric statistics, or partition assignments.
- **Disclosures:** Fully incorporates all four permanent epistemic disclosures at top level.

### B. Sufficiency Document Succession
- **Superseded:** `data/metadata/ops01_dataset_sufficiency_v4.json`
- **Successor:** `data/metadata/ops01_dataset_sufficiency_v5.json` (v5.0.0)
- **Parent Reference:** Declares parent artifact and recovered pre-P3 SHA-256 hash.
- **Evaluation Status:** Re-affirms Decision `A. CORRECTED -- SUFFICIENT FOR P3` under canonical `ops01_taxonomy_v1.json` nomenclature.
- **Disclosures:** Formally embeds all four permanent epistemic disclosures.

---

## 6. Dataset Content-Change Assessment

An independent forensic comparison was conducted to establish whether Phase 8-P3 or Phase 8-P3-C1 altered the physical OPS-01 data layer. The findings are recorded in `data/metadata/ops01_p3_c1_change_reconciliation_v1.json`:

| Dimension | Evidence Category | Status | Verification Detail |
|:---|:---:|:---:|:---|
| **Physical Samples** | `PROVEN` | `PROVEN_UNCHANGED` | 147 samples identically present; identical sample IDs across all manifests |
| **Image Bytes** | `PROVEN` | `PROVEN_UNCHANGED` | All 147 physical GeoTIFF images on disk match manifest SHA-256 hashes |
| **Mask Bytes** | `PROVEN` | `PROVEN_UNCHANGED` | All 147 physical GeoTIFF masks on disk match manifest SHA-256 hashes |
| **Labels & OS Pixels** | `PROVEN` | `PROVEN_UNCHANGED` | All 9,633,792 audited pixels contain exactly 0 Class-14 (OS) pixels |
| **Source IDs** | `PROVEN` | `PROVEN_UNCHANGED` | 27 Sentinel-1 IW GRD parent products match source inventory v3 |
| **Parent Partitioning** | `PROVEN` | `PROVEN_UNCHANGED` | TRAIN=12 parents, DEV=7 parents, HOLDOUT=8 parents; 0 parent leakage |
| **Sample Distribution** | `PROVEN` | `PROVEN_UNCHANGED` | TRAIN=72, DEV=39, HOLDOUT=36 (Total=147) |
| **Metadata Layer** | `PROVEN` | `PROVEN_MUTATED` | Top-level disclosure fields were added during P3; now regularized into v4/v5 |

---

## 7. Dataset Identity Contract

Dataset identity is formally governed by `data/metadata/ops01_dataset_identity_v1.json` under the doctrine:

$$\text{DATASET IDENTITY} = \text{CONTENT} + \text{MANIFEST} + \text{TAXONOMY} + \text{SPLIT} + \text{PROVENANCE} + \text{PROTOCOL}$$

OPS-01 is defined by:
- **Authoritative Manifest:** `ops01_physical_dataset_manifest_v4.json`
- **Canonical Taxonomy:** `ops01_taxonomy_v1.json` (15 classes, OF=Ocean Front, OS=Mineral Oil Spill excluded)
- **Split Manifest:** `ops01_split_manifest_v4.json` (72 TRAIN / 39 DEV / 36 HOLDOUT)
- **Source Inventory:** `ops01_source_recovery_inventory_v3.json` (27 Level-1 parents)
- **Sufficiency Evaluation:** `ops01_dataset_sufficiency_v5.json`
- **Physical Contract:** 1-band VV 256×256 raw amplitude DN
- **Epistemic Disclosures:** All four permanent disclosures active
- **Reproducibility Tier:** Certified at Level B

---

## 8. Reproducibility Hierarchy & Operational Definitions

The project has established a formal five-tier reproducibility hierarchy in `data/metadata/ocean_sentinel_reproducibility_levels_v1.json`:

1. **LEVEL 0 — Non-Reproducible / Insufficient Record:** No verifiable cryptographic hashes or executable procedures exist.
2. **LEVEL A — Artifact Identity Reproducibility:** Exact stored artifacts are verifiable by cryptographic hash (SHA-256). Guarantees against bit-rot and in-place corruption.
3. **LEVEL B — Deterministic Verification Reproducibility:** Given stored inputs and declared environment, an independent operator running the verification suite reproduces identical derived outputs and assertions.
4. **LEVEL C — Pipeline Reconstruction Reproducibility:** An independent operator can reconstruct the complete processing pipeline from raw sensor inputs, code, configuration, and documentation, obtaining equivalent outputs.
5. **LEVEL D — Source-Process Reproducibility:** The primary sensor acquisition, annotation, and physical ground-truth validation are open, documented, and repeatable.

---

## 9. Current Certified Reproducibility Level

- **Current Evaluation:** **LEVEL B (Deterministic Verification Reproducibility)**
- **Justification:** All 147 samples, masks, manifests, and tiepoints are Level A hash-verified. All 20 reconciliation items, 61 P3 guardrails, 28 P3-C1 guardrails, and dataset counts deterministically recompute with zero discrepancy.
- **Level C / D Prohibitions:** Promotion of OPS-01 to Level C or Level D is **STRICTLY PROHIBITED**. The underlying tile extraction and block-mean correspondence hypothesis were reconstructed after the fact (`DATASET_GENERATION_METHOD = NOT_DIRECTLY_VERIFIED`). Claiming Level C or D would constitute a grave epistemic overclaim.

---

## 10. Permanent Epistemic Disclosures

The four permanent epistemic disclosures remain active and non-negotiable across all future manifests, models, and publications:

1. `HOLDOUT_PARTIALLY_USED_FOR_SELECTION`  
   *Holdout parent scenes were intentionally selected to satisfy class coverage requirements; the holdout is a partially blind benchmark.*
2. `CONDITIONAL_ENGINEERING_RECONSTRUCTION`  
   *Geographic alignment relies on XML tiepoint interpolation and is an engineering model, not an independently validated physical measurement.*
3. `EMPIRICALLY_SUPPORTED_PILOT_HYPOTHESIS`  
   *The 10× block-mean intensity correspondence model is an empirical pilot hypothesis.*
4. `DATASET_GENERATION_METHOD = NOT_DIRECTLY_VERIFIED`  
   *Primary tile generation code from original catalog authors was not directly observed or independently audited.*

---

## 11. Durable Governance & Institutional Memory

To ensure that future agents do not repeat historical mistakes, the project governance rules have been codified into:
- **Charter:** `experiments/PROJECT_GOVERNANCE/ocean_sentinel_governance_rules_v1.md` (Sections A through O)
- **Machine-Readable Register:** `data/metadata/ocean_sentinel_governance_rules_v1.json` (26 formal rules)

Key governance rules include:
- `GOV-RULE-001`: Literal contractual evaluation over mere class presence (LWA >= 2 parents).
- `GOV-RULE-003`: Algorithmic design parameter != physical uncertainty (50m buffer).
- `GOV-RULE-004`: Conditional residual != independent physical registration error (15.79m).
- `GOV-RULE-006`: Catalog declaration != physical imagery (47 declared != 47 materialized).
- `GOV-RULE-008`: Class presence != causal model failure (co-occurrence is not causation).
- `GOV-RULE-010`: Canonical taxonomy file is the sole semantic authority (no informal synonyms).
- `GOV-RULE-011`: OF = Ocean Front (label_id=6); BS = Biological Slicks; OS = Mineral Oil Spill (excluded).
- `GOV-RULE-012`: Exact basin wording only; never claim "globally representative".
- `GOV-RULE-013`: Temporal endpoint span != continuous temporal coverage.
- `GOV-RULE-015`: Repository component existence != dataset compatibility (TrujilloTileDataset is not OPS-01).
- `GOV-RULE-016`: Physical data reality outranks stale implementation assumptions (1-band 256×256 raw DN).
- `GOV-RULE-017`: Historical test result != freshly executed result.
- `GOV-RULE-018`: 0 staged != clean.
- `GOV-RULE-019`: Never modify a closed authoritative artifact in place without an explicit version transition.
- `GOV-RULE-020`: Reproducibility levels must have precise operational evidence definitions.
- `GOV-RULE-021`: Bounded investigation is mandatory; no unbounded recursive searches.
- `GOV-RULE-022`: Documented Part-I discrepancy is 7E vs 7F (never errant 7B transcription).
- `GOV-RULE-023`: Scientific protocol decisions must be frozen before implementation.
- `GOV-RULE-024`: OPS-01 DataLoader gap remains open until EXP-07 protocol is approved.
- `GOV-RULE-025`: Value domain representation is an open decision (OPEN-PREPROC-001).
- `GOV-RULE-026`: Training requires separate explicit authorization; Part-III remains firewalled.

---

## 12. Incident Learning Register

The permanent incident learning register has been established in `data/metadata/ocean_sentinel_incident_learning_register_v1.json`, capturing root causes, failed assumptions, impacts, resolutions, governance rule links, and automated regression tests for:
- `INC-P3-C1-001`: In-place mutation of manifest_v3 and sufficiency_v4
- `INC-P3-C1-002`: Unbounded recursive search stall
- `INC-P3-C1-003`: Unoperationalized Reproducibility Level B nomenclature
- `INC-P3-C1-004`: Part-I SHA discrepancy narrative wording error (7E vs 7F correction)
- `INC-P3-001`: Omission of permanent disclosures from P2-R2-C2 top-level metadata
- `INC-P3-002`: DataLoader contract mismatch with TrujilloTileDataset
- `INC-P3-003`: Raw amplitude DN value domain ambiguity
- `INC-P2-C2-001`: C1 report taxonomy terminology drift
- `INC-P2-C1-001`: LWA evaluated as sufficient with only 1 parent scene

---

## 13. Regression Guardrail Suite

A new dedicated automated test suite was created in `tests/test_phase_8_p3_c1_governance_guardrails.py` containing 28 rigorous semantic tests organized into 12 test groups:
1. `TestFrozenArtifactIntegrity` (EXP-06 and Part-I hashes exact)
2. `TestArtifactVersioningLineage` (manifest_v4, sufficiency_v5, lineage JSON)
3. `TestDatasetIdentityContract` (manifest, split, taxonomy, composition)
4. `TestReproducibilityHierarchy` (Levels 0–D, Level B certification, Level C/D prohibition)
5. `TestEpistemicDisclosures` (all 4 disclosures present across all authoritative files)
6. `TestTaxonomySemantics` (OF=Ocean Front, OS excluded, 0 OS pixels in samples)
7. `TestGovernanceRulesAndMemory` (rules JSON and sections A–O in markdown)
8. `TestIncidentLearningRegister` (all major incidents with root cause and regression test)
9. `TestDecisionSeparationAndOpenIssues` (scientific vs. engineering classification, loader gap open)
10. `TestPartIDiscrepancyWording` (correct 7E vs 7F present, errant 7B transcription absent)
11. `TestInvestigationBoundsAndTelemetry` (bounded status, valid run state)
12. `TestAbsoluteProhibitionsAndGitSafety` (zero EXP-07 artifacts, zero staged git changes)

---

## 14. Physical Dataset Recheck

The lightweight invariant recheck script (`scratch/dataset_recheck.py`) was executed directly against the filesystem. All values matched baseline specifications with zero deviation:

```json
{
  "sample_count": 147,
  "parent_count": 27,
  "partition_counts": {
    "TRAIN": 72,
    "DEV": 39,
    "HOLDOUT": 36
  },
  "partition_parent_counts": {
    "TRAIN": 12,
    "DEV": 7,
    "HOLDOUT": 8
  },
  "parent_leakage": 0,
  "duplicate_images": 0,
  "dominant_parent": "s1a-iw-grd-vv-20221031t055705-20221031t055730-045682-057692-001",
  "dominant_parent_count": 12,
  "dominant_parent_concentration": 0.0816,
  "core_lookalike_parents": {
    "AF": 7,
    "BS": 6,
    "LWA": 3,
    "OF": 9,
    "MCC": 11,
    "POW": 8,
    "RF": 5,
    "WS": 3,
    "Eddy": 3,
    "IWs": 12
  },
  "os_parent_count": 0,
  "status": "ALL_RECHECK_ITEMS_MATCH_EXACTLY"
}
```

---

## 15. Fresh Test Execution Results

In accordance with Rule 17 (*historical test result != freshly executed result*), all test suites were executed live with recorded timestamps, elapsed durations, exit codes, and counts:

| Suite Group | Test Command | Execution Time | Exit Code | Result |
|:---|:---|:---:|:---:|:---:|
| **P3-C1 Governance Guardrails** | `pytest tests/test_phase_8_p3_c1_governance_guardrails.py -v` | 1.44s | 0 | **28 passed, 0 failed** |
| **Phase 7C & Phase 8 Suites (13 files)** | `pytest tests/test_phase_7c*.py tests/test_phase_8*.py -q` | 5.76s | 0 | **306 passed, 0 failed** |
| **Active Governance Suites (20 files)** | `pytest [20 governance suites] -q` | 8.40s | 0 | **490 passed, 0 failed** |

---

## 16. Remaining Open Scientific Protocol Decisions

The fourteen open items for EXP-07 have been formally classified in `data/metadata/ops01_p3_c1_decision_classification_v1.json`. Crucially, scientific protocol decisions are isolated from engineering implementation choices:

1. **Value Domain Representation (`OPEN-PREPROC-001`):** Raw DN vs. Calibrated $\sigma^0$ vs. Decibel (dB). Documented in `ops01_p3_c1_preprocessing_decision_record_v1.json`. Must be resolved via planned experimental protocol in EXP-07.
2. **Normalization Statistics (`OPEN-PREPROC-002`):** Mean, standard deviation, or percentile clipping. Must be computed on TRAIN partition only.
3. **Task Formulation (`OPEN-PREPROC-004`):** Binary lookalike vs. non-lookalike, 15-class semantic segmentation, or hierarchical attribution.
4. **Loss Function Formulation:** Weighted BCE, Focal Loss, or Dice combinations to handle open-ocean class imbalance.
5. **Detection Threshold Protocol:** Calibrated on DEV only; evaluated on HOLDOUT without iterative tuning.
6. **Multi-Seed Protocol:** Statistical significance evaluation across independent random seeds.

---

## 17. Remaining Open Engineering Implementation Decisions

1. **OPS-01 DataLoader Implementation (`OPEN-LOADER-001`):** `OPS01Dataset` class must be designed to adhere strictly to the tensor and label contract frozen by the approved EXP-07 protocol.
2. **DataLoader Tensor Contract (`OPEN-LOADER-CONTRACT-001`):** Output shape, batch stacking, and channel handling.
3. **Batch Size (`OPEN-LOADER-004`):** Hardware memory optimization.
4. **DataLoader Worker Optimization (`OPEN-LOADER-003`):** `num_workers`, `pin_memory`, and shared memory configuration.
5. **Sampling and Class Balancing (`OPEN-LOADER-002`):** Tile sampling frequency across sparse lookalike classes.
6. **Checkpointing & Artifact Serialization:** Checkpoint retention schedule.

---

## 18. Explicit Non-Claims

Phase 8-P3-C1 does NOT establish:
- Any model training result or model convergence.
- Benchmark detection performance on Trujillo Part-III or any external dataset.
- Superiority of any new model over frozen EXP-06.
- Physical geodetic registration ground truth.
- Independent validation of original historical Li tile generation scripts.
- Global geographic representativeness of OPS-01.
- Complete blindness of the holdout split (partially used for selection).
- Selection of raw DN, dB, or calibrated $\sigma^0$ as the final input domain.
- Authorization to execute training on GPU.

---

## 19. Final Gate Decision

> # A. FINAL — P3 CLOSED; EXP-07 PROTOCOL DESIGN AUTHORIZED

### Verification Criteria Checklist
- [x] Version lineage is honest, explicit, and recorded (`ops01_p3_c1_version_lineage_v1.json`)
- [x] Historical pre-P3 hashes explicitly recovered (`ops01_p3_artifact_inventory_v1.json`)
- [x] Frozen EXP-06 checkpoint bit-identical (`B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF`)
- [x] Frozen Part-I split manifest bit-identical (`17F1FF35146C7CE62E90D6FCE7F197B711B55E3C3CB599610578443208669072`)
- [x] Physical OPS-01 dataset 100% unchanged (147 samples, 27 parents, 0 leakage, 0 OS pixels)
- [x] Reproducibility levels formally specified (Level 0, A, B, C, D)
- [x] Current reproducibility certified at Level B; Levels C/D explicitly prohibited
- [x] All four permanent epistemic disclosures active across all authoritative files
- [x] Durable institutional memory established (Markdown Charter + 26 Machine-Readable Rules)
- [x] Incident learning register fully populated with root causes and regression tests
- [x] 28/28 new P3-C1 governance guardrail tests passing
- [x] 306/306 Phase 7C and Phase 8 tests passing
- [x] Git staged mutations remain exactly zero
- [x] Zero Part-III access; zero GPU execution; zero unauthorized EXP-07 artifacts

---

## 20. Exact Next Authorized Phase

### AUTHORIZED NEXT PHASE:
**EXP-07 PROTOCOL SPECIFICATION & OPS-01 DATA INTERFACE DESIGN**

This authorized next phase may:
1. Formulate the scientific preprocessing decision (raw DN vs. calibrated $\sigma^0$ vs. dB) as an explicit protocol hypothesis.
2. Define the exact binary or multiclass task formulation.
3. Specify the normalization, augmentation, loss function, and evaluation threshold protocol.
4. Design and implement the `OPS01Dataset` PyTorch interface adhering strictly to the frozen protocol and the Part-III firewall.
5. Author the complete `EXP-07` experiment specification document.

### STRICTLY PROHIBITED IN THE NEXT PHASE:
- Initiating model training
- Utilizing GPU resources
- Generating experimental training run artifacts
- Evaluating on Part-III benchmark data
- Tuning thresholds on HOLDOUT
- Altering frozen EXP-06 or Part-I artifacts

*Training requires separate, explicit operator authorization following review and formal sign-off of the EXP-07 protocol specification document.*
