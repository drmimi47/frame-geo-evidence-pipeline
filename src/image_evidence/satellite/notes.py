"""Timed notes for a film: short lines of context shown under it in The Conductive Seam view (what the plant is, how many
lines it had, what happened when), each with its sources.

They are text beside the film, never drawn into it, and never evidence about the imagery: a note says what its sources
say, not what the pixels show. The area's config places each note by the film's shots (`{shot: open, s: 6.5}`: seconds
into the first shot of that kind, negative from its end; `n: 2` for the second, `n: -1` the last) or by distance along the line
(`{km: 3.0}`: when the camera first reaches it in a track). A note runs until its `to`, else until the next note's
`from`. Placing is redone without rendering (`evidence satellite notes`), so the words can be changed on their own.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import numpy as np

from ..layout import write_json
from .store import corridor_dir

log = logging.getLogger(__name__)

READ_CPS = 22.0  # characters a second a note needs to be read: shorter than that is logged
STATEMENT = ("Notes under the film are context from the sources named with each, placed by the film's shots or by "
             "distance along the line: not read from the imagery.")


def _when(film: dict[str, Any], a: dict[str, Any]) -> float:
    segs = film["segments"]
    if "km" in a:
        m = float(a["km"]) * 1000
        fi = {k: i for i, k in enumerate(film["camera"]["fields"])}
        tracks = [(s["t0"], s["t1"]) for s in segs if s["shot"] == "track"]
        pts = np.array([[x[fi["t"]], x[fi["along_m"]]] for x in film["camera"]["samples"]
                        if any(t0 <= x[fi["t"]] <= t1 for t0, t1 in tracks)])
        k = int(np.argmax(pts[:, 1] >= m)) if len(pts) and pts[-1, 1] >= m else -1
        if k < 0:
            raise ValueError(f"a note's km {a['km']} is beyond the film's line")
        if k == 0:
            return float(pts[0, 0])
        (ta, ma), (tb, mb) = pts[k - 1], pts[k]
        return float(ta + (tb - ta) * (m - ma) / max(1e-9, mb - ma))
    shots = [s for s in segs if s["shot"] == a["shot"]]
    n = int(a.get("n", 1))  # 1 the first, -1 the last
    if not (0 < n <= len(shots) or 0 < -n <= len(shots)):
        raise ValueError(f"a note names shot {a['shot']!r} #{n}, but the film has {len(shots)}")
    s, x = shots[n - 1 if n > 0 else n], float(a.get("s", 0))
    return min(s["t1"], max(s["t0"], (s["t1"] if x < 0 else s["t0"]) + x))


def place(film: dict[str, Any], notes: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """The notes with their times in this film, in order, none overlapping the next."""
    out = []
    for i, n in enumerate(notes or []):
        t0 = _when(film, n["from"])
        t1 = _when(film, n["to"]) if n.get("to") else (_when(film, notes[i + 1]["from"]) if i + 1 < len(notes)
                                                         else film["duration_s"])
        if t1 <= t0:
            raise ValueError(f"note {i + 1} ends before it starts ({t0:.1f} → {t1:.1f} s): {n['text'][:40]}…")
        out.append({"t0": round(t0, 2), "t1": round(t1, 2), "text": " ".join(n["text"].split()),
                    "sources": [{"title": s["title"], "url": s["url"]} for s in n.get("sources") or []]})
    out.sort(key=lambda x: x["t0"])
    for a, b in zip(out, out[1:]):
        a["t1"] = min(a["t1"], b["t0"])
    for x in out:
        if x["t1"] - x["t0"] < len(x["text"]) / READ_CPS:
            log.warning("Note at %.1f s shows %.1f s for %d characters: %s…", x["t0"], x["t1"] - x["t0"], len(x["text"]), x["text"][:40])
    return out


def write(root, corridor_id: str, film_id: str, notes: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Place the notes on a film already made, in its film.json (nothing else of the film changes)."""
    p = corridor_dir(root, corridor_id) / "films" / film_id / "film.json"
    film = json.loads(p.read_text())
    film["notes"] = place(film, notes)
    film["notes_statement"] = STATEMENT
    write_json(p, film)
    return film["notes"]
