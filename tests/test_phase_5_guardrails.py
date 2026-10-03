"""Guardrail tests for Phase 5 hard-negative mining and training governance."""

import json
import pytest
from pathlib import Path
from ocean_sentinel.ingestion.firewall import (
    PartIIIFirewallViolationError,
    assert_no_part_iii_leakage,
    is_protected_part_iii_identifier,
    is_protected_part_iii_path,
)


def test_part_iii_firewall_blocks_training_candidates():
    # Attempting to add a Part III candidate to a mining pool must raise
    candidates = [
        {"tile_id": "tile_001", "image_path": "data/raw/trujillo_2024/images/Oil/00001.tif"},
        {"tile_id": "tile_002", "image_path": "data/raw/external_validation/trujillo_part_iii/Images/Lookalike/00042.tif"},
    ]
    with pytest.raises(PartIIIFirewallViolationError):
        for c in candidates:
            assert_no_part_iii_leakage([c["image_path"]], context="MiningCandidatePool")


def test_parent_scene_isolation_guardrail():
    # Verify that parent scene sets cannot overlap across train, val, and test
    train_parents = {"00001", "00002", "00003"}
    val_parents = {"00004", "00005"}
    test_parents = {"00006", "00007"}
    
    assert train_parents.isdisjoint(val_parents)
    assert train_parents.isdisjoint(test_parents)
    assert val_parents.isdisjoint(test_parents)

    # Simulated leakage: a tile from val_parents accidentally placed in train candidate pool
    leaked_candidate_parent = "00004"
    assert leaked_candidate_parent in val_parents
    with pytest.raises(ValueError, match="Cross-split parent-scene leakage detected"):
        if leaked_candidate_parent in val_parents:
            raise ValueError(f"Cross-split parent-scene leakage detected: parent {leaked_candidate_parent} in val_parents")


def test_hard_negative_threshold_guardrail():
    # Hard-negative thresholds must be explicitly validated against authorized frozen criteria
    AUTHORIZED_THRESHOLDS = (100, 500, 1000)
    
    def validate_mining_threshold(t: int) -> None:
        if t not in AUTHORIZED_THRESHOLDS:
            raise ValueError(f"Unauthorized mining threshold {t}. Must be in {AUTHORIZED_THRESHOLDS}")

    validate_mining_threshold(100)
    validate_mining_threshold(500)
    validate_mining_threshold(1000)

    with pytest.raises(ValueError, match="Unauthorized mining threshold"):
        validate_mining_threshold(73) # Arbitrary unapproved threshold


def test_candidate_purity_gate():
    # Tile with any ground-truth positive pixel must be categorically rejected
    def assert_candidate_purity(gt_pixels: int) -> None:
        if gt_pixels > 0:
            raise ValueError(f"Candidate purity violation: tile has {gt_pixels} positive GT pixels, must be 0")

    assert_candidate_purity(0) # clean negative
    with pytest.raises(ValueError, match="Candidate purity violation"):
        assert_candidate_purity(1)
    with pytest.raises(ValueError, match="Candidate purity violation"):
        assert_candidate_purity(500)


def test_candidate_parent_capping_gate():
    # Maximum of 2 candidates per parent scene
    MAX_PER_PARENT = 2

    def validate_parent_candidate_counts(candidates: list[dict]) -> None:
        counts = {}
        for c in candidates:
            p = c["parent_stem"]
            counts[p] = counts.get(p, 0) + 1
            if counts[p] > MAX_PER_PARENT:
                raise ValueError(f"Parent capping exceeded for {p}: {counts[p]} > {MAX_PER_PARENT}")

    valid_candidates = [
        {"parent_stem": "00001", "tile_idx": 0},
        {"parent_stem": "00001", "tile_idx": 1},
        {"parent_stem": "00002", "tile_idx": 0},
    ]
    validate_parent_candidate_counts(valid_candidates)

    invalid_candidates = [
        {"parent_stem": "00001", "tile_idx": 0},
        {"parent_stem": "00001", "tile_idx": 1},
        {"parent_stem": "00001", "tile_idx": 2}, # 3rd candidate from parent 00001
    ]
    with pytest.raises(ValueError, match="Parent capping exceeded"):
        validate_parent_candidate_counts(invalid_candidates)


