# SIH Anti-Drone Detection & Tracking System

A modular, real-time computer vision system built with Python, OpenCV, PyTorch, and Ultralytics YOLOv8 for detection, persistent multi-drone tracking, 2D target displacement calculation, and simulated Pan/Tilt controller telemetry.

> **Project Scope Notice:** This system is strictly limited to visual object detection, tracking, and camera direction/servo error calculation. It contains NO weapon systems, firing mechanisms, countermeasures, jamming, or autonomous interception capabilities.

---

## 1. Project Purpose

The SIH Anti-Drone System provides real-time aerial surveillance using camera feeds (Mac webcam or external video feeds). It detects drones, airplanes, and helicopters, isolates drones for persistent multi-object tracking (`Drone #1`, `Drone #2`), calculates tracking error relative to the frame center, and emits Pan/Tilt servo adjustment commands (`PAN: LEFT/RIGHT/CENTER`, `TILT: UP/DOWN/CENTER`).

---

## 2. Directory & Architecture Structure

```text
parent/
│
├── drona/                                # Main Application Project
│   ├── models/
│   │   └── best.pt                       # Trained YOLOv8 model weights
│   │
│   ├── src/                              # Core Modular Code base
│   │   ├── __init__.py
│   │   ├── detector.py                   # YOLO inference & device auto-selection (MPS/CPU)
│   │   ├── tracker.py                    # Multi-drone tracking with persistent IDs & trajectory
│   │   ├── target.py                     # Target center error calculation, deadzones, & PAN/TILT
│   │   └── pantilt.py                    # Modular simulated Pan/Tilt controller
│   │
│   ├── tests/
│   │   └── test_system.py                # Comprehensive unit test suite
│   │
│   ├── webcam.py                         # Standalone real-time detection script
│   ├── tracker.py                        # Main integrated tracking & OSD dashboard app
│   ├── video_test.py                     # Video file testing & predictions export tool
│   ├── requirements.txt                  # Python dependencies
│   ├── README.md                         # Documentation
│   ├── .venv -> venv                     # Symlink for .venv/bin/python command support
│   └── venv/                             # Virtual environment
│
└── drone-detection-new.v5-new-train-yolov8/ # Cleaned Kaggle Dataset (External Input)
    ├── data.yaml                         # Dataset YAML configuration
    ├── train/                            # ~10,799 training images & labels
    ├── valid/                            # ~603 validation images & labels
    ├── test/                             # ~596 test images & labels
    └── runs/detect/train/weights/best.pt # Original trained model weights
```

---

## 3. Dataset & Trained Model Details

- **Dataset Location**: `../drone-detection-new.v5-new-train-yolov8/` relative to `drona/`
- **Dataset Classes (`nc: 3`)**:
  - `0`: **AirPlane**
  - `1`: **Drone**
  - `2`: **Helicopter**
- **Dataset Rules**: The original dataset folder and `data.yaml` remain completely untouched.
- **Model Weights Location**: `drona/models/best.pt` (copied from `runs/detect/train/weights/best.pt`).
- **Model Test Metrics**:
  - **mAP50**: 97.46%
  - **Precision**: 94.48%
  - **Recall**: 94.70%
  - **Drone Class mAP50**: 94.70%

---

## 4. Virtual Environment & Setup

1. **Navigate to `drona/`**:
   ```bash
   cd drona
   ```

2. **Activate Virtual Environment**:
   ```bash
   source .venv/bin/activate
   ```

3. **Install Dependencies** (if creating environment from scratch):
   ```bash
   pip install -r requirements.txt
   ```

---

## 5. How to Run

### A. Real-Time Webcam Detection (Phase 5)
Runs standalone YOLO object detection on Mac camera index 0 with bounding boxes, FPS, and red alert banner.
```bash
.venv/bin/python webcam.py
```

### B. Main Integrated Multi-Drone Tracking (Phases 7 - 11)
Runs detection, persistent multi-drone tracking (`Drone #1`, `Drone #2`), trajectory rendering, displacement vector lines, and simulated Pan/Tilt commands.
```bash
.venv/bin/python tracker.py --source 0
```

### C. Video File Testing (Phase 12)
Processes a pre-recorded video file, runs tracking, and exports annotated MP4 predictions to `runs/detect/video_predictions/`.
```bash
.venv/bin/python video_test.py --source path/to/drone_test.mp4
```

### D. Run Unit Test Suite (Phase 13)
Executes all automated tests for model loading, class index mapping, center math, dead-zones, PAN/TILT directions, and tracking IDs.
```bash
.venv/bin/python -m unittest discover -s tests
```

---

## 6. Target Selection & Pan/Tilt Logic

- **Dead Zones**: `DEAD_ZONE_X = 50` px, `DEAD_ZONE_Y = 50` px around frame center.
- **Direction Rules**:
  - **PAN**: `LEFT` (`error_x < -50`), `RIGHT` (`error_x > 50`), `CENTER`
  - **TILT**: `UP` (`error_y < -50`), `DOWN` (`error_y > 50`), `CENTER`
- **Target Selection Policy**: `TARGET_POLICY = "highest_confidence"` (configurable to `"largest"` or `"closest_to_center"`).

---

## 7. Future ESP32 Pan/Tilt Hardware Integration

In Phase 2 of hardware integration, `src/pantilt.py` can be updated to transmit serial commands over USB/UART to an ESP32 controlling two 180° pan/tilt servos:
```text
PAN:LEFT;TILT:UP
PAN:CENTER;TILT:CENTER
```

---

## 8. Current Limitations & Next Steps

- **Current Prototype Scope**: Visual object tracking and simulated servo commands only. No physical hardware connected yet.
- **Next Steps**:
  1. Flash ESP32 firmware with servo control library.
  2. Implement PySerial interface in `src/pantilt.py`.
  3. Mount camera onto physical pan/tilt servo gimbal.
