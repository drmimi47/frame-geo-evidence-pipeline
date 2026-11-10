"""The tower to scale, second pass (the user, 8 November 2026: the tower at the centre, its base truer, more cinematic
but still short). One continuous move: close on a person standing on the drained bed in front of the caisson, the
camera craning up and back as it tilts up the concrete and the steel, then backing far off while the lens lengthens
until the view is flat: the elevation drawing, centred, its dimensions arriving, the ground cut open to the caisson's
base. A perspective camera all the way (tower.py's crane view); at 20 km and a 2.5 m lens the last frames are flat to
under a pixel, so the drawing's lines are laid on them as on an orthographic view.
python zoom2.py OUT_DIR [--fps 30] [--skip-render] [--stills 0,2.5,5]
World: metres, x across the line (the tower's axis at 0), y toward the tower from the camera's side, z up from the
caisson's base. The base: 12.8 m under the old water (the only published depth, no. 19's), on the bed divers prepared
on the reservoir's floor (the caissons were floated out and flooded down onto it, 1977 and 1984); the drained bed
about 8.4 m under the old water (inferred), so the base about 4.4 m into the ground."""
import argparse, json, math, subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from image_evidence.satellite import zoomout as z
from zoom import OUTLINE, ease

ROOT = Path(__file__).resolve().parents[3]
C3D = ROOT / "libraries/conductive-seam/satellite/networks/znpp/scenes/crossing3d"
W_PX, H_PX, SS = 1920, 1080, 2
INK, DIM = (235, 235, 235), (140, 140, 140)

OLD_WATER, BED = 12.8, 4.4                  # above the caisson's base: the reservoir's old level; the bed today (inferred)
LEGS = OLD_WATER + 3.0                      # the caisson's top, the legs' feet
TOP = LEGS + 126.0
FIG = (11.0, -22.4, BED)                    # the person: on the bed, 1.5 m in front of the caisson's wall, right of centre
W_END = 300.0                               # the last frame's width on the tower's plane (m)
Z_END = TOP + 14 - W_END * 9 / 16 / 2       # its centre: the top 14 m under the frame's top edge
D_END = 20000.0                             # the camera's last distance: flat to well under a pixel over the caisson's depth

# the eye's keys: time (s), x, distance in front of the tower (m), height (from the caisson's base), lens (mm, 36 mm
# sensor). Each channel eased through its keys (monotone cubic: no overshoot, no stop between keys where a channel
# keeps going). The tilt isn't keyed: each frame it is solved so the person's feet stay low in the frame (FEET_Y), so
# the person is in every frame, shrinking under the tower as the camera pulls back; the eye's aim swings from the
# person to the tower's axis (AIM_S).
KEYS = [
    (0.0, 12.6, 31.3, BED + 1.6, 62.0),
    (0.7, 12.6, 31.3, BED + 1.6, 62.0),
    (2.4, 13.0, 62.0, BED + 1.7, 21.0),
    (3.8, 8.0, 150.0, BED + 4.0, 18.0),
    (5.0, 4.0, 560.0, 40.0, 62.0),
    (6.3, 0.0, D_END, Z_END, 36.0 * D_END / W_END),
]
FEET_Y = [(0.0, 906.0), (0.7, 906.0), (2.2, 960.0), (6.3, None)]   # None: wherever the flat drawing puts them
AIM_S = (0.7, 4.0)
T_END = 8.6                                  # the drawing held 2.6 s


def _pchip(t, v):
    """Monotone cubic through (t, v) (Fritsch-Carlson), flat at both ends."""
    h = np.diff(t); dl = np.diff(v) / h
    m = np.zeros(len(t))
    for i in range(1, len(t) - 1):
        if dl[i - 1] * dl[i] > 0:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / dl[i - 1] + w2 / dl[i])

    def f(s):
        i = int(np.clip(np.searchsorted(t, s) - 1, 0, len(t) - 2)); u = (s - t[i]) / h[i]
        return (v[i] * (2 * u ** 3 - 3 * u ** 2 + 1) + h[i] * m[i] * (u ** 3 - 2 * u ** 2 + u) +
                v[i + 1] * (-2 * u ** 3 + 3 * u ** 2) + h[i] * m[i + 1] * (u ** 3 - u ** 2))
    return f


