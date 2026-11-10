"""The v9 drowning's sound (the user, 8 November 2026: "a dramatic cut to the water already fully back"). v7's sound
(drowning_sound_v7.py) continued the soundscape past under-the-crossing's 30 s end: the line alone (the birds are gone
by 27.5 s), open until the lens went under, then muffled. v9 has no lens crossing: the eye is under from the first
frame, so the same 15 s (mix.py run 45 s long, seconds 30-45: the same recordings, seeds and levels) is muffled from
its first sample, at v7's muffled level (low-passed at 380 Hz, 3 dB under the open line's RMS). In the cut,
under-the-crossing plays with its hum run on to its last sample (v7/alt/under_the_crossing_continuous.wav: the same
45 s run's first 30 s, checked equal to 1 LSB), so the line here goes on from that sample, muffled at once: the cut is
heard as the hum closing over, with no gap and no click (the low-pass, an FFT filter, is run from 28 s so its start
is warm, and the first 2 s dropped). Its end is the run's own (the line fading over the last 2.5 s). Drawn: hearing from under the water, not a recording. No new recordings; nothing
pitched, looped or stretched; the line is synthesized.

    python -I drowning_sound_v9.py <soundscape dir> <xc1016141.mp3> <v9 dir> <scratch dir>
"""
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

SOUND = sys.argv[1]
sys.path.insert(0, os.path.join(SOUND, "scripts"))
import mix  # noqa: E402
from image_evidence.satellite.hum import SR, _filtered, write_wav  # noqa: E402

EXT, CUT = 45.0, 30.0
MUFFLE_HZ, MUFFLE_BELOW_DB = 380.0, 3.0           # v7's
WARM_S = 2.0                                      # the filter run from this much before the cut


def read_wav(p):
    import wave
    w = wave.open(p)
    return np.frombuffer(w.readframes(w.getnframes()), "<i2").reshape(-1, 2).astype(np.float32) / 32768


def rms_db(x):
    return 20 * math.log10(max(float(np.sqrt((x ** 2).mean())), 1e-12))


def main(xc, v9, scratch):
    os.makedirs(scratch, exist_ok=True)
    ext_wav = os.path.join(scratch, "under_the_crossing_45s.wav")
    if not os.path.exists(ext_wav):
        total0 = mix.TOTAL
        mix.TOTAL = EXT
        mix.main(os.path.join(SOUND, "raw"), xc, ext_wav, os.path.join(scratch, "under_the_crossing_45s.json"))
        mix.TOTAL = total0
    ext = read_wav(ext_wav)
    tail = ext[int(CUT * SR):].copy()
    open_rms = rms_db(tail[int(0.5 * SR):int(4.0 * SR)])        # v7 measured the open line over 0.5 s .. the crossing
    k = int(WARM_S * SR)
    warm = ext[int(CUT * SR) - k:]
    muff = np.stack([_filtered(warm[:, c].copy(), None, MUFFLE_HZ) for c in range(2)], 1)[k:]
    m_rms = rms_db(muff[int(0.5 * SR):int((EXT - CUT - 3) * SR)])
    g_db = open_rms - MUFFLE_BELOW_DB - m_rms
    muff *= 10 ** (g_db / 20)
    muff = mix.limit(muff, 0.89)
    out = os.path.join(v9, "drowning.wav")
    s = write_wav(Path(out), muff)
    per_s = [round(rms_db(muff[int(i * SR):int((i + 1) * SR)]), 1) for i in range(int(EXT - CUT))]
    info = {"title": "The drowning's sound, v9 (under the water from the first frame)",
            "seconds": EXT - CUT, "sample_rate": SR, "sha256": s,
            "from": "mix.py with TOTAL = 45, seconds 30-45 (the line alone, Ferosplavna-1, synthesized, seed 330), as "
                    "v7's drowning_sound_v7.py; muffled from the first sample",
            "muffle": {"low_pass_hz": MUFFLE_HZ, "below_open_line_db": MUFFLE_BELOW_DB, "gain_db": round(g_db, 1),
                       "open_line_dbfs_rms": round(open_rms, 1)},
            "start": "sample-continuous with v7/alt/under_the_crossing_continuous.wav (the cut's under-the-crossing), "
                     "muffled from the first sample (the filter warmed over the 2 s before the cut)",
            "join": {"under_the_crossing_continuous_last_50ms_dbfs": round(rms_db(ext[int(CUT * SR) - 2400:int(CUT * SR)]), 1),
                     "drowning_first_50ms_dbfs": round(rms_db(muff[:2400]), 1),
                     "largest_step_at_the_cut": round(float(np.abs(muff[0] - ext[int(CUT * SR) - 1]).max()), 5)},
            "dbfs_rms_per_second": per_s, "limit": "-1 dBFS (mix.py's limiter)",
            "peak_dbfs": round(20 * math.log10(float(np.abs(muff).max())), 1), "rms_dbfs": round(rms_db(muff), 1),
            "statement": "A montage, not a recording: nothing was recorded at the crossing. No new recordings; nothing "
                         "pitched, looped or stretched. The line is synthesized, not recorded; its muffling under "
                         "water is drawn."}
    json.dump(info, open(os.path.join(v9, "drowning_sound.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(info, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main(*sys.argv[2:5])
