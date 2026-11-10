"""A plant's lines traced through a stubbed Overpass reply (Ukrainian names), and the zoom-out's schedule."""

import ast
import json
from datetime import date
from pathlib import Path

import numpy as np
import pytest

from image_evidence.satellite import network, zoomout


def _way(i, pts, **tags):
    return {"type": "way", "id": i, "tags": tags, "geometry": [{"lon": x, "lat": y} for x, y in pts]}


def _square(i, x, y, name, d=0.002, **tags):
    return _way(i, [(x - d, y - d), (x + d, y - d), (x + d, y + d), (x - d, y + d), (x - d, y - d)],
                name=name, **tags)


def _osm():
    els = [
        _square(1, 34.585, 47.508, "Запорізька АЕС", power="plant"),
        _square(2, 34.580, 47.500, "Запорізька АЕС", power="substation", voltage="750000"),
        _square(3, 34.700, 47.800, "Дніпровська-750", power="substation", voltage="750000"),
        _square(4, 34.900, 47.400, "Мелітопольська-330", power="substation", voltage="330000"),
        # 750 kV north in two ways, joined end to end; a branch at the join goes east and stops short
        _way(10, [(34.580, 47.502), (34.62, 47.60), (34.64, 47.65)], power="line", voltage="750000"),
        _way(11, [(34.64, 47.65), (34.68, 47.75), (34.700, 47.798)], power="line", voltage="750000"),
        _way(12, [(34.64, 47.65), (34.80, 47.66)], power="line", voltage="750000"),
        # 330 kV south-east, its second way 40 m from the first's end (unconnected in OSM)
        _way(20, [(34.582, 47.498), (34.70, 47.45)], power="line", voltage="330000"),
        _way(21, [(34.7004, 47.4502), (34.898, 47.401)], power="line", voltage="330000"),
    ]
    return {"query": "q", "server": "s", "fetched_at": "t", "licence": "ODbL", "reply": {"elements": els}}


def test_lines_are_traced_to_the_substation_where_they_end():
    net = network.Network(_osm())
    north = net.trace([10], 2, 750)
    assert north["ways"] == [10, 11]
    assert net.names[north["ends_at"]["osm_way"]] == "Дніпровська-750"
    assert north["branches"] and north["branches"][0]["taken"] == 11  # the straightest way on
    south = net.trace([20], 2, 330)
    assert south["ways"] == [20, 21] and south["ends_at"]["name"] == "Мелітопольська-330"
    assert south["coords"][0][0] == pytest.approx(34.582)  # starts at the switchyard's end


def test_a_line_ending_elsewhere_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(network, "reply", lambda root, cfg, http=None: _osm())
    cfg = {"id": "zaes", "name": "Запорізька АЕС", "plant": {"osm": 1, "label": "ЗАЕС"}, "origins": {"npp": 2},
           "lines": [{"name": "Дніпровська", "kv": 750, "from": "npp", "start": [10], "to": "Каховська-750"}]}
    with pytest.raises(ValueError, match="not Каховська-750"):
        network.build(tmp_path, cfg)
    assert not (network.network_dir(tmp_path, "zaes") / "network.json").exists()
    cfg["lines"][0]["to"] = "Дніпровська-750"
    doc = network.build(tmp_path, cfg)
    assert doc["lines"][0]["length_m"] > 30_000 and doc["context"]  # the branch east is context


def test_the_zoom_follows_the_lines_and_never_shrinks():
    plane = zoomout.Plane(34.585, 47.508)
    doc = network.Network(_osm())
    lines = [zoomout.Line({"name": "Дніпровська", "kv": 750, "coords": doc.trace([10], 2, 750)["coords"], "to": "x"}, plane),
             zoomout.Line({"name": "Мелітопольська", "kv": 330, "coords": doc.trace([20], 2, 330)["coords"], "to": "y"}, plane)]
    o = {"fps": 10, "hold_s": 3, "grow_s": 6, "end_hold_s": 3, "accel": 3, "margin": 1.2, "start_view_km": 4,
         "end_view_km": 80}
    sch = zoomout.schedule(lines, o, 16 / 9)
    hw = sch["half_w"]
    assert np.all(np.diff(hw) >= -1e-6)
    assert hw[0] == pytest.approx(2000) and np.all(hw[sch["t"] <= 3] == hw[0]) and hw[-1] >= 40_000  # held on the plant, then out
    s = sch["s"]
    assert s[0] == 0 and s[-1] == pytest.approx(max(ln.length for ln in lines))
    short = min(lines, key=lambda ln: ln.length)
    assert sch["landed_at"][id(short)] < sch["landed_at"][id(max(lines, key=lambda ln: ln.length))]
    for i in range(len(s)):  # everything drawn stays inside the frame
        for ln in lines:
            ex, ey = ln.extent(s[i])
            assert ex <= hw[i] and ey <= hw[i] * 9 / 16


