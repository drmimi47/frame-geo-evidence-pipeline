"""Add satellite passes to a corridor: the steps behind `evidence satellite fetch` and the site's Satellite panel.

1. The corridor (once): the area gate, the power lines from OpenStreetMap, `georef.json`.
2. A pass: the clearest overpass of the sensor between two dates that covers what the corridor needs (its strip round
   the line, or only round the line's first `until_km`) and isn't stored yet.
3. Stitched onto the grid tile by tile, laid on the corridor's reference pass, cut into chips, written with its sources.
4. Exposure: every chip after the dam's destruction is compared with the last pass before it, when there is one.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import cv2
import httpx
import numpy as np
import yaml

from .. import __version__
from ..layout import write_json
from ..schema import Provenance
from ..scope import UKRAINE_BBOX, Scope
from . import corridor as corr
from .providers import PROVIDER, SENSORS, Sensor, acquired, item_url, overpasses, search
from .schema import PassDerived, PassFiles, PassSource, SatellitePass, pass_id_for
from .store import corridor_dir, read_chips, read_georef, read_passes
from .schema import TileFile
from .stitch import BREACH, DISPLAY, TileSet, coregister, cut_chips, exposure, need_mask, tiles
from .stitch import fetch as fetch_mosaic

log = logging.getLogger(__name__)

DEFAULT_CONFIG = Path("config/conductive-seam.yaml")
_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")


@dataclass
class Area:
    corridor_id: str
    name: str
    bbox: tuple[float, float, float, float]
    lines: list[int]
    m_per_px: float = 10.0
    chip_size_m: float = 3000.0
    chip_spacing_m: float = 1500.0
    note: str = ""
    join_m: float = corr.JOIN_M        # ways joined through a substation up to this far apart
    strip_m: float | None = None       # imagery only within this distance of the line (a long corridor)
    film: dict[str, Any] = field(default_factory=dict)  # this corridor's film settings (over the config's `film`)

    @classmethod
    def from_dict(cls, corridor_id: str, d: dict[str, Any]) -> "Area":
        if not _ID.match(corridor_id):
            raise ValueError(f"a corridor id is lower-case letters, digits and hyphens: {corridor_id!r}")
        bbox = tuple(float(x) for x in d["bbox"])
        if len(bbox) != 4 or not (bbox[0] < bbox[2] and bbox[1] < bbox[3]):
            raise ValueError("an area is west, south, east, north (in degrees)")
        lines = [int(x) for x in d.get("lines") or []]
        if not lines:
            raise ValueError("choose at least one power line to follow")
        return cls(corridor_id=corridor_id, name=str(d.get("name") or corridor_id), bbox=bbox, lines=lines,
                   m_per_px=float(d.get("m_per_px", 10)), chip_size_m=float(d.get("chip_size_m", 3000)),
                   chip_spacing_m=float(d.get("chip_spacing_m", 1500)), note=str(d.get("note") or ""),
                   join_m=float(d.get("join_m", corr.JOIN_M)), strip_m=float(d["strip_m"]) if d.get("strip_m") else None,
                   film=dict(d.get("film") or {}))


@dataclass
class SeamConfig:
    areas: dict[str, Area] = field(default_factory=dict)
    film: dict[str, Any] = field(default_factory=dict)
    fetch: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path | None = None) -> "SeamConfig":
        path = Path(path or DEFAULT_CONFIG)
        if not path.is_file():
            return cls()
        d = yaml.safe_load(path.read_text()) or {}
        return cls(areas={k: Area.from_dict(k, v) for k, v in (d.get("areas") or {}).items()},
                   film=d.get("film") or {}, fetch=d.get("fetch") or {})


def area_named(root: Path, cfg: SeamConfig, name: str) -> Area:
    """An area of the config, or an existing corridor of the folder (to add another pass to it)."""
    if name in cfg.areas:
        return cfg.areas[name]
    g = read_georef(root, name) if name else None
    if g is None:
        raise ValueError(f"no area {name!r}")
    return Area(corridor_id=name, name=g["name"], bbox=tuple(g["grid"]["bbox"]), lines=g["line"]["ways"],
                m_per_px=g["grid"]["m_per_px"], chip_size_m=g["chip_size_m"], chip_spacing_m=g["chip_spacing_m"],
                strip_m=g.get("strip_m"))


def check_area(scope: Scope, bbox: tuple[float, float, float, float]) -> None:
    """The area gate: a corridor must lie inside its folder's place (for Ukraine, the collection's box). Runs
    before anything is written. Acquisition dates are not limited: a pass's date is a source fact, and the
    imagery of any year can be compared (the 2022-2026 rule is about YouTube publication)."""
    box = scope.bbox or (UKRAINE_BBOX if scope.is_ukraine else None)
    if box is None:
        raise ValueError(f"{scope.name} has no box to check an area against")
    w, s, e, n = bbox
    if not (box[0] <= w and e <= box[2] and box[1] <= s and n <= box[3]):
        raise ValueError(f"the area {bbox} isn't inside {scope.name}: nothing was saved")
    if (e - w) > 2.5 or (n - s) > 2.0:
        raise ValueError("the area is too large for one corridor (at most 2.5° by 2°)")


def ensure_corridor(root: Path, scope: Scope, area: Area, http: httpx.Client) -> dict[str, Any]:
    """The corridor's georef.json: read, or made (gate first, then OpenStreetMap). An existing corridor is fixed:
    a request must name the same box and lines."""
    georef = read_georef(root, area.corridor_id)
    if georef is not None:
        if list(georef["grid"]["bbox"]) != list(area.bbox) or georef["line"]["ways"] != area.lines:
            raise ValueError(f"the corridor “{georef['name']}” is fixed (its box and lines were set when it was made): "
                             "name a new corridor for another area")
        return georef
    check_area(scope, area.bbox)
    log.info("Fetching the power lines in %s from OpenStreetMap…", area.name)
    osm = corr.fetch_power(area.bbox, http)
    georef = corr.build(area.corridor_id, area.name, area.bbox, area.lines, osm, area.m_per_px, area.chip_size_m,
                        area.chip_spacing_m, area.join_m, area.strip_m)
    d = corridor_dir(root, area.corridor_id)
    (d / "raw").mkdir(parents=True, exist_ok=True)
    write_json(d / "raw" / "osm_power.json", osm)
    write_json(d / "georef.json", georef)
    g = georef["grid"]
    log.info("Corridor “%s”: %.1f km along %s, %d×%d px at %g m", area.name, georef["line"]["length_m"] / 1000,
             georef["line"]["label"], g["width"], g["height"], g["m_per_px"])
    return georef


def _inside(x: np.ndarray, y: np.ndarray, ring: list[list[float]]) -> np.ndarray:
    r = np.asarray(ring, float)
    out = np.zeros(x.shape, bool)
    for (x1, y1), (x2, y2) in zip(r, np.roll(r, -1, axis=0)):
        cross = ((y1 > y) != (y2 > y)) & (x < (x2 - x1) * (y - y1) / np.where(y2 == y1, 1e-12, y2 - y1) + x1)
        out ^= cross
    return out


def coverage(items: list[dict[str, Any]], points: tuple[np.ndarray, np.ndarray]) -> float:
    """Share of the points (longitudes, latitudes) that the items' footprints cover."""
    xs, ys = points
    hit = np.zeros(xs.shape, bool)
    for it in items:
        g = it.get("geometry") or {}
        polys = [g["coordinates"]] if g.get("type") == "Polygon" else g.get("coordinates", []) if g.get("type") == "MultiPolygon" else []
        for poly in polys:
            hit |= _inside(xs, ys, poly[0])
    return float(hit.mean()) if hit.size else 0.0


