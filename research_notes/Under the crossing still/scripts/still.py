"""A prototype still for `under-the-crossing` (the user, 5 November 2026: option 1, on the bed under the wire, with
"accurate looking trees dwarfed by the powerline towers"). Runs inside Blender on the flight south's scene file, at
one of its frames (the record's state there: 11 September 2026, Ferosplavna-1 connected, Dniprovska cut; the 2025
pass on the land), never saving it:

    blender -b --factory-startup <ZNPP-last-two-lines-3D-south.blend> -P still.py -- <trees.npz> <out_dir> [dawn|day ...]

Adds, for this still only: a camera 1.3 m over the bed under the Ferosplavna-1 span, looking up toward tower 22;
white willows and black poplars, modelled (representative shapes: stems, branches, leaf sprays), at the heights the
sources give for 2026 and where the 2025 pass shows vegetation (place_trees.py); a little grass round the camera; and,
for `dawn`, a drawn sky (a gradient and the low sun's glow), the haze and the fixed sun turned to a mid-May sunrise.
Everything is shaded the scene's way (unlit colour, by a fixed sun), so the trees sit with the towers. The towers,
wires and land are the scene's own.
"""

import math
import sys

import bpy
import numpy as np

FRAME = 4001
LENS, PITCH, EYE_M = 20.0, 18.0, 1.6
SIZE = (1920, 1080)
HAZE_RGB = (0.62, 0.66, 0.70)
SUN_DAY = (0.35, -0.61, 0.71)
DAWN_AZ, DAWN_EL = 57.0, 6.0          # mid-May sunrise at 47.5 N: azimuth about 57°, just up
PROTO_H = 6.5


def lin(c):
    return tuple(((v / 255 + 0.055) / 1.055) ** 2.4 if v / 255 > 0.04045 else v / 255 / 12.92 for v in c)


# ---------- the trees: representative white willow (multi-stemmed, upright, fine grey-green sprays) and black
# poplar (one stem, taller, a broader darker crown), each at PROTO_H, scaled per tree to its height

def basis(d):
    d = d / np.linalg.norm(d)
    a = np.array([1.0, 0, 0]) if abs(d[0]) < 0.9 else np.array([0, 1.0, 0])
    u = np.cross(d, a)
    u /= np.linalg.norm(u)
    return u, np.cross(d, u)


class Mesh:
    def __init__(self):
        self.v, self.f, self.m, self.t = [], [], [], []

    def cyl(self, p0, p1, r0, r1, sides):
        u, w = basis(np.asarray(p1) - np.asarray(p0))
        k = len(self.v)
        for p, r in ((p0, r0), (p1, r1)):
            for s in range(sides):
                a = 2 * math.pi * s / sides
                self.v.append(np.asarray(p) + r * (math.cos(a) * u + math.sin(a) * w))
        for s in range(sides):
            a, b = s, (s + 1) % sides
            self.f.append((k + a, k + b, k + sides + b, k + sides + a))
            self.m.append(0)
            self.t.append(0.0)

    def leaf(self, c, along, L, W, tint):
        u = along / np.linalg.norm(along)
        side, _ = basis(u)
        k = len(self.v)
        c = np.asarray(c)
        self.v += [c - u * L / 2, c - side * W / 2, c + u * L / 2, c + side * W / 2]   # a diamond: a narrow leaf spray
        self.f.append((k, k + 1, k + 2, k + 3))
        self.m.append(1)
        self.t.append(tint)


def stem_path(rng, base, lean, h, bend, n=6):
    pts = [np.asarray(base, float)]
    d = np.array([math.sin(lean[0]) * math.cos(lean[1]), math.sin(lean[0]) * math.sin(lean[1]), math.cos(lean[0])])
    for i in range(n):
        d = d + rng.normal(0, bend, 3) * np.array([1, 1, 0.2])
        d /= np.linalg.norm(d)
        pts.append(pts[-1] + d * h / n)
    return pts


