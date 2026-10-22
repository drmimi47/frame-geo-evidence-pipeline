"""The Conductive Seam: satellite passes along a power line, offline (Overpass, STAC and the data API are stubbed)."""

import io
import json
import subprocess
import re
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import cv2
import httpx
import numpy as np
import pytest

from image_evidence.jobs import ensure_seam_folder, list_libraries, rename_folder, next_folder
from image_evidence.layout import write_json
from image_evidence.satellite import corridor as corr
from image_evidence.satellite import film
from image_evidence.satellite.fetch import Area, check_area, run
from image_evidence.satellite.providers import latest_processing, overpasses
from image_evidence.satellite.schema import pass_id_for
from image_evidence.satellite import stitch
from image_evidence.satellite.stitch import Mosaic, coregister
from image_evidence.satellite.store import read_georef, read_passes, read_chips
from image_evidence.scope import SCOPE_FILE, UKRAINE, Scope

BBOX = (34.60, 47.50, 34.68, 47.57)
# two ways of one line (stub tags in Ukrainian, as mappers write them), joined at 47.53 N
WAY_A = [(34.64, 47.505), (34.641, 47.52), (34.642, 47.53)]
WAY_B = [(34.642, 47.53), (34.645, 47.55), (34.648, 47.565)]


def _osm_reply() -> dict:
    way = lambda i, pts, tags: {"type": "way", "id": i, "tags": tags, "geometry": [{"lon": x, "lat": y} for x, y in pts]}
    return {"elements": [
        way(1, WAY_A, {"power": "line", "voltage": "330000"}),
        way(2, list(reversed(WAY_B)), {"power": "line", "voltage": "330000", "ref": "Л-243;Л-244",
                                        "from": "Запорізька ТЕС", "to": "ПС Феросплавна"}),
        way(3, [(34.61, 47.51), (34.615, 47.56)], {"power": "line", "voltage": "750000"}),
        {"type": "node", "id": 9, "lon": 34.644, "lat": 47.545, "tags": {"power": "tower", "tower:type": "crossing"}},
    ]}


def _item(day: str, cloud: float = 0.5) -> dict:
    t = f"{day[:4]}{day[5:7]}{day[8:10]}T083641"
    return {"id": f"S2A_MSIL2A_{t}_R064_T36TXT_20241028T095503", "bbox": [34.3, 46.8, 35.8, 47.9],
            "geometry": {"type": "Polygon", "coordinates": [[[34.3, 46.8], [35.8, 46.8], [35.8, 47.9], [34.3, 47.9], [34.3, 46.8]]]},
            "properties": {"datetime": f"{day}T08:36:41Z", "platform": "Sentinel-2A", "eo:cloud_cover": cloud,
                           "s2:processing_baseline": "05.10", "s2:mean_solar_zenith": 50.0}}


def _scene(lon: np.ndarray, lat: np.ndarray, before: bool) -> tuple[np.ndarray, np.ndarray]:
    """Reflectance x 10000 (blue, green, red, nir, swir) and the scene class: before the dam's destruction the
    southern half is the reservoir; after it, only a river channel is water."""
    water = (lat < 47.535) if before else (np.abs(lat - 47.53) < 0.002)
    texture = 400 * np.sin(lon * 900) * np.cos(lat * 700) + 300 * np.sin(lon * 2300 + lat * 1700)
    land = np.stack([500 + texture * .2, 700 + texture * .3, 900 + texture * .4, 2500 + texture, 2000 + texture * .8])
    wet = np.stack([np.full_like(lon, v) for v in (300, 400, 300, 100, 50)])
    refl = np.where(water[None], wet, land)
    return refl, np.where(water, 6, 4)


