/**
 * TypeScript definitions matching Ocean Sentinel Backend API schemas.
 */

export type JobMode = 'DEMO' | 'REAL_REPOSITORY' | 'PHYSICAL'
export type PipelineType = 'DEMO_FUSION' | 'ARTIFACT_FUSION' | 'REAL_REPOSITORY' | 'PHYSICAL'
export type JobStatus =
  | 'CREATED'
  | 'VALIDATING'
  | 'RUNNING'
  | 'SUCCEEDED'
  | 'FAILED'
  | 'BLOCKED_PROVENANCE'
  | 'INVALID_INPUT'

export type ConnectionStatus = 'ONLINE' | 'OFFLINE' | 'UNREACHABLE'

export type ResultFreshness = 'LIVE_CURRENT' | 'CACHED_LAST_LOADED' | 'NONE'

export type JobExecutionState =
  | 'CREATED'
  | 'RUNNING'
  | 'SUCCEEDED'
  | 'BLOCKED_PROVENANCE'
  | 'FAILED'
  | 'UNKNOWN'

export type ProvenanceContext =
  | 'PHYSICAL'
  | 'REAL_REPOSITORY'
  | 'DEMO'
  | 'SYNTHETIC'
  | 'REAL_REPOSITORY_SCENARIO_WITH_SYNTHETIC_DEPENDENCY'
  | 'HISTORICAL_ARCHIVE'

export type ScientificValidity =
  | 'VALID_FOR_SCOPE'
  | 'PROVENANCE_LIMITED'
  | 'BLOCKED'
  | 'LEGACY_INVALID'

export type ApplicationGate = 'READY' | 'DEGRADED' | 'BLOCKED'
export type ApplicationGateStatus = ApplicationGate

export type LineageStatus = 'CURRENT' | 'LEGACY_INVALID_TEMPORAL_PAIR'

export type ResultUsage = 'ACTIVE' | 'QUARANTINED' | 'NONE'

export type ProvenanceClass =
  | 'VERIFIED_OPERATIONAL'
  | 'HISTORICAL_ARCHIVE'
  | 'SYNTHETIC_DEMO'
  | 'UNVERIFIED_EXTERNAL'

export type ExternalSourceStatus = 'AVAILABLE' | 'BLOCKED' | 'UNACCREDITED' | 'UNKNOWN'
export type ScientificExecutionStatus = 'ALLOWED' | 'BLOCKED' | 'PROVENANCE_LIMITED'

export interface OperationalGateState {
  application_gate: ApplicationGateStatus
  backend: ConnectionStatus
  external_sources: ExternalSourceStatus
  scientific_execution: ScientificExecutionStatus
  gate_reason: string
}

export interface SelectedLocation {
  lat: number
  lon: number
  selectedAtUtc?: string
}

export type SelectionType =
  | 'NONE'
  | 'USER_LOCATION'
  | 'CANDIDATE_VESSEL'
  | 'CANDIDATE_SPILL_ORIGIN'
  | 'EVIDENCE_ITEM'

export interface HealthResponse {
  service: string
  status: string
  api_version: string
  app_version: string
  mode_info: {
    supported_modes: string[]
    default_mode: string
    physical_operational_status: string
  }
  frozen_subsystems: Record<string, string>
}

export interface StageRecord {
  stage: string
  status: string
  started_at?: string
  finished_at?: string
  duration_seconds?: number
  message?: string
  details?: Record<string, any>
}

export interface ArtifactRecord {
  artifact_id: string
  artifact_type: string
  file_path: string
  relative_path?: string
  format: string
  generated_by_stage: string
  size_bytes?: number
  provenance_class: string
  availability?: string
}

export interface ArtifactListResponse {
  job_id: string
  total_artifacts: number
  artifacts: ArtifactRecord[]
}

export interface JobErrorRecord {
  code: string
  message: string
  stage?: string
  retryable?: boolean
  details?: Record<string, any>
}

export interface JobLinks {
  self: string
  artifacts: string
  result: string
}

export interface JobResponse {
  job_id: string
  mode: JobMode
  pipeline_type: PipelineType
  status: JobStatus
  scenario_id?: string
  investigation_label?: string
  current_stage?: string
  created_at: string
  started_at?: string
  finished_at?: string
  requested_config: Record<string, any>
  stage_status: Record<string, StageRecord>
  artifacts: ArtifactRecord[]
  error?: JobErrorRecord
  limitations: string[]
  links: JobLinks
}

