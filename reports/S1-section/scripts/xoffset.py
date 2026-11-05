"""S1 offset section: the cooling pond's north dike (x = -3000) and a line's crossing, two pieces of one section at one
scale (profile2.py renders), joined by a break line where the cut jogs east, the levels run across both, a key plan
of the cut. Pixels only placed; the type, levels and plan drawn here. Not the film.
python xoffset.py XF_DIR STATE LINE OUT.png      (LINE 0 Dniprovska, 1 Ferosplavna)"""
import json, math, sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

XF, K, LINE, OUT = Path(sys.argv[1]), sys.argv[2], int(sys.argv[3]), Path(sys.argv[4])
ST = {"flat": False, **json.loads((XF / "states.json").read_text())[K]}
HN = "/System/Library/Fonts/HelveticaNeue.ttc"
font = lambda n, m=False: ImageFont.truetype(HN, n, index=10 if m else 0)
F_DATE, F_EVENT, F_LAB, F_SMALL, F_TINY = font(34, True), font(19), font(17, True), font(15), font(13)
BALTIC, BOX_A, M, GAP = 0.4, 0.5, 80, 160
DATE = {"A": "6 SEPTEMBER 2022", "B": "27 SEPTEMBER 2025", "C": "23 AUGUST 2026"}
NAME = ["DNIPROVSKA", "FEROSPLAVNA"][LINE]

pieces = []
for p in ("dike", str(LINE)):
    im = Image.open(XF / "g" / f"{K}_{p}.png").convert("RGB"); lab = json.loads((XF / "g" / f"{K}_{p}.json").read_text())
    pieces.append((im, lab))
(di, dl), (ci, cl) = pieces
x0d, x1d = map(round, dl["_x"]); x0c, x1c = map(round, cl["_x"])
Wc = M + (x1d - x0d) + GAP + (x1c - x0c) + M
img = Image.new("RGB", (Wc, 1080))
img.paste(di.crop((x0d, 0, x1d, 1080)), (M, 0))
ox_c = M + (x1d - x0d) + GAP
img.paste(ci.crop((x0c, 0, x1c, 1080)), (ox_c, 0))
shift_d, shift_c = M - x0d, ox_c - x0c
y0, y10 = dl["_y"]["0"], dl["_y"]["10"]
Y = lambda h: y0 + (y10 - y0) * h / 10.0          # EGM2008 metres to the drawing's rows (both pieces)
ov = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)


def boxed(xy, text, f, alpha=1.0, fill=255, pad=(7, 4), anchor="la"):
    b = d.textbbox(xy, text, font=f, anchor=anchor)
    d.rectangle((b[0] - pad[0], b[1] - pad[1], b[2] + pad[0], b[3] + pad[1]), fill=(0, 0, 0, int(255 * BOX_A * alpha)))
    d.text(xy, text, font=f, fill=(fill, fill, fill, int(255 * alpha)), anchor=anchor)
    return b


def dashed(xa, xb, y, rgb, a=255, w=1, on=8, off=6):
    x = xa
    while x < xb:
        d.line([(x, y), (min(x + on, xb), y)], fill=(*rgb, a), width=w); x += on + off


# the levels, across both pieces: 12 m (the pumps' reported limit) and 2022's normal level once it has gone
dashed(M, Wc - M, Y(12.0 + BALTIC), (235, 235, 235), 230, 1)
d.text((Wc - M + 6, Y(12.0 + BALTIC)), "12 M", font=F_TINY, fill=(235, 235, 235, 230), anchor="lm")
if not ST["flat"]:
    dashed(M, Wc - M, Y(16.0 + BALTIC), (140, 140, 140), 200, 1, 4, 6)
    d.text((Wc - M + 6, Y(16.0 + BALTIC)), "16 M", font=F_TINY, fill=(160, 160, 160, 220), anchor="lm")
pa, pb = (v + shift_d for v in dl["_pond"])
for p in ST["past"]:   # the pond's earlier reports, over the pond only
    d.line([(pa, Y(p + BALTIC)), (pb, Y(p + BALTIC))], fill=(150, 150, 150, 200), width=1)