def test_the_camera_eases_into_its_widest_view_while_the_lines_grow_on():
    plane = zoomout.Plane(34.585, 47.508)
    doc = network.Network(_osm())
    lines = [zoomout.Line({"name": "Дніпровська", "kv": 750, "coords": doc.trace([10], 2, 750)["coords"], "to": "x"}, plane),
             zoomout.Line({"name": "Мелітопольська", "kv": 330, "coords": doc.trace([20], 2, 330)["coords"], "to": "y"}, plane)]
    o = {"fps": 60, "hold_s": 3, "grow_s": 6, "end_hold_s": 3, "accel": 3, "margin": 1.2, "start_view_km": 4,
         "end_view_km": 80, "max_view_km": 30}
    sch = zoomout.schedule(lines, o, 16 / 9)
    hw = sch["half_w"]
    assert hw[0] == pytest.approx(2000, rel=1e-3) and hw.max() <= 15_000 and hw[-1] > 14_000  # opens as set, never past the cap
    assert np.all(np.diff(hw) >= -1e-6) and np.all(np.abs(np.diff(np.log(hw), 2)) < 1e-3)  # no corner in the move
    assert sch["s"][-1] == pytest.approx(max(ln.length for ln in lines))  # the lines grow on, off the frame


def test_the_record_cuts_and_reconnects_lines_on_their_dates():
    from image_evidence.satellite.record import Record

    cfg = {"start": "2022-02-24", "end": "2022-12-31", "run_s": 20, "intro_s": 2, "min_blink_s": 0.5,
           "lines": {"Дніпровська": ["Дніпровська", 750], "Феросплавна-1": ["Феросплавна", 330, 0]},
           "sources": {"iaea": {"title": "МАГАТЕ", "url": "https://www.iaea.org"}},
           "events": [{"at": "2022-03-03", "lines": "all", "to": "unknown", "src": ["iaea"]},
                      {"at": "2022-08-25", "lines": "Дніпровська", "to": True, "src": ["iaea"]},  # YAML's on
                      {"at": "2022-09-03", "lines": "Дніпровська", "to": False, "until": "2022-09-17", "src": ["iaea"]},
                      {"at": "2022-10-08", "loop": 2, "brief": True, "caption": "Знеструмлення", "src": ["iaea"]}]}
    rec = Record(cfg, 10.0)
    t = lambda d: rec.t(date.fromisoformat(d).toordinal())
    assert rec.state("Дніпровська", 11) == "on" and rec.state("Феросплавна-1", t("2022-05-01")) == "unknown"
    assert rec.state("Дніпровська", t("2022-09-10")) == "off" and rec.state("Дніпровська", t("2022-09-20")) == "on"
    a = t("2022-10-08")
    assert rec.state("Феросплавна-1", a + 0.4) == "off" and rec.state("Дніпровська", a + 0.4) == "off"  # a blink, shown 0.5 s
    assert rec.state("Дніпровська", a + 0.6) == "on" and rec.loss_count(a + 1) == (2, a)
    assert rec.day(rec.t1) == date(2022, 12, 31) and rec.caption(a + 1)[0] == "Знеструмлення"
    with pytest.raises(ValueError, match="no line"):
        Record({**cfg, "events": [{"at": "2022-03-03", "lines": "Каховська", "to": "off"}]}, 10.0)


