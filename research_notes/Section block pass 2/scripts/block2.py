"""Section block pass 2 inside Blender: the region as one block at heights x3 (from the first frame; towers and wires at
true size), on one day's pass; the 2D section's cut traced on it (the pond's north dike, the jog dashed, the line's
crossing), the rest of the block dropping away and fading so that only the two slices the section is cut through stay
(each 250 m deep behind its cut: what the section draws), then the camera square to the cuts (prototype B: the dike's
slice swung beside the crossing's, one camera; prototype A: each slice where it is, a camera each, split at the
section's break), the slices' tops fading to leave only the cut faces, drawn by cutlib.py as the section draws them.
Pixels of the pass only resampled; nothing generated. Not the film.
blender -b --factory-startup -P block2.py -- XF_DIR STATE SCENE_DIR PASSES_DIR PROTO LINE OUT_DIR [--res P] [--frames a:b:step]
[--samples N]   PROTO A | B; LINE 0 Dniprovska | 1 Ferosplavna. Writes OUT_DIR/f_NNNN_K.png (K the camera) and f_NNNN.json."""
import json, math, sys
from pathlib import Path

import bpy
import numpy as np
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Euler, Matrix, Vector

sys.path.insert(0, str(Path(__file__).parent))
import cutlib as C  # noqa: E402
import cuts as K  # noqa: E402

a = sys.argv[sys.argv.index("--") + 1:]
XF, STATE, SD, PS, PROTO, LINE, OUT = Path(a[0]), a[1], Path(a[2]), Path(a[3]), a[4], a[5], Path(a[6])
opt = lambda k, d: a[a.index(k) + 1] if k in a else d
RES, SAMPLES = int(opt("--res", 100)), int(opt("--samples", 32))
SHADOWS = "--no-shadows" not in a       # the sun's shadows: invisible at this scale, and costly on the land's mesh
FPS = 30
EX = 3.0
OUT.mkdir(parents=True, exist_ok=True)
s = bpy.context.scene
for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)
C.render_setup(s, SAMPLES)
s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage = 1920, 1080, RES
land = C.Land(XF, STATE, SD); ST = land.ST
LAY = K.layout(LINE)
coll = s.collection


def mesh(name, verts, faces, uvs=None, parent=None, mat=None, smooth=False):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    if uvs is not None:
        uv = me.uv_layers.new(name="uv")
        uv.data.foreach_set("uv", np.asarray(uvs, np.float32)[np.asarray(faces).ravel()].ravel())
    me.update()
    if smooth:
        me.shade_smooth()
    if mat:
        me.materials.append(mat)
    ob = bpy.data.objects.new(name, me); coll.objects.link(ob); ob.parent = parent
    return ob


def land_mat(name):
    img = bpy.data.images.get("pass") or bpy.data.images.load(str(PS / ST["pass"] / "rgb.webp"))
    img.name = "pass"
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    bs = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"); out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    im = nt.nodes.new("ShaderNodeTexImage"); im.image = img; im.extension = "EXTEND"
    uvn = nt.nodes.new("ShaderNodeUVMap"); uvn.uv_map = "uv"; nt.links.new(uvn.outputs[0], im.inputs["Vector"])
    dim = nt.nodes.new("ShaderNodeMixRGB"); dim.blend_type = "MULTIPLY"; dim.inputs[0].default_value = 1.0
    dim.inputs[2].default_value = (0.78, 0.78, 0.78, 1)
    nt.links.new(im.outputs["Color"], dim.inputs[1]); nt.links.new(dim.outputs[0], bs.inputs["Base Color"])
    bs.inputs["Roughness"].default_value = 1.0
    C.add_fade(m, bs.outputs[0], out)
    return m


