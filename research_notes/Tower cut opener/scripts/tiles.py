"""Tile sheets of a download for looking at by eye: one tile every STEP s from START, its time written on it.

    python -I tiles.py DOWNLOADS ID STEP OUT_PREFIX [START END]
"""
import subprocess, sys, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

dl, yid, step, out = Path(sys.argv[1]), sys.argv[2], float(sys.argv[3]), sys.argv[4]
start = float(sys.argv[5]) if len(sys.argv) > 5 else 0.0
end = float(sys.argv[6]) if len(sys.argv) > 6 else None
mp4 = dl / yid / (dl / yid / "done").read_text().strip()
with tempfile.TemporaryDirectory() as tmp:
    cmd = ["ffmpeg", "-v", "error", "-ss", str(start)] + (["-to", str(end)] if end else []) + [
        "-i", str(mp4), "-vf", f"fps=1/{step},scale=240:-2", "-q:v", "4", f"{tmp}/%05d.jpg"]
    subprocess.run(cmd, check=True)
    files = sorted(Path(tmp).glob("*.jpg"))
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 15)
    cols, rows = 8, 10
    for p in range(0, len(files), cols * rows):
        ims = [Image.open(f).convert("RGB") for f in files[p:p + cols * rows]]
        tw, th = ims[0].size
        sheet = Image.new("RGB", (cols * tw, rows * th), "black")
        dr = ImageDraw.Draw(sheet)
        for k, im in enumerate(ims):
            x, y = (k % cols) * tw, (k // cols) * th
            sheet.paste(im, (x, y))
            t = start + (p + k) * step
            dr.rectangle([x, y, x + 52, y + 18], fill="black")
            dr.text((x + 3, y + 1), f"{t:.0f}", fill="yellow", font=font)
        sheet.save(f"{out}-{p // (cols * rows):02d}.jpg", quality=85)
print(len(files), "tiles")
