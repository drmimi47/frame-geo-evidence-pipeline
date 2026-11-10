"""Section block pass 2: the offset section without the key plan (the block before it shows where it is cut), with
little text: the date, at most one short line, the heights note, and the drawing's own labels (gfilm.py's, fewer).
Two ways from the block's x3 to the section (SCALE):
  ease   the section starts at x3, towers and wires at true size (the block's last frame, exactly), then eases to
         gfilm.py's x10 (towers and sag x10 too: the plan-and-profile convention), said by the heights note;
  x3     the section stays at x3 throughout, towers at true size; the dike's detail, larger, carries the levels.
Its pieces are profile3.py renders (one Blender session for all, `jobs`); drawing here is PIL only (pixels placed,
mixed in a dissolve between two days' drawings, faded).
python gfilm2.py jobs LINE SCALE GF_DIR JOBS.json           write the renders the section needs, as profile3.py jobs
python gfilm2.py film LINE SCALE GF_DIR XF_DIR OUT.mp4 [--sheet SHEET.jpg]     the section alone, from its x3 frame"""
import json, math, subprocess, sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
import cuts as K  # noqa: E402

HN = "/System/Library/Fonts/HelveticaNeue.ttc"
font = lambda n, m=False: ImageFont.truetype(HN, n, index=10 if m else 0)
F_DATE, F_LINE, F_LAB, F_SMALL, F_TINY = font(34, True), font(19), font(15, True), font(15), font(13)
W, H, BALTIC, BOX_A, FPS = 1920, 1080, 0.4, 0.5, 30
DATE = {"A": "6 SEPTEMBER 2022", "B": "27 SEPTEMBER 2025", "C": "23 AUGUST 2026"}
EASE_S, EASE_N = 2.0, 60
GROW_S = 1.6                                  # the detail growing out of its frame                      # the ease x3 -> x10: its length, its rendered steps
DETAIL = {"ease": dict(s0=300.0, s1=2300.0, sc=1300.0, px=4141 / 1920, zc=120.0, ex_g=10, ex_t=10, top=27.0, bot=-6.0),
          "x3": dict(s0=1000.0, s1=1950.0, sc=1475.0, px=K.PX / 12, zc=13.0 * 3, ex_g=3, ex_t=1, top=30.0, bot=-4.0)}


def ease(u):
    u = min(1.0, max(0.0, u)); return 0.5 - 0.5 * math.cos(math.pi * u)


def ease_ex(i):
    """The ease's step i (0..EASE_N): one parameter for both, from (x3, towers true) to (x10, x10)."""
    u = ease(i / EASE_N)
    return 3.0 * (10.0 / 3.0) ** u, 10.0 ** u


def name(gf, k, piece, tag):
    return str(Path(gf) / f"{k}_{piece}_{tag}")


def jobs(line, scale, gf):
    lay = K.layout(line); out = []
    job = lambda k, piece, exg, ext, tag, ortho=K.PX * W, sc=None, zc=K.ZC: dict(
        piece=piece, state=k, ex_g=exg, ex_t=ext, ortho=ortho, s_centre=lay[piece]["mid"] if sc is None else sc, zc=zc,
        png=name(gf, k, piece, tag) + ".png", json=name(gf, k, piece, tag) + ".json")
    final = (10, 10) if scale == "ease" else (3, 1)
    for k in "ABC":
        for piece in ("dike", line):
            out.append(job(k, piece, *final, "final"))
        D = DETAIL[scale]
        out.append(job(k, "dike", D["ex_g"], D["ex_t"], "detail", D["px"] * W, D["sc"], D["zc"]))
    if scale == "ease":
        for i in range(EASE_N + 1):
            exg, ext = ease_ex(i)
            for piece in ("dike", line):
                out.append(job("A", piece, exg, ext, f"e{i:02d}"))
    return out


def dashed(d, xa, xb, y, rgb, a=255, w=1, on=8, off=6):
    x = xa
    while x < xb:
        d.line([(x, y), (min(x + on, xb), y)], fill=(*rgb, a), width=w); x += on + off


def boxed(d, xy, text, f, alpha=1.0, fill=255, pad=(7, 4), anchor="la"):
    if alpha <= 0:
        return
    b = d.textbbox(xy, text, font=f, anchor=anchor)
    d.rectangle((b[0] - pad[0], b[1] - pad[1], b[2] + pad[0], b[3] + pad[1]), fill=(0, 0, 0, int(255 * BOX_A * alpha)))
    d.text(xy, text, font=f, fill=(fill, fill, fill, int(255 * alpha)), anchor=anchor)


