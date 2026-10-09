from image_evidence.config import ExtractionConfig
from image_evidence.frames import extract, select_candidates


def test_scene_changes_and_interval_sampling(synthetic_video):
    probe, cands, it = extract(synthetic_video, ExtractionConfig(interval_s=4, dedup_hamming=0))
    assert (probe.width, probe.height, round(probe.fps)) == (1280, 720, 30)
    scene = [c.pts_time for c in cands if c.selection == "scene_change"]
    assert scene == [6.0, 12.0]
    frames = list(it)
    assert frames[0].timestamp_s == 0.0 and frames[0].frame_number == 0
    for f in frames:
        assert f.frame_number == round(f.timestamp_s * 30)
        assert f.rgb.shape == (720, 1280, 3)


def test_dedup_and_cap(synthetic_video):
    # 1s sampling over 18s; the static SMPTE-bars segment collapses to one frame
    _, cands, it = extract(synthetic_video, ExtractionConfig(interval_s=1, min_gap_s=0.5))
    kept = list(it)
    assert len(cands) >= 18
    assert len(kept) < len(cands) - 4
    assert len({f.quality.dhash for f in kept}) == len(kept)
    _, cands, _ = extract(synthetic_video, ExtractionConfig(interval_s=1, max_frames_per_video=3))
    assert len(cands) == 3


def test_a_pan_gives_a_frame_for_each_new_view(panning_video, synthetic_video):
    cfg = ExtractionConfig(interval_s=30)
    cands = select_candidates(panning_video, cfg)
    assert [c.selection for c in cands[:1]] == ["interval"]
    moves = [c.pts_time for c in cands if c.selection == "camera_move"]
    assert len(moves) >= 3 and all(t > 4 for t in moves)  # the still opening adds nothing; the pan adds several
    assert len(select_candidates(panning_video, ExtractionConfig(interval_s=30, view_step_s=0))) == 1
    # Still shots and shots with motion but a steady camera (SMPTE bars, test pattern) add no camera moves.
    assert not [c for c in select_candidates(synthetic_video, cfg) if c.selection == "camera_move" and c.pts_time < 12]
