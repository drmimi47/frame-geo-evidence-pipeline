"""Who repaired the lines, ways to draw it (the user, 8 November 2026: "make it feel more like a network of repairs
... lines coming from the Ukrainian side or Russian side to each repair depending on whether the reports stated they
were joint repairs or just from one side"; options A to E, stills before any animation; A, B and D deleted by the user, 8 November 2026, with C3 and C4 of
repair_sides_c.py).

Every option is pass 5's map (repair_regions_v5.py) and repairs.yaml's `side`, `arranged_by` and `worked_on`
(sides/who_repaired.md). The sides are never places: no link starts where a crew was, a tower, the Dniprovska
substation or any point on the land. One vocabulary throughout: a solid link, that side did the work; a dotted one, the
sources don't say who; a small open diamond, under a local ceasefire the IAEA brokered (it never repaired).

C  a network diagram, no map: actors above, every repair on a time axis, the areas below
E  the side in the rings: solid Ukrainian, dashed Russian, dash-dot both, dotted not said

    .venv/bin/python -I "research_notes/Repair regions still/scripts/repair_sides.py" [C E]
"""

from __future__ import annotations

import json
import math
import sys
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

import cv2
import numpy as np
import yaml
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import repair_regions_v2 as V2  # noqa: E402
import repair_regions_v5 as V5  # noqa: E402

from image_evidence.satellite import zoomout  # noqa: E402
from image_evidence.satellite.zoomout import _blend  # noqa: E402

OUT = V5.HERE / "sides"
V5.AXIS = (V5.AXIS[0], date(2026, 11, 30))   # pass 5's axis ends with September 2026; R48 is 23 October (these stills only)
WHITE = (255, 255, 255)
LINK_A, LINK_W = 0.6, 0.8                 # a link's strength and width (px at 1920)
DOT_ON, DOT_OFF = 1.2, 3.2                # dotted: the sources don't say who
DASH_ON, DASH_OFF = 7.0, 3.5              # dashed (E: the Russian side)
SIDE_TEXT = {"ukrainian": "UKRAINIAN CREWS", "russian": "THE RUSSIAN SIDE", "both": "BOTH SIDES", "unknown": "NOT SAID"}
SIDE_FULL = {"ukrainian": "UKRENERGO, ENERGOATOM, THE PLANT’S UKRAINIAN STAFF",
             "russian": "THE PLANT’S STAFF UNDER ROSATOM, ROSATOM, ROSSETI"}


# ---- drawing: masks at the render size, positions in px, widths in px at 1920 times sc

def _p(a):
    return (np.asarray(a, np.float64) * 16).round().astype(np.int32)


def poly(m, pts, w, closed=False, v=255):
    cv2.polylines(m, [_p(pts)], closed, v, max(1, round(w)), cv2.LINE_AA, shift=4)


def dashed(m, pts, on, off, w, closed=False, pattern=None):
    """A polyline drawn as dashes by length along it (pattern: [on, off, on, off, ...] px)."""
    pts = np.asarray(pts, np.float64)
    if closed:
        pts = np.vstack([pts, pts[:1]])
    seg = np.hypot(*np.diff(pts, axis=0).T)
    cum = np.r_[0, np.cumsum(seg)]
    pat = pattern or [on, off]
    s, k = 0.0, 0
    while s < cum[-1]:
        e = min(cum[-1], s + pat[k % len(pat)])
        if k % 2 == 0:
            ts = np.r_[s, cum[(cum > s) & (cum < e)], e]
            xs, ys = np.interp(ts, cum, pts[:, 0]), np.interp(ts, cum, pts[:, 1])
            poly(m, np.stack([xs, ys], 1), w)
        s, k = e, k + 1


def bezier(p0, p1, p2, n=90):
    t = np.linspace(0, 1, n)[:, None]
    return (1 - t) ** 2 * np.asarray(p0) + 2 * (1 - t) * t * np.asarray(p1) + t ** 2 * np.asarray(p2)


def diamond(m, c, r, w):
    x, y = c
    poly(m, [(x, y - r), (x + r, y), (x, y + r), (x - r, y)], w, closed=True)


def at_frac(curve, f):
    cum = np.r_[0, np.cumsum(np.hypot(*np.diff(curve, axis=0).T))]
    s = f * cum[-1]
    return float(np.interp(s, cum, curve[:, 0])), float(np.interp(s, cum, curve[:, 1]))


# ---- the shared picture