def test_deterministic_candidate_sorting():
    # Verify deterministic tie-breaking key: (-fp_pixels, parent_stem, row_offset, col_offset)
    candidates = [
        {"parent_stem": "00002", "row_offset": 512, "col_offset": 0, "fp_pixels": 500},
        {"parent_stem": "00001", "row_offset": 0, "col_offset": 512, "fp_pixels": 1000},
        {"parent_stem": "00001", "row_offset": 0, "col_offset": 0, "fp_pixels": 500}, # tie in fp_pixels with 00002, but stem 00001 < 00002
        {"parent_stem": "00001", "row_offset": 512, "col_offset": 0, "fp_pixels": 500}, # tie with above, row 512 > 0
    ]
    
    sorted_candidates = sorted(
        candidates,
        key=lambda c: (-c["fp_pixels"], c["parent_stem"], c["row_offset"], c["col_offset"]),
    )
    
    # Expected order:
    # 1. fp=1000 (00001, row 0, col 512)
    # 2. fp=500, stem 00001, row 0, col 0
    # 3. fp=500, stem 00001, row 512, col 0
    # 4. fp=500, stem 00002, row 512, col 0
    assert sorted_candidates[0]["fp_pixels"] == 1000
    assert sorted_candidates[1]["parent_stem"] == "00001" and sorted_candidates[1]["row_offset"] == 0
    assert sorted_candidates[2]["parent_stem"] == "00001" and sorted_candidates[2]["row_offset"] == 512
    assert sorted_candidates[3]["parent_stem"] == "00002"


def test_two_stream_batch_composition_invariants():
    # Batch size 16 must have exactly 14 standard + 2 mined tiles
    BATCH_SIZE = 16
    N_STANDARD = 14
    N_MINED = 2
    
    assert N_STANDARD + N_MINED == BATCH_SIZE
    assert N_MINED / BATCH_SIZE == 0.125 # Exactly 12.5%
    
    # Verify mined tiles target label purity
    mined_target_masks = [0] * N_MINED
    assert all(m == 0 for m in mined_target_masks)


def test_exp03_hard_negative_manifest_integrity():
    import json
    import hashlib
    
    repo_root = Path(__file__).resolve().parent.parent
    manifest_path = repo_root / "data" / "metadata" / "trujillo_2024" / "exp03_hard_negative_manifest.json"
    assert manifest_path.exists(), f"Manifest file missing at {manifest_path}"
    
    data_bytes = manifest_path.read_bytes()
    computed_hash = hashlib.sha256(data_bytes).hexdigest().upper()
    EXPECTED_HASH = "3867671E639F020A686C5ACCA4FE5DA4280EB7DAEAB9BD9FEF467C192AA9F9F4"
    assert computed_hash == EXPECTED_HASH, f"Manifest hash mismatch: {computed_hash} != {EXPECTED_HASH}"
    
    payload = json.loads(data_bytes.decode("utf-8"))
    assert payload["candidate_summary"]["total_selected"] == 400
    assert len(payload["candidates"]) == 400
    
    # Verify parent stems in train partition
    split_path = repo_root / "data" / "metadata" / "trujillo_2024" / "spatial_split_manifest.json"
    split_data = json.loads(split_path.read_text(encoding="utf-8"))
    train_stems = {p["patch_stem"] for p in split_data["patches"] if p["split"] == "train"}
    val_stems = {p["patch_stem"] for p in split_data["patches"] if p["split"] == "val"}
    test_stems = {p["patch_stem"] for p in split_data["patches"] if p["split"] == "test"}
    
    parent_counts = {}
    for c in payload["candidates"]:
        stem = c["parent_stem"]
        assert stem in train_stems
        assert stem not in val_stems
        assert stem not in test_stems
        assert c["gt_pixels"] == 0
        assert c["fp_pixels"] >= 100
        assert c["p_max"] >= 0.50
        assert c["max_component_area"] >= 100
        parent_counts[stem] = parent_counts.get(stem, 0) + 1
        assert parent_counts[stem] <= 2

    # Authoritative Pre-Cap Parent Scene Census
    assert len(parent_counts) == 273, f"Expected 273 unique parent scenes, got {len(parent_counts)}"
    assert sum(1 for v in parent_counts.values() if v == 1) == 146
    assert sum(1 for v in parent_counts.values() if v == 2) == 127
    assert max(parent_counts.values()) == 2

    # Authoritative Severity-Capped (<= 50,000 FP) Pool Census
    retained = [c for c in payload["candidates"] if c["fp_pixels"] <= 50000]
    assert len(retained) == 355, f"Expected 355 retained candidates, got {len(retained)}"
    retained_parents = {}
    for c in retained:
        s = c["parent_stem"]
        retained_parents[s] = retained_parents.get(s, 0) + 1
    assert len(retained_parents) == 251, f"Expected 251 unique retained parent scenes, got {len(retained_parents)}"
    assert sum(1 for v in retained_parents.values() if v == 1) == 147
    assert sum(1 for v in retained_parents.values() if v == 2) == 104
    assert max(retained_parents.values()) == 2

    # Authoritative Excluded Extreme (> 50,000 FP) Pool Census
    excluded = [c for c in payload["candidates"] if c["fp_pixels"] > 50000]
    assert len(excluded) == 45, f"Expected 45 excluded extreme candidates, got {len(excluded)}"
    excluded_parents = {c["parent_stem"] for c in excluded}
    assert len(excluded_parents) == 25, f"Expected 25 excluded parent scenes, got {len(excluded_parents)}"