MAT = {f"land_{k}": land_mat(f"land_{k}") for k in ("rest", "slice")}
for k in ("rest", "slice"):
    MAT[f"water_{k}"] = C.flat(f"water_{k}", C.lin((46, 74, 98)), fade=True)
    MAT[f"side_{k}"] = C.flat(f"side_{k}", C.lin((26, 26, 28)), fade=True)
MAT["trace"] = C.flat("trace", C.lin((255, 255, 255)), 1.0, fade=True)
MAT["jog"] = C.flat("jog", C.lin((255, 255, 255)), 1.0, fade=True)
LM_REST, LM_SLICE = C.line_mats(fade=True), C.line_mats()


def surface(x, y):
    """The block's top at points (x, y): heights, wet, levels and pond (xfilm.py's rules, the joined grid)."""
    z = land.at_all(x, y, land.z); pond = land.at_all(x, y, land.pond).astype(bool)
    wat = land.at_all(x, y, land.wat).astype(bool); roff = land.at_all(x, y, land.roff)
    river = np.full(z.shape, ST["river_egm"]) if ST["flat"] else ST["river_egm"] + roff
    wet = ((z < river) & (ST["flat"] | wat)) | (wat & ~pond & (z < river + 1.5))
    pwet = pond & (wat | ST["flat"]); wet = (wet & ~pond) | pwet
    zg = np.where(pond, np.where(pwet, land.pond_lv - 6.0, land.pond_lv + 0.25), z)
    lvl = np.where(pond, land.pond_lv, river)
    return zg, wet, lvl


def sheet(name, gx, gy, keepq, parent, k):
    """A piece of land on the points gx, gy (2D arrays): its surface textured by the pass, its water at the day's
    levels; quads where keepq (one per cell) is true."""
    zg, wet, lvl = surface(gx, gy)
    ny, nx = gx.shape
    I = np.arange(ny * nx).reshape(ny, nx)
    Fq = np.stack([I[:-1, :-1], I[:-1, 1:], I[1:, 1:], I[1:, :-1]], -1).reshape(-1, 4)
    kq = keepq.ravel()
    u, v = land.uv(gx, gy)
    used = np.unique(Fq[kq]); remap = -np.ones(ny * nx, int); remap[used] = np.arange(len(used))
    V = np.stack([gx.ravel(), gy.ravel(), (zg * EX).ravel()], 1)
    ob = mesh(name, V[used], remap[Fq[kq]], uvs=np.stack([u.ravel(), v.ravel()], 1)[used], parent=parent,
              mat=MAT[f"land_{k}"], smooth=True)
    wq = (wet[:-1, :-1] & wet[:-1, 1:] & wet[1:, 1:] & wet[1:, :-1]).ravel() & kq
    used = np.unique(Fq[wq]); remap = -np.ones(ny * nx, int); remap[used] = np.arange(len(used))
    W_ = np.stack([gx.ravel(), gy.ravel(), lvl.ravel() * EX + 0.5], 1)
    wo = mesh(name + " water", W_[used], remap[Fq[wq]], parent=parent, mat=MAT[f"water_{k}"])
    return zg


def skirt(name, pts, zg_edge, parent, k):
    """A dark wall from the land's edge (pts, its heights) down to the section's floor."""
    vs, fs = [], []
    for (p, zp), (q, zq) in zip(zip(pts[:-1], zg_edge[:-1]), zip(pts[1:], zg_edge[1:])):
        n0 = len(vs); vs += [(p[0], p[1], zp * EX), (q[0], q[1], zq * EX), (q[0], q[1], C.BASE * EX), (p[0], p[1], C.BASE * EX)]
        fs.append((n0, n0 + 1, n0 + 2, n0 + 3))
    return mesh(name, vs, fs, parent=parent, mat=MAT[f"side_{k}"])


