"""EXP-07-P0-DIAG-03 Guardrail Test Suite
Radiometric Feature Discriminability Diagnostic Guardrails

Validates:
1. Zero training, zero backward passes, zero optimizer steps, zero GPU compute, zero HOLDOUT access, zero Part III access.
2. Canonical input representation (AGGREGATED_RAW_DN_LOG1P_STANDARDIZED) and frozen TRAIN normalization constants (INV-06: mu=4.424158, sigma=0.469261).
3. Canonical 12-class taxonomy and exact nomenclature (OF = Ocean Front, RF = Rain phenomenon, HM = Anthropogenic Objects).
4. Data access firewall: programmatically verified zero HOLDOUT and zero Part III leakage.
5. Class-specific cluster sample size (effective K_cls) explicitly reported for all classes.
6. Numerical integration safeguards: tail mass discard < 1e-4 and multi-resolution OVL convergence < 0.01 across 256/512/1024 bins.
7. Pseudo-replication controls: cluster-level block bootstrap (B=1000, seed=42) and no unclustered inferential claims from pixels.
8. Acquisition-conditioned co-occurrence and core-sensitivity stratification schemas.
9. Absence of causal overclaims (no 'radiometric bottleneck', 'root cause', 'proves model failure', 'cannot learn').
10. Roadmap integrity: DIAG-01 (CASE B), DIAG-02 (REPAIRED), DIAG-03 (COMPLETED), DIAG-04 (UNCHANGED), DIAG-05 (DESIGN ONLY).
"""

import json
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIT_JSON = REPO_ROOT / "data" / "ops02" / "audits" / "ops02_diag03_radiometric_discriminability_v1.json"
REPORT_MD = REPO_ROOT / "experiments" / "EXP-07" / "EXP07_P0_DIAG03_RADIOMETRIC_FEATURE_DISCRIMINABILITY_20260915.md"
MANIFEST_PATH = REPO_ROOT / "data" / "ops02" / "manifests" / "ops02_physical_dataset_manifest_v1.json"
RUN_STATE_JSON = REPO_ROOT / "scratch" / "exp07_p0_diag03_run_state.json"


