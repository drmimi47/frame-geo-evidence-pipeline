"""The v8 shot `drowning` (the user, 8 November 2026: "another pass where the plants and stuff die off as the water rises
so at the end of the animation it will only show the tower and the powerlines in the background"; the eye stays put
and ends under the water). v7's water is drawn in numpy (composite_v8.py) from passes; here those passes are rendered
PER FRAME with the plants dying (dieoff_v8.py: colour, leaf and twig loss, slump, fall, sinking into the bed), so what
a dying plant uncovers (the plants behind it, the bed, the tower, the wires) is the scene's own.

Runs inside Blender on the flight south's scene file at frame 4001, NEVER saving it (still_v5.py / still_v4.py /
still_v3.py exec'd without their mains, unchanged; v3's plants, v5's camera f by day):

    blender -b --factory-startup <south.blend> -P still_v8.py -- <views_v5.json> <plants_f.npz> <out_dir> <mode> [args]

Modes:
  prep           the plants laid on the ground as v3/v5/v6 lay them: P (x, y, z, rot, scale, proto index) and their
                 family, height, level of detail and variant, to <out_dir>/plants_laid.npz (the die-off's input)
  frames LIST    per frame K of the shot (LIST: K,K,... or A:B, frames already on disk skipped):
                   static_K.exr  the picture without the moving parts (v6's static: 2x, or 1x past `--one-x-from`),
                                 EEVEE 32 samples, film-transparent
                   pos_K.exr     every surface's world height (R) and distance (G), 2x, 1 sample, filter off, 32-bit
                   matte_K.exr   the moving wires drawn white and everything else black (1x, 32 samples): how much of
                                 the lit wires the (dying) plants leave in view
                 with the plants as dieoff_v8.state(K) has them. `--one-x-from F`: static at 1x from frame F on.

Every plant keeps v3's model, rotation, size, variant and object name ("plants f" seeds each plant's random
brightness), so with nothing dying a frame is v6's static picture. The models get two face attributes (built here,
the models' geometry and colours untouched): `lr`, one random number per leaf, blade, card or stem, and `ord`, a stem's
drop order (thinnest first; stems from the ground never drop). Each plant (instance) carries `dead` (colour: green to
yellow-brown to grey-brown), `leaf` (share of leaves gone), `twig` (share of the finer stems gone) and `fade` (all of it
gone, at the end, as it settles into the silt), read by the plant material as instancer attributes.
"""
import json
import math
import os
import sys
import time

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
V5_DIR = os.path.abspath(os.path.join(HERE, "..", "..", "scripts"))
sys.path.insert(0, V5_DIR)
sys.path.insert(0, HERE)
V5 = {"__file__": os.path.join(V5_DIR, "still_v5.py"), "__name__": "still_v5"}
_src = open(os.path.join(V5_DIR, "still_v5.py")).read()
exec(compile(_src[:_src.rindex("\nmain()")], "still_v5.py", "exec"), V5)
V4 = V5["V4"]
V3 = V4["V3"]
PL = V3["PL"]
import dieoff_v8 as DO  # noqa: E402

LEAF_W = 0.10          # a leaf fades over this much of the loss (soft, so a leaf thins rather than pops)
NVAR = V3["NVAR"]


# ---------------------------------------------------------------- the models with per-leaf and per-stem numbers

