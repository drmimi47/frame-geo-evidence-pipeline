"""Both satellites, same months, study towns and far controls. Usage: compare.py DIR_SNPP DIR_N20 OUT_CSV"""
import csv, sys
from pathlib import Path
import numpy as np
TOWNS = [("Enerhodar", 47.49048, 34.66199, "occ, by plant"), ("Kamianka-Dn.", 47.49629, 34.41026, "occ, front"),
         ("Vasylivka", 47.44218, 35.28213, "occ, front"), ("Dniprorudne", 47.38993, 35.00065, "occ, near front"),
         ("Melitopol", 46.84735, 35.38196, "occ, far"), ("Simferopol", 44.95719, 34.11079, "Crimea, far"),
         ("Nikopol", 47.56826, 34.39126, "UA, front"), ("Marhanets", 47.63088, 34.6245, "UA, front"),
         ("Zaporizhzhia", 47.85167, 35.11714, "UA, city"), ("Dnipro", 48.46664, 35.04066, "UA, far")]
def val(z, la, lo, r=2.0):
    lat, lon = z["lat"], z["lon"]
    near = ((lat[:, None] - la) * 111.2) ** 2 + ((lon[None, :] - lo) * 111.2 * np.cos(np.radians(la))) ** 2 <= r * r
    out = np.full(near.shape, np.nan, np.float32)
    for kind in ("Snow_Free", "Snow_Covered"):
        v, q = z[f"AllAngle_Composite_{kind}"], z[f"AllAngle_Composite_{kind}_Quality"]
        t = np.isnan(out) & (q == 0) & (v >= 0); out[t] = v[t]
    g = near & ~np.isnan(out)
    return round(float(out[g].mean()), 2) if g.sum() >= 0.8 * near.sum() else None
rows = []
months = sorted(p.stem for p in Path(sys.argv[1]).glob("*.npz"))
print("month    sat   " + " ".join(f"{t[0][:11]:>11}" for t in TOWNS))
print(" " * 15 + " ".join(f"{t[3][:11]:>11}" for t in TOWNS))
for m in months:
    for sat, d in (("SNPP", sys.argv[1]), ("N20", sys.argv[2])):
        z = np.load(Path(d) / f"{m}.npz")
        vals = [val(z, la, lo) for _, la, lo, _ in TOWNS]
        rows.append({"month": m, "satellite": sat, **{t[0]: v for t, v in zip(TOWNS, vals)}})
        print(f"{m}  {sat:5} " + " ".join(f"{('-' if v is None else v):>11}" for v in vals))
with open(sys.argv[3], "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