def _chan(vals, log=False):
    t = np.array([k[0] for k in KEYS])
    f = _pchip(t, np.array([math.log(x) if log else x for x in vals], float))
    return lambda s: (math.exp(f(min(max(s, 0), t[-1]))) if log else float(f(min(max(s, 0), t[-1]))))


_EX, _ED, _EZ, _LENS = (_chan([k[1] for k in KEYS]), _chan([k[2] for k in KEYS], True), _chan([k[3] for k in KEYS]),
                        _chan([k[4] for k in KEYS], True))


def _feet_y(t):
    end = H_PX / 2 + (Z_END - BED) * W_PX / W_END     # where the flat drawing puts the feet
    ks = [(a, end if y is None else y) for a, y in FEET_Y]
    for (t0, y0), (t1, y1) in zip(ks, ks[1:]):
        if t <= t1:
            return y0 + (y1 - y0) * ease((t - t0) / (t1 - t0))
    return ks[-1][1]


def camera(t):
    """Eye, target and lens at t seconds (sensor 36 mm wide): the tilt solved so the person's feet sit at _feet_y."""
    t = min(max(t, 0.0), KEYS[-1][0])
    eye = np.array([_EX(t), -_ED(t), max(_EZ(t), BED + 1.2)]); lens = _LENS(t)
    s = ease((t - AIM_S[0]) / (AIM_S[1] - AIM_S[0]))
    aim = np.array([FIG[0] * (1 - s), FIG[1] * (1 - s)])
    yaw = math.atan2(aim[0] - eye[0], aim[1] - eye[1]); reach = float(np.hypot(*(aim - eye[:2])))
    want, feet = _feet_y(t), (FIG[0], FIG[1], BED)
    lo, hi = math.radians(-30), math.radians(80)
    for _ in range(60):                                 # tilting up moves the feet down the frame
        pitch = (lo + hi) / 2
        tgt = eye + reach * np.array([math.sin(yaw) * math.cos(pitch), math.cos(yaw) * math.cos(pitch), math.sin(pitch)])
        if project(feet, (eye, tgt, lens))[1] < want:
            lo = pitch
        else:
            hi = pitch
    return eye, tgt, lens


def project(p, cam):
    """World point to pixels as Blender's camera sees it (track -Z, up Y toward world Z, horizontal sensor fit)."""
    eye, tgt, lens = cam
    f = tgt - eye; f /= np.linalg.norm(f)
    r = np.cross(f, [0, 0, 1.0]); r /= np.linalg.norm(r); u = np.cross(r, f)
    q = np.asarray(p, float) - eye; k = lens / 36.0 * W_PX / q.dot(f)
    return W_PX / 2 + q.dot(r) * k, H_PX / 2 - q.dot(u) * k


def flatness(t):
    """0 while the view is in perspective, 1 once it is flat enough for the drawing's lines."""
    return ease((math.log(_ED(min(t, KEYS[-1][0]))) - math.log(2500)) / (math.log(D_END) - math.log(2500)))


