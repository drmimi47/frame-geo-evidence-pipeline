"""The v7 shot `drowning` (the user, 6 November 2026: a second pass to replace waterline-reprise, following directly
on under-the-crossing), drawn frame by frame from v6's passes, as v6 (composite_v6.py, kept as it was), with:
- no blue line, no label: from v5's plain picture;
- the moving parts continued from where under_the_crossing_f_day.mp4 ends: its moving pass (the lit wires' flow and
  the drawn birds) rendered on past its 900 frames by v5's own still_v5.py (frames 900-1349 of the same timeline), so
  frame 0 here is the frame after its last; where there is no water, the picture is v5's 1080p plate itself (the
  water is added as a difference from the 2x plate, so dry pixels are v5's exactly);
- the rise from the first frame (0-10 s), held under to 15 s;
- under the water a darker, siltier bottom (a DRAWN CONVENTION, to show that the plants die when it refloods):
  brown-green suspended silt, shorter absorption under the surface, darker toward the bottom, the submerged plants
  dulled, darkened and greyed toward silt the longer they are under; the tower and the wires kept faintly readable
  through the surface; the underside's ripple brightness toned down.

    python -I composite_v7.py frames <render_dir> <v5_render_dir> <anim_dir> <out_dir> [A:B]    PNG per frame, skips
                                                                                                frames on disk
    python -I composite_v7.py frame  <render_dir> <v5_render_dir> <anim_dir> <K> <out.png>
    python -I composite_v7.py video  <frames_dir> <audio.wav> <out.mp4>
    python -I composite_v7.py timeline

The water itself is v6's (see composite_v6.py): a flat surface at h(t) covering the pixels whose visible surface lies
below it, the scene's water material from above, the drawn meniscus over the lens, and from below a drawn convention
(Snell's window not drawn).
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
V5S = os.path.abspath(os.path.join(HERE, "..", "..", "scripts"))
sys.path.insert(0, V5S)
import composite_v5 as C5  # noqa: E402
C = C5.C                                             # composite_v4: read, over, to8, lin, srgb, rays

W, H = 1920, 1080
W2, H2 = 2 * W, 2 * H
FPS, SECONDS = 30, 15.0
N = int(FPS * SECONDS)
ANIM0 = 900                                          # the 30 s shot's moving pass continued: frames 900-1349
EYE = np.array([4355.0, 6870.0, 10.854730606079102])  # the static log's camera (ground 9.255 m + 1.6 m)
VIEW = dict(lens=18.0, pitch=14.0, heading_deg=22.0)

LEVEL_BALTIC, BALTIC_TO_EGM2008 = 12.7, 0.4
LEVEL = LEVEL_BALTIC + BALTIC_TO_EGM2008             # 13.1 m, scene z (FABDEM's metres above EGM2008)
H0 = 9.0                                             # where the drawn rise starts: just under the lowest ground the
                                                     # view shows (the lane's ground, 9.25 m at the camera; the pass:
                                                     # 0.2% of pixels under 9.25 m, none under 9.0 but a few far off)
RISE = (0.0, 10.0)                                   # s: the rise, eased (slow start, steady, slowing to the level)
EASE_IN, EASE_OUT = 0.2, 0.4                         # shares of the rise spent speeding up and slowing down
WATER_IN = 0.8                                       # s: the water's opacity at the first frames (see above1)
WIPE_S = 0.5                                         # the waterline's sweep over the lens

DAY = C5.DAY                                         # the overcast world, linear
BODY = np.array([0.0176, 0.0252, 0.0176], np.float32)        # the scene's water colour (material "water")
GLOSS_TINT, FRESNEL_MIX, IOR = 0.8, 0.5, 1.333                # the scene's glossy tint, its Fresnel x 0.5
SHALLOW_M = 0.12                                     # path in water (m) over which the ground stops showing (drawn)
CURRENT = np.array([-0.7071, -0.7071])               # toward the south-west (roughly toward the camera)
RIPPLES = [  # tile (m), drift speed (m/s), direction, slope amplitude, feature size (m) for distance filtering
    dict(tile=7.0, v=0.30, dir=CURRENT, a=0.050, feat=0.9),
    dict(tile=1.9, v=0.42, dir=np.array([-0.5, -0.866]), a=0.030, feat=0.25),
]
# under the surface (drawn): absorption lengths along the ray per channel (m), murk colours (sRGB)
ABSORB_UP_M = np.array([4.8, 5.0, 3.6], np.float32)  # along a ray up through the surface: the tower kept faint
ABSORB_SILT_M = np.array([1.7, 1.5, 0.9], np.float32)  # toward what lies under the surface: silt-laden, short
MURK_UP = C.lin((96, 92, 60)).astype(np.float32)     # brown-green suspended silt, lit from above
MURK_DOWN = C.lin((20, 18, 11)).astype(np.float32)   # darker toward the bottom
DEPTH_DIM_M = 1.6                                    # light falls off with depth below the surface (drawn)
SILT_TINT = C.lin((74, 68, 50)).astype(np.float32)   # the greyed silt colour the drowned plants turn toward
SILT_TAU_S = 2.5                                     # how fast (in the shot's compressed time) they dull
SILT_MAX = 0.8                                       # how far toward silt at most
MOTTLE = 0.05                                        # the surface's underside brighter and darker with its ripples
WAVER_PX = 9.0                                       # the through-surface picture's sway at 1080p (drawn)
STATEMENT = ("PROPOSED LEVEL · 12.7 M · VYSHNEVSKYI & SHEVCHUK 2024 · REACHED OVER MONTHS · THE BED'S HEIGHTS "
             "INFERRED · DRAWN")                 # not on the picture (the user): to be said elsewhere in the film


# ---------------------------------------------------------------- the timeline

def _ease_table(n=20001):
    u = np.linspace(0, 1, n)
    v = np.ones_like(u)
    a, b = EASE_IN, EASE_OUT
    v = np.where(u < a, np.sin(np.pi / 2 * u / a) ** 2, v)
    v = np.where(u > 1 - b, np.sin(np.pi / 2 * (1 - u) / b) ** 2, v)
    s = np.concatenate([[0], np.cumsum((v[1:] + v[:-1]) / 2)])
    return u, s / s[-1]


_U, _S = _ease_table()


def level_at(t):
    u = (t - RISE[0]) / (RISE[1] - RISE[0])
    return H0 + (LEVEL - H0) * float(np.interp(u, _U, _S))


def crossing_s():
    """When the level passes the eye."""
    f = (EYE[2] - H0) / (LEVEL - H0)
    return RISE[0] + (RISE[1] - RISE[0]) * float(np.interp(f, _S, _U))


_TS = np.linspace(RISE[0], RISE[1], 4001)
_HS = None


def submerged_at(z):
    """When the drawn level reached height z (s; inf where it never does)."""
    global _HS
    if _HS is None:
        _HS = np.array([level_at(t) for t in _TS])
    return np.where(z <= LEVEL, np.interp(z, _HS, _TS), np.inf)


def timeline():
    tc = crossing_s()
    first = next(k for k in range(N) if level_at(k / FPS) > 9.3)
    return {"frames": N, "fps": FPS, "seconds": SECONDS, "rise_s": list(RISE), "ease": [EASE_IN, EASE_OUT],
            "level_start_m": H0, "level_end_m": LEVEL, "eye_m": round(float(EYE[2]), 3),
            "lens_crossing_s": round(tc, 3), "lens_crossing_frame": round(tc * FPS),
            "wipe_s": [round(tc - WIPE_S / 2, 3), round(tc + WIPE_S / 2, 3)],
            "first_water_seen_frame": first,
            "level_by_second": {f"{s:.0f}": round(level_at(s), 3) for s in np.arange(0, SECONDS + 0.01, 1.0)}}


# ---------------------------------------------------------------- geometry

def rotation():
    al, ga = math.radians(90 + VIEW["pitch"]), -math.radians(VIEW["heading_deg"])
    Rx = np.array([[1, 0, 0], [0, math.cos(al), -math.sin(al)], [0, math.sin(al), math.cos(al)]])
    Rz = np.array([[math.cos(ga), -math.sin(ga), 0], [math.sin(ga), math.cos(ga), 0], [0, 0, 1]])
    return Rz @ Rx


def project(Q, w, h):
    """World points (..., 3) to pixel coordinates (i across, j down; centres at integers) and forward depth."""
    R = rotation()
    c = (Q - EYE) @ R                     # camera space (x right, y up, -z forward)
    f = VIEW["lens"] / 36.0
    fwd = -c[..., 2]
    fz = np.maximum(fwd, 1e-4)
    i = (c[..., 0] / fz * f + 0.5) * w - 0.5
    j = (0.5 - c[..., 1] / fz * f * w / h) * h - 0.5
    return i, j, fwd


def tile_noise(seed, n=512):
    """A periodic height field (unit RMS) and its gradient per tile length, from band-passed noise."""
    rng = np.random.default_rng(seed)
    k = np.fft.fftfreq(n) * n
    KX, KY = np.meshgrid(k, k)
    kk = np.hypot(KX, KY)
    amp = np.exp(-((kk - 9) / 5.0) ** 2) + 0.35 * np.exp(-((kk - 22) / 9.0) ** 2)
    F = (rng.standard_normal((n, n)) + 1j * rng.standard_normal((n, n))) * amp
    hgt = np.real(np.fft.ifft2(F))
    s = hgt.std()
    gx = np.real(np.fft.ifft2(F * 2j * np.pi * KX)) / s     # d/du over one tile
    gy = np.real(np.fft.ifft2(F * 2j * np.pi * KY)) / s
    g = math.sqrt((gx ** 2 + gy ** 2).mean() / 2)
    return (hgt / s).astype(np.float32), (gx / g).astype(np.float32), (gy / g).astype(np.float32)


TILES = [tile_noise(11 + i) for i in range(len(RIPPLES))]


def remap(T, u, v, border):
    """cv2.remap for coordinate arrays of any shape (cv2 wants both sides under 32767 px)."""
    shp = u.shape
    u, v = u.reshape(-1), v.reshape(-1)
    n, w = u.size, 16384
    rows = max(1, -(-n // w))
    pad = rows * w - n
    U = np.concatenate([u, np.zeros(pad, np.float32)]).reshape(rows, w).astype(np.float32)
    V = np.concatenate([v, np.zeros(pad, np.float32)]).reshape(rows, w).astype(np.float32)
    o = cv2.remap(T, U, V, cv2.INTER_LINEAR, borderMode=border)
    o = o.reshape(rows * w, *T.shape[2:])[:n]
    return o.reshape(*shp, *T.shape[2:])


def ripples(x, y, t, footprint):
    """The drawn surface's normal at plane points (x, y) at time t: slopes (sx, sy) and a height term."""
    sx = np.zeros_like(x, np.float32)
    sy = np.zeros_like(x, np.float32)
    hh = np.zeros_like(x, np.float32)
    for R, (hg, gx, gy) in zip(RIPPLES, TILES):
        n = hg.shape[0]
        u = ((x - R["dir"][0] * R["v"] * t) / R["tile"] * n).astype(np.float32)
        v = ((y - R["dir"][1] * R["v"] * t) / R["tile"] * n).astype(np.float32)
        u, v = np.mod(u, n), np.mod(v, n)
        wgt = (1.0 / (1.0 + (footprint / R["feat"]) ** 2)).astype(np.float32)
        smp = lambda T: remap(T, u, v, cv2.BORDER_WRAP)  # noqa: E731
        sx += R["a"] * wgt * smp(gx)
        sy += R["a"] * wgt * smp(gy)
        hh += wgt * smp(hg) / len(RIPPLES)
    return sx, sy, hh