def tree(kind, seed, lod):
    rng = np.random.default_rng(seed)
    m = Mesh()
    near = lod <= 1
    LEAF = {0: (0.15, 0.035, 0.13, 0.07), 1: (0.34, 0.09, 0.30, 0.16)}   # willow length, width; poplar length, width
    stems = [1] if kind == 1 else [1] * int(rng.integers(2, 6))
    tint0 = rng.uniform(0, 0.25)
    for si, _ in enumerate(stems):
        h = PROTO_H * (rng.uniform(0.72, 1.0) if kind == 0 else rng.uniform(0.95, 1.08))
        lean = (rng.uniform(0.03, 0.16) if kind == 0 else rng.uniform(0.0, 0.05), rng.uniform(0, 2 * math.pi))
        base = rng.normal(0, 0.35, 2).tolist() + [0.0] if kind == 0 else [0.0, 0.0, 0.0]
        path = stem_path(rng, base, lean, h, 0.06 if kind == 0 else 0.03)
        r0 = (0.07 if kind == 0 else 0.13) * rng.uniform(0.8, 1.2)
        for i in range(len(path) - 1):
            a, b = 1 - i / (len(path) - 1), 1 - (i + 1) / (len(path) - 1)
            m.cyl(path[i], path[i + 1], r0 * (0.25 + 0.75 * a), r0 * (0.25 + 0.75 * b), {0: 7, 1: 5, 2: 3}[lod])
        # branches up the stem: willow steep and fine, poplar wider in the upper crown
        nb = int(rng.integers(9, 15)) if kind == 0 else int(rng.integers(14, 20))
        for _ in range(nb):
            f = rng.uniform(0.32, 0.92) if kind == 0 else rng.uniform(0.38, 0.95)
            j = min(int(f * (len(path) - 1)), len(path) - 2)
            p = path[j] + (path[j + 1] - path[j]) * (f * (len(path) - 1) - j)
            az = rng.uniform(0, 2 * math.pi)
            el = math.radians(rng.uniform(52, 72) if kind == 0 else rng.uniform(35, 58))
            d = np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])
            L = h * (0.24 if kind == 0 else 0.30) * (1.05 - 0.55 * f) * rng.uniform(0.7, 1.2)
            q = p + d * L
            if near:
                m.cyl(p, q, r0 * 0.28, r0 * 0.08, 4)
            nl = {0: 230 if kind == 0 else 170, 1: 70 if kind == 0 else 60, 2: 8}[lod]
            for _ in range(nl):
                t = rng.uniform(0.25, 1.05)
                c = p + (q - p) * t + rng.normal(0, 0.32 if kind == 0 else 0.42, 3) * np.array([1, 1, 0.8])
                along = d * 0.4 + rng.normal(0, 1, 3) + np.array([0, 0, -0.6 if kind == 0 else 0.0])   # willow droops a little
                if near:
                    lw = LEAF[lod]
                    m.leaf(c, along, lw[0] if kind == 0 else lw[2], lw[1] if kind == 0 else lw[3], tint0 + rng.uniform(0, 0.6))
                else:
                    m.leaf(c, along, 1.1, 0.5 if kind == 0 else 0.7, tint0 + rng.uniform(0, 0.6))
        # the stem's top: a spray of its own
        top = path[-1]
        for _ in range({0: 200, 1: 60, 2: 8}[lod]):
            c = top + rng.normal(0, 0.4, 3) * np.array([1, 1, 1.2]) - np.array([0, 0, 0.4])
            along = rng.normal(0, 1, 3)
            if near:
                lw = LEAF[lod]
                m.leaf(c, along, lw[0] if kind == 0 else lw[2], lw[1] if kind == 0 else lw[3], tint0 + rng.uniform(0, 0.6))
            else:
                m.leaf(c, along, 1.1, 0.5, tint0 + rng.uniform(0, 0.6))
    return m


def grass(seed):
    rng = np.random.default_rng(seed)
    m = Mesh()
    for _ in range(26):
        b = np.array([rng.normal(0, 0.18), rng.normal(0, 0.18), 0.0])
        h = rng.uniform(0.35, 1.0)
        tip = b + np.array([rng.normal(0, 0.15), rng.normal(0, 0.15), h])
        k = len(m.v)
        side, _ = basis(tip - b)
        m.v += [b - side * 0.012, b + side * 0.012, tip]
        m.f.append((k, k + 1, k + 2))
        m.m.append(2)
        m.t.append(rng.uniform(0, 1))
    return m


def to_object(name, mesh, mats):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in mesh.v], [], mesh.f)
    for mt in mats:
        me.materials.append(mt)
    me.polygons.foreach_set("material_index", mesh.m)
    at = me.attributes.new("tint", "FLOAT", "FACE")
    at.data.foreach_set("value", mesh.t)
    me.update()
    return bpy.data.objects.new(name, me)


# ---------- materials the scene's way: an unlit colour, shaded by the fixed sun, into the haze by distance

