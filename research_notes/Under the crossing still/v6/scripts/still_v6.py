"""The v6 shot `drowning` (decided with the user, 6 November 2026): v5's view f by day, held, while the proposed level
(12.7 m Baltic, 13.1 m in the scene) is drawn rising through the scene's own ground, past the plants and the lens.

The water is not a Blender object: it is drawn per frame by composite_v6.py from passes rendered here ONCE, because a
flat surface at height h seen from a still camera covers exactly the pixels whose visible surface lies below h (from
above: a ray going down meets the scene's points above h before it crosses the plane; from below, the same the other
way), so the picture under the water, the plants left above it and the order between them all follow from the
scene's own heights. Runs inside Blender on the flight south's scene file at frame 4001, NEVER saving it (still_v5.py
and still_v4.py exec'd without their mains, unchanged):

    blender -b --factory-startup <south.blend> -P still_v6.py -- <views_v5.json> <plants_f.npz> <out_dir> <mode> [scale]

Modes:
  static    v5's static picture (everything that does not move: the plants, towers, land, the cut line), at `scale`
            times 1920x1080 (2: 3840x2160, so the water's edge against the grass is drawn from 4 samples a pixel),
            EEVEE 32 samples, film-transparent, linear EXR. The wires' 0.7 px floor is kept in 1080p pixels.
  pos       the same objects, every surface's world height (R) and its distance from the eye (G) drawn flat
            (material override, emission), 1 sample, the pixel filter off, 32-bit float: one exact surface a pixel.
            The glows are left out (light round the wires, not surfaces), as in v5's contour pass.
"""
import json
import os
import sys
import time

import bpy

V5_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))
sys.path.insert(0, V5_DIR)
V5 = {"__file__": os.path.join(V5_DIR, "still_v5.py"), "__name__": "still_v5"}
_src = open(os.path.join(V5_DIR, "still_v5.py")).read()
exec(compile(_src[:_src.rindex("\nmain()")], "still_v5.py", "exec"), V5)
V4 = V5["V4"]


def pos_material():
    m = bpy.data.materials.new("position v6")
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    cam = nt.nodes.new("ShaderNodeCameraData")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Position"], sep.inputs[0])
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(sep.outputs["Z"], comb.inputs["X"])
    nt.links.new(cam.outputs["View Distance"], comb.inputs["Y"])
    comb.inputs["Z"].default_value = 1.0
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(comb.outputs[0], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


def main():
    a = sys.argv[sys.argv.index("--") + 1:]
    views_json, npz, out_dir, mode = a[:4]
    scale = int(a[4]) if len(a) > 4 else 2
    view = next(v for v in json.load(open(views_json))["views"] if v["id"] == "f")
    os.makedirs(out_dir, exist_ok=True)
    t0 = time.time()
    ctx = V4["setup"](view)
    s = ctx["s"]
    s.world = ctx["dawn"]                         # (a "day" view: the scene's own world; film-transparent anyway)
    W, H = 1920 * scale, 1080 * scale
    s.render.resolution_x, s.render.resolution_y = W, H
    P, pts, z, info = V4["plants"](ctx, npz)
    V4["V3"]["scatter"](P, ctx["protos"], "plants f")    # the name seeds each plant's random brightness (as v3, v5)
    mov = V4["moving"](ctx)
    for ob in mov:
        ob.hide_render = True
    log = {"mode": mode, "size": [W, H], "camera": {"location": list(ctx["co"].location),
                                                    "ground_m": round(ctx["ground"], 3), "on": ctx["ground_on"],
                                                    "heading": ctx["heading"], "pitch": view["pitch"],
                                                    "lens": view["lens"]},
           "plants": info, "hidden_moving": [o.name for o in mov]}
    if mode == "pos":
        glows = [ob.name for ob in bpy.data.objects if ob.name.startswith("glow ")]
        for nm in glows:
            bpy.data.objects[nm].hide_render = True
        log["hidden_glows"] = glows
        bpy.context.view_layer.material_override = pos_material()
        s.eevee.taa_render_samples = 1
        s.render.filter_size = 0.0
        s.render.image_settings.color_depth = "32"
        log["filter_size"] = s.render.filter_size
    log["prepare_s"] = round(time.time() - t0, 1)
    log["render_s"] = V4["render"](f"{out_dir}/{mode}{scale}x.exr")
    log["samples"] = s.eevee.taa_render_samples
    json.dump(log, open(f"{out_dir}/log_{mode}{scale}x.json", "w"), indent=1, default=float)
    print("DONE", mode, log["render_s"])


main()
