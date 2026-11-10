"""A speculative soundscape: under the Enerhodar crossing on a May morning now, one line connected (the user,
5 November 2026: "how the area under the Enerhodar crossing probably sounds like now", about 30 s, no graphics yet).

    python -I mix.py <raw dir> <xc1016141.mp3> <out.wav> <out.json>      (from the project root, the project's venv)

Nothing here was recorded at the crossing: no one has recorded there since the breach (reports/Kakhovka bed nature
sounds.md). It is a montage, said to be one:
- The line: Ferosplavna-1 (330 kV), the one line the record has connected since 24 March 2026, synthesized as the
  Hum synthesizes a 330 kV line (hum.py: the 100 Hz hum and its harmonics in the 330 kV's shape, its own partial
  stressed; corona at full strength, the 330 kV's: a smoother hiss pulsing twice a cycle, sparse cracks, rolling off
  above 8 kHz; since 9 November 2026, `HUM_SHAPE`, `CORONA`). Heard from under the span, so centred. A May morning
  "now" is no dated day, so no weather swell: the dry level (until 9 November the crackle was a little denser than the
  Hum's, for a dewy morning; dropped so the line sounds as the Hum's own 330 kV voice). It never reacts to the birds or
  they to it.
- The birds: Oleksii Vasyliuk's recordings on the drained bed at Mar'ianske, 13-14 May 2026, about 50 km downstream
  of the crossing (iNaturalist, CC BY); one thrush nightingale by Ekaterina Kormina near Marhanets, 16 April 2025,
  the north bank opposite (xeno-canto XC1016141, CC0). The marsh frog: W.D. Keeper, 28 April 2024, about 90 km
  north-west (iNaturalist, CC BY); no frog has been recorded or described on the bed, so the frog is a guess.
- Only cut, high-passed at 250 Hz (the recorders' wind rumble; the birds sing above it, the hum lies below it),
  levelled, panned and faded. Never pitched, stretched, looped or reverberated. Seconds with a broadband transient
  (screen.py: handling, a wingbeat, or a distant bang) are never used, nor 1950255's 75-85 s (a broad hump: maybe an
  engine). No sounds of fighting.
"""

import json
import math
import subprocess
import sys

import numpy as np

from image_evidence.satellite.hum import CORONA, HARMONICS, HUM_SHAPE, SR, _conv, _filtered, _noise, write_wav

TOTAL = 30.0
CROSSING = (34.60, 47.53)    # where the two lines cross the bed, for the distances only
INAT = "https://www.inaturalist.org/observations/"
# layer: file, segment in the recording (s), placed at (s), pan (-1 left .. 1 right), level (dBFS RMS where it sounds),
# fade (s), what it holds (the observations identified in it), the recording's credit and place
# Three handovers, never more than three recordings at once over the line (the user, 5 November 2026: the first mix,
# up to eight at once round 13-24 s, was too busy): one near nightingale leads throughout; behind it the reeds, then
# the frog and a far nightingale answering, then the chorus and one hoopoe. Full, not crowded.
LAYERS = [
    dict(id="nightingale-near", file="snd_1950271/1950271.wav", seg=(5, 30), at=4.0, pan=0.2, db=-20, fade=1.5,
         holds="thrush nightingale (361637893)", obs=[361637893]),
    dict(id="reeds", file="snd_1950258/1950258.wav", seg=(62, 72), at=2.5, pan=-0.55, db=-29, fade=3.0,
         holds="great reed warbler (361639437), Eurasian coot (361639473), European bee-eater (361466739)",
         obs=[361639437, 361639473, 361466739]),
    dict(id="frog", file="snd_997953/997953.wav", seg=(0, 8), at=11.5, pan=-0.3, db=-31, fade=2.0,
         holds="marsh frog (211010127)", obs=[211010127]),
    dict(id="nightingale-far", file="XC1016141", seg=(6, 14), at=13.0, pan=-0.85, db=-33, fade=2.5,
         holds="thrush nightingale, a blue tit behind (XC1016141)", obs=[]),
    dict(id="chorus", file="snd_1950176/1950176.wav", seg=(40, 47), at=20.0, pan=-0.45, db=-30, fade=2.0,
         holds="thrush nightingale, great reed warbler, common reed warbler, cuckoo (361639097, 361639110, "
               "361639062, 361639005)", obs=[361639097, 361639110, 361639062, 361639005]),
    dict(id="hoopoe", file="snd_1950256/1950256.wav", seg=(0, 6), at=21.0, pan=0.8, db=-34, fade=1.5,
         holds="Eurasian hoopoe (361466662)", obs=[361466662]),
]
HUM_DB = -30            # the line: in the background, under the birds (before the master's level)
LINE_IN, LINE_OUT = 2.5, 2.5            # the line alone first and last: it was there before the birds and stays
BIRDS = (2.0, 25.5, 2.0)                # the birds' bus: in from, out from, over (s)
MASTER_DB = -20         # the whole at about -20 dBFS RMS while the birds sing; peaks held under -1 dBFS


