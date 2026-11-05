"""S1 section film, one per line: the offset section (the cooling pond's north dike, a break, the line's crossing) on
the three days of complete loss, 2022, 2025, 2026, dissolving from one to the next so the water falls; under it the
dike enlarged three times, where the pond's fall reads. Each day a drawing of its own (profile2.py renders, its pass
in the key plan); a dissolve only mixes two days' drawings and says so. Not the film.
python gfilm.py XF_DIR LINE OUT.mp4 [--sheet SHEET.png]      (LINE 0 Dniprovska, 1 Ferosplavna)"""
import json, math, subprocess, sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

XF, LINE, OUT = Path(sys.argv[1]), int(sys.argv[2]), Path(sys.argv[3])
SHEET = Path(sys.argv[sys.argv.index("--sheet") + 1]) if "--sheet" in sys.argv else None
G = XF / "gf"
STATES = {k: {"flat": False, **v} for k, v in json.loads((XF / "states.json").read_text()).items()}
HN = "/System/Library/Fonts/HelveticaNeue.ttc"
font = lambda n, m=False: ImageFont.truetype(HN, n, index=10 if m else 0)
F_DATE, F_EVENT, F_LAB, F_SMALL, F_TINY = font(34, True), font(19), font(15, True), font(15), font(13)
FPS, W, H, BALTIC, BOX_A, GAP, DY = 30, 1920, 1080, 0.4, 0.5, 120, -60
DATE = {"A": "6 SEPTEMBER 2022", "B": "27 SEPTEMBER 2025", "C": "23 AUGUST 2026"}
NAME = ["DNIPROVSKA", "FEROSPLAVNA"][LINE]
PAST = {16.67: "11 JUN 2023", 15.4: "MAY 2024", 14.34: "SEP 2024", 13.54: "11 AUG 2025"}   # the pond's reports
D_S0, D_S1, D_SC, D_PX, D_ZC = 300.0, 2300.0, 1300.0, 4141 / 1920, 12.0                       # the detail's frame


def dashed(d, xa, xb, y, rgb, a=255, w=1, on=8, off=6):
    x = xa
    while x < xb:
        d.line([(x, y), (min(x + on, xb), y)], fill=(*rgb, a), width=w); x += on + off


def boxed(d, xy, text, f, alpha=1.0, fill=255, pad=(7, 4), anchor="la"):
    b = d.textbbox(xy, text, font=f, anchor=anchor)
    d.rectangle((b[0] - pad[0], b[1] - pad[1], b[2] + pad[0], b[3] + pad[1]), fill=(0, 0, 0, int(255 * BOX_A * alpha)))
    d.text(xy, text, font=f, fill=(fill, fill, fill, int(255 * alpha)), anchor=anchor)


def names(d, items, placed):
    """Each name above its point on a leader, climbing past names already placed."""
    for t, x, y in sorted(items, key=lambda it: -it[2]):
        rise = 26
        while True:
            b = d.textbbox((x, y - rise), t, font=F_LAB, anchor="ms"); b = (b[0] - 8, b[1] - 5, b[2] + 8, b[3] + 5)
            if not any(b[0] < o[2] and o[0] < b[2] and b[1] < o[3] and o[1] < b[3] for o in placed):
                break
            rise += 7
        placed.append(b); d.line([(x, y), (x, y - rise + 5)], fill=(235, 235, 235, 200))
        boxed(d, (x, y - rise), t, F_LAB, anchor="ms", pad=(6, 3))


def brk(d, x, top, bot, mid):
    """A break line: straight, with a Z where it crosses the ground."""
    d.line([(x, top), (x, mid - 11), (x + 7, mid - 4), (x - 7, mid + 4), (x, mid + 11), (x, bot)],
           fill=(235, 235, 235, 255), width=2, joint="curve")


