#!/usr/bin/env python3
"""
Extreme Conditions Failure Prediction - Model Training Script
Trains an Isolation Forest model on normal baseline sensor telemetry (processed_sensor_data.csv),
saves model artifacts in ml/model/, and generates evaluation plots and dataset_report.md.
"""

import json
import os
import sys
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

# Set visual style
plt.style.use('seaborn-v0_8-darkgrid' if 'seaborn-v0_8-darkgrid' in plt.style.available else 'default')
sns.set_theme(style="whitegrid")

# Selected Model Features (Explicitly excluding timestamp_ms)
FEATURE_COLUMNS = [
    'temperature_c',
    'humidity_percent',
    'accel_mag_g',
    'gyro_mag_dps',
    'accel_mag_mean',
    'accel_mag_std',
    'accel_mag_rms',
    'accel_mag_max',
    'accel_mag_min',
    'gyro_mag_mean',
    'gyro_mag_std',
    'gyro_mag_rms',
    'gyro_mag_max',
    'gyro_mag_min',
    'accel_z_std',
    'gyro_z_std',
    'temp_change_rate',
    'humidity_change_rate'
]


def train_anomaly_model(data_path, model_dir, report_dir):
    """Loads processed baseline data, trains Isolation Forest, saves artifacts and plots."""
    print("=" * 65)
    print(" EXTREME CONDITIONS FAILURE PREDICTION - MODEL TRAINING (STAGE 3)")
    print("=" * 65)

    if not os.path.exists(data_path):
        print(f"Error: Processed dataset '{data_path}' not found.")
        print("Please run 'python3 extreme_conditions/ml/preprocess.py' first.")
        sys.exit(1)

    df = pd.read_csv(data_path)
    print(f"Loaded processed dataset: {df.shape[0]} rows x {df.shape[1]} columns")

    # 1. Validate Feature Columns
    missing_cols = [c for c in FEATURE_COLUMNS if c not in df.columns]
    if missing_cols:
        print(f"Error: Missing required feature columns in dataset: {missing_cols}")
        sys.exit(1)

    X_raw = df[FEATURE_COLUMNS].copy()

    # 2. Handle missing / inf values safely
    X_raw = X_raw.replace([np.inf, -np.inf], np.nan).fillna(method='bfill').fillna(method='ffill').fillna(0.0)

    # 3. Fit Standard Scaler
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_raw)

    # 4. Train Isolation Forest Model
    contamination_rate = 0.03  # Expected ~3% baseline anomaly sensitivity for prototype tuning
    random_seed = 42

    iso_model = IsolationForest(
        n_estimators=100,
        contamination=contamination_rate,
        random_state=random_seed,
        n_jobs=-1
    )
    iso_model.fit(X_scaled)

    # 5. Calculate Predictions & Scores on Baseline Dataset
    raw_decision_scores = iso_model.decision_function(X_scaled)
    predictions = iso_model.predict(X_scaled)  # +1 for inliers, -1 for outliers

    # Transform raw decision scores to 0.0 - 1.0 Anomaly Risk Score
    # Raw decision_score > 0 is normal, < 0 is outlier.
    # Linear offset mapping: Risk = clip((0.10 - score) / 0.25, 0.0, 1.0)
    risk_scores = np.clip((0.10 - raw_decision_scores) / 0.25, 0.0, 1.0)

    num_anomalies = np.sum(predictions == -1)
    pct_anomalies = (num_anomalies / len(df)) * 100.0

    print(f"\nTraining Results Summary:")
    print(f"   - Baseline Samples Trained: {len(df)}")
    print(f"   - Selected Feature Count: {len(FEATURE_COLUMNS)}")
    print(f"   - Contamination Parameter: {contamination_rate:.2f}")
    print(f"   - Random Seed: {random_seed}")
    print(f"   - Samples Flagged as Baseline Anomalies: {num_anomalies} ({pct_anomalies:.2f}%)")
    print(f"   - Raw Decision Score Range: Min={raw_decision_scores.min():.4f} | Max={raw_decision_scores.max():.4f} | Mean={raw_decision_scores.mean():.4f}")
    print(f"   - Anomaly Risk Score Range: Min={risk_scores.min():.4f} | Max={risk_scores.max():.4f} | Mean={risk_scores.mean():.4f}")

    # 6. Save Model Artifacts
    os.makedirs(model_dir, exist_ok=True)
    model_filepath = os.path.join(model_dir, "isolation_forest.joblib")
    config_filepath = os.path.join(model_dir, "feature_config.json")

    # Baseline statistics dictionary for feature deviation explainability
    baseline_stats = {}
    for col in FEATURE_COLUMNS:
        baseline_stats[col] = {
            "mean": float(X_raw[col].mean()),
            "std": float(X_raw[col].std()) if X_raw[col].std() > 1e-6 else 1.0,
            "min": float(X_raw[col].min()),
            "max": float(X_raw[col].max())
        }

    # Save joblib bundle
    model_bundle = {
        "model": iso_model,
        "scaler": scaler,
        "feature_columns": FEATURE_COLUMNS,
        "baseline_stats": baseline_stats,
        "contamination": contamination_rate,
        "random_state": random_seed
    }
    joblib.dump(model_bundle, model_filepath)

    # Save JSON configuration
    config_data = {
        "model_type": "IsolationForest",
        "library_version": "scikit-learn",
        "contamination": contamination_rate,
        "random_state": random_seed,
        "feature_columns": FEATURE_COLUMNS,
        "baseline_sample_count": len(df),
        "risk_thresholds": {
            "NORMAL": "< 0.25",
            "LOW_ANOMALY": "0.25 - 0.50",
            "MEDIUM_ANOMALY": "0.50 - 0.75",
            "HIGH_ANOMALY": ">= 0.75"
        },
        "baseline_stats": baseline_stats
    }
    with open(config_filepath, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2)

    print(f"\n[SAVED] Saved model bundle to: {model_filepath}")
    print(f"[SAVED] Saved feature config to: {config_filepath}")

    # 7. Generate Report & Plots
    generate_anomaly_plots(df, raw_decision_scores, risk_scores, X_raw, report_dir)
    generate_anomaly_markdown_report(df, raw_decision_scores, risk_scores, num_anomalies, pct_anomalies, report_dir)

    return model_bundle


