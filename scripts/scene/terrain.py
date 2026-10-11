# Scene Viewer, step 3 (optional): the land around a take, so the little the footage rebuilt can be read in its place.
# Writes `derived/scene/terrain.json` (heights on a grid, the Route Map's lines, how the take is placed),
# `terrain_layers.webp` (what the viewer draws the land with: open water and how wet the ground stays, from Sentinel-2)
# and `terrain.jpg` (the true-colour image, kept for a photo drape). Tier inferred: the heights and images are measured,
# but where the take sits in them, and which way round, is an estimate (the footage has no coordinates or compass).
#   terrain.py VIDEO_DIR --piece pools [--bearing DEG --bearing-note "..."] [--at LON,LAT] [--bbox W,S,E,N]
#              [--image SENTINEL2_ITEM] [--dem fabdem|copernicus] [--exag 1]
# --at defaults to the Route Map's position for the take (the median of inferred/track.json's samples in it).
# --bearing: the compass bearing the take's -z axis (the way its first camera looks, levelled) is turned to. By default
# the take is turned so its cameras' way (first to last) runs as the Route Map's walk does over the same seconds.
# Heights: FABDEM (Copernicus GLO-30 with forests and buildings taken out: the ground, not the tree tops), true to
# size unless --exag; its tile is read out of the 10° archive by byte ranges. Runs with the project's .venv (numpy,
# OpenCV, requests); the tiles are cached in --cache.
import argparse, io, json, math, pathlib, time
import cv2, numpy as np, requests

ap = argparse.ArgumentParser()
ap.add_argument("video_dir", type=pathlib.Path)
ap.add_argument("--piece", required=True)
ap.add_argument("--bearing", type=float)
ap.add_argument("--bearing-note")
ap.add_argument("--at")
ap.add_argument("--at-note", help="who placed it there, and why (with --at)")
ap.add_argument("--bbox", default="35.150,47.726,35.215,47.762")
ap.add_argument("--image", default="S2B_MSIL2A_20240306T083719_R064_T36TXT_20240306T131243")
ap.add_argument("--exag", type=float, default=1.0)
ap.add_argument("--dem", choices=["fabdem", "copernicus"], default="fabdem")
# the cloud-free Sentinel-2 dates after the drainage whose moisture is averaged (how wet the ground stays)
ap.add_argument("--wet-items", default="S2B_MSIL2A_20230928T083729_R064_T36TXT_20230928T142659,"
                "S2B_MSIL2A_20231107T084049_R064_T36TXT_20231107T125346,S2B_MSIL2A_20240306T083719_R064_T36TXT_20240306T131243,"
                "S2A_MSIL2A_20240430T083601_R064_T36TXT_20240430T134316,S2B_MSIL2A_20240714T083559_R064_T36TXT_20240714T134633,"
                "S2A_MSIL2A_20240818T083601_R064_T36TXT_20240818T115150")
ap.add_argument("--step", type=float, default=15.0, help="grid spacing, m")
ap.add_argument("--cache", type=pathlib.Path, default=pathlib.Path.home() / ".cache" / "evidence-terrain")
a = ap.parse_args()

out = a.video_dir / "derived" / "scene"
scene = json.load(open(out / "scene.json"))
piece = next(p for p in scene["pieces"] if p["name"] == a.piece)
track = json.load(open(a.video_dir / "inferred" / "track.json"))
plan = json.load(open(a.video_dir / "inferred" / "walk_plan.json"))
W, S, E, N = map(float, a.bbox.split(","))

if a.at:
    lon0, lat0 = map(float, a.at.split(","))
    at_note = f"Placed at {lat0:.5f} N, {lon0:.5f} E" + (f": {a.at_note}" if a.at_note else ", as given") + "."
else:
    f = track["sample_fields"]
    inside = [s for s in track["samples"] if piece["start"] <= s[f.index("t")] <= piece["end"]]
    lon0 = float(np.median([s[f.index("lon")] for s in inside]))
    lat0 = float(np.median([s[f.index("lat")] for s in inside]))
    sig = int(np.median([s[f.index("sigma_m")] for s in inside]))
    at_note = (f"Placed where the Route Map puts the take ({lat0:.5f} N, {lon0:.5f} E, the middle of its estimate from "
               f"{piece['start']:.0f} to {piece['end']:.0f} s, ±{sig} m).")

