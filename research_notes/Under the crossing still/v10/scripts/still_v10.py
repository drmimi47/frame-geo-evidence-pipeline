"""The v10 shot `drowning`'s passes (the user, 9 November 2026, on v9: "remove the top right branch that looks like a
mistake ... also remove the birds ..."). As still_v9.py (v8's machinery exec'd without its main, the plants in
dead_v9's state, every loss binary), with one fix:

  A STEM IS KEPT ONLY WHILE THE STEM IT GROWS FROM IS KEPT. v8 ranked each model's stems by radius with a random
  share mixed in (`ord`), and dropped the thinnest first; so a thick secondary branch could outrank the primary it grows
  from and stay when that primary went, floating in the air, unattached (the user's "mistake": pieces of the near
  willows' crowns left in the sky at the frame's top left). Here each stem's parent is found from the models' own
  geometry (a branch starts on its parent's centre line: plants.py `along`), and a stem's order is capped by its
  parent's (ord = min(own, parent's)): whatever the share dropped, every kept stem joins a kept stem, down to a trunk.
  The order's random draws are v8's exactly, so every stem v9 kept attached stays.

Runs inside Blender on the flight south's scene file at frame 4001, NEVER saving it:

    blender -b --factory-startup <south.blend> -P still_v10.py -- <views_v5.json> <plants_f.npz> <plants_laid.npz> <out_dir> <mode>

Modes:
  preview    the dead plants alone (no water, no moving parts), 1920x1080, 16 samples: pv.png
  stems      every model's stems (centre lines, radii, order, parent) to <out_dir>/stems.npz (the crossings' input)
  passes     static2x.exr, pos2x.exr, matte.exr (as still_v9.py)
"""
import json
import os
import sys
import time

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
V8_DIR = os.path.abspath(os.path.join(HERE, "..", "..", "v8", "scripts"))
V9_DIR = os.path.abspath(os.path.join(HERE, "..", "..", "v9", "scripts"))
sys.path.insert(0, V9_DIR)
V8 = {"__file__": os.path.join(V8_DIR, "still_v8.py"), "__name__": "still_v8"}
_src = open(os.path.join(V8_DIR, "still_v8.py")).read()
exec(compile(_src[:_src.rindex("\nmain()")], "still_v8.py", "exec"), V8)
V4, V3 = V8["V4"], V8["V3"]
PL = V3["PL"]
_wa = V8["with_alpha"]
V8["with_alpha"] = lambda mat, binary=False: _wa(mat, True)      # nothing moves: every loss binary (as v9)
import dead_v9 as DV  # noqa: E402

PARENT_TOL = 0.02          # m (model units): a branch's first point lies on its parent's centre line (exactly, but for
                           # floating point); farther than this from every earlier stem it is an orphan (kept as is)
STEMS = {}                 # model seed*10+lod -> the stems' records (for the `stems` mode)


class _Rec10:
    """v8's _Rec, also keeping each stem's centre line and radii (the geometry and every random draw unchanged)."""
    def __init__(self):
        self.orig = {}

    def install(self):
        G = PL.Geo
        for nm in ("tubes", "leaves", "blades"):
            self.orig[nm] = getattr(G, nm)
        rec = self

        def tubes(g, P, R, sides, col):
            n0 = sum(len(f) for f in g.F)
            out = rec.orig["tubes"](g, P, R, sides, col)
            P = np.asarray(P, float)
            n1 = sum(len(f) for f in g.F)
            if n1 > n0:
                b, n = P.shape[:2]
                per = (n - 1) * sides * 2
                R = np.asarray(R, float)
                for k in range(b):
                    g._grp.append((per, float(R[k].mean()), float(P[k, :, 2].min())))
                    g._cl.append((P[k].copy(), R[k].copy()))
            return out

        def leaves(g, B, U, S, L, W, col, widest=0.35, fold=0.22, outline=None):
            n0 = sum(len(f) for f in g.F)
            out = rec.orig["leaves"](g, B, U, S, L, W, col, widest, fold, outline)
            n1 = sum(len(f) for f in g.F)
            m = len(B)
            if m and n1 > n0:
                per = (n1 - n0) // m
                g._grp.extend([(per, 0.0, 1.0)] * m)
                g._cl.extend([None] * m)
            return out

        def blades(g, B, D, L, W, bend, col, segs=4, taper=1.5, rng=None):
            n0 = sum(len(f) for f in g.F)
            out = rec.orig["blades"](g, B, D, L, W, bend, col, segs, taper, rng)
            n1 = sum(len(f) for f in g.F)
            m = len(B)
            if m and n1 > n0:
                per = (n1 - n0) // m
                g._grp.extend([(per, 0.0, 1.0)] * m)
                g._cl.extend([None] * m)
            return out

        G.tubes, G.leaves, G.blades = tubes, leaves, blades
        _init = G.__init__

        def init(g):
            _init(g)
            g._grp = []
            g._cl = []
        G.__init__ = init


