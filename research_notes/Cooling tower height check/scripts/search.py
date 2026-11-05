import sys, json, httpx
from datetime import date
sys.path.insert(0, "src")
from image_evidence.satellite import providers as p
s2 = p.SENSORS["sentinel-2"]
bbox = (34.555, 47.500, 34.640, 47.530)
out = []
with httpx.Client() as h:
    for y in range(2018, 2026):
        for it in p.search(s2, bbox, date(y, 11, 15), date(y + 1, 1, 31), 2, h):
            pr = it["properties"]
            out.append((pr["datetime"][:16], round(pr["eo:cloud_cover"], 2), round(90 - pr.get("s2:mean_solar_zenith", 0), 2),
                        round(pr.get("s2:mean_solar_azimuth", 0), 1), it["id"]))
for o in sorted(out): print(*o)
json.dump(out, open(sys.argv[1], "w"))
