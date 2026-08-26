# Extreme Conditions Failure Prediction — Machine Learning Pipeline & Roadmap

This directory contains the machine learning modules for the Extreme Conditions Failure Prediction system of the drone detection platform.

---

## 1. Project 5-Stage Roadmap

```text
[ STAGE 1 ] Sensor Data Collection (ESP32 + DHT11 + MPU6050) — COMPLETED
     │
     ▼
[ STAGE 2 ] Dataset Inspection & Feature Engineering — COMPLETED
     │
     ▼
[ STAGE 3 ] Unsupervised Anomaly Detection (Isolation Forest) — COMPLETED
     │
     ▼
[ STAGE 4 ] Controlled-Condition & Stress Data Collection — NEXT STAGE
     │
     ▼
[ STAGE 5 ] Component-Specific Supervised Failure Prediction — FUTURE STAGE
```

---

## 2. Stage Breakdown & Requirements

### STAGE 1: Sensor Data Collection (COMPLETED)
- Hardware logger firmware (`sensor_logger.ino`) on ESP32.
- Serial logger (`serial_logger.py`) collecting 9-channel raw CSV telemetry.

### STAGE 2: Dataset Inspection & Feature Engineering (COMPLETED)
- Quality audit of 221 baseline samples.
- Feature extraction (`feature_extraction.py`): 3D vector magnitudes, rolling RMS, std, min, max, mean.
- Processed dataset: `extreme_conditions/data/processed/processed_sensor_data.csv`.

### STAGE 3: Unsupervised Anomaly Detection (COMPLETED)
- Model Architecture: `sklearn.ensemble.IsolationForest`.
- Feature Selection: 18 physical & rolling telemetry features (excluding `timestamp_ms`).
- Artifacts: `isolation_forest.joblib` and `feature_config.json` saved in `extreme_conditions/ml/model/`.
- Score Calibration: Raw decision score mapped to calibrated **Anomaly Risk Score** ($0.0 \rightarrow 1.0$).
- Feature Deviation Explainability: Ranks top 3 unusual features by normalized z-score deviation ($|(x - \mu)/\sigma|$).
- Live Monitor: `live_anomaly_monitor.py` displaying live dashboard over Serial or CSV stream.

### STAGE 4: Controlled-Condition & Stress Data Collection (NEXT STAGE)
Before moving to supervised failure prediction, collect telemetry under varied operating regimes:
1. **Dynamic Motion Runs:** Gentle tilt, pitch, roll, and vibration maneuvers.
2. **Thermal Stress Runs:** Heating DHT11 (warm air) / cooling runs.
3. **Mechanical Vibration Stress:** Frame tapping, unbalance simulation.

### STAGE 5: Component-Specific Supervised Failure Prediction (FUTURE STAGE)
Supervised machine learning algorithms (Random Forest Classifier, XGBoost, or Logistic Regression) require **verified ground-truth failure labels** (`0 = Normal`, `1 = Degradation/Fault`).

#### Required Labeled Data for Subsystem Risk Targets:
- **`pan_tilt_risk`**: Requires labeled telemetry collected while forcing pan/tilt servo resistance, gear slipping, or motor binding.
- **`camera_subsystem_risk`**: Requires labeled telemetry collected during camera frame drops, video feed freezing, or optical brownouts.
- **`electronics_risk`**: Requires labeled telemetry under ESP32 thermal throttling ($> 65^\circ\text{C}$), voltage dips, or I2C clock stretching.
- **`overall_system_risk`**: Aggregate composite score calculated from subsystem risk predictions.

> **Crucial Rule:** Supervised models cannot be trained until real/defensible component fault labels are gathered during Stage 4 experiments.

---

## 3. How to Run Stage 3 ML Scripts

From the project root directory (`/Users/chouhantej/SIH DRONE`):

### 1. Train Anomaly Detection Model
```bash
python3 extreme_conditions/ml/train_anomaly_model.py
```
*Trains Isolation Forest on baseline data, saves model in `ml/model/`, and outputs `data/reports/anomaly_analysis.md` and 4 plots in `data/reports/anomaly/`.*

### 2. Run Anomaly Prediction & Explainability
```bash
python3 extreme_conditions/ml/predict_anomaly.py --file extreme_conditions/data/processed/processed_sensor_data.csv
```
*Loads trained Isolation Forest, computes anomaly risk scores, assigns risk levels, and prints feature deviation explanations.*

### 3. Launch Live Anomaly Monitor
- **CSV Simulation Mode:**
  ```bash
  python3 extreme_conditions/ml/live_anomaly_monitor.py --file extreme_conditions/data/raw/sensor_data_2026-08-26_110040.csv
  ```
- **Live ESP32 Serial Mode:**
  ```bash
  python3 extreme_conditions/ml/live_anomaly_monitor.py --serial /dev/cu.SLAB_USBtoUART
  ```
