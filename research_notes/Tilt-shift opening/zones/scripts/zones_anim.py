"""The zones animated for the storyboard, in place of the zoom-out's zone close-up (the user, 10 November 2026: "please
add these to the storyboard instead of the zo-zone in an animation with appropriate length"), from the approved white
stills (zones.py, palette `white`): one zone and its own label at a time, no other text on the map.

Render once, push afterwards (establish.py's push): each camera rendered once, OVERSCAN larger (the same view in more
pixels, picture and depth), the tilt-shift and the zones drawn on that still (zones.py's coverage at its size, its lines
as many pixels wider), graded once, one graded copy per zone; then each frame a crop about the centre resampled to the
frame (Lanczos, always a reduction), the zone shown by a mix of the graded copy without it and with it, the look's
vignette and grain, and the labels drawn sharp at their places for that frame's view.
- 0-7.6 s the close camera (zones.CLOSE): from black over 0.6 s, a slow zoom in to rest by 7.6 s; the dome fades in
  (1.0-2.5 s: its opacity only, never a shape that grows), then its four lines (2.5-3.3 s), out before the dissolve.
- 7.6-8.8 s a dissolve to the wide camera (zones.WIDE), a mix of the two renders.
- the wide camera eases back from 1.2x to the approved framing (by 20 s), then holds: the precautionary band and its
  label (9.0 s), the planning band (13.6 s) as the first goes, Ukraine's 30 km ring (19.2 s) as that goes; held to the end.
Silent (the user: no line sound on the opening for now). 30 fps for the storyboard; the final at 60.

    .venv/bin/python -I "research_notes/Tilt-shift opening/zones/scripts/zones_anim.py" [--fps 60]
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import shutil
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("zones", HERE / "zones.py")
Z = importlib.util.module_from_spec(spec)
spec.loader.exec_module(Z)
E = Z.E
W, H = E.W, E.H
OUT = Z.OUT
STEM = "zones_animation"
PALETTE = "white"
OVERSCAN = E.OVERSCAN
BIG = (round(W * OVERSCAN), round(H * OVERSCAN))

# the timeline, seconds (zone: in from, in to, out from, out to; None: held to the end)
DUR = 24.5
FADE_IN = (0.0, 0.6)
CLOSE_ZOOM = (1.0, 1.05, 0.0, 7.6)        # from, to, start, end (eased in and out: rest to rest)
DISSOLVE = (7.6, 8.8)
WIDE_ZOOM = (1.2, 1.0, 7.6, 20.0)
DOME = (1.0, 2.5, None, None)             # the dome stays on through the dissolve
DOME_TEXT = (2.5, 3.3, 6.8, 7.4)
ZONES = {"paz": {"band": (9.0, 10.0, 13.6, 14.6), "label": (9.4, 10.2, 13.3, 13.9)},
         "upz": {"band": (13.6, 14.6, 19.2, 20.2), "label": (14.3, 15.1, 18.9, 19.5)},
         "obs": {"band": (19.2, 20.2, None, None), "label": (19.9, 20.7, None, None)}}
MARGIN = 30


def ease(u: float) -> float:
    u = min(max(u, 0.0), 1.0)
    return 0.5 - 0.5 * math.cos(math.pi * u)


def ramp(t: float, a: float, b: float) -> float:
    return ease((t - a) / (b - a))


def alpha(t: float, w: tuple) -> float:
    a = ramp(t, w[0], w[1])
    return a if w[2] is None else a * (1.0 - ramp(t, w[2], w[3]))


def zoom_at(t: float, z: tuple) -> float:
    return z[0] + (z[1] - z[0]) * ramp(t, z[2], z[3])


def zoomed(f0: dict, z: float) -> dict:
    """The frame's view for a crop `z` times smaller about the centre: the same camera, its lens z times longer."""
    f = dict(f0)
    f["lens"] = f0["lens"] * z
    return f


def render_big(v: dict, folder: str, cam: dict) -> tuple[Path, float | None]:
    d = E.SCRATCH / folder
    if (d / "d_0001.npy").exists():
        return d, None
    d.mkdir(parents=True, exist_ok=True)
    keep = E.HAZE_VISIBILITY_KM
    E.HAZE_VISIBILITY_KM = v.get("haze_visibility_km", keep)
    E.camera_json([E.frame(cam, v, "present")], cam, d / "camera.json")
    E.HAZE_VISIBILITY_KM = keep
    return d, E.blender(d / "camera.json", d, "1", d / "blender.log", size=BIG)


