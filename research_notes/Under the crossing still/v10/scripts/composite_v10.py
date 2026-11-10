"""The v10 shot `drowning` (the user, 9 November 2026, on v9: no birds; the stray branch gone (still_v10.py); "make it
a bit more realistic how the water will interact with the branches poking out of the water. maybe some white
water/flow around it since it is going to be interupting the water. this could also visually communicate better the
height of the water in relation to the trees since the camera is to remain not moving"). v9's shot otherwise: the
level 13.1 m from the first frame, the eye under it, v9's murk and calm surface, v7's moving pass (frames 900-1349).

The water round the stems (DRAWN, seen from under the surface): at every place a kept stem pierces the surface
(crossings_v10.py, from the plants' own geometry), the underside of the surface shows
- the meniscus: a thin dark-then-bright ring hugging the stem, where the surface bends up against the wood;
- a collar of foam and caught scum, heavier on the upstream side (the slow current presses it against the stem),
  its bubbles boiling slowly;
- a short wake trailing downstream with v7's CURRENT (toward the south-west): a widening band of broken foam flecks
  and streaks drifting with the surface at RIPPLES' first speed, fading over a few metres, and the surface itself
  more disturbed in it (the picture seen through it sways more there).
Foam seen from below is bright (it scatters the daylight above it) and fairly opaque; it is absorbed by the water
between it and the eye like everything else seen through the surface. Sizes scale with the stem's radius; thin
features are widened to the pixel's footprint and dimmed to match (no shimmer). The current's speed and the foam's
amounts are drawn, not measured.

    python -I composite_v10.py frames <v10_render_dir> <v5_render_dir> <v8_render_dir> <anim_dir> <out_dir> [A:B]
    python -I composite_v10.py frame  <v10_render_dir> <v5_render_dir> <v8_render_dir> <anim_dir> <K> <out.png>
    python -I composite_v10.py video  <frames_dir> <audio.wav> <out.mp4>
    python -I composite_v10.py sheet  <frames_dir> <out.png> [cols] [every_s]
"""
import json
import math
import os
import subprocess
import sys
import time

os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "1"
import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "v9", "scripts")))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "v7", "scripts")))
import composite_v7 as V7  # noqa: E402
import composite_v9 as C9  # noqa: E402   (v9's murk values, sheet, video)
C = V7.C

W, H, W2, H2 = V7.W, V7.H, V7.W2, V7.H2
FPS, N = C9.FPS, C9.N
DAY = V7.DAY
LEVEL = V7.LEVEL
EYE = V7.EYE
STATEMENT = ("PROPOSED LEVEL · 12.7 M · VYSHNEVSKYI & SHEVCHUK 2024 · THE TREES DEAD AND STANDING, THE WATER ROUND THEM "
             "AND THE BED'S HEIGHTS DRAWN OR INFERRED · DRAWN")

CUR = V7.CURRENT / np.linalg.norm(V7.CURRENT)                 # downstream, toward the south-west
CROSS = np.array([-CUR[1], CUR[0]])
FLOW = V7.RIPPLES[0]["v"]                                     # m/s: the foam drifts with the surface's ripples
FOAM = np.array([1.00, 1.02, 0.98], np.float32) * DAY / DAY.mean()   # foam from below: bright, the daylight above it
                                                             # scattered (not cut by the surface's Fresnel transmission)
WAKE = dict(len_m=(1.6, 26.0), spread=0.09, width_r=1.8)     # wake length = a + b * radius; its half-width grows
COLLAR = dict(width_m=0.03, width_r=1.4, alpha=0.85, up=0.55)  # foam collar: width = a + b * radius, upstream share
MENISCUS = dict(width_m=0.008, dark=0.5, bright=0.6)
WAKE_ALPHA = 0.5
WAKE_SLOPE = 0.06                                            # the surface's extra slope in the wake (cf. ripples 0.05)
R_MIN = 0.003                                                 # thinner stems are left out (reed culms barely mark it)


def _noise_tiles():
    h1, g1x, g1y = V7.tile_noise(41)
    h2, _, _ = V7.tile_noise(43)
    return h1, g1x, g1y, h2


NT = _noise_tiles()


def _sample(T, u, v):
    n = T.shape[0]
    return V7.remap(T, np.mod(u * n, n).astype(np.float32), np.mod(v * n, n).astype(np.float32), cv2.BORDER_WRAP)


