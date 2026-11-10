"""Look pass 3 (south_look3): the record on selected dates, the variant's flow periods, the shoreline drawn sub-pixel."""
import numpy as np
import pytest

from image_evidence.satellite.scene3d import look, states

NET = {
    "lines": {"D": {"kv": 750}, "F": {"kv": 330}},
    "sources": {"a": "https://example.org/a", "b": "https://example.org/b"},
    "events": [
        {"at": "2022-03-04", "lines": "all", "to": "unknown", "src": ["a"]},
        {"at": "2022-09-05", "until": "2022-09-10", "loop": False, "lines": "all", "to": "off", "island": True, "src": ["a"]},
        {"at": "2022-09-16", "lines": ["D"], "to": "on", "src": ["b"]},
        {"at": "2023-01-17", "lines": ["F"], "to": "on", "src": ["b"]},
        {"at": "2023-03-01", "lines": ["F"], "to": "off", "src": ["a"]},
        {"at": "2023-03-01", "until": "2023-03-01", "lines": ["D"], "to": "off", "src": ["a"]},   # over within the day
        {"at": "2025-09-23", "until": "2025-11-08", "loop": True, "src": ["b"]},
        {"at": "2025-11-08", "lines": "all", "to": "on", "src": ["b"]},
    ],
}
O = {"lines": {"D": {}, "F": {}}, "at_s": 1.0, "fade_on_s": 0.6, "fade_off_s": 0.25, "ramp_s": 1.0}


def test_a_days_state_is_the_records_lasting_one_and_spans_override_it():
    s = lambda day: states.day_states(NET, ["D", "F"], day)
    assert s("2022-02-24")["states"] == {"D": "on", "F": "on"}
    assert s("2022-03-04")["states"] == {"D": "unknown", "F": "unknown"}
    i = s("2022-09-06")
    assert i["states"] == {"D": "off", "F": "off"} and i["island"] and not i["loss"]
    assert s("2022-09-16")["states"] == {"D": "on", "F": "unknown"}
    m = s("2023-03-01")
    assert m["states"] == {"D": "on", "F": "off"}           # D's outage within the day is not the day's state
    assert m["within_day"] and m["within_day"][0]["lines"] == ["D"]
    assert m["set_by"]["F"]["sources"] == ["a"]
    loss = s("2025-09-23")
    assert loss["states"] == {"D": "off", "F": "off"} and loss["loss"]
    assert s("2025-11-08")["states"] == {"D": "on", "F": "on"} and not s("2025-11-08")["loss"]


def _sel(entries):
    return states.Selected(NET, {**O, "select": entries})


def test_the_selection_shows_each_dates_state_and_nothing_between():
    r = _sel([{"at": "2022-02-24", "s": 1, "expect": {"D": "on", "F": "on"}},
              {"at": "2022-09-06", "s": 5, "island": True},
              {"at": "2022-09-16", "s": 9, "expect": {"D": "on", "F": "unknown"}},
              {"at": "2025-09-23", "s": 13, "loss": True},
              {"at": "2025-11-08", "s": 20}])
    assert r.shown(0.5) is None and str(r.shown(1.0)) == "2022-02-24" and str(r.shown(8.99)) == "2022-09-06"
    assert [r.state("D", t) for t in (2, 6, 10, 15, 21)] == ["on", "off", "on", "off", "on"]
    assert list(r.states("F", np.array([2, 6, 10]))) == ["on", "off", "unknown"]
    assert r.in_island(6) and not r.in_island(10) and r.on_diesel(15) and not r.on_diesel(21)
    assert r.mix("D", 5.1)["on"] > 0 and r.mix("D", 5.5) == {"off": 1.0}   # a cut dims in 0.25 s
    assert 0 < r.mix("D", 9.3)["on"] < 1 and r.mix("D", 9.7) == {"on": 1.0}   # a reconnection swells over 0.6 s
    doc = r.doc()
    assert doc["statement"] == states.SELECT_STATEMENT and "selected dates" in doc["statement"]
    assert [d["film_s"][0] for d in doc["dates"]] == [1, 5, 9, 13, 20] and doc["dates"][-1]["film_s"][1] is None


def test_a_selection_the_record_does_not_bear_out_is_refused():
    with pytest.raises(ValueError, match="not forced"):
        _sel([{"at": "2022-09-16", "s": 1, "expect": {"F": "on"}}])
    with pytest.raises(ValueError, match="island"):
        _sel([{"at": "2022-09-16", "s": 1, "island": True}])
    with pytest.raises(ValueError, match="complete loss"):
        _sel([{"at": "2025-11-08", "s": 1, "loss": True}])
    with pytest.raises(ValueError, match="dates out of order"):
        _sel([{"at": "2023-01-17", "s": 1}, {"at": "2022-09-16", "s": 2}])


def test_the_days_ease_to_each_new_date_or_run_on_day_by_day():
    r = _sel([{"at": "2023-06-06", "s": 1, "run": True}, {"at": "2023-06-16", "s": 6},
              {"at": "2023-07-01", "s": 10}])
    d0 = r.entries[0]["at"]
    assert r.days(1.0) == d0 and r.days(3.5) == pytest.approx(d0 + 5)   # running on through the falling water
    assert r.days(6.0) == d0 + 10                                         # after a run, no ease: it is there
    assert r.days(10.0) == d0 + 10 and r.days(10.5) == pytest.approx(d0 + 17.5) and r.days(11.2) == d0 + 25


def test_the_variants_flow_periods_come_first_and_the_shared_ones_stay():
    fo = {"dash_m": 30, "speed_mps": 20, "periods": [{"from": "2022-09-16", "toward": "plant", "src": ["b"]}]}
    assert states.flow_config(fo, {}) is fo                                # the approved films: unchanged
    assert states.flow_toward(fo, None) == 1                               # before the date: the first period's
    v = {"flow_periods": [{"from": "2021-09-01", "until": "2022-09-11", "toward": "grid", "src": ["a"]}]}
    f3 = states.flow_config(fo, v)
    assert fo["periods"] == [{"from": "2022-09-16", "toward": "plant", "src": ["b"]}]   # not changed in place
    assert states.flow_toward(f3, None) == -1 and states.flow_toward(f3, "2022-02-24") == -1
    assert states.flow_toward(f3, "2022-09-13") == 0 and states.flow_toward(f3, "2023-03-01") == 1


def test_the_shoreline_drawn_sub_pixel_stays_within_half_a_pixel_of_the_mask():
    yy, xx = np.mgrid[:80, :80]
    m = ((xx - 40) ** 2 + ((yy - 40) * 1.6) ** 2 < 25 ** 2) | ((xx > 60) & (yy > 10) & (yy < 13))   # a blob and a 3 px channel
    f = look.edge_field(m, 0.5)
    assert f.min() >= 0 and f.max() <= 1 and np.array_equal(look.edge_field(m, 0) >= 0.5, m)
    tol = look.edge_tolerance(m, f)
    assert tol["max_px"] <= 0.55 and tol["mask_to_contour_max_px"] <= 0.55
    assert look.edge_tolerance(m, look.edge_field(m, 3.0))["mask_to_contour_max_px"] > 0.55   # too soft is caught
