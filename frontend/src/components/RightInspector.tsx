import React, { useState } from 'react'
import {
  FileText,
  Ship,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  HelpCircle,
  Layers,
  ChevronDown,
  ChevronRight,
  GitBranch,
  Info,
  Target,
  X,
  ShieldAlert,
  Database,
  Calendar,
  Hash,
  Activity,
  Cpu,
} from 'lucide-react'
import type {
  CandidateVesselHypothesis,
  InvestigationEvent,
  InvestigationRun,
  JobMode,
  JobResultResponse,
  ResultFreshness,
  SelectedLocation,
  SelectionType,
} from '../types/api'

interface RightInspectorProps {
  result: JobResultResponse | null
  investigation?: InvestigationRun | null
  selectedEvent?: InvestigationEvent | null
  onClearEvent?: () => void
  onClearInvestigation?: () => void
  selectedEvidenceId: string | null
  onSelectEvidence: (id: string | null) => void
  selectedLocation: SelectedLocation | null
  selectionType: SelectionType
  onClearLocation: () => void
  resultFreshness?: ResultFreshness
  activeMode?: JobMode
  selectedScenarioId?: string
  isQuarantined?: boolean
}

export const RightInspector: React.FC<RightInspectorProps> = ({
  result,
  investigation,
  selectedEvent,
  onClearEvent,
  onClearInvestigation,
  selectedEvidenceId,
  onSelectEvidence,
  selectedLocation,
  selectionType,
  onClearLocation,
  resultFreshness = 'NONE',
  activeMode,
  selectedScenarioId,
  isQuarantined: isQuarantinedProp,
}) => {
  const isScenarioMismatch = Boolean(
    result && selectedScenarioId && result.scenario_id && selectedScenarioId !== result.scenario_id
  )
  const isModeMismatch = Boolean(
    result && activeMode && result.mode && activeMode !== result.mode
  )
  const isQuarantined = isQuarantinedProp ?? (isScenarioMismatch || isModeMismatch)
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(
    result?.candidate_vessel_hypotheses?.[0]?.hypothesis_id || null
  )
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    supporting: true,
    conflicting: true,
    unknown: true,
    consistent: true,
    limitations: true,
  })

  const toggleSection = (key: string) => {
    setExpandedSections((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  // Find active candidate vessel hypothesis
  const activeCandidate =
    result?.candidate_vessel_hypotheses?.find(
      (h) => h.hypothesis_id === (selectedCandidateId || selectedEvidenceId)
    ) || result?.candidate_vessel_hypotheses?.[0]

  // Find active candidate spill hypothesis
  const activeSpillHypothesis = result?.candidate_spill_hypotheses?.find(
    (h) => h.hypothesis_id === selectedEvidenceId
  )

  // Find active evidence item from ledger
  const activeEvidenceItem = result?.evidence_ledger?.find(
    (e) => e.evidence_id === selectedEvidenceId
  )

  // Determine badge styling based on selectionType
  const getSelectionTypeBadge = () => {
    switch (selectionType) {
      case 'USER_LOCATION':
        return {
          label: 'USER LOCATION (REFERENCE)',
          className: 'badge',
          style: {
            background: 'rgba(0, 242, 254, 0.18)',
            color: 'var(--cyan-primary)',
            border: '1px solid rgba(0, 242, 254, 0.4)',
          },
        }
      case 'USER_AOI':
        return {
          label: 'USER INPUT (OPERATOR AOI)',
          className: 'badge',
          style: {
            background: 'rgba(0, 242, 254, 0.18)',
            color: 'var(--cyan-primary)',
            border: '1px solid rgba(0, 242, 254, 0.4)',
          },
        }
      case 'OBSERVATION_FOOTPRINT':
        return {
          label: 'REAL REPOSITORY EVIDENCE (S1 FOOTPRINT)',
          className: 'badge badge-healthy',
          style: {
            background: 'rgba(16, 185, 129, 0.18)',
            color: 'var(--emerald-secondary)',
            border: '1px solid rgba(16, 185, 129, 0.4)',
          },
        }
      case 'CANDIDATE_VESSEL':
        return {
          label: 'CANDIDATE VESSEL HYPOTHESIS',
          className: 'badge badge-healthy',
          style: {},
        }
      case 'CANDIDATE_SPILL_ORIGIN':
        return {
          label: 'CANDIDATE ORIGIN HYPOTHESIS',
          className: 'badge badge-physical',
          style: {},
        }
      case 'EVIDENCE_ITEM':
        return {
          label: 'EVIDENCE ITEM (LEDGER)',
          className: 'badge badge-demo',
          style: {},
        }
      default:
        return {
          label: investigation ? 'INVESTIGATION (PHASE 7C)' : 'OVERVIEW (ALL LAYERS)',
          className: 'badge',
          style: {
            background: 'rgba(100, 116, 139, 0.2)',
            color: 'var(--text-muted)',
            border: '1px solid rgba(100, 116, 139, 0.3)',
          },
        }
    }
  }

  const selectionBadge = getSelectionTypeBadge()

  return (
    <aside className="side-panel right-panel">
      <div className="panel-header">
        <span className="panel-title">
          <FileText size={14} />
          <span>EVIDENCE FUSION EXPLORER</span>
        </span>
        <span
          className={selectionBadge.className}
          style={{ fontSize: '9px', padding: '2px 6px', ...selectionBadge.style }}
        >
          {selectionBadge.label}
        </span>
      </div>

      <div className="panel-content">
        {/* Scientific Execution Gate Banner (Phase 7 Non-Negotiable Boundary) */}
        {investigation && (
          <section
            style={{
              padding: '10px 12px',
              background: 'rgba(239, 68, 68, 0.15)',
              borderRadius: '8px',
              border: '1px solid rgba(239, 68, 68, 0.55)',
              boxShadow: '0 0 12px rgba(239, 68, 68, 0.25)',
              display: 'flex',
              flexDirection: 'column',
              gap: '4px',
            }}
            data-testid="scientific-gate-banner"
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <ShieldAlert size={15} style={{ color: '#f87171' }} />
              <strong style={{ fontSize: '11px', color: '#fca5a5', letterSpacing: '0.4px' }}>
                BLOCKED: Scientific execution gated
              </strong>
            </div>
            <div style={{ fontSize: '10px', color: '#fee2e2', lineHeight: 1.35 }}>
              <code>EXECUTION_AUTHORIZED = False</code>. Stages <code>[INFER]</code> and <code>[INTERPRET]</code> remain strictly blocked. Automated oil spill detection, holdout inference, and vessel attribution are NOT authorized.
            </div>
          </section>
        )}

        {/* Selected Event Details Inspector Card */}
        {selectedEvent && (
          <section
            style={{
              padding: '10px 12px',
              background: 'rgba(15, 23, 42, 0.85)',
              borderRadius: '8px',
              border: '1px solid #38bdf8',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
            }}
            data-testid="selected-event-card"
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Activity size={13} style={{ color: '#38bdf8' }} />
                <span style={{ fontSize: '11px', fontWeight: 600, color: '#38bdf8' }}>
                  EVENT #{selectedEvent.sequence}: {selectedEvent.event_type}
                </span>
              </div>
              {onClearEvent && (
                <button
                  type="button"
                  onClick={onClearEvent}
                  style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
                  title="Dismiss Event"
                >
                  <X size={12} />
                </button>
              )}
            </div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px' }}>
              <div>Time: <span style={{ color: '#ffffff' }}>{new Date(selectedEvent.timestamp_utc).toUTCString()}</span></div>
              <div>Stage: <span style={{ color: '#38bdf8' }}>{selectedEvent.stage_name || 'N/A'}</span></div>
              {selectedEvent.error_type && (
                <div style={{ gridColumn: 'span 2', color: '#f87171' }}>
                  Error: {selectedEvent.error_type}
                </div>
              )}
            </div>
            {selectedEvent.payload && Object.keys(selectedEvent.payload).length > 0 && (
              <pre
                style={{
                  fontSize: '9px',
                  background: 'rgba(0, 0, 0, 0.4)',
                  padding: '6px',
                  borderRadius: '4px',
                  maxHeight: '100px',
                  overflowY: 'auto',
                  color: 'var(--text-secondary)',
                }}
              >
                {JSON.stringify(selectedEvent.payload, null, 2)}
              </pre>
            )}
          </section>
        )}

        {/* Investigation Run (Phase 7B/7C) Lifecycle Card */}
        {investigation && (
          <section
            style={{
              padding: '10px 12px',
              background: 'rgba(15, 23, 42, 0.85)',
              borderRadius: '8px',
              border: '1px solid rgba(56, 189, 248, 0.3)',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
            }}
            data-testid="investigation-lifecycle-card"
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '11px', fontWeight: 600, color: '#38bdf8' }}>
                INVESTIGATION RUN
              </span>
              <span
                className="badge"
                style={{
                  fontSize: '9px',
                  padding: '2px 6px',
                  background:
                    investigation.status === 'SUCCEEDED' || investigation.status === 'READY_FOR_DETECTION'
                      ? 'rgba(16, 185, 129, 0.15)'
                      : investigation.status === 'BLOCKED' || investigation.status === 'STAGE_BLOCKED'
                      ? 'rgba(239, 68, 68, 0.15)'
                      : 'rgba(56, 189, 248, 0.15)',
                  color:
                    investigation.status === 'SUCCEEDED' || investigation.status === 'READY_FOR_DETECTION'
                      ? 'var(--emerald-secondary)'
                      : investigation.status === 'BLOCKED' || investigation.status === 'STAGE_BLOCKED'
                      ? '#f87171'
                      : '#38bdf8',
                  border: '1px solid currentColor',
                }}
                data-testid="investigation-status-badge"
              >
                {investigation.status}
              </span>
            </div>

            <div style={{ fontSize: '10px', color: 'var(--text-muted)', display: 'grid', gridTemplateColumns: '1fr', gap: '4px' }}>
              <div>Run ID: <code style={{ color: '#ffffff' }}>{investigation.run_id}</code></div>
              {investigation.created_at_utc && (
                <div>Created: <span style={{ color: '#ffffff' }}>{new Date(investigation.created_at_utc).toUTCString()}</span></div>
              )}
              <div>Safety Gate: <strong style={{ color: '#f87171' }}>EXECUTION_AUTHORIZED = False</strong></div>
            </div>

            {/* Stages DAG Manifest */}
            <div style={{ marginTop: '4px' }}>
              <div style={{ fontSize: '9px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>
                EXECUTION DAG STAGES:
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                {['INGEST', 'DISCOVER', 'ACQUIRE', 'PERSIST', 'VALIDATE', 'INFER', 'INTERPRET'].map((st) => {
                  const stRec = investigation.stages ? (investigation.stages as any)[st] : null
                  const stStatus = stRec?.status || (st === 'INFER' || st === 'INTERPRET' ? 'BLOCKED' : 'COMPLETED')
                  const isBlocked = stStatus === 'BLOCKED' || stStatus === 'STAGE_BLOCKED'
                  return (
                    <div
                      key={st}
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        padding: '2px 6px',
                        borderRadius: '3px',
                        background: 'rgba(0, 0, 0, 0.3)',
                        fontSize: '9px',
                        fontFamily: 'var(--font-mono)',
                      }}
                    >
                      <span style={{ color: isBlocked ? '#fca5a5' : '#ffffff' }}>DAG:{st}</span>
                      <span style={{ color: isBlocked ? '#f87171' : 'var(--emerald-secondary)', fontWeight: 600 }}>
                        {isBlocked ? 'BLOCKED (GATED)' : 'COMPLETED'}
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
          </section>
        )}

        {/* Real Sentinel-1 Evidence Metadata Card */}
        {investigation?.observation_metadata && (
          <section
            style={{
              padding: '10px 12px',
              background: 'rgba(6, 78, 59, 0.2)',
              borderRadius: '8px',
              border: '1px solid rgba(16, 185, 129, 0.4)',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
            }}
            data-testid="s1-evidence-metadata-card"
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--emerald-secondary)' }}>
                SENTINEL-1 ACQUISITION EVIDENCE
              </span>
              <span
                className="badge badge-healthy"
                style={{ fontSize: '8.5px', padding: '1px 5px' }}
                data-testid="evidence-class-badge"
              >
                REAL_REPOSITORY_EVIDENCE
              </span>
            </div>

            <div style={{ fontSize: '9.5px', display: 'flex', flexDirection: 'column', gap: '3px' }}>
              <div>
                <span className="meta-label">Product / Scene ID: </span>
                <span style={{ color: '#ffffff', wordBreak: 'break-all' }}>
                  {investigation.observation_metadata.product_id || investigation.observation_metadata.scene_id || 'S1A_IW_GRDH_1SDV_REPOSITORY'}
                </span>
              </div>
              {investigation.observation_metadata.acquisition_timestamp_utc && (
                <div>
                  <span className="meta-label">Acquisition UTC: </span>
                  <span style={{ color: 'var(--emerald-secondary)' }}>
                    {investigation.observation_metadata.acquisition_timestamp_utc}
                  </span>
                </div>
              )}
              <div>
                <span className="meta-label">CRS: </span>
                <span style={{ color: '#ffffff' }}>
                  {investigation.observation_metadata.crs || 'EPSG:4326'}
                </span>
              </div>
              {investigation.observation_metadata.raster_dimensions && (
                <div>
                  <span className="meta-label">Dimensions: </span>
                  <span style={{ color: '#ffffff' }}>
                    {Array.isArray(investigation.observation_metadata.raster_dimensions)
                      ? `${investigation.observation_metadata.raster_dimensions[0]} × ${investigation.observation_metadata.raster_dimensions[1]} px`
                      : String(investigation.observation_metadata.raster_dimensions)}
                  </span>
                </div>
              )}
              <div>
                <span className="meta-label">Polarization / Bands: </span>
                <span style={{ color: '#ffffff' }}>
                  {Array.isArray(investigation.observation_metadata.polarization)
                    ? investigation.observation_metadata.polarization.join(', ')
                    : investigation.observation_metadata.polarization || 'VV, VH'}
                </span>
              </div>
              <div>
                <span className="meta-label">Raster Format: </span>
                <span style={{ color: '#ffffff' }}>
                  {investigation.observation_metadata.format || 'GeoTIFF (Cloud-Optimized)'}
                </span>
              </div>
              {investigation.observation_metadata.sha256 && (
                <div>
                  <span className="meta-label">SHA-256 Digest: </span>
                  <code style={{ fontSize: '8.5px', color: 'var(--cyan-primary)', wordBreak: 'break-all' }}>
                    {investigation.observation_metadata.sha256}
                  </code>
                </div>
              )}
              {investigation.observation_metadata.persistence_path && (
                <div>
                  <span className="meta-label">Persistence Ref: </span>
                  <code style={{ fontSize: '8.5px', color: 'var(--text-muted)' }}>
                    {investigation.observation_metadata.persistence_path.replace(/^[A-Z]:[/\\][^/\\]+[/\\][^/\\]+[/\\]/, '').replace(/\\/g, '/')}
                  </code>
                </div>
              )}
            </div>
          </section>
        )}

        {/* Operator AOI Parameters Card */}
        {investigation?.request && (
          <section
            style={{
              padding: '10px 12px',
              background: 'rgba(15, 23, 42, 0.8)',
              borderRadius: '8px',
              border: '1px solid rgba(0, 242, 254, 0.3)',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
            }}
            data-testid="aoi-geometry-card"
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--cyan-primary)' }}>
                OPERATOR AOI PARAMETERS
              </span>
              <span
                className="badge"
                style={{
                  fontSize: '8.5px',
                  padding: '1px 5px',
                  background: 'rgba(0, 242, 254, 0.15)',
                  color: 'var(--cyan-primary)',
                  border: '1px solid rgba(0, 242, 254, 0.3)',
                }}
                data-testid="aoi-evidence-class-badge"
              >
                USER_INPUT
              </span>
            </div>
            <div style={{ fontSize: '9.5px', display: 'flex', flexDirection: 'column', gap: '3px' }}>
              <div>
                <span className="meta-label">AOI Name: </span>
                <span style={{ color: '#ffffff' }}>{investigation.request.aoi_name || 'Operator Specified AOI'}</span>
              </div>
              {investigation.request.aoi_bounding_box && (
                <div>
                  <span className="meta-label">Bounding Box: </span>
                  <code style={{ fontSize: '8.5px', color: 'var(--cyan-secondary)' }}>
                    [{investigation.request.aoi_bounding_box.map((n: number) => n.toFixed(3)).join(', ')}]
                  </code>
                </div>
              )}
              <div>
                <span className="meta-label">Requested Polarization: </span>
                <span style={{ color: '#ffffff' }}>{investigation.request.polarization || 'VV+VH'}</span>
              </div>
            </div>
            <div
              style={{
                fontSize: '9px',
                color: 'var(--amber-secondary)',
                background: 'rgba(245, 158, 11, 0.1)',
                padding: '4px 6px',
                borderRadius: '4px',
                border: '1px solid rgba(245, 158, 11, 0.25)',
                lineHeight: 1.3,
              }}
            >
              <strong>NON-EVIDENCE INVARIANT:</strong> Operator AOI is user input parameterization, not physical satellite evidence.
            </div>
          </section>
        )}
        {/* User-Selected Location Inspector Card (Explicitly Non-Evidence) */}
        {selectedLocation && (
          <section
            style={{
              padding: '12px',
              background: 'rgba(15, 25, 48, 0.9)',
              borderRadius: '8px',
              border: '1px solid var(--cyan-primary)',
              boxShadow: '0 0 14px rgba(0, 242, 254, 0.25)',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Target size={14} style={{ color: 'var(--cyan-primary)' }} />
                <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--cyan-primary)' }}>
                  USER-SELECTED COORDINATE
                </span>
              </div>
              <button
                type="button"
                onClick={onClearLocation}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                }}
                title="Clear Selected Location"
              >
                <X size={13} />
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px', fontSize: '11px' }}>
              <div>
                <span className="meta-label">Latitude: </span>
                <span className="meta-value">
                  {selectedLocation.lat >= 0 ? `${selectedLocation.lat.toFixed(4)}° N` : `${Math.abs(selectedLocation.lat).toFixed(4)}° S`}
                </span>
              </div>
              <div>
                <span className="meta-label">Longitude: </span>
                <span className="meta-value">
                  {selectedLocation.lon >= 0 ? `${selectedLocation.lon.toFixed(4)}° E` : `${Math.abs(selectedLocation.lon).toFixed(4)}° W`}
                </span>
              </div>
              {selectedLocation.selectedAtUtc && (
                <div style={{ gridColumn: 'span 2' }}>
                  <span className="meta-label">Selected UTC: </span>
                  <span className="meta-value">
                    {new Date(selectedLocation.selectedAtUtc).toUTCString()}
                  </span>
                </div>
              )}
            </div>

            <div
              style={{
                fontSize: '10px',
                color: 'var(--amber-secondary)',
                background: 'rgba(245, 158, 11, 0.1)',
                padding: '6px 8px',
                borderRadius: '4px',
                border: '1px solid rgba(245, 158, 11, 0.25)',
                lineHeight: 1.4,
              }}
            >
              <strong>NON-EVIDENCE INVARIANT:</strong> A user-selected location is an operator reference target only. It is strictly isolated from scientific evidence, does not originate drift trajectories, and does not alter candidate vessel hypotheses.
            </div>
          </section>
        )}

        {/* Result Freshness Indicator Notice */}
        {result && resultFreshness === 'CACHED_LAST_LOADED' && (
          <div
            style={{
              padding: '6px 10px',
              marginBottom: '8px',
              borderRadius: '6px',
              background: 'rgba(245, 158, 11, 0.12)',
              border: '1px solid rgba(245, 158, 11, 0.4)',
              fontSize: '10px',
              color: 'var(--amber-secondary)',
              lineHeight: 1.35,
            }}
            data-testid="inspector-cached-notice"
          >
            <strong style={{ display: 'block', color: 'var(--amber-primary)', marginBottom: '2px' }}>
              ⚠ CACHED / LAST LOADED RESULT
            </strong>
            This evidence is from a prior execution (Job: <code>{result.job_id}</code>). It is NOT a live current execution. Backend availability or reconnection does not convert cached results into live results.
          </div>
        )}

        {result && resultFreshness === 'LIVE_CURRENT' && (
          <div
            style={{
              padding: '5px 8px',
              marginBottom: '8px',
              borderRadius: '4px',
              background: 'rgba(16, 185, 129, 0.12)',
              border: '1px solid rgba(16, 185, 129, 0.35)',
              fontSize: '9.5px',
              color: 'var(--emerald-secondary)',
            }}
            data-testid="inspector-live-notice"
          >
            ● <strong>LIVE CURRENT RESULT:</strong> Freshly executed against active backend in current session.
          </div>
        )}

        {/* Cached Evidence Quarantine Banner */}
        {result && isQuarantined && (
          <div
            style={{
              padding: '10px 12px',
              marginBottom: '10px',
              borderRadius: '6px',
              background: 'rgba(239, 68, 68, 0.2)',
              border: '1px solid rgba(239, 68, 68, 0.65)',
              color: '#ffffff',
              lineHeight: 1.4,
              boxShadow: '0 0 12px rgba(239, 68, 68, 0.25)',
            }}
            data-testid="quarantine-banner"
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
              <ShieldAlert size={14} style={{ color: '#f87171' }} />
              <strong style={{ color: '#fca5a5', fontSize: '11px', letterSpacing: '0.3px' }}>
                CACHED EVIDENCE QUARANTINED — NOT ACTIVE FOR CURRENT CONTEXT
              </strong>
            </div>
            <div style={{ fontSize: '10px', color: '#fee2e2', marginBottom: '4px' }}>
              {isScenarioMismatch && (
                <div>• <strong>Scenario Mismatch:</strong> Selected <code>{selectedScenarioId}</code> ≠ Cached Result <code>{result.scenario_id}</code></div>
              )}
              {isModeMismatch && (
                <div>• <strong>Mode Mismatch:</strong> Active Mode <code>{activeMode}</code> ≠ Cached Result Mode <code>{result.mode}</code></div>
              )}
            </div>
            <div style={{ fontSize: '9.5px', color: '#fca5a5', borderTop: '1px dashed rgba(239, 68, 68, 0.4)', paddingTop: '4px' }}>
              Original provenance, scientific validity, and historical identity are preserved. Interactive controls are neutralized to prevent misattribution. Execute fresh investigation to activate evidence for selected context.
            </div>
          </div>
        )}

        {/* Scenario Identity Protection Alert */}
        {result && selectedScenarioId && result.scenario_id && selectedScenarioId !== result.scenario_id && (
          <div
            style={{
              padding: '8px 10px',
              marginBottom: '8px',
              borderRadius: '6px',
              background: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid rgba(239, 68, 68, 0.45)',
              fontSize: '10px',
              color: '#fca5a5',
              lineHeight: 1.35,
            }}
            data-testid="inspector-scenario-mismatch-alert"
          >
            <strong style={{ display: 'block', color: '#f87171', marginBottom: '2px' }}>
              ⚠ SCENARIO SELECTION MISMATCH — EVIDENCE QUARANTINED
            </strong>
            Evidence explorer is displaying cached result for scenario <code>{result.scenario_id}</code>, but operational control selection is <code>{selectedScenarioId}</code>. This cached result is QUARANTINED and does NOT belong to the selected scenario.
          </div>
        )}

        {/* Mode Isolation Protection Alert */}
        {result && activeMode && result.mode && activeMode !== result.mode && (
          <div
            style={{
              padding: '8px 10px',
              marginBottom: '8px',
              borderRadius: '6px',
              background: 'rgba(245, 158, 11, 0.15)',
              border: '1px solid rgba(245, 158, 11, 0.45)',
              fontSize: '10px',
              color: 'var(--amber-secondary)',
              lineHeight: 1.35,
            }}
            data-testid="inspector-mode-mismatch-alert"
          >
            <strong style={{ display: 'block', color: 'var(--amber-primary)', marginBottom: '2px' }}>
              ⚠ MODE MISMATCH — EVIDENCE QUARANTINED
            </strong>
            Active operational mode is <code>{activeMode}</code>, but this cached result was generated under <code>{result.mode}</code>. Evidence is QUARANTINED. Mode switching never silently converts cached results between modes.
          </div>
        )}

        {/* Real Repository Investigation Provenance Card */}
        {result?.mode === 'REAL_REPOSITORY' && (
          <section
            style={{
              padding: '10px 12px',
              borderRadius: '8px',
              background: 'rgba(6, 182, 212, 0.08)',
              border: '1px solid rgba(6, 182, 212, 0.4)',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
            }}
            data-testid="real-repo-provenance-card"
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--cyan-primary)' }}>
                REAL REPOSITORY INVESTIGATION
              </span>
              <span
                className="badge badge-demo"
                style={{
                  fontSize: '9px',
                  padding: '2px 6px',
                  background: 'rgba(245, 158, 11, 0.15)',
                  color: 'var(--amber-secondary)',
                  border: '1px solid rgba(245, 158, 11, 0.35)',
                }}
                data-testid="provenance-badge"
              >
                {result.provenance_status === 'PROVENANCE_LIMITED' || result.has_synthetic_dependencies
                  ? 'FUSION STATUS: PROVENANCE LIMITED'
                  : `PROVENANCE: ${result.provenance_class || 'HISTORICAL_ARCHIVE'}`}
              </span>
            </div>

            {/* Lineage & Provenance Breakdown per Section 7 */}
            <div
              style={{
                padding: '6px 8px',
                borderRadius: '4px',
                background: 'rgba(15, 23, 42, 0.65)',
                border: '1px solid rgba(245, 158, 11, 0.25)',
                display: 'flex',
                flexDirection: 'column',
                gap: '3px',
                fontSize: '9.5px',
              }}
              data-testid="lineage-provenance-breakdown"
            >
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Satellite Source:</span>
                <span style={{ color: 'var(--emerald-secondary)', fontWeight: 600 }}>
                  {result.stage_provenance?.satellite || 'HISTORICAL_ARCHIVE'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Temporal Analysis:</span>
                <span style={{ color: 'var(--emerald-secondary)', fontWeight: 600 }}>
                  {result.stage_provenance?.temporal || 'HISTORICAL_ARCHIVE (DERIVED)'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Drift Forcing:</span>
                <span style={{ color: 'var(--amber-secondary)', fontWeight: 600 }}>
                  {result.stage_provenance?.drift || 'SYNTHETIC_DEMO'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>AIS Feed:</span>
                <span style={{ color: 'var(--amber-secondary)', fontWeight: 600 }}>
                  {result.stage_provenance?.ais || 'SYNTHETIC_DEMO'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '2px', marginTop: '2px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Fusion Status:</span>
                <span style={{ color: 'var(--amber-secondary)', fontWeight: 600 }}>
                  PROVENANCE LIMITED
                </span>
              </div>
            </div>

            <div style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>
              <strong>Scenario: </strong>
              <span style={{ color: '#ffffff' }}>
                {result.scenario_metadata?.label || result.investigation_label || result.scenario_id}
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px', fontSize: '9px' }}>
              <div>
                <span className="meta-label">Satellite Product ID: </span>
                <span style={{ color: 'var(--amber-secondary)' }}>
                  {result.scenario_metadata?.satellite_product_id || 'METADATA UNAVAILABLE'}
                </span>
              </div>
              <div>
                <span className="meta-label">Ground Truth: </span>
                <span style={{ color: 'var(--amber-secondary)' }}>
                  {result.scenario_metadata?.vessel_truth || 'METADATA UNAVAILABLE'}
                </span>
              </div>
              <div style={{ gridColumn: 'span 2' }}>
                <span className="meta-label">Incident Label: </span>
                <span style={{ color: 'var(--amber-secondary)' }}>
                  {result.scenario_metadata?.physical_incident_label || 'METADATA UNAVAILABLE'}
                </span>
              </div>
            </div>

            <div
              style={{
                fontSize: '9px',
                color: 'var(--amber-secondary)',
                lineHeight: 1.3,
                background: 'rgba(245, 158, 11, 0.08)',
                padding: '5px 7px',
                borderRadius: '4px',
                border: '1px dashed rgba(245, 158, 11, 0.35)',
              }}
            >
              <strong>PROVENANCE NOTICE:</strong> Real repository Sentinel-1 imagery with synthetic-derived downstream drift and AIS dependencies. Cannot claim pure historical provenance.
            </div>
          </section>
        )}

        {/* Guard Notice: Non-Attribution & Non-Guilt */}
        <div className="notice-box notice-warning">
          <AlertTriangle size={15} style={{ flexShrink: 0, marginTop: '2px' }} />
          <div>
            <strong>SPATIO-TEMPORAL COMPATIBILITY ONLY</strong>
            <div style={{ marginTop: '2px', fontSize: '10px' }}>
              Compatibility scores measure geometric/temporal alignment, NOT guilt, culpability, or causal attribution. Culpability or responsibility cannot be established through automated evidence correlation alone.
            </div>
          </div>
        </div>

        {/* Candidate Vessel Hypotheses Selector */}
        <section>
          <div
            style={{
              fontSize: '11px',
              fontWeight: 600,
              textTransform: 'uppercase',
              color: 'var(--text-muted)',
              marginBottom: '8px',
              letterSpacing: '0.4px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <span>CANDIDATE VESSEL HYPOTHESES</span>
            <span style={{ fontSize: '10px' }}>
              {result?.candidate_vessel_hypotheses?.length || 0} IDENTIFIED
            </span>
          </div>

          {/* Neutralization Notice when Quarantined */}
          {isQuarantined && (
            <div
              style={{
                padding: '6px 8px',
                marginBottom: '8px',
                borderRadius: '4px',
                background: 'rgba(239, 68, 68, 0.12)',
                border: '1px dashed rgba(239, 68, 68, 0.4)',
                fontSize: '9.5px',
                color: '#fca5a5',
                fontStyle: 'italic',
                lineHeight: 1.3,
              }}
              data-testid="quarantine-control-notice"
            >
              Interactive candidate selection neutralized while evidence is quarantined.
            </div>
          )}

          {result?.candidate_vessel_hypotheses?.map((cand: CandidateVesselHypothesis) => {
            const isSelected =
              activeCandidate?.hypothesis_id === cand.hypothesis_id
            const isConflicting = cand.overall_status === 'CONFLICTING_EVIDENCE'
            const isGap =
              cand.coverage_status === 'TELEMETRY_GAP' ||
              cand.overall_status === 'INSUFFICIENT_EVIDENCE'

            return (
              <div
                key={cand.hypothesis_id}
                className={`candidate-card ${isSelected ? 'selected' : ''}`}
                role="button"
                tabIndex={0}
                style={
                  isQuarantined
                    ? {
                        opacity: 0.55,
                        cursor: 'not-allowed',
                        filter: 'grayscale(0.35)',
                      }
                    : undefined
                }
                onClick={() => {
                  if (isQuarantined) return
                  setSelectedCandidateId(cand.hypothesis_id)
                  onSelectEvidence(cand.hypothesis_id)
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    if (isQuarantined) return
                    setSelectedCandidateId(cand.hypothesis_id)
                    onSelectEvidence(cand.hypothesis_id)
                  }
                }}
              >
                <div className="candidate-header">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Ship
                      size={14}
                      style={{
                        color: isConflicting
                          ? 'var(--rose-secondary)'
                          : isGap
                          ? 'var(--text-muted)'
                          : 'var(--cyan-primary)',
                      }}
                    />
                    <span className="candidate-name">
                      {cand.vessel_name || cand.mmsi}
                    </span>
                  </div>
                  <span
                    className="candidate-score"
                    style={{
                      color: isConflicting
                        ? 'var(--rose-secondary)'
                        : isGap
                        ? 'var(--text-muted)'
                        : 'var(--cyan-primary)',
                    }}
                  >
                    {cand.evidence_compatibility_score.toFixed(4)}
                  </span>
                </div>

                <div className="candidate-meta-grid">
                  <div>
                    <span className="meta-label">MMSI: </span>
                    <span className="meta-value">{cand.mmsi}</span>
                  </div>
                  <div>
                    <span className="meta-label">Min Distance: </span>
                    <span className="meta-value">
                      {Math.round(cand.closest_approach_distance_m)} m
                    </span>
                  </div>
                  <div>
                    <span className="meta-label">Temporal Offset: </span>
                    <span className="meta-value">
                      {cand.temporal_offset_hours.toFixed(1)} h
                    </span>
                  </div>
                  <div>
                    <span className="meta-label">Origin Enclosed: </span>
                    <span className="meta-value">
                      {cand.inside_origin_region ? 'YES' : 'NO'}
                    </span>
                  </div>
                </div>

                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    marginTop: '8px',
                    paddingTop: '6px',
                    borderTop: '1px solid rgba(79, 142, 247, 0.15)',
                    fontSize: '10px',
                  }}
                >
                  <span
                    className={`badge ${
                      isConflicting
                        ? 'badge-physical'
                        : isGap
                        ? 'badge-demo'
                        : 'badge-healthy'
                    }`}
                    style={{ fontSize: '9px', padding: '1px 5px' }}
                  >
                    {cand.overall_status}
                  </span>

                  <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    {cand.dependency_summary?.independent_source_clusters || 0} INDEP. CLUSTERS
                  </span>
                </div>
              </div>
            )
          })}
        </section>

        {/* Selected Candidate Evidence Chain */}
        {activeCandidate && (
          <section className="evidence-chain-section">
            <div
              style={{
                fontSize: '11px',
                fontWeight: 600,
                textTransform: 'uppercase',
                color: 'var(--text-muted)',
                letterSpacing: '0.4px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <GitBranch size={13} />
              <span>EVIDENCE CHAIN: {activeCandidate.vessel_name || activeCandidate.mmsi}</span>
            </div>

            {/* Supporting Evidence Group */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <div
                className="evidence-group-header"
                style={{ color: 'var(--emerald-secondary)', cursor: 'pointer' }}
                onClick={() => toggleSection('supporting')}
              >
                {expandedSections.supporting ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                <CheckCircle2 size={12} />
                <span>
                  SUPPORTING EVIDENCE ({activeCandidate.supporting_evidence_ids?.length || 0})
                </span>
              </div>

              {expandedSections.supporting && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', paddingLeft: '16px' }}>
                  {activeCandidate.supporting_evidence_ids?.length === 0 ? (
                    <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                      No direct supporting evidence items
                    </div>
                  ) : (
                    activeCandidate.supporting_evidence_ids?.map((id) => (
                      <div
                        key={id}
                        className={`evidence-item-pill ${selectedEvidenceId === id ? 'selected' : ''}`}
                        role="button"
                        tabIndex={0}
                        style={isQuarantined ? { opacity: 0.55, cursor: 'not-allowed' } : undefined}
                        onClick={() => {
                          if (isQuarantined) return
                          onSelectEvidence(id)
                        }}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault()
                            if (isQuarantined) return
                            onSelectEvidence(id)
                          }
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                          <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{id}</span>
                          <span style={{ color: 'var(--emerald-secondary)', fontSize: '10px' }}>CORROBORATED</span>
                        </div>
                        <span style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>
                          Spatio-temporal alignment with modelled release window.
                        </span>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>

            {/* Conflicting Evidence Group */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <div
                className="evidence-group-header"
                style={{ color: 'var(--rose-secondary)', cursor: 'pointer' }}
                onClick={() => toggleSection('conflicting')}
              >
                {expandedSections.conflicting ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                <XCircle size={12} />
                <span>
                  CONFLICTING EVIDENCE ({activeCandidate.conflicting_evidence_ids?.length || 0})
                </span>
              </div>

              {expandedSections.conflicting && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', paddingLeft: '16px' }}>
                  {activeCandidate.conflicting_evidence_ids?.length === 0 ? (
                    <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                      No direct conflicting evidence items
                    </div>
                  ) : (
                    activeCandidate.conflicting_evidence_ids?.map((id) => (
                      <div
                        key={id}
                        className={`evidence-item-pill ${selectedEvidenceId === id ? 'selected' : ''}`}
                        role="button"
                        tabIndex={0}
                        style={isQuarantined ? { opacity: 0.55, cursor: 'not-allowed' } : undefined}
                        onClick={() => {
                          if (isQuarantined) return
                          onSelectEvidence(id)
                        }}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault()
                            if (isQuarantined) return
                            onSelectEvidence(id)
                          }
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                          <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{id}</span>
                          <span style={{ color: 'var(--rose-secondary)', fontSize: '10px' }}>CONFLICT</span>
                        </div>
                        <span style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>
                          Temporal or spatial distance exceeds allowable tolerance bounds.
                        </span>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>

            {/* Unknown / Telemetry Gaps */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <div
                className="evidence-group-header"
                style={{ color: 'var(--amber-secondary)', cursor: 'pointer' }}
                onClick={() => toggleSection('unknown')}
              >
                {expandedSections.unknown ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                <HelpCircle size={12} />
                <span>
                  DATA_UNAVAILABLE / TELEMETRY GAPS ({activeCandidate.unknown_evidence_ids?.length || 0})
                </span>
              </div>

              {expandedSections.unknown && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', paddingLeft: '16px' }}>
                  {activeCandidate.unknown_evidence_ids?.length === 0 ? (
                    <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                      No unresolved telemetry gaps in observation window
                    </div>
                  ) : (
                    activeCandidate.unknown_evidence_ids?.map((id) => (
                      <div
                        key={id}
                        className={`evidence-item-pill ${selectedEvidenceId === id ? 'selected' : ''}`}
                        role="button"
                        tabIndex={0}
                        style={isQuarantined ? { opacity: 0.55, cursor: 'not-allowed' } : undefined}
                        onClick={() => {
                          if (isQuarantined) return
                          onSelectEvidence(id)
                        }}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault()
                            if (isQuarantined) return
                            onSelectEvidence(id)
                          }
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                          <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{id}</span>
                          <span style={{ color: 'var(--amber-secondary)', fontSize: '10px' }}>GAP</span>
                        </div>
                        <span style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>
                          AIS telemetry outage: position was not interpolated across gap.
                        </span>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>

            {/* Scientific Limitations Accordion */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginTop: '6px' }}>
              <div
                className="evidence-group-header"
                style={{ color: 'var(--text-secondary)', cursor: 'pointer' }}
                onClick={() => toggleSection('limitations')}
              >
                {expandedSections.limitations ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                <Info size={12} />
                <span>SCIENTIFIC LIMITATIONS ({activeCandidate.limitations?.length || 0})</span>
              </div>

              {expandedSections.limitations && (
                <ul
                  style={{
                    paddingLeft: '24px',
                    fontSize: '10.5px',
                    color: 'var(--text-muted)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '4px',
                  }}
                >
                  {activeCandidate.limitations?.map((lim, idx) => (
                    <li key={idx}>{lim}</li>
                  ))}
                </ul>
              )}
            </div>
          </section>
        )}

        {/* Selected Evidence Item Inspector (when a specific item is clicked) */}
        {activeEvidenceItem && (
          <section
            style={{
              padding: '12px',
              background: 'rgba(15, 23, 42, 0.85)',
              borderRadius: '8px',
              border: '1px solid var(--border-subtle)',
              marginTop: '12px',
            }}
          >
            <div
              style={{
                fontSize: '11px',
                fontWeight: 600,
                color: 'var(--cyan-primary)',
                marginBottom: '8px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <Layers size={13} />
              <span>SELECTED EVIDENCE METADATA</span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '11px' }}>
              <div>
                <span className="meta-label">Evidence ID: </span>
                <span className="meta-value" style={{ wordBreak: 'break-all' }}>
                  {activeEvidenceItem.evidence_id}
                </span>
              </div>
              <div>
                <span className="meta-label">Evidence Type: </span>
                <span className="meta-value">{activeEvidenceItem.evidence_type}</span>
              </div>
              <div>
                <span className="meta-label">Source Type: </span>
                <span className="meta-value">{activeEvidenceItem.source_type}</span>
              </div>
              <div>
                <span className="meta-label">Observation Time: </span>
                <span className="meta-value">
                  {new Date(activeEvidenceItem.observation_time_utc).toUTCString()}
                </span>
              </div>
              <div>
                <span className="meta-label">Observation Status: </span>
                <span
                  className={`badge ${
                    activeEvidenceItem.observed_vs_inferred === 'OBSERVED'
                      ? 'badge-healthy'
                      : activeEvidenceItem.observed_vs_inferred === 'INFERRED'
                      ? 'badge-demo'
                      : 'badge-physical'
                  }`}
                  style={{ fontSize: '9px', padding: '1px 5px' }}
                >
                  {activeEvidenceItem.observed_vs_inferred}
                </span>
              </div>
              <div>
                <span className="meta-label">Provenance Class: </span>
                <span className="meta-value">{activeEvidenceItem.provenance_class}</span>
              </div>
              <div>
                <span className="meta-label">Derivation Type: </span>
                <span className="meta-value">{activeEvidenceItem.derivation_type}</span>
              </div>
            </div>
          </section>
        )}

        {/* Selected Candidate Spill Hypothesis (Origin Region) */}
        {activeSpillHypothesis && (
          <section
            style={{
              padding: '12px',
              background: 'rgba(234, 88, 12, 0.12)',
              borderRadius: '8px',
              border: '1px solid rgba(234, 88, 12, 0.35)',
              marginTop: '12px',
            }}
          >
            <div
              style={{
                fontSize: '11px',
                fontWeight: 600,
                color: 'var(--amber-secondary)',
                marginBottom: '8px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <Layers size={13} />
              <span>CANDIDATE ORIGIN HYPOTHESIS</span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '11px' }}>
              <div>
                <span className="meta-label">Hypothesis ID: </span>
                <span className="meta-value">{activeSpillHypothesis.hypothesis_id}</span>
              </div>
              <div>
                <span className="meta-label">Subject ID: </span>
                <span className="meta-value">{activeSpillHypothesis.subject_id}</span>
              </div>
              <div>
                <span className="meta-label">Overall Status: </span>
                <span className="badge badge-demo" style={{ fontSize: '9px', padding: '1px 5px' }}>
                  {activeSpillHypothesis.overall_status}
                </span>
              </div>
              <div>
                <span className="meta-label">Indep. Source Clusters: </span>
                <span className="meta-value">
                  {activeSpillHypothesis.independent_support_cluster_count}
                </span>
              </div>
              <div>
                <span className="meta-label">Summary: </span>
                <span style={{ fontSize: '10.5px', color: 'var(--text-secondary)' }}>
                  {activeSpillHypothesis.summary}
                </span>
              </div>
            </div>
          </section>
        )}
      </div>
    </aside>
  )
}
