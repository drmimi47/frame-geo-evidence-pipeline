"""Where a library keeps its satellite data, and a small in-memory index over it for the site.

The JSON sidecars are canonical (as for videos); there is no database table yet: a folder holds a few passes of
tens of chips, so the index reads them all and reloads when a pass.json or a film's frames.json changes. Each
corridor's newest film with frames (`film_frames.py`) is a group of the gallery too, ahead of the passes.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .schema import SatelliteChip, SatellitePass


def satellite_dir(root: Path) -> Path:
    return Path(root) / "satellite"


def corridor_dir(root: Path, corridor_id: str) -> Path:
    return satellite_dir(root) / "corridors" / corridor_id


def corridor_ids(root: Path) -> list[str]:
    d = satellite_dir(root) / "corridors"
    return sorted(p.name for p in d.iterdir() if (p / "georef.json").is_file()) if d.is_dir() else []


def read_georef(root: Path, corridor_id: str) -> dict[str, Any] | None:
    p = corridor_dir(root, corridor_id) / "georef.json"
    return json.loads(p.read_text()) if p.is_file() else None


def read_passes(root: Path, corridor_id: str) -> list[SatellitePass]:
    d = corridor_dir(root, corridor_id) / "passes"
    out = [SatellitePass.model_validate_json(p.read_text()) for p in d.glob("*/pass.json")] if d.is_dir() else []
    return sorted(out, key=lambda p: p.source.acquired_at)


def read_chips(root: Path, corridor_id: str, pass_id: str) -> list[SatelliteChip]:
    d = corridor_dir(root, corridor_id) / "passes" / pass_id / "chips" / "meta"
    out = [SatelliteChip.model_validate_json(p.read_text()) for p in d.glob("*.json")] if d.is_dir() else []
    return sorted(out, key=lambda c: c.source.station)


def films(root: Path) -> list[dict[str, Any]]:
    """Every rendered film in the library, newest first."""
    out = []
    for cid in corridor_ids(root):
        for p in (corridor_dir(root, cid) / "films").glob("*/film.json"):
            out.append(json.loads(p.read_text()))
    return sorted(out, key=lambda f: f["created_at"], reverse=True)


def pass_title(p: SatellitePass) -> str:
    t = p.source.acquired_at
    return f"{p.source.platform} · {t.day} {t:%B %Y}"


@dataclass
class SatelliteIndex:
    """The library's chips as the grid shows them: one group per pass, oldest pass first, stations in order."""

    root: Path
    _stamp: tuple = field(default=(), repr=False)
    _passes: dict[str, tuple[SatellitePass, dict[str, Any]]] = field(default_factory=dict, repr=False)  # group id ->
    _chips: dict[str, tuple[SatelliteChip, str]] = field(default_factory=dict, repr=False)  # chip id -> (chip, group id)
    _films: dict[str, tuple[dict[str, Any], list[dict[str, Any]]]] = field(default_factory=dict, repr=False)  # group id -> (film, frames)
    _film_frames: dict[str, tuple[dict[str, Any], str]] = field(default_factory=dict, repr=False)  # frame id -> (frame, group id)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def _refresh(self) -> None:
        files = sorted(satellite_dir(self.root).glob("corridors/*/passes/*/pass.json")) + sorted(
            satellite_dir(self.root).glob("corridors/*/films/*/frames/frames.json")) + sorted(
            satellite_dir(self.root).glob("corridors/*/films/*/film.json"))  # (notes placed again change only film.json)
        stamp = tuple((str(p), p.stat().st_mtime_ns) for p in files)
        with self._lock:
            if stamp == self._stamp:
                return
            passes, chips, films, frames = {}, {}, {}, {}
            for cid in corridor_ids(self.root):
                made = sorted((corridor_dir(self.root, cid) / "films").glob("*/frames/frames.json"))
                if made:  # the newest film's frames (film ids sort by when they were made)
                    film = json.loads((made[-1].parent.parent / "film.json").read_text()) if (made[-1].parent.parent / "film.json").is_file() else None
                    if film is not None:
                        gid = f"sat_film_{cid}_{film['film_id']}"
                        fr = json.loads(made[-1].read_text())["frames"]
                        films[gid] = (film, fr)
                        frames.update({f["frame_id"]: (f, gid) for f in fr})
                georef = read_georef(self.root, cid)
                for p in read_passes(self.root, cid):
                    gid = f"sat_{cid}_{p.pass_id}"
                    passes[gid] = (p, georef)
                    for c in read_chips(self.root, cid, p.pass_id):
                        chips[c.chip_id] = (c, gid)
            self._passes, self._chips, self._films, self._film_frames, self._stamp = passes, chips, films, frames, stamp

    def __len__(self) -> int:
        self._refresh()
        return len(self._chips) + len(self._film_frames)

    def films(self) -> list[tuple[str, dict[str, Any], list[dict[str, Any]]]]:
        """Each corridor's newest film with frames: (group id, film.json, frames)."""
        self._refresh()
        return [(gid, f, fr) for gid, (f, fr) in sorted(self._films.items())]

    def film_frame(self, frame_id: str) -> tuple[dict[str, Any], dict[str, Any]] | None:
        self._refresh()
        if frame_id not in self._film_frames:
            return None
        fr, gid = self._film_frames[frame_id]
        return fr, self._films[gid][0]

    def groups(self) -> list[tuple[str, SatellitePass, dict[str, Any], list[SatelliteChip]]]:
        self._refresh()
        out = []
        for gid, (p, georef) in sorted(self._passes.items(), key=lambda kv: (kv[1][1]["corridor_id"], kv[1][0].source.acquired_at)):
            chips = sorted((c for c, g in self._chips.values() if g == gid), key=lambda c: c.source.station)
            out.append((gid, p, georef, chips))
        return out

    def chip(self, chip_id: str) -> tuple[SatelliteChip, SatellitePass, dict[str, Any]] | None:
        self._refresh()
        if chip_id not in self._chips:
            return None
        c, gid = self._chips[chip_id]
        p, georef = self._passes[gid]
        return c, p, georef
