"""S1 film pass: a block of the land on one dated pass: heights as the 3D scene's land (FABDEM, the drained bed
inferred), the pass's own pixels (u, v into its rgb.webp) and its water (bed.channels' rule, sampled nearest).
Usage: prep3f.py OUT.npz X0 X1 Y0 Y1 PASS_DIR   (metres on the scene's plane, the plant at 0, 0)"""
import json, sys
from pathlib import Path

import numpy as np

D = Path("libraries/conductive-seam/satellite/networks/znpp/scenes/crossing3d")
t = np.load(D / "terrain.npz"); X, Y, Z = t["x"], t["y"], t["z"]
bed = np.load(D / "bed" / "bed.npz"); BJ = json.loads((D / "bed" / "bed.json").read_text())
PL = json.loads((D / "scene.json").read_text())["plane"]
X0, X1, Y0, Y1 = map(float, sys.argv[2:6]); PD = Path(sys.argv[6])
P = json.loads((PD / "pass.json").read_text()); M = np.load(PD / "masks.npz")
ix = np.where((X >= X0) & (X <= X1))[0]; iy = np.where((Y >= Y0) & (Y <= Y1))[0]
xs, ys = X[ix], Y[iy]
z = Z[np.ix_(iy, ix)].astype(np.float32)
gx, gy = np.meshgrid(xs, ys)
lon = PL["lon0"] + gx / PL["kx"]; lat = PL["lat0"] + gy / PL["kz"]
w, s_, e, n = P["grid"]["bbox"]; H, W = M["water"].shape
u = (lon - w) / (e - w); v = (lat - s_) / (n - s_)            # into the pass's image (v up, as Blender's UVs)
col = np.clip((u * W).astype(int), 0, W - 1); row = np.clip(((1 - v) * H).astype(int), 0, H - 1)
water = M["water"][row, col]
g = BJ["grid"]
c = ((lon - g["bbox"][0]) * g["kx"] / g["m_per_px"]).astype(int); r = ((g["bbox"][3] - lat) * g["kz"] / g["m_per_px"]).astype(int)
ok = (c >= 0) & (c < g["width"]) & (r >= 0) & (r < g["height"])
inferred = np.zeros(z.shape, bool); inferred[ok] = bed["footprint"][r[ok], c[ok]]
pond = (np.abs(z - 15.0) < 0.05) & (gx > -5600) & (gx < -800) & (gy > -1800) & (gy < 2000)   # inside the dike (FABDEM's flat 15.0)
slope = BJ["river_slope"]["m_per_deg_lon"]; at_lon = BJ["river_slope"]["at_lon"]
np.savez_compressed(sys.argv[1], x=xs, y=ys, z=z, u=u.astype(np.float32), v=v.astype(np.float32), pond=pond,
                    inferred=inferred, water=water, river_off=(slope * (lon - at_lon)).astype(np.float32))
print(Path(sys.argv[1]).name, z.shape, "water in pond", round(float(water[pond].mean()), 3), "water outside", round(float(water[~pond].mean()), 3))
