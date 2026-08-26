import React from 'react';
import { AlertCircle } from 'lucide-react';

export function AnomalyGauge({ riskScore, status }) {
  const pct = Math.min(100, Math.max(0, riskScore * 100));

  let gaugeColor = 'var(--accent-green)';
  if (pct >= 60) {
    gaugeColor = 'var(--accent-red)';
  } else if (pct >= 30) {
    gaugeColor = 'var(--accent-amber)';
  }

  return (
    <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center' }}>
      <div className="card-title" style={{ alignSelf: 'flex-start' }}>
        <AlertCircle size={16} color={gaugeColor} />
        ANOMALY RISK SCORE (ISOLATION FOREST)
      </div>

      <div style={{ position: 'relative', margin: '20px 0 10px 0', width: '180px', height: '180px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        {/* Circular Progress Arc */}
        <svg width="180" height="180" viewBox="0 0 180 180">
          <circle cx="90" cy="90" r="75" fill="none" stroke="var(--bg-card-border)" strokeWidth="12" />
          <circle
            cx="90"
            cy="90"
            r="75"
            fill="none"
            stroke={gaugeColor}
            strokeWidth="12"
            strokeDasharray={471}
            strokeDashoffset={471 - (471 * pct) / 100}
            strokeLinecap="round"
            transform="rotate(-90 90 90)"
            style={{ transition: 'stroke-dashoffset 0.5s ease, stroke 0.5s ease' }}
          />
        </svg>

        <div style={{ position: 'absolute', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <span style={{ fontSize: '2.6rem', fontWeight: '900', fontFamily: 'var(--font-mono)', color: gaugeColor }}>
            {pct.toFixed(0)}%
          </span>
          <span style={{ fontSize: '0.75rem', fontWeight: '700', color: 'var(--text-muted)', letterSpacing: '0.05em' }}>
            {status}
          </span>
        </div>
      </div>

      {/* Threshold Bands Bar */}
      <div style={{ width: '100%', marginTop: '10px' }}>
        <div style={{ height: '6px', background: 'var(--bg-card-border)', borderRadius: '3px', overflow: 'hidden', display: 'flex' }}>
          <div style={{ width: '30%', background: 'var(--accent-green)', opacity: 0.6 }} />
          <div style={{ width: '30%', background: 'var(--accent-amber)', opacity: 0.6 }} />
          <div style={{ width: '40%', background: 'var(--accent-red)', opacity: 0.6 }} />
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: 'var(--text-dim)', marginTop: '4px', fontFamily: 'var(--font-mono)' }}>
          <span>0% NORMAL</span>
          <span>30% WARNING</span>
          <span>60% HIGH</span>
          <span>100%</span>
        </div>
      </div>

      <p style={{ fontSize: '0.7rem', color: 'var(--text-dim)', marginTop: '12px', textAlign: 'center' }}>
        * Prototype risk score threshold based on baseline telemetry isolation depth.
      </p>
    </div>
  );
}
