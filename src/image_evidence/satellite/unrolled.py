"""The two last lines unrolled (NEXT.md I5, idea 1; the user, 4 November 2026: time "left to right, not unrolling down
like a scroll", and "only the most critical stuff"): Ferosplavna-1 and Dniprovska drawn on the map, then each unrolled
like a tape into an upright bar (its switchyard at the bottom, km up it, north as on the map, so the river crosses it as
a band), and the bars move right with the date while the frame pans with them, each line's reported state left behind
as a ribbon (lit while connected, dark while cut, dotted where the reports don't say which), the complete losses across
both, and the repair truces as regions in the ribbons, as tall as their sources say where the work was (a Marey chart,
as train timetables are drawn, on its side).

The safety rule (CLAUDE.md, NEXT.md I5): a repair is drawn only as a stretch of line of at least about 3 km and never
finer than its source: the side of the front, a bank or the crossing (the shores the day before the dam, the channel
after it, from the survey's water masks), or the whole bar where no place was published. A narrower region is refused.
Never a tower, a pin or a crew; the bars stop at `show_km` (both lines go on, said so; Dniprovska's substation never
shown).

Drawn with D3 in a page (`unrolled_web/`) that draws any moment on demand (`draw(t)`), each frame taken from Chrome
headless (Playwright, the installed Chrome) and encoded by FFmpeg. `unrolled.json` beside the film is what the page
draws, with every source: the lines (OpenStreetMap through network.json), the record's states (record.py, the config's
dated reports), the truces (the config's `unrolled.truces`).
"""

from __future__ import annotations

import hashlib
import json
import math
import shutil
import subprocess
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from . import network, record, zoomout
from .scene3d import export

WEB = Path(__file__).parent / "unrolled_web"
MIN_REGION_M = 3000.0      # the safety rule: a repair's region at least about 3 km of line
STEP_M = 100.0             # the bars' points, every 100 m along the line
SHORE_CLOSE_M = 600.0      # the reservoir's outline: inlets narrower than this closed (zoomout._shoreline)


def out_dir(root: Path, network_id: str) -> Path:
    return network.network_dir(root, network_id) / "unrolled"


def _day(v: Any) -> int:
    return record._day(v)


def _iso(d: int) -> str:
    return date.fromordinal(int(d)).isoformat()


def _stretch(survey: dict[str, Any], pass_id: str, drawn: str) -> dict[str, Any]:
    """The longest water stretch along the line on that pass (survey.json: metres along the line from its start)."""
    st = survey["water"][pass_id]["lines"][drawn]["stretches"]
    if not st:
        raise ValueError(f"{pass_id}: no water along {drawn}")
    return max(st, key=lambda s: s["to_m"] - s["from_m"])


def _states(rec: record.Record, key: str) -> list[list[Any]]:
    """The line's state day by day as runs [first day, day after the last, state], read at the end of each day (from a
    record without the cuts over within the day: those are ticks of their own, not runs)."""
    runs: list[list[Any]] = []
    for d in range(rec.d0, rec.d1 + 1):
        s = rec.state(key, rec.t(d + 1) - 1e-3) if d < rec.d1 else rec.state(key, rec.t1 + 1e-3)
        if runs and runs[-1][2] == s:
            runs[-1][1] = d + 1
        else:
            runs.append([d, d + 1, s])
    return [[_iso(a), _iso(b), s] for a, b, s in runs]


def _plan(L: zoomout.Line, show_m: float) -> np.ndarray:
    """The line's first `show_m` every STEP_M along it, in metres east and north of the plant."""
    s = np.arange(0.0, show_m + 1e-6, STEP_M)
    if s[-1] < show_m:
        s = np.append(s, show_m)
    return np.stack([np.interp(s, L.cum, L.xy[:, 0]), np.interp(s, L.cum, L.xy[:, 1]), s], 1)


def _shore(net: dict[str, Any], plane: zoomout.Plane, box: tuple[float, float, float, float]) -> list[list[list[float]]]:
    """The former reservoir's outer shore (OSM's Великий Луг, as the zoom-out draws it), cut to the map's box."""
    rings = [plane.xy(r) for a in net.get("areas") or [] for r in a["rings"]]
    if not rings:
        return []
    x0, y0, x1, y1 = box
    out = []
    for ring in zoomout._shoreline(rings, SHORE_CLOSE_M, res=50.0):
        inside = (ring[:, 0] >= x0) & (ring[:, 0] <= x1) & (ring[:, 1] >= y0) & (ring[:, 1] <= y1)
        run: list[list[float]] = []
        for p, ok in zip(ring, inside):
            if ok:
                run.append([round(float(p[0]), 1), round(float(p[1]), 1)])
            elif run:
                if len(run) > 1:
                    out.append(run)
                run = []
        if len(run) > 1:
            out.append(run)
    return out


