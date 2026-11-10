"""Section block pass 2: what the 2D section (profile3.py) and the 3D block (block2.py) share, so the block's cut faces
and the section's drawing are made by one piece of code and meet exactly at the hand-over.

A cut is a straight line on the scene's plane (metres east and north of the plant): the cooling pond's north dike
(x = -3000, y 600 to 4400, seen from the east) or a line's crossing (Dniprovska towers 21 to 27, Ferosplavna 18 to 26,
500 m on at each end, seen from the east-south-east). Its face is drawn as profile2.py drew it (S1, 4 November 2026):
the ground dark with a white line (dotted where the drained bed's height is inferred), water blue at the day's level,
the pond's water fading out below its level (its depth not published). Its towers (within 250 m of the cut) and wires
in elevation, every wire bare steel (each day a complete loss of off-site power). Two exaggerations: ex_g for the
ground and water, ex_t for the towers and sag (ex_t = 1: true size, as the block draws them; ex_t = ex_g: the
plan-and-profile convention of the S1 sections). Runs inside Blender (bpy); numpy only otherwise.
"""
import json
from pathlib import Path

import bpy
import numpy as np

BALTIC = 0.4            # EGM2008 = Baltic + 0.4 m here (bed.json)
BASE = -4.0             # the section's floor, true metres
NEAR = 250.0            # towers and wires drawn within this of the cut (profile2.py)
from cuts import CUTS, geom  # noqa: E402  (the cuts, shared with the composer)


def lin(c):
    c = np.asarray(c, float) / 255
    return tuple(np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4))


GROUND, WATER, INK, DARK = lin((52, 52, 54)), lin((70, 108, 140)), lin((235, 235, 235)), lin((10, 14, 18))
STEEL = {750: lin((150, 154, 160)), 330: lin((110, 113, 118))}


def flat(name, rgb, strength=1.0, attr=False, fade=False):
    """An emission material (the section's flat drawing); `fade` adds a mix with transparency driven by the
    node named 'alpha' (its default_value), for the block's fades."""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new("ShaderNodeOutputMaterial"); e = nt.nodes.new("ShaderNodeEmission")
    if attr:
        at = nt.nodes.new("ShaderNodeAttribute"); at.attribute_name = "col"; nt.links.new(at.outputs["Color"], e.inputs["Color"])
    else:
        e.inputs["Color"].default_value = (*rgb, 1)
    e.inputs["Strength"].default_value = strength
    if fade:
        add_fade(m, e.outputs[0], o)
    else:
        nt.links.new(e.outputs[0], o.inputs["Surface"])
    return m


def add_fade(m, shader_out, out_node):
    nt = m.node_tree
    tr = nt.nodes.new("ShaderNodeBsdfTransparent"); mx = nt.nodes.new("ShaderNodeMixShader")
    v = nt.nodes.new("ShaderNodeValue"); v.name = "alpha"; v.outputs[0].default_value = 1.0
    nt.links.new(v.outputs[0], mx.inputs[0]); nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(shader_out, mx.inputs[2])
    nt.links.new(mx.outputs[0], out_node.inputs["Surface"])
    if hasattr(m, "surface_render_method"):
        m.surface_render_method = "DITHERED"


def set_alpha(m, a):
    m.node_tree.nodes["alpha"].outputs[0].default_value = float(a)


