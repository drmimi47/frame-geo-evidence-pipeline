"""Pass 1, the camera animatic: each opening rendered by Blender (headless, `build.py`) from the exported scene, then
an mp4 and a contact sheet per opening, and the openings side by side (compare.mp4) to choose between them.

On disk: scenes/crossing3d/animatic/<variant>/f_*.png, <variant>.mp4, <variant>_contact.webp, compare.mp4. A stretch
of one (`seconds`, to test): <variant>_<a>-<b>s/ and <variant>_<a>-<b>s.mp4, its frames and sound those of the whole.
The Hum is <title or variant>.wav beside the mp4. A whole render also saves its scene, <title or variant>.blend, to
open in Blender (`blend` saves it without rendering); only the configured variants' scene files are kept (the user,
2 November 2026: prototypes come and go), never a .blend1. The date, names, fade and the Hum are added after Blender, so the scene file has the picture only.
"""

from __future__ import annotations

import json
import logging
import math
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import export, states

log = logging.getLogger(__name__)

BUILD = Path(__file__).with_name("build.py")
CONTACT_EVERY_S = 1.5
ISLAND_LABEL = "ISLAND MODE: ONE REACTOR POWERS THE PLANT"   # under the date while every line is cut (record `island`)
FONTS = ("/System/Library/Fonts/HelveticaNeue.ttc", "/System/Library/Fonts/Helvetica.ttc")


def render(root: Path, cfg: dict[str, Any], variants: list[str] | None = None,
           seconds: tuple[float, float] | None = None) -> dict[str, Any]:
    sc = export.scene(root, cfg)
    base = export.scene_dir(root, cfg["id"])
    out = base / "animatic"
    o = cfg["crossing3d"]["animatic"]
    fps = int(o["fps"])
    blender = shutil.which("blender")
    if not blender:
        raise RuntimeError("blender isn't on PATH (docs/crossing-3d-plan.txt: a wrapper script in ~/.local/bin)")
    done = {}
    for v in variants or list(o["variants"]):
        n = sc["cameras"][v]
        first, last = (max(1, round(seconds[0] * fps) + 1), min(n, round(seconds[1] * fps))) if seconds else (1, n)
        name = f"{v}_{seconds[0]:g}-{seconds[1]:g}s" if seconds else v
        d = out / name
        if d.exists():
            shutil.rmtree(d)
        t0 = time.time()
        log.info("Rendering %s: frames %d-%d", name, first, last)
        subprocess.run([blender, "-b", "--factory-startup", "-P", str(BUILD), "--",
                        str(base / "scene.json"), str(base / f"camera_{v}.json"), str(d),
                        *([str(first), str(last)] if seconds else ["--blend", str(_blend_path(out, o, v))])],
                       check=True, stdout=subprocess.DEVNULL)
        frames = json.loads((base / f"camera_{v}.json").read_text())["frames"]
        title = name if seconds else o["variants"][v].get("title", v)   # the whole film under its own name, if it has one
        sound = []
        if o["variants"][v].get("record"):  # the two lines' record: the date and their names on screen, the Hum heard
            ro = states.options(cfg["crossing3d"], o["variants"][v])
            _overlay(d, frames, ro, fps)
            wav = out / f"{title}.wav"   # the Hum beside the film, under its name
            _hum(cfg, ro, frames, fps, wav, float(o["variants"][v].get("fade_out_s", o["fade_out_s"])))
            cut = ["-ss", f"{(first - 1) / fps:.3f}", "-t", f"{(last - first + 1) / fps:.3f}"] if seconds else []
            sound = [*cut, "-i", str(wav), "-c:a", "aac", "-b:a", "192k", "-shortest"]
        _fade(d, frames)
        mp4 = out / f"{title}.mp4"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(fps), "-start_number", str(first),
                        "-i", str(d / "f_%04d.png"), *sound, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
                        str(mp4)], check=True)
        if seconds:
            (out / f"{title}.wav").unlink(missing_ok=True)
        _contact(sorted(d.glob("f_*.png")), fps, out / f"{title}_contact.webp")
        done[v] = {"frames": last - first + 1, "seconds": round(time.time() - t0), "mp4": str(mp4)}
    _tidy(out, o)
    if len(done) == 2:  # side by side, the shorter held on its last frame
        a, b = (done[v]["mp4"] for v in done)
        n = max(done[v]["frames"] for v in done)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", a, "-i", b, "-filter_complex",
                        f"[0]tpad=stop_mode=clone:stop={n}[x];[1]tpad=stop_mode=clone:stop={n}[y];"
                        f"[x][y]hstack=2,trim=end_frame={n}", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
                        str(out / "compare.mp4")], check=True)
    return done


def blend(root: Path, cfg: dict[str, Any], variants: list[str] | None = None) -> dict[str, str]:
    """Each variant's scene saved to open in Blender, without rendering (default: the variants with a `title`, the
    segments the film uses)."""
    export.scene(root, cfg)
    base = export.scene_dir(root, cfg["id"])
    out = base / "animatic"
    o = cfg["crossing3d"]["animatic"]
    blender = shutil.which("blender")
    if not blender:
        raise RuntimeError("blender isn't on PATH (docs/crossing-3d-plan.txt: a wrapper script in ~/.local/bin)")
    done = {}
    for v in variants or [v for v, x in o["variants"].items() if x.get("title")]:
        path = _blend_path(out, o, v)
        log.info("Saving %s's scene: %s", v, path)
        subprocess.run([blender, "-b", "--factory-startup", "-P", str(BUILD), "--",
                        str(base / "scene.json"), str(base / f"camera_{v}.json"), str(out / v),
                        "--blend", str(path), "--no-render"], check=True, stdout=subprocess.DEVNULL)
        done[v] = str(path)
    _tidy(out, o)
    return done


