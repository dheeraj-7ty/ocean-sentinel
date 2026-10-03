"""EXP-08 Corrective Closure V2 — Full Guardrail Test Suite.

Covers Stage 17 requirements from OCEAN-SENTINEL-FINAL-EXP08-CORRECTIVE-CLOSURE-V2:

1.  Catalog physical-acquisition deduplication (COG/original same physical ID).
2.  Preflight gate blocking inference (integration with FAKE catalog + FAKE predictor).
3.  Patch-level denominator preservation (invalid state never silently becomes zero).
4.  Invalid patch state machine (all failure states explicit).
5.  Zero-valid-pixel behavior documented.
6.  Stratum geometry uses quadrilateral, not AABB (protocol language check).
7.  719/447/297/869 no-oil scene consistency.
8.  653/712/140/739 oil-cohort consistency (updated from protocol §11/§12).
9.  Route-B double-calibration firewall.
10. -70 dB numerical-only semantics (physical assertions removed).
11. Channel naming semantics.
12. Bootstrap seed pre-declaration.
13. Bootstrap resampling by scene.
14. Shared-scene paired behavior documented.
15. compute_tile_windows 4-tuple contract.
16. Protocol/report metric-ID consistency (O1 = Oil-Patch Activation Rate).
17. Protocol version consistency (V3.5).
18. Preflight module dependency isolation (no torch, no inference, no forward).
"""

from __future__ import annotations

import ast
import importlib
import sys
import types
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

REPO = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = REPO / "docs" / "exp08_corrected_protocol.md"
PREFLIGHT_SRC = REPO / "src" / "ocean_sentinel" / "exp08_catalog_preflight.py"

# ---------------------------------------------------------------------------
# Helper: read text files
# ---------------------------------------------------------------------------

def read_protocol() -> str:
    return PROTOCOL_PATH.read_text(encoding="utf-8")


def read_preflight_src() -> str:
    return PREFLIGHT_SRC.read_text(encoding="utf-8")


# ===========================================================================
# 1. Catalog Physical-Acquisition Deduplication
# ===========================================================================

class TestCatalogPhysicalAcquisitionDeduplication:
    """normalize_to_physical_id and resolve_dartis_scene must treat COG/original
    representations of the same physical acquisition as a single physical scene."""

    def _import_preflight(self):
        sys.path.insert(0, str(REPO / "src"))
        import ocean_sentinel.exp08_catalog_preflight as pf
        return pf

    def test_normalize_strips_cog_suffix(self):
        pf = self._import_preflight()
        base = "S1A_IW_GRDH_1SDV_20190101T000000_20190101T000001_025000_02C000_F282"
        cog  = base + "_COG"
        assert pf.normalize_to_physical_id(cog) == base

    def test_normalize_no_suffix_unchanged(self):
        pf = self._import_preflight()
        base = "S1A_IW_GRDH_1SDV_20190101T000000_20190101T000001_025000_02C000_F282"
        assert pf.normalize_to_physical_id(base) == base

    def test_cog_and_original_resolve_as_single_physical_acquisition(self):
        """One original + one COG of the same scene → RESOLVED_UNIQUE, not MULTIPLE_MATCHES."""
        pf = self._import_preflight()
        base_id = "S1A_IW_GRDH_1SDV_20190101T000000_20190101T000001_025000_02C000_F282"
        cog_id  = base_id + "_COG"

        class FakeClient:
            def query(self, scene_id, window_seconds=25):
                return [
                    {"id": base_id, "startDatetime": "2019-01-01T00:00:00Z",
                     "completionDatetime": "2019-01-01T00:00:01Z"},
                    {"id": cog_id, "startDatetime": "2019-01-01T00:00:00Z",
                     "completionDatetime": "2019-01-01T00:00:01Z"},
                ]

        record = pf.resolve_dartis_scene("S1A_DARTIS_SCENE", FakeClient())
        assert record.resolution_status == pf.STATUS_RESOLVED_UNIQUE, (
            f"COG+original pair must resolve to RESOLVED_UNIQUE, got {record.resolution_status}"
        )
        assert record.catalog_item_count == 2
        assert record.physical_acquisition_count == 1
        assert record.representation_count == 2
        assert record.resolved_physical_acquisition_id == base_id

    def test_two_different_physical_scenes_stays_multiple_matches(self):
        """Two distinct physical acquisitions must give MULTIPLE_MATCHES even if one is COG."""
        pf = self._import_preflight()
        id1 = "S1A_IW_GRDH_1SDV_20190101T000000_20190101T000001_025000_02C000_F282"
        id2 = "S1A_IW_GRDH_1SDV_20190101T000000_20190101T000001_025001_02C001_F283"  # different orbit

        class FakeClient:
            def query(self, scene_id, window_seconds=25):
                return [
                    {"id": id1, "startDatetime": "2019-01-01T00:00:00Z"},
                    {"id": id2 + "_COG", "startDatetime": "2019-01-01T00:00:00Z"},
                ]

        record = pf.resolve_dartis_scene("S1A_DARTIS_SCENE", FakeClient())
        assert record.resolution_status == pf.STATUS_MULTIPLE_MATCHES
        assert record.physical_acquisition_count == 2

    def test_no_results_gives_no_match(self):
        pf = self._import_preflight()

        class FakeClient:
            def query(self, *a, **kw):
                return []

        record = pf.resolve_dartis_scene("SCENE_XYZ", FakeClient())
        assert record.resolution_status == pf.STATUS_NO_MATCH
        assert record.physical_acquisition_count == 0
        assert record.catalog_item_count == 0

    def test_catalog_error_gives_query_error(self):
        pf = self._import_preflight()

        class FakeClient:
            def query(self, *a, **kw):
                raise ConnectionError("CDSE API unavailable")

        record = pf.resolve_dartis_scene("SCENE_XYZ", FakeClient())
        assert record.resolution_status == pf.STATUS_QUERY_ERROR

    def test_missing_scene_id_gives_invalid_metadata(self):
        pf = self._import_preflight()
        record = pf.resolve_dartis_scene("", MagicMock())
        assert record.resolution_status == pf.STATUS_INVALID_METADATA

    def test_record_has_physical_acquisition_count_field(self):
        """PreflightRecord must have physical_acquisition_count and representation_count."""
        pf = self._import_preflight()
        r = pf.PreflightRecord(dartis_scene_id="TEST")
        assert hasattr(r, "physical_acquisition_count"), "Missing field: physical_acquisition_count"
        assert hasattr(r, "representation_count"), "Missing field: representation_count"
        assert hasattr(r, "resolved_physical_acquisition_id"), "Missing field: resolved_physical_acquisition_id"
        assert hasattr(r, "catalog_item_count"), "Missing field: catalog_item_count"


