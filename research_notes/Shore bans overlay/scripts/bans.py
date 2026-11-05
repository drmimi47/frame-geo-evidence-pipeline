"""A storyboard still: who may go near the shore round the crossing, on both banks (NEXT.md S4/I9, the user,
5 November 2026: "how the Enerhodar side is closed off", with the other bans on residents for context).

    python -I bans.py <deepstate.geojson> <osm_boundaries.json> <out.jpg> <out.json>      (from the project root)

The ground is the zoom-out's own pass of 28 August 2025: its 10 m crops round the crossing (c3d, c3s) over its 60 m
wide crop, only resampled (linear in lon/lat, as stored) and dimmed; no date shown, so no film moment is implied. Drawn
on it, every extent as its source gives it (research_notes/Shore bans overlay/restrictions.md):
- DeepStateMAP's occupied area of 4 November 2026 (as the front line overlay test), a faint red and its edge.
- The reservoir's shore before the breach: OpenStreetMap's outline of the bed (relation 1600087, network.json
  `areas`), its outer edge as the film draws it (zoomout._shoreline). No source says which shore its ban means: this
  is our reading, said on the still.
- Enerhodar's ban (the occupation administration's reminder of 1 August 2024, TASS): no closer than 500 m to the shore,
  no crossing. Drawn inside OSM's Enerhodar hromada (relation 12207507: the area is not stated, so the town's own
  hromada) and the occupied area only: the 500 m on land beyond the old shore (the hromada reaches barely into the bed,
  so the ban on crossing is said, not drawn).
- Balitsky's 15 km (Epiphany services without parishioners, January 2025 and 2026): a limit on gatherings, not on
  movement; a dashed edge 15 km from the old shore over the occupied land.
- Nikopol district's order 34 (25 March 2022, still cited April 2026): the water and the shore strip, no distance
  given, so only a dashed white edge along the north bank's old shore inside OSM's Nikopol raion (relation 1738037),
  never a band of our own.
- The towns named in relocation or evacuation orders: GeoNames points, Kamianka-Dniprovska from OSM (node 337675581).
"""

import json
import math
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from image_evidence.satellite.zoomout import _shoreline

ZNPP = "libraries/conductive-seam/satellite/networks/znpp"
FONT = "/System/Library/Fonts/HelveticaNeue.ttc"
W, H = 1920, 1080
KZ = 110574.0
LON_C, LAT_C, VIEW_M = 34.60, 47.50, 56000.0
GAIN = 0.62
RED = np.array([214, 40, 40], np.float32)
YELLOW = (255, 205, 60)
BAN = np.array([255, 255, 255], np.float32)
STRIP_M, GATHER_M = 500.0, 15000.0
TOWNS = [   # name, lon, lat, the order's line (restrictions.md 2.1, 3.5, 3.6)
    ("ENERHODAR", 34.66199, 47.49048, "IN THE “TEMPORARY RELOCATION” OF 18 SETTLEMENTS, MAY 2023", 1),
    ("KAMIANKA-DNIPROVSKA", 34.4109, 47.4901, "IN THE “TEMPORARY RELOCATION” OF 18 SETTLEMENTS, MAY 2023", 1),
    ("NIKOPOL", 34.39126, 47.56826, "COMPULSORY EVACUATION, MAY 2026: ALMOST 100 STREETS, NOT NAMED", -1),
    ("MARHANETS", 34.6245, 47.63088, "COMPULSORY EVACUATION, MAY 2026: ONE STREET, NOT NAMED", 1),
    ("VYSHCHETARASIVKA", 34.88115, 47.57106, "COMPULSORY EVACUATION OF ALL RESIDENTS, JULY 2026", -1),
]

kx = 111320.0 * math.cos(math.radians(LAT_C))
mpp = VIEW_M / W
west, east = LON_C - VIEW_M / 2 / kx, LON_C + VIEW_M / 2 / kx
north, south = LAT_C + H / 2 * mpp / KZ, LAT_C - H / 2 * mpp / KZ


def px(lonlat):
    a = np.asarray(lonlat, np.float64)[:, :2]
    return np.stack([W / 2 + (a[:, 0] - LON_C) * kx / mpp, H / 2 - (a[:, 1] - LAT_C) * KZ / mpp], 1)


