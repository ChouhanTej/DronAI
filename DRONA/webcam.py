"""
Anti-Drone Detection System - Standalone Real-time Webcam Detector
Executes YOLO object detection on Mac camera feed (index 0), drawing bounding boxes,
class labels, confidence scores, real-time FPS, and a prominent drone alert banner.

Run command:
    .venv/bin/python webcam.py
"""

import time
import sys
from pathlib import Path
import cv2

# Add current directory to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.detector import YOLOObjectDetector


def main():
    print("=" * 60)
    print("      SIH ANTI-DRONE SYSTEM — WEBCAM DETECTION       ")
    print("=" * 60)

    model_path = PROJECT_ROOT / "models" / "best.pt"
    if not model_path.exists():
        print(f"Error: Model not found at {model_path}.")
        return

    # Initialize YOLO Detector wrapper
    try:
        detector = YOLOObjectDetector(model_path=model_path, confidence_threshold=0.25)
    except Exception as e:
        print(f"Failed to initialize detector: {e}")
        return

    # Open Mac Webcam (Index 0)
    print("Opening Mac webcam (Index 0)...")
    cap = cv2.VideoCapture(0)

    # Set Resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    if not cap.isOpened():
        print("\n" + "!" * 60)
        print("ERROR: Could not access Mac webcam (cv2.VideoCapture(0)).")
        print("Please check camera permissions in macOS System Settings.")
        print("!" * 60 + "\n")
        return

    print("\nLive webcam feed started!")
    print("Press 'q' or 'ESC' in the window to quit.\n")

    # Color palette (BGR)
    COLOR_DRONE = (0, 0, 230)        # Bright Red/Magenta for Drone
    COLOR_AIRPLANE = (255, 200, 0)   # Bright Cyan for AirPlane
    COLOR_HELICOPTER = (0, 220, 255) # Bright Yellow for Helicopter
    COLOR_DEFAULT = (0, 255, 0)      # Green

    prev_time = time.time()
    fps = 0.0

    window_title = "Anti-Drone System - Real-time Webcam Detection"
    cv2.namedWindow(window_title, cv2.WINDOW_NORMAL)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret or frame is None:
            print("Failed to capture frame from webcam.")
            break

        # Calculate FPS
        curr_time = time.time()
        dt = curr_time - prev_time
        if dt > 0:
            fps = 0.8 * fps + 0.2 * (1.0 / dt)
        prev_time = curr_time

        # Run YOLO inference
        detections = detector.detect(frame)

        drone_detected = False
        drone_count = 0

        for det in detections:
            is_drone = det.class_id == 1 or det.class_name.lower() == "drone"
            is_airplane = det.class_id == 0 or "airplane" in det.class_name.lower()
            is_helicopter = det.class_id == 2 or "helicopter" in det.class_name.lower()

            if is_drone:
                drone_detected = True
                drone_count += 1
                box_color = COLOR_DRONE
                thickness = 3
                label_str = f"⚠️ DRONE: {det.confidence*100:.1f}%"
            elif is_airplane:
                box_color = COLOR_AIRPLANE
                thickness = 2
                label_str = f"AIRPLANE: {det.confidence*100:.1f}%"
            elif is_helicopter:
                box_color = COLOR_HELICOPTER
                thickness = 2
                label_str = f"HELICOPTER: {det.confidence*100:.1f}%"
            else:
                box_color = COLOR_DEFAULT
                thickness = 2
                label_str = f"{det.class_name.upper()}: {det.confidence*100:.1f}%"

            # Draw bounding box
            cv2.rectangle(frame, (det.x1, det.y1), (det.x2, det.y2), box_color, thickness)

            # Label box background
            (w, h), _ = cv2.getTextSize(label_str, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(frame, (det.x1, max(det.y1 - 25, 0)), (det.x1 + w + 10, det.y1), box_color, -1)
            cv2.putText(
                frame,
                label_str,
                (det.x1 + 5, max(det.y1 - 7, 12)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )

        # Top alert banner when Drone is detected
        if drone_detected:
            cv2.rectangle(frame, (0, 0), (frame.shape[1], 45), (0, 0, 200), -1)
            alert_text = f"🚨 ALERT: {drone_count} DRONE(S) DETECTED! 🚨"
            (tw, th), _ = cv2.getTextSize(alert_text, cv2.FONT_HERSHEY_SIMPLEX, 0.85, 2)
            tx = (frame.shape[1] - tw) // 2
            cv2.putText(
                frame, alert_text, (tx, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (255, 255, 255), 2, cv2.LINE_AA
            )

        # Draw FPS overlay box
        fps_text = f"FPS: {fps:.1f}"
        cv2.rectangle(frame, (10, frame.shape[0] - 45), (150, frame.shape[0] - 10), (20, 20, 20), -1)
        cv2.rectangle(frame, (10, frame.shape[0] - 45), (150, frame.shape[0] - 10), (0, 255, 0), 1)
        cv2.putText(
            frame, fps_text, (20, frame.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2, cv2.LINE_AA
        )

        # Show frame
        cv2.imshow(window_title, frame)

        # Keyboard quit handling
        key = cv2.waitKey(1) & 0xFF
        if key in (ord('q'), ord('Q'), 27):
            print("Quit requested by user.")
            break

    cap.release()
    cv2.destroyAllWindows()
    print("Webcam feed stopped cleanly.")


if __name__ == "__main__":
    main()
