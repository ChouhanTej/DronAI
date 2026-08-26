import React from 'react';
import { ListFilter } from 'lucide-react';

export function EventLog({ events, onClear }) {
  return (
    <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <div className="card-title" style={{ marginBottom: 0 }}>
          <ListFilter size={16} color="var(--accent-blue)" />
          SYSTEM EVENT & ALERT LOG
        </div>
        <button
          onClick={onClear}
          style={{
            fontSize: '0.75rem',
            background: 'transparent',
            border: 'none',
            color: 'var(--text-muted)',
            cursor: 'pointer',
            textDecoration: 'underline'
          }}
        >
          Clear Log
        </button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', maxHeight: '220px', fontSize: '0.8rem', fontFamily: 'var(--font-mono)' }}>
        {events.length === 0 ? (
          <p style={{ color: 'var(--text-dim)', fontStyle: 'italic' }}>No system events logged yet.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {events.slice(0, 100).map((evt, idx) => {
              let badgeStyle = 'var(--text-muted)';
              if (evt.level === 'ANOMALY' || evt.level === 'HIGH') badgeStyle = 'var(--accent-red)';
              else if (evt.level === 'WARNING') badgeStyle = 'var(--accent-amber)';
              else if (evt.level === 'NORMAL') badgeStyle = 'var(--accent-green)';
              else if (evt.level === 'SYSTEM') badgeStyle = 'var(--accent-cyan)';

              return (
                <div key={idx} style={{ display: 'grid', gridTemplateColumns: '70px 90px 1fr', gap: '10px', padding: '4px 0', borderBottom: '1px solid rgba(255,255,255,0.02)' }}>
                  <span style={{ color: 'var(--text-dim)' }}>{evt.time}</span>
                  <span style={{ color: badgeStyle, fontWeight: '700' }}>[{evt.level}]</span>
                  <span style={{ color: 'var(--text-main)' }}>{evt.message}</span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
