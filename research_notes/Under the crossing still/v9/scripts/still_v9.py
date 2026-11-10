"""The v9 shot `drowning`'s passes (the user, 8 November 2026: the water already fully back, the plants dead: see
dead_v9.py). Rendered ONCE (the plants stand still): v8's machinery (still_v8.py exec'd without its main, unchanged:
v3's plants with v8's per-leaf and per-stem numbers, the dying colour and losses as instancer attributes) with the
plants in dead_v9's state.

Runs inside Blender on the flight south's scene file at frame 4001, NEVER saving it:

    blender -b --factory-startup <south.blend> -P still_v9.py -- <views_v5.json> <plants_f.npz> <plants_laid.npz> <out_dir> <mode> [args]

Modes:
  preview TW,...   the dead plants alone (no water, no moving parts), 1920x1080, 16 samples, one PNG per tree twig share
  perch I,...      for those plants (indices into plants_laid): the highest points of their kept stems, in the world and
                   on the 1080p frame (the perched birds' footing), to <out_dir>/perch.json
  passes           static2x.exr (the plate without the moving parts, 2x, 32 samples, film-transparent), pos2x.exr
                   (world height R, distance G, 2x, one exact sample), matte.exr (the moving wires white over
                   everything else black, 1x, 32 samples: how much of the lit wires the dead plants leave in view)
"""
import json
import math
import os
import sys
import time

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
V8_DIR = os.path.abspath(os.path.join(HERE, "..", "..", "v8", "scripts"))
sys.path.insert(0, HERE)
V8 = {"__file__": os.path.join(V8_DIR, "still_v8.py"), "__name__": "still_v8"}
_src = open(os.path.join(V8_DIR, "still_v8.py")).read()
exec(compile(_src[:_src.rindex("\nmain()")], "still_v8.py", "exec"), V8)
V4, V3 = V8["V4"], V8["V3"]
# nothing moves, so every loss is binary (a stem is there or not): v8's soft edge (LEAF_W) drawn dithered left the stems
# just past the cut as pale dotted strokes
_wa = V8["with_alpha"]
V8["with_alpha"] = lambda mat, binary=False: _wa(mat, True)
import dead_v9 as DV  # noqa: E402


def main():
    a = sys.argv[sys.argv.index("--") + 1:]
    views_json, npz, laid, out_dir, mode = a[:5]
    rest = a[5:]
    view = next(v for v in json.load(open(views_json))["views"] if v["id"] == "f")
    os.makedirs(out_dir, exist_ok=True)
    t0 = time.time()
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
    sob = V8["scatter_v8"](P, ctx["protos"], "plants f")       # the name seeds each plant's random brightness
    mov = V4["moving"](ctx)
    for ob in mov:
        ob.pass_index = 1
    glows = [ob for ob in bpy.data.objects if ob.name.startswith("glow ")]
    hide0 = {ob.name: ob.hide_render for ob in set(mov) | set(glows)}
    filt0 = s.render.filter_size
    print("PREPARED", round(time.time() - t0, 1), flush=True)

    if mode == "preview":
        for ob in mov:
            ob.hide_render = True
        s.render.resolution_x, s.render.resolution_y = 1920, 1080
        s.eevee.taa_render_samples = 16
        s.render.film_transparent = False
        s.render.image_settings.file_format = "PNG"
        s.render.image_settings.color_depth = "8"
        s.render.image_settings.color_mode = "RGB"
        for tw in rest[0].split(","):
            D = DV.Dead(L, twig_tree=float(tw))
            V8["set_state"](sob, D.state())
            V4["render"](f"{out_dir}/pv_twig{tw}.png")
            print("PREVIEW", tw, json.dumps(D.summary()), flush=True)
        return

    D = DV.Dead(L)
    st = D.state()
    V8["set_state"](sob, st)

    if mode == "perch":
        cam = ctx["co"]
        bpy.context.view_layer.update()
        from bpy_extras.object_utils import world_to_camera_view
        protos = {ob.name: ob for ob in ctx["protos"].objects}
        out = {"twig_tree": DV.TWIG_TREE, "twig_near": DV.TWIG_NEAR, "camera": list(cam.location), "plants": {}}
        for i in (int(x) for x in rest[0].split(",")):
            ob = protos[f"p{int(P[i, 5]):03d}"]
            me = ob.data
            nf = len(me.polygons)
            card = np.zeros(nf, np.float32); me.attributes["card"].data.foreach_get("value", card)
            ordv = np.zeros(nf, np.float32); me.attributes["ord"].data.foreach_get("value", ordv)
            keepf = (card < 0.5) & (ordv >= D.twig[i])
            vs = np.zeros(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", vs); vs = vs.reshape(-1, 3)
            idx = sorted({v for f, k in zip(me.polygons, keepf) if k for v in f.vertices})
            V = vs[idx].astype(float)
            r, sc = P[i, 3], P[i, 4]
            Rz = np.array([[math.cos(r), -math.sin(r), 0], [math.sin(r), math.cos(r), 0], [0, 0, 1]])
            Wv = (V * sc) @ Rz.T + P[i, :3]
            top = np.argsort(-Wv[:, 2])[:400]
            pts_ = []
            for j in top:
                q = world_to_camera_view(s, cam, __import__("mathutils").Vector(Wv[j]))
                pts_.append([round(float(c), 3) for c in Wv[j]] + [round(q.x * 1920, 1), round((1 - q.y) * 1080, 1)])
            out["plants"][str(i)] = {"proto": ob.name, "fam": int(L["fam"][i]), "h": float(L["h"][i]),
                                     "base": [float(c) for c in P[i, :3]], "rot": float(r), "scale": float(sc),
                                     "kept_stem_faces": int(keepf.sum()), "faces": nf, "top": pts_}
            print("PERCH", i, ob.name, pts_[0], flush=True)
        json.dump(out, open(f"{out_dir}/perch.json", "w"), indent=1)
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