def _rec_cfg():
    return {"start": "2022-02-24", "end": "2022-12-31", "run_s": 20, "intro_s": 2, "min_blink_s": 0.5,
            "lines": {"Дніпровська": ["Дніпровська", 750], "Феросплавна-1": ["Феросплавна", 330, 0]},
            "sources": {"iaea": {"title": "МАГАТЕ", "url": "https://www.iaea.org"}},
            "events": [{"at": "2022-09-03", "lines": "Дніпровська", "to": False, "until": "2022-09-17", "src": ["iaea"]},
                       {"at": "2022-10-08", "loop": 2, "until": "2022-10-20", "src": ["iaea"]}]}


def test_the_date_shown_steps_from_one_reported_change_to_the_next():
    from image_evidence.satellite.record import Record

    rec = Record(_rec_cfg(), 10.0)
    t = lambda d: rec.t(date.fromisoformat(d).toordinal())
    assert rec.shown(5.0) is None and rec.shown(t("2022-06-01")) == date(2022, 2, 24)  # nothing reported: held
    assert rec.shown(t("2022-09-10")) == date(2022, 9, 3) and rec.shown(t("2022-09-17")) == date(2022, 9, 17)
    assert rec.shown(rec.t1) == date(2022, 12, 31)  # the last report
    ts = np.array([11.0, t("2022-09-10"), t("2022-10-10")])
    assert list(rec.states("Дніпровська", ts)) == [rec.state("Дніпровська", v) for v in ts] == ["on", "off", "off"]


def test_a_held_day_holds_the_date_without_a_change_reported():
    from image_evidence.satellite.record import Record

    rec = Record({**_rec_cfg(), "holds": [{"at": "2022-06-01", "s": 6}]}, 10.0)
    t = lambda d: rec.t(date.fromisoformat(d).toordinal())
    assert t("2022-09-03") - t("2022-06-01") >= 6 - 1e-6  # the date stays on its day for the held moment
    assert rec.shown(t("2022-06-01") + 3) == date(2022, 6, 1) and rec.t1 == Record(_rec_cfg(), 10.0).t1  # same run


def test_the_hum_follows_the_record():
    from image_evidence.satellite import hum
    from image_evidence.satellite.record import Record

    rec = Record(_rec_cfg(), 2.0)
    x, doc = hum.score(rec, {"Дніпровська": -0.3, "Феросплавна-1": -0.6}, {"Дніпровська": 750, "Феросплавна-1": 330},
                       rec.end, 1.0, start_s=0.5, fade_in_s=1.0)
    rms = lambda a, b: float(np.sqrt((x[int(a * hum.SR):int(b * hum.SR)] ** 2).mean()))
    t = lambda d: rec.t(date.fromisoformat(d).toordinal())
    assert x.shape == (int(round(rec.end * hum.SR)), 2) and np.abs(x).max() < 1.0
    assert rms(0, 0.5) < 1e-4 and rms(1.6, 1.9) > 0.05  # silent, then every line, before the record starts
    full, cut = rms(t("2022-06-01"), t("2022-06-01") + 0.3), rms(t("2022-09-10"), t("2022-09-10") + 0.3)
    assert cut < full * 0.8  # a line cut: quieter, one voice
    assert rms(t("2022-10-08") + 0.05, t("2022-10-08") + 0.15) < cut * 0.2  # a complete loss: the hum stops at once
    assert rms(t("2022-10-08") + 1.0, t("2022-10-08") + 1.3) < cut * 0.1  # silent through it (no diesel)
    assert rms(t("2022-10-21"), t("2022-10-21") + 0.3) > cut * 0.8  # and the lines are back
    assert [v["harmonic_hz"] for v in doc["voices"]] == [200, 600]


