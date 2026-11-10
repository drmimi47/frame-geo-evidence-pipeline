"""Who repaired the lines: still prototypes of the next ideas (the user, 8 November 2026: "please test out these new
ideas using still frame prototypes", after keeping E, C, C1 and C2).

E2  the rings ordered by side: all solid, the Ukrainian outermost, a gap, then the Russian; both doubled, not said faint
E3  the rings by brightness: Ukrainian white, the Russian side grey, not said faint; both doubled; in date order
E4  split rings: a Ukrainian repair drawn on its area's north half, a Russian one on the south half, both whole
W   waiting bars: each repair a bar from the cut to the line back (the cut as the dataset's `what` gives it)
ST  a space-time stack: pass 5's map tilted, each repair's ring lifted by its date over its area
U   a unit chart: one square per repair, grouped by side, then by line (the animation moves between them)
Q   the sources' own words: one line per repair, as the source put it, grouped by side
P   a punch card: the areas by month, a mark per repair

Every fact is repairs.yaml's (sides/who_repaired.md, sides/new_repairs_check.md). The areas are pass 5's; no repair is
a point. Ceasefire repairs (`arranged_by`) are marked in each. Prototypes: stills only.

    .venv/bin/python -I "research_notes/Repair regions still/scripts/repair_sides_more.py" [E2 E3 E4 W ST U Q P]
"""

from __future__ import annotations

import json
import math
import re
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
import repair_sides_c as SC  # noqa: E402
from repair_sides import DOT_OFF, DOT_ON, SIDE_TEXT, WHITE, dashed, poly  # noqa: E402

from image_evidence.satellite import zoomout  # noqa: E402
from image_evidence.satellite.zoomout import _blend  # noqa: E402

OUT = S.OUT
GREY = (150, 150, 152)            # E3, W, ST: the Russian side
SIDE_RGB = {"ukrainian": WHITE, "russian": GREY, "both": WHITE, "unknown": (110, 110, 112)}
SIDE_A = {"ukrainian": 0.9, "russian": 0.95, "both": 0.9, "unknown": 0.55}
ORDER = ["ukrainian", "both", "unknown", "russian"]     # E2: outermost first

# W: when each line went down, as the dataset's `what` says (approx: the source gives only a part of a month);
# missing: no cut date published
CUT = {
    "R03": ("2022-08-22", 0), "R04": ("2022-08-25", 0), "R05a": ("2022-09-05", 0), "R07": ("2022-10-08", 0),
    "R08": ("2022-10-12", 0), "R11": ("2022-11-02", 0), "R11b": ("2022-11-02", 0), "R13": ("2022-12-29", 0),
    "R15": ("2023-03-01", 0), "R16": ("2023-03-09", 0), "R17": ("2023-05-22", 0), "R19": ("2023-11-26", 0),
    "R20": ("2023-12-01", 0), "R21": ("2024-02-20", 0), "R23": ("2024-04-04", 0), "R27": ("2024-10-21", 0),
    "R33": ("2025-02-01", 1), "R34": ("2025-07-04", 0), "R35f": ("2025-05-01", 1), "R35d": ("2025-09-23", 0),
    "R36": ("2025-10-30", 1), "R37": ("2025-11-14", 0), "R39": ("2025-12-15", 1), "R40": ("2026-01-02", 0),
    "R41": ("2026-02-10", 0), "R44": ("2026-06-10", 0), "R45": ("2026-03-24", 0), "R46": ("2026-08-20", 0),
    "R48": ("2026-09-19", 0),
}