class _Rec:
    """Wraps plants.Geo's primitives to note, per face, which element (leaf, blade, card, stem) it belongs to and a
    stem's radius. The wrapped calls are the originals: the geometry and every random draw are unchanged."""
    def __init__(self):
        self.orig = {}

    def install(self):
        G = PL.Geo
        for nm in ("tubes", "leaves", "blades"):
            self.orig[nm] = getattr(G, nm)
        rec = self

        def tubes(g, P, R, sides, col):
            n0 = sum(len(f) for f in g.F)
            out = rec.orig["tubes"](g, P, R, sides, col)
            P = np.asarray(P, float)
            n1 = sum(len(f) for f in g.F)
            if n1 > n0:
                b, n = P.shape[:2]
                per = (n - 1) * sides * 2
                R = np.asarray(R, float)
                for k in range(b):
                    g._grp.append((per, float(R[k].mean()), float(P[k, :, 2].min())))
            return out

        def leaves(g, B, U, S, L, W, col, widest=0.35, fold=0.22, outline=None):
            n0 = sum(len(f) for f in g.F)
            out = rec.orig["leaves"](g, B, U, S, L, W, col, widest, fold, outline)
            n1 = sum(len(f) for f in g.F)
            m = len(B)
            if m and n1 > n0:
                per = (n1 - n0) // m
                g._grp.extend([(per, 0.0, 1.0)] * m)
            return out

        def blades(g, B, D, L, W, bend, col, segs=4, taper=1.5, rng=None):
            n0 = sum(len(f) for f in g.F)
            out = rec.orig["blades"](g, B, D, L, W, bend, col, segs, taper, rng)
            n1 = sum(len(f) for f in g.F)
            m = len(B)
            if m and n1 > n0:
                per = (n1 - n0) // m
                g._grp.extend([(per, 0.0, 1.0)] * m)
            return out

        G.tubes, G.leaves, G.blades = tubes, leaves, blades
        _init = G.__init__

        def init(g):
            _init(g)
            g._grp = []
        G.__init__ = init


def face_numbers(geo, seed):
    """Per face: lr (one random number per element) and ord (a stem's drop order: 0 thinnest .. 1 thickest; 9 for a
    stem rising from the ground, which never drops)."""
    V, F, C, K = geo.arrays()
    rng = np.random.default_rng(900000 + seed)
    per = np.array([p for p, r, z in geo._grp], int)
    if per.sum() != len(F):
        raise SystemExit(f"face groups {per.sum()} != faces {len(F)} (seed {seed})")
    rad = np.array([r for p, r, z in geo._grp])
    zmin = np.array([z for p, r, z in geo._grp])
    lr = rng.uniform(0, 1, len(per))
    stem = rad > 0
    ordv = np.full(len(per), 0.5)
    if stem.any():
        rk = rad[stem].argsort().argsort() / max(stem.sum() - 1, 1)
        ordv[stem] = 0.85 * rk + 0.15 * rng.uniform(0, 1, stem.sum())
    ordv[stem & (zmin < 0.03)] = 9.0
    return np.repeat(lr, per), np.repeat(ordv, per)


def build_protos_v8(mat):
    """As still_v3.build_protos, with the face numbers added to each prototype."""
    rec = _Rec()
    rec.install()
    col = bpy.data.collections.new("plant prototypes v3")
    index, k, tris = {}, 0, 0
    for fam, (name, fn, H, lods) in PL.FAMILIES.items():
        for lod in lods:
            for var in range(NVAR):
                seed = 1000 * fam + var
                geo = fn(seed, lod, H)
                ob = V3["to_object"](f"p{k:03d}", geo, mat)
                lr, ordv = face_numbers(geo, seed * 10 + lod)
                me = ob.data
                for key, val in (("lr", lr), ("ord", ordv)):
                    a = me.attributes.new(key, "FLOAT", "FACE")
                    a.data.foreach_set("value", val.astype(np.float32))
                ob.visible_shadow = False
                tris += len(ob.data.polygons)
                col.objects.link(ob)
                index[(fam, lod, var)] = k
                k += 1
    return col, index, tris


# ---------------------------------------------------------------- the material: dying colours and losses

def _attr(nt, name, kind="GEOMETRY"):
    a = nt.nodes.new("ShaderNodeAttribute")
    a.attribute_name = name
    a.attribute_type = kind
    return a.outputs["Fac"]


def _math(nt, op, a, b=None, clamp=False):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    n.use_clamp = clamp
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[0]


