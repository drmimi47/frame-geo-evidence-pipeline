"""Offline end-to-end: pipeline -> JSON sidecars -> SQLite -> service, with YouTube calls stubbed."""

import json
import shutil
import sqlite3

import pytest

from image_evidence import acquisition
from image_evidence.config import Config
from image_evidence.layout import Library
from image_evidence.pipeline import Pipeline, reindex, slim
from image_evidence.schema import Acquisition, DiscoveryContext, MediaFile
from image_evidence.service import EvidenceService
from image_evidence.store import SQLiteRepository

from .test_discovery import API_ITEM

YID = API_ITEM["id"]


@pytest.fixture
def pipeline(tmp_path, synthetic_video, monkeypatch):
    info = {"id": YID, "availability": "public", "age_limit": 0, "duration": 18}
    monkeypatch.setattr(acquisition, "fetch_info", lambda yid: info)
    monkeypatch.setattr(acquisition, "save_youtube_thumbnails", lambda s, d, lib: {})

    def fake_download(cfg, dirs, lib, yid):
        dest = dirs.media / f"{yid}.mp4"
        shutil.copy(synthetic_video, dest)
        return Acquisition(status="downloaded", policy=cfg.policy, media=MediaFile(path=lib.rel(dest), sha256="x")), dest

    monkeypatch.setattr(acquisition, "download", fake_download)
    cfg = Config(library_dir=tmp_path / "lib")
    cfg.extraction.interval_s = 4
    cfg.classification.backend = "none"
    return Pipeline(cfg)


def test_ingest_produces_linked_frames(pipeline):
    ctx = DiscoveryContext(run_id="r", query="Kyiv drone", location="Kyiv", category="drone", rank=0)
    result = pipeline.ingest(YID, api_item=API_ITEM, contexts=[ctx])
    assert result.status == "processed" and result.frames >= 3

    lib = pipeline.lib
    dirs = lib.video(YID)
    video = json.loads(dirs.video_json.read_text())
    assert video["source"]["published_at"] == "2023-06-01T12:00:00Z"
    assert video["source"]["retrieved_via"] == ["youtube_data_api_v3", "yt-dlp"]
    assert (dirs.raw / "youtube_api.json").exists() and (dirs.raw / "ytdlp_info.json").exists()

    metas = sorted(dirs.meta.glob("*.json"))
    assert len(metas) == result.frames == len(video["frame_ids"])
    rec = json.loads(metas[1].read_text())
    assert rec["source"]["youtube_id"] == YID
    assert rec["source"]["timestamped_url"].endswith(f"&t={int(rec['frame']['timestamp_s'])}s")
    for key in ("web", "thumb"):
        assert lib.abs(rec["frame"]["files"][key]).exists()
    # by default neither the video nor full-resolution frames are kept; the hashes are
    assert rec["frame"]["files"]["original"] is None and rec["frame"]["sha256_of"] == "pixels" and len(rec["frame"]["sha256"]) == 64
    assert not list(dirs.media.iterdir()) and not list(dirs.originals.iterdir())
    assert video["acquisition"]["media"]["sha256"] and "deleted" in video["acquisition"]["reason"]
    assert EvidenceService(pipeline.repo).frame(rec["frame_id"])["urls"]["original"] is None
    # only the uploader geotag carries coordinates; country and place-name candidates don't
    locs = {loc["provenance"]["method"]: loc for loc in rec["inferred"]["locations"]}
    assert locs["youtube_recording_details_geotag"]["latitude"] == 50.1
    assert locs["discovery_query_context"]["place_name"] == "Kyiv" and locs["discovery_query_context"]["latitude"] is None
    assert locs["scope_check"]["place_name"] == "Ukraine" and locs["scope_check"]["confidence"] <= 0.95
    assert video["scope"]["in_scope"] is True

    # second run is a no-op
    assert pipeline.ingest(YID, api_item=API_ITEM, contexts=[ctx]).status == "skipped_existing"


