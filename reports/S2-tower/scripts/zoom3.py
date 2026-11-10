"""The tower to scale, third pass (the user, 9 November 2026: longer, about 30 s, "this one feels rushed"; the person's,
the crossarm's, the levels' and the base's captions gone; then the line it belongs to named under it, the line's other
towers in the old reservoir appearing behind it in line, nearly overlapping, the farther ones fainter, and the stack
moving left as the other line's towers appear beside it, already flat).

zoom2.py's move, unchanged in shape, drawn out (its keys' times stretched: the hold on the person 1.8 s, the pull-back
11.2 s), rendered by tower3.py (tower.py's crane view). From the end of the move the picture is laid out in 2D from
sprites: each type rendered once from the last frame's camera, film transparent (at 20 km and a 2.4 m lens the view
is flat to under a pixel, so a sprite shifted sideways is the same tower further along). The hero sprite over black is
the last frame of the move itself, so the hand-over doesn't show.

The towers in the reservoir (towers.py `assign`: the crossing scheme's inner towers, less the two shore towers; the
same towers the survey finds in the water of 5 June 2023): Dniprovska К-П-П-А-П-П-К, three of the five on caissons:
a 126 m suspension tower, the 100 m anchor, a 126 m suspension tower, south to north. Ferosplavna 1, 2 (one row of
towers for both circuits) К-А-А-А-А-А-А-А-К, five of the seven on caissons, double-circuit anchors of 90 and 100 m
(which is which isn't published: all drawn at no. 19's 100 m, as the 3D film). Seen along each line from the south,
the nearest in front; spread sideways to be seen (a drawing: in line they would hide each other). The shapes are
representative of each type (towers.py); the bases (12.8 m under the old water, no. 19's) and the bed (inferred, at
the 750 kV caissons) drawn at one level for all.

python zoom3.py OUT_DIR [--fps 30] [--skip-render] [--skip-sprites] [--stills 0,5,13,...]
"""
import argparse, json, math, subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import zoom2 as Z
from zoom import OUTLINE, ease
from image_evidence.satellite import zoomout as z

ROOT = Path(__file__).resolve().parents[3]
C3D = ROOT / "libraries/conductive-seam/satellite/networks/znpp/scenes/crossing3d"
W_PX, H_PX, SS = 1920, 1080, 2
INK, DIM = Z.INK, Z.DIM


def stretch(t):
    """zoom2's time to this pass's: the first hold 0.7 -> 1.8 s, the move twice as long."""
    return t if t <= 0 else 1.8 * t / 0.7 if t < 0.7 else 1.8 + (t - 0.7) * 2.0


Z.KEYS = [(stretch(k[0]), *k[1:]) for k in Z.KEYS]
Z.FEET_Y = [(stretch(a), y) for a, y in Z.FEET_Y]
Z.AIM_S = tuple(stretch(a) for a in Z.AIM_S)
Z._EX, Z._ED, Z._EZ, Z._LENS = (Z._chan([k[1] for k in Z.KEYS]), Z._chan([k[2] for k in Z.KEYS], True),
                                Z._chan([k[3] for k in Z.KEYS]), Z._chan([k[4] for k in Z.KEYS], True))
T_MOVE = Z.KEYS[-1][0]                       # 13.0 s
PX_M = W_PX / Z.W_END                        # 6.4 px a metre on the towers' plane at the end

# the timeline (s)
T_DIMS = (13.4, 15.6, 16.1)                  # 126 M and 41 M ACROSS in; 41 M out before the caption takes its place
T_TITLE = (13.9, 21.0)                       # the first title in, out before the stack moves into its place
T_CAP = 16.4                                 # the line named under the tower
T_BEHIND = [(18.6, 20.0), (19.5, 20.9)]      # the two towers behind slide out from behind it
T_SUB2 = 20.4                                # the caption's second line becomes the count
T_SHIFT = (22.4, 25.4)                       # the stack moves left
T_FERO = 23.2                                # the other line's towers come in from the right, a little apart
T_FERO_STEP, T_FERO_DUR = 0.14, 2.3
T_CAP2 = 25.8                                # its caption
T_NOTE = 26.6                                # the note on what is drawn
T_END = 31.0

# the layout at the end (px, integers so the held frames are crisp): Dniprovska's group, a gap, Ferosplavna's
STEP_750, STEP_330 = 77, 64                  # 12 m and 10 m sideways each tower further back
OPA_750 = [1.0, 0.62, 0.42]                  # the farther ones fainter
OPA_330 = [1.0, 0.74, 0.57, 0.45, 0.35]
W750, W330 = round(41.0 * PX_M), round(44.6 * PX_M)   # the caissons' width (the widest part)
G750, G330, GAP = W750 + 2 * STEP_750, W330 + 4 * STEP_330, 256
LEFT = (W_PX - (G750 + GAP + G330)) // 2
X750 = LEFT + W750 // 2                      # the hero's centre at the end
X330 = LEFT + G750 + GAP + W330 // 2         # Ferosplavna's front tower
SHIFT = X750 - W_PX // 2                     # -476 px
FERO_IN = 420                                # px: where they come in from, right of their places

