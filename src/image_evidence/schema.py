"""Normalized metadata schema.

Every record separates three tiers of metadata, and the tier is part of the
field path so consumers can never confuse them:

1. ``source``   -- values reported directly by YouTube (Data API / yt-dlp).
                   Uploader-supplied claims (recording date/location) live here
                   too, but are explicitly named ``claimed_*``.
2. ``derived``  -- values computed deterministically or by a model from the
                   pixels of the frame (categories, quality metrics, hashes).
3. ``inferred`` -- interpretations about the real world (where / when the
                   footage was captured). Always carry confidence + provenance.
                   Unknown values stay ``None``; nothing is guessed.

The frame -> source video link (``FrameRecord.source`` and ``FrameRecord.frame``)
is frozen: pydantic refuses mutation, and the SQLite store enforces the same
invariant with a trigger.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "1.0"


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Mutable(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------
# Provenance
# --------------------------------------------------------------------------


class Provenance(Frozen):
    """How a derived or inferred value was produced."""

    method: str = Field(description="Machine-readable method id, e.g. 'siglip_zero_shot'.")
    model: str | None = Field(default=None, description="Model identifier, if a model was used.")
    evidence: str | None = Field(default=None, description="Human-readable justification.")
    created_at: datetime = Field(default_factory=utcnow)


# --------------------------------------------------------------------------
# 1. Source metadata (YouTube)
# --------------------------------------------------------------------------


class ClaimedLocation(Frozen):
    """Uploader-supplied recordingDetails.location. A claim, not a verified fact."""

    latitude: float | None = None
    longitude: float | None = None
    altitude: float | None = None
    description: str | None = None


class SourceVideo(Frozen):
    youtube_id: str
    source_url: str
    title: str
    title_localizations: dict[str, str] = Field(
        default_factory=dict,
        description="Titles the uploader set for other languages (YouTube API `localizations`), e.g. {'en': ...}. "
        "YouTube shows these to viewers in that language; otherwise it shows `title`.",
    )
    description: str = ""
    channel_id: str | None = None
    channel_title: str | None = None
    published_at: datetime = Field(description="YouTube publication time. NOT the capture date.")
    duration_s: float | None = None
    tags: tuple[str, ...] = ()
    category_id: str | None = None
    default_language: str | None = None
    license: str | None = Field(default=None, description="'youtube' | 'creativeCommon' (YouTube license field).")
    privacy_status: str | None = None
    embeddable: bool | None = None
    view_count: int | None = None
    like_count: int | None = None
    thumbnails: dict[str, str] = Field(default_factory=dict, description="size -> remote URL")
    claimed_recording_date: datetime | None = Field(default=None, description="Uploader-claimed recordingDetails.recordingDate.")
    claimed_recording_location: ClaimedLocation | None = None
    retrieved_via: tuple[str, ...] = Field(description="e.g. ('youtube_data_api_v3', 'yt-dlp')")
    retrieved_at: datetime = Field(default_factory=utcnow)


class DiscoveryContext(Frozen):
    """Which configured query found this video. Search context, not evidence."""

    run_id: str
    query: str
    location: str | None = None
    category: str | None = None
    published_after: datetime | None = None
    published_before: datetime | None = None
    geo_filtered: bool = False
    rank: int
    discovered_at: datetime = Field(default_factory=utcnow)


class MediaFile(Frozen):
    path: str = Field(description="Path relative to the library root.")
    format_id: str | None = None
    ext: str | None = None
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    vcodec: str | None = None
    acodec: str | None = None
    filesize: int | None = None
    sha256: str


class Acquisition(Frozen):
    status: Literal["downloaded", "existing", "skipped_policy", "unavailable", "failed", "metadata_only"]
    policy: str
    reason: str | None = None
    media: MediaFile | None = None
    tool: str | None = Field(default=None, description="e.g. 'yt-dlp 2025.09.26'")
    acquired_at: datetime = Field(default_factory=utcnow)


# --------------------------------------------------------------------------
# 2. Derived visual metadata
# --------------------------------------------------------------------------


class CategoryLabel(Frozen):
    label: str
    confidence: float = Field(ge=0.0, le=1.0)
    provenance: Provenance


class FrameQuality(Frozen):
    sharpness: float = Field(description="Variance of Laplacian (grayscale, full res).")
    brightness: float = Field(description="Mean luma 0-255.")
    contrast: float = Field(description="Std dev of luma.")
    dhash: str = Field(description="64-bit difference hash, hex.")


class VisualFeatures(Mutable):
    """Descriptive pixel statistics and zero-shot shares, used to sort frames (visual.py). Not claims about the world."""

    color_hex: str = Field(description="Mean colour.")
    hue: float | None = Field(default=None, description="Dominant hue in degrees (weighted by saturation x value); None if mostly grey.")
    saturation: float
    lightness: float
    warmth: float = Field(description="Mean (R - B), -1..1: positive = warm light.")
    greenness: float = Field(description="Share of vegetation-green pixels (seasonal cue).")
    snow: float = Field(description="Share of bright, unsaturated pixels in the lower half (snow cue).")
    viewpoint: str | None = Field(default=None, description="Most likely camera angle (visual.VIEWPOINTS).")
    viewpoint_scores: dict[str, float] = Field(default_factory=dict)
    damage: float | None = Field(default=None, description="0 intact .. 1 destroyed, among frames that show buildings.")
    damage_scores: dict[str, float] = Field(default_factory=dict)
    provenance: Provenance | None = None


class OcrLine(Frozen):
    text: str
    confidence: float
    box: tuple[float, float, float, float] = Field(description="x, y, width, height; normalised, origin top-left.")


class OcrResult(Frozen):
    """On-screen text read from the frame (derived from pixels)."""

    lines: list[OcrLine] = Field(default_factory=list)
    provenance: Provenance


class DerivedVisual(Mutable):
    categories: list[CategoryLabel] = Field(default_factory=list, description="Labels above threshold.")
    category_scores: dict[str, float] = Field(default_factory=dict, description="Raw per-label scores, for re-thresholding.")
    classifier: Provenance | None = None
    quality: FrameQuality
    features: VisualFeatures | None = None
    ocr: OcrResult | None = None


class VideoDerived(Mutable):
    text_categories: list[CategoryLabel] = Field(
        default_factory=list,
        description="Labels matched in title/tags/description. Video-level text signal, not visual.",
    )


# --------------------------------------------------------------------------
# 3. Inferred metadata
# --------------------------------------------------------------------------


class InferredLocation(Frozen):
    """A candidate capture location. Coordinates are null unless a source supplied them."""

    latitude: float | None = None
    longitude: float | None = None
    place_name: str | None = None
    uncertainty_m: float | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    provenance: Provenance


class InferredCaptureDate(Frozen):
    """Capture-date estimate, expressed as a bound and/or point value."""

    value: date | None = None
    earliest: date | None = None
    latest: date | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    provenance: Provenance


class Inferred(Mutable):
    locations: list[InferredLocation] = Field(default_factory=list, description="Ranked candidates, best first.")
    capture_date: list[InferredCaptureDate] = Field(default_factory=list)


class ScopeSignal(Frozen):
    kind: Literal["geotag", "gazetteer", "language"]
    field: str
    match: str
    weight: float = Field(description="Contribution to relevance; negative = evidence against (e.g. geotag outside Ukraine).")


class ScopeCheck(Frozen):
    """Inferred: is this video about Ukraine? Gate for the collection scope (see scope.py)."""

    in_scope: bool
    confidence: float = Field(ge=0.0, le=1.0)
    signals: list[ScopeSignal] = Field(default_factory=list)
    rules_version: str
    checked_at: datetime = Field(default_factory=utcnow)


# --------------------------------------------------------------------------
# Records
# --------------------------------------------------------------------------


class FrameSourceLink(Frozen):
    """Immutable link from a frame back to its source video."""

    video_id: str
    youtube_id: str
    source_url: str
    timestamped_url: str
    published_at: datetime


class FrameFiles(Frozen):
    original: str
    web: str
    thumb: str


class FrameCore(Frozen):
    timestamp_s: float = Field(description="Presentation time from video start, seconds.")
    frame_number: int = Field(description="0-based frame index = round(timestamp_s * fps).")
    fps: float
    width: int
    height: int
    selection: Literal["scene_change", "interval"]
    scene_score: float | None = None
    original_format: Literal["png", "jpg"]
    sha256: str = Field(description="SHA-256 of the original-quality file.")
    files: FrameFiles


class PipelineInfo(Frozen):
    version: str
    config_digest: str
    created_at: datetime = Field(default_factory=utcnow)


class FrameRecord(Mutable):
    schema_version: str = SCHEMA_VERSION
    frame_id: str
    source: FrameSourceLink
    frame: FrameCore
    derived: DerivedVisual
    inferred: Inferred
    pipeline: PipelineInfo


class VideoRecord(Mutable):
    schema_version: str = SCHEMA_VERSION
    video_id: str
    source: SourceVideo
    discovery: list[DiscoveryContext] = Field(default_factory=list)
    acquisition: Acquisition | None = None
    derived: VideoDerived = Field(default_factory=VideoDerived)
    scope: ScopeCheck | None = Field(default=None, description="Inferred Ukraine-relevance check (collection gate).")
    youtube_thumbnails: dict[str, str] = Field(default_factory=dict, description="size -> local path (library-relative)")
    frame_ids: list[str] = Field(default_factory=list)
    status: Literal["discovered", "processed", "failed"] = "discovered"
    errors: list[str] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=utcnow)


def video_id_for(youtube_id: str) -> str:
    return f"yt_{youtube_id}"


def frame_id_for(youtube_id: str, frame_number: int) -> str:
    return f"yt_{youtube_id}_f{frame_number:07d}"


def timestamped_url(youtube_id: str, timestamp_s: float) -> str:
    return f"https://www.youtube.com/watch?v={youtube_id}&t={int(timestamp_s)}s"