def ground():
    """The pass, sampled at each frame pixel's lon/lat: the 60 m crop under, the 10 m crops where they have pixels."""
    lon = west + (np.arange(W) + 0.5) / W * (east - west)
    lat = north - (np.arange(H) + 0.5) / H * (north - south)
    LON, LAT = np.meshgrid(lon, lat)
    out, have = np.zeros((H, W, 3), np.float32), np.zeros((H, W), np.float32)
    for name in ("wide_s2", "c3d_2025_08", "c3s_2025_08"):
        g = json.load(open(f"{ZNPP}/imagery/{name}.json"))["grid"]
        w0, s0, e0, n0 = g["bbox"]
        src = np.asarray(Image.open(f"{ZNPP}/imagery/{name}/rgb.webp").convert("RGB")).astype(np.float32)
        sh, sw = src.shape[:2]
        mx = ((LON - w0) / (e0 - w0) * sw - 0.5).astype(np.float32)
        my = ((n0 - LAT) / (n0 - s0) * sh - 0.5).astype(np.float32)
        img = cv2.remap(src, mx, my, cv2.INTER_AREA if name != "wide_s2" else cv2.INTER_CUBIC,
                        borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        inside = ((mx >= 0) & (mx <= sw - 1) & (my >= 0) & (my <= sh - 1)).astype(np.float32)
        if name != "wide_s2":   # the close crops feathered in over 40 px, as a close-up laid over the wide pass
            inside = cv2.GaussianBlur(cv2.erode(inside, np.ones((41, 41), np.uint8)), (0, 0), 12)
        out = out * (1 - inside[..., None]) + img * inside[..., None]
        have = np.maximum(have, inside)
    return out * GAIN


def ways_to_rings(rel):
    """A boundary relation's outer ways joined end to end into closed rings (lon, lat)."""
    segs = [[(p["lon"], p["lat"]) for p in m["geometry"]] for m in rel["members"]
            if m["type"] == "way" and m.get("role", "outer") in ("outer", "") and m.get("geometry")]
    rings = []
    while segs:
        ring = segs.pop(0)
        grown = True
        while grown and ring[0] != ring[-1]:
            grown = False
            for i, s in enumerate(segs):
                if s[0] == ring[-1]:
                    ring += s[1:]
                elif s[-1] == ring[-1]:
                    ring += s[::-1][1:]
                elif s[-1] == ring[0]:
                    ring = s[:-1] + ring
                elif s[0] == ring[0]:
                    ring = s[::-1][:-1] + ring
                else:
                    continue
                segs.pop(i)
                grown = True
                break
        rings.append(ring)
    return rings


def mask_of(rings_px):
    m = np.zeros((H, W), np.uint8)
    cv2.fillPoly(m, [np.round(r * 4).astype(np.int32) for r in rings_px], 255, cv2.LINE_AA, shift=2)
    return m > 127


def dashed(d, pts, on=9, off=7, fill=(255, 255, 255, 235), width=2, keep=None):
    """A polyline drawn dashed by length along it; keep(x, y) chooses which stretches are drawn."""
    acc, draw = 0.0, True
    for a, b in zip(pts[:-1], pts[1:]):
        L = math.dist(a, b)
        if L == 0:
            continue
        t = 0.0
        while t < L:
            step = min((on if draw else off) - acc, L - t)
            p = (a[0] + (b[0] - a[0]) * t / L, a[1] + (b[1] - a[1]) * t / L)
            q = (a[0] + (b[0] - a[0]) * (t + step) / L, a[1] + (b[1] - a[1]) * (t + step) / L)
            if draw and (keep is None or keep(*p)):
                d.line([p, q], fill=fill, width=width)
            t += step
            acc += step
            if acc >= (on if draw else off) - 1e-6:
                acc, draw = 0.0, not draw


def main(ds_path, osm_path, out, out_json):
    base = ground()
    net = json.load(open(f"{ZNPP}/network.json"))
    lon0, lat0 = 34.5879012, 47.5085556     # the zoom-out's plane (film.json camera centre)
    kx0 = 111320.0 * math.cos(math.radians(lat0))
    meadow = next(a for a in net["areas"] if a.get("osm_relation") == 1600087)
    rings_m = [np.stack([(np.asarray(r)[:, 0] - lon0) * kx0, (np.asarray(r)[:, 1] - lat0) * KZ], 1)
               for r in meadow["rings"]]
    shore = [np.stack([lon0 + s[:, 0] / kx0, lat0 + s[:, 1] / KZ], 1) for s in _shoreline(rings_m, 500.0)]
    shore_px = [px(s) for s in shore]
    bed = mask_of(shore_px)

    occ_rings = []
    for f in json.load(open(ds_path))["features"]:
        if "Occupied" not in (f.get("properties") or {}).get("name", ""):
            continue
        g = f["geometry"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"] if g["type"] == "MultiPolygon" else []
        occ_rings += [px(p[0]) for p in polys]
    occ = mask_of(occ_rings)

    rel = {e["id"]: e for e in json.load(open(osm_path))["elements"]}
    ener = mask_of([px(r) for r in ways_to_rings(rel[12207507])])
    nikopol = mask_of([px(r) for r in ways_to_rings(rel[1738037])])

    land = ~bed
    dist = cv2.distanceTransform(land.astype(np.uint8), cv2.DIST_L2, 5) * mpp     # metres to the old shore
    strip = land & (dist <= STRIP_M) & ener & occ
    gather = land & (dist <= GATHER_M) & occ

    # the occupied area: a faint red over the ground, as the front line overlay
    a = occ.astype(np.float32)[..., None]
    img = base + (RED - base) * 0.16 * a
    # Enerhodar's ban: the 500 m strip filled
    s = cv2.GaussianBlur(strip.astype(np.float32), (0, 0), 0.7)[..., None]
    img = img + (BAN - img) * 0.55 * s
    o = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(o, "RGBA")

    def contours(m):
        return [c[:, 0].astype(np.float64) for c in cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL,
                                                                     cv2.CHAIN_APPROX_NONE)[0] if len(c) > 8]

    for c in contours(occ):
        d.line([tuple(p) for p in c] + [tuple(c[0])], fill=(214, 40, 40, 230), width=2)
    for c in contours(strip):
        d.line([tuple(p) for p in c] + [tuple(c[0])], fill=(255, 255, 255, 255), width=2)
    # the 15 km edge: only where it runs over the occupied land, not along the front or the frame's edge
    g_edge = gather & ~cv2.erode(gather.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    inner = cv2.erode(occ.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
    for c in contours(gather):
        dashed(d, [tuple(p) for p in c], on=6, off=6, fill=(255, 255, 255, 210), width=2,
               keep=lambda x, y: 4 < x < W - 4 and 4 < y < H - 4 and inner[int(y), int(x)] and dist[int(y), int(x)] > 3000)
    # Nikopol district's order: no distance, so only the north bank's old shore, dashed
    for sp in shore_px:
        dashed(d, [tuple(p) for p in sp], on=10, off=7, fill=(255, 255, 255, 235), width=2,
               keep=lambda x, y: 0 <= x < W and 0 <= y < H and nikopol[int(y), int(x)] and not occ[int(y), int(x)])

    for k in (0, 4):     # Dniprovska; Ferosplavna-1's strand (network.json), plain: no state
        d.line([tuple(p) for p in px(net["lines"][k]["coords"])], fill=YELLOW + (225,), width=2)

    f = lambda z, i=0: ImageFont.truetype(FONT, z, index=i)
    for name, lo, la, note, side in TOWNS:
        x, y = px([(lo, la)])[0]
        d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(255, 255, 255, 240))
        tw = max(d.textlength(name, font=f(15)), d.textlength(note, font=f(12)))
        x0 = min(max(x - tw / 2, 16), W - 16 - tw)
        y0 = y + 10 if side > 0 else y - 50
        d.rectangle([x0 - 6, y0 - 3, x0 + tw + 6, y0 + 40], fill=(0, 0, 0, 140))
        d.text((x0, y0), name, font=f(15), fill=(255, 255, 255))
        d.text((x0, y0 + 21), note, font=f(12), fill=(225, 225, 225))

    # the key, top right
    rows = [
        ("strip", "ENERHODAR: NO CLOSER THAN 500 M TO THE RESERVOIR'S SHORE, AND NO CROSSING IT",
         "THE OCCUPATION ADMINISTRATION, 1 AUGUST 2024 (TASS): \u201cONCE AGAIN\u201d, AFTER MINES KILLED CIVILIANS "
         "CROSSING THE SHALLOWS", "WHICH SHORE IS NOT SAID: DRAWN FROM THE SHORE BEFORE THE BREACH, IN THE TOWN'S "
         "HROMADA (THE AREA IS NOT STATED EITHER)"),
        ("thin", "UNDER 15 KM FROM THE SHORE OR THE FRONT: EPIPHANY SERVICES WITHOUT PARISHIONERS",
         "BALITSKY, RUSSIAN-INSTALLED GOVERNOR, JANUARY 2025 AND 2026 · A LIMIT ON GATHERINGS, NOT ON MOVEMENT", ""),
        ("dash", "NIKOPOL DISTRICT: NO GOING ONTO THE WATER OR THE SHORE STRIP",
         "ORDER 34, 25 MARCH 2022, STILL CITED APRIL 2026 · NO DISTANCE GIVEN, SO ONLY THE SHORE IS MARKED", ""),
        ("red", "OCCUPIED, 4 NOVEMBER 2026", "DEEPSTATEMAP, AN ASSESSMENT FROM OPEN SOURCES", ""),
    ]
    hgt = 46 + sum(50 + (16 if r[3] else 0) for r in rows) + 40
    kw = max(max(d.textlength(r[1], font=f(14)), d.textlength(r[2], font=f(11)), d.textlength(r[3], font=f(11)))
             for r in rows) + 32
    kx0_, ky0 = W - 36 - kw, H - 96 - hgt    # bottom right, over the occupied land: the towns keep the top
    d.rectangle([kx0_ - 16, ky0 - 12, W - 22, ky0 + hgt], fill=(0, 0, 0, 165))
    d.text((kx0_, ky0), "WHO MAY GO NEAR THE SHORE", font=f(22), fill=(255, 255, 255))
    y = ky0 + 44
    for kind, t1, t2, t3 in rows:
        sx = kx0_
        if kind == "strip":
            d.rectangle([sx, y + 3, sx + 22, y + 13], fill=(235, 235, 235, 200), outline=(255, 255, 255), width=1)
        elif kind == "thin":
            dashed(d, [(sx, y + 8), (sx + 22, y + 8)], on=6, off=6, fill=(255, 255, 255, 210), width=2)
        elif kind == "dash":
            dashed(d, [(sx, y + 8), (sx + 22, y + 8)], on=10, off=7, width=2)
        else:
            d.rectangle([sx, y + 3, sx + 22, y + 13], fill=(120, 40, 40, 220), outline=(214, 40, 40), width=2)
        d.text((sx + 32, y), t1, font=f(14), fill=(255, 255, 255))
        d.text((sx + 32, y + 20), t2, font=f(11), fill=(215, 215, 215))
        if t3:
            d.text((sx + 32, y + 36), t3, font=f(11), fill=(215, 215, 215))
        y += 50 + (16 if t3 else 0)
    d.text((kx0_, y + 2), "ALSO: A CURFEW ON BOTH BANKS · ENERHODAR'S CHECKPOINT CLOSED BOTH WAYS, 12 MAY 2026",
           font=f(11), fill=(215, 215, 215))

    d.text((24, H - 58), "BANS: TASS 1 AUG 2024; BALITSKY'S TELEGRAM; KOMMERSANT; NIKOPOL COUNCIL; DNIPROPETROVSK "
           "REGIONAL MILITARY ADMINISTRATION · SHORE, HROMADA, DISTRICT, LINES: OPENSTREETMAP · TOWNS: GEONAMES",
           font=f(12), fill=(255, 255, 255, 170))
    d.text((24, H - 38), "SENTINEL-2 · 28 AUGUST 2025 · CONTAINS MODIFIED COPERNICUS SENTINEL DATA 2025",
           font=f(12), fill=(255, 255, 255, 130))
    o.save(out, quality=92)
    json.dump({"view": {"centre": [LON_C, LAT_C], "width_m": VIEW_M, "m_per_px": round(mpp, 2),
                        "bbox": [round(west, 5), round(south, 5), round(east, 5), round(north, 5)]},
               "drawn_km2": {"enerhodar_strip": round(float(strip.sum()) * mpp * mpp / 1e6, 1)},
               "shore": "OSM relation 1600087's outer edge (zoomout._shoreline, inlets under 1 km closed): our reading "
                        "of 'the shore', no source defines it",
               "sources": "research_notes/Shore bans overlay/restrictions.md"}, open(out_json, "w"), indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:5])
