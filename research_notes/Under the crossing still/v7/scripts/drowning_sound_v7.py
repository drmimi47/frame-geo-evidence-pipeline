"""The v7 drowning's sound (the user, 6 November 2026: the cut from under-the-crossing into the drowning seamless in
sound too, continuing the soundscape from its 30 s end; the muffled part louder than v6's).

What plays at under_the_crossing.wav's end (measured): the birds are gone by 27.5 s (mix.py's bus fades out over
25.5-27.5 s); the line alone then fades to silence over the last 2.5 s (mix.py's LINE_OUT), digital silence at 30 s.
So the chorus cannot drop out in the drowning (it has already gone), and the drowning keeps that state: the line
alone, muffled once the lens is under.

The line continued: mix.py run as it is but 45 s long (mix.TOTAL = 45, nothing else changed: the same recordings,
segments, placements, levels, bird-bus fade at 25.5-27.5 s, master window), so seconds 30-45 of that run are the
soundscape going on past 30 s (its line synthesized at the same seed, the same voice; with nothing but the line after
27.5 s). Two versions are written:
- drowning.wav, for the cut as it stands (v5's under_the_crossing_f_day.mp4 unchanged, ending in silence): seconds
  30-45, rising from silence over the first 2.5 s (the shot's own fade-out mirrored), so there is no jump in level at
  the cut; the hum dips to nothing across it.
- drowning_continuous.wav with under_the_crossing_continuous.wav: the 45 s run cut at 30 s, the second without the
  line's fade-out at its end, so the hum runs unbroken through the cut (sample-continuous); to use it, the
  under-the-crossing clip's sound has to be replaced by under_the_crossing_continuous.wav (made here as
  alt/under_the_crossing_f_day_continuous.mp4, v5's picture untouched).
From the lens crossing the line is low-passed and quieter (a drawn convention for hearing from under the water).
No new recordings; nothing pitched, looped or stretched. The line is synthesized.

    python -I drowning_sound_v7.py <soundscape dir> <xc1016141.mp3> <v7 dir> <scratch dir>
"""
import hashlib
import json
import math
import os
import sys
import wave
from pathlib import Path

import numpy as np

