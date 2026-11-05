"""Distant birds for the v4 shot `under-the-crossing` (the user, 5 November 2026: "animate birds flying in the distance
to give a broader sense of immersion"). Drawn, not observed: the species are ones recorded on or over the bed and at
these crossings, their shapes and flight are representative (span, body, wingbeat and speed typical of each), and the
paths are composed for the frame: in the open sky either side of the line, never in front of the tower or the wires
and never across a conductor (checked against `mask.npy`, every line's wires and every tower in frame, by `check`).

Species (sources in v4.json):
  bee-eater   Merops apiaster: heard in the soundscape's reeds layer (iNat 361466739, Vasyliuk, Mar'ianske, on the bed,
              14 May 2026). Small loose groups, flurries of quick wingbeats between glides. Span 0.45 m.
  cormorant   Phalacrocorax carbo: 1,240 nests on six towers of these crossings in 2012 (Sidorenko & Siokhin 2016);
              nothing counted since. A slow line, steady wingbeats, neck out. Span 1.4 m. Drawn far off and flying
              away, never at a tower: no colony is shown or implied.
  gull        Larus cachinnans (Caspian gull): nested on the crossing in 2012 (the same survey). Long glides, a few
              slow beats. Span 1.42 m.

Used inside Blender by still_v4.py (Flock.mesh) and alone to plan and check:

    python -I birds_v4.py check <mask.npy> <still.png> <out.png>      (the paths drawn on a still, and the check)
"""
import json
import math
import sys
import zlib

import numpy as np

FRAMES, FPS = 900, 30
W, H = 1920, 1080
CAM = dict(lens=18.0, pitch=15.0)

# span, body length, wing chord at the root, wingbeat Hz, beat amplitude (deg), glide dihedral (deg), speed m/s,
# flap pattern (seconds flapping, seconds gliding; None: always), colour (sRGB, before the haze)
SPECIES = {
    "bee-eater": dict(span=0.45, body=0.27, chord=0.075, hz=6.0, amp=38, dihedral=4, speed=9.0, pattern=(0.7, 0.9),
                      neck=0.02, tail=0.09, rgb=(64, 60, 50), hand=0.55, sweep=0.35),
    "cormorant": dict(span=1.40, body=0.85, chord=0.22, hz=4.2, amp=26, dihedral=0, speed=14.0, pattern=None,
                      neck=0.28, tail=0.12, rgb=(38, 38, 40), hand=0.5, sweep=0.12),
    "gull": dict(span=1.42, body=0.60, chord=0.19, hz=2.6, amp=30, dihedral=6, speed=9.5, pattern=(1.2, 4.5),
                 neck=0.08, tail=0.1, rgb=(118, 118, 122), hand=0.55, sweep=0.45),
}
HAZE = (222, 200, 186)     # the dawn haze (still_v4): birds are tinted toward it with distance, a drawn aerial haze

# control points on the screen (x, y px of the 1920x1080 frame) and their distance from the eye (m), turned into
# camera-relative points (X right of the axis, Y ahead along it, Z above the eye) and joined by a spline in 3D; t0 when
# the first bird is at the first point. Members: offsets (along, side, up) m and a delay s. Every path starts and
# ends off the frame or behind the trees, or runs past the shot's end.
GROUPS = [
    dict(id="bee-eaters left", species="bee-eater", t0=1.0,
         screen=[(-60, 520, 55), (250, 430, 60), (520, 380, 66), (640, 330, 72), (560, 260, 78), (380, 240, 74),
                 (180, 280, 66), (-220, 330, 60)],
         members=[(0, 0, 0, 0), (-2.5, 1.8, 0.6, 0.35), (-4.0, -2.2, -0.8, 0.6), (-6.5, 0.8, 1.4, 1.0),
                  (-9.0, -1.0, 0.2, 1.5)]),
    dict(id="cormorants", species="cormorant", t0=4.0,
         screen=[(-80, 420, 260), (300, 430, 250), (560, 470, 260), (700, 540, 300), (640, 640, 420),
                 (570, 745, 600), (540, 800, 800)],
         members=[(0, 0, 0, 0), (-3.5, -2.4, 0.2, 0.2), (-7.0, -4.8, 0.4, 0.4), (-10.5, -7.2, 0.6, 0.6),
                  (-14.0, -9.6, 0.5, 0.8), (-17.5, -12.0, 0.8, 1.0)]),
    dict(id="gull", species="gull", t0=5.0,
         screen=[(1500, -40, 170), (1420, 120, 160), (1330, 260, 165), (1360, 360, 175), (1480, 380, 185),
                 (1560, 300, 190), (1530, 180, 195), (1450, 60, 200), (1400, -60, 210)],
         members=[(0, 0, 0, 0)]),
    dict(id="bee-eaters right", species="bee-eater", t0=16.0,
         screen=[(2000, 330, 58), (1700, 300, 62), (1450, 280, 66), (1300, 230, 70), (1380, 170, 72),
                 (1600, 160, 68), (2160, 200, 62)],
         members=[(0, 0, 0, 0), (-2.2, -1.6, 0.5, 0.4), (-4.5, 1.4, -0.4, 0.9)]),
    dict(id="gull far", species="gull", t0=10.0,
         screen=[(-60, 300, 420), (200, 290, 430), (420, 300, 450), (560, 250, 470), (600, 180, 480),
                 (520, 80, 500), (420, -60, 520)],
         members=[(0, 0, 0, 0)]),
]


