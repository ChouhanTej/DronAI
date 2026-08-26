#!/usr/bin/env python3
"""
Extreme Conditions Failure Prediction - Serial Logger Tool
Connects to ESP32 over serial, validates incoming CSV sensor data,
and logs structured readings to timestamped files in data/raw/.
"""

import argparse
import datetime
import os
import sys
import time

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    serial = None


EXPECTED_HEADER = "timestamp_ms,temperature_c,humidity_percent,accel_x_g,accel_y_g,accel_z_g,gyro_x_dps,gyro_y_dps,gyro_z_dps"
EXPECTED_COLUMN_COUNT = 9


def list_serial_ports():
    """List available serial ports on the system."""
    if serial is None:
        print("Error: 'pyserial' is not installed. Install via: pip install pyserial")
        return []
    return list(serial.tools.list_ports.comports())


def validate_csv_line(line: str) -> bool:
    """
    Validates if a serial output line is a valid 9-column CSV sensor measurement.
    Ignores non-CSV, header lines, error logs, and malformed strings.
    """
    line = line.strip()
    if not line or line.startswith("ERROR") or line.startswith("timestamp_ms"):
        return False

    parts = line.split(",")
    if len(parts) != EXPECTED_COLUMN_COUNT:
        return False

    # Verify all elements are numerical or 'nan'
    for part in parts:
        part_clean = part.strip().lower()
        if part_clean == "nan":
            continue
        try:
            float(part_clean)
        except ValueError:
            return False

    return True


def find_esp32_port():
    """Attempts to automatically discover potential ESP32 serial ports."""
    ports = list_serial_ports()
    esp32_ports = []
    for port in ports:
        device = port.device
        desc = port.description.lower()
        if any(keyword in device.lower() or keyword in desc for keyword in ["usbserial", "slab", "ch340", "cp210", "ftdi", "usbmodem", "esp32"]):
            esp32_ports.append(device)

    # On macOS, Silicon Labs CP2102 drivers create both /dev/cu.SLAB_USBtoUART and /dev/cu.usbserial-0001
    slab_ports = [p for p in esp32_ports if "SLAB_USBtoUART" in p]
    if slab_ports:
        return [slab_ports[0]], ports

    unique_ports = list(dict.fromkeys(esp32_ports))
    return unique_ports, ports


def main():
    parser = argparse.ArgumentParser(
        description="ESP32 Sensor Logger for Extreme Conditions Failure Prediction System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python serial_logger.py --list
  python serial_logger.py --port /dev/cu.usbserial-1410
  python serial_logger.py -p /dev/cu.SLAB_USBtoUART -b 115200
        """
    )
    parser.add_argument("-p", "--port", type=str, help="Serial port (e.g. /dev/cu.usbserial-1410 or COM3)")
    parser.add_argument("-b", "--baud", type=int, default=115200, help="Baud rate (default: 115200)")
    parser.add_argument("-o", "--output-dir", type=str, default=None, help="Directory to save raw CSV files")
    parser.add_argument("-l", "--list", action="store_true", help="List available serial ports and exit")
    parser.add_argument("--test", action="store_true", help="Run internal validation self-test")

    args = parser.parse_args()

    if args.test:
        print("[TEST] Running serial logger line validator self-test...")
        valid_line = "1000,29.40,62.00,0.02,-0.01,1.01,0.12,0.52,0.31"
        nan_line = "2000,nan,nan,0.03,-0.02,1.00,0.15,0.48,0.29"
        invalid_line = "ERROR: MPU6050 not detected!"
        header_line = EXPECTED_HEADER

        assert validate_csv_line(valid_line) == True, "Failed to validate valid line"
        assert validate_csv_line(nan_line) == True, "Failed to validate line with NaN"
        assert validate_csv_line(invalid_line) == False, "Failed to reject error line"
        assert validate_csv_line(header_line) == False, "Failed to reject header line"
        print("[TEST] All line validation tests passed successfully!")
        return

    if args.list:
        print("=== Available Serial Ports ===")
        ports = list_serial_ports()
        if not ports:
            print("No serial ports found or pyserial not installed.")
        else:
            for p in ports:
                print(f"  Port: {p.device} | Description: {p.description} | Hardware ID: {p.hwid}")
        return

    if serial is None:
        print("Error: 'pyserial' package is not installed. Run: pip install pyserial")
        sys.exit(1)

    port_name = args.port
    if not port_name:
        esp_ports, all_ports = find_esp32_port()
        if len(esp_ports) == 1:
            port_name = esp_ports[0]
            print(f"Auto-detected ESP32 serial port: {port_name}")
        elif len(all_ports) == 1:
            port_name = all_ports[0].device
            print(f"Using available serial port: {port_name}")
        else:
            print("Error: No serial port specified and could not auto-detect a unique ESP32 port.")
            print("\nAvailable ports:")
            for p in all_ports:
                print(f"  {p.device} ({p.description})")
            print("\nPlease specify port using --port / -p option, e.g.:")
            print("  python serial_logger.py --port /dev/cu.usbserial-1410")
            sys.exit(1)

    # Determine output raw directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, ".."))
    raw_data_dir = args.output_dir or os.path.join(project_root, "data", "raw")
    os.makedirs(raw_data_dir, exist_ok=True)

    # Generate timestamped filename
    timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    output_filename = f"sensor_data_{timestamp_str}.csv"
    output_filepath = os.path.join(raw_data_dir, output_filename)

    print("==================================================")
    print(" Extreme Conditions Failure Prediction - Logger")
    print("==================================================")
    print(f"Connecting to ESP32 on port: {port_name} @ {args.baud} baud...")

    try:
        ser = serial.Serial(port_name, args.baud, timeout=2.0)
        time.sleep(1.5)  # Allow ESP32 connection reboot/stabilize
        print("Connected to ESP32 successfully!")
    except Exception as e:
        print(f"Error: Failed to open serial port '{port_name}': {e}")
        print("Tip: Make sure Serial Monitor in Arduino IDE is closed and ESP32 USB cable is connected.")
        sys.exit(1)

    print("Recording started. Saving data to:")
    print(f"  -> {output_filepath}")
    print("Press Ctrl+C to stop recording safely.\n")

    sample_count = 0
    csv_file = None

    try:
        csv_file = open(output_filepath, "w", encoding="utf-8")
        csv_file.write(EXPECTED_HEADER + "\n")
        csv_file.flush()

        while True:
            raw_line = ser.readline().decode("utf-8", errors="replace").strip()
            if not raw_line:
                continue

            if validate_csv_line(raw_line):
                csv_file.write(raw_line + "\n")
                csv_file.flush()
                sample_count += 1

                parts = raw_line.split(",")
                ts, temp, hum, ax, ay, az, gx, gy, gz = parts
                print(f"[Sample #{sample_count:04d}] t={ts}ms | Temp={temp}°C | Hum={hum}% | Accel=({ax},{ay},{az})g | Gyro=({gx},{gy},{gz})dps")
            else:
                if raw_line.startswith("ERROR"):
                    print(f"\n[ESP32 SENSOR ERROR] {raw_line}")

    except KeyboardInterrupt:
        print("\nKeyboardInterrupt received.")
    except Exception as e:
        print(f"\nError reading serial stream: {e}")
    finally:
        print("--------------------------------------------------")
        print("Stopping recording...")
        if csv_file:
            csv_file.close()
        if 'ser' in locals() and ser and ser.is_open:
            ser.close()

        print("Recording stopped safely.")
        print(f"Total valid samples recorded: {sample_count}")
        print(f"File saved to: {output_filepath}")
        print("--------------------------------------------------")


if __name__ == "__main__":
    main()