if a.bearing is None:
    # the Route Map's walk over the take's seconds: its first to last position, against the take's first to last camera
    f = track["sample_fields"]
    inside = [s_ for s_ in track["samples"] if piece["start"] <= s_[f.index("t")] <= piece["end"]]
    (lo1, la1), (lo2, la2) = [(s_[f.index("lon")], s_[f.index("lat")]) for s_ in (inside[0], inside[-1])]
    moved = math.hypot((lo2 - lo1) * 111320 * math.cos(math.radians(la1)), (la2 - la1) * 110574)
    if moved >= 5:  # the Route Map's walk over these seconds
        walk = math.degrees(math.atan2((lo2 - lo1) * math.cos(math.radians(la1)), la2 - la1)) % 360
        walk_note = f"runs as the Route Map's walk does over the same seconds ({walk:.0f}°)"
    else:  # the Route Map holds the camera in one place here: the way it faces there (the path's direction)
        hs = [math.radians(s_[f.index("heading_deg")]) for s_ in inside]
        walk = math.degrees(math.atan2(sum(map(math.sin, hs)), sum(map(math.cos, hs)))) % 360
        walk_note = f"runs the way the Route Map faces there ({walk:.0f}°, along the path at the place it holds the take)"
    c0, c1 = piece["cameras"][0]["position"], piece["cameras"][-1]["position"]
    off = math.degrees(math.atan2(c1[0] - c0[0], -(c1[2] - c0[2])))  # the cameras' way, from the take's -z toward +x
    a.bearing = round((walk - off) % 360, 1)
    a.bearing_note = (f"The footage has no compass. The take is turned so its cameras' way, first to last "
                      f"({math.dist(c0, c1):.0f} m), {walk_note}: an assumption, as uncertain as the Route Map there.")
elif not a.bearing_note:
    ap.error("--bearing needs --bearing-note (why that way)")

# local metres around the take: x east, z south (three.js: y up, -z north)
KX, KZ = 111320 * math.cos(math.radians(lat0)), 110574
to_xz = lambda lon, lat: ((lon - lon0) * KX, -(lat - lat0) * KZ)

# ---- heights: 1 arcsecond tiles (pixel centres on whole arcseconds from the tile's corner)
FABDEM = "https://data.bris.ac.uk/datasets/s5hqmjcdj8yo2ibzi9b4ew3sn"
class Remote(io.RawIOBase):  # a file read by HTTP byte ranges: one tile out of a 1.2 GB zip, not the whole zip
    def __init__(self, url):
        self.url, self.pos = url, 0
        self.size = int(requests.head(url, timeout=60).headers["Content-Length"])
    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.pos
    def seek(self, o, whence=0):
        self.pos = {0: o, 1: self.pos + o, 2: self.size + o}[whence]
        return self.pos
    def readinto(self, b):
        if not len(b) or self.pos >= self.size: return 0
        r = requests.get(self.url, headers={"Range": f"bytes={self.pos}-{self.pos + len(b) - 1}"}, timeout=300)
        r.raise_for_status(); b[:len(r.content)] = r.content; self.pos += len(r.content)
        return len(r.content)
tiles = {}
def dem_tile(la, lo):
    if (la, lo) not in tiles:
        a.cache.mkdir(parents=True, exist_ok=True)
        if a.dem == "fabdem":
            p = a.cache / f"N{la:02d}E{lo:03d}_FABDEM_V1-2.tif"
            if not p.exists():
                import zipfile
                z0, z1 = la // 10 * 10, lo // 10 * 10
                z = zipfile.ZipFile(io.BufferedReader(Remote(f"{FABDEM}/N{z0:02d}E{z1:03d}-N{z0 + 10:02d}E{z1 + 10:03d}_FABDEM_V1-2.zip"), 1 << 20))
                p.write_bytes(z.read(next(n for n in z.namelist() if n.endswith(p.name))))
        else:
            name = f"Copernicus_DSM_COG_10_N{la:02d}_00_E{lo:03d}_00_DEM"
            p = a.cache / f"{name}.tif"
            if not p.exists():
                r = requests.get(f"https://copernicus-dem-30m.s3.amazonaws.com/{name}/{name}.tif", timeout=300)
                r.raise_for_status(); p.write_bytes(r.content)
        h = cv2.imread(str(p), cv2.IMREAD_UNCHANGED).astype(np.float32)
        tiles[(la, lo)] = cv2.GaussianBlur(h, (0, 0), 0.8)  # light: 30 m steps would show as terraces
    return tiles[(la, lo)]
