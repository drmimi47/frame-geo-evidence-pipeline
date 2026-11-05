"""The crossing in 3D, pass 0: the survey's geometry on plain arrays (metres east and north of the plant)."""

from datetime import date

import numpy as np
import pytest

from image_evidence.satellite import hum
from image_evidence.satellite.scene3d import bed, export, states, towers


def _two_lines():
    # a 750 kV line from the west that turns north, and a 330 kV line from the east that it passes over; north of the
    # crossing they run side by side 400 m apart
    a = np.array([[0, 0], [1000, 1000], [1200, 2000], [1200, 6000]], float)
    b = np.array([[1600, 0], [1000, 1500], [800, 2500], [800, 6000]], float)
    return a, b


def test_where_the_lines_cross_and_the_midline_between_them():
    a, b = _two_lines()
    p, ia, ib = export.crossing_point(a, b)
    assert (ia, ib) == (1, 0)
    assert a[1][1] < p[1] < a[2][1]
    na, nb = export.from_point(a, ia, p), export.from_point(b, ib, p)
    mid = export.midline(na, nb, float(p[1]), 5000.0, step=100)
    assert mid["xy"][0] == pytest.approx(p)          # it starts where they cross
    assert mid["xy"][-1, 1] == 5000.0
    assert mid["gap"][-1] == pytest.approx(400)
    # it stays between the two lines all the way
    xa, xb = export.x_at(na, mid["xy"][:, 1]), export.x_at(nb, mid["xy"][:, 1])
    assert np.all((mid["xy"][:, 0] >= np.minimum(xa, xb) - 1e-6) & (mid["xy"][:, 0] <= np.maximum(xa, xb) + 1e-6))


def test_a_line_that_turns_back_south_has_no_single_easting():
    with pytest.raises(ValueError):
        export.x_at(np.array([[0, 0], [0, 100], [50, 50]], float), np.array([60.0]))


def test_vertices_are_towers_only_at_the_same_osm_point():
    xy = np.array([[0, 0], [100, 0], [200, 0]], float)
    nodes = np.array([[100.4, 0.3], [205, 0], [0, 0]], float)
    assert export.snap(xy, nodes).tolist() == [2, 0, -1]   # 5 m off is another point, not this tower
    assert export.snap(xy, np.zeros((0, 2))).tolist() == [-1, -1, -1]


def test_water_runs_close_together_are_one_stretch():
    s = np.arange(0, 3000, 20.0)
    wet = np.zeros(len(s), bool)
    wet[(s >= 500) & (s < 1000)] = True
    wet[(s >= 1200) & (s < 1600)] = True      # an island 200 m wide: the same stretch
    wet[(s >= 2400) & (s < 2600)] = True      # 800 m on: another
    out = export.stretches(wet, s, merge_m=300)
    assert [(a, b) for a, b, _ in out] == [(500, 1580), (2400, 2580)]
    assert 0.8 < out[0][2] < 1.0 and out[1][2] == 1.0


# ------------------------------------------------------------------ the camera (pass 1)

from image_evidence.satellite.scene3d import camera  # noqa: E402

_OPEN = {"ground_m": 15, "hold_s": 1, "flight_s": 4, "start": {"view_km": 11, "lens_mm": 200},
         "flight": {"altitude_m": 120, "pitch_deg": -12, "lens_mm": 28, "speed_mps": 80},
         "variants": {"centred": {"tilt_s": 6}, "low": {"tilt_s": 6, "flight": {"altitude_m": 70, "pitch_deg": -7}}}}


def _corridor():
    # the midline north of where the lines cross: it jogs while they spread, then runs straight between them
    y = np.arange(2500, 9001, 50.0)
    x = 3000 + 0.3 * (y - 2500) + np.where(y < 3000, 150 * (3000 - y) / 500, 0)
    gap = np.where(y < 3100, 365 * (y - 2500) / 600, 365)
    return np.stack([x, y], 1), gap


def test_top_down_with_a_long_lens_is_the_2d_frame():
    st = camera.State((100.0, 200.0, 15.0), 0.0, -90.0, 11000.0, 200.0)
    assert st.position == pytest.approx([100, 200, 15 + 11000 * 200 / 36])
    assert st.blender()["rotation"] == pytest.approx([0, 0, 0])   # looking straight down, north up


def test_the_axis_ignores_the_jog_where_the_lines_spread():
    xy, gap = _corridor()
    c, d, off = camera.axis(xy, gap)
    assert off < 1.0
    assert camera.heading_of(d) == pytest.approx(np.degrees(np.arctan(0.3)), abs=0.01)


def test_the_tilt_lands_centred_on_the_axis_at_the_flights_speed():
    xy, gap = _corridor()
    c, d, _ = camera.axis(xy, gap)
    for v in _OPEN["variants"]:
        fr = camera.frames(v, _OPEN, (0, 0), xy, gap, 2500.0, 30)
        assert len(fr) == (1 + 6 + 4) * 30
        assert fr[0]["location"] == pytest.approx([0, 0, 15 + 11000 * 200 / 36])
        loc = np.array([f["location"] for f in fr])
        k = next(i for i, f in enumerate(fr) if f["phase"] == "flight")
        alt = 120 if v == "centred" else 70
        # at the landing: over the axis at the flight's height, and from then on along it, centred, at 80 m/s
        for f in fr[k:]:
            p = np.array(f["location"][:2])
            assert abs((p - c) @ np.array([-d[1], d[0]])) < 0.01   # positions are kept to the millimetre
            assert f["location"][2] == pytest.approx(15 + alt)
        speed = np.hypot(*np.diff(loc[:, :2], axis=0).T) * 30
        assert speed[k:] == pytest.approx(80, abs=0.1)
        # no stop on the way in: the camera keeps moving once it has started, and slows into the flight's speed
        moving = speed[30 + 5:k]
        assert moving.min() > 1.0
        assert abs(speed[k - 1] - 80) < 1
        dv = np.abs(np.diff(speed[k - 15:k + 15]))   # no jolt round the landing: the braking fades out into it
        assert np.all(np.diff(dv[:15]) <= 1e-6) and dv[14] < 0.5 and dv[15:].max() < 0.1



