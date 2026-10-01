from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from image_evidence.config import DiscoveryConfig
from image_evidence.inference import infer
from image_evidence.schema import ClaimedLocation, SourceVideo
from image_evidence.scope import check_scope, mentioned_places


def _src(title="", description="", tags=(), published=datetime(2023, 5, 1, tzinfo=timezone.utc), **kw) -> SourceVideo:
    return SourceVideo(
        youtube_id="abcdefghijk", source_url="https://www.youtube.com/watch?v=abcdefghijk",
        title=title, description=description, tags=tuple(tags), published_at=published, retrieved_via=("test",), **kw,
    )


def test_config_refuses_dates_outside_hard_range():
    with pytest.raises(ValidationError):
        DiscoveryConfig(published_after=date(2021, 12, 31))
    with pytest.raises(ValidationError):
        DiscoveryConfig(published_before=date(2027, 1, 1))


@pytest.mark.parametrize("published", [datetime(2021, 12, 31, 23, tzinfo=timezone.utc), datetime(2027, 1, 1, tzinfo=timezone.utc)])
def test_publication_outside_range_is_rejected_even_if_about_ukraine(published):
    v = check_scope(_src("Kyiv drone footage", published=published))
    assert not v.accepted and "outside hard range" in v.reason


def test_non_ukraine_video_is_rejected():
    v = check_scope(_src("2023 Chico 4K Drone Stock Footage", "Drone footage of Chico, California", ["drone", "4k"]))
    assert not v.accepted and v.check.confidence == 0


def test_ukrainian_metadata_is_accepted_but_never_certain():
    v = check_scope(_src("Вадим Манюк про колишнє водосховище", "Каховського водосховища", ["війна в україні", "нікополь"]))
    assert v.accepted
    assert 0.5 <= v.check.confidence <= 0.95
    assert {s.kind for s in v.check.signals} >= {"gazetteer", "language"}


def test_language_alone_is_not_enough():
    v = check_scope(_src("Четверте літо: що змінилося", "", [], default_language="uk"))
    assert not v.accepted  # 0.4 < 0.5


def test_geotag_outside_ukraine_rejects():
    v = check_scope(_src("Kyiv", claimed_recording_location=ClaimedLocation(latitude=39.7, longitude=-121.8)))
    assert not v.accepted and "outside Ukraine" in v.reason


def test_gazetteer_avoids_common_word_false_positives():
    assert mentioned_places("кримінальна справа, рівень води, лиман, суми грошей, Bucharest") == []
    names = {n for n, _ in mentioned_places("у Криму, в Києві, біля Харкова")}
    assert names == {"Crimea", "Kyiv", "Kharkiv"}


def test_archival_hints_become_low_confidence_capture_dates():
    src = _src("Mariupol before the war: footage from 2019", "")
    inf = infer(src, [], check_scope(src).check)
    methods = {d.provenance.method: d for d in inf.capture_date}
    assert methods["source_text_year_mention"].earliest == date(2019, 1, 1)
    assert methods["source_text_archival_keyword"].latest == date(2021, 12, 31)
    assert all(d.confidence < 0.5 for m, d in methods.items() if m != "publication_upper_bound")
    # place mentions never get coordinates
    assert all(loc.latitude is None for loc in inf.locations)
