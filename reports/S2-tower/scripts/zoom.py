"""The tower to scale as a quick zoom (the user, 5 November 2026): close on a person standing on the drained bed by
the caisson, out to the whole 126 m tower, the elevation drawing's dimensions arriving as the frame takes them in.
python zoom.py OUT_DIR [--fps 30]   (renders with tower.py's zoom view, draws the figure and the text, writes
OUT_DIR/S2_elevation_zoom.mp4 and its last frame)
World: metres, x across the line (the tower's axis at 0), z up from the caisson's base (12.8 m below the old water)."""
import argparse, json, math, subprocess
from pathlib import Path

from PIL import Image, ImageDraw

from image_evidence.satellite import zoomout as z

ROOT = Path(__file__).resolve().parents[3]
C3D = ROOT / "libraries/conductive-seam/satellite/networks/znpp/scenes/crossing3d"
W_PX, H_PX, SS = 1920, 1080, 2          # the overlay drawn at twice the size, then reduced: smooth edges
INK, DIM, FIGURE = (235, 235, 235), (140, 140, 140), (245, 245, 245)

OLD_WATER, BED, TOP = 12.8, 4.4, 12.8 + 3.0 + 126   # the reservoir's 16 m; the bed about 8 m (inferred); the top
FIG_X, FIG_H = 24.0, 1.75                # the figure on the bed, 3.5 m out from the caisson's wall (x 20.5)
START = (23.4, BED + 1.3, 8.0)           # centre x, centre z, frame width (m): the figure and the caisson's foot
END = (-69.6, TOP / 2 + 2, 290.0)        # the elevation drawing's frame, as S2_elevation_dimensioned.png
HOLD_IN, ZOOM, HOLD_OUT = 0.5, 2.4, 3.1  # seconds: 6 s, as the still it replaces

# a person standing, front on: the right half of the outline, (x, z) in metres from the feet's centre, top to toe;
# head, neck, shoulder, the arm hanging free of the body, the hip, the leg, the foot (mirrored for the left)
HALF = ([(0.085 * math.sin(a), 1.635 + 0.115 * math.cos(a)) for a in [i * math.pi / 12 for i in range(0, 11)]] +
        [(0.045, 1.505), (0.05, 1.475), (0.15, 1.45), (0.205, 1.425), (0.232, 1.375), (0.243, 1.25), (0.25, 1.06),
         (0.246, 0.9), (0.238, 0.8), (0.222, 0.765), (0.2, 0.775), (0.192, 0.84), (0.195, 0.98), (0.19, 1.15),
         (0.178, 1.3), (0.166, 1.26), (0.152, 1.1), (0.148, 1.0), (0.172, 0.93), (0.17, 0.72), (0.156, 0.46),
         (0.14, 0.2), (0.128, 0.07), (0.168, 0.025), (0.17, 0.0), (0.042, 0.0), (0.044, 0.08), (0.05, 0.42),
         (0.034, 0.76), (0.0, 0.8)])
OUTLINE = HALF + [(-x, zz) for x, zz in reversed(HALF[1:-1])]


