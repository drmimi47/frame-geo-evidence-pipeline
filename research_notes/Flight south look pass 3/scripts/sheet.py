"""Look-dev sheet: per still, south_look2 as rendered at the same place (left: the frame whose camera is nearest the
same distance along the track, graded) | the south_look3 still (right, graded).
python sheet.py <stills dir> <camera json of the stills> <out.jpg> [frames] [--crop x,y,w,h]   (run from the repo root)"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from image_evidence.satellite.scene3d.animatic import grade_image
from image_evidence.satellite.scene3d.states import date_label

args = [a for a in sys.argv[1:] if not a.startswith("--")]
crop = next((tuple(int(v) for v in a.split("=", 1)[1].split(",")) for a in sys.argv[1:] if a.startswith("--crop=")), None)
new, camp, outp = Path(args[0]), Path(args[1]), Path(args[2])
B = Path("libraries/conductive-seam/satellite/networks/znpp/scenes/crossing3d")
old = B / "animatic/south_look2"
l2 = json.loads((B / "camera_south_look2.json").read_text())
l3 = json.loads(camp.read_text())
fr = [int(x) for x in args[3].split(",")] if len(args) > 3 else sorted(int(p.stem[2:]) for p in new.glob("f_*.png"))
a2 = np.array([f["along_m"] for f in l2["frames"]])
W, H = 960, 540
cw, ch = (crop[2] * 2, crop[3] * 2) if crop else (W, H)
sheet = Image.new("RGB", (2 * cw, len(fr) * ch), (0, 0, 0))
d = ImageDraw.Draw(sheet)
for k, f in enumerate(fr):
    y = k * ch
    g3 = l3["frames"][f - 1]
    j = int(np.argmin(np.abs(a2 - g3["along_m"]))) + 1
    if f / 30 > 74 and g3["phase"] == "rise":   # look 2 curves away there: the same time into its rise instead
        j = min(len(a2), f + 2617 - 2230)
    p0 = old / "raw" / f"f_{j:04d}.png"
    p = new / f"f_{f:04d}.png"
    for x0, path, cam, look in ((0, p0, l2, l2["look"]), (cw, p, l3, l3["look"])):
        if not path.exists():
            continue
        im = grade_image(Image.open(path), look.get("grade", {}), f)
        if crop:
            im = im.crop((crop[0], crop[1], crop[0] + crop[2], crop[1] + crop[3])).resize((cw, ch), Image.LANCZOS)
        sheet.paste(im, (x0, y))
    d.text((10, y + 8), f"look2 frame {j} ({(j - 1) / 30:.1f} s), {date_label(l2['frames'][j - 1].get('date'))}", fill=(255, 255, 0))
    d.text((cw + 10, y + 8), f"look3 {(f - 1) / 30:.1f} s (frame {f}), {date_label(g3.get('date'))}, along {g3['along_m']:.0f} m",
           fill=(255, 255, 0))
sheet.save(outp, quality=88)
print(outp)
