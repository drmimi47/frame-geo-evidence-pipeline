import bpy, time
s = bpy.context.scene
bpy.data.objects["water mirror"].hide_render = True
s.eevee.use_shadows = False
s.eevee.ray_tracing_options.resolution_scale = "1"
def r(tag, frame):
    s.frame_set(frame)
    s.render.filepath = f"/private/tmp/claude-501/-Users-patrickrodriguez-dev-sandbox-frame-geo-evidence-pipeline/1a0b7111-211b-446e-85aa-40a4418b76a9/scratchpad/look/tim/{tag}_{frame}"
    t = time.time(); bpy.ops.render.render(write_still=True); print("TIME", tag, frame, round(time.time() - t, 2), flush=True)
r("warm", 841)
s.render.use_motion_blur = True
for sp in (16, 32, 64):
    s.eevee.taa_render_samples = sp
    r(f"s{sp}", 842 + sp); r(f"s{sp}", 843 + sp)
r("s64_land", 2251); r("s64_plant", 3601)
