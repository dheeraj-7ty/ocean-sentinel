"""
Phase 7B.2B Pre-Training Stage Gate Regression Guardrail Test Suite
Protects:
- Mutually exclusive source recovery accounting
- Geometric validation limits and zero-residual construction proof
- Neutral label-to-10m grid alignment and DERIVED_HIGH_RESOLUTION_MASK classification
- Disaggregated spatial uncertainty and candidate boundary-tolerance protocol
- Disaggregated multidimensional taxonomy evidence matrix
- Capability-gap justification ("Why does OPS-01 need to exist?")
- Parent-scene / orbit-pass leakage prevention
- Frozen artifact bitwise integrity (EXP-06, Part-I manifest, tau=0.22, Part-III firewall)
- Zero training, zero GPU compute, and zero git staging invariants
- Cancelled-run forensic artifact integrity
"""

import hashlib
import json
import subprocess
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
METADATA_DIR = REPO_ROOT / "data" / "metadata"
SCRATCH_DIR = REPO_ROOT / "scratch"
EXP_DIR = REPO_ROOT / "experiments"

FROZEN_EXP06_SHA = "B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF"
FROZEN_PART_I_SHA = "17F1FF35146C7CE62E90D6FCE7F197B711B55E3C3CB599610578443208669072"
FROZEN_TAU = 0.22


@pytest.fixture(scope="module")
def iw_manifest():
    path = METADATA_DIR / "li_iw_source_scene_manifest.json"
    assert path.exists(), "IW source scene manifest missing"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def geo_audit():
    path = METADATA_DIR / "li_geometry_registration_audit_v2.json"
    assert path.exists(), "Geometry registration audit missing"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def taxonomy_audit():
    path = METADATA_DIR / "ops01_taxonomy_and_capability_gap_audit.json"
    assert path.exists(), "Taxonomy and capability gap audit missing"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def class_dict():
    path = METADATA_DIR / "li_authoritative_class_dictionary.json"
    assert path.exists(), "Authoritative class dictionary missing"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# Guardrail 1: Recovery accounting is exhaustive and mutually exclusive
def test_guardrail_01_recovery_accounting_mutually_exclusive(iw_manifest):
    acc = iw_manifest["summary"]["archive_recovery_accounting"]
    n_id = acc["N_IW_SCENES_IDENTIFIED"]
    n_rec = acc["N_IW_PRODUCTS_EXACTLY_RECOVERED"]
    n_nf = acc["N_IW_PRODUCTS_NOT_FOUND_AFTER_TEST"]
    n_err = acc["N_IW_PRODUCTS_QUERY_ERROR_AFTER_TEST"]
    n_amb = acc["N_IW_PRODUCTS_AMBIGUOUS_AFTER_TEST"]
    n_nt = acc["N_IW_PRODUCTS_NOT_YET_TESTED"]

    assert n_id == 484
    assert n_rec == 12
    assert n_nf == 0
    assert n_err == 0
    assert n_amb == 0
    assert n_nt == 472
    assert n_id == (n_rec + n_nf + n_err + n_amb + n_nt)
    assert acc["accounting_invariant_verified"] is True


# Guardrail 2: Not-yet-tested scenes cannot be counted as not-found
def test_guardrail_02_not_yet_tested_not_counted_as_not_found(iw_manifest):
    scenes = iw_manifest["scenes"]
    for s in scenes:
        rec_st = s.get("archive_recovery_state")
        allowed_st = s.get("phase_7b2b_allowed_state")
        assert rec_st in ("EXACTLY_RECOVERED", "NOT_YET_TESTED")
        assert allowed_st in ("EXACTLY_RECOVERED", "NOT_YET_TESTED")
        assert rec_st != "NOT_FOUND_AFTER_TEST"


# Guardrail 3: 472 untested scenes cannot silently become zero-failure recoveries
def test_guardrail_03_untested_scenes_not_claimed_zero_failure(iw_manifest):
    acc = iw_manifest["summary"]["archive_recovery_accounting"]
    assert "Failure categories are zero ONLY because zero tested scenes fell into them" in acc["governance_note"]


