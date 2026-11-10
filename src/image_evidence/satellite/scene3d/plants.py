"""Representative plant models, built from numbers (stems, branches, twigs, leaves, blades, spikes),
never from images or scans: a copy of research_notes/Under the crossing still/scripts/plants.py (the v3 stills of
`under-the-crossing`, 5 November 2026), used by the flight south's look pass 2 (vegetation.py) with one level more,
`crown` (LOD 3: a trunk and a few broad cards, for trees a kilometre and more from the camera). Each function returns a Geo: triangles with a colour (linear RGB) and a flag per face
(1 for a thin card lit from either side, 0 for a stem lit like the towers). Used by still_v3.py inside Blender; plain
numpy, so it can also be run outside Blender to count faces.

Shapes (all representative, said so):
  white willow (Salix alba, S. x rubens): several stems from the base, ascending branches, slender drooping twigs,
    narrow lance-shaped leaves (7-11 cm by 1-2 cm), grey-green above, silvery beneath;
  black poplar (Populus nigra): one straighter stem, wider-spreading branches, rhombic-deltoid leaves with rounded shoulders on stalks;
  saplings: clumps of thin young willow (reddish twigs: S. x rubens) or poplar stems;
  Amorpha fruticosa: arching stems, pinnate leaves, dark seed spikes at the tips;
  Tamarix ramosissima: arching stems, feathery blue-green sprays, pink plumes;
  Phragmites australis: clumps of tall culms, long blades, purple-brown plumes, some of last year's dry culms;
  Typha: upright strap leaves, brown spikes;
  tall grasses (Calamagrostis epigejos, Phalaris arundinacea, Echinochloa): arching blades, fluffy panicles;
  broad-leaved herbs (Xanthium orientale, Chenopodium album): branched stems, broad leaves, burrs or seed clusters;
  Artemisia (A. vulgaris, A. absinthium): grey-green, finely cut leaves, brownish flower panicles;
  flowering herbs: Lythrum salicaria (magenta spikes), Melilotus albus (white racemes), Epilobium hirsutum (pink);
  dry stalks: Erigeron canadensis and the year's dead herbs, straw-coloured;
  low grasses: tufts of blades, green and straw.
"""
import math
import numpy as np


def lin(c):
    c = np.asarray(c, float) / 255
    return np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)


def unit(v):
    v = np.asarray(v, float)
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-9)


def perp(u, rng=None):
    """A unit vector at right angles to each u, near horizontal."""
    a = np.zeros_like(u)
    a[..., 2] = 1.0
    s = np.cross(u, a)
    bad = np.linalg.norm(s, axis=-1) < 1e-3
    if np.any(bad):
        b = np.zeros_like(u)
        b[..., 0] = 1.0
        s[bad] = np.cross(u[bad], b[bad])
    s = unit(s)
    if rng is not None:
        s = unit(s + rng.normal(0, 0.25, s.shape))
        s = unit(s - (s * u).sum(-1, keepdims=True) * u)
    return s


