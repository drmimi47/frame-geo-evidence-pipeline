from datetime import date

import httpx

from image_evidence import focus
from image_evidence.config import CategorySpec, DiscoveryConfig, FocusSpec
from image_evidence.discovery import YouTubeClient, build_search_specs, discover

SPEC = FocusSpec(places=["Нікополь", "Марганець", "Енергодар", "Біленьке", "Водяне", "Кушугум"], radius_km=15,
                 topic_terms=["обстріл"])


def item(vid="abcdefghijk", title="", desc="", tags=(), loc=None, caption="false"):
    return {
        "id": vid,
        "snippet": {"publishedAt": "2023-06-01T12:00:00Z", "title": title, "description": desc, "tags": list(tags),
                    "channelId": "UC1", "channelTitle": "Канал"},
        "contentDetails": {"duration": "PT4M", "caption": caption},
        "status": {"license": "youtube", "privacyStatus": "public"},
        "recordingDetails": {"location": {"latitude": loc[0], "longitude": loc[1]}} if loc else {},
    }


def test_area_takes_the_namesake_by_the_other_places():
    a = focus.area(SPEC)
    oblasts = {p.name: p.oblast for p in a.anchors}
    assert oblasts["Bilenke"] == "Zaporizhzhia Oblast"  # not the Bilenke in Donetsk Oblast
    assert oblasts["Vodiane"] == "Zaporizhzhia Oblast"
    lat, lon, r = a.circle()
    assert 47 < lat < 48 and 34 < lon < 35.5 and r < 120


def test_rank_prefers_named_small_places_geotags_and_coordinates():
    named = focus.rank(item(title="Нікополь після обстрілу", desc="Марганець, Червоногригорівка"), SPEC)
    assert named.in_area and named.places[0] == "Nikopol"
    assert any("обстріл" in r for r in named.reasons)
    geotagged = focus.rank(item(title="Прогулянка", loc=(47.71, 35.21)), SPEC)
    assert geotagged.in_area and geotagged.score >= 4
    assert not geotagged.on_topic and named.on_topic  # a geotag is where the uploader is, not what the video shows
    coords = focus.rank(item(title="Дно", desc="47.5512, 34.4011"), SPEC)
    assert coords.in_area and "inside the area" in coords.reasons[-1]
    elsewhere = focus.rank(item(title="Харків з дрона", desc="Харків, Ізюм"), SPEC)
    assert not elsewhere.in_area and elsewhere.score <= 0


def test_a_name_shared_with_a_bigger_place_elsewhere_needs_context():
    # "Lviv" is also a village by the Dnipro; alone it means the city
    assert not focus.rank(item(title="Lviv drone"), SPEC).in_area
    assert not focus.rank(item(title="Покрова", desc="Свято Покрови у Львові"), SPEC).in_area


def test_focus_adds_geotag_searches_and_ranks_candidates():
    cfg = DiscoveryConfig(published_after=date(2022, 1, 1), published_before=date(2026, 12, 31), split_by_year=False,
                          extra_queries=["q"], focus=SPEC.model_copy(update={"geotagged_terms": ["", "дрон"]}))
    geo = [s for s in build_search_specs(cfg) if s.geo]
    assert [s.query for s in geo] == ["", "дрон"]

    items = {"aaaaaaaaaaa": item("aaaaaaaaaaa", title="Харків"), "bbbbbbbbbbb": item("bbbbbbbbbbb", title="Енергодар з дрона")}
    seen_q = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/search"):
            seen_q.append(request.url.params.get("q"))
            return httpx.Response(200, json={"items": [{"id": {"videoId": v}} for v in items]})
        return httpx.Response(200, json={"items": list(items.values())})

    cfg = cfg.model_copy(update={"max_videos_total": 10, "categories": [CategorySpec(name="c", terms=["t"])]})
    cands = discover(cfg, YouTubeClient("k", httpx.Client(transport=httpx.MockTransport(handler))), "run1")
    assert None in seen_q  # a geotag search sends no q at all
    assert [c.youtube_id for c in cands] == ["bbbbbbbbbbb", "aaaaaaaaaaa"]
    assert cands[0].rank.in_area and not cands[1].rank.in_area


def test_near_sort_uses_geotags_and_named_places_never_oblasts():
    from types import SimpleNamespace as NS

    from image_evidence.sorting import by_study_place

    nikopol = focus.study_places([SPEC])["Nikopol"][0]
    loc = lambda name, conf=0.3, lat=None, lon=None: NS(place_name=name, confidence=conf, latitude=lat, longitude=lon,
                                                       provenance=NS(method="source_text_gazetteer"))
    frame = lambda i, *locs: NS(frame_id=i, inferred=NS(locations=list(locs)),
                                source=NS(published_at=0, video_id="v"), frame=NS(timestamp_s=i))
    rows = by_study_place([
        frame(1, loc("Ukraine"), loc("Dnipropetrovsk Oblast")),
        frame(2, loc("Червоногригорівка")),               # ~11 km away
        frame(3, loc("Нікополь", 0.5, 47.57, 34.40)),      # geotag in town
        frame(4, loc("Kyiv")),
    ], nikopol, 15)
    assert [(f.frame_id, g) for f, g, _ in rows] == [(3, "at"), (2, "near"), (1, "elsewhere"), (4, "elsewhere")]
    assert "not a verified filming location" in rows[0][2]
