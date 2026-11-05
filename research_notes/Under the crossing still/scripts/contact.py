"""The v3 contact sheet: every view's renders side by side, labelled (letter, light, a short line).

    python -I contact.py <views.json> <v3_dir> <out.jpg>
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

TILE = (960, 540)
SHORT = {"a": "sand bar SW of tower 20 (the first still's spot)", "b": "forest edge, up at tower 20 over the reeds",
         "c": "in the reeds at the channel, along the span to 21 and 22", "d": "lying under the span 21-22, looking up",
         "e": "water's edge, wide: the forest line, the lit span, Dniprovska tower 24", "f": "meadow between 22 and 23, toward tower 23"}


def font(size):
    for p in ("/System/Library/Fonts/Helvetica.ttc", "/System/Library/Fonts/Supplemental/Arial.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def main(views_json, d, out):
    views = json.load(open(views_json))["views"]
    rows = []
    for v in views:
        for light in ("dawn", "day"):
            f = f"{d}/{v['id']}_{light}.png"
            if os.path.exists(f):
                rows.append((v, light, f))
    cols = 2
    n = len(rows)
    W, H = cols * TILE[0] + (cols + 1) * 16, ((n + cols - 1) // cols) * (TILE[1] + 52) + 16
    sheet = Image.new("RGB", (W, H), (24, 24, 24))
    dr = ImageDraw.Draw(sheet)
    f1, f2 = font(26), font(20)
    for i, (v, light, f) in enumerate(rows):
        x = 16 + (i % cols) * (TILE[0] + 16)
        y = 16 + (i // cols) * (TILE[1] + 52)
        sheet.paste(Image.open(f).convert("RGB").resize(TILE, Image.LANCZOS), (x, y))
        dr.text((x, y + TILE[1] + 8), f"{v['id']}  {light}", font=f1, fill=(240, 240, 240))
        dr.text((x + 110, y + TILE[1] + 12), f"{SHORT.get(v['id'], v['what'])} · {v['lens']:.0f} mm, {v['pitch']:.0f}° up",
                font=f2, fill=(170, 170, 170))
    sheet.save(out, quality=88)
    print(out, sheet.size, n)


if __name__ == "__main__":
    main(*sys.argv[1:4])
