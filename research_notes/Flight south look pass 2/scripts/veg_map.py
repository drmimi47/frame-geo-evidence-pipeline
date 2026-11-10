import json, sys
import numpy as np
from PIL import Image, ImageDraw
Z = "/Users/patrickrodriguez/dev/sandbox/frame-geo-evidence-pipeline/libraries/conductive-seam/satellite/networks/znpp"
out = sys.argv[1]
v = np.load(f"{Z}/scenes/crossing3d/vegetation.npz")
P, fam = v["pts"], v["fam"]
pl = json.load(open(f"{Z}/scenes/crossing3d/scene.json"))["plane"]
g = json.load(open(f"{Z}/imagery/c3d_2025_08.json"))["grid"]
im = Image.open(f"{Z}/imagery/c3d_2025_08/rgb.webp").convert("RGB")
w, s, e, n = g["bbox"]
def px(x, y):
    lon, lat = pl["lon0"] + x / pl["kx"], pl["lat0"] + y / pl["kz"]
    return (lon - w) / (e - w) * g["width"], (n - lat) / (n - s) * g["height"]
cam = json.load(open(f"{Z}/scenes/crossing3d/camera_south_look1.json"))["frames"]
T = np.array([f["location"][:2] for f in cam])
c, r = px(P[:, 0], P[:, 1])
tc, tr = px(T[:, 0], T[:, 1])
x0, x1, y0, y1 = int(tc.min()) - 450, int(tc.max()) + 450, int(tr.min()) - 350, int(tr.max()) + 300
crop = im.crop((x0, y0, x1, y1)).resize(((x1 - x0) * 2, (y1 - y0) * 2))
d = ImageDraw.Draw(crop)
cols = {0: (255, 255, 0), 1: (255, 128, 0), 2: (0, 255, 255), 3: (255, 0, 255), 4: (255, 0, 255), 5: (60, 120, 255), 6: (60, 120, 255)}
sel = (c > x0) & (c < x1) & (r > y0) & (r < y1)
rng = np.random.default_rng(0)
idx = np.flatnonzero(sel)
idx = idx[rng.random(len(idx)) < 0.25]
for i in idx:
    xx, yy = (c[i] - x0) * 2, (r[i] - y0) * 2
    col = (255, 255, 255) if P[i, 7] > 1.5 else cols[int(fam[i])]
    d.point((xx, yy), fill=col)
d.line(list(zip((tc - x0) * 2, (tr - y0) * 2)), fill=(255, 0, 0), width=2)
crop.save(out, quality=88)
print(crop.size, len(idx))
