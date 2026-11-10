"""Two cormorants perched on the tops of the tallest dead trees in the v9 shot `drowning` (the user, 8 November 2026:
"have a bird or two perched near the top of the tallest dead tree branches so that even though the camera is under
water we can tell that the top of the tree is not since the bird is there moving its head or something").

Drawn, not observed. The species is birds_v4's cormorant (Phalacrocorax carbo: 1,240 nests on six towers of these
crossings in 2012, Sidorenko & Siokhin 2016); perching on drowned dead trees and holding the wings out to dry after
fishing are what the species does (a drawing of typical behaviour, not a record of these birds). Sizes typical: about
0.85 m long, 1.35 m across the wings. No colony is shown or implied at a tower.

Each bird is a few ellipsoids (body, neck, head, white cheek, bill, tail, feet; two panels a wing when they open),
ray-traced in numpy through v7's camera (composite_v7: the eye, lens 18, pitch 14, heading 22) at 4x4 samples a
pixel, hidden where the scene's own surfaces (pos2x) lie nearer. Lit by the overcast sky (DAY) from above, tinted
toward the day haze with distance as birds_v5. Output: a premultiplied linear RGBA layer at 1080p, laid over the dry
picture before the water is drawn (so it wavers through the surface with everything above it).

    python -I birds_v9.py still <perch.json> <pos2x.exr> <picture.png> <out.png> [t ...]    the birds on a picture
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "v7", "scripts")))
import composite_v7 as V7  # noqa: E402

W, H = V7.W, V7.H
SS = 4                                      # samples a pixel, each way
EYE = V7.EYE
RGB = (38, 38, 40)                          # birds_v4's cormorant
CHEEK = (196, 192, 182)
HAZE_RGB = np.array([0.62, 0.66, 0.70])
UP = np.array([0.0, 0.0, 1.0])


def lin(c):
    c = np.asarray(c, float) / 255
    return np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)


def ease(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def keyed(keys, t, dur=0.14):
    """Piecewise holds with quick eased moves between them (a bird's head moves in jerks): keys [(t, value...)]."""
    v = np.array(keys[0][1:], float)
    for k0, k1 in zip(keys, keys[1:]):
        if t >= k1[0]:
            v = np.array(k1[1:], float)
        elif t > k1[0] - dur:
            u = ease((t - (k1[0] - dur)) / dur)
            return np.array(k0[1:], float) * (1 - u) + np.array(k1[1:], float) * u
    return v


# the birds: which tree top (perch.json plant index), feet this far under the tip, facing (degrees from the camera's
# right, turning toward the camera), head keys (t s, yaw deg left of facing, pitch deg up), wings (open, held, close s)
BIRDS = [
    dict(id="A", plant="109", below=0.12, facing=168, scale=1.0,
         head=[(0, 0, 12), (1.3, 35, 8), (2.9, -10, 15), (4.2, 70, 5), (5.0, 20, 10), (6.6, -45, 18), (8.1, 0, 12),
               (9.4, 80, 0), (10.0, 40, 6), (11.8, -20, 20), (13.2, 25, 10), (14.3, 60, 4)],
         wings=None),
    dict(id="B", plant="101", below=0.10, facing=-55, scale=0.95,
         head=[(0, 10, 15), (0.9, -30, 10), (2.2, 40, 12), (3.4, 0, 20), (8.6, -25, 15), (9.8, 20, 10),
               (11.3, -50, 8), (12.6, 0, 14), (14.0, 35, 10)],
         wings=(4.0, 4.6, 10.6, 11.4)),
]


class Ell:
    __slots__ = ("c", "A", "Ai", "rgb")

    def __init__(self, c, axes, rgb):
        self.c = np.asarray(c, float)
        self.A = np.stack(axes, 1)                        # columns: the semi-axes as vectors
        self.Ai = np.linalg.inv(self.A)
        self.rgb = rgb


def frame_of(facing_deg):
    """The bird's forward (horizontal) and left, from the camera's right turned `facing` degrees toward the camera."""
    R = V7.rotation()
    right = R[:, 0].copy(); right[2] = 0; right /= np.linalg.norm(right)
    toward = -R[:, 2].copy(); toward[2] = 0; toward /= -np.linalg.norm(toward)   # from the scene toward the eye
    a = math.radians(facing_deg)
    f = right * math.cos(a) + toward * math.sin(a)
    return f, np.cross(UP, f)


def shape(b, t, foot):
    """The bird's ellipsoids at time t, in world metres, standing at `foot`."""
    s = b["scale"]
    f, l = frame_of(b["facing"])
    u = UP
    dark, cheek = lin(RGB), lin(CHEEK)
    th = math.radians(58)                                       # the body held upright
    a = math.cos(th) * f + math.sin(th) * u
    n_ = -math.sin(th) * f + math.cos(th) * u                  # the body's back-to-belly axis
    sway = 0.012 * math.sin(2 * math.pi * 0.31 * t + float(b["id"] == "B"))   # balancing on a thin tip
    bc = foot + s * (0.25 * u - 0.02 * f) + s * sway * l
    E = [Ell(foot + s * 0.035 * u, [s * 0.035 * f, s * 0.05 * l, s * 0.04 * u], dark),          # feet on the branch
         Ell(bc, [s * 0.235 * a, s * 0.085 * l, s * 0.10 * n_], dark)]                          # body
    tdir = -0.33 * f - 0.94 * u; tdir /= np.linalg.norm(tdir)
    tp = np.cross(tdir, l)
    E.append(Ell(bc - s * 0.17 * a + s * 0.13 * tdir, [s * 0.12 * tdir, s * 0.05 * l, s * 0.016 * tp], dark))  # tail
    nb = bc + s * 0.19 * a
    ndir = 0.22 * f + 0.975 * u; ndir /= np.linalg.norm(ndir)
    E.append(Ell(nb + s * 0.085 * ndir, [s * 0.105 * ndir, s * 0.036 * l, s * 0.04 * np.cross(l, ndir)], dark))  # neck
    yaw, pitch = (math.radians(x) for x in keyed(b["head"], t))
    hf = math.cos(pitch) * (math.cos(yaw) * f + math.sin(yaw) * l) + math.sin(pitch) * u
    hl = np.cross(u, hf); hl /= np.linalg.norm(hl)
    hu = np.cross(hf, hl)
    hc = nb + s * 0.185 * ndir + s * 0.02 * hf
    E.append(Ell(hc, [s * 0.062 * hf, s * 0.034 * hl, s * 0.038 * hu], dark))                 # head
    E.append(Ell(hc + s * 0.012 * hf - s * 0.018 * hu, [s * 0.034 * hf, s * 0.036 * hl, s * 0.022 * hu], cheek))  # cheek
    E.append(Ell(hc + s * 0.095 * hf - s * 0.006 * hu, [s * 0.05 * hf, s * 0.011 * hl, s * 0.012 * hu], dark))   # bill
    if b["wings"]:
        o0, o1, c0, c1 = b["wings"]
        e = float(ease((t - o0) / (o1 - o0)) * (1 - ease((t - c0) / (c1 - c0))))
        if e > 0.02:
            shiver = 0.0
            if o1 < t < c0:                                   # now and then a slow shake of the held wings
                for t0 in (6.2, 8.9):
                    if t0 < t < t0 + 0.9:
                        shiver = 0.10 * math.sin(2 * math.pi * 3.0 * (t - t0)) * math.sin(math.pi * (t - t0) / 0.9)
            for sg in (1, -1):
                sh = bc + s * 0.11 * a + s * sg * 0.07 * l
                fold = -a * 0.8 + sg * l * 0.2; fold /= np.linalg.norm(fold)
                up_a = math.radians(12) + shiver
                spread = sg * l * math.cos(up_a) + u * math.sin(up_a)
                w1 = fold * (1 - e) + spread * e; w1 /= np.linalg.norm(w1)
                L1 = s * (0.12 + 0.07 * e)
                c1v = np.cross(w1, f); c1v *= -np.sign(c1v[2]) if abs(c1v[2]) > 1e-6 else 1   # the chord, downward
                E.append(Ell(sh + w1 * L1, [w1 * L1, c1v * s * (0.06 + 0.06 * e), f * s * 0.014], dark))
                el = sh + w1 * 2 * L1 * 0.95
                dr = math.radians(48) - 0.6 * shiver
                w2 = sg * l * math.cos(dr) - u * math.sin(dr)
                w2 = w2 * e + w1 * (1 - e); w2 /= np.linalg.norm(w2)
                L2 = s * (0.08 + 0.10 * e)
                c2v = np.cross(w2, f); c2v *= -np.sign(c2v[2]) if abs(c2v[2]) > 1e-6 else 1
                E.append(Ell(el + w2 * L2, [w2 * L2, c2v * s * 0.05 * (0.5 + 0.5 * e), f * s * 0.012], dark))
    return E


def trace(E, O, D):
    """Nearest hit of rays (O, D (n, 3)) on the ellipsoids: distance (inf for none), normal, colour."""
    n = len(D)
    best = np.full(n, np.inf)
    nrm = np.zeros((n, 3))
    col = np.zeros((n, 3))
    for e in E:
        o = (O - e.c) @ e.Ai.T
        d = D @ e.Ai.T
        A = (d * d).sum(1)
        B = 2 * (o * d).sum(1)
        Cc = (o * o).sum(1) - 1
        disc = B * B - 4 * A * Cc
        ok = disc > 0
        s = np.where(ok, (-B - np.sqrt(np.maximum(disc, 0))) / (2 * A), np.inf)
        s = np.where(s > 0, s, np.inf)
        m = s < best
        if m.any():
            best[m] = s[m]
            p = o[m] + s[m, None] * d[m]
            nw = p @ e.Ai                                   # A^-T p
            nrm[m] = nw / np.linalg.norm(nw, axis=1, keepdims=True)
            col[m] = e.rgb
    return best, nrm, col


class Birds:
    def __init__(self, perch_json, pos2x=None):
        j = json.load(open(perch_json))
        self.feet = {}
        for b in BIRDS:
            tip = np.array(j["plants"][b["plant"]]["top"][0][:3], float)
            self.feet[b["id"]] = tip - np.array([0, 0, b["below"]])
        self.d2 = None
        if pos2x is not None:
            os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "1"
            p = V7.C.read(pos2x)
            self.d2 = np.where(p[..., 3] > 0.5, p[..., 1], 1e6).astype(np.float32)

    def layer(self, t):
        """Premultiplied linear RGBA (H, W, 4) of the birds at time t."""
        out = np.zeros((H, W, 4), np.float32)
        R = V7.rotation()
        f = V7.VIEW["lens"] / 36.0
        for b in BIRDS:
            foot = self.feet[b["id"]]
            E = shape(b, t, foot)
            i, j, _ = V7.project(foot[None], W, H)
            x0, x1 = int(i[0]) - 40, int(i[0]) + 40
            y0, y1 = int(j[0]) - 50, int(j[0]) + 30
            x0, y0 = max(x0, 0), max(y0, 0)
            x1, y1 = min(x1, W), min(y1, H)
            if x1 <= x0 or y1 <= y0:
                continue
            xs = x0 + (np.arange((x1 - x0) * SS) + 0.5) / SS
            ys = y0 + (np.arange((y1 - y0) * SS) + 0.5) / SS
            X, Y = np.meshgrid(xs, ys)
            dc = np.stack([(X / W - 0.5) / f, (0.5 - Y / H) * (H / W) / f, -np.ones_like(X)], -1).reshape(-1, 3)
            D = dc @ R.T
            dn = np.linalg.norm(D, axis=1, keepdims=True)
            D = D / dn
            s, nrm, col = trace(E, np.broadcast_to(EYE, D.shape), D)
            hit = np.isfinite(s)
            if self.d2 is not None:                          # the scene's own surfaces nearer than the bird hide it
                jj = np.clip((Y.reshape(-1) * 2).astype(int), 0, 2 * H - 1)
                ii = np.clip((X.reshape(-1) * 2).astype(int), 0, 2 * W - 1)
                hit &= ~(self.d2[jj, ii] < s - 0.15)
            sky = 0.42 + 0.38 * nrm[:, 2] + 0.12 * np.clip(-(nrm * D).sum(1), 0, 1)   # overcast from above
            spec = 0.03 * np.clip(nrm[:, 2], 0, 1) ** 4                                 # the plumage's faint sheen
            c = col * HAZE_RGB * sky[:, None] + spec[:, None]
            dist = float(np.linalg.norm(foot - EYE))
            k = 0.02 + 0.45 * (1 - math.exp(-dist / 900.0))   # (birds_v5: 0.1 at the least, for far birds)
            c = c * (1 - k) + HAZE_RGB * k
            rgba = np.concatenate([c * hit[:, None], hit[:, None].astype(float)], 1)
            rgba = rgba.reshape(y1 - y0, SS, x1 - x0, SS, 4).mean((1, 3)).astype(np.float32)
            a = rgba[..., 3:4]
            win = out[y0:y1, x0:x1]
            win[..., :3] = rgba[..., :3] + (1 - a) * win[..., :3]
            win[..., 3:4] = a + (1 - a) * win[..., 3:4]
        return out


def main():
    a = sys.argv[1:]
    if a[0] == "still":
        from PIL import Image
        bd = Birds(a[1], None if a[2] == "-" else a[2])
        pic = np.asarray(Image.open(a[3]).convert("RGB"), np.float32)
        lin_pic = lin(pic * 0 + pic)   # sRGB to linear
        ts = [float(x) for x in a[5:]] or [0.0]
        tiles = []
        for t in ts:
            L = bd.layer(t)
            o = L[..., :3] + (1 - L[..., 3:4]) * lin_pic
            img = (V7.C.srgb(o) * 255).round().astype(np.uint8)
            tiles.append(img)
        full = Image.fromarray(tiles[0])
        full.save(a[4])
        # a crop strip round the birds at 4x
        crops = [Image.fromarray(im).crop((520, 470, 840, 600)).resize((960, 390), Image.NEAREST) for im in tiles]
        S = Image.new("RGB", (960, 390 * len(crops)))
        for k, c in enumerate(crops):
            S.paste(c, (0, 390 * k))
        S.save(a[4].replace(".png", "_crops.png"))


if __name__ == "__main__":
    main()
