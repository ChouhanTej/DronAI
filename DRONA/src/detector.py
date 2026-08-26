"""
YOLO Object Detector Module
Handles loading YOLO models using relative pathlib paths, device auto-selection (MPS/CUDA/CPU),
running inference, and outputting standardized Detection objects.
"""

from dataclasses import dataclass
import logging
from pathlib import Path
from typing import List, Tuple, Optional
import numpy as np
import torch

logger = logging.getLogger("YOLOObjectDetector")


@dataclass
class Detection:
    """Class representing a single object detection."""
    class_id: int
    class_name: str
    confidence: float
    x1: int
    y1: int
    x2: int
    y2: int
    center_x: float
    center_y: float
    width: float
    height: float

    @property
    def box(self) -> Tuple[int, int, int, int]:
        return (self.x1, self.y1, self.x2, self.y2)

    @property
    def area(self) -> float:
        return self.width * self.height


class YOLOObjectDetector:
    """YOLO model detector wrapper."""

    def __init__(
        self,
        model_path: Optional[Path] = None,
        confidence_threshold: float = 0.25,
        iou_threshold: float = 0.50,
    ):
        self.project_root = Path(__file__).resolve().parent.parent
        if model_path is None:
            self.model_path = self.project_root / "models" / "best.pt"
        else:
            self.model_path = Path(model_path)

        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold

        # Device selection (Apple Silicon MPS / CUDA / CPU)
        if torch.backends.mps.is_available():
            self.device = 'mps'
        elif torch.cuda.is_available():
            self.device = 0
        else:
            self.device = 'cpu'

        self.model = None
        self._load_model()

    def _load_model(self) -> None:
        """Loads the YOLO model from the specified relative path."""
        try:
            from ultralytics import YOLO
        except ImportError as e:
            logger.error("Ultralytics package is not installed.")
            raise e

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Model file not found at {self.model_path}. "
                "Ensure models/best.pt exists in project root."
            )

        logger.info(f"Loading YOLO model from: {self.model_path} on device: {self.device}")
        self.model = YOLO(str(self.model_path))
        logger.info(f"Model loaded successfully with classes: {self.model.names}")

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """
        Runs object detection on an BGR image frame.

        Args:
            frame: BGR numpy image frame from OpenCV.

        Returns:
            List of standardized Detection dataclass objects.
        """
        if self.model is None or frame is None:
            return []

        detections: List[Detection] = []

        try:
            results = self.model.predict(
                frame,
                conf=self.confidence_threshold,
                iou=self.iou_threshold,
                device=self.device,
                verbose=False,
            )

            if not results:
                return detections

            result = results[0]
            boxes = result.boxes

            if boxes is None or len(boxes) == 0:
                return detections

            for box in boxes:
                xyxy = box.xyxy[0].cpu().numpy()
                x1, y1, x2, y2 = map(int, xyxy)
                conf = float(box.conf[0].cpu().numpy())
                cls_id = int(box.cls[0].cpu().numpy())
                cls_name = str(self.model.names.get(cls_id, f"class_{cls_id}"))

                w = float(x2 - x1)
                h = float(y2 - y1)
                center_x = (x1 + x2) / 2.0
                center_y = (y1 + y2) / 2.0

                detection = Detection(
                    class_id=cls_id,
                    class_name=cls_name,
                    confidence=conf,
                    x1=x1,
                    y1=y1,
                    x2=x2,
                    y2=y2,
                    center_x=center_x,
                    center_y=center_y,
                    width=w,
                    height=h,
                )
                detections.append(detection)

        except Exception as e:
            logger.error(f"Error during YOLO inference: {e}")

        return detections
