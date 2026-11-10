"""Option C again, with the lines' own shapes in place of its flat time axis (the user, 8 November 2026: "maybe using
the powerline satellite shapes themselves instead of a horizontal line"; stills first).

C1  each line's shape as its own axis: Ferosplavna-1, Dniprovska and Kakhovska 750 kV laid flat left to right from the
    plant (the switchyards a straight axis), all on one time scale; the actors above and the areas below as in C
C2  each line its own timeline: the lines as on the map (north up, one scale, no ground), time running out from the
    plant along each line, year marks on it; the switchyards' repairs round a ring at the plant
(C3, time as distance from the plant, and C4, beads on the map, were deleted by the user, 8 November 2026.)

The shapes are OpenStreetMap's (network.json, as pass 5 draws them). In C1 and C2 a position along a line is a date, never
a place, and every still says so; Which line a
repair belongs to is repairs.yaml's `line` (LINE_OF), the IAEA's "the 330 kV (back-up) line" being Ferosplavna-1 from
late 2022 (CLAUDE.md) and R01 the Kakhovska 750 kV line (sides/who_repaired.md).

    .venv/bin/python -I "research_notes/Repair regions still/scripts/repair_sides_c.py" [C1 C2]
"""

from __future__ import annotations

import json
import math
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import repair_regions_v2 as V2  # noqa: E402
import repair_regions_v5 as V5  # noqa: E402
import repair_sides as S  # noqa: E402
from repair_sides import DOT_OFF, DOT_ON, LINK_W, SIDE_FULL, SIDE_TEXT, WHITE, bezier, dashed, diamond, poly  # noqa: E402

from image_evidence.satellite.zoomout import _blend  # noqa: E402

OUT = S.OUT
CLIP_KM = {"fero": 34.4, "dnip": 34.4, "kakh": 20.0}
CLIP_SHORT = {"kakh": 6.0}                               # C2: one repair on it, so a stub   # each line from the plant out to here (Ferosplavna-1 whole)
LINE_NAME = {"fero": "FEROSPLAVNA-1", "dnip": "DNIPROVSKA", "kakh": "KAKHOVSKA 750 KV",
             "yards": "THE SWITCHYARDS AND THEIR LINKS"}
LINE_RGB = {"fero": V5.LINE_RGB[330], "dnip": V5.LINE_RGB[750], "kakh": V5.LINE_RGB[750]}
ARC_A, NODE_R = 0.38, 3.2


def line_of(rp) -> str:
    rg, t = rp.get("region") or "", rp["line"].lower()
    if rp["id"] == "R01":
        return "kakh"
    if rg == "switchyards" or any(w in t for w in ("thermal", "link", "150 kv", "reserve line")):
        return "yards"
    if rg.startswith("fe") or "ferosplavna" in t or "330 kv" in t:
        return "fero"
    if rg.startswith("dn") or "dniprovska" in t or "750 kv" in t:
        return "dnip"
    raise ValueError(rp["id"])


def shapes(B):
    f = B["film"]
    get = lambda name, kv: next(ln for ln in f.lines if ln.d["name"].startswith(name) and ln.kv == kv)
    lines = {"fero": get("Ferosplavna", 330), "dnip": get("Dniprovska", 750), "kakh": get("Kakhovska", 750)}
    return {k: ln.upto(CLIP_KM[k] * 1000) for k, ln in lines.items()}


def cum(xy):
    return np.r_[0, np.cumsum(np.hypot(*np.diff(xy, axis=0).T))]


def at_s(xy, s):
    c = cum(xy)
    return np.stack([np.interp(s, c, xy[:, 0]), np.interp(s, c, xy[:, 1])], -1)


def frac(d):
    return (d - V5.AXIS[0]).days / (V5.AXIS[1] - V5.AXIS[0]).days


def spread(vals, gap):
    """Positions in order, pushed apart to at least gap (forward only, as the ticks are)."""
    out = []
    for v in vals:
        out.append(max(v, out[-1] + gap) if out else v)
    return out


def arc(p, q, bend):
    mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
    dx, dy = q[0] - p[0], q[1] - p[1]
    return bezier(p, (mx - dy * bend, my + dx * bend), q)


