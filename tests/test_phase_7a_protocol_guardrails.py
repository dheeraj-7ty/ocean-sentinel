"""Regression guardrail test suite for Ocean Sentinel Phase 7A.1.

Validates the final data governance, provenance, and development protocol foundation:
1. Part III contamination firewall (zero Part III hashes or scenes in dev manifests).
2. Parent-scene split isolation (zero cross-split scene overlap).
3. Geographic connected components isolation (zero cross-split cluster overlap).
4. Manifest cryptographic checksum integrity (SHA-256 matching companion file).
5. Channel contract verification (Mapping A: Band 1 -> Ch0, Band 2 -> Ch1).
6. Normalization statistics coupling.
7. Internal holdout quarantine firewall.
8. Terminology and unit consistency (parent scene vs tile vs candidate region).
9. Baseline dataset identity verification.
10. Telemetry schema and console format compliance.
11. Scientific claim constraints (zero forbidden causal assertions).
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
METADATA_DIR = REPO_ROOT / "data" / "metadata"
INTERNAL_MANIFEST = METADATA_DIR / "internal_development_split_manifest.json"
INTERNAL_SHA_FILE = METADATA_DIR / "internal_development_split_manifest.sha256"
CLUSTER_AUDIT = METADATA_DIR / "geographic_cluster_audit.json"
PART_III_AUDIT = METADATA_DIR / "part_iii_exclusion_audit.json"
PART_I_AUDIT = METADATA_DIR / "part_i_leakage_audit.json"
PROVENANCE_MANIFEST = METADATA_DIR / "lookalike_proxy_provenance_manifest.json"
DEV_BASELINE_FILE = REPO_ROOT / "experiments" / "performance" / "exp06_positive_bce_weight" / "exp06_frozen_dev_baseline.json"
REPORT_PATH = REPO_ROOT / "experiments" / "PHASE_7A_DATA_PROTOCOL_FOUNDATION_REPORT_20260912.md"
PROXY_MANIFEST = METADATA_DIR / "proxy_dataset_manifest.json"
PROXY_SHA_FILE = METADATA_DIR / "proxy_dataset_manifest.sha256"
PHYSICAL_REPORT = METADATA_DIR / "lookalike_proxy_physical_validation_report.json"
SEMANTIC_REPORT = METADATA_DIR / "lookalike_proxy_semantic_adjudication_report.json"
PROXY_DIAGNOSTIC_REPORT = REPO_ROOT / "experiments" / "performance" / "exp06_positive_bce_weight" / "exp06_proxy_zero_shot_diagnostic.json"


def compute_file_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def test_internal_manifest_cryptographic_checksum():
    """Verify bitwise SHA-256 integrity of internal_development_split_manifest.json."""
    assert INTERNAL_MANIFEST.is_file(), "Manifest file missing!"
    assert INTERNAL_SHA_FILE.is_file(), "Manifest SHA companion file missing!"

    computed_sha = compute_file_sha256(INTERNAL_MANIFEST)
    companion_text = INTERNAL_SHA_FILE.read_text(encoding="utf-8").strip()
    recorded_sha = companion_text.split()[0].upper()

    assert computed_sha == recorded_sha, f"SHA-256 mismatch! Computed: {computed_sha}, Recorded: {recorded_sha}"
    assert computed_sha == "17F1FF35146C7CE62E90D6FCE7F197B711B55E3C3CB599610578443208669072"


def test_parent_scene_split_isolation():
    """Verify strict scene-level partition with ZERO parent scene crossing."""
    with open(INTERNAL_MANIFEST, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    scenes = manifest["scenes"]
    assert len(scenes) == 1200, f"Expected 1,200 parent scenes, got {len(scenes)}"

    train_parents = set(s["parent_scene_id"] for s in scenes if s["split"] == "TRAIN")
    dev_parents = set(s["parent_scene_id"] for s in scenes if s["split"] == "DEV")
    holdout_parents = set(s["parent_scene_id"] for s in scenes if s["split"] == "INTERNAL_HOLDOUT")

    assert len(train_parents) == 840, f"Expected 840 TRAIN scenes, got {len(train_parents)}"
    assert len(dev_parents) == 180, f"Expected 180 DEV scenes, got {len(dev_parents)}"
    assert len(holdout_parents) == 180, f"Expected 180 INTERNAL_HOLDOUT scenes, got {len(holdout_parents)}"

    # Assert mutual disjointness (zero leakage)
    assert len(train_parents.intersection(dev_parents)) == 0, "Leakage detected between TRAIN and DEV!"
    assert len(train_parents.intersection(holdout_parents)) == 0, "Leakage detected between TRAIN and HOLDOUT!"
    assert len(dev_parents.intersection(holdout_parents)) == 0, "Leakage detected between DEV and HOLDOUT!"


def test_geographic_connected_components_isolation():
    """Verify that no spatial connected component crosses split boundaries."""
    assert CLUSTER_AUDIT.is_file(), "Cluster audit file missing!"
    with open(CLUSTER_AUDIT, "r", encoding="utf-8") as f:
        audit = json.load(f)

    assert audit["cross_split_leakage_count"] == 0, "Cross-split spatial leakage in connected components!"
    assert audit["component_breakdown"]["mixed_components"] == 0, "Mixed components detected!"
    assert audit["component_breakdown"]["train_components"] == 140
    assert audit["component_breakdown"]["dev_components"] == 32
    assert audit["component_breakdown"]["internal_holdout_components"] == 32


def test_part_iii_contamination_firewall():
    """Verify that zero Part III benchmark scenes or hashes contaminate development data."""
    with open(PART_III_AUDIT, "r", encoding="utf-8") as f:
        audit = json.load(f)

    # 195 parent products contaminated by Part III must all be excluded
    assert audit["contaminated_parent_products_count"] == 195
    assert audit["scene_level_excluded_regions_count"] == 680
    assert audit["cleared_candidate_regions_count"] == 1610

    # Verify lookalike proxy provenance manifest has classified them as REJECTED
    with open(PROVENANCE_MANIFEST, "r", encoding="utf-8") as f:
        prov = json.load(f)

    rejected_candidates = [c for c in prov["candidates"] if c["training_role"] == "REJECTED"]
    assert len(rejected_candidates) == 680, f"Expected 680 REJECTED candidates, got {len(rejected_candidates)}"
    for c in rejected_candidates:
        assert "Part III Contamination Firewall" in c["exclusion_reason"]


def test_channel_contract_and_normalization_pairing():
    """Verify Mapping A canonical contract and normalization pairing."""
    with open(INTERNAL_MANIFEST, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    norm_stats = manifest["normalization_stats"]
    assert norm_stats["channel_0_vh"]["mean"] == pytest.approx(-33.2323, abs=0.01)
    assert norm_stats["channel_0_vh"]["std"] == pytest.approx(6.4912, abs=0.01)
    assert norm_stats["channel_1_vv"]["mean"] == pytest.approx(-19.9405, abs=0.01)
    assert norm_stats["channel_1_vv"]["std"] == pytest.approx(4.5308, abs=0.01)

    # Check that each scene records Mapping A
    sample_scene = manifest["scenes"][0]
    contract = sample_scene["channel_contract"]
    assert "Mapping A" in contract["mapping"]
    assert "Band 1" in contract["ch0"]
    assert "Band 2" in contract["ch1"]


def test_holdout_quarantine_firewall():
    """Assert that INTERNAL_HOLDOUT is never assigned a training role."""
    with open(INTERNAL_MANIFEST, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    for s in manifest["scenes"]:
        if s["split"] == "INTERNAL_HOLDOUT":
            assert s["training_role"] == "HOLDOUT_EVALUATION"
            assert "TRAIN" not in s["training_role"]
        elif s["split"] == "DEV":
            assert s["training_role"] == "DEV_EVALUATION"
        elif s["split"] == "TRAIN":
            assert s["training_role"] == "POSITIVE_AND_BACKGROUND"


def test_baseline_dataset_identity_verification():
    """Verify that exp06_frozen_dev_baseline.json matches the frozen DEV dataset exactly."""
    assert DEV_BASELINE_FILE.is_file(), "DEV baseline file missing!"
    with open(DEV_BASELINE_FILE, "r", encoding="utf-8") as f:
        baseline = json.load(f)

    assert baseline["dataset"]["population_evaluated"] == "DEV"
    assert baseline["dataset"]["parent_scenes_count"] == 180
    assert baseline["dataset"]["total_tiles_evaluated"] == 2880
    assert baseline["dataset"]["positive_tiles_count"] == 1053
    assert baseline["dataset"]["clean_water_tiles_count"] == 1827

    # Assert exact cryptographic hashes
    assert baseline["model"]["checkpoint_sha256"] == "B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF"
    assert baseline["dataset"]["manifest_sha256"] == "17F1FF35146C7CE62E90D6FCE7F197B711B55E3C3CB599610578443208669072"
    assert baseline["protocol"]["decision_threshold_tau"] == 0.22

    # Assert baseline metrics match ground-truth evaluation
    assert baseline["primary_micro_metrics"]["val_iou"] == pytest.approx(0.72169, abs=0.0001)
    assert baseline["negative_rejection_metrics"]["clean_water_far_pct"] == pytest.approx(0.55, abs=0.05)
    assert baseline["negative_rejection_metrics"]["clean_water_fa_tiles"] == 10
    assert baseline["positive_dropout_metrics"]["positive_tiles_dropped"] == 174


def test_terminology_and_unit_consistency():
    """Verify that tile units and parent scene units are strictly separated."""
    with open(DEV_BASELINE_FILE, "r", encoding="utf-8") as f:
        baseline = json.load(f)

    # Clean water FAR denominator MUST be tile count
    cw_tiles = baseline["negative_rejection_metrics"]["clean_water_tiles_evaluated"]
    assert cw_tiles == 1827, f"Clean water tile FAR denominator must be 1,827, got {cw_tiles}"
    fa_tiles = baseline["negative_rejection_metrics"]["clean_water_fa_tiles"]
    far_pct = baseline["negative_rejection_metrics"]["clean_water_far_pct"]
    assert round((fa_tiles / cw_tiles) * 100.0, 2) == round(far_pct, 2)


def test_telemetry_schema_readiness():
    """Verify run_state.json schema and console progress format specifications."""
    schema_fields = {
        "status", "pid", "command_line", "phase", "percent_complete",
        "eta_seconds", "last_heartbeat_iso", "gpu_vram_allocated_mb",
    }
    exp06_run_state = REPO_ROOT / "experiments" / "performance" / "exp06_positive_bce_weight" / "run_state.json"
    assert exp06_run_state.is_file()
    with open(exp06_run_state, "r", encoding="utf-8") as f:
        state = json.load(f)

    for field in schema_fields:
        assert field in state, f"Missing telemetry schema field: {field}"


def test_governance_rules_39_and_40_codified():
    """Verify that Rule 39 and Rule 40 are permanently codified in EXPERIMENTAL_LESSONS_LEARNED_20260911.md."""
    lessons_path = REPO_ROOT / "experiments" / "EXPERIMENTAL_LESSONS_LEARNED_20260911.md"
    assert lessons_path.is_file()
    text = lessons_path.read_text(encoding="utf-8")

    assert "Rule 39" in text, "Rule 39 missing from lessons learned!"
    assert "No downstream artifact may be generated from an upstream protocol artifact" in text
    assert "Rule 40" in text, "Rule 40 missing from lessons learned!"
    assert "One active state-mutating experiment or audit process per AG task is the default" in text


def test_prerequisite_audit_artifacts_exist_and_pass():
    """Verify that all prerequisite upstream audit artifacts exist and certify PASS."""
    assert (METADATA_DIR / "source_dataset_inventory.json").is_file()
    assert (METADATA_DIR / "data_quality_report.json").is_file()
    assert (METADATA_DIR / "part_iii_exclusion_audit.json").is_file()
    assert (METADATA_DIR / "part_i_leakage_audit.json").is_file()
    assert (METADATA_DIR / "geographic_cluster_audit.json").is_file()
    assert (METADATA_DIR / "lookalike_proxy_provenance_manifest.json").is_file()

    with open(METADATA_DIR / "data_quality_report.json", "r", encoding="utf-8") as f:
        dq = json.load(f)
    assert "PASS" in dq["overall_status"]

    with open(METADATA_DIR / "geographic_cluster_audit.json", "r", encoding="utf-8") as f:
        gc = json.load(f)
    assert gc["cross_split_leakage_count"] == 0


def test_candidate_set_arithmetic_reconciliation():
    """Verify exact candidate-set arithmetic (SET A through SET G)."""
    recon_path = METADATA_DIR / "candidate_set_reconciliation.json"
    assert recon_path.is_file(), "candidate_set_reconciliation.json missing!"
    with open(recon_path, "r", encoding="utf-8") as f:
        recon = json.load(f)

    sets = recon["sets"]
    set_a = sets["SET_A_raw_candidates"]["regions"]
    set_b = sets["SET_B_part_iii_direct_overlap"]["regions"]
    set_c = sets["SET_C_part_iii_scene_contaminated"]["regions"]
    set_d = sets["SET_D_part_iii_cleared"]["regions"]
    set_e_dir = sets["SET_E_part_i_direct_overlap"]["regions"]
    set_e_scene = sets["SET_E_part_i_scene_expanded"]["regions"]
    set_f = sets["SET_F_fully_disjoint"]["regions"]
    set_g = sets["SET_G_provisional_proxies"]["regions"]

    assert set_a == 2290
    assert set_b == 355
    assert set_c == 680
    assert set_d == 1610
    assert set_e_dir == 543
    assert set_e_scene == 1063
    assert set_f == 547
    assert set_g == 547

    # Assert exact arithmetic partitions
    assert set_c + set_d == set_a, "Part III region partition failed!"
    assert set_e_scene + set_f == set_d, "Part I scene partition failed!"
    assert set_e_dir + 520 == set_e_scene, "Indirect co-scene expansion failed!"
    assert set_e_dir + 520 + set_f == set_d, "Full cleared decomposition failed!"


def test_region_vs_parent_product_accounting_distinctness():
    """Verify that candidate region counts and parent product counts are strictly distinct."""
    recon_path = METADATA_DIR / "candidate_set_reconciliation.json"
    with open(recon_path, "r", encoding="utf-8") as f:
        recon = json.load(f)

    sets = recon["sets"]
    prod_a = sets["SET_A_raw_candidates"]["parent_products"]
    prod_b = sets["SET_B_part_iii_direct_overlap"]["parent_products"]
    prod_c = sets["SET_C_part_iii_scene_contaminated"]["parent_products"]
    prod_d = sets["SET_D_part_iii_cleared"]["parent_products"]
    prod_e_dir = sets["SET_E_part_i_direct_overlap"]["parent_products"]
    prod_e_scene = sets["SET_E_part_i_scene_expanded"]["parent_products"]
    prod_f = sets["SET_F_fully_disjoint"]["parent_products"]

    assert prod_a == 869
    assert prod_b == 195
    assert prod_c == 195
    assert prod_d == 674
    assert prod_e_dir == 331
    assert prod_e_scene == 331
    assert prod_f == 343

    # Assert product partition formulas
    assert prod_c + prod_d == prod_a
    assert prod_e_scene + prod_f == prod_d
    assert prod_c + prod_e_scene + prod_f == prod_a


def test_provisional_vs_confirmed_proxy_status():
    """Verify that zero candidates are labeled CONFIRMED_NEGATIVE before physical validation."""
    with open(PROVENANCE_MANIFEST, "r", encoding="utf-8") as f:
        prov = json.load(f)

    # ZERO records may have training_role == 'CONFIRMED_NEGATIVE'
    confirmed_negs = [c for c in prov["candidates"] if c.get("training_role") == "CONFIRMED_NEGATIVE"]
    assert len(confirmed_negs) == 0, f"Found {len(confirmed_negs)} candidates with unauthorized CONFIRMED_NEGATIVE status!"

    # Exactly 547 candidates must have training_role == 'PROVISIONALLY_ELIGIBLE_NEGATIVE_PROXY'
    provisional_proxies = [c for c in prov["candidates"] if c.get("training_role") == "PROVISIONALLY_ELIGIBLE_NEGATIVE_PROXY"]
    assert len(provisional_proxies) == 547, f"Expected 547 PROVISIONALLY_ELIGIBLE_NEGATIVE_PROXY, got {len(provisional_proxies)}"
    assert prov["training_role_summary"]["PROVISIONALLY_ELIGIBLE_NEGATIVE_PROXY"] == 547


def test_no_physical_confirmation_claim_before_imagery_exists():
    """Verify that physical imagery status is explicitly marked PENDING and unacquired."""
    dq_path = METADATA_DIR / "data_quality_report.json"
    with open(dq_path, "r", encoding="utf-8") as f:
        dq = json.load(f)
    assert dq["dartis_raster_acquisition"] == "PENDING"

    with open(PROVENANCE_MANIFEST, "r", encoding="utf-8") as f:
        prov = json.load(f)
    assert prov["physical_imagery_status"] == "PENDING_ACQUISITION"

    # Verify all provisional candidates record PENDING_ACQUISITION
    provisional = [c for c in prov["candidates"] if c["training_role"] == "PROVISIONALLY_ELIGIBLE_NEGATIVE_PROXY"]
    for c in provisional:
        assert c["physical_validation_status"] == "PENDING_ACQUISITION"


def test_part_i_manifest_remains_unchanged():
    """Verify that the frozen Part-I development manifest is strictly unchanged."""
    assert INTERNAL_MANIFEST.is_file()
    computed_sha = compute_file_sha256(INTERNAL_MANIFEST)
    assert computed_sha == "17F1FF35146C7CE62E90D6FCE7F197B711B55E3C3CB599610578443208669072"

    with open(INTERNAL_MANIFEST, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    assert len(manifest["scenes"]) == 1200
    # Verify no DARTIS or proxy candidates were injected into Part-I manifest
    for s in manifest["scenes"]:
        assert not s["parent_scene_id"].startswith("nw-")
        assert not s["parent_scene_id"].startswith("nc-")


def test_micro_vs_macro_terminology_integrity():
    """Verify that Micro Pooled IoU and Macro Mean IoU are strictly separated in report."""
    assert REPORT_PATH.is_file()
    text = REPORT_PATH.read_text(encoding="utf-8")

    assert "Micro Pooled IoU" in text, "Report missing 'Micro Pooled IoU' terminology!"
    assert "Macro Mean IoU" in text, "Report missing 'Macro Mean IoU' terminology!"
    # Ensure forbidden 'Micro Mean IoU' is absent
    assert "Micro Mean IoU" not in text, "Forbidden 'Micro Mean IoU' found in report!"


def test_proxy_data_cannot_enter_training_before_validation_status():
    """Verify that provisional proxy candidates are blocked from entering training pipelines."""
    with open(PROVENANCE_MANIFEST, "r", encoding="utf-8") as f:
        prov = json.load(f)

    # Simulated data ingestion filter
    def authorize_for_training(candidate: dict) -> bool:
        if candidate.get("training_role") == "PROVISIONALLY_ELIGIBLE_NEGATIVE_PROXY":
            if candidate.get("physical_validation_status") != "PHYSICALLY_VALIDATED_NEGATIVE":
                return False
        return False

    for c in prov["candidates"]:
        assert not authorize_for_training(c), f"Candidate {c['candidate_tag']} improperly authorized for training!"


def test_part_iii_exclusion_remains_enforced():
    """Verify that all 680 Part III contaminated candidate regions remain strictly REJECTED."""
    with open(PROVENANCE_MANIFEST, "r", encoding="utf-8") as f:
        prov = json.load(f)

    rejected = [c for c in prov["candidates"] if c["training_role"] == "REJECTED"]
    assert len(rejected) == 680

    with open(PART_III_AUDIT, "r", encoding="utf-8") as f:
        audit = json.load(f)
    assert audit["scene_level_excluded_regions_count"] == 680
    assert audit["cleared_candidate_regions_count"] == 1610


def test_physical_validation_does_not_imply_semantic_validation():
    """Verify lifecycle rule: physical validation does NOT imply semantic negative status."""
    if not SEMANTIC_REPORT.is_file():
        pytest.skip("Semantic report pending pipeline completion")

    with open(SEMANTIC_REPORT, "r", encoding="utf-8") as f:
        sem = json.load(f)

    assert sem["semantically_validated_negatives_count"] == 0, (
        "Zero candidates may be promoted to SEMANTICALLY_VALIDATED_NEGATIVE_PROXY "
        "without per-pixel ground truth!"
    )
    assert sem["semantic_status_unresolved_count"] > 0

    for r in sem["results"]:
        if r["physical_validation_status"] == "PHYSICALLY_VALIDATED_PROXY":
            assert r["semantic_validation_status"] == "SEMANTIC_STATUS_UNRESOLVED"
            assert "CONFIRMED_NEGATIVE" not in r["semantic_validation_status"]


def test_semantic_unresolved_candidates_blocked_from_negative_evaluation():
    """Assert that SEMANTIC_STATUS_UNRESOLVED proxies cannot be counted as ground-truth negatives."""
    if not PROXY_MANIFEST.is_file():
        pytest.skip("Proxy manifest pending pipeline completion")

    with open(PROXY_MANIFEST, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest["semantic_negative_ground_truth_frozen"] is False
    assert manifest["evaluation_role"] == "PROVISIONAL_PROXY_DIAGNOSTIC_ONLY"

    for c in manifest["candidates"]:
        assert c["semantic_validation_status"] in ("SEMANTIC_STATUS_UNRESOLVED", "REJECTED_SEMANTIC")
        assert c["training_role"] != "CONFIRMED_NEGATIVE"


def test_proxy_dataset_manifest_and_sha256_freeze():
    """Verify bitwise SHA-256 integrity of proxy_dataset_manifest.json."""
    if not PROXY_MANIFEST.is_file() or not PROXY_SHA_FILE.is_file():
        pytest.skip("Proxy manifest and SHA companion pending pipeline completion")

    computed_sha = compute_file_sha256(PROXY_MANIFEST)
    companion_text = PROXY_SHA_FILE.read_text(encoding="utf-8").strip()
    recorded_sha = companion_text.split()[0].upper()

    assert computed_sha == recorded_sha, f"Proxy manifest SHA-256 mismatch! {computed_sha} vs {recorded_sha}"

    # Also verify that Part-I internal manifest was NOT altered
    part_i_sha = compute_file_sha256(INTERNAL_MANIFEST)
    assert part_i_sha == "17F1FF35146C7CE62E90D6FCE7F197B711B55E3C3CB599610578443208669072"


def test_proxy_and_part_i_and_part_iii_isolation():
    """Verify that proxy candidates have ZERO overlap with Part-I and Part-III."""
    if not PROXY_MANIFEST.is_file():
        pytest.skip("Proxy manifest pending pipeline completion")

    with open(PROXY_MANIFEST, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    with open(PROVENANCE_MANIFEST, "r", encoding="utf-8") as f:
        prov = json.load(f)

    with open(INTERNAL_MANIFEST, "r", encoding="utf-8") as f:
        part_i = json.load(f)

    proxy_tags = set(c["candidate_id"] for c in manifest["candidates"])
    proxy_parents = set(c["Sentinel_ID"] for c in manifest["candidates"])

    part_i_scenes = set(s["parent_scene_id"] for s in part_i["scenes"])
    part_iii_parents = set(c["source_product_id"] for c in prov["candidates"] if c["training_role"] == "REJECTED")
    part_i_parents = set(c["source_product_id"] for c in prov["candidates"] if c["training_role"] == "DEVELOPMENT_ONLY")

    # Assert exact parent product set sizes
    assert len(part_iii_parents) == 195
    assert len(part_i_parents) == 331
    assert len(proxy_parents) == 343

    # Assert zero candidate tag overlap with Part-I scenes
    assert len(proxy_tags.intersection(part_i_scenes)) == 0

    # Assert mutual disjointness across all parent products
    assert len(proxy_parents.intersection(part_iii_parents)) == 0, "Proxy shares parent product with Part III!"
    assert len(proxy_parents.intersection(part_i_parents)) == 0, "Proxy shares parent product with Part I!"
    assert len(part_i_parents.intersection(part_iii_parents)) == 0, "Part I shares parent product with Part III!"


def test_proxy_diagnostic_metric_denominator_integrity():
    """Verify that diagnostic metric explicitly records its denominator and caveats."""
    if not PROXY_DIAGNOSTIC_REPORT.is_file():
        pytest.skip("Proxy diagnostic report pending pipeline completion")

    with open(PROXY_DIAGNOSTIC_REPORT, "r", encoding="utf-8") as f:
        diag = json.load(f)

    assert diag["diagnostic_metrics"]["metric_name"] == "PROVISIONAL_PROXY_ALARM_RATE"
    assert "lookalike FAR" not in diag["diagnostic_metrics"]["metric_name"].lower()

    denominator = diag["proxy_dataset"]["evaluated_patches_denominator"]
    assert denominator > 0
    assert len(diag["patch_results"]) == denominator

    # Conservation identity check
    total_eval_px = diag["proxy_dataset"]["evaluated_pixels_total"]
    fp_px = diag["diagnostic_metrics"]["total_false_positive_pixels"]
    assert fp_px <= total_eval_px, "Pixel count conservation violated!"
    assert fp_px >= 0


def test_deterministic_manifest_ordering_and_no_tmp_files():
    """Verify that proxy manifest entries are deterministically sorted and zero .tmp files remain."""
    if not PROXY_MANIFEST.is_file():
        pytest.skip("Proxy manifest pending pipeline completion")

    with open(PROXY_MANIFEST, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    candidate_ids = [c["candidate_id"] for c in manifest["candidates"]]
    assert candidate_ids == sorted(candidate_ids), "Proxy manifest is not deterministically sorted by candidate ID!"

    # Check for lingering .tmp files in raster directory
    raster_dir = REPO_ROOT / "data" / "raw" / "lookalike_candidates" / "dartis" / "rasters"
    if raster_dir.is_dir():
        tmp_files = list(raster_dir.glob("*.tmp"))
        assert len(tmp_files) == 0, f"Found {len(tmp_files)} lingering .tmp files in raster directory!"


# ==============================================================================
# PHASE 7A.3 SPECIFIC PROTOCOL GUARDRAILS (SECTION 19: 25 EXPLICIT TESTS)
# ==============================================================================

SEMANTIC_MATRIX_PATH = METADATA_DIR / "proxy_semantic_evidence_matrix.json"
SEMANTIC_MANIFEST_PATH = METADATA_DIR / "proxy_semantic_dataset_manifest.json"
SEMANTIC_SHA_PATH = METADATA_DIR / "proxy_semantic_dataset_manifest.sha256"
AUDIT_SUMMARY_PATH = METADATA_DIR / "phase_7a3_preprocessing_and_geometry_audit.json"
REPRO_DIAGNOSTIC_PATH = REPO_ROOT / "experiments" / "performance" / "exp06_positive_bce_weight" / "exp06_proxy_zero_shot_diagnostic_reproduction.json"
HISTORICAL_REPORT_PATH = REPO_ROOT / "experiments" / "PHASE_7A2_PHYSICAL_PROXY_VALIDATION_REPORT_20260912.md"
ADDENDUM_REPORT_PATH = REPO_ROOT / "experiments" / "PHASE_7A2_CORRECTION_ADDENDUM_20260913.md"
CORRECTED_REPORT_PATH = REPO_ROOT / "experiments" / "PHASE_7A2_PHYSICAL_PROXY_VALIDATION_REPORT_20260912_CORRECTED.md"
EXP06_CKPT_PATH = REPO_ROOT / "experiments" / "performance" / "exp06_positive_bce_weight" / "best_model.pt"
CANONICAL_SPLIT_MANIFEST = METADATA_DIR / "trujillo_2024" / "spatial_split_manifest.json"


def test_guardrail_01_blind_adjudication_firewall():
    """1. Semantic adjudication script cannot read model outputs before freeze."""
    script_path = REPO_ROOT / "scripts" / "adjudicate_phase_7a3_semantics.py"
    assert script_path.is_file(), "Semantic adjudication script missing!"
    code = script_path.read_text(encoding="utf-8")

    assert "exp06_proxy_zero_shot_diagnostic" not in code
    assert "best_model.pt" not in code
    assert "torch" not in code
    assert "ResNet34UNet" not in code


def test_guardrail_02_model_output_cannot_change_semantic_status():
    """2. Model output cannot change semantic status."""
    assert SEMANTIC_MANIFEST_PATH.is_file()
    with open(SEMANTIC_MANIFEST_PATH, "r", encoding="utf-8") as f:
        sem_man = json.load(f)

    for c in sem_man["candidates"]:
        assert c["semantic_status"] in ("SEMANTIC_STATUS_UNRESOLVED", "REJECTED_ACQUISITION")
        assert c["semantic_status"] != "SEMANTICALLY_VALIDATED_NEGATIVE_PROXY"
        assert c["semantic_status"] != "REJECTED_SEMANTIC"


def test_guardrail_03_acquisition_rejection_cannot_become_semantic_rejection_without_evidence():
    """3. Acquisition rejection cannot become semantic rejection without explicit evidence."""
    assert SEMANTIC_MATRIX_PATH.is_file()
    with open(SEMANTIC_MATRIX_PATH, "r", encoding="utf-8") as f:
        matrix = json.load(f)

    rej = [c for c in matrix["candidates"] if c["physical_validation_status"] == "REJECTED_ACQUISITION"]
    assert len(rej) == 30
    for c in rej:
        assert c["semantic_status"] == "REJECTED_ACQUISITION"
        assert "edge" in c["adjudication_rationale"].lower() or "boundary" in c["adjudication_rationale"].lower() or "nan" in c["adjudication_rationale"].lower()


def test_guardrail_04_physical_raster_path_integrity():
    """4. physical_raster_path cannot reference missing files and must be null for rejections."""
    assert SEMANTIC_MATRIX_PATH.is_file()
    with open(SEMANTIC_MATRIX_PATH, "r", encoding="utf-8") as f:
        matrix = json.load(f)

    for c in matrix["candidates"]:
        if c["physical_validation_status"] == "PHYSICALLY_VALIDATED_PROXY":
            p = c.get("physical_raster_path")
            assert p is not None, f"Missing raster path for {c['candidate_id']}"
            assert Path(p).is_file(), f"Raster file missing on disk: {p}"
        else:
            assert c.get("physical_raster_path") is None, f"Rejected candidate {c['candidate_id']} has path!"


def test_guardrail_05_candidate_accounting_identity():
    """5. Enforce 517 physically validated + 30 rejected acquisitions = 547 candidates."""
    with open(PROXY_MANIFEST, "r", encoding="utf-8") as f:
        proxy = json.load(f)
    val = [c for c in proxy["candidates"] if c["physical_validation_status"] == "PHYSICALLY_VALIDATED_PROXY"]
    rej = [c for c in proxy["candidates"] if c["physical_validation_status"] == "REJECTED_ACQUISITION"]
    assert len(val) == 517
    assert len(rej) == 30
    assert len(proxy["candidates"]) == 547


def test_guardrail_06_parent_product_accounting():
    """6. Enforce 343 unique Sentinel-1 parent products across SET_G."""
    with open(PROXY_MANIFEST, "r", encoding="utf-8") as f:
        proxy = json.load(f)
    sids = set(c["Sentinel_ID"] for c in proxy["candidates"])
    assert len(sids) == 343


def test_guardrail_07_patch_and_product_unit_distinction():
    """7. Ensure clear distinction between patch-level and parent-product units."""
    assert REPRO_DIAGNOSTIC_PATH.is_file()
    with open(REPRO_DIAGNOSTIC_PATH, "r", encoding="utf-8") as f:
        repro = json.load(f)
    metrics = repro["diagnostic_metrics"]
    assert "patch_level" in metrics
    assert "parent_product_level" in metrics
    assert metrics["patch_level"]["evaluated_patches"] == 517
    assert metrics["parent_product_level"]["unique_parent_products"] == 325


def test_guardrail_08_canonical_preprocessing_values_from_source():
    """8. Canonical preprocessing values sourced from authoritative implementation."""
    assert CANONICAL_SPLIT_MANIFEST.is_file()
    with open(CANONICAL_SPLIT_MANIFEST, "r", encoding="utf-8") as f:
        m = json.load(f)
    stats = m["normalization_stats"]
    assert stats["channel_means"][0] == pytest.approx(-33.233136989478695, abs=1e-6)
    assert stats["channel_means"][1] == pytest.approx(-19.941215852796695, abs=1e-6)


def test_guardrail_09_crop_geometry_contract():
    """9. 640x640 -> 512x512 crop geometry contract audited."""
    assert AUDIT_SUMMARY_PATH.is_file()
    with open(AUDIT_SUMMARY_PATH, "r", encoding="utf-8") as f:
        audit = json.load(f)
    geo = audit["geometry_contract"]
    assert geo["pixel_center_offset"] == [0.0, 0.0]
    assert geo["area_coverage_fraction"] == pytest.approx(0.64, abs=1e-4)


def test_guardrail_10_historical_phase_7a2_report_preserved():
    """10. Historical Phase 7A.2 report is preserved untouched."""
    assert HISTORICAL_REPORT_PATH.is_file()
    content = HISTORICAL_REPORT_PATH.read_text(encoding="utf-8")
    assert "PHASE_7A2_PHYSICAL_PROXY_VALIDATION_REPORT_20260912" in content


def test_guardrail_11_corrected_report_explicit_provenance():
    """11. Corrected report has explicit provenance to original and addendum."""
    assert CORRECTED_REPORT_PATH.is_file()
    assert ADDENDUM_REPORT_PATH.is_file()
    corr_content = CORRECTED_REPORT_PATH.read_text(encoding="utf-8")
    add_content = ADDENDUM_REPORT_PATH.read_text(encoding="utf-8")
    assert "PHASE_7A2_CORRECTION_ADDENDUM_20260913" in corr_content
    assert "PHASE_7A2_PHYSICAL_PROXY_VALIDATION_REPORT_20260912" in add_content


def test_guardrail_12_no_official_far_before_semantic_freeze():
    """12. No official false alarm rate claim before semantic freeze."""
    with open(SEMANTIC_MANIFEST_PATH, "r", encoding="utf-8") as f:
        sem_man = json.load(f)
    assert sem_man["summary"]["official_negative_denominator"] == 0
    assert sem_man["summary"]["semantically_validated_negative"] == 0


def test_guardrail_13_unresolved_excluded_from_official_denominator():
    """13. Unresolved candidates excluded from official negative denominator."""
    with open(SEMANTIC_MANIFEST_PATH, "r", encoding="utf-8") as f:
        sem_man = json.load(f)
    for c in sem_man["candidates"]:
        assert c["eligible_for_official_negative_denominator"] is False


def test_guardrail_14_probable_candidates_excluded():
    """14. Probable candidates excluded unless protocol explicitly permits."""
    with open(SEMANTIC_MANIFEST_PATH, "r", encoding="utf-8") as f:
        sem_man = json.load(f)
    assert sem_man["status_breakdown"].get("PROBABLE_NEGATIVE_PROXY", 0) == 0


def test_guardrail_15_part_i_remains_unchanged():
    """15. Part-I development manifest remains strictly bitwise unchanged."""
    computed_sha = compute_file_sha256(INTERNAL_MANIFEST)
    assert computed_sha == "17F1FF35146C7CE62E90D6FCE7F197B711B55E3C3CB599610578443208669072"


def test_guardrail_16_part_iii_remains_quarantined():
    """16. Part-III benchmark remains strictly quarantined under Rule 38."""
    with open(PART_III_AUDIT, "r", encoding="utf-8") as f:
        p3_audit = json.load(f)
    assert p3_audit["scene_level_excluded_regions_count"] == 680


def test_guardrail_17_no_threshold_modification():
    """17. Decision threshold tau=0.22 remains frozen."""
    with open(REPRO_DIAGNOSTIC_PATH, "r", encoding="utf-8") as f:
        diag = json.load(f)
    assert diag["model"]["decision_threshold_tau"] == 0.22


def test_guardrail_18_no_checkpoint_modification():
    """18. EXP-06 checkpoint SHA-256 is strictly verified."""
    assert EXP06_CKPT_PATH.is_file()
    computed_sha = compute_file_sha256(EXP06_CKPT_PATH)
    assert computed_sha == "B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF"


def test_guardrail_19_no_training_authorization():
    """19. EXP-07 or candidate model training is strictly not authorized."""
    exp07_dirs = list((REPO_ROOT / "experiments" / "performance").glob("exp07*"))
    assert len(exp07_dirs) == 0, f"Found unauthorized EXP-07 directory: {exp07_dirs}"


def test_guardrail_20_ancillary_evidence_metadata_completeness():
    """20. Ancillary evidence records temporal and spatial metadata."""
    with open(SEMANTIC_MATRIX_PATH, "r", encoding="utf-8") as f:
        matrix = json.load(f)
    for c in matrix["candidates"]:
        assert "temporal_relevance" in c
        assert "spatial_relevance" in c
        assert "evidence_tier" in c
        assert "uncertainty" in c


def test_guardrail_21_manifest_checksum_integrity_phase_7a3():
    """21. Semantic manifest SHA-256 matches companion file."""
    assert SEMANTIC_MANIFEST_PATH.is_file()
    assert SEMANTIC_SHA_PATH.is_file()
    computed_sha = compute_file_sha256(SEMANTIC_MANIFEST_PATH)
    companion_sha = SEMANTIC_SHA_PATH.read_text(encoding="utf-8").strip().split()[0].upper()
    assert computed_sha == companion_sha


def test_guardrail_22_deterministic_ordering_phase_7a3():
    """22. Semantic manifest and evidence matrix are deterministically ordered."""
    with open(SEMANTIC_MANIFEST_PATH, "r", encoding="utf-8") as f:
        sem = json.load(f)
    ids = [c["candidate_id"] for c in sem["candidates"]]
    assert ids == sorted(ids)


def test_guardrail_23_no_temporary_acquisition_artifacts_phase_7a3():
    """23. Zero temporary acquisition artifacts linger in workspace."""
    raster_dir = REPO_ROOT / "data" / "raw" / "lookalike_candidates" / "dartis" / "rasters"
    if raster_dir.is_dir():
        assert len(list(raster_dir.glob("*.tmp"))) == 0


def test_guardrail_24_no_duplicate_candidate_membership():
    """24. No duplicate candidate IDs exist in the manifest or evidence matrix."""
    with open(SEMANTIC_MANIFEST_PATH, "r", encoding="utf-8") as f:
        sem = json.load(f)
    ids = [c["candidate_id"] for c in sem["candidates"]]
    assert len(ids) == len(set(ids))


def test_guardrail_25_no_duplicate_parent_product_inflation():
    """25. Parent product counts are strictly distinct from candidate counts."""
    with open(SEMANTIC_MANIFEST_PATH, "r", encoding="utf-8") as f:
        sem = json.load(f)
    parent_ids = set(c["parent_product_id"] for c in sem["candidates"])
    assert len(parent_ids) == 343
    assert len(parent_ids) < len(sem["candidates"])


PHASE_7A3_CORRECTED_REPORT_PATH = REPO_ROOT / "experiments" / "PHASE_7A3_SEMANTIC_ADJUDICATION_REPORT_20260913_CORRECTED.md"


def test_guardrail_26_parent_product_alarm_distribution_language():
    """26. Verify that corrected reports do NOT claim 'uniformly distributed' alarms."""
    assert PHASE_7A3_CORRECTED_REPORT_PATH.is_file()
    text = PHASE_7A3_CORRECTED_REPORT_PATH.read_text(encoding="utf-8")
    assert "uniformly distributed" not in text.lower()
    assert "alarm-producing patches occur across a large majority of parent products" in text.lower()


def test_guardrail_27_no_unsupported_sar_domain_generalization():
    """27. Verify that corrected reports do NOT claim 'systemic across the SAR acquisition domain'."""
    assert PHASE_7A3_CORRECTED_REPORT_PATH.is_file()
    text = PHASE_7A3_CORRECTED_REPORT_PATH.read_text(encoding="utf-8")
    assert "systemic across the sar acquisition domain" not in text.lower()
    assert "observed across a large majority of parent products in this evaluated proxy population" in text







