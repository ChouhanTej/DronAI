import React from 'react';
import { Activity, Play, Square, RefreshCw, Radio, AlertTriangle } from 'lucide-react';

export function StatusHeader({ wsConnected, isMonitoring, onToggleMonitoring, demoMode, onToggleDemo, onClearEvents }) {
  return (
    <header className="glass-card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Activity size={24} color="#00f2fe" />
          <h1 style={{ fontSize: '1.4rem', fontWeight: '800', letterSpacing: '0.05em', color: '#fff' }}>
            EXTREME CONDITIONS <span style={{ color: '#00f2fe' }}>SYSTEM HEALTH MONITOR</span>
          </h1>
        </div>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '4px' }}>
          Real-Time Environmental & Motion Anomaly Detection Subsystem
        </p>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
        {/* Demo Mode Badge */}
        {demoMode && (
          <span className="badge badge-warning" style={{ padding: '6px 12px', fontSize: '0.8rem' }}>
            <AlertTriangle size={14} /> DEMO MODE (REPLAYING CSV DATASET)
          </span>
        )}

        {/* WebSocket Connection Status */}
        <span className={`badge ${wsConnected ? 'badge-normal' : 'badge-offline'}`}>
          <Radio size={12} /> {wsConnected ? 'LIVE WS CONNECTED' : 'WS OFFLINE'}
        </span>

        {/* Start / Stop Monitoring Button */}
        <button
          onClick={onToggleMonitoring}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '8px 16px',
            borderRadius: '8px',
            border: 'none',
            fontWeight: '600',
            cursor: 'pointer',
            background: isMonitoring ? 'var(--accent-red)' : 'var(--accent-cyan)',
            color: '#000'
          }}
        >
          {isMonitoring ? <Square size={14} /> : <Play size={14} />}
          {isMonitoring ? 'STOP MONITORING' : 'START MONITORING'}
        </button>

        {/* Toggle Demo Mode Button */}
        <button
          onClick={onToggleDemo}
          style={{
            padding: '8px 14px',
            borderRadius: '8px',
            border: '1px solid var(--bg-card-border)',
            background: 'var(--bg-card-hover)',
            color: 'var(--text-main)',
            fontWeight: '600',
            fontSize: '0.85rem',
            cursor: 'pointer'
          }}
        >
          {demoMode ? 'SWITCH TO LIVE ESP32' : 'ENABLE DEMO MODE'}
        </button>

        {/* Clear Events Button */}
        <button
          onClick={onClearEvents}
          style={{
            padding: '8px 14px',
            borderRadius: '8px',
            border: '1px solid var(--bg-card-border)',
            background: 'transparent',
            color: 'var(--text-muted)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            fontSize: '0.85rem'
          }}
        >
          <RefreshCw size={12} /> CLEAR EVENTS
        </button>
      </div>
    </header>
  );
}