# ---- the slices: S1 behind the dike's cut (x -3250 to -3000, y 600 to 4400), S2 behind the crossing's (250 m WNW of it)
D = K.DEPTH
s1 = bpy.data.objects.new("S1", None); coll.objects.link(s1)
s2 = bpy.data.objects.new("S2", None); coll.objects.link(s2)
rest = bpy.data.objects.new("rest", None); coll.objects.link(rest)
pieces = {"S1": ("dike", s1), "S2": (LINE, s2)}
for key, (piece, par) in pieces.items():
    P0, U, N, L, pad, S = K.geom(piece)
    ss = S                                       # the face's samples
    nn = np.arange(-D, 0.0 + 1e-6, 10.0)
    gs, gn = np.meshgrid(ss, nn)
    gx = P0[0] + gs * U[0] + gn * N[0]; gy = P0[1] + gs * U[1] + gn * N[1]
    zg = sheet(key, gx, gy, np.ones((len(nn) - 1, len(ss) - 1), bool), par, "slice")
    [skirt(f"{key} back", np.stack([gx[0], gy[0]], 1), zg[0], par, "slice"),
             skirt(f"{key} s0", np.stack([gx[:, 0], gy[:, 0]], 1), zg[:, 0], par, "slice"),
             skirt(f"{key} s1", np.stack([gx[:, -1], gy[:, -1]], 1), zg[:, -1], par, "slice")]

# ---- the rest of the block: the joined grid without the slices' cells, skirts round its outside
gx, gy = np.meshgrid(land.xs, land.ys)
cx, cy = (gx[:-1, :-1] + gx[1:, 1:]) / 2, (gy[:-1, :-1] + gy[1:, 1:]) / 2
inside = np.zeros(cx.shape, bool)
for key, (piece, par) in pieces.items():
    P0, U, N, L, pad, S = K.geom(piece)
    ps = (cx - P0[0]) * U[0] + (cy - P0[1]) * U[1]; pn = (cx - P0[0]) * N[0] + (cy - P0[1]) * N[1]
    inside |= (ps > S[0]) & (ps < S[-1]) & (pn > -D) & (pn < 0)
zr = sheet("rest", gx, gy, ~inside, rest, "rest")
for nm, sl in (("s", (0, slice(None))), ("n", (-1, slice(None))), ("w", (slice(None), 0)), ("e", (slice(None), -1))):
    skirt(f"rest {nm}", np.stack([gx[sl], gy[sl]], 1), zr[sl], rest, "rest")

# ---- the lines: the crossing's towers and wires near its cut stay with S2; every other tower and wire goes with the rest
inblock = lambda xy: land.xs[0] + 30 <= xy[0] <= land.xs[-1] - 30 and land.ys[0] + 30 <= xy[1] <= land.ys[-1] - 30
kt, kw = C.near_cut(LINE)
px0 = K.PX
wires = []
tw, cs, cv, _ = C.lines(land, int(LINE), EX, 1.0, px0, (kt, kw), LM_SLICE, parent=s2, name="slice")
wires += cv
for li in range(len(land.SC["lines"])):
    near = (kt, kw) if li == int(LINE) else (lambda xy: False, lambda xy: False)
    keep = (lambda xy, n=near: inblock(xy) and not n[0](xy), lambda xy, n=near: inblock(xy) and not n[1](xy))
    tw, cs, cv, _ = C.lines(land, li, EX, 1.0, px0, keep, LM_REST, parent=rest, name=f"rest{li}")
    wires += cv

# ---- light, camera
sun = bpy.data.lights.new("sun", "SUN"); sun.energy = 4.5; sun.angle = math.radians(2); sun.use_shadow = SHADOWS
so = bpy.data.objects.new("sun", sun); coll.objects.link(so); so.rotation_euler = Euler((math.radians(55), 0, math.radians(-40)))
cam = bpy.data.cameras.new("cam"); co = bpy.data.objects.new("cam", cam); coll.objects.link(co); s.camera = co
cam.type = "ORTHO"; cam.clip_end = 400000


