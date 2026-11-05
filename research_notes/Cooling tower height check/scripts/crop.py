import sys, json, httpx, numpy as np
sys.path.insert(0, "src")
from image_evidence.satellite import providers as p
s2 = p.SENSORS["sentinel-2"]
out = sys.argv[1]
bbox = (34.555, 47.497, 34.640, 47.532)
W, H = 639, 389
ids = sys.argv[2:]
with httpx.Client() as h:
    for i in ids:
        arr, rec = p.crop(s2, i, ("B04", "B08", "B11"), bbox, W, H, "nearest", h)
        np.save(f"{out}/{i[11:19]}.npy", arr)
        print(i, arr.shape, rec["sha256"][:12])
