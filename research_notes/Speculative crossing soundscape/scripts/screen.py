"""Screen each recording second by second before mixing: wind (share of energy under 300 Hz) and broadband
transients (a 20 ms frame more than 18 dB over the clip's median in at least 80% of the bands from 300 Hz to 10 kHz:
handling, a wingbeat on the microphone, or a distant bang). A second with a transient is never used.

    python -I screen.py <out.json> <clip> ...      (from the project root)
"""
import json, subprocess, sys
from pathlib import Path
import numpy as np

SR = 24000

def decode(p):
    return np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                                        capture_output=True, check=True).stdout, np.float32)

def main(out, *clips):
    rep = {}
    edges = np.geomspace(300, 10000, 13)
    for c in clips:
        x = decode(c)
        win = 480
        n = len(x) // win
        fr = x[:n * win].reshape(n, win) * np.hanning(win)
        S = np.abs(np.fft.rfft(fr, axis=1)) ** 2
        f = np.fft.rfftfreq(win, 1 / SR)
        bands = np.stack([S[:, (f >= a) & (f < b)].sum(1) for a, b in zip(edges[:-1], edges[1:])], 1) + 1e-12
        db = 10 * np.log10(bands)
        hot = ((db - np.median(db, 0)) > 18).mean(1) >= 0.8
        secs = int(len(x) / SR)
        low = []
        for s in range(secs):
            F = np.abs(np.fft.rfft(x[s * SR:(s + 1) * SR])) ** 2
            ff = np.fft.rfftfreq(SR, 1 / SR)
            low.append(round(float(F[ff < 300].sum() / max(F.sum(), 1e-12)), 2))
        bad = sorted({int(i * win / SR) for i in np.nonzero(hot)[0]})
        rep[Path(c).stem] = {"seconds": secs, "transient_s": bad, "low_share": low}
    json.dump(rep, open(out, "w"), indent=1)
    for k, v in rep.items():
        print(k, v["seconds"], "transients at", v["transient_s"])
        print("   low:", "".join("#" if s > 0.8 else "+" if s > 0.5 else "." for s in v["low_share"]))

if __name__ == "__main__":
    main(*sys.argv[1:])
