"""Frame-level place (and date) clues from text tied to a moment in the video.

Video-level inference (inference.py) gives every frame the same candidates. These clues are
specific to a frame's timestamp:

* on-screen text (OCR of this frame): "Часів Яр 2021", "Проспект Миру";
* the description chapter the frame falls in ("05:12 Під лісом колишні села");
* speech near the frame (YouTube captions, usually auto-generated) within +/- SPEECH_WINDOW_S.

All of them yield place *names* (no coordinates) with a confidence and provenance that quotes the
evidence. The channel's own logo text (e.g. "Суспільне" / "Дніпро" for Суспільне Дніпро) is ignored.
Repeated on-screen labels are kept on purpose: broadcasters often overlay the region ("Запорізька обл")
or the filming month ("вересень 2023") on every shot, which is exactly the evidence wanted.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import httpx

from . import spatial
from .places import Match, find_places
from .schema import FrameRecord, InferredCaptureDate, InferredLocation, Provenance, VideoRecord

log = logging.getLogger(__name__)

CONF_OCR = 0.55
CONF_CHAPTER = 0.45
CONF_SPEECH_NEAR = 0.4    # spoken within SPEECH_NEAR_S of the frame
CONF_SPEECH_FAR = 0.3     # spoken within SPEECH_WINDOW_S
CONF_OCR_YEAR = 0.4
CONF_OCR_MONTH = 0.5       # "вересень 2023" overlaid on the shot: broadcasters label footage by month
AMBIGUOUS_FACTOR = 0.5    # several settlements share the name and nothing narrows it down
SPEECH_NEAR_S = 15
SPEECH_WINDOW_S = 45

_CHAPTER = re.compile(r"^\s*[\[(]?((?:\d{1,2}:)?\d{1,2}:\d{2})[\])]?\s*[-–—:|.]?\s*(.+?)\s*$")
_YEAR = re.compile(r"(?<!\d)(19[5-9]\d|20[0-2]\d)(?!\d)")
_MONTHS = {  # Ukrainian and Russian, nominative and genitive stems -> month number
    "січ": 1, "лют": 2, "берез": 3, "квіт": 4, "травн": 5, "черв": 6, "лип": 7, "серп": 8, "верес": 9, "жовт": 10,
    "листопад": 11, "груд": 12, "январ": 1, "феврал": 2, "март": 3, "апрел": 4, "ма": 5, "июн": 6, "июл": 7,
    "август": 8, "сентябр": 9, "октябр": 10, "ноябр": 11, "декабр": 12,
}
_MONTH_YEAR = re.compile(r"(?<![\w])([А-Яа-яІіЇїЄєҐґ]{2,9})\s+(19[5-9]\d|20[0-2]\d)(?!\d)")


# ------------------------------------------------------------------ sources


def parse_chapters(description: str, duration_s: float | None) -> list[tuple[float, float, str]]:
    """YouTube-style chapters: lines starting with a timestamp, in ascending order, from 0:00."""
    marks = []
    for line in description.splitlines():
        if m := _CHAPTER.match(line):
            parts = [int(x) for x in m.group(1).split(":")]
            t = parts[-1] + 60 * parts[-2] + (3600 * parts[-3] if len(parts) == 3 else 0)
            marks.append((float(t), m.group(2)))
    if len(marks) < 2 or marks[0][0] != 0 or any(b[0] <= a[0] for a, b in zip(marks, marks[1:])):
        return []
    end = duration_s if duration_s and duration_s > marks[-1][0] else marks[-1][0] + 600
    return [(t, marks[i + 1][0] if i + 1 < len(marks) else end, title) for i, (t, title) in enumerate(marks)]


def fetch_captions(info: dict, prefer: list[str]) -> dict | None:
    """Captions from a fresh yt-dlp info dict. (The Data API lists caption tracks but only lets a video's
    owner download them, so the text comes through yt-dlp.) The original track, which place matching
    reads: manual in a preferred language other than English, else the auto captions of what is spoken,
    else manual English. Plus the uploader's own English subtitles when the original isn't English
    (``english``, else None). YouTube's auto-translation is not used: it is rate-limited (HTTP 429) for downloads.
    Returns {"lang", "kind", "cues": [[start, end, text], ...], "word_times": [[t, ...] per cue], "english": {...} | None};
    ``word_times`` gives when each whitespace-separated word of a cue is spoken (auto captions time every word)."""
    manual = {k: v for k, v in (info.get("subtitles") or {}).items() if k != "live_chat"}
    auto = info.get("automatic_captions") or {}
    base = lambda k: k.split("-")[0].lower()  # "uk-UA" -> "uk"
    choice = None
    for lang in prefer:
        if lang != "en" and (key := next((k for k in manual if base(k) == lang), None)):
            choice = ("manual", lang, manual[key])
            break
    if not choice:
        orig = [k for k in auto if k.endswith("-orig")]
        orig.sort(key=lambda k: prefer.index(k[:-5]) if k[:-5] in prefer else 99)
        if orig:
            choice = ("auto", orig[0][:-5], auto[orig[0]])
    if not choice and (key := next((k for k in manual if base(k) == "en"), None)):
        choice = ("manual", "en", manual[key])
    if not choice:
        return None
    kind, lang, formats = choice
    got = _json3(formats)
    if got is None:
        return None
    cues, times = got
    english = None
    if base(lang) != "en" and (key := next((k for k in manual if base(k) == "en"), None)):
        if (en := _json3(manual[key])) and en[0]:
            english = {"lang": key, "kind": "manual", "cues": en[0], "word_times": en[1]}
    return {"lang": lang, "kind": kind, "cues": cues, "word_times": times, "english": english}


def _json3(formats: list[dict]) -> tuple[list[list], list[list[float]]] | None:
    """Cues [[start, end, text]] and, per cue, the time of each of its words (text.split())."""
    url = next((f["url"] for f in formats if f.get("ext") == "json3"), None)
    if not url:
        return None
    data = httpx.get(url, timeout=30).json()
    cues, times = [], []
    for ev in data.get("events", []):
        segs = ev.get("segs") or []
        text = "".join(s.get("utf8", "") for s in segs).strip()
        if not text:
            continue
        start = ev.get("tStartMs", 0) / 1000
        end = start + ev.get("dDurationMs", 0) / 1000
        at = []  # a segment is one word in auto captions, a whole line in manual ones: spread its words
        for i, seg in enumerate(segs):
            words = seg.get("utf8", "").split()
            t0 = start + seg.get("tOffsetMs", 0) / 1000
            t1 = start + segs[i + 1].get("tOffsetMs", 0) / 1000 if i + 1 < len(segs) else end
            at += [round(t0 + (max(t1, t0) - t0) * k / len(words), 2) for k in range(len(words))]
        cues.append([round(start, 2), round(end, 2), text])
        times.append(at)
    return cues, times


def load_captions(path: Path) -> dict | None:
    return json.loads(path.read_text()) if path.exists() else None


def english_captions_path(video_dir):
    """Local machine translation of the captions (derived, not from YouTube)."""
    return video_dir / "derived" / "captions_en.json"


def english_captions(video_dir, captions: dict | None) -> dict | None:
    """The English track to read alongside the original: the uploader's English subtitles, else the local
    machine translation. None when the original is English or there is neither."""
    if captions and captions.get("english"):
        return captions["english"]
    return load_captions(english_captions_path(video_dir))


PARAGRAPH_S = 20   # a subtitle paragraph spans at most this long
PAUSE_S = 6        # ... and breaks early at a pause this long between cues


def _groups(cues: list[list]) -> list[list[int]]:
    """Indices of the cues in each paragraph (see paragraphs)."""
    out: list[list[int]] = []
    first = last = 0.0
    for i, (start, _, text) in enumerate(cues):
        if not text.split():
            continue
        if out and start - first < PARAGRAPH_S and start - last < PAUSE_S:
            out[-1].append(i)
        else:
            out.append([i])
            first = start
        last = start
    return out


def paragraphs(cues: list[list]) -> list[list]:
    """Join caption cues (auto captions: a few overlapping words each) into short paragraphs,
    [[start, end, text], ...], for translation (which needs whole phrases) and place matching."""
    return [[cues[g[0]][0], max(cues[i][1] for i in g), " ".join(w for i in g for w in cues[i][2].split())]
            for g in _groups(cues)]


def timed_words(track: dict | None) -> list[list]:
    """[[t, word], ...] for a caption track: each word at the moment it is spoken, when the track times its
    words (auto captions); otherwise spread evenly over its cue (a manual line, or a translated paragraph)."""
    cues = (track or {}).get("cues") or []
    times = (track or {}).get("word_times") or []
    out = []
    for i, (start, end, text) in enumerate(cues):
        words = text.split()
        at = times[i] if i < len(times) and len(times[i]) == len(words) else None
        if at is None:
            stop = min(end, cues[i + 1][0]) if i + 1 < len(cues) else end
            at = [start + (max(stop, start) - start) * k / max(1, len(words)) for k in range(len(words))]
        out += [[round(t, 2), w] for t, w in zip(at, words)]
    return out


NON_SPEECH = re.compile(r"^\[.*\]$|^>>$")  # "[музика]", "[Music]"; ">>" marks a new speaker


# English names for places the original names, for marking them in the English row: exonyms, and
# what the local translation turns them into (it mangles names: "Каховського" -> "Cahokia", "Kachovsky").
# Used only when the original or the metadata names the place.
EN_NAMES = {
    "Dnipro": r"dniep(?:er|r)\w*",
    "Velykyi Luh": r"(?:great|big)\s+meadows?|luh\w*|lug[ua]?",
    "Kakhovka": r"ka[ck]?hovk\w*|kachovsk\w*|kakhovsk\w*|cahok\w*",
    "Zaporizhzhya": r"zaporo[zž]h?\w*",
    "Zaporizhzhia Oblast": r"zaporo[zž]h?\w*",
    "Nikopol": r"nicopol\w*",
    "Dnipropetrovsk Oblast": r"dnipropetrov\w*|dnepropetrov\w*",
}


def _flags(timed: list[list], allow: set[str], english: bool = False) -> tuple[list[int], set[str]]:
    """Flag each word (see subtitles) and return the place names found. English: a place name is only
    marked when the original or the video's metadata names that place (a translation never adds one)."""
    text, offsets = "", []
    for _, w in timed:
        offsets.append(len(text) + (1 if text else 0))
        text += (" " if text else "") + w
    place, names = [False] * len(timed), set()
    spans = []
    for m in find_places(text, allow=allow, speech=True):
        if english and m.name not in allow:
            continue
        names.add(m.name)
        spans.append((m.start, m.start + len(m.matched)))
    if english:
        for name in allow & EN_NAMES.keys():
            spans += [m.span() for m in re.finditer(rf"\b(?:{EN_NAMES[name]})\b", text, re.IGNORECASE)]
    for start, stop in spans:
        for k, a in enumerate(offsets):  # every word the match touches (the whole inflected word)
            if a < stop and start < a + len(timed[k][1]):
                place[k] = True
    flags = [1 if place[k] else 2 if NON_SPEECH.match(w) else 3 if spatial.is_spatial(w, english) else 0
             for k, (_, w) in enumerate(timed)]
    for k in range(1, len(timed)):  # "200 метрів", "five kilometres": the number goes with its unit
        if (flags[k] in (0, 3) and flags[k - 1] == 0 and spatial.is_unit(timed[k][1], english)
                and spatial.is_number(timed[k - 1][1], english)):
            flags[k - 1] = flags[k] = 3
    return flags, names