def ease(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def camera(t):
    """Centre and width at t (0..1 of the zoom): the width on a log scale, the figure gliding from where it stands
    in the first frame to where it stands in the drawing, so the frame opens about it without a swing."""
    e = ease(t)
    w = math.exp(math.log(START[2]) + (math.log(END[2]) - math.log(START[2])) * e)
    fz = BED + FIG_H / 2
    u0, v0 = screen(FIG_X, fz, START); u1, v1 = screen(FIG_X, fz, END)
    u, v = u0 + (u1 - u0) * e, v0 + (v1 - v0) * e
    k = W_PX / w
    return (FIG_X - (u - W_PX / 2) / k, fz + (v - H_PX / 2) / k, w)


def screen(x, zz, cam):
    cx, cz, w = cam; k = W_PX / w
    return W_PX / 2 + (x - cx) * k, H_PX / 2 - (zz - cz) * k


def frames(fps):
    n_in, n_zoom, n_out = (round(s * fps) for s in (HOLD_IN, ZOOM, HOLD_OUT))
    cams = [camera(0)] * n_in + [camera(i / (n_zoom - 1)) for i in range(n_zoom)] + [camera(1)] * n_out
    return cams, n_in, n_zoom


def overlay(cam, t_zoom, t_s):
    """The text and marks for one frame (RGBA, at SS times the size)."""
    im = Image.new("RGBA", (W_PX * SS, H_PX * SS), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
    P = lambda x, zz: tuple(c * SS for c in screen(x, zz, cam))
    font = lambda size: z._hn(size * SS, 0)
    FS, MED = font(14), font(30)
    a_dims = ease((t_zoom - 0.62) / 0.3)                     # the tower's dimensions once the frame holds them
    a_title = ease((t_s - (HOLD_IN + ZOOM - 0.2)) / 0.7)
    col = lambda rgb, a: (*rgb, int(255 * a))

    def dim_v(x, z0, z1, label):
        (xa, ya), (_, yb) = P(x, z0), P(x, z1)
        dr.line([(xa, ya), (xa, yb)], fill=col(INK, a_dims), width=SS)
        for yy in (ya, yb):
            dr.line([(xa - 6 * SS, yy), (xa + 6 * SS, yy)], fill=col(INK, a_dims), width=SS)
        dr.text((xa + 12 * SS, (ya + yb) / 2), label, font=FS, fill=col(INK, a_dims), anchor="lm")

    def level(zw, label, dash):
        """A level across the drawing, its label at its left end, or at the frame's left edge while the end is off
        it (the line then starts after the label, so the two never cross)."""
        (xa, y), (xb, _) = P(-48, zw), P(48, zw)
        tw = dr.textlength(label, font=FS)
        lx = max(xa - 10 * SS, 40 * SS + tw)
        x0 = max(xa, lx + 14 * SS)
        if dash:
            xx = x0
            while xx < xb:
                dr.line([(xx, y), (min(xx + 10 * SS, xb), y)], fill=col(DIM, 1), width=SS); xx += 18 * SS
        else:
            dr.line([(x0, y), (xb, y)], fill=col(DIM, 1), width=SS)
        l, t, r, bt = dr.textbbox((lx, y), label, font=FS, anchor="rm")   # on a dark box: legible over the caisson
        dr.rectangle([l - 6 * SS, t - 4 * SS, r + 6 * SS, bt + 4 * SS], fill=(0, 0, 0, 200))
        dr.text((lx, y), label, font=FS, fill=col(DIM, 1), anchor="rm")

    level(OLD_WATER, "THE RESERVOIR, 16 M (UNTIL 6 JUNE 2023)", False)
    level(BED, "THE DRAINED BED TODAY, ABOUT 8 M (INFERRED)", True)
    base_t = 12.8 + 3.0
    dim_v(34, base_t, base_t + 126, "126 M")
    dim_v(28, base_t, base_t + 113, "113 M: THE LOWER CROSSARM")
    (xd, ya), (_, yb) = P(-30, 0), P(-30, OLD_WATER)
    dr.line([(xd, ya), (xd, yb)], fill=col(INK, a_dims), width=SS)
    for yy in (ya, yb):
        dr.line([(xd - 6 * SS, yy), (xd + 6 * SS, yy)], fill=col(INK, a_dims), width=SS)
    dr.text((xd - 12 * SS, P(-30, (BED + OLD_WATER) / 2)[1]), "12.8 M BELOW THE OLD WATER", font=FS, fill=col(INK, a_dims), anchor="rm")
    (xa, y), (xb, _) = P(-20.5, -4), P(20.5, -4)
    dr.line([(xa, y), (xb, y)], fill=col(INK, a_dims), width=SS)
    dr.text(((xa + xb) / 2, y + 8 * SS), "41 M ACROSS", font=FS, fill=col(INK, a_dims), anchor="ma")

    dr.polygon([P(FIG_X + x, BED + zz) for x, zz in OUTLINE], fill=col(FIGURE, 1))
    hx, hy = P(FIG_X + 0.4, BED + FIG_H * 0.55)
    hy = min(hy, P(0, BED)[1] - 12 * SS)   # never on the bed's line when the figure is small
    dr.text((max(hx, P(FIG_X, 0)[0] + 10 * SS), hy), "A PERSON, 1.75 M", font=FS,
            fill=col(INK, 1), anchor="lm")

    for i, line in enumerate(["THE 750 KV CROSSING TOWER", "OVER THE DNIPRO"]):
        dr.text((120 * SS, (140 + i * 30 * 1.35) * SS), line, font=MED, fill=col(INK, a_title))
    dr.text((120 * SS, 245 * SS), "SUSPENSION TOWER, ONE OF FOUR ON THE CROSSING. A REPRESENTATIVE MODEL OF THE TYPE, "
            "DRAWN FROM PHOTOGRAPHS", font=FS, fill=col(DIM, a_title))
    dr.text((120 * SS, 268 * SS), "AND PUBLISHED HEIGHTS. THE FIGURE, A DRAWN PERSON OF 1.75 M, STANDS ON THE DRAINED "
            "BED.", font=FS, fill=col(DIM, a_title))
    return im.resize((W_PX, H_PX), Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("out"); ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--skip-render", action="store_true")
    a = ap.parse_args(); out = Path(a.out); raw = out / "zoom_raw"; fr = out / "zoom_frames"
    raw.mkdir(parents=True, exist_ok=True); fr.mkdir(exist_ok=True)
    cams, n_in, n_zoom = frames(a.fps)
    moving = cams[n_in - 1:n_in + n_zoom]                    # the frames that differ: the zoom, from its first
    (out / "zoom_cams.json").write_text(json.dumps({"frames": moving}))
    if not a.skip_render:
        subprocess.run(["blender", "-b", "--factory-startup", "-P", str(Path(__file__).with_name("tower.py")), "--",
                        str(C3D / "towers.npz"), str(C3D / "scene.json"), "zoom", str(raw), str(out / "zoom_cams.json")],
                       check=True, stdout=subprocess.DEVNULL)
    for f, cam in enumerate(cams):
        j = min(max(f - (n_in - 1), 0), len(moving) - 1)
        t_zoom = min(max((f - n_in) / (n_zoom - 1), 0), 1)
        base = Image.open(raw / f"f_{j + 1:04d}.png").convert("RGBA")
        Image.alpha_composite(base, overlay(cam, t_zoom, f / a.fps)).convert("RGB").save(fr / f"f_{f:04d}.png")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(a.fps), "-i", str(fr / "f_%04d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", str(out / "S2_elevation_zoom.mp4")], check=True)
    Image.open(fr / f"f_{len(cams) - 1:04d}.png").save(out / "S2_elevation_zoom_last.png")
    Image.open(fr / f"f_{0:04d}.png").save(out / "S2_elevation_zoom_first.png")


if __name__ == "__main__":
    main()