def generate_anomaly_plots(df, decision_scores, risk_scores, X_raw, report_dir):
    """Generates 4 analysis plots in data/reports/anomaly/."""
    plot_dir = os.path.join(report_dir, "anomaly")
    os.makedirs(plot_dir, exist_ok=True)
    t_sec = (df['timestamp_ms'] - df['timestamp_ms'].iloc[0]) / 1000.0 if 'timestamp_ms' in df.columns else np.arange(len(df))

    # Plot 1: Anomaly Score Distribution
    fig, ax = plt.subplots(figsize=(9, 4.5))
    sns.histplot(risk_scores, kde=True, bins=25, color='#0275d8', ax=ax)
    ax.axvline(0.25, color='green', linestyle='--', label='Low Anomaly Threshold (0.25)')
    ax.axvline(0.50, color='orange', linestyle='--', label='Medium Anomaly Threshold (0.50)')
    ax.axvline(0.75, color='red', linestyle='--', label='High Anomaly Threshold (0.75)')
    ax.set_title('Baseline Anomaly Risk Score Distribution', fontsize=14, fontweight='bold', pad=10)
    ax.set_xlabel('Anomaly Risk Score (0.0 = Normal, 1.0 = High Anomaly)', fontsize=12)
    ax.set_ylabel('Frequency', fontsize=12)
    ax.legend(loc='upper right')
    plt.tight_layout()
    p1 = os.path.join(plot_dir, 'anomaly_score_distribution.png')
    plt.savefig(p1, dpi=200)
    plt.close()
    print(f"   [CREATED] {os.path.basename(p1)}")

    # Plot 2: Key Feature Distributions (Boxplots)
    key_cols = ['accel_mag_g', 'gyro_mag_dps', 'accel_mag_rms', 'gyro_mag_rms', 'accel_z_std']
    available_cols = [c for c in key_cols if c in X_raw.columns]
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.boxplot(data=X_raw[available_cols], palette='Set2', ax=ax)
    ax.set_title('Baseline Feature Distributions (Boxplot)', fontsize=14, fontweight='bold', pad=10)
    ax.set_ylabel('Value Scale', fontsize=12)
    plt.xticks(rotation=15)
    plt.tight_layout()
    p2 = os.path.join(plot_dir, 'feature_distributions.png')
    plt.savefig(p2, dpi=200)
    plt.close()
    print(f"   [CREATED] {os.path.basename(p2)}")

    # Plot 3: Baseline Feature Ranges (Mean ± 2 Std Dev)
    means = X_raw[available_cols].mean()
    stds = X_raw[available_cols].std()
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.errorbar(x=range(len(available_cols)), y=means, yerr=2*stds, fmt='o', color='#d9534f', ecolor='#5bc0de', elinewidth=2, capsize=5, label='Mean ± 2 Std Dev')
    ax.set_xticks(range(len(available_cols)))
    ax.set_xticklabels(available_cols, rotation=15)
    ax.set_title('Baseline Feature Operational Ranges', fontsize=14, fontweight='bold', pad=10)
    ax.set_ylabel('Feature Scale', fontsize=12)
    ax.legend(loc='upper right')
    ax.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    p3 = os.path.join(plot_dir, 'baseline_feature_ranges.png')
    plt.savefig(p3, dpi=200)
    plt.close()
    print(f"   [CREATED] {os.path.basename(p3)}")

    # Plot 4: Anomaly Score vs Time
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(t_sec, risk_scores, color='#6f42c1', linewidth=1.8, label='Anomaly Risk Score')
    ax.axhline(0.25, color='green', linestyle=':', label='Low Anomaly (0.25)')
    ax.axhline(0.50, color='orange', linestyle=':', label='Medium Anomaly (0.50)')
    ax.axhline(0.75, color='red', linestyle=':', label='High Anomaly (0.75)')
    ax.set_title('Baseline Anomaly Risk Timeline', fontsize=14, fontweight='bold', pad=10)
    ax.set_xlabel('Time (seconds)', fontsize=12)
    ax.set_ylabel('Anomaly Risk Score', fontsize=12)
    ax.set_ylim(-0.05, 1.05)
    ax.legend(loc='upper right')
    ax.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    p4 = os.path.join(plot_dir, 'anomaly_score_vs_time.png')
    plt.savefig(p4, dpi=200)
    plt.close()
    print(f"   [CREATED] {os.path.basename(p4)}")