def test_island_mode_cuts_every_line_without_counting_a_loss_and_holds_one_low_note():
    from image_evidence.satellite import hum
    from image_evidence.satellite.record import Record

    cfg = {**_rec_cfg(), "events": _rec_cfg()["events"] + [
        {"at": "2022-09-05", "lines": "all", "to": "off", "until": "2022-09-10", "island": True, "src": ["iaea"]}]}
    rec = Record(cfg, 2.0)
    t = lambda d: rec.t(date.fromisoformat(d).toordinal())
    mid = (t("2022-09-05") + t("2022-09-10")) / 2
    assert rec.in_island(mid) and not rec.on_diesel(mid) and rec.loss_count(mid) == (0, -np.inf)  # not a complete loss
    assert rec.state("Дніпровська", mid) == rec.state("Феросплавна-1", mid) == "off"
    assert rec.state("Феросплавна-1", t("2022-09-12")) == "on" and not rec.in_island(t("2022-09-12"))
    assert [e for e in rec.doc()["events"] if e["island"]][0]["state"] == "off"
    x, doc = hum.score(rec, {"Дніпровська": -0.3, "Феросплавна-1": -0.6}, {"Дніпровська": 750, "Феросплавна-1": 330},
                       rec.end, 1.0, start_s=0.5, fade_in_s=1.0)
    rms = lambda a, b: float(np.sqrt((x[int(a * hum.SR):int(b * hum.SR)] ** 2).mean()))
    note, full = rms(mid - 0.1, mid + 0.1), rms(t("2022-06-01"), t("2022-06-01") + 0.3)
    assert full * 0.03 < note < full * 0.5 and "island_mode" in doc  # a low note, quieter than the lines
    with pytest.raises(ValueError, match="island mode needs"):
        Record({**cfg, "events": [{"at": "2022-09-05", "lines": "all", "to": "off", "island": True}]}, 2.0)


def test_complete_losses_and_the_zone_are_held_and_lines_cut_fast_but_return_slowly():
    from image_evidence.satellite.record import Record

    cfg = {**_rec_cfg(), "run_s": 40, "min_hold_s": 0.5, "loss_s": 2.0, "loss_hold_s": 2.5, "loss_day_s": 0.1,
           "loss_max_s": 3.0, "fade_off_s": 0.2, "fade_on_s": 0.8,
           "zone": {"from": "2022-09-06", "until": "2022-12-01", "hold_s": 6.0},
           "events": _rec_cfg()["events"] + [{"at": "2022-11-23", "loop": 3, "brief": True, "src": ["iaea"]}]}
    rec = Record(cfg, 10.0)
    t = lambda d: rec.t(date.fromisoformat(d).toordinal())
    assert t("2022-09-17") - t("2022-09-06") >= 6.0 - 1e-6  # the zone's day held
    assert t("2022-10-20") - t("2022-10-08") >= 3.0 - 1e-6  # a 12-day loss: 2.5 s + 0.1 s a day, capped at 3 s
    a = t("2022-11-23")
    assert rec.on_diesel(a + 1.9) and not rec.on_diesel(a + 2.1)  # a loss within the day: shown 2 s, every line off
    assert t("2022-12-01") - a >= 2.5 - 1e-6 and rec.loss_weight(a + 1.0) == 1.0
    cut = t("2022-09-03")
    assert rec.mix("Дніпровська", cut + 0.25) == {"off": 1.0}  # a cut: dimmed in 0.2 s
    back = t("2022-09-17")
    assert 0 < rec.mix("Дніпровська", back + 0.4)["on"] < 1  # a reconnection: still swelling back
    assert rec.mix("Дніпровська", back + 0.85) == {"on": 1.0}
    with pytest.raises(ValueError, match="needs at least"):
        Record({**cfg, "run_s": 10}, 10.0)


def test_an_unreported_line_is_dotted_and_its_dots_hold_still():
    lay = np.zeros((20, 400), np.uint8)
    pts = np.array([[10.0, 10.0], [390.0, 10.0]])
    zoomout._dotted(lay, pts, 255, 2, 0.0, 4.0)
    row = lay[10] > 128
    assert row.any() and not row[10:390].all()  # dots, with gaps between
    # a piece of the same line drawn from further along keeps the dots where they were
    later = np.zeros_like(lay)
    zoomout._dotted(later, np.array([[110.0, 10.0], [390.0, 10.0]]), 255, 2, 100.0, 4.0)
    assert np.array_equal(later[10, 120:380] > 128, row[120:380])


