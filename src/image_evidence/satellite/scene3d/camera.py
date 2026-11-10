"""The 3D camera, frame by frame, in the zoom-out's plane (metres east and north of the plant; Z up, metres above sea).

A camera state is what the eye reads: the ground point looked at (`target`), the heading (degrees clockwise from
north), the pitch (-90 straight down, 0 level), the width of ground seen at the target and the lens. The distance
follows from width and lens (`dist`), so a long lens high up is the 2D film's top-down view, and dollying in while the
lens shortens keeps the ground's width (the plan's match cut).

The opening (chosen by the user, 25 October 2026: tilt while travelling from the plant, not slide then tilt) is one
move into the flight, with no correction at its end and no stop:
- The corridor's axis: the straight line through the flight path where the two lines run parallel (`axis`; within
  metres of the midline there). North of where they cross the midline jogs for a kilometre while they spread apart;
  the camera never follows that, it flies the axis.
- The camera's ground track is one path: a curve from over the zone's circle that meets the axis tangent to it where
  the camera lands, then the axis. Its speed eases up from rest to the flight's speed exactly as the tilt ends, and
  stays (the track is the camera's own, so its speed is what the viewer feels: no rush and brake at the landing).
- Heading, pitch, width and lens ease over the tilt (pitch over its later part, so the camera comes down before it
  tilts); the height follows from them. At the tilt's end the camera is on the axis at the flight's height, centred.

A variant may come onto the axis before the landing (`approach_m`; the user's call, 25 October 2026, after trying
the camera turning to follow the yellow line: the map must stay north up, never swivel): the camera zooms in and
tilts over the corridor's axis extended back from the crossing, so its last part is a straight run up the axis, and
its slide from the zone's centre happens while it is high and looking straight down (a pan of the map, north up).
The user chose `axis2k` (2 km).

After the landing the camera keeps to the axis along a `route` (the user's call, 25 October 2026: on to the end of
the crossing): keys by km north of the plant, each with the speed there and any change of view (height, pitch, lens,
a turn from the axis's heading). Between keys the camera's place along the axis is a quintic with those speeds at
its ends and no acceleration there (no jolt at a key); the view eases over the same stretch. A stretch's time follows
from its length and its end speeds (its mean speed is theirs), or is given (`s`: a turn on the spot, a hold).
The user's call (25 October 2026): level all the way (no tilting down to look, no hover), the drain happening while
the camera flies on at speed, and at the end a lift up and away, fading to white; never a turn round.

A variant with a `track` of its own (`frames_track`; the user's call, 4 November 2026) flies the other way: south
toward the plant, with the power, from a fade in from white over the north bank to a slow rise looking at the units.

Each frame also says how far the land has dissolved to the drained bed (`drain`, eased as the camera goes north from
`drain_km[0]` to `drain_km[1]`) and, over the last `fade_out_s`, how far it has faded to white (`fade`).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

SENSOR_MM = 36.0  # the camera's sensor width (Blender's default; horizontal fit)


@dataclass(frozen=True)
class State:
    target: tuple[float, float, float]
    heading: float   # degrees clockwise from north
    pitch: float     # degrees: -90 down, 0 level
    width: float     # metres of ground seen across the frame at the target
    lens: float      # mm

    @property
    def dist(self) -> float:
        return self.width * self.lens / SENSOR_MM

    @property
    def forward(self) -> np.ndarray:
        h, p = math.radians(self.heading), math.radians(self.pitch)
        return np.array([math.sin(h) * math.cos(p), math.cos(h) * math.cos(p), math.sin(p)])

    @property
    def position(self) -> np.ndarray:
        return np.asarray(self.target, float) - self.forward * self.dist

    def blender(self) -> dict[str, Any]:
        """Location, Euler XYZ rotation (radians; the camera looks down its -Z, its +Y up) and lens."""
        return {"location": [round(float(v), 3) for v in self.position],
                "rotation": [math.radians(90 + self.pitch), 0.0, math.radians(-self.heading)],
                "lens": round(self.lens, 4)}


def smootherstep(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return x * x * x * (x * (6 * x - 15) + 10)


def heading_of(v) -> float:
    return math.degrees(math.atan2(v[0], v[1]))


class Path:
    """A polyline in the plane, by distance along it."""

    def __init__(self, xy: np.ndarray):
        self.xy = np.asarray(xy, float)
        self.cum = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(self.xy, axis=0).T))])
        self.length = float(self.cum[-1])

    def at(self, s: float) -> np.ndarray:
        s = min(max(s, 0.0), self.length)
        return np.array([np.interp(s, self.cum, self.xy[:, 0]), np.interp(s, self.cum, self.xy[:, 1])])


def axis(points: np.ndarray, gaps: np.ndarray, keep: float = 0.9) -> tuple[np.ndarray, np.ndarray, float]:
    """The straight line through the flight path's points where the two lines run parallel (gap at least `keep` of the
    median): a point on it, its unit direction (northward) and the largest distance of those points from it."""
    q = points[gaps >= keep * np.nanmedian(gaps)]
    c = q.mean(0)
    d = np.linalg.svd(q - c)[2][0]
    d = d if d[1] >= 0 else -d
    off = np.abs((q - c) @ np.array([-d[1], d[0]]))
    return c, d, float(off.max())


def on_axis(c: np.ndarray, d: np.ndarray, north: float) -> np.ndarray:
    """The axis's point at a northing."""
    return c + d * (north - c[1]) / d[1]


