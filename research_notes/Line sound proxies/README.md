# Line sound proxies, and what follows from Earshot's *Zifzafa* (5 November 2026)

Five storyboard pieces from the user's pick of the ideas drawn from Earshot's *Zifzafa* (one wind turbine's sound
across a region, and someone simply recording it): 1 and 2 first, then 3, 4 and 5 (not 6, 7 or 8). Storyboard material,
not evidence: every figure below is either a source's or an estimate said to be one. NEXT.md S4 carries what is left.

## 1. The proxies: someone else's recording of a line of the same class

No recording of Dniprovska or Ferosplavna-1 is known (reports/Enerhodar crossing voices and sound.md). These stand in,
said on screen to be recorded elsewhere, never passed off as the lines' own sound.

- `proxy-750kV-fog.mp4` (40 s, from 4:05 of the original): **3P61XgO8OXM**, "ЛЭП 750 кв в тумане Треск проводов",
  Ted3871, uploaded 20 September 2023; the description's only words "электроэнергетика, осень, 2021 год" (so autumn
  2021, the uploader's own word); place not given. A walk along a foggy track to Soviet portal towers with bundled
  conductors, a 750 kV class line. **Standard YouTube licence: permission needed before any public screening.**
- `proxy-330kV-crossing.mp4` (34 s, whole): **EnMMoi6IY-Y**, "Пересечение ЛЭП 330 кВ [01]", Dmitry Novoklimov,
  filmed 9 May 2012 (his description), location "ДНЕПР", uploaded 9 May 2020; **CC BY** (credit him). Lattice towers
  against a spring sky; the hum fainter, with wind.
