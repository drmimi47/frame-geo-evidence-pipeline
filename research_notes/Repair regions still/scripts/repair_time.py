"""The repairs in time: still prototypes of the D3 gallery's options 1-3 (the user, 9 November 2026: "please
prototype/preview option 1, 2, and 3"), none of them a map: no repair is placed, so the safety rule holds by itself.

1  arcs      each repair an arc from the day its line was cut to the day it came back (the arc's width is the wait);
             Ferosplavna-1 and the links to it above the axis, Dniprovska below; the two lines' record as ribbons
2  calendar  one square per day of the record, lit by how many of the plant's ten lines were connected; a dot per repair
3  deficit   the lines connected out of ten over time, the gap up to ten shaded: what the repairs never brought back
then (the user, 9 November 2026: "do option 4 and 5. also do some other variations of Calender option"):
4  parsets   parallel sets: the 42 repairs through who did the work, the year, the line, a ceasefire, a place published
5  swarm     a dot per repair along time, a row per line, swarmed; dots: the same stacked by month (a dot histogram)
2b cal_split the calendar with each day split: Ferosplavna-1 above, Dniprovska below
2c cal_ten   every line every day: a band of ten rows per year, a column per day
2d cal_spiral the calendar as a spiral, a turn per year
2e cal_waffle the days counted: every day of the record a square, grouped by how many lines were connected
   cal_waffle_anim  the black-and-white waffle (bw3) centred and animated, square by square (`--anim`: the mp4)

The lines' states day by day are the zoom-out's record (config networks.znpp.record), read at the end of each day; a
complete loss within a day is a mark of its own. The repairs, who did them and the ceasefires are repairs.yaml's; the
cut dates are repair_sides_more.py's (`CUT`, as each repair's `what` gives them). Drawn by D3 (the unrolled film's
vendored 7.9.0) in the installed Chrome, as the unrolled film is.

    .venv/bin/python -I "research_notes/Repair regions still/scripts/repair_time.py" [arcs calendar deficit]
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import date, timedelta
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from repair_sides_c import line_of  # noqa: E402
from repair_sides_more import CUT  # noqa: E402

from image_evidence.satellite import network, record  # noqa: E402

ROOT = HERE.parents[2]
NOTES = HERE.parent
OUT = NOTES / "time"
WEB = Path(__file__).resolve().parents[3] / "src/image_evidence/satellite/unrolled_web"
END = date(2026, 10, 31)          # the axis runs on past the record's last report (11 September 2026) to the last repair


def _iso(d: int) -> str:
    return date.fromordinal(d).isoformat()


def day_states(rcfg: dict) -> dict:
    """Each line's state at the end of each day, and the days with a complete loss or island mode in them."""
    rec = record.Record({**rcfg, "events": [e for e in rcfg["events"] if not record.Record._within_day(e)]}, 0.0)
    keys = list(rec.lines)
    days = []
    for d in range(rec.d0, rec.d1 + 1):
        t = rec.t(d + 1) - 1e-3 if d < rec.d1 else rec.t1 + 1e-3
        days.append({k: rec.state(k, t) for k in keys})
    loss, island, brief = set(), set(), {}
    for e in rcfg["events"]:
        a = date.fromisoformat(str(e["at"])).toordinal()
        b = date.fromisoformat(str(e["until"])).toordinal() if e.get("until") is not None else a
        if e.get("loop"):
            loss |= set(range(a, max(a, b) + 1))
        if e.get("island"):
            island |= set(range(a, b + 1))
        if record.Record._within_day(e) and not e.get("loop"):
            for k in rec._keys(e.get("lines", [])):
                brief.setdefault(k, []).append(_iso(a))
    out = []
    for i, s in enumerate(days):
        d = rec.d0 + i
        out.append({"d": _iso(d), "on": sum(v == "on" for v in s.values()), "unk": sum(v == "unknown" for v in s.values()),
                    "fero": s["Ferosplavna-1"], "dnip": s["Dniprovska"], "loss": d in loss, "island": d in island,
                    "s": "".join({"on": "o", "off": "x"}.get(s[k], "u") for k in keys)})   # every line, in `keys` order
    losses = [{"n": e["loop"], "at": str(e["at"]), "until": str(e["until"]) if e.get("until") is not None else None,
               "count": e.get("count")} for e in rcfg["events"] if e.get("loop")]
    islands = [{"at": str(e["at"]), "until": str(e["until"])} for e in rcfg["events"] if e.get("island")]
    return {"keys": [[k, *rec.lines[k][:2]] for k in keys], "start": _iso(rec.d0), "end": _iso(rec.d1), "days": out, "losses": losses, "islands": islands,
            "brief": {k: brief.get(k, []) for k in ("Ferosplavna-1", "Dniprovska")}}


