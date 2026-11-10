# Flight south, look pass 1 (7 November 2026)

A new variant, `south_look1`, beside the approved `south_record` (decided with the user, 7 November 2026: an improved
full-length render made overnight). Same camera path and motion, record, timing, sound and fades; only the look
changed. The output sits beside the old film:
`libraries/conductive-seam/satellite/networks/znpp/scenes/crossing3d/animatic/ZNPP-last-two-lines-3D-south-look1.mp4`
(.wav, .blend, _contact.webp). How to follow, pause and resume the render: RESUME.md.

The look target was the user's reference frame (overcast, dark water, long vertical reflections, crisp dark wires on a
bright sky). It may be AI-made: it was used only as a look to aim for; nothing from it is in the film.

## How it is built (all options of the variant; the approved films render exactly as before)

- Config: `crossing3d.animatic.variants.south_look1` in config/conductive-seam.yaml (a copy of `south_record` plus
  `title` and `look:`). Nothing shared was changed.
- `scene3d/build.py`: a `look` read from camera_<variant>.json; every option off by default. Checked: south_record's
  frames 841 and 1201 rendered with the new code are identical to the ones rendered before it (mean difference 0.0002
  of a level, max 1).
- `scene3d/look.py` (new): the pre-breach pass, the colour matching, the per-frame shares and wet band.
- `scene3d/export.py`: the variant's `look` copied into its camera json; scene.json `look.south_look1` (the matched
  copies and their fits, the pre-breach pass, a statement of everything drawn).
- `scene3d/animatic.py`: the grade (`grade_image`, `_grade`, raw frames kept in `<variant>/raw/` so it can be redone
  without rendering); `--resume`.
- `cli.py`: `--resume`. build.py: `--frames a,b,c` (stills) and `--keep-existing`.
- tests/test_look.py (4 tests); the whole suite passes (166 passed, 1 skipped).

## The improvements, 1-11

1. Sky: done. A drawn overcast sky (world shader): grey, lighter toward the horizon, a soft low-contrast cloud deck
   (noise on a plane 1.5 km up, seen in perspective from where the camera is, drifting 3 m/s). Kept faint after the
   first try (too streaky near the horizon): cloud size 5 km, little detail, the deck thinning into the horizon grey.
2. Water: done in part. Darker and bluer (the passes' measured water colour, tinted); fine wind ripples stretched
   across the view (they show the speed and stretch the reflections into vertical streaks), fading out far off so they
   don't shimmer; Fresnel reflections at full strength, smoother water. The planar light probe was tried: in Blender
   5.2's EEVEE it cost 4 s a frame and the reflections disappeared (badly placed or unsupported with screen tracing);
   dropped. Screen-space reflections at full resolution instead: the towers' reflections show (see v2/v3 stills),
   but what is off screen (the towers' tops near the frame's top edge) isn't reflected.
   The water's colour is now uniform per pass (`water.uniform`: the median of the pass's water pixels, as before for
   the later passes) instead of the 2021 pass's own pixels: those carried the caissons' concrete as pale blots round
   each caisson (the "white halo discs").
3. Caissons: done. Their own concrete (grey, lit), darker under and in a band just over the frame's water level
   (keyed, so the band follows the drain), the halo gone (above).