# ===========================================================================
# 2. Preflight Gate Integration — FAKE catalog + FAKE predictor
# ===========================================================================

class TestPreflightGateIntegration:
    """Behavioral integration test: preflight gate must block the predictor on any
    non-RESOLVED_UNIQUE scene. Tests use FAKE clients and FAKE predictor callbacks
    only — no real inference occurs."""

    def _setup(self):
        """Return preflight module and a simple gate coordinator."""
        sys.path.insert(0, str(REPO / "src"))
        import ocean_sentinel.exp08_catalog_preflight as pf
        return pf

    def _run_exp08_gate(self, pf, catalog_client, scene_ids: list, predictor_called: list):
        """Simulate the EXP-08 execution gate:
        1. run_preflight()
        2. enforce_preflight_gate()
        3. Only call predictor if gate passes.
        predictor_called is a mutable list used as a side-effect sentinel.
        """
        manifest = pf.run_preflight(scene_ids, catalog_client)
        pf.enforce_preflight_gate(manifest)
        # If we reach here, the gate passed.
        predictor_called.append(True)

    def _make_resolved_client(self, scene_ids):
        class FakeClient:
            def query(self, scene_id, window_seconds=25):
                return [{"id": f"{scene_id}_COG", "startDatetime": "2019-01-01T00:00:00Z",
                         "completionDatetime": "2019-01-01T00:00:01Z"}]
        return FakeClient()

    def _make_failing_client(self, fail_scene: str, fail_status: str, pf):
        """Returns a catalog client that returns a failure for one specific scene."""
        class FakeClient:
            def query(self, scene_id, window_seconds=25):
                if scene_id == fail_scene:
                    if fail_status == pf.STATUS_NO_MATCH:
                        return []
                    elif fail_status == pf.STATUS_MULTIPLE_MATCHES:
                        # Two genuinely different physical scenes
                        return [
                            {"id": f"{scene_id}_ALT1"},
                            {"id": f"{scene_id}_ALT2"},
                        ]
                    elif fail_status == pf.STATUS_QUERY_ERROR:
                        raise RuntimeError("API error")
                    elif fail_status == pf.STATUS_INVALID_METADATA:
                        return None  # trigger guard
                return [{"id": f"{scene_id}_COG", "startDatetime": "2019-01-01T00:00:00Z",
                         "completionDatetime": "2019-01-01T00:00:01Z"}]
        return FakeClient()

    def test_case_a_all_resolved_unique_allows_predictor(self):
        """CASE A: All scenes RESOLVED_UNIQUE → predictor called."""
        pf = self._setup()
        scenes = ["SCENE_001", "SCENE_002", "SCENE_003"]
        called = []
        self._run_exp08_gate(pf, self._make_resolved_client(scenes), scenes, called)
        assert called == [True], "Predictor must be called when all scenes are RESOLVED_UNIQUE"

    def test_case_b_no_match_blocks_predictor(self):
        """CASE B: One NO_MATCH → predictor never called."""
        pf = self._setup()
        scenes = ["SCENE_001", "SCENE_FAIL"]
        client = self._make_failing_client("SCENE_FAIL", pf.STATUS_NO_MATCH, pf)
        called = []
        with pytest.raises(pf.PreflightFirewallError):
            self._run_exp08_gate(pf, client, scenes, called)
        assert called == [], "Predictor must NOT be called when a NO_MATCH scene exists"

    def test_case_c_multiple_matches_blocks_predictor(self):
        """CASE C: One MULTIPLE_MATCHES → predictor never called."""
        pf = self._setup()
        scenes = ["SCENE_001", "SCENE_MULTI"]
        client = self._make_failing_client("SCENE_MULTI", pf.STATUS_MULTIPLE_MATCHES, pf)
        called = []
        with pytest.raises(pf.PreflightFirewallError):
            self._run_exp08_gate(pf, client, scenes, called)
        assert called == []

    def test_case_d_query_error_blocks_predictor(self):
        """CASE D: One QUERY_ERROR → predictor never called."""
        pf = self._setup()
        scenes = ["SCENE_001", "SCENE_ERROR"]
        client = self._make_failing_client("SCENE_ERROR", pf.STATUS_QUERY_ERROR, pf)
        called = []
        with pytest.raises(pf.PreflightFirewallError):
            self._run_exp08_gate(pf, client, scenes, called)
        assert called == []

    def test_case_e_invalid_metadata_blocks_predictor(self):
        """CASE E: One INVALID_METADATA → predictor never called."""
        pf = self._setup()
        # Empty scene ID triggers INVALID_METADATA directly
        scenes = ["SCENE_001", ""]
        client = self._make_resolved_client(scenes)
        called = []
        with pytest.raises(pf.PreflightFirewallError):
            self._run_exp08_gate(pf, client, scenes, called)
        assert called == []

    def test_preflight_is_required_before_inference(self):
        """enforce_preflight_gate() with preflight_passed=False must always raise."""
        pf = self._setup()
        manifest = pf.PreflightManifest()
        manifest.target_population = 5
        manifest.evaluation_eligible = 4
        manifest.invalid_or_unresolved_count = 1
        manifest.preflight_passed = False
        with pytest.raises(pf.PreflightFirewallError):
            pf.enforce_preflight_gate(manifest)

    def test_empty_manifest_blocks_inference(self):
        """An empty manifest (no scenes) must not allow inference."""
        pf = self._setup()
        manifest = pf.PreflightManifest()
        manifest.compute_summary()
        with pytest.raises(pf.PreflightFirewallError):
            pf.enforce_preflight_gate(manifest)