# Q: the sources' words (sides/who_repaired.md's key quotes; R48 from new_repairs_check.md); the English is the
# source's own or, for Ukrainian and Russian, the translation given there
QUOTES = {
    "R01": ("«Ремонтники НЕК «Укренерго» відновили високовольтну лінію 750 кВ Запорізька АЕС – Каховська»", "Ukrenergo's repair crews restored the 750 kV ZNPP–Kakhovska line", "Ministry of Energy"),
    "R02": ("", "Ukraine informed the IAEA about the restoration of a power line", "IAEA"),
    "R03": ("", "a disconnection ... before it was restored later the same day", "IAEA"),
    "R04": ("«НЕК \"Укренерго\" відновила роботу двох пошкоджених ... магістральних ліній»", "Ukrenergo restored two main lines damaged by Russian shelling", "Interfax-Ukraine"),
    "R05a": ("", "plant operators and engineers have been able to restore one of the reserve power lines", "IAEA"),
    "R05b": ("", "Ukrainian engineers have made further headway in repairing vital power infrastructure", "IAEA"),
    "R06": ("", "engineers repaired one of the four main external power lines", "IAEA"),
    "R07": ("«Українські фахівці відремонтували та ввели в роботу ... 750 кВ ЗАЕС - Дніпровська»", "Ukrainian specialists repaired and reconnected the line", "Energoatom, via Espreso"),
    "R08": ("«Українські фахівці знайшли технічне рішення, як відновити роботу лінії зв'язку»", "Ukrainian specialists found a technical solution to restore the line", "Energoatom"),
    "R09": ("", "(no repairer named: the plant's staff told the IAEA that power was back)", "IAEA"),
    "R10": ("", "Ukrainian engineers have managed to restore back-up power", "IAEA"),
    "R11": ("«фахівці відремонтували обидві зовнішні лінії»", "specialists repaired both external lines", "Espreso"),
    "R11b": ("«фахівці відремонтували обидві зовнішні лінії»", "specialists repaired both external lines (as R11)", "Espreso"),
    "R12": ("", "now restored", "OECD-NEA"),
    "R13": ("", "work to repair the line is already under way", "IAEA"),
    "R15": ("«Укренерго вкотре повернуло в роботу одну з ліній»", "Ukrenergo once again returned one of the lines to service", "Espreso"),
    "R16": ("«Щойно буде можливість і дозвіл військових, одразу розпочнеться відновлення»", "as soon as there is an opportunity and the military's permission, the repair starts", "Mind.ua"),
    "R17": ("«\"Укренерго\" доклало максимум зусиль і відновило живлення атомної станції»", "Ukrenergo did its utmost and restored the plant's supply", "ArmyInform"),
    "R19": ("«Пошкоджену лінію 750 кВ українські фахівці відремонтували о 20:52»", "Ukrainian specialists repaired the damaged 750 kV line at 20:52", "Interfax-Ukraine"),
    "R20": ("", "Ukrenergo has restored a high-voltage line", "Ukrinform"),
    "R21": ("«Військові пускають наших хлопців працювати лише на 2-2,5 години»", "the military let our men work only 2-2.5 hours", "Ukrinform"),
    "R23": ("«зусиллями українських фахівців»", "through the efforts of Ukrainian specialists", "Espreso"),
    "R25": ("«Ремонтні бригади чекали дозволу військовослужбовців»", "the repair crews waited for the soldiers' permission", "Kyiv Post"),
    "R26": ("«Ремонтні бригади понад добу чекали дозволу для того, щоб почати ремонт»", "the repair crews waited more than a day for permission to start", "Espreso"),
    "R27": ("«Ремонтні бригади НЕК \"Укренерго\" відновили лінію живлення»", "Ukrenergo's crews restored the line", "Ukrinform"),
    "R29": ("«Енергетики почали відновлювальні роботи одразу після дозволів від військових»", "energy workers started repairs right after the military's permission", "Kyiv Post"),
    "R30": ("", "the voltage stabilizer ... located in an open switchyard outside the plant, was being repaired", "IAEA"),
    "R32": ("", "once again available after it was lost for around a week", "IAEA"),
    "R33": ("«Линия введена по итогам проведенных восстановительных работ»", "the line was put in after restoration work", "the plant's channel"),
    "R34": ("«Фахівці НЕК \"Укренерго\" відновили роботу високовольтної лінії»", "Ukrenergo's specialists restored the line", "Interfax-Ukraine"),
    "R35d": ("«Персонал Запорожской АЭС совместно со специалистами компании «Россети» приступил к ремонтно-восстановительным работам»", "the ZNPP's staff with Rosseti specialists began repair work", "the plant's channel"),
    "R35f": ("«Українські фахівці відновлюють лінії електропостачання ...»", "Ukrainian specialists are restoring the lines that feed the ZNPP", "Kyiv Post"),
    "R36": ("", "Technicians repaired a damaged cable ... with an IAEA team monitoring their work", "IAEA"),
    "R37": ("", "Following repairs ... the line was restored (the plant's channel: a protection trip, no repair)", "IAEA"),
    "R39": ("«Ремонтные мероприятия проводились совместными усилиями специалистов ЗАЭС и компании «Россети»»", "the repair was done by the ZNPP's and Rosseti's specialists together", "the plant's channel"),
    "R40": ("«Украинская ремонтная бригада выполняет восстановление линии»", "a Ukrainian repair crew is restoring the line", "Profile.ru"),
    "R41": ("«Специалисты Госкорпорации «Росатом» начали ремонтно-восстановительные работы»", "Rosatom specialists began repair work at the thermal plant's open switchyard", "the plant's channel"),
    "R44": ("", "An IAEA team observed the repair activities on 13 June", "IAEA"),
    "R45": ("«с российской стороны инфраструктура полностью восстановлена»", "on the Russian side the infrastructure is fully restored", "the plant's channel"),
    "R45b": ("", "At the ZTPP, repairs were completed both on switchyard equipment and on a back-up transmission line", "IAEA"),
    "R46": ("«Саме українські фахівці ... виконали потрібні роботи»", "it was Ukrainian specialists who did the work", "Energoatom, via Fakty"),
    "R48": ("«Наши специалисты сейчас выходят и начинают ремонт»", "our specialists are going out now to start the repair", "Likhachev, Rosatom"),
}
ACTOR_WORDS = r"(Укренерго|Ukrenergo|[Уу]країнськ\w*|Ukrainian|Росатом\w*|Rosatom|Россети|Rosseti|ЗАЭС|ZNPP's staff|ZNPP's and Rosseti's|Персонал|plant operators|engineers|specialists|фахівці|Ремонтні бригади|Ремонтники|Енергетики|energy workers|Technicians|Наши специалисты|our specialists|IAEA team|Украинская ремонтная бригада)"


def d_of(s):
    return date.fromisoformat(s)


