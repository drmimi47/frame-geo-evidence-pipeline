"""A storyboard still: where crews were sent to repair the plant's lines, 2022-2026, accumulated (the user, 5 November
2026: at about 5:18, beside zo-night-after, "use the same map background but render in circles (similar to the
soundscape style) of where crews were dispatched to fix the wires").

    .venv/bin/python -I "research_notes/Repair regions still/scripts/repair_regions.py"      (from the project root)

The ground is the zoom-out's own (zoomout._Film, its config untouched): the Sentinel-2 pass of 28 August 2025 (the
10 m crop round the crossing over the 60 m wide crop), only resampled and dimmed by the film's one factor, the Great
Meadow's outline as the film draws it at this width. On it the plant's lines (OpenStreetMap, network.json) drawn plain
in the film's two yellows, without a state (the still has no date), and each repair whose place was published as the
area its source names: a stretch of its line (the record's sides and banks, as the unrolled film reads them from the
survey's water masks) widened to a band at least `MIN_M` across, never narrower, never a tower, a pin or a crew. Each
repair lays its own translucent band, so where repairs recur the area grows brighter (accumulated); each distinct area
is outlined dashed (an area, not a point; the unrolled film's convention) and counted. Repairs with no published place
are counted, not drawn. Everything placed comes from repairs.yaml (each with its dates, sources and the source's own
wording for the place); regions.json is what was drawn, with the safety check.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
import yaml
from PIL import Image

from image_evidence.satellite import network, unrolled, zoomout
from image_evidence.satellite.zoomout import (CORE_RGB, CREDIT_A, FADE_LEVELS, FADE_TO, GROUND, MEADOW_RGB, _blend,
                                              _Film, _smooth_ramp, _smoothstep)

HERE = Path(__file__).resolve().parents[1]
ROOT_LIB = Path("libraries/conductive-seam")
CONFIG = Path("config/conductive-seam.yaml")
W, H = 3840, 2160
MIN_M = 3000.0                 # the safety rule: an area at least about 3 km across, a stretch at least 3 km long
EACH_A = 0.065                 # one repair's band: this much white; repairs in the same place add up
REGION_RGB = (236, 240, 244)   # a cool white: apart from the lines' yellows and the Meadow's warm white
PAPER = np.array([56, 57, 59], np.float32)        # the plain grey ground (the user, 5 November 2026: "more stylized ...
WATER_RGB = np.array([38, 40, 43], np.float32)    # just the outline of the shores + river ... grey background")
EDGE_RGB = (176, 180, 186)                        # the river's and the old shore's outlines
# each area's own colour, an outline only (the user, 5 November 2026: "bright colorful borders that are semi-transparent
# with no infill", to tell the areas apart): six hues apart from the lines' yellows, checked with the dataviz skill's
# validator on this grey (every pair: colour-blind dE >= 10.9, normal vision >= 17.2; brighter than its band for fills
# on near-black, on purpose: thin outlines on mid-grey), in a fixed order by area
AREA_RGB = {"fe-north": (0x38, 0xd6, 0xf5), "fe-south": (0x8b, 0xe0, 0x4e), "switchyards": (0xff, 0xff, 0xff),
            "dn-occupied": (0xff, 0x6b, 0x2b), "dn-crossing": (0xff, 0x4f, 0xa8), "dn-north": (0x9d, 0x7d, 0xff)}
EDGE_A = 0.72                  # the outlines' strength: semi-transparent, so crossing outlines and the lines show through
MIN_WATER_PX = 300                                # at 10.4 m a pixel, about 3 ha
BED = Path("libraries/conductive-seam/satellite/networks/znpp/scenes/crossing3d/bed/bed.npz")  # the reservoir, 5 June 2023
HATCH_PX, HATCH_A = 18, 0.42   # where the water used to be: a light diagonal hatch, this far apart (at 3840), this strong
HATCH_W = 1.1                  # its lines' half-width, in px at 1920 (the user, 5 November 2026: "make the hatches more visible")
WATER = Path("libraries/conductive-seam/satellite/networks/znpp/imagery/c3d_2025_08")   # the 3D survey's water mask


def stretch(ln: zoomout.Line, a: float, b: float) -> np.ndarray:
    """The line between a and b metres from its switchyard (plant metres)."""
    s = np.concatenate([[a], ln.cum[(ln.cum > a) & (ln.cum < b)], [b]])
    return np.stack([np.interp(s, ln.cum, ln.xy[:, 0]), np.interp(s, ln.cum, ln.xy[:, 1])], 1)


def main() -> None:
    spec = yaml.safe_load((HERE / "repairs.yaml").read_text())
    cfg = network.config("znpp", CONFIG)
    cfg["film"] = {**cfg["film"], "size": [W, H]}
    root = ROOT_LIB.resolve()
    film = _Film(root, cfg)
    sc = film.sc
    v = spec["view"]
    view_m = float(v["view_km"]) * 1000
    camx, camy = (float(x) * 1000 for x in v["centre_km"])
    mpp = view_m / W
    lw = math.log(view_m)
    to_px = lambda xy: np.stack([W / 2 + (xy[:, 0] - camx) / mpp, H / 2 - (xy[:, 1] - camy) / mpp], 1)

    # the ground: plain grey, no imagery. On it only the water as the pass of 28 August 2025 saw it (the 3D survey's
    # mask, imagery/c3d_2025_08/water.png on its own 10 m lon/lat grid: the river and its channels in the drained bed),
    # filled a shade darker and outlined, and the former reservoir's shore (OpenStreetMap's Great Meadow, the drained
    # bed, as the zoom-out draws its outer shore), outlined only
    frame = np.empty((H, W, 3), np.float32)
    frame[:] = PAPER
    # where the water used to be (the user, 5 November 2026: "in a light hatch"): the reservoir as Sentinel-2 saw it on
    # 5 June 2023, the last clear pass before the dam was destroyed (the 3D bed's footprint, bed.npz on its 20 m lon/lat
    # grid: the one body of water that held the crossing; the plant's cooling pond and the lakes behind dikes are not
    # part of it), hatched light at 45 degrees and its shore outlined faintly
    bed = np.load(BED)
    bw, bs, be, bn = (float(x) for x in bed["bbox"])
    fp = bed["footprint"].astype(np.float32)
    u, vv = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    lon = film.plane.lon0 + (camx + (u + 0.5 - W / 2) * mpp) / film.plane.kx
    lat = film.plane.lat0 + (camy - (vv + 0.5 - H / 2) * mpp) / zoomout.KZ
    old = cv2.remap(fp, ((lon - bw) / (be - bw) * fp.shape[1] - 0.5).astype(np.float32),
                    ((bn - lat) / (bn - bs) * fp.shape[0] - 0.5).astype(np.float32), cv2.INTER_LINEAR,
                    borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    old = cv2.GaussianBlur(old, (0, 0), 1.0 * sc)
    ph = np.mod(u + vv, HATCH_PX)   # 45 degrees, down to the right
    lines = np.clip(1.0 - np.abs(ph - HATCH_PX / 2) / (HATCH_W * sc), 0, 1)
    _blend(frame, lines * old * HATCH_A, EDGE_RGB)
    del u, vv, lon, lat, ph, lines
    oldedge = np.zeros((H, W), np.uint8)
    cs, _ = cv2.findContours((old > 0.5).astype(np.uint8), cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    cv2.polylines(oldedge, [(c[:, 0].astype(np.float64) * 16).astype(np.int32) for c in cs if len(c) > 40], True, 255,
                  max(1, round(1.0 * sc)), cv2.LINE_AA, shift=4)
    _blend(frame, oldedge.astype(np.float32) / 255 * 0.5, EDGE_RGB)
    g = json.loads((WATER.parent / f"{WATER.name}.json").read_text())["grid"]
    w0, s0, e0, n0 = g["bbox"]
    wm = np.asarray(Image.open(WATER / "water.png"), np.float32) / 255
    u, vv = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    lon = film.plane.lon0 + (camx + (u + 0.5 - W / 2) * mpp) / film.plane.kx
    lat = film.plane.lat0 + (camy - (vv + 0.5 - H / 2) * mpp) / zoomout.KZ
    water = cv2.remap(wm, ((lon - w0) / (e0 - w0) * g["width"] - 0.5).astype(np.float32),
                      ((n0 - lat) / (n0 - s0) * g["height"] - 0.5).astype(np.float32), cv2.INTER_LINEAR,
                      borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    del u, vv, lon, lat
    n_cc, cc, st, _ = cv2.connectedComponentsWithStats((water > 0.5).astype(np.uint8), connectivity=8)
    keep = np.isin(cc, np.flatnonzero(st[:, cv2.CC_STAT_AREA] >= MIN_WATER_PX)[1:])   # pools under ~3 ha left out
    water = cv2.GaussianBlur(water * keep, (0, 0), 0.8 * sc)
    _blend(frame, water, WATER_RGB)
    edge = np.zeros((H, W), np.uint8)
    cs, _ = cv2.findContours(keep.astype(np.uint8), cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    cv2.polylines(edge, [(c[:, 0].astype(np.float64) * 16).astype(np.int32) for c in cs if len(c) > 6], True, 255,
                  max(1, round(0.9 * sc)), cv2.LINE_AA, shift=4)
    _blend(frame, edge.astype(np.float32) / 255 * 0.6, EDGE_RGB)
    # (the old shore was OpenStreetMap's Great Meadow outline; now the observed shore of 5 June 2023 above)
    era = film.eras[-1]

    # the areas: each repair's own band, the same area's bands adding up
    rd = unrolled.data(root, {**cfg, "unrolled": {**cfg["unrolled"], "show_km": 1000}})  # whole lines: their sides and banks
    stretches = {ln["record"]: ln["regions"] for ln in rd["lines"]}
    record_lines = cfg["record"]["lines"]
    by_name = {(ln.d["name"], ln.kv): ln for ln in film.lines}

    def line_of(rec_name: str) -> zoomout.Line:
        name, kv, *_ = record_lines[rec_name]
        return by_name[(name, kv)]

    regions = {}
    for r in spec["regions"]:
        if "around" in r:  # an area round facilities (switchyards): the smallest circle round their outlines, widened
            pts = np.vstack([film.plane.xy(film.net["origins"][k]["outline"]) for k in r["around"]])
            (ccx, ccy), rad = cv2.minEnclosingCircle(pts.astype(np.float32))
            rad = max(float(rad) + float(r.get("margin_km", 0.5)) * 1000, MIN_M / 2)
            mask = np.zeros((H, W), np.uint8)
            c = to_px(np.array([[ccx, ccy]]))[0]
            cv2.circle(mask, (round(c[0] * 16), round(c[1] * 16)), round(rad / mpp * 16), 255, -1, cv2.LINE_AA, shift=4)
            regions[r["id"]] = {**r, "shape": "a circle round the switchyards' OpenStreetMap outlines, widened",
                                "length_km": round(2 * rad / 1000, 2), "width_km": round(2 * rad / 1000, 2),
                                "extent_km": [round(2 * rad / 1000, 2)] * 2,
                                "area_km2": round(math.pi * rad * rad / 1e6, 1), "mask": mask, "repairs": [],
                                "centre_px": c, "radius_px": rad / mpp}
            continue
        ln = line_of(r["line"])
        if "stretch" in r:
            a, b = stretches[r["line"]][r["stretch"]]
        else:
            a, b = (float(x) * 1000 for x in r["km"])
        a, b = max(0.0, a), min(ln.length, b)
        width = float(r.get("width_km", MIN_M / 1000)) * 1000
        if b - a < MIN_M or width < MIN_M:
            raise ValueError(f"region {r['id']}: {(b - a) / 1000:.1f} km long and {width / 1000:.1f} km wide, under the "
                             f"safety rule's {MIN_M / 1000:.0f} km")
        xy = stretch(ln, a, b)
        mask = np.zeros((H, W), np.uint8)
        cv2.polylines(mask, [(to_px(xy) * 16).astype(np.int32)], False, 255, max(1, round(width / mpp)), cv2.LINE_AA,
                      shift=4)
        # in metres too: how wide the area is at its narrowest (its band), how long, how far across overall
        ext = np.ptp(xy, axis=0) + width
        regions[r["id"]] = {**r, "from_m": round(a, 1), "to_m": round(b, 1), "length_km": round((b - a) / 1000, 2),
                            "width_km": round(width / 1000, 2), "extent_km": [round(float(e) / 1000, 2) for e in ext],
                            "area_km2": round(((b - a) * width + math.pi * width * width / 4) / 1e6, 1),  # about
                            "shape": "a band along the line's stretch, rounded at its ends", "mask": mask,
                            "repairs": [], "xy": xy, "line_obj": ln}
    placed, unplaced = [], []
    for rp in spec["repairs"]:
        (placed if rp.get("region") else unplaced).append(rp)
        if rp.get("region"):
            if rp["region"] not in regions:
                raise ValueError(f"repair {rp['id']}: no region {rp['region']!r}")
            regions[rp["region"]]["repairs"].append(rp)
    # each area outlined in its own colour, no fill (drawn after the lines, below)

    # the plant's lines, plain: the film's two yellows and lighter core, fading toward their ends, no state (no glow)
    for kv_draw in (330, 750):
        lay = np.zeros((H, W), np.uint8)
        for ln in film.lines:
            kv = 750 if ln.kv >= 750 else 330
            if kv != kv_draw:
                continue
            px = to_px(ln.xy)
            mid = (ln.cum[1:] + ln.cum[:-1]) / 2 / ln.length
            q = np.round((1 - (1 - FADE_TO) * mid ** 0.8) * FADE_LEVELS).astype(int)
            cut = np.flatnonzero(np.diff(q)) + 1
            wd = max(1, round((2.6 if kv == 750 else 1.7) * sc))
            for i0, i1 in zip(np.r_[0, cut], np.r_[cut, len(q)]):
                cv2.polylines(lay, [(px[i0:i1 + 1] * 16).astype(np.int32)], False, round(255 * q[i0] / FADE_LEVELS), wd,
                              cv2.LINE_AA, shift=4)
        m = lay.astype(np.float32) / 255
        _blend(frame, np.clip(m * 0.97, 0, 1), film.colour["on"][kv_draw], CORE_RGB["on"][kv_draw], m * 0.55)

    # each area's edge, solid in its own colour, semi-transparent, no fill
    ov = film.ov
    ov.clear()
    for rg in regions.values():
        if not rg["repairs"]:
            continue
        cs, _ = cv2.findContours((rg["mask"] > 127).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        e = np.zeros((H, W), np.uint8)
        cv2.polylines(e, [(c[:, 0].astype(np.float64) * 16).astype(np.int32) for c in cs], True, 255,
                      max(1, round(2.2 * sc)), cv2.LINE_AA, shift=4)
        _blend(frame, e.astype(np.float32) / 255 * EDGE_A, np.array(AREA_RGB[rg["id"]], np.float32))

    f_label, f_small, f_plant, f_count = film.f_label, film.f_small, film.f_plant, zoomout._hn(round(30 * sc), 10)
    trk, trk_s, pad, pad_s = film.trk, film.trk_s, film.pad, film.pad_s
    # the plant: its white mark, named to the west (as the film)
    cx, cy = to_px(np.zeros((1, 2)))[0]
    ov.label([((0, 0), "ZAPORIZHZHIA NPP", f_plant, "rm", trk, 1.0)], (cx - 16 * sc, cy), 1.0, pad)
    ov.dot((cx, cy), 4.5 * sc, 1.0)
    # the lines named where the config says (only those that help)
    for lab in spec.get("line_labels", []):
        ln = line_of(lab["line"])
        x, y = (float(t) for t in to_px(ln.upto(float(lab["at_km"]) * 1000)[-1:])[0])
        right = lab.get("side", "right") == "right"
        lx = x + (14 * sc + pad[0]) * (1 if right else -1)
        ov.label([((0, 0), lab["text"].upper(), f_small, "lm" if right else "rm", trk_s, 1.0)], (lx, y), 0.95, pad_s)
    # towns, for reading the map
    for name, p in film.towns:
        if name not in spec.get("towns", []):
            continue
        x, y = (float(t) for t in to_px(p[None])[0])
        if 0 < x < W and 0 < y < H:
            ov.dot((x, y), 1.8 * sc, 0.8)
            ov.label([((0, 0), name.upper(), f_small, "mt", trk_s, 1.0)], (x, y + 9 * sc), 0.8, pad_s)
    # each area's centre: a small cross (where translucent areas overlap, the crosses tell how many do); the centre of
    # the area as drawn (a band's on its line), never a place of work
    for rg in regions.values():
        if not rg["repairs"]:
            continue
        mk = rg["mask"] > 127
        ys, xs = np.nonzero(mk)
        cx0, cy0 = float(xs.mean()), float(ys.mean())
        if "xy" in rg:   # a band: halfway along the part of its line in the frame, so the mark sits in the band
            s = to_px(stretch(rg["line_obj"], rg["from_m"], rg["to_m"]))
            s = np.concatenate([np.linspace(s[i], s[i + 1], 20, endpoint=False) for i in range(len(s) - 1)] + [s[-1:]])
            s = s[(s[:, 0] > 0) & (s[:, 0] < W) & (s[:, 1] > 0) & (s[:, 1] < H)]
            d = np.r_[0, np.cumsum(np.hypot(*np.diff(s, axis=0).T))]
            cx0, cy0 = (float(t) for t in s[np.searchsorted(d, d[-1] / 2)])
        if not mk[min(H - 1, max(0, round(cy0))), min(W - 1, max(0, round(cx0)))]:
            i = int(np.argmin((xs - cx0) ** 2 + (ys - cy0) ** 2))
            cx0, cy0 = float(xs[i]), float(ys[i])
        rg["centroid_px"] = (cx0, cy0)
        arm = 9 * sc   # the centre's sign: a plain cross on a dark halo (a ring round it read as a gunsight)
        halo = np.zeros((H, W), np.uint8)
        q = lambda x, y: (round(x * 16), round(y * 16))
        for c0, c1 in (((cx0 - arm, cy0), (cx0 + arm, cy0)), ((cx0, cy0 - arm), (cx0, cy0 + arm))):
            cv2.line(halo, q(*c0), q(*c1), 255, max(1, round(4 * sc)), cv2.LINE_AA, shift=4)
        _blend(frame, cv2.GaussianBlur(halo.astype(np.float32) / 255, (0, 0), 1.0 * sc) * 0.55, GROUND)
        cr = np.zeros((H, W), np.uint8)   # the cross in its area's colour
        for c0, c1 in (((cx0 - arm, cy0), (cx0 + arm, cy0)), ((cx0, cy0 - arm), (cx0, cy0 + arm))):
            cv2.line(cr, q(*c0), q(*c1), 255, max(1, round(1.6 * sc)), cv2.LINE_AA, shift=4)
        _blend(frame, cr.astype(np.float32) / 255, np.array(AREA_RGB[rg["id"]], np.float32))

    # each area: how many repairs, and its place in the source's terms
    for rg in regions.values():
        n = len(rg["repairs"])
        if not n:
            continue
        lab = rg["label"]
        if "line_obj" in rg:  # a point on the stretch (km from the line's start), else the area's centre
            at = float(lab["at_km"]) * 1000 if "at_km" in lab else rg["from_m"] + float(lab["at"]) * (rg["to_m"] - rg["from_m"])
            x, y = (float(t) for t in to_px(rg["line_obj"].upto(at)[-1:])[0])
        else:
            x, y = (float(t) for t in rg["centre_px"])
        dx, dy = (float(t) * sc for t in lab["offset_px"])
        anc = lab.get("anchor", "l")
        items = [((0, 0), f"{n} {'REPAIR' if n == 1 else 'REPAIRS'}", f_label, anc + "t", trk, 1.0)]
        for k, part in enumerate(lab["text"]):
            items.append(((0, (22 + 17 * k) * sc), part.upper(), f_small, anc + "t", trk_s, 0.85))
        days = [_day(p) for p in sorted(rg["repairs"], key=lambda p: str(p["when"]))]   # each repair's date
        for k in range(0, len(days), 4):
            items.append(((0, (27 + 17 * (len(lab["text"]) + k // 4)) * sc), " · ".join(days[k:k + 4]).upper(),
                          f_small, anc + "t", trk_s, 0.65))
        box = ov.label(items, (x + dx, y + dy), 1.0, pad, box=True)
        if lab.get("leader", True):  # a hairline from the label to the area's centre, stopping short of its cross
            x, y = rg["centroid_px"]
            bx = min(max(x, box[0]), box[2])
            by = min(max(y, box[1]), box[3])
            dist = math.hypot(bx - x, by - y)
            gap = 14 * sc
            if dist > gap + 4 * sc:
                ld = np.zeros((H, W), np.uint8)
                cv2.line(ld, (round((x + (bx - x) * gap / dist) * 16), round((y + (by - y) * gap / dist) * 16)),
                         (round(bx * 16), round(by * 16)), 255, max(1, round(1.0 * sc)), cv2.LINE_AA, shift=4)
                _blend(frame, ld.astype(np.float32) / 255 * 0.7, np.array(AREA_RGB[rg["id"]], np.float32))
    # no key box (removed by the user, 5 November 2026): what the frame must still say goes in the faint line above the
    # credit (the areas drawn, the + a centre, the repairs not drawn)
    note = spec["key"]["note"].format(placed=len(placed), unplaced=len(unplaced),
                                      regions=sum(1 for r in regions.values() if r["repairs"])).upper()
    ov.label([((0, 0), note, f_small, "lb", trk_s, 1.0)], (24 * sc, H - 44 * sc), CREDIT_A, pad_s, box=False)
    # the count, bottom left (the user, 5 November 2026): every repair found, first to last, drawn or not
    when = sorted(spec["repairs"], key=lambda p: str(p["when"]))
    ov.label([((0, 0), f"{len(when)} REPAIRS", f_count, "lt", trk, 1.0),
              ((0, 40 * sc), f"{_day(when[0])} – {_day(when[-1])}".upper(), f_small, "lt", trk_s, 0.85),
              ((0, 57 * sc), f"{len(placed)} DRAWN · {len(unplaced)} WITH NO PLACE PUBLISHED".upper(), f_small, "lt",
               trk_s, 0.65)], (24 * sc, H - 250 * sc), 1.0, pad, box=True)
    # the imagery's credit, bottom left, faint and unboxed (as the film)
    credit = (f"WATER: SENTINEL-2 · 28 AUGUST 2025 · {film._atts([era])} · HATCHED, THE RESERVOIR ON 5 JUNE 2023 · LINES: OPENSTREETMAP "
              "CONTRIBUTORS").upper()
    ov.label([((0, 0), credit, f_small, "lb", trk_s, 1.0)], (24 * sc, H - 24 * sc), CREDIT_A, pad_s, box=False)
    frame = ov.onto(frame)
    img = Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8))
    png, jpg = HERE / "repair_regions_3840.png", HERE / "repair_regions_1920.jpg"
    img.save(png, optimize=True)
    img.resize((1920, 1080), Image.LANCZOS).save(jpg, quality=92)

    # regions.json: what was drawn, with every source, and the safety check
    drawn = [r for r in regions.values() if r["repairs"]]
    smallest = min(min(r["length_km"], r["width_km"]) for r in drawn)
    out = {
        "schema": "repair-regions/1",
        "made_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "made_by": "research_notes/Repair regions still/scripts/repair_regions.py",
        "asked": spec["asked"],
        "image": {"png": png.name, "jpg": jpg.name, "size": [W, H],
                  "png_sha256": hashlib.sha256(png.read_bytes()).hexdigest()},
        "view": {"centre_km_east_north_of_plant": v["centre_km"], "width_km": v["view_km"],
                 "m_per_px": round(mpp, 2), "north_up": True, "as": v.get("as")},
        "ground": {"plain": "grey, no imagery", "credit": credit,
                   "water": {"mask": str(WATER / "water.png"), **json.loads((WATER / "water.json").read_text()),
                             "drawn": "resampled onto the frame (bilinear), filled a shade darker and outlined"},
                   "old_water": {"mask": str(BED), "what": "the 3D bed's footprint: the water on the last clear pass "
                                 "before the dam was destroyed (Sentinel-2, 5 June 2023; bed.json `reference`)",
                                 "drawn": f"hatched light at 45 degrees ({HATCH_PX} px apart at {W} px, {HATCH_A} "
                                          "strong), its shore outlined faintly"}},
        "areas_drawn": "each area outlined in its own colour (AREA_RGB), semi-transparent, no fill; its label lists "
                       "each repair's date (the date its source gives for the work or the reconnection)",
        "centres": {"drawn": "a small cross at each area's centre (of the area as drawn; on the area when a bent band's "
                             "centre falls outside it): marks the area, so overlapping areas can be told apart and "
                             "counted; never a place of work, a tower or a crew"},
        "lines": {"source": "OpenStreetMap power=line ways traced in network.json (ODbL)",
                  "drawn": "plain, in the zoom-out's two yellows (750 kV the brighter), fading toward their ends; no "
                           "state: the still has no date"},
        "rule": {"min_km": MIN_M / 1000,
                 "text": "Where lines were damaged or repaired, or crews sent, only as a general region: a stretch of "
                         "line or an area at least about 3 km across, never finer than the source; never a tower, a "
                         "pin, coordinates or a crew's position; never the Dniprovska substation's place or the "
                         "trench site (CLAUDE.md; NEXT.md I5)"},
        "how_drawn": spec["how_drawn"],
        "safety_check": {"smallest_km": smallest,
                         "each": {r["id"]: {"length_km": r["length_km"], "width_km": r["width_km"],
                                            "extent_km": r["extent_km"]} for r in drawn},
                         "dniprovska_substation_in_frame": False if _substation_out(film, to_px) else True},
        "regions": [{k: r[k] for k in ("id", "line", "around", "stretch", "name", "granularity", "from_m", "to_m",
                                        "length_km", "width_km", "extent_km", "area_km2", "shape", "beyond_frame", "why")
                     if k in r} | {"repairs": [p["id"] for p in r["repairs"]]} for r in drawn],
        "repairs": [_expand(p) for p in spec["repairs"]],
        "unplaced": {"count": len(unplaced), "ids": [p["id"] for p in unplaced],
                     "why": "no place published for the work (or only the substation, never shown); counted, not drawn"},
        "not_counted": [_expand(p) for p in spec.get("not_counted", [])],
        "caveats": spec.get("caveats", []),
    }
    (HERE / "regions.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str) + "\n")
    print(f"{png}\n{jpg}\n{len(drawn)} regions, smallest {smallest} km; {len(placed)} placed, {len(unplaced)} unplaced")


def _day(p: dict) -> str:
    """A repair's date as the label lists it ("9 Oct 2022"); a `when` of "YYYY-MM" gives the month."""
    s = str(p["when"])
    return (datetime.strptime(s[:10], "%Y-%m-%d").strftime("%-d %b %Y") if len(s) >= 10
            else datetime.strptime(s[:7], "%Y-%m").strftime("%b %Y"))


def _month(p: dict) -> str:
    """A repair's month, as the label lists them ("October 2025"); its `when` is a date or "YYYY-MM"."""
    s = str(p["when"])
    return datetime.strptime(s[:7], "%Y-%m").strftime("%b %Y")


PREFIX = {"GS ": "https://www.globalsecurity.org/wmd/library/news/ukraine/", "RW ": "https://reliefweb.int/report/ukraine/"}


def _expand(rp: dict) -> dict:
    """A repair as written to regions.json: its sources' shorthands (GS, RW) spelt out as URLs."""
    out = dict(rp)
    srcs = []
    for s in rp.get("sources", []):
        for k, v in PREFIX.items():
            if s.startswith(k):
                s = v + s[len(k):]
        srcs.append(s)
    out["sources"] = srcs
    return out


def _substation_out(film: _Film, to_px) -> bool:
    """Dniprovska's far end (its substation) outside the frame."""
    ln = next(ln for ln in film.lines if ln.d["name"] == "Dniprovska")
    x, y = to_px(ln.xy[-1:])[0]
    return not (0 <= x < W and 0 <= y < H)


if __name__ == "__main__":
    sys.exit(main())
