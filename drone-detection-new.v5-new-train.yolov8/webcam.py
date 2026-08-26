import cv2
import time
import torch
from pathlib import Path
from ultralytics import YOLO

def main():
    base_dir = Path(__file__).parent.resolve()
    best_model_path = base_dir / "runs" / "detect" / "train" / "weights" / "best.pt"
    
    if best_model_path.exists():
        print(f"Loading trained model from: {best_model_path}")
        model_path = str(best_model_path)
    else:
        print(f"Warning: Trained model {best_model_path} not found. Falling back to base yolov8n.pt.")
        model_path = "yolov8n.pt"
        
    model = YOLO(model_path)
    
    # Device selection (Apple Silicon MPS / CUDA / CPU)
    if torch.backends.mps.is_available():
        device = 'mps'
    elif torch.cuda.is_available():
        device = 0
    else:
        device = 'cpu'
        
    print(f"Running real-time detection on Mac webcam using device: {device}")
    
    # Open Mac webcam (camera index 0)
    cap = cv2.VideoCapture(0)
    
    # Set camera resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    if not cap.isOpened():
        print("Error: Could not access Mac webcam (cv2.VideoCapture(0)). Please check camera permissions.")
        return
        
    print("\nLive webcam feed started!")
    print("Press 'q' or 'ESC' in the webcam window to quit.\n")
    
    prev_time = time.time()
    fps = 0.0
    
    # Color palette (BGR format)
    DRONE_COLOR = (0, 0, 255)       # Bright Red/Magenta for Drone
    AIRPLANE_COLOR = (255, 255, 0)   # Cyan for AirPlane
    HELICOPTER_COLOR = (0, 255, 255) # Yellow for Helicopter
    DEFAULT_COLOR = (0, 255, 0)     # Green default
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("Failed to capture frame from webcam.")
            break
            
        # Calculate FPS
        curr_time = time.time()
        time_diff = curr_time - prev_time
        if time_diff > 0:
            fps = 1.0 / time_diff
        prev_time = curr_time
        
        # Perform YOLO inference
        results = model.predict(frame, conf=0.35, device=device, verbose=False)
        
        drone_detected = False
        drone_count = 0
        
        for result in results:
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                class_name = model.names[cls_id]
                
                # Check if class is Drone
                is_drone = class_name.lower() == "drone" or cls_id == 1
                
                if is_drone:
                    drone_detected = True
                    drone_count += 1
                    color = DRONE_COLOR
                    thickness = 4  # Thick bold box for Drone
                    label = f"⚠️ DRONE: {conf*100:.1f}%"
                else:
                    thickness = 2
                    if "airplane" in class_name.lower() or cls_id == 0:
                        color = AIRPLANE_COLOR
                    elif "helicopter" in class_name.lower() or cls_id == 2:
                        color = HELICOPTER_COLOR
                    else:
                        color = DEFAULT_COLOR
                    label = f"{class_name.upper()}: {conf*100:.1f}%"
                    
                # Draw bounding box
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
                
                # Draw label background box
                (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
                cv2.rectangle(frame, (x1, y1 - 25), (x1 + w + 10, y1), color, -1)
                
                # Draw label text
                text_color = (255, 255, 255)
                cv2.putText(frame, label, (x1 + 5, y1 - 7), cv2.FONT_HERSHEY_SIMPLEX, 0.7, text_color, 2)
                
        # Top banner overlay if Drone is detected
        if drone_detected:
            # Red alert banner across top
            cv2.rectangle(frame, (0, 0), (frame.shape[1], 45), (0, 0, 200), -1)
            alert_text = f"🚨 ALERT: {drone_count} DRONE(S) DETECTED! 🚨"
            (tw, th), _ = cv2.getTextSize(alert_text, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)
            tx = (frame.shape[1] - tw) // 2
            cv2.putText(frame, alert_text, (tx, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
            
        # Draw FPS overlay
        fps_text = f"FPS: {fps:.1f}"
        cv2.rectangle(frame, (10, frame.shape[0] - 45), (150, frame.shape[0] - 10), (0, 0, 0), -1)
        cv2.putText(frame, fps_text, (20, frame.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Display frame
        cv2.imshow("Anti-Drone Prototype - Real-time Detection", frame)
        
        # Break loop on 'q' or ESC key press
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:
            break
            
    cap.release()
    cv2.destroyAllWindows()
    print("Webcam stream stopped.")

if __name__ == "__main__":
    main()
