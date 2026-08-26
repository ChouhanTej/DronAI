"""
Anti-Drone Detection & Tracking System - Main Application
Runs real-time camera capture, YOLO object detection, target selection, frame tracking,
error/direction computation, and OpenCV UI display.
"""

import logging
import sys
import time
import cv2
import numpy as np

import config
from controller import PanTiltController
from detector import Detection, YOLOObjectDetector
from tracker import TargetTracker

# Setup logging
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
logger = logging.getLogger("AntiDroneMain")


class AntiDroneApp:
    """Main application manager for camera processing and tracking UI."""

    def __init__(self):
        self.detector = None
        self.tracker = None
        self.controller = None
        self.cap = None

        self.fps = 0.0
        self.frame_count = 0
        self.start_time = time.time()
        self.last_frame_time = time.time()

        self.show_crosshair = config.SHOW_CROSSHAIR
        self.show_fps = config.SHOW_FPS

    def initialize(self) -> bool:
        """Initializes detector, tracker, controller, and camera feed."""
        logger.info("Initializing Anti-Drone Detection & Tracking System...")

        # 1. Initialize YOLO Object Detector
        try:
            self.detector = YOLOObjectDetector(
                model_name=config.MODEL_NAME,
                confidence_threshold=config.CONFIDENCE_THRESHOLD,
                models_dir=config.MODELS_DIR,
            )
        except Exception as e:
            logger.critical(f"Failed to initialize YOLO detector: {e}")
            return False

        # 2. Initialize Target Tracker & Pan/Tilt Controller
        self.tracker = TargetTracker(
            preferred_class=config.TARGET_CLASS,
            target_lock_enabled=config.TARGET_LOCK,
            deadzone_pixels=config.DEADZONE_PIXELS,
        )
        self.controller = PanTiltController()

        # 3. Open Mac Webcam
        logger.info(f"Opening camera index {config.CAMERA_INDEX}...")
        self.cap = cv2.VideoCapture(config.CAMERA_INDEX)

        # Attempt to set frame width & height
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)

        if not self.cap.isOpened():
            self._print_mac_permission_warning()
            return False

        # Read test frame
        ret, frame = self.cap.read()
        if not ret or frame is None:
            logger.error("Opened camera, but failed to capture test frame.")
            self._print_mac_permission_warning()
            return False

        logger.info("Camera feed successfully initialized.")
        return True

    def _print_mac_permission_warning(self):
        """Prints a friendly explanation of macOS Camera permissions."""
        print("\n" + "=" * 70)
        print(" [!] CAMERA INITIALIZATION ERROR")
        print("=" * 70)
        print(" Could not open macOS camera feed (Index 0).")
        print("\n Possible Causes & Solutions:")
        print(" 1. macOS Privacy Permission:")
        print("    Go to System Settings -> Privacy & Security -> Camera")
        print("    Ensure permissions are granted for Terminal, iTerm, VS Code,")
        print("    or Antigravity IDE.")
        print(" 2. Camera in use:")
        print("    Close FaceTime, Zoom, Photo Booth, or other apps using the webcam.")
        print(" 3. External Camera Index:")
        print("    If using an external webcam, update CAMERA_INDEX in config.py.")
        print("=" * 70 + "\n")

    def run(self):
        """Runs the main application processing loop."""
        if not self.initialize():
            logger.error("Initialization failed. Exiting.")
            sys.exit(1)

        cv2.namedWindow(config.WINDOW_TITLE, cv2.WINDOW_NORMAL)
        logger.info("System operational. Press 'q' or 'Esc' to exit.")

        try:
            while True:
                ret, frame = self.cap.read()
                if not ret or frame is None:
                    logger.warning("Frame read failed or video stream interrupted.")
                    time.sleep(0.01)
                    continue

                current_time = time.time()
                dt = current_time - self.last_frame_time
                self.last_frame_time = current_time
                if dt > 0:
                    self.fps = 0.9 * self.fps + 0.1 * (1.0 / dt)

                h, w, _ = frame.shape

                # Step 1: Detect objects using YOLO
                detections = self.detector.detect(frame)

                # Step 2: Track target & compute error/direction
                target, telemetry = self.tracker.update(detections, w, h)

                # Step 3: Update simulated Servo / Controller
                if telemetry["is_locked"]:
                    self.controller.update_from_error(
                        telemetry["error_x"], telemetry["error_y"]
                    )

                # Step 4: Render UI Overlays
                self._draw_overlay(frame, detections, target, telemetry, w, h)

                # Display frame
                cv2.imshow(config.WINDOW_TITLE, frame)

                # Keyboard event handling
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), ord("Q"), 27):  # 'q' or Esc
                    logger.info("Quit command received.")
                    break
                elif key in (ord("c"), ord("C")):
                    self.show_crosshair = not self.show_crosshair
                    logger.info(f"Crosshair display set to: {self.show_crosshair}")
                elif key in (ord("f"), ord("F")):
                    self.show_fps = not self.show_fps
                elif key in (ord("r"), ord("R")):
                    self.tracker.tracked_target = None
                    logger.info("Target lock manually reset.")

        except KeyboardInterrupt:
            logger.info("Ctrl+C received. Shutting down gracefully...")
        finally:
            self.cleanup()

    def _draw_overlay(
        self,
        frame: np.ndarray,
        detections: list,
        target: Detection,
        telemetry: dict,
        frame_width: int,
        frame_height: int,
    ):
        """Renders bounding boxes, target lock reticle, crosshair, and OSD panel."""
        frame_center_x = frame_width // 2
        frame_center_y = frame_height // 2

        # 1. Draw crosshairs through frame center
        if self.show_crosshair:
            ch_color = config.COLOR_CROSSHAIR
            # Vertical line
            cv2.line(frame, (frame_center_x, 0), (frame_center_x, frame_height), ch_color, 1)
            # Horizontal line
            cv2.line(frame, (0, frame_center_y), (frame_width, frame_center_y), ch_color, 1)
            # Center circle reticle
            cv2.circle(frame, (frame_center_x, frame_center_y), 6, ch_color, 1)
            cv2.circle(frame, (frame_center_x, frame_center_y), 2, ch_color, -1)

        # 2. Draw standard bounding boxes for all detected objects
        if config.SHOW_ALL_BOUNDING_BOXES:
            for det in detections:
                if target is not None and det == target:
                    continue  # Draw target separately with special reticle

                x1, y1, x2, y2 = det.box
                cx, cy = int(det.center_x), int(det.center_y)

                # Box
                cv2.rectangle(frame, (x1, y1), (x2, y2), config.COLOR_DETECTION_BOX, 1)
                # Center point
                cv2.circle(frame, (cx, cy), 4, config.COLOR_DETECTION_BOX, -1)

                # Label string
                label = f"{det.class_name} {det.confidence:.2f}"
                cv2.putText(
                    frame,
                    label,
                    (x1, max(y1 - 6, 15)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45,
                    config.COLOR_DETECTION_BOX,
                    1,
                    cv2.LINE_AA,
                )

        # 3. Draw distinctive Reticle & Vector line for Tracked Target
        if target is not None:
            tx1, ty1, tx2, ty2 = target.box
            tcx, tcy = int(target.center_x), int(target.center_y)

            # Highlighted corner bracket reticle for target
            self._draw_corner_brackets(frame, tx1, ty1, tx2, ty2, config.COLOR_TARGET_BOX, thickness=2, length=15)
            # Target box
            cv2.rectangle(frame, (tx1, ty1), (tx2, ty2), config.COLOR_TARGET_BOX, 1)

            # Target center point
            cv2.circle(frame, (tcx, tcy), 5, config.COLOR_TARGET_CENTER, -1)
            cv2.circle(frame, (tcx, tcy), 8, config.COLOR_TARGET_BOX, 1)

            # Vector line connecting frame center to target center
            cv2.line(
                frame,
                (frame_center_x, frame_center_y),
                (tcx, tcy),
                config.COLOR_TARGET_BOX,
                1,
                cv2.LINE_AA,
            )

            # Target Label
            target_label = f"LOCKED: {target.class_name.upper()} ({target.confidence:.2f})"
            cv2.putText(
                frame,
                target_label,
                (tx1, max(ty1 - 8, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                config.COLOR_TARGET_BOX,
                2,
                cv2.LINE_AA,
            )

        # 4. Draw OSD Telemetry Side Panel
        if config.SHOW_OSD_PANEL:
            self._draw_osd_panel(frame, telemetry, len(detections), frame_width, frame_height)

    def _draw_corner_brackets(self, img, x1, y1, x2, y2, color, thickness=2, length=15):
        """Draws tactical corner brackets around target bounding box."""
        # Top-Left
        cv2.line(img, (x1, y1), (x1 + length, y1), color, thickness)
        cv2.line(img, (x1, y1), (x1, y1 + length), color, thickness)
        # Top-Right
        cv2.line(img, (x2, y1), (x2 - length, y1), color, thickness)
        cv2.line(img, (x2, y1), (x2, y1 + length), color, thickness)
        # Bottom-Left
        cv2.line(img, (x1, y2), (x1 + length, y2), color, thickness)
        cv2.line(img, (x1, y2), (x1, y2 - length), color, thickness)
        # Bottom-Right
        cv2.line(img, (x2, y2), (x2 - length, y2), color, thickness)
        cv2.line(img, (x2, y2), (x2, y2 - length), color, thickness)

    def _draw_osd_panel(self, frame, telemetry, det_count, width, height):
        """Draws on-screen telemetry dashboard panel."""
        panel_w = 320
        panel_h = 240
        margin = 10

        # Semi-transparent overlay box
        sub_img = frame[margin : margin + panel_h, margin : margin + panel_w]
        black_bg = np.full_like(sub_img, config.COLOR_BACKGROUND_PANEL)
        blend = cv2.addWeighted(sub_img, 0.3, black_bg, 0.7, 0)
        frame[margin : margin + panel_h, margin : margin + panel_w] = blend

        # Border
        cv2.rectangle(
            frame,
            (margin, margin),
            (margin + panel_w, margin + panel_h),
            config.COLOR_CROSSHAIR,
            1,
        )

        # Content lines
        lines = [
            ("ANTI-DRONE SYSTEM", config.COLOR_CROSSHAIR, True),
            (f"FPS: {self.fps:.1f} | Res: {width}x{height}", config.COLOR_TEXT, False),
            (f"Detections: {det_count}", config.COLOR_TEXT, False),
            ("-----------------------------------", (100, 100, 100), False),
        ]

        if telemetry["is_locked"]:
            lines.extend([
                (f"Target: {telemetry['class_name']}", config.COLOR_TARGET_BOX, True),
                (f"Confidence: {telemetry['confidence']:.2f}", config.COLOR_TEXT, False),
                (f"Target Center: {telemetry['target_center']}", config.COLOR_TEXT, False),
                (f"Frame Center:  {telemetry['frame_center']}", config.COLOR_TEXT, False),
                (f"Error X: {telemetry['error_x']:+d} px", config.COLOR_TEXT, False),
                (f"Error Y: {telemetry['error_y']:+d} px", config.COLOR_TEXT, False),
                (f"Direction: {telemetry['direction']}", config.COLOR_TARGET_BOX, True),
            ])
        else:
            lines.extend([
                ("Target: NO TARGET LOCKED", (0, 0, 255), True),
                ("Direction: SEARCHING...", (150, 150, 150), False),
            ])

        y_offset = margin + 20
        for text, color, bold in lines:
            thickness = 2 if bold else 1
            font_scale = 0.45 if not bold else 0.48
            cv2.putText(
                frame,
                text,
                (margin + 10, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale,
                color,
                thickness,
                cv2.LINE_AA,
            )
            y_offset += 19

    def cleanup(self):
        """Releases camera hardware and destroys OpenCV display windows."""
        logger.info("Cleaning up resources...")
        if self.cap is not None:
            self.cap.release()
            self.cap = None
            logger.info("Webcam released.")
        cv2.destroyAllWindows()
        logger.info("OpenCV windows destroyed. Application stopped cleanly.")


def main():
    app = AntiDroneApp()
    app.run()


if __name__ == "__main__":
    main()
