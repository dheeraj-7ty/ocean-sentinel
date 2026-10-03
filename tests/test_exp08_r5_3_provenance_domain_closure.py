"""Stage 15 Guardrail Tests — Phase 11-R5.3 EXP-08 Final Provenance + Evaluation-Domain Closure.

Validates all 15 Phase 11-R5.3 invariants:
1. Normalization mean/std source-of-truth in src/ocean_sentinel/inference.py
2. No conflicting frozen normalization constants in live documents
3. Exact acquisition identity requirement and zero mosaicking ambiguity
4. Broad timeRange cannot establish exact product provenance (25s window uniqueness)
5. Process API upsampling is explicit (NEAREST) and scientifically justified
6. dataMask != ocean mask (sensor swath footprint validity only)
7. AABB != DARTIS polygon (quadrilateral inclination and area excess)
8. Primary evaluation domain explicitly defined (AABB retrieval vs polygon evaluation mask)
9. Spatial non-intersection != statistical independence
10. 5515 != patch denominator
11. 2290 = no-oil patch denominator
12. 1365 = oil patch denominator
13. Catalog 40/1063 != catalog-wide resolution
14. CDSE radiometric domain != proven Trujillo numerical equivalence
15. EXECUTION_AUTHORIZED remains FALSE throughout all live documents
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys
from unittest.mock import MagicMock

import numpy as np
import pytest

REPO = Path(__file__).parent.parent

# Safe import of ocean_sentinel.inference without requiring torch binary install
for mod in ["torch", "torch.nn", "torch.utils", "torch.utils.data", "torchvision", "torchvision.models"]:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

from ocean_sentinel.inference import DEFAULT_NORM_MEAN, DEFAULT_NORM_STD


class TestNormalizationContractSourceOfTruthR53:
    """Invariants 1 & 2: Normalization mean/std source of truth and guard against conflicting constants."""

    @pytest.fixture
    def protocol_doc(self) -> str:
        return (REPO / "docs" / "exp08_corrected_protocol.md").read_text(encoding="utf-8")

    @pytest.fixture
    def pilot_doc(self) -> str:
        return (REPO / "docs" / "exp08_cdse_physical_compatibility_pilot.md").read_text(encoding="utf-8")

    def test_authoritative_normalization_constants_in_code(self):
        """Invariant 1: Authoritative constants in src/ocean_sentinel/inference.py must match exact frozen values."""
        assert np.allclose(DEFAULT_NORM_MEAN, [-33.2323, -19.9405], atol=1e-4)
        assert np.allclose(DEFAULT_NORM_STD, [6.4912, 4.5308], atol=1e-4)

    def test_no_conflicting_frozen_normalization_constants_in_live_documents(self, protocol_doc: str, pilot_doc: str):
        """Invariant 2: No alternative normalization means (e.g. [-19.86, -11.96]) appear as frozen constants."""
        for doc_name, text in [("Protocol", protocol_doc), ("Pilot", pilot_doc)]:
            assert "33.2323" in text, f"{doc_name} must contain exact VH mean 33.2323"
            assert "19.9405" in text, f"{doc_name} must contain exact VV mean 19.9405"
            assert "6.4912" in text, f"{doc_name} must contain exact VH std 6.4912"
            assert "4.5308" in text, f"{doc_name} must contain exact VV std 4.5308"
            # Ensure the historical typo values do NOT appear in live docs
            assert "-19.86" not in text, f"{doc_name} contains conflicting/historical mean -19.86"
            assert "-11.96" not in text, f"{doc_name} contains conflicting/historical mean -11.96"


class TestProductProvenanceAndAcquisitionWindowR53:
    """Invariants 3 & 4: Exact acquisition identity requirement and broad timeRange risk."""

    @pytest.fixture
    def validation_report(self) -> dict:
        path = REPO / "data" / "metadata" / "yang_singha_2025" / "cdse_validation_report.json"
        assert path.exists(), "cdse_validation_report.json must exist"
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    @pytest.fixture
    def pilot_results_r5_3(self) -> list[dict]:
        path = REPO / "scratch" / "cdse_physical_pilot_results_r5_3.json"
        assert path.exists(), "cdse_physical_pilot_results_r5_3.json must exist"
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def test_exact_acquisition_identity_requirement(self, validation_report: dict, pilot_results_r5_3: list[dict]):
        """Invariant 3: Each pilot must match the exact Sentinel-1 product ID with zero ambiguity."""
        assert len(pilot_results_r5_3) == 3
        for pilot in pilot_results_r5_3:
            prov = pilot["provenance_metadata"]
            assert prov["exact_product_match"] is True
            assert prov["mosaicking_ambiguity"] is False
            assert prov["platform"] == "sentinel-1a"
            assert "VV" in prov["polarization_channels"]
            assert "VH" in prov["polarization_channels"]
            assert prov["canonical_payload_sha256"] is not None
            assert len(prov["canonical_payload_sha256"]) == 64
            # Verify prefix correspondence
            safe_prefix = prov["dartis_safe_id"][:60]
            cdse_prefix = prov["cdse_cog_id"][:60]
            assert safe_prefix == cdse_prefix, f"Prefix mismatch: {safe_prefix} vs {cdse_prefix}"

    def test_broad_timerange_risk_and_narrow_window_defense(self, validation_report: dict, pilot_results_r5_3: list[dict]):
        """Invariant 4: Broad timeRange (multi-hour/day) is insufficient; exact 25s window pins unique product."""
        records = validation_report.get("records", [])
        assert len(records) == 40
        # All records matched with zero multiple matches when using exact product time window
        assert validation_report["summary"]["multiple_possible_matches"] == 0
        for p in pilot_results_r5_3:
            assert p["provenance_metadata"]["temporal_window_seconds"] == 25
            assert p["provenance_metadata"]["mosaicking_ambiguity"] is False


class TestProcessApiParametersAndUpsamplingR53:
    """Invariant 5: Explicit Process API parameters including upsampling = NEAREST."""

    @pytest.fixture
    def pilot_results_r5_3(self) -> list[dict]:
        path = REPO / "scratch" / "cdse_physical_pilot_results_r5_3.json"
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    @pytest.fixture
    def pilot_doc(self) -> str:
        return (REPO / "docs" / "exp08_cdse_physical_compatibility_pilot.md").read_text(encoding="utf-8")

    @pytest.fixture
    def protocol_doc(self) -> str:
        return (REPO / "docs" / "exp08_corrected_protocol.md").read_text(encoding="utf-8")

    def test_upsampling_nearest_explicit_in_configuration(self, pilot_results_r5_3: list[dict]):
        """Invariant 5: upsampling and downsampling must be explicitly pinned to NEAREST."""
        for p in pilot_results_r5_3:
            res = p["processing_resampling"]
            assert res["upsampling"] == "NEAREST"
            assert res["downsampling"] == "NEAREST"
            assert res["speckleFilter"] == "NONE"
            assert res["service_backCoeff"] == "SIGMA0_ELLIPSOID"
            assert res["service_orthorectify"] == "false"

    def test_upsampling_nearest_justification_in_docs(self, pilot_doc: str, protocol_doc: str):
        """Invariant 5: Documentation must explicitly justify NEAREST upsampling."""
        for doc in [pilot_doc, protocol_doc]:
            assert "NEAREST" in doc
            assert "discrete" in doc.lower() or "boundary" in doc.lower() or "intermediate" in doc.lower()


class TestDataMaskSemanticsR53:
    """Invariant 6: dataMask != ocean mask (sensor footprint validity only)."""

    @pytest.fixture
    def pilot_doc(self) -> str:
        return (REPO / "docs" / "exp08_cdse_physical_compatibility_pilot.md").read_text(encoding="utf-8")

    @pytest.fixture
    def protocol_doc(self) -> str:
        return (REPO / "docs" / "exp08_corrected_protocol.md").read_text(encoding="utf-8")

    def test_datamask_not_an_ocean_mask(self, pilot_doc: str, protocol_doc: str):
        """Invariant 6: dataMask is data/no-data sensor swath validity, not an ocean or land mask."""
        for doc in [pilot_doc, protocol_doc]:
            assert "valid ocean pixels" not in doc.lower()
            assert "ocean" in doc.lower()
            assert "swath" in doc.lower() or "nodata" in doc.lower() or "sensor footprint" in doc.lower()


class TestEvaluationDomainAndAABBSemanticsR53:
    """Invariants 7 & 8: Rotated quadrilateral vs AABB and primary evaluation domain definition."""

    @pytest.fixture
    def pilot_results_r5_3(self) -> list[dict]:
        path = REPO / "scratch" / "cdse_physical_pilot_results_r5_3.json"
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    @pytest.fixture
    def protocol_doc(self) -> str:
        return (REPO / "docs" / "exp08_corrected_protocol.md").read_text(encoding="utf-8")

    def test_aabb_area_strictly_greater_than_dartis_quadrilateral(self, pilot_results_r5_3: list[dict]):
        """Invariant 7: Rotated quadrilateral footprint area is ~26% smaller than enclosing AABB."""
        for p in pilot_results_r5_3:
            geom = p["footprint_geometry"]
            assert geom["coverage_type"] == "AXIS_ALIGNED_BOUNDING_BOX"
            assert geom["encloses_rotated_patch"] is True
            area_ratio = geom["polygon_to_aabb_area_ratio_pct"]
            assert 70.0 <= area_ratio <= 80.0, f"Area ratio {area_ratio} should be ~74%"

    def test_primary_evaluation_domain_strictly_defined_in_protocol(self, protocol_doc: str):
        """Invariant 8: Primary evaluation domain must be restricted to DARTIS quadrilateral footprint."""
        assert "RETRIEVAL_DOMAIN" in protocol_doc or "DARTIS AABB" in protocol_doc
        assert "PRIMARY_EVALUATION_DOMAIN" in protocol_doc or "primary_eval_mask" in protocol_doc
        assert "dartis_polygon_mask" in protocol_doc or "dartis\\_polygon\\_mask" in protocol_doc


class TestSpatialOverlapAndIndependenceR53:
    """Invariant 9: Spatial non-intersection != statistical independence."""

    def test_absence_of_footprint_intersection_not_statistical_independence(self):
        """Invariant 9: Documentation must state zero footprint intersection != statistical independence."""
        overlap_doc = (REPO / "docs" / "exp08_spatial_overlap_r4.md").read_text(encoding="utf-8")
        protocol_doc = (REPO / "docs" / "exp08_corrected_protocol.md").read_text(encoding="utf-8")
        for doc in [overlap_doc, protocol_doc]:
            assert "zero geometric intersection" in doc.lower() or "absence of footprint intersection" in doc.lower()
            assert "statistical independence" in doc.lower()


class TestDenominatorsAndCatalogScopeR53:
    """Invariants 10, 11, 12, 13: Patch denominators and catalog sample scope."""

    @pytest.fixture
    def protocol_doc(self) -> str:
        return (REPO / "docs" / "exp08_corrected_protocol.md").read_text(encoding="utf-8")

    def test_5515_rejected_as_patch_denominator(self, protocol_doc: str):
        """Invariant 10: 5515 is strictly an annotation record count, not a patch denominator."""
        assert "5,515" in protocol_doc
        assert "NOT a patch count" in protocol_doc

    def test_authoritative_patch_denominators(self, protocol_doc: str):
        """Invariants 11 & 12: 2,290 no-oil patches and 1,365 oil patches are authoritative."""
        assert "2,290" in protocol_doc
        assert "1,365" in protocol_doc
        assert "34.5%" in protocol_doc  # 789 / 2290
        assert "65.5%" in protocol_doc  # 1501 / 2290
        assert "52.2%" in protocol_doc  # 712 / 1365
        assert "47.8%" in protocol_doc  # 653 / 1365

    def test_catalog_sample_scope_not_catalog_wide(self, protocol_doc: str):
        """Invariant 13: 40/1,063 is an informational sample and remaining 1,023 are unproven."""
        assert "40/1,063" in protocol_doc
        assert "1,023" in protocol_doc
        assert "NOT proven" in protocol_doc or "not proven" in protocol_doc


class TestRadiometricEquivalenceAndFirewallR53:
    """Invariants 14 & 15: Radiometric domain vs Trujillo equivalence and execution firewall."""

    @pytest.fixture
    def protocol_doc(self) -> str:
        return (REPO / "docs" / "exp08_corrected_protocol.md").read_text(encoding="utf-8")

    @pytest.fixture
    def pilot_doc(self) -> str:
        return (REPO / "docs" / "exp08_cdse_physical_compatibility_pilot.md").read_text(encoding="utf-8")

    def test_radiometric_domain_verified_but_trujillo_equivalence_not_proven(self, protocol_doc: str, pilot_doc: str):
        """Invariant 14: CDSE radiometric domain is verified but Trujillo author equivalence is NOT_PROVEN."""
        # Both documents must reflect that radiometric domain is verified/confirmed
        assert "radiometric" in protocol_doc.lower()
        assert "RADIOMETRIC_DOMAIN_CONFIRMED" in pilot_doc
        # Both documents must reflect that calibration equivalence is NOT_PROVEN
        assert "NOT_PROVEN" in protocol_doc
        assert "CALIBRATION_EQUIVALENCE_NOT_PROVEN" in pilot_doc

    def test_execution_authorized_strictly_false(self, protocol_doc: str, pilot_doc: str):
        """Invariant 15: EXECUTION_AUTHORIZED = FALSE throughout live documents."""
        assert "EXECUTION_AUTHORIZED = FALSE" in protocol_doc
        assert "EXECUTION_AUTHORIZED = FALSE" in pilot_doc