def truce(t: dict[str, Any], ln: dict[str, Any] | None) -> dict[str, Any]:
    """A truce placed on its line: the stretch its source names (one of the line's `regions`), refused if narrower
    than the safety rule allows."""
    if ln is None:
        raise ValueError(f"truce {t['n']}: {t['line']} isn't drawn")
    if t["region"] not in ln["regions"]:
        raise ValueError(f"truce {t['n']}: no region {t['region']!r} (one of {', '.join(ln['regions'])})")
    a, b = ln["regions"][t["region"]]
    if b - a < MIN_REGION_M:
        raise ValueError(f"truce {t['n']}: its region ({t['region']}, {(b - a) / 1000:.1f} km) is narrower than the "
                         f"safety rule's {MIN_REGION_M / 1000:.0f} km")
    return {**{k: (str(v) if isinstance(v, date) else v) for k, v in t.items()}, "from_m": a, "to_m": b}


def data(root: Path, cfg: dict[str, Any]) -> dict[str, Any]:
    """Everything the page draws, with its sources."""
    u = cfg["unrolled"]
    net = json.loads((network.network_dir(root, cfg["id"]) / "network.json").read_text())
    survey = json.loads((export.scene_dir(root, cfg["id"]) / "survey.json").read_text())
    plane = zoomout.Plane(*net["plant"]["lonlat"])
    rec = record.Record(cfg["record"], 0.0)
    # the states day by day from the record without what was over within the day (on film each is a blink at the
    # start of its interval, which would spill into the days after it here): those are ticks of their own
    days = record.Record({**cfg["record"], "events": [e for e in cfg["record"]["events"]
                                                      if not record.Record._within_day(e)]}, 0.0)
    show_m = float(u["show_km"]) * 1000
    lines, plans = [], []
    for spec in u["lines"]:
        ln = next((x for x in net["lines"] if x["name"] == spec["drawn"]), None)
        if ln is None:
            raise ValueError(f"unrolled: no line {spec['drawn']!r} in network.json")
        L = zoomout.Line(ln, plane)
        shown = min(show_m, L.length)
        pl = _plan(L, shown)
        water, river = _stretch(survey, u["water_pass"], spec["drawn"]), _stretch(survey, u["river_pass"], spec["drawn"])
        for st in (water, river):  # the survey's distances are along the same trace: its north matches ours
            y = float(np.interp(st["from_m"], L.cum, L.xy[:, 1]))
            if abs(y - st["north_m"][0]) > 250:
                raise ValueError(f"unrolled: {spec['drawn']} water at {st['from_m']} m is {y:.0f} m north here, "
                                 f"{st['north_m'][0]} m in the survey")
        front = (river["from_m"] + river["to_m"]) / 2
        regions = {"south_bank": [0.0, float(water["from_m"])], "crossing": [float(water["from_m"]), float(water["to_m"])],
                   "north_bank": [float(water["to_m"]), shown], "occupied": [0.0, front], "held": [front, shown],
                   "unknown": [0.0, shown]}
        brief = [{"at": str(e["at"]), "note": e.get("note"), "src": e.get("src", [])} for e in cfg["record"]["events"]
                 if not e.get("loop") and record.Record._within_day(e) and spec["record"] in rec._keys(e.get("lines", []))]
        lines.append({"record": spec["record"], "drawn": spec["drawn"], "label": spec["label"], "kv": int(ln["kv"]),
                      "from": spec["from"], "to": spec["to"], "length_m": round(L.length, 1), "shown_m": round(shown, 1),
                      "cut": shown < L.length,
                      "plan": [[round(float(x), 1), round(float(y), 1), round(float(s), 1)] for x, y, s in pl],
                      "shores": {"south_m": float(water["from_m"]), "north_m": float(water["to_m"]),
                                 "pass": u["water_pass"], "acquired": survey["water"][u["water_pass"]]["acquired"]},
                      "front_m": round(front, 1), "front_pass": u["river_pass"],
                      "regions": regions, "states": _states(days, spec["record"]), "brief": brief})
        plans.append(pl)
    allp = np.vstack(plans)
    pad = 2500.0
    box = (float(allp[:, 0].min() - pad), float(allp[:, 1].min() - pad), float(allp[:, 0].max() + pad),
           float(allp[:, 1].max() + pad))
    by = {ln["record"]: ln for ln in lines}
    truces = [truce(t, by.get(t["line"])) for t in u["truces"]]
    losses = [{"n": e["loop"], "at": str(e["at"]), "until": str(e["until"]) if e.get("until") is not None else None,
               "count": e.get("count"), "note": e.get("note"), "src": e.get("src", [])}
              for e in cfg["record"]["events"] if e.get("loop")]
    captions = [{"at": str(e["at"]), "text": e["caption"], "src": e.get("src", [])}
                for e in cfg["record"]["events"] if e.get("caption")]
    srcs = {**(cfg["record"].get("sources") or {}), **(u.get("sources") or {})}
    used = {s for t in u["truces"] for s in t.get("src", [])} | set(u["sides"].get("sources", [])) | set(u["dam"]["src"])
    used |= {s for e in cfg["record"]["events"] for s in e.get("src", [])}
    missing = sorted(s for s in used if s not in srcs)
    if missing:
        raise ValueError(f"unrolled: sources not in the config: {', '.join(missing)}")
    sc = _day(u["scale_change"])
    return {
        "schema": "unrolled/1", "network_id": cfg["id"], "title": u["title"],
        "made_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "start": _iso(rec.d0), "end": _iso(rec.d1), "dam": {**u["dam"], "at": str(u["dam"]["at"])}, "scale_change": _iso(sc),
        "px_per_day": [float(x) for x in u["px_per_day"]], "show_m": show_m, "sides": u["sides"],
        "map": {"box": [round(x, 1) for x in box], "shore": _shore(net, plane, box),
                "plant": [0.0, 0.0], "tpp": [round(float(v), 1) for v in plane.xy([net["origins"]["tpp330"]["lonlat"]])[0]]},
        "lines": lines, "truces": truces, "losses": losses, "captions": captions,
        "sources": {k: srcs[k] for k in sorted(used)},
        "statement": (
            "The lines are OpenStreetMap's (network.json), straightened: distance along each line from its switchyard, "
            "the first {km:.0f} km (Dniprovska runs on to its substation, not shown), its switchyard at the bottom. "
            "Time runs left to right, the last year at six times the scale (said on the axis). Each line's state is the record's, from dated reports (the "
            "IAEA's updates, through the WNA's chronology, and news reports): lit while connected, dark while cut, "
            "dotted where the reports don't say which lines were cut; complete losses of off-site power across both "
            "(the IAEA's count). The reservoir's shores along each line are from Sentinel-2 the day before the dam was "
            "destroyed; the channel through the drained bed, taken as the front between the sides the reports name, "
            "from a pass three months after. The truces are drawn where their sources say the work was, never finer: "
            "a side of the front, a bank or the crossing, or the whole bar where no place was published; never a "
            "tower or a crew. Hatching and dashed edges mean a region, not a point.").format(km=show_m / 1000),
    }


