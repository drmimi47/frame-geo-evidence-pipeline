"""Ukrainian place-name matching: the curated scope gazetteer plus ~10k GeoNames settlements.

Used for frame-level location clues (on-screen text, chapters, speech) and video text. Matching
returns *names* only: coordinates from the gazetteer are used for internal checks (e.g. is the
uploader geotag near any place the video names?) and are never attached to a frame.

Ukrainian and Russian inflect place names (Маріуполь -> Маріуполя, Авдіївка -> Авдіївці). Each
Cyrillic name is indexed with the case forms its ending takes, so a word must be a real form of the
name. A loose stem is not enough: "рівня" ("level") is not a form of Рівне. Big places match
anywhere. Small ones need to be written as a proper noun, not at the start of a sentence, because
many village names are also ordinary words.
"""

from __future__ import annotations

import gzip
import math
import re
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from itertools import product

from .scope import _PATTERNS as _CURATED

BIG_POPULATION = 50_000  # matches even in lower-case text (auto captions); smaller towns' names are often ordinary words
_WORD = re.compile(r"[A-Za-zА-Яа-яІіЇїЄєҐґЁё][A-Za-zА-Яа-яІіЇїЄєҐґЁё'’ʼ]*")  # hyphens split words: Часів-Яр = Часів Яр
_CYR = re.compile(r"[А-Яа-яІіЇїЄєҐґЁё]")
_SENTENCE_START = re.compile(r"(^|[.!?…:«»\"„“\n]\s*|^\W*)$")
_OBLAST_WORD = re.compile(r"^\W*(обл|област|oblast|region|регіон)", re.IGNORECASE)
# Settlement names that are also everyday words, surnames, or very common repeated names.
_COMMON = {
    "мир", "нова", "новий", "нове", "зоря", "дружба", "перемога", "весела", "веселе", "степове", "лісове",
    "садове", "сонячне", "центральне", "польове", "травневе", "шевченко", "шевченкове", "калинівка",
    "олександрівка", "іванівка", "петрівка", "миколаївка", "андріївка", "михайлівка", "новоселівка",
    "мирне", "світле", "прогрес", "урожайне", "виноградне", "вишневе", "квіткове", "зелене", "лиман",
    "тополі", "берег", "острів", "яр", "балка", "долина", "поле", "гора", "майдан", "центр", "площа",
    "верба", "вода", "луг", "ліс", "азов", "буде", "карпати", "дніпровське", "українка", "мена", "щастя", "зелена",
    "глибока", "висока", "високий", "берегове", "гребінка", "стрий", "центральний", "основа",
    "победа", "мирное", "новое", "дружное", "степное", "лесное", "садовое", "солнечное",
    "may", "mir", "nova", "novyi", "center", "victory", "pobeda", "druzhba", "hora", "azov",
    "vladimir", "play", "paris", "svoboda", "свобода", "radio", "media", "news",
    "tik", "тік", "тик",  # Tik-Tok / Тік-Ток: hyphens split words
}


@dataclass(frozen=True)
class Place:
    name: str               # canonical English name
    oblast: str             # "" for curated entries without one
    population: int
    lat: float | None
    lon: float | None
    curated: bool = False   # from scope.GAZETTEER (hand-checked spellings)


@dataclass(frozen=True)
class Match:
    name: str
    matched: str            # the text that matched
    places: tuple[Place, ...]  # >1 when the name is ambiguous (several settlements share it)
    start: int              # character offset in the text

    @property
    def oblasts(self) -> list[str]:
        return sorted({p.oblast for p in self.places if p.oblast})


def _norm(word: str) -> str:
    return word.lower().replace("ё", "е").replace("’", "'").replace("ʼ", "'")


