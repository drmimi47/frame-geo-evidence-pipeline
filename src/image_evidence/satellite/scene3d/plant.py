"""The plant, the thermal plant and Enerhodar, modelled for the flight south (S6; the user, 4 November 2026: "the
nuclear power plant modeled from afar"). Massing, not survey: what reads from a kilometre or two away.

From OpenStreetMap (raw/osm_plant.json, saved verbatim, fetched once): every building's footprint and place, the six
units' containments (`power=generator`, `generator:source=nuclear`: 45 m circles), the vent stacks and chimneys
(`man_made=chimney`), the two cooling towers (`tower:type=cooling`) and the heights OSM tags (the thermal plant's
chimneys 320 m; the units 40 m). Heights from the sources in SOURCES where OSM has none: the containment (45 m across,
the dome's top at +66.45 m), the cooling towers (125 m), the special building's chimney (100 m). Where neither says,
a building is drawn at its `building:levels` (3 m a storey) or a representative height for its kind (`TYPICAL`), and
the unit's vent stacks at about 105 m, read off photographs against the containment's published height.

Not in OSM, placed from the Sentinel-2 imagery (10 m, so to within about 10-20 m) and photographs: each unit's
turbine hall, running west-north-west from its containment toward the cooling-water canal, and a lower bay beside it.
Colours as photographed (weathered): the containments' red-brown, the units' grey concrete and pale panels, the stacks'
white, the special building's red-and-white bands, the cooling towers' rust-brown, the thermal plant's dark chimneys.

Not drawn: the fire damage to cooling tower no. 1 (11 August 2024; the IAEA: mostly inside the tower, at the water
distribution level, about 10 m up), which photographs from outside don't show clearly; the switchyards' gantries
(their places aren't mapped); trees and roofs' detail.

Geometry only (numpy, towers.Mesh in the plane's metres, z above sea): build.py makes it one object, shaded by the
fixed sun like the towers.
"""

from __future__ import annotations

import math
from typing import Any, Callable

import numpy as np

from .towers import Mesh

CONCRETE, PANEL, CONTAINMENT, CROWN, STACK, RED, COOLING, COOLING_BAND, CHIMNEY, TOWN, ROOF, GLASSHOUSE, TANK = range(13)
# linear RGB, unlit (build.py shades them by the fixed sun); weathered, as photographed
MATERIALS = {CONCRETE: ("concrete, grey", (0.30, 0.295, 0.27)), PANEL: ("wall panels, pale", (0.46, 0.455, 0.42)),
             CONTAINMENT: ("containment, red-brown paint, weathered", (0.20, 0.045, 0.030)),
             CROWN: ("containment's crown, pale", (0.42, 0.40, 0.36)), STACK: ("vent stack, white, weathered", (0.52, 0.51, 0.48)),
             RED: ("paint red, weathered", (0.30, 0.032, 0.022)),
             COOLING: ("cooling tower concrete, rust-brown", (0.15, 0.075, 0.045)),
             COOLING_BAND: ("cooling tower's pale bands", (0.36, 0.30, 0.24)),
             CHIMNEY: ("thermal plant chimney, dark", (0.075, 0.065, 0.06)),
             TOWN: ("town walls, panel concrete", (0.36, 0.35, 0.32)), ROOF: ("flat roofs, bitumen", (0.12, 0.12, 0.115)),
             GLASSHOUSE: ("greenhouse glass", (0.38, 0.42, 0.42)), TANK: ("tanks, pale", (0.50, 0.50, 0.47))}