def repairs() -> list[dict]:
    doc = yaml.safe_load((NOTES / "repairs.yaml").read_text())
    out = []
    for r in doc["repairs"]:
        w = str(r["when"])
        when = w[:10] if len(w) >= 10 else w[:7] + "-15"
        cut, approx = CUT.get(r["id"], (None, 0))
        out.append({"id": r["id"], "line": line_of(r), "when": when, "cut": cut, "cut_month_only": bool(approx),
                    "side": r["side"], "truce": bool(r.get("arranged_by")),
                    "placed": r.get("region") is not None,
                    "never": r["id"] == "R45",   # Dniprovska repaired in June 2026, its substation too damaged to reconnect
                    "what": r["what"]})
    return sorted(out, key=lambda r: r["when"])


def build() -> Path:
    cfg = network.config("znpp", None)
    data = {"record": day_states(cfg["record"]), "repairs": repairs(), "axis_end": END.isoformat(),
            "rgb": {"750": [255, 214, 0], "330": [240, 156, 0]}}   # the zoom-out's line_rgb: two yellows, 750 kV the brighter
    OUT.mkdir(exist_ok=True)
    (OUT / "data.json").write_text(json.dumps(data, indent=1, ensure_ascii=False))
    (OUT / "data.js").write_text("window.DATA = " + json.dumps(data, ensure_ascii=False) + ";\n")
    shutil.copy(WEB / "d3.v7.9.0.min.js", OUT / "d3.v7.9.0.min.js")
    return OUT


OPTS = ["arcs", "calendar", "deficit", "parsets", "swarm", "dots", "cal_split", "cal_ten", "cal_spiral", "cal_waffle", "cal_waffle_bw", "cal_waffle_bw2", "cal_waffle_bw3"]


def shoot(opts: list[str], scale: int = 1) -> list[Path]:
    from playwright.sync_api import sync_playwright

    page_url = (OUT / "time.html").resolve().as_uri()
    done = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        pg = browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=scale)
        for o in opts:
            pg.goto(f"{page_url}?opt={o}")
            pg.wait_for_function("window.DRAWN === true")
            errs = pg.evaluate("window.ERRS || []")
            if errs:
                raise RuntimeError(f"{o}: {errs}")
            f = OUT / f"time_{o}_{1920 * scale}.png"
            pg.screenshot(path=str(f))
            done.append(f)
        browser.close()
    return done


