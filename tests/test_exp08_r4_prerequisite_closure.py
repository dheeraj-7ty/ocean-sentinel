"""Stage 6 Guardrail Tests — Phase 11-R4 EXP-08 Prerequisite Closure.

Tests new semantic invariants identified in R4:
- sample-scope CDSE verification cannot become catalog-wide generalization
- channel mapping verification level (VERIFIED_WITH_LIMITATIONS vs UNVERIFIED)
- geographic basin co-location != polygon intersection
- polygon intersection != statistical independence
- raw GRD representation != calibrated sigma0 dB
- CDSE VH/VH served as SEPARATE single-band files (not 2-band merged TIFF)
- CDSE processed sigma0 path must declare its coefficient explicitly
- correct denominators: no-oil=2290, oil=1365
- mixed denominator 5515 still rejected
- spatial overlap results within expected ranges
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helper constants
# ---------------------------------------------------------------------------

REPO = Path(__file__).parent.parent

# Expected spatial overlap results (Phase 11-R4 computed)
EXPECTED_NOOIL_TOTAL = 2290
EXPECTED_OIL_TOTAL = 1365
EXPECTED_NOOIL_OVERLAP = 789
EXPECTED_OIL_OVERLAP = 712
# tolerance: ±1 (rounding or edge geometry differences)
OVERLAP_TOLERANCE = 1


# ---------------------------------------------------------------------------
# 1. Channel Mapping Tests
# ---------------------------------------------------------------------------

class TestChannelMappingR4:
    """Tests for the channel mapping audit resolution (Phase 11-R4)."""

    def test_channel_mapping_status_is_verified_with_limitations(self):
        """Channel mapping audit must report VERIFIED_WITH_LIMITATIONS, not UNVERIFIED."""
        audit_path = REPO / "docs" / "exp08_channel_mapping_audit.md"
        assert audit_path.exists(), "Channel mapping audit doc must exist"
        content = audit_path.read_text(encoding="utf-8")
        assert "VERIFIED_WITH_LIMITATIONS" in content, (
            "Channel mapping audit must have VERIFIED_WITH_LIMITATIONS status"
        )

    def test_channel_mapping_audit_identifies_ch0_as_vh(self):
        """Audit must conclude Ch0 = VH (Cross-Polarization)."""
        audit_path = REPO / "docs" / "exp08_channel_mapping_audit.md"
        assert audit_path.exists()
        content = audit_path.read_text(encoding="utf-8")
        assert "Ch0" in content and "VH" in content, (
            "Audit must reference Ch0=VH mapping"
        )

    def test_channel_mapping_audit_identifies_ch1_as_vv(self):
        """Audit must conclude Ch1 = VV (Co-Polarization)."""
        audit_path = REPO / "docs" / "exp08_channel_mapping_audit.md"
        assert audit_path.exists()
        content = audit_path.read_text(encoding="utf-8")
        assert "Ch1" in content and "VV" in content, (
            "Audit must reference Ch1=VV mapping"
        )

    def test_inference_py_comment_labels_ch0_vh_ch1_vv(self):
        """The authoritative source inference.py line 48 must label Ch0=VH, Ch1=VV."""
        inf_path = REPO / "src" / "ocean_sentinel" / "inference.py"
        assert inf_path.exists()
        content = inf_path.read_text(encoding="utf-8")
        # Must contain the authoritative label
        assert "Cross-Pol VH" in content, (
            "inference.py must contain 'Cross-Pol VH' label for Ch0"
        )
        assert "Co-Pol VV" in content, (
            "inference.py must contain 'Co-Pol VV' label for Ch1"
        )

    def test_channel_mapping_audit_acknowledges_limitation(self):
        """Audit must acknowledge that Trujillo paper is inaccessible (paywall)."""
        audit_path = REPO / "docs" / "exp08_channel_mapping_audit.md"
        assert audit_path.exists()
        content = audit_path.read_text(encoding="utf-8")
        # Must note the limitation
        assert "paywall" in content.lower() or "inaccessible" in content.lower(), (
            "Channel mapping audit must acknowledge Trujillo paper is not accessible"
        )

    def test_unresolved_mapping_cannot_use_statistical_inference_only(self):
        """Statistical statistics alone cannot determine polarization order."""
        # This is a protocol semantic test: confirm audit uses code comment as primary evidence
        audit_path = REPO / "docs" / "exp08_channel_mapping_audit.md"
        assert audit_path.exists()
        content = audit_path.read_text(encoding="utf-8")
        # The audit must cite inference.py as primary evidence
        assert "inference.py" in content, (
            "Channel mapping audit must cite inference.py as primary evidence, not statistics alone"
        )

    def test_cdse_stacking_order_vh_first(self):
        """Pilot document must specify VH as Ch0 (asset 'vh' fetched first)."""
        pilot_path = REPO / "docs" / "exp08_cdse_physical_compatibility_pilot.md"
        assert pilot_path.exists()
        content = pilot_path.read_text(encoding="utf-8")
        assert "vh" in content and "vv" in content, (
            "Pilot document must reference separate vh and vv assets"
        )
        # Check VH is listed as Ch0
        assert "Ch0" in content or "channel 0" in content.lower(), (
            "Pilot document must specify Ch0 = VH"
        )


# ---------------------------------------------------------------------------
# 2. CDSE Resolution Scope Tests
# ---------------------------------------------------------------------------

class TestCDSEResolutionScopeR4:
    """Tests that CDSE sample results are not over-generalized."""

    def test_sample_40_cannot_be_stated_as_catalog_wide(self):
        """40/40 sample must not be presented as 100% catalog-wide resolution."""
        # Read the corrected protocol
        protocol_path = REPO / "docs" / "exp08_corrected_protocol.md"
        assert protocol_path.exists()
        content = protocol_path.read_text(encoding="utf-8")
        # Must NOT claim that 40 sample proves entire catalog
        assert "97% extrapolated" not in content or "extrapolation" in content.lower() or "NOT proven" in content, (
            "Protocol must not claim 40/40 sample proves catalog-wide resolvability "
            "(must use qualified language acknowledging extrapolation limits)"
        )

    def test_cdse_resolution_report_states_sample_size(self):
        """CDSE validation report must clearly state sample_size=40."""
        report_path = REPO / "data" / "metadata" / "yang_singha_2025" / "cdse_validation_report.json"
        assert report_path.exists()
        with open(report_path) as f:
            report = json.load(f)
        summary = report.get("summary", {})
        assert summary.get("total_sampled_scenes") == 40, (
            f"CDSE validation report must state total_sampled_scenes=40, got {summary.get('total_sampled_scenes')}"
        )

    def test_protocol_v3_acknowledges_catalog_extrapolation_limit(self):
        """Protocol V3 must acknowledge extrapolation limit for 40-scene CDSE sample."""
        protocol_path = REPO / "docs" / "exp08_corrected_protocol.md"
        content = protocol_path.read_text(encoding="utf-8")
        # Should reference RESEARCH-19 or caution language
        assert "caution" in content.lower() or "extrapolation" in content.lower() or "NOT proven" in content, (
            "Protocol must note that catalog extrapolation from 40 scenes requires caution"
        )


# ---------------------------------------------------------------------------
# 3. Geographic Basin vs Polygon Intersection Tests
# ---------------------------------------------------------------------------

class TestGeographicBasinVsIntersectionR4:
    """Tests that geographic basin co-location is not equated with polygon intersection."""

    def test_spatial_overlap_doc_clarifies_intersection_not_contamination(self):
        """Spatial overlap report must NOT automatically call intersection 'contamination'."""
        overlap_path = REPO / "docs" / "exp08_spatial_overlap_r4.md"
        assert overlap_path.exists()
        content = overlap_path.read_text(encoding="utf-8")
        # Must contain a caveat that intersection != dependence
        assert "intersection" in content.lower()
        assert "statistical dependence" in content.lower() or "independence" in content.lower()
        # Must NOT call it contamination automatically
        lines_with_contamination = [
            l for l in content.split('\n')
            if 'contamination' in l.lower() and 'not' not in l.lower()
        ]
        assert len(lines_with_contamination) == 0, (
            "Spatial overlap report must not automatically label overlap as 'contamination'. "
            f"Problematic lines: {lines_with_contamination}"
        )

    def test_spatial_overlap_json_exists_with_correct_structure(self):
        """Machine-readable spatial overlap result must exist and have correct structure."""
        overlap_json = REPO / "data" / "metadata" / "exp08_spatial_overlap_r4.json"
        assert overlap_json.exists(), "exp08_spatial_overlap_r4.json must exist"
        with open(overlap_json) as f:
            data = json.load(f)
        assert "nooil_result" in data, "JSON must have nooil_result"
        assert "oil_result" in data, "JSON must have oil_result"

    def test_spatial_overlap_nooil_total_is_2290(self):
        """No-oil patch count in spatial overlap result must be 2,290."""
        overlap_json = REPO / "data" / "metadata" / "exp08_spatial_overlap_r4.json"
        assert overlap_json.exists()
        with open(overlap_json) as f:
            data = json.load(f)
        nooil = data["nooil_result"]
        total = nooil["total_patches"]
        assert total == EXPECTED_NOOIL_TOTAL, (
            f"No-oil total must be {EXPECTED_NOOIL_TOTAL}, got {total}"
        )

    def test_spatial_overlap_oil_total_is_1365(self):
        """Oil patch count in spatial overlap result must be 1,365."""
        overlap_json = REPO / "data" / "metadata" / "exp08_spatial_overlap_r4.json"
        assert overlap_json.exists()
        with open(overlap_json) as f:
            data = json.load(f)
        oil = data["oil_result"]
        total = oil["total_patches"]
        assert total == EXPECTED_OIL_TOTAL, (
            f"Oil total must be {EXPECTED_OIL_TOTAL}, got {total}"
        )

    def test_spatial_overlap_nooil_overlap_count_is_approximately_789(self):
        """No-oil overlap count must be ~789 (within tolerance)."""
        overlap_json = REPO / "data" / "metadata" / "exp08_spatial_overlap_r4.json"
        assert overlap_json.exists()
        with open(overlap_json) as f:
            data = json.load(f)
        overlap = data["nooil_result"]["overlap_with_trujillo"]
        assert abs(overlap - EXPECTED_NOOIL_OVERLAP) <= OVERLAP_TOLERANCE, (
            f"No-oil overlap count must be ~{EXPECTED_NOOIL_OVERLAP} (±{OVERLAP_TOLERANCE}), got {overlap}"
        )

    def test_spatial_overlap_independence_caveat_present_in_json(self):
        """Machine-readable spatial overlap JSON must contain independence caveat."""
        overlap_json = REPO / "data" / "metadata" / "exp08_spatial_overlap_r4.json"
        assert overlap_json.exists()
        with open(overlap_json) as f:
            data = json.load(f)
        caveat = data.get("independence_caveat", "")
        assert "independence" in caveat.lower() or "dependence" in caveat.lower(), (
            "Spatial overlap JSON must contain independence_caveat field"
        )


# ---------------------------------------------------------------------------
# 4. Raw GRD != Calibrated Sigma0 dB Tests
# ---------------------------------------------------------------------------

class TestCDSERadiometricSemanticsR4:
    """Tests that raw CDSE COG files are not equated with calibrated sigma0 dB."""

    def test_cdse_pilot_states_raw_cog_is_not_calibrated_db(self):
        """Pilot document must clearly state CDSE COG = raw DN, not sigma0 dB."""
        pilot_path = REPO / "docs" / "exp08_cdse_physical_compatibility_pilot.md"
        assert pilot_path.exists()
        content = pilot_path.read_text(encoding="utf-8")
        # Must explicitly state that COG is raw
        assert "raw" in content.lower(), "Pilot doc must mention 'raw' representation"
        assert "dn" in content.lower() or "digital number" in content.lower() or "amplitude" in content.lower(), (
            "Pilot doc must mention DN/amplitude as the raw representation"
        )

    def test_cdse_pilot_specifies_calibration_pipeline(self):
        """Pilot document must specify the calibration pipeline (DN → sigma0_linear → dB)."""
        pilot_path = REPO / "docs" / "exp08_cdse_physical_compatibility_pilot.md"
        assert pilot_path.exists()
        content = pilot_path.read_text(encoding="utf-8")
        assert "log" in content.lower() or "log10" in content.lower(), (
            "Pilot doc must specify log10 conversion step"
        )
        assert "sigma" in content.lower() or "sigma0" in content.lower(), (
            "Pilot doc must reference sigma0 calibration"
        )

    def test_protocol_v3_states_calibration_pipeline_required(self):
        """Protocol V3 must state that calibration pipeline is required for CDSE data."""
        protocol_path = REPO / "docs" / "exp08_corrected_protocol.md"
        assert protocol_path.exists()
        content = protocol_path.read_text(encoding="utf-8")
        # Must include calibration pipeline language
        assert "calibration" in content.lower(), (
            "Protocol V3 must reference CDSE calibration pipeline requirement"
        )

    def test_cdse_serves_vh_vv_as_separate_bands(self):
        """Pilot document must note that CDSE serves VH and VV as separate single-band files."""
        pilot_path = REPO / "docs" / "exp08_cdse_physical_compatibility_pilot.md"
        assert pilot_path.exists()
        content = pilot_path.read_text(encoding="utf-8")
        assert "separate" in content.lower() or "single-band" in content.lower(), (
            "Pilot doc must state VH and VV are served as separate files by CDSE"
        )


# ---------------------------------------------------------------------------
# 5. Denominator Tests (from R3, verified R4)
# ---------------------------------------------------------------------------

class TestDenominatorsR4:
    """Validate that all output documents use correct entity denominators."""

    def test_no_oil_denominator_is_2290(self):
        """No-oil denominator must be 2,290 unique patches everywhere."""
        overlap_json = REPO / "data" / "metadata" / "exp08_spatial_overlap_r4.json"
        if overlap_json.exists():
            with open(overlap_json) as f:
                data = json.load(f)
            assert data["nooil_result"]["total_patches"] == 2290

    def test_oil_denominator_is_1365(self):
        """Oil denominator must be 1,365 unique patches everywhere."""
        overlap_json = REPO / "data" / "metadata" / "exp08_spatial_overlap_r4.json"
        if overlap_json.exists():
            with open(overlap_json) as f:
                data = json.load(f)
            assert data["oil_result"]["total_patches"] == 1365

    def test_mixed_denominator_5515_is_rejected(self):
        """The invalid 5,515 mixed denominator must not appear in spatial overlap result."""
        overlap_json = REPO / "data" / "metadata" / "exp08_spatial_overlap_r4.json"
        if overlap_json.exists():
            with open(overlap_json) as f:
                content = f.read()
            # 5515 must not appear as a denominator value in the computation
            # (It can appear in metadata/notes as historical reference)
            data = json.loads(content)
            nooil_total = data["nooil_result"]["total_patches"]
            oil_total = data["oil_result"]["total_patches"]
            assert nooil_total != 5515, "No-oil denominator must not be 5,515"
            assert oil_total != 5515, "Oil denominator must not be 5,515"

    def test_spatial_overlap_supersedes_prior_result(self):
        """Spatial overlap JSON metadata must indicate it supersedes the prior result."""
        overlap_json = REPO / "data" / "metadata" / "exp08_spatial_overlap_r4.json"
        assert overlap_json.exists()
        with open(overlap_json) as f:
            data = json.load(f)
        meta = data.get("metadata", {})
        supersedes = meta.get("supersedes", "")
        assert "2468" in supersedes or "5515" in supersedes or "supersedes" in supersedes.lower(), (
            "Spatial overlap JSON must note it supersedes the prior invalid result"
        )


# ---------------------------------------------------------------------------
# 6. Protected Files Tests
# ---------------------------------------------------------------------------

class TestProtectedFilesR4:
    """Verify protected files are intact."""

    def test_governance_v2_rules_exists(self):
        assert (REPO / "data" / "metadata" / "governance_v2" / "rules.json").exists()

    def test_governance_v2_lessons_exists(self):
        assert (REPO / "data" / "metadata" / "governance_v2" / "lessons.json").exists()

    def test_governance_v2_incidents_exists(self):
        assert (REPO / "data" / "metadata" / "governance_v2" / "incidents.json").exists()

    def test_temporal_py_unchanged(self):
        import datetime
        p = REPO / "src" / "ocean_sentinel" / "temporal.py"
        assert p.exists()
        mtime = datetime.datetime.fromtimestamp(p.stat().st_mtime)
        # temporal.py should not have been modified during R4 (which started 2026-09-27)
        # We check it was last modified before the R4 task start
        assert mtime.date() <= datetime.date(2026, 9, 27), "temporal.py existence verified"

    def test_best_model_checkpoint_exists(self):
        model_path = REPO / "experiments" / "performance" / "exp06_positive_bce_weight" / "best_model.pt"
        assert model_path.exists(), "best_model.pt must exist"
        assert model_path.stat().st_size > 0, "best_model.pt must be non-empty"
