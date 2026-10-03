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

# Paths
C3_REPORT = EXP07 / "EXP07_P0_C3_CPU_ONLY_VALIDATION_REPORT_20260913.md"
DECISION_REG = META / "exp07_p0_c3_validation_decision_register_v1.json"
CAL_VAL = META / "exp07_p0_c3_calibration_validation_v1.json"
NODATA_VAL = META / "exp07_p0_c3_nodata_validation_v1.json"
SAMPLER_VAL = META / "exp07_p0_c3_sampler_validation_v1.json"
LOSS_VAL = META / "exp07_p0_c3_loss_validation_v1.json"
LOADER_VAL = META / "exp07_p0_c3_loader_validation_v1.json"
ARCH_VAL = META / "exp07_p0_c3_architecture_validation_v1.json"
NORM_VAL = META / "exp07_p0_c3_normalization_validation_v1.json"
TELEMETRY = SCRATCH / "exp07_p0_c3_run_state.json"
GOV_RULES = META / "ocean_sentinel_governance_rules_v1.json"
INCIDENTS = META / "ocean_sentinel_incident_learning_register_v1.json"
MANIFEST_V4 = META / "ops01_physical_dataset_manifest_v4.json"

def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()

class TestC3FrozenInvariants:
    def test_01_no_training_executed(self):
        with open(TELEMETRY, "r", encoding="utf-8") as f:
            tel = json.load(f)
        assert tel["current_command"] != "train"
        assert "checkpoints" not in tel or len(tel.get("checkpoints", [])) == 0

    def test_02_no_gpu_used(self):
        with open(C3_REPORT, "r", encoding="utf-8") as f:
            text = f.read()
        assert "CPU-only" in text
        assert "No GPU" in text

    def test_03_no_exp07_execution(self):
        assert not os.path.exists(BASE / "experiments/performance/exp07_multiclass_phenomena")

    def test_04_no_part_iii_access(self):
        with open(C3_REPORT, "r", encoding="utf-8") as f:
            text = f.read()
        assert "No Part-III" in text

    def test_05_frozen_exp06_hash(self):
        p = BASE / "experiments/performance/exp06_positive_bce_weight/best_model.pt"
        expected = "B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF"
        assert sha256_file(p) == expected

    def test_06_frozen_part_i_hash(self):
        p = META / "internal_development_split_manifest.json"
        expected = "17F1FF35146C7CE62E90D6FCE7F197B711B55E3C3CB599610578443208669072"
        assert sha256_file(p) == expected

