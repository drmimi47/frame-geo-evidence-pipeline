"""S1 film test: the X block's opening (Blender's unique frames) and its three dated days composed into one test video
at 30 fps, the type and the levels' gauge drawn here. Pixels only mixed (a dissolve between two days' renders) or
faded; nothing generated. Not the film.
python xcompose.py XF_DIR OUT.mp4 [--sheet SHEET.png]"""
import json, math, subprocess, sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

XF, OUT = Path(sys.argv[1]), Path(sys.argv[2])
SHEET = Path(sys.argv[sys.argv.index("--sheet") + 1]) if "--sheet" in sys.argv else None
FPS, W, H = 30, 1920, 1080
HN = "/System/Library/Fonts/HelveticaNeue.ttc"
ST = json.loads((XF / "states.json").read_text())
OPEN = sorted((XF / "open").glob("u_*.png"))
BOX_A, BALTIC = 0.5, 0.4


def font(size, medium=False):
    return ImageFont.truetype(HN, size, index=10 if medium else 0)


F_DATE, F_EVENT, F_LAB, F_SMALL, F_TINY = font(34, True), font(19), font(17, True), font(15), font(13)

# the timeline: (start s, what) in order; the opening's frames are shown at the frames' own pace
T_FADE, T_GROW = 1.0, 3.3
T_SLIDE = T_GROW + 105 / FPS + 0.5
T_OPEN = T_SLIDE + 105 / FPS
HOLDS = [("A", T_OPEN, 6.2), ("B", None, 6.0), ("C", None, 6.0)]
DISSOLVE, FADE_OUT = 2.5, 1.5
t = T_OPEN
plan = []                       # (state, t0, t1) holds and ("A>B", t0, t1) dissolves
for i, (k, _, hold) in enumerate(HOLDS):
    plan.append((k, t, t + hold)); t += hold
    if i + 1 < len(HOLDS):
        plan.append((f"{k}>{HOLDS[i + 1][0]}", t, t + DISSOLVE)); t += DISSOLVE
END = t
TOTAL = END + FADE_OUT
DATE = {"A": "6 SEPTEMBER 2022", "B": "27 SEPTEMBER 2025", "C": "23 AUGUST 2026"}


def load(p):
    return np.asarray(Image.open(p).convert("RGB"), np.float32)


STILL = {k: load(XF / "out" / f"{k}.png") for k in "ABC"}
LABS = {k: {n: v for n, v in json.loads((XF / "out" / f"{k}.json").read_text()).items() if not n.startswith("_")}
        for k in "ABC"}
cache = {}


def opening(i):
    if i not in cache:
        cache.clear(); cache[i] = load(OPEN[i])
    return cache[i]


def ease(u):
    u = min(1.0, max(0.0, u)); return 0.5 - 0.5 * math.cos(math.pi * u)


def state_at(t):
    """(picture, label weights {state: w}, the day's values interpolated, dissolve or None)"""
    for k, t0, t1 in plan:
        if t0 <= t < t1 or (k == plan[-1][0] and t >= t0):
            if ">" not in k:
                return STILL[k], {k: 1.0}, k, None
            a, b = k.split(">"); w = ease((t - t0) / (t1 - t0))
            return STILL[a] * (1 - w) + STILL[b] * w, {a: 1 - w, b: w}, (a, b, w), (a, b)
    raise ValueError(t)


def val(day, key):
    if isinstance(day, str):
        return ST[day][key]
    a, b, w = day
    return ST[a][key] * (1 - w) + ST[b][key] * w


def boxed(d, xy, text, f, alpha, fill=255, pad=(7, 4), anchor="la"):
    x0, y0, x1, y1 = d.textbbox(xy, text, font=f, anchor=anchor)
    box = (x0 - pad[0], y0 - pad[1], x1 + pad[0], y1 + pad[1])
    d.rectangle(box, fill=(0, 0, 0, int(255 * BOX_A * alpha)))
    d.text(xy, text, font=f, fill=(fill, fill, fill, int(255 * alpha)), anchor=anchor)
    return box


