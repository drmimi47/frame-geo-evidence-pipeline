"""The monthly chart redrawn for the film (5 November 2026): full frame, black ground, little text.
The same data as monthly_chart.png (monthly_towns.csv); its sources and method go in the film's credits."""
import csv
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent.parent
rows = list(csv.DictReader(open(HERE / "monthly_towns.csv")))
t = [date(int(r["month"][:4]), int(r["month"][5:7]), 15) for r in rows]


def series(name):   # months without a good-quality value are left out, as in monthly_chart.png
    pts = [(d, max(float(r[name]), 0.05)) for d, r in zip(t, rows) if r[name] != ""]
    return [d for d, _ in pts], [v for _, v in pts]

plt.rcParams["font.family"] = "Helvetica Neue"
fig = plt.figure(figsize=(19.2, 10.8), dpi=100, facecolor="black")
ax = fig.add_axes([0.07, 0.12, 0.80, 0.78], facecolor="black")
LINES = [("ZNPP site", "THE PLANT", "white", 3.2, (0, (4, 2))), ("Enerhodar", "ENERHODAR", "#f2c14e", 2.6, "-"),
         ("Nikopol", "NIKOPOL", "#8fb3ff", 2.6, "-")]
for name in ("Kamianka-Dniprovska", "Vasylivka", "Marhanets", "Pokrov"):
    ax.plot(*series(name), color="#555555", lw=1.2)
for name, label, col, lw, ls in LINES:
    x, y = series(name)
    ax.plot(x, y, color=col, lw=lw, ls=ls)
    ax.text(x[-1], y[-1] * (2.6 if name == "Enerhodar" else 1), f"  {label}", color=col, fontsize=17, va="center")
ax.set_yscale("log")
ax.set_xlim(date(2019, 8, 1), date(2026, 11, 30))
for d, txt in ((date(2022, 2, 24), "INVASION"), (date(2023, 6, 6), "DAM DESTROYED")):
    ax.axvline(d, color="#777777", lw=1, ls=":")
    ax.text(d, 34, f" {txt}", color="#aaaaaa", fontsize=14, va="top")
ax.text(date(2019, 9, 1), 0.075, "OTHER TOWNS NEARBY, GREY", color="#777777", fontsize=13)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
for s in ("bottom", "left"):
    ax.spines[s].set_color("#777777")
# y: the brightness, log, each step ten times the one below; 0.05 is the floor (no light measured is drawn there)
ax.set_yticks([0.05, 0.1, 1, 10])
ax.set_yticklabels(["DARK", "0.1", "1", "10"])
ax.yaxis.set_minor_locator(matplotlib.ticker.NullLocator())
for v in (0.1, 1, 10):
    ax.axhline(v, color="#262626", lw=1, zorder=0)
ax.tick_params(axis="y", colors="#aaaaaa", labelsize=15, length=6, color="#777777")
# x: a tick at each new year, the year's name in the middle of its span, a mark for every month measured
# (each September until 2021, monthly in 2022, then every three months), so the gaps between them show
ax.xaxis.set_major_locator(matplotlib.dates.YearLocator())
ax.xaxis.set_major_formatter(matplotlib.ticker.NullFormatter())
ax.xaxis.set_minor_locator(matplotlib.dates.YearLocator(month=7))
ax.xaxis.set_minor_formatter(matplotlib.dates.DateFormatter("%Y"))
ax.tick_params(axis="x", which="major", length=12, color="#777777")
ax.tick_params(axis="x", which="minor", length=0, colors="#aaaaaa", labelsize=15, pad=10)
ax.plot(t, [0.043] * len(t), ls="none", marker="|", ms=7, mew=1.2, color="#aaaaaa", clip_on=False)
ax.set_ylim(0.04, 40)
ax.text(date(2019, 10, 15), 0.0363, "2019", color="#aaaaaa", fontsize=15, ha="center", va="top")   # its last months
ax.text(date(2026, 11, 30), 0.043, "  A MONTH MEASURED", color="#777777", fontsize=12, va="center")
fig.text(0.07, 0.94, "LIGHT AT NIGHT, MONTH BY MONTH", color="white", fontsize=22)
fig.text(0.07, 0.905, "NASA BLACK MARBLE · BRIGHTNESS IN nW/cm²/sr, LOG SCALE: EACH STEP TEN TIMES THE ONE BELOW · "
         "DARK: UNDER 0.05", color="#888888", fontsize=14)
fig.savefig(HERE / "monthly_chart_film.png", facecolor="black")
