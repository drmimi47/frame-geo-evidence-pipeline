"""Review sheets of the scan's best tower candidates (for looking at, not evidence).

    python -I review_sheet.py SCAN_DIR PREVIEW_DIR OUT_PREFIX [per_video] [min_score]

Per video: previews whose tower+pole share is high and people/graphic/damage share low, at least 4 s apart and
not near-duplicates (SigLIP embedding cosine < 0.93). Pages of 6x5 tiles, each labelled "<id> <seconds>".
Writes OUT_PREFIX-<page>.jpg and OUT_PREFIX.json (the tiles in order).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

COLS, ROWS, TW, TH = 6, 5, 320, 200


def main() -> None:
    scan, prev, out = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    per_video = int(sys.argv[4]) if len(sys.argv) > 4 else 12
    min_score = float(sys.argv[5]) if len(sys.argv) > 5 else 0.45
    tiles = []
    only = set(sys.argv[6].split(",")) if len(sys.argv) > 6 else None
    for npz in sorted(scan.glob("*.npz")):
        if only and npz.stem not in only:
            continue
        d = np.load(npz)
        groups = list(d["groups"])
        sc, t, emb, step = d["scores"], d["times"], d["emb"].astype(np.float32), float(d["step"])
        g = {k: sc[:, i] for i, k in enumerate(groups)}
        good = g["tower"] + g["pole"] - g["people"] - g["graphic"] - g["damage"] - g["interior"]
        order = np.argsort(-good)
        kept = []
        for i in order:
            if good[i] < min_score or len(kept) >= per_video:
                break
            if any(abs(t[i] - t[j]) < 4 for j in kept) or any(float(emb[i] @ emb[j]) > 0.93 for j in kept):
                continue
            kept.append(i)
        for i in sorted(kept, key=lambda i: t[i]):
            f = d["files"][i] if "files" in d.files else prev / npz.stem / f"{int(round(t[i] / step)) + 1:06d}.jpg"
            tiles.append({"id": npz.stem, "t": float(t[i]), "score": round(float(good[i]), 2), "file": str(f),
                          "tower": round(float(g["tower"][i]), 2), "pole": round(float(g["pole"][i]), 2)})
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 15)
    n = COLS * ROWS
    for p in range(0, len(tiles), n):
        sheet = Image.new("RGB", (COLS * TW, ROWS * TH), "black")
        dr = ImageDraw.Draw(sheet)
        for k, tile in enumerate(tiles[p:p + n]):
            im = Image.open(tile["file"]).convert("RGB")
            im.thumbnail((TW - 4, TH - 22))
            x, y = (k % COLS) * TW, (k // COLS) * TH
            sheet.paste(im, (x + 2, y + 2))
            tile["page"], tile["slot"] = p // n, k
            dr.text((x + 4, y + TH - 19), f"{p + k}: {tile['id']} {tile['t']:.0f}s  t{tile['tower']:.2f} p{tile['pole']:.2f}",
                    fill="yellow", font=font)
        sheet.save(f"{out}-{p // n:02d}.jpg", quality=85)
    Path(out + ".json").write_text(json.dumps(tiles, indent=1))
    print(len(tiles), "tiles,", (len(tiles) + n - 1) // n, "pages")


if __name__ == "__main__":
    main()
