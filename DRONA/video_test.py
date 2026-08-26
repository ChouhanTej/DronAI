"""
Anti-Drone System - Video Testing Utility
Processes a video file (or camera feed), runs YOLO object detection, multi-drone tracking,
trajectory rendering, and target telemetry calculation, saving annotated output to
runs/detect/video_predictions/.

Usage:
    .venv/bin/python video_test.py --source path/to/drone_video.mp4
    .venv/bin/python video_test.py --source 0
"""

import argparse
import sys
import time
from pathlib import Path
import cv2
import numpy as np

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.detector import YOLOObjectDetector
from src.tracker import DroneTracker
from src.target import TargetAnalyzer


def process_video(source_path: str, output_dir: Path):
    model_path = PROJECT_ROOT / "models" / "best.pt"
    if not model_path.exists():
        print(f"Error: Model file not found at {model_path}")
        return

    detector = YOLOObjectDetector(model_path=model_path, confidence_threshold=0.25)
    tracker = DroneTracker(max_lost_frames=15)
    analyzer = TargetAnalyzer(dead_zone_x=50, dead_zone_y=50)

    is_cam = source_path.isdigit()
    cap_src = int(source_path) if is_cam else source_path

    cap = cv2.VideoCapture(cap_src)
    if not cap.isOpened():
        print(f"Error: Unable to open video source: {source_path}")
        return

    # Extract Video Properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1280
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 720
    fps_in = cap.get(cv2.CAP_PROP_FPS)
    fps_out = fps_in if (fps_in and fps_in > 0 and fps_in <= 120) else 30.0

    output_dir.mkdir(parents=True, exist_ok=True)
    out_filename = "webcam_predictions.mp4" if is_cam else f"pred_{Path(source_path).name}"
    out_filepath = output_dir / out_filename

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_filepath), fourcc, fps_out, (width, height))

    print(f"\nProcessing video source: {source_path}")
    print(f"Frame resolution: {width}x{height} | Output FPS: {fps_out:.1f}")
    print(f"Saving predictions to: {out_filepath}")
    print("Press 'q' or 'ESC' in preview window to stop processing.\n")

    frame_count = 0
    start_time = time.time()
    prev_time = time.time()
    fps = 0.0

    cv2.namedWindow("Anti-Drone Video Testing", cv2.WINDOW_NORMAL)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret or frame is None:
            break

        frame_count += 1
        curr_time = time.time()
        dt = curr_time - prev_time
        if dt > 0:
            fps = 0.85 * fps + 0.15 * (1.0 / dt)
        prev_time = curr_time

        # 1. Detection
        detections = detector.detect(frame)

        # 2. Multi-Drone Tracking
        active_drones = tracker.update(detections)

        # 3. Visualization & Telemetry
        frame_center = (width // 2, height // 2)

        # Draw frame center crosshair
        cv2.line(frame, (frame_center[0], 0), (frame_center[0], height), (0, 255, 255), 1)
        cv2.line(frame, (0, frame_center[1]), (width, frame_center[1]), (0, 255, 255), 1)

        primary_drone = None
        if active_drones:
            primary_drone = max(active_drones, key=lambda d: d.confidence)

        for drone in active_drones:
            is_primary = primary_drone and drone.track_id == primary_drone.track_id
            box_color = (0, 0, 255) if is_primary else (0, 165, 255)
            thickness = 3 if is_primary else 2

            cv2.rectangle(frame, (drone.x1, drone.y1), (drone.x2, drone.y2), box_color, thickness)
            cv2.circle(frame, (int(drone.center_x), int(drone.center_y)), 4, box_color, -1)

            label_str = f"{drone.label} ({drone.confidence*100:.0f}%)"
            cv2.putText(
                frame,
                label_str,
                (drone.x1, max(drone.y1 - 7, 15)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                box_color,
                2,
            )

            # Draw trajectory
            points = list(drone.history)
            for i in range(1, len(points)):
                cv2.line(frame, points[i - 1], points[i], (0, 255, 0), 2)

        if primary_drone:
            telemetry = analyzer.analyze(primary_drone, width, height)
            cv2.line(frame, frame_center, telemetry.drone_center, (0, 255, 0), 2)

            osd_text = f"TARGET: {telemetry.label} | Err: ({telemetry.error_x:+d}, {telemetry.error_y:+d}) | PAN:{telemetry.pan_direction} TILT:{telemetry.tilt_direction}"
            cv2.putText(frame, osd_text, (20, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Write frame to output video file
        writer.write(frame)

        # Display preview
        fps_str = f"FPS: {fps:.1f} | Frame: {frame_count}"
        cv2.putText(frame, fps_str, (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
        cv2.imshow("Anti-Drone Video Testing", frame)

        key = cv2.waitKey(1) & 0xFF
        if key in (ord('q'), ord('Q'), 27):
            print("Stopping video processing...")
            break

    cap.release()
    writer.release()
    cv2.destroyAllWindows()

    elapsed = time.time() - start_time
    avg_fps = frame_count / elapsed if elapsed > 0 else 0
    print(f"\nProcessing complete!")
    print(f"Total Frames Processed: {frame_count}")
    print(f"Average Processing FPS: {avg_fps:.1f}")
    print(f"Annotated output saved to: {out_filepath}")


def main():
    parser = argparse.ArgumentParser(description="Anti-Drone System Video Test Tool")
    parser.add_argument("--source", type=str, required=True, help="Path to input video file or webcam index (e.g. 0)")
    args = parser.parse_args()

    out_dir = PROJECT_ROOT / "runs" / "detect" / "video_predictions"
    process_video(args.source, out_dir)


if __name__ == "__main__":
    main()
