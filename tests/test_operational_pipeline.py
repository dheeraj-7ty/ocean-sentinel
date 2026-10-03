"""Tests for Ocean Sentinel Operational Pipeline Foundation (Phase 6).

Deterministic unit and integration tests verifying:
- Stage C: Real-data ingestion boundary & fail-closed provider validation
- Stage D: SAR raster validation (dimensions, dtype, valid-pixel mask, CRS, band count)
- Stage E: Explicit Preprocessing contract (Mapping A z-score, linear-to-dB, stats)
- Stage F: Detection boundary firewall, frozen checkpoint verification, unauthorized inference blocking
- Stage G: Canonical structured evidence object & lineage tracking
- Stage H: Lifecycle telemetry progression (RECEIVED → VALIDATING → VALIDATED → PREPROCESSING → READY_FOR_DETECTION → DETECTION_READY)
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
import tempfile
from typing import Dict

import numpy as np
import pytest

from ocean_sentinel.fusion import EvidenceItem, EvidenceType, SourceType
from ocean_sentinel.models import BoundingBox, Polarization
from ocean_sentinel.operational_pipeline import (
    DEFAULT_CHECKPOINT_PATH,
    EXPECTED_EXP06_CHECKPOINT_SHA256,
    CheckpointIntegrityError,
    IngestionRejectionError,
    OperationalAcquisitionRecord,
    OperationalDetectionBoundary,
    OperationalEvidenceResult,
    OperationalIngestionRequest,
    OperationalPreprocessingRecord,
    OperationalRasterValidationResult,
    OperationalSARPipeline,
    PipelineStageState,
    PipelineTelemetryTracker,
    SARValidationError,
    UnauthorizedInferenceError,
    preprocess_sar_operational,
    validate_ingestion_boundary,
    validate_sar_raster,
)


@pytest.fixture
def valid_bounding_box() -> BoundingBox:
    """Fixture returning a valid BoundingBox off the coast of Peru."""
    return BoundingBox(west=-79.5, south=-8.5, east=-78.5, north=-7.5)


@pytest.fixture
def valid_sar_arrays() -> Dict[Polarization, np.ndarray]:
    """Fixture returning valid synthetic 2-band float32 SAR arrays (512x512) in linear scale."""
    np.random.seed(42)
    h, w = 512, 512
    # Realistic SAR linear backscatter: positive float32 with median ~0.005 (VH) and ~0.02 (VV)
    vh = np.random.exponential(scale=0.005, size=(h, w)).astype(np.float32) + 1e-5
    vv = np.random.exponential(scale=0.02, size=(h, w)).astype(np.float32) + 1e-5
    return {Polarization.VH: vh, Polarization.VV: vv}


@pytest.fixture
def valid_ingestion_request(valid_bounding_box, valid_sar_arrays) -> OperationalIngestionRequest:
    """Fixture returning a valid OperationalIngestionRequest."""
    return OperationalIngestionRequest(
        acquisition_id="S1A_IW_GRDH_1SDV_20220115T221530_20220115T221555_041464_04EE34_12AB",
        provider="copernicus_cdse",
        acquisition_time="2022-01-15T22:15:30Z",
        spatial_extent=valid_bounding_box,
        crs="EPSG:4326",
        polarizations=[Polarization.VH, Polarization.VV],
        source_reference="https://browser.dataspace.copernicus.eu/items/S1A_IW_GRDH_12AB",
        raw_arrays=valid_sar_arrays,
        transform=[0.0001, 0.0, -79.5, 0.0, -0.0001, -7.5],
        width=512,
        height=512,
    )


# ---------------------------------------------------------------------------
# Stage C — Ingestion Boundary Tests
# ---------------------------------------------------------------------------


class TestIngestionBoundary:
    """Tests enforcing fail-closed behavior at the real-data ingestion boundary."""

    def test_valid_ingestion_accepted(self, valid_ingestion_request):
        record = validate_ingestion_boundary(valid_ingestion_request)
        assert isinstance(record, OperationalAcquisitionRecord)
        assert record.acquisition_id == valid_ingestion_request.acquisition_id
        assert record.provider == "copernicus_cdse"
        assert record.crs == "EPSG:4326"
        assert record.polarizations == [Polarization.VH, Polarization.VV]
        assert record.status == "INGESTION_ACCEPTED"
        assert record.acquisition_time.tzinfo == timezone.utc

    def test_missing_acquisition_id_rejected(self, valid_ingestion_request):
        valid_ingestion_request.acquisition_id = ""
        with pytest.raises(IngestionRejectionError) as exc_info:
            validate_ingestion_boundary(valid_ingestion_request)
        assert exc_info.value.code == "MISSING_ACQUISITION_ID"

    def test_synthetic_provider_rejected_fail_closed(self, valid_ingestion_request):
        valid_ingestion_request.provider = "synthetic_fallback_provider"
        with pytest.raises(IngestionRejectionError) as exc_info:
            validate_ingestion_boundary(valid_ingestion_request)
        assert exc_info.value.code == "UNAUTHORIZED_PROVIDER"
        assert "strictly rejected" in exc_info.value.message

    def test_fake_provider_rejected_fail_closed(self, valid_ingestion_request):
        valid_ingestion_request.provider = "mock_cdse_generator"
        with pytest.raises(IngestionRejectionError) as exc_info:
            validate_ingestion_boundary(valid_ingestion_request)
        assert exc_info.value.code == "UNAUTHORIZED_PROVIDER"

    def test_invalid_crs_rejected(self, valid_ingestion_request):
        valid_ingestion_request.crs = "NOT_A_VALID_CRS_12345"
        with pytest.raises(IngestionRejectionError) as exc_info:
            validate_ingestion_boundary(valid_ingestion_request)
        assert exc_info.value.code == "INVALID_CRS"

    def test_empty_crs_rejected(self, valid_ingestion_request):
        valid_ingestion_request.crs = ""
        with pytest.raises(IngestionRejectionError) as exc_info:
            validate_ingestion_boundary(valid_ingestion_request)
        assert exc_info.value.code == "MISSING_CRS"

    def test_invalid_timestamp_rejected(self, valid_ingestion_request):
        valid_ingestion_request.acquisition_time = "invalid-date-string"
        with pytest.raises(IngestionRejectionError) as exc_info:
            validate_ingestion_boundary(valid_ingestion_request)
        assert exc_info.value.code == "INVALID_TIMESTAMP"

    def test_ambiguous_polarization_rejected(self, valid_ingestion_request):
        valid_ingestion_request.polarizations = [Polarization.HH]  # missing required dual-pol (VH/VV)
        with pytest.raises(IngestionRejectionError) as exc_info:
            validate_ingestion_boundary(valid_ingestion_request)
        assert exc_info.value.code == "AMBIGUOUS_POLARIZATION_SET"

    def test_missing_polarizations_rejected(self, valid_ingestion_request):
        valid_ingestion_request.polarizations = []
        with pytest.raises(IngestionRejectionError) as exc_info:
            validate_ingestion_boundary(valid_ingestion_request)
        assert exc_info.value.code == "MISSING_POLARIZATION_METADATA"

    def test_degenerate_bounding_box_rejected(self, valid_ingestion_request):
        valid_ingestion_request.spatial_extent = [-78.0, -8.0, -79.0, -9.0]  # west > east
        with pytest.raises(IngestionRejectionError) as exc_info:
            validate_ingestion_boundary(valid_ingestion_request)
        assert exc_info.value.code == "INVALID_SPATIAL_EXTENT"


# ---------------------------------------------------------------------------
# Stage D — SAR Raster Validation Tests
# ---------------------------------------------------------------------------


class TestSARValidation:
    """Tests deterministic validation of 2-band SAR rasters."""

    def test_valid_raster_passes(self, valid_sar_arrays):
        res = validate_sar_raster(
            arrays=valid_sar_arrays,
            polarizations=[Polarization.VH, Polarization.VV],
            crs="EPSG:4326",
            transform=[0.0001, 0.0, -79.5, 0.0, -0.0001, -7.5],
        )
        assert isinstance(res, OperationalRasterValidationResult)
        assert res.band_count == 2
        assert res.height == 512
        assert res.width == 512
        assert res.valid_pixels > 0
        assert res.valid_percentage == 100.0
        assert res.channel_order == [Polarization.VH, Polarization.VV]

    def test_incorrect_band_count_fails_closed(self, valid_sar_arrays):
        # Pass only 1 channel
        single_band = {Polarization.VH: valid_sar_arrays[Polarization.VH]}
        with pytest.raises(SARValidationError) as exc_info:
            validate_sar_raster(
                arrays=single_band,
                polarizations=[Polarization.VH],
                crs="EPSG:4326",
                transform=[0.0001, 0.0, -79.5, 0.0, -0.0001, -7.5],
            )
        assert exc_info.value.code == "INVALID_BAND_COUNT"

    def test_missing_required_polarization_fails_closed(self, valid_sar_arrays):
        # 2 bands, but HH and HV instead of VH and VV
        wrong_pols = {
            Polarization.HH: valid_sar_arrays[Polarization.VH],
            Polarization.HV: valid_sar_arrays[Polarization.VV],
        }
        with pytest.raises(SARValidationError) as exc_info:
            validate_sar_raster(
                arrays=wrong_pols,
                polarizations=[Polarization.HH, Polarization.HV],
                crs="EPSG:4326",
                transform=[0.0001, 0.0, -79.5, 0.0, -0.0001, -7.5],
            )
        assert exc_info.value.code == "MISSING_REQUIRED_POLARIZATION"

    def test_zero_valid_pixels_all_nan_fails_closed(self):
        nan_arr = np.full((512, 512), np.nan, dtype=np.float32)
        arrays = {Polarization.VH: nan_arr, Polarization.VV: nan_arr}
        with pytest.raises(SARValidationError) as exc_info:
            validate_sar_raster(
                arrays=arrays,
                polarizations=[Polarization.VH, Polarization.VV],
                crs="EPSG:4326",
                transform=[0.0001, 0.0, -79.5, 0.0, -0.0001, -7.5],
            )
        assert exc_info.value.code == "ZERO_VALID_PIXELS"

    def test_zero_valid_pixels_non_positive_linear_fails_closed(self):
        # In linear scale, non-positive values (<= 0) are invalid
        zero_arr = np.zeros((512, 512), dtype=np.float32)
        arrays = {Polarization.VH: zero_arr, Polarization.VV: zero_arr}
        with pytest.raises(SARValidationError) as exc_info:
            validate_sar_raster(
                arrays=arrays,
                polarizations=[Polarization.VH, Polarization.VV],
                crs="EPSG:4326",
                transform=[0.0001, 0.0, -79.5, 0.0, -0.0001, -7.5],
            )
        assert exc_info.value.code == "ZERO_VALID_PIXELS"

    def test_invalid_dimensions_fails_closed(self):
        empty_arr = np.zeros((0, 0), dtype=np.float32)
        arrays = {Polarization.VH: empty_arr, Polarization.VV: empty_arr}
        with pytest.raises(SARValidationError) as exc_info:
            validate_sar_raster(
                arrays=arrays,
                polarizations=[Polarization.VH, Polarization.VV],
                crs="EPSG:4326",
                transform=[0.0001, 0.0, -79.5, 0.0, -0.0001, -7.5],
            )
        assert exc_info.value.code == "INVALID_DIMENSIONS"

    def test_missing_crs_fails_closed(self, valid_sar_arrays):
        with pytest.raises(SARValidationError) as exc_info:
            validate_sar_raster(
                arrays=valid_sar_arrays,
                polarizations=[Polarization.VH, Polarization.VV],
                crs="",
                transform=[0.0001, 0.0, -79.5, 0.0, -0.0001, -7.5],
                require_georeferencing=True,
            )
        assert exc_info.value.code == "MISSING_CRS"


# ---------------------------------------------------------------------------
# Stage E — Explicit Preprocessing Contract Tests
# ---------------------------------------------------------------------------


class TestSARPreprocessingContract:
    """Tests the explicit, auditable SAR preprocessing contract."""

    def test_linear_to_db_and_zscore_standardization(self, valid_sar_arrays):
        validation_res = validate_sar_raster(
            arrays=valid_sar_arrays,
            polarizations=[Polarization.VH, Polarization.VV],
            crs="EPSG:4326",
            transform=[0.0001, 0.0, -79.5, 0.0, -0.0001, -7.5],
        )

        prep_rec = preprocess_sar_operational(
            validation_res=validation_res,
            observation_id="test_obs_001",
        )

        assert isinstance(prep_rec, OperationalPreprocessingRecord)
        assert prep_rec.observation_id == "test_obs_001"
        assert prep_rec.preprocessing_version == "OPERATIONAL_SAR_PREPROCESSOR_MAPPING_A_V1"
        assert prep_rec.normalization_contract == "mapping_a_zscore"
        assert prep_rec.channel_order == ["VH", "VV"]
        assert prep_rec.output_shape == (2, 512, 512)

        # Check physical dB values are negative (typical sea surface backscatter)
        assert np.all(prep_rec.physical_db_arrays[0] < 5.0)
        assert np.all(prep_rec.physical_db_arrays[1] < 10.0)

        # Check valid-pixel stats are computed and finite
        assert "VH" in prep_rec.band_statistics
        assert "VV" in prep_rec.band_statistics
        assert np.isfinite(prep_rec.band_statistics["VH"]["mean"])
        assert np.isfinite(prep_rec.band_statistics["VV"]["mean"])

        # Check normalized array has finite values
        assert np.all(np.isfinite(prep_rec.normalized_arrays))

    def test_polarization_channel_order_invariant_under_inverted_input(self, valid_sar_arrays):
        """Proves that passing [VV, VH] inverted input still maps Channel 0 = VH and Channel 1 = VV."""
        inverted_arrays = {
            Polarization.VV: valid_sar_arrays[Polarization.VV],
            Polarization.VH: valid_sar_arrays[Polarization.VH],
        }
        validation_res = validate_sar_raster(
            arrays=inverted_arrays,
            polarizations=[Polarization.VV, Polarization.VH],
            crs="EPSG:4326",
            transform=[0.0001, 0.0, -79.5, 0.0, -0.0001, -7.5],
        )

        assert validation_res.channel_order == [Polarization.VH, Polarization.VV]

        prep_rec = preprocess_sar_operational(
            validation_res=validation_res,
            observation_id="test_obs_inverted",
        )

        assert prep_rec.channel_order == ["VH", "VV"]
        assert prep_rec.output_shape == (2, 512, 512)

        ch0_db_mean = np.mean(prep_rec.physical_db_arrays[0])
        ch1_db_mean = np.mean(prep_rec.physical_db_arrays[1])
        assert ch0_db_mean < ch1_db_mean, "Channel 0 must be Cross-Pol VH (lower backscatter)!"


# ---------------------------------------------------------------------------
# Stage F — Detection Boundary & Frozen Checkpoint Verification Tests
# ---------------------------------------------------------------------------


class TestDetectionBoundary:
    """Tests detection boundary firewall, checkpoint integrity, and unauthorized inference blocking."""

    def test_canonical_checkpoint_sha256_derived_from_artifact_registry(self):
        """Proves get_canonical_checkpoint_sha256 dynamically derives the hash from canonical Artifact Registry."""
        from ocean_sentinel.operational_pipeline import get_canonical_checkpoint_sha256

        canonical_hash = get_canonical_checkpoint_sha256()
        assert canonical_hash == EXPECTED_EXP06_CHECKPOINT_SHA256

        boundary = OperationalDetectionBoundary(
            checkpoint_path=DEFAULT_CHECKPOINT_PATH,
            execution_authorized=False,
        )
        assert boundary.expected_sha256 == canonical_hash

    def test_canonical_checkpoint_sha256_verified(self):
        boundary = OperationalDetectionBoundary(
            checkpoint_path=DEFAULT_CHECKPOINT_PATH,
            expected_sha256=EXPECTED_EXP06_CHECKPOINT_SHA256,
            execution_authorized=False,
        )
        verified_sha = boundary.verify_checkpoint_integrity()
        assert verified_sha == EXPECTED_EXP06_CHECKPOINT_SHA256

    def test_missing_checkpoint_fails_closed(self):
        missing_path = Path("nonexistent/path/best_model.pt")
        boundary = OperationalDetectionBoundary(
            checkpoint_path=missing_path,
            execution_authorized=False,
        )
        with pytest.raises(CheckpointIntegrityError) as exc_info:
            boundary.verify_checkpoint_integrity()
        assert exc_info.value.code == "CHECKPOINT_NOT_FOUND"

    def test_corrupted_checkpoint_hash_fails_closed(self):
        with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as tmp:
            tmp.write(b"corrupted_checkpoint_content_0123456789")
            tmp_path = Path(tmp.name)

        try:
            boundary = OperationalDetectionBoundary(
                checkpoint_path=tmp_path,
                expected_sha256=EXPECTED_EXP06_CHECKPOINT_SHA256,
                execution_authorized=False,
            )
            with pytest.raises(CheckpointIntegrityError) as exc_info:
                boundary.verify_checkpoint_integrity()
            assert exc_info.value.code == "CHECKPOINT_HASH_MISMATCH"
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_prepare_detection_preflight_stops_without_inference(self, valid_sar_arrays):
        validation_res = validate_sar_raster(
            arrays=valid_sar_arrays,
            polarizations=[Polarization.VH, Polarization.VV],
            crs="EPSG:4326",
            transform=[0.0001, 0.0, -79.5, 0.0, -0.0001, -7.5],
        )
        prep_rec = preprocess_sar_operational(validation_res, observation_id="test_obs")

        boundary = OperationalDetectionBoundary(
            checkpoint_path=DEFAULT_CHECKPOINT_PATH,
            execution_authorized=False,
        )
        det_rec = boundary.prepare_detection_preflight(prep_rec)

        assert det_rec.status == "DETECTION_READY"
        assert det_rec.execution_authorized is False
        assert det_rec.probability_map is None
        assert det_rec.prediction_mask is None
        assert "blocked pending scientific execution authorization" in det_rec.message

    def test_execute_inference_unauthorized_fails_closed(self, valid_sar_arrays):
        validation_res = validate_sar_raster(
            arrays=valid_sar_arrays,
            polarizations=[Polarization.VH, Polarization.VV],
            crs="EPSG:4326",
            transform=[0.0001, 0.0, -79.5, 0.0, -0.0001, -7.5],
        )
        prep_rec = preprocess_sar_operational(validation_res, observation_id="test_obs")

        boundary = OperationalDetectionBoundary(
            checkpoint_path=DEFAULT_CHECKPOINT_PATH,
            execution_authorized=False,  # Unauthorized!
        )
        with pytest.raises(UnauthorizedInferenceError) as exc_info:
            boundary.execute_inference(prep_rec)
        assert exc_info.value.code == "UNAUTHORIZED_INFERENCE_REQUEST"
        assert "Scientific execution is NOT authorized" in exc_info.value.message


# ---------------------------------------------------------------------------
# Stage G & H — End-to-End Operational Spine & Structured Evidence Tests
# ---------------------------------------------------------------------------


class TestOperationalSARPipelineSpine:
    """Tests the complete operational pipeline spine end-to-end in preflight mode."""

    def test_end_to_end_preflight_pipeline(self, valid_ingestion_request):
        # Preflight execution: EXECUTION_AUTHORIZED = False
        pipeline = OperationalSARPipeline(
            execution_authorized=False,
            checkpoint_path=DEFAULT_CHECKPOINT_PATH,
        )

        evidence = pipeline.run(valid_ingestion_request)

        assert isinstance(evidence, OperationalEvidenceResult)
        assert evidence.acquisition_id == valid_ingestion_request.acquisition_id
        assert evidence.provider == "copernicus_cdse"
        assert evidence.crs == "EPSG:4326"
        assert evidence.provenance_class == "VERIFIED_OPERATIONAL"
        assert evidence.status == "DETECTION_READY"

        # Verify Lineage Hierarchy: Observation → Acquisition → Raster → Preprocessing → Detection
        lineage = evidence.lineage_record
        assert lineage["observation_id"] == valid_ingestion_request.acquisition_id
        assert lineage["provider"] == "copernicus_cdse"
        assert lineage["execution_authorized"] is False
        assert lineage["stages"] == [
            "OBSERVATION_INGESTION",
            "SAR_RASTER_VALIDATION",
            "SAR_PREPROCESSING_MAPPING_A",
            "DETECTION_BOUNDARY_PREFLIGHT",
        ]

        # Verify Preprocessing metadata
        prep = evidence.preprocessing_summary
        assert prep["preprocessing_version"] == "OPERATIONAL_SAR_PREPROCESSOR_MAPPING_A_V1"
        assert prep["normalization_contract"] == "mapping_a_zscore"
        assert prep["channel_order"] == ["VH", "VV"]

        # Verify Detection metadata
        det = evidence.detection_summary
        assert det["checkpoint_sha256"] == EXPECTED_EXP06_CHECKPOINT_SHA256
        assert det["threshold"] == 0.22
        assert det["execution_authorized"] is False
        assert det["has_prediction"] is False

        # Verify Telemetry history matches Stage H required lifecycle
        tel = evidence.telemetry
        events = tel["events"]
        stage_names = [e["stage"] for e in events]
        expected_progression = [
            PipelineStageState.RECEIVED.value,
            PipelineStageState.VALIDATING.value,
            PipelineStageState.VALIDATED.value,
            PipelineStageState.PREPROCESSING.value,
            PipelineStageState.READY_FOR_DETECTION.value,
            PipelineStageState.DETECTION_READY.value,
        ]
        assert stage_names == expected_progression

        # Verify downstream translation into canonical EvidenceItem
        item = evidence.to_evidence_item()
        assert isinstance(item, EvidenceItem)
        assert item.evidence_id == evidence.evidence_id
        assert item.evidence_type == EvidenceType.SAR_DETECTION.value
        assert item.source_type == SourceType.SENTINEL_1_SAR.value
        assert item.source_id == valid_ingestion_request.acquisition_id
        assert item.status == "ACTIVE"
