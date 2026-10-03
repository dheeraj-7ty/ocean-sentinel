"""Test Suite for Phase 7A: Investigation Run Kernel & Durable Scientific Execution Spine.

Covers:
1. InvestigationRun serialization & deserialization roundtrip
2. InvestigationContext consistency & canonical baseline binding
3. ScientificDAG topological ordering & independent branch representation
4. ScientificDAG invalid dependency & cycle detection
5. Stage state transitions & granular attempt audit persistence
6. ArtifactRef SHA-256 integrity binding & corruption detection
7. Stage idempotency & duplicate artifact prevention
8. Dynamic restart & crash recovery proof (Section 13 mandatory proof)
9. Scientific safety firewall fail-closed enforcement (Section 14 mandatory proof)
10. Phase 6C AcquisitionJobManifest backward compatibility & bridge
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import pytest

from ocean_sentinel.orchestration.dag import (
    DAGNode,
    DAGValidationError,
    ScientificDAG,
    create_canonical_scientific_dag,
)
from ocean_sentinel.orchestration.engine import (
    InvestigationEngine,
    InvestigationEngineError,
    ScientificGateViolationError,
)
from ocean_sentinel.orchestration.investigation_context import (
    CANONICAL_MODEL_CHECKPOINT,
    CANONICAL_MODEL_SHA256,
    CANONICAL_PROTOCOL_DOC,
    CANONICAL_PROTOCOL_SHA256,
    AuthorizationState,
    InvestigationContext,
)
from ocean_sentinel.orchestration.investigation_run import (
    ArtifactRef,
    ArtifactType,
    ContentStatus,
    InvestigationRun,
    InvestigationRunRecoveryState,
    InvestigationRunRequest,
    InvestigationRunStatus,
    InvestigationStageState,
    ProvenanceClass,
    StageAttempt,
    StageExecutionStatus,
    StageRetryPolicy,
)
from ocean_sentinel.orchestration.investigation_store import InvestigationRunStore


# ===========================================================================
# 1. Serialization & Domain Root Roundtrip
# ===========================================================================


def test_investigation_run_serialization_roundtrip():
    """Verify complete lossless serialization and deserialization of InvestigationRun."""
    req = InvestigationRunRequest(
        bbox=[-12.5, -77.5, -12.0, -77.0],
        time_window={"start_time": "2026-10-01T00:00:00Z", "end_time": "2026-10-02T00:00:00Z"},
        analysis_mode="PHYSICAL",
        requested_outputs=["GEOTIFF", "EVIDENCE_OBJECT"],
        provider="copernicus_cdse",
        platform="sentinel-1",
        polarizations=["VV", "VH"],
        investigation_label="Test Spill Investigation 01",
    )

    run = InvestigationRun(
        run_id="inv_20261004_test01",
        request=req,
        provenance_policy="FAIL_CLOSED_OPERATIONAL",
        graph_id="canonical_scientific_dag_v1",
        overall_status=InvestigationRunStatus.REQUESTED.value,
    )

    # Add a stage
    run.set_stage_status("VALIDATE", StageExecutionStatus.COMPLETED, message="Validation passed")

    # Add an attempt
    attempt = StageAttempt(
        attempt_id="att_val_01",
        stage_id="VALIDATE",
        attempt_number=1,
        status=StageExecutionStatus.COMPLETED.value,
        output_hashes={"art_req_01": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"},
        config_fingerprint="fp_val_test",
    )
    run.record_attempt(attempt)

    # Add an artifact
    art = ArtifactRef(
        artifact_id="art_req_01",
        type=ArtifactType.JSON_METADATA.value,
        format="application/json",
        path="outputs/investigations/inv_20261004_test01/manifest.json",
        size_bytes=1024,
        sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        producer_stage="VALIDATE",
        provenance_class=ProvenanceClass.DERIVED_ANALYTICAL.value,
        content_status=ContentStatus.UNVERIFIED.value,
    )
    run.add_artifact(art)

    data = run.to_dict()
    assert isinstance(data, dict)
    assert data["run_id"] == "inv_20261004_test01"
    assert data["overall_status"] == InvestigationRunStatus.REQUESTED.value
    assert len(data["stages"]) == 1
    assert len(data["artifacts"]) == 1
    assert len(data["attempts"]) == 1

    reconstructed = InvestigationRun.from_dict(data)
    assert reconstructed.run_id == run.run_id
    assert reconstructed.overall_status == run.overall_status
    assert reconstructed.request.bbox == [-12.5, -77.5, -12.0, -77.0]
    assert reconstructed.request.analysis_mode == "PHYSICAL"
    assert reconstructed.stages["VALIDATE"].status == StageExecutionStatus.COMPLETED.value
    assert reconstructed.stages["VALIDATE"].message == "Validation passed"
    assert len(reconstructed.artifacts) == 1
    assert reconstructed.artifacts[0].artifact_id == "art_req_01"
    assert reconstructed.artifacts[0].sha256 == art.sha256
    assert len(reconstructed.attempts) == 1
    assert reconstructed.attempts[0].attempt_id == "att_val_01"


# ===========================================================================
# 2. Context Consistency & Canonical Baseline Binding
# ===========================================================================


def test_investigation_context_consistency():
    """Verify InvestigationContext binds canonical model and protocol identities."""
    ctx = InvestigationContext(
        run_id="inv_ctx_test",
        request={"mode": "DEMO"},
        aoi={"type": "Polygon", "coordinates": []},
        provenance_policy="FAIL_CLOSED_OPERATIONAL",
    )

    # Invariant: Must bind canonical model checkpoint and protocol document
    assert ctx.model_identity == CANONICAL_MODEL_CHECKPOINT
    assert ctx.model_sha256 == CANONICAL_MODEL_SHA256
    assert ctx.protocol_identity == CANONICAL_PROTOCOL_DOC
    assert ctx.protocol_sha256 == CANONICAL_PROTOCOL_SHA256

    # Invariant: Scientific execution disabled by default
    assert not ctx.authorization_state.SCIENTIFIC_EXECUTION_AUTHORIZED
    assert not ctx.authorization_state.MODEL_INFERENCE_AUTHORIZED
    assert not ctx.authorization_state.HOLDOUT_ACCESS_AUTHORIZED
    assert not ctx.authorization_state.PART_III_ACCESS_AUTHORIZED
    assert not ctx.authorization_state.THRESHOLD_TUNING_AUTHORIZED

    # Roundtrip serialization
    data = ctx.to_dict()
    reconstructed = InvestigationContext.from_dict(data)
    assert reconstructed.run_id == "inv_ctx_test"
    assert reconstructed.model_sha256 == CANONICAL_MODEL_SHA256
    assert not reconstructed.authorization_state.MODEL_INFERENCE_AUTHORIZED


# ===========================================================================
# 3. Scientific DAG Ordering & Independent Branches
# ===========================================================================


def test_scientific_dag_topological_ordering():
    """Verify canonical DAG topological order satisfies all dependencies."""
    dag = create_canonical_scientific_dag()
    order = dag.get_topological_order()

    assert len(order) == 10
    # Invariant: Root must be VALIDATE
    assert order[0] == "VALIDATE"

    idx_map = {stage_id: idx for idx, stage_id in enumerate(order)}

    # Ingest depends on Validate
    assert idx_map["VALIDATE"] < idx_map["INGEST"]
    # Preprocess depends on Ingest
    assert idx_map["INGEST"] < idx_map["PREPROCESS"]
    # Infer depends on Preprocess
    assert idx_map["PREPROCESS"] < idx_map["INFER"]
    # Interpret depends on Infer
    assert idx_map["INFER"] < idx_map["INTERPRET"]
    # Temporal depends on Preprocess
    assert idx_map["PREPROCESS"] < idx_map["TEMPORAL"]
    # Drift and AIS depend on Validate
    assert idx_map["VALIDATE"] < idx_map["DRIFT"]
    assert idx_map["VALIDATE"] < idx_map["AIS"]
    # Fusion depends on Drift, AIS, Temporal
    assert idx_map["DRIFT"] < idx_map["FUSION"]
    assert idx_map["AIS"] < idx_map["FUSION"]
    assert idx_map["TEMPORAL"] < idx_map["FUSION"]
    # Export depends on Fusion
    assert idx_map["FUSION"] < idx_map["EXPORT"]


def test_scientific_dag_ready_stages():
    """Verify ready stage determination given completed stages."""
    dag = create_canonical_scientific_dag()

    # Initial state: only root VALIDATE is ready
    ready0 = dag.get_ready_stages(set())
    assert ready0 == ["VALIDATE"]

    # When VALIDATE completed: INGEST, AIS, DRIFT become ready simultaneously
    ready1 = dag.get_ready_stages({"VALIDATE"})
    assert set(ready1) == {"INGEST", "AIS", "DRIFT"}

    # When INGEST completed: PREPROCESS becomes ready
    ready2 = dag.get_ready_stages({"VALIDATE", "INGEST"})
    assert "PREPROCESS" in ready2


# ===========================================================================
# 4. DAG Cycle & Invalid Dependency Rejection
# ===========================================================================


def test_dag_cycle_and_invalid_dependency_rejection():
    """Verify DAG rejects missing dependencies, self-dependencies, and cycles."""
    # 1. Missing dependency
    dag_missing = ScientificDAG(graph_id="missing_dep_test")
    dag_missing.add_node(DAGNode(id="B", dependencies=["NON_EXISTENT"]))
    with pytest.raises(DAGValidationError, match="depends on undefined stage"):
        dag_missing.validate()

    # 2. Self dependency
    dag_self = ScientificDAG(graph_id="self_dep_test")
    dag_self.add_node(DAGNode(id="A", dependencies=["A"]))
    with pytest.raises(DAGValidationError, match="cannot depend on itself"):
        dag_self.validate()

    # 3. Direct cycle A -> B -> A
    dag_cycle = ScientificDAG(graph_id="cycle_test")
    dag_cycle.add_node(DAGNode(id="A", dependencies=["B"]))
    dag_cycle.add_node(DAGNode(id="B", dependencies=["A"]))
    with pytest.raises(DAGValidationError, match="Cyclic dependency detected"):
        dag_cycle.validate()


# ===========================================================================
# 5. Stage State Transitions & Attempt Persistence
# ===========================================================================


def test_stage_state_transitions_and_attempts(tmp_path: Path):
    """Verify stage transitions, attempts, and sidecar persistence to disk."""
    store = InvestigationRunStore(base_dir=tmp_path / "investigations")
    run = InvestigationRun(
        run_id="inv_test_transitions",
        request=InvestigationRunRequest(analysis_mode="DEMO"),
    )

    run.set_stage_status("VALIDATE", StageExecutionStatus.RUNNING)
    assert run.stages["VALIDATE"].status == StageExecutionStatus.RUNNING.value
    assert run.stages["VALIDATE"].started_at is not None
    assert run.overall_status == InvestigationRunStatus.RUNNING.value

    # Record attempt
    attempt = StageAttempt(
        attempt_id="att_01",
        stage_id="VALIDATE",
        attempt_number=1,
        status=StageExecutionStatus.RUNNING.value,
        config_fingerprint="fp_123",
    )
    run.record_attempt(attempt)
    store.save_run(run)

    # Verify sidecar files written atomically
    run_dir = store.get_run_dir("inv_test_transitions")
    assert (run_dir / "manifest.json").is_file()
    assert (run_dir / "stages.json").is_file()
    assert (run_dir / "attempts.json").is_file()
    assert (run_dir / "artifacts.json").is_file()

    # Complete stage
    attempt.mark_completed({"output_val": "hash_abc"})
    run.set_stage_status("VALIDATE", StageExecutionStatus.COMPLETED)
    assert run.stages["VALIDATE"].status == StageExecutionStatus.COMPLETED.value
    assert run.stages["VALIDATE"].finished_at is not None
    assert run.stages["VALIDATE"].duration_seconds is not None

    store.save_run(run)

    # Reload from disk
    loaded = store.load_run("inv_test_transitions")
    assert loaded is not None
    assert loaded.stages["VALIDATE"].status == StageExecutionStatus.COMPLETED.value
    assert len(loaded.attempts) == 1
    assert loaded.attempts[0].status == StageExecutionStatus.COMPLETED.value


# ===========================================================================
# 6. ArtifactRef Integrity Binding & Corruption Detection
# ===========================================================================


def test_artifact_ref_integrity_verification(tmp_path: Path):
    """Verify ArtifactRef checks SHA-256 integrity, detects corruption, and handles missing files."""
    repo_root = tmp_path
    rel_path = "outputs/data/test_raster.tif"
    full_path = repo_root / rel_path
    full_path.parent.mkdir(parents=True, exist_ok=True)

    payload = b"FAKE_SAR_GEOTIFF_FLOAT32_PAYLOAD"
    full_path.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()

    art = ArtifactRef(
        artifact_id="art_sar_01",
        type=ArtifactType.GEOTIFF.value,
        format="raster/geotiff",
        path=rel_path,
        size_bytes=len(payload),
        sha256=digest,
        producer_stage="ACQUIRE",
        provenance_class=ProvenanceClass.REAL_OBSERVATION.value,
    )

    # 1. Valid integrity
    assert art.verify_integrity(repo_root) is True
    assert art.content_status == ContentStatus.INTEGRITY_VERIFIED.value

    # 2. Corrupted file
    full_path.write_bytes(b"CORRUPTED_BYTES")
    assert art.verify_integrity(repo_root) is False
    assert art.content_status == ContentStatus.CORRUPTED.value

    # 3. Missing file
    full_path.unlink()
    assert art.verify_integrity(repo_root) is False
    assert art.content_status == ContentStatus.MISSING.value


# ===========================================================================
# 7. Stage Idempotency & Duplicate Artifact Prevention
# ===========================================================================


def test_stage_idempotency_and_duplicate_prevention(tmp_path: Path):
    """Verify that re-executing a completed stage with identical fingerprint is skipped idempotently."""
    store = InvestigationRunStore(base_dir=tmp_path / "investigations", repo_root=tmp_path)
    engine = InvestigationEngine(store=store, repo_root=tmp_path)

    run = InvestigationRun(
        run_id="inv_idempotency_test",
        request=InvestigationRunRequest(analysis_mode="DEMO"),
    )
    context = InvestigationContext(run_id=run.run_id)

    call_count = 0

    def mock_validate_handler(ctx: InvestigationContext, r: InvestigationRun) -> list[ArtifactRef]:
        nonlocal call_count
        call_count += 1
        # Materialize an output artifact
        out_rel = f"outputs/investigations/{r.run_id}/artifacts/validate_result.json"
        out_full = tmp_path / out_rel
        out_full.parent.mkdir(parents=True, exist_ok=True)
        content = b'{"validation": "passed"}'
        out_full.write_bytes(content)
        digest = hashlib.sha256(content).hexdigest()

        return [
            ArtifactRef(
                artifact_id=f"art_val_{r.run_id}",
                type=ArtifactType.JSON_METADATA.value,
                format="application/json",
                path=out_rel,
                size_bytes=len(content),
                sha256=digest,
                producer_stage="VALIDATE",
            )
        ]

    # First execution: handler should be invoked
    att1 = engine.execute_stage(run, context, "VALIDATE", mock_validate_handler)
    assert call_count == 1
    assert att1.status == StageExecutionStatus.COMPLETED.value
    assert len(run.artifacts) == 1

    # Second execution with identical context and outputs: should be skipped idempotently
    att2 = engine.execute_stage(run, context, "VALIDATE", mock_validate_handler)
    assert call_count == 1  # Handler NOT called again!
    assert att2.attempt_id == att1.attempt_id
    assert len(run.artifacts) == 1  # No duplicate artifacts registered


# ===========================================================================
# 8. Dynamic Restart & Crash Recovery Proof (Section 13 Mandatory Proof)
# ===========================================================================


def test_dynamic_restart_and_recovery_proof(tmp_path: Path):
    """Mandatory Section 13 Acceptance Test:

    1. Start a run.
    2. Complete safe stages (VALIDATE, INGEST, PREPROCESS) and persist artifacts.
    3. Simulate process interruption before next stage (TEMPORAL).
    4. Simulate process restart (create fresh store & engine with empty in-memory state).
    5. Reconstruct run from durable state.
    6. Verify completed stages are not redundantly re-executed.
    7. Resume safely from earliest resumable stage (TEMPORAL).
    8. Verify artifact/input hashes remain consistent.
    9. Verify scientific authorization remains unchanged (EXECUTION_AUTHORIZED = False).
    """
    store1 = InvestigationRunStore(base_dir=tmp_path / "investigations", repo_root=tmp_path)
    engine1 = InvestigationEngine(store=store1, repo_root=tmp_path)

    run1 = InvestigationRun(
        run_id="inv_recovery_proof_001",
        request=InvestigationRunRequest(analysis_mode="DEMO"),
    )
    ctx1 = InvestigationContext(run_id=run1.run_id)

    stages_executed: list[str] = []

    def make_handler(stage_name: str):
        def handler(c: InvestigationContext, r: InvestigationRun) -> list[ArtifactRef]:
            stages_executed.append(stage_name)
            out_rel = f"outputs/investigations/{r.run_id}/artifacts/{stage_name.lower()}_out.json"
            out_full = tmp_path / out_rel
            out_full.parent.mkdir(parents=True, exist_ok=True)
            payload = f'{{"stage": "{stage_name}"}}'.encode("utf-8")
            out_full.write_bytes(payload)
            digest = hashlib.sha256(payload).hexdigest()
            return [
                ArtifactRef(
                    artifact_id=f"art_{stage_name.lower()}_{r.run_id}",
                    type=ArtifactType.JSON_METADATA.value,
                    format="application/json",
                    path=out_rel,
                    size_bytes=len(payload),
                    sha256=digest,
                    producer_stage=stage_name,
                )
            ]

        return handler

    handlers = {
        "VALIDATE": make_handler("VALIDATE"),
        "INGEST": make_handler("INGEST"),
        "PREPROCESS": make_handler("PREPROCESS"),
        "TEMPORAL": make_handler("TEMPORAL"),
    }

    # Step 1-3: Run stages, intercepting/interrupting before TEMPORAL
    run1 = engine1.run_pipeline(run1, ctx1, handlers, interrupt_before_stage="TEMPORAL")
    assert stages_executed == ["VALIDATE", "INGEST", "PREPROCESS"]
    assert run1.overall_status == InvestigationRunStatus.SUSPENDED.value
    assert run1.stages["TEMPORAL"].status == StageExecutionStatus.RUNNING.value

    # Verify physical files written to disk
    run_dir = store1.get_run_dir("inv_recovery_proof_001")
    assert (run_dir / "manifest.json").is_file()
    assert (tmp_path / "outputs/investigations/inv_recovery_proof_001/artifacts/validate_out.json").is_file()
    assert (tmp_path / "outputs/investigations/inv_recovery_proof_001/artifacts/ingest_out.json").is_file()
    assert (tmp_path / "outputs/investigations/inv_recovery_proof_001/artifacts/preprocess_out.json").is_file()

    # Step 4: Simulate complete process restart (drop in-memory engine and store)
    del engine1
    del store1
    del run1
    del ctx1

    store2 = InvestigationRunStore(base_dir=tmp_path / "investigations", repo_root=tmp_path)
    engine2 = InvestigationEngine(store=store2, repo_root=tmp_path)

    # Step 5: Reconstruct run from durable state
    loaded_run = store2.load_run("inv_recovery_proof_001")
    assert loaded_run is not None

    recovery = store2.determine_recovery_state(loaded_run)
    assert recovery.can_resume is True
    assert set(recovery.completed_stages) == {"VALIDATE", "INGEST", "PREPROCESS"}
    assert recovery.interrupted_stage == "TEMPORAL"
    assert recovery.next_resumable_stage == "TEMPORAL"

    # Prepare resume (resets interrupted attempt, cleans up state)
    resumed_run, next_stage = store2.prepare_resume(loaded_run)
    assert next_stage == "TEMPORAL"
    assert resumed_run.stages["TEMPORAL"].status == StageExecutionStatus.PENDING.value
    assert resumed_run.overall_status == InvestigationRunStatus.RUNNING.value

    # Step 6-8: Resume pipeline without redundant execution of completed stages
    resumed_ctx = InvestigationContext(run_id=resumed_run.run_id)
    # Populate context with already-verified artifacts
    for a in resumed_run.artifacts:
        resumed_ctx.register_artifact(a)

    final_run = engine2.run_pipeline(resumed_run, resumed_ctx, handlers)

    # Invariant: VALIDATE, INGEST, PREPROCESS were NOT re-executed! Only TEMPORAL executed.
    assert stages_executed == ["VALIDATE", "INGEST", "PREPROCESS", "TEMPORAL"]
    assert final_run.stages["TEMPORAL"].status == StageExecutionStatus.COMPLETED.value

    # Step 9: Verify artifact hashes remain consistent
    for art in final_run.artifacts:
        assert art.verify_integrity(tmp_path) is True

    # Step 10: Verify scientific authorization remains strictly disabled
    assert not resumed_ctx.authorization_state.SCIENTIFIC_EXECUTION_AUTHORIZED
    assert not resumed_ctx.authorization_state.MODEL_INFERENCE_AUTHORIZED
    assert not resumed_ctx.authorization_state.HOLDOUT_ACCESS_AUTHORIZED
    assert not resumed_ctx.authorization_state.PART_III_ACCESS_AUTHORIZED


# ===========================================================================
# 9. Scientific Safety Firewall Fail-Closed Enforcement (Section 14 Mandatory)
# ===========================================================================


def test_scientific_firewall_strictly_fail_closed(tmp_path: Path):
    """Mandatory Section 14 Acceptance Test:

    Verify that introducing InvestigationRun / DAG / recovery does NOT accidentally enable:
    - MODEL_INFERENCE
    - MODEL_TRAINING
    - HOLDOUT_ACCESS
    - PART_III_ACCESS
    - THRESHOLD_TUNING

    When INFER or INTERPRET is reached, the engine strictly halts fail-closed,
    marks the stage BLOCKED, and transitions run to READY_FOR_DETECTION without forward passes.
    """
    store = InvestigationRunStore(base_dir=tmp_path / "investigations", repo_root=tmp_path)
    engine = InvestigationEngine(store=store, repo_root=tmp_path)

    run = InvestigationRun(
        run_id="inv_firewall_test",
        request=InvestigationRunRequest(analysis_mode="DEMO"),
    )
    ctx = InvestigationContext(run_id=run.run_id)

    # Invariant check: all scientific execution flags are False
    assert not ctx.authorization_state.SCIENTIFIC_EXECUTION_AUTHORIZED
    assert not ctx.authorization_state.MODEL_INFERENCE_AUTHORIZED
    assert not ctx.authorization_state.HOLDOUT_ACCESS_AUTHORIZED
    assert not ctx.authorization_state.PART_III_ACCESS_AUTHORIZED
    assert not ctx.authorization_state.THRESHOLD_TUNING_AUTHORIZED

    model_called = False

    def mock_model_inference_handler(c: InvestigationContext, r: InvestigationRun) -> list[ArtifactRef]:
        nonlocal model_called
        model_called = True
        return []

    # Manually mark PREPROCESS completed to make INFER eligible by DAG dependencies
    run.set_stage_status("VALIDATE", StageExecutionStatus.COMPLETED)
    run.set_stage_status("INGEST", StageExecutionStatus.COMPLETED)
    run.set_stage_status("PREPROCESS", StageExecutionStatus.COMPLETED)

    # Attempting to execute INFER must fail closed
    with pytest.raises(ScientificGateViolationError, match="scientific-gated"):
        engine.execute_stage(run, ctx, "INFER", mock_model_inference_handler)

    # Assert model was NEVER invoked
    assert model_called is False
    assert run.stages["INFER"].status == StageExecutionStatus.BLOCKED.value
    assert "gated" in run.stages["INFER"].message.lower()

    # Attempt record must show BLOCKED with explicit error
    infer_attempts = [a for a in run.attempts if a.stage_id == "INFER"]
    assert len(infer_attempts) == 1
    assert infer_attempts[0].status == StageExecutionStatus.BLOCKED.value
    assert infer_attempts[0].error["code"] == "SCIENTIFIC_EXECUTION_GATED"


# ===========================================================================
# 10. Phase 6C AcquisitionJobManifest Backward Compatibility
# ===========================================================================


def test_phase6c_acquisition_manifest_backward_compatibility():
    """Verify InvestigationRun.from_acquisition_manifest converts Phase 6C manifest cleanly."""
    from ocean_sentinel.orchestration.acquisition_job import (
        AcquisitionJobManifest,
        AcquisitionJobStatus,
    )

    acq_manifest = AcquisitionJobManifest(
        job_id="acq_20261003_120000_abcd",
        status=AcquisitionJobStatus.READY_FOR_DETECTION.value,
        request_params={
            "bbox": [-12.5, -77.5, -12.0, -77.0],
            "start_time": "2026-10-01T00:00:00Z",
            "end_time": "2026-10-02T00:00:00Z",
            "provider": "copernicus_cdse",
            "platform": "sentinel-1",
            "polarizations": ["VV", "VH"],
            "investigation_label": "CDSE Live Smoke Ingestion",
        },
        acquisition_id="S1A_IW_GRDH_1SDV_20261001T000000_D2F2_COG",
        provider="copernicus_cdse",
        geotiff_path="data/raw/acquisitions/S1A_..._D2F2/observation.tif",
        metadata_path="data/raw/acquisitions/S1A_..._D2F2/metadata.json",
        content_sha256="c41fbf7bed0102f9fd29cee4df752c4496b6c281632852b41f124ac7d3c9d8ee",
        evidence_id="ev_acq_20261003_120000_abcd",
        execution_authorized=False,
        has_prediction=False,
    )

    inv_run = InvestigationRun.from_acquisition_manifest(acq_manifest)

    assert inv_run.run_id == "acq_20261003_120000_abcd"
    assert inv_run.overall_status == InvestigationRunStatus.READY_FOR_DETECTION.value
    assert inv_run.request.bbox == [-12.5, -77.5, -12.0, -77.0]
    assert inv_run.request.analysis_mode == "PHYSICAL"
    assert inv_run.evidence_state["evidence_id"] == "ev_acq_20261003_120000_abcd"
    assert inv_run.evidence_state["execution_authorized"] is False
    assert inv_run.evidence_state["has_prediction"] is False

    # Check registered artifacts
    geotiff_art = inv_run.get_artifact("art_geotiff_acq_20261003_120000_abcd")
    assert geotiff_art is not None
    assert geotiff_art.type == ArtifactType.GEOTIFF.value
    assert geotiff_art.sha256 == "c41fbf7bed0102f9fd29cee4df752c4496b6c281632852b41f124ac7d3c9d8ee"
    assert geotiff_art.path == "data/raw/acquisitions/S1A_..._D2F2/observation.tif"

    meta_art = inv_run.get_artifact("art_metadata_acq_20261003_120000_abcd")
    assert meta_art is not None
    assert meta_art.type == ArtifactType.JSON_METADATA.value


# ===========================================================================
# 11. Security Guardrail: Raw Secrets Prohibited from Durable State
# ===========================================================================


def test_investigation_security_strictly_prohibits_raw_secrets():
    """Verify raw bearer tokens, passwords, and API keys are strictly rejected from durable state."""
    # 1. Clean context and run must serialize with zero credential fields
    ctx = InvestigationContext(run_id="sec_test_01")
    serialized_ctx = ctx.to_dict()
    assert "access_token" not in serialized_ctx
    assert "password" not in serialized_ctx
    assert "client_secret" not in serialized_ctx

    run = InvestigationRun(run_id="sec_test_01")
    serialized_run = run.to_dict()
    assert "access_token" not in serialized_run
    assert "secret" not in serialized_run

    # 2. Injecting raw secret keys into context request dictionary must be rejected
    ctx_adversarial = InvestigationContext(
        run_id="sec_test_bad",
        request={"client_secret": "raw_oauth_secret_value_12345"},
    )
    with pytest.raises(ValueError, match="Security violation: Raw credential field 'client_secret'"):
        ctx_adversarial.to_dict()

    # 3. Injecting raw bearer token into run evidence_state must be rejected
    run_adversarial = InvestigationRun(
        run_id="sec_test_bad_run",
        evidence_state={"bearer_token": "eyJh...sensitive...jwt"},
    )
    with pytest.raises(ValueError, match="Security violation: Raw credential field 'bearer_token'"):
        run_adversarial.to_dict()

    # 4. Deserialization must also reject raw secrets
    with pytest.raises(ValueError, match="Security violation"):
        InvestigationRun.from_dict({
            "run_id": "sec_test_bad_import",
            "request": {"api_key": "secret_api_key_xyz"},
        })


# ===========================================================================
# 12. Tampered Artifact Idempotency Rejection
# ===========================================================================


def test_stage_idempotency_detects_tampered_artifact_and_refuses_skip(tmp_path: Path):
    """Verify that tampering with a completed stage artifact on disk forces re-execution."""
    store = InvestigationRunStore(base_dir=tmp_path / "investigations", repo_root=tmp_path)
    engine = InvestigationEngine(store=store, repo_root=tmp_path)

    run = InvestigationRun(
        run_id="inv_tamper_test",
        request=InvestigationRunRequest(analysis_mode="DEMO"),
    )
    context = InvestigationContext(run_id=run.run_id)

    call_count = 0
    art_path = tmp_path / "outputs/investigations/inv_tamper_test/artifacts/validate_result.json"

    def mock_validate_handler(ctx: InvestigationContext, r: InvestigationRun) -> list[ArtifactRef]:
        nonlocal call_count
        call_count += 1
        art_path.parent.mkdir(parents=True, exist_ok=True)
        content = f'{{"validation": "call_{call_count}"}}'.encode("utf-8")
        art_path.write_bytes(content)
        digest = hashlib.sha256(content).hexdigest()

        return [
            ArtifactRef(
                artifact_id=f"art_val_{r.run_id}",
                type=ArtifactType.JSON_METADATA.value,
                format="application/json",
                path=f"outputs/investigations/{r.run_id}/artifacts/validate_result.json",
                size_bytes=len(content),
                sha256=digest,
                producer_stage="VALIDATE",
            )
        ]

    # First execution: handler invoked
    att1 = engine.execute_stage(run, context, "VALIDATE", mock_validate_handler)
    assert call_count == 1
    assert att1.status == StageExecutionStatus.COMPLETED.value

    # Tamper with the artifact content on disk (modify bytes)
    tampered_content = b'{"validation": "tampered_bytes"}'
    art_path.write_bytes(tampered_content)

    # Second execution: engine must detect SHA-256 mismatch and refuse to skip
    att2 = engine.execute_stage(run, context, "VALIDATE", mock_validate_handler)
    assert call_count == 2  # Re-executed due to tampered artifact!
    assert att2.status == StageExecutionStatus.COMPLETED.value
    # Artifact on disk must now be restored to fresh valid content
    assert run.artifacts[0].verify_integrity(tmp_path) is True


# ===========================================================================
# 13. Tampered Artifact Crash Recovery Fail-Closed
# ===========================================================================


def test_recovery_detects_tampered_artifact_and_fails_closed(tmp_path: Path):
    """Verify that crash recovery detects corrupted/tampered artifacts and fails closed."""
    store = InvestigationRunStore(base_dir=tmp_path / "investigations", repo_root=tmp_path)

    run = InvestigationRun(
        run_id="inv_recovery_tamper_001",
        request=InvestigationRunRequest(analysis_mode="DEMO"),
    )

    # Persist completed stage and valid artifact
    out_rel = "outputs/investigations/inv_recovery_tamper_001/artifacts/validate_out.json"
    out_full = tmp_path / out_rel
    out_full.parent.mkdir(parents=True, exist_ok=True)
    payload = b'{"stage": "VALIDATE"}'
    out_full.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()

    art = ArtifactRef(
        artifact_id="art_val_001",
        type=ArtifactType.JSON_METADATA.value,
        format="application/json",
        path=out_rel,
        size_bytes=len(payload),
        sha256=digest,
        producer_stage="VALIDATE",
    )
    run.add_artifact(art)
    run.set_stage_status("VALIDATE", StageExecutionStatus.COMPLETED)
    store.save_run(run)

    # Verify recovery initially reports can_resume = True
    rec_clean = store.determine_recovery_state(run)
    assert rec_clean.can_resume is True

    # Tamper with artifact on disk
    out_full.write_bytes(b'{"corrupted": true}')

    # Store must detect corrupted artifact
    rec_tampered = store.determine_recovery_state(run)
    assert rec_tampered.can_resume is False
    assert "art_val_001" in rec_tampered.corrupted_artifacts

    # prepare_resume must fail closed
    resumed_run, next_stage = store.prepare_resume(run)
    assert next_stage is None
    assert resumed_run.overall_status == InvestigationRunStatus.FAILED.value
    assert resumed_run.error["code"] == "CANNOT_RESUME"


# ===========================================================================
# 14. Missing Required Handler Semantics
# ===========================================================================


def test_missing_required_handler_fails_closed_and_prevents_false_success(tmp_path: Path):
    """Verify that omitting a handler for a required stage prevents false success."""
    store = InvestigationRunStore(base_dir=tmp_path / "investigations", repo_root=tmp_path)
    engine = InvestigationEngine(store=store, repo_root=tmp_path)

    run = InvestigationRun(
        run_id="inv_missing_handler_test",
        request=InvestigationRunRequest(analysis_mode="DEMO"),
    )
    ctx = InvestigationContext(run_id=run.run_id)

    # Provide VALIDATE and PREPROCESS, but omit INGEST
    def mock_validate(c: InvestigationContext, r: InvestigationRun) -> list[ArtifactRef]:
        return []

    def mock_preprocess(c: InvestigationContext, r: InvestigationRun) -> list[ArtifactRef]:
        return []

    handlers = {
        "VALIDATE": mock_validate,
        # INGEST is intentionally omitted!
        "PREPROCESS": mock_preprocess,
    }

    # Executing the pipeline must fail closed when PREPROCESS cannot run due to unmet INGEST dependency
    with pytest.raises(InvestigationEngineError, match="Unmet dependencies for 'PREPROCESS'"):
        engine.run_pipeline(run, ctx, handlers)

    assert run.overall_status == InvestigationRunStatus.FAILED.value
    assert run.stages["PREPROCESS"].status == StageExecutionStatus.FAILED.value
