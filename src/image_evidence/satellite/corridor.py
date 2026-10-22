"""The corridor: a box, the power lines in it (OpenStreetMap) and the grid every satellite pass is laid on.

Fixed once, by the first satellite job for it (`georef.json`), like a folder's `scope.json`: later passes, of any date,
are resampled onto the same grid, so the same stations and camera path fit every one of them.

- The grid is linear in longitude and latitude (as the data API returns crops, and as terrain.py does). Distances
  along the line and the camera path use a sinusoidal projection round the box's middle (x east = longitude x the
  local scale at each latitude, y north), true to within a fraction of a percent over a hundred kilometres; the film
  turns each frame into degrees by the local scale where it is.
- The lines are OpenStreetMap's `power=line` ways, with their own coordinates and the tags mappers gave them (today's
  map: a tower in the drained reservoir is where OSM has it, not where the imagery shows it). They are never detected
  from the pixels: at 10-30 m the wires don't show, and a pylon is a few pixels at best.
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx
import numpy as np

log = logging.getLogger(__name__)

OVERPASS = ("https://overpass-api.de/api/interpreter", "https://overpass.private.coffee/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter")
USER_AGENT = "frame-geo-evidence-pipeline/satellite (research; corridor lines, cached per corridor)"
JOIN_M = 80.0          # ways whose ends lie closer than this are joined into one line (more, with `join_m`, through
                       # a substation, where one line's end and the next one's start can be a kilometre apart)
CAMERA_STEP_M = 25.0   # camera path samples
POS_SIGMA_M = 150.0    # the camera's position is smoothed over this (no jolt at each pylon's kink)
HEADING_SIGMA_M = 1200.0  # and its heading over this, so the frame turns slowly
KZ = 110574.0          # m per degree of latitude (as terrain.py)


@dataclass(frozen=True)
class Grid:
    bbox: tuple[float, float, float, float]  # lon_min, lat_min, lon_max, lat_max
    m_per_px: float

    @property
    def lon0(self) -> float:
        return (self.bbox[0] + self.bbox[2]) / 2

    @property
    def lat0(self) -> float:
        return (self.bbox[1] + self.bbox[3]) / 2

    @property
    def kx(self) -> float:
        return 111320.0 * math.cos(math.radians(self.lat0))

    @property
    def width(self) -> int:
        return max(1, round((self.bbox[2] - self.bbox[0]) * self.kx / self.m_per_px))

    @property
    def height(self) -> int:
        return max(1, round((self.bbox[3] - self.bbox[1]) * KZ / self.m_per_px))

    def to_px(self, lon: float, lat: float) -> tuple[float, float]:
        """(column, row) in pixel units, 0 at the box's west and north edges."""
        w, s, e, n = self.bbox
        return (lon - w) / (e - w) * self.width, (n - lat) / (n - s) * self.height

    def to_lonlat(self, col: float, row: float) -> tuple[float, float]:
        w, s, e, n = self.bbox
        return w + col / self.width * (e - w), n - row / self.height * (n - s)

    def to_m(self, lon: float, lat: float) -> tuple[float, float]:
        return (lon - self.lon0) * self.kx, (lat - self.lat0) * KZ

    def to_json(self) -> dict[str, Any]:
        return {"bbox": list(self.bbox), "m_per_px": self.m_per_px, "width": self.width, "height": self.height,
                "lon0": round(self.lon0, 7), "lat0": round(self.lat0, 7), "kx": round(self.kx, 3), "kz": KZ}

    @classmethod
    def from_json(cls, d: dict[str, Any]) -> "Grid":
        return cls(bbox=tuple(d["bbox"]), m_per_px=float(d["m_per_px"]))


# ------------------------------------------------------------------ OpenStreetMap


def overpass_query(bbox: tuple[float, float, float, float]) -> str:
    w, s, e, n = bbox
    b = f"{s},{w},{n},{e}"
    return (f'[out:json][timeout:120];(way["power"~"^(line|cable)$"]({b});'
            f'node["power"~"^(tower|portal)$"]({b}););out tags geom;')


def fetch_power(bbox: tuple[float, float, float, float], http: httpx.Client, rounds: int = 5) -> dict[str, Any]:
    """The power lines and towers in the box, from Overpass."""
    return fetch_overpass(overpass_query(bbox), http, rounds)