def hermite(p0, p1, m0, m1, n: int = 400) -> np.ndarray:
    u = np.linspace(0, 1, n)[:, None]
    return ((2 * u ** 3 - 3 * u ** 2 + 1) * p0 + (u ** 3 - 2 * u ** 2 + u) * m0
            + (-2 * u ** 3 + 3 * u ** 2) * p1 + (u ** 3 - u ** 2) * m1)


def hermite5(p0, p1, m0, m1, n: int = 400) -> np.ndarray:
    """The quintic Hermite curve with no second derivative at either end: it leaves and meets a straight with no
    sudden turning."""
    u = np.linspace(0, 1, n)[:, None]
    return ((1 - 10 * u ** 3 + 15 * u ** 4 - 6 * u ** 5) * p0 + (u - 6 * u ** 3 + 8 * u ** 4 - 3 * u ** 5) * m0
            + (10 * u ** 3 - 15 * u ** 4 + 6 * u ** 5) * p1 + (-4 * u ** 3 + 7 * u ** 4 - 3 * u ** 5) * m1)


def route(keys: list[dict[str, Any]], s_land: float, land_north: float, d: np.ndarray, speed: float, alt: float,
          pitch: float, lens: float, fps: int, s_of=None) -> list[tuple]:
    """The frames after the landing, from the route's keys: (track distance, pitch, width, lens, turn from the axis's
    heading, phase) each. `s_of`: a key's distance along the track (from s_land) when keys aren't by km north of the
    plant on the axis (a track of its own: `frames_track`)."""
    cur = {"s": 0.0, "v": speed, "altitude_m": alt, "pitch_deg": pitch, "lens_mm": lens, "turn_deg": 0.0}
    out = []
    for k in keys:
        nxt = {**cur, **{q: float(k[q]) for q in ("altitude_m", "pitch_deg", "lens_mm", "turn_deg") if q in k}}
        at = s_of(k) if s_of else ((float(k["north_km"]) * 1000 - land_north) / d[1] if "north_km" in k else None)
        nxt["s"] = cur["s"] if at is None else at
        nxt["v"] = float(k.get("speed_mps", 0.0 if at is None else cur["v"]))
        run = nxt["s"] - cur["s"]
        if run < 0:
            raise ValueError(f"route: {k} goes back down the axis")
        if "s" in k:
            T = float(k["s"])
        elif cur["v"] + nxt["v"] > 0:
            T = 2 * run / (cur["v"] + nxt["v"])
        else:
            raise ValueError(f"route: {k} needs a time (`s`): it starts and ends at rest")
        n = max(1, round(T * fps))
        for i in range(n):
            u = i / n
            pos = (cur["s"] * (1 - 10 * u ** 3 + 15 * u ** 4 - 6 * u ** 5) + nxt["s"] * (10 * u ** 3 - 15 * u ** 4 + 6 * u ** 5)
                   + T * (cur["v"] * (u - 6 * u ** 3 + 8 * u ** 4 - 3 * u ** 5) + nxt["v"] * (-4 * u ** 3 + 7 * u ** 4 - 3 * u ** 5)))
            e = smootherstep(u)
            a, p_, f, h = (cur[q] + (nxt[q] - cur[q]) * e for q in ("altitude_m", "pitch_deg", "lens_mm", "turn_deg"))
            dist = a / math.sin(math.radians(-p_))
            out.append((s_land + pos, p_, dist * SENSOR_MM / f, f, h, k.get("phase", "flight")))
        cur = nxt
    return out