def test_both_films_draw_a_cut_line_unlit_in_steel_grey_not_red():
    src = Path(zoomout.__file__).with_name("scene3d").joinpath("build.py").read_text()
    steel_3d = next(ast.literal_eval(n.value) for n in ast.walk(ast.parse(src))
                    if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "STEEL_RGB")
    for rgb in [*steel_3d.values(), *(tuple(c) for c in zoomout.STATE_RGB["off"].values())]:
        assert max(rgb) - min(rgb) <= 12  # a neutral grey
    for kv in (750, 330):
        assert np.array_equal(zoomout.STATE_RGB["off"][kv], zoomout.STATE_RGB["unknown"][kv])  # told apart by the dots
    assert all(v == 0 for k, v in zoomout.STATE_GLOW.items() if k != "on")


def _bands(x, a, b, ch):
    from image_evidence.satellite import hum

    y = x[int(a * hum.SR):int(b * hum.SR), ch].astype(np.float64)
    X, f = np.fft.rfft(y), np.fft.rfftfreq(len(y), 1 / hum.SR)
    band = lambda lo, hi: np.fft.irfft(X * ((f >= lo) & (f < hi)), len(y))
    db = lambda z: 20 * np.log10(np.sqrt((z ** 2).mean()) + 1e-12)
    hb = band(2000, 8000)
    return {"crackle": db(hb), "top": db(band(9000, 16000)), "kurtosis": float(((hb - hb.mean()) ** 4).mean() / hb.var() ** 2)}


def test_the_crackle_sets_750_kv_apart_from_330_kv_and_swells_on_wet_dates():
    from image_evidence.satellite import hum
    from image_evidence.satellite.record import Record

    rec = Record(_rec_cfg(), 2.0)
    t = lambda d: rec.t(date.fromisoformat(d).toordinal())
    wet = {date(2022, 10, 20).toordinal(): 12}   # the day the lines come back: 12 wet hours; every other day dry
    pans, kvs = {"Дніпровська": 1.0, "Феросплавна-1": -1.0}, {"Дніпровська": 750, "Феросплавна-1": 330}
    x, doc = hum.score(rec, pans, kvs, rec.end, 1.0, start_s=0.5, fade_in_s=1.0, wet=wet,
                       weather_doc={"source": "test"})
    dry = t("2022-06-01")
    r, l = _bands(x, dry, dry + 0.6, 1), _bands(x, dry, dry + 0.6, 0)   # Dniprovska alone right, Ferosplavna-1 left
    assert r["crackle"] > l["crackle"] + 4    # the 750 kV louder
    assert r["top"] > l["top"] + 15           # and brighter: it reaches 16 kHz, the 330 kV rolls off above 8
    assert r["kurtosis"] > 2 * l["kurtosis"]  # and cracks where the 330 kV hisses
    w = t("2022-10-20") + 0.8                 # (the swell eased in)
    assert _bands(x, w, w + 0.6, 1)["crackle"] > r["crackle"] + 5
    assert _bands(x, w, w + 0.6, 0)["crackle"] > l["crackle"] + 3
    assert doc["weather"]["dates"] == [{"date": "2022-10-20", "wet_hours": 12, "film_s": doc["weather"]["dates"][0]["film_s"]}]
    assert np.abs(x).max() < 1.0
    x2, doc2 = hum.score(rec, pans, kvs, rec.end, 1.0, start_s=0.5, fade_in_s=1.0)
    assert doc2["weather"].startswith("none") and abs(_bands(x2, dry, dry + 0.6, 1)["crackle"] - r["crackle"]) < 0.5


def test_wet_days_counts_rain_and_inferred_fog(tmp_path: Path):
    from image_evidence.satellite import hum

    h = {"time": ["2023-06-11T00:00", "2023-06-11T01:00", "2023-06-11T02:00", "2023-06-12T00:00"],
         "precipitation": [0.0, 0.2, 0.0, None], "relative_humidity_2m": [98, 80, 98, 99],
         "wind_speed_10m": [1.0, 2.0, 5.0, None]}
    f = tmp_path / "era5.json"
    f.write_text(json.dumps({"hourly": h}))
    assert hum.wet_days(f) == {date(2023, 6, 11).toordinal(): 2, date(2023, 6, 12).toordinal(): 0}   # fog, rain; windy; no wind value
