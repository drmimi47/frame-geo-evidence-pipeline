"""A storyboard still: where the region's own sounds were recorded, against where the lines can be heard (Earshot's
Zifzafa idea 5, NEXT.md S4 and I9, 5 November 2026).

    python -I soundscape.py <inat_p1.json> <inat_p2.json> <out.jpg> <out.json> [<now playing>]   (from the root)

The ground is the 3D film's 10 m crop of the Sentinel-2 pass of 28 August 2025 (imagery/c3d_2025_08, the zoom-out's
own pass), cut north up to 40 x 22.5 km and only scaled (Lanczos) and dimmed by the zoom-out's one factor (0.8). On it
the two lines (OpenStreetMap, network.json; drawn plain, no state), their audible bands as footprint.py estimates them,
and iNaturalist's observations with sounds in the box 47.30-47.80 N, 34.05-35.10 E (the API's reply saved verbatim in
raw/inat/, 5 November 2026), counted in 1 km cells and drawn one dot a cell, its area by the count, never at a
recording's own place (they are one recordist's, round a frontline town: a home must not be read off them). Distances
to the nearest line are measured from each recording's own position, then only reported as a range.
"""

import json
import math
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

IMG = "libraries/conductive-seam/satellite/networks/znpp/imagery/c3d_2025_08"
NET = "libraries/conductive-seam/satellite/networks/znpp/network.json"
FONT = "/System/Library/Fonts/HelveticaNeue.ttc"
W, H = 1920, 1080
KZ = 110574.0
NORTH = 47.703
GAIN = 0.8
CELL_M = 1000.0
YELLOW = (255, 205, 60)
GREEN = (150, 230, 170)
BANDS = [(1400, 0.10), (400, 0.20), (140, 0.55)]     # footprint.py's
TOWNS = {"NIKOPOL": (34.39126, 47.56826), "MARHANETS": (34.6245, 47.63088)}