def subtitles(video: VideoRecord, captions: dict | None, english: dict | None) -> dict:
    """A video's subtitles laid out in time, for the timeline: every word of the original with the moment
    it is spoken and a flag (1 = part of a place name, 2 = not speech, e.g. "[музика]", 3 = describes the land:
    water, terrain, roads, directions, distances; see spatial.py), and the English
    words (the uploader's English subtitles, or a local machine translation spread over each phrase).
    Place names are matched in the original, over whole paragraphs (the same matcher as the speech clues;
    a name split across two cues still matches). The English words get the same flags for reading
    alongside, but a place is only marked there when the original or the metadata names it: this is
    display emphasis, never a location clue."""
    meta = {k: english[k] for k in ("lang", "kind", "from", "model") if english and k in english} or None
    if not captions or not captions.get("cues"):
        return {"lang": None, "kind": None, "english": None, "words": [], "en": []}
    allow = video_clues(video, [], None).text_places
    cues, times = captions["cues"], captions.get("word_times") or []
    words, said = [], set()
    for g in _groups(cues):
        timed = timed_words({"cues": [cues[i] for i in g], "word_times": [times[i] if i < len(times) else [] for i in g]})
        flags, names = _flags(timed, allow)
        said |= names
        words += [[t, w, f] for (t, w), f in zip(timed, flags)]
    en = timed_words(english)
    en_flags, _ = _flags(en, allow | said, english=True) if en else ([], set())
    return {"lang": captions.get("lang"), "kind": captions.get("kind"), "english": meta,
            "words": words, "en": [[t, w, f] for (t, w), f in zip(en, en_flags)]}


