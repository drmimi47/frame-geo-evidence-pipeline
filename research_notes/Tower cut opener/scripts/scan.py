"""Scan the gated downloads for frames showing a power-line tower (SigLIP zero-shot).

Run with `python -I` (the downloads are untrusted). For each finished download (DOWNLOADS/<id>/, see
gate_download.py), FFmpeg samples a small preview every `step` seconds into the scratch
directory; SigLIP (the pipeline's model) embeds them and scores each against tower / pole / unwanted captions.
Writes <out>/<id>.npz (times, embeddings, scores) and skips videos already scanned. Scores are search aids only.

    python -I scan.py DOWNLOADS SCRATCH OUT [ids... | watch=PID]
"""
from __future__ import annotations

import json
import os
import time
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from image_evidence.classify import SiglipClassifier
from image_evidence.config import ClassificationConfig

# The pipeline's so400m model by default; SCAN_MODEL=google/siglip-base-patch16-224 is ~10x faster on CPU (a
# prefilter only: every candidate is looked at by eye).
MODEL = os.environ.get("SCAN_MODEL", "google/siglip-so400m-patch14-384")

GROUPS = {
    "tower": ["a high-voltage electricity transmission tower", "a large steel lattice pylon carrying power lines",
              "a tall power line tower standing over water", "electricity pylons in a field",
              "a power transmission tower seen from below"],
    "pole": ["a wooden utility pole with wires", "a concrete electricity pole with wires along a village road",
             "a distribution power line on poles"],
    "people": ["a person talking to the camera", "a group of people", "a close-up of a person's face"],
    "interior": ["an indoor room", "the inside of a car"],
    "graphic": ["a map", "text on a screen", "a logo"],
    "damage": ["a destroyed building", "smoke and fire", "a fallen power line tower", "military vehicles"],
    "other": ["a landscape without power lines", "a river", "a forest", "a city street", "a video frame"],
}


def duration(mp4: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(mp4)],
                         capture_output=True, text=True, check=True).stdout
    return float(json.loads(out)["format"]["duration"])


def main() -> None:
    lib, scratch, out = (Path(a) for a in sys.argv[1:4])
    watch = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4].startswith("watch=") else None
    ids = [] if watch else sys.argv[4:]
    out.mkdir(parents=True, exist_ok=True)
    clf = None
    while True:
        clf = scan(lib, scratch, out, ids or sorted(p.name for p in lib.iterdir() if p.is_dir()), clf)
        pid = int(watch.split("=")[1]) if watch else None
        if pid is None:
            return
        try:
            os.kill(pid, 0)
        except OSError:  # the ingest has finished: one last pass
            scan(lib, scratch, out, sorted(p.name for p in lib.iterdir() if p.is_dir()), clf)
            return
        time.sleep(30)


def scan(lib: Path, scratch: Path, out: Path, ids: list[str], clf):
    skip = set(os.environ.get("SCAN_SKIP", "").split())  # videos already embedded elsewhere (the main library's)
    for yid in ids:
        if yid in skip:
            continue
        done = lib / yid / "done"
        if not done.exists():
            continue  # still downloading
        mp4 = lib / yid / done.read_text().strip()
        dst = out / f"{yid}.npz"
        if dst.exists() or not mp4.exists():
            continue
        dur = duration(mp4)
        step = 3.0 if dur <= 900 else 6.0
        tmp = scratch / yid
        tmp.mkdir(parents=True, exist_ok=True)
        for f in tmp.glob("*.jpg"):
            f.unlink()
        subprocess.run(["ffmpeg", "-v", "error", "-i", str(mp4), "-vf", f"fps=1/{step},scale=384:-2", "-q:v", "5",
                        str(tmp / "%06d.jpg")], check=True)
        files = sorted(tmp.glob("*.jpg"))
        times = np.array([(int(f.stem) - 1) * step for f in files], np.float32)
        if clf is None:
            if os.environ.get("SCAN_CPU"):  # the GPU is shared with Blender renders; CPU is steadier then
                import torch
                from transformers import AutoModel, AutoProcessor  # noqa: F401 (import before the patch below)
                torch.backends.mps.is_available = lambda: False
                torch.set_num_threads(int(os.environ["SCAN_CPU"]))
            clf = SiglipClassifier(ClassificationConfig(model=MODEL))
        emb = []
        for i in range(0, len(files), 64):
            emb.append(clf.embed([Image.open(f) for f in files[i:i + 64]]))
        emb = np.concatenate(emb) if emb else np.zeros((0, 1152), np.float32)
        shares = clf.zero_shot(emb, GROUPS)
        scores = np.array([[s[k] for k in GROUPS] for s in shares], np.float32)
        np.savez_compressed(dst, times=times, emb=emb.astype(np.float16), scores=scores, groups=np.array(list(GROUPS)),
                            step=step, model=MODEL)
        print(f"{yid}: {len(files)} previews, best tower {scores[:, 0].max() if len(scores) else 0:.2f}, "
              f"{int((scores[:, 0] + scores[:, 1] > 0.5).sum())} over 0.5", flush=True)
    return clf


if __name__ == "__main__":
    main()
