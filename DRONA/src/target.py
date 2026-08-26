"""
Target Position Module
Calculates target position telemetry relative to frame center, applies X/Y dead zones,
determines PAN (LEFT/RIGHT/CENTER) and TILT (UP/DOWN/CENTER) directions.
"""

from dataclasses import dataclass
from typing import Tuple, Optional
from src.tracker import TrackedDrone

DEAD_ZONE_X = 50
DEAD_ZONE_Y = 50


@dataclass
class TargetTelemetry:
    """Telemetry data structure for a tracked drone target."""
    drone_id: int
    label: str
    confidence: float
    drone_center: Tuple[int, int]
    frame_center: Tuple[int, int]
    error_x: int
    error_y: int
    pan_direction: str   # LEFT, RIGHT, CENTER
    tilt_direction: str  # UP, DOWN, CENTER


class TargetAnalyzer:
    """Calculates displacement error vectors and pan/tilt directions for tracked drones."""

    def __init__(self, dead_zone_x: int = DEAD_ZONE_X, dead_zone_y: int = DEAD_ZONE_Y):
        self.dead_zone_x = dead_zone_x
        self.dead_zone_y = dead_zone_y

    def analyze(self, drone: TrackedDrone, frame_width: int, frame_height: int) -> TargetTelemetry:
        """
        Analyzes drone position relative to frame center and calculates telemetry.

        Args:
            drone: TrackedDrone instance.
            frame_width: Video frame width in pixels.
            frame_height: Video frame height in pixels.

        Returns:
            TargetTelemetry object containing error coordinates and pan/tilt commands.
        """
        frame_center_x = frame_width / 2.0
        frame_center_y = frame_height / 2.0

        drone_center_x = drone.center_x
        drone_center_y = drone.center_y

        error_x = int(drone_center_x - frame_center_x)
        error_y = int(drone_center_y - frame_center_y)

        # Determine PAN direction
        if error_x < -self.dead_zone_x:
            pan_dir = "LEFT"
        elif error_x > self.dead_zone_x:
            pan_dir = "RIGHT"
        else:
            pan_dir = "CENTER"

        # Determine TILT direction (in OpenCV y-axis is inverted: negative error_y means target is above center)
        if error_y < -self.dead_zone_y:
            tilt_dir = "UP"
        elif error_y > self.dead_zone_y:
            tilt_dir = "DOWN"
        else:
            tilt_dir = "CENTER"

        return TargetTelemetry(
            drone_id=drone.track_id,
            label=drone.label,
            confidence=drone.confidence,
            drone_center=(int(drone_center_x), int(drone_center_y)),
            frame_center=(int(frame_center_x), int(frame_center_y)),
            error_x=error_x,
            error_y=error_y,
            pan_direction=pan_dir,
            tilt_direction=tilt_dir,
        )
