"""Read the monthly crops (VNP46A3). Usage: monthly_read.py IN_DIR OUT_DIR
Per town: mean of the all-angle snow-free composite within 2 km, good-quality pixels only (quality 0; never the
gap-filled 2); where the month had snow cover and no snow-free value, the snow-covered composite, marked "snow".
Writes monthly.csv, monthly.png (chart) and maps.png (chosen months side by side)."""
import csv, datetime as dt, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as md
from PIL import Image, ImageDraw

IN, OUT = Path(sys.argv[1]), Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
TOWNS = [("Enerhodar", 47.49048, 34.66199, "occupied", "#c2410c", 2.4),
         ("Kamianka-Dniprovska", 47.49629, 34.41026, "occupied", "#f59e0b", 1.2),
         ("Vasylivka", 47.44218, 35.28213, "occupied", "#a16207", 1.2),
         ("Nikopol", 47.56826, 34.39126, "Ukrainian-held", "#1d4ed8", 1.2),
         ("Marhanets", 47.63088, 34.6245, "Ukrainian-held", "#0891b2", 1.2),
         ("Pokrov", 47.65361, 34.11488, "Ukrainian-held", "#6366f1", 1.2),
         ("ZNPP site", 47.5085556, 34.5879012, "occupied", "#111827", 1.6)]
RADIUS = {"ZNPP site": 1.0}
ZNPP = ("ZNPP", 47.5085556, 34.5879012)   # OSM way 28877213, network.json
R_KM = 2.0


def layer(z):
    """The month's composite with good pixels only; NaN elsewhere. Snow-free first, else snow-covered."""
    out = np.full(z["AllAngle_Composite_Snow_Free"].shape, np.nan, np.float32); snow = np.zeros(out.shape, bool)
    for kind in ("Snow_Free", "Snow_Covered"):
        v, q = z[f"AllAngle_Composite_{kind}"], z[f"AllAngle_Composite_{kind}_Quality"]
        take = np.isnan(out) & (q == 0) & (v >= 0)
        out[take] = v[take]; snow |= take & (kind == "Snow_Covered")
    return out, snow


rows, maps = [], {}
for p in sorted(IN.glob("*.npz")):
    z = np.load(p); ym = p.stem; lat, lon = z["lat"], z["lon"]
    v, snow = layer(z); maps[ym] = (v, lat, lon)
    row = {"month": ym}
    for name, la, lo, *_ in TOWNS:
        near = ((lat[:, None] - la) * 111.2) ** 2 + ((lon[None, :] - lo) * 111.2 * np.cos(np.radians(la))) ** 2 <= RADIUS.get(name, R_KM) ** 2
        good = near & ~np.isnan(v)
        row[name] = round(float(v[good].mean()), 2) if good.sum() >= 0.8 * near.sum() else ""
        row[name + "_snow"] = int((near & snow).any())
    rows.append(row)