def set_cam(c):
    az, el = math.radians(c["az"]), math.radians(c["el"])
    d = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
    cam.ortho_scale = c["w"]; co.location = Vector(c["L"]) + d * 120000
    co.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    return c["w"] / 1920


# ---- per frame: the things rebuilt (faces, trace) and the things moved
P0d, Ud = K.geom("dike")[0], K.geom("dike")[1]
d_, c_ = LAY["dike"], LAY[LINE]
th_end = math.atan2(c_["U"][1], c_["U"][0]) - math.atan2(Ud[1], Ud[0])
tgt = c_["P0"] + d_["sigma"] * c_["U"]          # where the dike's start lands in B
dyn = []


def s1_matrix(u):
    piv = Vector((P0d[0], P0d[1], 0)); to = Vector((P0d[0] + (tgt[0] - P0d[0]) * u, P0d[1] + (tgt[1] - P0d[1]) * u, 0))
    return Matrix.Translation(to) @ Matrix.Rotation(th_end * u, 4, "Z") @ Matrix.Translation(-piv)


def top_z(xy):
    zg, wet, lvl = surface(np.array([xy[0]]), np.array([xy[1]]))
    return float(max(zg[0], lvl[0] if wet[0] else -99)) * EX + 3.0


def trace_curve(name, pts, frac, px, parent, mat, dash=None):
    """The cut drawn on the land: the polyline pts up to frac of its length (dashed if dash = (on, off) metres)."""
    if frac <= 0:
        return
    P = np.asarray(pts, float); seg = np.linalg.norm(np.diff(P[:, :2], axis=0), axis=1); cum = np.concatenate([[0], np.cumsum(seg)])
    Ltot = cum[-1] * frac
    runs = [(0.0, Ltot)] if dash is None else [(a0, min(a0 + dash[0], Ltot)) for a0 in np.arange(0, Ltot, sum(dash))]
    cu = bpy.data.curves.new(name, "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = 1.1 * px; cu.bevel_resolution = 1
    for a0, a1 in runs:
        if a1 - a0 < 1:
            continue
        ss = np.concatenate([[a0], cum[(cum > a0) & (cum < a1)], [a1]])
        q = np.stack([np.interp(ss, cum, P[:, i]) for i in range(3)], 1)
        sp = cu.splines.new("POLY"); sp.points.add(len(q) - 1)
        sp.points.foreach_set("co", np.hstack([q, np.ones((len(q), 1))]).ravel().astype(np.float32))
    cu.materials.append(mat); ob = bpy.data.objects.new(name, cu); coll.objects.link(ob); ob.parent = parent
    dyn.append(ob)
    return ob


def path(piece, s0, s1_, step=40.0):
    P0, U = K.geom(piece)[:2]
    return [(*(P0 + q * U), top_z(P0 + q * U)) for q in np.append(np.arange(s0, s1_, step), s1_)]


C1 = path("dike", 0.0, 3790.0)
C2 = path(LINE, -500.0, c_["S1"])
a_, b_ = np.array(C1[-1][:2]), np.array(C2[0][:2])
JOG = [(*(a_ + (b_ - a_) * q), top_z(a_ + (b_ - a_) * q)) for q in np.linspace(0, 1, 120)]


def screen(p):
    q = world_to_camera_view(s, co, Vector(p)); return [q.x * 1920, (1 - q.y) * 1080]


END = (K.TA if PROTO == "A" else K.T)["end"]
frames = [K.block_state(PROTO, LINE, i / FPS) for i in range(int(round(END * FPS)) + 1)]
fr = opt("--frames", None)
idx = range(len(frames)) if fr is None else range(*[int(v) for v in fr.split(":")])
for i in idx:
    st = frames[i]
    for o in dyn:
        bpy.data.objects.remove(o, do_unlink=True)
    dyn.clear()
    for m in list(bpy.data.meshes) + list(bpy.data.curves):
        if m.users == 0 and m not in C._tmesh.values():
            (bpy.data.meshes if isinstance(m, bpy.types.Mesh) else bpy.data.curves).remove(m)
    rest.location.z = st["rest_dz"]
    for k in ("land_rest", "water_rest", "side_rest"):
        C.set_alpha(MAT[k], st["rest_a"])
    for m in LM_REST.values():
        C.set_alpha(m, st["rest_a"])
    for k in ("land_slice", "water_slice", "side_slice"):
        C.set_alpha(MAT[k], st["tops_a"])
    for o in rest.children_recursive:
        o.hide_render = st["rest_a"] <= 0.001
    s1.matrix_world = s1_matrix(st["s1_u"])
    C.set_alpha(MAT["trace"], st["trace_a"]); C.set_alpha(MAT["jog"], st["trace_a"] * st["jog_a"])
    info = {"t": st["t"], "cams": []}

    def extents():
        ext = {}
        for key, piece in (("S1", "dike"), ("S2", LINE)):
            P0, U, N, L, pad, S = K.geom(piece)
            M_ = s1.matrix_world if key == "S1" else Matrix.Identity(4)
            xs_ = [screen(M_ @ Vector((*(P0 + q * U), 30.0 * EX)))[0] for q in (S[0], S[-1])]
            ext[key] = [min(xs_), max(xs_)]
        return ext

    exts = []
    for c in st["cams"]:
        set_cam(c); bpy.context.view_layer.update(); exts.append(extents())   # the camera's matrix updated first
    seam = (exts[0]["S1"][1] + exts[1]["S2"][0]) / 2 if len(exts) == 2 else None   # A: between the two views
    info["seam_px"] = seam
    for ci, c in enumerate(st["cams"]):
        px = set_cam(c)
        for o in dyn:
            bpy.data.objects.remove(o, do_unlink=True)
        dyn.clear()
        if st["faces_a"] > 0:   # the cut faces, their lines a pixel wide at this frame's scale
            f1, _ = C.face(land, "dike", EX, px, "face S1", parent=s1); f2, _ = C.face(land, LINE, EX, px, "face S2", parent=s2)
            dyn.extend([f1, f2])
        trace_curve("c1", C1, st["c1"], px, s1, MAT["trace"])
        trace_curve("c2", C2, st["c2"], px, s2, MAT["trace"])
        if st["jog_a"] > 0 and len(st["cams"]) == 1:
            trace_curve("jog", JOG, st["jog"], px, None, MAT["jog"], dash=(110.0, 90.0))
        for ob, r in wires:
            ob.data.bevel_depth = r * px
        for key, par in (("S1", s1), ("S2", s2)):   # each camera sees its own slices (A: one each)
            hid = key not in c["show"]
            for o in par.children_recursive:
                o.hide_render = hid or (o.name.endswith((" back", " s0", " s1")) and st["faces_a"] <= 0)
        fading = 0.001 < st["rest_a"] < 0.999 or 0.001 < st["tops_a"] < 0.999   # dithered fades need more samples
        s.eevee.taa_render_samples = SAMPLES * 2 if fading else SAMPLES
        s.render.use_border = seam is not None     # A: each camera rendered only on its side of the seam (+ 20 px)
        s.render.use_crop_to_border = False
        if seam is not None:
            sp_ = seam / 1920
            s.render.border_min_y, s.render.border_max_y = 0.0, 1.0
            s.render.border_min_x, s.render.border_max_x = (0.0, min(1.0, sp_ + 0.01)) if ci == 0 else (max(0.0, sp_ - 0.01), 1.0)
        s.render.filepath = str(OUT / f"f_{i:04d}_{ci}.png")
        bpy.ops.render.render(write_still=True)
        info["cams"].append({**{k: c[k] for k in ("az", "el", "w")}, "L": list(c["L"]), "show": c["show"], "ext": exts[ci]})
    json.dump(info, open(OUT / f"f_{i:04d}.json", "w"))
print("block2: frames", idx)
