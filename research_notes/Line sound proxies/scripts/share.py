"""A storyboard still: how little the last two lines carry (Earshot's Zifzafa idea 3, the tiny share; NEXT.md S4,
5 November 2026).

    python -I share.py <out.jpg>      (from the project root)

One bar, Ukraine's winter peak, and in it what the lines carry into the plant in cold shutdown, drawn to scale:
11-50 MW, about 0.1-0.3% of the peak (Interfax-Ukraine; Ukrainska Pravda, 8 September 2026; reports/Enerhodar
crossing voices and sound.md). No absolute peak is drawn: the share is the sources', the bar only its scale.
"""

import sys

from PIL import Image, ImageDraw, ImageFont

FONT = "/System/Library/Fonts/HelveticaNeue.ttc"
W, H = 1920, 1080
X0, X1, Y = 140, 1780, 560
YELLOW = (255, 205, 60)


def main(out):
    o = Image.new("RGB", (W, H), (0, 0, 0))
    g = ImageDraw.Draw(o, "RGBA")
    f = lambda s: ImageFont.truetype(FONT, s, index=0)
    g.text((X0, 330), "THE LAST TWO LINES NOW CARRY 11 TO 50 MW, INTO THE PLANT", font=f(40), fill=(255, 255, 255))
    g.text((X0, 392), "ABOUT 0.1–0.3% OF UKRAINE'S WINTER PEAK, DRAWN TO SCALE", font=f(20), fill=(215, 215, 215))
    g.rectangle([X0, Y, X1, Y + 70], outline=(255, 255, 255, 120), width=1)
    span = X1 - X0
    g.rectangle([X0, Y, X0 + span * 0.003, Y + 70], fill=YELLOW + (110,))     # 0.3%
    g.rectangle([X0, Y, X0 + span * 0.001, Y + 70], fill=YELLOW)             # 0.1%
    g.text((X0, Y + 92), "0.1–0.3%", font=f(18), fill=(255, 255, 255))
    t = "UKRAINE'S WINTER PEAK, 100%"
    g.text((X1 - g.textlength(t, font=f(18)), Y + 92), t, font=f(18), fill=(255, 255, 255))
    g.text((X0, 760), "THE PLANT'S OWN NEEDS IN COLD SHUTDOWN: ITS COOLING AND SAFETY SYSTEMS",
           font=f(18), fill=(200, 200, 200))
    g.text((X0, 980), "SOURCES: INTERFAX-UKRAINE; UKRAINSKA PRAVDA, 8 SEPTEMBER 2026 · THE PLANT IN COLD SHUTDOWN "
                      "SINCE 13 APRIL 2024 (IAEA)", font=f(13), fill=(160, 160, 160))
    o.save(out, quality=92)


if __name__ == "__main__":
    main(sys.argv[1])
