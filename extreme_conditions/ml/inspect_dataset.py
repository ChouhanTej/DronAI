#!/usr/bin/env python3
"""
Extreme Conditions Failure Prediction - Dataset Inspection & Quality Check Tool
Inspects raw sensor datasets, audits data quality, calculates sampling statistics,
and generates visualization plots in data/reports/.
"""

import argparse
import glob
import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Set visual style
plt.style.use('seaborn-v0_8-darkgrid' if 'seaborn-v0_8-darkgrid' in plt.style.available else 'default')
sns.set_theme(style="whitegrid")

# Standard column mapping
COLUMN_MAPPING = {
    'timestamp_ms': 'timestamp_ms',
    'temperature_c': 'temperature_c',
    'humidity_percent': 'humidity_percent',
    'accel_x_g': 'accel_x_g',
    'accel_y_g': 'accel_y_g',
    'accel_z_g': 'accel_z_g',
    'gyro_x_dps': 'gyro_x_dps',
    'gyro_y_dps': 'gyro_y_dps',
    'gyro_z_dps': 'gyro_z_dps'
}


def find_latest_raw_csv(data_dir):
    """Finds the raw CSV file with the most rows or latest modification time."""
    pattern = os.path.join(data_dir, "sensor_data_*.csv")
    csv_files = glob.glob(pattern)
    if not csv_files:
        # Fallback to any CSV in raw directory
        csv_files = glob.glob(os.path.join(data_dir, "*.csv"))
        # Exclude hidden files
        csv_files = [f for f in csv_files if not os.path.basename(f).startswith('.')]

    if not csv_files:
        return None

    # Sort by size / line count to pick primary dataset
    best_file = max(csv_files, key=os.path.getsize)
    return best_file


def inspect_dataset(file_path):
    """Performs Part 1 (Inspection) and Part 2 (Quality Checks) on the raw CSV file."""
    print("=" * 60)
    print(" EXTREME CONDITIONS FAILURE PREDICTION - DATASET INSPECTION")
    print("=" * 60)
    print(f"Target File: {file_path}")

    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' does not exist.")
        sys.exit(1)

    df_raw = pd.read_csv(file_path)
    rows_count, cols_count = df_raw.shape
    print(f"\n1. Dataset Dimensions: {rows_count} rows x {cols_count} columns")

    # Column Mapping check
    print(f"\n2. Columns & Data Types:")
    for col in df_raw.columns:
        print(f"   - {col:20s} | Type: {str(df_raw[col].dtype):10s} | Nulls: {df_raw[col].isnull().sum()}")

    # Ensure expected numerical columns
    df = df_raw.copy()
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    non_numeric_counts = df.isnull().sum() - df_raw.isnull().sum()
    print(f"\n3. Data Quality Audit:")
    print(f"   - Duplicate Rows: {df_raw.duplicated().sum()}")
    print(f"   - Total Missing (NaN) Values: {df.isnull().sum().sum()}")
    print(f"   - Non-numeric / Corrupted entries: {non_numeric_counts.sum()}")

    # Statistical Summary
    numeric_cols = [c for c in df.columns if c != 'timestamp_ms']
    stats_df = pd.DataFrame({
        'Min': df[numeric_cols].min(),
        'Max': df[numeric_cols].max(),
        'Mean': df[numeric_cols].mean(),
        'Std': df[numeric_cols].std()
    })
    print(f"\n4. Sensor Statistical Summary:")
    print(stats_df.round(4).to_string())

    # Timestamp & Sampling Rate Analysis
    print(f"\n5. Sampling Rate & Time Analysis:")
    if 'timestamp_ms' in df.columns:
        unique_ts = df['timestamp_ms'].nunique()
        ts_diff = df['timestamp_ms'].diff().dropna()
        total_duration_sec = (df['timestamp_ms'].max() - df['timestamp_ms'].min()) / 1000.0 if rows_count > 1 else 0
        mean_dt = ts_diff.mean()
        std_dt = ts_diff.std()
        sampling_rate = 1000.0 / mean_dt if mean_dt > 0 else 0

        print(f"   - Total Recorded Duration: {total_duration_sec:.2f} seconds ({total_duration_sec / 60.0:.2f} minutes)")
        print(f"   - Unique Timestamps: {unique_ts} / {rows_count}")
        print(f"   - Sampling Interval (dt): Mean={mean_dt:.2f} ms | Std={std_dt:.2f} ms | Min={ts_diff.min():.0f} ms | Max={ts_diff.max():.0f} ms")
        print(f"   - Effective Sampling Frequency: {sampling_rate:.2f} Hz (~1 sample every {mean_dt / 1000.0:.2f} s)")

    # Suspicious Value Flagging
    flags = []
    if 'temperature_c' in df.columns:
        invalid_temp = df[(df['temperature_c'] < -10) | (df['temperature_c'] > 60)]
        if len(invalid_temp) > 0:
            flags.append(f"{len(invalid_temp)} temperature values outside physical range (-10°C to 60°C)")

    if 'humidity_percent' in df.columns:
        invalid_hum = df[(df['humidity_percent'] < 0) | (df['humidity_percent'] > 100)]
        if len(invalid_hum) > 0:
            flags.append(f"{len(invalid_hum)} humidity values outside 0-100%")

    if {'accel_x_g', 'accel_y_g', 'accel_z_g'}.issubset(df.columns):
        accel_mag = np.sqrt(df['accel_x_g']**2 + df['accel_y_g']**2 + df['accel_z_g']**2)
        stationary_anomaly = df[(accel_mag < 0.5) | (accel_mag > 2.5)]
        if len(stationary_anomaly) > 0:
            flags.append(f"{len(stationary_anomaly)} acceleration magnitude anomalies outside 0.5g–2.5g range")

    print(f"\n6. Suspicious Reading Flags:")
    if flags:
        for f in flags:
            print(f"   [FLAG] {f}")
    else:
        print("   [CLEAN] No physical bound violations detected in raw data.")

    return df, stats_df


