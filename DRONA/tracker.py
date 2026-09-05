"""
SIH Anti-Drone System - Integrated Tracking Application

Current demo architecture:

Laptop Webcam
      ↓
YOLO Drone Detection
      ↓
Persistent Drone Tracking
      ↓
Primary Target Selection
      ↓
Target X/Y Error
      ↓
ESP32 Wi-Fi HTTP
      ↓
MCPWM
      ↓
Pan / Tilt Servos

Run:

    python tracker.py --source 0
"""

import argparse
import sys
import time
import threading

from pathlib import Path
from typing import Optional

import cv2
import numpy as np


# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent

sys.path.insert(
    0,
    str(PROJECT_ROOT),
)


# ============================================================
# DRONAI MODULES
# ============================================================

from src.detector import YOLOObjectDetector

from src.tracker import (
    DroneTracker,
    TrackedDrone,
)

from src.target import (
    TargetAnalyzer,
    TargetTelemetry,
)

from src.pantilt import (
    ESP32PanTiltController,
)


# ============================================================
# TARGET POLICY
# ============================================================

TARGET_POLICY = "highest_confidence"


# ============================================================
# LOW-LATENCY VIDEO CAPTURE
# ============================================================

class LatestFrameCapture:
    """
    Continuously reads the camera in a background thread.

    Only the newest frame is retained.

    This prevents YOLO from processing a long queue of
    old frames.
    """

    def __init__(self, source):

        self.source = source

        self.cap = cv2.VideoCapture(
            source
        )

        # Some OpenCV backends respect this.
        self.cap.set(
            cv2.CAP_PROP_BUFFERSIZE,
            1,
        )

        if not self.cap.isOpened():

            raise RuntimeError(
                f"Could not open video source: {source}"
            )

        self._frame = None
        self._frame_id = 0
        self._timestamp = 0.0

        self._condition = (
            threading.Condition()
        )

        self._running = True

        self._thread = threading.Thread(
            target=self._reader_loop,
            name="LatestFrameCapture",
            daemon=True,
        )

        self._thread.start()

    # ========================================================
    # BACKGROUND CAMERA READER
    # ========================================================

    def _reader_loop(self):

        while self._running:

            ok, frame = self.cap.read()

            if (
                not ok
                or frame is None
            ):

                if not self._running:
                    break

                time.sleep(0.01)

                continue

            timestamp = (
                time.monotonic()
            )

            with self._condition:

                self._frame = frame

                self._timestamp = (
                    timestamp
                )

                self._frame_id += 1

                self._condition.notify_all()

    # ========================================================
    # GET NEWEST FRAME
    # ========================================================

    def read(
        self,
        last_frame_id=-1,
        timeout=1.0,
    ):

        deadline = (
            time.monotonic()
            + timeout
        )

        with self._condition:

            while (
                self._running
                and self._frame_id
                <= last_frame_id
            ):

                remaining = (
                    deadline
                    - time.monotonic()
                )

                if remaining <= 0:

                    return (
                        False,
                        None,
                        last_frame_id,
                        0.0,
                    )

                self._condition.wait(
                    timeout=remaining
                )

            if self._frame is None:

                return (
                    False,
                    None,
                    last_frame_id,
                    0.0,
                )

            return (
                True,
                self._frame.copy(),
                self._frame_id,
                self._timestamp,
            )

    # ========================================================
    # STOP CAPTURE
    # ========================================================

    def stop(self):

        self._running = False

        with self._condition:
            self._condition.notify_all()

        self.cap.release()

        if self._thread.is_alive():

            self._thread.join(
                timeout=1.0
            )


# ============================================================
# MAIN APPLICATION
# ============================================================

