# Ocean Sentinel — Phase 7B: Event Spine & Stream Telemetry Specification

**Document Version**: 1.0.0
**Status**: VERIFIED & COMPLETE
**Milestone**: Phase 7B (Event Spine & Stream Telemetry)
**Parent Architecture**: [Phase 7A Investigation Run Kernel & Durable Scientific Execution Spine](PHASE_7A_INVESTIGATION_RUN_KERNEL.md)

---

## 1. Overview & Architectural Intent

Phase 7B establishes an observable, durable, and reconnectable event spine on top of the completed Phase 7A investigation execution kernel.

The event architecture transforms an `InvestigationRun` into an observable stream of structured events, exposing:
- Durable lifecycle and stage execution transitions.
- Artifact integrity registration events.
- Provenance and scientific safety boundary blocking events.
- Real-time Server-Sent Events (SSE) streaming with reconnect and replay capability.
- Live operational telemetry without fabricating uncomputed scientific metrics.

```
       Operator / HTTP Client
                 │
                 ▼
          FastAPI Router
      (/api/v1/investigations)
                 │
                 ▼
         InvestigationEngine
                 │
     ┌───────────┴───────────┐
     ▼                       ▼
InvestigationRun       DurableEventLog
 (Domain State)     (outputs/.../events.jsonl)
     │                       │
     ▼                       ▼
InvestigationStore        EventBus (In-Process Hub)
 (Disk Manifest)             │
                             ├────► SSE Streaming Client (GET /.../events)
                             ├────► Telemetry Observers
                             └────► Future Reflection / UI
```

### Core Architectural Invariants

1. **Events are Observability History, Not Authorization**:
   An event indicates that an execution step occurred or was evaluated. An event does not grant permission to execute.
2. **Canonical State Precedence**:
   - Manifest / Domain State (`InvestigationRun`) = Authoritative current run state.
   - Event Log (`events.jsonl`) = Append-only historical event stream.
   - Safety Boundary (`AuthorizationState`) = Authoritative execution gate.
3. **Strict Write Order**:
   State update is persisted to canonical run storage first, durably appended to `events.jsonl` second, and broadcast to in-process subscribers third. Subscribers can never observe an event that cannot be replayed from durable disk.
4. **Local-First, No External Broker**:
   Phase 7B uses synchronous local filesystem persistence and in-process async event dispatching without external dependencies (no Redis, Kafka, Celery, or Postgres).

---

## 2. Event Domain Model

The canonical event shape is implemented in `src/ocean_sentinel/orchestration/events.py` as `InvestigationEvent`:

