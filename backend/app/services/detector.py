"""YOLO inference with ONNX Runtime (no PyTorch needed in production).

The trained Ultralytics model is exported to ONNX (see ml/ notebook). This module
reproduces Ultralytics pre/post-processing: letterbox to 640, RGB/255, and
class-aware NMS on the (1, 4+nc, N) output. If MODEL_PATH points to a .pt file
and the `ultralytics` package is installed, it is used instead.

If no weights are present the service raises ModelUnavailable — the API then
returns 503 instead of inventing results.
"""
import ast
import io
import json
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

from ..config import get_settings

settings = get_settings()
_lock = threading.Lock()
_backend = None
_meta: dict | None = None
IMGSZ = 640

PALETTE = [(220, 38, 38), (234, 88, 12), (202, 138, 4), (22, 163, 74), (8, 145, 178),
           (37, 99, 235), (124, 58, 237), (219, 39, 119), (101, 163, 13), (13, 148, 136)]


class ModelUnavailable(RuntimeError):
    pass


class InvalidImage(ValueError):
    pass


@dataclass
class Box:
    pest_class: str
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float
    low_confidence: bool


@dataclass
class Result:
    boxes: list[Box]
    width: int
    height: int
    inference_ms: float
    annotated_jpeg: bytes
    original_jpeg: bytes


def model_meta() -> dict:
    global _meta
    if _meta is None:
        p = Path(settings.model_meta_path)
        _meta = json.loads(p.read_text()) if p.exists() else {}
    return _meta


def is_available() -> bool:
    return Path(settings.model_path).exists()


class OnnxBackend:
    def __init__(self, path: str):
        import onnxruntime as ort
        so = ort.SessionOptions()
        so.intra_op_num_threads = 2
        self.sess = ort.InferenceSession(path, so, providers=["CPUExecutionProvider"])
        self.inp = self.sess.get_inputs()[0].name
        names = model_meta().get("classes")
        if not names:
            raw = self.sess.get_modelmeta().custom_metadata_map.get("names")
            d = ast.literal_eval(raw) if raw else {}
            names = [d[k] for k in sorted(d)]
        self.names = names

    @staticmethod
    def letterbox(img: np.ndarray):
        h, w = img.shape[:2]
        r = min(IMGSZ / h, IMGSZ / w)
        nh, nw = round(h * r), round(w * r)
        resized = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR)
        top, left = (IMGSZ - nh) // 2, (IMGSZ - nw) // 2
        canvas = np.full((IMGSZ, IMGSZ, 3), 114, dtype=np.uint8)
        canvas[top:top + nh, left:left + nw] = resized
        return canvas, r, left, top

    def predict(self, rgb: np.ndarray, conf: float, iou: float, max_det: int = 300):
        canvas, r, dx, dy = self.letterbox(rgb)
        x = canvas.astype(np.float32).transpose(2, 0, 1)[None] / 255.0
        out = self.sess.run(None, {self.inp: x})[0][0]  # (4+nc, N)
        out = out.T
        boxes_xywh, scores_all = out[:, :4], out[:, 4:]
        cls = scores_all.argmax(1)
        scores = scores_all[np.arange(len(cls)), cls]
        keep = scores >= conf
        boxes_xywh, scores, cls = boxes_xywh[keep], scores[keep], cls[keep]
        if not len(scores):
            return []
        xyxy = np.empty_like(boxes_xywh)
        xyxy[:, 0] = boxes_xywh[:, 0] - boxes_xywh[:, 2] / 2
        xyxy[:, 1] = boxes_xywh[:, 1] - boxes_xywh[:, 3] / 2
        xyxy[:, 2] = boxes_xywh[:, 0] + boxes_xywh[:, 2] / 2
        xyxy[:, 3] = boxes_xywh[:, 1] + boxes_xywh[:, 3] / 2
        # class-aware NMS: offset boxes by class id (same trick as Ultralytics)
        off = xyxy + cls[:, None] * 4096.0
        rects = [[float(a), float(b), float(c - a), float(d - b)] for a, b, c, d in off]
        idx = cv2.dnn.NMSBoxes(rects, scores.astype(float).tolist(), conf, iou)
        idx = np.array(idx).flatten()[:max_det] if len(idx) else []
        h, w = rgb.shape[:2]
        res = []
        for i in idx:
            x1, y1, x2, y2 = xyxy[i]
            x1, x2 = np.clip([(x1 - dx) / r, (x2 - dx) / r], 0, w)
            y1, y2 = np.clip([(y1 - dy) / r, (y2 - dy) / r], 0, h)
            res.append((self.names[int(cls[i])], float(scores[i]), float(x1), float(y1), float(x2), float(y2)))
        return res