def names(d, items, placed):
    for t, x, y in sorted(items, key=lambda it: -it[2]):
        rise = 26
        while True:
            b = d.textbbox((x, y - rise), t, font=F_LAB, anchor="ms"); b = (b[0] - 8, b[1] - 5, b[2] + 8, b[3] + 5)
            if not any(b[0] < o[2] and o[0] < b[2] and b[1] < o[3] and o[1] < b[3] for o in placed):
                break
            rise += 7
        placed.append(b); d.line([(x, y), (x, y - rise + 5)], fill=(235, 235, 235, 200))
        boxed(d, (x, y - rise), t, F_LAB, anchor="ms", pad=(6, 3))


def brk(d, x, top, bot, mid):
    d.line([(x, top), (x, mid - 11), (x + 7, mid - 4), (x - 7, mid + 4), (x, mid + 11), (x, bot)],
           fill=(235, 235, 235, 255), width=2, joint="curve")


class Section:
    def __init__(self, line, scale, gf, xf):
        self.line, self.scale, self.gf = line, scale, Path(gf)
        self.lay = K.layout(line)
        self.ST = {k: {"flat": False, **v} for k, v in json.loads((Path(xf) / "states.json").read_text()).items()}
        self.base, self.over, self._full = {}, {}, {}
        for k in "ABC":
            self.base[k], lab = self.pieces(k, "final")
            self.over[k] = self.overlay(k, lab)
        self.ease = [self.pieces("A", f"e{i:02d}")[0] for i in range(EASE_N + 1)] if scale == "ease" else None
        self.start = self.ease[0] if self.ease else self.base["A"]

    def pieces(self, k, tag):
        """The two pieces laid out as gfilm.py lays them (pixels placed only)."""
        d, c = self.lay["dike"], self.lay[self.line]
        di = Image.open(name(self.gf, k, "dike", tag) + ".png").convert("RGB")
        ci = Image.open(name(self.gf, k, self.line, tag) + ".png").convert("RGB")
        img = Image.new("RGB", (W, H))
        img.paste(di.crop((d["x0"], 0, d["x1"], H)), (self.lay["M"], K.DY))
        img.paste(ci.crop((c["x0"], 0, c["x1"], H)), (c["oxc"], K.DY))
        lab = (json.loads(Path(name(self.gf, k, "dike", tag) + ".json").read_text()),
               json.loads(Path(name(self.gf, k, self.line, tag) + ".json").read_text()))
        return np.asarray(img, np.float32), lab

    def overlay(self, k, lab):
        """What comes in once the section has its final scale, in three parts (the user, 8 November 2026: not all at
        once): "sec" the break lines and what they leave out, the levels, the names and the detail's dashed frame (RGBA);
        then the detail itself, "crop" (RGB), which grows out of that frame ("box") to its place ("rect"); then "dlab"
        its levels and names (RGBA, at its place)."""
        ST, lay = self.ST[k], self.lay; (dl, cl) = lab
        d_, c_ = lay["dike"], lay[self.line]
        M, sd, sc = lay["M"], d_["shift"], c_["shift"]
        y0, y10 = dl["_y"]["0"] + K.DY, dl["_y"]["10"] + K.DY
        Y = lambda h: y0 + (y10 - y0) * h / 10.0
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
        R = c_["oxc"] + (c_["x1"] - c_["x0"])
        if self.scale == "ease":   # at x3 the levels are 2 px apart here: they are read in the detail only
            dashed(d, M, R, Y(12.0 + BALTIC), (235, 235, 235), 230)
            d.text((R + 5, Y(12.0 + BALTIC)), "12 M", font=F_TINY, fill=(235, 235, 235, 230), anchor="lm")
        if not ST["flat"] and self.scale == "ease":
            dashed(d, M, R, Y(16.0 + BALTIC), (140, 140, 140), 200, 1, 4, 6)
            d.text((R + 5, Y(16.0 + BALTIC) - 6), "16 M", font=F_TINY, fill=(160, 160, 160, 220), anchor="lm")
        hb = 30 if self.scale == "ease" else 60     # the break lines' reach (x3: the drawing is lower, so taller)
        brk(d, M, Y(hb), Y(-12 if self.scale == "ease" else -40), Y(13))
        gx = lay["gx"]
        brk(d, gx, Y(hb), Y(-12 if self.scale == "ease" else -40), Y(13))
        d.text((gx, Y(-16 if self.scale == "ease" else -50)), f"≈ {lay['jog_km']:.1f} KM OMITTED", font=F_TINY,
               fill=(225, 225, 225, 240), anchor="mt")
        rv = ST["river_egm"] - BALTIC
        ren = {"RIVER": f"RIVER {rv:.2f} M", "RESERVOIR": f"RESERVOIR {rv:.2f} M"}
        # the pond's and the dike's names only in the detail, and no line's name over the wires (the user, 8 November 2026)
        items = [(n, p[0] + sd, p[1] + K.DY) for n, p in dl.items() if not n.startswith("_") and n not in ("COOLING POND", "DIKE")]
        items += [(ren.get(n, n), p[0] + sc, p[1] + K.DY) for n, p in cl.items() if not n.startswith("_") and " KV" not in n]
        names(d, items, [])
        # the detail: the pond's last stretch, its dike and the bed beyond, larger; the levels read here
        D = DETAIL[self.scale]
        ei = Image.open(name(self.gf, k, "dike", "detail") + ".png").convert("RGB")
        el = json.loads(Path(name(self.gf, k, "dike", "detail") + ".json").read_text())
        xa, xb = 960 + (D["s0"] - D["sc"]) / D["px"], 960 + (D["s1"] - D["sc"]) / D["px"]
        ey0, ey10 = el["_y"]["0"], el["_y"]["10"]
        YE = lambda h: ey0 + (ey10 - ey0) * h / 10.0
        top, bot = YE(D["top"]), YE(D["bot"])
        DX0, DY0 = M, 742 if self.scale == "ease" else 760
        crop = ei.crop((round(xa), round(top), round(xb), round(bot)))
        sec_ov = ov
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)      # the detail's levels and names
        ox, oy = DX0 - xa, DY0 - top
        YD = lambda h: YE(h) + oy
        dw = crop.width
        dashed(d, DX0, DX0 + dw, YD(12.0 + BALTIC), (235, 235, 235), 235, 1)
        d.text((DX0 + dw + 6, YD(12.0 + BALTIC)), "12 M", font=F_TINY, fill=(235, 235, 235, 235), anchor="lm")
        if not ST["flat"]:
            dashed(d, DX0, DX0 + dw, YD(16.0 + BALTIC), (140, 140, 140), 210, 1, 4, 6)
            d.text((DX0 + dw + 6, YD(16.0 + BALTIC)), "16 M", font=F_TINY, fill=(170, 170, 170, 230), anchor="lm")
        pa, pb = max(el["_pond"][0] + ox, DX0), min(el["_pond"][1] + ox, DX0 + dw)
        for p in ST["past"]:
            d.line([(pa, YD(p + BALTIC)), (pb, YD(p + BALTIC))], fill=(150, 150, 150, 210), width=1)
        placed = []
        if ST["past"]:   # at the pond's right end, kept clear of the names
            xy = (pb - 6, YD(max(ST["past"]) + BALTIC) - 4)
            d.text(xy, "EARLIER REPORTS", font=F_TINY, fill=(170, 170, 170, 230), anchor="rs")
            bb = d.textbbox(xy, "EARLIER REPORTS", font=F_TINY, anchor="rs"); placed.append((bb[0] - 4, bb[1] - 4, bb[2] + 4, bb[3] + 4))
        ren_d = {"COOLING POND": f"COOLING POND {ST['pond_baltic']:.2f} M", **ren}
        dl_ = []
        for n, p in el.items():
            if n.startswith("_"):
                continue
            x = p[0] + ox
            if n == "COOLING POND" and not DX0 + 40 < x < DX0 + dw - 40:
                x = (pa + pb) / 2                      # on the stretch of pond the detail shows
            if DX0 + 40 < x < DX0 + dw - 40:
                dl_.append((ren_d.get(n, n), x, p[1] + oy))
        names(d, dl_, placed)
        # where the detail is in the section: a dashed frame round that stretch (the same stretch and heights), no words
        d = ImageDraw.Draw(sec_ov)
        sx = lambda s: 960 + (s - d_["mid"]) / K.PX + sd
        fx0, fx1, fy0, fy1 = sx(D["s0"]), sx(D["s1"]), Y(D["top"]), Y(D["bot"])
        for yy in (fy0, fy1):
            dashed(d, fx0, fx1, yy, (200, 200, 200), 220, 1, 4, 4)
        for xv in (fx0, fx1):
            yv = fy0
            while yv < fy1:
                d.line([(xv, yv), (xv, min(yv + 4, fy1))], fill=(200, 200, 200, 220)); yv += 8
        return {"sec": sec_ov, "crop": crop, "box": (fx0, fy0, fx1, fy1), "rect": (DX0, DY0, DX0 + dw, DY0 + crop.height),
                "dlab": ov}

    def drawing(self, k, a=1.0, g=1.0, b=1.0):
        """Day k's section (float RGB): its labels and dashed frame at alpha a; the detail at g along its way out of
        the frame (0 the frame, 1 its place; None not yet there); the detail's labels at alpha b."""
        full = a >= 1 and g is not None and g >= 1 and b >= 1
        if full and k in self._full:
            return self._full[k]
        if a <= 0:
            return self.base[k]
        o = self.over[k]
        im = Image.alpha_composite(Image.fromarray(self.base[k].astype(np.uint8)).convert("RGBA"), _alpha(o["sec"], a))
        if g is not None:
            # the detail grows out of its frame: one rectangle eased from the frame to its place (the same stretch and
            # heights, three times larger), the pixels only scaled; it fades in over the first 0.15 of the way
            e = ease(g)
            r = [u + (v - u) * e for u, v in zip(o["box"], o["rect"])]
            cw, ch = o["crop"].size
            sxk, syk = (r[2] - r[0]) / cw, (r[3] - r[1]) / ch
            src = o["crop"].convert("RGBA")
            mv = src.transform((W, H), Image.AFFINE, (1 / sxk, 0, -r[0] / sxk, 0, 1 / syk, -r[1] / syk), Image.BICUBIC,
                               fillcolor=(0, 0, 0, 0))
            ImageDraw.Draw(mv).rectangle((round(r[0]) - 1, round(r[1]) - 1, round(r[2]), round(r[3])),
                                         outline=(110, 110, 110, 255))
            im = Image.alpha_composite(im, _alpha(mv, min(1.0, g / 0.15)))
            if b > 0:
                im = Image.alpha_composite(im, _alpha(o["dlab"], b))
        out = np.asarray(im.convert("RGB"), np.float32)
        if full:
            self._full[k] = out
        return out


