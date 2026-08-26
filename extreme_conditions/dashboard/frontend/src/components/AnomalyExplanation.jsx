import React from 'react';
import { HelpCircle } from 'lucide-react';

export function AnomalyExplanation({ unusualParams }) {
  const params = unusualParams || [];

  return (
    <div className="glass-card">
      <div className="card-title">
        <HelpCircle size={16} color="var(--accent-amber)" />
        MOST UNUSUAL PARAMETERS (FEATURE EXPLAINABILITY)
      </div>

      {params.length === 0 ? (
        <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
          All sensor channels operating within normal baseline limits.
        </p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {params.map((item, idx) => (
            <div
              key={idx}
              style={{
                background: 'rgba(255,255,255,0.02)',
                border: '1px solid var(--bg-card-border)',
                borderRadius: '8px',
                padding: '12px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}
            >
              <div>
                <div style={{ fontSize: '0.9rem', fontWeight: '700', color: '#fff' }}>
                  {idx + 1}. {item.parameter}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--accent-amber)', marginTop: '2px' }}>
                  {item.deviation_level} (+{item.z_score} std dev)
                </div>
              </div>

              <div style={{ textAlign: 'right', fontFamily: 'var(--font-mono)' }}>
                <div style={{ fontSize: '0.9rem', fontWeight: '700', color: 'var(--accent-cyan)' }}>
                  Current: {item.current_value}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                  Baseline Mean: {item.baseline_mean}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <p style={{ fontSize: '0.7rem', color: 'var(--text-dim)', marginTop: '12px' }}>
        * Highlights potential contributing conditions relative to static baseline distribution without claiming causal hardware failures.
      </p>
    </div>
  );
}
