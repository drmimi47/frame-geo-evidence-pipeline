"""The crossing's towers, modelled (pass 4; the user, 25 October 2026: "as accurate/detailed as the real things ...
they come in different sizes"). Every OSM tower node is drawn as the type of tower it is, at its OSM position:

- Dniprovska (750 kV, ZNPP - Dniprovska, 1984): on land guyed portals (`pp750`, as photographed at its tower no. 30)
  and, where OSM tags `triple_tower=yes` (angles and the crossing's ends), three separate single-phase towers
  (`triple750`); over the water the crossing, К-П-П-А-П-П-К: four 126 m suspension towers (`crossing750_p`) and a
  100 m anchor in the middle (`crossing750_a`), three of the five on caissons in the reservoir.
- Ferosplavna (330 kV, Л-243/Л-244, 1977): on land П-shaped reinforced-concrete portals (`pvs330`, "ПВС"), three
  single-phase end towers (`triple330`) where OSM tags them; over the water seven double-circuit anchor towers of 90
  and 100 m (`crossing330`), five of them on caissons.
- The switchyard's gantry where a line starts (`gantry750`, `gantry330`): no OSM node, the trace's end.

Sourced: the types, heights, crossbar heights, schemes and caissons (SOURCES, each named in scene.json). Modelled
(representative, said so): the members, panels and arms' proportions (from the photos: the crossarms flat on top,
their bottom chords rising to the tips, as on these towers' heads), the fittings (glass disc strings in sets side by
side between yoke plates, rings on the 750 kV sets, the bundle's clamps on a crescent yoke for 750 kV's five
sub-conductors and a plate for 330 kV's two, spacers along the spans and Stockbridge dampers by the clamps: their
kind as photographed, their sizes and spacing typical), the paint (weathered, as photographed on the shore towers,
assumed the same on those in the water) and the conductors' sag. Which of the 330 kV crossing towers are 90 m and
which 100 m isn't published: all are drawn at no. 19's 100 m.

Geometry only (numpy): each type is one mesh in its own frame (x across the line, right of the way it runs; y along
it; z up from its base), its conductors' attachment points (per circuit, each phase's bundle centre back and forward:
the same point under a suspension string, the two dead ends of the tension sets on an anchor; the sub-conductors sit
round it as `BUNDLE`) and its earth wires' points. build.py turns the meshes into Blender objects; export.py places
them, hangs the wires (`wires`) and their spacers and dampers (`fittings`).
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

STEEL, WHITE, RED, CONCRETE, GLASS, GUY, ALU, RUST, STAINED = range(9)
# linear RGB, unlit (build.py shades them by a fixed sun): weathered, as photographed, never the paint chart's pure
# white and signal red (the user, 26 October 2026: "too pure white & orange")
MATERIALS = {STEEL: ("galvanised steel", (0.30, 0.315, 0.315)), WHITE: ("paint white, weathered", (0.56, 0.545, 0.48)),
             RED: ("paint red, weathered", (0.30, 0.032, 0.022)), CONCRETE: ("concrete", (0.35, 0.33, 0.29)),
             GLASS: ("toughened glass", (0.15, 0.34, 0.30)), GUY: ("dark steel", (0.05, 0.052, 0.055)),
             ALU: ("fittings", (0.36, 0.37, 0.36)), RUST: ("weathered steel", (0.12, 0.05, 0.028)),
             STAINED: ("concrete long under water, stained", (0.16, 0.15, 0.115))}

SOURCES = {
    "novoklimov": {"what": "photo report of both crossings and their land towers (May 2011): types (ПВС portals, triple "
                           "end towers), schemes К-П-П-А-П-П-К and К-А-…-К, 126 m / 375 t and 100 m / 350 t, 90 and 100 m, "
                           "spans, the floated caissons, ZNPP-Dniprovska tower no. 30; close-ups of the crossing towers' "
                           "heads (flat-topped crossarms, multi-string glass insulator sets, yoke plates, rings, bundle "
                           "clamps, the weathered red and white) and a 6-string tension set on the crossing's drawing",
                   "url": "http://novoklimov.blogspot.com/2011/01/330-750.html"},
    "ssp_63206": {"what": "750 kV crossing pylon no. 23: 126 m (413 ft), 2nd crossbar 113 m (371 ft), caisson 40 m across",
                  "url": "https://skyscraperpage.com/b63206"},
    "ssp_94005": {"what": "330 kV crossing pylon no. 19: 100 m (328 ft), crossbars 92, 81, 70 m (unconfirmed there), "
                          "caisson 43.6 m across at its base and 29 m at its top, its base 12.8 m (42 ft) down",
                  "url": "https://skyscraperpage.com/b94005"},
    "ukwiki": {"what": "Переходи ЛЕП через Дніпро (Енергодар): 330 kV towers 90 m, the central 100 m, foundations about "
                       "30 m across rising 2-5 m above the water; 750 kV 126 m and 100 m, foundations about 40 m",
               "url": "https://uk.wikipedia.org/wiki/Переходи_ЛЕП_через_Дніпро_(Енергодар)"},
    "osm": {"what": "tower positions and tags (tower:type=crossing; design=monopolar + triple_tower=yes: three single-"
                    "phase towers); bundles: 750 kV fivefold, 330 kV double",
            "url": "https://www.openstreetmap.org"},
    "esri": {"what": "World Imagery over each tower (checked 25 October 2026): the triple towers' three shadows, the "
                     "crossing towers' red and white paint, the caissons", "url": "https://www.arcgis.com/home/item.html?id=10df2279f9684e4a9f6a7f08febac2a9"},
}

WATER_UP_M = 3.0    # a caisson's top above the water (sources: 2-5 m)
CAISSON_DOWN_M = 12.8  # its base below the water (no. 19: -42 ft)
POOL_M = 16.4       # the reservoir's normal level the caissons were set to: 16.0 m Baltic (raised to EGM2008, bed.py)
CAISSON_PANELS = 32  # the drum's faceted panels, a pilaster rib at each joint (Esri, 23 August 2024: the exposed drums)
CAISSON_DRUM_M = 8.5  # the drum's wall, from its base; then a faceted cone up to the flat top (representative)

# A phase's sub-conductors round its bundle centre ((x across, z up), m): OSM's fivefold 750 kV and double 330 kV
# bundles; 750 kV's five on a 0.6 m pentagon, a corner up (its clamps on a crescent yoke), 330 kV's two 0.4 m apart
# (typical splits, representative). Their radius (АС-400 class) and the earth wire's: real sizes, which build.py
# draws at least MIN_PX wide however far.
BUNDLE = {750: [(0.51 * math.cos(math.radians(90 + 72 * k)), 0.51 * math.sin(math.radians(90 + 72 * k))) for k in range(5)],
          330: [(-0.2, 0.0), (0.2, 0.0)]}
CONDUCTOR_R = {750: 0.0135, 330: 0.0135}
EARTH_R = 0.0055
DISC = {750: (0.30, 0.17), 330: (0.28, 0.17)}   # a glass disc's diameter and pitch (ПС-120/ПС-210 class)
SPACER_M = {750: 55.0, 330: 65.0}                # spacers along a span (typical)
CROSS_EASE_M = 150.0   # the flow drawn fullest over the water, easing to its land strength within this beyond its shores
_D = False             # the look's `detail` (look pass 2): set while build_types(detail=True) builds the meshes
DETAIL_STATEMENT = (
    "Look pass 2's towers (towers.build_types(detail=True)): the same types, heights, positions and attachment points "
    "(so the same wires), with more of what Novoklimov's 2011 photographs of these crossings show (b13, b15, b16, b29, "
    "b30, b38-b40, b46): built-up legs (two angles back to back), a redundant horizontal and short sub-diagonals in "
    "each face's panels, square-in-square plan bracing at the girts, gusset plates at the legs' joints, a walkway deck "
    "on the railed crossarms, a ladder up one leg of the crossing towers, the small railed bracket on one side below "
    "the 750 kV suspension towers' main arm (photographed on shore tower no. 26; its use isn't known); glass discs with "
    "their ribbed skirts; 750 kV spacer-dampers with a hub and arms; Stockbridge dampers with bell weights. No aviation "
    "warning markers: none show on the photographs of these crossings. Member sizes, counts and spacing representative.")


def _basis(u: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    p = np.cross(u, (0.0, 0.0, 1.0) if abs(u[2]) < 0.9 else (1.0, 0.0, 0.0))
    p /= np.linalg.norm(p)
    return p, np.cross(u, p)


def _unit(v) -> np.ndarray:
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


class Mesh:
    """Faces of any size (loops + counts) with a material each; built from beams, rods and solids."""

    def __init__(self) -> None:
        self.v: list[np.ndarray] = []
        self.loops: list[int] = []
        self.counts: list[int] = []
        self.mat: list[int] = []

    def _face(self, idx: list[int], mat: int) -> None:
        self.loops += idx
        self.counts.append(len(idx))
        self.mat.append(mat)

    def _rings(self, rings: list[tuple[np.ndarray, float]], u: np.ndarray, mat: int, n: int, phase: float = 0.0) -> None:
        """Quads between successive rings (centre, radius) about the axis u."""
        p, q = _basis(u)
        k0 = len(self.v)
        for c, r in rings:
            for k in range(n):
                t = 2 * math.pi * (k + phase) / n
                self.v.append(c + r * (math.cos(t) * p + math.sin(t) * q))
        for j in range(len(rings) - 1):
            for k in range(n):
                a, b = k0 + j * n, k0 + (j + 1) * n
                self._face([a + k, a + (k + 1) % n, b + (k + 1) % n, b + k], mat)

    def rod(self, a, b, w: float, mat: int = STEEL, n: int = 4) -> None:
        """A member from a to b: an n-sided prism `w` across (square for steel angles, round-ish for strings)."""
        a, b = np.asarray(a, float), np.asarray(b, float)
        L = float(np.linalg.norm(b - a))
        if L < 1e-6:
            return
        r = w / 2 / (math.cos(math.pi / n) if n == 4 else 1.0)
        self._rings([(a, r), (b, r)], (b - a) / L, mat, n, 0.5)

    def angle(self, a, b, w: float, mat: int = STEEL, turn: bool = False) -> None:
        """A steel angle from a to b: an L section, flanges `w` wide and a tenth of that thick (`turn`: the same turned
        half round, so two make a built-up cross-section)."""
        a, b = np.asarray(a, float), np.asarray(b, float)
        L = float(np.linalg.norm(b - a))
        if L < 1e-6:
            return
        p, q = _basis((b - a) / L)
        if turn:
            p, q = -p, -q
        t = max(0.012, 0.1 * w)
        sec = [(0, 0), (w, 0), (w, t), (t, t), (t, w), (0, w)]
        k0 = len(self.v)
        for end in (a, b):
            for x, y in sec:
                self.v.append(end + (x - w / 3) * p + (y - w / 3) * q)
        n = len(sec)
        for k in range(n):
            self._face([k0 + k, k0 + (k + 1) % n, k0 + n + (k + 1) % n, k0 + n + k], mat)

    def disc(self, c, u, r: float, mat: int = GLASS, n: int = 8) -> None:
        """A cap-and-pin glass disc on the axis u, its skirt opening toward +u (in detail: the shell, the rim and the
        ribbed skirt under it)."""
        c = np.asarray(c, float)
        if _D:
            self._rings([(c - 0.06 * u, 0.2 * r), (c - 0.01 * u, 0.62 * r), (c + 0.012 * u, r), (c + 0.026 * u, 0.86 * r),
                         (c + 0.03 * u, 0.62 * r), (c + 0.045 * u, 0.5 * r)], u, mat, 10)
            return
        self._rings([(c - 0.05 * u, 0.22 * r), (c + 0.015 * u, r), (c + 0.04 * u, 0.55 * r)], u, mat, n)

    def ring(self, c, u, R: float, w: float, mat: int = ALU, n: int = 14) -> None:
        """A grading ring (a torus, as rods) of radius R about the axis u."""
        p, q = _basis(_unit(u))
        pts = [np.asarray(c, float) + R * (math.cos(2 * math.pi * k / n) * p + math.sin(2 * math.pi * k / n) * q)
               for k in range(n + 1)]
        for a, b in zip(pts, pts[1:]):
            self.rod(a, b, w, mat, n=6)

    def block(self, c, ax, ay, size, mat: int) -> None:
        """A box of `size` along the axes ax, ay and their cross product (a plate when one size is thin)."""
        ax, ay = _unit(ax), _unit(ay)
        az = np.cross(ax, ay)
        h = np.asarray(size, float) / 2
        k0 = len(self.v)
        for sx, sy, sz in [(-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1), (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]:
            self.v.append(np.asarray(c, float) + sx * h[0] * ax + sy * h[1] * ay + sz * h[2] * az)
        for f in ([0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]):
            self._face([k0 + i for i in f], mat)

    def box(self, c, size, mat: int) -> None:
        self.block(c, (1, 0, 0), (0, 1, 0), size, mat)

    def frustum(self, z0: float, z1: float, r0: float, r1: float, mat: int, n: int = 48, cap: bool = True) -> None:
        k0 = len(self.v)
        self._rings([(np.array([0.0, 0.0, z0]), r0), (np.array([0.0, 0.0, z1]), r1)], np.array([0.0, 0.0, 1.0]), mat, n)
        if cap:
            self._face([k0 + n + k for k in range(n)], mat)

    def arrays(self) -> dict[str, np.ndarray]:
        return {"v": np.array(self.v, np.float32).reshape(-1, 3), "loops": np.array(self.loops, np.int32),
                "counts": np.array(self.counts, np.int32), "mat": np.array(self.mat, np.uint8)}


# ------------------------------------------------------------------ parts

def _hw(profile: list[tuple[float, float]], z: float) -> float:
    zs, ws = zip(*profile)
    return float(np.interp(z, zs, ws))


def _paint(z: float, band: tuple[float, float, int] | None, base: int = STEEL) -> int:
    """Aviation marking: `n` equal bands from z0 to z1, red at the top, alternating with white; unpainted below."""
    if band is None:
        return base
    z0, z1, n = band
    if z < z0:
        return base
    k = min(n - 1, int((z - z0) / ((z1 - z0) / n)))
    return RED if (n - 1 - k) % 2 == 0 else WHITE


def lattice(m: Mesh, profile, at=(0.0, 0.0), leg=0.5, brace=0.22, band=None, panel=1.0, window=None,
            base: int = STEEL) -> None:
    """A square lattice body: four legs along the profile ((z, half-width), base to top), girts at each panel point
    and an X of braces on each face, panels about as tall as the body is wide there (and at every kink). `window`
    (z0, z1): the faces across the line (±y) left open there, where a phase passes through the body."""
    x0, y0 = at
    ztop = profile[-1][0]
    kinks = [z for z, _ in profile] + (list(window) if window else [])
    zs = [0.0]
    while zs[-1] < ztop - 1e-6:
        nxt = zs[-1] + max(1.2, panel * 2 * _hw(profile, zs[-1]))
        nxt = min([k for k in kinks if k > zs[-1] + 0.5] + [nxt])
        zs.append(min(nxt, ztop))
    corners = [(1, 1), (-1, 1), (-1, -1), (1, -1)]   # faces: 0 and 2 across the line (±y), 1 and 3 along it (±x)
    pts = [[np.array([x0 + sx * _hw(profile, z), y0 + sy * _hw(profile, z), z]) for sx, sy in corners] for z in zs]
    for i in range(len(zs) - 1):
        mat = _paint((zs[i] + zs[i + 1]) / 2, band, base)
        open_ = window is not None and zs[i] >= window[0] - 1e-6 and zs[i + 1] <= window[1] + 1e-6
        for c in range(4):
            a, b, a2, b2 = pts[i][c], pts[i][(c + 1) % 4], pts[i + 1][c], pts[i + 1][(c + 1) % 4]
            m.angle(a, a2, leg, mat)
            if _D and leg >= 0.2:   # built-up legs: two angles back to back (b31, b40)
                m.angle(a, a2, leg * 0.8, mat, turn=True)
            if open_ and c in (0, 2):
                continue
            m.angle(a, b2, brace, mat)
            m.angle(b, a2, brace, mat)
            mid = (a + b + a2 + b2) / 4   # a redundant member across the X, as on the photos' heavier panels
            if np.linalg.norm(b - a) > 6:
                m.angle((a + b) / 2, mid, brace * 0.7, mat)
            if _D and np.linalg.norm(b - a) > 2.5:   # a redundant horizontal through the X, short sub-diagonals
                la, lb = (a + a2) / 2, (b + b2) / 2   # from the legs to the braces (b29, b40)
                m.angle(la, lb, brace * 0.6, mat)
                for p0, p1, q in ((a, b2, la), (b, a2, lb)):
                    m.angle(q, p0 + 0.25 * (p1 - p0), brace * 0.5, mat)
                for p0, p1, q in ((b, a2, la), (a, b2, lb)):
                    m.angle(q, p0 + 0.75 * (p1 - p0), brace * 0.5, mat)
    for i, z in enumerate(zs):
        mat = _paint(z, band, base)
        for c in range(4):
            if window is not None and window[0] + 1e-6 < z < window[1] - 1e-6 and c in (0, 2):
                continue
            m.angle(pts[i][c], pts[i][(c + 1) % 4], brace * 1.2, mat)
        if i % 3 == 0 and _hw(profile, z) > 2.5:   # a horizontal diaphragm now and then
            m.angle(pts[i][0], pts[i][2], brace * 0.8, mat)
        if _D and _hw(profile, z) > 1.5:   # square-in-square plan bracing (b38, b39) and gussets at the legs (b15)
            sm = [(pts[i][c] + pts[i][(c + 1) % 4]) / 2 for c in range(4)]
            for c in range(4):
                m.angle(sm[c], sm[(c + 1) % 4], brace * 0.7, mat)
            for c in range(4):
                for o in (pts[i][(c + 1) % 4], pts[i][(c + 3) % 4]):
                    dvec = _unit(o - pts[i][c])
                    m.block(pts[i][c] + dvec * 0.35 + (0.0, 0.0, 0.15), dvec, (0.0, 0.0, 1.0), (0.6, 0.45, 0.02), mat)


def arm(m: Mesh, z_top: float, depth: float, x_in: float, reach: float, side: int, half_in: float,
        half_tip: float = 0.5, tip_depth: float = 0.8, at=(0.0, 0.0), band=None, w=0.25, rail: bool = False,
        base: int = STEEL) -> np.ndarray:
    """A crossarm as on these towers' heads: two trusses (fore and aft of the body) from the body's face (x_in from
    `at`, `depth` deep there) to its tip at `reach` (both measured from `at`, toward `side`), their top chords level at
    `z_top` and their bottom chords rising to `tip_depth` below it at the tip; a walkway's handrail along the top if
    `rail`. Returns the tip's bottom point."""
    x0, y0 = at
    n = max(2, int(abs(reach - x_in) / 2.5))
    mat = _paint(z_top - depth / 2, band, base)
    rows = []
    for k in range(n + 1):
        t = k / n
        x = x0 + side * (x_in + t * (reach - x_in))
        hy = half_in + t * (half_tip - half_in)
        bot = z_top - (depth + t * (tip_depth - depth))
        rows.append([(np.array([x, y0 + s * hy, bot]), np.array([x, y0 + s * hy, z_top])) for s in (-1, 1)])
    for k in range(n):
        for s in range(2):
            (b0, t0), (b1, t1) = rows[k][s], rows[k + 1][s]
            m.angle(b0, b1, w * 1.4, mat)
            m.angle(t0, t1, w * 1.4, mat)
            m.angle(b0 if k % 2 else t0, t1 if k % 2 else b1, w, mat)
        m.angle(rows[k][0][0], rows[k][1][0], w, mat)
        m.angle(rows[k][0][1], rows[k][1][1], w * 0.8, mat)
        m.angle(rows[k][0][0], rows[k + 1][1][0], w * 0.8, mat)
        m.angle(rows[k][0][1], rows[k + 1][1][1], w * 0.6, mat)
    for s in range(2):
        m.angle(*rows[0][s], w, mat)
        m.angle(*rows[n][s], w, mat)
    m.angle(rows[n][0][0], rows[n][1][0], w, mat)
    m.angle(rows[n][0][1], rows[n][1][1], w, mat)
    if rail and _D:   # the walkway's deck along the top (b16)
        c0 = (rows[0][0][1] + rows[0][1][1]) / 2
        c1 = (rows[n][0][1] + rows[n][1][1]) / 2
        m.block((c0 + c1) / 2 + (0.0, 0.0, 0.03), c1 - c0, (0.0, 1.0, 0.0),
                (float(np.linalg.norm(c1 - c0)), 0.8, 0.03), STEEL)
    if rail:
        for s in range(2):
            posts = [rows[k][s][1] for k in range(n + 1)]
            for p in posts:
                m.angle(p, p + (0, 0, 1.1), 0.05, mat)
            m.angle(posts[0] + (0, 0, 1.1), posts[-1] + (0, 0, 1.1), 0.05, mat)
    return np.array([x0 + side * reach, y0, z_top - tip_depth])


