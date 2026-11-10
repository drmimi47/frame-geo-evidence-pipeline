"""Where the dead plants' kept stems pierce the surface in the v10 shot `drowning` (plain numpy).

From still_v10.py's stems.npz (every model's stem centre lines, radii and capped order), v8's plants_laid.npz (each
plant's place, turn, size, model) and dead_v9's state (which plants stand, what share of their stems is dropped): each
kept stem of each standing plant within MAX_M of the eye, turned and scaled as the instancer lays it, is cut by the
plane z = LEVEL (13.1 m, the proposed level). Each cut is a crossing: where on the surface, the stem's radius there,
its tilt. The water's disturbance (composite_v10.py) is drawn round these: the plants' own geometry, nothing placed by
hand.

    python -I crossings_v10.py <stems.npz> <plants_laid.npz> <out.npz>
"""
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "v9", "scripts")))
import dead_v9 as DV  # noqa: E402

LEVEL = 13.1
MAX_M = 70.0               # beyond this the surface near the horizon is absorbed (v9's murk): nothing drawn reads
CUT = 0.05                 # a stem shows while ord > twig - CUT (v8's soft edge, LEAF_W 0.1, made binary at 0.5)


def main(stems_p, laid_p, out_p):
    S = np.load(stems_p)
    L = np.load(laid_p)
    D = DV.Dead(L)
    P, eye = D.P, np.asarray(L["eye"], float)
    dist = np.hypot(P[:, 0] - eye[0], P[:, 1] - eye[1])
    rows = []
    cache = {}
    for i in np.flatnonzero(D.keep & (dist < MAX_M)):
        k = int(P[i, 5])
        if k not in cache:
            n = S[f"k{k}_n"]
            cache[k] = (np.split(S[f"k{k}_cl"], np.cumsum(n)[:-1]), np.split(S[f"k{k}_rad"], np.cumsum(n)[:-1]),
                        S[f"k{k}_ord"])
        cls, rads, ordv = cache[k]
        r, sc = P[i, 3], P[i, 4]
        Rz = np.array([[math.cos(r), -math.sin(r), 0], [math.sin(r), math.cos(r), 0], [0, 0, 1]])
        for j, (cl, rad) in enumerate(zip(cls, rads)):
            if ordv[j] <= D.twig[i] - CUT:
                continue
            W = (cl * sc) @ Rz.T + P[i, :3]
            z = W[:, 2] - LEVEL
            hit = np.flatnonzero(z[:-1] * z[1:] < 0)
            for h in hit:
                f = z[h] / (z[h] - z[h + 1])
                p = W[h] + (W[h + 1] - W[h]) * f
                d = W[h + 1] - W[h]
                d /= np.linalg.norm(d)
                rows.append([p[0], p[1], (rad[h] + (rad[h + 1] - rad[h]) * f) * sc, d[0], d[1], d[2], i, j,
                             float(np.hypot(p[0] - eye[0], p[1] - eye[1]))])
    A = np.array(rows, float).reshape(-1, 9)
    np.savez_compressed(out_p, xy=A[:, :2], r=A[:, 2], dir=A[:, 3:6], plant=A[:, 6].astype(int), stem=A[:, 7].astype(int),
                        dist=A[:, 8], level=LEVEL, max_m=MAX_M)
    print("crossings", len(A), "plants", len(set(A[:, 6].astype(int))) if len(A) else 0,
          "radius m 5/50/95/max", np.percentile(A[:, 2], [5, 50, 95, 100]).round(3) if len(A) else None,
          "within 15 m", int((A[:, 8] < 15).sum()) if len(A) else 0)


if __name__ == "__main__":
    main(*sys.argv[1:4])
