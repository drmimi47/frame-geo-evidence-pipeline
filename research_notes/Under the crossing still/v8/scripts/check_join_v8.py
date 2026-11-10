"""Check the cut from under-the-crossing (v5/under_the_crossing_f_day.mp4) into the drowning (v8: the plants dying),
from the project root with the project's venv (v7's check_join_v7.py, with v8's frames, and v8's frame 0 also
against v7's frame 0, which v8 must keep):

    python -I check_join_v8.py <v5_render_dir> <frames_dir> <v8 dir> <v7 frames dir>

- Its last frame against the drowning's first: v5's frame 899 recomposited from v5's passes (as its mp4 was made)
  and the mp4's last frame decoded, each against v8's frame 0; for scale, the step between v5's frames 898 and 899
  and between v8's frames 0 and 1 (a frame's flow dashes and birds move by that much).
- A join test: the last 3 s of under-the-crossing and the first 3 s of the drowning joined by FFmpeg
  (join_test.mp4, both of each pair: the cut as it stands, and the continuous pair in alt/), with the frames round the
  cut laid side by side (join_contact.png) and the sound's level each 50 ms round the cut.
Writes join_check.json in the v8 dir.
"""
import json
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "scripts")))
import composite_v5 as C5  # noqa: E402
C = C5.C
V5MP4 = "research_notes/Under the crossing still/v5/under_the_crossing_f_day.mp4"


def stats(a, b):
    d = np.abs(a.astype(int) - b.astype(int)).max(-1)
    return {"mean": round(float(d.mean()), 3), "max": int(d.max()), "px_over_8": int((d > 8).sum()),
            "px_over_32": int((d > 32).sum())}


def ff(*a):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *a], check=True)


def levels(path, t0, t1, step=0.05):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t0), "-t", str(t1 - t0), "-i", path, "-ac", "1",
                          "-ar", "48000", "-f", "f32le", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32)
    n = int(48000 * step)
    return [round(20 * math.log10(max(float(np.sqrt((x[i:i + n] ** 2).mean())), 1e-9)), 1)
            for i in range(0, len(x) - n + 1, n)]


def main(v5dir, fdir, v7, v7frames=None):
    tmp = os.path.join(v7, ".join_tmp")
    os.makedirs(tmp, exist_ok=True)
    ps = C.Passes(v5dir)
    f899 = C.to8(ps.frame(899), seed=899)
    f898 = C.to8(ps.frame(898), seed=898)
    ff("-sseof", "-0.1", "-i", V5MP4, "-update", "1", "-frames:v", "1", f"{tmp}/mp4_last.png")
    mp = np.asarray(Image.open(f"{tmp}/mp4_last.png").convert("RGB"))
    d0 = np.asarray(Image.open(f"{fdir}/f_0000.png").convert("RGB"))
    d1 = np.asarray(Image.open(f"{fdir}/f_0001.png").convert("RGB"))
    out = {"frames": {
        "v5_frame_899_vs_v8_frame_0": stats(f899, d0),
        "reference_v5_898_vs_899": stats(f898, f899),
        "reference_v8_0_vs_1": stats(d0, d1),
        "mp4_last_frame_vs_v8_frame_0": stats(mp, d0),
        "mp4_last_frame_vs_v5_frame_899_png": stats(mp, f899),
        **({"v8_frame_0_vs_v7_frame_0": stats(d0, np.asarray(Image.open(f"{v7frames}/f_0000.png").convert("RGB"))),
            "v8_frame_24_vs_v7_frame_24 (the last before any plant changes)":
                stats(np.asarray(Image.open(f"{fdir}/f_0024.png").convert("RGB")),
                      np.asarray(Image.open(f"{v7frames}/f_0024.png").convert("RGB")))} if v7frames else {}),
        "note": "v5's frame 899 and v8's frame 0 differ by one frame's motion (the flow dashes, a far bird), as "
                "neighbouring frames do; the mp4 differs from the PNGs by its encoding"}}
    Image.fromarray(np.clip(np.abs(f899.astype(int) - d0.astype(int)).max(-1) * 8, 0, 255).astype(np.uint8)).save(
        os.path.join(v7, "join_diff_899_to_0.png"))
    joins = {}
    for name, a, b in (("as_it_stands", V5MP4, os.path.join(v7, "drowning.mp4")),
                       ("continuous", os.path.join(v7, "..", "v7", "alt", "under_the_crossing_f_day_continuous.mp4"),
                        os.path.join(v7, "alt", "drowning_continuous.mp4"))):
        if not (os.path.exists(a) and os.path.exists(b)):
            continue
        o = os.path.join(v7, "join_test.mp4" if name == "as_it_stands" else os.path.join("alt", "join_test_continuous.mp4"))
        ff("-ss", "27", "-i", a, "-t", "3", "-i", b, "-filter_complex",
           "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]", "-map", "[v]", "-map", "[a]", "-c:v", "libx264",
           "-crf", "16", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", o)
        joins[name] = {"file": os.path.relpath(o, v7), "levels_dbfs_every_50ms_2_5_to_3_5_s": levels(o, 2.5, 3.5)}
        if name == "as_it_stands":
            # frames round the cut (the cut at 3.0 s = frame 90): 87..92
            ff("-i", o, "-vf", "select='between(n\\,87\\,92)',scale=640:-1,tile=3x2", "-frames:v", "1",
               "-fps_mode", "passthrough", os.path.join(v7, "join_contact.png"))
    out["joins"] = joins
    json.dump(out, open(os.path.join(v7, "join_check.json"), "w"), indent=1)
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:5])
