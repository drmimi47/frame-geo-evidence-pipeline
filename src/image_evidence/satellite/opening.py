"""The film's opening: a fade in on a power plant, then its lines drawn out from it in red, labelled.

The lines are OpenStreetMap ways from the corridor's saved Overpass reply for the plants' surroundings
(`raw/osm_opening.json`, fetched once, like `osm_power.json`): coordinates from a source that has its own, drawn,
never seen in the imagery. Each branch starts at the end nearest its origin (a plant or switchyard, also from the
reply) and grows outward. Labels name a line as the area's config does: from the ways' own tags (ref, from, to) and,
where a way has none, from the source the config names (e.g. Bellona's map of the plant's lines).
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import httpx
import numpy as np
from PIL import Image, ImageDraw

from ..layout import write_json
from .corridor import KZ, Grid, fetch_overpass
from .store import corridor_dir

OPENING_FILE = "osm_opening.json"
LABEL_FADE_S = 0.8
FADE_OUT_S = 4.0  # the other lines and the labels fade out over the track's first seconds


def sites_query(bbox: tuple[float, float, float, float]) -> str:
    w, s, e, n = bbox
    box = f"{s},{w},{n},{e}"
    return (f'[out:json][timeout:120];(nwr({box})[power~"^(plant|substation)$"];way({box})[power=line];);'
            "out tags geom;")


def reply(root: Path, corridor_id: str, bbox: tuple[float, float, float, float], http: httpx.Client | None = None) -> dict[str, Any]:
    """The saved reply for the opening's box, fetched the first time (the reply saved verbatim)."""
    path = corridor_dir(root, corridor_id) / "raw" / OPENING_FILE
    if not path.is_file():
        with (http or httpx.Client()) as client:
            write_json(path, fetch_overpass(sites_query(bbox), client))
    return json.loads(path.read_text())


