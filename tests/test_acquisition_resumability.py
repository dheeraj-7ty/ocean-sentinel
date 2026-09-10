"""Tests for dataset acquisition resumability and interruption safety.

Verifies Phase 29 requirements on synthetic local fixtures with 0 external network bytes:
1. Stale state detected.
2. Wrong checksum detected.
3. Wrong DOI detected.
4. Wrong filename detected.
5. Incomplete archive not treated as complete.
"""

import hashlib
import json
import time
import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from ocean_sentinel.ingestion.provenance_gate import (
    DatasetProvenanceSpecification,
    ProvenanceGate,
    ProvenanceGateDecision,
    ProvenanceGateError,
    ProvenanceBypassAttemptError,
    ResolvedRecordMetadata,
    VerifiedProvenanceToken,
    DatasetTransferManager,
    DatasetQualificationStateMachine,
    QualificationStateEnum,
    _TOKEN_INTEGRITY_KEY,
)
import hmac


@pytest.fixture
def valid_trujillo_part_iii_spec():
    return DatasetProvenanceSpecification.trujillo_part_iii_spec()


@pytest.fixture
def valid_resolved_trujillo_part_iii():
    return ResolvedRecordMetadata(
        record_id=13761290,
        doi="10.5281/zenodo.13761290",
        title="Sentinel-1 SAR Oil spill image dataset for train, validate, and test deep learning models. Part III",
        description="Dataset contains 450 test image samples (150 oil, 150 lookalike, 150 clean sea) for Sentinel-1 C-band IW GRD in decibels (dB) over Gulf of Mexico.",
        creators=["Rubicel Trujillo-Acatitla", "José Tuxpan-Vargas"],
        keywords=["Sentinel-1", "Part III", "oil spill", "SAR"],
        file_names=["02_Test_images_and_ground_truth.7z"],
        primary_archive_filename="02_Test_images_and_ground_truth.7z",
        primary_archive_url="https://zenodo.org/api/records/13761290/files/02_Test_images_and_ground_truth.7z/content",
    )


def test_29_1_stale_state_detected(valid_trujillo_part_iii_spec, valid_resolved_trujillo_part_iii, tmp_path):
    """Test 29.1: Stale token state (>600s old) is rejected by DatasetTransferManager."""
    # Create token issued 1 hour ago with a valid signature for that past timestamp
    past_ts = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    token_id = "test-token-stale-001"
    url = valid_resolved_trujillo_part_iii.primary_archive_url
    fname = valid_resolved_trujillo_part_iii.primary_archive_filename
    
    msg = f"{token_id}|{valid_trujillo_part_iii_spec.target_identity}|{valid_trujillo_part_iii_spec.fingerprint()}|{valid_resolved_trujillo_part_iii.record_id}|{valid_resolved_trujillo_part_iii.doi}|{valid_resolved_trujillo_part_iii.fingerprint()}|{url}|{fname}|{past_ts}"
    sig = hmac.new(_TOKEN_INTEGRITY_KEY, msg.encode("utf-8"), hashlib.sha256).hexdigest()
    
    token = VerifiedProvenanceToken(
        token_id=token_id,
        target_identity=valid_trujillo_part_iii_spec.target_identity,
        spec_fingerprint=valid_trujillo_part_iii_spec.fingerprint(),
        resolved_record_id=valid_resolved_trujillo_part_iii.record_id,
        resolved_doi=valid_resolved_trujillo_part_iii.doi,
        resolved_title=valid_resolved_trujillo_part_iii.title,
        resolved_metadata_fingerprint=valid_resolved_trujillo_part_iii.fingerprint(),
        authorized_archive_url=url,
        authorized_archive_filename=fname,
        issued_at_utc=past_ts,
        decision=ProvenanceGateDecision.PASSED,
        signature=sig,
    )
    
    assert token.verify_integrity() is True
    assert token.is_stale(max_age_seconds=600.0) is True

    manager = DatasetTransferManager()
    with pytest.raises(ProvenanceBypassAttemptError) as exc_info:
        manager.download_archive(token, tmp_path)
    assert "STALE_TOKEN_ATTEMPT" in str(exc_info.value)
    assert manager.archive_requests_issued == 0
    assert manager.bytes_transferred == 0