class Land:
    """The day's land: the W and E blocks of S1 (prep3f.py: FABDEM heights, the drained bed inferred, the pass's own
    pixels and water) joined at x = -3000 (the same column in both)."""

    def __init__(self, xf, state, sd):
        xf, sd = Path(xf), Path(sd)
        self.ST = {"flat": False, **json.loads((xf / "states.json").read_text())[state]}
        W, E = np.load(xf / f"W_{state}.npz"), np.load(xf / f"E_{state}.npz")
        cat = lambda k: np.concatenate([W[k][:, :-1], E[k]], 1)
        self.xs = np.concatenate([W["x"][:-1], E["x"]]); self.ys = E["y"]
        self.z = cat("z").astype(np.float64); self.u, self.v = cat("u"), cat("v")
        self.pond, self.inf, self.wat, self.roff = cat("pond"), cat("inferred"), cat("water"), cat("river_off")
        self.E = {k: E[k] for k in E.files}   # the 2D section samples E alone (profile2.py); loaded once (an npz
        self.E["z64"] = self.E["z"].astype(np.float64)   # decompresses a key on every access)
        ex_, ey_ = self.xs, self.ys   # u, v are linear in x, y (lon/lat linear in metres on the plane)
        self.du = (self.u[0, -1] - self.u[0, 0]) / (ex_[-1] - ex_[0]); self.dv = (self.v[-1, 0] - self.v[0, 0]) / (ey_[-1] - ey_[0])
        self.U0, self.V0 = self.u[0, 0] - self.du * ex_[0], self.v[0, 0] - self.dv * ey_[0]
        self.SC = json.loads((sd / "scene.json").read_text()); self.T = np.load(sd / "towers.npz")
        self.pond_lv = self.ST["pond_baltic"] + BALTIC

    def uv(self, x, y):
        return self.U0 + self.du * np.asarray(x), self.V0 + self.dv * np.asarray(y)

    def at(self, x, y, arr):
        """profile2.py's sampling (the grid node at or after the point), on E's grid."""
        xs, ys = self.E["x"], self.E["y"]
        i = int(np.clip(np.searchsorted(xs, x), 0, len(xs) - 1)); j = int(np.clip(np.searchsorted(ys, y), 0, len(ys) - 1))
        return arr[j, i]

    def at_all(self, x, y, arr):
        """The same rule on the joined grid (the block's slices, x below -3000 too)."""
        i = np.clip(np.searchsorted(self.xs, x), 0, len(self.xs) - 1); j = np.clip(np.searchsorted(self.ys, y), 0, len(self.ys) - 1)
        return arr[j, i]


def profile(land, piece):
    """The cut's samples as profile2.py takes them: ground, inferred, water, level, pond, along S."""
    P0, U, N, L, pad, S = geom(piece)
    E = land.E; ST = land.ST
    XY = P0 + S[:, None] * U
    g = np.array([land.at(x, y, E["z64"]) for x, y in XY])
    fi = np.array([land.at(x, y, E["inferred"]) for x, y in XY])
    w = np.array([land.at(x, y, E["water"]) for x, y in XY]); ro = np.array([land.at(x, y, E["river_off"]) for x, y in XY])
    pd = np.array([land.at(x, y, E["pond"]) for x, y in XY]).astype(bool)
    if ST["flat"]:
        lv = np.full(len(S), ST["river_egm"]); wet = g < lv
    else:
        lv = ST["river_egm"] + ro; wet = w & (g < lv + 1.5)
    lv = np.where(pd, land.pond_lv, lv); wet = wet | pd
    return dict(P0=P0, U=U, N=N, L=L, pad=pad, S=S, g=g, fi=fi, lv=lv, wet=wet, pd=pd)


_cut_mat = {}