class Geo:
    def __init__(self):
        self.V, self.F, self.C, self.K, self.n = [], [], [], [], 0

    def add(self, V, F, C, K):
        V = np.asarray(V, float).reshape(-1, 3)
        F = np.asarray(F, np.int64).reshape(-1, 3)
        self.V.append(V)
        self.F.append(F + self.n)
        self.C.append(np.broadcast_to(np.asarray(C, float), (len(F), 3)).copy() if np.ndim(C) == 1 else np.asarray(C))
        self.K.append(np.full(len(F), float(K)))
        self.n += len(V)

    def arrays(self):
        if not self.V:
            return np.zeros((0, 3)), np.zeros((0, 3), np.int64), np.zeros((0, 3)), np.zeros(0)
        return np.vstack(self.V), np.vstack(self.F), np.vstack(self.C), np.concatenate(self.K)

    # ---- primitives
    def tubes(self, P, R, sides, col):
        """Tubes along paths P (b, n, 3) with radii R (b, n); col (b, 3) or (3,)."""
        P = np.asarray(P, float)
        b, n, _ = P.shape
        if b == 0:
            return
        T = unit(np.gradient(P, axis=1))
        u = perp(T)
        w = np.cross(T, u)
        a = 2 * math.pi * np.arange(sides) / sides
        V = P[:, :, None, :] + np.asarray(R)[:, :, None, None] * (
            np.cos(a)[None, None, :, None] * u[:, :, None, :] + np.sin(a)[None, None, :, None] * w[:, :, None, :])
        idx = np.arange(b * n * sides).reshape(b, n, sides)
        a0, b0 = idx[:, :-1, :], idx[:, 1:, :]
        a1, b1 = np.roll(idx, -1, 2)[:, :-1, :], np.roll(idx, -1, 2)[:, 1:, :]
        F = np.stack([np.stack([a0, a1, b1], -1), np.stack([a0, b1, b0], -1)], -2).reshape(-1, 3)
        col = np.asarray(col, float)
        C = np.repeat(col if col.ndim == 2 else col[None].repeat(b, 0), (n - 1) * sides * 2, axis=0)
        self.add(V.reshape(-1, 3), F, C, 0)

    def leaves(self, B, U, S, L, W, col, widest=0.35, fold=0.22, outline=None):
        """Leaf cards: base B, along U, across S, length L, width W (each (m,...)); a midrib fold of fold * W.
        outline: (along, half-width share of W) pairs for one side, base to tip, mirrored: a rounder leaf as a fan."""
        B, U, S = (np.asarray(a, float) for a in (B, U, S))
        m = len(B)
        if m == 0:
            return
        L, W = np.asarray(L, float)[:, None], np.asarray(W, float)[:, None]
        N = np.cross(U, S)
        if outline is not None:
            ring = [B] + [B + U * L * a - S * W * w for a, w in outline] + [B + U * L] + \
                   [B + U * L * a + S * W * w for a, w in outline[::-1]]
            k = len(ring)
            V = np.stack(ring + [B + U * L * 0.4 + N * W * fold], 1).reshape(-1, 3)
            tri = np.array([[i, (i + 1) % k, k] for i in range(k)])
            F = ((np.arange(m) * (k + 1))[:, None, None] + tri[None]).reshape(-1, 3)
            col = np.asarray(col, float)
            C = np.repeat(col if col.ndim == 2 else col[None].repeat(m, 0), k, axis=0)
            self.add(V, F, C, 1)
            return
        v0 = B
        v2 = B + U * L
        v1 = B + U * L * widest - S * W / 2
        v3 = B + U * L * widest + S * W / 2
        v4 = B + U * L * 0.45 + N * W * fold
        V = np.stack([v0, v1, v2, v3, v4], 1).reshape(-1, 3)
        base = (np.arange(m) * 5)[:, None, None]
        F = (base + np.array([[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4]])[None]).reshape(-1, 3)
        col = np.asarray(col, float)
        C = np.repeat(col if col.ndim == 2 else col[None].repeat(m, 0), 4, axis=0)
        self.add(V, F, C, 1)

    def blades(self, B, D, L, W, bend, col, segs=4, taper=1.5, rng=None):
        """Grass-like blades: from B along D, curving down by bend (per unit length), width W tapering to the tip."""
        B, D = np.asarray(B, float), unit(D)
        m = len(B)
        if m == 0:
            return
        L, W, bend = (np.asarray(a, float) for a in (L, W, bend))
        S = perp(D, rng)
        pts = [B]
        d = D.copy()
        for i in range(segs):
            d = unit(d - np.array([0, 0, 1.0]) * (bend * L / segs)[:, None])
            pts.append(pts[-1] + d * (L / segs)[:, None])
        P = np.stack(pts, 1)                                         # (m, segs+1, 3)
        t = np.linspace(0, 1, segs + 1)
        wt = (1 - t ** taper)[None, :] * W[:, None]
        wt[:, -1] = 0.002 * W / np.maximum(W, 1e-6)
        V = np.stack([P - S[:, None, :] * wt[..., None] / 2, P + S[:, None, :] * wt[..., None] / 2], 2)  # (m,s+1,2,3)
        idx = np.arange(m * (segs + 1) * 2).reshape(m, segs + 1, 2)
        a0, a1, b0, b1 = idx[:, :-1, 0], idx[:, :-1, 1], idx[:, 1:, 0], idx[:, 1:, 1]
        F = np.stack([np.stack([a0, a1, b1], -1), np.stack([a0, b1, b0], -1)], -2).reshape(-1, 3)
        col = np.asarray(col, float)
        C = np.repeat(col if col.ndim == 2 else col[None].repeat(m, 0), segs * 2, axis=0)
        self.add(V.reshape(-1, 3), F, C, 1)
        return P

    def cluster(self, rng, A, D, length, radius, n, L, W, col, up=0.0):
        """Small cards round an axis from A along D (a plume, a panicle, a spike of flowers)."""
        A, D = np.asarray(A, float), unit(D)
        t = rng.uniform(0, 1, n)
        rad = radius * (1 - 0.6 * t) * np.sqrt(rng.uniform(0, 1, n))
        side = perp(np.repeat(D[None], n, 0), rng)
        ang = rng.uniform(0, 2 * math.pi, n)
        other = np.cross(D, side)
        C = A + D * (t * length)[:, None] + (np.cos(ang) * rad)[:, None] * side + (np.sin(ang) * rad)[:, None] * other
        U = unit(D * (0.6 + up) + rng.normal(0, 0.6, (n, 3)))
        S = perp(U, rng)
        self.leaves(C - U * (L / 2), U, S, np.full(n, L), np.full(n, W), col, widest=0.5, fold=0.1)


def path(rng, p0, d0, L, n, droop=0.0, wander=0.05, up=0.0):
    pts = [np.asarray(p0, float)]
    d = unit(d0)
    for i in range(n):
        d = unit(d + rng.normal(0, wander, 3) + np.array([0, 0, up - droop * (i + 1) / n]))
        pts.append(pts[-1] + d * L / n)
    return np.array(pts)


def along(P, t):
    """Points and directions at fractions t of a polyline P."""
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    tt = np.asarray(t) * s[-1]
    j = np.clip(np.searchsorted(s, tt) - 1, 0, len(P) - 2)
    f = ((tt - s[j]) / np.maximum(seg[j], 1e-9))[..., None]
    return P[j] + (P[j + 1] - P[j]) * f, unit(P[j + 1] - P[j])


def dirs(az, el):
    az, el = np.asarray(az), np.asarray(el)
    return np.stack([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)], -1)


def mixc(rng, a, b, n):
    u = rng.uniform(0, 1, (n, 1))
    return lin(a) * (1 - u) + lin(b) * u


# ---------------------------------------------------------------- trees

LEAF = {  # (top colour a, top colour b, underside, share underside, yellowing)
    "willow": ((86, 106, 60), (124, 140, 92), (156, 166, 146), 0.32, (168, 156, 84)),
    "poplar": ((70, 98, 48), (94, 118, 56), (108, 128, 84), 0.12, (146, 142, 70)),
}


# black poplar's leaf, rhombic-deltoid with rounded shoulders and a drawn-out tip (typical of the species)
POPLAR_LEAF = [(0.06, 0.34), (0.2, 0.5), (0.36, 0.46), (0.56, 0.3), (0.78, 0.13)]


