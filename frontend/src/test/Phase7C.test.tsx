import React from 'react'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import App from '../App'
import { oceanSentinelApi } from '../services/api'
import type {
  CreateInvestigationPayload,
  InvestigationEvent,
  InvestigationRun,
  InvestigationSummary,
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

// Deterministic Phase 7C mock investigation fixture derived from canonical Trujillo dataset
const mockInvestigationRun: InvestigationRun = {
  run_id: 'OS-RUN-20240410-TRUJILLO-00007-01339',
  request: {
    aoi_name: 'Trujillo Eastern Mediterranean AOI',
    aoi_bounding_box: [31.5, 30.0, 32.5, 31.0],
    polarization: 'VV+VH',
    max_cloud_cover: 20.0,
  },
  status: 'READY_FOR_DETECTION',
  created_at_utc: '2024-04-10T14:00:00Z',
  completed_at_utc: '2024-04-10T14:02:15Z',
  execution_authorized: false,
  stages: {
    INGEST: {
      status: 'COMPLETED',
      completed_at_utc: '2024-04-10T14:00:30Z',
    },
    DISCOVER: {
      status: 'COMPLETED',
      completed_at_utc: '2024-04-10T14:01:00Z',
    },
    ACQUIRE: {
      status: 'COMPLETED',
      completed_at_utc: '2024-04-10T14:01:30Z',
    },
    PERSIST: {
      status: 'COMPLETED',
      completed_at_utc: '2024-04-10T14:02:00Z',
    },
    VALIDATE: {
      status: 'COMPLETED',
      completed_at_utc: '2024-04-10T14:02:15Z',
    },
    INFER: {
      status: 'BLOCKED',
      message: 'Scientific execution gated (EXECUTION_AUTHORIZED = False)',
      completed_at_utc: '2024-04-10T14:02:15Z',
    },
    INTERPRET: {
      status: 'BLOCKED',
      message: 'Scientific execution gated (EXECUTION_AUTHORIZED = False)',
      completed_at_utc: '2024-04-10T14:02:15Z',
    },
  },
  observation_metadata: {
    product_id: 'S1A_IW_GRDH_1SDV_20240410T140000_TRUJILLO_01339',
    scene_id: '01339',
    acquisition_timestamp_utc: '2024-04-10T14:00:00Z',
    crs: 'EPSG:4326',
    raster_dimensions: [1024, 1024],
    polarization: ['VV', 'VH'],
    format: 'GeoTIFF (Cloud-Optimized)',
    sha256: 'a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef0',
    persistence_path: 'data/sentinel1/trujillo_01339.tif',
  },
  observation_footprint: {
    type: 'Polygon',
    coordinates: [
      [
        [31.5, 30.0],
        [32.5, 30.0],
        [32.5, 31.0],
        [31.5, 31.0],
        [31.5, 30.0],
      ],
    ],
  },
}

const mockInvestigationSummary: InvestigationSummary = {
  run_id: 'OS-RUN-20240410-TRUJILLO-00007-01339',
  status: 'READY_FOR_DETECTION',
  created_at_utc: '2024-04-10T14:00:00Z',
  execution_authorized: false,
  stages_count: 7,
}

const mockEvents: InvestigationEvent[] = [
  {
    sequence: 1,
    event_type: 'RUN_CREATED',
    timestamp_utc: '2024-04-10T14:00:00Z',
    run_id: 'OS-RUN-20240410-TRUJILLO-00007-01339',
    payload: { aoi_name: 'Trujillo Eastern Mediterranean AOI' },
  },
  {
    sequence: 2,
    event_type: 'RUN_STARTED',
    timestamp_utc: '2024-04-10T14:00:05Z',
    run_id: 'OS-RUN-20240410-TRUJILLO-00007-01339',
  },
  {
    sequence: 3,
    event_type: 'STAGE_STARTED',
    stage_name: 'VALIDATE',
    timestamp_utc: '2024-04-10T14:02:00Z',
    run_id: 'OS-RUN-20240410-TRUJILLO-00007-01339',
  },
  {
    sequence: 4,
    event_type: 'STAGE_COMPLETED',
    stage_name: 'VALIDATE',
    timestamp_utc: '2024-04-10T14:02:15Z',
    run_id: 'OS-RUN-20240410-TRUJILLO-00007-01339',
  },
  {
    sequence: 5,
    event_type: 'STAGE_BLOCKED',
    stage_name: 'INFER',
    timestamp_utc: '2024-04-10T14:02:15Z',
    run_id: 'OS-RUN-20240410-TRUJILLO-00007-01339',
    payload: { reason: 'Scientific execution gated (EXECUTION_AUTHORIZED = False)' },
  },
  {
    sequence: 6,
    event_type: 'RUN_COMPLETED',
    timestamp_utc: '2024-04-10T14:02:15Z',
    run_id: 'OS-RUN-20240410-TRUJILLO-00007-01339',
  },
]

describe('Ocean Sentinel Phase 7C Operational Interface Suite', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(oceanSentinelApi, 'getHealth').mockResolvedValue({
      status: 'healthy',
      version: '1.0.0',
      timestamp: '2026-10-05T00:00:00Z',
      subsystems: { backend: 'healthy' } as any,
    })
    vi.spyOn(oceanSentinelApi, 'listJobs').mockResolvedValue({
      total_jobs: 0,
      limit: 10,
      jobs: [],
    })
    vi.spyOn(oceanSentinelApi, 'listScenarios').mockResolvedValue({
      total_scenarios: 0,
      scenarios: [],
    })
    vi.spyOn(oceanSentinelApi, 'listInvestigations').mockResolvedValue([mockInvestigationSummary])
    vi.spyOn(oceanSentinelApi, 'getInvestigation').mockResolvedValue(mockInvestigationRun)
    vi.spyOn(oceanSentinelApi, 'getInvestigationEventHistory').mockResolvedValue(mockEvents)
    vi.spyOn(oceanSentinelApi, 'subscribeInvestigationEvents').mockReturnValue(() => {})
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  // 1. Real investigation payload rendering
  it('1. Renders canonical investigation run identity, lifecycle status, and created date', async () => {
    render(<App />)

    await waitFor(() => {
      expect(screen.getByTestId('phase7-investigation-console')).toBeInTheDocument()
      expect(screen.getByTestId('investigation-lifecycle-card')).toBeInTheDocument()
      expect(screen.getByText(/OS-RUN-20240410-TRUJILLO/)).toBeInTheDocument()
      expect(screen.getByTestId('investigation-status-badge')).toHaveTextContent('READY_FOR_DETECTION')
    })
  })

  // 2. AOI geometry rendering and distinction as USER_INPUT
  it('2. Renders operator AOI parameters and distinctly labels them USER_INPUT (never scientific evidence)', async () => {
    render(<App />)

    await waitFor(() => {
      const aoiCard = screen.getByTestId('aoi-geometry-card')
      expect(aoiCard).toBeInTheDocument()
      expect(screen.getByTestId('aoi-evidence-class-badge')).toHaveTextContent('USER_INPUT')
      expect(aoiCard).toHaveTextContent('Trujillo Eastern Mediterranean AOI')
      expect(aoiCard).toHaveTextContent('NON-EVIDENCE INVARIANT')
    })
  })

  // 3. Observation footprint rendering and distinction as REAL_REPOSITORY_EVIDENCE
  it('3. Renders Sentinel-1 observation metadata and footprint classified as REAL_REPOSITORY_EVIDENCE', async () => {
    render(<App />)

    await waitFor(() => {
      const evidenceCard = screen.getByTestId('s1-evidence-metadata-card')
      expect(evidenceCard).toBeInTheDocument()
      expect(screen.getByTestId('evidence-class-badge')).toHaveTextContent('REAL_REPOSITORY_EVIDENCE')
      expect(evidenceCard).toHaveTextContent('S1A_IW_GRDH_1SDV_20240410T140000_TRUJILLO_01339')
      expect(evidenceCard).toHaveTextContent('EPSG:4326')
      expect(evidenceCard).toHaveTextContent('1024 × 1024 px')
    })
  })

  // 4. Lifecycle state rendering faithful to exact DAG status
  it('4. Renders DAG execution status without fabricated completion percentages', async () => {
    render(<App />)

    await waitFor(() => {
      expect(screen.getByText('DAG:VALIDATE')).toBeInTheDocument()
      expect(screen.getByText('DAG:INFER')).toBeInTheDocument()
      expect(screen.getByText('DAG:INTERPRET')).toBeInTheDocument()
      // Blocked stages show BLOCKED (GATED)
      const blockedElements = screen.getAllByText('BLOCKED (GATED)')
      expect(blockedElements.length).toBeGreaterThanOrEqual(2)
    })
  })

  // 5. SSE event ingestion into investigation event spine
  it('5. Ingests and renders investigation event stream chronologically', async () => {
    render(<App />)

    await waitFor(() => {
      expect(screen.getByTestId('investigation-event-track')).toBeInTheDocument()
      expect(screen.getByTestId('event-node-1')).toHaveTextContent('RUN_CREATED')
      expect(screen.getByTestId('event-node-5')).toHaveTextContent('STAGE_BLOCKED')
      expect(screen.getByTestId('event-node-6')).toHaveTextContent('RUN_COMPLETED')
    })
  })

  // 6. SSE reconnect indicator & status transition
  it('6. Displays SSE connection telemetry status honestly', async () => {
    let capturedOnStatusChange: ((status: any) => void) | null = null
    vi.spyOn(oceanSentinelApi, 'subscribeInvestigationEvents').mockImplementation(
      (_runId, _onEvent, _onError, onStatusChange) => {
        capturedOnStatusChange = onStatusChange || null
        if (onStatusChange) onStatusChange('STREAMING')
        return () => {}
      }
    )

    render(<App />)

    await waitFor(() => {
      expect(screen.getByTestId('sse-status-indicator')).toHaveTextContent('SSE: LIVE STREAM')
    })

    // Simulate network drop / reconnecting
    if (capturedOnStatusChange) {
      ;(capturedOnStatusChange as any)('RECONNECTING')
    }

    await waitFor(() => {
      expect(screen.getByTestId('sse-status-indicator')).toHaveTextContent('SSE: RECONNECTING')
    })
  })

  // 7. Duplicate event suppression
  it('7. Suppresses duplicate sequence events emitted during replay or reconnection', async () => {
    let capturedOnEvent: ((event: InvestigationEvent) => void) | null = null
    vi.spyOn(oceanSentinelApi, 'subscribeInvestigationEvents').mockImplementation(
      (_runId, onEvent) => {
        capturedOnEvent = onEvent
        return () => {}
      }
    )

    render(<App />)

    await waitFor(() => {
      expect(screen.getByTestId('event-node-1')).toBeInTheDocument()
    })

    // Emit identical sequence 1 event twice
    if (capturedOnEvent) {
      ;(capturedOnEvent as any)({
        sequence: 1,
        event_type: 'RUN_CREATED',
        timestamp_utc: '2024-04-10T14:00:00Z',
        run_id: 'OS-RUN-20240410-TRUJILLO-00007-01339',
      })
      ;(capturedOnEvent as any)({
        sequence: 1,
        event_type: 'RUN_CREATED',
        timestamp_utc: '2024-04-10T14:00:00Z',
        run_id: 'OS-RUN-20240410-TRUJILLO-00007-01339',
      })
    }

    // Only one node with sequence 1 should exist
    const node1List = screen.getAllByTestId('event-node-1')
    expect(node1List).toHaveLength(1)
  })

  // 8. Blocked scientific-stage rendering (EXECUTION_AUTHORIZED = False)
  it('8. Visibly displays fail-closed scientific execution gate banner and blocks INFER/INTERPRET', async () => {
    render(<App />)

    await waitFor(() => {
      const banner = screen.getByTestId('scientific-gate-banner')
      expect(banner).toBeInTheDocument()
      expect(banner).toHaveTextContent('BLOCKED: Scientific execution gated')
      expect(banner).toHaveTextContent('EXECUTION_AUTHORIZED = False')
      expect(banner).toHaveTextContent('Stages [INFER] and [INTERPRET] remain strictly blocked')
    })
  })

  // 9. Missing evidence handling without crash
  it('9. Gracefully handles missing observation metadata without crashing', async () => {
    const minimalRun: InvestigationRun = {
      run_id: 'OS-RUN-MINIMAL-001',
      request: { aoi_name: 'Minimal Test AOI' },
      status: 'RUNNING',
      created_at_utc: '2024-04-10T14:00:00Z',
      execution_authorized: false,
      stages: {},
    }
    vi.spyOn(oceanSentinelApi, 'getInvestigation').mockResolvedValue(minimalRun)
    vi.spyOn(oceanSentinelApi, 'getInvestigationEventHistory').mockResolvedValue([])

    render(<App />)

    await waitFor(() => {
      expect(screen.getByTestId('investigation-lifecycle-card')).toBeInTheDocument()
      expect(screen.getByText(/OS-RUN-MINIMAL-001/)).toBeInTheDocument()
      // Observation evidence card is omitted gracefully when metadata is missing
      expect(screen.queryByTestId('s1-evidence-metadata-card')).not.toBeInTheDocument()
    })
  })

  // 10. API error handling renders notice without crashing UI
  it('10. Renders operational error banner when investigation fetch fails', async () => {
    vi.spyOn(oceanSentinelApi, 'listInvestigations').mockResolvedValue([mockInvestigationSummary])
    vi.spyOn(oceanSentinelApi, 'getInvestigation').mockRejectedValue(new Error('Network gateway timeout'))

    render(<App />)

    await waitFor(() => {
      expect(screen.getByText(/Network gateway timeout/)).toBeInTheDocument()
    })
  })

  // 11. Clear distinction: USER_INPUT vs REAL_REPOSITORY_EVIDENCE
  it('11. Prohibits presenting user input parameters as detected phenomena', async () => {
    render(<App />)

    await waitFor(() => {
      const aoiBadge = screen.getByTestId('aoi-evidence-class-badge')
      expect(aoiBadge).toHaveTextContent('USER_INPUT')

      const s1Badge = screen.getByTestId('evidence-class-badge')
      expect(s1Badge).toHaveTextContent('REAL_REPOSITORY_EVIDENCE')

      // Ensure no UI copy claims detection
      expect(screen.queryByText(/Oil spill detected/i)).not.toBeInTheDocument()
      expect(screen.queryByText(/Confirmed slick/i)).not.toBeInTheDocument()
    })
  })

  // 12. Host-path and credentials privacy safety
  it('12. Enforces repository-relative persistence paths and never exposes local host paths', async () => {
    const runWithLocalPath: InvestigationRun = {
      ...mockInvestigationRun,
      observation_metadata: {
        ...mockInvestigationRun.observation_metadata!,
        persistence_path: 'C:\\Users\\Operator\\AppData\\ocean_sentinel\\data\\sentinel1\\scene.tif',
      },
    }
    vi.spyOn(oceanSentinelApi, 'getInvestigation').mockResolvedValue(runWithLocalPath)

    render(<App />)

    await waitFor(() => {
      const evidenceCard = screen.getByTestId('s1-evidence-metadata-card')
      expect(evidenceCard).toBeInTheDocument()
      // Must NOT contain C:\ or local host user path
      expect(evidenceCard.textContent).not.toContain('C:\\Users')
      expect(evidenceCard.textContent).toContain('ocean_sentinel/data/sentinel1/scene.tif')
    })
  })

  // 13. Cleanup and unsubscribe behavior on unmount
  it('13. Cleanly unsubscribes from SSE event stream when changing investigations or unmounting', async () => {
    const unsubscribeSpy = vi.fn()
    vi.spyOn(oceanSentinelApi, 'subscribeInvestigationEvents').mockReturnValue(unsubscribeSpy)

    const { unmount } = render(<App />)

    await waitFor(() => {
      expect(oceanSentinelApi.subscribeInvestigationEvents).toHaveBeenCalled()
    })

    unmount()
    expect(unsubscribeSpy).toHaveBeenCalled()
  })
})
