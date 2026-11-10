"""Where crews were sent to repair the lines, pass 2 (the user, 8 November 2026: ideas 1, 4, 6, 7 and 8 of the review):
1. one ring per repair: each area's outline is its first repair, every later one a ring inside it (so the area as
   drawn stays exactly the source's, never wider), the count read from the shape;
4. the front: the river channel (28 August 2025) taken as the front, the land beyond it from the plant faintly tinted
   and named occupied, the land on the plant's far bank named Ukrainian-controlled;
6. a timeline strip along the foot: a tick per repair at its date, in its area's colour, grey where no place was
   published; the areas' labels lose their lists of dates;
7. the footnote clear of the lines (a dark band at the foot), the switchyards' area in a colour of its own (a blue),
   the frame tightened from the east;
8. the build-up: the same picture, the rings appearing in date order while a playhead runs along the timeline (8 s at
   30 fps; the last frame is the still).
Everything placed is v1's (repairs.yaml, the same regions and the same safety rule); v1's files are kept.

    .venv/bin/python -I "research_notes/Repair regions still/scripts/repair_regions_v2.py" [still|video|sheet|all]
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import cv2
import numpy as np
import yaml
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import repair_regions as V1  # noqa: E402  (v1: its helpers and constants; nothing in it runs on import)

from image_evidence.satellite import network, unrolled, zoomout  # noqa: E402
from image_evidence.satellite.zoomout import CORE_RGB, CREDIT_A, FADE_LEVELS, FADE_TO, GROUND, _blend, _Film  # noqa: E402

HERE = V1.HERE
OUT = HERE / "v2"
VIEW_KM, CENTRE_KM = 38.0, (2.0, 4.9)   # 7: 2 km off the empty east; the west edge stays on the old water's mask box
# 7: the switchyards' area a blue (was white) and Dniprovska north a lighter violet, so all six pass the dataviz skill's
# validator on this grey, every pair: colour-blind dE 9.4, normal vision 16.4, contrast >= 3:1 (8 November 2026)
AREA_RGB = {**V1.AREA_RGB, "switchyards": (0x00, 0x7f, 0xff), "dn-north": (0xa5, 0x94, 0xf9)}
RING_GAP = 5.0                          # px at 1920 between one repair's ring and the next, inward
UNPLACED_RGB = (150, 153, 158)
OCCUPIED_RGB, OCCUPIED_A = (190, 70, 70), 0.11   # 4: the occupied side's faint tint
FPS, SECONDS = 30, 8.0
T0, T1 = 0.6, 6.0                       # 8: the playhead runs the timeline between these seconds, then holds
AXIS = (date(2022, 2, 24), date(2026, 9, 30))    # the invasion to the end of the record's last month


def build(W: int) -> dict:
    """The picture at width W (16:9): the ground and the static marks as one image, and every mark that comes with a
    repair as its own layer, so the still and each frame of the build-up are composed from the same parts."""
    H = W * 9 // 16
    spec = yaml.safe_load((HERE / "repairs.yaml").read_text())
    cfg = network.config("znpp", V1.CONFIG)
    cfg["film"] = {**cfg["film"], "size": [W, H]}
    root = V1.ROOT_LIB.resolve()
    film = _Film(root, cfg)
    sc = film.sc                         # 1 at 1920
    view_m = VIEW_KM * 1000
    camx, camy = (x * 1000 for x in CENTRE_KM)
    mpp = view_m / W
    to_px = lambda xy: np.stack([W / 2 + (xy[:, 0] - camx) / mpp, H / 2 - (xy[:, 1] - camy) / mpp], 1)
    s38 = W / 3840                       # v1's constants were set at 3840

    frame = np.empty((H, W, 3), np.float32)
    frame[:] = V1.PAPER
    u, vv = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    lon = film.plane.lon0 + (camx + (u + 0.5 - W / 2) * mpp) / film.plane.kx
    lat = film.plane.lat0 + (camy - (vv + 0.5 - H / 2) * mpp) / zoomout.KZ

    # the water now (28 August 2025): first, since the front is read from it
    g = json.loads((V1.WATER.parent / f"{V1.WATER.name}.json").read_text())["grid"]
    w0, s0, e0, n0 = g["bbox"]
    wm = np.asarray(Image.open(V1.WATER / "water.png"), np.float32) / 255
    water = cv2.remap(wm, ((lon - w0) / (e0 - w0) * g["width"] - 0.5).astype(np.float32),
                      ((n0 - lat) / (n0 - s0) * g["height"] - 0.5).astype(np.float32), cv2.INTER_LINEAR,
                      borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    _, cc, st, _ = cv2.connectedComponentsWithStats((water > 0.5).astype(np.uint8), connectivity=8)
    keep = np.isin(cc, np.flatnonzero(st[:, cv2.CC_STAT_AREA] >= V1.MIN_WATER_PX * s38 * s38)[1:])

    # 4: the front. The land joined to the plant without crossing the water is its side (the occupied one); the land
    # joined to Marhanets and Nikopol the other. Islands between the channels are neither and stay untinted.
    towns = dict(film.towns)
    seed = lambda xy: tuple(int(round(t)) for t in to_px(np.asarray(xy, float)[None])[0])
    land = (~keep).astype(np.uint8)
    for grow in range(0, 6):             # thicken the water by a pixel at a time until the banks part
        lw = cv2.erode(land, np.ones((3, 3), np.uint8), iterations=grow) if grow else land
        _, lab = cv2.connectedComponents(lw, connectivity=4)
        sx, sy = seed(towns["Enerhodar"]); nx, ny = seed(towns["Marhanets"])
        if lab[sy, sx] and lab[ny, nx] and lab[sy, sx] != lab[ny, nx]:
            break
    else:
        raise RuntimeError("the banks don't part along the water: no front drawn")
    occ = (lab == lab[sy, sx]).astype(np.uint8)
    held = (lab == lab[ny, nx]) | (lab == lab[seed(towns["Nikopol"])[::-1]])
    cs, _ = cv2.findContours(occ, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    occ = np.zeros_like(occ)
    cv2.drawContours(occ, cs, -1, 1, -1)   # the plant's cooling pond and the lakes on that side inside it
    occ_a = cv2.GaussianBlur(occ.astype(np.float32), (0, 0), 1.2 * sc) * OCCUPIED_A
    _blend(frame, occ_a, OCCUPIED_RGB)
    front = {"grow_px": grow, "occupied_km2": round(float(occ.sum()) * mpp * mpp / 1e6, 1),
             "held_km2": round(float(held.sum()) * mpp * mpp / 1e6, 1)}

    # where the water used to be (5 June 2023), hatched; then the water now, filled and outlined (as v1)
    bed = np.load(V1.BED)
    bw, bs, be, bn = (float(x) for x in bed["bbox"])
    fp = bed["footprint"].astype(np.float32)
    old = cv2.remap(fp, ((lon - bw) / (be - bw) * fp.shape[1] - 0.5).astype(np.float32),
                    ((bn - lat) / (bn - bs) * fp.shape[0] - 0.5).astype(np.float32), cv2.INTER_LINEAR,
                    borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    old = cv2.GaussianBlur(old, (0, 0), 1.0 * sc)
    hp = V1.HATCH_PX * s38
    ph = np.mod(u + vv, hp)
    _blend(frame, np.clip(1.0 - np.abs(ph - hp / 2) / (V1.HATCH_W * sc), 0, 1) * old * V1.HATCH_A, V1.EDGE_RGB)
    del u, vv, lon, lat, ph
    oldedge = np.zeros((H, W), np.uint8)
    cs, _ = cv2.findContours((old > 0.5).astype(np.uint8), cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    cv2.polylines(oldedge, [(c[:, 0].astype(np.float64) * 16).astype(np.int32) for c in cs if len(c) > 40 * s38 * 2],
                  True, 255, max(1, round(1.0 * sc)), cv2.LINE_AA, shift=4)
    _blend(frame, oldedge.astype(np.float32) / 255 * 0.5, V1.EDGE_RGB)
    _blend(frame, cv2.GaussianBlur(water * keep, (0, 0), 0.8 * sc), V1.WATER_RGB)
    edge = np.zeros((H, W), np.uint8)
    cs, _ = cv2.findContours(keep.astype(np.uint8), cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    cv2.polylines(edge, [(c[:, 0].astype(np.float64) * 16).astype(np.int32) for c in cs if len(c) > 6], True, 255,
                  max(1, round(0.9 * sc)), cv2.LINE_AA, shift=4)
    _blend(frame, edge.astype(np.float32) / 255 * 0.6, V1.EDGE_RGB)
    era = film.eras[-1]

    # the regions, exactly as v1 makes them (the same stretches, widths and safety rule)
    rd = unrolled.data(root, {**cfg, "unrolled": {**cfg["unrolled"], "show_km": 1000}})
    stretches = {ln["record"]: ln["regions"] for ln in rd["lines"]}
    record_lines = cfg["record"]["lines"]
    by_name = {(ln.d["name"], ln.kv): ln for ln in film.lines}
    line_of = lambda rec: by_name[tuple(record_lines[rec][:2])]
    regions = {}
    for r in spec["regions"]:
        if "around" in r:
            pts = np.vstack([film.plane.xy(film.net["origins"][k]["outline"]) for k in r["around"]])
            (ccx, ccy), rad = cv2.minEnclosingCircle(pts.astype(np.float32))
            rad = max(float(rad) + float(r.get("margin_km", 0.5)) * 1000, V1.MIN_M / 2)
            mask = np.zeros((H, W), np.uint8)
            c = to_px(np.array([[ccx, ccy]]))[0]
            cv2.circle(mask, (round(c[0] * 16), round(c[1] * 16)), round(rad / mpp * 16), 255, -1, cv2.LINE_AA, shift=4)
            regions[r["id"]] = {**r, "mask": mask, "repairs": [], "centre_px": c, "width_km": 2 * rad / 1000,
                                "length_km": 2 * rad / 1000}
            continue
        ln = line_of(r["line"])
        a, b = stretches[r["line"]][r["stretch"]] if "stretch" in r else (float(x) * 1000 for x in r["km"])
        a, b = max(0.0, a), min(ln.length, b)
        width = float(r.get("width_km", V1.MIN_M / 1000)) * 1000
        if b - a < V1.MIN_M or width < V1.MIN_M:
            raise ValueError(f"region {r['id']}: under the safety rule's {V1.MIN_M / 1000:.0f} km")
        xy = V1.stretch(ln, a, b)
        mask = np.zeros((H, W), np.uint8)
        cv2.polylines(mask, [(to_px(xy) * 16).astype(np.int32)], False, 255, max(1, round(width / mpp)), cv2.LINE_AA,
                      shift=4)
        regions[r["id"]] = {**r, "mask": mask, "repairs": [], "xy": xy, "line_obj": ln, "from_m": a, "to_m": b,
                            "width_km": width / 1000, "length_km": (b - a) / 1000}
    placed, unplaced = [], []
    for rp in spec["repairs"]:
        (placed if rp.get("region") else unplaced).append(rp)
        if rp.get("region"):
            regions[rp["region"]]["repairs"].append(rp)
    for rg in regions.values():
        rg["repairs"].sort(key=lambda p: str(p["when"]))

    # the plant's lines, plain (as v1)
    for kv_draw in (330, 750):
        lay = np.zeros((H, W), np.uint8)
        for ln in film.lines:
            if (750 if ln.kv >= 750 else 330) != kv_draw:
                continue
            px = to_px(ln.xy)
            mid = (ln.cum[1:] + ln.cum[:-1]) / 2 / ln.length
            q = np.round((1 - (1 - FADE_TO) * mid ** 0.8) * FADE_LEVELS).astype(int)
            cut = np.flatnonzero(np.diff(q)) + 1
            wd = max(1, round((2.6 if kv_draw == 750 else 1.7) * sc))
            for i0, i1 in zip(np.r_[0, cut], np.r_[cut, len(q)]):
                cv2.polylines(lay, [(px[i0:i1 + 1] * 16).astype(np.int32)], False, round(255 * q[i0] / FADE_LEVELS), wd,
                              cv2.LINE_AA, shift=4)
        m = lay.astype(np.float32) / 255
        _blend(frame, np.clip(m * 0.97, 0, 1), film.colour["on"][kv_draw], CORE_RGB["on"][kv_draw], m * 0.55)

    # 7: a dark band at the foot, under the timeline and the footnote, so the lines running off the frame's foot don't
    # run through the text
    yy = np.arange(H, dtype=np.float32)[:, None]
    foot = np.clip((yy - (H - 175 * sc)) / (80 * sc), 0, 1) ** 1.5 * 0.9
    _blend(frame, np.broadcast_to(foot, (H, W)).copy(), (24, 25, 27))

    layers, events = [], []

    def layer(a: np.ndarray, rgb, key: str, peak: float = 1.0) -> int:
        ys, xs = np.nonzero(a > 0.002)
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        layers.append({"a": a[y0:y1, x0:x1].astype(np.float32), "rgb": np.array(rgb, np.float32),
                       "box": (y0, y1, x0, x1), "key": key, "peak": peak})
        return len(layers) - 1

    # 1: the rings, the first repair the area's own outline, each later one RING_GAP further in
    gap = RING_GAP * sc
    for rg in regions.values():
        if not rg["repairs"]:
            continue
        rgb = AREA_RGB[rg["id"]]
        base = (rg["mask"] > 127).astype(np.uint8)
        rg["rings"] = []
        for k, rp in enumerate(rg["repairs"]):
            r = round(k * gap)
            m = cv2.erode(base, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))) if r else base
            cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            e = np.zeros((H, W), np.uint8)
            cv2.polylines(e, [(c[:, 0].astype(np.float64) * 16).astype(np.int32) for c in cs], True, 255,
                          max(1, round(2.0 * sc)), cv2.LINE_AA, shift=4)
            rg["rings"].append(layer(e.astype(np.float32) / 255, rgb, f"ring {rg['id']} {k + 1}", V1.EDGE_A))
        # its centre's cross (on a dark halo), as v1
        mk = base > 0
        ys, xs = np.nonzero(mk)
        cx0, cy0 = float(xs.mean()), float(ys.mean())
        if "xy" in rg:
            s = to_px(V1.stretch(rg["line_obj"], rg["from_m"], rg["to_m"]))
            s = np.concatenate([np.linspace(s[i], s[i + 1], 20, endpoint=False) for i in range(len(s) - 1)] + [s[-1:]])
            s = s[(s[:, 0] > 0) & (s[:, 0] < W) & (s[:, 1] > 0) & (s[:, 1] < H)]
            d = np.r_[0, np.cumsum(np.hypot(*np.diff(s, axis=0).T))]
            cx0, cy0 = (float(t) for t in s[np.searchsorted(d, d[-1] / 2)])
        if not mk[min(H - 1, max(0, round(cy0))), min(W - 1, max(0, round(cx0)))]:
            i = int(np.argmin((xs - cx0) ** 2 + (ys - cy0) ** 2))
            cx0, cy0 = float(xs[i]), float(ys[i])
        rg["centroid_px"] = (cx0, cy0)
        arm = 9 * sc
        q = lambda x, y: (round(x * 16), round(y * 16))
        halo, cr = np.zeros((H, W), np.uint8), np.zeros((H, W), np.uint8)
        for c0, c1 in (((cx0 - arm, cy0), (cx0 + arm, cy0)), ((cx0, cy0 - arm), (cx0, cy0 + arm))):
            cv2.line(halo, q(*c0), q(*c1), 255, max(1, round(4 * sc)), cv2.LINE_AA, shift=4)
            cv2.line(cr, q(*c0), q(*c1), 255, max(1, round(1.6 * sc)), cv2.LINE_AA, shift=4)
        rg["halo"] = layer(cv2.GaussianBlur(halo.astype(np.float32) / 255, (0, 0), 1.0 * sc), GROUND, "halo", 0.55)
        rg["cross"] = layer(cr.astype(np.float32) / 255, rgb, f"cross {rg['id']}")

    ov = film.ov
    f_label, f_small, f_plant, f_count = film.f_label, film.f_small, film.f_plant, zoomout._hn(round(30 * sc), 10)
    trk, trk_s, pad, pad_s = film.trk, film.trk_s, film.pad, film.pad_s

    # the areas' labels: the count and the place in the source's terms, no dates (6: the dates are on the timeline)
    def area_items(rg, n):
        anc = rg["label"].get("anchor", "l")
        items = [((0, 0), f"{n} {'REPAIR' if n == 1 else 'REPAIRS'}", f_label, anc + "t", trk, 1.0)]
        for k, part in enumerate(rg["label"]["text"]):
            items.append(((0, (22 + 17 * k) * sc), part.upper(), f_small, anc + "t", trk_s, 0.85))
        return items

    for rg in regions.values():
        if not rg["repairs"]:
            continue
        lab = rg["label"]
        if "line_obj" in rg:
            at = float(lab["at_km"]) * 1000 if "at_km" in lab else rg["from_m"] + float(lab["at"]) * (rg["to_m"] - rg["from_m"])
            x, y = (float(t) for t in to_px(rg["line_obj"].upto(at)[-1:])[0])
        else:
            x, y = (float(t) for t in rg["centre_px"])
        if rg["id"] in LABEL_OFFSET:
            off, anc = LABEL_OFFSET[rg["id"]]
            rg["label"] = lab = {**lab, "offset_px": off, "anchor": anc}
        dx, dy = (float(t) * sc for t in lab["offset_px"])
        rg["label_at"] = (x + dx, y + dy)
        box = ov.measure(area_items(rg, len(rg["repairs"])), rg["label_at"], pad)
        x, y = rg["centroid_px"]
        bx, by = min(max(x, box[0]), box[2]), min(max(y, box[1]), box[3])
        dist, g14 = math.hypot(bx - x, by - y), 14 * sc
        rg["leader"] = None
        if lab.get("leader", True) and dist > g14 + 4 * sc:
            ld = np.zeros((H, W), np.uint8)
            cv2.line(ld, (round((x + (bx - x) * g14 / dist) * 16), round((y + (by - y) * g14 / dist) * 16)),
                     (round(bx * 16), round(by * 16)), 255, max(1, round(1.0 * sc)), cv2.LINE_AA, shift=4)
            rg["leader"] = layer(ld.astype(np.float32) / 255, AREA_RGB[rg["id"]], f"leader {rg['id']}", 0.7)

    # 6: the timeline along the foot
    x_a, x_b = 24 * sc, W - 24 * sc
    y_tl = H - 92 * sc
    span = (AXIS[1] - AXIS[0]).days
    x_of = lambda d: x_a + (d - AXIS[0]).days / span * (x_b - x_a)
    axis = np.zeros((H, W), np.uint8)
    cv2.line(axis, (round(x_a * 16), round(y_tl * 16)), (round(x_b * 16), round(y_tl * 16)), 255, max(1, round(sc)),
             cv2.LINE_AA, shift=4)
    years = []
    for yr in range(2023, 2027):
        xx = x_of(date(yr, 1, 1))
        cv2.line(axis, (round(xx * 16), round((y_tl - 4 * sc) * 16)), (round(xx * 16), round((y_tl + 4 * sc) * 16)), 255,
                 max(1, round(sc)), cv2.LINE_AA, shift=4)
        years.append((xx, str(yr)))
    _blend(frame, axis.astype(np.float32) / 255 * 0.45, (220, 222, 226))
    allr = sorted(spec["repairs"], key=lambda p: (str(p["when"]), p["id"]))
    used: list[float] = []
    for i, rp in enumerate(allr):
        d = _date(rp)
        xx = x_of(d)
        while any(abs(xx - u0) < 3 * sc for u0 in used):   # the same week: side by side, never on top
            xx += 3 * sc
        used.append(xx)
        hgt = (17 if rp.get("region") else 10) * sc
        tk = np.zeros((H, W), np.uint8)
        cv2.line(tk, (round(xx * 16), round((y_tl - 2 * sc) * 16)), (round(xx * 16), round((y_tl - hgt) * 16)), 255,
                 max(1, round(2 * sc)), cv2.LINE_AA, shift=4)
        rgb = AREA_RGB[rp["region"]] if rp.get("region") else UNPLACED_RGB
        ev = {"id": rp["id"], "date": d, "t": T0 + (d - AXIS[0]).days / span * (T1 - T0), "region": rp.get("region"),
              "tick": layer(tk.astype(np.float32) / 255, rgb, f"tick {rp['id']}"), "x": xx}
        if rp.get("region"):
            rg = regions[rp["region"]]
            k = rg["repairs"].index(rp)
            ev["ring"], ev["n"] = rg["rings"][k], k + 1
        events.append(ev)

    note = (spec["key"]["note"] + " · One ring per repair, the first outermost · The river taken as the front").upper()
    credit = (f"WATER: SENTINEL-2 · 28 AUGUST 2025 · {film._atts([era])} · HATCHED, THE RESERVOIR ON 5 JUNE 2023 · "
              "LINES: OPENSTREETMAP CONTRIBUTORS").upper()
    cx, cy = to_px(np.zeros((1, 2)))[0]
    town_px = {n: tuple(float(t) for t in to_px(p[None])[0]) for n, p in film.towns if n in spec.get("towns", [])}
    # 4: the sides named, in the empty east, and the river named the front where it leaves the frame
    side_at = {"occupied": tuple(float(t) for t in to_px(np.array([[14500.0, -1500.0]]))[0]),
               "held": tuple(float(t) for t in to_px(np.array([[14500.0, 12500.0]]))[0])}
    river_x = W - 30 * sc   # where the channel leaves the frame; the label right-aligned above it
    ys = np.flatnonzero(occ[:, int(river_x)])   # the channel's north shore where the occupied side meets it
    river_y = float(ys.min()) if len(ys) else H * 0.55
    for _ in range(int(12 * sc)):   # past the bank's eroded edge, if the banks were parted that way
        if river_y > 1 and not keep[int(river_y) - 1, int(river_x)]:
            river_y -= 1
    while river_y > 1 and keep[int(river_y) - 1, int(river_x)]:
        river_y -= 1

    def overlay(fr: np.ndarray, t: float | None) -> np.ndarray:
        """The labels, the count, the timeline's years and the playhead, over fr; t None: the still (all shown)."""
        ov.clear()
        ov.label([((0, 0), "ZAPORIZHZHIA NPP", f_plant, "rm", trk, 1.0)], (cx - 16 * sc, cy), 1.0, pad)
        ov.dot((cx, cy), 4.5 * sc, 1.0)
        for name, (x, y) in town_px.items():
            if 0 < x < W and 0 < y < H:
                ov.dot((x, y), 1.8 * sc, 0.8)
                ov.label([((0, 0), name.upper(), f_small, "mt", trk_s, 1.0)], (x, y + 9 * sc), 0.8, pad_s)
        ov.label([((0, 0), "OCCUPIED SINCE MARCH 2022", f_small, "mm", trk_s, 1.0)], side_at["occupied"], 0.8, pad_s,
                 box=False)
        ov.label([((0, 0), "UKRAINIAN-CONTROLLED", f_small, "mm", trk_s, 1.0)], side_at["held"], 0.8, pad_s, box=False)
        ov.label([((0, 0), "THE RIVER, THE FRONT", f_small, "rb", trk_s, 1.0)], (W - 24 * sc, river_y - 10 * sc), 0.6,
                 pad_s, box=False)
        for xx, yr in years:
            ov.label([((0, 0), yr, f_small, "lt", trk_s, 1.0)], (xx + 4 * sc, y_tl + 6 * sc), 0.55, pad_s, box=False)
        ov.label([((0, 0), "2022", f_small, "lt", trk_s, 1.0)], (x_a, y_tl + 6 * sc), 0.55, pad_s, box=False)
        seen = events if t is None else [e for e in events if e["t"] <= t]
        for rg in regions.values():
            if not rg["repairs"]:
                continue
            mine = [e for e in seen if e["region"] == rg["id"]]
            if mine:
                op = 1.0 if t is None else min(1.0, (t - mine[0]["t"]) / 0.3)
                ov.label(area_items(rg, len(mine)), rg["label_at"], op, pad, box=True)
        if seen:   # the count: every repair found up to the playhead, drawn or not
            n_pl = sum(1 for e in seen if e["region"])
            last = events[-1]["date"] if t is None else seen[-1]["date"]
            ov.label([((0, 0), f"{len(seen)} {'REPAIR' if len(seen) == 1 else 'REPAIRS'}", f_count, "lb", trk, 1.0),
                      ((0, 17 * sc), f"{_fmt(events[0]['date'])} – {_fmt(last)}".upper(), f_small, "lb", trk_s, 0.85),
                      ((0, 34 * sc), f"{n_pl} DRAWN · {len(seen) - n_pl} WITH NO PLACE PUBLISHED", f_small, "lb", trk_s,
                       0.65)], (24 * sc, y_tl - 66 * sc), 1.0, pad, box=True)
        if t is not None and T0 - 0.2 <= t <= T1 + 0.8:   # the playhead and its month
            op = min(1.0, (t - (T0 - 0.2)) / 0.2, (T1 + 0.8 - t) / 0.4)
            u0 = min(max((t - T0) / (T1 - T0), 0.0), 1.0)
            xx = x_a + u0 * (x_b - x_a)
            dd = date.fromordinal(AXIS[0].toordinal() + round(u0 * span))
            ov.line((xx, y_tl - 24 * sc), (xx, y_tl + 3 * sc), op)
            ov.label([((0, 0), dd.strftime("%b %Y").upper(), f_small, "mb", trk_s, 1.0)],
                     (min(max(xx, x_a + 30 * sc), x_b - 30 * sc), y_tl - 27 * sc), op, pad_s, box=False)
        ov.label([((0, 0), note, f_small, "lb", trk_s, 1.0)], (24 * sc, H - 40 * sc), CREDIT_A, pad_s, box=False)
        ov.label([((0, 0), credit, f_small, "lb", trk_s, 1.0)], (24 * sc, H - 22 * sc), CREDIT_A, pad_s, box=False)
        return ov.onto(fr)

    return {"W": W, "H": H, "base": frame, "layers": layers, "events": events, "regions": regions, "overlay": overlay,
            "placed": placed, "unplaced": unplaced, "front": front, "mpp": mpp, "film": film, "to_px": to_px,
            "credit": credit, "note": note, "spec": spec}