def insulator(m: Mesh, a, b, kv: int) -> None:
    """One string of cap-and-pin glass discs from a to b (their skirts toward b), on its pins and caps."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    L = float(np.linalg.norm(b - a))
    u = (b - a) / L
    d, pitch = DISC[kv]
    m.rod(a, b, 0.035, ALU, n=4)
    k = max(1, int((L - 0.3) / pitch))
    for i in range(k):
        m.disc(a + u * (0.15 + (i + 0.5) * (L - 0.3) / k), u, d / 2)


def string_set(m: Mesh, a, b, kv: int, n: int = 1, across=(1.0, 0.0, 0.0), gap: float = 0.45,
               ring: float = 0.0) -> None:
    """`n` strings side by side (`gap` apart along `across`) between yoke plates at a and b, linked to a and b;
    a grading ring round the line end (b) if `ring`."""
    a, b, across = np.asarray(a, float), np.asarray(b, float), _unit(across)
    u = _unit(b - a)
    offs = (np.arange(n) - (n - 1) / 2) * gap
    ends = (a + 0.25 * u, b - 0.25 * u) if n > 1 else (a, b)
    for o in offs:
        insulator(m, ends[0] + o * across, ends[1] + o * across, kv)
    if n > 1:
        span = (n - 1) * gap + 0.25
        for p in ends:   # the yoke plates across the strings, and the link to the tower or the clamps
            m.block(p, across, u, (span, 0.22, 0.035), ALU)
        m.rod(a, ends[0], 0.07, ALU, n=6)
        m.rod(ends[1], b, 0.07, ALU, n=6)
    if ring:
        m.ring(b - 0.55 * u, u, ring + 0.5 * (n - 1) * gap, 0.06)


def clamps(m: Mesh, top, kv: int, along=(0.0, 1.0, 0.0)) -> np.ndarray:
    """The bundle's suspension clamps under a string's yoke at `top`: for 750 kV a crescent yoke over the upper three
    sub-conductors' clamps, the lower two hung from its horns; for 330 kV a plate with a clamp at each corner. Returns
    the bundle's centre."""
    top, along = np.asarray(top, float), _unit(along)
    across = np.cross(along, (0.0, 0.0, 1.0))
    sub = BUNDLE[kv]
    if kv == 750:
        R = 0.51 + 0.11
        c = top - (0.0, 0.0, R + 0.12)
        arc = [c + R * (math.cos(math.radians(t)) * across + math.sin(math.radians(t)) * np.array([0.0, 0.0, 1.0]))
               for t in np.linspace(-28, 208, 14)]
        for p, q in zip(arc, arc[1:]):
            m.block((p + q) / 2, q - p, along, (float(np.linalg.norm(q - p)) + 0.02, 0.03, 0.12), ALU)
        m.rod(top, c + (0.0, 0.0, R), 0.08, ALU, n=6)
        for k, (x, z) in enumerate(sub):
            p = c + x * across + (0.0, 0.0, z)
            m.rod(p - 0.18 * along, p + 0.18 * along, 0.075, ALU, n=6)
            hang = arc[0] if x > 0 and z < 0 else arc[-1] if z < 0 else c + _unit(p - c) * R
            m.rod(p, hang, 0.035, ALU)
        m.ring(c, along, 0.95, 0.05, n=18)   # the bundle's grading ring
        return c
    c = top - (0.0, 0.0, 0.32)
    m.block(c + (0.0, 0.0, 0.16), across, (0.0, 0.0, 1.0), (0.55, 0.32, 0.03), ALU)
    m.rod(top, c + (0.0, 0.0, 0.32), 0.06, ALU, n=6)
    for x, z in sub:
        p = c + x * across + (0.0, 0.0, z)
        m.rod(p - 0.15 * along, p + 0.15 * along, 0.07, ALU, n=6)
        m.rod(p, p + (0.0, 0.0, 0.16), 0.03, ALU)
    return c


