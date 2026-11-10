"""The tower to scale, third pass with the user's fixes (9 November 2026: "remove the top right text ... replace the
text under the titles of each line so it just has the count of towers in each ... show the width and the hight lines
for both powerline groups once all of them are shown ... dont show the height x width of the tower at around 14
seconds anymore ... remove the top left text"). zoom3.py's picture unchanged: its renders (the move's frames and the
three sprites) are reused as they are; only the drawn marks and the type change:
- no 126 M / 41 M ACROSS at the end of the move, no title top left, no note top right (what they said is in the
  JSON's "to be said elsewhere");
- each caption's second line is the count: "3 TOWERS OVER WATER", "5 TOWERS OVER WATER";
- once both groups are in place, each group's height (the front tower's, from the caisson's top to the tower's top)
  and width (its front caisson across at the base, the widest part) drawn in zoom2's dimension style. To make room
  for the width under the bases, the whole picture rises 46 px while the stack moves left, and the captions step down
  under the widths;
- the hold on the end a second longer (32 s) to read the dimensions.

python zoom3b.py SCRATCH_DIR ZOOM3_DIR OUT_DIR [--fps 30] [--stills 0,13,16.4,...]
  ZOOM3_DIR: zoom3.py's scratch (crane3_raw/, sprites3/); OUT_DIR: where the video, last frame and sheet go
"""
import argparse, math, subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import zoom3 as Z3
import zoom2 as Z
from zoom import ease
from image_evidence.satellite import zoomout as z

W_PX, H_PX, SS = Z3.W_PX, Z3.H_PX, Z3.SS
INK, DIM = Z3.INK, Z3.DIM
T_MOVE, T_SHIFT = Z3.T_MOVE, Z3.T_SHIFT
T_DIMS = (26.8, 0.8)                         # both groups' dimensions in, once Ferosplavna is named (25.8)
T_END = 32.0
DY = 46                                      # px the picture rises while the stack moves left (whole px at rest)
CAP = {"d_name": "DNIPROVSKA · 750 KV", "d_count": "3 TOWERS OVER WATER",
       "f_name": "FEROSPLAVNA 1 AND 2 · 330 KV", "f_count": "5 TOWERS OVER WATER"}
# the dimensions: heights the towers' (towers.py, the published 126 m; the 330 kV drawn at 100 m), widths the
# caissons' at the base as published (ssp_63206: 750 kV caisson 40 m across; ssp_94005: 330 kV caisson 43.6 m across at
# its base); the lines span the caissons as drawn (their ribs stand about 0.5 m proud of the drum)
DIMS = {"750": {"height": "126 M", "width": "40 M ACROSS", "h_m": 126.0},
        "330": {"height": "100 M", "width": "43.6 M ACROSS", "h_m": 100.0}}
HALF_750, HALF_330 = 131.5, 142.5            # px: the front caissons' half-widths at the base, measured on the sprites


def lift(t):
    return DY * ease((t - T_SHIFT[0]) / (T_SHIFT[1] - T_SHIFT[0]))


def vshift(img, dy):
    """An RGBA image moved dy px up (whole px exact; a fraction linear between two), black below."""
    a = np.asarray(img).astype(np.float32)
    k = math.floor(dy); f = dy - k

    def up(n):
        out = np.zeros_like(a); out[..., 3] = 255
        out[:H_PX - n] = a[n:] if n else a
        return out
    b = up(k) if f < 1e-3 else up(k) * (1 - f) + up(k + 1) * f
    return Image.fromarray(np.clip(b + 0.5, 0, 255).astype(np.uint8), "RGBA")


