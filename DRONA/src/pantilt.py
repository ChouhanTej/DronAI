"""
Pan/Tilt Controller Module
Modular controller interface generating pan/tilt directional and angular commands.
Operates in Simulation Mode for Phase 1, ready for ESP32 hardware serial interface in Phase 2.
"""

import urllib.parse
import urllib.request
import urllib.error
import time

from abc import ABC, abstractmethod
import logging
from typing import Tuple, Optional

logger = logging.getLogger("PanTiltController")


class BasePanTiltController(ABC):
    """Abstract Base Class for Pan/Tilt controllers."""

    @abstractmethod
    def update(self, pan_direction: str, tilt_direction: str, error_x: int = 0, error_y: int = 0) -> Tuple[str, str]:
        """Sends or simulates pan/tilt control updates."""
        pass


class SimulatedPanTiltController(BasePanTiltController):
    """
    Simulated Pan/Tilt controller.
    Logs directional and relative movement commands without connecting to physical hardware.
    """

    def __init__(self):
        self.current_pan_cmd: str = "CENTER"
        self.current_tilt_cmd: str = "CENTER"
        logger.info("SimulatedPanTiltController initialized (Hardware disconnected).")

    def update(self, pan_direction: str, tilt_direction: str, error_x: int = 0, error_y: int = 0) -> Tuple[str, str]:
        """
        Updates simulated pan/tilt command state and prints/logs changes.

        Args:
            pan_direction: "LEFT", "RIGHT", or "CENTER"
            tilt_direction: "UP", "DOWN", or "CENTER"
            error_x: Pixel error along X axis
            error_y: Pixel error along Y axis

        Returns:
            Tuple of (pan_command_str, tilt_command_str)
        """
        pan_cmd = f"PAN:{pan_direction}"
        tilt_cmd = f"TILT:{tilt_direction}"

        # Only log when command direction changes or active tracking
        if pan_direction != self.current_pan_cmd or tilt_direction != self.current_tilt_cmd:
            self.current_pan_cmd = pan_direction
            self.current_tilt_cmd = tilt_direction
            logger.info(f"[SIMULATED SERVO COMMAND] {pan_cmd} | {tilt_cmd} (Error: X={error_x:+d}, Y={error_y:+d})")

        return pan_cmd, tilt_cmd


class ESP32PanTiltController(BasePanTiltController):
    """
    Temporary laptop-camera -> ESP32 pan/tilt controller.

    The laptop webcam is NOT mounted on the pan/tilt mechanism, so this
    controller maps target position directly to an absolute servo position.

    This is intentionally different from the final closed-loop controller
    that will be used with the ESP32-CAM stream.
    """

    def __init__(
        self,
        esp32_ip: str = "192.168.4.1",
        pan_min_us: int = 1450,
        pan_max_us: int = 1550,
        tilt_min_us: int = 1450,
        tilt_max_us: int = 1550,
        pan_center_us: int = 1500,
        tilt_center_us: int = 1500,
        frame_width: int = 1280,
        frame_height: int = 720,
        pan_invert: bool = False,
        tilt_invert: bool = False,
    ):
        self.base_url = f"http://{esp32_ip}"

        # SAFE range we already physically tested.
        self.pan_min_us = pan_min_us
        self.pan_max_us = pan_max_us
        self.tilt_min_us = tilt_min_us
        self.tilt_max_us = tilt_max_us

        self.pan_center_us = pan_center_us
        self.tilt_center_us = tilt_center_us

        self.frame_width = frame_width
        self.frame_height = frame_height

        self.pan_invert = pan_invert
        self.tilt_invert = tilt_invert

        self.current_pan_us = pan_center_us
        self.current_tilt_us = tilt_center_us

        self.last_sent_pan = None
        self.last_sent_tilt = None

        self.last_error_log = 0.0

        logger.info(
            "ESP32PanTiltController initialized: %s",
            self.base_url,
        )

    @staticmethod
    def _clamp(value, minimum, maximum):
        return max(minimum, min(maximum, value))

    def _send_command(self, pan_us: int, tilt_us: int):
        # Avoid sending the exact same command repeatedly.
        if (
            pan_us == self.last_sent_pan
            and tilt_us == self.last_sent_tilt
        ):
            return

        query = urllib.parse.urlencode(
            {
                "pan": pan_us,
                "tilt": tilt_us,
            }
        )

        url = f"{self.base_url}/pantilt?{query}"

        try:
            with urllib.request.urlopen(url, timeout=0.12) as response:
                response.read()

            self.last_sent_pan = pan_us
            self.last_sent_tilt = tilt_us

        except (
            urllib.error.URLError,
            TimeoutError,
            OSError,
        ) as exc:

            # Avoid printing an error every video frame.
            now = time.monotonic()

            if now - self.last_error_log > 1.0:
                logger.warning(
                    "ESP32 pan/tilt command failed: %s",
                    exc,
                )
                self.last_error_log = now

    def update(
        self,
        pan_direction: str,
        tilt_direction: str,
        error_x: int = 0,
        error_y: int = 0,
    ) -> Tuple[str, str]:

        # -------------------------------------------------
        # Normalize target displacement.
        #
        # Laptop webcam is requested at 1280x720:
        #
        # X ~= -640 ... +640
        # Y ~= -360 ... +360
        #
        # Clamp to [-1, +1].
        # -------------------------------------------------

        half_width = self.frame_width / 2.0
        half_height = self.frame_height / 2.0

        normalized_x = self._clamp(
            error_x / half_width,
            -1.0,
            1.0,
        )

        normalized_y = self._clamp(
            error_y / half_height,
            -1.0,
            1.0,
        )

        # TargetAnalyzer has already applied the dead zone.
        # If it says CENTER, force that axis to center.
        if pan_direction == "CENTER":
            normalized_x = 0.0

        if tilt_direction == "CENTER":
            normalized_y = 0.0

        # Allow mechanical mounting direction to be reversed.
        if self.pan_invert:
            normalized_x *= -1.0

        if self.tilt_invert:
            normalized_y *= -1.0

        # -------------------------------------------------
        # Direct image-position -> servo-position mapping
        #
        # center target      -> 1500 us
        # far left/right     -> 1450 / 1550 us
        #
        # This is intentionally safe and limited for the
        # FIRST automatic movement test.
        # -------------------------------------------------

        if normalized_x >= 0:
            pan_range = (
                self.pan_max_us
                - self.pan_center_us
            )
        else:
            pan_range = (
                self.pan_center_us
                - self.pan_min_us
            )

        if normalized_y >= 0:
            tilt_range = (
                self.tilt_max_us
                - self.tilt_center_us
            )
        else:
            tilt_range = (
                self.tilt_center_us
                - self.tilt_min_us
            )

        pan_us = int(
            round(
                self.pan_center_us
                + normalized_x * pan_range
            )
        )

        tilt_us = int(
            round(
                self.tilt_center_us
                + normalized_y * tilt_range
            )
        )

        pan_us = self._clamp(
            pan_us,
            self.pan_min_us,
            self.pan_max_us,
        )

        tilt_us = self._clamp(
            tilt_us,
            self.tilt_min_us,
            self.tilt_max_us,
        )

        self.current_pan_us = pan_us
        self.current_tilt_us = tilt_us

        self._send_command(
            pan_us,
            tilt_us,
        )

        return (
            f"PAN:{pan_us}us",
            f"TILT:{tilt_us}us",
        )