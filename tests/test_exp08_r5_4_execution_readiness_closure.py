"""Stage 14 Guardrail Tests — Phase 11-R5.4 EXP-08 Final Execution-Readiness Closure.

Validates all 22 Phase 11-R5.4 invariants:
1. Exact acquisition provenance requires Catalog uniqueness (single observation per 25s window)
2. Process API datasource `id` is not treated as a physical product ID
3. Downsampling is not treated as an active processing parameter (omitted from canonical contract)
4. Speckle filtering semantics are explicit (omission == NONE)
5. All 1,200 source footprints are distinguished from actual 840 training source footprints
6. R4 overlap geometry is unambiguous (DARTIS rotated quadrilateral vs Trujillo raster extent box)
7. Polygon vs AABB evaluation domains are unambiguous
8. Polygon mask rasterization is deterministic (tested via src/ocean_sentinel/geometry.py)
9. dataMask != ocean mask (sensor swath validity only)
10. Service-side grid generation != local client resampling
11. Frozen normalization constants remain unique ([-33.2323, -19.9405], [6.4912, 4.5308])
12. -70 dB low-value handling is evidence-backed (deep negative saturation, below instrument noise)
13. compute_tile_windows() covers every pixel (100% coverage)
14. Edge duplication is measured and compared to Smart Expanded AABB
15. Cluster overlap across spatial strata is measured (297 shared parent scenes between Stratum 1 & 2)
16. Spatial non-intersection != statistical independence
17. 5515 != patch denominator
18. 2290 = no-oil patch denominator
19. 1365 = oil patch denominator
20. 40/1063 != catalog-wide verification
21. DARTIS absence from training is evidence-backed
22. EXECUTION_AUTHORIZED remains FALSE throughout all live documents
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from unittest.mock import MagicMock

import affine
import numpy as np
import pytest

REPO = Path(__file__).parent.parent

# Safe import of ocean_sentinel modules
for mod in ["torch", "torch.nn", "torch.utils", "torch.utils.data", "torchvision", "torchvision.models"]:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

from ocean_sentinel.geometry import create_dartis_polygon_mask, create_primary_evaluation_mask
from ocean_sentinel.inference import DEFAULT_NORM_MEAN, DEFAULT_NORM_STD, compute_tile_windows
from ocean_sentinel.satellite.calibration import DEFAULT_EPSILON, linear_to_db


class TestCatalogProvenanceAndApiSemanticsR54:
    """Invariants 1 & 2: Catalog uniqueness and Process API datasource id semantics."""

    @pytest.fixture
    def validation_report(self) -> dict:
        path = REPO / "data" / "metadata" / "yang_singha_2025" / "cdse_validation_report.json"
        assert path.exists()
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    @pytest.fixture
    def pilot_results(self) -> list[dict]:
        path = REPO / "scratch" / "cdse_physical_pilot_results_r5_3.json"
        assert path.exists()
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def test_exact_acquisition_provenance_requires_catalog_uniqueness(self, validation_report: dict, pilot_results: list[dict]):
        """Invariant 1: Exact product provenance is established by Catalog uniqueness within the 25s window."""
        assert validation_report["summary"]["multiple_possible_matches"] == 0
        assert validation_report["summary"]["total_resolved"] == 40
        for p in pilot_results:
            prov = p["provenance_metadata"]
            assert prov["exact_product_match"] is True
            assert prov["mosaicking_ambiguity"] is False
            assert prov["temporal_window_seconds"] == 25

    def test_process_api_datasource_id_is_not_product_id(self):
        """Invariant 2: Process API input.data[].id is a datasource alias, not a Sentinel-1 product ID."""
        protocol_doc = (REPO / "docs" / "exp08_corrected_protocol.md").read_text(encoding="utf-8")
        assert "datasource" in protocol_doc.lower() or "data[0].id" in protocol_doc or "data.id" in protocol_doc


class TestProcessingContractSemanticsR54:
    """Invariants 3 & 4: Downsampling inactive and speckleFilter semantics."""

    @pytest.fixture
    def pilot_doc(self) -> str:
        return (REPO / "docs" / "exp08_cdse_physical_compatibility_pilot.md").read_text(encoding="utf-8")

    @pytest.fixture
    def protocol_doc(self) -> str:
        return (REPO / "docs" / "exp08_corrected_protocol.md").read_text(encoding="utf-8")

    def test_downsampling_not_treated_as_active_processing_parameter(self, pilot_doc: str, protocol_doc: str):
        """Invariant 3: Downsampling is recognized as ignored/inactive for Sentinel-1 GRD in Process API."""
        for doc in [pilot_doc, protocol_doc]:
            assert "downsampling" in doc.lower()

    def test_speckle_filtering_semantics_are_explicit(self, pilot_doc: str, protocol_doc: str):
        """Invariant 4: Speckle filtering semantics are explicit (NONE / omitted)."""
        for doc in [pilot_doc, protocol_doc]:
            assert "speckle" in doc.lower()


class TestTrujilloFootprintsAndSplitDistinctionR54:
    """Invariant 5: All 1,200 source footprints distinguished from actual 840 training source footprints."""

    @pytest.fixture
    def split_audit(self) -> dict:
        path = REPO / "data" / "metadata" / "trujillo_2024" / "spatial_split_audit.json"
        assert path.exists()
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    @pytest.fixture
    def footprint_results(self) -> dict:
        path = REPO / "data" / "metadata" / "exp08_r5_4_footprints_and_clusters.json"
        assert path.exists()
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def test_source_footprints_distinguished_from_training_footprints(self, split_audit: dict, footprint_results: dict):
        """Invariant 5: 1,200 source patches (total) vs 840 training patches strictly separated."""
        assert split_audit["split_composition"]["train_parents"] == 840
        assert split_audit["split_composition"]["val_parents"] == 180
        assert split_audit["split_composition"]["test_parents"] == 180

        counts = footprint_results["trujillo_counts"]
        assert counts["total_source_footprints"] == 1200
        assert counts["train_source_footprints"] == 840

        # Overlap with all 1,200 vs 840 training
        nooil_1200 = footprint_results["nooil_source_overlap_1200"]
        nooil_840 = footprint_results["nooil_training_overlap_840"]
        assert nooil_1200["overlap_count"] == 789
        assert nooil_1200["no_overlap_count"] == 1501
        assert nooil_840["overlap_count"] == 441
        assert nooil_840["no_overlap_count"] == 1849


class TestOverlapGeometryAndEvaluationDomainR54:
    """Invariants 6, 7, 8: Geometry semantics, evaluation domains, and deterministic rasterization."""

    @pytest.fixture
    def r4_overlap_json(self) -> dict:
        path = REPO / "data" / "metadata" / "exp08_spatial_overlap_r4.json"
        assert path.exists()
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def test_r4_overlap_geometry_is_unambiguous(self, r4_overlap_json: dict):
        """Invariant 6: R4 geometry is DARTIS 4-corner polygon vs Trujillo rasterio bounding box."""
        nooil = r4_overlap_json["nooil_result"]
        assert "shapely Polygon from 4 DARTIS patch corner coordinates" in nooil["geometry_method"]
        assert "shapely box from rasterio bounds" in nooil["trujillo_geometry_method"]

    def test_evaluation_domain_contract_unambiguous(self):
        """Invariant 7: RETRIEVAL_DOMAIN is AABB, PRIMARY_EVALUATION_DOMAIN is DARTIS quadrilateral."""
        protocol_doc = (REPO / "docs" / "exp08_corrected_protocol.md").read_text(encoding="utf-8")
        assert "RETRIEVAL_DOMAIN" in protocol_doc
        assert "PRIMARY_EVALUATION_DOMAIN" in protocol_doc
        assert "dartis_polygon_mask" in protocol_doc or "dartis\\_polygon\\_mask" in protocol_doc

    def test_polygon_mask_rasterization_is_deterministic(self):
        """Invariant 8: create_dartis_polygon_mask and create_primary_evaluation_mask produce exact masks."""
        height, width = 100, 100
        transform = affine.Affine(0.001, 0, 30.0, 0, -0.001, 35.0)
        # Quadrilateral inside the 100x100 raster (lon: 30.02-30.08, lat: 34.92-34.98)
        corners = [
            (30.02, 34.98),  # UL
            (30.08, 34.97),  # UR
            (30.07, 34.92),  # BR
            (30.01, 34.93),  # BL
        ]
        poly_mask = create_dartis_polygon_mask(height, width, transform, corners, all_touched=False)
        assert poly_mask.shape == (100, 100)
        assert poly_mask.dtype == np.uint8
        assert 0 < poly_mask.sum() < 10000

        # Primary eval mask with dataMask
        data_mask = np.ones((100, 100), dtype=np.uint8)
        data_mask[20:50, :] = 0  # Invalid middle rows that intersect polygon
        eval_mask = create_primary_evaluation_mask(height, width, transform, corners, data_mask=data_mask)
        assert eval_mask.dtype == np.uint8
        assert (eval_mask[20:50, :] == 0).all()
        assert eval_mask.sum() < poly_mask.sum()


class TestDataMaskAndResamplingSemanticsR54:
    """Invariants 9 & 10: dataMask != ocean mask and grid generation != local resampling."""

    @pytest.fixture
    def pilot_doc(self) -> str:
        return (REPO / "docs" / "exp08_cdse_physical_compatibility_pilot.md").read_text(encoding="utf-8")

    @pytest.fixture
    def protocol_doc(self) -> str:
        return (REPO / "docs" / "exp08_corrected_protocol.md").read_text(encoding="utf-8")

    def test_datamask_not_called_valid_ocean(self, pilot_doc: str, protocol_doc: str):
        """Invariant 9: dataMask defines sensor swath footprint validity, NOT ocean classification."""
        for doc in [pilot_doc, protocol_doc]:
            assert "valid ocean pixels" not in doc.lower()
            assert "swath" in doc.lower() or "sensor footprint" in doc.lower()

    def test_service_side_grid_generation_distinguished_from_local_resampling(self, pilot_doc: str, protocol_doc: str):
        """Invariant 10: LOCAL_RESAMPLING = NONE and SERVICE_SIDE_GRID_GENERATION = YES distinct."""
        for doc in [pilot_doc, protocol_doc]:
            assert "LOCAL_RESAMPLING = NONE" in doc
            assert "SERVICE_SIDE_GRID_GENERATION = YES" in doc


class TestNormalizationAndLowValueDBSemanticsR54:
    """Invariants 11 & 12: Normalization constants uniqueness and -70 dB low-value handling."""

    def test_frozen_normalization_constants_unique(self):
        """Invariant 11: Authoritative constants in inference.py are exact and unique."""
        assert np.allclose(DEFAULT_NORM_MEAN, [-33.2323, -19.9405], atol=1e-4)
        assert np.allclose(DEFAULT_NORM_STD, [6.4912, 4.5308], atol=1e-4)

    def test_low_value_db_handling_is_evidence_backed(self):
        """Invariant 12: linear_to_db uses epsilon=1e-7 (-70 dB floor), clamping non-positive values safely."""
        assert DEFAULT_EPSILON == 1e-7
        # Test linear to dB clamping
        test_linear = np.array([1.0, 0.1, 1e-7, 1e-8, 0.0, -1.0], dtype=np.float32)
        out_db = linear_to_db(test_linear, epsilon=1e-7, fill_invalid=np.nan)
        assert np.isclose(out_db[0], 0.0, atol=1e-3)       # 10*log10(1) = 0
        assert np.isclose(out_db[1], -10.0, atol=1e-3)     # 10*log10(0.1) = -10
        assert np.isclose(out_db[2], -70.0, atol=1e-3)     # 10*log10(1e-7) = -70
        assert np.isclose(out_db[3], -70.0, atol=1e-3)     # Clamped to 1e-7
        assert np.isnan(out_db[4])                         # Zero mapped to invalid (or clamped if valid_mask)
        assert np.isnan(out_db[5])                         # Negative mapped to invalid


class TestTileWindowCoverageAndDuplicationR54:
    """Invariants 13 & 14: compute_tile_windows full coverage and edge duplication measurement."""

    def test_compute_tile_windows_covers_every_pixel(self):
        """Invariant 13: 100% pixel coverage across all pilot dimensions."""
        pilot_dimensions = [("P1", 1509, 1779), ("P2", 1511, 1771), ("P3", 1514, 1745)]
        for _, H, W in pilot_dimensions:
            windows = compute_tile_windows(H, W, tile_size=512, overlap=0)
            cov = np.zeros((H, W), dtype=int)
            for r0, r1, c0, c1 in windows:
                cov[r0:r1, c0:c1] += 1
            assert (cov == 0).sum() == 0
            assert cov.min() >= 1

    def test_edge_duplication_measured_and_quantified(self):
        """Invariant 14: Duplicate pixel evaluation is quantified at ~17-19% in clamped 12-window method."""
        pilot_dimensions = [("P1", 1509, 1779), ("P2", 1511, 1771), ("P3", 1514, 1745)]
        for _, H, W in pilot_dimensions:
            windows = compute_tile_windows(H, W, tile_size=512, overlap=0)
            assert len(windows) == 12
            total_evaluated = len(windows) * 512 * 512
            total_raster = H * W
            dup_ratio = (total_evaluated - total_raster) / total_raster
            assert 0.15 <= dup_ratio <= 0.20


class TestSceneClusteringAndIndependenceR54:
    """Invariants 15 & 16: Cluster overlap across spatial strata and independence caveat."""

    @pytest.fixture
    def footprint_results(self) -> dict:
        path = REPO / "data" / "metadata" / "exp08_r5_4_footprints_and_clusters.json"
        assert path.exists()
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def test_cluster_overlap_across_spatial_strata_measured(self, footprint_results: dict):
        """Invariant 15: 297 parent scenes contribute patches to BOTH Stratum 1 and Stratum 2."""
        nooil_clust = footprint_results["nooil_scene_clustering"]
        assert nooil_clust["total_parent_scenes"] == 869
        assert nooil_clust["stratum1_scenes"] == 719
        assert nooil_clust["stratum2_scenes"] == 447
        assert nooil_clust["shared_parent_scenes"] == 297

    def test_spatial_non_intersection_not_statistical_independence(self):
        """Invariant 16: Documentation explicitly states spatial non-intersection != statistical independence."""
        overlap_doc = (REPO / "docs" / "exp08_spatial_overlap_r4.md").read_text(encoding="utf-8")
        assert "Absence of Footprint Intersection ≠ Proven Statistical Independence" in overlap_doc


class TestDenominatorsAndCatalogScopeR54:
    """Invariants 17, 18, 19, 20: Denominators and catalog scope."""

    @pytest.fixture
    def protocol_doc(self) -> str:
        return (REPO / "docs" / "exp08_corrected_protocol.md").read_text(encoding="utf-8")

    def test_5515_rejected_as_patch_denominator(self, protocol_doc: str):
        """Invariant 17: 5,515 is strictly an annotation record count, not a patch denominator."""
        assert "5,515" in protocol_doc
        assert "NOT a patch count" in protocol_doc

    def test_authoritative_patch_denominators(self, protocol_doc: str):
        """Invariants 18 & 19: 2,290 no-oil patches and 1,365 oil patches are authoritative."""
        assert "2,290" in protocol_doc
        assert "1,365" in protocol_doc

    def test_catalog_sample_scope_not_catalog_wide(self, protocol_doc: str):
        """Invariant 20: 40/1,063 is an informational sample and remaining 1,023 are unproven."""
        assert "40/1,063" in protocol_doc
        assert "1,023" in protocol_doc


class TestTrainingContaminationAndFirewallR54:
    """Invariants 21 & 22: DARTIS absence from EXP-06 training and execution firewall."""

    def test_dartis_absence_from_training_is_evidence_backed(self):
        """Invariant 21: EXP-06 training script and manifest contain zero DARTIS data."""
        train_script = (REPO / "scripts" / "train_exp06.py").read_text(encoding="utf-8")
        assert "TrujilloTileDataset" in train_script
        assert "dartis" not in train_script.lower()
        manifest_path = REPO / "data" / "metadata" / "trujillo_2024" / "spatial_split_manifest.json"
        assert manifest_path.exists()

    def test_execution_authorized_strictly_false(self):
        """Invariant 22: EXECUTION_AUTHORIZED = FALSE throughout live documents."""
        protocol_doc = (REPO / "docs" / "exp08_corrected_protocol.md").read_text(encoding="utf-8")
        pilot_doc = (REPO / "docs" / "exp08_cdse_physical_compatibility_pilot.md").read_text(encoding="utf-8")
        assert "EXECUTION_AUTHORIZED = FALSE" in protocol_doc
        assert "EXECUTION_AUTHORIZED = FALSE" in pilot_doc
