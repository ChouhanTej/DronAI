import os
import yaml
import torch
from pathlib import Path
from ultralytics import YOLO

def main():
    base_dir = Path(__file__).parent.resolve()
    yaml_path = base_dir / "data.yaml"
    
    print(f"Dataset root: {base_dir}")
    print(f"Loading configuration from: {yaml_path}")
    
    with open(yaml_path, 'r') as f:
        data_config = yaml.safe_load(f)
    
    # Create runtime configuration with resolved paths without modifying original data.yaml
    data_config['path'] = str(base_dir)
    data_config['train'] = 'train/images'
    data_config['val'] = 'valid/images'
    data_config['test'] = 'test/images'
    
    runtime_yaml_path = base_dir / ".runtime_data.yaml"
    with open(runtime_yaml_path, 'w') as f:
        yaml.dump(data_config, f)
        
    print(f"Runtime dataset config prepared at: {runtime_yaml_path}")
    print(f"Classes ({data_config.get('nc')}): {data_config.get('names')}")
    
    # Detect device (Apple Silicon MPS GPU / CUDA / CPU)
    if torch.backends.mps.is_available():
        device = 'mps'
    elif torch.cuda.is_available():
        device = 0
    else:
        device = 'cpu'
        
    print(f"Using compute device: {device}")
    
    # Load YOLOv8n lightweight nano model
    model = YOLO("yolov8n.pt")
    
    # Train for 30 epochs
    print("Starting YOLOv8n model training...")
    results = model.train(
        data=str(runtime_yaml_path),
        epochs=30,
        imgsz=640,
        batch=16,
        device=device,
        project=str(base_dir / "runs" / "detect"),
        name="train",
        exist_ok=True,
        workers=4,
        verbose=True
    )
    
    best_model_path = base_dir / "runs" / "detect" / "train" / "weights" / "best.pt"
    print("\n" + "="*60)
    print("TRAINING COMPLETED SUCCESSFULLY!")
    print(f"Best model weights saved at: {best_model_path}")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
