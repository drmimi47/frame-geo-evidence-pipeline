"""The zoom-out film: the plant at the centre, north up; the camera pulls back while every line from it grows outward,
named, to the substation where it ends (`network.py`).

- Growth: all lines leave together and grow at one speed in km along the line, so a line's length is when it lands;
  the speed builds exponentially at first (the zoom then reads as steady) and settles as the longest lands.
- The opening (the camera's centre moves with it): on the six units, outlined one by one (OpenStreetMap
  `power=generator` ways); out to the two switchyards while each unit's own 750 kV line is drawn into the plant's
  750 kV switchyard and the links into the thermal plant's 330 kV switchyard (`feeds`, `links`), each switchyard
  outlined as they arrive (white: the plant's inside). Only then do the lines leave, from the switchyards.
- Zoom: then one eased move in log scale toward the frame that holds every line's end, its centre easing onto the
  plant; the lines' growth is held back wherever that frame hasn't opened enough for it. The camera eases into
  `max_view_km` (the Dnipro and the Great Meadow framed) and stays; the lines grow on past its edges.
- Rendered in parts at once, one process a core (`render`): a quick layout pass gives each part the labels' state at its
  start, so the frames are those of one process drawing them in order.
- Smooth: 60 fps; the growth is smoothed looking back only (so it never gets ahead of the frame) and labels and marks
  are placed at sub-pixel positions (`_Overlay`).
- Ground: Sentinel-2 all the way (`network.imagery`: a sharp crop for the close-up over a wide one of the same pass),
  or faded to a dark ground (`imagery_fade_km`), which is not imagery. Two eras (the layers' `era`): a pre-war pass
  until the record reaches `imagery_switch` (the dam's destruction), then a dissolve to the later pass; dimmed by
  one factor (`imagery_gain`) so the lines stand out. The faint lines are the rest of the 750 and
  330 kV grid in the same OpenStreetMap reply, and the towns are GeoNames places (positions for a map, not evidence).
  The Great Meadow is OpenStreetMap's area (`network.sites`), drawn as its outer shore only (`_shoreline`: the channels
  of the drained bed closed, so the outline holds for the reservoir and the river before it), drawn on as the frame
  takes it in.
- Lines in two yellows (`line_rgb` by kV, decided with the user: blue read as rivers): 750 kV the brighter; a lighter core and a faint glow, brightest where they leave the plant and fading toward the substation where they
  end. Every text is white capitals in Helvetica Neue on a black box at half opacity. A line's name rides its tip
  until the tip nears the frame's edge (`label_zone`), then stays at that point of the line while the tip goes on;
  names are kept apart by stacking (a hairline back to the line when moved off it); on landing the length is added
  and the end, when on screen, is ringed.
- The record (`record.py`): once the lines have landed, the date runs from the invasion and each line shows its state
  from dated, sourced reports: lit (yellow, glowing) connected, unlit (a steel-grey hairline) cut off, unlit and dotted
  where lines were cut but the reports don't say which;
  Ferosplavna's two circuits part into two strands. Top left: the date, the IAEA's count of complete losses of
  off-site power, the legend and what happened. The date shown steps from one reported change to the next. The IAEA's
  protection zone (the record's `zone`): a dashed circle round the plant's site while the proposal stood, labelled
  as never agreed (no size was published). Island mode (the record's `island`, 5-10 September 2022: every line cut, a
  reactor powering the plant, not a complete loss) is named under the count. The Hum (`hum.py`) is laid under it, from
  when the camera settles.
- Night lights (`night_lights`, decided with the user, 2 November 2026): at held moments (before the war, during it on a
  day of the record, and at the end, the camera pulled back out to the settled frame) the ground is shown at night: a
  month of NASA's Black Marble laid on the daylight pass dimmed to a faint map, each pixel a block as measured, hatched
  where there is no good-quality value, named top right with why it is dark where a source says.
Pixels of the imagery are only resampled; everything else is drawn, and film.json says what.
"""

from __future__ import annotations

import copy
import csv
import gzip
import hashlib
import json
import logging
import math
import multiprocessing as mp
import os
import shutil
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import date, datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ..layout import write_json
from .corridor import KZ
from .film import _font
from . import hum
from .network import OSM_FILE, network_dir
from .record import Record, _day

log = logging.getLogger(__name__)

GROUND = np.array([11, 11, 12], np.float32)
MEADOW_RGB = np.array([226, 214, 186], np.float32)  # warm white: an area, apart from the lines' blue
# a line's colour by its state in the record (connected: the config's `line_rgb`), and its core; 750 kV the brighter of
# each pair. Light means power (decided with the user, 2 November 2026; before, cut was dark red and unreported grey,
# which vanished on the dark ground, read as roads and clashed with the 3D towers' red paint): connected lines are lit,
# glowing, white-hot at the core; cut lines are unlit, the bare wire: a thin steel-grey hairline with a dark edge (so it
# shows on dark fields and pale sand alike) and no glow; lines not reported line by line the same, dotted (not
# confirmed, as the zone's dashed circle). scene3d/build.py draws the wires the same way.
STEEL_RGB = {750: (200, 204, 210), 330: (172, 176, 182)}
STATE_RGB = {"off": {kv: np.array(c, np.float32) for kv, c in STEEL_RGB.items()},
             "unknown": {kv: np.array(c, np.float32) for kv, c in STEEL_RGB.items()}}
CORE_RGB = {"on": {750: np.array([255, 250, 228], np.float32), 330: np.array([255, 232, 182], np.float32)},
            "off": STATE_RGB["off"], "unknown": STATE_RGB["unknown"]}
STATE_A = {"on": 1.0, "off": 0.9, "unknown": 0.9}
STATE_W = {"on": 1.0, "off": 0.55, "unknown": 0.8}  # of the line's width
STATE_GLOW = {"on": 1.0, "off": 0.0, "unknown": 0.0}
STATE_EDGE = {"on": 0.0, "off": 0.55, "unknown": 0.55}  # an unlit line's dark edge
DOT_PX = (2.4, 5.4)  # an unreported line's dots at 1080p: a dot this long, one every this far
GLOW = {750: (0.95, 0.30), 330: (0.75, 0.22)}  # a connected line's glow: near (3.5 px) and wide (11 px)
PULSE_RGB = np.array([255, 252, 240], np.float32)
NIGHT_RGB = np.array([255, 246, 228], np.float32)  # night lights: a warm white, apart from the lines' yellows
HATCH_RGB = np.array([150, 150, 150], np.float32)  # no good-quality night-light value: a grey hatch (an area, not a line)
FADE_TO = 0.32  # a line's brightness at its end substation, against 1 where it leaves the plant
FADE_LEVELS = 28
BOX_A = 0.5  # every text on a black box at half opacity (but the imagery's credit)
CREDIT_A = 0.6  # the imagery's credit, bottom left: no box, faint
HELVETICA = "/System/Library/Fonts/HelveticaNeue.ttc"
PLACES = Path(__file__).resolve().parents[1] / "data" / "ua_places.tsv.gz"
TOWNS = ("Enerhodar", "Nikopol", "Marhanets", "Melitopol", "Nova Kakhovka", "Kakhovka", "Vasylivka")
MIN_POP = 150_000
STATEMENT = ("The lines, the plant's units and the Great Meadow's outline are OpenStreetMap features, drawn: never seen in "
             "the imagery. The lines are traced to the substations where they end. The daylight imagery is Sentinel-2, a "
             "pre-war pass until the record reaches the dam's destruction, then a dissolve (an interpolation) to a later "
             "pass; only resampled, and dimmed by one factor so the lines stand out (a little more during a complete loss of off-site power). The "
             "faint lines are the rest of the 750 and 330 kV grid in the same reply; the towns are GeoNames places, placed "
             "for reading the map. The lines' states over time are drawn from dated reports (film.json `record`: each event's "
             "dates, its time in the film and its sources), not seen in the imagery. The IAEA's protection zone is a dashed "
             "circle round the plant's site: no size was published, and it was never agreed; on its day the camera closes in on it and "
             "pulls back out with a ring of light spreading from the plant (a drawn mark). Connected lines are drawn lit and "
             "cut ones unlit: a drawing convention, not a measurement of the current. After the "
             "dissolve the camera closes in on the Dnipro crossing, where the plant's last two lines cross the drained bed. "
             "The sound is synthesized "
             "from the record (film.json `sound`), not recorded; it is said here and in film.json, not on screen.")
NIGHT_STATEMENT = (" At held moments the ground is shown at night: NASA's Black Marble monthly night lights (VIIRS, pixels "
                   "of about 500 m, good-quality only, never gap-filled) laid on the daylight pass dimmed to a faint map, each "
                   "pixel a block as measured, hatched where there is no good-quality value (film.json `night_lights`). "
                   "Brightness is not electricity: the satellite shows where it was dark, not why; a reason is given only "
                   "where a source gives one.")


def _night_month(path: Path) -> dict[str, Any]:
    """A month of Black Marble (VNP46A3 crop): the snow-free composite, good-quality pixels only (quality 0; never
    the gap-filled), NaN elsewhere; pixel centres in lon/lat."""
    z = np.load(path)
    v = z["AllAngle_Composite_Snow_Free"].astype(np.float32)
    v[(z["AllAngle_Composite_Snow_Free_Quality"] != 0) | (v < 0)] = np.nan
    return {"v": np.nan_to_num(v, nan=-1.0), "lat": z["lat"].astype(np.float64), "lon": z["lon"].astype(np.float64),
            "granule": str(z["source"]), "file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "no_data_share": round(float(np.isnan(v).mean()), 3)}


def _smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


class Plane:
    """Metres east and north of the plant (equirectangular at the plant's latitude, as the corridors' grids)."""

    def __init__(self, lon0: float, lat0: float):
        self.lon0, self.lat0, self.kx = lon0, lat0, 111320.0 * math.cos(math.radians(lat0))

    def xy(self, coords) -> np.ndarray:
        c = np.asarray(coords, np.float64)
        return np.stack([(c[:, 0] - self.lon0) * self.kx, (c[:, 1] - self.lat0) * KZ], 1)


class Line:
    def __init__(self, d: dict[str, Any], plane: Plane):
        self.d = d
        self.xy = plane.xy(d["coords"])
        self.cum = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(self.xy, axis=0).T))])
        self.length = float(self.cum[-1])
        self.ext_x = np.maximum.accumulate(np.abs(self.xy[:, 0]))  # the farthest the line has reached, east-west
        self.ext_y = np.maximum.accumulate(np.abs(self.xy[:, 1]))
        self.kv = int(d["kv"])
        self.title = f"{d['name']} {self.kv} kV" + (f" · {d['ref']}" if d.get("ref") else "")
        self.right = self.xy[-1, 0] >= 0  # the label's side: the side its end is on

    def upto(self, s: float) -> np.ndarray:
        k = int(np.searchsorted(self.cum, s))
        if k >= len(self.cum):
            return self.xy
        if k == 0:
            return self.xy[:1]
        f = (s - self.cum[k - 1]) / max(1e-9, self.cum[k] - self.cum[k - 1])
        return np.vstack([self.xy[:k], self.xy[k - 1] + (self.xy[k] - self.xy[k - 1]) * f])

    def extent(self, s: float) -> tuple[float, float]:
        """The farthest east-west and north-south the first s metres reach."""
        k = int(np.searchsorted(self.cum, s))
        if k >= len(self.cum):
            return float(self.ext_x[-1]), float(self.ext_y[-1])
        p = self.upto(s)[-1]
        return max(float(self.ext_x[k - 1]) if k else 0.0, abs(p[0])), max(float(self.ext_y[k - 1]) if k else 0.0, abs(p[1]))


def _towns(plane: Plane, half_w: float, half_h: float) -> list[tuple[str, np.ndarray]]:
    out = []
    with gzip.open(PLACES, "rt") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            pop = int(r["population"] or 0)
            if r["fcode"] == "PPLX" or (pop < MIN_POP and not (r["name"] in TOWNS and pop >= 10_000)):
                continue
            p = plane.xy([[float(r["lon"]), float(r["lat"])]])[0]
            if abs(p[0]) < half_w * 0.97 and abs(p[1]) < half_h * 0.95:
                out.append((pop, r["name"], p))
    return [(name, p) for _, name, p in sorted(out, key=lambda x: -x[0])]  # biggest first: they win a clash


