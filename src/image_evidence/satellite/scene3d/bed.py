"""Pass 3, the bed (the user, 26 October 2026: "build the bed's shape ... realistic water level drop, and exposed
powerline foundations"): the drained reservoir's floor round the crossing, and the water's fall over it.

No open elevation model of the drained bed exists (searched 26 October 2026: docs/crossing-3d-plan.txt). It is built
here from what was observed, each part said for what it is:
- The reservoir's footprint: the water on the last clear pass before the dam was destroyed (5 June 2023), the one
  body of water that holds the crossing (the plant's cooling pond and the lakes behind dikes are not part of it).
- Shorelines (the waterline method): every clear optical pass of the weeks after (Sentinel-2, Landsat 8/9) and the
  calm radar passes of the first days (Sentinel-1, where open water is far darker than the wet bed) say where the
  water still was at that moment; the reported water level at that moment (the config's dated, sourced `levels`)
  makes each shoreline a contour. A point first seen dry between two passes lies between their two levels, placed
  between them by how far it is from the ground that dried before it and the ground that dried after (`surface`).
- Only water joined to the river stands at the reported level: pools cut off from it (the old floodplain's lakes)
  keep their own, unknown level, so there the pass counts as unseen (`water_of`).
- Where the water never left (the river's channels and the pools), below the last level, a bank sloping in at
  CHANNEL_SLOPE down to CHANNEL_DEPTH_M: inferred, under the water in every frame.
- Checked against ICESat-2's measured ground heights on the bed (August 2023, the `icesat2` points): the residuals
  are in bed.json.
- The pre-1956 map (`old_map`): the floodplain's channels and spot heights before the reservoir, which the bed still
  carries (Rybak & Dubis 2023: its microrelief largely unchanged after 68 years under water).

Heights are metres above the EGM2008 geoid, FABDEM's datum; the gauges' Baltic heights are taken as the same (the
difference here is under a metre, unmeasured: said in the doc). Everything out of the footprint stays FABDEM's.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import cv2
import httpx
import numpy as np
from PIL import Image

from ...layout import write_json
from .. import providers
from ..corridor import Grid
from ..network import _layer
from ..stitch import _pieces, fetch as fetch_tile

log = logging.getLogger(__name__)

POINT_REACH_M = 700.0    # a measured height pulls the bed round it this far (a Gaussian's sigma), within its band
STILL_WET = (15, 0.6, 4)  # wet in this share of its last passes (of at least this many seen): still under the water
CHANNEL_SLOPE = 0.05      # m down per m out from the last shore, where the water never left (inferred)
CHANNEL_DEPTH_M = 4.0     # and no deeper than this below the last level
MNDWI_MIN = 0.2           # water: (green - SWIR) / (green + SWIR) over this (Xu 2006), and
WATER_NIR_MAX = 1500      # NIR under 15%: turbid floodwater stays bright in green and NIR but dark in SWIR; wet mud
                          # is dark in green too, so its MNDWI stays low
WATER_RULE = (f"water: clear pixels with MNDWI over {MNDWI_MIN} (green against SWIR) and NIR reflectance under "
              f"{WATER_NIR_MAX / 100:g}%")
RADAR_MEDIAN_PX = 5       # the radar's speckle: a median over this many pixels before it is read
STRUCTURE_M = 45.0        # round each crossing tower in the reservoir: its caisson (30-44 m across) and the sand heaped
                          # on it, which the passes see as dry ground from the start; not the bed, so left unseen there
LATE_MARGIN_M = (0.3, 0.1)  # on the later passes (`observe.also`) water joined to the river lies this far under their
                          # level, and open ground this far over it


def _t(v: Any) -> datetime:
    d = v if isinstance(v, datetime) else datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def level(series: list[dict[str, Any]], when: Any) -> float:
    """The water level (m) at a moment: the reports linearly between them, held before the first and after the last."""
    ts = np.array([_t(p["at"]).timestamp() for p in series])
    ms = np.array([float(p["m"]) for p in series])
    o = np.argsort(ts)
    return float(np.interp(_t(when).timestamp(), ts[o], ms[o]))


def series(b: dict[str, Any], d: Path) -> list[dict[str, Any]]:
    """The water level at the crossing over time (m above EGM2008): the config's dated reports, Baltic heights raised
    by `baltic_m`, then each month's median of SWOT's river reaches either side, interpolated to the crossing by
    longitude (`swot`). Each point keeps its source."""
    out = [p | {"m": round(float(p["m"]) + (float(b.get("baltic_m", 0)) if p.get("datum") == "baltic" else 0), 2)}
           for p in b["levels"]]
    sw = b.get("swot")
    if sw:
        reach = {str(k): float(v) for k, v in sw["reaches"].items()}
        months = _swot_months(d / sw["file"], reach)
        (a, la), (c, lc) = sorted(reach.items(), key=lambda kv: kv[1])
        t = (float(sw["at_lon"]) - la) / (lc - la)
        for mo, by in sorted(months.items()):
            if mo < str(sw["from"])[:7] or a not in by or c not in by:
                continue
            m = (1 - t) * float(np.median(by[a])) + t * float(np.median(by[c]))
            out.append({"at": f"{mo}-15T12:00:00Z", "m": round(m, 2), "place": "the crossing",
                        "source": sw["source"], "passes": len(by[a]) + len(by[c])})
    return sorted(out, key=lambda p: _t(p["at"]))


def _swot_months(path: Path, reach: dict[str, float]) -> dict[str, dict[str, list[float]]]:
    """SWOT's river heights by month and reach (each pass once: the file lists it under two processing versions)."""
    import csv
    from collections import defaultdict
    months: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    seen = set()
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            key = (r["reach_id"], r["time_utc"][:16])
            if r["reach_id"] not in reach or key in seen or not r["wse_m_EGM2008"]:
                continue
            seen.add(key)
            v = float(r["wse_m_EGM2008"])
            if -50 < v < 50:
                months[r["time_utc"][:7]][r["reach_id"]].append(v)
    return months


