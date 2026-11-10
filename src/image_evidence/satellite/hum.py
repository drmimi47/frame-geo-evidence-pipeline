"""The Hum on the zoom-out (decided with the user, 22 October 2026): the lines' record (`record.py`) heard.

Synthesized, not recorded (these lines can't be recorded): each of the plant's lines is a voice on the hum of a 50 Hz
grid, 100 Hz and its harmonics (transformers and lines hum at twice the grid's frequency), with corona crackle, which
follows the line's voltage and the weather, never what it carries (the user, 9 November 2026; reports/Enerhodar crossing
voices and sound.md): every connected line crackles at full strength, a 750 kV line louder, denser and brighter than a
330 kV one (`CORONA`, shaped on two recordings of lines of those classes: research_notes/Line sound proxies/kv/), and the
crackle swells on the dates ERA5 has wet hours at the crossing (rain, or fog inferred from humidity and wind: `wet_days`;
a drawing convention from modelled weather, said so). Each line stresses one harmonic of its own (a design choice, so a cut takes a partial out of
the chord: 750 kV lower, 330 kV higher) and is panned by the bearing of its end from the plant. A line sounds while the
record says it is connected, stops at once when cut, and swells back slowly when reconnected (a transformer's inrush);
where the reports don't say which lines were cut it is heard muffled, as through a wall: the record is silent, not
the line. During a complete loss of off-site power every voice stops (no diesel generators: removed at the user's
request, 22 October 2026). In island mode (every line cut, a reactor at low power for the plant's own needs, not a
complete loss: 5-10 September 2022) the lines are silent and one low note holds in the middle, the hum's lowest
partials alone: the plant powering itself (a design choice, said in `doc`). The level follows how many lines are connected, compressed so one line alone stays
audible. It fades in once the camera has stopped pulling back, all ten lines connected (before the war), well
before the record's date runs. No sounds of fighting.
"""

from __future__ import annotations

import hashlib
import json
import math
import wave
from pathlib import Path
from datetime import date
from typing import Any

import numpy as np

from .record import Record

SR = 48_000
CTRL = 1000  # Hz: envelopes and slow wobble, interpolated to the audio rate
HARMONICS = 12  # of 100 Hz
ISLAND_PARTIALS = ((1, 1.0), (2, 0.35))  # island mode's note: the hum's lowest partials (harmonic, amplitude)
ISLAND_LEVEL = 0.22  # its level against a line's voice (about one line alone, a little lower)
# the hum's shape by voltage (amplitude of 100 Hz and its harmonics, before a line's own partial is stressed): the 750 kV
# recording's tone sits at 100 and 200 Hz with a weaker 300 Hz and little above; the 330 kV's 200 Hz is stronger than
# its 100 Hz, with 300-600 Hz clearly there (kv/compare_kv.json: dB over their neighbours; the shapes a design choice)
HUM_SHAPE = {750: (1.0, 0.9, 0.35, 0.12, 0.06, 0.04, 0.03, 0.02, 0.02, 0.015, 0.012, 0.01),
             330: (0.6, 1.0, 0.5, 0.45, 0.32, 0.38, 0.22, 0.16, 0.12, 0.09, 0.07, 0.05)}
