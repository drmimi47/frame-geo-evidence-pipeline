"""Render the tower cut: each chosen frame moved by a similarity transform so its tower stands on the same line.

    python -I render.py BASE_DIR [--fps 30] [--only-contact]

BASE_DIR is "research_notes/Tower cut opener". Reads marks.json (the marks, by eye, and the layout: every base on one
line, the height by size class) and gate*.json (each video's gate result and metadata); frames come from downloads/<id>/ (extracted once to frames/<key>.png at full
resolution). Pixels are only resampled (area when shrinking, bicubic otherwise) by a shift, a uniform scale and a
rotation; nothing is generated, filled or sharpened; where the moved frame doesn't reach, the canvas is black.
Hard cuts; a fade from black at the start only. Silent (no audio stream), H.264.
Writes tower_cut.mp4, tower_cut_contact.jpg and tower_cut.json.
"""
from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080


def target_height(i: int, n: int, layout) -> float:
    """The tower's height on the canvas for the i-th of n frames: grows gently from height_from to height_to over
    the sequence (smoothstep), so small poles stay small and the 750 kV towers fill the frame."""
    u = i / max(1, n - 1)
    u = u * u * (3 - 2 * u)
    return layout["height_from"] + (layout["height_to"] - layout["height_from"]) * u


def similarity(top, base, layout, tgt):
    """2x3 matrix taking the source's base->(axis_x, base_y) and top->(axis_x, base_y - tgt)."""
    (tx, ty), (bx, by) = top, base
    vx, vy = bx - tx, by - ty
    s = tgt / math.hypot(vx, vy)
    rot = math.atan2(tgt, 0) - math.atan2(vy, vx)  # radians, counter-clockwise in image coordinates
    c, n = s * math.cos(rot), s * math.sin(rot)
    a = np.array([[c, -n], [n, c]])
    t = np.array([layout["axis_x"], layout["base_y"] - tgt]) - a @ np.array([tx, ty])
    return np.hstack([a, t[:, None]]), s, math.degrees(rot)


def place(img: np.ndarray, m: np.ndarray, s: float, crop) -> np.ndarray:
    if crop:  # keep only this source rectangle (cuts a logo or a caption off); the rest of the frame is not used
        x0, y0, x1, y1 = crop
        keep = np.zeros_like(img)
        keep[y0:y1, x0:x1] = img[y0:y1, x0:x1]
        img = keep
    if s < 1:  # shrink with area averaging first, then only rotate and shift (bicubic)
        small = cv2.resize(img, (max(1, round(img.shape[1] * s)), max(1, round(img.shape[0] * s))), interpolation=cv2.INTER_AREA)
        sx, sy = small.shape[1] / img.shape[1], small.shape[0] / img.shape[0]
        m = m @ np.array([[1 / sx, 0, 0], [0, 1 / sy, 0], [0, 0, 1]])
        img = small
    return cv2.warpAffine(img, m, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))