def slope(b: dict[str, Any], d: Path) -> float:
    """How the river's surface rises eastward, upstream (m per degree of longitude): a line through the median of
    each of SWOT's reaches over `swot.slope.months` (0 without it)."""
    sl = (b.get("swot") or {}).get("slope")
    if not sl:
        return 0.0
    reach = {str(k): float(v) for k, v in sl["reaches"].items()}
    lo, hi = (str(m) for m in sl["months"])
    per: dict[str, list[float]] = {r: [] for r in reach}
    for mo, by in _swot_months(d / b["swot"]["file"], reach).items():
        if lo <= mo <= hi:
            for r, v in by.items():
                per[r] += v
    xs = [reach[r] for r in reach if per[r]]
    return float(np.polyfit(xs, [float(np.median(per[r])) for r in reach if per[r]], 1)[0])


def tilt(lv: float, full: float, settled: float) -> float:
    """How far the river's slope has formed at a level (0..1): none while the reservoir is full and flat, all of it
    once the level has settled (inferred: in between, as far as the level has fallen)."""
    return float(np.clip((full - lv) / max(full - settled, 1e-6), 0.0, 1.0))


def bed_dir(base: Path) -> Path:
    return base / "bed"


def grid(root: Path, cfg: dict[str, Any]) -> Grid:
    """The bed's grid: its box (`grid_of`, a layer's: the reservoir round the crossing; else the land texture's) at
    the bed's pixel size."""
    c3 = cfg["crossing3d"]
    tex = _layer(root, cfg, c3["bed"].get("grid_of") or c3["texture"], None)
    return Grid(bbox=tuple(tex["grid"]["bbox"]), m_per_px=float(cfg["crossing3d"]["bed"]["m_per_px"]))


# ------------------------------------------------------------------ observations


def observe(root: Path, cfg: dict[str, Any], base: Path, http: httpx.Client | None = None) -> list[dict[str, Any]]:
    """Every pass the bed is read from, fetched once onto the bed's grid (obs/<id>.npz: water, known, and the
    radar's backscatter), with its items, time and what share of the box it saw."""
    b = cfg["crossing3d"]["bed"]
    g = grid(root, cfg)
    out = bed_dir(base) / "obs"
    out.mkdir(parents=True, exist_ok=True)
    o = b["observe"]
    from datetime import date
    start, end = date.fromisoformat(str(o["start"])), date.fromisoformat(str(o["end"]))
    # and the later days whose water is drawn as seen (`also`: the texture layers' passes), never read as shorelines
    spans = [(start, end, ("sentinel-2", "landsat"))] + [(date.fromisoformat(str(a)), date.fromisoformat(str(a)),
                                                          ("sentinel-2",)) for a in o.get("also", [])]
    with (http or httpx.Client(timeout=120)) as c:
        for s, sen, start, end in ((s, providers.SENSORS[s], a, e) for a, e, ss in spans for s in ss):
            for grp in providers.overpasses(providers.search(sen, g.bbox, start, end, float(o["max_cloud"]), c)):
                if grp[0]["properties"].get("platform") in o.get("skip_platforms", []):
                    continue
                when = providers.acquired(grp[0])
                f = out / f"{s}_{when:%Y%m%dT%H%M%S}.npz"
                if f.exists():
                    continue
                m = fetch_tile(sen, grp, g, c, piece_px=1000)
                q = lambda x: np.clip(np.nan_to_num(x), -32000, 32000).astype(np.int16)   # reflectance x 10000
                np.savez_compressed(f, green=q(m.rgb_refl[1]), nir=q(m.nir), swir=q(m.swir), known=m.clear,
                                    rgb=m.rgb())
                write_json(f.with_suffix(".json"), {"sensor": sen.label, "kind": "optical", "acquired": when.isoformat(),
                                                    "items": [i["id"] for i in grp], "seen": round(float(m.clear.mean()), 4),
                                                    "rule": WATER_RULE})
        s1 = SimpleNamespace(collection="sentinel-1-rtc")
        for item in o.get("radar", []):
            f = out / f"sentinel-1_{item['at'].replace('-', '').replace(':', '')}.npz"
            if f.exists():
                continue
            vv = np.zeros((g.height, g.width), np.float32)
            vh, ok = vv.copy(), np.zeros(vv.shape, bool)
            for pr, pc, box in _pieces(g, slice(0, g.height), slice(0, g.width), 1000):
                arr, _ = providers.crop(s1, item["id"], ("vv", "vh"), box, pc.stop - pc.start, pr.stop - pr.start,
                                        "bilinear", c)
                vv[pr, pc], vh[pr, pc], ok[pr, pc] = arr[0], arr[1], arr[2] > 0
            db = lambda x: (10 * np.log10(np.clip(x, 1e-5, None))).astype(np.float16)
            np.savez_compressed(f, vh_db=db(vh), vv_db=db(vv), known=ok)
            write_json(f.with_suffix(".json"), {"sensor": "Sentinel-1 RTC", "kind": "radar", "acquired": item["at"],
                                                "items": [item["id"]], "seen": round(float(ok.mean()), 4),
                                                "why": item.get("why"),
                                                "rule": "water: VH backscatter (median of 5x5) under the pass's own "
                                                        "split between water and bed inside the footprint (Otsu)"})
    return sorted((json.loads(p.read_text()) | {"file": p.with_suffix(".npz").name}
                   for p in out.glob("*.json")), key=lambda d: _t(d["acquired"]))