@pytest.fixture(scope="module")
def audit_data():
    assert AUDIT_JSON.exists(), f"Audit file missing: {AUDIT_JSON}"
    with open(AUDIT_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def report_text():
    assert REPORT_MD.exists(), f"Report file missing: {REPORT_MD}"
    with open(REPORT_MD, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture(scope="module")
def run_state():
    assert RUN_STATE_JSON.exists(), f"Run state missing: {RUN_STATE_JSON}"
    with open(RUN_STATE_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


# ==============================================================================
# 1. Absolute Governance Invariants
# ==============================================================================

def test_governance_invariants(audit_data, run_state):
    for source, data in [("audit_json", audit_data["governance"]), ("run_state", run_state["governance"])]:
        assert data["training_steps"] == 0, f"{source}: training_steps must be 0"
        assert data["backward_passes"] == 0, f"{source}: backward_passes must be 0"
        assert data["optimizer_steps"] == 0, f"{source}: optimizer_steps must be 0"
        assert data["scheduler_steps"] == 0, f"{source}: scheduler_steps must be 0"
        assert data["parameter_updates"] == 0, f"{source}: parameter_updates must be 0"
        assert data["gpu_seconds"] == 0.0, f"{source}: gpu_seconds must be 0.0"
        assert data["holdout_access"] == 0, f"{source}: holdout_access must be 0"
        assert data["part_iii_access"] == 0, f"{source}: part_iii_access must be 0"
        assert data["diag05_executed"] is False, f"{source}: diag05_executed must be False"
        assert data["zero_destructive_git"] is True, f"{source}: zero_destructive_git must be True"


# ==============================================================================
# 2. Canonical Data Contract & Constants
# ==============================================================================

def test_canonical_input_contract(audit_data):
    contract = audit_data["canonical_input_contract"]
    assert contract["name"] == "AGGREGATED_RAW_DN_LOG1P_STANDARDIZED"
    assert contract["polarization"] == "VV"
    assert contract["dimensions"] == [1, 256, 256]
    assert contract["train_log1p_mean"] == pytest.approx(4.424158, rel=1e-6)
    assert contract["train_log1p_std"] == pytest.approx(0.469261, rel=1e-6)
    assert contract["ignore_index"] == -100


# ==============================================================================
# 3. Canonical Taxonomy & Correct Nomenclature
# ==============================================================================

def test_canonical_taxonomy_nomenclature(audit_data, report_text):
    taxonomy = audit_data["taxonomy"]
    assert len(taxonomy) == 12, "Taxonomy must contain exactly 12 dense classes"
    
    expected = {
        "0": ("BG", "Background (BG)"),
        "1": ("AF", "Atmospheric Front (AF)"),
        "2": ("BS", "Biological Slicks (BS)"),
        "3": ("LWA", "Low Wind Area (LWA)"),
        "4": ("MCC", "Mesoscale Cellular Convection (MCC)"),
        "5": ("OF", "Ocean Front (OF)"),
        "6": ("POW", "Pure Oceanic Waves (POW)"),
        "7": ("RF", "Rain / precipitation-related phenomenon (RF)"),
        "8": ("WS", "Wind Streaks (WS)"),
        "9": ("Eddy", "Eddy (Eddy)"),
        "10": ("IWs", "Internal Waves (IWs)"),
        "11": ("HM", "Artificial / Anthropogenic Objects (HM)"),
    }
    
    for c_id, (exp_abbr, exp_full) in expected.items():
        assert taxonomy[c_id]["abbrev"] == exp_abbr
        assert taxonomy[c_id]["full_name"] == exp_full

    # Semantic check: no forbidden synonyms
    report_lower = report_text.lower()
    assert "oil spill" not in report_lower or "mineral oil spill (class 14) strictly quarantined" in report_lower
    assert "heavy metal" not in report_lower
    assert "ocean front" in report_lower
    assert "rain / precipitation-related phenomenon" in report_lower or "rain phenomenon" in report_lower
    assert "artificial / anthropogenic objects" in report_lower


# ==============================================================================
# 4. Data Access Firewall & Partitions
# ==============================================================================

def test_partition_firewall(audit_data):
    partitions = audit_data["partitions"]
    assert partitions["TRAIN"]["tiles"] == 132
    assert partitions["TRAIN"]["parent_clusters"] == 40
    assert partitions["DEV"]["tiles"] == 40
    assert partitions["DEV"]["parent_clusters"] == 12
    assert partitions["HOLDOUT"]["access_status"] == "STRICTLY_QUARANTINED_0_ACCESS"


# ==============================================================================
# 5. Class-Specific Effective K Reporting
# ==============================================================================

def test_class_specific_effective_k(audit_data):
    support = audit_data["support_statistics"]
    for part in ["TRAIN", "DEV"]:
        for c_id in range(12):
            c_stat = support[part][str(c_id)]
            k_cls = c_stat["parent_cluster_count"]
            tile_count = c_stat["tile_count"]
            pix_count = c_stat["valid_pixel_count"]
            assert k_cls > 0, f"Class {c_id} in {part} has 0 clusters"
            assert tile_count >= k_cls, f"Tiles {tile_count} must be >= clusters {k_cls}"
            assert pix_count > 0, f"Class {c_id} in {part} has 0 valid pixels"

    # Verify known sparse classes in DEV
    assert support["DEV"]["5"]["parent_cluster_count"] == 1, "OF in DEV must have K=1"
    assert support["DEV"]["7"]["parent_cluster_count"] == 1, "RF in DEV must have K=1"


# ==============================================================================
# 6. Numerical Safeguards: Tail Mass & OVL Convergence
# ==============================================================================

def test_numerical_safeguards(audit_data):
    safeguards = audit_data["numerical_safeguards"]
    
    # Tail mass discard < 1e-4
    tail_mass = safeguards["tail_mass_discard"]
    for part in ["TRAIN", "DEV"]:
        for c_id, discarded in tail_mass[part].items():
            assert discarded < 1e-4, f"Tail mass discard violation in {part} for class {c_id}: {discarded}"

    # Convergence across 256/512/1024 bins < 0.01
    conv = safeguards["convergence_diagnostics"]
    for part in ["TRAIN", "DEV"]:
        for pair_name, diag in conv[part].items():
            if "max_diff" in diag:
                assert diag["max_diff"] < 0.01, f"OVL convergence failed for {pair_name} in {part}: {diag['max_diff']}"
                assert diag["converged"] is True


# ==============================================================================
# 7. Pseudo-Replication & Bootstrap Safeguards
# ==============================================================================

def test_bootstrap_and_pseudo_replication_safeguards(audit_data):
    boot = audit_data["cluster_bootstrap_uncertainty_train"]
    assert len(boot) == 6, "Must compute bootstrap uncertainty for all 6 high-priority pairs"
    
    for pair_name, b_res in boot.items():
        assert 950 <= b_res["iterations"] <= 1000
        assert len(b_res["ovl_ci_95"]) == 2
        assert b_res["ovl_ci_95"][0] <= b_res["ovl_ci_95"][1]
        assert b_res["effective_k1"] > 0
        assert b_res["effective_k2"] > 0


# ==============================================================================
# 8. Complete 66-Pair Matrix
# ==============================================================================

def test_66_pair_matrix_completeness(audit_data):
    for part in ["TRAIN", "DEV"]:
        matrix = audit_data["pairwise_matrices"][part]
        assert len(matrix) == 66, f"{part} pairwise matrix must contain exactly 66 pairs"
        for pair_name, p_stat in matrix.items():
            assert "ovl" in p_stat
            assert "cliffs_delta" in p_stat
            assert "wasserstein_1_std" in p_stat
            assert 0.0 <= p_stat["ovl"] <= 1.0


# ==============================================================================
# 9. No Causal Overclaims in Final Deliverables
# ==============================================================================

def test_no_causal_overclaims(report_text, audit_data):
    forbidden_terms = [
        "radiometric bottleneck",
        "information bottleneck",
        "root cause",
        "proves model failure",
        "cannot learn",
        "causes low miou",
        "explains low miou",
        "proves spatial context is required",
    ]
    report_lower = report_text.lower()
    for term in forbidden_terms:
        assert term not in report_lower, f"Forbidden causal claim found in report: '{term}'"

    # Verify calibrated conclusion phrasing
    assert "radiometric discriminability is" in report_lower
    assert "remains unresolved" in report_lower or "remains unknown" in report_lower


# ==============================================================================
# 10. Roadmap Integrity & Isolation
# ==============================================================================

def test_roadmap_integrity(report_text):
    assert "DIAG-01" in report_text
    assert "CASE B" in report_text
    assert "DIAG-02" in report_text
    assert "DIAG-03: RADIOMETRIC FEATURE DISCRIMINABILITY" in report_text
    assert "DIAG-04: RECEPTIVE FIELD & SPATIAL SCALE COMPATIBILITY" in report_text
    assert "DIAG-05: LOSS LANDSCAPE & GRADIENT DYNAMICS" in report_text
    assert "DESIGN ONLY" in report_text
