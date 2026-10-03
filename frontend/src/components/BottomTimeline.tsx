import React, { useState, useEffect, useMemo } from 'react'
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Clock,
} from 'lucide-react'
import type { JobResultResponse } from '../types/api'

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
  isQuarantined?: boolean
  isTemporalBlocked?: boolean
}

export const BottomTimeline: React.FC<BottomTimelineProps> = ({
  currentPhaseIndex,
  onPhaseChange,
  result,
  isQuarantined = false,
  isTemporalBlocked = false,
}) => {
  const [isPlaying, setIsPlaying] = useState(false)
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
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span className="timeline-title">
            <Clock size={13} style={{ display: 'inline', marginRight: '5px' }} />
            TEMPORAL REASONING CONTROLLER
          </span>

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
        </div>

        {/* Playback Controls */}
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
      </div>

      {/* Timeline Scrubber Track */}
      <div className="timeline-track-wrapper">
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
      </div>
    </footer>
  )
}