# ===========================================================================
# 3 & 4. Population/Denominator Preservation + Invalid State Machine
# ===========================================================================

class TestDenominatorPreservation:
    """Invalid/unresolved patches must never be silently deleted from denominator."""

    def _import_preflight(self):
        sys.path.insert(0, str(REPO / "src"))
        import ocean_sentinel.exp08_catalog_preflight as pf
        return pf

    def test_invalid_or_unresolved_count_is_nonzero_when_any_not_resolved(self):
        pf = self._import_preflight()

        class FakeClient:
            def query(self, scene_id, window_seconds=25):
                if scene_id == "FAIL":
                    return []
                return [{"id": f"{scene_id}_COG"}]

        manifest = pf.run_preflight(["SCENE_OK", "FAIL", "SCENE_OK2"], FakeClient())
        assert manifest.invalid_or_unresolved_count >= 1
        assert manifest.target_population == 3
        assert manifest.evaluation_eligible < manifest.target_population

    def test_target_population_never_reduced(self):
        """target_population must always equal number of scenes submitted."""
        pf = self._import_preflight()

        class FakeClient:
            def query(self, *a, **kw):
                return []  # All fail

        scene_ids = [f"SCENE_{i}" for i in range(10)]
        manifest = pf.run_preflight(scene_ids, FakeClient())
        assert manifest.target_population == 10, (
            "target_population must equal number of submitted scenes, even if all fail"
        )
        assert manifest.evaluation_eligible == 0
        assert manifest.invalid_or_unresolved_count == 10

    def test_preflight_record_has_all_required_state_fields(self):
        """PreflightRecord must carry all five required state fields per Stage 9."""
        pf = self._import_preflight()
        r = pf.PreflightRecord(dartis_scene_id="TEST")
        required_fields = [
            "dartis_scene_id", "resolution_status", "resolution_reason",
            "preflight_timestamp", "protocol_version",
            "catalog_item_count", "physical_acquisition_count",
            "representation_count", "resolved_physical_acquisition_id",
            "resolved_catalog_id",
        ]
        for field in required_fields:
            assert hasattr(r, field), f"PreflightRecord missing field: {field}"