SOURCES = {
    "osm": {"what": "OpenStreetMap: footprints, places, the units' containments (40 m), chimneys (the thermal plant's "
                    "320 m), the cooling towers, building:levels (raw/osm_plant.json)",
            "url": "https://www.openstreetmap.org/way/28877213"},
    "smirt19": {"what": "a typical VVER-1000 containment: 45 m across, cylinder 44 m, the dome's top at +66.45 m "
                        "(SMiRT 19 paper, via NCSU repository)",
                "url": "https://repository.lib.ncsu.edu/server/api/core/bitstreams/71e9ad79-03ba-43eb-861b-15aab51751c9/content"},
    "bigenc": {"what": "VVER-1000 containment: 45 m across, 67.5 m high (Great Russian Encyclopedia)",
               "url": "https://bigenc.ru/c/zashchitnaia-obolochka-iadernogo-reaktora-8f5dd4"},
    "ssp_63203": {"what": "ZNPP cooling tower no. 1 (1988): 125 m (410 ft)", "url": "https://skyscraperpage.com/b63203"},
    "ssp_78211": {"what": "ZNPP cooling tower no. 2 (1991): 125 m (410 ft)", "url": "https://skyscraperpage.com/b78211"},
    "ssp_60350": {"what": "the chimney of ZNPP's special building 1 (1984): 100 m (328 ft)",
                  "url": "https://skyscraperpage.com/b60350"},
    "shadow_check": {"what": "the towers' shadows on seven winter Sentinel-2 passes (2023-2025) against the sun's "
                             "elevation: about 120 m (112-129 m), agreeing with 125 m; ~81 m ruled out",
                     "url": "research_notes/Cooling tower height check/NOTES.md"},
    "ssp_63204": {"what": "Zaporizhzhia thermal plant chimney no. 1: 320 m (1050 ft); no. 2 the same (b75446)",
                  "url": "https://skyscraperpage.com/b63204"},
    "photos": {"what": "photographs of the plant (Wikimedia Commons: 'Kernkraftwerk Saporischschja.JPG' from the "
                       "reservoir, 'Zaporozhje AES.jpg' from the east): the units' grey boxes and red-brown containments, "
                       "white vent stacks about 1.6 times the containment's height, the striped special chimney, the "
                       "rust-brown cooling tower with pale bands, the thermal plant's dark chimneys",
               "url": "https://commons.wikimedia.org/wiki/File:Kernkraftwerk_Saporischschja.JPG"},
    "iaea_2024_08": {"what": "the fire at cooling tower no. 1, 11 August 2024: damage mostly inside, at the water "
                             "distribution level about 10 m up (not drawn)",
                     "url": "https://world-nuclear-news.org/Articles/Fire-at-Zaporizhzhia-cooling-tower"},
}

def query(bbox: tuple[float, float, float, float]) -> str:
    """The Overpass query for the plant's surroundings (south, west, north, east)."""
    b = ",".join(str(v) for v in bbox)
    return (f'[out:json][timeout:170];('
            f'way["building"]({b});relation["building"]({b});'
            f'way["man_made"]({b});node["man_made"]({b});'
            f'way["power"~"^(substation|plant|generator|switch|transformer|busbar|bay)$"]({b});'
            f'node["power"~"^(portal|transformer|generator)$"]({b});'
            f'way["landuse"="industrial"]({b});way["water"]({b});way["natural"="water"]({b});'
            f');out tags geom;')


STOREY_M = 3.0
TYPICAL = {"apartments": 27.0, "industrial": 12.0, "warehouse": 8.0, "garages": 3.0, "garage": 3.0, "roof": 5.0,
           "greenhouse": 4.0, "school": 12.0, "kindergarten": 7.0, "hospital": 15.0, "public": 12.0,
           "commercial": 9.0, "retail": 6.0, "service": 4.0, "house": 6.0, "detached": 6.0, "storage_tank": 12.0,
           "construction": 6.0, "ruins": 3.0, "yes": 6.0}
SITE_M = 15.0          # an untagged building inside the nuclear plant's site (from photographs: the long low blocks)
UNIT_BOX_M = 66.0      # the reactor building's square (Temelín's outer shell plan, the same V-320 design)
CONTAINMENT_R = 22.5   # 45 m across (smirt19, bigenc)
CYLINDER_TOP = 58.5    # the cylinder's top above ground, then the crown and the dome (representative of the photos)
DOME_TOP = 66.45       # smirt19
STACK_M = 105.0        # the units' vent stacks: about 1.6 times the dome's height in the photographs
SPECIAL_M = 100.0      # ssp_60350
COOLING_M = 125.0      # ssp_63203, ssp_78211; shadow_check
HALL = {"from_m": 33.0, "length_m": 155.0, "half_width_m": 30.0, "height_m": 34.0,   # each unit's turbine hall and
        "bay_width_m": 30.0, "bay_height_m": 24.0}                                   # its bay (imagery, photographs)


