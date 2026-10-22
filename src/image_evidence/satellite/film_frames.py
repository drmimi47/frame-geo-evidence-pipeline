"""A film's frames for the folder's gallery: the frames the film shows, as the Frame Gallery holds a video's.

Not every frame (a 5 minute film has 7,800): as for a video (`pipeline._extract`, `view_overlap`), a frame is kept once
its view shares less than half of its ground with the last kept frame, so a track gives a frame per new stretch of
line and a zoom one per step. A held shot gives nothing new that way, so its moments are kept by name: the plant's
lines drawn, the pan's end, before and after a dissolve, an inset at full strength, the last hold. Frames in a fade
(from or to black), mid-dissolve or with an inset still fading in are never kept by overlap.

Each frame is saved as the gallery's images are, WebP web (1600 px) and thumbnail (400 px), with its sha256 of the
frame's RGB pixels, and recorded in `frames/frames.json` with the film's own account of it: shot, passes and weights,
the camera (a viewing path, not where anything was observed from), and what is drawn on it.
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image

from ..layout import write_json

WEB_PX, THUMB_PX = 1600, 400
OVERLAP = 0.5
SELECTION = ("A frame is kept once its view shares less than half its ground with the last frame kept (as a video's "
             "frames are), plus the held moments a moving view can't give: the plant's lines drawn, the pan's end, "
             "before and after a dissolve, an inset at full strength, the last hold before the fade.")


def footprint(M: np.ndarray, w: int, h: int) -> np.ndarray:
    """The frame's corners on the corridor grid (pixels), in order round it."""
    c = np.array([[0, 0, 1], [w, 0, 1], [w, h, 1], [0, h, 1]], float)
    return (c @ M.T).astype(np.float32)


def overlap(a: np.ndarray, b: np.ndarray) -> float:
    """The ground two views share, as a share of the larger (so a zoom in or out counts as a new view)."""
    inter, _ = cv2.intersectConvexConvex(a, b)
    return float(inter) / max(cv2.contourArea(a), cv2.contourArea(b), 1e-9)


class FramePicker:
    def __init__(self, root: Path, out: Path, corridor_id: str, film_id: str, w: int, h: int):
        self.root, self.dir, self.w, self.h = Path(root), out / "frames", w, h
        self.prefix = f"sat_film_{corridor_id}_{film_id}"
        self.last: np.ndarray | None = None
        self.frames: list[dict[str, Any]] = []

    def offer(self, frame: np.ndarray, M: np.ndarray, record: dict[str, Any], key: str | None, eligible: bool) -> None:
        fp = footprint(M, self.w, self.h)
        if key:
            why = key
        elif not eligible:
            return
        elif self.last is None:
            why = "the first clear frame"
        else:
            share = overlap(fp, self.last)
            if share >= OVERLAP:
                return
            why = f"a new view: {math.floor(share * 100)}% of its ground in the last frame kept"
        self.last = fp
        n = len(self.frames) + 1
        fid = f"{self.prefix}_f{n:03d}"
        files = {}
        for kind, px in (("web", WEB_PX), ("thumb", THUMB_PX)):
            p = self.dir / kind / f"{fid}.webp"
            p.parent.mkdir(parents=True, exist_ok=True)
            size = (px, round(px * self.h / self.w)) if self.w >= px else (self.w, self.h)
            Image.fromarray(cv2.resize(frame, size, interpolation=cv2.INTER_AREA)).save(p, "WEBP", quality=88 if kind == "web" else 80)
            files[kind] = p.relative_to(self.root).as_posix()
        web = (WEB_PX, round(WEB_PX * self.h / self.w)) if self.w >= WEB_PX else (self.w, self.h)
        self.frames.append({"frame_id": fid, "n": n, **record, "kept": why, "files": files, "width": web[0], "height": web[1],
                            "film_size": [self.w, self.h], "sha256": hashlib.sha256(np.ascontiguousarray(frame).tobytes()).hexdigest(),
                            "sha256_of": "the film frame's RGB pixels, before encoding"})

    def write(self, film_id: str, corridor_id: str) -> dict[str, Any]:
        doc = {"schema": "film-frames/1", "film_id": film_id, "corridor_id": corridor_id, "selection": SELECTION,
               "frames": self.frames}
        write_json(self.dir / "frames.json", doc)
        return doc
