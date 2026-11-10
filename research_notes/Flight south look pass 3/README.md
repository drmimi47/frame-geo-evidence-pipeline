# Flight south, look pass 3 (7 November 2026)

A new variant, `south_look3`, beside the approved `south_record`, `south_look1` and `south_look2` (the plan approved by
the user, 7 November 2026). It is shorter and paced again: the record is shown on selected dates, the flight ends
over the Enerhodar bank with a straight lift, and the look is fixed (the river, its edge, the plants). Output, beside
the others:
`libraries/conductive-seam/satellite/networks/znpp/scenes/crossing3d/animatic/ZNPP-last-two-lines-3D-south-look3.mp4`
(.wav, .blend, _contact.webp). How to follow, pause and resume the render: RESUME.md.

**The curve toward the units is left out of this film.** It is to be a separate short render for the cooling chapter
(south_look2's track from 3.2 km north on, with the plant), not part of this flight.

## How it is built (options of the variant; the approved films render as before)

- Config: `crossing3d.animatic.variants.south_look3` in config/conductive-seam.yaml (south_look2's look plus what is
  below). Nothing shared was changed.
- `scene3d/states.py`: `day_states` (each line's state on a day by the network record's rules), `Selected` (the
  record on selected dates; the methods the 3D uses of Record), `SELECT_STATEMENT`, `flow_config` (a variant's own
  `flow_periods` before the shared ones). `record()` uses `Selected` only when the options have `select`.
- `scene3d/camera.py`: `frames_track` with no `end_xy_m` flies straight down the axis (the keys by `north_km` only; a
  `curve` or `beyond_m` key is refused).
- `scene3d/export.py`: a selected date with `along_m` is checked against the camera (within 100 m, the camera's along
  recorded); the flow by `flow_config`; `vegetation.track_from` (the plants placed along another variant's track: the
  same cache, so look3's plants are look2's); `_sheets_edge` and the look docs `water_edge` and `water_variation`.
- `scene3d/look.py`: `edge_field`, `edge_tolerance`, `water_edge`, `water_variation`.
- `scene3d/build.py`: `_water_detail` (the drawn surface), `_water_var`, `_edge_clip`, `_plant_tone`, the
  `far_plain.hole`, `rays` options, a keyed "water time". Every option off by default.
- `hum.py`: `score(..., island_level=None)` (the island's low note, set by the variant's `sound.island_level`).
- Tests: tests/test_look3.py (6: a day's state, the selection, refusals, the days' easing and running on, the flow
  periods, the edge tolerance) and a straight-track test in tests/test_scene3d.py. The whole suite passes (179
  passed, 1 skipped).
- Checked that the approved films are unchanged: after the last export with the new code, towers.npz,
  towers_detail.npz, camera_south_record.json, camera_south_look1.json, camera_south_look2.json, camera_axis2k.json,
  camera_axis2k_record.json, water.npz, terrain.npz, others.npz, vegetation.npz and vegetation.json are byte-identical
  to the backups made before the changes.

## 1. Pacing and camera

- Cruise 95 m/s (look2: 80). The opening as it was: from white, 300 m up at 45 m/s, down to 70 m by 8.6 km north
  (level flight from 14.9 s).
- No curve: straight on down the axis. The lift begins where look2's rise began (3.2 km north, 74.3 s) and climbs to
  320 m by 1.5 km north, pitch -7° to -9°, at the same speed; a 5 s fade to white. 93.0 s, 2790 frames at 30 fps
  (look2: 152.6 s). The heading never changes (checked: off the axis by under 1 m, heading constant).
- Motion blur 0.2 (look1 and look2: 0.35): at 0.35 the ground near the camera at 95 m/s smeared to streaks; at 0.2 it
  reads as ground moving fast. Chosen on the stills at 7 s, 50 s and 85 s.
- The thermal plant's chimneys are ahead at the end (in view from about 60 s), the nuclear plant off to the right,
  which suits handing over to the cooling chapter.

## 2. The record on selected dates

On each date both lines show the state the network record gives for that day; nothing between is shown. It is said in
camera_south_look3.json `record.statement` ("States shown on selected dates; the changes between them left out; the
full record in the zoom-out. ...") with every date, its film time, states, the events that set them and their
sources (`record.dates`). Every state is checked in code: each date's `expect` (and `island`, `loss`) against the
record, refused if they differ (`Selected`). **All 20 match the record; no mismatch.**

| Date | Film s | Dniprovska (left) | Ferosplavna-1 (right) | |
|---|---|---|---|---|
| 24 Feb 2022 | 3.5 | on | on | before the war, the full chord; dashes out to the grid |
| 4 Mar 2022 | 8.3 | unknown | unknown | lines cut, the reports don't say which; no dashes |
| 5 Sep 2022 | 12.6 | off | off | island mode (the note faint, the Hum's low note) |
| 16 Sep 2022 | 16.9 | on | unknown | Dniprovska back; dashes into the plant: the reversal |
| 17 Jan 2023 | 22.1 | on | on | |
| 1 Mar 2023 | 26.2 | on | off | (an outage of Dniprovska within that day is not shown: within_day_left_out) |
| 6 Jun 2023 | 30.3 | on | off | the dam: pinned at along 2508 m (camera there at 2504 m) |
| 7-11 Jun 2023 | 31.8, 32.7, 33.6, 34.5, 35.4 | on | off | the water falling day by day with the gauges |
| 17 Jun 2023 | 37.5 | on | off | settled |
| 1 Jul 2023 | 42.5 | on | on | |
| 21 Nov 2024 | 48.5 | off | on | the 330 kV alone |
| 7 May 2025 | 53.5 | on | off | |
| 23 Sep 2025 | 58.5 | off | off | the longest complete loss, held 8 s, silence |
| 8 Nov 2025 | 66.5 | on | on | |
| 24 Mar 2026 | 72.5 | off | on | the lift begins 1.8 s later |
| 11 Sep 2026 | 79.0 to the end (93.0) | off | on | the last report, held through the lift and fade |

- The dam lands at 30.3 s, earlier than the brief's ~32-34 s, because its place is pinned (along ~2508 m, where the
  approved films have it) and the cruise is faster. So the first six dates are held 4.1-5.2 s each, the bed's dates
  5-8 s.
- The date shown jumps; what changes with the date (the water's level, the passes, the plants) eases to the new date
  over 1.5 s, or runs on day by day from 6 to 11 June (the falling water, the gauge levels).
- Sides: Dniprovska on the left (pan -0.85), Ferosplavna-1 on the right (0.85). The names show from 12 s to 77 s
  (the lines cross ahead at about 81 s and swap sides).

## 3. Sound

- Swell 1.2 s on a reconnection, fall 0.6 s on a cut (look2: 0.6 and 0.3; the picture keeps its own fades, 0.6 s on and
  0.25 s off). The island's low note at 0.07.
- Checked on the Hum rendered alone (scripts/hum_check.py; sound/hum_envelopes.png): 11 moments where a line
  switches (16 line changes; the dam's steps change no line), the closest 4.1 s apart (8.3/12.6, 12.6/16.9 at 4.3,
  22.1/26.2 at 4.1). Silence in the complete loss (RMS 0.008 against 0.33 with both on), the island's low hold (0.018),
  unknown muffled.
- The two voices are distinct: with both on, the 200 Hz partial (the 750 kV's stressed harmonic) is 2.9 times stronger
  on the left (Dniprovska) than on the right, the 600 Hz (the 330 kV's) 4.2 times stronger on the right.

### The truer Hum (9 November 2026)

The user asked for the crackle at full strength on every connected line, swelling in rain and fog on the dates the
weather data shows, and the 750 and 330 kV voices clearly apart. hum.py now does that (its `CORONA`, `HUM_SHAPE`,
`wet_days`; the film's `.sound.json` beside the mp4 says what was made). The sound alone was made again and laid under
the same picture, copied, not re-encoded (`evidence satellite crossing3d --pass sound --variant south_look3`); the old
.wav and .mp4 are kept in the session's scratchpad.
- The picture's stream is byte-identical to before.
- Loudness: -9.0 LUFS integrated (was -9.2), RMS -13.8 dBFS (was -11.8), peaks -0.1 dBFS (rounded off above 0.7).
- The crackle against the hum (1.5-12 kHz against 80-650 Hz, median over the film): -5.6 dB on the left
  (Dniprovska) and -8.2 dB on the right (Ferosplavna-1), where the old Hum had -28 and -29: before, it was barely there.
- 12 of the dates shown have wet hours in ERA5 at the crossing (rain, or fog inferred from humidity and wind); 6 of
  them 6 hours or more, a full swell: 4 March 2022, 16 September 2022, 11 June 2023 (18 h, the week the dam broke),
  21 November 2024, 7 May 2025, 24 March 2026 (14 h, the day Dniprovska is cut). The swell eases in over 0.5 s and out
  over 1.5 s; it shows as the brighter blocks in the spectrograms.
- `sound/truer/`: the spectrograms, old and new, each channel (look3_{old,new}_{left,right}.png; the flight south has
  Dniprovska on the left) and look3_check.json; `scripts/truer_check.py` makes them.

## 4. Flow

A dated, sourced period toward the grid from 1 September 2021 until 11 September 2022, in the variant's own
`flow_periods` (`states.flow_config` puts it before the shared periods; the approved films don't have it, so their
frames before the date is shown keep the first shared period's direction). Sources: Wikipedia on the plant (more
than a fifth of Ukraine's electricity), the WNA's chronology, Energoatom via Babel (11 September 2022, unit 6
disconnected at 03:41). From 6 September the shared period (toward the plant) is drawn; no line is connected in island
mode, so no dashes either way. The dashes stay a drawing convention, said in the flow statement.

## 5. The look

1. **The river reads as moving water.** The cause of look2's "flat olive river with no detail" was not the water: it
   was look1's `far_plain` (a dark plain at 8 m meant for beyond the land) lying over the lower drained bed, so the
   river and the sand beside it showed as one flat sheet with stair-stepped edges (found by a debug render with the
   plain off). Fixed with `far_plain.hole` (look3 only: the plain only outside the land, 60 m in). Then the surface:
   the colour still the passes' own (the median of each pass's water), varied by each pass's own pixels over its
   water (each band's ratio to the median, blurred over 1 px, clamped 0.75-1.3, never on the caissons' discs:
   look/<pass>_watervar_v1.png, stats in scene.json), current streaks along 255° drifting at 0.6 m/s, gust patches,
   ripple and chop, faint scum lines, roughness by patch and streak, Fresnel reflection of the drawn sky. All drawn
   and said in scene.json `look.south_look3` (`water_variation`, the water detail statement).
2. **The stair-stepped edge, smoothed sub-pixel.** Each pass's river mask (the bed's 20 m grid) softened by a
   Gaussian of 0.5 px and read bilinearly; the water drawn where the field is at least 0.5 (a dithered alpha band
   0.3-0.7). Measured per pass (scene.json `look.south_look3.water_edge.tolerance_px`): the contour lies at most
   0.375 px (7.5 m) from the mask's pixel edges, and every pixel edge at most 0.525 px from the contour (the 99th
   percentile 0.25 and 0.35). At 0.6 px thin channels began to drop (0.67 px), so 0.5. No shoreline moved further.
   A dark rim under the sheet's edge (screen-traced reflections hitting the sheet's back) was cut with `rays.backface:
   false` and the wider band; a faint line remains at some angles.
3. **Plants.** Toned in the shader (`look.vegetation.tone`): saturation 0.55, pulled 40% toward the imagery under each
   plant, a late-summer olive and dry tint by clump (60 m), size varied by clump (±15%), darker toward the base. The
   bed reads as olive and straw saplings and shrubs over the sand, not bright green. The far woods on the banks were
   not measured against the imagery in this pass (look2 set `gain` 0.8 for that; the tone pulls them further toward
   the ground under them).
4. **Other things seen in the stills.** Done: the shorter motion blur. Left: the near ground is soft (10 m imagery
   from 70 m up), shown as it is: no haze or camera change to hide it (the user's rule). The faint edge line in 2. A
   measured check of the far woods' tone against the imagery.

## Look-dev (contact sheets/)

- look2_vs_look3_A_D_drain_river.jpg: look2 (left, matched by where the camera is) and look3 (right) at 7 s, 19 s,
  35 s and 46 s.
- look2_vs_look3_8_10_11_lift.jpg: the same at 50 s, 62 s, 69 s and 85 s (during the lift, look2's frame from its
  rise).
- sound/hum_envelopes.png: the Hum's two channels, the 200 Hz and 600 Hz partials, the selected dates.
- scripts/: sheet.py (the comparison), hum_check.py (the Hum alone, the switches and partials).

## Seen, for the main session

- The river now reads as water: ripples, reflections of the towers and wires, lighter and darker reaches as the
  passes saw them, soft shores. The olive plane is gone.
- 23 September 2025 (58.5-66.5 s): both lines unlit over the bed, silence; the frame holds well without the glow.
- The lift shows the thermal plant's chimneys ahead with Ferosplavna-1 lit, Dniprovska dark: a clear last image.
- The first six dates come quickly (about 4-5 s each) because the dam is pinned; if they feel rushed, a later start
  of the descent would give them room, not a slower cruise.