def overlay(cam, t):
    im = Image.new("RGBA", (W_PX * SS, H_PX * SS), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
    P = lambda x, zz, y=0.0: tuple(c * SS for c in project((x, y, zz), cam))
    font = lambda size: z._hn(size * SS, 0)
    FS, MED = font(14), font(30)
    fl = flatness(t)
    a_cut = ease((fl - 0.2) / 0.5)                      # the ground opened once the bed is seen edge on
    a_dims = ease((t - 6.0) / 0.6)
    a_title = ease((t - 6.5) / 0.7)
    a_fig0 = 1 - a_dims                                  # the person's label rides beside it, then gives way to the leader
    col = lambda rgb, a: (*rgb, int(255 * a))

    if a_cut > 0:   # the ground cut open: dark earth under the bed, hatched, the buried drum seen through it
        _, yb = P(0, BED)
        earth = Image.new("RGBA", im.size, (0, 0, 0, 0)); de = ImageDraw.Draw(earth)
        de.rectangle([0, yb, im.size[0], im.size[1]], fill=(8, 8, 9, int(150 * a_cut)))
        step = 14 * SS
        for x0 in range(-im.size[1], im.size[0], step):
            de.line([(x0, im.size[1]), (x0 + (im.size[1] - yb), yb)], fill=(70, 70, 72, int(110 * a_cut)), width=1)
        im = Image.alpha_composite(im, earth); dr = ImageDraw.Draw(im)

    def dim_v(x, z0, z1, label, a):
        (xa, ya), (_, yb) = P(x, z0), P(x, z1)
        dr.line([(xa, ya), (xa, yb)], fill=col(INK, a), width=SS)
        for yy in (ya, yb):
            dr.line([(xa - 6 * SS, yy), (xa + 6 * SS, yy)], fill=col(INK, a), width=SS)
        dr.text((xa + 12 * SS, (ya + yb) / 2), label, font=FS, fill=col(INK, a), anchor="lm")

    def level(zw, label, dash, a, dy=0):
        (xa, y), (xb, _) = P(-62, zw), P(62, zw)
        if dash:
            xx = xa
            while xx < xb:
                dr.line([(xx, y), (min(xx + 10 * SS, xb), y)], fill=col(DIM, a), width=SS); xx += 18 * SS
        else:
            dr.line([(xa, y), (xb, y)], fill=col(DIM, a), width=SS)
        dr.text((xa - 12 * SS, y + dy * SS), label, font=FS, fill=col(DIM, a), anchor="rm")

    if a_dims > 0:
        # the levels' names far left, the base's depth on the right of the caisson, so no two labels share a line
        level(OLD_WATER, "THE RESERVOIR UNTIL 6 JUNE 2023", False, a_dims, -4)
        level(BED, "THE DRAINED BED TODAY (INFERRED)", True, a_dims, 4)
        dim_v(48, LEGS, TOP, "126 M", a_dims)
        (xa, ya), (_, yb) = P(-30, LEGS), P(-30, LEGS + 113)   # 113 m on the left, its label to the left
        dr.line([(xa, ya), (xa, yb)], fill=col(INK, a_dims), width=SS)
        for yy in (ya, yb):
            dr.line([(xa - 6 * SS, yy), (xa + 6 * SS, yy)], fill=col(INK, a_dims), width=SS)
        dr.text((xa - 12 * SS, (ya + yb) / 2), "113 M: THE LOWER CROSSARM", font=FS, fill=col(INK, a_dims), anchor="rm")
        (xd, ya), (_, yb) = P(28, 0), P(28, OLD_WATER)
        dr.line([(xd, ya), (xd, yb)], fill=col(INK, a_dims), width=SS)
        for yy in (ya, yb):
            dr.line([(xd - 6 * SS, yy), (xd + 6 * SS, yy)], fill=col(INK, a_dims), width=SS)
        dr.text((xd + 12 * SS, (ya + yb) / 2 - 10 * SS), "THE BASE 12.8 M UNDER THE OLD WATER,", font=FS,
                fill=col(INK, a_dims), anchor="lm")
        dr.text((xd + 12 * SS, (ya + yb) / 2 + 10 * SS), "ABOUT 4 M INTO THE GROUND (INFERRED)", font=FS,
                fill=col(INK, a_dims), anchor="lm")
        (xa, y), (xb, _) = P(-20.5, -3), P(20.5, -3)
        dr.line([(xa, y), (xb, y)], fill=col(INK, a_dims), width=SS)
        dr.text(((xa + xb) / 2, y + 8 * SS), "41 M ACROSS", font=FS, fill=col(INK, a_dims), anchor="ma")
        # the person, a speck now: a leader down to the right, into the cut under the base's depth
        hx, hy = P(FIG[0], BED + 0.4, FIG[1])
        ex, ey = P(24, -5.5)
        dr.line([(hx + 2 * SS, hy + 2 * SS), (ex, ey)], fill=col(INK, a_dims * 0.8), width=SS)
        dr.text((ex + 8 * SS, ey), "A PERSON, 1.75 M", font=FS, fill=col(INK, a_dims), anchor="lm")
    if a_fig0 > 0:   # beside the head, at least a few pixels off the figure however small; on a dark box over the concrete
        (fx, fy), (hx, hy) = P(FIG[0] + 0.3, BED, FIG[1]), P(FIG[0] + 0.3, BED + 1.6, FIG[1])
        lx, ly = fx + max((fy - hy) * 0.25, 8 * SS), hy + min((fy - hy) * 0.1, 6 * SS)
        l, tp, r, bt = dr.textbbox((lx, ly), "A PERSON, 1.75 M", font=FS, anchor="lm")
        dr.rectangle([l - 5 * SS, tp - 4 * SS, r + 5 * SS, bt + 4 * SS], fill=(0, 0, 0, int(150 * a_fig0)))
        dr.text((lx, ly), "A PERSON, 1.75 M", font=FS, fill=col(INK, a_fig0), anchor="lm")

    if a_title > 0:
        for i, line in enumerate(["THE 750 KV CROSSING TOWER", "OVER THE DNIPRO"]):
            dr.text((120 * SS, (140 + i * 30 * 1.35) * SS), line, font=MED, fill=col(INK, a_title))
        dr.text((120 * SS, 245 * SS), "ONE OF FOUR ON THE CROSSING. A REPRESENTATIVE MODEL OF THE TYPE, DRAWN FROM",
                font=FS, fill=col(DIM, a_title))
        dr.text((120 * SS, 268 * SS), "PHOTOGRAPHS AND PUBLISHED HEIGHTS; THE PERSON DRAWN.", font=FS, fill=col(DIM, a_title))
    return im.resize((W_PX, H_PX), Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("out"); ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--skip-render", action="store_true"); ap.add_argument("--stills")
    a = ap.parse_args(); out = Path(a.out)
    ts = ([float(x) for x in a.stills.split(",")] if a.stills else
          [f / a.fps for f in range(round(T_END * a.fps))])
    tag = "stills" if a.stills else "crane"
    raw, fr = out / f"{tag}_raw", out / f"{tag}_frames"
    raw.mkdir(parents=True, exist_ok=True); fr.mkdir(exist_ok=True)
    t_move = KEYS[-1][0]
    n_move = sum(1 for t in ts if t <= t_move)
    cams = [camera(min(t, t_move)) for t in ts]
    rend = [cams[i] for i in range(len(ts)) if ts[i] <= t_move] or cams[:1]
    if not a.stills:
        rend = cams[:n_move]                            # the hold repeats the last moving frame
    (out / f"{tag}_cams.json").write_text(json.dumps({
        "frames": [[*map(float, e), *map(float, g), float(l), 1 - flatness(t)]
                   for t, (e, g, l) in zip(ts, rend if not a.stills else cams)],
        "figure": {"outline": OUTLINE, "at": FIG}, "bed": BED}))
    if not a.skip_render:
        subprocess.run(["blender", "-b", "--factory-startup", "-P", str(Path(__file__).with_name("tower.py")), "--",
                        str(C3D / "towers.npz"), str(C3D / "scene.json"), "crane", str(raw), str(out / f"{tag}_cams.json")],
                       check=True, stdout=subprocess.DEVNULL)
    for i, (t, cam) in enumerate(zip(ts, cams)):
        j = i if a.stills else min(i, n_move - 1)
        base = Image.open(raw / f"f_{j + 1:04d}.png").convert("RGBA")
        fade = ease(t / 0.5) if not a.stills else 1.0
        frame = Image.alpha_composite(base, overlay(cam, t)).convert("RGB")
        if fade < 1:
            frame = Image.eval(frame, lambda v, f=fade: int(v * f))
        frame.save(fr / f"f_{i:04d}.png")
    if a.stills:
        tiles = [Image.open(fr / f"f_{i:04d}.png").resize((640, 360)) for i in range(len(ts))]
        sheet = Image.new("RGB", (1920, 360 * math.ceil(len(tiles) / 3)))
        for i, im in enumerate(tiles):
            sheet.paste(im, ((i % 3) * 640, (i // 3) * 360))
        sheet.save(out / "stills_sheet.png"); print("sheet", out / "stills_sheet.png")
        return
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(a.fps), "-i", str(fr / "f_%04d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", str(out / "S2_elevation_zoom2.mp4")], check=True)
    Image.open(fr / f"f_{len(ts) - 1:04d}.png").save(out / "S2_elevation_zoom2_last.png")
    print("wrote", out / "S2_elevation_zoom2.mp4", f"{len(ts) / a.fps:.2f} s")


if __name__ == "__main__":
    main()
