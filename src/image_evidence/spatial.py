"""Words that describe the land in speech: water, terrain, built features, directions and distances.

Used to weight the subtitles view (a tier below place names), never as location evidence. A short
curated list of Ukrainian and Russian stems, each allowed only its own case endings, so "міст" (bridge)
and "мосту" match but "містить" (contains) doesn't. Words so common they would mark half of every
transcript ("вода", "місце", "тут") are left out on purpose: when a word lights up too much, remove
it here rather than loosening the endings.

The English row of the subtitles (uploader's subtitles or a local translation) gets the same weighting
from a parallel English list (`english=True`), for reading only.
"""

from __future__ import annotations

import re

# noun endings (Ukrainian + Russian cases, singular and plural)
N = r"(?:а|я|у|ю|і|и|ї|е|о|ом|ем|ою|ею|ой|ей|ам|ям|ах|ях|ами|ями|ів|ей|ові|еві|ы|ь)?"
# adjective endings
A = r"(?:ий|ій|а|я|е|є|ого|ього|ому|ьому|ім|ій|ої|ою|і|их|им|ими|ый|ой|ая|ое|ые|ую|ом|ых|ым|ыми|ее|ие|яя|ье)"

_PATTERNS = [
    # water
    # (not "рік"/"року": year; not "дні": days; not "канал": mostly "subscribe to the channel")
    r"річк" + N, r"річок", r"рік[аиуі]", r"ріці", r"рікою", r"рек[аиуеі]", r"рекой", r"берег" + N, r"березі", r"берегов" + A,
    r"остр[іо]в", r"остров" + N, r"протока?", r"проток" + N, r"затока?", r"заток" + N, r"затоці",
    r"водосховищ" + N, r"водохранилищ" + N, r"лиман" + N, r"озер" + N, r"озеро", r"русл" + N, r"плавн" + N,
    r"болот" + N, r"гирл" + N, r"заплав" + N, r"пляж" + N, r"узбережж" + N, r"течі[їєю]", r"течія",
    r"течени" + N, r"дно", r"дна", r"дном",
    # terrain
    r"балк" + N, r"балок", r"яр", r"яру", r"ярі", r"яри", r"пагорб" + N, r"схил" + N, r"степ" + N, r"степов" + A,
    r"ліс", r"лісу", r"лісі", r"лісом", r"ліси", r"лісів", r"лісах", r"лісов" + A, r"лес", r"леса", r"лесу", r"лесом",
    r"гай", r"гаю", r"луг", r"лугу", r"лузі", r"луки", r"долин" + N, r"пол[еяіюь]", r"полем", r"полях", r"пісок",
    r"піск" + N, r"піщан" + A, r"песок", r"песк" + N, r"круч" + N, r"урвищ" + N, r"дюн" + N, r"рівнин" + N,
    # built
    r"міст", r"мосту", r"мості", r"мостом", r"мости", r"мостів", r"мост", r"моста", r"мосте", r"мостов" + A,
    r"дамб" + N, r"гребл" + N, r"плотин" + N, r"дорог[аиуіе]", r"дорогою", r"дорогам?и?", r"дорогах", r"доріг", r"дорожн" + A, r"трас" + N, r"вулиц" + N,
    r"улиц" + N, r"проспект" + N, r"набережн" + A, r"причал" + N, r"пристан" + N, r"порт" + N, r"гес", r"аес",
    r"шлюз" + N, r"сел[оаіу]", r"селом", r"селах", r"сіл", r"селищ" + N, r"поселок", r"поселк" + N, r"поселен" + N, r"міст[аоі]", r"містом", r"город" + N,
    r"околиц" + N, r"район" + N, r"завод" + N, r"вишк" + N, r"опор" + N, r"руїн" + N, r"руин" + N,
    # directions and relative position
    r"північ", r"півночі", r"північн" + A, r"північніше", r"південь", r"південніше", r"східніше", r"західніше", r"півдня", r"півдні", r"південн" + A, r"схід", r"сходу",
    r"сході", r"східн" + A, r"західн" + A, r"север" + N, r"северн" + A, r"юг", r"юга", r"юге", r"южн" + A,
    r"восток" + N, r"восточн" + A, r"запад" + N, r"западн" + A, r"лів" + A, r"ліворуч", r"праворуч",
    r"правобережж" + N, r"лівобережж" + N, r"лев" + A, r"навпроти", r"напротив", r"вгору", r"униз", r"вниз",
    # distances and areas
    r"метр" + N, r"метрів", r"кілометр" + N, r"кілометрів", r"километр" + N, r"км", r"гектар" + N, r"гектарів",
]
_WORD = re.compile("|".join(f"(?:{p})" for p in _PATTERNS))

