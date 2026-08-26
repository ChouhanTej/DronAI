"""
Unit Test Suite for SIH Anti-Drone System
Tests model loading, class mapping, detection output structure, center calculations,
X/Y error vectors, dead zones, PAN/TILT directions, and multi-drone tracking IDs.
"""

import unittest
import sys
from pathlib import Path
import numpy as np

# Add parent DRONA root directory to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.detector import YOLOObjectDetector, Detection
from src.tracker import DroneTracker, TrackedDrone
from src.target import TargetAnalyzer, TargetTelemetry
from src.pantilt import SimulatedPanTiltController


class TestAntiDroneSystem(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parent.parent
        cls.model_path = cls.project_root / "models" / "best.pt"

    def test_01_model_loading_and_class_mapping(self):
        """1 & 2. Verify model loads and maps classes correctly."""
        self.assertTrue(self.model_path.exists(), f"Model file missing at {self.model_path}")
        detector = YOLOObjectDetector(model_path=self.model_path)
        self.assertIsNotNone(detector.model)

        class_names = detector.model.names
        self.assertEqual(class_names[0], "AirPlane")
        self.assertEqual(class_names[1], "Drone")
        self.assertEqual(class_names[2], "Helicopter")

    def test_02_detection_representation_and_center_calc(self):
        """3 & 4. Verify detection object output and center coordinate math."""
        det = Detection(
            class_id=1,
            class_name="Drone",
            confidence=0.95,
            x1=100,
            y1=200,
            x2=300,
            y2=400,
            center_x=(100 + 300) / 2.0,
            center_y=(200 + 400) / 2.0,
            width=200.0,
            height=200.0,
        )
        self.assertEqual(det.center_x, 200.0)
        self.assertEqual(det.center_y, 300.0)
        self.assertEqual(det.box, (100, 200, 300, 400))
        self.assertEqual(det.area, 40000.0)

    def test_03_target_error_and_deadzone_behavior(self):
        """5, 6, 7 & 8. Verify X/Y error vectors, deadzones, PAN and TILT direction rules."""
        analyzer = TargetAnalyzer(dead_zone_x=50, dead_zone_y=50)

        # Mock frame dimensions
        frame_w, frame_h = 1280, 720  # Frame center: (640, 360)

        # Case A: Target to the RIGHT (+200 error_x) and UP (-160 error_y)
        det_a = Detection(1, "Drone", 0.9, 800, 150, 880, 250, 840.0, 200.0, 80.0, 100.0)
        drone_a = TrackedDrone(1, det_a)
        telemetry_a = analyzer.analyze(drone_a, frame_w, frame_h)

        self.assertEqual(telemetry_a.error_x, 840 - 640)  # +200
        self.assertEqual(telemetry_a.error_y, 200 - 360)  # -160
        self.assertEqual(telemetry_a.pan_direction, "RIGHT")
        self.assertEqual(telemetry_a.tilt_direction, "UP")

        # Case B: Target to the LEFT (-240 error_x) and DOWN (+190 error_y)
        det_b = Detection(1, "Drone", 0.85, 360, 500, 440, 600, 400.0, 550.0, 80.0, 100.0)
        drone_b = TrackedDrone(2, det_b)
        telemetry_b = analyzer.analyze(drone_b, frame_w, frame_h)

        self.assertEqual(telemetry_b.error_x, 400 - 640)  # -240
        self.assertEqual(telemetry_b.error_y, 550 - 360)  # +190
        self.assertEqual(telemetry_b.pan_direction, "LEFT")
        self.assertEqual(telemetry_b.tilt_direction, "DOWN")

        # Case C: Target WITHIN DEADZONE (Error X = +20, Error Y = -30) -> CENTER, CENTER
        det_c = Detection(1, "Drone", 0.92, 620, 310, 700, 350, 660.0, 330.0, 80.0, 40.0)
        drone_c = TrackedDrone(3, det_c)
        telemetry_c = analyzer.analyze(drone_c, frame_w, frame_h)

        self.assertEqual(telemetry_c.pan_direction, "CENTER")
        self.assertEqual(telemetry_c.tilt_direction, "CENTER")

    def test_04_multiple_drone_tracking_ids(self):
        """9. Verify multiple drones receive distinct persistent IDs and non-drones are ignored."""
        tracker = DroneTracker(max_lost_frames=15)

        # Frame 1: 2 Drones and 1 AirPlane
        dets_frame1 = [
            Detection(1, "Drone", 0.91, 100, 100, 150, 150, 125.0, 125.0, 50.0, 50.0),
            Detection(1, "Drone", 0.88, 500, 500, 560, 560, 530.0, 530.0, 60.0, 60.0),
            Detection(0, "AirPlane", 0.95, 800, 200, 950, 300, 875.0, 250.0, 150.0, 100.0),
        ]

        active_drones_f1 = tracker.update(dets_frame1)
        self.assertEqual(len(active_drones_f1), 2)
        drone_ids_f1 = {d.track_id for d in active_drones_f1}
        self.assertIn(1, drone_ids_f1)
        self.assertIn(2, drone_ids_f1)

        # Frame 2: Slightly shifted Drones (Persistent IDs must be preserved)
        dets_frame2 = [
            Detection(1, "Drone", 0.93, 105, 105, 155, 155, 130.0, 130.0, 50.0, 50.0),
            Detection(1, "Drone", 0.87, 510, 510, 570, 570, 540.0, 540.0, 60.0, 60.0),
        ]

        active_drones_f2 = tracker.update(dets_frame2)
        self.assertEqual(len(active_drones_f2), 2)
        drone_ids_f2 = {d.track_id for d in active_drones_f2}
        self.assertEqual(drone_ids_f1, drone_ids_f2)

    def test_05_simulated_pantilt_controller(self):
        """Verify PanTiltController command output generation."""
        controller = SimulatedPanTiltController()
        pan_cmd, tilt_cmd = controller.update("RIGHT", "UP", error_x=120, error_y=-80)
        self.assertEqual(pan_cmd, "PAN:RIGHT")
        self.assertEqual(tilt_cmd, "TILT:UP")


if __name__ == "__main__":
    unittest.main()