class Canvas:
    def __init__(self, B, ground=True):
        self.B, self.sc, self.W, self.H = B, B["film"].sc, B["W"], B["H"]
        self.fr = np.empty((self.H, self.W, 3), np.float32)
        self.fr[:] = V5.GROUND_RGB
        self.m = {k: np.zeros((self.H, self.W), np.uint8) for k in ("arc", "dot", "node", "faint", "tick")}
        self.red = {k: np.zeros((self.H, self.W), np.uint8) for k in LINE_RGB}

    def node(self, p, filled):
        cv2.circle(self.m["node"], tuple(S._p(p)), round(NODE_R * self.sc * 16), 255,
                   -1 if filled else max(1, round(self.sc)), cv2.LINE_AA, shift=4)

    def hub(self, p, r=5.0):
        cv2.circle(self.m["node"], tuple(S._p(p)), round(r * self.sc * 16), 255, -1, cv2.LINE_AA, shift=4)

    def links(self, reps, pos, actors, iaea, bend_of=None, stub=(0, -1)):
        """Actor to repair: solid for who did it, an arc from each side for both, a dotted stub where no source
        says; dashed from the IAEA where it brokered a ceasefire."""
        sc = self.sc
        for rp in reps:
            p = pos[rp["id"]]
            sides = ["ukrainian", "russian"] if rp["side"] == "both" else [rp["side"]]
            for s in sides:
                if s == "unknown":
                    ux, uy = stub(p) if callable(stub) else stub
                    dashed(self.m["dot"], [(p[0] + ux * 6 * sc, p[1] + uy * 6 * sc), (p[0] + ux * 60 * sc, p[1] + uy * 60 * sc)],
                           DOT_ON * sc, DOT_OFF * sc, LINK_W * sc)
                else:
                    a = actors[s]
                    b = bend_of(a, p) if bend_of else (0.14 if p[0] > a[0] else -0.14)
                    poly(self.m["arc"], arc(a, p, b), LINK_W * sc)
            if S.truce_of(rp):
                dashed(self.m["arc"], arc(iaea, p, -0.16), 4.2 * sc, 3.5 * sc, 0.7 * sc)

    def finish(self):
        fr = self.fr
        for k, mm in self.red.items():
            _blend(fr, mm.astype(np.float32) / 255 * 0.95, LINE_RGB[k])
        _blend(fr, self.m["faint"].astype(np.float32) / 255 * 0.22, WHITE)
        _blend(fr, self.m["tick"].astype(np.float32) / 255 * 0.6, WHITE)
        _blend(fr, self.m["arc"].astype(np.float32) / 255 * ARC_A, WHITE)
        _blend(fr, self.m["dot"].astype(np.float32) / 255 * 0.7, WHITE)
        _blend(fr, self.m["node"].astype(np.float32) / 255, WHITE)
        return fr


def actor_labels(T, actors, iaea, reps, above=True):
    sc = T.sc
    c, _ = S.tally(reps)
    for s, xy in actors.items():
        d = -1 if above else 1
        T.tag(f"{SIDE_TEXT[s]} ({c[s]})", (xy[0], xy[1] + d * 22 * sc), "mm")
        T.tiny(SIDE_FULL[s], (xy[0], xy[1] + d * 41 * sc), "mm", 0.55)
    T.tag(f"THE IAEA BROKERED ({sum(map(S.truce_of, reps))})", (iaea[0], iaea[1] - 22 * sc), "mm")
    T.tiny("IT NEVER REPAIRED", (iaea[0], iaea[1] - 41 * sc), "mm", 0.55)


def foot(T, cv, text):
    sc, H = T.sc, T.B["H"]
    cv.fr[H - round(46 * sc):] = 0
    T.tiny(text, (24 * sc, H - 18 * sc))


def headline(T, reps):
    T.head(at=(40 * T.sc, 40 * T.sc), lines=(f"{len(reps)} repairs to the plant’s power lines since March 2022",))


def year_ticks_along(cv, T, xy_px, s_of_date, side=1, label=True):
    """A short mark across the line at each 1 January, the year beside it."""
    sc = cv.sc
    for yr in range(2022, 2027):
        d = V5.AXIS[0] if yr == 2022 else date(yr, 1, 1)
        s = s_of_date(d)
        c = cum(xy_px)
        if s > c[-1]:
            continue
        p = at_s(xy_px, s)
        q = at_s(xy_px, min(c[-1], s + 2))
        t = (q - p) / (np.hypot(*(q - p)) or 1)
        nrm = np.array([-t[1], t[0]]) * side
        poly(cv.m["tick"], [p - nrm * 5 * sc, p + nrm * 5 * sc], 0.9 * sc)
        if label:
            T.tiny(str(yr), tuple(p + nrm * 15 * sc), "mm", 0.55)


# ---- C1: each line's shape as its own axis

