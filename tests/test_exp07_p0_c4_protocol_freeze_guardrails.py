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

# Authoritative paths
C4_CONTRACT_MD = EXP07 / "EXP07_P0_C4_FINAL_PROTOCOL_FREEZE_IMPLEMENTATION_CONTRACT_20260913.md"
C4_PROTOCOL_JSON = META / "exp07_p0_c4_protocol_freeze_v1.json"
MANIFEST_V4 = META / "ops01_physical_dataset_manifest_v4.json"
SPLIT_MANIFEST = META / "internal_development_split_manifest.json"
EXP06_MODEL = BASE / "experiments" / "performance" / "exp06_positive_bce_weight" / "best_model.pt"
TAXONOMY_V1 = META / "ops01_taxonomy_v1.json"
TELEMETRY = SCRATCH / "exp07_p0_c4_run_state.json"

def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()

class TestC4FrozenHashes:
    def test_01_frozen_exp06_hash(self):
        expected = "B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF"
        assert sha256_file(EXP06_MODEL) == expected

    def test_02_frozen_part_i_hash(self):
        expected = "17F1FF35146C7CE62E90D6FCE7F197B711B55E3C3CB599610578443208669072"
        assert sha256_file(SPLIT_MANIFEST) == expected

    def test_03_frozen_ops01_v4_manifest_hash(self):
        expected = "FF1680C9135EF5CD9C7B77FBC8373953F9924BD5BE2830617EB0EF386C8DC85E"
        assert sha256_file(MANIFEST_V4) == expected

class TestC4ContractArtifactsExist:
    def test_04_final_contract_md_exists(self):
        assert os.path.exists(C4_CONTRACT_MD)
        assert os.path.getsize(C4_CONTRACT_MD) > 3000

    def test_05_machine_readable_protocol_json_exists(self):
        assert os.path.exists(C4_PROTOCOL_JSON)
        assert os.path.getsize(C4_PROTOCOL_JSON) > 2000

    def test_06_required_json_top_level_fields_exist(self):
        with open(C4_PROTOCOL_JSON, "r", encoding="utf-8") as f:
            d = json.load(f)
        required_fields = [
            "experiment_identity",
            "radiometric_domain",
            "validity_and_nodata_policy",
            "dataset_interface",
            "taxonomy_and_class_mapping",
            "sampler_specification",
            "loss_specification",
            "architecture_specification",
            "normalization_pipeline",
            "augmentation_policy",
            "multiclass_evaluation_contract",
            "holdout_epistemic_status"
        ]
        for field in required_fields:
            assert field in d, f"Missing required top-level JSON field: {field}"

class TestC4TaxonomyAndClasses:
    def test_07_class_count_is_12(self):
        with open(C4_PROTOCOL_JSON, "r", encoding="utf-8") as f:
            d = json.load(f)
        assert d["taxonomy_and_class_mapping"]["total_training_classes"] == 12
        assert len(d["taxonomy_and_class_mapping"]["dense_indices"]) == 12

    def test_08_dense_class_indices_0_to_11(self):
        with open(C4_PROTOCOL_JSON, "r", encoding="utf-8") as f:
            d = json.load(f)
        indices = [v["dense_index"] for v in d["taxonomy_and_class_mapping"]["dense_indices"].values()]
        assert sorted(indices) == list(range(12))

    def test_09_hm_taxonomy_identity_preserved(self):
        with open(C4_PROTOCOL_JSON, "r", encoding="utf-8") as f:
            d = json.load(f)
        hm_entry = d["taxonomy_and_class_mapping"]["dense_indices"]["11"]
        assert hm_entry["abbreviation"] == "HM"
        assert hm_entry["class_name"] == "Artificial / Anthropogenic Objects"
        assert hm_entry["source_label_id"] == 13
        assert "Vessel" not in hm_entry["class_name"]

    def test_10_os_training_exclusion(self):
        with open(C4_PROTOCOL_JSON, "r", encoding="utf-8") as f:
            d = json.load(f)
        excluded = [x["abbreviation"] for x in d["taxonomy_and_class_mapping"]["excluded_classes"]]
        assert "OS" in excluded
        assert "OS" not in [v["abbreviation"] for v in d["taxonomy_and_class_mapping"]["dense_indices"].values()]

class TestC4DatasetInterfaceAndValidity:
    def test_11_input_shape_contract(self):
        with open(C4_PROTOCOL_JSON, "r", encoding="utf-8") as f:
            d = json.load(f)
        assert d["dataset_interface"]["input_shape"] == "[B, 1, 256, 256]"
        assert d["dataset_interface"]["input_dtype"] == "float32"

    def test_12_output_shape_contract(self):
        with open(C4_PROTOCOL_JSON, "r", encoding="utf-8") as f:
            d = json.load(f)
        assert d["dataset_interface"]["output_shape"] == "[B, 12, 256, 256]"
        assert d["dataset_interface"]["output_dtype"] == "float32"
        assert "logits" in d["dataset_interface"]["output_semantics"]

    def test_13_validity_policy_and_ignore_index(self):
        with open(C4_PROTOCOL_JSON, "r", encoding="utf-8") as f:
            d = json.load(f)
        vp = d["validity_and_nodata_policy"]
        assert vp["validity_mask_formula"] == "raw_image > 0"
        assert vp["ignore_index"] == -100
        assert "completely unmodified" in vp["source_mask_integrity"]

