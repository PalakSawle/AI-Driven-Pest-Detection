"""Fine-tune a YOLO detector on the prepared IP102 YOLO dataset.

Usage:  python train.py --data /content/ip102_yolo/data.yaml --model yolo11s.pt --epochs 40
Outputs: runs/agriguard/<name>/weights/best.pt plus training logs (results.csv).
Resume after a Colab disconnect:  python train.py --resume runs/agriguard/<name>/weights/last.pt
"""
import argparse

from ultralytics import YOLO


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="/content/ip102_yolo/data.yaml")
    ap.add_argument("--model", default="yolo11s.pt")
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--project", default="runs/agriguard")
    ap.add_argument("--name", default="ip102_yolo11s")
    ap.add_argument("--resume", default="")
    ap.add_argument("--device", default="0", help='"0", "0,1" for 2 GPUs (DDP), or "cpu"')
    a = ap.parse_args()

    if a.resume:
        YOLO(a.resume).train(resume=True)
        return
    model = YOLO(a.model)  # COCO-pretrained weights -> transfer learning
    model.train(
        data=a.data, epochs=a.epochs, imgsz=a.imgsz, batch=a.batch,
        project=a.project, name=a.name, exist_ok=True,
        patience=15, save_period=5, seed=42, deterministic=False,
        cos_lr=True, close_mosaic=5, workers=4, plots=True, device=a.device,
    )


if __name__ == "__main__":
    main()