def leaf_colours(rng, kind, n):
    a, b, under, share, yel = LEAF[kind]
    c = mixc(rng, a, b, n)
    u = rng.uniform(0, 1, n)
    c[u < share] = lin(under) * rng.uniform(0.85, 1.05, ((u < share).sum(), 1))
    c[u > (0.975 if kind == "willow" else 0.99)] = lin(yel)
    return c


def shade_crown(pos, base, h, cols):
    """Crowns read as volumes: leaves inside and low in the crown darker (a drawn occlusion; the scene has no shadows)."""
    r = np.linalg.norm(pos[:, :2] - base[:2], axis=1)
    rr = r / max(np.percentile(r, 95), 0.3)
    hf = np.clip((pos[:, 2] - base[2]) / h, 0, 1.2)
    k = 0.48 + 0.52 * np.clip(0.55 * rr + 0.55 * hf - 0.1, 0, 1)
    return cols * k[:, None]


def tree(kind, seed, lod, H):
    """kind 'willow' or 'poplar', lod 0 (leaves), 1 (sprays on twigs), 2 (coarse sprays). H: the model's height."""
    rng = np.random.default_rng(seed)
    g = Geo()
    willow = kind == "willow"
    bark = lin((104, 98, 86)) if willow else lin((120, 116, 102))
    nst = int(rng.integers(2, 6)) if willow else 1
    leafB, leafU, leafS, leafL, leafW = [], [], [], [], []
    spray = []                       # (base, dir, length, width)
    sides = {0: 7, 1: 5, 2: 3}[lod]
    for si in range(nst):
        h = H * (rng.uniform(0.74, 1.0) if willow else rng.uniform(0.96, 1.04))
        lean = rng.uniform(0.04, 0.2) if willow else rng.uniform(0.0, 0.05)
        la = rng.uniform(0, 2 * math.pi)
        base = np.array([*rng.normal(0, 0.3, 2), 0.0]) if willow else np.zeros(3)
        st = path(rng, base, [math.sin(lean) * math.cos(la), math.sin(lean) * math.sin(la), math.cos(lean)], h, 7,
                  wander=0.05 if willow else 0.025)
        r0 = (0.045 if willow else 0.065) * rng.uniform(0.85, 1.15) * H / 6.5
        t = np.linspace(0, 1, len(st))
        g.tubes(st[None], (r0 * (1 - 0.78 * t))[None], sides, bark)
        npr = int(rng.integers(10, 15)) if willow else int(rng.integers(16, 23))
        fs = np.sort(rng.uniform(0.3 if willow else 0.36, 0.95, npr))
        az0 = rng.uniform(0, 2 * math.pi)
        prims = []
        for k, f in enumerate(fs):
            p, sd = along(st, f)
            az = az0 + k * 2.39996 + rng.normal(0, 0.3)
            el = math.radians((rng.uniform(48, 70) if willow else rng.uniform(32, 55)) + 15 * f)
            d = unit(dirs(az, el) + sd * 0.3)
            Lp = h * (0.31 if willow else 0.27) * (1.12 - 0.62 * f) * rng.uniform(0.75, 1.2)
            pp = path(rng, p, d, Lp, 4, droop=0.22 if willow else 0.08, wander=0.08)
            prims.append((pp, Lp, f))
        top, td = along(st, 1.0)
        prims.append((path(rng, top - td * 0.3, unit(td + [0, 0, 0.5]), h * 0.16, 3, wander=0.1), h * 0.16, 1.0))
        for pp, Lp, f in prims:
            rr = r0 * 0.34 * (1.05 - 0.5 * f)
            if lod <= 1 or Lp > 0.8:
                g.tubes(pp[None], (rr * np.linspace(1, 0.25, len(pp)))[None], 5 if lod == 0 else 3, bark)
            if lod == 2:
                n = 6
                ts = rng.uniform(0.3, 1.1, n)
                q, qd = along(pp, np.clip(ts, 0, 1))
                q = q + qd * np.maximum(ts - 1, 0)[:, None] * Lp + rng.normal(0, 0.3, (n, 3))
                for i in range(n):
                    spray.append((q[i], unit(qd[i] + rng.normal(0, 0.7, 3) + [0, 0, -0.3 if willow else 0]),
                                  rng.uniform(0.9, 1.3), 0.5 if willow else 0.7))
                continue
            nsec = {0: 9, 1: 6}[lod] if willow else {0: 8, 1: 6}[lod]
            ts = rng.uniform(0.22, 1.0, nsec)
            q, qd = along(pp, ts)
            for i in range(nsec):
                sd = unit(qd[i] + rng.normal(0, 0.65, 3) + [0, 0, 0.1])
                Ls = rng.uniform(0.4, 0.95) * min(1.0, Lp / 1.4 + 0.3)
                sp = path(rng, q[i], sd, Ls, 3, droop=0.5 if willow else 0.15, wander=0.1)
                if lod == 0:
                    g.tubes(sp[None], (np.linspace(0.011, 0.004, len(sp)))[None], 3, bark)
                ntw = {0: 9, 1: 6}[lod] if willow else {0: 11, 1: 6}[lod]
                tt = rng.uniform(0.12, 1.0, ntw)
                tq, tqd = along(sp, tt)
                for j in range(ntw):
                    td_ = unit(tqd[j] + rng.normal(0, 0.8, 3) + [0, 0, -0.75 if willow else -0.05])
                    Lt = rng.uniform(0.2, 0.42) if willow else rng.uniform(0.12, 0.24)
                    if lod == 1:
                        spray.append((tq[j], td_, Lt + 0.07, 0.085 if willow else 0.13))
                        continue
                    nl = max(3, int(Lt / (0.016 if willow else 0.02)))
                    s = np.linspace(0.08, 1.0, nl) * Lt
                    droop = (0.9 if willow else 0.2) * s ** 2
                    pos = tq[j] + td_ * s[:, None] - np.array([0, 0, 1.0]) * droop[:, None]
                    sidev = perp(np.repeat(td_[None], nl, 0), rng) * np.where(np.arange(nl) % 2, 1, -1)[:, None]
                    if willow:
                        U = unit(td_ * 0.7 + sidev * 0.5 + [0, 0, -0.35] + rng.normal(0, 0.15, (nl, 3)))
                        L = rng.uniform(0.075, 0.12, nl)
                        W = L * rng.uniform(0.14, 0.2, nl)
                        B = pos
                    else:
                        U = unit(sidev * 0.6 + td_ * 0.3 + [0, 0, -0.55] + rng.normal(0, 0.3, (nl, 3)))
                        L = rng.uniform(0.065, 0.095, nl)
                        W = L * rng.uniform(0.8, 1.0, nl)
                        B = pos + U * 0.03                   # the leaf stalk
                    leafB.append(B); leafU.append(U); leafL.append(L); leafW.append(W)
                    leafS.append(perp(U, rng))
    if leafB:
        B, U, S, L, W = (np.concatenate(a) for a in (leafB, leafU, leafS, leafL, leafW))
        c = shade_crown(B, np.zeros(3), H, leaf_colours(rng, kind, len(B)))
        g.leaves(B, U, S, L, W, c, widest=0.35 if willow else 0.3, fold=0.25 if willow else 0.12,
                 outline=None if willow else POPLAR_LEAF)
    if spray:
        B = np.array([s[0] for s in spray]); U = np.array([s[1] for s in spray])
        L = np.array([s[2] for s in spray]); W = np.array([s[3] for s in spray])
        c = shade_crown(B, np.zeros(3), H, leaf_colours(rng, kind, len(B)) * 0.95)
        g.leaves(B, U, perp(U, rng), L, W, c, widest=0.45, fold=0.15)
    return g