def _otsu(v: np.ndarray, lo: float = -32.0, hi: float = -8.0) -> float:
    h, e = np.histogram(v, bins=240, range=(lo, hi))
    c, p = (e[:-1] + e[1:]) / 2, h / max(h.sum(), 1)
    w0 = np.cumsum(p)
    m = np.cumsum(p * c)
    with np.errstate(divide="ignore", invalid="ignore"):
        between = (m[-1] * w0 - m) ** 2 / (w0 * (1 - w0))
    return float(c[np.nanargmax(between)])


def water_of(base: Path, ob: dict[str, Any], footprint: np.ndarray | None,
             rule: dict[str, Any] | None = None) -> tuple[np.ndarray, np.ndarray]:
    """(water, known) of one observation. After the breach (a footprint given) only the water joined to the river (a
    body reaching the box's east or west edge, joined across what the pass didn't see) stands at the reported level: a pool cut off from it keeps
    its own level, unknown, so it counts as unseen there, never as wet. A pass may have its own `rule` (the config's
    `observe.rules`: silt-laden floodwater, bright in NIR, is told from the sand by SWIR instead)."""
    z = np.load(bed_dir(base) / "obs" / ob["file"])
    if ob["kind"] == "optical":
        g, nir, sw = (z[b].astype(np.float32) for b in ("green", "nir", "swir"))
        mndwi = (g - sw) / np.maximum(g + sw, 1.0)
        known = z["known"]
        if rule:
            water = known & (mndwi > float(rule["mndwi_min"])) & (sw < float(rule["swir_max"]))
            ob["rule"] = rule["why"]
        else:
            water = known & (mndwi > MNDWI_MIN) & (nir < WATER_NIR_MAX)
    else:
        vh = cv2.medianBlur(z["vh_db"].astype(np.float32), RADAR_MEDIAN_PX)
        known = z["known"]
        thr = _otsu(vh[known & footprint]) if footprint is not None else -23.0
        ob["threshold_db"] = round(thr, 2)
        water = (vh < thr) & known
    if footprint is None:
        return water, known
    reach = (water | ~known) & footprint
    _, lab = cv2.connectedComponents(reach.astype(np.uint8), connectivity=8)
    ends = np.unique(np.concatenate([lab[:, 0], lab[:, -1]]))   # the river runs through the box, east to west
    river = np.isin(lab, ends[ends > 0])
    pools = water & ~river
    ob["pools_share"] = round(float(pools.sum() / max(footprint.sum(), 1)), 4)
    return water & river, known & ~pools


# ------------------------------------------------------------------ the surface


def structures(base: Path, g: Grid, fp: np.ndarray) -> np.ndarray:
    """The crossing towers standing in the reservoir (the survey's OSM nodes tagged tower:type=crossing inside the
    footprint), each a disc of STRUCTURE_M on the bed's grid."""
    sv = json.loads((base / "survey.json").read_text())
    out = np.zeros(fp.shape, np.uint8)
    r = max(1, int(round(STRUCTURE_M / g.m_per_px)))
    for ln in sv["lines"]:
        for v in ln["vertices"]:
            if v["tower"] and v["tower"]["tags"].get("tower:type") == "crossing":
                c, rr = g.to_px(*v["lonlat"])
                if 0 <= int(rr) < fp.shape[0] and 0 <= int(c) < fp.shape[1] and fp[int(rr), int(c)]:
                    cv2.circle(out, (int(c), int(rr)), r, 1, -1)
    return out.astype(bool)


def _fill(z: np.ndarray, hole: np.ndarray, ring_px: int = 3) -> np.ndarray:
    """z inside each hole (a caisson's disc) at the median of the ring of bed round it, `ring_px` wide."""
    out = z.copy()
    n, lab = cv2.connectedComponents(hole.astype(np.uint8), connectivity=8)
    k = np.ones((2 * ring_px + 1, 2 * ring_px + 1), np.uint8)
    for i in range(1, n):
        h = lab == i
        ring = cv2.dilate(h.astype(np.uint8), k).astype(bool) & ~hole & np.isfinite(z)
        if ring.any():
            out[h] = np.median(z[ring])
    return out


def footprint(water: np.ndarray, known: np.ndarray) -> np.ndarray:
    """The reservoir on the reference pass: its largest body of water, gaps under 5 px closed (towers, boats)."""
    w = (water & known).astype(np.uint8)
    w = cv2.morphologyEx(w, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(w, connectivity=4)
    return lab == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))


