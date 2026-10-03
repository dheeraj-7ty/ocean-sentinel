"""EXP-07 DIAG-05 Tier-1 Forensic and Governance Guardrails.

Protects invariants, cryptographic artifact hashes, edge-case forensic findings,
and statistical contracts validated during DIAG05-TIER1-FORENSIC-ANALYSIS-AND-GOVERNANCE-LEARNING.

Enforces:
- LL-DIAG05-EXEC-001: Post-validity support census and INELIGIBLE_ABSENT_MASK handling
- LL-DIAG05-EXEC-002: Explicit statistical test method binding in non-parametric inference
- LL-DIAG05-EXEC-003: Bounded negative interpretation of Step-0 non-significance (p > 0.05)
"""

import hashlib
import json
from pathlib import Path
from typing import Dict

import numpy as np
import pytest
import scipy.stats

REPO_ROOT = Path(__file__).resolve().parent.parent

TIER1_ARTIFACTS = {
    "diag05_tier1_run_manifest_v1.json": "F8ED430414351000CC3A6C9C184D2B29A18C64F3490295D9AECCF893D31C08A5",
    "diag05_tier1_h1_raw_metrics_v1.json": "5962B1C3A360AADC0B6F5DEA6E9A10545370D06E9A47CD449DA592C38E30D072",
    "diag05_tier1_h1_summary_v1.json": "6FCADA5DADCB5091E4EAB9260CFE758CA37125F11B3AB62A10072FA5FC565768",
    "diag05_tier1_h2_raw_tile_observations_v1.json": "A5A384D25CFF22B9BF724493ACFEC4EAD163E77E3253ED773C83FB6EE7D2B586",
    "diag05_tier1_h2_cluster_summaries_v1.json": "A7D2FC0618CB3CC823D3971045580650DC9B025E91274BF12AFACADD0FACDDD3",
    "diag05_tier1_h2_paired_inference_v1.json": "8BF6C9B3396D21306B666F9B16DB5F9C5716FF126370B7940783D044393D94AB",
    "ops02_diag05_tier1_gradient_dynamics_v1.json": "8DE5FF5383A2C36927673D977C062063FD4D9F144C42351D7E4E302CC2487250",
}


def test_diag05_tier1_artifacts_integrity_and_hashes():
    """1. Assert all 7 registered Tier-1 machine artifacts exist and match cryptographic hashes."""
    for filename, expected_sha in TIER1_ARTIFACTS.items():
        artifact_path = REPO_ROOT / "data" / "ops02" / "audits" / filename
        assert artifact_path.exists(), f"Tier-1 artifact missing: {filename}"
        actual_sha = hashlib.sha256(artifact_path.read_bytes()).hexdigest().upper()
        assert actual_sha == expected_sha, f"SHA-256 mismatch for {filename}: {actual_sha} vs {expected_sha}"


def test_diag05_tier1_execution_counters_and_safety_envelope():
    """2. Assert strictly zero training, optimizer, scheduler, or parameter updates occurred."""
    manifest_p = REPO_ROOT / "data" / "ops02" / "audits" / "diag05_tier1_run_manifest_v1.json"
    manifest = json.loads(manifest_p.read_text(encoding="utf-8"))
    counters = manifest["counters"]

    assert counters["backward_passes"] == 178
    assert counters["optimizer_steps"] == 0
    assert counters["scheduler_steps"] == 0
    assert counters["parameter_updates"] == 0
    assert counters["training_steps"] == 0
    assert counters["gpu_seconds"] == 0.0
    assert counters["holdout_access_count"] == 0
    assert counters["part_iii_access_count"] == 0
    assert manifest["wallclock_elapsed_seconds"] <= 180.0


def test_diag05_h1_dispersion_invariants():
    """3. Assert H1 dispersion invariants: canonical IQR is narrower than uniform IQR at Step 0."""
    h1_summary_p = REPO_ROOT / "data" / "ops02" / "audits" / "diag05_tier1_h1_summary_v1.json"
    h1_raw_p = REPO_ROOT / "data" / "ops02" / "audits" / "diag05_tier1_h1_raw_metrics_v1.json"
    h1_summary = json.loads(h1_summary_p.read_text(encoding="utf-8"))
    h1_raw = json.loads(h1_raw_p.read_text(encoding="utf-8"))

    assert len(h1_raw) == 33
    c_iqr = h1_summary["canonical_dispersion"]["iqr"]
    u_iqr = h1_summary["uniform_dispersion"]["iqr"]
    iqr_ratio = h1_summary["comparative_metrics"]["global_iqr_ratio"]

    assert c_iqr < u_iqr, "Canonical IQR was hypothesized to expand but is strictly narrower."
    assert abs(iqr_ratio - (c_iqr / u_iqr)) < 1e-6
    assert iqr_ratio < 1.0