def test_kept_originals_and_videos_can_be_slimmed_later(pipeline):
    pipeline.cfg.acquisition.keep_media = True
    pipeline.cfg.extraction.keep_originals = True
    pipeline.ingest(YID, api_item=API_ITEM, contexts=[])
    lib, dirs = pipeline.lib, pipeline.lib.video(YID)
    rec = json.loads(sorted(dirs.meta.glob("*.json"))[0].read_text())
    assert rec["frame"]["original_format"] == "png" and rec["frame"]["sha256_of"] == "original"
    has = lambda rel: lib.abs(rel).is_file()
    assert EvidenceService(pipeline.repo, has_file=has).frame(rec["frame_id"])["urls"]["original"]
    assert slim(lib, pipeline.repo, dry_run=True)[0][1] > 1 and list(dirs.media.iterdir())  # dry run deletes nothing
    (yid, n, size), = slim(lib, pipeline.repo)
    assert yid == YID and n > 1 and size > 0
    assert not list(dirs.media.iterdir()) and not list(dirs.originals.iterdir()) and list(dirs.web.iterdir())
    # the record keeps where the original was and its hash (the source link is immutable); the site stops linking it
    assert json.loads(sorted(dirs.meta.glob("*.json"))[0].read_text()) == rec
    assert EvidenceService(pipeline.repo, has_file=has).frame(rec["frame_id"])["urls"]["original"] is None
    assert "deleted" in json.loads(dirs.video_json.read_text())["acquisition"]["reason"]


def test_out_of_scope_video_writes_nothing(pipeline):
    item = {**API_ITEM, "snippet": {**API_ITEM["snippet"], "title": "Chico drone", "description": "California", "tags": []}}
    item["recordingDetails"] = {}
    result = pipeline.ingest(YID, api_item=item, contexts=[])
    assert result.status == "rejected"
    assert not pipeline.lib.video(YID).root.exists()


def test_policy_blocks_non_cc_download(pipeline):
    item = {**API_ITEM, "status": {**API_ITEM["status"], "license": "youtube"}}
    result = pipeline.ingest(YID, api_item=item, contexts=[])
    assert result.acquisition == "skipped_policy" and result.frames == 0
    assert not list(pipeline.lib.video(YID).media.iterdir())


def test_forced_reingest_that_cannot_download_keeps_the_frames(pipeline, monkeypatch):
    first = pipeline.ingest(YID, api_item=API_ITEM, contexts=[])
    refused = Acquisition(status="unavailable", policy="public", reason="Sign in to confirm you're not a bot")
    monkeypatch.setattr(acquisition, "download", lambda cfg, dirs, lib, yid: (refused, None))
    again = pipeline.ingest(YID, api_item=API_ITEM, contexts=[], force=True)
    video = json.loads(pipeline.lib.video(YID).video_json.read_text())
    assert again.frames == first.frames > 0 and len(video["frame_ids"]) == first.frames
    assert video["acquisition"]["status"] == "downloaded"


def test_frame_source_link_is_immutable_in_db(pipeline):
    pipeline.ingest(YID, api_item=API_ITEM, contexts=[])
    conn = sqlite3.connect(pipeline.lib.db_path)
    with pytest.raises(sqlite3.IntegrityError, match="immutable"):
        conn.execute("UPDATE frames SET timestamp_s = timestamp_s + 1")
    conn.execute("UPDATE frames SET web_path = web_path")  # mutable columns are fine


def test_service_search_related_and_reindex(pipeline, tmp_path):
    ctx = DiscoveryContext(run_id="r", query="Kyiv drone", location="Kyiv", rank=0)
    pipeline.ingest(YID, api_item=API_ITEM, contexts=[ctx])
    svc = EvidenceService(pipeline.repo)

    res = svc.search(text="old town", year=2023)
    assert res["total"] >= 3 and res["facets"]["year"] == {"2023": res["total"]}
    assert svc.search(year=2022)["total"] == 0
    assert svc.search(text="Kyiv")["total"] == res["total"]  # matches inferred place name

    first = res["items"][0]["frame_id"]
    related = svc.related(first, radius_km=1)
    assert related and all(r["relation"] == "geo_proximity" for r in related)
    assert first not in {r["frame_id"] for r in related}

    detail = svc.frame(first)
    assert detail["video"]["source"]["youtube_id"] == YID

    fresh = SQLiteRepository(tmp_path / "fresh.db")
    assert reindex(Library(pipeline.lib.root), fresh) == (1, res["total"])
    assert EvidenceService(fresh).search()["total"] == res["total"]