# corona by voltage. Levels are against the 750 kV line's hum (its RMS): dry, every connected 750 kV line's crackle a
# little under its hum, so it is heard; wet, 7 dB up (Hydro-Quebec's 735 kV line: +11 dBA in rain at the edge of its
# right of way, compressed for the mix), which brings it up to the hum, as the 750 kV recording in fog has its 1.5-8 kHz
# band 6.4 dB over its 80-420 Hz. The 330 kV 11 dB quieter dry and 5 dB up wet (below the voltage utilities treat corona
# as a concern; its measurements in rain scattered, no clear trend: TransGrid/WSP 2025): design choices, said in `doc`. The
# 750 kV recording's crackle is impulsive (kurtosis 11-19 in 2-8 kHz), reaches 16 kHz and pulses once a cycle (50 Hz:
# the positive half's corona); the 330 kV's is a smoother hiss (kurtosis about 4), rolling off above 8 kHz, pulsing
# twice a cycle (100 Hz). Wet, a line has many more points in corona: cracks come much more often.
CORONA = {750: {"dry_db": -3.0, "wet_db": 7.0, "cracks_per_s": (14.0, 90.0), "crack_sigma": 0.9, "crack_share": 0.7,
                "band": (900, 16000), "hiss_band": (2000, 14000), "pulse_hz": 50},
          330: {"dry_db": -14.0, "wet_db": 5.0, "cracks_per_s": (3.0, 18.0), "crack_sigma": 0.5, "crack_share": 0.25,
                "band": (900, 8000), "hiss_band": (1200, 8000), "pulse_hz": 100}}
WET_RULE = ("a wet hour: precipitation 0.1 mm or more, or (inferred) fog likely: relative humidity at 2 m 97% or more "
            "with wind at 10 m under 3 m/s")
REF_DB = -11.5  # the dry full chord's level, K-weighted: the films about as loud as before the crackle came up, the
                # wet swells on top (9 November 2026)
WET_FULL_H = 6.0  # wet hours on the date shown for the full swell (fewer: in proportion; a design choice)
WET_RISE_S, WET_FALL_S = 0.5, 1.5  # the swell eased in and out in film time, falling three times slower (in the rain
                                   # measured: up over about 15 min, down over about 40; compressed to the film's pace)
STATEMENT = ("Synthesized, not recorded. Each of the plant's lines is a voice on the 100 Hz hum of a 50 Hz grid and its "
             "harmonics, with corona crackle; each stresses one harmonic of its own (a design choice: a cut takes a "
             "partial out of the chord) and is panned by the bearing of its end from the plant. It sounds while the "
             "record says the line is connected, stops when cut and swells back when reconnected; muffled where the "
             "reports don't say which lines were cut; silent during a complete loss of off-site power; in island mode (every "
             "line cut, a reactor powering the plant itself) only a low note in the middle. The level follows "
             "how many lines are connected (compressed). It fades in once the camera has stopped pulling back, every "
             "line connected. The crackle follows the line's voltage and the weather, never what it carries: every "
             "connected line at full strength, a 750 kV line louder, denser and brighter than a 330 kV one, swelling "
             "on the dates the ERA5 reanalysis has wet hours at the crossing (rain, or fog inferred from humidity and "
             "wind; a drawing convention from modelled weather, not a measurement at the line). A line's silence "
             "means not connected by the record, not that the wire itself was silent. No sounds of fighting.")


def wet_days(path: Path | str) -> dict[int, int]:
    """Wet hours a day (date ordinal: hours, of 24) from an ERA5 hourly series as Open-Meteo's archive returns it
    (precipitation, relative_humidity_2m, wind_speed_10m; its local days), by `WET_RULE`."""
    h = json.loads(Path(path).read_text())["hourly"]
    out: dict[int, int] = {}
    for t, p, rh, ws in zip(h["time"], h["precipitation"], h["relative_humidity_2m"], h["wind_speed_10m"]):
        d = date.fromisoformat(t[:10]).toordinal()
        out[d] = out.get(d, 0) + int((p or 0) >= 0.1 or ((rh or 0) >= 97 and (ws if ws is not None else 99) < 3))
    return out


def weather(cfg: dict[str, Any] | None, base: Path) -> tuple[dict[int, int] | None, dict[str, Any] | None]:
    """A network's `weather` (its ERA5 file, relative to `base`): the wet hours a day and what to say of them."""
    if not cfg:
        return None, None
    f = base / cfg["era5"]
    return wet_days(f), {"source": cfg.get("source", "ERA5 reanalysis (Open-Meteo archive)"), "file": cfg["era5"],
                         "cell": cfg.get("cell"), "rule": WET_RULE}


