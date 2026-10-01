"""Storage interface.

JSON sidecars on disk are the canonical record; a Repository is a queryable
index over them that can always be rebuilt (`evidence reindex`). Swapping SQLite
for PostgreSQL/PostGIS means implementing this Protocol -- the ingestion
pipeline and the service layer only see this interface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from ..schema import FrameRecord, VideoRecord


@dataclass(frozen=True)
class FrameQuery:
    text: str | None = None  # free text, parsed by search.parse_query (categories, places, video text)
    categories: tuple[str, ...] = ()  # all must match
    min_confidence: float = 0.0
    year: int | None = None  # publication year
    youtube_id: str | None = None
    has_coordinates: bool | None = None
    bbox: tuple[float, float, float, float] | None = None  # min_lon, min_lat, max_lon, max_lat
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True)
class NearbyFrame:
    frame_id: str
    distance_km: float


@dataclass
class SearchPage:
    frame_ids: list[str]
    total: int
    facets: dict[str, dict[str, int]] = field(default_factory=dict)


class Repository(Protocol):
    def upsert_video(self, video: VideoRecord) -> None: ...

    def upsert_frame(self, frame: FrameRecord) -> None: ...

    def delete_frames_for_video(self, video_id: str) -> None: ...

    def delete_video(self, video_id: str) -> None: ...

    def get_video(self, video_id: str) -> VideoRecord | None: ...

    def get_frame(self, frame_id: str) -> FrameRecord | None: ...

    def get_frames(self, frame_ids: list[str]) -> list[FrameRecord]: ...

    def search_frames(self, q: FrameQuery) -> SearchPage: ...

    def frames_near(self, lat: float, lon: float, radius_km: float, limit: int = 50) -> list[NearbyFrame]: ...

    def frames_at_place(self, place_name: str, limit: int = 50) -> list[str]: ...

    def list_videos(self, limit: int = 100, offset: int = 0) -> list[VideoRecord]: ...

    def close(self) -> None: ...