def _cap(w: np.ndarray, cap: float, soft: float) -> np.ndarray:
    """Half-widths eased into a cap: unchanged well below it, never above it, with no corner (a smooth minimum in log
    scale, `soft` wide)."""
    d = math.log(cap) - np.log(w)
    return cap * np.exp(-(d + np.sqrt(d * d + soft * soft)) / 2)


def schedule(lines: list[Line], o: dict[str, Any], aspect: float,
             centres: dict[str, tuple[float, float]] | None = None) -> dict[str, np.ndarray]:
    """Per frame: time, distance grown along every line, the frame's half-width and its centre (m from the plant).

    The camera opens at `start_view_km` on `centres["units"]`; with `yards_view_km` it first pulls out to that (between
    `yards_zoom_s`), onto `centres["yards"]`, and holds while the plant's own lines are drawn. Then the lines' frame
    makes one move (smoothstep in log scale) toward the frame that holds every line's end, starting `zoom_lead_s` before
    the lines leave and ending after `zoom_share` of their growth, its centre easing onto the plant by `plant_centre_km`.
    The lines grow at one speed that builds exponentially, held back where that frame hasn't opened enough for them,
    smoothed so the speed never jumps. The camera is that frame, eased into `max_view_km` when it is set: past it, the
    lines grow off screen."""
    fps = int(o["fps"])
    hold, grow, end_hold = float(o["hold_s"]), float(o["grow_s"]), float(o["end_hold_s"])
    n = int(round((hold + grow + end_hold) * fps))
    t = np.arange(n) / fps
    margin = float(o["margin"])
    S = max(ln.length for ln in lines)

    def need(s: float) -> float:
        ex = [ln.extent(s) for ln in lines]
        return margin * max(max(e[0] for e in ex), max(e[1] for e in ex) * aspect)

    cap = float(o["max_view_km"]) * 500 if o.get("max_view_km") else None
    soft = float(o.get("view_cap_soft", 0.35))

    def uncap(w: float) -> float:  # the lines' frame the eased camera shows as w (exact for the opening views)
        if cap is None:
            return w
        dy = math.log(cap / w)
        return cap * math.exp(-(4 * dy * dy - soft * soft) / (4 * dy))

    w0 = float(o["start_view_km"]) * 500  # tight on the plant: the lines wait until the frame has room for them
    wa = float(o["yards_view_km"]) * 500 if o.get("yards_view_km") else None
    w1 = max(float(o["end_view_km"]) * 500, need(S))
    lw = np.full(n, math.log(uncap(w0)))
    if wa:
        a0, a1 = (float(v) for v in o["yards_zoom_s"])
        lw += (math.log(uncap(wa)) - math.log(uncap(w0))) * _smoothstep((t - a0) / (a1 - a0))
    lead = float(o.get("zoom_lead_s", 0.0))  # the camera starts pulling back this long before the lines leave
    x = _smoothstep((t - (hold - lead)) / (grow * float(o.get("zoom_share", 0.7)) + lead))
    lw += (math.log(w1) - math.log(uncap(wa or w0))) * x
    lines_w = np.exp(lw)
    half_w = lines_w
    if cap is not None:  # eased in, and landing on the cap itself by the end
        c = cap
        for _ in range(30):
            c *= cap / float(_cap(lines_w[-1:], c, soft)[0])
        half_w = np.minimum(_cap(lines_w, c, soft), cap)
    # the centre: on the units, then the switchyards, then the plant, as the frame widens
    centre = np.zeros((n, 2))
    if centres:
        keys = [(w0, centres["units"])] + ([(wa, centres["yards"])] if wa else []) + \
               [(float(o.get("plant_centre_km", 30)) * 500, (0.0, 0.0))]
        centre += np.array(keys[0][1], float)
        for (wa_, pa), (wb_, pb) in zip(keys, keys[1:]):
            f = _smoothstep((np.log(half_w) - math.log(wa_)) / (math.log(wb_) - math.log(wa_)))
            centre += (np.array(pb, float) - np.array(pa, float)) * f[:, None]
    cx, cy = centre[:, 0], centre[:, 1]
    u = np.clip((t - hold) / grow, 0, 1)
    a = float(o["accel"])
    planned = S * (np.exp(a * (1 - (1 - u) ** 1.6)) - 1) / (np.exp(a) - 1)  # settles as the longest line lands
    # the farthest the lines may reach in the lines' frame (round its centre), continuous: no steps
    ss = np.linspace(0, S, 4000)
    px = np.array([np.interp(np.minimum(ss, ln.length), ln.cum, ln.xy[:, 0]) for ln in lines])
    py = np.array([np.interp(np.minimum(ss, ln.length), ln.cum, ln.xy[:, 1]) for ln in lines])
    eps = ss * 1e-6  # strictly rising, to interpolate
    hx, hy = lines_w / margin, lines_w / aspect / margin
    allowed = np.minimum.reduce([
        np.interp(hx - cx, -np.minimum.accumulate(px.min(0)) + eps, ss),
        np.interp(cx + hx, np.maximum.accumulate(px.max(0)) + eps, ss),
        np.interp(hy - cy, -np.minimum.accumulate(py.min(0)) + eps, ss),
        np.interp(cy + hy, np.maximum.accumulate(py.max(0)) + eps, ss)])
    s = np.minimum(planned, allowed)
    # smoothed by looking back only (a kernel rising from nothing, about 0.9 s late on average): the growth then never
    # gets ahead of what the frame allows (it only ever widens), and a hold released at once still eases into speed
    tau = np.arange(0, 4 * fps) / fps
    k = tau ** 2 * np.exp(-tau / 0.3)
    s = np.convolve(np.pad(s, (len(k) - 1, 0), mode="edge"), k / k.sum(), mode="valid")
    s = np.maximum.accumulate(np.clip(s, 0, S))
    s[t >= min(hold + grow + 3.5, t[-1])] = S  # (already there: the growth settles with no speed left)
    return {"t": t, "s": s, "half_w": half_w, "lines_half_w": lines_w, "cx": cx, "cy": cy,
            "landed_at": {id(ln): float(t[np.argmax(s >= ln.length - 1.0)]) for ln in lines}}


def _smooth_ramp(v: float, a: float, b: float) -> float:
    """0 below a, 1 above b, eased (both in log scale of the frame's width)."""
    return float(_smoothstep((v - math.log(a)) / (math.log(b) - math.log(a))))


def _text(d: ImageDraw.ImageDraw | None, xy, text: str, font, anchor: str = "lm", fill=(255, 255), track: float = 0.0,
          measure_only: bool = False) -> tuple[float, float, float, float]:
    """Letter-spaced text anchored as PIL anchors (l/m/r, then t/m/b/s); returns its box. Drawn one letter at a time."""
    widths = [font.getlength(c) for c in text]
    w = sum(widths) + track * max(0, len(text) - 1)
    x0 = xy[0] - {"l": 0.0, "m": w / 2, "r": w}[anchor[0]]
    top, bottom = font.getbbox(text or " ", anchor="l" + anchor[1])[1::2]
    box = (x0, xy[1] + top, x0 + w, xy[1] + bottom)
    if d is None or measure_only:
        return box
    x = x0  # every letter on the whole text's baseline (a letter anchored on its own top would sit at its own height)
    base = xy[1] + top - font.getbbox(text or " ", anchor="ls")[1]
    for c, cw in zip(text, widths):
        d.text((x, base), c, font=font, anchor="ls", fill=fill)
        x += cw + track
    return box


def _boxed(items: list[tuple], pad: tuple[float, float]) -> tuple[float, float, float, float]:
    """The box round texts; items are (xy, text, font, anchor, track, opacity)."""
    bs = [_text(None, xy, text, font, anchor, track=track) for xy, text, font, anchor, track, _ in items]
    return (min(b[0] for b in bs) - pad[0], min(b[1] for b in bs) - pad[1],
            max(b[2] for b in bs) + pad[0], max(b[3] for b in bs) + pad[1])


class _Overlay:
    """White marks and boxed labels over a frame, at sub-pixel positions: a label is drawn once (white capitals on a
    black box at half opacity), then moved by resampling, so it glides instead of stepping a pixel at a time."""

    def __init__(self, w: int, h: int):
        self.w, self.h = w, h
        self.sprites: dict = {}
        self.boxes: dict = {}
        self.draw = True  # off: labels are only measured (the layout pass)

    def clear(self) -> None:
        if not self.draw:
            return
        self.p = np.zeros((self.h, self.w), np.float32)  # white, premultiplied
        self.a = np.zeros((self.h, self.w), np.float32)
        self.marks = np.zeros((self.h, self.w), np.uint8)

    @staticmethod
    def _key(items, pad):
        return tuple((xy, text, id(font), anchor, round(track, 3), round(a * 32) / 32)
                     for xy, text, font, anchor, track, a in items), pad

    def measure(self, items, at, pad) -> tuple[float, float, float, float]:
        """The label's box in the frame; items are placed relative to `at`."""
        key = self._key(items, pad)
        if key not in self.boxes:
            self.boxes[key] = _boxed(items, pad)
        b = self.boxes[key]
        return b[0] + at[0], b[1] + at[1], b[2] + at[0], b[3] + at[1]

    def label(self, items, at, op: float, pad, box: bool = True) -> tuple[float, float, float, float]:
        """Texts on a black box at half opacity (or, with box off, the texts alone); returns the box's place."""
        where = self.measure(items, at, pad)
        if op <= 0.004 or not self.draw:
            return where
        key = (self._key(items, pad), box)
        if key not in self.sprites:
            b = self.boxes[key[0]]
            x0, y0 = math.floor(b[0]) - 1, math.floor(b[1]) - 1
            w, h = math.ceil(b[2]) - x0 + 2, math.ceil(b[3]) - y0 + 2
            txt, bg = Image.new("L", (w, h), 0), Image.new("L", (w, h), 0)
            ImageDraw.Draw(bg).rectangle((b[0] - x0, b[1] - y0, b[2] - x0, b[3] - y0), fill=255)
            d = ImageDraw.Draw(txt)
            for xy, text, font, anchor, track, a in items:
                _text(d, (xy[0] - x0, xy[1] - y0), text, font, anchor, round(255 * a), track)
            tm = np.asarray(txt, np.float32) / 255
            ba = np.asarray(bg, np.float32) / 255 * (BOX_A if box else 0.0)
            self.sprites[key] = (x0, y0, np.dstack([tm, tm + ba * (1 - tm)]))
        x0, y0, img = self.sprites[key]
        X, Y = at[0] + x0, at[1] + y0
        ix, iy = math.floor(X), math.floor(Y)
        h, w = img.shape[:2]
        moved = cv2.warpAffine(img, np.array([[1, 0, X - ix], [0, 1, Y - iy]], np.float64), (w + 1, h + 1),
                               flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0) * op
        xa, ya, xb, yb = max(ix, 0), max(iy, 0), min(ix + w + 1, self.w), min(iy + h + 1, self.h)
        if xa < xb and ya < yb:
            src = moved[ya - iy:yb - iy, xa - ix:xb - ix]
            keep = 1 - src[..., 1]
            self.p[ya:yb, xa:xb] = src[..., 0] + self.p[ya:yb, xa:xb] * keep
            self.a[ya:yb, xa:xb] = src[..., 1] + self.a[ya:yb, xa:xb] * keep
        return where

    def dot(self, xy, r: float, op: float, width: int = -1) -> None:
        if not self.draw:
            return
        cv2.circle(self.marks, (round(xy[0] * 16), round(xy[1] * 16)), round(r * 16), round(255 * op), width,
                   cv2.LINE_AA, shift=4)

    def disc(self, xy, r: float, op: float) -> None:
        """A filled circle under what is marked already."""
        if not self.draw:
            return
        d = np.zeros_like(self.marks)
        cv2.circle(d, (round(xy[0] * 16), round(xy[1] * 16)), round(r * 16), round(255 * op), -1, cv2.LINE_AA, shift=4)
        np.maximum(self.marks, d, out=self.marks)

    def arc(self, xy, r: float, a0: float, a1: float, op: float, width: int) -> None:
        """Part of a circle, from angle a0 to a1 (degrees, clockwise from east on screen)."""
        if not self.draw:
            return
        cv2.ellipse(self.marks, (round(xy[0] * 16), round(xy[1] * 16)), (round(r * 16), round(r * 16)), 0, a0, a1,
                    round(255 * op), width, cv2.LINE_AA, shift=4)

    def line(self, p, q, op: float) -> None:
        if not self.draw:
            return
        cv2.line(self.marks, (round(p[0] * 16), round(p[1] * 16)), (round(q[0] * 16), round(q[1] * 16)), round(255 * op), 1,
                 cv2.LINE_AA, shift=4)

    def onto(self, frame: np.ndarray) -> np.ndarray:
        """The marks over the labels, over the frame (in place, in the tiles they touch)."""
        m = self.marks.astype(np.float32) / 255
        p, a = m + self.p * (1 - m), m + self.a * (1 - m)
        ys, xs = np.arange(0, self.h, TILE), np.arange(0, self.w, TILE)
        for ty, tx in zip(*np.nonzero(np.add.reduceat(np.add.reduceat(a > 0, ys, axis=0), xs, axis=1))):
            y0, x0 = ys[ty], xs[tx]
            f = frame[y0:y0 + TILE, x0:x0 + TILE]
            f *= 1 - a[y0:y0 + TILE, x0:x0 + TILE, None]
            f += 255 * p[y0:y0 + TILE, x0:x0 + TILE, None]
        return frame


