"""Permitted media acquisition and metadata preservation via yt-dlp.

This module never bypasses platform restrictions: no cookies, no login, no
age-gate or geo-block circumvention, no DRM handling. Videos that are not
public, are live, carry DRM, or are age-restricted are recorded as
``unavailable`` and skipped.
"""

from __future__ import annotations

import hashlib
import logging
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import yt_dlp

from .config import AcquisitionConfig
from .layout import Library, VideoDirs
from .schema import Acquisition, MediaFile, SourceVideo

log = logging.getLogger(__name__)

TOOL = f"yt-dlp {yt_dlp.version.__version__}"


class _QuietLogger:
    def debug(self, msg: str) -> None:
        pass

    def info(self, msg: str) -> None:
        pass

    def warning(self, msg: str) -> None:
        log.debug("yt-dlp: %s", msg)

    def error(self, msg: str) -> None:
        log.warning("yt-dlp: %s", msg)


def _js_runtimes() -> dict[str, dict]:
    # yt-dlp needs a JavaScript runtime to play YouTube's player JS. Use whatever is installed.
    return {name: {} for name in ("deno", "node", "bun") if shutil.which(name)}


def _base_opts() -> dict[str, Any]:
    return {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "logger": _QuietLogger(),
        "js_runtimes": _js_runtimes(),
        "cookiefile": None,
        "noplaylist": True,
    }


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_info(youtube_id: str) -> dict[str, Any]:
    """Metadata only. Returns the sanitized (JSON-serializable) yt-dlp info dict."""
    with yt_dlp.YoutubeDL(_base_opts()) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={youtube_id}", download=False)
        return ydl.sanitize_info(info)


def source_from_info(info: dict[str, Any]) -> SourceVideo:
    """Fallback SourceVideo when no Data API metadata is available."""
    ts = info.get("timestamp")
    if ts:
        published = datetime.fromtimestamp(ts, tz=timezone.utc)
    else:
        published = datetime.strptime(info["upload_date"], "%Y%m%d").replace(tzinfo=timezone.utc)
    # Keep YouTube's standard sizes (default, mq, hq, sd, maxres), named as the Data API names them.
    sizes = {"default": "default", "mqdefault": "medium", "hqdefault": "high", "sddefault": "standard", "maxresdefault": "maxres"}
    thumbs = {}
    for t in info.get("thumbnails", []):
        url = (t.get("url") or "").split("?")[0]
        stem = url.rsplit("/", 1)[-1].removesuffix(".jpg")
        if url.endswith(".jpg") and "/vi/" in url and stem in sizes:
            thumbs[sizes[stem]] = url
    return SourceVideo(
        youtube_id=info["id"],
        source_url=info.get("webpage_url") or f"https://www.youtube.com/watch?v={info['id']}",
        title=info.get("title") or "",
        description=info.get("description") or "",
        channel_id=info.get("channel_id"),
        channel_title=info.get("channel") or info.get("uploader"),
        published_at=published,
        duration_s=info.get("duration"),
        tags=tuple(info.get("tags") or ()),
        default_language=info.get("language"),
        license=None,  # yt-dlp does not reliably expose the YouTube license; unknown != creativeCommon
        privacy_status=info.get("availability"),
        view_count=info.get("view_count"),
        like_count=info.get("like_count"),
        thumbnails=thumbs,
        retrieved_via=("yt-dlp",),
    )


@dataclass(frozen=True)
class Decision:
    allowed: bool
    status: str
    reason: str


def decide(cfg: AcquisitionConfig, source: SourceVideo, info: dict[str, Any]) -> Decision:
    avail = info.get("availability")
    if avail not in (None, "public", "unlisted"):
        return Decision(False, "unavailable", f"availability={avail}")
    if info.get("is_live") or info.get("live_status") in ("is_live", "is_upcoming"):
        return Decision(False, "unavailable", "live or upcoming stream")
    if info.get("has_drm"):
        return Decision(False, "unavailable", "DRM-protected")
    if (info.get("age_limit") or 0) > 0:
        return Decision(False, "unavailable", "age-restricted (not bypassed)")
    if cfg.policy == "none":
        return Decision(False, "metadata_only", "acquisition policy is 'none'")
    if cfg.policy == "creative_commons" and source.license != "creativeCommon":
        return Decision(False, "skipped_policy", f"license={source.license or 'unknown'}; policy requires creativeCommon")
    duration = info.get("duration") or source.duration_s or 0
    if duration > cfg.max_duration_s:
        return Decision(False, "skipped_policy", f"duration {duration:.0f}s > max_duration_s {cfg.max_duration_s}")
    return Decision(True, "downloaded", f"policy={cfg.policy}, license={source.license or 'unknown'}")


def _format_selector(cfg: AcquisitionConfig) -> str:
    h = cfg.max_height
    # Prefer H.264 for decoder compatibility, then anything at/below max_height.
    if cfg.include_audio:
        return f"bv*[height<={h}][vcodec^=avc1]+ba[ext=m4a]/bv*[height<={h}]+ba/b[height<={h}]/b"
    return f"bv*[height<={h}][vcodec^=avc1]/bv*[height<={h}]/b[height<={h}]"


def download(cfg: AcquisitionConfig, dirs: VideoDirs, lib: Library, youtube_id: str) -> tuple[Acquisition, Path | None]:
    existing = sorted(p for p in dirs.media.glob(f"{youtube_id}.*") if p.suffix not in (".part", ".ytdl", ".json"))
    if existing:
        path = existing[0]
        return Acquisition(status="existing", policy=cfg.policy, media=MediaFile(path=lib.rel(path), ext=path.suffix[1:], sha256=sha256_file(path)), tool=TOOL), path

    opts = {
        **_base_opts(),
        "format": _format_selector(cfg),
        "merge_output_format": "mp4",
        "outtmpl": str(dirs.media / "%(id)s.%(ext)s"),
        "writeinfojson": False,
        "retries": 3,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={youtube_id}", download=True)
        info = ydl.sanitize_info(info)
    files = [Path(d["filepath"]) for d in info.get("requested_downloads", []) if d.get("filepath")]
    if not files or not files[0].exists():
        return Acquisition(status="failed", policy=cfg.policy, reason="yt-dlp produced no file", tool=TOOL), None
    path = files[0]
    media = MediaFile(
        path=lib.rel(path),
        format_id=info.get("format_id"),
        ext=path.suffix[1:],
        width=info.get("width"),
        height=info.get("height"),
        fps=info.get("fps"),
        vcodec=info.get("vcodec"),
        acodec=info.get("acodec"),
        filesize=path.stat().st_size,
        sha256=sha256_file(path),
    )
    return Acquisition(status="downloaded", policy=cfg.policy, media=media, tool=TOOL), path


def save_youtube_thumbnails(source: SourceVideo, dirs: VideoDirs, lib: Library) -> dict[str, str]:
    """Download the YouTube-provided thumbnails (published by YouTube for display)."""
    out: dict[str, str] = {}
    with httpx.Client(timeout=20, follow_redirects=True) as http:
        for size, url in source.thumbnails.items():
            ext = ".webp" if ".webp" in url else ".jpg"
            dest = dirs.thumbnails / f"youtube_{size}{ext}"
            if not dest.exists():
                try:
                    r = http.get(url)
                    r.raise_for_status()
                    dest.write_bytes(r.content)
                except httpx.HTTPError as e:
                    log.debug("thumbnail %s failed: %s", url, e)
                    continue
            out[size] = lib.rel(dest)
    return out