SPRITES = {"p750": {"tower": "crossing750_p", "caisson": "caisson750", "person": True},
           "a750": {"tower": "crossing750_a", "caisson": "caisson750", "person": False},
           "x330": {"tower": "crossing330", "caisson": "caisson330", "person": False}}
DNIPRO = ["p750", "a750", "p750"]           # south to north, the nearest first
FERO = ["x330"] * 5

CAP = {"d_name": "DNIPROVSKA · 750 KV",
       "d_one": "ONE OF ITS THREE TOWERS IN THE OLD RESERVOIR",
       "d_all": "ITS THREE TOWERS IN THE OLD RESERVOIR: 126, 100 AND 126 M",
       "f_name": "FEROSPLAVNA 1 AND 2 · 330 KV",
       "f_all": "ITS FIVE TOWERS IN THE OLD RESERVOIR: 90-100 M, ALL DRAWN AT 100 M"}
NOTE = ["SEEN ALONG EACH LINE FROM THE SOUTH, THE NEAREST IN FRONT, SPREAD SIDEWAYS TO BE SEEN. TO SCALE.",
        "REPRESENTATIVE MODELS OF EACH TYPE; THE BASES AND THE BED DRAWN AT ONE LEVEL; THE PERSON DRAWN."]


def mix(a, b, u):
    return a + (b - a) * u


def ramp(t, a, d=0.7):
    return ease((t - a) / d)


def P(x, zz, y=0.0):
    """The flat drawing: x m from the hero's axis, zz m up from the caissons' base, to supersampled px (the last
    frame's camera; x shifted by the stack's move is added in px by the caller)."""
    return tuple(c * SS for c in Z.project((x, y, zz), Z.camera(T_MOVE)))


def boxed(dr, xy, text, font, a, anchor="ma", fill=INK):
    l, tp, r, bt = dr.textbbox(xy, text, font=font, anchor=anchor)
    dr.rectangle([l - 6 * SS, tp - 4 * SS, r + 6 * SS, bt + 4 * SS], fill=(0, 0, 0, int(170 * a)))
    dr.text(xy, text, font=font, fill=(*fill, int(255 * a)), anchor=anchor)