def sapling(seed, lod, H):
    """A clump of young stems: var 0-1 willow (S. x rubens, reddish twigs), 2-3 poplar."""
    rng = np.random.default_rng(seed)
    kind = "willow" if seed % 4 < 2 else "poplar"
    g = Geo()
    stemc = lin((132, 84, 62)) if kind == "willow" else lin((118, 116, 98))
    n = int(rng.integers(3, 9))
    B_, U_, S_, L_, W_ = [], [], [], [], []
    spray = []
    for i in range(n):
        h = H * rng.uniform(0.5, 1.0)
        lean = rng.uniform(0.03, 0.22)
        la = rng.uniform(0, 2 * math.pi)
        base = np.array([*rng.normal(0, 0.22, 2), 0.0])
        st = path(rng, base, [math.sin(lean) * math.cos(la), math.sin(lean) * math.sin(la), math.cos(lean)], h, 5,
                  wander=0.05)
        r = rng.uniform(0.009, 0.018) * h / 3
        g.tubes(st[None], (r * np.linspace(1, 0.3, len(st)))[None], 4 if lod == 0 else 3, stemc)
        ntw = int(h / (0.035 if lod == 0 else 0.09))
        ts = rng.uniform(0.3, 1.0, ntw)
        q, qd = along(st, ts)
        for j in range(ntw):
            td_ = unit(dirs(rng.uniform(0, 2 * math.pi), math.radians(rng.uniform(25, 60))) * 0.8 + qd[j] * 0.4
                       + [0, 0, -0.2 if kind == "willow" else 0])
            Lt = rng.uniform(0.12, 0.32) * (1.2 - 0.5 * ts[j])
            if lod == 1:
                spray.append((q[j], td_, Lt + 0.06, 0.08 if kind == "willow" else 0.12))
                continue
            nl = max(3, int(Lt / (0.017 if kind == "willow" else 0.03)))
            s = np.linspace(0.1, 1.0, nl) * Lt
            pos = q[j] + td_ * s[:, None] - np.array([0, 0, 0.5]) * (s ** 2)[:, None]
            sidev = perp(np.repeat(td_[None], nl, 0), rng) * np.where(np.arange(nl) % 2, 1, -1)[:, None]
            if kind == "willow":
                U = unit(td_ * 0.7 + sidev * 0.5 + [0, 0, -0.2] + rng.normal(0, 0.15, (nl, 3)))
                L = rng.uniform(0.07, 0.12, nl); W = L * rng.uniform(0.13, 0.2, nl)
            else:
                U = unit(td_ * 0.3 + sidev * 0.8 + rng.normal(0, 0.45, (nl, 3)))
                L = rng.uniform(0.06, 0.095, nl); W = L * rng.uniform(0.8, 1.0, nl)
            B_.append(pos); U_.append(U); L_.append(L); W_.append(W); S_.append(perp(U, rng))
    if B_:
        B, U, S, L, W = (np.concatenate(a) for a in (B_, U_, S_, L_, W_))
        c = shade_crown(B, np.zeros(3), H, leaf_colours(rng, kind, len(B)))
        g.leaves(B, U, S, L, W, c, widest=0.35 if kind == "willow" else 0.42, fold=0.2,
                 outline=None if kind == "willow" else POPLAR_LEAF)
    if spray:
        B = np.array([s[0] for s in spray]); U = np.array([s[1] for s in spray])
        c = shade_crown(B, np.zeros(3), H, leaf_colours(rng, kind, len(B)))
        g.leaves(B, U, perp(U, rng), np.array([s[2] for s in spray]), np.array([s[3] for s in spray]), c,
                 widest=0.45, fold=0.15)
    return g