def material(name, kind, haze):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    N = nt.nodes
    attr = N.new("ShaderNodeAttribute")
    attr.attribute_name = "tint"
    oi = N.new("ShaderNodeObjectInfo")
    mixc = N.new("ShaderNodeMix")
    mixc.data_type = "RGBA"
    a, b = {"bark": ((96, 90, 80), (128, 120, 108)), "leaf": ((70, 92, 52), (142, 154, 120)),
            "grass": ((96, 104, 62), (150, 146, 96))}[kind]
    mixc.inputs["A"].default_value = (*lin(a), 1)
    mixc.inputs["B"].default_value = (*lin(b), 1)
    add = N.new("ShaderNodeMath")       # the leaf's own tint, and the tree's (its random) a little
    add.operation = "MULTIPLY_ADD"
    add.inputs[2].default_value = 0.0
    nt.links.new(attr.outputs["Fac"], add.inputs[0])
    add.inputs[1].default_value = 0.85
    add2 = N.new("ShaderNodeMath")
    add2.operation = "MULTIPLY_ADD"
    nt.links.new(oi.outputs["Random"], add2.inputs[0])
    add2.inputs[1].default_value = 0.25
    nt.links.new(add.outputs[0], add2.inputs[2])
    nt.links.new(add2.outputs[0], mixc.inputs["Factor"])
    geo = N.new("ShaderNodeNewGeometry")
    dot = N.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    dot.inputs[1].default_value = SUN_DAY
    dot.label = "tree sun"
    nt.links.new(geo.outputs["Normal"], dot.inputs[0])
    sh = N.new("ShaderNodeMath")
    if kind == "bark":           # as the towers: 0.35 facing away, 1.0 facing the sun
        sh.operation = "MULTIPLY_ADD"
        sh.inputs[1].default_value, sh.inputs[2].default_value = 0.325, 0.675
        nt.links.new(dot.outputs["Value"], sh.inputs[0])
    else:                        # thin leaves pass light: either face lit by how square it is to the sun
        ab = N.new("ShaderNodeMath")
        ab.operation = "ABSOLUTE"
        nt.links.new(dot.outputs["Value"], ab.inputs[0])
        sh.operation = "MULTIPLY_ADD"
        sh.inputs[1].default_value, sh.inputs[2].default_value = 0.5, 0.5
        nt.links.new(ab.outputs[0], sh.inputs[0])
    sc = N.new("ShaderNodeVectorMath")
    sc.operation = "SCALE"
    nt.links.new(mixc.outputs["Result"], sc.inputs[0])
    nt.links.new(sh.outputs[0], sc.inputs["Scale"])
    cam = N.new("ShaderNodeCameraData")
    rng_ = N.new("ShaderNodeMapRange")
    rng_.interpolation_type = "SMOOTHSTEP"
    rng_.inputs["From Min"].default_value, rng_.inputs["From Max"].default_value = haze
    nt.links.new(cam.outputs["View Distance"], rng_.inputs["Value"])
    hz = N.new("ShaderNodeMix")
    hz.data_type = "RGBA"
    hz.inputs["B"].default_value = (*HAZE_RGB, 1)
    nt.links.new(rng_.outputs["Result"], hz.inputs["Factor"])
    nt.links.new(sc.outputs["Vector"], hz.inputs["A"])
    em = N.new("ShaderNodeEmission")
    nt.links.new(hz.outputs["Result"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return mat


def scatter(pts, protos, name):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(p) for p in pts[:, :3]], [], [])
    for key, col, typ in (("idx", None, "INT"), ("rot", 4, "FLOAT"), ("scl", None, "FLOAT")):
        a = me.attributes.new(key, typ, "POINT")
        if key == "idx":
            a.data.foreach_set("value", pts[:, 8].astype(int).tolist())
        elif key == "rot":
            a.data.foreach_set("value", pts[:, 4].tolist())
        else:
            a.data.foreach_set("value", pts[:, 9].tolist())
    ob = bpy.data.objects.new(name, me)
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
    w = bpy.context.scene.world
    nt = w.node_tree
    for nd in list(nt.nodes):
        if nd.type != "OUTPUT_WORLD":
            nt.nodes.remove(nd)
    out = next(nd for nd in nt.nodes if nd.type == "OUTPUT_WORLD")
    N = nt.nodes
    tc = N.new("ShaderNodeTexCoord")
    nrm = N.new("ShaderNodeVectorMath")
    nrm.operation = "NORMALIZE"
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
    d = N.new("ShaderNodeVectorMath")       # the low sun's glow, round its direction
    d.operation = "DOT_PRODUCT"
    d.inputs[1].default_value = sun
    nt.links.new(nrm.outputs[0], d.inputs[0])
    pw = N.new("ShaderNodeMath")
    pw.operation = "POWER"
    nt.links.new(d.outputs["Value"], pw.inputs[0])
    pw.inputs[1].default_value = 10.0
    cl = N.new("ShaderNodeClamp")
    nt.links.new(pw.outputs[0], cl.inputs["Value"])
    mix = N.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["B"].default_value = (*lin((255, 214, 160)), 1)
    nt.links.new(cl.outputs[0], mix.inputs["Factor"])
    nt.links.new(ramp.outputs["Color"], mix.inputs["A"])
    bg = N.new("ShaderNodeBackground")
    nt.links.new(mix.outputs["Result"], bg.inputs["Color"])
    nt.links.new(bg.outputs[0], out.inputs["Surface"])


