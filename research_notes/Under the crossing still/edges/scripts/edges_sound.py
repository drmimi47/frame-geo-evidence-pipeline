"""Under the crossing with the nature sounds there from its first frame to its last (the user, 9 November 2026: "the
nature sounds are immediately heard when that video segment begins and ends. currently, it takes a couple seconds to
fade in and fade out").

The cut's under-the-crossing (v7/alt/under_the_crossing_f_day_continuous.mp4) plays mix.py's soundscape run 45 s and
cut at 30 s: the line fading in over 2.5 s, the birds' bus in over 2-4 s and out over 25.5-27.5 s, the line alone
after. Here, the same recordings, placements, pans and levels, with three changes:
- the birds' bus has no fades: full from 0 s to the cut at 30 s;
- three layers run on to the edges, each the same recording at the same alignment (the second of the recording heard
  at a given time unchanged), only longer, and only through seconds screen.py found clean: the near nightingale from
  0 s (1950271, 1-31 s, was 5-30 s at 4 s), the reeds from 0 s (1950258, 59.5-72 s, was 62-72 s at 2.5 s), the chorus
  to 30 s (1950176, 40-50 s, was 40-47 s); at 0 s and 30 s a 20 ms ramp only, against a click; inside, the fades as
  before. Still never more than three recordings at once;
- the line starts at once (a 20 ms ramp, was 2.5 s).
The line itself is the same samples at the same gain (the 45 s run's master gain, applied unchanged), so at 30 s it is
still sample-continuous with the drowning's sound (v9's, from the same run's 30 s on); only the birds now stop at the
cut. Nothing pitched, stretched, looped or reverberated; the line is synthesized; no new recordings.

    python -I edges_sound.py <soundscape dir> <xc1016141.mp3> <v5 picture mp4> <out dir>   (from the project root)
"""
import hashlib
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

SOUND, XC, PICTURE, OUT = sys.argv[1:5]
sys.path.insert(0, os.path.join(SOUND, "scripts"))
import mix  # noqa: E402
from image_evidence.satellite.hum import SR, _filtered, write_wav  # noqa: E402

EXT, CUT, EDGE = 45.0, 30.0, 0.02
# id -> new segment, placed at, fade in, fade out (None: the layer as in mix.py)
LONGER = {"nightingale-near": ((1, 31), 0.0, EDGE, EDGE),
          "reeds": ((59.5, 72), 0.0, EDGE, 3.0),
          "chorus": ((40, 50), 20.0, 2.0, EDGE)}
CLEAN = json.load(open(os.path.join(SOUND, "check_screen.json")))


def layers_bus(n, layers, fades):
    t = np.arange(n) / SR
    bus = np.zeros((n, 2), np.float32)
    for L in layers:
        x = mix.decode(XC if L["file"] == "XC1016141" else f"{SOUND}/raw/{L['file']}")
        a, b = L["seg"]
        key = "XC1016141" if L["file"] == "XC1016141" else L["file"].split("/")[-1][:-4]
        bad = [s for s in CLEAN[key]["transient_s"] if a - 1 < s < b]
        if bad:
            raise ValueError(f"{L['id']}: seconds {bad} of {key} have a transient")
        x = _filtered(x[int(a * SR):int(b * SR)], 250, None)
        m = len(x)
        fi, fo = L.get("fade_in", L["fade"]), L.get("fade_out", L["fade"])
        x = x * (mix.ss(np.arange(m) / SR / fi) * mix.ss((m / SR - np.arange(m) / SR) / fo)).astype(np.float32)
        x *= 10 ** ((L["db"] - mix.rms_db(x)) / 20) if L.get("ref") is None else L["ref"]
        i0 = int(L["at"] * SR)
        i1 = min(n, i0 + m)
        p = L["pan"]
        bus[i0:i1, 0] += x[:i1 - i0] * math.cos((p + 1) * math.pi / 4) * math.sqrt(2)
        bus[i0:i1, 1] += x[:i1 - i0] * math.sin((p + 1) * math.pi / 4) * math.sqrt(2)
    if fades:
        b0, b1, ov = mix.BIRDS
        bus *= (mix.ss((t - b0) / ov) * (1 - mix.ss((t - b1) / ov))).astype(np.float32)[:, None]
    return mix.limit(bus, 10 ** (-12 / 20))


def gains(layers):
    """Each layer's gain in mix.py's run (levelled on its own segment there): kept, so a longer segment of the same
    recording plays at the same loudness, not re-levelled on its new length."""
    g = {}
    for L in layers:
        x = mix.decode(XC if L["file"] == "XC1016141" else f"{SOUND}/raw/{L['file']}")
        a, b = L["seg"]
        x = _filtered(x[int(a * SR):int(b * SR)], 250, None)
        m = len(x)
        x = x * (mix.ss(np.arange(m) / SR / L["fade"]) * mix.ss((m / SR - np.arange(m) / SR) / L["fade"])).astype(np.float32)
        g[L["id"]] = 10 ** ((L["db"] - mix.rms_db(x)) / 20)
    return g


