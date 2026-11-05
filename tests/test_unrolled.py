from datetime import date

import pytest

from image_evidence.satellite import record, unrolled

_REC = {
    "start": "2025-09-01", "end": "2025-12-31", "run_s": 60, "sources": {"s": {"title": "a source", "url": "https://example.org"}},
    "lines": {"Dniprovska": ["Dniprovska", 750], "Ferosplavna-1": ["Ferosplavna 1, 2", 330, 0]},
    "events": [{"at": "2025-09-01", "lines": "all", "to": "on", "src": ["s"]},
               {"at": "2025-09-23", "lines": "Dniprovska", "to": "off", "src": ["s"]},
               {"at": "2025-10-01", "loop": 9, "brief": True, "src": ["s"]},
               {"at": "2025-10-23", "lines": "Dniprovska", "to": "on", "src": ["s"]}]}


def test_the_days_states_skip_what_was_over_within_the_day():
    days = record.Record({**_REC, "events": [e for e in _REC["events"] if not record.Record._within_day(e)]}, 0.0)
    runs = unrolled._states(days, "Dniprovska")
    assert runs == [["2025-09-01", "2025-09-23", "on"], ["2025-09-23", "2025-10-23", "off"], ["2025-10-23", "2026-01-01", "on"]]
    # Ferosplavna-1 stays lit through the brief complete loss (a tick of its own, never a run of days)
    assert unrolled._states(days, "Ferosplavna-1") == [["2025-09-01", "2026-01-01", "on"]]


def test_a_truce_is_drawn_only_as_wide_as_the_safety_rule_allows():
    ln = {"regions": {"south_bank": [0.0, 4280.0], "crossing": [4280.0, 6900.0], "unknown": [0.0, 34000.0]}}
    t = unrolled.truce({"n": 3, "line": "F", "from": date(2025, 11, 7), "until": date(2025, 11, 8), "region": "south_bank"}, ln)
    assert (t["from_m"], t["to_m"], t["from"]) == (0.0, 4280.0, "2025-11-07")
    with pytest.raises(ValueError, match="narrower than the safety rule"):
        unrolled.truce({"n": 6, "line": "F", "region": "crossing"}, ln)   # 2.6 km
    with pytest.raises(ValueError, match="no region"):
        unrolled.truce({"n": 6, "line": "F", "region": "tower"}, ln)
    with pytest.raises(ValueError, match="isn't drawn"):
        unrolled.truce({"n": 1, "line": "X", "region": "unknown"}, None)


def test_the_date_holds_at_each_truce_and_the_last_year_is_six_times_the_scale():
    d = {"start": "2025-01-01", "end": "2026-01-31", "scale_change": "2025-09-01", "px_per_day": [1.0, 6.0],
         "dam": {"at": "2025-03-01"}, "losses": [{"at": "2025-09-23", "until": "2025-10-23"}],
         "truces": [{"n": 1, "until": "2025-10-23"}, {"n": 2, "until": "2025-11-08", "open_end": True}],
         "captions": [{"at": "2025-11-08"}]}
    tl = unrolled.timeline(d, 30)
    by = {s["day"]: s for s in tl["stops"]}
    assert by["2025-10-23"]["why"] == ["truce 1"] and "2025-11-08" in by   # an open end isn't a stop, its caption is
    assert tl["x_end"] == pytest.approx(243 + 152 * 6)
    arr = [s["arrive_s"] for s in tl["stops"]]
    assert arr == sorted(arr) and tl["frames"] == int(-(-tl["total"] * 30 // 1))
