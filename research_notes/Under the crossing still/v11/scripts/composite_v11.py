"""The v11 shot `drowning` (the user, 9 November 2026, on v10's water round the branches: "its far too straight these
lines. wouldnt they be more wavy/disrupted due to the water waves? also, they seem to continue too far. additionally,
the foam from the tree branches sticking out of the water in the distance is too white and seems strange, perhaps
adjust the coloring of them. also could you improve the water surface so it reads more like water from under than
just textures on a treadmill"). v10's shot otherwise: its passes and crossings (the stray branch gone, no birds), the
level 13.1 m from the first frame, the eye under it, v9's murk, v7's moving pass (frames 900-1349), v9's sound.

All of it DRAWN, seen from under the surface:
- THE SURFACE is one wave field that evolves (`Waves`): a sum of WAVES_N small wind waves of a slow reservoir
  (wavelengths LAMBDA_M), travelling within about 50 degrees of v7's CURRENT (toward the south-west), each at its own
  speed by the dispersion of capillary-gravity waves (omega^2 = g k + (sigma/rho) k^3), so the pattern changes shape as
  it moves instead of sliding as one (v7's two tiles drifted at constant speed: "textures on a treadmill"). Rougher and
  calmer patches (cat's paws) drift slowly over it (the short waves' amplitude modulated by a coarse drifting field).
  Its RMS slope matches v7's (v9's calm surface). From the one field: the picture seen through the surface sways
  (v9's WAVER_PX per slope), the underside's brightness (soft brighter cells where the surface's curvature gathers the
  light: no hard caustics) and the wakes' wobble. Components shorter than a few pixels' footprint are filtered out
  (as v7 filters its tiles), so nothing shimmers. Evaluated on the 1080p grid, then resized to the 2x grid.
- THE WAKES are short (WAKE: about a quarter of v10's length) and fade fast. They bend and break: each wake's centre
  line meanders with a slowly evolving flow field and wobbles with the surface's slope, and its foam is cut into
  patches by an evolving noise whose threshold rises downstream, so it splits into flecks and dissolves.
- THE COLLAR round each stem is irregular and boiling, half again v10's width: its width varies round the stem and in
  time. The meniscus is v10's.
- THE FOAM is not white: seen from below it is a soft, pale grey-green (FOAM_TINT), about as bright as the water round
  it near the eye (FOAM_NEAR) and no brighter far off. It thins with the crossing's distance (FOAM_FADE_M), and like
  everything seen through the surface it is absorbed along the path through the water.
- SNELL'S WINDOW: at this view almost all of the surface seen lies outside it, so in reality it would mirror the murk
  and the tower would not show. The drawn convention is kept, so the towers and the lit wires stay readable (the
  user wants them seen). A hint of the mirror toward the horizon only: the view through the surface darkened toward
  the murk at grazing angles (MIRROR).

    python -I composite_v11.py frames <v10_render_dir> <v5_render_dir> <v8_render_dir> <anim_dir> <out_dir> [A:B]
    python -I composite_v11.py frame  <v10_render_dir> <v5_render_dir> <v8_render_dir> <anim_dir> <K,K..> <out_K.png>
    python -I composite_v11.py video  <frames_dir> <audio.wav> <out.mp4>
    python -I composite_v11.py sheet  <frames_dir> <out.png> [cols] [every_s]
"""
import math
import os
import sys
import time

os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "1"
import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "v10", "scripts")))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "v9", "scripts")))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "v7", "scripts")))
import composite_v7 as V7  # noqa: E402
import composite_v9 as C9  # noqa: E402
import composite_v10 as C10  # noqa: E402
C = V7.C

W, H, W2, H2 = V7.W, V7.H, V7.W2, V7.H2
FPS, N = C9.FPS, C9.N
DAY, LEVEL, EYE = V7.DAY, V7.LEVEL, V7.EYE
STATEMENT = C10.STATEMENT
CUR, CROSS, FLOW = C10.CUR, C10.CROSS, C10.FLOW

