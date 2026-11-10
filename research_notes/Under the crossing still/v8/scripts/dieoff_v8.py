"""The plants' dying in the v8 `drowning` (the user, 8 November 2026): each plant starts to die when the drawn water
reaches its base (its roots drowned), in the shot's compressed time, and is gone (fallen, settled into the bed and
dissolved into the silt) by its kind's deadline, so the last seconds hold on water, the bed, the tower and the wires.
Plain numpy: used by still_v8.py inside Blender (the per-frame state of every plant) and by the notes outside it.

The water's level in time is v7's exactly (composite_v7.py: 9.0 m to 13.1 m over 0-10 s, eased 0.2 / 0.4).

Per plant, from t0 = (when the water reaches its base) + its kind's lag (jittered), in its kind's own seconds (all
scaled down together when a plant is reached too late to finish by its kind's deadline):
  dead   0 -> 1  colour: as modelled, to yellow-brown (0.5), to grey-brown (1); this one from the moment the water
                 reaches the base (so the plants are seen turning while the water rises)
  leaf   0 -> 1  leaves, blades and cards gone, each at its own moment (a share of them)
  twig   0 -> x  the finer stems gone, thinnest first (stems from the ground stay)
  tilt   0 -> a  the plant leaning over about its base and falling (eased in, as a fall, then settling)
  slump          its height squashed and its width spread (herbs wilting, reeds breaking)
  sink   0 -> d  settling down into the bed (the bed's surface hides what is under it)
  fade   0 -> 1  whatever is left dissolved (each element at its own moment), as it settles into the silt
All of it is drawn: the pace is compressed from years (see v8.json), the shapes and the order are a drawing of how
these plants die under water, not a simulation.
"""
import math

import numpy as np

FPS = 30
H0, LEVEL = 9.0, 13.1
RISE = (0.0, 10.0)
EASE_IN, EASE_OUT = 0.2, 0.4

REF_LUM = 0.16                       # a typical leaf's luminance (linear): the dying colours keep relative brightness
YELLOW_LEAF, YELLOW_STEM = (128, 114, 72), (118, 104, 82)     # yellow-brown (dying)
DEAD_LEAF, DEAD_STEM = (92, 82, 64), (88, 82, 72)            # grey-brown (dead)

HERBS = (7, 8, 9, 10, 11, 12)
REEDS = (5, 6)
SHRUBS = (2, 3, 4)
TREES = (0, 1)

# per kind: lag after the water reaches the base, then (start, end) of each phase in the kind's own seconds, the
# phases' end values, and the deadline (shot seconds) by which every plant of the kind is gone
KINDS = {
    "herbs": dict(fams=HERBS, lag=0.2, dead=(0.0, 1.5), leaf=(0.6, 2.2, 0.85), twig=(1.0, 2.2, 0.5),
                  tilt=(0.7, 2.4, (10, 45)), slump=(0.6, 2.5, 0.32, 1.3), sink=(1.8, 3.4), fade=(2.4, 3.4),
                  sink_m=lambda h: 0.6 * h + 0.15, deadline=10.0, stretch=1.4),
    "reeds": dict(fams=REEDS, lag=0.45, dead=(0.0, 1.9), leaf=(0.8, 2.7, 0.9), twig=(1.0, 2.0, 0.0),
                  tilt=(1.6, 3.4, (62, 88)), slump=(1.5, 2.6, 0.75, 1.1), sink=(3.1, 4.5), fade=(3.7, 4.5),
                  sink_m=lambda h: 0.3 * h + 0.45, deadline=11.4, stretch=1.35),
    "shrubs": dict(fams=SHRUBS, lag=0.9, dead=(0.0, 2.0), leaf=(1.0, 3.0, 1.0), twig=(2.2, 3.2, 0.55),
                   tilt=(2.8, 4.4, (50, 85)), slump=(2.8, 4.2, 0.65, 1.15), sink=(4.0, 5.5), fade=(4.6, 5.5),
                   sink_m=lambda h: 0.45 * h + 0.4, deadline=12.0, stretch=1.25),
    "trees": dict(fams=TREES, lag=1.3, dead=(0.0, 2.6), leaf=(1.2, 3.8, 1.0), twig=(3.0, 4.0, 0.55),
                  tilt=(3.8, 5.8, (68, 88)), slump=(4.4, 6.0, 0.85, 1.05), sink=(5.2, 7.2), fade=(6.0, 7.2),
                  sink_m=lambda h: 0.45 * h + 0.6, deadline=13.0, stretch=1.15),
}
# each kind's "stretch": its lag and phases drawn this much slower than written above (the first test cleared the
# view by about 8.5 s, leaving 6 s empty; stretched, the view clears by about 12.5 s, the trees last and spread out)
MIN_SCALE = 0.45                     # a plant reached late dies at most this much faster than its kind's pace
JITTER_LAG = 0.35                    # s, each plant's lag varied by up to this
JITTER_PACE = 0.12                   # each plant's pace varied by up to this share
WATER_IN = 0.8                       # s: v7 draws the water at full strength from here (under 9.0 m it fades in)
NEAR_M = 14.0                        # plants this near the eye fall away from it, never toward the lens