# ---------------------------------------------------------------- shrubs

def amorpha(seed, lod, H):
    rng = np.random.default_rng(seed)
    g = Geo()
    n = int(rng.integers(5, 11))
    stemc = lin((96, 84, 70))
    for i in range(n):
        az = rng.uniform(0, 2 * math.pi)
        d = dirs(az, math.radians(rng.uniform(58, 82)))
        L = H * rng.uniform(0.75, 1.1)
        st = path(rng, [*rng.normal(0, 0.15, 2), 0], d, L, 5, droop=0.35, wander=0.05)
        g.tubes(st[None], (np.linspace(0.014, 0.005, len(st)))[None], 3, stemc)
        nlv = int(L / (0.045 if lod == 0 else 0.09))
        ts = rng.uniform(0.25, 0.97, nlv)
        q, qd = along(st, ts)
        for j in range(nlv):
            rd = unit(dirs(rng.uniform(0, 2 * math.pi), math.radians(rng.uniform(5, 45))) + qd[j] * 0.5)
            Lr = rng.uniform(0.16, 0.26)
            if lod == 1:
                g.leaves(q[j][None], rd[None], perp(rd[None], rng), [Lr], [0.11], mixc(rng, (54, 80, 40), (88, 110, 56), 1),
                         widest=0.5, fold=0.1)
                continue
            k = 13
            s = np.linspace(0.1, 1.0, k) * Lr
            P = q[j] + rd * s[:, None] - np.array([0, 0, 0.35]) * (s ** 2)[:, None]
            sv = perp(np.repeat(rd[None], k, 0)) * np.where(np.arange(k) % 2, 1, -1)[:, None]
            U = unit(sv + rd * 0.35 + rng.normal(0, 0.1, (k, 3)))
            U[-1] = rd
            Lf = rng.uniform(0.032, 0.048, k)
            g.leaves(P, U, perp(U, rng), Lf, Lf * 0.5, mixc(rng, (48, 72, 36), (84, 106, 54), k), widest=0.5, fold=0.12)
        tip, td_ = along(st, 1.0)
        for _ in range(int(rng.integers(1, 4))):
            sd = unit(td_ + rng.normal(0, 0.3, 3) + [0, 0, 0.4])
            g.cluster(rng, tip, sd, rng.uniform(0.08, 0.15), 0.015, 14 if lod == 0 else 4, 0.018, 0.008,
                      mixc(rng, (70, 48, 60), (98, 74, 56), 14 if lod == 0 else 4))
    return g


def tamarix(seed, lod, H):
    rng = np.random.default_rng(seed)
    g = Geo()
    n = int(rng.integers(4, 8))
    stemc = lin((120, 86, 76))
    for i in range(n):
        d = dirs(rng.uniform(0, 2 * math.pi), math.radians(rng.uniform(55, 80)))
        L = H * rng.uniform(0.75, 1.05)
        st = path(rng, [*rng.normal(0, 0.15, 2), 0], d, L, 5, droop=0.3, wander=0.06)
        g.tubes(st[None], (np.linspace(0.022, 0.006, len(st)))[None], 3, stemc)
        nb = int(L / (0.07 if lod == 0 else 0.16))
        ts = rng.uniform(0.25, 1.0, nb)
        q, qd = along(st, ts)
        U = unit(qd * 0.4 + rng.normal(0, 0.7, (nb, 3)) + [0, 0, -0.25])
        Lb = rng.uniform(0.25, 0.55, nb)
        if lod == 0:                      # each branchlet several fine sprays
            k = 5
            B = np.repeat(q, k, 0) + rng.normal(0, 0.05, (nb * k, 3))
            UU = unit(np.repeat(U, k, 0) + rng.normal(0, 0.35, (nb * k, 3)))
            LL = np.repeat(Lb, k) * rng.uniform(0.5, 1.0, nb * k)
            g.leaves(B, UU, perp(UU, rng), LL, np.full(nb * k, 0.018), mixc(rng, (98, 126, 104), (136, 156, 128), nb * k),
                     widest=0.5, fold=0.0)
        else:
            g.leaves(q, U, perp(U, rng), Lb, np.full(nb, 0.07), mixc(rng, (98, 126, 104), (136, 156, 128), nb), widest=0.5)
        top = ts > 0.6
        for j in np.nonzero(top)[0][: (12 if lod == 0 else 4)]:
            g.cluster(rng, q[j] + U[j] * Lb[j] * 0.6, U[j] * 0.3 + [0, 0, 0.7], 0.18, 0.04, 16 if lod == 0 else 5, 0.03,
                      0.012, mixc(rng, (196, 134, 150), (226, 172, 184), 16 if lod == 0 else 5))
    return g


# ---------------------------------------------------------------- marsh

