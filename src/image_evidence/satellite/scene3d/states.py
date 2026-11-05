"""The lines' record in 3D (the user's call, 25 October 2026): the two lines on screen, Ferosplavna-1 on the left and
Dniprovska on the right, heard and seen as they were cut off and reconnected, from the day the 3D takes over from the
zoom-out (the IAEA's zone, 6 September 2022) to the last report.

The network's `record` (record.py: every change a dated report with its sources), kept to these two lines and to the
complete losses of off-site power (which cut both), and paced so a listener can tell which side is live: every state
held at least `min_hold_s`, a line fading out over `fade_off_s` and back over `fade_on_s`. Outages over within the day
(a few hours) are left out (`within_day: omit`): at this pace each would be a blink, and there are 25 of them (18 of
them complete losses, most in 2026); they are listed in the doc as left out, never shown as if they hadn't happened.
The drawn row of Ferosplavna carries both its circuits; it shows Ferosplavna-1's state (the IAEA's "back-up line").
Where the reports don't say which lines were cut (Ferosplavna-1 until 29 December 2022), it is unknown: grey and
muffled, as in the 2D film, never shown as on or off. A span begun before the 3D's start and still running then (island
mode, 5-10 September 2022) is held from the first frame (`from_start`) and ends on its own day.
"""

from __future__ import annotations

import copy
import math
from datetime import date
from typing import Any

import numpy as np

from ..record import Record, _day, _state


def options(c3: dict[str, Any], v: dict[str, Any]) -> dict[str, Any]:
    """The record's options for a variant: the shared `record`, with what the variant's own `record` mapping changes
    (its pacing, pins, and each line's side, pan and label: flying south the lines are on the other sides)."""
    own = v.get("record") if isinstance(v.get("record"), dict) else {}
    o = {**c3["record"], **{k: x for k, x in own.items() if k != "lines"}}
    o["lines"] = {k: {**x, **(own.get("lines") or {}).get(k, {})} for k, x in c3["record"]["lines"].items()}
    return o


def record(net_record: dict[str, Any], o: dict[str, Any]) -> tuple[Record, dict[str, Any]]:
    """The 3D's own Record (film time = the video's seconds) and what was left out."""
    keep = list(o["lines"])
    groups = {"all": list(net_record["lines"]), **(net_record.get("groups") or {})}
    start = _day(o["start"])
    events, left_out = [], []
    first = {k: "on" for k in keep}  # each line's state when the 3D takes over: the lasting changes before it
    for e in net_record["events"]:
        names = [e["lines"]] if isinstance(e.get("lines"), str) else e.get("lines", [])
        hit = [k for n in names for k in groups.get(n, [n]) if k in keep]
        lasting = not (e.get("until") is not None or e.get("brief") or e.get("loop"))
        if _day(e["at"]) < start:
            if (hit or e.get("loop")) and e.get("until") is not None and _day(e["until"]) > start:
                events.append({**{k: v for k, v in e.items() if k != "caption"}, "at": o["start"], "from_start": True,
                               "began": str(e["at"]),
                               **({"lines": hit} if hit else {})})
            elif hit and "to" in e and lasting:
                first.update({k: _state(e["to"]) for k in hit})
            continue
        if not (hit or e.get("loop") or str(e["at"]) in {str(d) for d in o.get("dates", [])}):
            continue
        if (hit or e.get("loop")) and Record._within_day(e) and o.get("within_day") == "omit":
            left_out.append({"at": str(e["at"]), "lines": hit or keep, "loop": e.get("loop"), "note": e.get("note"),
                             "sources": e.get("src", []), "why": "over within the day"})
            continue
        if any(str(x["at"]) == str(e["at"]) and set(x.get("lines") or keep) == set(hit or keep) for x in o.get("omit", [])):
            left_out.append({"at": str(e["at"]), "until": str(e["until"]) if e.get("until") is not None else None,
                             "lines": hit or keep, "loop": e.get("loop"), "note": e.get("note"),
                             "sources": e.get("src", []), "why": "left out for pace (`omit`)"})
            continue
        events.append({**{k: v for k, v in e.items() if k != "caption"}, **({"lines": hit} if hit else {})})
    cfg = {**copy.deepcopy(net_record), "start": o["start"], "events": events, "groups": {},
           "lines": {k: net_record["lines"][k] for k in keep}, "caption_hold_s": 0}
    cfg.pop("zone", None)
    for k in ("at_s", "intro_s", "run_s", "outro_s", "min_hold_s", "loss_hold_s", "loss_day_s", "loss_max_s",
              "fade_on_s", "fade_off_s", "pins", "steps"):
        if k in o:
            cfg[k] = o[k]
    rec = Record(cfg, float(o["at_s"]))
    for k in keep:  # from the first frame (the sound fades in before the date appears)
        rec.base[k][0] = (-math.inf, first[k])
    doc = {**rec.doc(), "first_states": first, "lines_shown": {k: v for k, v in o["lines"].items()},
           "left_out": {"rule": "outages over within the day (a few hours) are left out at this pace, and the brief "
                                "cuts in `omit` so the rest keeps its pace; each is listed, never shown as if it hadn't "
                                "happened", "events": left_out},
           "statement": "The two lines' states from the record's dated reports (sources in each event); the drawn "
                        "Ferosplavna row shows Ferosplavna-1's state."}
    return rec, doc