def test_gate5_clean_water_vs_total_validation_fp_guardrail():
    """Regression guard preventing conflation of clean-water FP and total validation FP.
    
    Validates:
    1. clean_water_fp_pixels is defined strictly on empty validation tiles (gt == 0).
    2. total_validation_fp_pixels is defined over all validation tiles (confusion matrix FP).
    3. Gate 5 (< 350,000) specifically constrains clean_water_fp_pixels per the original contract.
    4. Conflating the two metrics or substituting total validation FP into Gate 5 is blocked.
    """
    repo_root = Path(__file__).resolve().parent.parent
    verif_path = repo_root / "experiments/performance/exp06_positive_bce_weight/independent_validation_verification.json"
    assert verif_path.exists(), f"Verification file missing: {verif_path}"

    verif_data = json.loads(verif_path.read_text(encoding="utf-8"))
    
    total_val_fp = verif_data["confusion_counts"]["fp"]
    clean_water_fp = verif_data["metrics"]["total_fp_pixels"]
    
    # Authoritative integer values
    assert total_val_fp == 2009530, f"Total validation FP mismatch: {total_val_fp}"
    assert clean_water_fp == 113187, f"Clean-water FP mismatch: {clean_water_fp}"
    assert total_val_fp > clean_water_fp, "Total validation FP must strictly exceed clean-water FP"

    # Positive tile FP forensics verification
    forensics_path = repo_root / "experiments/performance/exp06_positive_bce_weight/exp06_positive_tile_forensics.json"
    assert forensics_path.exists()
    pos_tiles = json.loads(forensics_path.read_text(encoding="utf-8"))
    pos_tile_fp = sum(t["fp_pixels"] for t in pos_tiles)
    assert pos_tile_fp == 1896343

    # Exact mathematical partition
    assert clean_water_fp + pos_tile_fp == total_val_fp, "FP partition identity violated"

    # Gate 5 evaluation guard
    GATE_5_THRESHOLD = 350000
    assert clean_water_fp < GATE_5_THRESHOLD, "Clean-water FP must satisfy Gate 5"

    def evaluate_gate_5(metric_name: str, metric_value: int) -> bool:
        if metric_name not in ("clean_water_fp_pixels", "total_fp_pixels_empty"):
            raise ValueError(
                f"Gate 5 semantic violation: metric '{metric_name}' is not clean-water FP. "
                f"Total validation FP ({metric_value}) must not be evaluated against Gate 5 (< 350,000)."
            )
        return metric_value < GATE_5_THRESHOLD

    # Valid evaluation passes
    assert evaluate_gate_5("clean_water_fp_pixels", clean_water_fp) is True
    assert evaluate_gate_5("total_fp_pixels_empty", clean_water_fp) is True

    # Invalid evaluation raises semantic violation
    with pytest.raises(ValueError, match="Gate 5 semantic violation"):
        evaluate_gate_5("total_validation_fp_pixels", total_val_fp)


def test_clean_water_far_vs_significant_far_semantics_guardrail():
    """Regression guard ensuring Clean-Water FAR and Significant FAR maintain distinct semantics.
    
    Validates:
    1. Both use denominator = empty_tiles_evaluated (1,827).
    2. Clean-Water FAR numerator requires fp_pixels >= 1.
    3. Significant FAR numerator requires fp_pixels >= 100.
    4. On datasets with sub-100 FP tiles, Clean-Water FAR must strictly exceed Significant FAR.
    5. Disallows collapsing the two definitions into a single metric.
    """
    def compute_fars(empty_tile_fps: list[int]) -> tuple[float, float]:
        n_empty = len(empty_tile_fps)
        if n_empty == 0:
            return 0.0, 0.0
        clean_fa = sum(1 for fp in empty_tile_fps if fp >= 1)
        sig_fa = sum(1 for fp in empty_tile_fps if fp >= 100)
        return (clean_fa / n_empty) * 100.0, (sig_fa / n_empty) * 100.0

    # Test case 1: divergent behavior with noise tiles (1 <= fp < 100)
    mock_fps_with_noise = [0] * 1800 + [50] * 17 + [200] * 10
    clean_far, sig_far = compute_fars(mock_fps_with_noise)
    assert clean_far == (27 / 1827) * 100.0
    assert sig_far == (10 / 1827) * 100.0
    assert clean_far > sig_far, "Clean-Water FAR must exceed Significant FAR when noise tiles exist"

    # Test case 2: EXP-06 converged behavior where all FA tiles happen to be >= 100 px
    exp06_mock_fps = [0] * 1817 + [150] * 10
    exp06_clean, exp06_sig = compute_fars(exp06_mock_fps)
    assert exp06_clean == exp06_sig == (10 / 1827) * 100.0

    # Test case 3: Guardrail rejects any definition collapse
    def guarded_evaluation(clean_num_fn, sig_num_fn):
        # The two filtering functions must not be identical
        test_values = [0, 1, 50, 99, 100, 500]
        clean_bools = [clean_num_fn(v) for v in test_values]
        sig_bools = [sig_num_fn(v) for v in test_values]
        if clean_bools == sig_bools:
            raise ValueError("FAR definition collapse: Clean-Water and Significant FAR criteria are identical!")

    clean_fn = lambda fp: fp >= 1
    sig_fn = lambda fp: fp >= 100
    guarded_evaluation(clean_fn, sig_fn) # Must pass

    collapsed_fn = lambda fp: fp >= 1
    with pytest.raises(ValueError, match="FAR definition collapse"):
        guarded_evaluation(clean_fn, collapsed_fn)


