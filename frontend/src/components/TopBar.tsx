import React from 'react'
import { Activity, ShieldAlert, Radio } from 'lucide-react'
import type {
  ApplicationGate,
  ConnectionStatus,
  HealthResponse,
  JobMode,
  JobResponse,
  ResultFreshness,
  ResultUsage,
  ScientificValidity,
} from '../types/api'

interface TopBarProps {
  health: HealthResponse | null
  connectionStatus: ConnectionStatus
  currentJob: JobResponse | null
  resultFreshness: ResultFreshness
  scientificValidity?: ScientificValidity
  applicationGate?: ApplicationGate
  resultUsage?: ResultUsage
  activeMode: JobMode
  onModeChange: (mode: JobMode) => void
  isExecuting: boolean
  isQuarantined?: boolean
}

export const TopBar: React.FC<TopBarProps> = ({
  health,
  connectionStatus,
  currentJob,
  resultFreshness,
  scientificValidity,
  applicationGate,
  resultUsage,
  activeMode,
  onModeChange,
  isExecuting,
  isQuarantined = false,
}) => {
  const effectiveGate: ApplicationGate =
    applicationGate ||
    (activeMode === 'PHYSICAL'
      ? 'BLOCKED'
      : connectionStatus === 'UNREACHABLE'
      ? 'DEGRADED'
      : 'READY')

  return (
    <header className="top-bar">
      <div className="brand-section">
        <div className="brand-logo">
          <Activity className="brand-icon" />
          <span>OCEAN SENTINEL</span>
        </div>
        <span className="brand-version">3D GEOSPATIAL V1.1</span>
      </div>

      <div className="top-bar-center">
        {/* Mode Selector: 3 Mutually Exclusive Modes */}
        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
          <button
            type="button"
            className={`btn ${activeMode === 'DEMO' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ padding: '4px 10px', fontSize: '11px' }}
            onClick={() => onModeChange('DEMO')}
            disabled={isExecuting}
            data-testid="mode-demo-btn"
          >
            DEMO MODE
          </button>
          <button
            type="button"
            className={`btn ${activeMode === 'REAL_REPOSITORY' ? 'btn-primary' : 'btn-secondary'}`}
            style={{
              padding: '4px 10px',
              fontSize: '11px',
              borderColor: activeMode === 'REAL_REPOSITORY' ? 'var(--cyan-primary)' : 'rgba(6, 182, 212, 0.4)',
              color: activeMode === 'REAL_REPOSITORY' ? '#ffffff' : 'var(--cyan-primary)',
              background: activeMode === 'REAL_REPOSITORY' ? 'rgba(6, 182, 212, 0.35)' : 'transparent',
              fontWeight: 600,
            }}
            onClick={() => onModeChange('REAL_REPOSITORY')}
            disabled={isExecuting}
            data-testid="mode-real-repo-btn"
          >
            REAL REPOSITORY
          </button>
          <button
            type="button"
            className={`btn ${activeMode === 'PHYSICAL' ? 'btn-danger' : 'btn-secondary'}`}
            style={{ padding: '4px 10px', fontSize: '11px' }}
            onClick={() => onModeChange('PHYSICAL')}
            disabled={isExecuting}
            data-testid="mode-physical-btn"
          >
            PHYSICAL (FAIL-CLOSED)
          </button>
        </div>

        {/* Current Job Display */}
        {currentJob && (
          <div className="job-indicator">
            <span style={{ color: 'var(--text-muted)' }}>JOB:</span>
            <span style={{ color: 'var(--cyan-primary)', fontWeight: 600 }}>
              {currentJob.job_id.length > 22
                ? `${currentJob.job_id.substring(0, 22)}...`
                : currentJob.job_id}
            </span>
            <span
              className={`badge ${
                currentJob.status === 'SUCCEEDED'
                  ? 'badge-healthy'
                  : currentJob.status === 'BLOCKED_PROVENANCE'
                  ? 'badge-physical'
                  : 'badge-demo'
              }`}
              style={{ fontSize: '9px', padding: '1px 5px' }}
            >
              {currentJob.status}
            </span>

            {/* Explicit Result Freshness Indicator */}
            {resultFreshness === 'LIVE_CURRENT' && connectionStatus === 'ONLINE' ? (
              <span
                className="badge badge-healthy"
                style={{
                  fontSize: '9px',
                  padding: '1px 6px',
                  background: 'rgba(16, 185, 129, 0.2)',
                  borderColor: 'rgba(16, 185, 129, 0.5)',
                  color: 'var(--emerald-secondary)',
                  fontWeight: 600,
                }}
                title="Fresh live execution verified in current session against active backend."
                data-testid="result-freshness-badge"
              >
                ● LIVE CURRENT
              </span>
            ) : (resultFreshness === 'CACHED_LAST_LOADED' || connectionStatus !== 'ONLINE') ? (
              <span
                className="badge badge-demo"
                style={{
                  fontSize: '9px',
                  padding: '1px 6px',
                  background: 'rgba(245, 158, 11, 0.2)',
                  borderColor: 'rgba(245, 158, 11, 0.5)',
                  color: 'var(--amber-secondary)',
                  fontWeight: 600,
                }}
                title="Backend is not currently connected or showing cached result from prior execution. Not a live current execution."
                data-testid="result-freshness-badge"
              >
                LAST LOADED RESULT
              </span>
            ) : null}

            {/* Explicit Scientific Validity Badge */}
            {scientificValidity && (
              <span
                className={`badge ${
                  scientificValidity === 'VALID_FOR_SCOPE'
                    ? 'badge-healthy'
                    : scientificValidity === 'PROVENANCE_LIMITED'
                    ? 'badge-demo'
                    : 'badge-physical'
                }`}
                style={{
                  fontSize: '9px',
                  padding: '1px 6px',
                  fontWeight: 600,
                }}
                title={`Scientific Validity: ${scientificValidity}`}
                data-testid="scientific-validity-badge"
              >
                {scientificValidity === 'BLOCKED'
                  ? 'SCIENTIFIC RESULT: BLOCKED'
                  : scientificValidity === 'PROVENANCE_LIMITED'
                  ? 'PROVENANCE LIMITED'
                  : scientificValidity === 'VALID_FOR_SCOPE'
                  ? 'VALID FOR SCOPE'
                  : 'LEGACY INVALID'}
              </span>
            )}

            {/* Explicit Quarantine / Result Usage Overlay Badge */}
            {(isQuarantined || resultUsage === 'QUARANTINED') && (
              <span
                className="badge badge-physical"
                style={{
                  fontSize: '9px',
                  padding: '1px 6px',
                  background: 'rgba(239, 68, 68, 0.25)',
                  borderColor: 'rgba(239, 68, 68, 0.6)',
                  color: '#fca5a5',
                  fontWeight: 700,
                  letterSpacing: '0.3px',
                }}
                title={`Result Usage Overlay: ${resultUsage || 'QUARANTINED'} — Cached evidence is quarantined from active operational interpretation due to scenario or mode mismatch.`}
                data-testid="quarantine-status-badge"
                data-result-usage={resultUsage || 'QUARANTINED'}
              >
                [EVIDENCE QUARANTINED]
              </span>
            )}
          </div>
        )}
      </div>

      <div className="top-bar-right">
        {/* Explicit Backend Connectivity State */}
        <div
          className={`badge ${
            connectionStatus === 'ONLINE'
              ? 'badge-healthy'
              : connectionStatus === 'OFFLINE'
              ? 'badge-demo'
              : 'badge-physical'
          }`}
          data-testid="backend-connection-badge"
          title={
            connectionStatus === 'ONLINE'
              ? `API ${health?.api_version || '1.0.0'} — ${health?.service || 'backend'} (Connected)`
              : connectionStatus === 'OFFLINE'
              ? 'Backend Service Offline (HTTP Error response)'
              : 'Backend Unreachable (Connection Refused / Network Error)'
          }
        >
          <span
            className="badge-status-dot"
            style={{
              backgroundColor:
                connectionStatus === 'ONLINE'
                  ? 'var(--emerald-primary)'
                  : connectionStatus === 'OFFLINE'
                  ? 'var(--amber-primary)'
                  : 'var(--rose-primary)',
              boxShadow:
                connectionStatus === 'ONLINE'
                  ? '0 0 8px var(--emerald-primary)'
                  : connectionStatus === 'OFFLINE'
                  ? '0 0 8px var(--amber-primary)'
                  : '0 0 8px var(--rose-primary)',
            }}
          />
          <span>BACKEND {connectionStatus}</span>
        </div>

        {/* Application Gate Indicator (Dimension 6: READY | DEGRADED | BLOCKED) */}
        <div
          className={`badge ${
            effectiveGate === 'BLOCKED'
              ? 'badge-physical'
              : effectiveGate === 'DEGRADED'
              ? 'badge-demo'
              : 'badge-healthy'
          }`}
          style={
            effectiveGate === 'READY'
              ? {
                  background: 'rgba(6, 182, 212, 0.15)',
                  color: 'var(--cyan-primary)',
                  border: '1px solid rgba(6, 182, 212, 0.4)',
                }
              : {}
          }
          data-testid="operational-gate-indicator"
          title={
            effectiveGate === 'BLOCKED'
              ? 'Application Gate: BLOCKED | External Sources: BLOCKED | Scientific Execution: BLOCKED (Fail-Closed). Physical mode requires verified operational feeds.'
              : effectiveGate === 'DEGRADED'
              ? 'Application Gate: DEGRADED | Backend: UNREACHABLE | External Sources: BLOCKED | Scientific Execution: CACHED INSPECTION ONLY.'
              : activeMode === 'REAL_REPOSITORY'
              ? 'Application Gate: READY | Backend: ONLINE | S1 Imagery: HISTORICAL_ARCHIVE | Drift & AIS: SYNTHETIC_DEMO | Scientific Validity: PROVENANCE_LIMITED.'
              : 'Application Gate: READY | Backend: ONLINE | Pipeline: SYNTHETIC_DEMO | Operational Feeds: NOT ATTACHED.'
          }
        >
          <ShieldAlert size={12} />
          <span>
            {effectiveGate === 'BLOCKED'
              ? 'APPLICATION GATE: BLOCKED'
              : effectiveGate === 'DEGRADED'
              ? 'APPLICATION GATE: DEGRADED'
              : 'APPLICATION GATE: READY'}
          </span>
        </div>

        {/* Non-Attribution Principle Notice */}
        <div
          className="badge"
          style={{
            background: 'rgba(79, 142, 247, 0.1)',
            color: 'var(--cyan-secondary)',
            border: '1px solid rgba(79, 142, 247, 0.25)',
          }}
          title="Non-Attribution Principle: Spatio-temporal compatibility only. No legal culpability or confirmed guilt."
        >
          <Radio size={12} />
          <span>NON-ATTRIBUTION V1</span>
        </div>
      </div>
    </header>
  )
}