class UltralyticsBackend:
    def __init__(self, path: str):
        from ultralytics import YOLO
        self.model = YOLO(path)
        self.names = [self.model.names[i] for i in range(len(self.model.names))]

    def predict(self, rgb: np.ndarray, conf: float, iou: float, max_det: int = 300):
        p = self.model.predict(rgb[:, :, ::-1], conf=conf, iou=iou, imgsz=IMGSZ, verbose=False, max_det=max_det)[0]
        return [(self.names[int(c)], float(s), *map(float, b))
                for b, s, c in zip(p.boxes.xyxy.tolist(), p.boxes.conf.tolist(), p.boxes.cls.tolist())]


def _get_backend():
    global _backend
    if _backend is None:
        with _lock:
            if _backend is None:
                if not is_available():
                    raise ModelUnavailable(
                        f"Model weights not found at {settings.model_path}. Train the model (ml/ notebook) "
                        "and place best.onnx there.")
                path = settings.model_path
                _backend = UltralyticsBackend(path) if path.endswith(".pt") else OnnxBackend(path)
    return _backend


def class_names() -> list[str]:
    meta = model_meta().get("classes")
    if meta:
        return meta
    return _get_backend().names if is_available() else []


def load_image(data: bytes) -> Image.Image:
    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img).convert("RGB")
    except Exception as e:
        raise InvalidImage("The file is not a readable image (JPEG, PNG or WebP).") from e
    if min(img.size) < 64:
        raise InvalidImage("Image is too small (minimum 64x64 pixels).")
    img.thumbnail((1920, 1920))
    return img


def _annotate(img: Image.Image, boxes: list[Box], names: list[str]) -> bytes:
    out = img.copy()
    d = ImageDraw.Draw(out)
    lw = max(2, int(min(out.size) / 300))
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", max(12, int(min(out.size) / 45)))
    except OSError:
        font = ImageFont.load_default()
    idx = {n: i for i, n in enumerate(names)}
    for b in boxes:
        color = PALETTE[idx.get(b.pest_class, 0) % len(PALETTE)]
        d.rectangle([b.x1, b.y1, b.x2, b.y2], outline=color, width=lw)
        label = f"{b.pest_class} {b.confidence * 100:.0f}%" + (" (low)" if b.low_confidence else "")
        tb = d.textbbox((0, 0), label, font=font)
        tw, th = tb[2] - tb[0] + 8, tb[3] - tb[1] + 6
        y = b.y1 - th if b.y1 - th > 0 else b.y1
        d.rectangle([b.x1, y, b.x1 + tw, y + th], fill=color)
        d.text((b.x1 + 4, y + 2), label, fill=(255, 255, 255), font=font)
    buf = io.BytesIO()
    out.save(buf, "JPEG", quality=88)
    return buf.getvalue()


def detect(data: bytes) -> Result:
    img = load_image(data)
    backend = _get_backend()
    rgb = np.asarray(img)
    t = time.perf_counter()
    raw = backend.predict(rgb, settings.conf_threshold, settings.iou_threshold)
    ms = (time.perf_counter() - t) * 1000
    boxes = [Box(n, round(s, 4), round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1),
                 low_confidence=s < settings.low_conf_threshold) for n, s, x1, y1, x2, y2 in raw]
    boxes.sort(key=lambda b: -b.confidence)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90)
    return Result(boxes, img.width, img.height, round(ms, 1), _annotate(img, boxes, backend.names), buf.getvalue())
