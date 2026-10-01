from datetime import datetime, timezone

from image_evidence.discovery import source_from_api
from image_evidence.geo_text import frame_clues, parse_chapters, video_clues
from image_evidence.inference import CONF_GEOTAG_FAR, CONF_UPLOADER_GEOTAG, infer_locations
from image_evidence.places import find_places
from image_evidence.schema import (
    DerivedVisual, FrameCore, FrameFiles, FrameQuality, FrameRecord, FrameSourceLink, Inferred, OcrLine, OcrResult,
    PipelineInfo, Provenance, VideoRecord, video_id_for,
)

from .test_discovery import API_ITEM

DESCRIPTION = """Репортаж з Донеччини.

00:00 Вступ
02:10 Руїни Часового Яру
05:00 Дорога на Костянтинівку
"""


def video(description=DESCRIPTION, channel="Суспільне Донбас", geotag=None):
    item = {**API_ITEM, "snippet": {**API_ITEM["snippet"], "title": "Фронтова дорога", "description": description,
                                    "channelTitle": channel, "tags": []}}
    item["recordingDetails"] = {"location": geotag} if geotag else {}
    s = source_from_api(item)
    return VideoRecord(video_id=video_id_for(s.youtube_id), source=s)


def frame(t, lines=()):
    v = video()
    ocr = OcrResult(lines=[OcrLine(text=x, confidence=1.0, box=(0, 0, 1, 1)) for x in lines], provenance=Provenance(method="test"))
    return FrameRecord(
        frame_id=f"f{int(t * 10)}",
        source=FrameSourceLink(video_id=v.video_id, youtube_id=v.source.youtube_id, source_url=v.source.source_url,
                               timestamped_url=v.source.source_url, published_at=datetime(2024, 6, 1, tzinfo=timezone.utc)),
        frame=FrameCore(timestamp_s=t, frame_number=int(t * 25), fps=25, width=1920, height=1080, selection="interval",
                        original_format="png", sha256="x", files=FrameFiles(original="a", web="b", thumb="c")),
        derived=DerivedVisual(quality=FrameQuality(sharpness=1, brightness=1, contrast=1, dhash="0"), ocr=ocr),
        inferred=Inferred(),
        pipeline=PipelineInfo(version="t", config_digest="t"),
    )


def names(locs, method):
    return {loc.place_name for loc in locs if loc.provenance.method == method}


def test_parse_chapters():
    ch = parse_chapters(DESCRIPTION, 600)
    assert [(a, b) for a, b, _ in ch] == [(0, 130), (130, 300), (300, 600)]
    assert parse_chapters("no chapters here\n1:00 only one", 600) == []


def test_matcher_handles_case_endings_and_blocks_common_words():
    assert {"Bakhmut", "Mariupol"} <= {m.name for m in find_places("у Бахмуті та біля Маріуполя")}
    assert {m.name for m in find_places("Часів-Яр")} == {"Chasiv Yar"}
    assert find_places("мирне життя") == []                       # common word, lower case
    assert find_places("їдемо до вугледара")[0].name == "Vuhledar"  # big place in lower-case speech


def test_chapter_and_ocr_clues_are_frame_specific():
    fr = [frame(10), frame(200, ["Часів Яр 2021"]), frame(400)]
    vc = video_clues(video(), fr, captions=None)
    early, mid, late = (frame_clues(vc, f) for f in fr)
    assert names(early[0], "frame_onscreen_text") == set()
    assert "Chasiv Yar" in names(mid[0], "frame_onscreen_text")
    assert "Kostyantynivka" in names(late[0], "description_chapter")  # "Костянтинівку", accusative
    assert [d.earliest.year for d in mid[1] if d.provenance.method == "frame_onscreen_year"] == [2021]


def test_watermarks_are_ignored():
    fr = [frame(t, ["Суспільне Дніпро", "Дніпро"]) for t in range(0, 60, 10)]
    vc = video_clues(video(channel="Суспільне Дніпро"), fr, captions=None)
    assert names(frame_clues(vc, fr[0])[0], "frame_onscreen_text") == set()


def test_speech_near_frame_only():
    caps = {"kind": "auto", "cues": [[100, 104, "ми зараз у покровську"], [400, 403, "а це вже краматорськ"]]}
    fr = [frame(110), frame(250)]
    vc = video_clues(video(), fr, caps)
    near = frame_clues(vc, fr[0])[0]
    assert "Pokrovsk" in names(near, "speech_captions")
    assert names(frame_clues(vc, fr[1])[0], "speech_captions") == set()


