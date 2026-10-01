"""Pipeline configuration (YAML -> pydantic)."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class _Cfg(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LocationSpec(_Cfg):
    name: str
    # Only used for the YouTube API `location` geo-filter. These coordinates are
    # never copied onto frames: a city centre is not where a frame was captured.
    latitude: float | None = None
    longitude: float | None = None
    radius_km: float = 25.0
    geo_filter: bool = Field(
        default=False,
        description="Restrict search to videos geotagged within radius_km (requires lat/lon). Few videos are geotagged.",
    )

    @model_validator(mode="after")
    def _check_geo(self) -> "LocationSpec":
        if self.geo_filter and (self.latitude is None or self.longitude is None):
            raise ValueError(f"location {self.name!r}: geo_filter requires latitude and longitude")
        return self


class CategorySpec(_Cfg):
    name: str
    terms: list[str] = Field(description="Search phrases substituted for {term} in the query template.")


class FocusSpec(_Cfg):
    """A study area: candidates are ranked by how well they can be placed in it (see focus.py)."""

    places: list[str] = Field(description="Gazetteer names of the area's places; the area is everything within radius_km of one.")
    radius_km: float = Field(default=15.0, gt=0)
    geotagged_terms: list[str] = Field(
        default_factory=list,
        description="Also search for videos geotagged inside the area, one search per term ('' = any video: mostly unrelated clips).",
    )
    topic_terms: list[str] = Field(
        default_factory=list, description="Word starts that mark the subject studied (e.g. war damage); a small bonus each.",
    )
    min_score: float = Field(default=2.0, description="Candidates scoring below this are listed but never ingested.")


class DiscoveryConfig(_Cfg):
    api_key_env: str = "YOUTUBE_API_KEY"
    published_after: date = date(2022, 1, 1)
    published_before: date = date(2026, 12, 31)
    split_by_year: bool = Field(default=True, description="Run each query once per calendar year to spread results across 2022-2026.")
    query_template: str = "{location} {term}"
    locations: list[LocationSpec] = Field(default_factory=list)
    categories: list[CategorySpec] = Field(default_factory=list)
    extra_queries: list[str] = Field(default_factory=list, description="Literal queries run as-is (per year window).")
    max_results_per_query: int = Field(default=5, ge=1, le=50)
    max_videos_total: int = Field(default=10, ge=1)
    focus: FocusSpec | None = None
    max_ingest: int | None = Field(
        default=None, ge=1, description="Ingest only the best-ranked N new candidates (all of them when unset).",
    )
    order: Literal["relevance", "date", "viewCount", "rating"] = "relevance"
    video_license: Literal["any", "creativeCommon"] = "creativeCommon"
    video_duration: Literal["any", "short", "medium", "long"] = "any"
    region_code: str | None = None
    relevance_language: str | None = None
    safe_search: Literal["none", "moderate", "strict"] = "moderate"

    @model_validator(mode="after")
    def _hard_date_range(self) -> "DiscoveryConfig":
        from .scope import HARD_END, HARD_START

        if self.published_after < HARD_START or self.published_before > HARD_END:
            raise ValueError(
                f"published_after/published_before must stay within the collection's hard range {HARD_START}..{HARD_END}"
            )
        if self.published_after > self.published_before:
            raise ValueError("published_after is later than published_before")
        return self


class ScopeConfig(_Cfg):
    min_confidence: float = Field(
        default=0.5, ge=0.3, le=1.0,
        description="Minimum Ukraine-relevance (noisy-OR of signals) to accept a video. Language alone (0.4) is not enough.",
    )


class AcquisitionConfig(_Cfg):
    policy: Literal["none", "creative_commons", "public"] = Field(
        default="creative_commons",
        description=(
            "none: metadata + thumbnails only. creative_commons: download only CC-BY licensed videos. "
            "public: any public, non-DRM, non-age-gated video (you are responsible for platform terms)."
        ),
    )
    max_height: int = 1080
    max_duration_s: int = 3600  # long-form Ukrainian reportage often runs 30-60 min
    include_audio: bool = True
    keep_media: bool = True


class ExtractionConfig(_Cfg):
    interval_s: float = Field(default=10.0, gt=0, description="Guarantee at least one frame every N seconds.")
    scene_threshold: float = Field(default=0.3, gt=0, lt=1, description="FFmpeg scene score threshold (0-1).")
    min_gap_s: float = Field(default=1.5, ge=0, description="Minimum spacing between selected frames.")
    max_frames_per_video: int = Field(default=100, ge=1)
    candidate_pool: int = Field(
        default=500, ge=1,
        description="Candidates previewed and classified per video; the best max_frames_per_video are kept (see classification.prefer).",
    )
    dedup_hamming: int = Field(default=6, ge=0, le=64, description="Drop frames whose dHash is within this distance of a kept frame.")
    drop_dark_below: float = Field(default=10.0, description="Drop near-black frames (mean luma).")
    drop_black_fraction: float = Field(
        default=0.7, gt=0, le=1,
        description="Drop frames where this fraction of pixels is near-black (credits, title cards, small inset clips).",
    )
    original_format: Literal["png", "jpg", "auto"] = Field(
        default="auto", description="auto: PNG (lossless) unless a video yields more than lossless_max_frames, then JPEG."
    )
    lossless_max_frames: int = 40
    jpeg_quality: int = Field(default=95, ge=50, le=100)
    web_max_px: int = 1600
    web_quality: int = 82
    thumb_max_px: int = 400
    thumb_quality: int = 75


# Label -> caption phrases (inserted into ClassificationConfig.prompt_template).
# SigLIP rewards concrete captions over bare nouns ("a person" scores ~0 on a portrait).
DEFAULT_LABELS: dict[str, list[str]] = {
    "architecture": ["historic architecture", "a notable building", "the facade of a building"],
    "landscape": ["a natural landscape", "fields and grassland", "a river or lake shore", "a dry riverbed", "wild vegetation", "countryside",
                  "a forest", "trees and nature", "scenic countryside"],
    "street": ["a street at ground level", "a road lined with buildings"],
    "urban": ["a city", "an urban area with many buildings"],
    "aerial": ["an aerial view from high above the ground", "a bird's-eye view of the ground below"],
    "drone": ["a drone shot looking down from high in the sky", "an aerial drone view over rooftops or fields"],
    "infrastructure": ["a bridge", "a highway", "railway tracks", "power lines", "a dam"],
    "industrial": ["a factory", "an industrial site", "a power plant"],
    "ruins": ["ruins", "a destroyed building", "rubble of collapsed buildings"],
    "reconstruction": ["a construction site", "a building under reconstruction", "scaffolding and cranes"],
    "wildlife": ["birds", "wild animals", "an animal", "farm animals"],
    # Unwanted subjects (see ClassificationConfig.avoid): frames dominated by these are not kept.
    "people": ["a person wearing a helmet and body armor", "a person being interviewed", "a man talking", "a woman talking", "a group of people",
               "a close-up portrait of a person", "a person's face", "a person speaking to the camera",
               "hands holding a phone or a remote controller"],
    "interior": ["an indoor room", "the interior of a building", "a room with furniture", "an office", "a television studio", "the inside of a car"],
    "graphic": ["a logo on a colored background", "a title card", "text on a plain background", "a map", "an infographic",
                "white text on a black screen", "end credits with a small picture on a black screen", "a book cover",
                "printed brochures on a table"],
}
# Sink label: absorbs frames that match no category. Never emitted as a category.
OTHER_LABEL = "_other"
OTHER_PROMPTS = ["a video frame", "a blurry photo", "a close-up of an object"]


class ClassificationConfig(_Cfg):
    backend: Literal["auto", "siglip", "none"] = Field(
        default="auto", description="auto: SigLIP if the [classify] extra is installed, else none."
    )
    model: str = Field(
        default="google/siglip-so400m-patch14-384",
        description="SigLIP checkpoint. so400m (~3.5GB) separates labels far better than the base models.",
    )
    prompt_template: str = "This is a photo of {}."
    temperature: float = Field(default=1.0, gt=0, description="Softmax temperature over label logits.")
    threshold: float = Field(
        default=0.15, ge=0, le=1,
        description="Keep labels whose softmax share (across all labels + an 'other' sink) is at least this. Relative, not calibrated.",
    )
    batch_size: int = 16
    # Frame choice. The collection is about places (landscape, architecture, nature, animals, infrastructure):
    # a candidate is kept only if its share of `prefer` labels minus its share of `avoid` labels is at least
    # min_subject. Wide shots with a few people pass; faces, interviews, car and room interiors do not.
    prefer: list[str] = Field(default_factory=lambda: [
        "landscape", "architecture", "street", "urban", "aerial", "drone", "infrastructure", "industrial",
        "ruins", "reconstruction", "wildlife",
    ])
    avoid: list[str] = Field(default_factory=lambda: ["people", "interior", "graphic"])
    min_subject: float = Field(default=0.4, ge=-1, le=1, description="Minimum prefer-minus-avoid share for a frame to be kept.")
    labels: dict[str, list[str]] = Field(default_factory=lambda: dict(DEFAULT_LABELS))


class Config(_Cfg):
    library_dir: Path = Path("library")
    discovery: DiscoveryConfig = Field(default_factory=DiscoveryConfig)
    scope: ScopeConfig = Field(default_factory=ScopeConfig)
    acquisition: AcquisitionConfig = Field(default_factory=AcquisitionConfig)
    extraction: ExtractionConfig = Field(default_factory=ExtractionConfig)
    classification: ClassificationConfig = Field(default_factory=ClassificationConfig)

    @classmethod
    def load(cls, path: Path | None) -> "Config":
        data = yaml.safe_load(Path(path).read_text()) if path else None
        cfg = cls.model_validate(data or {})
        cfg.library_dir = cfg.library_dir.resolve()  # relative paths resolve against the CWD
        return cfg

    def digest(self) -> str:
        """Stable short hash of settings that affect frame output."""
        payload = self.model_dump(mode="json", include={"extraction", "classification"})
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:12]
