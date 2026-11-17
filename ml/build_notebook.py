"""Builds ml/AgriGuard_Train_IP102.ipynb from the scripts in this folder."""
import json
from pathlib import Path

here = Path(__file__).parent
def md(s): return {"cell_type": "markdown", "metadata": {}, "source": s}
def code(s): return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": s}

cells = [
 md("# AgriGuard AI — train the pest detector on IP102 (Colab GPU)\n\n"
    "1. **Runtime → Change runtime type → T4 GPU → Save**\n2. **Runtime → Run all**\n"
    "3. Allow Google Drive access when asked (checkpoints are saved there so a disconnect doesn't lose training).\n"
    "4. When the last cell finishes, `agriguard_model.zip` downloads automatically. Leave it in your Downloads folder.\n\n"
    "Dataset: IP102 detection subset (Wu et al., CVPR 2019), official Google Drive mirror linked from https://github.com/xpwu95/IP102. "
    "Model: Ultralytics YOLO11s fine-tuned from COCO weights. Expected time on a T4: about 2–3 hours."),
 code("!nvidia-smi -L\nimport torch; assert torch.cuda.is_available(), 'No GPU! Runtime > Change runtime type > T4 GPU'"),
 code("from google.colab import drive\ndrive.mount('/content/drive')\n!mkdir -p /content/drive/MyDrive/agriguard_runs"),
 code("!pip -q install ultralytics==8.3.* gdown onnx onnxslim onnxruntime\n!mkdir -p /content/ag"),
]
for rel in ["dataset/prepare_ip102.py", "training/train.py", "training/evaluate.py"]:
    src = (here / rel).read_text()
    cells.append(code(f"%%writefile /content/ag/{Path(rel).name}\n{src}"))
cells += [
 md("## 1. Download, clean, convert and split IP102 (~15–25 min)"),
 code("!cd /content/ag && python prepare_ip102.py --work /content/ip102 --out /content/ip102_yolo"),
 md("## 2. Train (resumes automatically from Drive if a previous session was cut off)"),
 code("import os\nlast = '/content/drive/MyDrive/agriguard_runs/ip102_yolo11s/weights/last.pt'\n"
      "if os.path.exists(last):\n    !cd /content/ag && python train.py --resume {last}\n"
      "else:\n    !cd /content/ag && python train.py --data /content/ip102_yolo/data.yaml --model yolo11s.pt --epochs 35 --batch 32 --project /content/drive/MyDrive/agriguard_runs --name ip102_yolo11s"),
 md("## 3. Evaluate on the held-out TEST split"),
 code("!cd /content/ag && python evaluate.py --weights /content/drive/MyDrive/agriguard_runs/ip102_yolo11s/weights/best.pt "
      "--data /content/ip102_yolo/data.yaml --stats /content/ip102_yolo/dataset_stats.json --out /content/eval_out"),
 md("## 4. Package and download"),
 code("import shutil, os\nrun = '/content/drive/MyDrive/agriguard_runs/ip102_yolo11s'\nout = '/content/agriguard_model'\n"
      "os.makedirs(out, exist_ok=True)\nshutil.copy(f'{run}/weights/best.pt', out)\n"
      "for f in ['results.csv', 'results.png', 'args.yaml']:\n    if os.path.exists(f'{run}/{f}'): shutil.copy(f'{run}/{f}', out)\n"
      "for f in os.listdir('/content/eval_out'):\n    p = f'/content/eval_out/{f}'\n    if os.path.isfile(p): shutil.copy(p, out)\n"
      "shutil.copy('/content/ip102_yolo/dataset_stats.json', out)\n"
      "from ultralytics import YOLO\nonnx_path = YOLO(f'{out}/best.pt').export(format='onnx', imgsz=640, opset=12, simplify=True, dynamic=False)\n"
      "shutil.copy(onnx_path, f'{out}/best.onnx')\n"
      "shutil.make_archive('/content/agriguard_model', 'zip', out)\n"
      "shutil.copy('/content/agriguard_model.zip', '/content/drive/MyDrive/agriguard_runs/agriguard_model.zip')\n"
      "print(os.listdir(out))\nfrom google.colab import files\nfiles.download('/content/agriguard_model.zip')"),
]
nb = {"cells": cells, "metadata": {"accelerator": "GPU", "colab": {"gpuType": "T4", "provenance": []},
      "kernelspec": {"name": "python3", "display_name": "Python 3"}}, "nbformat": 4, "nbformat_minor": 0}
for c in nb["cells"]:
    c["source"] = c["source"].splitlines(keepends=True)
(here / "AgriGuard_Train_IP102.ipynb").write_text(json.dumps(nb, indent=1))
print("written")
