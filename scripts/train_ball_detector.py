"""
Train a YOLOv8n tennis ball detector on the Roboflow dataset.

Usage:
    uv run python scripts/train_ball_detector.py [--epochs N] [--device DEVICE]

Output:
    weights/yolov8n_tennis_ball.pt
"""
import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_YAML = ROOT / "data" / "tennis_ball" / "data.yaml"
OUTPUT_WEIGHTS = ROOT / "weights" / "yolov8n_tennis_ball.pt"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--device", type=str, default="mps", help="cpu | mps | 0 (CUDA)")
    args = parser.parse_args()

    from ultralytics import YOLO

    print(f"Training for {args.epochs} epochs on {args.device}")
    print(f"Data: {DATA_YAML}")

    model = YOLO("yolov8n.pt")
    results = model.train(
        data=str(DATA_YAML),
        epochs=args.epochs,
        imgsz=640,
        device=args.device,
        project=str(ROOT / "runs" / "train"),
        name="tennis_ball",
        exist_ok=True,
        verbose=False,
    )

    best = Path(results.save_dir) / "weights" / "best.pt"
    if best.exists():
        shutil.copy(best, OUTPUT_WEIGHTS)
        print(f"Saved: {OUTPUT_WEIGHTS}")
    else:
        print(f"ERROR: best.pt not found at {best}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