def reed(seed, lod, H):
    """Phragmites australis: a clump of culms, some of last year's standing dry."""
    rng = np.random.default_rng(seed)
    g = Geo()
    n = int(rng.integers(14, 26)) if lod == 0 else int(rng.integers(7, 11))
    for i in range(n):
        dry = rng.random() < 0.25
        h = H * rng.uniform(0.7, 1.0)
        base = np.array([*rng.normal(0, 0.28, 2), 0.0])
        lean = rng.uniform(0.0, 0.12)
        la = rng.uniform(0, 2 * math.pi)
        st = path(rng, base, [math.sin(lean) * math.cos(la), math.sin(lean) * math.sin(la), 1.0], h, 4, wander=0.02,
                  droop=0.03)
        culm = lin((176, 160, 118)) if dry else lin((118, 132, 82))
        g.tubes(st[None], np.full((1, len(st)), 0.0045), 3, culm)
        nl = (int(rng.integers(3, 6)) if dry else int(rng.integers(8, 13))) if lod == 0 else (2 if dry else 5)
        ts = np.sort(rng.uniform(0.15, 0.85, nl))
        q, _ = along(st, ts)
        az = rng.uniform(0, 2 * math.pi) + np.arange(nl) * math.pi + rng.normal(0, 0.4, nl)
        D = dirs(az, np.radians(rng.uniform(25, 60, nl)))
        col = mixc(rng, (166, 150, 108), (196, 178, 132), nl) if dry else mixc(rng, (96, 118, 66), (142, 152, 92), nl)
        g.blades(q, D, rng.uniform(0.25, 0.42, nl), rng.uniform(0.016, 0.026, nl), rng.uniform(1.5, 3.2, nl) * (1.5 if dry else 1),
                 col, segs=4 if lod == 0 else 2, rng=rng)
        top, td_ = along(st, 1.0)
        pc = mixc(rng, (182, 170, 140), (206, 192, 160), 1)[0] if dry else mixc(rng, (112, 88, 82), (160, 132, 110), 1)[0]
        g.cluster(rng, top - td_ * 0.02, unit(td_ + [rng.normal(0, 0.2), rng.normal(0, 0.2), -0.25]),
                  rng.uniform(0.22, 0.36), 0.065, 44 if lod == 0 else 7, 0.065, 0.016, pc, up=-0.3)
    return g


def typha(seed, lod, H):
    rng = np.random.default_rng(seed)
    g = Geo()
    nl = int(rng.integers(14, 24)) if lod == 0 else 7
    B = np.column_stack([rng.normal(0, 0.12, nl), rng.normal(0, 0.12, nl), np.zeros(nl)])
    D = dirs(rng.uniform(0, 2 * math.pi, nl), np.radians(rng.uniform(72, 86, nl)))
    g.blades(B, D, H * rng.uniform(0.7, 1.05, nl), rng.uniform(0.013, 0.02, nl), rng.uniform(0.08, 0.3, nl),
             mixc(rng, (96, 116, 70), (140, 148, 92), nl), segs=6 if lod == 0 else 3, taper=4.0, rng=rng)
    for i in range(int(rng.integers(2, 5))):
        h = H * rng.uniform(0.75, 0.95)
        st = path(rng, [*rng.normal(0, 0.1, 2), 0], [rng.normal(0, 0.04), rng.normal(0, 0.04), 1], h, 3, wander=0.01)
        g.tubes(st[None], np.full((1, len(st)), 0.005), 3, lin((128, 136, 88)))
        top, td_ = along(st, 0.92)
        sp = np.array([top, top + td_ * rng.uniform(0.15, 0.24)])
        g.tubes(sp[None], np.full((1, 2), rng.uniform(0.011, 0.015)), 6 if lod == 0 else 4, mixc(rng, (84, 58, 42), (112, 80, 56), 1)[0])
    return g


# ---------------------------------------------------------------- herbs and grasses

def tallgrass(seed, lod, H):
    rng = np.random.default_rng(seed)
    g = Geo()
    nb = int(rng.integers(30, 50)) if lod == 0 else 10
    B = np.column_stack([rng.normal(0, 0.07, nb), rng.normal(0, 0.07, nb), np.zeros(nb)])
    D = dirs(rng.uniform(0, 2 * math.pi, nb), np.radians(rng.uniform(50, 82, nb)))
    straw = rng.random(nb) < 0.3
    col = np.where(straw[:, None], mixc(rng, (168, 152, 108), (196, 180, 134), nb), mixc(rng, (98, 116, 64), (146, 150, 90), nb))
    g.blades(B, D, H * rng.uniform(0.35, 0.7, nb), rng.uniform(0.006, 0.011, nb), rng.uniform(0.6, 1.6, nb), col,
             segs=4 if lod == 0 else 2, rng=rng)
    nc = int(rng.integers(4, 10)) if lod == 0 else 3
    pan = [(150, 128, 132), (182, 168, 136), (196, 186, 150)][seed % 3]
    for i in range(nc):
        h = H * rng.uniform(0.8, 1.05)
        st = path(rng, [*rng.normal(0, 0.06, 2), 0], [rng.normal(0, 0.12), rng.normal(0, 0.12), 1], h, 3, droop=0.1,
                  wander=0.03)
        g.tubes(st[None], np.full((1, len(st)), 0.0025), 3, lin((150, 150, 100)))
        top, td_ = along(st, 1.0)
        g.cluster(rng, top - td_ * 0.18, td_, 0.2, 0.03, 18 if lod == 0 else 4, 0.035, 0.008,
                  mixc(rng, pan, np.minimum(np.array(pan) + 25, 255), 18 if lod == 0 else 4))
    return g


