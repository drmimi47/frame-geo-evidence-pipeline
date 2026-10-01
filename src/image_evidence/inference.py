"""Inferred metadata: where and when footage was plausibly captured.

Rules:
- Coordinates are only ever copied from a source that supplied them (the
  uploader's YouTube recordingDetails). They are never geocoded from a place
  name and never taken from the search configuration.
- Every value carries a confidence and provenance. Confidences are coarse,
  hand-set priors per method, not calibrated probabilities.
- Publication date is a hard upper bound on capture date; it is not a capture date.
  Videos published 2022-2026 can contain older (archival) footage, so text hints
  of pre-2022 material are surfaced as low-confidence capture-date candidates.
"""

from __future__ import annotations

import re
from datetime import date

from .places import find_places, km
from .schema import (
    DiscoveryContext,
    Inferred,
    InferredCaptureDate,
    InferredLocation,
    Provenance,
    ScopeCheck,
    SourceVideo,
)

CONF_UPLOADER_GEOTAG = 0.6
CONF_GEOTAG_FAR = 0.3          # geotag far from every place the video names (often the newsroom's city)
GEOTAG_FAR_KM = 60
CONF_UPLOADER_LOCATION_TEXT = 0.45
CONF_GEO_FILTERED_SEARCH = 0.4
CONF_QUERY_CONTEXT = 0.2
CONF_UPLOADER_RECORDING_DATE = 0.6
CONF_TEXT_PLACE_TITLE = 0.3
CONF_TEXT_PLACE_OTHER = 0.15
CONF_YEAR_MENTION = 0.2
CONF_ARCHIVAL_KEYWORD = 0.2

_YEAR = re.compile(r"(?<!\d)(19[5-9]\d|20[01]\d|202[01])(?!\d)")
_ARCHIVAL = re.compile(
    r"\b(archive|archival|archived|footage from|years ago|before the war|pre-war|"
    r"архів\w*|архив\w*|до війни|до вторгнення|до войны|довоєнн\w*|довоенн\w*)",
    re.IGNORECASE,
)


def infer_locations(source: SourceVideo, discovery: list[DiscoveryContext], scope: ScopeCheck | None = None) -> list[InferredLocation]:
    out: list[InferredLocation] = []
    claimed = source.claimed_recording_location
    if claimed and claimed.latitude is not None and claimed.longitude is not None:
        conf, note = _geotag_check(source, claimed.latitude, claimed.longitude)
        out.append(InferredLocation(
            latitude=claimed.latitude,
            longitude=claimed.longitude,
            place_name=claimed.description,
            confidence=conf,
            provenance=Provenance(
                method="youtube_recording_details_geotag",
                evidence="Uploader-set recordingDetails.location for the whole video; not verified per frame." + note,
            ),
        ))
    elif claimed and claimed.description:
        out.append(InferredLocation(
            place_name=claimed.description,
            confidence=CONF_UPLOADER_LOCATION_TEXT,
            provenance=Provenance(method="youtube_recording_details_text", evidence="Uploader-set locationDescription; no coordinates."),
        ))

    seen: set[str] = set()
    for ctx in discovery:
        if not ctx.location or ctx.location in seen:
            continue
        seen.add(ctx.location)
        conf = CONF_GEO_FILTERED_SEARCH if ctx.geo_filtered else CONF_QUERY_CONTEXT
        how = "geo-filtered YouTube search" if ctx.geo_filtered else "text search"
        out.append(InferredLocation(
            place_name=ctx.location,
            confidence=conf,
            provenance=Provenance(
                method="discovery_query_context",
                evidence=f"Video returned by {how} {ctx.query!r}. Relevance to the place is unverified; coordinates intentionally null.",
            ),
        ))

    # Places named in the video's own metadata. A mention is not a capture location: names only.
    for field, text, conf in (
        ("title", source.title, CONF_TEXT_PLACE_TITLE),
        ("tags", " | ".join(source.tags), CONF_TEXT_PLACE_OTHER),
        ("description", source.description, CONF_TEXT_PLACE_OTHER),
    ):
        for m in find_places(text):
            canonical, matched = m.name, m.matched
            if canonical == "Ukraine" or canonical in seen:
                continue
            seen.add(canonical)
            out.append(InferredLocation(
                place_name=canonical,
                confidence=conf,
                provenance=Provenance(
                    method="source_text_gazetteer",
                    evidence=f"{matched!r} named in video {field}. The video mentions this place; frames may show elsewhere.",
                ),
            ))

    if scope and scope.in_scope:
        out.append(InferredLocation(
            place_name="Ukraine",
            confidence=scope.confidence,
            provenance=Provenance(method="scope_check", evidence="Country-level: video judged Ukraine-relevant by the collection scope check."),
        ))
    return sorted(out, key=lambda loc: -loc.confidence)


def _geotag_check(source: SourceVideo, lat: float, lon: float) -> tuple[float, str]:
    """Lower the geotag's weight when it is far from every settlement the video names.

    Channels often tag every upload with their newsroom's city. Gazetteer coordinates are used only
    for this distance check; they are never attached to a frame.
    """
    named = [p for m in find_places(f"{source.title}\n{source.description}") for p in m.places
             if p.lat is not None and not m.name.endswith("Oblast")]
    if not named:
        return CONF_UPLOADER_GEOTAG, ""
    nearest = min(named, key=lambda p: km(lat, lon, p.lat, p.lon))
    d = km(lat, lon, nearest.lat, nearest.lon)
    if d <= GEOTAG_FAR_KM:
        return CONF_UPLOADER_GEOTAG, ""
    return CONF_GEOTAG_FAR, (f" The geotag is {round(d)} km from the nearest place the video names ({nearest.name}),"
                             " so it may be the uploader's base rather than where this was filmed.")


def infer_capture_dates(source: SourceVideo) -> list[InferredCaptureDate]:
    out = [
        InferredCaptureDate(
            latest=source.published_at.date(),
            confidence=1.0,
            provenance=Provenance(
                method="publication_upper_bound",
                evidence="Footage cannot have been captured after it was published. Earliest bound unknown (re-uploads are common).",
            ),
        )
    ]
    if source.claimed_recording_date:
        out.append(InferredCaptureDate(
            value=source.claimed_recording_date.date(),
            latest=source.published_at.date(),
            confidence=CONF_UPLOADER_RECORDING_DATE,
            provenance=Provenance(method="youtube_recording_details_date", evidence="Uploader-set recordingDetails.recordingDate."),
        ))

    # Hints that published-in-range video contains pre-2022 footage.
    text = f"{source.title}\n{source.description}"
    for year in sorted({int(y) for y in _YEAR.findall(text)}):
        out.append(InferredCaptureDate(
            earliest=date(year, 1, 1),
            latest=date(year, 12, 31),
            confidence=CONF_YEAR_MENTION,
            provenance=Provenance(
                method="source_text_year_mention",
                evidence=f"'{year}' appears in title/description; some footage may date from then (possibly archival).",
            ),
        ))
    if m := _ARCHIVAL.search(text):
        out.append(InferredCaptureDate(
            latest=date(2021, 12, 31),
            confidence=CONF_ARCHIVAL_KEYWORD,
            provenance=Provenance(
                method="source_text_archival_keyword",
                evidence=f"{m.group(0)!r} in title/description suggests some footage predates 2022.",
            ),
        ))
    return out


def infer(source: SourceVideo, discovery: list[DiscoveryContext], scope: ScopeCheck | None = None) -> Inferred:
    return Inferred(locations=infer_locations(source, discovery, scope), capture_date=infer_capture_dates(source))