def _ss(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def _band(f: np.ndarray, lo: float | None, hi: float | None, edge: float = 0.4) -> np.ndarray:
    """A smooth band-pass gain over frequencies f (raised edges `edge` octaves wide)."""
    lf = np.log2(np.maximum(f, 1.0))
    g = np.ones_like(f)
    if lo:
        g *= _ss((lf - math.log2(lo) + edge) / (2 * edge))
    if hi:
        g *= 1 - _ss((lf - math.log2(hi) + edge) / (2 * edge))
    return g


def _filtered(x: np.ndarray, lo: float | None, hi: float | None, rate: float = SR) -> np.ndarray:
    f = np.fft.rfftfreq(len(x), 1 / rate)
    return np.fft.irfft(np.fft.rfft(x) * _band(f, lo, hi), len(x)).astype(np.float32)


def _noise(rng: np.random.Generator, n: int, lo: float | None, hi: float | None, rate: float = SR) -> np.ndarray:
    """Band-limited noise at unit RMS."""
    x = _filtered(rng.standard_normal(n).astype(np.float32), lo, hi, rate)
    return x / max(float(x.std()), 1e-9)


def _follow(x: np.ndarray, up_s: float, down_s: float) -> np.ndarray:
    """A one-pole follower at the control rate: rises with `up_s`, falls with `down_s`."""
    au, ad = 1 - math.exp(-1 / (up_s * CTRL)), 1 - math.exp(-1 / (down_s * CTRL))
    y = np.empty_like(x)
    v = float(x[0])
    for i, xi in enumerate(x.tolist()):
        v += (xi - v) * (au if xi > v else ad)
        y[i] = v
    return y


def _conv(x: np.ndarray, k: np.ndarray) -> np.ndarray:
    n = len(x) + len(k) - 1
    m = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(k, m), m)[:len(x)].astype(np.float32)