def test_geotag_far_from_named_places_is_downweighted():
    # Kyiv-titled video geotagged in Lviv (~470 km away)
    far = infer_locations(video(description="Київ", geotag={"latitude": 49.84, "longitude": 24.03}).source, [])
    near = infer_locations(video(description="Київ", geotag={"latitude": 50.45, "longitude": 30.52}).source, [])
    geo = lambda locs: next(l for l in locs if l.provenance.method == "youtube_recording_details_geotag")
    assert geo(far).confidence == CONF_GEOTAG_FAR and "km from the nearest place" in geo(far).provenance.evidence
    assert geo(near).confidence == CONF_UPLOADER_GEOTAG


def test_onscreen_month_label_dates_the_shot():
    fr = [frame(30, ["Запорізька обл", "вересень 2023"])]
    vc = video_clues(video(), fr, captions=None)
    locs, dates = frame_clues(vc, fr[0])
    assert "Zaporizhzhia Oblast" in names(locs, "frame_onscreen_text")
    d = next(d for d in dates if d.provenance.method == "frame_onscreen_date")
    assert (d.earliest.isoformat(), d.latest.isoformat()) == ("2023-09-01", "2023-09-30")


def test_captions_prefer_original_and_keep_uploader_english(monkeypatch):
    from image_evidence import geo_text

    monkeypatch.setattr(geo_text, "_json3", lambda formats: ([[0.0, 2.0, formats[0]["url"]]], [[0.0]]))
    fmt = lambda name: [{"ext": "json3", "url": name}]
    info = {"subtitles": {"en-GB": fmt("manual en")},
            "automatic_captions": {"uk-orig": fmt("auto uk"), "en": fmt("youtube translation")}}
    caps = geo_text.fetch_captions(info, ["uk", "ru", "en"])
    assert (caps["lang"], caps["kind"], caps["cues"][0][2]) == ("uk", "auto", "auto uk")
    assert caps["english"]["lang"] == "en-GB" and caps["english"]["cues"] == [[0.0, 2.0, "manual en"]]
    # YouTube's own auto-translation is never used (its downloads are rate-limited)
    info["subtitles"] = {}
    assert geo_text.fetch_captions(info, ["uk"])["english"] is None
    # only English subtitles by the uploader: they are the original
    only_en = geo_text.fetch_captions({"subtitles": {"en": fmt("manual en")}}, ["uk", "en"])
    assert (only_en["lang"], only_en["english"]) == ("en", None)


def test_json3_times_every_word(monkeypatch):
    from image_evidence import geo_text

    events = {"events": [
        {"tStartMs": 1000, "dDurationMs": 3000, "segs": [{"utf8": "їдемо"}, {"utf8": " до", "tOffsetMs": 500},
                                                          {"utf8": " Бахмута", "tOffsetMs": 900}]},
        {"tStartMs": 2000, "dDurationMs": 100, "aAppend": 1, "segs": [{"utf8": "\n"}]},
        {"tStartMs": 5000, "dDurationMs": 2000, "segs": [{"utf8": "manual line of four"}]},
    ]}
    monkeypatch.setattr(geo_text.httpx, "get", lambda url, timeout: type("R", (), {"json": lambda self: events})())
    cues, times = geo_text._json3([{"ext": "json3", "url": "u"}])
    assert cues == [[1.0, 4.0, "їдемо до Бахмута"], [5.0, 7.0, "manual line of four"]]
    assert times == [[1.0, 1.5, 1.9], [5.0, 5.5, 6.0, 6.5]]


def test_paragraphs_join_cues_and_break_at_pauses():
    from image_evidence.geo_text import paragraphs

    cues = [[0, 3, "їдемо"], [2, 5, "до  Бахмута"], [4, 8, "зараз"], [30, 33, "тиша"], [34, 36, "далі"]]
    assert paragraphs(cues) == [[0, 8, "їдемо до Бахмута зараз"], [30, 36, "тиша далі"]]
    long = [[t, t + 2, "слово"] for t in range(0, 60, 2)]
    assert all(p[0] - q[0] >= 20 for q, p in zip(paragraphs(long), paragraphs(long)[1:]))