# ------------------------------------------------------------------ clues


@dataclass
class VideoClues:
    chapters: list[tuple[float, float, str, list[Match]]] = field(default_factory=list)
    speech: list[tuple[float, float, str, list[Match]]] = field(default_factory=list)
    watermarks: set[str] = field(default_factory=set)
    text_places: set[str] = field(default_factory=set)     # named in title/description/tags
    text_oblasts: set[str] = field(default_factory=set)
    caption_kind: str | None = None


def _norm(text: str) -> str:
    return re.sub(r"\W+", " ", text.lower()).strip()


def video_clues(video: VideoRecord, frames: list[FrameRecord], captions: dict | None) -> VideoClues:
    s = video.source
    vc = VideoClues()
    meta_text = "\n".join([s.title, s.description, " | ".join(s.tags)])
    for m in find_places(meta_text):
        vc.text_places.add(m.name)
        vc.text_oblasts.update(m.oblasts)
        if m.name.endswith("Oblast"):
            vc.text_oblasts.add(m.name)
    for start, end, title in parse_chapters(s.description, s.duration_s):
        vc.chapters.append((start, end, title, find_places(title)))
    if captions:
        vc.caption_kind = captions.get("kind")
        for start, end, text in captions.get("cues", []):
            if found := find_places(text, allow=vc.text_places, speech=True):
                vc.speech.append((start, end, text, found))
    # The channel's logo, which OCR often splits into one line per word.
    vc.watermarks = set(_norm(s.channel_title or "").split())
    return vc