def _shoreline(rings: list[np.ndarray], close_m: float, res: float = 25.0) -> list[np.ndarray]:
    """The outer edge of an area's rings (metres): merged, inlets narrower than twice close_m closed (the channels in
    a drained bed), holes dropped. What is left is the shore, which holds for the area's earlier states too."""
    allp = np.vstack(rings)
    x0, y0 = allp.min(0) - 3 * close_m - 4 * res
    x1, y1 = allp.max(0) + 3 * close_m + 4 * res
    w, h = int((x1 - x0) / res) + 1, int((y1 - y0) / res) + 1
    m = np.zeros((h, w), np.uint8)
    cv2.fillPoly(m, [(np.stack([(r[:, 0] - x0) / res, (y1 - r[:, 1]) / res], 1) * 16).astype(np.int32) for r in rings],
                 255, cv2.LINE_8, shift=4)
    if close_m > 0:
        k = 2 * round(close_m / res) + 1
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    out = []
    for c in cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[0]:
        if cv2.contourArea(c) * res * res < 1e6:
            continue
        q = c[:, 0].astype(np.float64)
        q = (np.roll(q, 1, 0) + q + np.roll(q, -1, 0)) / 3  # off the pixel stairs
        out.append(np.stack([x0 + q[:, 0] * res, y1 - q[:, 1] * res], 1))
    return out


def _hn(size: int, index: int):
    """Helvetica Neue (0 regular, 10 medium), else the films' font."""
    try:
        return ImageFont.truetype(HELVETICA, size, index=index)
    except OSError:
        return _font(size)


def _hit(a, b) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _prefix(ring: np.ndarray, cum: np.ndarray, f: float) -> np.ndarray:
    """The first share f of a path (by length)."""
    s = f * cum[-1]
    k = int(np.searchsorted(cum, s))
    if k >= len(cum):
        return ring
    if k == 0:
        return ring[:1]
    t = (s - cum[k - 1]) / max(1e-9, cum[k] - cum[k - 1])
    return np.vstack([ring[:k], ring[k - 1] + (ring[k] - ring[k - 1]) * t])


def _beside(px: np.ndarray, d: float) -> np.ndarray:
    """A screen polyline moved d pixels to its left (one circuit of two on the same towers)."""
    g = np.gradient(px, axis=0) if len(px) > 1 else np.zeros_like(px)
    n = np.stack([g[:, 1], -g[:, 0]], 1)
    return px + n / np.maximum(np.hypot(n[:, 0], n[:, 1]), 1e-9)[:, None] * d


TILE = 120  # px: layers are blended only where they touch


def _blend(frame: np.ndarray, a: np.ndarray, rgb, core=None, c: np.ndarray | None = None) -> None:
    """frame (H, W, 3, float32) toward a colour by alpha a (H, W), in place and only in the tiles a touches; the colour
    is rgb, or rgb mixed toward core by c (H, W) when given (a line's lighter core)."""
    H, W = a.shape
    ys, xs = np.arange(0, H, TILE), np.arange(0, W, TILE)
    hit = np.add.reduceat(np.add.reduceat(a > 0, ys, axis=0), xs, axis=1) > 0
    rgb = np.asarray(rgb, np.float32)
    for ty, tx in zip(*np.nonzero(hit)):
        y0, x0 = ys[ty], xs[tx]
        f = frame[y0:y0 + TILE, x0:x0 + TILE]
        aa = a[y0:y0 + TILE, x0:x0 + TILE, None]
        col = rgb if c is None else rgb + (np.asarray(core, np.float32) - rgb) * c[y0:y0 + TILE, x0:x0 + TILE, None]
        f += (col - f) * aa


def _dotted(lay: np.ndarray, pts: np.ndarray, val: int, wd: int, s0: float, sc: float) -> None:
    """A line not reported line by line: dots along it, placed by arc length on screen from the line's start (`s0`
    where this piece begins), so they hold still while the camera does."""
    d = s0 + np.r_[0, np.cumsum(np.hypot(*np.diff(pts, axis=0).T))]
    on, per = DOT_PX[0] * sc, DOT_PX[1] * sc
    segs = []
    for a in np.arange(math.floor(d[0] / per) * per, d[-1], per):
        ss = np.linspace(max(a, d[0]), min(a + on, d[-1]), 3)
        if ss[-1] > ss[0]:
            segs.append((np.stack([np.interp(ss, d, pts[:, 0]), np.interp(ss, d, pts[:, 1])], 1) * 16).astype(np.int32))
    if segs:
        cv2.polylines(lay, segs, False, val, wd, cv2.LINE_AA, shift=4)


def _smoother(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * x * (x * (6 * x - 15) + 10)


def _zoom(sch: dict[str, np.ndarray], p: np.ndarray, half_w: float, k: np.ndarray) -> None:
    """A camera move after the camera has settled: the frame's half-width eased toward `half_w` by k (0..1, in log
    scale) about the point p, which stays where it is on screen."""
    hw0 = sch["half_w"].copy()
    hw = np.exp(np.log(hw0) + k * (math.log(half_w) - np.log(hw0)))
    for key, j in (("cx", 0), ("cy", 1)):
        sch[key] = p[j] + (sch[key] - p[j]) * hw / hw0
    sch["half_w"] = hw


def _path(xy: np.ndarray) -> np.ndarray:
    return np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(xy, axis=0).T))])


def _site_circle(base: Path, ways: list[int], plane: Plane) -> tuple[np.ndarray, float]:
    """The smallest circle round OpenStreetMap ways of the network's saved reply (m from the plant)."""
    els = json.loads((base / "raw" / OSM_FILE).read_text())["reply"]["elements"]
    pts = [plane.xy([(g["lon"], g["lat"]) for g in e["geometry"]]) for e in els
           if e.get("type") == "way" and e.get("id") in ways and e.get("geometry")]
    if len(pts) != len(set(ways)):
        raise ValueError(f"the zone's ways {ways} aren't all in the saved OpenStreetMap reply")
    (x, y), r = cv2.minEnclosingCircle(np.vstack(pts).astype(np.float32))
    return np.array([x, y], np.float64), float(r)


