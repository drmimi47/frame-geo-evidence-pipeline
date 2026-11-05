"""S1 offset section, one piece: a vertical section at one vertical scale for everything (EX: ground, water,
towers, sag), either along a line's crossing (its towers and wires in elevation, every wire bare steel: each day a
complete loss of off-site power) or through the cooling pond's north dike (x = -3000, south to north, no lines).
Both pieces at one width a pixel and one camera height, so the composite (xoffset.py) lines their levels up. Not the film.
blender -b --factory-startup -P profile2.py -- E_k.npz STATE EX OUT_PNG LABELS_JSON SCENE_DIR PIECE XF_DIR
   [ORTHO S_CENTRE Z_CENTRE]   (the frame: its width in m, the point along the piece and the true height in its middle)
STATE: A | B | C (states.json);  PIECE: 0 Dniprovska, 1 Ferosplavna, dike"""
import json, math, sys
from pathlib import Path

import bpy
import numpy as np
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

a = sys.argv[sys.argv.index("--") + 1:]
B = np.load(a[0]); STATE, EX, OUT, LAB, SD = a[1], float(a[2]), a[3], a[4], Path(a[5])
DIKE = a[6] == "dike"; LINE = -1 if DIKE else int(a[6])
ST = {"flat": False, **json.loads((Path(a[7]) / "states.json").read_text())[STATE]}
xs, ys, Z = B["x"], B["y"], B["z"].astype(np.float64)
BALTIC = 0.4
SC = json.loads((SD / "scene.json").read_text()); T = np.load(SD / "towers.npz")
s = bpy.context.scene
for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)


def lin(c):
    c = np.asarray(c, float) / 255
    return tuple(np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4))


def flat(name, rgb, strength=1.0, alpha=1.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new("ShaderNodeOutputMaterial"); e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*rgb, 1); e.inputs["Strength"].default_value = strength
    if alpha < 1:
        tr = nt.nodes.new("ShaderNodeBsdfTransparent"); mx = nt.nodes.new("ShaderNodeMixShader"); mx.inputs[0].default_value = alpha
        nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(e.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], o.inputs["Surface"])
        if hasattr(m, "surface_render_method"):
            m.surface_render_method = "BLENDED"
    else:
        nt.links.new(e.outputs[0], o.inputs["Surface"])
    return m


def at(x, y, arr):
    i = int(np.clip(np.searchsorted(xs, x), 0, len(xs) - 1)); j = int(np.clip(np.searchsorted(ys, y), 0, len(ys) - 1))
    return arr[j, i]


# the axis: Dniprovska's crossing, from its last tower on the Enerhodar bank to its first on the Nikopol bank's top
dn = [t for t in SC["lines"][0]["towers"] if t["type"]]
P0, P1 = [(np.array([3632.0, 3233.0]), np.array([5386.0, 9027.0])),    # Dniprovska: towers 21 to 27
          (np.array([3298.0, 3332.0]), np.array([5073.0, 9199.0])),    # Ferosplavna: 18 to 26
          (np.array([-3000.0, 600.0]), np.array([-3000.0, 4400.0]))][LINE]  # the pond's north part, its dike, the bed
U = (P1 - P0) / np.linalg.norm(P1 - P0); N = np.array([U[1], -U[0]])   # N: toward the camera (east-south-east)
L = float(np.linalg.norm(P1 - P0)); PAD = 0.0 if DIKE else 500.0
S = np.arange(-PAD, L + PAD, 10.0)
XY = P0 + S[:, None] * U
g = np.array([at(x, y, Z) for x, y in XY]); fi = np.array([at(x, y, B["inferred"]) for x, y in XY])
w = np.array([at(x, y, B["water"]) for x, y in XY]); ro = np.array([at(x, y, B["river_off"]) for x, y in XY])
pd = np.array([at(x, y, B["pond"]) for x, y in XY]).astype(bool)
pond_lv = ST["pond_baltic"] + BALTIC
if ST["flat"]:
    lv = np.full(len(S), ST["river_egm"]); wet = g < lv