# the surface
G, SIGMA_RHO = 9.81, 7.3e-5                 # gravity, water's surface tension / density (m^3/s^2)
WAVES_N = 40
LAMBDA_M = (0.06, 0.9)                      # wavelengths drawn (log-spaced); the slope peaks near LAMBDA_PEAK
LAMBDA_PEAK = 0.18                          # (phase speed about 0.53 m/s; v7's tiles drifted at 0.3-0.42)
SPREAD_DEG = 50                             # directions about the current's (normal, this sd)
SLOPE_RMS = 0.05                            # per axis, as v7's two tiles (0.05 and v9's 0.015)
PAWS = dict(scale_m=14.0, drift=0.35, lo=0.55, hi=1.45, short_m=0.35)   # rougher/calmer patches on the short waves
FOCUS = 0.07                                # the underside's brighter cells (v7's MOTTLE 0.05 on the height)
FOOT_K = 2.2                                # a wave of length L is filtered by exp(-(FOOT_K fp / L)^2), fp 1080p's
# the water round the stems
WAKE = dict(len_m=(0.4, 6.0), spread=0.11, width_r=1.6)   # v10 (1.6, 26.0), 0.09, 1.8
WAKE_ALPHA = 0.36                                         # v10 0.5
MEANDER = dict(scale_m=1.1, amp_r=0.6, amp_u=0.22, speed=0.12, wave_m=0.5)
FOAM_TINT = np.array(C.lin((178, 184, 174)), np.float32)
FOAM_TINT = FOAM_TINT / float(FOAM_TINT @ np.array([0.2126, 0.7152, 0.0722], np.float32))
FOAM_NEAR, FOAM_FAR = 1.30, 0.96            # the foam's brightness against the water round it, near and far
FOAM_FADE_M = (6.0, 40.0)                   # thins from 6 m to 40 m (to FOAM_FADE_MIN)
FOAM_FADE_MIN = 0.25
MIRROR = dict(dz=(0.24, 0.05), max=0.3)     # grazing rays: the view through darkened toward the murk