def hit(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def labels(d, weights, alpha):
    """Each place's name above its point on a leader, climbing past names already placed; a name both days share
    stays put (its point interpolated), one only a day has fades with it."""
    names = {}
    for k, w in weights.items():
        if w <= 1e-6:
            continue
        for n, p in LABS[k].items():
            q = names.setdefault(n, [np.zeros(2), 0.0, 0.0])
            q[0] += np.array(p) * w; q[1] += w; q[2] += w
    placed = []
    for n, (p, wsum, a) in sorted(names.items(), key=lambda kv: -kv[1][0][1] / kv[1][1]):
        x, y = p / wsum
        rise = 34
        while True:
            bb = d.textbbox((x, y - rise), n, font=F_LAB, anchor="ms")
            bb = (bb[0] - 9, bb[1] - 6, bb[2] + 9, bb[3] + 6)
            if not any(hit(bb, o) for o in placed):
                break
            rise += 8
        placed.append(bb)
        al = alpha * min(1.0, a)
        d.line([(x, y), (x, y - rise + 6)], fill=(235, 235, 235, int(200 * al)), width=1)
        boxed(d, (x, y - rise), n, F_LAB, al, anchor="ms")


GX, GY0, GY1, LO, HI = 1716, 150, 590, 6.0, 18.0   # the gauge: 6 to 18 m Baltic


def gy(m):
    return GY1 - (m - LO) / (HI - LO) * (GY1 - GY0)


def gauge(d, day, alpha, interp):
    """The levels, in metres Baltic: the pond's (its past reports as ticks), the river's at the crossing, and 12 m."""
    if alpha <= 0:
        return
    A = lambda v: int(v * alpha)
    d.rectangle((GX - 128, GY0 - 64, GX + 176, GY1 + 74), fill=(0, 0, 0, A(255 * BOX_A)))
    d.text((GX - 116, GY0 - 52), "LEVELS, M (BALTIC)", font=F_SMALL, fill=(235, 235, 235, A(255)))
    for m in range(int(LO), int(HI) + 1, 2):
        d.line([(GX - 6, gy(m)), (GX, gy(m))], fill=(160, 160, 160, A(255)))
        d.text((GX - 10, gy(m)), f"{m}", font=F_TINY, fill=(160, 160, 160, A(255)), anchor="rm")
    d.line([(GX, GY0), (GX, GY1)], fill=(160, 160, 160, A(255)))
    pond, river = val(day, "pond_baltic"), val(day, "river_egm") - BALTIC
    col = (70, 108, 140, A(255))
    for x0, lv, name in ((GX + 14, pond, "POND"), (GX + 84, river, "RIVER")):
        d.rectangle((x0, gy(lv), x0 + 46, GY1), fill=col)
        d.line([(x0 - 2, gy(lv)), (x0 + 48, gy(lv))], fill=(235, 235, 235, A(255)), width=2)
        d.text((x0 + 23, gy(lv) - 6), f"{lv:.2f}", font=F_SMALL, fill=(235, 235, 235, A(255)), anchor="ms")
        d.text((x0 + 23, GY1 + 18), name, font=F_TINY, fill=(235, 235, 235, A(255)), anchor="ms")
    past = ST[day]["past"] if isinstance(day, str) else ST[day[1]]["past"] if day[2] > 0.5 else ST[day[0]]["past"]
    for p in past:
        d.line([(GX + 12, gy(p)), (GX + 62, gy(p))], fill=(150, 150, 150, A(255)), width=1)
    x = GX + 6
    while x < GX + 140:   # 12 m, dashed: the pond's reported limit for the cooling water pumps
        d.line([(x, gy(12.0)), (min(x + 7, GX + 140), gy(12.0))], fill=(235, 235, 235, A(255)), width=2); x += 12
    d.text((GX + 144, gy(12.0)), "12", font=F_TINY, fill=(235, 235, 235, A(255)), anchor="lm")
    notes = ["POND: GREY TICKS ITS EARLIER REPORTS", "12 M DASHED: THE PUMPS' REPORTED LIMIT",
             "RIVER: AT THE CROSSING (SWOT, MONTHLY)" if not (isinstance(day, str) and ST[day].get("flat"))
             else "2022: THE RESERVOIR'S NORMAL LEVEL"]
    if interp:
        notes.append("BETWEEN TWO DAYS: INTERPOLATED")
    for i, n in enumerate(notes):
        d.text((GX - 116, GY1 + 34 + i * 16), n, font=F_TINY, fill=(190, 190, 190, A(255)))


FOOT = ["THE COOLING POND CUT 3 KM WEST OF THE PLANT, SEEN FROM THE SOUTH-EAST; THE PLANT'S SIDE PULLED 2.5 KM EAST SO "
        "THE CUT SHOWS. GROUND AND WATER x25; TOWERS AND SAG AT TRUE SIZE.",
        "THE DRAINED BED'S HEIGHTS INFERRED (DOTTED ON THE CUT); THE POND'S DEPTH NOT PUBLISHED (FADED). WATER WHERE "
        "EACH DAY'S PASS READS WATER, AT THE REPORTED LEVEL: A MODELLED SURFACE.",
        "THE THREE DAYS ARE DAYS OF COMPLETE LOSS OF OFF-SITE POWER, CHOSEN SO: EVERY LINE CUT, BARE STEEL. LINES: "
        "OPENSTREETMAP; TOWERS AT ITS POSITIONS, TYPES REPRESENTATIVE."]
STAGE = [(T_FADE, T_GROW, "TRUE TO SIZE"), (T_GROW, T_SLIDE, None), (T_SLIDE, T_OPEN, "THE BLOCK OPENED ALONG THE "
         "COOLING POND, 3 KM WEST OF THE PLANT")]


def frame(t):
    if t < T_OPEN:
        if t < T_GROW:
            i = 0
        elif t < T_GROW + 105 / FPS:
            i = 1 + min(104, int((t - T_GROW) * FPS))
        elif t < T_SLIDE:
            i = 105
        else:
            i = 106 + min(104, int((t - T_SLIDE) * FPS))
        pic, weights, day, dis = opening(min(i, len(OPEN) - 1)), {"A": 1.0}, "A", None
        ex = 1.0 if i == 0 else 25 ** ease(min(i, 105) / 105)
    else:
        pic, weights, day, dis = state_at(t); ex = 25.0
    img = Image.fromarray(np.clip(pic, 0, 255).astype(np.uint8)).convert("RGBA")
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    la = ease((t - T_OPEN) / 1.0)
    labels(d, weights, la) if la > 0 else None
    gauge(d, day, la, dis is not None)
    # top left: the day, what happened that day to the lines; in a dissolve, both days and that it is one
    if dis:
        a, b = dis; w = day[2]
        boxed(d, (60, 52), f"{DATE[a]}  >  {DATE[b]}", F_DATE, 1.0)
        boxed(d, (60, 104), "A DISSOLVE BETWEEN TWO DATED DAYS: NOT AN OBSERVATION", F_EVENT, 1.0)
    else:
        k = day
        boxed(d, (60, 52), DATE[k], F_DATE, 1.0)
        boxed(d, (60, 104), ST[k]["event"], F_EVENT, 1.0)
        boxed(d, (60, 136), "THE LEVELS: " + ST[k]["level_note"].upper(), F_TINY, la, fill=200)
    for t0, t1, cap in STAGE:   # the opening's captions, bottom middle
        if t0 <= t < t1:
            c = cap or f"HEIGHTS x{ex:.0f}: THE TOWERS AND WIRES STAY AT TRUE SIZE"
            boxed(d, (W / 2, 1000), c, F_EVENT, min(ease((t - t0) / 0.5), ease((t1 - t) / 0.5)), anchor="ms")
    for i, line in enumerate(FOOT):   # on boxes: the land runs under them
        boxed(d, (60, 984 + i * 19), line, F_TINY, 0.8 * la, fill=210, pad=(6, 3)) if la > 0 else None
    imag = ST["A" if isinstance(day, str) and day == "A" else (day if isinstance(day, str) else day[1 if day[2] > .5 else 0])]["imagery"]
    d.text((60, 1046), f"{imag}. CONTAINS MODIFIED COPERNICUS SENTINEL-2 DATA", font=F_TINY, fill=(200, 200, 200, 150))
    img = Image.alpha_composite(img, ov).convert("RGB")
    k = min(1.0, t / T_FADE, max(0.0, (TOTAL - t) / FADE_OUT))
    a = np.asarray(img, np.float32) * ease(k)
    return a.astype(np.uint8)


if SHEET:   # a contact sheet: one frame from each part
    ts = [0.5, 2.5, T_GROW + 1.75, T_SLIDE + 1.75, T_OPEN + 3, plan[1][1] + 1.25, plan[2][1] + 3, plan[4][1] + 3]
    tiles = [Image.fromarray(frame(x)).resize((W // 2, H // 2)) for x in ts]
    sh = Image.new("RGB", (W, H * len(tiles) // 4))
    for i, im in enumerate(tiles):
        sh.paste(im, ((i % 2) * W // 2, (i // 2) * H // 2))
    sh.save(SHEET); print("sheet", SHEET, [round(x, 2) for x in ts])
else:
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "17", "-preset", "slow",
                           "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(OUT)], stdin=subprocess.PIPE)
    n = int(round(TOTAL * FPS))
    for f in range(n):
        ff.stdin.write(frame(f / FPS).tobytes())
    ff.stdin.close(); ff.wait()
    print("wrote", OUT, f"{TOTAL:.1f} s", n, "frames; plan", [(k, round(a, 2), round(b, 2)) for k, a, b in plan])