def anim(fps: int = 30, opt: str = "cal_waffle_anim", name: str = "repair_days_waffle") -> Path:
    """The waffle animated (the user, 9 November 2026: "for the animation pass of this please center the graphic ...
    each square can be animated to appear from left to right, top to bottom"): the page's `drawAt(t)` for each frame,
    screenshotted in the installed Chrome and piped to FFmpeg; silent. A contact sheet of nine moments and a json of the
    timeline beside it."""
    import hashlib
    import io
    import math
    import subprocess

    from PIL import Image
    from playwright.sync_api import sync_playwright

    page_url = (OUT / "time.html").resolve().as_uri()
    mp4, sheet = OUT / f"{name}.mp4", OUT / f"{name}_sheet.jpg"
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        pg = browser.new_page(viewport={"width": 1920, "height": 1080})
        pg.goto(f"{page_url}?opt={opt}")
        pg.wait_for_function("window.DRAWN === true")
        errs = pg.evaluate("window.ERRS || []")
        if errs:
            raise RuntimeError(f"{opt}: {errs}")
        tl = pg.evaluate("window.TIMELINE")
        n = math.ceil(tl["duration_s"] * fps)
        ff = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "image2pipe", "-framerate", str(fps), "-i", "-",
                               "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                               "-r", str(fps), str(mp4)], stdin=subprocess.PIPE)
        g = tl["groups"]
        moments = [0.6, tl["fill"]["start_s"] - 0.1, g[1]["start_s"] + 0.8, g[2]["start_s"] + 1.0, g[2]["end_s"] - 0.5, g[3]["start_s"] + 2.0,
                   g[4]["start_s"] + 0.2, tl["fill"]["end_s"] + 0.3]
        picks = {round(m * fps): m for m in moments} | {n - 1: (n - 1) / fps}
        thumbs = {}
        for f in range(n):
            pg.evaluate(f"drawAt({f / fps})")
            png = pg.screenshot(type="png")
            ff.stdin.write(png)
            if f in picks:
                thumbs[f] = Image.open(io.BytesIO(png)).convert("RGB")
            if f == n - 1:
                (OUT / f"{name}_last.png").write_bytes(png)
        ff.stdin.close()
        if ff.wait():
            raise RuntimeError("ffmpeg failed")
        browser.close()
    tw, th = 640, 360
    im = Image.new("RGB", (tw * 3, th * 3), (0, 0, 0))
    for i, f in enumerate(sorted(thumbs)):
        im.paste(thumbs[f].resize((tw, th), Image.LANCZOS), ((i % 3) * tw, (i // 3) * th))
    im.save(sheet, quality=90)
    doc = {"title": tl["title"]["text"], "file": mp4.name, "sha256": hashlib.sha256(mp4.read_bytes()).hexdigest(),
           "fps": fps, "size": [1920, 1080], "frames": n, "sound": None, "timeline": tl,
           "sheet": {"file": sheet.name, "moments_s": [round(f / fps, 3) for f in sorted(thumbs)]},
           "drawn": "every day of the record (24 February 2022 to 11 September 2026) a square, grouped by how many of the "
                    "plant's ten lines were connected at the end of the day (white ten, light grey two, dark grey one, black "
                    "none; hatched where the reports don't say which lines were cut), in date order within each group, a row "
                    "of 60 days with its first day's date on the left; a dot on the day of each repair, by who did it (white "
                    "Ukrainian crews, grey Russian crews, half and half both, black ringed white unspecified). R48 (23 "
                    "October 2026) falls after the record's last report and has no square. No places shown: none of the "
                    "repairs is placed, so the safety rule holds by itself. The squares appear one by one at a constant "
                    "rate, group after group, so a group's time on screen is its share of the days: a drawing convention.",
           "sources": {"record": "config/conductive-seam.yaml networks.znpp.record (the zoom-out's: IAEA updates, WNA and "
                                 "OECD-NEA chronologies, Energoatom, news), each line's state at the end of each day",
                       "repairs": "research_notes/Repair regions still/repairs.yaml (each repair's sources there)",
                       "data": "time/data.json (repair_time.build())"}}
    (OUT / f"{name}.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False))
    return mp4


if __name__ == "__main__":
    build()
    if sys.argv[1:2] == ["--anim"]:
        print("wrote", anim().relative_to(ROOT))
        sys.exit()
    for f in shoot(sys.argv[1:] or OPTS):
        print("wrote", f.relative_to(ROOT))
