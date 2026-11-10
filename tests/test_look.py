"""The flight south's look pass (scene3d/look.py, animatic.grade_image): offline, no Blender."""

import numpy as np
from PIL import Image

from image_evidence.satellite.scene3d import look
from image_evidence.satellite.scene3d.animatic import grade_image


def test_fit_recovers_a_gain_and_offset_on_stable_land():
    rng = np.random.default_rng(0)
    ref = rng.integers(40, 200, (200, 200, 3)).astype(np.uint8)
    im = np.clip((ref.astype(np.float32) - 10) / 0.8, 0, 255).astype(np.uint8)   # ref = 0.8·im + 10
    im[:50] = rng.integers(40, 200, (50, 200, 3))   # a quarter changed (fields): trimmed away
    f = look.fit(ref, im, np.ones(ref.shape[:2], bool))
    assert np.allclose(f["gain"], 0.8, atol=0.03) and np.allclose(f["offset"], 10, atol=4)
    assert f["median_abs_diff_after"] < f["median_abs_diff_before"]


def test_apply_keeps_no_data_black():
    im = np.full((4, 4, 3), 100, np.uint8)
    im[0, 0] = 0
    out = look.apply(im, {"gain": [1.1, 1.0, 0.9], "offset": [5, 0, -5]})
    assert out[0, 0].tolist() == [0, 0, 0] and out[1, 1].tolist() == [115, 100, 85]


def test_pre_breach_share_eases_in_by_the_date_shown():
    frames = [{} for _ in range(5)]
    days = [look._day(d) for d in ("2022-12-01", "2022-12-15", "2023-03-03", "2023-05-20", "2023-06-06")]
    look.per_frame({"pre_breach": {"from": "2022-12-15", "until": "2023-05-20"}}, frames, days, None)
    w = [f["pre_breach"] for f in frames]
    assert w[0] == 0 and w[1] == 0 and 0 < w[2] < 1 and w[3] == 1 and w[4] == 1


def test_grade_is_the_same_each_time_and_off_changes_nothing():
    im = Image.fromarray(np.full((20, 30, 3), 120, np.uint8))
    g = {"saturation": 0.9, "tint": [0.98, 1.0, 1.03], "grain": 0.01, "vignette": 0.15}
    a, b = np.asarray(grade_image(im, g, 7)), np.asarray(grade_image(im, g, 7))
    assert (a == b).all() and a.shape == (20, 30, 3)
    assert (np.asarray(grade_image(im, {}, 7)) == 120).all()