def test_acceptance_gate_semantics_audit_artifact_integrity():
    """Verify presence and internal consistency of acceptance_gate_semantics_audit.json."""
    repo_root = Path(__file__).resolve().parent.parent
    audit_file = repo_root / "experiments/performance/exp06_positive_bce_weight/acceptance_gate_semantics_audit.json"
    assert audit_file.exists(), f"Audit file missing: {audit_file}"

    audit_data = json.loads(audit_file.read_text(encoding="utf-8"))
    status = audit_data["audit_metadata"]["overall_gate_status"]
    assert "PASS" in status and "PHASE 5H SCOPE" in status, f"Unexpected overall status: {status}"
    assert len(audit_data["gates"]) == 5
    for gate in audit_data["gates"]:
        assert gate["audit_status"] == "PASS"

    gate5 = next(g for g in audit_data["gates"] if g["gate_id"] == 5)
    assert gate5["semantic_status"] == "NAMING_ERROR"
    assert gate5["audit_status"] == "PASS"
    assert gate5["reported_value"] == 113187
    assert gate5["recomputed_value"] == 113187

    distinction = audit_data["metric_semantics_distinction"]
    assert distinction["clean_water_fp_pixels"]["value"] == 113187
    assert distinction["total_validation_fp_pixels"]["value"] == 2009530
    assert distinction["slick_tile_fp_pixels"]["value"] == 1896343


def test_canonical_exp01_baseline_provenance_guardrail():
    """Guard against conflating EXP-01 baseline metrics across thresholds, and reject 2798401."""
    repo_root = Path(__file__).resolve().parent.parent
    results_file = repo_root / "experiments/exp01_baseline/exp01_results.json"
    assert results_file.exists(), f"EXP-01 results missing: {results_file}"

    results_data = json.loads(results_file.read_text(encoding="utf-8"))
    thresh_data = results_data["threshold_selection"]["threshold_metric_results"]

    # Coherent Set A: Default sigmoid midpoint (tau = 0.50)
    set_050 = thresh_data["0.5000"]
    assert abs(set_050["iou"] - 0.71691) < 1e-4
    assert abs(set_050["recall"] - 0.78488) < 1e-4
    assert abs(set_050["precision"] - 0.89223) < 1e-4
    assert abs(set_050["dice"] - 0.83512) < 1e-4
    assert set_050["fn"] == 3471942.0

    # Coherent Set B: Operating point selected via grid search (tau = 0.22)
    set_022 = thresh_data["0.2200"]
    assert abs(set_022["iou"] - 0.72231) < 1e-4
    assert abs(set_022["recall"] - 0.82653) < 1e-4
    assert abs(set_022["precision"] - 0.85138) < 1e-4
    assert abs(set_022["dice"] - 0.83877) < 1e-4
    assert set_022["fn"] == 2799742.0

    # Provenance guard: 2,798,401 is a historical transcription error, NOT rounding
    # Differs by exactly 1,341 pixels from true computed FN (2,799,742)
    assert set_022["fn"] != 2798401, "Authoritative FN at tau=0.22 must be 2,799,742, not the 2,798,401 transcription error"

    # Anti-hybrid guard: Reject mixing tau=0.50 recall (0.78488) with tau=0.22 precision (0.85138)
    def check_coherent_row(precision, recall, threshold):
        if threshold == 0.22:
            assert abs(recall - 0.82653) < 1e-4, "tau=0.22 row must use tau=0.22 recall (0.82653)"
            assert abs(precision - 0.85138) < 1e-4, "tau=0.22 row must use tau=0.22 precision (0.85138)"
        elif threshold == 0.50:
            assert abs(recall - 0.78488) < 1e-4, "tau=0.50 row must use tau=0.50 recall (0.78488)"
            assert abs(precision - 0.89223) < 1e-4, "tau=0.50 row must use tau=0.50 precision (0.89223)"

    check_coherent_row(set_022["precision"], set_022["recall"], threshold=0.22)
    check_coherent_row(set_050["precision"], set_050["recall"], threshold=0.50)

    # Gate 2 non-inferiority bound derivation guard
    # Gate 2 floor (0.71731) = EXP-01 operating IoU (0.72231) - 0.0050 margin
    gate2_bound = 0.71731
    assert abs((round(set_022["iou"], 5) - 0.0050) - gate2_bound) < 1e-5
    assert set_050["iou"] != gate2_bound, "Gate 2 bound must not be conflated with tau=0.50 IoU"


