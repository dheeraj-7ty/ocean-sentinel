import React from 'react'

export const Legend: React.FC = () => {
  return (
    <div
      style={{
        position: 'absolute',
        bottom: '16px',
        right: '16px',
        background: 'rgba(9, 14, 26, 0.85)',
        backdropFilter: 'var(--glass-blur)',
        border: '1px solid var(--border-subtle)',
        borderRadius: '8px',
        padding: '10px 14px',
        zIndex: 10,
        fontSize: '11px',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px',
        boxShadow: '0 4px 16px rgba(0,0,0,0.3)',
      }}
    >
      <div
        style={{
          fontWeight: 600,
          textTransform: 'uppercase',
          fontSize: '10px',
          color: 'var(--text-muted)',
          letterSpacing: '0.4px',
          marginBottom: '2px',
        }}
      >
        GEOSPATIAL SYMBOLOGY
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span
          style={{
            width: '12px',
            height: '12px',
            borderRadius: '2px',
            border: '2px solid #00f2fe',
            background: 'rgba(0, 242, 254, 0.2)',
          }}
        />
        <span>SAR Detection Polygon (Observed)</span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span
          style={{
            width: '12px',
            height: '12px',
            borderRadius: '2px',
            border: '2px solid #d946ef',
            background: 'rgba(217, 70, 239, 0.2)',
          }}
        />
        <span>Temporal Change (Persistent/New)</span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span
          style={{
            width: '14px',
            height: '3px',
            background: '#f59e0b',
            borderRadius: '1px',
          }}
        />
        <span>Backward Drift Trajectory (Modelled)</span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span
          style={{
            width: '12px',
            height: '12px',
            borderRadius: '2px',
            border: '2px dashed #ea580c',
            background: 'rgba(234, 88, 12, 0.15)',
          }}
        />
        <span>Candidate Origin Region (Hypothesis)</span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span
          style={{
            width: '10px',
            height: '10px',
            borderRadius: '50%',
            background: '#10b981',
            boxShadow: '0 0 6px #10b981',
          }}
        />
        <span>Candidate Vessel (Supported / Corroborated)</span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span
          style={{
            width: '10px',
            height: '10px',
            borderRadius: '50%',
            background: '#ef4444',
            boxShadow: '0 0 6px #ef4444',
          }}
        />
        <span>Candidate Vessel (Conflicting Evidence)</span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span
          style={{
            width: '10px',
            height: '10px',
            borderRadius: '50%',
            background: '#94a3b8',
          }}
        />
        <span>Telemetry Gap (DATA_UNAVAILABLE)</span>
      </div>
    </div>
  )
}