def emergence(wet: np.ndarray, known: np.ndarray) -> np.ndarray:
    """For each pixel the first observation from which it is dry, fitted as one step (wet, then dry for good) that
    disagrees with the fewest of its observations: 0 dry from the first, n never dry. wet, known: (n, h, w)."""
    n = len(wet)
    dry_before = np.concatenate([np.zeros((1,) + wet.shape[1:], np.int16),
                                 np.cumsum(known & ~wet, axis=0, dtype=np.int16)])   # dry seen before k
    wet_from = np.concatenate([np.cumsum((known & wet)[::-1], axis=0, dtype=np.int16)[::-1],
                               np.zeros((1,) + wet.shape[1:], np.int16)])            # wet seen from k on
    cost = dry_before + wet_from   # (n + 1, h, w)
    return np.argmin(cost, axis=0).astype(np.int16)  # ties: the earliest


def surface(k: np.ndarray, inside: np.ndarray, levels: list[float], full: float, m_per_px: float) -> np.ndarray:
    """Heights inside the footprint from each pixel's step `k` and the levels at the observations: between the level
    when it was last wet and when first dry, by its distance to the ground that dried before it and after it; where
    it never dried, a bank sloping under the last level."""
    n = len(levels)
    lv = [np.broadcast_to(np.asarray(x, np.float32), k.shape) for x in levels]   # a level may vary across the box
    up = [np.broadcast_to(np.float32(full), k.shape)] + lv     # level when last wet, by k
    z = np.full(k.shape, np.nan, np.float32)

    def dist(mask):
        return cv2.distanceTransform((~mask).astype(np.uint8), cv2.DIST_L2, 5) * m_per_px

    for j in np.unique(k[inside]):
        sel = inside & (k == j)
        higher = ~inside | (k < j)
        if j == n:   # never dry: under the last level
            z[sel] = lv[-1][sel] - np.minimum(CHANNEL_DEPTH_M, CHANNEL_SLOPE * dist(higher)[sel])
            continue
        lower = inside & (k > j)
        d_hi, d_lo = dist(higher)[sel], dist(lower)[sel] if lower.any() else np.full(sel.sum(), 1e6)
        z[sel] = lv[j][sel] + (up[j][sel] - lv[j][sel]) * d_lo / np.maximum(d_hi + d_lo, 1e-6)
    return z


def constrain(z: np.ndarray, k: np.ndarray, inside: np.ndarray, levels: list[float], full: float,
              points: list[tuple[float, float, float, float]], m_per_px: float) -> tuple[np.ndarray, list[dict]]:
    """Measured heights (row, col, height, weight) move the bed round them toward themselves, smoothly (POINT_REACH_M),
    but never out of what the shorelines say each pixel is: between the level when it was last wet and when first
    dry. Where it never dried, left as it is. Returns the bed and each point's use."""
    n = len(levels)
    lv = [np.broadcast_to(np.asarray(x, np.float32), k.shape) for x in levels]
    hi_k = np.full(k.shape, np.float32(full))
    lo_k = np.full(k.shape, -np.inf, np.float32)
    for j in range(n):   # each pixel's band: the level when it was last wet, and when first dry
        sel = k == j
        lo_k[sel] = lv[j][sel]
        if j:
            hi_k[sel] = lv[j - 1][sel]
    num = np.zeros(z.shape, np.float32)
    den = np.zeros(z.shape, np.float32)
    used = []
    for r, c, h, w in points:
        ri, ci = int(r), int(c)
        if not (0 <= ri < z.shape[0] and 0 <= ci < z.shape[1]) or not inside[ri, ci] or k[ri, ci] == n:
            continue
        target = float(np.clip(h, lo_k[ri, ci], hi_k[ri, ci]))
        num[ri, ci] += w * (target - z[ri, ci])
        den[ri, ci] += w
        used.append({"row": ri, "col": ci, "height_m": round(h, 2), "band_m": [round(float(lo_k[ri, ci]), 2),
                     round(float(hi_k[ri, ci]), 2)], "bed_before_m": round(float(z[ri, ci]), 2)})
    if not used:
        return z, used
    sig = POINT_REACH_M / m_per_px
    nb, db = cv2.GaussianBlur(num, (0, 0), sig), cv2.GaussianBlur(den, (0, 0), sig)
    peak = cv2.GaussianBlur(np.pad(np.ones((1, 1), np.float32), 40), (0, 0), sig).max()   # one point's own weight
    shift = nb / np.maximum(db, 1e-12) * np.clip(db / peak, 0, 1)   # the mean pull, fading where no point is near
    out = np.where(inside & (k < n), np.clip(z + shift, lo_k, hi_k), z).astype(np.float32)
    for u in used:
        u["bed_after_m"] = round(float(out[u["row"], u["col"]]), 2)
    return out, used


def points_of(b: dict[str, Any], g: Grid, d: Path) -> list[tuple[float, float, float, float]]:
    """The measured heights the bed is held to: ICESat-2's ground on the drained bed (August 2023) and the 1941
    sheet's spot heights (before the reservoir: the bed's floodplain kept its relief), on the bed's grid."""
    out = []
    if b.get("icesat2"):
        src = b["icesat2"]
        for p in json.loads((d / src["file"]).read_text()):
            c, r = g.to_px(p["lon"], p["lat"])
            out.append((r, c, p["h_te_best_fit"] - float(src["geoid_m"]), float(src.get("weight", 1.0))))
    for m in b.get("old_maps", []):
        for p in m.get("spot_heights", []):
            c, r = g.to_px(*p["lonlat"])
            out.append((r, c, float(p["m"]), float(m.get("weight", 0.5))))
    return out