if ST["past"]:
    d.text((pb - 4, Y(max(ST["past"]) + BALTIC) - 4), "EARLIER REPORTS: " + ", ".join(f"{p:.2f}" for p in ST["past"]),
           font=F_TINY, fill=(170, 170, 170, 230), anchor="rs")


def brk(x, top, bot, mid):
    """A break line: straight, with a Z where it crosses the ground."""
    pts = [(x, top), (x, mid - 14), (x + 9, mid - 5), (x - 9, mid + 5), (x, mid + 14), (x, bot)]
    d.line(pts, fill=(235, 235, 235, 255), width=2, joint="curve")


brk(M, Y(34), Y(-9), Y(13))                                     # the pond goes on south
gx = M + (x1d - x0d) + GAP // 2
brk(gx, Y(34), Y(-9), Y(13))
end_d = np.array(dl["_ends"][1]); s_c = np.array(cl["_ends"][0]); U = np.subtract(cl["_ends"][1], cl["_ends"][0])
U = U / np.linalg.norm(U); start_c = s_c - 500 * U
km = np.linalg.norm(start_c - end_d) / 1000
boxed((gx, Y(40)), f"≈ {km:.1f} KM EAST OMITTED", F_SMALL, anchor="ms")
boxed((M, Y(40)), "THE POND GOES ON SOUTH", F_TINY, 0.9, fill=210, anchor="ls")

# the names, each above its point on a leader
placed = []
names = {**{n: (p[0] + shift_d, p[1]) for n, p in dl.items() if not n.startswith("_")},
         **{n: (p[0] + shift_c, p[1]) for n, p in cl.items() if not n.startswith("_")}}
pl = ST["pond_baltic"]; rv = ST["river_egm"] - BALTIC
ren = {"COOLING POND": f"COOLING POND {pl:.2f} M", "RIVER": f"RIVER {rv:.2f} M",
       "RESERVOIR": f"RESERVOIR {rv:.2f} M (NORMAL LEVEL)"}
for n, (x, y) in sorted(names.items(), key=lambda kv: kv[1][1]):
    t = ren.get(n, n); rise = 30
    while True:
        b = d.textbbox((x, y - rise), t, font=F_LAB, anchor="ms"); b = (b[0] - 9, b[1] - 6, b[2] + 9, b[3] + 6)
        if not any(b[0] < o[2] and o[0] < b[2] and b[1] < o[3] and o[1] < b[3] for o in placed):
            break
        rise += 8
    placed.append(b); d.line([(x, y), (x, y - rise + 6)], fill=(235, 235, 235, 200)); boxed((x, y - rise), t, F_LAB, anchor="ms")

# top left: the day and what happened to the lines; the section's course
boxed((60, 52), DATE[K], F_DATE)
boxed((60, 104), ST["event"], F_EVENT)
boxed((60, 136), f"SECTION THROUGH THE COOLING POND'S NORTH DIKE, 3 KM WEST OF THE PLANT, THEN ALONG {NAME}'S CROSSING "
      "(SOUTH LEFT, NORTH RIGHT)", F_SMALL, fill=225)
boxed((60, 160), "THE LEVELS: " + ST["level_note"].upper(), F_TINY, fill=200)

# the key plan: the day's pass, dimmed, the cut and its jog; no tower or point marked
E = np.load(XF / f"E_{K}.npz"); ex, ey, u, v = E["x"], E["y"], E["u"], E["v"]
pas = Image.open(Path(__file__).parent / "passes" / ST["pass"] / "rgb.webp").convert("RGB")
pw, ph = pas.size
du = (u[0, -1] - u[0, 0]) / (ex[-1] - ex[0]); dv = (v[-1, 0] - v[0, 0]) / (ey[-1] - ey[0])
U0, V0 = u[0, 0] - du * ex[0], v[0, 0] - dv * ey[0]
KX0, KX1, KY0, KY1, KS = -5600.0, 7400.0, -1500.0, 11500.0, 400   # inside the pass (x to 7500)
sc = KS / (KX1 - KX0)


