"""Lay the v4 renders together (from the project root, the project's venv):

    python -I composite_v4.py still <render.exr> <out.png>                     a full render over the sky
    python -I composite_v4.py frame <render_dir> <K> <out.png>                  frame K of the shot, from the passes
    python -I composite_v4.py frames <render_dir> <frames_dir> A:B             the shot's frames, as PNG
    python -I composite_v4.py video <render_dir> <audio.wav> <out.mp4>         the shot, H.264 with the sound
    python -I composite_v4.py compare <full.exr> <render_dir> <K> [diff.png]   the composite against a full render
    python -I composite_v4.py sky <out.png>                                    the sky alone (to set against EEVEE's)

The sky is v3's dawn world (still_v3.dawn_world: a gradient by the view's height, warm at the horizon, pale, then a
clear blue, and the low sun's glow, dot(view, sun)^10), evaluated per pixel in float from the still camera, then the
whole picture is turned to sRGB (the scene's view transform is Standard) with a triangular dither of one 8-bit step,
so no gradient bands. The renders are film-transparent and premultiplied (EXR, linear): over = a + (1 - alpha) b.

The passes in <render_dir> (still_v4.py): static.exr (all that does not move), anim/anim_KKKK.exr (only what moves,
over nothing), matte_A.exr and matte_B.exr (the moving wires' footprint with everything else as a holdout, and alone).
A frame is  moving x M  over  static  over  sky, where M is A / B on the wires' footprint (how much of each pixel of
the wires is in view: the wires, their glow and fittings are static geometry, only their shading moves) and, off it,
1 - the static plate's alpha (the birds: whatever static stands where a bird is, stands in front of it; the birds'
paths keep clear of everything behind them, birds_v4.py).
"""
import json
import math
import os
import sys

os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "1"
import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
VIEWS = os.path.join(HERE, "views_v4.json")
W, H = 1920, 1080
DAWN_AZ, DAWN_EL = 57.0, 6.0
RAMP = [(0.0, (236, 196, 164)), (0.12, (214, 204, 196)), (0.55, (118, 150, 196))]
GLOW = (255, 214, 160)


def lin(c):
    c = np.asarray(c, float) / 255
    return np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)


def srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x > 0.0031308, 1.055 * np.power(x, 1 / 2.4) - 0.055, 12.92 * x)


def view():
    v = next(v for v in json.load(open(VIEWS))["views"] if v["id"] == "f4")
    a, b = np.array(v["tower_from"]), np.array(v["tower_to"])
    ax = (b - a) / np.linalg.norm(b - a)
    v["heading_deg"] = math.degrees(math.atan2(ax[0], ax[1])) % 360
    return v


def rays(v, w=W, h=H):
    """World directions of each pixel's centre for the camera (Blender: rotation_euler XYZ (90 + pitch, 0, -heading))."""
    f = v["lens"] / 36.0
    xs = ((np.arange(w) + 0.5) / w - 0.5) / f
    ys = (0.5 - (np.arange(h) + 0.5) / h) * (h / w) / f
    X, Y = np.meshgrid(xs, ys)
    d = np.stack([X, Y, -np.ones_like(X)], -1)
    al, ga = math.radians(90 + v["pitch"]), -math.radians(v["heading_deg"])
    Rx = np.array([[1, 0, 0], [0, math.cos(al), -math.sin(al)], [0, math.sin(al), math.cos(al)]])
    Rz = np.array([[math.cos(ga), -math.sin(ga), 0], [math.sin(ga), math.cos(ga), 0], [0, 0, 1]])
    d = d @ (Rz @ Rx).T
    return d / np.linalg.norm(d, axis=-1, keepdims=True)


def smooth_ramp(z, pos, vals):
    """v3's colour ramp through the same stops, but C1: a monotone cubic (Fritsch-Carlson slopes inside, level at
    both ends) in place of Blender's linear interpolation, whose kinks at the stops showed as faint bands (Mach bands,
    curving across the wide lens's sky as 'diagonal' streaks)."""
    pos, vals = np.asarray(pos, float), np.asarray(vals, float)
    h = np.diff(pos)
    d = np.diff(vals) / h
    m = np.zeros(len(pos))
    for i in range(1, len(pos) - 1):
        if d[i - 1] * d[i] > 0:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
    zc = np.clip(z, pos[0], pos[-1])
    j = np.clip(np.searchsorted(pos, zc) - 1, 0, len(pos) - 2)
    t = (zc - pos[j]) / h[j]
    h00, h10, h01, h11 = 2 * t ** 3 - 3 * t ** 2 + 1, t ** 3 - 2 * t ** 2 + t, -2 * t ** 3 + 3 * t ** 2, t ** 3 - t ** 2
    return h00 * vals[j] + h10 * h[j] * m[j] + h01 * vals[j + 1] + h11 * h[j] * m[j + 1]


