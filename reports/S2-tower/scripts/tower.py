"""S2 test: the 750 kV crossing tower (suspension, 126 m) on its caisson, as modelled for the 3D film (towers.npz),
alone in an empty space, for stills and a slow turntable behind text. Not the film.
blender -b --factory-startup -P tower.py -- TOWERS_NPZ SCENE_JSON VIEW OUT [FRAMES SECONDS]
VIEW: monument | elevation | head | foot      (FRAMES > 1: a turntable, OUT a folder of PNGs)"""
import json, math, sys

import bpy
import numpy as np
from mathutils import Euler, Vector

a = sys.argv[sys.argv.index("--") + 1:]
T = np.load(a[0]); SC = json.load(open(a[1])); VIEW, OUT = a[2], a[3]
FRAMES = int(a[4]) if len(a) > 4 else 1
SECONDS = float(a[5]) if len(a) > 5 else 10.0
DEG_PER_S = 3.6      # a full turn in 100 s: slow enough to read text over
s = bpy.context.scene
for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)


def material(name, rgb, metal=0.0, rough=0.75, emit=None):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Metallic"].default_value = metal
    b.inputs["Roughness"].default_value = rough
    if emit is not None:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = 1.0
    return m


FLAT = VIEW == "elevation"   # an elevation drawing: every member one flat grey, no light
mats = []
for k in range(len(SC["towers"]["materials"])):
    name, rgb = SC["towers"]["materials"][str(k)]
    if FLAT:
        mats.append(material(name, (0, 0, 0), emit=(0.55, 0.55, 0.55)))
    else:
        mats.append(material(name, tuple(rgb), metal=0.35 if k in (0, 6) else 0.0, rough=0.6 if k in (0, 6) else 0.8))


def mesh(ty):
    v, loops, counts, mat = T[f"{ty}__v"], T[f"{ty}__loops"], T[f"{ty}__counts"], T[f"{ty}__mat"]
    me = bpy.data.meshes.new(ty)
    me.vertices.add(len(v)); me.vertices.foreach_set("co", v.ravel())
    me.loops.add(len(loops)); me.loops.foreach_set("vertex_index", loops)
    me.polygons.add(len(counts))
    me.polygons.foreach_set("loop_start", np.concatenate([[0], np.cumsum(counts)[:-1]]).astype(np.int32))
    me.polygons.foreach_set("loop_total", counts)
    me.update(calc_edges=True); me.validate()
    for m in mats:
        me.materials.append(m)
    me.polygons.foreach_set("material_index", mat.astype(np.int32))
    return me


# one pivot turns the tower and its caisson together; z 0 is the caisson's base (12.8 m below the old water)
pivot = bpy.data.objects.new("pivot", None); s.collection.objects.link(pivot)
up = SC["towers"]["water_up_m"]; down = 12.8
cais = bpy.data.objects.new("caisson", mesh("caisson750")); cais.location = (0, 0, down); cais.parent = pivot
tow = bpy.data.objects.new("tower", mesh("crossing750_p")); tow.location = (0, 0, down + up); tow.parent = pivot
for o in (cais, tow):
    s.collection.objects.link(o)
# the scale figure: a plain drawn person, 1.75 m, at the caisson's foot (said to be one)
fig = material("figure", (0, 0, 0), emit=(0.8, 0.8, 0.8))
bpy.ops.mesh.primitive_cylinder_add(radius=0.22, depth=1.45, location=(23.5, -6.0, 0.725))
body = bpy.context.object; body.data.materials.append(fig)
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.13, location=(23.5, -6.0, 1.62))
head = bpy.context.object; head.data.materials.append(fig)
for o in (body, head):
    o.parent = pivot

# light: a low key from the front left, a cold rim from behind, a dim fill; the world near black
def light(name, kind, energy, loc, rot, size=None, rgb=(1, 1, 1)):
    L = bpy.data.lights.new(name, kind); L.energy = energy; L.color = rgb
    if size and kind == "AREA":
        L.size = size
    if kind == "SUN":
        L.angle = math.radians(1.5)
    o = bpy.data.objects.new(name, L); o.location = loc; o.rotation_euler = Euler([math.radians(r) for r in rot])
    s.collection.objects.link(o)
    return o


