"""The plant's zones over the establishing shot: preview stills, one zone per image (the user approved the design, 9
November 2026; revised 10 November: "the other text on the map should not be visible when the zones are being shown
one by one ... for the dome zone it should be a gradient with the bottom of the being more opaque than the top, i dont
like the dotted/dashes mesh look ... show me one image per zone so i can differentiate them"). Sources and wording from
reports/ZNPP as a military shield.md ("Only the zone meant to stop the fighting never had a size", "Showing the shield").

What has a size is drawn on the ground at true scale; what has none is words only. Every image shows one zone and its
own label, and no other text (no town, plant or water names, no foot line).
- Z1 the IAEA protection zone (proposed 6 September 2022, never agreed, recast 30 March 2023; no size published, Grossi:
  "limited to the perimeter and the plant itself"): a smooth translucent hemisphere on the plant's site as the zoom-out
  draws it (the smallest circle round OSM way 28877213, 1.65 km across), most opaque at the ground and fading to nothing
  toward the top, so it never closes (the "never agreed" reading, in place of the earlier arcs stopped short); a faint
  rim where it meets the ground. Its shape and height are ours, and the label says it is drawn.
- Z2 the IAEA's precautionary action zone, a band from 3 to 5 km (a range: "suggested maximum radius", EPR-NPP Public
  Protective Actions 2013, Table 3).
- Z3 its urgent protective action planning zone, a band from 15 to 30 km, fainter.
- Z4 Ukraine's 30 km observation zone, dashed (secondary sources: Ukrhydromet's bulletin draws it so).
- C the dome close up (a separate, tighter camera still), its label only.
The UN Secretary-General's "demilitarised perimeter" (August 2022), Additional Protocol I Art. 56(5)'s "vicinity" and
the seven IAEA-brokered repair truces have no size: kept in zones.json as research, not drawn (the user, 10 November
2026: "if there is no visual proposal might as well not include it").

Revised again on 10 November ("yes make a wider view for z3 and z4 ... perhaps a better color than white?"): the rings
from a wider camera of their own (`WIDE`, `zones_wide_*`), and every zone in four palettes (`palettes.py`, checked for
colour-blind separation there), one image per zone and palette and a sheet per palette.
The 100 and 300 km distances are left out. Rings and dome share one centre, the site circle's (the six units' centroid
lies 233 m from it: well under the guidance's precision, whose radii are given as 3-5 and 15-30 km).

The draping: every pixel's ground point is known (the distance Blender rendered for it along its own ray), so its
distance from the centre on the ground is known; a band is the pixels whose ground lies between its radii, a ring the
pixels within a line's half-width of its radius (the half-width in metres from how fast that distance changes across
the screen there, so every ring is the same width on screen). The rings so lie on whatever the frame shows there, the
land, the drained bed, the water, roofs; what the ground hides stays hidden. The dome: each pixel's ray met with the
hemisphere (both its near and far surfaces), each surface's opacity by its height and by how obliquely the ray meets it,
hidden where the rendered ground stands in front; at twice the frame's size, then reduced.

    .venv/bin/python -I "research_notes/Tilt-shift opening/zones/scripts/zones.py" [palette ...]
"""

from __future__ import annotations

import importlib.util
import json
import math
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
spec = importlib.util.spec_from_file_location("establish", HERE.parents[1] / "scripts" / "establish.py")
E = importlib.util.module_from_spec(spec)
spec.loader.exec_module(E)
pspec = importlib.util.spec_from_file_location("palettes", HERE / "palettes.py")
P = importlib.util.module_from_spec(pspec)
pspec.loader.exec_module(P)
W, H = E.W, E.H

CENTRE, SITE_R = [-3.8, 151.2], 824.9   # the smallest circle round OSM way 28877213 (the zoom-out's zone circle)
UNITS_C = [-110.2, 358.9]                # the six units' centroid (OSM ways 1572378821-30), 233 m off: not used
CENTRE_LONLAT = [34.587851, 47.509923]
LAND = (-16980.0, 23000.0, -19480.0, 28500.0)   # the land's box (terrain.npz with terrain_south.npz): x0, x1, y0, y1
FAR_Z = 8.0                                     # the look's far plain (config: south_look3 look.far_plain.z_m)
HALF_MAX = 65000.0                              # the depth pass's ceiling (half float, 65,504), with a margin
_TERRAIN = []


