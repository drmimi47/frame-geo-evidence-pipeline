"""A plant's lines as a network: every line leaving it, traced through OpenStreetMap to the substation where it ends.

For the zoom-out film (`zoomout.py`): the plant at the centre, its lines growing outward to where they join the wider
grid. Kept apart from the corridors (one line each, a fixed grid): a network lives in `satellite/networks/<id>/`.

- Lines: OpenStreetMap `power=line` ways at the config's voltages in a box round the plant (the Overpass reply saved
  verbatim, fetched once, like a corridor's), with the substations and plants. Coordinates from a source that has its
  own; never detected from pixels.
- Tracing: each line starts with the ways the config names (its first way out of the switchyard, or the shared towers
  before a branch) and is followed way to way, end to end (the straightest way on where several meet, an unconnected
  end within JOIN_M), until it reaches a substation other than the one it left. The config names the substation each
  line must reach; a trace that ends anywhere else is refused, never drawn.
- Sites (a second reply, `osm_sites.json`): the plant's units (`power=generator` ways, outlined in the film) and areas
  named in the config (the Great Meadow: OSM's multipolygon of the drained Kakhovka reservoir's bed, mapped since 2023
  as the wetland Великий Луг), its outer ways joined into rings.
- Imagery: layers round the plant (the wide frame is a dark ground, not imagery), each the clearest pass of its sensor
  between its dates that covers its whole box at one instant: a sharp one for the close-up, a wider one under it.
"""

from __future__ import annotations

import json
import logging
import math
from datetime import date
from pathlib import Path
from typing import Any

import httpx
import numpy as np
import yaml
from PIL import Image

from ..layout import write_json
from . import providers
from .corridor import KZ, Grid, fetch_overpass
from .fetch import DEFAULT_CONFIG, coverage
from .stitch import fetch as fetch_tile
from .store import satellite_dir

log = logging.getLogger(__name__)

OSM_FILE = "osm_network.json"
SITES_FILE = "osm_sites.json"
JOIN_M = 60.0     # an unconnected way end this close continues the line
ARRIVE_M = 400.0  # a line ends once its end is inside a substation or this close to it (lines end at portals)


def network_dir(root: Path, network_id: str) -> Path:
    return satellite_dir(root) / "networks" / network_id


def config(network_id: str, path: Path | None = None) -> dict[str, Any]:
    d = yaml.safe_load(Path(path or DEFAULT_CONFIG).read_text()) or {}
    nets = d.get("networks") or {}
    if network_id not in nets:
        raise ValueError(f"no network {network_id!r} in the config (networks: {', '.join(nets) or 'none'})")
    return {"id": network_id, **nets[network_id], "trace_rgb": (d.get("film") or {}).get("trace_rgb", [255, 59, 48])}


def query(cfg: dict[str, Any]) -> str:
    w, s, e, n = cfg["bbox"]
    box = f"{s},{w},{n},{e}"
    kv = "|".join(str(int(v) * 1000) for v in cfg["voltages_kv"])
    ids = ",".join(str(i) for i in [cfg["plant"]["osm"], *cfg["origins"].values()])
    return (f'[out:json][timeout:300];(way({box})[power=line][voltage~"(^|;)({kv})(;|$)"];'
            f'nwr({box})[power~"^(substation|plant)$"][voltage~"({kv})"];way(id:{ids}););out tags geom;')


def reply(root: Path, cfg: dict[str, Any], http: httpx.Client | None = None) -> dict[str, Any]:
    path = network_dir(root, cfg["id"]) / "raw" / OSM_FILE
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        with (http or httpx.Client()) as client:
            write_json(path, fetch_overpass(query(cfg), client))
    return json.loads(path.read_text())


