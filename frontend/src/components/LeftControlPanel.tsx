import React from 'react'
import {
  Play,
  Layers,
  History,
  ShieldCheck,
  AlertOctagon,
  Navigation,
} from 'lucide-react'
import type {
  InvestigationScenario,
  JobMode,
  JobResponse,
  LayerVisibility,
  PipelineType,
  ResultFreshness,
} from '../types/api'

interface LeftControlPanelProps {
  activeMode: JobMode
  currentJob: JobResponse | null
  jobList: JobResponse[]
  layers: LayerVisibility
  scenarios: InvestigationScenario[]
  selectedScenarioId: string
  onSelectScenario: (scenarioId: string) => void
  onToggleLayer: (layerKey: keyof LayerVisibility) => void
  onRunPipeline: (mode: JobMode, pipelineType: PipelineType) => void
  onRunRealInvestigation: (scenarioId: string) => void
  onSelectJob: (jobId: string) => void
  isExecuting: boolean
  resultFreshness?: ResultFreshness
  isQuarantined?: boolean
}

export const LeftControlPanel: React.FC<LeftControlPanelProps> = ({
  activeMode,
  currentJob,
  jobList,
  layers,
  scenarios,
  selectedScenarioId,
  onSelectScenario,
  onToggleLayer,
  onRunPipeline,
  onRunRealInvestigation,
  onSelectJob,
  isExecuting,
  resultFreshness = 'NONE',
  isQuarantined = false,
}) => {
  const selectedScenario = scenarios.find((s) => s.scenario_id === selectedScenarioId) || scenarios[0]

  const PIPELINE_STAGES = [
    'VALIDATE',
    'INGEST',
    'INFER',
    'INTERPRET',
    'TEMPORAL',
    'DRIFT',
    'AIS',
    'FUSION',
    'EXPORT',
  ]

  return (
    <aside className="side-panel left-panel">
      <div className="panel-header">
        <span className="panel-title">
          <Navigation size={14} />
          <span>OPERATIONAL CONTROLS</span>
        </span>
        <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
          {isQuarantined && (
            <span
              className="badge badge-physical"
              style={{ fontSize: '8.5px', padding: '1px 5px', fontWeight: 700 }}
              title="Evidence is quarantined for the selected context"
            >
              QUARANTINED
            </span>
          )}
          <span
            className={`badge ${
              activeMode === 'REAL_REPOSITORY'
                ? 'badge-healthy'
                : activeMode === 'PHYSICAL'
                ? 'badge-physical'
                : 'badge-demo'
            }`}
            style={{ fontSize: '9px', padding: '1px 6px' }}
          >
            {activeMode}
          </span>
        </div>
      </div>

      <div className="panel-content">
        {/* Real Repository Scenario Investigation Mode */}
        {activeMode === 'REAL_REPOSITORY' && (
          <section>
            <div
              style={{
                fontSize: '11px',
                fontWeight: 600,
                textTransform: 'uppercase',
                color: 'var(--cyan-primary)',
                marginBottom: '8px',
                letterSpacing: '0.4px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <Layers size={13} />
              <span>REAL DATASET SCENARIO</span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div>
                <label style={{ fontSize: '10px', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>
                  SELECT VERIFIED SCENARIO:
                </label>
                <select
                  className="btn btn-secondary btn-block"
                  style={{
                    textAlign: 'left',
                    padding: '6px 8px',
                    fontSize: '11px',
                    background: 'rgba(15, 23, 42, 0.8)',
                    borderColor: 'var(--cyan-primary)',
                    color: '#ffffff',
                    cursor: 'pointer',
                  }}
                  value={selectedScenarioId}
                  onChange={(e) => onSelectScenario(e.target.value)}
                  disabled={isExecuting}
                  data-testid="scenario-select"
                >
                  {scenarios.map((sc) => (
                    <option key={sc.scenario_id} value={sc.scenario_id} style={{ background: '#0b1120' }}>
                      {sc.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Scenario Metadata Card (Authentic: never manufactured) */}
              {selectedScenario && (
                <div
                  style={{
                    padding: '8px 10px',
                    borderRadius: '6px',
                    background: 'rgba(15, 23, 42, 0.65)',
                    border: '1px solid rgba(6, 182, 212, 0.25)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '4px',
                    fontSize: '10px',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Dataset:</span>
                    <span style={{ color: '#ffffff', fontWeight: 500, textAlign: 'right', maxWidth: '170px' }}>
                      {selectedScenario.dataset}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Scene Pair:</span>
                    <span style={{ color: 'var(--cyan-primary)', fontFamily: 'var(--font-mono)' }}>
                      {selectedScenario.scene_pair.join(' → ')}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Region:</span>
                    <span style={{ color: '#ffffff' }}>{selectedScenario.region}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Satellite Product ID:</span>
                    <span style={{ color: 'var(--amber-secondary)', fontStyle: 'italic' }}>
                      {selectedScenario.satellite_product_id}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Vessel Ground Truth:</span>
                    <span style={{ color: 'var(--amber-secondary)', fontStyle: 'italic' }}>
                      {selectedScenario.vessel_truth}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Provenance Class:</span>
                    <span
                      className={`badge ${
                        selectedScenario.has_synthetic_dependencies
                          ? 'badge-demo'
                          : 'badge-healthy'
                      }`}
                      style={{
                        fontSize: '9px',
                        padding: '1px 5px',
                        maxWidth: '170px',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                      title={selectedScenario.provenance_class}
                      data-testid="scenario-provenance-badge"
                    >
                      {selectedScenario.provenance_status === 'PROVENANCE_LIMITED'
                        ? 'PROVENANCE LIMITED'
                        : selectedScenario.provenance_class}
                    </span>
                  </div>
                  {selectedScenario.source_pair_status && (
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ color: 'var(--text-muted)' }}>Source Pair Status:</span>
                      <span
                        style={{
                          fontSize: '9px',
                          fontWeight: 600,
                          padding: '1px 5px',
                          borderRadius: '3px',
                          maxWidth: '170px',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          background:
                            selectedScenario.source_pair_status === 'INVALID_DUPLICATE_IMAGE_PAIR'
                              ? 'rgba(239, 68, 68, 0.2)'
                              : 'rgba(16, 185, 129, 0.2)',
                          color:
                            selectedScenario.source_pair_status === 'INVALID_DUPLICATE_IMAGE_PAIR'
                              ? '#fca5a5'
                              : '#6ee7b7',
                          border:
                            selectedScenario.source_pair_status === 'INVALID_DUPLICATE_IMAGE_PAIR'
                              ? '1px solid rgba(239, 68, 68, 0.4)'
                              : '1px solid rgba(16, 185, 129, 0.4)',
                        }}
                        data-testid="scenario-source-pair-status"
                      >
                        {selectedScenario.source_pair_status}
                      </span>
                    </div>
                  )}
                  {selectedScenario.temporal_status && (
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ color: 'var(--text-muted)' }}>Temporal Status:</span>
                      <span
                        style={{
                          fontSize: '9px',
                          fontWeight: 600,
                          color: selectedScenario.temporal_status === 'BLOCKED' ? '#ef4444' : '#10b981',
                        }}
                        data-testid="scenario-temporal-status"
                      >
                        {selectedScenario.temporal_status}
                      </span>
                    </div>
                  )}
                  {selectedScenario.source_pair_status === 'INVALID_DUPLICATE_IMAGE_PAIR' && (
                    <div
                      style={{
                        fontSize: '9px',
                        color: '#fca5a5',
                        background: 'rgba(239, 68, 68, 0.12)',
                        padding: '6px 8px',
                        borderRadius: '4px',
                        border: '1px solid rgba(239, 68, 68, 0.4)',
                        lineHeight: 1.35,
                        marginTop: '3px',
                      }}
                      data-testid="duplicate-raster-alert"
                    >
                      <strong style={{ display: 'block', color: '#f87171', marginBottom: '2px' }}>
                        IDENTICAL SOURCE RASTERS (NON-TEMPORAL)
                      </strong>
                      T0 and T1 source rasters are byte-for-byte identical. Temporal differencing is BLOCKED. Different annotation masks represent annotation divergence, NOT physical SAR change.
                    </div>
                  )}
                  {selectedScenario.has_synthetic_dependencies && (
                    <div
                      style={{
                        fontSize: '9px',
                        color: 'var(--amber-secondary)',
                        background: 'rgba(245, 158, 11, 0.1)',
                        padding: '3px 6px',
                        borderRadius: '3px',
                        border: '1px solid rgba(245, 158, 11, 0.25)',
                        lineHeight: 1.3,
                        marginTop: '2px',
                      }}
                    >
                      Synthetic dependencies detected: drift & AIS fixtures.
                    </div>
                  )}

                  {/* Scenario Identity Protection: Warn if cached job belongs to another scenario */}
                  {currentJob?.scenario_id && selectedScenarioId !== currentJob.scenario_id && (
                    <div
                      style={{
                        fontSize: '9px',
                        color: '#fca5a5',
                        background: 'rgba(239, 68, 68, 0.15)',
                        padding: '6px 8px',
                        borderRadius: '4px',
                        border: '1px solid rgba(239, 68, 68, 0.45)',
                        lineHeight: 1.35,
                        marginTop: '4px',
                      }}
                      data-testid="scenario-mismatch-banner"
                    >
                      <div style={{ marginBottom: '2px' }}>
                        <strong style={{ color: '#f87171' }}>
                          ⚠ SCENARIO SELECTION MISMATCH — EVIDENCE QUARANTINED
                        </strong>
                      </div>
                      Selected scenario is <code>{selectedScenarioId}</code>, but loaded cached evidence belongs to <code>{currentJob.scenario_id}</code>. Cached evidence is QUARANTINED and neutralized from active operational interpretation for the newly selected scenario. Original provenance and historical identity are preserved. Run investigation to generate fresh evidence for this scenario.
                    </div>
                  )}
                </div>
              )}

              <button
                type="button"
                className="btn btn-primary btn-block"
                style={{
                  background: 'linear-gradient(135deg, rgba(6, 182, 212, 0.4), rgba(59, 130, 246, 0.4))',
                  borderColor: 'var(--cyan-primary)',
                  fontWeight: 600,
                  boxShadow: '0 0 12px rgba(6, 182, 212, 0.25)',
                }}
                onClick={() => onRunRealInvestigation(selectedScenarioId)}
                disabled={isExecuting}
                data-testid="run-real-investigation-btn"
              >
                <Play size={13} fill="currentColor" />
                <span>RUN REAL INVESTIGATION</span>
              </button>
            </div>
          </section>
        )}

        {/* Demo Pipeline Execution Dispatch */}
        {activeMode === 'DEMO' && (
          <section>
            <div
              style={{
                fontSize: '11px',
                fontWeight: 600,
                textTransform: 'uppercase',
                color: 'var(--text-muted)',
                marginBottom: '8px',
                letterSpacing: '0.4px',
              }}
            >
              DEMO ORCHESTRATION
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <button
                type="button"
                className="btn btn-primary btn-block"
                onClick={() => onRunPipeline('DEMO', 'DEMO_FUSION')}
                disabled={isExecuting}
                data-testid="run-demo-fusion-btn"
              >
                <Play size={13} fill="currentColor" />
                <span>RUN DEMO_FUSION</span>
              </button>

              <button
                type="button"
                className="btn btn-secondary btn-block"
                onClick={() => onRunPipeline('DEMO', 'ARTIFACT_FUSION')}
                disabled={isExecuting}
                data-testid="run-artifact-fusion-btn"
              >
                <Layers size={13} />
                <span>RUN ARTIFACT_FUSION</span>
              </button>

              <button
                type="button"
                className="btn btn-danger btn-block"
                onClick={() => onRunPipeline('PHYSICAL', 'PHYSICAL')}
                disabled={isExecuting}
                title="Test PHYSICAL fail-closed provenance blocking"
                data-testid="run-physical-btn"
              >
                <AlertOctagon size={13} />
                <span>RUN PHYSICAL (TEST BLOCK)</span>
              </button>
            </div>
          </section>
        )}

        {/* Physical Mode Notice & Test Button */}
        {activeMode === 'PHYSICAL' && (
          <section>
            <div className="notice-box notice-danger">
              <AlertOctagon size={16} style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>
                <strong>PHYSICAL FAIL-CLOSED GATE</strong>
                <div style={{ marginTop: '2px' }}>
                  Operational physical satellite/AIS feeds are currently unavailable.
                  System rejects unauthenticated physical jobs to prevent synthetic bleed.
                </div>
              </div>
            </div>

            <button
              type="button"
              className="btn btn-danger btn-block"
              style={{ marginTop: '8px' }}
              onClick={() => onRunPipeline('PHYSICAL', 'PHYSICAL')}
              disabled={isExecuting}
              title="Test PHYSICAL fail-closed provenance blocking"
              data-testid="run-physical-btn-mode"
            >
              <AlertOctagon size={13} />
              <span>RUN PHYSICAL (TEST BLOCK)</span>
            </button>
          </section>
        )}

        {/* Pipeline Stage Progress Monitor (Manifest State Faithful per Section 10) */}
        {currentJob && (
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
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <span>PIPELINE STAGES MANIFEST</span>
                {resultFreshness === 'CACHED_LAST_LOADED' && (
                  <span
                    className="badge badge-demo"
                    style={{ fontSize: '8.5px', padding: '1px 5px', color: 'var(--amber-secondary)' }}
                    data-testid="manifest-cached-badge"
                    title="Manifest shows cached results from a prior execution."
                  >
                    CACHED
                  </span>
                )}
                {currentJob?.scenario_id && selectedScenarioId !== currentJob.scenario_id && (
                  <>
                    <span
                      className="badge badge-demo"
                      style={{
                        fontSize: '8.5px',
                        padding: '1px 5px',
                        color: 'var(--rose-secondary)',
                        borderColor: 'rgba(244, 63, 94, 0.4)',
                      }}
                      data-testid="manifest-mismatch-badge"
                      title={`Job belongs to ${currentJob.scenario_id}, not currently selected ${selectedScenarioId}`}
                    >
                      MISMATCH
                    </span>
                    <span
                      className="badge badge-physical"
                      style={{
                        fontSize: '8.5px',
                        padding: '1px 5px',
                        background: 'rgba(239, 68, 68, 0.25)',
                        borderColor: 'rgba(239, 68, 68, 0.6)',
                        color: '#fca5a5',
                      }}
                      data-testid="manifest-quarantine-badge"
                      title="Evidence quarantined due to scenario mismatch"
                    >
                      QUARANTINED
                    </span>
                  </>
                )}
              </div>
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
            </div>

            <div
              style={{
                borderRadius: '6px',
                background: 'rgba(11, 18, 33, 0.7)',
                border: '1px solid var(--border-subtle)',
                overflow: 'hidden',
              }}
            >
              {PIPELINE_STAGES.map((stName) => {
                const rec = currentJob.stage_status?.[stName]
                const statusVal = rec?.status || (currentJob.status === 'RUNNING' && currentJob.current_stage === stName ? 'RUNNING' : 'PENDING')

                let statusBadgeColor = 'var(--text-muted)'
                let statusBg = 'transparent'
                let labelText = statusVal

                if (statusVal === 'COMPLETED') {
                  statusBadgeColor = 'var(--emerald-secondary)'
                  statusBg = 'rgba(16, 185, 129, 0.15)'
                  labelText = '✓ COMPLETED'
                } else if (statusVal === 'SKIPPED') {
                  statusBadgeColor = 'var(--amber-secondary)'
                  statusBg = 'rgba(245, 158, 11, 0.15)'
                  labelText = 'SKIPPED'
                } else if (statusVal === 'BLOCKED') {
                  statusBadgeColor = 'var(--rose-secondary)'
                  statusBg = 'rgba(244, 63, 94, 0.15)'
                  labelText = 'BLOCKED'
                } else if (statusVal === 'FAILED') {
                  statusBadgeColor = 'var(--rose-secondary)'
                  statusBg = 'rgba(244, 63, 94, 0.15)'
                  labelText = 'FAILED'
                } else if (statusVal === 'RUNNING') {
                  statusBadgeColor = 'var(--cyan-primary)'
                  statusBg = 'rgba(6, 182, 212, 0.2)'
                  labelText = 'RUNNING'
                }

                return (
                  <div
                    key={stName}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      padding: '4px 8px',
                      borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
                      fontSize: '10px',
                      fontFamily: 'var(--font-mono)',
                    }}
                    title={rec?.message || undefined}
                  >
                    <span style={{ color: statusVal === 'COMPLETED' ? '#ffffff' : 'var(--text-secondary)' }}>
                      {stName}
                    </span>
                    <span
                      style={{
                        padding: '1px 5px',
                        borderRadius: '3px',
                        fontSize: '9px',
                        color: statusBadgeColor,
                        background: statusBg,
                        fontWeight: 600,
                      }}
                    >
                      {labelText}
                    </span>
                  </div>
                )
              })}
            </div>
          </section>
        )}

        {/* Layer Visibility Toggles */}
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
            <span>GEOSPATIAL EVIDENCE LAYERS</span>
            <span style={{ fontSize: '10px' }}>7 LAYERS</span>
          </div>

          <div className="layer-toggle-group">
            {/* 1. SAR Detection */}
            <div
              className={`layer-toggle-item ${layers.sar_detection ? 'active' : ''}`}
              onClick={() => onToggleLayer('sar_detection')}
            >
              <div className="layer-info">
                <span
                  className="layer-color-indicator"
                  style={{ background: '#00f2fe', boxShadow: '0 0 6px #00f2fe' }}
                />
                <span className="layer-name">SAR Detection</span>
              </div>
              <label className="toggle-switch" onClick={(e) => e.stopPropagation()}>
                <input
                  type="checkbox"
                  checked={layers.sar_detection}
                  onChange={() => onToggleLayer('sar_detection')}
                />
                <span className="slider" />
              </label>
            </div>

            {/* 2. Temporal Change */}
            <div
              className={`layer-toggle-item ${layers.temporal_change ? 'active' : ''}`}
              onClick={() => onToggleLayer('temporal_change')}
            >
              <div className="layer-info">
                <span
                  className="layer-color-indicator"
                  style={{ background: '#d946ef', boxShadow: '0 0 6px #d946ef' }}
                />
                <span className="layer-name">Temporal Change (T0/T1)</span>
              </div>
              <label className="toggle-switch" onClick={(e) => e.stopPropagation()}>
                <input
                  type="checkbox"
                  checked={layers.temporal_change}
                  onChange={() => onToggleLayer('temporal_change')}
                />
                <span className="slider" />
              </label>
            </div>

            {/* 3. Drift Trajectories */}
            <div
              className={`layer-toggle-item ${layers.drift_trajectory ? 'active' : ''}`}
              onClick={() => onToggleLayer('drift_trajectory')}
            >
              <div className="layer-info">
                <span
                  className="layer-color-indicator"
                  style={{ background: '#f59e0b', boxShadow: '0 0 6px #f59e0b' }}
                />
                <span className="layer-name">Drift Trajectories</span>
              </div>
              <label className="toggle-switch" onClick={(e) => e.stopPropagation()}>
                <input
                  type="checkbox"
                  checked={layers.drift_trajectory}
                  onChange={() => onToggleLayer('drift_trajectory')}
                />
                <span className="slider" />
              </label>
            </div>

            {/* 4. Drift Origin */}
            <div
              className={`layer-toggle-item ${layers.drift_origin ? 'active' : ''}`}
              onClick={() => onToggleLayer('drift_origin')}
            >
              <div className="layer-info">
                <span
                  className="layer-color-indicator"
                  style={{ background: '#ea580c', boxShadow: '0 0 6px #ea580c' }}
                />
                <span className="layer-name">Candidate Origin Region</span>
              </div>
              <label className="toggle-switch" onClick={(e) => e.stopPropagation()}>
                <input
                  type="checkbox"
                  checked={layers.drift_origin}
                  onChange={() => onToggleLayer('drift_origin')}
                />
                <span className="slider" />
              </label>
            </div>

            {/* 5. AIS Tracks / Candidates */}
            <div
              className={`layer-toggle-item ${layers.ais_tracks ? 'active' : ''}`}
              onClick={() => onToggleLayer('ais_tracks')}
            >
              <div className="layer-info">
                <span
                  className="layer-color-indicator"
                  style={{ background: '#3b82f6', boxShadow: '0 0 6px #3b82f6' }}
                />
                <span className="layer-name">AIS Observations / Tracks</span>
              </div>
              <label className="toggle-switch" onClick={(e) => e.stopPropagation()}>
                <input
                  type="checkbox"
                  checked={layers.ais_tracks}
                  onChange={() => onToggleLayer('ais_tracks')}
                />
                <span className="slider" />
              </label>
            </div>

            {/* 6. Fused Evidence */}
            <div
              className={`layer-toggle-item ${layers.fused_evidence ? 'active' : ''}`}
              onClick={() => onToggleLayer('fused_evidence')}
            >
              <div className="layer-info">
                <span
                  className="layer-color-indicator"
                  style={{ background: '#10b981', boxShadow: '0 0 6px #10b981' }}
                />
                <span className="layer-name">Fused Evidence Network</span>
              </div>
              <label className="toggle-switch" onClick={(e) => e.stopPropagation()}>
                <input
                  type="checkbox"
                  checked={layers.fused_evidence}
                  onChange={() => onToggleLayer('fused_evidence')}
                />
                <span className="slider" />
              </label>
            </div>

            {/* 7. Candidate Hypotheses */}
            <div
              className={`layer-toggle-item ${layers.hypotheses ? 'active' : ''}`}
              onClick={() => onToggleLayer('hypotheses')}
            >
              <div className="layer-info">
                <span
                  className="layer-color-indicator"
                  style={{ background: '#a855f7', boxShadow: '0 0 6px #a855f7' }}
                />
                <span className="layer-name">Hypothesis Regions</span>
              </div>
              <label className="toggle-switch" onClick={(e) => e.stopPropagation()}>
                <input
                  type="checkbox"
                  checked={layers.hypotheses}
                  onChange={() => onToggleLayer('hypotheses')}
                />
                <span className="slider" />
              </label>
            </div>
          </div>
        </section>

        {/* Job History Selector */}
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
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <History size={12} />
            <span>RECENT JOBS ({jobList.length})</span>
          </div>

          <div
            style={{
              maxHeight: '130px',
              overflowY: 'auto',
              display: 'flex',
              flexDirection: 'column',
              gap: '4px',
            }}
          >
            {jobList.length === 0 ? (
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                No executed jobs in session
              </div>
            ) : (
              jobList.map((job) => (
                <div
                  key={job.job_id}
                  onClick={() => onSelectJob(job.job_id)}
                  style={{
                    padding: '6px 8px',
                    borderRadius: '4px',
                    background:
                      currentJob?.job_id === job.job_id
                        ? 'rgba(0, 242, 254, 0.15)'
                        : 'rgba(15, 23, 42, 0.5)',
                    border:
                      currentJob?.job_id === job.job_id
                        ? '1px solid var(--cyan-primary)'
                        : '1px solid var(--border-subtle)',
                    cursor: 'pointer',
                    fontSize: '11px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <span style={{ fontFamily: 'var(--font-mono)' }}>
                    {job.job_id.substring(0, 16)}...
                  </span>
                  <span
                    style={{
                      fontSize: '9px',
                      color:
                        job.status === 'SUCCEEDED'
                          ? 'var(--emerald-secondary)'
                          : job.status === 'BLOCKED_PROVENANCE'
                          ? 'var(--rose-secondary)'
                          : 'var(--amber-secondary)',
                    }}
                  >
                    {job.status}
                  </span>
                </div>
              ))
            )}
          </div>
        </section>

        {/* Negative Proof Guard Banner */}
        <div className="notice-box notice-info">
          <ShieldCheck size={16} style={{ flexShrink: 0, marginTop: '2px' }} />
          <div>
            <strong>NEGATIVE-PROOF GUARD</strong>
            <div style={{ marginTop: '2px', fontFamily: 'var(--font-mono)', fontSize: '10px' }}>
              AIS_ABSENCE_IS_NOT_VESSEL_ABSENCE
            </div>
            <div style={{ marginTop: '2px', color: 'var(--text-muted)' }}>
              Telemetry gaps appear as DATA_UNAVAILABLE, never as verified absence.
            </div>
          </div>
        </div>
      </div>
    </aside>
  )
}