def suspend(m: Mesh, top, length: float, kv: int, n: int = 1, across=(0.0, 1.0, 0.0),
            gap: float = 0.5) -> tuple[np.ndarray, np.ndarray]:
    """A suspension set: `n` strings (side by side along `across`) hanging `length` from `top`, the bundle clamped
    under them; the conductors pass through its centre."""
    top = np.asarray(top, float)
    low = top - (0.0, 0.0, length)
    string_set(m, top, low, kv, n, across, gap, ring=0.35 if kv == 750 else 0.0)
    c = clamps(m, low, kv)
    return c, c


def tension(m: Mesh, tip, length: float, kv: int, n: int = 2, drop: float = 0.4, face: float = 0.0,
            dirs=(-1, 1)) -> tuple[np.ndarray, np.ndarray]:
    """Tension sets back and forward along the line from an anchor's tip (`face` out from it): `n` strings side by
    side between yoke plates, then a dead-end yoke across the bundle with a clamp for each sub-conductor. Returns
    the bundle's centres where the conductors end (back, forward)."""
    tip = np.asarray(tip, float)
    out = []
    for sy in dirs:
        a = tip + (0.0, sy * face, 0.0)
        b = a + (0.0, sy * length, -drop)
        string_set(m, a, b, kv, n, (1.0, 0.0, 0.0), 0.42, ring=0.45 if kv == 750 else 0.0)
        u = _unit(b - a)
        c = b + 0.75 * u
        xs = [x for x, _ in BUNDLE[kv]]
        zs = [z for _, z in BUNDLE[kv]]
        m.block(b + 0.06 * u, (1.0, 0.0, 0.0), (0.0, 0.0, 1.0),
                (max(xs) - min(xs) + 0.3, max(zs) - min(zs) + 0.3, 0.04), ALU)
        for x, z in BUNDLE[kv]:   # the dead-end clamps, along the line from the yoke to where the conductors start
            m.rod(b + 0.06 * u + (x, 0.0, z), c + (x, 0.0, z), 0.07, ALU, n=6)
        out.append(c)
    return (out[0], out[-1]) if len(out) == 2 else (out[0], out[0])


