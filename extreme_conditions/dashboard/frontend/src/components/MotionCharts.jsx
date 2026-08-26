import React from 'react';
import { Gauge, Compass } from 'lucide-react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip } from 'recharts';

export function MotionCharts({ history }) {
  const chartData = history.slice(-60); // Show last 60-120 seconds of data

  const latestAccelMag = chartData.length > 0 ? (chartData[chartData.length - 1].accel_mag_g || 0).toFixed(2) : '--';
  const latestAccelRms = chartData.length > 0 ? (chartData[chartData.length - 1].accel_mag_rms || 0).toFixed(2) : '--';
  const latestGyroMag = chartData.length > 0 ? (chartData[chartData.length - 1].gyro_mag_dps || 0).toFixed(2) : '--';
  const latestGyroRms = chartData.length > 0 ? (chartData[chartData.length - 1].gyro_mag_rms || 0).toFixed(2) : '--';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Acceleration Chart */}
      <div className="glass-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <div className="card-title" style={{ marginBottom: 0 }}>
            <Gauge size={16} color="var(--accent-amber)" />
            ACCELERATION & MOTION VIBRATION (MPU6050)
          </div>
          <div style={{ display: 'flex', gap: '16px', fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>
            <div>MAG: <span style={{ color: 'var(--accent-amber)', fontWeight: '700' }}>{latestAccelMag} g</span></div>
            <div>RMS: <span style={{ color: '#fff', fontWeight: '700' }}>{latestAccelRms} g</span></div>
          </div>
        </div>

        <div style={{ height: '180px' }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <XAxis dataKey="timestamp" stroke="var(--text-dim)" fontSize={10} tickLine={false} />
              <YAxis stroke="var(--text-dim)" fontSize={10} domain={['auto', 'auto']} tickLine={false} />
              <Tooltip contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--bg-card-border)', color: '#fff' }} />
              <Line type="monotone" dataKey="accel_mag_g" stroke="var(--accent-amber)" name="||Accel|| (g)" strokeWidth={2} dot={false} isAnimationActive={false} />
              <Line type="monotone" dataKey="accel_mag_rms" stroke="#ffffff" name="Accel RMS (g)" strokeDasharray="3 3" strokeWidth={1.5} dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Gyroscope Chart */}
      <div className="glass-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <div className="card-title" style={{ marginBottom: 0 }}>
            <Compass size={16} color="var(--accent-cyan)" />
            GYROSCOPE ANGULAR VELOCITY (MPU6050)
          </div>
          <div style={{ display: 'flex', gap: '16px', fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>
            <div>MAG: <span style={{ color: 'var(--accent-cyan)', fontWeight: '700' }}>{latestGyroMag} dps</span></div>
            <div>RMS: <span style={{ color: '#fff', fontWeight: '700' }}>{latestGyroRms} dps</span></div>
          </div>
        </div>

        <div style={{ height: '180px' }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <XAxis dataKey="timestamp" stroke="var(--text-dim)" fontSize={10} tickLine={false} />
              <YAxis stroke="var(--text-dim)" fontSize={10} domain={['auto', 'auto']} tickLine={false} />
              <Tooltip contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--bg-card-border)', color: '#fff' }} />
              <Line type="monotone" dataKey="gyro_mag_dps" stroke="var(--accent-cyan)" name="||Gyro|| (dps)" strokeWidth={2} dot={false} isAnimationActive={false} />
              <Line type="monotone" dataKey="gyro_mag_rms" stroke="#ffffff" name="Gyro RMS (dps)" strokeDasharray="3 3" strokeWidth={1.5} dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