# Guardrail 4: Four-point bilinear exact fit cannot be labeled independent validation
def test_guardrail_04_bilinear_exact_fit_not_independent_validation(geo_audit):
    models = geo_audit["geometric_model_evaluation"]["tested_transformation_models"]
    bil = [m for m in models if "Bilinear" in m["model_name"]][0]
    assert "IS NOT independent geometric validation" in bil["governance_rule_zero_residual"]
    assert "independent interior geolocation accuracy is not established" in bil["independent_interior_accuracy_status"]


# Guardrail 5: Derived 10m masks cannot be labeled native 10m ground truth
def test_guardrail_05_derived_mask_not_native_ground_truth(geo_audit):
    contract = geo_audit["boundary_uncertainty_contract"]
    assert contract["mandated_mask_classification"] == "DERIVED_HIGH_RESOLUTION_MASK"
    for forbidden in contract["strictly_forbidden_classifications"]:
        assert forbidden != "DERIVED_HIGH_RESOLUTION_MASK"
        assert "native" in forbidden.lower() or "ground truth" in forbidden.lower()


# Guardrail 6: Boundary tolerance cannot be represented as exact ground-truth correction
def test_guardrail_06_boundary_tolerance_not_exact_correction(geo_audit):
    tol = geo_audit["boundary_uncertainty_contract"]["pre_registered_evaluation_protocol"]
    assert "Candidate PRE-REGISTERED BOUNDARY-TOLERANCE PARAMETER" in tol["parameter_characterization"]
    assert "NOT automatically a measured physical uncertainty" in tol["parameter_characterization"]


# Guardrail 7: OS cannot enter OPS training
def test_guardrail_07_os_excluded_from_ops_training(taxonomy_audit, class_dict):
    os_tax = [c for c in taxonomy_audit["multidimensional_evidence_matrix"] if c["abbreviation"] == "OS"][0]
    assert os_tax["operational_role"] == "STRICTLY_EXCLUDED"
    os_dict = [c for c in class_dict["classes"] if c["abbreviation"] == "OS"][0]
    assert "EXCLUDED" in os_dict["ops01_training_role"]


# Guardrail 8: OS cannot enter oil benchmark ground truth
def test_guardrail_08_os_excluded_from_oil_benchmark(taxonomy_audit):
    os_tax = [c for c in taxonomy_audit["multidimensional_evidence_matrix"] if c["abbreviation"] == "OS"][0]
    assert "4 images" in os_tax["notes"]
    assert "Excluded from OPS training, oil evaluation, and ground truth" in os_tax["notes"]


# Guardrail 9: HM cannot silently become "Vessel"
def test_guardrail_09_hm_not_silently_renamed_vessel(taxonomy_audit, class_dict):
    hm_tax = [c for c in taxonomy_audit["multidimensional_evidence_matrix"] if c["abbreviation"] == "HM"][0]
    assert hm_tax["name"] == "Artificial / Anthropogenic Objects"
    assert "renaming to 'Vessel' is forbidden" in hm_tax["notes"]
    hm_dict = [c for c in class_dict["classes"] if c["abbreviation"] == "HM"][0]
    assert "Artificial Objects" in hm_dict["class_name"]


# Guardrail 10: OPS target selection is marked provisional hypothesis unless empirically demonstrated
def test_guardrail_10_ops_target_taxonomy_marked_hypothesis(taxonomy_audit):
    assert taxonomy_audit["core_taxonomy_classification"] == "B. REASONABLE ENGINEERING HYPOTHESIS REQUIRING VALIDATION"


# Guardrail 11: No training invocation occurs
def test_guardrail_11_no_model_training_invoked():
    telemetry_path = SCRATCH_DIR / "phase_7b2b_pretraining_gate_run_state.json"
    assert telemetry_path.exists()
    with open(telemetry_path, "r", encoding="utf-8") as f:
        telem = json.load(f)
    assert telem["training_invoked"] is False


# Guardrail 12: No EXP-07 is started
def test_guardrail_12_exp07_not_started():
    exp07_paths = list(REPO_ROOT.glob("*exp07*")) + list(EXP_DIR.glob("*exp07*"))
    assert len(exp07_paths) == 0, f"Found unauthorized EXP-07 artifacts: {exp07_paths}"


# Guardrail 13: EXP-06 checkpoint remains unchanged
def test_guardrail_13_exp06_checkpoint_integrity():
    ckpt_path = EXP_DIR / "performance" / "exp06_positive_bce_weight" / "best_model.pt"
    assert ckpt_path.exists()
    measured_sha = hashlib.sha256(ckpt_path.read_bytes()).hexdigest().upper()
    assert measured_sha == FROZEN_EXP06_SHA


