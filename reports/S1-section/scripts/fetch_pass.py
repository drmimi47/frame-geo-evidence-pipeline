"""S1: one Sentinel-2 pass cropped to the section's blocks (10 m, north up), its true colour (the project's one tone
curve), its water as the bed's rule sees it (bed.channels) and its clear mask. Open data (Copernicus via Planetary
Computer); saved in the scratchpad, not the library.
Usage: fetch_pass.py OUT_DIR DATE HH:MM (the overpass, UTC)"""
import json, sys
from datetime import date
from pathlib import Path

import httpx
import numpy as np
from PIL import Image

from image_evidence.satellite import providers
from image_evidence.satellite.corridor import Grid
from image_evidence.satellite.scene3d.bed import channels
from image_evidence.satellite.stitch import fetch as fetch_tile

out = Path(sys.argv[1]); day, hhmm = sys.argv[2], sys.argv[3]
pl = json.load(open("libraries/conductive-seam/satellite/networks/znpp/scenes/crossing3d/scene.json"))["plane"]
lon = lambda x: pl["lon0"] + x / pl["kx"]; lat = lambda y: pl["lat0"] + y / pl["kz"]
bbox = (lon(-10500), lat(-4500), lon(7500), lat(14500))
grid = Grid(bbox=bbox, m_per_px=10.0)
s = providers.SENSORS["sentinel-2"]
with httpx.Client(timeout=120) as c:
    items = providers.search(s, bbox, date.fromisoformat(day), date.fromisoformat(day), 100.0, c)
    group = next(g for g in providers.overpasses(items) if providers.acquired(g[0]).strftime("%H:%M") == hhmm)
    m = fetch_tile(s, group, grid, c, piece_px=1024)
d = out / f"{day}_{hhmm.replace(':', '')}"; d.mkdir(parents=True, exist_ok=True)
Image.fromarray(m.rgb()).save(d / "rgb.webp", "WEBP", quality=92)
water = channels(np.nan_to_num(m.rgb_refl[1]).astype(np.float32), np.nan_to_num(m.nir).astype(np.float32),
                 np.nan_to_num(m.swir).astype(np.float32), m.clear)
np.savez_compressed(d / "masks.npz", water=water, clear=m.clear, valid=m.valid)
doc = {"date": day, "acquired": providers.acquired(group[0]).isoformat(), "items": [it["id"] for it in group],
       "grid": grid.to_json(), "clear_share": round(float(m.clear.mean()), 4), "valid_share": round(float(m.valid.mean()), 4),
       "water_share": round(float(water.mean()), 4), "licence": s.licence, "attribution": s.attribution.format(year=int(day[:4])),
       "requests": m.requests}
(d / "pass.json").write_text(json.dumps(doc, indent=1))
print(d.name, "clear", doc["clear_share"], "valid", doc["valid_share"], "water", doc["water_share"])
