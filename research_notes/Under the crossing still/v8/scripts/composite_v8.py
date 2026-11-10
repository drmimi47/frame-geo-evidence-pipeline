"""The v8 shot `drowning` (the user, 8 November 2026: the plants die off as the water rises; the eye stays put and ends
under the water, with only the water, the bare bed, the tower and the lit wires left). v7's compositor
(composite_v7.py, imported, unchanged) draws the water exactly as in v7; what changes is the picture it draws the water
on: per frame, the passes still_v8.py rendered with the plants dying (dieoff_v8.py), instead of v6's passes rendered
once.

Per frame k:
- the plate without the moving parts: frames rendered at 2x: v5's own 1080p plate plus the 2x plate's change from
  v6's static plate (so where nothing has changed the picture is v5's exactly, as in v7); frames rendered at 1x
  (from under the surface on): the 1x render itself (as v5's plate was made);
- the surfaces' heights and distances: the frame's own 2x pass (the water's order against the plants);
- the lit wires' matte: v5's matte plus the change of the frame's matte render from frame 0's (rendered every
  MSTEP frames, linearly between: the dying plants uncover wires behind them);
- before the die-off's first change and after its last, the passes of the nearest rendered frame (v6's / v5's before).
Under the water, from MURK_SETTLE on, the silt is drawn settling as the dying ends (the absorption toward the bottom
lengthening a little, so the bare bed shows faintly) and the bed greyed further toward silt: a drawn convention.

    python -I composite_v8.py frames <pass_dir> <v6_render_dir> <v5_render_dir> <anim_dir> <out_dir> [A:B]
    python -I composite_v8.py frame  <pass_dir> <v6_render_dir> <v5_render_dir> <anim_dir> <K> <out.png>
    python -I composite_v8.py video  <frames_dir> <audio.wav> <out.mp4>
    python -I composite_v8.py sheet  <frames_dir> <out.png> [cols] [every_s]
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
import dieoff_v8 as DO  # noqa: E402
C = V7.C

W, H, W2, H2 = V7.W, V7.H, V7.W2, V7.H2
FPS, SECONDS = 30, 15.0
N = int(FPS * SECONDS)
DAY = V7.DAY
STATEMENT = ("PROPOSED LEVEL · 12.7 M · VYSHNEVSKYI & SHEVCHUK 2024 · THE PLANTS' DYING COMPRESSED FROM YEARS · "
             "THE BED'S HEIGHTS INFERRED · DRAWN")          # not on the picture (the user): to be said elsewhere
# the silt settling as the dying ends (drawn): absorption toward what lies under the surface, v7's -> SETTLED
MURK_SETTLE = (10.5, 13.5)
ABSORB_SILT_V7 = V7.ABSORB_SILT_M.copy()
ABSORB_SILT_SETTLED = np.array([2.6, 2.3, 1.4], np.float32)
SILT_MAX_V7, SILT_MAX_SETTLED = V7.SILT_MAX, 0.92


def down2(a):
    return V7.down2(a)


def settle(t):
    return float(V7.ss((t - MURK_SETTLE[0]) / (MURK_SETTLE[1] - MURK_SETTLE[0])))


class Scene8(V7.Scene):
    def __init__(self, pdir, rdir, v5dir, animdir):
        super().__init__(rdir, v5dir, animdir)        # v7's: v6's 2x passes, v5's plate and matte, the anim dir
        self.pdir = pdir
        self.ref_plate2 = self.plate2
        self.ref_pos = (self.surf2, self.z2, self.d2, self.dq, self.zq)
        self.ref_st2a = C.read(f"{rdir}/static2x.exr")[..., 3]
        self.ref_base1 = self.base1
        st1 = C.read(f"{v5dir}/static.exr")
        self.ref_st1a = st1[..., 3]
        A, B = C.read(f"{v5dir}/matte_A.exr")[..., 3], C.read(f"{v5dir}/matte_B.exr")[..., 3]
        self.B = B
        self.wire = B > 1e-3
        self.M5 = np.where(self.wire, np.clip(A / np.maximum(B, 1e-6), 0, 1), 0)
        ks = sorted(int(f[7:11]) for f in os.listdir(pdir) if f.startswith("static_") and f.endswith(".exr"))
        self.ks = ks
        self.mks = sorted(int(f[6:10]) for f in os.listdir(pdir) if f.startswith("matte_") and f.endswith(".exr"))
        self.A0 = C.read(f"{pdir}/matte_0000.exr")[..., 0] if os.path.exists(f"{pdir}/matte_0000.exr") else None
        self.first, self.last = DO_range(pdir)

    def _src(self, k):
        """The rendered frame whose plants stand as at frame k (none before the die-off's first change)."""
        if k < self.first:
            return None
        return min(k, self.last)

    def _matte(self, k):
        """The frame's wire matte change, A_k - A_0, from the matte renders (every MSTEP frames; linear between)."""
        ms = [m for m in self.mks if m <= max(k, 0)]
        lo = ms[-1] if ms else None
        hi = next((m for m in self.mks if m >= k), None)
        if lo is None and hi is None:
            return 0
        rd = lambda m: C.read(f"{self.pdir}/matte_{m:04d}.exr")[..., 0]   # noqa: E731
        if hi is None or lo == hi or lo is None:
            a = rd(lo if lo is not None else hi)
        else:
            w = (k - lo) / (hi - lo)
            a = rd(lo) * (1 - w) + rd(hi) * w
        return a - self.A0

    def load(self, k):
        j = self._src(k)
        if j is None:                                       # nothing has changed yet: v7's passes as they are
            st2 = None
        else:
            st = C.read(f"{self.pdir}/static_{j:04d}.exr")
            st2 = st
        if st2 is None:
            plate2 = self.ref_plate2
            pic1 = self.ref_base1
            a1 = self.ref_st1a
            p = None
        elif st2.shape[0] == H2:
            plate2 = C.over(st2, np.broadcast_to(DAY, (H2, W2, 3))).astype(np.float32)
            pic1 = np.maximum(self.ref_base1 + down2(plate2 - self.ref_plate2), 0)
            a1 = np.clip(self.ref_st1a + down2(st2[..., 3] - self.ref_st2a), 0, 1)
        else:
            pic1 = C.over(st2, np.broadcast_to(DAY, (H, W, 3))).astype(np.float32)
            plate2 = cv2.resize(pic1, (W2, H2), interpolation=cv2.INTER_LINEAR)
            a1 = st2[..., 3]
        if j is not None:
            p = C.read(f"{self.pdir}/pos_{j:04d}.exr")
            self.surf2 = p[..., 3] > 0.5
            self.z2 = np.where(self.surf2, p[..., 0], 1e4).astype(np.float32)
            self.d2 = np.where(self.surf2, p[..., 1], 1e6).astype(np.float32)
            q = 4
            d4 = self.d2.reshape(H2 // q, q, W2 // q, q).transpose(0, 2, 1, 3).reshape(H2 // q, W2 // q, q * q)
            z4 = self.z2.reshape(H2 // q, q, W2 // q, q).transpose(0, 2, 1, 3).reshape(H2 // q, W2 // q, q * q)
            kk = d4.argmin(-1)
            self.dq = np.take_along_axis(d4, kk[..., None], -1)[..., 0]
            self.zq = np.take_along_axis(z4, kk[..., None], -1)[..., 0]
            dA = self._matte(j) if self.A0 is not None else 0
        else:
            self.surf2, self.z2, self.d2, self.dq, self.zq = self.ref_pos
            dA = 0
        self.plate2 = plate2
        self.plate2_down = down2(plate2)
        self.base1 = pic1
        Mw = np.clip(self.M5 + dA / np.maximum(self.B, 1e-6), 0, 1)
        self.M = np.where(self.wire, Mw, 1 - a1)[..., None].astype(np.float32)

    def frame(self, k):
        t = k / FPS
        self.load(k)
        s = settle(t)
        V7.ABSORB_SILT_M = (ABSORB_SILT_V7 * (1 - s) + ABSORB_SILT_SETTLED * s).astype(np.float32)
        V7.SILT_MAX = SILT_MAX_V7 * (1 - s) + SILT_MAX_SETTLED * s
        return super().frame(k)


def DO_range(pdir):
    """The die-off's first and last changing frames (written by run_v8.sh's plan, else from the passes on disk)."""
    p = os.path.join(pdir, "plan.json")
    if os.path.exists(p):
        j = json.load(open(p))
        return j["first"], j["last"]
    ks = sorted(int(f[7:11]) for f in os.listdir(pdir) if f.startswith("static_") and f.endswith(".exr"))
    return (ks[0], ks[-1]) if ks else (10 ** 9, 10 ** 9)


def sheet(fdir, out, cols=5, every_s=1.0):
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
    if a[0] == "frame":
        sc = Scene8(a[1], a[2], a[3], a[4])
        t0 = time.time()
        img, h = sc.frame(int(a[5]))
        Image.fromarray(img).save(a[6])
        print("frame", a[5], "level", round(h, 3), "s", round(time.time() - t0, 1))
    elif a[0] == "frames":
        out = a[5]
        os.makedirs(out, exist_ok=True)
        A, B = (int(v) for v in a[6].split(":")) if len(a) > 6 else (0, N)
        todo = [k for k in range(A, B) if not os.path.exists(f"{out}/f_{k:04d}.png")]
        print("todo", len(todo), flush=True)
        if not todo:
            return
        sc = Scene8(a[1], a[2], a[3], a[4])
        for k in todo:
            if os.path.exists(f"{out}/f_{k:04d}.png"):
                continue
            t0 = time.time()
            img, h = sc.frame(k)
            tmp = f"{out}/.f_{k:04d}.{os.getpid()}.png"
            Image.fromarray(img).save(tmp, compress_level=1)
            os.replace(tmp, f"{out}/f_{k:04d}.png")
            print("frame", k, "level", round(h, 3), "s", round(time.time() - t0, 1), flush=True)
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
        sheet(a[1], a[2], int(a[3]) if len(a) > 3 else 5, float(a[4]) if len(a) > 4 else 1.0)


if __name__ == "__main__":
    main()