# ------------------------------------------------------------------ the film's time

def timeline(d: dict[str, Any], fps: int) -> dict[str, Any]:
    """When the page draws what: the opening (fade in, the lines growing on the map, the unrolling, the bands), the
    run (the date eased from one stop to the next, held at each: the dam, the losses on diesel, each truce's end),
    and the overview (the whole record fitted to the frame, held, faded)."""
    a, b = d["px_per_day"]
    sc = _day(d["scale_change"])
    d0 = _day(d["start"])

    def y(day: int) -> float:
        return (min(day, sc) - d0) * a + max(0, day - sc) * b

    stops = [(_day(d["dam"]["at"]), 1.4, "dam")]
    stops += [(_day(x["at"]), 1.8, "loss") for x in d["losses"] if x["until"] and _day(x["at"]) >= sc]
    stops += [(_day(t["until"]), 2.2, f"truce {t['n']}") for t in d["truces"] if not t.get("open_end")]
    stops += [(_day(c["at"]), 2.0, "caption") for c in d["captions"] if _day(c["at"]) >= sc]
    days = {}
    for day, hold, why in stops:
        h, w = days.get(day, (0.0, []))
        days[day] = (max(h, hold), w + [why])
    keys = [(d0, 0.0, ["start"])] + [(k, *days[k]) for k in sorted(days) if d0 < k < _day(d["end"])]
    keys.append((_day(d["end"]), 2.0, ["end"]))
    run0 = 11.0
    t, out = run0, []
    for i, (day, hold, why) in enumerate(keys):
        if i:
            px = y(day) - y(keys[i - 1][0])
            t += max(1.2, px / 130.0 + 0.6)  # about 130 px of chart a second, eased in and out between stops
        out.append({"day": _iso(day), "x": y(day), "arrive_s": round(t, 3), "hold_s": hold, "why": why})
        t += hold
    run1 = t
    o = {"fade_in": [0.0, 1.0], "grow": [0.6, 4.6], "unroll": [5.0, 9.0], "bands": [8.4, 10.8], "run": [run0, run1],
         "overview": [run1 + 0.8, run1 + 5.8], "fade_out": [run1 + 12.0, run1 + 14.0], "total": run1 + 14.0,
         "stops": out, "x_end": y(_day(d["end"])), "fps": fps}
    o["frames"] = int(math.ceil(o["total"] * fps))
    return o


