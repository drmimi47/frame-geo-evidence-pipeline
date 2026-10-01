"""Video discovery through the official YouTube Data API v3.

Quota: search.list costs 100 units per call; videos.list costs 1 unit per call
(up to 50 ids). The default daily quota is 10,000 units.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, time, timezone
from typing import Any, Iterable

import httpx

from .config import DiscoveryConfig
from .schema import ClaimedLocation, DiscoveryContext, SourceVideo

log = logging.getLogger(__name__)

API_BASE = "https://www.googleapis.com/youtube/v3"
VIDEO_PARTS = "snippet,contentDetails,status,recordingDetails,statistics,topicDetails,localizations"
SEARCH_COST = 100


class DiscoveryError(RuntimeError):
    pass


@dataclass(frozen=True)
class SearchSpec:
    query: str
    location: str | None
    category: str | None
    published_after: datetime
    published_before: datetime
    geo: tuple[float, float, float] | None = None  # lat, lon, radius_km


@dataclass
class Candidate:
    youtube_id: str
    contexts: list[DiscoveryContext] = field(default_factory=list)
    api_item: dict[str, Any] | None = None
    rank: Any = None  # focus.Rank when a study area is configured


def _utc(d, end: bool = False) -> datetime:
    return datetime.combine(d, time.max if end else time.min).replace(tzinfo=timezone.utc, microsecond=0)


def year_windows(cfg: DiscoveryConfig) -> list[tuple[datetime, datetime]]:
    start, end = _utc(cfg.published_after), _utc(cfg.published_before, end=True)
    if not cfg.split_by_year:
        return [(start, end)]
    windows = []
    for year in range(start.year, end.year + 1):
        lo = max(start, datetime(year, 1, 1, tzinfo=timezone.utc))
        hi = min(end, datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc))
        windows.append((lo, hi))
    return windows


def build_search_specs(cfg: DiscoveryConfig) -> list[SearchSpec]:
    """Expand locations x category terms x year windows (+ literal extra queries)."""
    specs: list[SearchSpec] = []
    windows = year_windows(cfg)
    locations = cfg.locations or [None]
    for lo, hi in windows:
        for loc in locations:
            for cat in cfg.categories:
                for term in cat.terms:
                    q = cfg.query_template.format(location=loc.name if loc else "", term=term)
                    geo = (loc.latitude, loc.longitude, loc.radius_km) if loc and loc.geo_filter else None
                    specs.append(SearchSpec(" ".join(q.split()), loc.name if loc else None, cat.name, lo, hi, geo))
        for q in cfg.extra_queries:
            specs.append(SearchSpec(q, None, None, lo, hi))
        if cfg.focus:
            from .focus import area

            circle = area(cfg.focus).circle()  # videos the uploader geotagged inside the study area
            for term in cfg.focus.geotagged_terms:
                specs.append(SearchSpec(term, None, "geotagged", lo, hi, circle))
    return specs


def estimate_quota(cfg: DiscoveryConfig) -> int:
    return len(build_search_specs(cfg)) * SEARCH_COST + cfg.max_videos_total // 50 + 1


class YouTubeClient:
    def __init__(self, api_key: str, http: httpx.Client | None = None):
        self.api_key = api_key
        self.http = http or httpx.Client(timeout=30)

    @classmethod
    def from_env(cls, env_var: str) -> "YouTubeClient":
        key = os.environ.get(env_var)
        if not key:
            raise DiscoveryError(f"Set ${env_var} to a YouTube Data API v3 key (https://console.cloud.google.com/apis/library/youtube.googleapis.com)")
        return cls(key)

    def _get(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        params = {k: v for k, v in params.items() if v is not None}
        resp = self.http.get(f"{API_BASE}/{endpoint}", params={**params, "key": self.api_key})
        if resp.status_code != 200:
            try:
                err = resp.json()["error"]
                msg = f"{err.get('code')} {err.get('message')}"
            except Exception:
                msg = resp.text[:300]
            raise DiscoveryError(f"YouTube API {endpoint} failed: {msg}")
        return resp.json()

    def search(self, spec: SearchSpec, cfg: DiscoveryConfig, max_results: int) -> list[str]:
        params: dict[str, Any] = {
            "part": "snippet",
            "type": "video",
            "q": spec.query or None,  # no q: any video (geotag searches)
            "maxResults": min(max_results, 50),
            "order": cfg.order,
            "publishedAfter": spec.published_after.isoformat().replace("+00:00", "Z"),
            "publishedBefore": spec.published_before.isoformat().replace("+00:00", "Z"),
            "videoLicense": None if cfg.video_license == "any" else cfg.video_license,
            "videoDuration": None if cfg.video_duration == "any" else cfg.video_duration,
            "regionCode": cfg.region_code,
            "relevanceLanguage": cfg.relevance_language,
            "safeSearch": cfg.safe_search,
        }
        if spec.geo:
            lat, lon, radius = spec.geo
            params["location"] = f"{lat},{lon}"
            params["locationRadius"] = f"{radius:g}km"
        data = self._get("search", params)
        return [it["id"]["videoId"] for it in data.get("items", []) if it.get("id", {}).get("videoId")]

    def videos(self, ids: Iterable[str]) -> dict[str, dict[str, Any]]:
        ids = list(dict.fromkeys(ids))
        out: dict[str, dict[str, Any]] = {}
        for i in range(0, len(ids), 50):
            data = self._get("videos", {"part": VIDEO_PARTS, "id": ",".join(ids[i : i + 50]), "maxResults": 50})
            for item in data.get("items", []):
                out[item["id"]] = item
        return out


def discover(cfg: DiscoveryConfig, client: YouTubeClient, run_id: str) -> list[Candidate]:
    """Run all search specs; return de-duplicated candidates with full API metadata."""
    candidates: dict[str, Candidate] = {}
    specs = build_search_specs(cfg)
    log.info("discovery: %d searches (~%d quota units)", len(specs), estimate_quota(cfg))
    for spec in specs:
        if len(candidates) >= cfg.max_videos_total:
            break
        try:
            ids = client.search(spec, cfg, cfg.max_results_per_query)
        except DiscoveryError as e:
            log.error("search %r failed: %s", spec.query or "(geotagged)", e)
            if "quota" in str(e).lower():
                break
            continue
        log.info("  %-50s %s..%s -> %d", repr(spec.query) + (" (geotagged)" if spec.geo else ""), spec.published_after.year, spec.published_before.date(), len(ids))
        for rank, vid in enumerate(ids):
            ctx = DiscoveryContext(
                run_id=run_id,
                query=spec.query,
                location=spec.location,
                category=spec.category,
                published_after=spec.published_after,
                published_before=spec.published_before,
                geo_filtered=spec.geo is not None,
                rank=rank,
            )
            if vid in candidates:
                candidates[vid].contexts.append(ctx)
            elif len(candidates) < cfg.max_videos_total:
                candidates[vid] = Candidate(vid, [ctx])
    details = client.videos(candidates)
    for vid, cand in candidates.items():
        cand.api_item = details.get(vid)
    found = [c for c in candidates.values() if c.api_item]
    if cfg.focus:
        from .focus import rank

        for c in found:
            c.rank = rank(c.api_item, cfg.focus)
        # best placed first; ties keep the search engine's order
        found.sort(key=lambda c: (-c.rank.score, min(ctx.rank for ctx in c.contexts)))
    return found


# --------------------------------------------------------------------------
# Normalization: API item -> SourceVideo
# --------------------------------------------------------------------------

_DURATION = re.compile(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?")


def parse_iso_duration(value: str | None) -> float | None:
    if not value:
        return None
    m = _DURATION.fullmatch(value)
    if not m:
        return None
    d, h, mi, s = (float(x) if x else 0.0 for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


def _dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def _int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def source_from_api(item: dict[str, Any]) -> SourceVideo:
    sn = item.get("snippet", {})
    st = item.get("status", {})
    stats = item.get("statistics", {})
    rec = item.get("recordingDetails", {}) or {}
    loc = rec.get("location") or {}
    claimed_loc = None
    if loc or rec.get("locationDescription"):
        claimed_loc = ClaimedLocation(
            latitude=loc.get("latitude"),
            longitude=loc.get("longitude"),
            altitude=loc.get("altitude"),
            description=rec.get("locationDescription"),
        )
    return SourceVideo(
        youtube_id=item["id"],
        source_url=f"https://www.youtube.com/watch?v={item['id']}",
        title=sn.get("title", ""),
        title_localizations={k: v["title"] for k, v in (item.get("localizations") or {}).items() if v.get("title")},
        description=sn.get("description", ""),
        channel_id=sn.get("channelId"),
        channel_title=sn.get("channelTitle"),
        published_at=_dt(sn["publishedAt"]),
        duration_s=parse_iso_duration(item.get("contentDetails", {}).get("duration")),
        tags=tuple(sn.get("tags", [])),
        category_id=sn.get("categoryId"),
        default_language=sn.get("defaultLanguage") or sn.get("defaultAudioLanguage"),
        license=st.get("license"),
        privacy_status=st.get("privacyStatus"),
        embeddable=st.get("embeddable"),
        view_count=_int(stats.get("viewCount")),
        like_count=_int(stats.get("likeCount")),
        thumbnails={k: v["url"] for k, v in sn.get("thumbnails", {}).items() if "url" in v},
        claimed_recording_date=_dt(rec.get("recordingDate")),
        claimed_recording_location=claimed_loc,
        retrieved_via=("youtube_data_api_v3",),
    )
