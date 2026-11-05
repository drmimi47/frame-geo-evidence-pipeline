"""Chart of towns.csv (daily). Usage: chart_daily.py CSV OUT_PNG
Each point is one satellite pass at about 03:30 Kyiv time, shown as the night it ends (file date d: night d-1 to d)."""
import csv, datetime as dt, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

rows = list(csv.DictReader(open(sys.argv[1])))
days = [dt.date.fromisoformat(r["file_date_utc"]) for r in rows]
x = {d: k for k, d in enumerate(days)}                     # one slot per night
STYLE = {"Enerhodar": ("#c2410c", 2.6, "occupied"), "Kamianka-Dniprovska": ("#f59e0b", 1.1, "occupied"),
         "Vasylivka": ("#a16207", 1.1, "occupied"), "Nikopol": ("#1d4ed8", 1.1, "Ukrainian-held"),
         "Marhanets": ("#0891b2", 1.1, "Ukrainian-held"), "Pokrov": ("#6366f1", 1.1, "Ukrainian-held"),
         "Zaporizhzhia": ("#64748b", 1.1, "Ukrainian-held")}
D = lambda m, d: dt.date(2022, m, d)
fig, ax = plt.subplots(figsize=(13, 6.8), dpi=150)

# the plant in island mode: its last line cut 5 Sep, grid power back the evening of 10 Sep (Energoatom)
ax.axvspan(x[D(9, 5)] + 0.4, x[D(9, 11)] - 0.2, color="#fde68a", alpha=0.35, lw=0)
ax.text(x[D(9, 5)] + 0.5, 30, "Plant on its own reactor ('island mode'):\nlast line cut 5 Sep, grid power back\n"
        "evening of 10 Sep (Energoatom)", fontsize=7.5, va="top", color="#78350f")
# the blackout night
ax.axvspan(x[D(9, 9)] - 0.45, x[D(9, 9)] + 0.45, color="#c2410c", alpha=0.12, lw=0)
ax.annotate("Night of 8-9 Sep 2022:\nEnerhodar dark, the plant lit.\nIAEA, 9 Sep: shelling of the thermal\n"
            "plant's switchyard caused a\n'complete power black-out' in the city",
            (x[D(9, 9)], 0.1), xytext=(x[D(9, 9)] + 2.4, 0.016), fontsize=7.5, color="#7c2d12",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#c2410c", lw=0.6, alpha=0.92),
            arrowprops=dict(arrowstyle="-", color="#c2410c", lw=0.8), zorder=5)
for d, txt, ha in [(D(8, 25), "25 Aug: the plant's last line cut\nfor a day, its first complete\nloss of outside power (WNA)", "left"),
                   (D(9, 3), "3 Sep: last 750 kV\nline cut (Dniprovska)", "right")]:
    ax.axvline(x[d] + 0.5, color="#999", lw=0.8, ls=":")
    ax.text(x[d] + (0.55 if ha == "left" else 0.45), 30, txt, fontsize=7.5, va="top", ha=ha, color="#444")

for name, (c, lw, bank) in STYLE.items():
    pts = [(x[d], float(r[name])) for d, r in zip(days, rows) if r[name]]
    ax.plot([p[0] for p in pts], [max(p[1], 0.01) for p in pts], "-o", color=c, lw=lw, ms=4.5 if lw > 2 else 3,
            label=f"{name} ({bank})", zorder=3 if lw > 2 else 2)
for d in (D(9, 8), D(9, 9), D(9, 12)):                       # the three nights in the close-up image
    ax.text(x[d], 0.013, "close-up", fontsize=6.5, ha="center", color="#555")

ax.set_xticks(range(len(days)))
ax.set_xticklabels([f"{(d - dt.timedelta(1)).day}-{d.day}\n{d:%b}" if d.day != 1 else f"{(d - dt.timedelta(1)).day} Aug-\n1 Sep"
                    for d in days], fontsize=7)
ax.set_xlabel("Night, August-September 2022 (each point: the satellite's pass at about 03:30 Kyiv time, "
              "at the end of that night)", fontsize=8.5)
ax.set_xlim(-0.6, len(days) - 0.4)
ax.set_yscale("log"); ax.set_ylim(0.01, 40)
ax.set_ylabel("night-time brightness, town average within 2 km\n(nW/cm²/sr, log scale: each line up = 10x brighter)",
              fontsize=8.5)
ax.set_title("Night lights round the Zaporizhzhia NPP, 23 August to 15 September 2022", fontsize=11, loc="left",
             fontweight="bold")
fig.text(0.008, 0.005, "NASA Black Marble VNP46A2 (Suomi NPP), clear-sky good-quality pixels only, never gap-filled. "
         "A gap in a line: that night too cloudy over the town (under 80% of its pixels usable).", fontsize=7, color="#555")
ax.grid(axis="y", color="#eee"); ax.spines[["top", "right"]].set_visible(False)
ax.legend(fontsize=7, loc="lower left", frameon=False, ncol=4, bbox_to_anchor=(0, 0.02))
fig.tight_layout(rect=(0, 0.02, 1, 1)); fig.savefig(sys.argv[2])
