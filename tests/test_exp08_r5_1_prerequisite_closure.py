"""Stage 14 Guardrail Tests — Phase 11-R5.1 EXP-08 Final Spatial-Fidelity + Protocol Closure.

Validates all 14 Stage 14 invariants:
1. 64x64 over a DARTIS patch cannot be labeled spatially compatible solely from tensor shape
2. Spatial compatibility requires comparison against the actual frozen Trujillo/EXP-06 grid
3. Process API output resolution must be recorded explicitly
4. Channel source-truth UNKNOWN and operational EXP-06 mapping coexist only when distinguished
5. No document may claim catalog-wide CDSE resolution from a 40-scene sample
6. Raw and processed radiometric representations must remain distinct
7. SIGMA0_ELLIPSOID must be declared explicitly for the selected route
8. dB conversion must be explicit
9. Nodata/dataMask must not become valid model pixels silently
10. Spatial overlap must not be labeled statistical independence
11. 5,515 remains rejected as a scientific patch denominator
12. 2,290 is the no-oil patch denominator
13. 1,365 is the oil patch denominator
14. EXECUTION_AUTHORIZED must remain FALSE
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

REPO = Path(__file__).parent.parent


class TestSpatialGridFidelityR51:
    """Invariants 1, 2, 3: Spatial grid fidelity and resolution matching."""

    @pytest.fixture
    def pilot_results(self) -> list[dict]:
        path = REPO / "scratch" / "cdse_physical_pilot_results_r5_1.json"
        assert path.exists(), "cdse_physical_pilot_results_r5_1.json must exist"
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    @pytest.fixture
    def protocol_content(self) -> str:
        path = REPO / "docs" / "exp08_corrected_protocol.md"
        assert path.exists()
        return path.read_text(encoding="utf-8")

    def test_64x64_is_rejected_as_spatially_compatible(self, protocol_content: str):
        """Invariant 1: A 64x64 raster over a DARTIS patch cannot be deemed spatially compatible."""
        # The pilot doc and protocol must require true resolution matching, not 64x64 tensor shape match
        pilot_doc = (REPO / "docs" / "exp08_cdse_physical_compatibility_pilot.md").read_text(encoding="utf-8")
        assert "64×64 rasters (~232m pixel spacing)" in pilot_doc or "coarse 64×64" in pilot_doc
        assert "failed to achieve spatial-resolution equivalence" in pilot_doc

    def test_spatial_compatibility_matches_trujillo_grid(self, pilot_results: list[dict]):
        """Invariant 2: Target spatial grid must match Trujillo grid (dx=dy ~ 8.98315e-5 deg, ~10m)."""
        trujillo_ref = 8.983152841195215e-05
        for p in pilot_results:
            assert p["status"] == "SUCCESS"
            # Width and height must cover full patch at ~10m resolution (>= 1000 pixels)
            assert p["width"] >= 1000
            assert p["height"] >= 1000
            res_x, res_y = p["angular_resolution"]
            # Angular resolution deviation must be under 0.05%
            assert abs(res_x - trujillo_ref) / trujillo_ref < 0.0005
            assert abs(res_y - trujillo_ref) / trujillo_ref < 0.0005
            assert p["statuses"]["spatial_grid"] == "SPATIAL_GRID_COMPATIBLE"

    def test_process_api_output_resolution_recorded_explicitly(self, pilot_results: list[dict]):
        """Invariant 3: Output resolution must be recorded explicitly with metric equivalents."""
        for p in pilot_results:
            assert "angular_resolution" in p
            assert "approx_pixel_spacing_meters" in p
            lat_m = p["approx_pixel_spacing_meters"]["latitude_meters"]
            assert abs(lat_m - 10.0) < 0.5, f"Latitude spacing must be ~10m, got {lat_m}"


class TestChannelMappingAndRadiometryR51:
    """Invariants 4, 6, 7, 8, 9: Channel semantics, radiometric routes, dB, and dataMask."""

    @pytest.fixture
    def protocol_content(self) -> str:
        return (REPO / "docs" / "exp08_corrected_protocol.md").read_text(encoding="utf-8")

    def test_channel_mapping_distinguishes_source_truth_and_operational(self, protocol_content: str):
        """Invariant 4: Source truth UNKNOWN and operational contract VERIFIED_WITH_LIMITATIONS distinct."""
        assert "UNKNOWN / UNVERIFIED AT SOURCE" in protocol_content
        assert "VERIFIED_WITH_LIMITATIONS" in protocol_content

    def test_raw_and_processed_radiometric_representations_distinct(self, protocol_content: str):
        """Invariant 6: Raw COG (DN amplitude) and processed (sigma0) must be distinguished."""
        assert "Raw CDSE COG files are NOT calibrated sigma0 dB" in protocol_content
        assert "contain raw DN amplitude" in protocol_content

    def test_sigma0_ellipsoid_declared_explicitly(self):
        """Invariant 7: Selected route explicitly specifies SIGMA0_ELLIPSOID."""
        pilot_doc = (REPO / "docs" / "exp08_cdse_physical_compatibility_pilot.md").read_text(encoding="utf-8")
        assert "SIGMA0_ELLIPSOID" in pilot_doc

    def test_db_conversion_is_explicit(self):
        """Invariant 8: dB conversion formula is explicitly 10 * log10."""
        from ocean_sentinel.satellite.calibration import linear_to_db
        arr = np.array([1.0, 0.1, 0.01], dtype=np.float32)
        db = linear_to_db(arr)
        assert np.isclose(db[0], 0.0, atol=1e-3)
        assert np.isclose(db[1], -10.0, atol=1e-3)
        assert np.isclose(db[2], -20.0, atol=1e-3)

    def test_datamask_does_not_become_valid_silently(self):
        """Invariant 9: Invalid dataMask pixels must not become valid ocean pixels."""
        from ocean_sentinel.satellite.calibration import apply_nodata_datamask
        raster = np.ones((2, 4, 4), dtype=np.float32)
        datamask = np.ones((4, 4), dtype=np.uint8)
        datamask[0, 0] = 0  # Invalid pixel
        masked = apply_nodata_datamask(raster, datamask, nodata_value=np.nan)
        assert np.isnan(masked[0, 0, 0])
        assert np.isnan(masked[1, 0, 0])
        assert masked[0, 1, 1] == 1.0


class TestStatisticalDenominatorsAndOverlapR51:
    """Invariants 5, 10, 11, 12, 13, 14: Sample scope, overlap terminology, denominators, and gate."""

    @pytest.fixture
    def protocol_content(self) -> str:
        return (REPO / "docs" / "exp08_corrected_protocol.md").read_text(encoding="utf-8")

    def test_no_catalog_wide_claim_from_sample(self, protocol_content: str):
        """Invariant 5: 40-scene sample cannot be extrapolated to catalog-wide 100% or 97%."""
        assert "40/1,063 scenes explicitly confirmed" in protocol_content
        assert "the remaining 1,023 are NOT proven to be resolvable" in protocol_content

    def test_spatial_overlap_not_labeled_statistical_independence(self):
        """Invariant 10: 1,501 disjoint patches must not be called independent evaluation samples."""
        overlap_doc = (REPO / "docs" / "exp08_spatial_overlap_r4.md").read_text(encoding="utf-8")
        assert "Absence of Footprint Intersection ≠ Proven Statistical Independence" in overlap_doc
        assert "most independent evaluation samples" not in overlap_doc

    def test_5515_rejected_as_patch_denominator(self, protocol_content: str):
        """Invariant 11: 5,515 is rejected as a scientific patch denominator."""
        assert "5,515 is the annotation record count. It is NOT a patch count, object count, or valid scientific denominator" in protocol_content

    def test_no_oil_denominator_is_2290(self, protocol_content: str):
        """Invariant 12: No-oil patch denominator is 2,290."""
        assert "Total no-oil" in protocol_content
        assert "2,290" in protocol_content

    def test_oil_denominator_is_1365(self, protocol_content: str):
        """Invariant 13: Oil patch denominator is 1,365."""
        assert "Total oil" in protocol_content
        assert "1,365" in protocol_content

    def test_execution_authorized_must_remain_false(self, protocol_content: str):
        """Invariant 14: EXECUTION_AUTHORIZED = FALSE throughout."""
        assert "EXECUTION_AUTHORIZED = FALSE" in protocol_content


import numpy as np