def broadleaf(seed, lod, H):
    """var 0-1 Xanthium orientale (big leaves, burrs), 2-3 Chenopodium album (smaller mealy leaves, seed clusters)."""
    rng = np.random.default_rng(seed)
    xan = seed % 4 < 2
    g = Geo()
    ns = int(rng.integers(2, 5))
    for i in range(ns):
        h = H * rng.uniform(0.7, 1.0)
        st = path(rng, [*rng.normal(0, 0.08, 2), 0], [rng.normal(0, 0.1), rng.normal(0, 0.1), 1], h, 4, wander=0.05)
        g.tubes(st[None], (np.linspace(0.009, 0.003, len(st)))[None], 3,
                lin((120, 110, 80)) if xan else lin((136, 120, 96)))
        nl = (int(rng.integers(16, 24)) if lod == 0 else 7)
        ts = np.sort(rng.uniform(0.1, 0.95, nl))
        q, qd = along(st, ts)
        U = unit(dirs(rng.uniform(0, 2 * math.pi, nl), np.radians(rng.uniform(-30, 20, nl))))
        L = (rng.uniform(0.09, 0.16, nl) if xan else rng.uniform(0.05, 0.09, nl)) * (1.3 - 0.6 * ts)
        col = mixc(rng, (66, 94, 44), (110, 128, 66), nl) if xan else mixc(rng, (104, 122, 84), (146, 154, 118), nl)
        col *= (0.6 + 0.4 * ts)[:, None]
        g.leaves(q + U * 0.03, U, perp(U, rng), L, L * (0.95 if xan else 0.7), col, widest=0.4, fold=0.15)
        nb = 10 if lod == 0 else 3
        tq, _ = along(st, rng.uniform(0.5, 1.0, nb))
        for j in range(nb):
            g.cluster(rng, tq[j], [rng.normal(0, 0.5), rng.normal(0, 0.5), 0.6], 0.07, 0.025, 9 if lod == 0 else 3,
                      0.014 if xan else 0.009, 0.011 if xan else 0.007,
                      mixc(rng, (110, 110, 60), (140, 128, 76), 9 if lod == 0 else 3) if xan
                      else mixc(rng, (150, 150, 112), (172, 164, 124), 9 if lod == 0 else 3))
    return g


def artemisia(seed, lod, H):
    rng = np.random.default_rng(seed)
    g = Geo()
    for i in range(int(rng.integers(3, 7))):
        h = H * rng.uniform(0.7, 1.0)
        st = path(rng, [*rng.normal(0, 0.1, 2), 0], [rng.normal(0, 0.08), rng.normal(0, 0.08), 1], h, 4, wander=0.03)
        g.tubes(st[None], (np.linspace(0.008, 0.003, len(st)))[None], 3, lin((120, 92, 82)))
        nl = int(rng.integers(34, 50)) if lod == 0 else 9
        ts = np.sort(rng.uniform(0.08, 0.85, nl))
        q, _ = along(st, ts)
        U = unit(dirs(rng.uniform(0, 2 * math.pi, nl), np.radians(rng.uniform(-10, 40, nl))))
        L = rng.uniform(0.06, 0.1, nl) * (1.25 - 0.55 * ts)
        under = rng.random(nl) < 0.35
        col = np.where(under[:, None], mixc(rng, (132, 142, 124), (150, 158, 140), nl), mixc(rng, (82, 100, 72), (116, 128, 100), nl))
        g.leaves(q, U, perp(U, rng), L, L * 0.45, col, widest=0.4, fold=0.2)
        top, td_ = along(st, 0.78)
        g.cluster(rng, top, td_, h * 0.26, 0.09, 50 if lod == 0 else 8, 0.02, 0.008,
                  mixc(rng, (132, 104, 82), (166, 136, 104), 50 if lod == 0 else 8), up=0.2)
    return g


def flowering(seed, lod, H):
    """var 0-1 Lythrum salicaria (magenta), 2 Melilotus albus (white), 3 Epilobium hirsutum (pink)."""
    rng = np.random.default_rng(seed)
    v = seed % 4
    fl = {0: ((158, 56, 118), (196, 92, 150)), 1: ((150, 60, 120), (186, 98, 156)), 2: ((214, 210, 186), (232, 228, 204)),
          3: ((196, 110, 150), (222, 146, 178))}[v]
    g = Geo()
    for i in range(int(rng.integers(3, 8))):
        h = H * rng.uniform(0.65, 1.0)
        st = path(rng, [*rng.normal(0, 0.09, 2), 0], [rng.normal(0, 0.12), rng.normal(0, 0.12), 1], h, 4, wander=0.04)
        g.tubes(st[None], (np.linspace(0.006, 0.0025, len(st)))[None], 3, lin((120, 112, 82)))
        nl = int(rng.integers(18, 28)) if lod == 0 else 6
        ts = np.sort(rng.uniform(0.1, 0.72, nl))
        q, _ = along(st, ts)
        U = unit(dirs(rng.uniform(0, 2 * math.pi, nl), np.radians(rng.uniform(-5, 35, nl))))
        L = rng.uniform(0.05, 0.09, nl) if v != 2 else rng.uniform(0.025, 0.04, nl)
        g.leaves(q, U, perp(U, rng), L, L * (0.3 if v != 2 else 0.5), mixc(rng, (70, 96, 52), (112, 128, 72), nl), widest=0.4)
        top, td_ = along(st, 0.72)
        n = 70 if lod == 0 else 10
        L, W = (0.024, 0.016) if v != 2 else (0.012, 0.008)
        g.cluster(rng, top, td_, h * 0.32, 0.035 if v != 2 else 0.06, n, L, W, mixc(rng, *fl, n), up=0.3)
    return g


