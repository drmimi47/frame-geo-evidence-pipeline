"""Builds the crossing's scene in Blender from scene.json and renders one camera's frames. Runs inside Blender:

    blender -b --factory-startup -P build.py -- <scene.json> <camera_<variant>.json> <out_dir> [first last]
                                                [--blend <file.blend>] [--no-render]

`--blend` saves the built scene to open in Blender (the segment's scene file, no .blend1 beside it); `--no-render`
stops there.

Everything comes from the files: the land (terrain.npz: FABDEM heights on the zoom-out's plane, the drained bed's
inside the reservoir; the passes as its colour, unlit: the imagery is the light; each pass crossfaded into the next by
the frame's `textures`), the water (water.npz: a surface over the reservoir at the frame's `level_m`, its colour the
passes' water, a sky's reflection and drawn ripples), the
towers as modelled (towers.npz: each type's mesh, placed at its OSM point and turned to its line, caissons under those
in the water, shaded by a fixed sun), the fittings along the spans, each phase's sub-conductors hung between them
(emissive, by voltage, with a glow round the bundle; unlit steel grey while the record says cut off) and the earth
wires, every wire at its real size or `MIN_PX` wide where that is thinner (by its own distance from the camera,
geometry nodes), the camera keyed frame by frame. Never edited by hand.
Only bpy and numpy (Blender's own Python), so no imports from the package.
"""

import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np

def _lin(rgb):
    """An on-screen (sRGB, 0-255) colour as Blender's linear light, so the render shows it as the 2D film does."""
    return tuple(((v / 255 + 0.055) / 1.055) ** 2.4 if v / 255 > 0.04045 else v / 255 / 12.92 for v in rgb)


WIRE_RGB = {750: (1.0, 0.86, 0.12), 330: (1.0, 0.5, 0.04)}
# Light means power (decided with the user, 2 November 2026), as in the 2D film (zoomout.STATE_RGB): a connected wire
# lit (above, with its glow and flow); a cut one unlit, the bare wire in steel grey, thinner and with no glow; an
# unreported one the same, dotted along it (still dots, unlike the flow's moving dashes). The 2D film's steel a shade
# darker, as here it is seen against the sky. Given as on screen, converted (they were once the 2D's numbers used as
# linear, which showed a pale salmon for its dark red).
STEEL_RGB = {750: (150, 154, 160), 330: (136, 140, 146)}
DOT_GAP_RGB = (52, 54, 58)  # between an unreported wire's dots
DOT_M = 24.0  # an unreported wire's dot and gap, metres along it
OFF_RGB = {kv: _lin(c) for kv, c in STEEL_RGB.items()}
UNKNOWN_RGB = OFF_RGB
OFF_WIDTH, UNKNOWN_WIDTH = 0.5, 0.75  # of its width (zoomout.STATE_W)
GLOW_R = {750: 0.6, 330: 0.6}  # the glow round a connected phase's bundle, the same on both lines so their flow reads alike
# (a drawing convention, said in scene.json)
GLOW_A = 0.25
GLOW_NEAR_M = (60.0, 400.0)  # it fades out closer than this to the camera, so the clamps and sub-conductors show
MIN_PX = 0.7  # however far, a wire is drawn at least this many pixels across (a drawing convention, said in scene.json)
WIRES = {}  # drawn line's name -> (its state mixes, its glow's mix, its min-width value), keyed per frame from the record
EARTHS = []  # the earth wires' min-width values
MESHES = {}  # each tower type's mesh (and "_mats", the towers' materials), made once by towers_and_wires
FLOW = {}  # drawn line's name -> its materials' flow nodes ("flow time", "flow dir", "flow"), keyed per frame
FLOW_HEAD = 3.0   # a dash's head this much brighter than the wire (white-hot), its tail fading behind it
FLOW_TAIL = 14.0  # how sharply the tail fades (the power of its fall-off: higher is shorter)
FLOW_DOT_M = 10.0  # still dots along the wire between the dashes, as on TouchDesigner's cooking wires
FLOW_LAND = 0.35   # the dashes' and dots' strength on land, against 1 over the water (the wires' `cross`, towers.wires);
# the wire under them is the same everywhere
HAZE_RGB = (0.62, 0.66, 0.70)
RELIEF = (0.5, 0.645)  # the land shaded by its slope toward the same sun: level ground as the imagery has it (x1.0),
                       # a bank facing away darker (a drawn hillshade, true to size, so the bed's depth reads)
SUN = (0.35, -0.61, 0.71)  # toward the sun: the south-east, 45° up, as in the imagery (a morning pass): the towers' shading


def _args():
    a = sys.argv[sys.argv.index("--") + 1:]
    blend = None
    if "--blend" in a:
        i = a.index("--blend")
        blend = Path(a[i + 1])
        del a[i:i + 2]
    render = "--no-render" not in a
    a = [x for x in a if x != "--no-render"]
    rng = (int(a[3]), int(a[4])) if len(a) >= 5 else None
    return Path(a[0]), Path(a[1]), Path(a[2]), rng, blend, render


def _node(nodes, kind):
    return nodes.new(kind)


