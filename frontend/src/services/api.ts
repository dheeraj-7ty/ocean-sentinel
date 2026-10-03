/**
 * Ocean Sentinel Typed API Client Service.
 * 
 * Provides typed HTTP calls to the backend orchestration and evidence fusion API.
 * Adheres strictly to backend schemas and fail-closed physical mode gates.
 */

import type {
  ArtifactListResponse,
  CreateJobPayload,
  HealthResponse,
  InvestigationScenario,
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
}
