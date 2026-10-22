"""Lay one satellite pass on a corridor's grid: crop, stitch, co-register, measure water, cut chips.

- Tiles: the grid is fetched in tiles of TILE pixels, and only those within the corridor's strip round its line (all
  of a small corridor; along a long line, a band a few kilometres wide), or round its first `until_m` metres for a
  pass fetched only for the start of the line. Each tile is fetched, laid on the reference pass, written and let go,
  so a corridor of any length fits in memory.
- Crop and stitch: each item of the pass (the tiles of one overpass) is cropped to a tile in pieces of at most 2048
  pixels, each piece's box on exact pixel edges, so every piece and every item lands on the same pixels. Where items
  overlap the first with data wins (they are the same instant). Bands are read bilinear, the cloud mask (scene
  classification / pixel QA) nearest-neighbour.
- Co-register: the products are orthorectified, but passes can sit a few metres apart (Landsat against Sentinel-2
  by 10-15 m). Each tile of a later pass is shifted onto the same tile of the corridor's reference pass by phase
  correlation of near-infrared detail on clear land (water left out: the reservoir is exactly what changed), refined
  by ECC; only small, clear shifts are applied, and the shift is recorded either way.
- Water: open water is dark in the near and shortwave infrared (reflectance under 3%, as scripts/scene/terrain.py).
"""

from __future__ import annotations

import hashlib
import logging
import math
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import cv2
import httpx
import numpy as np

from ..derivatives import write_derivative
from ..schema import FrameFiles, Provenance
from .corridor import Grid
from .providers import MAX_CROP_PX, Sensor, crop
from .schema import Alignment, ChipCore, ChipDerived, ChipLink, PassFiles, SatelliteChip, TileFile, chip_id_for

log = logging.getLogger(__name__)

TILE = 2048                 # pixels a side of a stored tile
WATER_REFL = 300            # reflectance x 10000: open water stays under 3% in NIR and SWIR
MAX_SHIFT_PX = 3.0          # larger shifts are recorded, never applied (likely a wrong match, not a misregistration)
MIN_RESPONSE = 0.08         # phase-correlation peak below this: too weak to trust
BREACH = date(2023, 6, 6)   # the Kakhovka dam was destroyed: exposure is measured against the last pass before it
# True colour for display, the same for every pass and sensor so passes compare: red, green and blue surface
# reflectance linear up to a knee, then a soft shoulder reaching white at WHITE (the drained bed's bright sand and shells
# keep their detail instead of clipping), then a gentle gamma.
KNEE, WHITE, SHOULDER, GAMMA = 0.16, 0.42, 2.2, 1 / 1.4
DISPLAY = (f"true colour from red, green and blue surface reflectance: linear to {KNEE:.2f}, a soft shoulder to white at "
           f"{WHITE:.2f}, gamma {1 / GAMMA:.1f}; the same for every pass")
WEB_PX, THUMB_PX = 1600, 400
OVERVIEW_PX = 2400          # the whole corridor's chip, at most this many pixels a side


def tone(refl: np.ndarray) -> np.ndarray:
    """Surface reflectance (0..1) -> display value (0..1)."""
    t = np.clip((refl - KNEE) / (WHITE - KNEE), 0, None)
    shoulder = KNEE / WHITE + (1 - KNEE / WHITE) * (1 - np.exp(-SHOULDER * t)) / (1 - np.exp(-SHOULDER))
    return np.clip(np.where(refl < KNEE, refl / WHITE, shoulder), 0, 1) ** GAMMA


