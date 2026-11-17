"""Test setup: temporary SQLite DB, temp upload dir and a tiny stand-in ONNX model.

The stand-in model is a TEST FIXTURE ONLY. It has the exact input/output
signature of an Ultralytics YOLO ONNX export, (1,3,640,640) -> (1, 4+nc, N),
and returns fixed candidate boxes so the real pre/post-processing, NMS,
storage, density, severity, alert and export code paths can be exercised
deterministically. Production uses the trained IP102 model.
"""
import io
import json
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

TMP = Path(tempfile.mkdtemp(prefix="agriguard_test_"))
CLASSES = ["brown plant hopper", "aphids", "rice leaf roller"]


def build_stub_onnx(path: Path):
    import onnx
    from onnx import TensorProto, helper
    # candidates in 640x640 letterbox space: cx, cy, w, h, scores...
    cands = [
        (100, 200, 40, 40, [0.90, 0.01, 0.01]),   # BPH
        (102, 202, 40, 40, [0.80, 0.01, 0.01]),   # duplicate of the above -> removed by NMS
        (300, 300, 50, 50, [0.85, 0.02, 0.01]),   # BPH
        (400, 250, 30, 30, [0.35, 0.02, 0.01]),   # BPH, low confidence (< 0.40) but above 0.25
        (500, 400, 60, 60, [0.02, 0.75, 0.01]),   # aphid
        (200, 500, 60, 60, [0.10, 0.05, 0.12]),   # below conf threshold -> dropped
    ]
    n = len(cands)
    arr = np.zeros((1, 4 + len(CLASSES), n), dtype=np.float32)
    for j, (cx, cy, w, h, s) in enumerate(cands):
        arr[0, :4, j] = (cx, cy, w, h)
        arr[0, 4:, j] = s
    const = helper.make_node("Constant", [], ["output0"], value=helper.make_tensor(
        "v", TensorProto.FLOAT, arr.shape, arr.flatten().tolist()))
    graph = helper.make_graph([const], "stub",
                              [helper.make_tensor_value_info("images", TensorProto.FLOAT, [1, 3, 640, 640])],
                              [helper.make_tensor_value_info("output0", TensorProto.FLOAT, list(arr.shape))])
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 12)])
    model.ir_version = 8
    onnx.save(model, str(path))


(TMP / "weights").mkdir(parents=True, exist_ok=True)
build_stub_onnx(TMP / "weights" / "best.onnx")
(TMP / "weights" / "model_meta.json").write_text(json.dumps({
    "name": "Test stub", "version": "test-0", "architecture": "stub", "dataset": "test", "classes": CLASSES,
    "metrics": {"map50": 0.0}}))

os.environ.update({
    "DATABASE_URL": f"sqlite:///{TMP / 'test.db'}",
    "MODEL_PATH": str(TMP / "weights" / "best.onnx"),
    "MODEL_META_PATH": str(TMP / "weights" / "model_meta.json"),
    "UPLOAD_DIR": str(TMP / "uploads"),
    "JWT_SECRET": "test-secret",
    "LLM_PROVIDER": "none",
    "RATE_LIMIT_DETECT": "1000/minute", "RATE_LIMIT_CHAT": "1000/minute", "RATE_LIMIT_AUTH": "1000/minute",
    "ADMIN_EMAIL": "admin@test.in", "ADMIN_PASSWORD": "AdminPass123",
})
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from app.limiter import limiter  # noqa: E402
from app.main import app  # noqa: E402

limiter.enabled = False


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def _register(client, email, name="Ramesh Kumar"):
    r = client.post("/api/auth/register", json={"email": email, "password": "Secret123!", "full_name": name})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def auth(client):
    return _register(client, "farmer1@test.in")


@pytest.fixture(scope="session")
def auth2(client):
    return _register(client, "farmer2@test.in", "Sita Devi")


@pytest.fixture
def jpeg():
    img = Image.new("RGB", (800, 600), (90, 140, 60))
    buf = io.BytesIO()
    img.save(buf, "JPEG")
    return buf.getvalue()