def test_an_approach_comes_onto_the_axis_before_the_landing_with_the_map_north_up():
    xy, gap = _corridor()
    c, d, _ = camera.axis(xy, gap)
    o = {**_OPEN, "variants": {"a": {"tilt_s": 8, "approach_m": 1500}}}
    fr = camera.frames("a", o, (0, 0), xy, gap, 2500.0, 30)
    loc = np.array([f["location"] for f in fr])
    off = np.abs((loc[:, :2] - c) @ np.array([-d[1], d[0]]))
    k = next(i for i, f in enumerate(fr) if f["phase"] == "flight")
    # on the axis well before the landing (the run up it), and only ever turning from north up to the axis's heading
    first = next(i for i in range(len(fr)) if off[i:].max() < 0.01)
    assert first < k - 30
    head = np.array([-np.degrees(f["rotation"][2]) for f in fr])
    assert np.all(np.diff(head) >= -1e-9) and head[0] == 0 and head[k:] == pytest.approx(camera.heading_of(d), abs=1e-6)
    speed = np.hypot(*np.diff(loc[:, :2], axis=0).T) * 30
    assert speed[k:] == pytest.approx(80, abs=0.1) and abs(speed[k - 1] - 80) < 1


def test_the_route_goes_on_up_the_axis_slows_hovers_stops_and_turns_round():
    xy, gap = _corridor()
    c, d, _ = camera.axis(xy, gap)
    o = {**_OPEN, "variants": {"a": {"tilt_s": 8, "approach_m": 1500}},
         "route": [{"north_km": 3.5, "speed_mps": 80},
                   {"north_km": 3.8, "speed_mps": 4, "altitude_m": 110, "phase": "slow"},
                   {"north_km": 3.9, "speed_mps": 4, "phase": "hover"},
                   {"north_km": 4.3, "speed_mps": 80, "altitude_m": 70},
                   {"north_km": 4.9, "speed_mps": 0, "phase": "stop"},
                   {"s": 6, "turn_deg": -180, "phase": "turn"}]}
    fr = camera.frames("a", o, (0, 0), xy, gap, 2500.0, 30)
    loc = np.array([f["location"] for f in fr])
    k = next(i for i, f in enumerate(fr) if f["phase"] == "flight")
    speed = np.hypot(*np.diff(loc[:, :2], axis=0).T) * 30
    # always on the axis, never backwards, the speed changing smoothly (no jump at a key)
    assert np.abs((loc[k:, :2] - c) @ np.array([-d[1], d[0]])).max() < 0.01
    assert np.all(np.diff(loc[k:, :2] @ d) > -1e-3)
    assert np.abs(np.diff(speed[k:])).max() < 1.0   # under 30 m/s² (a jump at a key would be tens of m/s in a frame)
    hover = [i for i, f in enumerate(fr) if f["phase"] == "hover"]
    assert speed[hover[0]:hover[-1]] == pytest.approx(4, abs=0.2)
    assert len(hover) == pytest.approx(30 * 2 * 100 / d[1] / 8, abs=2)   # 100 m north at 4 m/s
    assert loc[hover[0], 2] == pytest.approx(15 + 110)
    # the turn on the spot: to the left, ending looking back down the axis
    turn = [i for i, f in enumerate(fr) if f["phase"] == "turn"]
    head = np.array([-np.degrees(f["rotation"][2]) for f in fr])
    assert speed[turn[0]:turn[-1]].max() < 0.1
    assert np.all(np.diff(head[turn]) <= 1e-9)
    assert head[-1] == pytest.approx(camera.heading_of(d) - 180, abs=0.5)


def test_the_drain_and_the_fade_are_said_frame_by_frame_and_the_lift_stays_level():
    xy, gap = _corridor()
    o = {**_OPEN, "variants": {"a": {"tilt_s": 8, "approach_m": 1500}}, "drain_km": [3.2, 3.6], "fade_out_s": 2,
         "route": [{"north_km": 4.0, "speed_mps": 80}, {"north_km": 5.0, "speed_mps": 60, "altitude_m": 300}]}
    fr = camera.frames("a", o, (0, 0), xy, gap, 2500.0, 30)
    y = np.array([f["location"][1] for f in fr])
    drain = np.array([f["drain"] for f in fr])
    assert np.all(drain[y < 3200] == 0) and np.all(drain[y > 3600] == 1) and np.all(np.diff(drain) >= 0)
    k = next(i for i, f in enumerate(fr) if f["phase"] == "flight")
    speed = np.hypot(*np.diff(np.array([f["location"][:2] for f in fr]), axis=0).T) * 30
    assert speed[(y[:-1] > 3200) & (y[:-1] < 3600)].min() > 79   # no slowing for the drain
    assert [f["rotation"][0] for f in fr[k:]] == pytest.approx([np.radians(90 - 12)] * (len(fr) - k))   # level throughout
    assert fr[-1]["location"][2] == pytest.approx(15 + 300)
    fade = [f.get("fade", 0) for f in fr]
    assert fade[-1] == 1 and fade[-61] == 0 and fade[-58] > 0 and np.all(np.diff(fade) >= 0)