def generate_visualizations(df, output_dir):
    """Generates 7 visualization plots and saves them into output_dir."""
    os.makedirs(output_dir, exist_ok=True)
    print(f"\n7. Generating Visualization Plots in: {output_dir}")

    # Calculate time in seconds
    t_sec = (df['timestamp_ms'] - df['timestamp_ms'].iloc[0]) / 1000.0 if 'timestamp_ms' in df.columns else np.arange(len(df))
    accel_mag = np.sqrt(df['accel_x_g']**2 + df['accel_y_g']**2 + df['accel_z_g']**2) if {'accel_x_g', 'accel_y_g', 'accel_z_g'}.issubset(df.columns) else None
    gyro_mag = np.sqrt(df['gyro_x_dps']**2 + df['gyro_y_dps']**2 + df['gyro_z_dps']**2) if {'gyro_x_dps', 'gyro_y_dps', 'gyro_z_dps'}.issubset(df.columns) else None

    # Plot 1: Temperature vs Time
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(t_sec, df['temperature_c'], color='#d9534f', linewidth=2, label='Temperature (°C)')
    ax.set_title('DHT11 Temperature vs Time', fontsize=14, fontweight='bold', pad=10)
    ax.set_xlabel('Time (seconds)', fontsize=12)
    ax.set_ylabel('Temperature (°C)', fontsize=12)
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.legend(loc='upper right')
    plt.tight_layout()
    plot1_path = os.path.join(output_dir, 'temperature_vs_time.png')
    plt.savefig(plot1_path, dpi=200)
    plt.close()
    print(f"   [CREATED] {os.path.basename(plot1_path)}")

    # Plot 2: Humidity vs Time
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(t_sec, df['humidity_percent'], color='#0275d8', linewidth=2, label='Humidity (%)')
    ax.set_title('DHT11 Humidity vs Time', fontsize=14, fontweight='bold', pad=10)
    ax.set_xlabel('Time (seconds)', fontsize=12)
    ax.set_ylabel('Humidity (%)', fontsize=12)
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.legend(loc='upper right')
    plt.tight_layout()
    plot2_path = os.path.join(output_dir, 'humidity_vs_time.png')
    plt.savefig(plot2_path, dpi=200)
    plt.close()
    print(f"   [CREATED] {os.path.basename(plot2_path)}")

    # Plot 3: Acceleration X/Y/Z vs Time
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(t_sec, df['accel_x_g'], label='Accel X (g)', alpha=0.85)
    ax.plot(t_sec, df['accel_y_g'], label='Accel Y (g)', alpha=0.85)
    ax.plot(t_sec, df['accel_z_g'], label='Accel Z (g)', alpha=0.85)
    ax.set_title('MPU Motion Sensor Acceleration (X/Y/Z) vs Time', fontsize=14, fontweight='bold', pad=10)
    ax.set_xlabel('Time (seconds)', fontsize=12)
    ax.set_ylabel('Acceleration (g)', fontsize=12)
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.legend(loc='upper right')
    plt.tight_layout()
    plot3_path = os.path.join(output_dir, 'accel_xyz_vs_time.png')
    plt.savefig(plot3_path, dpi=200)
    plt.close()
    print(f"   [CREATED] {os.path.basename(plot3_path)}")

    # Plot 4: Gyroscope X/Y/Z vs Time
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(t_sec, df['gyro_x_dps'], label='Gyro X (dps)', alpha=0.85)
    ax.plot(t_sec, df['gyro_y_dps'], label='Gyro Y (dps)', alpha=0.85)
    ax.plot(t_sec, df['gyro_z_dps'], label='Gyro Z (dps)', alpha=0.85)
    ax.set_title('MPU Motion Sensor Gyroscope (X/Y/Z) vs Time', fontsize=14, fontweight='bold', pad=10)
    ax.set_xlabel('Time (seconds)', fontsize=12)
    ax.set_ylabel('Angular Velocity (dps)', fontsize=12)
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.legend(loc='upper right')
    plt.tight_layout()
    plot4_path = os.path.join(output_dir, 'gyro_xyz_vs_time.png')
    plt.savefig(plot4_path, dpi=200)
    plt.close()
    print(f"   [CREATED] {os.path.basename(plot4_path)}")

    # Plot 5: Acceleration Magnitude vs Time
    if accel_mag is not None:
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(t_sec, accel_mag, color='#f0ad4e', linewidth=2, label='||Accel|| (g)')
        ax.axhline(1.0, color='gray', linestyle=':', label='1.0g Gravity Ref')
        ax.set_title('Acceleration Vector Magnitude vs Time', fontsize=14, fontweight='bold', pad=10)
        ax.set_xlabel('Time (seconds)', fontsize=12)
        ax.set_ylabel('Magnitude (g)', fontsize=12)
        ax.grid(True, linestyle='--', alpha=0.6)
        ax.legend(loc='upper right')
        plt.tight_layout()
        plot5_path = os.path.join(output_dir, 'accel_mag_vs_time.png')
        plt.savefig(plot5_path, dpi=200)
        plt.close()
        print(f"   [CREATED] {os.path.basename(plot5_path)}")

    # Plot 6: Gyroscope Magnitude vs Time
    if gyro_mag is not None:
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(t_sec, gyro_mag, color='#5bc0de', linewidth=2, label='||Gyro|| (dps)')
        ax.set_title('Gyroscope Vector Magnitude vs Time', fontsize=14, fontweight='bold', pad=10)
        ax.set_xlabel('Time (seconds)', fontsize=12)
        ax.set_ylabel('Magnitude (dps)', fontsize=12)
        ax.grid(True, linestyle='--', alpha=0.6)
        ax.legend(loc='upper right')
        plt.tight_layout()
        plot6_path = os.path.join(output_dir, 'gyro_mag_vs_time.png')
        plt.savefig(plot6_path, dpi=200)
        plt.close()
        print(f"   [CREATED] {os.path.basename(plot6_path)}")

    # Plot 7: Sensor Correlation Heatmap
    corr_df = df.drop(columns=['timestamp_ms'], errors='ignore').copy()
    if accel_mag is not None:
        corr_df['accel_mag'] = accel_mag
    if gyro_mag is not None:
        corr_df['gyro_mag'] = gyro_mag

    fig, ax = plt.subplots(figsize=(9, 7))
    sns.heatmap(corr_df.corr(), annot=True, fmt=".2f", cmap="coolwarm", cbar=True, ax=ax, square=True, linewidths=0.5)
    ax.set_title('Sensor Feature Correlation Heatmap', fontsize=14, fontweight='bold', pad=10)
    plt.tight_layout()
    plot7_path = os.path.join(output_dir, 'correlation_heatmap.png')
    plt.savefig(plot7_path, dpi=200)
    plt.close()
    print(f"   [CREATED] {os.path.basename(plot7_path)}")


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, ".."))
    raw_data_dir = os.path.join(project_root, "data", "raw")
    reports_dir = os.path.join(project_root, "data", "reports")

    parser = argparse.ArgumentParser(description="Inspect and Audit Raw Sensor Dataset")
    parser.add_argument("-f", "--file", type=str, default=None, help="Path to raw CSV file")
    args = parser.parse_args()

    csv_path = args.file or find_latest_raw_csv(raw_data_dir)
    if not csv_path:
        print(f"Error: No raw CSV files found in '{raw_data_dir}'. Please record sensor data first.")
        sys.exit(1)

    df, stats_df = inspect_dataset(csv_path)
    generate_visualizations(df, reports_dir)
    print("\nInspection and visualization completed successfully!")


if __name__ == "__main__":
    main()