@dataclass
class Mosaic:
    """A piece of a pass on the grid. `rgb_refl` (red, green, blue reflectance x 10000) only while it is fetched; what
    is kept is the near and shortwave infrared (for water and alignment) and the masks."""

    nir: np.ndarray          # float32 (h, w), reflectance x 10000
    swir: np.ndarray
    valid: np.ndarray        # bool (h, w)
    cloud: np.ndarray        # bool (h, w)
    rgb_refl: np.ndarray | None = None  # float32 (3, h, w)
    requests: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def empty(cls, h: int, w: int, with_rgb: bool = False) -> "Mosaic":
        z = lambda: np.zeros((h, w), np.float32)
        return cls(z(), z(), np.zeros((h, w), bool), np.zeros((h, w), bool),
                   np.zeros((3, h, w), np.float32) if with_rgb else None)

    @property
    def clear(self) -> np.ndarray:
        return self.valid & ~self.cloud

    @property
    def water(self) -> np.ndarray:
        return self.clear & (self.nir < WATER_REFL) & (self.swir < WATER_REFL)

    def rgb(self) -> np.ndarray:
        x = tone(self.rgb_refl / 10000)
        out = (np.moveaxis(x, 0, -1) * 255 + 0.5).astype(np.uint8)
        out[~self.valid] = 0
        return out

    def save(self, path: Path) -> None:
        q = lambda a: np.round(a).clip(0, 65535).astype(np.uint16)
        np.savez_compressed(path, nir=q(self.nir), swir=q(self.swir), valid=self.valid, cloud=self.cloud)

    @classmethod
    def load(cls, path: Path) -> "Mosaic":
        z = np.load(path)
        if "bands" in z:  # the first passes kept all five bands (blue, green, red, nir, swir)
            b = z["bands"]
            return cls(b[3].astype(np.float32), b[4].astype(np.float32), z["valid"], z["cloud"])
        return cls(z["nir"].astype(np.float32), z["swir"].astype(np.float32), z["valid"], z["cloud"])


def need_mask(grid: Grid, georef: dict[str, Any], until_m: float | None = None, cell: int = 16) -> np.ndarray:
    """Which cells (cell x cell pixels) of the grid are within the corridor's strip of its line (or of its first
    `until_m` metres). Without a strip, the whole grid."""
    h, w = math.ceil(grid.height / cell), math.ceil(grid.width / cell)
    strip = georef.get("strip_m")
    if not strip and until_m is None:
        return np.ones((h, w), bool)
    strip = strip or max(grid.width, grid.height) * grid.m_per_px
    pts = [(lon, lat) for along, lon, lat, _ in georef["camera"]["samples"] if until_m is None or along <= until_m]
    m = np.zeros((h, w), np.uint8)
    for lon, lat in pts:
        c, r = grid.to_px(lon, lat)
        cv2.circle(m, (int(c / cell), int(r / cell)), int(math.ceil(strip / grid.m_per_px / cell)) + 1, 1, -1)
    return m.astype(bool)