def main():
    a = sys.argv[sys.argv.index("--") + 1:]
    trees_npz, out_dir, variants = a[0], a[1], (a[2:] or ["day", "dawn"])
    s = bpy.context.scene
    s.frame_set(FRAME)
    T = np.load(trees_npz)
    pts, cam_xyz, heading = T["pts"], T["cam"], float(T["heading"])

    # the camera: off the flight's keys, onto the bed
    co = s.camera
    old_lens = co.data.lens
    co.animation_data_clear()
    co.data.animation_data_clear()
    co.location = (cam_xyz[0], cam_xyz[1], cam_xyz[2] + EYE_M)
    co.rotation_mode = "XYZ"
    co.rotation_euler = (math.radians(90 + PITCH), 0.0, -math.radians(heading))
    co.data.lens = LENS
    co.data.clip_start = 0.1
    # the wires' least width, keyed for the flight's lens at 960 px: held at this frame's value, for this lens and size
    for ng in bpy.data.node_groups:
        ks = [nd for nd in ng.nodes if nd.label == "min width"]
        if ks:
            v = ks[0].outputs[0].default_value
            ng.animation_data_clear()
            ks[0].outputs[0].default_value = v * old_lens / LENS * 960 / SIZE[0]
    haze = next(((nd.inputs["From Min"].default_value, nd.inputs["From Max"].default_value)
                 for m in bpy.data.materials if m.node_tree for nd in m.node_tree.nodes if nd.label == "haze"),
                (7000.0, 16000.0))

    mats = [material("bark", "bark", haze), material("leaf", "leaf", haze), material("grass", "grass", haze)]
    protos = bpy.data.collections.new("tree prototypes")
    k = 0
    for lod in (0, 1, 2):
        for kind in (0, 1):
            for var in range(4):
                ob = to_object(f"t{k:02d}", tree(kind, 100 * kind + var, lod), mats)
                protos.objects.link(ob)
                k += 1
    gp = bpy.data.collections.new("grass prototypes")
    for g in range(4):
        gp.objects.link(to_object(f"g{g}", grass(g), mats))
    idx = pts[:, 6] * 8 + pts[:, 3] * 4 + pts[:, 7]
    P = np.column_stack([pts[:, :8], idx, pts[:, 5] / PROTO_H])
    scatter(P, protos, "trees")
    rng = np.random.default_rng(5)          # grass round the camera, in the clearing
    r = np.sqrt(rng.uniform(1.0, 22.0 ** 2, 2600))
    t = rng.uniform(0, 2 * math.pi, 2600)
    G = np.zeros((2600, 10))
    G[:, 0], G[:, 1] = cam_xyz[0] + r * np.sin(t), cam_xyz[1] + r * np.cos(t)
    G[:, 2] = cam_xyz[2]
    G[:, 4] = rng.uniform(0, 2 * math.pi, 2600)
    G[:, 8] = rng.integers(0, 4, 2600)
    G[:, 9] = rng.uniform(0.7, 1.3, 2600)
    scatter(G, gp, "grass")
    # the grass stands on the terrain under the camera; the bed there is near level (20 m grid), said in the README

    s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage = *SIZE, 100
    s.eevee.taa_render_samples = 32
    s.render.image_settings.file_format = "PNG"
    s.frame_start = s.frame_end = FRAME
    dots = [nd for m in bpy.data.materials if m.node_tree for nd in m.node_tree.nodes
            if nd.type == "VECT_MATH" and nd.operation == "DOT_PRODUCT"
            and tuple(round(x, 2) for x in nd.inputs[1].default_value) == SUN_DAY]
    hazes = [nd for m in bpy.data.materials if m.node_tree for nd in m.node_tree.nodes
             if nd.type == "MIX" and nd.data_type == "RGBA"
             and tuple(round(x, 2) for x in nd.inputs["B"].default_value[:3]) == HAZE_RGB]
    for v in variants:
        if v == "dawn":
            az, el = math.radians(DAWN_AZ), math.radians(DAWN_EL)
            sun = (math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el))
            for nd in dots:
                nd.inputs[1].default_value = sun
            for nd in hazes:
                nd.inputs["B"].default_value = (*lin((222, 200, 186)), 1)
            dawn_world(sun)
        s.render.filepath = f"{out_dir}/still_{v}.png"
        bpy.ops.render.render(write_still=True)
        print("WROTE", s.render.filepath, len(dots), len(hazes))


main()
