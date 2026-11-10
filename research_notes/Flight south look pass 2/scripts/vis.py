"""How many plants pass the GN culling at given frames, by distance band (mirrors build.vegetation)."""
import json, sys, math
import numpy as np
from image_evidence.satellite.scene3d import vegetation as V
B = "libraries/conductive-seam/satellite/networks/znpp/scenes/crossing3d"
c = json.load(open(f"{B}/camera_south_look2.json")); lv = c["look"]["vegetation"]
z = np.load(f"{B}/vegetation.npz"); P = z["pts"]
x, y, zz, rot, hf, shift, show, kind, far, rnd = P.T
for fr in [int(a) for a in sys.argv[1].split(",")]:
    f = c["frames"][fr - 1]; t = f["veg_day"]; L = np.array(f["location"]); rx, _, rz = f["rotation"]
    fwd = np.array([-math.sin(rz) * math.sin(rx), math.cos(rz) * math.sin(rx), -math.cos(rx)])
    tree = V.growth_at(np.clip(t - shift, 0, 1300)) 
    season = np.clip((t - shift) / 120, 0, 1); season = 0.15 + 0.85 * season * season * (3 - 2 * season)
    ap = np.clip((t - show) / 40, 0, 1); ap = ap * ap * (3 - 2 * ap)
    grow = np.where(kind < .5, tree, np.where(kind < 1.5, season, 1.0))
    sc = hf * grow * np.where(kind > 1.5, 1.0, ap)
    dv = P[:, :3] - L; d = np.linalg.norm(dv, axis=1); dot = (dv / d[:, None]) @ fwd
    thin = np.interp(d, [lv["thin_m"][0], lv["thin_m"][1]], [1, lv["thin_m"][2]])
    keep = (d <= far) & (sc >= lv["min_scale"]) & (rnd <= thin) & ~((dot < lv["cone_cos"]) & (d > 80))
    H = sc * 6.5
    bands = [0, 165, 400, 1200, 2500, 4500]
    s = " ".join(f"{a}-{b}:{((d>=a)&(d<b)&keep).sum()}" for a, b in zip(bands, bands[1:]))
    print(f"frame {fr} {f['date']} day {t:.0f} cam {L.round(0)} kept {keep.sum()} | {s} | median scale kept {np.median(sc[keep]) if keep.any() else 0:.2f} kinds {np.bincount(kind[keep].astype(int), minlength=3)}")
