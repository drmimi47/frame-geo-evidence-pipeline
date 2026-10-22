"""The Conductive Seam's film: one overhead travelling shot along a corridor's line, made only from its passes.

The camera follows the corridor's camera path (georef.json), the way along the line pointing up the frame (or north
up). Shots, chosen from the passes given (oldest first):
- open, pan (with `opening`): a fade in on a plant with its lines drawn out from it (`opening.py`), then a pan and zoom
  to the line's start;
- hold: still, at the start (without an opening) and the end;
- track: along the line, easing in and out;
- dissolve: still, from one pass to the next (a cross-fade between two dates: an interpolation, never shown as a
  date of its own), at `dissolve_at_km` along the line (else the line is divided evenly);
- inset: still, a supplied image fading in on top of the pass, where `insets` say (the camera zooms in on the way to
  it and out on the way on; the image fades out as it leaves).
Pace: `profile` sets the speed and the frame's ground width at points along the line (eased between them), so the
camera can linger at the crossing and widen and speed up over open country; it slows by itself in bends
(`max_turn_dps`: the frame never turns faster than that).

Every frame is the passes' own pixels resampled (bicubic) onto the frame, or a weighted mix of two passes in a
dissolve; nothing is generated, filled in or sharpened. Where a pass has no data the frame is black. Captions (sensor
and date, small) show on the holds and dissolves; the line can be drawn (`trace`, in `trace_rgb`); the last hold can
fade to black (`fade_out_s`). An inset is a
supplied image as given, only cropped, scaled and placed by its pins (image pixels on OpenStreetMap towers), smaller
than the frame and named in the caption, so it reads as an image laid on the map. `film.json` records each segment's passes and weights, the camera every
second and the overlays shown. The film's frames join the folder's gallery (`film_frames.py`, `gallery`), and
`notes` (`notes.py`) are placed on it for the view to show under it.
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import math
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ..layout import write_json
from . import notes as film_notes
from .corridor import KZ, Grid
from .film_frames import FramePicker
from .opening import FADE_OUT_S as OPENING_FADE_OUT_S, Opening, reply as opening_reply
from .stitch import TileSet
from .store import corridor_dir, pass_title, read_georef, read_passes

log = logging.getLogger(__name__)

DEFAULTS: dict[str, Any] = {"width": 1920, "height": 1080, "fps": 24, "view_m": 6000.0, "speed_mps": 150.0, "hold_s": 6.0,
                            "ease_s": 3.0, "dissolve_s": 6.0, "orient": "travel", "caption": True, "trace": False,
                            "profile": None, "max_turn_dps": 8.0, "dissolve_at_km": None, "trace_rgb": [255, 59, 48],
                            "insets": None, "opening": None, "fade_out_s": 0.0,
                            "notes": None, "gallery": True}
CAPTION_FADE_S = 1.2
INSET_FADE_IN_S, INSET_FADE_OUT_S = 2.0, 4.0
MAX_PIN_RESIDUAL_M = 15.0  # an inset whose pins disagree more than this with a north-up placement is refused
PACE_STEP_M = 5.0
FONTS = ("/System/Library/Fonts/Helvetica.ttc", "/System/Library/Fonts/SFNS.ttf", "/Library/Fonts/Arial.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
STATEMENT = ("Every frame is satellite imagery from the passes listed, resampled onto the frame; in a dissolve, two passes "
             "mixed by the weights given. Nothing is generated, filled in or sharpened. The camera's movement is a path for "
             "viewing along the line: each pass is a single moment, and moving over it shows no change in time.")
INSET_STATEMENT = (" An inset is a supplied image laid on top as given (only cropped, scaled and placed by its pins on "
                   "OpenStreetMap towers) and named in the caption: not satellite imagery from these passes.")


@dataclass
class Shot:
    kind: str            # hold | track | dissolve
    duration: float
    s0: float            # along the line (m)
    s1: float
    a: int               # index of the pass shown (dissolve: from)
    b: int | None = None  # dissolve: to
    end: bool = False    # the last hold (credits)
    inset: int | None = None  # inset: which of o["insets"]


def _eased(t: float, dur: float, ease: float) -> float:
    """Fraction of a track's distance covered at time t: constant speed with cosine ramps at both ends."""
    e = min(ease, dur / 2)
    if dur <= 0:
        return 1.0
    v = 1 / (dur - e)  # the cruising speed (distance 1 over the shot)
    ramp = lambda x: v * (x - e / math.pi * math.sin(math.pi * x / e)) / 2 if e > 0 else 0.0  # distance in the first x s
    if t <= e:
        return ramp(t)
    if t >= dur - e:
        return 1 - ramp(dur - t)
    return ramp(e) + v * (t - e)