def frames(variant: str, o: dict[str, Any], start_xy, flight_xy: np.ndarray, gaps: np.ndarray,
           land_north: float, fps: int) -> list[dict[str, Any]]:
    """The camera for every frame: the hold on the zone's frame, the tilt into the corridor and the flight on along
    its axis. `land_north`: the northing where the camera lands on the axis as the tilt ends."""
    v = o["variants"][variant]
    o = {**o, **{k: v[k] for k in ("route", "drain_km", "fade_out_s", "flight_s") if k in v}}   # a variant's own
    fl = {**o["flight"], **(v.get("flight") or {})}
    z0 = float(o["ground_m"])
    pitch, alt, lens, speed = (float(fl[k]) for k in ("pitch_deg", "altitude_m", "lens_mm", "speed_mps"))
    c, d, _ = axis(flight_xy, gaps)
    h_end = heading_of(d)
    d_end = alt / math.sin(math.radians(-pitch))
    land = on_axis(c, d, land_north)                    # the camera, as the tilt ends
    t_end = land + d * d_end * math.cos(math.radians(pitch))   # the target then

    # the camera's ground track: from over the zone's centre, a curve meeting the axis tangent to it, then the axis
    p0 = np.asarray(start_xy, float)
    span = float(np.hypot(*(land - p0)))
    run = float(v.get("approach_m", 0))
    if run > 0:
        # onto the axis that far before the landing, turning in with no sudden turning at either end, then up it
        onto = land - d * run
        reach = float(np.hypot(*(onto - p0)))
        curve = np.vstack([hermite5(p0, onto, (onto - p0) * 0.5, d * reach)[:-1], onto, land])
    else:
        curve = hermite(p0, land, (land - p0) * 0.5, d * span)
    north = [float(k["north_km"]) * 1000 for k in o.get("route") or [] if "north_km" in k]
    far = on_axis(c, d, max([float(flight_xy[-1, 1]), *north]) + 1000)   # on past the last key (a lift's look ahead)
    track = Path(np.vstack([curve, far[None]]))
    s_land = Path(curve).length

    start = State((*p0, z0), 0.0, -90.0, float(o["start"]["view_km"]) * 1000, float(o["start"]["lens_mm"]))
    end = State((*t_end, z0), h_end, pitch, d_end * SENSOR_MM / lens, lens)
    tilt = float(v["tilt_s"])
    tilt_from = float(v.get("tilt_from", 0.25))
    V = speed * tilt  # the camera's speed at the tilt's end, per unit of the tilt's time
    if V > 2.5 * s_land:
        raise ValueError(f"{variant}: the flight's speed is too high to reach smoothly over {s_land:.0f} m in {tilt} s")

    def over(xy, heading, pitch_, width, lens_) -> State:
        """The state whose camera is above ground point xy: its target that far ahead along the heading."""
        st = State((0.0, 0.0, z0), heading, pitch_, width, lens_)
        lead = st.forward[:2] * st.dist
        return State((xy[0] + lead[0], xy[1] + lead[1], z0), heading, pitch_, width, lens_)

    n_hold, n_tilt, n_fly = (round(float(x) * fps) for x in (o["hold_s"], tilt, o["flight_s"]))
    rows = []
    for i in range(n_tilt + n_fly):
        if i < n_tilt:
            u = i / n_tilt
            # from rest to the flight's speed, its acceleration zero at both ends (no jolt as it lands)
            s = s_land * (10 * u ** 3 - 15 * u ** 4 + 6 * u ** 5) + V * (-4 * u ** 3 + 7 * u ** 4 - 3 * u ** 5)
            e = smootherstep(u)
            ep = smootherstep((u - tilt_from) / (1 - tilt_from))
            rows.append((s, e, start.pitch + (end.pitch - start.pitch) * ep,
                         math.exp(math.log(start.width) + (math.log(end.width) - math.log(start.width)) * e),
                         start.lens + (end.lens - start.lens) * e, "tilt"))
        else:
            rows.append((s_land + speed * (i - n_tilt) / fps, 1.0, end.pitch, end.width, end.lens, "flight"))
    heads = [start.heading + (end.heading - start.heading) * row[1] for row in rows]
    if o.get("route"):
        rows, heads = rows[:n_tilt], heads[:n_tilt]
        for s, p, w, f, h, phase in route(o["route"], s_land, land_north, d, speed, alt, pitch, lens, fps):
            rows.append((s, 1.0, p, w, f, phase))
            heads.append(end.heading + h)

    out = []
    for i in range(n_hold):
        out.append({"phase": "hold", **start.blender(), "dist": round(start.dist, 1)})
    for (s, _, p, w, f, phase), h in zip(rows, heads):
        st = over(track.at(s), h, p, w, f)
        out.append({"phase": phase, **st.blender(), "dist": round(st.dist, 1), "along_m": round(max(0.0, s - s_land), 1)})
    dr = o.get("drain_km")
    nf = round(float(o.get("fade_out_s", 0)) * fps)
    for i, f in enumerate(out):
        if dr:
            f["drain"] = round(smootherstep((f["location"][1] - dr[0] * 1000) / ((dr[1] - dr[0]) * 1000)), 4)
        if nf and i >= len(out) - nf:
            f["fade"] = round(smootherstep((i - (len(out) - nf) + 1) / nf), 4)
    return out