def ss(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


class Scene10(V7.Scene):
    def __init__(self, rdir, v5dir, v8dir, animdir):
        super().__init__(rdir, v5dir, animdir)
        st2 = C.read(f"{rdir}/static2x.exr")
        self.base1 = V7.down2(self.plate2)
        a1 = V7.down2(st2[..., 3])
        A, B = C.read(f"{v5dir}/matte_A.exr")[..., 3], C.read(f"{v5dir}/matte_B.exr")[..., 3]
        wire = B > 1e-3
        M5 = np.where(wire, np.clip(A / np.maximum(B, 1e-6), 0, 1), 0)
        A9 = C.read(f"{rdir}/matte.exr")[..., 0]
        A0 = C.read(f"{v8dir}/matte_0000.exr")[..., 0]
        Mw = np.clip(M5 + (A9 - A0) / np.maximum(B, 1e-6), 0, 1)
        self.M = np.where(wire, Mw, 1 - a1)[..., None].astype(np.float32)
        self.under1 = (V7.down2((self.surf2 & (self.z2 < LEVEL)).astype(np.float32)) > 0.02)[..., None]
        # the view up through the surface is fixed (eye, level, rays): its pixels, surface points and footprints once
        d = self.rays2
        dz = d[..., 2]
        self.thr = ~(self.surf2 & (self.z2 < LEVEL)) & (dz > 1e-4)
        self.ty, self.tx = np.nonzero(self.thr)
        dw = d[self.ty, self.tx]
        tp = (LEVEL - EYE[2]) / dw[:, 2]
        self.tp, self.dw = tp, dw
        self.Pt = (EYE + tp[:, None] * dw)[:, :2]
        self.fpt = (tp * (36.0 / V7.VIEW["lens"] / W2) / dw[:, 2]).astype(np.float32)   # m a pixel on the surface
        self.cross = self._crossings(os.path.join(rdir, "crossings.npz"))

    def _crossings(self, path):
        """Per crossing: the thr pixels within its reach (indices into the thr arrays), precomputed."""
        c = np.load(path)
        idx_img = np.full((H2, W2), -1, np.int64)
        idx_img[self.ty, self.tx] = np.arange(len(self.ty))
        out = []
        rng = np.random.default_rng(10)
        for (x, y), r in zip(c["xy"], c["r"]):
            if r < R_MIN:
                continue
            Lw = WAKE["len_m"][0] + WAKE["len_m"][1] * r
            reach_up = 0.1 + 4 * r
            half = WAKE["width_r"] * r + WAKE["spread"] * Lw * 1.6 + 0.05
            corners = [np.array([x, y]) + CUR * a + CROSS * b for a in (-reach_up, Lw * 1.25) for b in (-half, half)]
            Q = np.array([[*q, LEVEL] for q in corners])
            i, j, f = V7.project(Q, W2, H2)
            if (f <= 0).any():
                continue
            x0, x1 = int(max(i.min() - 2, 0)), int(min(i.max() + 3, W2))
            y0, y1 = int(max(j.min() - 2, 0)), int(min(j.max() + 3, H2))
            if x1 <= x0 or y1 <= y0:
                continue
            ids = idx_img[y0:y1, x0:x1].ravel()
            ids = ids[ids >= 0]
            if not len(ids):
                continue
            rel = self.Pt[ids] - [x, y]
            u = rel @ CUR
            v = rel @ CROSS
            keep = (u > -reach_up) & (u < Lw * 1.25) & (np.abs(v) < half)
            if keep.any():
                out.append(dict(ids=ids[keep], u=u[keep].astype(np.float32), v=v[keep].astype(np.float32), r=float(r),
                                L=Lw, off=rng.uniform(0, 1, 2).astype(np.float32), ph=float(rng.uniform(0, 6.28))))
        return out

    def disturbance(self, t):
        """Over the thr pixels: foam opacity, the meniscus' brightness factor, extra slopes (sx, sy)."""
        n = len(self.ty)
        A = np.zeros(n, np.float32)
        K = np.ones(n, np.float32)
        sx = np.zeros(n, np.float32)
        sy = np.zeros(n, np.float32)
        h1, g1x, g1y, h2 = NT
        for c in self.cross:
            ids, u, v, r = c["ids"], c["u"], c["v"], c["r"]
            fp = self.fpt[ids]
            rho = np.sqrt(u * u + v * v) - r                     # from the stem's surface
            out = rho > -0.25 * fp
            # the meniscus: dark at the wood, a bright rim just beyond (widened to the pixel, dimmed to match)
            wm = MENISCUS["width_m"]
            we = np.maximum(wm, fp)
            k = wm / we
            dark = np.exp(-(np.maximum(rho, 0) / we) ** 2) * k * out
            bright = np.exp(-((rho - 1.6 * we) / we) ** 2) * k * out
            K[ids] *= 1 - MENISCUS["dark"] * dark
            # the collar: foam held against the stem, heavier upstream, boiling slowly
            wc = COLLAR["width_m"] + COLLAR["width_r"] * r
            wce = np.maximum(wc, fp)
            cosu = -u / np.maximum(rho + r, 1e-4)                  # 1 straight upstream
            side = (1 - COLLAR["up"]) + COLLAR["up"] * ss(0.5 + 0.5 * cosu)
            ang = np.arctan2(v, u)
            boil = _sample(h2, (ang / 6.2832 + c["off"][0] + 0.02 * t).astype(np.float32),
                           ((rho / (3 * wc + 0.01)) * 0.25 + c["off"][1] - 0.05 * t).astype(np.float32))
            coll = np.exp(-(np.maximum(rho, 0) / wce) ** 2) * (wc / wce) * side * ss(0.55 + 0.45 * boil) * out
            # the wake: downstream, widening, broken into flecks and streaks that drift with the surface
            Lw = c["L"]
            uu = np.maximum(u, 0)
            sig = WAKE["width_r"] * r + WAKE["spread"] * uu
            env = np.exp(-(v / np.maximum(sig, fp)) ** 2) * np.exp(-uu / Lw) * ss(u / (2 * r + 0.02)) * out
            s1 = (u - FLOW * t) / (2.5 + 20 * r)                   # patches drawn out along the flow (the tile's
            s2 = v / (0.6 + 12 * r)                                # features about a ninth of these lengths)
            fl = _sample(h1, (s1 + c["off"][0]).astype(np.float32), (s2 + c["off"][1]).astype(np.float32))
            fl2 = _sample(h2, (s1 * 2.3 + c["off"][1]).astype(np.float32), (s2 * 2.3 + c["off"][0] + 0.1 * math.sin(t + c["ph"])).astype(np.float32))
            fleck = ss((fl + 0.55 * fl2 - 0.15) / 1.0)
            # thin flecks far off average out: dimmed toward their mean where the pixel is larger than a fleck
            fsz = (0.6 + 12 * r) / 9
            mix = np.clip(fp / fsz, 0, 1)
            fleck = fleck * (1 - mix) + 0.35 * mix
            wake = env * fleck
            a = np.maximum(COLLAR["alpha"] * coll, WAKE_ALPHA * wake)
            a = np.maximum(a, MENISCUS["bright"] * bright)
            A[ids] = 1 - (1 - A[ids]) * (1 - a)
            # the surface more disturbed in the wake and round the stem: extra slope from the streak noise's gradient
            gu = _sample(g1x, (s1 + c["off"][0]).astype(np.float32), (s2 + c["off"][1]).astype(np.float32))
            gv = _sample(g1y, (s1 + c["off"][0]).astype(np.float32), (s2 + c["off"][1]).astype(np.float32))
            amp = WAKE_SLOPE * np.maximum(env, 0.6 * coll) / (1 + (fp / (0.3 * fsz)) ** 2)
            sx[ids] += amp * (gu * CUR[0] + gv * CROSS[0])
            sy[ids] += amp * (gu * CUR[1] + gv * CROSS[1])
        return np.clip(A, 0, 0.9), K, sx, sy

    def colour1(self, k_anim):
        """The picture above the surface at 1080p: the dead plate and the moving wires; under-surface pixels filled."""
        an = C.read(f"{self.animdir}/anim/anim_{k_anim:04d}.exr") * self.M
        src = C.over(an, self.base1).astype(np.float32)
        m = (~self.under1).astype(np.float32)
        num = cv2.GaussianBlur(src * m, (0, 0), C9.FILL_SIGMA)
        den = cv2.GaussianBlur(m, (0, 0), C9.FILL_SIGMA)[..., None]
        fill = np.where(den > 1e-3, num / np.maximum(den, 1e-4), DAY)
        return np.where(self.under1, fill, src).astype(np.float32), an

    def below(self, h, t, src1):
        """v7's below (its code, with v9's murk), the surface's disturbance round the stems added (see the docstring)."""
        d = self.rays2
        dz = d[..., 2]
        de = h - EYE[2]
        el = ss((dz + 0.3) / 0.9)[..., None]
        murk = (V7.MURK_DOWN * (1 - el) + V7.MURK_UP * el) * math.exp(-de / 5.0)
        out = np.empty((H2, W2, 3), np.float32)
        under = self.surf2 & (self.z2 < h)
        ys, xs = np.nonzero(under)
        T = np.exp(-self.d2[ys, xs][:, None] / V7.ABSORB_SILT_M)
        z = self.z2[ys, xs]
        lit = np.exp(-(h - z) / V7.DEPTH_DIM_M)[:, None]
        g = V7.SILT_MAX
        c = self.plate2[ys, xs]
        lum = (c @ np.array([0.2126, 0.7152, 0.0722], np.float32))[:, None]
        grey = lum / float(V7.SILT_TINT @ np.array([0.2126, 0.7152, 0.0722])) * V7.SILT_TINT
        c = (c * (1 - g) + grey * g) * (1 - 0.5 * g)
        out[ys, xs] = c * lit * T + murk[ys, xs] * (1 - T)
        # through the surface
        ys, xs, dw, tp, P = self.ty, self.tx, self.dw, self.tp, self.Pt
        sx, sy, hh = V7.ripples(P[:, 0].astype(np.float32), P[:, 1].astype(np.float32), t, self.fpt)
        A, K, dsx, dsy = self.disturbance(t)
        sx, sy = sx + dsx, sy + dsy
        Rm = V7.rotation()
        right, up = Rm[:, 0], Rm[:, 1]
        a = 2 * V7.WAVER_PX / 0.08
        u = xs + a * (sx * right[0] + sy * right[1])
        v = ys - a * (sx * up[0] + sy * up[1]) - a * 0.5 * (sx * right[1] - sy * right[0])
        src2 = cv2.resize(cv2.GaussianBlur(src1, (0, 0), C9.SRC_BLUR), (W2, H2), interpolation=cv2.INTER_LINEAR)
        col = V7.remap(src2, u.astype(np.float32), v.astype(np.float32), cv2.BORDER_REFLECT)
        col = col * K[:, None]
        T = np.exp(-tp[:, None] / V7.ABSORB_UP_M)
        tau = 1 - V7.schlick(np.clip(dw[:, 2], 0, 1))[:, None]
        col = col * (1 + V7.MOTTLE * hh[:, None]) * tau
        col = col * (1 - A[:, None]) + FOAM * A[:, None]           # the foam on the surface, over what is seen through it
        out[ys, xs] = col * T + murk[ys, xs] * (1 - T)
        rest = ~under & ~self.thr
        out[rest] = murk[rest]
        return out

    def frame(self, k):
        t = k / FPS
        src, an = self.colour1(V7.ANIM0 + k)
        out1 = V7.down2(self.below(LEVEL, t, src))
        return C.to8(out1, seed=V7.ANIM0 + k), LEVEL


def main():
    a = sys.argv[1:]
    if a[0] in ("frame", "frames"):
        C9.apply_murk()
    if a[0] == "frame":
        sc = Scene10(a[1], a[2], a[3], a[4])
        print("crossings drawn", len(sc.cross), flush=True)
        for kk in a[5].split(","):
            t0 = time.time()
            img, h = sc.frame(int(kk))
            Image.fromarray(img).save(a[6].replace("K", kk) if "K" in os.path.basename(a[6]) else a[6])
            print("frame", kk, "s", round(time.time() - t0, 1), flush=True)
    elif a[0] == "frames":
        out = a[5]
        os.makedirs(out, exist_ok=True)
        A_, B_ = (int(v) for v in a[6].split(":")) if len(a) > 6 else (0, N)
        todo = [k for k in range(A_, B_) if not os.path.exists(f"{out}/f_{k:04d}.png")]
        print("todo", len(todo), flush=True)
        if not todo:
            return
        sc = Scene10(a[1], a[2], a[3], a[4])
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
        C9.sheet(a[1], a[2], int(a[3]) if len(a) > 3 else 4, float(a[4]) if len(a) > 4 else 1.0)


if __name__ == "__main__":
    main()
