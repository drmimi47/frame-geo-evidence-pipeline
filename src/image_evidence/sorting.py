"""Orderings of the frame grid for spatial / forensic-architecture style review.

Each sort returns the frames in order with a ``group`` (consecutive frames with the same group are
laid out together) and a short ``note`` explaining the frame's position. Everything is derived from
pixels or from existing inferred metadata; nothing here is a new claim about the world.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from .schema import FrameRecord
from .visual import VIEW_NAMES, VIEW_ORDER

Sorted = list[tuple[FrameRecord, str, str]]  # (frame, group, note)

# SigLIP image-image cosine similarity. Nearest neighbours in this library sit around 0.9-0.96.
BREAK_SIM = 0.86   # the chain starts a new block below this
MATCH_SIM = 0.92   # 'closely matches' another video's frame (same site or re-used footage)

LABELS = {
    "video": "Video & time",
    "place": "Place",
    "similar": "Similar view",
    "angle": "Camera angle",
    "damage": "Damage",
    "scale": "Scale",
    "color": "Colour",
    "light": "Light",
    "season": "Season cues",
    "published": "Published",
    "detail": "Detail",
}


def _time(f: FrameRecord):
    return (f.source.published_at, f.source.video_id, f.frame.timestamp_s)


def by_place(frames: list[FrameRecord], _emb) -> Sorted:
    def best(f):
        locs = [loc for loc in f.inferred.locations if loc.place_name and loc.place_name != "Ukraine"]
        return max(locs, key=lambda loc: loc.confidence) if locs else None
    rows = []
    for f in frames:
        loc = best(f)
        name = loc.place_name if loc else "Unknown place"
        note = (f"Place: {name}, {round(loc.confidence * 100)}% ({loc.provenance.method.replace('_', ' ')}). "
                "Inferred from metadata, not a verified filming location") if loc else "No place inferred beyond Ukraine"
        rows.append((f, name, note))
    rows.sort(key=lambda r: (r[1] == "Unknown place", not r[1][:1].isascii(), r[1].lower(), _time(r[0])))
    return rows


def by_similarity(frames: list[FrameRecord], emb: dict[str, np.ndarray]) -> Sorted:
    """Greedy nearest-neighbour chain over SigLIP embeddings: the same site filmed in different
    videos ends up side by side. A new group starts where the chain jumps to a dissimilar view."""
    have = [f for f in frames if f.frame_id in emb]
    rest = [f for f in frames if f.frame_id not in emb]
    rows: Sorted = []
    if have:
        E = np.stack([emb[f.frame_id] for f in have])
        E /= np.linalg.norm(E, axis=1, keepdims=True)
        S = E @ E.T
        np.fill_diagonal(S, -np.inf)
        cur = int(np.argmax(np.sort(S, axis=1)[:, -3:].mean(1)))  # start inside the densest cluster
        seen = np.zeros(len(have), bool)
        group, prev_sim = 0, None
        for _ in range(len(have)):
            seen[cur] = True
            f = have[cur]
            others = {have[j].source.video_id for j in np.argsort(-S[cur])[:5] if S[cur, j] > MATCH_SIM}
            cross = len(others - {f.source.video_id})
            note = ("Visually similar frames are adjacent (SigLIP image embedding)" +
                    (f"; closely matches frames from {cross} other video{'s' * (cross > 1)}" if cross else ""))
            rows.append((f, f"g{group}", note))
            sims = np.where(seen, -np.inf, S[cur])
            if seen.all():
                break
            nxt = int(np.argmax(sims))
            prev_sim = sims[nxt]
            if prev_sim < BREAK_SIM:
                group += 1
            cur = nxt
    rows += [(f, "none", "No embedding yet (run `evidence analyze`)") for f in sorted(rest, key=_time)]
    return _merge_small(rows, 3)


def _merge_small(rows: Sorted, min_size: int) -> Sorted:
    """Runs of blocks smaller than min_size become one 'loose' block, so the grid isn't littered with lone tiles."""
    out: Sorted = []
    i = 0
    while i < len(rows):
        j = i
        while j < len(rows) and rows[j][1] == rows[i][1]:
            j += 1
        g = rows[i][1] if j - i >= min_size else f"loose{len(out)}"
        if g.startswith("loose") and out and out[-1][1].startswith("loose"):
            g = out[-1][1]
        out += [(f, g, n) for f, _, n in rows[i:j]]
        i = j
    return out