def option_c1(B, reps):
    cv = Canvas(B)
    T = S.Text(B)
    sc, W, H = cv.sc, cv.W, cv.H
    sh = shapes(B)
    x0, x1 = 300 * sc, W - 150 * sc
    x_of = lambda d: x0 + frac(d) * (x1 - x0)
    rows = {"fero": 420 * sc, "dnip": 520 * sc, "yards": 600 * sc, "kakh": 660 * sc}
    amp = {"fero": 40 * sc, "dnip": 40 * sc, "kakh": 16 * sc}
    axis = {}
    for kk, y in rows.items():
        if kk == "yards":                                      # no one line: a straight axis, a drawing
            xs = np.array([x0, x1])
            ys = np.array([y, y])
            dashed(cv.m["faint"], np.stack([xs, ys], 1), 6 * sc, 4 * sc, 1.0 * sc)
        else:
            xy = sh[kk] - sh[kk][0]
            ang = math.atan2(xy[-1, 1], xy[-1, 0])
            c, sn = math.cos(-ang), math.sin(-ang)
            q = np.stack([xy[:, 0] * c - xy[:, 1] * sn, -(xy[:, 0] * sn + xy[:, 1] * c)], 1)   # along, across (screen)
            q[:, 0] = np.maximum.accumulate(q[:, 0])
            xs = x0 + (q[:, 0] - q[0, 0]) / (q[-1, 0] - q[0, 0]) * (x1 - x0)
            ys = y + q[:, 1] / (np.abs(q[:, 1]).max() or 1) * amp[kk]
            poly(cv.red[kk], np.stack([xs, ys], 1), (1.6 if kk == "fero" else 2.2) * sc)
        axis[kk] = (xs, ys)
    for yr in range(2023, 2027):
        x = x_of(date(yr, 1, 1))
        dashed(cv.m["faint"], [(x, rows["fero"] - 60 * sc), (x, rows["kakh"] + 30 * sc)], 2 * sc, 5 * sc, 0.8 * sc)
        T.tiny(str(yr), (x, rows["fero"] - 70 * sc), "mm", 0.5)
    T.tiny("2022", (x0, rows["fero"] - 70 * sc), "mm", 0.5)
    pos = {}
    for kk in rows:
        mine = [r for r in reps if line_of(r) == kk]
        xs_ = spread([x_of(V2._date(r)) for r in mine], 8.5 * sc)
        for r, x in zip(mine, xs_):
            pos[r["id"]] = (x, float(np.interp(x, *axis[kk])))
        T.tiny(LINE_NAME[kk], (x0 - 16 * sc, rows[kk] + 3.5 * sc), "rm", 0.75)
    actors = {"ukrainian": (W * 0.3, 210 * sc), "russian": (W * 0.66, 210 * sc)}
    iaea = (W * 0.88, 210 * sc)
    order = ["dn-north", "fe-north", "dn-crossing", "dn-occupied", "fe-south", "switchyards", None]
    names = {"dn-north": "DNIPROVSKA, NORTH", "fe-north": "FEROSPLAVNA-1, NORTH", "dn-crossing": "DNIPROVSKA, CROSSING",
             "dn-occupied": "DNIPROVSKA, OCCUPIED SIDE", "fe-south": "FEROSPLAVNA-1, SOUTH BANK",
             "switchyards": "THE SWITCHYARDS", None: "NO PLACE PUBLISHED"}
    places = {k: (x0 + (i + 0.5) / len(order) * (x1 - x0), 900 * sc) for i, k in enumerate(order)}
    cv.links(reps, pos, actors, iaea)
    for r in reps:
        p, qq = pos[r["id"]], places[r.get("region")]
        poly(cv.m["arc"], arc(p, qq, 0.1 if qq[0] > p[0] else -0.1), LINK_W * sc)
        cv.node(p, bool(r.get("region")))
    for xy in list(actors.values()) + [iaea] + list(places.values()):
        cv.hub(xy)
    fr = cv.finish()
    actor_labels(T, actors, iaea, reps)
    for i, (k, xy) in enumerate(places.items()):
        n = sum(1 for r in reps if r.get("region") == k)
        T.tag(f"{names[k]} ({n})", (xy[0], xy[1] + (18 if i % 2 == 0 else 44) * sc), "mt")
    headline(T, reps)
    foot(T, cv, "EACH AXIS A LINE’S OWN SHAPE (OPENSTREETMAP), FROM THE PLANT AT LEFT, LAID FLAT · ACROSS: TIME, NOT PLACE "
         "· A FILLED DOT: ITS PLACE PUBLISHED, AS AN AREA · DASHED: BROKERED BY THE IAEA")
    return T.onto(fr), {"axes": "one per line, its shape laid left to right; x = date"}


# ---- C2: each line its own timeline

def fit(B, sh, box, extra=()):
    """North up, one scale: the shapes (metres) into a box on screen (px)."""
    allp = np.vstack(list(sh.values()) + [np.asarray(e, float).reshape(-1, 2) for e in extra])
    (mnx, mny), (mxx, mxy) = allp.min(0), allp.max(0)
    x0, y0, x1, y1 = box
    k = min((x1 - x0) / (mxx - mnx), (y1 - y0) / (mxy - mny))
    ox, oy = (x0 + x1) / 2 - (mnx + mxx) / 2 * k, (y0 + y1) / 2 + (mny + mxy) / 2 * k
    return lambda xy: np.stack([ox + np.asarray(xy)[..., 0] * k, oy - np.asarray(xy)[..., 1] * k], -1), k