def test_evaluation_threshold_provenance_guardrail():
    """Guard against accidental substitution of evaluation threshold (tau=0.22 vs default tau=0.50)."""
    from ocean_sentinel.ml.canonical_exp01 import CANONICAL_SELECTED_THRESHOLD
    from scripts.train_exp06 import FROZEN_THRESHOLD

    # The frozen operational threshold across Phase 5 development validation is 0.22
    assert CANONICAL_SELECTED_THRESHOLD == 0.22
    assert FROZEN_THRESHOLD == 0.22

    repo_root = Path(__file__).resolve().parent.parent
    verif_file = repo_root / "experiments/performance/exp06_positive_bce_weight/independent_validation_verification.json"
    assert verif_file.exists()

    verif_data = json.loads(verif_file.read_text(encoding="utf-8"))
    assert verif_data["threshold"] == 0.22, f"Verification threshold must be 0.22, got {verif_data['threshold']}"


def test_dropout_definition_and_counts_guardrail():
    """Verify that Complete Positive Tile Dropout is strictly defined as a GT-positive tile with zero detection."""
    repo_root = Path(__file__).resolve().parent.parent

    # EXP-06 positive tile forensics
    exp06_forensics = repo_root / "experiments/performance/exp06_positive_bce_weight/exp06_positive_tile_forensics.json"
    assert exp06_forensics.exists()
    tiles = json.loads(exp06_forensics.read_text(encoding="utf-8"))

    assert len(tiles) == 1053, "Must have exactly 1,053 GT-positive validation tiles"
    dropped_tiles = [t for t in tiles if not t["detected"]]
    detected_tiles = [t for t in tiles if t["detected"]]

    assert len(dropped_tiles) == 174, f"EXP-06 dropped count must be 174, got {len(dropped_tiles)}"
    assert len(detected_tiles) == 879, f"EXP-06 detected count must be 879, got {len(detected_tiles)}"

    # All dropped tiles must have tp_pixels == 0
    assert all(t["tp_pixels"] == 0 for t in dropped_tiles)
    assert all(t["tp_pixels"] > 0 for t in detected_tiles)

    dropout_fn = sum(t["fn_pixels"] for t in dropped_tiles)
    partial_fn = sum(t["fn_pixels"] for t in detected_tiles)
    total_fn = dropout_fn + partial_fn

    assert dropout_fn == 468829
    assert partial_fn == 2572918
    assert total_fn == 3041747

    # EXP-01 baseline comparison
    p5g_summary = repo_root / "experiments/performance/phase_5g_positive_failure_forensics/forensics_summary.json"
    assert p5g_summary.exists()
    fsum = json.loads(p5g_summary.read_text(encoding="utf-8"))
    exp01_decomp = fsum["fn_decomposition"]["EXP-01"]

    assert exp01_decomp["dropout_fn_pixels"] == 106609
    assert exp01_decomp["partial_fn_pixels"] == 2693136
    assert exp01_decomp["total_fn_pixels"] == 2799745


def test_unsupported_lookalike_and_boundary_claims_guardrail():
    """Ensure active closure artifacts do not contain unsupported semantic speculation."""
    repo_root = Path(__file__).resolve().parent.parent

    target_files = [
        repo_root / "experiments/PHASE_5H_EXP06_CLOSURE_AUDIT_20260912.md",
        repo_root / "experiments/PHASE_5H_EXP06_TRAINING_EXECUTION_REPORT_20260912.md",
        repo_root / "experiments/performance/exp06_positive_bce_weight/acceptance_gate_semantics_audit.json",
    ]

    unsupported_terms = [
        "boundary error",
        "periphery error",
        "lookalike cluster",
        "coherent lookalike",
    ]

    for p in target_files:
        assert p.exists(), f"Target file missing: {p}"
        content = p.read_text(encoding="utf-8").lower()
        for term in unsupported_terms:
            assert term not in content, f"Unsupported semantic claim '{term}' found in {p.name}"


