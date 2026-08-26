# Extreme Conditions Failure Prediction — Dataset & Quality Audit Report

**Report Generation Date:** 2026-08-26  
**Target Module:** Extreme Conditions Failure Prediction (Stage 2)  
**Primary Dataset File:** `sensor_data_2026-08-26_110040.csv`  

---

## 1. Dataset Overview & Dimensions
- **Total Valid Samples (Rows):** 221
- **Raw Sensor Columns (Cols):** 9
- **Processed Dataset Features:** 25 total columns
- **Recording Duration:** 220.00 seconds (~3.67 minutes)

## 2. Sensor Columns & Data Types
The raw dataset preserves the following 9 physical telemetry channels:

| Column Name | Data Type | Physical Unit | Description |
|-------------|-----------|---------------|-------------|
| `timestamp_ms` | `int64` | milliseconds | System uptime timestamp (`millis()`) |
| `temperature_c` | `float64` | °C | Ambient temperature from DHT11 |
| `humidity_percent` | `float64` | % | Relative humidity percentage from DHT11 |
| `accel_x_g` | `float64` | g | X-axis acceleration ($1\,g = 9.80665\,\text{m/s}^2$) |
| `accel_y_g` | `float64` | g | Y-axis acceleration |
| `accel_z_g` | `float64` | g | Z-axis acceleration |
| `gyro_x_dps` | `float64` | °/s (dps) | X-axis angular velocity |
| `gyro_y_dps` | `float64` | °/s (dps) | Y-axis angular velocity |
| `gyro_z_dps` | `float64` | °/s (dps) | Z-axis angular velocity |

## 3. Data Quality & Missing Value Audit
- **Missing (NaN) Values:** 0
- **Duplicate Rows:** 0
- **Corrupted / Non-numeric Values:** 0
- **Data Integrity Score:** **100% Valid CSV Structure**

## 4. Outliers & Suspicious Value Analysis
- **DHT11 Bounds Check:** Temperature ranged from 2.40°C to 2.50°C; Humidity ranged from 20.30% to 20.90%. All values fall strictly within physical sensor operational boundaries.
- **Gravity Vector Bounds:** Vector acceleration magnitude averaged ~1.07g, consistent with static desktop placement subject to minor sensor calibration offset. No impossible spikes ($>5.0g$) were observed.

## 5. Sampling Rate & Temporal Stability
- **Mean Sampling Interval ($\Delta t$):** 1000.00 ms
- **Standard Deviation of $\Delta t$:** 0.00 ms
- **Effective Sampling Frequency:** 1.00 Hz (~1 sample per second)
- **Frame Drop / Gap Analysis:** No lost frames or timeline discontinuities detected.

## 6. Raw Sensor Statistical Summary

```text
                    Min     Max     Mean     Std
temperature_c      2.40    2.50   2.4932  0.0252
humidity_percent  20.30   20.90  20.6154  0.1619
accel_x_g         -0.06    0.31  -0.0096  0.0748
accel_y_g         -0.11    0.44   0.0090  0.0984
accel_z_g          0.78    1.12   1.0594  0.0314
gyro_x_dps       -57.31   26.29  -0.1479  5.1547
gyro_y_dps       -68.00   74.84   1.3821  8.5235
gyro_z_dps       -36.20  125.48   1.7920  9.3660
```

## 7. Visual Observations
Generated 7 analysis plots stored under `extreme_conditions/data/reports/`:
1. `temperature_vs_time.png`: Steady temperature profile across recording window.
2. `humidity_vs_time.png`: Stable ambient relative humidity curve.
3. `accel_xyz_vs_time.png`: Clear separation between static gravity ($accel\_z \approx 1.07g$) and orthogonal axes ($accel\_x, accel\_y \approx 0.0g$).
4. `gyro_xyz_vs_time.png`: Baseline noise floor for gyroscope sensor axes.
5. `accel_mag_vs_time.png`: Total acceleration magnitude curve centered near 1.07g.
6. `gyro_mag_vs_time.png`: Gyroscope magnitude curve tracking rotational motion energy.
7. `correlation_heatmap.png`: Inter-feature correlation heatmap revealing relationships between directional components and magnitudes.

## 8. Feature Extraction Summary
Extracted **16 engineered features** using a rolling window $W = 5$ samples (5 seconds at 1 Hz):
- **3D Magnitudes:** `accel_mag_g`, `gyro_mag_dps`
- **Rolling Acceleration Stats:** `accel_mag_mean`, `accel_mag_std`, `accel_mag_rms`, `accel_mag_max`, `accel_mag_min`
- **Rolling Gyroscope Stats:** `gyro_mag_mean`, `gyro_mag_std`, `gyro_mag_rms`, `gyro_mag_max`, `gyro_mag_min`
- **Vibration & Dynamics:** `accel_z_std`, `gyro_z_std`, `temp_change_rate`, `humidity_change_rate`

## 9. Operating Condition Distribution
> **Important Note:** Dataset currently contains sensor measurements but no verified failure labels.

The 221 recorded samples represent **normal, static baseline desktop telemetry** with minimal environmental or mechanical disturbance.

## 10. Sufficiency Evaluation (221 Samples)
- **Is 221 samples sufficient for prototype pipeline verification?**  
  **YES.** 221 samples are fully sufficient to validate sensor drivers, data collection tools, feature extraction pipelines, and baseline anomaly detection algorithms.
- **Is 221 samples sufficient for a production Failure Prediction system?**  
  **NO.** 221 baseline samples cannot train a production machine learning model because they lack stress states, failure conditions, and failure labels.

## 11. Additional Data Required for ML Training
To build an operational failure prediction system, collect:
1. **Dynamic Motion Data:** Flight/movement maneuvers (pitch, roll, yaw dynamics).
2. **Mechanical Vibration Data:** Motor unbalance, propeller damage, frame stress.
3. **Thermal Stress Data:** Heated/cooled environment operational runs.
4. **Fault Injection Experiments:** Labeled instances of degraded components.

## 12. Supervised ML Feasibility Assessment
- **Supervised Classification / Regression:** **NOT CURRENTLY POSSIBLE** (requires target labels such as `component_fault = 0` or `1`).
- **Unsupervised Anomaly Detection:** **POSSIBLE & RECOMMENDED** (Isolation Forest, One-Class SVM, or Mahalanobis Distance trained on baseline data to detect deviations).

## 13. Recommended Next Step (Stage 3)
1. Implement **Unsupervised Baseline Anomaly Detection** (Isolation Forest) trained on this 221-sample clean baseline dataset.
2. Collect **Simulated Stress / Disturbance Datasets** (tapping/vibrating frame, heating DHT11) to evaluate the anomaly detector's sensitivity.
3. Define failure thresholds and risk scores for drone subsystems (`electronics_risk`, `mechanical_risk`).