def generate_anomaly_markdown_report(df, decision_scores, risk_scores, num_anomalies, pct_anomalies, report_dir):
    """Outputs data/reports/anomaly_analysis.md."""
    report_file = os.path.join(report_dir, "anomaly_analysis.md")

    inliers_cnt = len(df) - num_anomalies
    inliers_pct = 100.0 - pct_anomalies

    content = f"""# Extreme Conditions Failure Prediction — Stage 3 Anomaly Detection Report

**Report Generation Date:** 2026-08-26  
**Module Stage:** Stage 3 — Unsupervised Anomaly Detection  
**Model Architecture:** `sklearn.ensemble.IsolationForest`  
**Model Artifact:** `extreme_conditions/ml/model/isolation_forest.joblib`  

---

## 1. Baseline Training Overview
- **Baseline Sample Count:** {len(df)} samples (~3.67 minutes at 1.0 Hz)
- **Feature Space Dimension:** {len(FEATURE_COLUMNS)} selected physical telemetry features
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
{{
  "n_estimators": 100,
  "contamination": 0.03,
  "max_samples": "auto",
  "bootstrap": false,
  "random_state": 42
}}
```

## 4. Baseline Anomaly Classification Results
- **Inlier Baseline Samples (Normal):** {inliers_cnt} ({inliers_pct:.2f}%)
- **Flagged Baseline Outliers (Anomalies):** {num_anomalies} ({pct_anomalies:.2f}%)

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
1. **Unlabeled Baseline Data:** Trained on {len(df)} static desktop samples. Cannot classify specific hardware component faults (`camera_fault`, `pan_tilt_fault`).
2. **Environmental Scope:** Currently represents indoor room temperature (~2.5°C/DHT11 uncalibrated reading). Rapid ambient changes will trigger anomaly flags until multi-environment datasets are collected.

## 9. Recommended Next Experiments (Stage 4)
1. **Controlled Disturbance Runs:** Collect telemetry while tapping/vibrating the drone frame and heating the DHT11 to evaluate model anomaly sensitivity.
2. **Flight Maneuver Baseline:** Collect active hover and movement telemetry to expand the normal baseline profile.
"""

    with open(report_file, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, ".."))
    processed_csv = os.path.join(project_root, "data", "processed", "processed_sensor_data.csv")
    model_dir = os.path.join(project_root, "ml", "model")
    report_dir = os.path.join(project_root, "data", "reports")

    train_anomaly_model(processed_csv, model_dir, report_dir)


if __name__ == "__main__":
    main()