def dry(seed, lod, H):
    rng = np.random.default_rng(seed)
    g = Geo()
    for i in range(int(rng.integers(4, 9))):
        h = H * rng.uniform(0.6, 1.0)
        lean = rng.uniform(0.0, 0.5 if rng.random() < 0.3 else 0.15)
        la = rng.uniform(0, 2 * math.pi)
        st = path(rng, [*rng.normal(0, 0.1, 2), 0], [math.sin(lean) * math.cos(la), math.sin(lean) * math.sin(la), math.cos(lean)],
                  h, 4, wander=0.03)
        c = mixc(rng, (156, 136, 100), (194, 176, 134), 1)[0]
        g.tubes(st[None], (np.linspace(0.006, 0.0025, len(st)))[None], 3, c)
        nb = 16 if lod == 0 else 5
        ts = rng.uniform(0.45, 0.98, nb)
        q, qd = along(st, ts)
        D = unit(qd * 0.6 + rng.normal(0, 0.5, (nb, 3)) + [0, 0, 0.3])
        tips = q + D * rng.uniform(0.05, 0.18, nb)[:, None]
        P = np.stack([q, (q + tips) / 2, tips], 1)
        g.tubes(P, np.full((nb, 3), 0.0018), 3, c * 0.95)
        for j in range(nb if lod == 0 else 0):
            g.cluster(rng, tips[j], D[j], 0.03, 0.008, 5, 0.009, 0.006, mixc(rng, (170, 150, 112), (204, 188, 150), 5))
        nl = 4 if lod == 0 else 0
        if nl:
            q2, _ = along(st, rng.uniform(0.1, 0.5, nl))
            U = unit(dirs(rng.uniform(0, 2 * math.pi, nl), np.radians(rng.uniform(-60, -20, nl))))
            g.leaves(q2, U, perp(U, rng), np.full(nl, 0.05), np.full(nl, 0.01), mixc(rng, (130, 108, 76), (160, 136, 96), nl))
    return g


def grass(seed, lod, H):
    rng = np.random.default_rng(seed)
    g = Geo()
    nb = int(rng.integers(40, 70)) if lod == 0 else 14
    B = np.column_stack([rng.normal(0, 0.09, nb), rng.normal(0, 0.09, nb), np.zeros(nb)])
    D = dirs(rng.uniform(0, 2 * math.pi, nb), np.radians(rng.uniform(45, 85, nb)))
    straw = rng.random(nb) < [0.15, 0.3, 0.45, 0.25][seed % 4]
    col = np.where(straw[:, None], mixc(rng, (164, 150, 104), (196, 182, 136), nb), mixc(rng, (90, 110, 58), (148, 152, 92), nb))
    g.blades(B, D, H * rng.uniform(0.45, 1.0, nb), rng.uniform(0.004, 0.008, nb), rng.uniform(0.8, 2.2, nb), col,
             segs=3 if lod == 0 else 2, rng=rng)
    if seed % 2 == 0 and lod == 0:
        for i in range(int(rng.integers(2, 6))):
            st = path(rng, [*rng.normal(0, 0.06, 2), 0], [rng.normal(0, 0.2), rng.normal(0, 0.2), 1], H * rng.uniform(0.9, 1.25), 2,
                      droop=0.2, wander=0.05)
            g.tubes(st[None], np.full((1, len(st)), 0.0015), 3, lin((170, 160, 116)))
            top, td_ = along(st, 1.0)
            g.cluster(rng, top - td_ * 0.06, td_, 0.07, 0.012, 8, 0.016, 0.006, mixc(rng, (170, 156, 120), (200, 186, 146), 8))
    return g



def crown(kind, seed, H):
    """LOD 3, far off (over about 1.2 km, where a tree is a few pixels): a trunk and ten broad leaf cards round an
    ellipsoid crown, in the same leaf colours and drawn occlusion as the nearer levels."""
    rng = np.random.default_rng(seed)
    g = Geo()
    willow = kind == "willow"
    g.tubes(np.array([[[0, 0, 0], [0, 0, H * 0.45]]]), np.array([[0.09, 0.05]]) * H / 6.5, 3,
            lin((104, 98, 86)) if willow else lin((120, 116, 102)))
    n = 10
    rad, top = (0.32 if willow else 0.24) * H, H
    c0 = np.array([0.0, 0.0, H * (0.62 if willow else 0.6)])
    a = rng.uniform(0, 2 * math.pi, n)
    e = rng.uniform(-0.6, 0.8, n)
    pos = c0 + np.stack([np.cos(a) * np.cos(e) * rad, np.sin(a) * np.cos(e) * rad,
                         np.sin(e) * (top - c0[2]) * 0.9], 1)
    U = unit(np.stack([np.cos(a), np.sin(a), np.full(n, 0.9)], 1) + rng.normal(0, 0.3, (n, 3)))
    L = np.full(n, rad * 1.5)
    B = pos - U * L[:, None] * 0.5
    c = shade_crown(pos, np.zeros(3), H, leaf_colours(rng, kind, n) * 0.95)
    g.leaves(B, U, perp(U, rng), L, L * 0.85, c, widest=0.5, fold=0.3)
    return g

# family: (name, builder, model height m, lods)
FAMILIES = {
    0: ("white willow", lambda s, l, H: tree("willow", s, l, H), 6.5, (0, 1, 2)),
    1: ("black poplar", lambda s, l, H: tree("poplar", s, l, H), 7.5, (0, 1, 2)),
    2: ("saplings", sapling, 3.0, (0, 1)),
    3: ("Amorpha fruticosa", amorpha, 2.0, (0, 1)),
    4: ("Tamarix ramosissima", tamarix, 2.6, (0, 1)),
    5: ("Phragmites australis", reed, 3.0, (0, 1)),
    6: ("Typha", typha, 2.0, (0, 1)),
    7: ("tall grasses", tallgrass, 1.1, (0, 1)),
    8: ("Xanthium, Chenopodium", broadleaf, 1.0, (0, 1)),
    9: ("Artemisia", artemisia, 1.4, (0, 1)),
    10: ("Lythrum, Melilotus, Epilobium", flowering, 1.2, (0, 1)),
    11: ("dry stalks", dry, 1.0, (0, 1)),
    12: ("low grasses", grass, 0.5, (0, 1)),
}


if __name__ == "__main__":
    import time
    for f, (name, fn, H, lods) in FAMILIES.items():
        for lod in lods:
            t = time.time()
            V, F, C, K = fn(100 * f + 1, lod, H).arrays()
            print(f, name, "lod", lod, "verts", len(V), "tris", len(F), "%.2fs" % (time.time() - t))