def _blend_path(out: Path, o: dict[str, Any], v: str) -> Path:
    return out / f"{o['variants'][v].get('title', v)}.blend"


def _tidy(out: Path, o: dict[str, Any]) -> None:
    """Scene files of variants no longer configured, and every .blend1 backup, removed."""
    keep = {_blend_path(out, o, v).name for v in o["variants"]}
    for f in [*out.glob("*.blend"), *out.glob("*.blend1")]:
        if f.name not in keep:
            log.info("Removing old scene file %s", f.name)
            f.unlink()


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for f in FONTS:
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _boxed(im: Image.Image, xy: tuple[int, int], text: str, font, alpha: float, anchor: str = "la") -> None:
    """White capitals on a black box at half opacity (the 2D film's type), at `alpha`."""
    if alpha <= 0 or not text:
        return
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(layer)
    x0, y0, x1, y1 = dr.textbbox(xy, text, font=font, anchor=anchor)
    pad = 6
    dr.rectangle((x0 - pad, y0 - pad, x1 + pad, y1 + pad), fill=(0, 0, 0, round(128 * alpha)))
    dr.text(xy, text, font=font, anchor=anchor, fill=(255, 255, 255, round(255 * alpha)))
    im.alpha_composite(layer)


def _overlay(d: Path, frames: list[dict[str, Any]], ro: dict[str, Any], fps: int) -> None:
    """The date shown (top left, from the record's start), island mode under it while every line is cut and a reactor
    powers the plant (not a complete loss), and each line's name on its side (from the landing), dimmed while it is cut
    off."""
    font, small = _font(22), _font(16)
    at, names_at = float(ro["at_s"]), float(ro.get("names_at_s", 0))
    until = float(ro.get("names_until_s", math.inf))   # flying south the lines cross ahead: names off before they swap sides
    for i, f in enumerate(frames, start=1):
        t = (i - 1) / fps
        p = d / f"f_{i:04d}.png"
        if not p.exists():   # a stretch rendered alone
            continue
        im = Image.open(p).convert("RGBA")
        W, H = im.size
        date_a = min(1.0, max(0.0, (t - at) / 0.5))
        _boxed(im, (24, 24), states.date_label(f.get("date")), font, date_a)
        _boxed(im, (24, 62), ISLAND_LABEL, small, date_a * float(f.get("island", 0.0)))
        show = min(1.0, max(0.0, (t - names_at) / 1.5), max(0.0, (until - t) / 1.5))
        for key, line in ro["lines"].items():
            on, unknown = (f.get("lines") or {}).get(line["drawn"], (1.0, 0.0))
            left = line["pan"] < 0
            _boxed(im, (24 if left else W - 24, H - 24), line["label"], small, show * (0.35 + 0.65 * on + 0.3 * unknown),
                   anchor="ld" if left else "rd")
        im.convert("RGB").save(p)


def _hum(cfg: dict[str, Any], ro: dict[str, Any], frames: list[dict[str, Any]], fps: int, wav: Path,
         fade_out_s: float) -> None:
    """The Hum for the two lines (hum.py), each panned to its side, fading in and out with the picture."""
    from .. import hum

    rec, _ = states.record(cfg["record"], ro)
    so = ro["sound"]
    total = len(frames) / fps
    pans = {k: float(v["pan"]) for k, v in ro["lines"].items()}
    kvs = {k: int(cfg["record"]["lines"][k][1]) for k in ro["lines"]}
    # the level from the first second with both lines connected
    ts = np.arange(float(so["start_s"]) + float(so["fade_in_s"]), total, 0.1)
    both = np.all([rec.states(k, ts) == "on" for k in ro["lines"]], axis=0)
    i = next(j for j in range(len(ts) - 10) if both[j:j + 10].all())
    x, _ = hum.score(rec, pans, kvs, total, fade_out_s,
                     start_s=float(so["start_s"]), fade_in_s=float(so["fade_in_s"]),
                     follow=(float(so["swell_s"]), float(so["fall_s"])), ref_s=(ts[i], ts[i] + 1.0))
    hum.write_wav(wav, x)


def _fade(d: Path, frames: list[dict[str, Any]], rgb=(255, 255, 255)) -> None:
    """The frames' fade to white (the camera's `fade`), laid on the rendered PNGs."""
    for i, f in enumerate(frames, start=1):
        if f.get("fade") and (d / f"f_{i:04d}.png").exists():
            p = d / f"f_{i:04d}.png"
            im = Image.open(p).convert("RGB")
            Image.blend(im, Image.new("RGB", im.size, rgb), float(f["fade"])).save(p)


def _contact(frames: list[Path], fps: int, path: Path, cols: int = 4, w: int = 480) -> None:
    pick = frames[::max(1, round(CONTACT_EVERY_S * fps))]
    ims = [Image.open(f).convert("RGB") for f in pick]
    h = round(ims[0].height * w / ims[0].width)
    rows = -(-len(ims) // cols)
    sheet = Image.new("RGB", (cols * w, rows * h), (0, 0, 0))
    d = ImageDraw.Draw(sheet)
    for k, (im, f) in enumerate(zip(ims, pick)):
        x, y = k % cols * w, k // cols * h
        sheet.paste(im.resize((w, h), Image.LANCZOS), (x, y))
        i = int(f.stem.split("_")[1])
        d.text((x + 6, y + 4), f"{(i - 1) / fps:5.1f} s", fill=(255, 255, 255))
    sheet.save(path, "WEBP", quality=85)