def load():
    B = V5.build(V5.W_RENDER)
    spec = yaml.safe_load((V5.HERE / "repairs.yaml").read_text())
    reps = sorted(spec["repairs"], key=lambda p: (str(p["when"]), p["id"]))
    Text.n = len(reps)
    return B, reps


def rings_frame(B, dim=None):
    """The map with every ring at its last-frame strength (dim: repair id -> factor)."""
    fr = B["base"].copy()
    by_layer = {}
    for rg in B["regions"].values():
        if rg["repairs"]:
            by_layer[rg["leader"]] = 0.0          # the label's leader is drawn per option
    for e in B["events"]:
        if "ring" in e:
            by_layer[e["ring"]] = V5.ring_level(V5.T_STILL, e["t"]) * ((dim or {}).get(e["id"], 1.0))
    for i, f in by_layer.items():
        if f > 0:
            L = B["layers"][i]
            y0, y1, x0, x1 = L["box"]
            fr[y0:y1, x0:x1] += (L["rgb"] - fr[y0:y1, x0:x1]) * (L["a"] * L["peak"] * f)[..., None]
    return fr


class Text:
    """The overlay's texts, as pass 5 sets them."""

    def __init__(self, B):
        self.B, self.ov = B, B["film"].ov
        sc = self.sc = B["film"].sc
        self.f_head = zoomout._hn(round(50 * sc), 0)
        self.f_sub = zoomout._hn(round(13 * sc), 10)
        self.f_tag = zoomout._hn(round(12 * sc), 1)
        self.f_tiny = zoomout._hn(round(10.5 * sc), 10)
        self.tk, self.pad = 0.06 * 12 * sc, (round(6 * sc), round(4 * sc))
        self.ov.clear()

    n = 0   # every counted repair (load)

    def head(self, at=None, lines=None, sub=None):
        sc, W = self.sc, self.B["W"]
        lines = lines or (f"{self.n} repairs to the", "plant’s power lines", "since March 2022")
        at = at or (W - 470 * sc, 40 * sc)
        items = [((0, k * 56 * sc), s, self.f_head, "lt", 0, 1.0) for k, s in enumerate(lines)]
        self.ov.label(items, at, 1.0, (0, 0), box=False)
        if sub:
            y = len(lines) * 56 * sc + 18 * sc
            for k, s in enumerate(sub):
                self.ov.label([((0, 0), s, self.f_sub, "lt", 0.4 * sc, 1.0)], (at[0] + 2 * sc, at[1] + y + k * 19 * sc),
                              0.85, (0, 0), box=False)

    def tag(self, text, at, anchor="lm", op=1.0, box=True):
        return self.ov.label([((0, 0), text, self.f_tag, anchor, self.tk, 1.0)], at, op, self.pad, box=box)

    def tiny(self, text, at, anchor="lb", op=0.42):
        return self.ov.label([((0, 0), text, self.f_tiny, anchor, 0.8 * self.sc, 1.0)], at, op, (0, 0), box=False)

    def plant(self):
        cx, cy = self.B["to_px"](np.zeros((1, 2)))[0]
        self.tag("ZAPORIZHZHIA NPP", (cx - 12 * self.sc, cy), "rm")
        self.ov.dot((cx, cy), 3.5 * self.sc, 1.0)

    def areas(self, counts=True):
        """Each area's label with its count, and the dot its leader ends at (an area, never a place of work)."""
        sc = self.sc
        for rg in self.B["regions"].values():
            if not rg["repairs"]:
                continue
            box = self.tag(f"{V5.LABEL[rg['id']][0]}" + (f" ({len(rg['repairs'])})" if counts else ""), rg["label_at"],
                           rg["label"].get("anchor", "l") + "m")
            x, y = rg["centroid_px"]
            bx, by = min(max(x, box[0]), box[2]), min(max(y, box[1]), box[3])
            if math.hypot(bx - x, by - y) > 8 * sc:
                self.ov.line((x, y), (bx, by), 0.85)
            self.ov.disc((x, y), 2.6 * sc, 1.0)

    def credit(self, y_note=None):
        sc, H = self.sc, self.B["H"]
        self.tiny(self.B["credit"], (24 * sc, H - 11 * sc))

    def onto(self, fr):
        return np.clip(self.ov.onto(fr), 0, 255).astype(np.uint8)


def timeline(B, T, fr, x_a=None, y_tl=None, lanes=None):
    """Pass 5's bar: the axis, the years, a tick per repair (placed white and taller, unplaced grey)."""
    sc, W, H = B["film"].sc, B["W"], B["H"]
    x_a, x_b = (x_a or 24) * sc, W - 24 * sc
    y_tl = y_tl or H - 66 * sc
    span = (V5.AXIS[1] - V5.AXIS[0]).days
    x_of = lambda d: x_a + (d - V5.AXIS[0]).days / span * (x_b - x_a)
    return x_of, x_a, x_b, y_tl


