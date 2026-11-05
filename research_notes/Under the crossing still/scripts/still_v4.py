"""The v4 shot `under-the-crossing` (30 s, still camera): view f re-framed on the line's axis, the plants mirrored
about it with a young forest round tower 23 (place_v4.py), distant birds drawn (birds_v4.py), the flow dashes running
on the lit wires. Runs inside Blender on the flight south's scene file at frame 4001 (the record's last state, 11
September 2026: Ferosplavna-1 connected, Dniprovska cut), NEVER saving it:

    blender -b --factory-startup <south.blend> -P still_v4.py -- <views_v4.json> <plants.npz> <out_dir> <mode> [args]

Modes (every render is film-transparent, linear EXR; the drawn dawn sky is laid under it by composite_v4.py, the same
gradient and glow as v3's world, evaluated per pixel in float so it cannot band):
  full K,K,...   everything (plants, wires with the flow at frame K of the shot, birds at K): to check and to compare
  static         everything that does not move (the flow's wires and the birds left out): rendered once
  anim A:B       only what moves (the lit wires with their flow, the birds), frames A..B-1, with every object that
                 could stand in front of them as a holdout (the plants only where their screen box meets the moving
                 parts: plants nowhere near them cannot hide them)
  world          the v3 dawn world alone, as EEVEE draws it (to look at the banding)

The flow: the scene keys each line material's "flow time" per frame ((frame - 1) / fps); here it is set by hand to
(4001 - 1) / 30 + K / 30 for frame K of the shot, everything else held at frame 4001's values, so the dashes run at
the film's own pace and the record's state stays put. Light: v3's dawn (the fixed sun turned to a mid-May sunrise,
the haze warmed). The plants are shaded the scene's way, as in v3 (still_v3.py's material and models).
"""

import json
import math
import os
import sys
import time

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
V3 = {"__file__": os.path.join(HERE, "still_v3.py"), "__name__": "still_v3"}
_src = open(os.path.join(HERE, "still_v3.py")).read()
exec(compile(_src[:_src.rindex("\nmain()")], "still_v3.py", "exec"), V3)   # v3's functions, without running it
import birds_v4 as BI  # noqa: E402

PL = V3["PL"]
FRAME, FPS = 4001, 30
SIZE = V3["SIZE"]
SAMPLES = 32


def lin(c):
    return V3["lin"](c)


VIEW_ID = "f4"        # the view in the views file (v5's still_v5.py picks v3's f)


def camera_of(view):
    if "cam" in view:     # a view placed as in v3 (views.json): position and heading given
        return np.array(view["cam"], float), None, float(view["heading"])
    a, b = np.array(view["tower_from"]), np.array(view["tower_to"])
    ax = (b - a) / np.linalg.norm(b - a)
    cam = b - ax * view["back_m"]
    heading = math.degrees(math.atan2(ax[0], ax[1])) % 360
    return cam, ax, heading


