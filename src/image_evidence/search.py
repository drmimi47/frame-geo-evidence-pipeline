"""Free-text query parsing for frame search (storage-independent).

A query like "people in Kyiv" becomes terms that must all match (AND). Each term is one of:
- a *visual* term: a category label or common word for one ("person" -> people,
  "buildings" -> architecture). It matches frames the classifier labeled, not video text.
  Otherwise every frame of a video titled "... landscape ..." would match "landscape".
- a *text* term: matched at word starts in the video title, tags, description, and channel,
  and in the frame's inferred place names. Known places expand to all their spellings,
  so "kyiv" also finds "Київ" and "Kiev".
Filler words ("footage", "of", "the", ...) are dropped.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .scope import GAZETTEER

STOPWORDS = frozenset("""
a an the of in on at and or with without from to for by near around about into over under this that these those
footage video videos photo photos image images picture pictures pic pics clip clips frame frames shot shots
show shows showing scene scenes view views some any all
""".split())

# Words people type -> category labels (see config.DEFAULT_LABELS). Singular forms;
# simple English plurals are handled by _singular().
VISUAL_SYNONYMS: dict[str, tuple[str, ...]] = {
    "people": ("people",), "person": ("people",), "man": ("people",), "men": ("people",),
    "woman": ("people",), "women": ("people",), "human": ("people",), "soldier": ("people",),
    "crowd": ("people",), "civilian": ("people",), "child": ("people",), "children": ("people",),
    "kid": ("people",), "face": ("people",), "portrait": ("people",), "volunteer": ("people",),
    "люди": ("people",), "людина": ("people",),
    "architecture": ("architecture",), "architectural": ("architecture",), "building": ("architecture", "urban"),
    "house": ("architecture",), "church": ("architecture",), "cathedral": ("architecture",),
    "monument": ("architecture",), "facade": ("architecture",), "будівля": ("architecture",), "будинок": ("architecture",),
    "landscape": ("landscape",), "nature": ("landscape",), "field": ("landscape",), "countryside": ("landscape",),
    "scenery": ("landscape",), "river": ("landscape",), "lake": ("landscape",), "steppe": ("landscape",),
    "forest": ("landscape",), "tree": ("landscape",), "grass": ("landscape",), "meadow": ("landscape",),
    "пейзаж": ("landscape",), "природа": ("landscape",),
    "street": ("street",), "road": ("street",), "sidewalk": ("street",), "вулиця": ("street",),
    "urban": ("urban",), "city": ("urban",), "cities": ("urban",), "town": ("urban",), "skyline": ("urban",),
    "downtown": ("urban",), "місто": ("urban",),
    "aerial": ("aerial", "drone"), "overhead": ("aerial", "drone"), "birdseye": ("aerial", "drone"),
    "drone": ("drone", "aerial"), "uav": ("drone", "aerial"), "дрон": ("drone", "aerial"),
    "infrastructure": ("infrastructure",), "bridge": ("infrastructure",), "dam": ("infrastructure",),
    "railway": ("infrastructure",), "rail": ("infrastructure",), "train": ("infrastructure",),
    "power": ("infrastructure",), "powerline": ("infrastructure",), "pipeline": ("infrastructure",), "міст": ("infrastructure",),
    "industrial": ("industrial",), "factory": ("industrial",), "factories": ("industrial",), "plant": ("industrial",),
    "industry": ("industrial",), "mine": ("industrial",), "завод": ("industrial",),
    "ruins": ("ruins",), "ruin": ("ruins",), "rubble": ("ruins",), "destroyed": ("ruins",), "destruction": ("ruins",),
    "damage": ("ruins",), "damaged": ("ruins",), "bombed": ("ruins",), "wreckage": ("ruins",), "руїни": ("ruins",),
    "reconstruction": ("reconstruction",), "rebuilding": ("reconstruction",), "rebuild": ("reconstruction",),
    "construction": ("reconstruction",), "repair": ("reconstruction",), "restoration": ("reconstruction",),
    "wildlife": ("wildlife",), "animal": ("wildlife",), "bird": ("wildlife",), "dog": ("wildlife",), "cat": ("wildlife",),
    "horse": ("wildlife",), "cow": ("wildlife",), "fish": ("wildlife",), "deer": ("wildlife",), "insect": ("wildlife",),
    "тварини": ("wildlife",), "птах": ("wildlife",),
    "graphic": ("graphic",), "text": ("graphic",), "map": ("graphic",), "chart": ("graphic",), "caption": ("graphic",),
    "infographic": ("graphic",), "logo": ("graphic",),
    "interior": ("interior",), "indoor": ("interior",), "indoors": ("interior",), "inside": ("interior",),
    "room": ("interior",), "office": ("interior",), "studio": ("interior",),
}


@dataclass(frozen=True)
class Term:
    raw: str
    categories: tuple[str, ...] = ()  # visual term: any of these labels
    pattern: str | None = None        # text term: Python regex (case-insensitive) over text + place names


def _singular(w: str) -> list[str]:
    out = [w]
    if len(w) > 4 and w.endswith("ies"):
        out.append(w[:-3] + "y")
    if len(w) > 3 and w.endswith("es"):
        out.append(w[:-2])
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        out.append(w[:-1])
    return out


def _place_spellings(phrase: str) -> tuple[str, ...] | None:
    for canonical, spellings in GAZETTEER.items():
        forms = {canonical.casefold(), *(s.rstrip("=") for s in spellings)}
        if phrase in forms:
            return tuple(sorted(forms, key=len, reverse=True))
    return None


def parse_query(text: str, labels: set[str] | None = None) -> list[Term]:
    """Split a free-text query into AND-ed terms. `labels` adds any category names in the index."""
    words = [w for w in re.findall(r"[\w'’-]+", text.casefold()) if w not in STOPWORDS]
    terms: list[Term] = []
    i = 0
    while i < len(words):
        # multi-word place names first ("chasiv yar", "velykyi luh")
        if i + 1 < len(words) and (sp := _place_spellings(f"{words[i]} {words[i + 1]}")):
            terms.append(_text_term(f"{words[i]} {words[i + 1]}", sp))
            i += 2
            continue
        w = words[i]
        i += 1
        cats: set[str] = set()
        for form in _singular(w):
            cats.update(VISUAL_SYNONYMS.get(form, ()))
            if labels and form in labels:
                cats.add(form)
        if cats:
            terms.append(Term(raw=w, categories=tuple(sorted(cats))))
        elif places := _place_spellings(w):
            terms.append(_text_term(w, places))
        else:
            terms.append(_text_term(w, (w,), _latin_to_cyrillic(w)))
    return terms


def phrase_pattern(text: str) -> str | None:
    """For multi-word queries: the exact phrase in video text also matches ("old town" in a title),
    even when a word in it is a visual term that the frame's categories don't carry."""
    words = re.findall(r"[\w'’-]+", text.casefold())
    if len(words) < 2:
        return None
    return r"(?<!\w)" + r"\W+".join(re.escape(w) for w in words) + r"(?!\w)"


def _text_term(raw: str, forms: tuple[str, ...], extra: str | None = None) -> Term:
    # Word-start match: "kyiv" matches "Kyiv's" but "art" doesn't match "start".
    alts = [re.escape(f) for f in forms] + ([extra] if extra else [])
    return Term(raw=raw, pattern=r"(?<!\w)(?:" + "|".join(alts) + ")")


# Latin -> Ukrainian/Russian Cyrillic, loose enough for common romanizations
# (national 2010 system, BGN, and informal), so "maniuk" finds "Манюк".
_MULTI = {"shch": "щ", "zgh": "зг", "zh": "ж", "kh": "х", "ts": "ц", "ch": "ч", "sh": "ш",
          "yu": "ю", "iu": "ю", "ya": "я", "ia": "я", "ye": "є", "ie": "є", "yi": "ї", "yo": "ьо|йо|ё"}
_SINGLE = {"a": "а", "b": "б", "v": "в", "h": "[гх]", "g": "[гґ]", "d": "д", "e": "[еєэ]", "z": "з",
           "y": "[иийы]", "i": "[іиїй]", "j": "[йж]", "k": "к", "l": "л", "m": "м", "n": "н", "o": "о",
           "p": "п", "r": "р", "s": "с", "t": "т", "u": "у", "f": "ф", "c": "[цкс]", "w": "в",
           "x": "кс", "q": "к", "'": "['’ьъ]?", "’": "['’ьъ]?"}
_VOWELS = set("aeiouy'’")


def _latin_to_cyrillic(word: str) -> str | None:
    """Regex matching plausible Cyrillic spellings of a Latin word, or None if not applicable.
    Only for words of 5+ letters: short words transliterate into prefixes of too many words."""
    if len(word) < 5 or not re.fullmatch(r"[a-z'’]+", word):
        return None
    if len(word) >= 6 and word[-1] in "aeiouy":
        word = word[:-1]  # Cyrillic case endings vary: "katastrofa" should find "катастрофи"
    out, i = [], 0
    while i < len(word):
        for n in (4, 3, 2):
            if (chunk := word[i:i + n]) in _MULTI:
                singles = "".join(_SINGLE[c] for c in chunk)
                out.append(f"(?:{_MULTI[chunk]}|{singles})")
                i += n
                break
        else:
            c = word[i]
            out.append(_SINGLE[c] + ("" if c in _VOWELS else "ь?"))
            i += 1
    return "".join(out)
