"""The Hum of south_look3 alone (no render): written beside the stills, each channel's envelope plotted with the
selected dates, the switches counted (per line, film time) and the 200 Hz (750 kV) and 600 Hz (330 kV) partials
measured per channel. python hum_check.py <out dir>   (run from the repo root)"""
import json
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from image_evidence.satellite import network
from image_evidence.satellite.scene3d import animatic, states

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
cfg = network.config("znpp", None)
o = cfg["crossing3d"]["animatic"]
v = o["variants"]["south_look3"]
B = Path("libraries/conductive-seam/satellite/networks/znpp/scenes/crossing3d")
cam = json.loads((B / "camera_south_look3.json").read_text())
ro = states.options(cfg["crossing3d"], v)
wav = out / "south_look3_hum.wav"
animatic._hum(cfg, ro, cam["frames"], 30, wav, float(v["fade_out_s"]), Path("libraries/conductive-seam"))
with wave.open(str(wav)) as w:
    sr = w.getframerate()
    x = np.frombuffer(w.readframes(w.getnframes()), "<i2").reshape(-1, 2).astype(np.float32) / 32768
rec, doc = states.record(cfg["record"], ro)
# switches: each line's state changes between the selected dates
sw = []
for k in ro["lines"]:
    prev = None
    for d in doc["dates"]:
        s = d["states"][k]
        if prev is not None and s != prev:
            sw.append((d["film_s"][0], k, prev, s))
        prev = s
sw.sort()
moments = sorted({t for t, *_ in sw})
gaps = np.diff(moments)
# envelopes (50 ms RMS) and partials (per 0.5 s: 200 Hz and 600 Hz magnitudes)
hop = sr // 20
env = np.sqrt(np.add.reduceat(x ** 2, np.arange(0, len(x), hop), axis=0) / hop)
t = np.arange(len(env)) * hop / sr
win = sr // 2
part = []
for i in range(0, len(x) - win, win):
    seg = x[i:i + win] * np.hanning(win)[:, None]
    f = np.abs(np.fft.rfft(seg, axis=0))
    fr = np.fft.rfftfreq(win, 1 / sr)
    part.append([i / sr] + [float(f[np.argmin(np.abs(fr - h)), c]) for h in (200, 600) for c in (0, 1)])
part = np.array(part)
W, H, P = 1600, 900, 40
img = Image.new("RGB", (W, H), "white")
dr = ImageDraw.Draw(img)
T = len(x) / sr
rows = [("RMS  L=Dniprovska 750 kV (blue)  R=Ferosplavna-1 330 kV (red)", t, env[:, 0], env[:, 1]),
        ("200 Hz partial  L blue, R red", part[:, 0], part[:, 1], part[:, 2]),
        ("600 Hz partial  L blue, R red", part[:, 0], part[:, 3], part[:, 4])]
rh = (H - 2 * P) / 3
X = lambda s: P + (W - 2 * P) * s / T
for i, (lbl, tt, l, r) in enumerate(rows):
    y0 = P + i * rh
    m = max(float(l.max()), float(r.max()), 1e-9)
    dr.rectangle([P, y0, W - P, y0 + rh - 10], outline="black")
    for d in doc["dates"]:
        dr.line([X(d["film_s"][0]), y0, X(d["film_s"][0]), y0 + rh - 10], fill=(200, 200, 200))
    for ser, col in ((l, (30, 80, 200)), (r, (210, 40, 40))):
        pts = [(X(a), y0 + rh - 12 - (rh - 20) * v / m) for a, v in zip(tt, ser)]
        dr.line(pts, fill=col, width=1)
    dr.text((P + 6, y0 + 4), lbl, fill="black")
for s_ in range(0, int(T) + 1, 10):
    dr.text((X(s_) - 6, H - P + 8), f"{s_}s", fill="black")
dr.text((P, 10), "south_look3: the Hum's channels, the selected dates grey", fill="black")
img.save(out / "hum_envelopes.png")
print(json.dumps({"switch_moments": len(moments), "switches": [(round(a, 1), k, p, s) for a, k, p, s in sw],
                  "min_gap_s": round(float(gaps.min()), 2), "gaps": [round(float(g), 1) for g in gaps],
                  "partials_mean_both_on_4_8s": {"200L": round(float(part[(part[:, 0] > 4.5) & (part[:, 0] < 8), 1].mean()), 1),
                                                 "200R": round(float(part[(part[:, 0] > 4.5) & (part[:, 0] < 8), 2].mean()), 1),
                                                 "600L": round(float(part[(part[:, 0] > 4.5) & (part[:, 0] < 8), 3].mean()), 1),
                                                 "600R": round(float(part[(part[:, 0] > 4.5) & (part[:, 0] < 8), 4].mean()), 1)},
                  "rms_in_loss_59_66s": round(float(env[(t > 59.5) & (t < 66)].mean()), 5),
                  "rms_in_island_13_16s": round(float(env[(t > 13.2) & (t < 16.5)].mean()), 5),
                  "rms_both_on_5_8s": round(float(env[(t > 5) & (t < 8)].mean()), 5)}, indent=1))