def needed_points(georef: dict[str, Any], until_m: float | None) -> tuple[np.ndarray, np.ndarray]:
    """Sample points of what a pass must cover: the corridor's strip round its line (or its first until_m metres)."""
    grid = corr.Grid.from_json(georef["grid"])
    cell = 16
    need = need_mask(grid, georef, until_m, cell)
    rows, cols = np.nonzero(need)
    step = max(1, len(rows) // 1500)
    lon, lat = grid.to_lonlat((cols[::step] + .5) * cell, (rows[::step] + .5) * cell)
    return np.asarray(lon), np.asarray(lat)


def candidates(georef: dict[str, Any], sensor: Sensor, start: date, end: date, max_cloud: float,
               stored: set[str], http: httpx.Client, until_m: float | None = None) -> list[list[dict[str, Any]]]:
    """Overpasses covering what the corridor needs, not stored yet, clearest first."""
    pts = needed_points(georef, until_m)
    bbox = (float(pts[0].min()), float(pts[1].min()), float(pts[0].max()), float(pts[1].max()))
    items = search(sensor, bbox, start, end, max_cloud, http)
    out = []
    for group in overpasses(items):
        pid = pass_id_for(group[0]["properties"].get("platform", sensor.label), acquired(group[0]))
        if pid in stored or coverage(group, pts) < 0.99:
            continue
        out.append(group)
    cloud = lambda g: float(np.mean([it["properties"].get("eo:cloud_cover") or 0 for it in g]))
    return sorted(out, key=lambda g: (cloud(g), acquired(g[0])))


def tileset(root: Path, georef: dict[str, Any], p: SatellitePass) -> TileSet:
    return TileSet(root, p.files, corr.Grid.from_json(georef["grid"]))


def add_pass(root: Path, georef: dict[str, Any], sensor: Sensor, items: list[dict[str, Any]], http: httpx.Client,
             until_m: float | None = None) -> SatellitePass:
    """Fetch the pass tile by tile onto the corridor's grid (each laid on the same tile of the reference pass), cut its
    chips and write it."""
    grid = corr.Grid.from_json(georef["grid"])
    cid = georef["corridor_id"]
    first = items[0]
    when = acquired(first)
    platform = first["properties"].get("platform", sensor.label)
    pid = pass_id_for(platform, when)
    d = corridor_dir(root, cid) / "passes" / pid
    for sub in ("raw", "tiles"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    rel = lambda p_: Path(p_).resolve().relative_to(Path(root).resolve()).as_posix()
    ref_id = georef.get("reference_pass")
    ref = tileset(root, georef, next(p_ for p_ in read_passes(root, cid) if p_.pass_id == ref_id)) if ref_id else None
    todo = tiles(grid, georef, until_m)
    files, aligns, requests = [], [], []
    totals = dict(valid=0, cloud=0, clear=0, water=0, area=0)
    for k, (rows, cols) in enumerate(todo, 1):
        log.info("Tile %d of %d", k, len(todo))
        m = fetch_mosaic(sensor, items, grid, http, rows, cols)
        requests += m.requests
        if not m.valid.any():
            continue
        al = coregister(ref.mosaic(rows, cols) if ref else None, m, grid, ref_id)
        aligns.append(al)
        name = f"r{rows.start:06d}_c{cols.start:06d}"
        cv2.imwrite(str(d / "tiles" / f"{name}.png"), cv2.cvtColor(m.rgb(), cv2.COLOR_RGB2BGR))
        m.save(d / "tiles" / f"{name}.npz")
        files.append(TileFile(rows=(rows.start, rows.stop), cols=(cols.start, cols.stop), visual=rel(d / "tiles" / f"{name}.png"),
                              bands=rel(d / "tiles" / f"{name}.npz"), dx_m=al.dx_m, dy_m=al.dy_m, response=al.response,
                              applied=al.applied))
        for key, mask in (("valid", m.valid), ("cloud", m.cloud & m.valid), ("clear", m.clear), ("water", m.water)):
            totals[key] += int(mask.sum())
        totals["area"] += m.valid.size
    if totals["valid"] < 0.5 * max(1, totals["area"]):
        raise RuntimeError(f"{pid} has data over only {totals['valid'] / max(1, totals['area']):.0%} of what the corridor needs")
    align = _summary(aligns, ref_id, grid)
    log.info("%s: %s", pid, align.provenance.evidence)
    write_json(d / "raw" / "stac_items.json", items)
    write_json(d / "raw" / "requests.json", requests)
    pf = PassFiles(tiles=tuple(files), stac_items=rel(d / "raw" / "stac_items.json"), requests=rel(d / "raw" / "requests.json"))
    ids = tuple(it["id"] for it in items)
    chips = cut_chips(TileSet(root, pf, grid), grid, georef, pid, ids, when, d, rel, totals)
    props = first["properties"]
    p = SatellitePass(
        pass_id=pid, corridor_id=cid,
        source=PassSource(
            provider=PROVIDER, collection=sensor.collection, item_ids=ids,
            item_urls=tuple(item_url(sensor.collection, i) for i in ids), platform=platform, sensor=sensor.name,
            acquired_at=when, cloud_cover=round(float(np.mean([it["properties"].get("eo:cloud_cover") or 0 for it in items])), 3),
            sun_elevation=_sun_elevation(props),
            gsd_m=sensor.gsd_m, processing=props.get("s2:processing_baseline") or props.get("landsat:collection_number"),
            licence=sensor.licence, attribution=sensor.attribution.format(year=when.year)),
        derived=PassDerived(
            alignment=align, until_m=until_m,
            coverage=f"the line's first {until_m / 1000:g} km" if until_m else "the whole corridor",
            valid_share=round(totals["valid"] / max(1, totals["area"]), 4),
            cloud_share=round(totals["cloud"] / max(1, totals["valid"]), 4),
            water_share=round(totals["water"] / max(1, totals["clear"]), 4), display=DISPLAY,
            provenance=Provenance(method="stitch_on_corridor_grid", model=f"image_evidence {__version__}", evidence=(
                f"{len(ids)} item(s) of one overpass cropped to the corridor's grid by the data API in {len(files)} tile(s) "
                f"({len(requests)} requests, bands bilinear, the cloud mask nearest), stitched where each has data"
                + (f"; fetched only round the line's first {until_m / 1000:g} km" if until_m else "") + "."))),
        files=pf,
        chip_ids=[c.chip_id for c in chips],
    )
    for c in chips:
        write_json(d / "chips" / "meta" / f"{c.chip_id}.json", c.model_dump(mode="json"))
    write_json(d / "pass.json", p.model_dump(mode="json"))
    if not ref_id:
        georef["reference_pass"] = pid
        write_json(corridor_dir(root, cid) / "georef.json", georef)
    return p


def _summary(aligns: list, ref_id: str | None, grid: corr.Grid):
    """The pass's alignment: its one tile's, or the tiles' together (each tile's own is in pass.json files.tiles)."""
    from .schema import Alignment

    if len(aligns) == 1 or not ref_id:
        return aligns[0]
    done = [a for a in aligns if a.applied]
    dx = float(np.median([a.dx_m for a in done])) if done else 0.0
    dy = float(np.median([a.dy_m for a in done])) if done else 0.0
    return Alignment(reference_pass=ref_id, dx_m=round(dx, 2), dy_m=round(dy, 2),
                     response=round(float(np.median([a.response or 0 for a in aligns])), 3), applied=bool(done),
                     provenance=Provenance(method=aligns[0].provenance.method, evidence=(
                         f"Each tile laid on the reference pass on its own: {len(done)} of {len(aligns)} shifted "
                         f"(median {dx:+.1f} m east, {dy:+.1f} m north; each tile's shift is in the pass's record)"
                         + ("; the others too weak a match or too little clear land to compare."
                            if len(done) < len(aligns) else "."))))


def _sun_elevation(props: dict[str, Any]) -> float | None:
    if props.get("view:sun_elevation") is not None:
        return round(float(props["view:sun_elevation"]), 2)
    if props.get("s2:mean_solar_zenith") is not None:
        return round(90 - float(props["s2:mean_solar_zenith"]), 2)
    return None


def refresh_exposure(root: Path, corridor_id: str) -> None:
    """Each pass after the dam's destruction against the last pass before it: the share of each chip that was open
    water then and isn't now. Passes before it (or with nothing to compare) have none."""
    passes = read_passes(root, corridor_id)
    before = [p for p in passes if p.source.acquired_at.date() < BREACH]
    if not before:
        return
    b = before[-1]
    georef = read_georef(root, corridor_id)
    grid = corr.Grid.from_json(georef["grid"])
    base = corridor_dir(root, corridor_id) / "passes"
    bt = tileset(root, georef, b)
    for p in passes:
        if p.source.acquired_at.date() < BREACH:
            continue
        nt = tileset(root, georef, p)
        for c in read_chips(root, corridor_id, p.pass_id):
            exposure(bt, b.pass_id, nt, c, grid)
            write_json(base / p.pass_id / "chips" / "meta" / f"{c.chip_id}.json", c.model_dump(mode="json"))
        write_json(base / p.pass_id / "pass.json", p.model_dump(mode="json"))  # (the index reloads on its change)


def run(root: Path, scope: Scope, area: Area, sensor_name: str, start: date, end: date, max_cloud: float = 5.0,
        http: httpx.Client | None = None, tries: int = 3, until_km: float | None = None) -> dict[str, Any]:
    """Add the clearest new pass of the sensor between the dates (for the whole corridor, or only round the line's
    first `until_km`). Returns a result row for the job."""
    sensor = SENSORS[sensor_name]
    if start > end:
        raise ValueError("the dates start after they end")
    if start.year < sensor.first_year or end > date.today():
        raise ValueError(f"{sensor.label} imagery runs from {sensor.first_year} to today")
    http = http or httpx.Client(timeout=300, headers={"User-Agent": corr.USER_AGENT})
    georef = ensure_corridor(root, scope, area, http)
    until_m = until_km * 1000 if until_km else None
    if until_m is not None and until_m >= georef["line"]["length_m"]:
        until_m = None
    stored = {p.pass_id for p in read_passes(root, area.corridor_id)}
    log.info("Searching %s from %s to %s (at most %g%% cloud)…", sensor.label, start, end, max_cloud)
    found = candidates(georef, sensor, start, end, max_cloud, stored, http, until_m)
    if not found:
        return {"status": "rejected", "title": f"{sensor.label}, {start} – {end}",
                "reason": "no new pass covers the corridor with so little cloud between these dates"}
    for group in found[:tries]:
        when = acquired(group[0])
        log.info("Taking %s, %s (%d tile%s, %.2f%% cloud by the provider)", group[0]["properties"].get("platform"),
                 when.date(), len(group), "" if len(group) == 1 else "s", group[0]["properties"].get("eo:cloud_cover") or 0)
        p = add_pass(root, georef, sensor, group, http, until_m)
        georef = read_georef(root, area.corridor_id)  # (its reference pass, once there is one)
        if p.derived.cloud_share * 100 > max(max_cloud, 1.0):
            log.info("%s is %.1f%% cloud over the corridor itself: kept, and trying the next", p.pass_id, p.derived.cloud_share * 100)
            continue
        break
    refresh_exposure(root, area.corridor_id)
    return {"status": "processed", "title": f"{p.source.platform} · {p.source.acquired_at:%-d %B %Y}", "frames": len(p.chip_ids),
            "pass_id": p.pass_id, "corridor_id": area.corridor_id,
            "reason": f"{p.derived.coverage}: {p.derived.cloud_share:.1%} cloud, {p.derived.water_share:.0%} open water"}
