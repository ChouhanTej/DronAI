import React from 'react';
import { Thermometer, Droplets } from 'lucide-react';
import { ResponsiveContainer, AreaChart, Area } from 'recharts';

export function EnvironmentCards({ temperature, humidity, history }) {
  return (
    <>
      {/* Temperature Card */}
      <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
        <div>
          <div className="card-title">
            <Thermometer size={16} color="#d9534f" />
            TEMPERATURE (DHT11)
          </div>
          <div className="metric-value">
            {temperature != null ? temperature.toFixed(1) : '--'}
            <span className="unit">°C</span>
          </div>
        </div>

        <div style={{ height: '50px', marginTop: '12px' }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={history.slice(-20)}>
              <defs>
                <linearGradient id="tempGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#d9534f" stopOpacity={0.4}/>
                  <stop offset="95%" stopColor="#d9534f" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <Area type="monotone" dataKey="temperature_c" stroke="#d9534f" strokeWidth={2} fillOpacity={1} fill="url(#tempGrad)" isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Humidity Card */}
      <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
        <div>
          <div className="card-title">
            <Droplets size={16} color="#0275d8" />
            HUMIDITY (DHT11)
          </div>
          <div className="metric-value">
            {humidity != null ? humidity.toFixed(1) : '--'}
            <span className="unit">%</span>
          </div>
        </div>

        <div style={{ height: '50px', marginTop: '12px' }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={history.slice(-20)}>
              <defs>
                <linearGradient id="humGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#0275d8" stopOpacity={0.4}/>
                  <stop offset="95%" stopColor="#0275d8" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <Area type="monotone" dataKey="humidity_percent" stroke="#0275d8" strokeWidth={2} fillOpacity={1} fill="url(#humGrad)" isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </>
  );
}