def test_diag05_post_validity_support_census_guardrail():
    """4. Enforce LL-DIAG05-EXEC-001: Detect post-validity zero-support tiles and verify sensitivity invariance."""
    h2_raw_p = REPO_ROOT / "data" / "ops02" / "audits" / "diag05_tier1_h2_raw_tile_observations_v1.json"
    h2_raw = json.loads(h2_raw_p.read_text(encoding="utf-8"))

    # Exactly 28 raw observations
    assert len(h2_raw) == 28

    # Identify edge-case tile 15 where post-validity rare support was zero
    zero_support_tiles = [o for o in h2_raw if o["rare_pixel_count"] == 0]
    assert len(zero_support_tiles) == 1, "Expected exactly 1 post-validity zero-support tile (Finding F-DIAG05-001)."
    bad_tile = zero_support_tiles[0]
    assert bad_tile["sample_id"] == "s1a-iw-grd-vv-20220129t174639-20220129t174704-041679-04f573-001-22"

    # Sensitivity check: excluding the zero-support tile leaves 15 clusters and non-significant p-value
    valid_tiles = [o for o in h2_raw if o["rare_pixel_count"] > 0]
    assert len(valid_tiles) == 27

    cluster_to_obs: Dict[str, list] = {}
    for o in valid_tiles:
        cluster_to_obs.setdefault(o["parent_scene_id"], []).append(o)

    assert len(cluster_to_obs) == 15, "All 15 clusters must remain represented after excluding zero-support tile."

    c_meds = [float(np.median([x["canonical"]["cos_sim_global"] for x in cluster_to_obs[cid]])) for cid in sorted(cluster_to_obs)]
    u_meds = [float(np.median([x["uniform"]["cos_sim_global"] for x in cluster_to_obs[cid]])) for cid in sorted(cluster_to_obs)]

    res_sens = scipy.stats.wilcoxon(c_meds, u_meds, zero_method="wilcox", correction=True, alternative="two-sided", method="asymptotic")
    assert res_sens.pvalue > 0.05, f"Sensitivity inference became significant (p={res_sens.pvalue})!"
    assert abs(res_sens.statistic - 32.0) < 1e-6


def test_diag05_statistical_method_binding_guardrail():
    """5. Enforce LL-DIAG05-EXEC-002: Verify non-parametric test reproducibility and zero df field."""
    h2_inf_p = REPO_ROOT / "data" / "ops02" / "audits" / "diag05_tier1_h2_paired_inference_v1.json"
    h2_clus_p = REPO_ROOT / "data" / "ops02" / "audits" / "diag05_tier1_h2_cluster_summaries_v1.json"
    h2_inf = json.loads(h2_inf_p.read_text(encoding="utf-8"))
    h2_clus = json.loads(h2_clus_p.read_text(encoding="utf-8"))

    # Recompute both exact permutation and asymptotic p-values
    c_arr = [c["canonical_median_cos_sim"] for c in h2_clus]
    u_arr = [c["uniform_median_cos_sim"] for c in h2_clus]

    res_exact = scipy.stats.wilcoxon(c_arr, u_arr, zero_method="wilcox", correction=True, alternative="two-sided", method="exact")
    res_asymp = scipy.stats.wilcoxon(c_arr, u_arr, zero_method="wilcox", correction=True, alternative="two-sided", method="asymptotic")

    assert abs(h2_inf["statistic"] - 34.0) < 1e-6
    # Artifact recorded exact p-value
    assert abs(h2_inf["p_value"] - res_exact.pvalue) < 1e-6
    # Asymptotic p-value is also non-significant
    assert res_asymp.pvalue > 0.05
    assert abs(res_asymp.pvalue - 0.147532) < 1e-4

    # Assert no arbitrary df field
    assert "df" not in h2_inf
    assert "degrees_of_freedom" not in h2_inf


def test_diag05_bounded_negative_interpretation_guardrail():
    """6. Enforce LL-DIAG05-EXEC-003: Verify forensic analysis report bounds negative findings."""
    report_p = REPO_ROOT / "experiments" / "performance" / "diag05_tier1_forensic_analysis_report.md"
    assert report_p.exists(), "Forensic analysis report missing."
    content = report_p.read_text(encoding="utf-8")

    assert "NOT JUSTIFIED YET" in content
    assert "W = 34.0" in content
    assert "p = 0.1514" in content
    # Prohibit unhedged claims of "no effect"
    assert "there is no effect" not in content.lower()
    assert "proves no effect" not in content.lower()


def test_diag05_lessons_learned_database_consistency():
    """7. Assert newly consolidated lessons LL-DIAG05-EXEC-001 through 003 exist and are REGRESSION_PROTECTED."""
    db_p = REPO_ROOT / "data" / "metadata" / "ocean_sentinel_lessons_learned_v1.json"
    db = json.loads(db_p.read_text(encoding="utf-8"))
    lesson_map = {l["lesson_id"]: l for l in db["lessons"]}

    for lid in ["LL-DIAG05-EXEC-001", "LL-DIAG05-EXEC-002", "LL-DIAG05-EXEC-003"]:
        assert lid in lesson_map, f"Lesson {lid} missing from database."
        assert lesson_map[lid]["status"] == "REGRESSION_PROTECTED"
        assert len(lesson_map[lid]["validation_history"]) >= 1


