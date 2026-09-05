"""
SIH Anti-Drone System - Main Integrated Tracking Application
Integrates Webcam input, YOLO object detection, multi-drone tracking with persistent IDs,
trajectory rendering, target position error calculation, and simulated Pan/Tilt controller.

Run command:
    .venv/bin/python tracker.py --source 0
"""

import argparse
import sys
import time
import threading
from pathlib import Path
from typing import Optional, List, Tuple, Dict
import cv2
import numpy as np

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.detector import YOLOObjectDetector
from src.tracker import DroneTracker, TrackedDrone
from src.target import TargetAnalyzer, TargetTelemetry
from src.pantilt import (
    SimulatedPanTiltController,
    ESP32PanTiltController,
)

# Configurable Target Selection Policy: "highest_confidence", "largest", "closest_to_center"
TARGET_POLICY = "highest_confidence"

class LatestFrameCapture:
    """
    Continuously drains a video/MJPEG source in a background thread.

    Only the newest decoded frame is retained.
    Older frames are intentionally discarded so YOLO does not
    process a backlog of stale ESP32-CAM frames.
    """

    def __init__(self, source):
        self.source = source
        self.cap = cv2.VideoCapture(source)

        # Some OpenCV backends honor this, some do not.
        # The background reader is still the main anti-buffering mechanism.
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open video source: {source}")

        self._frame = None
        self._frame_id = 0
        self._timestamp = 0.0

        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        self._running = True

        self._thread = threading.Thread(
            target=self._reader_loop,
            name="LatestFrameCapture",
            daemon=True,
        )
        self._thread.start()

    def _reader_loop(self):
        while self._running:
            ok, frame = self.cap.read()

            if not ok or frame is None:
                if not self._running:
                    break

                time.sleep(0.01)
                continue

            timestamp = time.monotonic()

            with self._condition:
                self._frame = frame
                self._timestamp = timestamp
                self._frame_id += 1
                self._condition.notify_all()

    def read(self, last_frame_id=-1, timeout=1.0):
        """
        Wait for a frame newer than last_frame_id.

        Returns:
            ok, frame, frame_id, frame_timestamp
        """
        deadline = time.monotonic() + timeout

        with self._condition:
            while self._running and self._frame_id <= last_frame_id:
                remaining = deadline - time.monotonic()

                if remaining <= 0:
                    return False, None, last_frame_id, 0.0

                self._condition.wait(timeout=remaining)

            if self._frame is None:
                return False, None, last_frame_id, 0.0

            return (
                True,
                self._frame.copy(),
                self._frame_id,
                self._timestamp,
            )

    def stop(self):
        self._running = False

        with self._condition:
            self._condition.notify_all()

        self.cap.release()

        if self._thread.is_alive():
            self._thread.join(timeout=1.0)

