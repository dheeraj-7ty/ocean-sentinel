"""
PHASE 8-P3 PRE-TRAINING AUDIT GUARDRAILS
tests/test_phase_8_p3_pretraining_audit_guardrails.py

Regression guardrails for all material failures identified through Phase 7/8 audit history.
These tests must fail loudly on regression. They guard the OPS-01 dataset integrity,
alignment epistemic boundary, holdout status, taxonomy correctness, leakage,
and training-readiness contract.

Authoritative sources:
  data/metadata/ops01_taxonomy_v1.json
  data/metadata/ops01_physical_dataset_manifest_v3.json
  data/metadata/ops01_split_manifest_v4.json
  data/metadata/ops01_p3_*.json (P3 audit artifacts)
"""

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

MANIFEST = ROOT / "data/metadata/ops01_physical_dataset_manifest_v3.json"
TAXONOMY = ROOT / "data/metadata/ops01_taxonomy_v1.json"
SPLIT = ROOT / "data/metadata/ops01_split_manifest_v4.json"
SUFFICIENCY_V4 = ROOT / "data/metadata/ops01_dataset_sufficiency_v4.json"
LEDGER_V2 = ROOT / "data/metadata/ops01_corrective_audit_ledger_v2.json"
ARTIFACT_INV = ROOT / "data/metadata/ops01_p3_artifact_inventory_v1.json"
FS_RECONCILE = ROOT / "data/metadata/ops01_p3_filesystem_reconciliation_v1.json"
LABEL_INTEGRITY = ROOT / "data/metadata/ops01_p3_label_integrity_audit_v1.json"
LEAKAGE = ROOT / "data/metadata/ops01_p3_leakage_duplicate_audit_v1.json"
IDENTITY = ROOT / "data/metadata/ops01_p3_source_identity_audit_v1.json"
ALIGNMENT_EPIST = ROOT / "data/metadata/ops01_p3_alignment_epistemic_audit_v1.json"
DIVERSITY = ROOT / "data/metadata/ops01_p3_diversity_audit_v1.json"
REPRO = ROOT / "data/metadata/ops01_p3_reproducibility_audit_v1.json"
TRAINING_CONTRACT = ROOT / "data/metadata/ops01_p3_training_readiness_contract_v1.json"

EXP06_PATH = ROOT / "experiments/performance/exp06_positive_bce_weight/best_model.pt"
PART_I_PATH = ROOT / "data/metadata/internal_development_split_manifest.json"
EXP06_SHA = "B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF"
PART_I_SHA = "17F1FF35146C7CE62E90D6FCE7F197B711B55E3C3CB599610578443208669072"

PROHIBITED_DRIFT_TERMS_BY_ABBR = {
    "OF": ["Oil Slick Lookalike", "Organic Film", "Oil Front", "Class 8"],
    "MCC": ["Microalgae Bloom", "Marine Organisms"],
    "POW": ["Rain Cell / Precipitation"],
    "RF": ["Rain Cell Front"],
}
CANONICAL_OF_LABEL_ID = 6
CANONICAL_OF_NAME = "Ocean Front"

CORE_LOOKALIKES = ["AF", "BS", "LWA", "OF", "MCC", "POW", "RF", "WS", "Eddy", "IWs"]
OS_CLASS_14_LABEL_ID = 14


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while c := f.read(65536):
            h.update(c)
    return h.hexdigest().upper()


