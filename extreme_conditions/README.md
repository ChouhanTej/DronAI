# Extreme Conditions Sensing & Failure Risk Monitoring Subsystem

This module forms the complete **Extreme Conditions Sensing & Failure Risk Monitoring Subsystem** for the drone detection platform. It provides hardware sensor logging (ESP32 + DHT11 + MPU6050), data preprocessing & feature extraction, an Isolation Forest unsupervised anomaly detection engine, and a real-time web dashboard.

> [!NOTE]
> This module is completely decoupled from the drone detection/camera software in `DRONA/` and operates as an independent subsystem.

---

## Subsystem Architecture & Modules

```text
extreme_conditions/
├── firmware/           # ESP32 C++ Sensor Logger Firmware (DHT11 on D4, MPU6050 on D21/D22)
├── tools/              # Serial Logger CLI tool (pyserial)
├── data/
│   ├── raw/            # Timestamped raw telemetry CSV datasets
│   ├── processed/      # Processed sensor dataset with 25 engineered features
│   └── reports/        # Markdown reports and visualization plots (data reports & anomaly reports)
├── ml/
│   ├── model/          # Isolation Forest model bundle (joblib) & feature_config.json
│   ├── train_anomaly_model.py
│   ├── predict_anomaly.py
│   ├── live_anomaly_monitor.py
│   └── README.md
├── dashboard/          # Real-time Web Dashboard (FastAPI Backend + React/Vite Frontend)
│   ├── backend/
│   ├── frontend/
│   └── README.md
└── README.md
```

---

## 1. Hardware Connections & Pinout Mapping

**Target Controller:** ESP32 Dev Module (ESP32-D0WD-V3)

| Sensor | Sensor Pin | ESP32 Pin | GPIO / Function |
|--------|------------|-----------|-----------------|
| **DHT11** | VCC | 3V3 / D3V3 | 3.3V Power |
| **DHT11** | GND | GND | Ground |
| **DHT11** | OUT / DATA | D4 | GPIO 4 |
| **MPU6050** | VCC | 3V3 | 3.3V Power |
| **MPU6050** | GND | GND | Ground |
| **MPU6050** | SDA | D21 | GPIO 21 (I2C SDA) |
| **MPU6050** | SCL | D22 | GPIO 22 (I2C SCL) |

---

## 2. Required Arduino Libraries

Before compiling the firmware, install these official Arduino libraries:

1. **Adafruit MPU6050** (by Adafruit)
2. **DHT sensor library** (by Adafruit)
3. **Adafruit Unified Sensor** (by Adafruit - dependency)
4. **Adafruit BusIO** (by Adafruit - dependency)

### Installation Steps in Arduino IDE:
1. Open Arduino IDE.
2. Go to **Tools** -> **Manage Libraries...** (or press `Cmd + Shift + I` on macOS).
3. Search for `Adafruit MPU6050` and click **Install**. Click **Install All** when prompted to automatically include `Adafruit Unified Sensor` and `Adafruit BusIO`.
4. Search for `DHT sensor library` by Adafruit and click **Install**.

---

## 3. How to Upload Firmware to ESP32

1. Connect your ESP32 board to your computer using a Micro-USB/USB-C data cable.
2. Open `extreme_conditions/firmware/sensor_logger/sensor_logger.ino` in Arduino IDE.
3. Go to **Tools** -> **Board** -> **ESP32 Arduino** -> select **ESP32 Dev Module**.
4. Go to **Tools** -> **Port** -> select your ESP32 port (e.g. `/dev/cu.usbserial-1410` or `/dev/cu.SLAB_USBtoUART`).
5. Set upload speed to **115200** or default **921600**.
6. Click the **Upload** button (`Cmd + U`).
   *(If upload gets stuck on `Connecting...`, press and hold the **BOOT** button on the ESP32 board until uploading starts).*

---

## 4. How to Open Serial Monitor

1. Open Arduino IDE.
2. Go to **Tools** -> **Serial Monitor** (or press `Cmd + Shift + M`).
3. Set the baud rate dropdown in the bottom right corner to **115200 baud**.
4. Press the **EN / RST** button on the ESP32 to restart execution.
5. You should see the CSV header line followed by periodic sensor data.

---

## 5. CSV Output Column Definitions

The Serial stream outputs structured CSV lines using the following schema:

`timestamp_ms,temperature_c,humidity_percent,accel_x_g,accel_y_g,accel_z_g,gyro_x_dps,gyro_y_dps,gyro_z_dps`

