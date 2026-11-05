"""A storyboard still: where the last two lines can be heard (Earshot's Zifzafa idea 2, NEXT.md S4, 5 November 2026).

    python -I footprint.py <frame.png> <t_s> <out.jpg>      (from the project root)

The frame is the zoom-out's own (film-20261102-221617) at second t, its camera read from film.json (north up,
equirectangular about the plant, as zoomout.Plane). Round Dniprovska (750 kV) and Ferosplavna-1 (330 kV; the drawn
strand of "Ferosplavna 1, 2", OSM) three bands, an estimate from published measurements of other lines, never a
measurement here (reports/Enerhodar crossing voices and sound.md, "The lines are loud only when wet"):

- dry, fair weather: a faint crackle near the line only, to about 140 m (BAPE: 25 dBA or less 100 m beyond a
  735 kV right of way, its edge 40 m from the centreline; Duchassin et al. 2007);
- rain or fog: to about 0.4 km (Hydro-Quebec: about 53 dBA at 40 m in rain, about 40 dBA 100 m beyond the edge; that
  fall, about 7 dB per doubling of distance, carried on to a quiet night's 30 dBA, assumed);
- rain or fog on a still night, at most: to about 1.4 km (from 40 dBA at 140 m, spreading as a line source only,
  3 dB per doubling: an upper bound).
The 330 kV line gets the same bands, dashed: measured at 25-60 dBA in rain with no clear trend (TransGrid/WSP 2025),
so the 750 kV's figures are an upper estimate for it. Distances from each town's GeoNames point (its centre) to the
nearest of the two lines, measured on the same plane; the towns reach closer than their centres.
"""

import json
import math
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FILM = "libraries/conductive-seam/satellite/networks/znpp/films/film-20261102-221617/film.json"
NET = "libraries/conductive-seam/satellite/networks/znpp/network.json"
KZ = 110574.0
FONT = "/System/Library/Fonts/HelveticaNeue.ttc"
LINES = [("Dniprovska", 0, False), ("Ferosplavna 1, 2", 4, True)]       # name in network.json, index, dashed
BANDS = [(1400, 0.10), (400, 0.20), (140, 0.55)]                       # metres from the centreline, white alpha
TOWNS = {"Nikopol": (34.39126, 47.56826), "Marhanets": (34.6245, 47.63088), "Enerhodar": (34.66199, 47.49048)}


def camera(t):
    f = json.load(open(FILM))
    c = f["camera"]
    i = {k: n for n, k in enumerate(c["fields"])}
    s = min(c["samples"], key=lambda r: abs(r[0] - t))
    lon0, lat0 = c["centre"]
    return lon0, lat0, s[i["view_km"]] * 1000 / f["width"], s[i["centre_east_km"]] * 1000, s[i["centre_north_km"]] * 1000


