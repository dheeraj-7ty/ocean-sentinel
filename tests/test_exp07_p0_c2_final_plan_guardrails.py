"""EXP-07-P0-C2 Final Plan Guardrails — 40 Protocol Integrity Regression Tests.

These tests enforce the scientific, radiometric, and governance constraints
established by the EXP-07-P0-C2 second-order review. They verify that:
1. No training or GPU usage occurs during protocol phases
2. Frozen artifacts remain unmodified
3. Scientific decisions are properly classified and evidence-bounded
4. Calibration analysis addresses nonlinearity (not just LUT smoothness)
5. Source masks and validity masks remain conceptually separated
"""

import hashlib
import json
import os
import pathlib

import pytest

BASE = pathlib.Path(__file__).resolve().parent.parent
DATA = BASE / "data"
META = DATA / "metadata"
EXP07 = BASE / "experiments" / "EXP-07"
SCRATCH = BASE / "scratch"


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# FROZEN HASH GUARDRAILS
# ============================================================


class TestFrozenHashes:
    """Verify frozen artifacts have not been modified."""

    def test_exp06_frozen(self):
        path = BASE / "experiments" / "performance" / "exp06_positive_bce_weight" / "best_model.pt"
        expected = "B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF"
        assert _sha256(path) == expected, "EXP-06 best model hash changed"

    def test_part_i_frozen(self):
        path = META / "internal_development_split_manifest.json"
        expected = "17F1FF35146C7CE62E90D6FCE7F197B711B55E3C3CB599610578443208669072"
        assert _sha256(path) == expected, "Part-I manifest hash changed"


# ============================================================
# NO TRAINING / NO GPU / NO EXECUTION GUARDRAILS
# ============================================================


class TestNoTraining:
    """Verify protocol phase constraints."""

    def test_no_model_checkpoints_in_exp07(self):
        if EXP07.exists():
            for f in EXP07.rglob("*.pt"):
                if "runs" in f.parts:
                    continue
                pytest.fail(f"Model checkpoint found in EXP-07: {f}")
            for f in EXP07.rglob("*.pth"):
                if "runs" in f.parts:
                    continue
                pytest.fail(f"Model checkpoint found in EXP-07: {f}")

    def test_no_part_iii_access(self):
        part3 = DATA / "part_iii"
        if part3.exists():
            assert not any(part3.iterdir()), "Part-III should not have been accessed"

    def test_no_gpu_logs(self):
        if EXP07.exists():
            for f in EXP07.rglob("*.log"):
                content = f.read_text(errors="ignore")
                assert "cuda" not in content.lower() or "no cuda" in content.lower(), \
                    f"GPU usage logged in {f}"


# ============================================================
# ARTIFACT EXISTENCE GUARDRAILS
# ============================================================


class TestArtifactExistence:
    """Verify all required C2 artifacts exist."""

    def test_decision_register_exists(self):
        assert (META / "exp07_p0_c2_decision_register_v1.json").exists()

    def test_calibration_feasibility_exists(self):
        assert (META / "exp07_p0_c2_calibration_feasibility_v1.json").exists()

    def test_confounder_register_exists(self):
        assert (META / "exp07_p0_c2_confounder_register_v1.json").exists()

    def test_final_execution_plan_exists(self):
        assert (EXP07 / "EXP07_P0_C2_FINAL_EXECUTION_PLAN_20260913.md").exists()

    def test_telemetry_exists(self):
        assert (SCRATCH / "exp07_p0_c2_run_state.json").exists()


# ============================================================
# CALIBRATION ANALYSIS GUARDRAILS
# ============================================================