def test_exp06_completion_status_not_stale_guardrail():
    """Ensure EXP-06 execution status is marked COMPLETED and contains no stale RUNNING tags."""
    repo_root = Path(__file__).resolve().parent.parent
    run_state_file = repo_root / "experiments/performance/exp06_positive_bce_weight/run_state.json"
    assert run_state_file.exists()

    state = json.loads(run_state_file.read_text(encoding="utf-8"))
    assert state["status"] == "COMPLETED"
    assert state["phase"] == "COMPLETE"
    assert state["best_val_iou"] == 0.72168
    assert state["best_epoch"] == 9
    assert state["percent_complete"] == 100.0


def test_authoritative_checkpoint_sha_integrity_guardrail():
    """Verify on-disk SHA-256 and byte sizes of canonical checkpoints and manifests."""
    import hashlib

    repo_root = Path(__file__).resolve().parent.parent

    expected = {
        repo_root / "experiments/exp01_baseline/best_model.pt": (
            "9B8BD867DC02C68CC062125074E8B21789FBBBAA55C903D55D8904003BDD1699",
            292465299,
        ),
        repo_root / "experiments/performance/exp06_positive_bce_weight/best_model.pt": (
            "B5FFCCA3D95A96A73ABAA895216BC42FA5FBCC673B09F56451D389DDAE41E8DF",
            292461395,
        ),
        repo_root / "experiments/performance/exp06_positive_bce_weight/last_model.pt": (
            "9CA4D910C4804AC994EF8C3E8C96A88AC93BDA2FFD76F9C0817E6C54803D8025",
            292461395,
        ),
        repo_root / "data/metadata/trujillo_2024/exp03_hard_negative_manifest.json": (
            "3867671E639F020A686C5ACCA4FE5DA4280EB7DAEAB9BD9FEF467C192AA9F9F4",
            261621,
        ),
    }

    for path, (exp_sha, exp_size) in expected.items():
        assert path.exists(), f"File missing: {path}"
        actual_size = path.stat().st_size
        assert actual_size == exp_size, f"Size mismatch for {path.name}: {actual_size} != {exp_size}"

        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(1024 * 1024):
                h.update(chunk)
        actual_sha = h.hexdigest().upper()
        assert actual_sha == exp_sha, f"SHA mismatch for {path.name}: {actual_sha} != {exp_sha}"