4. Cut wires: done. Bare cut wire dark steel (62, 66, 72 on screen) instead of light steel, so "cut" reads against
   the sky; unreported: the same dark dots with light gaps (150, 155, 160). Lit wires unchanged (yellow, glow, flow),
   plus a soft bloom (Blender's compositor, Glare: Bloom).
5. Light: done without shadows. The towers, caissons and plant are lit surfaces (Principled) under the sky's light and
   a soft high sun (55°, from the SSE, 25° wide). Shadows were measured at about 13 s a frame (EEVEE's shadow maps over
   the whole 40 km scene), so they are off: no contact shadows. The land stays the imagery itself (unlit).
6. Grade: done. AgX (Medium High Contrast), a slight cool tint, faint vignette, very light grain (0.006; the first
   try's 0.025 was far too strong), motion blur (shutter 0.35). Saturation left at 1.0 (AgX already takes some off;
   0.85 greyed the towers' paint).
7. Samples: 64 (from 16). With shadows off a frame takes about 5.3 s at 64 samples.
8. Banks before the breach: done. Sentinel-2 of 5 June 2023 (`c3d_2023_06_05`, `c3s_2023_06_05`; the same orbit as
   the bed's reference pass, items' cloud 0-8.6%, the land clear by eye) dissolves in over the 2021 pass between 15
   December 2022 and 20 May 2023 by the date shown (the land and the reservoir's own pixels), so at the breach only
   the water changes. Said in scene.json `look.south_look1.pre_breach_statement`.
9. Colour matching: done. Every pass on the ground (the five, the pre-breach one; the south strip takes the same
   pass's fit) matched to the 2021 pass: a gain and offset per band fitted (reduced major axis; a plain least-squares
   fit shrank the gains to 0.3-0.7 because the fields change) on stable land (outside the reservoir's footprint
   widened 500 m, neither water nor cloud), trimmed to the best-agreeing 60% and refitted. Gains 0.86-0.95, offsets
   -7..+15 levels. The fits in scene.json `look.south_look1.matched` and scenes/crossing3d/look/match.json; matched
   copies in scenes/crossing3d/look/*.png (originals untouched).
10. Receding waterline: done. The water's colour follows its depth over the inferred bed (a neutral, drawn bottom tone
    at the shore turning into the water's colour by 1.5 m deep); it stays opaque, so no later pass is ever seen under
    it. A wet band: the bed the water left in the last 4 days darker (by 45%) and glossy (Fresnel), by height between
    the level now and the level 4 days before (an approximation of each spot's time out of the water), gone 3 days
    after the level settles. The mesh was not refined: the depth tone softens the 20 m mesh's edge enough in the
    stills.
11. Dissolving only where the ground changed: not done (no time left; optional).

## Look-dev stills (contact sheets/)

stills_v1.jpg, stills_v2.jpg, stills_v3.jpg: the reference on top, then the old render (left) and the new still
(right, graded) at 12, 20, 28, 40, 75, 120 s (v3: 12, 28, 33, 38, 40, 43, 120 s, the drain). v1: far too hazy,
bright and grainy, no reflections (the planar probe), caisson halos. v2: haze and grain down, probe off, SSR full
resolution, uniform water. v3 (the render's settings): brighter sky, softer clouds, lighter haze.

## Seen, to check in the finished film

- The ground near the camera is still soft (10 m imagery from 70 m up); nothing hides it (no haze or blur near).
- Distant towers' red reads greyish through the haze; near ones keep their paint.
- The lit wires' yellow is paler than in the old render (AgX); the bloom is soft. If it reads too pale, lower the
  view's contrast look or raise the wires' strength in a next pass.
- At 120 s the land beyond about 10 km is hazed (visibility 100 km in the model, but AgX lifts it); the plant and the
  cooling towers read.
- The clouds are faint; with the camera's -7° pitch little sky is in frame.
- Motion blur is on the whole film, with the shutter at 0.35: check the fast low stretch over the north bank (12 s).

## Times

Measured in Blender 5.2 on the M3 (timing scripts in scripts/): with shadows on, 19 s a frame (shadows 13.5 s, the
planar probe 4 s); without them 1.3 s at 16 samples, 3.2 s at 32, 4.8-5.1 s at 64 (with motion blur and full-resolution
reflections). Six stills spread over the film averaged 5.3 s each. The approved south_record's 8.3 h overnight render
took 6.5 s a frame at 16 samples, probably mostly EEVEE shadow maps (it has no lamp, but with shadows on a frame cost 4.9 s against 1.3 s off even with the sun's shadow off here: likely the world light's): a later pass could
turn `eevee.use_shadows` off there too, after checking the look is the same.

## Deleted (8 November 2026)

The render (frames, .mp4, .wav, .blend, contact sheet) and its storyboard preview were deleted at the user's request once look pass 3 went into the cut. The variant `south_look1` stays in the config; it can be rendered again from it.
