"""Where the prototype still's trees stand (NEXT.md, the shot `under-the-crossing`, the user, 5 November 2026): only
where the Sentinel-2 pass of 28 August 2025 shows vegetation on the bed, never on its water (the pass's own mask) or
within 26 m of a caisson; heights by the sources for 2026 (white willow and black poplar, self-seeded: about 3 m in
May 2024, about 7 m in 2025, the largest about 9 m by spring 2026; TSN 7 June 2026, Kuzemko, Frontliner). Positions
are the pass's vegetated pixels, jittered; each tree's shape is representative (modelled, said so).

    python -I place_trees.py <out.npz> <out.json> [tower_x tower_y dist_m bearing_deg]      (from the project root)

The camera stands dist_m from the tower on the bearing given (from the tower), looking at it. Three levels of detail
by distance from the camera (fine leaves within 45 m, sprays to 160 m, coarse beyond, to 800 m).
"""
import json, math, sys
import numpy as np
from PIL import Image

ZNPP = "libraries/conductive-seam/satellite/networks/znpp"
LON0, LAT0, KX, KZ = 34.5879012, 47.5085556, 75194.446, 110574.0
T21, T22 = np.array([3948.0, 5485.0]), np.array([4185.0, 6275.0])
CAISSONS = [(3729, 4757), (3948, 5485), (4185, 6275), (4426, 7062), (4658, 7836),      # Ferosplavna 20-24
            (4154, 4955), (4511, 6137), (4866, 7318)]                                  # Dniprovska 23-25
CLEAR_M = 8.0            # a clearing round the camera, so it stands among the first trees, not inside one
BANDS = ((3.8, CLEAR_M, 45.0, 0), (4.2, 45.0, 160.0, 1), (6.5, 160.0, 800.0, 2))   # spacing, from, to, detail


def main(out, out_json, tx=None, ty=None, dist=None, bearing=None):
    rng = np.random.default_rng(23)
    if tx is None:          # the first prototype: on span 21-22, 35 m west of the line, toward tower 22
        d = T22 - T21
        n = np.array([d[1], -d[0]]) / np.linalg.norm(d)
        cam = T21 + d * 0.8 - n * 35.0
        tower = T22
    else:
        tower = np.array([float(tx), float(ty)])
        b = math.radians(float(bearing))
        cam = tower + float(dist) * np.array([math.sin(b), math.cos(b)])
    v = tower - cam
    HEADING = math.degrees(math.atan2(v[0], v[1]))
    t = np.load(f"{ZNPP}/scenes/crossing3d/terrain.npz")
    X, Y, Z = t["x"], t["y"], t["z"]
    g = json.load(open(f"{ZNPP}/imagery/c3d_2025_08.json"))["grid"]
    w0, s0, e0, n0 = g["bbox"]
    rgb = np.asarray(Image.open(f"{ZNPP}/imagery/c3d_2025_08/rgb.webp").convert("RGB")).astype(np.float32)
    wat = np.asarray(Image.open(f"{ZNPP}/imagery/c3d_2025_08/water.png")).astype(np.float32) / 255
    H, W = wat.shape

    def px(x, y):
        lon, lat = LON0 + x / KX, LAT0 + y / KZ
        return ((lon - w0) / (e0 - w0) * W).astype(int), ((n0 - lat) / (n0 - s0) * H).astype(int)

    def ground(x, y):     # bilinear on FABDEM/the bed's grid (20 m)
        fx = np.interp(x, X, np.arange(len(X)))
        fy = np.interp(y, Y, np.arange(len(Y))) if Y[0] < Y[-1] else np.interp(-y, -Y, np.arange(len(Y)))
        i0, j0 = np.floor(fy).astype(int), np.floor(fx).astype(int)
        i1, j1 = np.minimum(i0 + 1, len(Y) - 1), np.minimum(j0 + 1, len(X) - 1)
        a, b = fy - i0, fx - j0
        return (Z[i0, j0] * (1 - a) * (1 - b) + Z[i0, j1] * (1 - a) * b + Z[i1, j0] * a * (1 - b) + Z[i1, j1] * a * b)

    pts = []
    for spacing, r0, r1, lod in BANDS:
        gx = np.arange(-r1, r1, spacing)
        xx, yy = np.meshgrid(gx, gx)
        xx = xx.ravel() + rng.uniform(-0.45, 0.45, xx.size) * spacing
        yy = yy.ravel() + rng.uniform(-0.45, 0.45, yy.size) * spacing
        r = np.hypot(xx, yy)
        az = (np.degrees(np.arctan2(xx, yy)) - HEADING + 180) % 360 - 180
        keep = (r >= r0) & (r < r1) & ((np.abs(az) < 62) | (r < 45))
        x, y = cam[0] + xx[keep], cam[1] + yy[keep]
        c, rr = px(x, y)
        ok = (c >= 3) & (c < W - 3) & (rr >= 3) & (rr < H - 3)
        x, y, c, rr = x[ok], y[ok], c[ok], rr[ok]
        col = rgb[rr, c]
        veg = (wat[rr, c] < 0.3) & (col[:, 1] >= col[:, 0] * 0.98) & (col.mean(1) < 115)
        far = np.ones(len(x), bool)
        for cx, cy in CAISSONS:
            far &= np.hypot(x - cx, y - cy) > 26
        sel = veg & far & (rng.random(len(x)) > 0.12)
        x, y = x[sel], y[sel]
        kind = (rng.random(len(x)) < 0.22).astype(int)              # 1: black poplar, 0: white willow
        h = np.where(kind == 1, rng.uniform(6.5, 9.5, len(x)), np.clip(rng.normal(6.4, 1.2, len(x)), 4.0, 9.0))
        pts.append(np.stack([x, y, ground(x, y), kind, rng.uniform(0, 2 * math.pi, len(x)), h,
                             np.full(len(x), lod), rng.integers(0, 4, len(x))], 1))
    P = np.vstack(pts)
    cz = float(ground(np.array([cam[0]]), np.array([cam[1]]))[0])
    np.savez(out, pts=P, cam=np.array([cam[0], cam[1], cz]), heading=HEADING)
    json.dump({"camera_xy": [round(float(v), 1) for v in cam], "camera_ground_m": round(cz, 2), "heading_deg": HEADING,
               "tower_xy": [round(float(v), 1) for v in tower],
               "trees": int(len(P)), "by_detail": [int((P[:, 6] == k).sum()) for k in range(3)],
               "poplar_share": round(float(P[:, 3].mean()), 2),
               "heights_m": [round(float(np.percentile(P[:, 5], q)), 1) for q in (5, 50, 95)],
               "rule": "a tree where the 2025 pass's pixel is vegetation (green at least red, darker than 115 of 255, "
                       "not water by its own mask), 26 m off any caisson, an 8 m clearing round the camera; every "
                       "~4 m to 160 m, ~6.5 m beyond, 12% left out at random",
               "sources": ["TSN, 7 June 2026: largest trees about 9 m (spring 2026)", "Kuzemko (Hmarochos, 3 Sep 2025):"
                           " about 7 m in 2025", "Frontliner w3hLYa_n8ao (13 Aug 2026): a 5-metre forest"]},
              open(out_json, "w"), indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:7])
