"""What the crossing's 3D scenes are built from, in the zoom-out's plane (metres east and north of the plant).

Pass 0, the survey (`survey`): the data check before any scene is built.
- The two lines: the network's traced lines (OSM ways, `network.json`), cut to the window north of the plant.
- Their towers: each vertex of a line matched to a `power=tower` node of the corridor's saved Overpass reply (the same
  point in OSM, so within a metre); the node's own tags kept (`tower:type=crossing`, `fixme`, `design`).
- Where they cross (Dniprovska passes over Ferosplavna's row north of the thermal plant), and from there north the
  gap between them.
- The water along each line, on passes already on the corridor's grid: clear pixels with NIR and SWIR reflectance
  under 3% (`stitch.Mosaic.water`), sampled every SAMPLE_M along the line; water runs closer than MERGE_M (islands,
  reeds) are one stretch.
- The flight path: the midline between the two lines, point by point at the same northing, from where they cross to
  `flight_until_km`. A viewing path, not an observation.
- Heights under it: FABDEM (the ground without trees and buildings; 2011-15, so the reservoir is water in it), the
  same tiles and cache as `scripts/scene/terrain.py`.
"""

from __future__ import annotations

import io
import json
import logging
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import cv2
import httpx
import numpy as np
import requests
from PIL import Image, ImageDraw

from ...layout import write_json
from ..corridor import KZ, Grid
from ..network import network_dir
from ..schema import SatellitePass
from ..store import corridor_dir
from ..stitch import TileSet
from ..zoomout import Plane

log = logging.getLogger(__name__)

SAMPLE_M = 20.0      # water sampled this often along a line
MERGE_M = 300.0      # water runs closer than this along a line are one stretch (islands, reeds, a pier)
TOWER_M = 1.0        # a line's vertex is a tower when an OSM tower node is this close (the same OSM point)
STEP_M = 50.0        # the flight path's points, by northing
FABDEM = "https://data.bris.ac.uk/datasets/s5hqmjcdj8yo2ibzi9b4ew3sn"
FABDEM_CACHE = Path.home() / ".cache" / "evidence-terrain"
COLOURS = {750: (255, 214, 10), 330: (255, 159, 10)}
WIRE_KINDS = ["phase", "jumper", "bundle", "earth"]  # towers.npz wire_kind: sub-conductors, jumpers, glow, earth


def scene_dir(root: Path, network_id: str) -> Path:
    return network_dir(root, network_id) / "scenes" / "crossing3d"


# ------------------------------------------------------------------ geometry (plain arrays, metres)

def crossing_point(a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, int, int] | None:
    """The first point (along a) where polylines a and b cross, with the segment of each it lies on."""
    for i in range(len(a) - 1):
        p, r = a[i], a[i + 1] - a[i]
        for j in range(len(b) - 1):
            q, s = b[j], b[j + 1] - b[j]
            den = r[0] * s[1] - r[1] * s[0]
            if abs(den) < 1e-9:
                continue
            t = ((q - p)[0] * s[1] - (q - p)[1] * s[0]) / den
            u = ((q - p)[0] * r[1] - (q - p)[1] * r[0]) / den
            if 0 <= t <= 1 and 0 <= u <= 1:
                return p + t * r, i, j
    return None


def from_point(a: np.ndarray, seg: int, p: np.ndarray) -> np.ndarray:
    """Polyline a from point p (on segment seg) to its end."""
    return np.vstack([p, a[seg + 1:]])


