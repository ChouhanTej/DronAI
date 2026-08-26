import React from 'react';
import { Info, Server, Cpu, Activity, Database } from 'lucide-react';

export function SystemInfoCard({ esp32Status, dht11Status, mpu6050Status, mlModelStatus }) {
  return (
    <div className="glass-card">
      <div className="card-title">
        <Info size={16} color="var(--accent-blue)" />
        HARDWARE & ML SYSTEM DETAILS
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '14px', fontSize: '0.85rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Cpu size={14} color="var(--text-muted)" />
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>ESP32 HARDWARE</div>
            <div style={{ fontWeight: '700', color: esp32Status === 'CONNECTED' ? 'var(--accent-green)' : 'var(--accent-red)' }}>
              {esp32Status}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Activity size={14} color="var(--text-muted)" />
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>DHT11 SENSOR</div>
            <div style={{ fontWeight: '700', color: dht11Status === 'ONLINE' ? 'var(--accent-green)' : 'var(--accent-red)' }}>
              {dht11Status}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Activity size={14} color="var(--text-muted)" />
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>MPU6050 SENSOR</div>
            <div style={{ fontWeight: '700', color: mpu6050Status === 'ONLINE' ? 'var(--accent-green)' : 'var(--accent-red)' }}>
              {mpu6050Status}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Database size={14} color="var(--text-muted)" />
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>ML ALGORITHM</div>
            <div style={{ fontWeight: '700', color: 'var(--accent-cyan)' }}>
              ISOLATION FOREST
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Server size={14} color="var(--text-muted)" />
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>MODEL ARTIFACT</div>
            <div style={{ fontWeight: '700', color: mlModelStatus === 'LOADED' ? 'var(--accent-green)' : 'var(--accent-red)' }}>
              {mlModelStatus}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Activity size={14} color="var(--text-muted)" />
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>SAMPLING FREQUENCY</div>
            <div style={{ fontWeight: '700', color: 'var(--text-main)' }}>
              ~1 Hz (1000 ms)
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