def main():
    n = int(EXT * SR)
    t = np.arange(n) / SR
    old = [dict(L) for L in mix.LAYERS]
    g = gains(old)
    new = []
    for L in old:
        L = dict(L, ref=g[L["id"]])
        if L["id"] in LONGER:
            seg, at, fi, fo = LONGER[L["id"]]
            L.update(seg=seg, at=at, fade_in=fi, fade_out=fo)
        new.append(L)
    hum = mix.line(n)                                   # the same seed and length as the 45 s run: the same samples
    hum *= 10 ** ((mix.HUM_DB - mix.rms_db(hum)) / 20)
    a, b = int((mix.BIRDS[0] + mix.BIRDS[2]) * SR), int(mix.BIRDS[1] * SR)
    # the 45 s run as mix.py made it, for its master gain only
    old_mix = layers_bus(n, [dict(L, ref=g[L["id"]]) for L in old], True) + \
        hum * (mix.ss(t / mix.LINE_IN) * mix.ss((EXT - t) / mix.LINE_OUT)).astype(np.float32)[:, None]
    master = 10 ** ((mix.MASTER_DB - mix.rms_db(old_mix[a:b])) / 20)
    line = hum * mix.ss(t / EDGE).astype(np.float32)[:, None]      # no fade-out: it runs on past the cut
    out = (layers_bus(n, new, False) + line) * master
    out = mix.limit(out[:int(CUT * SR)], 0.89)
    os.makedirs(OUT, exist_ok=True)
    wav = Path(OUT) / "under_the_crossing_edges.wav"
    sha = write_wav(wav, out)
    # the join: the line's last 50 ms here against the same run's line alone (what the drowning continues)
    ref = (line * master)[int(CUT * SR) - 2400:int(CUT * SR)]
    mp4 = Path(OUT) / "under_the_crossing_f_day_edges.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", PICTURE, "-i", str(wav), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-t", str(CUT), "-movflags", "+faststart", str(mp4)], check=True)
    first = out[:int(0.5 * SR)]
    doc = {"title": "Under the crossing, a May morning now (speculative): the nature sounds edge to edge",
           "asked": "the user, 9 November 2026: the nature sounds heard at once when the shot begins and until it ends",
           "picture": f"{PICTURE} (v5's, copied unchanged)", "sound": wav.name, "sha256": sha, "seconds": CUT,
           "from": "mix.py's soundscape run 45 s (the cut's under-the-crossing), its first 30 s, with the changes below",
           "changes": {"birds_bus": "no fades (was in over 2-4 s, out over 25.5-27.5 s)",
                       "layers": {k: {"segment_s": list(v[0]), "placed_s": v[1], "fade_in_s": v[2], "fade_out_s": v[3]}
                                  for k, v in LONGER.items()},
                       "line": f"in over {EDGE} s (was {mix.LINE_IN} s); no fade-out (runs on into the drowning)",
                       "levels": "each layer at its gain in mix.py's run; the master gain of the 45 s run, unchanged"},
           "screened": "every second used is clean in check_screen.json (no broadband transient)",
           "at_most_three_at_once": True,
           "first_500ms_dbfs_rms": round(mix.rms_db(first), 1),
           "last_500ms_dbfs_rms": round(mix.rms_db(out[-int(0.5 * SR):]), 1),
           "join": {"line_alone_last_50ms_dbfs": round(mix.rms_db(ref), 1),
                    "note": "the line here is the 45 s run's line at its gain, so the drowning (v9's sound, the same run "
                            "from 30 s) goes on from it; the birds stop at the cut"},
           "peak_dbfs": round(20 * math.log10(float(np.abs(out).max())), 1),
           "statement": "A speculative montage, not a recording (as under_the_crossing.json says): the line synthesized, "
                        "the birds recorded on the drained bed about 50 km downstream and on the north bank opposite, the "
                        "frog about 90 km away. Cut, high-passed, levelled, panned; never pitched, stretched, looped or "
                        "reverberated. No sounds of fighting.",
           "mp4": mp4.name, "mp4_sha256": hashlib.sha256(mp4.read_bytes()).hexdigest()}
    json.dump(doc, open(Path(OUT) / "edges.json", "w"), indent=1)
    print(json.dumps({k: doc[k] for k in ("first_500ms_dbfs_rms", "last_500ms_dbfs_rms", "join", "peak_dbfs")}))


if __name__ == "__main__":
    main()