# the labels moved for the tighter frame (px at 1920; v1's repairs.yaml offsets otherwise)
LABEL_OFFSET: dict = {"switchyards": ([275, 88], "l")}   # east of its circle, off the count


def compose(B: dict, t: float | None) -> np.ndarray:
    """The frame at t seconds of the build-up (None: everything, the still)."""
    fr = B["base"].copy()
    lay = B["layers"]
    show = {}
    for rg in B["regions"].values():
        if not rg["repairs"]:
            continue
        first = next(e["t"] for e in B["events"] if e["region"] == rg["id"])
        for k in ("halo", "cross"):
            show[rg[k]] = _ramp(t, first, 0.3)
        if rg["leader"] is not None:
            show[rg["leader"]] = _ramp(t, first, 0.3)
    for e in B["events"]:
        show[e["tick"]] = _ramp(t, e["t"], 0.15)
        if "ring" in e:   # a ring comes in brighter, then settles
            r = _ramp(t, e["t"], 0.3)
            flash = 0.0 if t is None or t < e["t"] else 0.45 * math.exp(-(t - e["t"]) / 0.35)
            show[e["ring"]] = r * (1 + flash / lay[e["ring"]]["peak"])
    order = sorted(show, key=lambda i: ("tick" in lay[i]["key"], lay[i]["key"].startswith(("halo", "cross"))))
    for i in order:
        f = show[i]
        if f <= 0:
            continue
        L = lay[i]
        y0, y1, x0, x1 = L["box"]
        a = np.clip(L["a"] * min(1.0, L["peak"] * f), 0, 1)[..., None]
        fr[y0:y1, x0:x1] += (L["rgb"] - fr[y0:y1, x0:x1]) * a
    return np.clip(B["overlay"](fr, t), 0, 255).astype(np.uint8)


