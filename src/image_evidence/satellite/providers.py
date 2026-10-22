"""Satellite products from Microsoft Planetary Computer: STAC search and cropped reads through its data API.

No key is needed (scripts/scene/terrain.py uses the same service). A crop is asked for in lon/lat (EPSG:4326) at an
exact pixel size, so its pixels fall on the corridor's grid; the reply is NumPy (`.npy`): the asked bands as stored
(uint16), then a validity mask (255 = data). The data API times out now and then (504): requests are retried.
"""

from __future__ import annotations

import hashlib
import io
import logging
import time
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Callable

import httpx
import numpy as np

log = logging.getLogger(__name__)

PROVIDER = "Microsoft Planetary Computer"
STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
DATA_URL = "https://planetarycomputer.microsoft.com/api/data/v1"
MAX_CROP_PX = 2048  # per side, per request


@dataclass(frozen=True)
class Sensor:
    name: str                       # "sentinel-2" | "landsat"
    label: str                      # for titles
    collection: str
    bands: tuple[str, ...]          # assets for blue, green, red, nir, swir (in that order)
    mask_asset: str                 # scene classification / pixel QA, read with nearest-neighbour resampling
    gsd_m: float
    licence: str
    attribution: str                # with {year}
    first_year: int
    reflectance: Callable[[np.ndarray, dict[str, Any]], np.ndarray]  # stored values -> reflectance x 10000
    clouds: Callable[[np.ndarray], np.ndarray]                       # mask band -> cloud or shadow (bool)


def _s2_reflectance(dn: np.ndarray, props: dict[str, Any]) -> np.ndarray:
    # L2A since processing baseline 04.00 (January 2022, and every reprocessed item) adds 1000 to every value
    try:
        offset = 1000 if float(props.get("s2:processing_baseline") or "0") >= 4.0 else 0
    except ValueError:
        offset = 1000
    return np.clip(dn.astype(np.float32) - offset, 0, None)


def _landsat_reflectance(dn: np.ndarray, props: dict[str, Any]) -> np.ndarray:
    # Collection 2 Level-2 surface reflectance: DN x 0.0000275 - 0.2
    return np.clip((dn.astype(np.float32) * 0.0000275 - 0.2) * 10000, 0, None)


SENSORS: dict[str, Sensor] = {
    "sentinel-2": Sensor(
        name="sentinel-2", label="Sentinel-2", collection="sentinel-2-l2a",
        bands=("B02", "B03", "B04", "B08", "B11"), mask_asset="SCL", gsd_m=10.0,
        licence="Copernicus Sentinel data: free, full and open access (Copernicus data policy)",
        attribution="Contains modified Copernicus Sentinel data {year}", first_year=2015,
        reflectance=_s2_reflectance,
        clouds=lambda scl: np.isin(scl, (3, 8, 9, 10)),  # cloud shadow, cloud medium/high probability, cirrus
    ),
    "landsat": Sensor(
        name="landsat", label="Landsat", collection="landsat-c2-l2",
        bands=("blue", "green", "red", "nir08", "swir16"), mask_asset="qa_pixel", gsd_m=30.0,
        licence="USGS Landsat: public domain",
        attribution="Landsat imagery courtesy of the U.S. Geological Survey", first_year=1982,
        reflectance=_landsat_reflectance,
        clouds=lambda qa: (qa.astype(np.uint16) & 0b11010) > 0,  # dilated cloud, cloud, cloud shadow
    ),
}


def _retry(fn: Callable[[], httpx.Response], what: str, attempts: int = 4) -> httpx.Response:
    for k in range(attempts):
        try:
            r = fn()
            if r.status_code < 500 or k == attempts - 1:
                r.raise_for_status()
                return r
        except (httpx.TimeoutException, httpx.TransportError):
            if k == attempts - 1:
                raise
        wait = 5 * (k + 1)
        log.info("%s: the server is busy, trying again in %d s", what, wait)
        time.sleep(wait)
    raise RuntimeError("unreachable")


def search(sensor: Sensor, bbox: tuple[float, float, float, float], start: date, end: date, max_cloud: float,
           http: httpx.Client) -> list[dict[str, Any]]:
    """Every item of the sensor's collection over the box between the dates (both included), clearest first."""
    body: dict[str, Any] = {
        "collections": [sensor.collection], "bbox": list(bbox),
        "datetime": f"{start.isoformat()}T00:00:00Z/{end.isoformat()}T23:59:59Z",
        "query": {"eo:cloud_cover": {"lte": max_cloud}}, "limit": 100,
        "sortby": [{"field": "eo:cloud_cover", "direction": "asc"}],
    }
    if sensor.name == "landsat":  # Landsat 4-9 Level-2 only (MSS has no surface reflectance)
        body["query"]["platform"] = {"in": ["landsat-4", "landsat-5", "landsat-7", "landsat-8", "landsat-9"]}
    items: list[dict[str, Any]] = []
    url: str | None = f"{STAC_URL}/search"
    while url and len(items) < 1000:
        r = _retry(lambda: http.post(url, json=body, timeout=120), "STAC search")
        d = r.json()
        items += d.get("features", [])
        nxt = next((ln for ln in d.get("links", []) if ln.get("rel") == "next"), None)
        url, body = (nxt["href"], nxt.get("body") or body) if nxt else (None, body)
    return items


def latest_processing(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sentinel-2 items reprocessed later keep their acquisition name with a newer processing time at the end
    (S2A_MSIL2A_20230923T083641_R064_T36TXT_<processed>): keep only the newest of each."""
    best: dict[str, dict[str, Any]] = {}
    for it in items:
        key = it["id"].rsplit("_", 1)[0] if it["id"].startswith("S2") else it["id"]
        if key not in best or it["id"] > best[key]["id"]:
            best[key] = it
    return list(best.values())


def acquired(item: dict[str, Any]) -> datetime:
    return datetime.fromisoformat(item["properties"]["datetime"].replace("Z", "+00:00"))


def overpasses(items: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Items grouped by overpass: the same platform within the same minute (the tiles of one strip)."""
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for it in latest_processing(items):
        key = (it["properties"].get("platform", ""), acquired(it).strftime("%Y%m%dT%H%M"))
        groups.setdefault(key, []).append(it)
    return list(groups.values())


def item_url(collection: str, item_id: str) -> str:
    return f"{STAC_URL}/collections/{collection}/items/{item_id}"


def crop(sensor: Sensor, item_id: str, assets: tuple[str, ...], bbox: tuple[float, float, float, float],
         width: int, height: int, resampling: str, http: httpx.Client) -> tuple[np.ndarray, dict[str, Any]]:
    """The assets over the box at width x height (lon/lat linear, north row first). Returns (array, request record):
    the array is (len(assets) + 1, height, width), the last band the validity mask (255 = data)."""
    w, s, e, n = bbox
    url = f"{DATA_URL}/item/bbox/{w!r},{s!r},{e!r},{n!r}/{width}x{height}.npy"
    params = [("collection", sensor.collection), ("item", item_id), *[("assets", a) for a in assets],
              ("resampling", resampling)]
    r = _retry(lambda: http.get(url, params=params, timeout=300), f"crop {item_id}")
    arr = np.load(io.BytesIO(r.content), allow_pickle=False)
    if arr.shape != (len(assets) + 1, height, width):
        raise RuntimeError(f"unexpected crop shape {arr.shape} for {item_id}")
    record = {"url": url, "params": params, "bytes": len(r.content), "sha256": hashlib.sha256(r.content).hexdigest(),
              "fetched_at": datetime.now().astimezone().isoformat(timespec="seconds")}
    return arr, record
