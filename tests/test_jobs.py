import json
from datetime import date, datetime, timezone

import httpx
import pytest
from pydantic import ValidationError

from image_evidence.config import DiscoveryConfig
from image_evidence.jobs import (JobRequest, list_libraries, next_folder, plain_queries, plan_with_llm, redact, rename_folder,
                                 resolve_folder, youtube_ids)
from image_evidence.scope import SCOPE_FILE
from image_evidence.layout import write_json
from image_evidence.schema import ClaimedLocation, SourceVideo
from image_evidence.scope import UKRAINE, Scope, check_scope, library_scope

POLAND = Scope.from_json({"name": "Poland", "start": "2015-01-01", "end": "2026-12-31",
                          "spellings": ["polska", "kraków", "krakow", "warszaw"], "bbox": [14.1, 49.0, 24.2, 54.9], "language": "pl"})


def _src(title="", published=datetime(2018, 5, 1, tzinfo=timezone.utc), **kw) -> SourceVideo:
    return SourceVideo(youtube_id="abcdefghijk", source_url="https://www.youtube.com/watch?v=abcdefghijk", title=title,
                       description="", tags=(), published_at=published, retrieved_via=("test",), **kw)


def _req(**kw) -> JobRequest:
    return JobRequest.parse({"prompt": "drone footage", "youtube_key": "yt-test", **kw})


def test_another_scope_gates_on_its_own_place_and_dates():
    assert check_scope(_src("Kraków z drona 4K"), scope=POLAND).accepted
    assert check_scope(_src("Kraków z drona 4K"), scope=POLAND).check.scope_name == "Poland"
    assert not check_scope(_src("Kyiv drone footage"), scope=POLAND).accepted
    assert not check_scope(_src("Kraków", published=datetime(2014, 6, 1, tzinfo=timezone.utc)), scope=POLAND).accepted
    far = ClaimedLocation(latitude=50.45, longitude=30.52)  # Kyiv
    assert "outside Poland" in check_scope(_src("Kraków", claimed_recording_location=far), scope=POLAND).reason
    # and the main library still refuses a Polish video published in its years
    assert not check_scope(_src("Kraków z drona", published=datetime(2023, 5, 1, tzinfo=timezone.utc))).accepted


def test_library_scope_is_ukraine_unless_the_library_has_its_own(tmp_path):
    assert library_scope(tmp_path) is UKRAINE
    write_json(tmp_path / "scope.json", {"name": "Ukraine", "start": "2014-01-01", "end": "2026-12-31"})
    sc = library_scope(tmp_path)
    assert sc.start == date(2014, 1, 1) and sc.bbox == UKRAINE.bbox
    assert {n for n, _ in sc.places("у Києві")} == {"Kyiv"}  # Ukraine over other years keeps the curated gazetteer


def test_a_new_folder_takes_the_requests_place_over_whole_years(tmp_path):
    main = tmp_path / "library"
    root, sc, new, title = resolve_folder(main, _req(start="2014-02-20"))
    assert root == tmp_path / "libraries" / "folder-1" and new and title == "Evidence folder 1"
    assert sc.is_ukraine and sc.start == date(2014, 1, 1) and sc.end == date(2026, 12, 31)
    root, sc, _, title = resolve_folder(main, _req(country="Poland", start="2015-06-01", end="2020-12-31", folder_name=" Wisła  dam "))
    assert sc.name == "Poland" and sc.start == date(2015, 1, 1) and title == "Wisła dam"


def test_an_existing_folder_only_takes_its_own_place_and_years(tmp_path):
    main = tmp_path / "library"
    assert resolve_folder(main, _req(folder="", start="2023-01-01", end="2024-12-31"))[:3] == (main, UKRAINE, False)
    with pytest.raises(ValueError, match="keeps only Ukraine"):
        resolve_folder(main, _req(folder="", country="Poland"))
    with pytest.raises(ValueError, match="2022–2026"):
        resolve_folder(main, _req(folder="", start="2014-01-01"))  # the main library never widens
    with pytest.raises(ValueError, match="no longer exists"):
        resolve_folder(main, _req(folder="folder-9"))