class _Film:
    """The zoom-out set up from its config. Every process that renders a part sets it up the same way, so the parts
    join into the film a single process would make."""

    def __init__(self, root: Path, cfg: dict[str, Any]):
        self.cfg = cfg
        base = self.base = network_dir(root, cfg["id"])
        net = self.net = json.loads((base / "network.json").read_text())
        o = self.o = cfg["film"]
        self.W, self.H = (int(v) for v in o["size"])
        W, H = self.W, self.H
        self.fps = fps = int(o["fps"])
        sc = self.sc = H / 1080
        plane = self.plane = Plane(*net["plant"]["lonlat"])
        lines = self.lines = [Line(d, plane) for d in net["lines"]]
        self.context = [(c["kv"], plane.xy(c["coords"])) for c in net["context"]]
        units = self.units = []
        for u in net.get("units", []):
            xy = plane.xy(u["coords"])
            units.append((u, xy, _path(xy)))
        ucen = self.ucen = np.vstack([xy for _, xy, _ in units]).mean(0) if units else np.zeros(2)
        # the plant's own lines, drawn before the lines leave: each unit's line into the 750 kV switchyard (from the
        # unit), then the links to the thermal plant's 330 kV switchyard (from the plant); each switchyard outlined as
        # they arrive
        staged = self.staged = []
        f0, l0 = float(o.get("feeds_at_s", 7.4)), float(o.get("links_at_s", 10.8))
        for j, d in enumerate(net.get("feeds", [])):
            xy = plane.xy(d["coords"])
            xy = xy if np.hypot(*(xy[0] - ucen)) <= np.hypot(*(xy[-1] - ucen)) else xy[::-1]
            staged.append((xy, _path(xy), f0 + 0.3 * j, f0 + 0.3 * j + 2.2))
        for j, d in enumerate(net["links"]):
            xy = plane.xy(d["coords"])
            xy = xy if np.hypot(*xy[0]) <= np.hypot(*xy[-1]) else xy[::-1]
            staged.append((xy, _path(xy), l0 + 0.4 * j, l0 + 0.4 * j + 2.4))
        yards = self.yards = []
        for key, v in net["origins"].items():
            if not v.get("outline"):
                continue
            xy = plane.xy(v["outline"])
            arrive = [t1 for sxy, _, _, t1 in staged
                      if cv2.pointPolygonTest(xy.astype(np.float32), (float(sxy[-1, 0]), float(sxy[-1, 1])), True) > -150]
            yards.append((key, xy, _path(xy), (max(arrive) - 0.3) if arrive else f0))
        stage_pts = np.vstack([xy for _, xy, _ in units] + [xy for xy, _, _, _ in staged] + [xy for _, xy, _, _ in yards])
        centres = {"units": tuple(ucen), "yards": tuple((stage_pts.min(0) + stage_pts.max(0)) / 2)}
        meadows = self.meadows = []
        for a in net.get("areas", []):
            rings = []
            for xy in _shoreline([plane.xy(r) for r in a["rings"]], float(o.get("meadow_close_m", 500))):
                xy = cv2.approxPolyDP(xy.astype(np.float32)[:, None], 40.0, True)[:, 0].astype(np.float64)  # 40 m: drawn, not read
                k = int(np.argmin(np.hypot(xy[:, 0], xy[:, 1])))  # drawn on from the point nearest the plant
                xy = np.vstack([xy[k:], xy[:k], xy[k:k + 1]])
                rings.append((xy, _path(xy)))
            meadows.append((a, rings, plane.xy([a["label_at"]])[0]))
        rgb = o.get("line_rgb", cfg["trace_rgb"])
        self.colour = {"on": {kv: np.array(rgb[kv] if isinstance(rgb, dict) else rgb, np.float32) for kv in (750, 330)}, **STATE_RGB}
        self.hum = o.get("hum")
        # the camera's schedule, then the film's time: once the camera has settled (and the Hum faded in), the record
        # starts `wait_s` later; the lines still growing off screen then grow faster, so all have landed by then
        sch0 = schedule(lines, {**o, "end_hold_s": float(o["end_hold_s"]) + 300}, W / H, centres)
        hw0 = sch0["half_w"]
        self.settled = float(sch0["t"][int(np.argmax(hw0 >= 0.99 * hw0[-1]))])
        rcfg = cfg.get("record")
        at = float(rcfg["at_s"]) if rcfg else None
        self.warp, self.warp_rate = None, 1.0
        if rcfg and o.get("wait_s") is not None:
            ready = self.settled + (float(self.hum.get("fade_in_s", 4.0)) if self.hum else 0.0)
            at = ready + float(o["wait_s"]) - float(rcfg.get("intro_s", 3.0))
            land = max(sch0["landed_at"].values()) + 1.0  # the last line landed, its length shown
            if land > at:
                self.warp = (ready, at, land)
        # the night lights (NASA Black Marble, decided with the user, 2 November 2026): a month laid on the ground at
        # held moments; one on a day of the record holds the date on that day (the record's `holds`)
        nl = self.night_cfg = o.get("night_lights") or {}
        moments = nl.get("moments") or []
        self.night_fade, night_lead = float(nl.get("fade_s", 1.2)), float(nl.get("lead_s", 0.4))
        if moments and not rcfg:
            raise ValueError("the night lights are placed by the record: the film needs one")
        held = [{"at": m["at"], "s": night_lead + 2 * self.night_fade + float(m["hold_s"]) + 0.3}
                for m in moments if m["at"] not in ("before", "end")]
        # the record: after the lines have landed, the date runs and each line shows its state (`record.py`)
        rec = self.rec = Record({**rcfg, "holds": [*(rcfg.get("holds") or []), *held]}, at) if rcfg else None
        end_m = next((m for m in moments if m["at"] == "end"), None)
        extra = 0.0  # the film runs on past the record's end for the last night: the pull back out, then the hold
        if end_m:
            extra = max(0.0, rec.t1 + night_lead + float(end_m["pull_s"]) + float(end_m["hold_s"])
                        + float(o.get("fade_out_s", 0.0)) - rec.end)
        self.circuits: list[list[tuple[str, int | None]]] = [[] for _ in lines]  # per drawn line: its record names
        for key, (name, kv, *strand) in (rec.lines.items() if rec else []):
            j = next((j for j, ln in enumerate(lines) if ln.d["name"] == name and ln.kv == kv), None)
            if j is None:
                raise ValueError(f"record line {key!r}: no drawn line {name} {kv} kV")
            self.circuits[j].append((key, strand[0] if strand else None))
        self.n = round((rec.end + extra if rec else float(o["hold_s"]) + float(o["grow_s"]) + float(o["end_hold_s"])) * fps)
        self.total = self.n / fps
        tau = np.arange(self.n) / fps
        ts = self._schedule_time(tau)
        sch = self.sch = {k: np.interp(ts, sch0["t"], sch0[k]) for k in ("s", "half_w", "lines_half_w", "cx", "cy")}
        sch["t"] = tau
        sch["landed_at"] = {k: float(np.interp(v, ts, tau)) for k, v in sch0["landed_at"].items()}
        final_hw = float(sch["half_w"][-1])
        self.towns = _towns(plane, final_hw, final_hw * H / W)
        self.settled_w = 2 * final_hw  # the frame's width once the camera has settled (`max_view_km`)
        self.hold, self.grow = float(o["hold_s"]), float(o["grow_s"])
        # the imagery: one or two eras (a pre-war pass until the record reaches `imagery_switch`, then the later one),
        # each a close-up over a wider crop of the same pass
        eras: dict[str, list] = {}
        self.layer_fade = {}  # a close-up's frame widths (m): shown below the first, gone above the second
        self._full: dict[str, np.ndarray] = {}
        for im in cfg["imagery"]:
            ly = json.loads((base / "imagery" / f"{im['name']}.json").read_text())
            eras.setdefault(str(im.get("era", "")), []).append((ly, np.asarray(Image.open(base / ly["file"]).convert("RGB")), ly["grid"]))
            if im.get("fade_km"):
                self.layer_fade[im["name"]] = tuple(float(v) * 1000 for v in im["fade_km"])
        self.eras = list(eras.values())
        self.switch = None
        sw = o.get("imagery_switch")
        if len(self.eras) > 2 or len(self.eras) == 2 and not (sw and rec):
            raise ValueError("two eras of imagery need the film's `imagery_switch` and a record")
        if len(self.eras) == 2:
            ts = rec.t(_day(sw["at"]))  # from the date on (the date shown has reached it), never before
            self.switch = (ts, ts + float(sw.get("dissolve_s", 3.0)))
        self.gain = float(o.get("imagery_gain", 1.0))
        self.loss_dim = float(o.get("loss_dim", 1.0))  # the imagery's brightness during a complete loss, of the usual
        fade = o.get("imagery_fade_km")  # none: the imagery stays all the way out
        self.fade_ab = tuple(float(v) * 1000 for v in fade) if fade else None
        self.close_a, self.close_b = (float(v) * 1000 for v in o.get("close_fade_km", (11, 19)))
        self.meadow_a, self.meadow_b = (float(v) * 1000 for v in o.get("meadow_draw_km", (24, 110)))
        # the IAEA's protection zone (never agreed, no size published): a dashed circle round the plant's site
        z = (cfg.get("record") or {}).get("zone")
        self.zone = None
        if z and rec:
            c, r = _site_circle(base, z["around"], plane)
            self.zone = {"c": c, "r": r, "t0": rec.t(_day(z["from"])),
                         "t1": rec.t(_day(z["until"])) if z.get("until") else math.inf, "cfg": z,
                         "reach": max(float(np.hypot(*(ln.xy - c).T).max()) for ln in lines)}  # the farthest a line goes
        # camera moves once the camera has settled (decided with the user, 22 October 2026). The zone's held moment:
        # the date holds on its day while the camera pushes in until the circle reads at its true size, holds, and pulls
        # back out while a ring of light spreads from the plant. Then, once the imagery has dissolved to the drained bed, a
        # push in on the crossing of the Dnipro, framing the plant's last two lines; it stays there to the end.
        tau = sch["t"]
        self.moment = None
        if self.zone and z.get("view_km"):
            t0 = self.zone["t0"]
            ta = t0 + float(z.get("lead_s", 0.5))
            tb = ta + float(z.get("in_s", 2.4))
            td = t0 + float(z["hold_s"]) - float(z.get("tail_s", 0.6))
            tc = td - float(z.get("out_s", 3.0))
            if not self.settled < ta < tb <= tc < td:
                raise ValueError("the zone's moment needs its hold_s to hold the push in, the hold and the pull out")
            self.moment = (ta, tb, tc, td)
            _zoom(sch, self.zone["c"], float(z["view_km"]) * 500,
                  _smoother((tau - ta) / (tb - ta)) * (1 - _smoother((tau - tc) / (td - tc))))
        self.crossing = None
        cr = o.get("crossing")
        if cr and self.switch:
            ta = self.switch[1] + float(cr.get("after_s", 1.0))
            tb = ta + float(cr["push_s"])
            i = min(int(round(ta * fps)), self.n - 1)
            c0 = np.array([sch["cx"][i], sch["cy"][i]])
            c1 = np.array(cr["centre_km"], float) * 1000
            r = float(cr["view_km"]) * 500 / float(sch["half_w"][i])
            self.crossing = {"t": (ta, tb), "cfg": cr, "labels": []}
            _zoom(sch, (c1 - r * c0) / (1 - r), float(cr["view_km"]) * 500, _smoother((tau - ta) / (tb - ta)))
            for lab in cr.get("labels", []):
                j = next((j for j, cs in enumerate(self.circuits) if any(k == lab["line"] for k, _ in cs)), None)
                if j is None:
                    raise ValueError(f"crossing label: no record line {lab['line']!r}")
                self.crossing["labels"].append((lab, j, lines[j].upto(float(lab["at_km"]) * 1000)[-1]))
        # the night lights' moments: (fade in from, full, fade out from, gone); the last one stays to the end
        self.nights, self.end_pull = [], None
        for m in moments:
            hold = float(m["hold_s"])
            if m["at"] == "before":  # in the full chord, before the date appears
                ready = self.settled + (float(self.hum.get("fade_in_s", 4.0)) if self.hum else 0.0)
                a = ready + night_lead
                win = (a, a + self.night_fade, a + self.night_fade + hold, a + 2 * self.night_fade + hold)
                if win[3] > rec.at:
                    raise ValueError("the night lights before the war need the film's `wait_s` longer")
            elif m["at"] == "end":  # the date stopped: the camera pulls back out to the settled frame, the night fades in
                ta = rec.t1 + night_lead
                pull = float(m["pull_s"])
                i, j = min(int(round(ta * fps)), self.n - 1), min(int(round(rec.at * fps)), self.n - 1)
                c_now, hw_now = np.array([sch["cx"][i], sch["cy"][i]]), float(sch["half_w"][i])
                c_set, hw_set = np.array([sch["cx"][j], sch["cy"][j]]), float(sch["half_w"][j])
                r = hw_set / hw_now
                if abs(1 - r) > 1e-3:  # zooming about the point that lands the frame exactly on the settled one
                    _zoom(sch, (c_set - r * c_now) / (1 - r), hw_set, _smoother((tau - ta) / pull))
                self.end_pull = (ta, ta + pull)
                win = (ta + 0.45 * pull, ta + pull, math.inf, math.inf)
            else:  # on its day of the record, the date held
                d = _day(m["at"])
                a = rec.t(d) + night_lead
                win = (a, a + self.night_fade, a + self.night_fade + hold, a + 2 * self.night_fade + hold)
                k = rec.changes.index(d)
                if k + 1 < len(rec.changes) and win[3] > rec.t(rec.changes[k + 1]) + 1e-6:
                    raise ValueError(f"the night lights of {m['at']} need their day held longer")
            self.nights.append({"m": m, "win": win, **_night_month(root / nl["dir"] / f"{m['month']}.npz")})
        self.lw_max = np.maximum.accumulate(np.log(2 * sch["half_w"]))  # the widest the frame has been

        self.f_label, self.f_small, self.f_plant, self.f_unit = (_hn(round(15 * sc), 10), _hn(round(12 * sc), 10),
                                                                 _hn(round(17 * sc), 10), _hn(round(13 * sc), 10))
        self.f_clock = _hn(round(30 * sc), 10)
        self.trk, self.trk_s = 1.4 * sc, 1.1 * sc
        self.pad, self.pad_s = (7 * sc, 5 * sc), (5 * sc, 4 * sc)
        self.inner = 30 * sc  # labels keep this far inside the frame's edge
        self.zone_lab = [float(v) for v in o.get("label_zone", (0.86, 0.84))]  # a name rides its tip while the tip is this far out
        self.yard_names = o.get("origin_labels") or {}
        self.fade_in, self.fade_out = float(o["fade_in_s"]), float(o["fade_out_s"])
        self.ov = _Overlay(W, H)

    def _schedule_time(self, tau: np.ndarray) -> np.ndarray:
        """The camera schedule's time at film time tau: the same, but faster between the warp's ends (the rate rising
        from 1 and back to 1, no jolt), so the schedule gains what the film skips."""
        if not self.warp:
            return tau.copy()
        a, b, land = self.warp
        xs = np.linspace(0, 1, 4001)
        shape = _smoothstep(xs / 0.3) * (1 - _smoothstep((xs - 0.7) / 0.3))
        cum = np.concatenate([[0.0], np.cumsum((shape[1:] + shape[:-1]) / 2 * np.diff(xs))])
        self.warp_rate = 1 + (land - b) / ((b - a) * cum[-1])  # the fastest, in the middle
        return tau + (self.warp_rate - 1) * (b - a) * np.interp((tau - a) / (b - a), xs, cum)

    def moment_k(self, t: float) -> float:
        """How far into the zone's held moment (0 outside, 1 while held close)."""
        if not self.moment:
            return 0.0
        ta, tb, tc, td = self.moment
        return float(_smoothstep((t - ta) / (tb - ta)) * (1 - _smoothstep((t - tc) / (td - tc))))

    def _pulse(self, frame: np.ndarray, t: float, hw: float, to_px) -> None:
        """A ring of light spreading out from the plant, from the zone's edge past the settled frame's, as the camera
        pulls back (its front keeps pace with the frame): one soft band, a thin bright front and a faint wash fading
        inward behind it. Off the lines (decided with the user, 2 November 2026): a light running along them, as it
        first did, read as power flowing through lines that were all cut."""
        sc = self.sc
        tc, td = self.moment[2], self.moment[3]
        hw_z, hw_s = float(self.zone["cfg"]["view_km"]) * 500, self.settled_w / 2
        r = self.zone["r"]
        front = r * (hw / hw_z) ** (math.log(1.2 * hw_s / r) / math.log(hw_s / hw_z))
        po = float(_smoothstep((t - tc) / 0.3)) * (1 - float(_smoothstep((t - td) / 0.6)))
        if po <= 0:
            return
        c = np.asarray(self.zone["c"], float).reshape(1, 2)
        cp = to_px(c)[0]
        rp = float(np.hypot(*(to_px(c + [[front, 0.0]])[0] - cp)))
        x0, y0 = max(int(cp[0] - rp - 8 * sc), 0), max(int(cp[1] - rp - 8 * sc), 0)
        x1, y1 = min(int(cp[0] + rp + 8 * sc) + 1, self.W), min(int(cp[1] + rp + 8 * sc) + 1, self.H)
        if x1 <= x0 or y1 <= y0:
            return
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        d = np.hypot(xx - cp[0], yy - cp[1])
        tw = 0.22 * rp
        wash = np.clip((d - (rp - tw)) / tw, 0, 1) ** 2 * (d <= rp) * 0.28
        a = np.zeros((self.H, self.W), np.float32)
        a[y0:y1, x0:x1] = np.maximum(wash, np.exp(-((d - rp) / (1.3 * sc)) ** 2))
        _blend(frame, np.clip(a, 0, 1) * po * 0.8, PULSE_RGB)

    def ease(self, k: float) -> float:
        return 1 - (1 - k) ** (24 / self.fps)  # per-frame easing tuned at 24 fps, the same in time at any rate

    def night_at(self, t: float) -> tuple[dict[str, Any] | None, float]:
        """The night lights' moment at t and how far it has faded in (0 outside every moment)."""
        for n in self.nights:
            a, b, c, d = n["win"]
            if a < t < d:
                w = float(_smoothstep((t - a) / (b - a)))
                if math.isfinite(d):
                    w *= 1 - float(_smoothstep((t - c) / (d - c)))
                return n, w
        return None, 0.0

    def pull_k(self, t: float) -> float:
        """How far the last pull back out has gone (0 before it)."""
        if not self.end_pull:
            return 0.0
        a, b = self.end_pull
        return float(_smoothstep((t - a) / (0.4 * (b - a))))

    def _night(self, day: np.ndarray, n: dict[str, Any], camx: float, camy: float, mpp: float) -> np.ndarray:
        """The ground at night: the daylight dimmed to a faint map, the month's night-light pixels on it as they are
        (nearest neighbour: each pixel a block, never smoothed or sharpened), hatched where there is no good-quality
        value (fixed to the ground, one stripe every two pixels)."""
        W, H, p = self.W, self.H, self.plane
        glon = p.lon0 + (camx + (np.arange(W) + 0.5 - W / 2) * mpp) / p.kx
        glat = p.lat0 + (camy - (np.arange(H) + 0.5 - H / 2) * mpp) / KZ
        lon, lat = n["lon"], n["lat"]
        mx = np.broadcast_to(((glon - lon[0]) / (lon[1] - lon[0]))[None, :], (H, W)).astype(np.float32)
        my = np.broadcast_to(((glat - lat[0]) / (lat[1] - lat[0]))[:, None], (H, W)).astype(np.float32)
        val = cv2.remap(n["v"], mx, my, cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=-2)
        out = GROUND + (day - GROUND) * float(self.night_cfg.get("day_a", 0.22))
        top = float(self.night_cfg.get("top", 60.0))
        out += (NIGHT_RGB - out) * np.clip(np.log10(np.maximum(val, 0) + 1) / math.log10(top + 1), 0, 1)[..., None]
        hatch = (val == -1) & (np.mod((mx + my) / 2, 1.0) < 0.14)
        out[hatch] += (HATCH_RGB - out[hatch]) * 0.45
        return out

    def state0(self) -> dict[str, Any]:
        """What carries from frame to frame (labels easing, names parked, towns fading): a part starts from a copy."""
        nl = len(self.lines)
        return {"offsets": [0.0] * nl, "flipped": set(), "shown": [0.0] * nl, "parked": {}, "last_in": {},
                "towns": {name: 0.0 for name, _ in self.towns}}

    def era_w(self, t: float) -> float:
        """How far the imagery has dissolved from the first era to the second."""
        if not self.switch:
            return 0.0
        a, b = self.switch
        return float(_smoothstep((t - a) / (b - a)))

    @staticmethod
    def _passes(era, sensor: bool = True) -> str:
        return " · ".join(f"{sen + ' · ' if sensor else ''}{datetime.fromisoformat(day):%-d %B %Y}" for sen, day in
                          sorted({(ly["sensor"], ly["acquired"][:10]) for ly, _, _ in era}))

    @staticmethod
    def _atts(eras) -> str:
        """The passes' attributions, one line per wording ("... data 2021, 2025")."""
        by: dict[str, list[str]] = {}
        for era in eras:
            for ly, _, _ in era:
                head, _, year = ly["attribution"].rpartition(" ")
                (by.setdefault(head, []).append(year) if year.isdigit() else by.setdefault(ly["attribution"], []))
        return "; ".join(f"{h} {', '.join(sorted(set(y)))}".strip() for h, y in by.items())

    def credit(self, t: float) -> list[tuple]:
        """Bottom left, the whole film: the satellite imagery's credit only (decided with the user: no other text there;
        the lines' and towns' sources and the record's are in film.json)."""
        w = self.era_w(t)
        if 0 < w < 1:
            a, b = self.eras[0], self.eras[-1]
            same = {ly["sensor"] for ly, _, _ in a} == {ly["sensor"] for ly, _, _ in b}
            img = f"{self._passes(a)} DISSOLVING TO {self._passes(b, sensor=not same)} · {self._atts([a, b])}"
        else:
            era = self.eras[-1] if w >= 1 else self.eras[0]
            img = f"{self._passes(era)} · {self._atts([era])}"
        return [((0, 0), img.upper(), self.f_small, "lb", self.trk_s, 1.0)]

    def _ground(self, era, lw: float, camx: float, camy: float, mpp: float, img_a: float) -> np.ndarray:
        """The daylight: the wider pass, the sharp ones over it on the close-up (screen -> imagery is linear in
        lon/lat); a close-up only where it has pixels."""
        W, H, plane = self.W, self.H, self.plane
        frame = np.broadcast_to(GROUND, (H, W, 3)).astype(np.float32)
        for k, (ly, img, g) in enumerate(reversed(era)):
            a = img_a * (1.0 if k == 0 else 1 - _smooth_ramp(lw, *self.layer_fade.get(ly["name"], (self.close_a, self.close_b))))
            if a <= 0:
                continue
            gw_, gs_, ge_, gn_ = g["bbox"]
            ax = mpp / plane.kx / (ge_ - gw_) * g["width"]
            bx = (plane.lon0 + (camx - W / 2 * mpp) / plane.kx - gw_) / (ge_ - gw_) * g["width"]
            ay = mpp / KZ / (gn_ - gs_) * g["height"]
            by = (gn_ - plane.lat0 - (camy + H / 2 * mpp) / KZ) / (gn_ - gs_) * g["height"]
            M = np.array([[ax, 0, bx], [0, ay, by]])
            day = cv2.warpAffine(img, M, (W, H),
                                 flags=(cv2.INTER_CUBIC if ax < 1 else cv2.INTER_AREA if ax > 2 else cv2.INTER_LINEAR) | cv2.WARP_INVERSE_MAP,
                                 borderMode=cv2.BORDER_CONSTANT, borderValue=0).astype(np.float32)
            inside = bx >= 0 and by >= 0 and bx + ax * W <= g["width"] and by + ay * H <= g["height"]
            if k > 0 and not inside:  # a close-up over the wider pass only where it has pixels
                full = self._full.setdefault(ly["name"], np.full((g["height"], g["width"]), 255, np.uint8))
                cover = cv2.warpAffine(full, M, (W, H),
                                       flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_CONSTANT,
                                       borderValue=0).astype(np.float32)[..., None] * (a / 255)
                frame += (day - frame) * cover
            elif a >= 1:
                frame = day
            else:
                frame += (day - frame) * a
        return frame

    def _view(self, i: int):
        sch, W = self.sch, self.W
        t, s, hw = float(sch["t"][i]), float(sch["s"][i]), float(sch["half_w"][i])
        lw = math.log(2 * hw)
        img_a = 1 - _smooth_ramp(lw, *self.fade_ab) if self.fade_ab else 1.0
        return t, s, hw, float(sch["cx"][i]), float(sch["cy"][i]), 2 * hw / W, lw, img_a

    def sample(self, i: int) -> list[float]:
        """The camera at frame i, for film.json."""
        t, s, hw, camx, camy, mpp, lw, img_a = self._view(i)
        return [round(t, 2), round(2 * hw / 1000, 2), round(s / 1000, 2), round(img_a, 3),
                round(_smooth_ramp(lw, 30_000, 160_000), 3), round(_smooth_ramp(lw, self.meadow_a, self.meadow_b), 3),
                round(camx / 1000, 3), round(camy / 1000, 3)]

    def frame(self, i: int, st: dict[str, Any], draw: bool = True) -> np.ndarray | None:
        """Frame i, carrying `st` on to the next frame. With draw off only what carries is worked out (the layout
        pass that gives each part its start)."""
        W, H, sc, fps = self.W, self.H, self.sc, self.fps
        lines, rec, ov, sch = self.lines, self.rec, self.ov, self.sch
        f_label, f_small, f_plant, f_unit, f_clock = self.f_label, self.f_small, self.f_plant, self.f_unit, self.f_clock
        trk, trk_s, pad, pad_s = self.trk, self.trk_s, self.pad, self.pad_s
        t, s, hw, camx, camy, mpp, lw, img_a = self._view(i)
        to_px = lambda xy: np.stack([W / 2 + (xy[:, 0] - camx) / mpp, H / 2 - (xy[:, 1] - camy) / mpp], 1)
        pp = to_px(np.zeros((1, 2)))[0]  # the plant on screen
        opening = t < self.settled  # (the camera's later moves close in again: what the opening showed stays its own)
        draw_m = _smooth_ramp(float(self.lw_max[i]), self.meadow_a, self.meadow_b)  # once drawn, the outline stays
        unit_a = (1 - _smooth_ramp(lw, 8_000, 13_000)) if opening else 0.0
        ov.draw = draw
        frame = None
        if draw:
            w = self.era_w(t)
            frame = self._ground(self.eras[-1 if w >= 1 else 0], lw, camx, camy, mpp, img_a)
            if 0 < w < 1:  # a dissolve between the two passes (an interpolation, said in the credit)
                frame = frame * (1 - w) + self._ground(self.eras[-1], lw, camx, camy, mpp, img_a) * w
            night, nw = self.night_at(t)
            if nw > 0:  # the ground at night (a month of Black Marble)
                frame += (self._night(frame, night, camx, camy, mpp) - frame) * nw
            frame -= GROUND  # the imagery dimmed for the lines (one factor, everywhere), more in a complete loss
            frame *= self.gain * (1 - (1 - self.loss_dim) * rec.loss_weight(t) if rec else 1.0)
            frame += GROUND
            # the Great Meadow: drawn on as the frame takes it in, then a faint fill
            for a_, rings, _ in self.meadows:
                if draw_m <= 0:
                    continue
                layer = np.zeros((H, W), np.uint8)
                cv2.polylines(layer, [(to_px(_prefix(xy, cum, draw_m)) * 16).astype(np.int32) for xy, cum in rings], False,
                              255, max(1, round(1.2 * sc)), cv2.LINE_AA, shift=4)
                a = layer.astype(np.float32) / 255 * (0.5 if opening else 0.5 * _smooth_ramp(lw, 14_000, 30_000))
                fill = float(_smoothstep((draw_m - 0.85) / 0.15))
                if fill > 0:
                    fl = np.zeros((H, W), np.uint8)
                    cv2.fillPoly(fl, [(to_px(xy) * 16).astype(np.int32) for xy, _ in rings], 255, cv2.LINE_AA, shift=4)
                    a = np.maximum(a, fl.astype(np.float32) / 255 * 0.045 * fill)
                _blend(frame, a, MEADOW_RGB)
            # the rest of the grid, faint, as the frame widens
            ctx_a = _smooth_ramp(lw, 30_000, 160_000)
            if ctx_a > 0:
                for kv_, alpha in ((330, 0.10), (750, 0.18)):
                    layer = np.zeros((H, W), np.uint8)
                    pts = [(to_px(xy) * 16).astype(np.int32) for k, xy in self.context if (k >= 750) == (kv_ == 750)]
                    cv2.polylines(layer, pts, False, 255, max(1, round(sc)), cv2.LINE_AA, shift=4)
                    _blend(frame, layer.astype(np.float32) / 255 * (alpha * ctx_a), (255, 255, 255))
            # the plant's units, outlined one by one on the close-up
            if unit_a > 0 and self.units:
                layer = np.zeros((H, W), np.uint8)
                for k, (u, xy, cum) in enumerate(self.units):
                    f = float(_smoothstep((t - (2.2 + 0.55 * k)) / 1.1))
                    if f > 0:
                        cv2.polylines(layer, [(to_px(_prefix(xy, cum, f)) * 16).astype(np.int32)], False, 255,
                                      max(1, round(1.4 * sc)), cv2.LINE_AA, shift=4)
                _blend(frame, layer.astype(np.float32) / 255 * (0.92 * unit_a), (245, 245, 245))
            # the plant's own lines into its two switchyards, and the switchyards outlined (white: the plant's inside)
            layer = np.zeros((H, W), np.uint8)
            for xy, cum, t0, t1 in self.staged:
                f = float(_smoothstep((t - t0) / (t1 - t0)))
                if f > 0:
                    cv2.polylines(layer, [(to_px(_prefix(xy, cum, f)) * 16).astype(np.int32)], False, 255,
                                  max(1, round(1.4 * sc)), cv2.LINE_AA, shift=4)
            for _, xy, cum, t0 in self.yards:
                f = float(_smoothstep((t - t0) / 1.2))
                if f > 0:
                    cv2.polylines(layer, [(to_px(_prefix(xy, cum, f)) * 16).astype(np.int32)], False, 255,
                                  max(1, round(1.4 * sc)), cv2.LINE_AA, shift=4)
            if layer.any():
                _blend(frame, layer.astype(np.float32) / 255 * (0.9 * (1 - 0.4 * _smooth_ramp(lw, 20_000, 60_000)) if opening else 0.4),
                       (245, 245, 245))
        # the plant's lines (none until they leave): 750 kV brighter than 330 kV, each fading toward its end
        tips = []  # per line: where its label hangs (its tip, or where it leaves the frame), and whether the tip shows
        drawn = None  # where the plant's lines are, so towns keep off them
        town_on = _smooth_ramp(lw, 28_000, 90_000) if opening else 0.0 if self.moment_k(t) > 0 else 1.0  # (none in the zone's moment)
        if s > 0:
            runs = []  # (layer, brightness, points, width)
            split = float(_smoothstep((t - rec.at) / 1.0)) if rec else 0.0  # two circuits on one row of towers part
            for j, ln in enumerate(lines):
                part = ln.upto(s)
                px = to_px(part)
                tips.append((px[-1], bool(0 <= px[-1, 0] <= W and 0 <= px[-1, 1] <= H)))
                if len(part) < 2:
                    continue
                cu = ln.cum if len(part) == len(ln.cum) else np.append(ln.cum[:len(part) - 1], s)
                mid = (cu[1:] + cu[:-1]) / 2 / ln.length
                q = np.round((1 - (1 - FADE_TO) * mid ** 0.8) * FADE_LEVELS).astype(int)
                cut = np.flatnonzero(np.diff(q)) + 1
                kv = 750 if ln.kv >= 750 else 330
                wd = (2.6 if kv == 750 else 1.7) * sc
                strands = [(0.0, {"on": 1.0})] if not rec or t < rec.at or not self.circuits[j] else \
                    [((0.0 if k is None else (k - 0.5) * 2.6 * sc * split), rec.mix(key, t)) for key, k in self.circuits[j]]
                for off_px, mix in strands:
                    pts_ = _beside(px, off_px) if off_px else px
                    arc = np.r_[0, np.cumsum(np.hypot(*np.diff(pts_, axis=0).T))]  # on screen, from the line's start
                    for st_, w in mix.items():
                        for i0, i1 in zip(np.r_[0, cut], np.r_[cut, len(q)]):
                            runs.append(((kv, st_), q[i0] * w, pts_[i0:i1 + 1], max(1, round(wd * STATE_W[st_])), arc[i0]))
            if draw or town_on > 0 or any(v > 0.01 for v in st["towns"].values()):  # (towns: only when they may show)
                lay_by = {(kv, st_): np.zeros((H, W), np.uint8) for kv in (330, 750) for st_ in ("unknown", "off", "on")}
                for key, lev, pts, wd, s0 in sorted(runs, key=lambda r: r[1]):  # brighter over dimmer where lines cross
                    if key[1] == "unknown":
                        _dotted(lay_by[key], pts, round(255 * lev / FADE_LEVELS), wd, s0, sc)
                    else:
                        cv2.polylines(lay_by[key], [(pts * 16).astype(np.int32)], False, round(255 * lev / FADE_LEVELS),
                                      wd, cv2.LINE_AA, shift=4)
                drawn = cv2.dilate(np.any([m > 0 for m in lay_by.values()], 0).astype(np.uint8), np.ones((5, 5), np.uint8))
                for (kv, st_), lay in (lay_by.items() if draw else ()):  # the 750 kV lines over the 330 kV ones; connected over cut
                    if not lay.any():
                        continue
                    m = lay.astype(np.float32) / 255
                    a = m * 0.97
                    if STATE_GLOW[st_] > 0:  # connected lines glow; cut ones don't
                        g1, g2 = GLOW[kv]
                        a = a + (cv2.GaussianBlur(m, (0, 0), 3.5 * sc) * g1 + cv2.GaussianBlur(m, (0, 0), 11 * sc) * g2) * STATE_GLOW[st_]
                    if STATE_EDGE[st_] > 0:  # unlit lines: a dark edge under them
                        e = cv2.GaussianBlur(cv2.dilate(m, np.ones((3, 3), np.uint8)), (0, 0), 0.8 * sc)
                        _blend(frame, np.clip(e * 1.5, 0, 1) * STATE_EDGE[st_], (0, 0, 0))
                    _blend(frame, np.clip(a, 0, 1) * STATE_A[st_], self.colour[st_][kv], CORE_RGB[st_][kv], m * 0.55)
            # the zone's moment: a ring of light spreads from the plant as the camera pulls back
            if draw and self.moment and self.moment[2] <= t < self.moment[3] + 0.6:
                self._pulse(frame, t, hw, to_px)

        ov.clear()
        cx, cy = float(pp[0]), float(pp[1])
        credit_now = self.credit(t)
        placed = [ov.measure(credit_now, (24 * sc, H - 24 * sc), pad_s)]  # the bottom left is the sources' corner
        swatches = []
        night_y = 24 * sc  # the night lights' label: under the record's caption room (top left, off the lit cities)
        rec_op = float(_smoothstep((t - rec.at) / 1.0)) if rec else 0.0
        if rec_op > 0:  # the record, top left: the date, the count, the legend, what happened
            n_loss, _ = rec.loss_count(t)
            head = "BEFORE THE WAR" if t < rec.t0 else f"{rec.shown(t):%-d %B %Y}".upper()  # steps from change to change
            items = [((0, 0), head, f_clock, "lt", trk, 1.0),
                     ((0, 42 * sc), f"COMPLETE LOSSES OF OFF-SITE POWER: {n_loss}", f_small, "lt", trk_s, 0.9)]
            if rec.on_diesel(t):
                items.append(((0, 62 * sc), "ON DIESEL GENERATORS", f_small, "lt", trk_s, 1.0))
            elif rec.in_island(t):  # every line cut, but not a complete loss: a reactor powers the plant itself
                items.append(((0, 62 * sc), "ISLAND MODE: ONE REACTOR POWERS THE PLANT", f_small, "lt", trk_s, 1.0))
            box = ov.label(items, (24 * sc + pad[0], 24 * sc + pad[1]), rec_op, pad)
            placed.append(box)
            y = box[3] + 8 * sc
            for st_, text in (("on", "CONNECTED TO THE PLANT"), ("off", "CUT OFF"), ("unknown", "NOT REPORTED LINE BY LINE")):
                b = ov.label([((0, 0), " " * 6 + text, f_small, "lt", trk_s, 0.9)], (24 * sc + pad_s[0], y + pad_s[1]),
                             rec_op, pad_s)
                placed.append(b)
                swatches.append((st_, b, rec_op))
                y = b[3] + 4 * sc
            placed.append((0, y, 24 * sc + 680 * sc, y + 60 * sc))  # the caption's room, kept whether or not one shows
            night_y = y + 72 * sc
            cap = rec.caption(t)
            if cap:
                text, d, op = cap
                ov.label([((0, 0), f"{date.fromordinal(d):%-d %B %Y}".upper(), f_small, "lt", trk_s, 0.8),
                          ((0, 18 * sc), text.upper(), f_label, "lt", trk, 1.0)],
                         (24 * sc + pad[0], y + 6 * sc + pad[1]), op * rec_op, pad)
        # the night lights named top left: the month, what the pixels are, why it is dark where a source says
        night, nw = self.night_at(t)
        if nw > 0:
            m = night["m"]
            items = [((0, 0), f"NIGHT LIGHTS · {m['title']}".upper(), f_label, "lt", trk, 1.0),
                     ((0, 22 * sc), "NASA BLACK MARBLE (VIIRS) · THE MONTH'S CLEAR NIGHTS · PIXELS ABOUT 500 M",
                      f_small, "lt", trk_s, 0.85),
                     ((0, 39 * sc), "HATCHED: NO GOOD-QUALITY VALUE", f_small, "lt", trk_s, 0.85)]
            for k, part in enumerate(str(m.get("why", "")).split(" · ") if m.get("why") else []):
                items.append(((0, (60 + 18 * k) * sc), part.upper(), f_small, "lt", trk_s, 1.0))
            placed.append(ov.label(items, (24 * sc + pad[0], night_y + pad[1]), nw, pad))
        # the plant: named above it on the close-up, its units numbered; then a white mark, named to the west
        mark = _smooth_ramp(lw, 16_000, 24_000) if opening else 1.0  # after the title has gone, never both at once
        title_a = float(_smoothstep((t - 0.8) / 1.4)) * (1 - _smooth_ramp(lw, 9_000, 14_000)) if opening else 0.0
        if title_a > 0:
            top = min((to_px(xy)[:, 1].min() for _, xy, _ in self.units), default=cy) - 24 * sc
            ux = float(to_px(self.ucen[None])[0, 0])
            ov.label([((0, 0), "ZAPORIZHZHIA NUCLEAR POWER PLANT", f_plant, "mb", trk, 1.0)], (ux, top), title_a, pad)
        for k, (u, xy, cum) in enumerate(self.units):
            op = unit_a * float(_smoothstep((t - (2.2 + 0.55 * k) - 0.8) / 0.6))
            if op > 0:
                p = to_px(xy)
                ov.label([((0, 0), str(u["ref"]).upper(), f_unit, "rm", 0, 1.0)],
                         (p[:, 0].min() - 10 * sc, p[:, 1].mean()), op, (4 * sc, 3 * sc))
        for key, xy, _, t0 in self.yards:  # the switchyards named while they are large enough to see
            op = float(_smoothstep((t - t0 - 0.6) / 0.6)) * (1 - _smooth_ramp(lw, 9_000, 14_000))
            if op > 0 and self.yard_names.get(key):
                p = to_px(xy)
                at_, anc = ((p[:, 0].mean(), p[:, 1].max() + 12 * sc), "mt") if key.endswith("750") else \
                           ((p[:, 0].mean(), p[:, 1].min() - 12 * sc), "mb")
                placed.append(ov.label([((0, 0), str(self.yard_names[key]).upper(), f_small, anc, trk_s, 1.0)], at_, op, pad_s))
        if mark > 0:
            r = 4.5 * sc
            placed.append(ov.label([((0, 0), "ZAPORIZHZHIA NPP", f_plant, "rm", trk, 1.0)], (cx - 16 * sc, cy), mark, pad))
            ov.dot((cx, cy), r, mark)
            placed.append((cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2))
        # the IAEA's protection zone: a dashed circle round the plant's site while the proposal stood (never agreed;
        # no size was published, so it is drawn round the site, as Grossi described it), named below it to the east
        zn = self.zone
        if zn:
            op = float(_smoothstep((t - zn["t0"]) / 0.8)) * (1 - float(_smoothstep((t - zn["t1"]) / 1.2)))
            if op > 0:
                zc = to_px(zn["c"][None])[0]
                rp = zn["r"] / mpp
                held = self.moment_k(t)  # the zone's held moment: filled faintly, its reach said
                if held > 0:
                    ov.disc(zc, rp, 0.10 * held * op)
                nd = max(10, int(2 * math.pi * rp / (7 * sc)))
                for k in range(nd):
                    ov.arc(zc, rp, 360 * k / nd, 360 * (k + 0.55) / nd, op, max(1, round((1.6 + 0.8 * held) * sc)))
                edge = (zc[0] + rp * math.cos(math.radians(40)), zc[1] + rp * math.sin(math.radians(40)))
                at_ = (edge[0] + 30 * sc + pad[0], edge[1] + 24 * sc + pad[1])
                z = zn["cfg"]
                sub = z["sublabel"].format(km=f"{2 * zn['r'] / 1000:.1f}")
                items = [((0, 0), z["label"].upper(), f_label, "lt", trk, 1.0)]
                for k, part in enumerate(sub.split(" · ")):  # one line each
                    items.append(((0, (22 + 17 * k) * sc), part.upper(), f_small, "lt", trk_s, 0.85))
                if z.get("measure") and held > 0:
                    items.append(((0, (26 + 17 * (len(items) - 1)) * sc), z["measure"].format(km=f"{zn['reach'] / 1000:.0f}").upper(),
                                  f_small, "lt", trk_s, round(held * 16) / 16))
                b = ov.measure(items, at_, pad)
                at_ = (at_[0] - max(0.0, b[2] - (W - self.inner)), at_[1] - max(0.0, b[3] - (H - 60 * sc)))
                box = ov.label(items, at_, op, pad)
                ov.line(edge, (box[0], box[1]), 0.7 * op)
                placed.append(box)
        # the Great Meadow's name, once its outline is mostly drawn
        for a_, rings, at in self.meadows:
            op = float(_smoothstep((draw_m - 0.6) / 0.3))
            if op > 0:
                items = [((0, 0), a_["label"].upper(), f_label, "mb", trk, 1.0)]
                if a_.get("label_local"):
                    items.append(((0, 6 * sc), a_["label_local"].upper(), f_small, "mt", trk_s, 0.8))
                placed.append(ov.label(items, tuple(to_px(at[None])[0]), op, pad))
        # line labels: ride the tip until it nears the frame's edge, then stay at that point of the line (the tip
        # goes on alone); stacked apart, kept inside the frame; the length added on landing
        zone = self.zone_lab
        for j, (ln, (tip, seen)) in enumerate(zip(lines, tips)):
            if j not in st["parked"]:
                if abs(tip[0] - W / 2) <= zone[0] * W / 2 and abs(tip[1] - H / 2) <= zone[1] * H / 2:
                    st["last_in"][j] = s
                else:
                    st["parked"][j] = st["last_in"].get(j, s)
            tx, ty = (float(tip[0]), float(tip[1])) if j not in st["parked"] else \
                tuple(float(v) for v in to_px(ln.upto(st["parked"][j])[-1:])[0])
            dist = math.hypot(tx - cx, ty - cy)
            op = float(_smoothstep((dist - 70 * sc) / (60 * sc))) * _smooth_ramp(lw, 22_000, 40_000)
            op = st["shown"][j] = max(st["shown"][j], op)  # once named, a line stays named
            if not opening:  # (but not while the camera closes in again: their names are out at the frame's edge)
                op *= 1 - float(_smoothstep((self.settled_w / (2 * hw) - 1) / 0.08))
            if op <= 0:
                continue
            landed = s >= ln.length - 1.0
            title = f"{ln.d['name']}  {ln.kv} kV".upper() + (f"  {ln.d['ref']}".upper() if ln.d.get("ref") else "")
            km = f"{ln.length / 1000:.0f} KM"
            tw = _text(None, (0, 0), title, f_label, "lm", track=trk)[2] + 2 * pad[0]
            if ln.right and tx + 12 * sc + tw > W - 20 * sc or not ln.right and tx - 12 * sc - tw < 20 * sc:
                st["flipped"].add(j)  # no room on its side: the other side, from then on
            right = ln.right != (j in st["flipped"])
            anchor = "lm" if right else "rm"
            lab_x = tx + ((12 * sc + pad[0]) if right else -(12 * sc + pad[0]))
            items = lambda k=0.0: [((0, 0), title, f_label, anchor, trk, 1.0),
                                   ((0, 12 * sc), km, f_small, "lt" if right else "rt", trk_s, k)]
            sgn = -1 if ty > H - 120 * sc else 1 if ty < 120 * sc else (1 if ty >= cy else -1)
            lo, hi = self.inner + 6 * sc, H - self.inner - 22 * sc
            want = 0.0
            for _ in range(6):  # room for the length too, from the start
                if not any(_hit(ov.measure(items(), (lab_x, min(max(ty + want, lo), hi)), pad), p) for p in placed):
                    break
                want += 26 * sc * sgn
            st["offsets"][j] += (want - st["offsets"][j]) * self.ease(0.12)
            y = min(max(ty + st["offsets"][j], lo), hi)
            if abs(y - ty) > 8 * sc:  # a hairline from the label back to its line
                ov.line((tx, ty), (lab_x - (pad[0] if right else -pad[0]), y), 0.65 * op)
            k = float(_smoothstep((t - sch["landed_at"][id(ln)]) / 0.8)) if landed else 0.0
            placed.append(ov.label(items(k) if landed else items()[:1], (lab_x, y), op, pad))
            ex_, ey_ = float(tip[0]), float(tip[1])  # the line's own end: the ring marks it, wherever the name is
            if seen and landed:
                ov.dot((ex_, ey_), 4.5 * sc * (0.6 + 0.4 * k), k, max(1, round(sc)))
                placed.append((ex_ - 8 * sc, ey_ - 8 * sc, ex_ + 8 * sc, ey_ + 8 * sc))
            elif seen:
                ov.dot((ex_, ey_), 2.4 * sc, 0.9 * op)
        # the crossing: the last two lines named where they cross the drained bed, with their state
        if self.crossing:
            ta, tb = self.crossing["t"]
            op = float(_smoothstep((t - (ta + 0.6 * (tb - ta))) / (0.4 * (tb - ta)))) * (1 - self.pull_k(t))
            for lab, j, at in (self.crossing["labels"] if op > 0 else ()):
                ln = lines[j]
                x, y = (float(v) for v in to_px(at[None])[0])
                right = lab.get("side", "right") == "right"
                state = {"on": "CONNECTED", "off": "CUT OFF", "unknown": "NOT REPORTED"}[rec.state(lab["line"], t)]
                anc = "lm" if right else "rm"
                lx = x + (14 * sc + pad[0]) * (1 if right else -1)
                items = [((0, 0), f"{lab.get('name', ln.d['name'])}  {ln.kv} kV".upper(), f_label, anc, trk, 1.0),
                         ((0, 13 * sc), f"{lab['note']} · {state}".upper(), f_small, "lt" if right else "rt", trk_s, 0.9)]
                placed.append(ov.label(items, (lx, y), op, pad))
        # towns, never over another label or the plant's lines (the biggest first)
        for name, p in self.towns:
            x, y = (float(v) for v in to_px(p[None])[0])
            item = [((0, 0), name.upper(), f_small, "mt", trk_s, 1.0)]
            box = ov.measure(item, (x, y + 9 * sc), pad_s)
            box = (box[0], y - 3 * sc, box[2], box[3])
            clash = any(_hit(box, b) for b in placed)
            if not clash and drawn is not None:
                bx = [min(max(int(v), 0), m_) for v, m_ in zip(box, (W, H, W, H))]
                clash = bool(drawn[bx[1]:bx[3], bx[0]:bx[2]].any())
            st["towns"][name] += ((0.0 if clash else town_on) - st["towns"][name]) * self.ease(0.1)
            if not clash and st["towns"][name] > 0.01:
                placed.append(box)
            if st["towns"][name] > 0.01 and box[0] > 0 and box[2] < W and box[1] > 0 and box[3] < H:
                op = st["towns"][name] * 0.85
                ov.dot((x, y), 1.8 * sc, 0.9 * op)
                ov.label(item, (x, y + 9 * sc), op, pad_s)
        if not draw:
            return None
        # the imagery's credit, small, bottom left: no box, faint (decided with the user: not to draw the eye)
        ov.label(credit_now, (24 * sc, H - 24 * sc), CREDIT_A * img_a, pad_s, box=False)
        frame = ov.onto(frame)
        for st_, b, op in swatches:  # the legend's colours (750 kV over 330 kV), in the room left for them
            x0, y0, x1, y1 = int(b[0]), int(b[1]), int(b[0] + pad_s[0] + 24 * sc), int(b[3]) + 1
            ym = (b[1] + b[3]) / 2 - y0
            roi = frame[y0:y1, x0:x1]
            for kv, dy in ((750, -2.2 * sc), (330, 2.2 * sc)):
                lay = np.zeros(roi.shape[:2], np.uint8)
                cv2.line(lay, (round((pad_s[0] + 1 * sc) * 16), round((ym + dy) * 16)),
                         (round((pad_s[0] + 16 * sc) * 16), round((ym + dy) * 16)), 255,
                         max(2 if st_ == "off" else 1, round((2.6 if kv == 750 else 1.7) * sc * STATE_W[st_])), cv2.LINE_AA, shift=4)
                if st_ == "unknown":  # dotted, as the lines
                    lay[:, np.mod(np.arange(lay.shape[1]) - (pad_s[0] + 1 * sc), DOT_PX[1] * sc) > DOT_PX[0] * sc] = 0
                m = lay.astype(np.float32)[..., None] / 255 * op * STATE_A[st_]
                roi = roi * (1 - m) + self.colour[st_][kv] * m
            frame[y0:y1, x0:x1] = roi
        total, fade_in, fade_out = self.total, self.fade_in, self.fade_out
        black = (min(1.0, t / fade_in) if fade_in else 1.0) * (1 - float(_smoothstep((t - (total - fade_out)) / fade_out)) if fade_out else 1.0)
        return np.clip(frame * black, 0, 255).astype(np.uint8)

    def encoder(self, path: Path, threads: int | None = None) -> subprocess.Popen:
        return subprocess.Popen(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{self.W}x{self.H}",
             "-r", str(self.fps), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-tune", "film",
             *(["-threads", str(threads)] if threads else []), "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(path)],
            stdin=subprocess.PIPE)


