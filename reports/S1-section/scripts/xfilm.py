"""S1 film test inside Blender: the region as one block, its heights grown from true size to x25, then split along the
pond's cut (3 km west of the plant) and the plant's side slid 2.5 km east so the cut face shows, drawn as a section.
Every line cut on each of the three days drawn (complete losses of off-site power): the bare wire, no line lit.
Towers and sag at true size standing on the exaggerated ground; the caissons to the ground's scale. Not the film.
blender -b --factory-startup -P xfilm.py -- XF_DIR STATE MODE OUT SCENE_DIR PASSES_DIR
STATE: A | B | C (states.json);  MODE: still (open, x25: OUT a png, labels beside it) | open (OUT a folder: the
opening's unique frames from XF_DIR/opening.json, each {ex, dx, cut})"""
import json, math, sys
from pathlib import Path

import bpy
import numpy as np
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Euler, Vector

a = sys.argv[sys.argv.index("--") + 1:]
XF, STATE, MODE, OUT, SD, PS = Path(a[0]), a[1], a[2], Path(a[3]), Path(a[4]), Path(a[5])
ST = {"flat": False, **json.loads((XF / "states.json").read_text())[STATE]}
EX = 25.0           # the heights as built; the opening scales them down to true size and back (object scale)
GAP = 2500.0
BALTIC = 0.4
pond_lv = ST["pond_baltic"] + BALTIC
s = bpy.context.scene
for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)
TEX = str(PS / ST["pass"] / "rgb.webp")


def lin(c):
    c = np.asarray(c, float) / 255
    return tuple(np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4))