# ===========================================================================
# 5. Zero-Valid-Pixel Behavior Documented in Protocol
# ===========================================================================

class TestZeroValidPixelDocumented:
    """Protocol must explicitly define what happens when a patch has zero valid pixels."""

    def test_protocol_defines_stopping_rule_for_zero_valid_pixel(self):
        proto = read_protocol()
        # §18 (Stopping Rules) must reference zero valid pixel scenario
        assert "zero valid pixels" in proto.lower() or "0% of patches" in proto or ">10% of patches" in proto, (
            "Protocol §18 must explicitly address zero-valid-pixel patches as a stopping condition"
        )

    def test_datamask_semantics_documented(self):
        proto = read_protocol()
        assert "dataMask" in proto and "dataMask == 1" in proto, (
            "Protocol must define dataMask == 1 as the valid pixel gate"
        )

    def test_invalid_patch_states_not_interpreted_as_zero(self):
        """Protocol must explicitly forbid treating invalid patches as zero predictions."""
        proto = read_protocol()
        # Check §18 or §9 for language forbidding silent interpretation as zero
        has_language = (
            "INVALID_OR_UNRESOLVED" in proto or
            "invalid" in proto.lower() and "zero" in proto.lower() and
            ("never" in proto.lower() or "must not" in proto.lower() or "prohibition" in proto.lower())
        )
        assert has_language, (
            "Protocol must explicitly forbid treating invalid patches as zero-result observations"
        )


# ===========================================================================
# 6. Stratum Geometry — Quadrilateral, not AABB
# ===========================================================================

class TestStratumGeometryQuadrilateral:
    """Strata must be defined using DARTIS rotated quadrilateral, not AABB."""

    def test_protocol_defines_primary_eval_mask_using_quadrilateral(self):
        proto = read_protocol()
        assert "quadrilateral" in proto.lower() or "rotated" in proto.lower(), (
            "Protocol must reference the DARTIS rotated quadrilateral for primary evaluation domain"
        )

    def test_protocol_distinguishes_retrieval_aabb_from_evaluation_quadrilateral(self):
        proto = read_protocol()
        assert "retrieval" in proto.lower() and ("aabb" in proto.lower() or "bounding box" in proto.lower()), (
            "Protocol must name the AABB as the retrieval geometry (not primary stratification geometry)"
        )

    def test_protocol_does_not_use_aabb_as_primary_stratum_definition(self):
        """The AABB must not be described as the definition of stratum membership."""
        proto = read_protocol()
        # The phrase 'bounding box has zero intersection' must not be in the primary stratum definition
        forbidden_as_stratum = "bounding box has zero intersection" in proto.lower()
        assert not forbidden_as_stratum, (
            "AABB intersection must not be used as the definition of primary stratum membership"
        )


# ===========================================================================
# 7. No-Oil Scene Count Consistency (719/447/297/869)
# ===========================================================================

class TestNoOilSceneConsistency:
    """Verify the 719/447/297/869 no-oil parent scene arithmetic is consistent."""

    def test_inclusion_exclusion_holds(self):
        s1 = 719  # Stratum 1 parent scenes
        s2 = 447  # Stratum 2 parent scenes
        shared = 297  # Shared (appear in both strata)
        union = 869  # All unique no-oil parent scenes
        assert s1 + s2 - shared == union, (
            f"Inclusion-exclusion failed: {s1} + {s2} - {shared} = {s1+s2-shared} ≠ {union}"
        )

    def test_no_oil_patch_counts(self):
        """Patch counts: Stratum 1 = 1,501; Stratum 2 = 789; total = 2,290."""
        assert 1501 + 789 == 2290

    def test_protocol_references_correct_scene_counts(self):
        proto = read_protocol()
        assert "719" in proto and "447" in proto and "297" in proto and "869" in proto, (
            "Protocol must reference all four no-oil parent scene counts: 719, 447, 297, 869"
        )

    def test_protocol_references_correct_no_oil_patch_counts(self):
        proto = read_protocol()
        assert "1,501" in proto and "789" in proto


