"""Where the plants of the v3 stills stand (the shot `under-the-crossing`, the user, 5 November 2026: "add more trees,
vegetation, different types of plants ... should really look like nature is growing"). For each view in views.json,
plants are placed by the habitat the Sentinel-2 pass of 28 August 2025 shows at each spot (its own 10 m bands and its
own water mask), never on its water or within 26 m of a caisson; the heights are the sources' for 2025-26 (trees) or
typical for each species (the rest: README). The positions are a pattern drawn from 10 m pixels, not individual
plants; each plant's shape is representative (modelled, said so).

    python -I place_plants.py <views.json> <out_dir> [view ids ...]          (from the project root)

Habitat of a pixel (bands of the pass: green, NIR, SWIR; GNDVI = (NIR - green) / (NIR + green), NDMI = (NIR - SWIR) /
(NIR + SWIR)):
  water  the pass's own water mask (water.png over 0.3)
  reed   not water, GNDVI >= 0.35, within 30 m of water        (Kuzemko et al. 2025: "marshy vegetation")
  woody  GNDVI >= 0.6 and NDMI >= 0.18                          ("closed willow and poplar thickets")
  herbs  GNDVI 0.35 to 0.6 (or green but dry)                  (open, herb-covered bed)
  sand   GNDVI 0.2 to 0.35                                      ("sparse vegetation on shells and sands")
  bare   GNDVI under 0.2
Each plant reads its habitat at its own spot jittered by about 4 m, so the 10 m pixel edges blur into each other.

Columns saved (pts): x, y, z (FABDEM/the bed's 20 m grid; still_v3.py lays each on the scene's own ground), family,
rot, height, lod, variant. Families: 0 white willow, 1 black poplar, 2 willow/poplar saplings, 3 Amorpha fruticosa,
4 Tamarix ramosissima, 5 Phragmites australis, 6 Typha, 7 tall grasses, 8 broad-leaved herbs (Xanthium,
Chenopodium), 9 Artemisia, 10 flowering herbs (Lythrum, Melilotus, Epilobium), 11 dry stalks (Erigeron and the
year's dead herbs), 12 low grasses.
"""
import json, math, sys
import numpy as np
from PIL import Image

ZNPP = "libraries/conductive-seam/satellite/networks/znpp"
LON0, LAT0, KX, KZ = 34.5879012, 47.5085556, 75194.446, 110574.0
CAISSONS = [(3729, 4757), (3948, 5485), (4185, 6275), (4426, 7062), (4658, 7836),      # Ferosplavna 20-24
            (4154, 4955), (4511, 6137), (4866, 7318)]                                  # Dniprovska 23-25
HAB = ["water", "reed", "woody", "herbs", "sand", "bare"]

# heights (m): trees from the sources (README), the rest typical for the species (general floras, not measured here)
HEIGHT = {0: ("normal", 6.4, 1.2, 4.0, 9.0), 1: ("uniform", 6.5, 9.5), 2: ("uniform", 1.4, 4.0),
          3: ("uniform", 1.2, 2.6), 4: ("uniform", 1.6, 3.6), 5: ("uniform", 2.0, 3.6), 6: ("uniform", 1.5, 2.4),
          7: ("uniform", 0.6, 1.5), 8: ("uniform", 0.5, 1.5), 9: ("uniform", 0.9, 1.9), 10: ("uniform", 0.7, 1.6),
          11: ("uniform", 0.5, 1.4), 12: ("uniform", 0.2, 0.7)}

# layers: (name, families chosen by habitat, bands (spacing m, from, to, lod)), with p = chance of a plant per
# candidate point by habitat and the mix of families by habitat
LAYERS = [
    ("canopy", [(3.3, 0, 22, 0), (3.6, 22, 60, 1), (4.0, 60, 160, 1), (6.0, 160, 800, 2), (9.0, 800, 2500, 2)],
     {"reed": 0.06, "woody": 0.95, "herbs": 0.07, "sand": 0.02},
     {"reed": {0: 0.85, 1: 0.15}, "woody": {0: 0.78, 1: 0.22}, "herbs": {0: 0.75, 1: 0.25}, "sand": {0: 0.6, 1: 0.4}}),
    ("understorey", [(1.5, 0, 30, 0), (2.4, 30, 150, 1)],
     {"reed": 0.06, "woody": 0.6, "herbs": 0.16, "sand": 0.1},
     {"reed": {2: 1.0}, "woody": {2: 0.95, 3: 0.03, 4: 0.02}, "herbs": {2: 0.45, 3: 0.4, 4: 0.15},
      "sand": {2: 0.25, 3: 0.55, 4: 0.2}}),
    ("marsh", [(0.85, 0, 25, 0), (1.5, 25, 220, 1)],
     {"reed": 0.85, "herbs": 0.03, "woody": 0.015},
     {"reed": {5: 0.8, 6: 0.2}, "herbs": {5: 1.0}, "woody": {5: 1.0}}),
    ("herbs", [(0.5, 0, 25, 0), (1.15, 25, 120, 1)],
     {"reed": 0.35, "woody": 0.32, "herbs": 0.9, "sand": 0.5, "bare": 0.08},
     {"reed": {10: 0.4, 7: 0.3, 8: 0.1, 11: 0.2}, "woody": {7: 0.4, 10: 0.2, 8: 0.25, 11: 0.1, 9: 0.05},
      "herbs": {7: 0.3, 8: 0.2, 9: 0.17, 10: 0.12, 11: 0.13, 5: 0.08},
      "sand": {7: 0.42, 8: 0.33, 11: 0.15, 9: 0.1}, "bare": {8: 0.5, 7: 0.3, 11: 0.2}}),
    ("grass", [(0.38, 0, 30, 0), (0.85, 30, 70, 1)],
     {"reed": 0.4, "woody": 0.5, "herbs": 0.9, "sand": 0.55, "bare": 0.15},
     {k: {12: 1.0} for k in ("reed", "woody", "herbs", "sand", "bare")}),
]
TALL = {0, 1, 2, 3, 4, 5, 6}