def _features_last(frames, key, group, note) -> Sorted:
    have = [f for f in frames if f.derived.features is not None]
    rest = [f for f in frames if f.derived.features is None]
    rows = [(f, group(f.derived.features), note(f.derived.features)) for f in sorted(have, key=lambda f: key(f.derived.features))]
    return rows + [(f, "none", "Not analyzed yet (run `evidence analyze`)") for f in sorted(rest, key=_time)]


def by_angle(frames, _emb) -> Sorted:
    def expected(x):
        return sum(VIEW_ORDER.index(k) * p for k, p in x.viewpoint_scores.items()) if x.viewpoint_scores else 99
    return _features_last(
        [f for f in frames],
        key=lambda x: (VIEW_ORDER.index(x.viewpoint) if x.viewpoint else 99, expected(x)),
        group=lambda x: x.viewpoint or "unknown",
        note=lambda x: (f"Camera angle: {VIEW_NAMES[x.viewpoint]} ({round(x.viewpoint_scores[x.viewpoint] * 100)}%, zero-shot)"
                        if x.viewpoint else "Camera angle unknown"),
    )


def by_damage(frames, _emb) -> Sorted:
    def level(x):
        if x.damage is None:
            return "no buildings"
        return "destroyed" if x.damage >= 0.66 else "damaged" if x.damage >= 0.33 else "intact"
    return _features_last(
        frames,
        key=lambda x: (x.damage is None, -(x.damage or 0)),
        group=level,
        note=lambda x: (f"Visible damage: {level(x)} ({round(x.damage * 100)} on a 0-100 scale, zero-shot)"
                        if x.damage is not None else "Few or no buildings in view"),
    )


def by_scale(frames, _emb) -> Sorted:
    """Close-up to aerial: a flower up close first, a whole town from a drone last."""
    def band(x):
        return "close-up" if x.scale < 0.2 else "near" if x.scale < 0.4 else "street" if x.scale < 0.6 else "wide" if x.scale < 0.8 else "aerial"
    missing = [f for f in frames if f.derived.features is not None and f.derived.features.scale is None]
    rows = _features_last(
        [f for f in frames if f.derived.features is None or f.derived.features.scale is not None],
        key=lambda x: x.scale,
        group=band,
        note=lambda x: f"Scale: {band(x)} ({round(x.scale * 100)} from close-up 0 to aerial 100, zero-shot)",
    )
    return rows + [(f, "none", "Scale not computed yet (run `evidence analyze`)") for f in sorted(missing, key=_time)]


def by_color(frames, _emb) -> Sorted:
    def grey(x):
        return x.hue is None or x.saturation < 0.12
    return _features_last(
        frames,
        key=lambda x: (1, -x.lightness) if grey(x) else (0, (x.hue + 15) % 360),
        group=lambda x: "grey" if grey(x) else f"h{int(((x.hue + 15) % 360) // 30)}",
        note=lambda x: f"Mean colour {x.color_hex}" + (", mostly grey" if grey(x) else f", hue {round(x.hue)}°"),
    )


def by_light(frames, _emb) -> Sorted:
    def band(x):
        return "dark" if x.lightness < 0.25 else "dim" if x.lightness < 0.4 else "mid" if x.lightness < 0.55 else "bright"
    return _features_last(
        frames,
        key=lambda x: x.lightness,
        group=band,
        note=lambda x: f"Light: {band(x)}, {'warm' if x.warmth > 0.04 else 'cool' if x.warmth < -0.04 else 'neutral'} "
                       f"(lightness {round(x.lightness * 100)}%). Cue for time of day and weather",
    )


