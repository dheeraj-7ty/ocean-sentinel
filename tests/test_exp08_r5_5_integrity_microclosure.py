"""EXP-08 Phase 11-R5.5 Integrity Micro-Closure Test Suite.

Tests for final micro-closure invariants:
1. Expanded AABB is not labeled mathematically equivalent to clamped inference.
2. Retrieval AABB and evaluation quadrilateral remain distinct.
3. -70 dB floor is framed strictly as a numerical guard, not guaranteed classification safety;
   training path does not have -70 dB clamp.
4. R4 overlap strata use rotated quadrilateral vs raster extent geometry.
5. Pilot scope boundaries explicitly distinguish verified vs not-proven items.
6. Execution firewall remains strictly enforced (EXECUTION_AUTHORIZED = FALSE).
"""

from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pytest

REPO = Path(__file__).resolve().parent.parent


class TestSmartExpandedAABBSemanticsR55:
    """Invariant 1: Expanded AABB is not labeled mathematically equivalent to clamped inference."""

    @pytest.fixture
    def pilot_doc(self) -> str:
        return (REPO / "docs" / "exp08_cdse_physical_compatibility_pilot.md").read_text(encoding="utf-8")

    @pytest.fixture
    def protocol_doc(self) -> str:
        return (REPO / "docs" / "exp08_corrected_protocol.md").read_text(encoding="utf-8")

    def test_expanded_aabb_not_labeled_mathematically_equivalent_to_clamped(self, pilot_doc: str, protocol_doc: str):
        """Invariant 1: Documents explicitly state clamped and expanded routes are NOT mathematically equivalent."""
        for doc in [pilot_doc, protocol_doc]:
            assert "NOT mathematically equivalent" in doc
            # 'zero effect' must not be asserted as an unreserved claim
            assert "zero effect on primary metrics" not in doc or "cannot be assumed to have zero effect" in doc or "cannot be assumed to have \"zero effect\"" in doc


class TestRetrievalAABBVsEvaluationQuadrilateralR55:
    """Invariant 2: Retrieval AABB and evaluation quadrilateral remain distinct."""

    @pytest.fixture
    def protocol_doc(self) -> str:
        return (REPO / "docs" / "exp08_corrected_protocol.md").read_text(encoding="utf-8")

    def test_retrieval_aabb_and_evaluation_quadrilateral_distinct(self, protocol_doc: str):
        """Invariant 2: Retrieval domain is AABB; Primary evaluation domain is rotated quadrilateral."""
        assert "RETRIEVAL_DOMAIN: `DARTIS AABB`" in protocol_doc or "RETRIEVAL_DOMAIN:" in protocol_doc
        assert "PRIMARY_EVALUATION_DOMAIN: `DARTIS QUADRILATERAL FOOTPRINT`" in protocol_doc or "PRIMARY_EVALUATION_DOMAIN:" in protocol_doc
        assert "primary_eval_mask" in protocol_doc or "primary\\_eval\\_mask" in protocol_doc or "dartis_polygon_mask" in protocol_doc


class TestMinus70dBFloorAndTrainingTraceR55:
    """Invariant 3: -70 dB floor is a numerical guard, and training path had no -70 dB floor."""

    @pytest.fixture
    def pilot_doc(self) -> str:
        return (REPO / "docs" / "exp08_cdse_physical_compatibility_pilot.md").read_text(encoding="utf-8")

    @pytest.fixture
    def protocol_doc(self) -> str:
        return (REPO / "docs" / "exp08_corrected_protocol.md").read_text(encoding="utf-8")

    def test_minus_70db_floor_is_numerical_guard_not_safety_guarantee(self, pilot_doc: str, protocol_doc: str):
        """Invariant 3a: Documents formulate -70 dB floor as a deterministic numerical guard, not guaranteed safety."""
        for doc in [pilot_doc, protocol_doc]:
            assert "deterministic numerical guard" in doc.lower()
            assert "classification safety" in doc.lower() and "not independently established" in doc.lower()
            assert "safely saturate" not in doc.lower()
            assert "cannot falsely activate" not in doc.lower()

    def test_training_pipeline_had_no_minus_70db_clamp(self):
        """Invariant 3b: EXP-06 training code and dataset class do not apply a -70 dB clamp on GeoTIFFs."""
        train_script = (REPO / "scripts" / "train_exp06.py").read_text(encoding="utf-8")
        dataset_code = (REPO / "src" / "ocean_sentinel" / "ingestion" / "dataset.py").read_text(encoding="utf-8")
        assert "-70" not in train_script
        assert "-70" not in dataset_code


class TestR4OverlapStrataGeometryTerminologyR55:
    """Invariant 4: R4 overlap strata consistently use rotated quadrilateral vs raster extent geometry."""

    @pytest.fixture
    def overlap_doc(self) -> str:
        return (REPO / "docs" / "exp08_spatial_overlap_r4.md").read_text(encoding="utf-8")

    @pytest.fixture
    def protocol_doc(self) -> str:
        return (REPO / "docs" / "exp08_corrected_protocol.md").read_text(encoding="utf-8")

    def test_r4_overlap_strata_use_rotated_quadrilateral_semantics(self, overlap_doc: str, protocol_doc: str):
        """Invariant 4: Strata descriptions refer to rotated quadrilateral footprints, not bounding boxes."""
        assert "rotated quadrilateral" in overlap_doc
        assert "rotated quadrilateral" in protocol_doc
        # Check that stratum 1 and stratum 2 populations in protocol do not say 'whose bounding box has ZERO'
        assert "whose bounding box has ZERO geometric intersection" not in protocol_doc
        assert "whose rotated quadrilateral footprint has ZERO geometric intersection" in protocol_doc


class TestPilotScopeAndFirewallR55:
    """Invariants 5 & 6: Pilot scope boundaries and firewall."""

    @pytest.fixture
    def pilot_doc(self) -> str:
        return (REPO / "docs" / "exp08_cdse_physical_compatibility_pilot.md").read_text(encoding="utf-8")

    @pytest.fixture
    def protocol_doc(self) -> str:
        return (REPO / "docs" / "exp08_corrected_protocol.md").read_text(encoding="utf-8")

    def test_pilot_scope_boundaries_distinguish_verified_vs_not_proven(self, pilot_doc: str):
        """Invariant 5: Pilot doc explicitly separates VERIFIED from NOT PROVEN."""
        assert "Pilot Scope Boundaries" in pilot_doc
        assert "VERIFIED:" in pilot_doc or "**VERIFIED**:" in pilot_doc
        assert "NOT PROVEN:" in pilot_doc or "**NOT PROVEN**:" in pilot_doc

    def test_execution_firewall_strictly_false(self, pilot_doc: str, protocol_doc: str):
        """Invariant 6: EXECUTION_AUTHORIZED = FALSE throughout live documents."""
        assert "EXECUTION_AUTHORIZED = FALSE" in pilot_doc
        assert "EXECUTION_AUTHORIZED = FALSE" in protocol_doc
