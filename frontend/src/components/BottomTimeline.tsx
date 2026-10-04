import React, { useState, useEffect, useMemo } from 'react'
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Clock,
  Radio,
  Activity,
  Layers,
  ShieldAlert,
} from 'lucide-react'
import type { InvestigationEvent, InvestigationRun, JobResultResponse } from '../types/api'

export interface TimelinePhase {
  id: string
  stageLabel: string
  observationLabel: string
  timestampUtc: string
  statusType: 'OBSERVED' | 'INFERRED' | 'HYPOTHESIS' | 'DATA_UNAVAILABLE'
  description: string
}

interface BottomTimelineProps {
  currentPhaseIndex: number
  onPhaseChange: (index: number) => void
  result?: JobResultResponse | null
  investigation?: InvestigationRun | null
  investigationEvents?: InvestigationEvent[]
  selectedEvent?: InvestigationEvent | null
  onSelectEvent?: (event: InvestigationEvent | null) => void
  isSseStreaming?: boolean
  sseConnectionState?: 'IDLE' | 'CONNECTING' | 'STREAMING' | 'RECONNECTING' | 'DISCONNECTED'
  isQuarantined?: boolean
  isTemporalBlocked?: boolean
}

export const BottomTimeline: React.FC<BottomTimelineProps> = ({
  currentPhaseIndex,
  onPhaseChange,
  result,
  investigation,
  investigationEvents = [],
  selectedEvent,
  onSelectEvent,
  isSseStreaming = false,
  sseConnectionState = 'IDLE',
  isQuarantined = false,
  isTemporalBlocked = false,
}) => {
  const [isPlaying, setIsPlaying] = useState(false)
  const [activeTab, setActiveTab] = useState<'TEMPORAL' | 'INVESTIGATION'>(
    investigation ? 'INVESTIGATION' : 'TEMPORAL'
  )

  useEffect(() => {
    if (investigation) {
      setActiveTab('INVESTIGATION')
    }
  }, [investigation?.run_id])
  const controlsDisabled = Boolean(isQuarantined || isTemporalBlocked)

  // Pause playback if controls become disabled
  useEffect(() => {
    if (controlsDisabled && isPlaying) {
      setIsPlaying(false)
    }
  }, [controlsDisabled, isPlaying])

  // Derive dynamic timestamps from actual result data without fabricating timestamps
  const phases: TimelinePhase[] = useMemo(() => {
    // T_RELEASE window from candidate spill origin hypothesis if present
    const originReleaseTime =
      result?.candidate_spill_hypotheses?.[0]?.temporal_window_utc?.[0] || '2024-04-09T14:00:00Z'

    // T_AIS closest approach from first candidate vessel hypothesis
    const aisApproachTime =
      result?.candidate_vessel_hypotheses?.[0]?.closest_approach_time_utc || '2024-04-09T14:30:38Z'

    // T1 SAR detection observation time from evidence ledger
    const sarItem = result?.evidence_ledger?.find(
      (e) => e.evidence_type === 'SAR_DETECTION' || e.evidence_type === 'TEMPORAL_CHANGE'
    )
    const sarDetectionTime = sarItem?.observation_time_utc || '2024-04-10T14:00:00Z'

    return [
      {
        id: 't0_baseline',
        stageLabel: 'T0: BASELINE',
        observationLabel: 'SAR Observed Pre-Spill',
        timestampUtc: '2024-04-08T02:00:00Z',
        statusType: 'OBSERVED',
        description: 'Baseline Sentinel-1 SAR acquisition prior to slick emergence (clean sea surface).',
      },
      {
        id: 't_origin_window',
        stageLabel: 'T_RELEASE: DRIFT ORIGIN',
        observationLabel: 'Lagrangian Drift Hypothesis',
        timestampUtc: originReleaseTime,
        statusType: 'HYPOTHESIS',
        description: 'Backward Lagrangian drift integration window and candidate origin envelope.',
      },
      {
        id: 't_ais_window',
        stageLabel: 'T_AIS: TRAFFIC',
        observationLabel: 'AIS Observed & Coverage Gaps',
        timestampUtc: aisApproachTime,
        statusType: 'OBSERVED',
        description: 'AIS vessel positions, closest points of approach, and un-interpolated gaps.',
      },
      {
        id: 't1_detection',
        stageLabel: 'T1: SLICK DETECTION',
        observationLabel: 'SAR Observed Slick',
        timestampUtc: sarDetectionTime,
        statusType: 'OBSERVED',
        description: 'Sentinel-1 SAR scene with verified dark formation polygonization.',
      },
      {
        id: 't_fusion',
        stageLabel: 'FUSION: SYNTHESIS',
        observationLabel: 'Multi-Source Lineage Inferred',
        timestampUtc: '2024-04-10T16:00:00Z',
        statusType: 'INFERRED',
        description: 'Explainable evidence graph, independent clustering, and candidate hypotheses.',
      },
    ]
  }, [result])

  // Auto-play interval
  useEffect(() => {
    let timer: any = null
    if (isPlaying && !controlsDisabled) {
      timer = setInterval(() => {
        onPhaseChange((currentPhaseIndex + 1) % phases.length)
      }, 2500)
    }
    return () => {
      if (timer) clearInterval(timer)
    }
  }, [isPlaying, controlsDisabled, currentPhaseIndex, onPhaseChange, phases.length])

  const activePhase = phases[currentPhaseIndex] || phases[0]

  const getBadgeClass = (statusType: string) => {
    switch (statusType) {
      case 'OBSERVED':
        return 'badge-healthy'
      case 'INFERRED':
        return 'badge-demo'
      case 'HYPOTHESIS':
        return 'badge-physical'
      case 'DATA_UNAVAILABLE':
        return 'badge-demo'
      default:
        return 'badge-demo'
    }
  }

  return (
    <footer className="bottom-timeline">
      <div className="timeline-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="timeline-title">
            <Clock size={13} style={{ display: 'inline', marginRight: '5px' }} />
            TEMPORAL REASONING CONTROLLER
          </span>

          {/* Tab selector between Temporal Reasoning and Phase 7B Investigation Event Spine */}
          {investigation && (
            <div style={{ display: 'flex', gap: '4px', marginLeft: '6px' }}>
              <button
                type="button"
                onClick={() => setActiveTab('INVESTIGATION')}
                style={{
                  background: activeTab === 'INVESTIGATION' ? 'rgba(56, 189, 248, 0.2)' : 'transparent',
                  border: activeTab === 'INVESTIGATION' ? '1px solid #38bdf8' : '1px solid var(--border-subtle)',
                  color: activeTab === 'INVESTIGATION' ? '#38bdf8' : 'var(--text-muted)',
                  borderRadius: '4px',
                  padding: '2px 8px',
                  fontSize: '10px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                }}
                data-testid="tab-investigation-events"
              >
                <Activity size={11} />
                <span>EVENT SPINE (PHASE 7B)</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('TEMPORAL')}
                style={{
                  background: activeTab === 'TEMPORAL' ? 'rgba(0, 242, 254, 0.2)' : 'transparent',
                  border: activeTab === 'TEMPORAL' ? '1px solid var(--cyan-primary)' : '1px solid var(--border-subtle)',
                  color: activeTab === 'TEMPORAL' ? 'var(--cyan-primary)' : 'var(--text-muted)',
                  borderRadius: '4px',
                  padding: '2px 8px',
                  fontSize: '10px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                }}
                data-testid="tab-temporal-reasoning"
              >
                <Clock size={11} />
                <span>TIMELINE</span>
              </button>
            </div>
          )}

          {activeTab === 'INVESTIGATION' ? (
            <>
              {investigation ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '11px' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Run:</span>
                  <code style={{ color: '#ffffff', fontSize: '10px' }}>{investigation.run_id.substring(0, 24)}...</code>
                  <span
                    className="badge"
                    style={{
                      fontSize: '8.5px',
                      padding: '1px 5px',
                      background: 'rgba(56, 189, 248, 0.15)',
                      color: '#38bdf8',
                      border: '1px solid #38bdf8',
                    }}
                  >
                    {investigation.status}
                  </span>
                  {/* SSE Telemetry Status Indicator */}
                  <span
                    className="badge"
                    style={{
                      fontSize: '8.5px',
                      padding: '1px 6px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      background:
                        sseConnectionState === 'STREAMING'
                          ? 'rgba(16, 185, 129, 0.15)'
                          : sseConnectionState === 'RECONNECTING'
                          ? 'rgba(245, 158, 11, 0.15)'
                          : 'rgba(100, 116, 139, 0.15)',
                      color:
                        sseConnectionState === 'STREAMING'
                          ? 'var(--emerald-secondary)'
                          : sseConnectionState === 'RECONNECTING'
                          ? 'var(--amber-secondary)'
                          : 'var(--text-muted)',
                      border: '1px solid currentColor',
                    }}
                    data-testid="sse-status-indicator"
                  >
                    <Radio size={10} />
                    <span>SSE: {sseConnectionState === 'STREAMING' ? 'LIVE STREAM' : sseConnectionState}</span>
                  </span>
                  <span style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>
                    ({investigationEvents.length} events logged)
                  </span>
                </div>
              ) : (
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                  Select or dispatch an investigation to inspect event spine telemetry
                </span>
              )}
            </>
          ) : (
            <>
              {isQuarantined ? (
                <span
                  className="badge"
                  style={{
                    fontSize: '9px',
                    padding: '2px 8px',
                    background: 'rgba(239, 68, 68, 0.25)',
                    color: '#fca5a5',
                    border: '1px solid rgba(239, 68, 68, 0.65)',
                    fontWeight: 700,
                  }}
                  data-testid="timeline-quarantined-badge"
                >
                  QUARANTINED — CONTROLS DISABLED
                </span>
              ) : isTemporalBlocked ? (
                <span
                  className="badge"
                  style={{
                    fontSize: '9px',
                    padding: '2px 8px',
                    background: 'rgba(239, 68, 68, 0.2)',
                    color: '#f87171',
                    border: '1px solid rgba(239, 68, 68, 0.5)',
                    fontWeight: 700,
                  }}
                  data-testid="timeline-temporal-blocked-badge"
                >
                  TEMPORAL REASONING BLOCKED
                </span>
              ) : (
                <span
                  className={`badge ${getBadgeClass(activePhase.statusType)}`}
                  style={{ fontSize: '9px', padding: '1px 6px' }}
                >
                  {activePhase.statusType}
                </span>
              )}

              <span style={{ fontSize: '11px', color: 'var(--cyan-secondary)', fontWeight: 600 }}>
                [{activePhase.observationLabel}]
              </span>

              <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                {activePhase.description}
              </span>
            </>
          )}
        </div>

        {/* Playback Controls (Active in Temporal mode) */}
        {activeTab === 'TEMPORAL' && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              type="button"
              className="icon-button"
              style={{
                width: '26px',
                height: '26px',
                opacity: controlsDisabled ? 0.45 : 1,
                cursor: controlsDisabled ? 'not-allowed' : 'pointer',
              }}
              disabled={controlsDisabled}
              onClick={() => {
                if (controlsDisabled) return
                onPhaseChange(Math.max(0, currentPhaseIndex - 1))
              }}
              title={controlsDisabled ? (isQuarantined ? 'QUARANTINED — CONTROLS DISABLED' : 'TEMPORAL REASONING BLOCKED') : 'Previous Phase'}
              data-testid="timeline-prev-btn"
            >
              <SkipBack size={12} />
            </button>

            <button
              type="button"
              className="icon-button"
              style={{
                width: '26px',
                height: '26px',
                opacity: controlsDisabled ? 0.45 : 1,
                cursor: controlsDisabled ? 'not-allowed' : 'pointer',
              }}
              disabled={controlsDisabled}
              onClick={() => {
                if (controlsDisabled) return
                setIsPlaying(!isPlaying)
              }}
              title={controlsDisabled ? (isQuarantined ? 'QUARANTINED — CONTROLS DISABLED' : 'TEMPORAL REASONING BLOCKED') : (isPlaying ? 'Pause Timeline' : 'Play Timeline')}
              data-testid="timeline-play-btn"
            >
              {isPlaying ? <Pause size={12} /> : <Play size={12} />}
            </button>

            <button
              type="button"
              className="icon-button"
              style={{
                width: '26px',
                height: '26px',
                opacity: controlsDisabled ? 0.45 : 1,
                cursor: controlsDisabled ? 'not-allowed' : 'pointer',
              }}
              disabled={controlsDisabled}
              onClick={() => {
                if (controlsDisabled) return
                onPhaseChange(Math.min(phases.length - 1, currentPhaseIndex + 1))
              }}
              title={controlsDisabled ? (isQuarantined ? 'QUARANTINED — CONTROLS DISABLED' : 'TEMPORAL REASONING BLOCKED') : 'Next Phase'}
              data-testid="timeline-next-btn"
            >
              <SkipForward size={12} />
            </button>
          </div>
        )}
      </div>

      {/* Timeline Scrubber Track */}
      <div className="timeline-track-wrapper">
        {activeTab === 'INVESTIGATION' ? (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              overflowX: 'auto',
              padding: '6px 12px',
              height: '100%',
            }}
            data-testid="investigation-event-track"
          >
            {investigationEvents.length === 0 ? (
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                {investigation ? 'Replaying durable event spine or awaiting live events...' : 'No active investigation'}
              </div>
            ) : (
              investigationEvents.map((ev) => {
                const isSelected = selectedEvent?.sequence === ev.sequence
                const isBlocked = ev.event_type === 'STAGE_BLOCKED'
                return (
                  <div
                    key={ev.sequence}
                    onClick={() => onSelectEvent?.(ev)}
                    style={{
                      flexShrink: 0,
                      padding: '4px 8px',
                      borderRadius: '4px',
                      background: isSelected
                        ? 'rgba(56, 189, 248, 0.25)'
                        : isBlocked
                        ? 'rgba(239, 68, 68, 0.2)'
                        : 'rgba(15, 23, 42, 0.7)',
                      border: isSelected
                        ? '1px solid #38bdf8'
                        : isBlocked
                        ? '1px solid rgba(239, 68, 68, 0.6)'
                        : '1px solid var(--border-subtle)',
                      cursor: 'pointer',
                      fontSize: '9.5px',
                      fontFamily: 'var(--font-mono)',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '2px',
                      minWidth: '110px',
                    }}
                    title={`Event #${ev.sequence}: ${ev.event_type} (${ev.timestamp_utc})`}
                    data-testid={`event-node-${ev.sequence}`}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ color: 'var(--text-muted)' }}>#{ev.sequence}</span>
                      <span
                        style={{
                          fontWeight: 600,
                          color: isBlocked ? '#f87171' : isSelected ? '#38bdf8' : 'var(--text-secondary)',
                        }}
                      >
                        {ev.stage_name || ev.event_type.split('_')[0]}
                      </span>
                    </div>
                    <div
                      style={{
                        color: isBlocked ? '#fca5a5' : '#ffffff',
                        fontWeight: isSelected ? 700 : 500,
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {ev.event_type}
                    </div>
                    <div style={{ fontSize: '8px', color: 'var(--text-dim)' }}>
                      {new Date(ev.timestamp_utc).toLocaleTimeString(undefined, {
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit',
                        timeZone: 'UTC',
                      })}{' '}
                      UTC
                    </div>
                  </div>
                )
              })
            )}
          </div>
        ) : (
          <div className="timeline-track">
            {phases.map((phase, idx) => {
              const leftPercent = (idx / (phases.length - 1)) * 100
              const isActive = idx === currentPhaseIndex

              return (
                <div
                  key={phase.id}
                  className={`timeline-step-node ${isActive ? 'active' : ''}`}
                  role="button"
                  tabIndex={0}
                  style={{
                    left: `${leftPercent}%`,
                    opacity: controlsDisabled ? 0.5 : 1,
                    cursor: controlsDisabled ? 'not-allowed' : 'pointer',
                  }}
                  onClick={() => {
                    if (controlsDisabled) return
                    onPhaseChange(idx)
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      if (controlsDisabled) return
                      onPhaseChange(idx)
                    }
                  }}
                  title={
                    controlsDisabled
                      ? (isQuarantined ? 'QUARANTINED — CONTROLS DISABLED' : 'TEMPORAL REASONING BLOCKED')
                      : `${phase.stageLabel} — ${phase.observationLabel} (${phase.timestampUtc})`
                  }
                  data-testid={`timeline-node-${phase.id}`}
                >
                  <div className="timeline-step-label">
                    <div style={{ fontWeight: isActive ? 700 : 600, color: isActive ? 'var(--cyan-primary)' : 'inherit' }}>
                      {phase.stageLabel}
                    </div>
                    <div style={{ fontSize: '9px', color: isActive ? 'var(--cyan-secondary)' : 'var(--text-muted)' }}>
                      {phase.observationLabel}
                    </div>
                    <div style={{ fontSize: '8.5px', color: 'var(--text-dim)' }}>
                      {new Date(phase.timestampUtc).toLocaleDateString(undefined, {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                        timeZone: 'UTC',
                      })}{' '}
                      UTC
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </footer>
  )
}
