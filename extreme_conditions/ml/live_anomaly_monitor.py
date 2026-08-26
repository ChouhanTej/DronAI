#!/usr/bin/env python3
"""
Extreme Conditions Failure Prediction - Live Sensor Monitor
Monitors real-time ESP32 sensor telemetry (over Serial or CSV stream),
calculates rolling feature vectors, evaluates anomaly risk, and displays live dashboard.
"""

import argparse
import collections
import os
import sys
import time
import numpy as np
import pandas as pd

from feature_extraction import extract_features
from predict_anomaly import load_model_and_config, calculate_anomaly_risk, get_risk_level, explain_unusual_features

try:
    import serial
except ImportError:
    serial = None


def render_dashboard(row_raw, risk_score, risk_level, top_unusual):
    """Prints formatted real-time terminal dashboard."""
    temp_c = float(row_raw.get('temperature_c', 0.0))
    hum_pct = float(row_raw.get('humidity_percent', 0.0))
    
    ax = float(row_raw.get('accel_x_g', 0.0))
    ay = float(row_raw.get('accel_y_g', 0.0))
    az = float(row_raw.get('accel_z_g', 1.0))
    accel_mag = np.sqrt(ax**2 + ay**2 + az**2)
    
    gx = float(row_raw.get('gyro_x_dps', 0.0))
    gy = float(row_raw.get('gyro_y_dps', 0.0))
    gz = float(row_raw.get('gyro_z_dps', 0.0))
    gyro_mag = np.sqrt(gx**2 + gy**2 + gz**2)

    print("\n--------------------------------")
    print(" EXTREME CONDITIONS MONITOR")
    print("--------------------------------")
    print(f"Temperature:  {temp_c:6.2f} °C")
    print(f"Humidity:     {hum_pct:6.2f} %")
    print(f"Acceleration: {accel_mag:6.2f} g")
    print(f"Gyroscope:    {gyro_mag:6.2f} dps")
    print(f"\nAnomaly Risk: {risk_score:.2f} ({risk_score*100.0:.1f}%)")
    print(f"Status:       {risk_level}")
    
    if risk_level != "NORMAL":
        print("ALERT: Abnormal operating condition detected.")

    print("\nMost unusual features:")
    for feat in top_unusual:
        print(f" - {feat['feature']:20s}: {feat['current_value']:8.4f} (baseline mean: {feat['baseline_mean']:8.4f}, +{feat['z_score']:.2f} std dev)")
    print("--------------------------------")


def process_live_stream(data_generator, bundle):
    """Processes stream of raw telemetry dictionaries using a 5-sample sliding window buffer."""
    iso_model = bundle["model"]
    scaler = bundle["scaler"]
    feature_cols = bundle["feature_columns"]
    baseline_stats = bundle["baseline_stats"]

    window_buffer = collections.deque(maxlen=10)

    sample_counter = 0
    for raw_sample in data_generator:
        sample_counter += 1
        window_buffer.append(raw_sample)

        # Convert buffer to DataFrame for feature extraction
        df_buf = pd.DataFrame(list(window_buffer))
        df_feat = extract_features(df_buf, window_size=5)

        latest_row = df_feat.iloc[-1]
        X_latest = pd.DataFrame([latest_row])[feature_cols].replace([np.inf, -np.inf], np.nan).fillna(0.0)
        X_scaled = scaler.transform(X_latest)

        raw_score = float(iso_model.decision_function(X_scaled)[0])
        risk_score = calculate_anomaly_risk(raw_score)
        risk_level = get_risk_level(risk_score)
        top_unusual = explain_unusual_features(X_latest.iloc[0], feature_cols, baseline_stats, top_k=3)

        render_dashboard(raw_sample, risk_score, risk_level, top_unusual)


def file_sample_generator(csv_path, delay=0.5):
    """Yields samples line-by-line from a CSV file."""
    df = pd.read_csv(csv_path)
    for _, row in df.iterrows():
        sample = row.to_dict()
        yield sample
        if delay > 0:
            time.sleep(delay)


def serial_sample_generator(port_name, baud_rate=115200):
    """Yields samples line-by-line from an active ESP32 serial stream."""
    if serial is None:
        print("Error: 'pyserial' package is not installed.")
        sys.exit(1)

    print(f"Connecting to ESP32 on port '{port_name}' @ {baud_rate} baud...")
    ser = serial.Serial(port_name, baud_rate, timeout=2.0)
    time.sleep(1.5)
    print("Connected! Reading live telemetry stream...")

    while True:
        line = ser.readline().decode("utf-8", errors="replace").strip()
        if not line or line.startswith("ERROR") or line.startswith("timestamp_ms"):
            continue

        parts = line.split(",")
        if len(parts) == 9:
            try:
                ts, temp, hum, ax, ay, az, gx, gy, gz = parts
                sample = {
                    'timestamp_ms': float(ts),
                    'temperature_c': float(temp),
                    'humidity_percent': float(hum),
                    'accel_x_g': float(ax),
                    'accel_y_g': float(ay),
                    'accel_z_g': float(az),
                    'gyro_x_dps': float(gx),
                    'gyro_y_dps': float(gy),
                    'gyro_z_dps': float(gz),
                }
                yield sample
            except ValueError:
                continue


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, ".."))
    model_dir = os.path.join(project_root, "ml", "model")

    parser = argparse.ArgumentParser(description="Live Sensor Anomaly Monitor")
    parser.add_argument("-f", "--file", type=str, default=None, help="Path to CSV file to simulate stream")
    parser.add_argument("-s", "--serial", type=str, default=None, help="Serial port (e.g. /dev/cu.SLAB_USBtoUART)")
    parser.add_argument("-b", "--baud", type=int, default=115200, help="Baud rate (default: 115200)")
    parser.add_argument("--delay", type=float, default=0.2, help="Delay between CSV frames in seconds")
    args = parser.parse_args()

    bundle, config = load_model_and_config(model_dir)

    if args.serial:
        gen = serial_sample_generator(args.serial, args.baud)
    else:
        file_path = args.file or os.path.join(project_root, "data", "raw", "sensor_data_2026-08-26_110040.csv")
        if not os.path.exists(file_path):
            print(f"Error: CSV file '{file_path}' not found.")
            sys.exit(1)
        print(f"Running monitor in CSV simulation mode using '{os.path.basename(file_path)}'...")
        gen = file_sample_generator(file_path, delay=args.delay)

    try:
        process_live_stream(gen, bundle)
    except KeyboardInterrupt:
        print("\nLive Anomaly Monitor stopped safely.")


if __name__ == "__main__":
    main()