_NET_RECORD = {
    "start": "2022-02-24", "end": "2022-12-31", "run_s": 100,
    "lines": {"Dniprovska": ["Dniprovska", 750], "Ferosplavna-1": ["Ferosplavna 1, 2", 330, 0],
              "Zaporizka 750": ["Zaporizka", 750]},
    "groups": {"other 750": ["Zaporizka 750"]},
    "sources": {"s": {"title": "a source", "url": "https://example.org"}},
    "events": [{"at": "2022-02-24", "lines": "all", "to": "on", "src": ["s"]},
               {"at": "2022-03-03", "lines": "all", "to": "unknown", "src": ["s"]},
               {"at": "2022-08-25", "lines": "Dniprovska", "to": "on", "src": ["s"]},
               {"at": "2022-09-03", "lines": "Dniprovska", "to": "off", "src": ["s"]},
               {"at": "2022-09-17", "lines": "Dniprovska", "to": "on", "src": ["s"]},
               {"at": "2022-10-01", "lines": "other 750", "to": "off", "src": ["s"]},
               {"at": "2022-10-08", "loop": 2, "until": "2022-10-09", "src": ["s"]},
               {"at": "2022-10-12", "loop": 3, "brief": True, "src": ["s"]},
               {"at": "2022-11-01", "lines": "Ferosplavna-1", "to": "on", "src": ["s"]},
               {"at": "2022-12-01", "lines": "Dniprovska", "to": "off", "until": "2022-12-05", "src": ["s"]}]}
_3D = {"start": "2022-09-06", "within_day": "omit", "at_s": 2, "intro_s": 1, "run_s": 20, "min_hold_s": 1.3, "loss_hold_s": 2.0,
       "fade_on_s": 0.8, "fade_off_s": 0.4,
       "lines": {"Ferosplavna-1": {"drawn": "Ferosplavna 1, 2", "pan": -0.85, "label": "F"},
                 "Dniprovska": {"drawn": "Dniprovska", "pan": 0.85, "label": "D"}}}


def test_the_3d_record_starts_where_the_reports_leave_the_lines_and_leaves_out_what_is_over_within_the_day():
    rec, doc = states.record(_NET_RECORD, _3D)
    assert doc["first_states"] == {"Ferosplavna-1": "unknown", "Dniprovska": "off"}
    assert states.weights(rec, "Ferosplavna-1", 0) == [0, 1] and states.weights(rec, "Dniprovska", 0) == [0, 0]
    # the brief complete loss is listed as left out, never shown; the one lasting a day is shown (both lines cut)
    assert [e["at"] for e in doc["left_out"]["events"]] == ["2022-10-12"]
    t = rec.t(date(2022, 10, 8).toordinal()) + 0.5
    assert rec.state("Dniprovska", t) == "off" and rec.state("Ferosplavna-1", t) == "off"
    # another line's change is no moment of its own; every state held at least min_hold_s
    assert date(2022, 10, 1).toordinal() not in rec.changes
    assert np.diff(rec._ts).min() >= 1.3 - 1e-9
    # a line fades out and swells back, never snaps
    t_on = rec.t(date(2022, 9, 17).toordinal())
    assert 0 < states.weights(rec, "Dniprovska", t_on + 0.4)[0] < 1
    assert states.weights(rec, "Dniprovska", t_on + 0.9)[0] == 1


def test_a_span_begun_before_the_3d_starts_is_held_from_the_first_frame():
    net = {**_NET_RECORD, "events": _NET_RECORD["events"] + [
        {"at": "2022-09-05", "lines": "all", "to": "off", "until": "2022-09-10", "island": True, "src": ["s"]}]}
    rec, doc = states.record(net, _3D)
    end = rec.t(date(2022, 9, 10).toordinal())
    assert states.weights(rec, "Ferosplavna-1", 0) == [0, 0] and rec.in_island(0) and rec.in_island(end - 0.1)
    assert not rec.in_island(end + 0.1) and states.weights(rec, "Ferosplavna-1", end + 1.0) == [0, 1]  # grey again
    island = [e for e in doc["events"] if e["island"]][0]
    assert island["began"] == "2022-09-05" and island["film_s"][0] == 0.0
    pf = states.per_frame(rec, _3D, 30 * 5, 30)
    assert pf[30 * 3]["island"] == 1.0 and "island" not in pf[-1]


def test_the_frames_carry_the_states_and_the_date():
    rec, _ = states.record(_NET_RECORD, _3D)
    pf = states.per_frame(rec, _3D, 30 * 25, 30)
    assert pf[0]["date"] is None and pf[30 * 3]["date"] == "2022-09-06"
    assert set(pf[0]["lines"]) == {"Ferosplavna 1, 2", "Dniprovska"}
    assert states.date_label("2022-09-06") == "6 SEPTEMBER 2022"


def test_a_pinned_day_lands_on_its_time_steps_day_by_day_and_omitted_cuts_are_listed():
    o = {**_3D, "run_s": 30, "pins": [{"at": "2022-11-01", "s": 14, "min_hold_s": 0.5}, {"at": "2022-11-04", "s": 16}],
         "steps": ["2022-11-02", "2022-11-03"], "omit": [{"at": "2022-12-01", "lines": ["Dniprovska"]}]}
    rec, doc = states.record(_NET_RECORD, o)
    assert rec.t(date(2022, 11, 1).toordinal()) == pytest.approx(14)
    assert rec.t(date(2022, 11, 4).toordinal()) == pytest.approx(16)
    assert [rec.shown(t).isoformat() for t in (14.1, 14.8, 15.5)] == ["2022-11-01", "2022-11-02", "2022-11-03"]
    assert rec.days(15.0) == pytest.approx(date(2022, 11, 2).toordinal() + 0.5, abs=0.3)   # the day runs on smoothly
    left = [e for e in doc["left_out"]["events"] if "omit" in e["why"]]
    assert [e["at"] for e in left] == ["2022-12-01"]
    assert rec.state("Dniprovska", rec.t(date(2022, 12, 2).toordinal())) == "on"   # never shown, listed instead


