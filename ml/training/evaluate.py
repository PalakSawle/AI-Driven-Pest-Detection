"""Evaluate trained weights on the held-out TEST split and write model_meta.json.

Reports precision, recall, F1, mAP@0.5 and mAP@0.5:0.95 (overall and per class)
and saves the confusion matrix produced by Ultralytics.

Usage: python evaluate.py --weights best.pt --data data.yaml --stats dataset_stats.json --out eval_out
"""
import argparse
import json
import shutil
import time
from pathlib import Path

from ultralytics import YOLO


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--stats", default="")
    ap.add_argument("--out", default="eval_out")
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--version", default="1.0.0")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

    model = YOLO(a.weights)
    t = time.time()
    r = model.val(data=a.data, split="test", imgsz=a.imgsz, batch=32, plots=True,
                  project=str(out), name="test", exist_ok=True)
    names = model.names
    p, rc = float(r.box.mp), float(r.box.mr)
    f1 = 2 * p * rc / (p + rc) if p + rc else 0.0
    per_class = {}
    for i, c in enumerate(r.box.ap_class_index):
        c = int(c)
        pc, rcc = float(r.box.p[i]), float(r.box.r[i])
        per_class[names[c]] = {
            "precision": round(pc, 4), "recall": round(rcc, 4),
            "f1": round(2 * pc * rcc / (pc + rcc), 4) if pc + rcc else 0.0,
            "map50": round(float(r.box.ap50[i]), 4), "map50_95": round(float(r.box.ap[i]), 4),
        }
    metrics = {
        "split": "test",
        "precision": round(p, 4), "recall": round(rc, 4), "f1": round(f1, 4),
        "map50": round(float(r.box.map50), 4), "map50_95": round(float(r.box.map), 4),
        "speed_ms_per_image": {k: round(v, 2) for k, v in r.speed.items()},
        "eval_seconds": round(time.time() - t, 1),
        "per_class": per_class,
    }
    stats = json.loads(Path(a.stats).read_text()) if a.stats else {}
    meta = {
        "name": "AgriGuard Pest Detector",
        "version": a.version,
        "architecture": f"Ultralytics {Path(a.weights).name} ({model.model.yaml.get('yaml_file', 'YOLO')})",
        "dataset": stats.get("dataset", "IP102 detection subset"),
        "dataset_source": stats.get("homepage", ""),
        "classes": [names[i] for i in range(len(names))],
        "metrics": metrics,
        "dataset_stats": {k: v for k, v in stats.items() if k != "classes"},
    }
    (out / "model_meta.json").write_text(json.dumps(meta, indent=2))
    for f in (out / "test").glob("*.png"):
        shutil.copy2(f, out / f.name)
    print(json.dumps({k: v for k, v in metrics.items() if k != "per_class"}, indent=2))


if __name__ == "__main__":
    main()
