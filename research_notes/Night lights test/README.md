# Night lights test (NEXT.md N2), 2 November 2026

What NASA's Black Marble night lights show around the plant, Enerhodar and the two banks, 2019-2026. A test, not yet
part of the film: nothing here is in the storyboard or a film.json.

## Findings

1. **The night of 8-9 September 2022: the town went dark, the plant stayed lit.** At about 03:30 Kyiv time on
   9 September, Enerhodar's lights read 0.1 nW/cm²/sr (brightest pixel 1.1), against 6-8 on every other clear night
   from 23 August to 15 September (brightest pixels 26-36). The sky over the town was clear, quality flags good, the
   moon near full. The plant's own site, 6 km west, stayed lit. Nearby towns read as on other nights, so the dark is
   local. On 9 September the IAEA's Director General said shelling of the switchyard at Enerhodar's thermal power
   plant had caused a "complete power black-out" in the city, which had developed the night before
   ([Al Jazeera, 9 Sep 2022](https://www.aljazeera.com/news/2022/9/9/shelling-near-zaporizhzhia-plant-unsustainable-iaea-says);
   [RFE/RL](https://www.rferl.org/a/iaea-zaporizhzhya-blackout-ukraine-shelling-russia/32026246.html)).
   By the next clear night (11-12 September) the town was lit again.
   Why the plant stayed lit: Energoatom said shelling cut its last line to the grid (330 kV, to Ferosplavna) on
   5 September, and unit 6 ran on its own ("island mode", 114-140 MW for the plant's own needs) until grid power came
   back on the evening of 10 September; unit 6 was shut down at 03:41 on 11 September
   ([Rubryka, 5 Sep 2022](https://rubryka.com/en/2022/09/05/na-zaes-vidimknulas-ostannya-liniya-yaka-z-yednuvala-stantsiyu-z-energosystemoyu-ukrayiny-energoatom/);
   [Ukrinform](https://www.ukrinform.net/rubric-economy/3565030-znpps-power-unit-no6-disconnected-from-ukraines-power-grid.html)).
   The film's record does not have this yet: it shows Dniprovska cut and the 330 kV lines grey (unreported) through
   5-10 September, not every line cut; fixed in the config (NEXT.md D3), in the films at the next render.
   See `sep2022_enerhodar_blackout.png` (7-8, 8-9 and 11-12 September side by side) and `sep2022_chart.png`.
2. **From March 2022 the Ukrainian bank went dark and the occupied bank stayed lit.** Nikopol: 18.5 in February 2022,
   0.8 in March. Pokrov and Marhanets the same. Even Dnipro, far from the front, fell from about 54 to about 1-6, so it
   is wartime light discipline across government-held Ukraine, not the front alone. Occupied Melitopol stayed at about
   14-17 until March 2026, Simferopol (Crimea) brightened. Enerhodar held at 6-9 into early 2024, apart from November-December 2022 (about 3).
3. **From 2024 Enerhodar went dark too, before the rest of the occupied south.** About 6.5 in March 2024, 1.6 in
   September 2024, about 1 through 2025, while Melitopol stayed lit. Partly explained: drone strikes cut the town's
   power in October 2024 ([Bluewin/Keystone-SDA, 22 Oct 2024](https://www.bluewin.ch/en/news/international/occupied-enerhodar-without-electricity-after-kiev-drone-strikes-li.2415929)).
   Not fully explained yet: an open question.
4. **Summer 2026: the whole occupied south dims.** Melitopol 16 in March 2026, 1-2 in July, near 0 in September;
   Simferopol halves. Enerhodar 0.08 in July and 0.0 in September 2026. Reported: Ukrainian drone strikes on substations
   cut power to nearly a million people in the occupied regions
   ([Moscow Times, 31 Jul 2026](https://www.themoscowtimes.com/2026/07/31/ukrainian-drone-strikes-cut-power-to-nearly-1m-people-in-occupied-regions);
   Crimea's region-wide blackout, [Moscow Times, 6 Jul 2026](https://www.themoscowtimes.com/2026/07/06/regionwide-blackout-hits-crimea-after-ukrainian-strikes-a93169/pdf)).
   Texty.org.ua published a satellite analysis of these blackouts
   ([Texty](https://texty.org.ua/articles/118222/usf-disabled-267-power-nodes-in-occupied-territories-blackouts-visible-from-space/)):
   a reference and a check on this method.
5. **The plant outshines its town again at the end.** Plant site (within 1 km) against Enerhodar: July 2026 4.1
   against 0.08; September 2026 1.6 against 0.0 (the month of the 18 days on diesel, 20 August-7 September, and the
   reconnection after it). The site dims from 2024 too, but it never goes out the way the town does.

In one line for the film: in 2022 the river divided a dark bank from a lit one; by 2026 both banks are dark, and the
plant's site is one of the last lights on.

## Checks that make it trustworthy

- **Two satellites agree.** The same months from Suomi NPP (VNP46A3) and NOAA-20 (VJ146A3) match within normal
  scatter (`monthly_two_satellites.csv`), so the darkening is not the ageing Suomi NPP drifting.
- **Far controls.** Melitopol and Simferopol (occupied, far), Dnipro and Zaporizhzhia (Ukrainian-held): the 2022 drop
  is on the Ukrainian side everywhere; the 2024 drop is Enerhodar's own; the 2026 drop is the occupied south's.
- **The pass time read from the data,** not assumed: the at-sensor product (VNP46A1, UTC_Time) gives 00:48 and 00:29
  UTC over Enerhodar on 8 and 9 September 2022, so each daily file shows the early hours (about 03:30 Kyiv) of its
  own date.

## Limits (say them if any of this reaches the film)

- Pixels are about 460 × 310 m: the plant's site and Enerhodar are separate, but a building or a street is not.
- Clear skies only: most nights are cloudy (dark red in the images: no good-quality value, never filled). June has
  no data at all (short nights). Snow months use the snow-covered composite, which reads brighter.
- Brightness is not electricity. A dark town can be a blackout, a curfew, light discipline, or people gone; a source
  must say which. The satellite shows when and where, never why.
- The drained reservoir shows as a large "no good-quality value" shape from 2023: a quirk of NASA's quality flags
  where the water was, not darkness.
- Town values are the mean within 2 km of the GeoNames point (the plant: 1 km round its OSM position). A point is
  left blank if under 80% of those pixels are usable.
- Only good-quality pixels: Mandatory_Quality_Flag 0/1 and a clear cloud mask (daily), quality 0 (monthly). The
  Gap_Filled layers are never used.

## Data and files

- NASA Black Marble, Collection 2 (LAADS DAAC, Earthdata Login; the user accepted LAADS's licence on 2 Nov 2026):
  VNP46A2 daily, tile h21v04, 23 Aug-15 Sep 2022; VNP46A1 for 8-9 Sep 2022 (pass times); VNP46A3 monthly, 33 months
  2019-2026; VJ146A3 (NOAA-20) monthly, 10 months. Raw files kept (about 690 MB, gitignored) in `libraries/conductive-seam/satellite/nightlights/blackmarble/`, with `provenance.json` (each file's granule and sha256). Also VNP46A3 for September 2021, 2022 and 2026 over the zoom-out's whole 172 km frame (`frame_VNP46A3/`).
- `sep2022_*`: the daily test. `monthly_*`: the monthly series and the two-satellite check.
- `scripts/`: how it was made (Python, h5py; the token is read from .env and only sent in the request header).

## Legibility test: the zoom-out's 172 km frame (NEXT.md N2)

`frame172_2021-09.png`, `frame172_2022-09.png`, `frame172_2026-09.png` (and `frame172_triptych.png`): the zoom-out as
configured, its camera held at the settled 172 km frame, the daylight pass dimmed to a faint map and the month's
Black Marble pixels laid on it as they are (nearest neighbour, never smoothed). Made by `scripts/stills172.py`.

- **It reads at this scale.** A pixel is 3-5 screen pixels: the towns are soft blocks, not noise. The two banks show
  at a glance: in September 2021 both lit; in September 2022 Nikopol, Marhanets and the north bank dark, Enerhodar and
  the occupied south still lit; in September 2026 nearly everything dark but Zaporizhzhia city.
- **The plant's own light doesn't read here.** In 2026 its site (about 1.6 nW) is one faint block under the plant's
  mark. "The plant is one of the last lights on" needs a closer frame (about 30-40 km) or a moment of its own.
- **No data must not be red.** From 2023 the drained reservoir has no good-quality value (NASA's flags, not darkness);
  drawn dark red it reads as a signal and clashes with the "cut off" red of the lines. In the film: a neutral hatch,
  said in the legend.
- **A month under a day.** The lights are the month's composite, the record a day: the label must say the month (and
  "the month's clear nights"), never imply that night.
- The lines and labels cover some towns; a night-lights beat may want the lines dimmed, or its own moment.

## What it could become (N3)

- Not the 3D "light difference" first imagined: at this resolution a 3D surface would mostly show noise.
- A two-bank sequence: the river between a dark bank and a lit one in 2022, then both dark by 2026, the plant's
  site still lit. Monthly maps (`monthly_maps.png`) are the raw material; the drawing would say what is measured.
- The night of 8-9 September 2022 as a held moment in the record: the town dark, the plant lit, with the IAEA's words.
