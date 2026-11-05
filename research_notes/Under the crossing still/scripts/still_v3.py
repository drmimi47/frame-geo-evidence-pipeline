"""The v3 comparison stills for `under-the-crossing` (the user, 5 November 2026: "add more trees, vegetation,
different types of plants ... generate other views so i can compare too"). Runs inside Blender on the flight south's
scene file at one of its frames (the record's state there: 11 September 2026, Ferosplavna-1 connected, Dniprovska
cut; the 2025 pass on the land), NEVER saving it:

    blender -b --factory-startup <ZNPP-last-two-lines-3D-south.blend> -P still_v3.py -- \
        <views.json> <plants_dir> <out_dir> <dawn,day> [view ids ...]
    blender -b --factory-startup -P still_v3.py -- specimens <out.png>        (the models alone, on grey)

Adds, for these stills only: the plants placed by place_plants.py (13 kinds, plants.py: representative models built
from numbers, at three levels of detail by distance), each laid on the scene's own ground (a ray down onto the land;
a plant whose ray meets the scene's water, a caisson or a tower first is left out); a still camera per view; for
`dawn`, a drawn sky (a gradient and the low sun's glow) with the haze and the fixed sun turned to a mid-May sunrise.
Everything is shaded the scene's way (unlit colour, by a fixed sun, into the haze by distance), so the plants sit with
the towers. The towers, wires, water and land are the scene's own.
"""

import json
import math
import os
import sys
import time

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plants as PL  # noqa: E402

FRAME = 4001
SIZE = (1920, 1080)
HAZE_RGB = (0.62, 0.66, 0.70)
SUN_DAY = (0.35, -0.61, 0.71)
DAWN_AZ, DAWN_EL = 57.0, 6.0          # mid-May sunrise at 47.5 N: azimuth about 57°, just up
NVAR = 4
THIN = ("wire ", "earth ", "glow ", "fittings")


def lin(c):
    return tuple(((v / 255 + 0.055) / 1.055) ** 2.4 if v / 255 > 0.04045 else v / 255 / 12.92 for v in c)


# ---------- the plants' one material, the scene's way: an unlit colour shaded by the fixed sun, hazed by distance

def plant_material(haze):
    mat = bpy.data.materials.new("plant v3")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    N, Lk = nt.nodes, nt.links.new
    col = N.new("ShaderNodeAttribute"); col.attribute_name = "col"
    card = N.new("ShaderNodeAttribute"); card.attribute_name = "card"
    geo = N.new("ShaderNodeNewGeometry")
    dot = N.new("ShaderNodeVectorMath"); dot.operation = "DOT_PRODUCT"; dot.inputs[1].default_value = SUN_DAY
    dot.label = "plant sun"
    Lk(geo.outputs["Normal"], dot.inputs[0])
    stem = N.new("ShaderNodeMath"); stem.operation = "MULTIPLY_ADD"          # as the towers: 0.35 away, 1.0 facing
    stem.inputs[1].default_value, stem.inputs[2].default_value = 0.325, 0.675
    Lk(dot.outputs["Value"], stem.inputs[0])
    ab = N.new("ShaderNodeMath"); ab.operation = "ABSOLUTE"                   # thin cards pass light: either face
    Lk(dot.outputs["Value"], ab.inputs[0])
    cardsh = N.new("ShaderNodeMath"); cardsh.operation = "MULTIPLY_ADD"
    cardsh.inputs[1].default_value, cardsh.inputs[2].default_value = 0.32, 0.68
    Lk(ab.outputs[0], cardsh.inputs[0])
    mx = N.new("ShaderNodeMix"); mx.data_type = "FLOAT"
    Lk(card.outputs["Fac"], mx.inputs["Factor"])
    Lk(stem.outputs[0], mx.inputs["A"]); Lk(cardsh.outputs[0], mx.inputs["B"])
    oi = N.new("ShaderNodeObjectInfo")                                        # each plant a little lighter or darker
    br = N.new("ShaderNodeMath"); br.operation = "MULTIPLY_ADD"
    br.inputs[1].default_value, br.inputs[2].default_value = 0.26, 0.87
    Lk(oi.outputs["Random"], br.inputs[0])
    k = N.new("ShaderNodeMath"); k.operation = "MULTIPLY"
    Lk(mx.outputs["Result"], k.inputs[0]); Lk(br.outputs[0], k.inputs[1])
    sc = N.new("ShaderNodeVectorMath"); sc.operation = "SCALE"
    Lk(col.outputs["Color"], sc.inputs[0]); Lk(k.outputs[0], sc.inputs["Scale"])
    cam = N.new("ShaderNodeCameraData")
    rng_ = N.new("ShaderNodeMapRange"); rng_.interpolation_type = "SMOOTHSTEP"
    rng_.inputs["From Min"].default_value, rng_.inputs["From Max"].default_value = haze
    Lk(cam.outputs["View Distance"], rng_.inputs["Value"])
    hz = N.new("ShaderNodeMix"); hz.data_type = "RGBA"
    hz.inputs["B"].default_value = (*HAZE_RGB, 1)
    Lk(rng_.outputs["Result"], hz.inputs["Factor"]); Lk(sc.outputs["Vector"], hz.inputs["A"])
    em = N.new("ShaderNodeEmission")
    Lk(hz.outputs["Result"], em.inputs["Color"])
    Lk(em.outputs[0], out.inputs["Surface"])
    return mat


