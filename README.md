# DronAI — Smart Drone Detection & Extreme Conditions Failure Risk Monitoring System

**DronAI** is an AI-powered defense & monitoring platform featuring real-time YOLOv8 drone detection, pan/tilt tracking, environmental sensing, and Isolation Forest anomaly prediction.

---

## 🏗️ Repository Architecture

```text
DronAI/
├── DRONA/                                  # Drone Detection & Camera Pan/Tilt Subsystem
│   ├── src/                                # Detection, tracking, & servo control scripts
│   └── ...                                 # Video models & dataset configs
│
├── extreme_conditions/                     # Environmental & Motion Sensing Subsystem
│   ├── firmware/                           # ESP32 C++ Sensor Logger Firmware (DHT11 + MPU6050)
│   ├── tools/                              # Serial Data Logger CLI tool
│   ├── data/
│   │   ├── raw/                            # Baseline sensor telemetry CSVs
│   │   ├── processed/                      # 25-feature processed sensor dataset
│   │   └── reports/                        # Data inspection reports & anomaly plots
│   ├── ml/
│   │   ├── model/                          # Trained Isolation Forest model & config
│   │   ├── train_anomaly_model.py          # Model training pipeline
│   │   ├── predict_anomaly.py              # Anomaly risk & explainability module
│   │   ├── live_anomaly_monitor.py         # Terminal dashboard monitor
│   │   └── README.md
│   └── dashboard/                          # Real-Time Web Dashboard Subsystem
│       ├── backend/                        # FastAPI WebSocket & REST API server
│       ├── frontend/                       # React + Vite Dark Industrial Engineering UI
│       └── README.md
│
└── README.md
```

---

## ⚡ Quick Start: Extreme Conditions Dashboard

### 1. Backend Server (FastAPI + WebSockets)
```bash
python3 extreme_conditions/dashboard/backend/main.py
```
*(Runs on `http://localhost:8000`)*

### 2. Frontend Web Interface (React + Vite)
```bash
cd extreme_conditions/dashboard/frontend
npm install
npm run dev
```
*(Runs on `http://localhost:5173`)*

👉 **Browser Dashboard URL:** `http://localhost:5173/`

---

## 🛡️ Key Features

1. **YOLOv8 Target Detection:** Real-time drone identification with pan/tilt hardware tracking (`DRONA/`).
2. **Multi-Sensor Telemetry:** High-frequency logging of temperature, humidity, 3D acceleration, and 3D gyroscope angular velocity (`extreme_conditions/firmware/`).
3. **Isolation Forest Anomaly Engine:** Unsupervised anomaly detection model trained on baseline telemetry with feature deviation explainability (`extreme_conditions/ml/`).
4. **Real-Time Web Dashboard:** Dark engineering web dashboard visualization of sensor metrics, radial anomaly risk score (0–100%), event logs, and historical timeline (`extreme_conditions/dashboard/`).