def legend(B, T, fr, items, y=None, x=None):
    """A key in the bar: a short sample of each mark, then its words."""
    sc, H = B["film"].sc, B["H"]
    x = (x or 24) * sc
    y = y or H - 30 * sc
    m = np.zeros(fr.shape[:2], np.uint8)
    for kind, text in items:
        if kind == "solid":
            poly(m, [(x, y), (x + 22 * sc, y)], LINK_W * sc)
            x += 28 * sc
        elif kind == "dotted":
            dashed(m, [(x, y), (x + 22 * sc, y)], DOT_ON * sc, DOT_OFF * sc, LINK_W * sc)
            x += 28 * sc
        elif kind == "dashed":
            dashed(m, [(x, y), (x + 22 * sc, y)], DASH_ON * sc, DASH_OFF * sc, LINK_W * sc)
            x += 28 * sc
        elif kind == "dashdot":
            dashed(m, [(x, y), (x + 22 * sc, y)], 0, 0, LINK_W * sc, pattern=[6 * sc, 2.5 * sc, 1.2 * sc, 2.5 * sc])
            x += 28 * sc
        elif kind == "diamond":
            diamond(m, (x + 4 * sc, y), 3.6 * sc, 0.9 * sc)
            x += 13 * sc
        box = T.tiny(text, (x, y + 3.5 * sc), "lm", 0.75)
        x = box[2] + 16 * sc
    _blend(fr, m.astype(np.float32) / 255 * 0.85, WHITE)


def ticks(B, T, fr, reps, x_of, y_tl, years=True):
    sc = B["film"].sc
    m = np.zeros(fr.shape[:2], np.uint8)
    g = np.zeros_like(m)
    poly(m, [(x_of(V5.AXIS[0]), y_tl), (x_of(V5.AXIS[1]), y_tl)], 0.8 * sc, v=100)
    used = []
    for rp in reps:
        xx = x_of(V2._date(rp))
        while any(abs(xx - u) < 2.5 * sc for u in used):
            xx += 2.5 * sc
        used.append(xx)
        h = (14 if rp.get("region") else 7) * sc
        poly(m if rp.get("region") else g, [(xx, y_tl - 1.5 * sc), (xx, y_tl - h)], 1.2 * sc)
    _blend(fr, m.astype(np.float32) / 255 * 0.95, WHITE)
    _blend(fr, g.astype(np.float32) / 255 * 0.42, WHITE)
    if years:
        T.tiny("2022", (x_of(V5.AXIS[0]), y_tl + 7 * sc), "lt", 0.5)
        for yr in range(2023, 2027):
            T.tiny(str(yr), (x_of(date(yr, 1, 1)), y_tl + 7 * sc), "lt", 0.5)


def tally(reps):
    c = Counter(r["side"] for r in reps)
    return c, (f"{c['ukrainian']} BY UKRAINIAN CREWS · {c['russian']} BY THE RUSSIAN SIDE · {c['both']} BY BOTH · "
               f"{c['unknown']} NOT SAID")


def truce_of(rp):
    return bool(rp.get("arranged_by"))


# ---- C: a network diagram, no map

