"""An inferred camera path for one video, for the site's Temporal Map.

A claim about the world, so it lives in the video's `inferred/track.json` with its confidence and provenance, and
never reaches a frame record (`inferred.locations` stays as it is). It is built from sources that have their own
coordinates, never from a place name alone:

- the road: an OpenStreetMap driving route (OSRM) between a start and an end read off the uploader's own route map,
  shown in the video (the caller gives them, with a note saying where they came from);
- the timing: a dashcam clock burned into the frames ("GARMIN 12/09/2021 15:52:29", read by the stored OCR). A jump
  in the clock against the video's own time is a cut: the stretch of road driven meanwhile was not filmed.

Between the ends the camera is placed at the average speed over the clock time, so the position is least certain
mid-route. `sigma_m` is that uncertainty as a distance along the road (the camera is on the road; where on it is the
question). GeoNames settlements within reach of the route label it, by distance along it only.
"""

from __future__ import annotations

import gzip
import json
import math
import re
from datetime import datetime
from importlib import resources
from pathlib import Path
from typing import Any

import httpx

from .layout import write_json
from .schema import Provenance

OSRM = "https://router.project-osrm.org/route/v1/driving/"
USER_AGENT = "frame-geo-evidence-pipeline/0.1 (research prototype)"
CLOCK = re.compile(r"(\d{2})[./-](\d{2})[./-](\d{4})\s+(\d{1,2}):(\d{2}):(\d{2})")
SAME_CUT_S = 3.0          # clock-minus-video offsets this close belong to one continuous stretch
SIGMA_END_M = 300.0       # how well the ends are placed (read off the uploader's map)
SIGMA_PER_M = 0.08        # growth with distance from the nearer end (speed varies through villages)
SETTLEMENT_REACH_M = 1500.0
CONFIDENCE = 0.6          # inferred values are never certain; this one is a model of average speed


def track_path(video_dir: Path) -> Path:
    return video_dir / "inferred" / "track.json"


# ------------------------------------------------------------ geometry

def _haversine(a: tuple[float, float], b: tuple[float, float]) -> float:
    (lo1, la1), (lo2, la2) = a, b
    p1, p2 = math.radians(la1), math.radians(la2)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lo2 - lo1) / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(h))


