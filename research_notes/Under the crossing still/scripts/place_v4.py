"""Where the plants of the v4 view stand (the user, 5 November 2026, on view f: the line "at the center of the frame
... the cables symmetrical", "more trees closer to the base of the tower in the distance", the d-type trees, "the
composition of the final f version's nature should be somewhat symmetrical").

    python -I place_v4.py <views_v4.json> <out_dir> [view id]          (from the project root)

Three origins, kept per plant (column `origin` in the .npz, counted in the .json):
  0 rule      placed by the v3 rule (place_plants.place: the 28 August 2025 pass's habitat at each spot), on the
              left of the axis only (the vertical plane through towers 22 and 23 and the camera);
  1 mirrored  each of those mirrored across the axis, then jittered (position, height within its family's range, a new
              rotation and variant, and 12% swapped to a kindred family), so the right reads as grown, not cloned.
              A composition choice: the pass's habitat on the right is not read;
  2 base      a young forest composed round tower 23's caisson (white willow and black poplar, the d trees, as in v3:
              heights as sourced), left half placed and mirrored the same way; lower growth only in front of the
              caisson, so its base shows. A composition choice, not observed: the pass's habitat there is recorded.
Nothing within `caisson_clear_m` of any caisson's centre (its concrete is 22.5 m in radius; v3 kept 26 m).
"""
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import place_plants as PP  # noqa: E402

KIN = [(0, 1), (2, 3, 4), (7, 8, 9, 10, 11), (5,)]     # families a mirrored plant may swap to (12%)
TREES = (0, 1)


def axis(view):
    a, b = np.array(view["tower_from"]), np.array(view["tower_to"])
    ax = (b - a) / np.linalg.norm(b - a)
    nrm = np.array([ax[1], -ax[0]])                       # to the right, looking along the span
    cam = b - ax * view["back_m"]
    heading = math.degrees(math.atan2(ax[0], ax[1])) % 360
    return cam, ax, nrm, heading, b


def bounds(fam):
    spec = PP.HEIGHT[int(fam)]
    return (spec[3], spec[4]) if spec[0] == "normal" else (spec[1], spec[2])


def mirror(rng, pts, cam, nrm, keep_lod=None):
    """pts columns x, y, z, fam, rot, h, lod, var. Mirror across the axis plane and jitter."""
    p = pts.copy()
    lat = (p[:, :2] - cam) @ nrm
    p[:, :2] -= 2 * lat[:, None] * nrm[None]
    r = np.hypot(*(p[:, :2] - cam).T)
    sig = np.minimum(0.25 + 0.02 * r, 3.0)
    p[:, :2] += rng.normal(0, 1, (len(p), 2)) * sig[:, None]
    fam = p[:, 3].astype(int)
    swap = rng.random(len(p)) < 0.12
    for grp in KIN:
        m = swap & np.isin(fam, grp)
        if len(grp) > 1 and m.any():
            fam[m] = rng.choice(grp, m.sum())
    changed = fam != p[:, 3].astype(int)
    p[changed, 5] = PP.heights(rng, fam[changed])
    p[:, 3] = fam
    lo = np.array([bounds(f)[0] for f in fam]); hi = np.array([bounds(f)[1] for f in fam])
    p[:, 5] = np.clip(p[:, 5] * rng.uniform(0.88, 1.12, len(p)), lo, hi)
    p[:, 4] = rng.uniform(0, 2 * math.pi, len(p))
    p[:, 7] = rng.integers(0, 4, len(p))
    keep = rng.random(len(p)) > 0.05
    return p[keep]


def base_forest(rng, view, cam, ax, nrm, tower, ground):
    """A young forest round tower 23's caisson, left half; lower growth in front of it."""
    bf = view["base_forest"]
    r0, r1 = bf["r"]
    s = bf["spacing_m"]
    g = np.arange(-r1, r1 + s, s)
    xx, yy = np.meshgrid(g, g)
    q = np.column_stack([xx.ravel(), yy.ravel()]) + rng.uniform(-0.5, 0.5, (xx.size, 2)) * s
    rt = np.hypot(*q.T)
    q = q[(rt >= r0) & (rt < r1)]
    rt = np.hypot(*q.T)
    pos = tower + q
    lat = (pos - cam) @ nrm
    along = (pos - cam) @ ax
    q, pos, rt, lat, along = (a[lat < 0] for a in (q, pos, rt, lat, along))
    pr = bf["p_near"] + (bf["p_far"] - bf["p_near"]) * np.clip((rt - r0) / (r1 - r0), 0, 1)
    sel = rng.random(len(pos)) < pr
    pos, rt, lat, along = pos[sel], rt[sel], lat[sel], along[sel]
    dt = view["back_m"]
    front = along < dt
    fam = np.where(rng.random(len(pos)) < bf["poplar_share"], 1, 0)
    # in front of the caisson: only herbs within front_low_half_m of the axis (left to the v3 layers), saplings and
    # shrubs out to front_shrub_half_m, then the trees
    low = front & (np.abs(lat) < bf["front_low_half_m"])
    shrub = front & ~low & (np.abs(lat) < bf["front_shrub_half_m"])
    fam = np.where(shrub, rng.choice([2, 2, 2, 3, 4], len(fam)), fam)
    keep = ~low
    pos, fam = pos[keep], fam[keep]
    n = len(pos)
    h = PP.heights(rng, fam)
    pts = np.column_stack([pos[:, 0], pos[:, 1], ground(pos[:, 0], pos[:, 1]), fam,
                           rng.uniform(0, 2 * math.pi, n), h, np.ones(n), rng.integers(0, 4, n)])
    return pts