def to_object(name, geo, mat):
    V, F, C, K = geo.arrays()
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(V))
    me.vertices.foreach_set("co", V.astype(np.float32).ravel())
    me.loops.add(len(F) * 3)
    me.loops.foreach_set("vertex_index", F.astype(np.int32).ravel())
    me.polygons.add(len(F))
    me.polygons.foreach_set("loop_start", (np.arange(len(F)) * 3).astype(np.int32))
    me.update(calc_edges=True)
    a = me.attributes.new("col", "FLOAT_COLOR", "FACE")
    a.data.foreach_set("color", np.column_stack([C, np.ones(len(C))]).astype(np.float32).ravel())
    b = me.attributes.new("card", "FLOAT", "FACE")
    b.data.foreach_set("value", K.astype(np.float32))
    me.materials.append(mat)
    return bpy.data.objects.new(name, me)


def build_protos(mat):
    """Every family at each of its levels of detail, NVAR variants each, in one collection; index by (family, lod, var)."""
    col = bpy.data.collections.new("plant prototypes v3")
    index, k, tris = {}, 0, 0
    for fam, (name, fn, H, lods) in PL.FAMILIES.items():
        for lod in lods:
            for var in range(NVAR):
                geo = fn(1000 * fam + var, lod, H)      # the seed's last digit is the variant (plants.py uses it)
                ob = to_object(f"p{k:03d}", geo, mat)
                ob.visible_shadow = False
                tris += len(ob.data.polygons)
                col.objects.link(ob)
                index[(fam, lod, var)] = k
                k += 1
    return col, index, tris