def _forms(word: str) -> set[str]:
    """Case forms of one word of a place name (nominative included)."""
    w = _norm(word)
    if not _CYR.search(w):
        return {w, w + "'s"}
    out = {w}
    def add(stem: str, endings: str) -> None:
        if len(stem) >= 4:  # very short stems inflect into ordinary words ("стр" + "ого" = "строго")
            out.update(stem + e for e in endings.split())
    if w.endswith(("ий", "ій", "ой", "ый")):              # masc. adjective: Кривий, Великий
        add(w[:-2], "ого ому им ім ий ій ый ой")
    elif w.endswith(("е", "є", "ое")):                     # neut. adjective / noun: Рівне, Мирне, Запоріжжя-type handled by я
        add(w[:-1], "е ого ому им ім") if not w.endswith("ое") else add(w[:-2], "ое ого ому ым ом")
    elif w.endswith("ка"):                                 # Авдіївка -> Авдіївки, Авдіївці, Авдіївку
        add(w[:-2], "ка ки ці ку кою ке кой ки")
    elif w.endswith("га"):
        add(w[:-2], "га ги зі гу гою ге гой")
    elif w.endswith(("а", "я")):                           # Буча, Запоріжжя
        s, soft = w[:-1], w.endswith("я")
        add(s, "я і ю ею ї ей" if soft else "а и і у ою ої ій ы е ой")
    elif w.endswith("ь"):                                  # Маріуполь -> Маріуполя, Маріуполі
        add(w[:-1], "ь я ю ем і е ём")
    elif w.endswith("о"):                                  # Дніпро -> Дніпра, Дніпрі
        add(w[:-1], "о а у і ом е")
    elif w.endswith(("и", "і", "ы")):                      # plural names: Черкаси, Суми
        add(w[:-1], "и і ы ах ам ами ів")
    elif w.endswith("ів"):                                 # Харків -> Харкова (і -> о)
        add(w[:-2] + "ов", "а у і ом")
        add(w, "а у і ом")
    elif w.endswith("їв"):                                 # Київ -> Києва
        add(w[:-2] + "єв", "а у і ом")
    else:                                                  # consonant: Бахмут -> Бахмута, Бахмуті
        add(w, "а у і ом ові е")
    return {f for f in out if f == w or f not in _COMMON}


@lru_cache(maxsize=1)
def _index() -> tuple[dict[tuple[str, ...], list[Place]], int]:
    idx: dict[tuple[str, ...], list[Place]] = {}
    raw = resources.files(__package__).joinpath("data/ua_places.tsv.gz").read_bytes()
    for line in gzip.decompress(raw).decode("utf-8").splitlines()[1:]:
        gid, name, fcode, oblast, pop, lat, lon, forms = line.split("\t")
        big = int(pop) >= BIG_POPULATION or fcode in ("PPLC", "PPLA")  # capital / oblast centres
        oblast = oblast if not oblast or oblast.endswith("Oblast") or oblast.endswith("City") else f"{oblast} Oblast"
        place = Place(name, oblast, max(int(pop), BIG_POPULATION) if big else int(pop),
                      float(lat), float(lon))
        for form in forms.split("|"):
            words = _WORD.findall(form)
            if not words or (len(words) == 1 and _norm(words[0]) in _COMMON):
                continue
            variants = [sorted(_forms(w)) for w in words]
            for key in list(product(*variants))[:400]:
                bucket = idx.setdefault(key, [])
                if place not in bucket:
                    bucket.append(place)
    return idx, max(len(k) for k in idx)


