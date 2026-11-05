"""Helpers for marking a tower's top and base by eye (alignment only, not evidence). Run with `python -I`.

    mark_tool.py extract MP4 SECONDS OUT.png          one frame at full resolution (FFmpeg, accurate seek)
    mark_tool.py grid IN.png OUT.jpg [X Y W H [STEP]]  a crop (default: whole frame) with a labelled pixel grid,
                                                      scaled to about 1600 px wide so coordinates can be read
    mark_tool.py check IN.png OUT.jpg TX TY BX BY     the marks drawn on a scratch copy (top red, base cyan)
"""
from __future__ import annotations

import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

FONT = "/System/Library/Fonts/Helvetica.ttc"


def extract(mp4: str, t: float, out: str) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", mp4, "-frames:v", "1", out], check=True)


def grid(src: str, out: str, x: int = 0, y: int = 0, w: int | None = None, h: int | None = None, step: int | None = None) -> None:
    im = Image.open(src).convert("RGB")
    w = w or im.width - x
    h = h or im.height - y
    crop = im.crop((x, y, x + w, y + h))
    s = 1600 / w
    crop = crop.resize((round(w * s), round(h * s)), Image.LANCZOS)
    step = step or (100 if w > 800 else 50 if w > 300 else 20)
    dr = ImageDraw.Draw(crop)
    font = ImageFont.truetype(FONT, 18)
    for gx in range((x // step + 1) * step, x + w, step):
        px = (gx - x) * s
        dr.line([(px, 0), (px, crop.height)], fill=(255, 255, 0) if gx % (step * 5) == 0 else (255, 120, 0), width=1)
        dr.text((px + 2, 2), str(gx), fill="yellow", font=font)
    for gy in range((y // step + 1) * step, y + h, step):
        py = (gy - y) * s
        dr.line([(0, py), (crop.width, py)], fill=(255, 255, 0) if gy % (step * 5) == 0 else (255, 120, 0), width=1)
        dr.text((2, py + 2), str(gy), fill="yellow", font=font)
    crop.save(out, quality=88)


def check(src: str, out: str, tx: float, ty: float, bx: float, by: float) -> None:
    im = Image.open(src).convert("RGB")
    dr = ImageDraw.Draw(im)
    dr.line([(tx, ty), (bx, by)], fill=(255, 0, 255), width=2)
    for (x, y), c in (((tx, ty), (255, 0, 0)), ((bx, by), (0, 255, 255))):
        dr.ellipse([x - 9, y - 9, x + 9, y + 9], outline=c, width=3)
    im.thumbnail((1600, 1600))
    im.save(out, quality=88)


if __name__ == "__main__":
    cmd, *a = sys.argv[1:]
    if cmd == "extract":
        extract(a[0], float(a[1]), a[2])
    elif cmd == "grid":
        grid(a[0], a[1], *map(int, a[2:]))
    elif cmd == "check":
        check(a[0], a[1], *map(float, a[2:6]))