def terrain_z(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """The land's height (terrain.npz and terrain_south.npz, the same columns) at points, bilinear; FAR_Z off it."""
    if not _TERRAIN:
        n, s = np.load(E.SCENE / "terrain.npz"), np.load(E.SCENE / "terrain_south.npz")
        ys = np.concatenate([s["y"][:-1], n["y"]]) if s["y"][-1] == n["y"][0] else np.concatenate([s["y"], n["y"]])
        zz = np.concatenate([s["z"][:-1], n["z"]]) if s["y"][-1] == n["y"][0] else np.concatenate([s["z"], n["z"]])
        _TERRAIN.extend([n["x"], ys, np.nan_to_num(zz.astype(np.float32), nan=FAR_Z)])
    xs, ys, zz = _TERRAIN
    fx = np.interp(x, xs, np.arange(len(xs)), left=-1, right=-1)
    fy = np.interp(y, ys, np.arange(len(ys)), left=-1, right=-1)
    i0 = np.clip(np.floor(fy).astype(int), 0, len(ys) - 2)
    j0 = np.clip(np.floor(fx).astype(int), 0, len(xs) - 2)
    a, b = np.clip(fy - i0, 0, 1), np.clip(fx - j0, 0, 1)
    out = (zz[i0, j0] * (1 - a) * (1 - b) + zz[i0, j0 + 1] * (1 - a) * b + zz[i0 + 1, j0] * a * (1 - b)
           + zz[i0 + 1, j0 + 1] * a * b)
    return np.where((fx < 0) | (fy < 0), FAR_Z, out)

# the dome: opacity = DOME_A * height fade * obliqueness; the height fade (1 - h / (DOME_TOP * R)) ** DOME_GAMMA reaches
# nothing at DOME_TOP of its height; the obliqueness mixes DOME_FACE (a surface faced square on) up to 1 (grazing),
# so the shell's edges read and its middle stays clear
DOME_A, DOME_TOP, DOME_GAMMA = 0.55, 0.92, 1.3
DOME_FACE, DOME_FRES = 0.38, 2.0
DOME_SOFT_M = 200.0  # the ground hides it over this depth, not at a hard edge (so the plant's buildings don't cut it)
DOME_FOOT_M = 25.0   # its foot fades in over this height: no hard bright line where the far wall meets the ground
DOME_RGB = (0.94, 0.97, 1.0)
DOME_RIM = 0.55   # the ring where it meets the ground

REPORT = "reports/ZNPP as a military shield.md"
EPR = "IAEA, EPR-NPP Public Protective Actions (2013), Table 3: suggested maximum radius"
RINGS = {
    "paz": {"band": [3000, 5000], "fill": 0.14, "edge": 0.8, "rgb": (236, 240, 244),
            "label": "Precautionary action zone  ·  out to 3–5 km  ·  IAEA", "label_at_deg": 150, "label_r": 5300,
            "source": EPR},
    # combined with the observation zone the outer limit had no line (the band faded out toward 30 km, where the dashed
    # ring is); shown alone it has a faint one
    "upz": {"band": [15000, 30000], "fill": 0.13, "edge": 0.55, "outer": 0.3, "fade_out": True, "rgb": (220, 228, 236),
            "label": "Urgent protective action planning zone  ·  out to 15–30 km  ·  IAEA", "label_at_deg": 352,
            "label_r": 14300, "source": EPR},
    "obs": {"ring": 30000, "dash_m": 900, "edge": 0.9, "rgb": (250, 222, 178),
            "label": "Observation zone  ·  30 km  ·  Ukraine", "label_at_deg": 302, "label_r": 29000,
            "source": "Ukrainian norms as reported; Ukrhydromet's daily radiological bulletin draws 30 km dashed round "
                      "each plant (secondary sources, as the report says)"},
}
DOME_LABEL = ["IAEA protection zone",
              "proposed 6 Sep 2022, never agreed",
              "no size published: “limited to the perimeter and the plant itself”",
              "drawn on the plant’s site: its shape and height are ours"]
UNSIZED = {"facts": ["the UN Secretary-General's 'demilitarised perimeter' (August 2022)",
                     "Additional Protocol I, Art. 56(5): 'the vicinity' (undefined)",
                     "seven IAEA-brokered repair truces (2025-26): no distances published"],
           "status": "research only: no size, so not drawn (the user, 10 November 2026)"}

E.STYLE.update({
    "zone": {"weight": "Semibold", "size": 15, "rgb": (244, 246, 248), "halo": 0.7, "tracking": 0.4},
    "zone_obs": {"weight": "Semibold", "size": 15, "rgb": (252, 226, 186), "halo": 0.7, "tracking": 0.4},
    "dome": {"weight": "Semibold", "size": 17, "rgb": (255, 255, 255), "halo": 0.7},
    "dome_small": {"weight": "Medium", "size": 14, "rgb": (234, 238, 242), "halo": 0.75},
})


def fields(f: dict, dist: np.ndarray) -> dict:
    """Each pixel's ground distance from the centre (smoothed), metres per pixel across it, and bearing (at the depth
    pass's size: the frame's, or an oversized render's for a push)."""
    r = E.rays(f, (dist.shape[1], dist.shape[0]))
    c = np.array(f["location"])
    P = c + r * dist[..., None]
    # EEVEE's buffer is half float: a distance past 65,504 m comes back clamped there (the wide view's far corner of
    # the land read as ground 2 km up, the ring broken there); those pixels' rays are met with the terrain instead
    sat = np.isfinite(dist) & (dist >= HALF_MAX)
    if sat.any():
        rs, h = r[sat], np.full(int(sat.sum()), FAR_Z)
        for _ in range(12):
            t = (h - c[2]) / rs[:, 2]
            Q = c + rs * t[:, None]
            h = 0.5 * h + 0.5 * terrain_z(Q[:, 0], Q[:, 1])
        P[sat] = Q
    # beyond the land's box the ground is the look's far plain, flat at FAR_Z: each pixel's point there is its ray met
    # with that plane (the render's surface past the box isn't reliable ground)
    t = (FAR_Z - c[2]) / np.where(np.abs(r[..., 2]) > 1e-9, r[..., 2], -1e-9)
    Pf = c + r * t[..., None]
    off = ~np.isfinite(dist) | (P[..., 0] < LAND[0]) | (P[..., 0] > LAND[1]) | (P[..., 1] < LAND[2]) | (P[..., 1] > LAND[3])
    P = np.where(off[..., None], Pf, P)
    P[off & (t <= 0)] = np.nan
    d = np.hypot(P[..., 0] - CENTRE[0], P[..., 1] - CENTRE[1])
    sky = ~np.isfinite(d)
    ds = cv2.GaussianBlur(np.where(sky, np.nanmax(d), d).astype(np.float32), (0, 0), 1.2)
    gy, gx = np.gradient(ds)
    grad = np.maximum(cv2.medianBlur(np.hypot(gx, gy).astype(np.float32), 5), 0.5)
    ang = np.degrees(np.arctan2(P[..., 0] - CENTRE[0], P[..., 1] - CENTRE[1])) % 360
    return {"ds": ds, "grad": grad, "ang": ang, "sky": sky}


def ring_cov(F: dict, radius: float, width_px: float) -> np.ndarray:
    return np.clip(1.0 - np.abs(F["ds"] - radius) / (F["grad"] * width_px / 2.0), 0.0, 1.0)


def blend(img: np.ndarray, cov: np.ndarray, rgb) -> np.ndarray:
    a = img.astype(np.float32) / 255.0
    a = a * (1 - cov[..., None]) + np.array(rgb, np.float32) * cov[..., None]
    return (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)


def overlay_zone(img: np.ndarray, F: dict, key: str) -> np.ndarray:
    return blend(img, zone_cov(F, key), np.array(RINGS[key]["rgb"], np.float32) / 255.0)


def zone_cov(F: dict, key: str, scale: float = 1.0) -> np.ndarray:
    """The zone's coverage (0-1) per pixel; `scale`: the image's width over W (its lines as many pixels wider)."""
    z = RINGS[key]
    ds, grad = F["ds"], F["grad"]
    cov = np.zeros(ds.shape, np.float32)
    if "band" in z:
        r0, r1 = z["band"]
        inside = np.clip((ds - r0) / grad + 0.5, 0, 1) * np.clip((r1 - ds) / grad + 0.5, 0, 1)
        if z.get("fade_out"):
            inside = inside * np.clip((r1 - ds) / (r1 - r0), 0, 1) ** 0.7
        cov = np.maximum(cov, inside * z["fill"])
        cov = np.maximum(cov, ring_cov(F, r0, 1.6 * scale) * z["edge"])
        cov = np.maximum(cov, ring_cov(F, r1, 1.6 * scale) * z.get("outer", z["edge"]))
    else:
        arc = (F["ang"] / 360.0 * 2 * math.pi * z["ring"]) % z["dash_m"]
        cov = ring_cov(F, z["ring"], 2.2 * scale) * (arc < z["dash_m"] * 0.55) * z["edge"]
    cov[F["sky"]] = 0
    return cov


def overlay_dome(img: np.ndarray, f: dict, dist: np.ndarray, F: dict, ss: int = 2) -> np.ndarray:
    return blend(img, dome_cov(f, dist, ss), DOME_RGB)


def dome_cov(f: dict, dist: np.ndarray, ss: int = 2) -> np.ndarray:
    """A smooth translucent hemisphere on the site circle: each pixel's ray met with it, far surface laid first and
    the near one over it; each surface's opacity fades with its height (nothing near the top) and rises where the ray
    meets it obliquely; hidden where the rendered ground stands nearer. Then the rim where it meets the ground. At the
    depth pass's size (the frame's or an oversized render's), worked at `ss` times it, then reduced."""
    h0, w0 = dist.shape
    sc = w0 / W   # an oversized render: the same view in more pixels
    w, h = w0 * ss, h0 * ss
    r = E.rays(f, (w, h))
    cam = np.array(f["location"], float)
    base = E.ground(CENTRE, {}) + 2.0
    ctr = np.array([CENTRE[0], CENTRE[1], base])
    R = SITE_R
    oc = cam - ctr
    b = r @ oc
    disc = b * b - (oc @ oc - R * R)
    hit = disc > 0
    sq = np.sqrt(np.maximum(disc, 0.0))
    seen = cv2.resize(np.where(np.isfinite(dist), dist, 1e6).astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
    acc = np.zeros((h, w), np.float32)
    for t in (-b + sq, -b - sq):   # the far surface, then the near
        p = cam + r * t[..., None]
        hgt = p[..., 2] - base
        ok = (hit & (t > 0) & (hgt >= 0)) * np.clip((seen + DOME_SOFT_M / 2 - t) / DOME_SOFT_M, 0, 1)
        n = (p - ctr) / R
        cosv = np.abs((n * r).sum(-1))
        g = np.clip(1.0 - hgt / (DOME_TOP * R), 0, 1) ** DOME_GAMMA * np.clip(hgt / DOME_FOOT_M, 0, 1)
        fres = DOME_FACE + (1 - DOME_FACE) * (1 - cosv) ** DOME_FRES
        a = (DOME_A * g * fres * ok).astype(np.float32)
        acc = a + acc * (1 - a)
    # the rim: the footprint circle at the terrain's height (not draped on roofs), hidden where the ground is nearer
    rim = np.zeros((h, w), np.float32)
    th = np.linspace(0, 2 * math.pi, 721)
    pts = np.array([[CENTRE[0] + R * math.sin(a), CENTRE[1] + R * math.cos(a), 0.0] for a in th])
    tz = np.load(E.SCENE / "terrain.npz")
    gi = np.clip(np.searchsorted(tz["y"], pts[:, 1]), 0, len(tz["y"]) - 1)
    gj = np.clip(np.searchsorted(tz["x"], pts[:, 0]), 0, len(tz["x"]) - 1)
    pts[:, 2] = tz["z"][gi, gj] + 2.0
    xy = E.project(f, pts)
    xy[:, :2] *= sc
    mid = (pts[:-1] + pts[1:]) / 2
    mx = np.clip(((xy[:-1, 0] + xy[1:, 0]) / 2).astype(int), 0, w0 - 1)
    my = np.clip(((xy[:-1, 1] + xy[1:, 1]) / 2).astype(int), 0, h0 - 1)
    t = np.linalg.norm(mid - cam, axis=1)
    vis = np.clip((dist[my, mx] + DOME_SOFT_M / 2 - t) / DOME_SOFT_M, 0, 1)
    vis = np.convolve(np.r_[vis[-20:], vis, vis[:20]], np.ones(41) / 41, "same")[20:-20]   # fades, never breaks
    for k in range(len(pts) - 1):
        (x0, y0, z0), (x1, y1, z1) = xy[k], xy[k + 1]
        if z0 <= 0 or vis[k] <= 0.01:
            continue
        cv2.line(rim, (int(x0 * ss * 16), int(y0 * ss * 16)), (int(x1 * ss * 16), int(y1 * ss * 16)),
                 float(DOME_RIM * vis[k]), max(1, round(1.4 * ss * sc)), cv2.LINE_AA, shift=4)
    acc = np.maximum(acc, rim)
    return cv2.resize(acc, (w0, h0), interpolation=cv2.INTER_AREA)


def arc_path(r: float, at_deg: float, span_deg: float) -> list[list[float]]:
    out = []
    for b in np.linspace(at_deg - span_deg / 2, at_deg + span_deg / 2, 9):
        out.append([CENTRE[0] + r * math.sin(math.radians(b)), CENTRE[1] + r * math.cos(math.radians(b))])
    return out


def ring_label(layer, f: dict, sf: dict, key: str) -> str:
    """The zone's name along its ring, at its preferred bearing, else the nearest bearing where it fits the frame."""
    z = RINGS[key]
    r = z["label_r"]
    span = math.degrees(560.0 / r) * (8 if r < 10000 else 5)
    lvl = sf.get("level_m") or 3.0
    for dev in [0] + [s * k for k in range(10, 181, 10) for s in (1, -1)]:
        path = E.densify(arc_path(r, z["label_at_deg"] + dev, span), 40.0)
        pts = np.array([[x, y, max(E.ground([x, y], sf), lvl) + 2] for x, y in path])
        xy = E.project(f, pts)
        if (xy[:, 2] > 0).all() and (xy[:, 0] > 30).all() and (xy[:, 0] < W - 30).all() and (xy[:, 1] > 30).all() \
                and (xy[:, 1] < H - 30).all():
            E._along(layer, {"text": z["label"], "style": f"zone_{key}"}, xy[:, :2], 1.0)
            return z["label"]
    return f"(not in frame: {z['label']})"


def block(layer, lines: list[str], x: float, y: float, styles: tuple[str, str], step: float) -> list[str]:
    for i, line in enumerate(lines):
        E._place(layer, {"text": line, "style": styles[0] if i == 0 else styles[1], "dot": False}, x, y + i * step, 1.0)
    return list(lines)


def base_image(raw: Path, dep: Path, f: dict, sf: dict) -> tuple[np.ndarray, np.ndarray]:
    img = np.asarray(Image.open(raw).convert("RGB"))
    dist = np.load(dep)
    return E.tilt_shift(img, E.blur_map(f, dist, *E.focal_plane(E.plane_points(sf)))), dist


def apply_palette(name: str) -> None:
    """The palette's colours on the zones, the dome and their labels (a label a little lighter than its zone)."""
    global DOME_RGB
    pal = P.PALETTES[name]
    lift = lambda c: tuple(int(round(255 - (255 - v) * 0.6)) for v in c)   # 40% toward white: reads on the dark ground
    for key in RINGS:
        RINGS[key]["rgb"] = tuple(int(x) for x in P.rgb(pal[key]) * 255 + 0.5)
        E.STYLE[f"zone_{key}"] = {"weight": "Semibold", "size": 15, "rgb": lift(RINGS[key]["rgb"]), "halo": 0.72,
                                  "tracking": 0.4}
    DOME_RGB = tuple(float(x) for x in P.rgb(pal["dome"]))
    d = tuple(int(x * 255 + 0.5) for x in DOME_RGB)
    E.STYLE["dome"] = dict(E.STYLE["dome"], rgb=lift(d))
    E.STYLE["dome_small"] = dict(E.STYLE["dome_small"], rgb=lift(tuple(int(v * 0.97) for v in d)))


def make(name: str, img: np.ndarray, dist: np.ndarray, f: dict, cam: dict, sf: dict, what: str) -> tuple[Path, list]:
    F = fields(f, dist)
    if what in RINGS:
        img = overlay_zone(img, F, what)
    if what == "dome":
        img = overlay_dome(img, f, dist, F)
    im = E.grade(img, E.GRADE, 1, cam["look"].get("grade") or {})
    layer = E.Layer()
    if what in RINGS:
        shown = [ring_label(layer, f, sf, what)]
    else:
        x, y, _ = E.project(f, np.array([[CENTRE[0] + SITE_R * 0.75, CENTRE[1] - SITE_R * 0.75, 30.0]]))[0]
        shown = block(layer, DOME_LABEL, float(x) + 34, float(y) + 30, ("dome", "dome_small"), 21)
    layer.onto(im)
    path = OUT / f"zones_{name}.png"
    im.save(path)
    return path, shown


# the dome's close-up: A2's direction, nearer the plant (same heading and pitch), a separate still render
CLOSE = {"target": [-60.0, 250.0, 20.0], "heading": -40.0, "pitch": -30.0, "dist": 4200.0, "lens": 30.0,
         "why": "the shot's direction, closer on the plant, so the dome and its words read"}
# the rings' wide view: the shot's heading, higher and further back, the whole 15 km ring in the frame (found by
# projecting the ring for headings -40..0, pitches -40..-70, 20-28 mm, 20-90 km: the widest fit); the haze thinned
# for it (visibility 1500 km: at 42 km the look's air greyed the land out); beyond the land's box (17 km W, 23 km E,
# 19.5 km S, 28.5 km N of the plant) the ground is the look's far plain, a flat drawn ground in the land's mean colour
WIDE = {"target": [-3.8, 151.2, 15.0], "heading": -40.0, "pitch": -45.0, "dist": 42500.0, "lens": 28.0,
        "haze_visibility_km": 1500.0,
        "why": "the whole 15 km ring on the ground, Nikopol and Marhanets at its edge, Enerhodar near the centre; as much "
               "of the 30 km ring as the frame holds"}
RING_STILLS = ["paz", "upz", "obs"]


def render_still(v: dict, folder: str, cam: dict) -> tuple[Path, float | None]:
    d = E.SCRATCH / folder
    if (d / "d_0001.npy").exists():
        return d, None
    d.mkdir(parents=True, exist_ok=True)
    keep = E.HAZE_VISIBILITY_KM
    E.HAZE_VISIBILITY_KM = v.get("haze_visibility_km", keep)
    E.camera_json([E.frame(cam, v, "present")], cam, d / "camera.json")
    E.HAZE_VISIBILITY_KM = keep
    return d, E.blender(d / "camera.json", d, "1", d / "blender.log")


def sheet(name: str, paths: list[Path]) -> Path:
    """The palette's four images side by side, half size, each labelled by its file."""
    from PIL import ImageDraw
    tw, th = W // 2, H // 2
    sh = Image.new("RGB", (tw * 2, th * 2), (0, 0, 0))
    dr = ImageDraw.Draw(sh)
    for k, p in enumerate(paths):
        sh.paste(Image.open(p).resize((tw, th), Image.LANCZOS), ((k % 2) * tw, (k // 2) * th))
        dr.text(((k % 2) * tw + 8, (k // 2) * th + 6), p.stem, fill=(255, 255, 255))
    out = OUT / f"zones_sheet_{name}.jpg"
    sh.save(out, quality=90)
    return out


def main(which: list[str]) -> None:
    t0 = time.time()
    cam = E.look3()
    sf = cam["frames"][E.STATES["present"]["frame"]]
    secs = {}
    dc, secs["close"] = render_still(CLOSE, "zones_close", cam)
    dw, secs["wide"] = render_still(WIDE, "zones_wide", cam)
    fc, fw = E.frame(cam, CLOSE, "present"), E.frame(cam, WIDE, "present")
    close = base_image(dc / "f_0001.png", dc / "d_0001.npy", fc, sf)
    wide = base_image(dw / "f_0001.png", dw / "d_0001.npy", fw, sf)
    bw = E.blur_map(fw, wide[1], *E.focal_plane(E.plane_points(sf)))
    done = {}
    for pal in which:
        apply_palette(pal)
        paths = [make(f"C_dome_{pal}", *close, fc, cam, sf, "dome")]
        paths += [make(f"wide_{key}_{pal}", *wide, fw, cam, sf, key) for key in RING_STILLS]
        done[pal] = {"stills": {p.name: s for p, s in paths}, "sheet": sheet(pal, [p for p, _ in paths]).name}
    doc = {"title": "The plant's zones: preview stills, one zone each, in four palettes", "report": REPORT,
           "centre": {"m": CENTRE, "lonlat": CENTRE_LONLAT,
                      "how": "the centre of the smallest circle round OSM way 28877213 (the plant's site), for the rings "
                             "and the dome alike; the six units' centroid (OSM power=generator ways 1572378821-30) lies "
                             "233 m from it, well under the guidance's precision (3-5 km, 15-30 km)"},
           "dome": {"footprint": "the smallest circle round OSM way 28877213, as the zoom-out's zone",
                    "radius_m": SITE_R, "height_m": SITE_R,
                    "opacity": {"max": DOME_A, "fades_to_nothing_at_height": f"{DOME_TOP:.0%} of the radius",
                                "height_gamma": DOME_GAMMA, "ground_soft_m": DOME_SOFT_M, "foot_m": DOME_FOOT_M,
                                "square_on": DOME_FACE, "obliqueness_power": DOME_FRES, "rim": DOME_RIM},
                    "label": DOME_LABEL,
                    "statement": "drawn: no size was ever published (Grossi: 'limited to the perimeter and the plant "
                                 "itself'); its shape and height are the film's; it fades to nothing toward its top, so it "
                                 "never closes: it was never agreed"},
           "rings": {k: {kk: vv for kk, vv in z.items() if kk != "rgb"} for k, z in RINGS.items()},
           "unsized": UNSIZED,
           "palettes": {k: P.PALETTES[k] for k in which}, "palette_check": "palettes.json",
           "note": "planning distances, not barriers: said here and in the README; no foot line on these previews "
                   "(the user: no other text while the zones are shown one by one)",
           "distances_from_centre_km": {"Enerhodar": 5.98, "Vodiane": 6.91, "Kamianka-Dniprovska": 13.44,
                                        "Marhanets": 13.66, "Nikopol": 16.13},
           "camera": {"C": CLOSE, "wide": WIDE},
           "wide_blur_px": {"max": round(float(bw.max()), 2), "mean": round(float(bw.mean()), 3),
                            "note": "the tilt-shift kept at the shot's settings: at 42 km the depth across the frame is "
                                    "small, so it softens only the frame's far and near edges a little (as a real lens's "
                                    "depth of field would at this distance)"},
           "far_plain": "beyond the land's box (17 km W, 23 km E, 19.5 km S, 28.5 km N of the plant) the ground is the "
                        "look's far plain, a flat drawn ground in the land's mean colour; the rings run on over it",
           "stills": done, "render_s": {"close": 49, "wide": 53, "note": "Blender still renders (picture and depth), "
                                         "cached in the scratchpad; this run: " + json.dumps(secs)}, "seconds": round(time.time() - t0),
           "safety": "no tower, substation, repair site or firing position marked; no claimed firing region"}
    (OUT / "zones.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False))
    for k, v in done.items():
        print(k, v)
    print(f"{time.time() - t0:.0f} s")


if __name__ == "__main__":
    main(sys.argv[1:] or list(P.PALETTES))
