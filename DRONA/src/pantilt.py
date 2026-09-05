"""
DronAI Pan/Tilt Controller

Supports:
1. Simulation mode
2. ESP32 Wi-Fi HTTP pan/tilt control

For the current demo:
Laptop webcam -> YOLO -> target coordinates -> ESP32 -> servos

Because the laptop webcam is NOT physically mounted on the pan/tilt unit,
the detected target position is mapped directly to an absolute servo
position rather than using closed-loop incremental control.
"""

from abc import ABC, abstractmethod
import logging
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Tuple


logger = logging.getLogger("PanTiltController")


# ============================================================
# BASE CONTROLLER
# ============================================================

class BasePanTiltController(ABC):
    """Base interface for pan/tilt controllers."""

    @abstractmethod
    def update(
        self,
        pan_direction: str,
        tilt_direction: str,
        error_x: int = 0,
        error_y: int = 0,
    ) -> Tuple[str, str]:
        pass

    def set_frame_size(self, width: int, height: int):
        """Optional frame-size update."""
        pass

    def close(self):
        """Optional cleanup."""
        pass


# ============================================================
# SIMULATION CONTROLLER
# ============================================================

class SimulatedPanTiltController(BasePanTiltController):
    """Pan/Tilt simulation without physical hardware."""

    def __init__(self):
        self.current_pan_cmd = "CENTER"
        self.current_tilt_cmd = "CENTER"

        logger.info(
            "SimulatedPanTiltController initialized."
        )

    def update(
        self,
        pan_direction: str,
        tilt_direction: str,
        error_x: int = 0,
        error_y: int = 0,
    ) -> Tuple[str, str]:

        pan_cmd = f"PAN:{pan_direction}"
        tilt_cmd = f"TILT:{tilt_direction}"

        if (
            pan_direction != self.current_pan_cmd
            or tilt_direction != self.current_tilt_cmd
        ):
            self.current_pan_cmd = pan_direction
            self.current_tilt_cmd = tilt_direction

            logger.info(
                "[SIMULATED] %s | %s | X=%+d Y=%+d",
                pan_cmd,
                tilt_cmd,
                error_x,
                error_y,
            )

        return pan_cmd, tilt_cmd


# ============================================================
# ESP32 WIFI CONTROLLER
# ============================================================

