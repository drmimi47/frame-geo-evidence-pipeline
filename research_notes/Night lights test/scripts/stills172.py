"""Night lights in the zoom-out's 172 km frame: a legibility test (NEXT.md N2). Usage: stills172.py CROPS_DIR OUT_DIR
The zoom-out as configured, with its later camera moves (the zone's push in, the crossing) left out so the camera stays
at the settled 172 km frame, and the ground at night: the daylight pass dimmed to a faint map and Black Marble's
monthly pixels laid on it as they are (nearest neighbour: each 15" pixel a block, never smoothed or sharpened).
Good-quality pixels only (quality 0); none: a faint dark red. Not part of the film: a test."""
import json, math, sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from image_evidence.satellite import network
from image_evidence.satellite.zoomout import GROUND, KZ, _Film, _day, _hn

CROPS, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
ROOT = Path("libraries/conductive-seam")
DAY_A = 0.22                                  # the daylight pass kept as a faint map under the lights
LIGHT = np.array([255, 246, 228], np.float32)  # a warm white, apart from the lines' yellows
NODATA = np.array([70, 20, 20], np.float32)
TOP = 60.0                                    # nW/cm²/sr at full white (log scale), as the test's maps

# the stills: the month of night lights, and the film's time to show it at (the record's date, or just before it starts)
STILLS = [("2021-09", None, "SEPTEMBER 2021 (BEFORE THE INVASION)"),
          ("2022-09", "2022-09-25", "SEPTEMBER 2022"),
          ("2026-09", "2026-09-11", "SEPTEMBER 2026")]


def lights(ym):
    z = np.load(CROPS / f"{ym}.npz")
    v, q = z["AllAngle_Composite_Snow_Free"].astype(np.float32), z["AllAngle_Composite_Snow_Free_Quality"]
    v[(q != 0) | (v < 0)] = np.nan
    return v, z["lat"], z["lon"], str(z["source"])


class NightFilm(_Film):
    night = None

    def _ground(self, era, lw, camx, camy, mpp, img_a):
        day = super()._ground(era, lw, camx, camy, mpp, img_a)
        if self.night is None:
            return day
        v, lat, lon = self.night
        W, H, p = self.W, self.H, self.plane
        xs = np.arange(W, dtype=np.float32) + 0.5
        ys = np.arange(H, dtype=np.float32) + 0.5
        glon = p.lon0 + (camx + (xs - W / 2) * mpp) / p.kx
        glat = p.lat0 + (camy - (ys - H / 2) * mpp) / KZ
        dlon, dlat = lon[1] - lon[0], lat[1] - lat[0]  # pixel centres; lat runs north to south
        mx = np.broadcast_to(((glon - lon[0]) / dlon)[None, :], (H, W)).astype(np.float32)
        my = np.broadcast_to(((glat - lat[0]) / dlat)[:, None], (H, W)).astype(np.float32)
        val = cv2.remap(np.nan_to_num(v, nan=-1).astype(np.float32), mx, my, cv2.INTER_NEAREST,
                        borderMode=cv2.BORDER_CONSTANT, borderValue=-2)
        out = GROUND + (day - GROUND) * DAY_A
        g = np.clip(np.log10(np.maximum(val, 0) + 1) / math.log10(TOP + 1), 0, 1)[..., None]
        out = out + (LIGHT - out) * g
        out[val == -1] = out[val == -1] * 0.6 + NODATA * 0.4
        return out


cfg = network.config("znpp")
cfg["film"] = {**cfg["film"], "fps": 30, "crossing": None}
cfg["record"] = {**cfg["record"], "zone": {**cfg["record"]["zone"], "view_km": None}}
f = NightFilm(ROOT, cfg)
rec = f.rec
want = {}
for ym, d, title in STILLS:
    t = rec.t(_day(d)) + 0.4 if d else f.settled + 3.0
    want[min(int(round(t * f.fps)), f.n - 1)] = (ym, title)
st = f.state0()
for i in range(max(want) + 1):
    if i not in want:
        f.frame(i, st, draw=False)
        continue
    ym, title = want[i]
    v, lat, lon, src = lights(ym)
    f.night = (v, lat, lon)
    im = f.frame(i, st, draw=True)
    f.night = None
    t, s, hw, *_ = f._view(i)
    img = Image.fromarray(np.clip(im, 0, 255).astype(np.uint8))
    print(ym, "frame", i, "t", round(t, 1), "width km", round(2 * hw / 1000, 1), "date", rec.shown(t), src)
    from PIL import ImageDraw
    dr = ImageDraw.Draw(img, "RGBA")
    font = _hn(round(12 * f.sc), 10)
    txt = [f"NIGHT LIGHTS · NASA BLACK MARBLE VNP46A3 · {title} · MONTHLY, GOOD-QUALITY PIXELS ONLY",
           "DAYLIGHT PASS DIMMED UNDER THEM · DARK RED: NO GOOD-QUALITY VALUE · TEST, NOT IN THE FILM"]
    y = 20 * f.sc
    for line in txt:
        w = dr.textlength(line, font=font)
        x = f.W - 24 * f.sc - w
        dr.rectangle((x - 6, y - 4, x + w + 6, y + 18 * f.sc), fill=(0, 0, 0, 128))
        dr.text((x, y), line, font=font, fill=(255, 255, 255, 255))
        y += 26 * f.sc
    img.save(OUT / f"frame172_{ym}.png")
