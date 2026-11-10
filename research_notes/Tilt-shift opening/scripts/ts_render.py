"""Runs inside Blender after the crossing's build.py (`-P build.py -P ts_render.py`, build.py given `--no-render`): the
scene as build.py made it from the camera json, rendered at the size asked, each frame twice: the picture (build.py's
own settings: EEVEE, the look's samples, bloom, AgX) and the distance from the camera to what each pixel shows (every
material swapped for one that emits that distance, the sky transparent), for the tilt-shift laid on afterwards.

Options by environment (build.py owns the arguments after `--`):
    TS_OUT      folder for f_####.png (picture) and d_####.npy (distance, metres, float32; inf where sky; EEVEE
                passes it through a half-float buffer, so past 65,504 m it comes back clamped there)
    TS_FRAMES   "a,b,c" or "a-b" (1-based, the camera json's frames)
    TS_SIZE     "1920x1080"
    TS_DEPTH    "1" (default) to render the distance too
"""

import os
from pathlib import Path

import bpy
import numpy as np

out = Path(os.environ["TS_OUT"])
out.mkdir(parents=True, exist_ok=True)
spec = os.environ["TS_FRAMES"]
if "-" in spec:
    a, b = (int(x) for x in spec.split("-"))
    frames = list(range(a, b + 1))
else:
    frames = [int(x) for x in spec.split(",")]
w, h = (int(x) for x in os.environ.get("TS_SIZE", "1920x1080").split("x"))
depth = os.environ.get("TS_DEPTH", "1") == "1"

s = bpy.context.scene
s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage = w, h, 100
s.render.image_settings.file_format = "PNG"

todo = [k for k in frames if not (out / f"f_{k:04d}.png").exists()]
for k in todo:
    s.frame_set(k)
    s.render.filepath = str(out / f"f_{k:04d}")
    bpy.ops.render.render(write_still=True)

if depth:
    mat = bpy.data.materials.new("distance")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    cam = nt.nodes.new("ShaderNodeCameraData")
    em = nt.nodes.new("ShaderNodeEmission")
    mo = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(cam.outputs["View Distance"], em.inputs["Color"])
    nt.links.new(em.outputs[0], mo.inputs["Surface"])
    vl = bpy.context.view_layer
    vl.material_override = mat
    s.render.film_transparent = True
    s.render.use_compositing = False
    s.render.use_motion_blur = False
    if hasattr(s, "eevee"):
        s.eevee.taa_render_samples = 1   # no averaging across an edge: each pixel one surface's distance
        s.eevee.use_raytracing = False
    s.render.image_settings.file_format = "OPEN_EXR"
    s.render.image_settings.color_depth = "32"
    s.view_settings.view_transform = "Standard"
    s.view_settings.look = "None"
    s.view_settings.exposure = 0.0
    for k in frames:
        npy = out / f"d_{k:04d}.npy"
        if npy.exists():
            continue
        s.frame_set(k)
        exr = out / f"d_{k:04d}.exr"
        s.render.filepath = str(exr)
        bpy.ops.render.render(write_still=True)
        im = bpy.data.images.load(str(exr))
        px = np.empty(im.size[0] * im.size[1] * im.channels, np.float32)
        im.pixels.foreach_get(px)
        px = px.reshape(im.size[1], im.size[0], im.channels)[::-1]   # Blender's rows run bottom up
        d = px[..., 0].copy()
        d[px[..., 3] < 0.5] = np.inf
        np.save(npy, d)
        bpy.data.images.remove(im)
        exr.unlink()