def _alpha(ov, a):
    if a >= 1:
        return ov
    ov = ov.copy(); ov.putalpha(Image.fromarray((np.asarray(ov)[..., 3] * max(0.0, a)).astype(np.uint8)))
    return ov


# ---- the section's own timeline, from its first frame (the block's last): seconds
def plan(scale):
    t = 0.0; P = []
    P.append(("x3", t, t + 0.4)); t += 0.4
    if scale == "ease":
        P.append(("ease", t, t + EASE_S)); t += EASE_S
    P.append(("in", t, t + 0.9)); t += 0.9          # the section's labels and the detail's dashed frame
    P.append(("grow", t, t + GROW_S)); t += GROW_S  # the detail grows out of its frame to its place
    P.append(("dlab", t, t + 0.6)); t += 0.6        # then its levels and names
    for i, k in enumerate("ABC"):
        hold = {"A": 3.6 - GROW_S - 0.6, "B": 4.0, "C": 5.0}[k]   # day A seen as long as before, from "in"
        P.append((k, t, t + hold)); t += hold
        if k != "C":
            P.append((k + ">" + "ABC"[i + 1], t, t + 2.0)); t += 2.0
    P.append(("out", t, t + 1.2)); t += 1.2
    return P, t


NOTE = {"x3": "HEIGHTS x3 · TOWERS AND WIRES AT TRUE SIZE", "x10": "HEIGHTS x10 · TOWERS AND WIRES x10"}