def unproject(x, y, d, pitch, lens):
    """A screen point at a distance from the eye, as a camera-relative point (X right, Y ahead, Z up)."""
    p = math.radians(pitch)
    f = lens / 36.0
    fwd = np.array([0.0, math.cos(p), math.sin(p)])
    up = np.array([0.0, -math.sin(p), math.cos(p)])
    r = fwd + np.array([1.0, 0, 0]) * (x / W - 0.5) / f + up * (0.5 - y / H) * (H / W) / f
    return r / np.linalg.norm(r) * d


def catmull(P, n=60):
    P = np.asarray(P, float)
    P = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        t = np.linspace(0, 1, n, endpoint=False)[:, None]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t ** 2
                          + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-2][None])
    return np.vstack(out)


class Flock:
    def __init__(self, cam, heading, ground, view):
        h = math.radians(heading)
        self.ax = np.array([math.sin(h), math.cos(h), 0.0])
        self.nrm = np.array([math.cos(h), -math.sin(h), 0.0])
        self.up = np.array([0.0, 0.0, 1.0])
        self.eye = np.array([cam[0], cam[1], ground + view["eye"]])
        self.birds = []
        for g in GROUPS:
            sp = SPECIES[g["species"]]
            pts = [unproject(x, y, d, view.get("pitch", CAM["pitch"]), view.get("lens", CAM["lens"]))
                   for x, y, d in g["screen"]]
            C = catmull(pts)
            seg = np.linalg.norm(np.diff(C, axis=0), axis=1)
            s = np.concatenate([[0], np.cumsum(seg)])
            for i, (da, ds, du, dt) in enumerate(g["members"]):
                rng = np.random.default_rng(zlib.crc32(f"{g['id']} {i}".encode()))
                self.birds.append(dict(group=g["id"], species=g["species"], sp=sp, C=C, s=s, t0=g["t0"] + dt,
                                       off=(da, ds, du), phase=rng.uniform(0, 1), wander=rng.uniform(0, 2 * math.pi),
                                       hz=sp["hz"] * rng.uniform(0.92, 1.08)))

    def world(self, Q):
        return self.eye + Q[..., 0:1] * self.nrm + Q[..., 1:2] * self.ax + Q[..., 2:3] * self.up

    def state(self, b, t):
        """Position (camera-relative), forward unit vector, or None when the bird is not on its path."""
        d = (t - b["t0"]) * b["sp"]["speed"]
        if d < 0 or d > b["s"][-1]:
            return None
        C, s = b["C"], b["s"]
        j = min(np.searchsorted(s, d) - 1, len(C) - 2)
        j = max(j, 0)
        f = (d - s[j]) / max(s[j + 1] - s[j], 1e-9)
        p = C[j] * (1 - f) + C[j + 1] * f
        fw = C[j + 1] - C[j]
        fw = fw / np.linalg.norm(fw)
        side = np.cross([0, 0, 1.0], fw)
        side /= max(np.linalg.norm(side), 1e-9)
        da, ds, du = b["off"]
        w = 0.5 * math.sin(0.9 * t + b["wander"])                 # a loose group: each drifts a little
        p = p + fw * da + side * (ds + w) + np.array([0, 0, du + 0.3 * math.cos(1.3 * t + b["wander"])])
        return p, fw

    def flap(self, b, t):
        sp = b["sp"]
        ph = 2 * math.pi * (b["hz"] * t + b["phase"])
        if sp["pattern"]:
            a, g = sp["pattern"]
            c = (t + b["phase"] * (a + g)) % (a + g)
            if c > a:                                              # gliding: wings held, a slight dihedral
                return math.radians(sp["dihedral"]), 0.0
        ang = math.radians(sp["amp"]) * math.sin(ph) + math.radians(sp["dihedral"])
        return ang, math.sin(ph)

    def shape(self, b, t, p, fw):
        """The bird's triangles in camera-relative metres: a body cross and two two-panel wings."""
        sp = b["sp"]
        side = np.cross([0, 0, 1.0], fw); side /= max(np.linalg.norm(side), 1e-9)
        up = np.cross(fw, side)
        ang, beat = self.flap(b, t)
        hs = sp["span"] / 2
        L, c = sp["body"], sp["chord"]
        nose = p + fw * (L * 0.5 + sp["neck"])
        tail = p - fw * (L * 0.5 + sp["tail"])
        bw = c * 0.32
        V = [nose, p + side * bw, tail, p - side * bw, p + up * bw * 0.8, p - up * bw * 0.8]
        F = [(0, 1, 2), (0, 2, 3), (0, 4, 2), (0, 2, 5)]
        for sgn in (1, -1):
            sd = side * sgn
            a1 = ang
            a2 = ang * 1.5 - 0.15 * beat                            # the hand flexes more than the arm
            r1 = hs * sp["hand"]
            arm = sd * math.cos(a1) + up * math.sin(a1)
            elbow = p + arm * r1 + fw * c * 0.1
            hand = sd * math.cos(a2) + up * math.sin(a2)
            tip = elbow + hand * (hs - r1) - fw * c * sp["sweep"] * 1.6
            s0 = p + fw * c * 0.35
            s1 = p - fw * c * 0.65
            e0 = elbow + fw * c * 0.25
            e1 = elbow - fw * c * 0.75
            k = len(V)
            V += [s0, s1, e0, e1, tip]
            F += [(k, k + 2, k + 1), (k + 1, k + 2, k + 3), (k + 2, k + 4, k + 3)]
        return np.array(V), np.array(F)

    def colour(self, b, dist):
        k = 0.1 + 0.45 * (1 - math.exp(-dist / 900.0))
        c = np.array(b["sp"]["rgb"], float) * (1 - k) + np.array(HAZE, float) * k
        return lin(c)

    def mesh(self, t):
        Vs, Fs, Cs, n = [], [], [], 0
        for b in self.birds:
            st = self.state(b, t)
            if st is None:
                continue
            p, fw = st
            V, F = self.shape(b, t, p, fw)
            Vs.append(self.world(V)); Fs.append(F + n); n += len(V)
            Cs.append(np.repeat(self.colour(b, float(np.linalg.norm(p)))[None], len(F), 0))
        if not Fs:
            return np.zeros((0, 3)), np.zeros((0, 3), np.int64), np.zeros((0, 3))
        return np.vstack(Vs), np.vstack(Fs), np.vstack(Cs)

    def all_points(self, ts):
        out = []
        for t in ts:
            for b in self.birds:
                st = self.state(b, t)
                if st is not None:
                    out.append(self.world(st[0]))
        return np.array(out) if out else np.zeros((0, 3))