def _smooth(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


@dataclass
class Camera:
    along: np.ndarray
    lon: np.ndarray
    lat: np.ndarray
    heading: np.ndarray

    @classmethod
    def from_georef(cls, georef: dict[str, Any]) -> "Camera":
        s = np.array(georef["camera"]["samples"], float)
        return cls(along=s[:, 0], lon=s[:, 1], lat=s[:, 2], heading=s[:, 3])

    @property
    def length(self) -> float:
        return float(self.along[-1])

    def at(self, s: float) -> tuple[float, float, float]:
        return (float(np.interp(s, self.along, self.lon)), float(np.interp(s, self.along, self.lat)),
                float(np.interp(s, self.along, self.heading)))


class Pace:
    """Speed and ground width along the line: the profile's points (km, speed_mps, view_m), eased between them, the
    speed lowered wherever the frame would turn faster than max_turn_dps. `tau` is the time the camera takes to reach
    each point when cruising (the track's eases come on top)."""

    def __init__(self, cam: Camera, o: dict[str, Any]):
        prof = sorted(o.get("profile") or [{"km": 0, "speed_mps": o["speed_mps"], "view_m": o["view_m"]}], key=lambda p: p["km"])
        self.s = np.arange(0, cam.length + PACE_STEP_M, PACE_STEP_M)
        self.s[-1] = cam.length
        km = np.array([p["km"] * 1000 for p in prof])
        ease = lambda key: self._keyed(km, np.array([float(p.get(key, o[key])) for p in prof]))
        speed, self.view = ease("speed_mps"), ease("view_m")
        for z in o.get("insets") or []:  # zoom in on the way to an inset, out on the way on (eased, in proportion)
            at, zi, zo = float(z["at_km"]) * 1000, float(z.get("zoom_in_m", 800)), float(z.get("zoom_out_m", 800))
            wz = np.where(self.s <= at, _smooth((self.s - at + zi) / zi), _smooth((at + zo - self.s) / zo))
            self.view = np.exp(np.log(self.view) * (1 - wz) + math.log(float(z["view_m"])) * wz)
        h = np.interp(self.s, cam.along, cam.heading)
        turn = np.abs(np.gradient(h, self.s))  # degrees per metre
        speed = np.minimum(speed, float(o["max_turn_dps"]) / np.maximum(turn, 1e-9))
        r = int(400 / PACE_STEP_M)  # smooth the slowing, so the camera eases into a bend
        k = np.exp(-0.5 * (np.arange(-3 * r, 3 * r + 1) / r) ** 2)
        speed = np.convolve(np.pad(speed, 3 * r, mode="edge"), k / k.sum(), mode="valid")
        self.speed = np.maximum(speed, 5.0)
        self.tau = np.concatenate([[0], np.cumsum(np.diff(self.s) / ((self.speed[1:] + self.speed[:-1]) / 2))])

    def _keyed(self, at: np.ndarray, val: np.ndarray) -> np.ndarray:
        if len(at) == 1:
            return np.full_like(self.s, val[0], dtype=float)
        out = np.interp(self.s, at, val)
        for (a0, a1), (v0, v1) in zip(zip(at, at[1:]), zip(val, val[1:])):  # eased, not linear, between the points
            m = (self.s >= a0) & (self.s <= a1)
            if a1 > a0:
                out[m] = v0 + (v1 - v0) * _smooth((self.s[m] - a0) / (a1 - a0))
        return out

    def cruise(self, s0: float, s1: float) -> float:
        return float(np.interp(s1, self.s, self.tau) - np.interp(s0, self.s, self.tau))

    def along(self, s0: float, u: float) -> float:
        """The point reached u cruising seconds after s0."""
        return float(np.interp(np.interp(s0, self.s, self.tau) + u, self.tau, self.s))

    def view_at(self, s: float) -> float:
        return float(np.interp(s, self.s, self.view))


def plan(length_m: float, n_passes: int, o: dict[str, Any], pace: Pace) -> list[Shot]:
    stops = [km * 1000 for km in (o.get("dissolve_at_km") or [])][: n_passes - 1]
    if len(stops) != n_passes - 1 or any(not 0 <= a < length_m for a in stops) or stops != sorted(stops):
        stops = [length_m * k / n_passes for k in range(1, n_passes)]
    insets = {float(z["at_km"]) * 1000: i for i, z in enumerate(o.get("insets") or [])}
    if any(not 0 < a < length_m for a in insets):
        raise ValueError("an inset's at_km must lie along the line")
    op = o.get("opening")
    shots = ([Shot("open", float(op["hold_s"]), 0, 0, 0), Shot("pan", float(op["pan_s"]), 0, 0, 0)] if op
             else [Shot("hold", o["hold_s"], 0, 0, 0)])
    s, k = 0.0, 0
    for stop in sorted(set(stops) | set(insets)) + [length_m]:
        if stop > s:
            shots.append(Shot("track", pace.cruise(s, stop) + o["ease_s"], s, stop, k))
        if stop in stops and k < n_passes - 1:
            shots.append(Shot("dissolve", o["dissolve_s"], stop, stop, k, k + 1))
            k += 1
        if stop in insets:  # after a dissolve at the same stop, so the image lies on the later pass
            shots.append(Shot("inset", float(o["insets"][insets[stop]].get("hold_s", 10)), stop, stop, k, inset=insets[stop]))
        s = stop
    shots.append(Shot("hold", o["hold_s"], length_m, length_m, n_passes - 1, end=True))
    return shots


def _opening_view(op: Opening, cam: Camera, pace: Pace, o: dict[str, Any], kind: str, local: float, dur: float,
                  w: int) -> tuple[float, float, float, float]:
    """Camera (lon, lat, heading, metres a pixel) in the opening: held on the plant, turned as the line's start is, then
    eased across to the line's start, zooming to the track's width there."""
    lon1, lat1, h1 = cam.at(0.0)
    h1 = h1 if o["orient"] == "travel" else 0.0
    (lon0, lat0), v0, v1 = op.centre, float(op.cfg["view_m"]), pace.view_at(0.0)
    if kind == "open":
        return lon0, lat0, h1, v0 / w
    f = (1 - math.cos(math.pi * min(1.0, local / dur))) / 2
    return lon0 + (lon1 - lon0) * f, lat0 + (lat1 - lat0) * f, h1, math.exp(math.log(v0) * (1 - f) + math.log(v1) * f) / w


def _matrix(grid: Grid, lon: float, lat: float, heading: float, mpp: float, w: int, h: int) -> np.ndarray:
    """Frame pixel -> grid pixel: the frame's centre at (lon, lat), mpp ground metres a frame pixel, `heading` up. The
    grid is linear in degrees, so metres are turned into its pixels by the local scale where the frame is."""
    cx, cy = grid.to_px(lon, lat)
    w_, s_, e_, n_ = grid.bbox
    sx = grid.width / ((e_ - w_) * 111320.0 * math.cos(math.radians(lat)))  # grid columns per metre east
    sy = grid.height / ((n_ - s_) * KZ)                                       # grid rows per metre north
    c, s = math.cos(math.radians(heading)), math.sin(math.radians(heading))
    return np.array([[sx * mpp * c, -sx * mpp * s, cx - sx * mpp * (c * w / 2 - s * h / 2)],
                     [sy * mpp * s, sy * mpp * c, cy - sy * mpp * (s * w / 2 + c * h / 2)]], np.float64)


def render_view(ts: TileSet, grid: Grid, M: np.ndarray, w: int, h: int) -> tuple[np.ndarray, np.ndarray]:
    """The frame (uint8 RGB) and its data mask: the grid region under the frame read from the pass's tiles, scaled
    down by a whole factor first when the frame shows more than 1.5 grid pixels per frame pixel."""
    corners = M @ np.array([[0, w, 0, w], [0, 0, h, h], [1, 1, 1, 1]], float)
    c0, c1 = int(max(0, math.floor(corners[0].min()) - 4)), int(min(grid.width, math.ceil(corners[0].max()) + 4))
    r0, r1 = int(max(0, math.floor(corners[1].min()) - 4)), int(min(grid.height, math.ceil(corners[1].max()) + 4))
    if c0 >= c1 or r0 >= r1:
        return np.zeros((h, w, 3), np.uint8), np.zeros((h, w), np.float32)
    region = ts.rgb(slice(r0, r1), slice(c0, c1))
    k = math.hypot(M[0, 0], M[1, 0])
    f = max(1, int(math.floor(k))) if k > 1.5 else 1
    if f > 1:
        region = cv2.resize(region, (max(1, (c1 - c0) // f), max(1, (r1 - r0) // f)), interpolation=cv2.INTER_AREA)
    L = M.copy()
    L[0, 2] -= c0
    L[1, 2] -= r0
    L /= f
    img = cv2.warpAffine(region, L, (w, h), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderValue=(0, 0, 0))
    ok = cv2.warpAffine(region.any(axis=2).astype(np.float32), L, (w, h), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                        borderValue=0)
    return img, ok


def _font(size: int):
    for p in FONTS:
        if Path(p).is_file():
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
    return ImageFont.load_default(size)


class Captions:
    """Small text at the bottom left, drawn once per text and blended with an opacity."""

    def __init__(self, w: int, h: int):
        self.w, self.h = w, h
        self.size = max(9, round(h * 0.021))
        self.font, self.small = _font(self.size), _font(max(8, round(self.size * 0.72)))
        self.cache: dict[tuple[str, str], np.ndarray] = {}

    def layer(self, text: str, credit: str = "") -> np.ndarray:
        if (text, credit) not in self.cache:
            im = Image.new("L", (self.w, self.h), 0)
            d = ImageDraw.Draw(im)
            x, y = round(self.h * 0.045), self.h - round(self.h * 0.06) - self.size
            if credit:
                d.text((x, y + round(self.size * 1.5)), credit, font=self.small, fill=150)
                y -= round(self.size * 0.2)
            d.text((x, y), text, font=self.font, fill=225)
            self.cache[(text, credit)] = np.asarray(im, np.float32)[..., None] / 255
        return self.cache[(text, credit)]


class Inset:
    """A supplied image laid on the passes: read from the corridor's insets/ folder as given (its sha256 recorded) and only
    cropped, scaled and placed. Its pins tie image pixels to OpenStreetMap towers in the corridor's saved Overpass reply
    (coordinates from a source that has its own); the placement is a north-up similarity fitted to them by least squares
    (map imagery is north up), each pin's residual recorded and a poor fit refused."""

    def __init__(self, root: Path, corridor_id: str, cfg: dict[str, Any], grid: Grid, nodes: dict[int, dict[str, Any]]):
        self.cfg, self.grid = cfg, grid
        path = corridor_dir(root, corridor_id) / "insets" / cfg["image"]
        if not path.is_file():
            raise ValueError(f"no inset image {cfg['image']!r} in the corridor's insets/ folder")
        data = path.read_bytes()
        self.sha256 = hashlib.sha256(data).hexdigest()
        rgb = np.asarray(Image.open(io.BytesIO(data)).convert("RGB"))
        x0, y0, x1, y1 = (int(v) for v in (cfg.get("crop") or (0, 0, rgb.shape[1], rgb.shape[0])))
        self.crop = (x0, y0, x1, y1)
        self.pixels = np.ascontiguousarray(rgb[y0:y1, x0:x1])
        self.pins = []
        for p in cfg["pins"]:
            node = nodes.get(int(p["osm_node"]))
            if node is None:
                raise ValueError(f"inset pin: OpenStreetMap node {p['osm_node']} is not in the corridor's Overpass reply")
            self.pins.append({"px": [float(v) for v in p["px"]], "osm_node": int(p["osm_node"]), "lon": node["lon"],
                              "lat": node["lat"], "label": p.get("label", "")})
        if len(self.pins) < 2:
            raise ValueError("an inset needs at least two pins")
        lon0, lat0 = float(np.mean([q["lon"] for q in self.pins])), float(np.mean([q["lat"] for q in self.pins]))
        kx = 111320.0 * math.cos(math.radians(lat0))
        A, b = [], []
        for q in self.pins:  # east = m x + tx, north = -m y + ty
            A += [[q["px"][0], 1, 0], [-q["px"][1], 0, 1]]
            b += [(q["lon"] - lon0) * kx, (q["lat"] - lat0) * KZ]
        (m, tx, ty), *_ = np.linalg.lstsq(np.array(A, float), np.array(b, float), rcond=None)
        for q in self.pins:
            q["residual_m"] = round(math.hypot(m * q["px"][0] + tx - (q["lon"] - lon0) * kx,
                                               -m * q["px"][1] + ty - (q["lat"] - lat0) * KZ), 1)
        if max(q["residual_m"] for q in self.pins) > MAX_PIN_RESIDUAL_M:
            raise ValueError(f"inset {cfg['image']!r}: its pins disagree with a north-up placement by up to "
                             f"{max(q['residual_m'] for q in self.pins):.0f} m: check the pins")
        a, c = self.pins[0], self.pins[1]  # the turn a free fit would add: recorded, not applied
        self.turn = math.degrees(math.atan2((c["lat"] - a["lat"]) * KZ, (c["lon"] - a["lon"]) * kx)
                                 - math.atan2(-(c["px"][1] - a["px"][1]), c["px"][0] - a["px"][0]))
        self.m_per_px = float(m)
        to_grid = lambda x, y: grid.to_px(lon0 + (m * x + tx) / kx, lat0 + (-m * y + ty) / KZ)
        g0, gx, gy = (np.array(to_grid(x0 + u, y0 + v)) for u, v in ((0, 0), (1, 0), (0, 1)))
        self.G = np.column_stack([gx - g0, gy - g0, g0])  # crop pixel -> grid pixel
        self.levels: dict[int, np.ndarray] = {1: self.pixels}

    def _to_frame(self, M: np.ndarray) -> np.ndarray:
        inv = cv2.invertAffineTransform(M)  # grid pixel -> frame pixel
        return np.column_stack([inv[:, :2] @ self.G[:, :2], inv[:, :2] @ self.G[:, 2] + inv[:, 2]])

    def draw(self, img: np.ndarray, M: np.ndarray, opacity: float) -> np.ndarray:
        """The image on top at `opacity`: just the image, no frame or marks."""
        h, w = img.shape[:2]
        A = self._to_frame(M)
        k = 1 / math.hypot(A[0, 0], A[1, 0])  # image pixels a frame pixel
        f = max(1, int(math.floor(k))) if k > 1.5 else 1
        if f not in self.levels:
            ph, pw = self.pixels.shape[:2]
            self.levels[f] = cv2.resize(self.pixels, (max(1, pw // f), max(1, ph // f)), interpolation=cv2.INTER_AREA)
        src = self.levels[f]
        Af = A.copy()
        Af[:, :2] *= self.pixels.shape[1] / src.shape[1]
        pic = cv2.warpAffine(src, Af, (w, h), flags=cv2.INTER_CUBIC, borderValue=(0, 0, 0)).astype(np.float32)
        cover = cv2.warpAffine(np.ones(src.shape[:2], np.float32), Af, (w, h), flags=cv2.INTER_LINEAR, borderValue=0)
        a = (cover * opacity)[..., None]
        return img * (1 - a) + pic * a

    def record(self) -> dict[str, Any]:
        return {"image": self.cfg["image"], "sha256": self.sha256, "title": self.cfg.get("title", ""), "credit": self.cfg.get("credit", ""),
                "source": self.cfg.get("source", "supplied; source and date not given"), "crop": list(self.crop),
                "at_km": self.cfg["at_km"], "view_m": self.cfg["view_m"],
                "pins": self.pins, "placement": {
                    "method": "north-up similarity fitted to the pins by least squares (scale and position only)",
                    "m_per_px": round(self.m_per_px, 4), "turn_a_free_fit_would_add_deg": round(self.turn, 2)}}


def _check_coverage(shots: list[Shot], chosen, o: dict[str, Any], pace: Pace) -> None:
    """A pass fetched only for the line's start may only be shown there (with half a frame to spare)."""
    for sh in shots:
        for k in (sh.a, sh.b):
            if k is None or chosen[k].derived.until_m is None:
                continue
            reach = max(sh.s0, sh.s1) + pace.view_at(max(sh.s0, sh.s1)) * 0.3
            if reach > chosen[k].derived.until_m:
                raise ValueError(f"{pass_title(chosen[k])} covers only {chosen[k].derived.coverage}: dissolve to the next pass "
                                 f"before km {max(0.0, (chosen[k].derived.until_m - pace.view_at(0) * 0.3) / 1000):.1f} "
                                 "(dissolve_at_km)")


def render(root: Path, corridor_id: str, pass_ids: list[str] | None = None, options: dict[str, Any] | None = None) -> dict[str, Any]:
    """Render a film into satellite/corridors/<id>/films/<film_id>/ and return its film.json."""
    o = {**DEFAULTS, **(options or {})}
    w, h, fps = int(o["width"]) // 2 * 2, int(o["height"]) // 2 * 2, int(o["fps"])
    georef = read_georef(root, corridor_id)
    if georef is None:
        raise ValueError(f"no corridor {corridor_id!r}: fetch a pass first")
    stored = {p.pass_id: p for p in read_passes(root, corridor_id)}
    if missing := [i for i in (pass_ids or []) if i not in stored]:
        raise ValueError(f"no pass {missing[0]!r} in this corridor")
    chosen = [stored[i] for i in pass_ids] if pass_ids else list(stored.values())
    if not chosen:
        raise ValueError("the corridor has no passes yet")
    chosen.sort(key=lambda p: p.source.acquired_at)
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is needed to encode the film")

    grid = Grid.from_json(georef["grid"])
    cam = Camera.from_georef(georef)
    pace = Pace(cam, o)
    shots = plan(cam.length, len(chosen), o, pace)
    _check_coverage(shots, chosen, o, pace)
    sources = [TileSet(root, p.files, grid, keep=16) for p in chosen]
    caps = Captions(w, h)
    titles = [pass_title(p) for p in chosen]
    credits = " · ".join(dict.fromkeys(p.source.attribution for p in chosen)) + (
        " · Line: © OpenStreetMap contributors" if o["trace"] else "")
    line_px = np.array([grid.to_px(lon, lat) for lon, lat in georef["line"]["coords"]], np.float64)
    trace_rgb = np.array(o["trace_rgb"], np.float32)
    insets: list[Inset] = []
    if o["insets"]:
        reply = json.loads((corridor_dir(root, corridor_id) / "raw" / "osm_power.json").read_text())["reply"]
        nodes = {e["id"]: e for e in reply["elements"] if e["type"] == "node"}
        insets = [Inset(root, corridor_id, z, grid, nodes) for z in o["insets"]]
    opening = None
    if o["opening"]:
        opening = Opening(o["opening"], opening_reply(root, corridor_id, tuple(o["opening"]["box"])), grid, georef["line"]["coords"])

    film_id = datetime.now(timezone.utc).strftime("film-%Y%m%d-%H%M%S")
    out = corridor_dir(root, corridor_id) / "films" / film_id
    out.mkdir(parents=True, exist_ok=True)
    video = out / "film.mp4"
    ff = subprocess.Popen(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
         "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-tune", "film",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(video)], stdin=subprocess.PIPE)

    total = sum(s.duration for s in shots)
    n_frames = int(round(total * fps))
    log.info("Rendering %d frames (%.0f s) along %.1f km", n_frames, total, cam.length / 1000)
    segments, samples, keep = [], [], {}
    contact_at = set(int(round(n_frames * (j + 0.5) / 12)) for j in range(12))
    poster_at = int(round((float(o["opening"]["hold_s"]) - 1 if opening else min(o["hold_s"] * 0.6, total / 2)) * fps))
    t0 = 0.0
    for shot in shots:
        seg = {"t0": round(t0, 3), "t1": round(t0 + shot.duration, 3), "shot": shot.kind,
               "kind": "dissolve" if shot.kind == "dissolve" else "observed",
               "passes": ([{"pass_id": chosen[shot.a].pass_id, "weight": [1, 0]}, {"pass_id": chosen[shot.b].pass_id, "weight": [0, 1]}]
                          if shot.kind == "dissolve" else [{"pass_id": chosen[shot.a].pass_id, "weight": [1, 1]}]),
               "along_m": [round(shot.s0, 1), round(shot.s1, 1)],
               "view_m": [round(pace.view_at(shot.s0)), round(pace.view_at(shot.s1))],
               "label": f"{titles[shot.a]} → {titles[shot.b]}" if shot.kind == "dissolve" else titles[shot.a],
               "overlays": (["caption"] if o["caption"] and shot.kind not in ("track", "pan") else [])
                           + (["trace"] if o["trace"] or opening else []),
               "nodata_share": 0.0}
        if shot.kind == "open":
            seg["overlays"] += [f"fade from black over {float(o['opening']['fade_s']):g} s", "the plant's lines, drawn out from it"]
        elif shot.kind == "pan":
            seg["overlays"].append("the thermal plant's lines, drawn out from it")
        elif segments and segments[-1]["shot"] == "pan":
            seg["overlays"].append(f"the plants' other lines and labels, fading out over {OPENING_FADE_OUT_S:g} s")
        if shot.end and float(o["fade_out_s"] or 0):
            seg["overlays"].append(f"fade to black over the last {float(o['fade_out_s']):g} s")
        if shot.kind == "inset":
            seg["inset"] = o["insets"][shot.inset]["image"]
            seg["overlays"].append("inset")
            insets[shot.inset].cfg["shown"] = [seg["t0"], round(seg["t1"] + INSET_FADE_OUT_S, 3)]
        elif segments and segments[-1]["shot"] == "inset" and shot.kind == "track":
            seg["inset"] = segments[-1]["inset"]
            seg["overlays"].append(f"inset (fading out over {INSET_FADE_OUT_S:g} s)")
        segments.append(seg)
        t0 += shot.duration
    # the held moments kept for the gallery by name (a moving view is kept by overlap)
    key_at: dict[int, str] = {}
    fade_out = float(o["fade_out_s"] or 0)
    first_in = lambda t: min(n_frames - 1, max(0, math.ceil(t * fps - 0.5)))      # the first frame from t on
    last_in = lambda t: min(n_frames - 1, max(0, math.ceil(t * fps - 0.5) - 1))   # the last frame before t
    for sh, sg in zip(shots, segments):
        if sh.kind == "open":
            key_at[last_in(sg["t1"] - 0.4)] = "the opening: the plant's lines drawn"
        elif sh.kind == "pan":
            key_at[last_in(sg["t1"])] = "the end of the pan: the thermal plant's lines drawn"
        elif sh.kind == "dissolve":
            key_at[first_in(sg["t0"])] = "before the dissolve: the earlier pass"
            key_at[last_in(sg["t1"])] = "after the dissolve: the later pass"
        elif sh.kind == "inset":
            key_at[last_in(sg["t1"] - 0.4)] = "the inset at full strength"
        elif sh.end:
            key_at[last_in(sg["t1"] - fade_out - 0.3)] = "the last hold" + (", before the fade to black" if fade_out else "")
    picker = FramePicker(root, out, corridor_id, film_id, w, h) if o["gallery"] else None
    seg_index, last_log = 0, -1
    try:
        for fi in range(n_frames):
            t = (fi + 0.5) / fps
            while seg_index < len(shots) - 1 and t >= segments[seg_index]["t1"]:
                seg_index += 1
            shot, seg = shots[seg_index], segments[seg_index]
            local = t - seg["t0"]
            s = shot.s0
            if shot.kind == "track":
                cruise = shot.duration - o["ease_s"]
                s = pace.along(shot.s0, _eased(local, shot.duration, o["ease_s"]) * cruise)
            if shot.kind in ("open", "pan"):
                lon, lat, heading, mpp = _opening_view(opening, cam, pace, o, shot.kind, local, shot.duration, w)
            else:
                lon, lat, heading = cam.at(s)
                heading = heading if o["orient"] == "travel" else 0.0
                mpp = pace.view_at(s) / w
            M = _matrix(grid, lon, lat, heading, mpp, w, h)
            img, ok = render_view(sources[shot.a], grid, M, w, h)
            wb = 0.0
            on: list[str] = []  # what is drawn on this frame (for the gallery's record)
            inset, inset_op = None, 0.0
            if shot.kind == "inset":
                inset, inset_op = insets[shot.inset], float(_smooth(local / INSET_FADE_IN_S))
            elif seg_index and shots[seg_index - 1].kind == "inset" and local < INSET_FADE_OUT_S:
                inset, inset_op = insets[shots[seg_index - 1].inset], 1 - float(_smooth(local / INSET_FADE_OUT_S))
            plain = shot.kind == "track" and not o["trace"] and inset is None and opening is None
            if not plain:
                img = img.astype(np.float32)
            if shot.kind == "dissolve":
                wb = float(_smooth(local / shot.duration))
                img_b, ok_b = render_view(sources[shot.b], grid, M, w, h)
                img = img * (1 - wb) + img_b.astype(np.float32) * wb
                ok = ok * (1 - wb) + ok_b * wb
            opening_now = opening is not None and (shot.kind in ("open", "pan") or (seg_index == 2 and local < OPENING_FADE_OUT_S))
            if opening_now:
                t_open = sum(x.duration for x in shots[:seg_index]) + local
                others = 1 - float(_smooth(local / OPENING_FADE_OUT_S)) if shot.kind == "track" else 1.0
                img = opening.draw(img, M, t_open, others, trace_rgb)
                on.append("the plants' lines and their labels (OpenStreetMap), drawn in red" if others >= 1 else
                          f"the line (OpenStreetMap), in red; the plants' other lines and labels at {others:.0%}")
                if shot.kind == "open":
                    img = img * float(_smooth(local / float(o["opening"]["fade_s"])))
            elif o["trace"]:
                inv = cv2.invertAffineTransform(M)
                pts = (line_px @ inv[:, :2].T + inv[:, 2]) * 16
                over = np.zeros((h, w), np.uint8)
                cv2.polylines(over, [pts.astype(np.int32)], False, 255, max(1, round(h / 540)), cv2.LINE_AA, shift=4)
                a = over.astype(np.float32)[..., None] / 255 * 0.9
                img = img * (1 - a) + trace_rgb * a
                on.append("the line (OpenStreetMap), drawn in red")
            if inset is not None and inset_op > 0:  # over the line, so the image's own wires show where it lies
                img = inset.draw(img, M, inset_op)
                on.append(f"inset at {inset_op:.0%}: {inset.cfg.get('title') or inset.cfg['image']}")
            if o["caption"] and shot.kind not in ("track", "pan"):
                fade = max(0.0, min(1.0, local / CAPTION_FADE_S, (shot.duration - local) / CAPTION_FADE_S))
                if shot.kind == "open":  # after the fade from black
                    fade = max(0.0, min(1.0, (local - float(o["opening"]["fade_s"])) / CAPTION_FADE_S,
                                        (shot.duration - local) / CAPTION_FADE_S))
                if shot.kind == "dissolve":
                    # one caption at a time: the earlier date goes out over the first half, the later comes in over the second
                    for text, op in ((titles[shot.a], max(0.0, 1 - 2 * wb)), (titles[shot.b], max(0.0, 2 * wb - 1))):
                        a = caps.layer(text) * (op * fade)
                        img = img * (1 - a) + 235 * a
                elif shot.kind == "inset":
                    z = o["insets"][shot.inset]
                    a = caps.layer(z.get("title") or "Supplied image", " · ".join(x for x in (
                        z.get("credit"), f"on {titles[shot.a]}", f"placed by {len(z['pins'])} towers (OpenStreetMap)") if x)) * fade
                    img = img * (1 - a) + 235 * a
                else:
                    a = caps.layer(titles[shot.a], credits if shot.end else "") * fade
                    img = img * (1 - a) + 235 * a
                if fade > 0:
                    on.append("caption" + (" and credits" if shot.end else ""))
            black = 0.0
            if shot.end and fade_out:  # the last seconds fade to black, credits and all
                black = 1 - float(_smooth((shot.duration - local) / fade_out))
                img = img * (1 - black)
            frame = img if plain else np.clip(img + 0.5, 0, 255).astype(np.uint8)
            ff.stdin.write(frame.tobytes())
            nodata = float(1 - ok.mean())
            seg["nodata_share"] = max(seg["nodata_share"], round(nodata, 4))
            if fi % fps == 0:
                samples.append([round(t, 2), round(s, 1), round(lon, 6), round(lat, 6), round(heading % 360, 1),
                                round(mpp, 3), round(wb, 3), round(nodata, 4)])
            if fi in contact_at or fi == poster_at:
                keep[fi] = frame
            if picker is not None:
                eligible = not ((shot.kind == "open" and local < float(o["opening"]["fade_s"]) + 0.5) or shot.kind == "dissolve"
                                or (shot.kind == "inset" and local < INSET_FADE_IN_S) or black > 0)
                if fi in key_at or eligible:
                    picker.offer(frame, M, {
                        "t": round(t, 3), "shot": shot.kind, "kind": seg["kind"],
                        "passes": ([{"pass_id": chosen[shot.a].pass_id, "weight": round(1 - wb, 3)},
                                    {"pass_id": chosen[shot.b].pass_id, "weight": round(wb, 3)}] if shot.kind == "dissolve"
                                   else [{"pass_id": chosen[shot.a].pass_id, "weight": 1.0}]),
                        "along_m": round(s, 1), "camera": {"lon": round(lon, 6), "lat": round(lat, 6),
                                                           "heading_deg": round(heading % 360, 1), "m_per_px": round(mpp, 3),
                                                           "view_m": round(mpp * w)},
                        "overlays": on, "nodata_share": round(nodata, 4)}, key_at.get(fi), eligible)
            if (pct := fi * 10 // n_frames) != last_log:
                last_log = pct
                log.info("Film %d%% (%.1f of %.1f km)", pct * 10, s / 1000, cam.length / 1000)
    finally:
        ff.stdin.close()
    if ff.wait() != 0:
        raise RuntimeError("ffmpeg failed to encode the film")

    Image.fromarray(keep[poster_at]).save(out / "poster.webp", "WEBP", quality=88)
    cw = min(480, w)
    tiles = [cv2.resize(keep[i], (cw, round(cw * h / w)), interpolation=cv2.INTER_AREA) for i in sorted(contact_at) if i in keep]
    rows = [np.concatenate(tiles[r:r + 4] + [np.zeros_like(tiles[0])] * (4 - len(tiles[r:r + 4])), 1) for r in range(0, len(tiles), 4)]
    Image.fromarray(np.concatenate(rows, 0)).save(out / "contact.webp", "WEBP", quality=85)

    views = pace.view
    film = {
        "schema": "film/1", "film_id": film_id, "corridor_id": corridor_id, "corridor": georef["name"],
        "line": {"label": georef["line"]["label"], "length_m": georef["line"]["length_m"]},
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "duration_s": round(n_frames / fps, 3), "fps": fps, "width": w, "height": h,
        "options": {k: v for k, v in o.items() if k != "notes"}, "ground_m_per_px": round(float(views.min()) / w, 3), "ground_m_per_px_max": round(float(views.max()) / w, 3),
        "files": {"video": "film.mp4", "poster": "poster.webp", "contact": "contact.webp",
                  **({"frames": "frames/frames.json"} if picker else {})},
        "gallery_frames": len(picker.frames) if picker else 0,
        "sha256": hashlib.sha256(video.read_bytes()).hexdigest(),
        "passes": [{"pass_id": p.pass_id, "title": pass_title(p), "platform": p.source.platform, "sensor": p.source.sensor,
                    "acquired_at": p.source.acquired_at.isoformat(), "gsd_m": p.source.gsd_m, "coverage": p.derived.coverage,
                    "cloud_share": p.derived.cloud_share, "item_ids": list(p.source.item_ids),
                    "item_urls": list(p.source.item_urls), "attribution": p.source.attribution, "licence": p.source.licence,
                    "alignment": p.derived.alignment.provenance.evidence} for p in chosen],
        "segments": segments,
        "camera": {"fields": ["t", "along_m", "lon", "lat", "heading_deg", "m_per_px", "dissolve_weight", "nodata_share"],
                   "samples": samples, "path": georef["camera"]["smoothing"]},
        "statement": STATEMENT + (INSET_STATEMENT if insets else ""),
        "insets": [z.record() | {"shown_s": z.cfg.get("shown")} for z in insets],
        "opening": opening.record() if opening else None,
        "provenance": [
            {"label": "Imagery", "evidence": "; ".join(f"{pass_title(p)} ({p.derived.coverage}): {', '.join(p.source.item_ids)}"
                                                      for p in chosen) + f". {chosen[0].derived.display}."},
            {"label": "Resampling", "evidence": f"Bicubic, {float(views.min()):.0f}–{float(views.max()):.0f} m across {w} pixels "
             f"({float(views.min()) / w:.1f}–{float(views.max()) / w:.1f} m a pixel) from {min(p.source.gsd_m for p in chosen):g} m "
             "imagery; finer than the imagery's pixels is soft, never sharpened."},
            {"label": "Camera", "evidence": f"Along {georef['line']['label']} ({georef['line']['length_m'] / 1000:.1f} km, OpenStreetMap), "
             f"{'the way along the line up' if o['orient'] == 'travel' else 'north up'}; {georef['camera']['smoothing']}; "
             + (f"pace by the profile ({len(o['profile'])} points: speed and width along the line)" if o["profile"]
                else f"{o['speed_mps']:g} m/s") + f", slowed in bends so the frame turns at most {o['max_turn_dps']:g}° a second, "
             f"{o['ease_s']:g} s eases. A path for viewing, not an observation."},
            {"label": "Dissolves", "evidence": "A cross-fade between two passes at a held stop: an interpolation between two "
             "dates, not imagery of any date between them." if len(chosen) > 1 else "None (one pass)."},
            {"label": "Overlays", "evidence": ("Captions: sensor and date on the holds and dissolves; credits on the last hold. "
             if o["caption"] else "No captions. ") + ("The line: OpenStreetMap's geometry drawn in red, not seen in the imagery."
             if o["trace"] else "The line is not drawn.") + (f" The last {fade_out:g} s fade to black." if fade_out else "")},
        ] + ([{"label": "Opening", "evidence": f"A fade from black on the plant (OpenStreetMap way {o['opening']['plant']}), "
              f"its lines drawn out from it in red: OpenStreetMap ways from {opening.osm['server'].split('/')[2]} "
              f"({opening.osm['fetched_at']}), " + "; ".join(f"{b.label or 'unlabelled'}: {', '.join(map(str, b.ways)) or 'the corridor line'}"
                                                            for b in opening.branches)
              + f". Names: {o['opening'].get('names', 'the ways’ tags')}. Then a pan and zoom to the line's start."}] if opening else [])
        + [{"label": "Inset", "evidence": f"{z.cfg.get('title') or z.cfg['image']} ({z.cfg.get('source', 'supplied; source and date not given')}; "
              f"sha256 {z.sha256[:16]}…): cropped to {z.crop}, {z.m_per_px:.2f} m a pixel, north up, placed by "
              + ", ".join(f"OpenStreetMap node {q['osm_node']}{' (' + q['label'] + ')' if q['label'] else ''} within {q['residual_m']:g} m"
                          for q in z.pins) + f". At km {z.cfg['at_km']:g}, the frame {z.cfg['view_m']:g} m across."} for z in insets],
    }
    if picker is not None:
        picker.write(film_id, corridor_id)
    film["notes"] = film_notes.place(film, o["notes"])
    film["notes_statement"] = film_notes.STATEMENT
    write_json(out / "film.json", film)
    log.info("Film %s: %.0f s, %d×%d, %d pass%s", film_id, film["duration_s"], w, h, len(chosen), "" if len(chosen) == 1 else "es")
    return film


def load(root: Path, corridor_id: str, film_id: str) -> dict[str, Any] | None:
    p = corridor_dir(root, corridor_id) / "films" / film_id / "film.json"
    return json.loads(p.read_text()) if p.is_file() else None
