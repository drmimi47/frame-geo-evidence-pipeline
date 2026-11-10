"""Builds the crossing's scene in Blender from scene.json and renders one camera's frames. Runs inside Blender:

    blender -b --factory-startup -P build.py -- <scene.json> <camera_<variant>.json> <out_dir> [first last]
                                                [--blend <file.blend>] [--no-render] [--frames a,b,c]
                                                [--keep-existing]

`--blend` saves the built scene to open in Blender (the segment's scene file, no .blend1 beside it); `--no-render`
stops there. `--frames` renders only those frames (stills for look development); `--keep-existing` leaves frames
already on disk and renders the rest (to resume a long render stopped part way).

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
# A variant's `look` (camera_<variant>.json; the flight south's look pass, 7 November 2026): every option below is
# off unless the variant asks, so the approved films render as they did. LOOKDOC is the scene's own data for it
# (scene.json `look.<variant>`: colour-matched copies of the passes, the pass before the breach).
LOOK = {}
LOOKDOC = {}
BED = {}   # the land's heights as an image (the water's depth over the bed, `look.water.shallow_m`)
PASSES = {}   # look pass 3: the land's pass images in date order and the pre-breach one (the water's colour variation)
SUN = (0.35, -0.61, 0.71)  # toward the sun: the south-east, 45° up, as in the imagery (a morning pass): the towers' shading


def _args():
    a = sys.argv[sys.argv.index("--") + 1:]
    blend = None
    if "--blend" in a:
        i = a.index("--blend")
        blend = Path(a[i + 1])
        del a[i:i + 2]
    stills = None
    if "--frames" in a:
        i = a.index("--frames")
        stills = [int(x) for x in a[i + 1].split(",")]
        del a[i:i + 2]
    render = "--no-render" not in a
    keep = "--keep-existing" in a
    a = [x for x in a if x not in ("--no-render", "--keep-existing")]
    rng = (int(a[3]), int(a[4])) if len(a) >= 5 else None
    return Path(a[0]), Path(a[1]), Path(a[2]), rng, blend, render, stills, keep


def _node(nodes, kind):
    return nodes.new(kind)


def _img(path):
    """A pass's image; with the look's `match`, its colour-matched copy (look.py: a gain and offset per band, measured
    on stable land against the reference pass, said in scene.json)."""
    path = str(path)
    if LOOK.get("match"):
        path = (LOOKDOC.get("matched") or {}).get(path, {}).get("file", path)
    return bpy.data.images.load(path, check_existing=True)


def _math(nt, op, a, b=None, c=None, label=None):
    n = _node(nt.nodes, "ShaderNodeMath")
    n.operation = op
    if label:
        n.label = label
    for k, x in ((0, a), (1, b), (2, c)):
        if x is None:
            continue
        if isinstance(x, (int, float)):
            n.inputs[k].default_value = x
        else:
            nt.links.new(x, n.inputs[k])
    return n.outputs[0]


def _haze_fac(nt):
    """The look's haze (`look.haze`): the air's own, by distance from the camera, 1 - exp(-d / L) for a visibility V
    (L = V / 3.912, Koschmieder), at most `max`: light, as on an overcast day with the far bank still readable; never
    used to hide the ground near the camera."""
    hz = LOOK["haze"]
    L = float(hz["visibility_km"]) * 1000 / 3.912
    d = _node(nt.nodes, "ShaderNodeCameraData").outputs["View Distance"]
    e = _math(nt, "EXPONENT", _math(nt, "MULTIPLY", d, -1.0 / L))
    return _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", 1.0, e), float(hz.get("max", 1.0)))


def _haze_rgb():
    return tuple(LOOK["sky"]["horizon_rgb"]) if LOOK.get("sky") else HAZE_RGB


def _haze(mat, colour_socket, haze_m):
    """Mix a colour into the sky's haze by distance from the camera (the land's box ends; the far land fades)."""
    nt = mat.node_tree
    mix = _node(nt.nodes, "ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["B"].default_value = (*_haze_rgb(), 1.0)
    if LOOK.get("haze"):
        nt.links.new(_haze_fac(nt), mix.inputs["Factor"])
        nt.links.new(colour_socket, mix.inputs["A"])
        return mix.outputs["Result"]
    cam = _node(nt.nodes, "ShaderNodeCameraData")
    ramp = _node(nt.nodes, "ShaderNodeMapRange")
    ramp.inputs["From Min"].default_value, ramp.inputs["From Max"].default_value = haze_m
    ramp.interpolation_type = "SMOOTHSTEP"
    ramp.label = "haze"  # keyed per frame: measured on from what the camera looks at
    nt.links.new(cam.outputs["View Distance"], ramp.inputs["Value"])
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


def _lit_material(name, haze_m, rgb, rough=0.7):
    """The look's lit surfaces (`look.light`): the towers, caissons and plant as diffuse surfaces under the sky's light
    and a soft high sun (Blender lamps, drawn), hazed by distance as the rest."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    bs = _node(nt.nodes, "ShaderNodeBsdfPrincipled")
    if isinstance(rgb, tuple):
        bs.inputs["Base Color"].default_value = (*rgb, 1.0)
    else:
        nt.links.new(rgb(nt), bs.inputs["Base Color"])
    bs.inputs["Roughness"].default_value = rough
    if "Specular IOR Level" in bs.inputs:
        bs.inputs["Specular IOR Level"].default_value = 0.3
    hz = _node(nt.nodes, "ShaderNodeEmission")
    hz.inputs["Color"].default_value = (*_haze_rgb(), 1.0)
    mix = _node(nt.nodes, "ShaderNodeMixShader")
    if LOOK.get("haze"):
        nt.links.new(_haze_fac(nt), mix.inputs["Fac"])
    else:
        mix.inputs["Fac"].default_value = 0.0
    nt.links.new(bs.outputs[0], mix.inputs[1])
    nt.links.new(hz.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return mat


def _wet(nt, colour):
    """The look's wet band (`look.wet`, drawn): the bed just left by the water darker and glossier, drying over the
    following days. Each frame keys the level now and the level `days` before ("wet level", "wet top", without the
    reservoir's hand-over) and how much is shown ("wet amount"); a point between them is wetter the more recently the
    water left it (linear in height between the two levels: an approximation of its time out of the water)."""
    z = _node(nt.nodes, "ShaderNodeSeparateXYZ")
    nt.links.new(_node(nt.nodes, "ShaderNodeNewGeometry").outputs["Position"], z.inputs[0])
    vals = {}
    for k in ("wet top", "wet level", "wet amount"):
        v = _node(nt.nodes, "ShaderNodeValue")
        v.label = k
        vals[k] = v.outputs[0]
    zz = z.outputs["Z"]
    span = _math(nt, "ADD", _math(nt, "SUBTRACT", vals["wet top"], vals["wet level"]), 0.3)
    frac = _math(nt, "DIVIDE", _math(nt, "SUBTRACT", vals["wet top"], zz), span)
    frac = _math(nt, "MINIMUM", _math(nt, "MAXIMUM", frac, 0.0), 1.0)
    near = _math(nt, "GREATER_THAN", zz, _math(nt, "SUBTRACT", vals["wet level"], 0.5))
    wet = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", frac, near), vals["wet amount"])
    k = float(LOOK["wet"].get("darken", 0.45))
    dim = _math(nt, "MULTIPLY_ADD", wet, -k, 1.0)
    sc = _node(nt.nodes, "ShaderNodeVectorMath")
    sc.operation = "SCALE"
    nt.links.new(colour, sc.inputs[0])
    nt.links.new(dim, sc.inputs["Scale"])
    return sc.outputs["Vector"], wet


def _emission_material(name, haze_m, rgb=None, image=None, strength=1.0, after=None, off_rgb=None, unknown_rgb=None,
                       sun=False, glow=False, flow=None, images=None, relief=False, masks=None, pre=None, wet=False):
    if sun and LOOK.get("light", {}).get("lit") and rgb is not None and not glow and flow is None:
        return _lit_material(name, haze_m, tuple(rgb))
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
                if pre is not None:   # the look's pass from just before the breach, dissolved in over the first ("pre breach")
                    tp = _node(nt.nodes, "ShaderNodeTexImage")
                    tp.image = pre
                    tp.extension = "EXTEND"
                    tp.interpolation = "Cubic"
                    mp = _node(nt.nodes, "ShaderNodeMix")
                    mp.data_type = "RGBA"
                    mp.label = "pre breach"
                    mp.inputs["Factor"].default_value = 0.0
                    nt.links.new(colour, mp.inputs["A"])
                    nt.links.new(tp.outputs["Color"], mp.inputs["B"])
                    colour = mp.outputs["Result"]
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
            dots.inputs["B"].default_value = (*_lin(tuple(LOOK.get("cut_gap_rgb", DOT_GAP_RGB))), 1.0)
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
    wetness = None
    if wet and LOOK.get("wet"):
        colour, wetness = _wet(nt, colour)
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
        nt.links.new(em.outputs["Emission"] if wetness is None else _wet_gloss(nt, em.outputs["Emission"], wetness),
                     both.inputs[1])
        nt.links.new(shader, both.inputs[2])
        nt.links.new(both.outputs[0], out.inputs["Surface"])
        return mat
    if wetness is not None:   # the wet band's gloss: the sky reflected by Fresnel, as much as it is wet
        nt.links.new(_wet_gloss(nt, em.outputs["Emission"], wetness), out.inputs["Surface"])
        return mat
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return mat


def _wet_gloss(nt, shader, wetness):
    gl = _node(nt.nodes, "ShaderNodeBsdfGlossy")
    gl.inputs["Roughness"].default_value = 0.15
    fr = _node(nt.nodes, "ShaderNodeFresnel")
    fr.inputs["IOR"].default_value = 1.333
    k = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", fr.outputs[0], wetness), float(LOOK["wet"].get("gloss", 0.6)))
    mx = _node(nt.nodes, "ShaderNodeMixShader")
    nt.links.new(k, mx.inputs["Fac"])
    nt.links.new(shader, mx.inputs[1])
    nt.links.new(gl.outputs[0], mx.inputs[2])
    return mx.outputs[0]


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
        pre = LOOKDOC.get("pre_breach", {}).get("land") if LOOK.get("pre_breach") else None
        PASSES.update(files=[t["file"] for t in ts], pre=pre["file"] if pre else None)
        ob.data.materials.append(_emission_material("land", haze_m, images=[_img(t["file"]) for t in ts],
                                                    relief=True, masks=masks if any(masks) else None,
                                                    pre=_img(pre["file"]) if pre else None, wet=True))
        BED.update(x=xs, y=ys, z=z, u=u, v=v)
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
    BED["south_y0"] = float(ys[0])   # the far plain's frame starts south of the strip (look pass 3)
    pre = LOOKDOC.get("pre_breach", {}).get("south") if LOOK.get("pre_breach") else None
    ob.data.materials.append(_emission_material("land south", haze_m, relief=True,
                                                images=[_img(x["file"]) for x in ls["textures"]],
                                                pre=_img(pre["file"]) if pre else None))
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
    first = _img(sc["terrain"]["textures"][0]["file"])
    mat, body, noise, seen = _water_material(haze_m, first)
    ob = _sheet("reservoir", w["mask"], t["x"] - float(w["pivot_x"]), t["y"], t["u"], t["v"], mat)
    keys = []
    if "sheet_z" in w.files:
        # look pass 3 (`look.water.smooth_edge`): the sheet carried past the water and cut by the shader at each
        # pass's sub-pixel contour (look.water_edge), its own material
        edge = LOOKDOC.get("water_edge") if (LOOK.get("water") or {}).get("smooth_edge") else None
        src = np.load(base / edge["sheet"]) if edge else w
        region = src["sheet_region"]
        smat = _water_material(haze_m, None, edge=edge)[0] if edge else mat
        sh = _sheet("seen", region, t["x"], t["y"], t["u"], t["v"], smat, z=t["z"] - 1.0)
        if edge:   # the water drawn on the land just beyond its edge (lower) mustn't mirror the sheet's rim
            sh.visible_glossy = False
        idx = np.flatnonzero(region.ravel())   # the region's vertices, in the order _sheet keeps them
        sh.shape_key_add(name="hidden", from_mix=False)
        for i, zz in enumerate(src["sheet_z"]):
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


def _water_material(haze_m, first, edge=None):
    """The water's look; its colour the first pass's own pixels while that pass is shown (the reservoir as observed,
    keyed "water seen"), then the passes' measured water colour (keyed "water colour"). With `edge` (look pass 3) the
    surface is cut at the water's sub-pixel contour (`_edge_clip`)."""
    mat = bpy.data.materials.new("water" if edge is None else "water seen")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    shader, body, noise, seen = _water_nodes(nt, haze_m, first)
    if edge is not None:
        shader = _edge_clip(nt, shader, edge)
        mat.surface_render_method = "DITHERED"
    nt.links.new(shader, out.inputs["Surface"])
    return mat, body, noise, seen


def _edge_clip(nt, shader, edge):
    """The river sheet shown only inside the water's contour (look pass 3, look.water_edge): each pass's edge field
    (its river mask softened a little, on the bed's grid, read bilinearly at the point's place) chained by the passes'
    keyed shares ("texture i"; the pre-war pass has no sheet), the surface transparent below 0.5."""
    pos = _node(nt.nodes, "ShaderNodeNewGeometry").outputs["Position"]
    (x0, x1), (y0, y1) = edge["x_m"], edge["y_m"]
    mp = _node(nt.nodes, "ShaderNodeMapping")
    mp.inputs["Location"].default_value = (-x0 / (x1 - x0), -y0 / (y1 - y0), 0.0)
    mp.inputs["Scale"].default_value = (1.0 / (x1 - x0), 1.0 / (y1 - y0), 1.0)
    nt.links.new(pos, mp.inputs["Vector"])
    v0 = _node(nt.nodes, "ShaderNodeValue")
    v0.outputs[0].default_value = 0.0
    chain = v0.outputs[0]
    for i, f in enumerate(edge["files"], start=1):
        tex = _node(nt.nodes, "ShaderNodeTexImage")
        tex.image = bpy.data.images.load(f, check_existing=True)
        tex.image.colorspace_settings.name = "Non-Color"
        tex.extension = "CLIP"
        tex.interpolation = "Linear"
        nt.links.new(mp.outputs["Vector"], tex.inputs["Vector"])
        mix = _node(nt.nodes, "ShaderNodeMix")
        mix.data_type = "FLOAT"
        mix.label = f"texture {i}"
        mix.inputs["Factor"].default_value = 0.0
        nt.links.new(chain, mix.inputs["A"])
        nt.links.new(tex.outputs["Color"], mix.inputs["B"])
        chain = mix.outputs["Result"]
    a = _node(nt.nodes, "ShaderNodeMapRange")
    a.inputs["From Min"].default_value, a.inputs["From Max"].default_value = \
        (LOOK.get("water") or {}).get("smooth_edge", {}).get("band", (0.46, 0.54))
    a.interpolation_type = "SMOOTHSTEP"
    nt.links.new(chain, a.inputs["Value"])
    tr = _node(nt.nodes, "ShaderNodeBsdfTransparent")
    mx = _node(nt.nodes, "ShaderNodeMixShader")
    nt.links.new(a.outputs["Result"], mx.inputs["Fac"])
    nt.links.new(tr.outputs[0], mx.inputs[1])
    nt.links.new(shader, mx.inputs[2])
    return mx.outputs[0]


def _water_nodes(nt, haze_m, first=None, colour=None):
    """The water's shader in a node tree: its colour (an RGB keyed "water colour", or with `first` that pass's
    pixels mixed over it, keyed "water seen"; or a given `colour`, the land's own pixels) as emission, a glossy
    reflection by Fresnel on drawn ripples (keyed "ripples"), hazed by distance as the land. Returns the shader and
    the keyed nodes."""
    body, seen = None, None
    det = (LOOK.get("water") or {}).get("detail")
    if colour is not None and det and first is None:
        # look pass 3: the water drawn on the land (pools, channels, the river where the sheet doesn't reach) takes
        # the same colour as the sheet (the passes' measured water, varied by their own pixels below), so the two meet
        # without a seam; the pass's pixels still give the variation
        colour = None
    if colour is None:
        body = _node(nt.nodes, "ShaderNodeRGB")
        body.label = "water colour"   # keyed: the passes' water, by the frame's textures
        colour = body.outputs[0]
    if first is not None:
        img = _node(nt.nodes, "ShaderNodeTexImage")
        img.image = first
        img.extension = "EXTEND"
        src = img.outputs["Color"]
        pre = LOOKDOC.get("pre_breach", {}).get("land") if LOOK.get("pre_breach") else None
        if pre:   # the reservoir as the pass before the breach saw it, dissolved in with the land ("pre breach")
            tp = _node(nt.nodes, "ShaderNodeTexImage")
            tp.image = _img(pre["file"])
            tp.extension = "EXTEND"
            mp = _node(nt.nodes, "ShaderNodeMix")
            mp.data_type = "RGBA"
            mp.label = "pre breach"
            mp.inputs["Factor"].default_value = 0.0
            nt.links.new(src, mp.inputs["A"])
            nt.links.new(tp.outputs["Color"], mp.inputs["B"])
            src = mp.outputs["Result"]
        seen = _node(nt.nodes, "ShaderNodeMix")
        seen.data_type = "RGBA"
        seen.label = "water seen"
        nt.links.new(colour, seen.inputs["A"])
        # the look's `uniform` water: the passes' measured water colour only (the median of the water's pixels), not
        # the full pass's pixels, which carry the caissons' concrete as pale blots on the water
        nt.links.new(colour if (LOOK.get("water") or {}).get("uniform") else src, seen.inputs["B"])
        colour = seen.outputs["Result"]
    lw = LOOK.get("water") or {}
    if det and LOOKDOC.get("water_variation"):   # look pass 3: the passes' own variation over their water
        colour = _water_var(nt, colour, float(det.get("variation", {}).get("share", 0.8)))
    if lw.get("tint"):   # the look's water a little darker and bluer than the passes' own (drawn, said in scene.json)
        tint = _node(nt.nodes, "ShaderNodeVectorMath")
        tint.operation = "MULTIPLY"
        nt.links.new(colour, tint.inputs[0])
        tint.inputs[1].default_value = tuple(lw["tint"])
        colour = tint.outputs["Vector"]
    if lw.get("shallow_m") and first is not None and BED:   # its depth over the bed: shallow water a drawn bottom tone
        colour = _shallow(nt, colour, float(lw["shallow_m"]), tuple(lw.get("bottom_rgb", (0.05, 0.05, 0.045))))
    if det:
        shader, _, rip, _ = _water_detail(nt, haze_m, colour, lw, det)
        return shader, body, rip, seen
    em = _node(nt.nodes, "ShaderNodeEmission")
    nt.links.new(colour, em.inputs["Color"])
    coords = _node(nt.nodes, "ShaderNodeTexCoord")
    noise = _node(nt.nodes, "ShaderNodeTexNoise")
    noise.noise_dimensions = "4D"
    noise.label = "ripples"       # keyed: W runs with the film's time
    noise.inputs["Scale"].default_value = 1.0 / float(lw.get("ripple_m", RIPPLE_M))
    noise.inputs["Detail"].default_value = float(lw.get("ripple_detail", 6.0))
    noise.inputs["Roughness"].default_value = 0.55
    if lw.get("ripple_stretch"):   # wind ripples: longer across than along (drawn)
        mp = _node(nt.nodes, "ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (1.0, float(lw["ripple_stretch"]), 1.0)
        nt.links.new(coords.outputs["Object"], mp.inputs["Vector"])
        nt.links.new(mp.outputs["Vector"], noise.inputs["Vector"])
    else:
        nt.links.new(coords.outputs["Object"], noise.inputs["Vector"])
    bump = _node(nt.nodes, "ShaderNodeBump")
    bump.inputs["Strength"].default_value = float(lw.get("ripple_bump", RIPPLE_BUMP))
    bump.inputs["Distance"].default_value = 0.5
    if lw.get("ripple_far_m"):   # far off the ripples average out to the surface's roughness (no shimmer)
        far = _node(nt.nodes, "ShaderNodeMapRange")
        far.inputs["From Min"].default_value, far.inputs["From Max"].default_value = lw["ripple_far_m"]
        far.inputs["To Min"].default_value, far.inputs["To Max"].default_value = float(lw.get("ripple_bump", RIPPLE_BUMP)), 0.0
        nt.links.new(_node(nt.nodes, "ShaderNodeCameraData").outputs["View Distance"], far.inputs["Value"])
        nt.links.new(far.outputs["Result"], bump.inputs["Strength"])
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    gl = _node(nt.nodes, "ShaderNodeBsdfGlossy")
    gl.inputs["Roughness"].default_value = float(lw.get("rough", WATER_ROUGH))
    gl.inputs["Color"].default_value = (*tuple(lw.get("reflect_rgb", REFLECT_RGB)), 1.0)
    nt.links.new(bump.outputs["Normal"], gl.inputs["Normal"])
    fr = _node(nt.nodes, "ShaderNodeFresnel")
    fr.inputs["IOR"].default_value = 1.333
    nt.links.new(bump.outputs["Normal"], fr.inputs["Normal"])
    k = _node(nt.nodes, "ShaderNodeMath")
    k.operation = "MULTIPLY"
    k.inputs[1].default_value = float(lw.get("reflect", REFLECT))
    nt.links.new(fr.outputs["Fac"], k.inputs[0])
    mix = _node(nt.nodes, "ShaderNodeMixShader")
    nt.links.new(k.outputs[0], mix.inputs["Fac"])
    nt.links.new(em.outputs["Emission"], mix.inputs[1])
    nt.links.new(gl.outputs["BSDF"], mix.inputs[2])
    hz = _node(nt.nodes, "ShaderNodeEmission")
    hz.inputs["Color"].default_value = (*_haze_rgb(), 1.0)
    fin = _node(nt.nodes, "ShaderNodeMixShader")
    if LOOK.get("haze"):
        nt.links.new(_haze_fac(nt), fin.inputs["Fac"])
    else:
        cam = _node(nt.nodes, "ShaderNodeCameraData")   # hazed by distance, as the land
        ramp = _node(nt.nodes, "ShaderNodeMapRange")
        ramp.inputs["From Min"].default_value, ramp.inputs["From Max"].default_value = haze_m
        ramp.interpolation_type = "SMOOTHSTEP"
        ramp.label = "haze"
        nt.links.new(cam.outputs["View Distance"], ramp.inputs["Value"])
        nt.links.new(ramp.outputs["Result"], fin.inputs["Fac"])
    nt.links.new(mix.outputs[0], fin.inputs[1])
    nt.links.new(hz.outputs["Emission"], fin.inputs[2])
    return fin.outputs[0], body, noise, seen


def _water_var(nt, colour, share):
    """The passes' own colour variation over their water (look pass 3, look.water_variation: each band's ratio to the
    pass's median, 0.5..1.5 stored as 0..1), chained by the passes' keyed shares ("texture i", "pre breach") like the
    land, times the colour: colour · (1 + share · (ratio - 1))."""
    files = LOOKDOC["water_variation"]["files"]
    chain = None
    for i, f in enumerate(PASSES.get("files") or []):
        tex = _node(nt.nodes, "ShaderNodeTexImage")
        if files.get(f):
            tex.image = bpy.data.images.load(files[f], check_existing=True)
            tex.image.colorspace_settings.name = "Non-Color"
        tex.extension = "EXTEND"
        src = tex.outputs["Color"]
        if chain is None:
            chain = src
            pf = PASSES.get("pre")
            if pf and files.get(pf):
                tp = _node(nt.nodes, "ShaderNodeTexImage")
                tp.image = bpy.data.images.load(files[pf], check_existing=True)
                tp.image.colorspace_settings.name = "Non-Color"
                tp.extension = "EXTEND"
                mp = _node(nt.nodes, "ShaderNodeMix")
                mp.data_type = "RGBA"
                mp.label = "pre breach"
                mp.inputs["Factor"].default_value = 0.0
                nt.links.new(chain, mp.inputs["A"])
                nt.links.new(tp.outputs["Color"], mp.inputs["B"])
                chain = mp.outputs["Result"]
            continue
        mix = _node(nt.nodes, "ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.label = f"texture {i}"
        mix.inputs["Factor"].default_value = 0.0
        nt.links.new(chain, mix.inputs["A"])
        nt.links.new(src, mix.inputs["B"])
        chain = mix.outputs["Result"]
    if chain is None:
        return colour
    # 1 + share · (ratio - 1), ratio = stored + 0.5
    k = _node(nt.nodes, "ShaderNodeVectorMath")
    k.operation = "MULTIPLY_ADD"
    nt.links.new(chain, k.inputs[0])
    k.inputs[1].default_value = (share, share, share)
    k.inputs[2].default_value = (1 - 0.5 * share,) * 3
    out = _node(nt.nodes, "ShaderNodeVectorMath")
    out.operation = "MULTIPLY"
    nt.links.new(colour, out.inputs[0])
    nt.links.new(k.outputs["Vector"], out.inputs[1])
    return out.outputs["Vector"]


def _water_detail(nt, haze_m, colour, lw, det):
    """The water's surface drawn in detail (look pass 3, `look.water.detail`; drawn, said in scene.json): in world
    coordinates, so the sheet and the water on the land match. Fine wind ripples (as before), a chop a few metres
    long across the wind, streaks drawn out along the current (`current_deg`, the way it flows, drifting at
    `drift_mps`) where the surface is smoother (slicks) with faint lines of scum along the strongest, and broad
    patches where a gust roughens it (cat's paws); the sky reflected by Fresnel on that surface, rougher in the patches.
    Far off the ripples and chop average out (no shimmer). Returns as _water_nodes."""
    def noise(vec, scale, detail=3.0, rough=0.5, w=None, wscale=0.0):
        n = _node(nt.nodes, "ShaderNodeTexNoise")
        n.noise_dimensions = "4D"
        n.inputs["Scale"].default_value = scale
        n.inputs["Detail"].default_value = detail
        n.inputs["Roughness"].default_value = rough
        nt.links.new(vec, n.inputs["Vector"])
        if w is not None:
            nt.links.new(_math(nt, "MULTIPLY", w, wscale), n.inputs["W"])
        return n
    pos = _node(nt.nodes, "ShaderNodeNewGeometry").outputs["Position"]
    tv = _node(nt.nodes, "ShaderNodeValue")
    tv.label = "water time"   # keyed: the film's seconds
    t = tv.outputs[0]
    sep = _node(nt.nodes, "ShaderNodeSeparateXYZ")
    nt.links.new(pos, sep.inputs[0])
    a = math.radians(float(det.get("current_deg", 255.0)))
    ux, uy = math.sin(a), math.cos(a)   # the way the current flows (east, north)
    along = _math(nt, "ADD", _math(nt, "MULTIPLY", sep.outputs["X"], ux), _math(nt, "MULTIPLY", sep.outputs["Y"], uy))
    across = _math(nt, "SUBTRACT", _math(nt, "MULTIPLY", sep.outputs["Y"], ux), _math(nt, "MULTIPLY", sep.outputs["X"], uy))
    drift = float(det.get("drift_mps", 0.6))
    sl, sw = det.get("streak_m", (70.0, 5.0))
    sv = _node(nt.nodes, "ShaderNodeCombineXYZ")   # streaks: long along the current, drifting with it
    nt.links.new(_math(nt, "DIVIDE", _math(nt, "SUBTRACT", along, _math(nt, "MULTIPLY", t, drift)), float(sl)), sv.inputs[0])
    nt.links.new(_math(nt, "DIVIDE", across, float(sw)), sv.inputs[1])
    sn = noise(sv.outputs[0], 1.0, 2.0, 0.5, t, 0.02)
    lo, hi = det.get("streak_band", (0.52, 0.68))
    streak = _node(nt.nodes, "ShaderNodeMapRange")
    streak.inputs["From Min"].default_value, streak.inputs["From Max"].default_value = lo, hi
    streak.interpolation_type = "SMOOTHSTEP"
    nt.links.new(sn.outputs["Fac"], streak.inputs["Value"])
    st = streak.outputs["Result"]
    pv = _node(nt.nodes, "ShaderNodeCombineXYZ")   # gusts: broad patches, slowly changing
    nt.links.new(_math(nt, "DIVIDE", sep.outputs["X"], float(det.get("patch_m", 160.0))), pv.inputs[0])
    nt.links.new(_math(nt, "DIVIDE", sep.outputs["Y"], float(det.get("patch_m", 160.0))), pv.inputs[1])
    pn = noise(pv.outputs[0], 1.0, 2.0, 0.55, t, 0.03)
    patch = _node(nt.nodes, "ShaderNodeMapRange")
    patch.inputs["From Min"].default_value, patch.inputs["From Max"].default_value = 0.35, 0.7
    patch.interpolation_type = "SMOOTHSTEP"
    nt.links.new(pn.outputs["Fac"], patch.inputs["Value"])
    pt = patch.outputs["Result"]
    # the surface's height: fine ripples and a chop across the wind, weaker on the slicks, stronger in the gusts
    rv = _node(nt.nodes, "ShaderNodeMapping")
    rv.inputs["Scale"].default_value = (1.0, float(lw.get("ripple_stretch", 4.0)), 1.0)
    nt.links.new(pos, rv.inputs["Vector"])
    rip = noise(rv.outputs["Vector"], 1.0 / float(lw.get("ripple_m", RIPPLE_M)), 4.0, 0.55, t, 0.15)
    cv = _node(nt.nodes, "ShaderNodeMapping")
    cm = float(det.get("chop_m", 12.0))
    cv.inputs["Scale"].default_value = (1.0 / cm, 3.0 / cm, 1.0)
    nt.links.new(pos, cv.inputs["Vector"])
    chop = noise(cv.outputs["Vector"], 1.0, 2.0, 0.5, t, 0.08)
    camd = _node(nt.nodes, "ShaderNodeCameraData").outputs["View Distance"]
    def fade(r0, r1):
        f = _node(nt.nodes, "ShaderNodeMapRange")
        f.inputs["From Min"].default_value, f.inputs["From Max"].default_value = r0, r1
        f.inputs["To Min"].default_value, f.inputs["To Max"].default_value = 1.0, 0.0
        nt.links.new(camd, f.inputs["Value"])
        return f.outputs["Result"]
    rf, cf = lw.get("ripple_far_m", (300.0, 2500.0)), det.get("chop_far_m", (900.0, 5000.0))
    calm = _math(nt, "MULTIPLY_ADD", st, -0.7, 1.0)   # the slicks smoother
    gust = _math(nt, "MULTIPLY_ADD", pt, 0.8, 0.6)    # the gusts rougher
    k = _math(nt, "MULTIPLY", calm, gust)
    hgt = _math(nt, "ADD", _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", rip.outputs["Fac"], fade(*rf)),
                                 float(lw.get("ripple_bump", RIPPLE_BUMP))),
                _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", chop.outputs["Fac"], fade(*cf)), float(det.get("chop_bump", 0.25))))
    bump = _node(nt.nodes, "ShaderNodeBump")
    bump.inputs["Distance"].default_value = 0.5
    up = _node(nt.nodes, "ShaderNodeCombineXYZ")   # water lies level: on a bank's slope too (the water drawn on the land)
    up.inputs["Z"].default_value = 1.0
    nt.links.new(up.outputs[0], bump.inputs["Normal"])
    nt.links.new(k, bump.inputs["Strength"])
    nt.links.new(hgt, bump.inputs["Height"])
    # the colour: the passes' own, a little lighter along the strongest streaks (scum lines, drawn)
    lines = _math(nt, "MULTIPLY", _math(nt, "POWER", st, 3.0), float(det.get("scum", 0.08)))
    sc = _node(nt.nodes, "ShaderNodeVectorMath")
    sc.operation = "SCALE"
    nt.links.new(colour, sc.inputs[0])
    nt.links.new(_math(nt, "ADD", lines, 1.0), sc.inputs["Scale"])
    em = _node(nt.nodes, "ShaderNodeEmission")
    nt.links.new(sc.outputs["Vector"], em.inputs["Color"])
    gl = _node(nt.nodes, "ShaderNodeBsdfGlossy")
    r0, r1 = det.get("rough", (0.015, 0.08))
    rough = _math(nt, "MULTIPLY", _math(nt, "ADD", _math(nt, "MULTIPLY", pt, r1 - r0), r0), calm)
    nt.links.new(rough, gl.inputs["Roughness"])
    gl.inputs["Color"].default_value = (*tuple(lw.get("reflect_rgb", REFLECT_RGB)), 1.0)
    nt.links.new(bump.outputs["Normal"], gl.inputs["Normal"])
    fr = _node(nt.nodes, "ShaderNodeFresnel")
    fr.inputs["IOR"].default_value = 1.333
    nt.links.new(bump.outputs["Normal"], fr.inputs["Normal"])
    kk = _math(nt, "MULTIPLY", fr.outputs["Fac"], float(lw.get("reflect", REFLECT)))
    mix = _node(nt.nodes, "ShaderNodeMixShader")
    nt.links.new(kk, mix.inputs["Fac"])
    nt.links.new(em.outputs["Emission"], mix.inputs[1])
    nt.links.new(gl.outputs["BSDF"], mix.inputs[2])
    hz = _node(nt.nodes, "ShaderNodeEmission")
    hz.inputs["Color"].default_value = (*_haze_rgb(), 1.0)
    fin = _node(nt.nodes, "ShaderNodeMixShader")
    nt.links.new(_haze_fac(nt), fin.inputs["Fac"])
    nt.links.new(mix.outputs[0], fin.inputs[1])
    nt.links.new(hz.outputs["Emission"], fin.inputs[2])
    return fin.outputs[0], None, rip, None


def _bed_image():
    """The land's heights (terrain.npz, the bed inside the reservoir) as a float image on its grid, made once."""
    if "image" not in BED:
        z = np.asarray(BED["z"], np.float32)
        ny, nx = z.shape
        im = bpy.data.images.new("bed heights", nx, ny, alpha=False, float_buffer=True)
        im.colorspace_settings.name = "Non-Color"
        px = np.zeros((ny, nx, 4), np.float32)
        px[..., 0] = px[..., 1] = px[..., 2] = z
        px[..., 3] = 1.0
        im.pixels.foreach_set(px.ravel())
        im.pack()
        BED["image"] = im
    return BED["image"]


def _shallow(nt, colour, shallow_m, bottom):
    """The water's colour by its depth over the bed (look.water.shallow_m): a drawn, neutral bottom tone at the shore
    turning into the water's own colour by `shallow_m` deep, so the edge reads as a shoreline on the bed. Never a later
    pass's pixels under the water."""
    xs, ys = BED["x"], BED["y"]
    step = float(xs[1] - xs[0])
    pos = _node(nt.nodes, "ShaderNodeNewGeometry").outputs["Position"]
    mp = _node(nt.nodes, "ShaderNodeMapping")
    mp.inputs["Location"].default_value = ((-float(xs[0]) + step / 2) / (len(xs) * step),
                                           (-float(ys[0]) + step / 2) / (len(ys) * step), 0.0)
    mp.inputs["Scale"].default_value = (1.0 / (len(xs) * step), 1.0 / (len(ys) * step), 1.0)
    nt.links.new(pos, mp.inputs["Vector"])
    tex = _node(nt.nodes, "ShaderNodeTexImage")
    tex.image = _bed_image()
    tex.extension = "EXTEND"
    tex.interpolation = "Linear"
    nt.links.new(mp.outputs["Vector"], tex.inputs["Vector"])
    sep = _node(nt.nodes, "ShaderNodeSeparateXYZ")
    nt.links.new(pos, sep.inputs[0])
    sc = _node(nt.nodes, "ShaderNodeSeparateColor")
    nt.links.new(tex.outputs["Color"], sc.inputs[0])
    depth = _math(nt, "SUBTRACT", sep.outputs["Z"], sc.outputs[0])
    t = _node(nt.nodes, "ShaderNodeMapRange")
    t.inputs["From Min"].default_value, t.inputs["From Max"].default_value = 0.0, shallow_m
    t.interpolation_type = "SMOOTHSTEP"
    nt.links.new(depth, t.inputs["Value"])
    mix = _node(nt.nodes, "ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (*bottom, 1.0)
    nt.links.new(t.outputs["Result"], mix.inputs["Factor"])
    nt.links.new(colour, mix.inputs["B"])
    return mix.outputs["Result"]


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
    # the look's `detail` (look pass 2): the same towers, attachment points and wires with more members and finer
    # fittings (towers_detail.npz, towers.build_types(detail=True))
    detail = LOOKDOC.get("detail") if LOOK.get("detail") else None
    npz = np.load(base / (detail["file"] if detail else tdoc["file"]))
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
                ob = bpy.data.objects.new(f"{t['caisson']} {t['osm_node']}", _caisson_mesh(meshes, t["caisson"]))
                ob.location = (t["xy"][0], t["xy"][1], t["ground_m"])
                bpy.context.scene.collection.objects.link(ob)
    _line_wires(sc["lines"], npz, tdoc, mats, haze_m, camera, flow)


CAISSON_MATS = {}


def _caisson_mesh(meshes, kind):
    """A caisson's mesh; with the look's `caisson`, a copy in its own concrete (grey, darker where it is wet and in a
    band at the water's line, keyed by the frame's level: drawn, said in scene.json)."""
    lc = LOOK.get("caisson")
    if not lc:
        return meshes[kind]
    key = f"{kind} look"
    if key not in meshes:
        me = meshes[kind].copy()
        if not CAISSON_MATS:
            for idx, base in ((3, lc["concrete_rgb"]), (8, lc["stained_rgb"])):   # towers.CONCRETE, towers.STAINED
                CAISSON_MATS[idx] = _lit_material(f"caisson {idx}", None, _caisson_colour(tuple(base), lc), rough=0.85) \
                    if LOOK.get("light", {}).get("lit") else _emission_material(f"caisson {idx}", None, rgb=tuple(base), sun=True)
        for i, m in enumerate(me.materials):
            for idx, cm in CAISSON_MATS.items():
                if m == MESHES["_mats"][idx]:
                    me.materials[i] = cm
        meshes[key] = me
    return meshes[key]


def _caisson_colour(base, lc):
    """The concrete's colour by height against the frame's level ("water level", keyed): darker below it (wet) and in
    a band just above it (the water's line, `band_m`), as concrete in a river is."""
    def make(nt):
        z = _node(nt.nodes, "ShaderNodeSeparateXYZ")
        nt.links.new(_node(nt.nodes, "ShaderNodeNewGeometry").outputs["Position"], z.inputs[0])
        lv = _node(nt.nodes, "ShaderNodeValue")
        lv.label = "water level"
        h = _math(nt, "SUBTRACT", z.outputs["Z"], lv.outputs[0])
        band = _node(nt.nodes, "ShaderNodeMapRange")   # 1 at and under the line, 0 `band_m` over it
        band.inputs["From Min"].default_value, band.inputs["From Max"].default_value = 0.0, float(lc.get("band_m", 0.8))
        band.inputs["To Min"].default_value, band.inputs["To Max"].default_value = 1.0, 0.0
        band.interpolation_type = "SMOOTHSTEP"
        nt.links.new(h, band.inputs["Value"])
        k = _math(nt, "MULTIPLY_ADD", band.outputs["Result"], -float(lc.get("band_darken", 0.45)), 1.0)
        sc = _node(nt.nodes, "ShaderNodeVectorMath")
        sc.operation = "SCALE"
        sc.inputs[0].default_value = base
        nt.links.new(k, sc.inputs["Scale"])
        return sc.outputs["Vector"]
    return make


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

        off = _lin(tuple(LOOK["cut_rgb"])) if LOOK.get("cut_rgb") else OFF_RGB.get(kv, (0.5, 0.1, 0.1))
        state = dict(rgb=WIRE_RGB.get(kv, (1, 1, 1)), off_rgb=off,
                     unknown_rgb=off if LOOK.get("cut_rgb") else UNKNOWN_RGB.get(kv, (0.5, 0.5, 0.5)))
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


def _plant_material(haze_m):
    """The plants' one material (look pass 2): each face's own colour (`col`, the models' leaf and bark colours) shaded
    by the fixed sun as the towers were (a stem 0.35 facing away to 1.0 facing it; a thin leaf card from either side),
    each plant a little lighter or darker (its instance's random), times the look's `gain`; hazed by distance as the
    rest. Unlit and shadowless like the land: the plants cast no shadows."""
    lv = LOOK["vegetation"]
    mat = bpy.data.materials.new("plants")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    col, card = _node(nt.nodes, "ShaderNodeAttribute"), _node(nt.nodes, "ShaderNodeAttribute")
    col.attribute_name, card.attribute_name = "col", "card"
    dot = _node(nt.nodes, "ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    dot.inputs[1].default_value = SUN
    nt.links.new(_node(nt.nodes, "ShaderNodeNewGeometry").outputs["Normal"], dot.inputs[0])
    stem = _math(nt, "MULTIPLY_ADD", dot.outputs["Value"], 0.325, 0.675)
    leaf = _math(nt, "MULTIPLY_ADD", _math(nt, "ABSOLUTE", dot.outputs["Value"]), 0.32, 0.68)
    mx = _node(nt.nodes, "ShaderNodeMix")
    mx.data_type = "FLOAT"
    nt.links.new(card.outputs["Fac"], mx.inputs["Factor"])
    nt.links.new(stem, mx.inputs["A"])
    nt.links.new(leaf, mx.inputs["B"])
    rnd = _math(nt, "MULTIPLY_ADD", _node(nt.nodes, "ShaderNodeObjectInfo").outputs["Random"], 0.26, 0.87)
    k = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", mx.outputs["Result"], rnd), float(lv.get("gain", 1.0)))
    leaf_col = col.outputs["Color"]
    if lv.get("tone"):   # look pass 3: toned to the ground under each plant (drawn, said in scene.json)
        leaf_col, ao = _plant_tone(nt, leaf_col, lv["tone"])
        k = _math(nt, "MULTIPLY", k, ao)
    sc_ = _node(nt.nodes, "ShaderNodeVectorMath")
    sc_.operation = "SCALE"
    nt.links.new(leaf_col, sc_.inputs[0])
    nt.links.new(k, sc_.inputs["Scale"])
    em = _node(nt.nodes, "ShaderNodeEmission")
    nt.links.new(_haze(mat, sc_.outputs["Vector"], haze_m), em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return mat


def _plant_tone(nt, col, to):
    """The plants' colour toned to where they stand (look pass 3, `look.vegetation.tone`; the user: bright green
    flecks on the pale sand): each model's own colour less saturated (`sat`), pulled toward the pass's colour on the
    ground under the plant (`pull`, darkened by `ground_k`: the same keyed passes as the land, read at the plant's
    place, its instance attribute `guv`), toward late-summer olive or dry straw by a broad noise over the plants'
    places (clumps of tone, `olive_rgb`, `dry_rgb`), and darker at its foot (`ao`: by each vertex's share of its
    model's height, `hrel`), so it sits on the ground. Returns the colour and the foot's darkening."""
    lum = _node(nt.nodes, "ShaderNodeVectorMath")
    lum.operation = "DOT_PRODUCT"
    nt.links.new(col, lum.inputs[0])
    lum.inputs[1].default_value = (0.2126, 0.7152, 0.0722)
    sat = float(to.get("sat", 0.55))
    grey = _node(nt.nodes, "ShaderNodeCombineXYZ")
    for j in range(3):
        nt.links.new(lum.outputs["Value"], grey.inputs[j])
    ds = _node(nt.nodes, "ShaderNodeMix")   # less saturated
    ds.data_type = "RGBA"
    ds.inputs["Factor"].default_value = sat
    nt.links.new(grey.outputs[0], ds.inputs["A"])
    nt.links.new(col, ds.inputs["B"])
    guv = _node(nt.nodes, "ShaderNodeAttribute")
    guv.attribute_type, guv.attribute_name = "INSTANCER", "guv"
    ground = None
    for i, f in enumerate(PASSES.get("files") or []):
        tex = _node(nt.nodes, "ShaderNodeTexImage")
        tex.image = _img(f)
        tex.extension = "EXTEND"
        nt.links.new(guv.outputs["Vector"], tex.inputs["Vector"])
        if ground is None:
            ground = tex.outputs["Color"]
            if PASSES.get("pre"):
                tp = _node(nt.nodes, "ShaderNodeTexImage")
                tp.image = _img(PASSES["pre"])
                tp.extension = "EXTEND"
                nt.links.new(guv.outputs["Vector"], tp.inputs["Vector"])
                mp = _node(nt.nodes, "ShaderNodeMix")
                mp.data_type = "RGBA"
                mp.label = "pre breach"
                mp.inputs["Factor"].default_value = 0.0
                nt.links.new(ground, mp.inputs["A"])
                nt.links.new(tp.outputs["Color"], mp.inputs["B"])
                ground = mp.outputs["Result"]
            continue
        mix = _node(nt.nodes, "ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.label = f"texture {i}"
        mix.inputs["Factor"].default_value = 0.0
        nt.links.new(ground, mix.inputs["A"])
        nt.links.new(tex.outputs["Color"], mix.inputs["B"])
        ground = mix.outputs["Result"]
    c = ds.outputs["Result"]
    if ground is not None:
        gk = _node(nt.nodes, "ShaderNodeVectorMath")
        gk.operation = "SCALE"
        nt.links.new(ground, gk.inputs[0])
        gk.inputs["Scale"].default_value = float(to.get("ground_k", 0.85))
        pm = _node(nt.nodes, "ShaderNodeMix")
        pm.data_type = "RGBA"
        pm.inputs["Factor"].default_value = float(to.get("pull", 0.4))
        nt.links.new(c, pm.inputs["A"])
        nt.links.new(gk.outputs["Vector"], pm.inputs["B"])
        c = pm.outputs["Result"]
    nv = _node(nt.nodes, "ShaderNodeVectorMath")   # clumps of tone: a broad noise over the plants' places
    nv.operation = "SCALE"
    nt.links.new(guv.outputs["Vector"], nv.inputs[0])
    nv.inputs["Scale"].default_value = 40000.0 / float(to.get("clump_m", 60.0))
    n = _node(nt.nodes, "ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = 1.0
    n.inputs["Detail"].default_value = 1.5
    nt.links.new(nv.outputs["Vector"], n.inputs["Vector"])
    band = _node(nt.nodes, "ShaderNodeMapRange")
    band.inputs["From Min"].default_value, band.inputs["From Max"].default_value = 0.35, 0.65
    band.interpolation_type = "SMOOTHSTEP"
    nt.links.new(n.outputs["Fac"], band.inputs["Value"])
    tint = _node(nt.nodes, "ShaderNodeMix")
    tint.data_type = "RGBA"
    tint.inputs["A"].default_value = (*to.get("olive_rgb", (0.92, 0.95, 0.72)), 1.0)
    tint.inputs["B"].default_value = (*to.get("dry_rgb", (1.08, 1.0, 0.72)), 1.0)
    nt.links.new(band.outputs["Result"], tint.inputs["Factor"])
    tm = _node(nt.nodes, "ShaderNodeVectorMath")
    tm.operation = "MULTIPLY"
    nt.links.new(c, tm.inputs[0])
    nt.links.new(tint.outputs["Result"], tm.inputs[1])
    hrel = _node(nt.nodes, "ShaderNodeAttribute")
    hrel.attribute_type, hrel.attribute_name = "GEOMETRY", "hrel"
    a0, h1 = to.get("ao", (0.5, 0.3))
    ao = _node(nt.nodes, "ShaderNodeMapRange")
    ao.inputs["From Min"].default_value, ao.inputs["From Max"].default_value = 0.0, float(h1)
    ao.inputs["To Min"].default_value, ao.inputs["To Max"].default_value = float(a0), 1.0
    ao.interpolation_type = "SMOOTHSTEP"
    nt.links.new(hrel.outputs["Fac"], ao.inputs["Value"])
    return tm.outputs["Vector"], ao.outputs["Result"]


def vegetation(sc, base, haze_m, camera):
    """The look's vegetation (look pass 2; vegetation.py, scene.json `look.<variant>.vegetation`): the prototypes'
    meshes in a collection of their own, instanced on vegetation.npz's points by geometry nodes. Per frame: each plant's
    size by the date shown (keyed "veg day", days from the dam's destruction: trees by the sources' growth curve from
    their cohort, the rest over their first season, faded in before the pass they first show on; bank trees always),
    its level of detail by its distance from the camera (LOD 1 near, 2 mid, 3 far, each threshold jittered per plant so
    the changes don't sweep as rings), thinned beyond `thin_m`, and left out behind the camera, past its family's
    `far`, or while too small to see. Returns the keyed day."""
    lv, vd = LOOK["vegetation"], LOOKDOC["vegetation"]
    z = np.load(base / vd["file"])
    mat = _plant_material(haze_m)
    protos = bpy.data.collections.new("plant prototypes")
    nv, nf = z["proto_nv"], z["proto_nf"]
    ov, of = np.concatenate([[0], np.cumsum(nv)]), np.concatenate([[0], np.cumsum(nf)])
    for i in range(len(nv)):
        V = z["proto_v"][ov[i]:ov[i + 1]]
        F = z["proto_f"][of[i]:of[i + 1]]
        me = bpy.data.meshes.new(f"plant {i:03d}")
        me.vertices.add(len(V))
        me.vertices.foreach_set("co", V.ravel())
        me.loops.add(F.size)
        me.loops.foreach_set("vertex_index", F.ravel())
        me.polygons.add(len(F))
        me.polygons.foreach_set("loop_start", (np.arange(len(F)) * 3).astype(np.int32))
        me.polygons.foreach_set("loop_total", np.full(len(F), 3, np.int32))
        me.update(calc_edges=True)
        a = me.attributes.new("col", "FLOAT_COLOR", "FACE")
        a.data.foreach_set("color", np.column_stack([z["proto_c"][of[i]:of[i + 1]], np.ones(len(F))]).astype(np.float32).ravel())
        b = me.attributes.new("card", "FLOAT", "FACE")
        b.data.foreach_set("value", z["proto_k"][of[i]:of[i + 1]])
        if lv.get("tone"):   # look pass 3: each vertex's share of its model's height (its foot darker)
            hr = me.attributes.new("hrel", "FLOAT", "POINT")
            hr.data.foreach_set("value", np.clip(V[:, 2] / max(float(V[:, 2].max()), 1e-3), 0, 1).astype(np.float32))
        me.materials.append(mat)
        ob = bpy.data.objects.new(f"plant {i:03d}", me)
        ob.visible_shadow = False
        protos.objects.link(ob)
    P = z["pts"]
    me = bpy.data.meshes.new("vegetation")
    me.vertices.add(len(P))
    me.vertices.foreach_set("co", P[:, :3].ravel())
    names = ("rot", "hf", "shift", "show", "kind", "far", "rnd")
    for j, key in enumerate(names, start=3):
        a = me.attributes.new(key, "FLOAT", "POINT")
        a.data.foreach_set("value", P[:, j].astype(np.float32))
    for key in ("idx", "nlod"):
        a = me.attributes.new(key, "INT", "POINT")
        a.data.foreach_set("value", z[key].astype(np.int32))
    if lv.get("tone") and "u" in BED:   # look pass 3: where each plant stands on the passes' images (u, v linear in x, y)
        xs_, ys_ = np.asarray(BED["x"], float), np.asarray(BED["y"], float)
        ku = np.polyfit(xs_, np.asarray(BED["u"], float)[0, :], 1)
        kv = np.polyfit(ys_, np.asarray(BED["v"], float)[:, 0], 1)
        g = me.attributes.new("guv", "FLOAT_VECTOR", "POINT")
        g.data.foreach_set("vector", np.column_stack([np.polyval(ku, P[:, 0]), np.polyval(kv, P[:, 1]),
                                                      np.zeros(len(P))]).astype(np.float32).ravel())
    ob = bpy.data.objects.new("vegetation", me)
    ob.visible_shadow = False
    bpy.context.scene.collection.objects.link(ob)

    ng = bpy.data.node_groups.new("vegetation", "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    n, L = ng.nodes, ng.links.new
    gi, go = n.new("NodeGroupInput"), n.new("NodeGroupOutput")

    def attr(key, typ="FLOAT"):
        a = n.new("GeometryNodeInputNamedAttribute")
        a.data_type = typ
        a.inputs["Name"].default_value = key
        return a.outputs["Attribute"]

    def m(op, a, b=None, c=None):
        return _math(ng, op, a, b, c)

    def maprange(v, a, b, lo=0.0, hi=1.0, smooth=False):
        r = n.new("ShaderNodeMapRange")
        r.data_type = "FLOAT"
        if smooth:
            r.interpolation_type = "SMOOTHSTEP"
        for k, x in (("Value", v), ("From Min", a), ("From Max", b), ("To Min", lo), ("To Max", hi)):
            if isinstance(x, (int, float)):
                r.inputs[k].default_value = x
            else:
                L(x, r.inputs[k])
        return r.outputs["Result"]

    day = n.new("ShaderNodeValue")
    day.label = "veg day"
    t = day.outputs[0]
    # the growth: trees by the curve from their cohort (shift), the rest over their season, faded in before their pass
    curve = n.new("ShaderNodeFloatCurve")
    cm = curve.mapping
    gmax = max(g for _, g in vd["growth"]["trees"]) * 1.02
    span = float(vd.get("growth_span", 1300.0))
    pts_ = cm.curves[0].points
    want = [(d / span, g / gmax) for d, g in vd["growth"]["trees"]]
    while len(pts_) < len(want):
        pts_.new(0.5, 0.5)
    for p, (x, y) in zip(pts_, want):
        p.location = (x, y)
        p.handle_type = "VECTOR"   # straight between the sources' heights (interpolated, said so)
    cm.update()
    curve.inputs["Factor"].default_value = 1.0
    L(maprange(m("SUBTRACT", t, attr("shift")), 0.0, span), curve.inputs["Value"])
    tree = m("MULTIPLY", curve.outputs["Value"], gmax)
    season = maprange(m("SUBTRACT", t, attr("shift")), 0.0, float(vd["growth"]["season_days"]), 0.15, 1.0, True)
    appear = maprange(t, attr("show"), m("ADD", attr("show"), float(vd["growth"]["appear_days"])), 0.0, 1.0, True)
    kind = attr("kind")
    is0 = m("LESS_THAN", kind, 0.5)
    is1 = m("MULTIPLY", m("GREATER_THAN", kind, 0.5), m("LESS_THAN", kind, 1.5))
    is2 = m("GREATER_THAN", kind, 1.5)
    grow = m("ADD", m("ADD", m("MULTIPLY", is0, tree), m("MULTIPLY", is1, season)), is2)
    scale = m("MULTIPLY", m("MULTIPLY", attr("hf"), grow), m("MAXIMUM", appear, is2))
    if (lv.get("tone") or {}).get("clump_size"):   # look pass 3: shrubs and reeds taller or lower in clumps (drawn)
        cn = n.new("ShaderNodeTexNoise")
        cn.inputs["Scale"].default_value = 1.0 / float(lv["tone"].get("clump_m", 60.0))
        L(n.new("GeometryNodeInputPosition").outputs[0], cn.inputs["Vector"])
        amp = float(lv["tone"]["clump_size"])
        var = m("MULTIPLY_ADD", m("SUBTRACT", cn.outputs["Fac"], 0.5), 2.0 * amp, 1.0)
        scale = m("MULTIPLY", scale, m("ADD", m("MULTIPLY", is1, m("SUBTRACT", var, 1.0)), 1.0))
    # the camera: distance, and whether in front of it
    cam = n.new("GeometryNodeObjectInfo")
    cam.inputs["Object"].default_value = camera
    pos = n.new("GeometryNodeInputPosition").outputs[0]
    dv = n.new("ShaderNodeVectorMath")
    dv.operation = "SUBTRACT"
    L(pos, dv.inputs[0])
    L(cam.outputs["Location"], dv.inputs[1])
    dist = n.new("ShaderNodeVectorMath")
    dist.operation = "LENGTH"
    L(dv.outputs[0], dist.inputs[0])
    d = dist.outputs["Value"]
    rnd = attr("rnd")
    gone = m("GREATER_THAN", d, attr("far"))
    gone = m("MAXIMUM", gone, m("LESS_THAN", scale, float(lv.get("min_scale", 0.03))))
    tn = lv.get("thin_m", [1500.0, 4500.0, 0.35])
    gone = m("MAXIMUM", gone, m("GREATER_THAN", rnd, maprange(d, tn[0], tn[1], 1.0, tn[2])))
    try:   # behind the camera or well outside its view (a cone 53° round its axis, beyond 80 m)
        fwd = n.new("FunctionNodeRotateVector")
        fwd.inputs["Vector"].default_value = (0.0, 0.0, -1.0)
        L(cam.outputs["Rotation"], fwd.inputs["Rotation"])
        nrm = n.new("ShaderNodeVectorMath")
        nrm.operation = "NORMALIZE"
        L(dv.outputs[0], nrm.inputs[0])
        dt = n.new("ShaderNodeVectorMath")
        dt.operation = "DOT_PRODUCT"
        L(nrm.outputs[0], dt.inputs[0])
        L(fwd.outputs[0], dt.inputs[1])
        out_of_view = m("MULTIPLY", m("LESS_THAN", dt.outputs["Value"], float(lv.get("cone_cos", 0.6))),
                        m("GREATER_THAN", d, 80.0))
        gone = m("MAXIMUM", gone, out_of_view)
    except (RuntimeError, KeyError) as e:
        print("vegetation: no view culling:", e)
    dele = n.new("GeometryNodeDeleteGeometry")
    dele.domain = "POINT"
    L(gi.outputs[0], dele.inputs["Geometry"])
    L(gone, dele.inputs["Selection"])
    lods = lv.get("lod_m", [350.0, 1200.0])
    jit = m("MULTIPLY_ADD", rnd, 0.3, 0.85)
    sel = m("ADD", m("GREATER_THAN", d, m("MULTIPLY", jit, float(lods[0]))),
            m("GREATER_THAN", d, m("MULTIPLY", jit, float(lods[1]))))
    slot = m("MINIMUM", sel, m("SUBTRACT", attr("nlod", "INT"), 1.0))
    ci = n.new("GeometryNodeCollectionInfo")
    ci.inputs["Collection"].default_value = protos
    ci.inputs["Separate Children"].default_value = True
    ci.inputs["Reset Children"].default_value = True
    iop = n.new("GeometryNodeInstanceOnPoints")
    iop.inputs["Pick Instance"].default_value = True
    L(dele.outputs[0], iop.inputs["Points"])
    L(ci.outputs[0], iop.inputs["Instance"])
    L(m("ADD", attr("idx", "INT"), slot), iop.inputs["Instance Index"])
    rot = n.new("ShaderNodeCombineXYZ")
    L(attr("rot"), rot.inputs["Z"])
    L(rot.outputs[0], iop.inputs["Rotation"])
    L(scale, iop.inputs["Scale"])
    L(iop.outputs[0], go.inputs[0])
    ob.modifiers.new("vegetation", "NODES").node_group = ng
    return day


def sky(world):
    """The look's sky (`look.sky`, drawn, said in scene.json): an overcast grey, lighter toward the horizon, with a soft,
    low-contrast cloud deck (noise on a plane `height_m` up, seen in perspective) drifting slowly; under the horizon
    the horizon's grey. Its light is the scene's ambient light. Returns the keyed mapping (the deck's offset)."""
    ls = LOOK["sky"]
    nt = world.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_WORLD":
            nt.nodes.remove(n)
    out = next(n for n in nt.nodes if n.type == "OUTPUT_WORLD")
    d = _node(nt.nodes, "ShaderNodeTexCoord").outputs["Generated"]   # the view direction
    sep = _node(nt.nodes, "ShaderNodeSeparateXYZ")
    nt.links.new(d, sep.inputs[0])
    up = _math(nt, "MAXIMUM", sep.outputs["Z"], 0.02)
    k = _math(nt, "DIVIDE", float(ls.get("height_m", 1500.0)), up)
    xy = _node(nt.nodes, "ShaderNodeCombineXYZ")
    nt.links.new(_math(nt, "MULTIPLY", sep.outputs["X"], k), xy.inputs[0])
    nt.links.new(_math(nt, "MULTIPLY", sep.outputs["Y"], k), xy.inputs[1])
    mp = _node(nt.nodes, "ShaderNodeMapping")
    mp.label = "cloud offset"   # keyed: the camera's place and the drift
    nt.links.new(xy.outputs[0], mp.inputs["Vector"])
    noise = _node(nt.nodes, "ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 1.0 / float(ls.get("cloud_m", 3000.0))
    noise.inputs["Detail"].default_value = float(ls.get("detail", 2.5))
    noise.inputs["Roughness"].default_value = 0.55
    nt.links.new(mp.outputs["Vector"], noise.inputs["Vector"])
    soft = _node(nt.nodes, "ShaderNodeMapRange")
    soft.inputs["From Min"].default_value, soft.inputs["From Max"].default_value = ls.get("cloud_range", (0.3, 0.75))
    soft.interpolation_type = "SMOOTHSTEP"
    nt.links.new(noise.outputs["Fac"], soft.inputs["Value"])
    cl = _node(nt.nodes, "ShaderNodeMix")
    cl.data_type = "RGBA"
    cl.inputs["A"].default_value = (*ls["cloud_dark_rgb"], 1.0)
    cl.inputs["B"].default_value = (*ls["cloud_light_rgb"], 1.0)
    nt.links.new(soft.outputs["Result"], cl.inputs["Factor"])
    hz = _node(nt.nodes, "ShaderNodeMapRange")   # toward the horizon the deck thins into the horizon's grey
    hz.inputs["From Min"].default_value, hz.inputs["From Max"].default_value = ls.get("horizon_band", (0.0, 0.35))
    hz.interpolation_type = "SMOOTHSTEP"
    nt.links.new(sep.outputs["Z"], hz.inputs["Value"])
    mix = _node(nt.nodes, "ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (*ls["horizon_rgb"], 1.0)
    nt.links.new(hz.outputs["Result"], mix.inputs["Factor"])
    nt.links.new(cl.outputs["Result"], mix.inputs["B"])
    bg = _node(nt.nodes, "ShaderNodeBackground")
    bg.inputs["Strength"].default_value = float(ls.get("strength", 1.0))
    nt.links.new(mix.outputs["Result"], bg.inputs["Color"])
    nt.links.new(bg.outputs[0], out.inputs["Surface"])
    return mp


def far_plain(sc, haze_m):
    """The look's ground beyond the land's box (`look.far_plain`, drawn): a flat plain in the land's mean colour a few
    metres under the lowest land, so the light haze ends on ground at the horizon, not on the box's edge."""
    fp = LOOK["far_plain"]
    r = float(fp.get("size_m", 150000.0))
    me = bpy.data.meshes.new("far plain")
    z = float(fp.get("z_m", 8.0))
    if fp.get("hole") and "x" in BED:
        # look pass 3: only beyond the land (the drained bed lies under the plain's `z_m`, which covered it as a flat
        # sheet in look passes 1-2): a frame round the land's box (and the strip south of it), set in by `inset_m`
        t = BED
        ins = float(fp.get("inset_m", 60.0))
        x0, x1 = float(t["x"][0]) + ins, float(t["x"][-1]) - ins
        y0, y1 = float(BED.get("south_y0", t["y"][0])) + ins, float(t["y"][-1]) - ins
        v = [(-r, -r, z), (r, -r, z), (r, r, z), (-r, r, z), (x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)]
        me.from_pydata(v, [], [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])
    else:
        me.from_pydata([(-r, -r, z), (r, -r, z), (r, r, z), (-r, r, z)], [], [(0, 1, 2, 3)])
    ob = bpy.data.objects.new("far plain", me)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(_emission_material("far plain", haze_m, rgb=tuple(fp["rgb"])))
    return ob


def main():
    scene_path, cam_path, out, rng, blend, render, stills, keep = _args()
    sc = json.loads(scene_path.read_text())
    cam = json.loads(cam_path.read_text())
    base = scene_path.parent
    LOOK.update(cam.get("look") or {})
    LOOKDOC.update((sc.get("look") or {}).get(cam.get("variant"), {}))
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
    vegday = vegetation(sc, base, haze_m, co) if LOOK.get("vegetation") and LOOKDOC.get("vegetation") else None

    world = s.world or bpy.data.worlds.new("World")
    s.world = world
    world.use_nodes = True
    clouds = None
    if LOOK.get("sky"):
        clouds = sky(world)
    else:
        bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
        bg.inputs["Color"].default_value = (*HAZE_RGB, 1.0)
        bg.inputs["Strength"].default_value = 1.0
    if LOOK.get("far_plain"):
        far_plain(sc, haze_m)
    ll = LOOK.get("light") or {}
    if ll.get("lit"):   # a soft, high sun (drawn): the sky's light does the rest
        ld = bpy.data.lights.new("sun", "SUN")
        ld.energy = float(ll.get("sun_strength", 1.0))
        ld.angle = math.radians(float(ll.get("sun_angle_deg", 20.0)))
        ld.color = tuple(ll.get("sun_rgb", (1.0, 0.97, 0.92)))
        sun = bpy.data.objects.new("sun", ld)
        el, az = (math.radians(float(x)) for x in ll.get("sun_deg", (55.0, 150.0)))   # elevation, azimuth from north
        sun.rotation_euler = (math.pi / 2 - el, 0.0, math.pi - az)
        s.collection.objects.link(sun)
    probe = None
    if (LOOK.get("water") or {}).get("planar") and wat:   # crisp reflections of the towers and wires on the water
        pd = bpy.data.lightprobes.new("water mirror", "PLANE")
        pd.influence_distance = 1.5
        probe = bpy.data.objects.new("water mirror", pd)
        probe.scale = (20000.0, 20000.0, 1.0)
        s.collection.objects.link(probe)

    frames = cam["frames"]
    hazes = [n for m in bpy.data.materials if m.node_tree for n in m.node_tree.nodes if n.label == "haze"]
    drains = [n for m in bpy.data.materials if m.node_tree for n in m.node_tree.nodes if n.label == "drain"]
    bodies = [n for m in bpy.data.materials if m.node_tree for n in m.node_tree.nodes if n.label == "water colour"]
    ripples = [n for m in bpy.data.materials if m.node_tree for n in m.node_tree.nodes if n.label == "ripples"]
    layers = sorted(((int(n.label.split()[1]), n) for m in bpy.data.materials if m.node_tree
                     for n in m.node_tree.nodes if n.label.startswith("texture ")), key=lambda x: x[0])
    pres = [n for m in bpy.data.materials if m.node_tree for n in m.node_tree.nodes if n.label == "pre breach"]
    wets = [n for m in bpy.data.materials if m.node_tree for n in m.node_tree.nodes
            if n.label in ("wet top", "wet level", "wet amount", "water level")]
    wtimes = [n for m in bpy.data.materials if m.node_tree for n in m.node_tree.nodes if n.label == "water time"]
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
        for n in wtimes:   # look pass 3: the water's drawn surface moves with the film's time
            n.outputs[0].default_value = (i - 1) / cam["fps"]
            n.outputs[0].keyframe_insert("default_value", frame=i)
        for m in pres:   # the look's pass before the breach, by its share
            m.inputs["Factor"].default_value = float(f.get("pre_breach", 0.0))
            m.inputs["Factor"].keyframe_insert("default_value", frame=i)
        if wets and f.get("wet"):
            top, lvl, amount = f["wet"]
            for n in wets:
                n.outputs[0].default_value = {"wet top": top, "wet level": lvl, "wet amount": amount,
                                              "water level": lvl}[n.label]
                n.outputs[0].keyframe_insert("default_value", frame=i)
        if vegday is not None:   # the plants' growth by the date shown
            vegday.outputs[0].default_value = float(f.get("veg_day", -1000.0))
            vegday.outputs[0].keyframe_insert("default_value", frame=i)
        if clouds is not None:   # the deck seen from where the camera is, drifting
            ls = LOOK["sky"]
            drift = float(ls.get("drift_mps", 2.0)) * (i - 1) / cam["fps"]
            clouds.inputs["Location"].default_value = (f["location"][0] + drift, f["location"][1], 0.0)
            clouds.inputs["Location"].keyframe_insert("default_value", frame=i)
        if probe is not None and f.get("level_m") is not None:
            probe.location = (8000.0, 8000.0, (f.get("wet") or [0, f["level_m"]])[1])
            probe.keyframe_insert("location", frame=i)
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
        s.eevee.taa_render_samples = int(LOOK.get("samples", 16))
        if wat:   # the water's reflections of the towers and wires: screen-space rays (what is on screen)
            s.eevee.use_raytracing = True
            s.eevee.ray_tracing_method = "SCREEN"
            s.eevee.ray_tracing_options.resolution_scale = str(LOOK.get("ray_scale", "2"))   # half: the ripples break them up
            s.eevee.ray_tracing_options.trace_max_roughness = 0.3
            rt = LOOK.get("rays") or {}   # look pass 3: thinner screen-trace hits (no false hits on the sheet's edge)
            for k, x in (("thickness", "screen_trace_thickness"), ("quality", "screen_trace_quality")):
                if k in rt:
                    setattr(s.eevee.ray_tracing_options, x, float(rt[k]))
            if "backface" in rt:
                s.eevee.ray_tracing_options.use_backface_hit = bool(rt["backface"])
        if ll.get("lit"):
            s.eevee.use_shadows = bool(ll.get("shadows", True))
    if LOOK.get("motion_blur"):   # the look's motion blur: the shutter open this share of a frame
        s.render.use_motion_blur = True
        s.render.motion_blur_shutter = float(LOOK["motion_blur"])
    grade = LOOK.get("grade") or {}
    try:  # the imagery's colours as they are (a dynamic enum: RNA lists no items, so set it and see)
        s.view_settings.view_transform = grade.get("view", "Standard")
        if grade.get("look"):
            s.view_settings.look = grade["look"]
        s.view_settings.exposure = float(grade.get("exposure", 0.0))
    except TypeError as e:
        print("view transform left as it was:", e)
    if LOOK.get("bloom"):   # a soft bloom on what glows (the lit wires), Blender's compositor
        b = LOOK["bloom"]
        ng = bpy.data.node_groups.new("look", "CompositorNodeTree")
        ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
        rl = ng.nodes.new("CompositorNodeRLayers")
        gl = ng.nodes.new("CompositorNodeGlare")
        gl.inputs["Type"].default_value = "Bloom"
        for k, x in (("Threshold", "threshold"), ("Strength", "strength"), ("Size", "size"), ("Smoothness", "smoothness")):
            if x in b:
                gl.inputs[k].default_value = b[x]
        go = ng.nodes.new("NodeGroupOutput")
        ng.links.new(rl.outputs["Image"], gl.inputs["Image"])
        ng.links.new(gl.outputs["Image"], go.inputs[0])
        s.compositing_node_group = ng
        s.render.use_compositing = True
    s.render.image_settings.file_format = "PNG"
    out.mkdir(parents=True, exist_ok=True)
    s.render.filepath = str(out / "f_")
    if blend:
        bpy.context.preferences.filepaths.save_version = 0   # no .blend1: one scene file per segment, replaced each build
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    if render and stills:
        for k in stills:
            s.frame_set(k)
            s.render.filepath = str(out / f"f_{k:04d}")
            bpy.ops.render.render(write_still=True)
    elif render:
        if keep:   # resume: frames already written are left as they are
            s.render.use_overwrite = False
        bpy.ops.render.render(animation=True)


main()
