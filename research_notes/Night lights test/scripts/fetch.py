"""Download Black Marble tiles from LAADS. Usage: fetch.py ENV_FILE OUT_DIR PRODUCT YEAR DOY_FROM DOY_TO [TILE]
The token is read from ENV_FILE and only ever sent in the Authorization header; never printed."""
import json, re, sys, time, urllib.request
from pathlib import Path
env, out, product, year, d0, d1 = sys.argv[1:7]
tile = sys.argv[7] if len(sys.argv) > 7 else "h21v04"
tok = re.search(r"^EARTHDATA_TOKEN=(\S+)", Path(env).read_text(), re.M).group(1)
out = Path(out); out.mkdir(parents=True, exist_ok=True)
base = f"https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/5200/{product}/{year}"
for doy in range(int(d0), int(d1) + 1):
    try:
        lst = json.load(urllib.request.urlopen(f"{base}/{doy:03d}.json", timeout=60))
    except Exception as e:
        print(doy, "list failed", type(e).__name__); continue
    lst = lst.get("content", lst) if isinstance(lst, dict) else lst
    if isinstance(lst, dict): lst = list(lst.values())
    f = next((x for x in lst if f".{tile}." in x["name"]), None)
    if not f:
        print(doy, "no tile"); continue
    dst = out / f["name"]
    if dst.exists() and dst.stat().st_size == f["size"]:
        print(doy, "have"); continue
    for attempt in range(3):
        try:
            req = urllib.request.Request(f["downloadsLink"], headers={"Authorization": f"Bearer {tok}"})
            with urllib.request.urlopen(req, timeout=300) as r:
                data = r.read()
            if data[:4] != b"\x89HDF":
                raise ValueError("not HDF5 (auth page?)")
            dst.write_bytes(data); print(doy, "ok", len(data)); break
        except Exception as e:
            print(doy, "try", attempt, type(e).__name__, str(e)[:80]); time.sleep(5)
