"""The v9 shot `drowning` (the user, 8 November 2026: "instead of the water rising from the bottom up i want the start
of v9 to already have the water at the full height of the river ... right after under-the-crossing this v9 will play
and it will be a dramatic cut to the water already fully back"; "the murkiness has to be toned down a bit so that the
two powerlines and their towers are a bit more visible. let the camera stay where it is"). v7's compositor
(composite_v7.py, imported, unchanged) draws the water; here:
- the level is the proposed level (13.1 m, 12.7 Baltic + 0.4) from the first frame: no rise, no waterline over the
  lens; the eye (10.85 m) is under the surface throughout, v7's `below` every frame;
- the picture it draws the water on is still_v9.py's passes, rendered once with the plants dead (dead_v9.py): the
  plate (2x; the 1080p picture through the surface is its half size), heights and distances (2x), and the wires'
  matte (v5's matte plus the change of the dead state's matte render from v8's frame 0, the plants alive);
- the moving parts are v7's (under_the_crossing's moving pass continued: frames 900-1349), so the wires' flow runs on
  from the shot before; the two perched cormorants (birds_v9.py) are laid over the picture above the surface, so they
  waver through it with the treetops and the towers;
- less murk (drawn): the absorption up through the surface and toward what lies under it twice v7's and more
  (MURK below), the murk itself a little lighter, the surface calmer (the picture through it sways less);
- what lies under the surface has been under for years (the dead trees, the bed): greyed toward silt at once (v7's
  SILT_MAX, v8's settled value).
STATEMENT is not on the picture (the user): to be said elsewhere in the film.

    python -I composite_v9.py frames <v9_render_dir> <v5_render_dir> <v8_render_dir> <anim_dir> <out_dir> [A:B]
    python -I composite_v9.py frame  <v9_render_dir> <v5_render_dir> <v8_render_dir> <anim_dir> <K> <out.png>
    python -I composite_v9.py video  <frames_dir> <audio.wav> <out.mp4>
    python -I composite_v9.py sheet  <frames_dir> <out.png> [cols] [every_s]
"""
import json
import os
import subprocess
import sys
import time

os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "1"
import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "v7", "scripts")))
import composite_v7 as V7  # noqa: E402
import birds_v9 as BD  # noqa: E402
C = V7.C

W, H, W2, H2 = V7.W, V7.H, V7.W2, V7.H2
FPS, SECONDS = 30, 15.0
N = int(FPS * SECONDS)
DAY = V7.DAY
LEVEL = V7.LEVEL
STATEMENT = ("PROPOSED LEVEL · 12.7 M · VYSHNEVSKYI & SHEVCHUK 2024 · THE TREES DEAD AND STANDING, THE BIRDS AND THE "
             "BED'S HEIGHTS DRAWN OR INFERRED · DRAWN")
# less murk than v7/v8 (the user): v7's values, for the record, in v9.json
MURK = dict(
    ABSORB_UP_M=np.array([10.0, 10.5, 7.6], np.float32),     # v7 [4.8, 5.0, 3.6]: the towers and wires through the surface
    ABSORB_SILT_M=np.array([3.4, 3.0, 1.9], np.float32),     # v7 [1.7, 1.5, 0.9], v8 settled [2.6, 2.3, 1.4]
    MURK_UP=C.lin((104, 101, 70)).astype(np.float32),        # v7 (96, 92, 60)
    MURK_DOWN=C.lin((26, 24, 16)).astype(np.float32),        # v7 (20, 18, 11)
    WAVER_PX=3.0,                                            # v7 9.0: a calmer surface
    SILT_MAX=0.9,                                            # v7 0.8, v8 settled 0.92: long under
)
SRC_BLUR = 0.8                                               # v7 blurs the picture through the surface by 1.2 px
FINE_RIPPLE_A = 0.015                                        # v7 0.030: the short ripples' slope (they shredded the
                                                             # birds and the towers' lattice)
FILL_SIGMA = 6.0                                             # px: what lies under the surface, filled from round it in
                                                             # the picture seen up through the surface (see colour1)


def apply_murk():
    for k, v in MURK.items():
        setattr(V7, k, v)
    V7.submerged_at = lambda z: np.full(np.shape(z), -1e6)  # under for years: greyed toward silt at once
    V7.RIPPLES[1]["a"] = FINE_RIPPLE_A