def test_the_hum_puts_each_line_on_its_side():
    rec, _ = states.record(_NET_RECORD, _3D)
    pans = {k: v["pan"] for k, v in _3D["lines"].items()}
    both = rec.t(date(2022, 11, 1).toordinal())   # both connected from here: the level's reference
    x, _ = hum.score(rec, pans, {"Dniprovska": 750, "Ferosplavna-1": 330}, 25.0, 1.0, start_s=0.5, fade_in_s=1.0,
                     follow=(0.6, 0.3), ref_s=(both + 1.5, both + 2.5))

    def lr(t):
        seg = x[int(t * hum.SR):int((t + 0.5) * hum.SR)]
        return np.sqrt((seg ** 2).mean(0))

    # September: only Dniprovska (right) connected; Ferosplavna-1 unreported, muffled on the left
    l, r = lr(rec.t(date(2022, 9, 17).toordinal()) + 1.2)
    assert r > 2.5 * l
    # the complete loss lasting a day: silence, once the lines have faded out (0.3 s, not a snap)
    l2, r2 = lr(rec.t(date(2022, 10, 8).toordinal()) + 1.2)
    assert max(l2, r2) < 0.05 * r
    # from November both connected: the left side clearly louder
    l3, r3 = lr(both + 1.5)
    assert l3 > 1.8 * l   # (Dniprovska leaks a little into the left: panned 0.85, not hard right)


# ------------------------------------------------------------------ pass 4: the towers

def _tower(x, y, kind="750", node=1, **tags):
    return {"xy": [x, y], "ground_m": 15.0, "kind": kind, "osm_node": node, "tags": tags}


def _crossing_line():
    # a 750 kV line from the plant's gantry north over the water: К-П-П-А-П-П-К as the sources give it
    tw = [_tower(0, 0, "portal", None), _tower(0, 400), _tower(0, 800, triple_tower="yes")]
    tw += [_tower(0, 800 + 1250 * k, "crossing", 10 + k) for k in range(1, 6)]
    tw += [_tower(0, 800 + 1250 * 6, triple_tower="yes"), _tower(300, 9000), _tower(300, 9400)]
    return {"name": "D", "kv": 750, "towers": tw}


def _placed(lines):
    for ln in lines:
        drawn = [t for t in ln["towers"] if t["type"]]
        for t, rz in zip(drawn, towers.headings(drawn)):
            t["rot_z"], t["base_m"] = rz, t["ground_m"] + (towers.WATER_UP_M if t["caisson"] else 0.0)
    return lines


def test_the_towers_are_the_heights_the_sources_give():
    types = towers.build_types()
    top = {k: float(m.arrays()["v"][:, 2].max()) for k, (m, _) in types.items()}
    assert top["crossing750_p"] == pytest.approx(126, abs=0.5)
    assert top["crossing750_a"] == pytest.approx(100, abs=0.5)
    assert top["crossing330"] == pytest.approx(100, abs=0.5)
    # no. 23's second crossbar at 113 m: the main arm's top chord at the body
    v = types["crossing750_p"][0].arrays()["v"]
    assert np.isclose(v[:, 2], 113.0, atol=0.3).any()
    # no. 19's crossbars at 92, 81 and 70 m: each phase's tension sets leave from just under one
    for c in types["crossing330"][1]["circuits"]:
        for back, fwd in c:
            z = min((92, 81, 70), key=lambda h: abs(h - back[2]))
            assert 0 < z - back[2] < 3 and back[2] == fwd[2]
    # the crossarms as photographed: flat on top, their bottom chords rising toward the tips
    m = towers.Mesh()
    tip = towers.arm(m, 113.0, 9.0, 3.0, 19.0, 1, 3.0, tip_depth=1.1)
    v = m.arrays()["v"]
    near, far = v[v[:, 0] < 3.5], v[v[:, 0] > 18.5]
    assert near[:, 2].max() == pytest.approx(far[:, 2].max(), abs=0.3) == pytest.approx(113, abs=0.3)  # level on top
    assert far[:, 2].min() - near[:, 2].min() > 6                            # deep at the body, shallow at the tip
    assert tip[2] == pytest.approx(111.9)
    # each caisson is wider at its top than the tower standing on it (corner to corner)
    for t, c in (("crossing750_p", "caisson750"), ("crossing330", "caisson330")):
        r_top = np.hypot(*types[c][0].arrays()["v"][:, :2].T)[types[c][0].arrays()["v"][:, 2] > 2.9].min()
        assert r_top > types[t][1]["base_hw"] * np.sqrt(2)


def test_each_tower_is_its_type_by_its_tags_and_its_crossings_scheme():
    ln = _crossing_line()
    ln["towers"].insert(-1, _tower(150, 8800, "portal", None))   # a bend of the way with no tower mapped
    towers.assign([ln], {"D": "К-П-П-А-П-П-К"})
    ty = [t["type"] for t in ln["towers"]]
    assert ty == ["gantry750", "pp750", "triple750", "crossing750_p", "crossing750_p", "crossing750_a",
                  "crossing750_p", "crossing750_p", "triple750", "pp750", None, "pp750"]
    # the shore towers stand on land, the three between them in the water
    assert [bool(t["caisson"]) for t in ln["towers"][3:8]] == [False, True, True, True, False]
    with pytest.raises(ValueError, match="scheme"):   # five crossing towers, a scheme with seven: refused
        towers.assign([_crossing_line()], {"D": "К-А-А-А-А-А-А-А-К"})
    bad = _crossing_line()
    bad["towers"][2]["tags"] = {}
    with pytest.raises(ValueError, match="triple_tower"):   # the crossing's end isn't a triple tower in OSM
        towers.assign([bad], {"D": "К-П-П-А-П-П-К"})
    cut = _crossing_line()
    cut["towers"].append(_tower(150, 9900, "portal", None))   # where the land's box cuts the line: no switchyard there
    cut["cut"] = True
    towers.assign([cut], {"D": "К-П-П-А-П-П-К"})
    assert cut["towers"][0]["type"] == "gantry750" and cut["towers"][-1]["type"] is None


def test_a_line_is_cut_where_it_leaves_the_window_and_says_so():
    a = np.array([[0, -2000], [0, 0], [100, 5000], [300, 12000], [200, 30000]], float)
    part, was_cut = export._window(a, -1500.0, 27000.0)
    assert was_cut and len(part) == 5 and part[-1][1] == 30000   # the vertex beyond kept, flagged as cut
    whole, was_cut = export._window(a[1:4], -1500.0, 27000.0)
    assert not was_cut and len(whole) == 3