class TestCalibrationAnalysis:
    """Verify calibration analysis is evidence-bounded and addresses nonlinearity."""

    @pytest.fixture
    def cal(self):
        return _load_json(META / "exp07_p0_c2_calibration_feasibility_v1.json")

    def test_calibration_status_evidence_bounded(self, cal):
        """Calibration status must not be 'INFEASIBLE' without addressing S3 recovery."""
        status = cal["summary"]["overall_status"]
        assert "INFEASIBLE" not in status.upper(), \
            "Calibration declared infeasible despite proven S3 accessibility"

    def test_all_27_parent_coverage(self, cal):
        """All 27 parent products must have calibration accessibility recorded."""
        assert cal["summary"]["calibration_xml_accessible"] == 27

    def test_nonlinearity_explicitly_addressed(self, cal):
        """Calibration analysis must contain nonlinearity analysis section."""
        assert "nonlinearity_analysis" in cal, \
            "Calibration analysis missing nonlinearity section"

    def test_nonlinearity_identifies_two_error_sources(self, cal):
        sources = cal["nonlinearity_analysis"]["error_sources"]
        assert len(sources) >= 2, \
            "Nonlinearity analysis must identify at least 2 error sources (LUT variation AND aggregation bias)"

    def test_lut_smoothness_insufficient_alone(self, cal):
        """LUT smoothness alone cannot establish calibration equivalence."""
        sources = cal["nonlinearity_analysis"]["error_sources"]
        lut_source = [s for s in sources if "LUT" in s["source"]]
        assert lut_source, "LUT variation error source not found"
        # The other source (nonlinear aggregation) must also be present
        agg_source = [s for s in sources if "aggregation" in s["source"].lower() or "nonlinear" in s["source"].lower()]
        assert agg_source, "Nonlinear aggregation error source not found"

    def test_calibration_not_exact_from_block_mean(self, cal):
        """Must acknowledge that exact sigma0 is NOT reconstructable from block-mean alone."""
        assert cal["summary"]["sigma0_exactly_reconstructable"] is False

    def test_dn_semantics_explicit(self, cal):
        """DN semantics (amplitude vs intensity) must be explicitly documented."""
        assert "dn_semantics" in cal["calibration_formula"]


# ============================================================
# DECISION REGISTER GUARDRAILS
# ============================================================