class TestC4RadiometricAndNormalization:
    def test_14_radiometric_truth_statement_present(self):
        with open(C4_PROTOCOL_JSON, "r", encoding="utf-8") as f:
            d = json.load(f)
        statement = d["radiometric_domain"]["truth_statement"]
        assert "Physical Sentinel-1 radiometric calibration is NOT identical" in statement
        assert d["radiometric_domain"]["epistemic_status"] == "EMPIRICALLY_CHARACTERIZED_APPROXIMATE_CALIBRATION_PATHWAY"

    def test_15_calibration_prohibitions_explicit(self):
        with open(C4_PROTOCOL_JSON, "r", encoding="utf-8") as f:
            d = json.load(f)
        prohibitions = d["radiometric_domain"]["prohibitions"]
        assert any("calibration is exact" in p for p in prohibitions)
        assert any("globally bounded at 20-30%" in p for p in prohibitions)
        assert any("instrument accuracy" in p for p in prohibitions)

    def test_16_normalization_constants(self):
        with open(C4_PROTOCOL_JSON, "r", encoding="utf-8") as f:
            d = json.load(f)
        norm = d["normalization_pipeline"]
        assert norm["train_mean"] == 4.2756
        assert norm["train_std"] == 0.3866
        assert "4.2756" in norm["formula"]
        assert "0.3866" in norm["formula"]

    def test_17_normalization_ordering_frozen(self):
        with open(C4_PROTOCOL_JSON, "r", encoding="utf-8") as f:
            d = json.load(f)
        seq = d["normalization_pipeline"]["operation_sequence"]
        assert "raw input" in seq[0]
        assert "validity_mask" in seq[1]
        assert "log1p" in seq[2]
        assert "standardize" in seq[3]

class TestC4SamplerAndLoss:
    def test_18_exact_70_30_hybrid_sampler_specification(self):
        with open(C4_PROTOCOL_JSON, "r", encoding="utf-8") as f:
            d = json.load(f)
        samp = d["sampler_specification"]
        assert "Candidate F" in samp["candidate"]
        assert "70% Parent-Balanced" in samp["candidate"]
        assert "30% Class-Presence" in samp["candidate"]
        assert "0.70 * p_parent + 0.30 * p_presence" in samp["hybrid_formula"]
        assert samp["samples_per_epoch"] == 72
        assert samp["seeds"] == [42, 101, 2024]

    def test_19_exact_loss_formula_and_weights(self):
        with open(C4_PROTOCOL_JSON, "r", encoding="utf-8") as f:
            d = json.load(f)
        loss = d["loss_specification"]
        assert "sqrt(median_frequency / class_frequency)" in loss["weight_formula"]
        assert loss["ignore_index"] == -100
        assert len(loss["class_weights"]) == 12
        # Check specific verified values
        assert abs(loss["class_weights"]["BG"] - 0.2726) < 0.005
        assert abs(loss["class_weights"]["HM"] - 12.151) < 0.05
        assert loss["double_correction_risk"] == "LOW"

class TestC4ArchitectureAndAugmentation:
    def test_20_architecture_contract_and_parameters(self):
        with open(C4_PROTOCOL_JSON, "r", encoding="utf-8") as f:
            d = json.load(f)
        arch = d["architecture_specification"]
        assert arch["model_name"] == "ResNet18-UNet"
        assert arch["input_channels"] == 1
        assert arch["output_classes"] == 12
        assert arch["trainable_parameters"] == 14310860
        assert arch["total_parameters"] == 14322636
        assert arch["batchnorm_layers_count"] == 30
        assert arch["normalization_contract_option"] == "OPTION_B"

    def test_21_augmentation_policy_state(self):
        with open(C4_PROTOCOL_JSON, "r", encoding="utf-8") as f:
            d = json.load(f)
        aug = d["augmentation_policy"]
        assert aug["baseline_policy"] == "BASELINE_IDENTITY_NO_AUGMENTATION"
        assert aug["classifications"]["rotations_90_deg"]["status"] == "DISALLOWED"
        assert aug["classifications"]["brightness_contrast_jitter"]["status"] == "DISALLOWED"
        assert aug["classifications"]["vertical_flip_azimuth"]["status"] == "SAFE"

class TestC4EvaluationAndGovernance:
    def test_22_binary_threshold_prohibition(self):
        with open(C4_PROTOCOL_JSON, "r", encoding="utf-8") as f:
            d = json.load(f)
        ev = d["multiclass_evaluation_contract"]
        assert ev["prediction_rule"] == "argmax(logits, dim=1)"
        assert ev["binary_thresholding"] == "STRICTLY_PROHIBITED"
        assert "tau=0.22" in ev["exp06_tau_reuse"]

    def test_23_holdout_disclosure(self):
        with open(C4_PROTOCOL_JSON, "r", encoding="utf-8") as f:
            d = json.load(f)
        ho = d["holdout_epistemic_status"]
        assert ho["status"] == "HOLDOUT_PARTIALLY_USED_FOR_SELECTION"
        assert "pristine" in ho["prohibited_descriptions"]
        assert "independent benchmark" in ho["prohibited_descriptions"]

    def test_24_no_part_iii_access_or_references(self):
        with open(C4_CONTRACT_MD, "r", encoding="utf-8") as f:
            text = f.read()
        assert "Part-III" in text
        assert "No Part-III" in text

    def test_25_telemetry_consistent(self):
        with open(TELEMETRY, "r", encoding="utf-8") as f:
            tel = json.load(f)
        assert tel["phase"] == "EXP-07-P0-C4"
        assert tel["git_state"]["staged"] == 0
        assert tel["git_state"]["branch"] == "master"