def prepare(d: Path, f0: dict, sf: dict, what: list[str]) -> dict:
    """The still tilt-shifted and graded, and one graded copy per zone drawn on it (uint8, BIG)."""
    img = np.asarray(Image.open(d / "f_0001.png").convert("RGB"))
    dist = np.load(d / "d_0001.npy")
    assert img.shape[:2] == (BIG[1], BIG[0]) == dist.shape, (img.shape, dist.shape)
    plane = E.focal_plane(E.plane_points(sf))
    ts = E.tilt_shift(img, E.blur_map(f0, dist, *plane, scale=OVERSCAN), [r * OVERSCAN for r in E.LEVELS])
    F = Z.fields(f0, dist)
    out = {"base": E.colour(ts, E.GRADE)}
    for k in what:
        if k == "dome":
            cov, rgb = Z.dome_cov(f0, dist), Z.DOME_RGB
        else:
            cov, rgb = Z.zone_cov(F, k, OVERSCAN), np.array(Z.RINGS[k]["rgb"], np.float32) / 255.0
        out[k] = E.colour(Z.blend(ts, cov, rgb), E.GRADE)
    return out


def crop(big: np.ndarray, z: float) -> np.ndarray:
    cx, cy = BIG[0] / 2, BIG[1] / 2
    hw, hh = BIG[0] / 2 / z, BIG[1] / 2 / z
    return np.asarray(Image.fromarray(big).resize((W, H), Image.LANCZOS, box=(cx - hw, cy - hh, cx + hw, cy + hh)))


def mix(layers: dict, shown: dict) -> np.ndarray:
    m = layers["base"]
    for k, a in shown.items():
        if a > 1e-3:
            m = cv2.addWeighted(m, 1.0 - a, layers[k], a, 0.0)
    return m


def label_course(key: str, sf: dict, views: list[dict]) -> np.ndarray:
    """The zone's label course on the ground (zones.ring_label's), at its preferred bearing, else the nearest that
    fits every view it is shown in: chosen once, so the label never jumps."""
    z = Z.RINGS[key]
    r = z["label_r"]
    span = math.degrees(560.0 / r) * (8 if r < 10000 else 5)
    lvl = sf.get("level_m") or 3.0
    for dev in [0] + [s * k for k in range(5, 181, 5) for s in (1, -1)]:
        path = E.densify(Z.arc_path(r, z["label_at_deg"] + dev, span), 40.0)
        pts = np.array([[x, y, max(E.ground([x, y], sf), lvl) + 2] for x, y in path])
        ok = True
        for f in views:
            xy = E.project(f, pts)
            if not ((xy[:, 2] > 0).all() and (xy[:, 0] > MARGIN).all() and (xy[:, 0] < W - MARGIN).all()
                    and (xy[:, 1] > MARGIN).all() and (xy[:, 1] < H - MARGIN).all()):
                ok = False
                break
        if ok:
            return pts, dev
    raise RuntimeError(f"{key}: its label fits no bearing in every view")


