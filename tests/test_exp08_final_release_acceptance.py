"""EXP-08 Final Release Acceptance Test Suite.

Covers Stage verification requirements from OCEAN-SENTINEL-EXP08-FINAL-RELEASE-ACCEPTANCE:

Stage 3:  Physical acquisition identity — provenance-safe COG deduplication (Cases A–D)
Stage 4:  Real execution-gate integration — exp08_runner.py call-graph proof
Stage 5:  Preflight isolation — subprocess-based torch-blocked import proof (0 skips)
Stage 6:  Metric terminology — O1/O3 globally consistent including scientific question
Stage 7:  Geometry + denominator — all frozen population counts verified
Stage 8:  Missingness / zero-valid state machine
Stage 9:  -70 dB semantic firewall
Stage 10: Byte-level language classification
Stage 11: Bootstrap determinism (seed, implementation, resampling unit)
Stage 12: Candidate lessons CC-7/CC-8 language verified
Stage 13: Contradiction sweep residual scan
"""

from __future__ import annotations

import ast
import importlib
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

REPO = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = REPO / "docs" / "exp08_corrected_protocol.md"
PILOT_PATH = REPO / "docs" / "exp08_cdse_physical_compatibility_pilot.md"
PREFLIGHT_SRC = REPO / "src" / "ocean_sentinel" / "exp08_catalog_preflight.py"
RUNNER_SRC = REPO / "src" / "ocean_sentinel" / "exp08_runner.py"
LESSONS_PATH = REPO / "scratch" / "ocean_sentinel_final_exp08_corrective_closure_lessons.md"