def option_c(B, reps):
    sc, W, H = B["film"].sc, B["W"], B["H"]
    fr = np.empty((H, W, 3), np.float32)
    fr[:] = V5.GROUND_RGB
    fr[H - round(46 * sc):] = 0
    T = Text(B)
    c, _ = tally(reps)
    y_ax, x0, x1 = 560 * sc, 140 * sc, W - 140 * sc
    span = (V5.AXIS[1] - V5.AXIS[0]).days
    x_of = lambda d: x0 + (d - V5.AXIS[0]).days / span * (x1 - x0)
    actors = {"ukrainian": (W * 0.3, 300 * sc), "russian": (W * 0.66, 300 * sc)}
    iaea = (W * 0.88, 300 * sc)
    order = ["dn-north", "fe-north", "dn-crossing", "dn-occupied", "fe-south", "switchyards", None]
    names = {"dn-north": "DNIPROVSKA, NORTH", "fe-north": "FEROSPLAVNA-1, NORTH", "dn-crossing": "DNIPROVSKA, CROSSING",
             "dn-occupied": "DNIPROVSKA, OCCUPIED SIDE", "fe-south": "FEROSPLAVNA-1, SOUTH BANK",
             "switchyards": "THE SWITCHYARDS", None: "NO PLACE PUBLISHED"}
    places = {k: (x0 + (i + 0.5) / len(order) * (x1 - x0), 850 * sc) for i, k in enumerate(order)}
    pos, used = {}, []
    for rp in reps:
        x = x_of(V2._date(rp))
        while any(abs(x - q) < 7 * sc for q in used):
            x += 7 * sc
        used.append(x)
        pos[rp["id"]] = (x, y_ax)
    m = np.zeros((H, W), np.uint8)
    d = np.zeros_like(m)
    nodes = np.zeros_like(m)
    poly(nodes, [(x0, y_ax), (x1, y_ax)], 0.8 * sc, v=90)

    def arc(p, q, bend):
        mid = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
        dx, dy = q[0] - p[0], q[1] - p[1]
        L = math.hypot(dx, dy) or 1
        return bezier(p, (mid[0] - dy / L * bend * L, mid[1] + dx / L * bend * L), q)

    for rp in reps:
        p = pos[rp["id"]]
        sides = ["ukrainian", "russian"] if rp["side"] == "both" else [rp["side"]]
        for s in sides:
            if s == "unknown":
                dashed(d, [(p[0], p[1] - 6 * sc), (p[0], p[1] - 70 * sc)], DOT_ON * sc, DOT_OFF * sc, LINK_W * sc)
            else:
                poly(m, arc(actors[s], p, 0.12 if p[0] > actors[s][0] else -0.12), LINK_W * sc)
        if truce_of(rp):
            dashed(m, arc(iaea, p, -0.18), DASH_ON * 0.6 * sc, DASH_OFF * sc, 0.7 * sc)
        q = places[rp.get("region")]
        poly(m, arc(p, q, 0.1 if q[0] > p[0] else -0.1), LINK_W * sc)
        cv2.circle(nodes, tuple(_p(p)), round(3.2 * sc * 16), 255, -1 if rp.get("region") else max(1, round(sc)),
                   cv2.LINE_AA, shift=4)
    for xy in list(actors.values()) + [iaea] + list(places.values()):
        cv2.circle(nodes, tuple(_p(xy)), round(5 * sc * 16), 255, -1, cv2.LINE_AA, shift=4)
    _blend(fr, m.astype(np.float32) / 255 * 0.42, WHITE)
    _blend(fr, d.astype(np.float32) / 255 * 0.7, WHITE)
    _blend(fr, nodes.astype(np.float32) / 255, WHITE)
    for s, xy in actors.items():
        T.tag(f"{SIDE_TEXT[s]} ({c[s]})", (xy[0], xy[1] - 22 * sc), "mm")
        if s in SIDE_FULL:
            T.tiny(SIDE_FULL[s], (xy[0], xy[1] - 42 * sc), "mm", 0.55)
    T.tag(f"THE IAEA BROKERED ({sum(map(truce_of, reps))})", (iaea[0], iaea[1] - 22 * sc), "mm")
    T.tiny("IT NEVER REPAIRED", (iaea[0], iaea[1] - 42 * sc), "mm", 0.55)
    T.tiny(f"NOT SAID ({c['unknown']}): A DOTTED STUB, NO ACTOR · BOTH SIDES ({c['both']}): AN ARC FROM EACH",
           (x0, y_ax - 110 * sc), "lm", 0.6)
    for i, (k, xy) in enumerate(places.items()):
        n = sum(1 for r in reps if r.get("region") == k)
        T.tag(f"{names[k]} ({n})", (xy[0], xy[1] + (18 if i % 2 == 0 else 44) * sc), "mt")
    T.tiny("2022", (x_of(V5.AXIS[0]), y_ax + 10 * sc), "lt", 0.5)
    for yr in range(2023, 2027):
        T.tiny(str(yr), (x_of(date(yr, 1, 1)), y_ax + 10 * sc), "lt", 0.5)
    T.head(at=(40 * sc, 40 * sc), lines=(f"{len(reps)} repairs to the plant’s power lines since March 2022",))
    T.tiny("A DIAGRAM, NOT A MAP: POSITIONS ARE NOT PLACES · A FILLED DOT: A REPAIR WHOSE PLACE WAS PUBLISHED, AS AN AREA "
           "· DASHED: BROKERED BY THE IAEA · " + "SOURCES: REPAIRS.YAML, SIDES/WHO_REPAIRED.MD", (24 * sc, H - 18 * sc))
    return T.onto(fr), {"actors": list(actors), "places": [k or "none" for k in order]}


# ---- E: the side in the rings