class ESP32PanTiltController(BasePanTiltController):
    """
    Laptop-camera -> ESP32 pan/tilt controller.

    The ESP32 endpoint is:

        http://192.168.4.1/pantilt?pan=1500&tilt=1500

    Servo commands are currently restricted to:

        PAN  : 1450 - 1550 us
        TILT : 1450 - 1550 us

    HTTP transmission runs in a background thread so network
    delays do not block YOLO inference.
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

        pan_invert: bool = False,
        tilt_invert: bool = False,

        command_rate_hz: float = 20.0,
        http_timeout: float = 0.25,
    ):

        self.base_url = f"http://{esp32_ip}"

        # ----------------------------------------------------
        # Servo limits
        # ----------------------------------------------------

        self.pan_min_us = pan_min_us
        self.pan_max_us = pan_max_us

        self.tilt_min_us = tilt_min_us
        self.tilt_max_us = tilt_max_us

        self.pan_center_us = pan_center_us
        self.tilt_center_us = tilt_center_us

        # ----------------------------------------------------
        # Direction configuration
        # ----------------------------------------------------

        self.pan_invert = pan_invert
        self.tilt_invert = tilt_invert

        # ----------------------------------------------------
        # ACTUAL webcam resolution.
        #
        # tracker.py updates these values every frame.
        # ----------------------------------------------------

        self.frame_width = 640
        self.frame_height = 480

        # ----------------------------------------------------
        # Current requested position
        # ----------------------------------------------------

        self.current_pan_us = pan_center_us
        self.current_tilt_us = tilt_center_us

        # Last command successfully delivered
        self.last_sent_pan = None
        self.last_sent_tilt = None

        # ----------------------------------------------------
        # HTTP configuration
        # ----------------------------------------------------

        self.http_timeout = http_timeout

        if command_rate_hz <= 0:
            command_rate_hz = 20.0

        self.command_interval = 1.0 / command_rate_hz

        self.last_error_log = 0.0

        # ----------------------------------------------------
        # Latest-command sender
        #
        # Only ONE pending servo command is stored.
        # Old commands are discarded automatically.
        # ----------------------------------------------------

        self._condition = threading.Condition()

        self._pending_command = None

        self._running = True

        self._stop_event = threading.Event()

        self._sender_thread = threading.Thread(
            target=self._sender_loop,
            name="ESP32PanTiltSender",
            daemon=True,
        )

        self._sender_thread.start()

        logger.info(
            "ESP32PanTiltController initialized at %s",
            self.base_url,
        )

    # ========================================================
    # UTILITY
    # ========================================================

    @staticmethod
    def _clamp(value, minimum, maximum):
        return max(
            minimum,
            min(maximum, value),
        )

    # ========================================================
    # FRAME SIZE
    # ========================================================

    def set_frame_size(
        self,
        width: int,
        height: int,
    ):
        """
        Update controller using the REAL webcam resolution.

        Example:
            640x480
            1280x720
            etc.

        This prevents incorrect normalization.
        """

        if width > 0:
            self.frame_width = width

        if height > 0:
            self.frame_height = height

    # ========================================================
    # QUEUE LATEST COMMAND
    # ========================================================

    def _queue_command(
        self,
        pan_us: int,
        tilt_us: int,
    ):

        with self._condition:

            # Replace any older unprocessed command.
            self._pending_command = (
                pan_us,
                tilt_us,
            )

            self._condition.notify()

    # ========================================================
    # BACKGROUND HTTP SENDER
    # ========================================================

    def _sender_loop(self):

        next_allowed_time = 0.0

        while self._running:

            # Wait for newest command
            with self._condition:

                while (
                    self._running
                    and self._pending_command is None
                ):
                    self._condition.wait(
                        timeout=0.5
                    )

                if not self._running:
                    break

                command = self._pending_command

                # Consume newest command.
                self._pending_command = None

            if command is None:
                continue

            pan_us, tilt_us = command

            # ------------------------------------------------
            # Rate limit servo network commands
            # ------------------------------------------------

            now = time.monotonic()

            wait_time = (
                next_allowed_time - now
            )

            if wait_time > 0:

                if self._stop_event.wait(wait_time):
                    break

            # ------------------------------------------------
            # Send command
            # ------------------------------------------------

            self._send_command(
                pan_us,
                tilt_us,
            )

            next_allowed_time = (
                time.monotonic()
                + self.command_interval
            )

    # ========================================================
    # SEND HTTP COMMAND
    # ========================================================

    def _send_command(
        self,
        pan_us: int,
        tilt_us: int,
    ):

        # Do not resend identical successful command.
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

        url = (
            f"{self.base_url}"
            f"/pantilt?{query}"
        )

        try:

            with urllib.request.urlopen(
                url,
                timeout=self.http_timeout,
            ) as response:

                response.read()

            self.last_sent_pan = pan_us
            self.last_sent_tilt = tilt_us

        except (
            urllib.error.URLError,
            TimeoutError,
            OSError,
        ) as exc:

            now = time.monotonic()

            # Avoid flooding terminal with errors.
            if (
                now - self.last_error_log
                > 1.0
            ):

                logger.warning(
                    "ESP32 command failed: %s",
                    exc,
                )

                self.last_error_log = now

    # ========================================================
    # TARGET -> SERVO MAPPING
    # ========================================================

    def update(
        self,
        pan_direction: str,
        tilt_direction: str,
        error_x: int = 0,
        error_y: int = 0,
    ) -> Tuple[str, str]:

        # ----------------------------------------------------
        # Prevent division by zero
        # ----------------------------------------------------

        half_width = max(
            self.frame_width / 2.0,
            1.0,
        )

        half_height = max(
            self.frame_height / 2.0,
            1.0,
        )

        # ----------------------------------------------------
        # Normalize target displacement
        #
        # Left edge   ~= -1
        # Center      ~=  0
        # Right edge  ~= +1
        #
        # Top edge    ~= -1
        # Center      ~=  0
        # Bottom edge ~= +1
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # TargetAnalyzer already decides dead zone.
        #
        # If target is centered on one axis, command that
        # servo to its calibrated center.
        # ----------------------------------------------------

        if pan_direction == "CENTER":
            normalized_x = 0.0

        if tilt_direction == "CENTER":
            normalized_y = 0.0

        # ----------------------------------------------------
        # Mechanical orientation correction
        # ----------------------------------------------------

        if self.pan_invert:
            normalized_x *= -1.0

        if self.tilt_invert:
            normalized_y *= -1.0

        # ----------------------------------------------------
        # X -> PAN
        # ----------------------------------------------------

        if normalized_x >= 0:

            available_pan_range = (
                self.pan_max_us
                - self.pan_center_us
            )

        else:

            available_pan_range = (
                self.pan_center_us
                - self.pan_min_us
            )

        pan_us = int(
            round(
                self.pan_center_us
                + (
                    normalized_x
                    * available_pan_range
                )
            )
        )

        # ----------------------------------------------------
        # Y -> TILT
        # ----------------------------------------------------

        if normalized_y >= 0:

            available_tilt_range = (
                self.tilt_max_us
                - self.tilt_center_us
            )

        else:

            available_tilt_range = (
                self.tilt_center_us
                - self.tilt_min_us
            )

        tilt_us = int(
            round(
                self.tilt_center_us
                + (
                    normalized_y
                    * available_tilt_range
                )
            )
        )

        # ----------------------------------------------------
        # Final safety clamp
        # ----------------------------------------------------

        pan_us = int(
            self._clamp(
                pan_us,
                self.pan_min_us,
                self.pan_max_us,
            )
        )

        tilt_us = int(
            self._clamp(
                tilt_us,
                self.tilt_min_us,
                self.tilt_max_us,
            )
        )

        self.current_pan_us = pan_us
        self.current_tilt_us = tilt_us

        # Send asynchronously.
        self._queue_command(
            pan_us,
            tilt_us,
        )

        return (
            f"PAN:{pan_us}us",
            f"TILT:{tilt_us}us",
        )

    # ========================================================
    # CLEAN SHUTDOWN
    # ========================================================

    def close(self):

        self._running = False
        self._stop_event.set()

        with self._condition:
            self._condition.notify_all()

        if self._sender_thread.is_alive():
            self._sender_thread.join(
                timeout=1.0
            )