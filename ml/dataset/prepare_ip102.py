"""Download, verify, clean and convert the IP102 detection subset to YOLO format.

Source: IP102 (Wu et al., CVPR 2019), official Google Drive folder linked from
https://github.com/xpwu95/IP102 . No explicit licence file is published; the
authors ask for citation. Use for research/education and cite the paper.

Steps (all re-runnable):
 1. Download only the Detection files from the official Drive folder (gdown).
 2. Extract the tar archives.
 3. Parse Pascal-VOC XML annotations; map numeric labels to classes.txt names.
 4. Validate: unreadable/corrupt images, empty or out-of-bounds boxes, unknown labels.
 5. Remove exact duplicate images (SHA-1) — duplicates are kept in ONE split only.
 6. Split using the official trainval/test lists when present (val carved from
    trainval with a fixed seed), otherwise a stratified 80/10/10 split.
 7. Write YOLO labels, data.yaml and dataset_stats.json.

Usage (Colab, downloads from Drive):
    python prepare_ip102.py --work /content/ip102 --out /content/ip102_yolo
Usage (Kaggle, dataset "parserpixy/ip102-dataset" attached as input — same IP102 detection subset, VOC format):
    python prepare_ip102.py --work /kaggle/input/ip102-dataset --skip-download --cache /kaggle/working --out /kaggle/working/ip102_yolo
"""
import argparse
import hashlib
import io
import os
import json
import random
import shutil
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

DRIVE_FOLDER = "https://drive.google.com/drive/folders/1svFSy2Da3cVMvekBwe13mzyx38XZ9xWo"
CLASSES_URL = "https://raw.githubusercontent.com/xpwu95/IP102/master/classes.txt"
SEED = 42


def sh(cmd):
    print("+", cmd, flush=True)
    subprocess.run(cmd, shell=True, check=True)


def load_classes(cache: Path) -> list[str]:
    cache.mkdir(parents=True, exist_ok=True)
    p = cache / "classes.txt"
    if not p.exists():
        sh(f"wget -q -O {p} {CLASSES_URL}")
    names = []
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        idx, name = line.split(maxsplit=1)
        names.append(" ".join(name.split()))
    assert len(names) == 102, f"expected 102 classes, got {len(names)}"
    return names


def download(work: Path):
    import gdown  # noqa
    work.mkdir(parents=True, exist_ok=True)
    files = gdown.download_folder(DRIVE_FOLDER, output=str(work / "drive"), skip_download=True, quiet=True)
    det = [f for f in files if "Detection" in f.path or "detection" in f.path.lower()]
    print("Drive files:", [f.path for f in files])
    print("Detection files selected:", [f.path for f in det])
    if not det:
        sys.exit("No Detection files found in the Drive folder — inspect the listing above.")
    for f in det:
        dest = Path(f.local_path)
        if dest.exists() and dest.stat().st_size > 0:
            print("exists:", dest)
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        gdown.download(id=f.id, output=str(dest), quiet=False)
        if not dest.exists():
            sys.exit(f"Download failed for {f.path} (Drive quota?). Retry later.")
    for tar in (work / "drive").rglob("*.tar*"):
        marker = tar.with_suffix(".extracted")
        if marker.exists():
            continue
        print("extracting", tar)
        with tarfile.open(tar) as t:
            t.extractall(tar.parent / "extracted", filter="data")
        marker.touch()


