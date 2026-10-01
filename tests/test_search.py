import re

from image_evidence.search import parse_query

TITLE = "Яким став Великий Луг через 4 роки після катастрофи: Вадим Манюк про Київ і Нікополь"


def matches(term, text=TITLE):
    return re.search(term.pattern, text, re.IGNORECASE) is not None


def test_visual_words_map_to_categories():
    assert parse_query("person")[0].categories == ("people",)
    assert parse_query("People")[0].categories == ("people",)
    assert parse_query("landscapes")[0].categories == ("landscape",)
    assert parse_query("buildings")[0].categories == ("architecture", "urban")
    assert parse_query("animals")[0].categories == ("wildlife",)
    assert parse_query("destroyed")[0].categories == ("ruins",)


def test_labels_from_index_are_searchable():
    assert parse_query("graffiti", labels={"graffiti"})[0].categories == ("graffiti",)


def test_filler_words_dropped_and_terms_anded():
    terms = parse_query("drone footage of people in Kyiv")
    assert [t.raw for t in terms] == ["drone", "people", "kyiv"]


def test_places_match_any_spelling():
    assert matches(parse_query("kyiv")[0])
    assert matches(parse_query("Kiev")[0])
    assert matches(parse_query("nikopol")[0])
    assert matches(parse_query("velykyi luh")[0])


def test_latin_transliteration_and_case_endings():
    assert matches(parse_query("maniuk")[0])
    assert matches(parse_query("vadym")[0])
    assert matches(parse_query("katastrofa")[0])  # катастрофи


def test_word_start_only():
    assert not matches(parse_query("art")[0], "start of the war")
    assert matches(parse_query("war")[0], "war-damaged bridge")


def test_multiword_phrase_alternative():
    from image_evidence.search import phrase_pattern
    assert phrase_pattern("town") is None
    assert re.search(phrase_pattern("old town"), "Kyiv old-town walk", re.IGNORECASE)