def build(root: Path, cfg: dict[str, Any], base: Path, http: httpx.Client | None = None) -> dict[str, Any]:
    """The bed (bed/bed.npz on the bed's grid: z, the footprint, each pixel's step) and its doc (bed/bed.json)."""
    from .export import heights   # FABDEM, sampled on the bed's grid

    b = cfg["crossing3d"]["bed"]
    g = grid(root, cfg)
    obs = observe(root, cfg, base, http)
    ref = next(o for o in obs if o["acquired"].startswith(str(b["reference"])))
    rw, rk = water_of(base, ref, None)
    fp = footprint(rw, rk)
    breach = _t(b["breach"])
    skip = {str(x["at"]): x["why"] for x in b["observe"].get("skip", [])}
    end = _t(b["observe"]["end"]) + timedelta(days=1)
    after = [o for o in obs if breach < _t(o["acquired"]) < end and o["seen"] >= float(b.get("min_seen", 0.2))
             and not any(o["acquired"].startswith(k) for k in skip)]
    lvls = series(b, bed_dir(base))
    settled = next(p for p in lvls if p.get("source", "").startswith("settled"))
    last_gauge = max((p for p in lvls if _t(p["at"]) < _t(settled["at"])), key=lambda p: _t(p["at"]))
    full = level(lvls, ref["acquired"])
    lv = np.minimum.accumulate([level(lvls, o["acquired"]) for o in after])   # the level only falls here
    # the river's slope along the box (SWOT), formed as far as the level has fallen: each pass's level by longitude
    s_deg = slope(b, bed_dir(base))
    w_, _, e_, _ = g.bbox
    lon = w_ + (np.arange(g.width) + 0.5) / g.width * (e_ - w_)
    at_lon = float(b["swot"]["at_lon"]) if b.get("swot") else float(lon.mean())
    lv_px = [x + s_deg * (lon - at_lon)[None, :] * tilt(x, full, float(lv[-1])) for x in lv]
    rules = {str(x["at"]): x for x in b["observe"].get("rules", [])}
    wet, known = zip(*(water_of(base, o, fp, next((r for k_, r in rules.items() if o["acquired"].startswith(k_)), None))
                       for o in after))
    struct = structures(base, g, fp)
    wet, known = np.stack(wet), np.stack(known) & fp[None] & ~struct[None]
    k = emergence(wet, known)
    # still under water at the end: wet in most of its last passes (a hazy pass that misses the river is not a drying)
    last, share, least = STILL_WET
    seen_late = known[-last:].sum(0)
    k[(seen_late >= least) & ((wet & known)[-last:].sum(0) >= share * np.maximum(seen_late, 1))] = len(after)
    z = surface(k, fp, lv_px, full, g.m_per_px)
    d = bed_dir(base)
    blind = _icesat2(b, g, z, fp, d)   # before the bed is held to them: an independent check of the waterline method
    z, used = constrain(z, k, fp, lv_px, full, points_of(b, g, d), g.m_per_px)
    z = _fill(z, struct & fp)   # under the caissons: the bed round them
    # the later passes (`observe.also`, after the shorelines' weeks): the river's water there lies under its level
    # then, the open ground over it (where the level only fell: the channels the river left, the ground it never
    # came back to); their water, the pools' too, kept for the scene (`seen_*`: drawn as seen on those days)
    late, seen = [], {}
    for day in b["observe"].get("also", []):
        o = max((o for o in obs if o["acquired"].startswith(str(day)) and o["kind"] == "optical"),
                key=lambda o: o["seen"], default=None)
        if o is None:
            continue
        river, kn = water_of(base, o, fp)
        allw, _ = water_of(base, o, None)
        seen[str(day)] = {"water": allw & fp, "river": river & fp, "known": kn & fp}
        if _t(o["acquired"]) < end:
            continue
        lt = level(lvls, o["acquired"])
        lt_px = (lt + s_deg * (lon - at_lon))[None, :].repeat(g.height, 0)
        dry = kn & ~river & ~(allw & fp) & fp & ~struct
        wet_r = river & kn & fp
        z = np.where(wet_r, np.minimum(z, lt_px - LATE_MARGIN_M[0]), z)
        z = np.where(dry, np.maximum(z, lt_px + LATE_MARGIN_M[1]), z)
        late.append({"acquired": o["acquired"], "items": o["items"], "level_m": round(lt, 2),
                     "river_px": int(wet_r.sum()), "dry_px": int(dry.sum()),
                     "lowered_px": int((wet_r & (z == lt_px - LATE_MARGIN_M[0])).sum()),
                     "raised_px": int((dry & (z == lt_px + LATE_MARGIN_M[1])).sum())})
    # smoothed a little inside the footprint (speckle, the step between bands); the land's edge left as it is
    zs = np.where(fp, z, 0).astype(np.float32)
    wsum = cv2.GaussianBlur(fp.astype(np.float32), (0, 0), 1.2)
    z = np.where(fp, cv2.GaussianBlur(zs, (0, 0), 1.2) / np.maximum(wsum, 1e-3), np.nan).astype(np.float32)
    rows, cols = np.mgrid[0:g.height, 0:g.width]
    w, s, e, n = g.bbox
    lon = w + (cols + 0.5) / g.width * (e - w)
    lat = n - (rows + 0.5) / g.height * (n - s)
    fab = heights(np.stack([lon.ravel(), lat.ravel()], 1)).reshape(g.height, g.width).astype(np.float32)
    check = _icesat2(b, g, z, fp, d)
    np.savez_compressed(d / "bed.npz", z=z, fabdem=fab, footprint=fp, k=k, bbox=np.array(g.bbox), m_per_px=g.m_per_px,
                        structures=struct, seen_days=np.array(list(seen)),
                        **{f"seen_{k_}_{day}": v[k_] for day, v in seen.items() for k_ in v})
    _preview(d, z, fab, fp)
    doc = {
        "made_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "grid": g.to_json(),
        "datum": f"metres above the EGM2008 geoid (FABDEM's, SWOT's); the gauges' Baltic heights raised by "
                 f"{b.get('baltic_m', 0)} m (inferred from altimetry against the gauge just before the breach)",
        "reference": {k_: ref[k_] for k_ in ("acquired", "items", "sensor")} | {"level_m": round(full, 2)},
        "breach": str(b["breach"]),
        "observations": [{k_: o.get(k_) for k_ in ("acquired", "sensor", "kind", "items", "seen", "threshold_db",
                                                    "pools_share", "rule", "why")}
                         | {"level_m": round(float(x), 2), "water_share": round(float((wi & fp).sum() / max(fp.sum(), 1)), 3)}
                         for o, x, wi in zip(after, lv, wet)],
        "left_out": [{"acquired": o["acquired"], "sensor": o["sensor"], "why": next(w for k, w in skip.items()
                                                                                if o["acquired"].startswith(k))}
                     for o in obs if any(o["acquired"].startswith(k) for k in skip)],
        "drawn": {"cap_m": round(float(lv[-1]), 2), "cap_from": last_gauge["at"], "cap_at": settled["at"],
                  "rule": "the water is drawn at the level reported, but once settled no higher than the lowest level "
                          "the bed was mapped at (the last pass's): the bed's floodplain is inferred too flat to hold "
                          "the river's seasonal rises, so those aren't drawn; its falls are. Between the last gauge "
                          "reading and the settling the cap eases down to it"},
        "levels": lvls,
        "river_slope": {"m_per_deg_lon": round(s_deg, 3), "at_lon": at_lon, "settled_m": round(float(lv[-1]), 2),
                        "rule": "the level reported at the crossing, plus SWOT's slope along the river by longitude, "
                                "formed as far as the level has fallen from full to settled (inferred)"},
        "structures": {"radius_m": STRUCTURE_M, "pixels": int((struct & fp).sum()),
                       "rule": "round each crossing tower in the reservoir the passes see its caisson, not the bed: "
                               "left unseen there, and the bed under it filled from the bed round it"},
        "later_passes": {"passes": late, "margins_m": list(LATE_MARGIN_M),
                         "rule": "on each later pass the water joined to the river lies under the level reported "
                                 "then (SWOT), and the open ground over it; the bed is moved only as far as that"},
        "pixels": {"footprint": int(fp.sum()), "never_dry": int((fp & (k == len(after))).sum()),
                   "dry_by_first": int((fp & (k == 0)).sum())},
        "icesat2_check": {"from_shorelines_alone": blind, "held_to_them": check},
        "held_to": {"rule": f"each measured height pulls the bed round it (sigma {POINT_REACH_M:.0f} m) toward itself, "
                            "never out of the band the shorelines give the pixel", "points": len(used),
                    "old_maps": [{k_: m[k_] for k_ in m if k_ != "spot_heights"} | {"spot_heights": m.get("spot_heights")}
                                 for m in b.get("old_maps", [])]},
        "tiers": {"footprint": "derived (the water on the reference pass)",
                  "bed": "inferred from observed shorelines and reported levels (the waterline method)",
                  "under_water": "inferred: a bank sloping under the last level, never seen"},
        "statement": "The drained bed's heights are inferred from where the water was on each pass and the level "
                     "reported then; no elevation model of the drained bed exists. Checked against ICESat-2's measured "
                     "ground heights (icesat2_check).",
    }
    write_json(d / "bed.json", doc)
    return doc