def _ring(el: dict[str, Any], xy: Callable) -> np.ndarray | None:
    g = el.get("geometry")
    if not g:
        return None
    p = xy(np.array([[q["lon"], q["lat"]] for q in g if q]))
    if len(p) > 1 and np.allclose(p[0], p[-1]):
        p = p[:-1]
    return p if len(p) >= 3 else None


def _area(p: np.ndarray) -> float:
    x, y = p[:, 0], p[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def _inside(p: np.ndarray, poly: np.ndarray) -> bool:
    x, y = p
    c = False
    for (x0, y0), (x1, y1) in zip(poly, np.roll(poly, -1, 0)):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            c = not c
    return c


def prism(m: Mesh, ring: np.ndarray, z0: float, z1: float, wall: int, roof: int) -> None:
    """A footprint raised from z0 to z1: its walls and a flat roof (counter-clockwise, so the faces look outward)."""
    if _area(ring) < 0:
        ring = ring[::-1]
    n = len(ring)
    k0 = len(m.v)
    for x, y in ring:
        m.v.append(np.array([x, y, z0]))
    for x, y in ring:
        m.v.append(np.array([x, y, z1]))
    for i in range(n):
        j = (i + 1) % n
        m._face([k0 + i, k0 + j, k0 + n + j, k0 + n + i], wall)
    m._face([k0 + n + i for i in range(n)], roof)


def lathe(m: Mesh, c: np.ndarray, profile: list[tuple[float, float, int]], n: int = 48, cap: int | None = None) -> None:
    """A round body about a vertical axis at c: rings (z, r) bottom to top, each band painted the material given at
    its lower ring; a flat cap on top if `cap`."""
    k0 = len(m.v)
    for z, r, _ in profile:
        for k in range(n):
            t = 2 * math.pi * k / n
            m.v.append(np.array([c[0] + r * math.cos(t), c[1] + r * math.sin(t), z]))
    for j in range(len(profile) - 1):
        for k in range(n):
            a, b = k0 + j * n, k0 + (j + 1) * n
            m._face([a + k, a + (k + 1) % n, b + (k + 1) % n, b + k], profile[j][2])
    if cap is not None:
        m._face([k0 + (len(profile) - 1) * n + k for k in range(n)], cap)


def _bands(z0: float, z1: float, r0: float, r1: float, cuts: list[tuple[float, int]]) -> list[tuple[float, float, int]]:
    """A tapering shaft's rings from z0 to z1 (radius r0 to r1), painted by `cuts`: (height above z0, material) from
    that height up."""
    out = []
    for i, (h, mat) in enumerate(cuts):
        z = z0 + h
        out.append((z, r0 + (r1 - r0) * h / (z1 - z0), mat))
    out.append((z1, r1, cuts[-1][1]))
    return out


def stack(m: Mesh, c, g: float, h: float, r0: float, r1: float, cuts: list[tuple[float, int]], n: int = 20) -> None:
    lathe(m, np.asarray(c, float), _bands(g - 1.0, g + h, r0, r1, cuts), n, cap=cuts[-1][1])


def cooling_tower(m: Mesh, c, g: float, r0: float, h: float = COOLING_M) -> None:
    """A hyperboloid shell: open at the top, its throat 0.62 of the base's radius at 0.8 of its height; on a dark band
    for the columns' open ring at its foot; pale bands near the top (as photographed)."""
    rt, zt = 0.62 * r0, 0.8 * h
    b = zt / math.sqrt((r0 / rt) ** 2 - 1)
    zs = list(np.linspace(0, h, 26))
    prof = [(g - 1.0, r0 * 1.02, CHIMNEY)]
    for z in zs:
        mat = COOLING_BAND if (0.86 * h <= z < 0.9 * h or 0.94 * h <= z < 0.97 * h) else COOLING
        prof.append((g + max(z, 8.0), rt * math.sqrt(1 + ((max(z, 8.0) - zt) / b) ** 2), mat))
    lathe(m, np.asarray(c, float), prof, 64)


def unit(m: Mesh, c: np.ndarray, g: float, row: np.ndarray, box_m: float) -> None:
    """A unit: the reactor building's grey box (OSM's height), the containment's red-brown cylinder out of it, a pale
    crown and a low dome; its turbine hall running away from the row (west-north-west) with a lower bay beside it."""
    across = np.array([-row[1], row[0]])          # 90° anticlockwise from the row: away from it on the west side
    if across[0] > 0:
        across = -across
    h = UNIT_BOX_M / 2
    corners = [c + sa * h * across + sb * h * row for sa, sb in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    prism(m, np.array(corners), g - 1.0, g + box_m, CONCRETE, CONCRETE)
    dome = [(g + box_m - 1.0, CONTAINMENT_R, CONTAINMENT), (g + CYLINDER_TOP - 2.5, CONTAINMENT_R, CROWN),
            (g + CYLINDER_TOP, CONTAINMENT_R, CONTAINMENT)]
    for k in range(1, 7):   # the dome: a low cap to its published top
        a = k / 6
        dome.append((g + CYLINDER_TOP + (DOME_TOP - CYLINDER_TOP) * math.sin(a * math.pi / 2),
                     CONTAINMENT_R * math.cos(a * math.pi / 2) + (0.01 if k == 6 else 0.0), CONTAINMENT))
    lathe(m, c, dome, 56, cap=CONTAINMENT)
    f, L, w = HALL["from_m"], HALL["length_m"], HALL["half_width_m"]
    hall = [c + across * f - row * w, c + across * (f + L) - row * w, c + across * (f + L) + row * w, c + across * f + row * w]
    prism(m, np.array(hall), g - 1.0, g + HALL["height_m"], PANEL, ROOF)
    bw = HALL["bay_width_m"]
    bay = [c + across * f - row * (w + bw), c + across * (f + L) - row * (w + bw), c + across * (f + L) - row * w,
           c + across * f - row * w]
    prism(m, np.array(bay), g - 1.0, g + HALL["bay_height_m"], CONCRETE, ROOF)


def build(reply: dict[str, Any], xy: Callable, ground: Callable) -> tuple[Mesh, dict[str, Any]]:
    """The model from the saved OSM reply: `xy` turns lon/lat rows into the plane's metres, `ground` gives the land's
    height at a point (the scene's terrain, so nothing floats or sinks)."""
    els = reply["reply"]["elements"]
    m = Mesh()
    site = next(_ring(e, xy) for e in els if e.get("tags", {}).get("power") == "plant"
                and e.get("tags", {}).get("plant:source") == "nuclear")
    units = [(e, _ring(e, xy)) for e in els if e.get("tags", {}).get("power") == "generator"
             and e.get("tags", {}).get("generator:source") == "nuclear"]
    units = [(e, r) for e, r in units if r is not None]
    centres = np.array([r.mean(0) for _, r in units])
    order = np.argsort(centres[:, 1])
    rowv = centres[order[-1]] - centres[order[0]]
    rowv /= np.linalg.norm(rowv)
    counts = {"units": 0, "buildings": 0, "heights": {"osm_height": 0, "osm_levels": 0, "typical": 0}, "stacks": 0,
              "chimneys": 0, "cooling_towers": 0}
    stacks = []
    for e in els:
        t = e.get("tags", {})
        if t.get("man_made") != "chimney":
            continue
        p = np.array([[e["lon"], e["lat"]]]) if e["type"] == "node" else None
        ring = None if p is not None else _ring(e, xy)
        c = xy(p)[0] if p is not None else (ring.mean(0) if ring is not None else None)
        if c is None:
            continue
        stacks.append((e, t, c, ring))
    for (e, ring), c in zip(units, centres):
        g = float(min(ground(q) for q in [c, *ring]))
        unit(m, c, g, rowv, float(e["tags"].get("height", 40)))
        counts["units"] += 1
    for e, t, c, ring in stacks:
        g = ground(c)
        near_unit = float(np.min(np.hypot(*(centres - c).T))) < 80
        if "height" in t:   # the thermal plant's chimneys (OSM 320 m; ssp_63204)
            r0 = math.sqrt(abs(_area(ring)) / math.pi) if ring is not None else 8.0
            h = float(t["height"])
            stack(m, c, g, h, r0, 0.6 * r0, [(0.0, CHIMNEY), (0.37 * h, COOLING_BAND), (0.39 * h, CHIMNEY),
                                             (0.68 * h, COOLING_BAND), (0.70 * h, CHIMNEY), (0.92 * h, COOLING_BAND),
                                             (0.95 * h, CHIMNEY)], 32)
            counts["chimneys"] += 1
        elif near_unit:     # a unit's vent stack (photographs: white, a red band at the top)
            stack(m, c, g, STACK_M, 2.2, 1.7, [(0.0, STACK), (STACK_M - 6, RED)])
            counts["stacks"] += 1
        elif ring is not None and site is not None and _inside(c, site):   # the special buildings' striped chimneys
            r0 = math.sqrt(abs(_area(ring)) / math.pi)
            stack(m, c, g, SPECIAL_M, r0, 0.6 * r0, [(k * 10.0, RED if k % 2 == 0 else STACK) for k in range(10)], 24)
            counts["chimneys"] += 1
    for e in els:
        t = e.get("tags", {})
        if e["type"] != "way" or "building" not in t or t.get("power") == "generator":
            continue
        ring = _ring(e, xy)
        if ring is None or abs(_area(ring)) < 12:
            continue
        c = ring.mean(0)
        g = float(min(ground(q) for q in ring[:: max(1, len(ring) // 8)]))
        if t.get("tower:type") == "cooling":
            cooling_tower(m, c, g, math.sqrt(abs(_area(ring)) / math.pi))
            counts["cooling_towers"] += 1
            continue
        try:
            h = float(t["height"]) if float(t.get("height", 0) or 0) > 0 else None
        except ValueError:
            h = None
        if h:
            counts["heights"]["osm_height"] += 1
        elif t.get("building:levels"):
            try:
                h = float(t["building:levels"]) * STOREY_M + 1.0
                counts["heights"]["osm_levels"] += 1
            except ValueError:
                h = None
        if not h:
            h = SITE_M if site is not None and _inside(c, site) else TYPICAL.get(t["building"], TYPICAL["yes"])
            counts["heights"]["typical"] += 1
        kind = t["building"]
        wall = GLASSHOUSE if kind == "greenhouse" else TANK if kind == "storage_tank" else \
            PANEL if site is not None and _inside(c, site) else TOWN
        prism(m, ring, g - 1.0, g + h, wall, GLASSHOUSE if kind == "greenhouse" else TANK if kind == "storage_tank" else ROOF)
        counts["buildings"] += 1
    doc = {"counts": counts, "sources": SOURCES, "materials": {str(k): v for k, v in MATERIALS.items()},
           "heights": {"containment": {"r_m": CONTAINMENT_R, "cylinder_top_m": CYLINDER_TOP, "dome_top_m": DOME_TOP},
                       "unit_box_m": "OSM's height (40 m)", "vent_stacks_m": STACK_M, "special_chimney_m": SPECIAL_M,
                       "cooling_towers_m": COOLING_M, "storey_m": STOREY_M, "typical_m": TYPICAL, "site_m": SITE_M,
                       "turbine_halls": HALL},
           "statement": "Massing, not a survey. Places and footprints from OpenStreetMap; heights from OSM's tags and the "
                        "sources named, else a building's storeys (3 m each) or a representative height for its kind. "
                        "The units' turbine halls and bays aren't mapped: placed from the 10 m imagery and photographs. "
                        "Shapes and colours representative, as photographed. The fire damage to cooling tower no. 1 "
                        "(11 August 2024, mostly inside it) and the switchyards' gantries are not drawn."}
    return m, doc