class IntegratedTrackerApp:
    """
    YOLO detection + persistent tracking + physical
    ESP32 Pan/Tilt control.
    """

    def __init__(
        self,
        source: str = "0",
        model_path: Optional[Path] = None,
        policy: str = TARGET_POLICY,
    ):

        self.source_arg = source

        self.policy = policy

        self.model_path = (
            model_path
            if model_path
            else PROJECT_ROOT
            / "models"
            / "best.pt"
        )

        # ----------------------------------------------------
        # YOLO
        # ----------------------------------------------------

        self.detector = YOLOObjectDetector(
            model_path=self.model_path,
            confidence_threshold=0.25,
        )

        # ----------------------------------------------------
        # Persistent drone tracking
        # ----------------------------------------------------

        self.drone_tracker = DroneTracker(
            max_lost_frames=15
        )

        # ----------------------------------------------------
        # Target error analyzer
        #
        # Target must be at least 50 px away from center
        # before an axis is considered LEFT/RIGHT/UP/DOWN.
        # ----------------------------------------------------

        self.target_analyzer = (
            TargetAnalyzer(
                dead_zone_x=50,
                dead_zone_y=50,
            )
        )

        # ----------------------------------------------------
        # REAL ESP32 CONTROLLER
        # ----------------------------------------------------

        self.pantilt_controller = (
            ESP32PanTiltController(
                esp32_ip="192.168.4.1",

                pan_min_us=1450,
                pan_max_us=1550,

                tilt_min_us=1450,
                tilt_max_us=1550,

                pan_center_us=1500,
                tilt_center_us=1500,

                # Change these later ONLY if an axis
                # physically moves opposite to what we want.
                pan_invert=False,
                tilt_invert=False,

                command_rate_hz=20.0,
                http_timeout=0.25,
            )
        )

        self.fps = 0.0

    # ========================================================
    # PRIMARY TARGET SELECTION
    # ========================================================

    def select_primary_target(
        self,
        tracked_drones: list,
        frame_w: int,
        frame_h: int,
    ) -> Optional[TrackedDrone]:

        if not tracked_drones:
            return None

        if (
            self.policy
            == "highest_confidence"
        ):

            return max(
                tracked_drones,
                key=lambda d: d.confidence,
            )

        elif self.policy == "largest":

            return max(
                tracked_drones,
                key=lambda d:
                (d.x2 - d.x1)
                * (d.y2 - d.y1),
            )

        elif (
            self.policy
            == "closest_to_center"
        ):

            cx_f = frame_w / 2.0
            cy_f = frame_h / 2.0

            return min(
                tracked_drones,
                key=lambda d:
                np.hypot(
                    d.center_x - cx_f,
                    d.center_y - cy_f,
                ),
            )

        return tracked_drones[0]

    # ========================================================
    # MAIN LOOP
    # ========================================================

    def run(self):

        source_is_camera = (
            self.source_arg.isdigit()
        )

        cap_source = (
            int(self.source_arg)
            if source_is_camera
            else self.source_arg
        )

        # ----------------------------------------------------
        # OPEN CAMERA
        # ----------------------------------------------------

        try:

            cap = LatestFrameCapture(
                cap_source
            )

        except RuntimeError as exc:

            print(
                f"Error: {exc}"
            )

            return

        last_frame_id = -1

        window_name = (
            "DronAI - Drone Tracking"
        )

        cv2.namedWindow(
            window_name,
            cv2.WINDOW_NORMAL,
        )

        prev_time = time.time()

        print()
        print("=" * 60)
        print(
            "       DRONAI LAPTOP CAMERA TRACKING"
        )
        print("=" * 60)

        print(
            f"Source       : {self.source_arg}"
        )

        print(
            f"Model        : {self.model_path}"
        )

        print(
            f"Target policy: {self.policy}"
        )

        print(
            "ESP32        : 192.168.4.1"
        )

        print(
            "Servo range  : 1450 - 1550 us"
        )

        print()
        print(
            "Press Q or ESC to exit."
        )
        print()

        # ----------------------------------------------------
        # MAIN PROCESSING LOOP
        # ----------------------------------------------------

        try:

            while True:

                (
                    ret,
                    frame,
                    frame_id,
                    frame_timestamp,
                ) = cap.read(
                    last_frame_id=last_frame_id,
                    timeout=2.0,
                )

                if (
                    not ret
                    or frame is None
                ):

                    print(
                        "Warning: no new frame received."
                    )

                    continue

                last_frame_id = (
                    frame_id
                )

                # --------------------------------------------
                # FRAME LATENCY
                # --------------------------------------------

                frame_age_ms = (
                    time.monotonic()
                    - frame_timestamp
                ) * 1000.0

                # --------------------------------------------
                # FPS
                # --------------------------------------------

                curr_time = time.time()

                dt = (
                    curr_time
                    - prev_time
                )

                if dt > 0:

                    instant_fps = (
                        1.0 / dt
                    )

                    self.fps = (
                        0.85
                        * self.fps
                        + 0.15
                        * instant_fps
                    )

                prev_time = curr_time

                # --------------------------------------------
                # ACTUAL CAMERA SIZE
                # --------------------------------------------

                h, w = frame.shape[:2]

                frame_center = (
                    w // 2,
                    h // 2,
                )

                # IMPORTANT:
                # Pan/Tilt controller now uses the actual
                # webcam resolution rather than assuming
                # 1280x720.
                self.pantilt_controller.set_frame_size(
                    w,
                    h,
                )

                # ============================================
                # 1. YOLO DETECTION
                # ============================================

                all_detections = (
                    self.detector.detect(
                        frame
                    )
                )

                # ============================================
                # 2. PERSISTENT DRONE TRACKING
                # ============================================

                active_drones = (
                    self.drone_tracker.update(
                        all_detections
                    )
                )

                # --------------------------------------------
                # Only CURRENTLY VISIBLE drones are eligible
                # to control physical servos.
                #
                # A tracker may remember a drone for up to
                # 15 lost frames, but stale coordinates must
                # NEVER command hardware.
                # --------------------------------------------

                visible_drones = [
                    drone
                    for drone
                    in active_drones
                    if drone.lost_frames == 0
                ]

                # ============================================
                # 3. PRIMARY TARGET
                # ============================================

                primary_drone = (
                    self.select_primary_target(
                        visible_drones,
                        w,
                        h,
                    )
                )

                telemetry: Optional[
                    TargetTelemetry
                ] = None

                # ============================================
                # 4. TARGET -> PHYSICAL PAN/TILT
                # ============================================

                if primary_drone:

                    telemetry = (
                        self.target_analyzer.analyze(
                            primary_drone,
                            w,
                            h,
                        )
                    )

                    # Because primary_drone came only
                    # from visible_drones, this is a
                    # CURRENT detection.
                    self.pantilt_controller.update(
                        telemetry.pan_direction,
                        telemetry.tilt_direction,
                        telemetry.error_x,
                        telemetry.error_y,
                    )

                # ============================================
                # VISUALIZATION
                # ============================================

                # --------------------------------------------
                # Center crosshair
                # --------------------------------------------

                cv2.line(
                    frame,
                    (
                        frame_center[0],
                        0,
                    ),
                    (
                        frame_center[0],
                        h,
                    ),
                    (0, 255, 255),
                    1,
                )

                cv2.line(
                    frame,
                    (
                        0,
                        frame_center[1],
                    ),
                    (
                        w,
                        frame_center[1],
                    ),
                    (0, 255, 255),
                    1,
                )

                cv2.circle(
                    frame,
                    frame_center,
                    6,
                    (0, 255, 255),
                    1,
                )

                cv2.circle(
                    frame,
                    frame_center,
                    2,
                    (0, 255, 255),
                    -1,
                )

                # --------------------------------------------
                # Non-drone detections
                # --------------------------------------------

                for det in all_detections:

                    is_drone = (
                        det.class_id == 1
                        or
                        "drone"
                        in det.class_name.lower()
                    )

                    if not is_drone:

                        cv2.rectangle(
                            frame,
                            (
                                det.x1,
                                det.y1,
                            ),
                            (
                                det.x2,
                                det.y2,
                            ),
                            (255, 180, 0),
                            1,
                        )

                        cv2.putText(
                            frame,
                            (
                                f"{det.class_name} "
                                f"{det.confidence:.2f}"
                            ),
                            (
                                det.x1,
                                max(
                                    det.y1 - 5,
                                    15,
                                ),
                            ),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.45,
                            (255, 180, 0),
                            1,
                        )

                # --------------------------------------------
                # Tracked drones
                # --------------------------------------------

                for drone in active_drones:

                    is_primary = (
                        primary_drone is not None
                        and
                        drone.track_id
                        == primary_drone.track_id
                    )

                    is_visible = (
                        drone.lost_frames == 0
                    )

                    if not is_visible:

                        box_color = (
                            100,
                            100,
                            100,
                        )

                        thickness = 1

                    elif is_primary:

                        box_color = (
                            0,
                            0,
                            255,
                        )

                        thickness = 3

                    else:

                        box_color = (
                            0,
                            165,
                            255,
                        )

                        thickness = 2

                    # Bounding box
                    cv2.rectangle(
                        frame,
                        (
                            drone.x1,
                            drone.y1,
                        ),
                        (
                            drone.x2,
                            drone.y2,
                        ),
                        box_color,
                        thickness,
                    )

                    cx = int(
                        drone.center_x
                    )

                    cy = int(
                        drone.center_y
                    )

                    cv2.circle(
                        frame,
                        (cx, cy),
                        4,
                        box_color,
                        -1,
                    )

                    if is_visible:

                        label_text = (
                            f"{drone.label} "
                            f"({drone.confidence * 100:.0f}%)"
                        )

                    else:

                        label_text = (
                            f"{drone.label} LOST "
                            f"{drone.lost_frames}"
                        )

                    cv2.putText(
                        frame,
                        label_text,
                        (
                            drone.x1,
                            max(
                                drone.y1 - 8,
                                18,
                            ),
                        ),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.55,
                        box_color,
                        2,
                    )

                    # ----------------------------------------
                    # Trajectory
                    # ----------------------------------------

                    points = list(
                        drone.history
                    )

                    for i in range(
                        1,
                        len(points),
                    ):

                        if (
                            points[i - 1] is None
                            or
                            points[i] is None
                        ):
                            continue

                        cv2.line(
                            frame,
                            points[i - 1],
                            points[i],
                            (0, 255, 0),
                            2,
                        )

                # --------------------------------------------
                # Target vector
                # --------------------------------------------

                if (
                    primary_drone
                    and telemetry
                ):

                    cv2.line(
                        frame,
                        frame_center,
                        telemetry.drone_center,
                        (0, 255, 0),
                        2,
                        cv2.LINE_AA,
                    )

                # --------------------------------------------
                # Alert banner
                # --------------------------------------------

                if visible_drones:

                    cv2.rectangle(
                        frame,
                        (0, 0),
                        (w, 40),
                        (0, 0, 200),
                        -1,
                    )

                    alert_text = (
                        f"ALERT: "
                        f"{len(visible_drones)} "
                        f"DRONE(S) DETECTED"
                    )

                    (
                        text_width,
                        _,
                    ), _ = cv2.getTextSize(
                        alert_text,
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        2,
                    )

                    cv2.putText(
                        frame,
                        alert_text,
                        (
                            max(
                                5,
                                (w - text_width)
                                // 2,
                            ),
                            27,
                        ),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (255, 255, 255),
                        2,
                    )

                # --------------------------------------------
                # Frame age + FPS
                # --------------------------------------------

                cv2.putText(
                    frame,
                    (
                        f"FPS: {self.fps:.1f} "
                        f"| Frame age: "
                        f"{frame_age_ms:.0f} ms"
                    ),
                    (
                        10,
                        h - 15,
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 255),
                    1,
                )

                # --------------------------------------------
                # Servo telemetry
                # --------------------------------------------

                servo_text = (
                    f"PAN: "
                    f"{self.pantilt_controller.current_pan_us} us"
                    f" | TILT: "
                    f"{self.pantilt_controller.current_tilt_us} us"
                )

                cv2.putText(
                    frame,
                    servo_text,
                    (
                        10,
                        max(
                            60,
                            h - 38,
                        ),
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 0),
                    1,
                )

                # --------------------------------------------
                # DISPLAY
                # --------------------------------------------

                cv2.imshow(
                    window_name,
                    frame,
                )

                key = (
                    cv2.waitKey(1)
                    & 0xFF
                )

                if key in (
                    ord("q"),
                    ord("Q"),
                    27,
                ):
                    break

        finally:

            # =================================================
            # CLEAN SHUTDOWN
            # =================================================

            cap.stop()

            self.pantilt_controller.close()

            cv2.destroyAllWindows()

            print()
            print(
                "DronAI tracking terminated."
            )


# ============================================================
# ENTRY POINT
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "DronAI Anti-Drone "
            "Tracking System"
        )
    )

    parser.add_argument(
        "--source",
        type=str,
        default="0",
        help=(
            "Video source. "
            "Use 0 for laptop webcam."
        ),
    )

    args = parser.parse_args()

    app = IntegratedTrackerApp(
        source=args.source
    )

    app.run()


if __name__ == "__main__":
    main()