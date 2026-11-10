"""The drowning's sound (v6, decided with the user, 6 November 2026): from the shot's own soundscape material only
(Speculative crossing soundscape, mix.py: its synthesized Ferosplavna-1 line and three of its recordings, cut and
levelled exactly as mix.py cuts and levels them, mix.py's own functions run here without changing it). No new
recordings; nothing pitched, looped or stretched.

The chorus drops out with each habitat as the drawn water reaches it (times from composite_v6.py's level): the reed
birds first (great reed warbler, coot, bee-eater), then the marsh frog, then the near thrush nightingale, gone as the
lens goes under. The line's hum runs throughout; once the lens is under it is muffled (low-passed, quieter), a
drawn convention for hearing from under water, not a recording of it.

    python -I drowning_sound_v6.py <soundscape dir> <out.wav> <out.json>
"""
import json
import math
import os
import sys
import tempfile
from pathlib import Path

import numpy as np

SOUND = sys.argv[1]
sys.path.insert(0, os.path.join(SOUND, "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mix  # noqa: E402
import composite_v6 as CV  # noqa: E402
from image_evidence.satellite.hum import SR, _filtered, write_wav  # noqa: E402

SECONDS = CV.SECONDS
FADE_IN, FADE_OUT = 1.0, 1.5
DROP_S = 0.9                                     # each layer's fade as its habitat floods
# the level (scene m) at which each layer's habitat is taken to be under: the reeds and the low wet ground first
# (the lane's lowest ground goes under from 9.3 m), the frog's shallow margins next, the nightingale's bushes last,
# with the lens; a drawn sequence, the user's order (6 November 2026)
DROPS = {"reeds": 9.4, "frog": 9.85, "nightingale-near": None}      # None: ends with the lens crossing
MUFFLE_HZ, MUFFLE_DB, MUFFLE_XF = 380.0, -6.0, 0.3


def t_of_level(h):
    ts = np.arange(0, SECONDS, 0.001)
    hs = np.array([CV.level_at(t) for t in ts])
    return float(ts[np.argmax(hs >= h)])


def master_gain():
    """The 30 s mix's master gain, read from mix.py's own run (as reprise_sound.py reads it)."""
    calls = []
    _rms = mix.rms_db

    def rec(x):
        v = _rms(x)
        calls.append(v)
        return v
    mix.rms_db = rec
    with tempfile.TemporaryDirectory() as d:
        mix.main(os.path.join(SOUND, "raw"), XC, os.path.join(d, "rerun.wav"), os.path.join(d, "rerun.json"))
        import hashlib
        same = (hashlib.sha256(open(os.path.join(d, "rerun.wav"), "rb").read()).hexdigest()
                == hashlib.sha256(open(os.path.join(SOUND, "under_the_crossing.wav"), "rb").read()).hexdigest())
    mix.rms_db = _rms
    return mix.MASTER_DB - calls[len(mix.LAYERS) + 1], same


XC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(SOUND))), "research_notes", "Line sound proxies",
                  "raw", "xc", "XC1016141", "XC1016141.mp3")


