import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import App from '../App'
import { RightInspector } from '../components/RightInspector'
import { LeftControlPanel } from '../components/LeftControlPanel'
import { GlobeView } from '../components/GlobeView'
import { BottomTimeline } from '../components/BottomTimeline'
import { TopBar } from '../components/TopBar'
import { oceanSentinelApi, ApiError } from '../services/api'
import type {
  HealthResponse,
  JobResponse,
  JobResultResponse,
  InvestigationScenario,
} from '../types/api'

// Mock Three.js to render cleanly in JSDOM
vi.mock('three', async () => {
  const actual: any = await vi.importActual('three')
  class MockWebGLRenderer {
    setSize = vi.fn()
    setPixelRatio = vi.fn()
    render = vi.fn()
    dispose = vi.fn()
    domElement = document.createElement('canvas')
  }
  return {
    ...actual,
    WebGLRenderer: vi.fn().mockImplementation(function () {
      return new MockWebGLRenderer()
    }),
  }
})

// Mock OrbitControls
vi.mock('three/addons/controls/OrbitControls.js', async () => {
  const three: any = await vi.importActual('three')
  class MockOrbitControls {
    update = vi.fn()
    target = new three.Vector3()
    enableDamping = true
    dampingFactor = 0.05
    minDistance = 100
    maxDistance = 600
  }
  return {
    OrbitControls: vi.fn().mockImplementation(function () {
      return new MockOrbitControls()
    }),
  }
})

const mockScenario: InvestigationScenario = {
  scenario_id: 'TRUJILLO_00007_01339',
  label: 'Trujillo Eastern Med Scene 00007 / 01339',
  dataset: 'Trujillo et al. (2024) Sentinel-1 SAR Dataset',
  scene_pair: ['00007', '01339'],
  region: 'Eastern Mediterranean (Crete / Levantine Basin)',
  centroid: [32.185, 30.642],
  event_id: 'evt_trujillo_00007_01339',
  artifacts: {
    t0_sar: 'data/trujillo/images/00007.tif',
    t1_sar: 'data/trujillo/images/01339.tif',
    mask: 'data/trujillo/masks/01339_mask.png',
  },
  acquisition_timestamps: {
    t0: 'METADATA UNAVAILABLE',
    t1: 'METADATA UNAVAILABLE',
  },
  satellite_product_id: 'METADATA UNAVAILABLE',
  vessel_truth: 'METADATA UNAVAILABLE',
  physical_incident_label: 'METADATA UNAVAILABLE',
  unverified_source_metadata: 'METADATA UNAVAILABLE',
  provenance_class: 'REAL_REPOSITORY_SCENARIO_WITH_SYNTHETIC_DEPENDENCY',
  provenance_status: 'PROVENANCE_LIMITED',
  has_synthetic_dependencies: true,
  stage_provenance: {
    satellite: 'HISTORICAL_ARCHIVE',
    temporal: 'HISTORICAL_ARCHIVE',
    drift: 'SYNTHETIC_DEMO',
    ais: 'SYNTHETIC_DEMO',
  },
  limitations: [
    'Pre-existing verified scientific masks used; inference stages skipped.',
    'Metadata not explicitly present in repository manifest marked METADATA UNAVAILABLE.',
    'Downstream drift and AIS artifacts generated with synthetic forcing and DEMO feeds (SYNTHETIC_DEMO).',
  ],
}

const mockScenarioB: InvestigationScenario = {
  ...mockScenario,
  scenario_id: 'TRUJILLO_00260_00608',
  label: 'Trujillo Gulf of Mexico Scene 00260 / 00608',
  scene_pair: ['00260', '00608'],
  region: 'Gulf of Mexico',
}

const mockHealth: HealthResponse = {
  service: 'ocean_sentinel_backend',
  status: 'HEALTHY',
  api_version: '1.0.0',
  app_version: '1.0.0',
  mode_info: {
    supported_modes: ['DEMO', 'REAL_REPOSITORY', 'PHYSICAL'],
    default_mode: 'DEMO',
    physical_operational_status: 'UNAVAILABLE_BLOCKED',
  },
  frozen_subsystems: {
    origin_drift: 'FROZEN',
    ais_correlation: 'FROZEN',
    evidence_fusion: 'FROZEN',
  },
}

const mockJob: JobResponse = {
  job_id: 'job_20260920_200537_6cfc7125',
  mode: 'DEMO',
  pipeline_type: 'DEMO_FUSION',
  status: 'SUCCEEDED',
  created_at: '2026-09-20T20:05:37.000Z',
  requested_config: {},
  stage_status: {
    VALIDATE: { stage: 'VALIDATE', status: 'SUCCEEDED' },
    FUSION: { stage: 'FUSION', status: 'SUCCEEDED' },
    EXPORT: { stage: 'EXPORT', status: 'SUCCEEDED' },
  },
  artifacts: [
    {
      artifact_id: 'job_20260920_200537_evidence_graph',
      artifact_type: 'EVIDENCE_GRAPH_JSON',
      file_path: '/path/graph.json',
      format: 'JSON',
      generated_by_stage: 'EXPORT',
      provenance_class: 'SYNTHETIC_DEMO',
    },
    {
      artifact_id: 'job_20260920_200537_evidence_summary',
      artifact_type: 'EVIDENCE_SUMMARY_JSON',
      file_path: '/path/summary.json',
      format: 'JSON',
      generated_by_stage: 'EXPORT',
      provenance_class: 'SYNTHETIC_DEMO',
    },
  ],
  limitations: [
    'Compatibility scores measure geometric/temporal alignment, NOT guilt, culpability, or causal attribution.',
  ],
  links: {
    self: '/api/v1/jobs/job_20260920_200537_6cfc7125',
    artifacts: '/api/v1/jobs/job_20260920_200537_6cfc7125/artifacts',
    result: '/api/v1/jobs/job_20260920_200537_6cfc7125/result',
  },
}

const mockResult: JobResultResponse = {
  job_id: 'job_20260920_200537_6cfc7125',
  engine: 'ocean_sentinel_evidence_fusion_v1',
  mode: 'DEMO',
  pipeline_type: 'DEMO_FUSION',
  total_evidence_items: 33,
  total_candidate_hypotheses: 7,
  multiple_plausible_candidates: true,
  plausible_candidate_count: 2,
  candidate_spill_hypotheses: [
    {
      hypothesis_id: 'hypothesis_origin_cluster_01',
      hypothesis_type: 'CANDIDATE_SPILL_ORIGIN',
      subject_id: 'drift_00007_01339_persistent_0003_backward',
      spatial_geometry: {
        type: 'Polygon',
        coordinates: [[[30.62, 31.90], [30.52, 32.00], [30.64, 31.93], [30.62, 31.90]]],
      },
      temporal_window_utc: ['2024-04-09T14:00:00Z', '2024-04-09T14:30:00Z'],
      supporting_evidence_ids: ['evidence_drift_001', 'evidence_drift_002'],
      conflicting_evidence_ids: ['evidence_temporal_001'],
      consistent_evidence_ids: [],
      independent_support_cluster_count: 1,
      dependency_summary: {
        total_supporting_items: 2,
        independent_source_clusters: 1,
        is_independent_corroboration: false,
        double_counting_prevented: true,
        clusters: [['evidence_drift_001', 'evidence_drift_002']],
      },
      overall_status: 'CONSISTENT_WITH_AVAILABLE_EVIDENCE',
      limitations: [
        'Candidate origin is an evidence-bounded hypothesis, NOT confirmed historical release location.',
      ],
      summary: 'Candidate origin evaluated across drift and temporal evidence.',
    },
  ],
  candidate_vessel_hypotheses: [
    {
      hypothesis_id: 'hypothesis_vessel_368123450',
      mmsi: '368123450',
      vessel_name: 'MT_HORIZON_STAR',
      vessel_type: 'Crude Oil Tanker',
      closest_approach_distance_m: 1321.9,
      closest_approach_time_utc: '2024-04-09T14:30:38Z',
      temporal_offset_hours: 0.0,
      is_position_inferred: true,
      inside_origin_region: true,
      inside_trajectory_envelope: true,
      coverage_status: 'OBSERVED_IN_WINDOW',
      evidence_compatibility_score: 0.8606,
      supporting_evidence_ids: ['evidence_ais_corr_368123450'],
      conflicting_evidence_ids: [],
      consistent_evidence_ids: [],
      unknown_evidence_ids: [],
      independent_support_cluster_count: 1,
      dependency_summary: {
        supporting_evidence_count: 1,
        conflicting_evidence_count: 0,
        independent_source_clusters: 1,
        clusters: [['evidence_ais_corr_368123450']],
      },
      overall_status: 'SUPPORTED_BY_AVAILABLE_EVIDENCE',
      limitations: [
        'AIS compatibility establishes spatio-temporal alignment only, NOT legal attribution.',
        'Absence of an AIS track does NOT prove vessel absence.',
      ],
      summary: 'Candidate vessel MT_HORIZON_STAR: score 0.8606.',
    },
    {
      hypothesis_id: 'hypothesis_vessel_368777880',
      mmsi: '368777880',
      vessel_name: 'GULF_SUPPLIER_VII',
      vessel_type: 'Offshore Supply',
      closest_approach_distance_m: 1492.0,
      closest_approach_time_utc: '2024-04-09T14:00:00Z',
      temporal_offset_hours: 0.0,
      is_position_inferred: true,
      inside_origin_region: true,
      inside_trajectory_envelope: true,
      coverage_status: 'OBSERVED_IN_WINDOW',
      evidence_compatibility_score: 0.8351,
      supporting_evidence_ids: ['evidence_ais_corr_368777880'],
      conflicting_evidence_ids: [],
      consistent_evidence_ids: [],
      unknown_evidence_ids: [],
      independent_support_cluster_count: 1,
      dependency_summary: {
        supporting_evidence_count: 1,
        conflicting_evidence_count: 0,
        independent_source_clusters: 1,
        clusters: [['evidence_ais_corr_368777880']],
      },
      overall_status: 'SUPPORTED_BY_AVAILABLE_EVIDENCE',
      limitations: [
        'AIS compatibility establishes spatio-temporal alignment only, NOT legal attribution.',
      ],
      summary: 'Candidate vessel GULF_SUPPLIER_VII: score 0.8351.',
    },
    {
      hypothesis_id: 'hypothesis_vessel_369555660',
      mmsi: '369555660',
      vessel_name: 'GLITCH_RUNNER',
      vessel_type: 'Cargo',
      closest_approach_distance_m: 1886.3,
      closest_approach_time_utc: '2024-04-09T13:00:00Z',
      temporal_offset_hours: 14.0,
      is_position_inferred: false,
      inside_origin_region: true,
      inside_trajectory_envelope: true,
      coverage_status: 'OUTSIDE_WINDOW',
      evidence_compatibility_score: 0.4461,
      supporting_evidence_ids: [],
      conflicting_evidence_ids: ['evidence_ais_corr_369555660'],
      consistent_evidence_ids: [],
      unknown_evidence_ids: [],
      independent_support_cluster_count: 0,
      dependency_summary: {
        supporting_evidence_count: 0,
        conflicting_evidence_count: 1,
        independent_source_clusters: 0,
        clusters: [],
      },
      overall_status: 'CONFLICTING_EVIDENCE',
      limitations: [
        'AIS compatibility establishes spatio-temporal alignment only, NOT legal attribution.',
      ],
      summary: 'Candidate vessel GLITCH_RUNNER: score 0.4461 (conflicting).',
    },
    {
      hypothesis_id: 'hypothesis_vessel_366333440',
      mmsi: '366333440',
      vessel_name: 'SEA_PROWLER',
      vessel_type: 'Fishing',
      closest_approach_distance_m: 4976.0,
      closest_approach_time_utc: '2024-04-09T14:00:00Z',
      temporal_offset_hours: 0.0,
      is_position_inferred: false,
      inside_origin_region: false,
      inside_trajectory_envelope: false,
      coverage_status: 'TELEMETRY_GAP',
      evidence_compatibility_score: 0.2087,
      supporting_evidence_ids: [],
      conflicting_evidence_ids: [],
      consistent_evidence_ids: [],
      unknown_evidence_ids: ['evidence_ais_corr_366333440'],
      independent_support_cluster_count: 0,
      dependency_summary: {
        supporting_evidence_count: 0,
        conflicting_evidence_count: 0,
        independent_source_clusters: 0,
        clusters: [],
      },
      overall_status: 'INSUFFICIENT_EVIDENCE',
      limitations: [
        'Track has large telemetry gap (8.0h); positions were not interpolated across gap.',
      ],
      summary: 'Candidate vessel SEA_PROWLER: telemetry gap.',
    },
  ],
  evidence_ledger: [
    {
      evidence_id: 'evidence_ais_corr_368123450',
      evidence_type: 'AIS_CORRELATION',
      source_type: 'AIS_STREAM',
      source_id: 'AIS_368123450',
      observation_time_utc: '2024-04-09T14:30:38Z',
      spatial_geometry: { type: 'Point', coordinates: [30.672, 32.215] },
      provenance_class: 'SYNTHETIC_DEMO',
      provenance_source: 'Synthetic_AIS_Fixture',
      root_source_ids: ['AIS_368123450'],
      derivation_type: 'SPATIO_TEMPORAL_INTERPOLATION',
      observed_vs_inferred: 'INFERRED',
      status: 'SUPPORTED',
      limitations: ['Spatio-temporal alignment only; does not establish causation.'],
    },
  ],
  evidence_graph: {
    nodes: {},
    edges: [],
    metadata: {
      node_count: 33,
      edge_count: 48,
      has_dependency_cycles: false,
      negative_proof_guard: 'AIS_ABSENCE_IS_NOT_VESSEL_ABSENCE',
      scientific_boundary: 'EVIDENCE_COMPATIBILITY_ONLY_NO_LEGAL_ATTRIBUTION',
    },
  },
  scientific_boundaries: [
    'EVIDENCE_COMPATIBILITY_ONLY_NO_LEGAL_ATTRIBUTION',
  ],
  negative_proof_guard: 'AIS_ABSENCE_IS_NOT_VESSEL_ABSENCE',
}