def test_the_wires_hang_from_the_towers_attachment_points():
    ln = _crossing_line()
    towers.assign([ln], {"D": "К-П-П-А-П-П-К"})
    lines = _placed([ln])
    types = towers.build_types()
    attach = {k: a for k, (_, a) in types.items()}
    ws = towers.wires(lines, attach, {"span": 1800.0, "crossing": 4200.0})
    ends = np.array([p for w in ws if w["kind"] in ("bundle", "earth") for p in (w["pts"][0], w["pts"][-1])])
    points = []
    for t in lines[0]["towers"]:
        if t["type"]:
            a = attach[t["type"]]
            points += [towers._world(t, q) for c in a["circuits"] for ph in c for q in ph]
            points += [towers._world(t, q) for q in a["earth"]]
    points = np.array(points)
    # every bundle and earth wire starts and ends at a modelled attachment point
    assert max(np.linalg.norm(points - e, axis=1).min() for e in ends) < 1e-6
    # each bundle's five sub-conductors hang round its centre, 0.6 m apart, from end to end
    for g in {w["group"] for w in ws if w["kind"] == "bundle"}:
        mine = [w["pts"] for w in ws if w.get("group") == g and w["kind"] in ("phase", "jumper")]
        centre = next(w["pts"] for w in ws if w.get("group") == g and w["kind"] == "bundle")
        assert len(mine) == 5
        for i in (0, -1):
            d = [np.linalg.norm(p[i] - centre[i]) for p in mine]
            assert np.allclose(d, 0.51, atol=0.01)
            assert np.linalg.norm(mine[0][i] - mine[1][i]) == pytest.approx(0.6, abs=0.01)
    # three conductors and two earth wires in every span
    spans = len([t for t in lines[0]["towers"] if t["type"]]) - 1
    assert sum(w["kind"] == "earth" for w in ws) == 2 * spans
    # between the crossing towers the conductors sag tens of metres and stay well above the water
    water = [w for w in ws if w["kind"] == "bundle" and np.ptp(w["pts"][:, 1]) > 1000
             and min(w["pts"][0][2], w["pts"][-1][2]) > 90]
    sag = [min(w["pts"][0][2], w["pts"][-1][2]) - w["pts"][:, 2].min() for w in water]
    assert water and min(sag) > 20 and all(w["pts"][:, 2].min() > 15 + 30 for w in water)


def test_a_single_circuit_meets_the_double_circuit_crossing_on_the_nearer_side():
    tw = [_tower(-30, 0, "330", 1), _tower(0, 300, "330", 2, triple_tower="yes")]
    tw += [_tower(0, 300 + 850 * k, "crossing", 10 + k) for k in range(1, 8)]
    tw += [_tower(0, 300 + 850 * 8, "330", 3, triple_tower="yes")]
    ln = {"name": "F", "kv": 330, "towers": tw}
    towers.assign([ln], {"F": "К-А-А-А-А-А-А-А-К"})
    assert ln["towers"][0]["type"] == "pvs330" and ln["towers"][1]["type"] == "triple330"
    lines = _placed([ln])
    attach = {k: a for k, (_, a) in towers.build_types().items()}
    ws = towers.wires(lines, attach, {"span": 1800.0, "crossing": 4200.0})
    first = [w for w in ws if w["kind"] == "bundle" and w["pts"][0][1] < 100]
    assert len(first) == 3                                   # the land circuit's three phases only
    crossing = [w for w in ws if w["kind"] == "bundle" and np.ptp(w["pts"][:, 1]) > 800]
    assert len(crossing) == 6 * 8                            # both circuits from end tower to end tower
    assert sum(w["kind"] == "phase" for w in ws) == 2 * sum(w["kind"] == "bundle" and np.ptp(w["pts"][:, 1]) > 100
                                                            for w in ws)   # two sub-conductors a phase


def test_the_spans_carry_spacers_and_dampers():
    ln = _crossing_line()
    towers.assign([ln], {"D": "К-П-П-А-П-П-К"})
    lines = _placed([ln])
    ws = towers.wires(lines, {k: a for k, (_, a) in towers.build_types().items()}, {"span": 1800.0, "crossing": 4200.0})
    v = towers.fittings(ws, [750]).arrays()["v"]
    # every sub-conductor and earth wire of a real span has a damper 2 m out from each clamp, the weights below it
    long = [w for w in ws if w["kind"] in ("phase", "earth") and towers._along(w["pts"])[-1] > 150]
    for w in long[:20]:
        for end, nxt in ((w["pts"][0], w["pts"][1]), (w["pts"][-1], w["pts"][-2])):
            p = end + 2.0 * (nxt - end) / np.linalg.norm(nxt - end)
            near = v[np.linalg.norm(v - p, axis=1) < 0.6]
            assert len(near) and near[:, 2].min() < p[2] - 0.1
    # a 1250 m crossing span's bundle is held apart about every 55 m, never within 25 m of a clamp
    w = next(w for w in ws if w["kind"] == "bundle" and np.ptp(w["pts"][:, 1]) > 1200)
    on = v[np.abs(v[:, 0] - w["pts"][0][0]) < 1.5]
    ys = np.unique(np.round(on[:, 1] - w["pts"][0][1]))
    inner = ys[(ys > 25) & (ys < np.ptp(w["pts"][:, 1]) - 25)]
    assert inner.size and np.diff(np.unique(np.round(inner / 5) * 5)).max() <= 60


def test_the_flow_runs_the_way_its_sources_say():
    fo = {"dash_m": 60, "speed_mps": 90, "periods": [
        {"from": "2021-01-01", "until": "2022-09-05", "toward": "grid"},
        {"from": "2022-09-06", "toward": "plant"}]}
    assert states.flow_toward(fo, "2022-03-01") == -1      # out to the grid (backward along: -1 runs away from the plant)
    assert states.flow_toward(fo, "2024-04-06") == 1       # in to the plant
    assert states.flow_toward(fo, None) == -1              # before a date is shown: the first period's
    assert states.flow_toward({**fo, "periods": fo["periods"][1:]}, "2020-01-01") == 0   # none covered: none drawn


