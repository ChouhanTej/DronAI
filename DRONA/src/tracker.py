"""
Drone Tracking Module
Tracks ONLY objects classified as 'Drone', assigning persistent IDs ('Drone #1', 'Drone #2'),
maintaining trajectory history (up to 30 center points), and handling lost-frame grace periods.
"""

from collections import deque
import math
from typing import List, Dict, Tuple, Optional
from src.detector import Detection

MAX_TRACK_LOST_FRAMES = 15
TRAJECTORY_MAX_LEN = 30
DISTANCE_THRESHOLD_PIXELS = 150.0
IOU_THRESHOLD = 0.20


class TrackedDrone:
    """Represents a single tracked drone entity across frames."""

    def __init__(self, track_id: int, initial_detection: Detection):
        self.track_id: int = track_id
        self.label: str = f"Drone #{track_id}"
        self.class_id: int = initial_detection.class_id
        self.class_name: str = initial_detection.class_name
        self.confidence: float = initial_detection.confidence

        self.x1: int = initial_detection.x1
        self.y1: int = initial_detection.y1
        self.x2: int = initial_detection.x2
        self.y2: int = initial_detection.y2

        self.center_x: float = (self.x1 + self.x2) / 2.0
        self.center_y: float = (self.y1 + self.y2) / 2.0

        self.history: deque = deque(maxlen=TRAJECTORY_MAX_LEN)
        self.history.append((int(self.center_x), int(self.center_y)))

        self.lost_frames: int = 0

    def update(self, detection: Detection):
        """Updates drone state with a new frame detection."""
        self.confidence = detection.confidence
        self.x1 = detection.x1
        self.y1 = detection.y1
        self.x2 = detection.x2
        self.y2 = detection.y2
        self.center_x = (self.x1 + self.x2) / 2.0
        self.center_y = (self.y1 + self.y2) / 2.0

        self.history.append((int(self.center_x), int(self.center_y)))
        self.lost_frames = 0

    @property
    def box(self) -> Tuple[int, int, int, int]:
        return (self.x1, self.y1, self.x2, self.y2)


class DroneTracker:
    """Multi-drone tracker maintaining persistent IDs and trajectory history using global cost matching."""

    def __init__(self, max_lost_frames: int = MAX_TRACK_LOST_FRAMES):
        self.max_lost_frames = max_lost_frames
        self.tracked_drones: Dict[int, TrackedDrone] = {}
        self.next_id: int = 1

    def update(self, detections: List[Detection]) -> List[TrackedDrone]:
        """
        Updates tracking state with detections from current frame.
        Only filters for detections classified as 'Drone' (class_id == 1 or 'drone' in class_name).

        Args:
            detections: List of Detection objects from YOLO detector.

        Returns:
            List of active TrackedDrone objects.
        """
        # Filter for drone class only
        drone_detections = [
            d for d in detections
            if d.class_id == 1 or "drone" in d.class_name.lower()
        ]

        # Calculate all valid track-to-detection assignment costs
        candidate_pairs = []
        for track_id, tracked_drone in self.tracked_drones.items():
            for idx, det in enumerate(drone_detections):
                dist = math.hypot(det.center_x - tracked_drone.center_x, det.center_y - tracked_drone.center_y)
                iou = self._calculate_iou(tracked_drone.box, det.box)

                if dist < DISTANCE_THRESHOLD_PIXELS or iou > IOU_THRESHOLD:
                    # Cost combines Euclidean distance weighted by IoU bonus
                    cost = dist * (1.0 - 0.5 * iou)
                    candidate_pairs.append((cost, track_id, idx))

        # Global optimal matching: sort pairs by ascending cost
        candidate_pairs.sort(key=lambda x: x[0])

        matched_track_ids = set()
        matched_det_indices = set()

        for cost, track_id, det_idx in candidate_pairs:
            if track_id not in matched_track_ids and det_idx not in matched_det_indices:
                matched_track_ids.add(track_id)
                matched_det_indices.add(det_idx)
                self.tracked_drones[track_id].update(drone_detections[det_idx])

        # Handle unmatched active tracks
        for track_id, tracked_drone in list(self.tracked_drones.items()):
            if track_id not in matched_track_ids:
                tracked_drone.lost_frames += 1
                if tracked_drone.lost_frames > self.max_lost_frames:
                    del self.tracked_drones[track_id]

        # Register new persistent tracks for unmatched drone detections
        for idx, det in enumerate(drone_detections):
            if idx not in matched_det_indices:
                new_drone = TrackedDrone(self.next_id, det)
                self.tracked_drones[self.next_id] = new_drone
                self.next_id += 1

        return list(self.tracked_drones.values())

    @staticmethod
    def _calculate_iou(boxA: Tuple[int, int, int, int], boxB: Tuple[int, int, int, int]) -> float:
        """Calculates Intersection over Union (IoU) between two bounding boxes."""
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])

        interArea = max(0, xB - xA) * max(0, yB - yA)
        boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
        boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])

        iou = interArea / float(boxAArea + boxBArea - interArea + 1e-6)
        return iou