def test_folders_are_listed_numbered_and_renamed(tmp_path):
    main = tmp_path / "library"
    for n in (1, 2, 10):
        (tmp_path / "libraries" / f"folder-{n}").mkdir(parents=True)
        write_json(tmp_path / "libraries" / f"folder-{n}" / SCOPE_FILE, POLAND.to_json())
    assert [x["slug"] for x in list_libraries(main)] == ["", "folder-1", "folder-2", "folder-10"]
    assert next_folder(main) == ("folder-11", "Evidence folder 11")
    assert rename_folder(main, "folder-2", "  Kakhovka   reservoir ") == "Kakhovka reservoir"
    assert {x["slug"]: x["title"] for x in list_libraries(main)}["folder-2"] == "Kakhovka reservoir"
    assert list_libraries(main)[0]["title"] == "Ukraine collection"
    with pytest.raises(ValueError):
        rename_folder(main, "folder-2", "  ")


def test_discovery_dates_are_checked_against_the_library_scope():
    with pytest.raises(ValidationError):
        DiscoveryConfig(published_after=date(2015, 1, 1))
    DiscoveryConfig.model_validate({"published_after": "2015-01-01"}, context={"scope": POLAND})


def test_request_parsing():
    assert youtube_ids("https://youtu.be/_8YUZVFXzWo, https://www.youtube.com/watch?v=abcdefghijk&t=3 _8YUZVFXzWo") == \
        ["_8YUZVFXzWo", "abcdefghijk"]
    with pytest.raises(ValueError):
        youtube_ids("https://example.com/video")
    with pytest.raises(ValueError):
        JobRequest.parse({})
    with pytest.raises(ValueError, match="YouTube Data API key"):
        JobRequest.parse({"urls": "abcdefghijk"})  # no key of the server's own: the page must send one
    r = JobRequest.parse({"urls": "abcdefghijk", "country": "україна", "max_videos": 500, "youtube_key": "yt-test"})
    assert r.country == "Ukraine" and r.max_videos == 25 and r.start == date(2022, 1, 1) and r.end == date(2026, 12, 31)
    assert "secret" not in repr(JobRequest.parse({"urls": "abcdefghijk", "youtube_key": "secret", "llm_key": "secret"}))


def test_without_an_llm_the_prompt_is_searched_as_typed():
    assert plain_queries(_req()) == ["drone footage Ukraine"]
    assert plain_queries(_req(places="Nikopol, Enerhodar")) == ["drone footage Nikopol", "drone footage Enerhodar"]


def test_llm_plan_is_parsed_and_the_token_only_goes_in_the_header():
    seen = {}

    def handle(request: httpx.Request) -> httpx.Response:
        seen["key"], seen["body"] = request.headers["x-api-key"], json.loads(request.content)
        plan = {"queries": ["Kraków z drona"], "relevance_language": "pl", "spellings": ["polska"], "bbox": [14, 49, 24, 55], "language": "pl"}
        return httpx.Response(200, json={"content": [{"type": "text", "text": "Here:\n" + json.dumps(plan)}]})

    req = _req(country="Poland", llm_key="sk-test")
    plan = plan_with_llm(req, True, httpx.Client(transport=httpx.MockTransport(handle)))
    assert plan["queries"] == ["Kraków z drona"] and seen["key"] == "sk-test"
    assert "sk-test" not in json.dumps(seen["body"]) and "spellings" in seen["body"]["messages"][0]["content"]


def test_tokens_are_blanked_out_of_job_logs():
    assert redact("GET ...&key=AIzaSECRET failed", ["AIzaSECRET", ""]) == "GET ...&key=••• failed"