def weights(rec: Record, key: str, t: float) -> list[float]:
    """How far the line is connected and how far unreported at t ([on, unknown]; the rest cut off): eased in over
    `fade_on_s`, out over `fade_off_s`."""
    m = rec.mix(key, t)
    return [round(float(m.get("on", 0.0)), 4), round(float(m.get("unknown", 0.0)), 4)]


def per_frame(rec: Record, o: dict[str, Any], n: int, fps: int) -> list[dict[str, Any]]:
    """Each frame's line states (by drawn line: [on, unknown]) and the date shown (the water's level and the bed's
    imagery by the record's day: export.scene, from bed.py)."""
    out = []
    for i in range(n):
        t = i / fps
        d = rec.shown(t)
        out.append({"lines": {v["drawn"]: weights(rec, k, t) for k, v in o["lines"].items()},
                    "date": d.isoformat() if d else None,
                    **({"island": round(rec.island_weight(t), 4)} if rec.island_weight(t) > 0 else {})})
    return out


def others_per_frame(net_record: dict[str, Any], o: dict[str, Any], rows: list[dict[str, Any]], rec: Record,
                     frames: list[dict[str, Any]], fps: int) -> list[dict[str, list[float]]]:
    """Each frame's states for the plant's other rows (export.other_rows), by the date the film shows: a row with a
    `record` name from the record, read on that day once its change has faded in (its own run, so the film's pacing
    stays the two lines'); a row that `follows` a line, as that line's drawn row is in the frame
    (`frames[i]["lines"]`)."""
    names = sorted({r["record"] for r in rows if r.get("record")})
    own = None
    if names:
        oo = {**o, "lines": {k: {"drawn": k} for k in names}, "pins": [], "omit": [], "steps": [], "dates": [],
              "at_s": 0.0, "intro_s": 0.0, "run_s": 4000.0}
        own, _ = record(net_record, oo)
    drawn = {k: v["drawn"] for k, v in o["lines"].items()}
    settle = max(float(o.get("fade_on_s", 0.0)), float(o.get("fade_off_s", 0.0)))
    out = []
    for i, f in enumerate(frames):
        d = rec.shown(i / fps)
        at = own.t(d.toordinal() if d else rec.days(i / fps)) + settle if own else 0.0
        out.append({r["name"]: (weights(own, r["record"], at) if r.get("record")
                                else list((f.get("lines") or {}).get(drawn[r["follows"]], (0.0, 0.0))))
                    for r in rows})
    return out


def date_label(iso: str | None) -> str:
    return date.fromisoformat(iso).strftime("%-d %B %Y").upper() if iso else ""


def flow_toward(fo: dict[str, Any], iso: str | None) -> int:
    """Which way power runs along the connected lines on that day, by the config's dated, sourced `periods`: +1 in to
    the plant (backward along a line traced from it), -1 out to the grid, 0 where no period covers the day (no flow
    drawn). Before the date is shown, the first period's."""
    periods = sorted(fo["periods"], key=lambda p: str(p["from"]))
    d = _day(iso) if iso else _day(periods[0]["from"])
    now = [p for p in periods if _day(p["from"]) <= d and (p.get("until") is None or d <= _day(p["until"]))]
    return {"plant": 1, "grid": -1}[now[-1]["toward"]] if now else 0


def flow_doc(fo: dict[str, Any]) -> dict[str, Any]:
    return {"dash_m": float(fo["dash_m"]), "speed_mps": float(fo["speed_mps"]), "periods": fo["periods"],
            "statement": "Dashes running along each connected line toward where its power goes, by the dated periods "
                         "and their sources: a drawing convention (the direction sourced; spacing and speed drawn, "
                         "not measured). None on a line cut off or unreported."}