def dist_px(mask, n=4):
    """Distance in pixels to the mask (chamfer, up to n)."""
    d = np.full(mask.shape, n + 1.0)
    cur = mask.copy()
    d[cur] = 0
    for k in range(1, n + 1):
        nb = cur.copy()
        nb[1:] |= cur[:-1]; nb[:-1] |= cur[1:]; nb[:, 1:] |= cur[:, :-1]; nb[:, :-1] |= cur[:, 1:]
        if k % 2 == 0:
            nb[1:, 1:] |= cur[:-1, :-1]; nb[:-1, :-1] |= cur[1:, 1:]; nb[1:, :-1] |= cur[:-1, 1:]; nb[:-1, 1:] |= cur[1:, :-1]
        d[nb & ~cur] = k
        cur = nb
    return d


class Pass:
    def __init__(self):
        g = json.load(open(f"{ZNPP}/imagery/c3d_2025_08.json"))["grid"]
        self.bbox = g["bbox"]
        wat = np.asarray(Image.open(f"{ZNPP}/imagery/c3d_2025_08/water.png")).astype(np.float32) / 255
        B = np.load(f"{ZNPP}/imagery/c3d_2025_08/water_bands.npz")
        gr, ni, sw = (B[k].astype(np.float32) for k in ("green", "nir", "swir"))
        gndvi = (ni - gr) / (ni + gr + 1e-3)
        ndmi = (ni - sw) / (ni + sw + 1e-3)
        w = wat > 0.3
        self.dwater = dist_px(w) * 10.0
        h = np.full(w.shape, 5, np.int8)                          # bare
        h[gndvi >= 0.2] = 4                                       # sand
        h[gndvi >= 0.35] = 3                                      # herbs
        h[(gndvi >= 0.6) & (ndmi >= 0.18)] = 2                    # woody
        h[(self.dwater <= 30) & (gndvi >= 0.35)] = 1              # reed
        h[w] = 0
        self.hab, self.H, self.W = h, *w.shape

    def px(self, x, y):
        w0, s0, e0, n0 = self.bbox
        lon, lat = LON0 + x / KX, LAT0 + y / KZ
        c = np.clip(((lon - w0) / (e0 - w0) * self.W).astype(int), 0, self.W - 1)
        r = np.clip(((n0 - lat) / (n0 - s0) * self.H).astype(int), 0, self.H - 1)
        return r, c


def ground_fn():
    t = np.load(f"{ZNPP}/scenes/crossing3d/terrain.npz")
    X, Y, Z = t["x"], t["y"], t["z"]

    def ground(x, y):     # bilinear on the 20 m grid
        fx = np.interp(x, X, np.arange(len(X)))
        fy = np.interp(y, Y, np.arange(len(Y)))
        i0, j0 = np.floor(fy).astype(int), np.floor(fx).astype(int)
        i1, j1 = np.minimum(i0 + 1, len(Y) - 1), np.minimum(j0 + 1, len(X) - 1)
        a, b = fy - i0, fx - j0
        return Z[i0, j0] * (1 - a) * (1 - b) + Z[i0, j1] * (1 - a) * b + Z[i1, j0] * a * (1 - b) + Z[i1, j1] * a * b
    return ground


def heights(rng, fam):
    out = np.empty(len(fam))
    for f in np.unique(fam):
        m = fam == f
        spec = HEIGHT[int(f)]
        if spec[0] == "normal":
            out[m] = np.clip(rng.normal(spec[1], spec[2], m.sum()), spec[3], spec[4])
        else:
            out[m] = rng.uniform(spec[1], spec[2], m.sum())
    return out