def _in(node, name, dtype):
    """A Mix node's input by its identifier (its A, B, Factor exist once per data type)."""
    ident = {"Factor": {"FLOAT": "Factor_Float", "RGBA": "Factor_Float"}}.get(name, {}).get(dtype) or \
        f"{name}_{ {'FLOAT': 'Float', 'RGBA': 'Color'}[dtype] }"
    return next(sk for sk in node.inputs if sk.identifier == ident)


def _out(node, dtype):
    ident = f"Result_{ {'FLOAT': 'Float', 'RGBA': 'Color'}[dtype] }"
    return next(sk for sk in node.outputs if sk.identifier == ident)


def alpha_socket(nt, binary=False):
    """1 where the face is still there, 0 where its leaf, twig or whole plant has gone (instancer attributes leaf,
    twig, fade against the face's lr and ord). Objects without the attributes read 0 for all: always there."""
    card = _attr(nt, "card")
    lr = _attr(nt, "lr")
    ordv = _attr(nt, "ord")
    leaf = _attr(nt, "leaf", "INSTANCER")
    twig = _attr(nt, "twig", "INSTANCER")
    fade = _attr(nt, "fade", "INSTANCER")
    # a leaf: 1 - (loss - lr) / w, clamped; a stem: the same with ord against twig; everything: lr against fade
    a_leaf = _math(nt, "SUBTRACT", 1.0, _math(nt, "DIVIDE", _math(nt, "SUBTRACT", leaf, lr), LEAF_W), clamp=True)
    a_stem = _math(nt, "SUBTRACT", 1.0, _math(nt, "DIVIDE", _math(nt, "SUBTRACT", twig, ordv), LEAF_W), clamp=True)
    mx = nt.nodes.new("ShaderNodeMix")
    mx.data_type = "FLOAT"
    nt.links.new(card, _in(mx, "Factor", "FLOAT"))
    nt.links.new(a_stem, _in(mx, "A", "FLOAT"))
    nt.links.new(a_leaf, _in(mx, "B", "FLOAT"))
    a_all = _math(nt, "SUBTRACT", 1.0, _math(nt, "DIVIDE", _math(nt, "SUBTRACT", fade, lr), LEAF_W), clamp=True)
    a = _math(nt, "MULTIPLY", _out(mx, "FLOAT"), a_all)
    if binary:
        a = _math(nt, "GREATER_THAN", a, 0.5)
    return a


def with_alpha(mat, binary=False):
    """Put the losses' alpha in front of a material's surface (a mix with a transparent BSDF)."""
    nt = mat.node_tree
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    src = out.inputs["Surface"].links[0].from_socket
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    ms = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(alpha_socket(nt, binary), ms.inputs["Fac"])
    nt.links.new(tr.outputs[0], ms.inputs[1])
    nt.links.new(src, ms.inputs[2])
    nt.links.new(ms.outputs[0], out.inputs["Surface"])
    try:
        mat.surface_render_method = "DITHERED"
    except Exception:
        pass
    return mat