def x_at(a: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Easting of polyline a at northings y; a must run north."""
    if np.any(np.diff(a[:, 1]) <= 0):
        raise ValueError("the line turns back south here: no single easting for a northing")
    return np.interp(y, a[:, 1], a[:, 0], left=np.nan, right=np.nan)


def midline(a: np.ndarray, b: np.ndarray, y0: float, y1: float, step: float = STEP_M) -> dict[str, np.ndarray]:
    """The midpoint between two north-running lines at each northing from y0 to y1, and the gap between them."""
    y = np.append(np.arange(y0, y1, step), y1)
    xa, xb = x_at(a, y), x_at(b, y)
    return {"xy": np.stack([(xa + xb) / 2, y], 1), "gap": np.abs(xa - xb)}


def snap(xy: np.ndarray, nodes: np.ndarray, max_m: float = TOWER_M) -> np.ndarray:
    """For each point, the index of the node within max_m of it, or -1."""
    if not len(nodes):
        return np.full(len(xy), -1)
    d = np.hypot(xy[:, None, 0] - nodes[None, :, 0], xy[:, None, 1] - nodes[None, :, 1])
    k = d.argmin(1)
    return np.where(d[np.arange(len(xy)), k] <= max_m, k, -1)


def along(a: np.ndarray, step: float = SAMPLE_M) -> tuple[np.ndarray, np.ndarray]:
    """Points every step metres along polyline a: (distance along, xy)."""
    cum = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(a, axis=0).T))])
    s = np.append(np.arange(0.0, cum[-1], step), cum[-1])
    return s, np.stack([np.interp(s, cum, a[:, 0]), np.interp(s, cum, a[:, 1])], 1)


def stretches(wet: np.ndarray, s: np.ndarray, merge_m: float = MERGE_M) -> list[tuple[float, float, float]]:
    """Stretches of water along a line from per-sample water flags: (start, end, share of samples wet), runs closer
    than merge_m joined."""
    out: list[list[float]] = []
    for k in np.flatnonzero(wet):
        if out and s[k] - out[-1][1] <= merge_m:
            out[-1][1] = s[k]
        else:
            out.append([s[k], s[k]])
    return [(a, b, float(wet[(s >= a) & (s <= b)].mean())) for a, b in out]


# ------------------------------------------------------------------ data

def fabdem_tile(lat: int, lon: int, cache: Path = FABDEM_CACHE) -> Path:
    """FABDEM V1-2's 1° tile, read from its 10° zip at the University of Bristol by range requests (cached)."""
    p = cache / f"N{lat:02d}E{lon:03d}_FABDEM_V1-2.tif"
    if p.exists():
        return p
    import zipfile

    class Remote(io.RawIOBase):
        def __init__(self, url):
            self.url, self.pos = url, 0
            self.size = int(requests.head(url, timeout=60).headers["Content-Length"])

        def seekable(self):
            return True

        def readable(self):
            return True

        def tell(self):
            return self.pos

        def seek(self, o, whence=0):
            self.pos = {0: o, 1: self.pos + o, 2: self.size + o}[whence]
            return self.pos

        def readinto(self, b):
            if not len(b) or self.pos >= self.size:
                return 0
            r = requests.get(self.url, headers={"Range": f"bytes={self.pos}-{self.pos + len(b) - 1}"}, timeout=300)
            r.raise_for_status()
            b[:len(r.content)] = r.content
            self.pos += len(r.content)
            return len(r.content)

    cache.mkdir(parents=True, exist_ok=True)
    z0, z1 = lat // 10 * 10, lon // 10 * 10
    url = f"{FABDEM}/N{z0:02d}E{z1:03d}-N{z0 + 10:02d}E{z1 + 10:03d}_FABDEM_V1-2.zip"
    log.info("FABDEM: %s from %s", p.name, url)
    z = zipfile.ZipFile(io.BufferedReader(Remote(url), 1 << 20))
    tmp = p.with_suffix(".part")
    tmp.write_bytes(z.read(next(n for n in z.namelist() if n.endswith(p.name))))
    tmp.replace(p)
    return p


def heights(lonlat: np.ndarray, cache: Path = FABDEM_CACHE) -> np.ndarray:
    """FABDEM heights (m) at lon/lat points (bilinear), the tiles fetched as needed."""
    out = np.full(len(lonlat), np.nan)
    keys = np.floor(lonlat[:, ::-1]).astype(int)  # (lat, lon) of each point's tile
    for la, lo in {tuple(k) for k in keys}:
        sel = (keys[:, 0] == la) & (keys[:, 1] == lo)
        dem = cv2.imread(str(fabdem_tile(la, lo, cache)), cv2.IMREAD_UNCHANGED).astype(np.float32)
        n = dem.shape[0]  # 3600: one arcsecond; the tile's pixel centres
        col = ((lonlat[sel, 0] - lo) * n).astype(np.float32)
        row = ((la + 1 - lonlat[sel, 1]) * n).astype(np.float32)
        k = len(col)
        w = 4096  # remap takes at most 32767 a side: the points in rows
        pad = -k % w
        cr = [np.pad(a, (0, pad)).reshape(-1, w) for a in (col, row)]
        out[sel] = cv2.remap(dem, *cr, cv2.INTER_LINEAR).ravel()[:k]
    return out


def _at(z: np.ndarray, xs: np.ndarray, ys: np.ndarray, xy) -> float:
    """A grid's value at a point (bilinear; xs, ys its regular axes)."""
    fx = float(np.clip((xy[0] - xs[0]) / (xs[1] - xs[0]), 0, len(xs) - 1.001))
    fy = float(np.clip((xy[1] - ys[0]) / (ys[1] - ys[0]), 0, len(ys) - 1.001))
    i, j, a, b = int(fy), int(fx), fy % 1, fx % 1
    return float((1 - a) * ((1 - b) * z[i, j] + b * z[i, j + 1]) + a * ((1 - b) * z[i + 1, j] + b * z[i + 1, j + 1]))


def _water_colours(root: Path, cfg: dict[str, Any], out: Path, layers: list[dict[str, Any]],
                   bdoc: dict[str, Any]) -> list[list[float]]:
    """The water's colour in each pass (linear RGB): the median of its pixels where the water was seen that day (the
    bed's `seen_*`), else where the bed lies under the level then, a metre or more."""
    from . import bed
    from .. import network
    bz = np.load(bed.bed_dir(out) / "bed.npz")
    fp, zb = bz["footprint"], bz["z"]
    g = Grid(tuple(float(x) for x in bz["bbox"]), float(bz["m_per_px"]))
    rows, cols = np.mgrid[0:g.height, 0:g.width]
    lon, lat = g.to_lonlat(cols + 0.5, rows + 0.5)
    res = []
    for ly in layers:
        im = np.asarray(Image.open(network.network_dir(root, cfg["id"]) / ly["file"]).convert("RGB"))
        lg = Grid.from_json(ly["grid"])
        c, r = lg.to_px(lon, lat)
        im = cv2.remap(im, (c - 0.5).astype(np.float32), (r - 0.5).astype(np.float32), cv2.INTER_LINEAR,
                       borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        key = f"seen_water_{ly['acquired'][:10]}"
        if key in bz.files:
            m = bz[key] & fp & (im.sum(-1) > 0)
        else:
            m = fp & (np.nan_to_num(zb, nan=99) < bed.level(bdoc["levels"], ly["acquired"]) - 1.0) & (im.sum(-1) > 0)
        m = cv2.erode(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)   # away from the shores
        c_ = np.median(im[m], axis=0) / 255.0 if m.sum() > 100 else np.array([0.12, 0.14, 0.13])
        res.append([round(float(np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)), 4) for x in c_])
    return res


def _sheets(out: Path, surfaces: list[np.ndarray], ll: np.ndarray, z: np.ndarray) -> dict[str, np.ndarray]:
    """The water seen on each later pass as one sheet on the land's grid, a height per vertex per pass (crossfaded
    by the passes' shares, build.py): at the water's surface where the pass saw water; on the vertices next to it
    just over the surface (or under the ground, whichever is lower), so the shore falls between them where the
    sheet meets the ground; elsewhere a metre under the ground, hidden. Only round where any pass saw water."""
    from . import bed
    wets, hs = [], []
    for h in surfaces:
        wet = np.isfinite(h)
        wets.append(bed.on_grid(out, wet.astype(np.float32), ll).reshape(z.shape) >= 0.5)
        hs.append(bed.on_grid(out, _nearest(np.nan_to_num(h, nan=0.0), wet), ll).reshape(z.shape))
    k3 = np.ones((3, 3), np.uint8)
    region = cv2.dilate(np.any(wets, 0).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    zs = []
    for wet, h in zip(wets, hs):
        near = cv2.dilate(wet.astype(np.uint8), k3).astype(bool) & ~wet
        zs.append(np.where(wet, h, np.where(near, np.minimum(z - 0.3, h + 0.05), z - 1.0))[region])
    return {"sheet_region": region, "sheet_z": np.stack(zs).astype(np.float32)}


def _sheets_edge(out: Path, surfaces: list[np.ndarray], ll: np.ndarray, z: np.ndarray) -> dict[str, np.ndarray]:
    """As `_sheets`, for a look with `water.smooth_edge` (look pass 3): the sheet at the water's surface over the water
    and two vertices beyond it (the renderer cuts it at the sub-pixel contour, look.water_edge), then a metre under
    the ground, hidden; so the shore is drawn where the contour is, not where a 20 m quad meets the ground."""
    from . import bed
    wets, hs = [], []
    for h in surfaces:
        wet = np.isfinite(h)
        wets.append(bed.on_grid(out, wet.astype(np.float32), ll).reshape(z.shape) >= 0.5)
        hs.append(bed.on_grid(out, _nearest(np.nan_to_num(h, nan=0.0), wet), ll).reshape(z.shape))
    region = cv2.dilate(np.any(wets, 0).astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
    zs = []
    for wet, h in zip(wets, hs):
        near = cv2.dilate(wet.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
        zs.append(np.where(near, h, z - 1.0)[region])
    return {"sheet_region": region, "sheet_z": np.stack(zs).astype(np.float32)}


def _nearest(a: np.ndarray, have: np.ndarray) -> np.ndarray:
    """a everywhere from its nearest pixel where `have` is (a as it is where none)."""
    if not have.any():
        return a.astype(np.float32)
    _, lab = cv2.distanceTransformWithLabels((~have).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    rr, cc = np.nonzero(have)
    src = np.zeros(lab.max() + 1, np.float32)
    src[lab[rr, cc]] = a[rr, cc]
    return src[lab].astype(np.float32)


def _lonlat(pl: Plane, xy: np.ndarray) -> np.ndarray:
    return np.stack([xy[:, 0] / pl.kx + pl.lon0, xy[:, 1] / KZ + pl.lat0], 1)


def _window(a: np.ndarray, y0: float, y1: float) -> tuple[np.ndarray, bool]:
    """Polyline a from its start until it first leaves northings [y0, y1] (that vertex kept), and whether it was cut
    there (else it runs to its end, the substation)."""
    out = np.flatnonzero((a[:, 1] < y0) | (a[:, 1] > y1))
    after = out[out > 0]
    return (a[:after[0] + 1], True) if len(after) else (a, False)


def _towers_reply(root: Path, cfg: dict[str, Any], out: Path, http: Any = None) -> dict[str, Any]:
    """OSM's towers over the land's box (raw/osm_power.json, saved verbatim, fetched once): the lines' towers beyond
    the corridor's reply, on north to the box's edge."""
    from .. import network
    from ..corridor import fetch_power
    path = out / "raw" / "osm_power.json"
    if not path.is_file():
        tex = network._layer(root, cfg, cfg["crossing3d"]["texture"], None)
        path.parent.mkdir(parents=True, exist_ok=True)
        with (http or httpx.Client()) as client:
            write_json(path, fetch_power(tuple(tex["grid"]["bbox"]), client))
    return json.loads(path.read_text())


def _plant_reply(out: Path, pc: dict[str, Any], http: Any = None) -> dict[str, Any]:
    """OSM's buildings, chimneys and towers round the plant, the thermal plant and Enerhodar (raw/osm_plant.json, saved
    verbatim, fetched once)."""
    from ..corridor import fetch_overpass
    from .plant import query
    path = out / "raw" / "osm_plant.json"
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        with (http or httpx.Client()) as client:
            write_json(path, fetch_overpass(query(tuple(pc["bbox"])), client))
    return json.loads(path.read_text())


SHARED_M = 25.0      # a line's vertex within this of a line drawn before it is on a shared row (drawn once)


def _towers_south(root: Path, cfg: dict[str, Any], out: Path, http: Any = None) -> dict[str, Any]:
    """OSM's towers over the land on south (raw/osm_power_south.json, saved verbatim, fetched once): the plant's
    other lines leave that way."""
    from .. import network
    from ..corridor import fetch_power
    path = out / "raw" / "osm_power_south.json"
    if not path.is_file():
        ly = network._layer(root, cfg, cfg["crossing3d"]["land_south"]["layers"][0], None)
        path.parent.mkdir(parents=True, exist_ok=True)
        with (http or httpx.Client()) as client:
            write_json(path, fetch_power(tuple(ly["grid"]["bbox"]), client))
    return json.loads(path.read_text())


def _in_box(a: np.ndarray, box: tuple[float, float, float, float]) -> tuple[np.ndarray, bool]:
    """Polyline a from its start until it first leaves the box (that vertex kept), and whether it was cut there."""
    x0, y0, x1, y1 = box
    out = np.flatnonzero((a[:, 0] < x0) | (a[:, 0] > x1) | (a[:, 1] < y0) | (a[:, 1] > y1))
    after = out[out > 0]
    return (a[:after[0] + 1], True) if len(after) else (a, False)


def _seg_dist(p: np.ndarray, a: np.ndarray) -> np.ndarray:
    """Each point's distance to polyline a."""
    s0, s1 = a[:-1], a[1:]
    d = s1 - s0
    t = np.clip(((p[:, None] - s0[None]) * d[None]).sum(-1) / np.maximum((d * d).sum(-1), 1e-9)[None], 0, 1)
    q = s0[None] + t[..., None] * d[None]
    return np.hypot(*(p[:, None] - q).transpose(2, 0, 1)).min(1)


def other_rows(net: dict[str, Any], oc: dict[str, Any], pl: Plane, box, drawn: list[np.ndarray]) -> list[dict[str, Any]]:
    """The plant's other lines (`oc["lines"]`, by network name and kV), the units' feeds into the 750 kV switchyard
    and the NPP-TPP 330 kV links, as polylines in the plane: each from its end nearest the plant (so `along` runs out
    from it and the flow toward the plant runs back along it), cut at the land's edge (`box`), and where it starts on a
    row already drawn (`drawn`, then each before it: two circuits on one row of towers) from the tower where it parts,
    that tower drawn once (`hidden`). A row wholly on another is left out."""
    want = [({"name": f"{d['name']} {d['kv']}", "kv": int(d["kv"]), "record": d["record"]},
             next(ln for ln in net["lines"] if ln["name"] == d["name"] and ln["kv"] == d["kv"])["coords"])
            for d in oc.get("lines", [])]
    for key, label in (("feeds", "feed"), ("links", "link")):
        if oc.get(key):
            want += [({"name": f"{label} {i}", "kv": int(ln.get("kv") or (750 if key == "feeds" else 330)),
                       "follows": oc[key]["follows"]}, ln["coords"]) for i, ln in enumerate(net[key], start=1)]
    rows, prior = [], list(drawn)
    for meta, coords in want:
        a = pl.xy(coords)
        if np.hypot(*a[-1]) < np.hypot(*a[0]):
            a = a[::-1]
        a, cut = _in_box(a, box)
        start, hidden = 0, False
        if prior:
            near = np.min([_seg_dist(a, p) for p in prior], axis=0) <= SHARED_M
            off = np.flatnonzero(~near)
            if not len(off):
                continue
            if off[0] > 0:
                start, hidden = int(off[0]) - 1, True
        a = a[start:]
        if len(a) < 2:
            continue
        rows.append({**meta, "xy": a, "cut": cut, "hidden_first": hidden})
        prior.append(a)
    return rows


def _others(root: Path, cfg: dict[str, Any], out: Path, pl: Plane, net: dict[str, Any], main: list[dict[str, Any]],
            ground, box, types: dict[str, Any], cat: dict[str, float], south: dict[str, Any] | None) -> dict[str, Any] | None:
    """The plant's other lines for a variant's `extras: [others]` (the flight south, the user, 4 November 2026):
    other_rows' polylines, a tower at each vertex where OSM has one (the land's replies), drawn as its land type, the
    wires hung between them (no fittings: too small to see this far), in others.npz like towers.npz."""
    oc = cfg["crossing3d"].get("others")
    if not oc:
        return None
    from . import towers
    reps = [json.loads((out / "raw" / "osm_power.json").read_text())] + ([_towers_south(root, cfg, out)] if south else [])
    nodes = {e["id"]: e for r in reps for e in r["reply"]["elements"]
             if e["type"] == "node" and (e.get("tags") or {}).get("power") == "tower"}
    tws = list(nodes.values())
    txy = pl.xy([[e["lon"], e["lat"]] for e in tws]) if tws else np.zeros((0, 2))
    rows = other_rows(net, oc, pl, box, [np.array([t["xy"] for t in ln["towers"]]) for ln in main])
    lines = []
    for r in rows:
        k = snap(r["xy"], txy)
        tw = []
        for i, (p, j) in enumerate(zip(r["xy"], k)):
            e = tws[j] if j >= 0 else None
            tw.append({"xy": [round(float(p[0]), 1), round(float(p[1]), 1)], "kind": str(r["kv"]) if e else "portal",
                       "osm_node": e["id"] if e else None, "tags": {t: v for t, v in (e.get("tags") or {}).items()
                                                                   if t != "power"} if e else {},
                       "hidden": bool(i == 0 and r["hidden_first"])})
        lines.append({**{k_: v for k_, v in r.items() if k_ not in ("xy", "hidden_first")}, "towers": tw})
    towers.assign(lines, {})
    for ln in lines:
        drawn = [t for t in ln["towers"] if t["type"]]
        for t, rz in zip(drawn, towers.headings(drawn)):
            t["rot_z"], t["base_m"] = round(rz, 6), round(float(ground(t["xy"])), 2)
    ws = towers.wires(lines, {k: a for k, (_, a) in types.items()}, cat)
    np.savez_compressed(out / "others.npz",
                        wire_pts=np.concatenate([w["pts"] for w in ws]).astype(np.float32),
                        wire_n=np.array([len(w["pts"]) for w in ws], np.int32),
                        wire_along=np.concatenate([w["along"] for w in ws]).astype(np.float32),
                        wire_cross=np.concatenate([w["cross"] for w in ws]).astype(np.float32),
                        wire_line=np.array([w["line"] for w in ws], np.int32),
                        wire_kind=np.array([WIRE_KINDS.index(w["kind"]) for w in ws], np.uint8))
    km = {ln["name"]: round(sum(float(np.hypot(*np.subtract(b["xy"], a["xy"]))) for a, b in
                                zip(ln["towers"], ln["towers"][1:])) / 1000, 1) for ln in lines}
    return {"file": "others.npz", "lines": lines, "km": km,
            "towers": {"files": ["raw/osm_power.json"] + (["raw/osm_power_south.json"] if south else []),
                       **{k: reps[-1].get(k) for k in ("server", "fetched_at", "licence")}},
            "statement": "The plant's other lines (network.json, traced through OpenStreetMap), cut where the land "
                         "ends (said so): the three other 750 kV lines and the four other 330 kV lines, by their "
                         "states in the record by date (sources in the record: the other 750 kV lines cut before "
                         "September 2022; the other 330 kV lines unreported, dotted, until 29 December 2022, then cut). "
                         "The units' feeds into the 750 kV switchyard and the NPP-TPP 330 kV links, which no report "
                         "names: lit while the line that feeds them is (Dniprovska; Ferosplavna-1), the path the "
                         "power must take into the plant: inferred, not reported. A row shared by two lines drawn "
                         "once. Towers at OSM's points, drawn as the land types (representative); no fittings."}


def _land_south(root: Path, cfg: dict[str, Any], out: Path, pl: Plane, ys_main: np.ndarray, step: float,
                n_layers: int) -> dict[str, Any] | None:
    """The land on south of the box (the flight south looks that way): the same passes over a strip of their own,
    FABDEM under them, its last row the land's first so the two meet (terrain_south.npz)."""
    from .. import network
    ls = cfg["crossing3d"].get("land_south")
    if not ls:
        return None
    layers = [network._layer(root, cfg, ly, None) for ly in ls["layers"]]
    if len(layers) != n_layers:
        raise ValueError(f"land_south needs a layer for each of the land's {n_layers} passes, in the same order")
    g = Grid.from_json(layers[0]["grid"])
    w, s, e, n = g.bbox
    xs = np.arange(math.ceil((w - pl.lon0) * pl.kx / step) * step, (e - pl.lon0) * pl.kx, step)
    ys = np.arange(math.ceil((s - pl.lat0) * KZ / step) * step, float(ys_main[0]) + step / 2, step)
    gx, gy = np.meshgrid(xs, ys)
    ll = _lonlat(pl, np.stack([gx.ravel(), gy.ravel()], 1))
    z = heights(ll).reshape(gx.shape).astype(np.float32)
    u = ((ll[:, 0] - w) / (e - w)).reshape(gx.shape).astype(np.float32)
    v = ((ll[:, 1] - s) / (n - s)).reshape(gx.shape).astype(np.float32)
    np.savez_compressed(out / "terrain_south.npz", x=xs.astype(np.float32), y=ys.astype(np.float32), z=z, u=u, v=v)
    return {"file": "terrain_south.npz", "size": [len(xs), len(ys)],
            "textures": [{"file": str((network_dir(root, cfg["id"]) / ly["file"]).resolve()), "pass": ly["pass_id"],
                          "acquired": ly["acquired"], "attribution": ly["attribution"]} for ly in layers],
            "statement": "The land south of the box, for the flight south: the same passes on a strip of their own "
                         "(crossfaded by the same dates), FABDEM heights; the reservoir there, where there is any, is "
                         "FABDEM's flat water (the drained bed's relief is only modelled inside the bed's box)"}


def survey(root: Path, cfg: dict[str, Any], http: Any = None) -> dict[str, Any]:
    """Pass 0: the two lines, their towers, the water, the flight path and the heights under it (survey.json)."""
    c3 = cfg["crossing3d"]
    net = json.loads((network_dir(root, cfg["id"]) / "network.json").read_text())
    pl = Plane(*net["plant"]["lonlat"])
    by_name = {ln["name"]: ln for ln in net["lines"]}
    names = c3["lines"]
    y0, y1 = (float(v) * 1000 for v in c3["window_km"])
    lines, cut = zip(*(_window(pl.xy(by_name[n]["coords"]), y0, y1) for n in names))

    cdir = corridor_dir(root, c3["towers_from"])
    georef = json.loads((cdir / "georef.json").read_text())
    osm = json.loads((cdir / "raw" / "osm_power.json").read_text())
    towers = [e for e in osm["reply"]["elements"] if e["type"] == "node" and (e.get("tags") or {}).get("power") == "tower"]
    more = _towers_reply(root, cfg, scene_dir(root, cfg["id"]), http)   # the corridor's first, as before
    have = {e["id"] for e in towers}
    towers += [e for e in more["reply"]["elements"] if e["type"] == "node" and e["id"] not in have
               and (e.get("tags") or {}).get("power") == "tower"]
    txy = pl.xy([[e["lon"], e["lat"]] for e in towers]) if towers else np.zeros((0, 2))

    hit = crossing_point(*lines)
    if hit is None:
        raise ValueError(f"{names[0]} and {names[1]} don't cross in the window")
    pcross, ia, ib = hit
    north = [from_point(lines[0], ia, pcross), from_point(lines[1], ib, pcross)]
    until = float(c3["flight_until_km"]) * 1000
    north = [a[:np.searchsorted(a[:, 1], until) + 1] for a in north]
    mid = midline(*north, float(pcross[1]), until)

    grid = Grid.from_json(georef["grid"])
    passes = {}
    for pid in c3["water_passes"]:
        p = SatellitePass.model_validate_json((cdir / "passes" / pid / "pass.json").read_text())
        passes[pid] = (p, TileSet(root, p.files, grid))
    lonlat_all = _lonlat(pl, np.vstack(lines))
    c, r = grid.to_px(lonlat_all[:, 0], lonlat_all[:, 1])
    pad = 80
    rows = slice(max(0, int(r.min()) - pad), min(grid.height, int(r.max()) + pad))
    cols = slice(max(0, int(c.min()) - pad), min(grid.width, int(c.max()) + pad))

    mosaics = {pid: ts.mosaic(rows, cols) for pid, (_, ts) in passes.items()}
    doc_lines, water = [], {pid: {} for pid in passes}
    for name, a, was_cut in zip(names, lines, cut):
        ln = by_name[name]
        k = snap(a, txy)
        ll = _lonlat(pl, a)
        verts = [{"xy_m": [round(float(x), 1), round(float(y), 1)], "lonlat": [round(float(lo), 7), round(float(la), 7)],
                  "tower": ({"osm_node": towers[j]["id"], "tags": {t: v for t, v in towers[j].get("tags", {}).items() if t != "power"}}
                            if j >= 0 else None)} for (x, y), (lo, la), j in zip(a, ll, k)]
        crossing = [v for v in verts if v["tower"] and v["tower"]["tags"].get("tower:type") == "crossing"]
        spans = [round(float(np.hypot(*(np.array(q["xy_m"]) - np.array(p_["xy_m"]))))) for p_, q in zip(crossing, crossing[1:])]
        doc_lines.append({"name": name, "kv": ln["kv"], "ways": ln["ways"], "vertices": verts, "cut": was_cut,
                          "towers_matched": int((k >= 0).sum()), "vertex_count": len(a),
                          "crossing_towers": [v["tower"]["osm_node"] for v in crossing], "crossing_spans_m": spans})
        s, pts = along(a)
        sll = _lonlat(pl, pts)
        pc, pr = grid.to_px(sll[:, 0], sll[:, 1])
        pc, pr = pc.astype(int) - cols.start, pr.astype(int) - rows.start
        inn = (pr >= 0) & (pr < rows.stop - rows.start) & (pc >= 0) & (pc < cols.stop - cols.start)
        s, pts, pc, pr = s[inn], pts[inn], pc[inn], pr[inn]   # the water only where the corridor's passes are
        for pid, m in mosaics.items():
            clear, wet = m.clear[pr, pc], m.water[pr, pc]
            water[pid][name] = {
                "clear_share": round(float(clear.mean()), 3),
                "stretches": [{"from_m": round(a_), "to_m": round(b_), "north_m": [round(float(np.interp(a_, s, pts[:, 1]))),
                                                                                  round(float(np.interp(b_, s, pts[:, 1])))],
                               "wet_share": round(sh, 2)} for a_, b_, sh in stretches(wet, s) if b_ - a_ >= MERGE_M],
            }

    mll = _lonlat(pl, mid["xy"])
    h = heights(mll)
    tower_h = {}
    for d in doc_lines:
        tw = [v for v in d["vertices"] if v["tower"]]
        hh = heights(np.array([v["lonlat"] for v in tw]))
        tower_h[d["name"]] = [{"osm_node": v["tower"]["osm_node"], "north_m": v["xy_m"][1], "ground_m": round(float(x), 1)}
                              for v, x in zip(tw, hh) if -1500 <= v["xy_m"][1] <= y1]
    seg = np.hypot(*np.diff(mid["xy"], axis=0).T)
    head = math.degrees(math.atan2(*(mid["xy"][-1] - mid["xy"][0])))

    out = scene_dir(root, cfg["id"])
    out.mkdir(parents=True, exist_ok=True)
    doc = {
        "schema": "crossing3d-survey/1", "network_id": cfg["id"],
        "made_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "plane": {"lon0": pl.lon0, "lat0": pl.lat0, "kx": round(pl.kx, 3), "kz": KZ,
                  "note": "metres east (x) and north (y) of the plant, as zoomout.Plane: Blender X, Y; Z up"},
        "window_north_m": [y0, y1],
        "lines": doc_lines,
        "lines_cross_at": {"xy_m": [round(float(v), 1) for v in pcross],
                           "lonlat": [round(float(v), 7) for v in _lonlat(pl, pcross[None])[0]],
                           "note": f"{names[0]} passes over {names[1]}'s row of towers here"},
        "flight": {
            "from_north_m": round(float(pcross[1])), "to_north_m": round(until), "length_m": round(float(seg.sum())),
            "heading_deg": round(head, 1),
            "gap_m": {"min": round(float(np.nanmin(mid["gap"]))), "median": round(float(np.nanmedian(mid["gap"]))),
                      "max": round(float(np.nanmax(mid["gap"])))},
            "points": [{"xy_m": [round(float(x), 1), round(float(y), 1)], "gap_m": round(float(g), 1),
                        "ground_m": round(float(z), 1)} for (x, y), g, z in zip(mid["xy"], mid["gap"], h)],
            "statement": "A viewing path (the midline between the two lines at each northing), not an observation.",
        },
        "water": {pid: {"acquired": p.source.acquired_at.isoformat(), "platform": p.source.platform, "lines": water[pid]}
                  for pid, (p, _) in passes.items()},
        "heights": {"towers": tower_h,
                    "source": "FABDEM V1-2 (Hawker et al. 2022, University of Bristol, CC BY-NC-SA 4.0): Copernicus GLO-30 "
                              "(TanDEM-X 2011-2015) with forests and buildings removed; the reservoir is water in it"},
        "sources": {
            "lines": {"file": "network.json", "osm": net.get("osm")},
            "towers": {"file": f"satellite/corridors/{c3['towers_from']}/raw/osm_power.json",
                       **{k: osm.get(k) for k in ("server", "fetched_at", "licence")},
                       "beyond": {"file": "raw/osm_power.json", **{k: more.get(k) for k in ("server", "fetched_at")}}},
            "water": "clear pixels with NIR and SWIR reflectance under 3% on the corridor's passes (stitch.Mosaic.water)",
        },
    }
    write_json(out / "survey.json", doc)
    _sheet(out / "survey.webp", lines, names, net, txy, towers, mid, pcross, passes, grid, pl, rows, cols)
    return doc


def _sheet(path, lines, names, net, txy, towers, mid, pcross, passes, grid, pl, rows, cols) -> None:
    """The check image: each water pass side by side, the lines, their towers (crossing towers larger), where they
    cross and the flight path drawn on it."""
    panels = []
    for pid, (p, ts) in passes.items():
        im = Image.fromarray(ts.rgb(rows, cols))
        d = ImageDraw.Draw(im)

        def px(xy):
            ll = _lonlat(pl, np.atleast_2d(xy))
            c, r = grid.to_px(ll[:, 0], ll[:, 1])
            return list(zip((c - cols.start).tolist(), (r - rows.start).tolist()))

        by = {ln["name"]: ln for ln in net["lines"]}
        for n, a in zip(names, lines):
            d.line(px(a), fill=COLOURS.get(by[n]["kv"], (255, 255, 255)), width=2)
        for e, (x, y) in zip(towers, txy):
            if any(np.min(np.hypot(a[:, 0] - x, a[:, 1] - y)) < TOWER_M for a in lines):
                big = (e.get("tags") or {}).get("tower:type") == "crossing"
                (cx, cy), = px([x, y])
                rr = 4 if big else 2
                d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=(255, 255, 255) if big else (200, 200, 200))
        d.line(px(mid["xy"]), fill=(80, 220, 255), width=1)
        (cx, cy), = px(pcross)
        d.ellipse([cx - 7, cy - 7, cx + 7, cy + 7], outline=(255, 59, 48), width=2)
        d.text((8, 8), f"{p.source.platform} {p.source.acquired_at:%Y-%m-%d}", fill=(255, 255, 255))
        panels.append(im)
    w = sum(i.width for i in panels) + 8 * (len(panels) - 1)
    sheet = Image.new("RGB", (w, panels[0].height), (0, 0, 0))
    x = 0
    for i in panels:
        sheet.paste(i, (x, 0))
        x += i.width + 8
    sheet.save(path, "WEBP", quality=90)


# ------------------------------------------------------------------ pass 1: the grey-box scene

LOOK_STATEMENT = (
    "A look pass (the variant's `look`): drawn, not observed: the overcast sky and its clouds (noise), the sun and the "
    "sky's light on the towers, caissons and plant (Blender lamps), the light haze of the air by distance "
    "(Koschmieder, at the visibility given), the plain beyond the land's box (the land's mean colour), the water's "
    "darker, bluer tint, its ripples and reflections (a planar mirror where asked), its colour by depth over the "
    "inferred bed (a neutral bottom tone in the shallows, never a later pass's pixels), the wet band on the bed just "
    "left by the water (darker and glossier, drying over the days given, by height between the levels then and now), "
    "the caissons' concrete (darker at the water's line), the cut wires' colour, the grade (view transform, saturation, "
    "tint, grain, vignette), bloom and motion blur. Positions, heights, levels, dates and the passes' pixels stay as "
    "sourced; the passes colour-matched as said in `match_statement`.")


VEGETATION_VERSION = 2


def _vegetation(root: Path, cfg: dict[str, Any], out: Path, vc: dict[str, Any], track: np.ndarray,
                plane: dict[str, Any], tower_xy: np.ndarray) -> dict[str, Any]:
    """vegetation.npz and its doc (vegetation.py), made again only when its options, the camera's track or the
    version change (vegetation.json keeps the doc and what it was made from)."""
    import hashlib
    from . import vegetation
    key = hashlib.sha256(json.dumps([VEGETATION_VERSION, {k: vc.get(k) for k in ("seed", "spacing")}], sort_keys=True).encode()
                         + np.round(track, 1).tobytes() + np.round(tower_xy, 1).tobytes()).hexdigest()[:16]
    cache = out / "vegetation.json"
    if cache.is_file() and (out / "vegetation.npz").is_file():
        doc = json.loads(cache.read_text())
        if doc.get("key") == key:
            return {k: v for k, v in doc.items() if k != "key"}
    log.info("Vegetation: placing the plants (vegetation.py)")
    doc = vegetation.build(root, cfg, out, vc, track, plane, tower_xy)
    write_json(cache, {**doc, "key": key})
    return doc


def _detail(out: Path, types: dict[str, Any], ws: list[dict[str, Any]], lines: list[dict[str, Any]],
            tcfg: dict[str, Any]) -> dict[str, Any]:
    """towers_detail.npz: towers.npz with the detailed meshes and fittings (the same attachment points, so the same
    wires; refused if any differs)."""
    from . import towers
    base = towers.build_types()
    def flat(v: Any) -> list[float]:
        return [x for e in v for x in flat(e)] if isinstance(v, (list, tuple)) else list(np.ravel(np.asarray(v, float)))

    for k, (_, a) in types.items():
        b = base[k][1]
        if a.keys() != b.keys() or any(len(flat(a[n])) != len(flat(b[n])) or
                                       not np.allclose(flat(a[n]), flat(b[n])) for n in a if n != "kv"):
            raise ValueError(f"{k}: the detailed tower's attachment points differ from the approved one's")
    arrays = {f"{k}__{n}": arr for k, (m, _) in types.items() for n, arr in m.arrays().items()}
    arrays |= {f"fittings__{n}": arr for n, arr in towers.fittings(ws, [ln["kv"] for ln in lines], detail=True).arrays().items()}
    old = np.load(out / "towers.npz")
    arrays |= {k: old[k] for k in old.files if k.startswith("wire_")}
    np.savez_compressed(out / "towers_detail.npz", **arrays)
    return {"file": "towers_detail.npz", "types": {k: int(len(m.counts)) for k, (m, _) in types.items()},
            "statement": towers.DETAIL_STATEMENT}


def scene(root: Path, cfg: dict[str, Any]) -> dict[str, Any]:
    """The animatic's scene (scene.json + terrain.npz) and the camera of each opening (camera_<variant>.json), from the
    survey (made first if missing)."""
    from .. import network, zoomout
    from . import bed, camera, states, towers

    c3 = cfg["crossing3d"]
    out = scene_dir(root, cfg["id"])
    sv_path = out / "survey.json"
    sv = json.loads(sv_path.read_text()) if sv_path.is_file() else survey(root, cfg)
    net = json.loads((network_dir(root, cfg["id"]) / "network.json").read_text())
    pl = Plane(*net["plant"]["lonlat"])

    # the land: FABDEM on a regular grid in the plane over the texture's box, with each vertex's place in the texture
    tex = network._layer(root, cfg, c3["texture"], None)
    tg = Grid.from_json(tex["grid"])
    # the drained bed: a later pass on the same grid (the zoom-out's own crop), dissolved in where the camera says
    after = network._layer(root, cfg, c3["texture_after"], None) if c3.get("texture_after") else None
    if after and after["grid"] != tex["grid"]:
        raise ValueError(f"{after['name']} isn't on {tex['name']}'s grid: a dissolve needs the same pixels in the same place")
    w, s, e, n = tg.bbox
    step = float(c3["terrain_step_m"])
    xs = np.arange(math.ceil((w - pl.lon0) * pl.kx / step) * step, (e - pl.lon0) * pl.kx, step)
    ys = np.arange(math.ceil((s - pl.lat0) * KZ / step) * step, (n - pl.lat0) * KZ, step)
    gx, gy = np.meshgrid(xs, ys)
    ll = _lonlat(pl, np.stack([gx.ravel(), gy.ravel()], 1))
    z = heights(ll).reshape(gx.shape).astype(np.float32)
    u = ((ll[:, 0] - w) / (e - w)).reshape(gx.shape).astype(np.float32)
    v = ((ll[:, 1] - s) / (n - s)).reshape(gx.shape).astype(np.float32)  # Blender's v runs up from the image's bottom
    # pass 3: the drained bed (bed.py) inside the reservoir's footprint, FABDEM's flat reservoir replaced by it; the
    # shore's first row of FABDEM raised to the full level where it lies under it (FABDEM's water's edge is a metre or
    # two low), so the water never stands over the land; the water's surface over the footprint, raised and lowered
    # to the level each frame
    bdoc, layers, water_rgb = None, [], []
    if c3.get("bed"):
        bdoc = json.loads((bed.bed_dir(out) / "bed.json").read_text())
        layers = [tex] + [network._layer(root, cfg, ly, None) | {k: ly[k] for k in ("shown_from", "fade_days", "why")
                                                                  if k in ly} for ly in c3["bed"]["textures"]["layers"]]
        for ly in layers:
            if ly["grid"] != tex["grid"]:
                raise ValueError(f"{ly['name']} isn't on {tex['name']}'s grid: a crossfade needs the same pixels in the same place")
        # the water seen on each later pass (the layers' own days), the bed carved under it
        days = [ly["acquired"][:10] for ly in layers[1:]]
        zc, surfaces, sheet_info = bed.sheets(out, bdoc, days)
        zb, f = bed.sample(out, ll, z=zc)
        zb, f = zb.reshape(z.shape), f.reshape(z.shape)
        full = float(bdoc["reference"]["level_m"])
        inside = f > 0
        ring = cv2.dilate(inside.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & ~inside
        shore = np.where(ring, np.maximum(z, full + 0.1), z)
        z = np.where(inside, f * np.nan_to_num(zb, nan=full) + (1 - f) * np.maximum(shore, full + 0.1), shore)
        z = z.astype(np.float32)
        wet = cv2.dilate(inside.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
        x_at = (float(bdoc["river_slope"]["at_lon"]) - pl.lon0) * pl.kx   # the surface tilts about the crossing
        sheet = _sheets(out, surfaces, ll, z)
        np.savez_compressed(out / "water.npz", mask=wet, pivot_x=x_at, **sheet)
        if any(((v.get("look") or {}).get("water") or {}).get("smooth_edge") for v in c3["animatic"]["variants"].values()):
            np.savez_compressed(out / "water_edge.npz", **_sheets_edge(out, surfaces, ll, z))   # look pass 3
        water_rgb = _water_colours(root, cfg, out, layers, bdoc)
    np.savez_compressed(out / "terrain.npz", x=xs.astype(np.float32), y=ys.astype(np.float32), z=z, u=u, v=v)

    # towers and wires (pass 4, towers.py): every vertex of the two lines, a tower at its OSM point drawn as its type,
    # the conductors and earth wires hung between them
    lines = []
    for ln in sv["lines"]:
        vx = ln["vertices"]
        ground = heights(np.array([q["lonlat"] for q in vx]))
        tw = []
        for q, g in zip(vx, ground):
            t = q["tower"]
            kind = "portal" if t is None else ("crossing" if t["tags"].get("tower:type") == "crossing" else str(ln["kv"]))
            tw.append({"xy": q["xy_m"], "ground_m": round(float(g), 2), "kind": kind,
                       "osm_node": t["osm_node"] if t else None, "tags": t["tags"] if t else {}})
        lines.append({"name": ln["name"], "kv": ln["kv"], "towers": tw, "cut": bool(ln.get("cut"))})
    tcfg = c3["towers"]
    towers.assign(lines, tcfg["schemes"])
    types = towers.build_types()
    for ln in lines:
        drawn = [t for t in ln["towers"] if t["type"]]
        for t, rz in zip(drawn, towers.headings(drawn)):
            t["rot_z"] = round(rz, 6)
            if t["caisson"]:   # on its caisson: set to the normal level (the reservoir's, not FABDEM's flat water)
                t["caisson_m"] = towers.POOL_M if bdoc else t["ground_m"]
                t["base_m"] = round(t["caisson_m"] + towers.WATER_UP_M, 2)
            else:
                t["base_m"] = round(float(_at(z, xs, ys, t["xy"])) if bdoc else t["ground_m"], 2)
    # the flow is fullest over the water: the reservoir on the survey's first water pass (the day before the dam broke)
    reservoir = sv["water"][c3["water_passes"][0]]["lines"]
    ws = towers.wires(lines, {k: a for k, (_, a) in types.items()}, {k: float(v) for k, v in tcfg["catenary_m"].items()},
                      {n: [tuple(st["north_m"]) for st in w["stretches"]] for n, w in reservoir.items()})
    arrays = {f"{k}__{n}": arr for k, (m, _) in types.items() for n, arr in m.arrays().items()}
    arrays |= {f"fittings__{n}": arr for n, arr in towers.fittings(ws, [ln["kv"] for ln in lines]).arrays().items()}
    np.savez_compressed(out / "towers.npz", **arrays,
                        wire_pts=np.concatenate([w["pts"] for w in ws]).astype(np.float32),
                        wire_n=np.array([len(w["pts"]) for w in ws], np.int32),
                        wire_along=np.concatenate([w["along"] for w in ws]).astype(np.float32),
                        wire_cross=np.concatenate([w["cross"] for w in ws]).astype(np.float32),
                        wire_line=np.array([w["line"] for w in ws], np.int32),
                        wire_kind=np.array([WIRE_KINDS.index(w["kind"]) for w in ws], np.uint8))

    # for the flight south (S6): the plant, the thermal plant and Enerhodar modelled (plant.py), and the land on south
    plant_doc = None
    if c3.get("plant"):
        from . import plant
        m, plant_doc = plant.build(_plant_reply(out, c3["plant"]), pl.xy, lambda q: _at(z, xs, ys, q))
        np.savez_compressed(out / "plant.npz", **m.arrays())
        plant_doc = {"file": "plant.npz", "osm": "raw/osm_plant.json", **plant_doc}
    south = _land_south(root, cfg, out, pl, ys, step, len(layers) if layers else 1)
    others_doc = None
    if c3.get("others"):   # the plant's other lines, its feeds and links (extras: [others]); heights off the land drawn
        sz = np.load(out / "terrain_south.npz") if south else None
        others_doc = _others(root, cfg, out, pl, json.loads((network_dir(root, cfg["id"]) / "network.json").read_text()),
                             lines, lambda q: _at(z, xs, ys, q) if sz is None or q[1] >= ys[0]
                             else _at(sz["z"], sz["x"], sz["y"], q),
                             (float(xs[0]), float(sz["y"][0] if sz is not None else ys[0]), float(xs[-1]), float(ys[-1])),
                             types, {k: float(v) for k, v in tcfg["catenary_m"].items()}, south)

    o = c3["animatic"]
    types_detail = (towers.build_types(detail=True)
                    if any((v.get("look") or {}).get("detail") for v in o["variants"].values()) else None)
    zone = (cfg.get("record") or {}).get("zone")
    centre, _ = zoomout._site_circle(network_dir(root, cfg["id"]), zone["around"], pl) if zone else (np.zeros(2), 0.0)
    flight = np.array([p["xy_m"] for p in sv["flight"]["points"]])
    gaps = np.array([p["gap_m"] for p in sv["flight"]["points"]])
    cross = float(sv["lines_cross_at"]["xy_m"][1])
    land = cross + float(o.get("land_after_m", 0))
    _, _, off = camera.axis(flight, gaps)
    cams, looks, tracks = {}, {}, {}
    for variant, v in o["variants"].items():
        at = cross + float(v.get("land_after_m", o.get("land_after_m", 0)))
        if v.get("track"):   # a track of its own: south toward the plant (the user, 4 November 2026)
            fr = camera.frames_track(variant, o, flight, gaps, int(o["fps"]))
        else:
            fr = camera.frames(variant, o, centre, flight, gaps, at, int(o["fps"]))
        doc = {"variant": variant, "fps": int(o["fps"]), "frames": fr, "extras": list(v.get("extras") or []),
               "statement": "A viewing path, designed; not an observation."}
        tracks[variant] = np.array([f["location"][:2] for f in fr])
        if v.get("record"):  # the two lines' record: each frame's line states, date and drain (pinned to its date)
            ro = states.options(c3, v)
            rec, rdoc = states.record(cfg["record"], ro)
            for x in ro.get("select") or []:   # look pass 3: a date placed by where the camera is, checked
                if x.get("along_m") is not None:
                    got = fr[min(len(fr) - 1, round(float(x["s"]) * int(o["fps"])))]["along_m"]
                    if abs(got - float(x["along_m"])) > float(x.get("along_tol_m", 100)):
                        raise ValueError(f"{variant}: {x['at']} at {x['s']} s finds the camera {got:.0f} m along, "
                                         f"not {x['along_m']} m: move its `s`")
                    for dd in rdoc.get("dates", []):
                        if dd["date"] == str(x["at"]):
                            dd["camera_along_m"] = {"placed_at": float(x["along_m"]), "found": got}
            for f, x in zip(fr, states.per_frame(rec, ro, len(fr), int(o["fps"]))):
                f.update(x)
            if bdoc:   # the water's level and the bed's imagery by the record's day (fractional) at each frame
                for i, f in enumerate(fr):
                    day = rec.days(i / int(o["fps"]))
                    when = datetime.fromordinal(int(day)).replace(tzinfo=timezone.utc) + timedelta(days=day % 1)
                    lv_m, slope_m = bed.drawn(bdoc, when)
                    f["level_m"], f["water_slope"] = round(lv_m, 3), round(slope_m, 7)
                    f["textures"] = bed.texture_weights(layers, day, float(c3["bed"]["textures"]["fade_days"]))
                    f["water_rgb"] = [round(sum(wt * c[k] for wt, c in zip(f["textures"], water_rgb)), 4) for k in range(3)]
            if others_doc and "others" in (v.get("extras") or []):   # the plant's other rows, by the date shown
                for f, x in zip(fr, states.others_per_frame(cfg["record"], ro, others_doc["lines"], rec, fr, int(o["fps"]))):
                    f["others"] = x
            if c3.get("flow"):  # which way the power runs (states.flow_toward), drawn along the connected lines
                fo = states.flow_config(c3["flow"], v)
                for f in fr:
                    f["flow"] = states.flow_toward(fo, f.get("date"))
                doc["flow"] = states.flow_doc(fo)
            doc["record"] = rdoc
            if v.get("look"):   # a look pass (look.py): its options for build.py, the pass before the breach, the wet band
                from . import look as look_mod
                south_layers = ([network._layer(root, cfg, ly, None) for ly in c3["land_south"]["layers"]]
                                if c3.get("land_south") else [])
                looks[variant] = look_mod.prepare(root, cfg, out, v["look"], layers or [tex], south_layers)
                look_mod.per_frame(v["look"], fr, [rec.days(i / int(o["fps"])) for i in range(len(fr))], bdoc)
                if v["look"].get("vegetation"):   # look pass 2: the plants, placed by rule from the dated passes
                    tw = np.array([t["xy"] for ln in lines + (others_doc["lines"] if others_doc else [])
                                   for t in ln["towers"] if t.get("type")], float)
                    # placed along this variant's track, or another's (`track_from`: look pass 3 keeps look 2's
                    # placement, so the cache is shared and neither moves a plant)
                    tf = v["look"]["vegetation"].get("track_from")
                    if tf and tf not in tracks:
                        raise ValueError(f"{variant}: vegetation track_from {tf!r} must be a variant listed before it")
                    looks[variant]["vegetation"] = _vegetation(root, cfg, out, v["look"]["vegetation"],
                                                               tracks[tf] if tf else tracks[variant], sv["plane"], tw)
                if v["look"].get("detail"):   # look pass 2: the towers and fittings in more detail
                    looks[variant]["detail"] = _detail(out, types_detail, ws, lines, tcfg)
                lw = v["look"].get("water") or {}
                if lw.get("smooth_edge") and bdoc:   # look pass 3: the river sheet's edge drawn sub-pixel
                    looks[variant]["water_edge"] = {"sheet": "water_edge.npz", **look_mod.water_edge(
                        out, [ly["acquired"][:10] for ly in layers[1:]], pl, float(lw["smooth_edge"].get("sigma_px", 0.35)))}
                if lw.get("detail") and bdoc:   # look pass 3: the passes' own colour variation over their water
                    pbl = (v["look"].get("pre_breach") or {}).get("land")
                    vd = lw["detail"].get("variation") or {}
                    looks[variant]["water_variation"] = look_mod.water_variation(
                        root, cfg, out, layers, looks[variant], network._layer(root, cfg, pbl, None) if pbl else None,
                        tuple(vd.get("clamp", (0.75, 1.3))), float(vd.get("sigma_px", 1.0)))
                doc["look"] = v["look"]
        write_json(out / f"camera_{variant}.json", doc)
        cams[variant] = len(fr)

    doc = {
        "schema": "crossing3d-scene/1", "pass": "animatic", "network_id": cfg["id"],
        "made_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "plane": sv["plane"],
        "terrain": {"file": "terrain.npz", "step_m": step, "size": [len(xs), len(ys)],
                    "texture": str((network_dir(root, cfg["id"]) / tex["file"]).resolve()),
                    "texture_pass": tex["pass_id"], "attribution": tex["attribution"],
                    "statement": "FABDEM heights, true to size (never exaggerated); the pre-war Sentinel-2 pass only "
                                 "resampled; shaded a little by each slope's turn toward a fixed sun so the relief "
                                 "reads (a drawn hillshade: level ground as the imagery has it)",
                    **({"textures": [{"file": str((network_dir(root, cfg["id"]) / ly["file"]).resolve()),
                                      "pass": ly["pass_id"], "acquired": ly["acquired"], "attribution": ly["attribution"],
                                      "water_rgb": wrgb, "why": ly.get("why"),
                                      **({"water": str(bed.layer_water(root, cfg, ly, out).resolve())} if i else {})}
                                     for i, (ly, wrgb) in enumerate(zip(layers, water_rgb))],
                        "textures_statement": "each pass shown from its date, crossfaded into the next (an "
                                              "interpolation between two dates, said so); only resampled",
                        "bed": {"file": "bed/bed.json", "statement": bdoc["statement"], "tiers": bdoc["tiers"],
                                "icesat2_check": bdoc["icesat2_check"]},
                        "water": {"file": "water.npz", "levels": "bed/bed.json levels",
                                  "drawn": bdoc["drawn"], "river_slope": bdoc["river_slope"],
                                  "seen": {"passes": sheet_info, "depth_m": list(bed.SHEET_DEPTH),
                                           "handover": {"days": bed.HANDOVER_DAYS, "m": bed.HANDOVER_M}},
                                  "statement": "The water's surface is modelled. While the reservoir drains, one "
                                               "surface at the level reported for the frame's date (gauges; "
                                               "bed.json), capped once settled (`drawn`), sloping along the river "
                                               "as SWOT measures it. Once settled it sinks away and the water is "
                                               "drawn where each later pass saw it (`seen`: the river at the level "
                                               "reported that day), crossfaded from one pass to the next with the imagery (an "
                                               "interpolation between two dates, said so); the bed under it is "
                                               "carved down to it (inferred); the pools and narrow channels each "
                                               "pass saw (its 10 m mask, `textures[].water`) drawn as water on the "
                                               "land. Its colour the median of the water "
                                               "in each pass, its ripples and reflections drawn (Blender), never "
                                               "observed"}}
                       if bdoc else {}),
                    **({"texture_after": {"file": str((network_dir(root, cfg["id"]) / after["file"]).resolve()),
                                          "pass": after["pass_id"], "attribution": after["attribution"],
                                          "statement": "the drain is a dissolve between the two passes' imagery (an "
                                                       "interpolation between two dates, not the water's real fall); "
                                                       "the bed's relief is FABDEM's flat reservoir until pass 3"}}
                       if after and not bdoc else {})},
        "lines": lines,
        "towers": {"file": "towers.npz", "types": towers.TYPE_DOC, "sources": towers.SOURCES,
                   "materials": {str(k): v for k, v in towers.MATERIALS.items()},
                   "catenary_m": tcfg["catenary_m"], "water_up_m": towers.WATER_UP_M,
                   "fittings": towers.FITTINGS_DOC, "wire_kinds": WIRE_KINDS,
                   "statement": "Positions from OpenStreetMap; each tower drawn as its type (OSM tags and the crossings' "
                                "schemes), heights and caissons from the sources named, shapes, fittings and colours "
                                "modelled from photographs of these towers: representative, not surveyed. Each phase's "
                                "sub-conductors and the earth wires hung between the modelled clamps with a "
                                "representative sag, at their real size but drawn at least a little over half a pixel "
                                "wide however far, and a glow round each connected phase: drawing conventions."},
        **({"plant": plant_doc} if plant_doc else {}),
        **({"land_south": south} if south else {}),
        **({"others": others_doc} if others_doc else {}),
        "render": {"size": o["size"], "fps": int(o["fps"]), "haze_m": [float(k) * 1000 for k in o["haze_km"]]},
        "cameras": cams,
        **({"look": {k: {**x, "statement": LOOK_STATEMENT} for k, x in looks.items()}} if looks else {}),
        "camera_axis": {"max_off_midline_m": round(off, 1), "lands_north_m": round(land),
                        "statement": "The camera flies the straight axis of the stretch where the two lines run parallel "
                                     "(the midline between them there, within the figure given); a viewing path."},
        "start_centre_m": [round(float(c), 1) for c in centre],
    }
    write_json(out / "scene.json", doc)
    return doc
