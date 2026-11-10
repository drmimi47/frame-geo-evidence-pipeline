"""The two proxies measured side by side, to ground the Hum's 750 kV and 330 kV voices (the user, 9 November 2026: "ensure
that the 750 and 330 sound different since it seems like they do according to the two videos on the storyboard
timeline"): the 750 kV line in fog (Ted3871, autumn 2021) as the cut plays it (0-24 s) and the 330 kV crossing in dry
spring air (Dmitry Novoklimov, 9 May 2012) as its parked shot plays it (0-16 s).

Measured on each: the level of the 100 Hz tone and its harmonics over their neighbours, the high band's level against
the hum's (the crackle and hiss, 1.5-8 kHz, against 80-420 Hz), where the high band's energy peaks, and how often it
cracks (impulses: 2-8 kHz envelope in 5 ms frames more than 8 dB over its running median, at least 20 ms apart).
Two recordings, different microphones, distances and weather: a direction and rough sizes, not a calibration.

    .venv/bin/python -I "research_notes/Line sound proxies/scripts/compare_kv.py"
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent.parent
SR = 48000
CLIPS = {"750": ("proxy-750kV-fog.mp4", 0, 24), "330": ("proxy-330kV-crossing.mp4", 0, 16)}


def decode(f, a, b):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(a), "-t", str(b - a), "-i", str(HERE / f), "-ac", "1",
                          "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)


def band_db(P, f, lo, hi):
    m = (f >= lo) & (f < hi)
    return 10 * np.log10(P[m].sum() + 1e-20)


def measure(x):
    n = 1 << 15
    win = np.hanning(n)
    frames = [x[i:i + n] * win for i in range(0, len(x) - n, n // 2)]
    P = np.mean([np.abs(np.fft.rfft(fr)) ** 2 for fr in frames], 0)
    f = np.fft.rfftfreq(n, 1 / SR)
    tones = {}
    for h in (50, 100, 200, 300, 400, 600):
        pk = band_db(P, f, h - 2, h + 2)
        nb = (band_db(P, f, h - 12, h - 4) + band_db(P, f, h + 4, h + 12)) / 2 + 10 * np.log10(4 / 8)
        tones[f"{h}_hz_over_neighbours_db"] = round(pk - nb, 1)
    hi_db, hum_db = band_db(P, f, 1500, 8000), band_db(P, f, 80, 420)
    m = (f >= 500) & (f < 12000)
    cen = float((f[m] * P[m]).sum() / P[m].sum())
    # cracks
    X = np.fft.rfft(x)
    fx = np.fft.rfftfreq(len(x), 1 / SR)
    hb = np.fft.irfft(X * ((fx >= 2000) & (fx < 8000)), len(x))
    fl = int(0.005 * SR)
    env = 10 * np.log10(np.array([np.mean(hb[i:i + fl] ** 2) for i in range(0, len(hb) - fl, fl)]) + 1e-20)
    med = np.array([np.median(env[max(0, i - 100):i + 100]) for i in range(len(env))])
    hits, last = 0, -999
    for i, v in enumerate(env - med):
        if v > 8 and i - last >= 4:
            hits, last = hits + 1, i
    oct = {f"{lo}-{2 * lo}": round(band_db(P, f, lo, 2 * lo) - hi_db, 1) for lo in (500, 1000, 2000, 4000, 8000)}
    return {"seconds": round(len(x) / SR, 1), "rms_dbfs": round(20 * np.log10(np.sqrt((x ** 2).mean())), 1), **tones,
            "high_1500_8000_over_hum_80_420_db": round(hi_db - hum_db, 1), "high_centroid_500_12000_hz": round(cen),
            "octaves_against_high_band_db": oct, "cracks_per_s": round(hits / (len(x) / SR), 2)}


def main():
    out = {}
    for kv, (f, a, b) in CLIPS.items():
        out[kv] = {"file": f, "from_s": a, "to_s": b, **measure(decode(f, a, b))}
    out["note"] = ("Two recordings, different microphones, distances and weather (the 750 kV in fog, the 330 kV in dry "
                   "spring air with wind): a direction and rough sizes for the Hum's two voices, never a calibration.")
    (HERE / "kv" / "compare_kv.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