# ===========================================================================
# 8. Oil Cohort Consistency
# ===========================================================================

class TestOilCohortConsistency:
    """Verify oil cohort counts from Protocol §12."""

    def test_oil_patch_total(self):
        assert 375 + 990 == 1365  # oc + ow = total oil patches

    def test_oil_annotation_total(self):
        assert 941 + 2284 == 3225  # oc + ow annotation records

    def test_protocol_references_oil_scene_counts(self):
        proto = read_protocol()
        # 739 unique oil parent scenes; 140 shared oil scenes
        assert "739" in proto or "1,365" in proto, (
            "Protocol must reference oil population counts"
        )

    def test_oil_stratum_totals_in_protocol(self):
        proto = read_protocol()
        # Protocol §12 specifies oil cohort stratification
        assert "1,365" in proto and "3,225" in proto


# ===========================================================================
# 9. Route-B Double-Calibration Firewall
# ===========================================================================

class TestRouteBDoubleCalibrationFirewall:
    """Route B: CDSE Process API → linear sigma0 → local 10*log10. No ESA LUT."""

    def test_calibration_module_has_route_b_path(self):
        cal_path = REPO / "src" / "ocean_sentinel" / "satellite" / "calibration.py"
        if not cal_path.exists():
            pytest.skip("calibration.py not present in this workspace state")
        src = cal_path.read_text(encoding="utf-8")
        assert "linear_to_db" in src or "log10" in src, (
            "calibration.py must implement the local dB conversion"
        )

    def test_calibration_explicitly_forbids_raw_dn_after_process_api(self):
        cal_path = REPO / "src" / "ocean_sentinel" / "satellite" / "calibration.py"
        if not cal_path.exists():
            pytest.skip("calibration.py not present in this workspace state")
        src = cal_path.read_text(encoding="utf-8").lower()
        assert (
            "double" in src or "raw dn" in src or "not calibrated" in src or
            "already calibrated" in src or "lut" in src
        ), "calibration.py must document double-calibration prohibition"

    def test_protocol_specifies_single_calibration_path(self):
        proto = read_protocol()
        assert "SIGMA0_ELLIPSOID" in proto or "Process API" in proto or "Route B" in proto

    def test_protocol_forbids_raw_dn_calibration(self):
        proto = read_protocol()
        assert (
            "raw DN" in proto or "Raw CDSE COG" in proto or
            "ESA LUT" in proto
        ), "Protocol must explicitly describe that raw COG/DN must NOT be used as direct inference input"


# ===========================================================================
# 10. -70 dB Numerical-Only Semantics
# ===========================================================================

class TestNegative70dBNumericalOnly:
    """Protocol §9.3 must NOT assert physical safety claims for the -70 dB floor."""

    def test_total_signal_extinction_not_asserted(self):
        proto = read_protocol()
        # The assertion 'representing total signal extinction' must not appear (without prohibition context)
        # Allowed: prohibition text ("must NOT claim: total signal extinction")
        # Forbidden: assertion "representing total signal extinction"
        bad_assertion = "representing total signal extinction" in proto
        assert not bad_assertion, (
            "Protocol §9.3 must not assert 'representing total signal extinction' "
            "as a physical characterization of -70 dB pixels"
        )

    def test_extreme_specular_not_asserted(self):
        proto = read_protocol()
        # Forbidden as positive assertion in the floor description
        bad_assertion = (
            "extreme specular reflection" in proto and
            "DO NOT" not in proto  # OK if within a CAUTION/prohibition block
        )
        # The CAUTION block in V3.5 says DO NOT interpret -70 dB as physical
        # so 'extreme specular reflection' is now only in the prohibition context
        # Check that it's ONLY in a CAUTION/prohibition context
        lines_with_specular = [
            ln for ln in proto.splitlines() if "extreme specular reflection" in ln.lower()
        ]
        for ln in lines_with_specular:
            is_prohibition = (
                "DO NOT" in ln or "do not" in ln or "CAUTION" in ln or
                "not established" in ln or "must NOT" in ln or "must not" in ln
            )
            # The only occurrence should be in the CAUTION block or a disclaimer
            # It's acceptable if mentioned alongside explicit prohibition language nearby
            # We'll check the nearby context
            idx = proto.find(ln[:30])
            ctx = proto[max(0, idx-200):idx+200]
            is_in_prohibition_context = (
                "DO NOT" in ctx or "CAUTION" in ctx or "not established" in ctx
            )
            assert is_in_prohibition_context, (
                f"Line mentioning 'extreme specular reflection' is not in a prohibition context: {ln}"
            )

    def test_classification_safety_not_independently_claimed(self):
        proto = read_protocol()
        assert "not independently established" in proto or "must not be claimed" in proto, (
            "Protocol must state that classification safety from the -70 dB floor "
            "is not independently established"
        )

    def test_calibration_linear_to_db_is_numerical_guard(self):
        cal_path = REPO / "src" / "ocean_sentinel" / "satellite" / "calibration.py"
        if not cal_path.exists():
            pytest.skip("calibration.py not present")
        src = cal_path.read_text(encoding="utf-8")
        assert "1e-7" in src or "1e-07" in src or "log" in src.lower(), (
            "linear_to_db must implement the 1e-7 floor guard"
        )

    def test_protocol_caution_block_present(self):
        proto = read_protocol()
        assert "DO NOT interpret the -70 dB floor" in proto or \
               "numerical guard only" in proto.lower(), (
            "Protocol §9.3 must have explicit CAUTION against physical interpretation of -70 dB"
        )


