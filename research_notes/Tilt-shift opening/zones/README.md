# The plant's zones (preview stills, one zone each, four palettes)

The zones round the Zaporizhzhia NPP as previews over the tilt-shift establishing shot's scene. The design was approved
with the user on 9 November 2026 and revised twice on 10 November.

First revision:

> the other text on the map should not be visible when the zones are being shown one by one. also for the dome zone it
> should be a gradient with the bottom of the being more opaque than the top, i dont like the dotted/dashes mesh look.
> please preview these shots before animating. for the improved zone still frames show me one image per zone so i can
> differentiate them

Second revision:

> yes make a wider view for z3 and z4. also remove z5 since if there is no visual proposal might as well not include
> it? also perhaps a better color than white?

Sources and wording are from `reports/ZNPP as a military shield.md` ("Only the zone meant to stop the fighting never
had a size", "Showing the shield"). These are stills only. No film code was changed and nothing went into the
storyboard.

    .venv/bin/python -I "research_notes/Tilt-shift opening/zones/scripts/palettes.py"   # the palettes' check
    .venv/bin/python -I "research_notes/Tilt-shift opening/zones/scripts/zones.py" [ice lavender mint rose]

`scripts/zones.py` reuses `../scripts/establish.py` for the camera, the blur, the grade and the type.

## The stills

Each image shows **one zone and its own label only**, with no other text. Every zone is made in each palette.

| File | Zone | Camera |
|---|---|---|
| `zones_C_dome_<palette>.png` | IAEA protection zone: the dome and its label | close: heading −40°, pitch −30°, 4.2 km from a point just south of the units, 30 mm |
| `zones_wide_paz_<palette>.png` | IAEA precautionary action zone, a band from 3 to 5 km | wide |
| `zones_wide_upz_<palette>.png` | IAEA urgent protective action planning zone, a band from 15 to 30 km, its fill fading toward 30 km | wide |
| `zones_wide_obs_<palette>.png` | Ukraine's observation zone, a dashed ring at 30 km | wide |
| `zones_sheet_<palette>.jpg` | the four above side by side, half size | |

The labels:
- "IAEA protection zone / proposed 6 Sep 2022, never agreed / no size published: “limited to the perimeter and the
  plant itself” / drawn on the plant’s site: its shape and height are ours"
- "Precautionary action zone · out to 3–5 km · IAEA"
- "Urgent protective action planning zone · out to 15–30 km · IAEA"
- "Observation zone · 30 km · Ukraine"

Sources:
- The IAEA bands: EPR-NPP Public Protective Actions (2013), Table 3, "suggested maximum radius".
- Ukraine's ring: Ukrainian norms as reported, and Ukrhydromet's daily bulletin, which draws 30 km dashed round each
  plant (secondary sources, as the report says).

What else changed:
- **Removed:** the unsized proposals (the UN Secretary-General's "demilitarised perimeter", AP I Art. 56(5)'s "the
  vicinity", the seven repair truces) are no longer drawn: they have no size, so nothing to show. They stay in
  `zones.json` (`unsized`) as research.
- **Superseded:** the A2-camera versions of the zones. The wide view shows the rings better, and the close-up shows the
  dome better.
- **The foot line** ("planning distances, not barriers") is left off, as asked. It is said here and in `zones.json`,
  and needs a place in the film (a caption or the narration).

## The wide view

Its own Blender still render (53 s), in the shot's heading family:
- Heading −40°, pitch −45°, 28 mm, 42.5 km from the zones' centre, about 30 km up.
- Found by projecting the 15 km ring for headings −40° to 0°, pitches −40° to −70°, lenses of 20–28 mm and distances
  of 20–90 km, and keeping the widest fit.
- The whole 15 km ring lies on the ground, with Enerhodar near the middle, Marhanets (13.7 km) just inside the ring and
  Nikopol (16.1 km) just outside. About 45% of the 30 km ring is in the frame.

The settings:
- **Haze:** visibility 1,500 km for this camera only. At 42 km the look's 300 km air greyed the land out.
- **Tilt-shift:** kept at the shot's settings. At this distance it softens only the frame's far and near edges, by at
  most 1.3 px (0.3 px on average), as a real lens's depth of field would.
- **Grade:** slate, as the opening.

**The land's box shows.** The modelled land ends 17 km west, 23 km east, 19.5 km south and 28.5 km north of the plant.
Beyond it lies the look's far plain, a flat drawn ground in the land's mean colour, 8 m up. From this height the land
reads as a tile on that plain, the cut-out look of a terrain model.
- The rings run on over the plain: there, each pixel's ground point is its ray met with the plain's plane, so the ring
  is exact.
- The 30 km ring steps a little where it crosses onto the land near the box's north corners, because the land stands
  higher than the plain and the box's edge is a drop. That is the scene's geometry, not an error.
- Off the land, the rings are drawn on drawn ground, and that has to be said wherever this view is used.

## Colour

Four palettes. In each, the IAEA zones are one hue family (the dome the lightest and most luminous, then the 3–5 km
band, then the 15–30 km band), and Ukraine's zone is another hue. All are kept away from:
- the lines' two yellows (#FFD600, #F09C00);
- the old amber (#FADEB2);
- the water label's muted blue (#ACCAE0);
- red (#DC2828, kept for the front line).

| Palette | Dome | 3–5 km band | 15–30 km band | Ukraine 30 km |
|---|---|---|---|---|
| **lavender** (recommended) | #DCCBFF | #C9B6FF | #A08BF2 | #86E3BE (mint) |
| ice | #BDF1F5 | #9BE7EC | #5FCBD6 | #C3A6F5 (violet) |
| mint | #BEF5DC | #93ECC8 | #52D0A2 | #E7A9CE (rose) |
| rose | #F8C8E2 | #F2AFD3 | #D886B8 | #86DDE8 (ice cyan) |

Labels are their zone's colour, taken 40% toward white so they read on the dark ground. The dome's rim is its own
colour.

**The check** (`scripts/palettes.py`, `palettes.json`):
- CIE76 colour difference (ΔE in Lab) between the IAEA zones' middle colour and Ukraine's colour, and from each
  reserved colour.
- Done with normal vision and simulated protanopia, deuteranopia and tritanopia (Machado, Oliveira & Fernandes 2009,
  severity 1.0, applied in linear RGB).
- Each colour's contrast ratio on the slate-graded ground (#5E5E58).

| Palette | IAEA vs Ukraine, ΔE: normal / protan / deutan / tritan | Worst | Closest a colour comes to a reserved one |
|---|---|---|---|
| lavender | 71.9 / 49.1 / 40.2 / 38.6 | 38.6 | the dome to the water blue, deutan, 9.4 |
| ice | 56.3 / 35.5 / 25.8 / 41.3 | 25.8 | the 15–30 km cyan to the water blue, protan, 3.2 |
| mint | 66.7 / 32.3 / 16.0 / 63.8 | 16.0 | Ukraine's rose to the water blue, protan, 7.3 |
| rose | 53.7 / 10.2 / 10.6 / 69.2 | 10.2 | Ukraine's cyan to the water blue, deutan, 2.6 |

**Recommended: lavender.**
- It keeps the IAEA family and Ukraine's zone furthest apart for every kind of colour vision (never under 38).
- No colour comes near a reserved one: the closest is the dome to the water blue under deuteranopia, at 9.4.
- Violet sits on the slate earth without reading as water, power or the front.
- Its one weakness is the 15–30 km band's colour, the dimmest (contrast 2.3:1 on the ground). As a faint fill with a
  thin edge it reads, but it could be lifted a step.

Ice is the runner-up, but its cyans fall close to the water label's blue for protan and deutan viewers. Mint and rose
lose the IAEA/Ukraine separation for red-green colour-blind viewers (16 and 10).

## One centre

The rings and the dome share one centre: the centre of the smallest circle round OSM way 28877213 (the plant's site,
the same circle the zoom-out's zone uses), (−3.8, 151.2) m in the scene's plane, lon 34.587851, lat 47.509923.

The six reactor units' centroid (OSM power=generator ways 1572378821–30) lies 233 m from it, well under the guidance's
precision (3–5 km, 15–30 km).

Distances from the centre:

| Place | Distance |
|---|---|
| Enerhodar | 5.98 km |
| Vodiane | 6.91 km |
| Kamianka-Dniprovska | 13.44 km |
| Marhanets | 13.66 km |
| Nikopol | 16.13 km |

## The dome: a gradient

The dome is a smooth translucent shell on the 825 m site circle. Its height equals that radius and is ours.
- Each pixel's ray is met with the hemisphere. Its far surface is laid first and its near surface over it.
- Each surface's opacity is `0.55 × (1 − h / (0.92 R))^1.3 × obliqueness`:
  - fullest at the ground and reaching nothing at 92% of the height, so it never closes: the "never agreed" reading;
  - obliqueness from 0.38 square on up to 1 grazing, as `(1 − |n·v|)^2`.
- Its foot fades in over the first 25 m.
- The ground hides it over a soft 200 m, so the plant's 40–50 m buildings don't cut it.
- A faint rim (0.55): a 3D circle at the terrain's height, fading where the ground is nearer.
- It is drawn at twice the frame's size, then reduced.

## Draping (the rings)

Every pixel's ground point comes from the camera, its own ray and the distance Blender rendered for it (on the far
plain, from the plain's plane). From that, each pixel's horizontal distance from the centre is known.
- A **band** is the set of pixels whose ground lies between its radii.
- A **ring** is the set of pixels within a line's half-width of its radius. Every ring is 1.6 px wide on screen (2.2 px
  for Ukraine's dashed ring, so its colour reads), anti-aliased.
- The dashes are 900 m on the ground, set by bearing.
- A ring label goes at its preferred bearing, else at the nearest bearing where it fits the frame.

The order is: raw frame → tilt-shift → zone → slate grade → label.

## Time

Making all sixteen stills and four sheets takes about 40 s. The two Blender still renders are cached in the
scratchpad: the close-up (49 s) and the wide view (53 s).

## 10 November 2026: white, and the far corner fixed

The user chose the white palette (`white` in `palettes.py`, the first design's colours: the IAEA zones near-white,
Ukraine's ring a pale amber) over lavender, ice, mint and rose; `zones_*_white.png` and `zones_sheet_white.jpg`.
The 30 km ring broke at the land's far corner in the wide view: Blender's depth pass is half float underneath, so
every distance past 65,504 m came back clamped there and those pixels read as ground about 2 km up. Such pixels are now
met with the terrain (`terrain_z`, each ray against terrain.npz and terrain_south.npz), so the rings run unbroken
across the corner and onto the far plain.

## 10 November 2026: the animation (`zones_anim.py`)

The user: "please add these to the storyboard instead of the zo-zone in an animation with appropriate length".
`zones_animation.mp4` (24.5 s, 30 fps, silent; `.json`, `_sheet.jpg`, `_last.png`), in the storyboard as `zones` in
zo-zone's place (zo-zone parked). Render once, push afterwards: each camera rendered once at 2400x1350, the tilt-shift,
the zones and the grade on that still, then each frame a centre crop resampled (always a reduction). 0-7.6 s close on
the plant, the dome fading in (1-2.5 s) and its four lines (2.5-3.3 s, out by 7.4 s), a slow zoom in to rest; a
dissolve to the wide view (7.6-8.8 s), easing back from 1.2x to the approved framing by 20 s while the zones come one
at a time, each with only its own label: 3-5 km (9 s), 15-30 km (13.6 s), Ukraine's 30 km ring (19.2 s, held to the
end). zones.py's overlays are now coverage maps at any size (`zone_cov`, `dome_cov`; the stills unchanged to the pixel).
`--fps 60` for the final.
