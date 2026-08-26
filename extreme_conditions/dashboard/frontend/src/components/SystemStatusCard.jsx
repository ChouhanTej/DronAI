import React from 'react';
import { ShieldCheck, ShieldAlert, Cpu, HardDrive } from 'lucide-react';

export function SystemStatusCard({ status, riskScore, timestamp, esp32Status, sensorsOnline }) {
  const isNormal = status === 'NORMAL';
  const isWarning = status === 'WARNING';
  const isHigh = status === 'HIGH ANOMALY';

  const badgeClass = isNormal ? 'badge-normal' : isWarning ? 'badge-warning' : 'badge-danger';
  const statusColor = isNormal ? 'var(--accent-green)' : isWarning ? 'var(--accent-amber)' : 'var(--accent-red)';

  return (
    <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
      <div>
        <div className="card-title">
          {isNormal ? <ShieldCheck size={16} color="var(--accent-green)" /> : <ShieldAlert size={16} color={statusColor} />}
          SYSTEM STATUS
        </div>

        <div style={{ display: 'flex', alignItems: 'baseline', gap: '16px', margin: '12px 0' }}>
          <div style={{ fontSize: '2.4rem', fontWeight: '900', color: statusColor, letterSpacing: '0.04em' }}>
            {status}
          </div>
          <span className={`badge ${badgeClass}`} style={{ fontSize: '0.9rem', padding: '6px 14px' }}>
            {status}
          </span>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginTop: '16px', paddingTop: '16px', borderTop: '1px solid var(--bg-card-border)' }}>
        <div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>ANOMALY RISK</div>
          <div style={{ fontSize: '1.4rem', fontWeight: '700', fontFamily: 'var(--font-mono)', color: statusColor }}>
            {(riskScore * 100).toFixed(1)}%
          </div>
        </div>

        <div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>ESP32 HARDWARE</div>
          <div style={{ fontSize: '0.9rem', fontWeight: '700', marginTop: '4px', color: esp32Status === 'CONNECTED' ? 'var(--accent-green)' : 'var(--accent-red)' }}>
            <Cpu size={12} style={{ display: 'inline', marginRight: '4px' }} />
            {esp32Status}
          </div>
        </div>

        <div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>SENSORS STATUS</div>
          <div style={{ fontSize: '0.9rem', fontWeight: '700', marginTop: '4px', color: sensorsOnline ? 'var(--accent-green)' : 'var(--text-dim)' }}>
            <HardDrive size={12} style={{ display: 'inline', marginRight: '4px' }} />
            {sensorsOnline ? '2 / 2 ONLINE' : 'OFFLINE'}
          </div>
        </div>

        <div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>LAST UPDATE</div>
          <div style={{ fontSize: '0.9rem', fontFamily: 'var(--font-mono)', color: 'var(--text-main)', marginTop: '4px' }}>
            {timestamp || '--:--:--'}
          </div>
        </div>
      </div>
    </div>
  );
}