def _seg_dist(p, P):
    """Distance from point p to the polyline P (n, 3)."""
    a, b = P[:-1], P[1:]
    ab = b - a
    t = np.clip(((p - a) * ab).sum(1) / np.maximum((ab * ab).sum(1), 1e-12), 0, 1)
    return float(np.linalg.norm(a + ab * t[:, None] - p, axis=1).min())


def face_numbers10(geo, seed):
    """v8's face_numbers (the same draws), the stems' order then capped by their parents' (see the docstring)."""
    V, F, C, K = geo.arrays()
    rng = np.random.default_rng(900000 + seed)
    per = np.array([p for p, r, z in geo._grp], int)
    if per.sum() != len(F):
        raise SystemExit(f"face groups {per.sum()} != faces {len(F)} (seed {seed})")
    rad = np.array([r for p, r, z in geo._grp])
    zmin = np.array([z for p, r, z in geo._grp])
    lr = rng.uniform(0, 1, len(per))
    stem = rad > 0
    ordv = np.full(len(per), 0.5)
    if stem.any():
        rk = rad[stem].argsort().argsort() / max(stem.sum() - 1, 1)
        ordv[stem] = 0.85 * rk + 0.15 * rng.uniform(0, 1, stem.sum())
    ground = stem & (zmin < 0.03)
    ordv[ground] = 9.0
    own = ordv.copy()
    parent = np.full(len(per), -1)
    idx = np.flatnonzero(stem)
    orphans = 0
    for j, k in enumerate(idx):
        if ground[k]:
            continue
        p0 = geo._cl[k][0][0]
        best, bd = -1, PARENT_TOL
        for m in idx[:j]:                        # parents are made before their branches (plants.py)
            d = _seg_dist(p0, geo._cl[m][0])
            if d < bd:
                best, bd = m, d
        if best < 0:
            orphans += 1
            continue
        parent[k] = best
        ordv[k] = min(ordv[k], ordv[best])
    STEMS[seed] = dict(cl=[geo._cl[k][0] for k in idx], rad=[geo._cl[k][1] for k in idx], ord=ordv[idx],
                       own=own[idx], ground=ground[idx], parent=parent[idx], orphans=orphans)
    return np.repeat(lr, per), np.repeat(ordv, per)


