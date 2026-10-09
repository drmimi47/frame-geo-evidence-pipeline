"""Temporal Map tracks: dashcam clock -> continuous stretches and cuts -> positions along a road (offline)."""

from datetime import datetime, timedelta

from image_evidence import track

T0 = datetime(2021, 9, 12, 15, 52, 0)


def _frame(fid: str, t: float, clock: datetime | None, extra: str | None = None) -> dict:
    lines = []
    if clock:
        lines.append({"text": f"GARMIN {clock:%d/%m/%Y %H:%M:%S}", "confidence": 1.0, "box": [0, 0, 1, 1]})
    if extra:
        lines.append({"text": extra, "confidence": 1.0, "box": [0, 0, 1, 1]})
    return {"frame_id": fid, "frame": {"timestamp_s": t}, "derived": {"ocr": {"lines": lines}}}


def _frames() -> list[dict]:
    # 0-100 s filmed in real time; then the clock jumps 600 s (a cut at ~100 s); 100-200 s real time again
    out = [_frame(f"f{t}", t, T0 + timedelta(seconds=t)) for t in (10, 40, 70, 95)]
    out += [_frame(f"g{t}", t, T0 + timedelta(seconds=t + 600), "Вел. Знам'янка" if t == 150 else None) for t in (105, 150, 190)]
    out.append(_frame("nolock", 120, None))
    return out


def _route() -> dict:
    # a straight road due north, ~11.1 km long
    coords = [[34.0, 47.0 + k * 0.01] for k in range(11)]
    return {"request": "x", "response": {"code": "Ok", "routes": [{"geometry": {"coordinates": coords},
            "legs": [{"steps": [{"name": "", "ref": "Т-08-04"}]}]}]}}


def test_clock_readings_and_cuts():
    readings = track.clock_readings(_frames())
    assert [r[0] for r in readings] == [10, 40, 70, 95, 105, 150, 190]
    segs = track.segments(readings, 200.0, drive_start=5.0)
    assert len(segs) == 2
    assert segs[0]["video_start"] == 5.0 and segs[0]["video_end"] == 100.0  # half way between 95 and 105
    assert segs[1]["video_end"] == 200.0
    assert segs[1]["clock_offset_s"] - segs[0]["clock_offset_s"] == 600
    # a cut measured more finely moves the boundary
    assert track.segments(readings, 200.0, 5.0, cuts=[98.0])[0]["video_end"] == 98.0


def test_build_places_frames_along_the_road():
    video = {"video_id": "yt_x", "source": {"youtube_id": "x", "duration_s": 200.0}}
    t = track.build(video, _frames(), _route(), start=(47.0, 34.0), end=(47.1, 34.0), route_note="test", drive_start=5.0)
    L = t["route"]["length_m"]
    assert 11000 < L < 11200
    assert t["tier"] == "inferred" and t["confidence"] < 1
    # clock time runs 5 s .. 800 s; the cut skips 600 s of it, so most of the road is unfilmed
    s0, s1 = t["segments"]
    assert s0["along_start_m"] == 0 and abs(s1["along_end_m"] - L) <= 1
    assert s1["along_start_m"] - s0["along_end_m"] > 0.7 * L
    # positions only move forward, and the uncertainty is smallest at the ends
    along = [s[1] for s in t["samples"]]
    assert along == sorted(along)
    sig = [s[5] for s in t["samples"]]
    assert sig[0] < max(sig) and sig[-1] < max(sig)
    # every stored frame is placed; non-clock on-screen text is kept with it as a clue
    by = {f["frame_id"]: f for f in t["frames"]}
    assert set(by) == {f["frame_id"] for f in _frames()}
    assert by["g150"]["onscreen_text"] == ["Вел. Знам'янка"]
    assert all(p["method"] for p in t["provenance"])