def _part(root: Path, cfg: dict[str, Any], path: Path, i0: int, i1: int, st: dict[str, Any],
          keep_at: list[int]) -> dict[int, np.ndarray]:
    """Frames i0..i1 into their own video (one process of the parallel render), from the state the layout pass gave."""
    cv2.setNumThreads(1)  # one core a part
    film = _Film(root, cfg)
    ff = film.encoder(path, threads=2)
    keep = {}
    try:
        for i in range(i0, i1):
            frame = film.frame(i, st)
            ff.stdin.write(frame.tobytes())
            if i in keep_at:
                keep[i] = frame
    finally:
        ff.stdin.close()
    if ff.wait() != 0:
        raise RuntimeError(f"ffmpeg failed to encode {path.name}")
    return keep


def _score(film: _Film, cfg: dict[str, Any]) -> tuple[np.ndarray, dict[str, Any]]:
    """The Hum under the film (hum.py): each line panned by where it ends, its crackle swelling with the weather on the
    date shown (the network's `weather`). The full chord fades in once the camera has stopped pulling back (decided
    with the user)."""
    pans, kvs = {}, {}
    for j, ln in enumerate(film.lines):
        end = ln.xy[-1]
        for key, strand in film.circuits[j]:
            pans[key] = float(np.clip(end[0] / max(np.hypot(*end), 1.0), -1, 1)) * 0.8 + \
                        (0.0 if strand is None else (strand - 0.5) * 0.12)
            kvs[key] = ln.kv
    wet, wdoc = hum.weather(cfg.get("weather"), film.base)
    return hum.score(film.rec, pans, kvs, film.total, film.fade_out, start_s=film.settled,
                     fade_in_s=float(film.hum.get("fade_in_s", 4.0)), seed=int(film.hum.get("seed", 50)), wet=wet,
                     weather_doc=wdoc)