def score(rec: Record, pans: dict[str, float], kvs: dict[str, int], total_s: float, fade_out_s: float,
          start_s: float | None = None, fade_in_s: float = 4.0, seed: int = 50,
          follow: tuple[float, float] = (0.25, 0.012), ref_s: tuple[float, float] | None = None,
          island_level: float | None = None, wet: dict[int, int] | None = None,
          weather_doc: dict[str, Any] | None = None) -> tuple[np.ndarray, dict[str, Any]]:
    """The film's sound, stereo float32 (n, 2) at `SR`, and what was made, for film.json. It fades in from `start_s`
    (default: the record's start) over `fade_in_s`. `follow`: how fast a line swells back and falls silent (s; the
    zoom-out's: a breaker); `ref_s`: when every line sounds, for the level (default: from the fade-in to the record);
    `island_level`: island mode's note against a line's voice (default ISLAND_LEVEL); `wet`: wet hours a day
    (`wet_days`), so the crackle swells by the weather on the date shown (none: dry throughout); `weather_doc`: what
    to say of it."""
    start_s = rec.at if start_s is None else float(start_s)
    rng = np.random.default_rng(seed)
    n = int(round(total_s * SR))
    nc = int(math.ceil(total_s * CTRL)) + 2
    tc = np.arange(nc) / CTRL
    ta = np.arange(n) / SR
    keys = list(rec.lines)
    k750 = [k for k in keys if kvs[k] >= 750]
    k330 = [k for k in keys if kvs[k] < 750]
    voice = {k: 2 + j for j, k in enumerate(k750)} | {k: 6 + j for j, k in enumerate(k330)}
    hs = np.arange(1, HARMONICS + 1)
    on, unk, inrush = {}, {}, {}
    for k in keys:
        st = rec.states(k, tc)
        raw_on = (st == "on").astype(np.float64)
        raw_unk = (st == "unknown").astype(np.float64)
        on[k] = _follow(raw_on, *follow)  # cut at once (a breaker), back with a slow swell (as the picture)
        unk[k] = _follow(raw_unk, 0.3, 0.03)  # (cut fast too, so a complete loss falls silent at once)
        rise = np.maximum(np.diff(raw_on, prepend=raw_on[0]), 0)
        inrush[k] = _follow(np.convolve(rise, np.ones(40), "same").clip(0, 1), 0.02, 0.7)  # a reconnection's growl
    # the master: the level follows how many lines sound, compressed (out ~ count^0.65)
    count = sum((1.0 if kvs[k] >= 750 else 0.7) * (on[k] + 0.4 * unk[k]) for k in keys)
    gain = np.maximum(count, 0.3) ** -0.35
    # the grid's frequency wanders a little (all lines on one grid: one hum, many partials)
    f0 = 100 * (1 + 0.00015 * np.interp(ta, tc, _noise(rng, nc, None, 0.08, CTRL)))
    phase = 2 * np.pi * np.cumsum(f0) / SR
    L, R = np.zeros(n, np.float32), np.zeros(n, np.float32)
    voices = []
    for h in hs:
        al, ar = np.zeros(nc), np.zeros(nc)
        for k in keys:
            shape = np.array(HUM_SHAPE[750 if kvs[k] >= 750 else 330])
            a = 0.45 * shape / np.sqrt((shape ** 2).sum()) + np.exp(-((hs - voice[k]) / 0.6) ** 2) * 0.5  # its own partial, stressed
            a = a / np.sqrt((a ** 2).sum()) * (1.0 if kvs[k] >= 750 else 0.7)
            wob = 1 + 0.12 * _noise(rng, nc, None, 0.9, CTRL)
            muffled = 0.45 if h <= 2 else 0.12 if h == 3 else 0.0
            amp = a[h - 1] * wob * (on[k] * (1 + (0.9 if h <= 3 else 0.2) * inrush[k]) + unk[k] * muffled) * gain
            p = pans[k]
            al += amp * math.cos((p + 1) * math.pi / 4)
            ar += amp * math.sin((p + 1) * math.pi / 4)
        s = np.sin(h * phase + rng.uniform(0, 2 * np.pi)).astype(np.float32)
        L += np.interp(ta, tc, al).astype(np.float32) * s
        R += np.interp(ta, tc, ar).astype(np.float32) * s
    # corona: cracks and a hiss at the voltage's peaks (the 750 kV's once a cycle, the 330 kV's twice), while the line is
    # connected, at full strength whatever it carries; on wet dates more cracks and louder (`CORONA`, `WET_*`)
    wetc = _wetness(rec, wet, tc)
    hum_rms = 1.0 / math.sqrt(2)   # a 750 kV line's hum (its partials' amplitudes normed to 1)
    extra_l, extra_r = np.zeros(n, np.float32), np.zeros(n, np.float32)   # the wet swell, kept apart for the level
    tk = np.arange(int(0.006 * SR)) / SR
    wet_a = np.interp(ta, tc, wetc).astype(np.float32)
    for k in keys:
        cv = CORONA[750 if kvs[k] >= 750 else 330]
        ph = phase / 2 if cv["pulse_hz"] == 50 else phase   # 50 Hz: one peak a cycle; 100 Hz: both halves
        pk = (0.5 + 0.5 * np.sin(ph + rng.uniform(0, 2 * np.pi))) if cv["pulse_hz"] == 50 else np.abs(np.sin(ph / 2))
        pulse = (0.3 + 0.7 * pk ** 6).astype(np.float32)
        hiss = _noise(rng, n, *cv["hiss_band"]) * pulse
        hiss /= max(float(hiss.std()), 1e-9)
        click = (rng.standard_normal(len(tk)) * np.exp(-tk / 0.0012)).astype(np.float32)

        def crackle(rate):
            c = np.zeros(n, np.float32)
            at = rng.random(n) < rate * pulse / pulse.mean() / SR
            c[at] = rng.lognormal(0, cv["crack_sigma"], int(at.sum()))
            c = _filtered(_conv(c, click), *cv["band"])
            return c / max(float(c.std()), 1e-9)

        dry_rate, wet_rate = cv["cracks_per_s"]
        mix = lambda cr: math.sqrt(cv["crack_share"]) * cr + math.sqrt(1 - cv["crack_share"]) * hiss
        dry = mix(crackle(dry_rate)) * (hum_rms * 10 ** (cv["dry_db"] / 20))
        swell = np.zeros(n, np.float32)
        if wet:   # the wet extra: more cracks and the hiss up, calibrated so a full swell is `wet_db` over dry in power
            raw = mix(crackle(wet_rate - dry_rate))
            swell = raw * (float(dry.std()) * math.sqrt(10 ** (cv["wet_db"] / 10) - 1) / max(float(raw.std()), 1e-9))
        env = np.interp(ta, tc, on[k] * gain).astype(np.float32)
        p = pans[k]
        cl, cr_ = math.cos((p + 1) * math.pi / 4), math.sin((p + 1) * math.pi / 4)
        L += dry * env * cl
        R += dry * env * cr_
        extra_l += swell * wet_a * env * cl
        extra_r += swell * wet_a * env * cr_
        voices.append({"line": k, "kv": kvs[k], "harmonic_hz": 100 * voice[k], "pan": round(p, 2)})
    # island mode: no line, the plant powering itself from one reactor: the hum's lowest partials alone, centred,
    # quiet and steady (no corona: no line is live)
    isl = _follow(np.array([rec.in_island(x) for x in tc], np.float64), *follow)
    if isl.any():
        env = np.interp(ta, tc, isl * (ISLAND_LEVEL if island_level is None else float(island_level))).astype(np.float32)
        tone = sum(a * np.sin(h * phase + rng.uniform(0, 2 * np.pi)) for h, a in ISLAND_PARTIALS).astype(np.float32)
        L += tone * env * math.cos(math.pi / 4)
        R += tone * env * math.sin(math.pi / 4)
    # the record's gaps: a low noise floor, muffled
    floor = _noise(rng, n, 50, 380) * np.interp(ta, tc, sum(unk[k] for k in keys) * gain * 0.04).astype(np.float32)
    L += floor
    R += floor
    # a faint air floor (never digital silence), then the fades: in once the camera has settled, out with the film
    air = _noise(rng, n, 20, 900) * 0.004
    out = np.stack([L + air, R + air], 1)
    extra = np.stack([extra_l, extra_r], 1)
    fade = _ss((ta - start_s) / fade_in_s) * (1 - _ss((ta - (total_s - fade_out_s)) / fade_out_s))
    out *= fade[:, None].astype(np.float32)
    extra *= fade[:, None].astype(np.float32)
    # the level: the full chord (every line connected, before the war) at `REF_DB` RMS as the ear weighs it (K-weighted,
    # as loudness meters do: the crackle's highs count for more than the hum's lows, so a louder crackle doesn't make
    # the film louder), dry (a wet day in the reference would turn every dry one down); then the wet swell on top;
    # peaks above 0.7 rounded off
    a, b = ref_s or (start_s + fade_in_s, rec.t0 + 0.5)
    ref = _kweighted(out[int(a * SR):int(b * SR)])
    out = (out + extra) * (10 ** (REF_DB / 20) / max(float(np.sqrt((ref ** 2).mean())), 1e-9))
    a = np.abs(out)
    out = np.where(a < 0.7, out, np.sign(out) * (0.7 + 0.29 * np.tanh((a - 0.7) / 0.29)))
    doc = {"statement": STATEMENT, "sample_rate": SR, "starts_s": round(start_s, 2), "fade_in_s": fade_in_s,
           "loudness": f"every line connected, dry, at {REF_DB} dB RMS K-weighted (approximated); the wet swells on top; "
                       "peaks above 0.7 rounded off",
           "voices": voices, "complete_losses": "silence (every voice stops; no diesel generators)",
           "island_mode": "every line silent; a low note of the hum's lowest partials (100 and 200 Hz) held in the "
                          "middle: the plant powering itself from one reactor (a design choice, not a recording)",
           "level": "follows how many lines are connected (750 kV 1, 330 kV 0.7, unreported 0.4 of that), compressed "
                    "to the 0.65 power",
           "corona": {"rule": "every connected line at full strength, whatever it carries (corona follows voltage, not "
                               "load); cut: silent; not reported: muffled, no crackle",
                      "by_kv": {str(kv): {**v, "band": list(v["band"]), "hiss_band": list(v["hiss_band"]),
                                          "cracks_per_s": list(v["cracks_per_s"])} for kv, v in CORONA.items()},
                      "hum_shape_by_kv": {str(kv): list(v) for kv, v in HUM_SHAPE.items()},
                      "grounding": "dB against the 750 kV line's hum; the shapes from two recordings of lines of these "
                                   "classes (research_notes/Line sound proxies/kv/compare_kv.json) and the measurements "
                                   "in reports/Enerhodar crossing voices and sound.md; the values design choices"},
           "weather": ({**(weather_doc or {}), "full_swell_wet_hours": WET_FULL_H, "rise_s": WET_RISE_S,
                        "fall_s": WET_FALL_S, "convention": "the crackle swells by the weather on the date shown, eased; "
                        "a drawing convention from modelled weather (a 25 km grid cell), not a measurement at the line",
                        "dates": _wet_dates(rec, wet, total_s)} if wet else "none: dry throughout")}
    return out.astype(np.float32), doc