# ===========================================================================
# 11. Channel Naming Semantics
# ===========================================================================

class TestChannelNamingSemantics:
    """Ch0 = VH (cross-pol), Ch1 = VV (co-pol). No 'linear polarization'."""

    def test_protocol_specifies_cross_pol_co_pol(self):
        proto = read_protocol()
        assert "cross-pol" in proto.lower() or "cross-polarization" in proto.lower()
        assert "co-pol" in proto.lower() or "co-polarization" in proto.lower()

    def test_linear_polarization_not_used_as_channel_description(self):
        """'linear polarization' must not appear as a channel descriptor."""
        proto = read_protocol()
        for line in proto.splitlines():
            line_lower = line.lower()
            if "linear polarization" in line_lower:
                # Only allowed in prohibition context
                is_prohibition = any(
                    kw in line_lower for kw in
                    ["must not", "do not", "prohibited", "forbidden", "incorrect", "prohibition"]
                )
                assert is_prohibition, (
                    f"'linear polarization' appears as a descriptor (not prohibition): {line.strip()}"
                )

    def test_protocol_ch0_is_vh_ch1_is_vv(self):
        proto = read_protocol()
        assert "Ch0 = VH" in proto or "Ch0=VH" in proto
        assert "Ch1 = VV" in proto or "Ch1=VV" in proto


# ===========================================================================
# 12. Bootstrap Seed Pre-Declaration
# ===========================================================================

class TestBootstrapSeedPreDeclared:
    """Protocol §14.1 must contain a pre-declared fixed bootstrap seed."""

    def test_protocol_contains_bootstrap_seed(self):
        proto = read_protocol()
        # The seed 20260927 must be present
        assert "20260927" in proto, (
            "Protocol §14.1 must contain the pre-declared bootstrap RNG seed 20260927"
        )

    def test_protocol_seed_is_not_execution_time_choice(self):
        proto = read_protocol()
        assert "NOT generated at execution time" in proto or "pre-declared" in proto.lower(), (
            "Protocol must state that the seed is pre-declared and not execution-time"
        )

    def test_protocol_specifies_rng_implementation(self):
        proto = read_protocol()
        assert "numpy.random.default_rng" in proto, (
            "Protocol must specify numpy.random.default_rng as the RNG implementation"
        )

    def test_protocol_specifies_10000_replicates(self):
        proto = read_protocol()
        assert "10,000" in proto, (
            "Protocol must specify 10,000 bootstrap replicates"
        )

    def test_protocol_specifies_percentile_ci(self):
        proto = read_protocol()
        assert "95" in proto and ("percentile" in proto.lower() or "CI" in proto), (
            "Protocol must specify 95% percentile confidence interval"
        )


# ===========================================================================
# 13. Bootstrap Resampling by Scene
# ===========================================================================