def drawing(k):
    """The day's drawing, everything but the date and its event (those change in a dissolve)."""
    ST = STATES[k]
    di, dl = Image.open(G / f"{k}_dike.png").convert("RGB"), json.loads((G / f"{k}_dike.json").read_text())
    ci, cl = Image.open(G / f"{k}_{LINE}.png").convert("RGB"), json.loads((G / f"{k}_{LINE}.json").read_text())
    ei, el = Image.open(G / f"{k}_detail.png").convert("RGB"), json.loads((G / f"{k}_detail.json").read_text())
    x0d, x1d = map(round, dl["_x"]); x0c, x1c = map(round, cl["_x"])
    M = (W - (x1d - x0d) - GAP - (x1c - x0c)) // 2
    img = Image.new("RGB", (W, H))
    img.paste(di.crop((x0d, 0, x1d, H)), (M, DY))
    oxc = M + (x1d - x0d) + GAP
    img.paste(ci.crop((x0c, 0, x1c, H)), (oxc, DY))
    sd, sc = M - x0d, oxc - x0c
    y0, y10 = dl["_y"]["0"] + DY, dl["_y"]["10"] + DY
    Y = lambda h: y0 + (y10 - y0) * h / 10.0
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    R = W - M
    dashed(d, M, R, Y(12.0 + BALTIC), (235, 235, 235), 230)
    d.text((R + 5, Y(12.0 + BALTIC)), "12 M", font=F_TINY, fill=(235, 235, 235, 230), anchor="lm")
    if not ST["flat"]:
        dashed(d, M, R, Y(16.0 + BALTIC), (140, 140, 140), 200, 1, 4, 6)
        d.text((R + 5, Y(16.0 + BALTIC) - 6), "16 M", font=F_TINY, fill=(160, 160, 160, 220), anchor="lm")
    brk(d, M, Y(30), Y(-12), Y(13))
    gx = M + (x1d - x0d) + GAP // 2
    brk(d, gx, Y(30), Y(-12), Y(13))
    end_d = np.array(dl["_ends"][1]); U = np.subtract(cl["_ends"][1], cl["_ends"][0]); U = U / np.linalg.norm(U)
    start_c = np.array(cl["_ends"][0]) - 500 * U
    km = np.linalg.norm(start_c - end_d) / 1000
    d.text((gx, Y(-16)), f"≈ {km:.1f} KM EAST OMITTED", font=F_TINY, fill=(225, 225, 225, 240), anchor="mt")
    d.text((M, Y(-16) + 18), "THE POND GOES ON SOUTH", font=F_TINY, fill=(200, 200, 200, 230), anchor="lt")
    rv = ST["river_egm"] - BALTIC
    ren = {"RIVER": f"RIVER {rv:.2f} M", "RESERVOIR": f"RESERVOIR {rv:.2f} M (NORMAL LEVEL)",
           "COOLING POND": f"COOLING POND {ST['pond_baltic']:.2f} M"}
    items = [(n if n in ("COOLING POND", "RESERVOIR") else ren.get(n, n), p[0] + sd, p[1] + DY) for n, p in dl.items()
             if not n.startswith("_")]   # the pond's level is read in the detail
    items += [(ren.get(n, n), p[0] + sc, p[1] + DY) for n, p in cl.items() if not n.startswith("_")]
    placed = []
    names(d, items, placed)

    # the detail: the pond's last stretch, its dike and the bed beyond, three times larger, heights still x10
    xa, xb = 960 + (D_S0 - D_SC) / D_PX, 960 + (D_S1 - D_SC) / D_PX
    ey0, ey10 = el["_y"]["0"], el["_y"]["10"]
    YE = lambda h: ey0 + (ey10 - ey0) * h / 10.0
    top, bot = YE(27.0), YE(-6.0)
    DX0, DY0 = M, 742
    crop = ei.crop((round(xa), round(top), round(xb), round(bot)))
    img.paste(crop, (DX0, DY0))
    ox, oy = DX0 - xa, DY0 - top
    YD = lambda h: YE(h) + oy
    dw = crop.width
    d.rectangle((DX0 - 1, DY0 - 1, DX0 + dw, DY0 + crop.height), outline=(110, 110, 110, 255))
    d.text((DX0, DY0 - 12), "DETAIL: THE POND'S NORTH DIKE, AT THREE TIMES THE SECTION'S SCALE (HEIGHTS STILL x10)",
           font=F_TINY, fill=(220, 220, 220, 240), anchor="ls")
    dashed(d, DX0, DX0 + dw, YD(12.0 + BALTIC), (235, 235, 235), 235, 1)
    d.text((DX0 + dw + 6, YD(12.0 + BALTIC)), "12 M: THE POND'S REPORTED LIMIT FOR THE COOLING WATER PUMPS",
           font=F_TINY, fill=(235, 235, 235, 235), anchor="lm")
    if not ST["flat"]:
        dashed(d, DX0, DX0 + dw, YD(16.0 + BALTIC), (140, 140, 140), 210, 1, 4, 6)
        d.text((DX0 + dw + 6, YD(16.0 + BALTIC)), "16 M: THE RESERVOIR'S NORMAL LEVEL, BEFORE THE DAM'S DESTRUCTION",
               font=F_TINY, fill=(170, 170, 170, 230), anchor="lm")
    pa, pb = el["_pond"][0] + ox, min(el["_pond"][1] + ox, DX0 + dw)
    pa = max(pa, DX0)
    for p in ST["past"]:
        d.line([(pa, YD(p + BALTIC)), (pb, YD(p + BALTIC))], fill=(150, 150, 150, 210), width=1)
    if ST["past"]:
        d.text((DX0 + dw + 6, YD(max(ST["past"]) + BALTIC) - 16), "GREY: THE POND'S EARLIER REPORTS, "
               + ", ".join(f"{p:.2f} ({PAST[p]})" for p in ST["past"]), font=F_TINY, fill=(170, 170, 170, 230), anchor="lm")
    di_items = [(ren.get(n, n), p[0] + ox, p[1] + oy) for n, p in el.items()
                if not n.startswith("_") and DX0 + 40 < p[0] + ox < DX0 + dw - 40]
    names(d, di_items, [])
    # where the detail is in the section: a dashed frame round that stretch
    sx = lambda s: 960 + (s - 1900.0) / dl["_px"] + sd   # the dike piece's frame centre: halfway along its 3.8 km
    fx0, fx1, fy0, fy1 = sx(D_S0), sx(D_S1), Y(27), Y(-6)
    for (a_, b_) in (((fx0, fy0), (fx1, fy0)), ((fx0, fy1), (fx1, fy1))):
        dashed(d, a_[0], b_[0], a_[1], (200, 200, 200), 220, 1, 4, 4)
    for xv in (fx0, fx1):
        yv = fy0
        while yv < fy1:
            d.line([(xv, yv), (xv, min(yv + 4, fy1))], fill=(200, 200, 200, 220)); yv += 8
    d.text((fx1 + 6, fy1), "DETAIL BELOW", font=F_TINY, fill=(210, 210, 210, 230), anchor="lt")

    # the key plan: the day's pass, dimmed; the cut and its jog; no tower or point marked
    E = np.load(XF / f"E_{k}.npz"); ex, ey, u, v = E["x"], E["y"], E["u"], E["v"]
    pas = Image.open(XF.parent / "passes" / ST["pass"] / "rgb.webp").convert("RGB"); pw, ph = pas.size
    du = (u[0, -1] - u[0, 0]) / (ex[-1] - ex[0]); dv = (v[-1, 0] - v[0, 0]) / (ey[-1] - ey[0])
    U0, V0 = u[0, 0] - du * ex[0], v[0, 0] - dv * ey[0]
    KX0, KX1, KY0, KY1, KS = -5600.0, 7400.0, -1500.0, 11500.0, 290
    ipx = lambda x, y: ((U0 + du * x) * pw, (1 - (V0 + dv * y)) * ph)
    a0, b0 = ipx(KX0, KY1); a1, b1 = ipx(KX1, KY0)
    kp = pas.crop((round(a0), round(b0), round(a1), round(b1))).resize((KS, KS), Image.LANCZOS)
    kp = Image.fromarray((np.asarray(kp, np.float32) * 0.55).astype(np.uint8))
    KX, KY = W - 60 - KS, 40
    img.paste(kp, (KX, KY))
    s_ = KS / (KX1 - KX0)
    P = lambda x, y: (KX + (x - KX0) * s_, KY + (KY1 - y) * s_)
    d.rectangle((KX, KY, KX + KS, KY + KS), outline=(120, 120, 120, 255))
    d.line([P(-3000, 600), P(-3000, 4400)], fill=(255, 255, 255, 255), width=2)
    d.line([P(*start_c), P(*(np.array(cl["_ends"][1]) + 500 * U))], fill=(255, 255, 255, 255), width=2)
    qa, qb = np.array(P(-3000, 4400)), np.array(P(*start_c)); n = int(np.linalg.norm(qb - qa) / 7)
    for i in range(0, n, 2):
        d.line([tuple(qa + (qb - qa) * i / n), tuple(qa + (qb - qa) * (i + 1) / n)], fill=(255, 255, 255, 220), width=2)
    nx_, ny_ = KX + KS - 20, KY + 18
    d.polygon([(nx_, ny_ - 10), (nx_ - 5, ny_ + 3), (nx_ + 5, ny_ + 3)], fill=(235, 235, 235, 255))
    d.text((nx_, ny_ + 6), "N", font=F_TINY, fill=(235, 235, 235, 255), anchor="mt")
    d.line([(KX + 12, KY + KS - 12), (KX + 12 + 2000 * s_, KY + KS - 12)], fill=(235, 235, 235, 255), width=2)
    d.text((KX + 12, KY + KS - 17), "2 KM", font=F_TINY, fill=(235, 235, 235, 255), anchor="ls")
    d.text((KX - 12, KY + KS - 18), "KEY PLAN: THE CUT, JOGGED EAST (DASHED)", font=F_TINY, fill=(200, 200, 200, 230),
           anchor="rs")
    d.text((KX - 12, KY + KS - 2), f"{ST['imagery']}, DIMMED", font=F_TINY, fill=(200, 200, 200, 230), anchor="rs")

    boxed(d, (60, 136), f"SECTION THROUGH THE COOLING POND'S NORTH DIKE, 3 KM WEST OF THE PLANT, THEN ALONG {NAME}'S "
          "CROSSING (SOUTH LEFT, NORTH RIGHT)", F_SMALL, fill=225)
    boxed(d, (60, 160), "THE LEVELS: " + ST["level_note"].upper(), F_TINY, fill=200)
    foot = ["EVERY HEIGHT x10 (GROUND, WATER, TOWERS, SAG: THE PLAN-AND-PROFILE CONVENTION); LENGTHS TRUE. THE DRAINED "
            "BED'S HEIGHTS INFERRED (DOTTED); THE POND'S DEPTH NOT PUBLISHED (FADED). LEVELS IN METRES BALTIC.",
            "THE THREE DAYS ARE DAYS OF COMPLETE LOSS OF OFF-SITE POWER, CHOSEN SO: EVERY WIRE BARE STEEL. LINES: "
            "OPENSTREETMAP; TOWERS AT ITS POSITIONS, TYPES REPRESENTATIVE.",
            "CONTAINS MODIFIED COPERNICUS SENTINEL-2 DATA (2022, 2025, 2026)."]
    for i, t in enumerate(foot):
        d.text((60, 1000 + i * 17), t, font=F_TINY, fill=(200, 200, 200, 200))
    return np.asarray(Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB"), np.float32)


PIC = {k: drawing(k) for k in "ABC"}
T_IN, HOLD = 1.0, {"A": 4.5, "B": 4.0, "C": 5.0}
DISSOLVE, T_OUT = 2.0, 1.2
plan, t = [], 0.0
for i, k in enumerate("ABC"):
    plan.append((k, t, t + HOLD[k])); t += HOLD[k]
    if k != "C":
        plan.append((k + ">" + "ABC"[i + 1], t, t + DISSOLVE)); t += DISSOLVE
TOTAL = t + T_OUT


def ease(u):
    u = min(1.0, max(0.0, u)); return 0.5 - 0.5 * math.cos(math.pi * u)


def frame(t):
    for k, t0, t1 in plan:
        if t0 <= t < t1 or (k == "C" and t >= t0):
            break
    if ">" in k:
        a, b = k.split(">"); w = ease((t - t0) / (t1 - t0)); pic = PIC[a] * (1 - w) + PIC[b] * w
        top = (f"{DATE[a]}  >  {DATE[b]}", "A DISSOLVE BETWEEN TWO DATED DAYS' DRAWINGS: NOT AN OBSERVATION")
    else:
        pic, top = PIC[k], (DATE[k], STATES[k]["event"])
    im = Image.fromarray(pic.astype(np.uint8)).convert("RGBA")
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    boxed(d, (60, 52), top[0], F_DATE); boxed(d, (60, 104), top[1], F_EVENT)
    a = np.asarray(Image.alpha_composite(im, ov).convert("RGB"), np.float32)
    return (a * ease(min(t / T_IN, (TOTAL - t) / T_OUT))).astype(np.uint8)


if SHEET:
    ts = [plan[0][1] + 3, plan[1][1] + 1, plan[2][1] + 2.5, plan[4][1] + 3]
    tiles = [Image.fromarray(frame(x)) for x in ts]
    sh = Image.new("RGB", (W, H * 2)); [sh.paste(im.resize((W // 2, H // 2)), ((i % 2) * W // 2, (i // 2) * H // 2))
                                        for i, im in enumerate(tiles)]
    sh.crop((0, 0, W, H)).save(SHEET); Image.fromarray(frame(ts[-1])).save(SHEET.with_name(SHEET.stem + "_C.png"))
    print("sheet", ts)
else:
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "16", "-preset", "slow",
                           "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(OUT)], stdin=subprocess.PIPE)
    for f in range(int(round(TOTAL * FPS))):
        ff.stdin.write(frame(f / FPS).tobytes())
    ff.stdin.close(); ff.wait()
    print("wrote", OUT, f"{TOTAL:.1f} s", [(k, round(a, 2), round(b, 2)) for k, a, b in plan])