assert math.floor(W) == math.floor(E) and math.floor(S) == math.floor(N), "the box must sit in one 1° tile"
dem = dem_tile(math.floor(S), math.floor(W))
nx = int(round((E - W) * KX / a.step)) + 1
ny = int(round((N - S) * KZ / a.step)) + 1
lons, lats = np.linspace(W, E, nx), np.linspace(N, S, ny)
cols = ((lons - math.floor(W)) * 3600).astype(np.float32)
rows = ((math.floor(S) + 1 - lats) * 3600).astype(np.float32)
H = cv2.remap(dem, *np.meshgrid(cols, rows), cv2.INTER_CUBIC).clip(-5, 300)
def height(lon, lat):
    return float(cv2.remap(dem, np.float32([[(lon - math.floor(W)) * 3600]]),
                           np.float32([[(math.floor(S) + 1 - lat) * 3600]]), cv2.INTER_LINEAR)[0, 0])
h0 = height(lon0, lat0)

# ---- images: Sentinel-2 L2A, cut to the box by the Planetary Computer's data API
img_w = 2048
img_h = int(round(img_w * (N - S) * KZ / ((E - W) * KX)))
def s2(item, assets, rescale=None):
    for attempt in range(4):  # the data API times out now and then (504): try again, a little later each time
        r = requests.get(f"https://planetarycomputer.microsoft.com/api/data/v1/item/bbox/{W},{S},{E},{N}/{img_w}x{img_h}.png",
                         params={"collection": "sentinel-2-l2a", "item": item, "assets": assets, "resampling": "bilinear",
                                 **({"rescale": rescale} if rescale else {})}, timeout=300)
        if r.status_code < 500 or attempt == 3:
            break
        time.sleep(5 * (attempt + 1))
    r.raise_for_status()
    return cv2.imdecode(np.frombuffer(r.content, np.uint8), cv2.IMREAD_UNCHANGED)
im = s2(a.image, "visual").astype(np.float32)[..., :3] / 255
im = np.clip(im ** 0.75 * 1.45, 0, 1)  # the true-colour product is dark; lift it for a dark viewer
cv2.imwrite(str(out / "terrain.jpg"), (im * 255).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 86])
# reflectance × 10000: L2A since processing baseline 04.00 (2022) adds 1000 to every value, taken off here
band = lambda item, b, top=6000: s2(item, b, f"0,{top}").astype(np.float32)[..., 0] * (top / 255) - 1000
# open water on the image's date: what stays dark in the near- and shortwave infrared (reflectance under 3%)
nir, swir = band(a.image, "B08", 2500), band(a.image, "B11", 2500)  # water is dark: a narrow range keeps its levels
water = cv2.GaussianBlur(cv2.medianBlur(((nir < 300) & (swir < 300)).astype(np.uint8), 5).astype(np.float32), (0, 0), 1.2)
# how wet the ground stays: the moisture index (near- against shortwave infrared) averaged over the dates, as standard
# scores; open water left out (it is drawn as water)
wet_items = a.wet_items.split(",")
ndmi = np.mean([(lambda n, s_: (n - s_) / np.maximum(n + s_, 50))(band(it, "B08"), band(it, "B11")) for it in wet_items], axis=0)
z = (ndmi - ndmi.mean()) / ndmi.std()
wet = cv2.GaussianBlur(np.clip((z - 0.4) / 2.0, 0, 1), (0, 0), 2.0) * (1 - water)
layers = np.zeros((img_h, img_w, 3), np.uint8)
layers[..., 2] = np.round(water * 255)  # R (OpenCV writes BGR)
layers[..., 1] = np.round(wet * 255)    # G
cv2.imwrite(str(out / "terrain_layers.webp"), layers, [cv2.IMWRITE_WEBP_QUALITY, 101])
date = a.image.split("_")[2][:8]
date_text = f"{int(date[6:])} {['January','February','March','April','May','June','July','August','September','October','November','December'][int(date[4:6]) - 1]} {date[:4]}"

# ---- the Route Map's lines, draped on the heights; not drawn where the take itself is
hole = float(piece.get("radius_m", 25))
# the take's own cameras on the ground (placed and turned as above): the lines leave out what the take itself shows
_b, _c = math.radians(a.bearing), piece["centre"]
cam_xz = np.array([[(c["position"][0] - _c[0]) * math.cos(_b) - (c["position"][2] - _c[2]) * math.sin(_b),
                    (c["position"][0] - _c[0]) * math.sin(_b) + (c["position"][2] - _c[2]) * math.cos(_b)] for c in piece["cameras"]])
