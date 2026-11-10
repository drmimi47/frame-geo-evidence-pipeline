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


def test_layout_marks_the_end_titles():
    pool = {**POOL, "shots": {**POOL["shots"], "e": {"title": "E", "status": "draft", "duration": 3, "card": "by X",
                                                      "end_titles": True}}}
    sp = plan.layout(pool, "cut", {"shots": ["a", "e"]}, resolve)
    assert [(s["id"], s["end_titles"]) for s in sp["shots"]] == [("a", False), ("e", True)]


def test_layout_carries_a_caption():
    pool = {**POOL, "shots": {**POOL["shots"], "a": {**POOL["shots"]["a"], "caption": "ON THE PICTURE"}}}
    assert plan.layout(pool, "cut", CUT, resolve)["shots"][0]["caption"] == "ON THE PICTURE"


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
        _strip("a", 151, 391, picture={"type": "MOVIE", "content_start": 91, "left": 91, "right": 391}),  # in 2 s
        _strip("b", 900, 1020),                        # moved past END: parked
        _strip("d", 391, 451),                         # brought in from the parked shots, 2 s
        _strip("Text", 600, 690, kind="TEXT", channel=5, text="Diver interview?"),   # after END: made, parked
        _strip("a.001", 451, 511, picture={"type": "MOVIE", "content_start": 151, "left": 151, "right": 571}),
    ]}
    new, report = plan.merge(POOL, CUT, rb)
    assert new["note"] == "n"
    assert new["shots"] == ["c", {"shot": "a", "in": 2.0}, "d", {"shot": "a.001", "in": 10.0, "out": 12.0}]
    assert "parked: b" in report and "into the cut: d" in report
    assert any(r.startswith("new: diver-interview") for r in report)


def test_layout_lays_a_shot_over_the_one_before():
    sp = plan.layout(POOL, "cut", {"shots": [{"shot": "a", "out": 5, "silent": True}, {"shot": "b", "over": True}, "c"]},
                     resolve)
    assert [(s["id"], s["start"], s.get("channel", 1), s["silent"]) for s in sp["shots"]] == [
        ("a", 1, 1, True), ("b", 1, 2, False), ("c", 151, 1, False)]


def test_merge_reads_a_shot_over_another_and_a_muted_sound():
    rb = {"fps": 30, "frame_end": 450, "markers": {"END": 451}, "strips": [
        _strip("a", 1, 151, silent=True, picture={"type": "MOVIE", "content_start": 1, "left": 1, "right": 151}),
        _strip("b", 1, 121, channel=2),
        _strip("c", 151, 301),
    ]}
    new, _ = plan.merge(POOL, CUT, rb)
    assert new["shots"] == [{"shot": "a", "out": 5.0, "silent": True}, {"shot": "b", "over": True}, "c"]


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
    assert new["hidden"] == ["d"] and "hidden: d (deleted in Blender; kept in the pool)" in report
    assert plan.parked(POOL, new) == [] and "d" in POOL["shots"]
    rb["strips"].append(_strip("d", 900, 960))                 # put back past END: parked again
    again, _ = plan.merge(POOL, new, rb)
    assert "hidden" not in again and plan.parked(POOL, again) == ["d"]


def test_merge_hides_a_shot_deleted_from_the_cut():
    rb = {"fps": 30, "frame_end": 570, "markers": {"END": 571}, "strips": [
        _strip("a", 1, 301, picture={"type": "MOVIE", "content_start": 1, "left": 1, "right": 301}),
        _strip("c", 301, 451), _strip("d", 900, 960)]}          # b deleted from the cut
    new, report = plan.merge(POOL, CUT, rb)
    assert new["shots"] == ["a", "c"] and new["hidden"] == ["b"] and "parked: b" not in report
    assert plan.parked(POOL, new) == ["d"]                    # a build won't bring b back
    pool = {**POOL, "shots": {**POOL["shots"], "e": {"title": "E", "status": "idea", "duration": 3}}}
    assert "e" not in plan.merge(pool, CUT, rb, built=["a", "b", "c", "d"])[0]["hidden"]  # new to the pool since



def test_parked_shots_keep_their_channel():
    pool = {**POOL, "shots": {**POOL["shots"], "e": {"title": "E", "status": "idea", "duration": 3}}}
    rb = {"fps": 30, "frame_end": 570, "markers": {"END": 571}, "strips": [
        _strip("a", 1, 301, picture={"type": "MOVIE", "content_start": 1, "left": 1, "right": 301}),
        _strip("b", 301, 421), _strip("c", 421, 571),
        _strip("e", 700, 790, channel=2), _strip("d", 900, 960, channel=2)]}    # the old parked shots, kept apart
    new, _ = plan.merge(pool, CUT, rb)
    assert new["lanes"] == {"2": ["e", "d"]}
    sp = plan.layout(pool, "cut", new, resolve)
    gap = 571 + plan.PARK_GAP_S * 30
    assert [(s["id"], s["channel"], s["start"]) for s in sp["parked"]] == [("e", 2, gap), ("d", 2, gap + 90)]
    rb["strips"][3] = _strip("e", 700, 790)                                   # moved down to the first channel
    again, _ = plan.merge(pool, new, rb)
    assert again["lanes"] == {"2": ["d"]}
    assert [(s["id"], s["channel"]) for s in plan.layout(pool, "cut", again, resolve)["parked"]] == [("e", 1), ("d", 2)]


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


