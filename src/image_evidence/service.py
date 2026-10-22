"""Read-side service: the image-evidence API a frontend consumes.

Pure Python and transport-agnostic (the FastAPI app in ``api.py`` is a thin
wrapper). It depends only on the Repository interface, never on ingestion code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .schema import FrameRecord, VideoRecord
from .sorting import SORTS, by_query_image, by_study_place
from .store import FrameQuery, Repository


@dataclass
class EvidenceService:
    repo: Repository
    media_base: str = "/media/"  # prefix joined to library-relative paths
    _videos: dict[str, VideoRecord | None] = field(default_factory=dict, repr=False)
    query_images: dict[str, Any] = field(default_factory=dict, repr=False)  # id -> embedding of an uploaded image
    study_places: dict[str, tuple[Any, float]] = field(default_factory=dict)  # name -> (place, radius_km): "near:" sorts
    has_file: Callable[[str], bool] = lambda rel: True  # is this library-relative file still on disk
    # The library's satellite chips (satellite/store.py SatelliteIndex), or None. They join the grid as one group per
    # pass, ahead of the videos; text and year filter them, categories and image sorts don't (they aren't classified).
    satellite: Any = None

    def _url(self, rel: str) -> str:
        return self.media_base + rel

    def _video(self, video_id: str) -> VideoRecord | None:
        if video_id not in self._videos:
            self._videos[video_id] = self.repo.get_video(video_id)
        return self._videos[video_id]

    def summary(self, f: FrameRecord) -> dict[str, Any]:
        """Compact shape for grid tiles."""
        v = self._video(f.source.video_id)
        top = f.inferred.locations[0] if f.inferred.locations else None
        return {
            "frame_id": f.frame_id,
            "video_id": f.source.video_id,
            "frame_number": f.frame.frame_number,
            "selection": f.frame.selection,
            "thumb_url": self._url(f.frame.files.thumb),
            "web_url": self._url(f.frame.files.web),
            "width": f.frame.width,
            "height": f.frame.height,
            "timestamp_s": f.frame.timestamp_s,
            "published_at": f.source.published_at.isoformat(),
            "video_title": v.source.title if v else None,
            "channel_title": v.source.channel_title if v else None,
            "duration_s": v.source.duration_s if v else None,
            "categories": [c.label for c in f.derived.categories],
            "category_scores": {c.label: c.confidence for c in f.derived.categories},
            "inferred_place": {"name": top.place_name, "confidence": top.confidence} if top and top.place_name else None,
            "has_coordinates": any(loc.latitude is not None for loc in f.inferred.locations),
        }

    # ------------------------------------------------------------ satellite chips

    def sat_summary(self, c, p, georef: dict[str, Any], group: str) -> dict[str, Any]:
        """A chip in the grid's shape: its pass is the group (the "video"), its distance along the line the time."""
        from .satellite.store import pass_title

        return {
            "frame_id": c.chip_id, "video_id": group, "kind": "satellite", "frame_number": c.source.station,
            "selection": c.chip.kind, "thumb_url": self._url(c.chip.files.thumb), "web_url": self._url(c.chip.files.web),
            "width": c.chip.width, "height": c.chip.height, "timestamp_s": c.source.along_m,
            "published_at": c.source.acquired_at.isoformat(), "video_title": pass_title(p),
            "channel_title": p.source.provider, "duration_s": georef["line"]["length_m"],
            "categories": [], "category_scores": {}, "inferred_place": None, "has_coordinates": True,
        }

    def film_summary(self, fr: dict[str, Any], film: dict[str, Any], group: str) -> dict[str, Any]:
        """A frame of a film in the grid's shape: the film is the group, its time in the film the time. Its "year" is
        the acquisition of the pass it shows most of."""
        passes = {p["pass_id"]: p for p in film["passes"]}
        main = passes[max(fr["passes"], key=lambda x: x["weight"])["pass_id"]]
        return {
            "frame_id": fr["frame_id"], "video_id": group, "kind": "satellite", "sat_kind": "film",
            "frame_number": fr["n"], "selection": fr["shot"], "thumb_url": self._url(fr["files"]["thumb"]),
            "web_url": self._url(fr["files"]["web"]), "width": fr["width"], "height": fr["height"],
            "timestamp_s": fr["t"], "published_at": main["acquired_at"], "video_title": f"Film · {film['corridor']}",
            "channel_title": "The Conductive Seam", "duration_s": film["duration_s"], "film_id": film["film_id"],
            "categories": [], "category_scores": {}, "inferred_place": None, "has_coordinates": True,
        }

    def _film_items(self, words: list[str], year: int | None) -> list[dict[str, Any]]:
        out = []
        for group, film, frames in self.satellite.films():
            hay = " ".join([film["corridor"], film["line"]["label"], "film satellite", *(p["title"] for p in film["passes"]),
                            *(n["text"] for n in film.get("notes") or [])]).lower()
            if not all(w in hay for w in words):
                continue
            items = [self.film_summary(fr, film, group) for fr in frames]
            out += [it for it in items if not year or it["published_at"].startswith(str(year))]
        return out

    def _sat_items(self, text: str | None, categories: list[str] | None, year: int | None) -> list[dict[str, Any]]:
        from .satellite.store import pass_title

        if self.satellite is None or categories:
            return []
        words = (text or "").lower().split()
        out = self._film_items(words, year)  # the film's frames first, then the passes' chips
        for group, p, georef, chips in self.satellite.groups():
            t = p.source.acquired_at
            hay = " ".join([pass_title(p), p.source.sensor,
                            p.source.collection, georef["name"], georef["line"]["label"], f"{t:%Y-%m-%d %B %Y}",
                            "satellite"]).lower()
            if (year and t.year != year) or not all(w in hay for w in words):
                continue
            out += [self.sat_summary(c, p, georef, group) for c in chips]
        return out

    @staticmethod
    def _with_sat_years(facets: dict[str, Any], sat: list[dict[str, Any]]) -> dict[str, Any]:
        years = dict(facets.get("year", {}))
        for it in sat:
            y = it["published_at"][:4]
            years[y] = years.get(y, 0) + 1
        return {**facets, "year": dict(sorted(years.items()))}

    def search(
        self,
        text: str | None = None,
        categories: list[str] | None = None,
        year: int | None = None,
        youtube_id: str | None = None,
        min_confidence: float = 0.0,
        limit: int = 60,
        offset: int = 0,
        sort: str = "video",
        image: str | None = None,
    ) -> dict[str, Any]:
        sat = [] if youtube_id else self._sat_items(text, categories, year)
        if sort in SORTS or (sort == "image" and image in self.query_images) or (sort.startswith("near:") and sort[5:] in self.study_places):
            return self._sorted_search(sort, text, categories, year, youtube_id, min_confidence, limit, offset, image, sat)
        # the satellite chips first (one group per pass), then the videos' frames
        limit = min(limit, 500)
        head = sat[offset : offset + limit]
        rest = limit - len(head)
        page = self.repo.search_frames(FrameQuery(
            text=text or None,
            categories=tuple(categories or ()),
            year=year,
            youtube_id=youtube_id,
            min_confidence=min_confidence,
            limit=max(1, rest),
            offset=max(0, offset - len(sat)),
        ))
        frames = [self.summary(f) for f in self.repo.get_frames(page.frame_ids)] if rest > 0 else []
        return {
            "total": page.total + len(sat),
            "offset": offset,
            "items": head + frames,
            "facets": self._with_sat_years(page.facets, sat),
        }

    def _sorted_search(self, sort, text, categories, year, youtube_id, min_confidence, limit, offset, image=None, sat=()) -> dict[str, Any]:
        """Non-default orderings need every matching frame, so they sort in Python, then page. Satellite chips
        aren't sorted (they have no categories, features or embeddings): they follow, in pass and station order."""
        page = self.repo.search_frames(FrameQuery(
            text=text or None, categories=tuple(categories or ()), year=year, youtube_id=youtube_id,
            min_confidence=min_confidence, limit=1_000_000, offset=0,
        ))
        records = self.repo.get_frames(page.frame_ids)
        emb = self.repo.get_embeddings(page.frame_ids) if sort in ("similar", "image") else {}
        if sort == "image":
            rows = by_query_image(records, emb, self.query_images[image])
        elif sort.startswith("near:"):
            rows = by_study_place(records, *self.study_places[sort.removeprefix("near:")])
        else:
            rows = SORTS[sort](records, emb)
        items = [{**self.summary(f), "sort_group": g, "sort_note": n} for f, g, n in rows]
        items += [{**it, "sort_group": f"satellite {it['video_id']}", "sort_note": "Satellite imagery: not sorted, in "
                   "pass and station order (it isn't classified)"} for it in sat]
        return {
            "total": page.total + len(sat),
            "offset": offset,
            "sort": sort,
            "items": items[offset : offset + min(limit, 500)],
            "facets": self._with_sat_years(page.facets, list(sat)),
        }

    def stats(self) -> dict[str, int]:
        page = self.repo.search_frames(FrameQuery(limit=1))
        groups = self.satellite.groups() if self.satellite is not None else []
        out = {"videos": len(self.repo.list_videos(100_000, 0)), "frames": page.total}
        if groups:  # a folder with satellite passes: its chips and its film's frames are images too
            chips = sum(len(g[3]) for g in groups)
            film_frames = sum(len(f[2]) for f in self.satellite.films())
            out.update(frames=page.total + chips + film_frames, passes=len(groups), chips=chips)
            if film_frames:
                out["film_frames"] = film_frames
        return out

    def satellite_chip(self, chip_id: str) -> dict[str, Any] | None:
        """A chip's full record with its pass and corridor, for the panel."""
        from .satellite.store import pass_title

        found = self.satellite.chip(chip_id) if self.satellite is not None else None
        if found is None:
            return None
        c, p, georef = found
        return {
            "kind": "satellite", **c.model_dump(mode="json"),
            "urls": {"web": self._url(c.chip.files.web), "thumb": self._url(c.chip.files.thumb)},
            "pass": {**p.model_dump(mode="json"), "title": pass_title(p)},
            "corridor": {"corridor_id": georef["corridor_id"], "name": georef["name"], "line": georef["line"]["label"],
                         "length_m": georef["line"]["length_m"], "stations": len(georef["stations"]),
                         "osm": georef["osm"], "provenance": georef["provenance"]},
        }

    def film_frame(self, frame_id: str) -> dict[str, Any] | None:
        """A film frame's record with its film: passes, the shot it is in, and the note shown under the film then."""
        found = self.satellite.film_frame(frame_id) if self.satellite is not None else None
        if found is None:
            return None
        fr, film = found
        t = fr["t"]
        return {
            "kind": "satellite", "sat_kind": "film", **fr,
            "urls": {"web": self._url(fr["files"]["web"]), "thumb": self._url(fr["files"]["thumb"])},
            "film": {k: film.get(k) for k in ("film_id", "corridor_id", "corridor", "line", "duration_s", "statement",
                                              "created_at", "sha256", "notes_statement")}
                    | {"passes": [p for p in film["passes"] if p["pass_id"] in {x["pass_id"] for x in fr["passes"]}],
                       "segment": next((s for s in film["segments"] if s["t0"] <= t < s["t1"]), film["segments"][-1]),
                       "insets": film.get("insets") or []},
            "note": next((n for n in film.get("notes") or [] if n["t0"] <= t < n["t1"]), None),
        }

    def frame(self, frame_id: str) -> dict[str, Any] | None:
        """Full record for the lightbox, including the source video's metadata."""
        if frame_id.startswith("sat_film_"):
            return self.film_frame(frame_id)
        if frame_id.startswith("sat_"):
            return self.satellite_chip(frame_id)
        f = self.repo.get_frame(frame_id)
        if f is None:
            return None
        v = self._video(f.source.video_id)
        files = f.frame.files
        return {
            **f.model_dump(mode="json"),
            # the full-resolution file only while it exists (new frames keep none; `evidence slim` removes old ones)
            "urls": {"original": self._url(files.original) if files.original and self.has_file(files.original) else None, "web": self._url(files.web), "thumb": self._url(files.thumb)},
            "video": {
                "video_id": v.video_id,
                "source": v.source.model_dump(mode="json", exclude={"description"}),
                "acquisition_status": v.acquisition.status if v.acquisition else None,
                "text_categories": [c.model_dump(mode="json") for c in v.derived.text_categories],
            } if v else None,
        }

    def related(self, frame_id: str, radius_km: float = 5.0, limit: int = 24) -> list[dict[str, Any]]:
        """Related frames: geographic proximity first, then shared inferred place, then same video."""
        f = None if frame_id.startswith("sat_") else self.repo.get_frame(frame_id)
        if f is None:
            return []
        out: dict[str, dict[str, Any]] = {}

        def add(ids: list[str], relation: str, **extra: Any) -> None:
            for other in self.repo.get_frames([i for i in ids if i != frame_id and i not in out]):
                if len(out) >= limit:
                    return
                out[other.frame_id] = {**self.summary(other), "relation": relation, **extra.get(other.frame_id, {})}

        for loc in f.inferred.locations:
            if loc.latitude is not None:
                near = self.repo.frames_near(loc.latitude, loc.longitude, radius_km, limit * 2)
                add([n.frame_id for n in near], "geo_proximity", **{n.frame_id: {"distance_km": n.distance_km} for n in near})
                break
        for loc in f.inferred.locations:
            if loc.place_name and len(out) < limit:
                add(self.repo.frames_at_place(loc.place_name, limit * 2), "same_inferred_place")
        if len(out) < limit:
            page = self.repo.search_frames(FrameQuery(youtube_id=f.source.youtube_id, limit=500))
            same = sorted(self.repo.get_frames(page.frame_ids), key=lambda o: abs(o.frame.timestamp_s - f.frame.timestamp_s))
            add([o.frame_id for o in same], "same_video")
        return list(out.values())

    def videos(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        """The videos, then (on the first page) the satellite passes in the same shape: their "duration" is the
        line's length and each chip's "time" its distance along it, for the panel's tally."""
        from .satellite.store import pass_title

        passes = [{"video_id": group, "kind": "satellite", "title": pass_title(p), "published_at": p.source.acquired_at.isoformat(),
                   "frames": len(chips), "duration_s": georef["line"]["length_m"], "acquisition_status": "satellite",
                   "frame_times": [[c.chip_id, c.source.along_m] for c in chips]}
                  for group, p, georef, chips in (self.satellite.groups() if self.satellite is not None and offset == 0 else [])]
        films = [{"video_id": group, "kind": "satellite", "sat_kind": "film", "title": f"Film · {film['corridor']}",
                  "published_at": film["created_at"], "frames": len(frames), "duration_s": film["duration_s"],
                  "acquisition_status": "satellite", "frame_times": [[fr["frame_id"], fr["t"]] for fr in frames]}
                 for group, film, frames in (self.satellite.films() if self.satellite is not None and offset == 0 else [])]
        return films + passes + [
            {
                "video_id": v.video_id,
                "youtube_id": v.source.youtube_id,
                "title": v.source.title,
                "title_en": english_title(v),
                "published_at": v.source.published_at.isoformat(),
                "source_url": v.source.source_url,
                "acquisition_status": v.acquisition.status if v.acquisition else None,
                "frames": len(v.frame_ids),
                "duration_s": v.source.duration_s,
                # (frame_id, timestamp_s) for every frame, for the timeline tally
                "frame_times": sorted(
                    ([f.frame_id, f.frame.timestamp_s] for f in self.repo.get_frames(v.frame_ids)),
                    key=lambda ft: ft[1],
                ),
            }
            for v in self.repo.list_videos(limit, offset)
        ]

    def video(self, video_id: str) -> dict[str, Any] | None:
        v = self.repo.get_video(video_id)
        return v.model_dump(mode="json") if v else None


def english_title(v: VideoRecord) -> dict[str, Any]:
    """The title YouTube shows an English-language viewer: the uploader's English localization
    (en, then en-US/en-GB/...), or the original title when the uploader set none."""
    locs = v.source.title_localizations
    lang = "en" if "en" in locs else next((k for k in sorted(locs) if k.lower().startswith("en")), None)
    if lang and locs[lang].strip() and locs[lang] != v.source.title:
        return {"text": locs[lang], "language": lang, "source": "uploader"}
    return {"text": v.source.title, "language": v.source.default_language, "source": "original"}