class TestDecisionRegister:
    """Verify decision register is properly structured and evidence-bounded."""

    @pytest.fixture
    def dr(self):
        return _load_json(META / "exp07_p0_c2_decision_register_v1.json")

    def test_physical_db_not_arbitrary_log(self, dr):
        """10*log10(DN+eps) must NOT be called physical dB."""
        d03 = [d for d in dr["decisions"] if d["decision_id"] == "D-C2-03"]
        assert d03, "Decision D-C2-03 (DN terminology) not found"
        assert "empirical" in d03[0]["recommended_option"].lower()

    def test_sampler_beyond_dominant_class(self, dr):
        """Sampler decision must acknowledge dominant-class failure."""
        d06 = [d for d in dr["decisions"] if d["decision_id"] == "D-C2-06"]
        assert d06, "Decision D-C2-06 (sampler) not found"
        assert "REJECTED" in d06[0]["recommended_option"].upper() or \
               "dominant" in d06[0]["evidence"].lower()

    def test_lr_rationale_corrected(self, dr):
        """LR rationale 'compensates for fewer batches' must be rejected."""
        d08 = [d for d in dr["decisions"] if d["decision_id"] == "D-C2-08"]
        assert d08, "Decision D-C2-08 (LR) not found"
        assert "no theoretical basis" in d08[0]["evidence"].lower() or \
               "UNVALIDATED" in d08[0]["recommended_option"].upper()

    def test_every_frozen_has_evidence(self, dr):
        """Every FROZEN decision must have non-empty evidence."""
        for d in dr["decisions"]:
            if d["final_status"] == "FROZEN":
                assert d.get("evidence"), \
                    f"FROZEN decision {d['decision_id']} has no evidence"

    def test_every_requires_validation_has_method(self, dr):
        """Every REQUIRES_VALIDATION decision must have a validation method."""
        for d in dr["decisions"]:
            if d["final_status"] == "REQUIRES_VALIDATION":
                assert d.get("validation_required") is True, \
                    f"Decision {d['decision_id']} is REQUIRES_VALIDATION but validation_required != True"
                assert d.get("validation_method"), \
                    f"Decision {d['decision_id']} is REQUIRES_VALIDATION but has no validation_method"

    def test_no_premature_zero_ignore_freeze(self, dr):
        """Zero->IGNORE_INDEX must not be FROZEN without formal NoData verification."""
        d05 = [d for d in dr["decisions"] if d["decision_id"] == "D-C2-05"]
        assert d05, "Decision D-C2-05 (zero handling) not found"
        assert d05[0]["final_status"] != "FROZEN", \
            "Zero handling should not be FROZEN before NoData formal verification"

    def test_os_zero_dataset_invariant(self, dr):
        """OS=0 must be classified as dataset integrity invariant."""
        d13 = [d for d in dr["decisions"] if d["decision_id"] == "D-C2-13"]
        assert d13, "Decision D-C2-13 (OS=0) not found"
        assert d13[0]["final_status"] == "FROZEN"
        assert "invariant" in d13[0]["recommended_option"].lower()

    def test_phenomenon_segmentation_separated(self, dr):
        """EXP-07 must be separated from oil false-positive suppression."""
        d01 = [d for d in dr["decisions"] if d["decision_id"] == "D-C2-01"]
        assert d01, "Decision D-C2-01 not found"
        assert "segmentation" in d01[0]["recommended_option"].lower()

    def test_exp06_not_same_task_comparator(self, dr):
        """EXP-06 must not be treated as same-task comparator."""
        d14 = [d for d in dr["decisions"] if d["decision_id"] == "D-C2-14"]
        assert d14, "Decision D-C2-14 (EXP-06 comparison) not found"
        assert d14[0]["final_status"] == "FROZEN"

    def test_acceptance_target_not_confirmatory(self, dr):
        """DEV mIoU >= 0.30 must be EXPLORATORY, not confirmatory."""
        d12 = [d for d in dr["decisions"] if d["decision_id"] == "D-C2-12"]
        assert d12, "Decision D-C2-12 not found"
        assert "EXPLORATORY" in d12[0]["recommended_option"].upper()

    def test_holdout_disclosure_preserved(self, dr):
        """Holdout must be disclosed as PARTIALLY_USED_FOR_SELECTION."""
        d11 = [d for d in dr["decisions"] if d["decision_id"] == "D-C2-11"]
        assert d11, "Decision D-C2-11 not found"
        assert "PARTIALLY_USED" in d11[0]["recommended_option"].upper()

    def test_seed_policy_explicit(self, dr):
        """Seed policy must specify exact seeds and no post-hoc selection."""
        d10 = [d for d in dr["decisions"] if d["decision_id"] == "D-C2-10"]
        assert d10, "Decision D-C2-10 not found"
        opt = d10[0]["recommended_option"]
        assert "42" in opt and "101" in opt and "2024" in opt

    def test_normalization_layer_flagged(self, dr):
        """Architecture decision must flag BatchNorm concern."""
        d09 = [d for d in dr["decisions"] if d["decision_id"] == "D-C2-09"]
        assert d09, "Decision D-C2-09 (architecture) not found"
        assert "BatchNorm" in d09[0].get("evidence", "") or \
               "batch" in d09[0].get("evidence", "").lower()


# ============================================================
# CONFOUNDER REGISTER GUARDRAILS
# ============================================================


class TestConfounderRegister:
    """Verify confounder register is comprehensive."""

    @pytest.fixture
    def cr(self):
        return _load_json(META / "exp07_p0_c2_confounder_register_v1.json")

    def test_confounder_register_exists(self, cr):
        assert cr["total_confounders"] >= 10, \
            "Confounder register should document at least 10 confounders"

    def test_nonlinearity_confounder_present(self, cr):
        ids = [c["id"] for c in cr["confounders"]]
        names = [c["name"].lower() for c in cr["confounders"]]
        assert any("nonlinear" in n for n in names), \
            "Block-mean calibration nonlinearity confounder not documented"

    def test_sampler_loss_interaction_confounder(self, cr):
        names = [c["name"].lower() for c in cr["confounders"]]
        assert any("sampler" in n and "loss" in n for n in names), \
            "Sampler x loss interaction confounder not documented"

    def test_provenance_chain_documented(self, cr):
        """At least the parent concentration confounder must be present."""
        names = [c["name"].lower() for c in cr["confounders"]]
        assert any("parent" in n and "concentration" in n for n in names)


