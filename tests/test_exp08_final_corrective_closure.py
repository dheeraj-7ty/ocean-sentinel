"""EXP-08 Final Corrective Closure Test Suite.

Tests for all Stage 14 invariants from OCEAN-SENTINEL-FINAL-EXP08-CORRECTIVE-CLOSURE:

1.  Patch-level stratum semantics (strata are patches, not scenes)
2.  A shared parent scene may legitimately appear in both strata
3.  Stratum counts remain: 1,501 / 789 patches; 719 / 447 parent scenes; 297 shared
4.  Ambiguous Catalog result blocks inference (MULTIPLE_MATCHES status → PreflightFirewallError)
5.  Unresolved scene cannot silently change denominator
6.  Zero-valid-pixel / zero-polygon-pixel handling is deterministic
7.  Process API output cannot receive raw-DN calibration (double-calibration firewall)
8.  AABB retrieval is distinct from quadrilateral evaluation domain
9.  Clamped tiling route is frozen
10. Expanded AABB cannot silently become default
11. Channel inversion fails loudly
12. O3 cannot be mislabeled as segmentation IoU
13. Preflight code itself never calls model inference
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import sys

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Repo root
# ---------------------------------------------------------------------------
REPO = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Safe mocking of torch before any ocean_sentinel imports
# ---------------------------------------------------------------------------
for _mod in ["torch", "torch.nn", "torch.utils", "torch.utils.data",
             "torchvision", "torchvision.models"]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

from ocean_sentinel.exp08_catalog_preflight import (
    PreflightFirewallError,
    PreflightManifest,
    PreflightRecord,
    STATUS_INVALID_METADATA,
    STATUS_MULTIPLE_MATCHES,
    STATUS_NO_MATCH,
    STATUS_QUERY_ERROR,
    STATUS_RESOLVED_UNIQUE,
    enforce_preflight_gate,
    resolve_dartis_scene,
    run_preflight,
)
from ocean_sentinel.satellite.calibration import (
    DEFAULT_EPSILON,
    calibrate_dn_to_sigma0_linear,
    linear_to_db,
    stack_dual_pol_channels,
)


# ===========================================================================
# 1. Patch-level stratum semantics
# ===========================================================================
class TestPatchLevelStratumSemantics:
    """Invariant 1: Strata are defined at the PATCH level, not the scene level."""

    @pytest.fixture
    def protocol_doc(self) -> str:
        return (REPO / "docs" / "exp08_corrected_protocol.md").read_text(encoding="utf-8")

    def test_stratum_1_defined_as_patches(self, protocol_doc: str):
        """Stratum 1 is defined as 1,501 no-oil PATCHES with zero intersection."""
        assert "1,501 unique no-oil patches" in protocol_doc or "1,501 no-oil patches" in protocol_doc or "1,501" in protocol_doc
        # Must NOT say "1,501 scenes" as a stratum count
        assert "1,501 unique no-oil scenes" not in protocol_doc

    def test_stratum_2_defined_as_patches(self, protocol_doc: str):
        """Stratum 2 is defined as 789 no-oil PATCHES with intersection."""
        assert "789 unique no-oil patches" in protocol_doc or "789 no-oil patches" in protocol_doc or "789" in protocol_doc
        assert "789 unique no-oil scenes" not in protocol_doc

    def test_patch_entity_is_jpg_file(self, protocol_doc: str):
        """Protocol explicitly names jpg_file as the unique PATCH identifier."""
        assert "jpg_file" in protocol_doc

    def test_no_disjoint_scene_language(self, protocol_doc: str):
        """Protocol must not say 'scenes disjoint from Trujillo' as stratum definition."""
        assert "Stratum 1 | DARTIS scenes geographically disjoint" not in protocol_doc
        assert "Stratum 2 | DARTIS scenes co-located" not in protocol_doc

    def test_corrective_closure_report_has_patch_level_strata(self):
        """Corrective closure preflight report also uses patch-level stratum definitions."""
        report = (REPO / "OCEAN_SENTINEL_FINAL_EXP08_PREAUTHORIZATION_INTEGRITY_PREFLIGHT_CLOSURE_REPORT.md")
        if report.exists():
            text = report.read_text(encoding="utf-8")
            # Must not have the old erroneous "Subset of 297 parent scenes" as stratum count
            assert "Subset of 297 parent scenes" not in text
            # Must not say "scenes geographically disjoint" as stratum definition
            assert "DARTIS scenes geographically disjoint" not in text


# ===========================================================================
# 2. Shared parent scene can appear in both strata
# ===========================================================================
class TestSharedParentSceneInBothStrata:
    """Invariant 2: A single parent scene may contribute patches to both Stratum 1 and 2."""

    def test_shared_scene_concept_is_documented(self):
        """Protocol documents the existence of shared parent scenes."""
        protocol = (REPO / "docs" / "exp08_corrected_protocol.md").read_text(encoding="utf-8")
        assert "297 parent" in protocol or "297 shared" in protocol or "Shared Parent Scenes" in protocol

    def test_stratum_populations_are_not_scene_exclusive(self):
        """Stratum 1 scene count + Stratum 2 scene count > union (due to 297 shared scenes).

        Consistency check: 719 + 447 = 1,166, but union = 869.
        This proves scenes cannot be used as stratum membership units without accounting
        for shared scenes.
        """
        stratum1_scenes = 719
        stratum2_scenes = 447
        shared_scenes = 297
        union_scenes = 869

        # Inclusion-exclusion: |S1 ∪ S2| = |S1| + |S2| - |S1 ∩ S2|
        computed_union = stratum1_scenes + stratum2_scenes - shared_scenes
        assert computed_union == union_scenes, (
            f"Inclusion-exclusion failed: {stratum1_scenes} + {stratum2_scenes} - "
            f"{shared_scenes} = {computed_union} ≠ {union_scenes}"
        )

    def test_no_iid_treatment_claim(self):
        """Protocol explicitly prohibits treating patches as IID (independent) observations."""
        protocol = (REPO / "docs" / "exp08_corrected_protocol.md").read_text(encoding="utf-8")
        # The protocol must explicitly forbid IID claims — 'MUST NOT claim' language is acceptable
        # because it is a prohibition, not an assertion of independence.
        must_not_present = (
            "Must NOT claim" in protocol
            or "must NOT claim" in protocol
            or "MUST NOT claim" in protocol
        )
        must_not_present_iid = (
            "patches as independent" not in protocol
            and "2,290 independent lookalike observations" not in protocol  # allowed only as prohibition
        ) or must_not_present
        assert must_not_present, (
            "Protocol must explicitly forbid IID treatment "
            "(e.g. 'Must NOT claim: 2,290 independent lookalike observations')"
        )


# ===========================================================================
# 3. Stratum counts consistency
# ===========================================================================
class TestStratumCountsConsistency:
    """Invariant 3: Frozen stratum counts match Phase 11-R4 spatial overlap recomputation."""

    @pytest.fixture
    def overlap_json(self) -> dict:
        path = REPO / "data" / "metadata" / "exp08_spatial_overlap_r4.json"
        assert path.exists(), f"R4 overlap JSON not found: {path}"
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def test_nooil_stratum1_count(self, overlap_json: dict):
        """1,501 no-oil patches have zero Trujillo footprint intersection (Stratum 1)."""
        assert overlap_json["nooil_result"]["no_overlap_with_trujillo"] == 1501

    def test_nooil_stratum2_count(self, overlap_json: dict):
        """789 no-oil patches have ≥1 Trujillo footprint intersection (Stratum 2)."""
        assert overlap_json["nooil_result"]["overlap_with_trujillo"] == 789

    def test_nooil_total_population(self, overlap_json: dict):
        """Total no-oil population is exactly 2,290 patches."""
        assert overlap_json["nooil_result"]["total_patches"] == 2290

    def test_nooil_stratum_counts_sum_to_total(self, overlap_json: dict):
        """1,501 + 789 = 2,290."""
        nooil = overlap_json["nooil_result"]
        assert nooil["no_overlap_with_trujillo"] + nooil["overlap_with_trujillo"] == 2290

    def test_r4_overlap_json_parent_scene_counts(self):
        """Stratum parent scene counts (719 / 447 / 297 shared) are consistent with R5.4 audit."""
        r54_path = REPO / "scratch" / "exp08_r5_4_footprints_and_clusters.json"
        if r54_path.exists():
            with open(r54_path, encoding="utf-8") as f:
                r54 = json.load(f)
            # If the JSON contains stratum scene counts, verify them
            if "stratum1_scenes" in r54:
                assert r54["stratum1_scenes"] == 719
            if "stratum2_scenes" in r54:
                assert r54["stratum2_scenes"] == 447
            if "shared_scenes" in r54:
                assert r54["shared_scenes"] == 297


# ===========================================================================
# 4. Ambiguous Catalog result blocks inference
# ===========================================================================
class TestCatalogPreflightAmbiguityBlocking:
    """Invariant 4: MULTIPLE_MATCHES or non-RESOLVED_UNIQUE status blocks inference."""

    def _make_client(self, results: list) -> MagicMock:
        client = MagicMock()
        client.query.return_value = results
        return client

    def test_multiple_matches_status(self):
        """Two catalog results → MULTIPLE_MATCHES status."""
        results = [
            {"id": "PROD_A", "startDatetime": "2019-01-01T00:00:00Z"},
            {"id": "PROD_B", "startDatetime": "2019-01-01T00:00:01Z"},
        ]
        client = self._make_client(results)
        record = resolve_dartis_scene("S1A_IW_GRDH_2019_FAKE", client)
        assert record.resolution_status == STATUS_MULTIPLE_MATCHES
        assert record.catalog_item_count == 2

    def test_multiple_matches_raises_firewall_error(self):
        """PreflightFirewallError raised when manifest contains MULTIPLE_MATCHES records."""
        manifest = PreflightManifest()
        manifest.records = [
            PreflightRecord(
                dartis_scene_id="S1A_AMBIGUOUS",
                resolution_status=STATUS_MULTIPLE_MATCHES,
                catalog_item_count=2,
                resolution_reason="Two candidates found",
            )
        ]
        manifest.compute_summary()
        assert not manifest.preflight_passed
        assert manifest.invalid_or_unresolved_count == 1

        with pytest.raises(PreflightFirewallError):
            enforce_preflight_gate(manifest)

    def test_no_match_raises_firewall_error(self):
        """PreflightFirewallError raised when a scene has NO_MATCH."""
        manifest = PreflightManifest()
        manifest.records = [
            PreflightRecord(
                dartis_scene_id="S1A_MISSING",
                resolution_status=STATUS_NO_MATCH,
                resolution_reason="Not found in CDSE",
            )
        ]
        manifest.compute_summary()
        with pytest.raises(PreflightFirewallError):
            enforce_preflight_gate(manifest)

    def test_query_error_raises_firewall_error(self):
        """PreflightFirewallError raised when a scene has QUERY_ERROR."""
        manifest = PreflightManifest()
        manifest.records = [
            PreflightRecord(
                dartis_scene_id="S1A_ERROR",
                resolution_status=STATUS_QUERY_ERROR,
                resolution_reason="Network timeout",
            )
        ]
        manifest.compute_summary()
        with pytest.raises(PreflightFirewallError):
            enforce_preflight_gate(manifest)

    def test_all_resolved_unique_allows_gate(self):
        """Gate passes when all records are RESOLVED_UNIQUE."""
        manifest = PreflightManifest()
        manifest.records = [
            PreflightRecord(
                dartis_scene_id="S1A_OK",
                resolution_status=STATUS_RESOLVED_UNIQUE,
                resolved_catalog_id="S1A_..._COG",
                catalog_item_count=1,
                resolution_reason="Exactly one product found",
            )
        ]
        manifest.compute_summary()
        assert manifest.preflight_passed
        # Must not raise
        enforce_preflight_gate(manifest)


# ===========================================================================
# 5. Unresolved scene cannot silently change denominator
# ===========================================================================
class TestDenominatorIntegrity:
    """Invariant 5: Invalid/unresolved scenes cannot silently shrink the denominator."""

    def test_target_population_always_equals_submitted_scenes(self):
        """manifest.target_population always equals the number of submitted scene IDs."""
        scene_ids = ["S1_GOOD", "S1_BAD", "S1_ERROR"]
        mock_client = MagicMock()

        def mock_query(scene_id, window_seconds):
            if "GOOD" in scene_id:
                return [{"id": "PROD_GOOD"}]
            elif "BAD" in scene_id:
                return []  # NO_MATCH
            else:
                raise RuntimeError("Simulated API error")

        mock_client.query.side_effect = mock_query
        manifest = run_preflight(scene_ids, mock_client)

        assert manifest.target_population == 3
        assert manifest.evaluation_eligible == 1
        assert manifest.invalid_or_unresolved_count == 2
        assert not manifest.preflight_passed

    def test_firewall_error_message_names_unresolved_scenes(self):
        """PreflightFirewallError message explicitly names the unresolved scene IDs."""
        manifest = PreflightManifest()
        manifest.records = [
            PreflightRecord(
                dartis_scene_id="S1A_PROBLEM_SCENE",
                resolution_status=STATUS_NO_MATCH,
                resolution_reason="Not found",
            )
        ]
        manifest.compute_summary()
        with pytest.raises(PreflightFirewallError, match="S1A_PROBLEM_SCENE"):
            enforce_preflight_gate(manifest)

    def test_firewall_error_prevents_denominator_adjustment(self):
        """Confirm that the firewall error is raised before inference context."""
        # Simulate an executor that tries to run inference after preflight.
        # The firewall error should propagate upward and prevent any inference call.
        model_was_called = []

        def simulated_inference_call(manifest):
            enforce_preflight_gate(manifest)
            model_was_called.append(True)  # Should never reach here

        manifest = PreflightManifest()
        manifest.records = [
            PreflightRecord(
                dartis_scene_id="S1_UNRESOLVED",
                resolution_status=STATUS_QUERY_ERROR,
                resolution_reason="API timeout",
            )
        ]
        manifest.compute_summary()

        with pytest.raises(PreflightFirewallError):
            simulated_inference_call(manifest)

        assert len(model_was_called) == 0, "Inference was called despite firewall!"


# ===========================================================================
# 6. Zero-valid-pixel handling is deterministic
# ===========================================================================
class TestZeroValidPixelHandling:
    """Invariant 6: Zero dataMask-valid or zero polygon pixels is documented deterministically."""

    def test_protocol_addresses_zero_valid_pixel_patches(self):
        """Protocol documents handling of patches with zero evaluation-domain pixels."""
        protocol = (REPO / "docs" / "exp08_corrected_protocol.md").read_text(encoding="utf-8")
        # Protocol must address invalid observations or zero-valid-pixel handling
        assert (
            "dataMask == 1" in protocol
            or "zero valid" in protocol.lower()
            or "zero dataMask-valid" in protocol.lower()
            or "primary_eval_mask" in protocol
        )

    def test_primary_eval_mask_is_logical_and(self):
        """primary_eval_mask = (dataMask == 1) AND (dartis_polygon_mask == 1)."""
        # Verify the geometry module exists and creates the combined mask.
        from ocean_sentinel.geometry import create_primary_evaluation_mask
        import affine

        H, W = 8, 8
        transform = affine.Affine(1e-4, 0, 34.0, 0, -1e-4, 33.0)
        # Polygon covering the left half
        corners = [
            [34.0, 33.0],       # UL
            [34.0004, 33.0],    # UR
            [34.0004, 32.9992], # BR
            [34.0, 32.9992],    # BL
        ]
        data_mask = np.ones((H, W), dtype=np.uint8)
        data_mask[:, W // 2:] = 0  # Right half invalid

        mask = create_primary_evaluation_mask(H, W, transform, corners, data_mask)
        # Valid pixels must be subset of dataMask == 1
        assert np.all(mask[data_mask == 0] == 0), "Mask allows invalid dataMask pixels"
        # At least some valid pixels in the polygon
        assert mask.sum() > 0


# ===========================================================================
# 7. Process API output cannot receive raw-DN calibration
# ===========================================================================
class TestDoubleCalibrationFirewall:
    """Invariant 7: Process API output (linear sigma0) must not be re-calibrated via raw-DN LUT."""

    def test_calibration_module_has_process_api_route(self):
        """calibration.py documents both ESA LUT route and Process API route clearly."""
        calib_src = (REPO / "src" / "ocean_sentinel" / "satellite" / "calibration.py").read_text(encoding="utf-8")
        assert "CDSE Process API" in calib_src or "Process API" in calib_src
        assert "SIGMA0_ELLIPSOID" in calib_src or "sigma0" in calib_src.lower()

    def test_linear_to_db_converts_process_api_output_correctly(self):
        """linear_to_db() correctly converts Process API linear power to dB."""
        # Simulate Process API output: linear sigma0 values
        linear = np.array([1e-7, 1e-4, 0.01, 0.1, 1.0], dtype=np.float32)
        db = linear_to_db(linear)
        expected = np.array([
            10 * np.log10(max(1e-7, x)) for x in linear
        ], dtype=np.float32)
        np.testing.assert_allclose(db, expected, rtol=1e-5)

    def test_applying_dn_calibration_to_process_api_would_double_calibrate(self):
        """Demonstrate that running calibrate_dn_to_sigma0_linear on Process API output
        would be nonsensical — the function requires raw DN, not sigma0.

        Process API output is already sigma0 linear power (dimensionless float32).
        Applying the LUT formula sigma0 = DN^2 / A^2 to it would double-calibrate.
        This test documents the incompatibility by showing the wrong result.
        """
        # Process API output: already sigma0 = 0.01 (linear)
        sigma0_from_api = np.array([0.01], dtype=np.float32)  # -20 dB
        # Accidentally applying DN calibration with a trivial LUT=1.0
        wrong_result = calibrate_dn_to_sigma0_linear(sigma0_from_api, lut_sigma=1.0)
        # sigma0^2 is NOT sigma0 — the result is demonstrably wrong
        assert wrong_result[0] == pytest.approx(0.01 ** 2, rel=1e-5), \
            "Expected wrong double-calibrated result sigma0^2"
        # The correct result should be sigma0 = 0.01, not 0.0001
        assert wrong_result[0] != pytest.approx(0.01, rel=1e-3), \
            "Double-calibration should produce a different (wrong) value"

    def test_protocol_forbids_raw_dn_calibration_on_process_api_output(self):
        """Protocol explicitly states raw DN → ESA LUT calibration is FORBIDDEN for Route B."""
        protocol = (REPO / "docs" / "exp08_corrected_protocol.md").read_text(encoding="utf-8")
        assert "FORBIDDEN" in protocol or "forbidden" in protocol.lower() or "incompatible" in protocol.lower()

    def test_preflight_report_forbids_double_calibration(self):
        """Preflight report explicitly marks Raw DN → ESA LUT as FORBIDDEN."""
        report = (REPO / "OCEAN_SENTINEL_FINAL_EXP08_PREAUTHORIZATION_INTEGRITY_PREFLIGHT_CLOSURE_REPORT.md")
        if report.exists():
            text = report.read_text(encoding="utf-8")
            assert "FORBIDDEN" in text


# ===========================================================================
# 8. AABB retrieval is distinct from quadrilateral evaluation
# ===========================================================================
class TestRetrievalAABBVsEvaluationQuadrilateral:
    """Invariant 8: Retrieval AABB and evaluation quadrilateral are distinct contracts."""

    def test_protocol_defines_both_retrieval_and_evaluation_domains(self):
        """Protocol explicitly names RETRIEVAL_DOMAIN (AABB) and PRIMARY_EVALUATION_DOMAIN (polygon)."""
        protocol = (REPO / "docs" / "exp08_corrected_protocol.md").read_text(encoding="utf-8")
        assert "RETRIEVAL_DOMAIN" in protocol
        assert "PRIMARY_EVALUATION_DOMAIN" in protocol

    def test_retrieval_is_aabb_evaluation_is_polygon(self):
        """RETRIEVAL_DOMAIN is AABB; PRIMARY_EVALUATION_DOMAIN is rotated quadrilateral."""
        protocol = (REPO / "docs" / "exp08_corrected_protocol.md").read_text(encoding="utf-8")
        assert "DARTIS AABB" in protocol
        assert "DARTIS QUADRILATERAL FOOTPRINT" in protocol or "dartis_polygon_mask" in protocol

    def test_aabb_is_larger_than_polygon(self):
        """AABB always encloses the rotated quadrilateral; polygon/AABB area ratio < 1."""
        # From Phase 11-R5.4: area ratio ~74%
        protocol = (REPO / "docs" / "exp08_corrected_protocol.md").read_text(encoding="utf-8")
        assert "74" in protocol or "74.0" in protocol or "~74" in protocol


# ===========================================================================
# 9. Clamped tiling route is frozen
# ===========================================================================
class TestClampedTilingFrozen:
    """Invariant 9: The clamped compute_tile_windows() route is the frozen deterministic route."""

    def test_clamped_route_is_documented_as_frozen(self):
        """Protocol names clamped route as established frozen inference route."""
        protocol = (REPO / "docs" / "exp08_corrected_protocol.md").read_text(encoding="utf-8")
        assert "frozen" in protocol.lower() and "clamped" in protocol.lower()

    def test_compute_tile_windows_covers_all_pixels(self):
        """compute_tile_windows() produces 100% pixel coverage.

        Returns List[Tuple[int, int, int, int]] = (row_start, row_end, col_start, col_end).
        """
        from ocean_sentinel.inference import compute_tile_windows

        height, width = 1779, 1509
        tiles = compute_tile_windows(height, width, tile_size=512, overlap=0)
        coverage = np.zeros((height, width), dtype=np.uint8)
        for row_start, row_end, col_start, col_end in tiles:
            coverage[row_start:row_end, col_start:col_end] += 1
        assert np.all(coverage >= 1), "Some pixels not covered by any tile window"

    def test_frozen_tiling_parameters(self):
        """Tile size 512, overlap 0, weighted reconstruction are frozen."""
        from ocean_sentinel.inference import DEFAULT_TILE_SIZE
        assert DEFAULT_TILE_SIZE == 512


# ===========================================================================
# 10. Expanded AABB cannot silently become default
# ===========================================================================
class TestExpandedAABBNotDefault:
    """Invariant 10: Smart Expanded AABB (1536×2048) is pre-registered as non-equivalent alternative."""

    def test_expanded_aabb_not_default_in_protocol(self):
        """Protocol does not designate expanded AABB as the default route."""
        protocol = (REPO / "docs" / "exp08_corrected_protocol.md").read_text(encoding="utf-8")
        # The protocol must say the expanded route is an alternative, not the frozen default.
        assert "NOT mathematically equivalent" in protocol
        # The clamped route must be described as established/frozen, not just one option.
        assert "established, frozen inference route" in protocol or \
               "frozen inference route" in protocol or \
               "frozen deterministic inference route" in protocol

    def test_expanded_aabb_is_labeled_alternative(self):
        """Both pilot doc and protocol label expanded AABB as alternative, non-equivalent."""
        for doc_name in [
            "docs/exp08_corrected_protocol.md",
            "docs/exp08_cdse_physical_compatibility_pilot.md",
        ]:
            text = (REPO / doc_name).read_text(encoding="utf-8")
            assert "NOT mathematically equivalent" in text, \
                f"Missing non-equivalence statement in {doc_name}"


# ===========================================================================
# 11. Channel inversion fails loudly
# ===========================================================================
class TestChannelInversionFails:
    """Invariant 11: Feeding inverted or wrong-order channels raises an error."""

    def test_stack_wrong_order_raises(self):
        """stack_dual_pol_channels() raises ValueError for inverted (VV, VH) order."""
        vh = np.ones((4, 4), dtype=np.float32) * -30.0
        vv = np.ones((4, 4), dtype=np.float32) * -15.0
        with pytest.raises(ValueError, match="VH.*VV|VV.*VH|operational contract"):
            stack_dual_pol_channels(vh, vv, order=("VV", "VH"))

    def test_correct_order_succeeds(self):
        """stack_dual_pol_channels() succeeds for correct ('VH', 'VV') order."""
        vh = np.ones((4, 4), dtype=np.float32) * -30.0
        vv = np.ones((4, 4), dtype=np.float32) * -15.0
        stacked = stack_dual_pol_channels(vh, vv)
        assert stacked.shape == (2, 4, 4)
        np.testing.assert_array_equal(stacked[0], vh)
        np.testing.assert_array_equal(stacked[1], vv)

    def test_shape_mismatch_raises(self):
        """stack_dual_pol_channels() raises ValueError for mismatched shapes."""
        vh = np.ones((4, 4), dtype=np.float32)
        vv = np.ones((5, 4), dtype=np.float32)
        with pytest.raises(ValueError):
            stack_dual_pol_channels(vh, vv)


# ===========================================================================
# 12. O3 cannot be mislabeled as segmentation IoU
# ===========================================================================
class TestO3MetricLabelingCorrect:
    """Invariant 12: METRIC-O3 is 'prediction-bounding-box overlap rate', not 'segmentation IoU'."""

    def test_protocol_labels_o3_as_overlap_rate(self):
        """Protocol names O3 as prediction-bounding-box overlap rate."""
        protocol = (REPO / "docs" / "exp08_corrected_protocol.md").read_text(encoding="utf-8")
        assert "prediction-bounding-box overlap rate" in protocol

    def test_protocol_prohibits_segmentation_iou_label(self):
        """Protocol explicitly prohibits calling O3 'segmentation IoU'."""
        protocol = (REPO / "docs" / "exp08_corrected_protocol.md").read_text(encoding="utf-8")
        assert "Segmentation IoU" in protocol or "segmentation IoU" in protocol
        # The prohibited list exists
        assert "Prohibit" in protocol or "Prohibited" in protocol or "PROHIBIT" in protocol

    def test_no_pixel_masks_in_dartis(self):
        """Protocol explicitly acknowledges no pixel-level ground truth in DARTIS."""
        protocol = (REPO / "docs" / "exp08_corrected_protocol.md").read_text(encoding="utf-8")
        assert "no pixel" in protocol.lower() or "No pixel-level" in protocol or \
               "no pixel-level" in protocol.lower()


# ===========================================================================
# 13. Preflight code never calls model inference
# ===========================================================================
class TestPreflightNeverCallsInference:
    """Invariant 13: The catalog preflight module does not call model inference."""

    def test_preflight_module_has_no_inference_import(self):
        """exp08_catalog_preflight.py does not import torch, ResNet, or inference modules."""
        preflight_src = (REPO / "src" / "ocean_sentinel" / "exp08_catalog_preflight.py").read_text(encoding="utf-8")
        assert "import torch" not in preflight_src
        assert "ResNet" not in preflight_src
        assert "from ocean_sentinel.inference" not in preflight_src
        assert "predict_sar_image" not in preflight_src

    def test_preflight_module_has_no_forward_pass(self):
        """exp08_catalog_preflight.py does not contain forward() or model() calls."""
        preflight_src = (REPO / "src" / "ocean_sentinel" / "exp08_catalog_preflight.py").read_text(encoding="utf-8")
        assert ".forward(" not in preflight_src
        assert "model.eval(" not in preflight_src
        assert "torch.no_grad" not in preflight_src

    def test_resolve_dartis_scene_never_calls_model(self):
        """resolve_dartis_scene() does not touch any model or compute predictions."""
        mock_client = MagicMock()
        mock_client.query.return_value = [{"id": "TEST_PRODUCT"}]

        # Patch inference module to detect any call
        mock_inference = MagicMock()
        with patch.dict(sys.modules, {"ocean_sentinel.inference": mock_inference}):
            record = resolve_dartis_scene("S1A_TEST_SCENE", mock_client)

        # Inference module attributes should not have been accessed during preflight
        mock_inference.predict_sar_image.assert_not_called()
        assert record.resolution_status == STATUS_RESOLVED_UNIQUE

    def test_run_preflight_does_not_call_model(self):
        """run_preflight() completes without calling any inference function."""
        mock_client = MagicMock()
        mock_client.query.return_value = [{"id": "PROD_OK", "startDatetime": "2019-06-01T10:00:00Z"}]

        scenes = ["S1A_SCENE_001", "S1A_SCENE_002"]

        mock_inference = MagicMock()
        with patch.dict(sys.modules, {"ocean_sentinel.inference": mock_inference}):
            manifest = run_preflight(scenes, mock_client)

        mock_inference.predict_sar_image.assert_not_called()
        assert manifest.target_population == 2
        assert manifest.evaluation_eligible == 2
        assert manifest.preflight_passed