def fetch_overpass(q: str, http: httpx.Client, rounds: int = 5) -> dict[str, Any]:
    """An Overpass query's reply with the query, server and time. The public servers are often at capacity: each round
    tries every server, then waits twice as long as before."""
    wait = 15
    for k in range(rounds):
        for url in OVERPASS:
            try:
                r = http.post(url, data={"data": q}, headers={"User-Agent": USER_AGENT}, timeout=180)
                if r.status_code == 200 and r.text.lstrip().startswith("{"):
                    return {"query": q, "server": url, "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                            "licence": "© OpenStreetMap contributors, ODbL 1.0", "reply": r.json()}
                log.info("Overpass %s: HTTP %d", url.split("/")[2], r.status_code)
            except httpx.HTTPError as e:
                log.info("Overpass %s: %s", url.split("/")[2], type(e).__name__)
        if k < rounds - 1:
            log.info("Overpass is busy; trying again in %d s", wait)
            time.sleep(wait)
            wait *= 2
    raise RuntimeError("OpenStreetMap's Overpass servers are all busy; try again in a few minutes")


def _length_m(coords: list[tuple[float, float]]) -> float:
    return sum(math.hypot((b[0] - a[0]) * 111320.0 * math.cos(math.radians((a[1] + b[1]) / 2)), (b[1] - a[1]) * KZ)
               for a, b in zip(coords, coords[1:]))


def to_sin(lon: float, lat: float, lon0: float, lat0: float) -> tuple[float, float]:
    """Metres east and north of (lon0, lat0) in a sinusoidal projection (true north-south, and east-west at every
    latitude; only far from lon0 does it shear)."""
    return (lon - lon0) * 111320.0 * math.cos(math.radians(lat)), (lat - lat0) * KZ


def from_sin(x: float, y: float, lon0: float, lat0: float) -> tuple[float, float]:
    lat = lat0 + y / KZ
    return lon0 + x / (111320.0 * math.cos(math.radians(lat))), lat


def ways(osm: dict[str, Any]) -> dict[int, dict[str, Any]]:
    out = {}
    for el in osm["reply"]["elements"]:
        if el["type"] == "way" and el.get("geometry"):
            coords = [(g["lon"], g["lat"]) for g in el["geometry"]]
            out[el["id"]] = {"id": el["id"], "tags": el.get("tags", {}), "coords": coords, "length_m": _length_m(coords)}
    return out


def towers(osm: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"id": el["id"], "lon": el["lon"], "lat": el["lat"], "tags": el.get("tags", {})}
            for el in osm["reply"]["elements"] if el["type"] == "node"]


def kv(tags: dict[str, str]) -> int:
    try:
        return max(int(v) for v in str(tags.get("voltage", "0")).split(";") if v.strip().isdigit()) // 1000
    except ValueError:
        return 0


def label(tags: dict[str, str]) -> str:
    """'330 kV Л-243;Л-244, Запорізька ТЕС → ПС "Феросплавна-330"' from the mappers' tags."""
    name = tags.get("ref") or tags.get("name") or tags.get("name:uk") or ""
    ends = f"{tags['from']} → {tags['to']}" if tags.get("from") and tags.get("to") else ""
    return ", ".join(x for x in (f"{kv(tags)} kV {name}".strip(), ends) if x)


def choices(osm: dict[str, Any], min_kv: int = 110, min_km: float = 0.5) -> list[dict[str, Any]]:
    """The lines worth following in the box, for the Satellite panel: high voltage first, then longest."""
    out = [{"id": w["id"], "label": label(w["tags"]), "kv": kv(w["tags"]), "length_m": round(w["length_m"])}
           for w in ways(osm).values() if kv(w["tags"]) >= min_kv and w["length_m"] >= min_km * 1000]
    return sorted(out, key=lambda c: (-c["kv"], -c["length_m"]))