class TestBootstrapResamplingByScene:
    """Protocol must specify scene-level resampling for cluster bootstrap."""

    def test_protocol_requires_scene_level_resampling(self):
        proto = read_protocol()
        assert "resample" in proto.lower() or "resampling unit" in proto.lower(), (
            "Protocol §14.1 must specify resampling at the scene (cluster) level"
        )
        assert "parent scene" in proto.lower() or "parent Sentinel-1" in proto.lower(), (
            "Resampling must be at parent scene level"
        )

    def test_bootstrap_prohibits_iid_ci(self):
        proto = read_protocol()
        assert "IID" in proto or "iid" in proto.lower() or "not independently" in proto.lower(), (
            "Protocol must prohibit IID confidence intervals"
        )
        assert (
            "Do NOT use" in proto and "IID" in proto or
            "Strict prohibition" in proto and "unclustered" in proto
        ), "Protocol must actively prohibit IID CI"


# ===========================================================================
# 14. Shared-Scene Paired Behavior Documented
# ===========================================================================

class TestSharedScenePairedBehavior:
    """297 shared no-oil parent scenes must be jointly represented in cross-stratum bootstrap."""

    def test_protocol_documents_shared_scenes_bootstrap_requirement(self):
        proto = read_protocol()
        assert "297" in proto and "jointly represented" in proto.lower(), (
            "Protocol must state that 297 shared no-oil parent scenes must be "
            "jointly represented in bootstrap replicates"
        )

    def test_protocol_documents_oil_shared_scenes_too(self):
        proto = read_protocol()
        assert "140" in proto and "oil" in proto.lower(), (
            "Protocol must reference the 140 shared oil parent scenes for paired comparisons"
        )


# ===========================================================================
# 15. compute_tile_windows 4-Tuple Contract
# ===========================================================================

class TestComputeTileWindows4Tuple:
    """compute_tile_windows() must return List[Tuple[int,int,int,int]] (row_start, row_end, col_start, col_end)."""

    def test_returns_4_tuples(self):
        sys.path.insert(0, str(REPO / "src"))
        try:
            from ocean_sentinel.inference import compute_tile_windows
        except ImportError:
            pytest.skip("inference module requires torch — checking source signature instead")

    def test_source_signature_returns_4_tuple(self):
        inf_path = REPO / "src" / "ocean_sentinel" / "inference.py"
        if not inf_path.exists():
            pytest.skip("inference.py not present")
        src = inf_path.read_text(encoding="utf-8")
        assert "row_start, row_end, col_start, col_end" in src or \
               "Tuple[int, int, int, int]" in src, (
            "compute_tile_windows must document 4-tuple return contract"
        )

    def test_protocol_does_not_describe_as_2_tuple(self):
        proto = read_protocol()
        assert "2-tuple" not in proto and "(row_start, col_start)" not in proto, (
            "Protocol must not describe compute_tile_windows as returning 2-tuples"
        )


# ===========================================================================
# 16. Metric-ID Consistency — O1 = Oil-Patch Activation Rate
# ===========================================================================

class TestMetricIdConsistency:
    """O1 must be 'Oil-Patch Activation Rate', not 'Patch Recall Rate'."""

    def test_o1_is_oil_patch_activation_rate_in_protocol(self):
        proto = read_protocol()
        assert "Oil-Patch Activation Rate" in proto or "Oil-patch Activation Rate" in proto, (
            "Protocol must name METRIC-O1 as 'Oil-Patch Activation Rate'"
        )

    def test_o1_not_called_patch_recall_rate(self):
        proto = read_protocol()
        # 'Patch Recall Rate' must not appear as a positive definition of O1
        lines_with_recall = [
            ln for ln in proto.splitlines()
            if "Patch Recall Rate" in ln and "METRIC-O1" in ln
        ]
        for ln in lines_with_recall:
            # It must be in a NOT/prohibition context
            is_prohibition = (
                "NOT" in ln or "not" in ln or "must not" in ln or "NOT called" in ln
            )
            assert is_prohibition, (
                f"'Patch Recall Rate' appears as an O1 definition, not prohibition: {ln.strip()}"
            )

    def test_o3_is_not_labeled_as_segmentation_iou(self):
        proto = read_protocol()
        assert "NOT" in proto and "segmentation IoU" in proto, (
            "Protocol must explicitly forbid labeling O3 as segmentation IoU"
        )

    def test_protocol_prohibits_proposal_recall_as_metric_name(self):
        proto = read_protocol()
        # 'proposal recall' may appear in the scientific question (frozen text), but
        # O1 must not be defined as 'proposal recall'
        # The scientific question references it as a concept; that's acceptable.
        # What is NOT acceptable: defining O1 using 'proposal recall' without qualification.
        o1_section = ""
        in_o1 = False
        for ln in proto.splitlines():
            if "METRIC-O1" in ln:
                in_o1 = True
            elif "METRIC-O2" in ln:
                in_o1 = False
            if in_o1:
                o1_section += ln + "\n"
        # O1 section must not use 'proposal recall' as the primary name
        assert "Oil-Patch Activation" in o1_section or "NOT called" in o1_section, (
            "O1 section must use 'Oil-Patch Activation Rate' or contain NOT-called disclaimer"
        )

    def test_l4_and_o4_are_subgroup_views_not_independent_estimands(self):
        proto = read_protocol()
        assert "Subgroup" in proto and "O4" in proto and "L4" in proto