def lin(c):
    c = np.asarray(c, float) / 255
    return np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)


def screen(Q):
    """Camera-relative points to pixels (the still camera: pitch up, lens on a 36 mm wide sensor)."""
    p = math.radians(CAM["pitch"])
    Q = np.atleast_2d(Q)
    fwd = Q[:, 1] * math.cos(p) + Q[:, 2] * math.sin(p)
    upc = -Q[:, 1] * math.sin(p) + Q[:, 2] * math.cos(p)
    f = CAM["lens"] / 36.0
    x = (0.5 + f * Q[:, 0] / fwd) * W
    y = (0.5 - f * upc / fwd * W / H) * H
    return x, y, fwd


def check(mask_path, still, out):
    from PIL import Image, ImageDraw
    mask = np.load(mask_path)
    # a margin round every wire and tower: birds keep at least this far (px)
    pad = 28
    m = mask.copy()
    ys, xs = np.nonzero(mask)
    for dy in range(-pad, pad + 1, 4):
        for dx in range(-pad, pad + 1, 4):
            if dx * dx + dy * dy <= pad * pad:
                m[np.clip(ys + dy, 0, H - 1), np.clip(xs + dx, 0, W - 1)] = True
    fl = Flock((0, 0), 0.0, -1.6, {"eye": 1.6, **CAM})
    im = Image.open(still).convert("RGB")
    ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(ov)
    dr.bitmap((0, 0), Image.fromarray((m * 60).astype(np.uint8)), fill=(255, 0, 0, 60))
    report = {"pad_px": pad, "groups": {}}
    cols = {"bee-eater": (255, 220, 0, 255), "cormorant": (0, 0, 0, 255), "gull": (255, 255, 255, 255)}
    hits = 0
    for b in fl.birds:
        xs_, ys_, inf, shown, first, last = [], [], 0, 0, None, None
        for k in range(FRAMES):
            st = fl.state(b, k / FPS)
            if st is None:
                continue
            x, y, d = screen(st[0])
            x, y = float(x[0]), float(y[0])
            ins = 0 <= x < W and 0 <= y < H
            if ins:
                shown += 1
                first = k if first is None else first
                last = k
                if m[int(y), int(x)]:
                    inf += 1
            xs_.append(x); ys_.append(y)
        hits += inf
        dr.line(list(zip(xs_, ys_)), fill=cols[b["species"]], width=2)
        g = report["groups"].setdefault(b["group"], {"species": b["species"], "birds": 0, "frames_in_frame": [],
                                                    "frames_near_wires_or_tower": 0, "enters_s": None, "leaves_s": None,
                                                    "distance_m": [1e9, 0], "size_px": [1e9, 0]})
        g["birds"] += 1
        g["frames_in_frame"].append(shown)
        g["frames_near_wires_or_tower"] += inf
        P = np.array([fl.state(b, k / FPS)[0] for k in range(FRAMES) if fl.state(b, k / FPS) is not None])
        if len(P):
            dist = np.linalg.norm(P, axis=1)
            g["distance_m"] = [round(min(g["distance_m"][0], dist.min()), 1), round(max(g["distance_m"][1], dist.max()), 1)]
            px = b["sp"]["span"] / dist * (CAM["lens"] / 36.0) * W
            g["size_px"] = [round(min(g["size_px"][0], px.min()), 1), round(max(g["size_px"][1], px.max()), 1)]
        tend = b["t0"] + b["s"][-1] / b["sp"]["speed"]
        for tt, what in ((b["t0"], "starts"), (tend, "ends")):
            if 0 < tt < FRAMES / FPS:
                x, y, d = screen(fl.state(b, min(max(tt, b["t0"]), tend - 1e-6))[0])
                g.setdefault("ends_at_px", []).append([what, round(tt, 2), round(float(x[0])), round(float(y[0]))])
        if first is not None:
            e = round(first / FPS, 2) if first > 0 else 0.0
            l_ = round((last + 1) / FPS, 2)
            g["enters_s"] = e if g["enters_s"] is None else min(g["enters_s"], e)
            g["leaves_s"] = l_ if g["leaves_s"] is None else max(g["leaves_s"], l_)
    im = Image.alpha_composite(im.convert("RGBA"), ov).convert("RGB")
    im.save(out)
    report["frames_near_wires_or_tower"] = hits
    print(json.dumps(report, indent=1))
    json.dump(report, open(out.rsplit(".", 1)[0] + ".json", "w"), indent=1)


if __name__ == "__main__":
    if sys.argv[1] == "check":
        check(*sys.argv[2:5])
