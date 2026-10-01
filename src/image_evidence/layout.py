"""On-disk library layout. All paths stored in records are relative to the library root.

library/
  evidence.db                       SQLite index (rebuildable from JSON via `evidence reindex`)
  runs/<run_id>.json                discovery + ingestion log per run
  videos/<youtube_id>/
    video.json                      normalized VideoRecord
    raw/youtube_api.json            verbatim YouTube Data API videos.list item
    raw/ytdlp_info.json             verbatim (sanitized) yt-dlp info dict
    raw/captions.json               YouTube captions: original track (+ the uploader's English, if any)
    derived/captions_en.json        local machine translation of the captions into English
    media/<youtube_id>.<ext>        source media, where permitted
    thumbnails/youtube_<size>.jpg   YouTube-provided thumbnails
    frames/original/<frame_id>.png  original-quality frames
    frames/web/<frame_id>.webp      web derivative
    frames/thumb/<frame_id>.webp    grid thumbnail
    frames/meta/<frame_id>.json     normalized FrameRecord
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def write_json(path: Path, data: Any) -> None:
    """Atomic JSON write."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str))
    tmp.replace(path)


@dataclass(frozen=True)
class VideoDirs:
    root: Path

    @property
    def video_json(self) -> Path:
        return self.root / "video.json"

    @property
    def raw(self) -> Path:
        return self.root / "raw"

    @property
    def media(self) -> Path:
        return self.root / "media"

    @property
    def thumbnails(self) -> Path:
        return self.root / "thumbnails"

    @property
    def originals(self) -> Path:
        return self.root / "frames" / "original"

    @property
    def web(self) -> Path:
        return self.root / "frames" / "web"

    @property
    def thumbs(self) -> Path:
        return self.root / "frames" / "thumb"

    @property
    def meta(self) -> Path:
        return self.root / "frames" / "meta"

    def create(self) -> "VideoDirs":
        for d in (self.raw, self.media, self.thumbnails, self.originals, self.web, self.thumbs, self.meta):
            d.mkdir(parents=True, exist_ok=True)
        return self


@dataclass(frozen=True)
class Library:
    root: Path

    @property
    def db_path(self) -> Path:
        return self.root / "evidence.db"

    @property
    def runs(self) -> Path:
        return self.root / "runs"

    @property
    def videos(self) -> Path:
        return self.root / "videos"

    def video(self, youtube_id: str) -> VideoDirs:
        return VideoDirs(self.videos / youtube_id)

    def rel(self, path: Path) -> str:
        return path.resolve().relative_to(self.root.resolve()).as_posix()

    def abs(self, rel: str) -> Path:
        return self.root / rel

    def create(self) -> "Library":
        self.runs.mkdir(parents=True, exist_ok=True)
        self.videos.mkdir(parents=True, exist_ok=True)
        return self
