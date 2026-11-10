"""Section block pass 2: one continuous clip, the block (block2.py's frames) handing over to the section (gfilm2.py) at
its first frame, with the type: the date, at most one short line, the heights note, the imagery's credit while the
imagery shows. Pixels only placed, mixed or faded; nothing generated. Not the film.
python compose2.py PROTO LINE SCALE BLOCK_DIR GF_DIR XF_DIR OUT.mp4 [--proto-s S PROTO_OUT.mp4] [--sheet SHEET.jpg]
PROTO A (two cameras, split at the break) | B (the dike's slice swung beside the crossing's); SCALE ease | x3."""
import json, math, subprocess, sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
import cuts as K  # noqa: E402
import gfilm2 as G  # noqa: E402

PROTO, LINE, SCALE, BD, GF, XF, OUT = sys.argv[1:8]
BD, OUT = Path(BD), Path(OUT)
opt = lambda k: sys.argv[sys.argv.index(k) + 1:sys.argv.index(k) + 3] if k in sys.argv else None
FPS, W, H = 30, 1920, 1080
TL = K.TA if PROTO == "A" else K.T
T_BLOCK = TL["cam"][1] + 0.1           # the camera is square and still from here: the hand-over
NB = int(round(T_BLOCK * FPS))                 # the block's last frame is the section's first
sec = G.Section(LINE, SCALE, GF, XF); P, T_SEC = G.plan(SCALE)
TOTAL = T_BLOCK + T_SEC
NAME = ["DNIPROVSKA", "FEROSPLAVNA"][int(LINE)]
KM = K.layout(LINE)["jog_km"]
ST = json.loads((Path(XF) / "states.json").read_text())["A"]
LINES = [((TL["c1"][0], TL["drop"][0] + 0.8), f"THE CUT: THE POND'S NORTH DIKE, THEN {NAME}'S CROSSING"),
         ((TL["swing"][0], TL["swing"][1] + 0.8), f"THE TWO CUTS LAID SIDE BY SIDE, ≈ {KM:.1f} KM LEFT OUT")
         if PROTO == "B" else
         ((TL["cam"][0] + 0.3, TL["cam"][1] - 1.0), f"EACH CUT SEEN SQUARE ON, ≈ {KM:.1f} KM LEFT OUT BETWEEN")]


def load(p):
    im = Image.open(p).convert("RGB")
    return im if im.size == (W, H) else im.resize((W, H), Image.LANCZOS)   # test renders at a lower size


def _seam(i):
    p = BD / f"f_{i:04d}.json"
    if not p.exists():
        return None
    info = json.loads(p.read_text())
    if len(info["cams"]) != 2:
        return None
    e0, e1 = info["cams"][0]["ext"]["S1"], info["cams"][1]["ext"]["S2"]
    return (e0[1] + e1[0]) / 2


SEAMS = {i: _seam(i) for i in range(NB + 3)}


def block_pic(i):
    a = load(BD / f"f_{i:04d}_0.png")
    seam = SEAMS[i]
    if seam is not None:   # A: the dike's camera left of the seam, the crossing's right of it
        b = load(BD / f"f_{i:04d}_1.png")
        # the median of the five frames round it: a run's first frame measured its seam stale (frames 217 and 255 jumped
        # about 100 px right, the user, 8 November 2026); each camera was rendered 19 px past its own seam, so the
        # smoothed one is held within that
        near = [SEAMS[j] for j in range(i - 2, i + 3) if SEAMS.get(j) is not None]
        seam = min(max(float(np.median(near)), seam - 18), seam + 18)
        x = int(round(seam)); a.paste(b.crop((x, 0, W, H)), (x, 0))
    return a, seam


def frame(f):
    t = f / FPS
    if f < NB:
        st = K.block_state(PROTO, LINE, t)
        img, seam = block_pic(f)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
        # A: no line drawn at the seam between the two views (the user, 8 November 2026: "without the vertical white line")
        vis = max(st["rest_a"], st["tops_a"] * (1 if t > TL["faces"] else 0), 1.0 if t < TL["drop"][0] else 0)
        d.text((60, 1046), f"{ST['imagery']} · CONTAINS MODIFIED COPERNICUS SENTINEL-2 DATA", font=G.F_TINY,
               fill=(200, 200, 200, int(140 * vis)))
        img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
        line = None; la = 0.0
        for (t0, t1), txt in LINES:
            if t0 <= t < t1:
                line, la = txt, min(K.ramp(t, t0, t0 + 0.5), 1 - K.ramp(t, t1 - 0.5, t1))
        img = G.texts(img, G.DATE["A"], None, G.NOTE["x3"], alpha=K.ramp(t, 0.2, 0.9))
        if line:
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); G.boxed(ImageDraw.Draw(ov), (60, 104), line, G.F_LINE, la)
            img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
        a = np.asarray(img, np.float32) * K.ramp(t, 0.0, 0.8)
        return a.astype(np.uint8)
    ts = t - T_BLOCK
    fade = min(1.0, max(0.0, (T_SEC - ts) / 1.2))
    return np.asarray(G.typed(sec, ts, P, T_SEC, fade))


if "--sheet" in sys.argv:
    sh = sys.argv[sys.argv.index("--sheet") + 1]
    ts = [0.5, TL["c1"][1], TL["c2"][1], TL["drop"][1] - 0.5, (TL["cam"][0] + TL["cam"][1]) / 2 - 1.0,
          (TL["cam"][0] + TL["cam"][1]) / 2 + 1.0, TL["cam"][1] - 0.9, T_BLOCK - 1 / FPS, T_BLOCK + 0.1]
    if SCALE == "ease":
        ts.append(T_BLOCK + 0.6 + G.EASE_S / 2)
    ts += [T_BLOCK + [b for k, a, b in P if k == "in"][0] + 1.0, T_BLOCK + [a for k, a, b in P if k == "C"][0] + 2]
    ts = ts[:12]
    tiles = [Image.fromarray(frame(int(round(x * FPS)))).resize((W // 3, H // 3)) for x in ts]
    img = Image.new("RGB", (W, H * len(tiles) // 9 + (H // 3 if len(tiles) % 3 else 0)))
    dr = ImageDraw.Draw(img)
    for k, (x, im) in enumerate(zip(ts, tiles)):
        px, py = (k % 3) * W // 3, (k // 3) * H // 3; img.paste(im, (px, py))
        dr.text((px + 6, py + H // 3 - 18), f"{x:.2f} s", font=G.F_TINY, fill=(255, 220, 0))
    img.save(sh, quality=90); print("sheet", sh, [round(x, 2) for x in ts])
else:
    ff = G.ffmpeg(OUT)
    n = int(round(TOTAL * FPS))
    for f in range(n):
        ff.stdin.write(frame(f).tobytes())
    ff.stdin.close(); ff.wait()
    print("wrote", OUT, f"{TOTAL:.2f} s ({n} frames; the block {T_BLOCK} s, the hand-over at frame {NB})")
    po = opt("--proto-s")
    if po:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(OUT), "-t", po[0], "-c:v", "libx264", "-crf", "16",
                        "-preset", "slow", "-pix_fmt", "yuv420p", "-movflags", "+faststart", po[1]], check=True)
        print("wrote", po[1], po[0], "s")