def test_every_wire_point_knows_how_far_along_its_line_it_is():
    ln = _crossing_line()
    towers.assign([ln], {"D": "К-П-П-А-П-П-К"})
    lines = _placed([ln])
    ws = towers.wires(lines, {k: a for k, (_, a) in towers.build_types().items()}, {"span": 1800.0, "crossing": 4200.0})
    for w in ws:
        assert len(w["along"]) == len(w["pts"])
    spans = [w for w in ws if w["kind"] == "bundle" and len(w["pts"]) > 11]
    # from the plant end outward, each span picking up where the one before ended
    starts = sorted({round(float(w["along"][0])) for w in spans})
    assert starts[0] == 0 and all(b > a for a, b in zip(starts, starts[1:]))
    for w in spans:
        assert np.all(np.diff(w["along"]) > 0)
        # tower to tower: the wire itself starts and ends on its tension sets, metres out
        assert w["along"][-1] - w["along"][0] == pytest.approx(np.linalg.norm(np.ptp(w["pts"][:, :2], axis=0)), abs=20)


def test_the_flow_is_fullest_over_the_crossing_and_fainter_on_land():
    ln = _crossing_line()
    towers.assign([ln], {"D": "К-П-П-А-П-П-К"})
    lines = _placed([ln])
    ws = towers.wires(lines, {k: a for k, (_, a) in towers.build_types().items()}, {"span": 1800.0, "crossing": 4200.0})
    for w in ws:
        assert len(w["cross"]) == len(w["pts"]) and np.all((w["cross"] >= 0) & (w["cross"] <= 1))
    spans = sorted((w for w in ws if w["kind"] == "bundle" and len(w["pts"]) > 11), key=lambda w: w["along"][0])
    mid = spans[len(spans) // 2]
    assert np.all(mid["cross"] == 1)       # between the crossing towers
    assert spans[0]["cross"][0] == 0        # out on land
    # by the surveyed water when given: full over it, none 150 m beyond its shores
    ws = towers.wires(lines, {k: a for k, (_, a) in towers.build_types().items()}, {"span": 1800.0, "crossing": 4200.0},
                      {ln["name"]: [(3000.0, 5000.0)]})
    for w in ws:
        y = w["pts"][:, 1]
        assert np.all(w["cross"][(y > 3000) & (y < 5000)] == 1)
        assert np.all(w["cross"][(y < 2850) | (y > 5150)] == 0)


# ------------------------------------------------------------------ pass 3: the bed


def test_the_level_falls_between_its_reports_and_baltic_heights_are_raised_to_the_geoid(tmp_path):
    b = {"baltic_m": 0.4, "levels": [{"at": "2023-06-05T00:00:00Z", "m": 16.8, "datum": "baltic"},
                                     {"at": "2023-06-07T00:00:00Z", "m": 13.0, "datum": "baltic"},
                                     {"at": "2023-06-20T00:00:00Z", "m": 9.3}]}
    lv = bed.series(b, tmp_path)
    assert [p["m"] for p in lv] == [17.2, 13.4, 9.3]
    assert bed.level(lv, "2023-06-06T00:00:00Z") == pytest.approx(15.3)
    assert bed.level(lv, "2023-01-01") == 17.2 and bed.level(lv, "2024-01-01") == 9.3   # held either side


def test_each_pixel_dries_once_where_its_passes_disagree_least():
    wet = np.array([[1, 1, 0, 1, 1], [1, 0, 0, 1, 1], [1, 0, 0, 1, 0]], bool)[:, :, None]   # (3 passes, 5 px, 1)
    known = np.ones_like(wet)
    known[1, 4] = False
    k = bed.emergence(wet, known)[:, 0]
    # never dry, dry from the 2nd pass, from the 1st, never, and from the 2nd (unseen then, dry on the 3rd: the earliest)
    assert list(k) == [3, 1, 0, 3, 1]
    noisy = np.array([[1, 0, 1, 0, 0]], bool).T[:, :, None]   # a wet blip after drying: one disagreement, not two drynesses
    assert bed.emergence(noisy, np.ones_like(noisy))[0, 0] == 1


def test_the_bed_lies_between_the_levels_either_side_of_when_it_dried():
    k = np.array([[0, 0, 1, 1, 2, 2, 2, 1, 0]] * 3, np.int16)
    inside = np.ones(k.shape, bool)
    inside[:, 0] = False
    z = bed.surface(k, inside, [14.0, 10.0], 17.0, 20.0)
    row = z[1]
    assert np.isnan(row[0])
    assert 14 <= row[1] <= 17 and np.all((row[2:4] <= 14) & (row[2:4] >= 10))
    assert np.all(row[4:7] < 10) and row[5] <= row[4]                      # never dry: under the last level, sloping in
    assert row[2] > row[3]                                                  # higher toward the shore
    held, used = bed.constrain(z, k, inside, [14.0, 10.0], 17.0, [(1, 3, 5.0, 1.0)], 20.0)
    assert held[1, 3] == pytest.approx(10.0)            # pulled toward the measured 5 m, but never out of its band
    assert used[0]["band_m"] == [10.0, 14.0]


def test_the_bed_imagery_arrives_on_its_date_and_the_one_before_leaves():
    ly = [{"acquired": "2021-09-08"}, {"acquired": "2023-06-20", "shown_from": "2023-06-07", "fade_days": 1},
          {"acquired": "2023-08-19"}]
    d = lambda s: date.fromisoformat(s).toordinal()
    assert bed.texture_weights(ly, d("2023-06-01"), 40) == [1, 0, 0]
    assert bed.texture_weights(ly, d("2023-06-07"), 40) == [0, 1, 0]
    mid = bed.texture_weights(ly, d("2023-07-30"), 40)
    assert sum(mid) == pytest.approx(1) and 0 < mid[1] < 1 and 0 < mid[2] < 1
    assert bed.texture_weights(ly, d("2023-08-19"), 40) == [0, 0, 1]


def test_the_caisson_stands_its_top_above_the_old_pool_and_its_base_on_the_bed():
    m, _ = towers.caisson(21.8, 14.5)
    v = m.arrays()["v"]
    assert v[:, 2].max() == pytest.approx(towers.WATER_UP_M)
    assert v[:, 2].min() == pytest.approx(-towers.CAISSON_DOWN_M)
    assert np.hypot(v[:, 0], v[:, 1]).max() == pytest.approx(21.8 + 0.45, abs=0.5)   # 43.6 m across, its ribs proud


def test_a_caissons_disc_takes_the_bed_round_it():
    z = np.full((9, 9), 8.0, np.float32)
    z[3:6, 3:6] = 12.0   # the caisson and its sand, seen dry from the first pass
    hole = np.zeros(z.shape, bool)
    hole[3:6, 3:6] = True
    assert np.allclose(bed._fill(z, hole, ring_px=2)[3:6, 3:6], 8.0)


def test_narrow_channels_under_plants_are_water_by_their_dark_swir():
    h, w = 40, 60
    g, nir, sw = (np.full((h, w), v, np.float32) for v in (600, 2500, 1800))   # willows and reeds
    sw[:, 30] = 700                                     # a channel a pixel wide: too mixed for MNDWI
    g[:, 30], nir[:, 30] = 500, 1700
    g[5:10, 5:15], nir[5:10, 5:15], sw[5:10, 5:15] = 800, 300, 150   # open water
    sw[20, 50] = 600                                    # a single dark pixel: a speck, dropped
    m = bed.channels(g, nir, sw, np.ones((h, w), bool))
    assert m[:, 30].all() and m[5:10, 5:15].all()
    assert not m[20, 50] and m.sum() == h + 50


def test_once_settled_the_reservoirs_sheet_sinks_away_under_the_water_seen():
    doc = {"levels": [{"at": "2023-06-05T00:00:00Z", "m": 17.2}, {"at": "2023-06-11T00:00:00Z", "m": 9.0},
                      {"at": "2023-06-17T00:00:00Z", "m": 9.3}],
           "drawn": {"cap_m": 8.9, "cap_from": "2023-06-11T00:00:00Z", "cap_at": "2023-06-17T00:00:00Z"},
           "reference": {"level_m": 17.2}, "river_slope": {"m_per_deg_lon": 0.0, "settled_m": 8.9},
           "grid": {"bbox": [34.4, 47.4, 34.9, 47.7]}}
    t = lambda s: bed._t(s)
    assert bed.drawn(doc, t("2023-06-17T00:00:00Z"))[0] == pytest.approx(8.9)
    assert bed.drawn(doc, t("2023-06-18T00:00:00Z"))[0] == pytest.approx(8.9 - bed.HANDOVER_M / 2)
    assert bed.drawn(doc, t("2024-06-01T00:00:00Z"))[0] == pytest.approx(8.9 - bed.HANDOVER_M)
    assert bed.drawn(doc, t("2024-06-01T00:00:00Z"), handover=False)[0] == pytest.approx(8.9)   # the river as seen


def test_the_flight_south_runs_down_the_axis_curves_off_its_own_way_and_fades_in_and_out():
    xy, gap = _corridor()
    o = {**_OPEN, "variants": {"s": {
        "fade_in_s": 1, "fade_out_s": 1, "flight": {"altitude_m": 70, "pitch_deg": -7, "lens_mm": 35, "speed_mps": 80},
        "track": {"start_north_km": 8.5, "leave_north_km": 4.0, "end_xy_m": [1500, 1500], "end_heading_deg": 253,
                  "start": {"altitude_m": 300, "speed_mps": 45},
                  "rise": {"from": {"curve": 0.0}, "to": {"curve": 1.0}, "altitude_m": [70, 320], "pitch_deg": [-7, -9]}},
        "route": [{"north_km": 7.5, "speed_mps": 80, "altitude_m": 70}, {"north_km": 4.0, "speed_mps": 80},
                  {"curve": 1.0, "speed_mps": 12}, {"beyond_m": 20, "speed_mps": 6}]}}}
    fr = camera.frames_track("s", o, xy, gap, 30)
    c, d, _ = camera.axis(xy, gap)
    pos = np.array([f["location"][:2] for f in fr])
    head = np.array([-np.degrees(f["rotation"][2]) for f in fr]) % 360
    on = pos[:, 1] > 4100   # down the axis, facing south along it (the flight north's heading turned round)
    assert np.abs((pos[on] - c) @ np.array([-d[1], d[0]])).max() < 1.0
    assert head[on] == pytest.approx((camera.heading_of(d) + 180) % 360, abs=0.01)
    step = np.diff(pos, axis=0)
    moving = np.hypot(*step.T) > 0.05
    travel = np.degrees(np.arctan2(step[:, 0], step[:, 1])) % 360
    assert np.abs((travel - head[:-1] + 180) % 360 - 180)[moving].max() < 1.5   # it faces the way it goes, never crabbing
    assert head[-1] == pytest.approx(253, abs=0.1)
    z = np.array([f["location"][2] for f in fr])
    assert z[0] == pytest.approx(315) and z[-1] == pytest.approx(335) and np.all(np.diff(z[~on][1:]) >= -1e-6)
    fade = [f.get("fade", 0) for f in fr]
    assert fade[0] > 0.9 and fade[31] == 0 and fade[-1] == 1


def test_a_variants_record_puts_the_lines_on_their_sides_and_keeps_the_rest():
    c3 = {"record": {**_3D, "at_s": 2}}
    o = states.options(c3, {"record": {"at_s": 5, "lines": {"Dniprovska": {"pan": -0.85}, "Ferosplavna-1": {"pan": 0.85}}}})
    assert o["at_s"] == 5 and o["run_s"] == 20
    assert o["lines"]["Dniprovska"] == {"drawn": "Dniprovska", "pan": -0.85, "label": "D"}
    assert states.options(c3, {"record": True}) == {**c3["record"], "lines": c3["record"]["lines"]}


def test_the_plant_is_drawn_at_the_heights_published_and_its_footprints_face_out():
    from image_evidence.satellite.scene3d import plant

    def way(i, tags, pts):
        return {"type": "way", "id": i, "tags": tags, "geometry": [{"lon": x, "lat": y} for x, y in pts]}

    sq = lambda x, y, r: [(x - r, y - r), (x + r, y - r), (x + r, y + r), (x - r, y + r), (x - r, y - r)]
    circle = lambda x, y, r: [(x + r * np.cos(t), y + r * np.sin(t)) for t in np.linspace(0, 2 * np.pi, 25)]
    els = [way(1, {"power": "plant", "plant:source": "nuclear"}, sq(0, 0, 900)),
           *[way(10 + k, {"power": "generator", "generator:source": "nuclear", "height": "40"}, circle(0, 150 * k, 22.5))
             for k in range(2)],
           {"type": "node", "id": 20, "tags": {"man_made": "chimney"}, "lon": 40.0, "lat": 20.0},
           way(30, {"man_made": "chimney", "height": "320"}, circle(3000, 0, 13)),
           way(40, {"building": "yes", "man_made": "tower", "tower:type": "cooling"}, circle(-1400, 1400, 43)),
           way(50, {"building": "apartments", "building:levels": "9"}, sq(4000, -2000, 30)),
           way(51, {"building": "garages"}, list(reversed(sq(4100, -2000, 10))))]
    m, doc = plant.build({"reply": {"elements": els}}, lambda ll: np.asarray(ll, float), lambda q: 20.0)
    v = np.array(m.v)
    assert doc["counts"] == {"units": 2, "buildings": 2, "heights": {"osm_height": 0, "osm_levels": 1, "typical": 1},
                             "stacks": 1, "chimneys": 1, "cooling_towers": 1}
    assert v[:, 2].max() == pytest.approx(20 + 320)
    near = lambda x, y, r: v[np.hypot(v[:, 0] - x, v[:, 1] - y) < r]
    assert near(0, 0, 23)[:, 2].max() == pytest.approx(20 + plant.DOME_TOP, abs=0.1)   # the dome's published top
    assert near(-1400, 1400, 45)[:, 2].max() == pytest.approx(20 + plant.COOLING_M)
    assert near(4000, -2000, 45)[:, 2].max() == pytest.approx(20 + 9 * 3 + 1)
    assert near(4100, -2000, 15)[:, 2].max() == pytest.approx(20 + plant.TYPICAL["garages"])
    k0 = 0   # every flat roof faces up, whichever way OSM's ring runs
    for n, mat in zip(m.counts, m.mat):
        f = v[m.loops[k0:k0 + n]]
        k0 += n
        if n > 4 and np.ptp(f[:, 2]) < 1e-6 and f[0, 2] > 21:
            nz = np.sum((f[:, 0] - np.roll(f[:, 0], -1)) * (f[:, 1] + np.roll(f[:, 1], -1)))   # twice its area, + facing up
            assert nz > -1e-6


# ------------------------------------------------------------------ the flight south's other lines

class _FlatPlane:
    def xy(self, coords):
        return np.asarray(coords, dtype=float)


def test_the_other_rows_run_out_from_the_plant_part_from_a_shared_row_and_stop_at_the_land():
    net = {"lines": [{"name": "A", "kv": 750, "coords": [[800, 3000], [0, 1000], [0, 500], [0, 0]]}],
           "feeds": [{"coords": [[0, 100], [0, 600]]}], "links": []}
    oc = {"lines": [{"name": "A", "kv": 750, "record": "A 750"}], "feeds": {"follows": "Dniprovska"}}
    rows = export.other_rows(net, oc, _FlatPlane(), (-1000, -1000, 600, 5000), [np.array([[0, 0], [0, 1000]])])
    assert [r["name"] for r in rows] == ["A 750"]   # the feed lies wholly on the drawn row: left out
    a = rows[0]
    assert a["xy"].tolist() == [[0, 1000], [800, 3000]]   # from the tower where it parts, out from the plant
    assert a["hidden_first"] and a["cut"] and a["record"] == "A 750"


def test_the_other_lines_states_follow_the_date_shown_and_the_feeds_follow_their_line():
    rec, _ = states.record(_NET_RECORD, _3D)
    frames = states.per_frame(rec, _3D, 30 * 25, 30)
    rows = [{"name": "Zaporizka 750", "record": "Zaporizka 750"}, {"name": "feed 1", "follows": "Dniprovska"}]
    out = states.others_per_frame(_NET_RECORD, _3D, rows, rec, frames, 30)
    assert out[30 * 3]["Zaporizka 750"] == [0, 1]   # unreported which lines were cut: unknown
    late = [i for i, f in enumerate(frames) if f["date"] and f["date"] >= "2022-10-03"]
    assert late and all(out[i]["Zaporizka 750"] == [0, 0] for i in late)
    assert all(out[i]["feed 1"] == list(frames[i]["lines"]["Dniprovska"]) for i in range(0, len(frames), 30))


def test_a_line_with_no_crossing_scheme_gets_land_types_and_refuses_crossing_towers():
    ln = {"name": "Z", "kv": 750, "towers": [_tower(0, 0, "portal", None), _tower(0, 400, node=2), _tower(0, 800, node=3)]}
    towers.assign([ln], {})
    kinds = [t["type"] for t in ln["towers"]]
    assert kinds[0] == "gantry750" and all(k and not k.startswith("crossing") for k in kinds)
    bad = {"name": "Z", "kv": 750, "towers": [_tower(0, 0, "portal", None), _tower(0, 400, "crossing", 2)]}
    with pytest.raises(ValueError, match="no crossing scheme"):
        towers.assign([bad], {})