def parse_voc(xml_path: Path):
    root = ET.parse(xml_path).getroot()
    fname = root.findtext("filename")
    size = root.find("size")
    w = int(float(size.findtext("width"))) if size is not None else 0
    h = int(float(size.findtext("height"))) if size is not None else 0
    objs = []
    for o in root.iter("object"):
        bb = o.find("bndbox")
        objs.append((o.findtext("name").strip(),
                     float(bb.findtext("xmin")), float(bb.findtext("ymin")),
                     float(bb.findtext("xmax")), float(bb.findtext("ymax"))))
    return fname, w, h, objs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/content/ip102")
    ap.add_argument("--out", default="/content/ip102_yolo")
    ap.add_argument("--skip-download", action="store_true",
                    help="use data already present under --work (e.g. a read-only Kaggle input)")
    ap.add_argument("--cache", default="", help="writable dir for classes.txt (default: --work)")
    a = ap.parse_args()
    work, out = Path(a.work), Path(a.out)
    names = load_classes(Path(a.cache) if a.cache else work)
    if not a.skip_download:
        download(work)

    from PIL import Image

    images, xmls, seen_real = {}, [], set()
    for root, _dirs, files in os.walk(work, followlinks=False):
        for fn in files:
            fp = Path(root) / fn
            real = os.path.realpath(fp)
            if real in seen_real:
                continue
            seen_real.add(real)
            if fn.lower().endswith(".jpg"):
                images.setdefault(fn, fp)
            elif fn.lower().endswith(".xml"):
                xmls.append(fp)
    print(f"found {len(images)} jpg, {len(xmls)} xml", flush=True)

    # Detect whether numeric labels are 0- or 1-based.
    raw_labels = Counter()
    parsed = []
    for k, x in enumerate(xmls):
        if k % 2000 == 0:
            print(f"  parsed {k}/{len(xmls)} xml", flush=True)
        try:
            parsed.append((x, *parse_voc(x)))
        except Exception as e:  # malformed XML
            print("bad xml", x, e)
    for _, _, _, _, objs in parsed:
        raw_labels.update(o[0] for o in objs)
    numeric = all(l.isdigit() for l in raw_labels)
    offset = 0
    if numeric:
        vals = sorted(int(l) for l in raw_labels)
        offset = 1 if vals[0] >= 1 and vals[-1] == 102 else 0
        print(f"numeric labels {vals[0]}..{vals[-1]} -> offset {offset}")
    name_to_idx = {n.lower(): i for i, n in enumerate(names)}

    stats = Counter()
    records = {}  # stem -> (img_path, w, h, [(cls, cx, cy, bw, bh)])
    hashes = {}
    n_done = 0
    for x, fname, w, h, objs in parsed:
        stem = Path(fname or x.stem).stem
        img = images.get(f"{stem}.jpg") or images.get(fname or "")
        if img is None:
            stats["missing_image"] += 1
            continue
        if n_done % 2000 == 0:
            print(f"  validated {n_done}/{len(parsed)} annotations", flush=True)
        n_done += 1
        try:
            raw = img.read_bytes()
            with Image.open(io.BytesIO(raw)) as im:
                im.verify()
            with Image.open(io.BytesIO(raw)) as im:
                w, h = im.size
        except Exception:
            stats["corrupt_image"] += 1
            continue
        digest = hashlib.sha1(raw).hexdigest()
        if digest in hashes:
            stats["duplicate_image"] += 1
            continue
        hashes[digest] = stem
        boxes = []
        for lab, x1, y1, x2, y2 in objs:
            if numeric:
                ci = int(lab) - offset
            else:
                ci = name_to_idx.get(lab.lower(), -1)
            if not 0 <= ci < len(names):
                stats["invalid_label"] += 1
                continue
            x1, x2 = max(0, min(x1, x2)), min(w, max(x1, x2))
            y1, y2 = max(0, min(y1, y2)), min(h, max(y1, y2))
            if x2 - x1 < 2 or y2 - y1 < 2:
                stats["degenerate_box"] += 1
                continue
            boxes.append((ci, (x1 + x2) / 2 / w, (y1 + y2) / 2 / h, (x2 - x1) / w, (y2 - y1) / h))
        if not boxes:
            stats["no_valid_boxes"] += 1
            continue
        records[stem] = (raw, w, h, boxes)
    print("cleaning stats:", dict(stats), "kept:", len(records))

    # Official split lists if present
    def read_list(name):
        for root, _d, files in os.walk(work, followlinks=False):
            if name in files:
                p = Path(root) / name
                return {l.strip() for l in p.read_text().split() if l.strip()}
        return None

    trainval, test = read_list("trainval.txt"), read_list("test.txt")
    if test and not trainval:  # some mirrors ship only test.txt (+ train.txt/val.txt)
        trainval = set(records) - test
    rnd = random.Random(SEED)
    split = {}
    if trainval and test:
        tv = sorted(s for s in records if s in trainval)
        rnd.shuffle(tv)
        n_val = max(1, int(0.1 * len(tv)))
        for s in tv[:n_val]:
            split[s] = "val"
        for s in tv[n_val:]:
            split[s] = "train"
        for s in records:
            if s in test:
                split[s] = "test"
        split_method = "official IP102 trainval/test lists; val = 10% of trainval (seed 42)"
    else:
        by_cls = defaultdict(list)
        for s, (_, _, _, boxes) in records.items():
            by_cls[boxes[0][0]].append(s)
        for cls, stems in by_cls.items():
            stems.sort(); rnd.shuffle(stems)
            n = len(stems); nt = int(0.8 * n); nv = int(0.1 * n)
            for i, s in enumerate(stems):
                split[s] = "train" if i < nt else ("val" if i < nt + nv else "test")
        split_method = "stratified 80/10/10 by first-box class (seed 42)"

    if out.exists():
        shutil.rmtree(out)
    per_split_imgs = Counter()
    per_class = {k: Counter() for k in ("train", "val", "test")}
    for s, (img, w, h, boxes) in records.items():
        sp = split.get(s)
        if sp is None:
            continue
        (out / "images" / sp).mkdir(parents=True, exist_ok=True)
        (out / "labels" / sp).mkdir(parents=True, exist_ok=True)
        (out / "images" / sp / f"{s}.jpg").write_bytes(img)
        (out / "labels" / sp / f"{s}.txt").write_text(
            "\n".join(f"{c} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}" for c, cx, cy, bw, bh in boxes))
        per_split_imgs[sp] += 1
        per_class[sp].update(b[0] for b in boxes)

    yaml_names = "\n".join(f"  {i}: \"{n}\"" for i, n in enumerate(names))
    (out / "data.yaml").write_text(
        f"path: {out}\ntrain: images/train\nval: images/val\ntest: images/test\nnc: {len(names)}\nnames:\n{yaml_names}\n")
    result = {
        "dataset": "IP102 detection subset (v1.1)",
        "source": DRIVE_FOLDER,
        "homepage": "https://github.com/xpwu95/IP102",
        "citation": "Wu et al., IP102: A Large-Scale Benchmark Dataset for Insect Pest Recognition, CVPR 2019",
        "licence": "No explicit licence published by the authors; research use with citation.",
        "classes": names,
        "split_method": split_method,
        "cleaning": dict(stats),
        "images_found": len(images), "annotations_found": len(xmls),
        "images_per_split": dict(per_split_imgs),
        "boxes_per_class": {sp: {names[c]: n for c, n in sorted(cnt.items())} for sp, cnt in per_class.items()},
    }
    (out / "dataset_stats.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k != "boxes_per_class"}, indent=2))


if __name__ == "__main__":
    main()
