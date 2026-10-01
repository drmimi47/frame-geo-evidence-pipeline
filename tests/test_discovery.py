from datetime import date

import httpx

from image_evidence.config import CategorySpec, DiscoveryConfig, LocationSpec
from image_evidence.discovery import YouTubeClient, build_search_specs, discover, parse_iso_duration, source_from_api

API_ITEM = {
    "id": "abcdefghijk",
    "snippet": {
        "publishedAt": "2023-06-01T12:00:00Z",
        "title": "Drone over the old town of Kyiv",
        "description": "4K drone flight over Kyiv, Ukraine",
        "channelId": "UC1",
        "channelTitle": "Some Channel",
        "tags": ["drone", "city"],
        "thumbnails": {"high": {"url": "https://i.ytimg.com/vi/abcdefghijk/hqdefault.jpg"}},
    },
    "contentDetails": {"duration": "PT4M13S"},
    "status": {"license": "creativeCommon", "privacyStatus": "public", "embeddable": True},
    "statistics": {"viewCount": "1234"},
    "recordingDetails": {"recordingDate": "2023-05-20T00:00:00Z", "location": {"latitude": 50.1, "longitude": 30.2}},
}


def test_search_specs_expand_locations_terms_and_years():
    cfg = DiscoveryConfig(
        published_after=date(2022, 1, 1),
        published_before=date(2024, 12, 31),
        locations=[LocationSpec(name="Kyiv"), LocationSpec(name="Lviv")],
        categories=[CategorySpec(name="drone", terms=["drone footage", "aerial"])],
        extra_queries=["literal query"],
    )
    specs = build_search_specs(cfg)
    assert len(specs) == 3 * (2 * 2 + 1)
    assert {s.published_after.year for s in specs} == {2022, 2023, 2024}
    assert any(s.query == "Kyiv drone footage" and s.location == "Kyiv" and s.category == "drone" for s in specs)
    assert all(s.geo is None for s in specs)


def test_parse_iso_duration():
    assert parse_iso_duration("PT4M13S") == 253
    assert parse_iso_duration("PT1H") == 3600
    assert parse_iso_duration("P1DT2S") == 86402
    assert parse_iso_duration(None) is None


def test_source_from_api_keeps_claims_separate_from_publication():
    s = source_from_api(API_ITEM)
    assert s.published_at.isoformat() == "2023-06-01T12:00:00+00:00"
    assert s.claimed_recording_date.date() == date(2023, 5, 20)
    assert s.claimed_recording_location.latitude == 50.1
    assert s.license == "creativeCommon"
    assert s.duration_s == 253
    assert s.view_count == 1234


def test_discover_dedupes_and_records_every_context():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path.endswith("/search"):
            assert request.url.params["videoLicense"] == "creativeCommon"
            return httpx.Response(200, json={"items": [{"id": {"videoId": "abcdefghijk"}}]})
        return httpx.Response(200, json={"items": [API_ITEM]})

    client = YouTubeClient("k", httpx.Client(transport=httpx.MockTransport(handler)))
    cfg = DiscoveryConfig(
        published_after=date(2022, 1, 1),
        published_before=date(2023, 12, 31),
        categories=[CategorySpec(name="drone", terms=["drone"])],
    )
    cands = discover(cfg, client, "run1")
    assert len(cands) == 1
    assert [c.published_after.year for c in cands[0].contexts] == [2022, 2023]
    assert cands[0].api_item["id"] == "abcdefghijk"
    assert calls.count("/youtube/v3/videos") == 1