def _ramp(t, t0, dur):
    return 1.0 if t is None else min(1.0, max(0.0, (t - t0) / dur))


def _date(rp: dict) -> date:
    w = rp["when"]
    if isinstance(w, date):
        return w
    s = str(w)
    return date.fromisoformat(s[:10]) if len(s) >= 10 else date.fromisoformat(s[:7] + "-15")


def _fmt(d: date) -> str:
    return d.strftime("%-d %b %Y")


def still() -> dict:
    OUT.mkdir(exist_ok=True)
    B = build(3840)
    img = Image.fromarray(compose(B, None))
    png, jpg = OUT / "repair_regions_v2_3840.png", OUT / "repair_regions_v2_1920.jpg"
    img.save(png, optimize=True)
    img.resize((1920, 1080), Image.LANCZOS).save(jpg, quality=92)
    print(png, jpg)
    return B


def video() -> dict:
    OUT.mkdir(exist_ok=True)
    B = build(1920)
    mp4 = OUT / "repair_regions_v2.mp4"
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1920x1080",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "16", "-preset", "slow", "-pix_fmt",
                           "yuv420p", "-movflags", "+faststart", str(mp4)], stdin=subprocess.PIPE)
    n = round(SECONDS * FPS)
    for f in range(n):
        ff.stdin.write(compose(B, f / FPS).tobytes())
    ff.stdin.close()
    ff.wait()
    print(mp4, f"{n} frames")
    return B