describe('Ocean Sentinel Frontend Geospatial Console V1.1 Suite', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(oceanSentinelApi, 'getHealth').mockResolvedValue(mockHealth)
    vi.spyOn(oceanSentinelApi, 'listJobs').mockResolvedValue({
      total_jobs: 1,
      limit: 10,
      jobs: [mockJob],
    })
    vi.spyOn(oceanSentinelApi, 'getJob').mockResolvedValue(mockJob)
    vi.spyOn(oceanSentinelApi, 'getJobResult').mockResolvedValue(mockResult)
    vi.spyOn(oceanSentinelApi, 'createJob').mockResolvedValue(mockJob)
    vi.spyOn(oceanSentinelApi, 'listScenarios').mockResolvedValue({
      total_scenarios: 2,
      scenarios: [mockScenario, mockScenarioB],
    })
    vi.spyOn(oceanSentinelApi, 'getScenario').mockImplementation(async (id: string) => {
      if (id === 'TRUJILLO_00260_00608') return mockScenarioB
      return mockScenario
    })
  })

  // 1. App renders
  it('1. App renders identity and core layout components', async () => {
    render(<App />)
    expect(screen.getByText('OCEAN SENTINEL')).toBeInTheDocument()
    expect(screen.getByText(/3D GEOSPATIAL V1/)).toBeInTheDocument()
    expect(screen.getByText('OPERATIONAL CONTROLS')).toBeInTheDocument()
    expect(screen.getByText('EVIDENCE FUSION EXPLORER')).toBeInTheDocument()
    expect(screen.getByText('TEMPORAL REASONING CONTROLLER')).toBeInTheDocument()
  })

  // 2. Backend health state renders ONLINE
  it('2. Backend health state displays BACKEND ONLINE when connected', async () => {
    render(<App />)
    await waitFor(() => {
      expect(screen.getByText('BACKEND ONLINE')).toBeInTheDocument()
    })
  })

  // 3. Backend connectivity semantics: OFFLINE and UNREACHABLE with LAST LOADED RESULT
  it('3. Backend unreachable displays BACKEND UNREACHABLE and marks cached job as LAST LOADED RESULT', async () => {
    vi.spyOn(oceanSentinelApi, 'getHealth').mockRejectedValue(new Error('Network connection failed'))
    render(<App />)
    await waitFor(() => {
      expect(screen.getByText('BACKEND UNREACHABLE')).toBeInTheDocument()
      expect(screen.getByText('LAST LOADED RESULT')).toBeInTheDocument()
    })
  })

  it('4. Backend error response displays BACKEND OFFLINE', async () => {
    vi.spyOn(oceanSentinelApi, 'getHealth').mockRejectedValue(
      new ApiError('SERVICE_UNAVAILABLE', 'Backend 503 error', 503)
    )
    render(<App />)
    await waitFor(() => {
      expect(screen.getByText('BACKEND OFFLINE')).toBeInTheDocument()
    })
  })

  // 5. DEMO job can be initiated
  it('5. DEMO job can be initiated via control button', async () => {
    render(<App />)
    const runBtn = screen.getByRole('button', { name: /RUN DEMO_FUSION/i })
    fireEvent.click(runBtn)
    await waitFor(() => {
      expect(oceanSentinelApi.createJob).toHaveBeenCalledWith({
        mode: 'DEMO',
        pipeline_type: 'DEMO_FUSION',
      })
    })
  })

  // 6. Job status renders
  it('6. Job status and ID render in top bar and control panel', async () => {
    render(<App />)
    await waitFor(() => {
      expect(screen.getAllByText('SUCCEEDED').length).toBeGreaterThan(0)
    })
  })

  // 7. Artifact list renders in session history
  it('7. Job list renders recent jobs', async () => {
    render(<App />)
    await waitFor(() => {
      expect(screen.getByText('RECENT JOBS (1)')).toBeInTheDocument()
    })
  })

  // 8. Evidence result renders candidate vessels and score metrics
  it('8. Evidence result renders candidate vessels and score metrics', async () => {
    render(<App />)
    await waitFor(() => {
      expect(screen.getByText('MT_HORIZON_STAR')).toBeInTheDocument()
      expect(screen.getByText('0.8606')).toBeInTheDocument()
    })
  })

  // 9. Layer visibility toggles
  it('9. Layer visibility switches can be toggled', async () => {
    render(<App />)
    const sarToggle = screen.getByText('SAR Detection')
    expect(sarToggle).toBeInTheDocument()
    fireEvent.click(sarToggle)
  })

  // 10. Evidence selection activates candidate details and evidence chain
  it('10. Evidence selection activates candidate details and evidence chain', async () => {
    render(<App />)
    await waitFor(() => {
      expect(screen.getByText('MT_HORIZON_STAR')).toBeInTheDocument()
    })
    const card = screen.getByText('GULF_SUPPLIER_VII')
    fireEvent.click(card)
    await waitFor(() => {
      expect(screen.getByText('EVIDENCE CHAIN: GULF_SUPPLIER_VII')).toBeInTheDocument()
      expect(screen.getByText('CANDIDATE VESSEL HYPOTHESIS')).toBeInTheDocument()
    })
  })

  // 11. Multiple candidates remain visible simultaneously
  it('11. Multiple candidate vessels remain simultaneously visible without single winner', async () => {
    render(<App />)
    await waitFor(() => {
      expect(screen.getByText('MT_HORIZON_STAR')).toBeInTheDocument()
      expect(screen.getByText('GULF_SUPPLIER_VII')).toBeInTheDocument()
      expect(screen.getByText('GLITCH_RUNNER')).toBeInTheDocument()
    })
  })

  // 12. Conflicting evidence remains visible
  it('12. Conflicting evidence remains explicit in candidate ledger', async () => {
    render(<App />)
    await waitFor(() => {
      expect(screen.getByText('GLITCH_RUNNER')).toBeInTheDocument()
      expect(screen.getByText('CONFLICTING_EVIDENCE')).toBeInTheDocument()
    })
  })

  // 13. DATA_UNAVAILABLE remains explicit
  it('13. Telemetry gaps are rendered as DATA_UNAVAILABLE / INSUFFICIENT_EVIDENCE', async () => {
    render(<App />)
    await waitFor(() => {
      expect(screen.getByText('SEA_PROWLER')).toBeInTheDocument()
      expect(screen.getByText('INSUFFICIENT_EVIDENCE')).toBeInTheDocument()
    })
  })

  // 14. PHYSICAL provenance block renders correctly
  it('14. PHYSICAL provenance block renders correctly fail-closed', async () => {
    vi.spyOn(oceanSentinelApi, 'createJob').mockRejectedValueOnce(
      new Error('PHYSICAL pipeline blocked by operational provenance gate.')
    )
    render(<App />)
    const physicalBtn = screen.getByText('RUN PHYSICAL (TEST BLOCK)')
    fireEvent.click(physicalBtn)
    await waitFor(() => {
      expect(screen.getByText(/PHYSICAL pipeline blocked/)).toBeInTheDocument()
    })
  })

  // 15. No synthetic evidence is labelled physical
  it('15. No synthetic evidence is labelled physical; DEMO mode badge is visible', async () => {
    render(<App />)
    expect(screen.getByText('DEMO MODE')).toBeInTheDocument()
    expect(screen.getByText('Vector Basemap (Fail-Closed: No Fabricated Satellite Imagery)')).toBeInTheDocument()
  })

  // 16. Temporal state changes update visualization and communicate both stage and observation
  it('16. Temporal controller communicates both pipeline stage and observation state', async () => {
    render(<App />)
    const t0Node = screen.getByText('T0: BASELINE')
    expect(t0Node).toBeInTheDocument()
    expect(screen.getByText('SAR Observed Pre-Spill')).toBeInTheDocument()
    expect(screen.getByText('Lagrangian Drift Hypothesis')).toBeInTheDocument()
    expect(screen.getByText('SAR Observed Slick')).toBeInTheDocument()
    expect(screen.getByText('Multi-Source Lineage Inferred')).toBeInTheDocument()

    fireEvent.click(t0Node)
    expect(screen.getByText(/Baseline Sentinel-1 SAR acquisition prior to slick emergence/)).toBeInTheDocument()
  })

  // 17. Evidence inspector shows provenance/lineage
  it('17. Evidence inspector displays provenance and independent source clusters', async () => {
    render(<App />)
    await waitFor(() => {
      expect(screen.getAllByText(/1 INDEP. CLUSTERS/).length).toBeGreaterThan(0)
    })
  })

  // 18. Candidate hypothesis does not become "confirmed" through UI wording
  it('18. Candidate hypothesis does NOT contain "confirmed responsible vessel" or "guilty"', async () => {
    render(<App />)
    await waitFor(() => {
      expect(screen.queryByText(/confirmed responsible vessel/i)).not.toBeInTheDocument()
      expect(screen.queryByText(/guilty vessel/i)).not.toBeInTheDocument()
      expect(screen.getByText(/SPATIO-TEMPORAL COMPATIBILITY ONLY/)).toBeInTheDocument()
    })
  })

  // 19. Event auto-focus HUD banner renders when result exists
  it('19. Event auto-focus HUD banner renders with incident details and recenter action', async () => {
    render(<App />)
    await waitFor(() => {
      expect(screen.getByText(/INCIDENT AUTO-FOCUS: EASTERN MEDITERRANEAN/)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /Recenter Event/i })).toBeInTheDocument()
    })
  })

  // 20. Empty result produces controlled empty state notice
  it('20. Empty result produces controlled empty state notice', async () => {
    vi.spyOn(oceanSentinelApi, 'listJobs').mockResolvedValueOnce({ total_jobs: 0, limit: 10, jobs: [] })
    vi.spyOn(oceanSentinelApi, 'getJobResult').mockResolvedValueOnce(null as any)
    render(<App />)
    await waitFor(() => {
      expect(screen.getByText('NO ACTIVE JOB LOADED')).toBeInTheDocument()
    })
  })

  // 21. Location selection renders operator reference without creating scientific evidence
  it('21. Location selection inspector displays user coordinate and non-evidence invariant', () => {
    const onClearMock = vi.fn()
    render(
      <RightInspector
        result={mockResult}
        selectedEvidenceId={null}
        onSelectEvidence={vi.fn()}
        selectedLocation={{ lat: 32.185, lon: 30.642, selectedAtUtc: '2026-09-20T20:00:00Z' }}
        selectionType="USER_LOCATION"
        onClearLocation={onClearMock}
      />
    )
    expect(screen.getByText('USER LOCATION (REFERENCE)')).toBeInTheDocument()
    expect(screen.getByText('USER-SELECTED COORDINATE')).toBeInTheDocument()
    expect(screen.getByText(/32.1850° N/)).toBeInTheDocument()
    expect(screen.getByText(/30.6420° E/)).toBeInTheDocument()
    expect(screen.getByText(/NON-EVIDENCE INVARIANT/)).toBeInTheDocument()
    expect(screen.getByText(/A user-selected location is an operator reference target only/)).toBeInTheDocument()

    const clearBtn = screen.getByTitle('Clear Selected Location')
    fireEvent.click(clearBtn)
    expect(onClearMock).toHaveBeenCalled()
  })

  // 22. GlobeView renders selected location HUD
  it('22. GlobeView renders selected location HUD with focus and clear actions', () => {
    const onSelectLocationMock = vi.fn()
    render(
      <GlobeView
        result={mockResult}
        selectedEvidenceId={null}
        onSelectEvidence={vi.fn()}
        selectedLocation={{ lat: 31.95, lon: 30.55 }}
        onSelectLocation={onSelectLocationMock}
        layers={{
          sar_detection: true,
          temporal_change: true,
          drift_trajectory: true,
          drift_origin: true,
          ais_tracks: true,
          fused_evidence: true,
          hypotheses: true,
        }}
        isLoading={false}
      />
    )
    expect(screen.getByText(/SELECTED LOCATION: 31.9500° N, 30.5500° E/)).toBeInTheDocument()
    expect(screen.getByText('OPERATOR REFERENCE — NOT EVIDENCE')).toBeInTheDocument()
    expect(screen.getByTitle('Fly Camera to Selected Location')).toBeInTheDocument()
    const clearBtn = screen.getByTitle('Clear Location Selection')
    fireEvent.click(clearBtn)
    expect(onSelectLocationMock).toHaveBeenCalledWith(null)
  })

  // 23. REAL_REPOSITORY mode is selectable and renders scenario dropdown with authentic metadata
  it('23. REAL_REPOSITORY mode is selectable and renders scenario dropdown with authentic metadata', async () => {
    render(<App />)
    // Switch mode to REAL REPOSITORY
    const realRepoTab = screen.getByRole('button', { name: /REAL REPOSITORY/i })
    fireEvent.click(realRepoTab)

    await waitFor(() => {
      expect(screen.getByText('REAL DATASET SCENARIO')).toBeInTheDocument()
      expect(screen.getByTestId('scenario-select')).toBeInTheDocument()
      expect(screen.getByText(/Trujillo et al/i)).toBeInTheDocument()
      // Authentic metadata assertions (never manufactured)
      const unavailables = screen.getAllByText('METADATA UNAVAILABLE')
      expect(unavailables.length).toBeGreaterThan(0)
    })
  })

  // 24. REAL_REPOSITORY job execution dispatches createJob with scenario_id
  it('24. REAL_REPOSITORY job execution dispatches createJob with scenario_id', async () => {
    render(<App />)
    await waitFor(() => {
      expect(screen.getByText('BACKEND ONLINE')).toBeInTheDocument()
    })

    const realRepoTab = screen.getByRole('button', { name: /REAL REPOSITORY/i })
    fireEvent.click(realRepoTab)

    await waitFor(() => {
      expect(screen.getByTestId('run-real-investigation-btn')).toBeInTheDocument()
    })

    const runBtn = screen.getByTestId('run-real-investigation-btn')
    fireEvent.click(runBtn)

    await waitFor(() => {
      expect(oceanSentinelApi.createJob).toHaveBeenCalledWith({
        mode: 'REAL_REPOSITORY',
        pipeline_type: 'REAL_REPOSITORY',
        scenario_id: 'TRUJILLO_00007_01339',
      })
    })
  })

  // 25. Manifest stage progress monitor renders SKIPPED stages
  it('25. Manifest stage progress monitor renders SKIPPED stages faithfully', async () => {
    const mockSkippedJob: JobResponse = {
      ...mockJob,
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00007_01339',
      stage_status: {
        VALIDATE: { stage: 'VALIDATE', status: 'COMPLETED' },
        INGEST: { stage: 'INGEST', status: 'COMPLETED' },
        INFER: { stage: 'INFER', status: 'SKIPPED' },
        INTERPRET: { stage: 'INTERPRET', status: 'SKIPPED' },
        FUSION: { stage: 'FUSION', status: 'COMPLETED' },
        EXPORT: { stage: 'EXPORT', status: 'COMPLETED' },
      },
    }
    vi.spyOn(oceanSentinelApi, 'listJobs').mockResolvedValueOnce({
      total_jobs: 1,
      limit: 10,
      jobs: [mockSkippedJob],
    })
    render(<App />)

    await waitFor(() => {
      expect(screen.getByText('PIPELINE STAGES MANIFEST')).toBeInTheDocument()
      expect(screen.getByText('INFER')).toBeInTheDocument()
      expect(screen.getByText('INTERPRET')).toBeInTheDocument()
      expect(screen.getAllByText('SKIPPED').length).toBeGreaterThanOrEqual(2)
    })
  })

  // 26. Real repository result renders FUSION STATUS: PROVENANCE LIMITED when synthetic dependencies exist
  it('26. Real repository result renders FUSION STATUS: PROVENANCE LIMITED in RightInspector', async () => {
    const mockRealResult: JobResultResponse = {
      ...mockResult,
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00007_01339',
      provenance_class: 'REAL_REPOSITORY_SCENARIO_WITH_SYNTHETIC_DEPENDENCY',
      provenance_status: 'PROVENANCE_LIMITED',
      has_synthetic_dependencies: true,
      stage_provenance: {
        satellite: 'HISTORICAL_ARCHIVE',
        temporal: 'HISTORICAL_ARCHIVE',
        drift: 'SYNTHETIC_DEMO',
        ais: 'SYNTHETIC_DEMO',
      },
      scenario_metadata: mockScenario,
    }
    render(
      <RightInspector
        result={mockRealResult}
        selectedEvidenceId={null}
        onSelectEvidence={vi.fn()}
        selectedLocation={null}
        selectionType="NONE"
        onClearLocation={vi.fn()}
      />
    )

    expect(screen.getByText('REAL REPOSITORY INVESTIGATION')).toBeInTheDocument()
    expect(screen.getByText('FUSION STATUS: PROVENANCE LIMITED')).toBeInTheDocument()
    expect(screen.getByText('Satellite Source:')).toBeInTheDocument()
    expect(screen.getByText('Drift Forcing:')).toBeInTheDocument()
    expect(screen.getByText('AIS Feed:')).toBeInTheDocument()
    expect(screen.getByText(/PROVENANCE NOTICE:/)).toBeInTheDocument()
    expect(screen.getByText('Trujillo Eastern Med Scene 00007 / 01339')).toBeInTheDocument()
  })

  // 27. Selected AIS evidence item renders SYNTHETIC_DEMO provenance
  it('27. Selected AIS evidence item renders SYNTHETIC_DEMO provenance in RightInspector', () => {
    render(
      <RightInspector
        result={mockResult}
        selectedEvidenceId="evidence_ais_corr_368123450"
        onSelectEvidence={vi.fn()}
        selectedLocation={null}
        selectionType="EVIDENCE_ITEM"
        onClearLocation={vi.fn()}
      />
    )
    expect(screen.getByText('SELECTED EVIDENCE METADATA')).toBeInTheDocument()
    expect(screen.getAllByText('evidence_ais_corr_368123450').length).toBeGreaterThan(0)
    expect(screen.getByText('SYNTHETIC_DEMO')).toBeInTheDocument()
  })

  // 28. Real repository mode does not display pure HISTORICAL_ARCHIVE for overall investigation
  it('28. Real repository mode does not display pure HISTORICAL_ARCHIVE for overall investigation', () => {
    const mockRealResult: JobResultResponse = {
      ...mockResult,
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00007_01339',
      provenance_class: 'REAL_REPOSITORY_SCENARIO_WITH_SYNTHETIC_DEPENDENCY',
      provenance_status: 'PROVENANCE_LIMITED',
      has_synthetic_dependencies: true,
      stage_provenance: {
        satellite: 'HISTORICAL_ARCHIVE',
        temporal: 'HISTORICAL_ARCHIVE',
        drift: 'SYNTHETIC_DEMO',
        ais: 'SYNTHETIC_DEMO',
      },
      scenario_metadata: mockScenario,
    }
    render(
      <RightInspector
        result={mockRealResult}
        selectedEvidenceId={null}
        onSelectEvidence={vi.fn()}
        selectedLocation={null}
        selectionType="NONE"
        onClearLocation={vi.fn()}
      />
    )
    expect(screen.queryByText('PROVENANCE: HISTORICAL_ARCHIVE')).not.toBeInTheDocument()
  })

  it('29. LeftControlPanel visibly displays IDENTICAL SOURCE RASTERS alert and blocked status for invalid duplicate pair', () => {
    const invalidDuplicateScenario: InvestigationScenario = {
      ...mockScenario,
      scenario_id: 'TRUJILLO_00007_01339',
      source_pair_status: 'INVALID_DUPLICATE_IMAGE_PAIR',
      temporal_status: 'BLOCKED',
      reason: 'IDENTICAL_SOURCE_RASTERS',
    }

    render(
      <LeftControlPanel
        activeMode="REAL_REPOSITORY"
        currentJob={null}
        jobList={[]}
        scenarios={[invalidDuplicateScenario]}
        selectedScenarioId="TRUJILLO_00007_01339"
        onSelectScenario={vi.fn()}
        onRunPipeline={vi.fn()}
        onRunRealInvestigation={vi.fn()}
        onSelectJob={vi.fn()}
        isExecuting={false}
        layers={{
          sar_detection: true,
          temporal_change: true,
          drift_trajectory: true,
          drift_origin: true,
          ais_tracks: true,
          fused_evidence: true,
          hypotheses: true,
        }}
        onToggleLayer={vi.fn()}
      />
    )

    expect(screen.getByTestId('duplicate-raster-alert')).toBeInTheDocument()
    expect(screen.getByText(/IDENTICAL SOURCE RASTERS/)).toBeInTheDocument()
    expect(screen.getByTestId('scenario-source-pair-status')).toHaveTextContent('INVALID_DUPLICATE_IMAGE_PAIR')
    expect(screen.getByTestId('scenario-temporal-status')).toHaveTextContent('BLOCKED')
  })

  // 30. Initial mount / browser reload loads past job as CACHED_LAST_LOADED, never LIVE CURRENT
  it('30. Initial mount / browser reload loads past job as CACHED_LAST_LOADED, never LIVE CURRENT', async () => {
    render(<App />)
    await waitFor(() => {
      expect(screen.getByText('BACKEND ONLINE')).toBeInTheDocument()
    })

    const badge = screen.getByTestId('result-freshness-badge')
    expect(badge).toHaveTextContent('LAST LOADED RESULT')
    expect(screen.queryByText('● LIVE CURRENT')).not.toBeInTheDocument()
  })

  // 31. Pipeline run produces LIVE CURRENT and backend disconnect transitions it to LAST LOADED RESULT
  it('31. Pipeline run produces LIVE CURRENT and disconnect transitions it to LAST LOADED RESULT', async () => {
    const { unmount } = render(<App />)
    await waitFor(() => {
      expect(screen.getByText('BACKEND ONLINE')).toBeInTheDocument()
    })

    // Execute pipeline to obtain LIVE_CURRENT
    const runBtn = screen.getByTestId('run-demo-fusion-btn')
    fireEvent.click(runBtn)

    await waitFor(() => {
      const badge = screen.getByTestId('result-freshness-badge')
      expect(badge).toHaveTextContent('● LIVE CURRENT')
    })
    unmount()

    // Now simulate backend becoming unreachable
    vi.spyOn(oceanSentinelApi, 'getHealth').mockRejectedValue(new Error('Connection lost'))
    const { unmount: unmount2 } = render(<App />)
    await waitFor(() => {
      expect(screen.getByText('BACKEND UNREACHABLE')).toBeInTheDocument()
      expect(screen.getByTestId('result-freshness-badge')).toHaveTextContent('LAST LOADED RESULT')
    })
    unmount2()
  })

  // 32. Scenario switch while cached result is displayed shows SCENARIO SELECTION MISMATCH warning
  it('32. Scenario switch while cached result is displayed shows SCENARIO SELECTION MISMATCH warning', async () => {
    const twoScenarios: InvestigationScenario[] = [
      mockScenario,
      {
        ...mockScenario,
        scenario_id: 'TRUJILLO_00260_00608',
        label: 'Trujillo Gulf of Mexico Scene 00260 / 00608',
      },
    ]
    vi.spyOn(oceanSentinelApi, 'listScenarios').mockResolvedValue({
      total_scenarios: 2,
      scenarios: twoScenarios,
    })
    const mockRealJob: JobResponse = {
      ...mockJob,
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00007_01339',
    }
    vi.spyOn(oceanSentinelApi, 'listJobs').mockResolvedValue({
      total_jobs: 1,
      limit: 10,
      jobs: [mockRealJob],
    })

    const { unmount } = render(<App />)

    // Switch to REAL REPOSITORY
    const realRepoTab = screen.getByRole('button', { name: /REAL REPOSITORY/i })
    fireEvent.click(realRepoTab)

    await waitFor(() => {
      expect(screen.getByTestId('scenario-select')).toBeInTheDocument()
    })

    const select = screen.getByTestId('scenario-select') as HTMLSelectElement
    fireEvent.change(select, { target: { value: 'TRUJILLO_00260_00608' } })

    await waitFor(() => {
      expect(document.querySelector('[data-testid="scenario-mismatch-banner"]')).not.toBeNull()
    })
    expect(screen.getByTestId('manifest-mismatch-badge')).toBeInTheDocument()
    expect(screen.getByTestId('manifest-quarantine-badge')).toBeInTheDocument()
    expect(screen.getByTestId('quarantine-status-badge')).toBeInTheDocument()
    unmount()
  })

  // 33. Mode switch DEMO <-> REAL_REPOSITORY displays MODE MISMATCH and retains original provenance
  it('33. Mode switch DEMO <-> REAL_REPOSITORY displays MODE MISMATCH and retains original provenance', () => {
    const mockRealResult: JobResultResponse = {
      ...mockResult,
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00007_01339',
      provenance_class: 'REAL_REPOSITORY_SCENARIO_WITH_SYNTHETIC_DEPENDENCY',
    }

    render(
      <RightInspector
        result={mockRealResult}
        selectedEvidenceId={null}
        onSelectEvidence={vi.fn()}
        selectedLocation={null}
        selectionType="NONE"
        onClearLocation={vi.fn()}
        resultFreshness="CACHED_LAST_LOADED"
        activeMode="DEMO"
        selectedScenarioId="TRUJILLO_00007_01339"
      />
    )

    // Must show mode mismatch banner and cached notice
    expect(screen.getByTestId('inspector-mode-mismatch-alert')).toBeInTheDocument()
    expect(screen.getByTestId('inspector-cached-notice')).toBeInTheDocument()
    expect(screen.getByText(/Mode switching never silently converts cached results/)).toBeInTheDocument()
  })

  // 34. Backend reconnection does NOT convert CACHED_LAST_LOADED into LIVE_CURRENT without fresh execution
  it('34. Backend reconnection does NOT convert CACHED_LAST_LOADED into LIVE_CURRENT without fresh execution', async () => {
    render(<App />)
    await waitFor(() => {
      expect(screen.getByText('BACKEND ONLINE')).toBeInTheDocument()
    })

    // Backend is connected, but result is cached from mount
    const freshnessBadge = screen.getByTestId('result-freshness-badge')
    expect(freshnessBadge).toHaveTextContent('LAST LOADED RESULT')
    expect(screen.queryByText('● LIVE CURRENT')).not.toBeInTheDocument()
  })

  // 35. Operational gate indicators clearly separate application gate, backend reachability, and external sources
  it('35. Operational gate indicators clearly separate application gate, backend reachability, and external sources', () => {
    // Check PHYSICAL mode renders BLOCKED gate
    const { unmount } = render(<App />)
    const physBtn = screen.getByTestId('mode-physical-btn')
    fireEvent.click(physBtn)
    expect(screen.getByTestId('operational-gate-indicator')).toHaveTextContent('APPLICATION GATE: BLOCKED')
    unmount()

    // Check REAL_REPOSITORY renders READY gate (never conflated with PROVENANCE_LIMITED)
    render(<App />)
    const realRepoBtn = screen.getByTestId('mode-real-repo-btn')
    fireEvent.click(realRepoBtn)
    expect(screen.getByTestId('operational-gate-indicator')).toHaveTextContent('APPLICATION GATE: READY')
  })

  // 36. Matching scenario + matching mode: cached result can be shown normally
  it('36. Matching scenario + matching mode: cached result can be shown normally', () => {
    const mockRealResult: JobResultResponse = {
      ...mockResult,
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00007_01339',
      provenance_class: 'REAL_REPOSITORY_SCENARIO_WITH_SYNTHETIC_DEPENDENCY',
    }

    const { unmount } = render(
      <RightInspector
        result={mockRealResult}
        selectedEvidenceId={null}
        onSelectEvidence={vi.fn()}
        selectedLocation={null}
        selectionType="NONE"
        onClearLocation={vi.fn()}
        resultFreshness="CACHED_LAST_LOADED"
        activeMode="REAL_REPOSITORY"
        selectedScenarioId="TRUJILLO_00007_01339"
      />
    )

    expect(screen.queryByTestId('quarantine-banner')).not.toBeInTheDocument()
    expect(screen.queryByTestId('inspector-scenario-mismatch-alert')).not.toBeInTheDocument()
    expect(screen.queryByTestId('inspector-mode-mismatch-alert')).not.toBeInTheDocument()
    expect(screen.queryByTestId('quarantine-control-notice')).not.toBeInTheDocument()
    expect(screen.getByText(/IDENTIFIED/)).toBeInTheDocument()
    unmount()
  })

  // 37. Scenario mismatch: mismatch alert appears; cached evidence is quarantined
  it('37. Scenario mismatch: mismatch alert appears; cached evidence is quarantined', () => {
    const mockRealResult: JobResultResponse = {
      ...mockResult,
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00007_01339',
      provenance_class: 'REAL_REPOSITORY_SCENARIO_WITH_SYNTHETIC_DEPENDENCY',
    }

    const { unmount } = render(
      <RightInspector
        result={mockRealResult}
        selectedEvidenceId={null}
        onSelectEvidence={vi.fn()}
        selectedLocation={null}
        selectionType="NONE"
        onClearLocation={vi.fn()}
        resultFreshness="CACHED_LAST_LOADED"
        activeMode="REAL_REPOSITORY"
        selectedScenarioId="TRUJILLO_00260_00608"
      />
    )

    expect(screen.getByTestId('quarantine-banner')).toBeInTheDocument()
    expect(screen.getByTestId('inspector-scenario-mismatch-alert')).toBeInTheDocument()
    expect(screen.getByTestId('quarantine-control-notice')).toBeInTheDocument()
    unmount()
  })

  // 38. Mode mismatch: mismatch alert appears; cached evidence is quarantined
  it('38. Mode mismatch: mismatch alert appears; cached evidence is quarantined', () => {
    const mockRealResult: JobResultResponse = {
      ...mockResult,
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00007_01339',
      provenance_class: 'REAL_REPOSITORY_SCENARIO_WITH_SYNTHETIC_DEPENDENCY',
    }

    const { unmount } = render(
      <RightInspector
        result={mockRealResult}
        selectedEvidenceId={null}
        onSelectEvidence={vi.fn()}
        selectedLocation={null}
        selectionType="NONE"
        onClearLocation={vi.fn()}
        resultFreshness="CACHED_LAST_LOADED"
        activeMode="DEMO"
        selectedScenarioId="TRUJILLO_00007_01339"
      />
    )

    expect(screen.getByTestId('quarantine-banner')).toBeInTheDocument()
    expect(screen.getByTestId('inspector-mode-mismatch-alert')).toBeInTheDocument()
    expect(screen.getByTestId('quarantine-control-notice')).toBeInTheDocument()
    unmount()
  })

  // 39. Quarantined evidence keeps original job_id, scenario_id, mode, provenance
  it('39. Quarantined evidence keeps original job_id, scenario_id, mode, provenance', () => {
    const mockRealResult: JobResultResponse = {
      ...mockResult,
      job_id: 'job_orig_12345678',
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00007_01339',
      provenance_class: 'REAL_REPOSITORY_SCENARIO_WITH_SYNTHETIC_DEPENDENCY',
      provenance_status: 'PROVENANCE_LIMITED',
      has_synthetic_dependencies: true,
    }

    const { unmount } = render(
      <RightInspector
        result={mockRealResult}
        selectedEvidenceId={null}
        onSelectEvidence={vi.fn()}
        selectedLocation={null}
        selectionType="NONE"
        onClearLocation={vi.fn()}
        resultFreshness="CACHED_LAST_LOADED"
        activeMode="PHYSICAL"
        selectedScenarioId="TRUJILLO_00260_00608"
      />
    )

    // Verify identity preserved despite quarantine
    expect(screen.getByTestId('quarantine-banner')).toBeInTheDocument()
    expect(screen.getByTestId('provenance-badge')).toHaveTextContent('FUSION STATUS: PROVENANCE LIMITED')
    expect(screen.getByText(/job_orig_12345678/)).toBeInTheDocument()
    expect(screen.getAllByText(/TRUJILLO_00007_01339/)[0]).toBeInTheDocument()
    unmount()
  })

  // 40. Quarantined evidence cannot silently become active for the new context (selection neutralized)
  it('40. Quarantined evidence cannot silently become active for the new context', () => {
    const mockRealResult: JobResultResponse = {
      ...mockResult,
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00007_01339',
      provenance_class: 'REAL_REPOSITORY_SCENARIO_WITH_SYNTHETIC_DEPENDENCY',
    }

    const onSelectEvidenceMock = vi.fn()

    const { unmount } = render(
      <RightInspector
        result={mockRealResult}
        selectedEvidenceId={null}
        onSelectEvidence={onSelectEvidenceMock}
        selectedLocation={null}
        selectionType="NONE"
        onClearLocation={vi.fn()}
        resultFreshness="CACHED_LAST_LOADED"
        activeMode="REAL_REPOSITORY"
        selectedScenarioId="TRUJILLO_00260_00608"
      />
    )

    // Find candidate card and attempt click
    const candidateName = screen.getByText('MT_HORIZON_STAR')
    fireEvent.click(candidateName)

    // Selection callback must NOT be called when evidence is quarantined
    expect(onSelectEvidenceMock).not.toHaveBeenCalled()
    unmount()
  })

  // 41. Fresh execution for newly selected context removes quarantine only after new result is successfully loaded
  it('41. Fresh execution for newly selected context removes quarantine only after new result is loaded', async () => {
    const jobScenarioA: JobResponse = {
      ...mockJob,
      job_id: 'job_scenario_A',
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00007_01339',
    }
    const resultScenarioA: JobResultResponse = {
      ...mockResult,
      job_id: 'job_scenario_A',
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00007_01339',
    }
    const jobScenarioB: JobResponse = {
      ...mockJob,
      job_id: 'job_scenario_B',
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00260_00608',
    }
    const resultScenarioB: JobResultResponse = {
      ...mockResult,
      job_id: 'job_scenario_B',
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00260_00608',
    }

    vi.spyOn(oceanSentinelApi, 'listJobs').mockResolvedValue({
      total_jobs: 1,
      limit: 10,
      jobs: [jobScenarioA],
    })
    vi.spyOn(oceanSentinelApi, 'getJobResult').mockImplementation(async (id: string) => {
      if (id === 'job_scenario_B') return resultScenarioB
      return resultScenarioA
    })
    vi.spyOn(oceanSentinelApi, 'createJob').mockResolvedValue(jobScenarioB)
    vi.spyOn(oceanSentinelApi, 'getJob').mockImplementation(async (id: string) => {
      if (id === 'job_scenario_B') return jobScenarioB
      return jobScenarioA
    })

    const { unmount } = render(<App />)

    // Wait for initial job load to settle
    await waitFor(() => {
      expect(screen.getAllByText('job_scenario_A')[0]).toBeInTheDocument()
    })

    // Switch to REAL REPOSITORY
    fireEvent.click(screen.getByRole('button', { name: /REAL REPOSITORY/i }))
    await waitFor(() => {
      expect(screen.getByTestId('scenario-select')).toBeInTheDocument()
    })

    // Select scenario B -> mismatch with Job A
    fireEvent.change(screen.getByTestId('scenario-select'), { target: { value: 'TRUJILLO_00260_00608' } })
    await waitFor(() => {
      expect(screen.getByTestId('quarantine-status-badge')).toBeInTheDocument()
    })

    // Now execute fresh investigation for scenario B
    const runBtn = screen.getByTestId('run-real-investigation-btn')
    fireEvent.click(runBtn)

    // After fresh B result loads, quarantine lifts and resultFreshness becomes LIVE_CURRENT
    await waitFor(() => {
      expect(screen.queryByTestId('quarantine-status-badge')).not.toBeInTheDocument()
      expect(screen.getByTestId('result-freshness-badge')).toHaveTextContent('● LIVE CURRENT')
    })
    unmount()
  })

  // 42. Reconnecting the backend does NOT remove quarantine
  it('42. Reconnecting backend does NOT remove quarantine when context is mismatched', async () => {
    const jobScenarioA: JobResponse = {
      ...mockJob,
      job_id: 'job_scenario_A',
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00007_01339',
    }
    const resultScenarioA: JobResultResponse = {
      ...mockResult,
      job_id: 'job_scenario_A',
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00007_01339',
    }

    vi.spyOn(oceanSentinelApi, 'listJobs').mockResolvedValue({
      total_jobs: 1,
      limit: 10,
      jobs: [jobScenarioA],
    })
    vi.spyOn(oceanSentinelApi, 'getJobResult').mockResolvedValue(resultScenarioA)

    const { unmount } = render(<App />)

    await waitFor(() => {
      expect(screen.getAllByText('job_scenario_A')[0]).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: /REAL REPOSITORY/i }))

    await waitFor(() => {
      expect(screen.getByTestId('scenario-select')).toBeInTheDocument()
    })

    // Change to Scenario B -> Quarantined
    fireEvent.change(screen.getByTestId('scenario-select'), { target: { value: 'TRUJILLO_00260_00608' } })
    await waitFor(() => {
      expect(screen.getByTestId('quarantine-status-badge')).toBeInTheDocument()
    })

    // Backend is still ONLINE, but quarantine remains strictly enforced
    expect(screen.getByText('BACKEND ONLINE')).toBeInTheDocument()
    expect(screen.getByTestId('quarantine-status-badge')).toBeInTheDocument()
    unmount()
  })

  // 43. Browser refresh does NOT remove quarantine
  it('43. Browser refresh / initial mount retains quarantine when latest cached job is mismatched', async () => {
    // If backend returns a Job from Scenario A on mount, but default/persisted selection is Scenario B
    const jobScenarioA: JobResponse = {
      ...mockJob,
      job_id: 'job_scenario_A',
      mode: 'DEMO', // Cached result is DEMO
      pipeline_type: 'DEMO_FUSION',
    }

    vi.spyOn(oceanSentinelApi, 'listJobs').mockResolvedValue({
      total_jobs: 1,
      limit: 10,
      jobs: [jobScenarioA],
    })

    const { unmount } = render(<App />)

    await waitFor(() => {
      expect(screen.getAllByText('job_scenario_A')[0]).toBeInTheDocument()
    })

    // Switch to REAL_REPOSITORY without executing -> Mode mismatch causes quarantine
    fireEvent.click(screen.getByTestId('mode-real-repo-btn'))

    await waitFor(() => {
      expect(screen.getByTestId('quarantine-status-badge')).toBeInTheDocument()
      expect(screen.getByTestId('result-freshness-badge')).toHaveTextContent('LAST LOADED RESULT')
    })
    unmount()
  })

  // 44. Switching back to original scenario/mode restores normal display without rewriting provenance
  it('44. Switching back to original scenario/mode restores normal display without rewriting provenance', async () => {
    const jobScenarioA: JobResponse = {
      ...mockJob,
      job_id: 'job_scenario_A',
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00007_01339',
    }
    const resultScenarioA: JobResultResponse = {
      ...mockResult,
      job_id: 'job_scenario_A',
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00007_01339',
      provenance_class: 'REAL_REPOSITORY_SCENARIO_WITH_SYNTHETIC_DEPENDENCY',
    }

    vi.spyOn(oceanSentinelApi, 'listJobs').mockResolvedValue({
      total_jobs: 1,
      limit: 10,
      jobs: [jobScenarioA],
    })
    vi.spyOn(oceanSentinelApi, 'getJobResult').mockResolvedValue(resultScenarioA)

    const { unmount } = render(<App />)

    await waitFor(() => {
      expect(screen.getAllByText('job_scenario_A')[0]).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: /REAL REPOSITORY/i }))

    await waitFor(() => {
      expect(screen.getByTestId('scenario-select')).toBeInTheDocument()
    })

    // 1. Switch to B -> Quarantined
    fireEvent.change(screen.getByTestId('scenario-select'), { target: { value: 'TRUJILLO_00260_00608' } })
    await waitFor(() => {
      expect(screen.getByTestId('quarantine-status-badge')).toBeInTheDocument()
    })

    // 2. Switch back to A -> Quarantine removed automatically
    fireEvent.change(screen.getByTestId('scenario-select'), { target: { value: 'TRUJILLO_00007_01339' } })
    await waitFor(() => {
      expect(screen.queryByTestId('quarantine-status-badge')).not.toBeInTheDocument()
      expect(screen.queryByTestId('scenario-mismatch-banner')).not.toBeInTheDocument()
    })
    unmount()
  })

  // 45. TopBar renders LIVE_CURRENT + PROVENANCE_LIMITED independently alongside JOB_STATE
  it('45. TopBar renders LIVE_CURRENT + PROVENANCE_LIMITED independently alongside JOB_STATE', () => {
    const { unmount } = render(
      <TopBar
        activeMode="REAL_REPOSITORY"
        onModeChange={vi.fn()}
        currentJob={{
          ...mockJob,
          job_id: 'job_fresh_scenario_b',
          status: 'SUCCEEDED',
        }}
        connectionStatus="ONLINE"
        applicationGate="READY"
        resultFreshness="LIVE_CURRENT"
        resultUsage="ACTIVE"
        scientificValidity="PROVENANCE_LIMITED"
      />
    )

    // Verify all badges render independently and simultaneously
    expect(screen.getByText('SUCCEEDED')).toBeInTheDocument()
    expect(screen.getByTestId('result-freshness-badge')).toHaveTextContent('● LIVE CURRENT')
    expect(screen.getByTestId('scientific-validity-badge')).toHaveTextContent('PROVENANCE LIMITED')
    expect(screen.getByTestId('operational-gate-indicator')).toBeInTheDocument()
    expect(screen.getByText('BACKEND ONLINE')).toBeInTheDocument()
    unmount()
  })

  // 46. BLOCKED_PROVENANCE duplicate job produces no scientific result, freshness NONE, and validity BLOCKED
  it('46. BLOCKED_PROVENANCE duplicate job produces no scientific result, freshness NONE, and validity BLOCKED', async () => {
    const blockedJob: JobResponse = {
      ...mockJob,
      job_id: 'job_duplicate_blocked',
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00007_01339',
      status: 'BLOCKED_PROVENANCE',
      stage_status: {
        VALIDATE: { status: 'COMPLETED' },
        INGEST: { status: 'SKIPPED', message: 'Ingest stopped: T0 and T1 source rasters are byte-for-byte identical duplicates.' },
        INFER: { status: 'SKIPPED' },
        INTERPRET: { status: 'SKIPPED' },
        TEMPORAL: { status: 'BLOCKED', message: 'T0 and T1 source rasters are identical' },
        DRIFT: { status: 'BLOCKED' },
        AIS: { status: 'BLOCKED' },
        FUSION: { status: 'BLOCKED' },
      },
    }

    vi.spyOn(oceanSentinelApi, 'listJobs').mockResolvedValue({
      total_jobs: 0,
      limit: 10,
      jobs: [],
    })
    vi.spyOn(oceanSentinelApi, 'createJob').mockResolvedValue(blockedJob)
    vi.spyOn(oceanSentinelApi, 'getJob').mockResolvedValue(blockedJob)

    const { unmount } = render(<App />)

    // Switch to REAL REPOSITORY
    fireEvent.click(screen.getByRole('button', { name: /REAL REPOSITORY/i }))

    await waitFor(() => {
      expect(screen.getByTestId('run-real-investigation-btn')).toBeInTheDocument()
    })

    // Click Run Real Investigation for duplicate scenario
    fireEvent.click(screen.getByTestId('run-real-investigation-btn'))

    await waitFor(() => {
      // Job state shows BLOCKED_PROVENANCE (TopBar + stages manifest)
      expect(screen.getAllByText('BLOCKED_PROVENANCE')[0]).toBeInTheDocument()
      // Scientific validity badge shows SCIENTIFIC RESULT: BLOCKED
      expect(screen.getByTestId('scientific-validity-badge')).toHaveTextContent('SCIENTIFIC RESULT: BLOCKED')
      // Result freshness is NONE (so live current badge is absent)
      expect(screen.queryByTestId('result-freshness-badge')).not.toBeInTheDocument()
    })
    unmount()
  })

  // 47. Temporal blocked stage disables timeline only while upstream SAR remains valid
  it('47. Temporal blocked stage disables timeline only while upstream SAR remains valid', () => {
    const onPhaseChangeMock = vi.fn()
    const { unmount } = render(
      <BottomTimeline
        currentPhaseIndex={0}
        onPhaseChange={onPhaseChangeMock}
        result={mockResult}
        isQuarantined={false}
        isTemporalBlocked={true}
      />
    )

    // Header displays TEMPORAL REASONING BLOCKED
    expect(screen.getByTestId('timeline-temporal-blocked-badge')).toHaveTextContent('TEMPORAL REASONING BLOCKED')

    // Play button is disabled
    const playBtn = screen.getByTestId('timeline-play-btn')
    expect(playBtn).toBeDisabled()
    fireEvent.click(playBtn)
    expect(onPhaseChangeMock).not.toHaveBeenCalled()

    // Timeline step node click is blocked
    const stepNode = screen.getByTestId('timeline-node-t1_detection')
    fireEvent.click(stepNode)
    expect(onPhaseChangeMock).not.toHaveBeenCalled()
    unmount()
  })

  // 48. Evidence pills neutralized while quarantined, but safe inspection remains operational
  it('48. Evidence pills neutralized while quarantined, but safe inspection remains operational', () => {
    const mockCandidateWithEvidence: JobResultResponse = {
      ...mockResult,
      candidate_vessel_hypotheses: [
        {
          hypothesis_id: 'hyp_vessel_1',
          mmsi: '368123450',
          vessel_name: 'MT_TEST_CARRIER',
          evidence_compatibility_score: 0.92,
          closest_approach_distance_m: 120,
          temporal_offset_hours: 0.5,
          inside_origin_region: true,
          overall_status: 'SUPPORTED_BY_EVIDENCE',
          coverage_status: 'OBSERVED',
          supporting_evidence_ids: ['ev_sar_1', 'ev_sar_2'],
          conflicting_evidence_ids: ['ev_ais_1'],
          unknown_evidence_ids: ['ev_gap_1'],
          limitations: ['Synthetic AIS feed assumption'],
        },
      ],
    }

    const onSelectEvidenceMock = vi.fn()

    const { unmount } = render(
      <RightInspector
        result={mockCandidateWithEvidence}
        selectedEvidenceId={null}
        onSelectEvidence={onSelectEvidenceMock}
        selectedLocation={null}
        selectionType="NONE"
        onClearLocation={vi.fn()}
        resultFreshness="CACHED_LAST_LOADED"
        activeMode="REAL_REPOSITORY"
        selectedScenarioId="TRUJILLO_00260_00608"
        isQuarantined={true}
      />
    )

    // Evidence pill is neutralized
    const pill = screen.getByText('ev_sar_1')
    fireEvent.click(pill)
    expect(onSelectEvidenceMock).not.toHaveBeenCalled()

    // Safe inspection: accordion toggles work freely
    const limitationsHeader = screen.getByText(/SCIENTIFIC LIMITATIONS/i)
    fireEvent.click(limitationsHeader)
    // Click again to re-expand
    fireEvent.click(limitationsHeader)
    expect(screen.getByText('Synthetic AIS feed assumption')).toBeInTheDocument()
    unmount()
  })

  // 49. Level 2 Gate: Matching context does NOT activate a BLOCKED stage in timeline controller
  it('49. Level 2 Gate: Matching context does NOT activate a BLOCKED stage in timeline controller', () => {
    const onPhaseChangeMock = vi.fn()
    // Even when isQuarantined is false (matching context), isTemporalBlocked blocks timeline controls
    const { unmount } = render(
      <BottomTimeline
        currentPhaseIndex={0}
        onPhaseChange={onPhaseChangeMock}
        result={mockResult}
        isQuarantined={false}
        isTemporalBlocked={true}
      />
    )

    expect(screen.getByTestId('timeline-temporal-blocked-badge')).toBeInTheDocument()
    expect(screen.getByTestId('timeline-play-btn')).toBeDisabled()
    expect(screen.getByTestId('timeline-next-btn')).toBeDisabled()
    expect(screen.getByTestId('timeline-prev-btn')).toBeDisabled()
    unmount()
  })

  // 50. GlobeView neutralizes evidence interaction during quarantine but preserves operator-reference click
  it('50. GlobeView neutralizes evidence interaction during quarantine but preserves operator-reference click', () => {
    const onSelectEvidenceMock = vi.fn()
    const onSelectLocationMock = vi.fn()

    const { unmount } = render(
      <GlobeView
        result={mockResult}
        selectedEvidenceId={null}
        onSelectEvidence={onSelectEvidenceMock}
        selectedLocation={null}
        onSelectLocation={onSelectLocationMock}
        layers={{
          sar_detection: true,
          temporal_change: true,
          drift_trajectory: true,
          drift_origin: true,
          ais_tracks: true,
          fused_evidence: true,
          hypotheses: true,
        }}
        isLoading={false}
        isQuarantined={true}
      />
    )

    // Quarantine watermark must be displayed on Globe
    expect(screen.getByTestId('globe-quarantine-watermark')).toBeInTheDocument()
    unmount()
  })

  // 51. Result retrieval failure after job acceptance never promotes freshness to LIVE_CURRENT
  it('51. Result retrieval failure after job acceptance never promotes freshness to LIVE_CURRENT', async () => {
    const successJob: JobResponse = {
      ...mockJob,
      job_id: 'job_retrieval_fail',
      status: 'SUCCEEDED',
    }

    vi.spyOn(oceanSentinelApi, 'createJob').mockResolvedValue(successJob)
    vi.spyOn(oceanSentinelApi, 'getJobResult').mockRejectedValue(new Error('Result payload corrupted'))

    const { unmount } = render(<App />)

    const runBtn = screen.getByTestId('run-demo-fusion-btn')
    fireEvent.click(runBtn)

    await waitFor(() => {
      // Must not display LIVE CURRENT
      expect(screen.queryByText('● LIVE CURRENT')).not.toBeInTheDocument()
    })
    unmount()
  })

  // 52. Result identity/context mismatch after retrieval sets CACHED_LAST_LOADED, not LIVE_CURRENT
  it('52. Result identity/context mismatch after retrieval sets CACHED_LAST_LOADED, not LIVE_CURRENT', async () => {
    const mismatchedResult: JobResultResponse = {
      ...mockResult,
      job_id: 'job_scenario_b_fresh',
      mode: 'REAL_REPOSITORY',
      scenario_id: 'UNEXPECTED_SCENARIO', // mismatch with selected scenario
    }

    const jobB: JobResponse = {
      ...mockJob,
      job_id: 'job_scenario_b_fresh',
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00260_00608',
      status: 'SUCCEEDED',
    }

    vi.spyOn(oceanSentinelApi, 'listJobs').mockResolvedValue({
      total_jobs: 0,
      limit: 10,
      jobs: [],
    })
    vi.spyOn(oceanSentinelApi, 'listScenarios').mockResolvedValue({
      total_scenarios: 2,
      scenarios: [
        mockScenario,
        {
          ...mockScenario,
          scenario_id: 'TRUJILLO_00260_00608',
          label: 'Trujillo Scene 00260 / 00608',
        },
      ],
    })
    vi.spyOn(oceanSentinelApi, 'createJob').mockResolvedValue(jobB)
    vi.spyOn(oceanSentinelApi, 'getJobResult').mockResolvedValue(mismatchedResult)

    const { unmount } = render(<App />)
    fireEvent.click(screen.getByRole('button', { name: /REAL REPOSITORY/i }))

    await waitFor(() => {
      expect(screen.getByTestId('run-real-investigation-btn')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByTestId('run-real-investigation-btn'))

    await waitFor(() => {
      // Because scenario_id mismatched, must NOT be LIVE_CURRENT
      expect(screen.queryByText('● LIVE CURRENT')).not.toBeInTheDocument()
      // Instead marked LAST LOADED RESULT (CACHED)
      expect(screen.getByTestId('result-freshness-badge')).toHaveTextContent('LAST LOADED RESULT')
    })
    unmount()
  })

  // 53. Stale-result race: starting a new execution immediately demotes prior LIVE_CURRENT to CACHED
  it('53. Stale-result race: starting a new execution immediately demotes prior LIVE_CURRENT to CACHED', async () => {
    let resolveCreateJob: (value: any) => void
    const pendingCreateJob = new Promise((resolve) => {
      resolveCreateJob = resolve
    })

    vi.spyOn(oceanSentinelApi, 'createJob').mockImplementation(() => pendingCreateJob as any)

    const { unmount } = render(<App />)

    // First load fresh result
    const runBtn = screen.getByTestId('run-demo-fusion-btn')
    fireEvent.click(runBtn)

    // While execution is pending, freshness badge is not falsely LIVE_CURRENT
    expect(screen.queryByText('● LIVE CURRENT')).not.toBeInTheDocument()

    // Resolve createJob as SUCCEEDED
    resolveCreateJob!({
      ...mockJob,
      job_id: 'job_async_1',
      status: 'SUCCEEDED',
    })
    unmount()
  })

  // 54. Blocked replacement execution purges stale evidence and sets freshness to NONE
  it('54. Blocked replacement execution purges stale evidence and sets freshness to NONE', async () => {
    const blockedJob: JobResponse = {
      ...mockJob,
      job_id: 'job_blocked_replacement',
      mode: 'REAL_REPOSITORY',
      status: 'BLOCKED_PROVENANCE',
      error: {
        code: 'BLOCKED_PROVENANCE',
        message: 'Duplicate raster pair rejected',
      },
    }

    vi.spyOn(oceanSentinelApi, 'listJobs').mockResolvedValue({
      total_jobs: 0,
      limit: 10,
      jobs: [],
    })
    vi.spyOn(oceanSentinelApi, 'listScenarios').mockResolvedValue({
      total_scenarios: 1,
      scenarios: [mockScenario],
    })
    vi.spyOn(oceanSentinelApi, 'createJob').mockResolvedValue(blockedJob)

    const { unmount } = render(<App />)
    fireEvent.click(screen.getByRole('button', { name: /REAL REPOSITORY/i }))

    await waitFor(() => {
      expect(screen.getByTestId('run-real-investigation-btn')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByTestId('run-real-investigation-btn'))

    await waitFor(() => {
      // Prior results purged, freshness NONE
      expect(screen.queryByTestId('result-freshness-badge')).not.toBeInTheDocument()
      expect(screen.getByTestId('scientific-validity-badge')).toHaveTextContent('SCIENTIFIC RESULT: BLOCKED')
    })
    unmount()
  })

  // 55. Keyboard activation on candidate cards and evidence pills is neutralized while quarantined
  it('55. Keyboard activation on candidate cards and evidence pills is neutralized while quarantined', () => {
    const onSelectEvidenceMock = vi.fn()
    const mockCandidateWithPills: JobResultResponse = {
      ...mockResult,
      candidate_vessel_hypotheses: [
        {
          hypothesis_id: 'hyp_vessel_kb',
          mmsi: '368123450',
          vessel_name: 'MT_KEYBOARD_TEST',
          evidence_compatibility_score: 0.88,
          closest_approach_distance_m: 150,
          temporal_offset_hours: 0.2,
          inside_origin_region: true,
          overall_status: 'SUPPORTED_BY_EVIDENCE',
          coverage_status: 'OBSERVED',
          supporting_evidence_ids: ['ev_kb_1'],
          conflicting_evidence_ids: [],
          unknown_evidence_ids: [],
          limitations: [],
        },
      ],
    }

    const { unmount } = render(
      <RightInspector
        result={mockCandidateWithPills}
        selectedEvidenceId={null}
        onSelectEvidence={onSelectEvidenceMock}
        selectedLocation={null}
        selectionType="NONE"
        onClearLocation={vi.fn()}
        resultFreshness="CACHED_LAST_LOADED"
        activeMode="REAL_REPOSITORY"
        selectedScenarioId="TRUJILLO_00260_00608"
        isQuarantined={true}
      />
    )

    // Select candidate card via Enter key
    const card = screen.getByRole('button', { name: /MT_KEYBOARD_TEST/i })
    fireEvent.keyDown(card, { key: 'Enter', code: 'Enter' })
    expect(onSelectEvidenceMock).not.toHaveBeenCalled()

    // Select candidate card via Space key
    fireEvent.keyDown(card, { key: ' ', code: 'Space' })
    expect(onSelectEvidenceMock).not.toHaveBeenCalled()

    // Select pill via Enter key
    const pill = screen.getByRole('button', { name: /ev_kb_1/i })
    fireEvent.keyDown(pill, { key: 'Enter', code: 'Enter' })
    expect(onSelectEvidenceMock).not.toHaveBeenCalled()

    unmount()
  })

  // 56. Case B execution disables BottomTimeline operational controls due to unverified chronology (TEMPORAL BLOCKED) while keeping SAR evidence selectable and inspectable
  it('56. Case B execution disables BottomTimeline operational controls due to unverified chronology while keeping SAR evidence selectable', async () => {
    const scenarioBJob: JobResponse = {
      ...mockJob,
      job_id: 'job_scenario_b_temporal_test',
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00260_00608',
      status: 'SUCCEEDED',
      stage_status: {
        VALIDATE: { status: 'COMPLETED' },
        INGEST: { status: 'COMPLETED' },
        INFER: { status: 'SKIPPED' },
        INTERPRET: { status: 'SKIPPED' },
        TEMPORAL: { status: 'COMPLETED' },
        DRIFT: { status: 'COMPLETED' },
        AIS: { status: 'COMPLETED' },
        FUSION: { status: 'COMPLETED' },
        EXPORT: { status: 'COMPLETED' },
      },
    }

    const scenarioBResult: JobResultResponse = {
      ...mockResult,
      job_id: 'job_scenario_b_temporal_test',
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00260_00608',
      provenance_class: 'REAL_REPOSITORY_SCENARIO_WITH_SYNTHETIC_DEPENDENCY',
      provenance_status: 'PROVENANCE_LIMITED',
      has_synthetic_dependencies: true,
      scenario_metadata: {
        scenario_id: 'TRUJILLO_00260_00608',
        label: 'Trujillo 2024 S1 Scene Pair 00260 / 00608 (Gulf of Mexico)',
        dataset: 'Trujillo et al., 2024 Sentinel-1 SAR Oil Spill Dataset',
        scene_pair: ['00260', '00608'],
        region: 'Gulf of Mexico',
        centroid: [-90.386402, 27.0864],
        event_id: '00260_00608_new_0010',
        artifacts: {},
        acquisition_timestamps: {},
        satellite_product_id: 'METADATA UNAVAILABLE',
        vessel_truth: 'METADATA UNAVAILABLE',
        physical_incident_label: 'METADATA UNAVAILABLE',
        unverified_source_metadata: 'METADATA UNAVAILABLE',
        provenance_class: 'REAL_REPOSITORY_SCENARIO_WITH_SYNTHETIC_DEPENDENCY',
        temporal_status: 'BLOCKED_AWAITING_AUTHORITATIVE_TIMESTAMPS',
        reason: 'TEMPORAL_ORDER_UNKNOWN',
        lineage_status: 'CURRENT',
        stage_provenance: {
          satellite: 'HISTORICAL_ARCHIVE',
          temporal: 'BLOCKED',
          drift: 'SYNTHETIC_DEMO',
          ais: 'SYNTHETIC_DEMO',
        },
        limitations: [],
      },
      candidate_vessel_hypotheses: [
        {
          hypothesis_id: 'hyp_sar_vessel_001',
          mmsi: '368123450',
          vessel_name: 'MT_HORIZON_STAR',
          evidence_compatibility_score: 0.9111,
          closest_approach_distance_m: 882,
          temporal_offset_hours: 0.8,
          inside_origin_region: true,
          overall_status: 'SUPPORTED_BY_AVAILABLE_EVIDENCE',
          coverage_status: 'OBSERVED',
          supporting_evidence_ids: ['ev_sar_1'],
          conflicting_evidence_ids: [],
          unknown_evidence_ids: [],
          limitations: [],
        },
      ],
    }

    vi.spyOn(oceanSentinelApi, 'listJobs').mockResolvedValue({
      total_jobs: 1,
      limit: 10,
      jobs: [scenarioBJob],
    })
    vi.spyOn(oceanSentinelApi, 'getJobResult').mockResolvedValue(scenarioBResult)

    const { unmount } = render(<App />)

    // Select Scenario B in scenario dropdown so context matches loaded result
    await waitFor(() => {
      expect(screen.getByTestId('scenario-select')).toBeInTheDocument()
    })
    fireEvent.change(screen.getByTestId('scenario-select'), {
      target: { value: 'TRUJILLO_00260_00608' },
    })

    // Wait for Scenario B to be active and verify TEMPORAL REASONING BLOCKED badge
    await waitFor(() => {
      expect(screen.getByTestId('timeline-temporal-blocked-badge')).toBeInTheDocument()
      expect(screen.getByTestId('timeline-temporal-blocked-badge')).toHaveTextContent('TEMPORAL REASONING BLOCKED')
    })

    // Verify timeline operational controls are disabled
    expect(screen.getByTestId('timeline-play-btn')).toBeDisabled()
    expect(screen.getByTestId('timeline-prev-btn')).toBeDisabled()
    expect(screen.getByTestId('timeline-next-btn')).toBeDisabled()

    // Verify SAR candidate vessel in RightInspector remains operational & selectable
    const candidateName = screen.getByText('MT_HORIZON_STAR')
    expect(candidateName).toBeInTheDocument()
    fireEvent.click(candidateName)

    // Vessel card was clicked; verify inspector surfaces vessel details
    await waitFor(() => {
      expect(screen.getByText('368123450')).toBeInTheDocument()
      expect(screen.getByText(/0.9111/)).toBeInTheDocument()
    })

    unmount()
  })

  // 57. Async race condition: delayed getJobResult from older dispatch does not overwrite newer dispatch state
  it('57. Async race condition: delayed getJobResult from older dispatch does not overwrite newer dispatch state', async () => {
    let resolveOldResult: (value: JobResultResponse) => void = () => {}
    const oldResultPromise = new Promise<JobResultResponse>((resolve) => {
      resolveOldResult = resolve
    })

    const jobA: JobResponse = {
      ...mockJob,
      job_id: 'job_A_slow',
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00260_00608',
      status: 'SUCCEEDED',
    }
    const resultA: JobResultResponse = {
      ...mockResult,
      job_id: 'job_A_slow',
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00260_00608',
      investigation_label: 'OLD_JOB_A',
    }

    const jobB: JobResponse = {
      ...mockJob,
      job_id: 'job_B_fast',
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00260_00608',
      status: 'SUCCEEDED',
    }
    const resultB: JobResultResponse = {
      ...mockResult,
      job_id: 'job_B_fast',
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00260_00608',
      investigation_label: 'NEW_JOB_B',
    }

    vi.spyOn(oceanSentinelApi, 'listJobs').mockResolvedValue({
      total_jobs: 0,
      limit: 10,
      jobs: [],
    })

    vi.spyOn(oceanSentinelApi, 'createJob')
      .mockResolvedValueOnce(jobA)
      .mockResolvedValueOnce(jobB)

    vi.spyOn(oceanSentinelApi, 'getJobResult')
      .mockImplementation((id: string) => {
        if (id === 'job_A_slow') return oldResultPromise
        if (id === 'job_B_fast') return Promise.resolve(resultB)
        return Promise.resolve(mockResult)
      })

    const { unmount } = render(<App />)

    fireEvent.click(screen.getByRole('button', { name: /REAL REPOSITORY/i }))

    await waitFor(() => {
      expect(screen.getByTestId('scenario-select')).toBeInTheDocument()
      expect(screen.getByTestId('run-real-investigation-btn')).toBeInTheDocument()
    })

    fireEvent.change(screen.getByTestId('scenario-select'), {
      target: { value: 'TRUJILLO_00260_00608' },
    })

    // Start Job A
    fireEvent.click(screen.getByTestId('run-real-investigation-btn'))

    await waitFor(() => {
      expect(screen.getAllByText('job_A_slow')[0]).toBeInTheDocument()
    })

    // While Job A's result is still pending, dispatch Job B
    fireEvent.click(screen.getByTestId('run-real-investigation-btn'))

    await waitFor(() => {
      expect(screen.getAllByText('job_B_fast')[0]).toBeInTheDocument()
      expect(screen.getByTestId('result-freshness-badge')).toHaveTextContent('● LIVE CURRENT')
    })

    // Now resolve the delayed Job A result
    resolveOldResult(resultA)

    // Wait a tick and assert Job B remains active and was NOT overwritten by Job A
    await new Promise((r) => setTimeout(r, 50))

    expect(screen.getAllByText('job_B_fast')[0]).toBeInTheDocument()
    expect(screen.queryByText('OLD_JOB_A')).not.toBeInTheDocument()
    expect(screen.getByTestId('result-freshness-badge')).toHaveTextContent('● LIVE CURRENT')

    unmount()
  })

  // 58. Async race condition: delayed getJobResult from older dispatch cannot resurrect purged evidence after blocked job
  it('58. Async race condition: delayed getJobResult from older dispatch cannot resurrect purged evidence after blocked job', async () => {
    let resolveOldResult: (value: JobResultResponse) => void = () => {}
    const oldResultPromise = new Promise<JobResultResponse>((resolve) => {
      resolveOldResult = resolve
    })

    const jobA: JobResponse = {
      ...mockJob,
      job_id: 'job_A_slow',
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00260_00608',
      status: 'SUCCEEDED',
    }
    const resultA: JobResultResponse = {
      ...mockResult,
      job_id: 'job_A_slow',
      scenario_id: 'TRUJILLO_00260_00608',
      candidate_vessel_hypotheses: [
        {
          hypothesis_id: 'ghost_vessel_A',
          mmsi: '999999999',
          vessel_name: 'GHOST_VESSEL_A',
          closest_approach_distance_m: 50,
          closest_approach_time_utc: '2024-04-10T14:00:00Z',
          temporal_offset_hours: 0,
          is_position_inferred: false,
          inside_origin_region: true,
          inside_trajectory_envelope: true,
          coverage_status: 'OBSERVED',
          evidence_compatibility_score: 0.99,
          supporting_evidence_ids: [],
          conflicting_evidence_ids: [],
          consistent_evidence_ids: [],
        },
      ],
    }

    const jobBlocked: JobResponse = {
      ...mockJob,
      job_id: 'job_duplicate_blocked',
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00007_01339',
      status: 'BLOCKED_PROVENANCE',
      error: {
        code: 'BLOCKED_PROVENANCE',
        message: 'Scenario execution blocked by provenance gate: duplicate raster pair.',
        stage: 'INGEST',
      },
    }

    vi.spyOn(oceanSentinelApi, 'listJobs').mockResolvedValue({
      total_jobs: 0,
      limit: 10,
      jobs: [],
    })

    vi.spyOn(oceanSentinelApi, 'createJob')
      .mockResolvedValueOnce(jobA)
      .mockResolvedValueOnce(jobBlocked)

    vi.spyOn(oceanSentinelApi, 'getJobResult')
      .mockImplementation((id: string) => {
        if (id === 'job_A_slow') return oldResultPromise
        return Promise.reject(new Error('No result'))
      })

    const { unmount } = render(<App />)

    fireEvent.click(screen.getByRole('button', { name: /REAL REPOSITORY/i }))

    await waitFor(() => {
      expect(screen.getByTestId('run-real-investigation-btn')).toBeInTheDocument()
    })

    // Select Scenario B for Job A
    fireEvent.change(screen.getByTestId('scenario-select'), {
      target: { value: 'TRUJILLO_00260_00608' },
    })

    // Start Job A
    fireEvent.click(screen.getByTestId('run-real-investigation-btn'))

    await waitFor(() => {
      expect(screen.getAllByText('job_A_slow')[0]).toBeInTheDocument()
    })

    // Switch to duplicate scenario and dispatch blocked job
    fireEvent.change(screen.getByTestId('scenario-select'), {
      target: { value: 'TRUJILLO_00007_01339' },
    })
    fireEvent.click(screen.getByTestId('run-real-investigation-btn'))

    // Verify duplicate job fails closed: job is BLOCKED_PROVENANCE, scientific validity is BLOCKED, but Application Gate remains READY
    await waitFor(() => {
      expect(screen.getAllByText('job_duplicate_blocked')[0]).toBeInTheDocument()
      expect(screen.getByTestId('operational-gate-indicator')).toHaveTextContent('APPLICATION GATE: READY')
      expect(screen.getByTestId('scientific-validity-badge')).toHaveTextContent('SCIENTIFIC RESULT: BLOCKED')
    })

    // Now resolve Job A's slow result
    resolveOldResult(resultA)

    // Wait a tick and verify Job A's ghost vessel did NOT resurrect
    await new Promise((r) => setTimeout(r, 50))

    expect(screen.queryByText('GHOST_VESSEL_A')).not.toBeInTheDocument()
    expect(screen.getAllByText('job_duplicate_blocked')[0]).toBeInTheDocument()
    expect(screen.getByTestId('operational-gate-indicator')).toHaveTextContent('APPLICATION GATE: READY')
    expect(screen.getByTestId('scientific-validity-badge')).toHaveTextContent('SCIENTIFIC RESULT: BLOCKED')

    unmount()
  })

  // 59. Temporal actionability: stage computation COMPLETED with unverified chronology disables timeline controls while SAR detections remain active
  it('59. Temporal actionability: stage computation COMPLETED with unverified chronology disables timeline controls while SAR detections remain active', async () => {
    const jobScenarioB: JobResponse = {
      ...mockJob,
      job_id: 'job_temporal_prec',
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00260_00608',
      status: 'SUCCEEDED',
      stage_status: {
        VALIDATE: { status: 'COMPLETED' },
        INGEST: { status: 'COMPLETED' },
        INFER: { status: 'COMPLETED' },
        INTERPRET: { status: 'COMPLETED' },
        TEMPORAL: { status: 'COMPLETED', message: 'Temporal change raster generated successfully' },
        DRIFT: { status: 'COMPLETED' },
        AIS: { status: 'COMPLETED' },
        FUSION: { status: 'COMPLETED' },
      },
    }

    const resultScenarioB: JobResultResponse = {
      ...mockResult,
      job_id: 'job_temporal_prec',
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00260_00608',
      scenario_metadata: {
        ...mockResult.scenario_metadata!,
        scenario_id: 'TRUJILLO_00260_00608',
        temporal_status: 'BLOCKED_AWAITING_AUTHORITATIVE_TIMESTAMPS',
        reason: 'TEMPORAL_ORDER_UNKNOWN',
        stage_provenance: {
          temporal: 'BLOCKED',
        },
      },
    }

    vi.spyOn(oceanSentinelApi, 'listJobs').mockResolvedValue({
      total_jobs: 1,
      limit: 10,
      jobs: [jobScenarioB],
    })
    vi.spyOn(oceanSentinelApi, 'getJobResult').mockResolvedValue(resultScenarioB)

    const { unmount } = render(<App />)

    await waitFor(() => {
      expect(screen.getByTestId('scenario-select')).toBeInTheDocument()
    })
    fireEvent.change(screen.getByTestId('scenario-select'), {
      target: { value: 'TRUJILLO_00260_00608' },
    })

    // Assert BottomTimeline renders TEMPORAL REASONING BLOCKED and controls are disabled
    await waitFor(() => {
      expect(screen.getByTestId('timeline-temporal-blocked-badge')).toBeInTheDocument()
      expect(screen.getByTestId('timeline-temporal-blocked-badge')).toHaveTextContent('TEMPORAL REASONING BLOCKED')
    })
    expect(screen.getByTestId('timeline-play-btn')).toBeDisabled()
    expect(screen.getByTestId('timeline-prev-btn')).toBeDisabled()
    expect(screen.getByTestId('timeline-next-btn')).toBeDisabled()

    // Assert SAR detection remains inspectable
    expect(screen.getByText('MT_HORIZON_STAR')).toBeInTheDocument()
    unmount()
  })

  // 60. Temporal actionability: stage status BLOCKED disables timeline controls
  it('60. Temporal actionability: stage status BLOCKED disables timeline controls', async () => {
    const jobTemporalBlockedStage: JobResponse = {
      ...mockJob,
      job_id: 'job_temporal_stage_blocked',
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00260_00608',
      status: 'SUCCEEDED',
      stage_status: {
        TEMPORAL: { status: 'BLOCKED', message: 'Temporal differencing blocked' },
      },
    }

    vi.spyOn(oceanSentinelApi, 'listJobs').mockResolvedValue({
      total_jobs: 1,
      limit: 10,
      jobs: [jobTemporalBlockedStage],
    })
    vi.spyOn(oceanSentinelApi, 'getJobResult').mockResolvedValue({
      ...mockResult,
      job_id: 'job_temporal_stage_blocked',
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00260_00608',
    })

    const { unmount } = render(<App />)

    fireEvent.click(screen.getByRole('button', { name: /REAL REPOSITORY/i }))

    await waitFor(() => {
      expect(screen.getByTestId('scenario-select')).toBeInTheDocument()
    })
    fireEvent.change(screen.getByTestId('scenario-select'), {
      target: { value: 'TRUJILLO_00260_00608' },
    })

    await waitFor(() => {
      expect(screen.getByTestId('timeline-temporal-blocked-badge')).toBeInTheDocument()
    })
    expect(screen.getByTestId('timeline-play-btn')).toBeDisabled()
    unmount()
  })

  // 61. Application Gate separation: scenario mismatch sets RESULT_USAGE QUARANTINED while Application Gate remains READY
  it('61. Application Gate separation: scenario mismatch sets RESULT_USAGE QUARANTINED while Application Gate remains READY', async () => {
    const jobB: JobResponse = {
      ...mockJob,
      job_id: 'job_scenario_B_loaded',
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00260_00608',
      status: 'SUCCEEDED',
    }
    const resultB: JobResultResponse = {
      ...mockResult,
      job_id: 'job_scenario_B_loaded',
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00260_00608',
    }

    vi.spyOn(oceanSentinelApi, 'listJobs').mockResolvedValue({
      total_jobs: 1,
      limit: 10,
      jobs: [jobB],
    })
    vi.spyOn(oceanSentinelApi, 'getJobResult').mockResolvedValue(resultB)

    const { unmount } = render(<App />)

    fireEvent.click(screen.getByRole('button', { name: /REAL REPOSITORY/i }))

    await waitFor(() => {
      expect(screen.getByTestId('scenario-select')).toBeInTheDocument()
    })

    // Currently selected scenario is Scenario A (TRUJILLO_00007_01339), while loaded job is Scenario B
    // Therefore, scenario mismatch quarantine is active!
    await waitFor(() => {
      expect(screen.getByTestId('quarantine-status-badge')).toBeInTheDocument()
      expect(screen.getByTestId('quarantine-status-badge')).toHaveAttribute('data-result-usage', 'QUARANTINED')
    })

    // Crucial invariant: Application Gate remains READY (NOT DEGRADED or BLOCKED)
    expect(screen.getByTestId('operational-gate-indicator')).toHaveTextContent('APPLICATION GATE: READY')
    expect(screen.getByText('BACKEND ONLINE')).toBeInTheDocument()

    unmount()
  })

  // 62. Application Gate separation: mode mismatch sets RESULT_USAGE QUARANTINED while Application Gate remains READY
  it('62. Application Gate separation: mode mismatch sets RESULT_USAGE QUARANTINED while Application Gate remains READY', async () => {
    const jobReal: JobResponse = {
      ...mockJob,
      job_id: 'job_real_repo_loaded',
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00260_00608',
      status: 'SUCCEEDED',
    }
    const resultReal: JobResultResponse = {
      ...mockResult,
      job_id: 'job_real_repo_loaded',
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00260_00608',
    }

    vi.spyOn(oceanSentinelApi, 'listJobs').mockResolvedValue({
      total_jobs: 1,
      limit: 10,
      jobs: [jobReal],
    })
    vi.spyOn(oceanSentinelApi, 'getJobResult').mockResolvedValue(resultReal)

    const { unmount } = render(<App />)

    await waitFor(() => {
      expect(screen.getAllByText('job_real_repo_loaded')[0]).toBeInTheDocument()
    })

    // Switch TopBar to DEMO mode -> Mode mismatch
    fireEvent.click(screen.getByTestId('mode-demo-btn'))

    await waitFor(() => {
      expect(screen.getByTestId('quarantine-status-badge')).toBeInTheDocument()
      expect(screen.getByTestId('quarantine-status-badge')).toHaveAttribute('data-result-usage', 'QUARANTINED')
    })

    // Crucial invariant: Application Gate remains READY (NOT DEGRADED or BLOCKED)
    expect(screen.getByTestId('operational-gate-indicator')).toHaveTextContent('APPLICATION GATE: READY')
    expect(screen.getByText('BACKEND ONLINE')).toBeInTheDocument()

    unmount()
  })

  // 63. Async race: context change while result load is pending prevents LIVE_CURRENT adoption in new context
  it('63. Async race: context change while result load is pending prevents LIVE_CURRENT adoption in new context', async () => {
    let resolveResultB: (value: JobResultResponse) => void = () => {}
    const pendingResultBPromise = new Promise<JobResultResponse>((resolve) => {
      resolveResultB = resolve
    })

    const jobB: JobResponse = {
      ...mockJob,
      job_id: 'job_scenario_B_pending',
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00260_00608',
      status: 'SUCCEEDED',
    }

    const resultB: JobResultResponse = {
      ...mockResult,
      job_id: 'job_scenario_B_pending',
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00260_00608',
    }

    vi.spyOn(oceanSentinelApi, 'listJobs').mockResolvedValue({
      total_jobs: 0,
      limit: 10,
      jobs: [],
    })
    vi.spyOn(oceanSentinelApi, 'createJob').mockResolvedValue(jobB)
    vi.spyOn(oceanSentinelApi, 'getJobResult').mockReturnValue(pendingResultBPromise)

    const { unmount } = render(<App />)

    fireEvent.click(screen.getByRole('button', { name: /REAL REPOSITORY/i }))

    await waitFor(() => {
      expect(screen.getByTestId('scenario-select')).toBeInTheDocument()
      expect(screen.getByTestId('run-real-investigation-btn')).toBeInTheDocument()
    })

    // Select Scenario B
    fireEvent.change(screen.getByTestId('scenario-select'), {
      target: { value: 'TRUJILLO_00260_00608' },
    })

    // Start execution for Scenario B
    fireEvent.click(screen.getByTestId('run-real-investigation-btn'))

    await waitFor(() => {
      expect(screen.getAllByText('job_scenario_B_pending')[0]).toBeInTheDocument()
    })

    // While result retrieval is pending, operator switches dropdown back to Scenario A
    fireEvent.change(screen.getByTestId('scenario-select'), {
      target: { value: 'TRUJILLO_00007_01339' },
    })

    // Now resolve the pending Scenario B result
    resolveResultB(resultB)

    // Wait for resolution and verify B does NOT become LIVE_CURRENT in current Scenario A context
    await waitFor(() => {
      expect(screen.getByTestId('result-freshness-badge')).toHaveTextContent('LAST LOADED RESULT')
      expect(screen.queryByText('● LIVE CURRENT')).not.toBeInTheDocument()
      // Context mismatch quarantine must be active
      expect(screen.getByTestId('quarantine-status-badge')).toBeInTheDocument()
      expect(screen.getByTestId('quarantine-status-badge')).toHaveAttribute('data-result-usage', 'QUARANTINED')
    })

    unmount()
  })

  // 64. Async race: mode change while result load is pending prevents LIVE_CURRENT adoption in new mode
  it('64. Async race: mode change while result load is pending prevents LIVE_CURRENT adoption in new mode', async () => {
    let resolveResultReal: (value: JobResultResponse) => void = () => {}
    const pendingRealPromise = new Promise<JobResultResponse>((resolve) => {
      resolveResultReal = resolve
    })

    const jobReal: JobResponse = {
      ...mockJob,
      job_id: 'job_mode_race',
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00260_00608',
      status: 'SUCCEEDED',
    }

    const resultReal: JobResultResponse = {
      ...mockResult,
      job_id: 'job_mode_race',
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00260_00608',
    }

    vi.spyOn(oceanSentinelApi, 'listJobs').mockResolvedValue({
      total_jobs: 0,
      limit: 10,
      jobs: [],
    })
    vi.spyOn(oceanSentinelApi, 'createJob').mockResolvedValue(jobReal)
    vi.spyOn(oceanSentinelApi, 'getJobResult').mockReturnValue(pendingRealPromise)

    const { unmount } = render(<App />)

    fireEvent.click(screen.getByRole('button', { name: /REAL REPOSITORY/i }))

    await waitFor(() => {
      expect(screen.getByTestId('scenario-select')).toBeInTheDocument()
      expect(screen.getByTestId('run-real-investigation-btn')).toBeInTheDocument()
    })

    fireEvent.change(screen.getByTestId('scenario-select'), {
      target: { value: 'TRUJILLO_00260_00608' },
    })

    // Start execution
    fireEvent.click(screen.getByTestId('run-real-investigation-btn'))

    await waitFor(() => {
      expect(screen.getAllByText('job_mode_race')[0]).toBeInTheDocument()
    })

    // While result retrieval is pending, operator switches UI mode to DEMO
    fireEvent.click(screen.getByTestId('mode-demo-btn'))

    // Now resolve the pending REAL_REPOSITORY result
    resolveResultReal(resultReal)

    // Verify it does NOT become LIVE_CURRENT in DEMO mode
    await waitFor(() => {
      expect(screen.getByTestId('result-freshness-badge')).toHaveTextContent('LAST LOADED RESULT')
      expect(screen.queryByText('● LIVE CURRENT')).not.toBeInTheDocument()
      // Mode mismatch quarantine is active
      expect(screen.getByTestId('quarantine-status-badge')).toBeInTheDocument()
      expect(screen.getByTestId('quarantine-status-badge')).toHaveAttribute('data-result-usage', 'QUARANTINED')
    })

    unmount()
  })

  // 65. Application Gate separation: duplicate blocked job fails closed with SCIENTIFIC RESULT: BLOCKED while Application Gate remains READY
  it('65. Application Gate separation: duplicate blocked job fails closed with SCIENTIFIC RESULT: BLOCKED while Application Gate remains READY', async () => {
    const duplicateJob: JobResponse = {
      ...mockJob,
      job_id: 'job_duplicate_pure_gate_check',
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00007_01339',
      status: 'BLOCKED_PROVENANCE',
      stage_status: {
        VALIDATE: { status: 'COMPLETED' },
        INGEST: { status: 'SKIPPED', message: 'Ingest stopped: T0 and T1 source rasters are byte-for-byte identical duplicates.' },
        TEMPORAL: { status: 'BLOCKED', message: 'T0 and T1 source rasters are identical' },
      },
    }

    vi.spyOn(oceanSentinelApi, 'listJobs').mockResolvedValue({
      total_jobs: 0,
      limit: 10,
      jobs: [],
    })
    vi.spyOn(oceanSentinelApi, 'createJob').mockResolvedValue(duplicateJob)

    const { unmount } = render(<App />)

    fireEvent.click(screen.getByRole('button', { name: /REAL REPOSITORY/i }))

    await waitFor(() => {
      expect(screen.getByTestId('run-real-investigation-btn')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByTestId('run-real-investigation-btn'))

    await waitFor(() => {
      // 1. Job execution state shows BLOCKED_PROVENANCE
      expect(screen.getAllByText('BLOCKED_PROVENANCE')[0]).toBeInTheDocument()
      // 2. Scientific validity shows SCIENTIFIC RESULT: BLOCKED
      expect(screen.getByTestId('scientific-validity-badge')).toHaveTextContent('SCIENTIFIC RESULT: BLOCKED')
      // 3. Result freshness is NONE
      expect(screen.queryByTestId('result-freshness-badge')).not.toBeInTheDocument()
      // 4. Crucial invariant: APPLICATION GATE is READY (NOT BLOCKED), because backend is ONLINE and system is ready for new jobs
      expect(screen.getByTestId('operational-gate-indicator')).toHaveTextContent('APPLICATION GATE: READY')
      expect(screen.getByText('BACKEND ONLINE')).toBeInTheDocument()
    })

    unmount()
  })

  // 66. Async race: context changes away and returns to original context before response arrives adopts deterministically
  it('66. Async race: context changes away and returns to original context before response arrives adopts deterministically', async () => {
    let resolveResultB: (value: JobResultResponse) => void = () => {}
    const pendingResultBPromise = new Promise<JobResultResponse>((resolve) => {
      resolveResultB = resolve
    })

    const jobB: JobResponse = {
      ...mockJob,
      job_id: 'job_B_roundtrip',
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00260_00608',
      status: 'SUCCEEDED',
    }

    const resultB: JobResultResponse = {
      ...mockResult,
      job_id: 'job_B_roundtrip',
      mode: 'REAL_REPOSITORY',
      pipeline_type: 'REAL_REPOSITORY',
      scenario_id: 'TRUJILLO_00260_00608',
    }

    vi.spyOn(oceanSentinelApi, 'listJobs').mockResolvedValue({
      total_jobs: 0,
      limit: 10,
      jobs: [],
    })
    vi.spyOn(oceanSentinelApi, 'createJob').mockResolvedValue(jobB)
    vi.spyOn(oceanSentinelApi, 'getJobResult').mockReturnValue(pendingResultBPromise)

    const { unmount } = render(<App />)

    fireEvent.click(screen.getByRole('button', { name: /REAL REPOSITORY/i }))

    await waitFor(() => {
      expect(screen.getByTestId('scenario-select')).toBeInTheDocument()
      expect(screen.getByTestId('run-real-investigation-btn')).toBeInTheDocument()
    })

    // Select Scenario B
    fireEvent.change(screen.getByTestId('scenario-select'), {
      target: { value: 'TRUJILLO_00260_00608' },
    })

    // Start execution for Scenario B
    fireEvent.click(screen.getByTestId('run-real-investigation-btn'))

    await waitFor(() => {
      expect(screen.getAllByText('job_B_roundtrip')[0]).toBeInTheDocument()
    })

    // While result retrieval is pending, operator switches dropdown to Scenario A
    fireEvent.change(screen.getByTestId('scenario-select'), {
      target: { value: 'TRUJILLO_00007_01339' },
    })

    // And then operator switches dropdown BACK to Scenario B before response arrives
    fireEvent.change(screen.getByTestId('scenario-select'), {
      target: { value: 'TRUJILLO_00260_00608' },
    })

    // Now resolve the pending Scenario B result
    resolveResultB(resultB)

    // Wait for resolution and verify B adopts as LIVE_CURRENT because live current context matches the resolved result!
    await waitFor(() => {
      expect(screen.getByTestId('result-freshness-badge')).toHaveTextContent('LIVE CURRENT')
      expect(screen.queryByTestId('quarantine-status-badge')).not.toBeInTheDocument()
      expect(screen.getByTestId('operational-gate-indicator')).toHaveTextContent('APPLICATION GATE: READY')
    })

    unmount()
  })
})