def note_at(scale, t, P):
    if scale == "x3":
        return NOTE["x3"]
    for k, t0, t1 in P:
        if k == "ease" and t0 <= t < t1:
            i = min(EASE_N, int(round((t - t0) / (t1 - t0) * EASE_N)))
            g, tw = ease_ex(i)
            return NOTE["x3"] if i == 0 else f"HEIGHTS x{g:.0f} · TOWERS AND WIRES x{tw:.0f}"
        if k == "ease" and t < t0:
            return NOTE["x3"]
    return NOTE["x10"]


def frame(sec, t, P, total):
    """The section at t (its own clock): (picture float RGB, date text, one short line or None, heights note)."""
    for k, t0, t1 in P:
        if t0 <= t < t1 or (k == "out" and t >= t0):
            break
    if k == "x3":
        pic, day = sec.start, "A"
    elif k == "ease":
        i = min(EASE_N, int(round((t - t0) / (t1 - t0) * EASE_N))); pic, day = sec.ease[i], "A"
    elif k == "in":
        pic, day = sec.drawing("A", ease((t - t0) / (t1 - t0)), None), "A"
    elif k == "grow":
        pic, day = sec.drawing("A", 1.0, (t - t0) / (t1 - t0), 0.0), "A"
    elif k == "dlab":
        pic, day = sec.drawing("A", 1.0, 1.0, ease((t - t0) / (t1 - t0))), "A"
    elif ">" in k:
        a, b = k.split(">"); w = ease((t - t0) / (t1 - t0))
        pic = sec.drawing(a, 1) * (1 - w) + sec.drawing(b, 1) * w
        return pic, f"{DATE[a]} – {DATE[b]}", "A DISSOLVE BETWEEN TWO DAYS' DRAWINGS, NOT AN OBSERVATION", note_at(sec.scale, t, P)
    elif k == "out":
        pic = sec.drawing("C", 1) * (1 - ease((t - t0) / (t1 - t0))); day = "C"
    else:
        pic, day = sec.drawing(k, 1), k
    return pic, DATE[day], None, note_at(sec.scale, t, P)


