"""Look-dev sheet: per time, south_look1 as rendered (left, graded) | the south_look2 still (right, graded the same).
python sheet.py <stills dir> <out.jpg> [frames] [crop]   (run from the repo root; crop "x,y,w,h" adds a 2x crop row)"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from image_evidence.satellite.scene3d.animatic import grade_image

new, outp = Path(sys.argv[1]), Path(sys.argv[2])
B = Path("libraries/conductive-seam/satellite/networks/znpp/scenes/crossing3d")
old = B / "animatic/south_look1"
look = json.loads((B / "camera_south_look2.json").read_text())["look"]
fr = [int(x) for x in sys.argv[3].split(",")] if len(sys.argv) > 3 else [361, 601, 841, 1201, 1291, 2251, 3601]
W, H = 960, 540
sheet = Image.new("RGB", (2 * W, len(fr) * H), (0, 0, 0))
d = ImageDraw.Draw(sheet)
for k, f in enumerate(fr):
    y = k * H
    p0 = old / "raw" / f"f_{f:04d}.png"
    if p0.exists():
        sheet.paste(grade_image(Image.open(p0), look.get("grade", {}), f), (0, y))
    elif (old / f"f_{f:04d}.png").exists():
        sheet.paste(Image.open(old / f"f_{f:04d}.png").convert("RGB"), (0, y))
    p = new / f"f_{f:04d}.png"
    if p.exists():
        sheet.paste(grade_image(Image.open(p), look.get("grade", {}), f), (W, y))
    d.text((10, y + 10), f"look1  {(f - 1) / 30:.1f} s  (frame {f})", fill=(255, 255, 0))
    d.text((W + 10, y + 10), "look2", fill=(255, 255, 0))
sheet.save(outp, quality=88)