def _kweighted(x: np.ndarray) -> np.ndarray:
    """x through an approximation of the K-weighting of loudness meters (ITU-R BS.1770): a high-pass about 38 Hz and a
    shelf about 4 dB up from 1-3 kHz (smooth, in the frequency domain)."""
    f = np.fft.rfftfreq(len(x), 1 / SR)
    lf = np.log2(np.maximum(f, 1.0))
    g = _ss((lf - math.log2(25)) / (math.log2(60) - math.log2(25))) * \
        (1 + (10 ** (4 / 20) - 1) * _ss((lf - math.log2(1000)) / (math.log2(3000) - math.log2(1000))))
    return np.fft.irfft(np.fft.rfft(x, axis=0) * g[:, None], len(x), axis=0)


def _wetness(rec: Record, wet: dict[int, int] | None, tc: np.ndarray) -> np.ndarray:
    """How wet the date shown is (0-1, at the control rate), eased in and out."""
    if not wet:
        return np.zeros(len(tc))
    ts = np.arange(0.0, float(tc[-1]) + 0.05, 0.05)
    w = np.zeros(len(ts))
    for i, t in enumerate(ts.tolist()):
        d = rec.shown(t)
        if d is not None:
            w[i] = min(1.0, wet.get(d.toordinal(), 0) / WET_FULL_H)
    return np.clip(_follow(np.interp(tc, ts, w), WET_RISE_S, WET_FALL_S), 0.0, 1.0)


def _wet_dates(rec: Record, wet: dict[int, int], total_s: float) -> list[dict[str, Any]]:
    """The dates shown with any wet hours, each with when it first shows (film s)."""
    out, seen = [], set()
    for t in np.arange(0.0, total_s, 0.05).tolist():
        d = rec.shown(t)
        if d is not None and d not in seen:
            seen.add(d)
            if wet.get(d.toordinal(), 0):
                out.append({"date": d.isoformat(), "wet_hours": wet[d.toordinal()], "film_s": round(t, 2)})
    return out


def write_wav(path: Path, x: np.ndarray, seed: int = 7) -> str:
    """16-bit stereo WAV (dithered); returns its sha256."""
    rng = np.random.default_rng(seed)
    d = (rng.random(x.shape) - rng.random(x.shape)) / 32768  # triangular dither
    pcm = np.clip(np.round((x + d) * 32767), -32768, 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return hashlib.sha256(path.read_bytes()).hexdigest()
