"""Spectrograms of the downloaded recordings, one row each, to check them before mixing: for engines and drones (a
harmonic stack low down, sweeping), explosions (broadband thumps under 300 Hz), voices and handling.

    python -I spectro.py <out.png> <out.json> <clip.wav> ...      (from the project root)

Log-frequency rows 50 Hz-12 kHz, 20 px a second; under each row the level each second (RMS) and the share of it under
300 Hz (a thump or an engine lifts it).
"""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

SR = 24000
PPS = 20
ROW_H = 160
FONT = "/System/Library/Fonts/HelveticaNeue.ttc"


def decode(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def main(out, out_json, *clips):
    rows, report = [], {}
    f_lo, f_hi = np.log2(50), np.log2(12000)
    for c in clips:
        x = decode(c)
        hop, win = SR // PPS, 2048
        frames = [x[i:i + win] * np.hanning(win) for i in range(0, max(1, len(x) - win), hop)]
        S = np.abs(np.fft.rfft(np.array(frames), axis=1)) + 1e-9
        f = np.fft.rfftfreq(win, 1 / SR)
        bins = np.clip(((np.log2(np.maximum(f, 1)) - f_lo) / (f_hi - f_lo) * ROW_H).astype(int), -1, ROW_H)
        img = np.zeros((ROW_H, len(frames)))
        for b in range(ROW_H):
            m = bins == b
            if m.any():
                img[ROW_H - 1 - b] = 20 * np.log10(S[:, m].mean(1))
        img = np.clip((img - img.max() + 70) / 70, 0, 1)
        rows.append((Path(c).stem, (img * 255).astype(np.uint8)))
        sec = [x[i * SR:(i + 1) * SR] for i in range(int(len(x) / SR))]
        lo = []
        for s in sec:
            F = np.abs(np.fft.rfft(s)) ** 2
            ff = np.fft.rfftfreq(len(s), 1 / SR)
            lo.append(float(F[ff < 300].sum() / max(F.sum(), 1e-12)))
        report[Path(c).stem] = {"seconds": round(len(x) / SR, 1),
                                "rms_db": [round(20 * np.log10(max(float(np.sqrt((s ** 2).mean())), 1e-9)), 1) for s in sec],
                                "low_share": [round(v, 2) for v in lo]}
    width = max(r[1].shape[1] for r in rows) + 120
    sheet = Image.new("RGB", (width, len(rows) * (ROW_H + 40)), (0, 0, 0))
    d = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(FONT, 14, index=0)
    for i, (name, img) in enumerate(rows):
        y = i * (ROW_H + 40)
        sheet.paste(Image.fromarray(img).convert("RGB"), (120, y))
        d.text((8, y + 4), name, font=font, fill=(255, 255, 255))
        for hz in (100, 300, 1000, 3000, 10000):
            yy = y + ROW_H - 1 - int((np.log2(hz) - f_lo) / (f_hi - f_lo) * ROW_H)
            d.text((70, yy - 8), f"{hz if hz < 1000 else str(hz // 1000) + 'k'}", font=font, fill=(160, 160, 160))
        for s in range(0, img.shape[1] // PPS + 1, 10):
            d.text((120 + s * PPS, y + ROW_H + 2), f"{s}s", font=font, fill=(160, 160, 160))
        low = report[name]["low_share"]
        for s, v in enumerate(low):
            d.rectangle([120 + s * PPS, y + ROW_H + 34 - int(v * 14), 120 + s * PPS + PPS - 2, y + ROW_H + 34],
                        fill=(230, 120, 60))
    sheet.save(out)
    json.dump(report, open(out_json, "w"), indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:])
