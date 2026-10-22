"""Records for satellite passes and the chips cut from them, in the same three tiers as `schema.py`.

The chip -> pass link (`SatelliteChip.source`, `.chip`) is frozen, like a frame's link to its video.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import Field

from ..schema import SCHEMA_VERSION, FrameFiles, Frozen, Mutable, Provenance, utcnow


class PassSource(Frozen):
    """What the provider says about the pass. Acquisition time is the capture time (a source fact)."""

    provider: str = Field(description="e.g. 'Microsoft Planetary Computer'")
    collection: str = Field(description="STAC collection, e.g. 'sentinel-2-l2a'")
    item_ids: tuple[str, ...] = Field(description="The STAC items stitched into this pass (tiles of one overpass).")
    item_urls: tuple[str, ...] = ()
    platform: str
    sensor: Literal["sentinel-2", "landsat"]
    acquired_at: datetime = Field(description="Acquisition time (UTC), from the items.")
    cloud_cover: float | None = Field(default=None, description="The items' own eo:cloud_cover (% of each tile).")
    sun_elevation: float | None = None
    gsd_m: float
    processing: str | None = Field(default=None, description="Processing baseline / collection version.")
    licence: str
    attribution: str
    retrieved_at: datetime = Field(default_factory=utcnow)


class Alignment(Frozen):
    """Shift that lays the pass on the corridor's reference pass (phase correlation on land)."""

    reference_pass: str | None
    dx_m: float = 0.0
    dy_m: float = Field(default=0.0, description="Positive: the image content moved north to match.")
    response: float | None = Field(default=None, description="Phase-correlation peak (0..1); low = unreliable.")
    applied: bool = False
    provenance: Provenance


class PassDerived(Mutable):
    alignment: Alignment
    coverage: str = Field(default="the whole corridor", description="What part of the line the pass was fetched for.")
    until_m: float | None = Field(default=None, description="Fetched only along the line's first this many metres.")
    valid_share: float = Field(description="Share of the fetched area the pass covers with data.")
    cloud_share: float | None = Field(default=None, description="Share of covered pixels flagged cloud or shadow.")
    water_share: float = Field(description="Share of clear pixels that are open water (NIR and SWIR reflectance < 3%).")
    display: str = Field(description="How true colour was stretched for display (same for every pass).")
    provenance: Provenance


class TileFile(Frozen):
    """One tile of a pass on the corridor's grid (a long corridor is fetched as tiles along a strip round its line)."""

    rows: tuple[int, int]
    cols: tuple[int, int]
    visual: str = Field(description="True colour (display stretch in the pass's derived.display).")
    bands: str = Field(description="NIR and SWIR reflectance x 10000, valid and cloud masks (npz).")
    dx_m: float = 0.0
    dy_m: float = 0.0
    response: float | None = None
    applied: bool = False


class PassFiles(Frozen):
    visual: str | None = Field(default=None, description="The whole grid in one image (a small corridor's first passes).")
    bands: str | None = None
    tiles: tuple[TileFile, ...] = ()
    stac_items: str
    requests: str


class SatellitePass(Mutable):
    schema_version: str = SCHEMA_VERSION
    pass_id: str
    corridor_id: str
    source: PassSource
    derived: PassDerived
    files: PassFiles
    chip_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)


class ChipLink(Frozen):
    """Immutable link from a chip to its pass and its place on the corridor."""

    pass_id: str
    corridor_id: str
    item_ids: tuple[str, ...]
    acquired_at: datetime
    station: int = Field(description="0 = the whole corridor; 1.. = along the line.")
    along_m: float = Field(description="Distance along the corridor's line to the chip's centre.")


class ChipCore(Frozen):
    kind: Literal["overview", "station"]
    centre_lat: float = Field(description="From the products' own georeference (a source with coordinates).")
    centre_lon: float
    bbox: tuple[float, float, float, float] = Field(description="lon_min, lat_min, lon_max, lat_max")
    size_m: tuple[float, float] = Field(description="width, height on the ground")
    m_per_px: float
    width: int
    height: int
    sha256: str = Field(description="SHA-256 of the chip's RGB pixels as cut from the mosaic.")
    sha256_of: Literal["pixels"] = "pixels"
    files: FrameFiles


class ChipDerived(Mutable):
    valid_share: float
    cloud_share: float | None = None
    water_share: float
    exposed_bed_share: float | None = Field(
        default=None, description="Share of clear pixels that were open water in `exposed_against` and are not now.")
    exposed_against: str | None = Field(default=None, description="The earlier pass compared with.")
    provenance: Provenance


class SatelliteChip(Mutable):
    schema_version: str = SCHEMA_VERSION
    chip_id: str
    source: ChipLink
    chip: ChipCore
    derived: ChipDerived
    created_at: datetime = Field(default_factory=utcnow)


def pass_id_for(platform: str, acquired: datetime) -> str:
    """'s2a_20230923T0836' (Sentinel-2A), 'l8_20200714T0842' (Landsat 8)."""
    p = platform.lower()
    tag = ("s" + p.removeprefix("sentinel-") if p.startswith("sentinel-") else
           "l" + p.removeprefix("landsat-") if p.startswith("landsat-") else re.sub(r"[^a-z0-9]", "", p))
    return f"{tag}_{acquired:%Y%m%dT%H%M}"


def chip_id_for(corridor_id: str, pass_id: str, station: int) -> str:
    return f"sat_{corridor_id}_{pass_id}_c{station:03d}"
