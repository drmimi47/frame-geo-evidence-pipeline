"""The tower to scale, fourth pass with the user's fixes (9 November 2026: "move the "100M" and its line measurement to
the left of the FEROSPLAVNA towers. When sliding the towers to the left ... do not do the slide left and move up move.
i jsut want them to be slid to the left ... the time between 12-18 seconds is wasted time. rmeove and ensure the flow
of things makes sense since there should be more time seeing all 8 towers on the page before the dimensions show
up"). zoom3.py's renders reused as they are (the move's frames and the three sprites); zoom3b.py's marks and type,
with:
- the picture's 46 px rise (room for the widths and the captions under the bases) folded into the pull-back's last
  1.8 s, while the camera is still settling and the frame's bottom is already black, so the flat part starts where
  it stays: from the hand-over nothing moves up or down, the stack only slides left;
- the captions at their final place from the first (under where the widths come), never stepping down;
- Ferosplavna's height on the left of its front tower, mirroring Dniprovska's;
- the hold after the pull-back cut: the line named 0.8 s after the camera lands, the rest following on, a longer hold
  on all eight towers with both captions before the dimensions; 30 s in all.

python zoom3c.py SCRATCH_DIR ZOOM3_DIR OUT_DIR [--fps 30] [--stills 0,13,16.4,...]
  ZOOM3_DIR: zoom3.py's scratch (crane3_raw/, sprites3/); OUT_DIR: where the video, last frame and sheet go
"""
import argparse, math, subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import zoom3 as Z3
import zoom3b as B
import zoom2 as Z
from zoom import ease
from image_evidence.satellite import zoomout as z

W_PX, H_PX, SS = Z3.W_PX, Z3.H_PX, Z3.SS
INK, DIM = Z3.INK, Z3.DIM
T_MOVE = Z3.T_MOVE                           # 13.0 s: the camera lands
# the new timing, set on zoom3 so its layout (the towers behind, the slide, Ferosplavna coming in) follows it
Z3.T_CAP = 13.8                              # Dniprovska named, after a short hold
Z3.T_BEHIND = [(14.8, 16.2), (15.7, 17.1)]   # the two towers behind slide out
Z3.T_SUB2 = 16.6                             # its count, once all three show
Z3.T_SHIFT = (18.0, 21.0)                    # the stack slides left (only left)
Z3.T_FERO = 18.8                             # Ferosplavna's towers come in from the right
Z3.T_CAP2 = 21.6                             # its caption
T_DIMS = (25.0, 0.8)                         # 3.4 s on all eight with both captions, then the dimensions
T_END = 30.0
DY = B.DY                                    # 46 px: the picture's rise, done by the end of the pull-back
T_RISE = (11.2, T_MOVE)                      # the frame's bottom rows are black in zoom3's renders from about 11.4 s
CAP, DIMS, HALF_750, HALF_330 = B.CAP, B.DIMS, B.HALF_750, B.HALF_330


def rise(t):
    return DY * ease((t - T_RISE[0]) / (T_RISE[1] - T_RISE[0]))


def earth(size, yb, a):
    """zoom2's ground cut open: dark earth under the bed, hatched, to the frame's bottom."""
    im = Image.new("RGBA", size, (0, 0, 0, 0)); de = ImageDraw.Draw(im)
    de.rectangle([0, yb, size[0], size[1]], fill=(8, 8, 9, int(150 * a)))
    for x0 in range(-size[1], size[0], 14 * SS):
        de.line([(x0, size[1]), (x0 + (size[1] - yb), yb)], fill=(70, 70, 72, int(110 * a)), width=1)
    return im


def move_overlay(cam, t, dy):
    """During the move only the ground cut, as zoom3's, risen with the picture."""
    size = (W_PX * SS, H_PX * SS)
    a_cut = ease((Z.flatness(t) - 0.2) / 0.5)
    if a_cut <= 0:
        return Image.new("RGBA", (W_PX, H_PX), (0, 0, 0, 0))
    yb = Z.project((0, 0, Z.BED), cam)[1] * SS - dy * SS
    return earth(size, yb, a_cut).resize((W_PX, H_PX), Image.LANCZOS)


def overlay(t, shift_px):
    """The marks after the move: the ground cut open, the captions, and at the end the groups' dimensions."""
    im = Image.new("RGBA", (W_PX * SS, H_PX * SS), (0, 0, 0, 0))
    font = lambda size: z._hn(size * SS, 0)
    FS, FC = font(14), font(20)
    col = lambda rgb, a: (*rgb, int(255 * a))
    P = lambda x, zz: (Z3.P(x, zz)[0], Z3.P(x, zz)[1] - DY * SS)
    _, yb = P(0, Z.BED)
    im = Image.alpha_composite(im, earth(im.size, yb, 1.0)); dr = ImageDraw.Draw(im)
    sx = shift_px * SS
    _, ybase = P(0, 0)
    y1, y2 = ybase + 48 * SS, ybase + 78 * SS     # zoom3b's captions where they ended: under the widths
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
        for kv, cx, half in (("750", Z3.X750, HALF_750), ("330", Z3.X330, HALF_330)):
            d = DIMS[kv]
            _, y_top = P(0, Z.LEGS + d["h_m"])
            # the height left of each group's front tower (the farther ones stand to its right)
            xh = (cx - half - 26) * SS
            dr.line([(xh, y_legs), (xh, y_top)], fill=col(INK, a), width=SS)
            for yy in (y_legs, y_top):
                dr.line([(xh - tick, yy), (xh + tick, yy)], fill=col(INK, a), width=SS)
            dr.text((xh - 12 * SS, (y_legs + y_top) / 2), d["height"], font=FS, fill=col(INK, a), anchor="rm")
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
        if t < T_MOVE:   # the move: zoom3's own frames, risen over its last 1.8 s, and the ground cut
            k = min(int(round(t * 30)), n_raw - 1)
            dy = rise(k / 30)
            base = B.vshift(Image.open(raw / f"f_{k + 1:04d}.png").convert("RGBA"), dy)
            frame = Image.alpha_composite(base, move_overlay(Z.camera(k / 30), k / 30, dy))
        else:
            base, sh = Z3.compose(sprites, t)
            frame = Image.alpha_composite(B.vshift(base, DY), overlay(t, sh))
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
        sheet.save(out / "S2_elevation_zoom3c_sheet.png"); print("sheet", out / "S2_elevation_zoom3c_sheet.png")
        return
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(a.fps), "-i", str(fr / "f_%04d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", "-movflags", "+faststart",
                    str(out / "S2_elevation_zoom3c.mp4")], check=True)
    Image.open(fr / f"f_{len(ts) - 1:04d}.png").save(out / "S2_elevation_zoom3c_last.png")
    print("wrote", out / "S2_elevation_zoom3c.mp4", f"{len(ts) / a.fps:.2f} s")


if __name__ == "__main__":
    main()
