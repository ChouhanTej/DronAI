# Extreme Conditions Sensing & Failure Risk Monitoring Dashboard

A modern, professional real-time web dashboard for the **Extreme Conditions Sensing & Failure Risk Monitoring** subsystem of the drone platform.

---

## 1. System Architecture

```text
ESP32 Controller (DHT11 + MPU6050)
         │  (115200 Baud CSV Serial Stream)
         ▼
Python FastAPI Backend (dashboard/backend/)
         │  (Rolling Window Buffer)
         ▼
Existing Feature Engineering Pipeline (ml/feature_extraction.py)
         │  (25 Features: 3D Magnitudes, Rolling RMS, std, min, max)
         ▼
Existing Isolation Forest Model (ml/model/isolation_forest.joblib)
         │  (Calibrated Anomaly Risk Score 0.0 -> 1.0 & Feature Deviation Explainability)
         ▼
FastAPI WebSocket Server (ws://localhost:8000/ws/telemetry)
         │
         ▼
React + Vite Dashboard (dashboard/frontend/)
```

---

## 2. Quick Start Guide (macOS)

### Step 1: Install Backend Python Dependencies
From the `extreme_conditions/dashboard/backend` directory:

```bash
cd extreme_conditions/dashboard/backend
pip3 install -r requirements.txt
```

### Step 2: Start the FastAPI Backend Server
Run:
```bash
python3 main.py
```
*(The backend server will start on `http://localhost:8000` and automatically connect to your ESP32 serial port `/dev/cu.SLAB_USBtoUART` or auto-detected device).*

### Step 3: Install Frontend Dependencies & Start React Server
Open a second terminal window and navigate to `extreme_conditions/dashboard/frontend`:

```bash
cd extreme_conditions/dashboard/frontend
npm install
npm run dev
```

### Step 4: Open Dashboard in Browser
Open your web browser and navigate to:
👉 **`http://localhost:5173`**

---

## 3. Dashboard Features & Layout

1. **System Status Card:** Large status state (`NORMAL`, `WARNING`, `HIGH ANOMALY`), Anomaly Risk Score %, ESP32 connection badge (`CONNECTED`/`DISCONNECTED`), and sensor status (`2/2 ONLINE`).
2. **Environment Section:** Live Temperature (°C) & Humidity (%) cards with real-time trend sparklines.
3. **Motion / Vibration Section:** Real-time scrolling charts for Acceleration Magnitude ($g$) & RMS, and Gyroscope Magnitude ($\text{dps}$) & RMS (showing last 60–120 seconds).
4. **Radial Anomaly Risk Gauge:** Prominent Anomaly Risk Score gauge (0–100%) with prototype threshold bands ($0-30\%$ NORMAL, $30-60\%$ WARNING, $60-100\%$ HIGH ANOMALY).
5. **Live Telemetry Table:** Auto-updating table listing all 8 physical sensor channels with live values and status badges.
6. **Feature Deviation Explainability Card:** *"MOST UNUSUAL PARAMETERS"* ranking the top 3 deviating features against baseline parameters ($\mu, \sigma$).
7. **System Event & Alert Log:** Real-time scrolling event table with event level filtering and a **CLEAR EVENTS** button.
8. **Historical Timeline Chart:** Anomaly Risk vs Time chart with range filter buttons (`Last 1m`, `Last 5m`, `Last 15m`, `Session`).
9. **Hardware & ML System Details:** Hardware status, ML algorithm details (`Isolation Forest`), artifact status, and sampling frequency (~1 Hz).

---

## 4. Live Mode vs. Demo Mode

- **Live Hardware Mode (Default):** Connects directly to the ESP32 serial stream on `/dev/cu.SLAB_USBtoUART`. Shows real hardware telemetry.
- **Demo Mode:** Click **ENABLE DEMO MODE** in the top header. Replays samples from the previously recorded raw CSV dataset (`sensor_data_2026-08-26_110040.csv`). When active, a prominent `DEMO MODE (REPLAYING CSV DATASET)` badge is displayed to ensure complete transparency.

---

## 5. Troubleshooting & Safety Notes

- **ESP32 Disconnected:** If the ESP32 USB cable is unplugged, the dashboard displays `ESP32 DISCONNECTED` and stops telemetry updates without displaying fake values.
- **Port Resource Busy:** Make sure Arduino IDE's Serial Monitor is closed before running the dashboard backend.
- **Honesty & Safety Disclaimer:** The Anomaly Risk Score represents statistical deviation from normal baseline telemetry. It is an anomaly-monitoring prototype metric, NOT a scientifically calibrated failure probability.