| Column | Unit | Description |
|--------|------|-------------|
| `timestamp_ms` | milliseconds | Elapsed time since ESP32 startup (`millis()`) |
| `temperature_c` | °C | Ambient temperature reading from DHT11 |
| `humidity_percent` | % | Relative humidity percentage from DHT11 |
| `accel_x_g` | g | Acceleration along X-axis ($1\,g = 9.80665\,\text{m/s}^2$) |
| `accel_y_g` | g | Acceleration along Y-axis |
| `accel_z_g` | g | Acceleration along Z-axis |
| `gyro_x_dps` | °/s (dps) | Angular velocity around X-axis (Degrees per second) |
| `gyro_y_dps` | °/s (dps) | Angular velocity around Y-axis |
| `gyro_z_dps` | °/s (dps) | Angular velocity around Z-axis |

---

## 6. How to Run `serial_logger.py`

### Prerequisites:
Install `pyserial`:
```bash
pip install pyserial
```

### Usage Options:
Navigate to `extreme_conditions/tools/`:

```bash
cd extreme_conditions/tools
```

- **Auto-Detect Port & Record:**
  ```bash
  python3 serial_logger.py
  ```

- **Specify Explicit Port:**
  ```bash
  python3 serial_logger.py --port /dev/cu.usbserial-1410
  ```

- **List All Available Ports:**
  ```bash
  python3 serial_logger.py --list
  ```

---

## 7. How to Find the ESP32 Serial Port on macOS

In your macOS Terminal, list active serial devices:

```bash
ls /dev/cu.*
```

Common port naming patterns for ESP32 on macOS:
- `/dev/cu.usbserial-1410` or `/dev/cu.usbserial-1420` (FTDI / Silicon Labs CP210x drivers)
- `/dev/cu.SLAB_USBtoUART` (Silicon Labs CP2102 driver)
- `/dev/cu.wchusbserial1410` (CH340/CH341 USB-to-Serial chip)

Alternatively, run:
```bash
python3 extreme_conditions/tools/serial_logger.py --list
```

---

## 8. Starting and Stopping Data Collection

1. **Start Collection:** Run `serial_logger.py`. The logger will automatically connect to the ESP32 and create a timestamped file in `extreme_conditions/data/raw/`, e.g., `sensor_data_2026-08-26_153000.csv`.
2. **Stop Collection:** Press `Ctrl + C` in your Terminal. The logger gracefully catches the signal, flushes all unwritten buffers, closes the CSV file, and disconnects from the port cleanly.

---

## 9. Example CSV Output

```csv
timestamp_ms,temperature_c,humidity_percent,accel_x_g,accel_y_g,accel_z_g,gyro_x_dps,gyro_y_dps,gyro_z_dps
1000,29.40,62.00,0.02,-0.01,1.01,0.12,0.52,0.31
2000,29.50,62.00,0.03,-0.02,1.00,0.15,0.48,0.29
3000,29.50,61.80,0.01,-0.01,1.02,0.10,0.50,0.30
```

---

## 10. Troubleshooting Guide

### MPU6050 Not Detected
- **Symptom:** ESP32 outputs `ERROR: MPU6050 not detected!`.
- **Solution:**
  - Verify pin wiring: `SDA` to `GPIO 21`, `SCL` to `GPIO 22`, `VCC` to `3V3`, `GND` to `GND`.
  - Check if your MPU6050 module uses I2C address `0x68` or `0x69` (the firmware automatically tests both).
  - Ensure breadboard jumper wires have solid electrical contact.

### DHT11 Reading Failed / Outputs `nan`
- **Symptom:** Temperature or humidity outputs `nan`.
- **Solution:**
  - Verify `OUT` pin is wired to `GPIO 4`.
  - Check that DHT11 is powered from `3V3` (or `5V` if your module has an onboard voltage regulator).
  - Ensure sampling interval is $\ge 1$ second (DHT11 cannot be polled faster than once per second).

### Serial Port Unavailable / Access Denied
- **Symptom:** `serial_logger.py` reports `Permission denied` or `Resource busy`.
- **Solution:**
  - Close Arduino IDE's Serial Monitor (only one application can access a serial port at a time).
  - Ensure no other Python scripts or terminals are using the port.

### ESP32 Disconnected Mid-Run
- **Symptom:** Data stream stops unexpectedly.
- **Solution:**
  - `serial_logger.py` will catch the disconnection and preserve all data logged prior to unplugging.
  - Re-plug the USB cable (make sure to use a data USB cable, not a charging-only cable).
