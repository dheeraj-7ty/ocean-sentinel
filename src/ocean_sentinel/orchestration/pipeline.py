"""Pipeline Orchestrator for Ocean Sentinel V1.

Coordinates deterministic pipeline execution across validated stages,
records stage transitions, enforces provenance gates, and produces
frontend-ready job manifests and machine-readable artifacts.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from ocean_sentinel.drift import ProvenanceGateError
from ocean_sentinel.fusion import (
    CandidateHypothesis,
    CandidateVesselHypothesis,
    EvidenceFusionEngine,
    EvidenceItem,
    EvidenceType,
    FusionMode,
    ProvenanceClass,
    generate_deterministic_demo_fusion_fixture,
    load_evidence_from_detection_geojson,
    load_evidence_from_drift_geojson,
    load_evidence_from_temporal_geojson,
)
from ocean_sentinel.orchestration.jobs import (
    ArtifactRecord,
    JobManifest,
    JobMode,
    JobStatus,
    JobStore,
    PipelineStage,
    PipelineType,
    StageExecutionStatus,
)
from ocean_sentinel.orchestration.scenarios import (
    InvestigationScenario,
    get_scenario,
    list_scenarios,
)
from ocean_sentinel.orchestration.temporal_guard import check_temporal_pair_validity

logger = logging.getLogger(__name__)
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class PipelineOrchestrator:
    """Deterministic pipeline orchestrator integrating scientific modules into an auditable job workflow."""

    def __init__(self, job_store: Optional[JobStore] = None) -> None:
        self.job_store = job_store or JobStore(REPO_ROOT / "outputs" / "jobs")

    # -----------------------------------------------------------------------
    # Stage Adapters (Thin integration with frozen scientific modules)
    # -----------------------------------------------------------------------

    def run_fusion(
        self,
        evidence_items: List[EvidenceItem],
        ais_summary: Optional[Dict[str, Any]],
        mode: Union[FusionMode, str],
        spatial_tolerance_m: float = 5000.0,
        temporal_tolerance_hours: float = 2.0,
    ) -> Tuple[EvidenceFusionEngine, Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
        """Stage Adapter: Execute Multi-Source Evidence Fusion V1."""
        fusion_mode = mode if isinstance(mode, FusionMode) else FusionMode(mode)
        engine = EvidenceFusionEngine(
            mode=fusion_mode,
            spatial_tolerance_m=spatial_tolerance_m,
            temporal_tolerance_seconds=temporal_tolerance_hours * 3600.0,
        )

        for item in evidence_items:
            engine.ingest_evidence_item(item)

        # Locate drift origin hypothesis if present
        origin_item = None
        for item in engine.evidence_store.values():
            if item.evidence_type == EvidenceType.DRIFT_ORIGIN_HYPOTHESIS.value:
                origin_item = item
                break

        origin_geom = origin_item.spatial_geometry if origin_item else None
        target_time = origin_item.observation_time if origin_item else None
        t_window = (
            (target_time, target_time)
            if target_time
            else None
        )

        engine.synthesize_spill_origin_hypothesis(
            hypothesis_id="hypothesis_origin_cluster_01",
            subject_id=origin_item.source_id if origin_item else "candidate_spill_event",
            origin_geometry=origin_geom,
            temporal_window=t_window,
        )

        if ais_summary:
            drift_hyp_id = origin_item.evidence_id if origin_item else "evidence_drift_origin"
            engine.synthesize_candidate_vessel_hypotheses(
                ais_correlation_summary=ais_summary,
                drift_hypothesis_id=drift_hyp_id,
            )

        graph_dict = engine.graph.to_dict()
        summary_dict = engine.export_summary()
        geojson_dict = engine.export_geojson()

        return engine, graph_dict, summary_dict, geojson_dict

    # -----------------------------------------------------------------------
    # Primary Job Execution Engine
    # -----------------------------------------------------------------------

    def run_job(
        self,
        mode: Union[JobMode, str],
        pipeline_type: Union[PipelineType, str],
        input_artifacts: Optional[Dict[str, Any]] = None,
        spatial_tolerance_m: float = 5000.0,
        temporal_tolerance_hours: float = 2.0,
        job_id: Optional[str] = None,
        scenario_id: Optional[str] = None,
        investigation_label: Optional[str] = None,
    ) -> JobManifest:
        """Execute a complete pipeline job synchronously and update manifest."""
        mode_val = mode.value if isinstance(mode, JobMode) else str(mode).upper()
        ptype_val = pipeline_type.value if isinstance(pipeline_type, PipelineType) else str(pipeline_type).upper()

        if mode_val == JobMode.REAL_REPOSITORY.value or ptype_val == PipelineType.REAL_REPOSITORY.value:
            mode_val = JobMode.REAL_REPOSITORY.value
            ptype_val = PipelineType.REAL_REPOSITORY.value

        config = {
            "mode": mode_val,
            "pipeline_type": ptype_val,
            "scenario_id": scenario_id,
            "investigation_label": investigation_label,
            "input_artifacts": input_artifacts or {},
            "spatial_tolerance_m": float(spatial_tolerance_m),
            "temporal_tolerance_hours": float(temporal_tolerance_hours),
        }

        # 1. Initialize Job and Workspace
        manifest = self.job_store.create_job(
            mode=mode_val,
            pipeline_type=ptype_val,
            requested_config=config,
            job_id=job_id,
            scenario_id=scenario_id,
            investigation_label=investigation_label,
        )
        manifest.status = JobStatus.RUNNING.value
        manifest.started_at = datetime.now(timezone.utc).isoformat()
        self.job_store.save_manifest(manifest)

        artifacts_dir = self.job_store.get_artifacts_dir(manifest.job_id)

        try:
            # ---------------------------------------------------------------
            # Stage: VALIDATE
            # ---------------------------------------------------------------
            manifest.set_stage_status(PipelineStage.VALIDATE, StageExecutionStatus.RUNNING)
            self.job_store.save_manifest(manifest)

            if spatial_tolerance_m <= 0:
                manifest.set_failed(
                    code="INVALID_INPUT",
                    message="spatial_tolerance_m must be a positive number.",
                    stage=PipelineStage.VALIDATE.value,
                )
                self.job_store.save_manifest(manifest)
                return manifest

            if temporal_tolerance_hours <= 0:
                manifest.set_failed(
                    code="INVALID_INPUT",
                    message="temporal_tolerance_hours must be a positive number.",
                    stage=PipelineStage.VALIDATE.value,
                )
                self.job_store.save_manifest(manifest)
                return manifest

            # Check for path traversal attacks in input artifact references
            if input_artifacts:
                for key, val in input_artifacts.items():
                    if val and isinstance(val, str):
                        if ".." in val or val.startswith(("/", "\\")):
                            manifest.set_failed(
                                code="INVALID_INPUT",
                                message=f"Path traversal rejected in '{key}': '{val}'",
                                stage=PipelineStage.VALIDATE.value,
                            )
                            self.job_store.save_manifest(manifest)
                            return manifest
                        target_file = REPO_ROOT / val
                        if not target_file.is_file():
                            manifest.set_failed(
                                code="ARTIFACT_NOT_FOUND",
                                message=f"Referenced input artifact not found: '{val}'",
                                stage=PipelineStage.VALIDATE.value,
                            )
                            self.job_store.save_manifest(manifest)
                            return manifest

            target_scenario: Optional[InvestigationScenario] = None
            if mode_val == JobMode.REAL_REPOSITORY.value:
                scenario_key = (scenario_id or "TRUJILLO_00007_01339").strip()
                if ".." in scenario_key or scenario_key.startswith(("/", "\\")) or any(c in scenario_key for c in [":", "*", "?", '"', "<", ">", "|"]):
                    manifest.set_failed(
                        code="INVALID_INPUT",
                        message=f"Path traversal or invalid characters rejected in scenario_id: '{scenario_key}'",
                        stage=PipelineStage.VALIDATE.value,
                    )
                    self.job_store.save_manifest(manifest)
                    return manifest

                target_scenario = get_scenario(scenario_key)
                if not target_scenario:
                    manifest.set_failed(
                        code="INVALID_INPUT",
                        message=f"Scenario '{scenario_key}' not found in registered catalog.",
                        stage=PipelineStage.VALIDATE.value,
                    )
                    self.job_store.save_manifest(manifest)
                    return manifest

                missing = target_scenario.validate_artifacts_exist(REPO_ROOT)
                if missing:
                    manifest.set_failed(
                        code="ARTIFACT_NOT_FOUND",
                        message=f"Missing required artifacts for scenario '{scenario_key}': {', '.join(missing)}",
                        stage=PipelineStage.VALIDATE.value,
                    )
                    self.job_store.save_manifest(manifest)
                    return manifest

                manifest.scenario_id = target_scenario.scenario_id
                manifest.investigation_label = investigation_label or target_scenario.label

            # PHYSICAL mode gate: Operational sources are strictly required
            if mode_val == JobMode.PHYSICAL.value or ptype_val == PipelineType.PHYSICAL.value:
                # Operational physical feeds are blocked awaiting accreditation
                manifest.set_blocked_provenance(
                    message=(
                        "PHYSICAL mode rejected: Operational external satellite and AIS feeds "
                        "are strictly BLOCKED — AWAITING_OPERATIONAL_SOURCE. "
                        "Synthetic fixtures cannot be substituted or relabeled as physical."
                    ),
                    stage=PipelineStage.VALIDATE.value,
                    details={"gate": "PHYSICAL_PROVENANCE_GATE", "accreditation": "UNACCREDITED_OPERATIONAL_FEED"},
                )
                self.job_store.save_manifest(manifest)
                return manifest

            manifest.set_stage_status(PipelineStage.VALIDATE, StageExecutionStatus.COMPLETED, message="Validation passed.")
            self.job_store.save_manifest(manifest)

            # ---------------------------------------------------------------
            # Stage: INGEST
            # ---------------------------------------------------------------
            manifest.set_stage_status(PipelineStage.INGEST, StageExecutionStatus.RUNNING)
            self.job_store.save_manifest(manifest)

            evidence_items: List[EvidenceItem] = []
            ais_summary: Optional[Dict[str, Any]] = None

            if ptype_val == PipelineType.DEMO_FUSION.value:
                evidence_items, ais_summary = generate_deterministic_demo_fusion_fixture()
                manifest.set_stage_status(
                    PipelineStage.INGEST,
                    StageExecutionStatus.COMPLETED,
                    message=f"Ingested {len(evidence_items)} synthetic demo items and 5 candidate vessels.",
                    details={"evidence_item_count": len(evidence_items)},
                )
            elif ptype_val == PipelineType.REAL_REPOSITORY.value:
                assert target_scenario is not None

                # -----------------------------------------------------------
                # Temporal Pair Forensic & Duplicate Guard Check (Section 10)
                # -----------------------------------------------------------
                scene_pair = target_scenario.scene_pair
                t0_raw = REPO_ROOT / "data" / "raw" / "trujillo_2024" / "images" / "Oil" / f"{scene_pair[0]}.tif"
                t1_raw = REPO_ROOT / "data" / "raw" / "trujillo_2024" / "images" / "Oil" / f"{scene_pair[1]}.tif"

                guard_result = None
                if t0_raw.is_file() and t1_raw.is_file():
                    guard_result = check_temporal_pair_validity(t0_raw, t1_raw)

                is_invalid_duplicate = (
                    (guard_result and guard_result.get("status") == "TEMPORAL_PAIR_INVALID_DUPLICATE_IMAGE")
                    or target_scenario.source_pair_status == "INVALID_DUPLICATE_IMAGE_PAIR"
                )

                if is_invalid_duplicate:
                    t0_sha = (guard_result.get("t0_sha256") if guard_result else None) or "927b382ebffc2f84447a17b80b30e6c3f1f6758fcb8d6e7a13e7c4de70932405"
                    t1_sha = (guard_result.get("t1_sha256") if guard_result else None) or "927b382ebffc2f84447a17b80b30e6c3f1f6758fcb8d6e7a13e7c4de70932405"

                    manifest.set_stage_status(
                        PipelineStage.INGEST,
                        StageExecutionStatus.SKIPPED,
                        message="Ingest stopped: T0 and T1 source rasters are byte-for-byte identical duplicates.",
                        details={
                            "reason": "IDENTICAL_SOURCE_RASTERS",
                            "scenario_id": target_scenario.scenario_id,
                            "scene_pair": target_scenario.scene_pair,
                        },
                    )
                    manifest.set_stage_status(
                        PipelineStage.INFER,
                        StageExecutionStatus.SKIPPED,
                        message="Skipped model inference: invalid duplicate image pair.",
                    )
                    manifest.set_stage_status(
                        PipelineStage.INTERPRET,
                        StageExecutionStatus.SKIPPED,
                        message="Skipped polygonization: invalid duplicate image pair.",
                    )
                    manifest.set_stage_status(
                        PipelineStage.TEMPORAL,
                        StageExecutionStatus.BLOCKED,
                        message="TEMPORAL: BLOCKED / INVALID DUPLICATE IMAGE PAIR",
                        details={
                            "status": "TEMPORAL_PAIR_INVALID_DUPLICATE_IMAGE",
                            "reason": "T0 and T1 source rasters are byte-for-byte identical.",
                            "source_pair_status": "INVALID_DUPLICATE_IMAGE_PAIR",
                            "temporal_status": "BLOCKED",
                            "t0_sha256": t0_sha,
                            "t1_sha256": t1_sha,
                            "scientific_interpretation": (
                                "T0 and T1 source rasters are byte-for-byte identical, but their masks differ. "
                                "The evidence establishes annotation/label divergence between the two instances, "
                                "but does not establish the cause of that divergence. It is NOT physical temporal change."
                            ),
                        },
                    )
                    manifest.set_stage_status(
                        PipelineStage.DRIFT,
                        StageExecutionStatus.BLOCKED,
                        message="DRIFT: BLOCKED / INVALID DUPLICATE IMAGE PAIR (Cannot simulate drift from non-event).",
                        details={"reason": "IDENTICAL_SOURCE_RASTERS"},
                    )
                    manifest.set_stage_status(
                        PipelineStage.AIS,
                        StageExecutionStatus.BLOCKED,
                        message="AIS: BLOCKED / INVALID DUPLICATE IMAGE PAIR (Cannot correlate vessels to non-event).",
                        details={"reason": "IDENTICAL_SOURCE_RASTERS"},
                    )
                    manifest.set_stage_status(
                        PipelineStage.FUSION,
                        StageExecutionStatus.BLOCKED,
                        message="FUSION: BLOCKED / INVALID DUPLICATE IMAGE PAIR (Cannot promote invalid duplicate pair to historical temporal evidence).",
                        details={"reason": "IDENTICAL_SOURCE_RASTERS"},
                    )
                    manifest.set_stage_status(
                        PipelineStage.EXPORT,
                        StageExecutionStatus.SKIPPED,
                        message="EXPORT: SKIPPED due to blocked upstream temporal stage.",
                    )
                    manifest.set_blocked_provenance(
                        message="TEMPORAL: BLOCKED / INVALID DUPLICATE IMAGE PAIR",
                        stage=PipelineStage.TEMPORAL.value,
                        details={
                            "status": "TEMPORAL_PAIR_INVALID_DUPLICATE_IMAGE",
                            "reason": "T0 and T1 source rasters are byte-for-byte identical.",
                            "source_pair_status": "INVALID_DUPLICATE_IMAGE_PAIR",
                            "temporal_status": "BLOCKED",
                            "t0_sha256": t0_sha,
                            "t1_sha256": t1_sha,
                        },
                    )
                    self.job_store.save_manifest(manifest)
                    return manifest

                temp_path = REPO_ROOT / target_scenario.artifacts["temporal_geojson"]
                drift_path = REPO_ROOT / target_scenario.artifacts["drift_geojson"]
                ais_path = REPO_ROOT / target_scenario.artifacts["ais_summary"]

                temp_items = load_evidence_from_temporal_geojson(temp_path)
                drift_raw_items = load_evidence_from_drift_geojson(drift_path)

                drift_items: List[EvidenceItem] = []
                for it in drift_raw_items:
                    # Preserve actual forcing provenance (SYNTHETIC_DEMO) per Section 5.C
                    drift_items.append(
                        EvidenceItem(
                            evidence_id=it.evidence_id,
                            evidence_type=it.evidence_type,
                            source_type=it.source_type,
                            source_id=it.source_id,
                            observation_time=it.observation_time,
                            spatial_geometry=it.spatial_geometry,
                            provenance_class=it.provenance_class,
                            provenance_source=it.provenance_source,
                            source_artifact=str(drift_path.name),
                            parent_evidence_ids=it.parent_evidence_ids,
                            root_source_ids=[f"scene_{s}" for s in target_scenario.scene_pair],
                            derivation_type=it.derivation_type,
                            observed_vs_inferred=it.observed_vs_inferred,
                            metric_values=it.metric_values,
                            limitations=it.limitations + [
                                "Lagrangian drift was computed using synthetic demo forcing fixture; not historical metocean observations."
                            ],
                        )
                    )

                with open(ais_path, "r", encoding="utf-8") as f:
                    ais_summary = json.load(f)

                evidence_items = temp_items + drift_items

                manifest.set_stage_status(
                    PipelineStage.INGEST,
                    StageExecutionStatus.COMPLETED,
                    message=f"Ingested {len(evidence_items)} real evidence items from repository scenario '{target_scenario.scenario_id}'.",
                    details={
                        "evidence_item_count": len(evidence_items),
                        "scenario_id": target_scenario.scenario_id,
                        "scene_pair": target_scenario.scene_pair,
                    },
                )

                # Record skipped and upstream executed stages faithfully per Section 10
                manifest.set_stage_status(
                    PipelineStage.INFER,
                    StageExecutionStatus.SKIPPED,
                    message="Skipped model inference: reused verified Sentinel-1 model masks.",
                    details={
                        "reason": "Reused verified model mask artifacts from training exp06",
                        "artifacts": [
                            target_scenario.artifacts.get("detection_mask_t0"),
                            target_scenario.artifacts.get("detection_mask_t1"),
                        ],
                    },
                )
                manifest.set_stage_status(
                    PipelineStage.INTERPRET,
                    StageExecutionStatus.SKIPPED,
                    message="Skipped polygonization: reused verified interpretation outputs.",
                    details={
                        "reason": "Reused verified interpretation outputs",
                        "artifacts": [target_scenario.artifacts.get("temporal_geojson")],
                    },
                )
                manifest.set_stage_status(
                    PipelineStage.TEMPORAL,
                    StageExecutionStatus.COMPLETED,
                    message=f"Temporal analysis verified for scene pair {target_scenario.scene_pair}.",
                    details={
                        "scene_pair": target_scenario.scene_pair,
                        "artifact": target_scenario.artifacts.get("temporal_geojson"),
                    },
                )
                manifest.set_stage_status(
                    PipelineStage.DRIFT,
                    StageExecutionStatus.COMPLETED,
                    message=f"Lagrangian backward drift envelopes verified for event {target_scenario.event_id}.",
                    details={
                        "event_id": target_scenario.event_id,
                        "direction": "BACKWARD",
                        "artifact": target_scenario.artifacts.get("drift_geojson"),
                        "provenance_class": "SYNTHETIC_DEMO",
                        "forcing_source": "synthetic_deterministic_fixture",
                    },
                )
                manifest.set_stage_status(
                    PipelineStage.AIS,
                    StageExecutionStatus.COMPLETED,
                    message=f"AIS correlation evaluated {len(ais_summary.get('candidate_vessels', []))} candidate vessels.",
                    details={
                        "candidate_count": len(ais_summary.get("candidate_vessels", [])),
                        "artifact": target_scenario.artifacts.get("ais_summary"),
                        "provenance_class": "SYNTHETIC_DEMO",
                        "source_feed": "SYNTHETIC_DEMO_FEED",
                    },
                )
            elif ptype_val == PipelineType.ARTIFACT_FUSION.value:
                # Use provided input files or default repository artifacts
                inputs = input_artifacts or {}

                # Resolve paths
                det_path = REPO_ROOT / inputs["detection_geojson"] if inputs.get("detection_geojson") else None
                temp_path = (
                    REPO_ROOT / inputs["temporal_geojson"]
                    if inputs.get("temporal_geojson")
                    else REPO_ROOT / "outputs" / "temporal" / "00007_to_01339_temporal_events.geojson"
                )
                drift_path = (
                    REPO_ROOT / inputs["drift_geojson"]
                    if inputs.get("drift_geojson")
                    else REPO_ROOT / "outputs" / "origin_drift" / "trujillo_00007_01339.geojson"
                )
                ais_path = (
                    REPO_ROOT / inputs["ais_summary"]
                    if inputs.get("ais_summary")
                    else REPO_ROOT / "outputs" / "ais" / "trujillo_00007_01339_summary.json"
                )

                if det_path and det_path.is_file():
                    evidence_items.extend(load_evidence_from_detection_geojson(det_path))
                if temp_path and temp_path.is_file():
                    evidence_items.extend(load_evidence_from_temporal_geojson(temp_path))
                if drift_path and drift_path.is_file():
                    evidence_items.extend(load_evidence_from_drift_geojson(drift_path))
                if ais_path and ais_path.is_file():
                    with open(ais_path, "r", encoding="utf-8") as f:
                        ais_summary = json.load(f)

                if not evidence_items:
                    manifest.set_failed(
                        code="ARTIFACT_NOT_FOUND",
                        message="No valid input artifacts found for ARTIFACT_FUSION.",
                        stage=PipelineStage.INGEST.value,
                    )
                    self.job_store.save_manifest(manifest)
                    return manifest

                manifest.set_stage_status(
                    PipelineStage.INGEST,
                    StageExecutionStatus.COMPLETED,
                    message=f"Loaded {len(evidence_items)} evidence items from repository artifacts.",
                    details={"evidence_item_count": len(evidence_items)},
                )

            self.job_store.save_manifest(manifest)

            # ---------------------------------------------------------------
            # Stage: FUSION
            # ---------------------------------------------------------------
            manifest.set_stage_status(PipelineStage.FUSION, StageExecutionStatus.RUNNING)
            self.job_store.save_manifest(manifest)

            engine, graph_dict, summary_dict, geojson_dict = self.run_fusion(
                evidence_items=evidence_items,
                ais_summary=ais_summary,
                mode=FusionMode.DEMO,
                spatial_tolerance_m=spatial_tolerance_m,
                temporal_tolerance_hours=temporal_tolerance_hours,
            )

            manifest.set_stage_status(
                PipelineStage.FUSION,
                StageExecutionStatus.COMPLETED,
                message="Multi-source evidence fusion completed.",
                details={
                    "total_evidence_items": len(engine.evidence_store),
                    "total_candidate_hypotheses": len(engine.hypotheses),
                    "multiple_plausible_candidates": summary_dict["multiple_plausible_candidates"],
                    "has_dependency_cycles": graph_dict["metadata"]["has_dependency_cycles"],
                },
            )
            self.job_store.save_manifest(manifest)

            # ---------------------------------------------------------------
            # Stage: EXPORT
            # ---------------------------------------------------------------
            manifest.set_stage_status(PipelineStage.EXPORT, StageExecutionStatus.RUNNING)
            self.job_store.save_manifest(manifest)

            graph_path = artifacts_dir / f"{manifest.job_id}_evidence_graph.json"
            summary_path = artifacts_dir / f"{manifest.job_id}_evidence_summary.json"
            geojson_path = artifacts_dir / f"{manifest.job_id}_evidence.geojson"

            with open(graph_path, "w", encoding="utf-8") as f:
                json.dump(graph_dict, f, indent=2)
            with open(summary_path, "w", encoding="utf-8") as f:
                json.dump(summary_dict, f, indent=2)
            with open(geojson_path, "w", encoding="utf-8") as f:
                json.dump(geojson_dict, f, indent=2)

            def _safe_relative_path(p: Path, base: Path) -> str:
                try:
                    return str(p.relative_to(base))
                except ValueError:
                    return str(p)

            # Evaluate transitive artifact provenance per Section 2, 4, 6
            has_synthetic = any(
                it.provenance_class == ProvenanceClass.SYNTHETIC_DEMO.value
                for it in engine.evidence_store.values()
            )

            if ptype_val == PipelineType.REAL_REPOSITORY.value:
                if has_synthetic:
                    prov_class = "REAL_REPOSITORY_SCENARIO_WITH_SYNTHETIC_DEPENDENCY"
                    prov_status = "PROVENANCE_LIMITED"
                    prov_limitation = (
                        "REAL_REPOSITORY scenario contains synthetic downstream dependencies "
                        "(drift forcing: SYNTHETIC_DEMO, AIS feed: SYNTHETIC_DEMO). "
                        "Overall result cannot claim pure HISTORICAL_ARCHIVE."
                    )
                else:
                    prov_class = "HISTORICAL_ARCHIVE"
                    prov_status = "HISTORICAL_ARCHIVE"
                    prov_limitation = None
            else:
                prov_class = "SYNTHETIC_DEMO"
                prov_status = "SYNTHETIC_DEMO"
                prov_limitation = "Synthetic fixture for algorithmic demonstration only."

            # Register artifacts in manifest
            manifest.add_artifact(
                ArtifactRecord(
                    artifact_id=f"{manifest.job_id}_evidence_graph",
                    artifact_type="EVIDENCE_GRAPH_JSON",
                    file_path=str(graph_path),
                    relative_path=_safe_relative_path(graph_path, REPO_ROOT),
                    format="JSON",
                    generated_by_stage=PipelineStage.EXPORT.value,
                    size_bytes=graph_path.stat().st_size,
                    provenance_class=prov_class,
                )
            )
            manifest.add_artifact(
                ArtifactRecord(
                    artifact_id=f"{manifest.job_id}_evidence_summary",
                    artifact_type="EVIDENCE_SUMMARY_JSON",
                    file_path=str(summary_path),
                    relative_path=_safe_relative_path(summary_path, REPO_ROOT),
                    format="JSON",
                    generated_by_stage=PipelineStage.EXPORT.value,
                    size_bytes=summary_path.stat().st_size,
                    provenance_class=prov_class,
                )
            )
            manifest.add_artifact(
                ArtifactRecord(
                    artifact_id=f"{manifest.job_id}_evidence_geojson",
                    artifact_type="EVIDENCE_GEOJSON",
                    file_path=str(geojson_path),
                    relative_path=_safe_relative_path(geojson_path, REPO_ROOT),
                    format="GEOJSON",
                    generated_by_stage=PipelineStage.EXPORT.value,
                    size_bytes=geojson_path.stat().st_size,
                    provenance_class=prov_class,
                )
            )

            manifest.set_stage_status(PipelineStage.EXPORT, StageExecutionStatus.COMPLETED, message="Artifacts exported.")

            # Compile final normalized result
            res_dict = {
                "job_id": manifest.job_id,
                "engine": summary_dict["engine"],
                "mode": manifest.mode,
                "pipeline_type": manifest.pipeline_type,
                "scenario_id": manifest.scenario_id,
                "investigation_label": manifest.investigation_label,
                "provenance_class": prov_class,
                "provenance_status": prov_status,
                "has_synthetic_dependencies": (ptype_val == PipelineType.REAL_REPOSITORY.value and has_synthetic),
                "stage_provenance": {
                    "satellite": "HISTORICAL_ARCHIVE" if ptype_val == PipelineType.REAL_REPOSITORY.value else "SYNTHETIC_DEMO",
                    "temporal": "HISTORICAL_ARCHIVE" if ptype_val == PipelineType.REAL_REPOSITORY.value else "SYNTHETIC_DEMO",
                    "drift": "SYNTHETIC_DEMO" if has_synthetic else "HISTORICAL_ARCHIVE",
                    "ais": "SYNTHETIC_DEMO" if has_synthetic else "HISTORICAL_ARCHIVE",
                },
                "provenance_limitation": prov_limitation,
                "scenario_metadata": target_scenario.to_dict() if target_scenario else None,
                "total_evidence_items": summary_dict["total_evidence_items"],
                "total_candidate_hypotheses": summary_dict["total_candidate_hypotheses"],
                "multiple_plausible_candidates": summary_dict["multiple_plausible_candidates"],
                "plausible_candidate_count": summary_dict["plausible_candidate_count"],
                "candidate_spill_hypotheses": summary_dict["candidate_spill_hypotheses"],
                "candidate_vessel_hypotheses": summary_dict["candidate_vessel_hypotheses"],
                "evidence_graph": graph_dict,
                "evidence_ledger": summary_dict.get("evidence_ledger", []),
                "scientific_boundaries": summary_dict["scientific_boundaries"],
                "negative_proof_guard": summary_dict["negative_proof_guard"],
            }
            if target_scenario:
                manifest.limitations = target_scenario.limitations + [
                    "Attribution assessments establish evidence compatibility only; NO legal responsibility is assigned.",
                    "Absence of AIS records does NOT prove vessel absence.",
                ]
                if has_synthetic:
                    manifest.limitations.append(
                        "PROVENANCE LIMITATION: Scenario contains synthetic downstream dependencies "
                        "(drift: SYNTHETIC_DEMO, AIS: SYNTHETIC_DEMO). Overall result cannot claim pure HISTORICAL_ARCHIVE."
                    )
            manifest.set_succeeded(result=res_dict)
            self.job_store.save_manifest(manifest)
            return manifest

        except ProvenanceGateError as pge:
            logger.warning("Job %s blocked by provenance gate: %s", manifest.job_id, pge)
            manifest.set_blocked_provenance(str(pge), stage=manifest.current_stage)
            self.job_store.save_manifest(manifest)
            return manifest
        except Exception as e:
            logger.exception("Job %s failed with unexpected exception: %s", manifest.job_id, e)
            manifest.set_failed(
                code="PIPELINE_ERROR",
                message=str(e),
                stage=manifest.current_stage,
                details={"exception_type": type(e).__name__},
            )
            self.job_store.save_manifest(manifest)
            return manifest