# ---- the rings, shared by E2, E3, E4

def contours(rg, k, sc):
    base = (rg["mask"] > 127).astype(np.uint8)
    r = round(k * V5.RING_GAP * sc)
    m = cv2.erode(base, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))) if r else base
    return [c[:, 0].astype(np.float64) for c in cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[0]]


def north_half(rg, pts, H):
    """True where a ring's point lies on its area's north side: above the line's stretch (a band) or the centre."""
    if "xy" not in rg:
        ys, xs = np.nonzero(rg["mask"] > 127)
        return pts[:, 1] <= ys.mean()
    s = rg["_px"]
    d = ((pts[:, None, :] - s[None, :, :]) ** 2).sum(-1)
    j = d.argmin(1)
    j0, j1 = np.clip(j - 1, 0, len(s) - 1), np.clip(j + 1, 0, len(s) - 1)
    t = s[j1] - s[j0]
    v = pts - s[j]
    cross = t[:, 0] * v[:, 1] - t[:, 1] * v[:, 0]
    side = cross > 0
    north_is = (pts[side, 1].mean() if side.any() else 0) < (pts[~side, 1].mean() if (~side).any() else 0)
    return side if north_is else ~side


def runs(mask):
    """Contiguous runs of True in a closed ring, as index arrays."""
    if mask.all():
        return [np.arange(len(mask))]
    start = int(np.argmin(mask))           # a False point: the runs never wrap past it
    idx = np.roll(np.arange(len(mask)), -start)
    m = mask[idx]
    out, cur = [], []
    for i, v in zip(idx, m):
        if v:
            cur.append(i)
        elif cur:
            out.append(np.array(cur))
            cur = []
    if cur:
        out.append(np.array(cur))
    return out


def ring_option(B, reps, style):
    sc, W, H = B["film"].sc, B["W"], B["H"]
    fr = S.rings_frame(B, dim={r["id"]: 0.0 for r in reps})
    T = S.Text(B)
    lay = {k: np.zeros((H, W), np.uint8) for k in SIDE_RGB}
    for rg in B["regions"].values():
        rs = sorted(rg["repairs"], key=lambda p: str(p["when"]))
        if not rs:
            continue
        if "xy" in rg:
            rg["_px"] = B["to_px"](rg["xy"])
        if style == "E2":
            rs = sorted(rs, key=lambda p: (ORDER.index(p["side"]), str(p["when"])))
        k = 0.0
        prev = None
        for rp in rs:
            if style == "E2" and prev is not None and rp["side"] != prev:
                k += 1.2                                   # the gap between the sides
            prev = rp["side"]
            w = (1.7 if S.truce_of(rp) else 1.0) * sc
            s = rp["side"] if style != "E2" else ("unknown" if rp["side"] == "unknown" else "ukrainian")
            for pts in contours(rg, k, sc):
                if style == "E4" and rp["side"] in ("ukrainian", "russian"):
                    nh = north_half(rg, pts, H)
                    want = nh if rp["side"] == "ukrainian" else ~nh
                    for run in runs(want):
                        if len(run) > 3:
                            poly(lay["ukrainian"], pts[run], w)
                elif style == "E4" and rp["side"] == "unknown":
                    dashed(lay["unknown"], pts, DOT_ON * sc, DOT_OFF * sc, w, closed=True)
                else:
                    poly(lay[s if style == "E3" else ("unknown" if s == "unknown" else "ukrainian")], pts, w, closed=True)
            if rp["side"] == "both":                        # doubled
                for pts in contours(rg, k + 0.45, sc):
                    poly(lay["ukrainian"], pts, 0.8 * sc, closed=True)
                k += 0.45
            k += 1
    for s, m in lay.items():
        _blend(fr, m.astype(np.float32) / 255 * SIDE_A[s], SIDE_RGB[s])
    x_of, x_a, x_b, y_tl = S.timeline(B, T, fr)
    S.ticks(B, T, fr, reps, x_of, y_tl)
    c, line = S.tally(reps)
    T.head(sub=[line.rsplit(" · ", 1)[0], f"{c['unknown']} NOT SAID · {sum(1 for r in reps if not r.get('region'))} "
                "WITH NO PLACE PUBLISHED, NOT DRAWN"])
    T.plant()
    area_labels(T, B)
    key = {"E2": "ALL RINGS SOLID · OUTSIDE: UKRAINIAN CREWS · AFTER THE GAP: THE RUSSIAN SIDE · DOUBLED: BOTH · FAINT: NOT SAID",
           "E3": "WHITE: UKRAINIAN CREWS · GREY: THE RUSSIAN SIDE · DOUBLED: BOTH · FAINT: NOT SAID",
           "E4": "NORTH HALF: UKRAINIAN CREWS · SOUTH HALF: THE RUSSIAN SIDE · WHOLE, DOUBLED: BOTH · DOTTED: NOT SAID"}[style]
    S.legend(B, T, fr, [(None, key + " · HEAVIER: UNDER AN IAEA-BROKERED CEASEFIRE")])
    T.credit()
    return T.onto(fr)


