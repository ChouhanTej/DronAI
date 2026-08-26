#!/usr/bin/env python3
"""
Extreme Conditions Failure Prediction - Feature Extraction Module
Calculates physical vector magnitudes, rolling window time-domain statistics,
and vibration energy metrics from raw MPU6050 and DHT11 telemetry.
"""

import numpy as np
import pandas as pd


def compute_rolling_rms(series, window, min_periods=1):
    """Calculates Root Mean Square (RMS) over a rolling window: sqrt(mean(x^2))."""
    return np.sqrt((series ** 2).rolling(window=window, min_periods=min_periods).mean())


def extract_features(df: pd.DataFrame, window_size: int = 5) -> pd.DataFrame:
    """
    Extracts engineered features from raw telemetry dataframe.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Input dataframe containing raw sensor columns.
    window_size : int, default=5
        Rolling window size in samples (~5 seconds at 1 Hz sampling rate).
        A 5-sample window captures short-term motion/vibration dynamics
        without causing severe delay or losing edge samples (using min_periods=1).
        
    Returns:
    --------
    pd.DataFrame
        Enriched dataframe containing original sensor columns and 15+ engineered features.
    """
    df_feat = df.copy()

    # 1. Calculate Vector Magnitudes
    if {'accel_x_g', 'accel_y_g', 'accel_z_g'}.issubset(df_feat.columns):
        df_feat['accel_mag_g'] = np.sqrt(
            df_feat['accel_x_g']**2 + df_feat['accel_y_g']**2 + df_feat['accel_z_g']**2
        )

    if {'gyro_x_dps', 'gyro_y_dps', 'gyro_z_dps'}.issubset(df_feat.columns):
        df_feat['gyro_mag_dps'] = np.sqrt(
            df_feat['gyro_x_dps']**2 + df_feat['gyro_y_dps']**2 + df_feat['gyro_z_dps']**2
        )

    # 2. Acceleration Rolling Window Features
    if 'accel_mag_g' in df_feat.columns:
        df_feat['accel_mag_mean'] = df_feat['accel_mag_g'].rolling(window=window_size, min_periods=1).mean()
        df_feat['accel_mag_std']  = df_feat['accel_mag_g'].rolling(window=window_size, min_periods=1).std().fillna(0.0)
        df_feat['accel_mag_rms']  = compute_rolling_rms(df_feat['accel_mag_g'], window=window_size, min_periods=1)
        df_feat['accel_mag_max']  = df_feat['accel_mag_g'].rolling(window=window_size, min_periods=1).max()
        df_feat['accel_mag_min']  = df_feat['accel_mag_g'].rolling(window=window_size, min_periods=1).min()

    # 3. Gyroscope Rolling Window Features
    if 'gyro_mag_dps' in df_feat.columns:
        df_feat['gyro_mag_mean'] = df_feat['gyro_mag_dps'].rolling(window=window_size, min_periods=1).mean()
        df_feat['gyro_mag_std']  = df_feat['gyro_mag_dps'].rolling(window=window_size, min_periods=1).std().fillna(0.0)
        df_feat['gyro_mag_rms']  = compute_rolling_rms(df_feat['gyro_mag_dps'], window=window_size, min_periods=1)
        df_feat['gyro_mag_max']  = df_feat['gyro_mag_dps'].rolling(window=window_size, min_periods=1).max()
        df_feat['gyro_mag_min']  = df_feat['gyro_mag_dps'].rolling(window=window_size, min_periods=1).min()

    # 4. Per-Axis Vibration / Jitter Indicators
    if 'accel_z_g' in df_feat.columns:
        df_feat['accel_z_std'] = df_feat['accel_z_g'].rolling(window=window_size, min_periods=1).std().fillna(0.0)

    if 'gyro_z_dps' in df_feat.columns:
        df_feat['gyro_z_std'] = df_feat['gyro_z_dps'].rolling(window=window_size, min_periods=1).std().fillna(0.0)

    # 5. Temperature / Humidity Change Rates (First Differences)
    if 'temperature_c' in df_feat.columns:
        df_feat['temp_change_rate'] = df_feat['temperature_c'].diff().fillna(0.0)

    if 'humidity_percent' in df_feat.columns:
        df_feat['humidity_change_rate'] = df_feat['humidity_percent'].diff().fillna(0.0)

    return df_feat


if __name__ == "__main__":
    # Internal validation test
    dummy_data = {
        'timestamp_ms': [1000, 2000, 3000, 4000, 5000],
        'temperature_c': [25.0, 25.1, 25.2, 25.2, 25.3],
        'humidity_percent': [50.0, 50.0, 49.9, 49.8, 49.7],
        'accel_x_g': [0.01, 0.02, -0.01, 0.03, 0.00],
        'accel_y_g': [-0.02, 0.00, 0.01, -0.01, 0.02],
        'accel_z_g': [1.00, 1.01, 0.99, 1.02, 1.00],
        'gyro_x_dps': [0.1, 0.2, 0.0, -0.1, 0.1],
        'gyro_y_dps': [0.5, 0.4, 0.6, 0.5, 0.5],
        'gyro_z_dps': [0.3, 0.3, 0.2, 0.4, 0.3],
    }
    test_df = pd.DataFrame(dummy_data)
    out_df = extract_features(test_df, window_size=3)
    print(f"Extraction test passed! Output shape: {out_df.shape}")
    print("Extracted Feature Columns:")
    for col in out_df.columns:
        print(f" - {col}")