def sound_only(root: Path, cfg: dict[str, Any], film_id: str | None = None, backup: Path | None = None) -> dict[str, Any]:
    """The Hum made again and laid under a film already drawn (default: the newest), its picture copied, not
    re-encoded: for a change to the sound alone. Refused if the config no longer gives the film's own timing (its
    length or the record's span). The old sound is copied to `backup` first, if given; film.json's `sound` updated."""
    film = _Film(root, cfg)
    films = sorted((json.loads(p.read_text())["made_at"], p.parent) for p in (film.base / "films").glob("*/film.json"))
    if not films:
        raise FileNotFoundError("no zoom-out film yet")
    out = film.base / "films" / film_id if film_id else films[-1][1]
    doc = json.loads((out / "film.json").read_text())
    rd = doc.get("record") or {}
    if abs(doc["duration_s"] - round(film.total, 2)) > 0.011 or not film.rec or (
            rd.get("film_s") and rd["film_s"] != film.rec.doc()["film_s"]):
        raise RuntimeError(f"{out.name}: the config no longer gives this film's timing ({doc['duration_s']} s against "
                           f"{film.total:.2f} s, or the record's span): render it again instead")
    video = out / doc["files"]["video"]
    x, sound = _score(film, cfg)
    sound["file"] = f"{film.o.get('title', 'hum')}.wav"
    if backup:
        backup.mkdir(parents=True, exist_ok=True)
        for f in (out / sound["file"], video):
            if f.exists():
                shutil.copy2(f, backup / f.name)
    sound["sha256"] = hum.write_wav(out / sound["file"], x)
    tmp = out / f".{video.stem}.sound.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(video), "-i", str(out / sound["file"]),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart",
                    str(tmp)], check=True)
    tmp.replace(video)
    doc["sound"] = {**sound, "remade_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                    "remade": "the sound alone, laid under the same picture (copied, not re-encoded)"}
    doc["files"]["sound"] = sound["file"]
    doc["sha256"] = hashlib.sha256(video.read_bytes()).hexdigest()
    write_json(out / "film.json", doc)
    return {"film_id": out.name, "video": str(video), "wav": str(out / sound["file"])}


def render(root: Path, cfg: dict[str, Any], workers: int | None = None) -> dict[str, Any]:
    """The film, drawn in parts at once (one process a core): a quick layout pass works out what carries from frame to
    frame (labels easing, names parked, towns fading) and starts each part from it, so the frames are those of one
    process drawing them in order; the parts are joined without re-encoding, the Hum laid under them."""
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is needed to encode the film")
    started = time.monotonic()
    film = _Film(root, cfg)
    n, fps, W, H = film.n, film.fps, film.W, film.H
    o, rec, net, lines, sch = film.o, film.rec, film.net, film.lines, film.sch
    # three parts in four cores by default: as fast as one a core on an 8-core M3 (4 of them efficiency cores), in
    # less memory (about 450 MB a part)
    workers = max(1, min(int(workers or o.get("workers") or (os.cpu_count() or 1) * 3 // 4), n // (2 * fps) or 1))
    film_id = "film-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    out = film.base / "films" / film_id
    out.mkdir(parents=True, exist_ok=True)
    bounds = [round(n * k / workers) for k in range(workers + 1)]
    contact_at = sorted({int(round(n * (j + 0.5) / 12)) for j in range(12)})
    parts = [out / f"part-{k:02d}.mp4" for k in range(workers)]
    samples, keep = [], {}
    log.info("Zoom-out: %d frames in %d parts", n, workers)
    st = film.state0()
    with ProcessPoolExecutor(workers, mp_context=mp.get_context("spawn")) as ex:
        futures = {}
        for i in range(n):
            if i in bounds[:-1]:
                k = bounds.index(i)
                futures[ex.submit(_part, root, cfg, parts[k], i, bounds[k + 1], copy.deepcopy(st),
                                  [c for c in contact_at if i <= c < bounds[k + 1]])] = k
            film.frame(i, st, draw=False)
            if i % fps == 0:
                samples.append(film.sample(i))
        log.info("Zoom-out: layout done in %.0f s; the parts are drawing", time.monotonic() - started)
        sound = None
        if film.hum and rec:
            x, sound = _score(film, cfg)
            sound["file"] = f"{o.get('title', 'hum')}.wav"   # the Hum under the film's name, beside it
            sound["sha256"] = hum.write_wav(out / sound["file"], x)
        for f in as_completed(futures):
            keep.update(f.result())
            log.info("Zoom-out: part %d of %d done (%.0f s)", futures[f] + 1, workers, time.monotonic() - started)
    video = out / f"{o.get('title', 'film')}.mp4"   # the file named by the film's title (the user, 2 November 2026)
    (out / "parts.txt").write_text("".join(f"file '{p.name}'\n" for p in parts))
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(out / "parts.txt")]
    if sound:
        cmd += ["-i", str(out / sound["file"]), "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "256k"]
    if subprocess.run(cmd + ["-c:v", "copy", "-movflags", "+faststart", str(video)]).returncode != 0:
        raise RuntimeError("ffmpeg failed to join the parts")
    for p in parts + [out / "parts.txt"]:
        p.unlink()
    cw = 480
    tiles = [cv2.resize(keep[i], (cw, round(cw * H / W)), interpolation=cv2.INTER_AREA) for i in sorted(keep)]
    rows = [np.concatenate(tiles[r:r + 4], 1) for r in range(0, len(tiles) - len(tiles) % 4, 4)]
    Image.fromarray(np.concatenate(rows, 0)).save(out / "contact.webp", "WEBP", quality=85)
    Image.fromarray(keep[sorted(keep)[-2]]).save(out / "poster.webp", "WEBP", quality=88)
    zn = film.zone
    doc = {"schema": "network-film/1", "film_id": film_id, "network_id": net["network_id"], "title": net["name"],
           "made_at": datetime.now().astimezone().isoformat(timespec="seconds"), "duration_s": round(film.total, 2),
           "fps": fps, "width": W, "height": H, "statement": STATEMENT + (NIGHT_STATEMENT if film.nights else ""),
           "options": o,
           "lines": [{"name": ln.d["name"], "kv": ln.kv, "ref": ln.d.get("ref"), "to": ln.d["to"],
                      "length_km": round(ln.length / 1000, 1), "lands_at_s": round(sch["landed_at"][id(ln)], 2),
                      "ways": ln.d["ways"]} for ln in lines],
           "units": [{"ref": u["ref"], "name": u["name"], "osm_way": u["osm_way"]} for u, _, _ in film.units],
           "staging": {"feeds": [d["ways"] for d in net.get("feeds", [])], "links": [d["ways"] for d in net["links"]],
                       "switchyards": {k: v["osm_way"] for k, v in net["origins"].items()},
                       "drawn": "white, before the lines leave: each unit's line into the 750 kV switchyard, the links to "
                                "the thermal plant's 330 kV switchyard, each switchyard outlined as they arrive"},
           "areas": [{"label": a["label"], "osm_relation": a["osm_relation"], "note": a["note"], "rings": len(r),
                      "drawn": "the outer shore only: the relation's outer rings merged, inlets narrower than "
                               f"{2 * float(o.get('meadow_close_m', 500)):.0f} m closed (the channels in the drained bed), "
                               "holes dropped, simplified to 40 m",
                      "drawn_simplified_m": 40} for a, r, _ in film.meadows],
           "imagery": {"eras": [[ly["name"] for ly, _, _ in era] for era in film.eras],
                       "switch": {"at": str(o["imagery_switch"]["at"]), "film_s": [round(v, 2) for v in film.switch],
                                  "shown": "a dissolve between the two passes (an interpolation, never an intermediate "
                                           "date), at the record's date of the dam's destruction"} if film.switch else None,
                       "gain": film.gain, "gain_note": "the imagery's brightness scaled by one factor everywhere, so the "
                                                       "lines stand out; no other change"},
           "time": {"camera_settled_s": round(film.settled, 2),
                    "sped_up": {"film_s": [round(film.warp[0], 2), round(film.warp[1], 2)],
                                "schedule_s": [round(film.warp[0], 2), round(film.warp[2], 2)],
                                "fastest": round(film.warp_rate, 2),
                                "note": "after the camera settles, the lines still growing off screen grow faster so the "
                                        "record starts `wait_s` after the full chord (decided with the user)"}
                    if film.warp else None},
           "record": rec.doc() if rec else None,
           "moves": {"zone": {"film_s": [round(v, 2) for v in film.moment], "view_km": film.zone["cfg"]["view_km"],
                              "drawn": "the camera closes in on the zone's circle about its centre, holds and pulls back "
                                       "out; a ring of white light spreads from the plant, its front keeping pace with the "
                                       "frame (a drawn mark, off the lines: not a flow of power); the date held on the "
                                       "zone's day"}
                     if film.moment else None,
                     "crossing": {"film_s": [round(v, 2) for v in film.crossing["t"]], "view_km": film.crossing["cfg"]["view_km"],
                                  "centre_km": film.crossing["cfg"]["centre_km"],
                                  "labels": [{k: v for k, v in lab.items()} for lab, _, _ in film.crossing["labels"]],
                                  "drawn": "once the imagery has dissolved to the drained bed, the camera closes in on the "
                                           "Dnipro crossing and stays; the last two lines named where they cross, with "
                                           "their state from the record"} if film.crossing else None,
                     "end": {"film_s": [round(v, 2) for v in film.end_pull],
                             "drawn": "the date stopped, the camera pulls back out from the crossing to the settled frame "
                                      "for the last night lights, held to the fade"} if film.end_pull else None,
                     "loss_dim": film.loss_dim,
                     "line_states": "light means power, a drawing convention: connected, lit (the line's colour, glowing, "
                                    "a white-hot core); cut off, unlit (a thin steel-grey hairline with a dark edge, no "
                                    "glow); not reported line by line, unlit and dotted"},
           "zone": {"label": zn["cfg"]["label"], "sublabel": zn["cfg"]["sublabel"], "osm_ways": zn["cfg"]["around"],
                    "centre_east_north_m": [round(v, 1) for v in zn["c"]], "radius_m": round(zn["r"], 1),
                    "film_s": [round(zn["t0"], 2), round(zn["t1"], 2) if math.isfinite(zn["t1"]) else None],
                    "from": str(zn["cfg"]["from"]), "until": str(zn["cfg"].get("until")), "note": zn["cfg"]["note"],
                    "sources": [rec.cfg["sources"][s] for s in zn["cfg"]["src"]]} if zn else None,
           "night_lights": {"product": film.night_cfg.get("product"),
                            "drawn": "the daylight pass dimmed to a faint map, the month's night-light pixels laid on it "
                                     "as they are (nearest neighbour, never smoothed), white at "
                                     f"{film.night_cfg.get('top', 60)} nW/cm²/sr on a log scale; hatched grey where there "
                                     "is no good-quality value (quality 0 only, never gap-filled)",
                            "note": "brightness is not electricity: the satellite shows where it was dark, not why",
                            "moments": [{"month": str(n["m"]["month"]), "at": str(n["m"]["at"]), "title": n["m"]["title"],
                                         "why": n["m"].get("why"),
                                         "film_s": [round(v, 2) if math.isfinite(v) else None for v in n["win"]],
                                         "granule": n["granule"], "file": n["file"], "sha256": n["sha256"],
                                         "no_data_share": n["no_data_share"],
                                         "sources": [film.night_cfg["sources"][k] for k in n["m"].get("src", [])]}
                                        for n in film.nights]} if film.nights else None,
           "sound": sound,
           "camera": {"fields": ["t", "view_km", "grown_km", "imagery_opacity", "grid_opacity", "meadow_drawn", "centre_east_km",
                                 "centre_north_km"],
                      "samples": samples, "centre": net["plant"]["lonlat"], "orientation": "north up",
                      "zoom_share": o.get("zoom_share", 0.7)},
           "sources": {"lines": net["osm"], "sites": net.get("osm_sites"),
                       "imagery": [{k: ly[k] for k in ("name", "pass_id", "sensor", "acquired", "items", "licence", "attribution")}
                                   for era in film.eras for ly, _, _ in era],
                       "towns": "GeoNames (CC BY 4.0), via the project's gazetteer"},
           "render": {"parts": workers, "seconds": round(time.monotonic() - started)},
           "files": {"video": video.name, "poster": "poster.webp", "contact": "contact.webp",
                     **({"sound": sound["file"]} if sound else {})},
           "sha256": hashlib.sha256(video.read_bytes()).hexdigest()}
    write_json(out / "film.json", doc)
    log.info("Zoom-out: %s in %.0f s", film_id, time.monotonic() - started)
    return doc