SOUND = sys.argv[1]
sys.path.insert(0, os.path.join(SOUND, "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mix  # noqa: E402
import composite_v7 as CV  # noqa: E402
from image_evidence.satellite.hum import SR, _filtered, write_wav  # noqa: E402

EXT = 45.0
CUT = 30.0
FADE_BACK = 2.5                                   # the drowning's line rising from the cut's silence (mix.py's LINE_OUT)
MUFFLE_HZ, MUFFLE_XF = 380.0, 0.3
MUFFLE_BELOW_DB = 3.0                             # the muffled hum this much under the open line's RMS (v6: ~13 dB)


def read_wav(p):
    w = wave.open(p)
    x = np.frombuffer(w.readframes(w.getnframes()), "<i2").reshape(-1, 2).astype(np.float32) / 32768
    return x


def rms_db(x):
    return 20 * math.log10(max(float(np.sqrt((x ** 2).mean())), 1e-12))


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main(xc, v7, scratch):
    os.makedirs(scratch, exist_ok=True)
    total0 = mix.TOTAL
    mix.TOTAL = EXT
    ext_wav = os.path.join(scratch, "under_the_crossing_45s.wav")
    mix.main(os.path.join(SOUND, "raw"), xc, ext_wav, os.path.join(scratch, "under_the_crossing_45s.json"))
    mix.TOTAL = total0
    ext = read_wav(ext_wav)
    orig = read_wav(os.path.join(SOUND, "under_the_crossing.wav"))
    n30 = int(CUT * SR)
    # how the 45 s run's first 30 s compare with the original (the line is a new draw of the same synthesis: its noise
    # is drawn for the run's length; the birds are the same samples)
    d = ext[:int(27.0 * SR)] - orig[:int(27.0 * SR)]
    cmp = {"first_27s_difference_dbfs_rms": round(rms_db(d), 1), "original_first_27s_dbfs_rms": round(rms_db(orig[:int(27 * SR)]), 1)}
    tail = ext[n30:].copy()
    t = np.arange(len(tail)) / SR
    tc = CV.crossing_s()
    open_rms = rms_db(tail[int(0.5 * SR):int((tc - 0.5) * SR)])
    muff = np.stack([_filtered(tail[:, c].copy(), None, MUFFLE_HZ) for c in range(2)], 1)
    m_rms = rms_db(muff[int((tc + 0.5) * SR):int((EXT - CUT - 3) * SR)])
    g_db = open_rms - MUFFLE_BELOW_DB - m_rms
    muff *= 10 ** (g_db / 20)
    w = mix.ss((t - (tc - MUFFLE_XF / 2)) / MUFFLE_XF).astype(np.float32)[:, None]
    under = tail * (1 - w) + muff * w
    under = mix.limit(under, 0.89)
    cont = os.path.join(v7, "alt", "drowning_continuous.wav")
    os.makedirs(os.path.dirname(cont), exist_ok=True)
    s_cont = write_wav(Path(cont), under)
    utc = os.path.join(v7, "alt", "under_the_crossing_continuous.wav")
    s_utc = write_wav(Path(utc), ext[:n30])
    cut_ver = under * mix.ss(t / FADE_BACK).astype(np.float32)[:, None]
    out = os.path.join(v7, "drowning.wav")
    s_out = write_wav(Path(out), cut_ver)
    # the join, checked: the last 50 ms before the cut and the first 50 ms after it
    k = int(0.05 * SR)
    join = {"cut_as_it_stands": {"under_the_crossing_last_50ms_dbfs": round(rms_db(orig[-k:]), 1),
                                 "drowning_first_50ms_dbfs": round(rms_db(cut_ver[:k]), 1)},
            "continuous_pair": {"under_the_crossing_continuous_last_50ms_dbfs": round(rms_db(ext[n30 - k:n30]), 1),
                                "drowning_continuous_first_50ms_dbfs": round(rms_db(under[:k]), 1),
                                "largest_step_at_the_cut": round(float(np.abs(under[0] - ext[n30 - 1]).max()), 5),
                                "largest_step_between_neighbouring_samples_near_the_cut":
                                    round(float(np.abs(np.diff(ext[n30 - k:n30 + k], axis=0)).max()), 5)}}
    per_s = [round(rms_db(cut_ver[int(i * SR):int((i + 1) * SR)]), 1) for i in range(int(EXT - CUT))]
    info = {"title": "The drowning's sound, v7 (the soundscape continued past its 30 s end)",
            "seconds": EXT - CUT, "sample_rate": SR,
            "what_plays_at_under_the_crossing_end": "the birds gone by 27.5 s (the bus faded over 25.5-27.5 s); the "
                                                    "line alone, fading to silence over 27.5-30 s; silence at 30 s",
            "decision": "the drowning keeps that state, the line alone, muffled once the lens is under: the chorus "
                        "has already gone at the cut, and bringing birds back would be a jump in content (and would "
                        "change under-the-crossing's own end). The soundscape is continued by running mix.py 45 s "
                        "long and taking seconds 30-45.",
            "from": "mix.py with TOTAL = 45 (nothing else changed); seconds 30-45 hold only the line (Ferosplavna-1, "
                    "synthesized, seed 330); first 27 s compared with under_the_crossing.wav: " + json.dumps(cmp),
            "files": {"drowning.wav": {"sha256": s_out, "for": "the cut as it stands (v5's clip, ending in silence)",
                                       "shape": f"rising from silence over {FADE_BACK} s, the line alone, muffled "
                                                f"from the lens crossing ({tc:.2f} s)"},
                      "alt/drowning_continuous.wav": {"sha256": s_cont, "for": "with alt/under_the_crossing_"
                                                      "continuous.wav: the hum unbroken through the cut"},
                      "alt/under_the_crossing_continuous.wav": {"sha256": s_utc, "what": "the 45 s run's first 30 s: "
                                                                "as under_the_crossing.wav but with no fade at its end "
                                                                "(and its line a new draw of the same synthesis)"}},
            "muffle": {"low_pass_hz": MUFFLE_HZ, "crossfade_s": MUFFLE_XF,
                       "gain_db": round(g_db, 1), "below_open_line_db": MUFFLE_BELOW_DB,
                       "open_line_dbfs_rms": round(open_rms, 1),
                       "note": "louder than v6's (about -35 dBFS RMS there; the user: too quiet). Drawn: hearing "
                               "from under the water, not a recording of it."},
            "join": join, "dbfs_rms_per_second": per_s,
            "limit": "-1 dBFS (mix.py's limiter)",
            "statement": "A montage, not a recording: nothing was recorded at the crossing. No new recordings; "
                         "nothing pitched, looped or stretched. The line is synthesized, not recorded; its muffling "
                         "under water is drawn.",
            "credit": "the line synthesized (the soundscape's recordings, Oleksii Vasyliuk CC BY, Ekaterina Kormina "
                      "CC0, W.D. Keeper CC BY, are silent in these 15 s)",
            "peak_dbfs": round(20 * math.log10(float(np.abs(cut_ver).max())), 1),
            "rms_dbfs": round(rms_db(cut_ver), 1)}
    json.dump(info, open(os.path.join(v7, "drowning_sound.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(info, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main(*sys.argv[2:5])