def area_labels(T, B):
    """Pass 5's labels, each with the split by side under it."""
    sc = T.sc
    for rg in B["regions"].values():
        rs = rg["repairs"]
        if not rs:
            continue
        box = T.tag(f"{V5.LABEL[rg['id']][0]} ({len(rs)})", rg["label_at"], rg["label"].get("anchor", "l") + "m")
        parts = [f"{sum(1 for r in rs if r['side'] == s)} {w}" for s, w in
                 (("ukrainian", "UKRAINIAN"), ("russian", "RUSSIAN SIDE"), ("both", "BOTH"), ("unknown", "NOT SAID"))
                 if any(r["side"] == s for r in rs)]
        T.tiny(" · ".join(parts), (box[0] + 6 * sc, box[3] + 10 * sc), "lm", 0.75)
        x, y = rg["centroid_px"]
        bx, by = min(max(x, box[0]), box[2]), min(max(y, box[1]), box[3])
        if math.hypot(bx - x, by - y) > 8 * sc:
            T.ov.line((x, y), (bx, by), 0.85)
        T.ov.disc((x, y), 2.6 * sc, 1.0)


# ---- W: waiting bars

def option_w(B, reps):
    cv = SC.Canvas(B)
    T = S.Text(B)
    sc, W, H = cv.sc, cv.W, cv.H
    x0, x1 = 170 * sc, W - 60 * sc
    span = (V5.AXIS[1] - V5.AXIS[0]).days
    x_of = lambda d: x0 + (d - V5.AXIS[0]).days / span * (x1 - x0)
    y_mid, step = 590 * sc, 13 * sc
    groups = {"ukrainian": [], "russian": [], "both": [], "unknown": []}
    for r in reps:
        groups[r["side"]].append(r)
    bars = np.zeros((H, W), np.uint8)
    grey = np.zeros_like(bars)
    faint = np.zeros_like(bars)
    for yr in range(2023, 2027):
        x = x_of(date(yr, 1, 1))
        dashed(faint, [(x, 170 * sc), (x, 960 * sc)], 2 * sc, 5 * sc, 0.8 * sc)
        T.tiny(str(yr), (x + 4 * sc, 175 * sc), "lt", 0.5)
    poly(faint, [(x0, y_mid), (x1, y_mid)], 0.9 * sc)
    rows = []
    for i, r in enumerate(groups["ukrainian"]):
        rows.append((r, y_mid - (i + 1.2) * step, bars))
    for i, r in enumerate(groups["both"]):
        rows.append((r, y_mid + 1.2 * step, bars))
    for i, r in enumerate(groups["russian"]):
        rows.append((r, y_mid + (i + 2.4) * step, grey))
    base_u = y_mid + (len(groups["russian"]) + 4.2) * step
    for i, r in enumerate(groups["unknown"]):
        rows.append((r, base_u + i * step, faint))
    labels = []
    for r, y, m in rows:
        end = x_of(V2._date(r))
        h = 3.2 * sc
        if r["id"] in CUT:
            s, approx = CUT[r["id"]]
            start = x_of(d_of(s))
            ww = max(end - start, 2.5 * sc)
            if r["side"] == "unknown":
                dashed(m, [(end - ww, y), (end, y)], 2 * sc, 2 * sc, 2 * h)
            else:
                cv2.rectangle(m, tuple(S._p((end - ww, y - h))), tuple(S._p((end, y + h))), 255, -1, cv2.LINE_AA, shift=4)
            if approx:                                         # the start only to the month: its first stretch faded
                cv2.rectangle(m, tuple(S._p((end - ww, y - h))), tuple(S._p((end - ww + min(ww, 10 * sc), y + h))), 90,
                              -1, cv2.LINE_AA, shift=4)
            if S.truce_of(r):                                  # a ceasefire: a mark at the end
                poly(cv.m["node"], [(end + 3 * sc, y - 5 * sc), (end + 3 * sc, y + 5 * sc)], 1.2 * sc)
            if (end - start) > 60 * sc:
                labels.append((r, end, y, (V2._date(r) - d_of(s)).days))
        else:                                                   # no cut date published: the repair's day only
            cv2.circle(m, tuple(S._p((end, y))), round(2.6 * sc * 16), 255, max(1, round(sc)), cv2.LINE_AA, shift=4)
    _blend(cv.fr, faint.astype(np.float32) / 255 * 0.55, WHITE)
    _blend(cv.fr, bars.astype(np.float32) / 255 * 0.92, WHITE)
    _blend(cv.fr, grey.astype(np.float32) / 255 * 0.95, GREY)
    fr = cv.finish()
    names = {"fero": "FEROSPLAVNA-1", "dnip": "DNIPROVSKA", "yards": "THE SWITCHYARDS", "kakh": "KAKHOVSKA 750 KV"}
    for r, end, y, days in labels:
        extra = " · NEVER RECONNECTED" if r["id"] == "R45" else ""
        text = f"{names[SC.line_of(r)]} · {days} DAYS{extra}"
        if end + 8 * sc + T.f_tiny.getlength(text) > W - 24 * sc:      # no room after the bar: inside it, at its end
            T.tiny(text, (end - 8 * sc, y - 9 * sc), "rm", 0.8)
        else:
            T.tiny(text, (end + 8 * sc, y + 3.5 * sc), "lm", 0.8)
    c, _ = S.tally(reps)
    T.tag(f"UKRAINIAN CREWS ({c['ukrainian']})", (24 * sc, y_mid - 40 * sc), "lm")
    T.tag(f"BOTH ({c['both']})", (24 * sc, y_mid + 1.2 * step + 3 * sc), "lm")
    T.tag(f"THE RUSSIAN SIDE ({c['russian']})", (24 * sc, y_mid + 4.5 * step), "lm")
    T.tag(f"NOT SAID ({c['unknown']})", (24 * sc, base_u + 2.5 * step), "lm")
    T.head(at=(40 * sc, 40 * sc), lines=(f"{len(reps)} repairs: from the cut to the line back",))
    SC.foot(T, cv, "EACH BAR FROM WHEN THE LINE WENT DOWN TO THE REPAIR, AS THE SOURCES GIVE THEM (FADED: ONLY THE MONTH "
                   "GIVEN) · A RING: NO CUT DATE PUBLISHED · A MARK AT THE END: UNDER AN IAEA-BROKERED CEASEFIRE")
    return T.onto(fr)