def overlay(cam, t, shift_px):
    """The drawing's marks over the picture: the ground cut open, the hero's dimensions, the captions, the titles."""
    im = Image.new("RGBA", (W_PX * SS, H_PX * SS), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
    Pm = (lambda x, zz, y=0.0: tuple(c * SS for c in Z.project((x, y, zz), cam))) if t < T_MOVE else P
    font = lambda size: z._hn(size * SS, 0)
    FS, FC, MED = font(14), font(20), font(30)
    col = lambda rgb, a: (*rgb, int(255 * a))
    fl = Z.flatness(min(t, T_MOVE))
    a_cut = ease((fl - 0.2) / 0.5)
    if a_cut > 0:   # the ground cut open: dark earth under the bed, hatched (zoom2's)
        _, yb = Pm(0, Z.BED)
        earth = Image.new("RGBA", im.size, (0, 0, 0, 0)); de = ImageDraw.Draw(earth)
        de.rectangle([0, yb, im.size[0], im.size[1]], fill=(8, 8, 9, int(150 * a_cut)))
        step = 14 * SS
        for x0 in range(-im.size[1], im.size[0], step):
            de.line([(x0, im.size[1]), (x0 + (im.size[1] - yb), yb)], fill=(70, 70, 72, int(110 * a_cut)), width=1)
        im = Image.alpha_composite(im, earth); dr = ImageDraw.Draw(im)
    if t < T_MOVE:
        return im.resize((W_PX, H_PX), Image.LANCZOS)
    sx = shift_px * SS
    # the hero's height, on its right, moving with it; out as the stack moves
    a126 = ramp(t, T_DIMS[0], 0.6) * (1 - ramp(t, T_SHIFT[0] - 0.2, 0.6))
    if a126 > 0:
        (xa, ya), (_, yb) = P(48, Z.LEGS), P(48, Z.TOP)
        xa += sx
        dr.line([(xa, ya), (xa, yb)], fill=col(INK, a126), width=SS)
        for yy in (ya, yb):
            dr.line([(xa - 6 * SS, yy), (xa + 6 * SS, yy)], fill=col(INK, a126), width=SS)
        dr.text((xa + 12 * SS, (ya + yb) / 2), "126 M", font=FS, fill=col(INK, a126), anchor="lm")
    a41 = ramp(t, T_DIMS[0], 0.6) * (1 - ramp(t, T_DIMS[1], T_DIMS[2] - T_DIMS[1]))
    if a41 > 0:
        (xa, y), (xb, _) = P(-20.5, -3), P(20.5, -3)
        dr.line([(xa, y), (xb, y)], fill=col(INK, a41), width=SS)
        dr.text(((xa + xb) / 2, y + 8 * SS), "41 M ACROSS", font=FS, fill=col(INK, a41), anchor="ma")
    # the captions under the base: the name, then a line under it (crossfading from "one of" to the count)
    _, ybase = P(0, 0)
    y1, y2 = ybase + 14 * SS, ybase + 44 * SS
    behind_u = ease((t - T_BEHIND[0][0]) / (T_BEHIND[-1][1] - T_BEHIND[0][0]))
    cx_d = (W_PX // 2 + mix(0, (G750 - W750) / 2, behind_u)) * SS + sx      # under the hero, then under the group
    a_cap = ramp(t, T_CAP)
    if a_cap > 0:
        boxed(dr, (cx_d, y1), CAP["d_name"], FC, a_cap)
        u2 = ramp(t, T_SUB2, 0.6)
        if u2 < 1:
            boxed(dr, (cx_d, y2), CAP["d_one"], FS, a_cap * (1 - u2), fill=DIM)
        if u2 > 0:
            boxed(dr, (cx_d, y2), CAP["d_all"], FS, a_cap * u2, fill=DIM)
    a_cap2 = ramp(t, T_CAP2)
    if a_cap2 > 0:
        cx_f = (X330 + 2 * STEP_330) * SS
        boxed(dr, (cx_f, y1), CAP["f_name"], FC, a_cap2)
        boxed(dr, (cx_f, y2), CAP["f_all"], FS, a_cap2, fill=DIM)
    a_title = ramp(t, T_TITLE[0]) * (1 - ramp(t, T_TITLE[1], 0.6))
    if a_title > 0:
        for i, line in enumerate(["THE 750 KV CROSSING TOWER", "OVER THE DNIPRO"]):
            dr.text((120 * SS, (140 + i * 30 * 1.35) * SS), line, font=MED, fill=col(INK, a_title))
        dr.text((120 * SS, 245 * SS), "A REPRESENTATIVE MODEL OF THE TYPE, DRAWN FROM PHOTOGRAPHS AND", font=FS,
                fill=col(DIM, a_title))
        dr.text((120 * SS, 268 * SS), "PUBLISHED HEIGHTS; THE PERSON DRAWN.", font=FS, fill=col(DIM, a_title))
    a_note = ramp(t, T_NOTE, 0.8)
    if a_note > 0:
        for i, line in enumerate(NOTE):
            dr.text(((W_PX - 120) * SS, (64 + i * 22) * SS), line, font=FS, fill=col(DIM, a_note), anchor="ra")
    return im.resize((W_PX, H_PX), Image.LANCZOS)


def _whole(spr, k):
    out = np.zeros_like(spr)
    if k >= 0:
        out[:, k:] = spr[:, :W_PX - k] if k else spr
    else:
        out[:, :W_PX + k] = spr[:, -k:]
    return out


def shifted(spr, dx):
    """A premultiplied float RGBA sprite moved dx px sideways (whole pixels exact; a fraction linear between two)."""
    k = math.floor(dx); f = dx - k
    if f < 1e-3:
        return _whole(spr, k)
    return _whole(spr, k) * (1 - f) + _whole(spr, k + 1) * f


def layout(t):
    """Each sprite at time t: (name, x shift px from the centre, opacity), back to front."""
    sh = SHIFT * ease((t - T_SHIFT[0]) / (T_SHIFT[1] - T_SHIFT[0]))
    out = []
    for i in range(len(FERO) - 1, -1, -1):
        u = ease((t - (T_FERO + i * T_FERO_STEP)) / T_FERO_DUR)
        if u > 0:
            x = X330 - W_PX // 2 + i * STEP_330 + FERO_IN * (1 - u)
            out.append((FERO[i], x, OPA_330[i] * u))
    for i in range(len(DNIPRO) - 1, 0, -1):
        a, b = T_BEHIND[i - 1]
        u = ease((t - a) / (b - a))
        if u > 0:
            out.append((DNIPRO[i], sh + i * STEP_750 * u, OPA_750[i] * min(1.0, u * 1.6)))
    out.append((DNIPRO[0], sh, 1.0))
    return out, sh


def compose(sprites, t):
    acc = np.zeros((H_PX, W_PX, 3), np.float32)
    items, sh = layout(t)
    for name, dx, op in items:
        s = shifted(sprites[name], dx)
        acc = acc * (1 - s[..., 3:4] * op) + s[..., :3] * op
    return Image.fromarray(np.clip(acc * 255 + 0.5, 0, 255).astype(np.uint8)).convert("RGBA"), sh


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("out"); ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--skip-render", action="store_true"); ap.add_argument("--skip-sprites", action="store_true")
    ap.add_argument("--stills")
    a = ap.parse_args(); out = Path(a.out)
    ts = [float(x) for x in a.stills.split(",")] if a.stills else [f / a.fps for f in range(round(T_END * a.fps))]
    raw, spr_dir = out / "crane3_raw", out / "sprites3"
    fr = out / ("stills3_frames" if a.stills else "crane3_frames")
    for d in (raw, spr_dir, fr):
        d.mkdir(parents=True, exist_ok=True)
    tower3 = str(Path(__file__).with_name("tower3.py"))
    run = lambda cj, dst: subprocess.run(["blender", "-b", "--factory-startup", "-P", tower3, "--",
                                          str(C3D / "towers.npz"), str(C3D / "scene.json"), "crane", str(dst), str(cj)],
                                         check=True, stdout=subprocess.DEVNULL)
    # the move: every frame to its end (the stills: just those asked for)
    mts = sorted({min(t, T_MOVE) for t in ts if t < T_MOVE}) if a.stills else \
        [f / a.fps for f in range(round(T_MOVE * a.fps))]
    cams = {mt: Z.camera(mt) for mt in mts}
    if not a.skip_render and mts:
        cj = out / "crane3_cams.json"
        cj.write_text(json.dumps({"frames": [[*map(float, e), *map(float, g), float(l), 1 - Z.flatness(mt)]
                                              for mt in mts for e, g, l in [cams[mt]]],
                                  "figure": {"outline": OUTLINE, "at": Z.FIG}, "bed": Z.BED}))
        run(cj, raw)
    if not a.skip_sprites:
        e, g, l = Z.camera(T_MOVE)
        for name, spec in SPRITES.items():
            cj = out / f"sprite3_{name}.json"
            cj.write_text(json.dumps({"frames": [[*map(float, e), *map(float, g), float(l), 0.0]], "transparent": True,
                                      "figure": {"outline": OUTLINE, "at": Z.FIG}, "bed": Z.BED, **spec}))
            d = spr_dir / name; d.mkdir(exist_ok=True)
            run(cj, d)
    sprites = {}
    for n in SPRITES:   # Blender's PNG keeps straight alpha: premultiplied here, so shifts and fades mix cleanly
        s = np.asarray(Image.open(spr_dir / n / "f_0001.png").convert("RGBA")).astype(np.float32) / 255.0
        sprites[n] = np.concatenate([s[..., :3] * s[..., 3:4], s[..., 3:4]], -1)
    idx = {mt: i for i, mt in enumerate(mts)}
    for i, t in enumerate(ts):
        if t < T_MOVE:
            base = Image.open(raw / f"f_{idx[min(t, T_MOVE)] + 1:04d}.png").convert("RGBA"); cam = cams[min(t, T_MOVE)]
            sh = 0.0
        else:
            base, sh = compose(sprites, t); cam = None
        frame = Image.alpha_composite(base, overlay(cam, t, sh)).convert("RGB")
        fade = ease(t / 0.8)
        if fade < 1:
            frame = Image.eval(frame, lambda v, f=fade: int(v * f))
        frame.save(fr / f"f_{i:04d}.png")
    if a.stills:
        tiles = [Image.open(fr / f"f_{i:04d}.png").resize((640, 360)) for i in range(len(ts))]
        sheet = Image.new("RGB", (1920, 360 * math.ceil(len(tiles) / 3)))
        dr = ImageDraw.Draw(sheet)
        for i, (t, im) in enumerate(zip(ts, tiles)):
            sheet.paste(im, ((i % 3) * 640, (i // 3) * 360))
            dr.text(((i % 3) * 640 + 8, (i // 3) * 360 + 8), f"{t:.1f} s", fill=(255, 220, 0))
        sheet.save(out / "stills3_sheet.png"); print("sheet", out / "stills3_sheet.png")
        return
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(a.fps), "-i", str(fr / "f_%04d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", "-movflags", "+faststart",
                    str(out / "S2_elevation_zoom3.mp4")], check=True)
    Image.open(fr / f"f_{len(ts) - 1:04d}.png").save(out / "S2_elevation_zoom3_last.png")
    print("wrote", out / "S2_elevation_zoom3.mp4", f"{len(ts) / a.fps:.2f} s")


if __name__ == "__main__":
    main()
