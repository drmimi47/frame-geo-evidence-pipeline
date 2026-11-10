"""The film's establishing shot, first pass (the user, 9 November 2026: "a tilt-shift photography effect at the start of
the film that has the nuclear power plant framed along with the enerhodar crossing ... relevant city names and location
names should be shown ... next we will transition from this to another view (where the camera zooms in a bit and
rotates to another perspective)").

The crossing's 3D scene as the flight south (south_look3, in the cut) builds it: the plant, the thermal plant and
Enerhodar modelled, the land and the passes, the towers and wires of both crossings and the plant's other lines, the
look pass's sky, haze, water, vegetation and grade. Only the camera is new: a high oblique from over the south bank
south-east of Enerhodar, looking north-west across the plant and the crossing to the north bank, nearly still (a slow
push). The scene's state is held at one date (`STATES`), taken from a frame of south_look3's camera json, so the
imagery, the water and the lines' states are that film's for that date.

Blender renders the picture and each pixel's distance (ts_render.py). The tilt-shift is laid on after, from that
distance: a focal plane (vertical, through the plant and the lines' landing on the north bank), each pixel blurred by
how far what it shows lies off that plane along its own ray (the thin lens: |1/t_focus - 1/t|), so the plant and the
crossing stay sharp and the near south bank and the far distance soften, as a lens tilted the other way would. A
drawn effect, said so in the json. Then the look's grade (a little more saturation and contrast: the miniature's
cues), then the names, never blurred.

    .venv/bin/python -I "research_notes/Tilt-shift opening/scripts/establish.py" stills   # vantages and dates to compare
    .venv/bin/python -I "research_notes/Tilt-shift opening/scripts/establish.py" push     # the shot: one render, zoomed into
    .venv/bin/python -I "research_notes/Tilt-shift opening/scripts/establish.py" clip     # every frame rendered (a moving camera)
    .venv/bin/python -I "research_notes/Tilt-shift opening/scripts/establish.py" post     # tilt-shift, grade, names again

Render once, push in afterwards (the user, 10 November 2026: "with a camera this still, one larger render could be
slowly zoomed into, the way the 2D films only resample real pixels"): `push` renders the shot's first frame once,
OVERSCAN larger each side with its distances, lays the tilt-shift and the colour grade on that one still, then makes
every frame a crop of it, resampled only (Lanczos, always smaller than the render: never upscaled), eased as the camera's
push was; then the look's vignette and grain and the names, drawn sharp at each frame's place. A zoom about the
look-at point is the push without its parallax: the same magnification at the look-at point's distance, nearer ground
grows a little less than a dolly would grow it, farther a little more (said in the json). `clip` and `post` keep the
per-frame render for a camera that moves.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
NOTES = HERE.parent
ROOT = HERE.parents[2]
SCENE = ROOT / "libraries/conductive-seam/satellite/networks/znpp/scenes/crossing3d"
BUILD = ROOT / "src/image_evidence/satellite/scene3d/build.py"
TS_RENDER = HERE / "ts_render.py"
SCRATCH = Path(os.environ.get("TS_SCRATCH", "/private/tmp/claude-501/-Users-patrickrodriguez-dev-sandbox-frame-geo-evidence-pipeline/"
                                            "1a0b7111-211b-446e-85aa-40a4418b76a9/scratchpad/tiltshift"))
W, H, FPS = 1920, 1080, 30
PLANE = {"lon0": 34.5879012, "lat0": 47.5085556, "kx": 75194.446, "kz": 110574.0}   # scene.json `plane`

# the state shown, from a frame of south_look3's camera json (0-based): its date's imagery, water and lines
STATES = {
    "present": {"frame": 2400, "date": "2026-09-11", "pass": "sentinel-2_2025-08-28",
                "lines": "the last reported state (11 September 2026): Ferosplavna-1 connected, Dniprovska cut; the "
                         "plant's other lines cut; the units' links to the thermal plant lit with the line feeding them"},
    "prewar": {"frame": 110, "date": "2022-02-24", "pass": "sentinel-2_2021-09-08",
               "lines": "before the war (24 February 2022): every line connected, power out to the grid"},
}

# vantages: look-at point (x east, y north of the plant, z m), heading (deg from north), pitch, distance, lens
VANTAGES = {
    "A": {"target": [3400.0, 1900.0, 15.0], "heading": -40.0, "pitch": -27.0, "dist": 10000.0, "lens": 22.0,
          "why": "from over the south bank south-east of Enerhodar, looking north-west: the plant, the thermal plant and "
                 "Enerhodar near, the lines running out across the reservoir left to right, the north bank beyond "
                 "(Nikopol far left, Marhanets right); the plant and the crossing at about the same distance, so one "
                 "focal band holds both"},
    # second pass (the user, 9 November 2026: the plant and the crossing "moved to the right of the screen a bit more so
    # they are more at the center"): A slid 1.6 km to the camera's left (south-west) and 0.4 km back, so the scene moves
    # right in the frame without turning; pitched 3 degrees further down, so less of the grey band at the top shows
    "A2": {"target": [2431.0, 565.0, 15.0], "heading": -40.0, "pitch": -30.0, "dist": 10000.0, "lens": 22.0,
           "why": "A's view, slid sideways so the plant and the crossing sit about the frame's centre (the plant at x "
                  "~720, the lines' landing on the south shore ~1190, the north bank's landing ~1650 of 1920)"},
    "B": {"target": [2200.0, 4500.0, 15.0], "heading": 8.0, "pitch": -30.0, "dist": 15000.0, "lens": 30.0,
          "why": "from the south, north up: the plant below, the lines running away up the frame to the north bank"},
}

OVERSCAN = 1.25         # push: the one render this much larger each side (the last frame's crop still 1.19x the frame)
PUSH = 0.045            # the clip: the camera this share nearer the target by its end, eased (no turn, no drift sideways)
CLIP_S = 9.0
HAZE_EXTRA_M = 4000.0   # build.py's haze starts `dist` + 5 km beyond the camera: pushed this much further, so the far bank shows
# the look's air (south_look3: visibility 100 km, made for a flight 70-300 m up) for a view from 4-5 km up: looking down
# through thinner air than along the ground, so the land near the camera isn't greyed (a drawn haze either way)
HAZE_VISIBILITY_KM = 300.0

# the depth of field (second pass, the user: "the things near the front are way too blurred. even the things in the
# background are too blurred ... ensure that the blurring effect and stuff is done tastefully, not so over-the-top")
BLUR_K = 1.0e5          # px of blur per unit of |1/t_focus - 1/t| (1/m), before the dead zone and the ceiling
BLUR_DEAD = 0.6         # px taken off everywhere: a wide band stays fully sharp
BLUR_MAX = 3.0          # px at 1920 wide: the most anything softens (eased into it, tanh)
LEVELS = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]   # blur radii rendered, each pixel between two

# the grade (second pass, the user: "experiment with a more appealing color grading ... it feels too yellowish"):
# white balance in linear light, contrast, saturation, split tone (shadows, highlights), gamma
GRADES = {
    "neutral": {"wb": [0.93, 0.98, 1.10], "contrast": 1.06, "sat": 0.92,
                "why": "the yellow balanced out, colours otherwise as the passes have them"},
    "slate": {"wb": [0.92, 0.98, 1.10], "contrast": 1.08, "sat": 0.74,
              "split": [[-0.010, 0.004, 0.016], [0.006, 0.003, -0.004]],
              "why": "desaturated, cool slate-teal shadows and faintly warm highlights: an editorial map look"},
    "daylight": {"wb": [0.95, 0.985, 1.07], "contrast": 1.10, "sat": 1.04, "gamma": 0.93,
                 "why": "clean, brighter midtones, a little more colour: a clear day"},
}
GRADE = "slate"

# the names (second pass, the user: "more like apple maps/google maps style, with a smaller font size too so it reads
# more sophisticated"; the water named "how google maps/apple maps does water names"): SF Pro (the system face Apple
# Maps uses), mixed case, light text with a soft dark halo, no boxes; a small dot on each place; the water in italic,
# letter-spaced, a muted water blue, set along its course
FONT, FONT_ITALIC = "/System/Library/Fonts/SFNS.ttf", "/System/Library/Fonts/SFNSItalic.ttf"
STYLE = {
    "plant": {"weight": "Semibold", "size": 20, "rgb": (255, 255, 255), "halo": 0.62},
    "site": {"weight": "Medium", "size": 16, "rgb": (238, 240, 242), "halo": 0.6},
    "town": {"weight": "Medium", "size": 18, "rgb": (250, 250, 250), "halo": 0.6, "tracking": 0.3},
    "lines": {"weight": "Medium", "size": 15, "rgb": (246, 232, 196), "halo": 0.6, "tracking": 0.6},
    "water": {"weight": "Medium Italic", "size": 17, "rgb": (172, 202, 224), "halo": 0.42, "tracking": 3.2, "italic": True},
}
HALO_RGB, HALO_PX, HALO_SOFT = (14, 18, 22), 1, 1.6
DOT_R, DOT_RGB = 3.5, (255, 255, 255)

# the names: anchor (x, y m on the scene's plane) or a course (`path`, a few points it passes through, smoothed), style
GEONAMES = "GeoNames (CC BY 4.0), the project's gazetteer src/image_evidence/data/ua_places.tsv.gz"
OSM = "OpenStreetMap (ODbL), raw/osm_plant.json, the way's polygon's mean vertex"


def _xy(lat: float, lon: float) -> list[float]:
    return [round((lon - PLANE["lon0"]) * PLANE["kx"], 1), round((lat - PLANE["lat0"]) * PLANE["kz"], 1)]


PLACES = [
    {"text": "Zaporizhzhia Nuclear Power Plant", "xy": _xy(47.50793, 34.58823), "style": "plant",
     "source": f"{OSM}: way 28877213 (Запорізька АЕС)"},
    {"text": "Zaporizhzhia Thermal Power Plant", "xy": _xy(47.50881, 34.62289), "style": "site",
     "source": f"{OSM}: way 28877239 (Запорізька ТЕС)"},
    {"text": "Enerhodar", "xy": _xy(47.49048, 34.66199), "style": "town", "source": f"{GEONAMES}: 709276"},
    {"text": "Nikopol", "xy": _xy(47.56826, 34.39126), "style": "town", "source": f"{GEONAMES}: 700051"},
    {"text": "Marhanets", "xy": _xy(47.63088, 34.6245), "style": "town", "source": f"{GEONAMES}: 701855"},
    {"text": "Vodiane", "xy": _xy(47.48674, 34.50246), "style": "town", "source": f"{GEONAMES}: 689321"},
    {"text": "Kamianka-Dniprovska", "xy": _xy(47.49629, 34.41026), "style": "town", "source": f"{GEONAMES}: 707026"},
    # set along the crossing, west of Ferosplavna's row (on screen just above the lines), as a map names a road: the
    # crossing named in general; no tower marked
    {"text": "Power lines to the north bank", "path": [[2900, 3760], [3530, 6320], [4320, 9550]], "style": "lines",
     "source": "a course over the water about 600 m west of the two lines (scene.json `lines`: OSM's towers), between "
               "and beside the spans: the crossing named in general"},
]
# the water's name along the drained bed (or the full reservoir) west of the crossing, as the maps set water names
WATER = {"present": {"text": "Former Kakhovka Reservoir", "path": [[-12331, 2098], [-6672, 4230], [-1444, 5604]],
                     "style": "water",
                     "source": "the reservoir drained after the Kakhovka dam's destruction on 6 June 2023; the name set "
                               "along the drained bed as the 2025 pass shows it"},
         "prewar": {"text": "Kakhovka Reservoir", "path": [[-12331, 2098], [-6672, 4230], [-1444, 5604]],
                    "style": "water", "source": "the reservoir full, as the 2021 pass shows it"}}
LABEL_AT_S, LABEL_FADE_S, LABEL_STEP_S = 1.6, 1.2, 0.3
LEAVE_S = 0.2   # push: a name leaving the frame has faded out this long before its last frame inside

# ---- the camera ----

def rotation(heading: float, pitch: float) -> list[float]:
    """Blender's XYZ Euler for a camera looking along `heading` (deg clockwise from north), `pitch` (deg, down < 0)."""
    return [math.radians(90.0 + pitch), 0.0, -math.radians(heading)]