def test_diag05_corrected_artifacts_integrity_and_reconciliation():
    """8. Assert all 3 versioned corrective machine artifacts exist with complete provenance."""
    corrective_artifacts = [
        "diag05_tier1_corrected_h2_eligibility_census_v1.json",
        "diag05_tier1_corrected_h2_cluster_summaries_v1.json",
        "diag05_tier1_corrected_h2_paired_inference_v1.json",
    ]
    for fname in corrective_artifacts:
        p = REPO_ROOT / "data" / "ops02" / "audits" / fname
        assert p.exists(), f"Corrective artifact {fname} missing!"
        data = json.loads(p.read_text(encoding="utf-8"))
        assert isinstance(data, (dict, list))

    # Check census numbers
    census_p = REPO_ROOT / "data" / "ops02" / "audits" / "diag05_tier1_corrected_h2_eligibility_census_v1.json"
    census = json.loads(census_p.read_text(encoding="utf-8"))
    assert census["summary_counts"]["candidate_population_n"] == 132
    assert census["summary_counts"]["originally_eligible_n"] == 28
    assert census["summary_counts"]["corrected_eligible_n"] == 27
    assert census["summary_counts"]["false_positive_eligibility_n"] == 1
    assert census["summary_counts"]["false_negative_eligibility_n"] == 0
    assert census["summary_counts"]["corrected_represented_clusters_n"] == 15


def test_diag05_corrected_paired_inference_contracts():
    """9. Assert corrected inference reproduces W=32.0, non-significance, and explicit method binding."""
    inf_p = REPO_ROOT / "data" / "ops02" / "audits" / "diag05_tier1_corrected_h2_paired_inference_v1.json"
    inf = json.loads(inf_p.read_text(encoding="utf-8"))

    assert inf["population_dimensions"]["raw_observations_retained_n"] == 27
    assert inf["population_dimensions"]["inferential_paired_clusters_n"] == 15
    assert inf["population_dimensions"]["effective_rankable_clusters_n"] == 15

    reg = inf["corrected_registered_result"]
    assert abs(reg["statistic"] - 32.0) < 1e-6
    assert abs(reg["p_value"] - 0.118313) < 1e-4
    assert reg["significance_verdict_alpha_0_05"] == "NON_SIGNIFICANT"

    exact = inf["corrected_exact_permutation_result"]
    assert abs(exact["statistic"] - 32.0) < 1e-6
    assert abs(exact["p_value"] - 0.120483) < 1e-4
    assert exact["significance_verdict_alpha_0_05"] == "NON_SIGNIFICANT"

    assert "df" not in reg
    assert "degrees_of_freedom" not in reg


def test_diag05_corrective_report_language_and_validity_matrix():
    """10. Assert corrective report eliminates intrinsic claims, bounds negative findings, and sets Tier-2 gate."""
    rep_p = REPO_ROOT / "experiments" / "performance" / "diag05_tier1_corrective_analysis_report_v1.md"
    assert rep_p.exists(), "Corrective report missing!"
    text = rep_p.read_text(encoding="utf-8")

    # Prohibit over-broad claims
    assert "intrinsic structural characteristic" not in text.lower()
    assert "there is no effect" not in text.lower()
    assert "proves no effect" not in text.lower()
    assert "guaranteed" not in text.lower()

    # Assert mandatory validity statuses and gate
    assert "VALID_AND_IMMUTABLE" in text
    assert "DEFECTIVE_ELIGIBILITY_CONSTRUCTION" in text
    assert "SCIENTIFICALLY_RECONCILED_POST_CORRECTION" in text
    assert "NOT_JUSTIFIED_YET" in text


def test_diag05_telemetry_analysis_only_authorization_guard():
    """11. Assert telemetry enforces execution_authorized=false and scientific_execution=false."""
    tel_p = REPO_ROOT / "scratch" / "diag05_preexecution_audit_run_state.json"
    assert tel_p.exists(), "Telemetry file missing!"
    tel = json.loads(tel_p.read_text(encoding="utf-8"))

    assert tel["analysis_authorized"] is True
    assert tel["execution_authorized"] is False
    assert tel["scientific_execution"] is False
    assert tel["backward_passes"] == 0
    assert tel["training_steps"] == 0
    assert tel["optimizer_steps"] == 0
    assert tel["parameter_updates"] == 0
    assert tel["gpu_seconds"] == 0.0
    assert tel["holdout_access_count"] == 0
    assert tel["part_iii_access_count"] == 0

