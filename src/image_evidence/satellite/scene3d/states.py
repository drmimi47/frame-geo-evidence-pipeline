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
    """The 3D's own Record (film time = the video's seconds) and what was left out. With `select` (look pass 3) the
    date jumps between chosen dates instead (`Selected`)."""
    if o.get("select"):
        sel = Selected(net_record, o)
        return sel, sel.doc()
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
              "at_s": 0.0, "intro_s": 0.0, "run_s": 4000.0, "select": None}
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


def flow_config(fo: dict[str, Any], v: dict[str, Any]) -> dict[str, Any]:
    """The flow's options for a variant: the shared ones, with the variant's own dated, sourced `flow_periods` added
    (look pass 3: power out to the grid before the war; kept to the variant, so the approved films, whose frames
    before the date is shown take the first period's direction, stay as they were)."""
    extra = v.get("flow_periods") or []
    return {**fo, "periods": list(extra) + list(fo["periods"])} if extra else fo


def flow_doc(fo: dict[str, Any]) -> dict[str, Any]:
    return {"dash_m": float(fo["dash_m"]), "speed_mps": float(fo["speed_mps"]), "periods": fo["periods"],
            "statement": "Dashes running along each connected line toward where its power goes, by the dated periods "
                         "and their sources: a drawing convention (the direction sourced; spacing and speed drawn, "
                         "not measured). None on a line cut off or unreported."}


# ------------------------------------------------------------------ look pass 3: selected dates

SELECT_STATEMENT = ("States shown on selected dates; the changes between them left out; the full record in the "
                    "zoom-out. On each date both lines show exactly the state the network record gives for that day "
                    "(its dated reports and their sources); outages over within the day are not shown.")


def day_states(net_record: dict[str, Any], keys: list[str], day: Any) -> dict[str, Any]:
    """Each line's state on a day as the network record gives it (record.py's rules): the last lasting change at or
    before the day, overridden by a span covering it (an outage with `until`, a complete loss, island mode); outages
    over within the day are not a day's state (listed in `within_day`). Also whether the day is in island mode or a
    complete loss lasting days, and the events that set each state (their sources)."""
    groups = {"all": list(net_record["lines"]), **(net_record.get("groups") or {})}
    d = _day(day)
    base = {k: ("on", None) for k in keys}
    spans: list[tuple[list[str], str, dict[str, Any]]] = []
    within = []
    for e in sorted(net_record["events"], key=lambda e: _day(e["at"])):
        if _day(e["at"]) > d:
            break
        names = [e["lines"]] if isinstance(e.get("lines"), str) else e.get("lines", [])
        hit = list(keys) if e.get("loop") else [k for n in names for k in groups.get(n, [n]) if k in keys]
        if not hit:
            continue
        if Record._within_day(e):
            if _day(e["at"]) == d:
                within.append({"at": str(e["at"]), "lines": hit, "loop": e.get("loop"), "note": e.get("note")})
            continue
        if e.get("until") is not None:
            if _day(e["at"]) <= d < _day(e["until"]):
                spans.append((hit, "off" if e.get("loop") else _state(e.get("to", "off")), e))
        elif "to" in e:
            for k in hit:
                base[k] = (_state(e["to"]), e)
    out, why = {}, {}
    for k in keys:
        hit = next(((s, e) for ks, s, e in spans if k in ks), None)   # the first span listed wins, as in Record.state
        out[k], ev = hit if hit else base[k]
        why[k] = ({"at": str(ev["at"]), **({"until": str(ev["until"])} if ev.get("until") is not None else {}),
                   "sources": ev.get("src", [])} if ev else None)
    return {"states": out, "set_by": why, "within_day": within,
            "island": any(e.get("island") for _, _, e in spans),
            "loss": any(e.get("loop") for _, _, e in spans)}


