"""Where crews were sent to repair the lines, pass 4 (the user, 8 November 2026): pass 3 with the map simplified: no
tint for the occupied side; the land one colour, the Dnipro another, hatched, its north and south shores outlined (the
reservoir's extent on 5 June 2023, the last clear pass before the dam was destroyed), today's channels faint inside it.

Pass 3: v2 made more stylized, after Lawrence
Abu Hamdan's "Air Pressure" (Earshot) (the user's reference): a near-black map, every ring white and thinner (the newest
brightest: each ring comes in at full white and decays toward a floor that stays white, never grey), the lines red, the
text as the reference sets it (one large sentence; small white capitals on solid black boxes, the count in brackets),
everything else that isn't needed taken off. The regions, rings, front, timeline and build-up are v2's.

    .venv/bin/python -I "research_notes/Repair regions still/scripts/repair_regions_v4.py" [still|video|sheet|all]
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
import repair_regions as V1  # noqa: E402
import repair_regions_v2 as V2  # noqa: E402

from image_evidence.satellite import network, unrolled, zoomout  # noqa: E402
from image_evidence.satellite.zoomout import FADE_LEVELS, FADE_TO, _blend, _Film  # noqa: E402

zoomout.BOX_A = 1.0                     # the reference's labels: solid black boxes (this script's overlay only)
HERE = V1.HERE
OUT = HERE / "v4"
W_RENDER = 3840                         # drawn at 3840 and halved for the video, so the 1 px rings stay smooth
GROUND_RGB = np.array([38, 38, 39], np.float32)   # the land: the reference's near-black, lifted so the river reads darker
# the map in two colours (the user, 8 November 2026: "the map terrain should be 1 color and where the dnieper is should
# be another that is hatched"): the land, and the Dnipro as the reservoir held it on 5 June 2023, hatched, its shores
# outlined; today's channels a little darker inside it
RIVER_RGB = np.array([15, 15, 16], np.float32)
HATCH_RGB, HATCH_A, HATCH_W = (78, 78, 83), 0.8, 0.6   # the hatch's lines: colour, strength, half-width (px at 1920)
SHORE_RGB, SHORE_A = (170, 170, 176), 0.8
CHANNEL_RGB, CHANNEL_A = (5, 5, 6), 1.0
LINE_RGB = {750: (232, 52, 46), 330: (196, 44, 40)}   # the lines red (the user)
RING_W, RING_GAP = 1.0, 4.0             # px at 1920: thinner rings, closer together (the user: "more elegant")
RING_FLOOR, RING_TAU = 0.72, 1.6        # each ring in at full white, decaying toward this, over about this many s
BAR_PX = 108                            # px at 1920: the black bar at the foot (the timeline, the note, the credit)
FPS, SECONDS, T0, T1, AXIS = V2.FPS, V2.SECONDS, V2.T0, V2.T1, V2.AXIS
LABEL = {   # each area's label: the place in short, the count follows in brackets; and where it sits (px at 1920)
    "fe-north": ("FEROSPLAVNA-1, NORTH OF THE DNIPRO", None),
    "fe-south": ("FEROSPLAVNA-1, SOUTH BANK", None),
    "switchyards": ("THE NUCLEAR AND THERMAL PLANTS’ SWITCHYARDS", ([275, 88], "l")),
    "dn-occupied": ("DNIPROVSKA, OCCUPIED SIDE", None),
    "dn-crossing": ("DNIPROVSKA, THE CROSSING", None),
    "dn-north": ("DNIPROVSKA, NORTH OF THE DNIPRO AND BEYOND", ([140, 70], "l")),
}


def build(W: int) -> dict:
    H = W * 9 // 16
    spec = yaml.safe_load((HERE / "repairs.yaml").read_text())
    cfg = network.config("znpp", V1.CONFIG)
    cfg["film"] = {**cfg["film"], "size": [W, H]}
    root = V1.ROOT_LIB.resolve()
    film = _Film(root, cfg)
    sc = film.sc
    camx, camy = (x * 1000 for x in V2.CENTRE_KM)
    mpp = V2.VIEW_KM * 1000 / W
    to_px = lambda xy: np.stack([W / 2 + (xy[:, 0] - camx) / mpp, H / 2 - (xy[:, 1] - camy) / mpp], 1)
    s38 = W / 3840

    frame = np.empty((H, W, 3), np.float32)
    frame[:] = GROUND_RGB
    u, vv = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    lon = film.plane.lon0 + (camx + (u + 0.5 - W / 2) * mpp) / film.plane.kx
    lat = film.plane.lat0 + (camy - (vv + 0.5 - H / 2) * mpp) / zoomout.KZ
    g = json.loads((V1.WATER.parent / f"{V1.WATER.name}.json").read_text())["grid"]
    w0, s0, e0, n0 = g["bbox"]
    wm = np.asarray(Image.open(V1.WATER / "water.png"), np.float32) / 255
    water = cv2.remap(wm, ((lon - w0) / (e0 - w0) * g["width"] - 0.5).astype(np.float32),
                      ((n0 - lat) / (n0 - s0) * g["height"] - 0.5).astype(np.float32), cv2.INTER_LINEAR,
                      borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    _, cc, st, _ = cv2.connectedComponentsWithStats((water > 0.5).astype(np.uint8), connectivity=8)
    keep = np.isin(cc, np.flatnonzero(st[:, cv2.CC_STAT_AREA] >= V1.MIN_WATER_PX * s38 * s38)[1:])

    # 4: the front, as v2 (the land joined to the plant without crossing the water of 28 August 2025)
    towns = dict(film.towns)
    seed = lambda xy: tuple(int(round(t)) for t in to_px(np.asarray(xy, float)[None])[0])
    land = (~keep).astype(np.uint8)
    for grow in range(0, 6):
        lw = cv2.erode(land, np.ones((3, 3), np.uint8), iterations=grow) if grow else land
        _, lab = cv2.connectedComponents(lw, connectivity=4)
        sx, sy = seed(towns["Enerhodar"]); nx, ny = seed(towns["Marhanets"])
        if lab[sy, sx] and lab[ny, nx] and lab[sy, sx] != lab[ny, nx]:
            break
    else:
        raise RuntimeError("the banks don't part along the water: no front drawn")
    occ = (lab == lab[sy, sx]).astype(np.uint8)
    cs, _ = cv2.findContours(occ, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    occ = np.zeros_like(occ)
    cv2.drawContours(occ, cs, -1, 1, -1)
    # (no tint: the user, 8 November 2026; the sides are named, the front said in the note)
    front = {"grow_px": grow, "occupied_km2": round(float(occ.sum()) * mpp * mpp / 1e6, 1)}

    bed = np.load(V1.BED)
    bw, bs, be, bn = (float(x) for x in bed["bbox"])
    fp = bed["footprint"].astype(np.float32)
    old = cv2.remap(fp, ((lon - bw) / (be - bw) * fp.shape[1] - 0.5).astype(np.float32),
                    ((bn - lat) / (bn - bs) * fp.shape[0] - 0.5).astype(np.float32), cv2.INTER_LINEAR,
                    borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    old = cv2.GaussianBlur(old, (0, 0), 1.0 * sc)
    hp = V1.HATCH_PX * s38
    ph = np.mod(u + vv, hp)
    _blend(frame, old, RIVER_RGB)
    chan = cv2.GaussianBlur(water * keep, (0, 0), 0.8 * sc) * old   # today's channels: solid, unhatched
    _blend(frame, np.clip(1.0 - np.abs(ph - hp / 2) / (HATCH_W * sc), 0, 1) * old * (1 - chan) * HATCH_A, HATCH_RGB)
    _blend(frame, chan * CHANNEL_A, CHANNEL_RGB)
    del u, vv, lon, lat, ph
    edge = np.zeros((H, W), np.uint8)   # the north and south shores of 5 June 2023
    cs, _ = cv2.findContours((old > 0.5).astype(np.uint8), cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    cs = [c[:, 0].astype(np.float64) for c in cs if len(c) > 40 * s38 * 2]
    cs = [(np.roll(c, 1, 0) + c + np.roll(c, -1, 0)) / 3 for c in cs]   # off the pixel stairs
    cv2.polylines(edge, [(c * 16).astype(np.int32) for c in cs], True, 255, max(1, round(1.0 * sc)), cv2.LINE_AA, shift=4)
    _blend(frame, edge.astype(np.float32) / 255 * SHORE_A, SHORE_RGB)
    era = film.eras[-1]

    # the regions, as v1 and v2
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
            regions[r["id"]] = {**r, "mask": mask, "repairs": [], "centre_px": c}
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
        regions[r["id"]] = {**r, "mask": mask, "repairs": [], "xy": xy, "line_obj": ln, "from_m": a, "to_m": b}
    placed, unplaced = [], []
    for rp in spec["repairs"]:
        (placed if rp.get("region") else unplaced).append(rp)
        if rp.get("region"):
            regions[rp["region"]]["repairs"].append(rp)
    for rg in regions.values():
        rg["repairs"].sort(key=lambda p: str(p["when"]))

    # the plant's lines, red, fading toward their ends; no core, no glow
    for kv_draw in (330, 750):
        lay = np.zeros((H, W), np.uint8)
        for ln in film.lines:
            if (750 if ln.kv >= 750 else 330) != kv_draw:
                continue
            px = to_px(ln.xy)
            mid = (ln.cum[1:] + ln.cum[:-1]) / 2 / ln.length
            q = np.round((1 - (1 - FADE_TO) * mid ** 0.8) * FADE_LEVELS).astype(int)
            cut = np.flatnonzero(np.diff(q)) + 1
            wd = max(1, round((2.2 if kv_draw == 750 else 1.4) * sc))
            for i0, i1 in zip(np.r_[0, cut], np.r_[cut, len(q)]):
                cv2.polylines(lay, [(px[i0:i1 + 1] * 16).astype(np.int32)], False, round(255 * q[i0] / FADE_LEVELS), wd,
                              cv2.LINE_AA, shift=4)
        _blend(frame, np.clip(lay.astype(np.float32) / 255 * 0.95, 0, 1), LINE_RGB[kv_draw])

    # the black bar at the foot (the reference's)
    frame[H - round(BAR_PX * sc):] = 0

    layers, events = [], []

    def layer(a, rgb, key, peak=1.0):
        ys, xs = np.nonzero(a > 0.002)
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        layers.append({"a": a[y0:y1, x0:x1].astype(np.float32), "rgb": np.array(rgb, np.float32),
                       "box": (y0, y1, x0, x1), "key": key, "peak": peak})
        return len(layers) - 1

    # 1: the rings, white, the first the area's outline, each later one further in; the area's dot (where its leader
    # ends: it marks the area, never a place of work)
    gap = RING_GAP * sc
    for rg in regions.values():
        if not rg["repairs"]:
            continue
        base = (rg["mask"] > 127).astype(np.uint8)
        rg["rings"] = []
        for k, rp in enumerate(rg["repairs"]):
            r = round(k * gap)
            m = cv2.erode(base, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))) if r else base
            cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            e = np.zeros((H, W), np.uint8)
            cv2.polylines(e, [(c[:, 0].astype(np.float64) * 16).astype(np.int32) for c in cs], True, 255,
                          max(1, round(RING_W * sc)), cv2.LINE_AA, shift=4)
            rg["rings"].append(layer(e.astype(np.float32) / 255, (255, 255, 255), f"ring {rg['id']} {k + 1}"))
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

    ov = film.ov
    f_head = zoomout._hn(round(50 * sc), 0)       # the sentence, as the reference's: large, regular, sentence case
    f_tag = zoomout._hn(round(12 * sc), 1)        # the labels: small bold capitals
    f_tiny = zoomout._hn(round(10.5 * sc), 10)    # the bar's text and the sides
    tk_tag, pad_tag = 0.06 * 12 * sc, (round(6 * sc), round(4 * sc))

    def tag(rg, n):
        return [((0, 0), f"{LABEL[rg['id']][0]} ({n})", f_tag, rg["label"].get("anchor", "l") + "m", tk_tag, 1.0)]

    for rg in regions.values():
        if not rg["repairs"]:
            continue
        lab = dict(rg["label"])
        if LABEL[rg["id"]][1]:
            lab["offset_px"], lab["anchor"] = LABEL[rg["id"]][1]
        rg["label"] = lab
        if "line_obj" in rg:
            at = float(lab["at_km"]) * 1000 if "at_km" in lab else rg["from_m"] + float(lab["at"]) * (rg["to_m"] - rg["from_m"])
            x, y = (float(t) for t in to_px(rg["line_obj"].upto(at)[-1:])[0])
        else:
            x, y = (float(t) for t in rg["centre_px"])
        dx, dy = (float(t) * sc for t in lab["offset_px"])
        rg["label_at"] = (x + dx, y + dy + 8 * sc)
        box = ov.measure(tag(rg, len(rg["repairs"])), rg["label_at"], pad_tag)
        x, y = rg["centroid_px"]
        bx, by = min(max(x, box[0]), box[2]), min(max(y, box[1]), box[3])
        dist = math.hypot(bx - x, by - y)
        ld = np.zeros((H, W), np.uint8)
        if dist > 8 * sc:
            cv2.line(ld, (round(x * 16), round(y * 16)), (round(bx * 16), round(by * 16)), 255, max(1, round(0.8 * sc)),
                     cv2.LINE_AA, shift=4)
        cv2.circle(ld, (round(x * 16), round(y * 16)), round(2.6 * sc * 16), 255, -1, cv2.LINE_AA, shift=4)
        rg["leader"] = layer(ld.astype(np.float32) / 255, (255, 255, 255), f"leader {rg['id']}", 0.85)

    # 6: the timeline, in the bar: placed repairs white, unplaced grey and shorter
    x_a, x_b = 24 * sc, W - 24 * sc
    y_tl = H - 66 * sc
    span = (AXIS[1] - AXIS[0]).days
    x_of = lambda d: x_a + (d - AXIS[0]).days / span * (x_b - x_a)
    axis = np.zeros((H, W), np.uint8)
    cv2.line(axis, (round(x_a * 16), round(y_tl * 16)), (round(x_b * 16), round(y_tl * 16)), 255, max(1, round(0.8 * sc)),
             cv2.LINE_AA, shift=4)
    years = []
    for yr in range(2023, 2027):
        xx = x_of(date(yr, 1, 1))
        cv2.line(axis, (round(xx * 16), round(y_tl * 16)), (round(xx * 16), round((y_tl + 5 * sc) * 16)), 255,
                 max(1, round(0.8 * sc)), cv2.LINE_AA, shift=4)
        years.append((xx, str(yr)))
    _blend(frame, axis.astype(np.float32) / 255 * 0.4, (255, 255, 255))
    allr = sorted(spec["repairs"], key=lambda p: (str(p["when"]), p["id"]))
    used: list[float] = []
    for rp in allr:
        d = V2._date(rp)
        xx = x_of(d)
        while any(abs(xx - u0) < 2.5 * sc for u0 in used):
            xx += 2.5 * sc
        used.append(xx)
        hgt = (14 if rp.get("region") else 7) * sc
        tk = np.zeros((H, W), np.uint8)
        cv2.line(tk, (round(xx * 16), round((y_tl - 1.5 * sc) * 16)), (round(xx * 16), round((y_tl - hgt) * 16)), 255,
                 max(1, round(1.2 * sc)), cv2.LINE_AA, shift=4)
        ev = {"id": rp["id"], "date": d, "t": T0 + (d - AXIS[0]).days / span * (T1 - T0), "region": rp.get("region"),
              "tick": layer(tk.astype(np.float32) / 255, (255, 255, 255), f"tick {rp['id']}",
                            0.95 if rp.get("region") else 0.42)}
        if rp.get("region"):
            rg = regions[rp["region"]]
            ev["ring"] = rg["rings"][rg["repairs"].index(rp)]
        events.append(ev)

    note = ("Areas drawn, not observed, each as wide as its source says · one ring per repair · a dot marks an area, "
            "not a place of work · the river taken as the front").upper()
    credit = (f"Water: Sentinel-2 · 28 August 2025 · {film._atts([era])} · hatched, the reservoir on 5 June 2023 · "
              "lines: OpenStreetMap contributors").upper()
    cx, cy = to_px(np.zeros((1, 2)))[0]
    town_px = {n: tuple(float(t) for t in to_px(p[None])[0]) for n, p in film.towns if n in ("Nikopol", "Enerhodar")}
    side_at = {"occupied": tuple(float(t) for t in to_px(np.array([[-12000.0, -2800.0]]))[0]),   # on each bank's land
               "held": tuple(float(t) for t in to_px(np.array([[14500.0, 8600.0]]))[0])}
    head_at = (W - 470 * sc, 40 * sc)

    def overlay(fr, t):
        ov.clear()
        seen = events if t is None else [e for e in events if e["t"] <= t]
        # the sentence, top right over the empty east (the reference's headline), counting up
        n = len(seen)
        ov.label([((0, 0), f"{n} {'repair' if n == 1 else 'repairs'} to the", f_head, "lt", 0, 1.0),
                  ((0, 56 * sc), "plant’s power lines", f_head, "lt", 0, 1.0),
                  ((0, 112 * sc), "since March 2022", f_head, "lt", 0, 1.0)], head_at, 1.0, (0, 0), box=False)
        n_pl = sum(1 for e in seen if e["region"])
        ov.label([((0, 0), f"{n_pl} WITH A PLACE PUBLISHED, DRAWN · {n - n_pl} WITHOUT", f_tiny, "lt", 0.8 * sc, 1.0)],
                 (head_at[0] + 2 * sc, head_at[1] + 180 * sc), 0.7, (0, 0), box=False)
        # the plant, the two towns, the sides
        ov.label([((0, 0), "ZAPORIZHZHIA NPP", f_tag, "rm", tk_tag, 1.0)], (cx - 12 * sc, cy), 1.0, pad_tag)
        ov.dot((cx, cy), 3.5 * sc, 1.0)
        for name, (x, y) in town_px.items():
            if 0 < x < W and 0 < y < H:
                ov.dot((x, y), 1.6 * sc, 0.6)
                ov.label([((0, 0), name.upper(), f_tiny, "mt", 0.8 * sc, 1.0)], (x, y + 7 * sc), 0.6, (0, 0), box=False)
        ov.label([((0, 0), "OCCUPIED", f_tiny, "mm", 2.0 * sc, 1.0)], side_at["occupied"], 0.55, (0, 0), box=False)
        ov.label([((0, 0), "UKRAINIAN-CONTROLLED", f_tiny, "mm", 2.0 * sc, 1.0)], side_at["held"], 0.55, (0, 0), box=False)
        for rg in regions.values():
            mine = [e for e in seen if e["region"] == rg["id"]]
            if mine:
                op = 1.0 if t is None else min(1.0, (t - mine[0]["t"]) / 0.3)
                ov.label(tag(rg, len(mine)), rg["label_at"], op, pad_tag, box=True)
        # the bar: the years, the playhead and its month, the note and the credit
        for xx, yr in [(x_a - 4 * sc, "2022")] + years:
            ov.label([((0, 0), yr, f_tiny, "lt", 0.8 * sc, 1.0)], (xx + 4 * sc, y_tl + 7 * sc), 0.5, (0, 0), box=False)
        if t is not None and T0 - 0.2 <= t <= T1 + 0.8:
            op = min(1.0, (t - (T0 - 0.2)) / 0.2, (T1 + 0.8 - t) / 0.4)
            u0 = min(max((t - T0) / (T1 - T0), 0.0), 1.0)
            xx = x_a + u0 * (x_b - x_a)
            dd = date.fromordinal(AXIS[0].toordinal() + round(u0 * span))
            ov.line((xx, y_tl - 20 * sc), (xx, y_tl + 2 * sc), op)
            ov.label([((0, 0), dd.strftime("%b %Y").upper(), f_tiny, "mb", 0.8 * sc, 1.0)],
                     (min(max(xx, x_a + 26 * sc), x_b - 26 * sc), y_tl - 23 * sc), op, (0, 0), box=False)
        ov.label([((0, 0), note, f_tiny, "lb", 0.8 * sc, 1.0)], (24 * sc, H - 26 * sc), 0.42, (0, 0), box=False)
        ov.label([((0, 0), credit, f_tiny, "lb", 0.8 * sc, 1.0)], (24 * sc, H - 11 * sc), 0.42, (0, 0), box=False)
        return ov.onto(fr)

    return {"W": W, "H": H, "base": frame, "layers": layers, "events": events, "regions": regions, "overlay": overlay,
            "placed": placed, "unplaced": unplaced, "front": front, "film": film, "to_px": to_px, "credit": credit,
            "note": note}


def ring_level(t: float, t0: float) -> float:
    """A ring's strength: nothing before its repair, full white as it comes in, then decaying toward RING_FLOOR (the
    newest brightest; the floor keeps every ring white)."""
    if t < t0:
        return 0.0
    rise = min(1.0, (t - t0) / 0.15)
    return rise * (RING_FLOOR + (1 - RING_FLOOR) * math.exp(-(t - t0) / RING_TAU))


def compose(B: dict, t: float) -> np.ndarray:
    fr = B["base"].copy()
    lay = B["layers"]
    show = {}
    for rg in B["regions"].values():
        if rg["repairs"]:
            first = next(e["t"] for e in B["events"] if e["region"] == rg["id"])
            show[rg["leader"]] = min(1.0, max(0.0, (t - first) / 0.3))
    for e in B["events"]:
        show[e["tick"]] = min(1.0, max(0.0, (t - e["t"]) / 0.15))
        if "ring" in e:
            show[e["ring"]] = ring_level(t, e["t"])
    for i, f in show.items():
        if f <= 0:
            continue
        L = lay[i]
        y0, y1, x0, x1 = L["box"]
        a = (L["a"] * (L["peak"] * f))[..., None]
        fr[y0:y1, x0:x1] += (L["rgb"] - fr[y0:y1, x0:x1]) * a
    return np.clip(B["overlay"](fr, t), 0, 255).astype(np.uint8)


def half(img: np.ndarray) -> np.ndarray:
    return cv2.resize(img, (img.shape[1] // 2, img.shape[0] // 2), interpolation=cv2.INTER_AREA)


T_STILL = SECONDS - 1 / FPS   # the still is the video's last frame


def main(what: str) -> None:
    OUT.mkdir(exist_ok=True)
    B = build(W_RENDER)
    if what in ("still", "all"):
        img = compose(B, T_STILL)
        Image.fromarray(img).save(OUT / "repair_regions_v4_3840.png", optimize=True)
        Image.fromarray(half(img)).save(OUT / "repair_regions_v4_1920.jpg", quality=92)
        record(B)
    if what in ("video", "all"):
        mp4 = OUT / "repair_regions_v4.mp4"
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s",
                               "1920x1080", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "16", "-preset", "slow",
                               "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(mp4)], stdin=subprocess.PIPE)
        for f in range(round(SECONDS * FPS)):
            ff.stdin.write(half(compose(B, f / FPS)).tobytes())
        ff.stdin.close()
        ff.wait()
        print(mp4)
    if what in ("sheet", "video", "all"):
        ts = [1.5, 3.0, 4.5, 5.3, 5.8, 6.4, 7.0, T_STILL]
        img = Image.new("RGB", (1920, 540 * 4))
        for k, t in enumerate(ts):
            img.paste(Image.fromarray(cv2.resize(compose(B, t), (960, 540), interpolation=cv2.INTER_AREA)),
                      ((k % 2) * 960, (k // 2) * 540))
        img.save(OUT / "repair_regions_v4_sheet.jpg", quality=88)
        print(OUT / "repair_regions_v4_sheet.jpg", ts)


def record(B: dict) -> None:
    doc = json.loads((V2.OUT / "regions_v2.json").read_text())
    png = OUT / "repair_regions_v4_3840.png"
    doc.update({
        "made_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "made_by": "research_notes/Repair regions still/scripts/repair_regions_v4.py",
        "asked_v4": "The user, 8 November 2026: no different colour for the occupied area; the land one colour, the "
                    "Dnipro another, hatched, so the north and south shores show clearly",
        "map": "the land #262627; the Dnipro as the reservoir held it on 5 June 2023 (the 3D bed's footprint) #0f0f10, "
               "hatched at 45 degrees, its shores outlined; today's channels (28 August 2025) solid near-black inside it, unhatched",
        "asked_v3": "The user, 8 November 2026: more stylized after Lawrence Abu Hamdan's Air Pressure (Earshot): its near-black "
                    "map, the rings all white and thinner, the newest brightest (a decay capped so they stay white), "
                    "the text and boxes improved, the power lines red, unnecessary text removed",
        "image": {"png": png.name, "jpg": "repair_regions_v4_1920.jpg", "video": "repair_regions_v4.mp4",
                  "size": [3840, 2160], "png_sha256": hashlib.sha256(png.read_bytes()).hexdigest(),
                  "video_fps": FPS, "video_seconds": SECONDS, "drawn_at": W_RENDER, "still": f"the video's last frame ({T_STILL:.3f} s)"},
        "areas_drawn": f"white rings, {RING_W} px (at 1920), {RING_GAP} px apart inward, the first repair the area's own "
                       "outline; each ring comes in at full white and decays toward "
                       f"{RING_FLOOR} (exp, {RING_TAU} s), so the newest are brightest and none goes grey; a dot at "
                       "the area's centre ends its label's leader (an area, never a place of work)",
        "palette": {"ground": "#262627", "river": "#0f0f10", "channels": "#050506", "rings": "#ffffff",
                    "lines_750": "#e8342e", "lines_330": "#c42c28", "bar": "#000000"},
        "text": {"sentence": "the count of every repair found, counting up with the playhead",
                 "labels": {k: v[0] for k, v in LABEL.items()}, "removed": ["the river's label", "Marhanets",
                 "the count box (now the sentence)", "the centres' crosses (now a dot)"]},
    })
    doc["safety_check"]["dniprovska_substation_in_frame"] = not V2._substation_out(B)
    doc["key_note"] = B["note"]
    doc["ground"]["credit"] = B["credit"]
    (OUT / "regions_v4.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False, default=str) + "\n")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "all")
