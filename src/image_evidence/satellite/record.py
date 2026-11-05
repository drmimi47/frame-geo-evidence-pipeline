"""The lines' record (decided with the user, 22 October 2026): when each of the plant's lines was cut off and
reconnected, 2022 on, played on the zoom-out against a running date.

Every change is a dated report with its sources (the config's `record`: the IAEA's updates, mostly through the World
Nuclear Association's and the OECD-NEA's chronologies that quote them, Energoatom, news reports). A line is in one of
three states: `on` (connected to the plant), `off` (cut off) or `unknown` (lines were cut and repaired, but the report
doesn't say which). An event either sets a line's state from its date on, or holds a state only for a while (`until`
a date, or `brief`: restored within the day, or no time given) and then the line goes back to what it was. A complete
loss of off-site power (`loop`, the IAEA's count) cuts every line for its span. Island mode (`island`, with `until`:
every line cut, a reactor running at low power for the plant's own needs, as on 5-10 September 2022) cuts the lines it
names for its span too, but it isn't a complete loss in the IAEA's count and no diesel generator runs: kept apart
(`islands`) so the films can say so.

Time (decided with the user, 22 October 2026: each state given room to breathe): the date runs from `start` to `end`
over `run_s` and steps from one reported change to the next (`shown`: days with nothing reported are skipped). Every
interval between reported changes is held at least `min_hold_s` (`caption_hold_s` where a caption is to be read); a cut
restored within the day is shown `min_blink_s` at the start of its interval, a complete loss `loss_s` (a longer pause
with every line off, decided with the user), one lasting days at least `loss_hold_s` plus `loss_day_s` a day (up to
`loss_max_s`), and the day the IAEA proposed its
protection zone the zone's `hold_s` (a held moment), and each of `holds` (`{at, s}`: a day the date holds on, e.g. the
zoom-out's night lights) its `s`; the rest of `run_s` is shared by how long each interval was (the log
of its days). `steps` are days the date
stops on with no line changing (the water's reported levels, say). `pins` fix a reported day to a film time (`{at, s}`; the record's runs either side of it are shared
separately), each optionally with its own `min_hold_s` for the intervals from it to the next pin (a stretch whose
date steps day by day). A line cuts off quickly and comes back with a slower swell (`mix`). film.json records each
event's real dates and its time in the film.
"""

from __future__ import annotations

import math
from datetime import date
from typing import Any

import numpy as np

STATES = ("on", "off", "unknown")


def _state(v: Any) -> str:
    """YAML reads on and off as booleans."""
    return {True: "on", False: "off"}.get(v, v) if isinstance(v, bool) else str(v)


def _day(v: Any) -> int:
    return (v if isinstance(v, date) else date.fromisoformat(str(v))).toordinal()


def _eased(spans: list[tuple[float, float]], t: float, ease: float) -> float:
    w = 0.0
    for a, b in spans:
        x, y = min(1.0, max(0.0, (t - a) / ease)), min(1.0, max(0.0, (b - t) / ease))
        w = max(w, min(x * x * (3 - 2 * x), y * y * (3 - 2 * y)))
    return w


