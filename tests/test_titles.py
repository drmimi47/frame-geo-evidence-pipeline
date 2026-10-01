from image_evidence.discovery import source_from_api
from image_evidence.schema import VideoRecord, video_id_for
from image_evidence.service import english_title

from .test_discovery import API_ITEM


def video(localizations):
    item = {**API_ITEM, "localizations": localizations}
    s = source_from_api(item)
    return VideoRecord(video_id=video_id_for(s.youtube_id), source=s)


def test_uploader_english_title_is_used():
    v = video({"uk": {"title": API_ITEM["snippet"]["title"]}, "en-US": {"title": "Kyiv from above"}})
    assert v.source.title_localizations["en-US"] == "Kyiv from above"
    assert english_title(v) == {"text": "Kyiv from above", "language": "en-US", "source": "uploader"}


def test_plain_en_preferred_over_regional():
    v = video({"en-AU": {"title": "A"}, "en": {"title": "B"}})
    assert english_title(v)["text"] == "B"


def test_no_english_title_falls_back_to_original():
    v = video({"uk": {"title": "x"}, "es": {"title": "Kiev desde arriba"}})
    t = english_title(v)
    assert t["source"] == "original" and t["text"] == API_ITEM["snippet"]["title"]