def _m(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot((b[0] - a[0]) * 111320.0 * math.cos(math.radians((a[1] + b[1]) / 2)), (b[1] - a[1]) * KZ)


def _length(pts: list[tuple[float, float]]) -> float:
    return sum(_m(a, b) for a, b in zip(pts, pts[1:]))


def _inside(p: tuple[float, float], ring: list[tuple[float, float]]) -> bool:
    x, y, c = p[0], p[1], False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def _key(p: tuple[float, float]) -> tuple[float, float]:
    return round(p[0], 7), round(p[1], 7)


class Network:
    def __init__(self, osm: dict[str, Any]):
        els = osm["reply"]["elements"]
        self.lines = {e["id"]: e for e in els if e["type"] == "way" and e.get("tags", {}).get("power") == "line"}
        self.areas = {e["id"]: [(g["lon"], g["lat"]) for g in e["geometry"]] for e in els
                      if e["type"] == "way" and e.get("geometry") and e["id"] not in self.lines}
        self.names = {e["id"]: e.get("tags", {}).get("name", "") for e in els if e["type"] == "way"}
        self.subs = [i for i, e in ((e["id"], e) for e in els if e["type"] == "way")
                     if e.get("tags", {}).get("power") in ("substation", "plant") and i in self.areas]
        self.ends: dict[tuple[float, float], list[int]] = {}
        for w in self.lines:
            g = self.pts(w)
            for p in (g[0], g[-1]):
                self.ends.setdefault(_key(p), []).append(w)

    def pts(self, w: int) -> list[tuple[float, float]]:
        return [(p["lon"], p["lat"]) for p in self.lines[w]["geometry"]]

    def kv(self, w: int) -> set[int]:
        return {int(v) // 1000 for v in self.lines[w]["tags"].get("voltage", "").split(";") if v.isdigit()}

    def centre(self, w: int) -> tuple[float, float]:
        g = self.areas[w]
        g = g[:-1] if len(g) > 1 and g[0] == g[-1] else g
        return float(np.mean([p[0] for p in g])), float(np.mean([p[1] for p in g]))

    def _dist(self, p: tuple[float, float], area: int) -> float:
        ring = self.areas[area]
        return 0.0 if _inside(p, ring) else min(_m(p, q) for q in ring)

    def arrived(self, p: tuple[float, float], skip: set[int]) -> int | None:
        best = min(((self._dist(p, s), s) for s in self.subs if s not in skip), default=None)
        return best[1] if best and best[0] <= ARRIVE_M else None

    def trace(self, start: list[int], origin: int, kv: int) -> dict[str, Any]:
        """The line from `origin` along the `start` ways and on to the substation where it ends."""
        line: list[tuple[float, float]] = []
        for w in start:  # the start ways, each turned to carry on from the last (the first: from the origin)
            g = self.pts(w)
            if not line:
                g = g if self._dist(g[0], origin) <= self._dist(g[-1], origin) else g[::-1]
            else:
                g = g if _m(line[-1], g[0]) <= _m(line[-1], g[-1]) else g[::-1]
            line += g if not line else g[1:]
        chain, used, branches = list(start), set(start), []
        while (sub := self.arrived(line[-1], {origin})) is None:
            tip = _key(line[-1])
            cand = [w for w in self.ends.get(tip, []) if w not in used and kv in self.kv(w)]
            if not cand:
                near = sorted((_m(line[-1], p), w) for w in self.lines if w not in used and kv in self.kv(w)
                              for p in (self.pts(w)[0], self.pts(w)[-1]))
                if not near or near[0][0] > JOIN_M:
                    raise ValueError(f"the {kv} kV line from way {start[0]} stops at {line[-1]} before any substation")
                cand = [near[0][1]]
            heading = math.atan2(line[-1][1] - line[-2][1], (line[-1][0] - line[-2][0]) * math.cos(math.radians(line[-1][1])))

            def turn(w: int) -> float:
                g = self.pts(w)
                g = g if _m(line[-1], g[0]) <= _m(line[-1], g[-1]) else g[::-1]
                h = math.atan2(g[1][1] - g[0][1], (g[1][0] - g[0][0]) * math.cos(math.radians(g[0][1])))
                return abs((h - heading + math.pi) % (2 * math.pi) - math.pi)

            w = min(cand, key=turn)
            if len(cand) > 1:
                branches.append({"at": [round(c, 6) for c in line[-1]], "ways": cand, "taken": w,
                                 "turns_deg": [round(math.degrees(turn(c))) for c in cand]})
            g = self.pts(w)
            line += (g if _m(line[-1], g[0]) <= _m(line[-1], g[-1]) else g[::-1])[1:]
            chain.append(w)
            used.add(w)
            if len(chain) > 500:
                raise ValueError(f"the line from way {start[0]} doesn't reach a substation")
        return {"ways": chain, "coords": [[round(x, 7), round(y, 7)] for x, y in line], "length_m": round(_length(line), 1),
                "ends_at": {"osm_way": sub, "name": self.names.get(sub, "")}, "branches": branches}


def _rings(rel: dict[str, Any], min_km2: float) -> list[list[list[float]]]:
    """A multipolygon's outer ways joined end to end into closed rings (the larger than min_km2)."""
    parts = [[(p["lon"], p["lat"]) for p in m["geometry"]] for m in rel["members"]
             if m.get("role") == "outer" and m.get("geometry")]
    rings = []
    while parts:
        ring = parts.pop(0)
        while _key(ring[0]) != _key(ring[-1]):
            k = next((i for i, q in enumerate(parts) if _key(q[0]) == _key(ring[-1]) or _key(q[-1]) == _key(ring[-1])), None)
            if k is None:
                break  # an open end (the relation clipped): left open
            q = parts.pop(k)
            ring += (q if _key(q[0]) == _key(ring[-1]) else q[::-1])[1:]
        lat = np.radians(np.mean([y for _, y in ring]))
        x = np.array([a for a, _ in ring]) * 111.32 * np.cos(lat)
        y = np.array([b for _, b in ring]) * 111.32
        if abs(0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)) >= min_km2:
            rings.append([[round(a, 6), round(b, 6)] for a, b in ring])
    return rings


def sites(root: Path, cfg: dict[str, Any], http: httpx.Client | None = None) -> dict[str, Any]:
    """The plant's units and the config's areas, from their own saved reply (fetched once)."""
    if not cfg.get("units") and not cfg.get("areas"):
        return {"units": [], "areas": [], "osm": None}
    path = network_dir(root, cfg["id"]) / "raw" / SITES_FILE
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        units = ",".join(str(u) for u in cfg.get("units") or [])
        rels = ",".join(str(a["osm_relation"]) for a in cfg.get("areas") or [])
        q = "[out:json][timeout:300];(" + (f"way(id:{units});" if units else "") + (f"rel(id:{rels});" if rels else "") + ");out geom;"
        with (http or httpx.Client()) as client:
            write_json(path, fetch_overpass(q, client))
    osm = json.loads(path.read_text())
    els = {(e["type"], e["id"]): e for e in osm["reply"]["elements"]}
    units = []
    for u in cfg.get("units") or []:
        e = els[("way", int(u))]
        units.append({"osm_way": u, "ref": e["tags"].get("ref", ""), "name": e["tags"].get("name:en") or e["tags"].get("name", ""),
                      "coords": [[round(p["lon"], 7), round(p["lat"], 7)] for p in e["geometry"]]})
    areas = []
    for a in cfg.get("areas") or []:
        e = els[("relation", int(a["osm_relation"]))]
        areas.append({"label": a["label"], "label_local": a.get("label_local", ""), "label_at": a["label_at"],
                      "osm_relation": a["osm_relation"], "tags": e["tags"], "note": a.get("note", ""),
                      "rings": _rings(e, float(a.get("min_km2", 2.0)))})
    return {"units": units, "areas": areas, "osm": {k: osm[k] for k in ("query", "server", "fetched_at", "licence")}}


def build(root: Path, cfg: dict[str, Any], http: httpx.Client | None = None) -> dict[str, Any]:
    """Trace every line of the config and write `network.json`; a line that ends anywhere but its `to` is refused."""
    osm = reply(root, cfg, http)
    net = Network(osm)
    plant = net.centre(cfg["plant"]["osm"])
    lines = []
    for spec in cfg["lines"]:
        t = net.trace([int(w) for w in spec["start"]], int(cfg["origins"][spec["from"]]), int(spec["kv"]))
        if t["ends_at"]["name"] != spec["to"]:
            raise ValueError(f"{spec['name']} ({spec['kv']} kV) ends at {t['ends_at']['name'] or t['ends_at']['osm_way']}, "
                             f"not {spec['to']} as the config says: check it before drawing")
        lines.append({**{k: spec[k] for k in ("name", "kv", "from", "to")}, **{k: spec[k] for k in ("ref", "checked") if k in spec},
                      **t})
        log.info("%s %d kV: %.1f km to %s (%d ways)", spec["name"], spec["kv"], t["length_m"] / 1000, spec["to"], len(t["ways"]))
    links = [{"ways": [w], "coords": [[round(x, 7), round(y, 7)] for x, y in net.pts(w)]} for w in cfg.get("links") or []]
    feeds = [{"ways": [w], "kv": max(net.kv(w)), "coords": [[round(x, 7), round(y, 7)] for x, y in net.pts(w)]}
             for w in cfg.get("feeds") or []]  # the units' own lines into the switchyard
    context = [{"kv": max(net.kv(w)), "coords": [[round(x, 5), round(y, 5)] for x, y in net.pts(w)]}
               for w in net.lines if not any(w in ln["ways"] for ln in lines)]
    st = sites(root, cfg, http)
    doc = {"schema": "network/1", "network_id": cfg["id"], "name": cfg["name"],
           "plant": {"osm_way": cfg["plant"]["osm"], "label": cfg["plant"]["label"], "lonlat": [round(c, 7) for c in plant]},
           "origins": {k: {"osm_way": v, "name": net.names.get(v, ""), "lonlat": [round(c, 7) for c in net.centre(v)],
                           "outline": [[round(x, 7), round(y, 7)] for x, y in net.areas[v]]}
                       for k, v in cfg["origins"].items()},
           "lines": lines, "links": links, "feeds": feeds, "context": context, "units": st["units"], "areas": st["areas"],
           "osm": {k: osm[k] for k in ("query", "server", "fetched_at", "licence")}, "osm_sites": st["osm"],
           "method": __doc__.split("\n\n")[1].strip()}
    network_dir(root, cfg["id"]).mkdir(parents=True, exist_ok=True)
    write_json(network_dir(root, cfg["id"]) / "network.json", doc)
    return doc


def imagery(root: Path, cfg: dict[str, Any], http: httpx.Client | None = None) -> list[dict[str, Any]]:
    """Every imagery layer of the config, each fetched once (`imagery/<name>.json`, the pixels in `imagery/<name>/`)."""
    return [_layer(root, cfg, im, http) for im in cfg["imagery"]]


def _layer(root: Path, cfg: dict[str, Any], im: dict[str, Any], http: httpx.Client | None) -> dict[str, Any]:
    out = network_dir(root, cfg["id"])
    rec = out / "imagery" / f"{im['name']}.json"
    if rec.is_file():
        return json.loads(rec.read_text())
    lon0, lat0 = Network(reply(root, cfg, http)).centre(cfg["plant"]["osm"])
    kx = 111320.0 * math.cos(math.radians(lat0))
    hw, hh = im["box_km"][0] * 500 / kx, im["box_km"][1] * 500 / KZ
    ox, oy = (float(v) * 1000 for v in im.get("centre_km", (0, 0)))  # the box's centre, m east and north of the plant
    lon0, lat0 = lon0 + ox / kx, lat0 + oy / KZ
    grid = Grid(bbox=(lon0 - hw, lat0 - hh, lon0 + hw, lat0 + hh), m_per_px=float(im["m_per_px"]))
    sensor = providers.SENSORS[im["sensor"]]
    with (http or httpx.Client()) as client:
        items = providers.search(sensor, grid.bbox, date.fromisoformat(str(im["start"])), date.fromisoformat(str(im["end"])),
                                 float(im.get("max_cloud", 5)), client)
        xs, ys = np.meshgrid(np.linspace(grid.bbox[0], grid.bbox[2], 9), np.linspace(grid.bbox[1], grid.bbox[3], 7))
        groups = [g for g in providers.overpasses(items) if coverage(g, (xs.ravel(), ys.ravel())) >= 1.0]
        if not groups:
            raise ValueError(f"no single pass covers the whole {im['name']} box between those dates; widen the dates")
        group = min(groups, key=lambda g: max(float(it["properties"].get("eo:cloud_cover", 100)) for it in g))
        when = providers.acquired(group[0])
        pass_id = f"{sensor.name}_{when:%Y-%m-%d}"
        log.info("Imagery %s: %s (%d items, %d×%d px)", im["name"], pass_id, len(group), grid.width, grid.height)
        m = fetch_tile(sensor, group, grid, client, piece_px=1024)  # smaller replies: whole 2048 px ones were cut off
    d = out / "imagery" / im["name"]  # a folder per layer: two layers may come from one pass
    d.mkdir(parents=True, exist_ok=True)
    Image.fromarray(m.rgb()).save(d / "rgb.webp", "WEBP", quality=92)
    write_json(d / "stac_items.json", group)
    doc = {"name": im["name"], "pass_id": pass_id, "sensor": sensor.label, "acquired": when.isoformat(), "grid": grid.to_json(),
           "items": [it["id"] for it in group], "cloud_cover": [it["properties"].get("eo:cloud_cover") for it in group],
           "file": f"imagery/{im['name']}/rgb.webp", "nodata_share": round(float(1 - m.valid.mean()), 4),
           "licence": sensor.licence, "attribution": sensor.attribution.format(year=when.year), "requests": m.requests}
    write_json(rec, doc)
    return doc