class Record:
    def __init__(self, cfg: dict[str, Any], at_s: float):
        self.cfg = cfg
        self.lines: dict[str, list] = cfg["lines"]  # record name -> [drawn line's name, kV, (strand)]
        self.groups: dict[str, list[str]] = {"all": list(self.lines), **(cfg.get("groups") or {})}
        self.d0, self.d1 = _day(cfg["start"]), _day(cfg["end"])
        self.at = at_s  # the record starts (the date box fades in)
        self.t0 = at_s + float(cfg.get("intro_s", 3.0))  # the date starts to run
        self.t1 = self.t0 + float(cfg["run_s"])  # and stops on `end`
        self.end = self.t1 + float(cfg.get("outro_s", 6.0))
        self.blink = float(cfg.get("min_blink_s", 0.8))
        self.loss_s = float(cfg.get("loss_s", self.blink))  # a complete loss restored within the day, on screen
        self.events = sorted(cfg["events"], key=lambda e: _day(e["at"]))  # stable: same-day events keep their order
        for e in self.events:
            for k in self._keys(e.get("lines", [])):
                if k not in self.lines:
                    raise ValueError(f"record event {e['at']}: no line {k!r}")
        changes = {self.d0, self.d1}  # the days something is reported (the end: the last report): the date steps between them
        for e in self.events:
            changes.add(_day(e["at"]))
            if e.get("until") is not None:
                changes.add(_day(e["until"]))
        for k in ("from", "until"):  # the protection zone's dates
            if (cfg.get("zone") or {}).get(k):
                changes.add(_day(cfg["zone"][k]))
        pins = sorted(cfg.get("pins") or [], key=lambda p: _day(p["at"]))
        held = {}  # a day held at least this long (a held moment of the film's own: the zoom-out's night lights)
        for h in cfg.get("holds") or []:
            held[_day(h["at"])] = max(held.get(_day(h["at"]), 0.0), float(h["s"]))
        changes |= {_day(p["at"]) for p in pins} | {_day(d) for d in cfg.get("steps") or []} | set(held)  # days shown without a change
        self.changes = sorted(d for d in changes if self.d0 <= d <= self.d1)
        # the pace: each interval between reported changes at least `min_hold_s` (plus the blink of a cut restored
        # within the day, or the pause of a complete loss, at its start), the rest of the run shared by the log of its days
        hold = float(cfg.get("min_hold_s", 0.8))
        holds = np.full(len(self.changes) - 1, hold)  # each interval's own least hold: a pin's from it to the next pin
        for p in pins:
            if p.get("min_hold_s") is not None:
                nxt = min([_day(q["at"]) for q in pins if _day(q["at"]) > _day(p["at"])] + [self.d1])
                for i, d in enumerate(self.changes[:-1]):
                    if _day(p["at"]) <= d < nxt:
                        holds[i] = float(p["min_hold_s"])
        blink = {}  # day -> what is shown at its start before the state it settles in
        for e in self.events:
            if self._within_day(e):
                d = _day(e["at"])
                blink[d] = max(blink.get(d, 0.0), self.loss_s if e.get("loop") else self.blink)
        long_loss = {}  # a complete loss lasting days: `loss_hold_s`, and `loss_day_s` a day up to `loss_max_s`
        for e in self.events:
            if e.get("loop") and not self._within_day(e):
                days = _day(e["until"]) - _day(e["at"])
                long_loss[_day(e["at"])] = min(float(cfg.get("loss_hold_s", 0.0)) + float(cfg.get("loss_day_s", 0.0)) * days,
                                               float(cfg.get("loss_max_s", math.inf)))
        ch = np.array(self.changes, float)
        captioned = {_day(e["at"]) for e in self.events if e.get("caption")}
        zone = cfg.get("zone") or {}
        self.zone_day = _day(zone["from"]) if zone.get("from") else None
        floor = np.array([max(h + blink.get(d, 0.0),
                              float(cfg.get("caption_hold_s", 0.0)) if d in captioned else 0.0,
                              long_loss.get(d, 0.0),
                              float(zone.get("hold_s", 0.0)) if d == self.zone_day else 0.0,
                              held.get(d, 0.0))
                          for d, h in zip(self.changes[:-1], holds)])
        w = np.log1p(np.diff(ch))
        # the run in stretches between the pins, each filled on its own
        edges = [(0, self.t0)] + [(self.changes.index(_day(p["at"])), float(p["s"])) for p in pins] \
            + [(len(self.changes) - 1, self.t1)]
        dur = np.zeros(len(floor))
        for (a, ta), (b, tb) in zip(edges, edges[1:]):
            dur[a:b] = self._fill(floor[a:b], w[a:b], tb - ta, str(date.fromordinal(self.changes[a])))
        self._days, self._ts = ch - self.d0, self.t0 + np.concatenate([[0.0], np.cumsum(dur)])
        # each line's states in film time: what it is from a moment on (base), and spans that override it
        self.base = {key: [(-math.inf, "on")] for key in self.lines}
        self.over: dict[str, list[tuple[float, float, str]]] = {key: [] for key in self.lines}
        self.loops: list[tuple[float, int]] = []
        self.losses: list[tuple[float, float]] = []  # complete losses on screen (diesel generators running)
        self.islands: list[tuple[float, float]] = []  # island mode on screen (no line, a reactor powering the plant)
        self.captions: list[tuple[float, str, int]] = []
        self.placed = []
        for e in self.events:
            d = _day(e["at"])
            ta = self.t(d)
            span = None
            if e.get("island") and (e.get("until") is None or e.get("loop")):
                raise ValueError(f"record event {e['at']}: island mode needs `until` and is not a complete loss")
            if e.get("until") is not None or e.get("brief") or e.get("loop"):
                # restored the same day, or no time given: within the day, shown `min_blink_s` (a loss: `loss_s`)
                brief = self.loss_s if e.get("loop") else self.blink
                span = (ta, ta + brief) if self._within_day(e) else (ta, self.t(_day(e["until"])))
                if e.get("from_start"):  # begun before this record's start (states.py): held from the first frame
                    span = (-math.inf, span[1])
            keys = list(self.lines) if e.get("loop") else self._keys(e.get("lines", []))
            state = "off" if e.get("loop") else _state(e.get("to", "off"))
            for key in keys:
                if span:
                    self.over[key].append((span[0], span[1], state))
                elif "to" in e:
                    self.base[key].append((ta, state))
            if e.get("loop"):
                self.loops.append((ta, int(e["loop"])))
                self.losses.append(span)
            if e.get("island"):
                self.islands.append(span)
            if e.get("caption"):  # each on screen at least `caption_min_s` before the next takes its place
                shown = max(ta, self.captions[-1][0] + float(cfg.get("caption_min_s", 2.5)) if self.captions else ta)
                self.captions.append((shown, str(e["caption"]), d))
            self.placed.append({"at": str(e["at"]), "until": str(e["until"]) if e.get("until") is not None else None,
                                "brief": bool(e.get("brief")), "lines": keys, "state": state, "loop": e.get("loop"),
                                "island": bool(e.get("island")),
                                **({"began": str(e["began"])} if e.get("began") else {}),
                                "loop_count": e.get("count", "source" if e.get("loop") else None),
                                "film_s": [round(max(span[0], 0.0), 2), round(span[1], 2)] if span else round(ta, 2),
                                "caption": e.get("caption"), "note": e.get("note"),
                                "sources": [self.cfg["sources"][s] for s in e.get("src", [])]})
            for s in e.get("src", []):
                if s not in self.cfg["sources"]:
                    raise ValueError(f"record event {e['at']}: no source {s!r}")
        # each line's changes in film time (for the crossfades)
        self.edges = {key: sorted({tb for tb, _ in self.base[key][1:]} | {v for a, b, _ in self.over[key] for v in (a, b)})
                      for key in self.lines}
        self.fade_on, self.fade_off = float(cfg.get("fade_on_s", 0.6)), float(cfg.get("fade_off_s", 0.25))

    @staticmethod
    def _fill(floor: np.ndarray, w: np.ndarray, run: float, at: str) -> np.ndarray:
        """Each interval's time: at least its floor, the rest of `run` shared by the log of its days."""
        if len(floor) == 0:
            return floor
        if floor.sum() > run + 1e-6:
            raise ValueError(f"the record from {at} needs at least {floor.sum():.1f} s for its {len(floor)} intervals; "
                             f"it has {run:.1f}")
        lo, hi = 0.0, run / max(w.sum(), 1e-9) * 2 + 1
        for _ in range(60):  # the share per log-day that fills the run exactly
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if np.maximum(floor, mid * w).sum() < run else (lo, mid)
        dur = np.maximum(floor, hi * w)
        return dur * run / dur.sum()

    @staticmethod
    def _within_day(e: dict[str, Any]) -> bool:
        """A cut restored within the day it began (or with no end given)."""
        if not (e.get("until") is not None or e.get("brief") or e.get("loop")):
            return False
        return e.get("until") is None or _day(e["until"]) <= _day(e["at"])

    def _keys(self, names) -> list[str]:
        names = [names] if isinstance(names, str) else names
        return [k for n in names for k in self.groups.get(n, [n])]

    def t(self, day: float) -> float:
        """Film time of a day (ordinal)."""
        return float(np.interp(day - self.d0, self._days, self._ts))

    def day(self, t: float) -> date | None:
        """The date on screen at film time t (None before the record starts)."""
        if t < self.at:
            return None
        return date.fromordinal(int(self.d0 + float(np.interp(t, self._ts, self._days))))

    def days(self, t: float) -> float:
        """The record's day at film time t as a fraction (ordinal), for what changes smoothly with the date."""
        return self.d0 + float(np.interp(t, self._ts, self._days))

    def shown(self, t: float) -> date | None:
        """The date on screen: the last reported change at or before t (None before the record starts)."""
        d = self.day(t)
        if d is None:
            return None
        k = int(np.searchsorted(self.changes, d.toordinal(), side="right")) - 1
        return date.fromordinal(self.changes[max(k, 0)])

    def state(self, key: str, t: float) -> str:
        for a, b, s in self.over[key]:
            if a <= t < b:
                return s
        return [s for tb, s in self.base[key] if tb <= t][-1]

    def mix(self, key: str, t: float) -> dict[str, float]:
        """The line's states at t as weights: a cut dims in `fade_off_s` (a breaker), a reconnection swells back over
        `fade_on_s`."""
        cur = self.state(key, t)
        k = int(np.searchsorted(self.edges[key], t, side="right")) - 1
        if k < 0:
            return {cur: 1.0}
        tb = self.edges[key][k]
        prev = self.state(key, tb - 1e-6)
        if prev == cur:
            return {cur: 1.0}
        x = min(1.0, max(0.0, (t - tb) / (self.fade_on if cur == "on" else self.fade_off)))
        w = x * x * (3 - 2 * x)
        return {cur: 1.0} if w >= 1 else {prev: 1 - w, cur: w}

    def states(self, key: str, ts: np.ndarray) -> np.ndarray:
        """`state` at many times at once."""
        tb = np.array([b[0] for b in self.base[key]])
        out = np.array([b[1] for b in self.base[key]], dtype=object)[np.searchsorted(tb, ts, side="right") - 1]
        for a, b, s in reversed(self.over[key]):  # the first span listed wins, as in `state`
            out[(ts >= a) & (ts < b)] = s
        return out

    def on_diesel(self, t: float) -> bool:
        """During a complete loss of off-site power (the plant's diesel generators run)."""
        return any(a <= t < b for a, b in self.losses)

    def loss_weight(self, t: float, ease: float = 0.4) -> float:
        """1 during a complete loss, eased in and out over `ease` s."""
        return _eased(self.losses, t, ease)

    def in_island(self, t: float) -> bool:
        """In island mode: no line connected, a reactor powering the plant's own needs (not on diesel)."""
        return any(a <= t < b for a, b in self.islands)

    def island_weight(self, t: float, ease: float = 0.4) -> float:
        """1 in island mode, eased in and out over `ease` s."""
        return _eased(self.islands, t, ease)

    def loss_count(self, t: float) -> tuple[int, float]:
        """The IAEA's count of complete losses of off-site power at t, and when it last went up."""
        past = [(ta, c) for ta, c in self.loops if ta <= t]
        return (past[-1][1], past[-1][0]) if past else (0, -math.inf)

    def caption(self, t: float, hold: float = 4.0) -> tuple[str, int, float] | None:
        """The caption at t (text, its day, opacity): each holds `hold` s or while the date stays on its day, whichever
        is longer, until the next one."""
        past = [c for c in self.captions if c[0] <= t]
        if not past:
            return None
        ta, text, d = past[-1]
        nxt = next((c[0] for c in self.captions if c[0] > ta), math.inf)
        k = int(np.searchsorted(self.changes, d, side="right"))
        step = float(self._ts[k]) if k < len(self.changes) else math.inf  # when the date moves on from its day
        until = min(max(ta + hold, step), nxt) if t < self.t1 else math.inf  # the last one stays to the end
        op = min(1.0, (t - ta) / 0.3) * max(0.0, min(1.0, (until - t) / 0.35))
        return (text, d, op) if op > 0 else None

    def doc(self) -> dict[str, Any]:
        return {"start": str(self.cfg["start"]), "end": str(self.cfg["end"]),
                "film_s": {"starts": round(self.at, 2), "date_runs": [round(self.t0, 2), round(self.t1, 2)],
                           "ends": round(self.end, 2)},
                "states": {"on": "connected to the plant (yellow)", "off": "cut off (red)",
                           "unknown": "lines were cut and repaired, but the reports don't say which (grey)"},
                "time": f"the date shown steps from one reported change to the next (days with nothing reported "
                        f"skipped); each interval between them held at least {self.cfg.get('min_hold_s', 0.8)} s, a cut "
                        f"restored within the day shown {self.blink} s, a complete loss {self.loss_s} s (one lasting days "
                        f"at least {self.cfg.get('loss_hold_s', 0)} s plus {self.cfg.get('loss_day_s', 0)} s a day, up to "
                        f"{self.cfg.get('loss_max_s')} s), the zone's day {(self.cfg.get('zone') or {}).get('hold_s', 0)} s, "
                        "the rest shared by the log of each interval's days; a cut dims in "
                        f"{self.fade_off} s, a reconnection swells back over {self.fade_on} s",
                "island_mode": "every line cut while a reactor runs at low power for the plant's own needs: no "
                               "off-site power, but not on diesel and not a complete loss in the IAEA's count (the "
                               "count stays); labelled on screen",
                "lines": self.lines, "groups": self.groups, "events": self.placed, "note": self.cfg.get("note")}