def ipx(x, y):
    return ((U0 + du * x) * pw, (1 - (V0 + dv * y)) * ph)


a0, b0 = ipx(KX0, KY1); a1, b1 = ipx(KX1, KY0)
kp = pas.crop((round(a0), round(b0), round(a1), round(b1))).resize((KS, KS), Image.LANCZOS)
kp = Image.fromarray((np.asarray(kp, np.float32) * 0.55).astype(np.uint8))
KX, KY = Wc - M - KS - 40, 40
img.paste(kp, (KX, KY))
P = lambda x, y: (KX + (x - KX0) * sc, KY + (KY1 - y) * sc)
d.rectangle((KX, KY, KX + KS, KY + KS), outline=(120, 120, 120, 255))
d.line([P(-3000, 600), P(-3000, 4400)], fill=(255, 255, 255, 255), width=3)
c0, c1 = start_c, np.array(cl["_ends"][1]) + 500 * U
d.line([P(*c0), P(*c1)], fill=(255, 255, 255, 255), width=3)
qa, qb = np.array(P(-3000, 4400)), np.array(P(*c0)); n = int(np.linalg.norm(qb - qa) / 9)
for i in range(0, n, 2):
    d.line([tuple(qa + (qb - qa) * i / n), tuple(qa + (qb - qa) * (i + 1) / n)], fill=(255, 255, 255, 220), width=2)
nx_, ny_ = KX + KS - 26, KY + 22   # north up
d.polygon([(nx_, ny_ - 12), (nx_ - 6, ny_ + 4), (nx_ + 6, ny_ + 4)], fill=(235, 235, 235, 255))
d.text((nx_, ny_ + 8), "N", font=F_TINY, fill=(235, 235, 235, 255), anchor="mt")
d.line([(KX + 16, KY + KS - 16), (KX + 16 + 2000 * sc, KY + KS - 16)], fill=(235, 235, 235, 255), width=2)
d.text((KX + 16, KY + KS - 22), "2 KM", font=F_TINY, fill=(235, 235, 235, 255), anchor="ls")
d.text((KX, KY + KS + 8), "KEY PLAN: THE CUT, JOGGED EAST (DASHED)", font=F_TINY, fill=(200, 200, 200, 230))
d.text((KX, KY + KS + 25), f"{ST['imagery']}, DIMMED", font=F_TINY, fill=(200, 200, 200, 230))

FOOT = ["EVERY HEIGHT x10 (GROUND, WATER, TOWERS, SAG: THE PLAN-AND-PROFILE CONVENTION); LENGTHS TRUE. THE DRAINED BED'S "
        "HEIGHTS INFERRED (DOTTED); THE POND'S DEPTH NOT PUBLISHED (FADED).",
        "LEVELS IN METRES BALTIC: 12 M DASHED, THE POND'S REPORTED LIMIT FOR THE COOLING WATER PUMPS; GREY, THE POND'S "
        "EARLIER REPORTS" + ("; 16 M, THE RESERVOIR'S NORMAL LEVEL BEFORE THE DAM'S DESTRUCTION." if not ST["flat"] else "."),
        "A DAY OF COMPLETE LOSS OF OFF-SITE POWER, CHOSEN SO: EVERY WIRE BARE STEEL. LINES: OPENSTREETMAP; TOWERS AT ITS "
        "POSITIONS, TYPES REPRESENTATIVE. CONTAINS MODIFIED COPERNICUS SENTINEL-2 DATA."]
FY = round(Y(-9)) + 70
for i, t in enumerate(FOOT):
    d.text((60, FY + i * 19), t, font=F_TINY, fill=(200, 200, 200, 210))
img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB").crop((0, 0, Wc, FY + 3 * 19 + 40))
img.save(OUT); print(OUT, img.size, f"omitted {km:.2f} km")