- Checked by ear and spectrum (8 kHz mono, 5 s windows): both have the corona's tone at **100 Hz** (twice Ukraine's
  50 Hz), 16.9 dB over its neighbours in the 750 kV (200 Hz 13.7 dB), 16.5 dB in the 330 kV (200 Hz 28.7 dB, and a
  50 Hz line at 20.4 dB, which may be the camera's own). The 750 kV crackle (1.5-3.8 kHz) is loudest at 3:30-5:05 of
  the original, the hum strongest at 4:20-5:00: the clip is taken there. The 330 kV's high band is steady and partly
  wind.
- Made by `scripts/proxy_clip.py`: cut, scaled 1.5x (Lanczos), placed smaller than the frame on black; the sound as
  recorded with half-second fades; three lines of text under it. The downloads are in `raw/` (gitignored, with each
  video's yt-dlp info.json).
- Other candidates looked at: dTnBrhR9NaQ (a 750/330 kV substation near Vinnytsia, 2013, damp), imH7uefbsYk
  (Novoklimov, CC BY, a 330 kV substation's hum), WopU7JXaly8 and vElauZlZqFA (US 765 kV).

## 2. The footprint: where the last two lines can be heard

`footprint_2024-03-22.jpg`, on the zoom-out's own frame at 128 s (48 km wide, 22 March 2024, both lines connected),
by `scripts/footprint.py`. Round each line three bands, **an estimate from other lines' measurements, never measured
here**: dry, a faint crackle to about 140 m (BAPE: 25 dBA or less 100 m beyond a 735 kV right of way); rain or fog,
about 0.4 km (Hydro-Québec's 53 dBA at 40 m and about 40 dBA at 140 m, that fall carried on to a quiet night's 30 dBA,
assumed); a still wet night at most 1.4 km (spreading as a line source only, an upper bound). The 330 kV dashed, with
the 750 kV's figures as an upper estimate (TransGrid/WSP measured 25-60 dBA in rain at 330 kV with no clear trend).
Towns: km from their GeoNames point (centre) to the nearest of the two lines, measured on the film's plane: Nikopol
5.3 km (to Ferosplavna-1's end by the Ferosplavna substation; the crossing is farther), Marhanets 1.5 km, Enerhodar 2.9
km. Their edges reach closer than their centres: the beat "Nikopol cannot hear the lines" holds for the crossing, not
for every street of the town.

## 3. The share: how little they carry

`share_card.jpg` (`scripts/share.py`): one bar, Ukraine's winter peak, and in it the 11-50 MW the lines carry into the
plant, about 0.1-0.3% (Interfax-Ukraine; Ukrainska Pravda, 8 September 2026), drawn to scale (1.6-4.9 px of 1640). No
absolute peak is drawn.

## 4. The weather: when they would have been loud

`weather_2022-2026.jpg` and `weather_2022-2026.json` (`scripts/weather.py`). ERA5 reanalysis from Open-Meteo's archive
(`models=era5`, the 0.25° cell at 47.5 N 34.5 E, hourly, 24 February 2022 to 11 September 2026, saved verbatim in
`raw/era5/`). A wet hour: 0.1 mm or more of precipitation, or (inferred) fog likely: relative humidity 97% or more with
wind under 3 m/s. Against each line's record day by day (the unrolled film's `unrolled.json` states):

| | connected | of them wet | cut or not reported | of them wet |
|---|---|---|---|---|
| Dniprovska | 1,253 days | 594 | 408 | 206 |
| Ferosplavna-1 | 913 days | 431 | 748 | 369 |

A model of the weather on a 25 km grid, not an observation at the line; the still says so.

## 5. The soundscape: where the region's birds were recorded

`soundscape.jpg`, `soundscape.json`, and `soundscape-nightingale.mp4` (the still with 30 s of the song), by
`scripts/soundscape.py`, on the 3D film's 10 m crop of the Sentinel-2 pass of 28 August 2025 (the zoom-out's own pass;
only scaled and dimmed by the film's 0.8).
- iNaturalist, observations with sounds in the box 47.30-47.80 N, 34.05-35.10 E (`raw/inat/`, the API's two pages as
  fetched): **116 recordings, 2022-2026, all by one recordist (uabird, CC BY-NC), all round Marhanets, north of the
  bed; none from the drained bed or the occupied bank; 2.2-6.2 km from the lines, outside the footprint's widest band.**
  Drawn as one dot per 1 km cell, never at a recording's own place: one person's points round a frontline town could
  give away a home.
- The song: **xeno-canto XC1016141**, a thrush nightingale (Luscinia luscinia), Ekaterina Kormina, 16 April 2025, near
  Marhanets, 60 s, **CC0** (public domain dedication), background a blue tit (`raw/xc/`, the page and the mp3 as fetched).
  Xeno-canto's API v2 is retired (v3 needs a key); the page gave the metadata.
- CC BY-NC (iNaturalist's) is non-commercial: fine for a festival or academic screening, to be asked about for anything
  else.

## 6. The two classes measured, for the Hum (9 November 2026)

`kv/compare_kv.json` (`scripts/compare_kv.py`): the 750 kV proxy as the cut plays it (0-24 s) and the 330 kV proxy as
its parked shot plays it (0-16 s), side by side. Two recordings, different microphones, distances and weather (fog
against dry spring air with wind): a direction and rough sizes, never a calibration.
- The hum: the 750 kV's tone at 100 Hz (15.8 dB over its neighbours) and 200 Hz (14.6), 300 Hz weaker (7.3), nothing
  above; the 330 kV's 200 Hz (20.7) over its 100 Hz (13.0), with 300, 400 and 600 Hz clearly there (11.4, 10.0, 9.3).
- The crackle (2-8 kHz): the 750 kV's impulsive (kurtosis 11, 19 at 8-16 kHz; a Gaussian hiss is 3), reaching 16 kHz
  (8-16 kHz only 0.7 dB under the 1.5-8 kHz band), its envelope pulsing once a cycle (50 Hz) more than twice; the
  330 kV's a smoother hiss (kurtosis about 4, partly wind), falling 10.5 dB above 8 kHz, pulsing at 100 Hz.
These set the shapes of hum.py's two voices (`HUM_SHAPE`, `CORONA`); the levels are the literature's and design
choices (said there). `kv/zoomout/`: the zoom-out's Hum before and after (spectrograms, zoomout_check.json: -14.0
LUFS integrated, was -14.1; picture copied, byte-identical; 41 dates shown with wet hours, 19 of them a full swell).
The ERA5 series used by the Hum is copied to the network's `weather/` folder (provenance.json there).