def test_narrate_lays_lines_from_their_shots(tmp_path: Path):
    sp = plan.layout(POOL, "cut", CUT, resolve)
    for n in ("l1", "l2", "l3"):
        (tmp_path / f"{n}.wav").write_bytes(b"")
    cfg = {"channel": 9, "lines": [
        {"id": "l1", "shot": "b", "at": 1.0, "text": "x"},
        {"id": "l2", "shot": "c", "at": 0.0, "text": "y"},
        {"id": "l3", "shot": "d", "at": 0.0, "text": "parked"},
        {"id": "l4", "shot": "a", "at": 0.0, "text": "not rendered"}]}
    rendered = {n: {"file": f"{n}.wav", "seconds": s} for n, s in (("l1", 4.0), ("l2", 2.0), ("l3", 1.0))}
    report = plan.narrate(sp, cfg, rendered, tmp_path)
    assert [(v["id"], v["start"], v["frames"]) for v in sp["narration"]] == [("l1", 331, 120), ("l2", 421, 60)]
    assert sp["narration_channel"] == 9
    assert "narration: l3 left out (d isn't in the cut)" in report
    assert any(r.startswith("narration: l4 left out (not rendered") for r in report)
    assert "narration: l1 runs 1.0 s into l2" in report


def test_merge_leaves_the_narration_out():
    rb = {"fps": 30, "frame_end": 570, "markers": {"END": 571}, "strips": [
        _strip("a", 1, 301, picture={"type": "MOVIE", "content_start": 1, "left": 1, "right": 301}),
        _strip("b", 301, 421), _strip("c", 421, 571),
        _strip("vo l1", 331, 451, kind="SOUND", channel=10)]}
    new, report = plan.merge(POOL, CUT, rb)
    assert new["shots"] == ["a", "b", "c"] and not any("vo l1" in r for r in report)


def test_layout_colours_by_status_unless_set_by_hand():
    sp = plan.layout(POOL, "cut", CUT, resolve)
    assert [s["color"] for s in sp["shots"] + sp["parked"]] == ["COLOR_04", "COLOR_05", "COLOR_01", "COLOR_08"]
    sp = plan.layout(POOL, "cut", {**CUT, "colors": {"b": "COLOR_09", "d": "COLOR_02"}}, resolve)
    assert [s["color"] for s in sp["shots"] + sp["parked"]] == ["COLOR_04", "COLOR_09", "COLOR_01", "COLOR_02"]


def test_merge_keeps_a_colour_set_in_blender():
    pic = {"type": "MOVIE", "content_start": 1, "left": 1, "right": 301}
    rb = {"fps": 30, "frame_end": 570, "markers": {"END": 571}, "strips": [
        _strip("a", 1, 301, picture=pic, color_tag="COLOR_04"), _strip("b", 301, 421, color_tag="COLOR_09"),
        _strip("c", 421, 571, color_tag="COLOR_01"), _strip("d", 900, 960, color_tag="COLOR_02")]}
    new, report = plan.merge(POOL, CUT, rb)
    assert new["colors"] == {"b": "COLOR_09", "d": "COLOR_02"}          # a and c as their status: not recorded
    assert "colour: b COLOR_09" in report
    rb["strips"][1]["color_tag"] = "COLOR_05"                            # b set back to its status's colour
    again, report = plan.merge(POOL, new, rb)
    assert again["colors"] == {"d": "COLOR_02"} and "colour: b back to its status's" in report
    rb["strips"].pop()                                                    # d deleted: hidden, its colour kept
    assert plan.merge(POOL, again, rb)[0]["colors"] == {"d": "COLOR_02"}


def test_layout_end_at_a_ceiling():
    sp = plan.layout({**POOL, "end_at_s": 60}, "cut", CUT, resolve)
    assert (sp["film_end"], sp["end"]) == (571, 1801)
    assert sp["parked"][0]["start"] == 1801                 # right after the ceiling, no gap
    sp = plan.layout({**POOL, "end_at_s": 10}, "cut", CUT, resolve)   # the cut runs past it: END where the cut ends
    assert (sp["end"], sp["parked"][0]["start"]) == (571, 571 + plan.PARK_GAP_S * 30)


def test_merge_and_layout_keep_a_gap():
    pic = {"type": "MOVIE", "content_start": 1, "left": 1, "right": 301}
    rb = {"fps": 30, "frame_end": 900, "markers": {"END": 901}, "strips": [
        _strip("a", 1, 301, picture=pic), _strip("b", 301, 421), _strip("c", 721, 871)]}   # 10 s of black before c
    new, report = plan.merge(POOL, CUT, rb)
    assert new["shots"][2] == {"shot": "c", "gap": 10.0} and "gap: 10.0 s before c" in report
    sp = plan.layout(POOL, "cut", new, resolve)
    assert [s["start"] for s in sp["shots"]] == [1, 301, 721] and sp["film_end"] == 871
    assert plan.show(POOL, "cut", new)[2].startswith("  0:24.0")
    rb["strips"][2].update(left=421, right=571)                              # closed again
    again, report = plan.merge(POOL, new, rb)
    assert again["shots"][2] == "c" and "gap: closed before c" in report