@pytest.fixture(scope="module")
def manifest_data():
    with open(MANIFEST, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def taxonomy_data():
    with open(TAXONOMY, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def split_data():
    with open(SPLIT, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def samples(manifest_data):
    return manifest_data["samples"]


@pytest.fixture(scope="module")
def canonical(taxonomy_data):
    return {c["abbreviation"]: c for c in taxonomy_data["classes"]}


# ============================================================
# GROUP 1: FROZEN ARTIFACT INTEGRITY
# ============================================================

class TestFrozenArtifactIntegrity:
    """Guard against mutation of frozen EXP-06 checkpoint and Part-I manifest."""

    def test_exp06_model_exists(self):
        assert EXP06_PATH.exists(), f"EXP-06 checkpoint missing: {EXP06_PATH}"

    def test_exp06_sha256_unchanged(self):
        actual = sha256(EXP06_PATH)
        assert actual == EXP06_SHA, (
            f"EXP-06 checkpoint has been MUTATED!\n"
            f"Expected: {EXP06_SHA}\n"
            f"Actual:   {actual}"
        )

    def test_part_i_manifest_exists(self):
        assert PART_I_PATH.exists(), f"Part-I manifest missing: {PART_I_PATH}"

    def test_part_i_sha256_unchanged(self):
        actual = sha256(PART_I_PATH)
        assert actual == PART_I_SHA, (
            f"Part-I manifest has been MUTATED!\n"
            f"Expected: {PART_I_SHA}\n"
            f"Actual:   {actual}"
        )


# ============================================================
# GROUP 2: TAXONOMY INTEGRITY (C2 INCIDENT REGRESSION)
# ============================================================

class TestTaxonomyIntegrity:
    """Prevents recurrence of C2 taxonomy drift incidents INC-P2R2-C2-001/002."""

    def test_of_canonical_name(self, canonical):
        assert "OF" in canonical, "OF abbreviation missing from taxonomy"
        assert canonical["OF"]["class_name"] == CANONICAL_OF_NAME, (
            f"OF class_name drift: expected '{CANONICAL_OF_NAME}', got '{canonical['OF']['class_name']}'"
        )

    def test_of_canonical_label_id(self, canonical):
        assert canonical["OF"]["source_label_id"] == CANONICAL_OF_LABEL_ID, (
            f"OF label_id drift: expected {CANONICAL_OF_LABEL_ID}, got {canonical['OF']['source_label_id']}"
        )

    def test_mcc_canonical_name(self, canonical):
        assert canonical["MCC"]["class_name"] == "Mesoscale Cellular Convection", (
            f"MCC class_name drift: got '{canonical['MCC']['class_name']}'"
        )

    def test_pow_canonical_name(self, canonical):
        assert canonical["POW"]["class_name"] == "Pure Ocean Wave", (
            f"POW drift: got '{canonical['POW']['class_name']}'"
        )

    def test_rf_canonical_name(self, canonical):
        assert canonical["RF"]["class_name"] == "Rain Cell / Rain Footprint", (
            f"RF drift: got '{canonical['RF']['class_name']}'"
        )

    def test_os_canonical_label_id(self, canonical):
        assert canonical["OS"]["source_label_id"] == OS_CLASS_14_LABEL_ID, (
            f"OS label_id must be 14, got {canonical['OS']['source_label_id']}"
        )

    def test_no_drift_terms_in_sample_class_names(self, samples, canonical):
        """Checks every sample's class_composition for prohibited drift terminology."""
        violations = []
        for s in samples:
            for abbr, info in s.get("class_composition", {}).items():
                stored_name = info.get("class_name", "")
                for prohibited_name in PROHIBITED_DRIFT_TERMS_BY_ABBR.get(abbr, []):
                    if prohibited_name.lower() in stored_name.lower():
                        violations.append(
                            f"sample={s['sample_id']}, abbr={abbr}, "
                            f"stored='{stored_name}', prohibited='{prohibited_name}'"
                        )
        assert not violations, f"Taxonomy drift terms found in {len(violations)} places:\n" + "\n".join(violations[:5])

    def test_of_not_class_8_in_any_sample(self, samples):
        """Specifically guards against INC-P2R2-C2-002: OF labeled as Class 8."""
        violations = []
        for s in samples:
            cc = s.get("class_composition", {})
            if "OF" in cc:
                sid = cc["OF"].get("source_label_id")
                if sid is not None and sid != CANONICAL_OF_LABEL_ID:
                    violations.append(f"sample={s['sample_id']}: OF has source_label_id={sid}, expected {CANONICAL_OF_LABEL_ID}")
        assert not violations, "OF class assigned wrong label ID:\n" + "\n".join(violations)

    def test_no_os_label_in_class_composition(self, samples):
        """OS (Class 14) must never appear in any OPS-01 sample's class_composition."""
        violations = []
        for s in samples:
            if "OS" in s.get("class_composition", {}):
                violations.append(s["sample_id"])
            if OS_CLASS_14_LABEL_ID in s.get("label_class_set", []):
                violations.append(f"{s['sample_id']} (in label_class_set)")
        assert not violations, f"OS (Class 14) found in {len(violations)} samples: {violations[:3]}"


# ============================================================
# GROUP 3: DATASET POPULATION INTEGRITY
# ============================================================

class TestDatasetPopulationIntegrity:
    """Verifies the OPS-01 physical population claims from P2-R2-C2."""

    def test_total_sample_count(self, samples):
        assert len(samples) == 147, f"Expected 147 samples, got {len(samples)}"

    def test_sample_id_uniqueness(self, samples):
        ids = [s["sample_id"] for s in samples]
        dupes = [id for id, cnt in Counter(ids).items() if cnt > 1]
        assert not dupes, f"Duplicate sample IDs found: {dupes}"

    def test_partition_counts(self, samples):
        counts = Counter(s["partition"] for s in samples)
        assert counts["TRAIN"] == 72, f"TRAIN count: expected 72, got {counts['TRAIN']}"
        assert counts["DEV"] == 39, f"DEV count: expected 39, got {counts['DEV']}"
        assert counts["HOLDOUT"] == 36, f"HOLDOUT count: expected 36, got {counts['HOLDOUT']}"

    def test_partition_parent_counts(self, samples):
        partition_parents = defaultdict(set)
        for s in samples:
            partition_parents[s["partition"]].add(s["parent_scene_id"])
        assert len(partition_parents["TRAIN"]) == 12, f"TRAIN parents: {len(partition_parents['TRAIN'])}"
        assert len(partition_parents["DEV"]) == 7, f"DEV parents: {len(partition_parents['DEV'])}"
        assert len(partition_parents["HOLDOUT"]) == 8, f"HOLDOUT parents: {len(partition_parents['HOLDOUT'])}"

    def test_total_parent_count(self, samples):
        all_parents = set(s["parent_scene_id"] for s in samples)
        assert len(all_parents) == 27, f"Expected 27 unique parents, got {len(all_parents)}"

    def test_image_sha256_uniqueness(self, samples):
        """All 147 images must have distinct SHA256 hashes."""
        shas = [s.get("image_sha256", "") for s in samples]
        dupes = [sha for sha, cnt in Counter(shas).items() if cnt > 1 and sha]
        assert not dupes, f"Duplicate image SHA256 hashes found: {dupes[:3]}"


# ============================================================
# GROUP 4: LEAKAGE / INDEPENDENCE
# ============================================================

class TestLeakageIndependence:
    """Zero inter-partition parent leakage must be maintained."""

    def test_no_parent_crosses_partitions(self, samples):
        parent_partitions = defaultdict(set)
        for s in samples:
            parent_partitions[s["parent_scene_id"]].add(s["partition"])
        leaky = {pid: sorted(parts) for pid, parts in parent_partitions.items() if len(parts) > 1}
        assert not leaky, (
            f"PARENT PARTITION LEAKAGE DETECTED in {len(leaky)} parents:\n"
            + "\n".join(f"  {pid}: {parts}" for pid, parts in list(leaky.items())[:3])
        )

    def test_no_duplicate_image_content_across_partitions(self, samples):
        sha_partition = {}
        violations = []
        for s in samples:
            sha = s.get("image_sha256", "")
            part = s.get("partition")
            if sha:
                if sha in sha_partition and sha_partition[sha] != part:
                    violations.append(f"SHA {sha[:16]}... in {sha_partition[sha]} and {part}")
                else:
                    sha_partition[sha] = part
        assert not violations, f"Cross-partition duplicate image content: {violations[:3]}"

    def test_split_manifest_consistency(self, samples, split_data):
        parts = split_data.get("partitions", {})
        split_train = set(parts.get("TRAIN", {}).get("sample_ids", []))
        split_dev = set(parts.get("DEV", {}).get("sample_ids", []))
        split_holdout = set(parts.get("HOLDOUT", {}).get("sample_ids", []))
        mismatches = []
        for s in samples:
            sid = s["sample_id"]
            part = s.get("partition")
            if part == "TRAIN" and sid not in split_train:
                mismatches.append(f"{sid}: manifest=TRAIN but not in split_manifest TRAIN")
            elif part == "DEV" and sid not in split_dev:
                mismatches.append(f"{sid}: manifest=DEV but not in split_manifest DEV")
            elif part == "HOLDOUT" and sid not in split_holdout:
                mismatches.append(f"{sid}: manifest=HOLDOUT but not in split_manifest HOLDOUT")
        assert not mismatches, f"Split manifest inconsistency in {len(mismatches)} samples: {mismatches[:3]}"


# ============================================================
# GROUP 5: CORE LOOKALIKE SUFFICIENCY
# ============================================================

class TestLookalikeSufficiency:
    """All core lookalike classes must satisfy multi-parent coverage contract."""

    def test_all_core_lookalikes_at_least_2_parents(self, samples):
        class_parents = defaultdict(set)
        for s in samples:
            for abbr in s.get("class_composition", {}):
                class_parents[abbr].add(s["parent_scene_id"])
        failures = []
        for abbr in CORE_LOOKALIKES:
            n = len(class_parents.get(abbr, set()))
            if n < 2:
                failures.append(f"{abbr}: only {n} parent(s)")
        assert not failures, f"Lookalike parent sufficiency failures:\n" + "\n".join(failures)

    def test_lwa_at_least_2_parents(self, samples):
        parents = set(s["parent_scene_id"] for s in samples if "LWA" in s.get("class_composition", {}))
        assert len(parents) >= 2, f"LWA has only {len(parents)} parent(s) — C1 incident regression"

    def test_hm_at_least_5_parents(self, samples):
        parents = set(s["parent_scene_id"] for s in samples if "HM" in s.get("class_composition", {}))
        assert len(parents) >= 5, f"HM has only {len(parents)} parent(s)"

    def test_no_os_class_in_dataset(self, samples):
        os_found = [s["sample_id"] for s in samples if OS_CLASS_14_LABEL_ID in s.get("label_class_set", [])]
        assert not os_found, f"OS (Class 14) present in {len(os_found)} samples: {os_found[:3]}"


# ============================================================
# GROUP 6: ALIGNMENT / EPISTEMIC BOUNDARY
# ============================================================

class TestAlignmentEpistemicBoundary:
    """Every sample must carry the correct epistemic status; no overclaiming allowed."""

    def test_all_samples_have_cer_status(self, samples):
        non_cer = [s["sample_id"] for s in samples
                   if s.get("alignment_status") != "CONDITIONAL_ENGINEERING_RECONSTRUCTION"]
        assert not non_cer, (
            f"{len(non_cer)} samples missing CONDITIONAL_ENGINEERING_RECONSTRUCTION status"
        )

    def test_all_samples_have_esp_status(self, samples):
        non_esp = [s["sample_id"] for s in samples
                   if s.get("intensity_correspondence_status") != "EMPIRICALLY_SUPPORTED_PILOT_HYPOTHESIS"]
        assert not non_esp, (
            f"{len(non_esp)} samples missing EMPIRICALLY_SUPPORTED_PILOT_HYPOTHESIS status"
        )

    def test_manifest_does_not_claim_ground_truth_registration(self, manifest_data):
        text = json.dumps(manifest_data).lower()
        prohibited = ["ground truth georegistration", "validated registration", "confirmed li method"]
        hits = [t for t in prohibited if t in text]
        assert not hits, f"Manifest contains overclaim terms: {hits}"

    def test_epistemic_boundary_constant_in_sufficiency_v4(self):
        text = SUFFICIENCY_V4.read_text(encoding="utf-8")
        assert "CONDITIONAL_ENGINEERING_RECONSTRUCTION" in text
        assert "EMPIRICALLY_SUPPORTED_PILOT_HYPOTHESIS" in text
        assert "NOT_DIRECTLY_VERIFIED" in text


# ============================================================
# GROUP 7: HOLDOUT STATUS PERMANENCE
# ============================================================

class TestHoldoutStatusPermanence:
    """HOLDOUT_PARTIALLY_USED_FOR_SELECTION must be present and never weakened."""

    def test_holdout_status_in_manifest(self, manifest_data):
        text = json.dumps(manifest_data)
        assert "HOLDOUT_PARTIALLY_USED_FOR_SELECTION" in text, (
            "HOLDOUT_PARTIALLY_USED_FOR_SELECTION disclosure missing from manifest"
        )

    def test_holdout_status_in_sufficiency_v4(self):
        text = SUFFICIENCY_V4.read_text(encoding="utf-8")
        assert "HOLDOUT_PARTIALLY_USED_FOR_SELECTION" in text, (
            "HOLDOUT_PARTIALLY_USED_FOR_SELECTION missing from sufficiency_v4"
        )

    def test_holdout_not_described_as_pristine(self, manifest_data):
        text = json.dumps(manifest_data).lower()
        prohibited = ["pristine holdout", "untouched benchmark", "fully blind test", "unbiased benchmark"]
        hits = [t for t in prohibited if t in text]
        assert not hits, f"Holdout weakening language found: {hits}"


# ============================================================
# GROUP 8: P3 AUDIT ARTIFACT EXISTENCE
# ============================================================

class TestP3AuditArtifactExistence:
    """All required P3 audit artifacts must exist on disk."""

    @pytest.mark.parametrize("path", [
        ARTIFACT_INV, FS_RECONCILE, LABEL_INTEGRITY,
        LEAKAGE, IDENTITY, ALIGNMENT_EPIST, DIVERSITY,
        REPRO, TRAINING_CONTRACT,
        ROOT / "data/metadata/ops01_p3_preprocessing_audit_v1.json",
        ROOT / "data/metadata/ops01_p3_dataloader_contract_audit_v1.json",
    ])
    def test_p3_artifact_exists(self, path):
        assert path.exists(), f"Required P3 artifact missing: {path}"

    def test_p3_filesystem_reconciliation_passed(self):
        with open(FS_RECONCILE, encoding="utf-8") as f:
            result = json.load(f)
        assert result["verdict"] == "PASS", (
            f"Filesystem reconciliation FAILED: {result.get('summary', {})}"
        )

    def test_p3_label_integrity_passed(self):
        with open(LABEL_INTEGRITY, encoding="utf-8") as f:
            result = json.load(f)
        assert result["overall_verdict"] == "PASS", (
            f"Label integrity FAILED: {result.get('summary', {})}"
        )

    def test_p3_leakage_passed(self):
        with open(LEAKAGE, encoding="utf-8") as f:
            result = json.load(f)
        assert result["verdict"] == "PASS", (
            f"Leakage audit FAILED: {result.get('issues', [])[:3]}"
        )

    def test_p3_alignment_epistemic_passed(self):
        with open(ALIGNMENT_EPIST, encoding="utf-8") as f:
            result = json.load(f)
        assert result["verdict"] == "PASS", (
            f"Alignment epistemic audit FAILED"
        )

    def test_p3_diversity_passed(self):
        with open(DIVERSITY, encoding="utf-8") as f:
            result = json.load(f)
        assert result["verdict"] == "PASS", (
            f"Diversity audit FAILED"
        )


# ============================================================
# GROUP 9: GEOGRAPHIC / TEMPORAL OVERCLAIM GUARDS
# ============================================================

class TestGeographicTemporalEpistemicBounds:
    """Prevents geographic and temporal overclaiming."""

    def test_basin_count_is_5_not_more(self, samples):
        basins = set(s.get("geographic_location", {}).get("ocean_basin", "UNKNOWN") for s in samples)
        assert len(basins) == 5, f"Basin count changed from 5: {sorted(basins)}"

    def test_south_atlantic_has_only_1_parent(self, samples):
        sa_parents = set(
            s["parent_scene_id"] for s in samples
            if s.get("geographic_location", {}).get("ocean_basin", "") == "South Atlantic"
        )
        # South Atlantic documented as 1 parent (single-scene limitation)
        assert len(sa_parents) <= 2, f"South Atlantic parents exceeded single-scene limitation: {len(sa_parents)}"

    def test_diversity_artifact_epistemic_bounds_present(self):
        with open(DIVERSITY, encoding="utf-8") as f:
            result = json.load(f)
        bounds = result.get("epistemic_bounds", [])
        assert any("5 basin labels" in b for b in bounds), "Missing epistemic bound: 5 basin labels != globally representative"
        assert any("27 parents" in b for b in bounds), "Missing epistemic bound: 27 parents != independent environments"


# ============================================================
# GROUP 10: TRAINING READINESS CONTRACT GUARDS
# ============================================================

class TestTrainingReadinessContract:
    """Ensures training cannot proceed without resolving open protocol decisions."""

    def test_training_readiness_contract_exists(self):
        assert TRAINING_CONTRACT.exists()

    def test_training_readiness_requires_operator_approval(self):
        with open(TRAINING_CONTRACT, encoding="utf-8") as f:
            contract = json.load(f)
        auth = contract.get("authorization_required_before_training", [])
        assert any("Operator sign-off" in a for a in auth), "Training contract missing operator approval requirement"

    def test_open_protocol_decisions_documented(self):
        with open(TRAINING_CONTRACT, encoding="utf-8") as f:
            contract = json.load(f)
        decisions = contract.get("open_protocol_decisions_summary", [])
        assert len(decisions) >= 10, f"Expected >= 10 open protocol decisions, got {len(decisions)}"

    def test_ops01_dataloader_marked_not_implemented(self):
        path = ROOT / "data/metadata/ops01_p3_dataloader_contract_audit_v1.json"
        with open(path, encoding="utf-8") as f:
            result = json.load(f)
        assert result.get("ops01_dataloader_status") == "NOT_IMPLEMENTED", (
            "OPS-01 DataLoader status changed from NOT_IMPLEMENTED without updating this test"
        )

    def test_no_ops01_training_script_exists(self):
        """Training must not be authorized until open decisions resolved."""
        train_scripts = list((ROOT / "scripts").glob("train_exp07*.py"))
        assert not train_scripts, (
            f"EXP-07 training script found before protocol authorization: {train_scripts}"
        )


# ============================================================
# GROUP 11: REPRODUCIBILITY LEVEL AUDIT
# ============================================================

class TestReproducibilityLevelAudit:
    """Prevents collapse of reproducibility levels A/B/C/D."""

    def test_reproducibility_artifact_exists(self):
        assert REPRO.exists()

    def test_highest_level_is_b_not_d(self):
        with open(REPRO, encoding="utf-8") as f:
            result = json.load(f)
        level = result.get("current_highest_level", "")
        assert level == "B_deterministic_rerun", (
            f"Reproducibility level changed to '{level}'; scientific procedure (Level D) not established"
        )

    def test_level_d_not_established(self):
        with open(REPRO, encoding="utf-8") as f:
            result = json.load(f)
        levels = result.get("reproducibility_levels_defined", {})
        d_val = levels.get("D_scientific_procedure_reproducibility", "")
        assert "NOT_ESTABLISHED" in d_val, (
            "Level D (scientific procedure) must remain NOT_ESTABLISHED until directly verified"
        )


# ============================================================
# GROUP 12: DOMINANT PARENT CONCENTRATION
# ============================================================

class TestDominantParentConcentration:
    """Dominant parent must stay below 20% concentration threshold."""

    def test_dominant_parent_below_20pct(self, samples):
        counts = Counter(s["parent_scene_id"] for s in samples)
        max_count = counts.most_common(1)[0][1]
        concentration = max_count / len(samples)
        assert concentration < 0.20, (
            f"Dominant parent concentration {concentration:.1%} >= 20% threshold"
        )