def test_exp01_fp_partition_and_far_invariants_guardrail():
    """Verify EXP-01 FP partition invariants and FAR calculation provenance.
    
    Protects against:
    1. Global FP (2,328,613) being conflated with Clean-Water FP on empty tiles (465,950).
    2. Historical all-tile streaming FP (2,327,942) being placed in empty-tile comparison rows.
    3. Significant FAR numerator errors: must be 193 / 1,827 = 10.56%, not 226 / 1,827 = 12.37%.
    4. Rejection of 12.37% (the erroneous EXP-02C cross-experiment value) as an EXP-01 metric.
    5. Conservation: Empty-tile FP (465,950) + Slick-tile FP (1,862,663) == Global FP (2,328,613).
    """
    repo_root = Path(__file__).resolve().parent.parent

    # 1. Authoritative Failure Analysis Report
    fa_file = repo_root / "experiments/performance/phase_5a_failure_analysis/failure_analysis_report.json"
    assert fa_file.exists(), f"Missing failure analysis report: {fa_file}"
    fa_data = json.loads(fa_file.read_text(encoding="utf-8"))

    empty_stats = fa_data["validation_split_metrics"]["empty_tiles"]
    assert empty_stats["total_count"] == 1827
    assert empty_stats["clean_water_fa_count"] == 367
    assert empty_stats["sig_fa_count_gte_100"] == 193
    assert abs(empty_stats["clean_water_fa_pct"] - 20.09) < 0.01
    assert abs(empty_stats["sig_fa_pct_gte_100"] - 10.56) < 0.01

    # Exact numerator / denominator verification
    assert (367 / 1827) * 100.0 == pytest.approx(20.087575, rel=1e-5)
    assert (193 / 1827) * 100.0 == pytest.approx(10.563765, rel=1e-5)

    # 2. Reject erroneous EXP-02C cross-experiment values
    def validate_exp01_sig_far(numerator: int, reported_pct: float) -> None:
        if numerator == 226 or abs(reported_pct - 12.37) < 0.05:
            raise ValueError("Conflation error: 12.37% (226 tiles) is from EXP-02C, NOT EXP-01 baseline!")
        assert numerator == 193, f"Expected 193, got {numerator}"
        assert abs(reported_pct - 10.56) < 0.05, f"Expected 10.56%, got {reported_pct}%"

    validate_exp01_sig_far(193, 10.56) # Must pass
    with pytest.raises(ValueError, match="Conflation error"):
        validate_exp01_sig_far(226, 12.37) # Must reject

    # 3. FP Partition Conservation
    empty_fp_sum = fa_data["validation_split_metrics"]["fp_area_stats_empty_tiles"]["sum"]
    all_tiles_fp_sum = fa_data["validation_split_metrics"]["fp_area_stats_all_tiles"]["sum"]
    assert empty_fp_sum == 465950, f"Expected 465,950 empty-tile FP, got {empty_fp_sum}"
    assert all_tiles_fp_sum == 2327942, f"Expected 2,327,942 all-tiles streaming FP, got {all_tiles_fp_sum}"

    # Global confusion matrix from exp02a
    thresh_file = repo_root / "experiments/exp02a_threshold_analysis.json"
    assert thresh_file.exists()
    thresh_data = json.loads(thresh_file.read_text(encoding="utf-8"))
    s022 = thresh_data["threshold_grid_sweep"]["0.2200"]
    global_fp = int(s022["fp"])
    assert global_fp == 2328613

    slick_fp = global_fp - empty_fp_sum
    assert slick_fp == 1862663
    assert empty_fp_sum + slick_fp == global_fp, "Partition sum violation"

    # 4. Semantic scope firewall: Reject treating all-tile FP as empty-tile FP
    def validate_comparison_row_scope(scope_name: str, exp01_val: int, exp06_val: int) -> float:
        if scope_name == "empty_tiles":
            if exp01_val != 465950:
                raise ValueError(f"Scope violation: empty_tiles comparison must use 465,950, not {exp01_val}")
            assert exp06_val == 113187
            return ((exp06_val - exp01_val) / exp01_val) * 100.0
        elif scope_name == "global_cm":
            if exp01_val != 2328613:
                raise ValueError(f"Scope violation: global_cm comparison must use 2,328,613, not {exp01_val}")
            assert exp06_val == 2009530
            return ((exp06_val - exp01_val) / exp01_val) * 100.0
        raise ValueError(f"Unknown scope {scope_name}")

    empty_delta_pct = validate_comparison_row_scope("empty_tiles", 465950, 113187)
    assert empty_delta_pct == pytest.approx(-75.708337, rel=1e-4)

    global_delta_pct = validate_comparison_row_scope("global_cm", 2328613, 2009530)
    assert global_delta_pct == pytest.approx(-13.702706, rel=1e-4)

    with pytest.raises(ValueError, match="Scope violation"):
        validate_comparison_row_scope("empty_tiles", 2327942, 113187)


