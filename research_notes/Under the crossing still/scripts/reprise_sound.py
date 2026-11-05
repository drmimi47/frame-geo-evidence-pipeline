"""The reprise's sound (v5 `waterline-reprise`): a calm stretch of the shot's own soundscape (Speculative crossing
soundscape/under_the_crossing.wav, made by its mix.py), only two of its parts: the line (Ferosplavna-1, synthesized as
the Hum does) and the near nightingale (iNat sound 1950271, Oleksii Vasyliuk, Mar'ianske on the drained bed, 14 May
2026, CC BY). No new recordings; never pitched, looped or stretched.

Both are made exactly as mix.py makes them for the 30 s mix (mix.py's own functions, run here without changing it):
the line synthesized for the whole 30 s with its seed and level, the nightingale's segment (5-30 s of the recording)
high-passed, faded, levelled and placed at 4 s, and the 30 s mix's master gain (read from mix.py's own run, which is
checked to reproduce under_the_crossing.wav bit for bit). Then one window of that 30 s timeline is cut, faded in and
out, and limited at -1 dBFS as mix.py limits.

    python -I reprise_sound.py <soundscape dir> <xc1016141.mp3> <scratch dir> <out.wav> <out.json> [t0] [seconds]
"""
import hashlib
import json
import math
import os
import sys

import numpy as np

SOUND = sys.argv[1]
sys.path.insert(0, os.path.join(SOUND, "scripts"))
import mix  # noqa: E402
from image_evidence.satellite.hum import SR, _filtered, write_wav  # noqa: E402


def main(xc, scratch, out, out_json, t0=13.5, secs=9.0, fade_in=1.0, fade_out=1.5):
    raw = os.path.join(SOUND, "raw")
    # mix.py's own run, its rms_db calls recorded: the master gain is MASTER_DB minus the call on the birds' stretch
    calls = []
    _rms = mix.rms_db

    def rec(x):
        v = _rms(x)
        calls.append(v)
        return v
    mix.rms_db = rec
    full = os.path.join(scratch, "under_the_crossing_rerun.wav")
    mix.main(raw, xc, full, os.path.join(scratch, "under_the_crossing_rerun.json"))
    mix.rms_db = _rms
    orig = os.path.join(SOUND, "under_the_crossing.wav")
    same = hashlib.sha256(open(full, "rb").read()).hexdigest() == hashlib.sha256(open(orig, "rb").read()).hexdigest()
    master_db = mix.MASTER_DB - calls[len(mix.LAYERS) + 1]
    n30 = int(mix.TOTAL * SR)
    # the near nightingale, as in the 30 s mix
    L = next(L for L in mix.LAYERS if L["id"] == "nightingale-near")
    x = mix.decode(os.path.join(raw, L["file"]))
    a, b = L["seg"]
    x = _filtered(x[int(a * SR):int(b * SR)], 250, None)
    m = len(x)
    x = x * (mix.ss(np.arange(m) / SR / L["fade"]) * mix.ss((m / SR - np.arange(m) / SR) / L["fade"])).astype(np.float32)
    x *= 10 ** ((L["db"] - _rms(x)) / 20)
    bird = np.zeros((n30, 2), np.float32)
    i0 = int(L["at"] * SR)
    i1 = min(n30, i0 + m)
    p = L["pan"]
    bird[i0:i1, 0] += x[:i1 - i0] * math.cos((p + 1) * math.pi / 4) * math.sqrt(2)
    bird[i0:i1, 1] += x[:i1 - i0] * math.sin((p + 1) * math.pi / 4) * math.sqrt(2)
    bird = mix.limit(bird, 10 ** (-12 / 20))     # the birds' bus limiter (in the 30 s mix it held all the birds)
    hum = mix.line(n30)
    hum *= 10 ** ((mix.HUM_DB - _rms(hum)) / 20)
    w0, w1 = int(t0 * SR), int((t0 + secs) * SR)
    y = (bird[w0:w1] + hum[w0:w1]) * 10 ** (master_db / 20)
    t = np.arange(len(y)) / SR
    y *= (mix.ss(t / fade_in) * mix.ss((secs - t) / fade_out)).astype(np.float32)[:, None]
    y = mix.limit(y, 0.89)
    sha = write_wav(__import__("pathlib").Path(out), y)
    rec_s = [round(a + (t0 - L["at"]), 2), round(a + (t0 + secs - L["at"]), 2)]
    info = {"title": "The waterline reprise's sound (a stretch of the speculative soundscape)",
            "seconds": secs, "sample_rate": SR, "sha256": sha,
            "from": "Speculative crossing soundscape/under_the_crossing.wav (mix.py), seconds "
                    f"{t0}-{t0 + secs} of its 30 s, only the line and the near nightingale",
            "rerun_matches_original": same, "master_gain_db": round(master_db, 2),
            "line": "Ferosplavna-1 as mix.py synthesizes it (seed 330, the 30 s synthesized and the same window cut; "
                    f"{mix.HUM_DB} dBFS RMS before the master)",
            "nightingale": {"recording": "iNat sound 1950271 (observation 361637893)", "recordist": "Oleksii Vasyliuk",
                            "licence": "CC BY", "date": "2026-05-14", "place": "Mar'ianske, on the drained bed",
                            "recording_seconds": rec_s, "level_dbfs_rms": L["db"], "pan": p},
            "fades_s": [fade_in, fade_out], "limit": "-1 dBFS (mix.py's limiter)",
            "statement": "No new recordings: cut from the shot's own montage; never pitched, looped or stretched. "
                         "The line is synthesized, not recorded.",
            "peak_dbfs": round(20 * math.log10(float(np.abs(y).max())), 1), "rms_dbfs": round(_rms(y), 1)}
    json.dump(info, open(out_json, "w"), indent=1)
    print(json.dumps(info, indent=1))


if __name__ == "__main__":
    a = sys.argv[2:]
    main(a[0], a[1], a[2], a[3], *(float(v) for v in a[4:]))