def _icesat2(b: dict[str, Any], g: Grid, z: np.ndarray, fp: np.ndarray, d: Path) -> dict[str, Any] | None:
    """The bed against ICESat-2's measured ground (ATL08 h_te_best_fit, ellipsoid heights less the geoid there)."""
    src = b.get("icesat2")
    if not src:
        return None
    pts = json.loads((d / src["file"]).read_text())
    res = []
    for p in pts:
        c, r = g.to_px(p["lon"], p["lat"])
        ci, ri = int(c), int(r)
        if 0 <= ri < g.height and 0 <= ci < g.width and fp[ri, ci] and np.isfinite(z[ri, ci]):
            res.append(float(z[ri, ci]) - (p["h_te_best_fit"] - float(src["geoid_m"])))
    if not res:
        return {"points": 0}
    a = np.array(res)
    return {"points": len(a), "median_m": round(float(np.median(a)), 2), "mad_m": round(float(np.median(np.abs(a - np.median(a)))), 2),
            "p10_p90_m": [round(float(x), 2) for x in np.percentile(a, [10, 90])], "source": src.get("source"),
            "statement": "the bed's height minus ICESat-2's measured ground height at each 100 m segment on the bed"}


def _preview(d: Path, z: np.ndarray, fab: np.ndarray, fp: np.ndarray) -> None:
    """A shaded picture of the land with the bed (bed/bed.webp) for checking."""
    h = np.where(fp, z, fab).astype(np.float32)
    gy, gx = np.gradient(h)
    shade = np.clip(0.6 + 1.5 * (gx - gy) / 20.0, 0, 1)
    tint = np.clip((h - 4) / 16, 0, 1)
    rgb = np.stack([shade * (0.5 + 0.5 * tint), shade * (0.55 + 0.35 * tint), shade * (0.75 - 0.25 * tint)], -1)
    Image.fromarray((rgb * 255).astype(np.uint8)).save(d / "bed.webp", quality=90)


