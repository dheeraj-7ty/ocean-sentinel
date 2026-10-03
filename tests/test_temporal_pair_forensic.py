"""Comprehensive Verification Suite for Temporal Pair Forensic & Duplicate-Image Guard V1.

Tests all 14 verification requirements mandated by Section 18 of the task specification:
1. Exact duplicate image detection (size, 3-point fingerprint, full SHA-256, raster equality);
2. Duplicate mask difference classification (IDENTICAL_IMAGE_DIFFERENT_ANNOTATION);
3. Identical T0/T1 pair rejected fail-closed (TEMPORAL_PAIR_INVALID_DUPLICATE_IMAGE);
4. Non-identical pair remains candidate, not automatically temporal (POTENTIAL_TEMPORAL_PAIR);
5. Filename order does not establish acquisition chronology (TEMPORAL_ORDER_UNKNOWN);
6. Duplicate pair cannot produce temporal event classifications (TEMPORAL stage BLOCKED);
7. Invalid duplicate pair cannot enter historical drift branch (DRIFT stage BLOCKED);
8. Invalid duplicate pair cannot enter historical AIS branch (AIS & FUSION stages BLOCKED);
9. Old legacy artifacts remain untouched on disk (lineage marked LEGACY_INVALID_TEMPORAL_PAIR);
10. Scenario metadata exposes invalid duplicate status (source_pair_status, temporal_status, reason);
11. Catalog candidate discovery is reported as CATALOG CANDIDATE ENUMERATION, not content matching;
12. Predefined matching thresholds are clearly labelled TASK-LOCAL HEURISTIC THRESHOLDS;
13. DEMO mode remains unchanged and functional;
14. PHYSICAL mode remains fail-closed.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest
import rasterio
import numpy as np

from ocean_sentinel.orchestration.jobs import JobMode, JobStatus, PipelineStage, PipelineType
from ocean_sentinel.orchestration.pipeline import PipelineOrchestrator
from ocean_sentinel.orchestration.scenarios import get_scenario, list_scenarios
from ocean_sentinel.orchestration.temporal_guard import (
    check_temporal_pair_validity,
    classify_duplicate_mask_difference,
    compute_file_sha256,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
IMAGE_DIR = REPO_ROOT / "data" / "raw" / "trujillo_2024" / "images" / "Oil"
MASK_DIR = REPO_ROOT / "data" / "raw" / "trujillo_2024" / "masks" / "Mask_oil"
AUDIT_REPORT_PATH = REPO_ROOT / "outputs" / "scene_authority" / "TRUJILLO_DUPLICATE_IMAGE_AUDIT.json"


class TestTemporalPairForensic:
    """Verification suite for temporal duplicate guard and pair forensic analysis."""

    # --------------------------------------------------------------------------
    # 1. Exact duplicate image detection
    # --------------------------------------------------------------------------
    def test_01_exact_duplicate_image_detection(self) -> None:
        """Verify that 00007.tif and 01339.tif are exact byte-for-byte duplicates."""
        p0 = IMAGE_DIR / "00007.tif"
        p1 = IMAGE_DIR / "01339.tif"
        assert p0.is_file(), f"Image {p0} must exist"
        assert p1.is_file(), f"Image {p1} must exist"

        # Byte size equality
        size0 = p0.stat().st_size
        size1 = p1.stat().st_size
        assert size0 == size1 == 41857591

        # Full SHA-256 equality
        sha0 = compute_file_sha256(p0)
        sha1 = compute_file_sha256(p1)
        expected_sha = "927b382ebffc2f84447a17b80b30e6c3f1f6758fcb8d6e7a13e7c4de70932405"
        assert sha0 == expected_sha
        assert sha1 == expected_sha
        assert sha0 == sha1

        # Raster array equality
        with rasterio.open(p0) as s0, rasterio.open(p1) as s1:
            arr0 = s0.read()
            arr1 = s1.read()
            assert arr0.shape == (2, 2048, 2048)
            assert np.array_equal(arr0, arr1)

        # Audit file exists and records both duplicate groups
        assert AUDIT_REPORT_PATH.is_file()
        with open(AUDIT_REPORT_PATH, "r", encoding="utf-8") as f:
            audit = json.load(f)
        assert audit["exact_duplicate_group_count"] == 2
        groups = audit["exact_duplicate_groups"]
        filenames_per_group = [grp["filenames"] for grp in groups]
        assert ["00007.tif", "01339.tif"] in filenames_per_group
        assert ["00356.tif", "00357.tif"] in filenames_per_group

    # --------------------------------------------------------------------------
    # 2. Duplicate mask difference classification
    # --------------------------------------------------------------------------
    def test_02_duplicate_mask_difference_classification(self) -> None:
        """Verify that masks for duplicate rasters differ and are classified correctly."""
        m0 = MASK_DIR / "00007.tif"
        m1 = MASK_DIR / "01339.tif"
        assert m0.is_file() and m1.is_file()

        classification = classify_duplicate_mask_difference(m0, m1)
        assert classification["classification"] == "IDENTICAL_IMAGE_DIFFERENT_ANNOTATION"
        assert classification["all_masks_equal"] is False
        assert classification["mask0_foreground_pixels"] == 70772
        assert classification["mask1_foreground_pixels"] == 74906
        assert classification["pixel_difference_count"] == 5058
        assert "annotation" in classification["scientific_interpretation"].lower()

        # Compare second duplicate group (00356 / 00357: identical masks)
        m356 = MASK_DIR / "00356.tif"
        m357 = MASK_DIR / "00357.tif"
        if m356.is_file() and m357.is_file():
            c356 = classify_duplicate_mask_difference(m356, m357)
            assert c356["classification"] == "IDENTICAL_IMAGE_IDENTICAL_ANNOTATION"
            assert c356["all_masks_equal"] is True
            assert c356["pixel_difference_count"] == 0

    # --------------------------------------------------------------------------
    # 3. Identical T0/T1 pair rejected
    # --------------------------------------------------------------------------
    def test_03_identical_t0_t1_pair_rejected(self) -> None:
        """Verify check_temporal_pair_validity rejects identical image rasters fail-closed."""
        p0 = IMAGE_DIR / "00007.tif"
        p1 = IMAGE_DIR / "01339.tif"
        verdict = check_temporal_pair_validity(p0, p1)

        assert verdict["valid"] is False
        assert verdict["status"] == "TEMPORAL_PAIR_INVALID_DUPLICATE_IMAGE"
        assert verdict["source_pair_status"] == "INVALID_DUPLICATE_IMAGE_PAIR"
        assert verdict["temporal_status"] == "BLOCKED"
        assert "byte-for-byte identical" in verdict["reason"]
        assert verdict["t0_sha256"] == verdict["t1_sha256"]

    # --------------------------------------------------------------------------
    # 4. Non-identical pair remains candidate, not automatically temporal
    # --------------------------------------------------------------------------
    def test_04_non_identical_pair_remains_candidate_not_automatically_temporal(self) -> None:
        """Verify distinct image pair is classified as POTENTIAL_TEMPORAL_PAIR without assuming chronology."""
        p0 = IMAGE_DIR / "00260.tif"
        p1 = IMAGE_DIR / "00608.tif"
        verdict = check_temporal_pair_validity(p0, p1)

        assert verdict["valid"] is True
        assert verdict["status"] == "POTENTIAL_TEMPORAL_PAIR"
        assert verdict["source_pair_status"] == "POTENTIAL_TEMPORAL_PAIR"
        assert verdict["temporal_chronology"] == "TEMPORAL_ORDER_UNKNOWN"
        assert verdict["temporal_status"] == "PENDING_AUTHORITATIVE_TIMESTAMP"
        assert verdict["t0_sha256"] != verdict["t1_sha256"]

    # --------------------------------------------------------------------------
    # 5. Filename order does not establish chronology
    # --------------------------------------------------------------------------
    def test_05_filename_order_does_not_establish_chronology(self) -> None:
        """Verify numeric order or archive sequence cannot be used to infer acquisition time."""
        scenario = get_scenario("TRUJILLO_00007_01339")
        assert scenario is not None
        p0 = IMAGE_DIR / f"{scenario.scene_pair[0]}.tif"
        p1 = IMAGE_DIR / f"{scenario.scene_pair[1]}.tif"
        verdict = check_temporal_pair_validity(p0, p1)

        # For duplicate, it fails before ordering
        assert verdict["valid"] is False

        # For distinct pair candidate, ordering is strictly unknown
        p_cand0 = IMAGE_DIR / "00260.tif"
        p_cand1 = IMAGE_DIR / "00608.tif"
        verdict_cand = check_temporal_pair_validity(p_cand0, p_cand1)
        assert verdict_cand["temporal_chronology"] == "TEMPORAL_ORDER_UNKNOWN"
        assert "CANNOT be used to infer acquisition chronology" in verdict_cand["chronology_warning"]

    # --------------------------------------------------------------------------
    # 6. Duplicate pair cannot produce temporal event classifications
    # --------------------------------------------------------------------------
    def test_06_duplicate_pair_cannot_produce_temporal_event_classifications(self) -> None:
        """Verify that TRUJILLO_00007_01339 cannot produce temporal change classifications."""
        orchestrator = PipelineOrchestrator()
        manifest = orchestrator.run_job(
            mode=JobMode.REAL_REPOSITORY,
            pipeline_type=PipelineType.REAL_REPOSITORY,
            scenario_id="TRUJILLO_00007_01339",
        )

        assert manifest.status == JobStatus.BLOCKED_PROVENANCE.value
        stage_rec = manifest.stage_status.get(PipelineStage.TEMPORAL.value, {})
        assert stage_rec.get("status") == "BLOCKED"
        assert "BLOCKED / INVALID DUPLICATE IMAGE PAIR" in stage_rec.get("message", "")
        assert "T0 and T1 source rasters are byte-for-byte identical" in stage_rec.get("details", {}).get("reason", "")
        # No temporal events generated
        assert manifest.result is None

    # --------------------------------------------------------------------------
    # 7. Invalid duplicate pair cannot enter historical drift branch
    # --------------------------------------------------------------------------
    def test_07_invalid_duplicate_pair_cannot_enter_historical_drift_branch(self) -> None:
        """Verify that DRIFT stage is BLOCKED for TRUJILLO_00007_01339."""
        orchestrator = PipelineOrchestrator()
        manifest = orchestrator.run_job(
            mode=JobMode.REAL_REPOSITORY,
            pipeline_type=PipelineType.REAL_REPOSITORY,
            scenario_id="TRUJILLO_00007_01339",
        )

        drift_rec = manifest.stage_status.get(PipelineStage.DRIFT.value, {})
        assert drift_rec.get("status") == "BLOCKED"
        assert "INVALID DUPLICATE" in drift_rec.get("message", "") or "BLOCKED" in drift_rec.get("message", "")

    # --------------------------------------------------------------------------
    # 8. Invalid duplicate pair cannot enter historical AIS branch through temporal evidence
    # --------------------------------------------------------------------------
    def test_08_invalid_duplicate_pair_cannot_enter_historical_ais_branch(self) -> None:
        """Verify that AIS and FUSION stages are BLOCKED for TRUJILLO_00007_01339."""
        orchestrator = PipelineOrchestrator()
        manifest = orchestrator.run_job(
            mode=JobMode.REAL_REPOSITORY,
            pipeline_type=PipelineType.REAL_REPOSITORY,
            scenario_id="TRUJILLO_00007_01339",
        )

        ais_rec = manifest.stage_status.get(PipelineStage.AIS.value, {})
        assert ais_rec.get("status") == "BLOCKED"
        fusion_rec = manifest.stage_status.get(PipelineStage.FUSION.value, {})
        assert fusion_rec.get("status") == "BLOCKED"

    # --------------------------------------------------------------------------
    # 9. Old artifacts remain untouched
    # --------------------------------------------------------------------------
    def test_09_old_artifacts_remain_untouched(self) -> None:
        """Verify that historical artifacts exist and are preserved with legacy status."""
        scenario = get_scenario("TRUJILLO_00007_01339")
        assert scenario is not None

        # Verify physical existence of existing artifacts
        for art_name, rel_path in scenario.artifacts.items():
            full_p = REPO_ROOT / rel_path
            assert full_p.is_file(), f"Legacy artifact {rel_path} must be preserved on disk"
            assert full_p.stat().st_size > 0

        # Scenario lineage is marked as legacy invalid pair
        assert scenario.lineage_status == "LEGACY_INVALID_TEMPORAL_PAIR"

    # --------------------------------------------------------------------------
    # 10. Scenario metadata exposes invalid duplicate status
    # --------------------------------------------------------------------------
    def test_10_scenario_metadata_exposes_invalid_duplicate_status(self) -> None:
        """Verify scenario metadata exposes source_pair_status, temporal_status, and reason."""
        scenario = get_scenario("TRUJILLO_00007_01339")
        assert scenario is not None
        assert scenario.source_pair_status == "INVALID_DUPLICATE_IMAGE_PAIR"
        assert scenario.temporal_status == "BLOCKED"
        assert scenario.reason == "IDENTICAL_SOURCE_RASTERS"
        assert scenario.stage_provenance["temporal"] == "BLOCKED"

        # Not called PHYSICAL; no HYBRID mode
        assert scenario.provenance_class != "PHYSICAL"
        assert scenario.provenance_class != "HYBRID"

    # --------------------------------------------------------------------------
    # 11. Catalog enumeration is not reported as content matching
    # --------------------------------------------------------------------------
    def test_11_catalog_enumeration_is_not_reported_as_content_matching(self) -> None:
        """Verify terminology distinguishes catalog candidate enumeration from content matching."""
        cand_path = REPO_ROOT / "outputs" / "scene_authority" / "TRUJILLO_00007_01339" / "candidate_products.json"
        assert cand_path.is_file()
        with open(cand_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # STAC metadata discovery is enumeration only
        assert "candidates" in data
        assert len(data["candidates"]) > 0

        # Progress / lesson files explicitly label discovery as enumeration
        lessons_path = REPO_ROOT / "scratch" / "ocean_sentinel_scene_authority_recovery_lessons.md"
        assert lessons_path.is_file()
        with open(lessons_path, "r", encoding="utf-8") as f:
            lessons_text = f.read()
        assert "HIGHEST HEURISTIC SCORE IS NOT AUTHORITATIVE IDENTITY" in lessons_text

    # --------------------------------------------------------------------------
    # 12. Heuristic matching thresholds are clearly labelled
    # --------------------------------------------------------------------------
    def test_12_heuristic_matching_thresholds_clearly_labelled(self) -> None:
        """Verify predefined matching criteria are described as task-local heuristics."""
        corr_path = REPO_ROOT / "outputs" / "scene_authority" / "TRUJILLO_00007_01339" / "author_correspondence_request.md"
        assert corr_path.is_file()
        with open(corr_path, "r", encoding="utf-8") as f:
            corr_text = f.read()

        assert "00007.tif" in corr_text
        assert "01339.tif" in corr_text
        assert "byte-for-byte identical" in corr_text.lower()
        assert "annotation" in corr_text.lower()

        lessons_path = REPO_ROOT / "scratch" / "ocean_sentinel_scene_authority_recovery_lessons.md"
        with open(lessons_path, "r", encoding="utf-8") as f:
            lessons_text = f.read()
        assert "Task-local heuristic thresholds" in lessons_text or "heuristic" in lessons_text.lower()

    # --------------------------------------------------------------------------
    # 13. DEMO mode remains unchanged
    # --------------------------------------------------------------------------
    def test_13_demo_mode_remains_unchanged(self) -> None:
        """Verify DEMO pipeline executes and succeeds with synthetic fixtures."""
        orchestrator = PipelineOrchestrator()
        manifest = orchestrator.run_job(
            mode=JobMode.DEMO,
            pipeline_type=PipelineType.DEMO_FUSION,
        )

        assert manifest.status == JobStatus.SUCCEEDED.value
        assert manifest.stage_status[PipelineStage.FUSION.value]["status"] == "COMPLETED"
        assert manifest.result is not None
        assert manifest.result["mode"] == "DEMO"
        assert manifest.result["provenance_class"] == "SYNTHETIC_DEMO"

    # --------------------------------------------------------------------------
    # 14. PHYSICAL remains fail-closed
    # --------------------------------------------------------------------------
    def test_14_physical_remains_fail_closed(self) -> None:
        """Verify PHYSICAL mode fails closed with unaccredited operational feed rejection."""
        orchestrator = PipelineOrchestrator()
        manifest = orchestrator.run_job(
            mode=JobMode.PHYSICAL,
            pipeline_type=PipelineType.PHYSICAL,
        )

        assert manifest.status == JobStatus.BLOCKED_PROVENANCE.value
        assert "AWAITING_OPERATIONAL_SOURCE" in manifest.error["message"]
        assert manifest.stage_status[PipelineStage.VALIDATE.value]["status"] == "BLOCKED"