def face(land, piece, ex_g, px, name="face", parent=None, fade=False):
    """The cut face as a mesh in world coordinates (profile2.py's, with ex_g); its line widths a pixel at `px`."""
    p = profile(land, piece); P0, U, N, S, g, fi, lv, wet, pd = (p[k] for k in ("P0", "U", "N", "S", "g", "fi", "lv", "wet", "pd"))
    pond_lv = land.pond_lv

    def P(si, h, off=0.0):
        xy = P0 + si * U + off * N
        return (xy[0], xy[1], h * ex_g)

    verts, faces, cols = [], [], []

    def quad(s0, s1, a0, b0, a1, b1, off, c0, c1):
        k = len(verts); verts.extend([P(s0, a0, off), P(s0, b0, off), P(s1, a1, off), P(s1, b1, off)])
        cols.extend([c0, c1, c0, c1]); faces.append((k, k + 1, k + 3, k + 2))

    hw = 0.9 * px / ex_g
    for j in range(len(S) - 1):
        s0, s1 = S[j], S[j + 1]
        if pd[j] and pd[j + 1]:
            quad(s0, s1, pond_lv - 5, pond_lv, pond_lv - 5, pond_lv, 1, DARK, WATER)
            quad(s0, s1, pond_lv - hw, pond_lv + hw, pond_lv - hw, pond_lv + hw, 2, INK, INK)
            continue
        quad(s0, s1, BASE, g[j], BASE, g[j + 1], 0, GROUND, GROUND)
        if not fi[j] or (j // 3) % 2 == 0:
            quad(s0, s1, g[j] - hw, g[j] + hw, g[j + 1] - hw, g[j + 1] + hw, 2, INK, INK)
        if wet[j] and wet[j + 1] and lv[j] > g[j]:
            quad(s0, s1, g[j], lv[j], g[j + 1], lv[j + 1], 1, WATER, WATER)
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces)
    att = me.color_attributes.new("col", "FLOAT_COLOR", "CORNER")
    cc = np.asarray(cols, np.float32)[np.asarray(faces).ravel()]
    att.data.foreach_set("color", np.hstack([cc, np.ones((len(cc), 1), np.float32)]).ravel())
    key = ("cut", fade)
    if key not in _cut_mat:
        _cut_mat[key] = flat("cut" + ("_f" if fade else ""), None, attr=True, fade=fade)
    me.materials.append(_cut_mat[key])
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob); ob.parent = parent
    return ob, p


_tmesh = {}


def tmesh(T, ty, mat):
    key = (ty, mat.name)
    if key not in _tmesh:
        v, loops, counts = T[f"{ty}__v"], T[f"{ty}__loops"], T[f"{ty}__counts"]
        m2 = bpy.data.meshes.new(ty); m2.vertices.add(len(v)); m2.vertices.foreach_set("co", v.ravel())
        m2.loops.add(len(loops)); m2.loops.foreach_set("vertex_index", loops); m2.polygons.add(len(counts))
        m2.polygons.foreach_set("loop_start", np.concatenate([[0], np.cumsum(counts)[:-1]]).astype(np.int32))
        m2.polygons.foreach_set("loop_total", counts); m2.update(calc_edges=True); m2.validate(); m2.materials.append(mat)
        _tmesh[key] = m2
    return _tmesh[key]


def foot(land, t):
    """A tower's foot (true metres): its caisson's top, else the ground under it (profile2.py: E's grid)."""
    x, y = t["xy"]
    return t["base_m"] if t["caisson"] else float(land.at_all(x, y, land.z))