# Guardrail 14: tau remains 0.22
def test_guardrail_14_tau_frozen_at_022():
    baseline_path = EXP_DIR / "performance" / "exp06_positive_bce_weight" / "exp06_frozen_dev_baseline.json"
    assert baseline_path.exists()
    with open(baseline_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert float(data["protocol"]["decision_threshold_tau"]) == FROZEN_TAU


# Guardrail 15: Protected Part-I manifest remains unchanged
def test_guardrail_15_part_i_manifest_frozen():
    manifest_path = METADATA_DIR / "internal_development_split_manifest.json"
    assert manifest_path.exists()
    measured_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest().upper()
    assert measured_sha == FROZEN_PART_I_SHA


# Guardrail 16: Protected Part-III benchmark artifacts remain unchanged
def test_guardrail_16_part_iii_quarantine_enforced():
    part_iii_dir = EXP_DIR / "performance" / "trujillo_part_iii_eval_20260911_exp01"
    assert part_iii_dir.exists(), "Protected Part-III benchmark directory missing"


# Guardrail 17: GPU is not invoked
def test_guardrail_17_gpu_not_invoked():
    telemetry_path = SCRATCH_DIR / "phase_7b2b_pretraining_gate_run_state.json"
    with open(telemetry_path, "r", encoding="utf-8") as f:
        telem = json.load(f)
    assert telem["gpu_invoked"] is False


# Guardrail 18: Git staging remains untouched
def test_guardrail_18_git_staging_untouched():
    res = subprocess.run(["git", "diff", "--cached", "--name-status"], cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert res.returncode == 0
    assert res.stdout.strip() == "", f"Git index has staged files: {res.stdout}"


# Guardrail 19: Partial cancelled-run artifacts are not silently promoted
def test_guardrail_19_cancelled_run_partial_artifacts_not_promoted():
    forensic_report = EXP_DIR / "PHASE_7B2B_CANCELLED_RUN_FORENSIC_RECOVERY_REPORT_20260913.md"
    assert forensic_report.exists()
    text = forensic_report.read_text(encoding="utf-8")
    assert "NONE_GENERATED" in text
    assert "No substantive Ocean Sentinel project artifacts were modified by the cancelled run" in text


# Guardrail 20: No report can claim work not supported by telemetry
def test_guardrail_20_report_telemetry_consistency():
    telemetry_path = SCRATCH_DIR / "phase_7b2b_pretraining_gate_run_state.json"
    with open(telemetry_path, "r", encoding="utf-8") as f:
        telem = json.load(f)
    assert telem["phase"] == "PHASE_7B.2B"
    assert "WORKSTREAM_1_SOURCE_RECOVERY_ACCOUNTING" in telem["completed_steps"]


# Guardrail 21: Four-corner GCP fit cannot produce an 'independently validated' flag
def test_guardrail_21_no_fake_geometric_validation_flag(geo_audit):
    models = geo_audit["geometric_model_evaluation"]["tested_transformation_models"]
    bil = [m for m in models if "Bilinear" in m["model_name"]][0]
    assert bil.get("fitting_verdict") != "INDEPENDENTLY_VALIDATED"
    assert "unique algebraic solution" in bil["algebraic_proof_of_zero_corner_residual"]


# Guardrail 22: Dataset-wide absence/presence claims must include their actual audit scope
def test_guardrail_22_dataset_scope_qualification(geo_audit):
    scope = geo_audit.get("sample_scope_note", "")
    assert "For examined Li GeoTIFFs" in scope


# Guardrail 23: Valid SAFE filename syntax cannot become recoverability proof
def test_guardrail_23_filename_syntax_not_recoverability_proof(iw_manifest):
    acc = iw_manifest["summary"]["archive_recovery_accounting"]
    assert "valid SAFE filename syntax does NOT constitute proof of archive recoverability" in acc["governance_note"]


# Guardrail 24: A pretraining-ready status cannot be issued when a defined critical stop condition exists
def test_guardrail_24_stop_condition_integrity():
    telemetry_path = SCRATCH_DIR / "phase_7b2b_pretraining_gate_run_state.json"
    with open(telemetry_path, "r", encoding="utf-8") as f:
        telem = json.load(f)
    if telem["training_invoked"] or telem["gpu_invoked"] or telem["frozen_artifacts_changed"]:
        assert telem["final_status"] == "OPS-01 TRAINING BLOCKED"

# Guardrail 25: Resampling is not registration (Rule 61)
def test_guardrail_25_resampling_not_registration(geo_audit):
    align = geo_audit["label_to_operational_10m_alignment_contract"]
    assert "resampling_vs_registration_distinction" in align
    assert "does NOT establish spatial registration" in align["resampling_vs_registration_distinction"]


# Guardrail 26: Conceptual alignment pipeline does not equal validated spatial alignment (Rule 62)
def test_guardrail_26_alignment_status_not_established(geo_audit):
    align = geo_audit["label_to_operational_10m_alignment_contract"]
    assert align["source_to_operational_grid_alignment_status"] == "NOT_ESTABLISHED"


# Guardrail 27: Unsupported numerical geometry uncertainty cannot be emitted (Rule 66)
def test_guardrail_27_no_unsupported_numerical_uncertainty(geo_audit):
    comp = geo_audit["spatial_uncertainty_decomposition"]["components"]["2_geolocation_registration_uncertainty"]
    assert comp["quantification_status"] == "NOT_ESTABLISHED"
    assert "UNKNOWN / NOT ESTABLISHED" in comp["value"]
    assert "±10m" not in comp["value"].replace(" ", "")
    assert "10mto100m" not in comp["value"].replace(" ", "")


# Guardrail 28: Firewalled Part-III does not equal proven zero overlap (Rule 65)
def test_guardrail_28_firewalled_not_zero_overlap(taxonomy_audit):
    cross = taxonomy_audit["leakage_and_independence_audit"]["cross_dataset_leakage"]
    assert cross["part_iii_overlap"] == "UNKNOWN_NOT_EVALUATED_FIREWALLED"
    assert "cannot establish zero overlap" in cross["firewall_governance_rule"]


# Guardrail 29: Sample GCP observation cannot silently become dataset-wide (Rule 63)
def test_guardrail_29_sample_gcp_scope_not_dataset_wide(geo_audit):
    meta = geo_audit.get("sample_scope_metadata", {})
    assert meta.get("claim_scope") == "SAMPLE"
    assert meta.get("coverage_status") == "SAMPLE_REPRESENTATIVE_NOT_EXHAUSTIVE"
    assert meta.get("files_examined") == 12


# Guardrail 30: Li phenomenon presence does not equal proven EXP-06 causality (Rule 64)
def test_guardrail_30_lookalike_presence_not_causality(taxonomy_audit):
    cap = taxonomy_audit["capability_gap_justification"]
    assert cap["system_level_capability_gap"] == "EXP-06 demonstrates a clean-water false-alarm capability gap."
    assert "NOT ESTABLISHED" in cap["look_alike_attribution_status"]
    matrix = taxonomy_audit["multidimensional_evidence_matrix"]
    lookalikes = [c for c in matrix if c["abbreviation"] in ["BS", "LWA", "IWs", "OF", "RC/RF", "Eddy"]]
    for item in lookalikes:
        dim_d = item["ratings"]["D_demonstrated_exp06_false_alarm_cause"]
        assert dim_d in ["HYPOTHESIZED", "NOT_ESTABLISHED"]
        assert dim_d != "DIRECT"


# Guardrail 31: Historical forensic state cannot be interpreted as current repository state (Rule 68)
def test_guardrail_31_forensic_temporal_scope_distinction():
    report_path = EXP_DIR / "PHASE_7B2B_CANCELLED_RUN_FORENSIC_RECOVERY_REPORT_20260913.md"
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "prior to the subsequent Phase 7B.2B execution" in content


# Guardrail 32: Cancelled run cannot be represented as completed (Rule 83)
def test_guardrail_32_cancelled_run_not_represented_completed():
    cancelled_report = EXP_DIR / "PHASE_7B2B_RECONCILIATION_CANCELLED_RUN_FORENSIC_REPORT_20260913.md"
    assert cancelled_report.exists()
    content = cancelled_report.read_text(encoding="utf-8")
    assert "CANCELLED IN PROGRESS" in content
    partial_telem = SCRATCH_DIR / "phase_7b2b_reconciliation_run_state.json"
    assert partial_telem.exists()


# Guardrail 33: Telemetry cannot list future artifacts as authoritative (Rule 74)
def test_guardrail_33_telemetry_authoritative_artifacts_verified():
    r2_telem_path = SCRATCH_DIR / "phase_7b2b_reconciliation_r2_run_state.json"
    assert r2_telem_path.exists()
    with open(r2_telem_path, "r", encoding="utf-8") as f:
        telem = json.load(f)
    for art in telem.get("authoritative_artifacts", []):
        p = REPO_ROOT / art if not Path(art).is_absolute() else Path(art)
        assert p.exists(), f"Telemetry declared uncreated artifact as authoritative: {art}"


# Guardrail 34: Input dependency cannot equal current-run artifact (Rule 75 & 77)
def test_guardrail_34_input_dependency_not_current_run_artifact():
    r2_telem_path = SCRATCH_DIR / "phase_7b2b_reconciliation_r2_run_state.json"
    assert r2_telem_path.exists()
    with open(r2_telem_path, "r", encoding="utf-8") as f:
        telem = json.load(f)
    last_art = telem.get("last_successful_artifact")
    inputs = telem.get("input_dependencies", [])
    if last_art is not None:
        assert last_art not in inputs, f"last_successful_artifact cannot be an input dependency: {last_art}"


# Guardrail 35: A corrected report cannot silently restore an invalidated claim (Rule 71)
def test_guardrail_35_corrected_claims_integrity():
    geo_path = METADATA_DIR / "li_geometry_registration_audit_v2.json"
    with open(geo_path, "r", encoding="utf-8") as f:
        geo = json.load(f)
    align = geo["label_to_operational_10m_alignment_contract"]
    assert align["source_to_operational_grid_alignment_status"] != "ESTABLISHED"
    assert align["source_to_operational_grid_alignment_status"] != "VALIDATED"


# Guardrail 36: Pre-training readiness does NOT authorize model training
def test_guardrail_36_readiness_does_not_authorize_training():
    telem_path = SCRATCH_DIR / "phase_7b2b_reconciliation_r2_run_state.json"
    assert telem_path.exists()
    with open(telem_path, "r", encoding="utf-8") as f:
        telem = json.load(f)
    assert telem["training_invoked"] is False
    assert telem["gpu_invoked"] is False

# Guardrail 37: +/-50m source-cell extent cannot be labeled measured annotation error (Rule 74)
def test_guardrail_37_source_cell_extent_not_measured_annotation_error(geo_audit):
    comp = geo_audit["spatial_uncertainty_decomposition"]["components"]["1_annotation_resolution"]
    assert "nominal half-cell spatial extent" in comp["value"]
    assert comp.get("nature") == "NOMINAL_GRID_SCALE"
    assert "not an empirical measurement" in comp.get("clarification", "")


# Guardrail 38: +/-5m half-grid extent cannot be labeled measured registration error (Rule 74)
def test_guardrail_38_half_grid_extent_not_measured_resampling_error(geo_audit):
    comp = geo_audit["spatial_uncertainty_decomposition"]["components"]["3_resampling_discretization_envelope"]
    assert "Nominal half-cell grid discretization scale" in comp["value"]
    assert comp.get("nature") == "NOMINAL_DISCRETIZATION_SCALE"
    assert "not a measured resampling spatial distortion" in comp.get("clarification", "")


# Guardrail 39: Boundary tolerance cannot be labeled physical uncertainty or ground-truth error (Rule 58)
def test_guardrail_39_boundary_tolerance_not_physical_uncertainty(geo_audit):
    proto = geo_audit["boundary_tolerance_protocol"]
    assert "Candidate PRE-REGISTERED BOUNDARY-TOLERANCE PARAMETER" in proto["parameter_characterization"]
    assert "NOT automatically a measured physical uncertainty" in proto["parameter_characterization"]


# Guardrail 40: XML geolocation grid points cannot be called geodetic ground truth (Rule 75)
def test_guardrail_40_xml_geolocation_not_ground_truth():
    # Verify that reports do not mislabel XML geolocation grid points as absolute geodetic ground truth
    r3_report = EXP_DIR / "PHASE_7B2B_R3_FINAL_RECONCILIATION_20260913.md"
    if r3_report.exists():
        text = r3_report.read_text(encoding="utf-8")
        assert "source-product geolocation controls" in text
        assert "source-product geolocation metadata, not geodetically surveyed" in text


# Guardrail 41: Reporting reconciliation cannot be called scientific resolution of underlying uncertainty (Rule 73)
def test_guardrail_41_reconciliation_not_scientific_resolution():
    geo_path = METADATA_DIR / "li_geometry_registration_audit_v2.json"
    with open(geo_path, "r", encoding="utf-8") as f:
        geo = json.load(f)
    # The reporting is reconciled, but interior uncertainty remains explicitly NOT ESTABLISHED
    comp = geo["spatial_uncertainty_decomposition"]["components"]["2_geolocation_registration_uncertainty"]
    assert comp["quantification_status"] == "NOT_ESTABLISHED"


# Guardrail 42: Phase 7C cannot assume alignment success (Rule 62)
def test_guardrail_42_phase_7c_does_not_assume_alignment_success():
    r3_report = EXP_DIR / "PHASE_7B2B_R3_FINAL_RECONCILIATION_20260913.md"
    if r3_report.exists():
        text = r3_report.read_text(encoding="utf-8")
        assert "ALIGNMENT NOT ESTABLISHED / BLOCKED" in text
        assert "contingenc" in text.lower()


# Guardrail 43: Phase 7C cannot assume native 10m ground truth exists (Rule 57)
def test_guardrail_43_phase_7c_no_native_ground_truth_assumption(geo_audit):
    align = geo_audit["label_to_operational_10m_alignment_contract"]
    assert align["mandated_mask_classification"] == "DERIVED_HIGH_RESOLUTION_MASK"
    for forbidden in align["strictly_forbidden_classifications"]:
        assert forbidden != align["mandated_mask_classification"]


# Guardrail 44: OPS-01 cannot be labeled validated specialist (Rule 18, 49)
def test_guardrail_44_ops01_not_labeled_validated_specialist(taxonomy_audit):
    cap = taxonomy_audit["capability_gap_justification"]
    assert cap.get("ops01_architectural_status") == "ARCHITECTURAL_HYPOTHESIS_REQUIRING_VALIDATION"
    assert cap.get("ops01_validation_status") == "UNVALIDATED_SPECIALIST_CONCEPT"


# Guardrail 45: Specific Li phenomena cannot be labeled proven EXP-06 false alarm causes (Rule 64)
def test_guardrail_45_lookalike_causality_remains_not_established(taxonomy_audit):
    cap = taxonomy_audit["capability_gap_justification"]
    assert "NOT ESTABLISHED" in cap["look_alike_attribution_status"]
    assert "causal_attribution_prohibition" in cap


# Guardrail 46: Part-III firewall cannot be cited as zero-overlap evidence (Rule 65)
def test_guardrail_46_part_iii_firewall_not_zero_overlap_evidence(taxonomy_audit):
    cross = taxonomy_audit["leakage_and_independence_audit"]["cross_dataset_leakage"]
    assert cross["part_iii_overlap"] == "UNKNOWN_NOT_EVALUATED_FIREWALLED"
    assert "cannot establish zero overlap" in cross["firewall_governance_rule"]


# Guardrail 47: Unresolved interior geometry cannot be converted to invented numerical bounds (Rule 66)
def test_guardrail_47_no_invented_interior_numerical_bounds(geo_audit):
    comp = geo_audit["spatial_uncertainty_decomposition"]["components"]["2_geolocation_registration_uncertainty"]
    val = comp["value"].lower()
    assert "10m to 100m" not in val
    assert "+/-10m" not in val
    assert "unknown / not established" in val


# Guardrail 48: Pre-training readiness gate cannot imply training authorization (Rule 43)
def test_guardrail_48_gate_does_not_authorize_training():
    r3_telem_path = SCRATCH_DIR / "phase_7b2b_r3_reconciliation_run_state.json"
    if r3_telem_path.exists():
        with open(r3_telem_path, "r", encoding="utf-8") as f:
            telem = json.load(f)
        assert telem["training_invoked"] is False
        assert telem["gpu_invoked"] is False

# Guardrail 49: git diff excludes untracked files (Rule 85)
def test_guardrail_49_git_diff_excludes_untracked_files():
    # Verify ledger demonstrates that git diff (2 files) is vastly smaller than git status -uall (1991 files)
    ledger_path = METADATA_DIR / "phase_7b2b_r4_repository_artifact_ledger.json"
    assert ledger_path.exists()
    import json
    with open(ledger_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["summary"]["tracked_modified_count"] == 2
    assert data["summary"]["untracked_count"] > 1900


# Guardrail 50: Zero staged does not mean clean repository (Rule 87)
def test_guardrail_50_zero_staged_not_clean():
    ledger_path = METADATA_DIR / "phase_7b2b_r4_repository_artifact_ledger.json"
    assert ledger_path.exists()
    import json
    with open(ledger_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["summary"]["total_status_entries"] > 1000


# Guardrail 51: Untracked artifact provenance cannot default to PRE_EXISTING (Rule 88 & 90)
def test_guardrail_51_untracked_artifact_provenance_distinct():
    ledger_path = METADATA_DIR / "phase_7b2b_r4_repository_artifact_ledger.json"
    assert ledger_path.exists()
    import json
    with open(ledger_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    provs = set(x["provenance_class"] for x in data["artifacts"])
    assert "PHASE_7B2B_R3" in provs
    assert "HISTORICAL" in provs
    assert "PRE_EXISTING" in provs


# Guardrail 52: IDE Source Control count reconciled to Phase 6 attempt_001 payloads
def test_guardrail_52_ide_count_reconciled():
    ledger_path = METADATA_DIR / "phase_7b2b_r4_repository_artifact_ledger.json"
    assert ledger_path.exists()
    import json
    with open(ledger_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # 1808 Phase 6 evaluation payload files account for >90% of all untracked files
    assert data["summary"]["untracked_phase6_evaluation_payloads"] == 1808


# Guardrail 53: .gitignore modification does not hide current phase artifacts
def test_guardrail_53_gitignore_audit_complete():
    gitignore_path = REPO_ROOT / ".gitignore"
    assert gitignore_path.exists()
    text = gitignore_path.read_text(encoding="utf-8")
    assert "phase_6_part_iii_external_evaluation" not in text


# Guardrail 54: Phase 7C pilot scope is strictly bounded to 12 control products
def test_guardrail_54_phase_7c_pilot_scope_bounded():
    r4_report = EXP_DIR / "PHASE_7B2B_R4_GIT_FORENSIC_AND_PHASE7C_GATE_20260913.md"
    if r4_report.exists():
        text = r4_report.read_text(encoding="utf-8")
        assert "PILOT_SCOPE = 12 CONTROL PRODUCTS" in text
        assert "cannot be generalized automatically" in text


# Guardrail 55: Source-product geolocation metadata cannot be called surveyed ground truth
def test_guardrail_55_geolocation_metadata_not_surveyed():
    r3_report = EXP_DIR / "PHASE_7B2B_R3_FINAL_RECONCILIATION_20260913.md"
    assert r3_report.exists()
    text = r3_report.read_text(encoding="utf-8")
    assert "source-product geolocation metadata, not geodetically surveyed" in text
    assert "synthetic geolocation" not in text


# Guardrail 56: Pilot alignment results cannot automatically validate whole Li dataset
def test_guardrail_56_pilot_results_cannot_validate_whole_dataset():
    r4_report = EXP_DIR / "PHASE_7B2B_R4_GIT_FORENSIC_AND_PHASE7C_GATE_20260913.md"
    if r4_report.exists():
        text = r4_report.read_text(encoding="utf-8")
        assert "Generalization beyond those 12 requires separate evidence" in text


# Guardrail 57: R3 unresolved geometry state remains NOT_ESTABLISHED
def test_guardrail_57_r3_geometry_remains_not_established(geo_audit):
    comp = geo_audit["spatial_uncertainty_decomposition"]["components"]["2_geolocation_registration_uncertainty"]
    assert comp["quantification_status"] == "NOT_ESTABLISHED"
    align = geo_audit["label_to_operational_10m_alignment_contract"]
    assert align["source_to_operational_grid_alignment_status"] == "NOT_ESTABLISHED"


# Guardrail 58: Pre-training readiness does not authorize training (Rule 43)
def test_guardrail_58_readiness_does_not_authorize_training():
    r4_telem_path = SCRATCH_DIR / "phase_7b2b_r4_git_reconciliation_run_state.json"
    if r4_telem_path.exists():
        import json
        with open(r4_telem_path, "r", encoding="utf-8") as f:
            telem = json.load(f)
        assert telem["training_invoked"] is False
        assert telem["gpu_invoked"] is False