export interface CandidateSpillHypothesis {
  hypothesis_id: string
  hypothesis_type: string
  subject_id: string
  spatial_geometry?: any
  temporal_window_utc?: [string, string]
  supporting_evidence_ids: string[]
  conflicting_evidence_ids: string[]
  consistent_evidence_ids: string[]
  independent_support_cluster_count: number
  dependency_summary: {
    total_supporting_items: number
    independent_source_clusters: number
    is_independent_corroboration: boolean
    double_counting_prevented: boolean
    clusters: string[][]
  }
  overall_status: string
  limitations: string[]
  summary: string
}

export interface CandidateVesselHypothesis {
  hypothesis_id: string
  mmsi: string
  vessel_name?: string
  vessel_type?: string
  closest_approach_distance_m: number
  closest_approach_time_utc: string
  temporal_offset_hours: number
  is_position_inferred: boolean
  inside_origin_region: boolean
  inside_trajectory_envelope: boolean
  coverage_status: string
  evidence_compatibility_score: number
  supporting_evidence_ids: string[]
  conflicting_evidence_ids: string[]
  consistent_evidence_ids: string[]
  unknown_evidence_ids: string[]
  independent_support_cluster_count: number
  dependency_summary: {
    supporting_evidence_count: number
    conflicting_evidence_count: number
    independent_source_clusters: number
    clusters: string[][]
  }
  overall_status: string
  limitations: string[]
  summary: string
}

export interface GraphEdge {
  source_id: string
  target_id: string
  relation_type: string
  independence: string
  rationale: string
  metrics?: Record<string, any>
}

export interface GraphNode {
  node_type: string
  evidence_type?: string
  hypothesis_type?: string
  data: any
}

export interface EvidenceGraph {
  nodes: Record<string, GraphNode>
  edges: GraphEdge[]
  metadata: {
    node_count: number
    edge_count: number
    has_dependency_cycles: boolean
    negative_proof_guard: string
    scientific_boundary: string
  }
}

export interface EvidenceItem {
  evidence_id: string
  evidence_type: string
  source_type: string
  source_id: string
  observation_time_utc: string
  spatial_geometry?: any
  provenance_class: string
  provenance_source: string
  root_source_ids: string[]
  derivation_type: string
  observed_vs_inferred: 'OBSERVED' | 'INFERRED' | 'HYPOTHESIS' | 'DATA_UNAVAILABLE' | string
  status?: string
  limitations: string[]
  metric_values?: Record<string, any>
}

export interface InvestigationScenario {
  scenario_id: string
  label: string
  dataset: string
  scene_pair: string[]
  region: string
  centroid: [number, number]
  event_id: string
  artifacts: Record<string, string>
  acquisition_timestamps: Record<string, string>
  satellite_product_id: string
  vessel_truth: string
  physical_incident_label: string
  unverified_source_metadata: string
  provenance_class: string
  provenance_status?: string
  source_pair_status?: string
  temporal_status?: string
  reason?: string
  lineage_status?: LineageStatus
  has_synthetic_dependencies?: boolean
  stage_provenance?: Record<string, string>
  limitations: string[]
}

export interface ScenarioListResponse {
  total_scenarios: number
  scenarios: InvestigationScenario[]
}

export interface CreateJobPayload {
  mode: JobMode
  pipeline_type: PipelineType
  scenario_id?: string
  investigation_label?: string
  input_artifacts?: Record<string, string>
  spatial_tolerance_m?: number
  temporal_tolerance_hours?: number
}

export interface JobResultResponse {
  job_id: string
  engine: string
  mode: string
  pipeline_type: string
  scenario_id?: string
  investigation_label?: string
  provenance_class?: string
  provenance_status?: string
  has_synthetic_dependencies?: boolean
  stage_provenance?: Record<string, string>
  provenance_limitation?: string
  lineage_status?: LineageStatus
  scenario_metadata?: InvestigationScenario
  total_evidence_items: number
  total_candidate_hypotheses: number
  multiple_plausible_candidates: boolean
  plausible_candidate_count: number
  candidate_spill_hypotheses: CandidateSpillHypothesis[]
  candidate_vessel_hypotheses: CandidateVesselHypothesis[]
  evidence_graph: EvidenceGraph
  evidence_ledger?: EvidenceItem[]
  scientific_boundaries: string[]
  negative_proof_guard: string
}

export interface LayerVisibility {
  sar_detection: boolean
  temporal_change: boolean
  drift_trajectory: boolean
  drift_origin: boolean
  ais_tracks: boolean
  fused_evidence: boolean
  hypotheses: boolean
}