# ---- ST: a space-time stack

def option_st(B, reps):
    sc, W, H = B["film"].sc, B["W"], B["H"]
    bar = round(V5.BAR_PX * sc)
    flat = S.rings_frame(B, dim={r["id"]: 0.0 for r in reps})[: H - bar]
    Hm = H - bar
    src = np.float32([[0, 0], [W, 0], [W, Hm], [0, Hm]])
    dst = np.float32([[760, 1240], [3080, 1240], [3600, 2020], [240, 2020]]) * (sc / 2)
    Hm_ = cv2.getPerspectiveTransform(src, dst)
    fr = np.empty((H, W, 3), np.float32)
    fr[:] = V5.GROUND_RGB * 0.8
    warped = cv2.warpPerspective(flat, Hm_, (W, H), flags=cv2.INTER_AREA, borderValue=(0, 0, 0))
    cover = cv2.warpPerspective(np.ones((Hm, W), np.float32), Hm_, (W, H), flags=cv2.INTER_LINEAR)
    fr = fr * (1 - cover[..., None]) + warped * cover[..., None]
    T = S.Text(B)
    proj = lambda pts: cv2.perspectiveTransform(np.asarray(pts, np.float32).reshape(-1, 1, 2), Hm_).reshape(-1, 2)
    zmax = 980 * sc / 2
    z_of = lambda d: SC.frac(d) * zmax
    lay = {k: np.zeros((H, W), np.uint8) for k in SIDE_RGB}
    guide = np.zeros((H, W), np.uint8)
    for rg in B["regions"].values():
        rs = sorted(rg["repairs"], key=lambda p: str(p["when"]))
        if not rs:
            continue
        cxy = proj([rg["centroid_px"]])[0]
        top = z_of(V2._date(rs[-1]))
        dashed(guide, [cxy, cxy - [0, top]], 3 * sc, 3 * sc, 0.8 * sc)
        outline = contours(rg, 0, sc)
        for pts in outline:
            dashed(guide, proj(pts), 4 * sc, 3 * sc, 0.8 * sc, closed=True)
        for k, rp in enumerate(rs):
            z = z_of(V2._date(rp))
            w = (1.6 if S.truce_of(rp) else 1.0) * sc
            for pts in contours(rg, k * 0.3, sc):
                q = proj(pts) - [0, z]
                if rp["side"] == "unknown":
                    dashed(lay["unknown"], q, DOT_ON * sc, DOT_OFF * sc, w, closed=True)
                else:
                    poly(lay[rp["side"]], q, w, closed=True)
    # the repairs with no place: a column of small rings beside the map, by date
    col = np.array([3560, 1180]) * (sc / 2)
    un = [r for r in reps if not r.get("region")]
    for rp in un:
        z = z_of(V2._date(rp))
        cv2.ellipse(lay[rp["side"]], tuple(S._p(col - [0, z])), (round(26 * sc * 16 / 2), round(8 * sc * 16 / 2)), 0, 0, 360,
                    255, max(1, round(sc)), cv2.LINE_AA, shift=4)
    dashed(guide, [col, col - [0, zmax]], 3 * sc, 3 * sc, 0.8 * sc)
    # the time scale: a post at the map's back left corner
    post = dst[0] - [60 * sc / 2, 0]
    poly(guide, [post, post - [0, zmax]], 0.9 * sc)
    for yr in range(2022, 2027):
        z = z_of(V5.AXIS[0] if yr == 2022 else date(yr, 1, 1))
        poly(guide, [post - [6 * sc, z], post - [-6 * sc, z]], 0.9 * sc)
        T.tiny(str(yr), tuple(post - [14 * sc, z]), "rm", 0.6)
    _blend(fr, guide.astype(np.float32) / 255 * 0.45, WHITE)
    for s, m in lay.items():
        _blend(fr, m.astype(np.float32) / 255 * SIDE_A[s], SIDE_RGB[s])
    fr[H - round(46 * sc):] = 0
    T.tiny(f"NO PLACE PUBLISHED ({len(un)})", tuple(col + [0, 24 * sc]), "mm", 0.7)
    for rg in B["regions"].values():
        if rg["repairs"]:
            at = proj([rg["label_at"]])[0]                     # pass 5's label place, tilted with the map
            T.tiny(f"{V5.LABEL[rg['id']][0]} ({len(rg['repairs'])})", tuple(at), rg["label"].get("anchor", "l") + "m", 0.75)
    cx, cy = proj([B["to_px"](np.zeros((1, 2)))[0]])[0]
    T.tag("ZAPORIZHZHIA NPP", (cx - 12 * sc, cy), "rm")
    T.ov.dot((cx, cy), 3.0 * sc, 1.0)
    T.head(at=(40 * sc, 40 * sc), lines=(f"{len(reps)} repairs to the plant’s power lines since March 2022",))
    T.tiny("EACH REPAIR A RING OVER ITS AREA, RAISED BY ITS DATE · WHITE: UKRAINIAN CREWS · GREY: THE RUSSIAN SIDE · "
           "DOTTED: NOT SAID · HEAVIER: AN IAEA-BROKERED CEASEFIRE · THE MAP TILTED, AREAS AS DRAWN, NOT OBSERVED",
           (24 * sc, H - 18 * sc))
    return T.onto(fr)


