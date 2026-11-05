"""Contact sheet of the candidates, grouped by line class (an estimate by eye; see marks.json class_how).

    python -I candidates_sheet.py BASE_DIR

Every frame in marks.json, used or left out (left out struck through in red; the reason is in marks.json), one group
per class, smallest first. Writes candidates.jpg. Frames come from downloads/<id>/ as render.py.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ORDER = ["distribution", "35", "35-110", "330", "750", "crossing"]
NAMES = {"distribution": "DISTRIBUTION 0.4-10 kV", "35": "35 kV", "35-110": "35-110 kV LATTICE", "330": "330 kV",
         "750": "750 kV",
         "crossing": "THE CROSSING (found footage and supplied photographs)"}
TW, TH, COLS = 320, 180, 6


def frame(base: Path, f: dict) -> Path:
    if f.get("file"):
        return base / f["file"]
    out = base / "frames" / f"{f['key']}.png"
    if not out.exists():
        dl = base / "downloads" / f["video"]
        mp4 = dl / (dl / "done").read_text().strip()
        out.parent.mkdir(exist_ok=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{f['t']:.3f}", "-i", str(mp4), "-frames:v", "1", str(out)], check=True)
    return out


def main() -> None:
    base = Path(sys.argv[1])
    frames = json.loads((base / "marks.json").read_text())["frames"]
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 13)
    head = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
    blocks = []
    for c in ORDER:
        fs = [f for f in frames if f["size_class"] == c]
        rows = (len(fs) + COLS - 1) // COLS
        img = Image.new("RGB", (COLS * TW, 34 + rows * (TH + 20)), "black")
        d = ImageDraw.Draw(img)
        d.text((6, 6), f"{NAMES[c]}  ({sum(1 for f in fs if not f.get('left_out'))} used, {sum(1 for f in fs if f.get('left_out'))} left out)",
               fill="white", font=head)
        for i, f in enumerate(fs):
            im = Image.open(frame(base, f)).convert("RGB")
            im.thumbnail((TW - 4, TH - 4))
            x, y = (i % COLS) * TW, 34 + (i // COLS) * (TH + 20)
            img.paste(im, (x + 2, y + 2))
            if f.get("left_out"):
                d.line([(x + 2, y + TH - 2), (x + TW - 2, y + 2)], fill=(220, 40, 40), width=3)
            d.text((x + 4, y + TH + 2), (f"{f['key']}  {f['file']}" if f.get("file") else f"{f['key']}  {f['video']} {f['t']}s") + ("  LEFT OUT" if f.get("left_out") else ""),
                   fill=(255, 120, 120) if f.get("left_out") else "yellow", font=font)
        blocks.append(img)
    sheet = Image.new("RGB", (COLS * TW, sum(b.height for b in blocks)), "black")
    y = 0
    for b in blocks:
        sheet.paste(b, (0, y))
        y += b.height
    sheet.save(base / "candidates.jpg", quality=86)
    print(sheet.size)


if __name__ == "__main__":
    main()
