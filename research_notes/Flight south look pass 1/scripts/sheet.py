"""contact sheet: reference on top, then per time: old | new (graded)."""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw
from image_evidence.satellite.scene3d.animatic import grade_image
S = Path(sys.argv[1]); new = S / sys.argv[2]; outp = Path(sys.argv[3])
B = Path("libraries/conductive-seam/satellite/networks/znpp/scenes/crossing3d")
old = B / "animatic/south_record"
look = json.loads((B / "camera_south_look1.json").read_text())["look"]
fr = [int(x) for x in sys.argv[4].split(",")] if len(sys.argv) > 4 else [361, 601, 841, 1201, 2251, 3601]
W, H = 960, 540
ref = Image.open(S.parent.parent / "images/18.png").convert("RGB").resize((W, round(W * 941 / 1672)))
rows = len(fr)
sheet = Image.new("RGB", (2 * W, ref.height + rows * H), (0, 0, 0))
sheet.paste(ref, (0, 0))
d = ImageDraw.Draw(sheet)
d.text((W + 10, 10), "top left: the user's reference (look only)\nleft column: south_record (old)\nright: south_look1 still", fill=(255, 255, 255))
for k, f in enumerate(fr):
    y = ref.height + k * H
    sheet.paste(Image.open(old / f"f_{f:04d}.png").convert("RGB"), (0, y))
    p = new / f"f_{f:04d}.png"
    if p.exists():
        sheet.paste(grade_image(Image.open(p), look.get("grade", {}), f), (W, y))
    d.text((10, y + 520), f"{(f-1)/30:.1f} s", fill=(255, 255, 0))
sheet.save(outp)
