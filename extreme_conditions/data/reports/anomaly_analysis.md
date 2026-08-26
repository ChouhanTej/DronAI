# Extreme Conditions Failure Prediction — Stage 3 Anomaly Detection Report

**Report Generation Date:** 2026-08-26  
**Module Stage:** Stage 3 — Unsupervised Anomaly Detection  
**Model Architecture:** `sklearn.ensemble.IsolationForest`  
**Model Artifact:** `extreme_conditions/ml/model/isolation_forest.joblib`  

---

## 1. Baseline Training Overview
- **Baseline Sample Count:** 221 samples (~3.67 minutes at 1.0 Hz)
- **Feature Space Dimension:** 18 selected physical telemetry features
- **Model Random Seed:** `42`
- **Contamination Parameter:** `0.03` (3.0% prototype noise sensitivity)

## 2. Selected Model Features
The Isolation Forest model is trained strictly on physical and rolling temporal features (excluding `timestamp_ms`):
- **Ambient Telemetry:** `temperature_c`, `humidity_percent`, `temp_change_rate`, `humidity_change_rate`
- **3D Magnitudes:** `accel_mag_g`, `gyro_mag_dps`
- **Rolling Acceleration Stats ($W=5$):** `accel_mag_mean`, `accel_mag_std`, `accel_mag_rms`, `accel_mag_max`, `accel_mag_min`
- **Rolling Gyroscope Stats ($W=5$):** `gyro_mag_mean`, `gyro_mag_std`, `gyro_mag_rms`, `gyro_mag_max`, `gyro_mag_min`
- **Vibration & Jitter Indicators:** `accel_z_std`, `gyro_z_std`

## 3. Model Parameters & Hyperparameters
```json
{
  "n_estimators": 100,
  "contamination": 0.03,
  "max_samples": "auto",
  "bootstrap": false,
  "random_state": 42
}
```

## 4. Baseline Anomaly Classification Results
- **Inlier Baseline Samples (Normal):** 214 (96.83%)
- **Flagged Baseline Outliers (Anomalies):** 7 (3.17%)

## 5. Anomaly Scoring & Calibration Method
The raw decision score S_raw from `IsolationForest.decision_function()` represents the mean isolation depth across 100 decision trees:
- S_raw > 0.0: Inlier (Normal telemetry)
- S_raw < 0.0: Outlier (Deviates from baseline)

To provide an intuitive metric for drone health monitoring, raw scores are mapped to a calibrated **Anomaly Risk Score** R in [0.0, 1.0]:
Risk = clip((0.10 - S_raw) / 0.25, 0.0, 1.0)

### Prototype Status Levels:
- **NORMAL:** Risk < 0.25 (Telemetry matches baseline)
- **LOW ANOMALY:** 0.25 <= Risk < 0.50 (Minor noise deviation)
- **MEDIUM ANOMALY:** 0.50 <= Risk < 0.75 (Moderate deviation / vibration spike)
- **HIGH ANOMALY:** Risk >= 0.75 (Severe departure from normal profile)

> **Important Note:** Risk scores represent normalized statistical deviations from the baseline distribution and are NOT true Bayesian probabilities of hardware failure.

## 6. Feature Deviation Explainability Method
Isolation Forest operates as an ensemble of random partitioning trees and does not provide traditional coefficient feature importances. To explain anomalous observations:
1. For each feature i, the normalized z-score deviation against baseline mean mu_i and standard deviation sigma_i is computed:
   z_i = |(x_i - mu_i) / sigma_i|
2. Features are ranked by z_i in descending order.
3. The top 3 features with the highest z_i are reported under *"Most unusual features"* without making false causal failure claims.

## 7. Analysis Plots Summary
Generated 4 evaluation plots in `extreme_conditions/data/reports/anomaly/`:
1. `anomaly_score_distribution.png`: Anomaly risk score distribution and threshold markers.
2. `feature_distributions.png`: Boxplots showing baseline feature spreads.
3. `baseline_feature_ranges.png`: Operational ranges (mean ± 2 std dev) for key features.
4. `anomaly_score_vs_time.png`: Anomaly risk score timeline over the baseline recording.

## 8. System Limitations
1. **Unlabeled Baseline Data:** Trained on 221 static desktop samples. Cannot classify specific hardware component faults (`camera_fault`, `pan_tilt_fault`).
2. **Environmental Scope:** Currently represents indoor room temperature (~2.5°C/DHT11 uncalibrated reading). Rapid ambient changes will trigger anomaly flags until multi-environment datasets are collected.

## 9. Recommended Next Experiments (Stage 4)
1. **Controlled Disturbance Runs:** Collect telemetry while tapping/vibrating the drone frame and heating the DHT11 to evaluate model anomaly sensitivity.
2. **Flight Maneuver Baseline:** Collect active hover and movement telemetry to expand the normal baseline profile.
