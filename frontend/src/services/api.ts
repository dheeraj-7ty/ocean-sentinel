/**
 * Ocean Sentinel Typed API Client Service.
 * 
 * Provides typed HTTP calls to the backend orchestration and evidence fusion API.
 * Adheres strictly to backend schemas and fail-closed physical mode gates.
 */

import type {
  ArtifactListResponse,
  CreateInvestigationPayload,
  CreateJobPayload,
  HealthResponse,
  InvestigationEvent,
  InvestigationListResponse,
  InvestigationRun,
  InvestigationScenario,
  InvestigationTelemetry,
  JobResponse,
  JobResultResponse,
  ScenarioListResponse,
} from '../types/api'

const API_BASE = '/api/v1'

export class ApiError extends Error {
  code: string
  stage?: string
  retryable: boolean
  details: Record<string, any>
  status: number

  constructor(status: number, data: any) {
    super(data?.message || `HTTP ${status}`)
    this.name = 'ApiError'
    this.status = status
    this.code = data?.code || 'API_ERROR'
    this.stage = data?.stage
    this.retryable = data?.retryable || false
    this.details = data?.details || {}
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorData: any = {}
    try {
      errorData = await res.json()
    } catch {
      errorData = { message: res.statusText || `Request failed with status ${res.status}` }
    }
    throw new ApiError(res.status, errorData)
  }
  return res.json() as Promise<T>
}