def earth_clamp(m: Mesh, p, up: float = 0.35) -> np.ndarray:
    """The earth wire's clamp hung under its peak or arm at p; returns where the wire passes."""
    p = np.asarray(p, float)
    q = p - (0.0, 0.0, up)
    m.rod(p, q, 0.04, ALU)
    m.rod(q - (0.0, 0.2, 0.0), q + (0.0, 0.2, 0.0), 0.06, ALU, n=6)
    return q


def footings(m: Mesh, profile, at=(0.0, 0.0), size=3.0) -> None:
    hw = profile[0][1]
    for sx, sy in [(1, 1), (-1, 1), (-1, -1), (1, -1)]:
        m.box((at[0] + sx * hw, at[1] + sy * hw, -0.5), (size, size, 1.6), CONCRETE)


def ladder(m: Mesh, profile, z1: float, mat: int = STEEL) -> None:
    """A ladder up the inside of one leg's face (detail; b32, b33): two rails 0.45 m apart and rungs every 0.4 m."""
    z, rails = np.linspace(0.5, z1, 24), []
    for s in (-0.225, 0.225):
        rails.append([np.array([_hw(profile, zz) - 0.7, s - _hw(profile, zz) + 0.9, zz]) for zz in z])
    for r in rails:
        for a, b in zip(r, r[1:]):
            m.rod(a, b, 0.05, mat)
    for zz in np.arange(0.8, z1, 0.4):
        x, y = _hw(profile, zz) - 0.7, 0.9 - _hw(profile, zz)
        m.rod((x, y - 0.225, zz), (x, y + 0.225, zz), 0.025, mat)


# ------------------------------------------------------------------ the types

