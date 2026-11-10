"""The v6 shot `drowning` (decided with the user, 6 November 2026), drawn frame by frame from passes rendered once:
v5's view f by day held 15 s while the proposed level (12.7 m Baltic = 13.1 m in the scene, Vyshnevskyi & Shevchuk
2024, p. 286) rises through the scene's own ground, past the plants and the lens, months compressed into seconds.

    python -I composite_v6.py frames <render_dir> <v5_render_dir> <out_dir> [A:B] [--every N]   PNG per frame, skips
                                                                                               frames on disk
    python -I composite_v6.py frame  <render_dir> <v5_render_dir> <K> <out.png>
    python -I composite_v6.py video  <frames_dir> <audio.wav> <out.mp4>
    python -I composite_v6.py timeline                                                       the level by frame (JSON)

Passes (still_v6.py, 3840x2160): static2x.exr (v5's static picture), pos2x.exr (each pixel's surface: world height,
distance from the eye; one exact sample). From v5's render dir (1920x1080): anim/anim_KKKK.exr (the lit wires' flow
and the far birds), matte_A/B.exr (how much of each wire pixel is in view), contour.exr (the reprise's blue line).

The water is a flat surface at height h(t), drawn, not simulated:
- From above (the eye over h): a pixel is water where its surface lies below h (a ray going down meets the points
  above h before it crosses the plane), so the water comes first where the visible ground is lowest and climbs the
  plants' stems, the shortest going under first; the plants stay as modelled. Its look is the film's water material
  (the scene's own: an unlit body colour, linear 0.0176, 0.0252, 0.0176, under a glossy reflection of tint 0.8 mixed
  by half its Fresnel at IOR 1.333, rippled), with the reflection traced in screen space through the picture's own
  surfaces (a reflected ray from the water marched against the pass's distances; off the picture: the overcast sky),
  drawn ripples drifting south-west with the current, and very shallow water letting the ground show through.
- The lens crossing: as the level passes the eye, the waterline sweeps up across the frame in half a second, as it
  would over a lens port (a drawn meniscus).
- From below (the eye under h): what lies under the surface is seen through murk (absorbed by its distance, darker
  with depth); what stands above it (the tower, the lit wires, the crowns, the sky) through the surface, wavering
  with the drawn ripples and absorbed along the ray's path in the water. A DRAWN CONVENTION: Snell's window is not
  drawn (from 2.25 m down a real eye looking 14 degrees up would see the surface as a mirror almost everywhere but
  overhead) and the water is drawn clearer than the reservoir's, so the tower can be seen.
The blue line of the reprise is held from the start (so the shot can follow the reprise) and fades as the water
reaches it. The label as v5's, bottom left.
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
ANIM0 = 450                                          # the 30 s shot's moving pass, frames 450-899 (far birds only)
EYE = np.array([4355.0, 6870.0, 10.854730606079102])  # the static log's camera (ground 9.255 m + 1.6 m)
VIEW = dict(lens=18.0, pitch=14.0, heading_deg=22.0)

LEVEL_BALTIC, BALTIC_TO_EGM2008 = 12.7, 0.4
LEVEL = LEVEL_BALTIC + BALTIC_TO_EGM2008             # 13.1 m, scene z (FABDEM's metres above EGM2008)
H0 = 9.0                                             # where the drawn rise starts: just under the lowest ground the
                                                     # view shows (the lane's ground, 9.25 m at the camera; the pass:
                                                     # 0.2% of pixels under 9.25 m, none under 9.0 but a few far off)
RISE = (1.0, 11.0)                                   # s: the rise, eased (slow start, steady, slowing to the level)
EASE_IN, EASE_OUT = 0.2, 0.4                         # shares of the rise spent speeding up and slowing down
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
ABSORB_M = np.array([3.5, 5.9, 4.9], np.float32)
MURK_UP = C.lin((110, 122, 92)).astype(np.float32)
MURK_DOWN = BODY
DEPTH_DIM_M = 3.5                                    # light falls off with depth below the surface (drawn)
MOTTLE = 0.16                                        # the surface's underside brighter and darker with its ripples
WAVER_PX = 9.0                                       # the through-surface picture's sway at 1080p (drawn)
LINE_FADE = (12.4, 13.0)                             # the blue line fades as the water nears it (scene m)
LABEL = ("PROPOSED LEVEL · 12.7 M · VYSHNEVSKYI & SHEVCHUK 2024 · REACHED OVER MONTHS · "
         "THE BED'S HEIGHTS INFERRED · DRAWN")


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
    def __init__(self, rdir, v5dir):
        self.v5 = v5dir
        st = C.read(f"{rdir}/static2x.exr")
        self.plate2 = C.over(st, np.broadcast_to(DAY, (H2, W2, 3))).astype(np.float32)
        p = C.read(f"{rdir}/pos2x.exr")
        self.surf2 = p[..., 3] > 0.5
        self.z2 = np.where(self.surf2, p[..., 0], 1e4).astype(np.float32)
        self.d2 = np.where(self.surf2, p[..., 1], 1e6).astype(np.float32)
        self.rays2 = C.rays(VIEW, W2, H2).astype(np.float32)
        self.base1 = down2(self.plate2)
        A, B = C.read(f"{v5dir}/matte_A.exr")[..., 3], C.read(f"{v5dir}/matte_B.exr")[..., 3]
        st1 = C.read(f"{v5dir}/static.exr")
        self.M = np.where(B > 1e-3, np.clip(A / np.maximum(B, 1e-6), 0, 1), 1 - st1[..., 3])[..., None]
        L = C.read(f"{v5dir}/contour.exr")
        self.line = np.clip(L[..., 0:1], 0, 1)
        self.edge = cv2.dilate(self.line[..., 0], np.ones((3, 3), np.uint8))[..., None]
        self.lab_rgb, self.lab_a, self.lab_box = self._label()
        # the screen-space reflection's grid: 960x540, each cell's nearest surface among its 4x4 samples
        q = 4
        d4 = self.d2.reshape(H2 // q, q, W2 // q, q).transpose(0, 2, 1, 3).reshape(H2 // q, W2 // q, q * q)
        z4 = self.z2.reshape(H2 // q, q, W2 // q, q).transpose(0, 2, 1, 3).reshape(H2 // q, W2 // q, q * q)
        k = d4.argmin(-1)
        self.dq = np.take_along_axis(d4, k[..., None], -1)[..., 0]
        self.zq = np.take_along_axis(z4, k[..., None], -1)[..., 0]
        self.raysq = C.rays(VIEW, W2 // q, H2 // q).astype(np.float32)

    def _label(self):
        C5.LABEL = LABEL
        return C5.label_layer()

    # -- one frame
    def colour1(self, k_anim, with_line):
        """The picture at 1080p without water (the static plate, the line, the moving wires)."""
        base = self.base1
        if with_line > 0:
            e = self.edge * with_line
            base = base * (1 - e) + C5.EDGE_RGB * e
            m = self.line * with_line
            base = base * (1 - m) + C5.LINE_RGB * m
        an = C.read(f"{self.v5}/anim/anim_{k_anim:04d}.exr") * self.M
        return C.over(an, base).astype(np.float32), an

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
        murk = (MURK_DOWN * (1 - el) + MURK_UP * el) * math.exp(-de / 6.0)
        out = np.empty((H2, W2, 3), np.float32)
        under = self.surf2 & (self.z2 < h)
        # under the surface: the scene's own surfaces, darker with depth, through murk along their distance
        ys, xs = np.nonzero(under)
        T = np.exp(-self.d2[ys, xs][:, None] / ABSORB_M)
        lit = np.exp(-(h - self.z2[ys, xs]) / DEPTH_DIM_M)[:, None]
        out[ys, xs] = self.plate2[ys, xs] * lit * T + murk[ys, xs] * (1 - T)
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
        T = np.exp(-tp[:, None] / ABSORB_M)
        tau = 1 - schlick(np.clip(dw[:, 2], 0, 1))[:, None]
        out[ys, xs] = col * (1 + MOTTLE * hh[:, None]) * tau * T + murk[ys, xs] * (1 - T)
        rest = ~under & ~thr
        out[rest] = murk[rest]
        return out

    def frame(self, k):
        t = k / FPS
        h = level_at(t)
        lf = 1 - float(ss((h - LINE_FADE[0]) / (LINE_FADE[1] - LINE_FADE[0])))
        src_noline, an = self.colour1(ANIM0 + k, 0.0)
        tc = crossing_s()
        p = (t - (tc - WIPE_S / 2)) / WIPE_S
        ez = float(EYE[2])
        if p <= 0:                                      # the eye over the water
            out1 = down2(self.above(min(h, ez - 1e-3), t, src_noline))
            out1 = self._line(out1, lf)
            out1 = C.over(an, out1)
        else:
            src_line, _ = self.colour1(ANIM0 + k, lf)
            und = down2(self.below(max(h, ez + 1e-3), t, src_line))
            if p >= 1:
                out1 = und
            else:                                       # the waterline sweeping up over the lens (drawn)
                ab = C.over(an, self._line(down2(self.above(min(h, ez - 1e-3), t, src_noline)), lf))
                x = np.arange(W)
                yb = H * (1 - float(ss(p))) * 1.08 - 0.04 * H + 10 * np.sin(x / 150.0 + t * 7) + 5 * np.sin(x / 41.0 - t * 11)
                yy = np.arange(H)[:, None]
                m = ss((yy - yb[None]) / 6.0 + 0.5)[..., None].astype(np.float32)   # 1 under the waterline
                out1 = ab * (1 - m) + und * m
                band = np.exp(-((yy - yb[None]) / 2.5) ** 2)[..., None].astype(np.float32)
                out1 = out1 * (1 - 0.55 * band) + 0.02 * band
        img = C.to8(out1, seed=k)
        a = self.lab_a
        img = np.clip(img.astype(np.float32) * (1 - a) + self.lab_rgb * 255 * a + 0.5, 0, 255).astype(np.uint8)
        return img, h

    def _line(self, base, f):
        if f <= 0:
            return base
        e = self.edge * f
        base = base * (1 - e) + C5.EDGE_RGB * e
        m = self.line * f
        return base * (1 - m) + C5.LINE_RGB * m


def main():
    a = [x for x in sys.argv[1:]]
    every = 1
    if "--every" in a:
        i = a.index("--every"); every = int(a[i + 1]); del a[i:i + 2]
    if a[0] == "timeline":
        print(json.dumps(timeline(), indent=1))
    elif a[0] == "frame":
        sc = Scene(a[1], a[2])
        t0 = time.time()
        img, h = sc.frame(int(a[3]))
        Image.fromarray(img).save(a[4])
        print("frame", a[3], "level", round(h, 3), "s", round(time.time() - t0, 1))
    elif a[0] == "frames":
        out = a[3]
        os.makedirs(out, exist_ok=True)
        A, B = (int(v) for v in a[4].split(":")) if len(a) > 4 else (0, N)
        todo = [k for k in range(A, B, every) if not os.path.exists(f"{out}/f_{k:04d}.png")]
        print("todo", len(todo), flush=True)
        if not todo:
            return
        sc = Scene(a[1], a[2])
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