def overlay(t, shift_px, dy):
    """The marks after the move: the ground cut open, the captions, and at the end the groups' dimensions."""
    im = Image.new("RGBA", (W_PX * SS, H_PX * SS), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
    font = lambda size: z._hn(size * SS, 0)
    FS, FC = font(14), font(20)
    col = lambda rgb, a: (*rgb, int(255 * a))
    P = lambda x, zz: (Z3.P(x, zz)[0], Z3.P(x, zz)[1] - dy * SS)
    _, yb = P(0, Z.BED)                       # the ground cut open: zoom2's dark earth, hatched (flat from here)
    earth = Image.new("RGBA", im.size, (0, 0, 0, 0)); de = ImageDraw.Draw(earth)
    de.rectangle([0, yb, im.size[0], im.size[1]], fill=(8, 8, 9, 150))
    for x0 in range(-im.size[1], im.size[0], 14 * SS):
        de.line([(x0, im.size[1]), (x0 + (im.size[1] - yb), yb)], fill=(70, 70, 72, 110), width=1)
    im = Image.alpha_composite(im, earth); dr = ImageDraw.Draw(im)
    sx = shift_px * SS
    u = dy / DY                               # the captions step down under the widths as the picture rises
    _, ybase = P(0, 0)
    y1, y2 = ybase + (14 + 34 * u) * SS, ybase + (44 + 34 * u) * SS
    behind_u = ease((t - Z3.T_BEHIND[0][0]) / (Z3.T_BEHIND[-1][1] - Z3.T_BEHIND[0][0]))
    cx_d = (W_PX // 2 + Z3.mix(0, (Z3.G750 - Z3.W750) / 2, behind_u)) * SS + sx
    a_cap = Z3.ramp(t, Z3.T_CAP)
    if a_cap > 0:
        Z3.boxed(dr, (cx_d, y1), CAP["d_name"], FC, a_cap)
        a2 = a_cap * Z3.ramp(t, Z3.T_SUB2, 0.6)
        if a2 > 0:
            Z3.boxed(dr, (cx_d, y2), CAP["d_count"], FS, a2, fill=DIM)
    a_cap2 = Z3.ramp(t, Z3.T_CAP2)
    if a_cap2 > 0:
        cx_f = (Z3.X330 + 2 * Z3.STEP_330) * SS
        Z3.boxed(dr, (cx_f, y1), CAP["f_name"], FC, a_cap2)
        Z3.boxed(dr, (cx_f, y2), CAP["f_count"], FS, a_cap2, fill=DIM)
    a = Z3.ramp(t, *T_DIMS)
    if a > 0:
        tick = 6 * SS
        _, y_legs = P(0, Z.LEGS)
        yw = ybase + 12 * SS
        for kv, cx, half, side in (("750", Z3.X750, HALF_750, -1), ("330", Z3.X330, HALF_330, 1)):
            d = DIMS[kv]
            _, y_top = P(0, Z.LEGS + d["h_m"])
            # the height beside the group: left of Dniprovska's front tower, right of Ferosplavna's farthest
            edge = cx - half if side < 0 else cx + 4 * Z3.STEP_330 + half
            xh = (edge + side * 26) * SS
            dr.line([(xh, y_legs), (xh, y_top)], fill=col(INK, a), width=SS)
            for yy in (y_legs, y_top):
                dr.line([(xh - tick, yy), (xh + tick, yy)], fill=col(INK, a), width=SS)
            dr.text((xh + side * 12 * SS, (y_legs + y_top) / 2), d["height"], font=FS, fill=col(INK, a),
                    anchor="rm" if side < 0 else "lm")
            # the width under the front caisson's base
            xa, xb = (cx - half) * SS, (cx + half) * SS
            dr.line([(xa, yw), (xb, yw)], fill=col(INK, a), width=SS)
            for xx in (xa, xb):
                dr.line([(xx, yw - tick), (xx, yw + tick)], fill=col(INK, a), width=SS)
            dr.text((cx * SS, yw + 8 * SS), d["width"], font=FS, fill=col(INK, a), anchor="ma")
    return im.resize((W_PX, H_PX), Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("scratch"); ap.add_argument("zoom3"); ap.add_argument("out")
    ap.add_argument("--fps", type=int, default=30); ap.add_argument("--stills")
    a = ap.parse_args(); sc, z3, out = Path(a.scratch), Path(a.zoom3), Path(a.out)
    ts = [float(x) for x in a.stills.split(",")] if a.stills else [f / a.fps for f in range(round(T_END * a.fps))]
    fr = sc / ("stills" if a.stills else "frames"); fr.mkdir(parents=True, exist_ok=True)
    raw = z3 / "crane3_raw"
    n_raw = len(list(raw.glob("f_*.png")))
    if n_raw != round(T_MOVE * 30):
        raise SystemExit(f"zoom3's move: {n_raw} frames, expected {round(T_MOVE * 30)} (rendered at 30 fps)")
    sprites = {}
    for n in Z3.SPRITES:
        s = np.asarray(Image.open(z3 / "sprites3" / n / "f_0001.png").convert("RGBA")).astype(np.float32) / 255.0
        sprites[n] = np.concatenate([s[..., :3] * s[..., 3:4], s[..., 3:4]], -1)
    for i, t in enumerate(ts):
        if t < T_MOVE:   # the move: zoom3's own frames and overlay (only the ground cut drawn there)
            k = min(int(round(t * 30)), n_raw - 1)
            base = Image.open(raw / f"f_{k + 1:04d}.png").convert("RGBA")
            frame = Image.alpha_composite(base, Z3.overlay(Z.camera(k / 30), t, 0.0))
        else:
            base, sh = Z3.compose(sprites, t)
            dy = lift(t)
            frame = Image.alpha_composite(vshift(base, dy), overlay(t, sh, dy))
        frame = frame.convert("RGB")
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
        sheet.save(out / "S2_elevation_zoom3b_sheet.png"); print("sheet", out / "S2_elevation_zoom3b_sheet.png")
        return
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(a.fps), "-i", str(fr / "f_%04d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", "-movflags", "+faststart",
                    str(out / "S2_elevation_zoom3b.mp4")], check=True)
    Image.open(fr / f"f_{len(ts) - 1:04d}.png").save(out / "S2_elevation_zoom3b_last.png")
    print("wrote", out / "S2_elevation_zoom3b.mp4", f"{len(ts) / a.fps:.2f} s")


if __name__ == "__main__":
    main()