def main(frame_path, t, out):
    img = Image.open(frame_path).convert("RGB")
    W, H = img.size
    lon0, lat0, mpp, cx, cy = camera(float(t))
    kx = 111320.0 * math.cos(math.radians(lat0))
    plane = lambda lo, la: ((lo - lon0) * kx, (la - lat0) * KZ)
    pix = lambda x, y: (W / 2 + (x - cx) / mpp, H / 2 - (y - cy) / mpp)
    net = json.load(open(NET))
    lines = {name: [plane(*p[:2]) for p in net["lines"][k]["coords"]] for name, k, _ in LINES}

    base = np.asarray(img).astype(np.float32)
    for name, _, dashed in LINES:
        pts = np.round(np.array([pix(*p) for p in lines[name]]) * 4).astype(np.int32)
        for m, a in BANDS:
            band = np.zeros((H, W), np.uint8)
            cv2.polylines(band, [pts], False, 255, max(1, int(round(2 * m / mpp))), cv2.LINE_AA, shift=2)
            k = band.astype(np.float32)[..., None] / 255 * (a * (0.6 if dashed else 1.0))
            base = base + (255 - base) * k * 0.55
        if dashed:   # the 330 kV band's edge dashed, every other stretch of its outline
            edge = np.zeros((H, W), np.uint8)
            cv2.polylines(edge, [pts], False, 255, int(round(2 * BANDS[0][0] / mpp)), cv2.LINE_AA, shift=2)
            cs, _ = cv2.findContours(edge, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            dash = np.zeros((H, W), np.uint8)
            for c in cs:
                c = c[:, 0]
                for j in range(0, len(c) - 6, 12):
                    cv2.line(dash, tuple(map(int, c[j])), tuple(map(int, c[j + 6])), 255, 1, cv2.LINE_AA)
            base = base + (255 - base) * dash[..., None].astype(np.float32) / 255 * 0.6
    o = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(o, "RGBA")
    f = lambda s: ImageFont.truetype(FONT, s, index=0)

    for town, (lo, la) in TOWNS.items():
        tx, ty = plane(lo, la)
        best = min(((math.hypot(x - tx, y - ty), (x, y), name) for name, c in lines.items() for x, y in c))
        dist, (nx, ny), _ = best
        a, b = pix(tx, ty), pix(nx, ny)
        if not (0 <= a[0] < W and 0 <= a[1] < H):
            continue
        d.line([a, b], fill=(255, 255, 255, 170), width=1)
        for p in (a, b):
            d.ellipse([p[0] - 2.5, p[1] - 2.5, p[0] + 2.5, p[1] + 2.5], fill=(255, 255, 255, 220))
        txt = f"{town.upper()} · {dist / 1000:.1f} KM"
        w = d.textlength(txt, font=f(15))
        if math.dist(a, b) > 120:      # beside the middle of a long leader, else beyond the line's end of a short one
            lx, ly = (a[0] + b[0]) / 2 + 12, (a[1] + b[1]) / 2 - 10
        else:
            lx, ly = (b[0] + 12, b[1] - 10) if b[0] >= a[0] else (b[0] - 22 - w, b[1] - 10)
        d.rectangle([lx - 5, ly - 2, lx + w + 5, ly + 19], fill=(0, 0, 0, 128))
        d.text((lx, ly), txt, font=f(15), fill=(255, 255, 255))

    # key, top right (the film's date and legend have the top left)
    rows = [("WHERE THE LAST TWO LINES CAN BE HEARD", 22, (255, 255, 255)),
            ("AN ESTIMATE FROM OTHER LINES' MEASUREMENTS, NOT MEASURED HERE", 14, (215, 215, 215))]
    key = [(0.55, "DRY WEATHER: A FAINT CRACKLE, ABOUT 140 M"),
           (0.20, "RAIN OR FOG: ABOUT 0.4 KM"),
           (0.10, "RAIN OR FOG, A STILL NIGHT: AT MOST 1.4 KM")]
    x0, y0, wbox = W - 40 - 560, 34, 560
    d.rectangle([x0 - 12, y0 - 10, W - 28, y0 + 196], fill=(0, 0, 0, 128))
    y = y0
    for s, z, c in rows:
        d.text((x0, y), s, font=f(z), fill=c)
        y += z + 12
    y += 4
    for a, s in key:
        g = int(255 * min(1, a * 1.6 + 0.15))
        d.rectangle([x0, y + 2, x0 + 26, y + 14], fill=(g, g, g, 200))
        d.text((x0 + 38, y), s, font=f(15), fill=(255, 255, 255))
        y += 24
    d.line([x0, y + 8, x0 + 26, y + 8], fill=(255, 255, 255, 200), width=1)
    for k in range(0, 26, 8):
        d.line([x0 + k, y + 12, x0 + k + 4, y + 12], fill=(255, 255, 255, 200), width=1)
    d.text((x0 + 38, y), "750 KV SOLID · 330 KV DASHED (MEASURED QUIETER)", font=f(15), fill=(255, 255, 255))
    y += 24
    d.text((x0 + 38, y), "TOWNS: KM FROM THEIR CENTRE TO THE NEAREST LINE", font=f(15), fill=(255, 255, 255))

    note = ("SOURCES: HYDRO-QUÉBEC 735 KV MEASUREMENTS (DUCHASSIN ET AL. 2007; BAPE) · TRANSGRID/WSP 2025 (330 KV) · "
            "LINES: OPENSTREETMAP · TOWNS: GEONAMES")
    d.text((24, H - 58), note, font=f(13), fill=(255, 255, 255, 150))
    o.save(out, quality=92)


if __name__ == "__main__":
    main(*sys.argv[1:4])