in_take = lambda x, z: float(np.min(np.hypot(cam_xz[:, 0] - x, cam_xz[:, 1] - z))) < 3.0
def drape(coords, every=4.0):
    pts = []
    for (lo1, la1), (lo2, la2) in zip(coords, coords[1:]):
        n = max(1, int(math.dist(to_xz(lo1, la1), to_xz(lo2, la2)) / every))
        pts += [(lo1 + (lo2 - lo1) * k / n, la1 + (la2 - la1) * k / n) for k in range(n)]
    pts.append(coords[-1])
    runs, run = [], []
    for lo, la in pts:
        x, z = to_xz(lo, la)
        if in_take(x, z):
            if len(run) > 1: runs.append(run)
            run = []
        else:
            run.append([round(x, 1), round(height(lo, la), 2), round(z, 1)])
    if len(run) > 1: runs.append(run)
    return runs

# the river: the user's nine points along the uploader's dot; the route as the Route Map draws it: the stretches filmed
# (solid), those skipped at the cuts (dashed), a tick for each frame, and its start and end (A, B)
lines = [{"name": p["name"], "kind": "river", "note": p["note"], "runs": drape(p["coords"])}
         for p in plan["pieces"] if p["name"] == "bandura_points"]
R = track["route"]
def along(m):  # the route's point m metres along it
    a, c = R["along_m"], R["coordinates"]
    k = max(0, min(len(a) - 2, int(np.searchsorted(a, m, side="right")) - 1))
    f = 0.0 if a[k + 1] == a[k] else min(1.0, max(0.0, (m - a[k]) / (a[k + 1] - a[k])))
    return [c[k][0] + (c[k + 1][0] - c[k][0]) * f, c[k][1] + (c[k + 1][1] - c[k][1]) * f]
def stretch(m0, m1):
    return [along(m0)] + [c for c, m in zip(R["coordinates"], R["along_m"]) if m0 < m < m1] + [along(m1)]
segs = track["segments"]
lines.append({"name": "filmed", "kind": "filmed", "note": "the route where it was filmed",
              "runs": [r for s in segs if s["along_end_m"] > s["along_start_m"] for r in drape(stretch(s["along_start_m"], s["along_end_m"]))]})
lines.append({"name": "unfilmed", "kind": "unfilmed", "note": "skipped at a cut: not filmed",
              "runs": [r for a_, b_ in zip(segs, segs[1:]) if b_["along_start_m"] > a_["along_end_m"]
                       for r in drape(stretch(a_["along_end_m"], b_["along_start_m"]))]})
xyz = lambda lon, lat: [round(v, 1) for v in (to_xz(lon, lat)[0], height(lon, lat), to_xz(lon, lat)[1])]
frame_marks = [xyz(f["lon"], f["lat"]) for f in track["frames"] if not in_take(*to_xz(f["lon"], f["lat"]))]
ends = [{"label": e["label"], "xyz": xyz(e["lon"], e["lat"])} for e in (track["start"], track["end"])]
marks = [{"label": str(k + 1), "xyz": [round(v, 1) for v in (to_xz(*c)[0], height(*c), to_xz(*c)[1])]}
         for k, c in enumerate(next(p.get("points", p["coords"]) for p in plan["pieces"] if p["name"] == "bandura_points"))]

# the long stretches not filmed (the Route Map's `skips`): a run of cuts with only short takes between them reads as
# one dash, and where those takes lie on it is a guess
clock = lambda t: f"{round(t) // 60}:{round(t) % 60:02d}"
dist = lambda m: f"{round(m, -1):.0f} m" if m < 1000 else f"{m / 1000:.1f} km"
long_skips = [x for x in track.get("skips", []) if x["skipped_m"] >= 100]
skip_text = (" Long stretches not filmed: " + "; ".join(
    f"{clock(x['video_start'])}, one cut, about {dist(x['skipped_m'])}" if x["cuts"] == 1 else
    f"{clock(x['video_start'])}–{clock(x['video_end'])}, {x['cuts']} cuts, about {dist(x['skipped_m'])} (about "
    f"{dist(x['filmed_m'])} filmed between them)" if x["filmed_m"] >= 5 else f"{clock(x['video_start'])}–{clock(x['video_end'])}, {x['cuts']} cuts, about {dist(x['skipped_m'])}" for x in long_skips) + ". Where cuts run together, the few metres filmed "
    "between them are too short to show as solid, and how the skipped ground divides between the cuts isn't known (it is "
    "spread evenly), so where those takes and their dots lie on it is a guess.") if long_skips else ""