# ---- U: a unit chart

def option_u(B, reps):
    cv = SC.Canvas(B)
    T = S.Text(B)
    sc, W, H = cv.sc, cv.W, cv.H
    sq, gap = 22 * sc, 7 * sc

    def block(items, x, y, cols):
        pos = {}
        for i, r in enumerate(items):
            pos[r["id"]] = (x + (i % cols) * (sq + gap), y + (i // cols) * (sq + gap))
        return pos

    def draw(pos, by):
        for r in reps:
            x, y = pos[r["id"]]
            m = cv.m["node"]
            if r["side"] == "unknown":
                dashed(m, [(x, y), (x + sq, y), (x + sq, y + sq), (x, y + sq)], 2 * sc, 2.5 * sc, 1.0 * sc, closed=True)
            elif r["side"] == "russian":
                cv2.rectangle(m, tuple(S._p((x, y))), tuple(S._p((x + sq, y + sq))), 255, max(1, round(1.4 * sc)), cv2.LINE_AA,
                              shift=4)
            elif r["side"] == "both":
                cv2.rectangle(m, tuple(S._p((x, y))), tuple(S._p((x + sq, y + sq))), 255, max(1, round(1.4 * sc)), cv2.LINE_AA,
                              shift=4)
                cv2.fillPoly(m, [S._p([(x, y), (x + sq, y), (x, y + sq)])], 255, cv2.LINE_AA, shift=4)
            else:
                cv2.rectangle(m, tuple(S._p((x, y))), tuple(S._p((x + sq, y + sq))), 255, -1, cv2.LINE_AA, shift=4)
            if S.truce_of(r):                                   # a ceasefire: a bar under the square
                poly(cv.m["tick"], [(x, y + sq + 3 * sc), (x + sq, y + sq + 3 * sc)], 1.4 * sc)
            if not r.get("region"):                             # no place published: a small notch in the corner
                cv2.circle(cv.m["arc"], tuple(S._p((x + sq - 4 * sc, y + 4 * sc))), round(1.8 * sc * 16), 255, -1, cv2.LINE_AA,
                           shift=4)

    # left: by side; right: by line (the same squares; the animation moves them)
    sides = [("ukrainian", 9), ("russian", 7), ("both", 1), ("unknown", 7)]
    pos, y = {}, 300 * sc
    for s, cols in sides:
        items = [r for r in reps if r["side"] == s]
        pos.update(block(items, 120 * sc, y, cols))
        T.tag(f"{SIDE_TEXT[s]} ({len(items)})", (120 * sc, y - 18 * sc), "lm")
        y += (math.ceil(len(items) / cols)) * (sq + gap) + 62 * sc
    draw(pos, "side")
    pos2, y = {}, 300 * sc
    for kk, cols in (("fero", 9), ("dnip", 9), ("yards", 9), ("kakh", 9)):
        items = sorted([r for r in reps if SC.line_of(r) == kk], key=lambda r: (ORDER.index(r["side"]), str(r["when"])))
        pos2.update(block(items, 1060 * sc, y, cols))
        T.tag(f"{SC.LINE_NAME[kk]} ({len(items)})", (1060 * sc, y - 18 * sc), "lm")
        y += (math.ceil(len(items) / cols)) * (sq + gap) + 62 * sc
    draw(pos2, "line")
    poly(cv.m["faint"], [(W / 2, 260 * sc), (W / 2, 900 * sc)], 0.9 * sc)
    fr = cv.finish()
    T.tiny("BY WHO DID THE WORK", (120 * sc, 250 * sc), "lm", 0.6)
    T.tiny("THEN THE SAME SQUARES BY LINE", (1060 * sc, 250 * sc), "lm", 0.6)
    T.head(at=(40 * sc, 40 * sc), lines=(f"{len(reps)} repairs to the plant’s power lines since March 2022",))
    SC.foot(T, cv, "ONE SQUARE PER REPAIR, IN DATE ORDER · FILLED: UKRAINIAN CREWS · OUTLINED: THE RUSSIAN SIDE · HALF: BOTH "
                   "· DASHED: NOT SAID · A DOT: NO PLACE PUBLISHED · A BAR UNDER: AN IAEA-BROKERED CEASEFIRE")
    return T.onto(fr)


# ---- Q: the sources' own words

def option_q(B, reps):
    cv = SC.Canvas(B)
    T = S.Text(B)
    sc, W, H = cv.sc, cv.W, cv.H
    f_q = zoomout._hn(round(11 * sc), 0)
    f_qb = zoomout._hn(round(11 * sc), 1)
    f_e = zoomout._hn(round(9.5 * sc), 0)
    cols = [(60 * sc, [r for r in reps if r["side"] == "ukrainian"][:14]),
            (700 * sc, [r for r in reps if r["side"] == "ukrainian"][14:]),
            (1340 * sc, [r for r in reps if r["side"] in ("russian", "both")] + [r for r in reps if r["side"] == "unknown"])]
    heads = [("UKRAINIAN CREWS", 60), ("", 700), ("THE RUSSIAN SIDE · BOTH · THEN NOT SAID", 1340)]
    for t, x in heads:
        if t:
            T.tag(t, (x * sc, 160 * sc), "lm")
    ov = T.ov
    y_step = 54 * sc
    room = {60 * sc: 610 * sc, 700 * sc: 610 * sc, 1340 * sc: W - 1340 * sc - 30 * sc}

    def fit(t, f, w):
        if f.getlength(t) <= w:
            return t
        while t and f.getlength(t + "…") > w:
            t = t[:-1]
        return t.rstrip() + "…"
    for x, items in cols:
        y = 200 * sc
        prev_side = None
        for r in items:
            if prev_side and r["side"] != prev_side:
                y += 14 * sc
            prev_side = r["side"]
            orig, eng, src = QUOTES[r["id"]]
            main = orig if orig else f"“{eng}”"
            main = fit(main, f_qb, room[x])
            op = 1.0 if r["side"] != "unknown" else 0.55
            ov.label([((0, 0), f"{V2._date(r).strftime('%d %b %Y').upper()} · {src.upper()}", T.f_tiny, "ls", 0.6 * sc, 1.0)],
                     (x, y), 0.45, (0, 0), box=False)
            xx = x
            for k, part in enumerate(re.split(ACTOR_WORDS, main)):
                if not part:
                    continue
                hi = k % 2 == 1
                ov.label([((0, 0), part, f_qb if hi else f_q, "ls", 0, 1.0)], (xx, y + 15 * sc), op * (1.0 if hi else 0.62),
                         (0, 0), box=False)
                xx += (f_qb if hi else f_q).getlength(part)
            if orig:
                ov.label([((0, 0), fit(f"“{eng}”", f_e, room[x]), f_e, "ls", 0, 1.0)], (x, y + 29 * sc), op * 0.45, (0, 0),
                         box=False)
            if S.truce_of(r):
                poly(cv.m["tick"], [(x - 12 * sc, y - 6 * sc), (x - 12 * sc, y + 30 * sc)], 1.2 * sc)
            y += y_step if orig else 40 * sc
    fr = cv.finish()
    T.head(at=(40 * sc, 40 * sc), lines=("Who repaired the lines, in the sources’ words",))
    SC.foot(T, cv, "ONE LINE PER REPAIR, IN DATE ORDER, AS THE SOURCE PUT IT (CUT SHORT WITH …) · BRIGHT: WHO DID THE WORK · "
                   "UNDER IT, THE ENGLISH GIVEN IN SIDES/WHO_REPAIRED.MD · A BAR AT LEFT: AN IAEA-BROKERED CEASEFIRE")
    return T.onto(fr)


# ---- P: a punch card

def option_p(B, reps):
    cv = SC.Canvas(B)
    T = S.Text(B)
    sc, W, H = cv.sc, cv.W, cv.H
    months = []
    d = date(2022, 2, 1)
    while d <= date(2026, 11, 1):
        months.append(d)
        d = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
    rows = ["fe-north", "fe-south", "dn-north", "dn-crossing", "dn-occupied", "switchyards", None]
    names = {"dn-north": "DNIPROVSKA, NORTH OF THE DNIPRO", "fe-north": "FEROSPLAVNA-1, NORTH OF THE DNIPRO",
             "dn-crossing": "DNIPROVSKA, THE CROSSING", "dn-occupied": "DNIPROVSKA, OCCUPIED SIDE",
             "fe-south": "FEROSPLAVNA-1, SOUTH BANK", "switchyards": "THE SWITCHYARDS", None: "NO PLACE PUBLISHED"}
    x0, y0 = 420 * sc, 300 * sc
    cw = (W - 80 * sc - x0) / len(months)
    rh = 64 * sc
    sq = min(cw, rh) * 0.7
    faint = cv.m["faint"]
    for i, m in enumerate(months):
        x = x0 + i * cw
        for j in range(len(rows)):
            y = y0 + j * rh
            cv2.circle(faint, tuple(S._p((x + cw / 2, y + rh / 2))), round(1.0 * sc * 16), 255, -1, cv2.LINE_AA, shift=4)
        if m.month == 1:
            dashed(faint, [(x, y0 - 20 * sc), (x, y0 + len(rows) * rh)], 2 * sc, 4 * sc, 0.8 * sc)
            T.tiny(str(m.year), (x + 4 * sc, y0 - 26 * sc), "lm", 0.55)
    T.tiny("2022", (x0 + 4 * sc, y0 - 26 * sc), "lm", 0.55)
    for j, rg in enumerate(rows):
        n = sum(1 for r in reps if r.get("region") == rg)
        T.tiny(f"{names[rg]} ({n})", (x0 - 20 * sc, y0 + j * rh + rh / 2 + 3 * sc), "rm", 0.8)
        cell = {}
        for r in [r for r in reps if r.get("region") == rg]:
            d = V2._date(r)
            i = (d.year - 2022) * 12 + d.month - 2
            k = cell.get(i, 0)
            cell[i] = k + 1
            n_i = sum(1 for q in reps if q.get("region") == rg and V2._date(q).year * 12 + V2._date(q).month ==
                      d.year * 12 + d.month)
            cx, cy = x0 + i * cw + cw / 2, y0 + j * rh + rh / 2
            s_ = sq
            if n_i > 1:                                        # a shared month: smaller marks, two by two in the cell
                s_ = sq * 0.47
                cx += (k % 2 - 0.5) * (s_ + 2 * sc)
                cy += (k // 2 - (0.5 if n_i > 2 else 0)) * (s_ + 2 * sc)
            a, b = (cx - s_ / 2, cy - s_ / 2), (cx + s_ / 2, cy + s_ / 2)
            m = cv.m["node"]
            if r["side"] == "ukrainian":
                cv2.rectangle(m, tuple(S._p(a)), tuple(S._p(b)), 255, -1, cv2.LINE_AA, shift=4)
            elif r["side"] == "russian":
                cv2.rectangle(m, tuple(S._p(a)), tuple(S._p(b)), 255, max(1, round(1.3 * sc)), cv2.LINE_AA, shift=4)
            elif r["side"] == "both":
                cv2.rectangle(m, tuple(S._p(a)), tuple(S._p(b)), 255, max(1, round(1.3 * sc)), cv2.LINE_AA, shift=4)
                cv2.fillPoly(m, [S._p([a, (b[0], a[1]), (a[0], b[1])])], 255, cv2.LINE_AA, shift=4)
            else:
                dashed(m, [a, (b[0], a[1]), b, (a[0], b[1])], 1.6 * sc, 2 * sc, 1.0 * sc, closed=True)
            if S.truce_of(r):
                poly(cv.m["tick"], [(a[0], b[1] + 3 * sc), (b[0], b[1] + 3 * sc)], 1.3 * sc)
    fr = cv.finish()
    T.head(at=(40 * sc, 40 * sc), lines=(f"{len(reps)} repairs, by area and month",))
    SC.foot(T, cv, "ONE MARK PER REPAIR IN THE MONTH IT WAS DONE · FILLED: UKRAINIAN CREWS · OUTLINED: THE RUSSIAN SIDE · "
                   "HALF: BOTH · DASHED: NOT SAID · A BAR UNDER: AN IAEA-BROKERED CEASEFIRE · AREAS AS IN THE MAP, NOT PLACES OF WORK")
    return T.onto(fr)


OPTIONS = {"E2": lambda B, r: ring_option(B, r, "E2"), "E3": lambda B, r: ring_option(B, r, "E3"),
           "E4": lambda B, r: ring_option(B, r, "E4"), "W": option_w, "ST": option_st, "U": option_u, "Q": option_q,
           "P": option_p}
NAMES = {"E2": "sides_E2", "E3": "sides_E3", "E4": "sides_E4", "W": "proto_waiting_bars", "ST": "proto_spacetime_stack",
         "U": "proto_unit_chart", "Q": "proto_sources_words", "P": "proto_punch_card"}


def main(which):
    B, reps = S.load()
    made = {}
    for k in which:
        img = OPTIONS[k](B, reps)
        f = OUT / f"{NAMES[k]}_1920.jpg"
        Image.fromarray(V5.half(img)).save(f, quality=92)
        made[k] = f.name
        print(f)
    rec = OUT / "sides.json"
    doc = json.loads(rec.read_text()) if rec.exists() else {}
    doc.setdefault("prototypes", {}).update(made)
    doc["prototypes_asked"] = "The user, 8 November 2026: test the new ideas as still prototypes"
    doc["cut_dates"] = {k: {"date": v[0], "month_only": bool(v[1])} for k, v in CUT.items()}
    doc["made_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rec.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    have = [OUT / f"{NAMES[k]}_1920.jpg" for k in OPTIONS if (OUT / f"{NAMES[k]}_1920.jpg").exists()]
    img = Image.new("RGB", (1920, 540 * ((len(have) + 1) // 2)), (0, 0, 0))
    for i, f in enumerate(have):
        img.paste(Image.open(f).resize((960, 540), Image.LANCZOS), ((i % 2) * 960, (i // 2) * 540))
    img.save(OUT / "proto_sheet.jpg", quality=88)


if __name__ == "__main__":
    main(sys.argv[1:] or list(OPTIONS))