def _bearing(a: tuple[float, float], b: tuple[float, float]) -> float:
    (lo1, la1), (lo2, la2) = a, b
    p1, p2, dl = math.radians(la1), math.radians(la2), math.radians(lo2 - lo1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def _cumulative(coords: list[list[float]]) -> list[float]:
    out = [0.0]
    for a, b in zip(coords, coords[1:]):
        out.append(out[-1] + _haversine(a, b))
    return out


def _at(coords: list[list[float]], cum: list[float], m: float) -> tuple[float, float]:
    m = min(max(m, 0.0), cum[-1])
    i = max(0, min(len(cum) - 2, next((k for k in range(1, len(cum)) if cum[k] >= m), len(cum) - 1) - 1))
    span = cum[i + 1] - cum[i] or 1.0
    f = (m - cum[i]) / span
    return (coords[i][0] + (coords[i + 1][0] - coords[i][0]) * f, coords[i][1] + (coords[i + 1][1] - coords[i][1]) * f)


def _heading(coords: list[list[float]], cum: list[float], m: float, window: float = 120.0) -> float:
    return _bearing(_at(coords, cum, m - window), _at(coords, cum, m + window))


# ------------------------------------------------------------ sources

def fetch_route(start: tuple[float, float], end: tuple[float, float], via: list[tuple[float, float]] = ()) -> dict:
    """OSRM driving route over OpenStreetMap roads. Points are (lat, lon)."""
    pts = ";".join(f"{lon:.6f},{lat:.6f}" for lat, lon in (start, *via, end))
    url = f"{OSRM}{pts}?overview=full&geometries=geojson&steps=true"
    r = httpx.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    r.raise_for_status()
    data = r.json()
    if data.get("code") != "Ok" or not data.get("routes"):
        raise RuntimeError(f"OSRM found no route: {data.get('code')} {data.get('message', '')}")
    return {"request": url, "response": data, "retrieved_at": datetime.now().astimezone().isoformat()}


def clock_readings(frames: list[dict]) -> list[tuple[float, datetime, str]]:
    """(video time, clock time, text) for every stored frame whose OCR shows a dashcam date and time."""
    out = []
    for f in frames:
        for line in ((f.get("derived") or {}).get("ocr") or {}).get("lines", []):
            m = CLOCK.search(line["text"])
            if not m:
                continue
            d, mo, y, h, mi, s = map(int, m.groups())
            try:
                out.append((f["frame"]["timestamp_s"], datetime(y, mo, d, h, mi, s), line["text"]))
            except ValueError:
                continue
            break
    return sorted(out, key=lambda r: r[0])


def segments(readings: list[tuple[float, datetime, str]], duration: float, drive_start: float | None,
             cuts: list[float] = ()) -> list[dict]:
    """Continuous stretches of footage: runs of readings whose clock keeps pace with the video. A cut lies between
    the last reading of one run and the first of the next: at a given cut time that falls there (measured on a denser
    read of the clock), else half way (the exact frame isn't stored)."""
    if not readings:
        raise ValueError("no dashcam clock in the stored frames' OCR (run `evidence relocate` first?)")
    runs: list[list[tuple[float, datetime, str]]] = []
    for r in readings:
        off = r[1].timestamp() - r[0]
        if runs and abs(off - (runs[-1][0][1].timestamp() - runs[-1][0][0])) <= SAME_CUT_S:
            runs[-1].append(r)
        else:
            runs.append([r])
    out = []
    for k, run in enumerate(runs):
        off = sorted(x[1].timestamp() - x[0] for x in run)[len(run) // 2]  # median: one misread digit doesn't move it
        v0 = (drive_start if drive_start is not None else run[0][0]) if k == 0 else out[-1]["video_end"]
        if k == len(runs) - 1:
            v1 = duration
        else:
            a, b = run[-1][0], runs[k + 1][0][0]
            v1 = next((c for c in cuts if a <= c <= b), (a + b) / 2)
        out.append({"video_start": round(v0, 2), "video_end": round(v1, 2), "clock_offset_s": off,
                    "clock_start": datetime.fromtimestamp(v0 + off).isoformat(timespec="seconds"),
                    "clock_end": datetime.fromtimestamp(v1 + off).isoformat(timespec="seconds"),
                    "readings": len(run), "first_reading": run[0][2], "last_reading": run[-1][2]})
    return out


def _settlements(coords: list[list[float]], cum: list[float]) -> list[dict]:
    raw = resources.files(__package__).joinpath("data/ua_places.tsv.gz").read_bytes()
    lo0, lo1 = min(c[0] for c in coords) - 0.05, max(c[0] for c in coords) + 0.05
    la0, la1 = min(c[1] for c in coords) - 0.05, max(c[1] for c in coords) + 0.05
    step = max(1, len(coords) // 400)
    out = []
    for line in gzip.decompress(raw).decode("utf-8").splitlines()[1:]:
        gid, name, fcode, oblast, pop, lat, lon, forms = line.split("\t")
        p = (float(lon), float(lat))
        if not (lo0 <= p[0] <= lo1 and la0 <= p[1] <= la1):
            continue
        d, k = min((_haversine(p, coords[k]), k) for k in range(0, len(coords), step))
        if d <= SETTLEMENT_REACH_M:
            # the Ukrainian spelling: a Cyrillic form with a letter Russian doesn't have
            uk = next((f for f in forms.split("|") if re.search(r"[ІіЇїЄєҐґ’]", f)), None)
            out.append({"name": name, "name_uk": uk, "geonameid": gid, "population": int(pop),
                        "along_m": round(cum[k]), "off_route_m": round(d)})
    return sorted(out, key=lambda s: s["along_m"])


# ------------------------------------------------------------ the track

def build(video: dict, frames: list[dict], route: dict, *, start: tuple[float, float], end: tuple[float, float],
          route_note: str, drive_start: float | None = None, cuts: list[float] = (), step_s: float = 1.0) -> dict[str, Any]:
    coords = route["response"]["routes"][0]["geometry"]["coordinates"]
    cum = _cumulative(coords)
    total = cum[-1]
    duration = float(video["source"]["duration_s"])
    segs = segments(clock_readings(frames), duration, drive_start, cuts)
    c0 = segs[0]["video_start"] + segs[0]["clock_offset_s"]
    c1 = segs[-1]["video_end"] + segs[-1]["clock_offset_s"]

    def along(t: float) -> float:
        if t <= segs[0]["video_start"]:
            return 0.0
        seg = next((s for s in segs if t < s["video_end"]), segs[-1])
        return total * min(1.0, max(0.0, (t + seg["clock_offset_s"] - c0) / (c1 - c0)))

    def sigma(m: float) -> float:
        return SIGMA_END_M + SIGMA_PER_M * min(m, total - m)

    samples = []
    t = 0.0
    while t <= duration + 1e-6:
        m = along(t)
        lon, lat = _at(coords, cum, m)
        samples.append([round(t, 2), round(m, 1), round(lon, 6), round(lat, 6),
                        round(_heading(coords, cum, m), 1), round(sigma(m))])
        t += step_s
    for s in segs:
        s["along_start_m"], s["along_end_m"] = round(along(s["video_start"] + 1e-3)), round(along(s["video_end"] - 1e-3))
    frame_points = []
    for f in sorted(frames, key=lambda f: f["frame"]["timestamp_s"]):
        ft = f["frame"]["timestamp_s"]
        m = along(ft)
        lon, lat = _at(coords, cum, m)
        ocr = [ln["text"] for ln in ((f.get("derived") or {}).get("ocr") or {}).get("lines", []) if not CLOCK.search(ln["text"])]
        frame_points.append({"frame_id": f["frame_id"], "t": ft, "along_m": round(m, 1), "lon": round(lon, 6),
                             "lat": round(lat, 6), "sigma_m": round(sigma(m)), "onscreen_text": ocr[:6]})
    created = datetime.now().astimezone()
    step0 = route["response"]["routes"][0]
    roads = sorted({st.get("ref") or st.get("name") for leg in step0["legs"] for st in leg["steps"]} - {"", None})
    return {
        "schema": "track/1",
        "tier": "inferred",
        "video_id": video["video_id"],
        "youtube_id": video["source"]["youtube_id"],
        "kind": "vehicle_dashcam",
        "confidence": CONFIDENCE,
        "summary": (f"Driven {total / 1000:.1f} km by road ({', '.join(roads) or 'OSM roads'}), filmed in "
                    f"{len(segs)} stretches; the camera is placed along the road at the average speed over the "
                    f"dashcam clock, so mid-route it is uncertain by up to ±{sigma(total / 2) / 1000:.1f} km."),
        "provenance": [
            Provenance(method="uploader_route_map", evidence=route_note, created_at=created).model_dump(mode="json"),
            Provenance(method="openstreetmap_route", model="OSRM (router.project-osrm.org)",
                       evidence=f"Driving route over OpenStreetMap roads ({', '.join(roads)}) between the start and end "
                                f"read off that map. Map data © OpenStreetMap contributors (ODbL).",
                       created_at=created).model_dump(mode="json"),
            Provenance(method="frame_onscreen_clock", model="apple_vision_ocr",
                       evidence=(f"Dashcam clock in the stored frames' OCR, {segs[0]['first_reading']} … "
                                 f"{segs[-1]['last_reading']}. The clock jumps {len(segs) - 1} time(s) against the video: "
                                 f"cuts, where the road driven meanwhile was not filmed."
                                 + (f" Cut times {', '.join(f'{c:g} s' for c in cuts)} measured on a denser read of the clock."
                                    if cuts else " Each cut is placed half way between the stored frames either side of it.")),
                       created_at=created).model_dump(mode="json"),
            Provenance(method="average_speed_model",
                       evidence=(f"Position = route length × elapsed clock time / total clock time "
                                 f"({(c1 - c0) / 60:.1f} min, {total / (c1 - c0) * 3.6:.0f} km/h on average). Real speed "
                                 f"varies (villages, junctions), so sigma grows from ±{SIGMA_END_M:.0f} m at the ends."),
                       created_at=created).model_dump(mode="json"),
        ],
        "capture": {"clock_start": datetime.fromtimestamp(c0).isoformat(timespec="seconds"), "clock_end": datetime.fromtimestamp(c1).isoformat(timespec="seconds"),
                    "note": "From the camera's own clock: when it was filmed, if the clock was set right."},
        "start": {"lat": start[0], "lon": start[1], "label": "A"},
        "end": {"lat": end[0], "lon": end[1], "label": "B"},
        "route": {"length_m": round(total, 1), "roads": roads, "coordinates": [[round(x, 6), round(y, 6)] for x, y in coords],
                  "along_m": [round(c, 1) for c in cum]},
        "segments": segs,
        "settlements": _settlements(coords, cum),
        "frames": frame_points,
        "sample_fields": ["t", "along_m", "lon", "lat", "heading_deg", "sigma_m"],
        "samples": samples,
        "created_at": created.isoformat(),
    }


def build_for(video_dir: Path, *, start: tuple[float, float], end: tuple[float, float], route_note: str,
              via: list[tuple[float, float]] = (), drive_start: float | None = None, cuts: list[float] = (),
              refetch: bool = False) -> dict:
    """Build and save `inferred/track.json` for a stored video. The OSRM answer is kept in `raw/route_osrm.json`
    and reused unless refetch (or the points changed)."""
    video = json.loads((video_dir / "video.json").read_text())
    frames = [json.loads(p.read_text()) for p in sorted((video_dir / "frames" / "meta").glob("*.json"))]
    cache = video_dir / "raw" / "route_osrm.json"
    route = json.loads(cache.read_text()) if cache.exists() and not refetch else None
    want = ";".join(f"{lon:.6f},{lat:.6f}" for lat, lon in (start, *via, end))
    if route is None or want not in route["request"]:
        route = fetch_route(start, end, list(via))
        write_json(cache, route)
    track = build(video, frames, route, start=start, end=end, route_note=route_note, drive_start=drive_start,
                  cuts=cuts)
    out = track_path(video_dir)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_json(out, track)
    return track
