# Ocean Sentinel — Phase 7A: Investigation Run Kernel & Durable Scientific Execution Spine

**Status**: IMPLEMENTED & TESTED (Phase 7A)  
**Safety Boundary**: FAIL-CLOSED (`EXECUTION_AUTHORIZED = False`)  
**Authority**: Human operator approval remains final authority.

---

## 1. Executive Overview & Purpose

Phase 7A extends the Ocean Sentinel operational foundation (Phases 6A–6C) into a durable, graph-aware, recoverable investigation execution spine. It introduces:

1. **`InvestigationRun` Domain Kernel**: A serializable, filesystem-backed domain root managing investigation lifecycles, structured requests, stage execution states, artifact references, and attempt records.
2. **`InvestigationContext`**: Canonical, run-wide state binding governing authorities, authorization state, canonical model checkpoint identity, and corrected CDSE replication protocol.
3. **Explicit Typed `ScientificDAG`**: A 10-stage directed acyclic graph defining stage versions, deterministic flags, retry policies, dependencies, and scientific execution gates.
4. **`ArtifactRef` Domain Abstraction**: First-class, immutable artifact references binding SHA-256 digests, physical relative paths, MIME formats, and producer stages. SHA-256 hashing verifies content integrity; it does not provide digital signatures, non-repudiation, or legal authenticity.
5. **Stage Attempts & Idempotency Fingerprinting**: Config- and protocol-derived SHA-256 stage fingerprints preventing accidental duplicate artifact materialization on restart or retry.
6. **Durable Crash Recovery**: State-machine recovery determining the earliest safely resumable stage and rolling back ungracefully interrupted attempts without redundant stage re-execution.
7. **Phase 6C Backward Compatibility**: Seamless conversion of Phase 6C `AcquisitionJobManifest` instances into full `InvestigationRun` representations.

---

## 2. Storage Layout & Filesystem Conventions

Investigation runs are persisted in dedicated, run-scoped directories under `outputs/investigations/<run_id>/`:

```
outputs/
  investigations/
    <run_id>/
      manifest.json       # Canonical run metadata, request, status, recovery state
      stages.json         # Per-stage execution state, timestamps, fingerprints
      attempts.json       # Comprehensive historical attempt audit ledger
      artifacts.json      # Registered first-class ArtifactRef records
      artifacts/          # Stage-materialized local output artifacts
      evidence/           # Derived investigation evidence payloads
      logs/               # Run-specific execution telemetry and logs
```

### Atomic Persistence Semantics & Concurrency Scope
All state files (`manifest.json`, `stages.json`, etc.) are written via atomic replacement: data is written to a temporary sibling file (`.<filename>.<pid>.tmp`) and atomically renamed into place using `os.replace`. Atomic replacement (`replace()`) prevents partial target-file replacement under supported filesystem replacement semantics. This design has been verified for sequential execution and process-restart recovery; concurrent multi-process worker locking is out of scope for Phase 7A and deferred by design.

---

## 3. Scientific DAG & Canonical Stages

The execution spine operates against an explicit, typed `ScientificDAG` containing 10 canonical stages:

```
            [ VALIDATE ] ──────────────────────┐
                 │                             │
                 ▼                             │
             [ INGEST ]                        ▼
                 │                          [ DRIFT ]
                 ▼                             │
           [ PREPROCESS ]                      │
            │          │                       ▼
            │          ▼                    [ AIS ]
            │     [ TEMPORAL ]                 │
            │          │                       │
            │          └──────────────┐        │
            │                         ▼        ▼
            │                    [ FUSION ] ◄──┘
            ▼                         │
        [ INFER ] (Gated)             ▼
            │                     [ EXPORT ]
            ▼
      [ INTERPRET ] (Gated)
```