def main():
    a = sys.argv[sys.argv.index("--") + 1:]
    views_json, npz, laid, out_dir, mode = a[:5]
    view = next(v for v in json.load(open(views_json))["views"] if v["id"] == "f")
    os.makedirs(out_dir, exist_ok=True)
    t0 = time.time()
    V8["_Rec"] = _Rec10
    V8["face_numbers"] = face_numbers10
    V3["build_protos"] = V8["build_protos_v8"]
    _pm = V3["plant_material"]
    V3["plant_material"] = lambda haze: V8["with_alpha"](V8["dying_colour"](_pm(haze)))
    ctx = V4["setup"](view)
    s = ctx["s"]
    s.world = ctx["dawn"]
    P, pts, z, info = V4["plants"](ctx, npz)
    L = np.load(laid)
    if len(L["P"]) != len(P) or np.abs(L["P"] - P).max() > 1e-3:
        raise SystemExit("plants_laid.npz does not match the plants laid now")
    sob = V8["scatter_v8"](P, ctx["protos"], "plants f")
    mov = V4["moving"](ctx)
    for ob in mov:
        ob.pass_index = 1
    glows = [ob for ob in bpy.data.objects if ob.name.startswith("glow ")]
    hide0 = {ob.name: ob.hide_render for ob in set(mov) | set(glows)}
    filt0 = s.render.filter_size
    D = DV.Dead(L)
    V8["set_state"](sob, D.state())
    print("PREPARED", round(time.time() - t0, 1), flush=True)

    if mode == "stems":
        # the models in build order (still_v8.build_protos_v8): proto index k -> its seed*10+lod key
        out, k = {}, 0
        for fam, (name, fn, H, lods) in PL.FAMILIES.items():
            for lod in lods:
                for var in range(V3["NVAR"]):
                    st = STEMS[(1000 * fam + var) * 10 + lod]
                    out[f"k{k}_n"] = np.array([len(c) for c in st["cl"]])
                    out[f"k{k}_cl"] = np.concatenate(st["cl"]) if st["cl"] else np.zeros((0, 3))
                    out[f"k{k}_rad"] = np.concatenate(st["rad"]) if st["rad"] else np.zeros(0)
                    for key in ("ord", "own", "ground", "parent"):
                        out[f"k{k}_{key}"] = st[key]
                    out[f"k{k}_orphans"] = np.array(st["orphans"])
                    k += 1
        np.savez_compressed(f"{out_dir}/stems.npz", **out)
        print("DONE stems", k, "orphans", sum(int(v) for kk, v in out.items() if kk.endswith("_orphans")),
              "capped", sum(int((out[f"k{i}_ord"] < out[f"k{i}_own"]).sum()) for i in range(k)), flush=True)
        return

    if mode == "preview":
        for ob in mov:
            ob.hide_render = True
        s.render.resolution_x, s.render.resolution_y = 1920, 1080
        s.eevee.taa_render_samples = 16
        s.render.film_transparent = False
        s.render.image_settings.file_format = "PNG"
        s.render.image_settings.color_depth = "8"
        s.render.image_settings.color_mode = "RGB"
        V4["render"](f"{out_dir}/pv.png")
        print("PREVIEW", flush=True)
        return

    if mode == "passes":
        log = {"camera": list(ctx["co"].location), "plants": info, "dead": D.summary(), "prepare_s": round(time.time() - t0, 1)}
        bpy.context.view_layer.material_override = None
        for ob in glows:
            ob.hide_render = hide0[ob.name]
        for ob in mov:
            ob.hide_render = True
        s.render.resolution_x, s.render.resolution_y = 3840, 2160
        s.eevee.taa_render_samples = 32
        s.render.filter_size = filt0
        s.render.image_settings.color_depth = "16"
        log["static_s"] = V4["render"](f"{out_dir}/static2x.exr")
        for ob in glows:
            ob.hide_render = True
        bpy.context.view_layer.material_override = V8["pos_material_v8"]()
        s.eevee.taa_render_samples = 1
        s.render.filter_size = 0.0
        s.render.image_settings.color_depth = "32"
        log["pos_s"] = V4["render"](f"{out_dir}/pos2x.exr")
        for ob in set(mov) | set(glows):
            ob.hide_render = hide0[ob.name]
        bpy.context.view_layer.material_override = V8["matte_material"]()
        s.render.resolution_x, s.render.resolution_y = 1920, 1080
        s.eevee.taa_render_samples = 32
        s.render.filter_size = filt0
        s.render.image_settings.color_depth = "16"
        log["matte_s"] = V4["render"](f"{out_dir}/matte.exr")
        bpy.context.view_layer.material_override = None
        json.dump(log, open(f"{out_dir}/log_passes.json", "w"), indent=1, default=float)
        print("DONE passes", json.dumps(log, default=float), flush=True)


main()