def crossing750(height: float) -> tuple[Mesh, dict[str, Any]]:
    """126 m suspension (crossbar at 113 m, no. 23) or 100 m anchor: a square tower, its main arm (flat on top at the
    crossbar's height, its bottom chords rising to the tips) carrying the outer phases at its tips and the middle one
    in a window through the body, a short top arm for the earth wires; red and white from base to top (shore tower
    no. 26 as photographed). Suspension: the outer phases on two strings in line, the middle on eight side by side
    from a beam across the window (as photographed); anchor: tension sets of four."""
    anchor = height < 120
    s = height / 126.0
    zt = 113.0 * s                 # the main arm's top chord: the crossbar's height
    za = zt - 9.0                  # its bottom chord at the body
    prof = [(0, 11.0), (za - 26 * s, 3.6), (za, 3.0), (zt, 3.0), (height - 2, 1.6), (height, 1.6)]
    band = (0.0, height, 7)
    m = Mesh()
    lattice(m, prof, leg=0.5, brace=0.17, band=band, panel=0.9, window=(za, zt))
    footings(m, prof, size=4.0)
    tips = [arm(m, zt, 9.0, 3.0, 19.0, side, 3.0, half_tip=0.7, tip_depth=1.1, band=band, w=0.2, rail=True)
            for side in (-1, 1)]
    for side in (-1, 1):
        arm(m, height, 3.0, 1.6, 11.0, side, 1.6, half_tip=0.4, tip_depth=0.6, band=band, w=0.15)
    if anchor:  # the middle phase on sets from the body's faces, back and forward, its jumper through the window
        mid = tension(m, (0.0, 0.0, tips[0][2]), 9.0, 750, n=4, face=3.0)
        phases = [tension(m, tips[0], 9.0, 750, n=4), mid, tension(m, tips[1], 9.0, 750, n=4)]
    else:
        beam = zt - 0.4
        m.rod((-3.0, 0.0, beam), (3.0, 0.0, beam), 0.45, _paint(beam, band))
        phases = [suspend(m, tips[0], 7.0, 750, n=2), suspend(m, (0.0, 0.0, beam), 6.0, 750, n=8, across=(1, 0, 0), gap=0.26),
                  suspend(m, tips[1], 7.0, 750, n=2)]
    earth = [earth_clamp(m, (sx * 11.0, 0.0, height - 0.6)) for sx in (-1, 1)]
    if _D:
        ladder(m, prof, zt, _paint(zt / 2, None))
        if not anchor:   # the railed bracket on one side below the main arm (b29, b30, b46; no. 26)
            zb = za - 9.0 * s
            arm(m, zb, 2.4, _hw(prof, zb), _hw(prof, zb) + 7.0, 1, _hw(prof, zb), half_tip=0.6, tip_depth=1.2,
                band=band, w=0.14, rail=True)
    return m, {"kv": 750, "circuits": [phases], "earth": earth, "base_hw": prof[0][1]}


def crossing330() -> tuple[Mesh, dict[str, Any]]:
    """100 m double-circuit anchor (no. 19: crossbars at 92, 81 and 70 m), three arms a side (the middle the longest),
    each flat on top with a walkway, a peak with a small arm for the earth wires; red and white from the bottom arms up
    (the shore tower as photographed, galvanised below); each phase on tension sets of six strings side by side (the
    crossing's drawing: 6 × ПС-22, 27 discs)."""
    h = 100.0
    prof = [(0, 9.5), (62, 2.8), (92, 2.2), (h - 1, 1.1), (h, 1.1)]
    band = (64.0, h, 5)
    m = Mesh()
    lattice(m, prof, leg=0.42, brace=0.15, band=band, panel=0.9)
    footings(m, prof, size=3.5)
    circuits = []
    for side in (-1, 1):
        ph = []
        for z, reach in ((92.0, 7.5), (81.0, 11.0), (70.0, 9.5)):
            tip = arm(m, z, 2.6, _hw(prof, z), reach, side, _hw(prof, z), half_tip=0.8, tip_depth=1.9, band=band,
                      w=0.16, rail=True)
            ph.append(tension(m, tip, 5.5, 330, n=6))
        circuits.append(ph)
    for side in (-1, 1):
        arm(m, h, 1.2, 1.1, 3.5, side, 1.1, half_tip=0.3, tip_depth=0.5, band=band, w=0.12)
    earth = [earth_clamp(m, (sx * 3.5, 0.0, h - 0.5)) for sx in (-1, 1)]
    if _D:
        ladder(m, prof, 92.0)
    return m, {"kv": 330, "circuits": circuits, "earth": earth, "base_hw": 9.5}


def column(m: Mesh, foot, top, width, n: int = 10, leg: float = 0.2, brace: float = 0.09) -> None:
    """A slim square lattice column from foot to top, `width(t)` its half-width along it (t 0 at the foot, 1 at the
    top): the guyed portal's legs and peaks."""
    foot, top = np.asarray(foot, float), np.asarray(top, float)
    p, q = _basis(_unit(top - foot))
    for k in range(n):
        t0, t1 = k / n, (k + 1) / n
        c0, c1 = foot + t0 * (top - foot), foot + t1 * (top - foot)
        q0 = [c0 + width(t0) * (dx * p + dy * q) for dx, dy in [(1, 1), (-1, 1), (-1, -1), (1, -1)]]
        q1 = [c1 + width(t1) * (dx * p + dy * q) for dx, dy in [(1, 1), (-1, 1), (-1, -1), (1, -1)]]
        for c in range(4):
            m.angle(q0[c], q1[c], leg)
            m.angle(q0[c], q1[(c + 1) % 4], brace)
            m.angle(q0[c], q0[(c + 1) % 4], brace)


def pp750() -> tuple[Mesh, dict[str, Any]]:
    """Guyed portal (ZNPP-Dniprovska no. 30): two lattice legs on pinned feet, closing toward the top, a truss beam
    with the three phases on single long I-strings (as photographed), earth-wire peaks, four guys."""
    m = Mesh()
    zb = 30.0
    for sx in (-1, 1):
        foot, top = np.array([sx * 15.0, 0.0, 0.0]), np.array([sx * 9.0, 0.0, zb])
        column(m, foot, top, lambda t: 0.3 + 0.7 * math.sin(math.pi * min(t, 0.85)))  # thinnest at the pinned foot
        column(m, top + (0, 0, 1.2), (sx * 13.0, 0.0, 41.0), lambda t: 0.55 - 0.45 * t, n=6, leg=0.12, brace=0.06)
        for sy in (-1, 1):
            m.rod(top + (0, 0, 1.0), (sx * 17.0, sy * 20.0, 0.0), 0.08, GUY)
    for sy in (-1, 1):  # the beam: a box truss, chords along the bottom fore and aft and one along the top
        for z in (zb, zb + 2.5):
            if z == zb + 2.5 and sy == 1:
                continue
            m.angle((-19.5, sy * 1.0 if z == zb else 0.0, z), (19.5, sy * 1.0 if z == zb else 0.0, z), 0.22)
    for k in range(14):
        x0, x1 = -19.5 + 39 * k / 14, -19.5 + 39 * (k + 1) / 14
        for sy in (-1, 1):
            m.angle((x0, sy * 1.0, zb), (x1, 0.0, zb + 2.5), 0.1)
            m.angle((x1, sy * 1.0, zb), (x1, 0.0, zb + 2.5), 0.08)
        m.angle((x0, -1.0, zb), (x0, 1.0, zb), 0.1)
    phases = [suspend(m, (x, 0.0, zb), 6.5, 750) for x in (-19.0, 0.0, 19.0)]
    earth = [earth_clamp(m, (sx * 13.0, 0.0, 41.0)) for sx in (-1, 1)]
    return m, {"kv": 750, "circuits": [phases], "earth": earth, "base_hw": 15.0}