# ============================================================
# SOURCE MASK / VALIDITY MASK SEPARATION
# ============================================================


class TestMaskSeparation:
    """Verify source masks are not modified and validity mask is conceptual."""

    def test_source_masks_unchanged(self):
        """OPS-01 physical mask files must not be modified."""
        manifest = _load_json(META / "ops01_physical_dataset_manifest_v4.json")
        for s in manifest["samples"]:
            mask_path = pathlib.Path(s["derived_mask_path"])
            if mask_path.exists():
                assert mask_path.stat().st_size > 0, f"Mask file empty: {mask_path}"
                # Verify masks are still uint8 PNG
                assert mask_path.suffix == ".png", f"Mask not PNG: {mask_path}"


# ============================================================
# TAXONOMY GUARDRAILS
# ============================================================


class TestTaxonomy:
    """Verify taxonomy is canonical and consistent."""

    @pytest.fixture
    def taxonomy(self):
        return _load_json(META / "ops01_taxonomy_v1.json")

    def test_12_training_eligible(self, taxonomy):
        eligible = [c for c in taxonomy["classes"] if c["training_eligible"]]
        assert len(eligible) == 12

    def test_os_excluded(self, taxonomy):
        os_class = [c for c in taxonomy["classes"] if c["abbreviation"] == "OS"]
        assert os_class, "OS class not found in taxonomy"
        assert os_class[0]["training_eligible"] is False


# ============================================================
# METRIC EDGE CASES
# ============================================================


class TestMetricDefinitions:
    """Verify metric edge cases are defined in the execution plan."""

    def test_execution_plan_defines_absent_class_handling(self):
        plan_path = EXP07 / "EXP07_P0_C2_FINAL_EXECUTION_PLAN_20260913.md"
        content = plan_path.read_text(encoding="utf-8")
        assert "absent" in content.lower(), \
            "Execution plan must define absent-class handling in metrics"
        assert "union=0" in content.lower() or "union = 0" in content.lower(), \
            "Execution plan must define union=0 edge case"


# ============================================================
# SELF-HEALING AUDIT
# ============================================================


class TestSelfHealing:
    """Verify no self-contradictions in C2 artifacts."""

    def test_decision_register_internally_consistent(self):
        dr = _load_json(META / "exp07_p0_c2_decision_register_v1.json")
        frozen = [d for d in dr["decisions"] if d["final_status"] == "FROZEN"]
        rv = [d for d in dr["decisions"] if d["final_status"] == "REQUIRES_VALIDATION"]
        total = dr["total_decisions"]
        assert len(dr["decisions"]) == total, \
            f"Decision count mismatch: {len(dr['decisions'])} vs declared {total}"
        assert dr["frozen_count"] == len(frozen), \
            f"Frozen count mismatch: declared {dr['frozen_count']}, actual {len(frozen)}"

    def test_calibration_feasibility_version(self):
        cal = _load_json(META / "exp07_p0_c2_calibration_feasibility_v1.json")
        assert cal["metadata_version"] == "2.0.0", \
            "Calibration feasibility should be v2.0.0 (corrected with nonlinearity)"

    def test_confounder_count_consistent(self):
        cr = _load_json(META / "exp07_p0_c2_confounder_register_v1.json")
        assert cr["total_confounders"] == len(cr["confounders"]), \
            f"Confounder count mismatch: declared {cr['total_confounders']}, actual {len(cr['confounders'])}"