export const oceanSentinelApi = {
  /**
   * Health check endpoint: returns service health, API version, and frozen subsystem status.
   */
  async getHealth(): Promise<HealthResponse> {
    const res = await fetch(`${API_BASE}/health`)
    return handleResponse<HealthResponse>(res)
  },

  /**
   * List recent jobs from local job store.
   */
  async listJobs(limit = 20): Promise<{ total_jobs: number; limit: number; jobs: JobResponse[] }> {
    const res = await fetch(`${API_BASE}/jobs?limit=${limit}`)
    return handleResponse<{ total_jobs: number; limit: number; jobs: JobResponse[] }>(res)
  },

  /**
   * Initialize and execute a pipeline job synchronously.
   */
  async createJob(payload: CreateJobPayload): Promise<JobResponse> {
    const res = await fetch(`${API_BASE}/jobs`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })
    return handleResponse<JobResponse>(res)
  },

  /**
   * Retrieve complete status and manifest of a job by ID.
   */
  async getJob(jobId: string): Promise<JobResponse> {
    const res = await fetch(`${API_BASE}/jobs/${encodeURIComponent(jobId)}`)
    return handleResponse<JobResponse>(res)
  },

  /**
   * Discover all artifacts produced by a job.
   */
  async getJobArtifacts(jobId: string): Promise<ArtifactListResponse> {
    const res = await fetch(`${API_BASE}/jobs/${encodeURIComponent(jobId)}/artifacts`)
    return handleResponse<ArtifactListResponse>(res)
  },

  /**
   * Retrieve normalized Evidence Fusion result for a job.
   */
  async getJobResult(jobId: string): Promise<JobResultResponse> {
    const res = await fetch(`${API_BASE}/jobs/${encodeURIComponent(jobId)}/result`)
    return handleResponse<JobResultResponse>(res)
  },

  /**
   * List registered real repository investigation scenarios.
   */
  async listScenarios(): Promise<ScenarioListResponse> {
    const res = await fetch(`${API_BASE}/investigations/scenarios`)
    return handleResponse<ScenarioListResponse>(res)
  },

  /**
   * Retrieve details for a registered investigation scenario.
   */
  async getScenario(scenarioId: string): Promise<InvestigationScenario> {
    const res = await fetch(`${API_BASE}/investigations/scenarios/${encodeURIComponent(scenarioId)}`)
    return handleResponse<InvestigationScenario>(res)
  },

  /**
   * List stored investigation runs and recent operational acquisitions.
   */
  async listInvestigations(limit = 50): Promise<InvestigationSummary[]> {
    const res = await fetch(`${API_BASE}/investigations?limit=${limit}`)
    const data = await handleResponse<{ total_runs: number; limit: number; runs: any[] }>(res)
    return (data.runs || []).map((r) => ({
      run_id: r.run_id,
      status: r.status,
      created_at_utc: r.created_at || r.created_at_utc,
      execution_authorized: false,
      stages_count: r.stages_count || (r.stages ? Object.keys(r.stages).length : 0),
    }))
  },

  /**
   * Retrieve full canonical InvestigationRun state by ID.
   */
  async getInvestigation(runId: string): Promise<InvestigationRun> {
    const res = await fetch(`${API_BASE}/investigations/${encodeURIComponent(runId)}`)
    return handleResponse<InvestigationRun>(res)
  },

  /**
   * Retrieve structured operational telemetry snapshot for an investigation run.
   */
  async getInvestigationTelemetry(runId: string): Promise<InvestigationTelemetry> {
    const res = await fetch(`${API_BASE}/investigations/${encodeURIComponent(runId)}/telemetry`)
    return handleResponse<InvestigationTelemetry>(res)
  },

  /**
   * Retrieve recorded event log history from durable disk log.
   */
  async getInvestigationEventHistory(
    runId: string,
    afterSequence?: number,
    limit = 100
  ): Promise<{ run_id: string; after_sequence?: number; total_returned: number; events: InvestigationEvent[] }> {
    const params = new URLSearchParams()
    if (afterSequence !== undefined) {
      params.set('after_sequence', String(afterSequence))
    }
    params.set('limit', String(limit))
    const res = await fetch(`${API_BASE}/investigations/${encodeURIComponent(runId)}/events/history?${params.toString()}`)
    return handleResponse<{ run_id: string; after_sequence?: number; total_returned: number; events: InvestigationEvent[] }>(res)
  },

  /**
   * Initialize and start a durable investigation run.
   */
  async createInvestigation(payload: CreateInvestigationPayload): Promise<InvestigationRun> {
    const res = await fetch(`${API_BASE}/investigations`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })
    return handleResponse<InvestigationRun>(res)
  },

  /**
   * Subscribe to real-time Server-Sent Events (SSE) for an investigation run.
   * Handles Last-Event-ID replay, reconnection, gapless delivery, and duplicate suppression.
   */
  subscribeInvestigationEvents(
    runId: string,
    onEvent: (event: InvestigationEvent) => void,
    onError?: (error: any) => void,
    initialLastEventId?: number
  ): () => void {
    let isClosed = false
    let currentLastEventId = initialLastEventId ?? 0
    let eventSource: EventSource | null = null
    const seenEventSequences = new Set<number>()

    const connect = () => {
      if (isClosed) return

      const url = new URL(`${window.location.origin}${API_BASE}/investigations/${encodeURIComponent(runId)}/events`)
      if (currentLastEventId > 0) {
        url.searchParams.set('last_event_id', String(currentLastEventId))
      }

      if (typeof EventSource === 'undefined') {
        if (onStatusChange) onStatusChange('ERROR')
        if (onError) onError(new Error('EventSource is not supported or defined in this environment'))
        return
      }

      eventSource = new EventSource(url.toString())

      const handleEventData = (rawData: string) => {
        try {
          const evt: InvestigationEvent = JSON.parse(rawData)
          if (evt && typeof evt.sequence === 'number') {
            if (seenEventSequences.has(evt.sequence)) {
              // Duplicate suppression: ignore already processed sequence
              return
            }
            seenEventSequences.add(evt.sequence)
            if (evt.sequence > currentLastEventId) {
              currentLastEventId = evt.sequence
            }
            onEvent(evt)
          }
        } catch (err) {
          console.warn('Malformed SSE event payload:', rawData, err)
        }
      }

      eventSource.onmessage = (e) => {
        handleEventData(e.data)
      }

      // Also listen on named canonical event types
      const eventTypes = [
        'RUN_CREATED',
        'RUN_STARTED',
        'RUN_COMPLETED',
        'RUN_FAILED',
        'RUN_SUSPENDED',
        'RUN_RESUMED',
        'STAGE_STARTED',
        'STAGE_PROGRESS',
        'STAGE_COMPLETED',
        'STAGE_FAILED',
        'STAGE_SKIPPED',
        'STAGE_BLOCKED',
        'ARTIFACT_DISCOVERED',
        'ARTIFACT_REGISTERED',
        'PROVENANCE_BLOCKED',
        'TELEMETRY_SNAPSHOT',
      ]
      eventTypes.forEach((type) => {
        eventSource?.addEventListener(type, (e: any) => {
          handleEventData(e.data)
        })
      })

      eventSource.onerror = (err) => {
        if (isClosed) return
        if (onError) onError(err)
      }
    }

    connect()

    return () => {
      isClosed = true
      if (eventSource) {
        eventSource.close()
        eventSource = null
      }
    }
  },
}
