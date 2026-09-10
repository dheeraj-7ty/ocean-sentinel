"""Comprehensive adversarial and regression tests for authoritative dataset provenance.

Implements CAO Phase 3.2R specifications:
- Test 4.1: Exact QPOSD incident regression
- Test 4.2: DOI mismatch
- Test 4.3: Sensor / platform mismatch
- Test 4.4: Geographic domain mismatch
- Test 4.5: Record / filename mismatch
- Test 4.6: Stale resume attack
- Test 4.7: Direct downloader bypass attack
- Test 4.8: Premature stream test
- Test 4.9: Valid positive path (controlled tiny fixture)
- Test 4.10: Changed remote record / stale metadata attack
- Test 4.11: Missing required metadata (fail closed)
- Test 4.12: Ambiguous identity (fail closed)
- Phase 5: Independent Zero-Byte Proof
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any
import pytest

from ocean_sentinel.errors import DatasetErrorCode
from ocean_sentinel.ingestion.provenance_gate import (
    DatasetPreflightContract,
    DatasetProvenanceSpecification,
    DatasetQualificationStateMachine,
    DatasetTransferManager,
    IllegalStateTransitionError,
    ProvenanceBypassAttemptError,
    ProvenanceGate,
    ProvenanceGateDecision,
    ProvenanceGateError,
    ProvenanceGateResult,
    QualificationStateEnum,
    ResolvedRecordMetadata,
    VerifiedProvenanceToken,
)


@pytest.fixture
def qposd_metadata() -> ResolvedRecordMetadata:
    """Fixture representing the authoritative Zenodo record 19258036 (QPOSD)."""
    return ResolvedRecordMetadata(
        record_id=19258036,
        doi="10.5281/zenodo.19258036",
        title="Quad-Polarization Dataset for Marine Oil Spill and Look-Alike Segmentation",
        description=(
            "This repository contains the Quad-Polarization Oil Spill Dataset (QPOSD) "
            "acquired by airborne UAVSAR in L-band over the U.S. Gulf of Mexico (2010-2022). "
            "Data consists of 9-channel coherency matrix (T) files and 4-class RGB masks."
        ),
        creators=["Jamal, Sohail", "Li, Yu"],
        keywords=["Oil Spill", "Look-alike", "UAVSAR", "Quad-Polarization", "L-band"],
        file_names=["QPOSD.zip", "load_qposd_example.py", "patchify_qposd_example.py"],
        publication_date="2026-01-15",
        primary_archive_url="https://zenodo.org/api/records/19258036/files/QPOSD.zip/content",
        primary_archive_filename="QPOSD.zip",
    )


@pytest.fixture
def valid_morp_synth_metadata() -> ResolvedRecordMetadata:
    """Fixture representing a valid Peruvian MORP-Synth record."""
    return ResolvedRecordMetadata(
        record_id=99999999,
        doi="10.5281/zenodo.99999999",
        title="MORP-Synth: Synthetic SAR Imagery for Oil Spill Detection in Peruvian Waters",
        description=(
            "Peruvian Sentinel-1 C-band dual-polarization (VV/VH) radar imagery and binary "
            "oil spill ground truth masks generated via Morphological Region Perturbation (MORP). "
            "Covers coastal regions of Peru (Humboldt Current upwelling zone)."
        ),
        creators=["Jara, Andrex", "Humpire-Mamani, Gabriel E."],
        keywords=["Sentinel-1", "Peru", "MORP", "Oil Spill", "C-band"],
        file_names=["morp_synth_peru_sample.zip"],
        publication_date="2026-03-01",
        primary_archive_url="mock://fixture/morp_synth_peru_sample.zip",
        primary_archive_filename="morp_synth_peru_sample.zip",
    )


# ==============================================================================
# TEST 4.1 — EXACT QPOSD INCIDENT REGRESSION
# ==============================================================================
def test_4_1_exact_qposd_incident_regression(qposd_metadata: ResolvedRecordMetadata, tmp_path: Path) -> None:
    """Encode the historical failure: QPOSD must fail provenance and cause 0 archive requests/bytes."""
    spec = DatasetProvenanceSpecification.morp_synth_peru_spec()
    sm = DatasetQualificationStateMachine()
    sm.transition_to(QualificationStateEnum.PROVENANCE_CHECK_IN_PROGRESS)

    transfer_attempts: list[str] = []

    def mock_transport(url: str, dest: Path) -> int:
        transfer_attempts.append(url)
        return 1024

    transfer_mgr = DatasetTransferManager(state_machine=sm, transport=mock_transport)

    # 1. Provenance check MUST fail
    result = ProvenanceGate.evaluate_provenance(spec, qposd_metadata)
    assert result.is_valid is False
    assert result.decision == ProvenanceGateDecision.BLOCKED_DATASET_PROVENANCE

    # 2. State machine transitions to BLOCKED_DATASET_PROVENANCE
    sm.transition_to(QualificationStateEnum.BLOCKED_DATASET_PROVENANCE)
    assert sm.current_state == QualificationStateEnum.BLOCKED_DATASET_PROVENANCE

    # 3. Attempting enforce_gate raises ProvenanceGateError
    with pytest.raises(ProvenanceGateError):
        ProvenanceGate.enforce_gate(spec, qposd_metadata)

    # 4. Attempting to download without token raises ProvenanceBypassAttemptError
    with pytest.raises(ProvenanceBypassAttemptError):
        transfer_mgr.download_archive(token=None, destination_dir=tmp_path)

    # 5. Assert exactly 0 archive requests and 0 bytes transferred
    assert len(transfer_attempts) == 0
    assert transfer_mgr.archive_requests_issued == 0
    assert transfer_mgr.bytes_transferred == 0


# ==============================================================================
# TEST 4.2 — DOI MISMATCH
# ==============================================================================
def test_4_2_doi_mismatch(valid_morp_synth_metadata: ResolvedRecordMetadata) -> None:
    """Otherwise plausible metadata with mismatched DOI must fail closed with 0 bytes."""
    spec = DatasetProvenanceSpecification(
        target_identity="Peruvian S1 / MORP-Synth",
        expected_doi="10.5281/zenodo.11111111",  # Different from 99999999
        expected_geographic_domain="Peru",
        required_keywords=["MORP", "Peru"],
        prohibited_keywords=["UAVSAR", "QPOSD"],
    )
    result = ProvenanceGate.evaluate_provenance(spec, valid_morp_synth_metadata)
    assert result.is_valid is False
    assert result.decision == ProvenanceGateDecision.BLOCKED_DATASET_PROVENANCE
    assert any("DOI mismatch" in m for m in result.mismatches)


# ==============================================================================
# TEST 4.3 — SENSOR / PLATFORM MISMATCH
# ==============================================================================
def test_4_3_sensor_platform_mismatch() -> None:
    """Expected Sentinel-1; supplying UAVSAR must fail immediately."""
    spec = DatasetProvenanceSpecification.morp_synth_peru_spec()
    meta = ResolvedRecordMetadata(
        record_id=12345,
        doi="10.5281/zenodo.12345",
        title="UAVSAR Airborne Radar Oil Spill Collection in Peru",
        description="Airborne L-band sensor UAVSAR data in Peruvian coastal waters.",
        keywords=["UAVSAR", "Peru", "Oil Spill"],
        file_names=["uavsar_peru.zip"],
    )
    result = ProvenanceGate.evaluate_provenance(spec, meta)
    assert result.is_valid is False
    assert any("PROHIBITED_KEYWORD_DETECTED" in m and "UAVSAR" in m for m in result.mismatches)


# ==============================================================================
# TEST 4.4 — GEOGRAPHIC MISMATCH
# ==============================================================================
def test_4_4_geographic_mismatch() -> None:
    """Expected Peru; supplying Gulf of Mexico domain must fail immediately."""
    spec = DatasetProvenanceSpecification.morp_synth_peru_spec()
    meta = ResolvedRecordMetadata(
        record_id=54321,
        doi="10.5281/zenodo.54321",
        title="Sentinel-1 MORP Synthetic Dataset for Gulf of Mexico",
        description="Synthetic Sentinel-1 C-band imagery over the Gulf of Mexico waters.",
        keywords=["Sentinel-1", "MORP", "Gulf of Mexico"],
        file_names=["morp_gom.zip"],
    )
    result = ProvenanceGate.evaluate_provenance(spec, meta)
    assert result.is_valid is False
    assert any("Gulf of Mexico" in m for m in result.mismatches)
    assert any("GEOGRAPHIC_DOMAIN_MISMATCH" in m for m in result.mismatches)


# ==============================================================================
# TEST 4.5 — RECORD / FILENAME MISMATCH
# ==============================================================================
def test_4_5_record_filename_mismatch() -> None:
    """Plausible title but archive filename contains prohibited keyword."""
    spec = DatasetProvenanceSpecification.morp_synth_peru_spec()
    meta = ResolvedRecordMetadata(
        record_id=88888,
        doi="10.5281/zenodo.88888",
        title="MORP Synthetic Oil Spill Dataset for Peru",
        description="Peruvian coastal Sentinel-1 SAR imagery.",
        keywords=["MORP", "Peru", "Sentinel-1"],
        file_names=["QPOSD_peru_edition.zip"],  # Contains QPOSD
    )
    result = ProvenanceGate.evaluate_provenance(spec, meta)
    assert result.is_valid is False
    assert any("QPOSD" in m for m in result.mismatches)


# ==============================================================================
# TEST 4.6 — STALE RESUME ATTACK
# ==============================================================================
def test_4_6_stale_resume_attack(
    valid_morp_synth_metadata: ResolvedRecordMetadata,
    qposd_metadata: ResolvedRecordMetadata,
    tmp_path: Path,
) -> None:
    """Stale state saying verified cannot authorize transfer if remote identity changes to QPOSD."""
    spec = DatasetProvenanceSpecification.morp_synth_peru_spec()
    sm = DatasetQualificationStateMachine()

    # Step 1: Simulated previous verification
    valid_token = ProvenanceGate.enforce_gate(spec, valid_morp_synth_metadata)
    sm.transition_to(QualificationStateEnum.PROVENANCE_CHECK_IN_PROGRESS)
    sm.transition_to(QualificationStateEnum.PROVENANCE_VERIFIED, token=valid_token)

    # Step 2: Remote identity changes to QPOSD on resume attempt
    transfer_mgr = DatasetTransferManager(state_machine=sm)

    # Attempting to download using old token while remote metadata is QPOSD must be rejected
    with pytest.raises(ProvenanceBypassAttemptError) as exc:
        transfer_mgr.download_archive(
            token=valid_token,
            destination_dir=tmp_path,
            expected_metadata=qposd_metadata,  # Metadata drift check!
        )
    assert "METADATA_DRIFT_DETECTED" in str(exc.value)
    assert transfer_mgr.archive_requests_issued == 0
    assert transfer_mgr.bytes_transferred == 0


# ==============================================================================
# TEST 4.7 — DIRECT DOWNLOADER BYPASS ATTACK
# ==============================================================================
def test_4_7_direct_downloader_bypass_attack(tmp_path: Path) -> None:
    """Invoking lower-level transfer layer directly without VerifiedProvenanceToken fails closed."""
    transfer_mgr = DatasetTransferManager()

    # Attempt with None
    with pytest.raises(ProvenanceBypassAttemptError):
        transfer_mgr.download_archive(token=None, destination_dir=tmp_path)

    # Attempt with spoofed boolean or dictionary
    with pytest.raises(ProvenanceBypassAttemptError):
        transfer_mgr.download_archive(
            token={"provenance_verified": True}, destination_dir=tmp_path
        )

    # Attempt with forged token (invalid signature)
    forged_token = VerifiedProvenanceToken(
        token_id="fake_id",
        target_identity="Peruvian S1 / MORP-Synth",
        spec_fingerprint="A" * 64,
        resolved_record_id=123,
        resolved_doi="10.5281/fake",
        resolved_title="Fake Title",
        resolved_metadata_fingerprint="B" * 64,
        authorized_archive_url="http://fake.url/data.zip",
        authorized_archive_filename="data.zip",
        issued_at_utc="2026-09-09T00:00:00+00:00",
        signature="tampered_signature",
    )
    with pytest.raises(ProvenanceBypassAttemptError) as exc:
        transfer_mgr.download_archive(token=forged_token, destination_dir=tmp_path)
    assert "integrity check" in str(exc.value).lower()
    assert transfer_mgr.archive_requests_issued == 0
    assert transfer_mgr.bytes_transferred == 0


# ==============================================================================
# TEST 4.8 — PREMATURE STREAM TEST
# ==============================================================================
def test_4_8_premature_stream_test(qposd_metadata: ResolvedRecordMetadata, tmp_path: Path) -> None:
    """Ensure no stream or file handle is opened before provenance passes."""
    spec = DatasetProvenanceSpecification.morp_synth_peru_spec()
    dest_file = tmp_path / "stream_canary.bin"

    opened_streams: list[Path] = []

    def tracking_transport(url: str, dest: Path) -> int:
        opened_streams.append(dest)
        dest.write_bytes(b"DATA")
        return 4

    transfer_mgr = DatasetTransferManager(transport=tracking_transport)

    with pytest.raises(ProvenanceGateError):
        ProvenanceGate.enforce_gate(spec, qposd_metadata)

    assert not dest_file.exists()
    assert len(opened_streams) == 0
    assert transfer_mgr.archive_requests_issued == 0


# ==============================================================================
# TEST 4.9 — VALID POSITIVE PATH (CONTROLLED TINY FIXTURE)
# ==============================================================================
def test_4_9_valid_positive_path(
    valid_morp_synth_metadata: ResolvedRecordMetadata, tmp_path: Path
) -> None:
    """Controlled fixture: valid metadata passes, allows transfer, verifies checksum, succeeds."""
    spec = DatasetProvenanceSpecification.morp_synth_peru_spec()
    sm = DatasetQualificationStateMachine()
    sm.transition_to(QualificationStateEnum.PROVENANCE_CHECK_IN_PROGRESS)

    # Tiny fixture payload
    fixture_content = b"MORP_SYNTH_TINY_TEST_DATA_PAYLOAD_2026"
    fixture_sha256 = hashlib.sha256(fixture_content).hexdigest().upper()

    def fixture_transport(url: str, dest: Path) -> int:
        dest.write_bytes(fixture_content)
        return len(fixture_content)

    transfer_mgr = DatasetTransferManager(state_machine=sm, transport=fixture_transport)

    # 1. Provenance Gate passes and issues token
    token = ProvenanceGate.enforce_gate(spec, valid_morp_synth_metadata)
    assert token.verify_integrity() is True
    assert token.decision == ProvenanceGateDecision.PASSED

    # 2. Transfer executes cleanly
    downloaded_path = transfer_mgr.download_archive(
        token=token,
        destination_dir=tmp_path,
        expected_metadata=valid_morp_synth_metadata,
    )
    assert downloaded_path.exists()
    assert downloaded_path.read_bytes() == fixture_content
    assert transfer_mgr.archive_requests_issued == 1
    assert transfer_mgr.bytes_transferred == len(fixture_content)

    # 3. Checksum verification stage
    computed_sha = hashlib.sha256(downloaded_path.read_bytes()).hexdigest().upper()
    assert computed_sha == fixture_sha256
    sm.transition_to(QualificationStateEnum.CHECKSUM_VERIFIED)
    assert sm.current_state == QualificationStateEnum.CHECKSUM_VERIFIED


# ==============================================================================
# TEST 4.10 — CHANGED REMOTE RECORD / STALE METADATA
# ==============================================================================
def test_4_10_changed_remote_record_stale_metadata(
    valid_morp_synth_metadata: ResolvedRecordMetadata,
    qposd_metadata: ResolvedRecordMetadata,
    tmp_path: Path,
) -> None:
    """Run A resolves valid identity; Run B resolves wrong identity; transfer using old state fails."""
    spec = DatasetProvenanceSpecification.morp_synth_peru_spec()
    token_run_a = ProvenanceGate.enforce_gate(spec, valid_morp_synth_metadata)

    transfer_mgr = DatasetTransferManager()

    # In Run B, remote metadata has changed to QPOSD
    with pytest.raises(ProvenanceBypassAttemptError) as exc:
        transfer_mgr.download_archive(
            token=token_run_a,
            destination_dir=tmp_path,
            expected_metadata=qposd_metadata,
        )
    assert "METADATA_DRIFT_DETECTED" in str(exc.value)
    assert transfer_mgr.archive_requests_issued == 0
    assert transfer_mgr.bytes_transferred == 0


# ==============================================================================
# TEST 4.11 — MISSING REQUIRED METADATA (FAIL CLOSED)
# ==============================================================================
def test_4_11_missing_required_metadata_fails_closed() -> None:
    """Missing required metadata (empty title or DOI) must fail closed."""
    spec = DatasetProvenanceSpecification.morp_synth_peru_spec()
    incomplete_meta = ResolvedRecordMetadata(
        record_id=0,
        doi="",  # Missing DOI
        title="",  # Missing Title
        description="Some description",
    )
    result = ProvenanceGate.evaluate_provenance(spec, incomplete_meta)
    assert result.is_valid is False
    assert result.decision == ProvenanceGateDecision.BLOCKED_DATASET_PROVENANCE
    assert any("MISSING_REQUIRED_METADATA" in m for m in result.mismatches)


# ==============================================================================
# TEST 4.12 — AMBIGUOUS IDENTITY (FAIL CLOSED)
# ==============================================================================
def test_4_12_ambiguous_identity_fails_closed() -> None:
    """Record referencing conflicting platforms (UAVSAR and Sentinel-1) must fail closed."""
    spec = DatasetProvenanceSpecification.morp_synth_peru_spec()
    ambiguous_meta = ResolvedRecordMetadata(
        record_id=77777,
        doi="10.5281/zenodo.77777",
        title="Comparison of Sentinel-1 and UAVSAR for Oil Spill Detection in Peru",
        description="Dataset containing both UAVSAR L-band and Sentinel-1 C-band imagery in Peru.",
        keywords=["Sentinel-1", "UAVSAR", "Peru", "MORP"],
        file_names=["dataset.zip"],
    )
    result = ProvenanceGate.evaluate_provenance(spec, ambiguous_meta)
    assert result.is_valid is False
    assert any(
        "PROHIBITED_KEYWORD_DETECTED" in m or "AMBIGUOUS_DATASET_IDENTITY" in m
        for m in result.mismatches
    )


# ==============================================================================
# PHASE 5 — INDEPENDENT ZERO-BYTE PROOF
# ==============================================================================
def test_phase_5_independent_zero_byte_proof(
    qposd_metadata: ResolvedRecordMetadata, tmp_path: Path
) -> None:
    """Independently prove that an invalid provenance path results in exactly 0 requests and 0 bytes transferred."""
    spec = DatasetProvenanceSpecification.morp_synth_peru_spec()

    network_wire_taps: list[dict[str, Any]] = []

    def wire_tap_transport(url: str, dest: Path) -> int:
        network_wire_taps.append({"url": url, "destination": str(dest)})
        dest.write_bytes(b"ILLEGAL_BYTES")
        return 13

    transfer_mgr = DatasetTransferManager(transport=wire_tap_transport)

    # Execute gate enforcement
    with pytest.raises(ProvenanceGateError):
        ProvenanceGate.enforce_gate(spec, qposd_metadata)

    # Attempt download without valid token
    with pytest.raises(ProvenanceBypassAttemptError):
        transfer_mgr.download_archive(token=None, destination_dir=tmp_path)

    # Absolute proof: 0 wire requests, 0 bytes transferred, 0 files created
    assert len(network_wire_taps) == 0, "FATAL: Network request was issued on invalid provenance!"
    assert transfer_mgr.archive_requests_issued == 0, "FATAL: Archive request count > 0!"
    assert transfer_mgr.bytes_transferred == 0, "FATAL: Bytes transferred > 0!"
    assert len(list(tmp_path.iterdir())) == 0, "FATAL: File created on disk on invalid provenance!"


# ==============================================================================
# STATE MACHINE TRANSITION SAFETY TESTS
# ==============================================================================
def test_state_machine_blocks_illegal_transitions() -> None:
    """Ensure BLOCKED_DATASET_PROVENANCE cannot jump directly to DOWNLOADING, EXTRACTING, or QUALIFIED."""
    sm = DatasetQualificationStateMachine(
        initial_state=QualificationStateEnum.BLOCKED_DATASET_PROVENANCE
    )

    # Cannot transition directly to DOWNLOADING
    with pytest.raises(IllegalStateTransitionError):
        sm.transition_to(QualificationStateEnum.DOWNLOADING)

    # Cannot transition directly to EXTRACTING
    with pytest.raises(IllegalStateTransitionError):
        sm.transition_to(QualificationStateEnum.EXTRACTING)

    # Cannot transition directly to QUALIFIED
    with pytest.raises(IllegalStateTransitionError):
        sm.transition_to(QualificationStateEnum.QUALIFIED)

    # Can ONLY transition back to fresh PROVENANCE_CHECK_IN_PROGRESS
    sm.transition_to(QualificationStateEnum.PROVENANCE_CHECK_IN_PROGRESS)
    assert sm.current_state == QualificationStateEnum.PROVENANCE_CHECK_IN_PROGRESS


# ==============================================================================
# PREFLIGHT CONTRACT TEST
# ==============================================================================
def test_dataset_preflight_contract(valid_morp_synth_metadata: ResolvedRecordMetadata) -> None:
    """Verify generation of formal DatasetPreflightContract."""
    spec = DatasetProvenanceSpecification.morp_synth_peru_spec()
    token = ProvenanceGate.enforce_gate(spec, valid_morp_synth_metadata)
    contract = DatasetPreflightContract.generate(spec, valid_morp_synth_metadata, token=token)

    assert contract.intended_dataset_identity == spec.target_identity
    assert contract.resolved_record_id == valid_morp_synth_metadata.record_id
    assert contract.verification_decision == ProvenanceGateDecision.PASSED
    assert contract.data_access_status == "MORP_SYNTH_DATA_ACCESS = UNRESOLVED"
    assert contract.token_fingerprint == token.signature


# ==============================================================================
# PATH TRAVERSAL AND CHECKSUM HARDENING TESTS
# ==============================================================================
def test_path_traversal_filename_blocked(
    valid_morp_synth_metadata: ResolvedRecordMetadata, tmp_path: Path
) -> None:
    """Verify that an archive filename attempting path traversal is immediately rejected."""
    spec = DatasetProvenanceSpecification.morp_synth_peru_spec()
    sm = DatasetQualificationStateMachine()
    sm.transition_to(QualificationStateEnum.PROVENANCE_CHECK_IN_PROGRESS)

    # If the resolved record itself has a path traversal in filename, verify token creation or transfer rejection
    bad_meta = valid_morp_synth_metadata.model_copy(
        update={"primary_archive_filename": "../../evil.zip"}
    )
    token = ProvenanceGate.enforce_gate(spec, bad_meta)

    transfer_mgr = DatasetTransferManager(state_machine=sm)
    with pytest.raises(ProvenanceBypassAttemptError, match="PATH_TRAVERSAL_DETECTED"):
        transfer_mgr.download_archive(token=token, destination_dir=tmp_path)


def test_verify_archive_checksum_success_and_failure(tmp_path: Path) -> None:
    """Verify that verify_archive_checksum transitions state upon success and rejects mismatches."""
    sm = DatasetQualificationStateMachine(initial_state=QualificationStateEnum.DOWNLOAD_COMPLETED)
    transfer_mgr = DatasetTransferManager(state_machine=sm)

    dummy_archive = tmp_path / "valid.zip"
    content = b"MORP_SYNTH_SAMPLE_DATA_BYTES"
    dummy_archive.write_bytes(content)

    import hashlib
    correct_sha256 = hashlib.sha256(content).hexdigest()

    # Mismatch fails and transitions to BLOCKED_DATASET_PROVENANCE
    with pytest.raises(ProvenanceBypassAttemptError, match="CHECKSUM_MISMATCH"):
        transfer_mgr.verify_archive_checksum(
            dummy_archive,
            expected_checksum="0000000000000000000000000000000000000000000000000000000000000000",
        )
    assert sm.current_state == QualificationStateEnum.BLOCKED_DATASET_PROVENANCE

    # Reset state machine to DOWNLOAD_COMPLETED
    sm.current_state = QualificationStateEnum.DOWNLOAD_COMPLETED
    assert transfer_mgr.verify_archive_checksum(dummy_archive, expected_checksum=correct_sha256) is True
    assert sm.current_state == QualificationStateEnum.CHECKSUM_VERIFIED

