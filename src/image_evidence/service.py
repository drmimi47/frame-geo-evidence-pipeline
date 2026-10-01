"""Read-side service: the image-evidence API a frontend consumes.

Pure Python and transport-agnostic (the FastAPI app in ``api.py`` is a thin
wrapper). It depends only on the Repository interface, never on ingestion code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

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
        if sort in SORTS or (sort == "image" and image in self.query_images) or (sort.startswith("near:") and sort[5:] in self.study_places):
            return self._sorted_search(sort, text, categories, year, youtube_id, min_confidence, limit, offset, image)
        page = self.repo.search_frames(FrameQuery(
            text=text or None,
            categories=tuple(categories or ()),
            year=year,
            youtube_id=youtube_id,
            min_confidence=min_confidence,
            limit=min(limit, 500),
            offset=offset,
        ))
        return {
            "total": page.total,
            "offset": offset,
            "items": [self.summary(f) for f in self.repo.get_frames(page.frame_ids)],
            "facets": page.facets,
        }

    def _sorted_search(self, sort, text, categories, year, youtube_id, min_confidence, limit, offset, image=None) -> dict[str, Any]:
        """Non-default orderings need every matching frame, so they sort in Python, then page."""
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
        rows = rows[offset : offset + min(limit, 500)]
        return {
            "total": page.total,
            "offset": offset,
            "sort": sort,
            "items": [{**self.summary(f), "sort_group": g, "sort_note": n} for f, g, n in rows],
            "facets": page.facets,
        }

    def stats(self) -> dict[str, int]:
        page = self.repo.search_frames(FrameQuery(limit=1))
        return {"videos": len(self.repo.list_videos(100_000, 0)), "frames": page.total}

    def frame(self, frame_id: str) -> dict[str, Any] | None:
        """Full record for the lightbox, including the source video's metadata."""
        f = self.repo.get_frame(frame_id)
        if f is None:
            return None
        v = self._video(f.source.video_id)
        files = f.frame.files
        return {
            **f.model_dump(mode="json"),
            "urls": {"original": self._url(files.original), "web": self._url(files.web), "thumb": self._url(files.thumb)},
            "video": {
                "video_id": v.video_id,
                "source": v.source.model_dump(mode="json", exclude={"description"}),
                "acquisition_status": v.acquisition.status if v.acquisition else None,
                "text_categories": [c.model_dump(mode="json") for c in v.derived.text_categories],
            } if v else None,
        }

    def related(self, frame_id: str, radius_km: float = 5.0, limit: int = 24) -> list[dict[str, Any]]:
        """Related frames: geographic proximity first, then shared inferred place, then same video."""
        f = self.repo.get_frame(frame_id)
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
        return [
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