class Scene9(V7.Scene):
    def __init__(self, rdir, v5dir, v8dir, animdir):
        super().__init__(rdir, v5dir, animdir)          # v9's 2x passes as v7 reads v6's; v5's plate and matte
        st2 = C.read(f"{rdir}/static2x.exr")
        self.base1 = V7.down2(self.plate2)              # the 1080p picture: the dead plate at half size
        a1 = V7.down2(st2[..., 3])
        A, B = C.read(f"{v5dir}/matte_A.exr")[..., 3], C.read(f"{v5dir}/matte_B.exr")[..., 3]
        wire = B > 1e-3
        M5 = np.where(wire, np.clip(A / np.maximum(B, 1e-6), 0, 1), 0)
        A9 = C.read(f"{rdir}/matte.exr")[..., 0]
        A0 = C.read(f"{v8dir}/matte_0000.exr")[..., 0]  # the same matte render with the plants alive (v8's frame 0)
        Mw = np.clip(M5 + (A9 - A0) / np.maximum(B, 1e-6), 0, 1)
        self.M = np.where(wire, Mw, 1 - a1)[..., None].astype(np.float32)
        self.birds = BD.Birds(os.path.join(rdir, "perch.json"), f"{rdir}/pos2x.exr")
        # what the eye sees up through the surface is only what stands above it: v7 sampled the whole picture, so the
        # stems under the surface near the eye showed again beside themselves, wavering (pale 'hairs' along them);
        # their pixels are filled from round them (a normalised blur) in that picture
        self.under1 = (V7.down2((self.surf2 & (self.z2 < LEVEL)).astype(np.float32)) > 0.02)[..., None]

    def colour1(self, k_anim):
        """The picture above the surface at 1080p: the dead plate, the moving wires, and the perched birds."""
        an = C.read(f"{self.animdir}/anim/anim_{k_anim:04d}.exr") * self.M
        src = C.over(an, self.base1).astype(np.float32)
        b = self.birds.layer((k_anim - V7.ANIM0) / FPS)
        src = C.over(b, src).astype(np.float32)
        m = (~self.under1).astype(np.float32)
        num = cv2.GaussianBlur(src * m, (0, 0), FILL_SIGMA)
        den = cv2.GaussianBlur(m, (0, 0), FILL_SIGMA)[..., None]
        fill = num / np.maximum(den, 1e-4)
        fill = np.where(den > 1e-3, fill, DAY)
        return np.where(self.under1, fill, src).astype(np.float32), an

    def below(self, h, t, src1):
        # v7's below, its 1.2 px blur of the picture through the surface swapped for SRC_BLUR for the call
        g = cv2.GaussianBlur
        cv2.GaussianBlur = lambda a, k, s, *r, **kw: g(a, k, SRC_BLUR if s == 1.2 else s, *r, **kw)
        try:
            return super().below(h, t, src1)
        finally:
            cv2.GaussianBlur = g

    def frame(self, k):
        t = k / FPS
        src, an = self.colour1(V7.ANIM0 + k)
        out1 = V7.down2(self.below(LEVEL, t, src))
        return C.to8(out1, seed=V7.ANIM0 + k), LEVEL


def sheet(fdir, out, cols=4, every_s=1.0):
    ks = [k for k in range(0, N, int(round(every_s * FPS)))] + [N - 1]
    ims = []
    for k in ks:
        im = Image.open(f"{fdir}/f_{k:04d}.png").convert("RGB").resize((384, 216), Image.LANCZOS)
        ImageDraw.Draw(im).text((6, 4), f"{k / FPS:.1f} s", fill=(255, 255, 255))
        ims.append(im)
    rows = -(-len(ims) // cols)
    S = Image.new("RGB", (cols * 384, rows * 216))
    for i, im in enumerate(ims):
        S.paste(im, ((i % cols) * 384, (i // cols) * 216))
    S.save(out)


def main():
    a = sys.argv[1:]
    if a[0] in ("frame", "frames"):
        apply_murk()
    if a[0] == "frame":
        sc = Scene9(a[1], a[2], a[3], a[4])
        t0 = time.time()
        img, h = sc.frame(int(a[5]))
        Image.fromarray(img).save(a[6])
        print("frame", a[5], "s", round(time.time() - t0, 1))
    elif a[0] == "frames":
        out = a[5]
        os.makedirs(out, exist_ok=True)
        A, B = (int(v) for v in a[6].split(":")) if len(a) > 6 else (0, N)
        todo = [k for k in range(A, B) if not os.path.exists(f"{out}/f_{k:04d}.png")]
        print("todo", len(todo), flush=True)
        if not todo:
            return
        sc = Scene9(a[1], a[2], a[3], a[4])
        for k in todo:
            if os.path.exists(f"{out}/f_{k:04d}.png"):
                continue
            t0 = time.time()
            img, h = sc.frame(k)
            tmp = f"{out}/.f_{k:04d}.{os.getpid()}.png"
            Image.fromarray(img).save(tmp, compress_level=1)
            os.replace(tmp, f"{out}/f_{k:04d}.png")
            print("frame", k, "s", round(time.time() - t0, 1), flush=True)
    elif a[0] == "video":
        fdir, wav, out = a[1], a[2], a[3]
        n = len([f for f in os.listdir(fdir) if f.startswith("f_") and f.endswith(".png")])
        if n != N:
            raise SystemExit(f"{n} of {N} frames on disk")
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", f"{fdir}/f_%04d.png", "-i", wav,
               "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p",
               "-movflags", "+faststart", "-c:a", "aac", "-b:a", "256k", "-shortest", out]
        t = time.time()
        subprocess.run(cmd, check=True)
        info = {"frames": n, "fps": FPS, "codec": "H.264 (libx264, preset slow, CRF 16, yuv420p)",
                "audio": os.path.relpath(wav) + " (AAC 256 kb/s)", "encode_s": round(time.time() - t, 1)}
        json.dump(info, open(out.rsplit(".", 1)[0] + "_encode.json", "w"), indent=1)
        print(json.dumps(info))
    elif a[0] == "sheet":
        sheet(a[1], a[2], int(a[3]) if len(a) > 3 else 4, float(a[4]) if len(a) > 4 else 1.0)


if __name__ == "__main__":
    main()
