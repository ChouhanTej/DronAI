#!/usr/bin/env python3
"""
Extreme Conditions Failure Prediction - Anomaly Prediction & Explainability Module
Loads trained Isolation Forest model bundle, calculates anomaly risk scores,
assigns prototype risk levels, and reports the top most unusual features against baseline parameters.
"""

import argparse
import json
import os
import sys
import joblib
import numpy as np
import pandas as pd

from feature_extraction import extract_features


def load_model_and_config(model_dir):
    """Loads fitted model bundle and feature_config.json."""
    model_path = os.path.join(model_dir, "isolation_forest.joblib")
    config_path = os.path.join(model_dir, "feature_config.json")

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Trained model not found at '{model_path}'. Run train_anomaly_model.py first.")

    bundle = joblib.load(model_path)

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    return bundle, config


def calculate_anomaly_risk(raw_decision_score):
    """
    Transforms raw Isolation Forest decision score into an Anomaly Risk Score in [0.0, 1.0].
    Raw score > 0.0 is inlier (normal), < 0.0 is outlier.
    Linear offset mapping: Risk = clip((0.10 - score) / 0.25, 0.0, 1.0)
    """
    return float(np.clip((0.10 - raw_decision_score) / 0.25, 0.0, 1.0))


def get_risk_level(risk_score):
    """Assigns prototype risk status based on anomaly risk score."""
    if risk_score < 0.25:
        return "NORMAL"
    elif risk_score < 0.50:
        return "LOW ANOMALY"
    elif risk_score < 0.75:
        return "MEDIUM ANOMALY"
    else:
        return "HIGH ANOMALY"


def explain_unusual_features(row, feature_cols, baseline_stats, top_k=3):
    """
    Ranks features by normalized z-score deviation against baseline mean and std dev:
    z_i = |x_i - mu_i| / sigma_i.
    Returns top_k most unusual features with current value, baseline mean, and deviation magnitude.
    """
    deviations = []
    for col in feature_cols:
        val = float(row[col]) if col in row else 0.0
        stats = baseline_stats.get(col, {"mean": 0.0, "std": 1.0})
        mean_val = stats["mean"]
        std_val = stats["std"] if stats["std"] > 1e-6 else 1.0

        z_score = abs(val - mean_val) / std_val
        deviations.append({
            "feature": col,
            "current_value": val,
            "baseline_mean": mean_val,
            "baseline_std": std_val,
            "z_score": z_score
        })

    # Sort descending by z_score
    deviations.sort(key=lambda x: x["z_score"], reverse=True)
    return deviations[:top_k]


def predict_anomalies_df(df_input, bundle):
    """
    Generates anomaly predictions, risk scores, and feature explanations for a DataFrame.
    """
    iso_model = bundle["model"]
    scaler = bundle["scaler"]
    feature_cols = bundle["feature_columns"]
    baseline_stats = bundle["baseline_stats"]

    # Auto-extract engineered features if missing
    if not all(col in df_input.columns for col in feature_cols):
        df_feat = extract_features(df_input, window_size=5)
    else:
        df_feat = df_input.copy()

    X_raw = df_feat[feature_cols].copy().replace([np.inf, -np.inf], np.nan).bfill().ffill().fillna(0.0)
    X_scaled = scaler.transform(X_raw)

    raw_scores = iso_model.decision_function(X_scaled)
    predictions = iso_model.predict(X_scaled)

    results = []
    for idx in range(len(df_feat)):
        raw_s = float(raw_scores[idx])
        risk_s = calculate_anomaly_risk(raw_s)
        status = get_risk_level(risk_s)
        top_unusual = explain_unusual_features(X_raw.iloc[idx], feature_cols, baseline_stats, top_k=3)

        res_entry = {
            "index": idx,
            "timestamp_ms": int(df_feat['timestamp_ms'].iloc[idx]) if 'timestamp_ms' in df_feat.columns else idx,
            "raw_decision_score": raw_s,
            "anomaly_risk_score": risk_s,
            "risk_level": status,
            "is_anomaly": bool(predictions[idx] == -1),
            "top_unusual_features": top_unusual
        }
        results.append(res_entry)

    return results


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, ".."))
    model_dir = os.path.join(project_root, "ml", "model")

    parser = argparse.ArgumentParser(description="Predict Anomaly Risk for Sensor Telemetry")
    parser.add_argument("-f", "--file", type=str, default=None, help="CSV file to evaluate")
    args = parser.parse_args()

    input_file = args.file or os.path.join(project_root, "data", "processed", "processed_sensor_data.csv")

    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found.")
        sys.exit(1)

    print("Loading Isolation Forest model bundle...")
    bundle, config = load_model_and_config(model_dir)

    df_in = pd.read_csv(input_file)
    print(f"Evaluating {len(df_in)} samples from '{os.path.basename(input_file)}'...")

    results = predict_anomalies_df(df_in, bundle)

    print(f"\nCompleted evaluation of {len(results)} samples.")
    high_anomalies = [r for r in results if r["risk_level"] in ["MEDIUM ANOMALY", "HIGH ANOMALY"]]
    print(f"Summary: {len(high_anomalies)} samples flagged with Medium/High Anomaly Risk.")

    # Display sample explanation for most unusual row
    most_anom = max(results, key=lambda x: x["anomaly_risk_score"])
    print(f"\nSample Anomaly Detail (Max Risk Row #{most_anom['index']}):")
    print(f"  Timestamp: {most_anom['timestamp_ms']} ms")
    print(f"  Raw Score: {most_anom['raw_decision_score']:.4f}")
    print(f"  Anomaly Risk: {most_anom['anomaly_risk_score']:.4f} ({most_anom['anomaly_risk_score']*100:.1f}%)")
    print(f"  Status: {most_anom['risk_level']}")
    print(f"  Most unusual features:")
    for feat in most_anom["top_unusual_features"]:
        print(f"   - {feat['feature']:20s}: {feat['current_value']:8.4f} (baseline mean: {feat['baseline_mean']:8.4f}, +{feat['z_score']:.2f} std dev)")


if __name__ == "__main__":
    main()