def chain(all_ways: dict[int, dict[str, Any]], ids: list[int], join_m: float = JOIN_M,
          joins: list[dict[str, Any]] | None = None) -> list[tuple[float, float]]:
    """The ways in the order given, joined end to end into one line (each turned as it needs to be). Ends up to
    `join_m` apart are joined straight (through a substation); each such join is added to `joins`."""
    missing = [i for i in ids if i not in all_ways]
    if missing:
        raise ValueError(f"OpenStreetMap has no power line {missing[0]} in this box")
    pts = list(all_ways[ids[0]]["coords"])
    if len(ids) > 1:  # the first way is turned so its end meets the second
        nxt = all_ways[ids[1]]["coords"]
        if min(_gap(pts[0], nxt[0]), _gap(pts[0], nxt[-1])) < min(_gap(pts[-1], nxt[0]), _gap(pts[-1], nxt[-1])):
            pts.reverse()
    for i in ids[1:]:
        c = list(all_ways[i]["coords"])
        if _gap(pts[-1], c[-1]) < _gap(pts[-1], c[0]):
            c.reverse()
        gap = _gap(pts[-1], c[0])
        if gap > join_m:
            raise ValueError(f"power line {i} doesn't join the one before it ({gap:.0f} m apart)")
        if gap > 1 and joins is not None:
            joins.append({"before_way": i, "at_m": round(_length_m(pts), 1), "gap_m": round(gap, 1)})
        pts += c[1:] if gap <= 1 else c
    return pts


def _gap(a: tuple[float, float], b: tuple[float, float]) -> float:
    return _length_m([a, b])


def clip(coords: list[tuple[float, float]], bbox: tuple[float, float, float, float]) -> list[tuple[float, float]]:
    """The longest run of the line inside the box (cut at the box's edge)."""
    w, s, e, n = bbox
    inside = lambda p: w <= p[0] <= e and s <= p[1] <= n
    dense = []
    for a, b in zip(coords, coords[1:]):
        k = max(1, int(_gap(a, b) / 10))
        dense += [(a[0] + (b[0] - a[0]) * j / k, a[1] + (b[1] - a[1]) * j / k) for j in range(k)]
    dense.append(coords[-1])
    runs, run = [], []
    for p in dense:
        if inside(p):
            run.append(p)
        elif run:
            runs.append(run)
            run = []
    if run:
        runs.append(run)
    if not runs:
        raise ValueError("the chosen line doesn't pass through the box")
    return max(runs, key=_length_m)  # (in steps of 10 m or less; every original vertex inside is kept)


def _resample(xy: np.ndarray, step: float) -> tuple[np.ndarray, np.ndarray]:
    seg = np.hypot(*np.diff(xy, axis=0).T)
    along = np.concatenate([[0], np.cumsum(seg)])
    s = np.arange(0, along[-1] + 1e-6, step)
    if s[-1] < along[-1]:
        s = np.append(s, along[-1])
    return s, np.stack([np.interp(s, along, xy[:, 0]), np.interp(s, along, xy[:, 1])], axis=1)


def _gauss(v: np.ndarray, sigma_samples: float) -> np.ndarray:
    if sigma_samples < 0.5:
        return v
    r = int(3 * sigma_samples)
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma_samples) ** 2)
    k /= k.sum()
    pad = np.pad(v, ((r, r), (0, 0)), mode="edge")
    return np.stack([np.convolve(pad[:, j], k, mode="valid") for j in range(v.shape[1])], axis=1)


def camera_path(grid: Grid, coords: list[tuple[float, float]], step: float = CAMERA_STEP_M) -> dict[str, Any]:
    """Samples along the line: distance along it, the camera's smoothed position and the way it travels (compass
    bearing, 0 = north). The position follows the line within ~10 m; the heading turns over a kilometre or so."""
    xy = np.array([to_sin(lon, lat, grid.lon0, grid.lat0) for lon, lat in coords])
    along, pts = _resample(xy, step)
    pos = _gauss(pts, POS_SIGMA_M / step)
    slow = _gauss(pts, HEADING_SIGMA_M / step)
    d = np.gradient(slow, axis=0)
    heading = np.degrees(np.unwrap(np.arctan2(d[:, 0], d[:, 1])))
    samples = []
    for s, (x, y), h in zip(along, pos, heading):
        lon, lat = from_sin(x, y, grid.lon0, grid.lat0)
        samples.append([round(float(s), 1), round(lon, 7), round(lat, 7), round(float(h), 2)])
    return {"step_m": step, "fields": ["along_m", "lon", "lat", "heading_deg"], "samples": samples,
            "smoothing": f"position smoothed over {POS_SIGMA_M:g} m, heading over {HEADING_SIGMA_M:g} m (Gaussian sigma)"}