def triple750() -> tuple[Mesh, dict[str, Any]]:
    """Three single-phase anchor towers across the line (OSM triple_tower; ZNPP-Dniprovska's anchor and end towers
    as photographed), each phase on tension sets of three strings from its tower's faces, ringed at the line end, the
    jumper looping round the tower's side; the outer two carry the earth wires on peaks."""
    m = Mesh()
    prof = [(0, 4.5), (26, 1.6), (30, 1.4)]
    phases, earth = [], []
    for x in (-19.0, 0.0, 19.0):
        lattice(m, prof, at=(x, 0.0), leg=0.3, brace=0.11)
        for sx in (-1, 1):
            m.rod((x + sx * 1.4, 0.0, 30.0), (x + sx * 3.2, 0.0, 30.0), 0.3)
        phases.append(tension(m, (x, 0.0, 28.0), 8.0, 750, n=3, face=_hw(prof, 28.0)))
        if x:
            top = np.array([x, 0.0, 30.0])
            m.rod(top, top + (0, 0, 5.0), 0.35)
            earth.append(earth_clamp(m, top + (0, 0, 5.0), 0.25))
    return m, {"kv": 750, "circuits": [phases], "earth": earth, "base_hw": 23.5, "jumper": (3.5, 0.0, -2.0)}


def triple330() -> tuple[Mesh, dict[str, Any]]:
    """Three single-phase end towers of the 330 kV crossing (OSM triple_tower; as photographed at Illinka, the steel
    weathered brown): both circuits end here, one phase of each on every tower (an arm at two heights), tension sets
    of four strings."""
    m = Mesh()
    prof = [(0, 3.2), (28, 1.0), (32, 0.8)]
    upper, lower, earth = [], [], []
    for x in (-10.0, 0.0, 10.0):
        lattice(m, prof, at=(x, 0.0), leg=0.25, brace=0.1, base=RUST)
        up = arm(m, 29.6, 1.6, _hw(prof, 28), 4.5, -1, _hw(prof, 28), at=(x, 0.0), w=0.12, base=RUST)
        lo = arm(m, 23.8, 1.8, _hw(prof, 22), 4.5, 1, _hw(prof, 22), at=(x, 0.0), w=0.12, base=RUST)
        upper.append(tension(m, up, 5.0, 330, n=4))
        lower.append(tension(m, lo, 5.0, 330, n=4))
        if x:
            top = np.array([x, 0.0, 32.0])
            m.rod(top, top + (0, 0, 3.0), 0.25, RUST)
            earth.append(earth_clamp(m, top + (0, 0, 3.0), 0.2))
    return m, {"kv": 330, "circuits": [upper, lower], "earth": earth, "base_hw": 13.2}


def pvs330() -> tuple[Mesh, dict[str, Any]]:
    """ПВС: a П-shaped reinforced-concrete portal with ties between its two poles (Л-243/Л-244 on land, as
    photographed), the phases on I-strings under its steel beam."""
    m = Mesh()
    for sx in (-1, 1):
        m.rod((sx * 4.25, 0.0, 0.0), (sx * 4.25, 0.0, 27.0), 0.62, CONCRETE, n=10)
    for z0, z1 in ((7.0, 14.0), (14.0, 21.0)):
        m.rod((-4.25, 0.0, z0), (4.25, 0.0, z1), 0.12)
        m.rod((4.25, 0.0, z0), (-4.25, 0.0, z1), 0.12)
    for z in (22.5, 24.0):
        m.rod((-8.8, 0.0, z), (8.8, 0.0, z), 0.25)
    for k in range(8):
        x0, x1 = -8.8 + 17.6 * k / 8, -8.8 + 17.6 * (k + 1) / 8
        m.rod((x0, 0.0, 22.5 if k % 2 else 24.0), (x1, 0.0, 24.0 if k % 2 else 22.5), 0.12)
    phases = [suspend(m, (x, 0.0, 22.5), 3.6, 330) for x in (-8.5, 0.0, 8.5)]
    earth = [earth_clamp(m, (sx * 4.25, 0.0, 27.0), 0.2) for sx in (-1, 1)]
    return m, {"kv": 330, "circuits": [phases], "earth": earth, "base_hw": 4.6}


def gantry(reach: float, z: float, kv: int) -> tuple[Mesh, dict[str, Any]]:
    """A switchyard gantry where the line leaves the yard: two lattice columns and a beam (representative)."""
    m = Mesh()
    x = reach + 3.0
    for sx in (-1, 1):
        lattice(m, [(0, 1.0), (z + 4, 0.6)], at=(sx * x, 0.0), leg=0.22, brace=0.1)
    for zz in (z, z + 1.5):
        m.rod((-x, 0.0, zz), (x, 0.0, zz), 0.3)
    phases = [tension(m, (px, 0.0, z), 5.0, kv, n=2 if kv == 750 else 1, drop=0.3, dirs=(1,)) for px in (-reach, 0.0, reach)]
    return m, {"kv": kv, "circuits": [phases], "earth": [np.array([sx * x, 0.0, z + 4.0]) for sx in (-1, 1)],
               "base_hw": x + 1}


def caisson(r_base: float, r_top: float) -> tuple[Mesh, dict[str, Any]]:
    """A floated foundation, as the drained bed shows them (Esri World Imagery, 23 August 2024, and the 2015 aerial
    film): a faceted reinforced-concrete drum with pilaster ribs at its joints and a faceted cone up to the flat top
    the tower's legs stand on, `WATER_UP_M` above the normal level (z 0 here: `POOL_M`). Below the old
    waterline the concrete is stained by 68 years under water (representative). Its proportions are representative;
    its diameters are the sources'."""
    m = Mesh()
    n = CAISSON_PANELS
    z0, zd, zt = -CAISSON_DOWN_M, -CAISSON_DOWN_M + CAISSON_DRUM_M, WATER_UP_M
    wet = -1.0   # the old waterline's band (the level swung about a metre)
    m.frustum(z0, zd, r_base, r_base, STAINED, n=n, cap=False)
    rw = r_base + (r_top - r_base) * (wet - zd) / (zt - zd)   # the cone's radius at the old waterline
    m.frustum(zd, wet, r_base, rw, STAINED, n=n, cap=False)
    m.frustum(wet, zt, rw, r_top, CONCRETE, n=n)
    for k in range(n):   # the ribs: up the drum, then up the cone
        t = 2 * math.pi * (k + 0.5) / n
        c, s_ = math.cos(t), math.sin(t)
        rb, rt = r_base + 0.25, r_top + 0.25
        m.rod((c * rb, s_ * rb, z0), (c * rb, s_ * rb, zd), 0.7, STAINED)
        m.rod((c * rb, s_ * rb, zd), (c * rt, s_ * rt, zt - 0.3), 0.6, CONCRETE if k % 2 else STAINED)
    m.frustum(zd - 0.4, zd + 0.4, r_base + 0.45, r_base + 0.45, STAINED, n=n, cap=False)   # the drum's capping beam
    return m, {"circuits": [], "earth": [], "base_hw": r_base}


def build_types(detail: bool = False) -> dict[str, tuple[Mesh, dict[str, Any]]]:
    """Every type's mesh and attachment points; `detail` (look pass 2): more members and finer fittings, the same
    attachment points."""
    global _D
    _D = detail
    try:
        return _build_types()
    finally:
        _D = False


def _build_types() -> dict[str, tuple[Mesh, dict[str, Any]]]:
    return {"crossing750_p": crossing750(126.0), "crossing750_a": crossing750(100.0), "crossing330": crossing330(),
            "pp750": pp750(), "triple750": triple750(), "triple330": triple330(), "pvs330": pvs330(),
            "gantry750": gantry(19.0, 20.0, 750), "gantry330": gantry(8.5, 17.0, 330),
            "caisson750": caisson(20.0, 16.0), "caisson330": caisson(21.8, 14.5)}


