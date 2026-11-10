# Tilt-shift opening

Asked by the user on 9 November 2026: the film's start "seems to jump too fast into the powerlines". The idea is an
opening shot with more context, using a tilt-shift photography effect. It should frame the nuclear power plant
together with the Enerhodar crossing, and show the relevant city and place names. The next shot will zoom in and
rotate to another perspective, where the titles get more specific.

## Second pass (the user's notes on the first, 9 November 2026)

The user's notes:

> the things near the front are way too blurred. even the things in the background are too blurred ... the znpp and
> the enerhodar crossing should be moved to the right of the screen a bit more so they are more at the center ... look
> at ... how the wsj did it ... the text ... more like apple maps/google maps style, with a smaller font size ... the
> 'former kakhova reservoir' can be placed like how google maps/apple maps does water names ... ensure that the
> blurring effect and stuff is done tastefully, not so over-the-top ... a more appealing color grading ... it feels too
> yellowish

### The reference

The WSJ piece is "How China would invade Taiwan" (wsj.com/world/china/how-china-chinese-invasion-taiwan-ba7e3916).
It couldn't be read: the fetch tool is refused by wsj.com, and the page wasn't opened another way.

What is taken from the WSJ's 3D map graphics in general:
- tilted, true-size terrain seen from high up;
- depth of field used sparingly, if at all;
- a muted, slightly cool palette that lets the overlays carry the colour;
- small, quiet map-style labels in mixed case, light on dark with a soft halo, and no boxes;
- water named in italic.

Worth checking against the page itself when someone can open it.

### What changed

- **Framing (vantage A2, re-rendered).**
  - The camera slides 1.6 km to its left (south-west) and 0.4 km back, with no turn, so the scene moves right in the
    frame.
  - The plant now sits at x ≈ 720, the lines' landing on the south shore at ≈ 1190, and the north bank's landing at
    ≈ 1650 (of 1920). The plant and the crossing are about centred.
  - Pitched 3° further down (−30°), so the grey band at the top is thinner. The haze is unchanged (visibility 300 km).
  - Same height family (about 4.8 km up), 22 mm lens, heading −40°, the same 4.5% eased push.
- **Depth of field, restrained.**
  - The same true focal plane as the first pass: vertical, through the plant and the lines' landing on the north bank.
  - The blur is k·|1/t_focus − 1/t| with k = 1.0e5, less a dead zone of 0.6 px, so a wide band stays fully sharp.
  - It is eased (tanh) into a ceiling of 3 px at 1080p, down from 13 px before.
  - Enerhodar in front and Nikopol and the north bank behind stay readable and only soften.
- **Names, set as maps set them.**
  - SF Pro (`SFNS.ttf`, the system face Apple Maps uses), in mixed case.
  - Light text with a soft dark halo (dilated by 1 px, then blurred by σ 1.6, at 0.6), no boxes, and a small white dot
    on each place, with the name beside it.
  - Sizes at 1080p:
    - the plant: Semibold 20 px;
    - the thermal plant: Medium 16 px;
    - towns: Medium 18 px.
  - "Power lines to the north bank" is Medium 15 px in a pale wire-yellow, set along the crossing about 600 m west of
    the lines, the way a map names a road. No tower is marked.
  - "Former Kakhovka Reservoir" is Medium Italic 17 px, letter-spaced 3.2 px, in a muted water blue (172, 202, 224)
    with a lighter halo, no dot. It is set along the drained bed's course west of the crossing; each letter is turned
    to a smooth curve through three points.
  - Names are drawn after the blur and the grade, so they are always sharp.
  - Kamianka-Dniprovska and Vodiane now fit in the frame, so they show.
- **Grade, three variants.** Each is a white balance in linear light (the yellow taken out), then contrast,
  saturation, an optional split tone and a gamma, plus the look's faint vignette (×0.7) and grain. No colour is
  painted.

  | Variant | What it does | Mean RGB, middle of frame |
  |---|---|---|
  | (render, ungraded) | | 110 / 107 / 100: R−B 11, the yellow |
  | `neutral` | yellow balanced out (wb 0.93 / 0.98 / 1.10), contrast 1.06, saturation 0.92 | R−B 3 |
  | `slate` | the same balance, saturation 0.74, contrast 1.08, cool slate-teal shadows, faintly warm highlights | R−B 0 |
  | `daylight` | a lighter balance (0.95 / 0.985 / 1.07), contrast 1.10, saturation 1.04, brighter midtones (gamma 0.93) | R−B 6 |

  **Picked: `slate`.** It is the least yellow and the most restrained: an editorial map palette like the WSJ's. The
  imagery stays believable. The lit line, the water name and the white names carry the colour, and the wire-yellow
  stands out more on cool ground. `neutral` is close behind. `daylight` still reads a little warm.
- **Stills** in `stills/`:
  - `still_A2_present_{neutral,slate,daylight}.png`;
  - `still_A2_prewar_slate.png` (the full reservoir, every line lit);
  - `*_plain.png` (the renders before the post).

## Third pass: render once, push in afterwards (the user, 10 November 2026)

> i would like this approach to be taken so the video is rendered much faster: Render once, push in afterwards. With a
> camera this still, one larger render could be slowly zoomed into, the way the 2D films only resample real pixels

`establish.py push` is now the method for near-still shots. `clip` keeps rendering every frame, for cameras that move.

How it works:
- **One render.** Blender renders the shot's first frame once, at 2400×1350 (1.25× each side, the same lens, so the
  same view with more pixels), with its distances.
- **On that one still:** the tilt-shift (from its depth, blurred by 1.25× as many pixels), then the colour grade.
- **The push is a zoom.** The 4.5% dolly toward the look-at point magnifies what lies at the look-at distance by
  1 / (1 − 4.5% · ease). The same magnification as a zoom about the frame's centre is the first frame's camera with its
  lens lengthened by that factor (up to 1.0471×), eased in and out exactly as the dolly was.