# ------------------------------------------------------------------ for the scene


def sample(d: Path, lonlat: np.ndarray, z: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """The bed's height (bilinear; `z` in its place, on the bed's grid, if given) and how far inside its footprint
    (0..1, bilinear) at each lon/lat; outside the bed's grid, nothing (nan, 0)."""
    b = np.load(bed_dir(d) / "bed.npz")
    zz = b["z"] if z is None else z
    fp = b["footprint"].astype(np.float32)
    f = on_grid(d, fp, lonlat)
    zs = on_grid(d, np.where(b["footprint"], np.nan_to_num(zz), 0).astype(np.float32), lonlat)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(f > 0, zs / f, np.nan), f


def on_grid(d: Path, a: np.ndarray, lonlat: np.ndarray) -> np.ndarray:
    """An array on the bed's grid at each lon/lat (bilinear; 0 outside it)."""
    b = np.load(bed_dir(d) / "bed.npz")
    w, s, e, n = (float(x) for x in b["bbox"])
    h, wd = a.shape
    c = (lonlat[:, 0] - w) / (e - w) * wd - 0.5
    r = (n - lonlat[:, 1]) / (n - s) * h - 0.5
    a = a.astype(np.float32)
    out = np.zeros(len(c), np.float32)
    for i in range(0, len(c), 30000):   # remap's maps stay under 32767 a side
        mx, my = c[i:i + 30000].astype(np.float32)[:, None], r[i:i + 30000].astype(np.float32)[:, None]
        out[i:i + 30000] = cv2.remap(a, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0).ravel()
    return out


CHANNEL_SWIR = (1100, 0.6, 31, -0.25, 6)   # and narrow channels under willows and reeds, too mixed for that rule
CHANNEL_RULE = (WATER_RULE + "; or SWIR under {:g}% and under {:g} of the median round it ({} px), MNDWI over {:g} "
                "(water in a pixel shared with plants: the narrow channels); runs under {} px dropped").format(
    CHANNEL_SWIR[0] / 100, *CHANNEL_SWIR[1:])


def channels(g: np.ndarray, nir: np.ndarray, sw: np.ndarray, clear: np.ndarray) -> np.ndarray:
    """The water on a texture layer's pass (10 m): open water by WATER_RULE, and the narrow channels the river left
    through the bed's willows, darker in SWIR than the ground round them (CHANNEL_SWIR; checked by eye against the
    passes' true colour, 2024 and 2025)."""
    mndwi = (g - sw) / np.maximum(g + sw, 1.0)
    swir_max, rel, win, mndwi_min, least = CHANNEL_SWIR
    bg = cv2.medianBlur(np.clip(sw / 10, 0, 255).astype(np.uint8), win).astype(np.float32) * 10
    w = clear & (((mndwi > MNDWI_MIN) & (nir < WATER_NIR_MAX)) | ((sw < swir_max) & (sw < rel * bg) & (mndwi > mndwi_min)))
    n, lab, st, _ = cv2.connectedComponentsWithStats(w.astype(np.uint8), connectivity=8)
    keep = np.zeros(n, bool)
    keep[1:] = st[1:, cv2.CC_STAT_AREA] >= least
    return keep[lab]


MASK_SOFT_PX = 1.2   # the mask's edge softened (a Gaussian, px), so its 10 m squares don't show up close


def layer_water(root: Path, cfg: dict[str, Any], ly: dict[str, Any], base: Path, http: httpx.Client | None = None) -> Path:
    """A texture layer's water as its pass saw it (imagery/<name>/water.png on the layer's own 10 m grid, fetched
    once from the same items: `WATER_RULE`), inside the bed's footprint: the river's narrow channels and the pools
    that the bed's 20 m don't hold, drawn as water on the land (build.py)."""
    from ..network import network_dir
    d = network_dir(root, cfg["id"]) / "imagery" / ly["name"]
    out = d / "water.png"
    if out.is_file():
        return out
    items = json.loads((d / "stac_items.json").read_text())
    lg = Grid.from_json(ly["grid"])
    bands = d / "water_bands.npz"   # green, NIR, SWIR (reflectance x 10000) and the clear mask, kept to re-read
    if not bands.is_file():
        with (http or httpx.Client(timeout=120)) as c:
            m = fetch_tile(providers.SENSORS["sentinel-2"], items, lg, c, piece_px=1024)
        q = lambda x: np.clip(np.nan_to_num(x), -32000, 32000).astype(np.int16)
        np.savez_compressed(bands, green=q(m.rgb_refl[1]), nir=q(m.nir), swir=q(m.swir), clear=m.clear)
    bz = np.load(bands)
    water = channels(*(bz[k].astype(np.float32) for k in ("green", "nir", "swir")), bz["clear"])
    rows, cols = np.mgrid[0:lg.height, 0:lg.width]
    lon, lat = lg.to_lonlat(cols.ravel() + 0.5, rows.ravel() + 0.5)
    fp = on_grid(base, np.load(bed_dir(base) / "bed.npz")["footprint"].astype(np.float32),
                 np.stack([lon, lat], 1)).reshape(lg.height, lg.width) > 0.5
    fp = cv2.dilate(fp.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    soft = cv2.GaussianBlur((water & fp).astype(np.float32), (0, 0), MASK_SOFT_PX)   # no 10 m steps up close
    Image.fromarray(np.clip(soft * 255, 0, 255).astype(np.uint8)).save(out)
    write_json(d / "water.json", {"rule": CHANNEL_RULE + f", inside the bed's footprint; the edge softened ({MASK_SOFT_PX} px)",
                                  "items": [i["id"] for i in items],
                                  "share": round(float((water & fp).mean()), 4)})
    return out


SHEET_DEPTH = (0.4, 0.05, 2.5)   # under the water seen on a later pass the bed lies at least this far down (m), deeper
                                 # by this much per m from its shore, down to this (inferred, under the water)


def sheets(d: Path, doc: dict[str, Any], days: list[str]) -> tuple[np.ndarray, list[np.ndarray], list[dict[str, Any]]]:
    """The river as seen on each day (the bed's `seen_*` masks: the water joined to it), on the bed's grid: its
    surface's height there (nan where dry), at the level drawn that day (`drawn`, sloping). The bed is carved under it
    (SHEET_DEPTH) so the water lies in it. The pools cut off from it and the narrow channels are too small for the
    bed's 20 m: they are drawn on the land from the layers' own 10 m masks (`layer_water`), not here. Returns the
    carved bed, each day's surface, and what each day holds."""
    b = np.load(bed_dir(d) / "bed.npz")
    z, fp = b["z"].copy(), b["footprint"]
    g = Grid(tuple(float(x) for x in b["bbox"]), float(b["m_per_px"]))
    w, _, e, _ = g.bbox
    x_m = ((w + (np.arange(g.width) + 0.5) / g.width * (e - w)) - float(doc["river_slope"]["at_lon"])) * g.kx
    out, info = [], []
    for day in days:
        water, river = b[f"seen_water_{day}"], b[f"seen_river_{day}"]
        when = _t(f"{day}T08:36:00Z")
        lv, per_m = drawn(doc, when, handover=False)
        h = np.full(z.shape, np.nan, np.float32)
        h[river] = (lv + per_m * x_m[None, :].repeat(g.height, 0))[river]
        wet = np.isfinite(h)
        dist = cv2.distanceTransform(wet.astype(np.uint8), cv2.DIST_L2, 5) * g.m_per_px
        a, k, cap = SHEET_DEPTH
        under = np.where(wet, h - np.minimum(a + k * dist, cap), np.inf)
        z = np.where(wet & fp, np.minimum(z, under), z)
        out.append(h)
        info.append({"day": day, "level_m": round(lv, 2), "river_px": int(river.sum()),
                     "pools_px": int((water & ~river).sum())})
    return z.astype(np.float32), out, info


HANDOVER_DAYS = 2.0   # once settled the reservoir's sheet sinks away over these days: the water seen on each pass
HANDOVER_M = 6.0      # (`sheets`) carries on, and the sheet goes this far under the settled level


def drawn(doc: dict[str, Any], when: datetime, handover: bool = True) -> tuple[float, float]:
    """The water's level as drawn at a moment (bed.json `drawn`: the reported level, capped once settled; then, with
    `handover`, the reservoir's sheet sinking away under the water seen on the passes) and its slope eastward (m per
    m) as far as it has formed."""
    lv = level(doc["levels"], when)
    dr = doc["drawn"]
    if handover:
        past = (when.timestamp() - _t(dr["cap_at"]).timestamp()) / 86400
        if past > 0:
            lv0, sl = drawn(doc, _t(dr["cap_at"]), handover=False)
            return lv0 - HANDOVER_M * min(1.0, past / HANDOVER_DAYS), sl
    t0, t1 = _t(dr["cap_from"]).timestamp(), _t(dr["cap_at"]).timestamp()
    if when.timestamp() > t0:
        x = min(1.0, (when.timestamp() - t0) / (t1 - t0))
        lv = min(lv, level(doc["levels"], dr["cap_from"]) * (1 - x) + float(dr["cap_m"]) * x)
    rs = doc["river_slope"]
    lat = 0.5 * (doc["grid"]["bbox"][1] + doc["grid"]["bbox"][3])
    per_m = float(rs["m_per_deg_lon"]) / (111320.0 * np.cos(np.radians(lat)))
    return lv, per_m * tilt(lv, float(doc["reference"]["level_m"]), float(rs["settled_m"]))


def texture_weights(layers: list[dict[str, Any]], day: float, fade_days: float) -> list[float]:
    """Each layer's share on a day (fractional ordinal): a layer arrives over the `fade_days` (its own, else the
    textures') ending on the day it is shown from (`shown_from`, else its pass's date), the one before it leaving."""
    w = [1.0] + [0.0] * (len(layers) - 1)
    for i, ly in enumerate(layers[1:], start=1):
        at = _t(ly["shown_from"]).toordinal() if ly.get("shown_from") else _t(ly["acquired"]).toordinal()
        f = float(ly.get("fade_days", fade_days))
        x = min(1.0, max(0.0, (day - (at - f)) / f)) if f > 0 else float(day >= at)
        x = x * x * (3 - 2 * x)
        w = [v * (1 - x) for v in w]
        w[i] = x
    return [round(v, 4) for v in w]