TYPE_DOC = {
    "crossing750_p": {"height_m": 126, "crossbar_m": 113, "sources": ["ssp_63206", "novoklimov", "ukwiki", "esri"],
                      "what": "750 kV crossing, suspension"},
    "crossing750_a": {"height_m": 100, "sources": ["novoklimov", "ukwiki"], "what": "750 kV crossing, the anchor"},
    "crossing330": {"height_m": 100, "crossbars_m": [92, 81, 70], "sources": ["ssp_94005", "novoklimov", "ukwiki", "esri"],
                    "what": "330 kV crossing, double-circuit anchor (sources: 90 and 100 m; which is which isn't "
                            "published, all drawn at no. 19's 100 m)"},
    "pp750": {"height_m": 41, "sources": ["novoklimov"], "what": "750 kV guyed portal (photo of no. 30); size representative"},
    "triple750": {"height_m": 35, "sources": ["osm", "novoklimov", "esri"], "what": "750 kV anchor/end: three single-phase towers"},
    "triple330": {"height_m": 35, "sources": ["osm", "novoklimov"], "what": "330 kV crossing's end: three single-phase towers"},
    "pvs330": {"height_m": 27, "sources": ["novoklimov"], "what": "330 kV ПВС reinforced-concrete portal; size representative"},
    "gantry750": {"height_m": 24, "sources": [], "what": "switchyard gantry, representative"},
    "gantry330": {"height_m": 21, "sources": [], "what": "switchyard gantry, representative"},
    "caisson750": {"diameter_m": 40, "sources": ["ssp_63206", "ukwiki", "novoklimov", "esri"],
                   "what": "floated caisson: faceted ribbed drum, cone to a flat top (proportions and top representative)"},
    "caisson330": {"diameter_m": [43.6, 29], "sources": ["ssp_94005", "novoklimov", "esri"],
                   "what": "floated caisson: faceted ribbed drum, cone to a flat top (proportions representative)"},
}

FITTINGS_DOC = {
    "bundle": {"750": "five sub-conductors on a 0.6 m pentagon", "330": "two sub-conductors 0.4 m apart"},
    "conductor_r_m": CONDUCTOR_R, "earth_r_m": EARTH_R, "disc": {str(k): {"d_m": d, "pitch_m": p} for k, (d, p) in DISC.items()},
    "spacer_m": SPACER_M,
    "statement": "Fittings of the kinds photographed on these towers (glass disc strings, yoke plates, rings, the "
                 "bundle's clamps, spacers, dampers); their sizes, counts and spacing typical, representative.",
}


# ------------------------------------------------------------------ placing them

def assign(lines: list[dict[str, Any]], schemes: dict[str, str]) -> None:
    """Each tower's type from its OSM tags and its line's crossing scheme (К end, П suspension, А anchor, the
    letters as the sources give them); a line whose towers don't fit its scheme is refused, never guessed. A line with
    no scheme crosses no river: land types only (and a crossing tower on it is refused)."""
    for ln in lines:
        kv = ln["kv"]
        tw = ln["towers"]
        idx = [i for i, t in enumerate(tw) if t["kind"] == "crossing"]
        if ln["name"] not in schemes:
            if idx:
                raise ValueError(f"{ln['name']}: crossing towers in OSM but no crossing scheme")
            inner = []
        else:
            inner = schemes[ln["name"]].replace("K", "К").replace("P", "П").replace("A", "А").split("-")[1:-1]
            if len(idx) != len(inner) or idx != list(range(idx[0], idx[0] + len(idx))):
                raise ValueError(f"{ln['name']}: {len(idx)} crossing towers in OSM, the scheme {schemes[ln['name']]} has {len(inner)}")
        for e in ([idx[0] - 1, idx[-1] + 1] if idx else []):
            if tw[e]["tags"].get("triple_tower") != "yes":
                raise ValueError(f"{ln['name']}: the crossing's end tower {tw[e]['osm_node']} isn't tagged triple_tower")
        for i, t in enumerate(tw):
            tg = t["tags"]
            water = False
            if t["osm_node"] is None:  # the switchyard where the line starts or ends (not where the land's box cuts
                end = i == 0 or (i == len(tw) - 1 and not ln.get("cut"))   # it); elsewhere a bend of the way
                ty = f"gantry{kv}" if end else None  # with no tower mapped: none drawn
            elif i in idx:
                letter = inner[i - idx[0]]
                ty = "crossing330" if kv == 330 else ("crossing750_a" if letter == "А" else "crossing750_p")
                water = i not in (idx[0], idx[-1])   # the shore towers stand on land, the rest in the reservoir
            elif tg.get("triple_tower") == "yes":
                ty = f"triple{kv}"
            else:
                ty = "pp750" if kv == 750 else "pvs330"
            t["type"] = ty
            t["caisson"] = f"caisson{kv}" if water else None


def headings(tw: list[dict[str, Any]]) -> list[float]:
    """Each tower's turn about z (radians) so its frame's y runs along the line (the bisector at an angle)."""
    xy = np.array([t["xy"] for t in tw], float)
    out = []
    for i in range(len(xy)):
        d = []
        if i > 0:
            d.append(xy[i] - xy[i - 1])
        if i < len(xy) - 1:
            d.append(xy[i + 1] - xy[i])
        a = sum(v / np.linalg.norm(v) for v in d)
        out.append(math.atan2(-a[0], a[1]))
    return out


def _world(t: dict[str, Any], p: np.ndarray) -> np.ndarray:
    c, s = math.cos(t["rot_z"]), math.sin(t["rot_z"])
    return np.array([t["xy"][0] + c * p[0] - s * p[1], t["xy"][1] + s * p[0] + c * p[1], t["base_m"] + p[2]])


def _sag(a: np.ndarray, b: np.ndarray, cat: float, n: int) -> np.ndarray:
    """The conductor between two points: a parabola (the catenary, close enough at these sags) of L²/8C."""
    t = np.linspace(0.0, 1.0, n)[:, None]
    L = float(np.linalg.norm((b - a)[:2]))
    p = a + t * (b - a)
    p[:, 2] -= 4 * (L * L / (8 * cat)) * t[:, 0] * (1 - t[:, 0])
    return p


def _phases(c):
    return sorted(c, key=lambda q: q[0][0])  # left to right across the line


def _length(A, ca, B, cb) -> float:
    return sum(float(np.linalg.norm(_world(A, x[1])[:2] - _world(B, y[0])[:2])) for x, y in zip(_phases(ca), _phases(cb)))


def _off(p: np.ndarray, o: tuple[float, float]) -> np.ndarray:
    return p + np.array([o[0], 0.0, o[1]])