def ss(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def omega(k):
    return np.sqrt(G * k + SIGMA_RHO * k ** 3)


class Waves:
    """The evolving surface: height, slopes and curvature at plane points (x, y), time t, footprint fp (m a pixel)."""

    def __init__(self, seed=11):
        rng = np.random.default_rng(seed)
        lam = np.exp(np.linspace(math.log(LAMBDA_M[0]), math.log(LAMBDA_M[1]), WAVES_N))
        lam *= np.exp(rng.uniform(-0.08, 0.08, WAVES_N))
        th0 = math.atan2(CUR[1], CUR[0])
        th = th0 + np.radians(rng.normal(0, SPREAD_DEG, WAVES_N))
        self.k = 2 * np.pi / lam
        self.lam = lam
        self.kx, self.ky = self.k * np.cos(th), self.k * np.sin(th)
        self.w = omega(self.k)
        self.ph = rng.uniform(0, 2 * np.pi, WAVES_N)
        s = np.exp(-((np.log(lam) - math.log(LAMBDA_PEAK)) / 1.0) ** 2)      # slope spectrum
        s *= SLOPE_RMS / math.sqrt((s ** 2).sum() / 4)
        self.s = s
        self.a = s / self.k                                                  # amplitudes (m)
        self.h_rms = math.sqrt((self.a ** 2).sum() / 2)
        self.c_rms = math.sqrt(((self.a * self.k ** 2) ** 2).sum() / 2)
        self.short = lam < PAWS["short_m"]
        self.paw = V7.tile_noise(53)[0]

    def paws(self, x, y, t):
        n = self.paw.shape[0]
        sc = PAWS["scale_m"]
        u = (x - CUR[0] * PAWS["drift"] * t) / sc * n
        v = (y - CUR[1] * PAWS["drift"] * t) / sc * n
        p = V7.remap(self.paw, np.mod(u, n).astype(np.float32), np.mod(v, n).astype(np.float32), cv2.BORDER_WRAP)
        u2 = (x + CROSS[0] * 0.21 * t) / (sc * 1.7) * n
        v2 = (y + CROSS[1] * 0.21 * t) / (sc * 1.7) * n
        p2 = V7.remap(self.paw, np.mod(u2 + 97, n).astype(np.float32), np.mod(v2 + 31, n).astype(np.float32), cv2.BORDER_WRAP)
        q = ss(0.5 + 0.35 * (p + 0.7 * p2))
        return (PAWS["lo"] + (PAWS["hi"] - PAWS["lo"]) * q).astype(np.float32)

    def field(self, x, y, t, fp):
        sx = np.zeros_like(x, np.float32)
        sy = np.zeros_like(x, np.float32)
        hh = np.zeros_like(x, np.float32)
        cv = np.zeros_like(x, np.float32)
        paw = self.paws(x, y, t)
        for i in range(WAVES_N):
            wgt = np.exp(-(FOOT_K * fp / self.lam[i]) ** 2).astype(np.float32)
            if self.short[i]:
                wgt = wgt * paw
            psi = (self.kx[i] * x + self.ky[i] * y - self.w[i] * t + self.ph[i]).astype(np.float32)
            sn, cs = np.sin(psi), np.cos(psi)
            sx -= (self.a[i] * self.kx[i] * wgt) * sn
            sy -= (self.a[i] * self.ky[i] * wgt) * sn
            hh += (self.a[i] * wgt / self.h_rms) * cs
            cv += (self.a[i] * self.k[i] ** 2 * wgt / self.c_rms) * cs   # minus the Laplacian: crests positive
        return sx, sy, hh, cv


WAVES = Waves()


class Scene11(C10.Scene10):
    def __init__(self, rdir, v5dir, v8dir, animdir):
        C10.WAKE = dict(len_m=WAKE["len_m"], spread=WAKE["spread"] * 2.2, width_r=WAKE["width_r"] * 1.6)  # reach, with
        super().__init__(rdir, v5dir, v8dir, animdir)                                                  # meander room
        # the 1080p grid of the view up through the surface (the wave field is evaluated there)
        d1 = C.rays(V7.VIEW, W, H).astype(np.float32)
        dz1 = d1[..., 2]
        self.g_ok = dz1 > 1e-4
        gy, gx = np.nonzero(self.g_ok)
        tp1 = (LEVEL - EYE[2]) / d1[gy, gx, 2]
        P1 = EYE + tp1[:, None] * d1[gy, gx]
        self.g_idx = (gy, gx)
        self.g_x, self.g_y = P1[:, 0].astype(np.float32), P1[:, 1].astype(np.float32)
        self.g_fp = (tp1 * (36.0 / V7.VIEW["lens"] / W) / d1[gy, gx, 2]).astype(np.float32)
        self.dzt = self.dw[:, 2]
        # per crossing: its distance from the eye (the foam's fade) and its ids' surface points
        for c in self.cross:
            q = self.Pt[c["ids"]]
            c["dist"] = float(np.hypot(*(q.mean(0) - EYE[:2])))
            c["L"] = WAKE["len_m"][0] + WAKE["len_m"][1] * c["r"]

    def surface(self, t):
        """The wave field at the thr pixels (2x): slopes, height, curvature."""
        sx, sy, hh, cv = WAVES.field(self.g_x, self.g_y, t, self.g_fp)
        out = []
        for a in (sx, sy, hh, cv):
            im = np.zeros((H, W), np.float32)
            im[self.g_idx] = a
            im2 = cv2.resize(im, (W2, H2), interpolation=cv2.INTER_LINEAR)
            out.append(im2[self.ty, self.tx])
        return out

    def disturbance(self, t, wsx, wsy):
        n = len(self.ty)
        A = np.zeros(n, np.float32)
        K = np.ones(n, np.float32)
        Gn = np.zeros(n, np.float32)                     # how near (0..1) the foam at each pixel is: its brightness
        sx = np.zeros(n, np.float32)
        sy = np.zeros(n, np.float32)
        h1, g1x, g1y, h2 = C10.NT
        smp = C10._sample
        for c in self.cross:
            ids, u, v, r = c["ids"], c["u"], c["v"], c["r"]
            fp = self.fpt[ids]
            Px, Py = self.Pt[ids, 0], self.Pt[ids, 1]
            near = float(np.clip(1 - (c["dist"] - FOAM_FADE_M[0]) / (FOAM_FADE_M[1] - FOAM_FADE_M[0]), 0, 1))
            fade = FOAM_FADE_MIN + (1 - FOAM_FADE_MIN) * near
            Lw = c["L"]
            uu = np.maximum(u, 0)
            # the wake's centre line meanders with a slowly evolving flow field and wobbles with the surface's slope
            ms = MEANDER["scale_m"]
            m1 = smp(g1x, ((Px - CUR[0] * MEANDER["speed"] * t) / ms / 9 + c["off"][0]).astype(np.float32),
                     ((Py - CUR[1] * MEANDER["speed"] * t) / ms / 9 + c["off"][1]).astype(np.float32))
            m2 = smp(g1y, ((Px + CROSS[0] * 0.07 * t) / (ms * 1.6) / 9 + c["off"][1]).astype(np.float32),
                     ((Py + CROSS[1] * 0.07 * t) / (ms * 1.6) / 9 + c["off"][0]).astype(np.float32))
            grow = ss(uu / max(0.35 * Lw, 1e-3))
            amp = (MEANDER["amp_r"] * r + MEANDER["amp_u"] * uu) * grow
            ws = wsx[ids] * CROSS[0] + wsy[ids] * CROSS[1]
            vv = v - amp * (0.7 * m1 + 0.5 * m2) - MEANDER["wave_m"] * ws * grow
            uw = u - 0.4 * amp * m2
            sig = WAKE["width_r"] * r + WAKE["spread"] * np.maximum(uw, 0)
            env = np.exp(-(vv / np.maximum(sig, fp)) ** 2) * np.exp(-(np.maximum(uw, 0) / Lw) ** 1.5) * \
                ss(u / (2 * r + 0.02)) * (rho_out := (np.sqrt(u * u + v * v) - r > -0.25 * fp))
            # the foam cut into patches by an evolving noise whose threshold rises downstream: flecks, then nothing
            s1 = (uw - FLOW * t) / (0.6 + 5 * r)               # patches about as long as wide: flecks, not lines
            s2 = vv / (0.45 + 5 * r)
            f1 = smp(h1, (s1 + c["off"][0]).astype(np.float32), (s2 + c["off"][1]).astype(np.float32))
            f2 = smp(h2, (s1 * 2.1 + c["off"][1] + 0.05 * t).astype(np.float32),
                     (s2 * 2.1 + c["off"][0] - 0.04 * t).astype(np.float32))
            thr = -0.2 + 1.3 * np.clip(np.maximum(uw, 0) / Lw, 0, 1.5)
            fleck = ss((0.65 * f1 + 0.55 * f2 - thr) / 0.45)
            fsz = (0.45 + 5 * r) / 9
            mixf = np.clip(fp / fsz, 0, 1)
            fleck = fleck * (1 - mixf) + 0.25 * ss(1 - thr) * mixf
            wake = env * fleck
            # the collar: irregular round the stem and boiling
            rho = np.sqrt(u * u + v * v) - r
            ang = np.arctan2(v, u)
            wc = 1.5 * (C10.COLLAR["width_m"] + C10.COLLAR["width_r"] * r)
            wn = smp(h2, (ang / 6.2832 * 3 + c["off"][0] + 0.03 * t).astype(np.float32),
                     (np.full_like(ang, c["off"][1]) + 0.09 * t).astype(np.float32))
            wvar = wc * (0.55 + 0.75 * ss(0.5 + 0.5 * wn))
            wce = np.maximum(wvar, fp)
            cosu = -u / np.maximum(rho + r, 1e-4)
            side = (1 - C10.COLLAR["up"]) + C10.COLLAR["up"] * ss(0.5 + 0.5 * cosu)
            boil = smp(h2, (ang / 6.2832 + c["off"][0] + 0.02 * t).astype(np.float32),
                       ((rho / (3 * wc + 0.01)) * 0.25 + c["off"][1] - 0.05 * t).astype(np.float32))
            coll = np.exp(-(np.maximum(rho, 0) / wce) ** 1.6) * (wvar / wce) * side * ss(0.4 + 0.6 * boil) * rho_out
            # the meniscus (v10's)
            wm = C10.MENISCUS["width_m"]
            we = np.maximum(wm, fp)
            k = wm / we
            dark = np.exp(-(np.maximum(rho, 0) / we) ** 2) * k * rho_out
            bright = np.exp(-((rho - 1.6 * we) / we) ** 2) * k * rho_out
            K[ids] *= 1 - C10.MENISCUS["dark"] * dark
            a = np.maximum(C10.COLLAR["alpha"] * coll, WAKE_ALPHA * wake)
            a = np.maximum(a, C10.MENISCUS["bright"] * 0.7 * bright) * fade
            A[ids] = 1 - (1 - A[ids]) * (1 - a)
            Gn[ids] = np.maximum(Gn[ids], near * (a > 0.01))
            # the surface more disturbed in the wake and round the stem
            gu = smp(g1x, (s1 + c["off"][0]).astype(np.float32), (s2 + c["off"][1]).astype(np.float32))
            gv = smp(g1y, (s1 + c["off"][0]).astype(np.float32), (s2 + c["off"][1]).astype(np.float32))
            am = C10.WAKE_SLOPE * 0.8 * np.maximum(env, 0.6 * coll) / (1 + (fp / (0.3 * fsz)) ** 2)
            sx[ids] += am * (gu * CUR[0] + gv * CROSS[0])
            sy[ids] += am * (gu * CUR[1] + gv * CROSS[1])
        return np.clip(A, 0, 0.85), K, Gn, sx, sy

    def below(self, h, t, src1):
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
        LUM = np.array([0.2126, 0.7152, 0.0722], np.float32)
        lum = (c @ LUM)[:, None]
        grey = lum / float(V7.SILT_TINT @ LUM) * V7.SILT_TINT
        c = (c * (1 - g) + grey * g) * (1 - 0.5 * g)
        out[ys, xs] = c * lit * T + murk[ys, xs] * (1 - T)
        # through the surface: the evolving wave field
        ys, xs, dw, tp = self.ty, self.tx, self.dw, self.tp
        wsx, wsy, hh, cv = self.surface(t)
        A, K, Gn, dsx, dsy = self.disturbance(t, wsx, wsy)
        sx, sy = wsx + dsx, wsy + dsy
        Rm = V7.rotation()
        right, up = Rm[:, 0], Rm[:, 1]
        a = 2 * V7.WAVER_PX / 0.08
        u = xs + a * (sx * right[0] + sy * right[1])
        v = ys - a * (sx * up[0] + sy * up[1]) - a * 0.5 * (sx * right[1] - sy * right[0])
        src2 = cv2.resize(cv2.GaussianBlur(src1, (0, 0), C9.SRC_BLUR), (W2, H2), interpolation=cv2.INTER_LINEAR)
        col = V7.remap(src2, u.astype(np.float32), v.astype(np.float32), cv2.BORDER_REFLECT)
        col = col * K[:, None]
        tau = 1 - V7.schlick(np.clip(dw[:, 2], 0, 1))[:, None]
        focus = 1 + FOCUS * (np.tanh(0.9 * cv) + 0.25 * np.tanh(0.6 * hh))   # soft brighter cells
        col = col * focus[:, None] * tau
        # the foam: pale grey-green, about as bright as the water round it (a touch brighter near the eye)
        lumc = (col @ LUM)[:, None]
        fb = (FOAM_FAR + (FOAM_NEAR - FOAM_FAR) * Gn)[:, None]
        foam = FOAM_TINT * lumc * fb
        col = col * (1 - A[:, None]) + foam * A[:, None]
        # a hint of the mirror at grazing angles (Snell's window not drawn: see the docstring)
        wm = (MIRROR["max"] * ss((MIRROR["dz"][0] - self.dzt) / (MIRROR["dz"][0] - MIRROR["dz"][1])))[:, None]
        col = col * (1 - wm) + V7.MURK_DOWN * 1.4 * wm
        T = np.exp(-tp[:, None] / V7.ABSORB_UP_M)
        out[ys, xs] = col * T + murk[ys, xs] * (1 - T)
        rest = ~under & ~self.thr
        out[rest] = murk[rest]
        return out


def main():
    a = sys.argv[1:]
    if a[0] in ("frame", "frames"):
        C9.apply_murk()
    if a[0] == "frame":
        sc = Scene11(a[1], a[2], a[3], a[4])
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
        step = int(a[7]) if len(a) > 7 else 1
        todo = [k for k in range(A_, B_, step) if not os.path.exists(f"{out}/f_{k:04d}.png")]
        print("todo", len(todo), flush=True)
        if not todo:
            return
        sc = Scene11(a[1], a[2], a[3], a[4])
        for k in todo:
            if os.path.exists(f"{out}/f_{k:04d}.png"):
                continue
            t0 = time.time()
            img, h = sc.frame(k)
            tmp = f"{out}/.f_{k:04d}.{os.getpid()}.png"
            Image.fromarray(img).save(tmp, compress_level=1)
            os.replace(tmp, f"{out}/f_{k:04d}.png")
            print("frame", k, "s", round(time.time() - t0, 1), flush=True)
    elif a[0] in ("video", "sheet"):
        C10.main()


if __name__ == "__main__":
    main()
