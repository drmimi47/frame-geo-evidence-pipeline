"""Section block pass 2: the block's last frame against the section's first (both before any type), and their
difference; the numbers and a figure.
python matchcheck.py BLOCK_LAST.png LINE GF_DIR XF_DIR OUT.png"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
import gfilm2 as G  # noqa: E402

blk, line, gf, xf, out = sys.argv[1:6]
sec = G.Section(line, "ease", gf, xf)
a = np.asarray(Image.open(blk).convert("RGB"), float); b = sec.start
d = np.abs(a - b).max(2)
stats = f"mean {d.mean():.3f} of 255, max {d.max():.0f}, {(d > 20).sum()} px over 20 (the pieces' edge columns)"
print(stats)
box, zoom = (40, 520, 1900, 620), (700, 540, 1100, 600)
dd = np.repeat(np.clip(d * 8, 0, 255)[..., None], 3, 2)
rows = [Image.fromarray(x.astype(np.uint8)).crop(box) for x in (a, b, dd)]
z = [Image.fromarray(x.astype(np.uint8)).crop(zoom).resize((1600, 240), Image.NEAREST) for x in (a, b, dd)]
labels = ["THE BLOCK'S LAST FRAME (BLENDER, 3D)", "THE SECTION'S FIRST FRAME (PROFILE3.PY, 2D, LAID OUT AS GFILM.PY)",
          "DIFFERENCE x8"]
img = Image.new("RGB", (box[2] - box[0], 3 * 130 + 3 * 270 + 60), (20, 20, 20)); dr = ImageDraw.Draw(img); y = 10
for r, l in zip(rows, labels):
    dr.text((10, y), l, fill=(255, 220, 0), font=G.F_TINY); img.paste(r, (0, y + 18)); y += 130
for r, l in zip(z, labels):
    dr.text((10, y), l + ", ENLARGED x4 (COLUMNS 700-1100)", fill=(255, 220, 0), font=G.F_TINY); img.paste(r, (0, y + 18)); y += 270
dr.text((10, y + 10), "MATCH: " + stats, fill=(255, 255, 255), font=G.F_SMALL)
img.save(out)