class Selected:
    """The record on selected dates (look pass 3, the user, 7 November 2026): the date shown jumps from one chosen
    date to the next (`select`: each `at` a date, `s` the film time it is shown from, placed by where the camera is);
    on each, both lines show exactly the state the network record gives for that day (`day_states`), checked against
    the entry's `expect` (refused if they differ). Nothing between is shown. A line's change is eased as in Record
    (`fade_on_s`, `fade_off_s`); the record's day for what changes with the date (the water's level, the passes, the
    plants) eases to the new date over `ramp_s` from the jump, or runs on day by day to the next date (`run`: the
    falling water after the dam). The methods the 3D uses of Record: shown, day, days, state, states, mix,
    in_island, island_weight, on_diesel, loss_weight."""

    def __init__(self, net_record: dict[str, Any], o: dict[str, Any]):
        keys = list(o["lines"])
        self.cfg = {"start": str(o["select"][0]["at"]), "end": str(o["select"][-1]["at"])}
        self.lines = {k: net_record["lines"][k] for k in keys}
        self.at = float(o["at_s"])
        self.fade_on, self.fade_off = float(o.get("fade_on_s", 0.6)), float(o.get("fade_off_s", 0.25))
        self.ramp = float(o.get("ramp_s", 1.5))
        sources = net_record.get("sources") or {}
        self.entries = []
        for x in sorted(o["select"], key=lambda x: float(x["s"])):
            ds = day_states(net_record, keys, x["at"])
            want = {k: _state(v) for k, v in (x.get("expect") or {}).items()}
            bad = {k: (v, ds["states"][k]) for k, v in want.items() if ds["states"].get(k) != v}
            if bad:
                raise ValueError(f"record selection {x['at']}: expected {bad} (expected, the record's) — the record "
                                 "gives otherwise; not forced")
            if x.get("island") is not None and bool(x["island"]) != ds["island"]:
                raise ValueError(f"record selection {x['at']}: island mode {x['island']} expected, the record gives {ds['island']}")
            if x.get("loss") is not None and bool(x["loss"]) != ds["loss"]:
                raise ValueError(f"record selection {x['at']}: complete loss {x['loss']} expected, the record gives {ds['loss']}")
            self.entries.append({"at": _day(x["at"]), "s": float(x["s"]), "run": bool(x.get("run")), **ds,
                                 "label": x.get("why"),
                                 "sources": sorted({s for v in ds["set_by"].values() if v for s in v["sources"]})})
        if any(b["s"] - a["s"] < 0 for a, b in zip(self.entries, self.entries[1:])):
            raise ValueError("record selection: film times out of order")
        if any(b["at"] < a["at"] for a, b in zip(self.entries, self.entries[1:])):
            raise ValueError("record selection: dates out of order")
        self.sources = sources
        self.t0, self.t1 = self.entries[0]["s"], self.entries[-1]["s"]
        self.d0 = self.entries[0]["at"]
        self._s = np.array([e["s"] for e in self.entries])
        self.changes = [e["at"] for e in self.entries]
        self.edges = {k: [e["s"] for a, e in zip(self.entries, self.entries[1:])
                          if a["states"][k] != e["states"][k]] for k in keys}

    def _i(self, t: float) -> int:
        return max(0, int(np.searchsorted(self._s, t, side="right")) - 1)

    def shown(self, t: float) -> date | None:
        return None if t < self.at else date.fromordinal(self.entries[self._i(t)]["at"])

    day = shown

    def days(self, t: float) -> float:
        """The record's day at t as a fraction (ordinal): held on each date, eased to the next over `ramp_s` from its
        jump, or running on day by day to the next date where the entry says `run`."""
        i = self._i(t)
        e = self.entries[i]
        if t < e["s"]:   # before the first date is shown
            return float(e["at"])
        if e["run"] and i + 1 < len(self.entries):
            n = self.entries[i + 1]
            return e["at"] + (n["at"] - e["at"]) * min(1.0, (t - e["s"]) / max(n["s"] - e["s"], 1e-9))
        if i > 0 and not self.entries[i - 1]["run"]:
            p = self.entries[i - 1]
            x = min(1.0, max(0.0, (t - e["s"]) / self.ramp))
            return p["at"] + (e["at"] - p["at"]) * x * x * (3 - 2 * x)
        return float(e["at"])

    def state(self, key: str, t: float) -> str:
        return self.entries[self._i(t)]["states"][key]

    def states(self, key: str, ts: np.ndarray) -> np.ndarray:
        idx = np.clip(np.searchsorted(self._s, ts, side="right") - 1, 0, len(self.entries) - 1)
        return np.array([e["states"][key] for e in self.entries], dtype=object)[idx]

    def mix(self, key: str, t: float) -> dict[str, float]:
        """As Record.mix: a cut dims in `fade_off_s`, a reconnection swells back over `fade_on_s`."""
        cur = self.state(key, t)
        past = [s for s in self.edges[key] if s <= t]
        if not past:
            return {cur: 1.0}
        tb = past[-1]
        prev = self.state(key, tb - 1e-6)
        x = min(1.0, max(0.0, (t - tb) / (self.fade_on if cur == "on" else self.fade_off)))
        w = x * x * (3 - 2 * x)
        return {cur: 1.0} if w >= 1 or prev == cur else {prev: 1 - w, cur: w}

    def _spans(self, flag: str) -> list[tuple[float, float]]:
        ends = list(self._s[1:]) + [math.inf]
        return [(e["s"] if i else -math.inf, b) for i, (e, b) in enumerate(zip(self.entries, ends)) if e[flag]]

    def in_island(self, t: float) -> bool:
        return self.entries[self._i(t)]["island"] and t >= self.at

    def island_weight(self, t: float, ease: float = 0.4) -> float:
        from ..record import _eased
        return _eased(self._spans("island"), t, ease)

    def on_diesel(self, t: float) -> bool:
        return bool(self.entries[self._i(t)]["loss"])

    def loss_weight(self, t: float, ease: float = 0.4) -> float:
        from ..record import _eased
        return _eased(self._spans("loss"), t, ease)

    def doc(self) -> dict[str, Any]:
        ends = [e["s"] for e in self.entries[1:]] + [None]
        return {"selected": True, "start": self.cfg["start"], "end": self.cfg["end"],
                "film_s": {"starts": round(self.at, 2), "first": round(self.t0, 2), "last": round(self.t1, 2)},
                "states": {"on": "connected to the plant (lit)", "off": "cut off (unlit)",
                           "unknown": "lines were cut and repaired, but the reports don't say which (dotted)"},
                "dates": [{"date": date.fromordinal(e["at"]).isoformat(), "film_s": [round(e["s"], 2),
                                                                                     round(b, 2) if b is not None else None],
                           "states": e["states"], "island": e["island"], "complete_loss": e["loss"],
                           "set_by": e["set_by"], "within_day_left_out": e["within_day"],
                           "sources": [self.sources.get(s, s) for s in e["sources"]],
                           **({"why": e["label"]} if e["label"] else {}),
                           **({"runs_on": True} if e["run"] else {})}
                          for e, b in zip(self.entries, ends)],
                "time": f"the date shown jumps between the selected dates; a cut dims in {self.fade_off} s, a "
                        f"reconnection swells back over {self.fade_on} s; what changes with the date (the water's "
                        f"level, the passes, the plants) eases to the new date over {self.ramp} s, or runs on day by "
                        "day where a date says so (the falling water after the dam)",
                "lines": self.lines, "statement": SELECT_STATEMENT}
