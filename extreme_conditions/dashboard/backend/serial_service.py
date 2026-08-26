"""
Extreme Conditions Failure Risk Dashboard - Serial & Hardware Service
Manages ESP32 serial communication, hardware connection state tracking,
and Demo Mode dataset replay logic.
"""

import asyncio
import os
import sys
import time
import pandas as pd
import numpy as np

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    serial = None

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))


def find_esp32_port():
    """Finds potential ESP32 serial port device path strictly matching USB-to-UART bridges."""
    if serial is None:
        return None
    ports = serial.tools.list_ports.comports()
    for port in ports:
        device = port.device.lower()
        desc = port.description.lower()
        # Strictly ignore macOS system debug/bluetooth pseudo ports
        if "debug-console" in device or "bluetooth" in device or "wlan" in device:
            continue
        if "slab" in device or "slab" in desc or "cp210" in desc or "usbserial" in device or "usbmodem" in device or "ch340" in device:
            return port.device
    return None


class SerialHardwareService:
    def __init__(self, port=None, baud=115200):
        self.port = port or "/dev/cu.SLAB_USBtoUART"
        self.baud = baud

        self.ser = None
        self.is_connected = False
        self.demo_mode = False
        self.last_connect_attempt = 0

        self.dht11_online = False
        self.mpu6050_online = False

        self.demo_df = None
        self.demo_idx = 0
        self._load_demo_dataset()

    def _load_demo_dataset(self):
        """Loads demo dataset for playback."""
        demo_path = os.path.join(PROJECT_ROOT, "data", "raw", "sensor_data_2026-08-26_110040.csv")
        if os.path.exists(demo_path):
            self.demo_df = pd.read_csv(demo_path)
            print(f"[SERIAL SERVICE] Loaded Demo dataset '{os.path.basename(demo_path)}' ({len(self.demo_df)} rows).")

    def connect(self):
        """Attempts to open serial connection to ESP32 with throttling."""
        if self.demo_mode:
            self.is_connected = True
            self.dht11_online = True
            self.mpu6050_online = True
            return True

        if serial is None:
            self.is_connected = False
            self.dht11_online = False
            self.mpu6050_online = False
            return False

        now = time.time()
        if now - self.last_connect_attempt < 2.0:
            return False
        self.last_connect_attempt = now

        active_port = self.port
        if not os.path.exists(active_port):
            auto_p = find_esp32_port()
            if auto_p:
                active_port = auto_p
            else:
                self.is_connected = False
                self.dht11_online = False
                self.mpu6050_online = False
                return False

        try:
            if self.ser and self.ser.is_open:
                try:
                    self.ser.close()
                except Exception:
                    pass
            self.ser = serial.Serial(active_port, self.baud, timeout=1.0)
            time.sleep(0.5)
            self.is_connected = True
            self.dht11_online = True
            self.mpu6050_online = True
            print(f"[SERIAL SERVICE] Connected to ESP32 on port: {active_port}")
            return True
        except Exception as e:
            self.is_connected = False
            self.dht11_online = False
            self.mpu6050_online = False
            self.ser = None
            return False

    def disconnect(self):
        """Closes serial connection safely."""
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except Exception:
                pass
        self.ser = None
        self.is_connected = False
        self.dht11_online = False
        self.mpu6050_online = False

    def read_next_sample(self) -> dict:
        """
        Reads next sensor sample dictionary from live ESP32 serial or demo dataset.
        Returns None if no sample is ready or port is disconnected.
        """
        if self.demo_mode:
            if self.demo_df is None or len(self.demo_df) == 0:
                return None

            row = self.demo_df.iloc[self.demo_idx]
            self.demo_idx = (self.demo_idx + 1) % len(self.demo_df)
            
            sample = row.to_dict()
            sample["is_demo"] = True
            sample["esp32_connected"] = True
            sample["dht11_online"] = True
            sample["mpu6050_online"] = True
            return sample

        if not self.is_connected or not self.ser:
            if not self.connect():
                return None

        try:
            line = self.ser.readline().decode("utf-8", errors="replace").strip()
            if not line:
                return None

            if line.startswith("ERROR"):
                if "MPU6050" in line:
                    self.mpu6050_online = False
                if "DHT11" in line:
                    self.dht11_online = False
                return None

            if line.startswith("timestamp_ms"):
                return None

            parts = line.split(",")
            if len(parts) == 9:
                try:
                    ts, temp, hum, ax, ay, az, gx, gy, gz = parts
                    
                    temp_f = float(temp) if temp.lower() != 'nan' else np.nan
                    hum_f = float(hum) if hum.lower() != 'nan' else np.nan

                    self.dht11_online = not np.isnan(temp_f) and not np.isnan(hum_f)
                    self.mpu6050_online = True

                    sample = {
                        "timestamp_ms": float(ts),
                        "temperature_c": temp_f if not np.isnan(temp_f) else 25.0,
                        "humidity_percent": hum_f if not np.isnan(hum_f) else 50.0,
                        "accel_x_g": float(ax),
                        "accel_y_g": float(ay),
                        "accel_z_g": float(az),
                        "gyro_x_dps": float(gx),
                        "gyro_y_dps": float(gy),
                        "gyro_z_dps": float(gz),
                        "is_demo": False,
                        "esp32_connected": True,
                        "dht11_online": self.dht11_online,
                        "mpu6050_online": self.mpu6050_online
                    }
                    return sample
                except ValueError:
                    return None

        except Exception as e:
            print(f"[SERIAL SERVICE WARNING] Serial read error: {e}")
            self.disconnect()
            return None

        return None