def setup(view):
    s = bpy.context.scene
    s.frame_set(FRAME)
    co = s.camera
    old_lens = co.data.lens
    co.animation_data_clear()
    co.data.animation_data_clear()
    co.rotation_mode = "XYZ"
    co.data.clip_start = 0.04
    co.data.sensor_fit = "HORIZONTAL"
    co.data.sensor_width = 36.0
    minw = []
    for ng in bpy.data.node_groups:
        ks = [nd for nd in ng.nodes if nd.label == "min width"]
        if ks:
            minw.append((ks[0], ks[0].outputs[0].default_value))
            ng.animation_data_clear()
    # the flow's clock: unkeyed, so it can be stepped by hand; every other key stays (the frame never changes)
    flow_t = []
    for m in bpy.data.materials:
        nt = m.node_tree
        if not nt:
            continue
        for nd in [nd for nd in nt.nodes if nd.label == "flow time"]:
            # an unkeyed twin takes over the keyed node's links (the keys stay in the file, unused here)
            tw = nt.nodes.new("ShaderNodeValue")
            tw.label = "flow time v4"
            for ln in list(nd.outputs[0].links):
                nt.links.new(tw.outputs[0], ln.to_socket)
            flow_t.append((m, tw))
    s.frame_set(FRAME)
    # which lines run: those whose keyed "flow" is above 0 at this frame
    running = set()
    for m in bpy.data.materials:
        if m.node_tree and any(nd.label == "flow" and nd.outputs[0].default_value > 1e-4 for nd in m.node_tree.nodes):
            running.add(m.name.split(" ", 1)[1])
    haze = next(((nd.inputs["From Min"].default_value, nd.inputs["From Max"].default_value)
                 for m in bpy.data.materials if m.node_tree for nd in m.node_tree.nodes if nd.label == "haze"),
                (7000.0, 16000.0))
    mat = V3["plant_material"](haze)
    t0 = time.time()
    protos, index, tris = V3["build_protos"](mat)
    print("PROTOS", len(index), "tris", tris, "%.1fs" % (time.time() - t0))
    s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage = *SIZE, 100
    s.eevee.taa_render_samples = SAMPLES
    s.render.film_transparent = True
    s.render.image_settings.file_format = "OPEN_EXR"
    s.render.image_settings.color_depth = "16"
    s.render.image_settings.exr_codec = "ZIP"
    s.render.image_settings.color_mode = "RGBA"
    s.frame_start = s.frame_end = FRAME
    # dawn, as v3: the fixed sun turned to a mid-May sunrise, the haze warmed (a view's "light": "day" keeps the
    # film's own: its fixed sun, its haze and its overcast world)
    day = view.get("light", "dawn") == "day"
    dots = [nd for m in bpy.data.materials if m.node_tree for nd in m.node_tree.nodes
            if nd.type == "VECT_MATH" and nd.operation == "DOT_PRODUCT"
            and tuple(round(x, 2) for x in nd.inputs[1].default_value) == V3["SUN_DAY"]]
    hazes = [nd for m in bpy.data.materials if m.node_tree for nd in m.node_tree.nodes
             if nd.type == "MIX" and nd.data_type == "RGBA"
             and tuple(round(x, 2) for x in nd.inputs["B"].default_value[:3]) == V3["HAZE_RGB"]]
    az, el = math.radians(V3["DAWN_AZ"]), math.radians(V3["DAWN_EL"])
    sun = (math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el))
    if day:
        sun = V3["SUN_DAY"]
        dawn = s.world
    else:
        for nd in dots:
            nd.inputs[1].default_value = sun
        for nd in hazes:
            nd.inputs["B"].default_value = (*lin((222, 200, 186)), 1)
        dawn = V3["dawn_world"](sun)
    # the camera, on the axis
    cam, ax, heading = camera_of(view)
    gz, gname = V3["camera_ground"](s, float(cam[0]), float(cam[1]))
    co.location = (float(cam[0]), float(cam[1]), gz + view["eye"])
    co.rotation_euler = (math.radians(90 + view["pitch"]), 0.0, -math.radians(heading))
    co.data.lens = view["lens"]
    for nd, w0 in minw:
        nd.outputs[0].default_value = w0 * old_lens / view["lens"] * 960 / SIZE[0]
    bpy.context.view_layer.update()          # the camera's matrix, for project()
    return dict(s=s, co=co, protos=protos, index=index, tris=tris, flow_t=flow_t, running=running, dawn=dawn,
                sun=sun, cam=cam, heading=heading, ground=gz, ground_on=gname, haze=haze)


def plants(ctx, npz):
    s = ctx["s"]
    T = np.load(npz)
    pts = T["pts"].astype(np.float64)
    origin = T["origin"] if "origin" in T.files else np.zeros(len(pts), np.int8)    # v3's files: all by rule
    t1 = time.time()
    keep, z, hits = V3["lay_on_ground"](s, pts)
    pts, z, origin = pts[keep], z[keep], origin[keep]
    fam, lod, var = pts[:, 3].astype(int), pts[:, 6].astype(int), pts[:, 7].astype(int)
    lod = np.array([min(l, max(PL.FAMILIES[f][3])) for f, l in zip(fam, lod)])
    idx = np.array([ctx["index"][(f, l, w)] for f, l, w in zip(fam, lod, var)])
    Hm = np.array([PL.FAMILIES[f][2] for f in fam])
    P = np.column_stack([pts[:, 0], pts[:, 1], z - 0.03, pts[:, 4], pts[:, 5] / Hm, idx])
    info = {"plants": int(keep.sum()), "left_out": int((~keep).sum()), "met_first": hits,
            "by_origin": {o: int((origin == i).sum()) for i, o in enumerate(("rule", "mirrored", "base"))},
            "lay_s": round(time.time() - t1, 1)}
    return P, pts, z, info


def flow_at(ctx, k):
    for m, nd in ctx["flow_t"]:
        nd.outputs[0].default_value = (FRAME - 1) / FPS + k / FPS


def moving(ctx):
    """The lit lines' wire and glow objects (their flow runs) and the birds."""
    return [ob for ob in bpy.data.objects
            if (ob.name.startswith(("wire ", "glow ")) and ob.name.split(" ", 1)[1] in ctx["running"])
            or ob.name == "fittings"]      # the insulator strings the lit wires pass through: drawn with them


