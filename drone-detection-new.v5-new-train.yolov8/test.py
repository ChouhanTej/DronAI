import os
import glob
from pathlib import Path
from ultralytics import YOLO
import torch

def main():
    base_dir = Path(__file__).parent.resolve()
    best_model_path = base_dir / "runs" / "detect" / "train" / "weights" / "best.pt"
    
    if not best_model_path.exists():
        print(f"Error: Model file not found at {best_model_path}. Please run train.py first.")
        return
        
    print(f"Loading trained YOLOv8 model from: {best_model_path}")
    model = YOLO(str(best_model_path))
    
    runtime_yaml_path = base_dir / ".runtime_data.yaml"
    data_source = str(runtime_yaml_path) if runtime_yaml_path.exists() else str(base_dir / "data.yaml")
    
    if torch.backends.mps.is_available():
        device = 'mps'
    elif torch.cuda.is_available():
        device = 0
    else:
        device = 'cpu'

    print(f"Using compute device: {device}")
    
    print("\n--- Evaluating Model Metrics on Test Split ---")
    try:
        metrics = model.val(data=data_source, split="test", device=device, project=str(base_dir / "runs" / "detect"), name="val_test", exist_ok=True)
        print(f"mAP50-95:  {metrics.box.map:.4f}")
        print(f"mAP50:     {metrics.box.map50:.4f}")
        print(f"Precision: {metrics.box.mp:.4f}")
        print(f"Recall:    {metrics.box.mr:.4f}")
    except Exception as e:
        print(f"Validation evaluation warning: {e}")

    test_images_dir = base_dir / "test" / "images"
    test_images = list(test_images_dir.glob("*.jpg")) + list(test_images_dir.glob("*.png")) + list(test_images_dir.glob("*.jpeg"))
    
    print(f"\nFound {len(test_images)} test images in {test_images_dir}.")
    if test_images:
        print("Running batch prediction on test images...")
        output_dir = base_dir / "runs" / "detect" / "test_predictions"
        results = model.predict(
            source=str(test_images_dir),
            save=True,
            conf=0.25,
            device=device,
            project=str(base_dir / "runs" / "detect"),
            name="test_predictions",
            exist_ok=True
        )
        print(f"Sample annotated images saved to: {output_dir}")

if __name__ == "__main__":
    main()