else:
    lv = ST["river_egm"] + ro; wet = w & (g < lv + 1.5)
lv = np.where(pd, pond_lv, lv); wet = wet | pd
BASE = -4.0


def P(si, h, off=0.0):   # a point on the cut plane (si metres along, h metres up, true), lifted toward the camera by off
    xy = P0 + si * U + off * N
    return (xy[0], xy[1], h * EX)


verts, faces, cols = [], [], []
GROUND = lin((52, 52, 54)); WATER = lin((70, 108, 140)); INK = lin((235, 235, 235)); DIM = lin((120, 120, 120))


def quad(s0, s1, a0, b0, a1, b1, off, c0, c1):
    k = len(verts); verts.extend([P(s0, a0, off), P(s0, b0, off), P(s1, a1, off), P(s1, b1, off)])
    cols.extend([c0, c1, c0, c1]); faces.append((k, k + 1, k + 3, k + 2))


ORTHO = float(a[8]) if len(a) > 8 else (6130.0 + 1000.0) * 1.04   # every piece at one width a pixel
px = ORTHO / 1920
hw = 0.9 * px / EX   # half a line's height, as true metres
DARK = lin((10, 14, 18))
for j in range(len(S) - 1):
    s0, s1 = S[j], S[j + 1]
    if pd[j] and pd[j + 1]:   # the pond: its depth not published, so its water fades out below the level
        quad(s0, s1, pond_lv - 5, pond_lv, pond_lv - 5, pond_lv, 1, DARK, WATER)
        quad(s0, s1, pond_lv - hw, pond_lv + hw, pond_lv - hw, pond_lv + hw, 2, INK, INK)
        continue
    quad(s0, s1, BASE, g[j], BASE, g[j + 1], 0, GROUND, GROUND)
    if not fi[j] or (j // 3) % 2 == 0:   # the ground's line, dotted where the bed's height is inferred
        quad(s0, s1, g[j] - hw, g[j] + hw, g[j + 1] - hw, g[j + 1] + hw, 2, INK, INK)
    if wet[j] and wet[j + 1] and lv[j] > g[j]:
        quad(s0, s1, g[j], lv[j], g[j + 1], lv[j + 1], 1, WATER, WATER)
me = bpy.data.meshes.new("cut"); me.from_pydata(verts, [], faces)
att = me.color_attributes.new("col", "FLOAT_COLOR", "CORNER")
cc = np.asarray(cols, np.float32)[np.asarray(faces).ravel()]
att.data.foreach_set("color", np.hstack([cc, np.ones((len(cc), 1), np.float32)]).ravel())
cut = bpy.data.objects.new("cut", me); s.collection.objects.link(cut)
cm = bpy.data.materials.new("cut"); cm.use_nodes = True; nt = cm.node_tree; nt.nodes.clear()
o_ = nt.nodes.new("ShaderNodeOutputMaterial"); e_ = nt.nodes.new("ShaderNodeEmission"); at_ = nt.nodes.new("ShaderNodeAttribute")
at_.attribute_name = "col"; nt.links.new(at_.outputs["Color"], e_.inputs["Color"]); nt.links.new(e_.outputs[0], o_.inputs["Surface"])
me.materials.append(cm)

# towers: drawn flat, as an elevation (Dniprovska on the cut, light; Ferosplavna beyond it, dimmer)
cache = {}


def tmesh(ty, mat):
    key = (ty, mat.name)
    if key not in cache:
        v, loops, counts = T[f"{ty}__v"], T[f"{ty}__loops"], T[f"{ty}__counts"]
        m2 = bpy.data.meshes.new(ty); m2.vertices.add(len(v)); m2.vertices.foreach_set("co", v.ravel())
        m2.loops.add(len(loops)); m2.loops.foreach_set("vertex_index", loops); m2.polygons.add(len(counts))
        m2.polygons.foreach_set("loop_start", np.concatenate([[0], np.cumsum(counts)[:-1]]).astype(np.int32))
        m2.polygons.foreach_set("loop_total", counts); m2.update(calc_edges=True); m2.validate(); m2.materials.append(mat)
        cache[key] = m2
    return cache[key]


TMAT = [flat("tower", lin((205, 205, 205)))] * 2
CMAT = [flat("caisson", lin((150, 148, 140)))] * 2
lifts, tops = {}, {}
for li, ln in enumerate(SC["lines"]):
    if li != LINE:
        continue
    tw = [t for t in ln["towers"] if t["type"]]
    al = np.concatenate([[0.0], np.cumsum([np.linalg.norm(np.subtract(b["xy"], a["xy"])) for a, b in zip(tw, tw[1:])])])
    lift = []
    for t in tw:
        x, y = t["xy"]; si = float(np.dot(np.subtract(t["xy"], P0), U))
        zb = t["base_m"] if t["caisson"] else at(x, y, Z)
        lift.append(zb - t["base_m"])
        if not (-PAD + 20 < si < L + PAD - 20) or abs(np.dot(np.subtract(t["xy"], P0), N)) > 250:
            continue
        ob = bpy.data.objects.new(t["type"], tmesh(t["type"], TMAT[li])); ob.location = (x, y, zb * EX)
        ob.rotation_euler = (0, 0, t["rot_z"]); ob.scale = (1, 1, EX); s.collection.objects.link(ob)
        if t["caisson"]:
            cb = bpy.data.objects.new(t["caisson"], tmesh(t["caisson"], CMAT[li])); cb.location = (x, y, (zb - 3.0) * EX)
            cb.scale = (1, 1, EX); s.collection.objects.link(cb)
        if t["type"].startswith("crossing"):
            tops.setdefault(li, []).append((x, y, (zb + (100 if t["type"] != "crossing750_p" else 126)) * EX))
    lifts[li] = (al, np.array(lift))

n = T["wire_n"]; st = np.concatenate([[0], np.cumsum(n)[:-1]]); kinds = SC["towers"]["wire_kinds"]
WIRE_RGB = {750: (1.0, 0.86, 0.12), 330: (1.0, 0.5, 0.04)}
STEEL = {750: lin((150, 154, 160)), 330: lin((110, 113, 118))}


def curve(name, polys, r, mat):
    cu = bpy.data.curves.new(name, "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = r; cu.bevel_resolution = 1
    for p in polys:
        sp = cu.splines.new("POLY"); sp.points.add(len(p) - 1)
        sp.points.foreach_set("co", np.hstack([p, np.ones((len(p), 1))]).ravel().astype(np.float32))
    ob = bpy.data.objects.new(name, cu); s.collection.objects.link(ob); cu.materials.append(mat)


for li, ln in enumerate(SC["lines"]):
    if li != LINE:
        continue
    kv = ln["kv"]; al, lift = lifts[li]; polys = []; earth = []
    for k in range(len(n)):
        if T["wire_line"][k] != li or kinds[T["wire_kind"][k]] not in ("bundle", "earth"):
            continue
        p = T["wire_pts"][st[k]:st[k] + n[k]].astype(float).copy()
        p[:, 2] = (p[:, 2] + np.interp(T["wire_along"][st[k]:st[k] + n[k]], al, lift)) * EX
        si = (p[:, :2] - P0) @ U
        keep = (si > -PAD) & (si < L + PAD) & (np.abs((p[:, :2] - P0) @ N) < 250)
        runs = np.split(np.arange(len(p)), np.where(np.diff(keep.astype(int)) != 0)[0] + 1)
        (earth if kinds[T["wire_kind"][k]] == "earth" else polys).extend(p[r] for r in runs if keep[r[0]] and len(r) > 1)
    curve(f"earth {li}", earth, 0.35 * px, flat("earth", lin((90, 92, 96))))   # the earth wires carry no power: never lit
    curve(f"wire {li}", polys, 0.5 * px, flat("steel", STEEL[kv]))   # every line cut on each of the days

s.world = bpy.data.worlds.new("w"); s.world.use_nodes = True
bg = next(n_ for n_ in s.world.node_tree.nodes if n_.type == "BACKGROUND"); bg.inputs["Color"].default_value = (0, 0, 0, 1)
cam = bpy.data.cameras.new("cam"); co = bpy.data.objects.new("cam", cam); s.collection.objects.link(co); s.camera = co
cam.type = "ORTHO"; cam.ortho_scale = ORTHO; cam.clip_end = 50000
mid = P0 + U * (float(a[9]) if len(a) > 9 else L / 2)
zc = float(a[10]) * EX if len(a) > 10 else 160 * EX * 0.42
d = Vector((N[0], N[1], 0.0))
co.location = Vector((mid[0], mid[1], zc)) + d * 8000
co.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
cam.shift_y = 0.0
s.render.resolution_x, s.render.resolution_y = 1920, 1080
try:
    s.render.engine = "BLENDER_EEVEE"
except TypeError:
    pass
if hasattr(s, "eevee"):
    s.eevee.taa_render_samples = 32
try:
    s.view_settings.view_transform = "Standard"
except TypeError:
    pass
s.render.filepath = OUT
bpy.ops.render.render(write_still=True)


def onscreen(p):
    q = world_to_camera_view(s, co, Vector(p)); return [q.x * 1920, (1 - q.y) * 1080]


lab = {}
if DIKE:
    sp = S[pd]; lab["COOLING POND"] = onscreen(P(float(sp.mean()), pond_lv + 1.5))
    ok = (S > 1300) & (S < 1900); jd = int(np.argmax(np.where(ok, g, -99)))
    lab["DIKE"] = onscreen(P(S[jd], g[jd] + 1))
    nb = (S > 2000) & wet & ~pd
    if nb.any():
        jr = int(np.argmin(np.where(nb, g, 99))); lab["RESERVOIR" if ST["flat"] else "CHANNEL"] = onscreen(P(S[jr], lv[jr] + 1))
    if not ST["flat"]:
        lab["DRAINED BED"] = onscreen(P(2600, at(*(P0 + 2600 * U), Z) + 1))
    lab["_pond"] = [onscreen(P(float(sp.min()), 0))[0], onscreen(P(float(sp.max()), 0))[0]]
else:
    lab["ENERHODAR BANK"] = onscreen(P(-300, at(*(P0 - 300 * U), Z) + 2))
    lab["NIKOPOL BANK"] = onscreen(P(L + 250, at(*(P0 + (L + 250) * U), Z) + 2))
    jr = int(np.argmin(np.where(wet, g, 99)))
    lab["RESERVOIR" if ST["flat"] else "RIVER"] = onscreen(P(S[jr], max(lv[jr], g[jr]) + 1))
    for li, nm in enumerate(("DNIPROVSKA · 750 KV: CUT", "FEROSPLAVNA 1, 2 · 330 KV: CUT")):
        if li in tops:
            x, y, zt = tops[li][len(tops[li]) // 2]
            lab[nm] = onscreen((x, y, zt + 6 * EX))
lab["_x"] = [onscreen(P(float(S[0]), 0))[0], onscreen(P(float(S[-1]), 0))[0]]
lab["_y"] = {str(h): onscreen(P(0, h))[1] for h in (0, 10, 20)}   # the shared height scale (EGM2008 m)
lab["_px"] = px; lab["_ex"] = EX; lab["_ends"] = [list(map(float, P0)), list(map(float, P1))]
json.dump(lab, open(LAB, "w"))