def freeze():
    """Hold everything at frame 4001's values: the scene's keys (record state, haze, water, ripples) are dropped
    after the frame is evaluated, so later frame numbers change nothing but what this script keys."""
    n = 0
    for coll in (bpy.data.objects, bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.node_groups,
                 bpy.data.shape_keys, bpy.data.cameras, bpy.data.worlds, bpy.data.scenes, bpy.data.lights):
        for idb in coll:
            if getattr(idb, "animation_data", None):
                idb.animation_data_clear(); n += 1
            nt = getattr(idb, "node_tree", None)
            if nt is not None and nt.animation_data:
                nt.animation_data_clear(); n += 1
    return n


def project(ctx, P3):
    """World points (n, 3) to pixels (x right, y down) and depth, for the still camera."""
    co = ctx["co"]
    M = np.array(co.matrix_world.inverted())
    Q = P3 @ M[:3, :3].T + M[:3, 3]
    d = -Q[:, 2]
    f = co.data.lens / co.data.sensor_width
    x = (0.5 + f * Q[:, 0] / np.maximum(d, 1e-3)) * SIZE[0]
    y = (0.5 - f * Q[:, 1] / np.maximum(d, 1e-3) * SIZE[0] / SIZE[1]) * SIZE[1]
    return x, y, d


def wire_points(ctx, names):
    out = []
    for nm in names:
        ob = bpy.data.objects.get(nm)
        if ob is None or ob.type != "CURVE":
            continue
        for sp in ob.data.splines:
            pts = np.array([p.co[:3] for p in sp.points]) if len(sp.points) else np.array([p.co[:] for p in sp.bezier_points])
            if len(pts) < 2:
                continue
            # dense along each span, so the screen polyline follows the sag
            t = np.linspace(0, 1, max(2, 8 * len(pts)))
            seg = np.interp(t * (len(pts) - 1), np.arange(len(pts)), np.arange(len(pts)))
            i0 = np.minimum(seg.astype(int), len(pts) - 2)
            fr = (seg - i0)[:, None]
            out.append(pts[i0] * (1 - fr) + pts[i0 + 1] * fr)
    return out


def mask_of(ctx, polylines, pad):
    W, H = SIZE
    m = np.zeros((H, W), bool)
    for P3 in polylines:
        x, y, d = project(ctx, P3)
        ok = d > 1
        for i in range(len(x) - 1):
            if not (ok[i] and ok[i + 1]):
                continue
            n = int(max(abs(x[i + 1] - x[i]), abs(y[i + 1] - y[i]))) + 1
            if n > 6000:
                continue
            xs = np.linspace(x[i], x[i + 1], n).astype(int)
            ys = np.linspace(y[i], y[i + 1], n).astype(int)
            v = (xs >= 0) & (xs < W) & (ys >= 0) & (ys < H)
            m[ys[v], xs[v]] = True
    return dilate(m, pad)