def dying_colour(mat):
    """The plant material's face colour turned with `dead` (instancer): 0 as modelled, 0.5 yellow-brown, 1 grey-brown,
    each element a little ahead or behind (its lr), keeping its relative brightness (the crowns' drawn occlusion)."""
    nt = mat.node_tree
    col_attr = next(n for n in nt.nodes if n.type == "ATTRIBUTE" and n.attribute_name == "col")
    links = [l.to_socket for l in col_attr.outputs["Color"].links]
    dead = _attr(nt, "dead", "INSTANCER")
    lr = _attr(nt, "lr")
    card = _attr(nt, "card")
    # d = clamp(1.25 dead - 0.25 lr): elements turn at slightly different times
    d = _math(nt, "SUBTRACT", _math(nt, "MULTIPLY", dead, 1.25), _math(nt, "MULTIPLY", lr, 0.25), clamp=True)
    s1 = _math(nt, "MULTIPLY", d, 2.0, clamp=True)
    s2 = _math(nt, "SUBTRACT", _math(nt, "MULTIPLY", d, 2.0), 1.0, clamp=True)
    bw = nt.nodes.new("ShaderNodeRGBToBW")
    nt.links.new(col_attr.outputs["Color"], bw.inputs[0])
    k = _math(nt, "MINIMUM", _math(nt, "MAXIMUM", _math(nt, "DIVIDE", bw.outputs[0], DO.REF_LUM), 0.45), 1.6)

    def target(rgb_leaf, rgb_stem):
        m = nt.nodes.new("ShaderNodeMix")
        m.data_type = "RGBA"
        nt.links.new(card, _in(m, "Factor", "RGBA"))
        _in(m, "A", "RGBA").default_value = (*DO.lin(rgb_stem), 1)
        _in(m, "B", "RGBA").default_value = (*DO.lin(rgb_leaf), 1)
        sc = nt.nodes.new("ShaderNodeVectorMath")
        sc.operation = "SCALE"
        nt.links.new(_out(m, "RGBA"), sc.inputs[0])
        nt.links.new(k, sc.inputs["Scale"])
        return sc.outputs["Vector"]

    m1 = nt.nodes.new("ShaderNodeMix"); m1.data_type = "RGBA"
    nt.links.new(s1, _in(m1, "Factor", "RGBA"))
    nt.links.new(col_attr.outputs["Color"], _in(m1, "A", "RGBA"))
    nt.links.new(target(DO.YELLOW_LEAF, DO.YELLOW_STEM), _in(m1, "B", "RGBA"))
    m2 = nt.nodes.new("ShaderNodeMix"); m2.data_type = "RGBA"
    nt.links.new(s2, _in(m2, "Factor", "RGBA"))
    nt.links.new(_out(m1, "RGBA"), _in(m2, "A", "RGBA"))
    nt.links.new(target(DO.DEAD_LEAF, DO.DEAD_STEM), _in(m2, "B", "RGBA"))
    for sock in links:
        nt.links.new(_out(m2, "RGBA"), sock)
    return mat