| Field | Type | Description |
| :--- | :--- | :--- |
| `event_id` | `str` | Globally unique identifier (`evt_{run_id}_{seq:06d}_{random_hex}`). |
| `run_id` | `str` | Associated investigation run identifier. |
| `sequence` | `int` | Strictly monotonically increasing positive integer (1, 2, 3...) per run. |
| `event_type` | `str` | Strict canonical enum member (`InvestigationEventType`). |
| `occurred_at` | `str` | ISO 8601 UTC timestamp of event generation. |
| `schema_version` | `str` | Schema version (`"1.0.0"`). |
| `stage_id` | `Optional[str]` | Optional associated DAG stage (e.g. `VALIDATE`, `INFER`). |
| `attempt_id` | `Optional[str]` | Optional associated stage attempt identifier. |
| `producer` | `str` | Producer component (default: `"InvestigationEngine"`). |
| `severity` | `str` | Event severity (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`). |
| `payload` | `Dict[str, Any]` | JSON-serializable structured metadata payload. |
| `correlation_id` | `Optional[str]` | Optional correlation token. |

### Canonical Event Vocabulary

- **Run Lifecycle**: `RUN_CREATED`, `RUN_STARTED`, `RUN_VALIDATED`, `RUN_COMPLETED`, `RUN_FAILED`, `RUN_SUSPENDED`, `RUN_RESUMED`, `RUN_CANCELLED`
- **Stage Lifecycle**: `STAGE_QUEUED`, `STAGE_STARTED`, `STAGE_PROGRESS`, `STAGE_COMPLETED`, `STAGE_FAILED`, `STAGE_SKIPPED`, `STAGE_INTERRUPTED`, `STAGE_BLOCKED`
- **Artifact Events**: `ARTIFACT_DISCOVERED`, `ARTIFACT_REGISTERED`, `ARTIFACT_VALIDATED`, `ARTIFACT_CORRUPTED`
- **Provenance / Safety**: `PROVENANCE_BLOCKED`, `SOURCE_UNAVAILABLE`
- **Recovery Events**: `RECOVERY_STARTED`, `RECOVERY_COMPLETED`, `RECOVERY_BLOCKED`
- **Telemetry**: `TELEMETRY_SNAPSHOT`

---

## 3. Durable Event Log (`events.jsonl`)

The durable event log is managed by `DurableEventLog` in `src/ocean_sentinel/orchestration/event_log.py`.

- **Storage Path**: `outputs/investigations/{run_id}/events.jsonl`
- **Format**: Structured JSON Lines (one valid JSON object per line).
- **Sequence Monotonicity**: Sequences start at 1 and increment strictly by 1.
- **Process Restart Continuity**: Upon process restart, `_initialize_log()` parses the log file, determines the highest durable sequence number, and ensures all subsequent events continue monotonically.
- **Trailing Partial Line Remediation**: If an abrupt crash terminates the process mid-write, partial or corrupted trailing records are cleanly removed, preserving all valid preceding events and rewinding the sequence cursor to the last valid line.

---

## 4. In-Process Event Bus & Subscriber Hub

The in-process broadcast mechanism is implemented in `src/ocean_sentinel/orchestration/event_bus.py`:

- **Run Isolation**: Subscriptions are scoped by `run_id`. Events from run A are never leaked to subscribers of run B.
- **Non-Blocking Execution**: Event emission utilizes non-blocking `put_nowait` on bounded subscriber queues (`maxsize=1000`). If a queue overflows or is closed, the event is safely dropped for that subscriber without blocking pipeline execution.
- **Subscriber Exception Isolation**: Synchronous callback exceptions are caught and logged; broken subscribers cannot disrupt stage execution.
- **Clean Unsubscription**: Subscribers disconnect cleanly, releasing queue resources.

---

## 5. Server-Sent Events (SSE) & Reconnect Semantics

Exposed via `GET /api/v1/investigations/{run_id}/events`.

### SSE Protocol Framing

Events are framed according to the W3C Server-Sent Events standard:
```
id: 3
event: STAGE_COMPLETED
data: {"event_id": "evt_...", "run_id": "inv_...", "sequence": 3, "payload": {...}}

: keepalive
```

### Reconnection via `Last-Event-ID`

A client that disconnects can resume streaming by providing the `Last-Event-ID` header (or `?after_sequence=N` query parameter):
1. **Replay Phase**: The server reads `events.jsonl` and streams all historical events with sequence `> N`.
2. **Live Phase**: If the run is active, the server subscribes the client to the `EventBus` and forwards newly arriving events in real time.
3. **Termination**: If the run is in a terminal state (`COMPLETED`, `FAILED`, `READY_FOR_DETECTION`, `BLOCKED`), the stream closes gracefully after history replay.

---

## 6. Live Operational Telemetry

Exposed via `GET /api/v1/investigations/{run_id}/telemetry` and REST history endpoint `GET /api/v1/investigations/{run_id}/events/history`.

The telemetry snapshot provides:
- Current overall run status and current active stage.
- Progress metrics: completed stages count, pending stages count, total stages.
- Active stage execution duration and stage attempt numbers.
- Total durable event count and timestamp of the latest event.
- Content-verified artifact counts.
- Scientific safety status (`scientific_execution_authorized: false`).
- Zero fabricated scientific performance metrics or synthetic confidence scores.

---

## 7. Security & Information Leakage Guardrails

`assert_no_event_secrets_or_host_paths` strictly scans event payloads prior to persistence and publication:
- **Prohibited Secrets**: Rejects tokens, API keys, passwords, client secrets, bearer credentials, and credential dictionaries.
- **Prohibited Host Paths**: Rejects Windows drive letters (`C:\`, `D:\`) and Unix root user paths (`/home/`, `/Users/`), enforcing clean relative path representations.

---

## 8. Scientific Safety Firewall

In accordance with standing governance invariants:
- `SCIENTIFIC_EXECUTION_AUTHORIZED = False`
- `INFER` and `INTERPRET` stages remain gated fail-closed.
- Gated stages emit `STAGE_BLOCKED` (with reason `"Scientific execution gated (EXECUTION_AUTHORIZED = False)"`), and **never** emit `STAGE_STARTED`.
- Zero model inference forward passes, zero training updates, zero holdout access.