def spot(name, power, loc, at, size, rgb):
    L = bpy.data.lights.new(name, "SPOT"); L.energy = power; L.color = rgb
    L.spot_size = math.radians(size); L.spot_blend = 0.7; L.shadow_soft_size = 2.0
    o = bpy.data.objects.new(name, L); o.location = loc
    o.rotation_euler = (Vector(at) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    s.collection.objects.link(o)


if not FLAT:   # a studio: one warm key pooling on a dark floor, a cold rim behind, the rest falling away to black
    spot("key", 5.5e6, (-210, -240, 250), (0, 0, 55), 44, (1.0, 0.93, 0.84))
    spot("rim", 4.0e6, (170, 280, 190), (0, 0, 70), 40, (0.70, 0.82, 1.0))
    light("fill", "SUN", 0.12, (0, 0, 0), (40, 0, 60))
    fl = material("floor", (0.010, 0.010, 0.011), rough=0.32)
    bpy.ops.mesh.primitive_plane_add(size=4000, location=(0, 0, 0)); bpy.context.object.data.materials.append(fl)
s.world = bpy.data.worlds.new("w"); s.world.use_nodes = True
bg = next(n for n in s.world.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs["Color"].default_value = (0, 0, 0, 1); bg.inputs["Strength"].default_value = 1.0

cam = bpy.data.cameras.new("cam"); co = bpy.data.objects.new("cam", cam); s.collection.objects.link(co); s.camera = co
cam.clip_end = 5000
H = down + up + 126.0
if VIEW == "monument":      # long lens from far off, a little below the head: near-parallel verticals
    cam.lens = 85; cam.shift_x = -0.24
    co.location = (0, -780, H / 2 + 4); co.rotation_euler = Euler((math.radians(90), 0, 0))
    pivot.rotation_euler = (0, 0, math.radians(-28))
elif VIEW == "elevation":   # orthographic, side on to the line: the crossarms' width
    cam.type = "ORTHO"; cam.ortho_scale = 290; cam.shift_x = -0.24
    co.location = (0, -500, H / 2 + 2); co.rotation_euler = Euler((math.radians(90), 0, 0))
elif VIEW == "head":        # the head: crossarms, glass strings, yokes
    cam.lens = 135; cam.dof.use_dof = False
    co.location = (-62, -150, 103); co.rotation_euler = Euler((math.radians(97), 0, math.radians(-22)))
    pivot.rotation_euler = (0, 0, math.radians(-15))
elif VIEW == "foot":        # from the bed, past the figure, up the caisson and the legs
    cam.lens = 20
    eye = Vector((46, -52, 1.5)); co.location = eye
    co.rotation_euler = (Vector((0, 0, 34)) - eye).to_track_quat("-Z", "Y").to_euler()
    pivot.rotation_euler = (0, 0, math.radians(-10))
    fwd = Vector((-46, 52, 0)).normalized(); right = Vector((fwd.y, -fwd.x, 0))
    p = eye + fwd * 16 + right * 3.2
    for o in (body, head):   # the figure stands in the foreground, on the bed
        o.parent = None; o.location = (p.x, p.y, o.location.z)

s.render.resolution_x, s.render.resolution_y = 1920, 1080
try:
    s.render.engine = "BLENDER_EEVEE"
except TypeError:
    pass
if hasattr(s, "eevee"):
    s.eevee.taa_render_samples = 64
    s.eevee.use_raytracing = True   # the floor's reflection
    s.eevee.ray_tracing_method = "SCREEN"
try:
    s.view_settings.view_transform = "Standard"
except TypeError:
    pass
if FRAMES <= 1:
    s.render.filepath = OUT
    bpy.ops.render.render(write_still=True)
else:
    s.render.fps = 30; s.frame_start, s.frame_end = 1, FRAMES
    r0 = pivot.rotation_euler.z
    for f in (1, FRAMES):   # linear: a turntable at one even speed
        pivot.rotation_euler.z = r0 + math.radians(DEG_PER_S * (f - 1) / 30)
        pivot.keyframe_insert("rotation_euler", index=2, frame=f)
    for fc in pivot.animation_data.action.fcurves if hasattr(pivot.animation_data.action, "fcurves") else []:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
    s.render.filepath = OUT.rstrip("/") + "/f_"
    bpy.ops.render.render(animation=True)
print("H", H)