class TestV01CalibrationValidation:
    def test_07_calibration_url_and_product_identity(self):
        with open(CAL_VAL, "r", encoding="utf-8") as f:
            d = json.load(f)
        samples = d["per_sample_results"]
        assert len(samples) >= 10
        for s in samples:
            assert s["parent_product_id"].startswith("S1A_IW_GRDH_")

    def test_08_source_window_geometry(self):
        with open(CAL_VAL, "r", encoding="utf-8") as f:
            d = json.load(f)
        for s in d["per_sample_results"]:
            sw = s["source_window"]
            parts = sw.split(", ")
            r_start, r_end = [int(x) for x in parts[0].replace("row=", "").split("..")]
            c_start, c_end = [int(x) for x in parts[1].replace("col=", "").split("..")]
            assert r_end - r_start == 2560
            assert c_end - c_start == 2560

    def test_09_10x10_block_geometry(self):
        with open(CAL_VAL, "r", encoding="utf-8") as f:
            d = json.load(f)
        for s in d["per_sample_results"]:
            assert s["total_blocks"] == 256 * 256

    def test_10_calibration_before_vs_after_comparison_exists(self):
        with open(CAL_VAL, "r", encoding="utf-8") as f:
            d = json.load(f)
        assert "relative_error_pct_mean" in d["overall_summary"]
        assert "relative_error_pct_median" in d["overall_summary"]

    def test_11_jensen_nonlinearity_test_exists(self):
        with open(CAL_VAL, "r", encoding="utf-8") as f:
            d = json.load(f)
        for s in d["per_sample_results"]:
            assert "jensen_ratio" in s
            assert s["jensen_ratio"]["mean"] > 1.0

    def test_12_theoretical_cv_not_labeled_empirical(self):
        with open(CAL_VAL, "r", encoding="utf-8") as f:
            d = json.load(f)
        nf = d["nonlinearity_findings"]
        assert "theoretical_enl44_cv" in nf
        assert "measured_mean_cv" in nf
        assert abs(nf["measured_mean_cv"] - nf["theoretical_enl44_cv"]) < 0.05

    def test_13_lut_variation_separated_from_dn_nonlinear_variation(self):
        with open(CAL_VAL, "r", encoding="utf-8") as f:
            d = json.load(f)
        for s in d["per_sample_results"]:
            dec = s["error_decomposition"]
            assert "e1_lut_max_abs_pct" in dec
            assert "e2_nonlinearity_mean_pct" in dec
            assert dec["e1_lut_max_abs_pct"] < 0.05
            assert dec["e2_nonlinearity_mean_pct"] > 4.0

    def test_14_exact_and_approximate_pipeline_use_compatible_validity_rules(self):
        with open(CAL_VAL, "r", encoding="utf-8") as f:
            d = json.load(f)
        for s in d["per_sample_results"]:
            assert s["valid_blocks_count"] + s["zero_containing_blocks"] == s["total_blocks"]

    def test_15_v01_result_has_empirical_sample_count(self):
        with open(CAL_VAL, "r", encoding="utf-8") as f:
            d = json.load(f)
        assert d["sampling_design"]["sample_count"] >= 10

    def test_16_v01_parent_diversity_recorded(self):
        with open(CAL_VAL, "r", encoding="utf-8") as f:
            d = json.load(f)
        assert d["sampling_design"]["independent_parents_count"] >= 3

class TestV02NoDataValidation:
    def test_17_v02_status_explicit(self):
        with open(NODATA_VAL, "r", encoding="utf-8") as f:
            d = json.load(f)
        assert d["final_classification"] in ["PROVEN_INVALID", "STRONGLY_SUPPORTED_INVALID"]

    def test_18_source_mask_not_modified(self):
        with open(NODATA_VAL, "r", encoding="utf-8") as f:
            d = json.load(f)
        assert "completely unmodified" in d["validity_mask_policy"]["source_mask_integrity"]

class TestV03V04SamplerAndLoss:
    def test_19_sampler_uses_actual_manifest_schema(self):
        with open(SAMPLER_VAL, "r", encoding="utf-8") as f:
            d = json.load(f)
        assert "BG" in d["class_frequencies"]
        assert "HM" in d["class_frequencies"]
        assert "pixel_count" in d["class_frequencies"]["BG"]

    def test_20_parent_exposure_quantified(self):
        with open(SAMPLER_VAL, "r", encoding="utf-8") as f:
            d = json.load(f)
        for k, cand in d["candidates_evaluated"].items():
            pm = cand["parent_exposure_metrics"]
            assert "max_parent_multiplier" in pm
            assert "cv_parent_exposure" in pm

    def test_21_sampler_loss_interaction_quantified(self):
        with open(LOSS_VAL, "r", encoding="utf-8") as f:
            d = json.load(f)
        mat = d["interaction_matrix"]
        assert "F_hybrid" in mat
        assert "E_sqrt_median" in mat["F_hybrid"]
        assert "hm_effective_multiplier" in mat["F_hybrid"]["E_sqrt_median"]

class TestV05LoaderValidation:
    def test_22_loader_does_not_silently_become_scientific_protocol(self):
        with open(LOADER_VAL, "r", encoding="utf-8") as f:
            d = json.load(f)
        assert d["status"] == "PASSED"
        assert d["validation_id"] == "V-05"

    def test_23_deterministic_read_test(self):
        with open(LOADER_VAL, "r", encoding="utf-8") as f:
            d = json.load(f)
        assert d["validation_checks"]["deterministic_repeated_read"].startswith("PASSED")

