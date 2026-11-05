"""The Hum on the zoom-out (decided with the user, 22 October 2026): the lines' record (`record.py`) heard.

Synthesized, not recorded (these lines can't be recorded): each of the plant's lines is a voice on the hum of a 50 Hz
grid, 100 Hz and its harmonics (transformers and lines hum at twice the grid's frequency), with corona crackle, which
follows the line's voltage. Each line stresses one harmonic of its own (a design choice, so a cut takes a partial out of
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
import math
import wave
from pathlib import Path
from typing import Any

import numpy as np

from .record import Record

SR = 48_000
CTRL = 1000  # Hz: envelopes and slow wobble, interpolated to the audio rate
HARMONICS = 12  # of 100 Hz
ISLAND_PARTIALS = ((1, 1.0), (2, 0.35))  # island mode's note: the hum's lowest partials (harmonic, amplitude)
ISLAND_LEVEL = 0.22  # its level against a line's voice (about one line alone, a little lower)
STATEMENT = ("Synthesized, not recorded. Each of the plant's lines is a voice on the 100 Hz hum of a 50 Hz grid and its "
             "harmonics, with corona crackle; each stresses one harmonic of its own (a design choice: a cut takes a "
             "partial out of the chord) and is panned by the bearing of its end from the plant. It sounds while the "
             "record says the line is connected, stops when cut and swells back when reconnected; muffled where the "
             "reports don't say which lines were cut; silent during a complete loss of off-site power; in island mode (every "
             "line cut, a reactor powering the plant itself) only a low note in the middle. The level follows "
             "how many lines are connected (compressed). It fades in once the camera has stopped pulling back, every "
             "line connected. No sounds of fighting.")


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
          follow: tuple[float, float] = (0.25, 0.012), ref_s: tuple[float, float] | None = None) -> tuple[np.ndarray, dict[str, Any]]:
    """The film's sound, stereo float32 (n, 2) at `SR`, and what was made, for film.json. It fades in from `start_s`
    (default: the record's start) over `fade_in_s`. `follow`: how fast a line swells back and falls silent (s; the
    zoom-out's: a breaker); `ref_s`: when every line sounds, for the level (default: from the fade-in to the record)."""
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
    base = 1 / hs ** 1.1
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
            a = 0.45 * base + np.exp(-((hs - voice[k]) / 0.6) ** 2) * 0.5  # its own partial, stressed
            if kvs[k] >= 750:
                a = a * np.where(hs <= 3, 1.3, 1.0)
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
    # corona: a hiss pulsing twice a cycle (at the voltage's peaks) and sparse cracks, while the line is connected
    pulse = (0.3 + 0.7 * np.abs(np.sin(phase / 2)) ** 6).astype(np.float32)
    tk = np.arange(int(0.006 * SR)) / SR
    for k in keys:
        hot = kvs[k] >= 750
        hiss = _noise(rng, n, 1800, 11000) * pulse
        cracks = np.zeros(n, np.float32)
        at = rng.random(n) < (7.0 if hot else 3.5) / SR
        cracks[at] = rng.lognormal(0, 0.6, int(at.sum()))
        cracks = _filtered(_conv(cracks, (rng.standard_normal(len(tk)) * np.exp(-tk / 0.0012)).astype(np.float32)), 900, 12000)
        c = (0.05 * hiss + 0.06 * cracks) * (1.0 if hot else 0.65)
        env = np.interp(ta, tc, on[k] * gain).astype(np.float32)
        p = pans[k]
        L += c * env * math.cos((p + 1) * math.pi / 4)
        R += c * env * math.sin((p + 1) * math.pi / 4)
        voices.append({"line": k, "kv": kvs[k], "harmonic_hz": 100 * voice[k], "pan": round(p, 2)})
    # island mode: no line, the plant powering itself from one reactor: the hum's lowest partials alone, centred,
    # quiet and steady (no corona: no line is live)
    isl = _follow(np.array([rec.in_island(x) for x in tc], np.float64), *follow)
    if isl.any():
        env = np.interp(ta, tc, isl * ISLAND_LEVEL).astype(np.float32)
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
    fade = _ss((ta - start_s) / fade_in_s) * (1 - _ss((ta - (total_s - fade_out_s)) / fade_out_s))
    out *= fade[:, None].astype(np.float32)
    # the level: the full chord (every line connected, before the war) at -10 dBFS RMS; peaks above 0.7 rounded off
    a, b = ref_s or (start_s + fade_in_s, rec.t0 + 0.5)
    ref = out[int(a * SR):int(b * SR)]
    out *= 10 ** (-10 / 20) / max(float(np.sqrt((ref ** 2).mean())), 1e-9)
    a = np.abs(out)
    out = np.where(a < 0.7, out, np.sign(out) * (0.7 + 0.29 * np.tanh((a - 0.7) / 0.29)))
    doc = {"statement": STATEMENT, "sample_rate": SR, "starts_s": round(start_s, 2), "fade_in_s": fade_in_s,
           "loudness": "every line connected at -10 dBFS RMS; peaks above 0.7 rounded off",
           "voices": voices, "complete_losses": "silence (every voice stops; no diesel generators)",
           "island_mode": "every line silent; a low note of the hum's lowest partials (100 and 200 Hz) held in the "
                          "middle: the plant powering itself from one reactor (a design choice, not a recording)",
           "level": "follows how many lines are connected (750 kV 1, 330 kV 0.7, unreported 0.4 of that), compressed "
                    "to the 0.65 power"}
    return out.astype(np.float32), doc


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