def main(out, out_json):
    n = int(SECONDS * SR)
    t = np.arange(n) / SR
    tc = CV.crossing_s()
    mdb, same = master_gain()
    birds = np.zeros((n, 2), np.float32)
    layers = []
    clips = {}
    for row in open(os.path.join(SOUND, "raw", "clips.tsv")):
        f = row.rstrip("\n").split("\t")
        clips[int(f[0])] = dict(date=f[1], credit=f[6], licence=f[5], user=f[2])
    for lid in ("reeds", "frog", "nightingale-near"):
        L = next(L for L in mix.LAYERS if L["id"] == lid)
        x = mix.decode(os.path.join(SOUND, "raw", L["file"]))
        a, b = L["seg"]
        x = _filtered(x[int(a * SR):int(b * SR)], 250, None)
        m = len(x)
        x = x * (mix.ss(np.arange(m) / SR / L["fade"]) * mix.ss((m / SR - np.arange(m) / SR) / L["fade"])).astype(np.float32)
        x *= 10 ** ((L["db"] - mix.rms_db(x)) / 20)       # mix.py's level, over its whole segment
        # placed from the shot's start: its segment from the beginning (cut short by the drop, never looped)
        y = np.zeros(n, np.float32)
        k = min(n, m)
        y[:k] = x[:k]
        if DROPS[lid] is None:
            end = tc + 0.1
        else:
            end = t_of_level(DROPS[lid]) + DROP_S
        env = mix.ss(t / FADE_IN) * (1 - mix.ss((t - (end - DROP_S)) / DROP_S))
        y *= env.astype(np.float32)
        p = L["pan"]
        birds[:, 0] += y * math.cos((p + 1) * math.pi / 4) * math.sqrt(2)
        birds[:, 1] += y * math.sin((p + 1) * math.pi / 4) * math.sqrt(2)
        c = clips[L["obs"][0]]
        layers.append({"layer": lid, "holds": L["holds"], "recording": L["file"].split("/")[-1],
                       "observations": [mix.INAT + str(o) for o in L["obs"]], "recordist": c["credit"],
                       "licence": c["licence"], "date": c["date"],
                       "place": ("Mar'ianske, on the drained bed, about 50 km downstream" if c["user"] == "vasyliuk1"
                                 else "near Kryvyi Rih, not on the bed (no frog has been recorded or described on "
                                      "the bed: the frog is a guess)"),
                       "recording_seconds_used": [a, round(a + min(m / SR, end), 2)],
                       "level_dbfs_rms": L["db"], "pan": p,
                       "drops_at_level_m": DROPS[lid], "gone_by_s": round(end, 2),
                       "drop": f"faded out over {DROP_S} s"
                               + (" as the lens goes under" if DROPS[lid] is None else
                                  f" once the drawn water reaches {DROPS[lid]} m")})
    birds = mix.limit(birds, 10 ** (-12 / 20))          # the birds' bus limiter, as mix.py
    hum = mix.line(int(mix.TOTAL * SR))[:n]               # the 30 s line as mix.py synthesizes it (seed 330), its
    hum *= 10 ** ((mix.HUM_DB - mix.rms_db(hum)) / 20)    # first 15 s
    muff = np.stack([_filtered(hum[:, c].copy(), None, MUFFLE_HZ) for c in range(2)], 1) * 10 ** (MUFFLE_DB / 20)
    w = mix.ss((t - (tc - MUFFLE_XF / 2)) / MUFFLE_XF).astype(np.float32)[:, None]
    hum = hum * (1 - w) + muff * w
    y = (birds + hum) * 10 ** (mdb / 20)
    y *= (mix.ss(t / 0.5) * mix.ss((SECONDS - t) / FADE_OUT)).astype(np.float32)[:, None]
    y = mix.limit(y, 0.89)
    sha = write_wav(Path(out), y)
    info = {"title": "The drowning's sound (from the speculative soundscape's own material)",
            "seconds": SECONDS, "sample_rate": SR, "sha256": sha,
            "from": "Speculative crossing soundscape (mix.py): its synthesized line and three of its recordings, "
                    "each cut, high-passed at 250 Hz, faded and levelled exactly as mix.py does, panned as there",
            "line": {"name": "Ferosplavna-1", "kv": 330, "made": "synthesized by mix.py's line() (hum.py's 330 kV "
                     "voice: 100 Hz and its harmonics, the 6th stressed, corona hiss and cracks), seed 330, the first "
                     f"15 s of its 30 s, {mix.HUM_DB} dBFS RMS before the master",
                     "under": f"from the lens crossing ({tc:.2f} s) low-passed at {MUFFLE_HZ:.0f} Hz and "
                              f"{MUFFLE_DB:.0f} dB, crossfaded over {MUFFLE_XF} s: a drawn convention for hearing "
                              "from under the water"},
            "layers": layers,
            "order": "the reed birds first, then the frog, then the near nightingale (with the lens); the hum "
                     "throughout (the user, 6 November 2026)",
            "master_gain_db": round(mdb, 2), "mix_rerun_matches_original": same,
            "fades_s": {"in": 0.5, "birds_in": FADE_IN, "out": FADE_OUT},
            "limit": "the birds' bus at -12 dBFS, the whole at -1 dBFS (mix.py's limiter)",
            "statement": "A montage, not a recording: nothing was recorded at the crossing. No new recordings; "
                         "nothing pitched, looped or stretched. The line is synthesized, not recorded; its "
                         "muffling under water is drawn.",
            "credit": "Oleksii Vasyliuk (CC BY), W.D. Keeper (CC BY), via iNaturalist; the line synthesized",
            "peak_dbfs": round(20 * math.log10(float(np.abs(y).max())), 1), "rms_dbfs": round(mix.rms_db(y), 1)}
    json.dump(info, open(out_json, "w"), indent=1, ensure_ascii=False)
    print(json.dumps(info, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[2], sys.argv[3])
