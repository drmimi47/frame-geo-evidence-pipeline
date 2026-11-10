"""The flight south's look pass 2 (scene3d/vegetation.py, plants.py, towers' `detail`): offline, no Blender."""

import numpy as np
import pytest

from image_evidence.satellite.scene3d import look, plants, towers, vegetation
from tests.test_scene3d import _crossing_line, _placed


def test_the_forest_grows_with_the_date_through_the_sourced_heights():
    g = vegetation.growth_at(np.arange(-100, 1500, 5.0))
    assert (np.diff(g) >= 0).all()                                    # never shrinks: no popping back
    assert vegetation.growth_at(0) == 0 and vegetation.growth_at(11) == 0   # bare and wet first
    assert vegetation.growth_at(814) == pytest.approx(1.0)            # the 2025 survey's heights (5-7 m)
    assert 1.2 < vegetation.growth_at(1224) <= 1.4                    # up to about 9 m in 2026
    assert vegetation.growth_at(444) < 0.5                            # herbs and saplings in 2023-24


def test_the_plants_day_is_set_only_with_the_option():
    days = [vegetation.D0 - 10.0, vegetation.D0 + 814.5]
    off, on = [{}, {}], [{}, {}]
    look.per_frame({}, off, days, None)
    look.per_frame({"vegetation": {"seed": 7}}, on, days, None)
    assert off == [{}, {}]
    assert [f["veg_day"] for f in on] == [-10.0, 814.5]


def test_the_far_crown_is_cheap_and_the_same_each_time():
    a, b = plants.crown("willow", 1003, 6.5).arrays(), plants.crown("willow", 1003, 6.5).arrays()
    assert all(np.array_equal(x, y) for x, y in zip(a, b))
    assert len(a[1]) < 80 and a[0][:, 2].max() <= 6.5 * 1.05


def test_the_jittered_grid_fades_across_a_band_edge():
    dist = np.tile(np.arange(0, 100) * vegetation.CELL, (40, 1)).astype(np.float32)   # distance grows eastward
    x, _ = vegetation._grid_pts(np.random.default_rng(0), dist, 0.0, 0.0, 0.0, 1000.0, 5.0)
    d = x                                                              # the distance is x here
    inner = ((d > 200) & (d < 700)).sum() / 500
    edge = ((d > 1000) & (d < 1100)).sum() / 100
    assert edge < inner * 0.75 and ((d > 1000 + vegetation.BLEND_M + vegetation.CELL)).sum() == 0


def _flat(v):
    if isinstance(v, (list, tuple)):
        return [x for e in v for x in _flat(e)]
    return list(np.ravel(np.asarray(v, float)))


def test_detailed_towers_keep_their_attachment_points_and_shapes_only_add():
    plain, fine = towers.build_types(), towers.build_types(detail=True)
    assert plain.keys() == fine.keys()
    for k in plain:
        a, b = plain[k][1], fine[k][1]
        assert a.keys() == b.keys(), k
        for n in a:                                                   # the same circuits, earth wires, jumpers
            assert np.allclose(np.asarray(_flat(a[n])), np.asarray(_flat(b[n]))), (k, n)
        pv, fv = plain[k][0].arrays()["v"], fine[k][0].arrays()["v"]
        assert len(fv) >= len(pv)
        assert fv[:, 2].max() == pytest.approx(pv[:, 2].max(), abs=0.5), k   # the same height
    assert len(fine["crossing330"][0].arrays()["counts"]) > 2 * len(plain["crossing330"][0].arrays()["counts"])
    again = towers.build_types()                                      # the option never leaks into a later build
    assert np.array_equal(again["crossing330"][0].arrays()["v"], plain["crossing330"][0].arrays()["v"])


def test_detailed_fittings_add_to_the_spans_and_leave_the_plain_ones_alone():
    ln = _crossing_line()
    towers.assign([ln], {"D": "К-П-П-А-П-П-К"})
    lines = _placed([ln])
    ws = towers.wires(lines, {k: a for k, (_, a) in towers.build_types().items()}, {"span": 1800.0, "crossing": 4200.0})
    plain = towers.fittings(ws, [750]).arrays()["v"]
    fine = towers.fittings(ws, [750], detail=True).arrays()["v"]
    assert len(fine) > len(plain)
    assert np.array_equal(towers.fittings(ws, [750]).arrays()["v"], plain)