def decode(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def ss(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def line(n, seed=330):
    """Ferosplavna-1 alone, as hum.py voices a 330 kV line (its shape, its own partial the 6th, 600 Hz; its corona at
    full strength, dry), stereo."""
    rng = np.random.default_rng(seed)
    nc = int(math.ceil(n / SR * 1000)) + 2
    tc, ta = np.arange(nc) / 1000, np.arange(n) / SR
    f0 = 100 * (1 + 0.00015 * np.interp(ta, tc, _noise(rng, nc, None, 0.08, 1000)))
    phase = 2 * np.pi * np.cumsum(f0) / SR
    hs = np.arange(1, HARMONICS + 1)
    shape = np.array(HUM_SHAPE[330])
    a = 0.45 * shape / np.sqrt((shape ** 2).sum()) + np.exp(-((hs - 6) / 0.6) ** 2) * 0.5
    a = a / np.sqrt((a ** 2).sum()) * 0.7
    hum = np.zeros(n, np.float32)
    for h in hs:
        wob = 1 + 0.12 * _noise(rng, nc, None, 0.9, 1000)
        hum += np.interp(ta, tc, a[h - 1] * wob).astype(np.float32) * np.sin(h * phase + rng.uniform(0, 2 * np.pi)).astype(np.float32)
    cv = CORONA[330]
    pulse = (0.3 + 0.7 * np.abs(np.sin(phase / 2)) ** 6).astype(np.float32)   # twice a cycle, as the Hum's 330 kV
    tk = np.arange(int(0.006 * SR)) / SR
    out = []
    for side in range(2):     # the span runs across overhead: its crackle a little apart in each ear
        hiss = _noise(rng, n, *cv["hiss_band"]) * pulse
        hiss /= max(float(hiss.std()), 1e-9)
        cracks = np.zeros(n, np.float32)
        at = rng.random(n) < cv["cracks_per_s"][0] * pulse / pulse.mean() / SR
        cracks[at] = rng.lognormal(0, cv["crack_sigma"], int(at.sum()))
        cracks = _filtered(_conv(cracks, (rng.standard_normal(len(tk)) * np.exp(-tk / 0.0012)).astype(np.float32)),
                           *cv["band"])
        cracks /= max(float(cracks.std()), 1e-9)
        c = math.sqrt(cv["crack_share"]) * cracks + math.sqrt(1 - cv["crack_share"]) * hiss
        out.append(hum + c * (10 ** (cv["dry_db"] / 20) / math.sqrt(2)))   # against a 750 kV line's hum, as hum.py
    return np.stack(out, 1)


def limit(x, ceil, release_s=0.12):
    """A peak limiter: gain rides down at once on a peak over `ceil` and back over `release_s` (no clipping)."""
    env = np.abs(x).max(1)
    need = np.minimum(1.0, ceil / np.maximum(env, 1e-9))
    k = int(0.002 * SR)            # 2 ms look-ahead
    need = np.minimum.reduce([np.roll(need, -j) for j in range(k)])
    g = np.empty_like(need)
    v, r = 1.0, 1 - math.exp(-1 / (release_s * SR))
    for i, ni in enumerate(need.tolist()):
        v = ni if ni < v else v + (ni - v) * r
        g[i] = v
    return x * g[:, None].astype(np.float32)


def rms_db(x):
    return 20 * math.log10(max(float(np.sqrt((x ** 2).mean())), 1e-9))


def km(lon, lat):
    return math.hypot((lon - CROSSING[0]) * 111320 * math.cos(math.radians(lat)), (lat - CROSSING[1]) * 110574) / 1000


def main(raw, xc, out, out_json):
    n = int(TOTAL * SR)
    t = np.arange(n) / SR
    mix = np.zeros((n, 2), np.float32)     # the birds' bus
    clips = {}
    for row in open(f"{raw}/clips.tsv"):
        f = row.rstrip("\n").split("\t")
        clips[int(f[0])] = dict(date=f[1], user=f[2], taxon=f[3], name=f[4], licence=f[5], credit=f[6],
                                lonlat=tuple(map(float, f[8].split(",")))[::-1])
    doc = []
    for L in LAYERS:
        x = decode(xc if L["file"] == "XC1016141" else f"{raw}/{L['file']}")
        a, b = L["seg"]
        x = _filtered(x[int(a * SR):int(b * SR)], 250, None)
        m = len(x)
        x = x * (ss(np.arange(m) / SR / L["fade"]) * ss((m / SR - np.arange(m) / SR) / L["fade"])).astype(np.float32)
        x *= 10 ** ((L["db"] - rms_db(x)) / 20)
        i0 = int(L["at"] * SR)
        i1 = min(n, i0 + m)
        p = L["pan"]
        mix[i0:i1, 0] += x[:i1 - i0] * math.cos((p + 1) * math.pi / 4) * math.sqrt(2)
        mix[i0:i1, 1] += x[:i1 - i0] * math.sin((p + 1) * math.pi / 4) * math.sqrt(2)
        if L["obs"]:
            c = clips[L["obs"][0]]
            src = dict(recording=L["file"].split("/")[-1], observations=[INAT + str(o) for o in L["obs"]],
                       recordist=c["credit"], licence=c["licence"], date=c["date"],
                       place=("Mar'ianske, on the drained bed" if c["user"] == "vasyliuk1" else
                              "near Kryvyi Rih (not on the bed)"),
                       km_from_crossing=round(km(*c["lonlat"]), 0))
        else:
            src = dict(recording="XC1016141", url="https://xeno-canto.org/1016141", recordist="Ekaterina Kormina",
                       licence="CC0", date="2025-04-16", place="near Marhanets, the north bank",
                       km_from_crossing=9)     # the report's figure (R1): about 9 km from where the lines cross
        doc.append(dict(layer=L["id"], holds=L["holds"], segment_s=list(L["seg"]),
                        placed_s=[L["at"], round(min(L["at"] + m / SR, BIRDS[1] + BIRDS[2]), 2)],
                        pan=p, level_dbfs_rms=L["db"], fade_s=L["fade"], **src))
    mix *= (ss((t - BIRDS[0]) / BIRDS[2]) * (1 - ss((t - BIRDS[1]) / BIRDS[2]))).astype(np.float32)[:, None]
    mix = limit(mix, 10 ** (-12 / 20))       # the song's peaks held, so its level can sit where it sounds
    hum = line(n)
    hum *= 10 ** ((HUM_DB - rms_db(hum)) / 20)
    hum *= (ss(t / LINE_IN) * ss((TOTAL - t) / LINE_OUT)).astype(np.float32)[:, None]
    mix += hum
    a, b = int((BIRDS[0] + BIRDS[2]) * SR), int(BIRDS[1] * SR)
    mix *= 10 ** ((MASTER_DB - rms_db(mix[a:b])) / 20)
    mix = limit(mix, 0.89)                    # -1 dBFS
    sha = write_wav(__import__("pathlib").Path(out), mix)
    json.dump({"title": "Under the crossing, a May morning now (speculative)",
               "statement": ("A speculative montage, not a recording: no one has recorded at the crossing since the "
                             "breach. The line is synthesized (Ferosplavna-1, 330 kV, the one line connected since "
                             "24 March 2026, voiced as the Hum voices it, its crackle a little denser for a dewy "
                             "morning). The birds were recorded on the drained bed about 50 km downstream and on the "
                             "north bank opposite; the frog about 90 km away, since no frog has been recorded or "
                             "described on the bed. Cut, high-passed at 250 Hz, levelled, panned, faded; never "
                             "pitched, stretched, looped or reverberated. No sounds of fighting."),
               "seconds": TOTAL, "sample_rate": SR, "sha256": sha,
               "shape": f"the line alone, fading in over {LINE_IN} s; the birds in from {BIRDS[0]} s and out by "
                        f"{BIRDS[1] + BIRDS[2]} s; the line alone again, fading out over the last {LINE_OUT} s",
               "level": "the birds' bus peak-limited at -12 dBFS (2 ms look-ahead, 120 ms release), the whole at "
                        "-20 dBFS RMS while the birds sing, peaks limited at -1 dBFS",
               "line": {"name": "Ferosplavna-1", "kv": 330, "level_dbfs_rms": HUM_DB, "pan": 0,
                        "made": "hum.py's 330 kV voice (100 Hz and 11 harmonics, the 6th stressed), corona hiss and "
                                "cracks at 6 a second (the Hum's 3.5), each ear its own crackle"},
               "layers": doc, "peak_dbfs": round(20 * math.log10(float(np.abs(mix).max())), 1),
               "rms_dbfs": round(rms_db(mix), 1)}, open(out_json, "w"), indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:5])