def option_c2(B, reps):
    cv = Canvas(B)
    T = S.Text(B)
    sc, W, H = cv.sc, cv.W, cv.H
    sh = shapes(B)
    sh["kakh"] = sh["kakh"][: max(2, int(np.searchsorted(cum(sh["kakh"]), CLIP_SHORT["kakh"] * 1000)) + 1)]
    to, k = fit(B, sh, (520 * sc, 130 * sc, 1400 * sc, 990 * sc))
    yard_c, yard_r = np.array([1800.0, -300.0]), 2600.0          # a ring round both switchyards (metres): a drawing
    ring = np.stack([yard_c[0] + yard_r * np.sin(np.linspace(0, 2 * np.pi, 200)),
                     yard_c[1] + yard_r * np.cos(np.linspace(0, 2 * np.pi, 200))], 1)
    px = {kk: to(v) for kk, v in sh.items()}
    px["yards"] = to(ring)
    for kk in ("fero", "dnip", "kakh"):
        poly(cv.red[kk], px[kk], (1.6 if kk == "fero" else 2.2) * sc)
    poly(cv.m["faint"], px["yards"], 0.9 * sc, closed=True)
    pos = {}
    for kk, xy in px.items():
        mine = [r for r in reps if line_of(r) == kk]
        L = cum(xy)[-1]
        s_of = lambda d, L=L: frac(d) * L
        ss = spread([s_of(V2._date(r)) for r in mine], 8.5 * sc)
        for r, s in zip(mine, ss):
            pos[r["id"]] = tuple(at_s(xy, min(s, L)))
        year_ticks_along(cv, T, xy, s_of, side=1 if kk != "yards" else -1, label=kk != "kakh")
    actors = {"ukrainian": (250 * sc, 470 * sc), "russian": (W - 250 * sc, 470 * sc)}
    iaea = (W - 250 * sc, 800 * sc)
    cv.links(reps, pos, actors, iaea, bend_of=lambda a, p: 0.12 if a[0] < W / 2 else -0.12)
    for r in reps:
        cv.node(pos[r["id"]], bool(r.get("region")))
    for xy in list(actors.values()) + [iaea]:
        cv.hub(xy)
    fr = cv.finish()
    actor_labels(T, actors, iaea, reps)
    ends = {kk: px[kk][-1] for kk in ("fero", "dnip", "kakh")}
    T.tiny(LINE_NAME["fero"], tuple(ends["fero"] + np.array([-10 * sc, -12 * sc])), "rm", 0.75)
    T.tiny(LINE_NAME["dnip"] + " (ON, OUT OF THE FRAME)", tuple(ends["dnip"] + np.array([0, -14 * sc])), "mm", 0.75)
    T.tiny(LINE_NAME["kakh"] + " (ON)", tuple(ends["kakh"] + np.array([0, 16 * sc])), "mm", 0.75)
    yt = px["yards"][np.argmin(px["yards"][:, 0])]
    T.tiny("THE SWITCHYARDS AND THEIR LINKS (A RING: A DRAWING)", tuple(yt + np.array([-14 * sc, 0])), "rm", 0.75)
    headline(T, reps)
    foot(T, cv, "THE LINES AS OPENSTREETMAP HAS THEM, NORTH UP, ONE SCALE · EACH A TIMELINE OUT FROM THE PLANT: A DOT’S PLACE "
         "ON ITS LINE IS ITS DATE, NOT WHERE THE WORK WAS · FILLED: ITS PLACE PUBLISHED · DASHED: BROKERED BY THE IAEA")
    return T.onto(fr), {"timelines": "each line from the plant out, 2022 to November 2026"}


OPTIONS = {"C1": option_c1, "C2": option_c2}


def main(which):
    OUT.mkdir(exist_ok=True)
    B, reps = S.load()
    assert sum(1 for r in reps if line_of(r)) == len(reps)
    made = {}
    for k in which:
        img, info = OPTIONS[k](B, reps)
        Image.fromarray(V5.half(img)).save(OUT / f"sides_{k}_1920.jpg", quality=92)
        made[k] = {"jpg": f"sides_{k}_1920.jpg", **info}
        print(OUT / f"sides_{k}_1920.jpg")
    rec = OUT / "sides.json"
    doc = json.loads(rec.read_text()) if rec.exists() else {}
    doc.setdefault("options_c", {}).update(made)
    doc["options_c_asked"] = ("The user, 8 November 2026: option C, with the power lines' own shapes in place of the "
                              "horizontal axis; stills first")
    doc["line_of"] = {r["id"]: line_of(r) for r in reps}
    doc["made_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rec.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    S.sheet()


if __name__ == "__main__":
    main(sys.argv[1:] or list(OPTIONS))
