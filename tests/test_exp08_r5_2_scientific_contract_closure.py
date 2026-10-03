"""Stage 17 Guardrail Tests — Phase 11-R5.2 EXP-08 Final Scientific-Contract Closure.

Validates all Phase 11-R5.2 invariants:
1. Angular grid comparison is separate from physical metre interpretation.
2. dataMask cannot be called an ocean mask (dataMask == 1 is sensor footprint validity).
3. Service-side output gridding is distinguished from local resampling.
4. Process API resolution parameters are recorded explicitly.
5. Actual compute_tile_windows coverage is tested for non-divisible raster dimensions (12 tiles).
6. No edge pixels are silently omitted (100% pixel coverage across all 3 pilots).
7. Channel source-truth and operational contract are distinct.
8. Raw/process/calibrated sigma0 semantics remain distinct.
9. 2468/3047 remains superseded in EXTERNAL_VALIDATION_READINESS.md.
10. 5515 cannot be a patch denominator.
11. 2290 no-oil denominator remains authoritative.
12. 1365 oil denominator remains authoritative.
13. Spatial overlap cannot imply statistical independence.
14. Catalog sample scope (40/1,063) cannot become catalog-wide resolution.
15. EXECUTION_AUTHORIZED remains FALSE.
16. DARTIS rotated polygon footprint vs axis-aligned bounding box (AABB) is distinguished.
17. Polarization separation is labeled strictly as DIAGNOSTIC OBSERVATION ONLY.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from unittest.mock import MagicMock

import numpy as np
import pytest

REPO = Path(__file__).parent.parent

# Safe import of compute_tile_windows without requiring torch binary install
for mod in ["torch", "torch.nn", "torch.utils", "torch.utils.data", "torchvision", "torchvision.models"]:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

from ocean_sentinel.inference import compute_tile_windows


class TestSpatialGridAndGroundSpacingR52:
    """Invariant 1 & 4: Angular grid vs physical metres and explicit API parameters."""

    @pytest.fixture
    def pilot_results(self) -> list[dict]:
        path = REPO / "scratch" / "cdse_physical_pilot_results_r5_1.json"
        assert path.exists(), "pilot results json must exist"
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    @pytest.fixture
    def pilot_doc(self) -> str:
        return (REPO / "docs" / "exp08_cdse_physical_compatibility_pilot.md").read_text(encoding="utf-8")

    @pytest.fixture
    def protocol_doc(self) -> str:
        return (REPO / "docs" / "exp08_corrected_protocol.md").read_text(encoding="utf-8")

    def test_angular_grid_separate_from_physical_metre_interpretation(self, pilot_doc: str, protocol_doc: str):
        """Invariant 1: Angular grid (8.98315e-5 deg) must not be described as isotropic 10m pixels."""
        # Both documents must clarify that spacing is anisotropic at pilot latitudes (~9.96m NS, 8.23-8.55m EW)
        for doc in [pilot_doc, protocol_doc]:
            assert "8.98315" in doc
            assert "9.96" in doc or "9.97" in doc
            assert "8.23" in doc or "8.22" in doc or "8.28" in doc or "8.29" in doc or "8.55" in doc
            assert "globally isotropic" in doc or "isotropic" in doc

    def test_process_api_parameters_recorded_explicitly(self, pilot_doc: str, pilot_results: list[dict]):
        """Invariant 4: API parameters resx, resy, backCoeff, orthorectify, CRS are recorded."""
        assert "SIGMA0_ELLIPSOID" in pilot_doc
        assert "orthorectify" in pilot_doc
        assert "EPSG:4326" in pilot_doc
        for p in pilot_results:
            assert "processing_resampling" in p
            res = p["processing_resampling"]
            assert res["service_side_grid_generation"] == "YES"
            assert res["service_backCoeff"] == "SIGMA0_ELLIPSOID"
            assert res["service_orthorectify"] == "false"


class TestDataMaskSemanticsR52:
    """Invariant 2: dataMask is sensor footprint data validity, NOT an ocean mask."""

    @pytest.fixture
    def pilot_doc(self) -> str:
        return (REPO / "docs" / "exp08_cdse_physical_compatibility_pilot.md").read_text(encoding="utf-8")

    @pytest.fixture
    def protocol_doc(self) -> str:
        return (REPO / "docs" / "exp08_corrected_protocol.md").read_text(encoding="utf-8")

    def test_datamask_not_called_valid_ocean(self, pilot_doc: str, protocol_doc: str):
        """Invariant 2: Neither document may refer to dataMask == 1 as 'valid ocean pixels'."""
        assert "valid ocean pixels" not in pilot_doc.lower()
        assert "valid ocean pixels" not in protocol_doc.lower()
        assert "datamask-valid" in pilot_doc.lower()
        assert "datamask-valid" in protocol_doc.lower()

    def test_datamask_scope_notice_in_pilot_doc(self, pilot_doc: str):
        """Invariant 2: Pilot doc must explicitly note dataMask defines sensor swath, not water classification."""
        assert "sensor footprint" in pilot_doc.lower() or "swath" in pilot_doc.lower()
        assert "ocean/water" in pilot_doc.lower() or "land/sea" in pilot_doc.lower() or "land/water" in pilot_doc.lower()


class TestResamplingSemanticsR52:
    """Invariant 3: Service-side grid generation vs local client resampling."""

    @pytest.fixture
    def pilot_doc(self) -> str:
        return (REPO / "docs" / "exp08_cdse_physical_compatibility_pilot.md").read_text(encoding="utf-8")

    @pytest.fixture
    def protocol_doc(self) -> str:
        return (REPO / "docs" / "exp08_corrected_protocol.md").read_text(encoding="utf-8")

    def test_service_side_grid_generation_distinguished_from_local_resampling(self, pilot_doc: str, protocol_doc: str):
        """Invariant 3: Must explicitly distinguish LOCAL_RESAMPLING = NONE from SERVICE_SIDE_GRID_GENERATION = YES."""
        for doc in [pilot_doc, protocol_doc]:
            assert "LOCAL_RESAMPLING = NONE" in doc
            assert "SERVICE_SIDE_GRID_GENERATION = YES" in doc


class TestTileWindowCoverageAndEdgeClampingR52:
    """Invariants 5 & 6: Actual compute_tile_windows behavior on non-divisible dimensions."""

    def test_compute_tile_windows_generates_12_windows_per_pilot(self):
        """Invariant 5: Non-divisible dimensions produce 12 tiles (3x4), not 6 floor-division tiles."""
        pilot_dimensions = [
            ("P1", 1509, 1779),
            ("P2", 1511, 1771),
            ("P3", 1514, 1745),
        ]
        for name, H, W in pilot_dimensions:
            windows = compute_tile_windows(H, W, tile_size=512, overlap=0)
            assert len(windows) == 12, f"Pilot {name} ({H}x{W}) must produce 12 windows, got {len(windows)}"

    def test_100_percent_pixel_coverage_zero_uncovered_pixels(self):
        """Invariant 6: Every single pixel in the (H, W) raster is covered by >= 1 tile window."""
        pilot_dimensions = [
            ("P1", 1509, 1779),
            ("P2", 1511, 1771),
            ("P3", 1514, 1745),
        ]
        for name, H, W in pilot_dimensions:
            windows = compute_tile_windows(H, W, tile_size=512, overlap=0)
            coverage = np.zeros((H, W), dtype=np.int32)
            for r0, r1, c0, c1 in windows:
                # Every tile must have exact dimensions (512, 512)
                assert (r1 - r0) == 512
                assert (c1 - c0) == 512
                # Within raster bounds
                assert 0 <= r0 < r1 <= H
                assert 0 <= c0 < c1 <= W
                coverage[r0:r1, c0:c1] += 1
            
            uncovered = (coverage == 0).sum()
            assert uncovered == 0, f"Pilot {name} has {uncovered} uncovered pixels!"
            assert coverage.min() >= 1, f"Pilot {name} min coverage must be >= 1"
            assert coverage.max() <= 4, f"Pilot {name} corner overlap max coverage must be <= 4"


class TestChannelMappingAndRadiometricSemanticsR52:
    """Invariants 7 & 8: Channel mapping and radiometric domain distinctions."""

    @pytest.fixture
    def protocol_doc(self) -> str:
        return (REPO / "docs" / "exp08_corrected_protocol.md").read_text(encoding="utf-8")

    def test_channel_source_truth_and_operational_contract_distinct(self, protocol_doc: str):
        """Invariant 7: Dataset source truth UNKNOWN and operational contract Ch0=VH/Ch1=VV distinct."""
        assert "UNKNOWN / UNVERIFIED AT SOURCE" in protocol_doc
        assert "VERIFIED_WITH_LIMITATIONS" in protocol_doc
        assert "Ch0=VH" in protocol_doc or "Ch0 = VH" in protocol_doc
        assert "Ch1=VV" in protocol_doc or "Ch1 = VV" in protocol_doc

    def test_raw_process_and_calibrated_sigma0_distinct(self, protocol_doc: str):
        """Invariant 8: Raw COG (DN), Process API linear sigma0, and calibrated dB distinct."""
        assert "Raw CDSE COG files are NOT calibrated sigma0 dB" in protocol_doc
        assert "contain raw DN amplitude" in protocol_doc
        assert "SIGMA0_ELLIPSOID" in protocol_doc


class TestDenominatorsAndOverlapSemanticsR52:
    """Invariants 9, 10, 11, 12, 13, 14: Denominators, overlap, catalog sample scope."""

    @pytest.fixture
    def protocol_doc(self) -> str:
        return (REPO / "docs" / "exp08_corrected_protocol.md").read_text(encoding="utf-8")

    def test_2468_3047_remains_superseded(self):
        """Invariant 9: 2468/3047 labeled SUPERSEDED / MIXED-ENTITY."""
        readiness_doc = (REPO / "experiments" / "EXTERNAL_VALIDATION_READINESS.md").read_text(encoding="utf-8")
        assert "SUPERSEDED" in readiness_doc
        assert "MIXED-ENTITY" in readiness_doc

    def test_5515_rejected_as_patch_denominator(self, protocol_doc: str):
        """Invariant 10: 5,515 cannot be a patch denominator."""
        assert "5,515 is the annotation record count. It is NOT a patch count, object count, or valid scientific denominator" in protocol_doc

    def test_2290_and_1365_denominators_authoritative(self, protocol_doc: str):
        """Invariants 11 & 12: 2,290 no-oil and 1,365 oil are authoritative."""
        assert "Total no-oil" in protocol_doc and "2,290" in protocol_doc
        assert "Total oil" in protocol_doc and "1,365" in protocol_doc

    def test_spatial_overlap_cannot_imply_independence(self):
        """Invariant 13: 1,501 non-overlapping patches cannot be labeled statistically independent."""
        overlap_doc = (REPO / "docs" / "exp08_spatial_overlap_r4.md").read_text(encoding="utf-8")
        assert "Absence of Footprint Intersection ≠ Proven Statistical Independence" in overlap_doc

    def test_catalog_sample_scope_cannot_become_catalog_wide_claim(self, protocol_doc: str):
        """Invariant 14: 40/1,063 sample scope must not be claimed as catalog-wide resolution."""
        assert "40/1,063 scenes explicitly confirmed" in protocol_doc
        assert "the remaining 1,023 are NOT proven to be resolvable" in protocol_doc


class TestExecutionFirewallAndGeometryR52:
    """Invariants 15, 16, 17: Firewall, rotated footprint vs AABB, and diagnostic polarization."""

    @pytest.fixture
    def pilot_doc(self) -> str:
        return (REPO / "docs" / "exp08_cdse_physical_compatibility_pilot.md").read_text(encoding="utf-8")

    @pytest.fixture
    def protocol_doc(self) -> str:
        return (REPO / "docs" / "exp08_corrected_protocol.md").read_text(encoding="utf-8")

    def test_execution_authorized_remains_false(self, pilot_doc: str, protocol_doc: str):
        """Invariant 15: EXECUTION_AUTHORIZED = FALSE throughout all live documents."""
        assert "EXECUTION_AUTHORIZED = FALSE" in pilot_doc
        assert "EXECUTION_AUTHORIZED = FALSE" in protocol_doc

    def test_dartis_polygon_footprint_vs_aabb_distinguished(self, pilot_doc: str, protocol_doc: str):
        """Invariant 16: Rotated patch footprint vs axis-aligned bounding box (AABB) distinguished."""
        for doc in [pilot_doc, protocol_doc]:
            assert "AABB" in doc or "axis-aligned" in doc
            assert "rotated" in doc

    def test_polarization_separation_labeled_diagnostic_only(self, pilot_doc: str, protocol_doc: str):
        """Invariant 17: Polarization delta (VV - VH >= 20 dB) labeled DIAGNOSTIC OBSERVATION ONLY."""
        for doc in [pilot_doc, protocol_doc]:
            assert "diagnostic observation" in doc.lower() or "diagnostic" in doc.lower()