def find_places(text: str, *, proper_nouns_only: bool = False, allow: set[str] | None = None,
                speech: bool = False) -> list[Match]:
    """Place names in text.

    proper_nouns_only: every settlement must be capitalised (titles, on-screen text).
    speech: lower-case/unreliably capitalised text (auto captions): only big places, or names in
        ``allow`` (e.g. places the video's own title/description already named).
    Otherwise big places match anywhere; small ones must be capitalised and not start a sentence.
    """
    # Curated spellings first (oblasts, regions, reservoirs, big cities with irregular forms).
    # Each hit spans the whole word it starts; a hit inside a longer one is dropped (ДНІПР in ДНІПРОПЕТРОВСЬКА).
    curated: list[tuple[int, int, str, str]] = []
    for canonical, pat in _CURATED:
        if canonical == "Ukraine":
            continue
        for m in pat.finditer(text):
            end = m.end() + re.match(r"\w*", text[m.end():]).end()
            curated.append((m.start(), end, canonical, m.group(0)))
    curated = [c for c in curated if not any(o[0] <= c[0] and c[1] <= o[1] and len(o[3]) > len(c[3]) for o in curated)]
    claimed: dict[tuple[int, int], str] = {}
    first: dict[str, Match] = {}
    for start, end, canonical, matched in sorted(curated):
        # A city-stem oblast name only claims its words when followed by "обл." etc., so "Херсон" still yields Kherson city.
        if not canonical.endswith("Oblast") or _OBLAST_WORD.match(text[end:]):
            claimed[(start, end)] = canonical
        if canonical not in first:
            known = [p for p in lookup(canonical) if p.name == canonical or canonical in _aliases().get(p.name, ())]
            # a curated name means the well-known place, not its small namesakes
            places = (max(known, key=lambda p: p.population),) if known else (Place(canonical, "", BIG_POPULATION, None, None, curated=True),)
            first[canonical] = Match(canonical, matched, places, start)
    out = list(first.values())
    have = set(first)
    idx, longest = _index()
    words = list(_WORD.finditer(text))
    i = 0
    while i < len(words):
        hit = None
        for n in range(min(longest, len(words) - i), 0, -1):
            span = words[i : i + n]
            s0, s1 = span[0].start(), span[-1].end()
            overlap = [k for k in claimed if k[0] < s1 and s0 < k[1]]
            # Overlapping a curated hit is only allowed for a longer name containing it (Нова Каховка > Каховка).
            if overlap and not all(s0 <= a and b <= s1 and (s1 - s0) > (b - a) and n > 1 for a, b in overlap):
                continue
            places = idx.get(tuple(_norm(w.group(0)) for w in span))
            if not places:
                continue
            big = any(p.population >= BIG_POPULATION for p in places)
            top = max(places, key=lambda p: p.population).name
            name = next(iter(_aliases().get(top, ())), top)  # GeoNames "Avdiyivka" -> curated "Avdiivka"
            allowed = allow is not None and name in allow
            first = span[0].group(0)
            capitalised = first[:1].isupper()
            if speech:
                ok = big or allowed
            elif proper_nouns_only:
                ok = capitalised
            else:
                # one-word Cyrillic names at a sentence start may just be a capitalised common word
                sentence_start = n == 1 and _CYR.search(first) and _SENTENCE_START.search(text[:s0])
                ok = big or allowed or (capitalised and not sentence_start)
            if ok:
                for k in overlap:  # the longer name replaces the curated hit it contains
                    replaced = claimed.pop(k)
                    out = [m for m in out if m.name != replaced]
                    have.discard(replaced)
                hit = (n, Match(name, text[s0:s1], tuple(places), s0))
                break
        if hit:
            n, m = hit
            if m.name not in have:
                out.append(m)
                have.add(m.name)
            i += n
        else:
            i += 1
    return sorted(out, key=lambda m: m.start)


@lru_cache(maxsize=1)
def _aliases() -> dict[str, tuple[str, ...]]:
    """GeoNames English name -> curated canonical name(s), when GeoNames lists the curated spelling."""
    out: dict[str, set[str]] = {}
    for canonical, _ in _CURATED:
        for p in _index()[0].get(tuple(_norm(w) for w in _WORD.findall(canonical)), []):
            if p.name != canonical and not canonical.endswith("Oblast"):
                out.setdefault(p.name, set()).add(canonical)
    return {k: tuple(sorted(v)) for k, v in out.items()}


def lookup(name: str) -> list[Place]:
    """Gazetteer entries for a canonical or local name (for internal distance checks only)."""
    return _index()[0].get(tuple(_norm(w) for w in _WORD.findall(name)), [])


def km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(a))