with open(OUT / "monthly.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
for r in rows:
    print(r["month"], " ".join(f"{t[0][:7]}:{str(r[t[0]]) or '-':>6}{'*' if r[t[0] + '_snow'] else ' '}" for t in TOWNS))

# chart
fig, ax = plt.subplots(figsize=(12, 6), dpi=150)
when = {r["month"]: dt.date(int(r["month"][:4]), int(r["month"][5:]), 15) for r in rows}
for name, la, lo, bank, c, lw in TOWNS:
    pts = [(when[r["month"]], float(r[name])) for r in rows if r[name]]
    ax.plot(*zip(*pts), "--o" if name == "ZNPP site" else "-o", color=c, lw=lw, ms=3.5,
            label=f"{name} ({bank} since 2022{', within 1 km' if name == 'ZNPP site' else ''})")
    ax.annotate(name, pts[-1], xytext=(6, 0), textcoords="offset points", va="center", fontsize=8, color="#333")
for d, txt, y in [(dt.date(2022, 2, 24), "24 Feb 2022:\nfull-scale invasion", 70),
                  (dt.date(2022, 10, 10), "10 Oct 2022: strikes on\nUkraine's grid begin", 35),
                  (dt.date(2023, 6, 6), "6 Jun 2023: Kakhovka\ndam destroyed", 70),
                  (dt.date(2026, 7, 6), "Jul 2026: strikes cut\npower in the occupied\nsouth (Moscow Times)", 70)]:
    ax.axvline(d, color="#999", lw=0.8, ls=":"); ax.text(d, y, " " + txt, fontsize=7, va="top", color="#444")
ax.set_yscale("log"); ax.set_ylim(0.05, 80)
ax.set_ylabel("night-time brightness, monthly average,\ntown within 2 km (nW/cm²/sr, log: each line up = 10x)")
ax.xaxis.set_major_locator(md.MonthLocator(bymonth=(3, 9))); ax.xaxis.set_major_formatter(md.DateFormatter("%b\n%Y"))
ax.tick_params(axis="x", labelsize=7.5)
ax.axvspan(dt.date(2022, 9, 1), dt.date(2022, 9, 30), color="#c2410c", alpha=0.12, lw=0)
ax.text(dt.date(2022, 8, 25), 4.6, "Sep 2022: the daily\ntest (shaded) ", fontsize=7, ha="right", va="center", color="#7c2d12", bbox=dict(fc="white", ec="none", alpha=0.85, pad=1))
ax.set_title("Black Marble VNP46A3 (NASA, Suomi NPP), all-angle composite, good-quality pixels only, never gap-filled.\n"
             "Snow-covered months use the snow-covered composite (brighter by snow). Months shown: Sep 2019-21, then "
             "every month to Mar 2023, then every third.", fontsize=8.5, loc="left")
ax.grid(axis="y", color="#eee"); ax.spines[["top", "right"]].set_visible(False)
ax.legend(fontsize=7, loc="lower left", frameon=False, ncol=2)
fig.tight_layout(); fig.savefig(OUT / "monthly.png")

# maps of chosen months
SC = 3; pick = [m for m in ("2021-09", "2022-09", "2025-09", "2026-09") if m in maps]
tiles = []
for ym in pick:
    v, lat, lon = maps[ym]
    g = np.clip(np.log10(np.nan_to_num(v, nan=0) + 1) / np.log10(61), 0, 1)
    rgb = np.stack([(g * 255).astype(np.uint8)] * 3, -1); rgb[np.isnan(v)] = (70, 20, 20)
    im = Image.fromarray(rgb).resize((rgb.shape[1] * SC, rgb.shape[0] * SC), Image.NEAREST); dr = ImageDraw.Draw(im)
    for name, la, lo, *_ in TOWNS:
        px = (lo - lon[0]) / (lon[1] - lon[0]) * SC + SC / 2; py = (la - lat[0]) / (lat[1] - lat[0]) * SC + SC / 2
        dr.ellipse((px - 3, py - 3, px + 3, py + 3), outline=(255, 190, 0)); dr.text((px + 5, py - 5), name, fill=(255, 210, 90))
    t = Image.new("RGB", (im.width, im.height + 20)); ImageDraw.Draw(t).text((5, 4), f"{ym}  monthly composite", fill="white")
    t.paste(im, (0, 20)); tiles.append(t)
cols = 2; W, H = tiles[0].size
sheet = Image.new("RGB", (cols * W + 8, ((len(tiles) + 1) // 2) * (H + 8) + 20))
for k, t in enumerate(tiles): sheet.paste(t, ((k % cols) * (W + 8), (k // cols) * (H + 8)))
ImageDraw.Draw(sheet).text((5, sheet.height - 16), "Black Marble VNP46A3 (NASA), log 0-60 nW/cm2/sr; dark red: no good-quality value. "
                           "The river runs between the towns: Nikopol and Marhanets north (Ukrainian-held), Enerhodar south.", fill=(180, 180, 180))
sheet.save(OUT / "maps.png")