def matte_material():
    """White for the moving wires (pass index 1), black for everything else, with the plants' losses."""
    m = bpy.data.materials.new("matte v8")
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    oi = nt.nodes.new("ShaderNodeObjectInfo")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (1, 1, 1, 1)
    nt.links.new(oi.outputs["Object Index"], em.inputs["Strength"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return with_alpha(m)


# ---------------------------------------------------------------- the scatter, with the die-off's attributes

POINT_ATTRS = (("idx", "INT"), ("rx", "FLOAT"), ("ry", "FLOAT"), ("rz", "FLOAT"), ("sx", "FLOAT"), ("sy", "FLOAT"),
               ("sz", "FLOAT"), ("dead", "FLOAT"), ("leaf", "FLOAT"), ("twig", "FLOAT"), ("fade", "FLOAT"))


def scatter_v8(P, protos, name):
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(P))
    me.vertices.foreach_set("co", P[:, :3].astype(np.float32).ravel())
    for key, typ in POINT_ATTRS:
        me.attributes.new(key, typ, "POINT")
    me.attributes["idx"].data.foreach_set("value", P[:, 5].astype(np.int32))
    ob = bpy.data.objects.new(name, me)
    ob.visible_shadow = False
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
    for key, typ in POINT_ATTRS[:7]:
        na[key] = n.new("GeometryNodeInputNamedAttribute")
        na[key].data_type = typ
        na[key].inputs["Name"].default_value = key
    rot = n.new("ShaderNodeCombineXYZ")
    scl = n.new("ShaderNodeCombineXYZ")
    for i, ax in enumerate("XYZ"):
        ng.links.new(na["r" + ax.lower()].outputs["Attribute"], rot.inputs[ax])
        ng.links.new(na["s" + ax.lower()].outputs["Attribute"], scl.inputs[ax])
    ng.links.new(gi.outputs[0], iop.inputs["Points"])
    ng.links.new(ci.outputs[0], iop.inputs["Instance"])
    ng.links.new(na["idx"].outputs["Attribute"], iop.inputs["Instance Index"])
    ng.links.new(rot.outputs[0], iop.inputs["Rotation"])
    ng.links.new(scl.outputs[0], iop.inputs["Scale"])
    ng.links.new(iop.outputs[0], go.inputs[0])
    ob.modifiers.new(name, "NODES").node_group = ng
    return ob


def set_state(ob, st):
    me = ob.data
    me.vertices.foreach_set("co", st["co"].astype(np.float32).ravel())
    for key in ("rx", "ry", "rz", "sx", "sy", "sz", "dead", "leaf", "twig", "fade"):
        me.attributes[key].data.foreach_set("value", st[key].astype(np.float32))
    me.update()


# ---------------------------------------------------------------- main

def pos_material_v8():
    """v6's position material (still_v6.py: world height in R, distance from the eye in G, emission), with the losses
    as a binary alpha (one exact sample a pixel: a leaf is there or not)."""
    m = bpy.data.materials.new("position v8")
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
    return with_alpha(m, binary=True)


def main():
    a = sys.argv[sys.argv.index("--") + 1:]
    views_json, npz, out_dir, mode = a[:4]
    rest = a[4:]
    one_x_from = 10 ** 9
    if "--one-x-from" in rest:
        i = rest.index("--one-x-from"); one_x_from = int(rest[i + 1]); del rest[i:i + 2]
    matte_every, matte_last = 1, -1
    if "--matte-every" in rest:                          # the matte only every N frames (and at frame LAST)
        i = rest.index("--matte-every"); matte_every, matte_last = (int(x) for x in rest[i + 1].split(","))
        del rest[i:i + 2]
    view = next(v for v in json.load(open(views_json))["views"] if v["id"] == "f")
    os.makedirs(out_dir, exist_ok=True)
    t0 = time.time()
    # v4's setup builds v3's prototypes: build ours instead (same models, the face numbers added)
    V3["build_protos"] = build_protos_v8
    _pm = V3["plant_material"]
    V3["plant_material"] = lambda haze: with_alpha(dying_colour(_pm(haze)))
    ctx = V4["setup"](view)
    s = ctx["s"]
    s.world = ctx["dawn"]                     # (a "day" view: the scene's own world; film-transparent anyway)
    P, pts, z, info = V4["plants"](ctx, npz)
    if mode == "prep":
        fam = pts[:, 3].astype(int)
        np.savez_compressed(f"{out_dir}/plants_laid.npz", P=P, fam=fam, h=pts[:, 5], lod=pts[:, 6].astype(int),
                            var=pts[:, 7].astype(int), ground=z,
                            eye=np.array(ctx["co"].location[:]), heading=ctx["heading"])
        json.dump({"info": info, "camera": list(ctx["co"].location), "prepare_s": round(time.time() - t0, 1)},
                  open(f"{out_dir}/log_prep.json", "w"), indent=1, default=float)
        print("DONE prep", len(P))
        return
    sob = scatter_v8(P, ctx["protos"], "plants f")       # the name seeds each plant's random brightness (v3, v5)
    mov = V4["moving"](ctx)
    for ob in mov:
        ob.pass_index = 1
    glows = [ob for ob in bpy.data.objects if ob.name.startswith("glow ")]
    hide0 = {ob.name: ob.hide_render for ob in set(mov) | set(glows)}      # as the scene has them at frame 4001
    filt0 = s.render.filter_size
    pos_mat = pos_material_v8()
    mat_mat = matte_material()
    D = DO.DieOff(np.load(f"{out_dir}/plants_laid.npz"))
    if len(D.P) != len(P) or np.abs(D.P - P).max() > 1e-3:
        raise SystemExit("plants_laid.npz does not match the plants laid now")
    log = {"camera": list(ctx["co"].location), "plants": info, "prepare_s": round(time.time() - t0, 1), "frames": {}}
    if mode == "preview":          # a quick look at the dying alone (no water): 960x540, 8 samples, over the world
        A, B, step = (int(x) for x in rest[0].split(":"))
        for ob in mov:
            ob.hide_render = True
        s.render.resolution_x, s.render.resolution_y = 960, 540
        s.eevee.taa_render_samples = 8
        s.render.film_transparent = False
        s.render.image_settings.file_format = "PNG"
        s.render.image_settings.color_depth = "8"
        s.render.image_settings.color_mode = "RGB"
        for k in range(A, B, step):
            set_state(sob, D.state(k))
            V4["render"](f"{out_dir}/pv_{k:04d}.png")
            print("PREVIEW", k, flush=True)
        return
    spec = rest[0]
    if ":" in spec:
        A, B = (int(x) for x in spec.split(":"))
        ks = list(range(A, B))
    else:
        ks = [int(x) for x in spec.split(",")]
    print("PREPARED", log["prepare_s"], flush=True)

    def render(path):
        return V4["render"](path)

    for k in ks:
        want_matte = k % matte_every == 0 or k == matte_last
        if all(os.path.exists(f"{out_dir}/{p}_{k:04d}.exr") for p in ("static", "pos") + (("matte",) if want_matte else ())):
            continue
        t1 = time.time()
        set_state(sob, D.state(k))
        lg = {"state_s": round(time.time() - t1, 2)}
        # 1. static: the moving parts hidden (v6's static)
        sc = 2 if k < one_x_from else 1
        bpy.context.view_layer.material_override = None
        for ob in glows:
            ob.hide_render = hide0[ob.name]
        for ob in mov:
            ob.hide_render = True
        s.render.resolution_x, s.render.resolution_y = 1920 * sc, 1080 * sc
        s.eevee.taa_render_samples = 32
        s.render.filter_size = filt0
        s.render.image_settings.color_depth = "16"
        tmp = f"{out_dir}/.static_{k:04d}.exr"
        lg["static_s"] = render(tmp); lg["static_scale"] = sc
        # 2. pos: heights and distances, glows left out, one exact sample
        for ob in glows:
            ob.hide_render = True
        bpy.context.view_layer.material_override = pos_mat
        s.render.resolution_x, s.render.resolution_y = 3840, 2160
        s.eevee.taa_render_samples = 1
        s.render.filter_size = 0.0
        s.render.image_settings.color_depth = "32"
        tmpp = f"{out_dir}/.pos_{k:04d}.exr"
        lg["pos_s"] = render(tmpp)
        # 3. matte: the moving wires white over everything else black, 1x (v5's matte's size and samples)
        tmpm = None
        for t_, p_ in ((tmp, "static"), (tmpp, "pos")):
            os.replace(t_, f"{out_dir}/{p_}_{k:04d}.exr")
        if not want_matte:
            lg["total_s"] = round(time.time() - t1, 2)
            log["frames"][k] = lg
            print("FRAME", k, json.dumps(lg), flush=True)
            json.dump(log, open(f"{out_dir}/log_frames_{os.getpid()}.json", "w"), indent=1, default=float)
            continue
        for ob in set(mov) | set(glows):
            ob.hide_render = hide0[ob.name]
        bpy.context.view_layer.material_override = mat_mat
        s.render.resolution_x, s.render.resolution_y = 1920, 1080
        s.eevee.taa_render_samples = 32
        s.render.filter_size = filt0
        s.render.image_settings.color_depth = "16"
        tmpm = f"{out_dir}/.matte_{k:04d}.exr"
        lg["matte_s"] = render(tmpm)
        os.replace(tmpm, f"{out_dir}/matte_{k:04d}.exr")
        lg["total_s"] = round(time.time() - t1, 2)
        log["frames"][k] = lg
        print("FRAME", k, json.dumps(lg), flush=True)
        json.dump(log, open(f"{out_dir}/log_frames_{os.getpid()}.json", "w"), indent=1, default=float)
    bpy.context.view_layer.material_override = None
    print("DONE frames", len(ks))


main()
