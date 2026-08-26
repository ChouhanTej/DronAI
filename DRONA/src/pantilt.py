"""
Pan/Tilt Controller Module
Modular controller interface generating pan/tilt directional and angular commands.
Operates in Simulation Mode for Phase 1, ready for ESP32 hardware serial interface in Phase 2.
"""

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
    Future ESP32 hardware Pan/Tilt controller placeholder.
    Will transmit serial strings over USB/UART to ESP32 micro-controller.
    """

    def __init__(self, port: str = "/dev/tty.usbmodem14101", baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        logger.info(f"ESP32PanTiltController configured for serial port {port} (Not connected yet).")

    def update(self, pan_direction: str, tilt_direction: str, error_x: int = 0, error_y: int = 0) -> Tuple[str, str]:
        command = f"PAN:{pan_direction};TILT:{tilt_direction}\n"
        # Future implementation will write `command.encode()` to serial port
        logger.debug(f"[ESP32 SERIAL OUT] {command.strip()}")
        return f"PAN:{pan_direction}", f"TILT:{tilt_direction}"