def main(p1, p2, out, out_json, playing=""):
    meta = json.load(open(f"{IMG}.json"))
    w0, s0, e0, n0 = meta["grid"]["bbox"]
    src = Image.open(f"{IMG}/rgb.webp").convert("RGB")
    sw, sh = src.size
    kx = 111320.0 * math.cos(math.radians(NORTH - 0.1))
    mpp = (e0 - w0) * kx / W
    south = NORTH - H * mpp / KZ
    ys = lambda la: (n0 - la) / (n0 - s0) * sh
    crop = src.crop((0, round(ys(NORTH)), sw, round(ys(south)))).resize((W, H), Image.LANCZOS)
    base = np.asarray(crop).astype(np.float32) * GAIN
    pix = lambda lo, la: ((lo - w0) / (e0 - w0) * W, (NORTH - la) * KZ / mpp)
    met = lambda lo, la: ((lo - w0) * kx, (la - south) * KZ)

    net = json.load(open(NET))
    lines = {k: net["lines"][k]["coords"] for k in (0, 4)}       # Dniprovska; the drawn strand of Ferosplavna 1, 2
    for k, c in lines.items():
        pts = np.round(np.array([pix(*p[:2]) for p in c]) * 4).astype(np.int32)
        for m, a in BANDS:
            band = np.zeros((H, W), np.uint8)
            cv2.polylines(band, [pts], False, 255, max(1, int(round(2 * m / mpp))), cv2.LINE_AA, shift=2)
            base += (255 - base) * band.astype(np.float32)[..., None] / 255 * a * (0.6 if k == 4 else 1.0) * 0.55
    o = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(o, "RGBA")
    for k, c in lines.items():
        d.line([pix(*p[:2]) for p in c], fill=YELLOW + (235,), width=2)

    dense = []
    for c in lines.values():
        q = [met(*p[:2]) for p in c]
        for a, b in zip(q, q[1:]):
            n = max(1, int(math.dist(a, b) / 50))
            dense += [(a[0] + (b[0] - a[0]) * j / n, a[1] + (b[1] - a[1]) * j / n) for j in range(n)]
    dense = np.array(dense)
    obs = json.load(open(p1))["results"] + json.load(open(p2))["results"]
    cells, dist, users, years, lic = {}, [], set(), [], set()
    for r in obs:
        la, lo = map(float, r["location"].split(","))
        x, y = met(lo, la)
        dist.append(float(np.min(np.hypot(dense[:, 0] - x, dense[:, 1] - y))))
        key = (math.floor(x / CELL_M), math.floor(y / CELL_M))
        cells[key] = cells.get(key, 0) + 1
        users.add(r["user"]["login"])
        years.append(int(r["observed_on"][:4]))
        lic.add(r["sounds"][0].get("license_code"))
    for (i, j), n in cells.items():
        cx, cy = (i + 0.5) * CELL_M / mpp, H - (j + 0.5) * CELL_M / mpp
        r = 4 + 3.2 * math.sqrt(n)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=GREEN + (140,), outline=GREEN + (255,), width=1)

    f = lambda s: ImageFont.truetype(FONT, s, index=0)
    for name, (lo, la) in TOWNS.items():
        x, y = pix(lo, la)
        d.ellipse([x - 2.5, y - 2.5, x + 2.5, y + 2.5], fill=(255, 255, 255, 230))
        tw = d.textlength(name, font=f(14))
        d.rectangle([x - tw / 2 - 5, y + 8, x + tw / 2 + 5, y + 28], fill=(0, 0, 0, 128))
        d.text((x - tw / 2, y + 10), name, font=f(14), fill=(255, 255, 255))
    for k, name, at in ((0, "DNIPROVSKA · 750 KV", 0.62), (4, "FEROSPLAVNA-1 · 330 KV", 0.55)):
        c = lines[k]
        x, y = pix(*c[int(len(c) * at)][:2]) if k == 4 else pix(*c[min(len(c) - 1, 40)][:2])
        tw = d.textlength(name, font=f(14))
        d.rectangle([x + 14, y - 10, x + 24 + tw, y + 10], fill=(0, 0, 0, 128))
        d.text((x + 19, y - 8), name, font=f(14), fill=(255, 255, 255))

    rows = [("WHERE THE REGION'S BIRDS WERE RECORDED", 22, (255, 255, 255)),
            (f"{len(obs)} SOUND RECORDINGS ON INATURALIST, {min(years)}–{max(years)}", 15, (255, 255, 255)),
            ("ALL BY ONE RECORDIST, ALL ROUND MARHANETS, NORTH OF THE BED", 15, (255, 255, 255)),
            (f"{min(dist) / 1000:.1f}–{max(dist) / 1000:.1f} KM FROM THE LINES: OUT OF THEIR EARSHOT", 15, (255, 255, 255)),
            ("NONE FROM THE DRAINED BED OR THE OCCUPIED BANK", 15, (255, 255, 255)),
            ("ONE DOT A 1 KM CELL, ITS AREA BY THE COUNT, NEVER AT A RECORDING'S PLACE", 13, (200, 200, 200)),
            ("ROUND THE LINES: WHERE THEY CAN BE HEARD WHEN CONNECTED, AN ESTIMATE", 13, (200, 200, 200))]
    x0, y0 = W - 40 - 590, 34
    d.rectangle([x0 - 12, y0 - 10, W - 28, y0 + 204], fill=(0, 0, 0, 128))
    y = y0
    for s, z, c in rows:
        d.text((x0, y), s, font=f(z), fill=c)
        y += z + (14 if z > 20 else 10)
    if playing:
        tw = d.textlength(playing, font=f(16))
        d.rectangle([28, 28, 52 + tw, 60], fill=(0, 0, 0, 128))
        d.text((40, 34), playing, font=f(16), fill=(255, 255, 255))
    d.text((24, H - 58), "SOUNDS: INATURALIST (UABIRD, CC BY-NC) · XENO-CANTO XC1016141 (EKATERINA KORMINA, CC0) · "
           "LINES: OPENSTREETMAP · BANDS: AN ESTIMATE FROM OTHER LINES' MEASUREMENTS", font=f(13),
           fill=(255, 255, 255, 160))
    d.text((24, H - 36), "SENTINEL-2 · 28 AUGUST 2025 · CONTAINS MODIFIED COPERNICUS SENTINEL DATA 2025", font=f(13),
           fill=(255, 255, 255, 120))
    o.save(out, quality=92)
    json.dump({"source": "api.inaturalist.org/v1/observations?sounds=true, box 47.30-47.80 N 34.05-35.10 E",
               "count": len(obs), "recordists": len(users), "years": [min(years), max(years)],
               "licences": sorted(x for x in lic if x), "cell_m": CELL_M, "cells": len(cells),
               "km_to_lines": [round(min(dist) / 1000, 2), round(float(np.median(dist)) / 1000, 2),
                               round(max(dist) / 1000, 2)],
               "ground": {"imagery": IMG, "pass": meta["pass_id"], "north": NORTH, "south": round(south, 4),
                          "m_per_px": round(mpp, 2), "gain": GAIN}}, open(out_json, "w"), indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:6])
