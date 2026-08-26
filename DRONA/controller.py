"""
Pan/Tilt Servo Controller Module (Phase 2 Stub / Future-Ready Interface)
Provides a modular interface for serial communication with an ESP32 micro-controller
and contains proportional (PID) error-to-servo angle calculations.
"""

import logging
from typing import Tuple
import config

logger = logging.getLogger("PanTiltController")


class PanTiltController:
    """
    Interface for pan/tilt servo positioning.
    Currently operates in simulation/logging mode for Phase 1.
    """

    def __init__(
        self,
        pan_center: int = config.PAN_CENTER_ANGLE,
        tilt_center: int = config.TILT_CENTER_ANGLE,
        kp_x: float = config.PID_KP_X,
        kp_y: float = config.PID_KP_Y,
    ):
        self.pan_angle: float = float(pan_center)
        self.tilt_angle: float = float(tilt_center)
        self.pan_center = pan_center
        self.tilt_center = tilt_center
        self.kp_x = kp_x
        self.kp_y = kp_y

        self.min_pan = config.PAN_MIN_ANGLE
        self.max_pan = config.PAN_MAX_ANGLE
        self.min_tilt = config.TILT_MIN_ANGLE
        self.max_tilt = config.TILT_MAX_ANGLE

        logger.info(
            f"PanTiltController initialized (Simulated). "
            f"Initial Angles -> Pan: {self.pan_angle}°, Tilt: {self.tilt_angle}°"
        )

    def set_pan(self, angle: float) -> float:
        """Sets the pan servo angle (clamped between min and max)."""
        clamped_angle = max(self.min_pan, min(self.max_pan, angle))
        if abs(clamped_angle - self.pan_angle) >= 0.5:
            self.pan_angle = clamped_angle
            logger.info(f"[SERVO COMMAND] PAN: {int(self.pan_angle)}°")
        return self.pan_angle

    def set_tilt(self, angle: float) -> float:
        """Sets the tilt servo angle (clamped between min and max)."""
        clamped_angle = max(self.min_tilt, min(self.max_tilt, angle))
        if abs(clamped_angle - self.tilt_angle) >= 0.5:
            self.tilt_angle = clamped_angle
            logger.info(f"[SERVO COMMAND] TILT: {int(self.tilt_angle)}°")
        return self.tilt_angle

    def center(self) -> Tuple[float, float]:
        """Resets both pan and tilt servos to their center positions."""
        self.set_pan(self.pan_center)
        self.set_tilt(self.tilt_center)
        logger.info("[SERVO COMMAND] CENTERED (90°, 90°)")
        return self.pan_angle, self.tilt_angle

    def update_from_error(self, error_x: int, error_y: int) -> Tuple[int, int]:
        """
        Calculates required pan and tilt adjustments based on target tracking error.

        Args:
            error_x: Target displacement in X axis (target_x - frame_center_x).
            error_y: Target displacement in Y axis (target_y - frame_center_y).

        Returns:
            Tuple of (new pan angle, new tilt angle)
        """
        # Proportional controller feedback
        # If target is to the right (error_x > 0), pan should increase (move right)
        # If target is below center (error_y > 0), tilt should increase (move down)
        delta_pan = error_x * self.kp_x
        delta_tilt = error_y * self.kp_y

        new_pan = self.set_pan(self.pan_angle + delta_pan)
        new_tilt = self.set_tilt(self.tilt_angle + delta_tilt)

        return int(new_pan), int(new_tilt)