def by_season(frames, _emb) -> Sorted:
    def stage(x):
        return "snow" if x.snow > 0.15 else "bare" if x.greenness < 0.08 else "some green" if x.greenness < 0.25 else "green"
    order = ["snow", "bare", "some green", "green"]
    return _features_last(
        frames,
        key=lambda x: (order.index(stage(x)), x.greenness),
        group=stage,
        note=lambda x: f"Season cues: {stage(x)} (vegetation {round(x.greenness * 100)}%, snow {round(x.snow * 100)}%). "
                       "Helps bound when footage was shot; not a date",
    )


def by_published(frames, _emb) -> Sorted:
    rows = sorted(frames, key=lambda f: (-f.source.published_at.timestamp(), f.source.video_id, f.frame.timestamp_s))
    return [(f, str(f.source.published_at.year), f"Published on YouTube {f.source.published_at:%Y-%m-%d} (not the capture date)") for f in rows]


def by_detail(frames, _emb) -> Sorted:
    rows = sorted(frames, key=lambda f: -f.derived.quality.sharpness)
    return [(f, "all", f"Sharpness {round(f.derived.quality.sharpness)} (Laplacian variance at full resolution). "
             "Sharper frames hold more measurable detail") for f in rows]


def by_query_image(frames: list[FrameRecord], emb: dict[str, np.ndarray], query: np.ndarray) -> Sorted:
    """Most similar to an uploaded image first (cosine similarity of SigLIP embeddings)."""
    q = query / np.linalg.norm(query)
    scored = sorted(((float(emb[f.frame_id] @ q / np.linalg.norm(emb[f.frame_id])), f) for f in frames if f.frame_id in emb),
                    key=lambda x: -x[0])
    rows = []
    for sim, f in scored:
        band = "very close" if sim >= 0.9 else "close" if sim >= 0.8 else "related" if sim >= 0.7 else "distant"
        rows.append((f, band, f"Similarity to your image: {sim:.2f} ({band}; SigLIP image embedding)"))
    rest = [f for f in frames if f.frame_id not in emb]
    return rows + [(f, "none", "No embedding yet (run `evidence analyze`)") for f in sorted(rest, key=_time)]


SORTS: dict[str, Callable[[list[FrameRecord], dict], Sorted]] = {
    "place": by_place,
    "similar": by_similarity,
    "angle": by_angle,
    "damage": by_damage,
    "scale": by_scale,
    "color": by_color,
    "light": by_light,
    "season": by_season,
    "published": by_published,
    "detail": by_detail,
}


AT_KM = 3.0  # a place this close counts as the place itself


def by_study_place(frames: list[FrameRecord], target, radius_km: float) -> Sorted:
    """Frames whose inferred locations put them at a study-area place first, then those near it (within
    radius_km), then the rest. Uses names only through the gazetteer's positions for the distance."""
    from .focus import nearness

    name = target.name
    rows = []
    for f in frames:
        best = None
        for loc in f.inferred.locations:
            n = nearness(loc, target)
            if n and n[0] <= radius_km and (best is None or (n[0], -loc.confidence) < (best[0], -best[2].confidence)):
                best = (n[0], n[1], loc)
        if best is None:
            rows.append((f, "elsewhere", f"Nothing inferred places this frame within {radius_km:g} km of {name}", (2, 0, 0)))
            continue
        km, what, loc = best
        group = "at" if km <= AT_KM else "near"
        where = f"at {name}" if group == "at" else f"near {name} ({what}, {km:.0f} km away)"
        note = (f"Inferred {where}: {round(loc.confidence * 100)}% ({loc.provenance.method.replace('_', ' ')}). "
                "From metadata, not a verified filming location")
        rows.append((f, group, note, (0 if group == "at" else 1, -loc.confidence, km)))
    rows.sort(key=lambda r: (r[3], _time(r[0])))
    return [(f, g, n) for f, g, n, _ in rows]
