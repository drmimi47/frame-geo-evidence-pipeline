"""Lay the v5 renders together (composite_v4.py's passes and maths, run here without changing it), from the project
root with the project's venv:

    python -I composite_v5.py still <render.exr> <out.png>                      a full render over the day sky
    python -I composite_v5.py frame <render_dir> <K> <out.png>                   frame K of the 30 s shot
    python -I composite_v5.py video <render_dir> <audio.wav> <out.mp4>          the 30 s shot, with the soundscape
    python -I composite_v5.py compare <full.exr> <render_dir> <K> [diff.png]    the composite against a full render
    python -I composite_v5.py reprise <render_dir> <audio.wav> <out.mp4> <A> [stills_prefix]   the waterline reprise

The sky: the film's day world, one flat colour (linear 0.62, 0.66, 0.70: the scene's world background, as v3's
f_day.png was rendered with it), so the plate is the static render over that colour; the rest is composite_v4's.

The reprise (REPRISE_S long, frames A.. of the 30 s shot's moving pass): plain for LINE_AT s, then the proposed level's
line (still_v5.py contour: its matte, the band's red channel) faded in over LINE_FADE s and held. The line is laid on
the static plate (so the lit wires and their glow still pass in front of it where they are nearer) in a saturated blue,
opaque, over a 1 px darker edge (the matte grown); with it the label, a short stroke of the line's blue before it, small, bottom left, in the film's style (white capitals, Helvetica Neue, black box at half
opacity).
"""
import json
import os
import subprocess
import sys
import time

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import composite_v4 as C  # noqa: E402

W, H = C.W, C.H
DAY = np.array([0.62, 0.66, 0.70], np.float32)
C._SKY = np.broadcast_to(DAY, (H, W, 3)).copy()

REPRISE_S, FPS = 9.0, 30
LINE_AT, LINE_FADE = 2.0, 2.0
LINE_SRGB = (40, 110, 230)                            # a saturated mid blue (the user: "thicker and blue so it stands
LINE_RGB = C.lin(LINE_SRGB).astype(np.float32)        # out"; blue reads as water, red is the traced lines' colour)
LINE_A = 1.0                                          # opaque
EDGE_SRGB = (12, 34, 80)                              # a thin darker edge round it, so it reads on pale ground
EDGE_RGB = C.lin(EDGE_SRGB).astype(np.float32)
EDGE_PX = 1                                           # the edge: the band's matte grown by this, under the band
LABEL = "PROPOSED LEVEL · 12.7 M · VYSHNEVSKYI & SHEVCHUK 2024 · THE BED'S HEIGHTS INFERRED"
FONT = "/System/Library/Fonts/HelveticaNeue.ttc"
LABEL_PX, LABEL_PAD, LABEL_AT = 16, 6, (24, H - 24)     # as the 3D film's small labels (scene3d/animatic.py)


def ss(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def label_layer():
    """The label as an sRGB RGBA layer (premultiplied by nothing: PIL's straight alpha)."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    font = ImageFont.truetype(FONT, LABEL_PX)
    sw, gap = 22, 8                                   # a short stroke of the line's blue before the text: the key
    at = (LABEL_AT[0] + sw + gap, LABEL_AT[1])
    x0, y0, x1, y1 = dr.textbbox(at, LABEL, font=font, anchor="ld")
    x0 -= sw + gap
    p = LABEL_PAD
    dr.rectangle((x0 - p, y0 - p, x1 + p, y1 + p), fill=(0, 0, 0, 128))
    ym = (y0 + y1) / 2
    dr.rectangle((x0 - 1, ym - 3, x0 + sw + 1, ym + 3), fill=(*EDGE_SRGB, 255))
    dr.rectangle((x0, ym - 2, x0 + sw, ym + 2), fill=(*LINE_SRGB, 255))
    dr.text(at, LABEL, font=font, anchor="ld", fill=(255, 255, 255, 255))
    a = np.asarray(im).astype(np.float32) / 255
    return a[..., :3], a[..., 3:4], (x0 - p, y0 - p, x1 + p, y1 + p)


class Reprise(C.Passes):
    def __init__(self, d):
        super().__init__(d)
        L = C.read(f"{d}/contour.exr")
        self.line = np.clip(L[..., 0:1], 0, 1)          # the band's coverage (white emission, premultiplied)
        k = 2 * EDGE_PX + 1
        self.edge = cv2.dilate(self.line[..., 0], np.ones((k, k), np.uint8))[..., None]   # grown: the dark edge
        self.lab_rgb, self.lab_a, self.lab_box = label_layer()

    def frame_at(self, k_anim, t):
        f = float(ss((t - LINE_AT) / LINE_FADE))
        base = self.base
        if f > 0:
            e = self.edge * f
            base = base * (1 - e) + EDGE_RGB * e
            m = self.line * (LINE_A * f)
            base = base * (1 - m) + LINE_RGB * m
        an = C.read(f"{self.d}/anim/anim_{k_anim:04d}.exr") * self.M
        out = C.to8(C.over(an, base), seed=k_anim)
        if f > 0:
            a = self.lab_a * f
            out = np.clip(out.astype(np.float32) * (1 - a) + self.lab_rgb * 255 * a + 0.5, 0, 255).astype(np.uint8)
        return out


def encode(frames, n, wav, out, extra):
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "slow",
           "-crf", "14", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-c:a", "aac", "-b:a", "256k",
           "-shortest", out]
    t = time.time()
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for k in range(n):
        pr.stdin.write(frames(k).tobytes())
    pr.stdin.close()
    pr.wait()
    info = {"frames": n, "fps": FPS, "codec": "H.264 (libx264, preset slow, CRF 14, yuv420p)",
            "audio": os.path.relpath(wav) + " (AAC 256 kb/s)", "encode_s": round(time.time() - t, 1), **extra}
    json.dump(info, open(out.rsplit(".", 1)[0] + "_encode.json", "w"), indent=1)
    print(json.dumps(info))


def main():
    a = sys.argv[1:]
    if a[0] == "reprise":
        d, wav, out, A = a[1], a[2], a[3], int(a[4])
        rp = Reprise(d)
        n = int(REPRISE_S * FPS)
        if len(a) > 5:      # stills: plain, mid-fade, held
            for nm, k in (("plain", 30), ("fading", int((LINE_AT + LINE_FADE / 2) * FPS)), ("held", n - 1)):
                Image.fromarray(rp.frame_at(A + k, k / FPS)).save(f"{a[5]}_{nm}.png")
        encode(lambda k: rp.frame_at(A + k, k / FPS), n, wav, out,
               {"anim_frames": [A, A + n], "line_at_s": LINE_AT, "line_fade_s": LINE_FADE, "line_srgb": list(LINE_SRGB), "edge_srgb": list(EDGE_SRGB), "edge_px": EDGE_PX,
                "line_a": LINE_A, "label": LABEL, "label_box_px": [round(v) for v in rp.lab_box],
                "line_px": int((rp.line[..., 0] > 0.05).sum())})
    elif a[0] == "video":
        ps = C.Passes(a[1])
        n = len([f for f in os.listdir(f"{a[1]}/anim") if f.endswith(".exr")])
        encode(lambda k: C.to8(ps.frame(k), seed=k), n, a[2], a[3], {})
    else:
        C.main()


if __name__ == "__main__":
    main()
