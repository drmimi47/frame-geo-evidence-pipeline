"""A storyboard clip: someone else's recording of a line of the same class, shown as recorded (NEXT.md S4, Earshot's
Zifzafa idea 1, 5 November 2026).

    python -I proxy_clip.py <video.mp4> <start_s> <seconds> <scale> <out.mp4> <title> <note> <credit>   (from the root)

The footage only cut, scaled (lanczos) and placed smaller than the frame on black, the way Forensic Architecture shows
a supplied video; its sound as recorded (a half-second fade at each end, nothing else). Under it three lines: what it
is, that it is a proxy recorded elsewhere, and whose it is. Text drawn with PIL (this FFmpeg has no drawtext).
"""

import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT = "/System/Library/Fonts/HelveticaNeue.ttc"
W, H = 1920, 1080


def main(src, start, secs, scale, out, title, note, credit):
    start, secs, scale = float(start), float(secs), float(scale)
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                            "-of", "csv=p=0", src], capture_output=True, text=True, check=True).stdout.split(",")
    w, h = (int(round(int(v) * scale / 2) * 2) for v in probe)
    x0, y0 = (W - w) // 2, 90
    over = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    f = lambda s: ImageFont.truetype(FONT, s, index=0)
    y = y0 + h + 34
    for s, z, c in ((title.upper(), 24, (255, 255, 255, 255)), (note.upper(), 16, (225, 225, 225, 255)),
                    (credit, 15, (190, 190, 190, 255))):
        d.text((x0, y), s, font=f(z), fill=c)
        y += z + 14
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "text.png"
        over.save(png)
        fo = max(0.0, secs - 0.5)
        subprocess.run([
            "ffmpeg", "-v", "error", "-y", "-ss", str(start), "-t", str(secs), "-i", src, "-loop", "1", "-i", str(png),
            "-filter_complex",
            f"[0:v]scale={w}:{h}:flags=lanczos,pad={W}:{H}:{x0}:{y0}:black,fps=30,setsar=1[v];"
            f"[v][1:v]overlay=0:0:shortest=1,format=yuv420p[o];"
            f"[0:a]afade=t=in:d=0.5,afade=t=out:st={fo}:d=0.5[a]",
            "-map", "[o]", "-map", "[a]", "-t", str(secs), "-c:v", "libx264", "-crf", "18", "-preset", "medium",
            "-c:a", "aac", "-b:a", "192k", out], check=True)


if __name__ == "__main__":
    main(*sys.argv[1:9])
