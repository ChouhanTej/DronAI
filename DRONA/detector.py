"""
YOLO Object Detector Module
Handles loading YOLO models, running inference, and extracting detection bounding boxes and centers.
"""

from dataclasses import dataclass
import logging
import os
from pathlib import Path
from typing import List, Optional, Tuple
import numpy as np

import config

# Setup logging
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("YOLOObjectDetector")


@dataclass
class Detection:
    """Class representing a single object detection."""
    box: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    confidence: float
    class_name: str
    class_id: int
    center_x: float
    center_y: float
    width: float
    height: float

    @property
    def area(self) -> float:
        return self.width * self.height


class YOLOObjectDetector:
    """Wrapper class for Ultralytics YOLO model inference."""

    def __init__(
        self,
        model_name: str = config.MODEL_NAME,
        confidence_threshold: float = config.CONFIDENCE_THRESHOLD,
        models_dir: Path = config.MODELS_DIR,
    ):
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(exist_ok=True)
        self.model = None

        self._load_model()

    def _load_model(self) -> None:
        """Loads the YOLO model, downloading it to models_dir if necessary."""
        try:
            from ultralytics import YOLO
        except ImportError:
            logger.error("Ultralytics library not found. Please install requirements.txt.")
            raise

        model_filepath = self.models_dir / self.model_name
        logger.info(f"Loading YOLO model from: {model_filepath}")

        try:
            # Ultralytics will auto-download if not present locally
            self.model = YOLO(str(model_filepath))
            logger.info(f"YOLO model '{self.model_name}' loaded successfully.")
        except Exception as e:
            logger.warning(f"Failed to load primary model '{self.model_name}': {e}")
            fallback_model = "yolov8n.pt"
            fallback_path = self.models_dir / fallback_model
            logger.info(f"Attempting fallback model: {fallback_model}")
            try:
                self.model = YOLO(str(fallback_path))
                self.model_name = fallback_model
                logger.info(f"Fallback model '{fallback_model}' loaded successfully.")
            except Exception as fallback_err:
                logger.error(f"Critical error loading fallback model: {fallback_err}")
                raise RuntimeError(
                    f"Could not load YOLO model ({self.model_name} or {fallback_model}). "
                    "Ensure internet connection is active for initial model download."
                ) from fallback_err

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """
        Runs object detection on an image frame.

        Args:
            frame: BGR numpy image frame from OpenCV.

        Returns:
            List of standardized Detection objects.
        """
        if self.model is None or frame is None:
            return []

        detections: List[Detection] = []

        try:
            # Run inference (verbose=False keeps console output clean)
            results = self.model(
                frame,
                conf=self.confidence_threshold,
                iou=config.NMS_IOU_THRESHOLD,
                verbose=False
            )

            if not results or len(results) == 0:
                return detections

            result = results[0]
            boxes = result.boxes

            if boxes is None or len(boxes) == 0:
                return detections

            for box in boxes:
                # Extract coordinates (x1, y1, x2, y2)
                xyxy = box.xyxy[0].cpu().numpy()
                x1, y1, x2, y2 = map(int, xyxy)

                conf = float(box.conf[0].cpu().numpy())
                cls_id = int(box.cls[0].cpu().numpy())
                cls_name = self.model.names.get(cls_id, f"class_{cls_id}")

                # Calculate center coordinates
                # center_x = (x1 + x2) / 2
                # center_y = (y1 + y2) / 2
                w = float(x2 - x1)
                h = float(y2 - y1)
                center_x = (x1 + x2) / 2.0
                center_y = (y1 + y2) / 2.0

                detection = Detection(
                    box=(x1, y1, x2, y2),
                    confidence=conf,
                    class_name=cls_name,
                    class_id=cls_id,
                    center_x=center_x,
                    center_y=center_y,
                    width=w,
                    height=h,
                )
                detections.append(detection)

        except Exception as e:
            logger.error(f"Error during detection inference: {e}")

        return detections
