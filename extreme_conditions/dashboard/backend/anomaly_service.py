"""
Extreme Conditions Failure Risk Dashboard - Anomaly Service
Integrates the existing trained Isolation Forest model, feature extraction pipeline,
and explainability calculations for the real-time web dashboard.
"""

import collections
import json
import os
import sys
import joblib
import numpy as np
import pandas as pd

# Add extreme_conditions/ml to Python path to reuse feature_extraction.py
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
ML_DIR = os.path.join(PROJECT_ROOT, "ml")
if ML_DIR not in sys.path:
    sys.path.insert(0, ML_DIR)

from feature_extraction import extract_features


class AnomalyService:
    def __init__(self, model_dir=None):
        self.model_dir = model_dir or os.path.join(PROJECT_ROOT, "ml", "model")
        self.model_path = os.path.join(self.model_dir, "isolation_forest.joblib")
        self.config_path = os.path.join(self.model_dir, "feature_config.json")

        self.bundle = None
        self.config = None
        self.is_loaded = False
        self.buffer = collections.deque(maxlen=15)

        self._load_artifacts()

    def _load_artifacts(self):
        """Loads trained Isolation Forest joblib bundle and feature_config.json."""
        try:
            if not os.path.exists(self.model_path):
                print(f"[ANOMALY SERVICE WARNING] Model file '{self.model_path}' not found.")
                return

            self.bundle = joblib.load(self.model_path)
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)

            self.is_loaded = True
            print("[ANOMALY SERVICE] Loaded Isolation Forest model and feature configuration successfully.")
        except Exception as e:
            print(f"[ANOMALY SERVICE ERROR] Failed to load model artifacts: {e}")
            self.is_loaded = False

    def process_sample(self, raw_sample: dict) -> dict:
        """
        Processes a raw sensor dictionary sample, updates rolling feature window,
        evaluates Isolation Forest anomaly score, and ranks feature deviations.
        """
        self.buffer.append(raw_sample)

        # Basic 3D magnitude calculations for raw sample
        ax = float(raw_sample.get('accel_x_g', 0.0))
        ay = float(raw_sample.get('accel_y_g', 0.0))
        az = float(raw_sample.get('accel_z_g', 1.0))
        accel_mag = float(np.sqrt(ax**2 + ay**2 + az**2))

        gx = float(raw_sample.get('gyro_x_dps', 0.0))
        gy = float(raw_sample.get('gyro_y_dps', 0.0))
        gz = float(raw_sample.get('gyro_z_dps', 0.0))
        gyro_mag = float(np.sqrt(gx**2 + gy**2 + gz**2))

        # Default telemetry values
        processed_result = {
            "timestamp_ms": int(raw_sample.get('timestamp_ms', 0)),
            "temperature_c": float(raw_sample.get('temperature_c', 0.0)),
            "humidity_percent": float(raw_sample.get('humidity_percent', 0.0)),
            "accel_x_g": ax,
            "accel_y_g": ay,
            "accel_z_g": az,
            "gyro_x_dps": gx,
            "gyro_y_dps": gy,
            "gyro_z_dps": gz,
            "accel_mag_g": accel_mag,
            "gyro_mag_dps": gyro_mag,
            "accel_mag_rms": accel_mag,
            "gyro_mag_rms": gyro_mag,
            "anomaly_risk_score": 0.0,
            "raw_decision_score": 0.30,
            "status": "NORMAL",
            "model_loaded": self.is_loaded,
            "most_unusual_parameters": []
        }

        if not self.is_loaded:
            return processed_result

        try:
            # Extract features over buffer
            df_buf = pd.DataFrame(list(self.buffer))
            df_feat = extract_features(df_buf, window_size=5)
            latest_feat = df_feat.iloc[-1]

            feature_cols = self.bundle["feature_columns"]
            scaler = self.bundle["scaler"]
            iso_model = self.bundle["model"]
            baseline_stats = self.bundle["baseline_stats"]

            X_latest = pd.DataFrame([latest_feat])[feature_cols].replace([np.inf, -np.inf], np.nan).fillna(0.0)
            X_scaled = scaler.transform(X_latest)

            raw_decision_score = float(iso_model.decision_function(X_scaled)[0])

            # Linear offset mapping to Risk Score (0.0 -> 1.0)
            risk_score = float(np.clip((0.10 - raw_decision_score) / 0.25, 0.0, 1.0))

            # Prototype status levels based on risk score thresholds
            # 0–30% NORMAL | 30–60% WARNING | 60–100% HIGH ANOMALY
            if risk_score < 0.30:
                status = "NORMAL"
            elif risk_score < 0.60:
                status = "WARNING"
            else:
                status = "HIGH ANOMALY"

            # Compute top 3 unusual parameter deviations
            unusual_params = []
            for col in feature_cols:
                val = float(X_latest.iloc[0][col])
                b_stat = baseline_stats.get(col, {"mean": 0.0, "std": 1.0})
                b_mean = b_stat["mean"]
                b_std = b_stat["std"] if b_stat["std"] > 1e-6 else 1.0

                z_score = abs(val - b_mean) / b_std
                
                # Human readable explanation level
                if z_score > 10.0:
                    dev_desc = "High deviation from baseline"
                elif z_score > 3.0:
                    dev_desc = "Moderate deviation from baseline"
                elif z_score > 1.5:
                    dev_desc = "Minor deviation from baseline"
                else:
                    dev_desc = "Normal range"

                unusual_params.append({
                    "parameter": col.replace('_g', '').replace('_dps', '').replace('_', ' ').title(),
                    "raw_key": col,
                    "current_value": round(val, 4),
                    "baseline_mean": round(b_mean, 4),
                    "z_score": round(z_score, 2),
                    "deviation_level": dev_desc
                })

            unusual_params.sort(key=lambda x: x["z_score"], reverse=True)
            top_3_unusual = unusual_params[:3]

            processed_result.update({
                "accel_mag_rms": float(latest_feat.get('accel_mag_rms', accel_mag)),
                "gyro_mag_rms": float(latest_feat.get('gyro_mag_rms', gyro_mag)),
                "anomaly_risk_score": round(risk_score, 4),
                "raw_decision_score": round(raw_decision_score, 4),
                "status": status,
                "most_unusual_parameters": top_3_unusual
            })
        except Exception as e:
            print(f"[ANOMALY SERVICE EXCEPTION] Error processing telemetry sample: {e}")

        return processed_result