def texts(img, date, line, note, alpha=1.0, note_a=1.0):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    boxed(d, (60, 52), date, F_DATE, alpha)
    if line:
        boxed(d, (60, 104), line, F_LINE, alpha)
    if note:
        boxed(d, (60, 1012), note, F_SMALL, alpha * note_a, fill=225)
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")


TYPE_X = 0.7                                  # the type crossfades over this at each change of day or dissolve


def typed(sec, t, P, total, alpha=1.0):
    """The section at t with its type, the type crossfaded at each boundary of a dissolve (it popped on and off in a
    frame: the user, 8 November 2026, "no glitching")."""
    pic, date, line, note = frame(sec, t, P, total)
    img = Image.fromarray(np.clip(pic, 0, 255).astype(np.uint8))
    here = texts(img, date, line, note, alpha)
    for k, t0, t1 in P:
        if ">" not in k:
            continue
        for bd in (t0, t1):
            if abs(t - bd) < TYPE_X / 2:
                _, d0, l0, n0 = frame(sec, bd - 1e-4, P, total)
                _, d1, l1, n1 = frame(sec, bd + 1e-4, P, total)
                w = ease((t - (bd - TYPE_X / 2)) / TYPE_X)
                a0 = np.asarray(texts(img, d0, l0, n0, alpha), np.float32)
                a1 = np.asarray(texts(img, d1, l1, n1, alpha), np.float32)
                return Image.fromarray((a0 * (1 - w) + a1 * w + 0.5).astype(np.uint8))
    return here


def ffmpeg(out, fps=FPS):
    return subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                             "-r", str(fps), "-i", "-", "-c:v", "libx264", "-crf", "16", "-preset", "slow",
                             "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)], stdin=subprocess.PIPE)


if __name__ == "__main__":
    mode, line, scale = sys.argv[1], sys.argv[2], sys.argv[3]
    if mode == "jobs":
        Path(sys.argv[5]).write_text(json.dumps(jobs(line, scale, sys.argv[4]), indent=0)); print(len(jobs(line, scale, sys.argv[4])), "jobs")
    else:
        gf, xf, out = sys.argv[4], sys.argv[5], Path(sys.argv[6])
        sec = Section(line, scale, gf, xf); P, total = plan(scale)
        ff = ffmpeg(out)
        for f in range(int(round(total * FPS))):
            fade = min(1.0, max(0.0, (total - f / FPS) / 1.2))
            ff.stdin.write(np.asarray(typed(sec, f / FPS, P, total, fade)).tobytes())
        ff.stdin.close(); ff.wait(); print("wrote", out, f"{total:.1f} s", P)