| Stage ID | Dependencies | Gating Status | Retry Policy | Description |
| :--- | :--- | :--- | :--- | :--- |
| `VALIDATE` | `[]` | Operational (Un-gated) | Safe, max 2 | AOI polygon, datetime window, parameter checks |
| `INGEST` | `[VALIDATE]` | Operational (Un-gated) | Safe, max 2 | Copernicus CDSE STAC search & authenticated Process API download |
| `PREPROCESS` | `[INGEST]` | Operational (Un-gated) | Safe, max 1 | SAR Mapping A channel contract (`Ch0=VH`, `Ch1=VV`), radiometric normalization |
| `INFER` | `[PREPROCESS]` | **SCIENTIFIC GATED** | Gated, 0 retries | Neural network forward pass on canonical model checkpoint |
| `INTERPRET` | `[INFER]` | **SCIENTIFIC GATED** | Gated, 0 retries | Confidence contouring & slick candidate extraction |
| `TEMPORAL` | `[PREPROCESS]` | Operational (Un-gated) | Safe, max 1 | Multi-temporal SAR difference geometry & persistence tracking |
| `DRIFT` | `[VALIDATE]` | Operational (Un-gated) | Safe, max 1 | Metocean Lagrangian backward/forward trajectory modeling |
| `AIS` | `[VALIDATE]` | Operational (Un-gated) | Safe, max 2 | Historical AIS vessel encounter correlation |
| `FUSION` | `[DRIFT, AIS, TEMPORAL]` | Operational (Un-gated) | Safe, max 1 | Multi-source hypothesis synthesis |
| `EXPORT` | `[FUSION]` | Operational (Un-gated) | Safe, max 1 | Evidence packaging and investigation report generation |

---

## 4. Stage Attempts & Idempotency Fingerprinting

Every stage execution records a granular `StageAttempt`:

- `attempt_id`: Deterministic token `att_{stage}_{timestamp}_{hex}`
- `attempt_number`: Monotonically increasing attempt index
- `status`: `RUNNING`, `COMPLETED`, `FAILED`, `INTERRUPTED`, `BLOCKED`, or `SKIPPED`
- `input_hashes`: Map of input artifact IDs to SHA-256 digests
- `config_fingerprint`: Deterministic SHA-256 digest of:
  $$\text{SHA-256}(\text{stage\_id} \mathbin{\Vert} \text{protocol\_sha256} \mathbin{\Vert} \text{model\_sha256} \mathbin{\Vert} \text{sorted\_input\_hashes} \mathbin{\Vert} \text{norm\_config})$$

### Duplicate Artifact Prevention
Prior to executing a stage handler, the engine checks whether the stage already completed with an identical configuration fingerprint and valid on-disk artifacts. If verified, the completed attempt is reused and the handler is not re-invoked.

---

## 5. Durable Crash Recovery Semantics

When recovering an investigation run after process termination or ungraceful shutdown:

1. **State Reconstruction**: The run, its stages, attempts, and registered artifact references are loaded from disk.
2. **On-Disk Integrity Verification**: All registered output artifacts for completed stages are verified against their SHA-256 hashes on disk. If any artifact is missing or corrupted, the stage is marked `FAILED`.
3. **Interrupted Stage Remediation**: If a stage was in `RUNNING` status when the process crashed, its latest attempt is marked `INTERRUPTED`, uncompleted output references are reset, and the stage status reverts to `PENDING`.
4. **Earliest Resumable Stage Calculation**: The store evaluates the DAG against completed stages and prioritizes the interrupted stage (or earliest unsatisfied ready stage).
5. **No Redundant Re-execution**: Completed stages with verified artifacts are preserved; only pending and resumable stages are scheduled.

---

## 6. Scientific Safety Firewall

In strict compliance with repository governance:

- `SCIENTIFIC_EXECUTION_AUTHORIZED = False`
- `MODEL_INFERENCE_AUTHORIZED = False`
- `HOLDOUT_ACCESS_AUTHORIZED = False`
- `PART_III_ACCESS_AUTHORIZED = False`
- `THRESHOLD_TUNING_AUTHORIZED = False`

The investigation engine executes operational and data preparation stages (`VALIDATE`, `INGEST`, `PREPROCESS`, `TEMPORAL`, etc.) and halts fail-closed at the boundary before `INFER`, transitioning the investigation run to terminal state `READY_FOR_DETECTION`. No neural network forward passes, training weight updates, or holdout evaluations are executed.
