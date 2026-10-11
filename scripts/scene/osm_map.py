# Scene Viewer, step 4 (optional): the Route Map's street map laid over the land, so the river and roads it draws
# (OpenStreetMap: today's map, after the reservoir drained) show on the heights (2011–15, the reservoir still full).
# Reads `derived/scene/terrain.json` for the land's extent and writes `terrain_osm.webp` over the same extent
# (OpenStreetMap's standard tiles, reprojected from Web Mercator to the land's grid), and adds it to terrain.json
# ("map", with a provenance line). Run after terrain.py, which keeps both on a rebuild.
#   osm_map.py VIDEO_DIR [--zoom 16]
# Only a backdrop, like the Route Map's: nothing is read off it. The tiles are cached in --cache and fetched slowly,
# as OpenStreetMap's tile policy asks; the viewer credits "© OpenStreetMap contributors".
import argparse, json, math, pathlib, time
import cv2, numpy as np, requests

ap = argparse.ArgumentParser()
ap.add_argument("video_dir", type=pathlib.Path)
ap.add_argument("--zoom", type=int, default=16)
ap.add_argument("--cache", type=pathlib.Path, default=pathlib.Path.home() / ".cache" / "evidence-terrain" / "osm")
a = ap.parse_args()

out = a.video_dir / "derived" / "scene"
T = json.load(open(out / "terrain.json"))
lon0, lat0 = T["at"]["lon"], T["at"]["lat"]
KX, KZ = 111320 * math.cos(math.radians(lat0)), 110574  # as terrain.py
(x0, x1), (z0, z1) = T["grid"]["x"], T["grid"]["z"]
W, E, N, S = lon0 + x0 / KX, lon0 + x1 / KX, lat0 - z0 / KZ, lat0 - z1 / KZ

# Web Mercator pixels at the zoom (256 px tiles)
Z = 2 ** a.zoom * 256
mx = lambda lon: (lon + 180) / 360 * Z
my = lambda lat: (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * Z
tx0, tx1, ty0, ty1 = int(mx(W) // 256), int(mx(E) // 256), int(my(N) // 256), int(my(S) // 256)
a.cache.mkdir(parents=True, exist_ok=True)
ua = {"User-Agent": "frame-geo-evidence-pipeline/scene osm_map.py (research; one-off backdrop, cached)"}
mosaic = np.zeros(((ty1 - ty0 + 1) * 256, (tx1 - tx0 + 1) * 256, 3), np.uint8)
for ty in range(ty0, ty1 + 1):
    for tx in range(tx0, tx1 + 1):
        f = a.cache / f"{a.zoom}_{tx}_{ty}.png"
        if not f.exists():
            r = requests.get(f"https://tile.openstreetmap.org/{a.zoom}/{tx}/{ty}.png", headers=ua, timeout=60)
            r.raise_for_status()
            f.write_bytes(r.content)
            time.sleep(0.5)
        mosaic[(ty - ty0) * 256:(ty - ty0 + 1) * 256, (tx - tx0) * 256:(tx - tx0 + 1) * 256] = cv2.imread(str(f), cv2.IMREAD_COLOR)

# onto the land's grid: linear in longitude and latitude, north row first (as terrain_layers.webp)
w = int(round((mx(E) - mx(W))))
h = int(round(w * (z1 - z0) / (x1 - x0)))
lons = W + (E - W) * (np.arange(w) + 0.5) / w
lats = N - (N - S) * (np.arange(h) + 0.5) / h
map_x = ((lons + 180) / 360 * Z - tx0 * 256).astype(np.float32)
map_y = ((1 - np.arcsinh(np.tan(np.radians(lats))) / np.pi) / 2 * Z - ty0 * 256).astype(np.float32)
img = cv2.remap(mosaic, *np.meshgrid(map_x, map_y), cv2.INTER_LINEAR)
cv2.imwrite(str(out / "terrain_osm.webp"), img, [cv2.IMWRITE_WEBP_QUALITY, 92])

T["map"] = "terrain_osm.webp"
T["provenance"] = [p for p in T["provenance"] if p["label"] != "Street map"] + [{
    "label": "Street map", "evidence": f"The Route Map's backdrop laid over the land: OpenStreetMap's standard map (zoom {a.zoom}, "
    f"fetched {time.strftime('%Y-%m-%d')}; © OpenStreetMap contributors, ODbL), so today's river and roads, not those of the "
    "filming date. Only a backdrop: nothing is read off it."}]
json.dump(T, open(out / "terrain.json", "w"), ensure_ascii=False, separators=(",", ":"))
print(f"street map: {(tx1 - tx0 + 1) * (ty1 - ty0 + 1)} tiles at zoom {a.zoom} → {w}×{h}")
