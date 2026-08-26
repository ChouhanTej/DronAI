import React, { useState } from 'react';
import { TrendingUp } from 'lucide-react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip } from 'recharts';

export function HistoricalChart({ history }) {
  const [range, setRange] = useState('5m');

  let sampleLimit = 60; // default 1 min (~60 samples)
  if (range === '5m') sampleLimit = 300;
  else if (range === '15m') sampleLimit = 900;
  else if (range === 'session') sampleLimit = history.length;

  const data = history.slice(-sampleLimit).map(item => ({
    timestamp: item.timestamp,
    risk: (item.anomaly_risk_score || 0) * 100
  }));

  return (
    <div className="glass-card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
        <div className="card-title" style={{ marginBottom: 0 }}>
          <TrendingUp size={16} color="var(--accent-cyan)" />
          ANOMALY RISK VS TIME (HISTORICAL TIMELINE)
        </div>

        {/* Range Buttons */}
        <div style={{ display: 'flex', gap: '6px' }}>
          {['1m', '5m', '15m', 'session'].map(r => (
            <button
              key={r}
              onClick={() => setRange(r)}
              style={{
                fontSize: '0.75rem',
                padding: '4px 10px',
                borderRadius: '6px',
                border: '1px solid var(--bg-card-border)',
                background: range === r ? 'var(--accent-cyan)' : 'var(--bg-card-hover)',
                color: range === r ? '#000' : 'var(--text-muted)',
                fontWeight: '600',
                cursor: 'pointer',
                textTransform: 'uppercase'
              }}
            >
              {r === 'session' ? 'Session' : `Last ${r}`}
            </button>
          ))}
        </div>
      </div>

      <div style={{ height: '220px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <defs>
              <linearGradient id="riskGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#00f2fe" stopOpacity={0.4}/>
                <stop offset="95%" stopColor="#00f2fe" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <XAxis dataKey="timestamp" stroke="var(--text-dim)" fontSize={10} tickLine={false} />
            <YAxis stroke="var(--text-dim)" fontSize={10} domain={[0, 100]} unit="%" tickLine={false} />
            <Tooltip contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--bg-card-border)', color: '#fff' }} />
            <Area type="monotone" dataKey="risk" stroke="#00f2fe" strokeWidth={2} fillOpacity={1} fill="url(#riskGrad)" isAnimationActive={false} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
