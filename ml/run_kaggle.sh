#!/usr/bin/env bash
# End-to-end training on a Kaggle GPU notebook.
# Requirements: Internet ON, Accelerator GPU, dataset "parserpixy/ip102-dataset" added as input.
# Outputs land in /kaggle/working (kept when the notebook is saved with "Save & Run All").
set -euo pipefail
cd /kaggle/working
W=/kaggle/working
ML=$W/ml
# Dataset: IP102 detection subset mirrored on Kaggle as parserpixy/ip102-dataset (VOC XML + official test split)
TV=$(find /kaggle/input -maxdepth 5 -name trainval.txt -print -quit 2>/dev/null || true)
if [ -n "$TV" ]; then
  DATA=$(dirname "$TV")
else
  DATA=$(python -c "import kagglehub; print(kagglehub.dataset_download('parserpixy/ip102-dataset'))")
fi
echo "IP102 data at: $DATA"; du -sh "$DATA" || true
nvidia-smi -L

pip -q install "ultralytics==8.3.*" onnx onnxslim onnxruntime 2>&1 | tail -2

echo "=== 1/4 prepare dataset ==="
python -u $ML/dataset/prepare_ip102.py --work "$DATA" --skip-download --cache $W --out $W/ip102_yolo

echo "=== 2/4 train ==="
NGPU=$(nvidia-smi -L | wc -l)
DEV=0; [ "$NGPU" -ge 2 ] && DEV=0,1
python -u $ML/training/train.py --data $W/ip102_yolo/data.yaml --model yolo11s.pt --epochs ${EPOCHS:-35} --batch 32 \
  --device $DEV --project $W/runs --name ip102_yolo11s \
|| { echo "multi-GPU run failed, retrying on one GPU"; python -u $ML/training/train.py --data $W/ip102_yolo/data.yaml \
  --model yolo11s.pt --epochs ${EPOCHS:-35} --batch 32 --device 0 --project $W/runs --name ip102_yolo11s; }

echo "=== 3/4 evaluate on held-out test split ==="
python $ML/training/evaluate.py --weights $W/runs/ip102_yolo11s/weights/best.pt --data $W/ip102_yolo/data.yaml \
  --stats $W/ip102_yolo/dataset_stats.json --out $W/eval_out

echo "=== 4/4 export ONNX + package ==="
OUT=$W/agriguard_model
mkdir -p $OUT
cp $W/runs/ip102_yolo11s/weights/best.pt $OUT/
cp $W/runs/ip102_yolo11s/results.csv $W/runs/ip102_yolo11s/args.yaml $OUT/ 2>/dev/null || true
cp $W/runs/ip102_yolo11s/*.png $OUT/ 2>/dev/null || true
cp $W/eval_out/*.json $W/eval_out/*.png $OUT/ 2>/dev/null || true
cp $W/ip102_yolo/dataset_stats.json $OUT/
python - <<EOF
from ultralytics import YOLO
p = YOLO("$OUT/best.pt").export(format="onnx", imgsz=640, opset=12, simplify=True, dynamic=False)
import shutil; shutil.copy(p, "$OUT/best.onnx"); print("onnx:", p)
EOF
cd $W && rm -f agriguard_model.zip && zip -qr agriguard_model.zip agriguard_model
# free space: Kaggle only keeps /kaggle/working up to 20 GB
rm -rf $W/ip102_yolo/images
ls -la $OUT
echo "DONE — download agriguard_model.zip from the notebook Output tab."