def mesh(name, verts, faces, cols=None, uvs=None, parent=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    if cols is not None:
        at = me.color_attributes.new("col", "FLOAT_COLOR", "CORNER")
        cc = np.asarray(cols, np.float32)[np.asarray(faces).ravel()]
        at.data.foreach_set("color", np.hstack([cc, np.ones((len(cc), 1), np.float32)]).ravel())
    if uvs is not None:
        uv = me.uv_layers.new(name="uv")
        uv.data.foreach_set("uv", np.asarray(uvs, np.float32)[np.asarray(faces).ravel()].ravel())
    me.update()
    ob = bpy.data.objects.new(name, me); s.collection.objects.link(ob); ob.parent = parent
    return ob


def emission(name, rgb, strength=1.0, attr=False):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new("ShaderNodeOutputMaterial"); e = nt.nodes.new("ShaderNodeEmission")
    if attr:
        at = nt.nodes.new("ShaderNodeAttribute"); at.attribute_name = "col"; nt.links.new(at.outputs["Color"], e.inputs["Color"])
    else:
        e.inputs["Color"].default_value = (*rgb, 1)
    e.inputs["Strength"].default_value = strength
    nt.links.new(e.outputs[0], o.inputs["Surface"])
    return m


img = bpy.data.images.load(TEX)
LAND = bpy.data.materials.new("land"); LAND.use_nodes = True; nt = LAND.node_tree
bs = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
im = nt.nodes.new("ShaderNodeTexImage"); im.image = img; im.extension = "EXTEND"
uvn = nt.nodes.new("ShaderNodeUVMap"); uvn.uv_map = "uv"; nt.links.new(uvn.outputs[0], im.inputs["Vector"])
dim = nt.nodes.new("ShaderNodeMixRGB"); dim.blend_type = "MULTIPLY"; dim.inputs[0].default_value = 1.0
dim.inputs[2].default_value = (0.78, 0.78, 0.78, 1)
nt.links.new(im.outputs["Color"], dim.inputs[1]); nt.links.new(dim.outputs[0], bs.inputs["Base Color"])
bs.inputs["Roughness"].default_value = 1.0
WATER_M = emission("water", lin((46, 74, 98)))
SIDE_M = emission("sides", lin((26, 26, 28)))
CUT_M = emission("cut", None, attr=True)
GROUND = lin((58, 58, 60)); WATER = lin((70, 108, 140)); INK = lin((235, 235, 235)); DARK = lin((14, 22, 30)); DIM = lin((150, 150, 150))
scaled, cuts = [], []   # what the opening scales in z; the cut faces (hidden while the block is whole)


def block(path, side, parent, face=True):
    """One block: the land on the pass's pixels, its water at the day's levels, its cut face on `side` (e | w) drawn
    as a section, plain skirts on the other three sides. Heights x EX (scaled back by the opening)."""
    B = np.load(path)
    xs, ys, z = B["x"], B["y"], B["z"].astype(np.float64)
    pond, inf, wat, roff = B["pond"], B["inferred"], B["water"], B["river_off"]
    river = np.full(z.shape, ST["river_egm"]) if ST["flat"] else ST["river_egm"] + roff
    wet = ((z < river) & (ST["flat"] | wat)) | (wat & ~pond & (z < river + 1.5))
    pwet = pond & (wat | ST["flat"])                 # the pond's water as the pass saw it: its shoals dry
    wet = (wet & ~pond) | pwet
    zg = np.where(pond, np.where(pwet, pond_lv - 6.0, pond_lv + 0.25), z)   # under the pond's water: never seen;
    ny, nx = z.shape                                                         # its shoals just above it (inferred)
    gx, gy = np.meshgrid(xs, ys)
    I = np.arange(ny * nx).reshape(ny, nx)
    Fq = np.stack([I[:-1, :-1], I[:-1, 1:], I[1:, 1:], I[1:, :-1]], -1).reshape(-1, 4)
    land = mesh("land", np.stack([gx.ravel(), gy.ravel(), (zg * EX).ravel()], 1), Fq,
                uvs=np.stack([B["u"].ravel(), B["v"].ravel()], 1), parent=parent)
    land.data.shade_smooth(); land.data.materials.append(LAND); scaled.append(land)
    lvl = np.where(pond, pond_lv, river)
    wq = wet[:-1, :-1] & wet[:-1, 1:] & wet[1:, 1:] & wet[1:, :-1]
    used = np.unique(Fq[wq.ravel()])
    remap = -np.ones(ny * nx, int); remap[used] = np.arange(len(used))
    w = mesh("water", np.stack([gx.ravel()[used], gy.ravel()[used], lvl.ravel()[used] * EX + 0.5], 1),
             remap[Fq[wq.ravel()]], parent=parent)
    w.data.materials.append(WATER_M); scaled.append(w)
    c = -1 if side == "e" else 0
    gz, pd, wc, fi = z[:, c], pond[:, c], wet[:, c], inf[:, c]
    pdw = pwet[:, c]; wl = np.where(pd, pond_lv, river[:, c])
    X = xs[c] + (1.0 if side == "e" else -1.0); sg = 1.0 if side == "e" else -1.0
    verts, faces, cols = [], [], []

    def quad(t0, t1, h00, h01, h10, h11, off, c0, c1):
        k = len(verts); xo = X + sg * off
        verts.extend([(xo, t0, h00), (xo, t0, h01), (xo, t1, h10), (xo, t1, h11)])
        cols.extend([c0, c1, c0, c1]); faces.append((k, k + 1, k + 3, k + 2))

    def band(t0, t1, h, half, off, col):
        quad(t0, t1, h - half, h + half, h - half, h + half, off, col, col)

    for j in range(ny - 1):
        t0, t1 = ys[j], ys[j + 1]
        if not (pd[j] and pd[j + 1]):
            g0, g1 = gz[j] * EX, gz[j + 1] * EX
            quad(t0, t1, -6.0 * EX, g0, -6.0 * EX, g1, 0, GROUND, GROUND)
            if (not fi[j]) or (j // 2) % 2 == 0:
                quad(t0, t1, g0 - 18, g0 + 6, g1 - 18, g1 + 6, 0.5, INK, INK)
            if wc[j] and wc[j + 1] and wl[j] > gz[j]:
                quad(t0, t1, g0, wl[j] * EX, g1, wl[j + 1] * EX, 0.3, WATER, WATER)
        else:   # the pond: water from its level down, fading out where its depth isn't published
            top = pond_lv * EX
            quad(t0, t1, -6.0 * EX, top, -6.0 * EX, top, 0, DARK, WATER)
            band(t0, t1, top, 4, 0.5, INK)
            for past in ST["past"]:   # where the pond stood before, by its dated reports
                band(t0, t1, (past + BALTIC) * EX, 2.5, 0.6, DIM)
            if (j // 2) % 2 == 0:     # 12 m: below it the cooling water pumps can't run (IAEA, via Babel)
                band(t0, t1, (12.0 + BALTIC) * EX, 2.5, 0.7, INK)
    if face:   # the plant's side faces away from the camera: its cut is never seen, so not drawn
        cut = mesh("cut", verts, faces, cols=cols, parent=parent); cut.data.materials.append(CUT_M)
        scaled.append(cut); cuts.append(cut)
    sk_v, sk_f = [], []
    edges = {"s": [(xs[i], ys[0], zg[0, i]) for i in range(nx)], "n": [(xs[i], ys[-1], zg[-1, i]) for i in range(nx)],
             "w": [(xs[0], ys[j], zg[j, 0]) for j in range(ny)], "e": [(xs[-1], ys[j], zg[j, -1]) for j in range(ny)]}
    for k, pts in edges.items():
        if k == side:
            continue
        for p, q in zip(pts[:-1], pts[1:]):
            n0 = len(sk_v); sk_v += [(p[0], p[1], p[2] * EX), (q[0], q[1], q[2] * EX), (q[0], q[1], -6.0 * EX), (p[0], p[1], -6.0 * EX)]
            sk_f.append((n0, n0 + 1, n0 + 2, n0 + 3))
    sk = mesh("sides", sk_v, sk_f, parent=parent); sk.data.materials.append(SIDE_M); scaled.append(sk)
    return xs, ys, zg


west = bpy.data.objects.new("west", None); s.collection.objects.link(west)
east = bpy.data.objects.new("east", None); s.collection.objects.link(east)
WX = block(XF / f"W_{STATE}.npz", "e", west)
xs, ys, zg = block(XF / f"E_{STATE}.npz", "w", east, face=False)
nx, ny = len(xs), len(ys)


def ground_at(x, y):
    i = int(np.clip(np.searchsorted(xs, x), 0, nx - 1)); j = int(np.clip(np.searchsorted(ys, y), 0, ny - 1))
    return zg[j, i]


def inside(x, y, pad=0.0):
    return xs[0] + pad <= x <= xs[-1] - pad and ys[0] + pad <= y <= ys[-1] - pad


# ---- the lines on the plant's side: the film's towers and wires, every wire the bare steel (all cut that day)
SC = json.loads((SD / "scene.json").read_text()); T = np.load(SD / "towers.npz")
tmats = []
for k in range(len(SC["towers"]["materials"])):
    name, rgb = SC["towers"]["materials"][str(k)]
    mm = bpy.data.materials.new(name); mm.use_nodes = True
    b = next(n for n in mm.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    rgb = [min(1.0, c * 1.6) for c in rgb]
    b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = 0.7
    b.inputs["Emission Color"].default_value = (*rgb, 1); b.inputs["Emission Strength"].default_value = 0.35
    tmats.append(mm)
cache = {}


def tmesh(ty):
    if ty not in cache:
        v, loops, counts, mat = T[f"{ty}__v"], T[f"{ty}__loops"], T[f"{ty}__counts"], T[f"{ty}__mat"]
        me = bpy.data.meshes.new(ty); me.vertices.add(len(v)); me.vertices.foreach_set("co", v.ravel())
        me.loops.add(len(loops)); me.loops.foreach_set("vertex_index", loops); me.polygons.add(len(counts))
        me.polygons.foreach_set("loop_start", np.concatenate([[0], np.cumsum(counts)[:-1]]).astype(np.int32))
        me.polygons.foreach_set("loop_total", counts); me.update(calc_edges=True); me.validate()
        for q in tmats:
            me.materials.append(q)
        me.polygons.foreach_set("material_index", mat.astype(np.int32))
        cache[ty] = me
    return cache[ty]


towers, caissons, splines, wires = [], [], [], []   # (object, its foot's height per unit of exaggeration)
M_PX = 30000 / 1920
STEEL = {750: lin((150, 154, 160)), 330: lin((136, 140, 146))}
for li, ln in enumerate(SC["lines"]):
    tw = [t for t in ln["towers"] if t["type"]]
    at = np.concatenate([[0.0], np.cumsum([np.linalg.norm(np.subtract(b["xy"], a["xy"])) for a, b in zip(tw, tw[1:])])])
    foot = []   # each tower's foot: true height per unit of exaggeration (the ground, or its caisson's top)
    for t in tw:
        x, y = t["xy"]
        fa = t["base_m"] if t["caisson"] else ground_at(x, y)
        foot.append(fa)
        if not inside(x, y, 30):
            continue
        ob = bpy.data.objects.new(t["type"], tmesh(t["type"])); ob.rotation_euler = (0, 0, t["rot_z"])
        ob.location = (x, y, fa * EX); ob.parent = east; s.collection.objects.link(ob); towers.append((ob, fa))
        if t["caisson"]:
            cb = bpy.data.objects.new(t["caisson"], tmesh(t["caisson"])); cb.location = (x, y, (fa - 3.0) * EX)
            cb.scale = (1, 1, EX); cb.parent = east; s.collection.objects.link(cb); caissons.append((cb, fa))
    foot = np.array(foot); base = np.array([t["base_m"] for t in tw])
    cu = bpy.data.curves.new(f"wire {li}", "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = 0.45 * M_PX; cu.bevel_resolution = 1
    n = T["wire_n"]; st = np.concatenate([[0], np.cumsum(n)[:-1]])
    for k in range(len(n)):
        if T["wire_line"][k] != li or SC["towers"]["wire_kinds"][T["wire_kind"][k]] != "bundle":
            continue
        p = T["wire_pts"][st[k]:st[k] + n[k]].astype(float); al = T["wire_along"][st[k]:st[k] + n[k]]
        keep = (p[:, 0] >= xs[0]) & (p[:, 0] <= xs[-1]) & (p[:, 1] >= ys[0]) & (p[:, 1] <= ys[-1])
        for r in np.split(np.arange(len(p)), np.where(np.diff(keep.astype(int)) != 0)[0] + 1):
            if not keep[r[0]] or len(r) < 2:
                continue
            q = p[r]; fa = np.interp(al[r], at, foot); fb = np.interp(al[r], at, base)
            sp = cu.splines.new("POLY"); sp.points.add(len(q) - 1)
            splines.append((sp, q[:, 0], q[:, 1], q[:, 2] - fb, fa))   # z(ex) = z_true - its foot + its foot's height x ex
    cu.materials.append(emission("steel", STEEL[ln["kv"]], 0.8))
    wires.append(cu)
    ob = bpy.data.objects.new(f"wire {li}", cu); ob.parent = east; s.collection.objects.link(ob)


OPEN_VIEW = (22000.0, (300.0, 4000.0, 300.0))   # the open block's frame: the pond's cut, the plant, the crossing


def pose(ex, dx, cut, ortho=30000.0, look=(-300.0, 5200.0, 300.0)):
    """The scene at an exaggeration and an opening: the land's heights x ex, the towers on it at true size; the
    camera's frame (north up the block's long side, never turned: only its width and centre change)."""
    cam.ortho_scale = ortho; co.location = Vector(look) + d * 80000
    for cu in wires:
        cu.bevel_depth = 0.45 * ortho / 1920
    for o in scaled:
        o.scale = (1, 1, ex / EX)
    for o, fa in towers:
        o.location.z = fa * ex
    for o, fa in caissons:
        o.location.z = (fa - 3.0) * ex; o.scale = (1, 1, ex)
    for sp, x, y, z0, fa in splines:
        sp.points.foreach_set("co", np.stack([x, y, z0 + fa * ex, np.ones_like(x)], 1).ravel().astype(np.float32))
    east.location.x = dx
    for o in cuts:
        o.hide_render = not cut


sun = bpy.data.lights.new("sun", "SUN"); sun.energy = 4.5; sun.angle = math.radians(2)
so = bpy.data.objects.new("sun", sun); s.collection.objects.link(so); so.rotation_euler = Euler((math.radians(55), 0, math.radians(-40)))
s.world = bpy.data.worlds.new("w"); s.world.use_nodes = True
bg = next(n_ for n_ in s.world.node_tree.nodes if n_.type == "BACKGROUND"); bg.inputs["Color"].default_value = (0, 0, 0, 1)
bg.inputs["Strength"].default_value = 0.0
cam = bpy.data.cameras.new("cam"); co = bpy.data.objects.new("cam", cam); s.collection.objects.link(co); s.camera = co
cam.clip_end = 300000; cam.type = "ORTHO"; cam.ortho_scale = 30000
d = Vector((1.0, -0.62, 0.95)).normalized(); co.location = Vector((-300, 5200, 300)) + d * 80000
co.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
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


def onscreen(p):
    q = world_to_camera_view(s, co, Vector(p)); return [q.x * 1920, (1 - q.y) * 1080]


if MODE == "still":
    pose(EX, GAP, True, *([float(a[6]), tuple(map(float, a[7].split(",")))] if len(a) > 7 else OPEN_VIEW))
    s.render.filepath = str(OUT); bpy.ops.render.render(write_still=True)
    X0 = WX[0][-1]
    river0 = ST["river_egm"]
    lab = {"ENERHODAR BANK": onscreen((X0, -2300, 30 * EX)),
           "COOLING POND": onscreen((X0, 0, (pond_lv + 1.5) * EX)),
           "DIKE": onscreen((X0, 2150, 22 * EX)),
           ("RESERVOIR" if ST["flat"] else "DRAINED BED"): onscreen((X0, 6500, 14 * EX)),
           "NIKOPOL BANK": onscreen((X0, 12700, 22 * EX)),
           "ZAPORIZHZHIA NPP": onscreen((GAP, -300, ground_at(0, -300) * EX + 60)),
           "_12m": onscreen((X0, 300, (12.0 + BALTIC) * EX))}
    for li, nm in enumerate(("DNIPROVSKA · 750 KV: CUT", "FEROSPLAVNA-1 · 330 KV: CUT")):
        tw = [t for t in SC["lines"][li]["towers"] if t["type"] and t["caisson"]]
        t = tw[len(tw) // 2]
        lab[nm] = onscreen((t["xy"][0] + GAP, t["xy"][1], t["base_m"] * EX + 140))
    json.dump(lab, open(OUT.with_suffix(".json"), "w"))
else:
    OUT.mkdir(parents=True, exist_ok=True)
    for i, f in enumerate(json.loads((XF / "opening.json").read_text())):
        pose(f["ex"], f["dx"], f["cut"], f["ortho"], tuple(f["look"]))
        s.render.filepath = str(OUT / f"u_{i:04d}.png"); bpy.ops.render.render(write_still=True)
