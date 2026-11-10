"""Section block pass 2: the 2D section's pieces (profile2.py's drawing through cutlib.py) at any exaggeration, many in
one Blender session. Each job: a piece (dike, 0 Dniprovska, 1 Ferosplavna), a day, ex_g (ground, water), ex_t (towers,
sag), the frame (its width in m, the point along the piece in its middle, the world height in its middle), a png and its
labels' json (profile2.py's keys). With ex_g = ex_t = 10 and profile2's frames it redraws the S1 sections.
blender -b --factory-startup -P profile3.py -- JOBS.json XF_DIR SCENE_DIR
JOBS.json: [{"piece", "state", "ex_g", "ex_t", "ortho", "s_centre", "zc", "png", "json", "res": 100}, ...]"""
import json, sys
from pathlib import Path

import bpy
import numpy as np
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).parent))
import cutlib as C  # noqa: E402

a = sys.argv[sys.argv.index("--") + 1:]
JOBS, XF, SD = json.loads(Path(a[0]).read_text()), Path(a[1]), Path(a[2])
s = bpy.context.scene
C.render_setup(s)
s.render.resolution_x, s.render.resolution_y = 1920, 1080
cam = bpy.data.cameras.new("cam"); co = bpy.data.objects.new("cam", cam); s.collection.objects.link(co); s.camera = co
cam.type = "ORTHO"; cam.clip_end = 50000
lands, mats = {}, C.line_mats()


def clear():
    for ob in list(s.collection.objects):
        if ob is not co:
            bpy.data.objects.remove(ob, do_unlink=True)
    for me in list(bpy.data.meshes):
        if me.users == 0 and me not in C._tmesh.values():
            bpy.data.meshes.remove(me)
    for cu in list(bpy.data.curves):
        if cu.users == 0:
            bpy.data.curves.remove(cu)


for job in JOBS:
    clear()
    k = job["state"]
    if k not in lands:
        lands[k] = C.Land(XF, k, SD)
    land = lands[k]; piece = job["piece"]; exg, ext = float(job["ex_g"]), float(job["ex_t"])
    ortho = float(job["ortho"]); px = ortho / 1920
    fo, p = C.face(land, piece, exg, px)
    tops = []
    if piece != "dike":
        tw, cs, cv, tops = C.lines(land, int(piece), exg, ext, px, C.near_cut(piece), mats)
    P0, U, N, L, S = p["P0"], p["U"], p["N"], p["L"], p["S"]
    mid = P0 + U * float(job["s_centre"])
    cam.ortho_scale = ortho
    d = Vector((N[0], N[1], 0.0))
    co.location = Vector((mid[0], mid[1], float(job["zc"]))) + d * 8000
    co.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    s.render.resolution_percentage = int(job.get("res", 100))
    s.render.filepath = job["png"]
    bpy.ops.render.render(write_still=True)

    def onscreen(q):
        r = world_to_camera_view(s, co, Vector(q)); return [r.x * 1920, (1 - r.y) * 1080]

    def Pw(si, h):
        xy = P0 + si * U; return (xy[0], xy[1], h * exg)

    g, lv, wet, pd = p["g"], p["lv"], p["wet"], p["pd"]
    ST = land.ST; lab = {}
    at = lambda si: land.at(*(P0 + si * U), land.E["z64"])
    if piece == "dike":
        sp = S[pd]; lab["COOLING POND"] = onscreen(Pw(float(sp.mean()), land.pond_lv + 1.5))
        ok = (S > 1300) & (S < 1900); jd = int(np.argmax(np.where(ok, g, -99)))
        lab["DIKE"] = onscreen(Pw(S[jd], g[jd] + 1))
        nb = (S > 2000) & wet & ~pd
        if nb.any():
            jr = int(np.argmin(np.where(nb, g, 99))); lab["RESERVOIR" if ST["flat"] else "CHANNEL"] = onscreen(Pw(S[jr], lv[jr] + 1))
        if not ST["flat"]:
            lab["DRAINED BED"] = onscreen(Pw(2600, at(2600) + 1))
        lab["_pond"] = [onscreen(Pw(float(sp.min()), 0))[0], onscreen(Pw(float(sp.max()), 0))[0]]
    else:
        lab["ENERHODAR BANK"] = onscreen(Pw(-300, at(-300) + 2))
        lab["NIKOPOL BANK"] = onscreen(Pw(L + 250, at(L + 250) + 2))
        jr = int(np.argmin(np.where(wet, g, 99)))
        lab["RESERVOIR" if ST["flat"] else "RIVER"] = onscreen(Pw(S[jr], max(lv[jr], g[jr]) + 1))
        nm = ("DNIPROVSKA · 750 KV: CUT", "FEROSPLAVNA 1, 2 · 330 KV: CUT")[int(piece)]
        if tops:
            x, y, zt = tops[len(tops) // 2]
            lab[nm] = onscreen((x, y, zt + 6 * ext))
    lab["_x"] = [onscreen(Pw(float(S[0]), 0))[0], onscreen(Pw(float(S[-1]), 0))[0]]
    lab["_y"] = {str(h): onscreen(Pw(0, h))[1] for h in (0, 10, 20)}
    lab["_px"] = px; lab["_ex"] = exg; lab["_ex_t"] = ext; lab["_ends"] = [list(map(float, P0)), list(map(float, P0 + L * U))]
    json.dump(lab, open(job["json"], "w"))
print("profile3: rendered", len(JOBS))