def _conf(base: float, m: Match, vc: VideoClues) -> tuple[float, str]:
    """Scale down names shared by several settlements unless the video names one of their oblasts."""
    if len(m.places) <= 1:
        return base, ""
    pops = sorted((p.population for p in m.places), reverse=True)
    if pops[0] >= 10_000 and pops[0] >= 5 * pops[1]:  # one well-known town dwarfs its namesakes (e.g. Kostiantynivka, Donetsk Oblast)
        return base, ""
    oblasts = {p.oblast for p in m.places}
    hit = oblasts & vc.text_oblasts
    if hit:
        return base, f" Several places share this name; the video names {', '.join(sorted(hit))}."
    return round(base * AMBIGUOUS_FACTOR, 3), f" {len(m.places)} places in Ukraine share this name; which one is unknown."


def frame_clues(vc: VideoClues, f: FrameRecord) -> tuple[list[InferredLocation], list[InferredCaptureDate]]:
    t = f.frame.timestamp_s
    locs: dict[tuple[str, str], InferredLocation] = {}

    def add(m: Match, base: float, method: str, evidence: str) -> None:
        conf, note = _conf(base, m, vc)
        key = (m.name, method)
        if key not in locs or locs[key].confidence < conf:
            locs[key] = InferredLocation(place_name=m.name, confidence=conf,
                                         provenance=Provenance(method=method, evidence=evidence + note))

    dates: list[InferredCaptureDate] = []
    if f.derived.ocr:
        for line in f.derived.ocr.lines:
            words = _norm(line.text).split()
            if not words or set(words) <= vc.watermarks:
                continue
            for m in find_places(line.text, proper_nouns_only=True):
                add(m, CONF_OCR, "frame_onscreen_text",
                    f"{line.text!r} is written on screen in this frame (OCR). A caption can name a place other than the one shown.")
            published = f.source.published_at.date()
            dated = set()
            for word, y in _MONTH_YEAR.findall(line.text):
                w = word.lower()
                month = 5 if w in ("май", "мая") else next((n for stem, n in _MONTHS.items() if len(stem) >= 3 and w.startswith(stem)), None)
                y = int(y)
                if month and date(y, month, 1) <= published:
                    last = date(y + (month == 12), month % 12 + 1, 1).toordinal() - 1
                    dates.append(InferredCaptureDate(
                        earliest=date(y, month, 1), latest=min(date.fromordinal(last), published), confidence=CONF_OCR_MONTH,
                        provenance=Provenance(method="frame_onscreen_date",
                                              evidence=f"{line.text!r} is written on screen in this frame (OCR); broadcasters label footage by when it was filmed."),
                    ))
                    dated.add(y)
            for y in {int(y) for y in _YEAR.findall(line.text)} - dated:
                if y <= published.year and line.confidence >= 0.5:
                    dates.append(InferredCaptureDate(
                        earliest=date(y, 1, 1), latest=min(date(y, 12, 31), published), confidence=CONF_OCR_YEAR,
                        provenance=Provenance(method="frame_onscreen_year",
                                              evidence=f"{line.text!r} is written on screen in this frame (OCR); it may date the shot."),
                    ))
    for start, end, title, found in vc.chapters:
        if start <= t < end:
            for m in found:
                add(m, CONF_CHAPTER, "description_chapter",
                    f"Frame falls in chapter {_clock(start)} {title!r} of the description.")
    for start, end, text, found in vc.speech:
        gap = max(0.0, start - t, t - end)
        if gap <= SPEECH_WINDOW_S:
            base = CONF_SPEECH_NEAR if gap <= SPEECH_NEAR_S else CONF_SPEECH_FAR
            for m in found:
                kind = "auto-generated captions" if vc.caption_kind == "auto" else "captions"
                add(m, base, "speech_captions",
                    f"{m.matched!r} said at {_clock(start)} ({round(gap)} s from this frame; {kind}): {text[:90]!r}.")
    return list(locs.values()), dates


def merge(video_level: list[InferredLocation], frame_level: list[InferredLocation]) -> list[InferredLocation]:
    return sorted([*frame_level, *video_level], key=lambda loc: -loc.confidence)


def _clock(s: float) -> str:
    s = int(s)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"