def lin(c):
    return tuple(((v / 255 + 0.055) / 1.055) ** 2.4 if v / 255 > 0.04045 else v / 255 / 12.92 for v in c)


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


_TS = np.linspace(RISE[0], RISE[1], 4001)
_HS = np.array([level_at(t) for t in _TS])


def submerged_at(z):
    """When the drawn level reached height z (s; 0 under the start, inf above the level)."""
    z = np.asarray(z, float)
    return np.where(z <= LEVEL, np.interp(z, _HS, _TS), np.inf)


def ss(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def ramp(t, a, b):
    return np.clip((t - a) / np.maximum(b - a, 1e-6), 0, 1)


def fall(p):
    """A fall's angle share: slow to tip, quicker as it goes (to 0.92 at 80%), then eased to rest (drag in water)."""
    p = np.clip(p, 0, 1)
    return np.where(p < 0.8, (p / 0.8) ** 2 * 0.92, 0.92 + 0.08 * ss((p - 0.8) / 0.2))


def euler_xyz(R):
    """Blender's XYZ Euler of rotation matrices R (n, 3, 3): R = Rz(c) Ry(b) Rx(a)."""
    b = np.arcsin(np.clip(-R[:, 2, 0], -1, 1))
    a = np.arctan2(R[:, 2, 1], R[:, 2, 2])
    c = np.arctan2(R[:, 1, 0], R[:, 0, 0])
    return a, b, c


class DieOff:
    def __init__(self, npz, seed=8):
        self.P = np.asarray(npz["P"], float)              # x, y, z, rot, scale, proto index (as still_v4.plants)
        self.fam = np.asarray(npz["fam"], int)
        self.h = np.asarray(npz["h"], float)
        self.eye = np.asarray(npz["eye"], float)
        n = len(self.P)
        rng = np.random.default_rng(seed)
        self.kind = np.empty(n, object)
        for k, K in KINDS.items():
            self.kind[np.isin(self.fam, K["fams"])] = k
        ground = self.P[:, 2] + 0.03
        # the water at the plant's base (its roots drowned); ground under the start level is reached once v7 has
        # faded the water in there (0.8 s)
        self.reach = np.maximum(submerged_at(ground), WATER_IN)
        self.lagj = rng.uniform(-1, 1, n) * JITTER_LAG
        self.pace = 1 + rng.uniform(-1, 1, n) * JITTER_PACE
        # fall direction: random; near the eye, away from it (within 100 degrees of straight away)
        away = np.arctan2(self.P[:, 1] - self.eye[1], self.P[:, 0] - self.eye[0])
        dist = np.hypot(self.P[:, 0] - self.eye[0], self.P[:, 1] - self.eye[1])
        phi = rng.uniform(-math.pi, math.pi, n)
        near = dist < NEAR_M
        phi[near] = away[near] + rng.uniform(-1, 1, near.sum()) * math.radians(100)
        self.phi, self.dist = phi, dist
        self.tilt_max = np.zeros(n)
        self.t0 = np.zeros(n)
        self.scale = np.ones(n)                            # each plant's own seconds per kind-second
        for k, K in KINDS.items():
            m = self.kind == k
            lo, hi = K["tilt"][2]
            self.tilt_max[m] = np.radians(rng.uniform(lo, hi, m.sum()))
            STRETCH = K["stretch"]
            total = K["fade"][1]
            t0 = self.reach[m] + np.maximum(K["lag"] + self.lagj[m], 0.0) * STRETCH     # never before the water
            sc = self.pace[m] * STRETCH
            # reached too late to finish at the kind's pace: faster (down to MIN_SCALE), then earlier (never
            # before the water reaches it)
            late = t0 + total * sc > K["deadline"]
            need = np.where(late, (K["deadline"] - t0) / total, sc)
            sc = np.where(late, np.maximum(need, MIN_SCALE * STRETCH), sc)
            t0 = np.where(late & (need < MIN_SCALE * STRETCH),
                          np.maximum(K["deadline"] - total * MIN_SCALE * STRETCH, self.reach[m]), t0)
            # a plant whose base the water never reaches (on ground above the level: far off, on the higher ground)
            # lives: it is left as it is
            never = ~np.isfinite(self.reach[m])
            t0 = np.where(never, np.inf, t0)
            self.t0[m], self.scale[m] = t0, sc
        self.never = ~np.isfinite(self.reach)

    def phases(self, t):
        """Each plant's phase values at shot time t."""
        n = len(self.P)
        out = {k: np.zeros(n) for k in ("dead", "leaf", "twig", "tilt", "sz", "sxy", "sink", "fade")}
        for k, K in KINDS.items():
            m = self.kind == k
            u = (t - self.t0[m]) / self.scale[m]           # the kind's own seconds since this plant began
            # the colour turns from the moment the water reaches the base (the roots drowned), before the rest
            ud = (t - self.reach[m]) / self.scale[m]
            out["dead"][m] = ss(ramp(ud, 0.0, K["dead"][1] + K["lag"]))
            out["leaf"][m] = ss(ramp(u, *K["leaf"][:2])) * K["leaf"][2]
            out["twig"][m] = ss(ramp(u, *K["twig"][:2])) * K["twig"][2]
            out["tilt"][m] = fall(ramp(u, *K["tilt"][:2])) * self.tilt_max[m]
            sl = ss(ramp(u, *K["slump"][:2]))
            out["sz"][m] = 1 + (K["slump"][2] - 1) * sl
            out["sxy"][m] = 1 + (K["slump"][3] - 1) * sl
            out["sink"][m] = ss(ramp(u, *K["sink"])) * K["sink_m"](self.h[m])
            out["fade"][m] = ramp(u, *K["fade"]) * 1.12          # past 1 + the leaf width: every element gone
        return out

    def state(self, k):
        """The scatter's per-plant values at shot frame k (positions, Euler rotation, scale, shader attributes)."""
        t = k / FPS
        ph = self.phases(t)
        n = len(self.P)
        a, phi, rot = ph["tilt"], self.phi, self.P[:, 3]
        # tilt about the horizontal axis k = z x u (u the fall direction), after the plant's own turn about z
        kx, ky = -np.sin(phi), np.cos(phi)
        ca, sa = np.cos(a), np.sin(a)
        K = np.zeros((n, 3, 3))
        K[:, 0, 2], K[:, 1, 2] = ky, -kx
        K[:, 2, 0], K[:, 2, 1] = -ky, kx
        I = np.eye(3)[None]
        KK = K @ K
        Rt = I + sa[:, None, None] * K + (1 - ca)[:, None, None] * KK
        cz, sz_ = np.cos(rot), np.sin(rot)
        Rz = np.zeros((n, 3, 3))
        Rz[:, 0, 0], Rz[:, 0, 1], Rz[:, 1, 0], Rz[:, 1, 1], Rz[:, 2, 2] = cz, -sz_, sz_, cz, 1
        rx, ry, rz = euler_xyz(Rt @ Rz)
        s = self.P[:, 4]
        co = self.P[:, :3].copy()
        co[:, 2] -= ph["sink"]
        return dict(co=co, rx=rx, ry=ry, rz=rz, sx=s * ph["sxy"], sy=s * ph["sxy"], sz=s * ph["sz"],
                    dead=ph["dead"], leaf=ph["leaf"], twig=ph["twig"], fade=ph["fade"])

    def summary(self):
        """When each kind starts and is gone (shot seconds), for the notes."""
        out = {}
        for k, K in KINDS.items():
            m = self.kind == k
            if not m.any():
                continue
            gone = self.t0[m] + K["fade"][1] * self.scale[m]
            out[k] = {"plants": int(m.sum()),
                      "water_at_base_s": [round(float(np.nanmin(self.reach[m])), 2),
                                          round(float(np.median(self.reach[m])), 2),
                                          round(float(np.max(np.where(np.isfinite(self.reach[m]), self.reach[m], 0))), 2)],
                      "first_starts_s": round(float(self.t0[m].min()), 2),
                      "median_starts_s": round(float(np.median(self.t0[m])), 2),
                      "median_gone_s": round(float(np.median(gone)), 2),
                      "last_gone_s": round(float(gone.max()), 2),
                      "sped_up": int((self.scale[m] < self.pace[m] * K["stretch"] - 1e-9).sum()),
                      "never_reached": int(self.never[m].sum())}
        return out