def _haze(mat, colour_socket, haze_m):
    """Mix a colour into the sky's haze by distance from the camera (the land's box ends; the far land fades)."""
    nt = mat.node_tree
    cam = _node(nt.nodes, "ShaderNodeCameraData")
    ramp = _node(nt.nodes, "ShaderNodeMapRange")
    ramp.inputs["From Min"].default_value, ramp.inputs["From Max"].default_value = haze_m
    ramp.interpolation_type = "SMOOTHSTEP"
    ramp.label = "haze"  # keyed per frame: measured on from what the camera looks at
    nt.links.new(cam.outputs["View Distance"], ramp.inputs["Value"])
    mix = _node(nt.nodes, "ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["B"].default_value = (*HAZE_RGB, 1.0)
    nt.links.new(ramp.outputs["Result"], mix.inputs["Factor"])
    nt.links.new(colour_socket, mix.inputs["A"])
    return mix.outputs["Result"]


def _sunlit(nt, colour, k=(0.325, 0.675)):
    """The colour shaded as by a fixed sun (unlit otherwise: emission, like the imagery): by default 0.35 facing away
    from it up to 1.0 facing it; `k` the slope and offset on the normal's dot with the sun."""
    geo = _node(nt.nodes, "ShaderNodeNewGeometry")
    dot = _node(nt.nodes, "ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    dot.inputs[1].default_value = SUN
    nt.links.new(geo.outputs["Normal"], dot.inputs[0])
    lit = _node(nt.nodes, "ShaderNodeMath")
    lit.operation = "MULTIPLY_ADD"
    nt.links.new(dot.outputs["Value"], lit.inputs[0])
    lit.inputs[1].default_value, lit.inputs[2].default_value = k   # dot -1..1 -> 0.35..1.0 by default
    scale = _node(nt.nodes, "ShaderNodeVectorMath")
    scale.operation = "SCALE"
    nt.links.new(colour, scale.inputs[0])
    nt.links.new(lit.outputs["Value"], scale.inputs["Scale"])
    return scale.outputs["Vector"]


def _flow(nt, colour, dash_m, speed):
    """Dashes running along the wire (its `along` attribute: metres from the line's plant end) at `speed`, toward the
    plant while the keyed "flow dir" is +1, away while -1: a bright head and a tail fading behind it every `dash_m`,
    still dots between; as much as the keyed "flow" (the line's connected weight). The wire dims the same everywhere;
    its dashes and dots are fullest over the water (`cross`) and FLOW_LAND of that on land. Returns the colour, the
    comet (as strong as the dashes there) and the keyed flow."""
    def node(kind, op=None, label=None, a=None, b=None):
        n = _node(nt.nodes, kind)
        if op:
            n.operation = op
        if label:
            n.label = label
        for k, x in ((0, a), (1, b)):
            if x is None:
                continue
            if isinstance(x, (int, float)):
                n.inputs[k].default_value = x
            else:
                nt.links.new(x, n.inputs[k])
        return n
    attr, cross = _node(nt.nodes, "ShaderNodeAttribute"), _node(nt.nodes, "ShaderNodeAttribute")
    attr.attribute_type, attr.attribute_name = "GEOMETRY", "along"
    cross.attribute_type, cross.attribute_name = "GEOMETRY", "cross"
    t, d, keyed = (node("ShaderNodeValue", label=x) for x in ("flow time", "flow dir", "flow"))
    where = node("ShaderNodeMath", "MULTIPLY_ADD", a=cross.outputs["Fac"], b=1.0 - FLOW_LAND)
    where.inputs[2].default_value = FLOW_LAND
    amount = node("ShaderNodeMath", "MULTIPLY", a=keyed.outputs[0], b=where.outputs[0])
    tv = node("ShaderNodeMath", "MULTIPLY", a=t.outputs[0], b=float(speed))   # u = along·dir + time·speed
    u = node("ShaderNodeMath", "ADD", a=node("ShaderNodeMath", "MULTIPLY", a=attr.outputs["Fac"], b=d.outputs[0]).outputs[0],
             b=tv.outputs[0])
    ph = node("ShaderNodeMath", "FRACT", a=node("ShaderNodeMath", "DIVIDE", a=u.outputs[0], b=float(dash_m)).outputs[0])
    comet = node("ShaderNodeMath", "POWER", a=node("ShaderNodeMath", "SUBTRACT", a=1.0, b=ph.outputs[0]).outputs[0],
                 b=FLOW_TAIL)
    dots = node("ShaderNodeMath", "GREATER_THAN",
                a=node("ShaderNodeMath", "FRACT", a=node("ShaderNodeMath", "DIVIDE", a=attr.outputs["Fac"], b=FLOW_DOT_M).outputs[0]).outputs[0],
                b=0.5)
    # the wire's brightness: 1 - 0.5·flow (the same on land and water), plus the particles as strong as the dashes
    # there: +0.12 on a dot, up to FLOW_HEAD at a head
    pat = node("ShaderNodeMath", "MULTIPLY_ADD", a=comet.outputs[0], b=FLOW_HEAD)
    nt.links.new(node("ShaderNodeMath", "MULTIPLY", a=dots.outputs[0], b=0.12).outputs[0], pat.inputs[2])
    dim = node("ShaderNodeMath", "MULTIPLY_ADD", a=keyed.outputs[0], b=-0.5)
    dim.inputs[2].default_value = 1.0
    lerp = node("ShaderNodeMath", "MULTIPLY_ADD", a=amount.outputs[0], b=pat.outputs[0])
    nt.links.new(dim.outputs[0], lerp.inputs[2])
    scaled = node("ShaderNodeVectorMath", "SCALE", a=colour)
    nt.links.new(lerp.outputs[0], scaled.inputs["Scale"])
    white = node("ShaderNodeMath", "MULTIPLY", a=comet.outputs[0], b=amount.outputs[0])
    hot = node("ShaderNodeVectorMath", "ADD", a=scaled.outputs["Vector"])
    nt.links.new(node("ShaderNodeMath", "MULTIPLY", a=white.outputs[0], b=0.8).outputs[0], hot.inputs[1])
    return hot.outputs["Vector"], white.outputs[0], keyed.outputs[0]


def _emission_material(name, haze_m, rgb=None, image=None, strength=1.0, after=None, off_rgb=None, unknown_rgb=None,
                       sun=False, glow=False, flow=None, images=None, relief=False, masks=None):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    em = _node(nt.nodes, "ShaderNodeEmission")
    em.inputs["Strength"].default_value = strength
    if images:   # the passes in date order, each mixed in by its keyed share of what is shown so far ("texture i")
        colour = None
        for i, im in enumerate(images):
            tex = _node(nt.nodes, "ShaderNodeTexImage")
            tex.image = im
            tex.extension = "EXTEND"
            tex.interpolation = "Cubic"
            if colour is None:
                colour = tex.outputs["Color"]
                continue
            mix = _node(nt.nodes, "ShaderNodeMix")
            mix.data_type = "RGBA"
            mix.label = f"texture {i}"
            mix.inputs["Factor"].default_value = 0.0
            nt.links.new(colour, mix.inputs["A"])
            nt.links.new(tex.outputs["Color"], mix.inputs["B"])
            colour = mix.outputs["Result"]
    elif image is not None:
        tex = _node(nt.nodes, "ShaderNodeTexImage")
        tex.image = image
        tex.extension = "EXTEND"
        colour = tex.outputs["Color"]
        if after is not None:  # the later pass on the same grid, mixed in by the frame's `drain` (keyed)
            tex2 = _node(nt.nodes, "ShaderNodeTexImage")
            tex2.image = after
            tex2.extension = "EXTEND"
            mix = _node(nt.nodes, "ShaderNodeMix")
            mix.data_type = "RGBA"
            mix.label = "drain"
            mix.inputs["Factor"].default_value = 0.0
            nt.links.new(colour, mix.inputs["A"])
            nt.links.new(tex2.outputs["Color"], mix.inputs["B"])
            colour = mix.outputs["Result"]
    else:
        rgbn = _node(nt.nodes, "ShaderNodeRGB")
        rgbn.outputs[0].default_value = (*rgb, 1.0)
        colour = rgbn.outputs[0]
        if off_rgb is not None:  # cut off (A) or connected (B), then unreported over it, by the frame's state (keyed)
            mix = _node(nt.nodes, "ShaderNodeMix")
            mix.data_type = "RGBA"
            mix.label = "state"
            mix.inputs["Factor"].default_value = 1.0
            mix.inputs["A"].default_value = (*off_rgb, 1.0)
            nt.links.new(colour, mix.inputs["B"])
            unk = _node(nt.nodes, "ShaderNodeMix")
            unk.data_type = "RGBA"
            unk.label = "unknown"
            unk.inputs["Factor"].default_value = 0.0
            along = _node(nt.nodes, "ShaderNodeAttribute")   # unreported: dotted along the wire, still
            along.attribute_type, along.attribute_name = "GEOMETRY", "along"
            per = _node(nt.nodes, "ShaderNodeMath")
            per.operation = "DIVIDE"
            per.inputs[1].default_value = DOT_M
            ph = _node(nt.nodes, "ShaderNodeMath")
            ph.operation = "FRACT"
            gap = _node(nt.nodes, "ShaderNodeMath")
            gap.operation = "GREATER_THAN"
            gap.inputs[1].default_value = 0.5
            dots = _node(nt.nodes, "ShaderNodeMix")
            dots.data_type = "RGBA"
            dots.inputs["A"].default_value = (*unknown_rgb, 1.0)
            dots.inputs["B"].default_value = (*_lin(DOT_GAP_RGB), 1.0)
            nt.links.new(along.outputs["Fac"], per.inputs[0])
            nt.links.new(per.outputs[0], ph.inputs[0])
            nt.links.new(ph.outputs[0], gap.inputs[0])
            nt.links.new(gap.outputs[0], dots.inputs["Factor"])
            nt.links.new(dots.outputs["Result"], unk.inputs["B"])
            nt.links.new(mix.outputs["Result"], unk.inputs["A"])
            colour = unk.outputs["Result"]
    seen_colour = colour   # the pixels as observed (the water drawn on the land keeps them)
    if sun:
        colour = _sunlit(nt, colour)
    elif relief:
        colour = _sunlit(nt, colour, RELIEF)
    comet = None
    if flow:
        colour, comet, fstrength = _flow(nt, colour, *flow)
    nt.links.new(_haze(mat, colour, haze_m), em.inputs["Color"])
    if glow:  # see-through, as much as the frame's state says (keyed)
        mat.surface_render_method = "BLENDED"
        tr = _node(nt.nodes, "ShaderNodeBsdfTransparent")
        mix = _node(nt.nodes, "ShaderNodeMixShader")
        fade = _node(nt.nodes, "ShaderNodeMapRange")   # none up close, full from GLOW_NEAR_M[1] out
        fade.inputs["From Min"].default_value, fade.inputs["From Max"].default_value = GLOW_NEAR_M
        fade.interpolation_type = "SMOOTHSTEP"
        nt.links.new(_node(nt.nodes, "ShaderNodeCameraData").outputs["View Distance"], fade.inputs["Value"])
        amount = _node(nt.nodes, "ShaderNodeMath")
        amount.operation = "MULTIPLY"
        amount.label = "glow"
        amount.inputs[1].default_value = GLOW_A
        nt.links.new(fade.outputs["Result"], amount.inputs[0])
        fac = amount.outputs[0]
        if comet is not None:  # the glow thickens at a dash's head, thins between (×0.5 .. ×2 as "flow" is full)
            k = _node(nt.nodes, "ShaderNodeMath")
            k.operation = "MULTIPLY_ADD"
            nt.links.new(comet, k.inputs[0])
            k.inputs[1].default_value = 1.5
            half = _node(nt.nodes, "ShaderNodeMath")
            half.operation = "MULTIPLY_ADD"   # 1 - 0.5·flow
            nt.links.new(fstrength, half.inputs[0])
            half.inputs[1].default_value, half.inputs[2].default_value = -0.5, 1.0
            nt.links.new(half.outputs[0], k.inputs[2])
            m2 = _node(nt.nodes, "ShaderNodeMath")
            m2.operation = "MULTIPLY"
            nt.links.new(fac, m2.inputs[0])
            nt.links.new(k.outputs[0], m2.inputs[1])
            fac = m2.outputs[0]
        nt.links.new(fac, mix.inputs["Fac"])
        nt.links.new(tr.outputs[0], mix.inputs[1])
        nt.links.new(em.outputs["Emission"], mix.inputs[2])
        nt.links.new(mix.outputs[0], out.inputs["Surface"])
        return mat
    if masks:   # the water each pass saw (its mask, chained by the same keyed shares as the passes): the water's look
        wm = None
        for i, im in enumerate(masks):
            if im is None:
                v = _node(nt.nodes, "ShaderNodeValue")
                v.outputs[0].default_value = 0.0
                src = v.outputs[0]
            else:
                tex = _node(nt.nodes, "ShaderNodeTexImage")
                tex.image = im
                tex.image.colorspace_settings.name = "Non-Color"
                tex.extension = "EXTEND"
                src = tex.outputs["Color"]
            if wm is None:
                wm = src
                continue
            mix = _node(nt.nodes, "ShaderNodeMix")
            mix.data_type = "FLOAT"
            mix.label = f"texture {i}"
            mix.inputs["Factor"].default_value = 0.0
            nt.links.new(wm, mix.inputs["A"])
            nt.links.new(src, mix.inputs["B"])
            wm = mix.outputs["Result"]
        edge = _node(nt.nodes, "ShaderNodeMapRange")   # the 10 m mask's edge, sharpened a little
        edge.inputs["From Min"].default_value, edge.inputs["From Max"].default_value = MASK_EDGE
        edge.interpolation_type = "SMOOTHSTEP"
        nt.links.new(wm, edge.inputs["Value"])
        shader, *_ = _water_nodes(nt, haze_m, colour=seen_colour)
        both = _node(nt.nodes, "ShaderNodeMixShader")
        nt.links.new(edge.outputs["Result"], both.inputs["Fac"])
        nt.links.new(em.outputs["Emission"], both.inputs[1])
        nt.links.new(shader, both.inputs[2])
        nt.links.new(both.outputs[0], out.inputs["Surface"])
        return mat
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return mat


MASK_EDGE = (0.25, 0.75)


def terrain(sc, base, haze_m):
    t = np.load(base / sc["terrain"]["file"])
    xs, ys, z, u, v = t["x"], t["y"], t["z"], t["u"], t["v"]
    ny, nx = z.shape
    gx, gy = np.meshgrid(xs, ys)
    verts = np.stack([gx.ravel(), gy.ravel(), z.ravel()], 1).astype(np.float32)
    i = np.arange(ny * nx).reshape(ny, nx)
    quads = np.stack([i[:-1, :-1], i[:-1, 1:], i[1:, 1:], i[1:, :-1]], -1).reshape(-1, 4)
    me = bpy.data.meshes.new("land")
    me.vertices.add(len(verts))
    me.vertices.foreach_set("co", verts.ravel())
    me.loops.add(quads.size)
    me.loops.foreach_set("vertex_index", quads.ravel().astype(np.int32))
    me.polygons.add(len(quads))
    me.polygons.foreach_set("loop_start", (np.arange(len(quads)) * 4).astype(np.int32))
    me.polygons.foreach_set("loop_total", np.full(len(quads), 4, np.int32))
    uv = me.uv_layers.new(name="uv")
    uvs = np.stack([u.ravel(), v.ravel()], 1)[quads.ravel()]
    uv.data.foreach_set("uv", uvs.astype(np.float32).ravel())
    me.update(calc_edges=True)
    me.validate()
    ob = bpy.data.objects.new("land", me)
    sc_ = bpy.context.scene
    sc_.collection.objects.link(ob)
    if sc["terrain"].get("textures"):
        me.shade_smooth()
        ts = sc["terrain"]["textures"]
        masks = [bpy.data.images.load(t["water"]) if t.get("water") else None for t in ts]
        ob.data.materials.append(_emission_material("land", haze_m, images=[bpy.data.images.load(t["file"]) for t in ts],
                                                    relief=True, masks=masks if any(masks) else None))
        return ob
    img = bpy.data.images.load(sc["terrain"]["texture"])
    after = sc["terrain"].get("texture_after")
    ob.data.materials.append(_emission_material("land", haze_m, image=img,
                                                after=bpy.data.images.load(after["file"]) if after else None))
    return ob


def land_south(sc, base, haze_m):
    """The land on south of the box (the flight south looks that way): the same passes on a strip of their own, keyed
    by the same shares ("texture i"), shaded by its relief like the land."""
    ls = sc["land_south"]
    t = np.load(base / ls["file"])
    xs, ys, z, u, v = t["x"], t["y"], t["z"], t["u"], t["v"]
    ny, nx = z.shape
    gx, gy = np.meshgrid(xs, ys)
    verts = np.stack([gx.ravel(), gy.ravel(), z.ravel()], 1).astype(np.float32)
    i = np.arange(ny * nx).reshape(ny, nx)
    quads = np.stack([i[:-1, :-1], i[:-1, 1:], i[1:, 1:], i[1:, :-1]], -1).reshape(-1, 4)
    me = _mesh("land south", verts, quads.ravel().astype(np.int32), np.full(len(quads), 4, np.int32),
               np.zeros(len(quads), np.int32), [])
    uv = me.uv_layers.new(name="uv")
    uv.data.foreach_set("uv", np.stack([u.ravel(), v.ravel()], 1)[quads.ravel()].astype(np.float32).ravel())
    me.shade_smooth()
    ob = bpy.data.objects.new("land south", me)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(_emission_material("land south", haze_m, relief=True,
                                                images=[bpy.data.images.load(x["file"]) for x in ls["textures"]]))
    return ob


def plant(sc, base, haze_m):
    """The plant, the thermal plant and Enerhodar as modelled (plant.npz, plant.py): one object, shaded by the fixed
    sun like the towers."""
    pd = sc["plant"]
    npz = np.load(base / pd["file"])
    mats = [_emission_material(f"plant {name}", haze_m, rgb=tuple(rgb), sun=True)
            for name, rgb in (pd["materials"][str(k)] for k in range(len(pd["materials"])))]
    ob = bpy.data.objects.new("plant", _mesh("plant", npz["v"], npz["loops"], npz["counts"], npz["mat"], mats))
    bpy.context.scene.collection.objects.link(ob)
    return ob


WATER_ROUGH = 0.06     # the surface's roughness: a light breeze (drawn)
RIPPLE_M = 9.0         # the ripples' size and how fast they move (drawn: noise, said in scene.json)
RIPPLE_BUMP = 0.2
REFLECT = 0.5          # the sky's reflection at half of Fresnel's, a little darker than the sky (a silty river under
REFLECT_RGB = (0.78, 0.8, 0.82)   # haze, not a mirror: drawn, said in scene.json)


def water(sc, base, haze_m):
    """The water's surface (pass 3): a sheet over the reservoir's footprint (water.npz on the land's grid), raised and
    lowered to the frame's level and tilted along the river as its slope forms, about the crossing (keyed); and the
    water seen on each later pass, one sheet with a shape key per pass, mixed by the passes' shares (keyed). Its
    colour the passes' own water (keyed), mixed with a glossy reflection by Fresnel; ripples drawn. Hazed by distance
    like the land."""
    t = np.load(base / sc["terrain"]["file"])
    w = np.load(base / sc["terrain"]["water"]["file"])
    first = bpy.data.images.load(sc["terrain"]["textures"][0]["file"])
    mat, body, noise, seen = _water_material(haze_m, first)
    ob = _sheet("reservoir", w["mask"], t["x"] - float(w["pivot_x"]), t["y"], t["u"], t["v"], mat)
    keys = []
    if "sheet_z" in w.files:
        region = w["sheet_region"]
        sh = _sheet("seen", region, t["x"], t["y"], t["u"], t["v"], mat, z=t["z"] - 1.0)
        idx = np.flatnonzero(region.ravel())   # the region's vertices, in the order _sheet keeps them
        sh.shape_key_add(name="hidden", from_mix=False)
        for i, zz in enumerate(w["sheet_z"]):
            kb = sh.shape_key_add(name=f"pass {i + 1}", from_mix=False)
            co = np.empty(len(sh.data.vertices) * 3, np.float32)
            kb.data.foreach_get("co", co)
            co = co.reshape(-1, 3)
            co[:, 2] = zz[np.searchsorted(idx, _used(region))]
            kb.data.foreach_set("co", co.ravel())
            keys.append(kb)
    return ob, float(w["pivot_x"]), body, noise, seen, keys


def _used(m):
    """The grid vertices a sheet over mask m keeps (its quads' corners), in its vertex order."""
    i = np.arange(m.size).reshape(m.shape)
    q = m[:-1, :-1] & m[:-1, 1:] & m[1:, 1:] & m[1:, :-1]
    return np.unique(np.stack([i[:-1, :-1][q], i[:-1, 1:][q], i[1:, 1:][q], i[1:, :-1][q]], -1))


def _sheet(name, m, xs, ys, us, vs, mat, z=None):
    ny, nx = m.shape
    gx, gy = np.meshgrid(xs, ys)
    i = np.arange(ny * nx).reshape(ny, nx)
    q = m[:-1, :-1] & m[:-1, 1:] & m[1:, 1:] & m[1:, :-1]
    quads = np.stack([i[:-1, :-1][q], i[:-1, 1:][q], i[1:, 1:][q], i[1:, :-1][q]], -1)
    used, inv = np.unique(quads, return_inverse=True)
    zs = np.zeros(len(used)) if z is None else z.ravel()[used]
    verts = np.stack([gx.ravel()[used], gy.ravel()[used], zs], 1).astype(np.float32)
    quads = inv.reshape(-1, 4)
    me = bpy.data.meshes.new(f"water {name}")
    me.vertices.add(len(verts))
    me.vertices.foreach_set("co", verts.ravel())
    me.loops.add(quads.size)
    me.loops.foreach_set("vertex_index", quads.ravel().astype(np.int32))
    me.polygons.add(len(quads))
    me.polygons.foreach_set("loop_start", (np.arange(len(quads)) * 4).astype(np.int32))
    me.polygons.foreach_set("loop_total", np.full(len(quads), 4, np.int32))
    uv = me.uv_layers.new(name="uv")
    uvs = np.stack([us.ravel()[used], vs.ravel()[used]], 1)[quads.ravel()]
    uv.data.foreach_set("uv", uvs.astype(np.float32).ravel())
    me.update(calc_edges=True)
    me.validate()
    ob = bpy.data.objects.new(f"water {name}", me)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(mat)
    return ob


def _water_material(haze_m, first):
    """The water's look; its colour the first pass's own pixels while that pass is shown (the reservoir as observed,
    keyed "water seen"), then the passes' measured water colour (keyed "water colour")."""
    mat = bpy.data.materials.new("water")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    shader, body, noise, seen = _water_nodes(nt, haze_m, first)
    nt.links.new(shader, out.inputs["Surface"])
    return mat, body, noise, seen


def _water_nodes(nt, haze_m, first=None, colour=None):
    """The water's shader in a node tree: its colour (an RGB keyed "water colour", or with `first` that pass's
    pixels mixed over it, keyed "water seen"; or a given `colour`, the land's own pixels) as emission, a glossy
    reflection by Fresnel on drawn ripples (keyed "ripples"), hazed by distance as the land. Returns the shader and
    the keyed nodes."""
    body, seen = None, None
    if colour is None:
        body = _node(nt.nodes, "ShaderNodeRGB")
        body.label = "water colour"   # keyed: the passes' water, by the frame's textures
        colour = body.outputs[0]
    if first is not None:
        img = _node(nt.nodes, "ShaderNodeTexImage")
        img.image = first
        img.extension = "EXTEND"
        seen = _node(nt.nodes, "ShaderNodeMix")
        seen.data_type = "RGBA"
        seen.label = "water seen"
        nt.links.new(colour, seen.inputs["A"])
        nt.links.new(img.outputs["Color"], seen.inputs["B"])
        colour = seen.outputs["Result"]
    em = _node(nt.nodes, "ShaderNodeEmission")
    nt.links.new(colour, em.inputs["Color"])
    coords = _node(nt.nodes, "ShaderNodeTexCoord")
    noise = _node(nt.nodes, "ShaderNodeTexNoise")
    noise.noise_dimensions = "4D"
    noise.label = "ripples"       # keyed: W runs with the film's time
    noise.inputs["Scale"].default_value = 1.0 / RIPPLE_M
    noise.inputs["Detail"].default_value = 6.0
    noise.inputs["Roughness"].default_value = 0.55
    nt.links.new(coords.outputs["Object"], noise.inputs["Vector"])
    bump = _node(nt.nodes, "ShaderNodeBump")
    bump.inputs["Strength"].default_value = RIPPLE_BUMP
    bump.inputs["Distance"].default_value = 0.5
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    gl = _node(nt.nodes, "ShaderNodeBsdfGlossy")
    gl.inputs["Roughness"].default_value = WATER_ROUGH
    gl.inputs["Color"].default_value = (*REFLECT_RGB, 1.0)
    nt.links.new(bump.outputs["Normal"], gl.inputs["Normal"])
    fr = _node(nt.nodes, "ShaderNodeFresnel")
    fr.inputs["IOR"].default_value = 1.333
    nt.links.new(bump.outputs["Normal"], fr.inputs["Normal"])
    k = _node(nt.nodes, "ShaderNodeMath")
    k.operation = "MULTIPLY"
    k.inputs[1].default_value = REFLECT
    nt.links.new(fr.outputs["Fac"], k.inputs[0])
    mix = _node(nt.nodes, "ShaderNodeMixShader")
    nt.links.new(k.outputs[0], mix.inputs["Fac"])
    nt.links.new(em.outputs["Emission"], mix.inputs[1])
    nt.links.new(gl.outputs["BSDF"], mix.inputs[2])
    cam = _node(nt.nodes, "ShaderNodeCameraData")   # hazed by distance, as the land
    ramp = _node(nt.nodes, "ShaderNodeMapRange")
    ramp.inputs["From Min"].default_value, ramp.inputs["From Max"].default_value = haze_m
    ramp.interpolation_type = "SMOOTHSTEP"
    ramp.label = "haze"
    nt.links.new(cam.outputs["View Distance"], ramp.inputs["Value"])
    hz = _node(nt.nodes, "ShaderNodeEmission")
    hz.inputs["Color"].default_value = (*HAZE_RGB, 1.0)
    fin = _node(nt.nodes, "ShaderNodeMixShader")
    nt.links.new(ramp.outputs["Result"], fin.inputs["Fac"])
    nt.links.new(mix.outputs[0], fin.inputs[1])
    nt.links.new(hz.outputs["Emission"], fin.inputs[2])
    return fin.outputs[0], body, noise, seen


def _mesh(name, v, loops, counts, mat, mats):
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(v))
    me.vertices.foreach_set("co", v.ravel())
    me.loops.add(len(loops))
    me.loops.foreach_set("vertex_index", loops)
    me.polygons.add(len(counts))
    me.polygons.foreach_set("loop_start", np.concatenate([[0], np.cumsum(counts)[:-1]]).astype(np.int32))
    me.polygons.foreach_set("loop_total", counts)
    me.update(calc_edges=True)
    me.validate()
    for m in mats:
        me.materials.append(m)
    me.polygons.foreach_set("material_index", mat.astype(np.int32))
    return me


def _curve(name, polylines, bevel, material, along=None, cross=None):
    """A curve of poly splines; `along` and `cross` (per spline, per point) ride in the points' radius and tilt for
    _wires to store."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = bevel
    cu.bevel_resolution = 1
    for k, pts in enumerate(polylines):
        sp = cu.splines.new("POLY")
        sp.points.add(len(pts) - 1)
        sp.points.foreach_set("co", np.hstack([pts, np.ones((len(pts), 1), np.float32)]).ravel())
        if along is not None:
            sp.points.foreach_set("radius", np.asarray(along[k], np.float32))
        if cross is not None:
            sp.points.foreach_set("tilt", np.asarray(cross[k], np.float32))
    ob = bpy.data.objects.new(name, cu)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(material)
    return ob


def _wires(name, polylines, r, material, camera, along=None, cross=None):
    """Wires at their real radius `r`, or wider where that is under `MIN_PX` pixels at their own distance from the
    camera (geometry nodes: a circle swept along each, scaled per point by max(r, distance × the frame's `min width`,
    keyed: half MIN_PX's metres a pixel per metre of distance, by the record's state)). Returns that value's node."""
    ob = _curve(name, polylines, 0.0, material, along, cross)
    ng = bpy.data.node_groups.new(name, "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    n = ng.nodes
    gin, gout = n.new("NodeGroupInput"), n.new("NodeGroupOutput")
    prof = n.new("GeometryNodeCurvePrimitiveCircle")
    prof.inputs["Resolution"].default_value, prof.inputs["Radius"].default_value = 6, 1.0
    pos, cam = n.new("GeometryNodeInputPosition"), n.new("GeometryNodeObjectInfo")
    cam.inputs["Object"].default_value = camera
    dist = n.new("ShaderNodeVectorMath")
    dist.operation = "DISTANCE"
    ng.links.new(pos.outputs[0], dist.inputs[0])
    ng.links.new(cam.outputs["Location"], dist.inputs[1])
    k = n.new("ShaderNodeValue")
    k.label = "min width"
    mul, mx = n.new("ShaderNodeMath"), n.new("ShaderNodeMath")
    mul.operation, mx.operation = "MULTIPLY", "MAXIMUM"
    ng.links.new(dist.outputs["Value"], mul.inputs[0])
    ng.links.new(k.outputs[0], mul.inputs[1])
    ng.links.new(mul.outputs[0], mx.inputs[0])
    mx.inputs[1].default_value = r
    sweep, setm = n.new("GeometryNodeCurveToMesh"), n.new("GeometryNodeSetMaterial")
    store = n.new("GeometryNodeStoreNamedAttribute")   # the points' radius (metres along the line) as `along`
    store.data_type, store.domain = "FLOAT", "POINT"
    store.inputs["Name"].default_value = "along"
    ng.links.new(gin.outputs[0], store.inputs["Geometry"])
    ng.links.new(n.new("GeometryNodeInputRadius").outputs[0], store.inputs["Value"])
    store2 = n.new("GeometryNodeStoreNamedAttribute")   # and their tilt as `cross`
    store2.data_type, store2.domain = "FLOAT", "POINT"
    store2.inputs["Name"].default_value = "cross"
    ng.links.new(store.outputs[0], store2.inputs["Geometry"])
    ng.links.new(n.new("GeometryNodeInputCurveTilt").outputs[0], store2.inputs["Value"])
    ng.links.new(store2.outputs[0], sweep.inputs["Curve"])
    ng.links.new(prof.outputs["Curve"], sweep.inputs["Profile Curve"])
    ng.links.new(mx.outputs[0], sweep.inputs["Scale"])
    ng.links.new(sweep.outputs["Mesh"], setm.inputs["Geometry"])
    setm.inputs["Material"].default_value = material
    ng.links.new(setm.outputs[0], gout.inputs[0])
    ob.modifiers.new("wire", "NODES").node_group = ng
    return k


def towers_and_wires(sc, base, haze_m, camera, flow=None):
    """Each tower type's mesh once (towers.npz), linked into an object per tower at its point, turned to its line;
    a caisson under those in the water; the fittings along the spans; then each line's sub-conductors and jumpers
    (keyed by the record), the glow round its bundles and its earth wires."""
    tdoc = sc["towers"]
    npz = np.load(base / tdoc["file"])
    mats = [_emission_material(name, haze_m, rgb=tuple(rgb), sun=True) for name, rgb in
            (tdoc["materials"][str(k)] for k in range(len(tdoc["materials"])))]
    meshes = MESHES
    for ty in list(tdoc["types"]) + ["fittings"]:
        meshes[ty] = _mesh(ty, npz[f"{ty}__v"], npz[f"{ty}__loops"], npz[f"{ty}__counts"], npz[f"{ty}__mat"], mats)
    MESHES["_mats"] = mats
    bpy.context.scene.collection.objects.link(bpy.data.objects.new("fittings", meshes["fittings"]))
    for ln in sc["lines"]:
        for t in ln["towers"]:
            if not t["type"] or t.get("hidden"):
                continue
            ob = bpy.data.objects.new(f"{t['type']} {t['osm_node']}", meshes[t["type"]])
            ob.location = (t["xy"][0], t["xy"][1], t["base_m"])
            ob.rotation_euler = (0.0, 0.0, t["rot_z"])
            bpy.context.scene.collection.objects.link(ob)
            if t["caisson"]:  # its z 0 is the reservoir's level, the tower stands on its top
                ob = bpy.data.objects.new(f"{t['caisson']} {t['osm_node']}", meshes[t["caisson"]])
                ob.location = (t["xy"][0], t["xy"][1], t["ground_m"])
                bpy.context.scene.collection.objects.link(ob)
    _line_wires(sc["lines"], npz, tdoc, mats, haze_m, camera, flow)


def _line_wires(lines, npz, tdoc, mats, haze_m, camera, flow):
    """Each line's sub-conductors and jumpers (keyed by its state), the glow round its bundles and its earth wires,
    from a towers.npz-like file's wire arrays."""
    pts, n = npz["wire_pts"], npz["wire_n"]
    starts = np.concatenate([[0], np.cumsum(n)[:-1]])
    polys = [pts[s:s + k] for s, k in zip(starts, n)]
    alongs = [npz["wire_along"][s:s + k] for s, k in zip(starts, n)]
    crosses = [npz["wire_cross"][s:s + k] for s, k in zip(starts, n)]
    kinds, fit = tdoc["wire_kinds"], tdoc["fittings"]
    for li, ln in enumerate(lines):
        kv = ln["kv"]
        mine = [k for k in range(len(polys)) if npz["wire_line"][k] == li]

        def of(*names, arr=polys):
            return [arr[k] for k in mine if kinds[npz["wire_kind"][k]] in names]

        state = dict(rgb=WIRE_RGB.get(kv, (1, 1, 1)), off_rgb=OFF_RGB.get(kv, (0.5, 0.1, 0.1)),
                     unknown_rgb=UNKNOWN_RGB.get(kv, (0.5, 0.5, 0.5)))
        wire = _emission_material(f"wire {ln['name']}", haze_m, strength=1.3, flow=flow, **state)
        glow = _emission_material(f"glow {ln['name']}", haze_m, strength=1.3, glow=True, flow=flow, **state)
        k = _wires(f"wire {ln['name']}", of("phase", "jumper"), fit["conductor_r_m"][str(kv)], wire, camera,
                   of("phase", "jumper", arr=alongs), of("phase", "jumper", arr=crosses))
        _wires(f"glow {ln['name']}", of("bundle"), GLOW_R.get(kv, 0.5), glow, camera, of("bundle", arr=alongs),
               of("bundle", arr=crosses))
        FLOW[ln["name"]] = [n for m in (wire, glow) for n in m.node_tree.nodes if n.label in ("flow time", "flow dir", "flow")]
        EARTHS.append(_wires(f"earth {ln['name']}", of("earth"), fit["earth_r_m"], mats[5], camera))
        WIRES[ln["name"]] = ([n for m in (wire, glow) for n in m.node_tree.nodes if n.label in ("state", "unknown")],
                             next(n for n in glow.node_tree.nodes if n.label == "glow"), k)


def others(sc, base, haze_m, camera, flow=None):
    """The plant's other lines, its feeds and links (others.npz; a variant's `extras`): their towers as the land types
    already made (a row's first tower left to the line drawn before it where they share it), their wires as the two
    lines', keyed by each frame's `others` states."""
    od = sc["others"]
    for ln in od["lines"]:
        for t in ln["towers"]:
            if not t["type"] or t.get("hidden"):
                continue
            ob = bpy.data.objects.new(f"{t['type']} {t['osm_node']}", MESHES[t["type"]])
            ob.location = (t["xy"][0], t["xy"][1], t["base_m"])
            ob.rotation_euler = (0.0, 0.0, t["rot_z"])
            bpy.context.scene.collection.objects.link(ob)
    _line_wires(od["lines"], np.load(base / od["file"]), sc["towers"], MESHES["_mats"], haze_m, camera, flow)


def main():
    scene_path, cam_path, out, rng, blend, render = _args()
    sc = json.loads(scene_path.read_text())
    cam = json.loads(cam_path.read_text())
    base = scene_path.parent
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    s = bpy.context.scene
    haze_m = sc["render"]["haze_m"]
    cd = bpy.data.cameras.new("camera")
    cd.sensor_width, cd.sensor_fit = 36.0, "HORIZONTAL"
    cd.clip_start, cd.clip_end = 5.0, 150000.0
    co = bpy.data.objects.new("camera", cd)
    s.collection.objects.link(co)
    s.camera = co
    co.rotation_mode = "XYZ"
    terrain(sc, base, haze_m)
    wat = water(sc, base, haze_m) if sc["terrain"].get("water") else None
    fl = cam.get("flow")
    towers_and_wires(sc, base, haze_m, co, (fl["dash_m"], fl["speed_mps"]) if fl else None)
    extras = cam.get("extras") or []   # a variant's own: the plant modelled, the land on south (the flight south)
    if "plant" in extras and sc.get("plant"):
        plant(sc, base, haze_m)
    if "land_south" in extras and sc.get("land_south"):
        land_south(sc, base, haze_m)
    if "others" in extras and sc.get("others"):
        others(sc, base, haze_m, co, (fl["dash_m"], fl["speed_mps"]) if fl else None)

    world = s.world or bpy.data.worlds.new("World")
    s.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (*HAZE_RGB, 1.0)
    bg.inputs["Strength"].default_value = 1.0

    frames = cam["frames"]
    hazes = [n for m in bpy.data.materials if m.node_tree for n in m.node_tree.nodes if n.label == "haze"]
    drains = [n for m in bpy.data.materials if m.node_tree for n in m.node_tree.nodes if n.label == "drain"]
    bodies = [n for m in bpy.data.materials if m.node_tree for n in m.node_tree.nodes if n.label == "water colour"]
    ripples = [n for m in bpy.data.materials if m.node_tree for n in m.node_tree.nodes if n.label == "ripples"]
    layers = sorted(((int(n.label.split()[1]), n) for m in bpy.data.materials if m.node_tree
                     for n in m.node_tree.nodes if n.label.startswith("texture ")), key=lambda x: x[0])
    for i, f in enumerate(frames, start=1):
        co.location = f["location"]
        co.rotation_euler = f["rotation"]
        cd.lens = f["lens"]
        co.keyframe_insert("location", frame=i)
        co.keyframe_insert("rotation_euler", frame=i)
        cd.keyframe_insert("lens", frame=i)
        for r in hazes:  # the haze starts haze_m[0] beyond the target, so the top-down view is clear from any height
            r.inputs["From Min"].default_value = f["dist"] + haze_m[0]
            r.inputs["From Max"].default_value = f["dist"] + haze_m[1]
            r.inputs["From Min"].keyframe_insert("default_value", frame=i)
            r.inputs["From Max"].keyframe_insert("default_value", frame=i)
        for m in drains:
            m.inputs["Factor"].default_value = f.get("drain", 0.0)
            m.inputs["Factor"].keyframe_insert("default_value", frame=i)
        if f.get("textures"):   # each pass's share of what is shown so far, so the chain of mixes sums to the weights
            w = f["textures"]
            for k, m in layers:
                so_far = sum(w[:k + 1])
                m.inputs["Factor"].default_value = w[k] / so_far if so_far > 1e-6 else 0.0
                m.inputs["Factor"].keyframe_insert("default_value", frame=i)
        if wat and f.get("level_m") is not None:
            ob, px, body, noise, seen, keys = wat
            for k, kb in enumerate(keys, start=1):   # the water seen on each later pass, by its pass's share
                kb.value = f["textures"][k] if k < len(f["textures"]) else 0.0
                kb.keyframe_insert("value", frame=i)
            seen.inputs["Factor"].default_value = f["textures"][0]
            seen.inputs["Factor"].keyframe_insert("default_value", frame=i)
            ob.location = (px, 0.0, f["level_m"])
            ob.rotation_euler = (0.0, -math.atan(f.get("water_slope", 0.0)), 0.0)   # rising east (upstream)
            ob.keyframe_insert("location", frame=i)
            ob.keyframe_insert("rotation_euler", frame=i)
            for b in bodies:
                b.outputs[0].default_value = (*f["water_rgb"], 1.0)
                b.outputs[0].keyframe_insert("default_value", frame=i)
            for nz in ripples:
                nz.inputs["W"].default_value = (i - 1) / cam["fps"] * 0.15
                nz.inputs["W"].keyframe_insert("default_value", frame=i)
        per_m = MIN_PX / 2 * 36.0 / f["lens"] / sc["render"]["size"][0]  # half MIN_PX in metres, per metre away
        for k in EARTHS:
            k.outputs[0].default_value = per_m
            k.outputs[0].keyframe_insert("default_value", frame=i)
        for name, (mixes, glow, k) in WIRES.items():  # weights eased in the record (connected without one); the rest cut off
            on, unknown = {**(f.get("others") or {}), **(f.get("lines") or {})}.get(name, (1.0, 0.0))
            share = on + unknown
            for m in mixes:
                m.inputs["Factor"].default_value = (on / share if share > 0 else 0.0) if m.label == "state" else unknown
                m.inputs["Factor"].keyframe_insert("default_value", frame=i)
            glow.inputs[1].default_value = GLOW_A * on
            glow.inputs[1].keyframe_insert("default_value", frame=i)
            k.outputs[0].default_value = per_m * (on + UNKNOWN_WIDTH * unknown + OFF_WIDTH * (1 - share))
            k.outputs[0].keyframe_insert("default_value", frame=i)
            d = f.get("flow", 0)   # the flow: only on a connected line, as far as it is connected
            for m in FLOW.get(name, []):
                m.outputs[0].default_value = {"flow time": (i - 1) / cam["fps"], "flow dir": float(d),
                                              "flow": on * abs(d)}[m.label]
                m.outputs[0].keyframe_insert("default_value", frame=i)

    w, h = sc["render"]["size"]
    s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage = w, h, 100
    s.render.fps = cam["fps"]
    s.frame_start, s.frame_end = rng if rng else (1, len(frames))
    try:
        s.render.engine = "BLENDER_EEVEE"
    except TypeError:
        pass
    if hasattr(s, "eevee"):
        s.eevee.taa_render_samples = 16
        if wat:   # the water's reflections of the towers and wires: screen-space rays (what is on screen)
            s.eevee.use_raytracing = True
            s.eevee.ray_tracing_method = "SCREEN"
            s.eevee.ray_tracing_options.resolution_scale = "2"   # half resolution: the ripples break them up anyway
            s.eevee.ray_tracing_options.trace_max_roughness = 0.3
    try:  # the imagery's colours as they are (a dynamic enum: RNA lists no items, so set it and see)
        s.view_settings.view_transform = "Standard"
    except TypeError as e:
        print("view transform left as it was:", e)
    s.render.image_settings.file_format = "PNG"
    out.mkdir(parents=True, exist_ok=True)
    s.render.filepath = str(out / "f_")
    if blend:
        bpy.context.preferences.filepaths.save_version = 0   # no .blend1: one scene file per segment, replaced each build
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    if render:
        bpy.ops.render.render(animation=True)


main()