def schlick(cos):
    f0 = ((IOR - 1) / (IOR + 1)) ** 2
    return f0 + (1 - f0) * np.clip(1 - cos, 0, 1) ** 5


def ss(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def down2(a):
    return cv2.resize(a, (a.shape[1] // 2, a.shape[0] // 2), interpolation=cv2.INTER_AREA)


# ---------------------------------------------------------------- the passes, loaded once

class Scene:
    def __init__(self, rdir, v5dir, animdir):
        self.animdir = animdir
        st = C.read(f"{rdir}/static2x.exr")
        self.plate2 = C.over(st, np.broadcast_to(DAY, (H2, W2, 3))).astype(np.float32)
        p = C.read(f"{rdir}/pos2x.exr")
        self.surf2 = p[..., 3] > 0.5
        self.z2 = np.where(self.surf2, p[..., 0], 1e4).astype(np.float32)
        self.d2 = np.where(self.surf2, p[..., 1], 1e6).astype(np.float32)
        self.rays2 = C.rays(VIEW, W2, H2).astype(np.float32)
        self.plate2_down = down2(self.plate2)
        A, B = C.read(f"{v5dir}/matte_A.exr")[..., 3], C.read(f"{v5dir}/matte_B.exr")[..., 3]
        st1 = C.read(f"{v5dir}/static.exr")
        self.base1 = C.over(st1, np.broadcast_to(DAY, (H, W, 3))).astype(np.float32)   # v5's own plate (1080p)
        self.M = np.where(B > 1e-3, np.clip(A / np.maximum(B, 1e-6), 0, 1), 1 - st1[..., 3])[..., None]
        # the screen-space reflection's grid: 960x540, each cell's nearest surface among its 4x4 samples
        q = 4
        d4 = self.d2.reshape(H2 // q, q, W2 // q, q).transpose(0, 2, 1, 3).reshape(H2 // q, W2 // q, q * q)
        z4 = self.z2.reshape(H2 // q, q, W2 // q, q).transpose(0, 2, 1, 3).reshape(H2 // q, W2 // q, q * q)
        k = d4.argmin(-1)
        self.dq = np.take_along_axis(d4, k[..., None], -1)[..., 0]
        self.zq = np.take_along_axis(z4, k[..., None], -1)[..., 0]
        self.raysq = C.rays(VIEW, W2 // q, H2 // q).astype(np.float32)

    # -- one frame
    def colour1(self, k_anim):
        """The picture at 1080p without water: v5's plate and the moving wires and birds (as v5's frames)."""
        an = C.read(f"{self.animdir}/anim/anim_{k_anim:04d}.exr") * self.M
        return C.over(an, self.base1).astype(np.float32), an

    def above1(self, h, t, src1):
        """The 1080p picture (no moving parts) with the water from above: v5's plate plus the water's difference."""
        # the few pixels already under the starting level (far ground seen through gaps, under 9.0 m) take the water
        # over the first WATER_IN s, so frame 0 is v5's picture exactly (the cut from under-the-crossing)
        k = float(ss(t / WATER_IN))
        return np.maximum(self.base1 + k * (down2(self.above(h, t, src1)) - self.plate2_down), 0)

    def reflection(self, h, t, src1):
        """Screen-space reflection off the plane at h, at 960x540, of the picture src1 (1080p), for rays going down."""
        hq, wq = self.dq.shape
        d = self.raysq
        dz = d[..., 2]
        ok = dz < -1e-4
        tp = np.where(ok, (h - EYE[2]) / np.where(ok, dz, -1), 0)
        P = EYE + tp[..., None] * d
        fp = tp * (36.0 / VIEW["lens"] / wq) / np.maximum(-dz, 0.02)
        sx, sy, _ = ripples(P[..., 0], P[..., 1], t, fp)
        n = np.stack([-sx, -sy, np.ones_like(sx)], -1)
        n /= np.linalg.norm(n, axis=-1, keepdims=True)
        r = d - 2 * (d * n).sum(-1, keepdims=True) * n
        r[..., 2] = np.maximum(r[..., 2], 0.002)
        r /= np.linalg.norm(r, axis=-1, keepdims=True)
        src = cv2.resize(src1, (wq, hq), interpolation=cv2.INTER_AREA)
        out = np.broadcast_to(DAY, (hq, wq, 3)).copy()
        idx = np.flatnonzero(ok)
        Pf, rf = P.reshape(-1, 3)[idx], r.reshape(-1, 3)[idx]
        s = 0.03
        while idx.size and s < 4000:
            ds = s * 0.3
            Q = Pf + s * rf
            i, j, fwd = project(Q, wq, hq)
            ii, jj = np.rint(i).astype(int), np.rint(j).astype(int)
            out_scr = (ii < 0) | (ii >= wq) | (jj < 0) | (jj >= hq) | (fwd <= 0.05)
            iic, jjc = np.clip(ii, 0, wq - 1), np.clip(jj, 0, hq - 1)
            dist = np.linalg.norm(Q - EYE, axis=-1)
            db = self.dq[jjc, iic]
            hit = (~out_scr) & (dist >= db) & (dist - db < np.maximum(0.35, 1.5 * ds)) & (self.zq[jjc, iic] >= h - 0.02)
            if hit.any():
                out.reshape(-1, 3)[idx[hit]] = src[jjc[hit], iic[hit]]
            keep = ~(hit | out_scr)
            idx, Pf, rf = idx[keep], Pf[keep], rf[keep]
            s *= 1.3
        out = cv2.GaussianBlur(out, (0, 0), 0.8)
        F = schlick(np.clip(-(d * n).sum(-1), 0, 1))
        return out, F.astype(np.float32)

    def above(self, h, t, src1):
        """The 2x picture with the water drawn from above at level h (eye over h)."""
        d = self.rays2
        dz = d[..., 2]
        water = self.surf2 & (self.z2 < h) & (dz < 0)
        out = self.plate2.copy()
        if not water.any():
            return out
        refl, F = self.reflection(h, t, src1)
        refl2 = cv2.resize(refl, (W2, H2), interpolation=cv2.INTER_LINEAR)
        F2 = cv2.resize(F, (W2, H2), interpolation=cv2.INTER_LINEAR)
        ys, xs = np.nonzero(water)
        dw = d[ys, xs]
        tp = (h - EYE[2]) / dw[:, 2]
        T = np.exp(-np.maximum(self.d2[ys, xs] - tp, 0) / SHALLOW_M)[:, None]
        body = self.plate2[ys, xs] * T + BODY * (1 - T)
        f = (FRESNEL_MIX * F2[ys, xs])[:, None]
        out[ys, xs] = body * (1 - f) + GLOSS_TINT * refl2[ys, xs] * f
        return out

    def below(self, h, t, src1):
        """The 2x picture from under the surface at level h (eye under h): a drawn convention (see the docstring)."""
        d = self.rays2
        dz = d[..., 2]
        de = h - EYE[2]
        el = ss((dz + 0.3) / 0.9)[..., None]
        murk = (MURK_DOWN * (1 - el) + MURK_UP * el) * math.exp(-de / 5.0)
        out = np.empty((H2, W2, 3), np.float32)
        under = self.surf2 & (self.z2 < h)
        # under the surface: the scene's own surfaces, darker with depth, through murk along their distance
        ys, xs = np.nonzero(under)
        T = np.exp(-self.d2[ys, xs][:, None] / ABSORB_SILT_M)
        z = self.z2[ys, xs]
        lit = np.exp(-(h - z) / DEPTH_DIM_M)[:, None]
        g = (SILT_MAX * (1 - np.exp(-np.maximum(t - submerged_at(z), 0) / SILT_TAU_S)))[:, None]
        c = self.plate2[ys, xs]
        lum = (c @ np.array([0.2126, 0.7152, 0.0722], np.float32))[:, None]
        grey = lum / float(SILT_TINT @ np.array([0.2126, 0.7152, 0.0722])) * SILT_TINT
        c = (c * (1 - g) + grey * g) * (1 - 0.5 * g)          # dulled, greyed toward silt, darkened
        out[ys, xs] = c * lit * T + murk[ys, xs] * (1 - T)
        # through the surface: the picture above, wavering, along the ray's path in the water
        thr = ~under & (dz > 1e-4)
        ys, xs = np.nonzero(thr)
        dw = d[ys, xs]
        tp = de / dw[:, 2]
        P = EYE + tp[:, None] * dw
        fp = tp * (36.0 / VIEW["lens"] / W2) / dw[:, 2]
        sx, sy, hh = ripples(P[:, 0].astype(np.float32), P[:, 1].astype(np.float32), t, fp.astype(np.float32))
        Rm = rotation()
        right, up = Rm[:, 0], Rm[:, 1]
        a = 2 * WAVER_PX / 0.08                       # px (at 2x) per unit slope
        u = xs + a * (sx * right[0] + sy * right[1])
        v = ys - a * (sx * up[0] + sy * up[1]) - a * 0.5 * (sx * right[1] - sy * right[0])
        src2 = cv2.resize(cv2.GaussianBlur(src1, (0, 0), 1.2), (W2, H2), interpolation=cv2.INTER_LINEAR)
        col = remap(src2, u.astype(np.float32), v.astype(np.float32), cv2.BORDER_REFLECT)
        T = np.exp(-tp[:, None] / ABSORB_UP_M)
        tau = 1 - schlick(np.clip(dw[:, 2], 0, 1))[:, None]
        out[ys, xs] = col * (1 + MOTTLE * hh[:, None]) * tau * T + murk[ys, xs] * (1 - T)
        rest = ~under & ~thr
        out[rest] = murk[rest]
        return out

    def frame(self, k):
        t = k / FPS
        h = level_at(t)
        src, an = self.colour1(ANIM0 + k)
        tc = crossing_s()
        p = (t - (tc - WIPE_S / 2)) / WIPE_S
        ez = float(EYE[2])
        if p <= 0:                                      # the eye over the water
            out1 = C.over(an, self.above1(min(h, ez - 1e-3), t, src))
        else:
            und = down2(self.below(max(h, ez + 1e-3), t, src))
            if p >= 1:
                out1 = und
            else:                                       # the waterline sweeping up over the lens (drawn)
                ab = C.over(an, self.above1(min(h, ez - 1e-3), t, src))
                x = np.arange(W)
                yb = H * (1 - float(ss(p))) * 1.08 - 0.04 * H + 10 * np.sin(x / 150.0 + t * 7) + 5 * np.sin(x / 41.0 - t * 11)
                yy = np.arange(H)[:, None]
                m = ss((yy - yb[None]) / 6.0 + 0.5)[..., None].astype(np.float32)   # 1 under the waterline
                out1 = ab * (1 - m) + und * m
                band = np.exp(-((yy - yb[None]) / 2.5) ** 2)[..., None].astype(np.float32)
                out1 = out1 * (1 - 0.55 * band) + 0.02 * band
        return C.to8(out1, seed=ANIM0 + k), h          # the dither's seed runs on from v5's (seed = frame)


def main():
    a = [x for x in sys.argv[1:]]
    every = 1
    if "--every" in a:
        i = a.index("--every"); every = int(a[i + 1]); del a[i:i + 2]
    if a[0] == "timeline":
        print(json.dumps(timeline(), indent=1))
    elif a[0] == "frame":
        sc = Scene(a[1], a[2], a[3])
        t0 = time.time()
        img, h = sc.frame(int(a[4]))
        Image.fromarray(img).save(a[5])
        print("frame", a[4], "level", round(h, 3), "s", round(time.time() - t0, 1))
    elif a[0] == "frames":
        out = a[4]
        os.makedirs(out, exist_ok=True)
        A, B = (int(v) for v in a[5].split(":")) if len(a) > 5 else (0, N)
        todo = [k for k in range(A, B, every) if not os.path.exists(f"{out}/f_{k:04d}.png")]
        print("todo", len(todo), flush=True)
        if not todo:
            return
        sc = Scene(a[1], a[2], a[3])
        for k in todo:
            if os.path.exists(f"{out}/f_{k:04d}.png"):      # another worker took it
                continue
            t0 = time.time()
            img, h = sc.frame(k)
            tmp = f"{out}/.f_{k:04d}.{os.getpid()}.png"
            Image.fromarray(img).save(tmp, compress_level=1)
            os.replace(tmp, f"{out}/f_{k:04d}.png")         # whole files only: a killed worker leaves no half frame
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


if __name__ == "__main__":
    main()