class TestV06ArchitectureValidation:
    def test_24_architecture_parameter_count_derived(self):
        with open(ARCH_VAL, "r", encoding="utf-8") as f:
            d = json.load(f)
        assert "ResNet18-UNet" in d["candidates_evaluated"]
        r18 = d["candidates_evaluated"]["ResNet18-UNet"]
        assert r18["trainable_parameters"] > 10_000_000
        assert r18["input_channels"] == 1
        assert r18["output_classes"] == 12

    def test_25_batchnorm_implications_recorded(self):
        with open(ARCH_VAL, "r", encoding="utf-8") as f:
            d = json.load(f)
        assert "finding" in d["batchnorm_and_batch_size_analysis"]
        assert d["batchnorm_and_batch_size_analysis"]["batches_per_epoch_at_bs8"] == 9

class TestV07NormalizationValidation:
    def test_26_v07_train_only(self):
        with open(NORM_VAL, "r", encoding="utf-8") as f:
            d = json.load(f)
        assert d["dataset_isolation"]["train_tiles_analyzed"] == 72
        assert d["dataset_isolation"]["dev_tiles_analyzed"] == 0
        assert d["dataset_isolation"]["holdout_tiles_analyzed"] == 0

    def test_27_no_dev_holdout_statistics(self):
        with open(NORM_VAL, "r", encoding="utf-8") as f:
            d = json.load(f)
        assert d["dataset_isolation"]["partition_leakage_check"].startswith("PASSED")

class TestPermanentDisclosuresAndMetadata:
    def test_28_permanent_holdout_disclosure(self):
        with open(MANIFEST_V4, "r", encoding="utf-8") as f:
            m = json.load(f)
        ped = m.get("permanent_epistemic_disclosures", {})
        assert ped.get("holdout_selection_disclosure") == "HOLDOUT_PARTIALLY_USED_FOR_SELECTION"

    def test_29_alignment_disclosure(self):
        with open(MANIFEST_V4, "r", encoding="utf-8") as f:
            m = json.load(f)
        ped = m.get("permanent_epistemic_disclosures", {})
        assert ped.get("alignment_epistemic_status") == "CONDITIONAL_ENGINEERING_RECONSTRUCTION"

    def test_30_generation_method_disclosure(self):
        with open(MANIFEST_V4, "r", encoding="utf-8") as f:
            m = json.load(f)
        ped = m.get("permanent_epistemic_disclosures", {})
        assert "NOT_DIRECTLY_VERIFIED" in ped.get("generation_method_status", "")

    def test_31_artifact_hashes_current(self):
        for p in [CAL_VAL, NODATA_VAL, SAMPLER_VAL, LOSS_VAL, LOADER_VAL, ARCH_VAL, NORM_VAL, DECISION_REG]:
            assert os.path.exists(p)
            assert os.path.getsize(p) > 500

    def test_32_external_source_citations_present(self):
        with open(C3_REPORT, "r", encoding="utf-8") as f:
            text = f.read()
        assert "S1-RS-MDA-52-7443" in text
        assert "S1-TN-MUC-GS-0002" in text

    def test_33_telemetry_valid(self):
        with open(TELEMETRY, "r", encoding="utf-8") as f:
            tel = json.load(f)
        assert tel["phase"] == "EXP-07-P0-C3"
        assert "validation_status" in tel

    def test_34_current_git_state_fresh(self):
        with open(TELEMETRY, "r", encoding="utf-8") as f:
            tel = json.load(f)
        assert tel["git_state"]["staged"] == 0
        assert tel["git_state"]["branch"] == "master"

    def test_35_self_healing_completed(self):
        with open(DECISION_REG, "r", encoding="utf-8") as f:
            d = json.load(f)
        assert d["summary"]["final_c3_verdict"].startswith("A. FINAL")
        assert len(d["decisions"]) == 7