def main(views_json, out_dir, vid="f4"):
    view = next(v for v in json.load(open(views_json))["views"] if v["id"] == vid)
    os.makedirs(out_dir, exist_ok=True)
    cam, ax, nrm, heading, tower = axis(view)
    P, ground = PP.Pass(), PP.ground_fn()
    rng = np.random.default_rng(4004)
    v3view = {k: view[k] for k in ("cone_deg", "far_m", "clear_m", "clear_tall_m", "gap", "eye")}
    v3view.update(cam=list(cam), heading=heading)
    saved = PP.CAISSONS
    PP.CAISSONS = []                                          # the clearance is applied below, at v4's distance
    pts, cz, counts = PP.place(v3view, P, ground, 4004)
    PP.CAISSONS = saved
    lat = (pts[:, :2] - cam) @ nrm
    rule = pts[lat < 0].astype(np.float64)
    mir = mirror(rng, rule, cam, nrm)
    base_l = base_forest(rng, view, cam, ax, nrm, tower, ground)
    base_r = mirror(rng, base_l, cam, nrm)
    # the mirrored and composed plants keep their own ground (z is re-read by the ray in Blender anyway)
    mir[:, 2] = ground(mir[:, 0], mir[:, 1]); base_r[:, 2] = ground(base_r[:, 0], base_r[:, 1])
    allp = np.vstack([rule, mir, base_l, base_r])
    origin = np.concatenate([np.zeros(len(rule)), np.ones(len(mir)), np.full(len(base_l) + len(base_r), 2)])
    # the caissons' clearance (all eight), the camera's clearing again for the mirrored ones
    far = np.ones(len(allp), bool)
    for cx, cy in PP.CAISSONS:
        far &= np.hypot(allp[:, 0] - cx, allp[:, 1] - cy) > view["caisson_clear_m"]
    r = np.hypot(*(allp[:, :2] - cam).T)
    fam = allp[:, 3].astype(int)
    tall = np.isin(fam, list(PP.TALL)) | (allp[:, 5] > view["eye"])
    ok = far & ((r > view["clear_m"]) | (fam == 12)) & (r > 0.5) & ~(tall & (r < view["clear_tall_m"]))
    half, g0, g1 = view["gap"]
    az = (np.degrees(np.arctan2(allp[:, 0] - cam[0], allp[:, 1] - cam[1])) - heading + 180) % 360 - 180
    ok &= ~(np.isin(fam, list(PP.TALL)) & (np.abs(az) < half) & (r > g0) & (r < g1) & (origin < 2))
    if "low_wedge" in view:   # a framing choice: only growth under the eye between the meadow's edge and the base
        lh, l0, l1, lmax = view["low_wedge"]
        ok &= ~((allp[:, 5] > lmax) & (np.abs(az) < lh) & (r > l0) & (r < l1) & (origin < 2))
    allp, origin, r, fam = allp[ok], origin[ok], r[ok], fam[ok]
    # levels of detail: the trees finer than v3 here (d's look nearer the base); the rest as placed
    lod = allp[:, 6].copy()
    t = np.isin(fam, TREES)
    L = view["lod"]
    lod[t] = np.where(r[t] < L["trees_lod0_m"], 0, np.where(r[t] < L["trees_lod1_m"], 1, 2))
    allp[:, 6] = lod
    # the pass's habitat at each plant (to say where the composition departs from it)
    rr, cc = P.px(allp[:, 0], allp[:, 1])
    hab = P.hab[rr, cc]
    np.savez_compressed(f"{out_dir}/plants_{vid}.npz", pts=allp.astype(np.float32), origin=origin.astype(np.int8),
                        hab=hab.astype(np.int8), cam=np.array([*cam, cz]), heading=heading)
    by = {}
    for o, oname in enumerate(("rule", "mirrored", "base")):
        m = origin == o
        by[oname] = {"plants": int(m.sum()),
                     "by_family": {str(k): int((fam[m] == k).sum()) for k in range(13) if (fam[m] == k).any()},
                     "habitat_at_spot": {PP.HAB[h]: int((hab[m] == h).sum()) for h in range(6) if (hab[m] == h).any()}}
    trees_off_woody = int((np.isin(fam, TREES) & (origin > 0) & (hab != PP.HAB.index("woody"))).sum())
    info = {"view": view, "camera": [round(float(cam[0]), 2), round(float(cam[1]), 2)], "heading": round(heading, 3),
            "camera_ground_m": round(cz, 2), "plants": int(len(allp)), "by_origin": by,
            "composed_trees_not_on_woody_ground": trees_off_woody,
            "by_family": {str(k): int((fam == k).sum()) for k in range(13)},
            "v3_layers_left": counts}
    json.dump(info, open(f"{out_dir}/plants_{vid}.json", "w"), indent=1)
    print(json.dumps({k: info[k] for k in ("camera", "heading", "plants", "composed_trees_not_on_woody_ground")}),
          {k: v["plants"] for k, v in by.items()})


if __name__ == "__main__":
    main(*sys.argv[1:])