def dilate(m, pad):
    if pad <= 0:
        return m
    out = m.copy()
    ys, xs = np.nonzero(m)
    for dy in range(-pad, pad + 1, max(1, pad // 3)):
        for dx in range(-pad, pad + 1, max(1, pad // 3)):
            yy, xx = np.clip(ys + dy, 0, m.shape[0] - 1), np.clip(xs + dx, 0, m.shape[1] - 1)
            out[yy, xx] = True
    return out


def plant_boxes(ctx, P, pts):
    """Each plant's screen box, generously: its stem from the ground to its top, widened by its crown."""
    h = pts[:, 5]
    fam = pts[:, 3].astype(int)
    rad = np.where(np.isin(fam, (0, 1)), 0.75 * h, np.where(np.isin(fam, (2, 3, 4, 5)), 0.6 * h, 0.5 * h)) + 0.3
    base = P[:, :3].copy()
    boxes = []
    xs, ys = [], []
    for dz in (0.0, 0.5, 1.0, 1.15):
        for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            q = base + np.column_stack([dx * rad, dy * rad, dz * h])
            x, y, d = project(ctx, q)
            bad = d <= 0.05
            x = np.where(bad, np.where(x > SIZE[0] / 2, 1e6, -1e6), x)
            y = np.where(bad, -1e6, y)
            xs.append(x); ys.append(y)
    xs, ys = np.array(xs), np.array(ys)
    return xs.min(0) - 2, xs.max(0) + 2, ys.min(0) - 2, ys.max(0) + 2


def overlaps(boxes, mask):
    x0, x1, y0, y1 = boxes
    H, W = mask.shape
    I = np.zeros((H + 1, W + 1), np.int64)
    I[1:, 1:] = mask.cumsum(0).cumsum(1)
    a0 = np.clip(np.floor(x0), 0, W).astype(int); a1 = np.clip(np.ceil(x1), 0, W).astype(int)
    b0 = np.clip(np.floor(y0), 0, H).astype(int); b1 = np.clip(np.ceil(y1), 0, H).astype(int)
    tot = I[b1, a1] - I[b0, a1] - I[b1, a0] + I[b0, a0]
    return tot > 0


def birds_object():
    mat = bpy.data.materials.new("birds v4")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    at = nt.nodes.new("ShaderNodeAttribute"); at.attribute_name = "col"
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(at.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    me = bpy.data.meshes.new("birds v4")
    ob = bpy.data.objects.new("birds v4", me)
    ob.visible_shadow = False
    me.materials.append(mat)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def set_birds(ob, V, F, C):
    me = ob.data
    me.clear_geometry()
    if len(F) == 0:
        return
    me.vertices.add(len(V))
    me.vertices.foreach_set("co", V.astype(np.float32).ravel())
    me.loops.add(len(F) * 3)
    me.loops.foreach_set("vertex_index", F.astype(np.int32).ravel())
    me.polygons.add(len(F))
    me.polygons.foreach_set("loop_start", (np.arange(len(F)) * 3).astype(np.int32))
    me.update(calc_edges=True)
    a = me.attributes.get("col") or me.attributes.new("col", "FLOAT_COLOR", "FACE")
    a.data.foreach_set("color", np.column_stack([C, np.ones(len(C))]).astype(np.float32).ravel())


def _fcurves(ad):
    """An animation's F-curves (Blender 5's layered actions, or the older flat list)."""
    if ad is None or ad.action is None:
        return []
    act = ad.action
    if hasattr(act, "fcurves"):
        try:
            return list(act.fcurves)
        except Exception:
            pass
    from bpy_extras import anim_utils
    cb = anim_utils.action_get_channelbag_for_slot(act, ad.action_slot)
    return list(cb.fcurves) if cb else []


def render(path):
    s = bpy.context.scene
    s.render.filepath = path
    t = time.time()
    bpy.ops.render.render(write_still=True)
    return round(time.time() - t, 2)


def main():
    a = sys.argv[sys.argv.index("--") + 1:]
    views_json, npz, out_dir, mode = a[:4]
    rest = a[4:]
    view = next(v for v in json.load(open(views_json))["views"] if v["id"] == VIEW_ID)
    os.makedirs(out_dir, exist_ok=True)
    t0 = time.time()
    ctx = setup(view)
    s = ctx["s"]
    log = {"mode": mode, "camera": {"location": list(ctx["co"].location), "heading": ctx["heading"],
                                    "pitch": view["pitch"], "lens": view["lens"], "ground_m": round(ctx["ground"], 2),
                                    "on": ctx["ground_on"]},
           "running": sorted(ctx["running"]), "protos_tris": ctx["tris"]}
    if mode == "mask":     # where birds must never be: every line's wires and earth wires, and the towers in frame
        names = [o.name for o in bpy.data.objects if o.name.startswith(("wire ", "earth "))]
        m = mask_of(ctx, wire_points(ctx, names), 0)
        for ob in bpy.data.objects:
            if ob.name.startswith(("crossing", "caisson", "pvs", "pp750", "triple", "gantry")) and ob.type == "MESH":
                V = np.array([ob.matrix_world @ v.co for v in ob.data.vertices])
                x, y, d = project(ctx, V)
                ok = d > 1
                if not ok.any():
                    continue
                x0, x1, y0, y1 = x[ok].min(), x[ok].max(), y[ok].min(), y[ok].max()
                if x1 < 0 or x0 > SIZE[0] or y1 < 0 or y0 > SIZE[1]:
                    continue
                m[max(0, int(y0)):int(min(SIZE[1], y1 + 1)), max(0, int(x0)):int(min(SIZE[0], x1 + 1))] = True
        np.save(f"{out_dir}/mask.npy", m)
        log["mask_px"] = int(m.sum())
        json.dump(log, open(f"{out_dir}/log_mask.json", "w"), indent=1, default=float)
        return
    if mode == "world":
        for ob in list(bpy.data.objects):
            if ob.type != "CAMERA":
                ob.hide_render = True
        s.world = ctx["dawn"]
        s.render.film_transparent = False
        s.render.image_settings.file_format = "PNG"
        s.render.image_settings.color_depth = "16"
        s.render.dither_intensity = 0.0
        log["render_s"] = render(f"{out_dir}/world_eevee.png")
        json.dump(log, open(f"{out_dir}/log_world.json", "w"), indent=1)
        return
    s.world = ctx["dawn"]          # (film-transparent: the sky is laid under in the composite)
    if mode != "anim":     # the moving pass draws no plants at all (the matte stands in for them)
        P, pts, z, info = plants(ctx, npz)
        log["plants"] = info
        sob = V3["scatter"](P, ctx["protos"], f"plants {VIEW_ID}")   # (the name seeds Object Info Random: v3 named its plants "plants f")
    bob = birds_object()
    flock = BI.Flock(ctx["cam"], ctx["heading"], ctx["ground"], view)
    mov = moving(ctx)
    log["moving"] = [o.name for o in mov]
    log["prepare_s"] = round(time.time() - t0, 1)
    if mode == "full":
        for k in [int(x) for x in rest[0].split(",")]:
            flow_at(ctx, k)
            set_birds(bob, *flock.mesh(k / FPS))
            log[f"render_full_{k}_s"] = render(f"{out_dir}/full_{k:04d}.exr")
            print("WROTE full", k, log[f"render_full_{k}_s"])
    elif mode == "static":
        for ob in mov + [bob]:
            ob.hide_render = True
        log["render_static_s"] = render(f"{out_dir}/static.exr")
    elif mode == "matte":
        # how much of each pixel of the moving wires (lit wires, their glow and fittings, all static geometry: only
        # their shading moves) is left in view by everything else: their footprint drawn flat white, once with every
        # other object (all the plants included) as a holdout (A) and once alone (B); A / B per pixel
        white = bpy.data.materials.new("matte white")
        white.use_nodes = True
        nt = white.node_tree
        for n in list(nt.nodes):
            if n.type != "OUTPUT_MATERIAL":
                nt.nodes.remove(n)
        em = nt.nodes.new("ShaderNodeEmission")
        nt.links.new(em.outputs[0], next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL").inputs["Surface"])
        bpy.context.view_layer.material_override = white
        bob.hide_render = True
        others = [ob for ob in bpy.data.objects if ob.type in ("MESH", "CURVE") and ob not in mov and ob is not bob]
        for ob in others:
            ob.is_holdout = True
        log["render_matte_A_s"] = render(f"{out_dir}/matte_A.exr")
        for ob in others:
            ob.hide_render = True
        log["render_matte_B_s"] = render(f"{out_dir}/matte_B.exr")
    elif mode == "anim":
        A, B = (int(x) for x in rest[0].split(":"))
        # only what moves: the lit wires (their glow and fittings) and the birds, over nothing; composite_v4.py
        # takes the occlusion of the wires from the matte and of the birds from the static plate's alpha
        for ob in bpy.data.objects:
            if ob.type in ("MESH", "CURVE") and ob not in mov and ob is not bob:
                ob.hide_render = True
        # one animation render (the render keeps its scene between frames: only the flow and the birds change)
        log["frozen_ids"] = freeze()
        for m, nd in ctx["flow_t"]:
            nt = m.node_tree
            for f, v in ((0, (FRAME - 1) / FPS), (FPS, (FRAME - 1) / FPS + 1.0)):
                nd.outputs[0].default_value = v
                nd.outputs[0].keyframe_insert("default_value", frame=f)
            for fc in _fcurves(nt.animation_data):
                fc.extrapolation = "LINEAR"
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"

        def birds_at(scene, *_):
            set_birds(bob, *flock.mesh(scene.frame_current / FPS))

        bpy.app.handlers.frame_change_pre.append(birds_at)
        s.render.use_lock_interface = True
        s.frame_start, s.frame_end = A, B - 1
        os.makedirs(f"{out_dir}/anim", exist_ok=True)
        s.render.filepath = f"{out_dir}/anim/anim_####"
        s.frame_set(A)
        t = time.time()
        bpy.ops.render.render(animation=True)
        tot = time.time() - t
        log["render_anim_s"] = {"frames": [A, B], "mean": round(tot / (B - A), 2), "total": round(tot, 1)}
    log["total_s"] = round(time.time() - t0, 1)
    tag = mode if mode != "anim" else f"anim_{rest[0].replace(':', '-')}"
    json.dump(log, open(f"{out_dir}/log_{tag}.json", "w"), indent=1, default=float)


main()
