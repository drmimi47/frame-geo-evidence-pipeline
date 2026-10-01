"""Study-area ranking: which discovered videos are about the area studied, and how well they can be placed.

A study area is a list of gazetteer places plus a radius (`discovery.focus`). Each candidate gets a score
from its API metadata only (no download), with a reason per point:
- the uploader geotag inside the area (strongest: it comes with coordinates);
- settlements of the area named in the title, tags, description or the uploader's location description,
  small places counting more than big cities (a village narrows the search far more than "Zaporizhzhia");
- coordinates or map links in the description, chapters naming places (they tie places to moments);
- the uploader's own captions (speech can be mined for places later);
- topic words (`focus.topic_terms`) for the subject studied, a small bonus.
Videos naming more places outside the area than inside lose a point. A video is only taken when it is in the
area and on topic: its text names a place there or uses a topic word. A geotag alone is where the uploader
lives, which for a pedicure clip says nothing about the area.

The score orders what gets ingested. It is search context, never evidence: nothing here is written onto a
frame, and the gazetteer coordinates are only used to test distances, never attached to anything.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from . import places
from .config import FocusSpec
from .geo_text import parse_chapters

BIG_CITY = 200_000          # a city this size narrows the search little: half weight
FIELD_WEIGHTS = {"title": 3.0, "location": 3.0, "description": 2.0, "tags": 1.5}
PLACES_CAP = 8.0
GEOTAG_IN_AREA, GEOTAG_ELSEWHERE = 4.0, 0.5
_COORDS = re.compile(r"(?<![\d.])(4[4-9]|5[0-2])[.,](\d{3,})\s*[,;/ ]\s*(2[2-9]|3\d|40)[.,](\d{3,})(?![\d.])")
_MAP_LINK = re.compile(r"google\.[a-z.]+/maps|maps\.app\.goo\.gl|goo\.gl/maps|openstreetmap\.org|maps\.apple\.com", re.I)


@dataclass(frozen=True)
class Area:
    anchors: tuple[places.Place, ...]
    radius_km: float

    def distance(self, lat: float, lon: float) -> float:
        return min(places.km(lat, lon, p.lat, p.lon) for p in self.anchors)

    def contains(self, lat: float | None, lon: float | None) -> bool:
        return lat is not None and lon is not None and self.distance(lat, lon) <= self.radius_km

    def circle(self) -> tuple[float, float, float]:
        """A circle around the whole area, for the API's geotag search (lat, lon, radius_km)."""
        lat = sum(p.lat for p in self.anchors) / len(self.anchors)
        lon = sum(p.lon for p in self.anchors) / len(self.anchors)
        r = max(places.km(lat, lon, p.lat, p.lon) for p in self.anchors) + self.radius_km
        return round(lat, 4), round(lon, 4), round(r)


def area(spec: FocusSpec) -> Area:
    return _area(tuple(spec.places), spec.radius_km)


