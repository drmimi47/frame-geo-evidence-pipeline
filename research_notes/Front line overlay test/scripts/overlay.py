"""A storyboard still: DeepStateMAP's occupied area over a frame of the zoom-out (NEXT.md N3/storyboard, 5 November 2026).

    python -I overlay.py <frame.png> <deepstate.geojson> <t_s> <label> <out.jpg>

The frame is the zoom-out film's own (film-20261102-221617), its camera read from film.json at second t (north up,
equirectangular about the plant: metres east = dlon * 111320 cos(lat0), north = dlat * 110574, as zoomout.Plane;
metres per pixel = view_km * 1000 / 1920). Only the polygons DeepStateMAP names "Occupied" are drawn: a faint red
over the ground (never over the lines or the text, which keep their own pixels) and a crisp red edge; "Unknown
status" a thin dashed edge. Points (attack directions, units) are left out. A storyboard idea, not a render.
"""

import json
import math
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FILM = "libraries/conductive-seam/satellite/networks/znpp/films/film-20261102-221617/film.json"
RED = np.array([214, 40, 40], np.float32)      # DeepStateMAP's red, approximately
TINT = 0.22
KZ = 110574.0
FONT = "/System/Library/Fonts/HelveticaNeue.ttc"


def camera(t):
    f = json.load(open(FILM))
    c = f["camera"]
    i = {k: n for n, k in enumerate(c["fields"])}
    s = min(c["samples"], key=lambda r: abs(r[0] - t))
    lon0, lat0 = c["centre"]
    return lon0, lat0, s[i["view_km"]] * 1000 / f["width"], s[i["centre_east_km"]] * 1000, s[i["centre_north_km"]] * 1000


def rings(geom):
    if geom["type"] == "Polygon":
        yield geom["coordinates"]
    elif geom["type"] == "MultiPolygon":
        yield from geom["coordinates"]
    elif geom["type"] == "GeometryCollection":
        for g in geom["geometries"]:
            yield from rings(g)


def main(frame_path, gj_path, t, label, out):
    img = np.asarray(Image.open(frame_path).convert("RGB")).astype(np.float32)
    H, W = img.shape[:2]
    lon0, lat0, mpp, cx, cy = camera(float(t))
    kx = 111320.0 * math.cos(math.radians(lat0))

    def px(ring):
        a = np.asarray(ring, np.float64)[:, :2]
        x = W / 2 + ((a[:, 0] - lon0) * kx - cx) / mpp
        y = H / 2 - ((a[:, 1] - lat0) * KZ - cy) / mpp
        return np.round(np.stack([x, y], 1) * 4).astype(np.int32)   # 2 bits of sub-pixel for cv2

    occ, unk = np.zeros((H, W), np.uint8), []
    edges = []
    for f in json.load(open(gj_path))["features"]:
        name = (f.get("properties") or {}).get("name", "")
        g = f.get("geometry") or {}
        for poly in rings(g):
            pts = [px(r) for r in poly]
            if "Occupied" in name:
                cv2.fillPoly(occ, pts, 255, lineType=cv2.LINE_AA, shift=2)
                edges += pts[:1]
            elif "Unknown status" in name or "Contested" in name or "Contensed" in name:
                unk += pts[:1]
    a = occ.astype(np.float32)[..., None] / 255
    # the lines (yellow, bright) and the text (near white) keep their own pixels
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    keep = ((r > 150) & (g > 110) & (b < 0.7 * g)) | ((r > 200) & (g > 200) & (b > 200))
    keep = cv2.dilate(keep.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)[..., None]
    out_img = np.where(keep, img, img + (RED - img) * TINT * a)
    o = Image.fromarray(np.clip(out_img, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(o)
    edge = np.zeros((H, W), np.uint8)
    cv2.polylines(edge, edges, True, 255, 2, cv2.LINE_AA, shift=2)
    o = Image.fromarray(np.where(keep, np.asarray(o), np.asarray(o) * (1 - edge[..., None] / 255 * 0.9)
                                 + RED * (edge[..., None] / 255 * 0.9)).astype(np.uint8))
    d = ImageDraw.Draw(o)
    for p in unk:   # dashed: every other stretch of the ring
        q = (p / 4).tolist()
        for k in range(0, len(q) - 1, 2):
            d.line([tuple(q[k]), tuple(q[k + 1])], fill=(214, 40, 40), width=1)
    font = ImageFont.truetype(FONT, 22, index=0)
    small = ImageFont.truetype(FONT, 16, index=0)
    txt, sub = label.upper(), "AN ASSESSMENT FROM OPEN SOURCES \u00b7 DEEPSTATEMAP.LIVE"
    w = max(d.textlength(txt, font=font), d.textlength(sub, font=small)) + 26
    x0, y0 = W - 40 - w, 34   # top right: the date, count and legend have the top left, the credit the bottom left
    box = Image.new("RGBA", o.size, (0, 0, 0, 0))
    ImageDraw.Draw(box).rectangle([x0 - 10, y0 - 8, W - 30, y0 + 54], fill=(0, 0, 0, 190))
    o = Image.alpha_composite(o.convert("RGBA"), box).convert("RGB")
    d = ImageDraw.Draw(o)
    d.rectangle([x0, y0 + 6, x0 + 18, y0 + 18], fill=(int(RED[0] * 0.6 + 40), 50, 50), outline=(214, 40, 40), width=2)
    d.text((x0 + 26, y0), txt, font=font, fill=(255, 255, 255))
    d.text((x0 + 26, y0 + 31), sub, font=small, fill=(220, 220, 220))
    o.save(out, quality=92)


if __name__ == "__main__":
    main(*sys.argv[1:6])