def lines(land, li, ex_g, ex_t, px, keep, mats, parent=None, name="l"):
    """One line's towers (where keep[0](xy) is true) and its wires (bundles and earth wires, the points where keep[1]
    is true) at ex_g / ex_t; returns (towers, caissons, wire curves, the crossing towers' tops for a label)."""
    SC, T = land.SC, land.T; ln = SC["lines"][li]
    tw = [t for t in ln["towers"] if t["type"]]
    al = np.concatenate([[0.0], np.cumsum([np.linalg.norm(np.subtract(b["xy"], a["xy"])) for a, b in zip(tw, tw[1:])])])
    feet = np.array([foot(land, t) for t in tw]); base = np.array([t["base_m"] for t in tw])
    towers, caissons, tops = [], [], []
    sc = bpy.context.scene.collection
    for t, fa in zip(tw, feet):
        if not keep[0](np.array(t["xy"])):
            continue
        x, y = t["xy"]
        ob = bpy.data.objects.new(t["type"], tmesh(T, t["type"], mats["tower"])); ob.location = (x, y, fa * ex_g)
        ob.rotation_euler = (0, 0, t["rot_z"]); ob.scale = (1, 1, ex_t); sc.objects.link(ob); ob.parent = parent; towers.append(ob)
        if t["caisson"]:
            cb = bpy.data.objects.new(t["caisson"], tmesh(T, t["caisson"], mats["caisson"])); cb.location = (x, y, (fa - 3.0) * ex_g)
            cb.scale = (1, 1, ex_g); sc.objects.link(cb); cb.parent = parent; caissons.append(cb)
        if t["type"].startswith("crossing"):
            tops.append((x, y, fa * ex_g + (100 if t["type"] != "crossing750_p" else 126) * ex_t))
    n = T["wire_n"]; st = np.concatenate([[0], np.cumsum(n)[:-1]]); kinds = SC["towers"]["wire_kinds"]
    polys, earth = [], []
    for k in range(len(n)):
        if T["wire_line"][k] != li or kinds[T["wire_kind"][k]] not in ("bundle", "earth"):
            continue
        p = T["wire_pts"][st[k]:st[k] + n[k]].astype(float).copy(); a = T["wire_along"][st[k]:st[k] + n[k]]
        p[:, 2] = (p[:, 2] - np.interp(a, al, base)) * ex_t + np.interp(a, al, feet) * ex_g
        kp = np.array([keep[1](q) for q in p[:, :2]])
        runs = np.split(np.arange(len(p)), np.where(np.diff(kp.astype(int)) != 0)[0] + 1)
        (earth if kinds[T["wire_kind"][k]] == "earth" else polys).extend(p[r] for r in runs if kp[r[0]] and len(r) > 1)
    curves = []
    for nm, ps, r, mat in ((f"{name} earth", earth, 0.35, mats["earth"]), (f"{name} wire", polys, 0.5, mats[f"steel{ln['kv']}"])):
        cu = bpy.data.curves.new(nm, "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = r * px; cu.bevel_resolution = 1
        for q in ps:
            sp = cu.splines.new("POLY"); sp.points.add(len(q) - 1)
            sp.points.foreach_set("co", np.hstack([q, np.ones((len(q), 1))]).ravel().astype(np.float32))
        cu.materials.append(mat); ob = bpy.data.objects.new(nm, cu); sc.objects.link(ob); ob.parent = parent
        curves.append((ob, r))
    return towers, caissons, curves, tops


def line_mats(fade=False):
    return {"tower": flat("tower", lin((205, 205, 205)), fade=fade), "caisson": flat("caisson", lin((150, 148, 140)), fade=fade),
            "earth": flat("earth", lin((90, 92, 96)), fade=fade), "steel750": flat("steel750", STEEL[750], fade=fade),
            "steel330": flat("steel330", STEEL[330], fade=fade)}


def near_cut(piece):
    """(keep a tower, keep a wire's point) for a cut: within NEAR of it and inside its length (profile2.py's tests)."""
    P0, U, N, L, pad, S = geom(piece)

    def keep_t(xy):
        si = float(np.dot(xy - P0, U)); return (-pad + 20 < si < L + pad - 20) and abs(float(np.dot(xy - P0, N))) <= NEAR

    def keep_w(xy):
        si = float(np.dot(xy - P0, U)); return (-pad < si < L + pad) and abs(float(np.dot(xy - P0, N))) < NEAR
    return keep_t, keep_w


def render_setup(s, samples=32):
    try:
        s.render.engine = "BLENDER_EEVEE"
    except TypeError:
        pass
    if hasattr(s, "eevee"):
        s.eevee.taa_render_samples = samples
    try:
        s.view_settings.view_transform = "Standard"
    except TypeError:
        pass
    s.world = bpy.data.worlds.new("w"); s.world.use_nodes = True
    bg = next(n_ for n_ in s.world.node_tree.nodes if n_.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0, 0, 0, 1); bg.inputs["Strength"].default_value = 0.0
