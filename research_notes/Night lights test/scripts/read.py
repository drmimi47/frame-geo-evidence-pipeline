"""Read Black Marble daily tiles (VNP46A2) for the study towns. Usage: read.py IN_DIR OUT_DIR
Only DNB_BRDF-Corrected_NTL (never Gap_Filled), and only pixels with Mandatory_Quality_Flag 0/1 and a cloud mask of
confident or probably clear. Writes towns.csv, chart.png and contact.png into OUT_DIR."""
import csv, datetime as dt, re, sys
from pathlib import Path

import h5py
import numpy as np
from PIL import Image, ImageDraw, ImageFont

IN, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
G = "HDFEOS/GRIDS/VIIRS_Grid_DNB_2d/Data Fields/"
# GeoNames points (src/image_evidence/data/ua_places.tsv.gz); bank as of September 2022
TOWNS = [("Enerhodar", 47.49048, 34.66199, "occupied"), ("Kamianka-Dniprovska", 47.49629, 34.41026, "occupied"),
         ("Vasylivka", 47.44218, 35.28213, "occupied"), ("Nikopol", 47.56826, 34.39126, "Ukrainian"),
         ("Marhanets", 47.63088, 34.6245, "Ukrainian"), ("Pokrov", 47.65361, 34.11488, "Ukrainian"),
         ("Zaporizhzhia", 47.85167, 35.11714, "Ukrainian")]
R_KM = 2.0
BOX = (33.95, 35.40, 47.30, 47.95)  # lon0, lon1, lat0, lat1 for the contact sheet


def night(path):
    m = re.search(r"\.A(\d{4})(\d{3})\.", path.name)
    d = dt.date(int(m[1]), 1, 1) + dt.timedelta(int(m[2]) - 1)
    with h5py.File(path, "r") as f:
        ntl = f[G + "DNB_BRDF-Corrected_NTL"][:]
        mqf = f[G + "Mandatory_Quality_Flag"][:]
        cld = f[G + "QF_Cloud_Mask"][:]
        snow = f[G + "Snow_Flag"][:]
        lat, lon = f[G + "lat"][:], f[G + "lon"][:]
    clear = ((cld >> 6) & 3) <= 1
    ok = (ntl >= 0) & np.isin(mqf, (0, 1)) & clear & (snow != 1)
    return d, ntl, ok, lat, lon


def main():
    files = sorted(IN.glob("VNP46A2.A*.h5"))
    rows, crops = [], []
    for p in files:
        d, ntl, ok, lat, lon = night(p)
        row = {"file_date_utc": d.isoformat(), "local_night": f"{d - dt.timedelta(1):%d %b} to {d:%d %b}"}
        for name, la, lo, bank in TOWNS:
            dy = (lat[:, None] - la) * 111.2
            dx = (lon[None, :] - lo) * 111.2 * np.cos(np.radians(la))
            near = dx ** 2 + dy ** 2 <= R_KM ** 2
            n = int(near.sum()); good = near & ok
            row[f"{name}_valid"] = round(good.sum() / n, 2)
            row[name] = round(float(ntl[good].mean()), 2) if good.sum() >= 0.8 * n else ""
        rows.append(row)
        j0, j1 = np.searchsorted(lon, BOX[0]), np.searchsorted(lon, BOX[1])
        i0, i1 = np.searchsorted(-lat, -BOX[3]), np.searchsorted(-lat, -BOX[2])
        crops.append((d, ntl[i0:i1, j0:j1], ok[i0:i1, j0:j1], lat[i0:i1], lon[j0:j1]))
    with open(OUT / "towns.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    contact(crops)
    print(f"{len(rows)} nights; columns: town mean radiance (nW/cm²/sr) within {R_KM} km, blank if <80% clear")
    for r in rows:
        print(r["local_night"].ljust(17), " ".join(f"{t[0][:6]}:{str(r[t[0]]) or '-':>6}" for t in TOWNS))


def contact(crops, scale=2, cols=6):
    font = ImageFont.load_default()
    h, w = crops[0][1].shape
    W, H = w * scale, h * scale + 14
    sheet = Image.new("RGB", (cols * W, ((len(crops) + cols - 1) // cols) * H), "black")
    for k, (d, ntl, ok, lat, lon) in enumerate(crops):
        v = np.clip(np.log10(np.maximum(ntl, 0) + 1) / np.log10(101), 0, 1)   # 0-100 nW, log
        g = (v * 255).astype(np.uint8)
        rgb = np.stack([g, g, g], -1)
        rgb[~ok] = (70, 20, 20)                                               # not clear or poor quality: dark red
        im = Image.fromarray(rgb).resize((W, H - 14), Image.NEAREST)
        dr = ImageDraw.Draw(im)
        for name, la, lo, _ in TOWNS:
            x = (lo - lon[0]) / (lon[1] - lon[0]) * scale; y = (la - lat[0]) / (lat[1] - lat[0]) * scale
            dr.ellipse((x - 2, y - 2, x + 2, y + 2), outline=(255, 200, 0))
        tile = Image.new("RGB", (W, H), "black"); tile.paste(im, (0, 14))
        ImageDraw.Draw(tile).text((3, 1), f"night {d - dt.timedelta(1):%d}-{d:%d %b}, ~03:30 Kyiv", fill="white", font=font)
        sheet.paste(tile, ((k % cols) * W, (k // cols) * H))
    sheet.save(OUT / "contact.png")


main()