def place(view, P, ground, seed):
    rng = np.random.default_rng(seed)
    cam = np.array(view["cam"], float)
    hd = view["heading"]
    out, counts = [], {}
    for li, (name, bands, prob, mix) in enumerate(LAYERS):
        for spacing, r0, r1, lod in bands:
            r1 = min(r1, view["far_m"])
            if r1 <= r0:
                continue
            g = np.arange(-r1, r1, spacing)
            xx, yy = np.meshgrid(g, g)
            xx = xx.ravel() + rng.uniform(-0.5, 0.5, xx.size) * spacing
            yy = yy.ravel() + rng.uniform(-0.5, 0.5, yy.size) * spacing
            r = np.hypot(xx, yy)
            az = (np.degrees(np.arctan2(xx, yy)) - hd + 180) % 360 - 180
            keep = (r >= r0) & (r < r1) & ((np.abs(az) < view["cone_deg"]) | (r < 20))
            x, y, r = cam[0] + xx[keep], cam[1] + yy[keep], r[keep]
            jr, jc = P.px(x + rng.normal(0, 4, len(x)), y + rng.normal(0, 4, len(y)))
            hab = P.hab[jr, jc]
            tr, tc = P.px(x, y)
            hab = np.where(P.hab[tr, tc] == 0, 0, hab)              # never on the pass's water at the spot itself
            p = np.zeros(len(x))
            for k, v in prob.items():
                p[hab == HAB.index(k)] = v
            far = np.ones(len(x), bool)
            for cx, cy in CAISSONS:
                far &= np.hypot(x - cx, y - cy) > 26
            sel = (rng.random(len(x)) < p) & far
            x, y, r, hab = x[sel], y[sel], r[sel], hab[sel]
            fam = np.full(len(x), -1)
            u = rng.random(len(x))
            for k, m in mix.items():
                hk = hab == HAB.index(k)
                acc = 0.0
                for f, share in m.items():
                    pick = hk & (u >= acc) & (u < acc + share)
                    fam[pick] = f
                    acc += share
            ok = fam >= 0
            x, y, r, fam = x[ok], y[ok], r[ok], fam[ok]
            # cattails nearest the water, reeds behind them
            near_w = P.dwater[P.px(x, y)] <= 10
            fam = np.where((fam == 6) & ~near_w, 5, fam)
            h = heights(rng, fam)
            # the camera's clearing: only low grass right round it, nothing taller than the eye a little further
            tall = np.isin(fam, list(TALL)) | (h > view["eye"])
            ok = (r > view["clear_m"]) | (fam == 12)
            ok &= (r > 0.5)
            ok &= ~(tall & (r < view["clear_tall_m"]))
            if "gap" in view:          # a framing choice: no trees, shrubs or reeds in a narrow wedge toward the tower
                half, g0, g1 = view["gap"][:3]
                which = np.isin(fam, list(TALL)) if len(view["gap"]) < 4 else (fam != 12)   # "all": open ground
                az = (np.degrees(np.arctan2(x - cam[0], y - cam[1])) - hd + 180) % 360 - 180
                ok &= ~(which & (np.abs(az) < half) & (r > g0) & (r < g1))
            x, y, fam, h = x[ok], y[ok], fam[ok], h[ok]
            n = len(x)
            out.append(np.stack([x, y, ground(x, y), fam, rng.uniform(0, 2 * math.pi, n), h,
                                 np.full(n, lod), rng.integers(0, 4, n)], 1))
            counts[f"{name} lod{lod}"] = counts.get(f"{name} lod{lod}", 0) + n
    pts = np.vstack(out).astype(np.float32)
    cz = float(ground(np.array([cam[0]]), np.array([cam[1]]))[0])
    return pts, cz, counts


def main(views_json, out_dir, *ids):
    V = json.load(open(views_json))["views"]
    P, ground = Pass(), ground_fn()
    for i, view in enumerate(V):
        if ids and view["id"] not in ids:
            continue
        pts, cz, counts = place(view, P, ground, 1000 + i)
        r, c = P.px(np.array([view["cam"][0]]), np.array([view["cam"][1]]))
        np.savez_compressed(f"{out_dir}/plants_{view['id']}.npz", pts=pts,
                            cam=np.array([*view["cam"], cz]), heading=view["heading"])
        fam = pts[:, 3].astype(int)
        info = {"view": view, "camera_ground_m": round(cz, 2), "habitat_at_camera": HAB[int(P.hab[r, c][0])],
                "plants": int(len(pts)), "by_layer": counts,
                "by_family": {str(k): int((fam == k).sum()) for k in range(13)}}
        json.dump(info, open(f"{out_dir}/plants_{view['id']}.json", "w"), indent=1)
        print(view["id"], info["habitat_at_camera"], len(pts), counts)


if __name__ == "__main__":
    main(*sys.argv[1:])