def main(fps: int) -> None:
    t0 = time.time()
    Z.apply_palette(PALETTE)
    cam = E.look3()
    sf = cam["frames"][E.STATES["present"]["frame"]]
    look_grade = cam["look"].get("grade") or {}
    secs = {}
    dc, secs["close"] = render_big(Z.CLOSE, "zones_anim_close", cam)
    dw, secs["wide"] = render_big(Z.WIDE, "zones_anim_wide", cam)
    fc, fw = E.frame(cam, Z.CLOSE, "present"), E.frame(cam, Z.WIDE, "present")
    close = prepare(dc, fc, sf, ["dome"])
    wide = prepare(dw, fw, sf, list(ZONES))
    t1 = time.time()
    n = round(DUR * fps)
    ts = [i / fps for i in range(n)]
    # the labels' courses, each fitted to every view it is shown in
    courses = {}
    for k, z in ZONES.items():
        views = [zoomed(fw, zoom_at(t, WIDE_ZOOM)) for t in ts if alpha(t, z["label"]) > 0]
        courses[k] = label_course(k, sf, views)
    dome_anchor = np.array([[Z.CENTRE[0] + Z.SITE_R * 0.75, Z.CENTRE[1] - Z.SITE_R * 0.75, 30.0]])
    fin = E.SCRATCH / "zones_anim" / f"final_{fps}"
    if fin.exists():
        shutil.rmtree(fin)
    fin.mkdir(parents=True)
    for i, t in enumerate(ts, start=1):
        wc = 1.0 - ramp(t, *DISSOLVE)
        zc, zw = zoom_at(t, CLOSE_ZOOM), zoom_at(t, WIDE_ZOOM)
        frame = None
        if wc > 1e-4:
            frame = crop(mix(close, {"dome": alpha(t, DOME)}), zc)
        if wc < 1 - 1e-4:
            w = crop(mix(wide, {k: alpha(t, z["band"]) for k, z in ZONES.items()}), zw)
            frame = w if frame is None else cv2.addWeighted(frame, wc, w, 1.0 - wc, 0.0)
        im = E.finish(Image.fromarray(frame), i, look_grade)
        layer = E.Layer()
        a = alpha(t, DOME_TEXT)
        if a > 1e-3:
            x, y, _ = E.project(zoomed(fc, zc), dome_anchor)[0]
            for j, line in enumerate(Z.DOME_LABEL):
                E._place(layer, {"text": line, "style": "dome" if j == 0 else "dome_small", "dot": False},
                         float(x) + 34, float(y) + 30 + j * 21, a)
        for k, z in ZONES.items():
            a = alpha(t, z["label"])
            if a > 1e-3:
                xy = E.project(zoomed(fw, zw), courses[k][0])
                E._along(layer, {"text": Z.RINGS[k]["label"], "style": f"zone_{k}"}, xy[:, :2], a)
        layer.onto(im)
        fade = ramp(t, *FADE_IN)
        if fade < 1:
            im = Image.fromarray((np.asarray(im).astype(np.float32) * fade + 0.5).astype(np.uint8))
        im.save(fin / f"f_{i:04d}.png")
    post_s = time.time() - t1
    suffix = "" if fps == 30 else f"_{fps}fps"
    mp4 = OUT / f"{STEM}{suffix}.mp4"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(fps), "-i", str(fin / "f_%04d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", "-movflags", "+faststart", str(mp4)], check=True)
    shutil.copy(fin / f"f_{n:04d}.png", OUT / f"{STEM}{suffix}_last.png")
    moments = [0.3, 2.0, 3.6, 8.2, 9.6, 12.0, 14.1, 16.5, 19.7, 21.0, 23.0, DUR - 1 / fps]
    tw, th = 640, 360
    sheet = Image.new("RGB", (tw * 3, th * 4), (0, 0, 0))
    dr = ImageDraw.Draw(sheet)
    for k, s in enumerate(moments):
        i = min(n, round(s * fps) + 1)
        sheet.paste(Image.open(fin / f"f_{i:04d}.png").resize((tw, th), Image.LANCZOS), ((k % 3) * tw, (k // 3) * th))
        dr.text(((k % 3) * tw + 8, (k // 3) * th + 6), f"{(i - 1) / fps:4.1f} s", fill=(255, 255, 255))
    sheet.save(OUT / f"{STEM}{suffix}_sheet.jpg", quality=90)
    zdoc = json.loads((OUT / "zones.json").read_text())
    doc = {"title": "The plant's zones: the protection zone never sized, three zones with a distance",
           "asked": "the user, 10 November 2026: 'please add these to the storyboard instead of the zo-zone in an "
                    "animation with appropriate length', from the white stills (zones.json)",
           "file": mp4.name, "sha256": hashlib.sha256(mp4.read_bytes()).hexdigest(), "fps": fps, "size": [W, H],
           "frames": n, "seconds": DUR, "sound": None, "palette": {PALETTE: Z.P.PALETTES[PALETTE]},
           "timeline": {"fade_in_s": FADE_IN, "close_zoom": {"from": CLOSE_ZOOM[0], "to": CLOSE_ZOOM[1], "s": CLOSE_ZOOM[2:]},
                        "dissolve_s": DISSOLVE, "wide_zoom": {"from": WIDE_ZOOM[0], "to": WIDE_ZOOM[1], "s": WIDE_ZOOM[2:]},
                        "dome": {"in_s": DOME[:2], "label_s": DOME_TEXT},
                        "zones": {k: {"band_s": z["band"], "label_s": z["label"],
                                      "label_bearing_deg": Z.RINGS[k]["label_at_deg"] + courses[k][1]}
                                  for k, z in ZONES.items()},
                        "note": "each fade eased (cosine); a zone shown alone with its own label, a band fading out as "
                                "the next fades in; no other text on the map"},
           "method": {"mode": "render once, push afterwards (establish.py push)", "render_size": list(BIG),
                      "overscan": OVERSCAN, "render_s": secs, "post_s": round(post_s), "total_s": round(time.time() - t0),
                      "statement": "a drawing convention: the moves are zooms into one rendered still per camera (no "
                                   "parallax), the dissolve and the zones' fades mixes of rendered and drawn pictures; "
                                   "pixels only resampled or mixed, never generated or interpolated between frames"},
           "cameras": {"close": Z.CLOSE, "wide": Z.WIDE}, "centre": zdoc["centre"], "dome": zdoc["dome"],
           "rings": zdoc["rings"], "unsized": zdoc["unsized"], "note": zdoc["note"], "far_plain": zdoc["far_plain"],
           "depth": "Blender's depth pass is half float underneath: past 65,504 m the rays are met with the terrain "
                    "(zones.py terrain_z)",
           "report": Z.REPORT, "stills": "zones.json (white)",
           "safety": zdoc["safety"]}
    (OUT / f"{STEM}{suffix}.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False))
    print(f"wrote {mp4.name}: {n} frames, {DUR} s; render {secs}, post {post_s:.0f} s, total {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main(int(sys.argv[sys.argv.index("--fps") + 1]) if "--fps" in sys.argv else 30)