def _smooth(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def _metres(coords: np.ndarray) -> np.ndarray:
    """Cumulative ground distance along lon/lat points."""
    d = np.diff(coords, axis=0)
    kx = 111320.0 * np.cos(np.radians((coords[1:, 1] + coords[:-1, 1]) / 2))
    return np.concatenate([[0.0], np.cumsum(np.hypot(d[:, 0] * kx, d[:, 1] * KZ))])


@dataclass
class Branch:
    label: str
    kv: int
    start_s: float
    draw_s: float
    reach_m: float
    label_m: float
    ways: list[int]
    lonlat: np.ndarray   # (n, 2), from the origin outward
    cum: np.ndarray      # metres along it
    px: np.ndarray       # grid pixels
    side: str = "auto"   # the label's side of the line: left, right, or auto (whichever has room)

    def reached(self, t: float) -> float:
        return self.reach_m * _smooth((t - self.start_s) / self.draw_s)

    def drawn(self, r: float) -> np.ndarray:
        """Grid pixels of the first r metres."""
        k = int(np.searchsorted(self.cum, r))
        if k >= len(self.cum):
            return self.px
        if k == 0:
            return self.px[:1]
        f = (r - self.cum[k - 1]) / max(1e-9, self.cum[k] - self.cum[k - 1])
        return np.vstack([self.px[:k], self.px[k - 1] + (self.px[k] - self.px[k - 1]) * f])

    def at(self, m: float) -> np.ndarray:
        return np.array([np.interp(m, self.cum, self.px[:, 0]), np.interp(m, self.cum, self.px[:, 1])])


class Opening:
    def __init__(self, cfg: dict[str, Any], osm: dict[str, Any], grid: Grid, line: list[list[float]]):
        self.cfg, self.grid, self.osm = cfg, grid, osm
        self.els = {(e["type"], e["id"]): e for e in osm["reply"]["elements"]}
        self.origins = {name: self._centre(i) for name, i in cfg["origins"].items()}
        self.centre = self._centre(cfg["plant"])
        self.branches = [self._branch(b) for b in cfg["branches"]]
        main = cfg.get("line") or {}
        coords = np.array(line, float)
        self.branches.append(Branch(main.get("label", ""), int(main.get("kv", 330)), float(main.get("start_s", 0)),
                                    float(main.get("draw_s", 5)), float(main.get("reach_m", 9000)),
                                    float(main.get("label_m", 2500)), [], coords, _metres(coords),
                                    np.array([grid.to_px(x, y) for x, y in coords])))
        self.main = self.branches[-1]
        self.sites = [(s["text"], self._foot(s["osm"])) for s in cfg.get("sites") or []]

    def _way(self, i: int) -> dict[str, Any]:
        e = self.els.get(("way", int(i)))
        if e is None or not e.get("geometry"):
            raise ValueError(f"opening: OpenStreetMap way {i} is not in the saved reply ({OPENING_FILE})")
        return e

    def _centre(self, i: int) -> tuple[float, float]:
        g = self._way(i)["geometry"]
        if len(g) > 1 and g[0] == g[-1]:  # a closed way repeats its first point
            g = g[:-1]
        return float(np.mean([p["lon"] for p in g])), float(np.mean([p["lat"] for p in g]))

    def _foot(self, i: int) -> tuple[float, float]:
        """The middle of a site's southern edge (where its label hangs)."""
        g = self._way(i)["geometry"]
        return float(np.mean([p["lon"] for p in g])), float(min(p["lat"] for p in g))

    def _branch(self, b: dict[str, Any]) -> Branch:
        ox, oy = self.origins[b["from"]]
        kx = 111320.0 * math.cos(math.radians(oy))
        pts: list[tuple[float, float]] = []
        for i in b["ways"]:  # each way turned so it starts where the last ended (the first: at the origin)
            g = [(p["lon"], p["lat"]) for p in self._way(i)["geometry"]]
            ax, ay = pts[-1] if pts else (ox, oy)
            near = lambda q: math.hypot((q[0] - ax) * kx, (q[1] - ay) * KZ)
            pts += g if near(g[0]) <= near(g[-1]) else g[::-1]
        coords = np.array(pts, float)
        tags = self._way(b["ways"][0]).get("tags", {})
        return Branch(b.get("label", ""), int(b.get("kv") or int(tags.get("voltage", "0").split(";")[0] or 0) // 1000),
                      float(b.get("start_s", 0)), float(b.get("draw_s", 5)), float(b.get("reach_m", 9000)),
                      float(b.get("label_m", 2500)), [int(i) for i in b["ways"]], coords, _metres(coords),
                      np.array([self.grid.to_px(x, y) for x, y in coords]), b.get("side", "auto"))

    def draw(self, img: np.ndarray, M: np.ndarray, t: float, others: float, rgb: np.ndarray) -> np.ndarray:
        """The lines as reached at t seconds into the opening (the corridor's own line always fully opaque, the others
        at `others`), then their labels and the sites' names."""
        h, w = img.shape[:2]
        inv = cv2.invertAffineTransform(M)
        to_frame = lambda px: px @ inv[:, :2].T + inv[:, 2]
        unit = max(1, round(h / 540))
        for group, alpha in ((self.branches[:-1], others), ([self.main], 1.0)):
            if alpha <= 0:
                continue
            layer = np.zeros((h, w), np.uint8)
            for b in group:
                r = b.reached(t)
                if r > 0:
                    pts = (to_frame(b.drawn(r)) * 16).astype(np.int32)
                    cv2.polylines(layer, [pts], False, 255, unit + (1 if b.kv >= 750 else 0), cv2.LINE_AA, shift=4)
            a = layer.astype(np.float32)[..., None] / 255 * 0.9 * alpha
            img = img * (1 - a) + rgb * a
        labels = Image.new("LA", (w, h), (0, 0))
        d = ImageDraw.Draw(labels)
        from .film import _font
        font = _font(max(9, round(h * 0.015)))
        for b in self.branches:  # every label goes with the other lines (the corridor's line stays, unlabelled)
            alpha = others
            r = b.reached(t)
            if not b.label or alpha <= 0 or r < b.label_m:
                continue
            # the label fades in once the line has reached it, beside the line at label_m
            since = (t - b.start_s) - b.draw_s * self._time_at(b, b.label_m)
            op = alpha * _smooth(since / LABEL_FADE_S)
            x, y = to_frame(b.at(b.label_m))
            right = {"left": False, "right": True}.get(b.side, x < w * 0.62)  # beside the line, where there's room
            d.text((x + 9 if right else x - 9, y), b.label, font=font, anchor="lm" if right else "rm",
                   fill=(240, round(255 * op)), stroke_width=2, stroke_fill=(15, round(190 * op)))
        for text, (lon, lat) in self.sites:
            x, y = to_frame(np.array(self.grid.to_px(lon, lat)))
            op = others * _smooth(t / LABEL_FADE_S - 2)
            d.text((x, y + 8), text, font=font, anchor="mt", fill=(240, round(255 * op)), stroke_width=2,
                   stroke_fill=(15, round(190 * op)))
        la = np.asarray(labels, np.float32)
        a = (la[..., 1] / 255)[..., None]
        return img * (1 - a) + la[..., :1] * a

    @staticmethod
    def _time_at(b: Branch, m: float) -> float:
        """The share of the draw at which the line reaches m metres (inverting the eased reach)."""
        lo, hi = 0.0, 1.0
        for _ in range(30):
            mid = (lo + hi) / 2
            if b.reach_m * _smooth(mid) < m:
                lo = mid
            else:
                hi = mid
        return hi

    def record(self) -> dict[str, Any]:
        return {"plant": self.cfg["plant"], "centre": [round(c, 6) for c in self.centre], "view_m": self.cfg["view_m"],
                "osm": {k: self.osm[k] for k in ("query", "server", "fetched_at", "licence")},
                "names": self.cfg.get("names", ""),
                "lines": [{"label": b.label, "kv": b.kv, "ways": b.ways or "the corridor's line",
                           "drawn_m": b.reach_m} for b in self.branches]}
