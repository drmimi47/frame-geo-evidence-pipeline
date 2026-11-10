"""The zones' colour palettes and their check (the user, 10 November 2026: "perhaps a better color than white?").

Each palette: the IAEA zones in one hue family (the dome its lightest and most luminous, then the precautionary band,
then the planning band) and Ukraine's observation zone in another hue. Kept away from the lines' two yellows, the old
amber, the water label's muted blue and red (reserved for the front line). The check: CIE76 colour difference (Lab)
between the IAEA zones' middle colour and Ukraine's, and from each reserved colour, with normal vision and simulated
protanopia, deuteranopia and tritanopia (Machado, Oliveira & Fernandes 2009, severity 1.0, in linear RGB); and each
colour's contrast ratio on the slate-graded ground.

    .venv/bin/python -I "research_notes/Tilt-shift opening/zones/scripts/palettes.py"
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

PALETTES = {
    # the first design's colours, chosen by the user over the four below (10 November 2026: "i actually prefer the
    # white color pallete"): the IAEA zones near-white, Ukraine's ring the old amber
    "white": {"dome": "#F0F7FF", "paz": "#ECF0F4", "upz": "#DCE4EC", "obs": "#FADEB2",
              "why": "IAEA near-white, Ukraine a pale amber (the first design)"},
    "ice": {"dome": "#BDF1F5", "paz": "#9BE7EC", "upz": "#5FCBD6", "obs": "#C3A6F5",
            "why": "IAEA a pale ice cyan, Ukraine a soft violet"},
    "lavender": {"dome": "#DCCBFF", "paz": "#C9B6FF", "upz": "#A08BF2", "obs": "#86E3BE",
                 "why": "IAEA lavender, Ukraine mint"},
    "mint": {"dome": "#BEF5DC", "paz": "#93ECC8", "upz": "#52D0A2", "obs": "#E7A9CE",
             "why": "IAEA mint teal, Ukraine a desaturated rose"},
    "rose": {"dome": "#F8C8E2", "paz": "#F2AFD3", "upz": "#D886B8", "obs": "#86DDE8",
             "why": "IAEA a desaturated rose, Ukraine ice cyan"},
}
RESERVED = {"line 750 kV": "#FFD600", "line 330 kV": "#F09C00", "old amber": "#FADEB2", "water label": "#ACCAE0",
            "red (front line)": "#DC2828"}
GROUND = "#5E5E58"   # the slate-graded earth round the plant (mean of the A2 still's middle, after the grade)

MACHADO = {
    "protan": [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]],
    "deutan": [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]],
    "tritan": [[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.303900]],
}


def rgb(h: str) -> np.ndarray:
    return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], float) / 255


def lin(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def unlin(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def lab(c: np.ndarray) -> np.ndarray:
    m = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = m @ lin(c) / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.array([116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])])


def sim(c: np.ndarray, kind: str | None) -> np.ndarray:
    return c if kind is None else unlin(np.array(MACHADO[kind]) @ lin(c))


def de(a: np.ndarray, b: np.ndarray, kind: str | None = None) -> float:
    return float(np.linalg.norm(lab(sim(a, kind)) - lab(sim(b, kind))))


def contrast(a: np.ndarray, b: np.ndarray) -> float:
    la, lb = (float(np.array([0.2126, 0.7152, 0.0722]) @ lin(x)) for x in (a, b))
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def check() -> dict:
    out = {}
    for name, p in PALETTES.items():
        iaea, ukr = rgb(p["paz"]), rgb(p["obs"])
        r = {"iaea_vs_ukraine": {k or "normal": round(de(iaea, ukr, k), 1) for k in (None, "protan", "deutan", "tritan")}}
        near = {}
        for col in ("dome", "paz", "upz", "obs"):
            worst = min(((de(rgb(p[col]), rgb(v), k), f"{rn}{' (' + k + ')' if k else ''}") for rn, v in RESERVED.items()
                         for k in (None, "protan", "deutan", "tritan")))
            near[col] = {"closest_reserved": worst[1], "delta_e": round(worst[0], 1),
                         "contrast_on_ground": round(contrast(rgb(p[col]), rgb(GROUND)), 2)}
        r["per_colour"] = near
        r["min_iaea_vs_ukraine"] = min(r["iaea_vs_ukraine"].values())
        out[name] = r
    return out


if __name__ == "__main__":
    res = check()
    for k, v in res.items():
        print(k, v["iaea_vs_ukraine"], {c: (x["closest_reserved"], x["delta_e"], x["contrast_on_ground"])
                                        for c, x in v["per_colour"].items()})
    Path(__file__).resolve().parents[1].joinpath("palettes.json").write_text(
        json.dumps({"palettes": PALETTES, "reserved": RESERVED, "ground": GROUND, "check": res,
                    "method": __doc__.split("\n\n")[1].replace("\n", " ")}, indent=1))