def sheet(B: dict | None = None) -> None:
    B = B or build(1920)
    ts = [0.0, 1.5, 3.0, 4.5, 5.3, 6.0, 6.6, 7.97]
    tiles = [Image.fromarray(compose(B, t)).resize((960, 540), Image.LANCZOS) for t in ts]
    img = Image.new("RGB", (1920, 540 * 4))
    for k, (t, tl) in enumerate(zip(ts, tiles)):
        img.paste(tl, ((k % 2) * 960, (k // 2) * 540))
    img.save(OUT / "repair_regions_v2_sheet.jpg", quality=88)
    print(OUT / "repair_regions_v2_sheet.jpg", ts)


def record(B: dict) -> None:
    """regions_v2.json: v1's record (every region, repair, source and the safety check) with what pass 2 changed."""
    doc = json.loads((HERE / "regions.json").read_text())
    png = OUT / "repair_regions_v2_3840.png"
    doc.update({
        "made_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "made_by": "research_notes/Repair regions still/scripts/repair_regions_v2.py",
        "asked_v2": "The user, 8 November 2026: ideas 1 (a ring per repair), 4 (the front), 6 (a timeline strip), 7 "
                    "(the footnote, the switchyards' colour, the frame tightened), 8 (the rings appearing in date order)",
        "image": {"png": png.name, "jpg": "repair_regions_v2_1920.jpg", "video": "repair_regions_v2.mp4",
                  "size": [3840, 2160], "png_sha256": hashlib.sha256(png.read_bytes()).hexdigest() if png.exists() else None,
                  "video_fps": FPS, "video_seconds": SECONDS},
        "view": {"centre_km_east_north_of_plant": list(CENTRE_KM), "width_km": VIEW_KM, "north_up": True,
                 "as": "v1's frame 2 km narrower from the east (empty there); its west edge stays on the old water's mask box"},
        "areas_drawn": "each area outlined in its own colour (AREA_RGB), semi-transparent, no fill: its first repair the "
                       f"area's own outline, each later repair a ring {RING_GAP} px (at 1920) further in, so the drawn "
                       "area is never wider than its source says; the count and the place on its label, the dates on the "
                       "timeline",
        "palette": {k: "#%02x%02x%02x" % v for k, v in AREA_RGB.items()} | {
            "check": "dataviz skill validator, all pairs on #38393b: colour-blind dE 9.4, normal 16.4, contrast >= 3:1"},
        "front": {"drawn": "the land joined to the plant without crossing the water of 28 August 2025 (the river and "
                           "its channels in the drained bed, the 3D survey's mask) tinted faintly and named occupied; "
                           "the far bank named Ukrainian-controlled; islands between the channels untinted",
                  "taken_as": "the river taken as the front (as the unrolled film; on this stretch the Dnipro has "
                              "separated the occupied south bank, Enerhodar and the plant from March 2022, from "
                              "Ukrainian-held Nikopol and Marhanets); a drawing convention, not a surveyed line",
                  **B["front"]},
        "timeline": {"axis": [str(AXIS[0]), str(AXIS[1])], "ticks": "a tick per repair at its date (`when`), its "
                     "area's colour, grey and shorter where no place was published; the same week side by side"},
        "animation": {"seconds": SECONDS, "fps": FPS, "playhead": [T0, T1],
                      "how": "the playhead runs linearly in time over the axis; each repair's tick, and for a placed "
                             "repair its ring (brighter for a moment, then settled), appear as it passes; an area's "
                             "label and cross appear with its first repair; the count counts up; held from 6 s; the last "
                             "frame is the still",
                      "events": [{"id": e["id"], "date": str(e["date"]), "t": round(e["t"], 3),
                                  "region": e["region"]} for e in B["events"]]},
    })
    doc["safety_check"]["dniprovska_substation_in_frame"] = not _substation_out(B)
    doc["key_note"] = B["note"]
    doc["ground"]["credit"] = B["credit"]
    (OUT / "regions_v2.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False, default=str) + "\n")
    print(OUT / "regions_v2.json")


def _substation_out(B: dict) -> bool:
    ln = next(ln for ln in B["film"].lines if ln.d["name"] == "Dniprovska")
    x, y = B["to_px"](ln.xy[-1:])[0]
    return not (0 <= x < B["W"] and 0 <= y < B["H"])


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what == "sheet":
        OUT.mkdir(exist_ok=True)
        sheet()
    if what in ("still", "all"):
        Bs = still()
        record(Bs)
    if what in ("video", "all"):
        Bv = video()
        sheet(Bv)