def option_e(B, reps):
    sc, W, H = B["film"].sc, B["W"], B["H"]
    fr = rings_frame(B, dim={r["id"]: 0.0 for r in reps})       # the map without pass 5's rings
    T = Text(B)
    gap = V5.RING_GAP * sc
    m = np.zeros((H, W), np.uint8)
    marks = np.zeros_like(m)
    for rg in B["regions"].values():
        base = (rg["mask"] > 127).astype(np.uint8)
        for k, rp in enumerate(rg["repairs"]):
            r = round(k * gap)
            mm = cv2.erode(base, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))) if r else base
            for cnt in cv2.findContours(mm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[0]:
                pts = cnt[:, 0].astype(np.float64)
                w = V5.RING_W * sc
                if rp["side"] == "ukrainian":
                    poly(m, pts, w, closed=True)
                elif rp["side"] == "russian":
                    dashed(m, pts, DASH_ON * sc, DASH_OFF * sc, w, closed=True)
                elif rp["side"] == "both":
                    dashed(m, pts, 0, 0, w, closed=True, pattern=[6 * sc, 2.5 * sc, 1.2 * sc, 2.5 * sc])
                else:
                    dashed(m, pts, DOT_ON * sc, DOT_OFF * sc, w, closed=True)
                if truce_of(rp) and len(pts):
                    top = pts[np.argmin(pts[:, 1])]
                    diamond(marks, (top[0] + 9 * sc * (k % 3), top[1]), 3.4 * sc, 0.9 * sc)
    _blend(fr, m.astype(np.float32) / 255 * 0.85, WHITE)
    _blend(fr, marks.astype(np.float32) / 255 * 0.9, WHITE)
    x_of, x_a, x_b, y_tl = timeline(B, T, fr)
    ticks(B, T, fr, reps, x_of, y_tl)
    T.head(sub=[tally(reps)[1].rsplit(" · ", 1)[0], f"{tally(reps)[0]['unknown']} NOT SAID · {sum(1 for r in reps if not r.get('region'))} WITH NO PLACE PUBLISHED, NOT DRAWN"])
    T.plant()
    T.areas()
    legend(B, T, fr, [("solid", "UKRAINIAN CREWS"), ("dashed", "THE RUSSIAN SIDE"), ("dashdot", "BOTH"),
                      ("dotted", "NOT SAID"), ("diamond", "UNDER A CEASEFIRE THE IAEA BROKERED"),
                      (None, "ONE RING PER REPAIR, EACH AREA AS WIDE AS ITS SOURCE SAYS")])
    T.credit()
    return T.onto(fr), {"rings": "styled by side"}


OPTIONS = {"C": option_c, "E": option_e}


def main(which):
    OUT.mkdir(exist_ok=True)
    B, reps = load()
    made = {}
    for k in which:
        img, info = OPTIONS[k](B, reps)
        Image.fromarray(V5.half(img)).save(OUT / f"sides_{k}_1920.jpg", quality=92)
        made[k] = {"jpg": f"sides_{k}_1920.jpg", **info}
        print(OUT / f"sides_{k}_1920.jpg")
    rec = OUT / "sides.json"
    doc = json.loads(rec.read_text()) if rec.exists() else {}
    c, line = tally(reps)
    doc.update({"made_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "made_by": "research_notes/Repair regions still/scripts/repair_sides.py",
                "asked": "The user, 8 November 2026: options A-E for who repaired, as stills, before the animation",
                "counts": dict(c), "tally": line, "under_ceasefires": sum(map(truce_of, reps)),
                "data": "repairs.yaml side / side_basis / worked_on / arranged_by (sides/who_repaired.md)",
                "safety": "no link starts at a place: the sides are nodes of a diagram with no map (C); the areas are pass 5's",
                "options": {**doc.get("options", {}), **made}})
    rec.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    sheet()


KEPT = ["C", "C1", "C2", "E"]   # the options still in play (repair_sides_c.py makes C1, C2)


def sheet():
    """The kept options side by side, two to a row."""
    have = [k for k in KEPT if (OUT / f"sides_{k}_1920.jpg").exists()]
    img = Image.new("RGB", (1920, 540 * ((len(have) + 1) // 2)), (0, 0, 0))
    for i, k in enumerate(have):
        img.paste(Image.open(OUT / f"sides_{k}_1920.jpg").resize((960, 540), Image.LANCZOS), ((i % 2) * 960, (i // 2) * 540))
    img.save(OUT / "sides_sheet.jpg", quality=88)


if __name__ == "__main__":
    main(sys.argv[1:] or list(OPTIONS))
