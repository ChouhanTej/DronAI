import React, { useState, useEffect, useCallback } from 'react';
import { StatusHeader } from './components/StatusHeader';
import { SystemStatusCard } from './components/SystemStatusCard';
import { EnvironmentCards } from './components/EnvironmentCards';
import { MotionCharts } from './components/MotionCharts';
import { AnomalyGauge } from './components/AnomalyGauge';
import { TelemetryTable } from './components/TelemetryTable';
import { AnomalyExplanation } from './components/AnomalyExplanation';
import { EventLog } from './components/EventLog';
import { HistoricalChart } from './components/HistoricalChart';
import { SystemInfoCard } from './components/SystemInfoCard';

import { wsService } from './services/websocket';

export default function App() {
  const [wsConnected, setWsConnected] = useState(false);
  const [isMonitoring, setIsMonitoring] = useState(true);
  const [demoMode, setDemoMode] = useState(false);

  const [esp32Status, setEsp32Status] = useState('DISCONNECTED');
  const [dht11Status, setDht11Status] = useState('ONLINE');
  const [mpu6050Status, setMpu6050Status] = useState('ONLINE');
  const [mlModelStatus, setMlModelStatus] = useState('LOADED');

  const [currentSample, setCurrentSample] = useState(null);
  const [history, setHistory] = useState([]);
  const [events, setEvents] = useState([
    { time: new Date().toLocaleTimeString(), level: 'SYSTEM', message: 'Dashboard initialized' }
  ]);

  const addEvent = useCallback((level, message) => {
    setEvents(prev => [
      { time: new Date().toLocaleTimeString(), level, message },
      ...prev.slice(0, 99)
    ]);
  }, []);

  const handleMessage = useCallback((payload) => {
    if (!isMonitoring) return;

    if (payload.esp32_status) setEsp32Status(payload.esp32_status);
    if (payload.dht11_status) setDht11Status(payload.dht11_status);
    if (payload.mpu6050_status) setMpu6050Status(payload.mpu6050_status);
    if (payload.ml_model_status) setMlModelStatus(payload.ml_model_status);
    if (payload.demo_mode !== undefined) setDemoMode(payload.demo_mode);

    if (payload.data) {
      const data = payload.data;
      const point = {
        ...data,
        timestamp: payload.timestamp
      };

      setCurrentSample(point);
      setHistory(prev => [...prev.slice(-999), point]);

      // Log status changes
      if (data.status === 'HIGH ANOMALY') {
        addEvent('ANOMALY', `High Anomaly Risk Score: ${(data.anomaly_risk_score * 100).toFixed(1)}%`);
      } else if (data.status === 'WARNING') {
        addEvent('WARNING', `Motion / Environmental Warning: ${(data.anomaly_risk_score * 100).toFixed(1)}%`);
      }
    }
  }, [isMonitoring, addEvent]);

  useEffect(() => {
    wsService.connect(handleMessage, (connected, msg) => {
      setWsConnected(connected);
      if (connected) {
        addEvent('SYSTEM', 'WebSocket connection established with backend');
      } else {
        addEvent('SYSTEM', `WebSocket status: ${msg}`);
      }
    });

    return () => {
      wsService.disconnect();
    };
  }, [handleMessage, addEvent]);

  const toggleMonitoring = () => {
    setIsMonitoring(prev => {
      const next = !prev;
      addEvent('SYSTEM', next ? 'Monitoring started' : 'Monitoring paused');
      return next;
    });
  };

  const toggleDemo = async () => {
    const nextDemo = !demoMode;
    try {
      await fetch('/api/demo-mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: nextDemo })
      });
      setDemoMode(nextDemo);
      addEvent('SYSTEM', nextDemo ? 'Demo Mode enabled (Replaying CSV)' : 'Live Serial Mode enabled');
    } catch (e) {
      console.error('Failed to toggle demo mode', e);
    }
  };

  const clearEvents = () => {
    setEvents([]);
  };

  const status = currentSample ? currentSample.status : 'NORMAL';
  const riskScore = currentSample ? currentSample.anomaly_risk_score : 0.0;
  const timestamp = currentSample ? currentSample.timestamp : null;
  const unusualParams = currentSample ? currentSample.most_unusual_parameters : [];

  return (
    <div className="dashboard-container">
      {/* Header */}
      <StatusHeader
        wsConnected={wsConnected}
        isMonitoring={isMonitoring}
        onToggleMonitoring={toggleMonitoring}
        demoMode={demoMode}
        onToggleDemo={toggleDemo}
        onClearEvents={clearEvents}
      />

      {/* Top Grid: Status Card & Environment */}
      <div className="grid-top">
        <SystemStatusCard
          status={status}
          riskScore={riskScore}
          timestamp={timestamp}
          esp32Status={esp32Status}
          sensorsOnline={dht11Status === 'ONLINE' && mpu6050Status === 'ONLINE'}
        />
        <EnvironmentCards
          temperature={currentSample?.temperature_c}
          humidity={currentSample?.humidity_percent}
          history={history}
        />
      </div>

      {/* Main Grid: Motion Charts & Anomaly Gauge */}
      <div className="grid-main">
        <MotionCharts history={history} />
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <AnomalyGauge riskScore={riskScore} status={status} />
          <AnomalyExplanation unusualParams={unusualParams} />
        </div>
      </div>

      {/* Historical Anomaly Chart */}
      <HistoricalChart history={history} />

      {/* Bottom Grid: Telemetry Table, Event Log & System Info */}
      <div className="grid-bottom">
        <TelemetryTable sample={currentSample} />
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <EventLog events={events} onClear={clearEvents} />
          <SystemInfoCard
            esp32Status={esp32Status}
            dht11Status={dht11Status}
            mpu6050Status={mpu6050Status}
            mlModelStatus={mlModelStatus}
          />
        </div>
      </div>
    </div>
  );
}
