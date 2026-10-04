"""Test Suite for Phase 7B: Event Spine & Stream Telemetry.

Covers:
1. Typed InvestigationEvent domain model, schema, and SSE serialization
2. Strict security validation: prohibition of raw secrets in event payloads
3. Strict security validation: prohibition of host absolute filesystem paths
4. DurableEventLog append, sequence monotonicity, and flush verification
5. DurableEventLog restart recovery and sequence continuity
6. DurableEventLog trailing corrupted/partial record remediation
7. DurableEventLog replay cursor (Last-Event-ID semantic support)
8. In-process EventBus run-scoped isolation and multi-subscriber delivery
9. In-process EventBus non-blocking subscriber exception isolation
10. InvestigationEngine canonical event emission during pipeline execution
11. Scientific safety firewall: gated stages emit STAGE_BLOCKED (never STAGE_STARTED)
12. Controlled crash and recovery event continuity and monotonically increasing sequence
13. Operational telemetry snapshot generation and emission
14. Phase 6C AcquisitionJob backward compatibility and missing log handling
15. FastAPI SSE endpoint framing, keepalive, and Last-Event-ID replay
16. FastAPI Investigation REST endpoints (run state, telemetry, event history)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
from unittest import mock
import pytest
from fastapi.testclient import TestClient

from ocean_sentinel.api.app import create_app
from ocean_sentinel.orchestration.dag import (
    DAGNode,
    ScientificDAG,
    create_canonical_scientific_dag,
)
from ocean_sentinel.orchestration.engine import (
    InvestigationEngine,
    ScientificGateViolationError,
)
from ocean_sentinel.orchestration.event_bus import (
    EventBus,
    EventSubscription,
    get_global_event_bus,
    set_global_event_bus,
)
from ocean_sentinel.orchestration.event_log import (
    DurableEventLog,
    DurableEventLogError,
)
from ocean_sentinel.orchestration.events import (
    EVENT_FORBIDDEN_SECRET_KEYS,
    EventSeverity,
    InvestigationEvent,
    InvestigationEventType,
    assert_no_event_secrets_or_host_paths,
)
from ocean_sentinel.orchestration.investigation_context import (
    AuthorizationState,
    InvestigationContext,
)
from ocean_sentinel.orchestration.investigation_run import (
    ArtifactRef,
    ArtifactType,
    ContentStatus,
    InvestigationRun,
    InvestigationRunRequest,
    InvestigationRunStatus,
    InvestigationStageState,
    ProvenanceClass,
    StageAttempt,
    StageExecutionStatus,
)
from ocean_sentinel.orchestration.investigation_store import InvestigationRunStore


# ===========================================================================
# 1. Event Model & Security Assertions
# ===========================================================================


def test_event_schema_and_serialization():
    """Verify InvestigationEvent schema, JSON serialization, and SSE framing."""
    evt = InvestigationEvent.create(
        run_id="inv_test_001",
        sequence=1,
        event_type=InvestigationEventType.RUN_CREATED,
        payload={"request_id": "req_123", "mode": "PHYSICAL"},
        stage_id=None,
        producer="TestRunner",
        severity=EventSeverity.INFO,
    )

    assert evt.run_id == "inv_test_001"
    assert evt.sequence == 1
    assert evt.event_type == "RUN_CREATED"
    assert evt.schema_version == "1.0"
    assert evt.payload == {"request_id": "req_123", "mode": "PHYSICAL"}

    # Dict roundtrip
    d = evt.to_dict()
    assert d["event_id"] == evt.event_id
    restored = InvestigationEvent.from_dict(d)
    assert restored.event_id == evt.event_id
    assert restored.sequence == evt.sequence
    assert restored.payload == evt.payload

    # JSON roundtrip
    json_str = evt.to_json()
    from_json_evt = InvestigationEvent.from_json(json_str)
    assert from_json_evt.event_id == evt.event_id

    # SSE formatting
    sse_text = evt.to_sse()
    assert f"id: {evt.sequence}\n" in sse_text
    assert f"event: {evt.event_type}\n" in sse_text
    assert "data: {" in sse_text
    assert sse_text.endswith("\n\n")


def test_event_security_strict_prohibition_of_secrets():
    """Verify that sensitive credentials cannot enter event payloads."""
    for key in ["password", "client_secret", "access_token", "api_key", "bearer_token"]:
        with pytest.raises(ValueError, match="Forbidden credential key"):
            InvestigationEvent.create(
                run_id="inv_sec_001",
                sequence=1,
                event_type=InvestigationEventType.RUN_STARTED,
                payload={key: "leaked_super_secret"},
            )

    # Nested secret key
    with pytest.raises(ValueError, match="Forbidden credential key"):
        InvestigationEvent.create(
            run_id="inv_sec_001",
            sequence=1,
            event_type=InvestigationEventType.STAGE_PROGRESS,
            payload={"auth": {"access_token": "secret_abc"}},
        )


def test_event_security_strict_prohibition_of_host_paths():
    """Verify that host-specific absolute paths are rejected while relative paths pass."""
    # Absolute Windows path
    with pytest.raises(ValueError, match="Host-specific absolute filesystem path"):
        InvestigationEvent.create(
            run_id="inv_sec_002",
            sequence=1,
            event_type=InvestigationEventType.ARTIFACT_REGISTERED,
            payload={"output_path": "D:\\Projects\\ocean-sentinel\\data\\raw\\test.tif"},
        )

    # Absolute Unix path
    with pytest.raises(ValueError, match="Host-specific absolute filesystem path"):
        InvestigationEvent.create(
            run_id="inv_sec_002",
            sequence=1,
            event_type=InvestigationEventType.ARTIFACT_REGISTERED,
            payload={"output_path": "/Users/developer/ocean-sentinel/data/raw/test.tif"},
        )

    # Relative path succeeds
    evt = InvestigationEvent.create(
        run_id="inv_sec_002",
        sequence=1,
        event_type=InvestigationEventType.ARTIFACT_REGISTERED,
        payload={"output_path": "data/raw/acquisitions/test.tif"},
    )
    assert evt.payload["output_path"] == "data/raw/acquisitions/test.tif"


# ===========================================================================
# 2. Durable Event Log & Persistence
# ===========================================================================


def test_durable_event_log_append_and_sequence_monotonicity(tmp_path: Path):
    """Verify append-only event logging, monotonic sequence enforcement, and replay."""
    log_file = tmp_path / "inv_log_001" / "events.jsonl"
    log = DurableEventLog(log_file)

    assert log.current_sequence == 0

    e1 = log.emit(InvestigationEventType.RUN_CREATED, {"name": "Test"})
    assert e1.sequence == 1
    assert log.current_sequence == 1

    e2 = log.emit(InvestigationEventType.STAGE_STARTED, {"stage": "VALIDATE"}, stage_id="VALIDATE")
    assert e2.sequence == 2
    assert log.current_sequence == 2

    # Sequence violation rejection
    bad_evt = InvestigationEvent.create(
        run_id="inv_log_001",
        sequence=2,  # Duplicate sequence
        event_type=InvestigationEventType.STAGE_COMPLETED,
    )
    with pytest.raises(DurableEventLogError, match="Sequence violation"):
        log.append(bad_evt)


def test_durable_event_log_restart_recovery(tmp_path: Path):
    """Verify that restarting the process reloads the exact latest sequence and continues monotonically."""
    log_file = tmp_path / "inv_restart_001" / "events.jsonl"
    log1 = DurableEventLog(log_file)
    log1.emit(InvestigationEventType.RUN_CREATED)
    log1.emit(InvestigationEventType.RUN_STARTED)
    log1.emit(InvestigationEventType.STAGE_STARTED, stage_id="VALIDATE")
    assert log1.current_sequence == 3

    # Simulate restart by creating a new instance
    log2 = DurableEventLog(log_file)
    assert log2.current_sequence == 3

    # Next emit increments cleanly
    e4 = log2.emit(InvestigationEventType.STAGE_COMPLETED, stage_id="VALIDATE")
    assert e4.sequence == 4
    assert log2.current_sequence == 4

    replayed = log2.replay()
    assert len(replayed) == 4
    assert [e.sequence for e in replayed] == [1, 2, 3, 4]


def test_durable_event_log_trailing_corruption_remediation(tmp_path: Path):
    """Verify that partial/corrupted trailing log records are remediated without losing prior valid records."""
    log_file = tmp_path / "inv_corrupt_001" / "events.jsonl"
    log = DurableEventLog(log_file)
    log.emit(InvestigationEventType.RUN_CREATED)
    log.emit(InvestigationEventType.RUN_STARTED)
    assert log.current_sequence == 2

    # Simulate abrupt power-off / crash mid-write
    with open(log_file, "a", encoding="utf-8") as f:
        f.write('{"event_id": "evt_partial", "run_id": "inv_corrupt_001", "sequence": 3, "event_type": "STAGE_STA\n')

    # Reopen log: should recover valid events and remediate corruption
    recovered_log = DurableEventLog(log_file)
    assert recovered_log.corrupted_records_count == 1
    assert recovered_log.current_sequence == 2

    events = recovered_log.replay()
    assert len(events) == 2
    assert [e.sequence for e in events] == [1, 2]

    # Can cleanly append new events after recovery
    e3 = recovered_log.emit(InvestigationEventType.STAGE_STARTED, stage_id="VALIDATE")
    assert e3.sequence == 3
    assert recovered_log.current_sequence == 3


def test_durable_event_log_replay_with_cursor(tmp_path: Path):
    """Verify cursor-based replay for Last-Event-ID SSE support."""
    log_file = tmp_path / "inv_replay_001" / "events.jsonl"
    log = DurableEventLog(log_file)

    for i in range(1, 6):
        log.emit(InvestigationEventType.STAGE_PROGRESS, {"step": i})

    assert log.current_sequence == 5

    # Replay after sequence 2
    replayed = log.replay(after_sequence=2)
    assert len(replayed) == 3
    assert [e.sequence for e in replayed] == [3, 4, 5]

    # Replay after latest sequence returns empty list
    assert log.replay(after_sequence=5) == []

    # Replay with limit
    limited = log.replay(after_sequence=1, limit=2)
    assert len(limited) == 2
    assert [e.sequence for e in limited] == [2, 3]


# ===========================================================================
# 3. In-Process EventBus Hub
# ===========================================================================


def test_event_bus_isolation_and_delivery():
    """Verify that the EventBus dispatches events to matching run subscriptions only."""
    bus = EventBus()
    sub_run1 = bus.subscribe("run_1")
    sub_run2 = bus.subscribe("run_2")

    e1 = InvestigationEvent.create(run_id="run_1", sequence=1, event_type=InvestigationEventType.RUN_STARTED)
    e2 = InvestigationEvent.create(run_id="run_2", sequence=1, event_type=InvestigationEventType.RUN_STARTED)

    bus.publish(e1)
    bus.publish(e2)

    # run_1 subscriber queue should only contain e1
    assert not sub_run1.queue.empty()
    received_run1 = sub_run1.queue.get_nowait()
    assert received_run1.run_id == "run_1"
    assert sub_run1.queue.empty()

    # run_2 subscriber queue should only contain e2
    assert not sub_run2.queue.empty()
    received_run2 = sub_run2.queue.get_nowait()
    assert received_run2.run_id == "run_2"
    assert sub_run2.queue.empty()

    bus.unsubscribe(sub_run1)
    bus.unsubscribe(sub_run2)


def test_event_bus_broken_subscriber_does_not_block_engine():
    """Verify that subscriber errors do not propagate to or crash the event publisher."""
    bus = EventBus()

    def faulty_callback(event):
        raise RuntimeError("Broken subscriber explodes!")

    received_events = []

    def healthy_callback(event):
        received_events.append(event)

    bus.subscribe_sync("run_fault", faulty_callback)
    bus.subscribe_sync("run_fault", healthy_callback)

    evt = InvestigationEvent.create(run_id="run_fault", sequence=1, event_type=InvestigationEventType.RUN_STARTED)

    # Publishing must not raise despite faulty_callback exception
    bus.publish(evt)

    assert len(received_events) == 1
    assert received_events[0].sequence == 1


# ===========================================================================
# 4. Investigation Engine Integration & Scientific Safety
# ===========================================================================


def test_engine_emits_canonical_events_during_pipeline_execution(tmp_path: Path):
    """Verify that InvestigationEngine emits canonical lifecycle and stage events."""
    store = InvestigationRunStore(base_dir=tmp_path / "investigations", repo_root=tmp_path)
    engine = InvestigationEngine(store=store, repo_root=tmp_path)

    run = InvestigationRun(
        run_id="inv_engine_evt_01",
        request=InvestigationRunRequest(),
    )
    store.save_run(run)
    context = InvestigationContext(run_id=run.run_id)

    # Handler for VALIDATE stage creating an artifact
    def validate_handler(ctx, r):
        art_path = store.get_artifacts_dir(r.run_id) / "validated_spec.json"
        content = b'{"status": "ok"}'
        art_path.write_bytes(content)
        digest = hashlib.sha256(content).hexdigest()
        rel_path = str(art_path.relative_to(tmp_path)).replace("\\", "/")
        return [
            ArtifactRef(
                artifact_id="art_val_spec",
                type=ArtifactType.JSON_METADATA.value,
                format="application/json",
                path=rel_path,
                size_bytes=len(content),
                sha256=digest,
                producer_stage="VALIDATE",
            )
        ]

    handlers = {"VALIDATE": validate_handler}

    engine.run_pipeline(run, context, handlers)

    event_log = store.get_event_log(run.run_id)
    events = event_log.replay()
    event_types = [e.event_type for e in events]

    assert "RUN_STARTED" in event_types
    assert "STAGE_STARTED" in event_types
    assert "ARTIFACT_REGISTERED" in event_types
    assert "STAGE_COMPLETED" in event_types

    # Ensure sequences are strictly increasing 1..N
    assert [e.sequence for e in events] == list(range(1, len(events) + 1))


def test_scientific_firewall_emits_stage_blocked_never_started(tmp_path: Path):
    """Verify that reaching scientific stages fail-closed emits STAGE_BLOCKED and never STAGE_STARTED."""
    store = InvestigationRunStore(base_dir=tmp_path / "investigations", repo_root=tmp_path)
    engine = InvestigationEngine(store=store, repo_root=tmp_path)

    run = InvestigationRun(
        run_id="inv_sci_firewall_01",
        request=InvestigationRunRequest(),
    )
    store.save_run(run)
    context = InvestigationContext(run_id=run.run_id)

    # Only supply operational handlers
    handlers = {
        "VALIDATE": lambda ctx, r: [],
        "INGEST": lambda ctx, r: [],
        "PREPROCESS": lambda ctx, r: [],
        "TEMPORAL": lambda ctx, r: [],
    }

    # Pipeline will execute up to PREPROCESS, then encounter INFER (gated)
    completed_run = engine.run_pipeline(run, context, handlers)

    assert completed_run.overall_status == InvestigationRunStatus.READY_FOR_DETECTION.value

    event_log = store.get_event_log(run.run_id)
    events = event_log.replay()
    event_types = [e.event_type for e in events]

    # Verify STAGE_BLOCKED was emitted
    assert "STAGE_BLOCKED" in event_types
    blocked_event = next(e for e in events if e.event_type == "STAGE_BLOCKED")
    assert blocked_event.stage_id == "INFER"
    assert "Scientific" in blocked_event.payload.get("gate_reason", "")

    # STAGE_STARTED must NEVER exist for INFER
    infer_started_events = [e for e in events if e.event_type == "STAGE_STARTED" and e.stage_id == "INFER"]
    assert len(infer_started_events) == 0, "Scientific stage INFER must never emit STAGE_STARTED"


def test_controlled_crash_and_recovery_event_continuity(tmp_path: Path):
    """Verify crash interruption and recovery emits RECOVERY_STARTED/COMPLETED and preserves sequence continuity."""
    store = InvestigationRunStore(base_dir=tmp_path / "investigations", repo_root=tmp_path)
    engine = InvestigationEngine(store=store, repo_root=tmp_path)

    run = InvestigationRun(
        run_id="inv_crash_evt_01",
        request=InvestigationRunRequest(),
    )
    store.save_run(run)
    context = InvestigationContext(run_id=run.run_id)

    handlers = {
        "VALIDATE": lambda ctx, r: [],
        "INGEST": lambda ctx, r: [],
    }

    # Interrupt before INGEST
    interrupted_run = engine.run_pipeline(run, context, handlers, interrupt_before_stage="INGEST")
    assert interrupted_run.overall_status == InvestigationRunStatus.SUSPENDED.value

    event_log_pre = store.get_event_log(run.run_id)
    seq_before_resume = event_log_pre.current_sequence
    assert seq_before_resume > 0

    # Resume pipeline
    resumed_run = engine.resume_pipeline(interrupted_run, context, handlers)

    event_log_post = store.get_event_log(run.run_id)
    events = event_log_post.replay()
    event_types = [e.event_type for e in events]

    assert "STAGE_INTERRUPTED" in event_types
    assert "RUN_SUSPENDED" in event_types
    assert "RECOVERY_STARTED" in event_types
    assert "RECOVERY_COMPLETED" in event_types
    assert "RUN_RESUMED" in event_types

    # Ensure strictly increasing sequence throughout the entire crash & resume lifecycle
    sequences = [e.sequence for e in events]
    assert sequences == list(range(1, len(events) + 1))


def test_operational_telemetry_generation(tmp_path: Path):
    """Verify structured operational telemetry generation without exposing unverified scientific metrics."""
    store = InvestigationRunStore(base_dir=tmp_path / "investigations", repo_root=tmp_path)
    engine = InvestigationEngine(store=store, repo_root=tmp_path)

    run = InvestigationRun(
        run_id="inv_telemetry_01",
        request=InvestigationRunRequest(),
    )
    store.save_run(run)

    # Emit telemetry event
    evt = engine.emit_telemetry_snapshot(run)
    assert evt.event_type == InvestigationEventType.TELEMETRY_SNAPSHOT.value
    payload = evt.payload

    assert payload["run_id"] == "inv_telemetry_01"
    assert payload["overall_status"] == InvestigationRunStatus.REQUESTED.value
    assert payload["total_stages"] == 10
    assert payload["scientific_execution_authorized"] is False
    assert "confidence_score" not in payload, "Fake confidence scores must never be exposed"


# ===========================================================================
# 5. FastAPI Endpoints & Server-Sent Events (SSE)
# ===========================================================================


def test_api_investigation_run_and_telemetry_endpoints(tmp_path: Path):
    """Verify GET /api/v1/investigations/{run_id} and /telemetry endpoints."""
    from ocean_sentinel.api.routes import set_investigation_engine, set_investigation_store

    store = InvestigationRunStore(base_dir=tmp_path / "investigations", repo_root=tmp_path)
    engine = InvestigationEngine(store=store, repo_root=tmp_path)
    set_investigation_store(store)
    set_investigation_engine(engine)

    run = InvestigationRun(
        run_id="inv_api_test_01",
        request=InvestigationRunRequest(),
    )
    store.save_run(run)

    app = create_app()
    client = TestClient(app)

    # 1. State endpoint
    resp = client.get("/api/v1/investigations/inv_api_test_01")
    assert resp.status_code == 200
    data = resp.json()
    assert data["run_id"] == "inv_api_test_01"
    assert data["overall_status"] == "REQUESTED"

    # 2. Telemetry endpoint
    t_resp = client.get("/api/v1/investigations/inv_api_test_01/telemetry")
    assert t_resp.status_code == 200
    t_data = t_resp.json()
    assert t_data["run_id"] == "inv_api_test_01"
    assert t_data["total_stages"] == 10
    assert t_data["scientific_execution_authorized"] is False


def test_api_investigation_event_history_and_sse_replay(tmp_path: Path):
    """Verify GET /api/v1/investigations/{run_id}/events/history and SSE replay."""
    from ocean_sentinel.api.routes import set_investigation_engine, set_investigation_store

    store = InvestigationRunStore(base_dir=tmp_path / "investigations", repo_root=tmp_path)
    engine = InvestigationEngine(store=store, repo_root=tmp_path)
    set_investigation_store(store)
    set_investigation_engine(engine)

    run = InvestigationRun(
        run_id="inv_sse_test_01",
        overall_status=InvestigationRunStatus.READY_FOR_DETECTION.value,
        request=InvestigationRunRequest(),
    )
    store.save_run(run)

    # Emit historical events
    log = store.get_event_log(run.run_id)
    log.emit(InvestigationEventType.RUN_CREATED)
    log.emit(InvestigationEventType.RUN_STARTED)
    log.emit(InvestigationEventType.STAGE_STARTED, stage_id="VALIDATE")
    log.emit(InvestigationEventType.STAGE_COMPLETED, stage_id="VALIDATE")
    log.emit(InvestigationEventType.STAGE_BLOCKED, stage_id="INFER", severity=EventSeverity.WARNING)

    app = create_app()
    client = TestClient(app)

    # 1. History endpoint
    h_resp = client.get("/api/v1/investigations/inv_sse_test_01/events/history?after_sequence=2")
    assert h_resp.status_code == 200
    h_data = h_resp.json()
    assert h_data["total_returned"] == 3
    assert [e["sequence"] for e in h_data["events"]] == [3, 4, 5]

    # 2. SSE endpoint with Last-Event-ID replay cursor
    sse_resp = client.get(
        "/api/v1/investigations/inv_sse_test_01/events",
        headers={"Last-Event-ID": "2"},
    )
    assert sse_resp.status_code == 200
    assert "text/event-stream" in sse_resp.headers["content-type"]
    sse_body = sse_resp.text

    assert "id: 3\n" in sse_body
    assert "id: 4\n" in sse_body
    assert "id: 5\n" in sse_body
    assert "id: 1\n" not in sse_body
    assert "id: 2\n" not in sse_body
    assert "event: STAGE_BLOCKED\n" in sse_body


def test_phase6c_compatibility_and_missing_event_log(tmp_path: Path):
    """Verify backward compatibility when an investigation or legacy job has no events.jsonl."""
    from ocean_sentinel.api.routes import set_investigation_engine, set_investigation_store
    from ocean_sentinel.orchestration.acquisition_job import (
        AcquisitionJobManifest,
        AcquisitionJobStatus,
    )

    store = InvestigationRunStore(base_dir=tmp_path / "investigations", repo_root=tmp_path)
    engine = InvestigationEngine(store=store, repo_root=tmp_path)
    set_investigation_store(store)
    set_investigation_engine(engine)

    # 1. Convert Phase 6C manifest to an InvestigationRun
    acq_manifest = AcquisitionJobManifest(
        job_id="acq_legacy_20261001_001",
        status=AcquisitionJobStatus.READY_FOR_DETECTION.value,
        request_params={
            "bbox": [-12.5, -77.5, -12.0, -77.0],
            "investigation_label": "Legacy Phase 6C Acquisition",
        },
        acquisition_id="S1A_IW_LEGACY_001",
        provider="copernicus_cdse",
        content_sha256="c41fbf7bed0102f9fd29cee4df752c4496b6c281632852b41f124ac7d3c9d8ee",
        evidence_id="ev_legacy_001",
        execution_authorized=False,
    )
    run = InvestigationRun.from_acquisition_manifest(acq_manifest)
    store.save_run(run)

    events_file = store.get_events_path(run.run_id)
    assert not events_file.exists()

    # Replay on uninitialized log must return empty list without fabricating historical events
    log = store.get_event_log(run.run_id)
    assert log.get_latest_sequence() == 0
    assert log.replay() == []

    # API endpoints must handle missing event log gracefully
    app = create_app()
    client = TestClient(app)

    h_resp = client.get(f"/api/v1/investigations/{run.run_id}/events/history")
    assert h_resp.status_code == 200
    assert h_resp.json()["events"] == []
    assert h_resp.json()["total_returned"] == 0

    # SSE endpoint with no events terminates cleanly for terminal run
    sse_resp = client.get(f"/api/v1/investigations/{run.run_id}/events")
    assert sse_resp.status_code == 200

    # Now emit first event: begins cleanly from sequence 1
    new_evt = log.emit(InvestigationEventType.RUN_RESUMED)
    assert new_evt.sequence == 1
    assert log.get_latest_sequence() == 1
    assert events_file.exists()


def test_sse_reconnect_replay_handoff_race_gapless_delivery(tmp_path: Path):
    """Verify that an event committed concurrently during replay/live handoff is gaplessly delivered exactly once."""
    from ocean_sentinel.api.routes import set_investigation_engine, set_investigation_store

    store = InvestigationRunStore(base_dir=tmp_path / "investigations", repo_root=tmp_path)
    engine = InvestigationEngine(store=store, repo_root=tmp_path)
    set_investigation_store(store)
    set_investigation_engine(engine)

    run = InvestigationRun(
        run_id="inv_race_01",
        overall_status=InvestigationRunStatus.RUNNING.value,
        request=InvestigationRunRequest(),
    )
    store.save_run(run)
    log = store.get_event_log(run.run_id)

    # Initial historical events 1 and 2
    log.emit(InvestigationEventType.RUN_CREATED)
    log.emit(InvestigationEventType.RUN_STARTED)

    # Hook into event_log.replay: while replay is occurring, simulate a concurrent event emission!
    orig_replay = log.replay

    def mock_replay(*args, **kwargs):
        res = orig_replay(*args, **kwargs)
        # Emit concurrent event 3 to disk and broadcast to event bus
        engine.emit_event(run, InvestigationEventType.STAGE_STARTED, stage_id="VALIDATE")
        # Explicitly close the active subscription after concurrent event broadcast
        # to cleanly terminate client stream observation without declaring run terminal
        for s in engine.event_bus._async_subscribers.get(run.run_id, []):
            s.close()
        return res

    with mock.patch.object(log, "replay", side_effect=mock_replay):
        app = create_app()
        client = TestClient(app)
        # Reconnect asking for events after seq 1 using streaming response
        with client.stream("GET", f"/api/v1/investigations/{run.run_id}/events", headers={"Last-Event-ID": "1"}) as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]
            body = "\n".join(resp.iter_lines()) + "\n"

    # Verify event 2 (from replay) and event 3 (from concurrent handoff) are present exactly once
    assert "id: 2\n" in body
    assert "id: 3\n" in body
    assert body.count("id: 2\n") == 1
    assert body.count("id: 3\n") == 1
    assert "id: 1\n" not in body


def test_event_append_failure_suppresses_broadcast_and_fails_closed(tmp_path: Path):
    """Verify that an event persistence failure suppresses broadcast to the EventBus and fails closed."""
    from ocean_sentinel.orchestration.engine import InvestigationEngineError

    store = InvestigationRunStore(base_dir=tmp_path / "investigations", repo_root=tmp_path)
    engine = InvestigationEngine(store=store, repo_root=tmp_path)

    run = InvestigationRun(
        run_id="inv_fail_closed_01",
        overall_status=InvestigationRunStatus.RUNNING.value,
        request=InvestigationRunRequest(),
    )
    store.save_run(run)

    # Register an active subscriber
    sub = engine.event_bus.subscribe(run.run_id)

    # Patch event_log.emit to simulate a disk write error
    log = store.get_event_log(run.run_id)
    with mock.patch.object(log, "emit", side_effect=IOError("Simulated disk write failure")):
        with pytest.raises(InvestigationEngineError) as exc_info:
            engine.emit_event(run, InvestigationEventType.STAGE_STARTED, stage_id="VALIDATE")
        assert "Durable event persistence failed" in str(exc_info.value)

    # Verify EventBus received ZERO events (no phantom broadcast)
    assert sub.queue.empty(), "Phantom event was leaked to subscriber queue despite disk failure!"


def test_event_bus_overflow_resynchronizes_from_durable_disk_log(tmp_path: Path):
    """Verify that subscriber queue overflow automatically resynchronizes all missed events from disk."""
    from ocean_sentinel.api.routes import set_investigation_engine, set_investigation_store

    store = InvestigationRunStore(base_dir=tmp_path / "investigations", repo_root=tmp_path)
    engine = InvestigationEngine(store=store, repo_root=tmp_path)
    set_investigation_store(store)
    set_investigation_engine(engine)

    run = InvestigationRun(
        run_id="inv_overflow_01",
        overall_status=InvestigationRunStatus.READY_FOR_DETECTION.value,
        request=InvestigationRunRequest(),
    )
    store.save_run(run)

    # Subscribe with tiny queue of size 2
    sub = engine.event_bus.subscribe(run.run_id, max_queue_size=2)

    # Emit 5 events through the engine
    for stage in ["VALIDATE", "DISCOVER", "ACQUIRE", "PERSIST", "PREFLIGHT"]:
        engine.emit_event(run, InvestigationEventType.STAGE_COMPLETED, stage_id=stage)

    # Confirm that subscriber queue overflowed
    assert sub.has_overflowed is True
    # The queue can hold at most 2 items
    assert sub.queue.qsize() <= 2

    # Consuming the SSE stream triggers automatic disk resynchronization
    app = create_app()
    client = TestClient(app)
    resp = client.get(f"/api/v1/investigations/{run.run_id}/events")
    assert resp.status_code == 200
    body = resp.text

    # All 5 events must be delivered sequentially without any gap
    for seq in [1, 2, 3, 4, 5]:
        assert f"id: {seq}\n" in body
        assert body.count(f"id: {seq}\n") == 1