# English, for the English row. Left out as too common or ambiguous: "water", "left"/"right", "channel"
# (subscribe), "bottom", "current", "plain", "bed", "plant", "lock", "mouth".
_EN = [
    # water
    r"rivers?", r"riverbanks?", r"riverbeds?", r"banks?", r"shores?", r"shoreline", r"coasts?", r"coastline",
    r"islands?", r"islets?", r"straits?", r"bays?", r"inlets?", r"reservoirs?", r"lakes?", r"estuar(?:y|ies)",
    r"floodplains?", r"swamps?", r"marsh(?:es)?", r"bogs?", r"wetlands?", r"beach(?:es)?", r"seabed",
    r"tributar(?:y|ies)", r"backwaters?", r"creeks?", r"ponds?",
    # terrain
    r"ravines?", r"gull(?:y|ies)", r"hills?", r"hillsides?", r"slopes?", r"steppes?", r"forests?", r"woods",
    r"woodlands?", r"groves?", r"meadows?", r"valle(?:y|ys)", r"fields?", r"sands?", r"sandy", r"cliffs?",
    r"dunes?", r"plains", r"terrain", r"landscape",
    # built
    r"bridges?", r"dams?", r"roads?", r"highways?", r"streets?", r"avenues?", r"embankments?", r"piers?",
    r"ports?", r"harbou?rs?", r"villages?", r"towns?", r"city", r"cities", r"settlements?", r"outskirts",
    r"districts?", r"factor(?:y|ies)", r"towers?", r"pylons?", r"ruins?",
    # directions and relative position
    r"north(?:ern|ward|wards|east|west)?", r"south(?:ern|ward|wards|east|west)?", r"east(?:ern|ward|wards)?",
    r"west(?:ern|ward|wards)?", r"upstream", r"downstream", r"uphill", r"downhill", r"opposite",
    # distances and areas
    r"met(?:er|re)s?", r"kilomet(?:er|re)s?", r"km", r"hectares?", r"miles?",
]
_WORD_EN = re.compile("|".join(f"(?:{p})" for p in _EN))
_EDGE = re.compile(r"^[^\w]+|[^\w']+$")
_NUMBER = re.compile(r"^\d+([.,]\d+)?$|^(один|два|дві|три|чотири|п'ять|шість|сім|вісім|дев'ять|десять|сто|двісті|триста|сотні|тисяч\w*|кілька|декілька|пару)$")
_NUMBER_EN = re.compile(r"^\d+([.,]\d+)?$|^(one|two|three|four|five|six|seven|eight|nine|ten|twenty|thirty|fifty|hundreds?|thousands?|several|a few|few)$")
UNITS = re.compile(r"^(метр|кілометр|километр|км|гектар)|^(м|га)$")  # "м", "га" only right after a number
UNITS_EN = re.compile(r"^(met(er|re)|kilomet(er|re)|km|hectare|mile)|^(m|ha)$")


def is_spatial(word: str, english: bool = False) -> bool:
    w = _EDGE.sub("", word.lower().replace("’", "'"))
    return bool(w) and (_WORD_EN if english else _WORD).fullmatch(w) is not None


def is_number(word: str, english: bool = False) -> bool:
    return (_NUMBER_EN if english else _NUMBER).match(_EDGE.sub("", word.lower())) is not None


def is_unit(word: str, english: bool = False) -> bool:
    return (UNITS_EN if english else UNITS).match(_EDGE.sub("", word.lower())) is not None