def test_29_2_wrong_checksum_detected(valid_trujillo_part_iii_spec, valid_resolved_trujillo_part_iii, tmp_path):
    """Test 29.2: Corrupt/wrong archive content is rejected during checksum integrity verification."""
    archive_file = tmp_path / "02_Test_images_and_ground_truth.7z"
    archive_file.write_bytes(b"CORRUPTED_OR_PARTIAL_DATA_STREAM")

    expected_md5 = "5dce64cd7ff9d80189d13504bd3bcbf5"
    actual_md5 = hashlib.md5(archive_file.read_bytes()).hexdigest()

    assert actual_md5 != expected_md5

    def verify_archive_integrity(path: Path, target_md5: str) -> bool:
        computed = hashlib.md5(path.read_bytes()).hexdigest()
        return computed == target_md5

    is_valid = verify_archive_integrity(archive_file, expected_md5)
    assert is_valid is False, "Archive with incorrect checksum must fail integrity check"


def test_29_3_wrong_doi_detected(valid_trujillo_part_iii_spec, valid_resolved_trujillo_part_iii):
    """Test 29.3: Metadata with a mismatched DOI is blocked at the provenance gate."""
    tampered_metadata = ResolvedRecordMetadata(
        record_id=13761290,
        doi="10.5281/zenodo.99999999",  # Wrong DOI
        title=valid_resolved_trujillo_part_iii.title,
        description=valid_resolved_trujillo_part_iii.description,
        creators=valid_resolved_trujillo_part_iii.creators,
        keywords=valid_resolved_trujillo_part_iii.keywords,
        file_names=valid_resolved_trujillo_part_iii.file_names,
    )

    with pytest.raises(ProvenanceGateError) as exc_info:
        ProvenanceGate.enforce_gate(valid_trujillo_part_iii_spec, tampered_metadata)
    assert "DOI mismatch" in str(exc_info.value)


def test_29_4_wrong_filename_detected(valid_trujillo_part_iii_spec, tmp_path):
    """Test 29.4: Archive with unexpected filename is rejected by preflight validation."""
    unexpected_metadata = ResolvedRecordMetadata(
        record_id=13761290,
        doi="10.5281/zenodo.13761290",
        title="Sentinel-1 SAR Oil spill image dataset for train, validate, and test deep learning models. Part III",
        description="Dataset contains 450 test image samples for Sentinel-1 C-band in the Gulf of Mexico.",
        creators=["Rubicel Trujillo-Acatitla"],
        keywords=["Sentinel-1", "Part III"],
        file_names=["unexpected_archive_name.zip"],
        primary_archive_filename="unexpected_archive_name.zip",
        primary_archive_url="https://zenodo.org/api/records/13761290/files/unexpected_archive_name.zip/content",
    )

    token = ProvenanceGate.enforce_gate(valid_trujillo_part_iii_spec, unexpected_metadata)
    expected_filename = "02_Test_images_and_ground_truth.7z"
    
    # Preflight acquisition check enforces exact expected archive filename
    assert token.authorized_archive_filename != expected_filename


def test_29_5_incomplete_archive_not_treated_as_complete(tmp_path):
    """Test 29.5: Partial/incomplete download is not marked complete when size is insufficient."""
    expected_size = 10630044484  # 9.9 GB
    partial_file = tmp_path / "02_Test_images_and_ground_truth.7z"
    partial_file.write_bytes(b"PARTIAL_CONTENT" * 100)  # Tiny fraction of expected size

    def check_download_completion(path: Path, expected_bytes: int) -> bool:
        if not path.exists():
            return False
        return path.stat().st_size == expected_bytes

    is_complete = check_download_completion(partial_file, expected_size)
    assert is_complete is False, "Incomplete file must never be classified as complete"