def stations(coords: list[tuple[float, float]], spacing_m: float) -> list[dict[str, Any]]:
    """Evenly spaced points on the line, its two ends included (the centres of the chips)."""
    lon0, lat0 = (min(c[0] for c in coords) + max(c[0] for c in coords)) / 2, (min(c[1] for c in coords) + max(c[1] for c in coords)) / 2
    along, pts = _resample(np.array([to_sin(*c, lon0, lat0) for c in coords]), 1.0)
    n = max(1, round(along[-1] / spacing_m))
    out = []
    for k in range(n + 1):
        s = along[-1] * k / n
        lon, lat = from_sin(*pts[min(len(pts) - 1, int(round(s)))], lon0, lat0)
        out.append({"station": k + 1, "along_m": round(float(s), 1), "lon": round(lon, 7), "lat": round(lat, 7)})
    return out


def build(corridor_id: str, name: str, bbox: tuple[float, float, float, float], line_ids: list[int],
          osm: dict[str, Any], m_per_px: float, chip_size_m: float, chip_spacing_m: float, join_m: float = JOIN_M,
          strip_m: float | None = None) -> dict[str, Any]:
    """georef.json for a new corridor."""
    all_ways = ways(osm)
    joins: list[dict[str, Any]] = []
    coords = clip(chain(all_ways, line_ids, join_m, joins), bbox)
    grid = Grid(bbox=bbox, m_per_px=m_per_px)
    first = all_ways[line_ids[0]]["tags"]
    labels = list(dict.fromkeys(label(all_ways[i]["tags"]) for i in line_ids))
    # A way without a name or ref is just its voltage: say it once, in the named ways' labels.
    labels = [x for x in labels if not any(y != x and y.startswith(x + " ") for y in labels)]
    context = [{"id": w["id"], "kv": kv(w["tags"]), "label": label(w["tags"]),
                "coords": [[round(x, 7), round(y, 7)] for x, y in w["coords"]]}
               for w in all_ways.values() if kv(w["tags"]) >= 110]
    tw = towers(osm)
    cam = camera_path(grid, coords)
    joined = (f" ({len(joins)} join{'' if len(joins) == 1 else 's'} straight across a substation, at most "
              f"{max(j['gap_m'] for j in joins):.0f} m)") if joins else ""
    return {
        "schema": "corridor/1", "corridor_id": corridor_id, "name": name,
        "grid": grid.to_json(), "chip_size_m": chip_size_m, "chip_spacing_m": chip_spacing_m, "strip_m": strip_m,
        "line": {"ways": line_ids, "label": " · ".join(labels) if len(labels) > 1 else labels[0], "labels": labels,
                 "kv": kv(first), "joins": joins,
                 "length_m": round(_length_m(coords), 1), "coords": [[round(x, 7), round(y, 7)] for x, y in coords]},
        "context_lines": context,
        "towers": [t for t in tw if t["tags"].get("tower:type") or t["tags"].get("design") or t["tags"].get("disused")],
        "tower_count": len(tw),
        "stations": stations(coords, chip_spacing_m),
        "camera": cam,
        "reference_pass": None,
        "osm": {"server": osm["server"], "fetched_at": osm["fetched_at"], "licence": osm["licence"]},
        "provenance": [
            {"label": "Line", "evidence": f"OpenStreetMap power=line ways {', '.join(map(str, line_ids))} ({'; '.join(labels)}), "
             f"joined end to end{joined} "
             f"and cut to the box; fetched {osm['fetched_at'][:10]} from {osm['server'].split('/')[2]} "
             "(© OpenStreetMap contributors, ODbL). Today's map, with the mappers' own coordinates: not detected in the imagery."},
            {"label": "Grid", "evidence": f"{grid.width}×{grid.height} pixels of about {m_per_px:g} m, linear in longitude and "
             f"latitude over {bbox}" + (f"; imagery only within {strip_m / 1000:g} km of the line" if strip_m else "")
             + "; distances by the local scale at each place."},
            {"label": "Camera", "evidence": "The camera follows the line: " + cam["smoothing"]
             + ". A path for viewing, not an observation."},
        ],
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