def test_subtitles_place_words_in_time_and_flag_places():
    from image_evidence.geo_text import subtitles

    caps = {"lang": "uk", "kind": "auto", "cues": [[0, 3, "ми їдемо"], [2, 5, "до Бахмута"], [40, 42, "[музика]"]],
            "word_times": [[0.0, 0.8], [2.0, 2.4], [40.0]]}
    en = {"lang": "en", "kind": "machine", "model": "m", "cues": [[0, 4, "we drive to Bakhmut"]]}
    d = subtitles(video(), caps, en)
    assert d["words"] == [[0.0, "ми", 0], [0.8, "їдемо", 0], [2.0, "до", 0], [2.4, "Бахмута", 1], [40.0, "[музика]", 2]]
    assert d["en"] == [[0.0, "we", 0], [1.0, "drive", 0], [2.0, "to", 0], [3.0, "Bakhmut", 1]]  # spread over the phrase
    assert d["english"] == {"lang": "en", "kind": "machine", "model": "m"}
    # stored before word times were kept: spread over each cue
    old = subtitles(video(), {**caps, "word_times": None}, None)
    assert [t for t, _, _ in old["words"]][:3] == [0.0, 1.0, 2.0]
    assert subtitles(video(), None, None)["words"] == []


def test_translation_goes_sentence_by_sentence():
    from image_evidence.translate import PIECE_WORDS, _pieces

    assert _pieces("Перше речення. Друге? Третє!") == ["Перше речення.", "Друге?", "Третє!"]
    run = " ".join(["слово"] * (PIECE_WORDS * 3))  # auto captions: no punctuation
    assert [len(p.split()) for p in _pieces(run)] == [PIECE_WORDS] * 3


def test_spatial_words_are_marked_with_their_case_endings():
    from image_evidence.geo_text import subtitles
    from image_evidence.spatial import is_spatial

    assert all(is_spatial(w) for w in "березі річки мосту лівому водосховища плавнях півночі км".split())
    # common words that only look like it: year, days, "contains", the YouTube channel, "expensive"
    assert not any(is_spatial(w) for w in "рік року дні містить канал дорого вода тут".split())
    caps = {"lang": "uk", "kind": "auto", "cues": [[0, 5, "за двісті метрів на лівому березі вода"]],
            "word_times": [[0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5][:7]]}
    flags = {w: f for _, w, f in subtitles(video(), caps, None)["words"]}
    assert flags == {"за": 0, "двісті": 3, "метрів": 3, "на": 0, "лівому": 3, "березі": 3, "вода": 0}
    caps = {"lang": "uk", "kind": "auto", "cues": [[0, 3, "ще 5 м і м"]], "word_times": [[0, 1, 2, 2.5, 2.8]]}
    assert [f for _, _, f in subtitles(video(), caps, None)["words"]] == [0, 3, 3, 0, 0]  # a bare "м" is not a unit


def test_english_row_gets_the_same_emphasis_but_never_adds_a_place():
    from image_evidence.geo_text import subtitles
    from image_evidence.spatial import is_spatial

    assert all(is_spatial(w, english=True) for w in "river bank, reservoir islands north kilometres".split())
    assert not any(is_spatial(w, english=True) for w in "water left right channel bottom current".split())
    caps = {"lang": "uk", "kind": "auto", "cues": [[0, 4, "біля Бахмута"]], "word_times": [[0.0, 1.0]]}
    en = {"lang": "en", "kind": "machine", "model": "m",
          "cues": [[0, 4, "near Bakhmut, five kilometres from the river, not Odesa"]]}
    flags = {w: f for _, w, f in subtitles(video(), caps, en)["en"]}
    # Bakhmut is said in the original; Odesa only appears in the translation, so it isn't marked
    en["cues"] = [[0, 4, "the Dnieper near Bakhmut"]]
    assert [f for _, _, f in subtitles(video(), caps, en)["en"]] == [0, 0, 0, 1]  # Dnipro isn't said
    caps["cues"] = [[0, 4, "біля Дніпра"]]
    assert [f for _, _, f in subtitles(video(), caps, en)["en"]] == [0, 1, 0, 0]  # the exonym, once it is
    en["cues"] = [[0, 4, "near Bakhmut, five kilometres from the river, not Odesa"]]
    caps["cues"] = [[0, 4, "біля Бахмута"]]
    flags = {w: f for _, w, f in subtitles(video(), caps, en)["en"]}
    assert flags == {"near": 0, "Bakhmut,": 1, "five": 3, "kilometres": 3, "from": 0, "the": 0, "river,": 3,
                     "not": 0, "Odesa": 0}
