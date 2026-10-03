import React, { useState, useEffect, useCallback, useRef } from 'react'
import { TopBar } from './components/TopBar'
import { LeftControlPanel } from './components/LeftControlPanel'
import { GlobeView } from './components/GlobeView'
import { RightInspector } from './components/RightInspector'
import { BottomTimeline } from './components/BottomTimeline'
import { Legend } from './components/Legend'
import { oceanSentinelApi, ApiError } from './services/api'
import type {
  ApplicationGate,
  ConnectionStatus,
  HealthResponse,
  InvestigationScenario,
  JobMode,
  JobResponse,
  JobResultResponse,
  LayerVisibility,
  PipelineType,
  ResultFreshness,
  ResultUsage,
  ScientificValidity,
  SelectedLocation,
  SelectionType,
} from './types/api'
import { AlertOctagon, X } from 'lucide-react'

export const App: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('OFFLINE')
  const [resultFreshness, setResultFreshness] = useState<ResultFreshness>('NONE')
  const [activeMode, setActiveMode] = useState<JobMode>('DEMO')
  const [currentJob, setCurrentJob] = useState<JobResponse | null>(null)
  const [jobList, setJobList] = useState<JobResponse[]>([])
  const [jobResult, setJobResult] = useState<JobResultResponse | null>(null)
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | null>(null)
  const [selectedLocation, setSelectedLocation] = useState<SelectedLocation | null>(null)
  const [selectionType, setSelectionType] = useState<SelectionType>('NONE')
  const [currentPhaseIndex, setCurrentPhaseIndex] = useState<number>(3) // Default to T1 SAR detection
  const [isExecuting, setIsExecuting] = useState<boolean>(false)
  const [activeError, setActiveError] = useState<{
    code: string
    message: string
    stage?: string
  } | null>(null)

  // Registered Real Repository Scenarios
  const [scenarios, setScenarios] = useState<InvestigationScenario[]>([
    {
      scenario_id: 'TRUJILLO_00007_01339',
      label: 'Trujillo 2024 S1 Scene Pair 00007 / 01339 (Eastern Mediterranean)',
      dataset: 'Trujillo et al., 2024 Sentinel-1 SAR Oil Spill Dataset',
      scene_pair: ['00007', '01339'],
      region: 'Eastern Mediterranean (Offshore Nile Delta)',
      centroid: [30.652577, 32.137832],
      event_id: '00007_01339_persistent_0003',
      artifacts: {
        detection_mask_t0: 'outputs/inference/00007_mask.tif',
        detection_mask_t1: 'outputs/inference/01339_mask.tif',
        temporal_geojson: 'outputs/temporal/00007_to_01339_temporal_events.geojson',
        drift_geojson: 'outputs/origin_drift/trujillo_00007_01339.geojson',
        ais_summary: 'outputs/ais/trujillo_00007_01339_summary.json',
        ais_geojson: 'outputs/ais/trujillo_00007_01339.geojson',
      },
      acquisition_timestamps: {
        t0: '2024-04-05T14:00:00+00:00 (EXTERNALLY_SUPPLIED_TEST_TIMESTAMP)',
        t1: '2024-04-10T14:00:00+00:00 (EXTERNALLY_SUPPLIED_TEST_TIMESTAMP)',
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
        'Data originates from Trujillo et al. (2024) repository baseline; physical external feeds remain unavailable.',
        'Scenario contains downstream drift and AIS artifacts generated with synthetic forcing and DEMO feeds (SYNTHETIC_DEMO); they are NOT historical metocean observations or physical vessel tracks.',
        'Overall scenario provenance is classified as REAL_REPOSITORY_SCENARIO_WITH_SYNTHETIC_DEPENDENCY and cannot claim pure HISTORICAL_ARCHIVE.',
        'Candidate vessels reflect spatio-temporal compatibility hypotheses only; NO legal responsibility or causal guilt is established.',
        'Absence of AIS signals does NOT prove vessel absence (AIS_ABSENCE_IS_NOT_VESSEL_ABSENCE).',
      ],
    },
    {
      scenario_id: 'TRUJILLO_00260_00608',
      label: 'Trujillo 2024 S1 Scene Pair 00260 / 00608 (Gulf of Mexico)',
      dataset: 'Trujillo et al., 2024 Sentinel-1 SAR Oil Spill Dataset',
      scene_pair: ['00260', '00608'],
      region: 'Gulf of Mexico (Deepwater offshore)',
      centroid: [-90.386402, 27.0864],
      event_id: '00260_00608_new_0010',
      artifacts: {
        detection_mask_t0: 'outputs/inference/00260_mask.tif',
        detection_mask_t1: 'outputs/inference/00608_mask.tif',
        temporal_geojson: 'outputs/temporal/00260_to_00608_temporal_events.geojson',
        drift_geojson: 'outputs/drift/00260_00608_new_0010_backward_drift.geojson',
        ais_summary: 'outputs/ais/00260_00608_new_0010_ais_correlation_summary.json',
        ais_geojson: 'outputs/ais/00260_00608_new_0010_ais_correlation.geojson',
      },
      acquisition_timestamps: {
        t0: '2024-05-01T00:00:00+00:00 (EXTERNALLY_SUPPLIED_TEST_TIMESTAMP)',
        t1: '2024-05-13T00:00:00+00:00 (EXTERNALLY_SUPPLIED_TEST_TIMESTAMP)',
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
        'Data originates from Trujillo et al. (2024) repository baseline; physical external feeds remain unavailable.',
        'Scenario contains downstream drift and AIS artifacts generated with synthetic forcing and DEMO feeds (SYNTHETIC_DEMO); they are NOT historical metocean observations or physical vessel tracks.',
        'Overall scenario provenance is classified as REAL_REPOSITORY_SCENARIO_WITH_SYNTHETIC_DEPENDENCY and cannot claim pure HISTORICAL_ARCHIVE.',
        'Candidate vessels reflect spatio-temporal compatibility hypotheses only; NO legal responsibility or causal guilt is established.',
        'Absence of AIS signals does NOT prove vessel absence (AIS_ABSENCE_IS_NOT_VESSEL_ABSENCE).',
      ],
    },
  ])
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>('TRUJILLO_00007_01339')

  // Layer visibility state
  const [layers, setLayers] = useState<LayerVisibility>({
    sar_detection: true,
    temporal_change: true,
    drift_trajectory: true,
    drift_origin: true,
    ais_tracks: true,
    fused_evidence: true,
    hypotheses: true,
  })

  // Ref to track if unmounted and execution generation token for async race protection
  const isMountedRef = useRef<boolean>(true)
  const executionTokenRef = useRef<number>(0)
  const activeModeRef = useRef<JobMode>(activeMode)
  activeModeRef.current = activeMode
  const selectedScenarioIdRef = useRef<string>(selectedScenarioId)
  selectedScenarioIdRef.current = selectedScenarioId
  useEffect(() => {
    isMountedRef.current = true
    return () => {
      isMountedRef.current = false
    }
  }, [])

  // Explicit health & connectivity check
  const checkHealth = useCallback(async () => {
    try {
      const h = await oceanSentinelApi.getHealth()
      if (!isMountedRef.current) return
      setHealth(h)
      setConnectionStatus('ONLINE')
      // Reconnecting does NOT alter resultFreshness (cached remains cached until fresh execution)
    } catch (err: any) {
      if (!isMountedRef.current) return
      if (err instanceof ApiError) {
        setConnectionStatus('OFFLINE')
      } else {
        // Network refusal or connection timeout
        setConnectionStatus('UNREACHABLE')
      }
      // When connection drops, any displayed live result transitions to cached
      setResultFreshness((prev) => (prev === 'LIVE_CURRENT' ? 'CACHED_LAST_LOADED' : prev))
    }
  }, [])

  // Load a job result given its ID
  const loadJobResult = useCallback(async (jobId: string, token?: number) => {
    try {
      const result = await oceanSentinelApi.getJobResult(jobId)
      if (!isMountedRef.current) return
      if (token !== undefined && token !== executionTokenRef.current) return
      setJobResult(result)
      setConnectionStatus('ONLINE')
    } catch (err: any) {
      if (!isMountedRef.current) return
      if (token !== undefined && token !== executionTokenRef.current) return
      console.warn('Job result not available or blocked:', err)
      setJobResult(null)
    }
  }, [])

  // Initial mount: load health, recent jobs, and start heartbeat
  useEffect(() => {
    const initApp = async () => {
      const initToken = ++executionTokenRef.current
      let isHealthy = false
      try {
        const h = await oceanSentinelApi.getHealth()
        if (!isMountedRef.current || initToken !== executionTokenRef.current) return
        setHealth(h)
        setConnectionStatus('ONLINE')
        isHealthy = true
      } catch (err: any) {
        if (!isMountedRef.current || initToken !== executionTokenRef.current) return
        if (err instanceof ApiError) {
          setConnectionStatus('OFFLINE')
        } else {
          setConnectionStatus('UNREACHABLE')
        }
      }

      try {
        const jobsData = await oceanSentinelApi.listJobs(10)
        if (!isMountedRef.current || initToken !== executionTokenRef.current) return
        setJobList(jobsData.jobs || [])
        if (isHealthy) {
          setConnectionStatus('ONLINE')
        }

        if (jobsData.jobs && jobsData.jobs.length > 0) {
          const latest = jobsData.jobs[0]
          setCurrentJob(latest)
          setActiveMode(latest.mode)
          setResultFreshness('CACHED_LAST_LOADED')
          if (latest.status === 'SUCCEEDED' && isHealthy) {
            await loadJobResult(latest.job_id, initToken)
          }
        }
      } catch (err: any) {
        if (!isMountedRef.current || initToken !== executionTokenRef.current) return
        console.warn('Failed to list jobs on mount:', err)
        if (err instanceof ApiError) {
          setConnectionStatus('OFFLINE')
        } else {
          setConnectionStatus('UNREACHABLE')
        }
      }

      // Fetch registered real repository scenarios
      try {
        const scData = await oceanSentinelApi.listScenarios()
        if (scData.scenarios && scData.scenarios.length > 0 && isMountedRef.current && initToken === executionTokenRef.current) {
          setScenarios(scData.scenarios)
        }
      } catch (err) {
        console.warn('Failed to load registered scenarios on mount:', err)
      }
    }

    initApp()

    // 4-second connectivity heartbeat poll
    const interval = setInterval(() => {
      checkHealth()
    }, 4000)

    return () => clearInterval(interval)
  }, [checkHealth, loadJobResult])

  // Handle location selection from globe click
  const handleSelectLocation = useCallback((loc: SelectedLocation | null) => {
    setSelectedLocation(loc)
    if (loc) {
      setSelectionType('USER_LOCATION')
    } else {
      setSelectionType((prev) => (prev === 'USER_LOCATION' ? 'NONE' : prev))
    }
  }, [])

  // Handle evidence / candidate hypothesis selection
  const handleSelectEvidence = useCallback(
    (id: string | null) => {
      setSelectedEvidenceId(id)
      if (!id) {
        setSelectionType((prev) => (prev !== 'USER_LOCATION' ? 'NONE' : prev))
        return
      }

      if (jobResult?.candidate_vessel_hypotheses?.some((v) => v.hypothesis_id === id)) {
        setSelectionType('CANDIDATE_VESSEL')
      } else if (jobResult?.candidate_spill_hypotheses?.some((s) => s.hypothesis_id === id)) {
        setSelectionType('CANDIDATE_SPILL_ORIGIN')
      } else {
        setSelectionType('EVIDENCE_ITEM')
      }
    },
    [jobResult]
  )

  // Pipeline Execution Dispatch
  const handleRunPipeline = async (mode: JobMode, pipelineType: PipelineType) => {
    const token = ++executionTokenRef.current
    setIsExecuting(true)
    setActiveError(null)
    setActiveMode(mode)
    // Stale result race protection: demote any prior live result during new execution
    setResultFreshness((prev) => (prev === 'LIVE_CURRENT' ? 'CACHED_LAST_LOADED' : prev))

    try {
      const newJob = await oceanSentinelApi.createJob({
        mode,
        pipeline_type: pipelineType,
      })
      if (token !== executionTokenRef.current || !isMountedRef.current) return

      setCurrentJob(newJob)
      setConnectionStatus('ONLINE')
      setJobList((prev) => [newJob, ...prev.filter((j) => j.job_id !== newJob.job_id)])
      setIsExecuting(false)

      if (newJob.status === 'SUCCEEDED') {
        try {
          const res = await oceanSentinelApi.getJobResult(newJob.job_id)
          if (token !== executionTokenRef.current || !isMountedRef.current) return

          const isJobMatch = Boolean(res && res.job_id === newJob.job_id)
          const isModeMatch = Boolean(res && res.mode === activeModeRef.current)

          if (isJobMatch && isModeMatch) {
            setJobResult(res)
            setResultFreshness('LIVE_CURRENT')
          } else if (isJobMatch) {
            // Mode mismatch after retrieval: keep result but mark cached/quarantined
            setJobResult(res)
            setResultFreshness('CACHED_LAST_LOADED')
          } else {
            // Wrong job identity or empty result
            setJobResult(null)
            setResultFreshness('NONE')
          }
        } catch {
          if (token !== executionTokenRef.current || !isMountedRef.current) return
          setJobResult(null)
          setResultFreshness('NONE')
        }
      } else if (newJob.status === 'BLOCKED_PROVENANCE') {
        setJobResult(null)
        setResultFreshness('NONE')
        setActiveError({
          code: newJob.error?.code || 'BLOCKED_PROVENANCE',
          message:
            newJob.error?.message ||
            'PHYSICAL pipeline blocked by operational provenance gate. Awaiting external feeds.',
          stage: newJob.error?.stage || 'VALIDATE',
        })
      } else if (newJob.status === 'FAILED') {
        setJobResult(null)
        setResultFreshness('NONE')
        setActiveError({
          code: newJob.error?.code || 'PIPELINE_ERROR',
          message: newJob.error?.message || 'Pipeline execution failed.',
          stage: newJob.error?.stage || 'UNKNOWN',
        })
      }
    } catch (err: any) {
      if (token !== executionTokenRef.current || !isMountedRef.current) return
      setJobResult(null)
      setResultFreshness('NONE')
      if (err instanceof ApiError) {
        setActiveError({
          code: err.code,
          message: err.message,
          stage: err.stage,
        })
        if (err.code === 'PROVENANCE_REJECTION') {
          // Update current job display to reflect blocked physical provenance
          setCurrentJob((prev) =>
            prev
              ? { ...prev, status: 'BLOCKED_PROVENANCE' }
              : ({
                  job_id: 'job_physical_blocked',
                  mode: 'PHYSICAL',
                  pipeline_type: 'PHYSICAL',
                  status: 'BLOCKED_PROVENANCE',
                  created_at: new Date().toISOString(),
                  requested_config: {},
                  stage_status: {},
                  artifacts: [],
                  limitations: [
                    'Physical operational sources unavailable. Pipeline failed closed.',
                  ],
                  links: { self: '', artifacts: '', result: '' },
                } as JobResponse)
          )
        }
      } else {
        setConnectionStatus('UNREACHABLE')
        setActiveError({
          code: 'CONNECTION_ERROR',
          message: err.message || 'Pipeline execution failed.',
        })
      }
    } finally {
      if (token === executionTokenRef.current && isMountedRef.current) {
        setIsExecuting(false)
      }
    }
  }

  // Real Repository Investigation Dispatch
  const handleRunRealInvestigation = async (scenarioId: string) => {
    const token = ++executionTokenRef.current
    setIsExecuting(true)
    setActiveError(null)
    setActiveMode('REAL_REPOSITORY')
    setSelectedScenarioId(scenarioId)
    // Stale result race protection: demote any prior live result during new execution
    setResultFreshness((prev) => (prev === 'LIVE_CURRENT' ? 'CACHED_LAST_LOADED' : prev))

    try {
      const newJob = await oceanSentinelApi.createJob({
        mode: 'REAL_REPOSITORY',
        pipeline_type: 'REAL_REPOSITORY',
        scenario_id: scenarioId,
      })
      if (token !== executionTokenRef.current || !isMountedRef.current) return

      setCurrentJob(newJob)
      setConnectionStatus('ONLINE')
      setJobList((prev) => [newJob, ...prev.filter((j) => j.job_id !== newJob.job_id)])
      setIsExecuting(false)

      if (newJob.status === 'SUCCEEDED') {
        try {
          const res = await oceanSentinelApi.getJobResult(newJob.job_id)
          if (token !== executionTokenRef.current || !isMountedRef.current) return

          const isJobMatch = Boolean(res && res.job_id === newJob.job_id)
          const isModeMatch = Boolean(res && res.mode === activeModeRef.current)
          const isScenarioMatch = Boolean(res && res.scenario_id === selectedScenarioIdRef.current)

          if (isJobMatch && isModeMatch && isScenarioMatch) {
            setJobResult(res)
            setResultFreshness('LIVE_CURRENT')
          } else if (isJobMatch) {
            // Scenario or mode mismatch after retrieval: keep result but mark cached/quarantined
            setJobResult(res)
            setResultFreshness('CACHED_LAST_LOADED')
          } else {
            // Wrong job identity or empty result
            setJobResult(null)
            setResultFreshness('NONE')
          }
        } catch {
          if (token !== executionTokenRef.current || !isMountedRef.current) return
          setJobResult(null)
          setResultFreshness('NONE')
        }
      } else if (newJob.status === 'BLOCKED_PROVENANCE') {
        setJobResult(null)
        setResultFreshness('NONE')
        setActiveError({
          code: newJob.error?.code || 'BLOCKED_PROVENANCE',
          message:
            newJob.error?.message ||
            'Scenario execution blocked by provenance gate: duplicate raster pair.',
          stage: newJob.error?.stage || 'INGEST',
        })
      } else if (newJob.status === 'FAILED') {
        setJobResult(null)
        setResultFreshness('NONE')
        setActiveError({
          code: newJob.error?.code || 'PIPELINE_ERROR',
          message: newJob.error?.message || 'Real repository investigation failed.',
          stage: newJob.error?.stage || 'UNKNOWN',
        })
      }
    } catch (err: any) {
      if (token !== executionTokenRef.current || !isMountedRef.current) return
      setJobResult(null)
      setResultFreshness('NONE')
      if (err instanceof ApiError) {
        setActiveError({
          code: err.code,
          message: err.message,
          stage: err.stage,
        })
      } else {
        setConnectionStatus('UNREACHABLE')
        setActiveError({
          code: 'CONNECTION_ERROR',
          message: err.message || 'Real investigation execution failed.',
        })
      }
    } finally {
      if (token === executionTokenRef.current && isMountedRef.current) {
        setIsExecuting(false)
      }
    }
  }

  // Handle layer toggle
  const handleToggleLayer = (layerKey: keyof LayerVisibility) => {
    setLayers((prev) => ({
      ...prev,
      [layerKey]: !prev[layerKey],
    }))
  }

  // Handle switching to a past job
  const handleSelectJob = async (jobId: string) => {
    const token = ++executionTokenRef.current
    try {
      const job = await oceanSentinelApi.getJob(jobId)
      if (token !== executionTokenRef.current || !isMountedRef.current) return

      setCurrentJob(job)
      setActiveMode(job.mode)
      setActiveError(null)
      setConnectionStatus('ONLINE')
      if (job.status === 'SUCCEEDED') {
        await loadJobResult(job.job_id, token)
        if (token !== executionTokenRef.current || !isMountedRef.current) return
        // Loaded past job: marked CACHED_LAST_LOADED
        setResultFreshness('CACHED_LAST_LOADED')
      } else {
        setJobResult(null)
        setResultFreshness('NONE')
        if (job.status === 'BLOCKED_PROVENANCE') {
          setActiveError({
            code: 'BLOCKED_PROVENANCE',
            message: job.error?.message || 'Job blocked by physical provenance gate.',
            stage: 'VALIDATE',
          })
        }
      }
    } catch (err: any) {
      if (token !== executionTokenRef.current || !isMountedRef.current) return
      if (err instanceof ApiError) {
        setConnectionStatus('OFFLINE')
      } else {
        setConnectionStatus('UNREACHABLE')
      }
      setActiveError({
        code: 'JOB_FETCH_ERROR',
        message: err.message || `Failed to fetch job ${jobId}`,
      })
    }
  }

  // Context Mismatch & Evidence Quarantine Computation
  const evidenceScenarioId = jobResult?.scenario_id || currentJob?.scenario_id
  const evidenceMode = jobResult?.mode || currentJob?.mode

  const isScenarioMismatch = Boolean(
    evidenceScenarioId &&
    selectedScenarioId &&
    selectedScenarioId !== evidenceScenarioId
  )
  const isModeMismatch = Boolean(
    evidenceMode &&
    activeMode &&
    activeMode !== evidenceMode
  )
  const isQuarantined = Boolean((jobResult || currentJob) && (isScenarioMismatch || isModeMismatch))

  // Level 2 Stage Gating: Temporal stage block check
  const isTemporalBlocked = Boolean(
    currentJob?.stage_status?.['TEMPORAL']?.status === 'BLOCKED' ||
    jobResult?.stage_provenance?.temporal === 'BLOCKED' ||
    jobResult?.scenario_metadata?.temporal_status?.startsWith('BLOCKED') ||
    jobResult?.scenario_metadata?.temporal_status === 'PENDING_AUTHORITATIVE_TIMESTAMP' ||
    jobResult?.scenario_metadata?.stage_provenance?.temporal === 'BLOCKED' ||
    jobResult?.scenario_metadata?.reason === 'TEMPORAL_ORDER_UNKNOWN'
  )

  // Contextual Overlay: Result Usage (ACTIVE | QUARANTINED | NONE)
  const resultUsage: ResultUsage = React.useMemo(() => {
    if (!jobResult && !currentJob) return 'NONE'
    if (currentJob?.status === 'BLOCKED_PROVENANCE' || currentJob?.status === 'FAILED') return 'NONE'
    if (isQuarantined) return 'QUARANTINED'
    return 'ACTIVE'
  }, [jobResult, currentJob?.status, isQuarantined])

  // Evidence-Scoped Scientific Validity Derivation
  const scientificValidity: ScientificValidity | undefined = React.useMemo(() => {
    // 1. Entire job stopped at provenance/validation gate with no result:
    if (currentJob?.status === 'BLOCKED_PROVENANCE') return 'BLOCKED'
    if (currentJob?.status === 'FAILED') return 'BLOCKED'

    // 2. If result exists, inspect its provenance and lineage:
    if (jobResult) {
      if (jobResult.lineage_status === 'LEGACY_INVALID_TEMPORAL_PAIR') {
        return 'LEGACY_INVALID'
      }
      if (
        jobResult.provenance_status === 'PROVENANCE_LIMITED' ||
        jobResult.has_synthetic_dependencies ||
        isTemporalBlocked
      ) {
        return 'PROVENANCE_LIMITED'
      }
      return 'VALID_FOR_SCOPE'
    }

    return undefined
  }, [currentJob, jobResult, isTemporalBlocked])

  // Dimension 6: Application Gate Derivation (READY | DEGRADED | BLOCKED)
  const applicationGate: ApplicationGate = React.useMemo(() => {
    if (activeMode === 'PHYSICAL') {
      return 'BLOCKED'
    }
    if (connectionStatus === 'UNREACHABLE') {
      return 'DEGRADED'
    }
    return 'READY'
  }, [activeMode, connectionStatus])

  return (
    <div className="app-container">
      {/* Top Operational Navigation Bar */}
      <TopBar
        health={health}
        connectionStatus={connectionStatus}
        currentJob={currentJob}
        resultFreshness={resultFreshness}
        scientificValidity={scientificValidity}
        applicationGate={applicationGate}
        resultUsage={resultUsage}
        activeMode={activeMode}
        onModeChange={(mode) => setActiveMode(mode)}
        isExecuting={isExecuting}
        isQuarantined={isQuarantined}
      />

      {/* Operational Error / Physical Block Banner */}
      {activeError && (
        <div
          style={{
            background: 'rgba(244, 63, 94, 0.95)',
            color: '#ffffff',
            padding: '8px 16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            zIndex: 1000,
            fontSize: '11px',
            fontFamily: 'var(--font-mono)',
            boxShadow: '0 4px 12px rgba(244, 63, 94, 0.4)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertOctagon size={16} />
            <span>
              [{activeError.code}] {activeError.stage ? `(Stage: ${activeError.stage}) ` : ''}
              {activeError.message}
            </span>
          </div>
          <button
            type="button"
            onClick={() => setActiveError(null)}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#ffffff',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Main Workspace Body */}
      <div className="workspace-body">
        {/* Left Side Control Panel */}
        <LeftControlPanel
          activeMode={activeMode}
          currentJob={currentJob}
          jobList={jobList}
          layers={layers}
          scenarios={scenarios}
          selectedScenarioId={selectedScenarioId}
          onSelectScenario={(id) => setSelectedScenarioId(id)}
          onToggleLayer={handleToggleLayer}
          onRunPipeline={handleRunPipeline}
          onRunRealInvestigation={handleRunRealInvestigation}
          onSelectJob={handleSelectJob}
          isExecuting={isExecuting}
          resultFreshness={resultFreshness}
          isQuarantined={isQuarantined}
        />

        {/* Center 3D Globe Viewport */}
        <div style={{ flex: 1, position: 'relative', display: 'flex' }}>
          <GlobeView
            result={jobResult}
            selectedEvidenceId={selectedEvidenceId}
            onSelectEvidence={handleSelectEvidence}
            selectedLocation={selectedLocation}
            onSelectLocation={handleSelectLocation}
            layers={layers}
            isLoading={isExecuting}
            isQuarantined={isQuarantined}
          />
          <Legend />
        </div>

        {/* Right Evidence & Candidate Inspector */}
        <RightInspector
          result={jobResult}
          selectedEvidenceId={selectedEvidenceId}
          onSelectEvidence={handleSelectEvidence}
          selectedLocation={selectedLocation}
          selectionType={selectionType}
          onClearLocation={() => handleSelectLocation(null)}
          resultFreshness={resultFreshness}
          activeMode={activeMode}
          selectedScenarioId={selectedScenarioId}
          isQuarantined={isQuarantined}
        />
      </div>

      {/* Bottom Temporal Controller */}
      <BottomTimeline
        currentPhaseIndex={currentPhaseIndex}
        onPhaseChange={(idx) => setCurrentPhaseIndex(idx)}
        result={jobResult}
        isQuarantined={isQuarantined}
        isTemporalBlocked={isTemporalBlocked}
      />
    </div>
  )
}
export default App
