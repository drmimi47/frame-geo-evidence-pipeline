"""Fetch VNP46A3 monthly tiles one at a time, keep a crop of the study area as .npz, delete the .h5.
Usage: monthly.py ENV_FILE OUT_DIR YYYY-MM [YYYY-MM ...]. The token is only sent in the Authorization header."""
import datetime as dt, json, os, re, sys, urllib.request
from pathlib import Path
import h5py, numpy as np
env, out, months = sys.argv[1], Path(sys.argv[2]), sys.argv[3:]
tok = re.search(r"^EARTHDATA_TOKEN=(\S+)", Path(env).read_text(), re.M).group(1)
out.mkdir(parents=True, exist_ok=True)
G = "HDFEOS/GRIDS/VIIRS_Grid_DNB_2d/Data Fields/"
BOX = tuple(map(float, os.environ.get("BOX", "33.95,35.40,47.30,47.95").split(",")))
PRODUCT = os.environ.get("PRODUCT", "VNP46A3")
ONLY = os.environ.get("ONLY", "")
for ym in months:
    dst = out / f"{ym}.npz"
    if dst.exists(): print(ym, "have"); continue
    y, m = map(int, ym.split("-")); doy = dt.date(y, m, 1).timetuple().tm_yday
    base = f"https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/5200/{PRODUCT}/{y}/{doy:03d}"
    try:
        lst = json.load(urllib.request.urlopen(base + ".json", timeout=60))
        lst = lst.get("content", lst) if isinstance(lst, dict) else lst
        if isinstance(lst, dict): lst = list(lst.values())
        f = next(x for x in lst if ".h21v04." in x["name"])
        req = urllib.request.Request(f["downloadsLink"], headers={"Authorization": f"Bearer {tok}"})
        tmp = out / (ym + ".h5")
        with urllib.request.urlopen(req, timeout=600) as r: tmp.write_bytes(r.read())
        with h5py.File(tmp, "r") as h:
            lat, lon = h[G + "lat"][:], h[G + "lon"][:]
            j0, j1 = np.searchsorted(lon, BOX[0]), np.searchsorted(lon, BOX[1])
            i0, i1 = np.searchsorted(-lat, -BOX[3]), np.searchsorted(-lat, -BOX[2])
            keep = {k: h[G + k][i0:i1, j0:j1] for k in h[G[:-1]].keys() if h[G + k].ndim == 2 and (not ONLY or k.startswith(ONLY))}
            attrs = {k: str(dict(h[G + k].attrs).get("long_name", b"")) for k in keep}
        np.savez_compressed(dst, lat=lat[i0:i1], lon=lon[j0:j1], source=f["name"], names=json.dumps(attrs), **keep)
        tmp.unlink(); print(ym, "ok", f["name"])
    except Exception as e:
        print(ym, "failed", type(e).__name__, str(e)[:80])