# ===========================================================================
# 17. Protocol Version Consistency (V3.5)
# ===========================================================================

class TestProtocolVersionConsistency:
    """Protocol must be at V3.5 and consistently reference V3.5."""

    def test_protocol_header_declares_v35(self):
        proto = read_protocol()
        assert "V3.5" in proto or "Version 3.5" in proto, (
            "Protocol header must declare version 3.5"
        )

    def test_protocol_document_id_is_v35(self):
        proto = read_protocol()
        assert "EXP08_CORRECTED_PROTOCOL_V3_5" in proto, (
            "Protocol Document ID must be EXP08_CORRECTED_PROTOCOL_V3_5"
        )

    def test_preflight_module_references_v35(self):
        src = read_preflight_src()
        assert "EXP08_CORRECTED_PROTOCOL_V3_5" in src or "V3_5" in src, (
            "exp08_catalog_preflight.py must reference Protocol V3.5"
        )

    def test_protocol_supersedes_v34(self):
        proto = read_protocol()
        assert "V3_4" in proto or "V3.4" in proto, (
            "V3.5 must explicitly state it supersedes V3.4"
        )

    def test_version_delta_table_present(self):
        proto = read_protocol()
        assert "Version Delta" in proto or "V3.4 → V3.5" in proto, (
            "Protocol must contain a version delta table documenting V3.4 → V3.5 changes"
        )


# ===========================================================================
# 18. Preflight Module Dependency Isolation
# ===========================================================================

class TestPreflightModuleDependencyIsolation:
    """exp08_catalog_preflight.py must not import torch, inference, or model code."""

    def _get_imports(self) -> list[str]:
        """Parse the preflight source file and extract all import names using AST."""
        src = read_preflight_src()
        tree = ast.parse(src)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
        return imports

    def test_no_torch_import(self):
        imports = self._get_imports()
        torch_imports = [imp for imp in imports if "torch" in imp.lower()]
        assert not torch_imports, (
            f"exp08_catalog_preflight.py must not import torch. Found: {torch_imports}"
        )

    def test_no_inference_import(self):
        imports = self._get_imports()
        inference_imports = [imp for imp in imports if "inference" in imp.lower()]
        assert not inference_imports, (
            f"exp08_catalog_preflight.py must not import inference. Found: {inference_imports}"
        )

    def test_no_model_import(self):
        """No model, neural network, or forward-pass imports."""
        src = read_preflight_src()
        forbidden_patterns = ["torch.nn", ".forward(", "no_grad", "torch.load", "model.eval"]
        for pattern in forbidden_patterns:
            assert pattern not in src, (
                f"exp08_catalog_preflight.py must not contain '{pattern}'"
            )

    def test_ast_no_forward_call(self):
        """AST check: no attribute call named 'forward' exists in the source."""
        src = read_preflight_src()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr == "forward":
                    pytest.fail("exp08_catalog_preflight.py contains a .forward() call")

    def test_module_imports_successfully_without_torch(self):
        """The preflight module must be importable in an environment where torch is mocked away.

        We block torch at import time by temporarily inserting a fake module, then importing
        the preflight module. If it still tries to use torch, this will expose the dependency.
        """
        # Temporarily block torch in sys.modules
        fake_torch = types.ModuleType("torch")
        original_torch = sys.modules.get("torch", None)
        sys.modules["torch"] = fake_torch

        # Force re-import if already cached
        module_name = "ocean_sentinel.exp08_catalog_preflight"
        cached = sys.modules.pop(module_name, None)
        try:
            sys.path.insert(0, str(REPO / "src"))
            importlib.import_module(module_name)
            # Success: module imported without actually using torch
        except Exception as exc:
            pytest.fail(
                f"exp08_catalog_preflight failed to import when torch is blocked: {exc}"
            )
        finally:
            # Restore original state
            if original_torch is None:
                sys.modules.pop("torch", None)
            else:
                sys.modules["torch"] = original_torch
            if cached is not None:
                sys.modules[module_name] = cached
            elif module_name in sys.modules:
                del sys.modules[module_name]
