"""A storyboard still: the weather over the crossing against the two lines' record (Earshot's Zifzafa idea 4,
NEXT.md S4, 5 November 2026).

    python -I weather.py <era5.json> <unrolled.json> <out.jpg> <out.json>      (from the project root)

Corona is a wet-weather sound (reports/Enerhodar crossing voices and sound.md): a connected line crackles and hums in
rain, snow and fog and is near silent when dry, whatever it carries. So each day of the record gets its wet hours from
ERA5 (Open-Meteo's archive, models=era5, the 0.25° cell at 47.5 N 34.5 E, hourly, saved verbatim in raw/era5/): an
hour is wet with any precipitation (0.1 mm or more) or, an inference, fog likely (relative humidity at 2 m 97% or more
and wind at 10 m under 3 m/s). Drawn per day above each line's row: white while the record has the line connected
(it would have been loud), grey while cut or not reported line by line (wet but silent). The lines' states are the
unrolled film's (unrolled.json `states`, the record read at the end of each day). A reanalysis is a model of the
weather, not an observation at the line, and the counts say so.
"""

import json
import sys
from datetime import date, datetime, timedelta

from PIL import Image, ImageDraw, ImageFont

FONT = "/System/Library/Fonts/HelveticaNeue.ttc"
W, H = 1920, 1080
X0, X1 = 170, 1800
LINE_RGB = {"on": (255, 205, 60), "off": (120, 124, 130), "unknown": (90, 92, 96)}
ROWS = [("Dniprovska", "DNIPROVSKA · 750 KV", 470), ("Ferosplavna-1", "FEROSPLAVNA-1 · 330 KV", 800)]
BAR_H = 150


def wet_hours(era5):
    h = era5["hourly"]
    out = {}
    for t, p, rh, ws in zip(h["time"], h["precipitation"], h["relative_humidity_2m"], h["wind_speed_10m"]):
        d = datetime.fromisoformat(t).date()
        wet = (p or 0) >= 0.1 or ((rh or 0) >= 97 and (ws if ws is not None else 99) < 3)
        out[d] = out.get(d, 0) + int(wet)
    return out


def main(era5_path, unrolled_path, out, out_json):
    era5 = json.load(open(era5_path))
    u = json.load(open(unrolled_path))
    wet = wet_hours(era5)
    d0, d1 = date(2022, 2, 24), date(2026, 9, 11)
    n = (d1 - d0).days + 1
    px = lambda d: X0 + (X1 - X0) * (d - d0).days / n
    states = {ln["record"]: [(date.fromisoformat(a), date.fromisoformat(b), s) for a, b, s in ln["states"]]
              for ln in u["lines"]}

    def state(name, d):
        return next((s for a, b, s in states[name] if a <= d < b), "unknown")

    o = Image.new("RGB", (W, H), (0, 0, 0))
    g = ImageDraw.Draw(o, "RGBA")
    f = lambda s: ImageFont.truetype(FONT, s, index=0)
    g.text((X0, 80), "WHEN THE LAST TWO LINES WOULD HAVE BEEN LOUD", font=f(34), fill=(255, 255, 255))
    g.text((X0, 132), "HOURS OF RAIN, SNOW OR LIKELY FOG OVER THE CROSSING EACH DAY, AGAINST EACH LINE'S RECORD. "
                      "A CONNECTED LINE CRACKLES WHEN WET, WHATEVER IT CARRIES", font=f(16), fill=(215, 215, 215))
    tally = {}
    for name, label, y in ROWS:
        c = {"on": [0, 0], "off": [0, 0], "unknown": [0, 0]}
        for i in range(n):
            d = d0 + timedelta(days=i)
            s = state(name, d)
            w = wet.get(d, 0)
            c[s][0] += 1
            c[s][1] += int(w > 0)
            x = px(d)
            # the line's state as a ribbon, as the unrolled film draws it
            if s == "on":
                g.rectangle([x, y - 2, x + 1.2, y + 2], fill=LINE_RGB["on"])
            elif s == "off":
                g.rectangle([x, y, x + 1.2, y + 1], fill=LINE_RGB["off"])
            elif i % 4 == 0:
                g.rectangle([x, y, x + 1, y + 1], fill=LINE_RGB["unknown"])
            if w:
                hgt = BAR_H * w / 24
                col = (255, 255, 255, 235) if s == "on" else (110, 110, 110, 200)
                g.rectangle([x, y - 8 - hgt, x + 0.9, y - 8], fill=col)
        tally[name] = {"days": {k: v[0] for k, v in c.items()}, "wet_days": {k: v[1] for k, v in c.items()}}
        g.text((X0, y + 18), label, font=f(18), fill=(255, 255, 255))
        txt = (f"CONNECTED ON {c['on'][0]} DAYS, {c['on'][1]} OF THEM WET · CUT OR NOT REPORTED ON "
               f"{c['off'][0] + c['unknown'][0]} DAYS, {c['off'][1] + c['unknown'][1]} OF THEM WET")
        g.text((X0, y + 46), txt, font=f(15), fill=(200, 200, 200))
    for yr in range(2023, 2027):
        x = px(date(yr, 1, 1))
        for _, _, y in ROWS:      # only through each row's bars, never through its text
            g.line([x, y - BAR_H - 20, x, y + 6], fill=(255, 255, 255, 40), width=1)
        g.text((x + 6, ROWS[0][2] - BAR_H - 22), str(yr), font=f(14), fill=(170, 170, 170))
    g.text((X0, ROWS[0][2] - BAR_H - 22), "24 FEB 2022", font=f(14), fill=(170, 170, 170))
    end = "11 SEP 2026"
    g.text((X1 - g.textlength(end, font=f(14)), ROWS[0][2] - BAR_H - 22), end, font=f(14), fill=(170, 170, 170))

    ky = 960
    g.rectangle([X0, ky + 2, X0 + 2, ky + 16], fill=(255, 255, 255))
    g.text((X0 + 12, ky), "WET WHILE CONNECTED: LOUD", font=f(15), fill=(255, 255, 255))
    g.rectangle([X0 + 280, ky + 2, X0 + 282, ky + 16], fill=(110, 110, 110))
    g.text((X0 + 292, ky), "WET WHILE CUT: SILENT", font=f(15), fill=(255, 255, 255))
    g.text((X0 + 520, ky), "BAR HEIGHT: WET HOURS THAT DAY, OF 24", font=f(15), fill=(255, 255, 255))
    g.text((X0, ky + 34), "WEATHER: ERA5 REANALYSIS (ECMWF, COPERNICUS) VIA OPEN-METEO, ONE 25 KM CELL: A MODEL, NOT "
                          "AN OBSERVATION AT THE LINE. FOG INFERRED FROM HUMIDITY 97%+ AND WIND UNDER 3 M/S. "
                          "STATES: THE RECORD (IAEA, ENERGOATOM)", font=f(13), fill=(160, 160, 160))
    o.save(out, quality=92)
    json.dump({"made": date.today().isoformat(), "cell": [era5["latitude"], era5["longitude"]], "rule":
               "wet hour: precipitation >= 0.1 mm, or relative humidity >= 97% with wind < 3 m/s (fog likely, inferred)",
               "lines": tally}, open(out_json, "w"), indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:5])
