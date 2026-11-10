"""A variant's look pass (`look:` in its config; the flight south's first, 7 November 2026, decided with the user): the
data it needs outside Blender. Everything is an option of the variant, so the approved films render as they did.

- `pre_breach`: a clear pass from just before the dam was destroyed (5 June 2023), for the land and the strip south of
  it, dissolved in over the 2021 pass while the reservoir is full (`from`..`until` by the date shown), so that at the
  breach only the water changes. Fetched like the other layers (Planetary Computer, no key; network._layer).
- `match`: every pass on the ground colour-matched to one reference pass, measured on stable land (outside the
  reservoir's footprint and its shores, neither dark water nor bright cloud in either pass, the pixels that changed
  least): a gain and offset per band (8-bit sRGB values), fitted by reduced major axis (symmetric) on the same pixels of
  both passes, trimmed to the best-agreeing share and refitted. The same pass's gains serve the land and the strip south of it (one
  acquisition), so the two meet without a seam. Written as copies (look/<layer>.png), the originals untouched; the
  fits in scene.json `look.<variant>.matched`.
- per frame: the pre-breach pass's share, the plants' day (`vegetation`, look pass 2), and the wet band's levels (`wet`: the level now and `days` before, and how
  much of the band is shown).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image

from ...layout import write_json
from ..corridor import KZ as KZ_, Grid

log = logging.getLogger(__name__)

MATCH_VERSION = 2
TRIM = 0.6          # the share of stable pixels kept (those agreeing best with the fit), refitted three times
SHORE_M = 500.0     # the reservoir's footprint widened by this: its shores changed with the water
DARK, BRIGHT = 22, 215   # luma (8-bit): water under it, cloud and bare chalk over it, in either pass, left out


def _rgb(root: Path, cfg: dict[str, Any], ly: dict[str, Any]) -> np.ndarray:
    from ..network import network_dir
    return np.asarray(Image.open(network_dir(root, cfg["id"]) / ly["file"]).convert("RGB"))


def stable_mask(out: Path, layer: dict[str, Any], shape: tuple[int, int]) -> np.ndarray:
    """Land that stays land: outside the bed's footprint (bed.npz) widened by SHORE_M, on the layer's grid."""
    from . import bed
    bz = np.load(bed.bed_dir(out) / "bed.npz")
    fp = bz["footprint"].astype(np.float32)
    g = Grid.from_json(layer["grid"])
    rows, cols = np.mgrid[0:shape[0], 0:shape[1]]
    lon, lat = g.to_lonlat(cols + 0.5, rows + 0.5)
    inside = bed.on_grid(out, fp, np.stack([lon.ravel(), lat.ravel()], 1)).reshape(shape) > 0.01
    r = max(1, int(round(SHORE_M / g.m_per_px)))
    inside = cv2.dilate(inside.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1)))
    return ~inside.astype(bool)


def fit(ref: np.ndarray, im: np.ndarray, stable: np.ndarray, seed: int = 0) -> dict[str, Any]:
    """Per band y = gain·x + offset taking `im` to `ref`, on stable pixels valid and neither dark nor bright in
    either; trimmed to the TRIM share with the smallest residuals and refitted, three times."""
    lr, li = ref.mean(-1), im.mean(-1)
    ok = stable & (ref.sum(-1) > 0) & (im.sum(-1) > 0) & (lr > DARK) & (li > DARK) & (lr < BRIGHT) & (li < BRIGHT)
    idx = np.flatnonzero(ok.ravel())
    rng = np.random.default_rng(seed)
    if len(idx) > 400000:
        idx = rng.choice(idx, 400000, replace=False)
    x = im.reshape(-1, 3)[idx].astype(np.float64)
    y = ref.reshape(-1, 3)[idx].astype(np.float64)
    keep = np.ones(len(idx), bool)
    for _ in range(4):   # reduced major axis (symmetric: least squares of y on x would shrink the gain, x being noisy)
        gains, offsets = [], []
        for b in range(3):
            xb, yb = x[keep, b], y[keep, b]
            g = float(np.std(yb) / max(np.std(xb), 1e-6))
            gains.append(g)
            offsets.append(float(np.mean(yb) - g * np.mean(xb)))
        res = np.abs(x * np.array(gains) + np.array(offsets) - y).sum(1)
        keep = res <= np.quantile(res, TRIM)
    before = float(np.median(np.abs(x - y).sum(1) / 3))
    after = float(np.median(np.abs(x * np.array(gains) + np.array(offsets) - y).sum(1) / 3))
    return {"gain": [round(g, 4) for g in gains], "offset": [round(o, 3) for o in offsets],
            "pixels": int(len(idx)), "kept": int(keep.sum()),
            "median_abs_diff_before": round(before, 2), "median_abs_diff_after": round(after, 2)}


def apply(im: np.ndarray, f: dict[str, Any]) -> np.ndarray:
    valid = im.sum(-1) > 0
    out = np.clip(im.astype(np.float32) * np.array(f["gain"], np.float32) + np.array(f["offset"], np.float32), 0, 255)
    out[~valid] = 0
    return np.round(out).astype(np.uint8)


def prepare(root: Path, cfg: dict[str, Any], out: Path, look: dict[str, Any], land: list[dict[str, Any]],
            south: list[dict[str, Any]]) -> dict[str, Any]:
    """scene.json's `look.<variant>`: the pre-breach layers (fetched once) and the colour-matched copies of every pass
    (land and south strip, the pre-breach ones too), each with its fit."""
    from .. import network
    doc: dict[str, Any] = {}
    nd = network.network_dir(root, cfg["id"])
    pb = look.get("pre_breach")
    pre = {}
    if pb:
        for k in ("land", "south"):
            if pb.get(k):
                ly = network._layer(root, cfg, pb[k], None)
                pre[k] = ly
                doc.setdefault("pre_breach", {})[k] = {"file": str((nd / ly["file"]).resolve()), "pass": ly["pass_id"],
                                                       "acquired": ly["acquired"], "attribution": ly["attribution"],
                                                       "items": ly["items"], "cloud_cover": ly["cloud_cover"]}
        doc["pre_breach_statement"] = (
            f"While the reservoir is full, the land (and the reservoir's own pixels) dissolve from the pre-war pass to "
            f"{pre['land']['pass_id']} ({pre['land']['acquired'][:10]}, the last clear pass before the dam was "
            f"destroyed), between {pb['from']} and {pb['until']} by the date shown: an interpolation between two dates, "
            "said so; at the breach only the water changes" if pre.get("land") else None)
    m = look.get("match")
    if m:
        ref_name = m["reference"]
        groups = [(ly, s) for ly, s in zip(land, south if south else [None] * len(land))]
        if pre.get("land"):
            groups.append((pre["land"], pre.get("south")))
        ref = next(ly for ly, _ in groups if ly["name"] == ref_name)
        ref_rgb = _rgb(root, cfg, ref)
        stable = stable_mask(out, ref, ref_rgb.shape[:2])
        d = out / "look"
        d.mkdir(exist_ok=True)
        cache_p = d / "match.json"
        cache = json.loads(cache_p.read_text()) if cache_p.is_file() else {}
        matched = {}
        for ly, sl in groups:
            key = f"{ly['name']}|{ref_name}|{MATCH_VERSION}"
            f = cache.get(key)
            dst = d / f"{ly['name']}.png"
            if f is None or not dst.is_file():
                im = _rgb(root, cfg, ly)
                f = ({"gain": [1.0, 1.0, 1.0], "offset": [0.0, 0.0, 0.0], "reference": True} if ly["name"] == ref_name
                     else fit(ref_rgb, im, stable))
                Image.fromarray(apply(im, f)).save(dst)
                cache[key] = f
                log.info("Look: %s matched to %s: gain %s offset %s", ly["name"], ref_name, f["gain"], f["offset"])
            matched[str((nd / ly["file"]).resolve())] = {"file": str(dst.resolve()), "pass": ly["pass_id"], **f}
            if sl is not None:
                dsts = d / f"{sl['name']}.png"
                if not dsts.is_file() or cache.get(f"{sl['name']}|{key}") != f:
                    Image.fromarray(apply(_rgb(root, cfg, sl), f)).save(dsts)
                    cache[f"{sl['name']}|{key}"] = f
                matched[str((nd / sl["file"]).resolve())] = {"file": str(dsts.resolve()), "pass": sl["pass_id"],
                                                             "fit_from": ly["name"], **f}
        write_json(cache_p, cache)
        doc["matched"] = matched
        doc["match_statement"] = (
            f"Every pass on the ground colour-matched to {ref['pass_id']} ({ref_name}): a gain and offset per band "
            "(8-bit sRGB), fitted (reduced major axis) on the same pixels of both passes on stable land (outside the reservoir's footprint "
            f"widened by {SHORE_M:g} m, neither water nor cloud in either), trimmed to the {TRIM:.0%} agreeing best and "
            "refitted; the strip south of the land takes the same pass's fit. A grade so that dissolves change content, "
            "not tint; the pixels are otherwise only resampled.")
    return doc


def _day(v: Any) -> float:
    return float(datetime.fromisoformat(str(v)).toordinal())


def per_frame(look: dict[str, Any], frames: list[dict[str, Any]], days: list[float], bdoc: dict[str, Any] | None) -> None:
    """Each frame's `pre_breach` share and `wet` band ([level `days` before, level now, amount]) from the record's
    (fractional) day at that frame."""
    from . import bed
    from .vegetation import D0
    pb, wet = look.get("pre_breach"), look.get("wet")
    for f, day in zip(frames, days):
        if look.get("vegetation"):   # the plants' growth: days from the dam's destruction (look pass 2)
            f["veg_day"] = round(day - D0, 4)
        if pb:
            a, b = _day(pb["from"]), _day(pb["until"])
            x = min(1.0, max(0.0, (day - a) / (b - a)))
            f["pre_breach"] = round(x * x * (3 - 2 * x), 4)
        if wet and bdoc:
            when = datetime.fromordinal(int(day)).replace(tzinfo=timezone.utc) + timedelta(days=day % 1)
            lvl, _ = bed.drawn(bdoc, when, handover=False)
            top, _ = bed.drawn(bdoc, when - timedelta(days=float(wet.get("days", 4))), handover=False)
            cap = bed._t(bdoc["drawn"]["cap_at"])
            past = (when - cap).total_seconds() / 86400
            amount = 1.0 - min(1.0, max(0.0, past / float(wet.get("fade_days", 3))))
            f["wet"] = [round(top, 3), round(lvl, 3), round(amount, 4)]


# ------------------------------------------------------------------ look pass 3: the water's edge and colour

EDGE_VERSION = 1
VAR_VERSION = 1


def edge_field(mask: np.ndarray, sigma_px: float) -> np.ndarray:
    """A water mask (one pass, its own grid) as a field whose 0.5 contour is the shoreline drawn sub-pixel: the mask
    softened by a small Gaussian (`sigma_px` of its pixels); the renderer reads it bilinearly between pixel centres,
    so the contour runs through the pixel edges' midpoints and rounds the corners instead of stepping round each
    pixel. Values 0..1."""
    f = mask.astype(np.float32)
    if sigma_px > 0:
        f = cv2.GaussianBlur(f, (0, 0), float(sigma_px), borderType=cv2.BORDER_REPLICATE)
    return np.clip(f, 0.0, 1.0)


def edge_tolerance(mask: np.ndarray, field: np.ndarray, up: int = 8) -> dict[str, float]:
    """How far the drawn contour (`field` read bilinearly between pixel centres, at 0.5) lies from the mask's own pixel
    edges, in the mask's pixels: both ways (contour to pixel edge, pixel edge to contour), the largest and the 99th
    percentile, measured on an `up` times finer grid."""
    h, w = mask.shape
    a = cv2.resize(mask.astype(np.uint8), (w * up, h * up), interpolation=cv2.INTER_NEAREST).astype(bool)
    # bilinear between pixel centres (cv2's INTER_LINEAR keeps the half-pixel alignment)
    b = cv2.resize(field.astype(np.float32), (w * up, h * up), interpolation=cv2.INTER_LINEAR) >= 0.5
    k = np.ones((3, 3), np.uint8)

    def edge(m):
        return m & ~cv2.erode(m.astype(np.uint8), k, borderType=cv2.BORDER_REPLICATE).astype(bool)

    ea, eb = edge(a), edge(b)
    if not ea.any() or not eb.any():
        return {"max_px": 0.0, "p99_px": 0.0, "mask_to_contour_max_px": 0.0, "mask_to_contour_p99_px": 0.0}
    da = cv2.distanceTransform((~ea).astype(np.uint8), cv2.DIST_L2, 5) / up
    db = cv2.distanceTransform((~eb).astype(np.uint8), cv2.DIST_L2, 5) / up
    x, y = da[eb], db[ea]
    return {"max_px": round(float(x.max()), 3), "p99_px": round(float(np.percentile(x, 99)), 3),
            "mask_to_contour_max_px": round(float(y.max()), 3), "mask_to_contour_p99_px": round(float(np.percentile(y, 99)), 3)}


def water_edge(out: Path, days: list[str], pl: Any, sigma_px: float) -> dict[str, Any]:
    """The river each later pass saw (bed.npz `seen_river_<day>`, the bed's 20 m grid) as edge fields (`edge_field`),
    one 8-bit PNG per pass in look/ (row 0 north), for the renderer to draw the sheet's edge sub-pixel; with the
    world box they cover (metres in the plane) and each pass's measured tolerance."""
    from . import bed
    bz = np.load(bed.bed_dir(out) / "bed.npz")
    w, s, e, n = (float(x) for x in bz["bbox"])
    d = out / "look"
    d.mkdir(exist_ok=True)
    files, tol = [], {}
    for day in days:
        m = bz[f"seen_river_{day}"]
        f = edge_field(m, sigma_px)
        p = d / f"water_edge_{day}_v{EDGE_VERSION}.png"
        Image.fromarray(np.round(f * 255).astype(np.uint8)).save(p)
        files.append(str(p.resolve()))
        tol[day] = edge_tolerance(m, np.round(f * 255) / 255)
    return {"files": files, "days": days, "sigma_px": sigma_px, "source_m_per_px": float(bz["m_per_px"]),
            "x_m": [(w - pl.lon0) * pl.kx, (e - pl.lon0) * pl.kx], "y_m": [(s - pl.lat0) * KZ_, (n - pl.lat0) * KZ_],
            "tolerance_px": tol,
            "statement": ("The river sheet's edge drawn sub-pixel: each pass's river mask (the bed's 20 m grid) softened "
                          f"by a Gaussian of {sigma_px:g} px and read bilinearly between pixel centres, the water shown "
                          "where it is at least 0.5 (the rest of the sheet transparent), so the shore follows a smooth "
                          "contour instead of the mask's 20 m steps; how far it lies from the mask's pixel edges is "
                          "measured per pass (`tolerance_px`, in the mask's pixels: contour to pixel edge, and pixel "
                          "edge to contour, which includes single-pixel specks dropped). No shoreline is moved further.")}


def water_variation(root: Path, cfg: dict[str, Any], out: Path, layers: list[dict[str, Any]], look_doc: dict[str, Any],
                    pre: dict[str, Any] | None, share_clamp: tuple[float, float], sigma_px: float) -> dict[str, Any]:
    """Each pass's own colour variation over its water (look pass 3: the river not a flat sheet): per band the pass's
    pixel over the median of its water pixels, only where it saw water (a later pass: its water mask and the bed's
    river; the pre-war and pre-breach passes: the reservoir's footprint), never on the caissons' discs (bed.npz
    `structures`, widened 30 m: their concrete would read as pale blots), averaged over `sigma_px` of water pixels and
    clamped to `share_clamp`; 1 elsewhere. One PNG per pass on its own grid (the ratio 0.5..1.5 as 0..1), for the
    renderer to modulate the passes' uniform water colour."""
    from . import bed
    from ..network import network_dir
    bz = np.load(bed.bed_dir(out) / "bed.npz")
    d = out / "look"
    d.mkdir(exist_ok=True)
    lo, hi = share_clamp
    files, stats = {}, {}
    todo = [(ly, i) for i, ly in enumerate(layers)] + ([(pre, 0)] if pre else [])
    for ly, i in todo:
        src = (look_doc.get("matched") or {}).get(str((network_dir(root, cfg["id"]) / ly["file"]).resolve()), {}).get("file") \
            or str(network_dir(root, cfg["id"]) / ly["file"])
        p = d / f"{ly['name']}_watervar_v{VAR_VERSION}.png"
        key = str((network_dir(root, cfg["id"]) / ly["file"]).resolve())
        sj = p.with_suffix(".json")
        if p.is_file() and sj.is_file():
            files[key] = str(p.resolve())
            stats.update(json.loads(sj.read_text()))
            continue
        im = np.asarray(Image.open(src).convert("RGB")).astype(np.float32)
        g = Grid.from_json(ly["grid"])
        rows, cols = np.mgrid[0:g.height, 0:g.width]
        lon, lat = g.to_lonlat(cols.ravel() + 0.5, rows.ravel() + 0.5)
        ll = np.stack([lon, lat], 1)
        shape = (g.height, g.width)
        fp = bed.on_grid(out, bz["footprint"].astype(np.float32), ll).reshape(shape) > 0.5
        st = bed.on_grid(out, bz["structures"].astype(np.float32), ll).reshape(shape) > 0.05
        r = max(1, int(round(30.0 / g.m_per_px)))
        st = cv2.dilate(st.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))).astype(bool)
        if i == 0:   # the reservoir full (the pre-war pass, the pass before the breach): its footprint
            wm = fp
        else:
            day = ly["acquired"][:10]
            wm = np.zeros(shape, bool)
            if f"seen_river_{day}" in bz.files:
                wm |= bed.on_grid(out, bz[f"seen_river_{day}"].astype(np.float32), ll).reshape(shape) > 0.5
            wp = bed.layer_water(root, cfg, ly, out)
            wm |= np.asarray(Image.open(wp).convert("L")) > 127
            wm &= fp
        wm &= ~st & (im.sum(-1) > 0)
        wm = cv2.erode(wm.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)   # off the shores' mixed pixels
        out_rgb = np.full(shape + (3,), 1.0, np.float32)
        if wm.sum() > 100:
            med = np.median(im[wm], axis=0)
            ratio = im / np.maximum(med, 1.0)
            wf = wm.astype(np.float32)
            den = cv2.GaussianBlur(wf, (0, 0), sigma_px)
            for b in range(3):
                num = cv2.GaussianBlur(ratio[..., b] * wf, (0, 0), sigma_px)
                out_rgb[..., b] = np.where(den > 0.05, num / np.maximum(den, 1e-6), 1.0)
            out_rgb = np.clip(np.where(wm[..., None], out_rgb, 1.0), lo, hi)
            q = out_rgb[wm]
            stats[ly["name"]] = {"median_rgb": [round(float(x), 1) for x in med], "water_px": int(wm.sum()),
                                 "ratio_p5_p95": [round(float(np.percentile(q, 5)), 3), round(float(np.percentile(q, 95)), 3)]}
        Image.fromarray(np.round(np.clip(out_rgb - 0.5, 0, 1) * 255).astype(np.uint8)).save(p)
        sj.write_text(json.dumps({ly["name"]: stats[ly["name"]]} if ly["name"] in stats else {}))
        files[key] = str(p.resolve())
    return {"files": files, "stats": stats, "clamp": [lo, hi], "sigma_px": sigma_px,
            "statement": ("The water's colour is still the passes' own: the median of each pass's water pixels (as "
                          "before), varied by that pass's own pixels over its water (each band's ratio to the median, "
                          f"averaged over {sigma_px:g} px of water, clamped to {lo:g}-{hi:g}; never on the caissons' "
                          "discs), so the river shows where the pass saw it lighter or darker (silt, depth, wind); "
                          "imagery only resampled and averaged, never generated.")}