class IntegratedTrackerApp:
    """Integrated Drone Detection, Tracking, and Pan/Tilt Telemetry Application."""

    def __init__(self, source: str = "0", model_path: Optional[Path] = None, policy: str = TARGET_POLICY):
        self.source_arg = source
        self.policy = policy
        self.model_path = model_path if model_path else PROJECT_ROOT / "models" / "best.pt"

        self.detector = YOLOObjectDetector(model_path=self.model_path, confidence_threshold=0.25)
        self.drone_tracker = DroneTracker(max_lost_frames=15)
        self.target_analyzer = TargetAnalyzer(dead_zone_x=50, dead_zone_y=50)
        self.pantilt_controller = ESP32PanTiltController(
            esp32_ip="192.168.4.1",
            pan_invert=False,
            tilt_invert=False,
        )

        self.fps = 0.0

    def select_primary_target(self, tracked_drones: list, frame_w: int, frame_h: int) -> Optional[TrackedDrone]:
        """Selects primary target drone according to policy."""
        if not tracked_drones:
            return None

        if self.policy == "highest_confidence":
            return max(tracked_drones, key=lambda d: d.confidence)
        elif self.policy == "largest":
            return max(tracked_drones, key=lambda d: (d.x2 - d.x1) * (d.y2 - d.y1))
        elif self.policy == "closest_to_center":
            cx_f, cy_f = frame_w / 2.0, frame_h / 2.0
            return min(tracked_drones, key=lambda d: np.hypot(d.center_x - cx_f, d.center_y - cy_f))
        else:
            return tracked_drones[0]

    def run(self):
        source_is_cam = self.source_arg.isdigit()
        cap_source = int(self.source_arg) if source_is_cam else self.source_arg

        try:
            cap = LatestFrameCapture(cap_source)
        except RuntimeError as exc:
            print(f"Error: {exc}")
            return

        last_frame_id = -1

        window_name = "Anti-Drone System - Multi-Drone Tracking & Targeting"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

        prev_time = time.time()
        print("\n" + "=" * 60)
        print("     SIH ANTI-DRONE INTEGRATED TRACKING APPLICATION      ")
        print("=" * 60)
        print(f"Source: {self.source_arg} | Target Policy: {self.policy}")
        print("Press 'q' or 'ESC' to exit.\n")

        while True:
            ret, frame, frame_id, frame_timestamp = cap.read(
                last_frame_id=last_frame_id,
                timeout=2.0,
            )

            if not ret or frame is None:
                print("Warning: no new frame received.")
                continue

            last_frame_id = frame_id

            frame_age_ms = (
                time.monotonic() - frame_timestamp
    ) * 1000.0

            curr_time = time.time()
            dt = curr_time - prev_time
            if dt > 0:
                self.fps = 0.85 * self.fps + 0.15 * (1.0 / dt)
            prev_time = curr_time

            h, w, _ = frame.shape
            frame_center = (w // 2, h // 2)

            # 1. Run YOLO inference
            all_detections = self.detector.detect(frame)

            # 2. Track ONLY Drones with persistent IDs
            active_drones = self.drone_tracker.update(all_detections)

            # 3. Select primary target drone
            primary_drone = self.select_primary_target(active_drones, w, h)
            telemetry: Optional[TargetTelemetry] = None

            if primary_drone:
                telemetry = self.target_analyzer.analyze(
                    primary_drone,
                    w,
                    h,
                )
                if primary_drone.lost_frames == 0:
                    self.pantilt_controller.update(
                        telemetry.pan_direction,
                        telemetry.tilt_direction,
                        telemetry.error_x,
                        telemetry.error_y,
                    )

            # --- VISUALIZATION OVERLAYS ---

            # Center Crosshair & Reticle
            cv2.line(frame, (frame_center[0], 0), (frame_center[0], h), (0, 255, 255), 1)
            cv2.line(frame, (0, frame_center[1]), (w, frame_center[1]), (0, 255, 255), 1)
            cv2.circle(frame, frame_center, 6, (0, 255, 255), 1)
            cv2.circle(frame, frame_center, 2, (0, 255, 255), -1)

            # Draw non-drone detections lightly
            for det in all_detections:
                if det.class_id != 1 and "drone" not in det.class_name.lower():
                    cv2.rectangle(frame, (det.x1, det.y1), (det.x2, det.y2), (255, 180, 0), 1)
                    cv2.putText(
                        frame,
                        f"{det.class_name} {det.confidence:.2f}",
                        (det.x1, max(det.y1 - 5, 15)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.45,
                        (255, 180, 0),
                        1,
                    )

            # Draw all tracked drones
            for drone in active_drones:
                is_primary = primary_drone and (drone.track_id == primary_drone.track_id)
                box_color = (0, 0, 255) if is_primary else (0, 165, 255)
                thickness = 3 if is_primary else 2

                # Bounding box
                cv2.rectangle(frame, (drone.x1, drone.y1), (drone.x2, drone.y2), box_color, thickness)

                # Center dot
                cx, cy = int(drone.center_x), int(drone.center_y)
                cv2.circle(frame, (cx, cy), 4, box_color, -1)

                # Label
                label_text = f"{drone.label} ({drone.confidence*100:.0f}%)"
                cv2.putText(
                    frame,
                    label_text,
                    (drone.x1, max(drone.y1 - 8, 18)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    box_color,
                    2,
                )

                # Trajectory path (last 30 positions)
                points = list(drone.history)
                for i in range(1, len(points)):
                    if points[i - 1] is None or points[i] is None:
                        continue
                    cv2.line(frame, points[i - 1], points[i], (0, 255, 0), 2)

            # Vector line from frame center to primary target center
            if primary_drone and telemetry:
                cv2.line(frame, frame_center, telemetry.drone_center, (0, 255, 0), 2, cv2.LINE_AA)

            # Top Drone Alert Banner
            if active_drones:
                cv2.rectangle(frame, (0, 0), (w, 40), (0, 0, 200), -1)
                alert_text = f"🚨 ALERT: {len(active_drones)} DRONE(S) DETECTED! 🚨"
                (tw, _), _ = cv2.getTextSize(alert_text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
                cv2.putText(frame, alert_text, ((w - tw) // 2, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

            # OSD Dashboard Side Panel
            # self._render_osd_panel(frame, active_drones, telemetry, w, h)

            cv2.putText(
                frame,
                f"Frame age: {frame_age_ms:.0f} ms",
                (10, h - 15),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 255),
                1,
            )

            cv2.imshow(window_name, frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord('q'), ord('Q'), 27):
                break

        cap.stop()
        cv2.destroyAllWindows()
        print("Tracking application terminated cleanly.")

    def _render_osd_panel(
        self, frame: np.ndarray, drones: list, telemetry: Optional[TargetTelemetry], width: int, height: int
    ):
        """Renders OSD telemetry dashboard."""
        panel_w = 320
        panel_h = 240
        margin = 10

        sub_img = frame[margin : margin + panel_h, margin : margin + panel_w]
        black_bg = np.full_like(sub_img, (20, 20, 20))
        blend = cv2.addWeighted(sub_img, 0.25, black_bg, 0.75, 0)
        frame[margin : margin + panel_h, margin : margin + panel_w] = blend

        cv2.rectangle(frame, (margin, margin), (margin + panel_w, margin + panel_h), (0, 255, 255), 1)

        lines = [
            ("DRONE DETECTION SYSTEM", (0, 255, 255), True),
            (f"FPS: {self.fps:.1f} | Tracked Drones: {len(drones)}", (240, 240, 240), False),
            ("-----------------------------------", (100, 100, 100), False),
        ]

        if telemetry:
            lines.extend([
                (f"TARGET: {telemetry.label}", (0, 0, 255), True),
                (f"Confidence: {telemetry.confidence*100:.1f}%", (240, 240, 240), False),
                (f"Drone Center: {telemetry.drone_center}", (240, 240, 240), False),
                (f"Frame Center: {telemetry.frame_center}", (240, 240, 240), False),
                (f"Error X: {telemetry.error_x:+d} px", (240, 240, 240), False),
                (f"Error Y: {telemetry.error_y:+d} px", (240, 240, 240), False),
                (f"PAN: {telemetry.pan_direction} | TILT: {telemetry.tilt_direction}", (0, 255, 0), True),
            ])
        else:
            lines.extend([
                ("STATUS: SEARCHING...", (150, 150, 150), False),
                ("PAN: CENTER | TILT: CENTER", (150, 150, 150), False),
            ])

        y_offset = margin + 20
        for text, color, bold in lines:
            thickness = 2 if bold else 1
            font_scale = 0.46 if bold else 0.43
            cv2.putText(frame, text, (margin + 10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)
            y_offset += 19


def main():
    parser = argparse.ArgumentParser(description="SIH Anti-Drone Tracking System")
    parser.add_argument("--source", type=str, default="0", help="Video source (0 for webcam or video file path)")
    args = parser.parse_args()

    app = IntegratedTrackerApp(source=args.source)
    app.run()


if __name__ == "__main__":
    main()