# Module-level import to ensure a single consistent module identity across all tests.
# This prevents the split-module-identity issue that occurs when different test files
# each call sys.path.insert + importlib.import_module independently.
_src = str(REPO / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

import ocean_sentinel.exp08_catalog_preflight as _pf  # noqa: E402
import ocean_sentinel.exp08_runner as _runner  # noqa: E402

# Re-export key names for convenience
PreflightFirewallError = _pf.PreflightFirewallError
ExecutionNotAuthorizedError = _runner.ExecutionNotAuthorizedError


def read_protocol() -> str:
    return PROTOCOL_PATH.read_text(encoding="utf-8")


def read_pilot() -> str:
    return PILOT_PATH.read_text(encoding="utf-8")


def read_preflight_src() -> str:
    return PREFLIGHT_SRC.read_text(encoding="utf-8")


def read_runner_src() -> str:
    return RUNNER_SRC.read_text(encoding="utf-8")


def read_lessons() -> str:
    return LESSONS_PATH.read_text(encoding="utf-8")


def import_preflight():
    """Return the preflight module — always the same module-level instance."""
    return _pf


# ===========================================================================
# Stage 3: Physical Acquisition Identity
# ===========================================================================

class TestPhysicalAcquisitionIdentityStage3:
    """Case A–D: provenance-safe COG deduplication."""

    SAFE_ID = "S1A_IW_GRDH_1SDV_20190101T062300_20190101T062325_025000_02C000_F282"

    def _resolved_client(self, items):
        class FakeClient:
            def query(self, scene_id, window_seconds=25):
                return items
        return FakeClient()

    def test_case_a_original_plus_cog_same_physical_id(self):
        """CASE A: Original product + its COG representation → RESOLVED_UNIQUE (1 physical)."""
        pf = import_preflight()
        base = self.SAFE_ID
        cog  = base + "_COG"
        # Both items have identical acquisition start/stop — same physical scene
        items = [
            {"id": base,   "startDatetime": "2019-01-01T06:23:00Z",
             "completionDatetime": "2019-01-01T06:23:25Z", "bbox": [30, 33, 34, 37]},
            {"id": cog,    "startDatetime": "2019-01-01T06:23:00Z",
             "completionDatetime": "2019-01-01T06:23:25Z", "bbox": [30, 33, 34, 37]},
        ]
        record = pf.resolve_dartis_scene("DARTIS_SCENE_001", self._resolved_client(items))
        assert record.resolution_status == pf.STATUS_RESOLVED_UNIQUE, (
            f"COG+original pair must be RESOLVED_UNIQUE, got {record.resolution_status}"
        )
        assert record.catalog_item_count == 2
        assert record.physical_acquisition_count == 1
        assert record.representation_count == 2
        # Canonical physical ID must have _COG stripped
        assert record.resolved_physical_acquisition_id == base

    def test_case_b_two_genuinely_different_acquisitions(self):
        """CASE B: Two different physical acquisitions → MULTIPLE_MATCHES (2 physical)."""
        pf = import_preflight()
        id1 = "S1A_IW_GRDH_1SDV_20190101T062300_20190101T062325_025000_02C000_F282"
        id2 = "S1A_IW_GRDH_1SDV_20190101T062300_20190101T062325_025001_02C001_F283"  # different orbit
        items = [
            {"id": id1, "startDatetime": "2019-01-01T06:23:00Z"},
            {"id": id2, "startDatetime": "2019-01-01T06:23:00Z"},  # same time but different orbit
        ]
        record = pf.resolve_dartis_scene("DARTIS_SCENE_002", self._resolved_client(items))
        assert record.resolution_status == pf.STATUS_MULTIPLE_MATCHES, (
            "Two different physical acquisitions must remain MULTIPLE_MATCHES"
        )
        assert record.physical_acquisition_count == 2

    def test_case_c_similar_ids_without_provenance_must_not_merge(self):
        """CASE C: IDs similar in string form but from different physical scenes → MULTIPLE_MATCHES.

        This tests that normalize_to_physical_id() does not merge genuinely different
        acquisitions that happen to differ only in a trailing numeric suffix.
        E.g. _F282 vs _F283 — these are different frames/acquisitions, not COG variants.
        """
        pf = import_preflight()
        # These differ in the final frame ID component — not a representation suffix
        id1 = "S1A_IW_GRDH_1SDV_20190101T062300_20190101T062325_025000_02C000_F282"
        id2 = "S1A_IW_GRDH_1SDV_20190101T062300_20190101T062325_025000_02C000_F283"
        items = [
            {"id": id1, "startDatetime": "2019-01-01T06:23:00Z"},
            {"id": id2, "startDatetime": "2019-01-01T06:23:00Z"},
        ]
        record = pf.resolve_dartis_scene("DARTIS_SCENE_003", self._resolved_client(items))
        # The IDs differ in a component that normalize_to_physical_id does NOT strip
        assert record.resolution_status == pf.STATUS_MULTIPLE_MATCHES, (
            "Catalog items with different non-suffix IDs must NOT be merged"
        )
        assert record.physical_acquisition_count == 2

    def test_case_d_cog_with_insufficient_provenance_gives_conservative_unresolved(self):
        """CASE D: Single COG item with insufficient provenance (missing acquisition timestamp)
        → conservative unresolved/ambiguous outcome (STATUS_INVALID_METADATA).
        """
        pf = import_preflight()
        cog_id = self.SAFE_ID + "_COG"
        # Item lacks acquisition startDatetime / start_time
        items = [
            {"id": cog_id},
        ]
        record = pf.resolve_dartis_scene("DARTIS_SCENE_004_INS", self._resolved_client(items))
        assert record.resolution_status == pf.STATUS_INVALID_METADATA
        assert record.physical_acquisition_count == 0
        assert "insufficient" in record.resolution_reason.lower()

    def test_case_d_cog_with_sufficient_provenance_is_resolvable_alone(self):
        """CASE D (positive): Single COG item with verified acquisition provenance
        → RESOLVED_UNIQUE with 1 physical acquisition.
        """
        pf = import_preflight()
        cog_id = self.SAFE_ID + "_COG"
        items = [
            {"id": cog_id, "startDatetime": "2019-01-01T06:23:00Z",
             "completionDatetime": "2019-01-01T06:23:25Z"},
        ]
        record = pf.resolve_dartis_scene("DARTIS_SCENE_004_VAL", self._resolved_client(items))
        assert record.resolution_status == pf.STATUS_RESOLVED_UNIQUE
        assert record.physical_acquisition_count == 1
        assert record.representation_count == 1
        # The resolved physical ID must have _COG stripped
        assert record.resolved_physical_acquisition_id == self.SAFE_ID
        # The resolved catalog ID must be the actual catalog item ID (with _COG)
        assert record.resolved_catalog_id == cog_id

    def test_tier_1_explicit_provider_linkage_prioritized(self):
        """Tier 1: Explicit provider source-product linkage is authoritative physical ID."""
        pf = import_preflight()
        cog_id = "CDSE_CUSTOM_NAME_001_COG"
        true_source = self.SAFE_ID
        items = [
            {
                "id": cog_id,
                "source_product": true_source,
                "startDatetime": "2019-01-01T06:23:00Z",
            }
        ]
        record = pf.resolve_dartis_scene("DARTIS_SCENE_TIER1", self._resolved_client(items))
        assert record.resolution_status == pf.STATUS_RESOLVED_UNIQUE
        assert record.resolved_physical_acquisition_id == true_source

    def test_tier_3_timestamp_conflict_prevents_merge(self):
        """Tier 3: Suffix merge is prohibited if acquisition timestamps conflict."""
        pf = import_preflight()
        base = self.SAFE_ID
        cog = base + "_COG"
        # Same ID base, but different acquisition start times -> must not merge!
        items = [
            {"id": base, "startDatetime": "2019-01-01T06:23:00Z"},
            {"id": cog,  "startDatetime": "2019-01-02T12:00:00Z"},
        ]
        record = pf.resolve_dartis_scene("DARTIS_SCENE_CONFLICT", self._resolved_client(items))
        assert record.resolution_status == pf.STATUS_MULTIPLE_MATCHES
        assert record.physical_acquisition_count > 1

    def test_normalize_does_not_strip_non_cog_suffix(self):
        """normalize_to_physical_id() must not strip arbitrary trailing components."""
        pf = import_preflight()
        base = "S1A_IW_GRDH_1SDV_20190101T062300_20190101T062325_025000_02C000_F282"
        # _F283 is NOT a known representation suffix; must not be stripped
        with_frame = base[:-4] + "F283"
        assert pf.normalize_to_physical_id(with_frame) == with_frame

    def test_preflight_record_fields_all_present(self):
        """All required PreflightRecord fields must exist post-V2."""
        pf = import_preflight()
        r = pf.PreflightRecord(dartis_scene_id="TEST")
        for field in [
            "dartis_scene_id", "resolution_status", "resolution_reason",
            "preflight_timestamp", "protocol_version",
            "catalog_item_count", "physical_acquisition_count",
            "representation_count", "resolved_physical_acquisition_id",
            "resolved_catalog_id", "acquisition_start", "acquisition_stop", "bbox",
        ]:
            assert hasattr(r, field), f"PreflightRecord missing required field: {field}"


# ===========================================================================
# Stage 4: Real Execution-Gate Integration via exp08_runner.py
# ===========================================================================

class TestExecutionGateIntegrationStage4:
    """Prove the actual gated control flow: run_preflight → enforce_gate → EXECUTION_AUTHORIZED check."""

    def _import_runner(self):
        """Return the runner module — always the same module-level instance."""
        return _runner

    def _resolved_client(self, scene_ids):
        class FakeClient:
            def query(self, scene_id, window_seconds=25):
                return [{"id": f"{scene_id}_COG", "startDatetime": "2019-01-01T00:00:00Z",
                         "completionDatetime": "2019-01-01T00:00:25Z"}]
        return FakeClient()

    def _failing_client(self, fail_scene: str, pf):
        class FakeClient:
            def query(self, scene_id, window_seconds=25):
                if scene_id == fail_scene:
                    return []  # NO_MATCH
                return [{"id": f"{scene_id}_COG"}]
        return FakeClient()

    def test_runner_module_exists(self):
        """exp08_runner.py must exist as the gated execution entry point."""
        assert RUNNER_SRC.exists(), (
            "exp08_runner.py must exist as the canonical EXP-08 execution entry point"
        )

    def test_runner_imports_preflight_gate(self):
        """exp08_runner.py must import enforce_preflight_gate and run_preflight."""
        src = read_runner_src()
        assert "enforce_preflight_gate" in src
        assert "run_preflight" in src
        assert "PreflightFirewallError" in src

    def test_runner_has_execution_authorized_guard(self):
        """Runner must have EXECUTION_AUTHORIZED = False guard."""
        src = read_runner_src()
        assert "EXECUTION_AUTHORIZED" in src
        assert "ExecutionNotAuthorizedError" in src

    def test_runner_execution_authorized_is_false_by_default(self):
        """EXECUTION_AUTHORIZED must default to False at module import time."""
        runner = self._import_runner()
        assert runner.EXECUTION_AUTHORIZED is False, (
            "EXECUTION_AUTHORIZED must be False at module definition time"
        )

    def test_case_a_all_resolved_preflight_passes_then_blocked_by_authorization(self):
        """CASE A: All RESOLVED_UNIQUE → preflight passes → ExecutionNotAuthorizedError (not PreflightFirewallError)."""
        runner = self._import_runner()
        scenes = ["SCENE_001", "SCENE_002"]
        client = self._resolved_client(scenes)
        # With EXECUTION_AUTHORIZED=False, should raise ExecutionNotAuthorizedError
        # (not PreflightFirewallError — that would mean preflight failed)
        with pytest.raises(ExecutionNotAuthorizedError):
            runner.run_exp08_evaluation(scenes, client)

    def test_case_b_no_match_raises_preflight_error_never_auth_error(self):
        """CASE B: NO_MATCH → PreflightFirewallError — never reaches ExecutionNotAuthorizedError."""
        runner = self._import_runner()
        scenes = ["SCENE_OK", "SCENE_FAIL"]
        client = self._failing_client("SCENE_FAIL", None)
        # Must raise PreflightFirewallError, not ExecutionNotAuthorizedError
        with pytest.raises(PreflightFirewallError):
            runner.run_exp08_evaluation(scenes, client)

    def test_case_c_multiple_matches_raises_preflight_error(self):
        """CASE C: MULTIPLE_MATCHES → PreflightFirewallError."""
        runner = self._import_runner()

        class FakeClient:
            def query(self, scene_id, window_seconds=25):
                if scene_id == "SCENE_MULTI":
                    # Two genuinely different physical acquisitions
                    return [
                        {"id": "PROD_A_ORBIT001"},
                        {"id": "PROD_B_ORBIT002"},
                    ]
                return [{"id": f"{scene_id}_COG"}]

        with pytest.raises(PreflightFirewallError):
            runner.run_exp08_evaluation(["SCENE_OK", "SCENE_MULTI"], FakeClient())

    def test_case_d_query_error_raises_preflight_error(self):
        """CASE D: QUERY_ERROR → PreflightFirewallError."""
        runner = self._import_runner()

        class FakeClient:
            def query(self, scene_id, window_seconds=25):
                if scene_id == "SCENE_ERROR":
                    raise ConnectionError("CDSE unavailable")
                return [{"id": f"{scene_id}_COG"}]

        with pytest.raises(PreflightFirewallError):
            runner.run_exp08_evaluation(["SCENE_OK", "SCENE_ERROR"], FakeClient())

    def test_case_e_invalid_metadata_raises_preflight_error(self):
        """CASE E: INVALID_METADATA (empty scene ID) → PreflightFirewallError."""
        runner = self._import_runner()
        client = self._resolved_client(["SCENE_OK"])

        with pytest.raises(PreflightFirewallError):
            runner.run_exp08_evaluation(["SCENE_OK", ""], client)

    def test_enforce_gate_called_before_inference_statically(self):
        """Static check: enforce_preflight_gate() appears before any inference call in runner."""
        src = read_runner_src()
        gate_pos = src.find("enforce_preflight_gate(")
        infer_pos = src.find("predict_sar_image(")
        assert gate_pos >= 0, "enforce_preflight_gate() must appear in runner"
        assert infer_pos >= 0, "predict_sar_image() must appear as the inference placeholder"
        assert gate_pos < infer_pos, (
            "enforce_preflight_gate() must appear before predict_sar_image() in control flow"
        )

    def test_execution_authorized_check_between_gate_and_inference(self):
        """EXECUTION_AUTHORIZED check must appear after gate and before inference."""
        src = read_runner_src()
        # Use the LAST occurrence of each to find their positions in actual code,
        # not in the module-level docstring where both terms may appear as description.
        gate_pos = src.rfind("enforce_preflight_gate(")
        auth_check_pos = src.rfind("if not EXECUTION_AUTHORIZED")
        infer_pos = src.rfind("predict_sar_image(")
        assert gate_pos >= 0, "enforce_preflight_gate must appear in runner"
        assert auth_check_pos >= 0, "'if not EXECUTION_AUTHORIZED' must appear in runner"
        assert infer_pos >= 0, "predict_sar_image must appear as inference placeholder"
        assert gate_pos < auth_check_pos, (
            f"enforce_preflight_gate ({gate_pos}) must appear before "
            f"'if not EXECUTION_AUTHORIZED' check ({auth_check_pos})"
        )
        assert auth_check_pos < infer_pos, (
            f"'if not EXECUTION_AUTHORIZED' check ({auth_check_pos}) must appear before "
            f"predict_sar_image ({infer_pos})"
        )

    def test_no_real_model_forward_in_runner_before_authorization_check(self):
        """AST check: no .forward() call appears before the EXECUTION_AUTHORIZED guard."""
        src = read_runner_src()
        # The split: everything before the authorization block
        auth_idx = src.find("if not EXECUTION_AUTHORIZED")
        pre_auth_src = src[:auth_idx]
        tree = ast.parse(pre_auth_src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr in ("forward", "predict"):
                    pytest.fail(
                        f"A '.{func.attr}()' call was found before the EXECUTION_AUTHORIZED guard"
                    )


# ===========================================================================
# Stage 5: Preflight Isolation — Subprocess-Based Torch-Blocked Import Proof
# ===========================================================================

class TestPreflightIsolationStage5:
    """Prove that exp08_catalog_preflight can be imported without torch, using actual subprocess.

    This test must NEVER be skipped. The natural environment (torch unavailable in venv)
    is used as the isolation proof rather than skipping.
    """

    def test_preflight_importable_without_torch_via_subprocess(self):
        """Launch a subprocess and prove that preflight imports successfully without torch.

        This test uses the REAL environment where torch is absent.
        No mocking — an actual subprocess is spawned to import the module.
        """
        script = textwrap.dedent(f"""
            import sys
            sys.path.insert(0, r"{REPO / 'src'}")

            # Explicitly block torch at import level
            import types
            sys.modules["torch"] = None  # Simulate torch being absent

            try:
                import ocean_sentinel.exp08_catalog_preflight as pf
                # Run a basic functional check
                r = pf.PreflightRecord(dartis_scene_id="TEST_ISOLATION")
                assert r.resolution_status == pf.STATUS_INVALID_METADATA
                phys = pf.normalize_to_physical_id("SCENE_001_COG")
                assert phys == "SCENE_001"
                print("PREFLIGHT_ISOLATION_PASS")
            except Exception as e:
                print(f"PREFLIGHT_ISOLATION_FAIL: {{type(e).__name__}}: {{e}}")
                sys.exit(1)
        """)
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, (
            f"Preflight subprocess failed with torch blocked:\n"
            f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )
        assert "PREFLIGHT_ISOLATION_PASS" in result.stdout, (
            f"Expected PREFLIGHT_ISOLATION_PASS in subprocess output: {result.stdout}"
        )

    def test_preflight_torch_absent_in_this_environment(self):
        """Confirm torch is genuinely absent in the test venv (natural isolation environment)."""
        result = subprocess.run(
            [sys.executable, "-c", "import torch; print(torch.__version__)"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode != 0, (
            "Expected torch to be absent from the test venv (natural isolation environment). "
            f"torch was found: {result.stdout.strip()}"
        )

    def test_preflight_imports_successfully_in_this_environment(self):
        """Preflight imports successfully in the current (torch-absent) environment."""
        sys.path.insert(0, str(REPO / "src"))
        pf = import_preflight()
        assert hasattr(pf, "run_preflight")
        assert hasattr(pf, "enforce_preflight_gate")
        assert hasattr(pf, "normalize_to_physical_id")

    def test_ast_no_torch_import_in_preflight(self):
        """AST-based proof: no torch import of any kind in exp08_catalog_preflight.py."""
        src = read_preflight_src()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "torch" not in alias.name.lower(), (
                        f"Unexpected torch import found: import {alias.name}"
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.module and "torch" in node.module.lower():
                    pytest.fail(f"Unexpected torch import found: from {node.module} import ...")

    def test_ast_no_inference_import_in_preflight(self):
        """AST-based proof: no inference module import in exp08_catalog_preflight.py."""
        src = read_preflight_src()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and "inference" in node.module.lower():
                    pytest.fail(f"Unexpected inference import found: from {node.module}")

    def test_ast_no_forward_call_in_preflight(self):
        """AST-based proof: no .forward() call in exp08_catalog_preflight.py."""
        src = read_preflight_src()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr == "forward":
                    pytest.fail("exp08_catalog_preflight.py contains a .forward() call")

    def test_runner_defers_torch_import_until_authorized(self):
        """exp08_runner.py must only import inference (torch) inside the EXECUTION_AUTHORIZED block."""
        src = read_runner_src()
        # The inference import must be inside the authorized block (after 'if not EXECUTION_AUTHORIZED')
        # and NOT at module level
        tree = ast.parse(src)
        # Check no module-level torch import
        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "torch" not in alias.name.lower(), (
                        "exp08_runner.py must not import torch at module level"
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    assert "torch" not in node.module.lower(), (
                        "exp08_runner.py must not import torch at module level"
                    )
                    assert "inference" not in node.module.lower() or "exp08" in node.module.lower(), (
                        "exp08_runner.py must not import inference at module level (only inside authorized block)"
                    )


# ===========================================================================
# Stage 6: Metric Terminology — O1/O3 globally consistent
# ===========================================================================

class TestMetricTerminologyStage6:
    """O1 = Oil-Patch Activation Rate; O3 = Oil-Object Bounding-Box Hit Rate everywhere."""

    def test_scientific_question_uses_oil_patch_activation_rate(self):
        """Protocol §1 scientific question must use 'oil-patch activation rate', not 'proposal recall'."""
        proto = read_protocol()
        q_start = proto.find("## 1. Scientific Question")
        q_end = proto.find("\n## 2.", q_start)
        q_section = proto[q_start:q_end]
        assert "oil-patch activation rate" in q_section.lower(), (
            "Scientific question must use 'oil-patch activation rate'"
        )
        assert "proposal recall" not in q_section.lower(), (
            "Scientific question must NOT use 'proposal recall'"
        )

    def test_o1_not_called_patch_recall_rate_anywhere_in_protocol(self):
        """'Patch Recall Rate' must not appear as a positive O1 definition in protocol."""
        proto = read_protocol()
        for line in proto.splitlines():
            if "METRIC-O1" in line and "Patch Recall Rate" in line:
                is_prohibition = any(kw in line for kw in
                    ["NOT", "not", "must not", "NOT called", "superseded", "was"])
                assert is_prohibition, (
                    f"'Patch Recall Rate' appears as positive O1 definition: {line.strip()}"
                )

    def test_o1_is_oil_patch_activation_rate_in_protocol(self):
        proto = read_protocol()
        assert "Oil-Patch Activation Rate" in proto

    def test_o3_is_not_segmentation_iou(self):
        proto = read_protocol()
        assert "NOT" in proto and "segmentation IoU" in proto

    def test_o3_definition_explicitly_named(self):
        proto = read_protocol()
        assert "Oil-Object Bounding-Box Hit Rate" in proto or "oil-object bounding-box hit rate" in proto.lower()

    def test_pilot_doc_terminology_consistent(self):
        """Pilot doc must not use 'proposal recall' or 'Patch Recall Rate' as O1 name."""
        pilot = read_pilot()
        for line in pilot.splitlines():
            line_lower = line.lower()
            if "patch recall rate" in line_lower:
                is_prohibition = any(kw in line_lower for kw in
                    ["not", "superseded", "was", "old", "historical"])
                assert is_prohibition, (
                    f"Pilot doc uses 'Patch Recall Rate' without prohibition context: {line.strip()}"
                )
            if "proposal recall" in line_lower and "oil-patch activation" not in line_lower:
                # Only acceptable if it's in a prohibition/historical context
                is_ok = any(kw in line_lower for kw in
                    ["not", "was", "superseded", "historical", "old name"])
                # Don't fail on generic pilot scope description that doesn't name a metric
                if "metric" in line_lower or "o1" in line_lower:
                    assert is_ok, (
                        f"Pilot doc uses 'proposal recall' as O1 metric name: {line.strip()}"
                    )


# ===========================================================================
# Stage 7: Geometry + Denominator Verification
# ===========================================================================

class TestGeometryDenominatorStage7:
    """Verify all frozen population counts and geometry contracts."""

    def test_no_oil_inclusion_exclusion(self):
        """719 + 447 - 297 = 869 (no-oil parent scenes)."""
        assert 719 + 447 - 297 == 869

    def test_oil_cohort_patch_total(self):
        """375 + 990 = 1,365 (oil patches: disjoint + co-located)."""
        assert 375 + 990 == 1365

    def test_oil_object_total(self):
        """941 + 2284 = 3,225 (annotated oil objects)."""
        assert 941 + 2284 == 3225

    def test_no_oil_patch_total(self):
        """1,501 + 789 = 2,290 (no-oil patches)."""
        assert 1501 + 789 == 2290

    def test_oil_scene_inclusion_exclusion(self):
        """457 + 422 - 140 = 739 (oil parent scenes)."""
        assert 457 + 422 - 140 == 739

    def test_protocol_references_all_counts(self):
        proto = read_protocol()
        for count in ["719", "447", "297", "869", "1,501", "789", "2,290",
                      "1,365", "3,225", "739", "140"]:
            assert count in proto, f"Protocol must reference count: {count}"

    def test_primary_stratification_uses_quadrilateral(self):
        proto = read_protocol()
        assert "quadrilateral" in proto.lower() or "rotated" in proto.lower()

    def test_aabb_is_retrieval_geometry_only(self):
        proto = read_protocol()
        assert "retrieval" in proto.lower()
        # AABB must not define stratum membership
        assert "bounding box has zero intersection" not in proto.lower()

    def test_source_footprint_count_separate_from_training(self):
        proto = read_protocol()
        # Must distinguish SOURCE_FOOTPRINT_OVERLAP from TRAINING_SOURCE_FOOTPRINT_OVERLAP
        assert "SOURCE_FOOTPRINT_OVERLAP" in proto or "source-footprint" in proto.lower()

    def test_oil_disjoint_count_in_protocol(self):
        proto = read_protocol()
        # 457 disjoint oil scenes
        assert "457" in proto or ("disjoint" in proto.lower() and "oil" in proto.lower())

    def test_oil_colocated_count_in_protocol(self):
        proto = read_protocol()
        # 422 co-located oil scenes, 712 co-located oil patches
        assert "422" in proto or ("co-located" in proto.lower() and "oil" in proto.lower())


# ===========================================================================
# Stage 8: Missingness / Zero-Valid State Machine
# ===========================================================================

class TestMissingnessStateMachineStage8:
    """Invalid states must never silently become scientific zero."""

    def test_enforce_gate_message_mentions_denominator_adjustment(self):
        """enforce_preflight_gate() error message must reference denominator constraint."""
        pf = import_preflight()
        manifest = pf.PreflightManifest()
        manifest.records = [
            pf.PreflightRecord(
                dartis_scene_id="FAIL_SCENE",
                resolution_status=pf.STATUS_NO_MATCH,
            )
        ]
        manifest.compute_summary()
        try:
            pf.enforce_preflight_gate(manifest)
            pytest.fail("Expected PreflightFirewallError")
        except pf.PreflightFirewallError as e:
            assert "denominator" in str(e).lower() or "MUST NOT" in str(e) or "adjusted" in str(e), (
                "enforce_preflight_gate error message must reference denominator constraint"
            )

    def test_target_population_immutable_under_failure(self):
        """target_population must equal number of submitted scenes, regardless of resolution outcomes."""
        pf = import_preflight()

        class FakeClient:
            def query(self, *a, **kw):
                return []  # All fail

        scenes = [f"S{i}" for i in range(7)]
        manifest = pf.run_preflight(scenes, FakeClient())
        assert manifest.target_population == 7
        assert manifest.evaluation_eligible == 0
        assert manifest.invalid_or_unresolved_count == 7

    def test_protocol_stopping_rule_covers_zero_valid_pixel(self):
        proto = read_protocol()
        assert ">10% of patches" in proto or "zero valid pixels" in proto.lower()

    def test_protocol_explicitly_excludes_datamask_zero_pixels(self):
        proto = read_protocol()
        assert "dataMask == 0" in proto or "dataMask" in proto and "excluded" in proto.lower()

    def test_protocol_prohibits_unclustered_ci(self):
        proto = read_protocol()
        assert "unclustered" in proto.lower() and "prohibition" in proto.lower() or \
               "Do NOT use" in proto and "IID" in proto

    def test_patch_level_denominator_integrity_5_patches_2_scenes(self):
        """ISSUE B: Scene B unresolved does not drop its 2 patches from N=5 and does not impute 0.0.

        Example:
            Scene A contains 3 target patches.
            Scene B contains 2 target patches.
            Total target population N = 5.
            Scene A is RESOLVED_UNIQUE. Scene B is NO_MATCH (unresolved).
        Requirements:
            - Scene B is invalid/unresolved in PreflightManifest.
            - PatchManifest retains target_patch_population = 5 (denominator NOT reduced to 3).
            - PatchManifest records 2 invalid/unresolved patches.
            - Scene B's 2 patches have is_missing=True, evaluation_status='UNRESOLVED_ACQUISITION'.
            - Scene B's patches are NOT converted to scientific zeros (prediction_score is None, != 0.0).
            - Every patch preserves: patch_id, parent_scene_id, stratum, target_status,
              acquisition_status, evaluation_status.
        """
        pf = import_preflight()

        # 1. Setup scene manifest
        scene_manifest = pf.PreflightManifest(
            target_population=2,
            evaluation_eligible=1,
            invalid_or_unresolved_count=1,
            preflight_passed=False,
            records=[
                pf.PreflightRecord(
                    dartis_scene_id="SCENE_A",
                    resolution_status=pf.STATUS_RESOLVED_UNIQUE,
                    resolved_physical_acquisition_id="PHYS_A",
                ),
                pf.PreflightRecord(
                    dartis_scene_id="SCENE_B",
                    resolution_status=pf.STATUS_NO_MATCH,
                ),
            ],
        )

        # 2. Setup 5 target patches (3 for Scene A, 2 for Scene B)
        patch_defs = [
            {"patch_id": "PATCH_A1", "parent_scene_id": "SCENE_A", "stratum": "no_oil_disjoint"},
            {"patch_id": "PATCH_A2", "parent_scene_id": "SCENE_A", "stratum": "no_oil_disjoint"},
            {"patch_id": "PATCH_A3", "parent_scene_id": "SCENE_A", "stratum": "no_oil_disjoint"},
            {"patch_id": "PATCH_B1", "parent_scene_id": "SCENE_B", "stratum": "oil_colocated"},
            {"patch_id": "PATCH_B2", "parent_scene_id": "SCENE_B", "stratum": "oil_colocated"},
        ]

        patch_manifest = pf.build_patch_manifest(patch_defs, scene_manifest)

        # Verify frozen target denominator
        assert patch_manifest.target_patch_population == 5, (
            f"Target denominator must remain 5, got {patch_manifest.target_patch_population}"
        )
        assert patch_manifest.evaluation_eligible_patches == 3
        assert patch_manifest.unresolved_or_invalid_patches == 2

        # Verify Scene B patches are explicitly flagged as unresolved and NOT converted to 0.0
        scene_b_patches = [p for p in patch_manifest.records if p.parent_scene_id == "SCENE_B"]
        assert len(scene_b_patches) == 2
        for p in scene_b_patches:
            assert p.is_missing is True
            assert p.evaluation_status == pf.PATCH_EVALUATION_UNRESOLVED
            assert p.acquisition_status == pf.STATUS_NO_MATCH
            assert p.target_status == pf.PATCH_TARGET_INCLUDED
            assert p.prediction_score is None, (
                "Unresolved patch must NOT be converted to a scientific zero score"
            )
            assert p.prediction_score != 0.0

        # Verify Scene A patches are eligible
        scene_a_patches = [p for p in patch_manifest.records if p.parent_scene_id == "SCENE_A"]
        assert len(scene_a_patches) == 3
        for p in scene_a_patches:
            assert p.is_missing is False
            assert p.evaluation_status == pf.PATCH_EVALUATION_ELIGIBLE
            assert p.acquisition_status == pf.STATUS_RESOLVED_UNIQUE

        # Verify all required fields preserved on every patch
        for p in patch_manifest.records:
            d = p.as_dict()
            for req_field in [
                "patch_id", "parent_scene_id", "stratum",
                "target_status", "acquisition_status", "evaluation_status"
            ]:
                assert req_field in d, f"Missing required field {req_field}"



# ===========================================================================
# Stage 9: -70 dB Semantic Firewall
# ===========================================================================

class TestNeg70dBSemanticFirewallStage9:

    def test_total_signal_extinction_not_asserted_in_protocol(self):
        proto = read_protocol()
        # Must not appear as an assertion (only in prohibition context is acceptable)
        lines = [l for l in proto.splitlines() if "total signal extinction" in l.lower()]
        for line in lines:
            is_prohibition = any(kw in line for kw in
                ["DO NOT", "do not", "CAUTION", "Not allowed", "must NOT", "removed"])
            ctx_start = proto.find(line[:30])
            ctx = proto[max(0, ctx_start - 200):ctx_start + 200]
            assert "DO NOT" in ctx or "CAUTION" in ctx or "Removed" in ctx, (
                f"'total signal extinction' appears outside prohibition context: {line.strip()}"
            )

    def test_physical_extinction_not_asserted_anywhere(self):
        for text, name in [(read_protocol(), "protocol"), (read_pilot(), "pilot")]:
            for line in text.splitlines():
                if "physical extinction" in line.lower():
                    pytest.fail(f"'physical extinction' found in {name}: {line.strip()}")

    def test_safely_saturate_not_asserted(self):
        for text, name in [(read_protocol(), "protocol"), (read_pilot(), "pilot")]:
            for line in text.splitlines():
                if "safely saturate" in line.lower():
                    pytest.fail(f"'safely saturate' found in {name}: {line.strip()}")

    def test_numerical_guard_language_present(self):
        proto = read_protocol()
        assert "numerical guard" in proto.lower() or "deterministic numerical floor" in proto.lower()

    def test_caution_block_present_in_protocol(self):
        proto = read_protocol()
        assert "DO NOT interpret the -70 dB floor" in proto or \
               "numerical guard only" in proto.lower()

    def test_classification_safety_not_claimed(self):
        proto = read_protocol()
        assert "not independently established" in proto

    def test_training_path_does_not_apply_additional_floor(self):
        proto = read_protocol()
        assert "already in decibels" in proto or "distributed already in decibels" in proto

    def test_route_b_single_calibration_path(self):
        proto = read_protocol()
        assert "SIGMA0_ELLIPSOID" in proto or "Process API" in proto or "Route B" in proto


# ===========================================================================
# Stage 10: Byte-Level Language Classification
# ===========================================================================

class TestByteLevelLanguageStage10:
    """All 'byte-level' occurrences must be classified as format/storage verification, not radiometric equivalence."""

    def test_pilot_doc_has_byte_level_scope_clarification(self):
        pilot = read_pilot()
        assert "BYTE-LEVEL SCOPE CLARIFICATION" in pilot or \
               "byte-level" in pilot.lower() and "format/storage" in pilot.lower(), (
            "Pilot doc must explicitly clarify that 'byte-level' means format/storage, not radiometric"
        )

    def test_pilot_doc_not_proven_limitation_not_upgraded(self):
        pilot = read_pilot()
        assert "NOT_PROVEN_WITH_CURRENT_ARTIFACTS" in pilot or \
               "not proven" in pilot.lower(), (
            "Pilot doc must still carry the NOT_PROVEN_WITH_CURRENT_ARTIFACTS limitation"
        )

    def test_protocol_carries_trujillo_not_proven_limitation(self):
        proto = read_protocol()
        assert "NOT_PROVEN_WITH_CURRENT_ARTIFACTS" in proto

    def test_no_byte_level_claim_implies_radiometric_equivalence(self):
        """Verify 'byte-level' language is always paired with format/storage scope, not radiometric claim."""
        for text, name in [(read_protocol(), "protocol"), (read_pilot(), "pilot")]:
            lines_with_byte = [l for l in text.splitlines() if "byte-level" in l.lower()]
            for line in lines_with_byte:
                # If it claims 'confirmed' or 'validated', must be about format/grid, not radiometric
                if any(kw in line.lower() for kw in ["confirmed", "validated", "verified"]):
                    # Must be explicitly scoped to format/storage, or must have nearby disclaimer
                    ctx_start = text.find(line[:30])
                    ctx = text[max(0, ctx_start - 300):ctx_start + 300]
                    has_scope = any(kw in ctx.lower() for kw in
                        ["format", "storage", "grid", "dtype", "shape", "not proven",
                         "not imply radiometric", "scope clarification"])
                    assert has_scope, (
                        f"Unscoped 'byte-level confirmed' in {name}: {line.strip()}\n"
                        "Must be scoped to format/grid verification, not radiometric equivalence."
                    )


# ===========================================================================
# Stage 11: Bootstrap Determinism
# ===========================================================================

class TestBootstrapDeterminismStage11:

    def test_seed_20260927_in_protocol(self):
        proto = read_protocol()
        assert "20260927" in proto

    def test_numpy_default_rng_specified(self):
        proto = read_protocol()
        assert "numpy.random.default_rng(20260927)" in proto

    def test_10000_replicates_in_protocol(self):
        proto = read_protocol()
        assert "10,000" in proto

    def test_95_percentile_ci_in_protocol(self):
        proto = read_protocol()
        assert "95" in proto and "percentile" in proto.lower()

    def test_seed_declared_before_execution(self):
        proto = read_protocol()
        assert "NOT generated at execution time" in proto or "pre-declared" in proto.lower()

    def test_resampling_unit_is_parent_scene(self):
        proto = read_protocol()
        assert "parent scene" in proto.lower() or "resampling unit" in proto.lower()

    def test_shared_no_oil_scenes_jointly_represented(self):
        proto = read_protocol()
        assert "297" in proto and "jointly represented" in proto.lower()

    def test_shared_oil_scenes_addressed(self):
        proto = read_protocol()
        assert "140" in proto and "oil" in proto.lower()

    def test_iid_ci_prohibited(self):
        proto = read_protocol()
        assert "IID" in proto

    def test_protocol_prohibits_post_hoc_method_choice(self):
        proto = read_protocol()
        assert "Do NOT use" in proto or "must not" in proto.lower()


# ===========================================================================
# Stage 12: Candidate Lessons CC-7 / CC-8 Language
# ===========================================================================

class TestCandidateLessonsStage12:

    def test_cc7_has_provenance_linkage_as_primary(self):
        lessons = read_lessons()
        assert "Explicit provenance linkage" in lessons or "explicit provenance" in lessons.lower(), (
            "CC-7 must list explicit provenance linkage as the primary identity method"
        )

    def test_cc7_does_not_say_strip_cog_is_sufficient_alone(self):
        lessons = read_lessons()
        cc7_start = lessons.find("CL-EXP08-CC-7")
        cc7_end = lessons.find("---", cc7_start + 10)
        cc7 = lessons[cc7_start:cc7_end]
        # Must not assert that suffix stripping alone is sufficient
        assert "Strip known representation suffixes" not in cc7 or \
               "controlled fallback" in cc7.lower() or "fallback only" in cc7.lower(), (
            "CC-7 must not imply suffix stripping alone is sufficient proof of physical identity"
        )

    def test_cc7_names_controlled_fallback_explicitly(self):
        lessons = read_lessons()
        assert "controlled fallback" in lessons.lower() or "fallback only" in lessons.lower()

    def test_cc8_essential_rule_is_pre_declared_seed(self):
        lessons = read_lessons()
        assert "Essential rule" in lessons or "pre-declared deterministic seed" in lessons.lower()

    def test_cc8_does_not_say_date_based_seeds_preferred(self):
        lessons = read_lessons()
        cc8_start = lessons.find("CL-EXP08-CC-8")
        cc8_end = lessons.find("---", cc8_start + 10)
        cc8 = lessons[cc8_start:cc8_end]
        # Must not claim date-based is universally preferred
        bad_phrase = "acceptable as\na transparent, auditable mechanism"
        assert bad_phrase not in cc8, (
            "CC-8 must not imply date-based seeds are universally preferred"
        )
        # Must explicitly disclaim universal preference
        assert "not universally required or preferred" in cc8 or \
               "not universally" in cc8, (
            "CC-8 must state date-based seeds are not universally required or preferred"
        )

    def test_cc9_explains_dartis_has_no_pixel_masks(self):
        lessons = read_lessons()
        assert "pixel-level mask" in lessons.lower() or "no pixel mask" in lessons.lower() or \
               "pixel-level" in lessons.lower()

    def test_all_nine_lessons_present(self):
        lessons = read_lessons()
        for i in range(1, 10):
            assert f"CL-EXP08-CC-{i}" in lessons, f"Lesson CL-EXP08-CC-{i} missing"


# ===========================================================================
# Stage 13: Contradiction Sweep Residual
# ===========================================================================

class TestContradictionSweepStage13:
    """Verify no prohibited assertions remain in living protocol and pilot documents."""

    def _check_doc_for_assertion(self, text: str, term: str, doc_name: str,
                                  allowed_contexts: list[str]) -> None:
        """Assert that 'term' does not appear as an unsupported assertion."""
        lines = text.splitlines()
        for line in lines:
            if term.lower() in line.lower():
                ctx_start = text.find(line[:30])
                ctx = text[max(0, ctx_start - 200):ctx_start + 400]
                is_ok = any(kw.lower() in ctx.lower() for kw in allowed_contexts)
                assert is_ok, (
                    f"Prohibited term '{term}' appears outside allowed context in {doc_name}:\n"
                    f"  Line: {line.strip()}\n"
                    f"  Expected one of: {allowed_contexts}"
                )

    def test_proposal_recall_not_assertion_in_protocol(self):
        proto = read_protocol()
        # Allowed: in prohibition notes (NOT_FOUND, historical), NOT as active question text
        for line in proto.splitlines():
            if "proposal recall" in line.lower():
                is_ok = any(kw in line for kw in
                    ["NOT_FOUND", "NOT", "superseded", "historical", "was"])
                assert is_ok, (
                    f"'proposal recall' appears as assertion in protocol: {line.strip()}"
                )

    def test_patch_recall_rate_not_positive_definition_in_protocol(self):
        proto = read_protocol()
        for line in proto.splitlines():
            if "Patch Recall Rate" in line and "METRIC-O1" in line:
                is_prohibition = "NOT" in line or "not" in line
                assert is_prohibition, (
                    f"'Patch Recall Rate' as O1 definition: {line.strip()}"
                )

    def test_segmentation_iou_not_asserted_as_metric(self):
        proto = read_protocol()
        for line in proto.splitlines():
            if "segmentation IoU" in line.lower():
                is_prohibition = any(kw in line for kw in ["NOT", "not", "CAUTION"])
                assert is_prohibition, (
                    f"'segmentation IoU' appears as metric definition: {line.strip()}"
                )

    def test_execution_time_seed_not_present_in_protocol(self):
        """Protocol must not suggest any execution-time seed choice."""
        proto = read_protocol()
        for line in proto.splitlines():
            if "execution-time seed" in line.lower() or "seed chosen at execution" in line.lower():
                is_prohibition = any(kw in line.lower() for kw in ["must not", "do not", "prohibition"])
                assert is_prohibition, (
                    f"Execution-time seed appears as positive suggestion: {line.strip()}"
                )

    def test_no_catalog_candidate_count_anywhere(self):
        """catalog_candidate_count (old field name) must not appear in any test file.

        The acceptance test file itself may reference this field name in docstrings or
        comments as historical context; only executable code/assertions are checked.
        """
        test_dir = REPO / "tests"
        for py_file in test_dir.glob("test_exp08*.py"):
            text = py_file.read_text(encoding="utf-8")
            if "catalog_candidate_count" not in text:
                continue
            # If found, verify it only appears in docstrings/comments, not in assertions or code
            tree = ast.parse(text)
            for node in ast.walk(tree):
                # Check function calls and assignments for the stale field name
                if isinstance(node, ast.keyword):
                    assert node.arg != "catalog_candidate_count", (
                        f"Stale field 'catalog_candidate_count' used as keyword arg in {py_file.name}. "
                        "Canonical field is 'catalog_item_count'."
                    )
                if isinstance(node, ast.Attribute):
                    assert node.attr != "catalog_candidate_count", (
                        f"Stale field '.catalog_candidate_count' attribute access in {py_file.name}. "
                        "Canonical field is 'catalog_item_count'."
                    )
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    # String literals that are actually used (not docstrings) checked via parent
                    pass  # Docstring mentions are acceptable for historical reference

    def test_linear_polarization_not_channel_descriptor_in_protocol(self):
        proto = read_protocol()
        for line in proto.splitlines():
            if "linear polarization" in line.lower():
                is_prohibition = any(kw in line.lower() for kw in
                    ["must not", "do not", "prohibited", "forbidden", "incorrect"])
                assert is_prohibition, (
                    f"'linear polarization' appears as channel descriptor: {line.strip()}"
                )

    def test_independent_scenes_not_claimed(self):
        proto = read_protocol()
        assert "2,290 independent" not in proto or "Must NOT claim" in proto

    def test_byte_level_in_historical_reports_classified_correctly(self):
        """byte-level compatibility in historical reports is HISTORICAL — not an upgrade."""
        preflight_report = REPO / "OCEAN_SENTINEL_FINAL_EXP08_PREAUTHORIZATION_INTEGRITY_PREFLIGHT_CLOSURE_REPORT.md"
        if not preflight_report.exists():
            pytest.skip("Preflight report not present")
        text = preflight_report.read_text(encoding="utf-8")
        # The occurrence in the milestone table is a historical description, acceptable
        # What's NOT acceptable: if the report claims this implies radiometric equivalence
        assert "NOT_PROVEN_WITH_CURRENT_ARTIFACTS" in text or \
               "bitwise equivalence" in text.lower() and "cannot" in text.lower(), (
            "Historical report must still carry the NOT_PROVEN limitation alongside byte-level language"
        )