def wires(lines: list[dict[str, Any]], attach: dict[str, dict[str, Any]], cat: dict[str, float],
          water: dict[str, list[tuple[float, float]]] | None = None) -> list[dict[str, Any]]:
    """Every conductor and earth wire as polylines in the plane: span by span between the towers' attachment points
    (circuit to circuit; where a tower carries two circuits and the next one, the pair that hangs shorter), a jumper
    below each anchor's tip joining its back and forward dead ends. Each phase is its bundle's centre line
    (`bundle`: the glow round it in build.py) and its sub-conductors (`phase`, `jumper`) round it as BUNDLE, in each
    tower's frame at its ends; `group` ties a phase's together. Sag representative (C by span: `cat`). Every point
    carries `along`: metres from the line's start (its plant end) tower to tower, for the flow drawn along it, and
    `cross`: 1 over the water, falling to 0 within CROSS_EASE_M beyond it on land. The water is `water` by line name
    (stretches as metres north, the survey's reservoir), else the crossing between its end towers."""
    out = []
    group = 0
    for li, ln in enumerate(lines):
        sub = BUNDLE[ln["kv"]]
        tw = [t for t in ln["towers"] if t["type"]]
        at = np.concatenate([[0.0], np.cumsum([np.linalg.norm(np.subtract(b["xy"], a["xy"])) for a, b in zip(tw, tw[1:])])])
        ci = [i for i, t in enumerate(tw) if t["type"].startswith("crossing")]
        wet = (water or {}).get(ln["name"])

        def cross(along, pts, wet=wet, span=(at[ci[0]], at[ci[-1]]) if ci else None):
            if wet:   # by how far north, out of the stretches of water
                d = np.min([np.maximum(a - pts[:, 1], pts[:, 1] - b) for a, b in wet], axis=0)
            elif span:
                d = np.maximum(span[0] - along, along - span[1])
            else:
                return np.zeros_like(along)
            x = 1 - (d.clip(0) / CROSS_EASE_M).clip(0, 1)
            return x * x * (3 - 2 * x)

        for i in range(len(tw) - 1):
            A, B = tw[i], tw[i + 1]
            aa, ab = attach[A["type"]], attach[B["type"]]
            big = "crossing" in A["type"] or "crossing" in B["type"]
            L = float(np.linalg.norm(np.subtract(B["xy"], A["xy"])))
            c = cat["crossing"] if big and L > 600 else cat["span"]
            n = max(8, int(L / 25))
            along = at[i] + np.linspace(0.0, L, n)
            ca, cb = aa["circuits"], ab["circuits"]
            if len(ca) == len(cb):
                pairs = list(zip(ca, cb))
            elif len(ca) == 1:
                pairs = [(ca[0], min(cb, key=lambda cc: _length(A, ca[0], B, cc)))]
            else:
                pairs = [(min(ca, key=lambda cc: _length(A, cc, B, cb[0])), cb[0])]
            for pa, pb in pairs:
                for x, y in zip(_phases(pa), _phases(pb)):
                    out.append({"line": li, "kind": "bundle", "group": group, "along": along,
                                "pts": _sag(_world(A, x[1]), _world(B, y[0]), c, n)})
                    for o in sub:
                        out.append({"line": li, "kind": "phase", "group": group, "along": along,
                                    "pts": _sag(_world(A, _off(x[1], o)), _world(B, _off(y[0], o)), c, n)})
                    group += 1
            for x, y in zip(sorted(aa["earth"], key=lambda q: q[0]), sorted(ab["earth"], key=lambda q: q[0])):
                out.append({"line": li, "kind": "earth", "along": along,
                            "pts": _sag(_world(A, x), _world(B, y), c * 1.15, n)})
        for t, a_t in zip(tw, at):  # jumpers at the anchors
            a = attach[t["type"]]
            for circ in a["circuits"]:
                for back, fwd in circ:
                    if np.allclose(back, fwd):
                        continue
                    sag = np.array(a.get("jumper", (0.0, 0.0, -(3.0 if ln["kv"] == 750 else 2.0))))
                    ts = np.linspace(0, 1, 11)[:, None]
                    for kind, o in [("bundle", (0.0, 0.0))] + [("jumper", o) for o in sub]:
                        b0, b1 = _off(back, o), _off(fwd, o)
                        mid = (b0 + b1) / 2 + sag
                        loc = (1 - ts) ** 2 * b0 + 2 * ts * (1 - ts) * mid + ts ** 2 * b1
                        jal = a_t + (ts[:, 0] - 0.5) * float(np.linalg.norm(b1 - b0))
                        out.append({"line": li, "kind": kind, "group": group, "along": jal,
                                    "pts": np.array([_world(t, q) for q in loc])})
                    group += 1
        for w in out:
            if w["line"] == li:
                w["cross"] = cross(w["along"], w["pts"])
    return out


def _along(pts: np.ndarray) -> np.ndarray:
    return np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])


def _at(pts: np.ndarray, s: np.ndarray, d: float) -> tuple[np.ndarray, np.ndarray]:
    """The point `d` metres along a polyline (cumulative lengths `s`) and the direction there."""
    i = int(np.clip(np.searchsorted(s, d) - 1, 0, len(pts) - 2))
    f = (d - s[i]) / max(s[i + 1] - s[i], 1e-9)
    return pts[i] + f * (pts[i + 1] - pts[i]), _unit(pts[i + 1] - pts[i])


def _damper(m: Mesh, p: np.ndarray, u: np.ndarray) -> None:
    """A Stockbridge damper: its clamp on the wire, the messenger cable below along it, a weight at each end (in
    detail: bell-shaped weights)."""
    q = p - (0.0, 0.0, 0.13)
    m.rod(p, q, 0.035, ALU)
    m.rod(q - 0.32 * u, q + 0.32 * u, 0.02, GUY, n=4)
    for sgn in (-1, 1):
        if _D:
            m._rings([(q + sgn * 0.2 * u, 0.025), (q + sgn * 0.26 * u, 0.045), (q + sgn * 0.4 * u, 0.05),
                      (q + sgn * 0.44 * u, 0.02)], sgn * u, GUY, 8)
        else:
            m.rod(q + sgn * 0.2 * u, q + sgn * 0.42 * u, 0.085, GUY, n=6)


def fittings(ws: list[dict[str, Any]], kvs: list[int], detail: bool = False) -> Mesh:
    """The fittings along the spans, in the world's frame: spacers holding each bundle's sub-conductors apart every
    SPACER_M (none within 25 m of a clamp), and Stockbridge dampers 2 m out from every clamp on each sub-conductor and
    earth wire. Spans under 150 m (the jumpers) get none. `detail` (look pass 2): 750 kV spacer-dampers with a hub
    and an arm to each sub-conductor's clamp, bell-weighted dampers."""
    global _D
    _D = detail
    try:
        return _fittings(ws, kvs)
    finally:
        _D = False


def _fittings(ws: list[dict[str, Any]], kvs: list[int]) -> Mesh:
    m = Mesh()
    groups: dict[int, list[np.ndarray]] = {}
    for w in ws:
        if w["kind"] == "phase":
            groups.setdefault(w["group"], []).append((w["line"], w["pts"]))
        if w["kind"] in ("phase", "earth"):
            s = _along(w["pts"])
            if s[-1] < 150:
                continue
            for d in (2.0, s[-1] - 2.0):
                p, u = _at(w["pts"], s, d)
                _damper(m, p, u)
    for subs in groups.values():
        kv = kvs[subs[0][0]]
        P = [p for _, p in subs]
        s = _along(P[0])
        if s[-1] < 150:
            continue
        k = max(1, int((s[-1] - 50) // SPACER_M[kv]))
        for frac in (25.0 + (s[-1] - 50.0) * (np.arange(k) + 0.5) / k) / s[-1]:
            pts = [_at(p, _along(p), frac * _along(p)[-1]) for p in P]
            for (a, u), (b, _) in zip(pts, pts[1:] + pts[:1] if len(pts) > 2 else pts[1:]):
                m.rod(a, b, 0.045, ALU, n=4)
            for a, u in pts:
                m.rod(a - 0.09 * u, a + 0.09 * u, 0.06, ALU, n=6)
            if _D and len(pts) > 2:   # the spacer-damper's hub and arms
                hub = sum(a for a, _ in pts) / len(pts)
                m.rod(hub - 0.06 * pts[0][1], hub + 0.06 * pts[0][1], 0.14, ALU, n=8)
                for a, _ in pts:
                    m.rod(hub, a, 0.035, ALU, n=4)
    return m