def frames_track(variant: str, o: dict[str, Any], flight_xy: np.ndarray, gaps: np.ndarray, fps: int) -> list[dict[str, Any]]:
    """The camera for a variant flying a `track` of its own (the user's call, 4 November 2026: toward the plant, with the
    power, instead of away from it): faded in from white high over the north bank, down onto the corridor's axis and
    south along it (the same axis as the flight north, flown the other way), off it on a curve with no sudden turning
    toward the plant, then a slow rise looking at the units from afar, fading to white. North stays where it is: the
    camera never turns round; its heading is the way it travels (no crabbing), eased along the curve.

    The track: the axis from `start_north_km` down to `leave_north_km`, a quintic curve to `end_xy_m` meeting it at
    `end_heading_deg`, then straight on. The route's keys are by km north on the axis (`north_km`), by the share of the
    curve (`curve`) or by metres past its end (`beyond_m`)."""
    v = o["variants"][variant]
    t = v["track"]
    st = {**o["flight"], **(v.get("flight") or {}), **(t.get("start") or {})}
    z0 = float(o["ground_m"])
    c, d, _ = axis(flight_xy, gaps)
    p0 = on_axis(c, d, float(t["start_north_km"]) * 1000)
    if t.get("end_xy_m") is None:
        # straight down the axis to the end (look pass 3, the user, 7 November 2026: ending over the south bank, the
        # curve toward the units kept for a separate shot): no curve, the keys by km north only
        straight, s_curve = math.inf, 0.0
        track = Path(np.vstack([p0, p0 - d * 40000.0]))
    else:
        a = on_axis(c, d, float(t["leave_north_km"]) * 1000)
        e = np.asarray(t["end_xy_m"], float)
        h = math.radians(float(t["end_heading_deg"]))
        u = np.array([math.sin(h), math.cos(h)])
        span = float(np.hypot(*(e - a)))
        curve = hermite5(a, e, -d * span, u * span)
        straight = float(np.hypot(*(a - p0)))
        track = Path(np.vstack([p0, curve, e + u * 3000]))
        s_curve = Path(np.vstack([a, curve[1:]])).length

    def s_of(k):
        if "north_km" in k:
            return (float(t["start_north_km"]) - float(k["north_km"])) * 1000 / d[1]
        if math.isinf(straight) and ("curve" in k or "beyond_m" in k):
            raise ValueError(f"{variant}: a straight track has no curve: key {k} by `north_km` only")
        if "curve" in k:
            return straight + float(k["curve"]) * s_curve
        if "beyond_m" in k:
            return straight + s_curve + float(k["beyond_m"])
        return None

    def heading(s: float) -> float:
        return heading_of(track.at(s + 8.0) - track.at(s - 8.0))

    rows = route(v["route"], 0.0, 0.0, d, float(st["speed_mps"]), float(st["altitude_m"]), float(st["pitch_deg"]),
                 float(st["lens_mm"]), fps, s_of=s_of)
    rise = t.get("rise")
    if rise:   # one smooth climb (and pitch) between two places, over the route's keys (whose eases would pause it)
        s0, s1 = s_of(rise["from"]), s_of(rise["to"])
        (a0, a1), (p0_, p1_) = rise["altitude_m"], rise["pitch_deg"]
        eased = []
        for s, p, w, f, turn, phase in rows:
            if s >= s0:
                e = smootherstep((s - s0) / (s1 - s0))
                a, p = a0 + (a1 - a0) * e, p0_ + (p1_ - p0_) * e
                w = a / math.sin(math.radians(-p)) * SENSOR_MM / f
                phase = "rise"
            eased.append((s, p, w, f, turn, phase))
        rows = eased
    out = []
    for s, p, w, f, turn, phase in rows:
        sv = State((0.0, 0.0, z0), heading(s) + turn, p, w, f)
        lead = sv.forward[:2] * sv.dist
        xy = track.at(s)
        sv = State((xy[0] + lead[0], xy[1] + lead[1], z0), sv.heading, p, w, f)
        out.append({"phase": phase, **sv.blender(), "dist": round(sv.dist, 1), "along_m": round(s, 1)})
    n_in, n_out = (round(float(v.get(k, o.get(k, 0))) * fps) for k in ("fade_in_s", "fade_out_s"))
    for i, f in enumerate(out):
        if n_in and i < n_in:
            f["fade"] = round(1 - smootherstep((i + 1) / n_in), 4)
        if n_out and i >= len(out) - n_out:
            f["fade"] = round(smootherstep((i - (len(out) - n_out) + 1) / n_out), 4)
    return out
