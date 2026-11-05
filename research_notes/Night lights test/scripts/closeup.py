"""Close-ups round the plant for chosen nights. Usage: closeup.py IN_DIR OUT_PNG YYYY-MM-DD ..."""
import datetime as dt, glob, sys
import h5py, numpy as np
from PIL import Image, ImageDraw, ImageFont
G = "HDFEOS/GRIDS/VIIRS_Grid_DNB_2d/Data Fields/"
BOX = (34.25, 34.85, 47.40, 47.70); SC = 7
MARK = [("Enerhodar", 47.49048, 34.66199), ("ZNPP", 47.5085556, 34.5879012), ("Nikopol", 47.56826, 34.39126),
        ("Marhanets", 47.63088, 34.6245), ("Kamianka-Dn.", 47.49629, 34.41026)]
tiles = []
TAG = {"2022-09-08": "BEFORE", "2022-09-09": "THE BLACKOUT: Enerhodar dark, the plant lit", "2022-09-12": "AFTER"}
for ds in sys.argv[3:]:
    d = dt.date.fromisoformat(ds)
    p = glob.glob(f"{sys.argv[1]}/VNP46A2.A{d.year}{d.timetuple().tm_yday:03d}.*.h5")[0]
    f = h5py.File(p, "r"); lat, lon = f[G + "lat"][:], f[G + "lon"][:]
    j0, j1 = np.searchsorted(lon, BOX[0]), np.searchsorted(lon, BOX[1]); i0, i1 = np.searchsorted(-lat, -BOX[3]), np.searchsorted(-lat, -BOX[2])
    s = np.s_[i0:i1, j0:j1]
    ntl = f[G + "DNB_BRDF-Corrected_NTL"][s]; mqf = f[G + "Mandatory_Quality_Flag"][s]; c = (f[G + "QF_Cloud_Mask"][s] >> 6) & 3
    ok = (ntl >= 0) & np.isin(mqf, (0, 1)) & (c <= 1)
    v = np.clip(np.log10(np.maximum(ntl, 0) + 1) / np.log10(41), 0, 1)
    g = (v * 255).astype(np.uint8); rgb = np.stack([g, g, g], -1); rgb[~ok] = (70, 20, 20)
    im = Image.fromarray(rgb).resize((rgb.shape[1] * SC, rgb.shape[0] * SC), Image.NEAREST)
    dr = ImageDraw.Draw(im); la, lo = lat[i0:i1], lon[j0:j1]
    for name, y, x in MARK:
        px = (x - lo[0]) / (lo[1] - lo[0]) * SC + SC / 2; py = (y - la[0]) / (la[1] - la[0]) * SC + SC / 2
        dr.ellipse((px - 5, py - 5, px + 5, py + 5), outline=(255, 190, 0), width=2); dr.text((px + 8, py - 6), name, fill=(255, 210, 90))
    head = Image.new("RGB", (im.width, 40), "black"); hd = ImageDraw.Draw(head)
    hd.text((6, 5), f"Night of {(d - dt.timedelta(1)).day}-{d.day} September 2022 (satellite pass about 03:30 Kyiv time, {d.day} Sep)", fill="white")
    hd.text((6, 22), TAG.get(ds, ""), fill=(255, 140, 90) if "BLACKOUT" in TAG.get(ds, "") else (200, 200, 200))
    t = Image.new("RGB", (im.width, im.height + 40)); t.paste(head, (0, 0)); t.paste(im, (0, 40)); tiles.append(t)
W = sum(t.width for t in tiles) + 8 * (len(tiles) - 1)
out = Image.new("RGB", (W, tiles[0].height + 22), "black"); x = 0
for t in tiles: out.paste(t, (x, 0)); x += t.width + 8
ImageDraw.Draw(out).text((6, tiles[0].height + 5), "NASA Black Marble VNP46A2. Black: no light. Grey to white: light (log scale, 0-40 nW/cm2/sr). Dark red: cloud or poor quality, no data. North up; each square about 460 x 310 m. 5-10 Sep the plant ran on its own reactor (Energoatom).", fill=(180, 180, 180))
out.save(sys.argv[2])