def scatter(P, protos, name):
    """P: x, y, z, rot, scale, idx."""
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(P))
    me.vertices.foreach_set("co", P[:, :3].astype(np.float32).ravel())
    for key, typ, j in (("idx", "INT", 5), ("rot", "FLOAT", 3), ("scl", "FLOAT", 4)):
        a = me.attributes.new(key, typ, "POINT")
        a.data.foreach_set("value", P[:, j].astype(np.int32 if typ == "INT" else np.float32))
    ob = bpy.data.objects.new(name, me)
    ob.visible_shadow = False            # unlit like the scene: no shadow maps for a million leaves
    bpy.context.scene.collection.objects.link(ob)
    ng = bpy.data.node_groups.new(name, "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    n = ng.nodes
    gi, go = n.new("NodeGroupInput"), n.new("NodeGroupOutput")
    ci = n.new("GeometryNodeCollectionInfo")
    ci.inputs["Collection"].default_value = protos
    ci.inputs["Separate Children"].default_value = True
    ci.inputs["Reset Children"].default_value = True
    iop = n.new("GeometryNodeInstanceOnPoints")
    iop.inputs["Pick Instance"].default_value = True
    na = {}
    for key, typ in (("idx", "INT"), ("rot", "FLOAT"), ("scl", "FLOAT")):
        na[key] = n.new("GeometryNodeInputNamedAttribute")
        na[key].data_type = typ
        na[key].inputs["Name"].default_value = key
    cxyz = n.new("ShaderNodeCombineXYZ")
    ng.links.new(na["rot"].outputs["Attribute"], cxyz.inputs["Z"])
    ng.links.new(gi.outputs[0], iop.inputs["Points"])
    ng.links.new(ci.outputs[0], iop.inputs["Instance"])
    ng.links.new(na["idx"].outputs["Attribute"], iop.inputs["Instance Index"])
    ng.links.new(cxyz.outputs[0], iop.inputs["Rotation"])
    ng.links.new(na["scl"].outputs["Attribute"], iop.inputs["Scale"])
    ng.links.new(iop.outputs[0], go.inputs[0])
    ob.modifiers.new(name, "NODES").node_group = ng
    return ob


def dawn_world(sun):
    w = bpy.data.worlds.new("dawn v3")
    w.use_nodes = True
    nt = w.node_tree
    for nd in list(nt.nodes):
        if nd.type != "OUTPUT_WORLD":
            nt.nodes.remove(nd)
    out = next(nd for nd in nt.nodes if nd.type == "OUTPUT_WORLD")
    N = nt.nodes
    tc = N.new("ShaderNodeTexCoord")
    nrm = N.new("ShaderNodeVectorMath"); nrm.operation = "NORMALIZE"
    nt.links.new(tc.outputs["Generated"], nrm.inputs[0])
    sep = N.new("ShaderNodeSeparateXYZ")
    nt.links.new(nrm.outputs[0], sep.inputs[0])
    ramp = N.new("ShaderNodeValToRGB")      # the sky by height: warm at the horizon, pale, then a clear blue
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = 0.0, (*lin((236, 196, 164)), 1)
    els[1].position, els[1].color = 0.55, (*lin((118, 150, 196)), 1)
    e = els.new(0.12)
    e.color = (*lin((214, 204, 196)), 1)
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    d = N.new("ShaderNodeVectorMath"); d.operation = "DOT_PRODUCT"   # the low sun's glow, round its direction
    d.inputs[1].default_value = sun
    nt.links.new(nrm.outputs[0], d.inputs[0])
    pw = N.new("ShaderNodeMath"); pw.operation = "POWER"
    nt.links.new(d.outputs["Value"], pw.inputs[0])
    pw.inputs[1].default_value = 10.0
    cl = N.new("ShaderNodeClamp")
    nt.links.new(pw.outputs[0], cl.inputs["Value"])
    mix = N.new("ShaderNodeMix"); mix.data_type = "RGBA"
    mix.inputs["B"].default_value = (*lin((255, 214, 160)), 1)
    nt.links.new(cl.outputs[0], mix.inputs["Factor"])
    nt.links.new(ramp.outputs["Color"], mix.inputs["A"])
    bg = N.new("ShaderNodeBackground")
    nt.links.new(mix.outputs["Result"], bg.inputs["Color"])
    nt.links.new(bg.outputs[0], out.inputs["Surface"])
    return w


def lay_on_ground(s, pts):
    """A ray down at each plant: keep it only where the first thing met is the land, and stand it there."""
    dg = bpy.context.evaluated_depsgraph_get()
    keep = np.zeros(len(pts), bool)
    z = np.zeros(len(pts))
    hits = {}
    for i, (x, y) in enumerate(pts[:, :2]):
        z0, name = 400.0, None
        for _ in range(80):          # wires, their glow and fittings are passed through, not stood under
            ok, loc, nrm, idx, ob, mtx = s.ray_cast(dg, (float(x), float(y), z0), (0.0, 0.0, -1.0))
            if not ok:
                name = None
                break
            name = ob.name
            if not name.startswith(THIN):
                break
            z0 = loc[2] - 0.6
        if name is None:
            continue
        if name.startswith("land"):
            keep[i] = True
            z[i] = loc[2]
        else:
            key = name.split(" 1")[0]
            hits[key] = hits.get(key, 0) + 1
    return keep, z, hits


def camera_ground(s, x, y):
    dg = bpy.context.evaluated_depsgraph_get()
    z0 = 400.0
    for _ in range(80):
        ok, loc, nrm, idx, ob, mtx = s.ray_cast(dg, (x, y, z0), (0.0, 0.0, -1.0))
        if not ok or not ob.name.startswith(THIN):
            break
        z0 = loc[2] - 0.6
    return loc[2], ob.name if ok else None


def specimens(out, fams=None):
    """The models alone on grey, by family and variant, at the finest level: to check their shapes."""
    s = bpy.context.scene
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    mat = plant_material((7000.0, 16000.0))
    world = bpy.data.worlds.new("grey")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (*lin((200, 204, 208)), 1)
    s.world = world
    x, top = 0.0, 0.0
    fams = fams or list(PL.FAMILIES)
    for fam in fams:
        name, fn, H, lods = PL.FAMILIES[fam]
        for var in range(2):
            ob = to_object(f"s{fam}_{var}", fn(1000 * fam + var, 0, H), mat)
            s.collection.objects.link(ob)
            w = max(H * 0.8, 0.9)
            ob.location = (x + w / 2, 0, 0)
            x += w
            top = max(top, H)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    s.collection.objects.link(cam)
    s.camera = cam
    cam.data.type = "ORTHO"
    asp = 2.0
    cam.data.ortho_scale = max(x, top * 1.1 * asp)
    cam.location = (x / 2, -60, top * 0.55)
    cam.rotation_euler = (math.radians(90), 0, 0)
    s.render.resolution_x, s.render.resolution_y = 2400, 1200
    s.render.engine = "BLENDER_EEVEE"
    s.eevee.taa_render_samples = 16
    s.render.filepath = out
    bpy.ops.render.render(write_still=True)


def main():
    a = sys.argv[sys.argv.index("--") + 1:]
    if a[0] == "specimens":
        specimens(a[1], [int(f) for f in a[2:]] or None)
        return
    views_json, plants_dir, out_dir, lights = a[0], a[1], a[2], a[3].split(",")
    ids = a[4:]
    views = [v for v in json.load(open(views_json))["views"] if not ids or v["id"] in ids]
    os.makedirs(out_dir, exist_ok=True)
    s = bpy.context.scene
    s.frame_set(FRAME)
    t0 = time.time()
    co = s.camera
    old_lens = co.data.lens
    co.animation_data_clear()
    co.data.animation_data_clear()
    co.rotation_mode = "XYZ"
    co.data.clip_start = 0.04
    co.data.sensor_fit = "HORIZONTAL"
    co.data.sensor_width = 36.0
    minw = []                  # the wires' least width, keyed for the flight's lens at 960 px
    for ng in bpy.data.node_groups:
        ks = [nd for nd in ng.nodes if nd.label == "min width"]
        if ks:
            minw.append((ks[0], ks[0].outputs[0].default_value))
            ng.animation_data_clear()
    haze = next(((nd.inputs["From Min"].default_value, nd.inputs["From Max"].default_value)
                 for m in bpy.data.materials if m.node_tree for nd in m.node_tree.nodes if nd.label == "haze"),
                (7000.0, 16000.0))
    mat = plant_material(haze)
    protos, index, tris = build_protos(mat)
    print("PROTOS", len(index), "tris", tris, "%.1fs" % (time.time() - t0))
    s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage = *SIZE, 100
    s.eevee.taa_render_samples = 32
    s.render.dither_intensity = 2.0       # the drawn sky's gradient without bands
    s.render.image_settings.file_format = "PNG"
    s.frame_start = s.frame_end = FRAME
    dots = [nd for m in bpy.data.materials if m.node_tree for nd in m.node_tree.nodes
            if nd.type == "VECT_MATH" and nd.operation == "DOT_PRODUCT"
            and tuple(round(x, 2) for x in nd.inputs[1].default_value) == SUN_DAY]
    hazes = [nd for m in bpy.data.materials if m.node_tree for nd in m.node_tree.nodes
             if nd.type == "MIX" and nd.data_type == "RGBA"
             and tuple(round(x, 2) for x in nd.inputs["B"].default_value[:3]) == HAZE_RGB]
    day_world = s.world
    az, el = math.radians(DAWN_AZ), math.radians(DAWN_EL)
    sun = (math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el))
    dawn = dawn_world(sun) if "dawn" in lights else None
    log = {}
    for v in views:
        t1 = time.time()
        T = np.load(f"{plants_dir}/plants_{v['id']}.npz")
        pts = T["pts"].astype(np.float64)
        keep, z, hits = lay_on_ground(s, pts)
        pts = pts[keep]
        z = z[keep]
        fam, lod, var = pts[:, 3].astype(int), pts[:, 6].astype(int), pts[:, 7].astype(int)
        lod = np.array([min(l, max(PL.FAMILIES[f][3])) for f, l in zip(fam, lod)])
        idx = np.array([index[(f, l, w)] for f, l, w in zip(fam, lod, var)])
        Hm = np.array([PL.FAMILIES[f][2] for f in fam])
        P = np.column_stack([pts[:, 0], pts[:, 1], z - 0.03, pts[:, 4], pts[:, 5] / Hm, idx])
        sob = scatter(P, protos, f"plants {v['id']}")
        gz, gname = camera_ground(s, *v["cam"])
        co.location = (v["cam"][0], v["cam"][1], gz + v["eye"])
        co.rotation_euler = (math.radians(90 + v["pitch"]), 0.0, -math.radians(v["heading"]))
        co.data.lens = v["lens"]
        for nd, w0 in minw:
            nd.outputs[0].default_value = w0 * old_lens / v["lens"] * 960 / SIZE[0]
        prep = time.time() - t1
        log[v["id"]] = {"plants": int(keep.sum()), "left_out": int((~keep).sum()), "met_first": hits,
                        "camera_ground_m": round(gz, 2), "camera_on": gname, "prepare_s": round(prep, 1)}
        print("VIEW", v["id"], log[v["id"]])
        for light in lights:
            if light == "dawn":
                for nd in dots:
                    nd.inputs[1].default_value = sun
                for nd in hazes:
                    nd.inputs["B"].default_value = (*lin((222, 200, 186)), 1)
                s.world = dawn
            else:
                for nd in dots:
                    nd.inputs[1].default_value = SUN_DAY
                for nd in hazes:
                    nd.inputs["B"].default_value = (*HAZE_RGB, 1)
                s.world = day_world
            t2 = time.time()
            s.render.filepath = f"{out_dir}/{v['id']}_{light}.png"
            bpy.ops.render.render(write_still=True)
            log[v["id"]][f"render_{light}_s"] = round(time.time() - t2, 1)
            print("WROTE", s.render.filepath, log[v["id"]][f"render_{light}_s"])
        bpy.data.objects.remove(sob)
    tag = "_".join(ids) if ids else "all"
    json.dump(log, open(f"{out_dir}/render_log_{tag}_{'-'.join(lights)}.json", "w"), indent=1)


main()
