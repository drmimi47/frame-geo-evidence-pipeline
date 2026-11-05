"""Score the main library's stored frame embeddings (read-only) with the scan's tower captions.

    python -I score_library.py LIBRARY OUT_DIR

The main library's videos already passed the scope gate and carry SigLIP embeddings of up to 100 frames each;
nothing is written to the library. Writes OUT_DIR/<id>.npz like scan.py, plus the web image of each frame.
"""
import json, os, sys
from pathlib import Path
import numpy as np
import torch
from transformers import AutoModel, AutoProcessor  # noqa: F401
from scan import GROUPS
from image_evidence.classify import SiglipClassifier
from image_evidence.config import ClassificationConfig

lib, out = Path(sys.argv[1]), Path(sys.argv[2])
torch.backends.mps.is_available = lambda: False
clf = SiglipClassifier(ClassificationConfig())
for v in sorted((lib / "videos").iterdir()):
    npz = v / "frames" / "embeddings.npz"
    if not npz.exists():
        continue
    d = np.load(npz)
    times, files = [], []
    for fid in d["ids"]:
        m = json.loads((v / "frames" / "meta" / f"{fid}.json").read_text())
        times.append(m["frame"]["timestamp_s"]); files.append(str(lib / m["frame"]["files"]["web"]))
    emb = d["vecs"].astype(np.float32)
    shares = clf.zero_shot(emb, GROUPS)
    scores = np.array([[s[k] for k in GROUPS] for s in shares], np.float32)
    np.savez_compressed(out / f"{v.name}.npz", times=np.array(times, np.float32), emb=emb.astype(np.float16),
                        scores=scores, groups=np.array(list(GROUPS)), step=0.0, files=np.array(files))
    print(v.name, len(times), f"best {scores[:, 0].max():.2f}", flush=True)