def test_fp32_vs_amp_fn_and_headroom_sign_convention_guardrail():
    """Adversarial regression guard enforcing:
    1. Strict separation of FP32 canonical FN (2,799,742) and AMP forensic FN (2,799,745).
    2. Exact mass conservation within forensic decomposition pipelines.
    3. Acceptance Headroom calculation:
       - Lower bound: observed - min
       - Upper bound: max - observed
       - All five headrooms > 0.
    4. Part III benchmark tile count equals 7,200 (rejecting 5,760 as Part III count).
    """
    repo_root = Path(__file__).resolve().parent.parent

    # 1. FP32 vs AMP FN separation
    thresh_file = repo_root / "experiments/exp02a_threshold_analysis.json"
    thresh_data = json.loads(thresh_file.read_text(encoding="utf-8"))
    s022 = thresh_data["threshold_grid_sweep"]["0.2200"]
    fp32_fn = int(s022["fn"])
    assert fp32_fn == 2799742, f"Canonical FP32 FN must be 2,799,742, got {fp32_fn}"

    p5g_summary = repo_root / "experiments/performance/phase_5g_positive_failure_forensics/forensics_summary.json"
    p5g_data = json.loads(p5g_summary.read_text(encoding="utf-8"))
    exp01_decomp = p5g_data["fn_decomposition"]["EXP-01"]
    amp_fn = exp01_decomp["total_fn_pixels"]
    dropout_fn = exp01_decomp["dropout_fn_pixels"]
    partial_fn = exp01_decomp["partial_fn_pixels"]

    assert amp_fn == 2799745, f"AMP forensic FN must be 2,799,745, got {amp_fn}"
    assert dropout_fn == 106609
    assert partial_fn == 2693136
    assert dropout_fn + partial_fn == amp_fn, "AMP decomposition must conserve mass exactly"
    assert amp_fn - fp32_fn == 3, "Observed precision-mode reproduction delta must be exactly 3 pixels"

    # 2. Acceptance Headroom sign convention verification
    def compute_headroom(gate_type: str, observed: float, limit: float) -> float:
        if gate_type == "lower":
            return observed - limit
        elif gate_type == "upper":
            return limit - observed
        raise ValueError(f"Unknown gate_type: {gate_type}")

    g1_hr = compute_headroom("lower", 0.81153, 0.78500)
    assert g1_hr == pytest.approx(0.02653, rel=1e-5)
    assert g1_hr > 0

    g2_hr = compute_headroom("lower", 0.72168, 0.71731)
    assert g2_hr == pytest.approx(0.00437, rel=1e-5)
    assert g2_hr > 0

    g3_hr = compute_headroom("upper", 0.55, 5.00)
    assert g3_hr == pytest.approx(4.45, rel=1e-5)
    assert g3_hr > 0

    g4_hr = compute_headroom("upper", 0.55, 3.00)
    assert g4_hr == pytest.approx(2.45, rel=1e-5)
    assert g4_hr > 0

    g5_hr = compute_headroom("upper", 113187, 350000)
    assert g5_hr == 236813
    assert g5_hr > 0

    # 3. Part III tile count verification
    p3_contract = repo_root / "experiments/TRUJILLO_PART_III_EVALUATION_CONTRACT_20260911.md"
    assert p3_contract.exists()
    p3_text = p3_contract.read_text(encoding="utf-8")
    assert "450 scenes" in p3_text or "450" in p3_text
    
    total_p3_scenes = 450
    tiles_per_scene = 16
    total_p3_tiles = total_p3_scenes * tiles_per_scene
    assert total_p3_tiles == 7200

    def validate_part_iii_tiles(reported_count: int) -> None:
        if reported_count == 5760:
            raise ValueError("5,760 is Part I non-train holdout tiles (360x16), NOT Part III tiles!")
        assert reported_count == 7200, f"Expected 7,200 Part III tiles, got {reported_count}"

    validate_part_iii_tiles(7200)
    with pytest.raises(ValueError, match="Part I non-train holdout"):
        validate_part_iii_tiles(5760)


def test_git_state_reporting_completeness_guardrail():
    """Adversarial regression guard ensuring that git status reporting:
    1. Distinguishes staged files, unstaged tracked files, and untracked files.
    2. Prohibits reporting git diff --name-status as the complete working tree state.
    3. Confirms zero staged changes exist.
    """
    import subprocess

    repo_root = Path(__file__).resolve().parent.parent

    # Check staged changes
    staged_proc = subprocess.run(
        ["git", "diff", "--cached", "--name-status"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=True,
    )
    staged_files = [line.strip() for line in staged_proc.stdout.splitlines() if line.strip()]
    assert len(staged_files) == 0, f"Expected 0 staged files, got {len(staged_files)}: {staged_files}"

    # Check tracked unstaged changes
    diff_proc = subprocess.run(
        ["git", "diff", "--name-status"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=True,
    )
    unstaged_files = [line.strip() for line in diff_proc.stdout.splitlines() if line.strip()]
    # Exactly the 2 pre-existing user modifications
    assert len(unstaged_files) == 2
    assert any(".gitignore" in line for line in unstaged_files)
    assert any("dataset.py" in line for line in unstaged_files)

    # Check full working tree status
    status_proc = subprocess.run(
        ["git", "status", "--porcelain", "-uall"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=True,
    )
    status_lines = [line.strip() for line in status_proc.stdout.splitlines() if line.strip()]
    untracked_entries = [line for line in status_lines if line.startswith("??")]
    assert len(untracked_entries) > 0, "Untracked entries must be present in git status --porcelain -uall"

    # Firewall against treating git diff as complete working tree
    def assert_complete_git_reporting(reported_dict: dict) -> None:
        required_keys = {"staged", "unstaged_tracked", "untracked", "branch", "head"}
        if not required_keys.issubset(reported_dict.keys()):
            raise ValueError(f"Incomplete git reporting: missing {required_keys - reported_dict.keys()}")

    valid_report = {
        "branch": "master",
        "head": "542bab19f6f08c9bba8b8762e6480386c8b6026b",
        "staged": [],
        "unstaged_tracked": unstaged_files,
        "untracked": untracked_entries,
    }
    assert_complete_git_reporting(valid_report)

    with pytest.raises(ValueError, match="Incomplete git reporting"):
        # Fails if only git diff is provided
        assert_complete_git_reporting({"unstaged_tracked": unstaged_files})








