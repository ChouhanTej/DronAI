"""
Anti-Drone Detection & Tracking System - Configuration Settings
"""

import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"
MODELS_DIR.mkdir(exist_ok=True)

# Camera Settings
CAMERA_INDEX = 0
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

# YOLO Detector Settings
MODEL_NAME = "yolo11n.pt"  # Lightweight YOLO11 model (auto-downloads if missing)
MODEL_PATH = os.path.join(MODELS_DIR, MODEL_NAME)
CONFIDENCE_THRESHOLD = 0.40
NMS_IOU_THRESHOLD = 0.45

# Target Selection & Tracking Settings
# Preferred target class name (e.g., "drone", "person", "cell phone").
# Set to None to dynamically pick the highest confidence / largest detection.
TARGET_CLASS = None
TARGET_LOCK = True
TRACKING_IOU_THRESHOLD = 0.3
TRACKING_DISTANCE_THRESHOLD = 150  # Max pixel distance between frames to maintain lock

# Center Alignment Deadzone (pixels)
# Target errors within this distance from center will be classified as "CENTER"
DEADZONE_PIXELS = 20

# Display & Visualization Options
WINDOW_TITLE = "Anti-Drone Detection System"
SHOW_FPS = True
SHOW_CROSSHAIR = True
SHOW_OSD_PANEL = True
SHOW_ALL_BOUNDING_BOXES = True

# UI Visual Colors (BGR Format)
COLOR_BACKGROUND_PANEL = (20, 20, 20)
COLOR_TEXT = (240, 240, 240)
COLOR_CROSSHAIR = (0, 255, 255)       # Yellow
COLOR_DETECTION_BOX = (255, 150, 0)   # Blue-orange accent
COLOR_TARGET_BOX = (0, 255, 0)        # Bright Neon Green
COLOR_TARGET_CENTER = (0, 0, 255)     # Bright Red
COLOR_FRAME_CENTER = (0, 255, 255)    # Yellow

# Servo / Pan-Tilt Control Settings (Future-Ready Phase 2 Defaults)
PAN_CENTER_ANGLE = 90
TILT_CENTER_ANGLE = 90
PAN_MIN_ANGLE = 0
PAN_MAX_ANGLE = 180
TILT_MIN_ANGLE = 0
TILT_MAX_ANGLE = 180
PID_KP_X = 0.05
PID_KP_Y = 0.05
