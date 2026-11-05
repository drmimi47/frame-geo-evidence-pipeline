"""Distant birds for the v5 shot `under-the-crossing` (v3's view f by day): birds_v4's species, shapes and flight
(sources in v4.json and v5.json), with paths composed again for this framing: all in the open sky right of the lit
span (x about 1170-1920, above the reeds), never in front of tower 23, the Dniprovska tower beyond it or any wire
(checked against this view's `mask.npy` by `check`, a 28 px margin). Drawn, not observed.

    python -I birds_v5.py check <mask.npy> <still.png> <out.png>
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import birds_v4 as BI  # noqa: E402

HAZE_RGB = (0.62, 0.66, 0.70)        # the film's day haze (linear; the scene's world and its materials' haze)


def srgb(c):
    return round(255 * (12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055))


BI.CAM = dict(lens=18.0, pitch=14.0)          # v3's view f
BI.HAZE = tuple(srgb(c) for c in HAZE_RGB)     # birds tinted toward the day haze with distance (a drawn haze)
BI.GROUPS = [
    dict(id="bee-eaters", species="bee-eater", t0=1.0,
         screen=[(2000, 380, 55), (1720, 330, 60), (1480, 290, 66), (1330, 220, 70), (1400, 140, 72),
                 (1620, 120, 68), (2350, 200, 62)],
         members=[(0, 0, 0, 0), (-2.5, 1.8, 0.6, 0.35), (-4.0, -2.2, -0.8, 0.6), (-6.5, 0.8, 1.4, 1.0)]),
    dict(id="gull", species="gull", t0=3.0,
         screen=[(1560, -40, 170), (1480, 100, 160), (1400, 230, 165), (1450, 330, 175), (1600, 350, 185),
                 (1700, 260, 190), (1660, 140, 195), (1580, 40, 200), (1540, -60, 210)],
         members=[(0, 0, 0, 0)]),
    dict(id="cormorants", species="cormorant", t0=6.0,
         screen=[(2020, 420, 280), (1760, 400, 300), (1570, 370, 330), (1470, 320, 380), (1520, 250, 440),
                 (1720, 210, 500), (2080, 190, 560)],
         members=[(0, 0, 0, 0), (-3.5, -2.4, 0.2, 0.2), (-7.0, -4.8, 0.4, 0.4), (-10.5, -7.2, 0.6, 0.6),
                  (-14.0, -9.6, 0.5, 0.8)]),
    dict(id="gull far", species="gull", t0=11.0,
         screen=[(2000, 60, 420), (1800, 90, 430), (1600, 140, 450), (1460, 170, 470), (1330, 120, 480),
                 (1290, -60, 500)],
         members=[(0, 0, 0, 0)]),
    dict(id="bee-eaters later", species="bee-eater", t0=16.0,
         screen=[(2000, 140, 58), (1760, 90, 62), (1520, 110, 66), (1420, 180, 70), (1540, 250, 72),
                 (1800, 240, 68), (2100, 260, 62)],
         members=[(0, 0, 0, 0), (-2.2, -1.6, 0.5, 0.4), (-4.5, 1.4, -0.4, 0.9)]),
]

if __name__ == "__main__":
    if sys.argv[1] == "check":
        BI.check(*sys.argv[2:5])