x0, z0 = to_xz(W, N)
x1, z1 = to_xz(E, S)
terrain = {
    "schema": "terrain/1", "tier": "inferred", "confidence": 0.25, "piece": a.piece,
    "at": {"lon": round(lon0, 6), "lat": round(lat0, 6)}, "bearing_deg": a.bearing,
    # the grid, north row first, in metres around the take (x east, z south); heights in m above sea level
    "grid": {"nx": nx, "ny": ny, "x": [round(x0, 1), round(x1, 1)], "z": [round(z0, 1), round(z1, 1)],
             "heights_dm": np.round(H * 10).astype(int).ravel().tolist()},
    "image": "terrain.jpg", "layers": "terrain_layers.webp",
    "base_m": round(h0, 2), "exaggeration": a.exag, "hole_m": round(hole, 1),
    "lines": lines, "marks": marks, "frames": frame_marks, "ends": ends,
    "summary": ("The land around the take as a map: the ground's height (true to size" + ("" if a.exag == 1 else f", ×{a.exag:g}")
                + "), contour lines every metre, open water, where the drained bed stays wet (its old channels), and the "
                "Route Map's lines. Where the take sits in it is an estimate."),
    "provenance": [
        {"label": "Heights", "evidence": (f"FABDEM: Copernicus GLO-30 (TanDEM-X radar, 2011–2015; 30 m) with forests and buildings "
         "taken out by a model, so the ground, not the tree tops; lightly smoothed" if a.dem == "fabdem" else
         "Copernicus GLO-30 surface model (TanDEM-X radar, 2011–2015; 30 m, lightly smoothed): tree tops, not the ground")
         + ("" if a.exag == 1 else f"; drawn {a.exag:g} times as tall") + ". Made while the reservoir was full, so its water is "
         f"flat at the level of the time (about {h0:.1f} m here): the drained bed has no relief in it."},
        {"label": "Water", "evidence": f"Open water on {date_text}: Sentinel-2 L2A, dark in the near- and shortwave infrared (reflectance under 3%; 10 m, {a.image})."},
        {"label": "Wet ground", "evidence": f"Where the drained bed stays wetter than the rest: the moisture index (NDMI: near- against "
         f"shortwave infrared) averaged over {len(wet_items)} cloud-free Sentinel-2 dates after the reservoir drained "
         f"({wet_items[0].split('_')[2][:4]}–{wet_items[-1].split('_')[2][:4]}); old channels hold water and grow greener. Not a height."},
        {"label": "Placed", "evidence": at_note + f" Its ground is set at the height model's height there ({h0:.1f} m)."},
        {"label": "Turned", "evidence": a.bearing_note},
        {"label": "Lines", "evidence": "From the Route Map. Blue: the Bandura as the old map draws it (the uploader's "
         "dot), through the user's points (Bandura river 1–8; 4–8 refitted to the old channel the drained bed shows). White: the walk as the Route Map draws it, solid where filmed, dashed where a cut "
         "skips it, a dot for each frame, and its start and end (A, B); estimates, the take's own stretch left out." + skip_text},
        {"label": "Sources", "evidence": ("FABDEM V1-2, Hawker et al. 2022, University of Bristol (CC BY-NC-SA 4.0), from " if a.dem == "fabdem" else "")
         + "Copernicus WorldDEM-30 © DLR e.V. 2010–2014 and © Airbus Defence and Space GmbH 2014–2018, provided under "
         "COPERNICUS by the European Union and ESA. Contains modified Copernicus Sentinel data 2023–2024, via Microsoft "
         "Planetary Computer."},
    ],
}
# the street map laid over it (osm_map.py) is kept: its extent is the box's, which a rebuild doesn't change
old = json.load(open(out / "terrain.json")) if (out / "terrain.json").exists() else {}
if old.get("map") and (out / old["map"]).exists():
    terrain["map"] = old["map"]
    terrain["provenance"] += [p for p in old["provenance"] if p["label"] == "Street map"]
json.dump(terrain, open(out / "terrain.json", "w"), ensure_ascii=False, separators=(",", ":"))
print(f"terrain: {nx}×{ny} at {a.step:g} m, {H.min():.1f}–{H.max():.1f} m, take at {lat0:.5f} N {lon0:.5f} E "
      f"(ground {h0:.1f} m), bearing {a.bearing:g}°, image {date_text}")