def source_frame(base: Path, f: dict) -> Path:
    if f.get("file"):  # a still supplied as a file (supplied/), used as given
        return base / f["file"]
    out = base / "frames" / f"{f['key']}.png"
    if not out.exists():
        dl = base / "downloads" / f["video"]
        mp4 = dl / (dl / "done").read_text().strip()
        out.parent.mkdir(exist_ok=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{f['t']:.3f}", "-i", str(mp4), "-frames:v", "1", str(out)], check=True)
    return out


def main() -> None:
    base = Path(sys.argv[1])
    fps = int(sys.argv[sys.argv.index("--fps") + 1]) if "--fps" in sys.argv else 30
    marks = json.loads((base / "marks.json").read_text())
    layout, fade_s = marks["layout"], marks.get("fade_in_s", 2.0)
    frames = [f for f in marks["frames"] if not f.get("left_out")]
    canv, records = [], []
    gate = {}
    for name in ("gate.json", "gate2.json", "gate3.json", "gate4.json", "gate5.json"):  # the gate runs, merged
        if (base / name).exists():
            gate.update(json.loads((base / name).read_text()))
    for i, f in enumerate(frames):
        src = source_frame(base, f)
        img = cv2.imread(str(src), cv2.IMREAD_COLOR)
        tgt = layout["heights"][f["size_class"]] if "heights" in layout else target_height(i, len(frames), layout)
        m, s, rot = similarity(f["top"], f["base"], layout, tgt)
        canv.append(place(img, m, s, f.get("crop")))
        if f.get("file"):  # a supplied still: its provenance is in marks.json, the scope gate (YouTube) doesn't apply
            pv = f["provenance"]
            src_rec = {"file": f["file"], "file_sha256": hashlib.sha256(src.read_bytes()).hexdigest(), "provenance": pv,
                       "channel": None, "published": None, "licence": pv["rights"], "title": None,
                       "scope_gate": "not a YouTube video: the gate doesn't apply"}
        else:
            g = gate[f["video"]]
            src_rec = {"video": f["video"], "url": f"https://www.youtube.com/watch?v={f['video']}&t={int(f['t'])}s",
                       "t_s": f["t"], "channel": g["channel"], "published": g["published"], "licence": g["license"],
                       "title": g["title"], "scope_gate": g["reason"]}
        records.append({
            "key": f["key"], **src_rec,
            "line_class": f["class"], "size_class": f.get("size_class"), "class_how": f["class_how"],
            "marks": {"top": f["top"], "base": f["base"], "base_cut": f.get("base_cut", False), "top_cut": f.get("top_cut", False),
                      "note": "by eye, for alignment only; not evidence"},
            "transform": {"matrix": [[round(v, 6) for v in row] for row in m.tolist()], "scale": round(s, 4),
                          "rotation_deg": round(rot, 3), "target_height_px": round(tgt, 1), "source_size": [img.shape[1], img.shape[0]]},
            "crop": f.get("crop"), "hold_s": f["hold_s"], "why": f["why"],
            "source_frame_sha256": hashlib.sha256(img.tobytes()).hexdigest(),
            "capture_date": None, "capture_note": "unknown; the publication date is only an upper bound",
            "capture_hint": f.get("capture_hint"),
        })
    if "--only-contact" not in sys.argv:
        cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(fps),
               "-i", "-", "-an", "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p",
               "-movflags", "+faststart", str(base / "tower_cut.mp4")]
        enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        n_total, at = 0, 0.0
        for c, r in zip(canv, records):
            n = max(1, round(r["hold_s"] * fps))
            r["starts_s"] = round(n_total / fps, 3)
            for k in range(n):
                tt = (n_total + k) / fps
                if tt < fade_s:
                    a = tt / fade_s
                    a = a * a * (3 - 2 * a)
                    enc.stdin.write((c.astype(np.float32) * a).round().astype(np.uint8).tobytes())
                else:
                    enc.stdin.write(c.tobytes())
            n_total += n
        enc.stdin.close()
        enc.wait()
        print(f"{len(canv)} frames, {n_total / fps:.2f} s at {fps} fps")
    # contact strip: every frame as placed, in order
    tw, th, cols = 384, 216, 6
    rows = math.ceil(len(canv) / cols)
    sheet = Image.new("RGB", (cols * tw, rows * (th + 20)), "black")
    dr = ImageDraw.Draw(sheet)
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
    for i, (c, r) in enumerate(zip(canv, records)):
        im = Image.fromarray(cv2.cvtColor(c, cv2.COLOR_BGR2RGB)).resize((tw - 2, th - 2), Image.LANCZOS)
        x, y = (i % cols) * tw, (i // cols) * (th + 20)
        sheet.paste(im, (x + 1, y + 1))
        dr.text((x + 3, y + th + 2), f"{i + 1}  {r['key']}  {r['size_class'] or r['line_class']}  {r['hold_s']} s", fill="white", font=font)
    sheet.save(base / "tower_cut_contact.jpg", quality=88)
    out = {
        "title": "Tower cut opener (prototype)", "video": "tower_cut.mp4", "fps": fps, "size": [W, H], "audio": None,
        "duration_s": round(sum(max(1, round(r["hold_s"] * fps)) for r in records) / fps, 3),
        "fade_in_s": fade_s, "layout": layout, "alignment": marks["alignment"],
        "rules": marks["rules"], "frames": records,
    }
    (base / "tower_cut.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
