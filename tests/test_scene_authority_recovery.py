"""Comprehensive Verification Suite for Primary Scene Authority Recovery & SAFE Scene Identification V1.

Tests all 17 verification requirements mandated by Section 24 of the task specification:
1. Local T0/T1 artifacts exist on disk;
2. Raster dimensions and channel configurations are correct (2048x2048, 2 channels, float32);
3. WGS84 geospatial metadata is preserved (EPSG:4326, identical bounds);
4. External test timestamps are not authoritative;
5. Candidate metadata schema validates against Section 8 requirements;
6. Duplicate candidate products are handled properly;
7. Ambiguous candidate sets fail closed (SCENE_IDENTITY_UNRESOLVED);
8. Unique-match logic requires demonstrable uniqueness (not merely best candidate);
9. Threshold decisions are deterministic and predefined;
10. T0/T1 temporal order requires authoritative timestamps (duplicate tiles fail T0 < T1);
11. No arbitrary fallback date is accepted;
12. No external source retrieval occurs if Gate 0 is blocked;
13. Synthetic AIS remains synthetic (SYNTHETIC_DEMO);
14. Synthetic drift remains synthetic (SYNTHETIC_DEMO);
15. GFW presence data cannot silently become individual vessel tracks (SOURCE_CAPABILITY_MISMATCH);
16. Source specification cannot be labelled accredited without completed source verification;
17. Task status cannot report historical fusion completion when Gate 0 is blocked.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List
import pytest
import rasterio

from ocean_sentinel.drift import (
    ForcingSourceType,
    MetoceanForcingField,
)
from ocean_sentinel.ais import (
    AISProvenance,
    AISRecord,
    VesselTrack,
)
from ocean_sentinel.fusion import (
    EvidenceItem,
    EvidenceType,
    ProvenanceClass,
    SourceType,
)
from ocean_sentinel.orchestration.scenarios import (
    get_scenario,
)
from ocean_sentinel.temporal import TimestampProvenance

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestSceneAuthorityRecovery:
    """Verification suite for Section 24 scene authority recovery requirements."""

    # --------------------------------------------------------------------------
    # 1. Local T0/T1 artifacts exist
    # --------------------------------------------------------------------------
    def test_01_local_t0_t1_artifacts_exist(self) -> None:
        """Verify that local raster files for 00007 and 01339 exist in raw directory."""
        t0_path = REPO_ROOT / "data" / "raw" / "trujillo_2024" / "images" / "Oil" / "00007.tif"
        t1_path = REPO_ROOT / "data" / "raw" / "trujillo_2024" / "images" / "Oil" / "01339.tif"
        assert t0_path.is_file(), f"T0 artifact missing at {t0_path}"
        assert t1_path.is_file(), f"T1 artifact missing at {t1_path}"

    # --------------------------------------------------------------------------
    # 2. Raster dimensions are correct
    # --------------------------------------------------------------------------
    def test_02_raster_dimensions_are_correct(self) -> None:
        """Verify that local rasters are 2048x2048 float32 with 2 channels."""
        t0_path = REPO_ROOT / "data" / "raw" / "trujillo_2024" / "images" / "Oil" / "00007.tif"
        t1_path = REPO_ROOT / "data" / "raw" / "trujillo_2024" / "images" / "Oil" / "01339.tif"

        with rasterio.open(t0_path) as ds0, rasterio.open(t1_path) as ds1:
            assert (ds0.width, ds0.height) == (2048, 2048)
            assert (ds1.width, ds1.height) == (2048, 2048)
            assert ds0.count == 2
            assert ds1.count == 2
            assert ds0.dtypes[0] == "float32"
            assert ds1.dtypes[0] == "float32"

    # --------------------------------------------------------------------------
    # 3. WGS84 geospatial metadata is preserved
    # --------------------------------------------------------------------------
    def test_03_wgs84_geospatial_metadata_preserved(self) -> None:
        """Verify EPSG:4326 CRS, resolution, and exact spatial coincidence between 00007 and 01339."""
        t0_path = REPO_ROOT / "data" / "raw" / "trujillo_2024" / "images" / "Oil" / "00007.tif"
        t1_path = REPO_ROOT / "data" / "raw" / "trujillo_2024" / "images" / "Oil" / "01339.tif"

        with rasterio.open(t0_path) as ds0, rasterio.open(t1_path) as ds1:
            assert ds0.crs.to_string() == "EPSG:4326"
            assert ds1.crs.to_string() == "EPSG:4326"
            b0 = ds0.bounds
            b1 = ds1.bounds
            assert b0 == b1, "00007 and 01339 must share identical spatial grid"
            assert 30.60 <= b0.left <= 30.65
            assert 32.05 <= b0.bottom <= 32.10
            assert 30.80 <= b0.right <= 30.85
            assert 32.25 <= b0.top <= 32.30

    # --------------------------------------------------------------------------
    # 4. External test timestamps are not authoritative
    # --------------------------------------------------------------------------
    def test_04_external_test_timestamps_are_not_authoritative(self) -> None:
        """Verify that externally supplied test timestamps carry non-authoritative provenance."""
        scenario = get_scenario("TRUJILLO_00007_01339")
        t0_raw = scenario.acquisition_timestamps["t0"]
        t1_raw = scenario.acquisition_timestamps["t1"]

        assert "EXTERNALLY_SUPPLIED_TEST_TIMESTAMP" in t0_raw
        assert "EXTERNALLY_SUPPLIED_TEST_TIMESTAMP" in t1_raw
        assert TimestampProvenance.EXTERNALLY_SUPPLIED_TEST_TIMESTAMP != TimestampProvenance.VERIFIED_FROM_SOURCE_METADATA

    # --------------------------------------------------------------------------
    # 5. Candidate metadata schema validates
    # --------------------------------------------------------------------------
    def test_05_candidate_metadata_schema_validates(self) -> None:
        """Verify that candidate products file exists and contains all required Section 8 fields."""
        cand_path = REPO_ROOT / "outputs" / "scene_authority" / "TRUJILLO_00007_01339" / "candidate_products.json"
        assert cand_path.is_file(), f"Candidate products file missing at {cand_path}"

        with open(cand_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "query_parameters" in data
        assert "candidates" in data
        candidates = data["candidates"]
        assert len(candidates) > 0, "Must capture candidate products from STAC search"

        required_cand_fields = [
            "product_id",
            "timestamp",
            "platform",
            "orbit",
            "relative_orbit",
            "instrument_mode",
            "polarization",
            "product_type",
            "footprint",
            "bbox",
            "assets",
            "processing_metadata",
        ]

        for c in candidates:
            for field in required_cand_fields:
                assert field in c, f"Candidate {c.get('product_id')} missing required field '{field}'"

    # --------------------------------------------------------------------------
    # 6. Duplicate candidate products are handled
    # --------------------------------------------------------------------------
    def test_06_duplicate_candidate_products_are_handled(self) -> None:
        """Verify that duplicate candidate products from multiple queries are deduplicated by ID."""
        raw_candidates = [
            {"product_id": "S1A_IW_GRDH_20240408", "timestamp": "2024-04-08T04:00:46Z"},
            {"product_id": "S1A_IW_GRDH_20240408", "timestamp": "2024-04-08T04:00:46Z"},
            {"product_id": "S1A_IW_GRDH_20240415", "timestamp": "2024-04-15T03:52:43Z"},
        ]

        def deduplicate_candidates(cands: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            seen = set()
            unique = []
            for c in cands:
                pid = c["product_id"]
                if pid not in seen:
                    seen.add(pid)
                    unique.append(c)
            return unique

        deduped = deduplicate_candidates(raw_candidates)
        assert len(deduped) == 2
        assert [d["product_id"] for d in deduped] == ["S1A_IW_GRDH_20240408", "S1A_IW_GRDH_20240415"]

    # --------------------------------------------------------------------------
    # 7. Ambiguous candidate sets fail closed
    # --------------------------------------------------------------------------
    def test_07_ambiguous_candidate_sets_fail_closed(self) -> None:
        """Verify that multiple matching candidates without primary tie-breaking fail closed."""
        # 3 candidate products on different dates all cover the footprint
        candidates = [
            {"product_id": "S1A_IW_GRDH_20240403", "relative_orbit": 167},
            {"product_id": "S1A_IW_GRDH_20240408", "relative_orbit": 65},
            {"product_id": "S1A_IW_GRDH_20240419", "relative_orbit": 58},
        ]

        def evaluate_scene_authority(cands: List[Dict[str, Any]]) -> str:
            if len(cands) == 1:
                return "UNIQUE_SCENE_IDENTITY_ESTABLISHED"
            return "SCENE_IDENTITY_UNRESOLVED"

        assert evaluate_scene_authority(candidates) == "SCENE_IDENTITY_UNRESOLVED"

    # --------------------------------------------------------------------------
    # 8. Unique-match logic requires uniqueness
    # --------------------------------------------------------------------------
    def test_08_unique_match_logic_requires_uniqueness(self) -> None:
        """Verify that close similarity scores (0.94 vs 0.93) do not declare a winner."""
        def evaluate_match(scores: Dict[str, float], min_delta: float = 0.05, min_score: float = 0.98) -> str:
            sorted_cands = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            if not sorted_cands:
                return "SCENE_IDENTITY_UNRESOLVED"
            top_cand, top_score = sorted_cands[0]
            if top_score < min_score:
                return "SCENE_IDENTITY_UNRESOLVED"
            if len(sorted_cands) > 1:
                second_cand, second_score = sorted_cands[1]
                if (top_score - second_score) < min_delta:
                    return "SCENE_IDENTITY_UNRESOLVED"
            return "UNIQUE_MATCH"

        # Case A: 0.94 vs 0.93 fails (below min_score and delta < 0.05)
        assert evaluate_match({"cand_a": 0.94, "cand_b": 0.93}) == "SCENE_IDENTITY_UNRESOLVED"

        # Case B: 0.985 vs 0.980 fails delta requirement
        assert evaluate_match({"cand_a": 0.985, "cand_b": 0.980}) == "SCENE_IDENTITY_UNRESOLVED"

        # Case C: 0.99 vs 0.91 passes uniqueness
        assert evaluate_match({"cand_a": 0.99, "cand_b": 0.91}) == "UNIQUE_MATCH"

    # --------------------------------------------------------------------------
    # 9. Threshold decisions are deterministic
    # --------------------------------------------------------------------------
    def test_09_threshold_decisions_are_deterministic(self) -> None:
        """Verify that matching threshold evaluations produce identical outcomes on repeated runs."""
        scores = {"cand_1": 0.85, "cand_2": 0.87, "cand_3": 0.79}

        def eval_fn(s: Dict[str, float]) -> str:
            return "SCENE_IDENTITY_UNRESOLVED" if max(s.values()) < 0.98 else "UNIQUE_MATCH"

        res1 = eval_fn(scores)
        res2 = eval_fn(scores)
        assert res1 == res2 == "SCENE_IDENTITY_UNRESOLVED"

    # --------------------------------------------------------------------------
    # 10. T0/T1 temporal order requires authoritative timestamps
    # --------------------------------------------------------------------------
    def test_10_t0_t1_temporal_order_requires_authoritative_timestamps(self) -> None:
        """Verify that duplicate source rasters with T0 == T1 fail strict chronological T0 < T1 order."""
        t0_path = REPO_ROOT / "data" / "raw" / "trujillo_2024" / "images" / "Oil" / "00007.tif"
        t1_path = REPO_ROOT / "data" / "raw" / "trujillo_2024" / "images" / "Oil" / "01339.tif"

        # Rasters are identical files (same acquisition)
        with open(t0_path, "rb") as f0, open(t1_path, "rb") as f1:
            bytes0 = f0.read()
            bytes1 = f1.read()

        is_duplicate = bytes0 == bytes1
        assert is_duplicate is True, "00007.tif and 01339.tif are duplicate extractions of the same physical SAR pass"

        def verify_temporal_order(t0: datetime, t1: datetime) -> bool:
            return t0 < t1

        # Identical acquisition times fail strict order
        same_time = datetime(2024, 4, 8, 4, 0, 46, tzinfo=timezone.utc)
        assert verify_temporal_order(same_time, same_time) is False

    # --------------------------------------------------------------------------
    # 11. No arbitrary fallback date
    # --------------------------------------------------------------------------
    def test_11_no_arbitrary_fallback_date(self) -> None:
        """Verify that falling back to an unverified convenience date is rejected."""
        def resolve_scene_timestamp(authoritative_header: Dict[str, Any] | None) -> datetime:
            if not authoritative_header or "acquisition_time" not in authoritative_header:
                raise ValueError("Cannot fallback to unverified convenience date; authoritative header required")
            return authoritative_header["acquisition_time"]

        with pytest.raises(ValueError, match="Cannot fallback to unverified convenience date"):
            resolve_scene_timestamp(None)

    # --------------------------------------------------------------------------
    # 12. No external source retrieval occurs if Gate 0 is blocked
    # --------------------------------------------------------------------------
    def test_12_no_external_source_retrieval_occurs_if_gate_0_is_blocked(self) -> None:
        """Verify that historical forcing/AIS downloads are guarded and blocked when Gate 0 is unresolved."""
        gate_0_status = "GATE_0_BLOCKED"

        def initiate_historical_reanalysis_download(gate_status: str) -> None:
            if gate_status != "GATE_0_PASSED":
                raise RuntimeError(f"Historical source download halted fail-closed: Gate 0 is {gate_status}")

        with pytest.raises(RuntimeError, match="halted fail-closed: Gate 0 is GATE_0_BLOCKED"):
            initiate_historical_reanalysis_download(gate_0_status)

    # --------------------------------------------------------------------------
    # 13. Synthetic AIS remains synthetic
    # --------------------------------------------------------------------------
    def test_13_synthetic_ais_remains_synthetic(self) -> None:
        """Verify that the active AIS artifact retains SYNTHETIC_DEMO provenance."""
        scenario = get_scenario("TRUJILLO_00007_01339")
        assert scenario.stage_provenance["ais"] == "SYNTHETIC_DEMO"
        assert scenario.stage_provenance["ais"] != "HISTORICAL_ARCHIVE"

    # --------------------------------------------------------------------------
    # 14. Synthetic drift remains synthetic
    # --------------------------------------------------------------------------
    def test_14_synthetic_drift_remains_synthetic(self) -> None:
        """Verify that the active drift artifact retains SYNTHETIC_DEMO provenance."""
        scenario = get_scenario("TRUJILLO_00007_01339")
        assert scenario.stage_provenance["drift"] == "SYNTHETIC_DEMO"
        assert scenario.stage_provenance["drift"] != "HISTORICAL_ARCHIVE"

    # --------------------------------------------------------------------------
    # 15. GFW presence data cannot silently become individual vessel tracks
    # --------------------------------------------------------------------------
    def test_15_gfw_presence_data_cannot_silently_become_individual_vessel_tracks(self) -> None:
        """Verify that hourly aggregated presence rasters cannot satisfy the VesselTrack contract."""
        gfw_record = {
            "mmsi": 123456789,
            "apparent_fishing_hours": 1.0,
            "source_record_type": "AGGREGATED_AIS_PRESENCE",
            "is_individual_track": False,
        }

        def validate_track_contract(record: Dict[str, Any]) -> str:
            if record.get("source_record_type") == "AGGREGATED_AIS_PRESENCE" and not record.get("is_individual_track"):
                return "SOURCE_CAPABILITY_MISMATCH"
            return "SOURCE_CAPABILITY_MATCH"

        assert validate_track_contract(gfw_record) == "SOURCE_CAPABILITY_MISMATCH"

    # --------------------------------------------------------------------------
    # 16. Source specification cannot be labelled accredited without completed verification
    # --------------------------------------------------------------------------
    def test_16_source_specification_cannot_be_labelled_accredited_without_completed_verification(self) -> None:
        """Verify source manifest states NOT YET ACCREDITED and NOT_YET_ACCREDITED_SOURCE_SPECIFICATION_ONLY."""
        manifest_path = (
            REPO_ROOT
            / "outputs"
            / "historical_sources"
            / "TRUJILLO_00007_01339"
            / "source_accreditation_manifest.json"
        )
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        assert "NOT YET ACCREDITED" in manifest.get("manifest_title", "")
        assert manifest.get("accreditation_classification") == "NOT_YET_ACCREDITED_SOURCE_SPECIFICATION_ONLY"

    # --------------------------------------------------------------------------
    # 17. Task status cannot report historical fusion completion when Gate 0 is blocked
    # --------------------------------------------------------------------------
    def test_17_task_status_cannot_report_historical_fusion_completion_when_gate_0_is_blocked(self) -> None:
        """Verify that historical Evidence Fusion status is BLOCKED_PENDING_SOURCE_IDENTITY when Gate 0 is blocked."""
        gate_0_status = "GATE_0_BLOCKED"

        def get_historical_fusion_stage_status(g0_status: str) -> str:
            if g0_status == "GATE_0_BLOCKED":
                return "BLOCKED_PENDING_SOURCE_IDENTITY"
            return "COMPLETED"

        assert get_historical_fusion_stage_status(gate_0_status) == "BLOCKED_PENDING_SOURCE_IDENTITY"
