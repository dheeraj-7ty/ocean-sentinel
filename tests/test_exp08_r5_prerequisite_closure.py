"""Stage 9 Guardrail Tests — Phase 11-R5 EXP-08 Final Prerequisite Closure.

Validates all Phase 11-R5 semantic invariants:
1. Reconciled channel-mapping distinction in Protocol V3 (Source Truth vs Operational Contract)
2. Protocol cannot simultaneously assert unqualified UNVERIFIED and VERIFIED_WITH_LIMITATIONS
3. Physical pilot execution results in scratch/cdse_physical_pilot_results_r5.json (3/3 scenes)
4. Measured float32 dtype, EPSG:4326 CRS, and stacked shape (2, H, W)
5. Physical SAR cross-pol suppression observed in all pilot scenes (VH < VV by >= 10 dB)
6. Pre-registered 2-strata spatial overlap analysis plan in Protocol V3
7. Superseded status of historical 2468/3047 mixed-entity calculation in EXTERNAL_VALIDATION_READINESS.md

EXECUTION_AUTHORIZED = FALSE (Unit & guardrail verification only).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent


class TestProtocolV3ContradictionReconciliation:
    """Verifies that Protocol V3 reconciles the channel mapping contradiction."""

    @pytest.fixture
    def protocol_content(self) -> str:
        protocol_path = REPO / "docs" / "exp08_corrected_protocol.md"
        assert protocol_path.exists(), "Protocol V3 must exist"
        return protocol_path.read_text(encoding="utf-8")

    def test_protocol_separates_source_truth_and_operational_contract(self, protocol_content: str):
        """Protocol Section 10 must explicitly distinguish source truth from operational contract."""
        assert "Ontological Separation: Source Truth vs Operational Contract" in protocol_content, (
            "Protocol Section 10 must contain the ontological separation header"
        )
        assert "UNKNOWN / UNVERIFIED AT SOURCE" in protocol_content, (
            "Protocol must classify dataset-source truth as UNKNOWN / UNVERIFIED AT SOURCE"
        )
        assert "VERIFIED_WITH_LIMITATIONS" in protocol_content, (
            "Protocol must classify EXP-06 operational contract as VERIFIED_WITH_LIMITATIONS"
        )

    def test_protocol_does_not_assert_unqualified_unverified_mapping(self, protocol_content: str):
        """Protocol must not contain the obsolete unqualified 'Formal status: UNVERIFIED' line."""
        assert "Formal status: `UNVERIFIED`" not in protocol_content, (
            "Obsolete unqualified 'Formal status: UNVERIFIED' must not appear in Section 10"
        )

    def test_protocol_stopping_rules_enforce_operational_mapping(self, protocol_content: str):
        """Stopping rules must enforce EXP06_OPERATIONAL_MAPPING (Ch0=VH, Ch1=VV)."""
        assert "EXP06_OPERATIONAL_MAPPING" in protocol_content or "Ch0 = VH, Ch1 = VV" in protocol_content, (
            "Stopping rules must enforce operational channel mapping order"
        )

    def test_protocol_version_footer_is_v3(self, protocol_content: str):
        """Footer must declare End of EXP-08 Corrected Protocol V3 or V3.1."""
        assert "*End of EXP-08 Corrected Protocol V3" in protocol_content, (
            "Protocol footer must state Version 3 or V3.1"
        )


class TestPhysicalPilotResultsR5:
    """Validates the actual measured physical pilot results."""

    @pytest.fixture
    def pilot_results(self) -> list[dict]:
        results_path = REPO / "scratch" / "cdse_physical_pilot_results_r5.json"
        assert results_path.exists(), "cdse_physical_pilot_results_r5.json must exist"
        with open(results_path) as f:
            return json.load(f)

    def test_pilot_has_three_scenes(self, pilot_results: list[dict]):
        """Pilot must contain records for all 3 designated scenes."""
        assert len(pilot_results) == 3, f"Expected 3 pilot scenes, got {len(pilot_results)}"

    def test_all_pilot_scenes_succeeded(self, pilot_results: list[dict]):
        """All 3 pilot scenes must report SUCCESS with valid bytes."""
        for rec in pilot_results:
            assert rec["status"] == "SUCCESS", f"Pilot {rec['pilot_index']} did not succeed: {rec}"
            assert rec["bytes_retrieved"] > 10000, f"Pilot {rec['pilot_index']} retrieved too few bytes"

    def test_pilot_data_contract(self, pilot_results: list[dict]):
        """All pilot rasters must match EXP-06 physical contract."""
        for rec in pilot_results:
            assert rec["dtype"] == "float32", f"Pilot {rec['pilot_index']} dtype is not float32"
            assert rec["crs"] == "EPSG:4326", f"Pilot {rec['pilot_index']} CRS is not EPSG:4326"
            assert rec["stacked_shape"] == [2, 64, 64], f"Pilot {rec['pilot_index']} shape is not [2, 64, 64]"
            assert rec["stacked_dtype"] == "float32"
            assert rec["datamask_valid_percentage"] == 100.0

    def test_physical_sar_polarization_separation(self, pilot_results: list[dict]):
        """In all pilot scenes, cross-pol (VH) must be significantly lower than co-pol (VV)."""
        for rec in pilot_results:
            vh_mean = rec["vh_stats_db"]["mean"]
            vv_mean = rec["vv_stats_db"]["mean"]
            assert vh_mean is not None and vv_mean is not None
            # Cross-pol (VH) backscatter over sea must be at least 10 dB lower than co-pol (VV)
            separation = vv_mean - vh_mean
            assert separation >= 10.0, (
                f"Pilot {rec['pilot_index']} has insufficient polarization separation: "
                f"VV={vv_mean:.2f} dB, VH={vh_mean:.2f} dB, sep={separation:.2f} dB"
            )


class TestPreRegisteredAnalysisPlanR5:
    """Verifies that the spatial overlap analysis plan is pre-registered in Protocol V3."""

    @pytest.fixture
    def protocol_content(self) -> str:
        protocol_path = REPO / "docs" / "exp08_corrected_protocol.md"
        assert protocol_path.exists()
        return protocol_path.read_text(encoding="utf-8")

    def test_protocol_defines_two_strata_for_no_oil(self, protocol_content: str):
        """Protocol must define Stratum 1 (1,501 disjoint) and Stratum 2 (789 co-located)."""
        assert "1,501 unique no-oil patches (65.5%)" in protocol_content, (
            "Protocol Section 12.2 must register Stratum 1 with 1,501 patches"
        )
        assert "789 unique no-oil patches (34.5%)" in protocol_content, (
            "Protocol Section 12.2 must register Stratum 2 with 789 patches"
        )

    def test_protocol_preserves_scene_as_primary_unit(self, protocol_content: str):
        """Protocol must mandate scene as primary statistical unit and forbid unclustered CIs."""
        assert "Strict prohibition of unclustered confidence intervals" in protocol_content, (
            "Protocol must explicitly forbid unclustered confidence intervals"
        )


class TestStaleClaimHygieneR5:
    """Verifies that superseded historical claims are marked in external validation doc."""

    def test_external_validation_marks_2468_superseded(self):
        """EXTERNAL_VALIDATION_READINESS.md must mark 2468/3047 as superseded with mixed-entity note."""
        doc_path = REPO / "experiments" / "EXTERNAL_VALIDATION_READINESS.md"
        assert doc_path.exists()
        content = doc_path.read_text(encoding="utf-8")
        assert "[SUPERSEDED / MIXED-ENTITY]" in content, (
            "EXTERNAL_VALIDATION_READINESS.md Section 1 table must label 2468/3047 as SUPERSEDED / MIXED-ENTITY"
        )
        assert "SUPERSEDED RESULT NOTICE" in content, (
            "EXTERNAL_VALIDATION_READINESS.md Section 3.1 must contain the SUPERSEDED RESULT NOTICE"
        )