def axes(rot: list[float]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x, _, z = rot
    rx = np.array([[1, 0, 0], [0, math.cos(x), -math.sin(x)], [0, math.sin(x), math.cos(x)]])
    rz = np.array([[math.cos(z), -math.sin(z), 0], [math.sin(z), math.cos(z), 0], [0, 0, 1]])
    r = rz @ rx
    return r[:, 0], r[:, 1], -r[:, 2]   # right, up, forward


def camera_at(v: dict, push: float = 0.0) -> dict:
    h, p = math.radians(v["heading"]), math.radians(v["pitch"])
    fwd = np.array([math.sin(h) * math.cos(p), math.cos(h) * math.cos(p), math.sin(p)])
    d = v["dist"] * (1.0 - push)
    loc = np.array(v["target"]) - d * fwd
    return {"location": [round(float(c), 3) for c in loc], "rotation": rotation(v["heading"], v["pitch"]),
            "lens": v["lens"], "dist": round(d + HAZE_EXTRA_M, 1)}


def project(f: dict, pts: np.ndarray) -> np.ndarray:
    right, up, fwd = axes(f["rotation"])
    q = pts - np.array(f["location"])
    z = q @ fwd
    fp = f["lens"] / 36.0 * W
    return np.column_stack([W / 2 + fp * (q @ right) / z, H / 2 - fp * (q @ up) / z, z])


def rays(f: dict, size: tuple[int, int] | None = None) -> np.ndarray:
    w, h = size or (W, H)
    right, up, fwd = axes(f["rotation"])
    fp = f["lens"] / 36.0 * w
    xs = (np.arange(w) + 0.5 - w / 2) / fp
    ys = (np.arange(h) + 0.5 - h / 2) / fp
    r = fwd[None, None, :] + xs[None, :, None] * right[None, None, :] - ys[:, None, None] * up[None, None, :]
    return r / np.linalg.norm(r, axis=-1, keepdims=True)


# ---- the scene's frames ----

def look3() -> dict:
    return json.loads((SCENE / "camera_south_look3.json").read_text())


def frame(cam: dict, v: dict, state: str, push: float = 0.0, t: float = 0.0) -> dict:
    f = copy.deepcopy(cam["frames"][STATES[state]["frame"]])
    f.pop("fade", None)
    f.update(camera_at(v, push))
    f["phase"] = "establish"
    f["t"] = round(t, 4)
    return f


def camera_json(frames: list[dict], cam: dict, path: Path) -> None:
    doc = copy.deepcopy({k: cam[k] for k in ("extras", "flow", "look") if k in cam})
    doc["look"]["haze"] = dict(doc["look"]["haze"], visibility_km=HAZE_VISIBILITY_KM)
    doc.update({"variant": "south_look3", "fps": FPS, "frames": frames,
                "statement": "A viewing point, designed; not an observation."})
    path.write_text(json.dumps(doc))


def blender(cam_path: Path, out: Path, frames: str, log: Path, size: tuple[int, int] | None = None) -> float:
    t0 = time.time()
    w, h = size or (W, H)
    env = dict(os.environ, TS_OUT=str(out), TS_FRAMES=frames, TS_SIZE=f"{w}x{h}")
    with open(log, "w") as fh:
        subprocess.run(["blender", "-b", "--factory-startup", "-P", str(BUILD), "-P", str(TS_RENDER), "--",
                        str(SCENE / "scene.json"), str(cam_path), str(out), "--no-render"],
                       check=True, stdout=fh, stderr=subprocess.STDOUT, env=env)
    return time.time() - t0


# ---- the depth of field ----

def focal_plane(points: list[list[float]]) -> tuple[np.ndarray, np.ndarray]:
    """A vertical plane through two ground points (the plant and the lines' landing on the north bank)."""
    a, b = np.array(points[0], float), np.array(points[1], float)
    g = b - a
    n = np.array([-g[1], g[0], 0.0])
    return a, n / np.linalg.norm(n)


def blur_map(f: dict, dist: np.ndarray, p0: np.ndarray, n: np.ndarray, scale: float = 1.0) -> np.ndarray:
    """Each pixel's blur radius: the thin lens's k * |1/t_focus - 1/t|, less a dead zone (a wide band left fully
    sharp), then eased into its ceiling (tanh), so the softening comes on gradually and never past BLUR_MAX. `scale`:
    the image's width over W (an oversized render blurs by as many more pixels)."""
    r = rays(f, (dist.shape[1], dist.shape[0]))
    c = np.array(f["location"])
    rn = r @ n
    with np.errstate(divide="ignore", invalid="ignore"):
        tf = ((p0 - c) @ n) / rn
    tf = np.where((tf > 0) & np.isfinite(tf), tf, np.inf)
    with np.errstate(divide="ignore", invalid="ignore"):
        raw = BLUR_K * np.abs(1.0 / tf - 1.0 / dist)
    raw = np.nan_to_num(raw, nan=1e3, posinf=1e3)
    b = scale * BLUR_MAX * np.tanh(np.maximum(raw - BLUR_DEAD, 0.0) / BLUR_MAX)
    return cv2.GaussianBlur(b.astype(np.float32), (0, 0), 3.0 * scale)   # the map itself smooth: no seams where depth jumps


def tilt_shift(img: np.ndarray, b: np.ndarray, levels: list[float] | None = None) -> np.ndarray:
    """Each pixel between the two nearest of a stack of blurred images (a disc's spread as a Gaussian, sigma r/2),
    in linear light, so bright wires soften without darkening."""
    levels = levels or LEVELS
    lin = (img.astype(np.float32) / 255.0) ** 2.2
    stack = [lin if r == 0 else cv2.GaussianBlur(lin, (0, 0), r / 2.0) for r in levels]
    out = np.zeros_like(lin)
    lv = np.array(levels, np.float32)
    k = np.clip(np.searchsorted(lv, b, side="right") - 1, 0, len(lv) - 2)
    a = np.clip((b - lv[k]) / (lv[k + 1] - lv[k]), 0, 1)[..., None]
    for i in range(len(lv) - 1):
        m = (k == i)[..., None]
        if m.any():
            out += m * ((1 - a) * stack[i] + a * stack[i + 1])
    return (np.clip(out, 0, 1) ** (1 / 2.2) * 255 + 0.5).astype(np.uint8)


# ---- the grade ----

def grade(img: np.ndarray, name: str, i: int, look_grade: dict) -> Image.Image:
    """One of GRADES on the frame (after the blur, before the names): a white balance in linear light (the yellow
    taken out), then contrast about mid-grey, saturation about each pixel's luma, an optional split tone (shadows and
    highlights nudged apart) and a gamma; then the look's own faint vignette and grain. A grade: no colour is painted."""
    return finish(Image.fromarray(colour(img, name)), i, look_grade)


def finish(im: Image.Image, i: int, look_grade: dict) -> Image.Image:
    """The look's own faint vignette and grain (the frame's, so after any crop)."""
    sys.path.insert(0, str(ROOT / "src"))
    from image_evidence.satellite.scene3d.animatic import grade_image
    return grade_image(im, {"vignette": look_grade.get("vignette", 0.15) * 0.7, "grain": look_grade.get("grain")}, i)


def colour(img: np.ndarray, name: str) -> np.ndarray:
    """The colour part of one of GRADES (white balance, contrast, saturation, split tone, gamma), any size."""
    g = GRADES[name]
    lin = (img.astype(np.float32) / 255.0) ** 2.2 * np.array(g["wb"], np.float32)
    a = np.clip(lin, 0, 1) ** (1 / 2.2)
    a = 0.5 + (a - 0.5) * g.get("contrast", 1.0)
    luma = (a * np.array([0.2126, 0.7152, 0.0722], np.float32)).sum(-1, keepdims=True)
    a = luma + (a - luma) * g.get("sat", 1.0)
    if g.get("split"):
        sh, hi = (np.array(x, np.float32) for x in g["split"])
        w = np.clip(luma, 0, 1)
        a = a + (1 - w) ** 2 * sh + w ** 2 * hi
    if g.get("gamma"):
        a = np.clip(a, 0, 1) ** g["gamma"]
    return (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)


# ---- the names, as the maps set them ----

def _font(name: str, size: int, italic: bool = False):
    try:
        f = ImageFont.truetype(FONT_ITALIC if italic else FONT, size)
        f.set_variation_by_name(name)
        return f
    except OSError:
        return ImageFont.truetype("/System/Library/Fonts/HelveticaNeue.ttc", size)


def ground(xy: list[float], state_frame: dict) -> float:
    z = np.load(SCENE / "terrain.npz")
    xs, ys, zz = z["x"], z["y"], z["z"]
    if not (xs[0] <= xy[0] <= xs[-1] and ys[0] <= xy[1] <= ys[-1]):
        return 20.0
    i, j = np.searchsorted(ys, xy[1]), np.searchsorted(xs, xy[0])
    return float(max(zz[min(i, len(ys) - 1), min(j, len(xs) - 1)], state_frame.get("level_m") or 0.0))


class Layer:
    """The names drawn into one frame-sized layer (colour and coverage), so the halo is made once from all of them."""

    def __init__(self):
        self.rgb = np.zeros((H, W, 3), np.float32)
        self.a = np.zeros((H, W), np.float32)
        self.halo = np.zeros((H, W), np.float32)   # how strongly each name wants its halo (its style's)

    def add(self, rgba: np.ndarray, m: np.ndarray, halo: float, alpha: float) -> None:
        """An upright RGBA image (premultiplied by nothing) placed by the 2x3 affine `m` (sub-pixel, bilinear); only
        the box it lands in is touched."""
        h0, w0 = rgba.shape[:2]
        c = np.array([[0, 0, 1], [w0, 0, 1], [0, h0, 1], [w0, h0, 1]], np.float32) @ np.asarray(m, np.float32).T
        x0, y0 = max(int(np.floor(c[:, 0].min())) - 1, 0), max(int(np.floor(c[:, 1].min())) - 1, 0)
        x1, y1 = min(int(np.ceil(c[:, 0].max())) + 2, W), min(int(np.ceil(c[:, 1].max())) + 2, H)
        if x1 <= x0 or y1 <= y0:
            return
        mm = np.asarray(m, np.float32).copy()
        mm[:, 2] -= (x0, y0)
        w = cv2.warpAffine(rgba, mm, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                           borderValue=0)
        al = w[..., 3] / 255.0 * alpha
        sl = (slice(y0, y1), slice(x0, x1))
        self.rgb[sl] = self.rgb[sl] * (1 - al[..., None]) + w[..., :3] * al[..., None]
        self.a[sl] = self.a[sl] + al * (1 - self.a[sl])
        self.halo[sl] = np.maximum(self.halo[sl], (w[..., 3] > 8) * halo * alpha)

    def onto(self, im: Image.Image) -> None:
        cover = cv2.dilate(self.a, np.ones((3, 3), np.uint8), iterations=HALO_PX)
        soft = cv2.GaussianBlur(cover, (0, 0), HALO_SOFT)
        hs = cv2.GaussianBlur(cv2.dilate(self.halo, np.ones((3, 3), np.uint8), iterations=HALO_PX + 2), (0, 0), HALO_SOFT)
        h = np.clip(soft, 0, 1) * hs
        b = np.asarray(im.convert("RGB")).astype(np.float32)
        b = b * (1 - h[..., None]) + np.array(HALO_RGB, np.float32) * h[..., None]
        b = b * (1 - self.a[..., None]) + self.rgb * self.a[..., None]
        im.paste(Image.fromarray(np.clip(b + 0.5, 0, 255).astype(np.uint8)))


def _glyphs(text: str, font, tracking: float) -> list[tuple[str, float]]:
    """Each character and its advance (the font's, plus tracking in px)."""
    return [(ch, font.getlength(ch) + tracking) for ch in text]


def _text_image(text: str, font, rgb, tracking: float = 0.0) -> tuple[np.ndarray, float, float]:
    """A run of text as an RGBA image; returns it and its baseline's y and its advance width."""
    asc, desc = font.getmetrics()
    adv = sum(a for _, a in _glyphs(text, font, tracking)) - tracking
    im = Image.new("RGBA", (int(adv) + 8, asc + desc + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = 4.0
    for ch, a in _glyphs(text, font, tracking):
        d.text((x, 4 + asc), ch, font=font, fill=(*rgb, 255), anchor="ls")
        x += a
    return np.asarray(im).astype(np.float32), 4 + asc, adv


def _place(layer: Layer, p: dict, x: float, y: float, alpha: float) -> list[float]:
    """A place: a small dot on it and its name beside it (right, or left where `side: left`), vertically centred on the
    dot, as the maps label towns."""
    st = STYLE[p["style"]]
    font = _font(st["weight"], st["size"])
    img, base, adv = _text_image(p["text"], font, st["rgb"], st.get("tracking", 0.0))
    asc, _ = font.getmetrics()
    cap = asc * 0.72
    gap = DOT_R + 6
    tx = x + gap - 4 if p.get("side") != "left" else x - gap - adv - 4
    ty = y - base + cap / 2
    layer.add(img, np.float32([[1, 0, tx], [0, 1, ty]]), st["halo"], alpha)
    if p.get("dot", True):
        r = DOT_R
        s = int(round(4 * (2 * r + 4)))
        dot = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        ImageDraw.Draw(dot).ellipse((8, 8, s - 8, s - 8), fill=(*DOT_RGB, 255), outline=(40, 44, 48, 255), width=4)
        dot = np.asarray(dot.resize((s // 4, s // 4), Image.LANCZOS)).astype(np.float32)
        layer.add(dot, np.float32([[1, 0, x - dot.shape[1] / 2], [0, 1, y - dot.shape[0] / 2]]), 0.6, alpha)
    return [round(tx + 4, 1), round(ty, 1), round(adv, 1)]


def _along(layer: Layer, p: dict, path_px: np.ndarray, alpha: float) -> list[float]:
    """A name set along a course (the water's, the lines'): each letter at its arc length on the projected path,
    turned to the path's direction, the run centred on the path and reading left to right."""
    st = STYLE[p["style"]]
    font = _font(st["weight"], st["size"], st.get("italic", False))
    if path_px[-1, 0] < path_px[0, 0]:
        path_px = path_px[::-1]
    seg = np.linalg.norm(np.diff(path_px, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    gl = _glyphs(p["text"], font, st.get("tracking", 0.0))
    total = sum(a for _, a in gl) - st.get("tracking", 0.0)
    pos = (s[-1] - total) / 2
    asc, _ = font.getmetrics()
    mid = asc * 0.36   # half the x-height: the letters' middle on the path
    for ch, a in gl:
        w = font.getlength(ch)
        c = pos + w / 2
        k = int(np.clip(np.searchsorted(s, c) - 1, 0, len(seg) - 1))
        u = (c - s[k]) / max(seg[k], 1e-6)
        pt = path_px[k] + u * (path_px[k + 1] - path_px[k])
        lo, hi = max(0, k - 2), min(len(path_px) - 1, k + 3)   # the direction over a few points: no jitter
        dvec = path_px[hi] - path_px[lo]
        ang = math.atan2(dvec[1], dvec[0])
        img, base, _ = _text_image(ch, font, st["rgb"])
        cx, cy = 4 + w / 2, base - mid
        ca, sa = math.cos(ang), math.sin(ang)
        m = np.float32([[ca, -sa, pt[0] - (ca * cx - sa * cy)], [sa, ca, pt[1] - (sa * cx + ca * cy)]])
        if ch != " ":
            layer.add(img, m, st["halo"], alpha)
        pos += a
    return [round(float(path_px[0, 0]), 1), round(float(path_px[0, 1]), 1), round(total, 1)]


def places_for(state: str, sf: dict) -> list[dict]:
    ps = [dict(p) for p in PLACES] + [dict(WATER[state])]
    for p in ps:
        if p.get("path"):
            lvl = sf.get("level_m") or 15.0
            p["pts"] = np.array([[x, y, max(lvl, 0.0) + 1.0] for x, y in densify(p["path"])])
        else:
            p["z"] = ground(p["xy"], sf) + 2.0
    return ps


def densify(path: list[list[float]], step: float = 60.0) -> list[list[float]]:
    """A smooth course through the given points (Catmull-Rom), a point every `step` m."""
    P = np.array(path, float)
    P = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        n = max(2, int(np.linalg.norm(p2 - p1) / step))
        for t in np.linspace(0, 1, n, endpoint=False):
            out.append(0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t ** 2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-2])
    return [list(map(float, q)) for q in out]


def _extent(p: dict, f: dict) -> tuple[float, float, float, float] | None:
    """A name's box on screen (approximate), or None behind the camera."""
    st = STYLE[p["style"]]
    font = _font(st["weight"], st["size"], st.get("italic", False))
    if p.get("path"):
        xy = project(f, p["pts"])
        if (xy[:, 2] <= 0).any():
            return None
        return float(xy[:, 0].min()), float(xy[:, 1].min()) - st["size"], float(xy[:, 0].max()), float(xy[:, 1].max()) + st["size"]
    x, y, z = project(f, np.array([[*p["xy"], p["z"]]]))[0]
    if z <= 0:
        return None
    adv = sum(a for _, a in _glyphs(p["text"], font, st.get("tracking", 0.0)))
    if p.get("side") == "left":
        return x - DOT_R - 6 - adv, y - st["size"], x + DOT_R, y + st["size"]
    return x - DOT_R, y - st["size"], x + DOT_R + 6 + adv, y + st["size"]


def fits(f: dict, ps: list[dict]) -> set[str]:
    """The names wholly in the frame (with a margin)."""
    ok = set()
    for p in ps:
        e = _extent(p, f)
        if e and e[0] >= 24 and e[1] >= 24 and e[2] <= W - 24 and e[3] <= H - 24:
            ok.add(p["text"])
    return ok


def names(im: Image.Image, f: dict, ps: list[dict], t: float | None, only: set[str] | None = None,
          until: dict[str, float] | None = None) -> list[dict]:
    """The names in `only` (in the frame all through the shot, so none appears or vanishes at the edge), else every
    one that fits, fading in one after another from LABEL_AT_S; a name in `until` fades out by that time (before it
    would reach the frame's edge); drawn sharp, after the blur and the grade."""
    ok = fits(f, ps) if only is None else only
    layer = Layer()
    shown, k = [], 0
    for p in ps:
        if p["text"] not in ok:
            continue
        a = 1.0 if t is None else min(1.0, max(0.0, (t - LABEL_AT_S - k * LABEL_STEP_S) / LABEL_FADE_S))
        if t is not None and until and p["text"] in until:
            a = min(a, max(0.0, (until[p["text"]] - t) / LABEL_FADE_S))
        a = a * a * (3 - 2 * a)
        if p.get("path"):
            at = _along(layer, p, project(f, p["pts"])[:, :2], a)
        else:
            x, y, _ = project(f, np.array([[*p["xy"], p["z"]]]))[0]
            at = _place(layer, p, float(x), float(y), a)
        shown.append({"text": p["text"], "style": p["style"], "at_px": at})
        k += 1
    layer.onto(im)
    return shown


# ---- the passes ----

def post_frame(raw: Path, dep: Path, f: dict, cam: dict, i: int, ps: list[dict], t: float | None, plane,
               only: set[str] | None = None, grade_name: str | None = None) -> tuple[Image.Image, list]:
    img = np.asarray(Image.open(raw).convert("RGB"))
    dist = np.load(dep)
    img = tilt_shift(img, blur_map(f, dist, *plane))
    im = grade(img, grade_name or GRADE, i, cam["look"].get("grade") or {})
    shown = names(im, f, ps, t, only)
    return im, shown


def plane_points(state_frame: dict) -> list[list[float]]:
    lvl = state_frame.get("level_m") or 15.0
    return [[0.0, 0.0, 20.0], [5300.0, 8900.0, lvl]]   # the plant; the lines' landing on the north bank (OSM's towers)


def stills() -> None:
    cam = look3()
    picks = [("A2", "present"), ("A2", "prewar")]
    frames = [frame(cam, VANTAGES[v], s) for v, s in picks]
    d = SCRATCH / "stills"
    d.mkdir(parents=True, exist_ok=True)
    cj = d / "camera_stills.json"
    camera_json(frames, cam, cj)
    if not all((d / f"d_{i:04d}.npy").exists() for i in range(1, len(frames) + 1)):   # else: the tilt-shift and names again
        secs = blender(cj, d, ",".join(str(i) for i in range(1, len(frames) + 1)), d / "blender.log")
        print(f"rendered {len(frames)} stills in {secs:.0f} s")
    out = NOTES / "stills"
    out.mkdir(exist_ok=True)
    for i, ((v, s), f) in enumerate(zip(picks, frames), start=1):
        sf = cam["frames"][STATES[s]["frame"]]
        for g in (GRADES if s == "present" else [GRADE]):   # the grades compared on the present
            im, shown = post_frame(d / f"f_{i:04d}.png", d / f"d_{i:04d}.npy", f, cam, i, places_for(s, sf), None,
                                   focal_plane(plane_points(sf)), grade_name=g)
            im.save(out / f"still_{v}_{s}_{g}.png")
            print(v, s, g, [x["text"] for x in shown])
        Image.open(d / f"f_{i:04d}.png").save(out / f"still_{v}_{s}_plain.png")


def clip_frames(v: str, state: str) -> list[dict]:
    cam = look3()
    n = round(CLIP_S * FPS)
    out = []
    for i in range(n):
        u = i / (n - 1)
        e = 0.5 - 0.5 * math.cos(math.pi * u)   # eased in and out: from rest to rest
        out.append(frame(cam, VANTAGES[v], state, PUSH * e, i / FPS))
    return out


def clip(v: str = "A2", state: str = "present", render: bool = True) -> None:
    cam = look3()
    frames = clip_frames(v, state)
    d = SCRATCH / f"clip_{v}_{state}"
    d.mkdir(parents=True, exist_ok=True)
    cj = d / "camera_clip.json"
    camera_json(frames, cam, cj)
    secs = None
    if render:
        secs = blender(cj, d, f"1-{len(frames)}", d / "blender.log")
        print(f"rendered {len(frames)} frames in {secs:.0f} s")
    post(v, state, secs)


def post(v: str = "A2", state: str = "present", secs: float | None = None) -> None:
    """The per-frame render's frames: tilt-shift, grade and names on each, into `tilt_shift_opening_perframe.*`."""
    cam = look3()
    frames = clip_frames(v, state)
    d = SCRATCH / f"clip_{v}_{state}"
    sf = cam["frames"][STATES[state]["frame"]]
    ps = places_for(state, sf)
    plane = focal_plane(plane_points(sf))
    fin = d / "final"
    fin.mkdir(exist_ok=True)
    shown = None
    only = fits(frames[0], ps) & fits(frames[-1], ps)
    for i, f in enumerate(frames, start=1):
        im, shown = post_frame(d / f"f_{i:04d}.png", d / f"d_{i:04d}.npy", f, cam, i, ps, f["t"], plane, only)
        im.save(fin / f"f_{i:04d}.png")
    outputs(fin, frames, v, state, plane, ps, shown, "tilt_shift_opening_perframe",
            {"mode": "per-frame", "render_s": None if secs is None else round(secs),
             "push": f"the camera {PUSH:.1%} nearer the look-at point over the shot, eased in and out (cosine), every "
                     "frame rendered; no turn, no sideways drift"})


def zoom_frames(v: str, state: str) -> list[dict]:
    """The push as a zoom about the look-at point (on the optical axis: the frame's centre): the first frame's camera,
    its lens lengthened by the magnification the dolly gives at the look-at point's distance, 1 / (1 - PUSH * ease)."""
    cam = look3()
    f0 = frame(cam, VANTAGES[v], state)
    n = round(CLIP_S * FPS)
    out = []
    for i in range(n):
        u = i / (n - 1)
        e = 0.5 - 0.5 * math.cos(math.pi * u)   # eased in and out: from rest to rest, as the dolly was
        f = copy.deepcopy(f0)
        f["zoom"] = 1.0 / (1.0 - PUSH * e)
        f["lens"] = f0["lens"] * f["zoom"]
        f["t"] = round(i / FPS, 4)
        out.append(f)
    return out


def push(v: str = "A2", state: str = "present") -> None:
    """Render once, push in afterwards: the first frame rendered OVERSCAN larger (same lens: the same view, more
    pixels), the tilt-shift and colour grade laid on that still, then each frame its centre crop resampled to W x H
    (Lanczos, a float box: sub-pixel; always a reduction), the vignette and grain, and the names at their places."""
    t0 = time.time()
    cam = look3()
    frames = zoom_frames(v, state)
    f0 = frame(cam, VANTAGES[v], state)
    big = (round(W * OVERSCAN), round(H * OVERSCAN))
    d = SCRATCH / f"push_{v}_{state}"
    d.mkdir(parents=True, exist_ok=True)
    secs = None
    if not (d / "d_0001.npy").exists():
        cj = d / "camera.json"
        camera_json([f0], cam, cj)
        secs = blender(cj, d, "1", d / "blender.log", size=big)
        print(f"rendered the {big[0]}x{big[1]} still in {secs:.0f} s")
    t1 = time.time()
    sf = cam["frames"][STATES[state]["frame"]]
    ps = places_for(state, sf)
    plane = focal_plane(plane_points(sf))
    img = np.asarray(Image.open(d / "f_0001.png").convert("RGB"))
    dist = np.load(d / "d_0001.npy")
    assert img.shape[:2] == (big[1], big[0]) == dist.shape, (img.shape, dist.shape)
    img = tilt_shift(img, blur_map(f0, dist, *plane, scale=OVERSCAN), [r * OVERSCAN for r in LEVELS])
    base = Image.fromarray(colour(img, GRADE))
    base.save(d / "still_graded.png")
    look_grade = cam["look"].get("grade") or {}
    # every name in the first frame; one that leaves the frame during the zoom fades out first, ending LEAVE_S before
    # its last frame in the frame (the user, 10 November 2026: Kamianka-Dniprovska faded, not dropped)
    only = fits(frames[0], ps)
    inside = [fits(f, ps) for f in frames]
    until = {}
    for name in only:
        last = max(i for i, s in enumerate(inside) if name in s and all(name in x for x in inside[:i + 1]))
        if last < len(frames) - 1:
            until[name] = frames[last]["t"] - LEAVE_S
    fin = d / "final"
    fin.mkdir(exist_ok=True)
    shown = None
    cx, cy = big[0] / 2, big[1] / 2
    for i, f in enumerate(frames, start=1):
        hw, hh = big[0] / 2 / f["zoom"], big[1] / 2 / f["zoom"]
        im = base.resize((W, H), Image.LANCZOS, box=(cx - hw, cy - hh, cx + hw, cy + hh))
        im = finish(im, i, look_grade)
        shown = names(im, f, ps, f["t"], only, until)
        im.save(fin / f"f_{i:04d}.png")
    post_s = time.time() - t1
    print("fading out before the edge:", until)
    outputs(fin, frames, v, state, plane, ps, shown, "tilt_shift_opening",
            {"mode": "render once, push in afterwards", "render_s": None if secs is None else round(secs),
             "post_s": round(post_s), "total_s": round(time.time() - t0),
             "render_size": list(big), "overscan": OVERSCAN,
             "names_faded_out": {k: f"by {v:.2f} s, before the zoom takes it past the frame's edge" for k, v in until.items()},
             "push": f"a zoom into one render: the first frame rendered {OVERSCAN}x each side, then each frame its centre "
                     f"crop resampled (Lanczos), {PUSH:.1%} of the look-at distance's dolly as a zoom of up to "
                     f"{frames[-1]['zoom']:.4f}x, eased in and out (cosine); the last frame's crop is still "
                     f"{OVERSCAN / frames[-1]['zoom']:.3f}x the frame, so nothing is upscaled",
             "statement": "a drawing convention: the push is a zoom into one rendered still, so it has no parallax (the "
                          "dolly it stands for would grow the nearer ground a few per cent more than the far); pixels "
                          "only resampled, never generated or interpolated between frames"})


def outputs(fin: Path, frames: list[dict], v: str, state: str, plane, ps: list[dict], shown, stem: str,
            method: dict) -> None:
    mp4 = NOTES / f"{stem}.mp4"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(FPS), "-i", str(fin / "f_%04d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", "-movflags", "+faststart", str(mp4)], check=True)
    shutil.copy(fin / f"f_{len(frames):04d}.png", NOTES / f"{stem}_last.png")
    picks = [round(s * FPS) + 1 for s in (0.0, 1.5, 2.5, 3.5, 5.0, 7.0, 8.0)] + [len(frames)]
    tw, th = 640, 360
    sheet = Image.new("RGB", (tw * 2, th * 4), (0, 0, 0))
    dr = ImageDraw.Draw(sheet)
    for k, i in enumerate(picks):
        im = Image.open(fin / f"f_{i:04d}.png").resize((tw, th), Image.LANCZOS)
        sheet.paste(im, ((k % 2) * tw, (k // 2) * th))
        dr.text(((k % 2) * tw + 8, (k // 2) * th + 6), f"{(i - 1) / FPS:4.1f} s", fill=(255, 255, 255))
    sheet.save(NOTES / f"{stem}_sheet.jpg", quality=90)
    p0, n = plane
    st = STATES[state]
    doc = {
        "title": "The establishing shot, tilt-shift (third pass: render once, push in afterwards)"
                 if method["mode"] != "per-frame" else "The establishing shot, tilt-shift (second pass, every frame rendered)",
        "asked": "the user, 9 November 2026: a tilt-shift effect at the start of the film framing the nuclear power plant "
                 "with the Enerhodar crossing, city and place names shown; the next shot zooms in and rotates",
        "file": mp4.name, "sha256": hashlib.sha256(mp4.read_bytes()).hexdigest(), "fps": FPS, "size": [W, H],
        "frames": len(frames), "seconds": round(len(frames) / FPS, 2), "sound": None,
        "method": method,
        "scene": {"from": "the crossing's 3D scene as south_look3 builds it (scene.json, camera_south_look3.json's look, "
                          "extras plant, land_south, others); only the camera is new",
                  "build": "src/image_evidence/satellite/scene3d/build.py --no-render, then scripts/ts_render.py"},
        "date_state": {"date": st["date"], "pass_shown": st["pass"], "lines": st["lines"],
                       "from_frame": f"camera_south_look3.json frame {st['frame']} (0-based): its imagery weights, water "
                                     "level and colour, wet band, plants' growth and every line's state, held"},
        "camera": {"vantage": v, **VANTAGES[v], "first": frames[0], "last": frames[-1],
                   "statement": "A viewing point and path, designed; not an observation."},
        "tilt_shift": {"method": "a focal plane, vertical, through the plant and the lines' landing on the north bank; each "
                                 "pixel blurred by k * |1/t_focus - 1/t| (t: the distance Blender rendered for what the pixel "
                                 "shows; t_focus: where the pixel's own ray meets the plane), less a dead zone, eased (tanh) into a "
                                 "ceiling, smoothed, then a stack "
                                 "of Gaussian blurs in linear light, each pixel between the two nearest",
                       "plane_point": [round(float(c), 1) for c in p0], "plane_normal": [round(float(c), 4) for c in n],
                       "k": BLUR_K, "dead_px": BLUR_DEAD, "max_px": BLUR_MAX, "levels_px": LEVELS,
                       "px_at": "the frame's 1920 width (an oversized render blurred by as many more pixels)",
                       "grade": {"name": GRADE, **{k: v for k, v in GRADES[GRADE].items()},
                                 "then": "the look's vignette x0.7 and grain, on each frame", "variants": list(GRADES),
                                 "statement": "a grade (white balance, contrast, saturation, split tone): no colour painted"},
                       "statement": "A drawn effect, a lens's depth of field imitated; the scene is at its true size. Blur "
                                    "hides detail, it adds none."},
        "names": {"style": "as the maps set them: SF Pro, mixed case, light text with a soft dark halo, no boxes; a small dot "
                           "on each place with its name beside it; the water in italic, letter-spaced, a muted blue, set "
                           "along its course; the crossing's name along the lines; never blurred or scaled, drawn at each "
                           f"frame's place; fading in one after another from {LABEL_AT_S} s over {LABEL_FADE_S} s, "
                           f"{LABEL_STEP_S} s apart",
                  "styles": STYLE, "halo": {"rgb": HALO_RGB, "dilate_px": HALO_PX, "sigma_px": HALO_SOFT},
                  "shown_last_frame": shown,
                  "places": [{"text": p["text"], **({"path_m": p["path"]} if p.get("path") else {"xy_m": p["xy"]}),
                              "source": p["source"]} for p in ps],
                  "safety": "names sit on towns, the two plants, the water and a course beside the lines' spans; "
                            "no tower, repair or damage site, crew position, substation or trench site is named or marked"},
        "statement": "The crossing's 3D scene (modelled from OSM's footprints and towers, FABDEM heights, Sentinel-2 passes; "
                     "massing and towers representative, said in scene.json) seen from a designed viewpoint, its "
                     "depth of field drawn. Contains modified Copernicus Sentinel data; © OpenStreetMap contributors "
                     "(ODbL); GeoNames (CC BY 4.0).",
    }
    (NOTES / f"{stem}.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False))
    print("wrote", mp4.relative_to(ROOT))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stills"
    args = sys.argv[2:]
    if cmd == "stills":
        stills()
    elif cmd == "clip":
        clip(*args[:2]) if args else clip()
    elif cmd == "post":
        post(*args[:2]) if args else post()
    elif cmd == "push":
        push(*args[:2]) if args else push()