# ------------------------------------------------------------------ rendering

def _frames(page, n: int, fps: int, ts: list[float] | None = None):
    for t in (ts if ts is not None else [i / fps for i in range(n)]):
        page.evaluate("t => window.draw(t)", t)
        yield page.screenshot(type="png", full_page=False, animations="disabled")


def render(root: Path, cfg: dict[str, Any], fps: int | None = None, seconds: tuple[float, float] | None = None,
           stills: list[float] | None = None) -> dict[str, Any]:
    """The film (or a stretch of it, or stills) into `unrolled/`, with unrolled.json and a contact sheet."""
    from playwright.sync_api import sync_playwright

    u = cfg["unrolled"]
    fps = int(fps or u.get("fps", 60))
    W, H = int(u.get("width", 1920)), int(u.get("height", 1080))
    out = out_dir(root, cfg["id"])
    out.mkdir(parents=True, exist_ok=True)
    d = data(root, cfg)
    tl = timeline(d, fps)
    d["time"] = tl
    d["files"] = {"page": "page/index.html"}
    page_dir = out / "page"  # the page as drawn (so the film can be drawn again from what is beside it)
    if page_dir.exists():
        shutil.rmtree(page_dir)
    shutil.copytree(WEB, page_dir)
    (page_dir / "unrolled.data.js").write_text("window.DATA = " + json.dumps(d, ensure_ascii=False) + ";\n")
    t0 = time.time()
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        page.goto((page_dir / "index.html").as_uri())
        page.wait_for_function("window.ready === true", timeout=30000)
        if stills:
            paths = []
            for t, png in zip(stills, _frames(page, 0, fps, stills)):
                f = out / f"still_{t:07.2f}.png"
                f.write_bytes(png)
                paths.append(str(f))
            browser.close()
            return {"stills": paths, "total_s": tl["total"]}
        i0, i1 = (0, tl["frames"]) if not seconds else (int(seconds[0] * fps), min(tl["frames"], int(seconds[1] * fps)))
        name = u["title"] + (f"_{seconds[0]:g}-{seconds[1]:g}s" if seconds else "")
        mp4 = out / f"{name}.mp4"
        ff = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "image2pipe", "-c:v", "png",
                               "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "16",
                               "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(mp4)], stdin=subprocess.PIPE)
        sheet_at = set(np.linspace(i0, i1 - 1, 24).astype(int).tolist())
        sheet = []
        try:
            for i, png in zip(range(i0, i1), _frames(page, 0, fps, [i / fps for i in range(i0, i1)])):
                ff.stdin.write(png)
                if i in sheet_at:
                    sheet.append(png)
        finally:
            ff.stdin.close()
            browser.close()
        if ff.wait() != 0:
            raise RuntimeError("ffmpeg failed to encode the unrolled film")
    _contact(sheet, out / f"{name}_contact.webp")
    d["files"].update({"video": mp4.name, "contact": f"{name}_contact.webp"})
    d["render"] = {"fps": fps, "width": W, "height": H, "frames": i1 - i0, "seconds": round(time.time() - t0, 1),
                   "browser": "Google Chrome (headless, Playwright)", "d3": "7.9.0",
                   "d3_sha256": hashlib.sha256((WEB / "d3.v7.9.0.min.js").read_bytes()).hexdigest()}
    if not seconds:
        (out / "unrolled.json").write_text(json.dumps(d, ensure_ascii=False, indent=1))
    return {"mp4": str(mp4), "frames": i1 - i0, "seconds": d["render"]["seconds"], "duration_s": round(tl["total"], 1)}


def _contact(pngs: list[bytes], path: Path) -> None:
    import io

    from PIL import Image

    if not pngs:
        return
    ims = [Image.open(io.BytesIO(b)).convert("RGB").resize((480, 270), Image.LANCZOS) for b in pngs]
    cols = 4
    sheet = Image.new("RGB", (480 * cols, 270 * math.ceil(len(ims) / cols)))
    for k, im in enumerate(ims):
        sheet.paste(im, ((k % cols) * 480, (k // cols) * 270))
    sheet.save(path, quality=88)