def tiles(grid: Grid, georef: dict[str, Any], until_m: float | None = None) -> list[tuple[slice, slice]]:
    """The grid's tiles that the corridor needs (row-major)."""
    cell = 16
    need = need_mask(grid, georef, until_m, cell)
    out = []
    for r0 in range(0, grid.height, TILE):
        for c0 in range(0, grid.width, TILE):
            if need[r0 // cell:math.ceil(min(grid.height, r0 + TILE) / cell), c0 // cell:math.ceil(min(grid.width, c0 + TILE) / cell)].any():
                out.append((slice(r0, min(grid.height, r0 + TILE)), slice(c0, min(grid.width, c0 + TILE))))
    return out


def _pieces(grid: Grid, rows: slice, cols: slice) -> list[tuple[slice, slice, tuple[float, float, float, float]]]:
    """A tile in pieces of at most MAX_CROP_PX a side: (rows, cols within the tile, box on the pieces' pixel edges)."""
    out = []
    for r0 in range(rows.start, rows.stop, MAX_CROP_PX):
        r1 = min(rows.stop, r0 + MAX_CROP_PX)
        for c0 in range(cols.start, cols.stop, MAX_CROP_PX):
            c1 = min(cols.stop, c0 + MAX_CROP_PX)
            w, n = grid.to_lonlat(c0, r0)
            e, s = grid.to_lonlat(c1, r1)
            out.append((slice(r0 - rows.start, r1 - rows.start), slice(c0 - cols.start, c1 - cols.start), (w, s, e, n)))
    return out


def _overlaps(a: tuple[float, ...], b: tuple[float, ...]) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def fetch(sensor: Sensor, items: list[dict[str, Any]], grid: Grid, http: httpx.Client,
          rows: slice | None = None, cols: slice | None = None) -> Mosaic:
    """One tile of the pass (the whole grid by default)."""
    rows, cols = rows or slice(0, grid.height), cols or slice(0, grid.width)
    m = Mosaic.empty(rows.stop - rows.start, cols.stop - cols.start, with_rgb=True)
    for item in items:
        for pr, pc, box in _pieces(grid, rows, cols):
            if item.get("bbox") and not _overlaps(tuple(item["bbox"]), box):
                continue
            ph, pw = pr.stop - pr.start, pc.stop - pc.start
            log.info("Cropping %s (%d×%d px at row %d, column %d)", item["id"], pw, ph, rows.start + pr.start, cols.start + pc.start)
            arr, rec = crop(sensor, item["id"], sensor.bands, box, pw, ph, "bilinear", http)
            qa, rec_qa = crop(sensor, item["id"], (sensor.mask_asset,), box, pw, ph, "nearest", http)
            m.requests += [rec, rec_qa]
            ok = (arr[-1] > 0) & (qa[-1] > 0) & ~m.valid[pr, pc]
            if sensor.name == "sentinel-2":
                ok &= qa[0] > 0  # scene classification 0: no data
            if not ok.any():
                continue
            refl = sensor.reflectance(arr[:-1], item["properties"])
            for b, dst in ((2, 0), (1, 1), (0, 2)):  # red, green, blue
                m.rgb_refl[dst, pr, pc][ok] = refl[b][ok]
            m.nir[pr, pc][ok] = refl[3][ok]
            m.swir[pr, pc][ok] = refl[4][ok]
            m.cloud[pr, pc][ok] = sensor.clouds(qa[0])[ok]
            m.valid[pr, pc] |= ok
    return m


def _detail(nir: np.ndarray, use: np.ndarray) -> np.ndarray:
    """Fine detail of the near infrared (the band minus its blur: signed, so its phase is kept), on clear land only,
    a few pixels in from any water or cloud edge (a shoreline that moved between the dates must not pull the match)."""
    hp = nir - cv2.GaussianBlur(nir, (0, 0), 4.0)
    inner = cv2.erode(use.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
    hp = np.where(inner, hp, 0).astype(np.float32)
    return cv2.GaussianBlur(hp, (0, 0), 0.7)


def coregister(ref: Mosaic | None, m: Mosaic, grid: Grid, reference_pass: str | None) -> Alignment:
    """Shift `m` onto `ref` (in place; the same piece of the grid) when the match is clear and small; recorded either way."""
    method = "phase_correlation_nir_detail_on_clear_land"
    if ref is None:
        return Alignment(reference_pass=None, provenance=Provenance(
            method="reference", evidence="The corridor's first pass: the others are laid on it."))
    use = ref.clear & m.clear & ~ref.water & ~m.water
    if use.mean() < 0.05:
        return Alignment(reference_pass=reference_pass, provenance=Provenance(
            method=method, evidence=f"Too little clear land in common ({use.mean():.0%}) to compare: not shifted."))
    h, w = m.nir.shape
    a, b = _detail(ref.nir, use), _detail(m.nir, use)
    (dx, dy), resp = cv2.phaseCorrelate(a, b, cv2.createHanningWindow((w, h), cv2.CV_32F))
    ok = resp >= MIN_RESPONSE and max(abs(dx), abs(dy)) <= MAX_SHIFT_PX
    if ok:  # phase correlation finds the shift; ECC measures it to a fraction of a pixel
        warp = np.float32([[1, 0, dx], [0, 1, dy]])
        try:
            _, warp = cv2.findTransformECC(a, b, warp, cv2.MOTION_TRANSLATION,
                                           (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 100, 1e-5),
                                           (a != 0).astype(np.uint8), 1)
            if max(abs(warp[0, 2] - dx), abs(warp[1, 2] - dy)) <= 1:
                dx, dy = float(warp[0, 2]), float(warp[1, 2])
                method += "_ecc_refined"
        except cv2.error:
            pass
    if ok and max(abs(dx), abs(dy)) >= 0.05:
        M = np.float32([[1, 0, -dx], [0, 1, -dy]])
        shift = lambda a_, flags: cv2.warpAffine(a_, M, (w, h), flags=flags)
        m.nir, m.swir = shift(m.nir, cv2.INTER_LINEAR), shift(m.swir, cv2.INTER_LINEAR)
        if m.rgb_refl is not None:
            m.rgb_refl = np.stack([shift(x, cv2.INTER_LINEAR) for x in m.rgb_refl])
        m.valid = shift(m.valid.astype(np.uint8), cv2.INTER_NEAREST).astype(bool)
        m.cloud = shift(m.cloud.astype(np.uint8), cv2.INTER_NEAREST).astype(bool)
    why = (f"{'Shifted' if ok else 'Not shifted'}: the pass sat {dx * grid.m_per_px:+.1f} m east, {-dy * grid.m_per_px:+.1f} m "
           f"north of the reference (peak {resp:.2f}; applied only if at least {MIN_RESPONSE} and at most "
           f"{MAX_SHIFT_PX * grid.m_per_px:g} m), compared on {use.mean():.0%} of the tile (clear land in both).")
    return Alignment(reference_pass=reference_pass, dx_m=round(-dx * grid.m_per_px, 2), dy_m=round(dy * grid.m_per_px, 2),
                     response=round(float(resp), 3), applied=bool(ok), provenance=Provenance(method=method, evidence=why))


class TileSet:
    """A stored pass read back by region: its tiles (or, for the first passes, its one whole-grid image), decoded on
    demand and kept for a while (`keep` tiles)."""

    def __init__(self, root: Path, files: PassFiles, grid: Grid, keep: int = 8):
        self.root, self.grid, self.keep = Path(root), grid, keep
        self.tiles = list(files.tiles) or [TileFile(rows=(0, grid.height), cols=(0, grid.width), visual=files.visual, bands=files.bands)]
        self._cache: OrderedDict[tuple[str, int], Any] = OrderedDict()

    def _read(self, kind: str, k: int):
        key = (kind, k)
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        t = self.tiles[k]
        v = (cv2.cvtColor(cv2.imread(str(self.root / t.visual)), cv2.COLOR_BGR2RGB) if kind == "rgb"
             else Mosaic.load(self.root / t.bands))
        self._cache[key] = v
        while len(self._cache) > self.keep:
            self._cache.popitem(last=False)
        return v

    def _parts(self, rows: slice, cols: slice):
        for k, t in enumerate(self.tiles):
            r0, r1 = max(rows.start, t.rows[0]), min(rows.stop, t.rows[1])
            c0, c1 = max(cols.start, t.cols[0]), min(cols.stop, t.cols[1])
            if r0 < r1 and c0 < c1:
                yield k, (slice(r0 - rows.start, r1 - rows.start), slice(c0 - cols.start, c1 - cols.start)), \
                    (slice(r0 - t.rows[0], r1 - t.rows[0]), slice(c0 - t.cols[0], c1 - t.cols[0]))

    def rgb(self, rows: slice, cols: slice) -> np.ndarray:
        out = np.zeros((rows.stop - rows.start, cols.stop - cols.start, 3), np.uint8)
        for k, dst, src in self._parts(rows, cols):
            out[dst] = self._read("rgb", k)[src]
        return out

    def mosaic(self, rows: slice, cols: slice) -> Mosaic:
        out = Mosaic.empty(rows.stop - rows.start, cols.stop - cols.start)
        for k, dst, src in self._parts(rows, cols):
            m = self._read("bands", k)
            for name in ("nir", "swir", "valid", "cloud"):
                getattr(out, name)[dst] = getattr(m, name)[src]
        return out

    def overview(self, max_px: int = OVERVIEW_PX) -> tuple[np.ndarray, np.ndarray, int]:
        """The whole grid, scaled down by a whole factor to at most max_px a side: (rgb, valid, factor)."""
        f = max(1, math.ceil(max(self.grid.width, self.grid.height) / max_px))
        h, w = math.ceil(self.grid.height / f), math.ceil(self.grid.width / f)
        rgb, valid = np.zeros((h, w, 3), np.uint8), np.zeros((h, w), bool)
        for k, t in enumerate(self.tiles):
            th, tw = math.ceil((t.rows[1] - t.rows[0]) / f), math.ceil((t.cols[1] - t.cols[0]) / f)
            r0, c0 = t.rows[0] // f, t.cols[0] // f
            src = self._read("rgb", k)
            small = src if f == 1 else cv2.resize(src, (tw, th), interpolation=cv2.INTER_AREA)
            ok = self._read("bands", k).valid
            ok = ok if f == 1 else cv2.resize(ok.astype(np.uint8), (tw, th), interpolation=cv2.INTER_NEAREST).astype(bool)
            rgb[r0:r0 + th, c0:c0 + tw] = small[:h - r0, :w - c0]
            valid[r0:r0 + th, c0:c0 + tw] = ok[:h - r0, :w - c0]
        return rgb, valid, f


def _share(mask: np.ndarray, within: np.ndarray) -> float:
    n = int(within.sum())
    return round(float((mask & within).sum()) / n, 4) if n else 0.0


def chip_boxes(grid: Grid, georef: dict[str, Any]) -> list[tuple[int, float, slice, slice]]:
    """(station, along_m, rows, cols): a square around each station, moved inside the grid where it would cross its edge."""
    out = []
    size = int(round(georef["chip_size_m"] / grid.m_per_px))
    for st in georef["stations"]:
        c, r = grid.to_px(st["lon"], st["lat"])
        c0 = int(min(max(0, round(c - size / 2)), max(0, grid.width - size)))
        r0 = int(min(max(0, round(r - size / 2)), max(0, grid.height - size)))
        out.append((st["station"], st["along_m"], slice(r0, min(grid.height, r0 + size)), slice(c0, min(grid.width, c0 + size))))
    return out


def _chip(georef, pass_id, item_ids, acquired, station, along, kind, px, rows, cols, grid, factor, derived, pass_dir, rel):
    cid = chip_id_for(georef["corridor_id"], pass_id, station)
    web, thumb = pass_dir / "chips" / "web" / f"{cid}.webp", pass_dir / "chips" / "thumb" / f"{cid}.webp"
    write_derivative(px, web, WEB_PX, 90)
    write_derivative(px, thumb, THUMB_PX, 82)
    w_, n_ = grid.to_lonlat(cols.start, rows.start)
    e_, s_ = grid.to_lonlat(cols.stop, rows.stop)
    return SatelliteChip(
        chip_id=cid,
        source=ChipLink(pass_id=pass_id, corridor_id=georef["corridor_id"], item_ids=item_ids, acquired_at=acquired,
                        station=station, along_m=along),
        chip=ChipCore(kind=kind, centre_lat=round((n_ + s_) / 2, 7), centre_lon=round((w_ + e_) / 2, 7),
                      bbox=(round(w_, 7), round(s_, 7), round(e_, 7), round(n_, 7)),
                      size_m=(round((cols.stop - cols.start) * grid.m_per_px), round((rows.stop - rows.start) * grid.m_per_px)),
                      m_per_px=grid.m_per_px * factor, width=px.shape[1], height=px.shape[0],
                      sha256=hashlib.sha256(np.ascontiguousarray(px).tobytes()).hexdigest(),
                      files=FrameFiles(web=rel(web), thumb=rel(thumb))),
        derived=derived)


WATER_NOTE = (f"Water: clear pixels with NIR and SWIR reflectance under {WATER_REFL / 100:g}%. "
              "Cloud: the product's own mask (scene classification / pixel QA).")


def cut_chips(ts: TileSet, grid: Grid, georef: dict[str, Any], pass_id: str, item_ids: tuple[str, ...], acquired,
              pass_dir: Path, rel, totals: dict[str, int], min_valid: float = 0.5) -> list[SatelliteChip]:
    """The whole corridor (scaled down when large) and a square at each station the pass covers; exposure is filled
    in later (`exposure`). `totals`: the pass's pixel counts (valid, cloud, clear, water) for the overview's shares."""
    for d in ("web", "thumb", "meta"):
        (pass_dir / "chips" / d).mkdir(parents=True, exist_ok=True)
    rgb, valid, f = ts.overview()
    full = (slice(0, grid.height), slice(0, grid.width))
    prov = Provenance(method="reflectance_thresholds", evidence=WATER_NOTE)
    out = [_chip(georef, pass_id, item_ids, acquired, 0, 0.0, "overview", rgb, *full, grid, f, ChipDerived(
        valid_share=round(float(valid.mean()), 4),
        cloud_share=round(totals["cloud"] / max(1, totals["valid"]), 4),
        water_share=round(totals["water"] / max(1, totals["clear"]), 4), provenance=prov), pass_dir, rel)]
    for station, along, rows, cols in chip_boxes(grid, georef):
        m = ts.mosaic(rows, cols)
        if m.valid.mean() < min_valid:  # a pass fetched for part of the line has no chip where it has no data
            continue
        out.append(_chip(georef, pass_id, item_ids, acquired, station, along, "station", ts.rgb(rows, cols), rows, cols, grid, 1,
                         ChipDerived(valid_share=round(float(m.valid.mean()), 4), cloud_share=_share(m.cloud, m.valid),
                                     water_share=_share(m.water, m.clear), provenance=prov), pass_dir, rel))
    return out


def exposure(before: TileSet, before_id: str, now: TileSet, chip: SatelliteChip, grid: Grid) -> None:
    """Share of the chip's clear pixels that were open water in `before` and are not now (the exposed bed). The
    whole corridor is counted tile by tile (it may be far larger than memory likes)."""
    whole = chip.chip.kind == "overview"
    regions = [(slice(*t.rows), slice(*t.cols)) for t in now.tiles] if whole else [_chip_slices(grid, chip)]
    exposed = both = seen = 0
    for rows, cols in regions:
        b, n = before.mosaic(rows, cols), now.mosaic(rows, cols)
        common = b.clear & n.clear
        exposed += int((b.water & ~n.water & common).sum())
        both += int(common.sum())
        seen += int(n.clear.sum())
    # the earlier pass must cover most of what this one shows clearly (a pass fetched only for the line's start
    # says nothing about the whole corridor)
    if both < (0.8 if whole else 0.5) * max(1, seen):
        chip.derived.exposed_bed_share = chip.derived.exposed_against = None
        return
    chip.derived.exposed_bed_share = round(exposed / both, 4)
    chip.derived.exposed_against = before_id


def _chip_slices(grid: Grid, chip: SatelliteChip) -> tuple[slice, slice]:
    c0, r0 = grid.to_px(chip.chip.bbox[0], chip.chip.bbox[3])
    c1, r1 = grid.to_px(chip.chip.bbox[2], chip.chip.bbox[1])
    return slice(int(round(r0)), int(round(r1))), slice(int(round(c0)), int(round(c1)))
