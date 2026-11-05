"""The storyboard's plan outside Blender: the layout, and reading a rearrangement back (no Blender or ffmpeg)."""

from pathlib import Path

import pytest
import yaml

from image_evidence.storyboard import plan

POOL = {
    "fps": 30,
    "size": [1920, 1080],
    "sources": {"film": {"network": "znpp"}, "fig": {"file": "reports/images/x.png"}},
    "shots": {
        "a": {"title": "A", "status": "good", "source": "film", "in": 0, "out": 10},
        "b": {"title": "B", "status": "still", "source": "fig", "duration": 4},
        "c": {"title": "C", "status": "missing", "duration": 5, "tells": "c tells"},
        "d": {"title": "D", "status": "idea", "duration": 2},
    },
}
CUT = {"note": "n", "shots": ["a", "b", "c"]}


def resolve(sh):
    if sh.get("source") == "film":
        return {"kind": "movie", "path": "/m/film.mp4", "frames": 900, "audio": True}
    if sh.get("source") == "fig":
        return {"kind": "image", "path": "/m/x.png"}
    return None


def test_layout_end_to_end_then_parked():
    sp = plan.layout(POOL, "cut", CUT, resolve)
    assert [(s["id"], s["start"], s["frames"], s["kind"]) for s in sp["shots"]] == [
        ("a", 1, 300, "movie"), ("b", 301, 120, "image"), ("c", 421, 150, "card")]
    assert sp["end"] == 571
    assert [(s["id"], s["start"]) for s in sp["parked"]] == [("d", 571 + plan.PARK_GAP_S * 30)]


def test_layout_trim_and_refusal():
    sp = plan.layout(POOL, "cut", {"shots": [{"shot": "a", "in": 2, "out": 40}]}, resolve)
    assert (sp["shots"][0]["in"], sp["shots"][0]["frames"]) == (60, 840)   # out clamped to the film's 900 frames
    with pytest.raises(ValueError):
        plan.layout(POOL, "cut", {"shots": [{"shot": "a", "in": 5, "out": 5}]}, resolve)


def _strip(name, left, right, kind="META", channel=1, mute=False, **kw):
    return {"name": name, "type": kind, "left": left, "right": right, "channel": channel, "mute": mute, **kw}


def test_merge_reads_order_trims_parking_and_new_strips():
    rb = {"fps": 30, "frame_end": 570, "markers": {"END": 571}, "strips": [
        _strip("c", 1, 151),
        _strip("a", 211, 451, picture={"type": "MOVIE", "content_start": 151, "left": 151, "right": 451}),  # in 2 s
        _strip("b", 900, 1020),                        # moved past END: parked
        _strip("d", 451, 511),                         # brought in from the parked shots, 2 s
        _strip("Text", 600, 690, kind="TEXT", channel=5, text="Diver interview?"),   # after END: made, parked
        _strip("a.001", 511, 571, picture={"type": "MOVIE", "content_start": 211, "left": 211, "right": 571}),
    ]}
    new, report = plan.merge(POOL, CUT, rb)
    assert new["note"] == "n"
    assert new["shots"] == ["c", {"shot": "a", "in": 2.0}, "d", {"shot": "a.001", "in": 10.0, "out": 12.0}]
    assert "parked: b" in report and "into the cut: d" in report
    assert any(r.startswith("new: diver-interview") for r in report)


def test_merge_keeps_a_shot_made_in_blender():
    cut = {"shots": ["a", {"shot": "note-1", "title": "Note", "status": "new", "duration": 3}]}
    rb = {"fps": 30, "frame_end": 500, "markers": {"END": 500}, "strips": [
        _strip("note-1", 1, 121),
        _strip("a", 121, 421, picture={"type": "MOVIE", "content_start": 121, "left": 121, "right": 421}),
    ]}
    new, _ = plan.merge(POOL, cut, rb)
    assert new["shots"] == [{"shot": "note-1", "title": "Note", "status": "new", "duration": 4.0}, "a"]


def test_merge_hides_a_parked_shot_deleted_in_blender():
    rb = {"fps": 30, "frame_end": 570, "markers": {"END": 571}, "strips": [
        _strip("a", 1, 301, picture={"type": "MOVIE", "content_start": 1, "left": 1, "right": 301}),
        _strip("b", 301, 421), _strip("c", 421, 571)]}          # d (parked) deleted
    new, report = plan.merge(POOL, CUT, rb)
    assert new["hidden"] == ["d"] and "hidden: d (deleted from the parked shots; kept in the pool)" in report
    assert plan.parked(POOL, new) == [] and "d" in POOL["shots"]
    rb["strips"].append(_strip("d", 900, 960))                 # put back past END: parked again
    again, _ = plan.merge(POOL, new, rb)
    assert "hidden" not in again and plan.parked(POOL, again) == ["d"]


def test_cuts_file_round_trip(tmp_path: Path):
    pool_p, cuts_p = tmp_path / "pool.yaml", tmp_path / "cuts.yaml"
    pool_p.write_text(yaml.safe_dump(POOL))
    cuts = {"draft": {"note": "a note: with a colon", "shots": ["c", {"shot": "a", "in": 2.0}, "b"]}}
    plan.write_cuts(POOL, cuts, cuts_p)
    assert "# A (good)" in cuts_p.read_text()
    _, back = plan.load(pool_p, cuts_p)
    assert back == cuts
    lines = plan.show(POOL, "draft", back["draft"])
    assert "0:17.0 in all" in lines[-2] and "parked (1): d" in lines[-1]


def test_load_refuses_bad_shots(tmp_path: Path):
    bad = {**POOL, "shots": {"Bad id": {"status": "good", "duration": 1}}}
    (tmp_path / "p.yaml").write_text(yaml.safe_dump(bad))
    with pytest.raises(ValueError):
        plan.load(tmp_path / "p.yaml", tmp_path / "none.yaml")
    bad = {**POOL, "shots": {"x": {"status": "good", "source": "fig"}}}   # a figure without a duration
    (tmp_path / "p.yaml").write_text(yaml.safe_dump(bad))
    with pytest.raises(ValueError):
        plan.load(tmp_path / "p.yaml", tmp_path / "none.yaml")
