import json

import numpy as np
from PIL import Image

from image_evidence.service import EvidenceService
from image_evidence.sorting import SORTS, by_similarity
from image_evidence.store import FrameQuery
from image_evidence.visual import pixel_features

from .test_discovery import API_ITEM
from .test_pipeline import YID, pipeline  # noqa: F401  (fixture)


def solid(rgb, lower=None):
    a = np.zeros((90, 160, 3), np.uint8)
    a[:] = rgb
    if lower is not None:
        a[45:] = lower
    return Image.fromarray(a)


def test_pixel_features():
    green = pixel_features(solid((40, 140, 50)))
    assert green["greenness"] > 0.9 and 90 < green["hue"] < 150
    grey = pixel_features(solid((120, 120, 120)))
    assert grey["hue"] is None and grey["greenness"] == 0
    snowy = pixel_features(solid((90, 110, 140), lower=(235, 238, 240)))  # blue sky, white ground
    assert snowy["snow"] > 0.4
    assert pixel_features(solid((200, 120, 60)))["warmth"] > 0.3


def test_similarity_puts_matching_views_together(pipeline):  # noqa: F811
    pipeline.ingest(YID, api_item=API_ITEM, contexts=[])
    frames = pipeline.repo.get_frames(pipeline.repo.search_frames(FrameQuery(limit=100)).frame_ids)
    assert len(frames) >= 4
    a, b = np.eye(8)[0], np.eye(8)[1]
    emb = {f.frame_id: (a if i % 2 == 0 else b) + 0.01 * i for i, f in enumerate(frames)}
    rows = by_similarity(frames, emb)
    assert len(rows) == len(frames)
    kind = {f.frame_id: i % 2 for i, f in enumerate(frames)}
    seq = [kind[f.frame_id] for f, _, _ in rows]
    assert sum(a != b for a, b in zip(seq, seq[1:])) == 1  # all 'a' views together, then all 'b' views


def test_every_sort_returns_all_frames(pipeline):  # noqa: F811
    pipeline.ingest(YID, api_item=API_ITEM, contexts=[])
    svc = EvidenceService(pipeline.repo)
    total = svc.search()["total"]
    meta = json.loads(next(pipeline.lib.video(YID).meta.glob("*.json")).read_text())
    assert meta["derived"]["features"]["color_hex"].startswith("#")  # pixel features computed at ingest
    for key in SORTS:
        res = svc.search(sort=key, limit=500)
        assert res["total"] == total and len(res["items"]) == total, key
        assert all(it["sort_note"] for it in res["items"]), key
    assert svc.stats() == {"videos": 1, "frames": total}


def test_query_image_ranks_by_similarity(pipeline):  # noqa: F811
    from image_evidence.sorting import by_query_image

    pipeline.ingest(YID, api_item=API_ITEM, contexts=[])
    frames = pipeline.repo.get_frames(pipeline.repo.search_frames(FrameQuery(limit=100)).frame_ids)
    emb = {f.frame_id: np.eye(8)[i % 8] for i, f in enumerate(frames)}
    target = frames[2]
    rows = by_query_image(frames, emb, emb[target.frame_id] * 3)
    assert rows[0][0].frame_id == target.frame_id and "1.00" in rows[0][2]


def test_scale_runs_from_close_up_to_aerial(pipeline):  # noqa: F811
    from image_evidence.sorting import by_scale

    pipeline.ingest(YID, api_item=API_ITEM, contexts=[])
    frames = pipeline.repo.get_frames(pipeline.repo.search_frames(FrameQuery(limit=100)).frame_ids)
    values = [0.95, 0.1, 0.5, None]  # aerial, close-up, street, not computed yet
    for f, v in zip(frames, values):
        f.derived.features.scale = v
    rows = by_scale(frames[:4], {})
    assert [r[1] for r in rows] == ["close-up", "street", "aerial", "none"]
    assert "close-up 0 to aerial 100" in rows[0][2] and "evidence analyze" in rows[-1][2]
