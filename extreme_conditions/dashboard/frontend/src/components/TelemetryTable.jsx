import React from 'react';
import { Table } from 'lucide-react';

export function TelemetryTable({ sample }) {
  if (!sample) {
    return (
      <div className="glass-card">
        <div className="card-title"><Table size={16} /> LIVE TELEMETRY TABLE</div>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Waiting for sensor telemetry stream...</p>
      </div>
    );
  }

  const rows = [
    { label: 'Temperature', val: sample.temperature_c != null ? sample.temperature_c.toFixed(2) : '--', unit: '°C', status: 'NORMAL' },
    { label: 'Humidity', val: sample.humidity_percent != null ? sample.humidity_percent.toFixed(2) : '--', unit: '%', status: 'NORMAL' },
    { label: 'Acceleration X', val: sample.accel_x_g != null ? sample.accel_x_g.toFixed(2) : '--', unit: 'g', status: 'NORMAL' },
    { label: 'Acceleration Y', val: sample.accel_y_g != null ? sample.accel_y_g.toFixed(2) : '--', unit: 'g', status: 'NORMAL' },
    { label: 'Acceleration Z', val: sample.accel_z_g != null ? sample.accel_z_g.toFixed(2) : '--', unit: 'g', status: 'NORMAL' },
    { label: 'Gyroscope X', val: sample.gyro_x_dps != null ? sample.gyro_x_dps.toFixed(2) : '--', unit: 'dps', status: 'NORMAL' },
    { label: 'Gyroscope Y', val: sample.gyro_y_dps != null ? sample.gyro_y_dps.toFixed(2) : '--', unit: 'dps', status: 'NORMAL' },
    { label: 'Gyroscope Z', val: sample.gyro_z_dps != null ? sample.gyro_z_dps.toFixed(2) : '--', unit: 'dps', status: 'NORMAL' }
  ];

  return (
    <div className="glass-card">
      <div className="card-title">
        <Table size={16} color="var(--accent-cyan)" />
        LIVE TELEMETRY CHANNELS
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--bg-card-border)', textAlign: 'left', color: 'var(--text-muted)' }}>
              <th style={{ padding: '8px' }}>Parameter</th>
              <th style={{ padding: '8px' }}>Value</th>
              <th style={{ padding: '8px' }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => (
              <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                <td style={{ padding: '8px', color: 'var(--text-main)', fontWeight: '500' }}>{row.label}</td>
                <td style={{ padding: '8px', fontFamily: 'var(--font-mono)', fontWeight: '600' }}>
                  {row.val} <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{row.unit}</span>
                </td>
                <td style={{ padding: '8px' }}>
                  <span className="badge badge-normal" style={{ fontSize: '0.65rem', padding: '2px 8px' }}>
                    {row.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
