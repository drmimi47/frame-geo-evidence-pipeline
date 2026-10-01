"""Collection scope: Ukraine only, YouTube publication date 2022-01-01..2026-12-31.

Both rules are hard limits enforced at ingestion (nothing out of scope is
written to disk) and re-checkable with `evidence rescope`.

- The date limit applies to the *YouTube publication date* only. Footage published
  in range may show events from before 2022; that is expected and handled as an
  inferred capture-date question (see inference.py), not a scope violation.
- Ukraine relevance is *inferred* from source metadata and recorded with its
  evidence. It says "this video is about Ukraine", never "this frame was shot at X".
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from .schema import ScopeCheck, ScopeSignal, SourceVideo

HARD_START = date(2022, 1, 1)
HARD_END = date(2026, 12, 31)

# lon_min, lat_min, lon_max, lat_max -- generous box around Ukraine incl. Crimea.
UKRAINE_BBOX = (22.0, 44.3, 40.3, 52.4)

SCOPE_RULES_VERSION = "1"
MIN_CONFIDENCE = 0.5
MAX_CONFIDENCE = 0.95  # an inference is never certain

# Canonical English name -> spellings. Latin spellings match whole words; Cyrillic
# spellings are stems matched at a word start (to cover case endings: Києві, Харкова).
# A trailing "=" forces a whole-word match for stems that prefix common words.
GAZETTEER: dict[str, tuple[str, ...]] = {
    "Ukraine": ("ukraine", "ukrainian", "україн", "украин"),
    # oblasts / regions
    "Crimea": ("crimea", "крим=", "криму=", "кримськ", "крым=", "крыма=", "крымск"),
    "Donbas": ("donbas", "donbass", "донбас"),
    "Kyiv Oblast": ("київщин", "киевщин"),
    "Kharkiv Oblast": ("харківщин", "харьковщин"),
    "Dnipropetrovsk Oblast": ("dnipropetrovsk", "дніпропетровськ", "днепропетровск", "дніпропетровщин", "днепропетровщин"),
    "Zaporizhzhia Oblast": ("запоріжжя", "запоріжж", "запорізьк", "запорож"),
    "Donetsk Oblast": ("donetsk", "донецьк", "донецк", "донеччин"),
    "Luhansk Oblast": ("luhansk", "lugansk", "луганськ", "луганск", "луганщин"),
    "Kherson Oblast": ("kherson", "херсон"),
    "Mykolaiv Oblast": ("mykolaiv", "nikolaev", "миколаїв", "николаев"),
    "Odesa Oblast": ("odesa", "odessa", "одес"),
    "Sumy Oblast": ("sumy", "сумськ", "сумщин", "сумах="),
    "Chernihiv Oblast": ("chernihiv", "chernigov", "чернігів", "чернігов", "чернигов"),
    "Poltava Oblast": ("poltava", "полтав"),
    "Vinnytsia Oblast": ("vinnytsia", "вінниц", "винниц"),
    "Zhytomyr Oblast": ("zhytomyr", "житомир"),
    "Lviv Oblast": ("lviv", "lvov", "львів", "львов"),
    "Volyn Oblast": ("volyn", "волин", "волын"),
    "Rivne Oblast": ("rivne", "рівненськ", "рівненщин", "ровенск"),
    "Ternopil Oblast": ("ternopil", "тернопіл", "тернопол"),
    "Khmelnytskyi Oblast": ("khmelnytskyi", "хмельницьк", "хмельницк"),
    "Ivano-Frankivsk Oblast": ("ivano-frankivsk", "івано-франківськ", "ивано-франковск"),
    "Zakarpattia Oblast": ("zakarpattia", "uzhhorod", "закарпатт", "ужгород"),
    "Chernivtsi Oblast": ("chernivtsi", "чернівц", "черновц"),
    "Cherkasy Oblast": ("cherkasy", "черкас"),
    "Kirovohrad Oblast": ("kropyvnytskyi", "kirovohrad", "кропивницьк", "кіровоград", "кировоград"),
    # cities and frequently documented places
    "Kyiv": ("kyiv", "kiev", "київ", "києв", "киев"),
    "Kharkiv": ("kharkiv", "kharkov", "харків", "харков"),
    "Dnipro": ("dnipro", "дніпро", "дніпр", "днепр"),
    "Mariupol": ("mariupol", "маріупол", "мариупол"),
    "Bakhmut": ("bakhmut", "бахмут"),
    "Avdiivka": ("avdiivka", "avdeevka", "авдіїв", "авдеев"),
    "Irpin": ("irpin", "ірпін", "ирпен"),
    "Bucha": ("bucha", "буча=", "бучі=", "бучу=", "бучанськ"),
    "Hostomel": ("hostomel", "гостомел"),
    "Borodianka": ("borodianka", "бородянк"),
    "Kramatorsk": ("kramatorsk", "краматорськ", "краматорск"),
    "Sloviansk": ("sloviansk", "slavyansk", "слов'янськ", "славянск"),
    "Sievierodonetsk": ("sievierodonetsk", "severodonetsk", "сєвєродонецьк", "северодонецк"),
    "Lysychansk": ("lysychansk", "лисичанськ", "лисичанск"),
    "Izium": ("izium", "izyum", "ізюм", "изюм"),
    "Kupiansk": ("kupiansk", "куп'янськ", "купянск"),
    "Pokrovsk": ("pokrovsk", "покровськ", "покровск"),
    "Chasiv Yar": ("chasiv yar", "часів яр", "часов яр"),
    "Vuhledar": ("vuhledar", "вугледар", "угледар"),
    "Soledar": ("soledar", "соледар"),
    "Nikopol": ("nikopol", "нікопол", "никопол"),
    "Enerhodar": ("enerhodar", "енергодар", "энергодар"),
    "Kakhovka": ("kakhovka", "каховк", "каховськ", "каховск"),
    "Melitopol": ("melitopol", "мелітопол", "мелитопол"),
    "Berdiansk": ("berdiansk", "бердянськ", "бердянск"),
    "Huliaipole": ("huliaipole", "гуляйпол"),
    "Orikhiv": ("orikhiv", "оріхів", "орехов"),
    "Vovchansk": ("vovchansk", "вовчанськ", "волчанск"),
    "Okhtyrka": ("okhtyrka", "охтирк", "ахтырк"),
    "Kremenchuk": ("kremenchuk", "кременчук"),
    "Velykyi Luh": ("velykyi luh", "великий луг", "великого лугу", "великому лузі"),
}

_UK_LETTERS = re.compile(r"[іїєґІЇЄҐ]")
# Ukrainian-specific letters that Belarusian/Russian don't use: ї, є, ґ.
_UK_ONLY = re.compile(r"[їєґЇЄҐ]")

_WEIGHTS = {"geotag": 0.9, "title": 0.8, "tags": 0.7, "description": 0.6, "language": 0.4}


def _compile() -> list[tuple[str, re.Pattern]]:
    out = []
    for canonical, spellings in GAZETTEER.items():
        parts = []
        for s in spellings:
            if s.endswith("="):
                parts.append(rf"(?<!\w){re.escape(s[:-1])}(?!\w)")
            elif s.isascii():
                parts.append(rf"\b{re.escape(s)}\b")
            else:
                parts.append(rf"(?<!\w){re.escape(s)}")
        out.append((canonical, re.compile("|".join(parts), re.IGNORECASE)))
    return out


_PATTERNS = _compile()


def mentioned_places(text: str) -> list[tuple[str, str]]:
    """(canonical name, matched text) for every gazetteer entry found in text."""
    found = []
    for canonical, pat in _PATTERNS:
        if m := pat.search(text):
            found.append((canonical, m.group(0)))
    return found


def in_ukraine_bbox(lat: float, lon: float) -> bool:
    lon_min, lat_min, lon_max, lat_max = UKRAINE_BBOX
    return lat_min <= lat <= lat_max and lon_min <= lon <= lon_max


def in_date_range(published: date) -> bool:
    return HARD_START <= published <= HARD_END


@dataclass(frozen=True)
class Verdict:
    accepted: bool
    reason: str
    check: ScopeCheck | None


def check_scope(source: SourceVideo, min_confidence: float = MIN_CONFIDENCE) -> Verdict:
    """Hard scope gate. Call before writing anything for a video."""
    published = source.published_at.date()
    if not in_date_range(published):
        return Verdict(False, f"published {published} outside hard range {HARD_START}..{HARD_END}", None)

    signals: list[ScopeSignal] = []
    geo = source.claimed_recording_location
    if geo and geo.latitude is not None and geo.longitude is not None:
        inside = in_ukraine_bbox(geo.latitude, geo.longitude)
        signals.append(ScopeSignal(
            kind="geotag", field="recordingDetails.location", match=f"{geo.latitude},{geo.longitude}",
            weight=_WEIGHTS["geotag"] if inside else -1.0,
        ))
    fields = {"title": source.title, "tags": " | ".join(source.tags), "description": source.description}
    for field, text in fields.items():
        for canonical, matched in mentioned_places(text):
            signals.append(ScopeSignal(kind="gazetteer", field=field, match=f"{matched} -> {canonical}", weight=_WEIGHTS[field]))
    lang = (source.default_language or "").lower()
    if lang.startswith("uk") or _UK_ONLY.search(source.title) or len(_UK_LETTERS.findall(source.title + source.description)) >= 5:
        signals.append(ScopeSignal(kind="language", field="language/title", match=lang or "ukrainian letters", weight=_WEIGHTS["language"]))

    if any(s.weight < 0 for s in signals):
        conf = 0.0
        reason = "uploader geotag is outside Ukraine"
    else:
        # Noisy-OR over independent signals.
        miss = 1.0
        for s in signals:
            miss *= 1 - s.weight
        conf = round(min(1 - miss, MAX_CONFIDENCE), 3)
        reason = f"Ukraine relevance {conf:.2f} (min {min_confidence})" if signals else "no Ukraine signal in title, tags, description, language or geotag"
    check = ScopeCheck(in_scope=conf >= min_confidence, confidence=conf, signals=signals, rules_version=SCOPE_RULES_VERSION)
    return Verdict(check.in_scope, reason, check)