def handler(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if "interpreter" in url:
        return httpx.Response(200, json=_osm_reply())
    if url.endswith("/search"):
        body = json.loads(request.content)
        assert body["collections"] == ["sentinel-2-l2a"]
        start = body["datetime"][:10]
        items = [_item("2023-05-20")] if start < "2023-06-06" else [_item("2023-09-23"), _item("2023-09-28", 3.0)]
        # the same acquisition reprocessed earlier: dropped for the newer one
        old = json.loads(json.dumps(items[0]))
        old["id"] = old["id"].rsplit("_", 1)[0] + "_20230923T145541"
        return httpx.Response(200, json={"features": items + [old], "links": []})
    m = re.search(r"/item/bbox/([^/]+)/(\d+)x(\d+)\.npy$", urlparse(url).path)
    if m:
        w, s, e, n = map(float, m.group(1).split(","))
        W, H = int(m.group(2)), int(m.group(3))
        q = parse_qs(urlparse(url).query)
        lon, lat = np.meshgrid(w + (np.arange(W) + .5) / W * (e - w), n - (np.arange(H) + .5) / H * (n - s))
        refl, scl = _scene(lon, lat, before="20230520" in q["item"][0])
        bands = scl[None] if q["assets"] == ["SCL"] else refl + 1000
        arr = np.concatenate([bands, np.full((1, H, W), 255)]).astype(np.uint16)
        buf = io.BytesIO()
        np.save(buf, arr)
        return httpx.Response(200, content=buf.getvalue())
    return httpx.Response(404)


@pytest.fixture
def http():
    return httpx.Client(transport=httpx.MockTransport(handler))


AREA = Area(corridor_id="test-crossing", name="Тестовий перехід", bbox=BBOX, lines=[1, 2], m_per_px=20, chip_size_m=1500, chip_spacing_m=2000)


def test_corridor_joins_the_ways_and_follows_them(http):
    osm = corr.fetch_power(BBOX, http)
    g = corr.build("x", "x", BBOX, [1, 2], osm, 20, 1500, 2000)
    line = g["line"]["coords"]
    assert line[0] == pytest.approx([34.64, 47.505]) and line[-1] == pytest.approx([34.648, 47.565])  # way 2 turned round
    assert "Л-243;Л-244" in g["line"]["label"] and g["line"]["kv"] == 330
    assert 6500 < g["line"]["length_m"] < 7000
    assert [s["station"] for s in g["stations"]] == [1, 2, 3, 4] and g["stations"][-1]["along_m"] == pytest.approx(g["line"]["length_m"], abs=2)
    cam = np.array(g["camera"]["samples"])
    assert cam[-1, 0] == pytest.approx(g["line"]["length_m"], abs=1)
    assert np.all(np.abs(((cam[:, 3] + 180) % 360) - 180) < 20)  # heading roughly north all the way
    assert [t["tags"].get("tower:type") for t in g["towers"]] == ["crossing"]
    assert {c["id"] for c in corr.choices(osm, min_km=0.1)} == {1, 2, 3}
    with pytest.raises(ValueError, match="doesn't join"):
        corr.chain(corr.ways(osm), [1, 3])


def test_grid_round_trips_lon_lat():
    g = corr.Grid(bbox=BBOX, m_per_px=10)
    c, r = g.to_px(34.63, 47.55)
    assert g.to_lonlat(c, r) == pytest.approx((34.63, 47.55))
    assert g.width == round(0.08 * g.kx / 10) and g.height == round(0.07 * corr.KZ / 10)


def test_ids_and_reprocessed_items():
    assert pass_id_for("Sentinel-2A", datetime(2023, 9, 23, 8, 36, tzinfo=timezone.utc)) == "s2a_20230923T0836"
    assert pass_id_for("landsat-5", datetime(1990, 7, 10, 8, 12)) == "l5_19900710T0812"
    a, b = _item("2023-09-23"), _item("2023-09-23")
    b["id"] = b["id"].rsplit("_", 1)[0] + "_20230923T145541"
    assert [i["id"] for i in latest_processing([b, a])] == [a["id"]]
    assert len(overpasses([a, b, _item("2023-09-28")])) == 2


def test_area_outside_ukraine_is_refused_before_anything_is_written(tmp_path, http):
    poland = Area(corridor_id="krakow", name="Kraków", bbox=(19.8, 49.9, 20.1, 50.2), lines=[1])
    with pytest.raises(ValueError, match="isn't inside Ukraine"):
        run(tmp_path, UKRAINE, poland, "sentinel-2", date(2023, 7, 1), date(2023, 9, 30), http=http)
    assert not (tmp_path / "satellite").exists()
    check_area(UKRAINE, BBOX)  # the test area is fine
    with pytest.raises(ValueError, match="isn't inside"):
        check_area(Scope.from_json({"name": "Poland", "start": "2015-01-01", "end": "2026-12-31", "bbox": [14.1, 49.0, 24.2, 54.9]}), BBOX)


def test_passes_of_any_date_land_on_the_corridors_grid(tmp_path, http):
    r = run(tmp_path, UKRAINE, AREA, "sentinel-2", date(2023, 7, 1), date(2023, 9, 30), 5, http=http)
    assert r["status"] == "processed" and r["pass_id"] == "s2a_20230923T0836"  # the clearest one
    georef = read_georef(tmp_path, "test-crossing")
    assert georef["reference_pass"] == "s2a_20230923T0836"
    # a pass from before the dam's destruction (and before 2022: dates aren't limited) goes on the same grid
    r2 = run(tmp_path, UKRAINE, AREA, "sentinel-2", date(2023, 5, 1), date(2023, 6, 1), 5, http=http)
    assert r2["status"] == "processed"
    passes = read_passes(tmp_path, "test-crossing")
    assert [p.pass_id for p in passes] == ["s2a_20230520T0836", "s2a_20230923T0836"]
    before, after = passes
    assert before.derived.alignment.reference_pass == "s2a_20230923T0836"
    assert abs(before.derived.alignment.dx_m) < 1 and abs(before.derived.alignment.dy_m) < 1  # same place: no shift
    assert before.derived.water_share > 0.3 > after.derived.water_share
    a_dir = tmp_path / "satellite/corridors/test-crossing/passes/s2a_20230923T0836"
    assert json.loads((a_dir / "raw/stac_items.json").read_text())[0]["id"].endswith("20241028T095503")
    assert all(len(x["sha256"]) == 64 for x in json.loads((a_dir / "raw/requests.json").read_text()))
    chips = read_chips(tmp_path, "test-crossing", "s2a_20230923T0836")
    assert [c.source.station for c in chips] == [0, 1, 2, 3, 4] and chips[0].chip.kind == "overview"
    assert all((tmp_path / c.chip.files.web).is_file() and (tmp_path / c.chip.files.thumb).is_file() for c in chips)
    # the bed exposed after the dam: water before, not now (station 1 is in the old reservoir, 4 isn't)
    assert chips[1].derived.exposed_against == "s2a_20230520T0836"
    assert chips[1].derived.exposed_bed_share > 0.5 and chips[4].derived.exposed_bed_share < 0.05
    assert read_chips(tmp_path, "test-crossing", "s2a_20230520T0836")[1].derived.exposed_bed_share is None
    # the corridor is fixed: another box under the same id is refused
    moved = Area(**{**AREA.__dict__, "bbox": (34.6, 47.5, 34.7, 47.6)})
    with pytest.raises(ValueError, match="is fixed"):
        run(tmp_path, UKRAINE, moved, "sentinel-2", date(2023, 7, 1), date(2023, 9, 30), http=http)


def test_coregister_finds_a_small_shift_and_records_it():
    grid = corr.Grid(bbox=BBOX, m_per_px=10)
    rng = np.random.default_rng(1)
    base = cv2.GaussianBlur(rng.random((grid.height, grid.width)).astype(np.float32), (0, 0), 2) * 4000 + 1000
    ok = np.ones((grid.height, grid.width), bool)
    ref = Mosaic(base, base * .8, ok, ~ok)
    moved = cv2.warpAffine(base, np.float32([[1, 0, 2], [0, 1, -1.5]]), (grid.width, grid.height), borderMode=cv2.BORDER_REFLECT)
    m = Mosaic(moved, moved * .8, ok.copy(), ~ok)
    al = coregister(ref, m, grid, "ref")
    assert al.applied and al.dx_m == pytest.approx(-20, abs=1) and al.dy_m == pytest.approx(-15, abs=1)  # a tenth of a pixel
    assert "Shifted" in al.provenance.evidence


def test_film_records_what_every_stretch_is(tmp_path, http):
    run(tmp_path, UKRAINE, AREA, "sentinel-2", date(2023, 7, 1), date(2023, 9, 30), 5, http=http)
    run(tmp_path, UKRAINE, AREA, "sentinel-2", date(2023, 5, 1), date(2023, 6, 1), 5, http=http)
    f = film.render(tmp_path, "test-crossing", None, {"width": 64, "height": 36, "fps": 8, "view_m": 2000, "speed_mps": 4000,
                                                      "hold_s": 0.5, "ease_s": 0.25, "dissolve_s": 0.5, "trace": True})
    out = tmp_path / "satellite/corridors/test-crossing/films" / f["film_id"]
    assert (out / "film.mp4").stat().st_size > 0 and (out / "poster.webp").is_file() and (out / "contact.webp").is_file()
    assert [s["shot"] for s in f["segments"]] == ["hold", "track", "dissolve", "track", "hold"]
    assert [s["kind"] for s in f["segments"]] == ["observed", "observed", "dissolve", "observed", "observed"]
    d = f["segments"][2]
    assert [p["pass_id"] for p in d["passes"]] == ["s2a_20230520T0836", "s2a_20230923T0836"]  # oldest first
    assert [p["pass_id"] for p in f["passes"]] == ["s2a_20230520T0836", "s2a_20230923T0836"]
    assert "Nothing is generated" in f["statement"] and all("trace" in s["overlays"] for s in f["segments"])
    assert f["duration_s"] == pytest.approx(sum(s["t1"] - s["t0"] for s in f["segments"]), abs=0.2)
    assert json.loads((out / "film.json").read_text())["sha256"] == f["sha256"]



def test_inset_is_placed_by_its_pins_and_recorded(tmp_path, http):
    from PIL import Image
    run(tmp_path, UKRAINE, AREA, "sentinel-2", date(2023, 7, 1), date(2023, 9, 30), 5, http=http)
    cdir = tmp_path / "satellite/corridors/test-crossing"
    raw = json.loads((cdir / "raw/osm_power.json").read_text())  # a second tower for the second pin
    raw["reply"]["elements"].append({"type": "node", "id": 10, "lon": 34.646, "lat": 47.546, "tags": {"power": "tower"}})
    (cdir / "raw/osm_power.json").write_text(json.dumps(raw))
    (cdir / "insets").mkdir()
    Image.fromarray(np.full((120, 160, 3), 200, np.uint8)).save(cdir / "insets/pylons.png")
    kx = 111320 * np.cos(np.radians(47.5455))  # 2 m a pixel, north up: tower 10 is 0.002° east, 0.001° north of 9
    pins = [{"px": [40, 90], "osm_node": 9, "label": "330 kV"},
            {"px": [40 + 0.002 * kx / 2, 90 - 0.001 * corr.KZ / 2], "osm_node": 10}]
    inset = {"image": "pylons.png", "title": "Надане зображення", "pins": pins, "crop": [10, 10, 150, 110], "at_km": 3.0,
             "view_m": 800, "zoom_in_m": 300, "zoom_out_m": 300, "hold_s": 0.5}
    opts = {"width": 64, "height": 36, "fps": 8, "view_m": 2000, "speed_mps": 4000, "hold_s": 0.5, "ease_s": 0.25,
            "trace": True, "insets": [inset]}
    f = film.render(tmp_path, "test-crossing", None, opts)
    assert [s["shot"] for s in f["segments"]] == ["hold", "track", "inset", "track", "hold"]
    assert "inset" in f["segments"][2]["overlays"] and f["segments"][3]["inset"] == "pylons.png"
    rec = f["insets"][0]
    assert rec["placement"]["m_per_px"] == pytest.approx(2, abs=0.01) and max(p["residual_m"] for p in rec["pins"]) < 0.5
    assert rec["sha256"] == __import__("hashlib").sha256((cdir / "insets/pylons.png").read_bytes()).hexdigest()
    assert "supplied image" in f["statement"] and any(p["label"] == "Inset" for p in f["provenance"])
    assert min(s[5] for s in f["camera"]["samples"]) == pytest.approx(800 / 64, abs=0.5)  # zoomed in at the stop
    with pytest.raises(ValueError, match="disagree"):  # a pin 40 m off is refused, not stretched to fit
        film.render(tmp_path, "test-crossing", None, {**opts, "insets": [{**inset, "pins": [pins[0], {**pins[1], "px": [95, 70]}]}]})


def test_opening_fades_in_on_the_plant_and_draws_its_lines(tmp_path, http):
    run(tmp_path, UKRAINE, AREA, "sentinel-2", date(2023, 7, 1), date(2023, 9, 30), 5, http=http)
    square = lambda lon, lat, d: [{"lon": lon + a, "lat": lat + b} for a, b in ((-d, -d), (d, -d), (d, d), (-d, d), (-d, -d))]
    reply = {"elements": [  # a stub plant and switchyard south-west of the line's start, and a line leaving it
        {"type": "way", "id": 1, "tags": {"power": "plant", "name": "Запорізька АЕС"}, "geometry": square(34.625, 47.50, 0.004)},
        {"type": "way", "id": 2, "tags": {"power": "substation", "voltage": "750000"}, "geometry": square(34.625, 47.495, 0.001)},
        {"type": "way", "id": 3, "tags": {"power": "line", "voltage": "750000"},
         "geometry": [{"lon": 34.60, "lat": 47.47}, {"lon": 34.625, "lat": 47.495}]},  # stored far end first
    ]}
    write_json(tmp_path / "satellite/corridors/test-crossing/raw/osm_opening.json",
               {"query": "stub", "server": "https://overpass.example/api", "fetched_at": "2026-10-19T00:00:00+00:00",
                "licence": "© OpenStreetMap contributors, ODbL 1.0", "reply": reply})
    opening = {"plant": 1, "box": [34.55, 47.45, 34.70, 47.55], "view_m": 3000, "fade_s": 0.5, "hold_s": 1.5, "pan_s": 1.0,
               "origins": {"yard": 2}, "sites": [{"osm": 1, "text": "Запорізька АЕС"}],
               "branches": [{"ways": [3], "from": "yard", "start_s": 0.5, "draw_s": 0.5, "label": "750 кВ · Каховська"}],
               "line": {"start_s": 0.5, "label": "330 кВ"}}
    f = film.render(tmp_path, "test-crossing", None, {"width": 64, "height": 36, "fps": 8, "view_m": 2000, "speed_mps": 4000,
                                                      "hold_s": 0.5, "ease_s": 0.25, "trace": True, "opening": opening})
    assert [s["shot"] for s in f["segments"]][:3] == ["open", "pan", "track"]
    assert any("fade from black" in x for x in f["segments"][0]["overlays"])
    assert any("fading out" in x for x in f["segments"][2]["overlays"])
    first = f["camera"]["samples"][0]
    assert (first[2], first[3]) == pytest.approx((34.625, 47.50), abs=1e-4)  # the plant in the middle
    o = f["opening"]
    assert o["plant"] == 1 and o["lines"][0]["ways"] == [3] and o["osm"]["server"] == "https://overpass.example/api"
    assert any(p["label"] == "Opening" for p in f["provenance"])
    with pytest.raises(ValueError, match="not in the saved reply"):
        film.render(tmp_path, "test-crossing", None, {"width": 64, "height": 36, "fps": 4, "opening": {**opening, "plant": 99}})

def test_seam_folder_sits_right_below_the_main_library(tmp_path):
    main = tmp_path / "library"
    main.mkdir()
    lib = tmp_path / "libraries" / "folder-1"
    lib.mkdir(parents=True)
    write_json(lib / SCOPE_FILE, UKRAINE.to_json())
    root = ensure_seam_folder(main)
    assert [x["slug"] for x in list_libraries(main)] == ["", "conductive-seam", "folder-1"]
    assert list_libraries(main)[1]["title"] == "The Conductive Seam"
    assert list_libraries(main)[1]["scope"].is_ukraine
    assert next_folder(main)[0] == "folder-2"
    rename_folder(main, "conductive-seam", "Шов")  # keeps its place
    assert [x["title"] for x in list_libraries(main)][:2] == ["Ukraine collection", "Шов"]
    assert ensure_seam_folder(main) == root


def test_the_site_shows_chips_as_a_group_per_pass(tmp_path, http):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from image_evidence.api import create_app

    main = tmp_path / "library"
    root = ensure_seam_folder(main)
    run(root, UKRAINE, AREA, "sentinel-2", date(2023, 7, 1), date(2023, 9, 30), 5, http=http)
    f = film.render(root, "test-crossing", None, {"width": 64, "height": 36, "fps": 4, "speed_mps": 4000, "hold_s": .5, "ease_s": .25,
                                                  "gallery": False})  # (its frames in the gallery: the test below)
    c = TestClient(create_app(main))
    c.cookies.set("lib", "conductive-seam")
    res = c.get("/api/frames?limit=500").json()
    assert res["total"] == 5 and {it["kind"] for it in res["items"]} == {"satellite"}
    assert res["items"][0]["video_title"] == "Sentinel-2A · 23 September 2023" and res["facets"]["year"] == {"2023": 5}
    assert c.get("/api/frames?limit=500&year=2022").json()["total"] == 0
    assert c.get("/api/frames?limit=500&q=sentinel").json()["total"] == 5
    assert c.get("/api/frames?limit=500&category=water").json()["total"] == 0  # chips aren't classified
    assert c.get("/api/frames?limit=500&sort=color").json()["items"][0]["sort_note"].startswith("Satellite imagery")
    chip = res["items"][1]
    d = c.get(f"/api/frames/{chip['frame_id']}").json()
    assert d["kind"] == "satellite" and d["pass"]["source"]["collection"] == "sentinel-2-l2a"
    assert c.get(chip["web_url"]).status_code == 200
    assert c.get(chip["web_url"].split("satellite/")[0] + "evidence.db").status_code == 404
    assert c.get("/api/stats").json() == {"videos": 0, "frames": 5, "passes": 1, "chips": 5}
    vids = c.get("/api/videos").json()
    assert vids[0]["kind"] == "satellite" and len(vids[0]["frame_times"]) == 5
    assert [x["slug"] for x in c.get("/api/folders").json()["folders"]] == ["", "conductive-seam"]
    films = c.get("/api/seam/films").json()
    assert [x["film_id"] for x in films] == [f["film_id"]]
    assert c.get(films[0]["urls"]["video"], headers={"Range": "bytes=0-99"}).status_code == 206  # seekable
    assert c.get(films[0]["urls"]["video"].replace("film.mp4", "../../georef.json")).status_code == 404
    setup = c.get("/api/satellite/setup").json()
    assert setup["corridors"][0]["passes"][0]["pass_id"] == "s2a_20230923T0836"
    # the panel's jobs only from this site, and a refused area never queues a job
    bad = {"area": {"corridor_id": "krakow", "name": "Kraków", "bbox": [19.8, 49.9, 20.1, 50.2], "lines": [1]}}
    assert c.post("/api/satellite/jobs", json=bad).status_code == 400
    assert c.post("/api/satellite/jobs", json=bad, headers={"Origin": "http://evil.example"}).status_code == 403


def test_a_films_frames_join_the_gallery_and_its_notes_are_placed(tmp_path, http):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from image_evidence.api import create_app
    from image_evidence.satellite import notes

    main = tmp_path / "library"
    root = ensure_seam_folder(main)
    run(root, UKRAINE, AREA, "sentinel-2", date(2023, 7, 1), date(2023, 9, 30), 5, http=http)
    run(root, UKRAINE, AREA, "sentinel-2", date(2023, 5, 1), date(2023, 6, 1), 5, http=http)
    say = [{"from": {"shot": "hold", "s": 0.1}, "text": "Запорізька АЕС: шість реакторів.", "sources": [{"title": "IAEA", "url": "https://www.iaea.org/"}]},
           {"from": {"km": 0.5}, "to": {"shot": "dissolve", "s": 0}, "text": "Лінія Феросплавна."},
           {"from": {"shot": "hold", "n": -1, "s": 0.1}, "text": "Кінець."}]
    f = film.render(root, "test-crossing", None, {"width": 64, "height": 36, "fps": 8, "view_m": 2000, "speed_mps": 2000, "hold_s": 1.5,
                                                  "ease_s": 0.25, "dissolve_s": 1.0, "fade_out_s": 1.0, "notes": say})
    out = root / "satellite/corridors/test-crossing/films" / f["film_id"]
    # the end fades to black (the last frame decoded from the mp4 is black), and the segment says so
    last = subprocess.run(["ffmpeg", "-loglevel", "error", "-sseof", "-0.2", "-i", str(out / "film.mp4"), "-frames:v", "1", "-f", "rawvideo",
                           "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    assert last and max(last) < 12
    assert any("fade to black" in o for o in f["segments"][-1]["overlays"])
    # frames: a new view each time half the ground is new, plus the held moments by name; none in a fade
    frames = json.loads((out / "frames/frames.json").read_text())["frames"]
    kept = [x["kept"] for x in frames]
    assert any(k.startswith("a new view") for k in kept) and "before the dissolve: the earlier pass" in kept
    assert "after the dissolve: the later pass" in kept and any(k.startswith("the last hold") for k in kept)
    end = f["segments"][-1]
    assert all(x["t"] < end["t1"] - 1.0 for x in frames)
    after = next(x for x in frames if x["kept"].startswith("after the dissolve"))
    assert [p["weight"] for p in after["passes"]] == pytest.approx([0, 1], abs=0.05)  # (the last frame inside the dissolve)
    assert (root / frames[0]["files"]["web"]).is_file() and len(frames[0]["sha256"]) == 64
    # the notes, placed by shot and by distance, in order and none overlapping
    ns = f["notes"]
    assert [n["text"] for n in ns] == ["Запорізька АЕС: шість реакторів.", "Лінія Феросплавна.", "Кінець."]
    assert ns[0]["t0"] == pytest.approx(0.1, abs=0.01) and ns[0]["t1"] == ns[1]["t0"] and ns[1]["t1"] == pytest.approx(f["segments"][2]["t0"], abs=0.01)
    assert ns[2]["t0"] == pytest.approx(end["t0"] + 0.1, abs=0.01) and ns[2]["t1"] == pytest.approx(f["duration_s"], abs=0.01)
    assert ns[0]["sources"][0]["url"] == "https://www.iaea.org/" and "not read from the imagery" in f["notes_statement"]
    with pytest.raises(ValueError, match="beyond the film's line"):
        notes.place(f, [{"from": {"km": 500}, "text": "x"}])
    # the site: the film's frames first, as a group of their own, with the note shown under the film then
    c = TestClient(create_app(main))
    c.cookies.set("lib", "conductive-seam")
    res = c.get("/api/frames?limit=500").json()
    first = res["items"][0]
    assert first["sat_kind"] == "film" and first["video_title"] == "Film · Тестовий перехід" and first["kind"] == "satellite"
    assert res["total"] == len(frames) + 10 and c.get("/api/stats").json()["film_frames"] == len(frames)
    vids = c.get("/api/videos").json()
    assert vids[0]["sat_kind"] == "film" and len(vids[0]["frame_times"]) == len(frames)
    in_note = next(x for x in frames if ns[1]["t0"] <= x["t"] < ns[1]["t1"])
    d = c.get(f"/api/frames/{in_note['frame_id']}").json()
    assert d["note"]["text"] == "Лінія Феросплавна." and d["film"]["film_id"] == f["film_id"] and d["camera"]["view_m"] > 0
    assert c.get(first["web_url"]).status_code == 200
    # the notes placed again without rendering (another text), and the site follows
    notes.write(root, "test-crossing", f["film_id"], [{"from": {"km": 0.5}, "text": "Інша примітка."}])
    assert c.get(f"/api/frames/{in_note['frame_id']}").json()["note"]["text"] == "Інша примітка."


def test_ways_join_through_a_substation_and_the_join_is_recorded(http):
    osm = corr.fetch_power(BBOX, http)
    ways = corr.ways(osm)
    ways[2]["coords"] = ways[2]["coords"][:-1] + [(34.6428, 47.5345)]  # its end 500 m from way 1's, across a substation
    with pytest.raises(ValueError, match="doesn't join"):
        corr.chain(ways, [1, 2])
    joins = []
    line = corr.chain(ways, [1, 2], join_m=1000, joins=joins)
    assert len(joins) == 1 and 400 < joins[0]["gap_m"] < 600 and line[2] == (34.642, 47.53) and line[3] == (34.6428, 47.5345)


def test_a_long_corridor_is_fetched_in_tiles_along_its_line_and_a_pass_can_cover_only_its_start(tmp_path, http, monkeypatch):
    monkeypatch.setattr(stitch, "TILE", 64)
    long_area = Area(**{**AREA.__dict__, "corridor_id": "strip", "strip_m": 700, "chip_spacing_m": 1000, "chip_size_m": 800})
    r = run(tmp_path, UKRAINE, long_area, "sentinel-2", date(2023, 7, 1), date(2023, 9, 30), 5, http=http)
    assert r["status"] == "processed"
    after = read_passes(tmp_path, "strip")[0]
    georef = read_georef(tmp_path, "strip")
    grid = corr.Grid.from_json(georef["grid"])
    every = -(-grid.width // 64) * -(-grid.height // 64)
    assert 1 < len(after.files.tiles) < every  # only the tiles near the line (it runs north-south through the box)
    assert {(t.rows[1] - t.rows[0], t.cols[1] - t.cols[0]) for t in after.files.tiles} <= {(64, 64), (grid.height % 64, 64), (64, grid.width % 64), (grid.height % 64, grid.width % 64)}
    assert len(read_chips(tmp_path, "strip", after.pass_id)) == 1 + len(georef["stations"])
    # a pass fetched only round the line's first 2 km: fewer tiles, chips only where it has data, and it says so
    r2 = run(tmp_path, UKRAINE, long_area, "sentinel-2", date(2023, 5, 1), date(2023, 6, 1), 5, http=http, until_km=2)
    before = next(p for p in read_passes(tmp_path, "strip") if p.pass_id == r2["pass_id"])
    assert before.derived.until_m == 2000 and before.derived.coverage == "the line's first 2 km"
    assert len(before.files.tiles) < len(after.files.tiles)
    chips = read_chips(tmp_path, "strip", before.pass_id)
    assert max(c.source.along_m for c in chips) <= 3000
    # the whole corridor's exposure needs the earlier pass over most of it: none; a station at the start has it
    after_chips = read_chips(tmp_path, "strip", after.pass_id)
    assert after_chips[0].derived.exposed_bed_share is None and after_chips[1].derived.exposed_against == before.pass_id
    # a film may show the partial pass only at the start
    opts = {"width": 64, "height": 36, "fps": 4, "speed_mps": 4000, "view_m": 600, "hold_s": .5, "ease_s": .25, "dissolve_s": .5}
    with pytest.raises(ValueError, match="covers only the line's first 2 km"):
        film.render(tmp_path, "strip", None, opts)
    f = film.render(tmp_path, "strip", None, {**opts, "dissolve_at_km": [1.0]})
    assert [s_["along_m"] for s_ in f["segments"] if s_["shot"] == "dissolve"] == [[1000.0, 1000.0]]
    assert max(s_["nodata_share"] for s_ in f["segments"]) < 0.05


def test_pace_follows_the_profile_and_slows_in_bends():
    s = np.arange(0, 20001, 25.0)
    heading = np.where(s < 10000, 0.0, 180.0)  # a hairpin at 10 km
    cam = film.Camera(along=s, lon=34.6 + 0 * s, lat=47.5 + s / 110574, heading=np.convolve(np.pad(heading, 40, mode="edge"), np.ones(81) / 81, "valid"))
    o = {**film.DEFAULTS, "profile": [{"km": 0, "speed_mps": 100, "view_m": 5000}, {"km": 4, "speed_mps": 500, "view_m": 10000}]}
    pace = film.Pace(cam, o)
    assert pace.view_at(0) == pytest.approx(5000) and pace.view_at(6000) == pytest.approx(10000)
    assert np.interp(6000, pace.s, pace.speed) == pytest.approx(500, rel=.01)
    assert np.interp(10000, pace.s, pace.speed) < 100  # the frame turns at most 8 degrees a second
    assert pace.cruise(0, 20000) > 20000 / 500
    assert pace.along(0, pace.cruise(0, 7000)) == pytest.approx(7000, abs=5)