def sky(v, linear=False):
    n = rays(v)
    z = n[..., 2]
    pos = [p for p, _ in RAMP]
    cols = np.array([lin(c) for _, c in RAMP])
    if linear:     # exactly v3's world (Blender's linear ramp), for comparison
        ramp = np.stack([np.interp(z, pos, cols[:, k]) for k in range(3)], -1)
    else:
        ramp = np.stack([smooth_ramp(z, pos, cols[:, k]) for k in range(3)], -1)
    az, el = math.radians(DAWN_AZ), math.radians(DAWN_EL)
    sun = np.array([math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)])
    g = np.clip(np.power(n @ sun, 10), 0, 1)[..., None]
    return ramp * (1 - g) + lin(GLOW) * g


def read(path):
    a = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if a is None:
        raise SystemExit(f"cannot read {path}")
    a = a.astype(np.float32)
    return np.concatenate([a[..., 2::-1], a[..., 3:4]], -1)        # BGRA to RGBA (premultiplied, linear)


class Passes:
    def __init__(self, d):
        self.d = d
        st = read(f"{d}/static.exr")
        self.base = over(st, the_sky())
        A, B = read(f"{d}/matte_A.exr")[..., 3], read(f"{d}/matte_B.exr")[..., 3]
        self.M = np.where(B > 1e-3, np.clip(A / np.maximum(B, 1e-6), 0, 1), 1 - st[..., 3])[..., None]

    def frame(self, k):
        an = read(f"{self.d}/anim/anim_{k:04d}.exr") * self.M
        return over(an, self.base)


def over(top, bottom_rgb):
    return top[..., :3] + (1 - top[..., 3:4]) * bottom_rgb


def to8(rgb, seed=0):
    rng = np.random.default_rng(seed)
    s = srgb(rgb) * 255
    s = s + (rng.random(s.shape) - rng.random(s.shape))            # triangular dither, one step
    return np.clip(np.round(s), 0, 255).astype(np.uint8)


_SKY = None


def the_sky():
    global _SKY
    if _SKY is None:
        _SKY = sky(view())
    return _SKY


def main():
    a = sys.argv[1:]
    if a[0] == "sky":
        Image.fromarray(to8(the_sky())).save(a[1])
        if len(a) > 2:
            Image.fromarray(to8(sky(view(), linear=True))).save(a[2])
    elif a[0] == "still":
        Image.fromarray(to8(over(read(a[1]), the_sky()))).save(a[2])
    elif a[0] == "frame":
        Image.fromarray(to8(Passes(a[1]).frame(int(a[2])), seed=int(a[2]))).save(a[3])
    elif a[0] == "frames":
        ps = Passes(a[1])
        A, B = (int(x) for x in a[3].split(":"))
        os.makedirs(a[2], exist_ok=True)
        for k in range(A, B):
            Image.fromarray(to8(ps.frame(k), seed=k)).save(f"{a[2]}/f_{k:04d}.png", compress_level=1)
        print("frames", A, B)
    elif a[0] == "video":
        import subprocess
        import time
        ps = Passes(a[1])
        n = len([f for f in os.listdir(f"{a[1]}/anim") if f.endswith(".exr")])
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
               "-r", "30", "-i", "-", "-i", a[2], "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "slow",
               "-crf", "14", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-c:a", "aac", "-b:a", "256k",
               "-shortest", a[3]]
        t = time.time()
        pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for k in range(n):
            pr.stdin.write(to8(ps.frame(k), seed=k).tobytes())
        pr.stdin.close()
        pr.wait()
        info = {"frames": n, "fps": 30, "codec": "H.264 (libx264, preset slow, CRF 14, yuv420p)",
                "audio": os.path.relpath(a[2]) + " (AAC 256 kb/s)", "encode_s": round(time.time() - t, 1)}
        json.dump(info, open(a[3].rsplit(".", 1)[0] + "_encode.json", "w"), indent=1)
        print(json.dumps(info))
    elif a[0] == "compare":
        full = srgb(over(read(a[1]), the_sky())) * 255
        comp = srgb(Passes(a[2]).frame(int(a[3]))) * 255
        d = np.abs(full - comp).max(-1)
        out = {"max": round(float(d.max()), 2), "mean": round(float(d.mean()), 4), "px_over_2": int((d > 2).sum()),
               "px_over_8": int((d > 8).sum()), "px_over_32": int((d > 32).sum())}
        print(json.dumps(out))
        if len(a) > 4:
            Image.fromarray(np.clip(d * 8, 0, 255).astype(np.uint8)).save(a[4])
            json.dump(out, open(a[4].rsplit(".", 1)[0] + ".json", "w"), indent=1)


if __name__ == "__main__":
    main()