- **Each frame:** the centre crop of the still for that zoom, resampled to 1920×1080 (Lanczos, a sub-pixel float box).
  It is always a reduction: the last frame's crop is still 1.194× the frame, so nothing is upscaled.
- **Then, per frame:** the look's vignette and grain (fixed to the frame), and the names drawn sharp at their places
  under the zoomed camera, so they stay locked to the picture and never scale soft.
- Pixels are only resampled: nothing is generated, and no frames are interpolated.
- **Names that leave the frame fade out first.** Every name in the first frame is drawn. A name the zoom would carry
  past the frame's edge fades out over 1.2 s, ending 0.2 s before its last frame inside (`LEAVE_S`), rather than being
  dropped. Under the zoom only Kamianka-Dniprovska leaves: it fades out by 7.33 s.

The json says so: the push is a zoom into one render, a drawing convention, with no parallax.

**Time.** About 2 min for the whole 9 s clip:

| Step | Time |
|---|---|
| Blender render of the still (build, picture, depth) | 57 s |
| Post: blur, grade and 270 frames of crop, grain and names | 73 s |

The per-frame render took 87 min. The names' layer now touches only each glyph's box; that alone took the post from
8 min to about 1 min, with identical output (at most 1 level apart, from rounding).

**Compared with the per-frame render** (`compare/compare_f0001.jpg`, `compare/compare_f0270.jpg`: both frames, the
difference ×6, and 1:1 crops of the plant):

| Frame | Mean abs difference | PSNR | Mean shift | 95th percentile shift |
|---|---|---|---|---|
| First | 0.33 / 255 | 51.7 dB | 0.01 px | — |
| Last | 8.9 / 255 | 23.5 dB | 4.9 px | 17 px |

- The first frame is the same picture.
- The last frame shows the same content. The difference is points standing a few pixels apart (dense edges light up
  in the difference image), not changed pixels.
- Mean shift by band, top to bottom: 2.9, 6.6, 1.4, 5.0, 8.7 px. Nothing is displaced at the plant's row (the
  look-at distance). Toward the near bottom edge, a dolly grows the ground more than the zoom does; toward the far top,
  less. That is the parallax the zoom leaves out: a few pixels over 9 s.
- The 1:1 crops of the plant are almost identical.

The per-frame render is kept as `tilt_shift_opening_perframe.mp4` (with its `_sheet`, `_last` and `.json`) for
comparison.

## What it is (every pass)

- **The scene.** It is the crossing's 3D scene exactly as the flight south (`south_look3`, in the cut) builds it:
  - the plant, the thermal plant and Enerhodar, modelled;
  - the land and the Sentinel-2 passes;
  - both crossings' towers and wires, and the plant's other lines;
  - the look pass's sky, water and vegetation.

  Only two things are new:
  - the camera;
  - the air: visibility 300 km instead of 100. From 4-5 km up you look down through thinner air than along the
    ground. It is a drawn haze either way.
- **The date.** The scene's state is held at one date, copied from a frame of `camera_south_look3.json`: its passes,
  water, wet band, plants' growth and every line's state.
  - `present`: 11 September 2026, the last report, on the 28 August 2025 pass. The bed is drained. Ferosplavna-1 is
    lit; Dniprovska and the plant's other lines are cut.
  - `prewar`: 24 February 2022, on the 8 September 2021 pass. The reservoir is full and every line is lit.
- **The motion.** 9 s, nearly still: a 4.5% push toward the look-at point, eased from rest to rest. There is no turn
  and no drift. The last frame is the handoff to the next shot.
- **The names.** They fade in one after another from 1.6 s. Only names inside the frame from the first frame to the
  last are shown, so none pops at an edge. Positions are from OpenStreetMap for the plants and GeoNames for the towns.
  No substation, tower, repair or damage site, crew position or trench site is named or marked.
- **No sound yet.**

## Files

- `scripts/establish.py`:
  - `push [A2 present]`: the shot by render once, push in afterwards (the method for near-still shots);
  - `clip [A2 present]`: every frame rendered (for a moving camera), then `post`;
  - `post [A2 present]`: redoes the per-frame render's depth of field, grade and names without rendering;
  - `stills`: renders A2 present and prewar, then posts the three grades.

  Blender runs headless. It runs `build.py --no-render`, then `scripts/ts_render.py` on the same scene: the picture,
  then each pixel's distance. The scratchpad holds:
  - `tiltshift/push_A2_present/`: the 2400×1350 still, its depth and the frames;
  - `tiltshift/clip_A2_present/`: the per-frame render, about 3.5 GB.

  Both may vanish with /private/tmp. The project's .blend files aren't touched.
- `tilt_shift_opening.mp4`: the shot (third pass, push), 30 fps (a test), silent. Beside it: `_sheet.jpg`,
  `_last.png`, and `.json`, which holds the method, camera, focal plane, date state, names and sources, and the
  statement.
- `tilt_shift_opening_perframe.*`: the second pass, every frame rendered, kept for comparison.
- `compare/`: the first and last frames of both methods, side by side, with their difference.
- `zones/`: the plant's zones, preview stills, one per zone in four palettes, with a wide view for the rings (its own
  README).
- Render time:
  - first pass: 88 min (about 16 s a frame for the picture, plus the distance pass);
  - second pass (A2, every frame): started at 22:51 on 9 November 2026, paused at 23:28 after 107 frames (the user
    went offline), resumed at 00:12 and finished at 01:13 on 10 November; about 87 min of rendering in all
    (37 + 50 min), then about 1 min of post;
  - third pass (A2, push): 57 s render and 73 s post, about 2 min.