@lru_cache(maxsize=8)
def _area(names: tuple[str, ...], radius_km: float) -> Area:
    found = {n: [p for p in places.lookup(n) if p.lat is not None] for n in names}
    if unknown := [n for n, ps in found.items() if not ps]:
        raise ValueError(f"focus places not in the gazetteer: {', '.join(unknown)}")
    # Names with one entry fix where the area is; a name shared by several places (Біленьке, Водяне) is the
    # one nearest to those. With no single-entry name, the biggest places stand in.
    sure = [ps[0] for ps in found.values() if len(ps) == 1] or [max(ps, key=lambda p: p.population) for ps in found.values()]
    lat, lon = sorted(p.lat for p in sure)[len(sure) // 2], sorted(p.lon for p in sure)[len(sure) // 2]
    anchors = [min(ps, key=lambda p: places.km(lat, lon, p.lat, p.lon)) for ps in found.values()]
    return Area(tuple(dict.fromkeys(anchors)), radius_km)


@dataclass
class Rank:
    score: float = 0.0
    in_area: bool = False
    on_topic: bool = False  # names a place of the area in its text, or a topic word: a geotag alone isn't enough
    places: list[str] = field(default_factory=list)     # the area's places the video names
    reasons: list[str] = field(default_factory=list)

    def add(self, points: float, reason: str) -> None:
        self.score = round(self.score + points, 2)
        self.reasons.append(f"{points:+g} {reason}")


def rank(item: dict[str, Any], spec: FocusSpec) -> Rank:
    a = area(spec)
    sn = item.get("snippet", {})
    rec = item.get("recordingDetails") or {}
    r = Rank()

    texts = {"title": sn.get("title", ""), "location": rec.get("locationDescription") or "",
             "description": sn.get("description", ""), "tags": " | ".join(sn.get("tags", []))}
    best: dict[str, tuple[float, str]] = {}   # place -> (points, field)
    outside: dict[str, str] = {}              # place -> first field naming it
    maybe: list[tuple[str, float, str]] = []    # names shared with a place elsewhere ("Lviv", "Novopavlivka")
    for fld, text in texts.items():
        if not text:
            continue
        for m in places.find_places(text, proper_nouns_only=fld == "tags"):
            located = [p for p in m.places if p.lat is not None]
            if not located:
                continue  # oblasts and regions: too coarse to place anything
            inside = [p for p in located if a.contains(p.lat, p.lon)]
            if not inside:
                outside.setdefault(m.name, fld)
                continue
            w = FIELD_WEIGHTS[fld] * (0.5 if max(p.population for p in inside) >= BIG_CITY else 1.0)
            if len(inside) < len(located) and max(p.population for p in located) < BIG_CITY:
                maybe.append((m.name, w, fld))  # villages sharing a name: which one is meant is unknown
            elif max(located, key=lambda p: p.population) not in inside:
                maybe.append((m.name, w, fld))  # a bigger place elsewhere has this name
            elif w > best.get(m.name, (0.0, ""))[0]:
                best[m.name] = (w, fld)
    # a shared name counts for the area only when the video also names a place there that isn't shared
    sure = bool(best)
    for name, w, fld in maybe:
        if sure and w > best.get(name, (0.0, ""))[0]:
            best[name] = (w, fld)
        elif not sure:
            outside.setdefault(name, fld)
    named_here = any(fld != "location" for _, fld in best.values())

    loc = rec.get("location") or {}
    if loc.get("latitude") is not None and loc.get("longitude") is not None:
        if not a.contains(loc["latitude"], loc["longitude"]):
            r.add(GEOTAG_ELSEWHERE, f"uploader geotag {a.distance(loc['latitude'], loc['longitude']):.0f} km from the area")
        elif outside and not named_here:
            r.in_area = True  # the newsroom's city, often, while the video is about somewhere else
            r.add(1.0, "uploader geotag inside the area, but the video only names places elsewhere")
        else:
            r.in_area = True
            r.add(GEOTAG_IN_AREA, "uploader geotag inside the area")
    if best:
        r.in_area = True
        r.on_topic = named_here
        r.places = sorted(best, key=lambda n: -best[n][0])
        pts = min(PLACES_CAP, sum(w for w, _ in best.values()))
        r.add(pts, "names " + ", ".join(f"{n} ({best[n][1]})" for n in r.places))
    if any(fld == "title" for fld in outside.values()) and not any(fld == "title" for _, fld in best.values()):
        r.add(-1.5, "the title names a place elsewhere")
    elif len(outside) > len(best):
        r.add(-1.0, f"names more places outside the area ({len(outside)})")

    desc = texts["description"]
    if m := _COORDS.search(desc):
        lat, lon = float(f"{m[1]}.{m[2]}"), float(f"{m[3]}.{m[4]}")
        inside = a.contains(lat, lon)
        r.in_area |= inside
        r.add(4.0 if inside else 1.0, "coordinates in the description" + (" (inside the area)" if inside else ""))
    elif _MAP_LINK.search(desc):
        r.add(1.5, "map link in the description")
    chapters = parse_chapters(desc, None)
    if chapters and any(places.find_places(title) for _, _, title in chapters):
        r.add(1.0, "chapters name places")

    if item.get("contentDetails", {}).get("caption") == "true":
        r.add(0.5, "uploader captions")

    if spec.topic_terms:
        text = " ".join(texts.values()).lower()
        hits = [t for t in spec.topic_terms if re.search(rf"(?<!\w){re.escape(t.lower())}", text)]
        if hits:
            r.on_topic = True
            r.add(min(1.5, 0.5 * len(hits)), "about " + ", ".join(hits[:4]))
    return r


# ------------------------------------------------------------------ the site's "Near a place" sorts


def study_places(specs: list[FocusSpec]) -> dict[str, tuple[places.Place, float]]:
    """English name -> (place, radius_km) for every place of the given study areas, in config order."""
    out: dict[str, tuple[places.Place, float]] = {}
    for spec in specs:
        for p in area(spec).anchors:
            out.setdefault(p.name, (p, spec.radius_km))
    return out


@lru_cache(maxsize=4096)
def _resolve(name: str) -> places.Place | None:
    """The gazetteer place a stored place name stands for (the biggest of that name). None for oblasts and
    regions, which are too coarse to be near anything."""
    if not name or name == "Ukraine" or name.endswith("Oblast"):
        return None
    for m in places.find_places(name, proper_nouns_only=True):  # a stored name is a proper noun, not a sentence start
        located = [p for p in m.places if p.lat is not None]
        if located:
            return max(located, key=lambda p: p.population)
    return None


def nearness(loc, target: places.Place) -> tuple[float, str] | None:
    """(km from target, what places it) for one inferred location: its own coordinates when it has them
    (uploader geotag), else the gazetteer position of the place it names. Distances only, never stored."""
    if loc.latitude is not None and loc.longitude is not None:
        return places.km(loc.latitude, loc.longitude, target.lat, target.lon), f"uploader geotag ({loc.place_name or 'no name'})"
    p = _resolve(loc.place_name or "")
    if p is None:
        return None
    return places.km(p.lat, p.lon, target.lat, target.lon), loc.place_name
