"""The truer Hum (the user, 9 November 2026: the crackle at full strength on every connected line, swelling in rain and fog
on the dates ERA5 shows them, 750 and 330 kV distinct) checked against the Hum it replaces, on two films' wavs:
loudness (RMS and ffmpeg's EBU R128 integrated loudness), peaks, the crackle band's level against the hum band's over
time with the wet dates marked, and each channel's spectrogram (Dniprovska right, Ferosplavna-1 left).

    python truer_check.py <old.wav> <new.wav> <sound.json with hum.py's doc> <out dir> <name> [south|ten]   (from the repo root)
    south: the flight south's sides (Dniprovska left, Ferosplavna-1 right); ten: the zoom-out's ten lines
"""
import json
import re
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

OLD, NEW, DOC, OUT, NAME = sys.argv[1:6]
SIDES = {"south": (("left", "Dniprovska, 750 kV"), ("right", "Ferosplavna-1, 330 kV")),
         "ten": (("left", "the lines panned by bearing"), ("right", "the lines panned by bearing"))}.get(
    (sys.argv[6:7] or [""])[0], (("left", "Ferosplavna-1, 330 kV"), ("right", "Dniprovska, 750 kV")))
out = Path(OUT)
out.mkdir(parents=True, exist_ok=True)
F = ImageFont.truetype("/System/Library/Fonts/HelveticaNeue.ttc", 15)


def read(p):
    with wave.open(p) as w:
        return np.frombuffer(w.readframes(w.getnframes()), "<i2").reshape(-1, 2).astype(np.float32) / 32768, w.getframerate()


def lufs(p):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", p, "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1])


def bands(x, sr, hop=0.25):
    n = int(sr * 0.25)
    w = np.hanning(n)
    f = np.fft.rfftfreq(n, 1 / sr)
    hi, lo = (f >= 1500) & (f < 12000), (f >= 80) & (f < 650)
    rows = []
    for i in range(0, len(x) - n, int(sr * hop)):
        P = np.abs(np.fft.rfft(x[i:i + n] * w)) ** 2
        rows.append((10 * np.log10(P[hi].sum() + 1e-12), 10 * np.log10(P[lo].sum() + 1e-12)))
    return np.array(rows)


def spectrogram(x, sr, path, title, dates):
    n = 4096
    w = np.hanning(n)
    cols = []
    for i in range(0, len(x) - n, sr // 20):
        cols.append(20 * np.log10(np.abs(np.fft.rfft(x[i:i + n] * w)) + 1e-9))
    S = np.array(cols).T
    f = np.fft.rfftfreq(n, 1 / sr)
    H = 360
    edges = np.geomspace(60, 16000, H + 1)   # log frequency
    img = np.stack([S[(f >= a) & (f < b)].max(0) if ((f >= a) & (f < b)).any() else S[np.searchsorted(f, a)]
                    for a, b in zip(edges[:-1], edges[1:])])[::-1]
    v = np.clip((img - (img.max() - 80)) / 80, 0, 1)
    im = Image.fromarray((v * 255).astype(np.uint8)).resize((1400, H)).convert("RGB")
    c = Image.new("RGB", (1400, H + 60), (0, 0, 0))
    c.paste(im, (0, 40))
    g = ImageDraw.Draw(c)
    g.text((8, 10), title, font=F, fill=(255, 255, 255))
    for hz in (100, 200, 600, 1000, 4000, 10000):
        y = 40 + H - int(np.log(hz / 60) / np.log(16000 / 60) * H)
        g.text((4, y - 8), f"{hz} Hz", font=F, fill=(255, 210, 0))
    dur = len(x) / sr
    for d in dates:
        xx = int(d["film_s"] / dur * 1400)
        g.line([(xx, 40), (xx, 44)], fill=(120, 200, 255), width=2)
    g.text((8, H + 42), f"0-{dur:.0f} s · blue ticks: dates shown with wet hours (ERA5)", font=F, fill=(200, 200, 200))
    c.save(path)


old, sr = read(OLD)
new, _ = read(NEW)
doc = json.loads(Path(DOC).read_text())
dates = doc["weather"]["dates"] if isinstance(doc.get("weather"), dict) else []
res = {}
for k, x, p in (("old", old, OLD), ("new", new, NEW)):
    res[k] = {"rms_dbfs": round(float(20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-12)), 1),
              "peak_dbfs": round(float(20 * np.log10(np.abs(x).max() + 1e-12)), 1), "lufs_integrated": lufs(p)}
    b = {f"{side} ({who})": bands(x[:, i], sr) for i, (side, who) in enumerate(SIDES)}
    res[k]["crackle_over_hum_db_median"] = {ch: round(float(np.median(v[:, 0] - v[:, 1])), 1) for ch, v in b.items()}
    for i, (side, who) in enumerate(SIDES):
        spectrogram(x[:, i], sr, out / f"{NAME}_{k}_{side}.png", f"{NAME} · {k} · {side} ({who})", dates)
# wet against dry in the new: the crackle band at wet dates against dry ones, per channel
bn = {ch: bands(new[:, i], sr) for i, ch in ((0, "left"), (1, "right"))}
t = np.arange(len(bn["left"])) * 0.25
wet_t = [d["film_s"] for d in dates if d["wet_hours"] >= 6]
res["wet_dates_shown"] = len(dates)
res["full_swell_dates"] = len(wet_t)
res["dates"] = dates
(out / f"{NAME}_check.json").write_text(json.dumps(res, indent=1))
print(json.dumps({k: v for k, v in res.items() if k != "dates"}, indent=1))
