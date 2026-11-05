"""The v5 shot `under-the-crossing` and its reprise (the user, 5 November 2026: "i prefer the composition of the
original "f day" still ... re-render the video so it is like the original "f day" proposal ... during the day", and
a separate short where the same view is shown "with the water line appearing as a reprise").

v3's view f exactly (views_v5.json: v3's camera, v3's plants v3/plants/plants_f.npz), in the film's day light (its
fixed sun, its haze and its overcast world, as v3's f_day.png), the flow dashes running at frame 4001's state, the
birds of birds_v5.py. Everything else is still_v4.py's (exec'd without its main): its modes mask, world, full,
static, matte and anim work the same here. One mode more:

  contour        the proposed level as a line (the reprise): every surface drawn flat black except a thin band where
                 its world height is within a few centimetres of the level, drawn white; film-transparent, so the
                 band's red channel is the line's matte (composite_v5.py lays it on the picture). The band's height
                 is scaled with the distance to the eye and the surface's slope, so it stays about 7 px wide on
                 screen whatever the surface (a level surface is held to sin(slope) 0.15, so a flat leaf or flat
                 ground at the level shows a thin band, never lit whole). Not water: no surface,
                 fill or tint is drawn, only where the scene's own surfaces cross that height.

    blender -b --factory-startup <south.blend> -P still_v5.py -- views_v5.json ../v3/plants/plants_f.npz <out> <mode>

The level: 12.7 m Baltic (Vyshnevskyi & Shevchuk 2024, p. 286: the dead-volume level, proposed for a refilled
reservoir), raised by the scene's Baltic-to-EGM2008 offset (+0.4 m, config crossing3d.bed baltic_m; the scene's z is
FABDEM's metres above EGM2008) to 13.1 m in scene units.
"""
import json
import math
import os
import sys
import time

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import birds_v5  # noqa: E402,F401  (sets birds_v4's camera, haze and paths for this view)

V4 = {"__file__": os.path.join(HERE, "still_v4.py"), "__name__": "still_v4"}
_src = open(os.path.join(HERE, "still_v4.py")).read()
exec(compile(_src[:_src.rindex("\nmain()")], "still_v4.py", "exec"), V4)
V4["VIEW_ID"] = "f"

LEVEL_BALTIC = 12.7
BALTIC_TO_EGM2008 = 0.4
LEVEL = LEVEL_BALTIC + BALTIC_TO_EGM2008           # 13.1 m, scene z
LINE_PX = 7.0                                       # the band's width on screen (px), for a surface seen square-on
MIN_SLOPE = 0.15                                    # sin(slope) held to at least this: a level surface (a leaf
                                                    # card lying flat, flat ground) keeps a thin band, never lit whole
FLOOR_M = 0.001                                     # the band's least half-height (m)


def contour_material(lens, width_px):
    m = bpy.data.materials.new("waterline v5")
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    N = nt.nodes.new
    L = nt.links.new
    geo = N("ShaderNodeNewGeometry")
    cam = N("ShaderNodeCameraData")
    sep = N("ShaderNodeSeparateXYZ"); L(geo.outputs["Position"], sep.inputs[0])
    sepn = N("ShaderNodeSeparateXYZ"); L(geo.outputs["Normal"], sepn.inputs[0])

    def op(o, a, b=None):
        n = N("ShaderNodeMath"); n.operation = o
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                L(v, n.inputs[i])
        return n.outputs[0]

    dz = op("ABSOLUTE", op("SUBTRACT", sep.outputs["Z"], LEVEL))
    # metres per pixel at this distance (36 mm sensor across 1920 px), times the half-width in px
    px = op("MULTIPLY", cam.outputs["View Distance"], 36.0 / (lens * 1920.0) * width_px / 2)
    # a slope's band of height h spans h / sin(slope) along the surface: scale h by sin(slope) = sqrt(1 - nz^2)
    sin_s = op("SQRT", op("MAXIMUM", op("SUBTRACT", 1.0, op("MULTIPLY", sepn.outputs["Z"], sepn.outputs["Z"])), 0.0))
    half = op("MAXIMUM", op("MULTIPLY", px, op("MAXIMUM", sin_s, MIN_SLOPE)), FLOOR_M)
    band = op("LESS_THAN", dz, half)
    em = N("ShaderNodeEmission")
    L(band, em.inputs["Strength"])
    em.inputs["Color"].default_value = (1, 1, 1, 1)
    L(em.outputs[0], out.inputs["Surface"])
    return m


def contour(view, npz, out_dir):
    t0 = time.time()
    ctx = V4["setup"](view)
    s = ctx["s"]
    P, pts, z, info = V4["plants"](ctx, npz)
    V4["V3"]["scatter"](P, ctx["protos"], "plants f")
    # the glows are light round the wires, not surfaces: left out; every other surface holds the band or hides it
    hidden = [ob.name for ob in bpy.data.objects if ob.name.startswith("glow ")]
    for nm in hidden:
        bpy.data.objects[nm].hide_render = True
    bpy.context.view_layer.material_override = contour_material(view["lens"], LINE_PX)
    s.render.film_transparent = True
    prep = round(time.time() - t0, 1)
    t = V4["render"](f"{out_dir}/contour.exr")
    cz = float(ctx["co"].location[2])
    log = {"mode": "contour", "level_baltic_m": LEVEL_BALTIC, "baltic_to_egm2008_m": BALTIC_TO_EGM2008,
           "level_scene_m": LEVEL, "line_px": LINE_PX, "min_slope_sin": MIN_SLOPE, "floor_half_m": FLOOR_M,
           "camera": {"location": list(ctx["co"].location), "ground_m": round(ctx["ground"], 2),
                      "eye_m": round(cz, 2), "eye_below_level_m": round(LEVEL - cz, 2)},
           "hidden": hidden, "plants": info, "prepare_s": prep, "render_s": t}
    json.dump(log, open(f"{out_dir}/log_contour.json", "w"), indent=1, default=float)


def main():
    a = sys.argv[sys.argv.index("--") + 1:]
    if a[3] == "contour":
        view = next(v for v in json.load(open(a[0]))["views"] if v["id"] == V4["VIEW_ID"])
        os.makedirs(a[2], exist_ok=True)
        contour(view, a[1], a[2])
    else:
        V4["main"]()


main()
